import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ArchTest
    
'''Test if records are correctly generated for different target archictecture.
'''
class RecordTest(ArchTest):
    @unittest.skip('')
    def test_simple_x32(self):
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

    @unittest.skip('')
    def test_simple_x64(self):
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
        flags = ['-target','i386-linux']
        self.namespace = self.gen('test/data/test-clang1.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.structName), 18)
        self.assertEquals(ctypes.sizeof(self.namespace.structName2), 20)
        self.assertEquals(ctypes.sizeof(self.namespace.Node), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.Node2), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.my__quad_t), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.my_bitfield), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.my_struct), 8)

    @unittest.skip('')
    def test_padding(self):
        flags = ['-target','i386-linux']
        self.namespace = self.gen('test/data/test-clang5.c', flags)
        
        self.assertEquals(ctypes.sizeof(self.namespace.structName), 14)
        self.assertEquals(ctypes.sizeof(self.namespace.structName2), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.Node), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.Node2), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.Node3), 12)
        self.assertEquals(ctypes.sizeof(self.namespace.Node4), 12)
        self.assertEquals(ctypes.sizeof(self.namespace.Node5), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.my_bitfield), 16)

        





if __name__ == "__main__":
    unittest.main()
