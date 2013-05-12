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

from events import EventQueue
from sapphire.core import KVObjectsManager, KVObject, KVEvent, settings

import os
import json
import logging
import datetime
import time
import threading

import bottle
from beaker.middleware import SessionMiddleware

API_SERVER_PORT = 8000
API_SERVER_STATIC_ROOT = os.getcwd()

try:
    API_SERVER_PORT = settings.API_SERVER_PORT
    API_SERVER_STATIC_ROOT = settings.API_SERVER_STATIC_ROOT

except:
    pass

INTERFACE = ('0.0.0.0', API_SERVER_PORT)
VERSION = "1.0"

API_PATH = '/api/v0'


def get_collections():
    all_objs = KVObjectsManager.query(all=True)

    collections = [o.collection for o in all_objs]

    # return uniquified list
    return list(set(collections))

def get_items(collection, **query_dict):
    if len(query_dict) > 0:
        items = KVObjectsManager.query(collection=collection, **query_dict)
    else:
        items = KVObjectsManager.query(collection=collection)

    return items

class ApiServerJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, KVObject):
            return obj.to_dict()
        elif isinstance(obj, KVEvent):
            return obj.to_dict()
        else:
            return super(ApiServerJsonEncoder, self).default(obj)


@bottle.get('/')
@bottle.get('/<file>')
def index(file=None):
    if not file:
        return bottle.static_file("index.html", root=API_SERVER_STATIC_ROOT)

    return bottle.static_file(file, root=API_SERVER_STATIC_ROOT)


@bottle.get(API_PATH + '/debug')
def get_debug():
    import objgraph

    return json.dumps(objgraph.typestats())


@bottle.get(API_PATH)
def get_root_collection():
    #return json.dumps(["objects", "events", "queries"])
    return json.dumps(["objects", "events"])

"""
@bottle.get(API_PATH + '/queries')
def get_query():
    # check that there are query parameters
    if len(bottle.request.params) == 0:
        return

    collections = list_databases()
    
    results = list()

    for collection in collections:
        s = ApiStore('/objects', collection)
        
        filtered = [v for v in s.values() if v.query(**bottle.request.params)]

        # run any query parameters
        results.extend(filtered)

    bottle.response.set_header('Content-Type', 'application/json')

    return ApiServerJsonEncoder().encode(results)
"""

@bottle.get(API_PATH + '/objects')
def get_object_list_collection():
    collections = get_collections()

    bottle.response.set_header('Content-Type', 'application/json')

    return json.dumps(collections)


@bottle.get(API_PATH + '/objects/<collection>')
def get_object_collection(collection=None):
    items = get_items(collection, **bottle.request.params)

    if len(items) == 0:
        bottle.abort(404, "Collection not found")

    bottle.response.set_header('Content-Type', 'application/json')

    return ApiServerJsonEncoder().encode(items)


@bottle.get(API_PATH + '/objects/<collection>/<key>')
def get_object_data(collection=None, key=None):
    items = KVObjectsManager.query(collection=collection, object_id=key)

    if len(items) == 0:
        bottle.abort(404, "Object not found")

    bottle.response.set_header('Content-Type', 'application/json')

    return ApiServerJsonEncoder().encode(items[0])


@bottle.put(API_PATH + '/objects/<collection>')
@bottle.put(API_PATH + '/objects/<collection>/<key>')
def put_object_data(collection=None, key=None):
    if key:
        obj = KVObject(object_id=key, collection=collection, **bottle.request.json)

    else:
        obj = KVObject(object_id=collection, **bottle.request.json)

    # publish to exchange
    obj.publish()

@bottle.route(API_PATH + '/objects/<collection>', method='patch')
@bottle.route(API_PATH + '/objects/<collection>/<key>', method='patch')
# NOTE: bottle does not have a shortcut path method, so route is used
def patch_object_data(collection=None, key=None):
    if key:
        items = KVObjectsManager.query(object_id=key, collection=collection)

    else:
        items = KVObjectsManager.query(object_id=collection)

    # if new object
    if len(items) == 0:
        bottle.abort(404, "Object not found")

        """
        if key:
            obj = KVObject(object_id=key, collection=collection, **bottle.request.json)

        else:
            obj = KVObject(object_id=collection, **bottle.request.json)
        """

    else:
        obj = items[0]

        # update attributes
        for k, v in bottle.request.json.iteritems():
            obj.set(k, v)

    # publish to exchange
    obj.publish()


@bottle.delete(API_PATH + '/objects/<collection>')
@bottle.delete(API_PATH + '/objects/<collection>/<key>')
def delete_object(collection=None, key=None):
    if key:
        items = KVObjectsManager.query(object_id=key, collection=collection)

    else:
        items = KVObjectsManager.query(object_id=collection)

    # check if object exists
    if len(items) == 0:
        bottle.abort(404, "Object not found")

    obj = items[0]
    obj.delete()


class SessionReaper(threading.Thread):
    def __init__(self, session):
        super(SessionReaper, self).__init__()

        self.session = session

        self.start()
    
    def run(self):
        while (time.time() - self.session['_accessed_time']) < 300:
            time.sleep(30.0)

        logging.debug("Reaping session: %s" % self.session.id)
        self.session.delete()


@bottle.get(API_PATH + '/events')
def events_collection():
    # get session, this will automatically create the session
    # if it did not exist
    session = bottle.request.environ.get('beaker.session')
    
    # check if there is a query for this session
    if "events" not in session:
        # create reaper for session
        SessionReaper(session)

        # create an event queue
        session["events"] = EventQueue()
    
        logging.debug("Starting new events session: %s" % (session.id))

        # return immediately to send session cookie to client
        #return

    # wait for stuff in queue
    events = [session["events"].get(block=True, timeout=60.0)]

    while not session["events"].empty():
        events.append(session["events"].get())

    # set content type
    bottle.response.set_header('Content-Type', 'application/json')
    
    logging.debug("Pushing events to session: %s" % (session.id))

    return ApiServerJsonEncoder().encode(events)


# these options control the Beaker sessions
session_opts = {
    'session.type': 'memory',
    'session.timeout': 300,
    'session.auto': True
}

class APIServer(object):
    def __init__(self):
        super(APIServer, self).__init__()
    
    def run(self):
        logging.info("APIServer serving on interface: %s port: %d" % (INTERFACE[0], INTERFACE[1]))
        logging.info("Static root: %s" % (API_SERVER_STATIC_ROOT))

        server_app = SessionMiddleware(bottle.app(), session_opts)
        #bottle.run(app=server_app, host=INTERFACE[0], port=INTERFACE[1], server='paste', quiet=settings.API_SERVER_QUIET)

        # NOTE: if daemon_threads is False, the server will tend to not terminate when requested
        bottle.run(app=server_app, host=INTERFACE[0], port=INTERFACE[1], server='paste', daemon_threads=True)
        
    

