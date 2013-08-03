import unittest
from ctypeslib.util import byref_at

from ctypes import *

import _ctypes_test

dll = CDLL(_ctypes_test.__file__)

# This test function will accept any ctypes pointer or pointer like
# object, and will return the pointer value as integer.
testfunc = dll._testfunc_p_p
testfunc.argtypes = [c_void_p]
testfunc.restype = c_void_p

class ByrefTest(unittest.TestCase):
    def test_byref_array(self):
        array = (c_int * 8)()
        # Passing an array is the same as passing a byref or pointer
        # to the array
        self.failUnlessEqual(addressof(array), testfunc(array))
        self.failUnlessEqual(addressof(array), testfunc(byref(array)))
        self.failUnlessEqual(addressof(array), testfunc(pointer(array)))

    def test_byref_fundamental(self):
        obj = c_int()
        self.failUnlessEqual(addressof(obj), testfunc(byref(obj)))
        self.failUnlessEqual(addressof(obj), testfunc(pointer(obj)))

    def test_byref_at(self):
        array = (c_int * 8)()
        self.failUnlessEqual(addressof(array) + 0,
                             testfunc(byref_at(array, 0)))
        self.failUnlessEqual(addressof(array) + 1,
                             testfunc(byref_at(array, 1)))
        for ofs in range(8 * sizeof(c_int)):
            self.failUnlessEqual(addressof(array) + ofs,
                                 testfunc(byref_at(array, ofs)))

if __name__ == "__main__":
    unittest.main()
