# -*- coding: utf-8 -*-
# ctypeslib package

from pkg_resources import get_distribution, DistributionNotFound
import os
import sys

try:
    __dist = get_distribution('ctypeslib2')
    # Normalize case for Windows systems
    # if you are in a virtualenv, ./local/* are aliases to ./*
    __dist_loc = os.path.normcase(os.path.realpath(__dist.location))
    __here = os.path.normcase(os.path.realpath(__file__))
    if not __here.startswith(os.path.join(__dist_loc, 'ctypeslib')):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = 'Please install the latest version of this python package'
else:
    __version__ = __dist.version

# configure python-clang to use the local clang library
from ctypes.util import find_library


def __find_clang_libraries():
    _libs = []
    # try default system name
    v0 = ["libclang", "clang"]
    # tries clang version 14 to 3
    v1 = ["clang-%d" % _ for _ in range(14, 6, -1)]
    # with the dotted form of clang 6 to 4
    v2 = ["clang-%.1f" % _ for _ in range(6, 3, -1)]
    # clang 3 supported versions
    v3 = ["clang-3.9", "clang-3.8", "clang-3.7"]
    v_list = v0 + v1 + v2 + v3
    for _version in v_list:
        _filename = find_library(_version)
        if _filename:
            _libs.append((_version, _filename))
    # On darwin, also consider either Xcode or CommandLineTools.
    if os.name == "posix" and sys.platform == "darwin":
        for _ in ['/Library/Developer/CommandLineTools/usr/lib/libclang.dylib',
                  '/Applications/Xcode.app/Contents/Frameworks/libclang.dylib',
                  ]:
            if os.path.exists(_):
                _libs.insert(0, (_, _))
    return _libs


# check which clang python module is available, if any
try:
    from clang import cindex
    __clang_py_version__ = get_distribution('clang').version
    # first try for a perfect match.
    __lib_filename = find_library("clang-" + __clang_py_version__)
    if __lib_filename is not None:
        cindex.Config.set_library_file(__lib_filename)
    else:
        __libs = __find_clang_libraries()
        if len(__libs) > 0:
            __version, __filename = __libs[0]
            cindex.Config.set_library_file(__filename)
except ImportError:
    __clang_py_version__ = None


def clang_version():
    return cindex.Config.library_file


def clang_py_version():
    return __clang_py_version__


from clang import cindex
from ctypeslib.codegen.codegenerator import translate, translate_files

__all__ = ['translate', 'translate_files', 'clang_version']
