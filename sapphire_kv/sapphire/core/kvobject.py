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
import uuid
import logging
import collections

import origin
from kvevent import KVEvent, SIGNAL_RECEIVED_KVEVENT, SIGNAL_SENT_KVEVENT
import queryable
from pubsub import Publisher, Subscriber
import json_codec
from pydispatch import dispatcher
import threading
import settings




class NotOriginatorException(Exception):
    pass

class KVObject(object):
    def __init__(self, 
                 object_id=None,
                 origin_id=None, 
                 updated_at=None, 
                 collection=None,
                 **kwargs):

        super(KVObject, self).__init__()

        self.__dict__["_lock"] = threading.RLock()
        
        self.__dict__["object_id"] = None
        self.__dict__["origin_id"] = None
        self.__dict__["updated_at"] = None
        self.__dict__["collection"] = None
        self.__dict__["_attrs"] = None

        if object_id:
            self.object_id = object_id
        else:
            self.object_id = str(uuid.uuid4())

        if origin_id:
            self.origin_id = origin_id
        else:
            self.origin_id = origin.id

        if updated_at:
            self.updated_at = updated_at
        else:
            self.updated_at = datetime.utcnow()

        if collection:
            self.collection = collection
        else:
            self.collection = None

        self._attrs = kwargs
        self._pending_events = dict()

    def to_dict(self):
        with self._lock:
            d = {"object_id": self.object_id,
                 "origin_id": self.origin_id,
                 "updated_at": self.updated_at.isoformat(),
                 "collection": self.collection}

            for k, v in self._attrs.iteritems():
                d[k] = v

            return d

    def to_json(self):
        return json_codec.Encoder().encode(self.to_dict())

    def from_dict(self, d):
        with self._lock:
            if "object_id" in d:
                self.object_id = d["object_id"]
                del d["object_id"]

            if "origin_id" in d:
                self.origin_id = d["origin_id"]
                del d["origin_id"]

            if "updated_at" in d:
                self.updated_at = datetime.strptime(d["updated_at"], "%Y-%m-%dT%H:%M:%S.%f")
                del d["updated_at"]

            if "collection" in d:
                self.collection = d["collection"]
                del d["collection"]

            for k, v in d.iteritems():
                self._attrs[k] = v

            return self

    def from_json(self, j):
        return self.from_dict(json_codec.Decoder().decode(j))

    def __str__(self):
        with self._lock:
            if self.collection:
                s = "KVObject:%s.%s" % \
                    (self.collection,
                     self.object_id)
            
            else:
                s = "KVObject:%s" % \
                    (self.object_id)    

            return s

    def query(self, **kwargs):
        d = self.to_dict()

        if queryable.query_dict(d, **kwargs):
            return self

        return None

    def __getattr__(self, key):
        if key == "_lock":
            return self.__dict__[key]

        else:
            with self.__dict__["_lock"]:
                if key in self.__dict__:
                    return self.__dict__[key]
                
                else:
                    return self._attrs[key]

    def __setattr__(self, key, value):
        with self._lock:
            if (key in self.__dict__) or \
               (key.startswith('_')):
                self.__dict__[key] = value

            else:
                self.set(key, value)

    def get(self, key):
        return self._attrs[key]

    def set(self, key, value, timestamp=None):    
        with self._lock:
            # only add a new key if we are the originator of this object
            if (key in self._attrs) or \
               (key not in self._attrs and self.is_originator()):

                # update current value
                self._attrs[key] = value

                if timestamp == None:
                    self.updated_at = datetime.utcnow()
                else:
                    self.updated_at = timestamp 

                # check if object has been published
                if self.object_id in KVObjectsManager._objects:
                    # generate event
                    event = KVEvent(key=key, 
                                    value=value, 
                                    timestamp=datetime.utcnow(),
                                    object_id=self.object_id)

                    # post event to change list (hash, actually)
                    self._pending_events[key] = event

            else:
                raise KeyError

    def update(self, key, value, timestamp=None):    
        with self._lock:
            self._attrs[key] = value

            if timestamp == None:
                self.updated_at = datetime.utcnow()
            else:
                self.updated_at = timestamp

    def publish(self):
        with self._lock:
            if self.is_originator():
                #if self.object_id not in KVObjectsManager._objects:
                logging.debug("Publishing object: %s" % (str(self)))

                # publish to exchange
                try:
                    KVObjectsManager._publisher.publish_method("publish", self)

                except AttributeError:
                    # publisher not running
                    pass

                # add to objects registry
                KVObjectsManager._objects[self.object_id] = self

            self.updated_at = datetime.utcnow()

            # push events to exchange
            try:
                # check if there are events to publish
                if len(self._pending_events) > 0:
                    logging.debug("Pushing events: %s" % (str(self)))
                    KVObjectsManager.send_events(self._pending_events.values())

                    # clear events
                    self._pending_events = dict()

            except AttributeError:
                # publisher not running
                pass

    def _unpublish(self):
        with self._lock:
            if self.is_originator():
                self.delete()

    def delete(self):
        with self._lock:
            if self.is_originator():
                logging.debug("Unpublishing object: %s" % (str(self)))

                try:
                    KVObjectsManager._publisher.publish_method("delete", self)

                except AttributeError:
                    # publisher not running
                    pass
                    
                del KVObjectsManager._objects[self.object_id]

            else:
                raise NotOriginatorException

    def is_originator(self):
        with self._lock:
            return self.origin_id == origin.id


class KVObjectsManager(object):
    _objects = dict()
    _publisher = None
    _subscriber = None
    __lock = threading.RLock()
    
    @staticmethod
    def query(**kwargs):
        with KVObjectsManager.__lock:
            return [o for o in KVObjectsManager._objects.values() if o.query(**kwargs)]

    @staticmethod
    def start():
        with KVObjectsManager.__lock:
        # this lock is not really needed here, since the start() method
        # should only be called one time per process.

            settings.init()

            KVObjectsManager._publisher = Publisher(KVObjectsManager)
            KVObjectsManager._subscriber = Subscriber(KVObjectsManager)

            origin_obj = KVObject(collection="origin")

            import socket
            origin_obj.hostname = socket.gethostname()

            origin_obj.publish()
        

    @staticmethod
    def request_objects():
        logging.debug("Requesting objects...")
        KVObjectsManager._publisher.publish_method("request_objects")

    @staticmethod
    def publish_objects():
        with KVObjectsManager.__lock:
            # publish all objects
            for o in KVObjectsManager._objects.values():
                o.publish()

    @staticmethod
    def unpublish_objects():
        with KVObjectsManager.__lock:
            for o in KVObjectsManager.query(all=True):
                o._unpublish()

    @staticmethod
    def delete(object_id):
        with KVObjectsManager.__lock:
            if object_id in KVObjectsManager._objects:
                obj = KVObjectsManager._objects[object_id]

                logging.debug("Deleted object: %s" % (str(obj)))

                del KVObjectsManager._objects[object_id]
          
    @staticmethod
    def update(data):
        # reconstruct object
        obj = KVObject().from_dict(data)

        with KVObjectsManager.__lock:
            if obj.object_id in KVObjectsManager._objects:
                # update object
                for k, v in obj._attrs.iteritems():
                    KVObjectsManager._objects[obj.object_id].update(k, v)

            else:
                # add new object
                KVObjectsManager._objects[obj.object_id] = obj
                logging.debug("Received new object: %s" % (str(obj)))
        

    @staticmethod
    def receive_events(events):
        # check if events is iterable
        if not isinstance(events, collections.Sequence):
            events = [events]

        events_temp = list()
        for event in events:
            if not isinstance(event, KVEvent):
                event = KVEvent().from_dict(event)

            events_temp.append(event)

        events = events_temp

        with KVObjectsManager.__lock:
            # update objects atomically
            for event in events:
                try:
                    # attach object to event
                    event.kvobject = KVObjectsManager._objects[event.object_id]

                    # update object
                    event.kvobject.update(event.key, event.value, timestamp=event.timestamp)

                except KeyError:
                    pass

        # object lock released, fire events    
        for event in events:
            event.receive()

    @staticmethod
    def send_events(events):
        # check if events is iterable
        if not isinstance(events, collections.Sequence):
            events = [events]

        KVObjectsManager._publisher.publish_method("events", events)

        for event in events:
            event.send()
            
    @staticmethod
    def stop():
        KVObjectsManager.unpublish_objects()

        KVObjectsManager._publisher.stop()
        KVObjectsManager._subscriber.stop()

    @staticmethod
    def join():        
        KVObjectsManager._publisher.join()
        KVObjectsManager._subscriber.join()


def start():
    KVObjectsManager.start()

def stop():
    KVObjectsManager.stop()

def query(**kwargs):
    return KVObjectsManager.query(**kwargs)

