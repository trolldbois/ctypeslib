# typedesc.py - classes representing C type descriptions
try:
    set
except NameError:
    from sets import Set as set

class Argument(object):
    "a Parameter in the argument list of a callable (Function, Method, ...)"
    def __init__(self, name, _type):
        self.typ = _type
        self.name = name

class _HasArgs(object):

    def __init__(self):
        self.arguments = []

    def add_argument(self, arg):
        assert isinstance(arg, Argument)
        self.arguments.append(arg)

    def iterArgTypes(self):
        for a in self.arguments:
            yield a.typ

    def iterArgNames(self):
        for a in self.arguments:
            yield a.name

    def fixup_argtypes(self, cb):
        #for a in self.arguments:
        #    getattr(cb, a.a.atype = typemap[a.atype]
        import code
        code.interact(local=locals())


################

class Alias(object):
    # a C preprocessor alias, like #define A B
    def __init__(self, name, alias, typ=None):
        self.name = name
        self.alias = alias
        self.typ = typ

class Macro(object):
    # a C preprocessor definition with arguments
    def __init__(self, name, args, body):
        # all arguments are strings, args is the literal argument list
        # *with* the parens around it:
        # Example: Macro("CD_INDRIVE", "(status)", "((int)status > 0)")
        self.name = name
        self.args = args
        self.body = body

class File(object):
    def __init__(self, name):
        self.name = name

class Function(_HasArgs):
    location = None
    def __init__(self, name, returns, attributes, extern):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns
        self.attributes = attributes # dllimport, __stdcall__, __cdecl__
        self.extern = extern

class Ignored(_HasArgs):
    location = None
    def __init__(self, name):
        _HasArgs.__init__(self)
        self.name = name

class OperatorFunction(_HasArgs):
    location = None
    def __init__(self, name, returns):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns

class FunctionType(_HasArgs):
    location = None
    def __init__(self, returns, attributes):
        _HasArgs.__init__(self)
        self.returns = returns
        self.attributes = attributes
        self.name = "FP_"

class Method(_HasArgs):
    location = None
    def __init__(self, name, returns):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns

class FundamentalType(object):
    location = None
    def __init__(self, name, size, align):
        self.name = name
        if name != "void":
            self.size = int(size)
            self.align = int(align)
        
class PointerType(object):
    location = None
    def __init__(self, typ, size, align):
        self.typ = typ
        self.size = int(size)
        self.align = int(align)
        # USELESS FIXME
        if type(typ) is str:
            self.name = "LP_%s"%(self.typ)
            log.warning('FIXME Pointertype subtype name should not be str')
        else:
            self.name = "LP_%s"%(self.typ.name)

class Typedef(object):
    location = None
    def __init__(self, name, typ):
        self.name = name
        self.typ = typ

class ArrayType(object):
    location = None
    def __init__(self, typ, size):
        self.typ = typ
        self.size = size
        self.name = "array_%s"%(typ.name)

class StructureHead(object):
    location = None
    def __init__(self, struct):
        self.struct = struct

class StructureBody(object):
    location = None
    def __init__(self, struct):
        self.struct = struct

class _Struct_Union_Base(object):
    location = None
    def get_body(self):
        return self.struct_body

    def get_head(self):
        return self.struct_head

class Structure(_Struct_Union_Base):
    def __init__(self, name, align, members, bases, size, artificial=None, 
                 packed=False):
        self.name = name
        self.align = int(align)
        self.members = members
        self.bases = bases
        self.artificial = artificial
        self.size = size
        self.packed = packed
        self.struct_body = StructureBody(self)
        self.struct_head = StructureHead(self)

class Union(_Struct_Union_Base):
    def __init__(self, name, align, members, bases, size, artificial=None, 
                 packed=False):
        self.name = name
        self.align = int(align)
        self.members = members
        self.bases = bases
        self.artificial = artificial
        if size is not None:
            self.size = int(size)
        else:
            self.size = None
        self.packed = packed
        self.struct_body = StructureBody(self)
        self.struct_head = StructureHead(self)

class Field(object):
    ''' Change bits if its a bitfield'''
    def __init__(self, name, typ, offset, bits, is_bitfield=False):
        self.name = name
        self.type = typ
        self.offset = offset
        self.bits = bits
        self.is_bitfield = is_bitfield

class CvQualifiedType(object):
    def __init__(self, typ, const, volatile):
        self.typ = typ
        self.const = const
        self.volatile = volatile
        self.name = 'CV_QUAL_%s'%(self.typ.name)

class Enumeration(object):
    location = None
    def __init__(self, name, size, align):
        self.name = name
        self.size = int(size)
        self.align = int(align)
        self.values = []

    def add_value(self, v):
        self.values.append(v)

class EnumValue(object):
    def __init__(self, name, value, enumeration):
        self.name = name
        self.value = value
        self.enumeration = enumeration

class Variable(object):
    location = None
    def __init__(self, name, typ, init=None):
        self.name = name
        self.typ = typ
        self.init = init

################################################################
