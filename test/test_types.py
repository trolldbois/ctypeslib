import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest
    
class Types(ClangTest):
    """Tests if the codegeneration return the proper types."""

    def test_doubel_underscore(self):
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
        self.assertEqual(ctypes.sizeof(self.namespace._P__Y), 4)
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
