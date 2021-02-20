import unittest
import ctypes

from ctypeslib.codegen.util import get_cursor
from ctypeslib.codegen.util import get_tu
from util import ClangTest

'''Test if macro are correctly generated.
'''


class Macro(ClangTest):
    # @unittest.skip('')

    def setUp(self):
        # we need to generate macro. Which is very long for some reasons.
        self.full_parsing_options = True

    def test_simple_integer_literal(self):
        flags = ['-target', 'i386-linux']
        self.convert('''#define MY_VAL 1''', flags)
        self.assertEqual(self.namespace.MY_VAL, 1)
        self.convert('''#define __MY_VAL 1''', flags)
        self.assertEqual(getattr(self.namespace, "__MY_VAL"), 1)

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
        self.assertEqual(self.namespace.a, "what")
        self.assertEqual(self.namespace.b, "why though")
        self.assertEqual(self.namespace.c, '"before"" after"')
        self.assertEqual(self.namespace.d, '"before"" after"')

    def test_long(self):
        flags = ['-target', 'i386-linux']
        self.convert('''#define BIG_NUM_L 1000000L''', flags)
        self.assertEqual(getattr(self.namespace, "BIG_NUM_L"), 1000000)

    def test_unsigned_long_long(self):
        flags = ['-target', 'i386-linux']
        self.convert('''#define BIG_NUM_ULL 0x0000000080000000ULL''', flags)
        self.assertEqual(getattr(self.namespace, "BIG_NUM_ULL"), 0x0000000080000000)

    def test_simple_replace_typedef(self):
        """When macro are used as typedef, it's transparent to us. """
        # Python does not have typedef so who care what type name is a variable ?
        self.convert('''
            #define macro_type int
            macro_type i = 10;
            ''')
        # macro_type = int # macro
        # i = 10 # Variable ctypes.c_int32
        # very little
        self.assertIn("i", self.namespace)
        self.assertEqual(self.namespace.i, 10)
        print(self.text_output)

    def test_simple_replace_function(self):
        """When macro are used as typedef, it's transparent to us. """
        # Python does not have typedef so who care what type name is a variable ?
        self.convert('''
            #define macro_type int
            macro_type fn(int a, int b) {return a+b} ;
            ''', )
        # macro_type = int # macro
        # i = 10 # Variable ctypes.c_int32
        # very little
        print(self.text_output)
        # self.assertIn("fn", self.namespace)
        # self.assertEqual(self.namespace.i, 10)

    def test_function(self):
        self.convert('''
#define fn_type void
#define fn_name(a,b) real_name(a,b)
fn_type fn_name(int a, int b);
''')
        self.assertIn("real_name", self.namespace)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
