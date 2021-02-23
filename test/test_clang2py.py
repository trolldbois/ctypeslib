import os
import subprocess
import sys
import unittest

from test.util import ClangTest


def run(args):
    if hasattr(subprocess, 'run'):
        p = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, stderr = p.stdout.decode(), p.stderr.decode()
        return p, output, stderr
    else:
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
        output, stderr = p.communicate()
        return p, output, stderr


__, clang2py_path, __ = run(['which', 'clang2py'])
clang2py_path = clang2py_path.strip()


def clang2py(args):
    return run([sys.executable, clang2py_path] + args)



class InputOutput(ClangTest):

    def test_stdout_default(self):
        """run clang2py test/data/test-includes.h"""
        p, output, stderr = clang2py(['test/data/test-includes.h'])
        self.assertEqual(0, p.returncode)
        self.assertIn("WORD_SIZE is:", output)

    def test_stdout_with_minus_sign(self):
        """run clang2py test/data/test-includes.h -o -"""
        p, output, stderr = clang2py(['test/data/test-includes.h', '-o', '-'])
        self.assertEqual(0, p.returncode)
        self.assertIn("WORD_SIZE is:", output)

    def test_stdin_succeed(self):
        """Support of stdin is done """
        # run cat  test/data/test-includes.h | clang2py -
        p, output, stderr = clang2py(['-'])
        self.assertEqual(0, p.returncode)
        self.assertIn("__all__", output)

    def test_no_files(self):
        """run cat  test/data/test-includes.h | clang2py"""
        p, output, stderr = clang2py(['-o', '/dev/null'])
        self.assertEqual(p.returncode, 2)
        if sys.version_info[0] < 3:
            self.assertIn("error: too few arguments", stderr)  # py2
        else:
            self.assertIn("error: the following arguments are required", stderr)

    def test_multiple_source_files(self):
        """run clang2py -i test/data/test-basic-types.c test/data/test-bitfield.c"""
        p, output, stderr = run(['clang2py', '-i', 'test/data/test-basic-types.c', 'test/data/test-bitfield.c'])
        self.assertEqual(0, p.returncode)
        self.assertIn("WORD_SIZE is:", output)
        self.assertIn("_long = ", output)
        self.assertIn("my__quad_t ", output)
        self.assertIn("class struct_bytes4(", output)


class ArgumentInclude(ClangTest):

    def test_include_with(self):
        """run clang2py -i test/data/test-includes.h"""
        p, output, stderr = clang2py(['-i', 'test/data/test-includes.h'])
        self.assertEqual(0, p.returncode)
        # struct_name are defined in another include file
        self.assertIn("struct_Name", output)
        self.assertIn("struct_Name2", output)
        self.assertIn("struct_Name3", output)

    def test_include_without(self):
        """run clang2py test/data/test-includes.h"""
        p, output, stderr = clang2py(['test/data/test-includes.h'])
        self.assertEqual(0, p.returncode)
        # struct_Name is a dependency. Name2 is not.
        self.assertIn("struct_Name", output)
        self.assertIn("struct_Name3", output)
        self.assertNotIn("struct_Name2", output)


class ArgumentHelper(ClangTest):

    def test_helper(self):
        """run clang2py -h"""
        p, output, stderr = clang2py(['-h', 'test/data/test-includes.h'])
        self.assertEqual(0, p.returncode)
        self.assertIn("Cross-architecture:", output)
        self.assertIn("usage:", output)
        self.assertIn("optional arguments", output)


class ArgumentVersion(ClangTest):

    def test_version(self):
        """run clang2py -V"""
        p, output, stderr = clang2py(['-V', 'XXXXX'])
        self.assertEqual(0, p.returncode)
        if sys.version_info[0] < 3:
            self.assertIn("clang2py version", stderr)
        else:
            self.assertIn("clang2py version", output)


class ArgumentTypeKind(ClangTest):

    @unittest.skip('find a good test for aliases')
    def test_alias(self):
        """run clang2py -k a test/data/test-stdint.cpp"""
        p, output, stderr = clang2py(['-k', 'a', 'test/data/test-stdint.cpp'])
        self.assertEqual(0, p.returncode)
        # TODO: nothing is outputed. Bad test.
        self.assertIn("ctypes", output)
        # TODO: find a good test

    def test_class(self):
        """run clang2py -k c test/data/test-stdint.cpp"""
        p, output, stderr = clang2py(['-k', 'c', 'test/data/test-stdint.cpp'])
        self.assertEqual(0, p.returncode)
        self.assertIn("struct_b", output)

    def test_variable(self):
        """run clang2py -k d test/data/test-strings.cpp"""
        p, output, stderr = clang2py(['-k', 'd', 'test/data/test-strings.cpp'])
        self.assertEqual(0, p.returncode)
        self.assertIn("a =", output)
        self.assertIn("b =", output)

    def test_enumeration(self):
        """run clang2py -k e test/data/test-records.c"""
        p, output, stderr = clang2py(['-k', 'e', 'test/data/test-records.c'])
        self.assertEqual(0, p.returncode)
        self.assertIn("myEnum =", output)

    @unittest.skip('find a good test for function')
    def test_function(self):
        """run clang2py -k f test/data/test-stdint.cpp"""
        p, output, stderr = clang2py(['-k', 'f', 'test/data/test-stdint.cpp'])
        self.assertEqual(0, p.returncode)
        # TODO: find a good test

    def test_macro(self):
        """run clang2py -k m test/data/test-macros.h"""
        p, output, stderr = clang2py(['-k', 'm', 'test/data/test-macros.h'])
        self.assertEqual(0, p.returncode)

    def test_structure(self):
        """run clang2py -k s test/data/test-records-complex.c"""
        p, output, stderr = clang2py(['-k', 's', 'test/data/test-records-complex.c'])
        self.assertEqual(0, p.returncode)
        self.assertIn("struct__complex6", output)
        self.assertIn("struct__complex6_0", output)
        self.assertIn("struct__complex6_1", output)

    def test_typedef(self):
        """run clang2py -k t test/data/test-basic-types.c"""
        p, output, stderr = clang2py(['-k', 't', 'test/data/test-basic-types.c'])
        self.assertEqual(0, p.returncode)
        self.assertIn("_char = ", output)
        self.assertIn("_short = ", output)
        self.assertIn("_uint = ", output)

    def test_union(self):
        """run clang2py -k u test/data/test-records-complex.c"""
        # FIXME, this test case is kinda screwy.
        # trying to generate only union, but looking at incomplete definition.
        p, output, stderr = clang2py(['-k', 'u', 'test/data/test-records-complex.c'])
        self.assertEqual(0, p.returncode)
        # only unions are generated
        self.assertNotIn("struct__complex3(", output)
        self.assertIn("union__complex3_0(", output)
        self.assertIn("struct__complex3_0_2(", output)
        self.assertIn("struct__complex3_0_0(", output)
        self.assertIn("struct__complex3_0_1(", output)
        # not in root
        self.assertNotIn("union__complex3_0_1_1(", output)


class ArgumentComments(ClangTest):

    @unittest.skip('find a good test for function')
    def test_comment(self):
        """run clang2py -c test/data/test-records-complex.c"""
        p, output, stderr = clang2py(['-c', 'test/data/test-records-complex.c'])
        self.assertEqual(0, p.returncode)


if __name__ == "__main__":
    unittest.main()
