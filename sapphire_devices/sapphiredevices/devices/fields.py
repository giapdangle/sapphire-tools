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

import socket
import struct
import uuid
import json
import binascii

from string import printable
from collections import OrderedDict

class Field(object):
    def __init__(self, value=None, name=None, **kwargs):
        self._value = value
        
        if name:
            self.name = name

        else:
            self.name = self.__class__.__name__

    def toBasic(self):
        return self._value

    def toJSON(self):
        return json.dumps(self.toBasic())

    def __str__(self):
        return str(self.value)
    
    def get_value(self):
        return self._value
    
    def set_value(self, value):
        self._value = value

    value = property(get_value, set_value)

    def size(self):
        return 0

    def unpack(self, buffer):
        self.value = None
    
        return self
    
    def pack(self):
        return ""

class ErrorField(Field):
    def __init__(self, value=None, name=None, **kwargs):
        super(ErrorField, self).__init__(value=value, **kwargs)
    
    def unpack(self, buffer):
        return self
    
    def pack(self):
        return ""


class BooleanField(Field):
    def __init__(self, value=False, **kwargs):
        super(BooleanField, self).__init__(value=value, **kwargs)

    def get_value(self):
        return self._value
    
    def set_value(self, value):
        try:
            if value.lower() == "false":
                value = False
            elif value.lower() == "true":
                value = True
            elif value.lower() == '0':
                value = False

        except:
            pass

        self._value = bool(value)

    value = property(get_value, set_value)
    
    def size(self):
        return struct.calcsize('<?')
    
    def unpack(self, buffer):
        self.value = struct.unpack_from('<?', buffer)[0]
        
        return self

    def pack(self):
        return struct.pack('<?', self.value)

class IntegerField(Field):
    def __init__(self, value=0, **kwargs):
        super(IntegerField, self).__init__(value=value, **kwargs)
    
    def get_value(self):
        return self._value
    
    def set_value(self, value):
        self._value = int(value)

    value = property(get_value, set_value)

class Int8Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Int8Field, self).__init__(value=value, **kwargs)
    
    def size(self):
        return struct.calcsize('<b')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<b', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<b', self.value)

class Uint8Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Uint8Field, self).__init__(value=value, **kwargs)
    
    def size(self):
        return struct.calcsize('<B')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<B', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<B', self.value)

class CharField(Field):
    def __init__(self, value=0, **kwargs):
        super(CharField, self).__init__(value=value, **kwargs)
    
    def size(self):
        return struct.calcsize('<c')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<c', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<c', self.value)

class Int16Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Int16Field, self).__init__(value=value, **kwargs)

    def size(self):
        return struct.calcsize('<h')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<h', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<h', self.value)

class Uint16Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Uint16Field, self).__init__(value=value, **kwargs)

    def size(self):
        return struct.calcsize('<H')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<H', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<H', self.value)

class Volts16Field(Uint16Field):
    def __init__(self, value=0, **kwargs):
        super(Volts16Field, self).__init__(value=value, **kwargs)

    def get_value(self):
        return self._value / 100.0

    def set_value(self, value):
        self._value = value * 100.0

    value = property(get_value, set_value)

    def unpack(self, buffer):
        self._value = struct.unpack_from('<H', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<H', self._value)

class TempC16Field(Volts16Field):
    def __init__(self, value=0, **kwargs):
        super(TempC16Field, self).__init__(value=value, **kwargs)

class Int32Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Int32Field, self).__init__(value=value, **kwargs)

    def size(self):
        return struct.calcsize('<i')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<i', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<i', self.value)

class Uint32Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Uint32Field, self).__init__(value=value, **kwargs)

    def size(self):
        return struct.calcsize('<I')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<I', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<I', self.value)

class Int64Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Uint64Field, self).__init__(value=value, **kwargs)

    def size(self):
        return struct.calcsize('<q')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<q', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<q', self.value)

class Uint64Field(IntegerField):
    def __init__(self, value=0, **kwargs):
        super(Uint64Field, self).__init__(value=value, **kwargs)

    def size(self):
        return struct.calcsize('<Q')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<Q', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<Q', self.value)

class FloatField(Field):
    def __init__(self, value=0.0, **kwargs):
        super(FloatField, self).__init__(value=value, **kwargs)

    def get_value(self):
        return self._value
    
    def set_value(self, value):
        self._value = float(value)

    value = property(get_value, set_value)

    def size(self):
        return struct.calcsize('<f')

    def unpack(self, buffer):
        self.value = struct.unpack_from('<f', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<f', self.value)

class Ipv4Field(Uint32Field):
    def __init__(self, value=0, **kwargs):
        super(Ipv4Field, self).__init__(value=value, **kwargs)

    def get_value(self):
        return socket.inet_ntoa(struct.pack('I', self._value))
    
    def set_value(self, value):
        self._value = struct.unpack('I',socket.inet_aton(value))[0]

    value = property(get_value, set_value)

    def unpack(self, buffer):
        self._value = struct.unpack_from('<I', buffer)[0]
    
        return self
    
    def pack(self):
        return struct.pack('<I', self._value)

class StringField(Field):
    def __init__(self, value="", length=None, **kwargs):
            
        if length == None:
            length = len(value)
        
        self.length = length

        # check if a string is given, if not,
        # initialize empty string with length
        if value == "":
            value = "\0" * length

        super(StringField, self).__init__(value=str(value), **kwargs)

    def __str__(self):
        return self.value
        
    def get_value(self):
        return self._value

    def set_value(self, data):
        try:
            self._value = data.encode('ascii', errors='replace') # convert to ascii, unicode will break
        except UnicodeDecodeError:
            self._value = data
            
    value = property(get_value, set_value)

    def size(self):
        return self.length
    
    def unpack(self, buffer):
        # check if length is not set
        if self.length == 0:
            # scan to null terminator
            s = [c for c in buffer if c != '\0']

            # set length, adding one byte for the null terminator
            self.length = len(s) + 1

            # add the null terminator
            s.append('\0')
            
        else:
            s = struct.unpack_from('<' + str(self.size()) + 's', buffer)[0]
        
        self.value = ''.join([c for c in s if c in printable])
        
        return self

    def pack(self):
        return struct.pack('<' + str(self.size()) + 's', self.value)

class String128Field(StringField):
    def __init__(self, value="", **kwargs):
        super(String128Field, self).__init__(value=value, length=128, **kwargs)

class String512Field(StringField):
    def __init__(self, value="", **kwargs):
        super(String512Field, self).__init__(value=value, length=512, **kwargs)

class UuidField(StringField):
    def __init__(self, **kwargs):
        kwargs['length'] = 16

        super(UuidField, self).__init__(**kwargs)

    def get_value(self):
        return str(uuid.UUID(bytes=self._value))
    
    def set_value(self, value):
        self._value = uuid.UUID(value).bytes
    
    value = property(get_value, set_value)

    def unpack(self, buffer):
        self._value = struct.unpack_from('<' + str(self.size()) + 's', buffer)[0]
        
        return self

    def pack(self):
        return struct.pack('<' + str(self.size()) + 's', self._value)

class RawBinField(Field):
    def __init__(self, value="", **kwargs):
        super(RawBinField, self).__init__(value=value, **kwargs)
        
    def __str__(self):
        return str(self.size()) + " bytes"
    
    def size(self):
        return len(self.value)
    
    def unpack(self, buffer):
        self.value = buffer
        
        return self

    def pack(self):
        return self.value

class Mac48Field(StringField):
    def __init__(self, value="00:00:00:00:00:00", **kwargs):
        super(Mac48Field, self).__init__(value=value, **kwargs)
    
    def __str__(self):
        s = ''
        for c in self.value:
            s += hex(ord(c))[2:] + ':'
        
        return s[:len(s)-1]
    
    def size(self):
        return 6

    def get_value(self):
        return self._value
    
    def set_value(self, value):
        self._value = value

    value = property(get_value, set_value)
    
    def unpack(self, buffer):
        # slice and reverse buffer
        buffer = buffer[:self.size()]
        #buffer = buffer[::-1]

        s = ''
        for c in buffer:
            s += hex(ord(c))[2:] + ':'
        
        self._value = s[:len(s)-1]
        
        return self

    def pack(self):
        tokens = self._value.split(':')
        
        s = ''
        for token in tokens:
            s += chr(int(token, 16))
        
        #return s[::-1]
        return s
        

class Mac64Field(Mac48Field):
    def __init__(self, value="00:00:00:00:00:00:00:00", **kwargs):
        super(Mac64Field, self).__init__(value=value, **kwargs)

    def size(self):
        return 8

class Key128Field(RawBinField):
    def __init__(self, value="00000000000000000000000000000000", **kwargs):
        super(Key128Field, self).__init__(value=value, **kwargs)
        
    def size(self):
        return 16

    def get_value(self):
        return self._value
    
    def set_value(self, value):
        if len(value) == 32:
            self._value = value

        else:
            raise ValueError("Key size must be 16 bytes")

    value = property(get_value, set_value)
    
    def unpack(self, buffer):
        self._value = binascii.hexlify(buffer[:16])
        
        return self
    
    def pack(self):
        return binascii.unhexlify(self._value)

class StructField(Field):
    def __init__(self, fields=[], **kwargs):
        self.fields = OrderedDict()
        
        for field in fields:
            if field.name in kwargs:
                field.value = kwargs[field.name]
            
            self.fields[field.name] = field
        
        if 'value' in kwargs:
            for k in kwargs['value'].fields:
                self.fields[k] = kwargs['value'].fields[k]

            del kwargs['value']

        super(StructField, self).__init__(value=self, **kwargs)

    def toBasic(self):
        d = {}

        for field in self.fields:
            d[field] = self.fields[field].value
        
        return d

    def __str__(self):
        s = self.name + ":\n"

        for field in self.fields.itervalues():
            s += " " + field.name + " = " + str(field) + "\n"
        
        if len(self.fields) == 0:
            s += " Empty"
        
        return s

    def __getattr__(self, name):
        if name in self.fields:
            return self.fields[name].value
    
    def __setattr__(self, name, value):
        if "fields" in self.__dict__ and name in self.__dict__["fields"]:
            self.__dict__["fields"][name].value = value

        else:
            super(StructField, self).__setattr__(name, value)

    def size(self):
        s = 0

        for field in self.fields.itervalues():
            s += field.size()

        return s

    def unpack(self, buffer):
        for field in self.fields.itervalues():
            field.unpack(buffer)
            buffer = buffer[field.size():]
        
        return self

    def pack(self):
        s = ""
            
        for field in self.fields.itervalues():
            s += field.pack()

        return s

class ArrayField(Field):
    def __init__(self, field=None, length=None, **kwargs):
        super(ArrayField, self).__init__(**kwargs)
       
        self.field = field
        self.fields = []

        if length:
            for i in xrange(length):
                self.fields.append(self.field())
        
        self.length = len(self.fields)

    def split_array(self, array, chunksize):
        
        n_chunks = len(array) / chunksize
        
        chunks = []

        for i in xrange(n_chunks):
            chunks.append(array[(i * chunksize):((i + 1) * chunksize)])
        
        return chunks
    
    def toBasic(self):
        a = []

        for field in self.fields:
            a.append(field.toBasic())

        return a

    def __str__(self):
        s = "Array of %d %ss\n" % (len(self.fields), self.field().__class__.__name__)
        s += " %d bytes packed\n  " % (self.size())

        for field in self.fields:
            s += "%s " % (field)

        return s
    
    def append(self, item):
        assert isinstance(item, self.field)
        self.fields.append(item)

    def __len__(self):
        return len(self.fields)

    def __getitem__(self, key):
        return self.fields[key].value

    def __setitem__(self, key, value):
        self.fields[key].value = value

    def get_value(self):
        return [field.value for field in self.fields]
    
    def set_value(self, value):
        self.fields = [self.field(value=v) for v in value]
    
    value = property(get_value, set_value)
    
    def size(self):
        s = 0

        for field in self.fields:
            s += field.size()

        return s

    def unpack(self, buffer):
        
        self.fields = []
        
        count = 0

        while len(buffer) > 0:
            field = self.field()
            self.fields.append(field.unpack(buffer))

            buffer = buffer[field.size():]
            count += 1
            
            if ( self.length > 0 ) and ( count >= self.length ):
                break           

        return self

    def pack(self):
        s = ""
            
        for field in self.fields:
            s += field.pack()

        return s





