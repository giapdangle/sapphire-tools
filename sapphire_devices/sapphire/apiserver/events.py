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

from Queue import Queue
import weakref

from sapphire.core import SIGNAL_RECEIVED_KVEVENT, SIGNAL_SENT_KVEVENT

from pydispatch import dispatcher

MAX_QUEUED_EVENTS = 512

class EventQueue(Queue):

    _event_q_list = weakref.WeakSet()

    def __init__(self, **kwargs):
        # Queue is an old-style class
        Queue.__init__(self, **kwargs)

        EventQueue._event_q_list.add(self)


def process_event(event):
    # don't process private events
    if event.private():
        return

    for q in EventQueue._event_q_list:
        q.put(event)

        # limit size of queue
        if q.qsize() > MAX_QUEUED_EVENTS:
            q.get()


dispatcher.connect(process_event, signal=SIGNAL_RECEIVED_KVEVENT)
dispatcher.connect(process_event, signal=SIGNAL_SENT_KVEVENT)






