# -*- coding: utf-8 -*-
# ctypeslib package

from pkg_resources import get_distribution, DistributionNotFound
import ctypes
from ctypes.util import find_library
import os
import re
import sys
import warnings

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


def __find_clang_libraries():
    """ configure python-clang to use the local clang library """
    _libs = []
    # try default system name
    v0 = ["libclang", "clang"]
    # tries clang version 16 to 7
    v1 = ["clang-%d" % _ for _ in range(16, 6, -1)]
    # with the dotted form of clang 6.0 to 4.0
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


def clang_version():
    """Pull the clang C library version from the API"""
    # avoid loading the cindex API (cindex.conf.lib) to avoid version conflicts
    get_version = cindex.conf.get_cindex_library().clang_getClangVersion
    get_version.restype = ctypes.c_char_p
    version_string = get_version()
    version = 'Unknown'
    if version_string and len(version_string) > 0:
        version_groups = re.match(br'.+version ((\d+\.)?(\d+\.)?(\*|\d+))', version_string)
        if version_groups and len(version_groups.groups()) > 0:
            version = version_groups.group(1).decode()
    return version


def clang_py_version():
    """Return the python clang package version"""
    return __clang_py_version__


def __configure_clang_cindex():
    global __clang_py_version__
    __clang_py_version__ = get_distribution('clang').version
    # first try for a perfect match.
    __lib_filename = find_library("clang-" + __clang_py_version__)
    if __lib_filename is not None:
        cindex.Config.set_library_file(__lib_filename)
        return __lib_filename
    else:
        __libs = __find_clang_libraries()
        if len(__libs) > 0:
            __version, __filename = __libs[0]
            cindex.Config.set_library_file(__filename)
            return __filename
    return None


# check which clang python module is available
# check which clang library is available
try:
    from clang import cindex

    __clang_py_version__ = 'not-installed'
    _filename = __configure_clang_cindex()
    if _filename is None:
        warnings.warn("Could not find the clang library. please install llvm libclang", RuntimeWarning)
        # do not fail - maybe the user has a plan
    else:
        # set a warning if major versions differs.
        if clang_version().split('.')[0] != clang_py_version().split('.')[0]:
            clang_major = clang_version().split('.')[0]
            warnings.warn("Version of python-clang (%s) and clang C library (%s) are different. "
                          "Did you try pip install clang==%s.*" % (
                              clang_py_version(), clang_version(), clang_major), RuntimeWarning)
except ImportError:
    __clang_py_version__ = None
    warnings.warn("Could not find a version of python-clang installed. please pip install clang", RuntimeWarning)

from clang import cindex
from ctypeslib.codegen.codegenerator import translate, translate_files

__all__ = ['translate', 'translate_files', 'clang_version']
