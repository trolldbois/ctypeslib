'''Create ctypes wrapper code for abstract type descriptions.
Type descriptions are collections of typedesc instances.
'''

from __future__ import print_function
from __future__ import unicode_literals
from functools import cmp_to_key
import textwrap
from io import StringIO

import sys

from ctypeslib.codegen import clangparser
from ctypeslib.codegen import typedesc

import logging
log = logging.getLogger('codegen')

class Generator(object):

    def __init__(self, output,
                 generate_comments=False,
                 known_symbols=None,
                 searched_dlls=None,
                 preloaded_dlls=None,
                 generate_docstrings=False,
                 generate_locations=False):
        self.output = output
        self.stream = StringIO()
        self.imports = StringIO()
        self.generate_locations = generate_locations
        self.generate_comments = generate_comments
        self.generate_docstrings = generate_docstrings
        self.known_symbols = known_symbols or {}
        self.preloaded_dlls = preloaded_dlls or []
        if searched_dlls is None:
            self.searched_dlls = []
        else:
            self.searched_dlls = searched_dlls

        self.done = set()  # type descriptions that have been generated
        self.names = set()  # names that have been generated
        self.macros = 0

    # pylint: disable=method-hidden
    def enable_fundamental_type_wrappers(self):
        """
        If a type is a int128, a long_double_t or a void, some placeholders need
        to be in the generated code to be valid.
        """
        # 2015-01 reactivating header templates
        #log.warning('enable_fundamental_type_wrappers deprecated - replaced by generate_headers')
        # return # FIXME ignore
        self.enable_fundamental_type_wrappers = lambda: True
        import pkgutil
        headers = pkgutil.get_data(
            'ctypeslib',
            'data/fundamental_type_name.tpl')
        from clang.cindex import TypeKind
        size = str(self.parser.get_ctypes_size(TypeKind.LONGDOUBLE) / 8)
        headers = headers.replace('__LONG_DOUBLE_SIZE__', size)
        print(headers, file=self.imports)
        return

    def enable_pointer_type(self):
        """
        If a type is a pointer, a platform-independent POINTER_T type needs
        to be in the generated code.
        """
        # 2015-01 reactivating header templates
        #log.warning('enable_pointer_type deprecated - replaced by generate_headers')
        # return # FIXME ignore
        self.enable_pointer_type = lambda: True
        import pkgutil
        headers = pkgutil.get_data('ctypeslib', 'data/pointer_type.tpl')
        import ctypes
        from clang.cindex import TypeKind
        # assuming a LONG also has the same sizeof than a pointer.
        word_size = self.parser.get_ctypes_size(TypeKind.POINTER) / 8
        word_type = self.parser.get_ctypes_name(TypeKind.ULONG)
        # pylint: disable=protected-access
        word_char = getattr(ctypes, word_type)._type_
        # replacing template values
        headers = headers.replace('__POINTER_SIZE__', str(word_size))
        headers = headers.replace('__REPLACEMENT_TYPE__', word_type)
        headers = headers.replace('__REPLACEMENT_TYPE_CHAR__', word_char)
        print(headers, file=self.imports)
        return

    def generate_headers(self, parser):
        # fix parser in self for later use
        self.parser = parser
        import pkgutil
        headers = pkgutil.get_data('ctypeslib', 'data/headers.tpl')
        from clang.cindex import TypeKind
        # get sizes from clang library
        word_size = self.parser.get_ctypes_size(TypeKind.LONG) / 8
        pointer_size = self.parser.get_ctypes_size(TypeKind.POINTER) / 8
        longdouble_size = self.parser.get_ctypes_size(TypeKind.LONGDOUBLE) / 8
        # replacing template values
        headers = headers.replace('__FLAGS__', str(self.parser.flags))
        headers = headers.replace('__WORD_SIZE__', str(word_size))
        headers = headers.replace('__POINTER_SIZE__', str(pointer_size))
        headers = headers.replace('__LONGDOUBLE_SIZE__', str(longdouble_size))
        print(headers, file=self.imports)
        return

    def type_name(self, t, generate=True):
        """
        Returns a string containing an expression that can be used to
        refer to the type. Assumes the 'from ctypes import *'
        namespace is available.
        """
        # no Test case for these
        # elif isinstance(t, typedesc.Argument):
        # elif isinstance(t, typedesc.CvQualifiedType):
        # elif isinstance(t, typedesc.Variable):
        #   return "%s" % self.type_name(t.typ, generate)
        # elif isinstance(t, typedesc.Enumeration):
        #   return t.name

        if isinstance(t, typedesc.FundamentalType):
            return self.FundamentalType(t)
        elif isinstance(t, typedesc.ArrayType):
            return "%s * %s" % (self.type_name(t.typ, generate), t.size)
        elif isinstance(t, typedesc.PointerType):
            self.enable_pointer_type()
            return "POINTER_T(%s)" % (self.type_name(t.typ, generate))
        elif isinstance(t, typedesc.FunctionType):
            args = [
                self.type_name(
                    x,
                    generate) for x in [
                    t.returns] +
                list(
                    t.iterArgTypes())]
            if "__stdcall__" in t.attributes:
                return "ctypes.WINFUNCTYPE(%s)" % ", ".join(args)
            else:
                return "ctypes.CFUNCTYPE(%s)" % ", ".join(args)
        # elif isinstance(t, typedesc.Structure):
        # elif isinstance(t, typedesc.Typedef):
        # elif isinstance(t, typedesc.Union):
        return t.name
        # All typedesc typedefs should be handled
        #raise TypeError('This typedesc should be handled %s'%(t))

    ################################################################

    _aliases = 0

    def Alias(self, alias):
        """Handles Aliases. No test cases yet"""
        # FIXME
        if self.generate_comments:
            self.print_comment(alias)
        print("%s = %s # alias" % (alias.name, alias.alias), file=self.stream)
        self._aliases += 1
        return

    _macros = 0

    def Macro(self, macro):
        """Handles macro. No test cases else that #defines."""
        if macro.location is None:
            log.info('Ignoring %s with no location', macro.name)
            return
        if self.generate_locations:
            print("# %s:%s" % (macro.location), file=self.stream)
        if self.generate_comments:
            self.print_comment(macro)
        print("%s = %s # macro" % (macro.name, macro.body), file=self.stream)
        self.macros += 1
        return
        # We don't know if we can generate valid, error free Python
        # code. All we can do is to try to compile the code.  If the
        # compile fails, we know it cannot work, so we comment out the
        # generated code; the user may be able to fix it manually.
        #
        # If the compilation succeeds, it may still fail at runtime
        # when the macro is called.
        # mcode = "def %s%s: return %s # macro" % (macro.name, macro.args,
        # macro.body)
        # try:
        #    compile(mcode, "<string>", "exec")
        # except SyntaxError:
        #    print >> self.stream, "#", mcode
        # else:
        #    print >> self.stream, mcode, '# Macro'
        #    self.names.add(macro.name)

    _typedefs = 0

    def Typedef(self, tp):
        if self.generate_comments:
            self.print_comment(tp)
        sized_types = {
            "uint8_t": "c_uint8",
            "uint16_t": "c_uint16",
            "uint32_t": "c_uint32",
            "uint64_t": "c_uint64",
            "int8_t": "c_int8",
            "int16_t": "c_int16",
            "int32_t": "c_int32",
            "int64_t": "c_int64",
        }
        name = self.type_name(tp)  # tp.name
        if (isinstance(tp.typ, typedesc.FundamentalType) and
                tp.name in sized_types):
            print("%s = ctypes.%s" % \
                (name, sized_types[tp.name]), file=self.stream)
            self.names.add(tp.name)
            return
        if tp.typ not in self.done:
            # generate only declaration code for records ?
            # if type(tp.typ) in (typedesc.Structure, typedesc.Union):
            #    self._generate(tp.typ.get_head())
            #    self.more.add(tp.typ)
            # else:
            #    self._generate(tp.typ)
            self._generate(tp.typ)
        # generate actual typedef code.
        if tp.name != self.type_name(tp.typ):
            print("%s = %s" % \
                (name, self.type_name(tp.typ)), file=self.stream)
        self.names.add(tp.name)
        self._typedefs += 1
        return

    def _get_real_type(self, tp):
        # FIXME, kinda useless really.
        if isinstance(tp, typedesc.Typedef):
            if isinstance(tp.typ, typedesc.Typedef):
                raise TypeError('Nested loop in Typedef %s' % (tp.name))
            return self._get_real_type(tp.typ)
        elif isinstance(tp, typedesc.CvQualifiedType):
            return self._get_real_type(tp.typ)
        return tp

    _arraytypes = 0

    def ArrayType(self, tp):
        self._generate(self._get_real_type(tp.typ))
        self._generate(tp.typ)
        self._arraytypes += 1
        return

    _functiontypes = 0

    def FunctionType(self, tp):
        self._generate(tp.returns)
        self.generate_all(tp.arguments)
        # print >> self.stream, "%s = %s # Functiontype " % (
        # self.type_name(tp), [self.type_name(a) for a in tp.arguments])
        self._functiontypes += 1
        return

    def Argument(self, tp):
        self._generate(tp.typ)

    _pointertypes = 0

    def PointerType(self, tp):
        # print 'generate', tp.typ
        if isinstance(tp.typ, typedesc.PointerType):
            self._generate(tp.typ)
        elif type(tp.typ) in (typedesc.Union, typedesc.Structure):
            self._generate(tp.typ.get_head())
            self.more.add(tp.typ)
        elif isinstance(tp.typ, typedesc.Typedef):
            self._generate(tp.typ)
        else:
            self._generate(tp.typ)
        self._pointertypes += 1
        return

    def CvQualifiedType(self, tp):
        self._generate(tp.typ)
        return

    _variables = 0
    _notfound_variables = 0

    def Variable(self, tp):
        self._variables += 1
        if self.generate_comments:
            self.print_comment(tp)
        dllname = self.find_dllname(tp)
        if dllname:
            self._generate(tp.typ)
            # calling convention does not matter for in_dll...
            libname = self.get_sharedlib(dllname, "cdecl")
            print("%s = (%s).in_dll(%s, '%s')" % (tp.name,
                                                self.type_name(tp.typ),
                                                libname,
                                                tp.name), file=self.stream)
            self.names.add(tp.name)
            # wtypes.h contains IID_IProcessInitControl, for example
            return

        # Hm.  The variable MAY be a #define'd symbol that we have
        # artifically created, or it may be an exported variable that
        # is not in the libraries that we search.  Anyway, if it has
        # no tp.init value we can't generate code for it anyway, so we
        # drop it.
        # if tp.init is None:
        #    self._notfound_variables += 1
        #    return
        # el
        if isinstance(tp.init, typedesc.FunctionType):
            print("%s = %s # args: %s" % (tp.name,
                                                          self.type_name(
                                                              tp.init),
                                                          [x for x in tp.typ.iterArgNames()]), file=self.stream)
        else:
            init_value = tp.init
            if isinstance(tp.typ, typedesc.PointerType) or \
                    isinstance(tp.typ, typedesc.ArrayType):
                if (isinstance(tp.typ.typ, typedesc.FundamentalType) and
                        (tp.typ.typ.name == "c_char" or tp.typ.typ.name == "c_wchar")):
                    # string
                    # FIXME a char * is not a python string.
                    # we should output a cstring() construct.
                    init_value = repr(tp.init)
                elif (isinstance(tp.typ.typ, typedesc.FundamentalType) and
                      ('int' in tp.typ.typ.name) or 'long' in tp.typ.typ.name):
                    # array of number
                    # CARE: size of elements must match size of array
                    init_value = repr(tp.init)
                    # we do NOT want Variable to be described as ctypes object
                    # when we can have a python abstraction for them.
                    #init_value_type = self.type_name(tp.typ, False)
                    #init_value = ','.join([str(x) for x in tp.init])
                    #init_value = "(%s)(%s)"%(init_value_type,init_value)
                else:
                    init_value = self.type_name(tp.typ, False)
            elif (isinstance(tp.typ, typedesc.FundamentalType) and
                  (tp.typ.name == "c_char" or tp.typ.name == "c_wchar")):
                # char
                init_value = repr(tp.init)
            elif isinstance(tp.typ, typedesc.Structure):
                init_value = self.type_name(tp.typ, False)
            else:
                # DEBUG int() float()
                init_value = tp.init
                # print init_value
                #init_value = repr(tp.init)
            # Partial --
            # now we do want to have FundamentalType variable use the actual
            # type, and not be a python object
            # if init_value is None:
            #    init_value = ''; # use default ctypes object constructor
            #init_value = "%s(%s)"%(self.type_name(tp.typ, False), init_value)
            #
            # print it out
            print("%s = %s # Variable %s" % (tp.name,
                                                             init_value,
                                                             self.type_name(tp.typ, False)), file=self.stream)
        #
        self.names.add(tp.name)
        # try:
        #    value = self.initialize(tp.typ, tp.init)
        # except (TypeError, ValueError, SyntaxError, NameError), detail:
        #    log.error("Could not init %s %s %s"% (tp.name, tp.init, detail))
        #    import code
        #    code.interact(local=locals())
        #    return
        #import code
        # code.interact(local=locals())

    _enumvalues = 0

    def EnumValue(self, tp):
        # FIXME should be in parser
        value = int(tp.value)
        print("%s = %d" % (tp.name, value), file=self.stream)
        self.names.add(tp.name)
        self._enumvalues += 1
        return

    _enumtypes = 0

    def Enumeration(self, tp):
        if self.generate_comments:
            self.print_comment(tp)
        print(u'', file=self.stream)
        if tp.name:
            print("# values for enumeration '%s'" % tp.name, file=self.stream)
        else:
            print("# values for unnamed enumeration", file=self.stream)
        # Some enumerations have the same name for the enum type
        # and an enum value.  Excel's XlDisplayShapes is such an example.
        # Since we don't have separate namespaces for the type and the values,
        # we generate the TYPE last, overwriting the value. XXX
        for item in tp.values:
            self._generate(item)
        if tp.name:
            print("%s = ctypes.c_int # enum" % tp.name, file=self.stream)
            self.names.add(tp.name)
        self._enumtypes += 1
        return

    def get_undeclared_type(self, item):
        """
        Checks if a typed has already been declared in the python output
        or is a builtin python type.
        """
        if item in self.done:
            return None
        if isinstance(item, typedesc.FundamentalType):
            return None
        if isinstance(item, typedesc.PointerType):
            return self.get_undeclared_type(item.typ)
        if isinstance(item, typedesc.ArrayType):
            return self.get_undeclared_type(item.typ)
        # else its an undeclared structure.
        return item

    _structures = 0

    def Structure(self, struct):
        self._structures += 1
        depends = set()
        # We only print a empty struct.
        if struct.members is None:
            log.info('No members for: %s', struct.name)
            self._generate(struct.get_head(), False)
            return
        # look in bases class for dependencies
        # FIXME - need a real dependency graph maker
        # remove myself, just in case.
        self.done.remove(struct)
        # checks members dependencies in bases
        for b in struct.bases:
            depends.update([self.get_undeclared_type(m.type)
                            for m in b.members])
        # checks members dependencies
        depends.update([self.get_undeclared_type(m.type)
                        for m in struct.members])
        self.done.add(struct)
        depends.discard(None)
        if len(depends) > 0:
            log.debug('Generate %s DEPENDS %s', struct.name, depends)
            self._generate(struct.get_head(), False)
            # generate dependencies
            for dep in depends:
                self._generate(dep)
            self._generate(struct.get_body(), False)
        else:
            log.debug('No depends for %s', struct.name)
            if struct.name in self.names:
                # headers already produced
                self._generate(struct.get_body(), False)
            else:
                self._generate(struct.get_head(), True)
                self._generate(struct.get_body(), True)
        return

    Union = Structure

    def StructureHead(self, head, inline=False):
        log.debug('Head start for %s inline:%s', head.name, inline)
        for struct in head.struct.bases:
            self._generate(struct.get_head())
            # add dependencies
            self.more.add(struct)
        basenames = [self.type_name(b) for b in head.struct.bases]
        if basenames:
            ### method_names = [m.name for m in head.struct.members if type(m) is typedesc.Method]
            print("class %s(%s):" % (
                head.struct.name, ", ".join(basenames)), file=self.stream)
        else:
            ### methods = [m for m in head.struct.members if type(m) is typedesc.Method]
            if isinstance(head.struct, typedesc.Structure):
                print("class %s(ctypes.Structure):" % head.struct.name, file=self.stream)
            elif isinstance(head.struct, typedesc.Union):
                print("class %s(ctypes.Union):" % head.struct.name, file=self.stream)
        if not inline:
            print("    pass\n", file=self.stream)
        # special empty struct
        if inline and not head.struct.members:
            print("    pass\n", file=self.stream)
        self.names.add(head.struct.name)
        log.debug('Head finished for %s', head.name)

    def StructureBody(self, body, inline=False):
        log.debug('Body start for %s', body.name)
        fields = []
        methods = []
        for m in body.struct.members:
            if isinstance(m, typedesc.Field):
                fields.append(m)
                # if type(m.type) is typedesc.Typedef:
                #    self._generate(get_real_type(m.type))
                # self._generate(m.type)
            elif isinstance(m, typedesc.Method):
                methods.append(m)
                # self._generate(m.returns)
                # self.generate_all(m.iterArgTypes())
            elif isinstance(m, typedesc.Ignored):
                pass
        # handled inline Vs dependent
        log.debug(
            "body inline:%s for structure %s",
            inline, body.struct.name)
        if not inline:
            prefix = "%s." % (body.struct.name)
        else:
            prefix = "    "
        if methods:
            # XXX we have parsed the COM interface methods but should
            # we emit any code for them?
            pass
        # LXJ: we pack all the time, because clang gives a precise field offset
        # per target architecture. No need to defer to ctypes logic for that.
        if fields:
            print("%s_pack_ = True # source:%s" % (
                prefix, body.struct.packed), file=self.stream)

        if body.struct.bases:
            if len(body.struct.bases) == 1:  # its a Struct or a simple Class
                self._generate(body.struct.bases[0].get_body(), inline)
            else:  # we have a multi-parent inheritance
                for b in body.struct.bases:
                    self._generate(b.get_body(), inline)
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
            if not f.name and isinstance(
                    f.type, (typedesc.Structure, typedesc.Union)):
                unnamed_fields[f] = "_%d" % len(unnamed_fields)
        if unnamed_fields:
            print("%s_anonymous_ = %r" % \
                (prefix, unnamed_fields.values()), file=self.stream)
        if len(fields) > 0:
            print("%s_fields_ = [" % (prefix), file=self.stream)

            if self.generate_locations and body.struct.location:
                print("    # %s %s" % body.struct.location, file=self.stream)
            index = 0
            for f in fields:
                fieldname = unnamed_fields.get(f, f.name)
                type_name = self.type_name(f.type)
                # handle "__" prefixed names by using a wrapper
                if type_name.startswith("__"):
                    type_name = "globals()['%s']" % type_name
                # a bitfield needs a triplet
                if f.is_bitfield is False:
                    print("    ('%s', %s)," % \
                        (fieldname, type_name), file=self.stream)
                else:
                    # FIXME: Python bitfield is int32 only.
                    #from clang.cindex import TypeKind
                    #print fieldname
                    #import code
                    #code.interact(local=locals())
                    print("    ('%s', %s, %s)," % \
                        (fieldname,
                         # self.parser.get_ctypes_name(TypeKind.LONG),
                         self.type_name(f.type),
                         f.bits), file=self.stream)
            if inline:
                print(prefix, end=' ', file=self.stream)
            print("]\n", file=self.stream)
        log.debug('Body finished for %s', body.name)
        return

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
                # pylint: disable=protected-access
                return dll._name
        return None

    _c_libraries = None

    def need_CLibraries(self):
        # Create a '_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._c_libraries is None:
            self._c_libraries = {}
            print("_libraries = {}", file=self.imports)
        return

    _stdcall_libraries = None

    def need_WinLibraries(self):
        # Create a '_stdcall_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._stdcall_libraries is None:
            self._stdcall_libraries = {}
            print("_stdcall_libraries = {}", file=self.imports)
        return

    def get_sharedlib(self, dllname, cc):
        if cc == "stdcall":
            self.need_WinLibraries()
            if dllname not in self._stdcall_libraries:
                print("_stdcall_libraries[%r] = ctypes.WinDLL(%r)" % (
                    dllname, dllname), file=self.imports)
                self._stdcall_libraries[dllname] = None
            return "_stdcall_libraries[%r]" % dllname
        self.need_CLibraries()
        if self.preloaded_dlls != []:
            global_flag = ", mode=ctypes.RTLD_GLOBAL"
        else:
            global_flag = ""
        if dllname not in self._c_libraries:
            print("_libraries[%r] = ctypes.CDLL(%r%s)" % (
                dllname, dllname, global_flag), file=self.imports)
            self._c_libraries[dllname] = None
        return "_libraries[%r]" % dllname

    _STRING_defined = False

    def need_STRING(self):
        if self._STRING_defined:
            return
        print("STRING = c_char_p", file=self.imports)
        self._STRING_defined = True
        return

    _WSTRING_defined = False

    def need_WSTRING(self):
        if self._WSTRING_defined:
            return
        print("WSTRING = c_wchar_p", file=self.imports)
        self._WSTRING_defined = True
        return

    _functiontypes = 0
    _notfound_functiontypes = 0

    def Function(self, func):
        dllname = self.find_dllname(func)
        if dllname:
            if self.generate_comments:
                self.print_comment(func)
            self._generate(func.returns)
            self.generate_all(func.iterArgTypes())
            args = [self.type_name(a) for a in func.iterArgTypes()]
            if "__stdcall__" in func.attributes:
                cc = "stdcall"
            else:
                cc = "cdecl"

            libname = self.get_sharedlib(dllname, cc)

            argnames = [
                a or "p%d" %
                (i +
                 1) for i,
                a in enumerate(
                    func.iterArgNames())]

            if self.generate_locations and func.location:
                print("# %s %s" % func.location, file=self.stream)
            print("%s = %s.%s" % (
                func.name, libname, func.name), file=self.stream)
            print("%s.restype = %s" % (
                func.name, self.type_name(func.returns)), file=self.stream)
            if self.generate_comments:
                print("# %s(%s)" % (
                    func.name, ", ".join(argnames)), file=self.stream)
            print("%s.argtypes = [%s]" % (
                func.name, ", ".join(args)), file=self.stream)

            if self.generate_docstrings:
                def typeString(typ):
                    if hasattr(typ, 'name'):
                        return typ.name
                    elif hasattr(typ, 'typ') and isinstance(typ, typedesc.PointerType):
                        return typeString(typ.typ) + " *"
                    else:
                        return "unknown"
                argsAndTypes = zip([typeString(t)
                                    for t in func.iterArgTypes()], argnames)
                print("""%(funcname)s.__doc__ = \\
    \"\"\"%(ret)s %(funcname)s(%(args)s)
    %(file)s:%(line)s\"\"\"""" % \
                    {'funcname': func.name,
                     'args': ", ".join(["%s %s" % i for i in argsAndTypes]),
                     'file': func.location[0],
                     'line': func.location[1],
                     'ret': typeString(func.returns),
                     }, file=self.stream)

            self.names.add(func.name)
            self._functiontypes += 1
        else:
            self._notfound_functiontypes += 1
        return

    def FundamentalType(self, _type):
        """Returns the proper ctypes class name for a fundamental type

        1) activates generation of appropriate headers for
        ## int128_t
        ## c_long_double_t
        2) return appropriate name for type
        """
        log.debug('HERE in FundamentalType for %s %s', _type, _type.name)
        if _type.name in ["None", "c_long_double_t", "c_uint128", "c_int128"]:
            self.enable_fundamental_type_wrappers()
            return _type.name
        return "ctypes.%s" % (_type.name)

    ########

    def _generate(self, item, *args):
        """ wraps execution of specific methods."""
        if item in self.done:
            return
        # verbose output with location.
        if self.generate_locations and item.location:
            print("# %s:%d" % item.location, file=self.stream)
        if self.generate_comments:
            self.print_comment(item)
        log.debug("generate %s, %s", item.__class__.__name__, item.name)
        #
        #log.debug('generate: %s( %s )', type(item).__name__, name)
        #if name in self.known_symbols:
        #    log.debug('item is in known_symbols %s'% name )
        #    mod = self.known_symbols[name]
        #    print >> self.imports, "from %s import %s" % (mod, name)
        #    self.done.add(item)
        #    if isinstance(item, typedesc.Structure):
        #        self.done.add(item.get_head())
        #        self.done.add(item.get_body())
        #    return
        #
        # to avoid infinite recursion, we have to mark it as done
        # before actually generating the code.
        self.done.add(item)
        # go to specific treatment
        mth = getattr(self, type(item).__name__)
        mth(item, *args)
        return

    def print_comment(self, item):
        if item.comment is None:
            return
        for l in textwrap.wrap(item.comment, 78):
            print("# %s" % (l), file=self.stream)
        return

    def generate_all(self, items):
        for item in items:
            self._generate(item)
        return

    def cmpitems(a, b):
        loc_a = getattr(a, "location", None)
        loc_b = getattr(b, "location", None)
        if loc_a is None:
            return -1
        if loc_b is None:
            return 1
        # FIXME: PY3 - can we do simpler ?
        _cmp = lambda x, y: (x > y) - (x < y)
        return _cmp(loc_a[0], loc_b[0]) or _cmp(int(loc_a[1]), int(loc_b[1]))
    cmpitems = staticmethod(cmpitems)

    def generate_items(self, items):
        items = set(items)
        loops = 0
        while items:
            loops += 1
            self.more = set()
            self.generate_all(sorted(items, key=cmp_to_key(self.cmpitems)))

            items |= self.more
            items -= self.done
        return loops

    def generate(self, parser, items):
        self.generate_headers(parser)
        self.generate_code(items)

    def generate_code(self, items):
        print("\n".join(["ctypes.CDLL('%s', ctypes.RTLD_GLOBAL)" % preloaded_dll
                                          for preloaded_dll
                                          in self.preloaded_dlls]), file=self.imports)
        loops = self.generate_items(items)

        self.output.write(self.imports.getvalue())
        self.output.write("\n\n")
        self.output.write(self.stream.getvalue())

        text = "__all__ = \\"
        # text Wrapper doesn't work for the first line in certain cases.
        print(text, file=self.output)
        # doesn't work for the first line in certain cases.
        wrapper = textwrap.TextWrapper(break_long_words=False, initial_indent="    ",
                                       subsequent_indent="    ")
        text = "[%s]" % ", ".join([repr(str(n)) for n in self.names])
        for line in wrapper.wrap(text):
            print(line, file=self.output)

        return loops

    def print_stats(self, stream):
        total = self._structures + self._functiontypes + self._enumtypes + self._typedefs +\
            self._pointertypes + self._arraytypes
        print("###########################", file=stream)
        print("# Symbols defined:", file=stream)
        print("#", file=stream)
        print("# Variables:          %5d" % self._variables, file=stream)
        print("# Struct/Unions:      %5d" % self._structures, file=stream)
        print("# Functions:          %5d" % self._functiontypes, file=stream)
        print("# Enums:              %5d" % self._enumtypes, file=stream)
        print("# Enum values:        %5d" % self._enumvalues, file=stream)
        print("# Typedefs:           %5d" % self._typedefs, file=stream)
        print("# Pointertypes:       %5d" % self._pointertypes, file=stream)
        print("# Arraytypes:         %5d" % self._arraytypes, file=stream)
        print("# unknown functions:  %5d" % self._notfound_functiontypes, file=stream)
        print("# unknown variables:  %5d" % self._notfound_variables, file=stream)
        print("#", file=stream)
        print("# Total symbols: %5d" % total, file=stream)
        print("###########################", file=stream)
        return

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
                  preloaded_dlls=None,
                  generate_docstrings=False,
                  generate_locations=False,
                  filter_location=False,
                  flags=None
                  ):

    # expressions is a sequence of compiled regular expressions,
    # symbols is a sequence of names
    parser = clangparser.Clang_Parser(flags or [])
    # if macros are not needed, use a faster TranslationUnit
    if typedesc.Macro in types:
        parser.activate_macros_parsing()
    if generate_comments is True:
        parser.activate_comment_parsing()

    if filter_location is True:
        parser.filter_location(srcfiles)

    #
    items = []
    for srcfile in srcfiles:
        # verifying that is really a file we can open
        with open(srcfile):
            pass
        parser.parse(srcfile)
        items += parser.get_result()
    log.debug('Input was parsed')
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
            log.warning("symbols not found %s",
                        [str(x) for x in list(syms)])

    if expressions:
        for s in expressions:
            log.debug("regexp: looking for %s",s.pattern)
            for i in items:
                log.debug("regexp: i.name is %s",i.name)
                if i.name is None:
                    continue
                match = s.match(i.name)
                # if we only want complete matches:
                if match and match.group() == i.name:
                    todo.append(i)
                    break
                # if we follow our own documentation,
                # allow regular expression match of any part of name:
                match = s.search(i.name)
                if match:
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

    # add some headers and ctypes import
    gen.generate_headers(parser)
    # make the structures
    loops = gen.generate_code(items)
    if verbose:
        gen.print_stats(sys.stderr)
        print("needed %d loop(s)" % loops, file=sys.stderr)
