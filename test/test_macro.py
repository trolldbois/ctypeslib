import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest

'''Test if macro are correctly generated.
'''


class Macro(ClangTest):
    #@unittest.skip('')

    def setUp(self):
        # we need to generate macro. Which is very long for some reasons.
        self.full_parsing_options = True

    def test_simple_integer_literal(self):
        flags = ['-target', 'i386-linux']
        self.convert('''#define MY_VAL 1''', flags)
        self.assertEquals(self.namespace.MY_VAL, 1)
        self.convert('''#define __MY_VAL 1''', flags)
        self.assertEquals(getattr(self.namespace,"__MY_VAL"), 1)


if __name__ == "__main__":
    unittest.main()
