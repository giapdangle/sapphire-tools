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

from datetime import timedelta, datetime

from sapphire.core import KVEvent
import macro


class Trigger(object):
    def __init__(self, source=None):
        super(Trigger, self).__init__()

        self.source_query = source

    def init(self):
        pass

    def _eval(self, event):
        if self.source_query:
            if event.object_id not in [o.object_id for o in self.source_query()]:
                return False
        
        return self.condition(event)

    def condition(self, event):
        pass

class IntervalTrigger(Trigger):
    def __init__(self, 
                 weeks=0,
                 days=0,
                 hours=0,
                 minutes=0,
                 seconds=0,
                 run_now=False,
                 run_once=False,
                 **kwargs):

        super(IntervalTrigger, self).__init__(**kwargs)

        self.weeks = weeks
        self.days = days
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        self.run_now = run_now
        self.run_once = run_once
        self._job = None

    def _fire(self):
        now = datetime.utcnow()
        event = KVEvent(key="__interval_trigger",
                        value=id(self))

        event.receive()

        if self.run_once:
            macro._sched.unschedule_job(self._job)

    def init(self):
        self._job = macro._sched.add_interval_job(self._fire, 
                                                  weeks=self.weeks, 
                                                  days=self.days, 
                                                  hours=self.hours, 
                                                  minutes=self.minutes, 
                                                  seconds=self.seconds)

        if self.run_now:
            self._fire()

        self.has_run = False

    def condition(self, event):
        if event.key != "__interval_trigger":
            return False

        if event.value != id(self):
            return False

        return True



