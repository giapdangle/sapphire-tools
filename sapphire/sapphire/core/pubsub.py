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

import gevent

from Queue import Queue
import logging
import uuid
import datetime
import socket

import origin

import redis
import json_codec
from sapphire.core import settings


class Publisher(gevent.Greenlet):
    def __init__(self, object_manager):
        super(Publisher, self).__init__()

        self._queue = Queue()
        self.object_manager = object_manager

        self.client = redis.Redis(settings.BROKER_HOST)

        self._running = True
        self.start()

    def publish_method(self, method, data=None):
        msg = {"method": method,
               "origin_id": origin.id,
               "data": data}

        self._queue.put(json_codec.Encoder().encode(msg))

    def _run(self):
        logging.info("ObjectPublisher started, server: %s" % (settings.BROKER_HOST))

        try:
            while self._running or not self._queue.empty():
                try:
                    o = self._queue.get()

                    self.client.publish("sapphire_objects", o)

                except redis.ConnectionError as e:
                    logging.info("Unable to connect to server, retrying...")
                    logging.error(e)
                    gevent.sleep(4.0)

                except Exception as e:
                    logging.error("ObjectPublisher unexpected exception: %s", str(e))

        except gevent.GreenletExit:
            pass

        except Exception as e:
            logging.critical("ObjectPublisher failed with: %s", str(e))

        logging.info("ObjectPublisher stopped")

    def stop(self):
        self._running = False

        if self._queue.empty():
            self.kill()


class Subscriber(gevent.Greenlet):
    def __init__(self, object_manager):
        super(Subscriber, self).__init__()

        self.client = redis.Redis(settings.BROKER_HOST)
        self.subscriber = self.client.pubsub()
        self.object_manager = object_manager

        self._running = True
        self.start()

    def _process_msg(self, msg):
        # check origin
        if msg["origin_id"] == origin.id:
            # don't process messages from us
            return

        # check methods
        if msg["method"] == "publish":
            self.object_manager.update(msg["data"])

        elif msg["method"] == "event":
            self.object_manager.receive_event(msg["data"])

        elif msg["method"] == "delete":
            self.object_manager.delete(msg["data"]["object_id"])

        elif msg["method"] == "request_objects":
            logging.debug("Received request for objects")
            self.object_manager.publish_objects()

    def _run(self):
        logging.info("ObjectSubscriber started, server: %s" % (settings.BROKER_HOST))

        try:
            while self._running:
                try:
                    self.subscriber.subscribe("sapphire_objects")
                    self.object_manager.request_objects()

                    for msg in self.subscriber.listen():
                        if msg["type"] != "message":
                            continue

                        self._process_msg(json_codec.Decoder().decode(msg["data"]))

                except redis.ConnectionError:
                    logging.info("Unable to connect to server, retrying...")
                    gevent.sleep(4.0)

                except Exception as e:
                    logging.error("ObjectSubscriber unexpected exception: %s", str(e))

        except gevent.GreenletExit:
            pass

        except Exception as e:
            logging.critical("ObjectSubscriber failed with: %s", str(e))

        logging.info("ObjectSubscriber stopped")

    def stop(self):
        self._running = False
        self.kill()

