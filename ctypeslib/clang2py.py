#!/usr/bin/env python3
import argparse
import logging
import os
import platform
import re
import subprocess
import six
import sys
import traceback

from ctypes import RTLD_LOCAL, RTLD_GLOBAL

import ctypeslib
from ctypeslib.codegen import typedesc
from ctypeslib.codegen.codegenerator import generate_code

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


class LibraryMeta(type):

    def __call__(cls, name, mode=RTLD_LOCAL, nm=None):

        if os.name == "nt":
            from ctypes import WinDLL
            # WinDLL does demangle the __stdcall names, so use that.
            return WinDLL(name, mode=mode)
        if os.path.exists(name) and mode != RTLD_GLOBAL and nm is not None:
            # Use 'nm' on Unixes to load native and cross-compiled libraries
            # (this is only possible if mode != RTLD_GLOBAL)
            return super().__call__(name, nm)
        from ctypes import CDLL
        from ctypes.util import find_library
        path = find_library(name)
        if path is None:
            # Maybe 'name' is not a library name in the linker style,
            # give CDLL a last chance to find the library.
            path = name
        return CDLL(path, mode=mode)


class Library(six.with_metaclass(LibraryMeta)):

    def __init__(self, filepath, nm):
        self.filepath = filepath
        self._name = os.path.basename(self.filepath)
        self.symbols = {}
        self._get_symbols(nm)

    # nm will print lines like this:
    # <addr> <kind> <name>
    def _get_symbols(self, nm):
        cmd = [nm, "--defined-only", "--extern-only", self.filepath]
        output = subprocess.check_output(cmd, universal_newlines=True)
        for line in output.split('\n'):
            fields = line.split(' ', 2)
            if len(fields) >= 3 and fields[1] == "T":
                self.symbols[fields[2]] = fields[0]

    def __getattr__(self, name):
        try:
            return self.symbols[name]
        except KeyError:
            pass
        raise AttributeError(name)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    local_platform_triple = "%s-%s" % (platform.machine(), platform.system())
    clang_opts = []
    files = None

    def windows_dlls(option, opt, value, parser):
        parser.values.dlls.extend(windows_dll_names)

    version = ctypeslib.__version__

    parser = argparse.ArgumentParser(prog='clang2py',
                                     description='Version %s. Generate python code from C headers' % (version))
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
                        default="cdefstu")

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
                        default="-")

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
                        default=None)

    parser.add_argument("-s", "--symbol",
                        dest="symbols",
                        metavar="SYMBOL",
                        action="append",
                        help="symbol to include "
                             "(if neither symbols nor expressions are specified,"
                             "everything will be included)",
                        default=None)

    parser.add_argument("-t", "--target",
                        dest="target",
                        help="target architecture (default: %s)" % local_platform_triple,
                        default=None)  # actually let clang alone decide.

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        dest="verbose",
                        help="verbose output",
                        default=False)
    parser.add_argument('-V', '--version',
                        action='version',
                        version="%(prog)s version " + version)

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

    # recognize - as stdin
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

    options = parser.parse_args()

    # handle stdin, just in case
    files = []
    for f in options.files:
        if f == sys.stdin:
            raise ValueError('stdin is not supported')
        files.append(f.name)
        f.close()
    # files = [f.name for f in options.files]
    if options.target is not None:
        clang_opts = ["-target", options.target]
    if options.clang_args is not None:
        clang_opts.extend(re.split("\s+", options.clang_args))

    level = logging.INFO
    if options.debug:
        level = logging.DEBUG
    elif options.quiet:
        level = logging.ERROR
    logging.basicConfig(level=level, stream=sys.stderr)

    if options.output == "-":
        stream = sys.stdout
        output_file = None
    else:
        stream = open(options.output, "w")
        output_file = stream

    if options.expressions:
        options.expressions = map(re.compile, options.expressions)

    if options.generate_comments:
        stream.write("# generated by 'clang2py'\n")
        stream.write("# flags '%s'\n" % " ".join(argv[1:]))

    known_symbols = {}

    # Preload libraries
    [Library(
        name,
        mode=RTLD_GLOBAL) for name in options.preload]

    # List exported symbols from libraries
    dlls = [Library(name, nm=options.nm) for name in options.dll]

    for name in options.modules:
        mod = __import__(name)
        for submodule in name.split(".")[1:]:
            mod = getattr(mod, submodule)
        for name, item in mod.__dict__.items():
            if isinstance(item, type):
                known_symbols[name] = mod.__name__

    type_table = {"a": [typedesc.Alias],
                  "c": [typedesc.Structure],
                  "d": [typedesc.Variable],
                  "e": [typedesc.Enumeration],  # , typedesc.EnumValue],
                  "f": [typedesc.Function],
                  "m": [typedesc.Macro],
                  "s": [typedesc.Structure],
                  "t": [typedesc.Typedef],
                  "u": [typedesc.Union],
                  }
    if options.kind:
        types = []
        for char in options.kind:
            try:
                typ = type_table[char]
                types.extend(typ)
            except KeyError:
                parser.error("%s is not a valid choice for a TYPEKIND" % char)
        options.kind = tuple(types)

    try:
        generate_code(files, stream,
                      symbols=options.symbols,
                      expressions=options.expressions,
                      verbose=options.verbose,
                      generate_comments=options.generate_comments,
                      generate_docstrings=options.generate_docstrings,
                      generate_locations=options.generate_locations,
                      filter_location=not options.generate_includes,
                      known_symbols=known_symbols,
                      searched_dlls=dlls,
                      preloaded_dlls=options.preload,
                      types=options.kind,
                      flags=clang_opts)
    except:
        if output_file is not None:
            output_file.close()
            os.remove(options.output)
        raise
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # return non-zero exit status in case of an unhandled exception
        traceback.print_exc()
        sys.exit(1)
