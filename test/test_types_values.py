# -*- coding: utf-8 -*-
import unittest

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
        self.assertIsNone(self.namespace.i1)

    def test_longlong(self):
        """Basic POD test variable on longlong values'
        """
        self.convert("""
        long long int i1 = 0x7FFFFFFFFFFFFFFFLL;
        long long int i2 = -1;
        unsigned long long ui3 = 0xFFFFFFFFFFFFFFFFULL;
        unsigned long long ui2 = 0x8000000000000000ULL;
        unsigned long long ui1 = 0x7FFFFFFFFFFFFFFFULL;
        """, flags=['-target', 'x86_64'])
        self.assertEquals(self.namespace.i1, 0x7FFFFFFFFFFFFFFF)
        self.assertEquals(self.namespace.i2, -1)
        self.assertEquals(self.namespace.ui1, 0x7FFFFFFFFFFFFFFF)
        self.assertEquals(self.namespace.ui3, 0xFFFFFFFFFFFFFFFF)
        self.assertEquals(self.namespace.ui2, 0x8000000000000000)

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

    def test_uint(self):
        self.convert("""
        unsigned int zero = 0;
        unsigned int one = 1;
        unsigned int maxuint = 0xFFFFFFFF;
        """)
        self.assertEqual(self.namespace.zero, 0)
        self.assertEqual(self.namespace.one, 1)
        self.assertEqual(self.namespace.maxuint, 0xFFFFFFFF)

    def test_doubles(self):
        self.convert("""
        double d = 0.0036;
        float f = 2.5;
        """)
        self.failUnlessAlmostEqual(self.namespace.d, 0.0036)
        self.failUnlessAlmostEqual(self.namespace.f, 2.5)

    def test_wchar(self):
        self.convert("""
        wchar_t X = L'X';
        wchar_t w_zero = 0;
        """, ['-x', 'c++'])  # force c++ lang for wchar
        self.assertEqual(self.namespace.X, 'X')
        self.assertEqual(type(self.namespace.X), unicode)
        self.assertEqual(self.namespace.w_zero, 0)
        # type cast will not work.
        #self.assertEqual(type(self.namespace.w_zero), unicode)

    def test_unicode(self):
        ''' unicode conversion test from unittest in clang'''
        self.gen('test/data/test-strings.cpp', ['-x', 'c++'])
        # force c++ lang for wchar
        self.assertEqual(self.namespace.aa, '\xc0\xe9\xee\xf5\xfc')  # "Àéîõü")
        self.assertEqual(self.namespace.a, "Кошка")
        # NULL terminated
        self.assertEqual(len(self.namespace.aa), 6 * 8 / 8 - 1)
        self.assertEqual(len(self.namespace.a), 11 * 8 / 8 - 1)

    @unittest.expectedFailure
    def test_unicode_wchar(self):
        ''' unicode conversion test from unittest in clang'''
        self.gen('test/data/test-strings.cpp', ['-x', 'c++'])
        # should be 10 or 20
        self.assertEqual(len(self.namespace.b.encode("utf-8")), 10)
        # utf-32, not supported. Should be 6 or 12
        self.assertEqual(len(self.namespace.b2.encode("utf-8")), 6)

    #@unittest.expectedFailure
    def test_unicode_cpp11(self):
        ''' unicode conversion test from unittest in clang'''
        self.gen('test/data/test-strings.cpp', ['-x', 'c++', '--std=c++11'])
        # force c++ lang for wchar
        # source code failures , wchar_16_t, u8 and u8R not recognised
        self.assertEqual(len(self.namespace.c.encode('utf-8')), 12 * 8 / 8 - 1)
        self.assertEqual(len(self.namespace.d.encode('utf-8')), 12 * 8 / 8 - 1)
        # should be 6*16/8
        self.assertEqual(len(self.namespace.e.encode('utf-8')), 11)
        # should be 6*32/8
        self.assertEqual(len(self.namespace.f.encode('utf-8')), 11)
        # should be 6*16/8
        self.assertEqual(len(self.namespace.g.encode('utf-8')), 11)
        # should be 6*32/8
        self.assertEqual(len(self.namespace.h.encode('utf-8')), 11)
        # should be 6*16/8
        self.assertEqual(len(self.namespace.i.encode('utf-8')), 11)

    def test_char(self):
        self.convert("""
        char x = 'x';
        char zero = 0;
        """)
        self.assertEqual(self.namespace.x, 'x')
        self.assertEqual(type(self.namespace.x), str)
        self.assertEqual(self.namespace.zero, 0)
        # type casting will not work in ctypes anyway
        #self.assertEqual(type(self.namespace.zero), str)

    def test_char_p(self):
        self.convert("""
        char x[10];
        char s[] = {'1',']'};
        char *p = "abcde";
        """)
        self.assertEqual(self.namespace.x, [])
        self.assertEqual(self.namespace.s, ['1', ']'])
        self.assertEqual(self.namespace.p, "abcde")

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
        self.assertSizes("array_t")
        self.assertSizes("union_u")

    def test_array(self):
        self.convert('''
        char c1[];
        char c2[3] = {'a','b','c'};
        char c3[] = {'a','b','c'};
        int tab1[];
        int tab2[3] = {1,2,3};
        int tab3[] = {1,2,3};
        ''')
        self.assertEqual(self.namespace.c1, [])
        self.assertEqual(self.namespace.c2, ['a', 'b', 'c'])
        self.assertEqual(self.namespace.c3, ['a', 'b', 'c'])
        self.assertEqual(self.namespace.tab1, [])
        self.assertEqual(self.namespace.tab2, [1, 2, 3])
        self.assertEqual(self.namespace.tab3, [1, 2, 3])

    def test_incomplete_array(self):
        self.convert("""
        typedef char array[];
        struct blah {
            char varsize[];
        };
        """)
        self.assertSizes("struct_blah")
        # self brewn size modification
        self.assertEqual(ctypes.sizeof(self.namespace.array), 0)

    def test_emptystruct(self):
        self.convert("""
        typedef struct tagEMPTY {
        } EMPTY;
        """)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_tagEMPTY), 0)
        self.assertEqual(ctypes.sizeof(self.namespace.EMPTY), 0)
        self.assertSizes("struct_tagEMPTY")

    def test_struct_named_twice(self):
        self.convert('''
        typedef struct xyz {
            int a;
        } xyz;
        ''')
        self.assertEqual(ctypes.sizeof(self.namespace.struct_xyz), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.xyz), 4)
        self.assertSizes('xyz')
        self.assertSizes("struct_xyz")

    def test_struct_with_pointer(self):
        self.convert('''
        struct x {
            int y;
        };
        typedef struct x *x_n_t;

        typedef struct p {
            x_n_t g[1];
        } *p_t;
        ''', flags=['-target', 'x86_64'])
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
        ''', flags=['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.struct_foo), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.foo_t), 4 * 256)
        self.assertEqual(ctypes.sizeof(self.namespace.somestruct), 4 * 256)
        self.assertSizes("struct_foo")
        self.assertSizes("foo_t")
        self.assertSizes("somestruct")

    def test_struct_with_struct_array_member(self):
        self.convert('''
        typedef struct A {
            int x
        } structA_t;
        struct B {
            structA_t x[8];
        };
        ''', flags=['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.struct_A), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.structA_t), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_B), 4 * 8)
        self.assertSizes("struct_A")
        self.assertSizes("structA_t")
        self.assertSizes("struct_B")

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
        self.assertEqual(
            self.namespace.func_ptr._argtypes_[0].__name__,
            'LP_c_char')

    def test_extern_function_pointer_multiarg(self):
        self.convert('''
        extern int (*func_ptr)(const char *arg, int c);
        ''')
        self.assertEqual(self.namespace.func_ptr._restype_, ctypes.c_int)
        self.assertEqual(
            self.namespace.func_ptr._argtypes_[0].__name__,
            'LP_c_char')
        self.assertEqual(
            self.namespace.func_ptr._argtypes_[1].__name__,
            'c_int')

    def test_operation(self):
        self.convert('''
        int i = -1;
        int i2 = -1+2*3/2-3;
        int i3 = -((1-2)*(1-2));
        int j = -i;
        ''')
        self.assertEqual(self.namespace.i, -1)
        self.assertEqual(self.namespace.i2, -1)
        self.assertEqual(self.namespace.i3, -1)
        self.assertEqual(self.namespace.j, 1)

    @unittest.expectedFailure
    def test_array_operation(self):
        self.convert('''
        int i = 1;
        int a[2] = {1,-2};
        int b[2] = {+1,-2-2+2};
        int c[2] = {+i,-i*2};
        ''')
        self.assertEqual(self.namespace.a, [1, -2])
        self.assertEqual(self.namespace.b, [1, -2])
        self.assertEqual(self.namespace.c, [1, -2])  # unsuported ref_expr

    # we are not actually looking at signed/unsigned types...
    @unittest.expectedFailure
    def test_uint_minus_one(self):
        self.convert("""
        unsigned int minusone = -1;
        """)
        self.assertEqual(self.namespace.minusone, 4294967295)

    # no macro support yet
    #@unittest.expectedFailure
        self.full_parsing_options = True
        self.convert("""
    def test_macro(self):
        #define A  0.9642
        #define B  1.0
        #define C  0.8249
        """)
        self.failUnlessAlmostEqual(self.namespace.A, 0.9642)
        self.failUnlessAlmostEqual(self.namespace.B, 1.0)
        self.failUnlessAlmostEqual(self.namespace.C, 0.8249)

    def test_anonymous_struct(self):
        flags = ['-target', 'i386-linux']
        self.convert(
            '''
        struct X {
            struct {
                long cancel_jmp_buf[8];
                int mask_was_saved;
            } cancel_jmp_buf[8];
            void * pad[4];
        };
        ''', flags)
        #import code
        # code.interact(local=locals())
        self.assertEqual(ctypes.sizeof(self.namespace.struct_X), 304)
        self.assertSizes("struct_X")

    def test_anonymous_struct_extended(self):
        flags = ['-target', 'x86_64-linux']
        self.convert(
            '''
typedef unsigned long int uint64_t;
typedef uint64_t ULONGLONG;
typedef union MY_ROOT_UNION {
 struct {
  ULONGLONG Alignment;
  ULONGLONG Region;
 };
 struct {
     struct {
        ULONGLONG Depth : 16;
        ULONGLONG Sequence : 9;
        ULONGLONG NextEntry : 39;
        ULONGLONG HeaderType : 1;
        ULONGLONG Init : 1;
        ULONGLONG Reserved : 59;
        ULONGLONG Region : 3;
    };
} Header8;
 struct {
     struct {
        ULONGLONG Depth : 16;
        ULONGLONG Sequence : 48;
        ULONGLONG HeaderType : 1;
        ULONGLONG Init : 1;
        ULONGLONG Reserved : 2;
        ULONGLONG NextEntry : 60;
    };
} Header16;
 struct {
  struct {
     struct {
        ULONGLONG Depth : 16;
        ULONGLONG Sequence : 48;
        ULONGLONG HeaderType : 1;
        ULONGLONG Reserved : 3;
        ULONGLONG NextEntry : 60;
    };
  } HeaderX64;
 };
} __attribute__((packed)) MY_ROOT_UNION, *PMY_ROOT_UNION, **PPMY_ROOT_UNION ;
        };
        ''', flags)
        self.assertIn("MY_ROOT_UNION", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_0", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_1", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_2", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_3", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_3_0", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_3_0_0", self.namespace.keys())
        self.assertIn("struct_MY_ROOT_UNION_1_0", self.namespace.keys())
        self.assertEqual(ctypes.sizeof(self.namespace.union_MY_ROOT_UNION), 16)
        self.assertSizes("union_MY_ROOT_UNION")

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

    @unittest.skip('find a good test for docstring')
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


import logging
import sys
if __name__ == "__main__":
    #logging.basicConfig( stream=sys.stderr, level=logging.DEBUG )
    unittest.main()
