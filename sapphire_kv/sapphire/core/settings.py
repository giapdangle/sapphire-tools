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
import json
import appdirs
import logging


def get_app_dir():
    d = appdirs.user_data_dir("sapphire", "SapphireOpenSystems")

    if not os.path.exists(d):
        os.makedirs(d)
    
    return d

_log_levels = {"debug": logging.DEBUG,
               "info": logging.INFO,
               "warning": logging.WARNING,
               "error": logging.ERROR,
               "critical": logging.CRITICAL}
    
##################
# DEFAULT CONFIG #
##################
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_HOST = "localhost"
LOG_FILENAME = os.path.splitext(os.path.split(sys.argv[0])[1])[0] + ".log"
LOG_PATH = get_app_dir()
LOG_LEVEL = "info"


###################
# INTERVAL CONFIG #
###################
_SETTINGS_PATH = None
_LOG_FILE_PATH = None
_LOG_LEVEL = logging.INFO
_INITIALIZED = False


def load_config(path=None):
    if not path:
        # try to automatically load a config file

        # start with CWD
        try:
            load_config("sapphire.conf")

        except IOError:
            
            # then try app directory
            try:
                load_config(os.path.join(get_app_dir(), "sapphire.conf"))

            except IOError:
                pass

    else:
        f = open(path, 'r')

        global _SETTINGS_PATH
        _SETTINGS_PATH = path

        try:
            config = json.loads(f.read())
            
            mod_dict = globals()
            for k, v in config.iteritems():
                mod_dict[k] = v

        except ValueError:
            raise

        f.close()


def init_logging():
    # set up logging
    dt_format = '%Y-%m-%dT%H:%M:%S'

    global _LOG_FILE_PATH
    _LOG_FILE_PATH = os.path.join(LOG_PATH, LOG_FILENAME)

    global _LOG_LEVEL
    _LOG_LEVEL = _log_levels[LOG_LEVEL]

    # set up file handler
    logging.basicConfig(filename=_LOG_FILE_PATH, 
                        format='%(asctime)s >>> %(levelname)s %(message)s', 
                        datefmt=dt_format, 
                        level=_LOG_LEVEL)

    # add a console handler to print to the console
    console = logging.StreamHandler()
    console.setLevel(_LOG_LEVEL)
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s', datefmt=dt_format)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def init():
    global _INITIALIZED
    
    if _INITIALIZED:
        return

    try:
        load_config()
        init_logging()

        global _SETTINGS_PATH

        if _SETTINGS_PATH:
            logging.info("Loaded config from: %s" % (_SETTINGS_PATH))

        else:
            logging.info("Loaded default config")

        logging.info("Log level: '%s' to file: %s" % (LOG_LEVEL, _LOG_FILE_PATH))

    except ValueError as e:
        init_logging()

        logging.error("Parse error in config file: %s" % (e))

    _INITIALIZED = True




