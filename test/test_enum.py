import unittest
import ctypes

from test.util import ClangTest


class EnumTest(ClangTest):

    """Test if Enum are correctly generated.
    """

    def test_enum(self):
        """
        """
        flags = ['-target', 'i386-linux']
        self.gen('test/data/test-enum.c', flags)
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEqual(self.namespace.ZERO, 0)
        self.assertEqual(self.namespace.ONE, 1)
        self.assertEqual(self.namespace.FOUR, 4)

    def test_enum_short_option(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.gen('test/data/test-enum.c', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum_byte), 1)
        self.assertEqual(self.namespace.MY_ENUM_BYTE_ZERO, 0)
        self.assertEqual(self.namespace.MY_ENUM_BYTE_MAX, 0xFF)

        # Expect enum stored in 2 bytes
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum_int16), 2)
        self.assertEqual(self.namespace.MY_ENUM_INT16_ZERO, 0)
        self.assertEqual(self.namespace.MY_ENUM_INT16_MAX, 0xFFFF)

        # Expect enum stored in 4 bytes
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum_int32), 4)
        self.assertEqual(self.namespace.MY_ENUM_INT32_ZERO, 0)
        self.assertEqual(self.namespace.MY_ENUM_INT32_MAX, 0xFFFFFFFF)

    def test_enum_no_short_option(self):
        """
        By default, enums are stored as 'int', so they will occupy 4 bytes.
        """
        flags = ['-target', 'i386-linux']
        self.gen('test/data/test-enum.c', flags)

        # Expect enum stored as 'int'
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum_byte), 4)
        self.assertEqual(self.namespace.MY_ENUM_BYTE_ZERO, 0)
        self.assertEqual(self.namespace.MY_ENUM_BYTE_MAX, 0xFF)

        # Expect enum stored as 'int'
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum_int16), 4)
        self.assertEqual(self.namespace.MY_ENUM_INT16_ZERO, 0)
        self.assertEqual(self.namespace.MY_ENUM_INT16_MAX, 0xFFFF)

        # Expect enum stored as 'int'
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum_int32), 4)
        self.assertEqual(self.namespace.MY_ENUM_INT32_ZERO, 0)
        self.assertEqual(self.namespace.MY_ENUM_INT32_MAX, 0xFFFFFFFF)


if __name__ == "__main__":
    # logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    # logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main()
