import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ArchTest
    
'''Compare python sizes with the clang framework.
'''
class CompareSizes(ArchTest):
    def test_simple(self):
        targets = ['badaboum', 'you_badaboum', 'big_badaboum', 
            'you_big_badaboum', 'double_badaboum', 'long_double_badaboum',
            'float_badaboum', 'ptr']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.namespace = self.gen('test/data/test-clang0.c', flags)
            for name in targets:
                self.assertSizes(name)

    def test_records(self):
        targets = ['structName', 'structName2','Node','Node2','myEnum',
            'my__quad_t','my_bitfield','my_struct']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.namespace = self.gen('test/data/test-clang1.c', flags)
            for name in targets:
                self.assertSizes(name)

        





if __name__ == "__main__":
    unittest.main()
