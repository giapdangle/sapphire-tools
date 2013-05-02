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

import logging
import socket

from sapphire.core import KVObjectsManager
from sapphire.devices.device import UnrecognizedKeyException

from sapphire.devices.udpx import ServerSocket
from sapphire.devices.sapphiredata import NotificationField



NOTIFICATION_SERVER_PORT = 59999

class NotificationServer(gevent.Greenlet):
    def __init__(self):
        super(NotificationServer, self).__init__()
                
        self.sock = ServerSocket()
        self.sock.bind(('0.0.0.0', NOTIFICATION_SERVER_PORT))
        self.sock.settimeout(1.0)
        
        self.running = True

        self.start()
    
    def _run(self):
        logging.info("NotificationServer listening on: %s:%d" % \
                    (self.sock.getsockname()[0], self.sock.getsockname()[1]))

        while self.running:
            try:
                # wait for messages
                msg, host = self.sock.recvfrom()
                
                # send empty response to initiate ack packet
                self.sock.sendto()
                
                # query for device
                try:
                    # unpack message
                    msg = NotificationField().unpack(msg)
                    
                    # query for device
                    device = KVObjectsManager.query(device_id=msg.device_id)[0]
                    
                    # send notification msg to device
                    device.receive_notification(msg)

                except IndexError:
                    logging.debug("(notifications) Device: %d not found" % (msg.device_id))

                except UnrecognizedKeyException as e:
                    logging.debug(e)

                except Exception as e:
                    logging.error("Exception: %s Host: %s" % (str(e), host[0]))                                        

            except socket.timeout:
                pass
        
        logging.info("NoticationServer stopped")
        
    def stop(self):
        logging.info("NoticationServer shutting down")
        self.running = False

