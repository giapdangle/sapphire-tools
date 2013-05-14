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


import gevent
import gevent.monkey
gevent.monkey.patch_all()

import logging
import socket
import json

from sapphire.core.version import VERSION
from sapphire.server import settings

DISCOVER_SERVER_PORT    = 25004


class ServerNotFoundException(Exception):
    pass


class DiscoveryServer(gevent.Greenlet):
    def __init__(self):
        super(DiscoveryServer, self).__init__()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', DISCOVER_SERVER_PORT))
        
        self.start()
    
    def _run(self):
        logging.info("DiscoveryServer listening on: %d" % (self.sock.getsockname()[1]))

        while True:
            # wait for messages
            msg, host = self.sock.recvfrom(4096)
            
            if msg == "server?":
                # send response
                response = {"server": "SapphireServer",
                            "version": VERSION,
                            "port": settings.API_SERVER_PORT}

                self.sock.sendto(json.dumps(response), host)
            


class DiscoveryClient(object):
    def __init__(self):
        super(DiscoveryClient, self).__init__()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.sock.settimeout(1.0)
    
    def discover(self):
        self.tries = 4

        while self.tries > 0:

            try:
                self.sock.sendto("server?", ("255.255.255.255", DISCOVER_SERVER_PORT))
                
                msg, host = self.sock.recvfrom(4096)

                return json.loads(msg), host[0]
            
            except socket.timeout:
                pass

            self.tries -= 1

        raise ServerNotFoundException

