import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest
    
'''Test if pointers are correctly generated in structures for different target
archictecture.
'''
class Pointer(ClangTest):
    #@unittest.skip('')
    def test_x32_pointer(self):
        flags = ['-target','i386-linux']
        self.gen('test/data/test-ctypes0.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_s0), 20)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_s1), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.union_u1), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_s2), 12)
        self.assertEquals(ctypes.sizeof(self.namespace.union_u2), 8)
        
    #@unittest.expectedFailure # invalid structs should have a size of 1
    def test_x32_pointer_errors(self):
        flags = ['-target','i386-linux']
        self.gen('test/data/test-ctypes0.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.union_invalid1), 8)

    def test_x64_pointer(self):
        flags = ['-target','x86_64-linux']
        self.gen('test/data/test-ctypes0.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_s0), 32)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_s1), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.union_u1), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_s2), 24)
        self.assertEquals(ctypes.sizeof(self.namespace.union_u2), 16)

    #@unittest.expectedFailure # invalid structs should have a size of 1
    def test_x64_pointer_errors(self):
        flags = ['-target','x86_64-linux']
        self.gen('test/data/test-ctypes0.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.union_invalid1), 16)

    def test_member_pointer(self):
        flags = ['-target','x86_64-linux','-x','c++']
        self.convert('''
        struct Blob {
          int i;
        };
        int Blob::*member_pointer;
        ''', flags)
        self.assertEquals(self.namespace.struct_Blob.i.size, 4)
        #FIXME
        self.fail('member pointer')
        #self.assertTrue(isinstance(self.namespace.member_pointer,POINTER_T) )
        
 
        
if __name__ == "__main__":
    unittest.main()
