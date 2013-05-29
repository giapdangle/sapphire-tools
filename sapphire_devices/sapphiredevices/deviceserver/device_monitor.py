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
import time
import logging
from datetime import datetime, timedelta

from sapphire.automaton import *
from sapphiredevices.devices import *
from sapphire.core import KVObjectsManager
from notification_server import NOTIFICATION_SERVER_PORT

from pydispatch import dispatcher

_monitors = dict()

# add/remove event handling
# these events come from netscan, which uses the dispatcher
def found_device(device):
    if device.device_id not in _monitors:
        logging.info("Adding device: %s" % (device.device_id))

        _monitors[device.device_id] = _DeviceMonitor(device)

dispatcher.connect(found_device, signal=SIGNAL_FOUND_DEVICE)



class _DeviceMonitor(threading.Thread):
    def __init__(self, device=None):
        super(_DeviceMonitor, self).__init__()
        
        self.device = device
        
        self.running = True

        self.start()
    
    def set_server(self):
        self.device.set_kv_server(port=NOTIFICATION_SERVER_PORT)

    def scan(self):
        self.device.scan()
        self.device.getAllKV()

    def run(self):
        logging.info("DeviceMonitor:%s running" % (self.device.device_id))

        while self.running:
            try:
                retry_timeout = 60

                self.set_server()

                self.scan()

                self.device._last_notification_timestamp = datetime.utcnow()
                self.device.notify()

                # device is online
                logging.info("Device: %s online" % (self.device.device_id))

                # watchdog
                while self.device.device_status == "online":
                    time.sleep(1.0)

                    if not self.running:
                        break

                    # check last notification time
                    if (datetime.utcnow() - self.device._last_notification_timestamp) > timedelta(minutes=2):
                        logging.info("Device: %s watchdog timeout" % (self.device.device_id))

                        # clear retry timeout so we'll try immediately
                        retry_timeout = 0

                        break

                self.device.device_status = "offline"
                logging.info("Device: %s offline" % (self.device.device_id))

            except DeviceUnreachableException:
                logging.info("Device: %s unreachable" % (self.device.device_id))
                pass

            except Exception as e:
                raise
                #logging.error("DeviceMonitor: %s raised exception: %s: %s" % (self.device.device_id, type(e), e))

            # wait up to retry_timeout seconds before retrying device
            for i in xrange(retry_timeout):
                time.sleep(1.0)

                # check status
                if self.device.device_status == "online":
                    break

                if not self.running:
                    break
            

        logging.info("DeviceMonitor:%d stopped" % (self.device.device_id))

    def stop(self):
        logging.info("DeviceMonitor:%d shutting down" % (self.device.short_addr))
        self.running = False


def stop():
    for monitor in _monitors.itervalues():
        monitor.stop()






