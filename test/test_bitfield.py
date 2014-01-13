import unittest
import ctypes
import logging
import sys

from util import get_cursor
from util import get_tu
from util import ClangTest
    
class RecordTest(ClangTest):
    """Test if records are correctly generated for different target archictecture.
    """
    #@unittest.skip('')
    def test_simple_x32(self):
        """Test sizes for simple POD types on i386.
        """
        flags = ['-target','i386-linux']
        self.gen('test/data/test-bitfield.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_byte1), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_byte1b), 4)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes2), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes2b), 4)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes3), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes3b), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes3c), 8)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes4), 12)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes4b), 4)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_complex), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_complex2), 16)

    #@unittest.skip('')
    def test_simple_x64(self):
        """Test sizes for simple POD types on x64.
        """
        flags = ['-target','x86_64-linux']
        self.gen('test/data/test-bitfield.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_byte1), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_byte1b), 4)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes2), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes2b), 4)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes3), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes3b), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes3c), 8)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes4), 12)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_bytes4b), 4)

        self.assertEquals(ctypes.sizeof(self.namespace.struct_complex), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_complex2), 16)


def p(s):
    import ctypes
    print 'sizeof',ctypes.sizeof(s)
    for x in s._fields_:
        if len(x) == 2:
            f,t = x
            print f,getattr(s,f)
        else:
            f,t,o = x
            print f,getattr(s,f)
        
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO)
    #logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main(verbosity=2)
