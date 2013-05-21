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

import threading
import logging
import socket
import struct

from sapphire.core import KVObjectsManager
from sapphiredevices.devices.device import UnrecognizedKeyException

from sapphiredevices.devices.udpx import ServerSocket
from sapphiredevices.devices.protocols import *
from sapphiredevices.devices.fields import *


NOTIFICATION_SERVER_PORT = 59999


class NotificationProtocol(Protocol):

    class Notification0(Payload):
        msg_type = 1
        fields = [Uint8Field(name="flags"),
                  Uint64Field(name="device_id"),
                  NTPTimestampField(name="timestamp"),
                  Uint8Field(name="group"),
                  Uint8Field(name="id"),
                  Uint8Field(name="data_type"),
                  RawBinField(name="data")]
        
    msg_type_format = Uint8Field()


class NotificationServer(threading.Thread):
    def __init__(self):
        super(NotificationServer, self).__init__()
                
        self.sock = ServerSocket()
        self.sock.bind(('0.0.0.0', NOTIFICATION_SERVER_PORT))
        self.sock.settimeout(1.0)
        
        self.running = True

        self.start()
    
    def run(self):
        logging.info("NotificationServer listening on: %s:%d" % \
                    (self.sock.getsockname()[0], self.sock.getsockname()[1]))

        while self.running:
            try:
                # wait for messages
                data, host = self.sock.recvfrom()
                
                # send empty response to initiate ack packet
                self.sock.sendto()

                msg = NotificationProtocol().unpack(data)

                if isinstance(msg, NotificationProtocol.Notification0):
                    
                    # query for device
                    try:
                        msg.data = sapphiretypes.getType(msg.data_type).unpack(msg.data)

                        # query for device
                        device = KVObjectsManager.query(device_id=msg.device_id)[0]
                        
                        # send notification msg to device
                        device.receive_notification(msg)

                    except IndexError:
                        logging.info("(notifications) Device: %d not found" % (msg.device_id))

                    except UnrecognizedKeyException as e:
                        logging.info("UnrecognizedKeyException: %s" % (str(e)))

                    except Exception as e:
                        logging.error("Exception: %s Host: %s" % (str(e), host[0]))                                        

                else:
                    logging.warn("Unknown message: %d from: %s" % (msg_type, str(host)))                    


            except socket.timeout:
                pass
        
        logging.info("NoticationServer stopped")
        
    def stop(self):
        logging.info("NoticationServer shutting down")
        self.running = False

