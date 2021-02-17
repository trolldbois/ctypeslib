# -*- coding: utf-8 -*-
# ctypeslib package

from pkg_resources import get_distribution, DistributionNotFound
import os
import sys

try:
    _dist = get_distribution('ctypeslib2')
    # Normalize case for Windows systems
    # if you are in a virtualenv, ./local/* are aliases to ./*
    dist_loc = os.path.normcase(os.path.realpath(_dist.location))
    here = os.path.normcase(os.path.realpath(__file__))
    if not here.startswith(os.path.join(dist_loc, 'ctypeslib')):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = 'Please install this project with setup.py'
else:
    __version__ = _dist.version

# configure python-clang to use the local clang library
try:
    from ctypes.util import find_library
    # debug for python-haystack travis-ci
    v1 = ["clang-%d" % _ for _ in range(14, 6, -1)]
    v2 = ["clang-%f" % _ for _ in range(6, 3, -1)]
    v_list = v1 + v2 + ["clang-3.9", "clang-3.8", "clang-3.7"]
    for version in ["libclang", "clang"] + v_list:
        if find_library(version) is not None:
            from clang import cindex
            cindex.Config.set_library_file(find_library(version))
            break
    else:
        if os.name == "posix" and sys.platform == "darwin":
            # On darwin, consider that Xcode should be installed in its default path.
            from clang import cindex
            cindex.Config.set_library_file('/Applications/Xcode.app/Contents/Frameworks/libclang.dylib')

    def clang_version():
        return cindex.Config.library_file
except ImportError as e:
    print(e)


