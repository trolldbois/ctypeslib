#!/usr/bin/env python3
import argparse
import logging
import os
import platform
import re
import sys
import tempfile
import traceback

from ctypes import RTLD_GLOBAL

import ctypeslib
from ctypeslib.codegen import typedesc, config
from ctypeslib.codegen.codegenerator import translate_files
from ctypeslib.library import Library
from ctypeslib import clang_version, clang_py_version

################################################################
windows_dll_names = """\
imagehlp
user32
kernel32
gdi32
advapi32
oleaut32
ole32
imm32
comdlg32
shell32
version
winmm
mpr
winscard
winspool.drv
urlmon
crypt32
cryptnet
ws2_32
opengl32
glu32
mswsock
msvcrt
msimg32
netapi32
rpcrt4""".split()


# rpcndr
# ntdll

def _is_typedesc(item):
    for c in item:
        if c not in 'acdefmstu':
            raise argparse.ArgumentTypeError("types choices are 'acdefmstu'")
    return item


class Input:
    def __init__(self, options):
        self.files = []
        self._stdin = None
        for f in options.files:
            # stdin case
            if f == sys.stdin:
                _stdin = tempfile.NamedTemporaryFile(mode="w", prefix="stdin", suffix=".c", delete=False)
                _stdin.write(f.read())
                f = _stdin
            self.files.append(f.name)
            f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._stdin:
            os.remove(self._stdin.name)
        return False


class Output:
    def __init__(self, options):
        # handle output
        if options.output == "-":
            self.stream = sys.stdout
            self.output_file = None
        else:
            self.stream = open(options.output, "w")
            self.output_file = self.stream

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self.output_file is not None:
            self.output_file.close()
            os.remove(self.options.output)
        # If an exception is supplied, and the method wishes to suppress the exception
        # (i.e., prevent it from being propagated), it should return a true value.
        return False


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    cfg = config.CodegenConfig()
    cfg.local_platform_triple = "%s-%s" % (platform.machine(), platform.system())
    cfg.known_symbols = {}
    cfg.searched_dlls = []
    cfg.clang_opts = []
    files = None

    def windows_dlls(option, opt, value, parser):
        parser.values.dlls.extend(windows_dll_names)

    cfg.version = ctypeslib.__version__

    parser = argparse.ArgumentParser(prog='clang2py',
                                     description='Version %s. Generate python code from C headers' % cfg.version)
    parser.add_argument("-c", "--comments",
                        dest="generate_comments",
                        action="store_true",
                        help="include source doxygen-style comments",
                        default=False)
    parser.add_argument("-d", "--doc",
                        dest="generate_docstrings", action="store_true",
                        help="include docstrings containing C prototype and source file location",
                        default=False)
    parser.add_argument("--debug",
                        action="store_const",
                        const=True,
                        help='setLevel to DEBUG')
    parser.add_argument("-e", "--show-definition-location",
                        dest="generate_locations",
                        action="store_true",
                        help="include source file location in comments",
                        default=False)
    parser.add_argument("-k", "--kind",
                        action="store",
                        dest="kind", help="kind of type descriptions to include: "
                                          "a = Alias,\n"
                                          "c = Class,\n"
                                          "d = Variable,\n"
                                          "e = Enumeration,\n"
                                          "f = Function,\n"
                                          "m = Macro, #define\n"
                                          "s = Structure,\n"
                                          "t = Typedef,\n"
                                          "u = Union\n"
                                          "default = 'cdefstu'\n",
                        metavar="TYPEKIND",
                        default="cdefstu",
                        type=_is_typedesc)

    parser.add_argument("-i", "--includes",
                        dest="generate_includes",
                        action="store_true",
                        help="include declaration defined outside of the sourcefiles",
                        default=False)

    parser.add_argument("-l", "--include-library",
                        dest="dll",
                        help="library to search for exported functions. Add multiple times if required",
                        action="append",
                        default=[])

    if os.name in ("ce", "nt"):
        default_modules = ["ctypes.wintypes"]
    else:
        default_modules = []  # ctypes is already imported

    parser.add_argument("-m", "--module",
                        dest="modules",
                        metavar="module",
                        help="Python module(s) containing symbols which will "
                             "be imported instead of generated",
                        action="append",
                        default=default_modules)

    parser.add_argument("--nm",
                        dest="nm",
                        default="nm",
                        help="nm program to use to extract symbols from libraries")

    parser.add_argument("-o", "--output",
                        dest="output",
                        help="output filename (if not specified, standard output will be used)",
                        default="-", )
    # type=argparse.FileType('w'))

    parser.add_argument("-p", "--preload",
                        dest="preload",
                        metavar="DLL",
                        help="dll to be loaded before all others (to resolve symbols)",
                        action="append",
                        default=[])

    parser.add_argument("-q", "--quiet",
                        action="store_const",
                        const="quiet",
                        help="Shut down warnings and below",
                        default=False)

    parser.add_argument("-r", "--regex",
                        dest="expressions",
                        metavar="EXPRESSION",
                        action="append",
                        help="regular expression for symbols to include "
                             "(if neither symbols nor expressions are specified,"
                             "everything will be included)",
                        default=[])

    parser.add_argument("-s", "--symbol",
                        dest="symbols",
                        metavar="SYMBOL",
                        action="append",
                        help="symbol to include "
                             "(if neither symbols nor expressions are specified,"
                             "everything will be included)",
                        default=[])

    parser.add_argument("-t", "--target",
                        dest="target",
                        help="target architecture (default: %s)" % cfg.local_platform_triple,
                        default=None)  # actually let clang alone decide.

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        dest="verbose",
                        help="verbose output",
                        default=False)
    parser.add_argument('-V', '--version',
                        action='version',
                        version="versions - %(prog)s:" + "%s clang:%s python-clang:%s" % (cfg.version, clang_version(),
                                                                                          clang_py_version()))

    parser.add_argument("-w",
                        action="store",
                        default=windows_dlls,
                        help="add all standard windows dlls to the searched dlls list")

    parser.add_argument("-x", "--exclude-includes",
                        action="store_true",
                        default=False,
                        help="Parse object in sources files only. Ignore includes")

    parser.add_argument("--show-ids", dest="showIDs",
                        help="Don't compute cursor IDs (very slow)",
                        default=False)

    parser.add_argument("--max-depth", dest="maxDepth",
                        help="Limit cursor expansion to depth N",
                        metavar="N",
                        type=int,
                        default=None)

    parser.add_argument("--validate", dest="validate",
                        help="validate the python code is correct",
                        type=bool,
                        default=True)

    # FIXME recognize - as stdin
    # we do NOT support stdin
    parser.add_argument("files", nargs="+",
                        help="source filenames. stdin is not supported",
                        type=argparse.FileType('r'))

    parser.add_argument("--clang-args",
                        action="store",
                        default=None,
                        required=False,
                        help="clang options, in quotes: --clang-args=\"-std=c99 -Wall\"",
                        type=str)

    parser.epilog = """Cross-architecture: You can pass target modifiers to clang.
    For example, try --clang-args="-target x86_64" or "-target i386-linux" to change the target CPU arch."""

    options = parser.parse_args(argv)

    # cfg is the CodegenConfig, not the runtime config.
    level = logging.INFO
    if options.debug:
        level = logging.DEBUG
    elif options.quiet:
        level = logging.ERROR
    logging.basicConfig(level=level, stream=sys.stderr)

    # capture codegen options in config
    cfg.parse_options(options)

    # handle input files, and outputs
    from ctypeslib.codegen.handler import InvalidTranslationUnitException
    try:
        with Input(options) as inputs, Output(options) as outputs:
            # start codegen
            if cfg.generate_comments:
                outputs.stream.write("# generated by 'clang2py'\n")
                outputs.stream.write("# flags '%s'\n" % " ".join(argv[1:]))

            # Preload libraries
            # [Library(name, mode=RTLD_GLOBAL) for name in options.preload]

            translate_files(inputs.files, outputs.stream, cfg)
    except InvalidTranslationUnitException:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        # return non-zero exit status in case of an unhandled exception
        traceback.print_exc()
        sys.exit(1)
