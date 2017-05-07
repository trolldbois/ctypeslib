"""A module for dynamic, incremental ctypes code generation.

See the 'include' function for usage information.
"""

from __future__ import print_function
import sys
import os
import time
import bz2
import cPickle
import tempfile
try:
    # md5 is deprecated in Python 2.5, so use hashlib if available
    from hashlib import md5
except ImportError:
    from md5 import new as md5

import ctypes
import ctypeslib
from ctypeslib.codegen import gccxmlparser, codegenerator, typedesc

gen_dir = os.path.join(tempfile.gettempdir(), "gccxml_cache")
if not os.path.exists(gen_dir):
    os.mkdir(gen_dir)

# TODO:
#
# Clean up the names Generator and CodeGenerator.
#


def include(code, persist=True, compilerflags=None):
    """This function replaces the *calling module* with a dynamic
    module that generates code on demand.  The code is generated from
    type descriptions that are created by gccxml compiling the C code
    'code'.

    If <persist> is True, generated code is appended to the module's
    source code, otherwise the generated code is executed and then
    thrown away.

    The calling module must load all the shared libraries that it uses
    *BEFORE* this function is called.

    NOTE:
     - the calling module MUST contain 'from ctypes import *',
       and, on windows, also 'from ctypes.wintypes import *'.
    """
    compilerflags = compilerflags or ["-c"]
    # create a hash for the code, and use that as basename for the
    # files we have to create
    fullcode = "/* compilerflags: %r */\n%s" % (compilerflags, code)
    hashval = md5(fullcode).hexdigest()

    fnm = os.path.abspath(os.path.join(gen_dir, hashval))
    h_file = fnm + ".h"
    xml_file = fnm + ".xml"
    tdesc_file = fnm + ".typedesc.bz2"

    if not os.path.exists(h_file):
        open(h_file, "w").write(fullcode)
    if is_newer(h_file, tdesc_file):
        if is_newer(h_file, xml_file):
            print("# Compiling into...", xml_file, file=sys.stderr)
            from ctypeslib import h2xml
            h2xml.compile_to_xml(["h2xml",
                                  "-I", os.path.dirname(fnm), "-q",
                                  h_file,
                                  "-o", xml_file] + list(compilerflags))
        if is_newer(xml_file, tdesc_file):
            print("# Parsing XML file and compressing type descriptions...", file=sys.stderr)
            decls = gccxmlparser.parse(xml_file)
            ofi = bz2.BZ2File(tdesc_file, "w")
            data = cPickle.dump(decls, ofi, -1)
            os.remove(xml_file)  # not needed any longer.

    frame = sys._getframe(1)
    glob = frame.f_globals
    name = glob["__name__"]
    mod = sys.modules[name]
    sys.modules[name] = DynamicModule(mod, tdesc_file, persist=persist)


def is_newer(source, target):
    """Return true if 'source' exists and is more recently modified than
    'target', or if 'source' exists and 'target' doesn't.  Return false if
    both exist and 'target' is the same age or younger than 'source'.
    Raise ValueError if 'source' does not exist.
    """
    if not os.path.exists(source):
        raise ValueError("file '%s' does not exist" % source)
    if not os.path.exists(target):
        return 1

    from stat import ST_MTIME
    mtime1 = os.stat(source)[ST_MTIME]
    mtime2 = os.stat(target)[ST_MTIME]

    return mtime1 > mtime2

################################################################


class DynamicModule(object):

    def __init__(self, mod, tdesc_file, persist):
        # We need to keep 'mod' alive, otherwise it would set the
        # values of it's __dict__ to None when it's deleted.
        self.__dict__ = mod.__dict__
        self.__orig_module__ = mod
        fnm = os.path.abspath(self.__file__)
        if fnm.endswith(".pyc") or fnm.endswith(".pyo"):
            fnm = fnm[:-1]
        if persist and not os.path.exists(fnm):
            raise ValueError("source file %r does not exist" % fnm)
        self.__code_generator_args = (fnm, tdesc_file, mod.__dict__, persist)
        self.__code_generator = None
        self.__tdesc_file = tdesc_file

    @property
    def _code_generator(self):
        if not self.__code_generator:
            self.__code_generator = CodeGenerator(*self.__code_generator_args)
        return self.__code_generator

    def __repr__(self):
        return "<DynamicModule(%r) %r from %r>" % (
            self.__tdesc_file, self.__name__, self.__file__)

    def __getattr__(self, name):
        if not name.startswith("__") and not name.endswith("__"):
            val = self._code_generator.generate(name)
# print "# Generating", name
            self.__dict__[name] = val
            return val
        raise AttributeError(name)

################


class UnknownSymbol(Exception):
    pass


class Generator(codegenerator.Generator):

    """A subclass of codegenerator, specialized for our requirements:

    - libraries are already loaded in the module, won't be loaded by
    the code we generate.

    - no need to generate symbols that are already present in
    self.namespace
    """

    def need_CLibraries(self):
        pass
    # Libraries are already loaded in the module, no code needed
    need_WinLibraries = need_CLibraries

    def generate(self, item):
        if isinstance(item, typedesc.StructureHead):
            name = getattr(item.struct, "name", None)
        else:
            name = getattr(item, "name", None)
        if name in self.namespace:
            return
        super(Generator, self).generate(item)

    def get_sharedlib(self, dllname, cc):
        # XXX This should assert that the correct calling convention
        # is used.
        dll = self.searched_dlls[dllname]
        if os.name == "nt":
            if cc == "stdcall":
                assert isinstance(
                    dll, ctypes.WinDLL), "wrong calling convention"
            else:
                assert not isinstance(
                    dll, ctypes.WinDLL), "wrong calling convention"
        return dllname

    def find_dllname(self, func):
        # Find which of the libraries in 'searched_dlls' exports the
        # function 'func'.  Return name of library or None.
        name = func.name
        for dllname, dll in self.searched_dlls.items():
            try:
                getattr(dll, name)
            except AttributeError:
                pass
            else:
                return dllname
        return None

    def Function(self, func):
        # XXX Not sure this is approach makes sense.
        super(Generator, self).Function(func)
        restype = self.type_name(func.returns)
        errcheck = self.namespace.get("%s_errcheck" % restype, None)
        if errcheck is not None:
            print("%s.errcheck = %s_errcheck" % (
                func.name, restype), file=self.stream)


class CodeGenerator(object):

    """Dynamic, incremental code generation.  The generated code is
    executed in the dictionary <ns>, and appended to the file
    specified by <src_path>, if <persist> is True."""
    output = None

    def __init__(self, src_path, tdesc_file, ns, persist):
        # We should do lazy initialization, so that all this stuff is
        # only done when really needed because we have to generate
        # something.
        if persist:
            # We open the file in universal newline mode, read the
            # contents to determine the line endings.  All this to
            # avoid creating files with mixed line endings!
            ifi = open(src_path, "U")
            ifi.read()
            ifi.close()
            self._newlines = ifi.newlines or "\n"
            self.output = open(src_path, "ab")
        data = open(tdesc_file, "rb").read()
        decls = cPickle.loads(bz2.decompress(data))
        names = {}
        self.namespace = ns
        done = set()
        for i in decls:
            try:
                name = i.name
            except AttributeError:
                continue
            if name in ns:
                done.add(i)
                if isinstance(i, typedesc.Structure):
                    done.add(i.get_head())
                    done.add(i.get_body())
            names[name] = i
        self.decls = names

        dlls = dict([o for o in ns.items()
                     if isinstance(o[1], ctypes.CDLL) and not isinstance(o[1], ctypes.PyDLL)])
        self.codegenerator = Generator(output=None,
                                       known_symbols=None,
                                       searched_dlls=dlls)
        self.codegenerator.errcheck = ns.get("errcheck")
        self.codegenerator.done |= done
        self.codegenerator.namespace = self.namespace

        self.imports = ""
        self.code = ""

    def generate(self, name):
        # Incremental code generation for one name.
        try:
            item = self.decls[name]
        except KeyError:
            raise UnknownSymbol(name)
        self.codegenerator.generate_items([item])

        # Could as well call getvalue(), and create a new StringIO
        # instance for .imports and .stream.
        imports = self.codegenerator.imports.getvalue()[len(self.imports):]
        self.imports += imports
        code = self.codegenerator.stream.getvalue()[len(self.code):]
        self.code += code

        code = imports + code

        exec(code, self.namespace)
        # I guess when this fails, it means that the dll exporting
        # this function is not in searched_dlls.  So we should
        # probably raise a different exception.

        if self.output is not None:
            code = code.replace("\n", self._newlines)
            self.output.write(code)
        try:
            return self.namespace[name]
        except KeyError:
            raise UnknownSymbol(name)

################################################################
