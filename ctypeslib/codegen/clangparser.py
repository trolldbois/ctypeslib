"""clangparser - use clang to get preprocess a source code."""

import clang
from clang.cindex import Index, TranslationUnit
from clang.cindex import CursorKind, TypeKind, TokenKind

import logging

import typedesc
import re

from . import util

log = logging.getLogger('clangparser')

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

def decorator(dec):
    def new_decorator(f):
        g = dec(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    new_decorator.__name__ = dec.__name__
    new_decorator.__doc__ = dec.__doc__
    new_decorator.__dict__.update(dec.__dict__)
    return new_decorator

@decorator
def log_entity(func):
    def fn(*args, **kwargs):
        name = args[0].get_unique_name(args[1])
        if name == '':
            parent = args[1].semantic_parent
            if parent:
                name = 'child of %s'%parent.displayname
        log.debug("%s: displayname:'%s'"%(func.__name__, name))
        #print 'calling {}'.format(func.__name__)
        return func(*args, **kwargs)
    return fn

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

class Clang_Parser(object):
    '''Will parse libclang AST tree to create a representation of Types and
    different others source code objects objets as described in Typedesc.

    For each Declaration a declaration will be saved, and the type of that 
    declaration will be cached and saved.
    '''
    # clang.cindex.CursorKind
    ## Declarations: 1-39
    ## Reference: 40-49
    ## Invalids: 70-73
    ## Expressions: 100-143
    ## Statements: 200-231
    ## Root Translation unit: 300
    ## Attributes: 400-403
    ## Preprocessing: 500-503
    has_values = set(["Enumeration", "Function", "FunctionType",
                      "OperatorFunction", "Method", "Constructor",
                      "Destructor", "OperatorMethod",
                      "Converter"])

    # FIXME, macro definition __SIZEOF_DOUBLE__
    ctypes_typename = {
        TypeKind.VOID : 'void' ,
        TypeKind.BOOL : 'c_bool' ,
        TypeKind.CHAR_U : 'c_ubyte' ,
        TypeKind.UCHAR : 'c_ubyte' ,
        TypeKind.CHAR16 : 'c_wchar' , # char16_t
        TypeKind.CHAR32 : 'c_wchar' , # char32_t
        TypeKind.USHORT : 'TBD' ,
        TypeKind.UINT : 'TBD' ,
        TypeKind.ULONG : 'TBD' ,
        TypeKind.ULONGLONG : 'TBD' ,
        TypeKind.UINT128 : 'c_uint128' , # FIXME
        TypeKind.CHAR_S : 'c_char' , 
        TypeKind.SCHAR : 'c_char' , #? 
        TypeKind.WCHAR : 'c_wchar' , # 
        TypeKind.SHORT : 'TBD' ,
        TypeKind.INT : 'TBD' ,
        TypeKind.LONG : 'TBD' ,
        TypeKind.LONGLONG : 'TBD' ,
        TypeKind.INT128 : 'c_int128' , # FIXME
        TypeKind.FLOAT : 'c_float' , 
        TypeKind.DOUBLE : 'c_double' , 
        TypeKind.LONGDOUBLE : 'TBD' ,
        TypeKind.POINTER : 'POINTER_T'
    }
    
    def __init__(self, flags):
        self.all = {}
        self.cpp_data = {}
        self._unhandled = []
        self.fields = {}
        self.tu = None
        self.flags = flags
        self.ctypes_sizes = {}
        self.init_parsing_options()
        self.make_ctypes_convertor(flags)
        self.init_fundamental_types()
    
    def init_parsing_options(self):
        """Set the Translation Unit to skip functions bodies per default."""
        self.tu_options = TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    
    def activate_macros_parsing(self):
        """Activates the detailled code parsing options in the Translation 
        Unit."""
        self.tu_options |= TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

    def activate_comment_parsing(self):
        """Activates the comment parsing options in the Translation Unit."""
        self.tu_options |= TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION 
        
    def init_fundamental_types(self):
        """Registers all fundamental typekind handlers"""
        for _id in range(1,24):
            setattr(self, TypeKind.from_id(_id).name, 
                          self._handle_fundamental_types)

    '''. reads 1 file
    . if there is a compilation error, print a warning
    . get root cursor and recurse
    . for each STRUCT_DECL, register a new struct type
    . for each UNION_DECL, register a new union type
    . for each TYPEDEF_DECL, register a new alias/typdef to the underlying type
        - underlying type is cursor.type.get_declaration() for Record
    . for each VAR_DECL, register a Variable
    . for each TYPEREF ??
    '''
    def parse(self, filename):
        index = Index.create()
        self.tu = index.parse(filename, self.flags, options=self.tu_options)
        if not self.tu:
            log.warning("unable to load input")
            return
        if len(self.tu.diagnostics)>0:
            for x in self.tu.diagnostics:
                if x.severity > 2:
                    log.warning("Source code has some error. Please fix.")
                    break
        root = self.tu.cursor
        for node in root.get_children():
            self.startElement( node )
        return

    def startElement(self, node ): 
        if node is None:
            return
        # find and call the handler for this element
        mth = getattr(self, node.kind.name)
        if mth is None:
            return
        log.debug('Found a %s|%s|%s'%(node.kind.name, node.displayname, node.spelling))
        # build stuff.
        try:
            stop_recurse = mth(node)
            # Signature of mth is:
            # if the fn returns True, do not recurse into children.
            # anything else will be ignored.
            if stop_recurse is True:
                return        
            # if fn returns something, if this element has children, treat them.
            for child in node.get_children():
                self.startElement( child )
        except InvalidDefinitionError, e:
            pass 
        # startElement returns None.
        return None

    def register(self, name, obj):
        if name in self.all:
            log.debug('register: %s already existed: %s'%(name,obj.name))
            #code.interact(local=locals())
            raise DuplicateDefinitionException(
                            'register: %s already existed: %s'%(name,obj.name))
        log.debug('register: %s '%(name))
        self.all[name] = obj
        return obj

    def get_registered(self, name):
        return self.all[name]

    def is_registered(self, name):
        return name in self.all

    def set_location(self, obj, cursor):
        """ Location is also used for codegeneration ordering."""
        if ( hasattr(cursor, 'location') and cursor.location is not None 
             and cursor.location.file is not None):
            obj.location = (cursor.location.file.name, cursor.location.line)

    def set_comment(self, obj, cursor):
        """ If a comment is available, add it to the typedesc."""
        if isinstance(obj, typedesc.T):
            obj.comment = cursor.brief_comment

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

    ########################################################################
    ''' clang types to ctypes for architecture dependent size types
    '''
    def make_ctypes_convertor(self, _flags):
        tu = util.get_tu('''
typedef short short_t;
typedef int int_t;
typedef long long_t;
typedef long long longlong_t;
typedef float float_t;
typedef double double_t;
typedef long double longdouble_t;
typedef void* pointer_t;''', flags=_flags)
        size = util.get_cursor(tu, 'short_t').type.get_size()*8
        self.ctypes_typename[TypeKind.SHORT] = 'c_int%d'%(size)
        self.ctypes_typename[TypeKind.USHORT] = 'c_uint%d'%(size)
        self.ctypes_sizes[TypeKind.SHORT] = size
        self.ctypes_sizes[TypeKind.USHORT] = size

        size = util.get_cursor(tu, 'int_t').type.get_size()*8
        self.ctypes_typename[TypeKind.INT] = 'c_int%d'%(size)
        self.ctypes_typename[TypeKind.UINT] = 'c_uint%d'%(size)
        self.ctypes_sizes[TypeKind.INT] = size
        self.ctypes_sizes[TypeKind.UINT] = size

        size = util.get_cursor(tu, 'long_t').type.get_size()*8
        self.ctypes_typename[TypeKind.LONG] = 'c_int%d'%(size)
        self.ctypes_typename[TypeKind.ULONG] = 'c_uint%d'%(size)
        self.ctypes_sizes[TypeKind.LONG] = size
        self.ctypes_sizes[TypeKind.ULONG] = size

        size = util.get_cursor(tu, 'longlong_t').type.get_size()*8
        self.ctypes_typename[TypeKind.LONGLONG] = 'c_int%d'%(size)
        self.ctypes_typename[TypeKind.ULONGLONG] = 'c_uint%d'%(size)
        self.ctypes_sizes[TypeKind.LONGLONG] = size
        self.ctypes_sizes[TypeKind.ULONGLONG] = size
        
        #FIXME : Float && http://en.wikipedia.org/wiki/Long_double
        size0 = util.get_cursor(tu, 'float_t').type.get_size()*8
        size1 = util.get_cursor(tu, 'double_t').type.get_size()*8
        size2 = util.get_cursor(tu, 'longdouble_t').type.get_size()*8
        if size1 != size2:
            self.ctypes_typename[TypeKind.LONGDOUBLE] = 'c_long_double_t'
        else:
            self.ctypes_typename[TypeKind.LONGDOUBLE] = 'c_double'
        
        self.ctypes_sizes[TypeKind.FLOAT] = size0
        self.ctypes_sizes[TypeKind.DOUBLE] = size1
        self.ctypes_sizes[TypeKind.LONGDOUBLE] = size2

        # save the target pointer size.
        size = util.get_cursor(tu, 'pointer_t').type.get_size()*8
        self.ctypes_sizes[TypeKind.POINTER] = size
        
        log.debug('ARCH sizes: long:%s longdouble:%s'%(
                self.ctypes_typename[TypeKind.LONG],
                self.ctypes_typename[TypeKind.LONGDOUBLE]))
    
    def is_fundamental_type(self, t):
        return (not self.is_pointer_type(t) and 
                t.kind in self.ctypes_typename.keys())

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
        return self.ctypes_typename[typekind]

    def get_ctypes_size(self, typekind):
        return self.ctypes_sizes[typekind]
        
    def parse_cursor(self, cursor):
        mth = getattr(self, cursor.kind.name)
        return mth(cursor)

    def parse_cursor_type(self, _cursor_type):
        mth = getattr(self, _cursor_type.kind.name)
        return mth(_cursor_type)

    ################################
    # do-nothing element handlers

    @log_entity
    def _pass_through_children(self, node, **args):
        if isinstance(node, clang.cindex.Type):
            return None
        for child in node.get_children():
            self.startElement( child ) 
        return True
        
    @log_entity
    def _do_nothing(self, node, **args):
        return True


    ###########################################
    # TODO FIXME:  only useful because we do not have 100% cursorKind coverage
    def __getattr__(self, name, **args):
        if "_fixup" in name:
            raise NotImplementedError('name')
        if name not in self._unhandled:
            log.warning('%s is not handled'%(name))
            self._unhandled.append(name)
        return self._do_nothing

    ##########################################################################
    ##### CursorKind handlers#######
    ##########################################################################

    ###########################################
    # ATTRIBUTES
    
    @log_entity
    def UNEXPOSED_ATTR(self, cursor): 
        parent = cursor.semantic_parent
        #print 'parent is',parent.displayname, parent.location, parent.extent
        # TODO until attr is exposed by clang:
        # readlines()[extent] .split(' ') | grep {inline,packed}
        pass

    @log_entity
    def PACKED_ATTR(self, cursor): 
        parent = cursor.semantic_parent
        #print 'parent is',parent.displayname, parent.location, parent.extent
        # TODO until attr is exposed by clang:
        # readlines()[extent] .split(' ') | grep {inline,packed}
        pass

    ################################
    # real element handlers

    #def File(self, attrs):
    #    name = attrs["name"]
    #    if sys.platform == "win32" and " " in name:
    #        # On windows, convert to short filename if it contains blanks
    #        from ctypes import windll, create_unicode_buffer, sizeof, WinError
    #        buf = create_unicode_buffer(512)
    #        if windll.kernel32.GetShortPathNameW(name, buf, sizeof(buf)):
    #            name = buf.value
    #    return typedesc.File(name)
    #
    #def _fixup_File(self, f): pass

    ################################
    # EXPRESSIONS handlers

    '''clang does not expose some types for some expression.
    Example: the type of a token group in a Char_s or char variable.
    Counter example: The type of an integer literal to a (int) variable.'''
    @log_entity
    def UNEXPOSED_EXPR(self, cursor):
        ret = []
        for child in cursor.get_children():
            mth = getattr(self, child.kind.name)
            ret.append(mth(child))
        if len(ret) == 1:
            return ret[0]
        return ret

    @log_entity
    def DECL_REF_EXPR(self, cursor):
        return cursor.displayname

    @log_entity
    def INIT_LIST_EXPR(self, cursor):
        """Returns a list of literal values."""
        values = [self.parse_cursor(child)
                    for child in list(cursor.get_children())]
        return values

    @log_entity
    def GNU_NULL_EXPR(self, cursor):
        return None

    ################################
    # TYPE REFERENCES handlers
    
    @log_entity
    def TYPE_REF(self, cursor):
        name = self.get_unique_name(cursor)
        if self.is_registered(name):
            return self.get_registered(name)
        #log.warning('TYPE_REF with no saved decl in self.all')
        #return None
        # Should probably never get here.
        # I'm a field. ?
        _definition = cursor.get_definition() 
        if _definition is None: 
            #log.warning('no definition in this type_ref ?')
            #code.interact(local=locals())
            #raise IOError('I doubt this case is possible')
            _definition = cursor.type.get_declaration() 
        return None #self.parse_cursor(_definition)   

    def _handle_fundamental_types(self, typ):
        """
        Handles POD types nodes.
        see init_fundamental_types for the registration.
        """
        ctypesname = self.get_ctypes_name(typ.kind)
        if typ.kind == TypeKind.VOID:
            size = align = 1
        else:
            size = typ.get_size()
            align = typ.get_align()
        return typedesc.FundamentalType( ctypesname, size, align )

    FundamentalType = _handle_fundamental_types

    def _init_Fundamental_types_handlers(self):
        # TypeKind 1-23
        # VOID, CHAR, INT, LONG, FLOAT...
        for _id in range(1,24):
            _type_kind = TypeKind.from_id(_id)
            log.debug('setattr Fundamental %s'%(_type_kind.name))
            setattr(self, _type_kind.name, _handle_fundamental_types)

    ################################
    # DECLARATIONS handlers
    #
    # UNEXPOSED_DECL are unexposed by clang. Go through the node's children.
    # VAR_DECL are Variable declarations. Initialisation value(s) are collected 
    #          within _get_var_decl_init_value
    #

    UNEXPOSED_DECL = _pass_through_children
    """Undexposed declaration. Go and see children. """
    
    @log_entity
    def ENUM_CONSTANT_DECL(self, cursor):
        """Gets the enumeration values"""
        name = cursor.displayname
        value = cursor.enum_value
        pname = self.get_unique_name(cursor.semantic_parent)
        parent = self.get_registered(pname)        
        obj = typedesc.EnumValue(name, value, parent)
        parent.add_value(obj)
        return obj

    @log_entity
    def ENUM_DECL(self, cursor):
        """Gets the enumeration declaration."""
        name = self.get_unique_name(cursor)
        if self.is_registered(name):
            return self.get_registered(name)
        align = cursor.type.get_align() 
        size = cursor.type.get_size() 
        obj = self.register(name, typedesc.Enumeration(name, size, align))
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def FUNCTION_DECL(self, cursor):
        """Handles function declaration"""
        # FIXME to UT
        name = self.get_unique_name(cursor)
        if self.is_registered(name):
            return self.get_registered(name)
        returns = self.parse_cursor_type(cursor.type.get_result())
        attributes = []
        extern = False
        obj = typedesc.Function(name, returns, attributes, extern)
        for arg in cursor.get_arguments():
            obj.add_argument(self.parse_cursor(arg))
        #code.interact(local=locals())
        self.register(name,obj)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def PARM_DECL(self, cursor):
        """Handles parameter declarations."""
        _type = cursor.type
        _name = cursor.spelling
        if ( self.is_array_type(_type) or
             self.is_fundamental_type(_type) or
             self.is_pointer_type(_type)):
            _argtype = self.parse_cursor_type(_type)
        elif self.is_unexposed_type(_type):
            return None # FIXME to for children maybe ?
        else: # FIXME which UT/case ?
            _argtype_decl = _type.get_declaration()
            _argtype_name = self.get_unique_name(_argtype_decl)
            if not self.is_registered(_argtype_name):
                log.error('this param type is not declared')
                #code.interact(local=locals())
                _argtype = self.parse_cursor_type(_type)
            else:
                _argtype = self.get_registered(_argtype_name)
        obj = typedesc.Argument(_name, _argtype)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def TYPEDEF_DECL(self, cursor):
        """
        Handles typedef statements. 
        Gets Type from cache if we known it. Add it to cache otherwise.
        """
        name = self.get_unique_name(cursor)
        # if the typedef is known, get it from cache
        if self.is_registered(name):
            return self.get_registered(name)
        # use the canonical type directly.
        _type = cursor.type.get_canonical()
        log.debug("TYPEDEF_DECL: name:%s"%(name))
        log.debug("TYPEDEF_DECL: typ.kind.displayname:%s"%(_type.kind))
        #FIXME: check if this can be useful to filter internal declaration
        #_decl_cursor = _type.get_declaration()
        #if _decl_cursor.kind == CursorKind.NO_DECL_FOUND:
        #    log.warning('TYPE %s has no declaration. Builtin type?'%(name))
        #    code.interact(local=locals())        
        
        # For all types (array, fundament, pointer, others), get the type
        p_type = self.parse_cursor_type(_type)
        if not isinstance(p_type, typedesc.T):
            log.error('Bad TYPEREF parsing in TYPEDEF_DECL: %s'%(_type))
            raise TypeError('Bad TYPEREF parsing in TYPEDEF_DECL: %s'%(_type))
        # register the type
        obj = self.register(name, typedesc.Typedef(name, p_type))
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj
               
    @log_entity
    def VAR_DECL(self, cursor):
        """ The cursor is on a Variable declaration."""
        # get the name
        name = self.get_unique_name(cursor)
        # double declaration ?
        if self.is_registered(name):
            return self.get_registered(name)
        # Get the type
        _ctype = cursor.type.get_canonical()
        # FIXME: Need working int128, long_double, etc...
        if self.is_fundamental_type(_ctype):
            ctypesname = self.get_ctypes_name(_ctype.kind)
            _type = typedesc.FundamentalType( ctypesname, 0, 0 )
            # FIXME: because c_long_double_t or c_unint128 are not real ctypes
            # we can make variable with them.
            # just write the value as-is.
            ### if literal_kind != CursorKind.DECL_REF_EXPR:
            ###    init_value = '%s(%s)'%(ctypesname, init_value)
        elif self.is_unexposed_type(_ctype): # string are not exposed
            log.error('PATCH NEEDED: %s type is not exposed by clang'%(name))
            ctypesname = self.get_ctypes_name(TypeKind.UCHAR)
            _type = typedesc.FundamentalType( ctypesname, 0, 0 )
        elif self.is_array_type(_ctype) or _ctype.kind == TypeKind.RECORD:
            _type = self.parse_cursor_type(_ctype)
        elif self.is_pointer_type(_ctype):
            # extern Function pointer 
            if _ctype.get_pointee().kind == TypeKind.UNEXPOSED:
                log.debug('Ignoring unexposed pointer type.')
                return True
            elif _ctype.get_pointee().kind == TypeKind.FUNCTIONPROTO:
                # Function pointers
                # cursor.type.get_pointee().kind == TypeKind.UNEXPOSED BUT
                # cursor.type.get_canonical().get_pointee().kind == TypeKind.FUNCTIONPROTO
                mth = getattr(self, _ctype.get_pointee().kind.name)
                _type = mth(_ctype.get_pointee())
            else: # Fundamental types, structs....
                _type = self.parse_cursor_type(_ctype )
        else:
            # What else ?
            raise NotImplementedError('What other type of variable? %s'%(_ctype.kind))
        ## get the init_value and special cases
        init_value = self._get_var_decl_init_value(cursor.type, 
                                                   list(cursor.get_children()))
        if self.is_unexposed_type(_ctype): 
            # string are not exposed
            init_value = '%s # UNEXPOSED TYPE. PATCH NEEDED.'%(init_value)
        elif ( self.is_pointer_type(_ctype) and 
                _ctype.get_pointee().kind == TypeKind.FUNCTIONPROTO):
            # Function pointers argument are handled inside
            if type(init_value) != list:
                init_value = [init_value]
            _type.arguments = init_value
            init_value = _type
        # finished
        log.debug('VAR_DECL: %s _ctype:%s _type:%s _init:%s location:%s'%(name, 
                    _ctype.kind.name, _type.name, init_value,
                    getattr(cursor, 'location')))
        obj = self.register(name, typedesc.Variable(name, _type, init_value) )
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return True # dont parse literals again

    def _get_var_decl_init_value(self, _ctype, children_iter):
        """
        Gathers initialisation values by parsing children nodes of a VAR_DECL.
        """
        init_value = None
        children = list(children_iter)
        # get the value of this variable 
        if len(children) == 0:
            log.debug('0 children in a var_decl')
            if self.is_array_type(_ctype):
                return []
            return None
        # seen in function pointer with args, 
        if (len(children) != 1):
            # test_codegen.py test_extern_function_pointer_multiarg
            log.debug('Multiple children in a var_decl')
            init_value = []
            for child in children:
                # early stop cases.
                _tmp = None
                try:
                    _tmp = self._get_var_decl_init_value_single(_ctype, child)
                except CursorKindException,e:
                    log.debug('children init value skip on %s'%(child.kind))
                    continue
                if self.is_array_type(_ctype):
                    # the only working child is an INIT_LIST_EXPR
                    init_value = _tmp
                else:                    
                    init_value.append( _tmp )
        else:
            child = children[0]
            # get the init value if possible
            try:
                init_value = self._get_var_decl_init_value_single(_ctype, child)
            except CursorKindException,e:
                log.debug('single init value skip on %s'%(child.kind))
                init_value = None
        return init_value
    
    def _get_var_decl_init_value_single(self, _ctype, child):
        """
        Handling of a single child for initialization value.
        Accepted types are expressions and declarations
        """
        log.debug('_ctype: %s Child.kind: %s'%(_ctype.kind, child.kind))
        # shorcuts.
        if not child.kind.is_expression() and not child.kind.is_declaration():
            raise CursorKindException(child.kind)
        ## POD init values handling.
        # As of clang 3.3, int, double literals are exposed.
        # float, long double, char , char* are not exposed directly in level1.
        # but really it depends... 
        if self.is_array_type(_ctype):
            if child.kind == CursorKind.INIT_LIST_EXPR:
                # init value will use INIT_LIST_EXPR
                init_value = self.parse_cursor(child)
            else:
                # probably the literal that indicates the size of the array
                # UT: test_char_p, with "char x[10];"
                init_value = []
            return init_value
        elif child.kind.is_unexposed():
            # recurse until we find a literal kind
            init_value = self._get_var_decl_init_value(_ctype, child.get_children())
        else: # literal or others
            init_value = self.parse_cursor(child)
        return init_value


    @log_entity
    def _literal_handling(self, cursor):
        """Parse all literal associated with this cursor.

        Literal handling is usually useful only for initialization values.
        
        We can't use a shortcut by getting tokens
            ## init_value = ' '.join([t.spelling for t in children[0].get_tokens() 
            ##                         if t.spelling != ';'])
        because some literal might need cleaning."""
        tokens = list(cursor.get_tokens())
        log.debug('literal has %d tokens.[ %s ]'%(len(tokens), 
            str([str(t.spelling) for t in tokens])))
        final_value = []
        #code.interact(local=locals())
        log.debug('cursor.type:%s'%(cursor.type.kind.name))
        for token in tokens:
            value = token.spelling
            log.debug('token:%s tk.kd:%11s tk.cursor.kd:%15s cursor.kd:%15s'%(
                token.spelling, token.kind.name, token.cursor.kind.name, 
                cursor.kind.name))
            # Punctuation is probably not part of the init_value, 
            # but only in specific case: ';' endl, or part of list_expr
            if ( token.kind == TokenKind.PUNCTUATION and 
                 ( token.cursor.kind == CursorKind.INVALID_FILE or
                   token.cursor.kind == CursorKind.INIT_LIST_EXPR)):
                log.debug('IGNORE token %s'%(value))
                continue
            elif token.kind == TokenKind.COMMENT:
                log.debug('Ignore comment %s'%(value))
                continue
            #elif token.cursor.kind == CursorKind.VAR_DECL:
            elif token.location not in cursor.extent:
                log.debug('FIXME BUG: token.location not in cursor.extent %s'%(value))
                # FIXME
                # there is most probably a BUG in clang or python-clang
                # when on #define with no value, a token is taken from 
                # next line. Which break stuff.
                # example:
                #   #define A
                #   extern int i;
                # // this will give "extern" the last token of Macro("A")
                # Lexer is choking ?
                # FIXME BUG: token.location not in cursor.extent
                #code.interact(local=locals())
                continue
            # Cleanup specific c-lang or c++ prefix/suffix for POD types.
            if token.cursor.kind == CursorKind.INTEGER_LITERAL:
                # strip type suffix for constants 
                value = value.replace('L','').replace('U','')
                value = value.replace('l','').replace('u','')
                if value[:2] == '0x' or value[:2] == '0X' :
                    value = '0x%s'%value[2:] #"int(%s,16)"%(value)
                else:
                    value = int(value)
            elif token.cursor.kind == CursorKind.FLOATING_LITERAL:
                # strip type suffix for constants 
                value = value.replace('f','').replace('F','')
                value = float(value)
            elif (token.cursor.kind == CursorKind.CHARACTER_LITERAL or
                  token.cursor.kind == CursorKind.STRING_LITERAL):
                # strip wchar_t type prefix for string/character
                # indicatively: u8 for utf-8, u for utf-16, U for utf32
                # assume that the source file is utf-8
                # utf-32 not supported in 2.7, lets keep all in utf8
                # FIXME python 3
                # max prefix len is 3 char
                if token.cursor.kind == CursorKind.CHARACTER_LITERAL:
                    prefix = value[:3].split("'")[0]
                elif token.cursor.kind == CursorKind.STRING_LITERAL:
                    prefix = value[:3].split('"')[0]
                value = value[len(prefix)+1:-1] # strip delimitors
                # string literal only: R for raw strings
                # we need to remove the raw-char-sequence prefix,suffix
                if 'R' in prefix:
                    # if there is no '(' in the 17 first char, its not valid
                    offset = value[:17].index('(')
                    value = value[offset+1:-offset-1]
                # then we strip encoding
                for encoding in ['u8','L','u','U']:
                    if encoding in prefix: # could be Ru ou uR
                        value = unicode(value,'utf-8')
                        break # just one prefix is possible 
            # add token
            final_value.append(value)
        # return the EXPR    
        #code.interact(local=locals())
        if len(final_value) == 1:
            return final_value[0]
        return final_value

    INTEGER_LITERAL = _literal_handling
    FLOATING_LITERAL = _literal_handling
    IMAGINARY_LITERAL = _literal_handling
    STRING_LITERAL = _literal_handling
    CHARACTER_LITERAL = _literal_handling

    @log_entity
    def _operator_handling(self, cursor):
        """return a string with the literal that are part of the operation."""
        values = self._literal_handling(cursor)
        retval = ''.join([str(val) for val in values])
        return retval
    
    UNARY_OPERATOR = _operator_handling
    BINARY_OPERATOR = _operator_handling

    @log_entity
    def STRUCT_DECL(self, cursor):
        """
        Handles Structure declaration.
        Its a wrapper to _record_decl.
        """
        return self._record_decl(cursor, typedesc.Structure)

    @log_entity
    def UNION_DECL(self, cursor):
        """
        Handles Union declaration.
        Its a wrapper to _record_decl.
        """
        return self._record_decl(cursor, typedesc.Union)

    def _record_decl(self, cursor, _output_type):
        """
        Handles record type declaration.
        Structure, Union...
        """
        name = self.get_unique_name(cursor)
        # TODO unittest: try redefinition.
        # check for definition already parsed 
        if (self.is_registered(name) and
            self.get_registered(name).members is not None):
            log.debug('_record_decl: %s is already registered with members'%(name))
            return self.get_registered(name)
        # FIXME: lets ignore bases for now.
        #bases = attrs.get("bases", "").split() # that for cpp ?
        bases = [] # FIXME: support CXX
        size = cursor.type.get_size()
        align = cursor.type.get_align() 
        if align < 0 :
            log.error('invalid structure %s %s align:%d size:%d'%(
                        name, cursor.location, align, size))
            #return None
            raise InvalidDefinitionError('invalid structure %s %s align:%d size:%d'%(
                                            name, cursor.location, align, size))
        log.debug('_record_decl: name: %s size:%d'%(name, size))
        # Declaration vs Definition point
        # when a struct decl happen before the definition, we have no members
        # in the first declaration instance.
        if not self.is_registered(name) and not cursor.is_definition():
            # juste save the spot, don't look at members == None
            log.debug('XXX cursor %s is not on a definition'%(name))
            obj = _output_type(name, align, None, bases, size, packed=False)
            return self.register(name, obj)
        log.debug('XXX cursor %s is a definition'%(name))
        # save the type in the registry. Useful for not looping in case of 
        # members with forward references
        obj = None
        declared_instance = False
        if not self.is_registered(name): 
            obj = _output_type(name, align, None, bases, size, packed=False)
            self.register(name, obj)
            self.set_location(obj, cursor)
            self.set_comment(obj, cursor)
            declared_instance = True
        # capture members declaration
        members = []
        # Go and recurse through children to get this record member's _id
        # Members fields will not be "parsed" here, but later.
        for childnum, child in enumerate(cursor.get_children()):
            if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                # CIndexUSR.cpp:800+ // Bit fields can be anonymous.
                _cid = self.get_unique_name(child)
                ## FIXME 2: no get_usr() for members of builtin struct
                if _cid == '' and child.is_bitfield():
                    _cid = cursor.get_usr() + "@Ab#" + str(childnum)
                # END FIXME
                members.append( self.FIELD_DECL(child) )
                continue
            # LLVM-CLANG, patched 
            if child.kind == clang.cindex.CursorKind.PACKED_ATTR:
                obj.packed = True
        if self.is_registered(name): 
            # STRUCT_DECL as a child of TYPEDEF_DECL for example
            # FIXME: make a test case for that.
            if not declared_instance:
                log.debug('_record_decl: %s was previously registered'%(name))
            obj = self.get_registered(name)
            obj.members = members
        return obj

    def _fixup_record(self, s):
        """Fixup padding on a record"""
        log.debug('Struct/Union_FIX: %s '%(s.name))
        if s.members is None:
            log.debug('Struct/Union_FIX: no members')
            s.members = []
            return
        ## No need to lookup members in a global var.
        ## Just fix the padding        
        members = []
        offset = 0
        padding_nb = 0
        member = None
        # create padding fields
        #DEBUG FIXME: why are s.members already typedesc objet ?
        #fields = self.fields[s.name]
        for m in s.members: # s.members are strings - NOT
            '''import code
            if m not in self.fields.keys():
                log.warning('Fixup_struct: Member unexpected : %s'%(m))
                raise TypeError('Fixup_struct: Member unexpected : %s'%(m))
            elif fields[m] is None:
                log.warning('record %s: ignoring field %s'%(s.name,m))
                continue
            elif type(fields[m]) != typedesc.Field:
                # should not happend ?
                log.warning('Fixup_struct: Member not a typedesc : %s'%(m))
                raise TypeError('Fixup_struct: Member not a typedesc : %s'%(m))
            member = fields[m]
            '''
            member = m
            log.debug('Fixup_struct: Member:%s offsetbits:%d->%d expecting offset:%d'%(
                    member.name, member.offset, member.offset + member.bits, offset))
            if member.offset > offset:
                #create padding
                length = member.offset - offset
                log.debug('Fixup_struct: create padding for %d bits %d bytes'%(length, length/8))
                p_name = 'PADDING_%d'%padding_nb
                padding = self._make_padding(p_name, offset, length)
                members.append(padding)
                padding_nb+=1
            if member.type is None:
                log.error('FIXUP_STRUCT: %s.type is None'%(member.name))
            members.append(member)
            offset = member.offset + member.bits
        # tail padding if necessary and last field is NOT a bitfield
        # FIXME: this isn't right. Why does Union.size returns 1.
        # Probably because of sizeof returning standard size instead of real size
        if member and member.is_bitfield:
            pass
        elif s.size*8 != offset:                
            length = s.size*8 - offset
            log.debug('Fixup_struct: s:%d create tail padding for %d bits %d bytes'%(s.size, length, length/8))
            p_name = 'PADDING_%d'%padding_nb
            padding = self._make_padding(p_name, offset, length)
            members.append(padding)
        if len(members) > 0:
            offset = members[-1].offset + members[-1].bits
        # go
        s.members = members
        log.debug("FIXUP_STRUCT: size:%d offset:%d"%(s.size*8, offset))
        # FIXME:
        if member and not member.is_bitfield:
            assert offset == s.size*8 #, assert that the last field stop at the size limit
        return

    _fixup_Structure = _fixup_record
    _fixup_Union = _fixup_record

    def _make_padding(self, name, offset, length):
        """Make padding Fields for a specifed size."""
        log.debug("_make_padding: for %d bits"%(length))
        if (length % 8) != 0:
            # FIXME
            log.warning('_make_padding: FIXME we need sub-bytes padding definition')
        if length > 8:
            bytes = length/8
            return typedesc.Field(name,
                     typedesc.ArrayType(
                       typedesc.FundamentalType(
                         self.ctypes_typename[TypeKind.CHAR_U], length, 1 ),
                       bytes),
                     offset, length)
        return typedesc.Field(name,
                 typedesc.FundamentalType( self.ctypes_typename[TypeKind.CHAR_U], 1, 1 ),
                 offset, length)


    Class = STRUCT_DECL
    _fixup_Class = _fixup_Structure

    @log_entity
    def FIELD_DECL(self, cursor):
        """Handles Field declarations.
        a fundamentalType field needs to get a _type
        a Pointer need to get treated by self.POINTER ( no children )
        a Record needs to be treated by self.record... etc..
        """
        # name, type
        name = self.get_unique_name(cursor)
        record_name = self.get_unique_name(cursor.semantic_parent)
        #_id = cursor.get_usr()
        offset = cursor.semantic_parent.type.get_offset(name)
        if offset < 0:
            log.error('BAD RECORD, Bad offset: %d for %s'%(offset, name))
            # FIXME if c++ class ?
        # bitfield
        bits = None
        if cursor.is_bitfield():
            bits = cursor.get_bitfield_width()
            if name == '': # TODO FIXME libclang, get_usr() should return != ''
                log.warning("Cursor has no displayname - anonymous bitfield")
                childnum = None
                for i, x in enumerate(cursor.semantic_parent.get_children()):
                  if x == cursor:
                    childnum = i
                    break
                else:
                  raise Exception('Did not find child in semantic parent')
                _id = cursor.semantic_parent.get_usr() + "@Ab#" + str(childnum)
                name = "anonymous_bitfield"
        else:
            bits = cursor.type.get_size() * 8
            if bits < 0:
                log.warning('Bad source code, bitsize == %d <0 on %s'%(bits, name))
                bits = 0
        # after dealing with anon bitfields
        if name == '': 
            raise ValueError("Field has no displayname")
        # try to get a representation of the type
        ##_canonical_type = cursor.type.get_canonical()
        # t-t-t-t-
        _type = None
        _canonical_type = cursor.type.get_canonical()
        _decl = cursor.type.get_declaration()
        if self.is_fundamental_type(_canonical_type):
            _type = self.parse_cursor_type(_canonical_type)
        elif self.is_pointer_type(_canonical_type):
            _type = self.parse_cursor_type(_canonical_type)
        elif self.is_array_type(_canonical_type):
            #code.interact(local=locals())
            _type = self.parse_cursor_type(_canonical_type)
        else:
            children = list(cursor.get_children())
            if len(children) > 0 and _decl.kind == CursorKind.NO_DECL_FOUND:
                # constantarray of typedef of pointer , and other cases ?
                _decl_name = self.get_unique_name(list(cursor.get_children())[0])
            else:
                _decl_name = self.get_unique_name(cursor.type.get_declaration()) # .spelling ??
            if self.is_registered(_decl_name):
                log.debug('FIELD_DECL: used type from cache: %s'%(_decl_name))
                _type = self.get_registered(_decl_name)
                # then we shortcut
                #code.interact(local=locals())
                
            else:
                # is it always the case ?
                log.debug("FIELD_DECL: name:'%s'"%(name))
                log.debug("FIELD_DECL: %s: nb children:%s"%(cursor.type.kind, 
                                len(children)))
                #code.interact(local=locals())
                # recurse into the right function
                _type = self.parse_cursor_type(_canonical_type)
                if _type is None:
                    log.warning("Field %s is an %s type - ignoring field type"%(
                                name,_canonical_type.kind.name))
                    return None
        return typedesc.Field(name, _type, offset, bits, is_bitfield=cursor.is_bitfield())

    def _fixup_Field(self, f):
        #print 'fixup field', f.type
        #if f.type is not None:
        #    mth = getattr(self, '_fixup_%s'%(type(f.type).__name__))
        #    mth(f.type)
        pass











    ##########################################################################
    ##### TypeKind handlers#######
    ##########################################################################

    # TODO 
    """ 
    INVALID
    UNEXPOSED
    NULLPTR
    OVERLOAD
    DEPENDENT
    OBJCID
    OBJCCLASS
    OBJCSEL
    COMPLEX
    BLOCKPOINTER
    LVALUEREFERENCE
    RVALUEREFERENCE
    OBJCINTERFACE
    OBJCOBJECTPOINTER
    FUNCTIONNOPROTO
    FUNCTIONPROTO
    VECTOR
    MEMBERPOINTER
    """

    ## const, restrict and volatile
    ## typedesc.CvQualifiedType(typ, const, volatile)
    # Type has multiple functions for const, volatile, restrict
    # not listed has node in the AST.
    # not very useful in python anyway.
    
    TYPEDEF = _do_nothing
    ENUM = _do_nothing

    @log_entity
    def POINTER(self, _cursor_type):
        """
        Handles POINTER types.
        """
        if not isinstance(_cursor_type, clang.cindex.Type):
            raise TypeError('Please call POINTER with a cursor.type')
        # we shortcut to canonical typedefs and to pointee canonical defs
        _type = _cursor_type.get_pointee().get_canonical()
        _p_type_name = self.get_unique_name(_type)
        # get pointer size
        size = _cursor_type.get_size() # not size of pointee
        align = _cursor_type.get_align() 
        log.debug("POINTER: size:%d align:%d typ:%s"%(size, align, _type.kind))
        if self.is_fundamental_type(_type):
            p_type = self.parse_cursor_type(_type)
        elif self.is_pointer_type(_type) or self.is_array_type(_type):
            p_type = self.parse_cursor_type(_type)
        elif _type.kind == TypeKind.FUNCTIONPROTO:
            p_type = self.parse_cursor_type(_type)
        else: #elif _type.kind == TypeKind.RECORD:
            # check registration
            decl = _type.get_declaration()
            decl_name = self.get_unique_name(decl)
            # Type is already defined OR will be defined later.
            if self.is_registered(decl_name):
                p_type = self.get_registered(decl_name)
            else: # forward declaration, without looping
                log.debug('POINTER: %s type was not previously declared'%(decl_name))
                #code.interact(local=locals())
                p_type = self.parse_cursor(decl)
        #elif _type.kind == TypeKind.FUNCTIONPROTO:
        #    log.error('TypeKind.FUNCTIONPROTO not implemented')
        #    return None
        log.debug("POINTER: pointee type_name:'%s'"%(_p_type_name))
        # return the pointer
        obj = typedesc.PointerType( p_type, size, align)
        obj.location = p_type.location
        return obj

    @log_entity
    def _array_handler(self, _cursor_type):
        """
        Handles all array types. 
        Resolves it's element type and makes a Array typedesc.
        """
        if not isinstance(_cursor_type, clang.cindex.Type):
            raise TypeError('Please call CONSTANTARRAY with a cursor.type')
        # The element type has been previously declared
        # we need to get the canonical typedef, in some cases
        _type = _cursor_type.get_canonical()
        size = _type.get_array_size()
        # FIXME: useful or not ?
        if size == -1 and _type.kind == TypeKind.INCOMPLETEARRAY:
            size = 0
            # Fixes error in negative sized array.
            # FIXME VARIABLEARRAY DEPENDENTSIZEDARRAY
        _array_type = _type.get_array_element_type()#.get_canonical()
        if self.is_fundamental_type(_array_type):
            _subtype = self.parse_cursor_type(_array_type)
        elif self.is_pointer_type(_array_type): 
            #code.interact(local=locals())
            # pointers to POD have no declaration ??
            # FIXME test_struct_with_pointer x_n_t g[1]
            _subtype = self.parse_cursor_type(_array_type)
        else:
            _subtype_decl = _array_type.get_declaration()
            _subtype = self.parse_cursor(_subtype_decl)
            #if _subtype_decl.kind == CursorKind.NO_DECL_FOUND:
            #    pass
            #_subtype_name = self.get_unique_name(_subtype_decl)
            #_subtype = self.get_registered(_subtype_name)
        #code.interact(local=locals())
        obj = typedesc.ArrayType(_subtype, size)
        obj.location = _subtype.location
        return obj

    CONSTANTARRAY = _array_handler
    INCOMPLETEARRAY = _array_handler
    VARIABLEARRAY = _array_handler
    DEPENDENTSIZEDARRAY = _array_handler

    @log_entity
    def FUNCTIONPROTO(self, _cursor_type):
        """Handles function prototype."""
        if not isinstance(_cursor_type, clang.cindex.Type):
            raise TypError('Please call FUNCTIONPROTO with a _cursor_type')
        # id, returns, attributes
        returns = _cursor_type.get_result()
        if self.is_fundamental_type(returns):
            returns = self.parse_cursor_type(returns)
        attributes = []
        obj = typedesc.FunctionType(returns, attributes)
        for i, _attr_type in enumerate(_cursor_type.argument_types()):
            arg = typedesc.Argument("a%d"%(i), self.parse_cursor(_attr_type))
            obj.add_argument( arg )
        #log.debug('FUNCTIONPROTO: can I get args ?')
        #code.interact(local=locals())    
        self.set_location(obj, None)
        return obj

    # structures, unions, classes
    
    @log_entity
    def RECORD(self, _cursor_type):
        ''' A record is a NOT a declaration. A record is the occurrence of of
        previously defined record type. So no action is needed. Type is already 
        known.
        Type is accessible by cursor.type.get_declaration() 
        '''
        if not isinstance(_cursor_type, clang.cindex.Type):
            raise TypeError('Please call RECORD with a cursor.type')
        _decl = _cursor_type.get_declaration() # is a record
        #code.interact(local=locals())
        #_decl_cursor = list(_decl.get_children())[0] # record -> decl
        name = self.get_unique_name(_decl)#_cursor)
        if self.is_registered(name):
            obj = self.get_registered(name)
        else:
            log.warning('Was in RECORD but had to parse record declaration ')
            obj = self.parse_cursor(_decl)
        return obj


    ################
    
    # Do not traverse into function bodies and other compound statements
    # now fixed by TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    @log_entity
    def COMPOUND_STMT(self, cursor):
        return True

    @log_entity
    def MACRO_DEFINITION(self, cursor):
        """Parse MACRO_DEFINITION, only present if the TranslationUnit is 
        used with TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD"""
        # TODO: optionalize macro parsing. It takes a LOT of time.
        name = self.get_unique_name(cursor)
        #if name == 'A':
        #    code.interact(local=locals())
        # Tokens !!! .kind = {IDENTIFIER, KEYWORD, LITERAL, PUNCTUATION, 
        # COMMENT ? } etc. see TokenKinds.def
        comment = None
        tokens = self._literal_handling(cursor)
        # Macro name is tokens[0]
        # get Macro value(s)
        value = True
        if isinstance(tokens, list):
            if len(tokens) == 2 :
                value = tokens[1]
            else:
                value = tokens[1:]
        # macro comment maybe in tokens. Not in cursor.raw_comment
        for t in cursor.get_tokens():
            if t.kind == TokenKind.COMMENT:
                comment = t.spelling
        # special case. internal __null
        # FIXME, there are probable a lot of others.
        # why not Cursor.kind GNU_NULL_EXPR child instead of a token ?
        if name == 'NULL' or value == '__null':
            value = None
        log.debug('MACRO: #define %s %s'%(tokens[0], value))
        obj = typedesc.Macro(name, None, value)
        try:
            self.register(name, obj)
        except DuplicateDefinitionException, e:
            log.info('Redefinition of %s %s->%s'%(name, self.all[name].args, value))
            # HACK 
            self.all[name] = obj
            pass
        self.set_location(obj, cursor)
        # set the comment in the obj 
        obj.comment = comment
        return True
    
    
    
    ################

    def get_macros(self, text):
        if text is None:
            return
        text = "".join(text)
        # preprocessor definitions that look like macros with one or more arguments
        for m in text.splitlines():
            name, body = m.split(None, 1)
            name, args = name.split("(", 1)
            args = "(%s" % args
            self.all[name] = typedesc.Macro(name, args, body)

    def get_aliases(self, text, namespace):
        if text is None:
            return
        # preprocessor definitions that look like aliases:
        #  #define A B
        text = "".join(text)
        aliases = {}
        for a in text.splitlines():
            name, value = a.split(None, 1)
            a = typedesc.Alias(name, value)
            aliases[name] = a
            self.all[name] = a

        for name, a in aliases.items():
            value = a.alias
            # the value should be either in namespace...
            if value in namespace:
                # set the type
                a.typ = namespace[value]
            # or in aliases...
            elif value in aliases:
                a.typ = aliases[value]
            # or unknown.
            else:
                # not known
##                print "skip %s = %s" % (name, value)
                pass

    def get_result(self):
        # all of these should register()
        interesting = (typedesc.Typedef, typedesc.Enumeration, typedesc.EnumValue,
                       typedesc.Function, typedesc.Structure, typedesc.Union,
                       typedesc.Variable, typedesc.Macro, typedesc.Alias,
                       typedesc.FunctionType )
                       #typedesc.Field) #???

        self.get_macros(self.cpp_data.get("functions"))
        # fix all objects after that all are resolved
        remove = []
        for _id, _item in self.all.items():
            if _item is None:
                log.warning('ignoring %s'%(_id))
                continue            
            location = getattr(_item, "location", None)
            # FIXME , why do we get different location types
            if location and hasattr(location, 'file'):
                _item.location = location.file.name, location.line
                log.error('%s %s came in with a SourceLocation'%(_id, _item))
            elif location is None:
                # FIXME make this optional to be able to see internals
                # FIXME macro/alias are here 
                remove.append(_item.name)
            # try fixup if needed
            fixup_cb_name = "_fixup_" + type(_item).__name__
            if hasattr(self, fixup_cb_name):
                mth = getattr(self, fixup_cb_name)
                mth(_item)

        for _x in remove:
            del self.all[_x]

        # Now we can build the namespace.
        namespace = {}
        for i in self.all.values():
            if not isinstance(i, interesting):
                log.debug('ignoring %s'%( i) )
                continue  # we don't want these
            name = getattr(i, "name", None)
            if name is not None:
                namespace[name] = i
        self.get_aliases(self.cpp_data.get("aliases"), namespace)

        result = []
        for i in self.all.values():
            if isinstance(i, interesting):
                result.append(i)

        #print 'self.all', self.all
        #code.interact(local=locals())

        
        #print 'clangparser get_result:',result
        return result
    
    


