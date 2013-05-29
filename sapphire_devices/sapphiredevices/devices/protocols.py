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
from sapphiredata import *

CMD2_APP_CMD_BASE = 32768

class GatewayServicesProtocol(Protocol):
    
    class PollGateway(Payload):
        msg_type = 1
        fields = [Uint16Field(name="short_addr")]

    class GatewayToken(Payload):
        msg_type = 2
        fields = [Uint32Field(name="token"),
                  Uint16Field(name="short_addr"),
                  Uint64Field(name="device_id")]
    
    class GetNetworkTime(Payload):
        msg_type = 9
        fields = []
    
    class NetworkTime(Payload):
        msg_type = 10
        fields = [Uint8Field(name="flags"),
                  Uint32Field(name="ntp_time_seconds"),
                  Uint32Field(name="ntp_time_fractional"),
                  Uint32Field(name="wcom_network_time")]
    
    msg_type_format = Uint8Field()


class DeviceCommandProtocol(Protocol):
    
    PORT = 16385

    class Echo(Payload):
        msg_type = 1
        fields = [StringField(length=128, name="echo_data")]

    class Reboot(Payload):
        msg_type = 2
        fields = []

    class SafeMode(Payload):
        msg_type = 3
        fields = []

    class LoadFirmware(Payload):
        msg_type = 4
        fields = []
    
    class FormatFS(Payload):
        msg_type = 10
        fields = []
    
    class GetFileID(Payload):
        msg_type = 20
        fields = [StringField(length=64, name="name")]

    class CreateFile(Payload):
        msg_type = 21
        fields = [StringField(length=64, name="name")]

    class ReadFileData(Payload):
        msg_type = 22
        fields = [Uint8Field(name="file_id"),
                  Uint32Field(name="position"),
                  Uint32Field(name="length")]

    class WriteFileData(Payload):
        msg_type = 23
        fields = [Uint8Field(name="file_id"),
                  Uint32Field(name="position"),
                  Uint32Field(name="length"),
                  RawBinField(name="data")]

    class RemoveFile(Payload):
        msg_type = 24
        fields = [Uint8Field(name="file_id")]
    
    class ResetCfg(Payload):
        msg_type = 32
        fields = []

    class RequestRoute(Payload):
        msg_type = 50;
        fields = [Ipv4Field(name="dest_ip"),
                  Uint16Field(name="dest_short"),
                  Uint8Field(name="dest_flags")]

    class ResetWcomTimeSync(Payload):
        msg_type = 70
        fields = []
    
    class SetKV(Payload):
        msg_type = 80
        #fields = [KVParamArray(name="params")]
        fields = [RawBinField(name="data")]

    class GetKV(Payload):
        msg_type = 81
        #fields = [KVRequestArray(name="params")]
        fields = [RawBinField(name="data")]
    
    class SetKVServer(Payload):
        msg_type = 85
        fields = [Ipv4Field(name="ip"),
                  Uint16Field(name="port")]

    class SetSecurityKey(Payload):
        msg_type = 90
        fields = [Uint8Field(name="key_id"),
                  Key128Field(name="key")]

    msg_type_format = Uint16Field()


class DeviceCommandResponseProtocol(Protocol):

    class Echo(Payload):
        msg_type = 1
        fields = [StringField(length=128, name="echo_data")]
 
    class Reboot(Payload):
        msg_type = 2
        fields = []

    class SafeMode(Payload):
        msg_type = 3
        fields = []

    class LoadFirmware(Payload):
        msg_type = 4
        fields = []

    class FormatFS(Payload):
        msg_type = 10
        fields = []
    
    class GetFileID(Payload):
        msg_type = 20
        fields = [Int8Field(name="file_id")]

    class CreateFile(Payload):
        msg_type = 21
        fields = [Int8Field(name="file_id")]

    class ReadFileData(Payload):
        msg_type = 22
        fields = [RawBinField(name="data")]
                  
    class WriteFileData(Payload):
        msg_type = 23
        fields = [Uint16Field(name="write_length")]
                  
    class RemoveFile(Payload):
        msg_type = 24
        fields = [Uint8Field(name="status")]

    class GetCfgParam(Payload):
        msg_type = 30
        fields = [RawBinField(name="data")]

    class SetCfgParam(Payload):
        msg_type = 31
        fields = []

    class ResetCfg(Payload):
        msg_type = 32
        fields = []

    class RequestRoute(Payload):
        msg_type = 50;
        fields = []

    class ResetWcomTimeSync(Payload):
        msg_type = 70
        fields = []

    class SetKV(Payload):
        msg_type = 80
        #fields = [KVStatusArray(name="params")]
        fields = [RawBinField(name="data")]

    class GetKV(Payload):
        msg_type = 81
        #fields = [KVParamArray(name="params")]
        fields = [RawBinField(name="data")]

    class SetKVServer(Payload):
        msg_type = 85
        fields = []

    class SetSecurityKey(Payload):
        msg_type = 90
        fields = []

    msg_type_format = Uint16Field()


if __name__ == '__main__':
    p = GatewayServicesProtocol()

    print p.unpack("\x01\x04\x00")

    m = p.PollGateway()
    a = m.unpack("\x01\x02\x00")
    print a

    m1 = p.PollGateway(short_addr = 6)
    print m1
    print repr(m1.pack())

    m2 = p.unpack(m1.pack())
    print m2


    s = StructField(name="struct",
                fields=[Uint8Field(name="field0"), 
                        Uint16Field(name="field1")])

    print s


    a = ArrayField(name="array", field=s)

    print a


    f = FileInfoField()
    print f

    a = FileInfoArray()
    print a

