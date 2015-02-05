import unittest
import sys
from ctypeslib import clang2py


class ToolchainTest(unittest.TestCase):
    if sys.platform == "win32":
        def test_windows(self):
            clang2py.main(["clang2py",
                           "-c",
                           "-w",
                           "-m", "ctypes.wintypes",
                           "-o", "_winapi_gen.py",
                           "windows.h"
                           ])
            import _winapi_gen

    def test(self):
        clang2py.main(["clang2py",
                       "-c",
                       "-o", "_stdio_gen.xml",
                       "stdio.h"
                       ])
        import _stdio_gen


if __name__ == "__main__":
    import unittest
    unittest.main()
