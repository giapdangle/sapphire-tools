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

from query import Query

import logging


class Action(object):
    def __init__(self):
        super(Action, self).__init__()

        self.running = False

    def run(self, event):
        self.running = True

        self.pre(event)
        self.action(event)
        self.post(event)

        self.running = False

    def init(self):
        pass

    def pre(self, event):
        pass

    def action(self, event):
        pass

    def post(self, event):
        pass

class TargetAction(Action):
    def __init__(self, targets=Query(), **kwargs):
        self.targets = targets

        super(TargetAction, self).__init__(**kwargs)

    def run(self, event):
        # run target query
        targets = self.targets()

        # if query came up empty, log and return
        if len(targets) == 0:
            logging.info("%s returned no objects" % (self.targets))

            return

        self.running = True

        self.pre(event)

        for target in targets:
            self.action(event, target)

        self.post(event)

        self.running = False

    def action(self, event, target):
        pass

