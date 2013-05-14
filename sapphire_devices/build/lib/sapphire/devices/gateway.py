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

from messages import *
from protocols import *
import device
from device import Device, DeviceUnreachableException
import socket
from sapphiredata import *
import udpx
import datetime
import logging
import time

from sapphire.core import KVObjectsManager


FWID = "e966b682-ce7c-4c80-8373-2f1ee344e39d"

NTP_EPOCH = datetime.datetime(1900, 1, 1)
NETWORK_SYNC_VALID_INTERVAL = datetime.timedelta(minutes=5)

GATEWAY_SERVICES_PORT           = 25002
GATEWAY_SERVICES_UDPX_PORT      = 25003

GATEWAY_NET_TIME_FLAGS_WCOM_NETWORK_SYNC     = 0x01
GATEWAY_NET_TIME_FLAGS_NTP_SYNC              = 0x02
GATEWAY_NET_TIME_FLAGS_VALID                 = 0x04



def getGateways(timeout=1.0):
    # create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    gateways = list()
 
    # send discovery message
    msg = GatewayServicesProtocol().PollGateway(short_addr = 0)
    sock.sendto(msg.pack(), ('255.255.255.255', GATEWAY_SERVICES_PORT))
    
    # mark start time
    start_time = time.time()

    while time.time() < ( start_time + timeout ):
        try:
            # receive data
            data, host = sock.recvfrom(4096)
            
            try:
                msg = GatewayServicesProtocol().unpack(data)
                
                # check if gateway is already in the object manager
                obj_query = KVObjectsManager.query(device_id=msg.device_id)

                if len(obj_query) > 0:
                    obj = obj_query[0]

                else:
                    obj = Gateway(host=host[0], short_addr=msg.short_addr, device_id=msg.device_id)

                gateways.append(obj)
            
            except:
                raise

        except socket.timeout:
            pass
    
    sock.close()

    return gateways

class TimeNotSynchronizedException(Exception):
    pass

class Gateway(Device):
   
    def __init__(self, **kwargs):
        super(Gateway, self).__init__(**kwargs)
        
        self._wcom_network_time_base = None
        self._ntp_time_base = None

        # gateway is its own gateway
        self._gateway = self

    def get_device_db(self):
        data = self.getFile("devicedb")

        db = DeviceDBArray()
        db.unpack(data)

        return db

    def getDevices(self):
        try:
            data = self.getFile("devicedb")
         
        except Exception as e:
            print e
            return list()

        devicedb = DeviceDBArray().unpack(data)
        
        devices = list()

        for d in devicedb:
            new_dev = device.createDevice(host=d.ip,
                                          device_id=d.device_id,
                                          short_addr=d.short_addr,
                                          gateway=self)
            
            devices.append(new_dev)

        return devices
    
    def getNetworkTime(self):
        cmd = GatewayServicesProtocol().GetNetworkTime()
        
        sock = udpx.ClientSocket()
        
        try:
            sock.sendto(cmd.pack(), (self.host, GATEWAY_SERVICES_UDPX_PORT))
            
            data, host = sock.recvfrom()
            msg = GatewayServicesProtocol().unpack(data)
            
            # convert raw NTP timestamp to seconds
            ntp_fraction = float(msg.ntp_time_fractional) / float(2**32)
            ntp_seconds = float(msg.ntp_time_seconds) + ntp_fraction
            
            # convert NTP seconds to datetime object
            ntp_now = datetime.timedelta(seconds=ntp_seconds) + NTP_EPOCH
            
            # check flags
            if msg.flags & GATEWAY_NET_TIME_FLAGS_VALID:
                # assign wcom network base
                self._wcom_network_time_base = msg.wcom_network_time
                
                # assign ntp base
                self._ntp_time_base = ntp_now
                
                logging.debug("Time resync network base:%s ntp base:%s" % (self._wcom_network_time_base, self._ntp_time_base))

            # not synchonized
            else:
                self._wcom_network_time_base = None
                self._ntp_time_base = None

        except socket.timeout:
            raise DeviceUnreachableException

        except socket.error:
            raise DeviceUnreachableException
        
        finally:
            sock.close()
        
        # return both timestamps
        return self._wcom_network_time_base, self._ntp_time_base
    
    def convertNetworkTime(self, network_time):
        try:
            # check if synchronized
            if self._ntp_time_base == None or self._wcom_network_time_base == None:
                # resync with gateway
                self.getNetworkTime()

            # get current time
            now = datetime.datetime.utcnow()
            
            # check if synchronization is out of date
            if now > self._ntp_time_base + NETWORK_SYNC_VALID_INTERVAL:
                # resync with gateway
                self.getNetworkTime()
            
            # get elapsed microseconds of network time
            elapsed_network_time = network_time - self._wcom_network_time_base

            # check if elapsed network time is valid
            if abs(elapsed_network_time) >= ((2**32) / 2):
                # resync with gateway
                self.getNetworkTime()
                elapsed_network_time = network_time - self._wcom_network_time_base

            # convert net time from microseconds to seconds
            elapsed_network_time = float(elapsed_network_time) / 1000000.0
            
            # add elapsed time to ntp base and return
            return self._ntp_time_base + datetime.timedelta(seconds=elapsed_network_time)
        
        except DeviceUnreachableException:
            raise TimeNotSynchronizedException

    def get_bridge_info(self):
        data = self.getFile("bridge")

        info = BridgeArray()
        info.unpack(data)

        return info

    def get_arp_info(self):
        data = self.getFile("arp_cache")

        info = ArpArray()
        info.unpack(data)

        return info

    def cli_bridgeinfo(self, line):
        info = self.get_bridge_info()

        s = "\nShort  IP                Lease    TimeLeft   Flags\n"

        for i in info:
            if i.short_addr == 0:
                continue

            flags = ''

            if i.flags & 1:
                flags += 'M'
            else:
                flags += '-'

            if i.flags & 2:
                flags += 'R'
            else:
                flags += '-'
            
            if i.flags & 4:
                flags += 'V'
            else:
                flags += '-'

            s += "%5d %15s %8d %8d %8s\n" % \
                (i.short_addr,
                 i.ip,
                 i.lease,
                 i.time_left,
                 flags)

        return s

    def cli_arpinfo(self, line):
        info = self.get_arp_info()

        s = "\nMAC               IP              Age\n"

        for i in info:
            if i.eth_mac == "0:0:0:0:0:0":
                continue

            s += "%17s %15s %3d\n" % \
                (i.eth_mac,
                 i.ip,
                 i.age)

        return s

    def cli_devicedbinfo(self, line):
        info = self.get_device_db()

        s = "\nID                      Short IP\n"

        for i in info:
            if i.short == 0:
                continue

            s += "%20d %5d %15s\n" % \
                (i.device_id,
                 i.short_addr,
                 i.ip)

        return s



