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

import os

from sapphire.buildtools import core

class FirmwareNotFoundException(Exception):
    def __init__(self, value = None):
        self.value = value
    
    def __str__(self):
        return repr(self.value)


def get_firmware(fwid):
    try:
        builder = core.get_project_builder(fwid=fwid)    

    except core.ProjectNotFoundException:
        builder = core.get_project_builder(proj_name=fwid)

    return os.path.join(builder.target_dir, "firmware.bin")

    