# From clang/bindings/python/cindex/test
# This file provides common utility functions for the test suite.
#

import ctypes 
from clang.cindex import Cursor
from clang.cindex import TranslationUnit
import unittest
from ctypeslib.codegen import clangparser, codegenerator
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


def get_tu(source, lang='c', all_warnings=False, flags=[]):
    """Obtain a translation unit from source and language.

    By default, the translation unit is created from source file "t.<ext>"
    where <ext> is the default file extension for the specified language. By
    default it is C, so "t.c" is the default file name.

    Supported languages are {c, cpp, objc}.

    all_warnings is a convenience argument to enable all compiler warnings.
    """
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

class ArchTest(unittest.TestCase):
    word_size = None
    def gen(self, fname, flags=None):
        ofi = StringIO()
        # leave the new parser accessible for tests
        self.parser = clangparser.Clang_Parser(flags)
        with open(fname):
            pass
        self.parser.parse(fname)
        items = self.parser.get_result()
        # gen code
        gen = codegenerator.Generator(ofi)
        gen.generate_headers(self.parser)
        gen.generate_code(items)
        # load code 
        namespace = {}
        # DEBUG
        print ofi.getvalue()
        # DEBUG 
        exec ofi.getvalue() in namespace
        return ADict(namespace)
    

__all__ = [
    'get_cursor',
    'get_cursors',
    'get_tu',
    'ArchTest',
]
