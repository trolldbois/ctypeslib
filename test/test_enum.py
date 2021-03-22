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
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = 0,   /* UINT8_MIN */
            MAX = 0xFF /* UINT8_MAX */
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 1)
        self.assertEqual(self.namespace.myEnum, ctypes.c_uint8)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFF)

    def test_enum_short_option_uint16(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = 0,      /* UINT16_MIN */
            MAX = 0xFFFF  /* UINT16_MAX */
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 2)
        self.assertEqual(self.namespace.myEnum, ctypes.c_uint16)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFFFF)

    def test_enum_short_option_uint32(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = 0,          /* UINT32_MIN */
            MAX = 0xFFFFFFFF  /* UINT32_MAX */
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEqual(self.namespace.myEnum, ctypes.c_uint32)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFFFFFFFF)

    def test_enum_short_option_uint64(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = 0,                  /* UINT64_MIN */
            MAX = 0xFFFFFFFFFFFFFFFF  /* UINT64_MAX*/
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 8)
        self.assertEqual(self.namespace.myEnum, ctypes.c_uint64)
        self.assertEqual(self.namespace.MIN, 0)
        self.assertEqual(self.namespace.MAX, 0xFFFFFFFFFFFFFFFF)

    def test_enum_short_option_int8(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = (-0x7F - 1), /* INT8_MIN */
            MAX =   0x7F       /* INT8_MAX */
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 1)
        self.assertEqual(self.namespace.myEnum, ctypes.c_int8)
        self.assertEqual(self.namespace.MIN, (-0x7F - 1))
        self.assertEqual(self.namespace.MAX,   0x7F)

    def test_enum_short_option_int16(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = (-0x7FFF - 1), /* INT16_MIN */
            MAX =   0x7FFF       /* INT16_MAX*/
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 2)
        self.assertEqual(self.namespace.myEnum, ctypes.c_int16)
        self.assertEqual(self.namespace.MIN, (-0x7FFF - 1))
        self.assertEqual(self.namespace.MAX,   0x7FFF)

    def test_enum_short_option_int32(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN = (-0x7FFFFFFF - 1), /* INT32_MIN */
            MAX =   0x7FFFFFFF       /* INT32_MAX*/
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 4)
        self.assertEqual(self.namespace.myEnum, ctypes.c_int32)
        self.assertEqual(self.namespace.MIN, (-0x7FFFFFFF - 1))
        self.assertEqual(self.namespace.MAX,   0x7FFFFFFF)

    def test_enum_short_option_int64(self):
        """
        Test the enum size when compiler flag '-fshort-enums' is used.
        Test the signedness of the enum, based on the sign of the values it contains.
        """
        flags = ['-fshort-enums']
        self.convert(
            '''
        enum myEnum {
            MIN =(-0x7FFFFFFFFFFFFFFF - 1), /* INT64_MIN */
            MAX =  0x7FFFFFFFFFFFFFFF       /* INT64_MAX*/
        };
        ''', flags)

        self.assertEqual(ctypes.sizeof(self.namespace.myEnum), 8)
        self.assertEqual(self.namespace.myEnum, ctypes.c_int64)
        self.assertEqual(self.namespace.MIN, (-0x7FFFFFFFFFFFFFFF - 1))
        self.assertEqual(self.namespace.MAX,   0x7FFFFFFFFFFFFFFF)


if __name__ == "__main__":
    # logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    # logging.getLogger('codegen').setLevel(logging.INFO)
    unittest.main()
