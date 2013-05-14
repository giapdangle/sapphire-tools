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

from UserDict import DictMixin

import sqlite3
import json
import datetime
import os

from sapphire.core import queryable
from sapphire.core.settings import get_app_dir



class StoreJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, StoreDict):
            return obj.to_dict()
        else:
            return super(StoreJsonEncoder, self).default(obj)


class StoreDict(DictMixin):
    def __init__(self, data=None):
        self.data = data

    def to_dict(self):
        return self.data

    def keys(self):
        return self.data.keys()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def query(self, **kwargs):
        if queryable.query_dict(self.data, **kwargs):
            return self

        return None


class Store(DictMixin):
    def __init__(self, db_path=get_app_dir(), db_name=None):
        self.db_name = db_name
        self.db_path = db_path
        self.db_file = os.path.join(db_path, db_name)

        self.conn = sqlite3.connect(self.db_file)
        self.c = self.conn.cursor()

        self.c.execute('''CREATE TABLE IF NOT EXISTS kv_data (key, value)''')

        self.commit()

    def commit(self):
        self.conn.commit()

    def keys(self):
        self.c.execute('''SELECT key FROM kv_data''')

        return [key[0] for key in self.c.fetchall()]

    def __len__(self):
        self.c.execute('''SELECT COUNT(*) FROM kv_data''')

        return self.c.fetchone()[0]

    def __getitem__(self, key):
        self.c.execute('''SELECT value FROM kv_data WHERE key=?''', (key,))

        value = self.c.fetchone()

        if value == None:
            raise KeyError

        return StoreDict(json.loads(value[0]))

    def __setitem__(self, key, value):
        self.c.execute('''SELECT value FROM kv_data WHERE key=?''', (key,))

        if not self.c.fetchone():
            self.c.execute('''INSERT INTO kv_data VALUES (?,?)''', (key, StoreJsonEncoder().encode(value),))

        else:
            self.c.execute('''UPDATE kv_data SET value=? WHERE key=?''', (StoreJsonEncoder().encode(value), key,))

        self.commit()

    def __delitem__(self, key):
        value = self[key] # raises KeyError if key does not exist

        self.c.execute('''DELETE FROM kv_data WHERE key=?''', (key,))
        self.commit()

    def delete(self):
        os.remove(self.db_file)






