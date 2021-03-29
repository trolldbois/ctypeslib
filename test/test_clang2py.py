import os
import subprocess
import sys
import unittest

from pathlib import Path
from test.util import ClangTest, main
import ctypeslib
from io import StringIO
from unittest import mock


def run(args, env):
    p = subprocess.run(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    output, stderr = p.stdout.decode(), p.stderr.decode()
    return p, output, stderr


clang2py_path = None
python_path = None
libclang_library = None
libclang_include_dir = None
use_pytest = False


try:
    import pytest

    @pytest.fixture(scope="module", autouse=True)
    def _clang2py_path(request):
        global python_path
        python_path = Path(request.fspath).parent.parent

    @pytest.fixture(scope="session", autouse=True)
    def libclang_config(pytestconfig, request):
        global libclang_library
        global libclang_include_dir
        libclang_library = pytestconfig.getoption("libclang_library")
        libclang_include_dir = pytestconfig.getoption("libclang_include_dir")

    use_pytest = True

except ImportError:
    python_path = Path(__file__).parent.parent

clang2py_path = Path(__file__).parent.parent / "ctypeslib" / "clang2py.py"


def clang2py(args):
    global libclang_include_dir
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{python_path}:{env['PYTHONPATH']}"
    if libclang_include_dir:
        args += [f'--clang-args=-isystem{libclang_include_dir}']
    return run([sys.executable, clang2py_path] + args, env=env)


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
        p, output, stderr = clang2py(['-i', 'test/data/test-basic-types.c', 'test/data/test-bitfield.c'])
        self.assertEqual(0, p.returncode)
        self.assertIn("WORD_SIZE is:", output)
        self.assertIn("_long = ", output)
        self.assertIn("my__quad_t ", output)
        self.assertIn("class struct_bytes4(", output)


class ArgumentInclude(ClangTest):

    def test_include_with(self):
        """run clang2py -i test/data/test-includes.h"""
        p, output, stderr = clang2py(['-i', 'test/data/test-includes.h'])
        # print(output)
        # print(stderr)
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


class ArgumentTypeKind(ClangTest):

    def setUp(self):
        # We need to generate macro (including function-like macro)
        # This used to take a long time to process but some performance
        # improvements have been implemented and I am not sure if it's
        # still the case for common workloads. (See: codegen.cache).
        self.full_parsing_options = True
        self.advanced_macro = True

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


class ArgumentVersion(ClangTest):

    def test_version(self):
        """run clang2py --version"""
        p, output, stderr = clang2py(['--version'])
        self.assertEqual(0, p.returncode)
        self.assertIn(str(ctypeslib.__version__), output)
        self.assertIn("libclang", output)

    def test_version(self):
        """run clang2py -V"""
        p, output, stderr = clang2py(['-V', 'XXXXX'])
        self.assertEqual(0, p.returncode)
        if sys.version_info[0] < 3:
            self.assertIn("clang2py version", stderr)
        else:
            self.assertIn("clang2py version", output)


class ArgumentVerbose(ClangTest):

    def test_verbose(self):
        """run clang2py --verbose test/data/test-records.c"""
        p, output, stderr = clang2py(['--verbose', 'test/data/test-records.c'])
        self.assertEqual(0, p.returncode, stderr)
        self.assertNotIn("DEBUG:", stderr)
        self.assertNotIn("DEBUG:", output)
        self.assertIn("# Total symbols:", stderr)

    def test_debug(self):
        """run clang2py --verbose test/data/test-records.c"""
        p, output, stderr = clang2py(['--verbose', 'test/data/test-records.c', '--debug'])
        self.assertEqual(0, p.returncode)
        self.assertIn("DEBUG:", stderr)
        self.assertNotIn("DEBUG:", output)
        self.assertIn("# Total symbols:", stderr)


if use_pytest:

    class ModuleTesting(ClangTest):
        def test_version(self):
            """run clang2py -v"""
            from ctypeslib import clang2py
            with self.assertRaises(SystemExit):
                clang2py.main(['--version'])
            captured = self.capfd.readouterr()
            self.assertIn(str(ctypeslib.__version__), captured.out)

        def test_arg_file(self):
            """run clang2py test/data/test-basic-types.c"""
            from ctypeslib import clang2py
            clang2py.main(['test/data/test-basic-types.c'])
            captured = self.capfd.readouterr()
            self.assertIn("_int = ctypes.c_int", captured.out)

        def test_arg_input_stdin(self):
            """run echo | clang2py - """
            from ctypeslib import clang2py
            with mock.patch('sys.stdin', StringIO('int i = 0;')) as stdin:
                clang2py.main(['-'])
                captured = self.capfd.readouterr()
                self.assertIn("__all__ =", captured.out)
                self.assertIn("# TARGET arch is:", captured.out)

        @unittest.skip('stderr capturing fails for some unknown reason...')
        def test_arg_debug(self):
            """run clang2py --debug test/data/test-basic-types.c"""
            from ctypeslib import clang2py
            clang2py.main(['--debug', 'test/data/test-basic-types.c'])
            captured = self.capfd.readouterr()
            self.assertIn("_int = ctypes.c_int", captured.out)
            self.assertIn("DEBUG:clangparser:ARCH sizes:", captured.err)
            self.assertNotIn("ERROR", captured.err)

        def test_arg_target(self):
            """run clang2py --target x86_64-Linux test/data/test-basic-types.c """
            from ctypeslib import clang2py
            clang2py.main(['--target', 'x86_64-Linux', 'test/data/test-basic-types.c'])
            captured = self.capfd.readouterr()
            self.assertIn("# TARGET arch is: x86_64-Linux", captured.out)
            self.assertIn("_int = ctypes.c_int", captured.out)
            self.assertIn("_long = ctypes.c_int64", captured.out)

            clang2py.main(['--target', 'i586-Linux', 'test/data/test-basic-types.c'])
            captured = self.capfd.readouterr()
            self.assertIn("# TARGET arch is: i586-Linux", captured.out)
            self.assertIn("_int = ctypes.c_int", captured.out)
            self.assertIn("_long = ctypes.c_int32", captured.out)

        # TODO
        @unittest.skip
        def test_arg_clang_args(self):
            """run clang2py test/data/test-basic-types.c --clang-args="-DDEBUG=2" """
            from ctypeslib import clang2py
            clang2py.main(['', '--clang-args="-DDEBUG=2"', '-'])
            captured = self.capfd.readouterr()
            self.assertIn("# TARGET arch is:", captured.out)
            self.assertIn("i = 2", captured.out)

        @pytest.fixture(autouse=True)
        def capfd(self, capfd):
            self.capfd = capfd


class OrderingTest(ClangTest):

    def test_brute(self):
        """run 20 times clang2py to identify ordering differences"""
        outputs = []
        for i in range(20):
            p, output, stderr = clang2py(['./test/data/test-include-order2.h'])
            outputs.append(output)
            var = output.index("f = struct_foo_s")
            decl = output.index("class struct_foo_s(Structure)")
            self.assertGreater(var, decl, "Generated incorrect ordering")

        set_outputs = set(outputs)
        self.assertEqual(len(set_outputs), 1)

    def test_enum_struct(self):
        """run clang2py on a ordering issue involving enum and struct"""
        p, output, stderr = clang2py(['./test/data/test-enum.c'])
        decl = output.index("('e', c__EA_E),")
        enum = output.index("c__EA_E = ctypes.c_uint32")
        print(output)
        self.assertGreater(decl, enum, "Generated incorrect ordering")


if __name__ == "__main__":
    main()
