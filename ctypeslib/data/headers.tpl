# -*- coding: utf-8 -*-
#
# TARGET arch is: __FLAGS__
# POINTER_SIZE is: __POINTER_SIZE__
#

import ctypes
from ctypes import *
c_int128 = c_ubyte*16
c_uint128 = c_int128
if sizeof(ctypes.c_longdouble) == __LONG_DOUBLE_SIZE__:
    c_long_double_t = c_longdouble
else:
    c_long_double_t = c_ubyte*__LONG_DOUBLE_SIZE__
void = None

# if local wordsize is same as target, keep ctypes pointer function.
if sizeof(ctypes.c_void_p) == __POINTER_SIZE__:
    POINTER_T = POINTER
else:
    # required to access _ctypes
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
        # make template
        class _T(_ctypes._SimpleCData,):
            _type_ = '__REPLACEMENT_TYPE_CHAR__'
            _subtype_ = pointee
            def _sub_addr_(self):
                return self.value
            def __repr__(self):
                return '%s(%d)'%(clsname, self.value)
            def contents(self):
                raise TypeError('This is not a ctypes pointer.')
            def __init__(self, **args):
                raise TypeError('This is not a ctypes pointer. It is not instanciable.')
        _class = type('LP_%d_%s'%(__POINTER_SIZE__, clsname), (_T,),{}) 
        return _class
# end headers
