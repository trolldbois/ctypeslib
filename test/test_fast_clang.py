import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest
    
class CompareSizes(ClangTest):
    """Compare python sizes with the clang framework.
    """


    #@unittest.skip('')
    def test_simple(self):
        """Test sizes of pod."""
        targets = ['badaboum', 'you_badaboum', 'big_badaboum', 
            'you_big_badaboum', 'double_badaboum', 'long_double_badaboum',
            'float_badaboum', 'ptr']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.gen('test/data/test-clang0.c', flags)
            for name in targets:
                self.assertSizes(name)

    #@unittest.skip('')
    @unittest.expectedFailure # packed attribute
    def test_records(self):
        """Test sizes of records."""
        targets = ['struct_Name', 'struct_Name2','struct_Node','struct_Node2','myEnum',
            'my__quad_t','my_bitfield','mystruct']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.gen('test/data/test-clang1.c', flags)
            for name in targets:
                self.assertSizes(name)

    def test_records_fields_offset(self):
        """Test offset of records fields."""
        targets = ['struct_Name', 'struct_Name2','struct_Node','struct_Node2',
            'my__quad_t','my_bitfield','mystruct']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.gen('test/data/test-clang1.c', flags)
            for name in targets:
                self.assertOffsets(name)

    #@unittest.skip('')
    def test_includes(self):
        """Test sizes of pod with std include."""
        targets = ['int8_t', 'intptr_t', 'intmax_t' ] 
        #no size here ['a','b','c','d','e','f','g','h']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.gen('test/data/test-clang2.c', flags)
            for name in targets:
                self.assertSizes(name)
        


import logging, sys
if __name__ == "__main__":
    logging.basicConfig( stream=sys.stderr, level=logging.DEBUG )
    #logging.getLogger( "SomeTest.testSomething" ).setLevel( logging.DEBUG )
    unittest.main()
