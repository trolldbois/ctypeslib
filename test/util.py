# From clang/bindings/python/cindex/test
# This file provides common utility functions for the test suite.
#

import ctypes 
import os
from clang.cindex import Cursor
from clang.cindex import TranslationUnit
import unittest
from ctypeslib.codegen import clangparser, codegenerator
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

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
    assert type(flags) == list
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
    def gen(self, fname, flags=[]):
        """Take a file input and generate the code.
        """ 
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
        #print ofi.getvalue()
        # DEBUG 
        exec ofi.getvalue() in namespace
        self.namespace = ADict(namespace)
        return

    def convert(self, src_code, flags=[]):
        """Take a string input, write it into a temp file and the code.
        """ 
        hfile = mktemp(".h")
        open(hfile, "w").write(src_code)
        try:
            self.gen(hfile, flags)
        finally:
            os.unlink(hfile)
        return

    def _get_target_with_struct_hack(self, name):
        """ # HACK FIXME: because we rename "struct x" to struct_x, we have to hack
        """
        target = get_cursor(self.parser.tu, name)
        if target is None:
            target = get_cursor(self.parser.tu, name.replace('struct_',''))
        if target is None:
            target = get_cursor(self.parser.tu, name.replace('union_',''))
        return target
            
    def assertSizes(self, name):
        """ Compare size of records using clang sizeof versus python sizeof.""" 
        target = self._get_target_with_struct_hack(name)
        self.assertTrue(target is not None, '%s was not found in source'%name )
        _clang = target.type.get_size()
        _python = ctypes.sizeof(getattr(self.namespace,name))
        self.assertEquals( _clang, _python, 
            'Sizes for target: %s Clang:%d Python:%d flags:%s'%(name, _clang, 
             _python, self.parser.flags))
        return
    
    def assertOffsets(self, name):
        """ Compare offset of records' fields using clang offsets versus 
        python offsets."""
        target = self._get_target_with_struct_hack(name)
        target = target.type.get_declaration()
        self.assertTrue(target is not None, '%s was not found in source'%name )
        members = [c.displayname for c in target.get_children() 
                   if c.kind.name == 'FIELD_DECL']
        _clang_type = target.type
        _python_type = getattr(self.namespace,name)
        # Does not handle bitfield
        for member in members:
            _c_offset = _clang_type.get_offset(member)
            _p_offset = 8*getattr(_python_type, member).offset
            self.assertEquals( _c_offset, _p_offset, 
                'Offsets for target: %s.%s Clang:%d Python:%d flags:%s'%(
                    name, member, _c_offset, _p_offset, self.parser.flags))
        return

__all__ = [
    'get_cursor',
    'get_cursors',
    'get_tu',
    'ArchTest',
]
