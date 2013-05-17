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

import threading

from sapphire.core import KVObjectsManager
from sapphiredevices.devices import Device, DeviceUnreachableException
from sapphiredevices.devices import netscan

import traceback
import sys

import cmd2 as cmd

from pyparsing import *


# set up query parse grammar
query_item   = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\()*+,-./:;<>?@[\\]^_`{|}~'
equals       = Suppress('=')
query_param  = Word(query_item).setResultsName('param')
query_value  = Word(query_item).setResultsName('value')
query_expr   = Group(query_param + equals + query_value)
query_list   = ZeroOrMore(query_expr)

def make_query_dict(line):
    q = query_list.parseString(line)
    
    d = dict()

    for i in q:
        d[i.param] = i.value
    
    return d

class SapphireConsole(cmd.Cmd):
   
    prompt = '(Nothing): '
    
    ruler = '-'
    
    def __init__(self, targets=[]):
        self.targets = targets

        cmd.Cmd.__init__(self)
    
    def cmdloop(self):
        SapphireConsole.next_cmd = None
        
        cmd.Cmd.cmdloop(self)
        
        return SapphireConsole.next_cmd
    
    def do_scan(self, line):
        netscan.scan()
    
    def query(self, line):
        if line == 'all':
            devices = [o for o in KVObjectsManager.query(all=True) if isinstance(o, Device)]
        
        else:
            qdict = make_query_dict(line)
            devices = [o for o in KVObjectsManager.query(**qdict) if isinstance(o, Device)]
        
        return devices
    
    def init_shell(self, query):
        # set up next command shell
        if len(self.targets) > 0:
            target_type = type(self.targets[0])

            # check if all targets are the same type
            for target in self.targets:
                if type(target) != target_type:
                    target_type = Device
                    break

            SapphireConsole.next_cmd = makeConsole(targets=self.targets, 
                                       device=target_type())

            #SapphireConsole.next_cmd.prompt = "(%s): " % (query)
            SapphireConsole.next_cmd.prompt = "(%3d devices): " % (len(self.targets))

        else:
            # no targets, set up empty shell
            SapphireConsole.next_cmd = SapphireConsole()

            SapphireConsole.next_cmd.prompt = "(Nothing): "

    def do_query(self, line):
        devices = self.query(line)

        if devices:
            print "Found %d devices" % (len(devices))

            for device in devices:
                print device.who()

    def do_select(self, line):
        # query for targets
        devices = self.query(line)
        
        self.targets = devices

        self.init_shell(line)
        
        print "Selected %d devices" % (len(self.targets))

        return True
    
    def do_add(self, line):
        # query for targets
        devices = self.query(line)
        
        for device in devices:
            self.targets.append(device)

        self.init_shell(line)
        
        print "Selected %d devices" % (len(self.targets))

        return True

    def do_remove(self, line):
        # query for targets
        devices = self.query(line)
        
        for device in devices:
            self.targets.remove(device)

        self.init_shell(line)
        
        print "Selected %d devices" % (len(self.targets))

        return True

    def do_who(self, line):
        for target in self.targets:
            print target.who()


cli_template = """
    def do_$fname(self, line):
        for target in self.targets:
            sys.stdout.write('%s@%5d: ' % (target.name.ljust(24), target.short_addr))

            try:
                print target.cli_$fname(line)
            
            except DeviceUnreachableException as e:
                print 'Error:%s from %s' % (e, target.host) 

            except Exception as e:
                print 'Error:%s from %s' % (e, target.host) 
                traceback.print_exc()

"""

def makeConsole(targets=[], device=None):
    if not device:
        try:
            device = targets[0]
        except:
            pass

    # get command line function listing from device
    cli_funcs = device.get_cli()
    
    s = "class aConsole(SapphireConsole):\n"

    for fname in cli_funcs:
        s += cli_template.replace('$fname', fname)

    exec(s)

    return aConsole(targets=targets)


if __name__ == '__main__':
    
    try:
        host = sys.argv[1]
        sys.argv[1] = '' # prevents an unknown syntax error in the command loop
        
        try:
            print "Connecting to %s" % host
            
            d = Device(host=host)
            d.scan()

            print d
            
            c = makeConsole(targets=[d])
            c.cmdloop()
            
        except:
            print "*** Unable to connect to %s" % host    
            raise 
    
    except IndexError:
        
        print "Searching for devices..."

        all_devices = netscan.scan()
        
        for d in all_devices:
            print "Found: %d" % (d.device_id)        


        threads = list()

        for device in all_devices:
            def scan_func(d):            
                print "Scanning: %d" % (d.device_id)

                try:
                    d.scan()
                    
                    print "Done: %d" % (d.device_id)

                except DeviceUnreachableException:
                    print "!!! Device %d unreachable" % (d.device_id)

            t = threading.Thread(target=scan_func, args=[device])
            t.start()

            threads.append(t)

        for t in threads:
            t.join()

        

        c = SapphireConsole()

        while c != None:
            c = c.cmdloop()
            
        


