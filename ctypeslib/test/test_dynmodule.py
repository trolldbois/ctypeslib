# Basic test of dynamic code generation
import unittest

import stdio
from ctypes import POINTER, c_int

class DynModTest(unittest.TestCase):
    def test_fopen(self):
        self.failUnlessEqual(stdio.fopen.restype, POINTER(stdio.FILE))
        self.failUnlessEqual(stdio.fopen.argtypes, [stdio.STRING, stdio.STRING])

    def test_constants(self):
        self.failUnlessEqual(stdio._O_RDONLY, 0)
        self.failUnlessEqual(stdio._O_WRONLY, 1)
        self.failUnlessEqual(stdio._O_RDWR, 2)

if __name__ == "__main__":
    unittest.main()
