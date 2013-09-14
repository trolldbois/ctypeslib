import unittest
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import ctypes

from util import ClangTest

class ConstantsTest(ClangTest):

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
        self.failUnlessEqual(ns.i1, 0x7FFFFFFFFFFFFFFF)
        self.failUnlessEqual(ns.i2, -1)
        self.failUnlessEqual(ns.ui1, 0x7FFFFFFFFFFFFFFF)

        # These two tests fail on 64-bit Linux! gccxml bug, I assume...
        self.failUnlessEqual(ns.ui3, 0xFFFFFFFFFFFFFFFF)
        self.failUnlessEqual(ns.ui2, 0x8000000000000000)

    @unittest.skip('')
    def test_int(self):
        ns = self.convert("""
        int zero = 0;
        int one = 1;
        int minusone = -1;
        int maxint = 2147483647;
        int minint = -2147483648;
        """)

        self.failUnlessEqual(ns.zero, 0)
        self.failUnlessEqual(ns.one, 1)
        self.failUnlessEqual(ns.minusone, -1)
        self.failUnlessEqual(ns.maxint, 2147483647)
        self.failUnlessEqual(ns.minint, -2147483648)

    @unittest.skip('')
    def test_uint(self):
        ns = self.convert("""
        unsigned int zero = 0;
        unsigned int one = 1;
        unsigned int minusone = -1;
        unsigned int maxuint = 0xFFFFFFFF;
        """)

        self.failUnlessEqual(ns.zero, 0)
        self.failUnlessEqual(ns.one, 1)
        self.failUnlessEqual(ns.minusone, 4294967295)
        self.failUnlessEqual(ns.maxuint, 0xFFFFFFFF)

    @unittest.skip('')
    def test_doubles(self):
        ns = self.convert("""
        #define A  0.9642
        #define B  1.0
        #define C  0.8249

        double d = 0.0036;
        float f = 2.5;
        """, "-c")
        self.failUnlessAlmostEqual(ns.A, 0.9642)
        self.failUnlessAlmostEqual(ns.B, 1.0)
        self.failUnlessAlmostEqual(ns.C, 0.8249)
        self.failUnlessAlmostEqual(ns.d, 0.0036)
        self.failUnlessAlmostEqual(ns.f, 2.5)

    @unittest.skip('')
    def test_char(self):
        ns = self.convert("""
        char x = 'x';
        wchar_t X = L'X';
        char zero = 0;
        wchar_t w_zero = 0;
        """)

        self.failUnlessEqual(ns.x, 'x')
        self.failUnlessEqual(ns.X, 'X')

        self.failUnlessEqual(type(ns.x), str)
        self.failUnlessEqual(type(ns.X), unicode)

        self.failUnlessEqual(ns.zero, '\0')
        self.failUnlessEqual(ns.w_zero, '\0')

        self.failUnlessEqual(type(ns.zero), str)
        self.failUnlessEqual(type(ns.w_zero), unicode)

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

        self.failUnlessEqual(ns.zero, 0)
        self.failUnlessEqual(ns.one, 1)
        self.failUnlessEqual(ns.minusone, -1)
        self.failUnlessEqual(ns.maxint, 2147483647)
        self.failUnlessEqual(ns.LARGE, 0xFFFFFFFF)
##        self.failUnlessEqual(ns.VERYLARGE, 0xFFFFFFFFFFFFFFFF)
##        self.failUnlessEqual(ns.minint, -2147483648)

        self.failUnlessEqual(ns.spam, "spam")
        self.failUnlessEqual(type(ns.spam), str)

        self.failUnlessEqual(ns.foo, "foo")
        self.failUnlessEqual(type(ns.foo), unicode)

    @unittest.skip('')
    def test_array_nosize(self):
        ns = self.convert("""
        typedef char array[];
        struct blah {
            char varsize[];
        };
        """, "-c")
        # for 'typedef char array[];', gccxml does XXX
        self.failUnlessEqual(ctypes.sizeof(ns.blah), 0)
        self.failUnlessEqual(ctypes.sizeof(ns.array), 0)

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
        self.failUnlessEqual(docstring[:len(prototype)], prototype)
        self.failUnless("malloc.h" in ns.malloc.__doc__)

    @unittest.skip('')
    def test_emptystruct(self):
        ns = self.convert("""
        typedef struct tagEMPTY {
        } EMPTY;
        """)

        self.failUnlessEqual(ctypes.sizeof(ns.tagEMPTY), 0)
    
    # @unittest.skip('')
    def test_inline_function_definition(self):
        ns = self.convert('''
        int zig = 1;

        inline void foo() {
          int zig = 2;
        }
        ''')
        
        self.failUnlessEqual(ns.zig, 1)
        
        # TODO: Make sure the inline function may be called? Currently it is basically ignored.
    
    # @unittest.skip('')
    def test_constantarray_of_structs(self):
        ns = self.convert('''
        typedef struct structA {
        	int	count;
        	int	size;
        }structA_t;

        struct structB {
        	structA_t fifo_data[8];
        	structA_t obsolete_data;
        	structA_t lifo_data[8];
        };

        struct structB x;
        ''')
    
    # @unittest.skip('')
    def test_uninitialized_extern(self):
        ns = self.convert('''
        extern int x;
        ''')
    
    # @unittest.skip('')
    def test_multi_anonymous_bitfield(self):
        ns = self.convert('''
        struct _sometype {
                        boolean_t foo:1;
                        :2;
                        int :28;                /* unused */
                        boolean_t :1;     /* bit 31 */
                } sometype;
        ''')
    
    def test_typedef_struct_array_on_separate_line(self):
        ns = self.convert('''
        struct foo {
         int bar;
        };
        
        typedef struct foo foo_t[256];
        
        typedef struct {
            foo_t baz;
        } __somestruct;
        ''')
    
    def test_extern_function_pointer(self):
        ns = self.convert('''
        extern int (*func_ptr)(const char *arg);
        ''')
    
    def test_extern_function_pointer_multiarg(self):
        ns = self.convert('''
        extern int (*func_ptr)(const char *arg, int c);
        ''')
    
    def test_struct_with_function_pointer(self):
        ns = self.convert('''
        typedef struct x {
         char *y;
         int z;
         void (*f)(void);
        } x_t;
        ''')
    
    def test_struct_with_pointer(self):
        ns = self.convert('''
        struct x {
            int y;
        };
        typedef struct x *x_n_t;

        typedef struct p {
            x_n_t g[1];
        } *p_t;
        ''')
    
    def test_struct_named_twice(self):
        ns = self.convert('''
        typedef	struct xyz {
        	int	fds_bits;
        } xyz;
        ''')

if __name__ == "__main__":
    unittest.main()
