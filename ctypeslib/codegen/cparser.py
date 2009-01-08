import sys, os, re, tempfile, linecache
import gccxmlparser, typedesc
import subprocess # the subprocess module is required

try:
    set
except NameError:
    from sets import Set as set

if sys.platform == "win32":

    def _locate_gccxml():
        import _winreg
        for subkey, valuename in [
            (r"Software\Kitware\gccxml 0.9.0", ""),
            (r"Software\Kitware\GCCXMLComplete 0.9.0", ""),
            (r"Software\gccxml", "loc"),
            (r"Software\Kitware\GCC_XML", "loc"),
            ]:
            for root in (_winreg.HKEY_CURRENT_USER, _winreg.HKEY_LOCAL_MACHINE):
                try:
                    hkey = _winreg.OpenKey(root, subkey, 0, _winreg.KEY_READ)
                except WindowsError, detail:
                    if detail.errno != 2:
                        raise
                else:
                    return _winreg.QueryValueEx(hkey, valuename)[0] + r"\bin"

    loc = _locate_gccxml()
    if loc:
        os.environ["PATH"] = loc

class CompilerError(Exception):
    pass

class IncludeParser(object):
    def __init__(self, options):
        """
        options must be an object having these attributes:
          verbose - integer
          flags - sequence of strings
          keep_temporary_files - true if temporary files should not be deleted
          cpp_symbols - whether to include preprocessor symbols in the XML file
          xml_file - pathname of output file (may be None)
        """
        self.options = options
        self.excluded = set()
            
    def create_source_file(self, lines, ext=".cpp"):
        "Create a temporary file, write lines to it, and return the filename"
        fd, fname = tempfile.mkstemp(ext, text=True)
        stream = os.fdopen(fd, "w")
        if lines:
            for line in lines:
                stream.write("%s\n" % line)
        stream.close()
        return fname

    def compile_and_dump(self, lines=None):
        """Create a temporary source file, dump preprocessor
        definitions, and remove the source file again."""
        fname = self.create_source_file(lines)
        try:
            args = ["gccxml", "--preprocess", "-dM", fname]
            if lines and self.options.flags:
                args.extend(self.options.flags)
            if self.options.verbose:
                print >> sys.stderr, "running:", " ".join(args)
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
            data, err = proc.communicate()
        finally:
            if not self.options.keep_temporary_files:
                os.remove(fname)
            else:
                print >> sys.stderr, "Info: file '%s' not removed" % fname
        return [line[len("#define "):]
                for line in data.splitlines()
                if line.startswith("#define ")]

    def create_xml(self, lines, xmlfile):
        """Create a temporary source file, 'compile' with gccxml to an
        xmlfile, and remove the source file again."""
        fname = self.create_source_file(lines)
        args = ["gccxml", fname]
        if xmlfile is not None:
            args.append("-fxml=%s" % xmlfile)
        if self.options.flags:
            args.extend(self.options.flags)
        try:
            if self.options.verbose:
                print >> sys.stderr, "running:", " ".join(args)
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
            data, err = proc.communicate()
            retcode = proc.wait()
            if retcode:
                raise CompilerError(err)
        finally:
            if not self.options.keep_temporary_files:
                os.remove(fname)
            else:
                print >> sys.stderr, "Info: file '%s' not removed" % fname

    def try_create_xml(self, lines, xmlfile):
        """Create a temporary source file, 'compile' with gccxml to an
        xmlfile, and remove the source file again."""
        fname = self.create_source_file(lines)
        args = ["gccxml", fname]
        args.append("-fxml=%s" % xmlfile)
        if self.options.flags:
            args.extend(self.options.flags)

        if self.options.verbose:
            print >> sys.stderr, "running:", " ".join(args)
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE)
        data, err = proc.communicate()
        retcode = proc.wait()
        invalid_symbols = set()
        if retcode:
            invalid_symbols = self.parse_compiler_errors(err.splitlines())
            os.remove(fname)
        return invalid_symbols

    def parse_compiler_errors(self, lines):
        pat = re.compile(r"(.*\.cpp):(\d+):(.*)")
        invalid_symbols = set()
        for line in lines:
            match = pat.search(line)
            if match:
                fnm, lineno, errmsg = match.groups()
                if re.match(r"\d+:", errmsg):
                    errmsg = errmsg.split(":", 1)[1]
                src_line = linecache.getline(fnm, int(lineno)).rstrip()
                is_define = re.match(r"^  DEFINE\((.*)\);$", src_line)
                if is_define:
                    sym = is_define.group(1)
                    if sym not in invalid_symbols:
                        invalid_symbols.add(is_define.group(1))
        return invalid_symbols

    def get_defines(self, include_files):
        """'Compile' an include file with gccxml, and return a
        dictionary of preprocessor definitions.  Empty and compiler
        internal definitions are not included."""
        # compiler internal definitions
        lines = self.compile_and_dump()
        predefined = [line.split(None, 1)[0]
                      for line in lines]
        # all definitions
        code = ['#include "%s"' % fname for fname in include_files]
        lines = self.compile_and_dump(code)
        defined = [line.split(None, 1)
                   for line in lines]
        # remove empty and compiler internal definitions
        defined = [pair for pair in defined
                   if len(pair) == 2 and pair[0] not in predefined]

        return dict(defined)

    wordpat = re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")
    def is_excluded(self, name, value):
        INVALID_CHARS = "=/{}&;"
        if "(" in name:
            return "IS_FUNCTION"
        if name in self.excluded:
            return "excluded"
        if value[0] in INVALID_CHARS or value[-1] in INVALID_CHARS:
            return "cannot be a value"
        if self.wordpat.match(name) and self.wordpat.match(value):
            # aliases are handled later, when (and if!) the rhs is known
            return "IS_ALIAS"
        return False

    def filter_definitions(self, defines):
        """Return a dict of aliases, a dict of fucntion-like macros, and
        another dict of constants and literals"""
        result = {}
        aliases = {}
        functions = {}
        excluded = {}
        for name, value in defines.iteritems():
            why = self.is_excluded(name, value)
            if not why:
                result[name] = value
            elif why == "IS_ALIAS":
                aliases[name] = value
            elif why == "IS_FUNCTION":
                functions[name] = value
            else:
                excluded[name] = value
        return aliases, functions, excluded, result

    ################################################################

    def find_types(self, include_files, defines):
        for i in range(20):
            source = []
            for fname in include_files:
                source.append('#include "%s"' % fname)
            source.append("#define DECLARE(sym) template <typename T> T symbol_##sym(T) {}")
            source.append("#define DEFINE(sym) symbol_##sym(sym)")
            for name in defines:
                # create a function template for each value
                source.append("DECLARE(%s)" % name)
            source.append("int main() {")
            for name in defines:
                # instantiate a function template.
                # The return type of the function is the symbol's type.
                source.append("  DEFINE(%s);" % name)
            source.append("}")

            fd, fname = tempfile.mkstemp(".xml")
            os.close(fd)
            invalid_symbols = self.try_create_xml(source, fname)
            if not invalid_symbols:
                break
            if self.options.verbose:
                if i == 0:
                    print >> sys.stderr, "compiler errors caused by '-c' flag.\n" \
                          "Trying to resolve them in multiple passes."
                print >> sys.stderr, "pass %d:" % (i + 1)
            for n in invalid_symbols:
                del defines[n]
                if self.options.verbose:
                    print >> sys.stderr, "\t", n
        else:
            raise CompilerError()

        items = gccxmlparser.parse(fname)
        # make sure the temporary file is removed after using it
        if not self.options.keep_temporary_files:
            os.remove(fname)
        else:
            print >> sys.stderr, "Info: file '%s' not removed" % fname

        types = {}
        for i in items:
            name = getattr(i, "name", None)
            if name and name.startswith("symbol_"):
                name = name[len("symbol_"):]
                typ = i.returns
                try:
                    typ = self.c_type_name(i.returns)
                except TypeError, detail:
                    # XXX Warning?
                    ## print >> sys.stderr,  "skipped #define %s %s" % (name, defines[name]), detail
                    pass
                else:
                    types[name] = typ
        return types

    def create_final_xml(self, include_files, types, xmlfile=None):
        source = []
        for fname in include_files:
            source.append('#include "%s"' % fname)
        for name, value in types.iteritems():
            source.append("const %s cpp_sym_%s = (const %s) %s;" % (types[name], name, types[name], name))
        self.create_xml(source, xmlfile)

    def c_type_name(self, tp):
        "Return the C type name for this type."
        if isinstance(tp, typedesc.FundamentalType):
            return tp.name
        elif isinstance(tp, typedesc.PointerType):
            return "%s *" % self.c_type_name(tp.typ)
        elif isinstance(tp, typedesc.CvQualifiedType):
            return self.c_type_name(tp.typ)
        elif isinstance(tp, typedesc.Typedef):
            return self.c_type_name(tp.typ)
        elif isinstance(tp, typedesc.Structure):
            return tp.name
        raise TypeError, type(tp).__name__

    def dump_as_cdata(self, f, mapping, name):
            f.write('  <CPP_DUMP name="%s"><![CDATA[' % name)
            names = mapping.keys()
            names.sort()
            for n in names:
                v = mapping[n]
                f.write("%s %s\n" % (n, v))
            f.write("]]></CPP_DUMP>\n")

    ################################################################

    def parse(self, include_files):
        """Parse include files."""
        options = self.options
        
        types = {}
        functions = {}
        aliases = {}
        excluded = {}

        if options.cpp_symbols:
            if options.verbose:
                print >> sys.stderr, "compile for syntax check ..."
            # compile the input files to check for compilation errors,
            # before trying the fancy stuff with cpp_symbols.
            self.create_final_xml(include_files, types, None)

        if options.cpp_symbols:
            if options.verbose:
                print >> sys.stderr, "finding definitions ..."
            defines = self.get_defines(include_files)
            if options.verbose:
                print >> sys.stderr, "%d found" % len(defines)

                print >> sys.stderr, "filtering definitions ..."
            aliases, functions, excluded, defines = self.filter_definitions(defines)
            if options.verbose:
                print >> sys.stderr, "%d values, %d aliases" % (len(defines), len(aliases))

            if options.verbose:
                print >> sys.stderr, "finding definitions types ..."

            try:
                # invoke C++ template magic
                types = self.find_types(include_files, defines)
                if options.verbose:
                    print >> sys.stderr, "found %d types ..." % len(types)
            except CompilerError:
                print >> sys.stderr, "Could not determine the types of #define symbols."
                types = {}

        if options.verbose:
            print >> sys.stderr, "creating xml output file ..."
        self.create_final_xml(include_files, types, options.xmlfile)

        # Include additional preprecessor definitions into the XML file.

        if options.xmlfile:
            f = open(options.xmlfile, "r+")
            f.seek(-12, 2)
            data = f.read()
            if len(data) == 11:
                # text mode on windows is strange.  You read 12
                # characters, but get 11.
                assert data == "</GCC_XML>\n"
                f.seek(-12, 2)
            else:
                # linux, ...
                assert data == "\n</GCC_XML>\n"
                f.seek(-11, 2)
            f.flush()

            self.dump_as_cdata(f, functions, "functions")
            self.dump_as_cdata(f, aliases, "aliases")
            self.dump_as_cdata(f, excluded, "excluded")

            f.write("</GCC_XML>\n")
            f.close()
