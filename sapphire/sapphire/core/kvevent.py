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

import json
from datetime import datetime

import origin

import json_codec

from pydispatch import dispatcher
import threading

SIGNAL_RECEIVED_KVEVENT = "signal_received_kvevent"
SIGNAL_SENT_KVEVENT = "signal_sent_kvevent"


class KVEvent(object):
    def __init__(self, 
                 key=None, 
                 value=None, 
                 timestamp=None, 
                 object_id=None, 
                 origin_id=origin.id):

        self.__dict__["_lock"] = threading.RLock()

        self.__dict__["key"] = key
        self.__dict__["value"] = value
        self.__dict__["timestamp"] = timestamp
        self.__dict__["object_id"] = object_id
        self.__dict__["origin_id"] = origin_id
        self.__dict__["kvobject"] = None

    def __getattr__(self, key):
        if key == "_lock":
            return self.__dict__[key]

        else:
            with self.__dict__["_lock"]: 
                if key == self.__dict__["key"]:
                    return self.__dict__["value"]

                else:
                    return self.__dict__[key]

    def __setattr__(self, key, value):
        with self._lock:
            if key == self.key:
                self.value = value

            else:
                self.__dict__[key] = value

    def __str__(self):
        with self._lock:
            s = "Object:%20s Key:%16s Value:%16s Timestamp:%16s" % \
                (self.object_id,
                 self.key,
                 self.value,
                 self.timestamp)

        return s

    def to_dict(self):
        with self._lock:
            d = {"object_id": self.object_id,
                 "origin_id": self.origin_id,
                 "key": self.key,
                 "value": self.value,
                 "timestamp": self.timestamp.isoformat()}

        return d

    def to_json(self):
        with self._lock:
            return json_codec.Encoder().encode(self.to_dict())

    def from_dict(self, d):
        with self._lock:
            self.object_id = d["object_id"]
            self.origin_id = d["origin_id"]
            self.key = d["key"]
            self.value = d["value"]
            self.timestamp = datetime.strptime(d["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")

        return self

    def from_json(self, j):
        with self._lock:
            return self.from_dict(json_codec.Decoder().decode(j))

    def send(self):
        with self._lock:
            # send dispatcher signal
            dispatcher.send(signal=SIGNAL_SENT_KVEVENT, event=self)

    def receive(self):
        with self._lock:
            # send dispatcher signal
            dispatcher.send(signal=SIGNAL_RECEIVED_KVEVENT, event=self)

    def private(self):
        with self._lock:
            return self.key.startswith('_')



