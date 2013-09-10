"""clangparser - use clang to get preprocess a source code."""

import clang
from clang.cindex import Index
from clang.cindex import CursorKind, TypeKind
import ctypes

import logging

import codegenerator
import typedesc
import sys
import re

from . import util

log = logging.getLogger('clangparser')

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
        name = args[1].displayname
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
    for k, v in [('<','_'), ('>','_'), ('::','__'), (',',''), (' ',''),
                 ("$", "DOLLAR"), (".", "DOT"), ("@", "_"), (":", "_")]:
        if k in name: # template
            name = name.replace(k,v)
    #FIXME: test case ? I want this func to be neutral on C valid names.
    if name.startswith("__"):
        return "_X" + name
    if name[0] in "01234567879":
        return "_" + name
    return name

WORDPAT = re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

def CHECK_NAME(name):
    if WORDPAT.match(name):
        return name
    return None

''' 
clang2py test1.cpp -target "x86_64-pc-linux-gnu" 
clang2py test1.cpp -target i386-pc-linux-gnu

'''
class Clang_Parser(object):
    '''clang2py test1.cpp -target "x86_64-pc-linux-gnu" 

   clang2py test1.cpp -target i386-pc-linux-gnu

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

    ctypes_typename = {
        TypeKind.VOID : 'void' ,
        TypeKind.BOOL : 'c_bool' ,
        TypeKind.CHAR_U : 'c_ubyte' ,
        TypeKind.UCHAR : 'c_ubyte' ,
        TypeKind.CHAR16 : 'c_wchar' ,
        TypeKind.CHAR32 : 'c_wchar*2' ,
        TypeKind.USHORT : 'TBD' ,
        TypeKind.UINT : 'TBD' ,
        TypeKind.ULONG : 'TBD' ,
        TypeKind.ULONGLONG : 'TBD' ,
        TypeKind.UINT128 : 'c_uint128' , # FIXME
        TypeKind.CHAR_S : 'c_char' , 
        TypeKind.SCHAR : 'c_char' , 
        TypeKind.WCHAR : 'c_wchar' ,
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
        self.tu = None
        self.flags = flags
        self.ctypes_sizes = {}
        self.make_ctypes_convertor(flags)
        

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
        self.tu = index.parse(filename, self.flags)
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
        stop_recurse = mth(node)
        # Signature of mth is:
        # if the fn returns True, do not recurse into children.
        # anything else will be ignored.
        if stop_recurse is True:
            return        
        # if fn returns something, if this element has children, treat them.
        for child in node.get_children():
            self.startElement( child )
        # startElement returns None.
        return None

    def register(self, name, obj):
        if name in self.all:
            log.debug('register: %s already existed: %s'%(name,obj.name))
            import code
            code.interact(local=locals())
            raise RuntimeError('register: %s already existed: %s'%(name,obj.name))
        log.debug('register: %s '%(name))
        self.all[name]=obj
        return obj

    def get_registered(self, name):
        if name not in self.all:
            return None
        return self.all[name]

    def is_registered(self, name):
        return name in self.all

    ''' Location is also used for codegeneration ordering.'''
    def set_location(self, obj, cursor):
        if hasattr(cursor, 'location') and cursor.location.file is not None:
            obj.location = (cursor.location.file.name, cursor.location.line)

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

    def is_unexposed_type(self, t):
        return t.kind == TypeKind.UNEXPOSED

    # deprecated
    def convert_to_ctypes(self, typekind):
        return self.ctypes_typename[typekind]

    def get_ctypes_name(self, typekind):
        return self.ctypes_typename[typekind]

    def get_ctypes_size(self, typekind):
        return self.ctypes_sizes[typekind]
        

    ################################
    # do-nothing element handlers

    #def Class(self, attrs): pass
    def Destructor(self, attrs): pass
    
    cvs_revision = None
    def GCC_XML(self, attrs):
        rev = attrs["cvs_revision"]
        self.cvs_revision = tuple(map(int, rev.split(".")))

    def Namespace(self, attrs): pass

    def Base(self, attrs): pass
    def Ellipsis(self, attrs): pass
    def OperatorMethod(self, attrs): pass


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

    #def CPP_DUMP(self, attrs):
    #    name = attrs["name"]
    #    # Insert a new list for each named section into self.cpp_data,
    #    # and point self.cdata to it.  self.cdata will be set to None
    #    # again at the end of each section.
    #    self.cpp_data[name] = self.cdata = []

    #def characters(self, content):
    #    if self.cdata is not None:
    #        self.cdata.append(content)

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

    # References

    @log_entity
    def DECL_REF_EXPR(self, cursor):
        return cursor.displayname
    
    @log_entity
    def TYPE_REF(self, cursor):
        return None
        # Should probably never get here.
        # I'm a field. ?
        _definition = cursor.get_definition() 
        if _definition is None: 
            _definition = cursor.type.get_declaration() 
            
        #_id = _definition.get_usr()
        name = _definition.displayname
        if name == '': 
            name = MAKE_NAME( _definition.get_usr() )
        obj = self.get_registered(name)
        if obj is None:
            log.warning('This TYPE_REF was not previously defined. %s. Adding it'%(name))
            # FIXME maybe do not fail and ignore record.
            #import code
            #code.interact(local=locals())
            #raise TypeError('This TYPE_REF was not previously defined. %s. Adding it'%(name))
            return self.TYPEDEF_DECL(_definition)
        return obj

    # Declarations     
    
    ''' The cursor is on a Variable declaration.'''
    @log_entity
    def VAR_DECL(self, cursor):
        # get the name
        name = cursor.displayname
        # the value is a literal in get_children()
        children = list(cursor.get_children())
        assert( len(children) == 1 )
        # token shortcut is not possible.
        literal_kind = children[0].kind
        if literal_kind.is_unexposed():
            literal_kind = list(children[0].get_children())[0].kind
        mth = getattr(self, literal_kind.name)
        # pod ariable are easy. some are unexposed.
        log.debug('Calling %s'%(literal_kind.name))
        # As of clang 3.3, int, double literals are exposed.
        # float, long double, char , char* are not exposed directly in level1.
        init_value = mth(children[0])
        # Get the type
        _ctype = cursor.type.get_canonical()
        #import code
        #code.interact(local=locals())
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
            init_value = '%s # UNEXPOSED TYPE. PATCH NEEDED.'%(init_value)
        elif _ctype.kind == TypeKind.RECORD:
          structname = self.get_unique_name(_ctype.get_declaration())
          _type = self.all[structname]
        else:
            ## What else ?
            raise NotImplementedError('What other type of variable?')
            # _type = cursor.get_usr()
            #import code
            #code.interact(local=locals())
            #_type = cursor.type.get_declaration().kind.name
            #if _type == '': 
            #    _type = MAKE_NAME( cursor.get_usr() )
        log.debug('VAR_DECL: %s _ctype:%s _type:%s _init:%s'%(name, 
                    _ctype.kind.name, _type.name, init_value))
        #print _type.__class__.__name__
        obj = self.register(name, typedesc.Variable(name, _type, init_value) )
        self.set_location(obj, cursor)
        return True # dont parse literals again

    def _fixup_Variable(self, t):
        if type(t.typ) == str: #typedesc.FundamentalType:
            t.typ = self.all[t.typ]

    '''
        Typedef_decl has 1 child, a typeref.
        the Typeref is himself.
        
        typedef_decl.get_definition().type.get_canonical().kind
        results the type.
    
    '''
    #def Typedef(self, attrs):
    @log_entity
    def TYPEDEF_DECL(self, cursor):
        ''' At some point the target type is declared.
        '''
        name = cursor.displayname
        log.debug("TYPEDEF_DECL: name:%s"%(name))
        _type = cursor.type.get_canonical()
        _id = cursor.get_usr()
        log.debug("TYPEDEF_DECL: typ.kind.displayname:%s"%(_type.kind.spelling))
        # FIXME feels weird not to call self.fundamental
        if self.is_fundamental_type(_type):
            p_type = self.FundamentalType(_type)
            #ctypesname = self.convert_to_ctypes(typ.kind)
            #typ = typedesc.FundamentalType( ctypesname, 0, 0 )
            #log.debug("TYPEDEF_DECL: fundamental typ:%s"%(typ))
        elif self.is_pointer_type(_type):
            p_type = self.POINTER(cursor)
            #import code
            #code.interact(local=locals())
        elif _type.kind == TypeKind.RECORD:
            # Typedef and struct_decl will have the same name. 
            decl = _type.get_declaration() 
            decl_name = decl.displayname
            if decl_name == '':
                decl_name = MAKE_NAME(decl.get_usr())
            # Type is already defined OR will be defined later.
            p_type = self.get_registered(decl_name) or decl_name
            #import code
            #code.interact(local=locals())
            '''
            _id = cursor.get_definition().get_usr()
            obj = self.get_registered(name)
            #import code
            #code.interact(local=locals())
            return obj or self.register(name, typedesc.Typedef(name, name))
            if obj is None:
                # kinda expected, isn't it ?
                log.info('TYPEDEF_DECL record was not previously defined. Not a surprise.')
                typ = name
                return self.register(name, typedesc.Typedef(name, typ))
            else:
                return obj
            '''
        else:
            # _type.kind == TypeKind.CONSTANTARRAY or
            #  _type.kind == TypeKind.FUNCTIONPROTO
            pass
            return None
        if p_type is None:
            import code
            code.interact(local=locals())
        # final
        obj = self.register(name, typedesc.Typedef(name, p_type))
        self.set_location(obj, cursor)
        return obj
        
    def _fixup_Typedef(self, t):
        #print 'fixing typdef %s name:%s with self.all[%s] = %s'%(id(t), t.name, t.typ, id(self.all[ t.typ])) 
        #print self.all.keys()
        if type(t.typ) == str: #typedesc.FundamentalType:
            log.debug("_fixup_Typedef: t:'%s' t.typ:'%s' t.name:'%s'"%(t, t.typ, t.name))
            t.typ = self.all[t.name]
        pass

       
    def FundamentalType(self, typ):
        #print cursor.displayname
        #t = cursor.type.get_canonical().kind
        ctypesname = self.convert_to_ctypes(typ.kind)
        if typ.kind == TypeKind.VOID:
            size = align = 1
        else:
            size = typ.get_size()
            align = typ.get_align()
        return typedesc.FundamentalType( ctypesname, size, align )

    def _fixup_FundamentalType(self, t): pass

    @log_entity
    def POINTER(self, cursor):
        # we shortcut to canonical typedefs and to pointee canonical defs
        _type = cursor.type.get_canonical().get_pointee().get_canonical()
        # get pointer size
        size = cursor.type.get_size() # not size of pointee
        align = cursor.type.get_align() 
        log.debug("POINTER: size:%d align:%d typ:%s"%(size, align, _type))
        if self.is_fundamental_type(_type):
            p_type = self.FundamentalType(_type)
        elif _type.kind == TypeKind.RECORD:
            #children = [c for c in cursor.get_children()]
            #assert len(children) == 1 # 'There is %d children - not expected in PointerType'%(len(children)))
            #assert children[0].kind == CursorKind.TYPE_REF#, 'Wasnt expecting a %s in PointerType'%(children[0].kind))
            # check registration
            decl = _type.get_declaration()
            decl_name = decl.displayname
            if decl_name == '':
                decl_name = MAKE_NAME(decl.get_usr())
            # Type is already defined OR will be defined later.
            p_type = self.get_registered(decl_name) or decl_name
            #p_type = children[0].get_definition().get_usr()
            #if p_type in self.all:
            #    p_type = self.all[p_type]
            #else: # forward declaration 
            #    child = children[0].type.get_declaration()
            #    mth = getattr(self, child.kind.name)
            #    if mth is None:
            #        log.debug('POINTER: mth is None')
            #        raise TypeError('unhandled POINTER TypeKind %s'%(child.kind))
            #    log.debug('POINTER: mth is %s'%(mth.__name__))
            #    res = mth(child)
            #    p_type = res
        #elif _type.kind == TypeKind.FUNCTIONPROTO:
        #    log.error('TypeKind.FUNCTIONPROTO not implemented')
        #    return None
        else:
            # 
            mth = getattr(self, _type.kind.name)
            p_type = mth(_type)
            #import code
            #code.interact(local=locals())
            #raise TypeError('Unknown scenario in PointerType - %s'%(_type))
        log.debug("POINTER: p_type:'%s'"%(p_type.__dict__))
        # return the pointer        
        obj = typedesc.PointerType( p_type, size, align)
        self.set_location(obj, cursor)
        return obj


    def _fixup_PointerType(self, p):
        #print '*** Fixing up PointerType', p.typ
        #import code
        #code.interact(local=locals())
        ##if type(p.typ.typ) != typedesc.FundamentalType:
        ##    p.typ.typ = self.all[p.typ.typ]
        if type(p.typ) == str:
            p.typ = self.all[p.typ]

    ReferenceType = POINTER
    _fixup_ReferenceType = _fixup_PointerType
    OffsetType = POINTER
    _fixup_OffsetType = _fixup_PointerType

    @log_entity
    def CONSTANTARRAY(self, cursor):
        # 
        #return typedesc.ArrayType('INT', 2)
        size = cursor.type.get_array_size()
        _type = cursor.type.get_array_element_type().get_canonical()
        if self.is_fundamental_type(_type):
            _type = self.FundamentalType(_type)
        else:
            mth = getattr(self, _type.kind.name)
            if mth is None:
                raise TypeError('unhandled Field TypeKind %s'%(_type.kind.name))
            _type  = mth(cursor)
            if _type is None:
                return None

        #import code
        #code.interact(local=locals())
        
        obj = typedesc.ArrayType(_type, size)
        self.set_location(obj, cursor)
        return obj

    def _fixup_ArrayType(self, a):
        # FIXME
        #if type(a.typ) != typedesc.FundamentalType:
        #    a.typ = self.all[a.typ]
        pass

    def CvQualifiedType(self, attrs):
        # id, type, [const|volatile]
        typ = attrs["type"]
        const = attrs.get("const", None)
        volatile = attrs.get("volatile", None)
        obj = typedesc.CvQualifiedType(typ, const, volatile)
        self.set_location(obj, cursor)
        return obj

    def _fixup_CvQualifiedType(self, c):
        c.typ = self.all[c.typ]

    # callables
    
    #def Function(self, attrs):
    @log_entity
    def FUNCTION_DECL(self, cursor):
        # name, returns, extern, attributes
        #name = attrs["name"]
        #returns = attrs["returns"]
        #attributes = attrs.get("attributes", "").split()
        #extern = attrs.get("extern")
        name = cursor.displayname
        returns = None
        attributes = None
        extern = None
        # FIXME:
        # cursor.get_arguments() or see def PARM_DECL()
        obj = typedesc.Function(name, returns, attributes, extern)
        self.set_location(obj, cursor)
        return obj

    def _fixup_Function(self, func):
        #FIXME
        #func.returns = self.all[func.returns]
        #func.fixup_argtypes(self.all)
        pass

    def FUNCTIONPROTO(self, cursor):
        # id, returns, attributes
        returns = cursor.get_result()
        if self.is_fundamental_type(returns):
            returns = self.FundamentalType(returns)
        attributes = []
        for attr in iter(cursor.argument_types()):
            if self.is_fundamental_type(attr):
                attributes.append(self.FundamentalType(attr))
            else:
                #mth = getattr(self, attr.kind.name)
                #if mth is None:
                #    raise TypeError('unhandled Field TypeKind %s'%(_type.kind.name))
                #_type  = mth(cursor)
                #if _type is None:
                #    return None
                attributes.append(attr)
        #import code
        #code.interact(local=locals())    
        obj = typedesc.FunctionType(returns, attributes)
        self.set_location(obj, cursor)
        return obj
    
    def _fixup_FunctionType(self, func):
        func.returns = self.all[func.returns]
        func.fixup_argtypes(self.all)

    @log_entity
    def OperatorFunction(self, attrs):
        # name, returns, extern, attributes
        name = attrs["name"]
        returns = attrs["returns"]
        obj = typedesc.OperatorFunction(name, returns)
        self.set_location(obj, cursor)
        return obj

    def _fixup_OperatorFunction(self, func):
        func.returns = self.all[func.returns]

    def _Ignored(self, attrs):
        log.debug("_Ignored: name:'%s' "%(cursor.spelling))
        name = attrs.get("name", None)
        if not name:
            name = attrs["mangled"]
        return typedesc.Ignored(name)

    def _fixup_Ignored(self, const): pass

    Converter = Constructor = Destructor = OperatorMethod = _Ignored

    def Method(self, attrs):
        # name, virtual, pure_virtual, returns
        name = attrs["name"]
        returns = attrs["returns"]
        return typedesc.Method(name, returns)

    def _fixup_Method(self, m):
        m.returns = self.all[m.returns]
        m.fixup_argtypes(self.all)

    # working, except for parent not being a Typedesc.
    def PARM_DECL(self, cursor):
        parent = cursor.semantic_parent
        #    if parent is not None:
        #        parent.add_argument(typedesc.Argument(p.type.get_canonical(), p.name))
        return

    # DEPRECATED
    # Function is not used any more, as variable assignate are goten directly
    # from the token.
    # We can't use a shortcut by getting tokens
    ## init_value = ' '.join([t.spelling for t in children[0].get_tokens() 
    ##                         if t.spelling != ';'])
    # because some literal might need cleaning.
    @log_entity
    def _literal_handling(self, cursor):
        tokens = list(cursor.get_tokens())
        log.debug('literal has %d tokens.[ %s ]'%(len(tokens), 
            str([str(t.spelling) for t in tokens])))
        final_value = []
        #import code
        #code.interact(local=locals())
        for token in tokens:
            value = token.spelling
            if value == ';':
                continue
            if cursor.kind == CursorKind.INTEGER_LITERAL:
                # strip type suffix for constants 
                value = value.replace('L','').replace('U','')
                value = value.replace('l','').replace('u','')
            elif cursor.kind == CursorKind.FLOATING_LITERAL:
                # strip type suffix for constants 
                value = value.replace('f','').replace('F','')
            # add token
            final_value.append(value)
        # return the EXPR    
        return ' '.join(final_value)

    INTEGER_LITERAL = _literal_handling
    FLOATING_LITERAL = _literal_handling
    IMAGINARY_LITERAL = _literal_handling
    STRING_LITERAL = _literal_handling
    CHARACTER_LITERAL = _literal_handling

    UNARY_OPERATOR = _literal_handling
    BINARY_OPERATOR = _literal_handling

    # enumerations

    @log_entity
    def ENUM_DECL(self, cursor):
        ''' Get the enumeration type'''
        # id, name
        #print '** ENUMERATION', cursor.displayname
        name = cursor.displayname
        if name == '':
            name = MAKE_NAME( cursor.get_usr() )
        #    #raise ValueError('could try get_usr()')
        align = cursor.type.get_align() 
        size = cursor.type.get_size() 
        #print align, size
        obj = self.register(name, typedesc.Enumeration(name, size, align))
        self.set_location(obj, cursor)
        return obj

    def _fixup_Enumeration(self, e): pass

    @log_entity
    def ENUM_CONSTANT_DECL(self, cursor):
        ''' Get the enumeration values'''
        name = cursor.displayname
        value = cursor.enum_value
        pname = cursor.semantic_parent.displayname
        if pname == '':
            pname = MAKE_NAME( cursor.semantic_parent.get_usr() )
        parent = self.all[pname]
        v = typedesc.EnumValue(name, value, parent)
        parent.add_value(v)
        return v

    def _fixup_EnumValue(self, e): pass

    # structures, unions, classes
    
    def get_unique_name(self, cursor):
      name = cursor.displayname
      _id = cursor.get_usr()
      if name == '': # anonymous is spelling == ''
          name = MAKE_NAME( _id )
      return name

    @log_entity
    def RECORD(self, cursor):
        ''' A record is a NOT a declaration. A record is the occurrence of of
        previously defined record type. So no action is needed. Type is already 
        known.
        Type is accessible by cursor.type.get_declaration() 
        '''
        if cursor.type.kind == TypeKind.CONSTANTARRAY:
            _decl = cursor.type.get_array_element_type().get_declaration()
        else:
            _decl = cursor.type.get_declaration()

        assert _decl.kind != CursorKind.NO_DECL_FOUND

        name = self.get_unique_name(_decl)
        obj = self.get_registered(name)
        if obj is None:
            log.warning('This RECORD was not previously defined. %s. NOT Adding it'%(name))
            #import code
            #code.interact(local=locals())
            raise ValueError('This RECORD was not previously defined. %s. NOT Adding it'%(name))
        return obj

    @log_entity
    def STRUCT_DECL(self, cursor):
        '''The cursor is on the declaration of a structure.'''
        return self._record_decl(typedesc.Structure, cursor)

    @log_entity
    def UNION_DECL(self, cursor):
        '''The cursor is on the declaration of a union.'''
        return self._record_decl(typedesc.Union, cursor)

    def _record_decl(self, _type, cursor):
        ''' a structure and an union have the same handling.'''
        
        name = self.get_unique_name(cursor)
        if name in codegenerator.dont_assert_size:
            return typedesc.Ignored(name)
        # TODO unittest: try redefinition.
        # check for definition already parsed 
        if (self.is_registered(name) and 
            self.get_registered(name).members is not None):
            return True 
        # FIXME: lets ignore bases for now.
        #bases = attrs.get("bases", "").split() # that for cpp ?
        bases = [] # FIXME: support CXX
        align = cursor.type.get_align() 
        if align < 0 :
            log.error('invalid structure %s %s'%(name, cursor.location))
            return True
        size = cursor.type.get_size()
        packed = False # FIXME
        log.debug('_record_decl: name: %s size:%d'%(name, size))
        # Declaration vs Definition point
        # when a struct decl happen before the definition, we have no members
        # in the first declaration instance.
        if not cursor.is_definition():
            # juste save the spot, don't look at members == None
            log.debug('XXX cursor %s is not on a definition'%(name))
            obj = _type(name, align, None, bases, size, packed=packed)
            return self.register(name, obj)
        log.debug('XXX cursor %s is a definition'%(name))
        # capture members declaration
        members = []
        # Go and recurse through children to get this record member's _id
        # Members fields will not be "parsed" here, but later.
        for child in cursor.get_children():
            if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                # LLVM-CLANG, issue https://github.com/trolldbois/python-clang/issues/2
                # CIndexUSR.cpp:800+ // Bit fields can be anonymous.
                _cid = child.get_usr()
                if _cid == '' and child.is_bitfield():
                    _cid = cursor.get_usr() + "@Ab"
                # END FIXME
                members.append( _cid )
                continue
            # FIXME LLVM-CLANG, patch http://lists.cs.uiuc.edu/pipermail/cfe-commits/Week-of-Mon-20130415/078445.html
            #if child.kind == clang.cindex.CursorKind.PACKED_ATTR:
            #    packed = True
        obj = None
        if self.is_registered(name): 
            # STRUCT_DECL as a child of TYPEDEF_DECL for example
            log.debug('%s was previously registered'%(name))
            obj = self.get_registered(name)
            obj.members = members
        else:
            obj = _type(name, align, members, bases, size, packed=packed)
            self.register(name, obj)
            self.set_location(obj, cursor)
        return obj

    def _make_padding(self, name, offset, length):
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

    def _fixup_Structure(self, s):
        log.debug('Struct/Union_FIX: %s '%(s.name))
        #import code
        #code.interact(local=locals())
        #print 'before', s.members
        #for m in s.members:
        #    if m not in self.all:
        #        print s.name,s.location
        members = []
        offset = 0
        padding_nb = 0
        member = None
        # create padding fields
        #DEBUG FIXME: why are s.members already typedesc objet ?
        for m in s.members: # s.members are strings - NOT
            if m not in self.all or type(self.all[m]) != typedesc.Field:
                # DEBUG
                #import code
                #code.interact(local=locals())
                log.warning('Fixup_struct: Member unexpected : %s'%(m))
                #continue
                raise TypeError('Fixup_struct: Member unexpected : %s'%(m))
            member = self.all[m]
            log.debug('Fixup_struct: Member:%s offset:%d-%d expecting offset:%d'%(
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
        offset = members[-1].offset + members[-1].bits
        # go
        s.members = members
        log.debug("FIXUP_STRUCT: size:%d offset:%d"%(s.size*8, offset))
        # FIXME:
        if member and not member.is_bitfield:
            assert offset == s.size*8 #, assert that the last field stop at the size limit
        pass
    _fixup_Union = _fixup_Structure

    Class = STRUCT_DECL
    _fixup_Class = _fixup_Structure

    @log_entity
    def FIELD_DECL(self, cursor):
        ''' a fundamentalType field needs to get a _type
        a Pointer need to get treated by self.POINTER ( no children )
        a Record needs to be treated by self.record... etc..
        '''
        # name, type
        name = cursor.displayname
        _id = cursor.get_usr()
        offset = cursor.semantic_parent.type.get_offset(name)
        # bitfield
        bits = None
        if cursor.is_bitfield():
            bits = cursor.get_bitfield_width()
            if name == '': # TODO FIXME libclang, get_usr() should return != ''
                log.warning("Cursor has no displayname - anonymous bitfield")
                _id = cursor.semantic_parent.get_usr() + "@Ab"
                name = "anonymous_bitfield"
        else:
            bits = cursor.type.get_size() * 8
        if name == '': 
            raise ValueError("Field has no displayname")
        # try to get a representation of the type
        _canonical_type = cursor.type.get_canonical()
        _type = None
        if self.is_fundamental_type(_canonical_type):
            _type = self.FundamentalType(_canonical_type)
        #elif self.is_pointer_type(_canonical_type):
        #    _type = self.POINTER(cursor)
        else: # RECORD, FNPTR
            ''' No need to try and get the subtypes, it will show up in children.
            '''
            log.debug("FIELD_DECL: displayname:'%s'"%(cursor.get_usr()))
            log.debug("%s: nb children:%s"%(cursor.type.kind, len([c for c in cursor.get_children()])))
            mth = getattr(self, _canonical_type.kind.name)
            if mth is None:
                raise TypeError('unhandled Field TypeKind %s'%(_canonical_type.kind.name))
            # Go and register the field's type from its declaration location
            #print'PPPPPPPPPPPPP'
            #import code, sys
            #code.interact(local=locals())
            #_type = mth(cursor.type.get_declaration())
            _type = mth(cursor)
            if _type is None:
                raise TypeError('Field can not be None %s'%(name ))   
        #else:
        #    log.debug("FIELD_DECL: TypeKind:'%s'"%(t.kind.name))
        #import code, sys
        #code.interact(local=locals())
        return self.register( _id, typedesc.Field(name, _type, offset, bits, is_bitfield=cursor.is_bitfield()))

    def _fixup_Field(self, f):
        #print 'fixup field', f.type
        #if f.type is not None:
        #    mth = getattr(self, '_fixup_%s'%(type(f.type).__name__))
        #    mth(f.type)
        pass

    ################

    def _fixup_Macro(self, m):
        pass

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
                       typedesc.Variable, typedesc.Macro, typedesc.Alias )
                       #typedesc.Field) #???

        self.get_macros(self.cpp_data.get("functions"))
        # fix all objects after that all are resolved
        remove = []
        for _id, _item in self.all.items():
            location = getattr(_item, "location", None)
            # FIXME , why do we get different location types
            if location and hasattr(location, 'file'):
                _item.location = location.file.name, location.line
                log.error('%s %s came in with a SourceLocation'%(_id, _item))
            elif location is None:
                log.warning('item %s has no location.'%(_id))
                #import code
                #code.interact(local=locals())
            #elif not hasattr(location, 'file'):
            #    log.warning('item %s location has no file.'%(_id))
            #    #import code
            #    #code.interact(local=locals())
            mth = getattr(self, "_fixup_" + type(_item).__name__)
            try:
                mth(_item)
            except IOError,e:#KeyError,e: # XXX better exception catching
                log.warning('function "%s" missing, err:%s, remove %s'%("_fixup_" + type(_item).__name__, e, _id) )
                remove.append(_id)
            
        for _x in remove:
            del self.all[_x]

        # Now we can build the namespace.
        namespace = {}
        for i in self.all.values():
            if not isinstance(i, interesting):
                #log.debug('ignoring %s'%( i) )
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
        #import code
        #code.interact(local=locals())

        
        #print 'clangparser get_result:',result
        return result
    
    #catch-all
    def __getattr__(self, name):
        if name not in self._unhandled:
            log.debug('%s is not handled'%(name))
            self._unhandled.append(name)
            #return None
        def p(node, **args):
            for child in node.get_children():
                self.startElement( child ) 
        return p


