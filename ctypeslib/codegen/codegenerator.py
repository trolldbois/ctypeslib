'''Create ctypes wrapper code for abstract type descriptions.
Type descriptions are collections of typedesc instances.
'''

import typedesc, sys, os
import textwrap
import struct
import ctypes

import clangparser

import logging
log = logging.getLogger('codegen')

import code

# This should be configurable
ASSUME_STRINGS = True

import StringIO # need unicode support, no cStringIO


# XXX Should this be in ctypes itself?
ctypes_names = {
    "bool": "c_bool",
    "unsigned char": "c_ubyte",
    "signed char": "c_byte",
    "char": "c_char",

    "wchar_t": "c_wchar",

    "short unsigned int": "c_ushort",
    "short int": "c_short",

    "long unsigned int": "c_ulong",
    "long int": "c_long",
    "long signed int": "c_long",

    "unsigned int": "c_uint",
    "int": "c_int",

    "long long unsigned int": "c_ulonglong",
    "long long int": "c_longlong",

    "double": "c_double",
    "float": "c_float",

    "long double": "c_longdouble",

    # Hm...
    "void": "None",
}

################

def storage(t):
    # return the size and alignment of a type
    if isinstance(t, typedesc.Typedef):
        return storage(t.typ)
    elif isinstance(t, typedesc.CvQualifiedType):
      return storage(t.typ)
    elif isinstance(t, typedesc.ArrayType):
        s, a = storage(t.typ)
        return s * (int(t.max) - int(t.min) + 1), a
    return int(t.size), int(t.align)



def get_real_type(tp):
    if type(tp) is typedesc.Typedef:
        if type(tp.typ) is typedesc.Typedef:
            import code
            code.interact(local=locals())
            raise TypeError('Nested loop in Typedef %s'%(tp.name))
        return get_real_type(tp.typ)
    elif isinstance(tp, typedesc.CvQualifiedType):
        return get_real_type(tp.typ)
    return tp

def _clean_name(func):
    def fn_clean(*args, **kwargs):
        name = func(*args, **kwargs)
        return name
    return fn_clean

################################################################

class Initializer(object):

    def __call__(self, tp, init, is_pointer=False):
        try:
            mth = getattr(self, tp.__class__.__name__)
        except AttributeError:
            raise TypeError("Cannot initialize %s" % tp.__class__.__name__)
        return mth(tp, init, is_pointer)

    def FundamentalType(self, tp, init, is_pointer=False):
        try:
            #mth = getattr(self, ctypes_names[tp.name].replace("None", "void"))
            mth = getattr(self, tp.name.replace("None", "void"))
        except AttributeError:
            raise TypeError("Cannot initialize %s" % tp.name)
        return mth(tp, init, is_pointer)

    def CvQualifiedType(self, tp, init, is_pointer=False):
        return self(tp.typ, init, is_pointer)

    def PointerType(self, tp, init, is_pointer=False):
        return self(tp.typ, init, is_pointer=True)

    ##### ctypes types initializers #####

    def void(self, tp, init, is_pointer=False):
        if not is_pointer:
            raise RuntimeError # a void type does not exist
        if init.find('"') >= 0:
            # strip off type casts, if any
            init = init[init.find('"'):]
        value = eval(init)
        return ctypes.c_void_p(value).value

    def c_ubyte(self, tp, init, is_pointer=False):
        value = eval(init)
        return ctypes.c_ubyte(value).value

    def c_char(self, tp, init, is_pointer=False):
        if init.find('"') >= 0:
            init = init[init.find('"'):]
        value = eval(init)
        if isinstance(value, (int, long)):
            if is_pointer:
                return ctypes.c_void_p(value).value
            else:
                return chr(value)
        if not is_pointer:
            assert isinstance(value, basestring)
            assert len(value) == 1
        return value

    def c_wchar(self, tp, init, is_pointer=False):
        if init.find('"') >= 0:
            init = init[init.find('"'):]
        value = eval(init)
        if isinstance(value, (int, long)):
            if is_pointer:
                return ctypes.c_void_p(value).value
            else:
                return unichr(value)
        if not is_pointer:
            assert isinstance(value, basestring)
            assert len(value) == 1
        if isinstance(value, str):
            # gccxml returns unicode initializers as 32-but values in
            # byte strings, with a 3-nul bytes termination:
            # "A\x00\x00\x00B\x00\x00\x00C\x00\x00\x00\x00\x00\x00" -> u"ABC"
            ws = ctypes.sizeof(ctypes.c_wchar)
            if ws == 4:
                v = value[:-3]
                value = "".join(map(unichr, struct.unpack("I" * (len(v)/4), v)))
            elif ws == 2:
                v = value[:-1]
                value = "".join(map(unichr, struct.unpack("H" * (len(v)/2), v)))
        return value

##    def void(self, tp, init, is_pointer=False):
##        if is_pointer:
##            value = eval(value)
##            return ctypes.c_void_p(value).value
##        raise RuntimeError("void???")

    def _init_integer(self, ctyp, suffixes, init):
        value = init.rstrip(suffixes)
        value = eval(value)
        return ctyp(value).value

    def _init_float(self, ctyp, suffixes, init):
        value = init.rstrip(suffixes)
        value = eval(value)
        return ctyp(value).value

    def c_short(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_short, "i", init)
                                                                                            
    def c_ushort(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_ushort, "ui", init)
                                                                                            
    def c_int(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_int, "i", init)
                                                                                            
    def c_uint(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_uint, "ui", init)
                                                                                            
    def c_long(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_long, "l", init)
                                                                                            
    def c_ulong(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_ulong, "ul", init)
                                                                                            
    def c_longlong(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_longlong, "l", init)
                                                                                            
    def c_ulonglong(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_ulonglong, "ul", init)
                                                                                            
    def c_double(self, tp, init, is_pointer=False):
        return self._init_float(ctypes.c_double, "", init)

    def c_float(self, tp, init, is_pointer=False):
        return self._init_float(ctypes.c_float, "f", init)

class Generator(object):
    def __init__(self, output,
                 generate_comments=False,
                 known_symbols=None,
                 searched_dlls=None,
                 preloaded_dlls=[],
                 generate_docstrings=False,
                 generate_locations=False):
        self.output = output
        self.stream = StringIO.StringIO()
        self.imports = StringIO.StringIO()
##        self.stream = self.imports = self.output
        self.generate_locations = generate_locations
        self.generate_comments = generate_comments
        self.generate_docstrings = generate_docstrings
        self.known_symbols = known_symbols or {}
        self.preloaded_dlls = preloaded_dlls
        if searched_dlls is None:
            self.searched_dlls = []
        else:
            self.searched_dlls = searched_dlls

        self.done = set() # type descriptions that have been generated
        self.names = set() # names that have been generated
        self.initialize = Initializer()

    def enable_pythonic_types(self):
        self.enable_pythonic_types = lambda : True
        import pkgutil
        headers = pkgutil.get_data('ctypeslib','data/pythonic_type_name.tpl')
        print >> self.imports, headers
    
    def type_name(self, t, generate=True):
        # Return a string containing an expression that can be used to
        # refer to the type. Assumes the 'from ctypes import *'
        # namespace is available.
        #import code
        #code.interact(local=locals())
        if isinstance(t, typedesc.Typedef):
            return t.name
        if isinstance(t, typedesc.PointerType):
            #print '** type_name we have pointer ',t
            # Following block is not useful if we use POINTER_T
            #if ASSUME_STRINGS:
            #    x = get_real_type(t.typ)
            #    if isinstance(x, typedesc.FundamentalType):
            #        if x.name == "c_char":
            #            self.need_STRING()
            #            return "STRING"
            #        elif x.name == "c_wchar":
            #            self.need_WSTRING()
            #            return "WSTRING"
            # Size of pointer is handled in headers now.
            #result = "POINTER%d(%s)" %(t.size*8, self.type_name(t.typ, generate))
            result = "POINTER_T(%s)" %(self.type_name(t.typ, generate))
            # XXX Better to inspect t.typ!
            if result.startswith("POINTER(WINFUNCTYPE"):
                return result[len("POINTER("):-1]
            if result.startswith("POINTER(CFUNCTYPE"):
                return result[len("POINTER("):-1]
            elif result == "POINTER(None)":
                return "c_void_p"
            return result
        elif isinstance(t, typedesc.ArrayType):
            return "%s * %s" % (self.type_name(t.typ, generate), t.size)
        elif isinstance(t, typedesc.FunctionType):
            args = [self.type_name(x, generate) for x in [t.returns] + list(t.iterArgTypes())]
            if "__stdcall__" in t.attributes:
                return "WINFUNCTYPE(%s)" % ", ".join(args)
            else:
                return "CFUNCTYPE(%s)" % ", ".join(args)
        elif isinstance(t, typedesc.Variable):
            return "%s" % self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.Argument):
            return "%s" % self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.CvQualifiedType):
            # const and volatile are ignored
            return "%s" % self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.FundamentalType):
            return t.name
        elif isinstance(t, typedesc.Structure):
            return t.name
        elif isinstance(t, typedesc.Enumeration):
            if t.name:
                return t.name
            return "c_int" # enums are integers
        elif isinstance(t, typedesc.Typedef):
            return t.name
        return t.name

    ################################################################

    def Alias(self, alias):
        if self.generate_comments:
            self.print_comment(alias)
        print >> self.stream, "%s = %s # alias" % (alias.name, alias.alias)
        return            

    def Macro(self, macro):
        if macro.location is None:
            log.info('Ignoring %s with no location'%(macro.name))
            return
        if self.generate_locations:
            print >> self.stream, "# %s:%s" % (macro.location)
        if self.generate_comments:
            self.print_comment(macro)
        print >> self.stream, "%s = %s # macro" % (macro.name, macro.body)
        return            
        # We don't know if we can generate valid, error free Python
        # code. All we can do is to try to compile the code.  If the
        # compile fails, we know it cannot work, so we comment out the
        # generated code; the user may be able to fix it manually.
        #
        # If the compilation succeeds, it may still fail at runtime
        # when the macro is called.
        #mcode = "def %s%s: return %s # macro" % (macro.name, macro.args, macro.body)
        try:
            compile(mcode, "<string>", "exec")
        except SyntaxError:
            print >> self.stream, "#", mcode
        else:
            print >> self.stream, mcode, '# Macro'
            self.names.add(macro.name)
        
    _typedefs = 0
    def Typedef(self, tp):
        #print 'Typedef', tp.name, tp.typ
        if self.generate_comments:
            self.print_comment(tp)
        sized_types = {
            "uint8_t":  "c_uint8",
            "uint16_t": "c_uint16",
            "uint32_t": "c_uint32",
            "uint64_t": "c_uint64",
            "int8_t":  "c_int8",
            "int16_t": "c_int16",
            "int32_t": "c_int32",
            "int64_t": "c_int64",
            }
        self._typedefs += 1
        name = self.type_name(tp) # tp.name
        if type(tp.typ) == typedesc.FundamentalType \
           and tp.name in sized_types:
            print >> self.stream, "%s = %s" % \
                  (name, sized_types[tp.name])
            self.names.add(tp.name)
            return
        if tp.typ not in self.done:
            if type(tp.typ) in (typedesc.Structure, typedesc.Union):
                self.generate(tp.typ.get_head())
                self.more.add(tp.typ)
            else:
                self.generate(tp.typ)
        if 0 and self.type_name(tp.typ) in self.known_symbols:
            stream = self.imports
        else:
            stream = self.stream
        # generate actual typedef code.
        if tp.name != self.type_name(tp.typ):
            print >> stream, "%s = %s" % \
                  (name, self.type_name(tp.typ))
        self.names.add(tp.name)

    _arraytypes = 0
    def ArrayType(self, tp):
        self._arraytypes += 1
        #print '***',tp.__class__.__name__, tp.typ.__dict__
        self.generate(get_real_type(tp.typ))
        self.generate(tp.typ)

    _functiontypes = 0
    def FunctionType(self, tp):
        self._functiontypes += 1
        self.generate(tp.returns)
        self.generate_all(tp.arguments)
        #print >> self.stream, "%s = %s # Functiontype " % (
        #          self.type_name(tp), [self.type_name(a) for a in tp.arguments])

    def Argument(self, tp):
        self.generate(tp.typ)
        
    _pointertypes = 0
    def PointerType(self, tp):
        self._pointertypes += 1
        #print 'generate', tp.typ
        if type(tp.typ) is typedesc.PointerType:
            self.generate(tp.typ)
        elif type(tp.typ) in (typedesc.Union, typedesc.Structure):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        elif type(tp.typ) is typedesc.Typedef:
            self.generate(tp.typ)
        else:
            self.generate(tp.typ)

    def CvQualifiedType(self, tp):
        self.generate(tp.typ)

    _variables = 0
    _notfound_variables = 0
    def Variable(self, tp):
        self._variables += 1
        if self.generate_comments:
            self.print_comment(tp)
        dllname = self.find_dllname(tp)
        if dllname:
            self.generate(tp.typ)
            # calling convention does not matter for in_dll...
            libname = self.get_sharedlib(dllname, "cdecl")
            print >> self.stream, \
                  "%s = (%s).in_dll(%s, '%s')" % (tp.name,
                                                  self.type_name(tp.typ),
                                                  libname,
                                                  tp.name)
            self.names.add(tp.name)
            # wtypes.h contains IID_IProcessInitControl, for example
            return

        # Hm.  The variable MAY be a #define'd symbol that we have
        # artifically created, or it may be an exported variable that
        # is not in the libraries that we search.  Anyway, if it has
        # no tp.init value we can't generate code for it anyway, so we
        # drop it.
        #code.interact(local=locals())
        #if tp.init is None:
        #    self._notfound_variables += 1
        #    return
        #el
        if isinstance(tp.init, typedesc.FunctionType):
            print >> self.stream, "%s = %s # args: %s" % (tp.name,
                                             self.type_name(tp.init), 
                                             [x for x in tp.typ.iterArgNames()])
        else:
            if ( isinstance(tp.typ, typedesc.PointerType) and 
                 isinstance(tp.typ.typ, typedesc.FundamentalType) and
                 (tp.typ.typ.name == "c_char" or tp.typ.typ.name == "c_wchar")):
                # char *
                init_value = repr(tp.init)
            elif ( isinstance(tp.typ, typedesc.FundamentalType) and
                 (tp.typ.name == "c_char" or tp.typ.name == "c_wchar")):
                # char
                init_value = repr(tp.init)
            else:
                ### DEBUG int() float() 
                init_value = tp.init
                #init_value = repr(tp.init)
            
            print >> self.stream, "%s = %s # Variable %s" % (tp.name,
                                             init_value,
                                             self.type_name(tp.typ, False))
        #
        self.names.add(tp.name)
        #try:
        #    value = self.initialize(tp.typ, tp.init)
        #except (TypeError, ValueError, SyntaxError, NameError), detail:
        #    log.error("Could not init %s %s %s"% (tp.name, tp.init, detail))
        #    import code
        #    code.interact(local=locals())
        #    return
        #import code
        #code.interact(local=locals())

    _enumvalues = 0
    def EnumValue(self, tp):
        # FIXME should be in parser
        value = int(tp.value)
        print >> self.stream, \
              "%s = %d" % (tp.name, value)
        self.names.add(tp.name)
        self._enumvalues += 1

    _enumtypes = 0
    def Enumeration(self, tp):
        self._enumtypes += 1
        if self.generate_comments:
            self.print_comment(tp)
        print >> self.stream
        if tp.name:
            print >> self.stream, "# values for enumeration '%s'" % tp.name
        else:
            print >> self.stream, "# values for unnamed enumeration"
        # Some enumerations have the same name for the enum type
        # and an enum value.  Excel's XlDisplayShapes is such an example.
        # Since we don't have separate namespaces for the type and the values,
        # we generate the TYPE last, overwriting the value. XXX
        for item in tp.values:
            self.generate(item)
        if tp.name:
            print >> self.stream, "%s = c_int # enum" % tp.name
            self.names.add(tp.name)


    _structures = 0
    def Structure(self, struct):
        self._structures += 1
        depends = []
        if struct.members is None:
            log.error('Error while parsing members for: %s'%(struct.name))
            return
        # look in bases class for dependencies
        # FIXME

        # checks members dependencies in bases
        for b in struct.bases:
            depends.extend([m.type for m in b.members 
                if m.type not in self.done and 
                          not isinstance(m.type, typedesc.FundamentalType)])
        # checks members dependencies
        depends.extend([m.type for m in struct.members 
                            if m.type not in self.done and 
                            not isinstance(m.type, typedesc.FundamentalType)])
        if len(depends) > 0:
            self.generate(struct.get_head())
            self.generate(struct.get_body())
        else:
            self.generate(struct.get_head(), True)
            self.generate(struct.get_body(), True)
        return

    Union = Structure

    def StructureHead(self, head, inline=False):
        for struct in head.struct.bases:
            self.generate(struct.get_head())
            # add dependencies
            self.more.add(struct)
        basenames = [self.type_name(b) for b in head.struct.bases]
        if basenames:
            ### method_names = [m.name for m in head.struct.members if type(m) is typedesc.Method]
            print >> self.stream, "class %s(%s):" % (head.struct.name, ", ".join(basenames))
        else:
            ### methods = [m for m in head.struct.members if type(m) is typedesc.Method]
            if type(head.struct) == typedesc.Structure:
                print >> self.stream, "class %s(Structure):" % head.struct.name
            elif type(head.struct) == typedesc.Union:
                print >> self.stream, "class %s(Union):" % head.struct.name
        if not inline:
            print >> self.stream, "    pass\n"
        # special empty struct
        if inline and not head.struct.members:
            print >> self.stream, "    pass\n"
        self.names.add(head.struct.name)


    def StructureBody(self, body, inline=False):
        fields = []
        methods = []
        for m in body.struct.members:
            if type(m) is typedesc.Field:
                fields.append(m)
                if type(m.type) is typedesc.Typedef:
                    self.generate(get_real_type(m.type))
                self.generate(m.type)
            elif type(m) is typedesc.Method:
                methods.append(m)
                self.generate(m.returns)
                self.generate_all(m.iterArgTypes())
            elif type(m) is typedesc.Ignored:
                pass
        # handled inline Vs dependent
        if not inline:
            prefix = "%s."%(body.struct.name)
        else:
            prefix = "    "
        if methods:
            # XXX we have parsed the COM interface methods but should
            # we emit any code for them?
            pass
        # LXJ: we pack all the time, because clang gives a precise field offset 
        # per target architecture. No need to defer to ctypes logic for that.
        if fields:
            print >> self.stream, "%s_pack_ = True # source:%s" % (
                        prefix, body.struct.packed)

        if body.struct.bases:
            if len(body.struct.bases) == 1: # its a Struct or a simple Class
              self.generate(body.struct.bases[0].get_body(), inline)
            else: # we have a multi-parent inheritance
              for b in body.struct.bases:
                self.generate(b.get_body(), inline)              
        # field definition normally span several lines.
        # Before we generate them, we need to 'import' everything they need.
        # So, call type_name for each field once,
        for f in fields:
            self.type_name(f.type)

        # unnamed fields get autogenerated names "_0", "_1", "_2", "_3", ...
        unnamed_fields = {}
        for f in fields:
            # _anonymous_ fields are fields of type Structure or Union,
            # that have no name.
            if not f.name and isinstance(f.type, (typedesc.Structure, typedesc.Union)):
                unnamed_fields[f] = "_%d" % len(unnamed_fields)
        if unnamed_fields:
            print >> self.stream, "%s_anonymous_ = %r" % \
                  (prefix, unnamed_fields.values())
        if len(fields) > 0:
            print >> self.stream, "%s_fields_ = [" %(prefix)

            if self.generate_locations and body.struct.location:
                print >> self.stream, "    # %s %s" % body.struct.location
            index = 0
            for f in fields:
                fieldname = unnamed_fields.get(f, f.name)
                type_name = self.type_name(f.type)
                if type_name.startswith("__"):
                    self.enable_pythonic_types()
                    type_name = "_p_type('%s')"%type_name
                if f.is_bitfield is False:
                    print >> self.stream, "    ('%s', %s)," % \
                     (fieldname, type_name)
                else:
                    # FIXME: Python bitfield is int32 only.
                    from clang.cindex import TypeKind                
                    print >> self.stream, "    ('%s', %s, %s)," % \
                        (fieldname, self.parser.get_ctypes_name(TypeKind.LONG), 
                        f.bits ) # self.type_name(f.type), f.bits)
            if inline:
                print >> self.stream, prefix,
            print >> self.stream, "]\n"
        
        # disable size checks because they are not portable across
        # platforms:
##        # generate assert statements for size and alignment
##        if body.struct.size and body.struct.name not in dont_assert_size:
##            size = body.struct.size // 8
##            print >> self.stream, "assert sizeof(%s) == %s, sizeof(%s)" % \
##                  (body.struct.name, size, body.struct.name)
##            align = body.struct.align // 8
##            print >> self.stream, "assert alignment(%s) == %s, alignment(%s)" % \
##                  (body.struct.name, align, body.struct.name)





    def find_dllname(self, func):
        if hasattr(func, "dllname"):
            return func.dllname
        name = func.name
        for dll in self.searched_dlls:
            try:
                getattr(dll, name)
            except AttributeError:
                pass
            else:
                return dll._name
##        if self.verbose:
        # warnings.warn, maybe?
##        print >> sys.stderr, "function %s not found in any dll" % name
        return None

    _c_libraries = None
    def need_CLibraries(self):
        # Create a '_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._c_libraries is None:
            self._c_libraries = {}
            print >> self.imports, "_libraries = {}"

    _stdcall_libraries = None
    def need_WinLibraries(self):
        # Create a '_stdcall_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._stdcall_libraries is None:
            self._stdcall_libraries = {}
            print >> self.imports, "_stdcall_libraries = {}"

    def get_sharedlib(self, dllname, cc):
        if cc == "stdcall":
            self.need_WinLibraries()
            if not dllname in self._stdcall_libraries:
                print >> self.imports, "_stdcall_libraries[%r] = WinDLL(%r)" % (dllname, dllname)
                self._stdcall_libraries[dllname] = None
            return "_stdcall_libraries[%r]" % dllname
        self.need_CLibraries()
        if self.preloaded_dlls != []:
          global_flag = ", mode=RTLD_GLOBAL"
        else:
          global_flag = ""
        if not dllname in self._c_libraries:
            print >> self.imports, "_libraries[%r] = CDLL(%r%s)" % (dllname, dllname, global_flag)
            self._c_libraries[dllname] = None
        return "_libraries[%r]" % dllname

    _STRING_defined = False
    def need_STRING(self):
        if self._STRING_defined:
            return
        print >> self.imports, "STRING = c_char_p"
        self._STRING_defined = True

    _WSTRING_defined = False
    def need_WSTRING(self):
        if self._WSTRING_defined:
            return
        print >> self.imports, "WSTRING = c_wchar_p"
        self._WSTRING_defined = True

    _functiontypes = 0
    _notfound_functiontypes = 0
    def Function(self, func):
        dllname = self.find_dllname(func)
        if dllname:
            if self.generate_comments:
                self.print_comment(func)
            self.generate(func.returns)
            self.generate_all(func.iterArgTypes())
            args = [self.type_name(a) for a in func.iterArgTypes()]
            if "__stdcall__" in func.attributes:
                cc = "stdcall"
            else:
                cc = "cdecl"

            libname = self.get_sharedlib(dllname, cc)

            argnames = [a or "p%d" % (i+1) for i, a in enumerate(func.iterArgNames())]

            if self.generate_locations and func.location:
                print >> self.stream, "# %s %s" % func.location
            print >> self.stream, "%s = %s.%s" % (func.name, libname, func.name)
            print >> self.stream, "%s.restype = %s" % (func.name, self.type_name(func.returns))
            if self.generate_comments:
                print >> self.stream, "# %s(%s)" % (func.name, ", ".join(argnames))
            print >> self.stream, "%s.argtypes = [%s]" % (func.name, ", ".join(args))
            
            if self.generate_docstrings:
                def typeString(typ):
                    if hasattr(typ, 'name'):
                        return typ.name
                    elif hasattr(typ, 'typ') and type(typ) == typedesc.PointerType:
                        return typeString(typ.typ) + " *"
                    else:
                        return "unknown"
                argsAndTypes = zip([typeString(t) for t in func.iterArgTypes()], argnames)
                print >> self.stream, """%(funcname)s.__doc__ = \\
    \"\"\"%(ret)s %(funcname)s(%(args)s)
    %(file)s:%(line)s\"\"\"""" % \
                    {'funcname': func.name, 
                    'args': ", ".join(["%s %s" % i for i in argsAndTypes]),
                    'file': func.location[0],
                    'line': func.location[1],
                    'ret': typeString(func.returns),
                    }

            self.names.add(func.name)
            self._functiontypes += 1
        else:
            self._notfound_functiontypes += 1

    def FundamentalType(self, item):
        pass # we should check if this is known somewhere
##        name = ctypes_names[item.name]
##        if name !=  "None":
##            print >> self.stream, "from ctypes import %s" % name
##        self.done.add(item)

    ########

    def generate(self, item, *args):
        """ """
        if item in self.done:
            return
        # verbose output with location.
        if self.generate_locations and item.location:
            print >> self.stream, "# %s:%d" % item.location
        if self.generate_comments:
            self.print_comment(item)
        log.debug("generate %s, %s"%(item, item.__dict__))
        '''
        #log.debug("generate %s, %s"%(item, item.__dict__))
        name=''
        if hasattr(item, 'name'):
            name = item.name
        elif isinstance( item, (str,)):
            log.error( '** got an string item %s'%( item ) )
            code.interact(local=locals())
            raise TypeError('Item should not be a string %s'%(item))
        log.debug('generate: %s( %s )'%( type(item).__name__, name))
        if name in self.known_symbols:
            log.debug('item is in known_symbols %s'% name )
            mod = self.known_symbols[name]
            print >> self.imports, "from %s import %s" % (mod, name)
            self.done.add(item)
            if isinstance(item, typedesc.Structure):
                self.done.add(item.get_head())
                self.done.add(item.get_body())
            return
        '''
        # to avoid infinite recursion, we have to mark it as done
        # before actually generating the code.
        self.done.add(item)
        # go to specific treatment
        mth = getattr(self, type(item).__name__)
        #code.interact(local=locals())
        mth(item, *args)

    def print_comment(self, item):
        if item.comment is None:
            return
        for l in textwrap.wrap(item.comment, 78):
            print >> self.stream, "# %s" % (l)

    def generate_all(self, items):
        for item in items:
            self.generate(item)

    def cmpitems(a, b):
        loc_a = getattr(a, "location", None)
        loc_b = getattr(b, "location", None)
        if loc_a is None: return -1
        if loc_b is None: return 1
        return cmp(loc_a[0],loc_b[0]) or cmp(int(loc_a[1]),int(loc_b[1]))
    cmpitems = staticmethod(cmpitems)

    def generate_items(self, items):
        items = set(items)
        loops = 0
        while items:
            loops += 1
            self.more = set()
            self.generate_all(sorted(items, self.cmpitems))

            items |= self.more
            items -= self.done
        return loops

    def generate_headers(self, parser):
        # fix parser in self for later use
        self.parser = parser 
        import clang
        from clang.cindex import TypeKind
        word_size = str(parser.get_ctypes_size(TypeKind.POINTER)/8)
        # assuming a LONG also has the same sizeof than a pointer. 
        word_type = parser.get_ctypes_name(TypeKind.ULONG)
        word_char =  getattr(ctypes,word_type)._type_
        long_double_size = str(parser.get_ctypes_size(TypeKind.LONGDOUBLE)/8)
        import pkgutil
        headers = pkgutil.get_data('ctypeslib','data/headers.tpl')
        headers = headers.replace('__FLAGS__', str(parser.flags))
        headers = headers.replace('__POINTER_SIZE__', word_size)
        headers = headers.replace('__REPLACEMENT_TYPE__' , word_type)
        headers = headers.replace('__REPLACEMENT_TYPE_CHAR__', word_char)
        headers = headers.replace('__LONG_DOUBLE_SIZE__', long_double_size)

        print >> self.imports, headers
        pass

    def generate_code(self, items):
        print >> self.imports, "\n".join(["CDLL('%s', RTLD_GLOBAL)" % preloaded_dll
                                          for preloaded_dll
                                          in  self.preloaded_dlls])
        loops = self.generate_items(items)
        
        self.output.write(self.imports.getvalue())
        self.output.write("\n\n")
        #code.interact(local=locals())
        self.output.write(self.stream.getvalue())

        text = "__all__ = [%s]" % ", ".join([repr(str(n)) for n in self.names])

        wrapper = textwrap.TextWrapper(break_long_words=False,
                                       subsequent_indent="           ")
        for line in wrapper.wrap(text):
            print >> self.output, line

        return loops

    def print_stats(self, stream):
        total = self._structures + self._functiontypes + self._enumtypes + self._typedefs +\
                self._pointertypes + self._arraytypes
        print >> stream, "###########################"
        print >> stream, "# Symbols defined:"
        print >> stream, "#"
        print >> stream, "# Variables:          %5d" % self._variables
        print >> stream, "# Struct/Unions:      %5d" % self._structures
        print >> stream, "# Functions:          %5d" % self._functiontypes
        print >> stream, "# Enums:              %5d" % self._enumtypes
        print >> stream, "# Enum values:        %5d" % self._enumvalues
        print >> stream, "# Typedefs:           %5d" % self._typedefs
        print >> stream, "# Pointertypes:       %5d" % self._pointertypes
        print >> stream, "# Arraytypes:         %5d" % self._arraytypes
        print >> stream, "# unknown functions:  %5d" % self._notfound_functiontypes
        print >> stream, "# unknown variables:  %5d" % self._notfound_variables
        print >> stream, "#"
        print >> stream, "# Total symbols: %5d" % total
        print >> stream, "###########################"

################################################################

def generate_code(srcfiles,
                  outfile,
                  expressions=None,
                  symbols=None,
                  verbose=False,
                  generate_comments=False,
                  known_symbols=None,
                  searched_dlls=None,
                  types=None,
                  preloaded_dlls=[],
                  generate_docstrings=False,
                  generate_locations=False,
                  flags=[]
                  ): 

    # expressions is a sequence of compiled regular expressions,
    # symbols is a sequence of names
    parser = clangparser.Clang_Parser(flags)
    # if macros are not needed, use a faster TranslationUnit
    if typedesc.Macro in types:
        parser.activate_macros_parsing()
    if generate_comments is True:
        parser.activate_comment_parsing()
    #
    items = []
    for srcfile in srcfiles:
        
        with open(srcfile):
            pass
        parser.parse(srcfile)
        items += parser.get_result()
    log.debug('Input was parsed')

    #code.interact(local=locals())

    # filter symbols to generate
    todo = []

    if types:
        items = [i for i in items if isinstance(i, types)]
    
    if symbols:
        syms = set(symbols)
        for i in items:
            if i.name in syms:
                todo.append(i)
                syms.remove(i.name)

        if syms:
           log.warning( "symbols not found %s"%( [str(x) for x in list(syms)]))

    if expressions:
        for i in items:
            for s in expressions:
                if i.name is None:
                    continue
                match = s.match(i.name)
                # we only want complete matches
                if match and match.group() == i.name:
                    todo.append(i)
                    break
    if symbols or expressions:
        items = todo

    ################
    gen = Generator(outfile,
                    generate_locations=generate_locations,
                    generate_comments=generate_comments,
                    generate_docstrings=generate_docstrings,
                    known_symbols=known_symbols,
                    searched_dlls=searched_dlls,
                    preloaded_dlls=preloaded_dlls)

    # change ctypes for arch dependent definition
    gen.generate_headers(parser)
    # make the structures
    loops = gen.generate_code(items)
    if verbose:
        gen.print_stats(sys.stderr)
        print >> sys.stderr, "needed %d loop(s)" % loops

