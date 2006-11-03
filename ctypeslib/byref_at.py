# hack a byref_at function

from ctypes import *

try:
    set
except NameError:
    from sets import Set as set

def _determine_layout():
    result = set()
    for obj in (c_int(), c_longlong(), c_float(), c_double(), (c_int * 32)()):
        ref = byref(obj)
        result.add((c_void_p * 32).from_address(id(ref))[:].index(id(obj)) * sizeof(c_void_p))
    if len(result) != 1:
        raise RuntimeError, "cannot determine byref() object layout"
    return result.pop()

offset = _determine_layout()

__all__ = ["byref_at"]
