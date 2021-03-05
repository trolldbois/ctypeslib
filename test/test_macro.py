import unittest
import datetime

from test.util import ClangTest

'''Test if macro are correctly generated.
'''

import logging

# logging.basicConfig(level=logging.DEBUG)


class Macro(ClangTest):
    # @unittest.skip('')

    def setUp(self):
        # we need to generate macro. Which is very long for some reasons.
        self.full_parsing_options = True

    def test_simple_integer_literal(self):
        self.convert('''#define MY_VAL 1''')
        self.assertEqual(self.namespace.MY_VAL, 1)
        self.convert('''#define __MY_VAL 1''')
        self.assertEqual(getattr(self.namespace, "__MY_VAL"), 1)

    def test_long(self):
        self.convert('''#define BIG_NUM_L 1000000L''')
        self.assertEqual(getattr(self.namespace, "BIG_NUM_L"), 1000000)

    def test_signed(self):
        self.convert('''
        #define ZERO 0
        #define POSITIVE 1
        #define NEGATIVE -1
        ''')
        self.assertIn("ZERO", self.namespace)
        self.assertEqual(self.namespace.ZERO, 0)
        self.assertIn("POSITIVE", self.namespace)
        self.assertEqual(self.namespace.POSITIVE, 1)
        self.assertIn("NEGATIVE", self.namespace)
        self.assertEqual(self.namespace.NEGATIVE, -1)

    def test_signed_long_long(self):
        self.convert('''
        #define ZERO 0x0000000000000000LL
        #define POSITIVE 0x0000000080000000LL
        #define NEGATIVE -0x0000000080000000LL
        ''')
        self.assertIn("ZERO", self.namespace)
        self.assertEqual(self.namespace.ZERO, 0)
        self.assertIn("POSITIVE", self.namespace)
        self.assertIn("NEGATIVE", self.namespace)
        self.assertEqual(self.namespace.POSITIVE, 0x0000000080000000)
        self.assertEqual(self.namespace.NEGATIVE, -0x0000000080000000)

    def test_signed_long(self):
        self.convert('''
        #define ZERO 0x0000000000000000L
        #define POSITIVE 0x0000000080000000L
        #define NEGATIVE -0x0000000080000000L
        ''')
        self.assertIn("ZERO", self.namespace)
        self.assertEqual(self.namespace.ZERO, 0)
        self.assertIn("POSITIVE", self.namespace)
        self.assertIn("NEGATIVE", self.namespace)
        self.assertEqual(self.namespace.POSITIVE, 0x0000000080000000)
        self.assertEqual(self.namespace.NEGATIVE, -0x0000000080000000)

    def test_unsigned_long_long(self):
        self.convert('''
        #define ZERO 0x0000000000000000ULL
        #define POSITIVE 0x0000000080000000ULL
        #define NEGATIVE -0x0000000080000000ULL
        ''')
        self.assertIn("ZERO", self.namespace)
        self.assertEqual(self.namespace.ZERO, 0)
        self.assertIn("POSITIVE", self.namespace)
        self.assertIn("NEGATIVE", self.namespace)
        self.assertEqual(self.namespace.POSITIVE, 0x0000000080000000)
        self.assertEqual(self.namespace.NEGATIVE, -0x0000000080000000)

    def test_char_arrays(self):
        self.convert('''
#define PRE "before"
#define POST " after"
#define APREPOST PRE POST

char a[] = "what";
char b[] = "why" " though";
char c[] = PRE POST;
char d[] = APREPOST;''')
        self.assertEqual(self.namespace.a, "what")
        self.assertEqual(self.namespace.b, "why though")
        self.assertEqual(self.namespace.c, 'before after')
        self.assertEqual(self.namespace.d, 'before after')
        # print(self.text_output)

    @unittest.skip
    def test_define_wchar_t(self):
        """'L' means wchar_t"""
        # currently this fails because of Bug #77 , in C
        # wchar.h contains recursive INTEGER_LITERAL MACROS that fail to be codegen properly
        self.convert("""
        #define SPAM "spam"
        #define STRING_NULL "NULL"
        #define FOO L"foo"
        
        #include <wchar.h>
        wchar_t * my_foo = FOO;
        """)

        self.assertEqual(self.namespace.SPAM, "spam")
        self.assertEqual(self.namespace.STRING_NULL, "NULL")
        self.assertEqual(self.namespace.FOO, "foo")
        self.assertEqual(self.namespace.my_foo, "foo")

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
        # print(self.text_output)

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
        # print(self.text_output)
        self.assertIn("fn", self.namespace)
        # self.assertIn("fn", self.text_output)
        # self.assertEqual(self.namespace.i, 10)

    def test_function(self):
        self.convert('''
#define fn_type void
#define fn_name(a,b) real_name(a,b)
fn_type fn_name(int a, int b);
''')
        self.assertIn("real_name", self.namespace)

    def test_simple_macro_function(self):
        self.convert('''
    #define HI(x) x
    HI(int) y;
    ''')
        # print(self.text_output)
        self.assertIn("y", self.namespace)
        self.assertEqual(self.namespace.y, 0)
        self.assertIn("HI", self.text_output)
        # only comments for functions
        self.assertNotIn("HI", self.namespace)

    def test_example(self):
        self.convert('''
#define DEBUG
#define PROD 1
#define MACRO_EXAMPLE(x,y) {x,y}
// #define MY 1 2 3 4 5 6

int tab1[] = MACRO_EXAMPLE(1,2); 
''')
        # print(self.text_output)
        self.assertIn("tab1", self.namespace)
        self.assertEqual(self.namespace.tab1, [1, 2])
        self.assertEqual(self.namespace.DEBUG, True)
        self.assertEqual(self.namespace.PROD, 1)
        # we don't gen macro functions
        self.assertNotIn('MACRO_EXAMPLE', self.namespace)
        # self.assertEqual(self.namespace.MY, 123456)
        # that is not a thing that compiles

    def test_macro_to_variable(self):
        """Test which macros are going to be defined """
        self.convert('''
        #define SPAM "spam"
        #define NO "no"
        #define SPACE " "
        #define FOO L"foo"
        #define NOSPAM NO SPAM
        #define NO_SPAM NO SPACE SPAM
        #define NO_SPAM_FOO NO SPACE SPAM SPACE FOO
        ''')
        # print(self.text_output)
        self.assertIn('SPAM', self.namespace)
        self.assertEqual('spam', self.namespace.SPAM)
        self.assertIn('NO', self.namespace)
        self.assertEqual('no', self.namespace.NO)
        self.assertIn('SPACE', self.namespace)
        self.assertEqual(' ', self.namespace.SPACE)
        self.assertIn('NO_SPAM', self.namespace)
        self.assertEqual('no spam', self.namespace.NO_SPAM)
        self.assertIn('NO_SPAM_FOO', self.namespace)
        self.assertEqual('no spam foo', self.namespace.NO_SPAM_FOO)


    def test_all(self):
        """Test which macros are going to be defined """
        self.convert('''
        #define DATE __DATE__
        #define DEBUG
        #define PROD 1
        #define MACRO_STRING "abcde"
        #define MACRO_FUNC(x,y) {x,y}
        // #define MACRO_LIST 1 2 3 4 5 6

        int tab1[] = MACRO_FUNC(1,2);
        char date[] = DATE; 
        ''')
        # print(self.text_output)
        self.assertIn('DEBUG', self.namespace.__all__)
        self.assertIn('PROD', self.namespace.__all__)
        self.assertIn('MACRO_STRING', self.namespace.__all__)
        self.assertNotIn('DATE', self.namespace.__all__)
        self.assertNotIn('__DATE__', self.namespace.__all__)
        self.assertNotIn('MACRO_FUNC', self.namespace.__all__)
        # self.assertIn('MACRO_LIST', self.namespace.__all__)

    """
    Bug #77
    2021-03
    Both compiler's Predefined Macros and standard's Preprocessor Macros handling works for string values.
    But predef macros for INTEGER_LITERAL do NOT work.
    https://gcc.gnu.org/onlinedocs/cpp/Standard-Predefined-Macros.html
    https://blog.kowalczyk.info/article/j/guide-to-predefined-macros-in-c-compilers-gcc-clang-msvc-etc..html
    """

    @unittest.skip
    def test_defines_predefined(self):
        self.convert('''
#define DATE __DATE__
char c1[] = DATE;
char f[] = __FILE__;
char v2[] = __clang_version__;

// this fails for now
int v = __STDC_VERSION__;
''')
        # print(self.text_output)
        self.assertIn("c1", self.namespace)
        # replace leading 0 in day by a whitespace.
        this_date = datetime.datetime.now().strftime("%b %d %Y").replace(" 0", "  ")
        self.assertEqual(self.namespace.c1, this_date)
        self.assertIn("# DATE = __DATE__", self.text_output)
        self.assertIn("f", self.namespace)
        self.assertIn("v", self.namespace)
        self.assertIn("v2", self.namespace)
        # v2 = '11.0.0' for example
        self.assertIn("v2 = '", self.text_output)
        # this is the current limit
        self.assertNotEqual(self.namespace.v, [])

    def test_internal_defines_recursive(self):
        self.convert('''
    #define DATE __DATE__
    #define DATE2 DATE
    char c1[] = DATE2;
        ''')
        # print(self.text_output)
        self.assertIn("c1", self.namespace)
        # replace leading 0 in day by a whitespace.
        this_date = datetime.datetime.now().strftime("%b %d %Y").replace(" 0", "  ")
        self.assertIn("# DATE = __DATE__", self.text_output)
        self.assertIn("# DATE2 = __DATE__", self.text_output)

    @unittest.skip
    def test_internal_defines_recursive_with_operation(self):
        self.convert('''
    #define VERSION __clang_major__
    #define VPLUS (VERSION+1)
    int version = VERSION;
    int vplus = VPLUS;
        ''')
        # print(self.text_output)
        self.assertIn("version", self.namespace)
        self.assertIn("vplus", self.namespace)
        self.assertIn("# VERSION = __clang_major__", self.text_output)
        self.assertIn("# VPLUS = ", self.text_output)

    def test_internal_defines_identifier(self):
        self.convert('''
    #define DATE "now"
    #define DATE2 DATE
    char c1[] = DATE2;
    ''')
        # print(self.text_output)
        self.assertIn("c1", self.namespace)
        self.assertEqual(self.namespace.c1, 'now')
        self.assertIn("DATE", self.namespace)
        self.assertEqual(self.namespace.DATE, 'now')
        self.assertIn("DATE2", self.namespace)
        self.assertEqual(self.namespace.DATE2, 'now')

    def test_pack_attribute(self):
        self.convert('''
    #define PACK __attribute__((aligned(2)))
    #define PACKTO __attribute__((packed))
    
    int x PACK = 0;
    struct foo {
        char a;
        int x[2] PACKTO;
    };
    ''')
        # print(self.text_output)
        self.assertIn("# PACK = __attribute__", self.text_output)
        self.assertIn("# PACKTO = __attribute__", self.text_output)
        self.assertIn("struct_foo", self.namespace)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
