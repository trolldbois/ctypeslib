import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest
    
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
        #self.assertEquals('A','B')
        
if __name__ == "__main__":
    unittest.main()
