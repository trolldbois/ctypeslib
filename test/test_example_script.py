# From clang/bindings/python/cindex/test
# This file provides common utility functions for the test suite.
#

import ctypes
import importlib
import os
import tempfile
from types import ModuleType
import unittest
from io import StringIO

from ctypeslib.codegen import clangparser, codegenerator

class ExampleTest(unittest.TestCase):
    def setUp(self):
        self.parser = None
        self.full_parsing_options = False

    def tearDown(self):
        self.parser = None

    def test_example(self):
        """Test ctypeslib inline in a python script"""
        flags = ['-target', 'i386-linux']
        source_code = """
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
"""
        # Create a clang parser instance, with the clang target flags
        self.parser = clangparser.Clang_Parser(flags)
        if self.full_parsing_options:
            self.parser.activate_macros_parsing()
            self.parser.activate_comment_parsing()

        try:
            # we have to store the code in a physical file.
            # libclang does not work on memory buffers.
            handle, filename = tempfile.mkstemp(".h")
            open(filename, "w").write(source_code)
            # race condition
            self.parser.parse(filename)
            items = self.parser.get_result()
        finally:
            os.unlink(filename)
        # use ctypeslib to generate Python ctypes code
        ofi = StringIO()
        # Create a ctypeslib code generator
        gen = codegenerator.Generator(ofi)
        # generate the code, first some headers and ctypes import
        gen.generate_headers(self.parser)
        # then the actual python structures
        gen.generate_code(items)
        # Now we can load code in a virtual module namespace
        namespace = {}
        # rewind the String Buffer
        ofi.seek(0)
        # ignore the first line to remove error
        # "SyntaxError: encoding declaration in Unicode string"
        ignore_coding = ofi.readline()
        # read the whole python code
        output = ''.join(ofi.readlines())
        # load the code in a module
        example = ModuleType('example')
        try:
            # run the python code in a namespace
            exec (output, example.__dict__)
        except ValueError:
            print(output)
        # print the python code.
        #print(output)
        # use the module
        one = example.struct_example()
        #print("Allocating struct detail one: %s" % type(one))
        one.count = 1
        one.details[0].first = 12
        assert(one.count == 1)
        assert(one.details[0].first == 12)
        #print("Sizeof structure one: %d" % ctypes.sizeof(one))
        #print("\tone.count == %d" % one.count)
        #print("\tone.details[0].first == %d" % one.details[0].first)
        return

if __name__ == "__main__":
    unittest.main()