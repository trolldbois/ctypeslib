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

    def test_simple_integer_literal(self):
        flags = ['-target', 'i386-linux']
        self.convert('''#define MY_VAL 1''', flags)
        self.assertEquals(self.namespace.MY_VAL, 1)
        self.convert('''#define __MY_VAL 1''', flags)
        self.assertEquals(getattr(self.namespace,"__MY_VAL"), 1)


    def test_char_arrays(self):
        flags = ['-target', 'i386-linux']
        self.convert('''
#define PRE "before"
#define POST " after"
#define PREPOST PRE POST

char a[] = "what";
char b[] = "why" " though";
char c[] = PRE POST;
char d[] = PREPOST;''', flags)
        self.assertEquals(self.namespace.a, "what")
        self.assertEquals(self.namespace.b, "why though")
        self.assertEquals(self.namespace.c, '"before"" after"')
        self.assertEquals(self.namespace.d, '"before"" after"')


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
