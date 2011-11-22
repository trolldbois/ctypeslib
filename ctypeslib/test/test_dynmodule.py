# Basic test of dynamic code generation
import unittest
import os, glob

import stdio
from ctypes import POINTER, c_int
from ctypeslib.dynamic_module import UnknownSymbol

if os.name == "nt":
    import winapi
    import winapi_without_defines

    #define'd constants are available in winapi, but not in winapi_without_defines
    class winapiTest(unittest.TestCase):
        def test_constants(self):
            self.failUnlessEqual(winapi.MB_OK, 0)

        def test_constants_2(self):
            # XXX I should raise AttributeError instead in UnknownSymbol
            self.failUnlessRaises((UnknownSymbol, AttributeError),
                                  lambda: winapi_without_defines.MB_OK)

class DynModTest(unittest.TestCase):

    def test_fopen(self):
        self.failUnlessEqual(stdio.fopen.restype, POINTER(stdio.FILE))
        self.failUnlessEqual(stdio.fopen.argtypes, [stdio.STRING, stdio.STRING])

    def test_constants(self):
        self.failUnlessEqual(stdio.O_RDONLY, 0)
        self.failUnlessEqual(stdio.O_WRONLY, 1)
        self.failUnlessEqual(stdio.O_RDWR, 2)

    def test_compiler_errors(self):
        from ctypeslib.codegen.cparser import CompilerError
        from ctypeslib.dynamic_module import include
        self.failUnlessRaises(CompilerError, lambda: include("#error"))

if __name__ == "__main__":
    unittest.main()
