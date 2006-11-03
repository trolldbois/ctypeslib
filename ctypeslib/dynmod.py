# A dynamic module generator for ctypes.
#
#
import sys, os, md5, bz2, cPickle, errno
import ctypes
from ctypes.wrap import xml2py, h2xml, gccxmlparser, codegenerator

def get_items(include_files,
              gccopts):
    # Process <include_files> with xml2py. <gccopts> is a list of
    # command line options to pass.  Then parse the XML file with
    # gccxmlparser, and return a tuple containing two items: a
    # generated filename, and a collection of type descriptions.
    #
    # Since all this takes some time, the resulting files are written
    # to a cache directory, and will be picked up from there instead
    # of recreated each time.  The filename is created by passing all
    # the options through a message digest, this creates a long,
    # unique filename.
    dirname = os.path.dirname(os.path.abspath(xml2py.__file__))
    cache_dir = os.path.join(dirname, "_cache")
    try:
        os.mkdir(cache_dir)
    except OSError, detail:
        if detail.errno != errno.EEXIST:
            raise
    if not os.path.exists(os.path.join(cache_dir, "__init__.py")):
        text = "# package for generated wrappers\n"
        open(os.path.join(cache_dir, "__init__.py"), "w").write(text)

    args = include_files + gccopts
    basename = "_" + md5.new(" ".join(args)).hexdigest()
    fullname = os.path.join(cache_dir, basename)

    # todo: record the options and the generated filename somewhere,
    # to be able to identify them laster.

    xml_file = fullname + ".xml"
    pck_file = fullname + ".pck.bz2"

    # todo: write a version number into the pickle file, and check
    # that before reading!

    if os.path.exists(pck_file):
        print "# reading", pck_file
        data = open(pck_file, "rb").read()
        data = bz2.decompress(data)
        items = cPickle.loads(data)
        return items

    if not os.path.exists(xml_file):
        print "# creating", xml_file
        h2xml.main(include_files + gccopts + ["-o", xml_file, "-q"])

    # todo: also compress the xml file because it's large!  Or should
    # we remove the xml file all together, oncew the pickle is
    # created?

    print "# parsing", xml_file
    items = gccxmlparser.parse(xml_file)

    print "# creating", pck_file
    data = cPickle.dumps(items, -1)
    data = bz2.compress(data)
    open(pck_file, "wb").write(data)
    return items

################################################################

class UnknownSymbol(Exception):
    pass

class DynamicGenerator(object):
    def __init__(self, py_file, items):
        self.items = items

        print "ITEMS", len(items)

        self._namespace = {}
        exec "from ctypes import *" in self._namespace

        if py_file.endswith(".pyc") or py_file.endswith(".pyo"):
            py_file = py_file[:-1]

        if os.path.exists(py_file):
            execfile(py_file, self._namespace)

        done = {}
        # names contained in the header files
        names_map = self.names_map = {}
        for i in items:
            if hasattr(i, "name"):
                name = i.name
                if name in self._namespace:
                    done[name] = i
                else:
                    names_map[name] = i

        self.logfile = open(py_file, "a")

        dlls = [ctypes.CDLL(name) for name in xml2py.windows_dll_names]

        self.generator = codegenerator.Generator(output=self,
                                                 generate_comments=False,
                                                 known_symbols=None,
                                                 searched_dlls=dlls)
        # the generator has .done and .names attributes, which are
        # sets.  They contain the type descriptions and the names of
        # symbols that are already generated.
        self.generator.done.update(done.values())
        self.generator.names.update(done.keys())

    def write(self, text):
        self._text.append(text)
        self.logfile.write(text)

    def generate(self, name):
        try:
            return self._namespace[name]
        except KeyError:
            try:
                item = self.names_map[name]
            except KeyError:
                raise UnknownSymbol, name
        # reset accumulated code
        self._text = []
        self.generator.generate_code([item])
        self.logfile.flush()
        # get the generated code
        code = "".join(self._text)
        exec code in self._namespace
        return self._namespace[name]
        
class DynamicModule(object):
    # class simulating a module
    def __init__(self, py_file, items):
        self.__gen = DynamicGenerator(py_file, items)

    def __getattr__(self, name):
        try:
            value = self.__gen.generate(name)
        except UnknownSymbol:
            raise AttributeError, name
        setattr(self, name, value)
        return value

def install(include_files,
            modname,
            gccopts=None):
    # function to install a dynamic module
    parent = None
    mod = __import__(modname)
    for part in modname.split(".")[1:]:
        parent = mod
        mod = getattr(mod, part)
    print "PARENT?", parent, part
    items = get_items(include_files, gccopts or [])
    module = DynamicModule(mod.__file__, items)
    if parent is not None:
        setattr(parent, part, module)
    sys.modules[modname] = module
    print "SYS.MODULES[%s]" % modname, module

################################################################

def _test():
    install(["windows.h", "commctrl.h"],
            "windows",
##            gccopts=["-DNO_STRICT", "-DUNICODE=1", "-DWIN32_LEAN_AND_MEAN"])
            gccopts=["-DNO_STRICT", "-DUNICODE=1"])
    import windows
    print windows.MessageBox
    print windows.MessageBoxA
    print windows.MessageBoxW
    print windows.MB_OK
    print windows.RECT
    print windows.POINT
    print windows.WNDCLASSEXA
    print windows.WNDCLASSEXW
    print windows.WM_USER
    print windows.tagREGCLS
    print windows.REGCLS_SURROGATE
    print windows.CLSCTX_ALL

if __name__ == "__main__":
    _test()
