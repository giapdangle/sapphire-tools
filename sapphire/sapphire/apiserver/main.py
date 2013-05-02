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

from sapphire.automaton import *

import apiserver

from sapphire.core.version import VERSION
from sapphire.core.settings import get_app_dir
from sapphire.core import settings
from sapphire.core import KVObjectsManager

import os
import sys
import logging
import argparse


def main():
    settings.init()

    logging.info("Sapphire API Server v%s" % (str(VERSION)))
    logging.info("Process ID: %d" % (os.getpid()))
        
    api_server = apiserver.APIServer()
    
    run()    
    
    
if __name__ == "__main__":
    main()



