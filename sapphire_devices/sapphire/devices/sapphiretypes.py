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

from fields import *


SAPPHIRE_TYPE_NONE             = 0
SAPPHIRE_TYPE_BOOL             = 1
SAPPHIRE_TYPE_UINT8            = 2
SAPPHIRE_TYPE_INT8             = 3
SAPPHIRE_TYPE_UINT16           = 4
SAPPHIRE_TYPE_INT16            = 5
SAPPHIRE_TYPE_UINT32           = 6
SAPPHIRE_TYPE_INT32            = 7
SAPPHIRE_TYPE_UINT64           = 8
SAPPHIRE_TYPE_INT64            = 9
SAPPHIRE_TYPE_FLOAT            = 10

SAPPHIRE_TYPE_STRING128        = 40
SAPPHIRE_TYPE_MAC48            = 41
SAPPHIRE_TYPE_MAC64            = 42
SAPPHIRE_TYPE_KEY128           = 43
SAPPHIRE_TYPE_IPv4             = 44
SAPPHIRE_TYPE_STRING512        = 45

SAPPHIRE_TYPE_MISMATCH         = -6

type_registry = {
    SAPPHIRE_TYPE_NONE: None,
    SAPPHIRE_TYPE_BOOL: BooleanField,
    SAPPHIRE_TYPE_UINT8: Uint8Field,
    SAPPHIRE_TYPE_INT8: Int8Field,
    SAPPHIRE_TYPE_UINT16: Uint16Field,
    SAPPHIRE_TYPE_INT16: Int16Field,
    SAPPHIRE_TYPE_UINT32: Uint32Field,
    SAPPHIRE_TYPE_INT32: Int32Field,
    SAPPHIRE_TYPE_UINT64: Uint64Field,
    SAPPHIRE_TYPE_INT64: Int64Field,
    SAPPHIRE_TYPE_FLOAT: FloatField,
    
    SAPPHIRE_TYPE_STRING128: String128Field,
    SAPPHIRE_TYPE_STRING512: String512Field,
    SAPPHIRE_TYPE_MAC48: Mac48Field,
    SAPPHIRE_TYPE_MAC64: Mac64Field,
    SAPPHIRE_TYPE_KEY128: Key128Field,
    SAPPHIRE_TYPE_IPv4: Ipv4Field,
    SAPPHIRE_TYPE_MISMATCH: ErrorField,
}

def getType(t, **kwargs):
    return type_registry[t](**kwargs)


