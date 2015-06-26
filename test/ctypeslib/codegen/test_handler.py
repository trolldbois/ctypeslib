import unittest
import ctypes

from ctypeslib.codegen import handler


class FakeParser():
    pass

class HandlerTest(unittest.TestCase):

    """
    """

    def setUP(self):
        self.parser = None
        self.handler = handler.ClangHandler(parser)

    def test_get_unique_name(self):
        """
        """



import logging
import sys
if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    # logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main()
