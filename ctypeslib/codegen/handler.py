"""Abstract Handler with helper methods."""

from clang.cindex import CursorKind, TypeKind

from ctypeslib.codegen import typedesc
from ctypeslib.codegen.util import log_entity

import logging
log = logging.getLogger('handler')

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

    def remove_registered(self, name):
        return self.parser.remove_registered(name)

    def set_location(self, obj, cursor):
        """ Location is also used for codegeneration ordering."""
        if (hasattr(cursor, 'location') and cursor.location is not None and
                cursor.location.file is not None):
            obj.location = (cursor.location.file.name, cursor.location.line)
        return

    def set_comment(self, obj, cursor):
        """ If a comment is available, add it to the typedesc."""
        if isinstance(obj, typedesc.T):
            obj.comment = cursor.brief_comment
        return

    def make_python_name(self, name):
        """Transforms an USR into a valid python name."""
        # FIXME see cindex.SpellingCache
        for k, v in [('<', '_'), ('>', '_'), ('::', '__'), (',', ''), (' ', ''),
                     ("$", "DOLLAR"), (".", "DOT"), ("@", "_"), (":", "_"),
                     ('-', '_')]:
            if k in name:  # template
                name = name.replace(k, v)
            # FIXME: test case ? I want this func to be neutral on C valid
            # names.
            if name.startswith("__"):
                return "_X" + name
        if len(name) == 0:
            raise ValueError
        elif name[0] in "01234567879":
            return "_" + name
        return name

    def _get_anon_name(self, cursor):
        '''Creates a name for anonymous fields'''
        # .spelling and .diplayname are ''
        # get the field number
        parent = cursor.semantic_parent
        if parent.kind not in [CursorKind.STRUCT_DECL,CursorKind.UNION_DECL,CursorKind.CLASS_DECL,CursorKind.FIELD_DECL]:
            log.debug('Parent is a root %s', parent.kind)
            return ''
        
        #log.debug('Asking parent get_unique_name')
        pname = self.get_unique_name(parent)
        log.debug('_get_anon_name: Got parent get_unique_name %s',pname)
        # cursor is a FIELD_DECL. we need the {STRUCT,UNION}_DECL
        _cursor_decl = cursor.type.get_declaration()

        if '/' in pname or pname=='struct_':
            print "pname is struct_"
            import code
            code.interact(local=locals())
        
        _t = None
        _i = 0
        found = False
        # Look at the parent fields to find myself
        if cursor.is_definition():
            for m in parent.get_children():
                log.debug('childs i:%d cursor.kind %s',_i,cursor.kind)
                log.debug('childs i:%d %s',_i, cursor.spelling)
                if m == _cursor_decl:
                    found = True
                    break
                _i+=1
        else:
            for m in parent.type.get_fields():
                log.debug('fields i:%d cursor.kind %s',_i,cursor.kind)
                log.debug('fields i:%d %s',_i, cursor.spelling)
                if m == cursor:
                    found = True
                    break
                _i+=1
        if not found:
            print 'BUG'
            import code
            code.interact(local=locals())
            raise NotImplementedError("BUG cursor location %s"%cursor.location)
        
        # cursor is FIELD_DECL, we need to find out if its a struct or a union
        _akind = cursor.type.get_declaration().kind
        if _akind == CursorKind.UNION_DECL:
            _t = 'Ua'
        elif _akind == CursorKind.STRUCT_DECL:
            _t = 'Sa'
        else:
            raise NotImplementedError("Not sure what kind of member that is %s"%_akind)
        # truncate parent name to remove the first part ( union or struct)
        _premainer = '_'.join(pname.split('_')[1:])
        name = '%s_%d%s'%(_premainer,_i,_t)
        return name


    def get_unique_name(self, cursor):
        name = ''
        from clang import cindex
        record_kind=[CursorKind.STRUCT_DECL,CursorKind.UNION_DECL,CursorKind.CLASS_DECL,CursorKind.FIELD_DECL]
        if cursor.kind in record_kind and (
            cursor.is_anonymous() or cursor.spelling == ''):
                #print 'anon kind is ', cursor.kind
                #print 'location', cursor.location
                #print 'get_usr', cursor.get_usr()
                #log.debug('Anonymous cursor, building name')
                name = self._get_anon_name(cursor)
                log.debug('Anonymous cursor, got name %s',name)
                #import code
                #code.interact(local=locals())
                
        elif hasattr(cursor, 'displayname'):
            name = cursor.displayname
        elif hasattr(cursor, 'spelling'):
            name = cursor.spelling
        if name == '' :#and hasattr(
            #cursor, 'get_usr'):
            log.error('get_unique_name: empty name and this is kind %s',cursor.kind)  
            #import code
            #code.interact(local=locals())
            # FIXME: 
            # BUG : name collision between to union field siblings children
            # we need to find a unique identifier for this anonymous struct.
            # would be nice to have a unique identifier based on the semantic parent
            # clang says
            '''A Unified Symbol Resolution (USR) is a string that identifies a
        particular entity (function, class, variable, etc.) within a
        program.'''
            '''
>>> cursor.get_usr()
'c:@S@_HEAP_ENTRY@Ua@Sa@Ua@Sa'
>>> x=list(cursor.semantic_parent.get_children())
>>> x[0].get_usr()
'c:@S@_HEAP_ENTRY@Ua@Sa@Ua@Sa'
>>> x[1].get_usr()
'c:@S@_HEAP_ENTRY@Ua@Sa@Ua@Sa'
'''
            # so we need to use the parent field name to construct it.
            # TODO: recurse on semantic_parent to reconstruct the field id 
            # of all anonymous siblings
            # cf codegenerator:531.
            #_id = cursor.get_usr()
        #    _id = self._get_anon_name(cursor)
            #if _id == '':  # anonymous is spelling == ''
            #    return None
        #    name = self.make_python_name(_id)
        #if cursor.kind == CursorKind.STRUCT_DECL:
        #    name = 'struct_%s' % (name)
        #elif cursor.kind == CursorKind.UNION_DECL:
        #    name = 'union_%s' % (name)
        #elif cursor.kind == CursorKind.CLASS_DECL:
        #    name = 'class_%s' % (name)
        #elif cursor.kind == CursorKind.TYPE_REF:
        #    name = name.replace(' ', '_')
        _prefix = None
        names= {CursorKind.STRUCT_DECL: 'struct_',
                CursorKind.UNION_DECL: 'union_',
                CursorKind.CLASS_DECL: 'class_',
                CursorKind.TYPE_REF: '_'}
        if cursor.kind in names:
            _prefix = names[cursor.kind]
        name = '%s%s' % (_prefix or '', name)
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
                t.kind == TypeKind.DEPENDENTSIZEDARRAY)

    def is_unexposed_type(self, t):
        return t.kind == TypeKind.UNEXPOSED

    def is_literal_cursor(self, t):
        return (t.kind == CursorKind.INTEGER_LITERAL or
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
                    TypeKind.SCHAR, TypeKind.WCHAR]  # DEBUG
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

    def parse_cursor(self, cursor):
        return self.parser.parse_cursor(cursor)

    def parse_cursor_type(self, _cursor_type):
        return self.parser.parse_cursor_type(_cursor_type)

    ################################
    # do-nothing element handlers

    @log_entity
    def _pass_through_children(self, node, **args):
        for child in node.get_children():
            self.parser.startElement(child)
        return True

    def _do_nothing(self, node, **args):
        name = self.get_unique_name(node)
        #import code
        # code.interact(local=locals())
        log.warning('_do_nothing for %s/%s',node.kind.name, name)
        return True

    ###########################################
    # TODO FIXME: 100% cursor/type Kind coverage
    def __getattr__(self, name, **args):
        if name not in self._unhandled:
            log.warning('%s is not handled',name)
            self._unhandled.append(name)
        return self._do_nothing
