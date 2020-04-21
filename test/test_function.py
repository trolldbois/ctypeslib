import unittest
import ctypes

from ctypeslib.codegen.util import get_cursor
from ctypeslib.codegen.util import get_tu
from test.util import ClangTest

'''Test if macro are correctly generated.
'''


class Macro(ClangTest):
    #@unittest.skip('')
    
    def setUp(self):
        # we need to generate macro. Which is very long for some reasons.
        self.full_parsing_options = True

    def test_simple_function(self):
        flags = ['-target', 'i386-linux']
        self.convert('''int get_one();''', flags)
        
    def test_function_return_enum(self):
        flags = ['-target', 'i386-linux']
        self.convert('''
enum NUM {
    ZERO = 0,
    ONE
};
enum NUM get_one();''', flags)
        
        
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
