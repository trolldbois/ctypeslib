# From clang/bindings/python/cindex/test
# This file provides common utility functions for the test suite.
#

import ctypes
import os
from io import StringIO
from ctypes import RTLD_GLOBAL

from clang.cindex import Cursor
from clang.cindex import TranslationUnit
import unittest
from ctypeslib.codegen import clangparser, codegenerator
from ctypeslib.library import Library

import tempfile


def mktemp(suffix):
    handle, fnm = tempfile.mkstemp(suffix)
    os.close(handle)
    return fnm


def get_tu(source, lang='c', all_warnings=False, flags=[]):
    """Obtain a translation unit from source and language.

    By default, the translation unit is created from source file "t.<ext>"
    where <ext> is the default file extension for the specified language. By
    default it is C, so "t.c" is the default file name.

    Supported languages are {c, cpp, objc}.

    all_warnings is a convenience argument to enable all compiler warnings.
    """
    assert isinstance(flags, list)
    args = list(flags)
    name = 't.c'
    if lang == 'cpp':
        name = 't.cpp'
        args.append('-std=c++11')
    elif lang == 'objc':
        name = 't.m'
    elif lang != 'c':
        raise Exception('Unknown language: %s' % lang)

    if all_warnings:
        args += ['-Wall', '-Wextra']

    return TranslationUnit.from_source(name, args, unsaved_files=[(name,
                                                                   source)])


def get_cursor(source, spelling):
    """Obtain a cursor from a source object.

    This provides a convenient search mechanism to find a cursor with specific
    spelling within a source. The first argument can be either a
    TranslationUnit or Cursor instance.

    If the cursor is not found, None is returned.
    """
    children = []
    if isinstance(source, Cursor):
        children = source.get_children()
    else:
        # Assume TU
        children = source.cursor.get_children()

    for cursor in children:
        if cursor.spelling == spelling:
            return cursor

        # Recurse into children.
        result = get_cursor(cursor, spelling)
        if result is not None:
            return result

    return None


def get_cursors(source, spelling):
    """Obtain all cursors from a source object with a specific spelling.

    This provides a convenient search mechanism to find all cursors with specific
    spelling within a source. The first argument can be either a
    TranslationUnit or Cursor instance.

    If no cursors are found, an empty list is returned.
    """
    cursors = []
    children = []
    if isinstance(source, Cursor):
        children = source.get_children()
    else:
        # Assume TU
        children = source.cursor.get_children()

    for cursor in children:
        if cursor.spelling == spelling:
            cursors.append(cursor)

        # Recurse into children.
        cursors.extend(get_cursors(cursor, spelling))

    return cursors


class ADict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class ClangTest(unittest.TestCase):
    namespace = None
    full_parsing_options = False

    def _gen(self, ofi, fname, flags=None, dlls=None):
        """Take a file input and generate the code.
        """
        flags = flags or []
        dlls = dlls or []
        dlls = [Library(name, RTLD_GLOBAL, nm=None) for name in dlls]
        # leave the new parser accessible for tests
        self.parser = clangparser.Clang_Parser(flags)
        if self.full_parsing_options:
            self.parser.activate_macros_parsing()
            self.parser.activate_comment_parsing()
        with open(fname):
            pass
        self.parser.parse(fname)
        items = self.parser.get_result()
        # gen code
        gen = codegenerator.Generator(ofi, searched_dlls=dlls)
        gen.generate_headers(self.parser)
        gen.generate_code(items)
        return gen

    def gen(self, fname, flags=None, dlls=[], debug=False):
        """Take a file input and generate the code.
        """
        flags = flags or []
        dlls = dlls or []
        ofi = StringIO()
        gen = self._gen(ofi, fname, flags=flags, dlls=dlls)
        # load code
        namespace = {}
        # DEBUG
        # print ofi.getvalue()
        # DEBUG
        ofi.seek(0)
        ignore_coding = ofi.readline()
        # exec ofi.getvalue() in namespace
        output = ''.join(ofi.readlines())
        try:
            # PY3 change
            exec(output, namespace)
        except Exception:
            print(output)
            raise
        # except NameError:
        #     print(output)
        self.namespace = ADict(namespace)
        if debug:
            print(output)
        return

    def convert(self, src_code, flags=[], debug=False):
        """Take a string input, write it into a temp file and the code.
        """
        hfile = mktemp(".h")
        with open(hfile, "w") as f:
            f.write(src_code)
        try:
            self.gen(hfile, flags, debug)
        finally:
            os.unlink(hfile)
        return

    def _get_target_with_struct_hack(self, name):
        """ because we rename "struct x" to struct_x, we have to reverse that
        """
        target = get_cursor(self.parser.tu, name)
        if target is None:
            target = get_cursor(self.parser.tu, name.replace('struct_', ''))
        if target is None:
            target = get_cursor(self.parser.tu, name.replace('union_', ''))
        return target

    def assertSizes(self, name):
        """ Compare size of records using clang sizeof versus python sizeof."""
        target = self._get_target_with_struct_hack(name)
        self.assertTrue(
            target is not None,
            '%s was not found in source' %
            name)
        _clang = target.type.get_size()
        _python = ctypes.sizeof(getattr(self.namespace, name))
        self.assertEqual(_clang, _python,
                         'Sizes for target: %s Clang:%d Python:%d flags:%s' % (name, _clang,
                                                                               _python, self.parser.flags))
        return

    def assertOffsets(self, name):
        """ Compare offset of records' fields using clang offsets versus
        python offsets.
        name: the name of the structure.
        The findings and offset comparaison of members fields is automatic.
        """
        target = self._get_target_with_struct_hack(name)
        target = target.type.get_declaration()
        self.assertTrue(
            target is not None,
            '%s was not found in source' %
            name)
        members = [(c.displayname, c) for c in target.type.get_fields()]
        _clang_type = target.type
        _python_type = getattr(self.namespace, name)
        # let'shandle bitfield - precalculate offsets
        fields_offsets = dict()
        for field_desc in _python_type._fields_:
            _n = field_desc[0]
            _f = getattr(_python_type, _n)
            bfield_bits = _f.size >> 16
            if bfield_bits:
                ofs = 8 * _f.offset + _f.size & 0xFFFF
            else:
                ofs = 8 * _f.offset
            # base offset
            fields_offsets[_n] = ofs
        # now use that
        for i, (membername, field) in enumerate(members):
            # anonymous fields
            if membername == '':
                membername = '_%d' % i
            # _c_offset = _clang_type.get_offset(member)
            _c_offset = field.get_field_offsetof()
            # _p_offset = 8*getattr(_python_type, member).offset
            _p_offset = fields_offsets[membername]
            self.assertEqual(_c_offset, _p_offset,
                             'Offsets for target: %s.%s Clang:%d Python:%d flags:%s' % (
                                 name, membername, _c_offset, _p_offset, self.parser.flags))
        return


__all__ = [
    'get_cursor',
    'get_cursors',
    'get_tu',
    'ArchTest',
]
