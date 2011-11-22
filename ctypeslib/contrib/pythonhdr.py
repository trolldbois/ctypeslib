# This code was contributed by Lenard Lindstrom, see
# http://sourceforge.net/tracker/?func=detail&aid=1619889&group_id=71702&atid=532156

# pythonhdr.py module
# Compatible with Python 2.3 and up, ctypes 1.0.1.

"""Python Application Programmer's Interface (Partial)

For information on functions and types in this module refer to the "Python/C
API Reference Manual" in the Python documentation.

Any exception raised by an API function is propagated. There is no need to
check the return type for an error. Where a PyObject * argument is expected
just pass in a Python object. Integer arguments will accept a Python int or
long. Other arguments require the correct ctypes type. The same relationships
apply to function return types. Py_ssize_t is available for Python 2.5 and up.
It defaults to c_int for earlier versions. Finally, a FILE_ptr type is defined
for FILE *.

Be aware that the Python file api funtions are an implementation detail that
may change.

It is safe to do an import * from this module.


An example where a Python string is copied to a ctypes character array:

>>> from pythonhdr import PyString_AsStringAndSize, Py_ssize_t
>>> from ctypes import c_char, byref, pointer, memmove, addressof
>>>
>>> char_array10 = (c_char * 10)()
>>> char_array10.raw
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
>>> py_str10 = "x" * 10
>>> py_str10
'xxxxxxxxxx'
>>>
>>> cp = pointer(c_char())
>>> sz = Py_ssize_t(0)
>>> PyString_AsStringAndSize(s, byref(cp), byref(sz))
0
>>> memmove(addressof(char_array10), cp, sz.value)
8111688
>>> del cp
>>> char_array10.raw
'xxxxxxxxxx'
"""

import ctypes


# Figure out Py_ssize_t (PEP 353).
#
# Py_ssize_t is only defined for Python 2.5 and above, so it defaults to
# ctypes.c_int for earlier versions.
#
if hasattr(ctypes.pythonapi, 'Py_InitModule4'):
    Py_ssize_t = ctypes.c_int
elif hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
    Py_ssize_t = ctypes.c_int64
else:
    raise TypeError("Cannot determine type of Py_ssize_t")

# Declare PyObject, allowing for additional Py_TRACE_REFS fields.
#
# By definition PyObject contains only PyObject_HEAD. Within Python it is
# accessible as the builtin 'object'. Whether or not the interpreter was built
# with Py_TRACE_REFS can be decided by checking object's size, its
# __basicsize__ attribute.
#
# Object references in Py_TRACE_REFS are not declared as ctypes.py_object to
# avoid reference counting. A PyObject pointer is used instead of a void
# pointer because technically the two types need not be the same size
# or alignment.
#
# To discourage access of the PyObject fields they are mangled into invalid
# Python identifiers. Only valid identifier characters are used in the
# unlikely event a future Python has a dictionary optimised for identifiers.
#
def make_PyObject(with_trace_refs=False):
    global PyObject
    class PyObject(ctypes.Structure):

        """This root object structure defines PyObject_HEAD.

        To declare other Python object structures simply subclass PyObject and
        provide a _fields_ attribute with the additional fields of the
        structure. Direct construction of PyObject instances is not supported.
        Instance are created with the from_address method instead. These
        instances should be deleted when finished.


        An usage example with the Python float type:

        >>> from pythonhdr import PyObject
        >>> from ctypes import c_double
        >>>
        >>> class PyFloatObject(PyObject):
        ...     _fields_ = [("ob_fval", c_double)]
        ...
        >>> d = 3.14
        >>> d
        3.1400000000000001
        >>>
        >>> e = PyFloatObject.from_address(id(d)).ob_fval
        >>> e
        3.1400000000000001
        """

        def __new__(cls, *args, **kwds):
            raise NotImplementedError(
                "Direct creation of %s instances is not supported" %
                cls.__name__)

    if with_trace_refs:
        optional_fields = [('9_ob_next', ctypes.POINTER(PyObject)),
                           ('9_ob_prev', ctypes.POINTER(PyObject))]
    else:
        optional_fields = []
    regular_fields = [('9ob_refcnt', Py_ssize_t),
                      ('9ob_type', ctypes.POINTER(PyObject))]
    PyObject._fields_ = optional_fields + regular_fields

make_PyObject()
if object.__basicsize__ > ctypes.sizeof(PyObject):
    make_PyObject(True)

assert ctypes.sizeof(PyObject) == object.__basicsize__, (
       "%s.%s declaration is inconsistent with actual PyObject size" %
       (__name__, PyObject.__name__))

# Buffer Protocol API.
#
PyObject_AsCharBuffer = ctypes.pythonapi.PyObject_AsCharBuffer
PyObject_AsCharBuffer.restype = ctypes.c_int
PyObject_AsCharBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(
                                      ctypes.POINTER(ctypes.c_char)),
                                  ctypes.POINTER(Py_ssize_t)]

PyObject_AsReadBuffer = ctypes.pythonapi.PyObject_AsReadBuffer
PyObject_AsReadBuffer.restype = ctypes.c_int
PyObject_AsReadBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(ctypes.c_void_p),
                                  ctypes.POINTER(Py_ssize_t)]

PyObject_CheckReadBuffer = ctypes.pythonapi.PyObject_CheckReadBuffer
PyObject_CheckReadBuffer.restype = ctypes.c_int
PyObject_CheckReadBuffer.argtypes = [ctypes.py_object]

PyObject_AsWriteBuffer = ctypes.pythonapi.PyObject_AsWriteBuffer
PyObject_AsWriteBuffer.restype = ctypes.c_int
PyObject_AsWriteBuffer.argtypes = [ctypes.py_object,
                                   ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.POINTER(Py_ssize_t)]

# Buffer Object API.
#
Py_END_OF_BUFFER = -1

PyBuffer_FromReadWriteObject = ctypes.pythonapi.PyBuffer_FromReadWriteObject
PyBuffer_FromReadWriteObject.restype = ctypes.py_object
PyBuffer_FromReadWriteObject.argtypes = [ctypes.py_object,
                                         Py_ssize_t,
                                         Py_ssize_t]

PyBuffer_FromMemory = ctypes.pythonapi.PyBuffer_FromMemory
PyBuffer_FromMemory.restype = ctypes.py_object
PyBuffer_FromMemory.argtypes = [ctypes.c_void_p,
                                Py_ssize_t]

PyBuffer_FromReadWriteMemory = ctypes.pythonapi.PyBuffer_FromReadWriteMemory
PyBuffer_FromReadWriteMemory.restype = ctypes.py_object
PyBuffer_FromReadWriteMemory.argtypes = [ctypes.c_void_p,
                                         Py_ssize_t]

PyBuffer_New = ctypes.pythonapi.PyBuffer_New
PyBuffer_New.restype = ctypes.py_object
PyBuffer_New.argtypes = [Py_ssize_t]

# File API.
#
# A FILE_ptr type is used instead of c_void_p because technically a pointer
# to structure can have a different size or alignment to a void pointer.
#
# Note that the file api may change.
#
try:
    class FILE(ctypes.Structure):
        pass
    FILE_ptr = ctypes.POINTER(FILE)

    PyFile_FromFile = ctypes.pythonapi.PyFile_FromFile
    PyFile_FromFile.restype = ctypes.py_object
    PyFile_FromFile.argtypes = [FILE_ptr,
                                ctypes.c_char_p,
                                ctypes.c_char_p,
                                ctypes.CFUNCTYPE(ctypes.c_int, FILE_ptr)]

    PyFile_AsFile = ctypes.pythonapi.PyFile_AsFile
    PyFile_AsFile.restype = FILE_ptr
    PyFile_AsFile.argtypes = [ctypes.py_object]
except AttributeError:
    del FILE_ptr

# Cell API.
#
PyCell_New = ctypes.pythonapi.PyCell_New
PyCell_New.restype = ctypes.py_object
PyCell_New.argtypes = [ctypes.py_object]

PyCell_Get = ctypes.pythonapi.PyCell_Get
PyCell_Get.restype = ctypes.py_object
PyCell_Get.argtypes = [ctypes.py_object]

PyCell_Set = ctypes.pythonapi.PyCell_Set
PyCell_Set.restype = ctypes.c_int
PyCell_Set.argtypes = [ctypes.py_object,
                       ctypes.py_object]

# String API.
#
PyString_AsStringAndSize = ctypes.pythonapi.PyString_AsStringAndSize
PyString_AsStringAndSize.restype = ctypes.c_int
PyString_AsStringAndSize.argtypes = [ctypes.py_object,
                                     ctypes.POINTER(
                                         ctypes.POINTER(ctypes.c_char)),
                                     ctypes.POINTER(Py_ssize_t)]

# Thread State API.
#
PyThreadState_SetAsyncExc = ctypes.pythonapi.PyThreadState_SetAsyncExc
PyThreadState_SetAsyncExc.restype = ctypes.c_int
PyThreadState_SetAsyncExc.argtypes = [ctypes.c_long,
                                      ctypes.py_object]

# OS API.
#
PyOS_InputHook = ctypes.CFUNCTYPE(ctypes.c_int).in_dll(ctypes.pythonapi,
                                                       'PyOS_InputHook')

# Memory API.
#
PyMem_Malloc = ctypes.pythonapi.PyMem_Malloc
PyMem_Malloc.restype = ctypes.c_void_p
PyMem_Malloc.argtypes = [ctypes.c_size_t]

PyMem_Realloc = ctypes.pythonapi.PyMem_Realloc
PyMem_Realloc.restype = ctypes.c_void_p
PyMem_Realloc.argtypes = [ctypes.c_void_p,
                          ctypes.c_size_t]

PyMem_Free = ctypes.pythonapi.PyMem_Free
PyMem_Free.restype = None
PyMem_Free.argtypes = [ctypes.c_void_p]


# Clean up so dir(...) only shows what is exported.
#
del ctypes, make_PyObject, FILE
