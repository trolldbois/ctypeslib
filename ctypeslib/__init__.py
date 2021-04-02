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
    from clang import cindex
    # debug for python-haystack travis-ci
    v1 = ["clang-%d" % _ for _ in range(14, 6, -1)]
    v2 = ["clang-%f" % _ for _ in range(6, 3, -1)]
    v_list = v1 + v2 + ["clang-3.9", "clang-3.8", "clang-3.7"]
    for version in ["libclang", "clang"] + v_list:
        if find_library(version) is not None:
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
        return cindex.Config.library_file
except ImportError as e:
    print(e)


def translate(input_io, cfg=None):
    """
        Take a readable C like input and translate it to python.
    """
    import io
    from ctypeslib.codegen import clangparser, codegenerator, config
    from ctypeslib.codegen import util
    from ctypeslib.library import Library
    from ctypeslib import codegen
    cfg = cfg or config.CodegenConfig()
    flags = cfg.clang_opts
    cfg.preloaded_dlls = [Library(name, nm="nm") for name in cfg.preloaded_dlls]
    parser = clangparser.Clang_Parser(flags)
    if cfg.generate_comments:
        parser.activate_comment_parsing()
    # if cfg....:
    #     parser.activate_macros_parsing()
    # TODO need to handle open file / io ?
    parser.parse_string(input_io, )
    items = parser.get_result()
    # gen code
    ofi = io.StringIO()
    gen = codegenerator.Generator(ofi, cfg=cfg)
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
