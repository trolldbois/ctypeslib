import unittest
import datetime
import textwrap

from test.util import ClangTest

"""Test if macro are correctly generated.
"""

import logging  # noqa

# logging.basicConfig(level=logging.DEBUG)


class Macro(ClangTest):
    # @unittest.skip('')

    def setUp(self):
        # we need to generate macro. Which is very long for some reasons.
        self.full_parsing_options = True

    def test_bitwise(self):
        self.convert(textwrap.dedent("""
            #define FOO(foo) (foo & 0x0FFFF)
        """))
        # print(self.text_output)
        self.assertEqual(self.namespace.FOO(0x1ABCD), 0x0ABCD)

    def test_va_args(self):
        self.convert(textwrap.dedent("""
            #define FOO(...) ("foo", __VA_ARGS__, "bar")
            #define BAR(a, b, c) FOO(c, b, a)
        """))
        # print(self.text_output)
        self.assertEqual(self.namespace.BAR(1, 2, 3), ("foo", 3, 2, 1, "bar"))

    def test_stdint(self):
        self.gen("test/data/stdint.h")
        # print(self.text_output)
        self.assertEqual(self.namespace.INT8_MIN, -128)
        self.assertEqual(self.namespace.INT16_MIN, -32767 - 1)
        self.assertEqual(self.namespace.INT32_MIN, -2147483647 - 1)
        self.assertEqual(self.namespace.INT64_MIN, -9223372036854775807 - 1)

        self.assertEqual(self.namespace.INT8_MAX, 127)
        self.assertEqual(self.namespace.INT16_MAX, 32767)
        self.assertEqual(self.namespace.INT32_MAX, 2147483647)
        self.assertEqual(self.namespace.INT64_MAX, 9223372036854775807)

        self.assertEqual(self.namespace.UINT8_MAX, 255)
        self.assertEqual(self.namespace.UINT16_MAX, 65535)
        self.assertEqual(self.namespace.UINT32_MAX, 4294967295)
        self.assertEqual(self.namespace.UINT64_MAX, 18446744073709551615)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    unittest.main(verbosity=2)
