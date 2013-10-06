import sys
from inspect import getmembers, isclass
self = sys.modules[__name__]
def _p_type(s):
    return dict(getmembers(self, isclass))[s]    
