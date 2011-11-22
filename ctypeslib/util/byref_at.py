from ctypes import *

def _calc_offset():
    # The definition of PyCArgObject (that is the type of object that
    # byref returns):
    class PyCArgObject(Structure):
        class value(Union):
            _fields_ = [("c", c_char),
                        ("h", c_short),
                        ("i", c_int),
                        ("l", c_long),
                        ("q", c_longlong),
                        ("d", c_double),
                        ("f", c_float),
                        ("p", c_void_p)]
        # Thanks to Lenard Lindstrom for this tip: The sizeof(PyObject_HEAD)
        # is the same as object.__basicsize__.
        _fields_ = [("PyObject_HEAD", c_byte * object.__basicsize__),
                    ("pffi_type", c_void_p),
                    ("tag", c_char),
                    ("value", value),
                    ("obj", c_void_p),
                    ("size", c_int)]

        _anonymous_ = ["value"]

    # additional checks to make sure that everything works as expected

    if sizeof(PyCArgObject) != type(byref(c_int())).__basicsize__:
        raise RuntimeError("sizeof(PyCArgObject) invalid")

    obj = c_int()
    ref = byref(obj)

    argobj = PyCArgObject.from_address(id(ref))

    if argobj.obj != id(obj) or \
       argobj.p != addressof(obj) or \
       argobj.tag != 'P':
        raise RuntimeError("PyCArgObject field definitions incorrect")

    return PyCArgObject.p.offset # offset of the pointer field

_byref_pointer_offset = _calc_offset()

def byref_at(obj, offset):
    """byref_at(cobj, offset) behaves similar this C code:

        (((char *)&obj) + offset)

    In other words, the returned 'reference' points to the address
    of 'cobj' + 'offset'.  'offset' is in units of bytes.
    """
    ref = byref(obj)
    # correct pointer field in the created byref object by 'offset'
    c_void_p.from_address(id(ref) + _byref_pointer_offset).value += offset
    return ref

__all__ = ["byref_at"]
