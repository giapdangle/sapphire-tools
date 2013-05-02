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

import collections
import logging

from datetime import datetime
from apscheduler.scheduler import Scheduler

from sapphire.core import SIGNAL_RECEIVED_KVEVENT

from pydispatch import dispatcher
import gevent

_sched = None



class Macro(object):
    _macros = list()

    @staticmethod
    def receive_event(event):
        for m in Macro._macros:
            m._run(event)

    def __init__(self, triggers=list(), actions=list()):
        super(Macro, self).__init__()

        if not isinstance(triggers, collections.Iterable):
            triggers = [triggers]
        
        if not isinstance(actions, collections.Iterable):
            actions = [actions]

        self.triggers = triggers
        self.actions = actions

        self.last_run = None
        self.running = False

        self._macros.append(self)

    def _setup(self):
        self.running = True

        for action in self.actions:
            action.init()

        # init triggers last so that interval triggers with
        # run_now set will be able to trigger actions
        for trigger in self.triggers:
            trigger.init()

    def _shutdown(self):
        self.running = False

    def _run(self, event):
        if not self.running:
            return

        self.last_run = datetime.utcnow()

        for trigger in self.triggers:
            try:
                if not trigger._eval(event):
                    continue
                
                logging.debug("Macro: %s triggered by: %s" % (self, trigger))

                for action in self.actions:
                    # check if action is already running
                    if action.running:
                        logging.debug("Action: %s already running" % (action))
                        continue

                    try:
                        logging.debug("Running action: %s" % (action))
                        
                        gevent.spawn(action._run, event)

                    except Exception as e:
                        logging.error("Action: %s raised exception: %s" % (str(action), str(e)))

                # we match only one of the triggers
                return

            except Exception as e:
                logging.error("Trigger: %s raised exception: %s" % (str(trigger), str(e)))


dispatcher.connect(Macro.receive_event, signal=SIGNAL_RECEIVED_KVEVENT)

def start():
    sched_logger = logging.getLogger("apscheduler")
    sched_logger.setLevel(logging.WARNING)

    global _sched
    _sched = Scheduler()
    _sched.start()

    for macro in Macro._macros:
        macro._setup()

def stop():
    for macro in Macro._macros:
        macro._shutdown()

    try:
        _sched.shutdown()
        
    except:
        pass



    
