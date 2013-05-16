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

import inspect
import struct

from fields import *


class Payload(StructField):
    
    msg_type_format = None
    msg_type = 0
    fields = []

    def __init__(self, **kwargs):
        super(Payload, self).__init__(fields=self.fields, **kwargs)
        
        if self.msg_type_format:
            self.msg_type_format.value = self.msg_type
    
    def size(self):
        field_size = super(Payload, self).size()
        
        if self.msg_type_format:
            field_size += self.msg_type_format.size()

        return field_size

    def unpack(self, buffer):
        if self.msg_type_format:
            # slice past message type if present
            buffer = buffer[self.msg_type_format.size():]
        
        super(Payload, self).unpack(buffer)

        return self

    def pack(self):
        s = ""

        if self.msg_type_format:
            s = self.msg_type_format.pack()
        
        s += super(Payload, self).pack()

        return s


class Protocol(object):
    
    class NullPayload(Payload):
        msg_type = 0
        fields = []

    msg_type_format = Uint8Field()

    def __init__(self):
        self.messages = self.get_msgs()
        self.__msg_dict = {}

        for message in self.messages:
            message.msg_type_format = self.msg_type_format
            self.__msg_dict[message.msg_type] = message
    
    def get_msgs(self):
        return [m[1] for m in inspect.getmembers(self) 
                    if hasattr(m[1], '__bases__') and Payload in m[1].__bases__]

    def unpack(self, data):
        # get message type from data
        msg_type = self.msg_type_format.unpack(data).value
        
        # initialize and unpack message
        try:
            msg = self.__msg_dict[msg_type]().unpack(data)

        except KeyError:
            raise

        return msg


if __name__ == '__main__':
    
    i = Int32Field()
    print i
    i.value = 5
    print i

    i = Ipv4Field()

    print i
    print i.value
    
    i.value = "1.2.3.4"
    print i



