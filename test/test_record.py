import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest


class RecordTest(ClangTest):

    """Test if records are correctly generated for different target archictecture.
    """

    #@unittest.skip('')
    def test_records_x32(self):
        """Test sizes for simple records on i386.
        """
        flags = ['-target', 'i386-linux']
        self.gen('test/data/test-records.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_Name), 18)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_Name2), 20)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_Node), 16)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_Node2), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.my__quad_t), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.my_bitfield), 4)
        self.assertEquals(ctypes.sizeof(self.namespace.mystruct), 5)

    # others size tests are in test_fast_clang

    #@unittest.skip('')
    def test_padding_x32(self):
        """Test padding for simple records on i386.
        """
        flags = ['-target', 'i386-linux']
        self.gen('test/data/test-padding.c', flags)
        self.assertEquals(self.namespace.struct_Name2.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.struct_Name2.PADDING_0.size, 2)
        self.assertEquals(self.namespace.struct_Name4.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.struct_Name4.PADDING_0.size, 2)
        self.assertEquals(self.namespace.struct_Name4.PADDING_1.offset, 10)
        self.assertEquals(self.namespace.struct_Name4.PADDING_1.size, 2)
        self.assertEquals(self.namespace.struct_Name4.PADDING_2.offset, 18)
        self.assertEquals(self.namespace.struct_Name4.PADDING_2.size, 2)
        self.assertEquals(self.namespace.struct_Node.PADDING_0.offset, 13)
        self.assertEquals(self.namespace.struct_Node.PADDING_0.size, 3)
        self.assertEquals(self.namespace.struct_Node2.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.struct_Node2.PADDING_0.size, 3)
        self.assertEquals(self.namespace.struct_Node3.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.struct_Node3.PADDING_0.size, 3)
        self.assertEquals(self.namespace.struct_Node3.PADDING_1.offset, 21)
        self.assertEquals(self.namespace.struct_Node3.PADDING_1.size, 3)
        self.assertEquals(self.namespace.struct_Node4.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.struct_Node4.PADDING_0.size, 1)
        self.assertEquals(self.namespace.struct_Node5.PADDING_0.offset, 6)
        self.assertEquals(self.namespace.struct_Node5.PADDING_0.size, 2)

    def test_padding_x64(self):
        """Test padding for simple records on x64.
        """
        flags = ['-target', 'x86_64-linux']
        self.gen('test/data/test-padding.c', flags)
        self.assertEquals(self.namespace.struct_Name2.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.struct_Name2.PADDING_0.size, 2)
        self.assertEquals(self.namespace.struct_Name4.PADDING_0.offset, 2)
        self.assertEquals(self.namespace.struct_Name4.PADDING_0.size, 6)
        self.assertEquals(self.namespace.struct_Name4.PADDING_1.offset, 18)
        self.assertEquals(self.namespace.struct_Name4.PADDING_1.size, 6)
        self.assertEquals(self.namespace.struct_Name4.PADDING_2.offset, 34)
        self.assertEquals(self.namespace.struct_Name4.PADDING_2.size, 6)
        self.assertEquals(self.namespace.struct_Node.PADDING_0.offset, 4)
        self.assertEquals(self.namespace.struct_Node.PADDING_0.size, 4)
        self.assertEquals(self.namespace.struct_Node.PADDING_1.offset, 25)
        self.assertEquals(self.namespace.struct_Node.PADDING_1.size, 7)
        self.assertEquals(self.namespace.struct_Node2.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.struct_Node2.PADDING_0.size, 7)
        self.assertEquals(self.namespace.struct_Node3.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.struct_Node3.PADDING_0.size, 7)
        self.assertEquals(self.namespace.struct_Node3.PADDING_1.offset, 41)
        self.assertEquals(self.namespace.struct_Node3.PADDING_1.size, 7)
        self.assertEquals(self.namespace.struct_Node4.PADDING_0.offset, 1)
        self.assertEquals(self.namespace.struct_Node4.PADDING_0.size, 1)
        self.assertEquals(self.namespace.struct_Node4.PADDING_1.offset, 4)
        self.assertEquals(self.namespace.struct_Node4.PADDING_1.size, 4)
        self.assertEquals(self.namespace.struct_Node5.PADDING_0.offset, 6)
        self.assertEquals(self.namespace.struct_Node5.PADDING_0.size, 2)

    def test_record_in_record(self):
        self.convert('''
typedef struct _complex {
	struct {
		int a;
	};
} complex, *pcomplex;
        ''', ['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.complex), 4)

    def test_record_in_record_2(self):
        self.convert('''
typedef struct _complex {
	struct {
		int a;
	};
	struct {
        long b;
	};
} complex, *pcomplex;
        ''', ['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.complex), 8)

    def test_record_in_record_3(self):
        self.convert('''
typedef struct _complex {
    union {
	    struct {
		    int a;
	    };
	    struct {
            long b;
            union {
                int c;
                struct {
                    long long d;
                    char e;
                };
            };
	    };
	    struct {
            long f;
	    };
	    int g;
    };
} complex, *pcomplex;
        ''', ['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.complex), 16)

    def test_record_in_record_packed(self):
        self.convert('''
typedef struct _complex {
	struct {
		char a;
	};
	struct __attribute__((packed)) {
		char b;
	};
} complex, *pcomplex;
        ''', ['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.complex), 2)

    def test_forward_decl(self):
        self.convert('''
typedef struct entry Entry;
struct entry {
  Entry * flink;
  Entry * blink;
};
        ''', ['-target', 'i386-linux'])
        self.assertEqual(ctypes.sizeof(self.namespace.struct_entry), 8)

    def test_zero_length_array(self):
        flags = ['-target', 'x86_64-linux']
        self.gen('test/data/test-zero-length-array.c', flags)
        self.assertEquals(self.namespace.struct_example_detail.first.offset, 0)
        self.assertEquals(self.namespace.struct_example_detail.last.offset, 4)
        self.assertEquals(self.namespace.struct_example.argsz.offset, 0)
        self.assertEquals(self.namespace.struct_example.flags.offset, 4)
        self.assertEquals(self.namespace.struct_example.count.offset, 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_example_detail), 8)
        self.assertEquals(ctypes.sizeof(self.namespace.struct_example), 12)


import logging
import sys
if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    # logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main()
