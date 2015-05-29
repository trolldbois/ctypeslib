import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest
from subprocess import Popen, PIPE

'''Test if clang2py works.
'''


class InputOutput(ClangTest):
    #@unittest.skip('')

    def test_stdout_default(self):
        'run clang2py test/data/test-includes.h'
        p = Popen(['clang2py', 'test/data/test-includes.h'], 
                  stdin=PIPE, 
                  stdout=PIPE, 
                  stderr=PIPE,
                  bufsize=-1)
        output, error = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertIn("WORD_SIZE is:", output)

    def test_stdout_with_minus_sign(self):
        'run clang2py test/data/test-includes.h -o -'
        p = Popen(['clang2py', 'test/data/test-includes.h','-o', '-'], 
                  stdin=PIPE, 
                  stdout=PIPE, 
                  stderr=PIPE,
                  bufsize=-1)
        output, error = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertIn("WORD_SIZE is:", output)

    def test_stdin_fail(self):
        'Support of stdin is on the TODO list'
        flags = ['-target', 'i386-linux']
        # run cat  test/data/test-includes.h | clang2py -
        p = Popen(['clang2py','-'], 
                  stdin=open('test/data/test-includes.h'), 
                  stdout=PIPE, 
                  stderr=PIPE,
                  bufsize=-1)
        output, error = p.communicate()
        self.assertEquals(p.returncode, 1)
        self.assertIn("ValueError: stdin is not supported", error)
        
    def test_no_files(self):
        'run cat  test/data/test-includes.h | clang2py'
        p = Popen(['clang2py', '-o', '/dev/null'], 
                  stdin=PIPE, 
                  stdout=PIPE, 
                  stderr=PIPE,
                  bufsize=-1)
        output, error = p.communicate()
        self.assertEquals(p.returncode, 2)
        self.assertIn("error: too few arguments", error)


class Arguments(ClangTest):
    #@unittest.skip('')

    def test_include_with(self):
        ' run clang2py -i test/data/test-includes.h'
        p = Popen(['clang2py', '-i', 'test/data/test-includes.h'], 
                  stdin=PIPE, 
                  stdout=PIPE, 
                  stderr=PIPE,
                  bufsize=-1)
        output, error = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertIn("struct_Name", output)
        self.assertIn("struct_Name2", output)
        self.assertIn("struct_Name3", output)

    def test_include_without(self):
        ' run clang2py test/data/test-includes.h'
        p = Popen(['clang2py', 'test/data/test-includes.h'], 
                  stdin=PIPE, 
                  stdout=PIPE, 
                  stderr=PIPE,
                  bufsize=-1)
        output, error = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertIn("struct_Name", output)
        self.assertIn("struct_Name3", output)
        self.assertNotIn("struct_Name2", output)


if __name__ == "__main__":
    unittest.main()
