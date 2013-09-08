import unittest
import ctypes

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
        self.namespace = self.gen('test/data/test-clang0.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.you_badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.big_badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.you_big_badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.double_badaboum), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.long_double_badaboum), 12)
        self.assertEquals(ctypes.sizeof(self.namespace.float_badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.ptr), 4)

    #@unittest.skip('')
    def test_simple_x64(self):
        """Test sizes for simple POD types on x64.
        """
        flags = ['-target','x86_64-linux']
        self.namespace = self.gen('test/data/test-clang0.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.you_badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.big_badaboum), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.you_big_badaboum), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.double_badaboum), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.long_double_badaboum), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.float_badaboum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.ptr), 8)

    #@unittest.skip('')
    def test_records_x32(self):
        """Test sizes for simple records on i386.
        """
        flags = ['-target','i386-linux']
        self.namespace = self.gen('test/data/test-clang1.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.structName), 18)
        self.assertEquals(ctypes.sizeof(self.namespace.structName2), 20)
        self.assertEquals(ctypes.sizeof(self.namespace.Node), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.Node2), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.my__quad_t), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.my_bitfield), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.mystruct), 5)
    
    # others size tests are in test_fast_clang
    
    #@unittest.skip('')
    def test_padding_x32(self):
        """Test padding for simple records on i386.
        """
        flags = ['-target','i386-linux']
        self.namespace = self.gen('test/data/test-clang5.c', flags)        
        self.assertEquals(self.namespace.structName2.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.structName2.PADDING_0.size, 2)
        self.assertEquals(self.namespace.structName4.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.structName4.PADDING_0.size, 2)
        self.assertEquals(self.namespace.structName4.PADDING_1.offset, 10)
        self.assertEquals(self.namespace.structName4.PADDING_1.size, 2)
        self.assertEquals(self.namespace.structName4.PADDING_2.offset, 18)
        self.assertEquals(self.namespace.structName4.PADDING_2.size, 2)
        self.assertEquals(self.namespace.Node.PADDING_0.offset, 13)
        self.assertEquals(self.namespace.Node.PADDING_0.size, 3)
        self.assertEquals(self.namespace.Node2.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.Node2.PADDING_0.size, 3)
        self.assertEquals(self.namespace.Node3.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.Node3.PADDING_0.size, 3)
        self.assertEquals(self.namespace.Node3.PADDING_1.offset, 21)
        self.assertEquals(self.namespace.Node3.PADDING_1.size, 3)
        self.assertEquals(self.namespace.Node4.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.Node4.PADDING_0.size, 1)
        self.assertEquals(self.namespace.Node5.PADDING_0.offset, 6)
        self.assertEquals(self.namespace.Node5.PADDING_0.size, 2)

    def test_padding_x64(self):
        """Test padding for simple records on x64.
        """
        flags = ['-target','x86_64-linux']
        self.namespace = self.gen('test/data/test-clang5.c', flags)        
        self.assertEquals(self.namespace.structName2.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.structName2.PADDING_0.size, 2)
        self.assertEquals(self.namespace.structName4.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.structName4.PADDING_0.size, 6)
        self.assertEquals(self.namespace.structName4.PADDING_1.offset, 18)
        self.assertEquals(self.namespace.structName4.PADDING_1.size, 6)
        self.assertEquals(self.namespace.structName4.PADDING_2.offset, 34)
        self.assertEquals(self.namespace.structName4.PADDING_2.size, 6)
        self.assertEquals(self.namespace.Node.PADDING_0.offset, 4)
        self.assertEquals(self.namespace.Node.PADDING_0.size, 4)
        self.assertEquals(self.namespace.Node.PADDING_1.offset, 25)
        self.assertEquals(self.namespace.Node.PADDING_1.size, 7)
        self.assertEquals(self.namespace.Node2.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.Node2.PADDING_0.size, 7)
        self.assertEquals(self.namespace.Node3.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.Node3.PADDING_0.size, 7)
        self.assertEquals(self.namespace.Node3.PADDING_1.offset, 41)
        self.assertEquals(self.namespace.Node3.PADDING_1.size, 7)
        self.assertEquals(self.namespace.Node4.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.Node4.PADDING_0.size, 1)
        self.assertEquals(self.namespace.Node4.PADDING_1.offset, 4)
        self.assertEquals(self.namespace.Node4.PADDING_1.size, 4)
        self.assertEquals(self.namespace.Node5.PADDING_0.offset, 6)
        self.assertEquals(self.namespace.Node5.PADDING_0.size, 2)

        





if __name__ == "__main__":
    unittest.main()
