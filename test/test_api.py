import unittest
import io

import ctypeslib
from ctypeslib.codegen import config
from ctypeslib.codegen import typedesc


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


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.input_io = io.StringIO('''
        struct example_1 {
            int first;
            int last;
        };

        union example_2 {
            int a;
            float f;
        };''')

    def test_no_config(self):
        py_namespace = ctypeslib.translate(self.input_io)
        self.assertIn("struct_example_1", py_namespace)
        self.assertIn("union_example_2", py_namespace)

    def test_config_default(self):
        cfg = config.CodegenConfig()
        py_namespace = ctypeslib.translate(self.input_io, cfg)
        self.assertIn("struct_example_1", py_namespace)
        self.assertIn("union_example_2", py_namespace)

    def test_filter_types(self):
        cfg = config.CodegenConfig()
        cfg._init_types("u")
        py_namespace = ctypeslib.translate(self.input_io, cfg=cfg)
        self.assertNotIn("struct_example_1", py_namespace)
        self.assertIn("union_example_2", py_namespace)


if __name__ == '__main__':
    unittest.main()
