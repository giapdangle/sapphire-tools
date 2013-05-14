#! python
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

import subprocess
import shlex

import os
import sys
import argparse
import signal
import hashlib
import time
import logging

from sapphire.core import settings


class AutomatonScript(object):
    def __init__(self, script):
        self.script = script
        self.proc = None
        self.file_hash = None

    def start(self):        
        self.file_hash = self.get_hash()

        self.proc = subprocess.Popen(shlex.split("python " + self.script),
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, 
                                     stdin=subprocess.PIPE)
        
    def stop(self):
        self.proc.terminate()

    def wait(self):
        self.proc.wait()

    def get_hash(self):
        h = hashlib.new('sha1')

        h.update(open(self.script).read())

        return h.hexdigest()


def sigterm_handler(signum, frame):
    logging.info("Received SIGTERM")
    sys.exit()


if __name__ == "__main__":
    settings.init()

    signal.signal(signal.SIGTERM, sigterm_handler) 

    parser = argparse.ArgumentParser(description='Sapphire Automaton')

    parser.add_argument("-s", "--script", help="Run a script")
    parser.add_argument("-d", "--dir", help="Run a directory of scripts")

    args = vars(parser.parse_args())

    scripts = list()

    if args["dir"]:
        for f in os.listdir(args["dir"]):
            if f.endswith('.py'):
                scripts.append(f)

    elif args["script"]:
        scripts.append(args["script"])

    else:
        logging.info("No scripts specified")
        sys.exit()

    processes = list()

    for script in scripts:
        proc = AutomatonScript(script)
        proc.start()

        logging.info("Running %s" % (proc.script))

        processes.append(proc)

    try:
        while True:
            time.sleep(1.0)

            # if monitoring a directory
            if args["dir"]:
                # check for new files
                for f in os.listdir(args["dir"]):
                    if f.endswith('.py') and f not in [p.script for p in processes]:
                        proc = AutomatonScript(f)
                        proc.start()

                        logging.info("Running %s" % (proc.script))

                        processes.append(proc)               

                remove_list = list()

                # check for removed files
                for proc in processes:
                    if proc.script not in os.listdir(args["dir"]):
                        proc.stop()
                        proc.wait()

                        remove_list.append(proc)

                for proc in remove_list:
                    logging.info("Removing %s" % (proc.script))
                    processes.remove(proc)

            # check for file changes in the current set of processes
            for proc in processes:
                if proc.get_hash() != proc.file_hash:
                    logging.info("Reloading %s" % (proc.script))

                    proc.stop()
                    proc.wait()
                    proc.start()

    except KeyboardInterrupt:
        logging.info("Shutdown requested")

    except SystemExit:
        logging.info("Shutdown requested by SIGTERM")

        for proc in processes:
            proc.stop()



