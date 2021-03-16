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

    def test_enum_short_option_uint8(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN=0,   /* UINT8_MIN */
            MAX=0xFF /* UINT8_MAX */
        };
        ''', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 1)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFF)

    def test_enum_short_option_uint16(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN=0,      /* UINT16_MIN */
            MAX=0xFFFF  /* UINT16_MAX */
        };
        ''', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 2)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFFFF)

    def test_enum_short_option_uint32(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN=0,          /* UINT32_MIN */
            MAX=0xFFFFFFFF  /* UINT32_MAX */
        };
        ''', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFFFFFFFF)

    def test_enum_short_option_int8(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN=-128, /* INT8_MIN */
            MAX= 127  /* INT8_MAX */
        };
        ''', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 1)
        self.assertEqual(self.namespace.MIN, -128)
        self.assertEqual(self.namespace.MAX, 127)

    def test_enum_short_option_int16(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN=-32768, /* INT16_MIN */
            MAX= 32767  /* INT16_MAX*/
        };
        ''', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 2)
        self.assertEqual(self.namespace.MIN, -32768)
        self.assertEqual(self.namespace.MAX, 32767)

    def test_enum_short_option_int32(self):
        """
        Enums can be forced to occupy less space than an int if possible:
          1) Add the attribute `__attribute__((__packed__))` to the C variable declarations
          2) Set the compiler flag ` CFLAGS += -fshort-enums`
        In any case, we should trust the enum size returned by the compiler.
        """
        flags = ['-target', 'i386-linux', '-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN=-65536, /* INT32_MIN */
            MAX= 65535  /* INT32_MAX*/
        };
        ''', flags)

        # Expect enum stored as 1 byte
        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEqual(self.namespace.MIN, -65536)
        self.assertEqual(self.namespace.MAX, 65535)


if __name__ == "__main__":
    # logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    # logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main()
