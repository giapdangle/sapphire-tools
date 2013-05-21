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
"""Sapphire Data
"""

from messages import *
import sapphiretypes



class FileInfoField(StructField):
    def __init__(self, **kwargs):
        fields = [Int32Field(name="filesize"),
                  StringField(name="filename", length=64),
                  Uint8Field(name="flags"),
                  ArrayField(name="reserved", field=Uint8Field, length=15)]

        super(FileInfoField, self).__init__(name="file_info", fields=fields, **kwargs)

class FileInfoArray(ArrayField):
    def __init__(self, **kwargs):
        field = FileInfoField
        
        super(FileInfoArray, self).__init__(field=field, **kwargs)

class FirmwareInfoField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint32Field(name="firmware_length"),
                  UuidField(name="firmware_id"),
                  StringField(name="os_name", length=128),
                  StringField(name="os_version", length=16),
                  StringField(name="app_name", length=128),
                  StringField(name="app_version", length=16)]

        super(FirmwareInfoField, self).__init__(name="firmware_info", fields=fields, **kwargs)

class DeviceDBField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint16Field(name="short_addr"),
                  Uint64Field(name="device_id"),
                  Ipv4Field(name="ip")]

        super(DeviceDBField, self).__init__(name="devicedb", fields=fields, **kwargs)
 
class DeviceDBArray(ArrayField):
    def __init__(self, **kwargs):
        field = DeviceDBField
        
        super(DeviceDBArray, self).__init__(field=field, **kwargs)

class SerialFrameHeader(StructField):
    def __init__(self, **kwargs):
        fields = [Uint16Field(name="len"),
                  Uint16Field(name="inverted_len")]
    
        super(SerialFrameHeader, self).__init__(name="frame_header", fields=fields, **kwargs)

class DnsCacheField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint8Field(name="status"),
                  Ipv4Field(name="ip"),
                  Uint32Field(name="ttl"),
                  StringField(name="query")]
    
        super(DnsCacheField, self).__init__(name="dns_cache", fields=fields, **kwargs)

class DnsCacheArray(ArrayField):
    def __init__(self, **kwargs):
        field = DnsCacheField
        
        super(DnsCacheArray, self).__init__(field=field, **kwargs)

class RouteQueryField(StructField):
  def __init__(self, **kwargs):
        fields = [Ipv4Field(name="dest_ip"),
                  Uint16Field(name="dest_short"),
                  Uint8Field(name="dest_flags")]
        
        super(RouteQueryField, self).__init__(fields=fields, **kwargs)

class RouteField(StructField):
    def __init__(self, **kwargs):
        fields = [Ipv4Field(name="dest_ip"),
                  Uint16Field(name="dest_short"),
                  Uint8Field(name="dest_flags"),
                  Uint16Field(name="cost"),
                  Uint8Field(name="age"),
                  Uint8Field(name="hop_count"),
                  ArrayField(name="hops", field=Uint16Field, length=8)]
        
        super(RouteField, self).__init__(fields=fields, **kwargs)

class RouteArray(ArrayField):
    def __init__(self, **kwargs):
        field = RouteField
        
        super(RouteArray, self).__init__(field=field, **kwargs)

class NeighborField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint16Field(name="flags"),
                  Ipv4Field(name="ip"),
                  Uint16Field(name="short_addr"),
                  ArrayField(name="iv", field=Uint8Field, length=16),
                  Uint32Field(name="replay_counter"),
                  Uint8Field(name="lqi"),
                  Uint8Field(name="rssi"),
                  Uint8Field(name="prr"),
                  Uint8Field(name="etx"),
                  Uint8Field(name="delay"),
                  Uint8Field(name="traffic_accumulator"),
                  Uint8Field(name="traffic"),
                  Uint8Field(name="age")]

        super(NeighborField, self).__init__(fields=fields, **kwargs)

class NeighborArray(ArrayField):
    def __init__(self, **kwargs):
        field = NeighborField
        
        super(NeighborArray, self).__init__(field=field, **kwargs)


class ThreadInfoField(StructField):
    def __init__(self, **kwargs):
        fields = [StringField(name="name", length=64),
                  Uint16Field(name="flags"),
                  Uint16Field(name="addr"),
                  Uint16Field(name="data_size"),
                  Uint32Field(name="run_time"),
                  Uint32Field(name="runs"),
                  Uint16Field(name="line"),
                  ArrayField(name="reserved", field=Uint8Field, length=32)]

        super(ThreadInfoField, self).__init__(fields=fields, **kwargs)

class ThreadInfoArray(ArrayField):
    def __init__(self, **kwargs):
        field = ThreadInfoField
        
        super(ThreadInfoArray, self).__init__(field=field, **kwargs)

class NTPTimestampField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint32Field(name="seconds"),
                  Uint32Field(name="fraction")]

        super(NTPTimestampField, self).__init__(fields=fields, **kwargs)

class SubscriptionField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint8Field(name="group"),
                  Uint8Field(name="id"),
                  Ipv4Field(name="ip"),
                  Uint16Field(name="port")]

        super(SubscriptionField, self).__init__(fields=fields, **kwargs)

class SubscriptionArray(ArrayField):
    def __init__(self, **kwargs):
        field = SubscriptionField
        
        super(SubscriptionArray, self).__init__(field=field, **kwargs)

class KVMetaField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint8Field(name="group"),
                  Uint8Field(name="id"),
                  Int8Field(name="type"),
                  Uint16Field(name="flags"),
                  Uint16Field(name="__var_ptr"),
                  Uint16Field(name="__notifier_ptr"),
                  StringField(name="param_name", length=32)]
        
        super(KVMetaField, self).__init__(fields=fields, **kwargs)

class KVMetaArray(ArrayField):
    def __init__(self, **kwargs):
        field = KVMetaField
        
        super(KVMetaArray, self).__init__(field=field, **kwargs)

class KVParamField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint8Field(name="group"),
                  Uint8Field(name="id"),
                  Int8Field(name="type")]
        
        # look up type
        if 'type' in kwargs:
            valuefield = sapphiretypes.getType(kwargs['type'], name='param_value')
            fields.append(valuefield)
            
            if 'param_value' in kwargs:
                valuefield.value = kwargs['param_value']
                kwargs['param_value'] = valuefield.value
        
        super(KVParamField, self).__init__(fields=fields, **kwargs)
    
    def unpack(self, buffer):
        super(KVParamField, self).unpack(buffer)
        
        buffer = buffer[self.size():]

        # get value field based on type
        valuefield = sapphiretypes.getType(self.type, name='param_value')
        valuefield.unpack(buffer)

        self.fields[valuefield.name] = valuefield
        
        return self
    
class KVParamArray(ArrayField):
    def __init__(self, **kwargs):
        field = KVParamField
        
        super(KVParamArray, self).__init__(field=field, **kwargs)

class KVStatusField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint8Field(name="group"),
                  Uint8Field(name="id"),
                  Int8Field(name="status")]

        super(KVStatusField, self).__init__(fields=fields, **kwargs)

class KVStatusArray(ArrayField):
    def __init__(self, **kwargs):
        field = KVStatusField
        
        super(KVStatusArray, self).__init__(field=field, **kwargs)

class KVRequestField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint8Field(name="group"),
                  Uint8Field(name="id"),
                  Int8Field(name="type")]
        
        super(KVRequestField, self).__init__(fields=fields, **kwargs)

        self.__type = None
    
    # return size of returned param in response to this request
    def paramSize(self):
        if self.__type != self.type:
            self.__type = self.type
            self.__param_size = KVParamField(type=self.type).size()

        return self.__param_size

    # return size of returned status in response to this request
    def statusSize(self):
        return KVStatusField().size()

class KVRequestArray(ArrayField):
    def __init__(self, **kwargs):
        field = KVRequestField
        
        super(KVRequestArray, self).__init__(field=field, **kwargs)

    # return size of returned param in response to this request
    def paramSize(self):
        return sum([request.paramSize() for request in self.fields])

    # return size of returned status in response to this request
    def statusSize(self):
        return sum([request.statusSize() for request in self.fields])

class BridgeField(StructField):
    def __init__(self, **kwargs):
        fields = [Uint16Field(name="short_addr"),
                  Ipv4Field(name="ip"),
                  Uint32Field(name="lease"),
                  Uint32Field(name="time_left"),
                  Uint8Field(name="flags")]

        super(BridgeField, self).__init__(fields=fields, **kwargs)

class BridgeArray(ArrayField):
    def __init__(self, **kwargs):
        field = BridgeField
        
        super(BridgeArray, self).__init__(field=field, **kwargs)

class ArpField(StructField):
    def __init__(self, **kwargs):
        fields = [Mac48Field(name="eth_mac"),
                  Ipv4Field(name="ip"),
                  Uint8Field(name="age")]

        super(ArpField, self).__init__(fields=fields, **kwargs)

class ArpArray(ArrayField):
    def __init__(self, **kwargs):
        field = ArpField
        
        super(ArpArray, self).__init__(field=field, **kwargs)


if __name__ == '__main__':
    
    d = DeviceDBField(ip="1.2.3.4")
    
    print d
    print d.size()

    if d.ip == "1.2.3.4":
        print "Yes"

    d.ip = "2.3.4.5"

    print d


