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

from sapphire.core import KVObjectsManager
from device import DeviceUnreachableException
import gateway

from pydispatch import dispatcher

SIGNAL_FOUND_DEVICE = "signal_found_device"

DEFAULT_SCAN_INTERVAL           = 8.0


def scan():
    gateways = gateway.getGateways()

    devices = list()

    devices.extend(gateways)

    try:
        for g in gateways:
            devices.extend(g.getDevices())        

    except:
        pass

    for device in devices:
        # check if device has been published
        if len(KVObjectsManager.query(device_id=device.device_id)) == 0:
            device.publish()   
            
        dispatcher.send(signal=SIGNAL_FOUND_DEVICE, device=device)

    return devices


class NetworkScanner(threading.Thread):
    def __init__(self, scan_interval=DEFAULT_SCAN_INTERVAL):
        super(NetworkScanner, self).__init__()
        
        self.scan_interval = scan_interval
        
        self._stop_event = threading.Event()

        self.start()

    def run(self):
        logging.info("NetworkScanner started")

        while not self._stop_event.is_set():
            try:
                scan()
            
            except DeviceUnreachableException as e:
                logging.info(e)
                
            self._stop_event.wait(self.scan_interval)
                
        logging.info("NetworkScanner stopped")

    def stop(self):
        logging.info("NetworkScanner shutting down")
        self._stop_event.set()

