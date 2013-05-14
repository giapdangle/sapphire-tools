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


from datetime import datetime

import json

class Encoder(json.JSONEncoder):
    def default(self, obj):
        from kvobject import KVObject
        from kvevent import KVEvent
    
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, KVObject):
            return obj.to_dict()
        elif isinstance(obj, KVEvent):
            return obj.to_dict()    
        else:
            return super(Encoder, self).default(obj)

class Decoder(json.JSONDecoder):
    def decode(self, obj):
        return super(Decoder, self).decode(obj)

