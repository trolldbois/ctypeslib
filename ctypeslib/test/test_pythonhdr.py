# This code was contributed by Lenard Lindstrom, see
# http://sourceforge.net/tracker/?func=detail&aid=1619889&group_id=71702&atid=532156

# test_pythonhdr.py program.
# Compatible with Python 2.3 and up, ctypes 1.0.1.

"""pythonhdr module unit test program."""

from ctypes import *
from ctypeslib.contrib.pythonhdr import *
import unittest, sys
from ctypeslib.test import is_resource_enabled
from thread import start_new_thread, allocate_lock
from array import array

from sys import getrefcount as grc


class Pythonhdr_TestCase(unittest.TestCase):

    def test_Py_ssize_t(self):
        if sys.version_info < (2,5,0):
            self.failUnless(Py_ssize_t is c_int)
        else:
            self.failUnlessEqual(sizeof(Py_ssize_t), sizeof(c_size_t))
    
    def test_PyObject(self):
        self.failUnlessRaises(NotImplementedError, PyObject, None)
        class PyFloatObject(PyObject):
            _fields_ = [("ob_fval", c_double)]
        self.failUnlessEqual(sizeof(PyFloatObject), float.__basicsize__,
                             "Alignment, float changed"
                             "or Py_TRACE_REFs not seen.")
        d = 100.0
        rcdt = grc(float)
        try:
            fo = PyFloatObject.from_address(id(d))
            self.failUnlessEqual(grc(float), rcdt)
            e = fo.ob_fval
        finally:
            del fo
        self.failUnlessEqual(d, e)
        del e
        self.failUnlessEqual(grc(float), rcdt)

    def test_buffer_protocol(self):
        o = 'abcdefghij'
        cp = pointer(c_char())
        sz = Py_ssize_t(0)
        try:
            PyObject_AsCharBuffer(o, byref(cp), byref(sz))
            self.failUnlessEqual(sz.value, len(o))
            self.failUnlessEqual(cp[0], o[0])
        finally:
            del cp
        o = c_double(0.0)
        vp = c_void_p()
        self.failUnless(PyObject_CheckReadBuffer(o))
        try:
            sz.value = 0
            PyObject_AsReadBuffer(o, byref(vp), byref(sz))
            self.failUnlessEqual(sz.value, sizeof(o))
            self.failUnlessEqual(addressof(o), vp.value)
        finally:
            del vp
        vp = c_void_p()
        try:
            sz.value = 0
            PyObject_AsWriteBuffer(o, byref(vp), byref(sz))
            self.failUnlessEqual(sz.value, sizeof(o))
            self.failUnless(addressof(o), vp.value)
        finally:
            del vp

    def test_buffer(self):
        o = create_string_buffer('abcdefghij')
        try:
            b = None
            b = PyBuffer_FromReadWriteObject(o, 0, Py_END_OF_BUFFER)
            self.failUnlessEqual(b[0], o[0])
        finally:
            del b
        try:
            b = None
            b = PyBuffer_FromMemory(o, sizeof(o))
            self.failUnlessEqual(len(b), len(o))
            self.failUnless(b[0], o[0])
        finally:
            del b
        try:
            b = None
            b = PyBuffer_FromReadWriteMemory(o, sizeof(o))
            self.failUnlessEqual(len(b), len(o))
            self.failUnless(b[0], o[0])
        finally:
            del b
        b = PyBuffer_New(10)
        self.failUnlessEqual(len(b), 10)

    def test_file(self):
        closefn = CFUNCTYPE(c_int, FILE_ptr)
        def close(f):
            return 1
        close_callback = closefn(close)
        try:
            path = sys.executable
            f = file(path, 'rb')
            try:
                fp = PyFile_AsFile(f)
                self.failUnless(fp)
                g = PyFile_FromFile(fp, path, 'rb', close_callback)
                fno = g.fileno()
                del g
                self.failUnlessEqual(f.fileno(), fno)
            finally:
                f.close()
        except (NameError, IOError):
            pass

    def test_cell(self):
        o = 1000
        c = PyCell_New(o)
        self.failUnless(PyCell_Get(c) is o)
        p = 1001
        PyCell_Set(c, p)
        self.failUnless(PyCell_Get(c) is p)

    def test_string(self):
        s = 'abcdefghij'
        cp = pointer(c_char())
        sz = Py_ssize_t(0)
        try:
            PyString_AsStringAndSize(s, byref(cp), byref(sz))
            self.failUnlessEqual(sz.value, len(s))
            self.failUnlessEqual(s[0], cp[0])
        finally:
            del cp

    def test_threadstate(self):
        def thread_proc(start, loop, success, finished):
            try:
                try:
                    start.release()
                    x = 1
                    while not loop.locked():
                        x = -x
                except StopIteration:
                    success.acquire()
            finally:
                finished.release()
        start = allocate_lock()
        start.acquire()
        loop = allocate_lock()
        success = allocate_lock()
        finished = allocate_lock()
        finished.acquire()
        tid = start_new_thread(thread_proc, (start, loop, success, finished))
        start.acquire()
        rval = PyThreadState_SetAsyncExc(tid, StopIteration())
        if rval > 1:
            PyThreadState_SetAsyncExc(tid, py_object())
            self.fail()
        self.failUnlessEqual(rval, 1)
        loop.acquire()
        finished.acquire()
        self.failUnless(success.locked())

    def test_memory(self):
        mem = PyMem_Malloc(1)
        self.failUnless(mem is not None)
        PyMem_Free(mem)
        mem = PyMem_Realloc(None, 0)
        self.failUnless(mem is not None)
        PyMem_Free(mem)

    def test_os(self):
        self.failUnless(len(PyOS_InputHook.argtypes) == 0)
        self.failUnless(PyOS_InputHook.restype is c_int)

if __name__ == "__main__":
    unittest.main()
