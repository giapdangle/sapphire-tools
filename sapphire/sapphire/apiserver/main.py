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

import apiserver

from sapphire.core.version import VERSION
from sapphire.core import settings
from sapphire.core import KVObjectsManager

import os
import sys
import logging
import argparse
import time


def main():
    settings.init()

    logging.info("Sapphire API Server v%s" % (str(VERSION)))
    logging.info("Process ID: %d" % (os.getpid()))
        

    KVObjectsManager.start()

    api_server = apiserver.APIServer()
    api_server.run()

    KVObjectsManager.stop()

    
if __name__ == "__main__":
    main()



