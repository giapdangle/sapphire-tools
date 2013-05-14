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

from sapphire.core import KVObjectsManager

class Query(object):
    def __init__(self, **kwargs):
        super(Query, self).__init__()

        self.criteria = kwargs

    def __str__(self):
        s = "Query: %s" % (self.criteria)
        return s

    def __call__(self):
        return KVObjectsManager.query(**self.criteria)
