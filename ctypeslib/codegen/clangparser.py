"""clangparser - use clang to get preprocess a source code."""

import clang.cindex 
from clang.cindex import Index
from clang.cindex import CursorKind, TypeKind
import ctypes

import logging

import codegenerator
import typedesc
import sys
import re

log = logging.getLogger('clangparser')
logging.basicConfig(level=logging.DEBUG)

# TODO:
# ignore packing method.
# clang does a better job.

################################################################
clang_ctypes_names = {
    #TypeKind.INVALID : 'None' ,
    #TypeKind.UNEXPOSED : 'c_' ,
    TypeKind.VOID : 'None' ,
    TypeKind.BOOL : 'c_bool' ,
    TypeKind.CHAR_U : 'c_ubyte' ,
    TypeKind.UCHAR : 'c_ubyte' ,
    TypeKind.CHAR16 : 'c_wchar' ,
    TypeKind.CHAR32 : 'c_wchar*2' , # FIXME
    TypeKind.USHORT : 'c_ushort' ,
    TypeKind.UINT : 'c_uint' ,
    TypeKind.ULONG : 'c_ulong' ,
    TypeKind.ULONGLONG : 'c_ulonglong' ,
    TypeKind.UINT128 : 'c_uin128' , #FIXME
    TypeKind.CHAR_S : 'c_byte' ,
    TypeKind.SCHAR : 'c_byte' ,
    TypeKind.WCHAR : 'c_wchar' ,
    TypeKind.SHORT : 'c_short' ,
    TypeKind.INT : 'c_int' ,
    TypeKind.LONG : 'c_long' ,
    TypeKind.LONGLONG : 'c_longlong' ,
    TypeKind.INT128 : 'c_int128' , # FIXME
    TypeKind.FLOAT : 'c_float' ,
    TypeKind.DOUBLE : 'c_double' ,
    TypeKind.LONGDOUBLE : 'c_longdouble' ,
    #TypeKind.NULLPTR : 'c_void_p' , #FIXME
    #TypeKind.OVERLOAD : 'c_' ,
    #TypeKind.DEPENDENT : 'c_' ,
    #TypeKind.OBJCID : 'c_' ,
    #TypeKind.OBJCCLASS : 'c_' ,
    #TypeKind.OBJCSEL : 'c_' ,
    #TypeKind.COMPLEX : 'c_' ,
    #TypeKind.POINTER : 'c_void_p' ,
    #TypeKind.BLOCKPOINTER : 'c_void_p' ,
    #TypeKind.LVALUEREFERENCE : 'c_' ,
    #TypeKind.RVALUEREFERENCE : 'c_' ,
    #TypeKind.RECORD : 'c_' ,
    #TypeKind.ENUM : 'c_' ,
    #TypeKind.TYPEDEF : 'c_' ,
    #TypeKind.OBJCINTERFACE : 'c_' ,
    #TypeKind.OBJCOBJECTPOINTER : 'c_' ,
    #TypeKind.FUNCTIONNOPROTO : 'c_' ,
    #TypeKind.FUNCTIONPROTO : 'c_' ,
    #TypeKind.CONSTANTARRAY : 'c_' ,
}

def MAKE_NAME(name):
    name = name.replace("$", "DOLLAR")
    name = name.replace(".", "DOT")
    name = name.replace("@", "_")
    name = name.replace(":", "_")
    if name.startswith("__"):
        return "_X" + name
    elif name[0] in "01234567879":
        return "_" + name
    return name

WORDPAT = re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

def CHECK_NAME(name):
    if WORDPAT.match(name):
        return name
    return None

''' 
-fdump-record-layouts
~/Compil/llvm/clang$ clang -cc1 -fdump-record-layouts test/CodeGenCXX/override-layout.cpp
works.

TODO: need more info on records.
in RecordLayoutBuidler:
        const ASTRecordLayout & ASTContext::getASTRecordLayout(const RecordDecl *D) const {
can give us the information.

So I need to 
a) export that function.
b) have an ASTContext object - OK

ASTUnit->getASTContext()

CIndex.cpp:56 
MakeCXTranslationUnit makes a CXTranslationUnit
CXTranslationUnit->TUData is a ASTUnit

CIndex.cpp:2536
clang_parseTranslationUnit take args in args.
and return the CXTranslationUnit

Donc dans 
    tu = index.parse(None, args)
tu.obj nous donne le pointer vers CXTranslationUnit
iil faudrait que cindex.py donne aces a un getASTUnit

struct CXTranslationUnitImpl {
  void *CIdx;
  void *TUData;
  void *StringPool;
  void *Diagnostics;
  void *OverridenCursorsPool;
  void *FormatContext;
  unsigned FormatInMemoryUniqueId;
};

So I could do ( preferably in C plutot )
    CXTranslationUnitImpl(Structure)
    ASTUnit(Structure) #on TUData
    ASTContext(Structure)
    then
    ADTUnit_getContext() restype ASTContext
    ASTContext_getASTRecordLayout( RecordDecl ) restype ASTRecordLayout
    ( also _align )

Best solution, 
add getASTRecordLayout infos into 

How to get a RecordDecl ?

##########################################################

TODO TEST
cross-arch native in clang:
-m64 or "-cc1" "-triple" "x86_64-pc-linux-gnu"
-m32 or "-cc1" "-triple" "i386-pc-linux-gnu"
ex: 
clang -\#\#\# -m64 test/CodeGenCXX/override-layout.cpp 
clang -\#\#\# -m32 test/CodeGenCXX/override-layout.cpp

clang -cc1 -triple "x86_64-pc-linux-gnu" -fdump-record-layouts test/CodeGenCXX/override-layout.cpp 
clang -cc1 -triple "i386-pc-linux-gnu" -fdump-record-layouts test/CodeGenCXX/override-layout.cpp 

==> cross arch ctypes definition. BIG WIN.

'''
class Clang_Parser(object):
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

    def __init__(self, *args):
        #self.args = *args
        self.context = []
        self.all = {}
        self.cpp_data = {}
        self._unhandled = []
        self.tu = None

    def parse(self, args):
        index = Index.create()
        self.tu = index.parse(None, args)
        if not self.tu:
            log.warning("unable to load input")
            return
        
        root = self.tu.cursor
        self.context = []
        for node in root.get_children():
            self.startElement( node )


    def startElement(self, node ): #kind, attrs):
        if node is None:
            return

        # find and call the handler for this element
        mth = getattr(self, node.kind.name)
        if mth is None:
            return
        
        #log.debug('Found a %s|%s|%s'%(node.kind.name, node.displayname, node.spelling))
        
        result = mth(node)
        if result is None:
            return
        #if isinstance(result, (str,)):
        #    return

        if node.location.file is not None:
            #print result, node
            result.location = node.location

        ## self.all[_id] should return the Typedesc object, so that type(x).__name__ is a local func to codegen object
        _id = node.get_usr()
        #print '++ startElement _id ', _id
        if _id != '' and result is not None: # TYPE_REF, Ignore.        
            self.all[_id] = result
        elif result is None:
            log.debug('None result')
        
        # if this element has children, treat them.
        # if name in self.has_values:

        self.context.append( node )
        for child in node.get_children():
            self.startElement( child )          
        self.context.pop()
        return result

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

    def UNEXPOSED_ATTR(self, cursor): 
        #log.debug('Found UNEXPOSED_ATTR %s %s'%(cursor.kind.name, cursor.kind.value))
        parent = self.context[-1]
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
    
    # simple types and modifiers
    # FIXME, token is bad, ar_ref is bad
    def VAR_DECL(self, cursor):
        import code
        #code.interact(local=locals())
        
        name = cursor.displayname
        if name.startswith("cpp_sym_"):
            # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXx fix me!
            name = name[len("cpp_sym_"):]
        # I dont have the value... 
        init = None
        for c in cursor.get_children():
            for t in c.get_tokens():
                init = t.spelling
                break
            break
            #print init
        #print 'VAR_DECL init', init
        try:
            int(init)
        except:
            init = None
        # now get the type
        typ = cursor.type.get_canonical().kind
        if typ in clang_ctypes_names:
            ctypesname = clang_ctypes_names[typ]
            typ = typedesc.FundamentalType( ctypesname, 0, 0 )
        else:
            typ = cursor.get_usr() #cursor.type.get_canonical().kind.name

        #print typ.__class__.__name__
        return typedesc.Variable(name, typ, init)

    def _fixup_Variable(self, t):
        if type(t.typ) == str: #typedesc.FundamentalType:
            t.typ = self.all[t.typ]

    #def Typedef(self, attrs):
    def TYPEDEF_DECL(self, cursor):
        name = cursor.displayname
        typ = cursor.type.get_canonical().kind
        if typ in clang_ctypes_names:
            ctypesname = clang_ctypes_names[typ]
            typ = typedesc.FundamentalType( ctypesname, 0, 0 )
        else:
            typ = cursor.get_usr() #cursor.type.get_canonical().kind.name
        return typedesc.Typedef(name, typ)

    def _fixup_Typedef(self, t):
        #print 'fixing typdef %s name:%s with self.all[%s] = %s'%(id(t), t.name, t.typ, id(self.all[ t.typ])) 
        if type(t.typ) == str: #typedesc.FundamentalType:
            t.typ = self.all[ t.typ]
        pass

    def TYPE_REF(self, t):
        if not t.is_definition():
            return
        # get the definition, create or reuse typedesc.
        next = t.get_definition()
        _id = next.get_usr()
        ##print '** _id is ', _id
        if _id in self.all:
            return self.all[_id]
        mth = getattr(self, next.kind.name)
        if mth is None:
            raise TypeError('unhandled Type_ref TypeKind %s'%(next.kind))
        res = mth(next)
        if res is not None:
            self.all[_id] = res
            return self.all[_id]
        log.error('None on TYPE_REF')
        return
        
        
    def FundamentalType(self, typ):
        #print cursor.displayname
        #t = cursor.type.get_canonical().kind
        ctypesname = clang_ctypes_names[typ]
        if ctypesname == "None":
            size = 0
        else:
            size = 0 # ctypes.sizeof(getattr(ctypes, ctypesname))
        align = self.all[ self.context[-1].get_usr() ].align
        return typedesc.FundamentalType( ctypesname, size, align )

    def _fixup_FundamentalType(self, t): pass

    def POINTER(self, cursor):
        # we shortcut to canonical defs
        typ = cursor.type.get_pointee().get_canonical().kind

        #import code
        #code.interact(local=locals())

        if typ in clang_ctypes_names:
            ctypesname = clang_ctypes_names[typ]
            if ctypesname == "None":
                size = 0
            else:
                size = 0 #ctypes.sizeof(getattr(ctypes, ctypesname))
            align = self.all[ self.context[-1].get_usr() ].align
            typ = typedesc.FundamentalType( ctypesname, size, align )
        elif typ == TypeKind.RECORD:
            children = [c for c in cursor.get_children()]
            if len(children) != 1:
                raise ValueError('There is %d children - not expected in PointerType'%(len(children)))
            if children[0].kind != CursorKind.TYPE_REF:
                raise TypeError('Wasnt expecting a %s in PointerType'%(children[0].kind))
            typ = children[0].get_definition().get_usr()
        else:
            raise TypeError('Unknown scenario in PointerType - %s'%(typ))

        #print typ
        # FIXME, size should be given by clang. Here we restrict size to local arch
        size = ctypes.sizeof(ctypes.c_void_p)
        #
        align = self.all[ self.context[-1].get_usr() ].align
        
        return typedesc.PointerType( typ, size, align)


    def _fixup_PointerType(self, p):
        #print '*** Fixing up PointerType', p.typ
        #import code
        #code.interact(local=locals())
        ##if type(p.typ.typ) != typedesc.FundamentalType:
        ##    p.typ.typ = self.all[p.typ.typ]
        if type(p.typ) != typedesc.FundamentalType:
            p.typ = self.all[p.typ]

    ReferenceType = POINTER
    _fixup_ReferenceType = _fixup_PointerType
    OffsetType = POINTER
    _fixup_OffsetType = _fixup_PointerType

    def CONSTANTARRAY(self, cursor):
        size = str( cursor.type.get_array_size() )
        typ = cursor.type.get_array_element_type().get_canonical().kind
        if typ in clang_ctypes_names:
            typ = self.FundamentalType( typ )
        else:
            mth = getattr(self, typ.name)
            if mth is None:
                raise TypeError('unhandled Field TypeKind %s'%(t.name))
            typ  = mth(cursor)
            if typ is None:
                return None

        #import code
        #code.interact(local=locals())
        
        return typedesc.ArrayType(typ, size, size)

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
        return typedesc.CvQualifiedType(typ, const, volatile)

    def _fixup_CvQualifiedType(self, c):
        c.typ = self.all[c.typ]

    # callables
    
    #def Function(self, attrs):
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
        return typedesc.Function(name, returns, attributes, extern)

    def _fixup_Function(self, func):
        #FIXME
        #func.returns = self.all[func.returns]
        #func.fixup_argtypes(self.all)
        pass

    def FunctionType(self, attrs):
        # id, returns, attributes
        returns = attrs["returns"]
        attributes = attrs.get("attributes", "").split()
        return typedesc.FunctionType(returns, attributes)
    
    def _fixup_FunctionType(self, func):
        func.returns = self.all[func.returns]
        func.fixup_argtypes(self.all)

    def OperatorFunction(self, attrs):
        # name, returns, extern, attributes
        name = attrs["name"]
        returns = attrs["returns"]
        return typedesc.OperatorFunction(name, returns)

    def _fixup_OperatorFunction(self, func):
        func.returns = self.all[func.returns]

    def _Ignored(self, attrs):
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
    def PARM_DECL(self, p):
    #    import code
    #    code.interact(local=locals())
    #    parent = self.context[-1]
    #    if parent is not None:
    #        parent.add_argument(typedesc.Argument(p.type.get_canonical(), p.name))
        return

    # Just ignore it.
    def INTEGER_LITERAL(self, i):
        #print ' im a integer i'
        #import code
        #code.interact(local=locals())
        return

    # enumerations

    def ENUM_DECL(self, cursor):
        # id, name
        #print '** ENUMERATION', cursor.displayname
        name = cursor.displayname
        #if name == '':
        #    #raise ValueError('could try get_usr()')
        #    name = MAKE_NAME( cursor.get_usr() )
        align = clang.cindex.conf.lib.clang_getRecordAlignment( self.tu, cursor) # 
        size = clang.cindex.conf.lib.clang_getRecordSize( self.tu, cursor) # 
        #print align, size
        return typedesc.Enumeration(name, size, align)

    def _fixup_Enumeration(self, e): pass

    def ENUM_CONSTANT_DECL(self, cursor):
        name = cursor.displayname
        value = cursor.enum_value
        parent = self.all[self.context[-1].get_usr()]        
        v = typedesc.EnumValue(name, value, parent)
        parent.add_value(v)
        return v

    def _fixup_EnumValue(self, e): pass

    # structures, unions, classes

    def RECORD(self, cursor):
        # either Union, Struct, Enum(?) in Ref or in Decl.
        ## TypeKind RECORD = cursor.type.get_canonical().kind
        children = [c for c in cursor.get_children()]
        if len(children) != 1:
            raise ValueError('There is %d children - not expected in a record type '%(len(children)))

        next = children[0]
        mth = getattr(self, next.kind.name)
        if mth is None:
            raise TypeError('unhandled Record TypeKind %s'%(next.kind))
        ## if next == CursorKind.TYPE_REF: # defer
        ## if next == CursorKind.UNION_DECL: # create
        ## if next == CursorKind.g: # create
        
        #import code
        #code.interact(local=locals())

        return mth(next)

    def STRUCT_DECL(self, cursor):

        #import code
        #code.interact(local=locals())
        
        if not cursor.is_definition():
            return
        
        # id, name, members
        name = cursor.displayname
        if name == '': # anonymous is spelling == ''
            name = MAKE_NAME( cursor.get_usr() )
            #import code
            #code.interact(local=locals())
        if name in codegenerator.dont_assert_size:
            return typedesc.Ignored(name)
        # should be in MAKE_NAME
        for k, v in [('<','_'), ('>','_'), ('::','__'), (',',''), (' ',''), ]:
          if k in name: # template
            name = name.replace(k,v)
        # FIXME: lets ignore bases for now.
        #bases = attrs.get("bases", "").split() # that for cpp ?
        bases = [] # FIXME: support CXX

        align = clang.cindex.conf.lib.clang_getRecordAlignment( self.tu, cursor) 
        size = clang.cindex.conf.lib.clang_getRecordSize( self.tu, cursor) 

        members = [ child.get_usr() for child in cursor.get_children() if child.kind == clang.cindex.CursorKind.FIELD_DECL ]
        #print 'found %d members'%( len(members))
        return typedesc.Structure(name, align, members, bases, size)

    def _fixup_Structure(self, s):
        #print 'before', s.members
        #for m in s.members:
        #    if m not in self.all:
        #        print s.name,s.location
        s.members = [self.all[m] for m in s.members if m in self.all and type(self.all[m]) == typedesc.Field ]
        #print 'after', [m.typ for m in s.members], len(s.members )
        #if s.members[0] is None:
        #    s.members = []
        #print len(s.members), type(s.members[0])
        #print 'after', [m.typ for m in s.members]
        #s.bases = [self.all[b] for b in s.bases]
        pass
    _fixup_Union = _fixup_Structure

    def UNION_DECL(self, cursor):
        name = cursor.displayname
        if name == '': # anonymous is spelling == ''
            name = MAKE_NAME( cursor.get_usr() )
        bases = [] # FIXME: support CXX
        align = clang.cindex.conf.lib.clang_getRecordAlignment( self.tu, cursor) # 
        size = clang.cindex.conf.lib.clang_getRecordSize( self.tu, cursor) # 
        members = [ child.get_usr() for child in cursor.get_children() if child.kind == clang.cindex.CursorKind.FIELD_DECL ]
        return typedesc.Union(name, align, members, bases, size)

    Class = STRUCT_DECL
    _fixup_Class = _fixup_Structure

    def FIELD_DECL(self, cursor):
        # name, type
        name = cursor.displayname
##        if name.startswith("__") and not name.endswith("__"):
##            print "INVALID FIELD NAME", name

        t = cursor.type.get_canonical().kind
        if t in clang_ctypes_names:
            # goto self.FundamentalType
            typ = self.FundamentalType(t)
        else:
            mth = getattr(self, t.name)
            if mth is None:
                raise TypeError('unhandled Field TypeKind %s'%(t.name))
            typ  = mth(cursor)
            if typ is None:
                return None
                #raise TypeError('Field can not be None %s %s'%(name, t.name))   

        # FIXME
        # bits = attrs.get("bits", None)
        bits = None
        offset = clang.cindex.conf.lib.clang_getRecordFieldOffset(self.tu, cursor)

        return typedesc.Field(name, typ, bits, offset)

    def _fixup_Field(self, f):
        #print 'fixup field', f.typ
        if f.typ is not None:
            mth = getattr(self, '_fixup_%s'%(type(f.typ).__name__))
            mth(f.typ)
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
        interesting = (typedesc.Typedef, typedesc.Enumeration, typedesc.EnumValue,
                       typedesc.Function, typedesc.Structure, typedesc.Union,
                       typedesc.Variable, typedesc.Macro, typedesc.Alias )
                       #typedesc.Field) #???

        self.get_macros(self.cpp_data.get("functions"))
        
        remove = []
        for n, i in self.all.items():
            location = getattr(i, "location", None)
            if location:
                i.location = location.file.name, location.line
            mth = getattr(self, "_fixup_" + type(i).__name__)
            try:
                mth(i)
            except IOError,e:#KeyError,e: # XXX better exception catching
                log.warning('function "%s" missing, err:%s, remove %s'%("_fixup_" + type(i).__name__, e, n) )
                remove.append(n)

        for n in remove:
            del self.all[n]

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
        def p(node):
            for child in node.get_children():
                self.startElement( child ) 
        return p

################################################################

def parse(args):
    # parse an XML file into a sequence of type descriptions
    parser = Clang_Parser()
    parser.parse(args)
    return parser.get_result()
