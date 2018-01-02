import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ClangTest
import logging
import sys


class EnumTest(ClangTest):

    """Test if Enum are correctly generated.
    """

    def test_enum(self):
        """
        """
        flags = ['-target', 'i386-linux']
        self.gen('test/data/test-enum.c', flags)
        self.assertEquals(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEquals(self.namespace.ZERO, 0)
        self.assertEquals(self.namespace.ONE, 1)
        self.assertEquals(self.namespace.FOUR, 4)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    # logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main()
