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
    from ctypeslib.codegen import cindex
    # debug for python-haystack travis-ci
    v1 = ["clang-%d" % _ for _ in range(14, 6, -1)]
    v2 = ["clang-%f" % _ for _ in range(6, 3, -1)]
    v_list = v1 + v2 + ["clang-3.9", "clang-3.8", "clang-3.7"]
    for version in ["libclang", "clang"] + v_list:
        if find_library(version) is not None:
            from ctypeslib.codegen import cindex
            cindex.Config.set_library_file(find_library(version))
            break
    else:
        if os.name == "posix" and sys.platform == "darwin":
            # On darwin, consider either Xcode or CommandLineTools.
            for f in ['/Applications/Xcode.app/Contents/Frameworks/libclang.dylib',
                      '/Library/Developer/CommandLineTools/usr/lib/libclang.dylib']:
                if os.path.exists(f):
                    cindex.Config.set_library_file(f)

    def clang_version():
        from ctypeslib.codegen import cindex
        return cindex.Config.library_file
except ImportError as e:
    print(e)


def translate(input_io, flags=None, dlls=None, full_parsing=False):
    """Take a readable C like input and translate it to python.
    """
    import io
    import ctypes
    from ctypeslib.codegen import clangparser, codegenerator
    from ctypeslib.codegen import util
    from ctypeslib.library import Library
    from ctypeslib import codegen
    flags = flags or []
    dlls = dlls or []
    dlls = [Library(name, nm="nm") for name in dlls]
    parser = clangparser.Clang_Parser(flags)
    if full_parsing:
        parser.activate_macros_parsing()
        parser.activate_comment_parsing()
    # TODO need to handle open file / io ?
    parser.parse_string(input_io, )
    items = parser.get_result()
    # gen code
    cross_arch = '-target' in ' '.join(flags)
    ofi = io.StringIO()
    gen = codegenerator.Generator(ofi, searched_dlls=dlls, cross_arch=cross_arch)
    gen.generate_headers(parser)
    gen.generate_code(items)
    ofi.seek(0)
    ignore_coding = ofi.readline()
    # exec ofi.getvalue() in namespace
    output = ''.join(ofi.readlines())
    namespace = {}
    exec(output, namespace)
    return util.ADict(namespace)


__all__ = ['translate']
