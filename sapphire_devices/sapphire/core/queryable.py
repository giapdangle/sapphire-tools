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

def query_dict(d, **kwargs):
    # check for all query (all trumps any other keywords)
    if "all" in kwargs:
        if kwargs["all"]:
            return d

        del kwargs["all"]

    if "expr" in kwargs:
        if not kwargs["expr"](d):    
            return None

        del kwargs["expr"]

    if "contains" in kwargs:
        attr_list = kwargs["contains"]

        # if passed a single string, make it a list
        if isinstance(attr_list, basestring):
            attr_list = [attr_list]
        
        for attr in attr_list:
            # converts keys in dict to string for comparison to work
            if attr not in [str(k) for k in d.keys()]:
                return None

        del kwargs["contains"]

    # if no other kwargs are passed, we have nothing to match against
    if len(kwargs) == 0:
        return None

    # match all kwargs
    for k in kwargs:
        if not k in d or str(d[k]) != str(kwargs[k]):
            return None

    return d