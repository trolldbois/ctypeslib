# -*- coding: utf-8 -*-
import unittest
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import ctypes

from util import ClangTest

class ConstantsTest(ClangTest):
    """Tests from the original ctypeslib.
    """

    def test_var(self):
        """Basic POD test variable declaration'
        """
        self.convert("""
        int i1;
        """)
        #self.assertEqual(ctypes.sizeof(self.namespace.i1), 4)
        self.assertTrue(True)

    #@unittest.skip('')
    def test_longlong(self):
        """Basic POD test variable on longlong values'
        """
        self.convert("""
        long long int i1 = 0x7FFFFFFFFFFFFFFFLL;
        long long int i2 = -1;
        unsigned long long ui3 = 0xFFFFFFFFFFFFFFFFULL;
        unsigned long long ui2 = 0x8000000000000000ULL;
        unsigned long long ui1 = 0x7FFFFFFFFFFFFFFFULL;
        """, flags=['-target','x86_64'])
        self.assertEquals(self.namespace.i1, 0x7FFFFFFFFFFFFFFF)
        self.assertEquals(self.namespace.i2, -1)
        self.assertEquals(self.namespace.ui1, 0x7FFFFFFFFFFFFFFF)
        self.assertEquals(self.namespace.ui3, 0xFFFFFFFFFFFFFFFF)
        self.assertEquals(self.namespace.ui2, 0x8000000000000000)

    #@unittest.skip('')
    def test_int(self):
        self.convert("""
        int zero = 0;
        int one = 1;
        int minusone = -1;
        int maxint = 2147483647;
        int minint = -2147483648;
        """)

        self.assertEqual(self.namespace.zero, 0)
        self.assertEqual(self.namespace.one, 1)
        self.assertEqual(self.namespace.minusone, -1)
        self.assertEqual(self.namespace.maxint, 2147483647)
        self.assertEqual(self.namespace.minint, -2147483648)

    # we are not actually looking at signed/unsigned types...
    @unittest.expectedFailure
    def test_uint_minus_one(self):
        self.convert("""
        unsigned int minusone = -1;
        """)
        self.assertEqual(self.namespace.minusone, 4294967295)

    def test_uint(self):
        self.convert("""
        unsigned int zero = 0;
        unsigned int one = 1;
        unsigned int maxuint = 0xFFFFFFFF;
        """)
        self.assertEqual(self.namespace.zero, 0)
        self.assertEqual(self.namespace.one, 1)
        self.assertEqual(self.namespace.maxuint, 0xFFFFFFFF)

    # no macro support yet
    @unittest.expectedFailure
    def test_macro(self):
        self.convert("""
        #define A  0.9642
        #define B  1.0
        #define C  0.8249
        """)
        self.failUnlessAlmostEqual(self.namespace.A, 0.9642)
        self.failUnlessAlmostEqual(self.namespace.B, 1.0)
        self.failUnlessAlmostEqual(self.namespace.C, 0.8249)

    def test_doubles(self):
        self.convert("""
        double d = 0.0036;
        float f = 2.5;
        """)
        self.failUnlessAlmostEqual(self.namespace.d, 0.0036)
        self.failUnlessAlmostEqual(self.namespace.f, 2.5)

    #@unittest.skip('')
    # FIXME, L prefix.
    def test_wchar(self):
        self.convert("""
        wchar_t X = L'X'; 
        wchar_t w_zero = 0;
        """, ['-x','c++']) # force c++ lang for wchar
        self.assertEqual(self.namespace.X, 'X')
        self.assertEqual(type(self.namespace.X), unicode)
        self.assertEqual(self.namespace.w_zero, '\0')
        self.assertEqual(type(self.namespace.w_zero), unicode)

    def test_unicode(self):
        ''' unicode conversion test from unittest in clang'''
        self.convert("""
//char const *aa = "Àéîõü";
//char const *a = "ÐÐŸÑÐºÐ°";
//wchar_t const *b = L"ÐÐŸÑÐºÐ°";
//wchar_t const *b2 = L"\x4f60\x597d\x10300";
char const *c = u8"1ÐÐŸÑÐºÐ°";
//char16_t const *e = u"2ÐÐŸÑÐºÐ°";
//char32_t const *f = U"3ÐÐŸÑÐºÐ°";
//char const *d = u8R"(4ÐÐŸÑÐºÐ°)";
//char16_t const *g = uR"(5ÐÐŸÑÐºÐ°)";
//char32_t const *h = UR"(6ÐÐŸÑÐºÐ°)";
//wchar_t const *i = LR"(7ÐÐŸÑÐºÐ°)";
        """, ['-x','c++']) # force c++ lang for wchar
        #self.assertEqual(self.namespace.aa, "Àéîõü")
        self.assertEqual(self.namespace.a, "ÐÐŸÑÐºÐ°")
        #self.assertEqual(self.namespace.b, "ÐÐŸÑÐºÐ°")
        #self.assertEqual(self.namespace.b2, "Àéîõü")
        #self.assertEqual(type(self.namespace.aa), unicode)
        #self.assertEqual(self.namespace.w_zero, '\0')
        #self.assertEqual(type(self.namespace.w_zero), unicode)

    #@unittest.skip('')
    def test_char(self):
        self.convert("""
        char x = 'x';
        char zero = 0;
        """) 
        self.assertEqual(self.namespace.x, 'x')
        self.assertEqual(type(self.namespace.x), str)
        self.assertEqual(self.namespace.zero, '\0') # not very true...
        # type casting will not work in ctypes anyway
        self.assertEqual(type(self.namespace.zero), str) # that is another problem.

    def test_char_p(self):
        self.convert("""
        char x[10];
        char s[] = {'1',']'};
        char *p = "abcde";
        """) 
        self.assertEqual(self.namespace.x, None)
        self.assertEqual(self.namespace.s, "abcde")
        self.assertEqual(self.namespace.p, "abcde")


    #@unittest.skip('')
    # no macro support yet
    @unittest.expectedFailure
    def test_defines(self):
        self.convert("""
        #define zero 0
        #define one 1
        #define minusone -1
        #define maxint 2147483647
        #define minint -2147483648
        #define spam "spam"
        #define foo L"foo"
        #define LARGE 0xFFFFFFFF

        #ifdef _MSC_VER
        # define VERYLARGE 0xFFFFFFFFFFFFFFFFui64
        #endif
        """)

        self.assertEqual(self.namespace.zero, 0)
        self.assertEqual(self.namespace.one, 1)
        self.assertEqual(self.namespace.minusone, -1)
        self.assertEqual(self.namespace.maxint, 2147483647)
        self.assertEqual(self.namespace.LARGE, 0xFFFFFFFF)
##        self.assertEqual(self.namespace.VERYLARGE, 0xFFFFFFFFFFFFFFFF)
##        self.assertEqual(self.namespace.minint, -2147483648)

        self.assertEqual(self.namespace.spam, "spam")
        self.assertEqual(type(self.namespace.spam), str)

        self.assertEqual(self.namespace.foo, "foo")
        self.assertEqual(type(self.namespace.foo), unicode)

    def test_typedef(self):
        self.convert("""
        typedef char char_t;
        typedef int array_t[16];
        typedef union u {
            int a;
            int b;
        } u;
        """)
        self.assertEqual(ctypes.sizeof(self.namespace.array_t), 64)
        self.assertEqual(ctypes.sizeof(self.namespace.union_u), 4)


    #@unittest.skip('')
    def test_incomplete_array(self):
        self.convert("""
        typedef char array[];
        struct blah {
            char varsize[];
        };
        """)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_blah), 1)
        # self brewn size modification
        self.assertEqual(ctypes.sizeof(self.namespace.array), 0)

    @unittest.skip('')
    def test_docstring(self):
        import os
        from ctypes import CDLL
        from ctypes.util import find_library
        if os.name == "nt":
            libc = CDLL("msvcrt")
        else:
            libc = CDLL(find_library("c"))
        self.convert("""
        #include <malloc.h>
        """,
           #               generate_docstrings=True,
           #               searched_dlls=[libc]
        )
        prototype = "void * malloc(size_t".replace(" ", "")
        docstring = self.namespace.malloc.__doc__.replace(" ", "")
        self.assertEqual(docstring[:len(prototype)], prototype)
        self.failUnless("malloc.h" in self.namespace.malloc.__doc__)

    #@unittest.skip('')
    def test_emptystruct(self):
        self.convert("""
        typedef struct tagEMPTY {
        } EMPTY;
        """)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_tagEMPTY), 0)
        self.assertEqual(ctypes.sizeof(self.namespace.EMPTY), 0)

    def test_struct_named_twice(self):
        self.convert('''
        typedef struct xyz {
            int a;
        } xyz;
        ''')
        self.assertEqual(ctypes.sizeof(self.namespace.struct_xyz), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.xyz), 4)
        self.assertSizes('xyz')

    def test_struct_with_pointer(self):
        self.convert('''
        struct x {
            int y;
        };
        typedef struct x *x_n_t;

        typedef struct p {
            x_n_t g[1];
        } *p_t;
        ''', flags=['-target','x86_64'])
        self.assertEqual(ctypes.sizeof(self.namespace.struct_x), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.x_n_t), 8)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_p), 8)
        self.assertEqual(ctypes.sizeof(self.namespace.p_t), 8)
        self.assertSizes('x_n_t')
        self.assertSizes('p_t')

    def test_struct_with_struct_array_member_type(self):
        self.convert('''
        struct foo {
             int bar;
        };
        typedef struct foo foo_t[256];
        typedef struct {
            foo_t baz;
        } somestruct;
        ''', flags=['-target','i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.struct_foo), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.foo_t), 4*256)
        self.assertEqual(ctypes.sizeof(self.namespace.somestruct), 4*256)

    def test_struct_with_struct_array_member(self):
        self.convert('''
        typedef struct A {
            int x
        } structA_t;
        struct B {
            structA_t x[8];
        };
        ''', flags=['-target','i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.struct_A), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.structA_t), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_B), 4*8)


    def test_var_decl_and_scope(self):
        self.convert('''
        int zig;

        inline void foo() {
          int zig;
        };
        ''')
        # FIXME: TranslationUnit PARSE_SKIP_FUNCTION_BODIES
        self.assertEqual(self.namespace.zig, None)
        #self.assertEqual(type(self.namespace.foo), None)

    def test_extern_function_pointer(self):
        self.convert('''
        extern int (*func_ptr)(const char *arg);
        ''')
        self.assertEqual(self.namespace.func_ptr._restype_, ctypes.c_int)
        self.assertEqual(self.namespace.func_ptr._argtypes_[0].__name__, 'LP_c_char')

    def test_extern_function_pointer_multiarg(self):
        self.convert('''
        extern int (*func_ptr)(const char *arg, int c);
        ''')
        self.assertEqual(self.namespace.func_ptr._restype_, ctypes.c_int)
        self.assertEqual(self.namespace.func_ptr._argtypes_[0].__name__, 'LP_c_char')
        self.assertEqual(self.namespace.func_ptr._argtypes_[1].__name__, 'c_int')
    
    
import logging, sys
if __name__ == "__main__":
    logging.basicConfig( stream=sys.stderr, level=logging.DEBUG )
    #logging.getLogger( "SomeTest.testSomething" ).setLevel( logging.DEBUG )
    unittest.main()
