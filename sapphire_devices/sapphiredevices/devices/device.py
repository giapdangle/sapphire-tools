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

"""Device
"""

from sapphire.core import KVObject

from protocols import *
from fields import *

import sapphiredata
import sapphiretypes
import firmware
import channel

import time
import sys
import datetime
import types
from datetime import datetime, timedelta

from pprint import pprint
import hashlib
import binascii
from UserDict import DictMixin

from sapphire.core.store import Store


NTP_EPOCH = datetime(1900, 1, 1)


FILE_TRANSFER_LEN   = 512
MAX_KV_DATA_LEN     = 548

# Key value groups
KV_GROUP_NULL               = 0
KV_GROUP_NULL1              = 254
KV_GROUP_SYS_CFG            = 1
KV_GROUP_SYS_INFO           = 2
KV_GROUP_SYS_STATS          = 3
KV_GROUP_APP_BASE           = 32

KV_GROUP_ALL                = 255


kv_groups = {
    "kv_group_null":        KV_GROUP_NULL,
    "kv_group_null_1":      KV_GROUP_NULL1,
    "kv_group_sys_cfg":     KV_GROUP_SYS_CFG,
    "kv_group_sys_info":    KV_GROUP_SYS_INFO,
    "kv_group_sys_stats":   KV_GROUP_SYS_STATS,
    "kv_group_all":         KV_GROUP_ALL,
}

KV_ID_ALL                   = 255

# Key value flags
KV_FLAGS_READ_ONLY          = 0x0001
KV_FLAGS_PERSIST            = 0x0004

# warning flags
SYS_WARN_MEM_FULL           = 0x0001
SYS_WARN_NETMSG_FULL        = 0x0002
SYS_WARN_FLASHFS_FAIL       = 0x0004
SYS_WARN_FLASHFS_HARD_ERROR = 0x0008
SYS_WARN_CONFIG_FULL        = 0x0010
SYS_WARN_CONFIG_WRITE_FAIL  = 0x0020

def decode_warnings(flags):
    warnings = list()

    if flags & SYS_WARN_MEM_FULL:
        warnings.append("mem_full")

    if flags & SYS_WARN_NETMSG_FULL:
        warnings.append("netmsg_full")
    
    if flags & SYS_WARN_FLASHFS_FAIL:
        warnings.append("flashfs_fail")

    if flags & SYS_WARN_FLASHFS_HARD_ERROR:
        warnings.append("flashfs_hard_error")

    if flags & SYS_WARN_CONFIG_FULL:
        warnings.append("config_full")

    if flags & SYS_WARN_CONFIG_WRITE_FAIL:
        warnings.append("config_write_fail")

    return warnings


CLI_PREFIX = 'cli_'

DeviceStatus = set(['unknown', 'offline', 'online', 'reboot'])


class DeviceUnreachableException(Exception):
    pass

class DuplicateKeyNameException(Exception):
    pass

class DuplicateKeyIDException(Exception):
    pass

class ReadOnlyKeyException(Exception):
    def __init__(self, key=None):
        self.key = key

class UnrecognizedKeyException(Exception):
    pass


class KVKey(object):
    def __init__(self, 
                 device=None, 
                 group=None, 
                 id=None, 
                 flags=None, 
                 type=None, 
                 value=None, 
                 key=None):

        self._device = device

        self.group = group
        self.id = id
        self.type = type
        self._value = value
        self.key = key

        # decode flags to strings
        self.flags = list()

        if flags & KV_FLAGS_READ_ONLY:
            self.flags.append("read_only")

        if flags & KV_FLAGS_PERSIST:
            self.flags.append("persist")

    def __str__(self):
        flags = ''

        if "persist" in self.flags:
            flags += 'P'
        else:
            flags += ' '

        if "read_only" in self.flags:
            flags += 'R'
        else:
            flags += ' '

        s = "%32s %3d %3d %6s %s" % (self.key, self.group, self.id, flags, str(self._value))
        return s

    def get_value(self):
        # if value hasn't been initialized, we load from the device
        if self._value == None:
            # internal meta data is auto-updated, so we can toss the return value
            self._device.getKey(self.key)

        return self._value

    def set_value(self, value):        
        self._value = value
        self._device.setKey(self.key, self._value)

    value = property(get_value, set_value)


class KVMeta(DictMixin):
    def __init__(self):
        self.kv_items = dict()

    def keys(self):
        return self.kv_items.keys()

    def __getitem__(self, key):
        return self.kv_items[key]

    def __setitem__(self, key, value):
        if key in self.kv_items:
            # we already have an item here
            raise DuplicateKeyNameException("DuplicateKeyNameException: %s" % (key))

        self.kv_items[key] = value
        value.key = key
        
    def __delitem__(self, key):
        del self.kv_items[key]

    def check(self):
        # check for duplicate IDs
        for key in self.kv_items:
            l = len([k for k, v in self.kv_items.iteritems() 
                        if v.group == self.kv_items[key].group
                            and v.id == self.kv_items[key].id])
            
            if l > 1:
                raise DuplicateKeyIDException("DuplicateKeyIDException: %s" % (key))
        

import threading
_my_lock = threading.Lock()


class Device(KVObject):
    
    def __init__(self, 
                 host=None, 
                 short_addr=0,
                 device_id=None,
                 command_protocol=DeviceCommandProtocol,
                 response_protocol=DeviceCommandResponseProtocol,
                 comm_channel=None,
                 gateway=None):
        
        super(Device, self).__init__()

        self.host = host
        self.firmware_id = None
        self.firmware_name = ""
        self.os_name = ""
        self.firmware_version = ""
        self.os_version = ""
        self.short_addr = short_addr
        self.device_id = device_id
        self.name = "<anon@%d>" % (short_addr)

        self.device_status = 'offline'
        self._last_notification_timestamp = NTP_EPOCH

        self.collection = "devices"
        self.object_id = str(self.device_id)
        
        self._keys = KVMeta()
        self._firmware_info_hash = None
        
        self._channel = comm_channel
        
        # if no channel is specified, create one
        if self._channel is None:
            self._channel = channel.createChannel(self.host, port=DeviceCommandProtocol.PORT)
        
        self._gateway = gateway

        # assign protocols
        self._protocol = command_protocol()
        self._response_protocol = response_protocol()
        
    def __str__(self):
        return "Device:%16s" % (self.device_id)
    
    # TODO this should move to the console
    def who(self):
        s = "%24s Short:%5d IP:%15s FW:%24s Ver:%8s OS:%8s" % \
            (self.name,
             self.short_addr,
             self.host,
             self.firmware_name,
             self.firmware_version,
             self.os_version)

        return s
    
    def update(self, key, value, timestamp=None):
        super(Device, self).update(key, value, timestamp=timestamp)

        self.setKey(key, value)

    def batch_update(self, updates, timestamp=None):
        self.setKV(**updates)

        if timestamp == None:
            self.updated_at = datetime.utcnow()
        else:
            self.updated_at = timestamp

    def receive_notification(self, msg):
        # verify address
        if msg.device_id != self.device_id:
            return

        # translate the ID and group to a name
        try:
            key = self.translateKey(msg.group, msg.id)

        except UnrecognizedKeyException:
            raise

        # verify data type
        if msg.data_type != self._keys[key].type:
            return
            
        # convert NTP timestamp to datetime object
        ntp_seconds = msg.timestamp.seconds + (msg.timestamp.fraction / (2^32))
        timestamp = timedelta(seconds=ntp_seconds) + NTP_EPOCH

        # set value
        value = msg.data.value
        self._keys[key]._value = value
        self.set(key, value, timestamp=timestamp)

        # set last received notification timestamp
        self._last_notification_timestamp = datetime.utcnow()
        
        # check if boot_mode
        if key == 'boot_mode':
            self.device_status = "offline"

        elif self.device_status != "online":
            self.device_status = "online"

        # push notifications to KV system
        self.notify()
        
    def scan(self):
        self.getFirmwareInfo()
        self.getKVMeta()
        try:
            self.getKV("name", "short_addr")

        # backwards compatibility hack
        # TODO make this go away
        except KeyError:
            self.getKV("device_name", "802.15.4_short")

        return self
    
    def _sendCommand(self, cmd):
        #_my_lock.acquire()

        try:
            self._channel.write(cmd.pack())
            
            data = self._channel.read()
            
            if self.device_status != 'online':
                self.device_status = 'online'

        except channel.ChannelException as e:
            if self.device_status == 'online':
                self.device_status = 'offline'

            #_my_lock.release()
            raise DeviceUnreachableException("Device:%d" % (self.short_addr))
        

        
        #return self._response_protocol.unpack(data)
        response = self._response_protocol.unpack(data)

        if len(data) != response.size():
            print "Cmd response: %s : %4d" % (self.host, len(data))
            print type(response), response.size()

            print "Second try:"
            response = self._response_protocol.unpack(data)
            print type(response), response.size()

            if len(data) != response.size():
                print "Third try:"
                response = self._response_protocol.unpack(data)
                print type(response), response.size()


            raise ValueError

        #_my_lock.release()
        
        return response

    def get_cli(self):
        return [f.replace(CLI_PREFIX, '', 1) for f in dir(self) 
                if f.startswith(CLI_PREFIX)
                and not f.startswith('_') 
                and isinstance(self.__getattribute__(f), types.MethodType)]
    
    # translate the ID and group to a name
    def translateKey(self, group, id):
        try:
            if id == KV_ID_ALL:
                key = [k for k, v in kv_groups.iteritems() 
                        if v == group].pop()
            
            else:
                key = [k for k, v in self._keys.iteritems() 
                        if v.group == group 
                            and v.id == id].pop()

        except IndexError:
            # key not found
            raise UnrecognizedKeyException("Device: %d Group: %d ID: %d" % (self.device_id, group, id))

        return key
    
    def getKVMeta(self):
        # check if we have a firmware info hash
        if not self._firmware_info_hash:
            # we do not, so lets get one
            self.getFirmwareInfo()

        # check meta cache for a matching hash
        s = Store(db_name="kv_meta_cache.db")

        try:
            data = binascii.unhexlify(s[self._firmware_info_hash]["kv_meta"])

        except KeyError:
            data = self.getFile("kvmeta")
            s[self._firmware_info_hash] = {"kv_meta": binascii.hexlify(data)} # store data

        # unpack kv meta data
        kvmeta = sapphiredata.KVMetaArray().unpack(data)
        
        # reset keys
        self._keys = KVMeta()
        
        # load keys into meta data
        for kv in kvmeta:
            self._keys[kv.param_name] = KVKey(key=kv.param_name, device=self, group=kv.group, id=kv.id, flags=kv.flags, type=kv.type)
    
    def getAllKV(self):
        keys = [key for key in self._keys]
        
        self.getKV(*keys)

    def setKey(self, param, value):
        self.setKV(**{param: value})

    def setKV(self, **kwargs):
        params = []
        
        keys = {}
        
        # iterate over keys and create requests for them
        for key in kwargs:
            # filter out keys which are not changing
            #if kwargs[key] == self._keys[key].value:
            #    continue

            # check if key is set to read only
            if 'read_only' in self._keys[key].flags:
                raise ReadOnlyKeyException(key)

            param = sapphiredata.KVParamField(group=self._keys[key].group,
                                              id=self._keys[key].id,
                                              type=self._keys[key].type,
                                              param_value=kwargs[key])
            params.append(param)
            
            keys[(param.group, param.id)] = key

        # now we have a list of requests, we need to batch them together such
        # that the params all fit within packet size constraints
        batches = [sapphiredata.KVParamArray() for param in params]
        
        for batch in batches:
            for param in params:
                if batch.size() + param.size() < MAX_KV_DATA_LEN:
                    batch.append(param)
            
            for param in batch:
                params.remove(param)
        
        # filter out batches which are empty
        batches = [batch for batch in batches if len(batch) > 0]

        # send each batch
        for batch in batches:
            cmd = self._protocol.SetKV(params=batch)
            
            response = self._sendCommand(cmd)
        
            # parse responses
            for param in response.params:
                key = keys[(param.group, param.id)]
                
                # check status
                if param.status >= 0:
                    self._keys[key]._value = kwargs[key]

                    # set internal KVObject attributes
                    self._attrs[key] = kwargs[key]
                
                else:
                    raise ValueError

    def getKey(self, param):
        return self.getKV(param)[param]

    def getKV(self, *args):
        params = []
        
        keys = {}

        # iterate over keys and create requests for them
        for key in args:
            param = sapphiredata.KVRequestField(group=self._keys[key].group,
                                                id=self._keys[key].id,
                                                type=self._keys[key].type)

            params.append(param)
            
            keys[(param.group, param.id)] = key

        # now we have a list of requests, we need to batch them together such
        # that the responses all fit within packet size constraints
        batches = [sapphiredata.KVRequestArray() for param in params]
        
        for batch in batches:
            for param in params:
                if ( batch.paramSize() + param.paramSize() ) < MAX_KV_DATA_LEN:
                    batch.append(param)
            
            for param in batch:
                params.remove(param)
            
        # filter out batches which are empty
        batches = [batch for batch in batches if len(batch) > 0]

        responses = {}
        
        # request each batch
        for batch in batches:
            cmd = self._protocol.GetKV(params=batch)

            response = self._sendCommand(cmd)

            # parse responses
            for param in response.params:
                try:
                    key = keys[(param.group, param.id)]

                except KeyError:
                    print "!!!!!!!!"
                    print self.object_id, self.host
                    
                    print response
                    #print response.params
                    print "!!!!!!!!"

                    raise

                responses[key] = param.param_value
                
                # update internal meta data
                self._keys[key]._value = param.param_value

                # TODO: hack to avoid clearing the device id
                if key != "device_id":
                    self.set(key, param.param_value)
                
        return responses

    def resetConfig(self):
        return self._sendCommand(self._protocol.ResetCfg())

    def setSecurityKey(self, key_id, key):
        cmd = self._protocol.SetSecurityKey(key_id=key_id, key=key)

        return self._sendCommand(cmd)

    def echo(self, data):
        return self._sendCommand(self._protocol.Echo(echo_data=data))
    
    def _rebootCmd(self, cmd):
        try:
            response = self._sendCommand(cmd)
            self.device_status = "reboot"
            
            # device delays 1 second before going offline
            time.sleep(1.0)

            self.device_status = "offline"

        except:
            raise
        
        return response

    def reboot(self):
        return self._rebootCmd(self._protocol.Reboot())

    def safeMode(self):
        return self._rebootCmd(self._protocol.SafeMode())
    
    def rebootAndLoadFW(self):
        return self._rebootCmd(self._protocol.LoadFirmware())

    def formatFS(self):
        return self._sendCommand(self._protocol.FormatFS())
    

    def get_file_id(self, name):
        result = self._sendCommand(self._protocol.GetFileID(name=name))
        
        if result.file_id < 0:
            raise IOError("File: %s not found" % (name))

        return result.file_id

    def create_file(self, name):
        result = self._sendCommand(self._protocol.CreateFile(name=name))
        
        if result.file_id < 0:
            raise IOError("File: %s not created" % (name))

        return result.file_id

    def read_file_data(self, file_id, pos, length):
        result = self._sendCommand(self._protocol.ReadFileData(file_id=file_id, position=pos, length=length))

        return result.data

    def write_file_data(self, file_id, pos, data):
        result = self._sendCommand(self._protocol.WriteFileData(file_id=file_id, position=pos, length=len(data), data=data))        

        return result.write_length

    def remove_file(self, file_id):
        result = self._sendCommand(self._protocol.RemoveFile(file_id=file_id))
        
        if result.status < 0:
            raise IOError("File: %s not deleted" % (file_id))

    def getFile(self, filename, progress=None):

        file_id = self.get_file_id(filename)
        
        data = ""
        pos = 0

        while True:
            if progress:
                progress(pos)

            result_data = self.read_file_data(file_id, pos, FILE_TRANSFER_LEN)
            
            data += result_data

            if len(result_data) < FILE_TRANSFER_LEN:
                break
            
            pos += FILE_TRANSFER_LEN
        
        if progress:
            progress(len(data))

        return data

    def putFile(self, filename, data, progress=None):
        
        # get file id
        try:
            file_id = self.get_file_id(filename)

        # create file
        except IOError:
            file_id = self.create_file(filename)

        pos = 0

        while pos < len(data):
            chunk = data[pos:pos + FILE_TRANSFER_LEN]
            
            if progress:
                progress(pos)

            if self.write_file_data(file_id, pos, chunk) < len(chunk):
                raise IOError("Write error occurred :-(")

            pos += FILE_TRANSFER_LEN
        
        if progress:
            progress(len(data))

    def listFiles(self):
        data = self.getFile("fileinfo")
        
        fileinfo = sapphiredata.FileInfoArray()

        fileinfo.unpack(data)

        return fileinfo
    
    def loadFirmware(self, firmware_id=None, progress=None):
        if firmware_id == None:
            fw_info = self.getFirmwareInfo()
            fw_file = firmware.get_firmware(fw_info.firmware_id)
            
        else:
            fw_file = firmware.get_firmware(firmware_id)
        
        if fw_file is None:
            raise IOError("Firmware image not found")
        
        # delete old firmware
        file_id = self.get_file_id("firmware.bin")
        self.remove_file(file_id)
        
        # read firmware data
        f = open(fw_file, 'rb')
        firmware_data = f.read()
        f.close()

        # load firmware image
        self.putFile("firmware.bin", firmware_data, progress=progress)
        
        # reboot to loader
        self.rebootAndLoadFW()
    
    def getFirmwareInfo(self):
        data = self.getFile("fwinfo")

        # create hash of firmware info
        h = hashlib.new('sha256')
        h.update(data)
        self._firmware_info_hash = h.hexdigest()
        
        # unpack
        fw_info = sapphiredata.FirmwareInfoField()
        fw_info.unpack(data)

        # update state
        self.firmware_id        = fw_info.firmware_id
        self.firmware_name      = fw_info.app_name
        self.firmware_version   = fw_info.app_version
        self.os_name            = fw_info.os_name
        self.os_version         = fw_info.os_version
    
        return fw_info
    
    def reset_time_sync(self):
        response = self._sendCommand(self._protocol.ResetWcomTimeSync())

        return response

    def getGcInfo(self):
        data = self.getFile("gc_data")
        
        gc_array = ArrayField(field=Uint32Field).unpack(data)
        
        return {"sector_erase_counts": gc_array}

    def getThreadInfo(self):
        data = self.getFile("threadinfo")
        
        info = sapphiredata.ThreadInfoArray()
        info.unpack(data)
        
        return info

    def getRouteInfo(self):
        data = self.getFile("routes")
        
        info = sapphiredata.RouteArray()
        info.unpack(data)
        
        return info

    def getNeighborInfo(self):
        data = self.getFile("neighbors")
        
        info = sapphiredata.NeighborArray()
        info.unpack(data)

        return info
    
    def getDnsInfo(self):
        data = self.getFile("dns_cache")
        info = sapphiredata.DnsCacheArray()
        info.unpack(data)
        
        return info

    def request_route(self, ip='0.0.0.0', short_addr=0):
        #query_field = RouteQueryField(dest_ip=ip, dest_short=short_addr)
        #print query_field
        #print self._protocol.RequestRoute(query=query_field)

        response = self._sendCommand(self._protocol.RequestRoute(dest_ip=ip, dest_short=short_addr))

        return response

    def set_kv_server(self, ip='0.0.0.0', port=0):
        return self._sendCommand(self._protocol.SetKVServer(ip=ip, port=port))


    ##########################
    # Command Line Interface
    ##########################
    def cli_scan(self, line):
        self.scan()

        return "Done"

    def cli_echo(self, line):
        start = time.time()

        s = self.echo(line).echo_data

        elapsed = time.time() - start

        s += " (%d ms)" % (elapsed * 1000)

        return s
    
    def cli_reboot(self, line):
        self.reboot()
        return "Rebooting"

    def cli_safemode(self, line):
        self.safeMode()
        return "Rebooting into safe mode"

    def cli_formatfs(self, line):
        self.formatFS()

        return "Formatting file system and rebooting..."

    def cli_rm(self, line):
        file_id = self.get_file_id(line)
        self.remove_file(file_id)
        
        return "Removed: %s" % (line)

    def cli_ls(self, line):
        fileinfo = self.listFiles()
        
        s = "\n"
        
        # iterate over file listing, filtering out empty files
        for f in [f for f in fileinfo if f.filesize >= 0]:
            v = ''
            
            if f.flags == 1:
                v = 'V'

            s += "%1s %6d %s\n" % \
                (v,
                 f.filesize, 
                 f.filename)
            
        return s

    def cli_cat(self, line):
        data = self.getFile(line)
        
        s = "\n" + data

        return s
    
    def cli_getfile(self, line):
        def progress(length):
            sys.stdout.write("\rReading: %5d bytes" % (length))
            sys.stdout.flush()
        
        print ""

        data = self.getFile(line, progress=progress)
        
        f = open(line, 'w')
        f.write(data)
        f.close()

        return ""

    def cli_putfile(self, line):
        def progress(length):
            sys.stdout.write("\rWrite: %5d bytes" % (length))
            sys.stdout.flush()
        
        f = open(line, 'rb')
        data = f.read()
        f.close()
        
        print ""

        self.putFile(line, data, progress=progress)
        
        return ""

    def cli_loadfw(self, line):
        def progress(length):
            sys.stdout.write("\rWrite: %5d bytes" % (length))
            sys.stdout.flush()
        
        if line == "":
            fw = None
        else:
            fw = line

        self.loadFirmware(firmware_id=fw, progress=progress)
        
        print ""

        return "Rebooting..."

    def cli_fwinfo(self, line):
        fwinfo = self.getFirmwareInfo()
        
        s = "App:%24s Ver:%s OSVer:%s ID:%s" % \
            (fwinfo.app_name,
             fwinfo.app_version,
             fwinfo.os_version,
             fwinfo.firmware_id)
        
        return s

    def cli_gcinfo(self, line):
        info = self.getGcInfo()
        
        i = 0
        sectors = []
        
        for sector in info["sector_erase_counts"]:
            sectors.append(sector)

        s = "Erases:%7d Least:%6d Most:%6d" % (sum(sectors), min(sectors), max(sectors))
        
        if line == "all":
            
            i = 0
            s += "\nSector erase counts:\n"

            for sector in sectors:
                i += 1

                s += "%6d " % (sector)

                if (i % 8) == 0:
                    s += "\n"
        
        return s

    def cli_threadinfo(self, line):
        info = self.getThreadInfo()

        s = "\nAddr  Line  Flags Data Time         Runs     Name\n"

        for n in info:
            
            flags = ''
            
            if n.flags & 1:
                flags += 'W'
            else:
                flags += ' '

            if n.flags & 2:
                flags += 'Y'
            else:
                flags += ' '

            if n.flags & 4:
                flags += 'S'
            else:
                flags += ' '

            if n.flags & 8:
                flags += 'I'
            else:
                flags += ' '

            s += "%4x  %4d   %4s %4d %12d %8d %s\n" % \
                (n.addr,
                 n.line,
                 flags,
                 n.data_size,
                 n.run_time,
                 n.runs,
                 n.name)
        
        return s

    def cli_routeinfo(self, line):
        info = self.getRouteInfo()
        
        s = "\nDestIP          DestShort Flags Cost  Age Hops\n"
           #"111.222.333.444 00026     0x00  10000 000 00  00000->11111->11111"

        for i in info:
            s += "%15s %5d     0x%2x  %5d %3d %2d  " % \
                (i.dest_ip,
                 i.dest_short,
                 i.dest_flags,
                 i.cost,
                 i.age,
                 i.hop_count)
            
            for hop in xrange(i.hop_count):
                s += "%5d->" % (i.hops[hop])
            
            s += "%5d\n" % (i.dest_short)
            
        return s

    def cli_neighborinfo(self, line):
        info = self.getNeighborInfo()
        
        s = "\nShort Flags     IP              LQI RSSI ETX Delay Age Traffic\n"
             #"00026 R-------- 111.222.333.444 000 000  000 00000 000"
        
        for n in info:

            flags = ['-', '-', '-', '-', '-', '-', '-', '-', '-']
            
            if n.flags & 1:
                flags[0] = 'R'

            if n.flags & 2:
                flags[1] = 'G'

            if n.flags & 4:
                flags[2] = 'D'

            if n.flags & 8:
                flags[3] = 'U'

            if n.flags & 16:
                flags[4] = 'F'

            if n.flags & 32:
                flags[5] = 'X'

            if n.flags & 64:
                flags[6] = 'T'

            if n.flags & 128:
                flags[7] = 'J'

            if n.flags & 256:
                flags[8] = 'N'
            
            flags_str = ''.join(flags)

            s += "%5d %9s %15s %3d %3d  %3d %5d %3d  %3d\n" % \
                (n.short_addr,
                 flags_str,
                 n.ip,
                 n.lqi,
                 n.rssi,
                 n.etx,
                 n.delay,
                 n.age,
                 n.traffic)
        
        return s

    def cli_dnsinfo(self, line):
        dnsinfo = self.getDnsInfo()

        s = "\n"
        
        # iterate over DNS cache entries, filtering out the empty ones
        for d in [d for d in dnsinfo if d.status != 0]:
            if d.status == 1:
                status = "valid"
            else:
                status = "invalid"

            s += "IP:%15s Status:%8s TTL:%8d Query:%s" % \
                (d.ip,
                 status,
                 d.ttl,
                 d.query)

        return s

    def cli_getkey(self, line):
        if line == "":
            keys = self._keys

            params = self.getKV(*keys)
            
            s = "\nName                            Group ID Flags  Value\n"

            for k in sorted(params.iterkeys()):
                s += "%s\n" % (self._keys[k])

        else:
            param = self.getKey(line)

            s = "%s = %s" % (line, param)
        
        return s
    
    def cli_setkey(self, line):
        param, value = line.split()
        
        self.setKey(param, value)
        
        new_param = self.getKey(param)
        
        return "%s set to: %s" % (param, new_param)


    def cli_resetcfg(self, line):
        print ""
        print "DANGER ZONE! Are you sure you want to do this?"
        print "Type 'yes' if you are sure."

        yes = raw_input()
        
        if yes == "yes":
            self.resetConfig()
        
            return "Configuration reset"
        
        return "No changes made"

    def cli_systime(self, line):
        t = self.getKey("sys_time")
        dt = timedelta(seconds=long(t / 1000))
        
        return "%11d ms (%s)" % (t, str(dt))

    def cli_status(self, line):  
        params = self.getKV("sys_mode", "mem_peak_usage", "fs_free_space", "sys_time", "supply_voltage")
        
        if params["sys_mode"] == 0:
            mode = "normal "

        elif params["sys_mode"] == 1:
            mode = "safe   "

        else:
            mode = "unknown"

        s = "Mode:%s PeakMem:%4d DiskSpace:%6d SysTime:%11d Volts:%2.1f" % (mode,
                                                                            params["mem_peak_usage"],
                                                                            params["fs_free_space"],
                                                                            params["sys_time"],
                                                                            params["supply_voltage"])

        return s

    def cli_warnings(self, line):
        params = self.getKey("sys_warnings")

        warnings = decode_warnings(params)

        s = ''
        for w in warnings:
            s += w + " "
        
        if len(warnings) == 0:
            s = "OK"

        return s

    def cli_diskinfo(self, line):
        params = self.getKV("fs_free_space", "fs_total_space", "fs_disk_files", "fs_max_disk_files", "fs_virtual_files", "fs_max_virtual_files")
        
        s = "Free:%6d Total:%6d Files:%2d / %2d Vfiles:%2d / %2d" % \
            (params["fs_free_space"],
             params["fs_total_space"],
             params["fs_disk_files"],
             params["fs_max_disk_files"],
             params["fs_virtual_files"],
             params["fs_max_virtual_files"])
        
        return s

    def cli_cpuinfo(self, line):
        params = self.getKV("thread_task_time", "thread_sleep_time", "thread_peak", "thread_loops", "thread_run_time")

        # convert all params to floats
        params = {k: float(v) for (k, v) in params.iteritems()}

        if params["thread_run_time"] == 0:
            loop_rate = 0
            cpu_usage = 0

        else:
            loop_rate = params["thread_loops"] / (params["thread_run_time"] / 1000.0)
            cpu_usage = (params["thread_task_time"] / params["thread_run_time"]) * 100.0
    
        s = "CPU:%2.1f%% Tsk:%8d Slp:%8d Ohd:%8d MaxT:%3d Loops:%8d @ %5d/sec" % \
            (cpu_usage,
             params["thread_task_time"],
             params["thread_sleep_time"],
             params["thread_run_time"] - (params["thread_task_time"] + params["thread_sleep_time"]),
             params["thread_peak"],
             params["thread_loops"],
             loop_rate)
        
        return s

    def cli_meminfo(self, line):
        params = self.getKV("mem_handles", "mem_max_handles", "mem_stack", "mem_max_stack", "mem_free_space", "mem_peak_usage", "mem_heap_size")
        
        s = "Handles:%3d/%3d Stack:%4d/%4d Free:%4d Used:%4d Peak:%4d Heap:%4d" % \
             (params["mem_handles"],
              params["mem_max_handles"],
              params["mem_stack"],
              params["mem_max_stack"],
              params["mem_free_space"],
              params["mem_heap_size"] - params["mem_free_space"],
              params["mem_peak_usage"],
              params["mem_heap_size"])

        return s

    def cli_macinfo(self, line):
        params = self.getKV("wcom_mac_be", "wcom_adaptive_cca_resolution", "wcom_nei_upstream", "wcom_nei_depth", "wcom_nei_beacon_interval")
        
        s = "Local BE:%1.3f Upstream:%5d Depth:%2d Interval:%3d" % \
            (float(params["wcom_mac_be"]) / float(params["wcom_adaptive_cca_resolution"]), 
             params["wcom_nei_upstream"], 
             params["wcom_nei_depth"], 
             params["wcom_nei_beacon_interval"])

        return s

    def cli_timeinfo(self, line):
        param = self.getKV("wcom_time_flags", "wcom_time_source_addr", "wcom_time_clock_source", "wcom_time_depth", "wcom_time_sequence", "wcom_time_drift", "wcom_time_local_time", "wcom_time_network_time")
        
        s = "Flags:%3d Src:%5d Clk:%3d Depth:%2d Seq:%3d Drift:%8ld Local:%10ld Net:%10ld" % \
            (param["wcom_time_flags"],
             param["wcom_time_source_addr"],
             param["wcom_time_clock_source"],
             param["wcom_time_depth"],
             param["wcom_time_sequence"],
             param["wcom_time_drift"],
             param["wcom_time_local_time"],
             param["wcom_time_network_time"])

        return s
    
    def cli_loaderinfo(self, line):
        params = self.getKV("loader_status", "loader_version_minor", "loader_version_major")

        s = "Loader version: %d.%d Status: %d" % \
            (params["loader_status"],
             params["loader_version_major"],
             params["loader_version_minor"])

        return s

    def cli_boardtemp(self, line):
        tempC = self.getKey("board_temperature")
        
        tempF = tempC * 1.8 + 32

        s = "%2.1fC %2.1fF" % (tempC, tempF)

        return s

    def cli_resettimesync(self, line):
        self.reset_time_sync()

        return "OK"

    def cli_ntptime(self, line):
        ntp_seconds = self.getKey("ntp_seconds")

        ntp_now = timedelta(seconds=ntp_seconds) + NTP_EPOCH

        return ntp_now.isoformat()

    def cli_requestroute(self, line):
        if len(line.split('.')) > 1:
            self.request_route(ip=line)

        else:
            self.request_route(short_addr=line)
    
    def cli_setkvserver(self, line):
        tokens = line.split()

        self.set_kv_server(tokens[0], tokens[1])

        return "OK"


import gateway

def createDevice(**kwargs):
    
    if 'firmware_id' not in kwargs:
        return Device(**kwargs)

    elif kwargs['firmware_id'] == "e966b682-ce7c-4c80-8373-2f1ee344e39d":
        return gateway.Gateway(**kwargs)

    return Device(**kwargs)
    

