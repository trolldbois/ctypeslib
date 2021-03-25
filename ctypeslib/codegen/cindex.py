"""Augmented python-clang API: cache-friendly types and missing libclang bindings"""

import collections.abc as collections_abc
from clang import cindex
from ctypes import byref, c_int
import ctypes
from ctypeslib.codegen.cache import (
    cached,
    cached_property,
    cached_classmethod,
    cached_staticmethod,
)
from ctypeslib.codegen.hash import hash_value, hash_combine

from clang.cindex import *  # noqa


class SourceLocation(cindex.SourceLocation):
    """
    A SourceLocation represents a particular location within a source file.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._cached_instantiation = None

    def __hash__(self):
        return hash(self._get_instantiation())

    _super_get_instantiation = cindex.SourceLocation._get_instantiation

    # _get_instantiation is non-cachable since it is used in __hash__
    def _get_instantiation(self):
        if getattr(self, "_cached_instantiation", None) is None:
            self._cached_instantiation = self._super_get_instantiation()
        return self._cached_instantiation


cindex.SourceLocation = SourceLocation


class SourceRange(cindex.SourceRange):
    """
    A SourceRange describes a range of source locations within the source
    code.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._cached_start = None
        self._cached_end = None

    def __hash__(self):
        return hash_combine((self.start, self.end))

    # start is non-cachable since it is used in __hash__
    _super_start = cindex.SourceRange.start

    @property
    def start(self):
        """
        Return a SourceLocation representing the first character within a
        source range.
        """
        if getattr(self, "_cached_start", None) is None:
            self._cached_start = self._super_start
        return self._cached_start

    # end is non-cachable since it is used in __hash__
    _super_end = cindex.SourceRange.end

    @property
    def end(self):
        """
        Return a SourceLocation representing the last character within a
        source range.
        """
        if getattr(self, "_cached_end", None) is None:
            self._cached_end = self._super_end
        return self._cached_end


cindex.SourceRange = SourceRange


class Diagnostic(cindex.Diagnostic):
    """
    A Diagnostic is a single instance of a Clang diagnostic. It includes the
    diagnostic severity, the message, the location the diagnostic occurred, as
    well as additional source ranges and associated fix-it hints.
    """

    def __hash__(self):
        return hash_value(self.spelling)


cindex.Diagnostic = Diagnostic


class Cursor(cindex.Cursor):
    """
    The Cursor class represents a reference to an element within the AST. It
    acts as a kind of iterator.
    """

    def __hash__(self):
        return hash_value(self.hash)

    @cached()
    def get_tokens(self):
        """Obtain Token instances formulating that compose this Cursor.
        This is a generator for Token instances. It returns all tokens which
        occupy the extent this cursor occupies.
        """
        return cindex.TokenGroup.get_tokens(self._tu, self.extent)


cindex.Cursor = Cursor


class Type(cindex.Type):
    """
    The type of an element in the abstract syntax tree.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._cached_spelling = None

    def __hash__(self):
        return hash_value(self.spelling)

    _super_spelling = cindex.Type.spelling

    @property  # spelling is non-cachable since it is used in __hash__
    def spelling(self):
        """Retrieve the spelling of this Type."""
        if getattr(self, "_cached_spelling", None) is None:
            self._cached_spelling = self._super_spelling
        return self._cached_spelling


cindex.Type = Type


class TranslationUnit(cindex.TranslationUnit):
    """Represents a source code translation unit.
    This is one of the main types in the API. Any time you wish to interact
    with Clang's representation of a source file, you typically start with a
    translation unit.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._cached_spelling = None

    def __hash__(self):
        return hash_value(self.spelling)

    _super_spelling = cindex.TranslationUnit.spelling

    @property  # spelling is non-cachable since it is used in __hash__
    def spelling(self):
        """Get the original translation unit source file name."""
        if getattr(self, "_cached_spelling", None) is None:
            self._cached_spelling = self._super_spelling
        return self._cached_spelling


cindex.TranslationUnit = TranslationUnit


class File(cindex.File):
    """
    The File class represents a particular source file that is part of a
    translation unit.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._cached_name = None

    def __hash__(self):
        return hash_value(self.name)

    _super_name = cindex.File.name

    @property
    def name(self):
        """Return the complete file and path name of the file."""
        if getattr(self, "_cached_name", None) is None:
            self._cached_name = self._super_name
        return self._cached_name


cindex.File = File


class Token(cindex.Token):
    """Represents a single token from the preprocessor.
    Tokens are effectively segments of source code. Source code is first parsed
    into tokens before being converted into the AST and Cursors.
    Tokens are obtained from parsed TranslationUnit instances. You currently
    can't create tokens manually.
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self._cached_spelling = None

    def __hash__(self):
        return hash_combine((self._tu, self.spelling))

    _super_spelling = cindex.Token.spelling

    @property  # spelling is non-cachable since it is used in __hash__
    def spelling(self):
        """The spelling of this token.
        This is the textual representation of the token in source.
        """
        if getattr(self, "_cached_spelling", None) is None:
            self._cached_spelling = self._super_spelling
        return self._cached_spelling

    _super_cursor = cindex.Token.cursor

    @cached_property()
    def cursor(self):
        """The Cursor this Token corresponds to."""
        return self._super_cursor


cindex.Token = Token


# Missing functions and types from python-clang
class TargetInfo(cindex.ClangObject):
    @classmethod
    def from_translation_unit(self, tu):
        return TargetInfo(cindex.conf.lib.clang_getTranslationUnitTargetInfo(tu))

    @cached_property()
    def triple(self):
        return cindex.conf.lib.clang_TargetInfo_getTriple(self)

    @cached_property()
    def pointer_width(self):
        return int(cindex.conf.lib.clang_TargetInfo_getPointerWidth(self))

    def __del__(self):
        cindex.conf.lib.clang_TargetInfo_dispose(self)


class Config(cindex.Config):
    @cindex.CachedProperty
    def lib(self):
        lib = self.get_cindex_library()
        register_functions(lib, not Config.compatibility_check)
        Config.loaded = True
        return lib


# monkey_patch cindex.conf object Class
cindex.conf.__class__ = Config


_functionList = cindex.functionList + [
    ("clang_getTranslationUnitTargetInfo", [TranslationUnit], cindex.c_object_p),
    ("clang_TargetInfo_dispose", [TargetInfo]),
    (
        "clang_TargetInfo_getTriple",
        [TargetInfo],
        cindex._CXString,
        cindex._CXString.from_result,
    ),
    ("clang_TargetInfo_getPointerWidth", [TranslationUnit], ctypes.c_int),
]


def _monkey_patch_type(_type):
    if getattr(_type, "__module__", None) in (
        "clang.cindex",
        "ctypes",
    ) and isinstance(_type, type):
        if issubclass(_type, ctypes._Pointer):
            _type = ctypes.POINTER(_monkey_patch_type(_type._type_))
        elif issubclass(_type, ctypes._CFuncPtr):
            _type = _monkey_patch_funcptr(_type)
        else:
            _type = globals().get(_type.__name__, _type)
    return _type


_c_functype_cache = {}


def _monkey_patch_funcptr(funcptr):
    global _c_functype_cache
    argtypes = funcptr._argtypes_
    restype = funcptr._restype_
    flags = funcptr._flags_
    try:
        return _c_functype_cache[(restype, argtypes, flags)]
    except KeyError:
        if argtypes:
            patched_argtypes = tuple(map(_monkey_patch_type, argtypes))

        class CFunctionType(ctypes._CFuncPtr):
            _argtypes_ = patched_argtypes
            _restype_ = _monkey_patch_type(restype)
            _flags_ = flags

        _c_functype_cache[(restype, argtypes, flags)] = CFunctionType
        return CFunctionType


def _monkey_patch_func(func):
    if isinstance(func, type) and issubclass(func, ctypes._CFuncPtr):
        return _monkey_patch_funcptr(func)
    func.restype = _monkey_patch_type(func.restype)
    if func.argtypes:
        func.argtypes = tuple(map(_monkey_patch_type, func.argtypes))
    return func


def register_functions(lib, ignore_errors):
    """Register function prototypes with a libclang library instance.
    This must be called as part of library instantiation so Python knows how
    to call out to the shared library.
    """
    cindex.callbacks.update(
        {name: _monkey_patch_func(func) for name, func in cindex.callbacks.items()}
    )

    def register(item):
        cindex.register_function(lib, item, ignore_errors)
        func = getattr(lib, item[0])
        _monkey_patch_func(func)

    for f in _functionList:
        register(f)


__all__ = cindex.__all__ + [
    "TargetInfo"
]
