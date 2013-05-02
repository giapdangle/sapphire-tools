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

from sapphire.core import KVObjectsManager
from device import DeviceUnreachableException
import gateway

from pydispatch import dispatcher

SIGNAL_FOUND_DEVICE = "signal_found_device"

DEFAULT_SCAN_INTERVAL           = 8.0


def scan():
    gateways = gateway.getGateways()

    devices = list()

    for g in gateways:
        devices.extend(g.getDevices())        

    devices.extend(gateways)

    all_devices = KVObjectsManager.query(all=True)

    for device in devices:
        # check if device has been published
        if len(KVObjectsManager.query(device_id=device.device_id)) == 0:
            device.publish()   
            
        dispatcher.send(signal=SIGNAL_FOUND_DEVICE, device=device)

    return devices


class NetworkScanner(gevent.Greenlet):
    def __init__(self, scan_interval=DEFAULT_SCAN_INTERVAL):
        super(NetworkScanner, self).__init__()
        
        self.scan_interval = scan_interval
        
        self.running = True

        self.start()

    def _run(self):
        logging.info("NetworkScanner started")

        while self.running:
            try:
                try:
                    scan()
                
                except DeviceUnreachableException as e:
                    logging.info(e)
                
            except gevent.GreenletExit:
                pass

            gevent.sleep(self.scan_interval)
                
        logging.info("NetworkScanner stopped")

    def stop(self):
        logging.info("NetworkScanner shutting down")
        self.running = False
        self.kill()

