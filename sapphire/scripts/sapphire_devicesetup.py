
from device import Device
import serial
import serial.tools.list_ports
import os
import sys
import struct
from getpass import getpass
import ConfigParser

def get_random_mac():
    # get 7 random bytes
    random_str = os.urandom(7)
    
    # initialize first byte
    # bit 0:
    #  0 = unicast
    #  1 = multicast
    # bit 1:
    #  0 = globally unique (OUI)
    #  1 = locally administered

    # we're setting a unicast locally administered address
    mac = 'A2' + ':' + ''.join([hex(ord(c)).replace('0x', '') + ':' for c in random_str])
    
    return mac[:22] # strip trailing :


def get_short_addr():
    try:
        with open("802_15_4_short.txt", 'r') as f:
            short = int(f.read())
    
    except IOError:
        short = 1  # don't start at 0!!!!

    short += 1
    
    with open("802_15_4_short.txt", 'w+') as f:
        f.write("%d" % (short))
    
    return short

if __name__ == '__main__':
    
    host = sys.argv[1]
    
    dev = Device(host=host)
    dev.scan()

    print ""
    print "Found device at %s" % (dev.host)
    
    
    # open config file
    cfg = ConfigParser.ConfigParser()
    cfg.read('sapphire.ini')
   
    for cfgitem in cfg.items('settings'):
        # program each item to target device
        print "Setting %s to %s" % (cfgitem[0], cfgitem[1])
        
        dev.setConfig(cfgitem[0], cfgitem[1])
    
    # get 802.15.4 MAC
    mac = get_random_mac()
    print "Setting 802.15.4 MAC to %s" % (mac)
    dev.setConfig("mac_addr", mac)

    # get short address
    short = get_short_addr()
    print "Setting 802.15.4 short to %d" % (short)
    dev.setConfig("short_addr", short)
    
    # set security keys
    auth_key = cfg.get('keys', 'wcom_auth_key')
    enc_key = cfg.get('keys', 'wcom_enc_key')
    
    print "Setting wireless authentication key"
    dev.setSecurityKey(0, auth_key)

    print "Setting wireless encryption key"
    dev.setSecurityKey(1, enc_key)
    

    dev.reboot()
    



    
