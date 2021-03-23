"""Create ctypes wrapper code for abstract type descriptions.
Type descriptions are collections of typedesc instances.
"""

from __future__ import print_function
from __future__ import unicode_literals

import collections
import ctypes
import logging
import os
import pkgutil
import sys
import textwrap
from io import StringIO
from collections import defaultdict

from ctypeslib.codegen import cache
from ctypeslib.codegen import clangparser
from ctypeslib.codegen import typedesc
from ctypeslib.codegen import util
from ctypeslib.codegen.preprocess import (
    process_c_literals,
    process_macro_function,
    replace_builtins,
    replace_pointer_types,
)

log = logging.getLogger('codegen')


class GeneratorResult:
    def __init__(self):
        self._out = defaultdict(StringIO)

    def stream_names(self):
        return list(self._out.keys())

    def streams(self):
        for k, v in self._out.items():
            yield (k, v.getvalue())

    def get(self, name):
        return self._out[name].getvalue()

    def update(self, other):
        for k, v in other._out.items():
            self._out[k].write(v.getvalue())

    def write(self, name, data, end=None):
        if end is None:
            end = "\n"
        self._out[name].write(data)
        if end:
            self._out[name].write(end)


class Generator(object):

    def __init__(
        self,
        output,
        generate_comments=False,
        known_symbols=None,
        searched_dlls=None,
        preloaded_dlls=None,
        generate_docstrings=False,
        generate_locations=False,
        cross_arch=False,
    ):
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

        # we use collections.OrderedDict() to keep ordering
        self.done = collections.OrderedDict()  # type descriptions that have been generated
        self.names = list()  # names that have been generated
        self.more = collections.OrderedDict()
        self.macros = 0
        self.cross_arch_code_generation = cross_arch
        # what record dependency were generated
        self.head_generated = set()
        self.body_generated = set()

    # pylint: disable=method-hidden
    def enable_fundamental_type_wrappers(self):
        """
        If a type is a int128, a long_double_t or a void, some placeholders need
        to be in the generated code to be valid.
        """
        self.enable_fundamental_type_wrappers = lambda: True
        import pkgutil
        headers = pkgutil.get_data(
            "ctypeslib",
            "data/fundamental_type_name.tpl").decode()
        from ctypeslib.codegen.cindex import TypeKind
        size = str(self.parser.get_ctypes_size(TypeKind.LONGDOUBLE) // 8)
        headers = headers.replace("__LONG_DOUBLE_SIZE__", size)
        print(headers, file=self.imports)

    def enable_pointer_type(self):
        """
        If a type is a pointer, a platform-independent POINTER_T type needs
        to be in the generated code.
        """
        # only enable if cross arch mode is on
        if not self.cross_arch_code_generation:
            return "ctypes.POINTER"
        self.enable_pointer_type = lambda: "POINTER_T"
        import pkgutil
        headers = pkgutil.get_data("ctypeslib", "data/pointer_type.tpl").decode()
        import ctypes
        from ctypeslib.codegen.cindex import TypeKind
        # assuming a LONG also has the same sizeof than a pointer.
        word_size = self.parser.get_ctypes_size(TypeKind.POINTER) // 8
        word_type = self.parser.get_ctypes_name(TypeKind.ULONG)
        # pylint: disable=protected-access
        word_char = getattr(ctypes, word_type)._type_
        # replacing template values
        headers = headers.replace("__POINTER_SIZE__", str(word_size))
        headers = headers.replace("__REPLACEMENT_TYPE__", word_type)
        headers = headers.replace("__REPLACEMENT_TYPE_CHAR__", word_char)
        print(headers, file=self.imports)
        return "POINTER_T"

    def enable_structure_type(self):
        """
        If a structure type is used, declare our ctypes.Structure extension type
        """
        self.enable_structure_type = lambda: True
        headers = pkgutil.get_data("ctypeslib", "data/structure_type.tpl").decode()
        print(headers, file=self.imports)

    def enable_string_cast(self):
        """
        If a structure type is used, declare our ctypes.Structure extension type
        """
        self.enable_string_cast = lambda: True
        headers = pkgutil.get_data("ctypeslib", "data/string_cast.tpl").decode()
        headers = headers.replace("__POINTER_TYPE__", self.enable_pointer_type())
        print(headers, file=self.imports)

    def enable_macro_processing(self):
        """
        If a structure type is used, declare our ctypes.Structure extension type
        """
        self.enable_macro_processing = lambda: True
        if not self.parser.advanced_macro:
            return
        import pkgutil
        shared = pkgutil.get_data('ctypeslib', 'codegen/preprocess.py').decode()
        print(shared, file=self.imports)
        return

    def generate_headers(self, parser):
        # fix parser in self for later use
        self.parser = parser
        import pkgutil
        headers = pkgutil.get_data('ctypeslib', 'data/headers.tpl').decode()
        from ctypeslib.codegen.cindex import TypeKind
        # get sizes from clang library
        word_size = self.parser.get_ctypes_size(TypeKind.LONG) // 8
        pointer_size = self.parser.get_ctypes_size(TypeKind.POINTER) // 8
        longdouble_size = self.parser.get_ctypes_size(TypeKind.LONGDOUBLE) // 8
        # replacing template values
        headers = headers.replace("__FLAGS__", str(self.parser.flags))
        headers = headers.replace("__WORD_SIZE__", str(word_size))
        headers = headers.replace("__POINTER_SIZE__", str(pointer_size))
        headers = headers.replace("__LONGDOUBLE_SIZE__", str(longdouble_size))
        print(headers, file=self.imports)

    @cache.cached_pure_method()
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
            return self._get_fundamental_typename(t)
        elif isinstance(t, typedesc.ArrayType):
            return f"{self.type_name(t.typ, generate)} * {t.size}"
        elif isinstance(t, typedesc.PointerType) and isinstance(t.typ, typedesc.FunctionType):
            return self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.PointerType):
            pointer_class = self.enable_pointer_type()
            if t.typ.name in ["c_ubyte", "c_char"]:
                self.enable_string_cast()
            return f"{pointer_class}({self.type_name(t.typ, generate)})"
        elif isinstance(t, typedesc.FunctionType):
            args = (self.type_name(x, generate) for x in [t.returns] + list(t.iterArgTypes()))
            args = ", ".join(args)
            if "__stdcall__" in t.attributes:
                return f"ctypes.WINFUNCTYPE({args})"
            else:
                return f"ctypes.CFUNCTYPE({args})"
        # elif isinstance(t, typedesc.Structure):
        # elif isinstance(t, typedesc.Typedef):
        # elif isinstance(t, typedesc.Union):
        return t.name
        # All typedesc typedefs should be handled
        # raise TypeError('This typedesc should be handled %s'%(t))

    ################################################################

    _aliases = 0

    @cache.cached_pure_method()
    def Alias(self, alias):
        """Handles Aliases. No test cases yet"""
        # FIXME
        ret = GeneratorResult()
        if self.generate_comments:
            ret.update(self.print_comment(alias))
        self._aliases += 1
        ret.write("stream", f"{alias.name} = {alias.alias}# alias")
        return ret

    _macros = 0

    @cache.cached_pure_method()
    def Macro(self, macro):
        """
        Handles macro. No test cases else that #defines.

        Clang will first give us the macro definition,
        and then later, the macro reference in code will be replaced by teh macro body.
        So really, there is nothing to actually generate.
        Just push the macro in comment, and let the rest work away

        """
        ret = GeneratorResult()
        if macro.location is None:
            log.info('Ignoring %s with no location', macro.name)
            return ret
        self.enable_macro_processing()
        if self.generate_locations:
            ret.write("stream", f"# {macro.name}:{macro.location}")
        if self.generate_comments:
            ret.update(self.print_comment(macro))

        # get tokens types all the way to here ?
        # 1. clang makes the decision on type casting and validity of data.
        # let's not try to be clever.
        # only ignore, undefined references, macro functions...
        # 2. or get a flag in macro that tells us if something contains undefinedIdentifier /is not codegenable ?
        # codegen should decide what codegen can do.
        macro_args = macro.args
        macro_body = macro.body
        if util.contains_invalid_code(macro):
            # we can't handle that, we comment it out
            if isinstance(macro.body, typedesc.InvalidGeneratedMacro):
                ret.write("stream", f"# {macro.name} = {macro.body.code} # macro")
            elif isinstance(macro.body, typedesc.UndefinedIdentifier):
                ret.write("stream", f"# {macro.name} = {macro.body.name} # macro")
            else:  # we assume it's a list
                macro_body = " ".join(str(_) for _ in macro.body)
                ret.write("stream", f"# {macro.name} = {macro_body} # macro")
        elif macro_args:
            if self.parser.advanced_macro:
                macro_func = process_macro_function(macro.name, macro.args, macro.body)
                if macro_func is not None:
                    ret.write("stream", f"\n# macro function {macro.name}{macro_func}")
                else:
                    ret.write("stream", f"\n# invalid macro function {macro.name}{macro.body}")
            else:
                ret.write("stream", f"\n# macro function {macro.name}")

        elif isinstance(macro_body, bool):
            ret.write("stream", f"{macro.name} = {macro_body} # macro")
            self.macros += 1
            self.names.append(macro.name)
        elif isinstance(macro_body, str):
            macro_body = macro_body
            macro_body = process_c_literals(macro_body, self.parser.get_pointer_width())
            macro_body = replace_builtins(macro_body)
            macro_body = replace_pointer_types(macro_body)
            # what about integers you ask ? body token that represents token are Integer here.
            # either it's just a thing we gonna print, or we need to have a registered item
            ret.write("stream", f"{macro.name} = ({macro_body}) # macro")
            self.macros += 1
            self.names.append(macro.name)
        # This is why we need to have token types all the way here.
        # but at the same time, clang does not type tokens. So we might as well guess them here too
        elif util.body_is_all_string_tokens(macro_body):
            macro_body = "".join(str(_) for _ in macro.body)
            ret.write("stream", f"{macro.name} = ({macro_body}) # macro")
            self.macros += 1
            self.names.append(macro.name)
        elif macro_body is None:
            ret.write("stream", f"# {macro.name} = ({macro_body}) # macro")
        else:
            # this might be a token list of float literal
            macro_body = macro_body
            macro_body = process_c_literals(macro_body, self.parser.get_pointer_width())
            macro_body = replace_builtins(macro_body)
            # or anything else that might be a valid python literal...
            ret.write("stream", f"{macro.name} = ({macro_body}) # macro")
            self.macros += 1
            self.names.append(macro.name)
        return ret

    _typedefs = 0

    @cache.cached()
    def Typedef(self, tp):
        ret = GeneratorResult()
        if self.generate_comments:
            ret.update(self.print_comment(tp))
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
            ret.write("stream", f"{name} = ctypes.{sized_types[tp.name]}")
            self.names.append(tp.name)
            return ret
        if tp.typ not in self.done:
            # generate only declaration code for records ?
            # if type(tp.typ) in (typedesc.Structure, typedesc.Union):
            #    self._generate(tp.typ.get_head())
            #    self.more.add(tp.typ)
            # else:
            #    self._generate(tp.typ)
            ret.update(self._generate(tp.typ))
        # generate actual typedef code.
        if tp.name != self.type_name(tp.typ):
            ret.write("stream", f"{name} = {self.type_name(tp.typ)}")

            if isinstance(tp.typ, typedesc.Enumeration):
                ret.write(
                    "stream",
                    f"{name}__enumvalues = {self.type_name(tp.typ)}__enumvalues"
                )
                self.names.append(f"{name}__enumvalues")

        self.names.append(tp.name)
        self._typedefs += 1
        return ret

    def _get_real_type(self, tp):
        # FIXME, kinda useless really.
        if isinstance(tp, typedesc.Typedef):
            if isinstance(tp.typ, typedesc.Typedef):
                raise TypeError(f"Nested loop in Typedef {tp.name}")
            return self._get_real_type(tp.typ)
        elif isinstance(tp, typedesc.CvQualifiedType):
            return self._get_real_type(tp.typ)
        return tp

    _arraytypes = 0

    @cache.cached()
    def ArrayType(self, tp):
        ret = GeneratorResult()
        ret.update(self._generate(self._get_real_type(tp.typ)))
        ret.update(self._generate(tp.typ))
        self._arraytypes += 1
        return ret

    _functiontypes = 0
    _notfound_functiontypes = 0

    @cache.cached()
    def FunctionType(self, tp):
        ret = GeneratorResult()
        ret.update(self._generate(tp.returns))
        ret.update(self.generate_all(tp.arguments))
        # print >> self.stream, "%s = %s # Functiontype " % (
        # self.type_name(tp), [self.type_name(a) for a in tp.arguments])
        self._functiontypes += 1
        return ret

    @cache.cached()
    def Argument(self, tp):
        return self._generate(tp.typ)

    _pointertypes = 0

    @cache.cached()
    def PointerType(self, tp):
        ret = GeneratorResult()
        # print 'generate', tp.typ
        if isinstance(tp.typ, typedesc.PointerType):
            ret.update(self._generate(tp.typ))
        elif type(tp.typ) in (typedesc.Union, typedesc.Structure):
            ret.update(self._generate(tp.typ.get_head()))
            self.more[tp.typ] = True
        elif isinstance(tp.typ, typedesc.Typedef):
            ret.update(self._generate(tp.typ))
        else:
            ret.update(self._generate(tp.typ))
        self._pointertypes += 1
        return ret

    @cache.cached()
    def CvQualifiedType(self, tp):
        return self._generate(tp.typ)

    _variables = 0
    _notfound_variables = 0

    @cache.cached()
    def Variable(self, tp):
        ret = GeneratorResult()
        self._variables += 1
        if self.generate_comments:
            ret.update(self.print_comment(tp))

        # 2021-02 give me a test case for this. it breaks all extern variables otherwise.
        if tp.extern and self.find_library_with_func(tp):
            dll_library = self.find_library_with_func(tp)
            ret.update(self._generate(tp.typ))
            # calling convention does not matter for in_dll...
            libname = self.get_sharedlib(ret, dll_library, "cdecl")
            ret.write(
                "stream",
                f"{tp.name} = ({self.type_name(tp.typ)}).in_dll({libname}, '{tp.name}')"
            )
            self.names.append(tp.name)
            # wtypes.h contains IID_IProcessInitControl, for example
            return ret

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
            func_args = tuple(x for x in tp.typ.iterArgNames())
            ret.write("stream", f"{tp.name} = {self.type_name(tp.init)} # args: {func_args}")
            self.names.append(tp.name)
            return ret
        elif isinstance(tp.typ, typedesc.PointerType) or isinstance(tp.typ, typedesc.ArrayType):
            if isinstance(tp.typ.typ, typedesc.FundamentalType) and (
                tp.typ.typ.name in ["c_ubyte", "c_char", "c_wchar"]
            ):
                # string
                # FIXME a char * is not a python string.
                # we should output a cstring() construct.
                init_value = repr(tp.init)
            elif isinstance(tp.typ.typ, typedesc.FundamentalType) and (
                "int" in tp.typ.typ.name or "long" in tp.typ.typ.name
            ):
                # array of number
                # CARE: size of elements must match size of array
                # init_value = repr(tp.init)
                init_value = ",".join(str(x) for x in tp.init)
                init_value = f"[{init_value}]"
                # we do NOT want Variable to be described as ctypes object
                # when we can have a python abstraction for them.
                # init_value_type = self.type_name(tp.typ, False)
                # init_value = "(%s)(%s)"%(init_value_type,init_value)
            elif isinstance(tp.typ.typ, typedesc.Structure):
                self._generate(tp.typ.typ)
                init_value = self.type_name(tp.typ, False) + "()"
            else:
                if tp.init is not None:
                    init_value = tp.init
                else:
                    init_value = self.type_name(tp.typ, False) + "()"

        elif isinstance(tp.typ, typedesc.Structure):
            init_value = self.type_name(tp.typ, False)
        elif isinstance(tp.typ, typedesc.FundamentalType) and tp.typ.name in [
            "c_ubyte",
            "c_char",
            "c_wchar",
        ]:
            if tp.init is not None:
                init_value = repr(tp.init)
            else:
                init_value = "'\\x00'"
        else:
            # we want to have FundamentalType variable use the actual
            # type default, and not be a python ctypes object
            # if init_value is None:
            #    init_value = ''; # use default ctypes object constructor
            # init_value = "%s(%s)"%(self.type_name(tp.typ, False), init_value)
            if tp.init is not None:
                # TODO, check that if tp.init is a string literal
                #  and that there is a definition for it ?
                init_value = tp.init
            elif tp.typ.name in ["c_float", "c_double", "c_longdouble"]:
                init_value = 0.0
            else:
                # integers
                init_value = 0
        #
        # print it out
        ret.write(
            "stream",
            f"{tp.name} = {init_value} # Variable {self.type_name(tp.typ, False)}"
        )
        #
        self.names.append(tp.name)
        return ret

    _enumvalues = 0

    @cache.cached_pure_method()
    def EnumValue(self, tp):
        # FIXME should be in parser
        ret = GeneratorResult()
        value = int(tp.value)
        ret.write("stream", f"{tp.name} = {value}")
        self.names.append(tp.name)
        self._enumvalues += 1
        return ret

    _enumtypes = 0

    @cache.cached_pure_method()
    def Enumeration(self, tp):
        ret = GeneratorResult()
        if self.generate_comments:
            ret.update(self.print_comment(tp))
        ret.write("stream", u'')
        if tp.name:
            ret.write("stream", f"# values for enumeration '{tp.name}'")
        else:
            ret.write("stream", "# values for unnamed enumeration")
        ret.write("stream", f"{tp.name}__enumvalues = {{")
        for item in tp.values:
            ret.write("stream", f"    {int(item.value)}: '{item.name}',")
        ret.write("stream", "}")

        # Some enumerations have the same name for the enum type
        # and an enum value.  Excel's XlDisplayShapes is such an example.
        # Since we don't have separate namespaces for the type and the values,
        # we generate the TYPE last, overwriting the value. XXX
        for item in tp.values:
            ret.update(self._generate(item))
        if tp.name:
            # Enums can be forced to occupy less space than an int when the compiler flag '-fshort-enums' is set.
            # The size adjustment is done when possible, depending on the values of the enum.
            # In any case, we should trust the enum size returned by the compiler.
            #
            # Furthermore, in order to obtain a correct (un)signed representation in Python,
            # the signedness of the enum is deduced from the sign of enum values.
            # If there is not any negative value in the enum, then the resulting ctype will be unsigned.
            # Sources:
            #   https://stackoverflow.com/a/54527229/1641819
            #   https://stackoverflow.com/a/56432050/1641819

            # Look for any negative value in enum
            has_negative = False
            for item in tp.values:
                if item.value < 0:
                    has_negative = True
                    break

            # Determine enum type depending on its size and signedness
            if tp.size == 1:
                enum_ctype = 'ctypes.c_int8' if has_negative else 'ctypes.c_uint8'
            elif tp.size == 2:
                enum_ctype = 'ctypes.c_int16' if has_negative else 'ctypes.c_uint16'
            elif tp.size == 4:
                enum_ctype = 'ctypes.c_int32' if has_negative else 'ctypes.c_uint32'
            elif tp.size == 8:
                enum_ctype = 'ctypes.c_int64' if has_negative else 'ctypes.c_uint64'
            else:
                enum_ctype = 'ctypes.c_int' if has_negative else 'ctypes.c_uint'

            ret.write("stream", f"{tp.name} = {enum_ctype} # enum")
            self.names.append(tp.name)
        self._enumtypes += 1
        return ret

    def get_undeclared_type(self, item):
        """
        Checks if a typed has already been declared in the python output
        or is a builtin python type.
        """
        if item.name in self.head_generated:
            return None
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

    def _get_undefined_head_dependencies(self, struct):
        """Return head dependencies on other record types.
        Head dependencies is exclusive of body dependency. It's one or the other.
        """
        r = set()
        for m in struct.members:
            if isinstance(m.type, typedesc.PointerType) and typedesc.is_record(m.type.typ):
                r.add(m.type)
        # remove all already defined heads
        r = [_ for _ in r if _.name not in self.head_generated]
        return r

    def _get_undefined_body_dependencies(self, struct):
        """Return head dependencies on other record types.
        Head dependencies is exclusive of body dependency. It's one or the other.
        """
        r = set()
        for m in struct.members:
            if isinstance(m.type, typedesc.ArrayType) and typedesc.is_record(m.type.typ):
                r.add(m.type.typ)
            elif typedesc.is_record(m.type):
                r.add(m.type)
            elif m.type not in self.done:
                r.add(m.type)
        # remove all already defined bodies
        r = [_ for _ in r if _.name not in self.body_generated]
        return r

    _structures = 0

    @cache.cached()
    def Structure(self, struct):
        ret = GeneratorResult()
        if struct.name in self.head_generated and struct.name in self.body_generated:
            self.done[struct] = True
            return ret
        self.enable_structure_type()
        self._structures += 1
        depends = set()
        # We only print a empty struct.
        if struct.members is None:
            log.info('No members for: %s', struct.name)
            ret.update(self._generate(struct.get_head(), False))
            return ret
        # look in bases class for dependencies
        # FIXME - need a real dependency graph maker
        # remove myself, just in case.
        if struct in self.done:
            del self.done[struct]
        # checks members dependencies in bases
        for b in struct.bases:
            depends.update([self.get_undeclared_type(m.type) for m in b.members])
        depends.discard(None)
        if len(depends) > 0:
            log.debug("Generate %s DEPENDS for Bases %s", struct.name, depends)
            for dep in depends:
                ret.update(self._generate(dep))

        # checks members dependencies
        # test_record_ordering head does not mean declared. _fields_ mean declared
        # CPOINTER members just require a class definition
        # whereas members that are non pointers require a full _fields_ declaration
        # before this record body is defined fully
        # depends.update([self.get_undeclared_type(m.type)
        #                 for m in struct.members])
        # self.done[struct] = True
        # hard dependencies for members types that are not pointer but records
        # soft dependencies for members pointers to record
        undefined_head_dependencies = self._get_undefined_head_dependencies(struct)
        undefined_body_dependencies = self._get_undefined_body_dependencies(struct)

        if len(undefined_body_dependencies) == 0:
            if len(undefined_head_dependencies) == 0:
                # generate this head and body in one go
                # if struct.get_head() not in self.done:
                if struct.name not in self.head_generated:
                    ret.update(self._generate(struct.get_head(), True))
                    ret.update(self._generate(struct.get_body(), True))
                else:
                    ret.update(self._generate(struct.get_body(), False))
            else:
                # generate this head first, to avoid recursive issue, then the dep, then this body
                ret.update(self._generate(struct.get_head(), False))
                for dep in undefined_head_dependencies:
                    ret.update(self._generate(dep))
                ret.update(self._generate(struct.get_body(), False))
        else:
            # hard dep on defining the body of these dependencies
            # generate this head first, to avoid recursive issue, then the dep, then this body
            ret.update(self._generate(struct.get_head(), False))
            for dep in undefined_head_dependencies:
                ret.update(self._generate(dep))
            for dep in undefined_body_dependencies:
                ret.update(self._generate(dep))
            for dep in undefined_body_dependencies:
                if isinstance(dep, typedesc.Structure):
                    ret.update(self._generate(dep.get_body(), False))
            ret.update(self._generate(struct.get_body(), False))

        # we defined ourselve
        self.done[struct] = True

        return ret

    Union = Structure

    @cache.cached()
    def StructureHead(self, head, inline=False):
        ret = GeneratorResult()
        if head.name in self.head_generated:
            log.debug("Skipping - Head already generated for %s", head.name)
            return ret
        log.debug("Head start for %s inline:%s", head.name, inline)
        for struct in head.struct.bases:
            ret.update(self._generate(struct.get_head()))
            # add dependencies
            self.more[struct] = True
        basenames = [self.type_name(b) for b in head.struct.bases]
        if basenames:
            # method_names = [m.name for m in head.struct.members if type(m) is typedesc.Method]
            ret.write("stream", f"class {head.struct.name}({', '.join(basenames)}):")
        else:
            # methods = [m for m in head.struct.members if type(m) is typedesc.Method]
            if isinstance(head.struct, typedesc.Structure):
                # Inherit from our ctypes.Structure extension
                ret.write("stream", f"class {head.struct.name}(Structure):")
            elif isinstance(head.struct, typedesc.Union):
                ret.write("stream", f"class {head.struct.name}(Union):")
        if not inline:
            ret.write("stream", "    pass\n")
        # special empty struct
        if inline and not head.struct.members:
            ret.write("stream", "    pass\n")
        self.names.append(head.struct.name)
        log.debug("Head finished for %s", head.name)
        self.head_generated.add(head.name)
        return ret

    @cache.cached()
    def StructureBody(self, body, inline=False):
        ret = GeneratorResult()
        if body.name in self.body_generated:
            log.debug("Skipping - Body already generated for %s", body.name)
            return ret
        log.debug("Body start for %s", body.name)
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
        log.debug("body inline:%s for structure %s", inline, body.struct.name)
        if not inline:
            prefix = f"{body.struct.name}."
        else:
            prefix = "    "
        if methods:
            # XXX we have parsed the COM interface methods but should
            # we emit any code for them?
            pass
        # LXJ: we pack all the time, because clang gives a precise field offset
        # per target architecture. No need to defer to ctypes logic for that.
        if fields:
            ret.write("stream", f"{prefix}_pack_ = True # source:{body.struct.packed}")

        if body.struct.bases:
            if len(body.struct.bases) == 1:  # its a Struct or a simple Class
                ret.update(
                    self._generate(body.struct.bases[0].get_body(), inline))
            else:  # we have a multi-parent inheritance
                for b in body.struct.bases:
                    ret.update(self._generate(b.get_body(), inline))
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
                unnamed_fields[f] = f"_{len(unnamed_fields)}"
        if unnamed_fields:
            ret.write("stream", f"{prefix}_anonymous_ = {unnamed_fields.values()}")
        if len(fields) > 0:
            ret.write("stream", f"{prefix}_fields_ = [")

            if self.generate_locations and body.struct.location:
                ret.write("stream", f"    # {body.struct.name} {body.struct.location}")
            index = 0
            for f in fields:
                if inline:
                    ret.write("stream", "    ", end='')
                fieldname = unnamed_fields.get(f, f.name)
                type_name = self.type_name(f.type)
                # handle "__" prefixed names by using a wrapper
                if type_name.startswith("__"):
                    type_name = f"globals()['{type_name}']"
                # a bitfield needs a triplet
                if f.is_bitfield is False:
                    ret.write("stream", f"    ('{fieldname}', {type_name}),")
                else:
                    # FIXME: Python bitfield is int32 only.
                    # from clang.cindex import TypeKind
                    # print fieldname
                    # import code
                    # code.interact(local=locals())
                    ret.write(
                        "stream",
                        f"    ('{fieldname}', {self.type_name(f.type)}, {f.bits}),"
                    )
            if inline:
                ret.write("stream", "    ", end='')
            ret.write("stream", "]\n")
        log.debug('Body finished for %s', body.name)
        self.body_generated.add(body.name)
        return ret

    def find_library_with_func(self, func):
        if hasattr(func, "dllname"):
            return func.dllname
        name = func.name
        if os.name == "posix" and sys.platform == "darwin":
            name = f"_{name}"
        for dll in self.searched_dlls:
            try:
                getattr(dll, name)
            except AttributeError:
                pass
            else:
                return dll
        return None

    _c_libraries = None

    def need_CLibraries(self):
        ret = GeneratorResult()
        # Create a '_libraries' dictionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._c_libraries is None:
            self._c_libraries = {}
            ret.write("imports", "_libraries = {}")
        return ret

    _stdcall_libraries = None

    def need_WinLibraries(self):
        # Create a '_stdcall_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        ret = GeneratorResult()
        if self._stdcall_libraries is None:
            self._stdcall_libraries = {}
            ret.write("imports", "_stdcall_libraries = {}")
        return ret

    _dll_stub_issued = False

    def get_sharedlib(self, ret, library, cc, stub=False):
        # deal with missing -l with a stub
        stub_comment = ""
        library_name = repr(library._name)
        library_filepath = repr(library._filepath)
        if stub and not self._dll_stub_issued:
            self._dll_stub_issued = True
            stub_comment = " FunctionFactoryStub() # "
            ret.write("imports", textwrap.dedent("""
                class FunctionFactoryStub:
                    def __getattr__(self, _):
                      return ctypes.CFUNCTYPE(lambda y:y)
                """))
            ret.write("imports", "# libraries['FIXME_STUB'] explanation")
            ret.write(
                "imports",
                "# As you did not list (-l libraryname.so) a library that "
                "exports this function"
            )
            ret.write("imports", "# This is a non-working stub instead. ")
            ret.write(
                "imports",
                "# You can either re-run clan2py with -l /path/to/library.so"
            )
            ret.write(
                "imports",
                "# Or manually fix this by comment the ctypes.CDLL loading"
            )

        # generate windows call
        if cc == "stdcall":
            ret.update(self.need_WinLibraries())
            if library._name not in self._stdcall_libraries:
                ret.write(
                    "imports",
                    f"_stdcall_libraries[{library_name}] "
                    f"={stub_comment} ctypes.WinDLL({library_filepath})"
                )

                self._stdcall_libraries[library._name] = None
            return f"_stdcall_libraries[{library_name}]"

        # generate clinux call
        ret.update(self.need_CLibraries())
        if self.preloaded_dlls != []:
            global_flag = ", mode=ctypes.RTLD_GLOBAL"
        else:
            global_flag = ""
        if library._name not in self._c_libraries:
            ret.write(
                "imports",
                f"_libraries[{library_name}] ={stub_comment} ctypes.CDLL({library_name}{global_flag})"
            )
            self._c_libraries[library._name] = None
        return f"_libraries[{library_name}]"

    _STRING_defined = False

    def need_STRING(self):
        ret = GeneratorResult()
        if self._STRING_defined:
            return
        ret.write("imports", "STRING = c_char_p")
        self._STRING_defined = True
        return ret

    _WSTRING_defined = False

    def need_WSTRING(self):
        ret = GeneratorResult()
        if self._WSTRING_defined:
            return
        ret.write("imports", "WSTRING = c_wchar_p")
        self._WSTRING_defined = True
        return ret

    _functiontypes = 0
    _notfound_functiontypes = 0

    @cache.cached()
    def Function(self, func):
        ret = GeneratorResult()
        # FIXME: why do we call this ? it does nothing
        if self.generate_comments:
            ret.update(self.print_comment(func))
        ret.update(self._generate(func.returns))
        ret.update(self.generate_all(func.iterArgTypes()))

        # useful code
        args = [self.type_name(a) for a in func.iterArgTypes()]
        cc = "cdecl"
        if "__stdcall__" in func.attributes:
            cc = "stdcall"

        #
        library = self.find_library_with_func(func)
        if library:
            libname = self.get_sharedlib(ret, library, cc)
        else:

            class LibraryStub:
                _filepath = "FIXME_STUB"
                _name = "FIXME_STUB"

            libname = self.get_sharedlib(ret, LibraryStub(), cc, stub=True)

        argnames = tuple(a or f"p{i}" % (i + 1) for i, a in enumerate(func.iterArgNames()))

        if self.generate_locations and func.location:
            ret.write("stream", f"# {func.name} {func.location}")
        # Generate the function decl code
        ret.write("stream", f"{func.name} = {libname}.{func.name}")
        ret.write("stream", f"{func.name}.restype = {self.type_name(func.returns)}")
        if self.generate_comments:
            ret.write("stream", f"# {func.name}({', '.join(argnames)})")
        ret.write("stream", f"{func.name}.argtypes = [{', '.join(args)}]")

        if self.generate_docstrings:

            def typeString(typ):
                if hasattr(typ, "name"):
                    return typ.name
                elif hasattr(typ, "typ") and isinstance(typ, typedesc.PointerType):
                    return typeString(typ.typ) + " *"
                else:
                    return "unknown"

            argsAndTypes = zip([typeString(t) for t in func.iterArgTypes()], argnames)
            argsAndTypes = ", ".join([f"{i[0]} {i[1]}" for i in argsAndTypes])
            file = func.location[0]
            line = func.location[1]
            ret.write(
                "stream",
                f'{func.name}.__doc__ = """{func.returns} {func.name}({argsAndTypes})\n'
                f'    {file}:{line}"""'.format(
                )
            )

        self.names.append(func.name)
        self._functiontypes += 1
        return ret

    @cache.cached_pure_method()
    def FundamentalType(self, _type):
        ret = GeneratorResult()
        self._get_fundamental_typename(_type)
        # there is actually nothing to generate here for FundamentalType
        return ret

    def _get_fundamental_typename(self, _type):
        """Returns the proper ctypes class name for a fundamental type

        1) activates generation of appropriate headers for
        ## int128_t
        ## c_long_double_t
        2) return appropriate name for type
        """
        log.debug("HERE in FundamentalType for %s %s", _type, _type.name)
        if _type.name in ["None", "c_long_double_t", "c_uint128", "c_int128"]:
            self.enable_fundamental_type_wrappers()
            return _type.name

        return f"ctypes.{_type.name}"

    ########

    @cache.cached()
    def _generate(self, item, *args):
        """ wraps execution of specific methods."""
        ret = GeneratorResult()
        if item in self.done:
            return ret
        # verbose output with location.
        if self.generate_locations and item.location:
            ret.write("stream," f"# {item.name or item}:{item.location}")
        if self.generate_comments:
            ret.update(self.print_comment(item))
        log.debug("generate %s, %s", item.__class__.__name__, item.name)
        # to avoid infinite recursion, we have to mark it as done
        # before actually generating the code.
        self.done[item] = True
        # go to specific treatment
        mth = getattr(self, type(item).__name__)
        ret.update(mth(item, *args))
        return ret

    @cache.cached_pure_method()
    def print_comment(self, item):
        ret = GeneratorResult()
        if item.comment is None:
            return
        for comment in textwrap.wrap(item.comment, 78):
            ret.write("stream", f"# {comment}")
        return ret

    def generate_all(self, items):
        ret = GeneratorResult()
        for item in items:
            ret.update(self._generate(item))
        return ret

    def generate_items(self, items, verbose=False):
        # items = set(items)
        ret = GeneratorResult()
        loops = 0
        items = list(items)
        while items:
            loops += 1
            self.more = collections.OrderedDict()
            ret.update(self.generate_all(tuple(items)))

            # items |= self.more , but keeping ordering
            _s = set(items)
            for k in self.more.keys():
                if k not in _s:
                    items.append(k)

            # items -= self.done, but keep ordering
            _done = self.done
            for i in list(items):
                if i in _done:
                    items.remove(i)

        if verbose:
            log.info("needed %d loop(s)" % loops)
        return ret

    def generate(self, parser, items, verbose=False):
        self.generate_headers(parser)
        self.generate_code(items)

    def generate_code(self, items, verbose=False):
        ret = GeneratorResult()
        ret.write(
            "imports",
            "\n".join([
                f"ctypes.CDLL({preloaded_dll}', ctypes.RTLD_GLOBAL)"
                for preloaded_dll
                in self.preloaded_dlls]
            )
        )
        ret.update(self.generate_items(items, verbose=verbose))
        print(ret.get("imports"), file=self.imports)
        print(ret.get("stream"), file=self.stream)

        self.output.write(self.imports.getvalue())
        self.output.write("\n\n")
        self.output.write(self.stream.getvalue())

        text = "__all__ = \\"
        # text Wrapper doesn't work for the first line in certain cases.
        print(text, file=self.output)
        # doesn't work for the first line in certain cases.
        wrapper = textwrap.TextWrapper(break_long_words=False, initial_indent="    ",
                                       subsequent_indent="    ")
        text = f"[{', '.join([repr(str(n)) for n in sorted(self.names)])}]"
        for line in wrapper.wrap(text):
            print(line, file=self.output)

    def print_stats(self, stream):
        total = (
            self._structures
            + self._functiontypes
            + self._enumtypes
            + self._typedefs
            + self._pointertypes
            + self._arraytypes
        )
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


def generate_code(
    srcfiles,
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
    flags=None,
    advanced_macro=False,
):
    # expressions is a sequence of compiled regular expressions,
    # symbols is a sequence of names
    parser = clangparser.Clang_Parser(flags or [])
    # if macros are not needed, use a faster TranslationUnit
    if typedesc.Macro in types:
        parser.activate_macros_parsing(advanced_macro)
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
        log.debug("Parsing input file %s", srcfile)
        parser.parse(srcfile)
    items += parser.get_result()
    log.debug("Input was parsed")
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
            else:
                log.debug("not generating {}: not a symbol".format(i.name))

        if syms:
            log.warning("symbols not found %s", [str(x) for x in list(syms)])

    if expressions:
        for s in expressions:
            log.debug("regexp: looking for %s", s.pattern)
            for i in items:
                log.debug("regexp: i.name is %s", i.name)
                if i.name is None:
                    continue
                match = s.match(i.name)
                # if we only want complete matches:
                if match and match.group() == i.name:
                    todo.append(i)
                    continue
                # if we follow our own documentation,
                # allow regular expression match of any part of name:
                match = s.search(i.name)
                if match:
                    todo.append(i)
                    continue
    if symbols or expressions:
        items = todo

    ################
    # TODO FIX this
    cross_arch = "-target" in " ".join(flags)
    gen = Generator(
        outfile,
        generate_locations=generate_locations,
        generate_comments=generate_comments,
        generate_docstrings=generate_docstrings,
        known_symbols=known_symbols,
        searched_dlls=searched_dlls,
        preloaded_dlls=preloaded_dlls,
        cross_arch=cross_arch,
    )

    # add some headers and ctypes import
    gen.generate_headers(parser)
    # make the structures
    gen.generate_code(tuple(items), verbose)
    if verbose:
        gen.print_stats(sys.stderr)
