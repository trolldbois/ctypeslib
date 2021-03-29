"""clangparser - use clang to get preprocess a source code."""

import collections
import functools
import itertools
import logging
import os
import platform

from ctypeslib.codegen.cindex import Index, TranslationUnit, TargetInfo
from ctypeslib.codegen.cindex import TypeKind
from ctypeslib.codegen.hash import hash_combine

from ctypeslib.codegen import cache
from ctypeslib.codegen import cursorhandler
from ctypeslib.codegen import preprocess
from ctypeslib.codegen import typedesc
from ctypeslib.codegen import typehandler
from ctypeslib.codegen import util
from ctypeslib.codegen.handler import DuplicateDefinitionException
from ctypeslib.codegen.handler import InvalidDefinitionError
from ctypeslib.codegen.handler import InvalidTranslationUnitException


log = logging.getLogger('clangparser')


class Clang_Parser(object):
    """
    Will parse libclang AST tree to create a representation of Types and
    different others source code objects objets as described in Typedesc.

    For each Declaration a declaration will be saved, and the type of that
    declaration will be cached and saved.
    """

    has_values = {"Enumeration", "Function", "FunctionType",
                  "OperatorFunction", "Method", "Constructor",
                  "Destructor", "OperatorMethod",
                  "Converter"}

    # FIXME, macro definition __SIZEOF_DOUBLE__
    ctypes_typename = {
        TypeKind.VOID: 'None',  # because ctypes.POINTER(None) == c_void_p
        TypeKind.BOOL: 'c_bool',
        TypeKind.CHAR_U: 'c_ubyte',  # ?? used for PADDING
        TypeKind.UCHAR: 'c_ubyte',  # unsigned char
        TypeKind.CHAR16: 'c_wchar',  # char16_t
        TypeKind.CHAR32: 'c_wchar',  # char32_t
        TypeKind.USHORT: 'c_ushort',
        TypeKind.UINT: 'c_uint',
        TypeKind.ULONG: 'TBD',
        TypeKind.ULONGLONG: 'c_ulonglong',
        TypeKind.UINT128: 'c_uint128',  # FIXME
        TypeKind.CHAR_S: 'c_char',  # char
        TypeKind.SCHAR: 'c_byte',  # signed char
        TypeKind.WCHAR: 'c_wchar',
        TypeKind.SHORT: 'c_short',
        TypeKind.INT: 'c_int',
        TypeKind.LONG: 'TBD',
        TypeKind.LONGLONG: 'c_longlong',
        TypeKind.INT128: 'c_int128',  # FIXME
        TypeKind.FLOAT: 'c_float',
        TypeKind.DOUBLE: 'c_double',
        TypeKind.LONGDOUBLE: 'c_longdouble',
        TypeKind.POINTER: 'POINTER_T',
        TypeKind.NULLPTR: 'c_void_p'
    }

    def __init__(self, flags):
        self.all = collections.OrderedDict()
        # a shortcut to identify registered decl in cases of records
        self.all_set = set()
        self.cpp_data = {}
        self._unhandled = []
        self.fields = {}
        self.tu = None
        local_triple = f"{platform.machine()}-{platform.system()}".lower()
        self.target_triple = local_triple
        flag_iterator = iter(flags)
        flags = []
        for (flag, argument) in itertools.zip_longest(flag_iterator, flag_iterator):
            if flag == "-target":
                self.target_triple = argument
                if self.target_triple == local_triple:
                    continue
            flags.append(flag)
            if argument is not None:
                flags.append(argument)
        self.flags = flags
        self.ctypes_sizes = {}
        self.init_parsing_options()
        self.make_ctypes_convertor(flags)
        self.cursorkind_handler = cursorhandler.CursorHandler(self)
        self.typekind_handler = typehandler.TypeHandler(self)
        self.__filter_location = None
        self.__processed_location = set()
        self._advanced_macro = False
        self.interpreter_namespace = {}

    def init_parsing_options(self):
        """Set the Translation Unit to skip functions bodies per default."""
        self.tu_options = TranslationUnit.PARSE_SKIP_FUNCTION_BODIES

    def activate_macros_parsing(self, advanced_macro=False):
        """Activates the detailled code parsing options in the Translation
        Unit."""
        self.tu_options |= TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        self._advanced_macro = advanced_macro

    @property
    def advanced_macro(self):
        return self._advanced_macro

    def activate_comment_parsing(self):
        """Activates the comment parsing options in the Translation Unit."""
        self.tu_options |= TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION

    def deactivate_function_body_parsing(self):
        self.tu_options |= TranslationUnit.PARSE_SKIP_FUNCTION_BODIES

    def filter_location(self, src_files):
        self.__filter_location = list(
            map(lambda f: os.path.abspath(f), src_files))

    @cache.cached_pure_method()
    def _do_parse(self, filename):
        if os.path.abspath(filename) in self.__processed_location:
            return None
        index = Index.create()
        tu = index.parse(filename, self.flags, options=self.tu_options)
        if not tu:
            log.warning("unable to load input")
            return None
        return tu

    def parse(self, filename):
        """
        . reads 1 file
        . if there is a compilation error, print a warning
        . get root cursor and recurse
        . for each STRUCT_DECL, register a new struct type
        . for each UNION_DECL, register a new union type
        . for each TYPEDEF_DECL, register a new alias/typdef to the underlying type
            - underlying type is cursor.type.get_declaration() for Record
        . for each VAR_DECL, register a Variable
        . for each TYPEREF ??
        """
        self.tu = self._do_parse(filename)
        if self.tu is None:
            return
        self.ti = TargetInfo.from_translation_unit(self.tu)
        self._parse_tu_diagnostics(self.tu, filename)
        root = self.tu.cursor
        for node in root.get_children():
            self.startElement(node)
        return

    @cache.cached_pure_method()
    def _do_parse_string(self, input_data, lang='c', all_warnings=False, flags=None):
        """Use this parser on a memory string/file, instead of a file on disk"""
        tu = util.get_tu(input_data, lang, all_warnings, flags)
        return tu

    def parse_string(self, input_data, lang='c', all_warnings=False, flags=None):
        """Use this parser on a memory string/file, instead of a file on disk"""
        self.tu = self._do_parse_string(input_data, lang, all_warnings, flags)
        self.ti = TargetInfo.from_translation_unit(self.tu)
        self._parse_tu_diagnostics(self.tu, "memory_input.c")
        root = self.tu.cursor
        for node in root.get_children():
            self.startElement(node)
        return

    @staticmethod
    def _parse_tu_diagnostics(tu, input_filename):
        if len(tu.diagnostics) == 0:
            return
        errors = []
        for x in tu.diagnostics:
            msg = "{} ({}:{}:{})".format(
                x.spelling, input_filename,
                x.location.line, x.location.column)
            log.warning(msg)
            if x.severity > 2:
                errors.append(msg)
        if len(errors) > 0:
            log.warning("Source code has %d error. Please fix.", len(errors))
            # code.interact(local=locals())
            raise InvalidTranslationUnitException(errors[0])

    def startElement(self, node):
        """Recurses in children of this node"""
        if node is None:
            return

        if self.__filter_location is not None:
            # dont even parse includes.
            # FIXME: go back on dependencies ?
            if node.location.file is None:
                return
            filepath = os.path.abspath(node.location.file.name)
            if filepath not in self.__filter_location:
                if not filepath.startswith('/usr'):
                    log.debug("skipping include '%s'", filepath)
                return
        # find and call the handler for this element
        log.debug(
            '%s:%d: Found a %s|%s|%s',
            node.location.file,
            node.location.line,
            node.kind.name,
            node.displayname,
            node.spelling)
        # build stuff.
        try:
            stop_recurse = self.parse_cursor(node)
            if node.location.file is not None:
                filepath = os.path.abspath(node.location.file.name)
                self.__processed_location.add(filepath)
            # Signature of parse_cursor is:
            # if the fn returns True, do not recurse into children.
            # anything else will be ignored.
            if stop_recurse is not False:  # True:
                return
            # if fn returns something, if this element has children, treat
            # them.
            for child in node.get_children():
                self.startElement(child)
        except InvalidDefinitionError:
            log.exception('Invalid definition')
            # if the definition is invalid
            pass
        # startElement returns None.
        return None

    def register(self, name, obj):
        """Registers an unique type description"""
        all_set_key = hash_combine((name, hash(obj)))
        if all_set_key in self.all_set and name in self.all:
            log.debug('register: %s already defined: %s', name, obj.name)
            return self.all[name]
        if name in self.all:
            if not isinstance(self.all[name], typedesc.Structure) or (
                    self.all[name].members is not None):
                # code.interact(local=locals())
                raise DuplicateDefinitionException(
                    'register: %s which has a previous incompatible definition: %s'
                    '\ndefined here: %s'
                    '\npreviously defined here: %s'
                    % (name, obj.name, obj.location, self.all[name].location))
            if isinstance(self.all[name], typedesc.Structure) and (
                    self.all[name].members is None):
                return obj
        log.debug('register: %s ', name)
        self.all[name] = obj
        self.all_set.add(all_set_key)
        return obj

    def get_registered(self, name):
        """Returns an registered type description"""
        return self.all[name]

    def is_registered(self, name):
        """Checks if a named type description is registered"""
        return name in self.all

    def update_register(self, name, new_obj):
        assert self.is_registered(name)
        obj = self.all.pop(name)
        all_set_key = hash_combine((name, obj))
        try:
            self.all_set.remove(all_set_key)
        except KeyError:
            # leak the previous definition hash in all_set
            pass
        all_set_key = hash_combine((name, new_obj))
        self.all[name] = new_obj
        self.all_set.add(all_set_key)
        return new_obj

    def remove_registered(self, name):
        """Removes a named type"""
        log.debug('Unregister %s', name)
        obj = self.all.pop(name)
        self.all_set.remove(hash_combine((name, obj)))

    def make_ctypes_convertor(self, _flags):
        """
        Fix clang types to ctypes conversion for this parsing instance.
        Some architecture dependent size types have to be changed if the target
        architecture is not the same as local
        """
        # NOTE: one could also use the __SIZEOF_x__ MACROs to obtain sizes.
        tu = util.get_tu('''
typedef short short_t;
typedef int int_t;
typedef long long_t;
typedef long long longlong_t;
typedef float float_t;
typedef double double_t;
typedef long double longdouble_t;
typedef void* pointer_t;''', flags=_flags)
        size = util.get_cursor(tu, 'short_t').type.get_size() * 8
        self.ctypes_typename[TypeKind.SHORT] = 'c_int%d' % (size)
        self.ctypes_typename[TypeKind.USHORT] = 'c_uint%d' % (size)
        self.ctypes_sizes[TypeKind.SHORT] = size
        self.ctypes_sizes[TypeKind.USHORT] = size

        size = util.get_cursor(tu, 'int_t').type.get_size() * 8
        self.ctypes_typename[TypeKind.INT] = 'c_int%d' % (size)
        self.ctypes_typename[TypeKind.UINT] = 'c_uint%d' % (size)
        self.ctypes_sizes[TypeKind.INT] = size
        self.ctypes_sizes[TypeKind.UINT] = size

        size = util.get_cursor(tu, 'long_t').type.get_size() * 8
        self.ctypes_typename[TypeKind.LONG] = 'c_int%d' % (size)
        self.ctypes_typename[TypeKind.ULONG] = 'c_uint%d' % (size)
        self.ctypes_sizes[TypeKind.LONG] = size
        self.ctypes_sizes[TypeKind.ULONG] = size

        size = util.get_cursor(tu, 'longlong_t').type.get_size() * 8
        self.ctypes_typename[TypeKind.LONGLONG] = 'c_int%d' % (size)
        self.ctypes_typename[TypeKind.ULONGLONG] = 'c_uint%d' % (size)
        self.ctypes_sizes[TypeKind.LONGLONG] = size
        self.ctypes_sizes[TypeKind.ULONGLONG] = size

        # FIXME : Float && http://en.wikipedia.org/wiki/Long_double
        size0 = util.get_cursor(tu, 'float_t').type.get_size() * 8
        size1 = util.get_cursor(tu, 'double_t').type.get_size() * 8
        size2 = util.get_cursor(tu, 'longdouble_t').type.get_size() * 8
        # 2014-01 stop generating crap.
        # 2015-01 reverse until better solution is found
        # the idea is that a you cannot assume a c_double will be same format as a c_long_double.
        # at least this pass size TU
        if size1 != size2:
            self.ctypes_typename[TypeKind.LONGDOUBLE] = 'c_long_double_t'
        else:
            self.ctypes_typename[TypeKind.LONGDOUBLE] = 'c_double'

        self.ctypes_sizes[TypeKind.FLOAT] = size0
        self.ctypes_sizes[TypeKind.DOUBLE] = size1
        self.ctypes_sizes[TypeKind.LONGDOUBLE] = size2

        # save the target pointer size.
        size = util.get_cursor(tu, 'pointer_t').type.get_size() * 8
        self.ctypes_sizes[TypeKind.POINTER] = size
        self.ctypes_sizes[TypeKind.NULLPTR] = size

        log.debug('ARCH sizes: long:%s longdouble:%s',
                  self.ctypes_typename[TypeKind.LONG],
                  self.ctypes_typename[TypeKind.LONGDOUBLE])
        return

    def get_ctypes_name(self, typekind):
        return self.ctypes_typename[typekind]

    def get_ctypes_size(self, typekind):
        return self.ctypes_sizes[typekind]

    def get_pointer_width(self):
        return self.ti.pointer_width

    def get_platform_triple(self):
        return self.ti.triple

    def parse_cursor(self, cursor):
        """Forward parsing calls to dedicated CursorKind Handlder"""
        return self.cursorkind_handler.parse_cursor(cursor)

    def parse_cursor_type(self, _cursor_type):
        """Forward parsing calls to dedicated TypeKind Handlder"""
        return self.typekind_handler.parse_cursor_type(_cursor_type)

    ###########################################################################

    ################

    def get_macros(self, text):
        if text is None:
            return
        text = "".join(text)
        # preprocessor definitions that look like macros with one or more
        # arguments
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
                # print "skip %s = %s" % (name, value)
                pass

    def get_result(self):
        # all of these should register()
        interesting = (typedesc.Typedef, typedesc.Enumeration, typedesc.EnumValue,
                       typedesc.Function, typedesc.Structure, typedesc.Union,
                       typedesc.Variable, typedesc.Macro, typedesc.Alias,
                       typedesc.FunctionType)
        # typedesc.Field) #???

        self.get_macros(self.cpp_data.get("functions"))
        # fix all objects after that all are resolved
        remove = []
        for _id, _item in self.all.items():
            if _item is None:
                log.warning('ignoring %s', _id)
                continue
            location = getattr(_item, "location", None)
            # FIXME , why do we get different location types
            if location and hasattr(location, 'file'):
                _item.location = location.file.name, location.line
                log.error('%s %s came in with a SourceLocation', _id, _item)

        for _x in remove:
            self.remove_registered(_x)

        # Now we can build the namespace.
        namespace = {}
        for i in self.all.values():
            if not isinstance(i, interesting):
                log.debug('ignoring %s', i)
                continue  # we don't want these
            name = getattr(i, "name", None)
            if name is not None:
                namespace[name] = i
        self.get_aliases(self.cpp_data.get("aliases"), namespace)

        result = []
        for i in self.all.values():
            if isinstance(i, interesting):
                result.append(i)

        log.debug("parsed items order: %s", result)
        return tuple(result)

    def interprete(self, expr):
        preprocess.exec_processed_macro(expr, self.interpreter_namespace)
