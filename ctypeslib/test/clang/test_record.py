import sys
import os
import unittest
import tempfile
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import ctypes
from ctypes.util import find_library
from ctypeslib import clang2py
from ctypeslib.codegen.codegenerator import generate_code

from .util import get_cursor
from .util import get_tu

class ADict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

        tu = get_tu(source)
        teststruct = get_cursor(tu, 'Test')

class ArchTest(unittest.TestCase):
    word_size = None
    flags = []
    def __init__(self, *args, **kw):
        unittest.TestCase.__init__(*args, **kw)
        tu = get_tu('typedef long L;')
        c = get_cursor(tu, 'L')
        self.word_size = c.type.get_size()

class X32Test(ArchTest):
    flags = ['-target','i386-linux']

class X64Test(ArchTest):
    flags = ['-target','x86_64-linux']
    
    
class StructureTest(unittest.TestCase):
    def setUp(self):
        self.test1 = self.gen('test/clang/test-clang1.c')
        #self.test2 = self.gen('test/clang/test-clang2.c')

    def gen(self, fname, flags=['-target','i386']):
        args = [fname]
        if flags:
            args.extend(flags)
            
        ofi = StringIO()
        #ofi = sys.stdout
        generate_code(args, ofi, use_clang=True) #, **kw)
        namespace = {}
        exec ofi.getvalue() in namespace
        print ofi.getvalue()
        return ADict(namespace)

    def test_offset(self):
        
        self.assertEquals( ctypes.sizeof(self.test1.structName), 20)
        self.assertEquals( ctypes.sizeof(self.test1.structName2), 20)
        





if __name__ == "__main__":
    unittest.main()
