import unittest
import sys
from ctypeslib import h2xml, xml2py

class ToolchainTest(unittest.TestCase):
    if sys.platform == "win32":
        def test(self):
            h2xml.main(["h2xml", "-q",
                        "-D WIN32_LEAN_AND_MEAN",
                        "-D _UNICODE", "-D UNICODE",
                        "-c", "windows.h",
                        "-o", "_windows_gen.xml"])
            xml2py.main(["xml2py", "_windows_gen.xml", "-w", "-o", "_winapi_gen.py"])
            import _winapi_gen

if __name__ == "__main__":
    import unittest
    unittest.main()
