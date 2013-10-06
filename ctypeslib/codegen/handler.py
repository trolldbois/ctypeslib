"""Abstract Handler with helper methods."""

from clang.cindex import CursorKind, TypeKind

from ctypeslib.codegen import typedesc
from ctypeslib.codegen.util import log_entity

import logging
log = logging.getLogger('handler')

## DEBUG
import code 

class CursorKindException(TypeError):
    """When a child node of a VAR_DECL is parsed as an initialization value, 
    when its not actually part of that initiwlization value."""
    pass

class InvalidDefinitionError(TypeError):
    """When a structure is invalid in the source code,  sizeof, alignof returns
    negatives value. We detect it and do our best."""
    pass

class DuplicateDefinitionException(KeyError):
    """When we encounter a duplicate declaration/definition name."""
    pass


################################################################

def MAKE_NAME(name):
    ''' Transforms an USR into a valid python name.
    '''
    # FIXME see cindex.SpellingCache
    for k, v in [('<','_'), ('>','_'), ('::','__'), (',',''), (' ',''),
                 ("$", "DOLLAR"), (".", "DOT"), ("@", "_"), (":", "_")]:
        if k in name: # template
            name = name.replace(k,v)
    #FIXME: test case ? I want this func to be neutral on C valid names.
    if name.startswith("__"):
        return "_X" + name
    elif len(name) == 0:
        raise ValueError
    elif name[0] in "01234567879":
        return "_" + name
    return name

class ClangHandler(object):
    """
    Abstract class for handlers.
    """
    def __init__(self, parser):
        self.parser = parser
        self._unhandled = []

    def register(self, name, obj):
        return self.parser.register(name, obj)

    def get_registered(self, name):
        return self.parser.get_registered(name)

    def is_registered(self, name):
        return self.parser.is_registered(name)

    def set_location(self, obj, cursor):
        """ Location is also used for codegeneration ordering."""
        if ( hasattr(cursor, 'location') and cursor.location is not None 
             and cursor.location.file is not None):
            obj.location = (cursor.location.file.name, cursor.location.line)
        return
        
    def set_comment(self, obj, cursor):
        """ If a comment is available, add it to the typedesc."""
        if isinstance(obj, typedesc.T):
            obj.comment = cursor.brief_comment
        return
        
    def get_unique_name(self, cursor):
        name = ''
        if hasattr(cursor, 'displayname'):
            name = cursor.displayname
        elif hasattr(cursor, 'spelling'):
            name = cursor.spelling
        if name == '' and hasattr(cursor,'get_usr'): #FIXME: should not get Type
            _id = cursor.get_usr()
            if _id == '': # anonymous is spelling == ''
                return None
            name = MAKE_NAME( _id )
        if cursor.kind == CursorKind.STRUCT_DECL:
            name = 'struct_%s'%(name)
        elif cursor.kind == CursorKind.UNION_DECL:
            name = 'union_%s'%(name)
        elif cursor.kind == CursorKind.CLASS_DECL:
            name = 'class_%s'%(name)
        elif cursor.kind == CursorKind.TYPE_REF:
            name = name.replace(' ', '_')
        return name

    def is_fundamental_type(self, t):
        return (not self.is_pointer_type(t) and 
                t.kind in self.parser.ctypes_typename.keys())

    def is_pointer_type(self, t):
        return t.kind == TypeKind.POINTER

    def is_array_type(self, t):
        return (t.kind == TypeKind.CONSTANTARRAY or
                t.kind == TypeKind.INCOMPLETEARRAY or
                t.kind == TypeKind.VARIABLEARRAY or
                t.kind == TypeKind.DEPENDENTSIZEDARRAY )

    def is_unexposed_type(self, t):
        return t.kind == TypeKind.UNEXPOSED

    def is_literal_cursor(self, t):
        return ( t.kind == CursorKind.INTEGER_LITERAL or
                 t.kind == CursorKind.FLOATING_LITERAL or
                 t.kind == CursorKind.IMAGINARY_LITERAL or
                 t.kind == CursorKind.STRING_LITERAL or
                 t.kind == CursorKind.CHARACTER_LITERAL)

    def get_literal_kind_affinity(self, literal_kind):
        ''' return the list of fundamental types that are adequate for which 
        this literal_kind is adequate'''
        if literal_kind == CursorKind.INTEGER_LITERAL:
            return [TypeKind.USHORT, TypeKind.UINT, TypeKind.ULONG, 
                    TypeKind.ULONGLONG, TypeKind.UINT128, 
                    TypeKind.SHORT, TypeKind.INT, TypeKind.LONG, 
                    TypeKind.LONGLONG, TypeKind.INT128, ]
        elif literal_kind == CursorKind.STRING_LITERAL:
            return [TypeKind.CHAR16, TypeKind.CHAR32, TypeKind.CHAR_S, 
                    TypeKind.SCHAR, TypeKind.WCHAR ] ## DEBUG
        elif literal_kind == CursorKind.CHARACTER_LITERAL:
            return [TypeKind.CHAR_U, TypeKind.UCHAR]
        elif literal_kind == CursorKind.FLOATING_LITERAL:
            return [TypeKind.FLOAT, TypeKind.DOUBLE, TypeKind.LONGDOUBLE]
        elif literal_kind == CursorKind.IMAGINARY_LITERAL:
            return []
        return []

    def get_ctypes_name(self, typekind):
        return self.parser.get_ctypes_name(typekind)

    def get_ctypes_size(self, typekind):
        return self.parser.get_ctypes_size(typekind)

    ################################
    # do-nothing element handlers

    @log_entity
    def _pass_through_children(self, node, **args):
        for child in node.get_children():
            self.startElement( child ) 
        return True
        
    @log_entity
    def _do_nothing(self, node, **args):
        return True


    ###########################################
    # TODO FIXME:  only useful because we do not have 100% cursorKind coverage
    #def __getattr__(self, name, **args):
    #   if "_fixup" in name:
    #        raise NotImplementedError('name')
    #    if name not in self._unhandled:
    #        log.warning('%s is not handled'%(name))
    #        self._unhandled.append(name)
    #    return self._do_nothing


