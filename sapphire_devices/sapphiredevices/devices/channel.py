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

import udpx
import serial
import crcmod
import sapphiredata
import socket
import struct
from Queue import Queue

SERIAL_SOF = 0xfd
SERIAL_INVERTED_SOF = ~SERIAL_SOF & 0xff
SERIAL_ACK = 0xa1
SERIAL_NAK = 0x1b

class ChannelException(Exception):
    def __init__(self, value = None):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class ChannelTimeoutException(ChannelException):
    pass

class ChannelErrorException(ChannelException):
    pass

class ChannelUnreachableException(ChannelException):
    pass

class Channel(object):
    def __init__(self, host, medium='none'):
        self.host = host   
        self.medium = medium
    
    def __del__(self):
        self.close()

    def open(self):
        raise NotImplementedError
    
    def close(self):
        raise NotImplementedError
    
    def read(self):
        raise NotImplementedError

    def write(self, data):
        raise NotImplementedError

    def settimeout(self, timeout=None):
        raise NotImplementedError

class NullChannel(Channel):
    def __init__(self, host):
        super(NullChannel, self).__init__(host, 'null')

    def open(self):
        pass

    def close(self):
        pass
    
    def read(self):
        pass

    def write(self, data):
        pass

    def settimeout(self, timeout=None):
        pass


class UdpxChannel(Channel):

    def __init__(self, host):
        
        super(UdpxChannel, self).__init__(host, 'udpx_client_socket')
        
        self.host = host
        self.sock = udpx.ClientSocket()
    
    def open(self):
        pass

    def close(self):
        self.sock.close()
    
    def read(self):
        try:
            data, host = self.sock.recvfrom()
        
            # check host address
            if host[0] != self.host[0]:
                raise CmdInvalidHostException(self.host)
            
            else:
                # set host so we have the host port
                self.host = host

        except socket.timeout:
            raise ChannelTimeoutException
        
        except socket.error:
            raise ChannelUnreachableException

        return data
    
    def write(self, data):
        try:
            self.sock.sendto(data, self.host)
        
        except socket.timeout:
            raise ChannelTimeoutException(self.host)

        except socket.error:
            raise ChannelUnreachableException

    def settimeout(self, timeout):
        self.sock.settimeout(timeout)

class SerialChannel(Channel):
    
    def __init__(self, host):
        
        super(SerialChannel, self).__init__(host, 'serial')
        
        #self.port = serial.Serial(host, baudrate=19200)
        self.port = serial.Serial(host, baudrate=115200)
        #self.port = serial.Serial(host, baudrate=250000)
        #self.port = serial.Serial(host, baudrate=500000)
        self.host = self.port.port

        # set up crc function
        self.crc_func = crcmod.predefined.mkCrcFun('crc-aug-ccitt')
        
        self.settimeout(timeout=1.0)

    def open(self):
        pass
    
    def close(self):
        self.port.close()
    
    def read(self):
        try:

            tries = 4
        
            while tries > 0:
                tries -= 1

                header = sapphiredata.SerialFrameHeader()

                # wait for header data
                header_data = self.port.read(header.size())
                
                # unpack header
                header.unpack(header_data)
                
                # check header
                if ( ( header.len != ( ~header.inverted_len & 0xffff ) ) ):
                    continue

                # receive data
                data = self.port.read(header.len)
                 
                # receive CRC
                crc = struct.unpack('>H', self.port.read(2))[0]
                
                # check crc
                if self.crc_func(data) == crc:
                    return data
                
                raise ChannelErrorException()

            if tries == 0:
                raise ChannelErrorException()

        except serial.SerialTimeoutException:
            raise ChannelTimeoutException
        
        except struct.error as e:
            raise ChannelErrorException
        

    def write(self, data):
        
        tries = 4
    
        while tries > 0:

            tries -= 1

            self.port.write(struct.pack('B', SERIAL_SOF))

            # wait for ACK
            try:
                response = struct.unpack('B', self.port.read(1))[0]
            
            except:
                continue

            if response != SERIAL_ACK:
                continue
            
            # set up header
            header = sapphiredata.SerialFrameHeader(len=len(data),
                                                    inverted_len=(~len(data) & 0xffff))
            
            self.port.write(header.pack())

            # wait for ACK
            try:
                response = struct.unpack('B', self.port.read(1))[0]
            
            except:
                continue

            if response != SERIAL_ACK:
                continue

            # send data
            self.port.write(data)

            # compute crc
            crc = self.crc_func(data)
            
            # send CRC
            self.port.write(struct.pack('>H', crc)) # note the big endian!
            
            # wait for ACK
            response = struct.unpack('B', self.port.read(1))[0]
            
            if response == SERIAL_ACK:
                return
        
        if tries == 0:
            raise ChannelErrorException()

    def settimeout(self, timeout):
        self.port.timeout = timeout


class UdpxClientPoolChannel(Channel):
    
    POOL_SIZE = 4

    __q = Queue(maxsize=POOL_SIZE)

    def __init__(self, host):
        super(UdpxClientPoolChannel, self).__init__(host, 'pool')
        
        self.timeout = None
        
        self.q = self.__q
        
    def open(self):
        pass

    def close(self):
        pass
    
    def getSock(self):
        # block on queue
        self.q.put(None)
        
        # create socket
        sock = udpx.ClientSocket()
    
        # set timeout
        if self.timeout != None:
            sock.settimeout(self.timeout)
        
        return sock
        
    def returnSock(self, sock):
        # remove dummy Q item
        self.q.get()

    def read(self):
        data = self.read_data
        self.read_data = None

        return data

    def write(self, data):
        sock = self.getSock()       
        
        try:
            #print "Sent %4d > %s" % (len(data), self.host)
            sock.sendto(data, self.host)
            
            self.read_data, host = sock.recvfrom()
            #print "Recv %4d > %s" % (len(self.read_data), host)
        
            # check host address
            if host[0] != self.host[0]:
                raise CmdInvalidHostException(self.host)
            
            else:
                # set host so we have the host port
                self.host = host
               
        except socket.timeout:
            raise ChannelTimeoutException(self.host)

        except socket.error as e:
            raise ChannelUnreachableException
        
        finally:
            self.returnSock(sock)


    def settimeout(self, timeout=None):
        self.timeout = timeout


def createChannel(host, port=None):
    try:
        socket.inet_aton(host)
        return UdpxClientPoolChannel(host=(host, port))
        #return UdpxChannel(host=(host, port))
    except:
        return SerialChannel(host)
