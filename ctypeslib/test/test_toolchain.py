import unittest
import sys
from ctypeslib import h2xml, xml2py

class ToolchainTest(unittest.TestCase):
    if sys.platform == "win32":
        def test_windows(self):
            h2xml.main(["h2xml", "-q",
                        "-D WIN32_LEAN_AND_MEAN",
                        "-D _UNICODE", "-D UNICODE",
                        "-D", "NO_STRICT",
                        "-c", "windows.h",
                        "-o", "_windows_gen.xml"])
            xml2py.main(["xml2py", "_windows_gen.xml",
                         "-w",
                         "-m", "ctypes.wintypes",
                         "-o", "_winapi_gen.py"])
            import _winapi_gen

    def test(self):
        h2xml.main(["h2xml", "-q",
                    "-c", "stdio.h",
                    "-o", "_stdio_gen.xml"])
        if sys.platform == "win32":
            xml2py.main(["xml2py", "_stdio_gen.xml", "-l", "msvcrt", "-o", "_stdio_gen.py"])
        else:
            xml2py.main(["xml2py", "_stdio_gen.xml", "-l", "c", "-o", "_stdio_gen.py"])
        import _stdio_gen


if __name__ == "__main__":
    import unittest
    unittest.main()
