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
from datetime import datetime, timedelta

from sapphire.automaton import *
from sapphire.devices import *
from sapphire.core import KVObjectsManager
from notification_server import NOTIFICATION_SERVER_PORT

from pydispatch import dispatcher

_monitors = dict()

# add/remove event handling
# these events come from netscan, which uses the dispatcher
def add_device(device):
    if device.device_id not in _monitors:
        logging.info("Adding device: %s" % (device.device_id))

        _monitors[device.device_id] = _DeviceMonitor(device)

def remove_device(device):
    logging.info("Removing device: %s" % (device.device_id))    

def found_device(device):
    pass
    # check if device has been published
    #if len(KVObjectsManager.query(device_id=device.device_id)) == 0:
        # device.publish()        

dispatcher.connect(add_device, signal=SIGNAL_ADD_DEVICE)
dispatcher.connect(remove_device, signal=SIGNAL_REMOVE_DEVICE)
dispatcher.connect(found_device, signal=SIGNAL_FOUND_DEVICE)


# Device attach event handling
# These come as notifications from the gateway
class DeviceAttachTrigger(Trigger):
    def condition(self, event):
        return event.key == "device_attach"

class DeviceAttachAction(Action):
    def action(self, event):
        # query for device by short address
        device = Universe().query(short_addr=event.device_attach)

        # notify device monitor
        _monitors[device.device_id].attach()

Macro(triggers=DeviceAttachTrigger(), actions=DeviceAttachAction())


class _DeviceMonitor(gevent.Greenlet):
    def __init__(self, device=None):
        super(_DeviceMonitor, self).__init__()
        
        self.device = device
        self.attach_event = gevent.event.Event()
        
        self.running = True

        self.start()
    
    def subscribe_notifications(self):    
        self.device.subscribeKV("kv_group_all", port=NOTIFICATION_SERVER_PORT)
    
    def unsubscribe_notifications(self):
        self.device.unsubscribeKV("kv_group_all", port=NOTIFICATION_SERVER_PORT)

    def attach(self):
        logging.info("Attach: %s" % (self.device.device_id))
        self.attach_event.set()

    def scan(self):
        self.device.scan()
        self.subscribe_notifications()
        self.device.getAllKV()

    def _run(self):
        logging.info("DeviceMonitor:%s running" % (self.device.device_id))

        try:

            while self.running:
                try:
                    self.scan()

                    # device is online
                    logging.info("Device: %s online" % (self.device.device_id))

                    # watchdog
                    while self.device.device_status == "online":
                        gevent.sleep(1.0)

                        # check heartbeat
                        #if (datetime.utcnow() - self.device.updated_at) > timedelta(minutes=2):
                        #    logging.info("Device: %s watchdog timeout" % (self.device.device_id))            

                        #    self.device.device_status = "offline"
                        #    logging.info("Device: %s offline" % (self.device.device_id))

                            # set the attach event now so we'll attempt to scan immediately
                        #    self.attach_event.set()

                except DeviceUnreachableException:
                    #logging.info("Device: %s unreachable" % (self.device.device_id))
                    pass

                except Exception as e:
                    logging.error("DeviceMonitor: %s raised exception: %s: %s" % (self.device.device_id, type(e), e))

                # wait for attach, or time delay to expire
                self.attach_event.wait(60.0)
                self.attach_event.clear()
                
                #logging.info("Retrying device: %s" % (self.device.device_id))                

        except gevent.GreenletExit:
            pass

        self.unsubscribe_notifications()

        logging.info("DeviceMonitor:%d stopped" % (self.device.device_id))

    def stop(self):
        logging.info("DeviceMonitor:%d shutting down" % (self.device.short_addr))
        self.running = False
        self.kill()


def stop():
    for monitor in _monitors.itervalues():
        monitor.stop()






