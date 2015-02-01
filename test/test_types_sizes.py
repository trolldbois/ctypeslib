import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest


class BasicTypes(ClangTest):
    """Tests the basic types for size.
Because we might (*) generate Fundamental types variable as python variable, 
we can't ctypes.sizeof a python object. So we used typedef to verify types sizes
because we can ctypes.sizeof a type name. Just not a variable.    

(*) Decision pending review
    """
    code = '''
typedef char _char;
typedef unsigned int _uint;
typedef unsigned long _ulong;
typedef double _double;
typedef long double _longdouble;
typedef float _float;
        '''

    def test_x32(self):
        flags = ['-target','i386-linux']
        self.convert(self.code, flags)
        self.assertEqual(ctypes.sizeof(self.namespace._char), 1)
        self.assertEqual(ctypes.sizeof(self.namespace._uint), 4)
        self.assertEqual(ctypes.sizeof(self.namespace._ulong), 4)
        self.assertEqual(ctypes.sizeof(self.namespace._double), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._longdouble), 12)
        self.assertEqual(ctypes.sizeof(self.namespace._float), 4)

    def test_x64(self):
        flags = ['-target','x86_64-linux']
        self.convert(self.code, flags)
        self.assertEqual(ctypes.sizeof(self.namespace._char), 1)
        self.assertEqual(ctypes.sizeof(self.namespace._uint), 4)
        self.assertEqual(ctypes.sizeof(self.namespace._ulong), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._double), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._longdouble), 16)
        self.assertEqual(ctypes.sizeof(self.namespace._float), 4)

    def test_win32(self):
        flags = ['-target','i386-win32']
        self.convert(self.code, flags)
        self.assertEqual(ctypes.sizeof(self.namespace._char), 1)
        self.assertEqual(ctypes.sizeof(self.namespace._uint), 4)
        self.assertEqual(ctypes.sizeof(self.namespace._ulong), 4)
        self.assertEqual(ctypes.sizeof(self.namespace._double), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._longdouble), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._float), 4)

    def test_win64(self):
        flags = ['-target','x86_64-win64']
        self.convert(self.code, flags)
        self.assertEqual(ctypes.sizeof(self.namespace._char), 1)
        self.assertEqual(ctypes.sizeof(self.namespace._uint), 4)
        self.assertEqual(ctypes.sizeof(self.namespace._ulong), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._double), 8)
        self.assertEqual(ctypes.sizeof(self.namespace._longdouble), 16)
        self.assertEqual(ctypes.sizeof(self.namespace._float), 4)


class Types(ClangTest):
    """Tests if the codegeneration return the proper types."""

    def test_double_underscore(self):
        flags = ['-target','i386-linux']
        self.convert(
        '''
        struct __X {
            int a;
        };
        typedef struct __X __Y;
        __Y v1;
        ''', flags)
        self.assertEqual(ctypes.sizeof(self.namespace.struct___X), 4)
        self.assertEqual(ctypes.sizeof(getattr(self.namespace, '__Y')), 4)
        self.assertEqual(self.namespace.v1, None)

    @unittest.expectedFailure 
    def test_double_underscore_field(self):
        # cant load in namespace with exec and expect to work.
        # Double underscore is a special private field in python
        flags = ['-target','i386-linux']
        self.convert(
        '''
        struct __X {
            int a;
        };
        typedef struct __X __Y;
        __Y v1;
        struct Z{
            __Y b;
            };
        ''', flags)
        self.assertEqual(ctypes.sizeof(self.namespace.struct___X), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_Z), 4)
        self.assertEqual(ctypes.sizeof(self.namespace.struct_Z.b), 4)
        self.assertEqual(ctypes.sizeof(getattr(self.namespace, '__Y')), 4)
        self.assertEqual(self.namespace.v1, None)

    def test_typedef(self):
        flags = ['-target','i386-linux']
        self.convert(
        '''
        typedef int A;
        typedef A B;
        typedef B C;
        typedef int* PA;
        typedef PA PB;
        typedef PB* PC;
        typedef PC PD;
        ''', flags)
        self.assertEquals(self.namespace.A,self.namespace.B)
        self.assertEquals(self.namespace.A,self.namespace.C)
        self.assertEquals(self.namespace.PA,self.namespace.PB)
        self.assertEquals(self.namespace.PC,self.namespace.PD)
        
       
        
if __name__ == "__main__":
    unittest.main()
