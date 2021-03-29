import unittest
import io

import ctypeslib

from test.util import main


class ApiTest(unittest.TestCase):
    def test_basic_use_string(self):
        py_namespace = ctypeslib.translate('''
int i = 12;
char c2[3] = {'a','b','c'};
struct example_detail {
    int first;
    int last;
};

struct example {
    int argsz;
    int flags;
    int count;
    struct example_detail details[2];
};        
        ''')
        self.assertIn("i", py_namespace)
        self.assertIn("c2", py_namespace)
        self.assertIn("struct_example_detail", py_namespace)
        self.assertIn("struct_example", py_namespace)
        self.assertEqual(py_namespace.i, 12)
        self.assertEqual(py_namespace.c2, ['a', 'b', 'c'])
        # import pprint
        # pprint.pprint(py_namespace)

    def test_basic_use_io(self):
        input_io = io.StringIO('''
int i = 12;
char c2[3] = {'a','b','c'};
struct example_detail {
    int first;
    int last;
};

struct example {
    int argsz;
    int flags;
    int count;
    struct example_detail details[2];
};        
        ''')
        py_namespace = ctypeslib.translate(input_io)
        self.assertIn("i", py_namespace)
        self.assertIn("c2", py_namespace)
        self.assertIn("struct_example_detail", py_namespace)
        self.assertIn("struct_example", py_namespace)
        self.assertEqual(py_namespace.i, 12)
        self.assertEqual(py_namespace.c2, ['a', 'b', 'c'])


if __name__ == '__main__':
    main()
