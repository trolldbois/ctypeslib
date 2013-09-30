#!/usr/bin/python -E
import argparse 
import logging
import os
import re
import sys

from ctypeslib.codegen.codegenerator import generate_code
from ctypeslib.codegen import typedesc

log = logging.getLogger('clang2py')

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

##rpcndr
##ntdll

def main(argv=None):
    if argv is None:
        argv = sys.argv

    def windows_dlls(option, opt, value, parser):
        parser.values.dlls.extend(windows_dll_names)

    parser = argparse.ArgumentParser(prog='clang2py', 
                 description='generate python ABI code from C code')
    parser.add_argument("--debug", dest="debug", action="store_const", 
                 const=True, help='setLevel to DEBUG')
    parser.add_argument("-c", dest="generate_comments", action="store_true", 
                 help="include source doxygen-style comments", default=False)
    parser.add_argument("-d", dest="generate_docstrings", action="store_true",
                 help="include docstrings containing C prototype and source file location",
                 default=False)
    parser.add_argument("-e", dest="generate_locations", action="store_true", 
                 help="include source file location in comments", default=False)
    parser.add_argument("-k", action="store",
                      dest="kind", help="kind of type descriptions to include: "
                        "a = Alias,"
                        "d = Variable,"
                        "e = Enumeration,"
                        "f = Function,"
                        "m = Macro, #define"
                        "s = Records, Structure,Union,Class "
                        "t = Typedef,",
                      metavar="TYPEKIND",
                      default="adefmst")

    parser.add_argument("-l",
                      dest="dlls",
                      help="libraries to search for exported functions",
                      action="append",
                      default=[])

    parser.add_argument("-o",
                      dest="output",
                      help="output filename (if not specified, standard output will be used)",
                      default="-")

    parser.add_argument("-r",
                      dest="expressions",
                      metavar="EXPRESSION",
                      action="append",
                      help="regular expression for symbols to include "
                      "(if neither symbols nor expressions are specified,"
                      "everything will be included)",
                      default=None)

    parser.add_argument("-s",
                      dest="symbols",
                      metavar="SYMBOL",
                      action="append",
                      help="symbol to include "
                      "(if neither symbols nor expressions are specified,"
                      "everything will be included)",
                      default=None)

    parser.add_argument("-v",
                      action="store_true",
                      dest="verbose",
                      help="verbose output",
                      default=False)

    parser.add_argument("-w",
                      action="store",
                      default=windows_dlls,
                      help="add all standard windows dlls to the searched dlls list")

    if os.name in ("ce", "nt"):
        default_modules = ["ctypes.wintypes" ]
    else:
        default_modules = [ ] # ctypes is already imported

    parser.add_argument("-m",
                      dest="modules",
                      metavar="module",
                      help="Python module(s) containing symbols which will "
                      "be imported instead of generated",
                      action="append",
                      default=default_modules)

    parser.add_argument("--preload",
                      dest="preload",
                      metavar="DLL",
                      help="dlls to be loaded before all others (to resolve symbols)",
                      action="append",
                      default=[])

    parser.add_argument("--show-ids", dest="showIDs",
                      help="Don't compute cursor IDs (very slow)",
                      default=False)

    parser.add_argument("--max-depth", dest="maxDepth",
                      help="Limit cursor expansion to depth N",
                      metavar="N", type=int, default=None)

    parser.add_argument("files", nargs="+",
                      help="source filenames", type=argparse.FileType('r'))

    #parser.add_argument("clang-opts", required=False, help="clang options", type=str)


    parser.epilog = '''About clang-args:     You can pass modifier to clang after your file name.
    For example, try "-target x86_64" or "-target i386-linux" as the last argument to change the target CPU arch.''' 
    
    options,clang_opts = parser.parse_known_args()
    files = [f.name for f in options.files]

    level=logging.INFO
    if options.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level, stream=sys.stderr)
    
    if options.output == "-":
        stream = sys.stdout
    else:
        stream = open(options.output, "w")

    if options.expressions:
        options.expressions = map(re.compile, options.expressions)

    if options.generate_comments:
        stream.write("# generated by 'clang2py'\n")
        stream.write("# flags '%s'\n" % " ".join(argv[1:]))

    known_symbols = {}

    from ctypes import CDLL, RTLD_LOCAL, RTLD_GLOBAL
    from ctypes.util import find_library

    def load_library(name, mode=RTLD_LOCAL):
        if os.name == "nt":
            from ctypes import WinDLL
            # WinDLL does demangle the __stdcall names, so use that.
            return WinDLL(name, mode=mode)
        path = find_library(name)
        if path is None:
            # Maybe 'name' is not a library name in the linker style,
            # give CDLL a last chance to find the library.
            path = name
        return CDLL(path, mode=mode)
    
    preloaded_dlls = [load_library(name, mode=RTLD_GLOBAL) for name in options.preload]
    
    dlls = [load_library(name) for name in options.dlls]

    for name in options.modules:
        mod = __import__(name)
        for submodule in name.split(".")[1:]:
            mod = getattr(mod, submodule)
        for name, item in mod.__dict__.iteritems():
            if isinstance(item, type):
                known_symbols[name] = mod.__name__

    if options.kind:
        types = []
        for char in options.kind:
            typ = {"a": [typedesc.Alias],
                   "d": [typedesc.Variable],
                   "e": [typedesc.Enumeration, typedesc.EnumValue],
                   "f": [typedesc.Function],
                   "m": [typedesc.Macro],
                   "s": [typedesc.Structure],
                   "t": [typedesc.Typedef],
                   }[char]
            types.extend(typ)
        options.kind = tuple(types)

    generate_code(files, stream,
                  symbols=options.symbols,
                  expressions=options.expressions,
                  verbose=options.verbose,
                  generate_comments=options.generate_comments,
                  generate_docstrings=options.generate_docstrings,
                  generate_locations=options.generate_locations,
                  known_symbols=known_symbols,
                  searched_dlls=dlls,
                  preloaded_dlls=options.preload,
                  types=options.kind,
                  flags=clang_opts)


if __name__ == "__main__":
    #sys.exit(main())
    main()
