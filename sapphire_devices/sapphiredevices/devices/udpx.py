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

"""UDPX socket module.

UDPX is a thin protocol on top of UDP that provides acknowledged datagram 
delivery with an automatic repeat request mechanism in the client.


"""


import socket
import random
import time

import bitstring



class Packet(object):
    
    VERSION = 0
    HEADER_FORMAT = 'uint:2, uint:1, uint:1, uint:1, uint:3, uint:8'

    def __init__(self, 
                 server=False,
                 ack_request=True,
                 ack=False, 
                 id=None, 
                 data=''):

        self.__version  = Packet.VERSION
        
        self.__server = 0
        self.__ack_request = 0
        self.__ack = 0

        if server:
            self.__server = 1
        
        if ack_request:
            self.__ack_request = 1

        if ack:
            self.__ack = 1

        if id is None:
            id = random.randint(0,255)

        self.__id = id

        self.__payload = data

        self.time = None
    
    def __str__(self):

        s = "Ver:%d | Svr:%d | Arq:%d | Ack:%d | ID:%3d | PayloadLength:%3d" % \
            (self.__version, 
             self.__server, 
             self.__ack_request, 
             self.__ack, 
             self.__id,
             len(self.__payload))
        
        if self.time:
            s += " | Time(ms):%5d" % (self.time * 1000)

        return s

    def pack(self):
        header = bitstring.pack(Packet.HEADER_FORMAT, 
                                self.__version, 
                                self.__server, 
                                self.__ack_request, 
                                self.__ack, 
                                0,
                                self.__id)
        
        return header.bytes + self.__payload

    def unpack(self, data):
        s = bitstring.BitStream(bytes=data[0:2])
        header = s.unpack(Packet.HEADER_FORMAT)
        
        self.__version      = header[0]
        self.__server       = header[1]
        self.__ack_request  = header[2]
        self.__ack          = header[3]
        # header[4] is reserved bits
        self.__id           = header[5]
        
        self.__payload = data[2:]
        
        return self
    
    def get_version(self):
        return self.__version

    def get_server(self):
        return self.__server != 0

    def get_ack_request(self):
        return self.__ack_request != 0
    
    def get_ack(self):
        return self.__ack != 0

    def get_id(self):
        return self.__id

    def get_payload(self):
        return self.__payload

    def set_payload(self, value):
        self.__payload = value

    version = property(get_version)
    server = property(get_server)
    ack_request = property(get_ack_request)
    ack = property(get_ack)
    id = property(get_id)
    payload = property(get_payload, set_payload)


class ClientSocket(object):
    
    DEFAULT_TRIES = 5
    INITIAL_TIMEOUT = 1.0
    TIMEOUT_INCREMENT = 0.1

    def __init__(self, addr_family=None, sock_type=None):
        self.__sock = socket.socket(socket.AF_INET,
                                    socket.SOCK_DGRAM)
        
        self.__tries = ClientSocket.DEFAULT_TRIES
        self.__initial_timeout = ClientSocket.INITIAL_TIMEOUT
        
        self.__received_data = None
        self.__received_addr = None

    def bind(self, address):
        self.__sock.bind(address)
    
    def settimeout(self, seconds):
        self.__initial_timeout = seconds

    def sendto(self, data, address):

        self.__sock.connect(address)

        # build data packet
        packet = Packet(data=data)
        
        # set initial timeout
        timeout = self.__initial_timeout
        
        start = time.time()

        # retry loop
        for i in xrange(self.__tries):
            # send packet
            try:
                self.__sock.send(packet.pack())
            
            except socket.error:
                # we'll get this if the host is unreachable,
                # or if some other error occurred
                raise

            # set timeout
            self.__sock.settimeout(timeout)
            
            # wait for timeout or received data
            try:
                ack, host = self.__sock.recvfrom(4096)

                # parse ack
                ack = Packet().unpack(ack)
                
                # check packet for errors
                if ack.version != ack.VERSION:
                    raise InvalidPacketException(packet)

                elif not ack.server:
                    raise InvalidPacketException(packet)

                elif ack.ack_request:
                    raise InvalidPacketException(packet)

                elif not ack.ack:
                    raise InvalidPacketException(packet)
                
                elif ack.id != packet.id:
                    continue

                ack.time = time.time() - start

                #print host, ack

                # set data and server host buffers
                self.__received_data = ack.payload
                self.__received_addr = host

                return

            except socket.timeout:
                
                # increase timeout
                timeout = timeout + ClientSocket.TIMEOUT_INCREMENT
            
            except socket.error:
                raise

        # we didn't receive an ack, raise the timeout exception
        raise socket.timeout
    
    def recvfrom(self, bufsize=4096):
        
        # check if there is already data waiting from a transaction
        if self.__received_data:
            data = self.__received_data
            addr = self.__received_addr
            
            self.__received_data = None
            self.__received_addr = None

            return data, addr
        
        else:
            raise InvalidOperationException("recvfrom() but no ack from server")
    
    def close(self):
        self.__sock.close()


class ServerSocket(object):
    
    def __init__(self, addr_family=None, sock_type=None):
        self.__sock = socket.socket(socket.AF_INET,
                                    socket.SOCK_DGRAM)
        
        self.__ack_host = None
        self.__ack_packet = None
    
    def bind(self, address):
        self.__sock.bind(address)
    
    def settimeout(self, seconds):
        self.__sock.settimeout(seconds)
    
    def getsockname(self):
        return self.__sock.getsockname()

    def sendto(self, data="", address=None):
        # check if there is an ack packet to send
        if self.__ack_packet:
            
            # attach data to packet
            self.__ack_packet.payload = data
            
            # send packet
            self.__sock.sendto(self.__ack_packet.pack(), self.__ack_host)   
            
            # delete ack packet and host
            self.__ack_host = None
            self.__ack_packet = None
        
        else:
            raise InvalidOperationException("sendto() but no message from client")
        
    def recvfrom(self, bufsize=4096):
        # receive packet and host address
        try:
            data, host = self.__sock.recvfrom(bufsize)
            
            # parse packet
            packet = Packet().unpack(data)
            
            # check packet for errors
            if packet.version != packet.VERSION:
                raise InvalidPacketException(packet)

            elif packet.server:
                raise InvalidPacketException(packet)

            elif packet.ack:
                raise InvalidPacketException(packet)
                
            # build and save ack packet
            self.__ack_packet = Packet(server=True, 
                                       ack_request=False,
                                       ack=True,
                                       id=packet.id,
                                       data=packet.payload)

            # save client host
            self.__ack_host = host

            return packet.payload, host

        except socket.timeout:
            raise socket.timeout


class EchoServer(object):
    def __init__(self, address):
        self.__sock = ServerSocket()
        self.__sock.bind(address)
    
    def serve_forever(self):
        while True:
            data, host = self.__sock.recvfrom()
            self.__sock.sendto(data)

class InvalidOperationException(Exception):
    def __init__(self, value=None):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class InvalidPacketException(Exception):
    def __init__(self, value=None):
        self.value = value
    
    def __str__(self):
        return repr(self.value)


if __name__ == '__main__':
    
    c = ClientSocket()
    

    c.sendto("Jeremy", ("192.168.2.233", 1234))

    print c.recvfrom()







