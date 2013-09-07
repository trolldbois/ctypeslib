# -*- coding: utf-8 -*-
#
# TARGET arch is: __ARCH__
# POINTER_SIZE is: __POINTER_SIZE__
#

## DEBUG
import ctypes
__POINTER_SIZE__ = 4
__REPLACEMENT_TYPE__ = ctypes.c_int32
__REPLACEMENT_TYPE_CHAR__ = 'I'
## DEBUG

import ctypes
class c_int128(ctypes.Structure):
    _fields_ = [('a', ctypes.c_int64), ('b', ctypes.c_int64)]
    _packed_ = True

c_uint128 = c_int128

# if local wordsize is same as target, keep ctypes pointer function.
if ctypes.sizeof(ctypes.c_void_p) == __POINTER_SIZE__:
    POINTER_T = ctypes.POINTER
else:
    # required to access _ctypes
    from ctypes import *
    import _ctypes
    # Emulate a pointer class using the approriate c_int32/c_int64 type
    # The new class should have :
    # ['__module__', 'from_param', '_type_', '__dict__', '__weakref__', '__doc__']
    def POINTER_T(pointee):
        # a pointer should have the same length as LONG
        fake_ptr_base_type = __REPLACEMENT_TYPE__ 
        # specific case for c_void_p
        if pointee is None: # VOID pointer type. c_void_p.
            pointee = type(None) # ctypes.c_void_p # ctypes.c_ulong
            clsname = 'c_void'
        else:
            clsname = pointee.__name__
        _class = type('ctypeslib.LP_%d_%s'%(__POINTER_SIZE__, clsname),
                (_ctypes._SimpleCData,),
                { '_type_': __REPLACEMENT_TYPE_CHAR__, 
                  '_subtype_': pointee, 
                  '_sub_addr_': lambda x: x.value, 
                  '__repr__': lambda x: '%s(%d)'%(clsname,x.value),
                  'contents': lambda x: TypeError('This is not a ctypes pointer'),
                  }) 
                  #, '__str__': lambda x: str(x.value)
        _class._sub_addr_ = property(_class._sub_addr_)
        return _class


