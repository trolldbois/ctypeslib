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

    #@unittest.skip('')
    def test_longlong(self):
        """Basic POD test variable on longlong values'
        """
        ns = self.convert("""
        long long int i1 = 0x7FFFFFFFFFFFFFFFLL;
        long long int i2 = -1;
        unsigned long long ui3 = 0xFFFFFFFFFFFFFFFFULL;
        unsigned long long ui2 = 0x8000000000000000ULL;
        unsigned long long ui1 = 0x7FFFFFFFFFFFFFFFULL;
        """)
        self.assertEquals(ns.i1, 0x7FFFFFFFFFFFFFFF)
        self.assertEquals(ns.i2, -1)
        self.assertEquals(ns.ui1, 0x7FFFFFFFFFFFFFFF)
        self.assertEquals(ns.ui3, 0xFFFFFFFFFFFFFFFF)
        self.assertEquals(ns.ui2, 0x8000000000000000)

    #@unittest.skip('')
    def test_int(self):
        ns = self.convert("""
        int zero = 0;
        int one = 1;
        int minusone = -1;
        int maxint = 2147483647;
        int minint = -2147483648;
        """)

        self.assertEqual(ns.zero, 0)
        self.assertEqual(ns.one, 1)
        self.assertEqual(ns.minusone, -1)
        self.assertEqual(ns.maxint, 2147483647)
        self.assertEqual(ns.minint, -2147483648)

    # we are not actually looking at signed/unsigned types...
    @unittest.expectedFailure
    def test_uint_minus_one(self):
        ns = self.convert("""
        unsigned int minusone = -1;
        """)
        self.assertEqual(ns.minusone, 4294967295)

    def test_uint(self):
        ns = self.convert("""
        unsigned int zero = 0;
        unsigned int one = 1;
        unsigned int maxuint = 0xFFFFFFFF;
        """)
        self.assertEqual(ns.zero, 0)
        self.assertEqual(ns.one, 1)
        self.assertEqual(ns.maxuint, 0xFFFFFFFF)

    # no macro support yet
    @unittest.expectedFailure
    def test_macro(self):
        ns = self.convert("""
        #define A  0.9642
        #define B  1.0
        #define C  0.8249
        """)
        self.failUnlessAlmostEqual(ns.A, 0.9642)
        self.failUnlessAlmostEqual(ns.B, 1.0)
        self.failUnlessAlmostEqual(ns.C, 0.8249)

    def test_doubles(self):
        ns = self.convert("""
        double d = 0.0036;
        float f = 2.5;
        """)
        self.failUnlessAlmostEqual(ns.d, 0.0036)
        self.failUnlessAlmostEqual(ns.f, 2.5)

    #@unittest.skip('')
    # FIXME, L prefix.
    def test_wchar(self):
        ns = self.convert("""
        wchar_t X = L'X'; 
        wchar_t w_zero = 0;
        """, ['-x','c++']) # force c++ lang for wchar
        self.assertEqual(ns.X, 'X')
        self.assertEqual(type(ns.X), unicode)
        self.assertEqual(ns.w_zero, '\0')
        self.assertEqual(type(ns.w_zero), unicode)

    def test_char(self):
        ns = self.convert("""
        char x = 'x';
        char zero = 0;
        """) 
        self.assertEqual(ns.x, 'x')
        self.assertEqual(type(ns.x), str)
        self.assertEqual(ns.zero, '\0') # not very true...
        # type casting will not work in ctypes anyway
        self.assertEqual(type(ns.zero), str) # that is another problem.


    @unittest.skip('')
    def test_defines(self):
        ns = self.convert("""
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
        """, "-c")

        self.assertEqual(ns.zero, 0)
        self.assertEqual(ns.one, 1)
        self.assertEqual(ns.minusone, -1)
        self.assertEqual(ns.maxint, 2147483647)
        self.assertEqual(ns.LARGE, 0xFFFFFFFF)
##        self.assertEqual(ns.VERYLARGE, 0xFFFFFFFFFFFFFFFF)
##        self.assertEqual(ns.minint, -2147483648)

        self.assertEqual(ns.spam, "spam")
        self.assertEqual(type(ns.spam), str)

        self.assertEqual(ns.foo, "foo")
        self.assertEqual(type(ns.foo), unicode)

    @unittest.skip('')
    def test_array_nosize(self):
        ns = self.convert("""
        typedef char array[];
        struct blah {
            char varsize[];
        };
        """, "-c")
        # for 'typedef char array[];', gccxml does XXX
        self.assertEqual(ctypes.sizeof(ns.blah), 0)
        self.assertEqual(ctypes.sizeof(ns.array), 0)

    @unittest.skip('')
    def test_docstring(self):
        from ctypes import CDLL
        from ctypes.util import find_library
        if os.name == "nt":
            libc = CDLL("msvcrt")
        else:
            libc = CDLL(find_library("c"))
        ns = self.convert("""
        #include <malloc.h>
        """,
                          generate_docstrings=True,
                          searched_dlls=[libc]
        )
        prototype = "void * malloc(size_t".replace(" ", "")
        docstring = ns.malloc.__doc__.replace(" ", "")
        self.assertEqual(docstring[:len(prototype)], prototype)
        self.failUnless("malloc.h" in ns.malloc.__doc__)

    @unittest.skip('')
    def test_emptystruct(self):
        ns = self.convert("""
        typedef struct tagEMPTY {
        } EMPTY;
        """)

        self.assertEqual(ctypes.sizeof(ns.tagEMPTY), 0)

import logging, sys
if __name__ == "__main__":
    logging.basicConfig( stream=sys.stderr, level=logging.DEBUG )
    #logging.getLogger( "SomeTest.testSomething" ).setLevel( logging.DEBUG )
    unittest.main()
