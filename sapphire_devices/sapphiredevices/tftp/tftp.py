#
# <license>
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# 
# 
# Copyright 2013 Sapphire Open Systems
#  
# </license>
#

import socket
import sys
import struct
import time
from Queue import Queue

CLIENT_POOL_SIZE = 4

TFTP_RRQ        = 1
TFTP_WRQ        = 2
TFTP_DAT        = 3
TFTP_ACK        = 4
TFTP_ERR        = 5

TFTP_SERVER_PORT = 69

TFTP_RETRIES = 10

# callback status codes
TFTP_STATUS_OK      = 0
TFTP_STATUS_ERR     = 1


def build_cmd_packet(cmd, filename):
    assert((cmd == TFTP_RRQ) or (cmd == TFTP_WRQ))
    
    format = '!H' + str(len(filename) + 1) + 's6s'
    
    return struct.pack(format, cmd, filename, 'octet')

def build_data_packet(block, data):
    if(len(data) > 512):
        data = data[:511]
        
    format = '!HH' + str(len(data)) + 's'
    
    return struct.pack(format, TFTP_DAT, block, data)

def build_ack_packet(block):
    return struct.pack('!HH', TFTP_ACK, block)

def build_error_packet(code, message):
    format = '!HH' + str(len(message) + 1)

    return struct.pack(format, TFTP_ERR, code, message)

def parse_packet(pkt):
    type = struct.unpack_from('!H', pkt)[0]
    
    if(type == TFTP_ACK):
        type, block = struct.unpack_from('!HH', pkt)
        return type, block, None
        
    elif(type == TFTP_DAT):
        data_len = len(pkt) - struct.calcsize('!HH')
    
        type, block, data = struct.unpack_from('!HH' + str(data_len) + 's', pkt)
        return type, block, data
        
    elif(type == TFTP_ERR):
        msg_len = len(pkt) - struct.calcsize('!HH')
    
        type, block, msg = struct.unpack_from('!HH' + str(msg_len) + 's', pkt)
        return type, block, msg

class TftpException(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class TftpTimeoutException(TftpException):
    def __init(self, value):
        super(TftpTimeoutException, self).__init__()

class TftpClient(object):

    # set up client pool queue
    _pool_q = Queue(maxsize=CLIENT_POOL_SIZE)

    def __init__(self, host, port=TFTP_SERVER_PORT):
        self.__host = (host, port)
        
        self.__retries = 0
        self.__block = 0
        self.__filedata = ''
        
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('',0))
        
        self.__sock.settimeout(1.0)

        self.packets_resent = 0
    
    def __transfer(self, pkt, response_type = None):
        self.__pkt = pkt        
        self.__retries = TFTP_RETRIES
        
        while(self.__retries > 0):
            # send write request
            self.__sock.sendto(pkt, self.__host)
            
            if(response_type != None):
                try:
                    # wait for response
                    recv_msg = self.__sock.recvfrom(4096)
                    
                    # check response
                    type, block, data = parse_packet(recv_msg[0])
                    
                    if((type != response_type) or (block != self.__block)):
                        raise TftpException("Invalid packet: type: %d (expected: %d) block: %d (expected: %d) data: %s" % (type, response_type, block, self.__block, data))
                    
                    return recv_msg, data
                    
                except socket.timeout:
                    
                    self.__retries = self.__retries - 1
                
                    if(self.__retries == 0):
                        raise TftpTimeoutException("TFTP transfer timed out")
                    else:
                        self.packets_resent = self.packets_resent + 1
                        
                except TftpException as e:
                    print e
                    
                    self.__retries = self.__retries - 1
                
                    if(self.__retries == 0):
                        raise
                    else:
                        self.packets_resent = self.packets_resent + 1
                
                except Exception as e:
                    raise
            
            else:
                # no response expected, set loop termination
                self.__retries = 0
    
    def get(self, filename, progress=None):
        # block on queue
        TftpClient._pool_q.put(None)

        try:
            # initiate connection
            self.__block = 1
            
            # clear filedata
            self.__filedata = ''
            
            # send read request
            recv_pkt, data = self.__transfer(build_cmd_packet(TFTP_RRQ, filename), response_type = TFTP_DAT)
            
            # response should contain first block of data
            self.__filedata = data
            
            # change host connection, server may have responded from a different port to 
            # handle the transfer
            self.__host = recv_pkt[1]
            
            # read data
            while(len(data) == 512):
                
                self.__block = self.__block + 1
                
                # request next block
                recv_pkt, data = self.__transfer(build_ack_packet(self.__block - 1), response_type = TFTP_DAT)
                
                # concatenate data
                self.__filedata = self.__filedata + data

                # call progress handler if given
                if progress:
                    progress(len(self.__filedata))
            
            #self.__block = self.__block + 1
            
            # send ack and finish
            self.__transfer(build_ack_packet(self.__block), response_type = None)
                
        except socket.timeout:
            raise TftpTimeoutException
            
        except Exception as e:
            raise

        finally:
            # release queue
            TftpClient._pool_q.get()

        return self.__filedata

    def put(self, filename, filedata, progress=None):
        # block on queue
        TftpClient._pool_q.put(None)

        self.__filedata = filedata

        try:
            # initiate connection
            self.__block = 0
        
            # send write request
            recv_pkt, recv_data = self.__transfer(build_cmd_packet(TFTP_WRQ, filename), response_type = TFTP_ACK)
            
            # change host connection, server may have responded from a different port to 
            # handle the transfer
            self.__host = recv_pkt[1]
            
            bytes_sent = 0

            # send data
            while((len(self.__filedata) > 0) or (self.__block == 0)):
                # get a 512 byte slice from the file data
                data = self.__filedata[0:512]
                self.__filedata = self.__filedata[512:]
                
                self.__block = self.__block + 1
                
                recv_pkt, recv_data = self.__transfer(build_data_packet(self.__block, data), response_type = TFTP_ACK)

                bytes_sent += len(data)

                # call progress handler if given
                if progress:
                    progress(bytes_sent)
                
        except socket.timeout:
            raise TftpTimeoutException
        
        except Exception as e:
            raise

        finally:
            # release queue
            TftpClient._pool_q.get()

def read_progress(bytes_read):
    sys.stdout.write("\rBytes received: %6d" % (bytes_read))
    sys.stdout.flush()

def write_progress(bytes_written):
    sys.stdout.write("\rBytes sent: %6d" % (bytes_written))
    sys.stdout.flush()

if __name__ == '__main__':
    
    try:
        host = sys.argv[1]
        cmd = sys.argv[2]
        remotefile = sys.argv[3]
        
    except:
        print "Usage: python tftp.py host command remotefile hostfile"
    
    try:
        hostfile = sys.argv[4]
    except:
        hostfile = None
    
    # if host filename is not given, use the remote file name
    if(hostfile == None):
        hostfile = remotefile

    c = TftpClient(host)
    
    if(cmd == 'get'):
        try:
            start_time = time.time()

            data = c.get(remotefile, progress=read_progress)

            finish_time = time.time()
            elapsed_time = finish_time - start_time
            
            print "\nRead %d bytes in %f seconds (%d bytes/second)" % (len(data), elapsed_time, len(data) / elapsed_time)
            
            # check if stdout requested
            if(hostfile == 'stdout'):
                print data
            
            elif(hostfile != None):
                print "Writing data to file: %s" % (hostfile)
                f = open(hostfile, 'wb')
                f.write(data)
                f.close()
        
        except:
            raise
        
    elif(cmd == 'put'):
        f = open(hostfile, 'rb')
        filedata = f.read()
        f.close()
        
        try:
            start_time = time.time()
            c.put(remotefile, filedata, progress=write_progress)
            finish_time = time.time()
            elapsed_time = finish_time - start_time
            
            print "\nWrote %d bytes in %f seconds (%d bytes/second)" % (len(filedata), elapsed_time, len(filedata) / elapsed_time)
        
        except:
            raise
    