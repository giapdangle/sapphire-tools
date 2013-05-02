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

import sys
import os
import socket
from sapphire.core import settings

import macro
from sapphire.core import KVObjectsManager, KVObject
from sapphire.core import origin

import logging
import signal
import time


# Change stdout to automatically encode to utf8.
# Without this, running this in a subprocess and directing
# stdout to subprocess.PIPE will result in unicode errors
# when doing something as inoccuous as "print".
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout) 


#def sigterm_handler(signum, frame):
def sigterm_handler():
    logging.info("Received SIGTERM")
    #gevent.shutdown()
    sys.exit()

def run(script_name=None):
    settings.init()

    if not script_name:
        script_name = sys.argv[0]
        
    script_control = KVObject(collection="automaton")
    script_control.running = True
    script_control.hostname = socket.gethostname()
    script_control.scriptname = script_name

    logging.info("Starting automaton script: %s" % (script_name))
    logging.info("Process ID: %d" % (os.getpid()))
    logging.info("Origin ID: %s" % (origin.id))

    try:
        KVObjectsManager.start()

        script_control.publish()

        # wait some time for objects to arrive...
        # this is not critical, but helps a bit for macros that run on startup
        #time.sleep(2.0)

        # main script control loop
        while True:

            macro.start()

            while script_control.running:
                time.sleep(1.0)

            macro.pause()

            logging.info("Automaton stopped by script control")

            while not script_control.running:
                time.sleep(1.0)                              

            logging.info("Automaton started by script control")

    except KeyboardInterrupt:
        logging.info("Shutdown requested")

    except SystemExit:
        logging.info("Shutdown requested by signal SIGTERM")

    macro.stop()

    KVObjectsManager.stop()
    KVObjectsManager.join()


if __name__ == "__main__":
    run()

