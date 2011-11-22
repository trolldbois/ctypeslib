"""gccxmlparser - parse a gccxml created XML file into sequence type descriptions"""
try:
    from xml.etree import cElementTree
except ImportError:
    try:
        import cElementTree
    except ImportError:
        cElementTree = None

if cElementTree:
    base = object
else:
    import xml.sax
    base = xml.sax.ContentHandler

import typedesc
import sys
try:
    set
except NameError:
    from sets import Set as set
import re

################################################################

def MAKE_NAME(name):
    name = name.replace("$", "DOLLAR")
    name = name.replace(".", "DOT")
    if name.startswith("__"):
        return "_X" + name
    elif name[0] in "01234567879":
        return "_" + name
    return name

WORDPAT = re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

def CHECK_NAME(name):
    if WORDPAT.match(name):
        return name
    return None

class GCCXML_Parser(base):
    has_values = set(["Enumeration", "Function", "FunctionType",
                      "OperatorFunction", "Method", "Constructor",
                      "Destructor", "OperatorMethod"])

    def __init__(self, *args):
        base.__init__(self, *args)
        self.context = []
        self.all = {}
        self.cpp_data = {}

    if cElementTree:
        def parse(self, xmlfile):
            for event, node in cElementTree.iterparse(xmlfile, events=("start", "end")):
                if event == "start":
                    self.startElement(node.tag, dict(node.items()))
                else:
                    if node.text:
                        self.characters(node.text)
                    self.endElement(node.tag)
                    node.clear()
    else:
        def parse(self, xmlfile):
            xml.sax.parse(xmlfile, self)

    def startElement(self, name, attrs):
        # find and call the handler for this element
        mth = getattr(self, name)
        result = mth(attrs)
        if result is not None:
            location = attrs.get("location", None)
            if location is not None:
                result.location = location
            # record the result
            _id = attrs.get("id", None)
            # The '_id' attribute is used to link together all the
            # nodes, in the _fixup_ methods.
            if _id is not None:
                self.all[_id] = result
            else:
                # EnumValue, for example, has no "_id" attribute.
                # Invent our own...
                self.all[id(result)] = result
        # if this element has children, push onto the context
        if name in self.has_values:
            self.context.append(result)

    cdata = None
    def endElement(self, name):
        # if this element has children, pop the context
        if name in self.has_values:
            self.context.pop()
        self.cdata = None

    ################################
    # do-nothing element handlers

    def Class(self, attrs): pass
    def Destructor(self, attrs): pass
    
    cvs_revision = None
    def GCC_XML(self, attrs):
        rev = attrs["cvs_revision"]
        self.cvs_revision = tuple(map(int, rev.split(".")))

    def Namespace(self, attrs): pass

    def Base(self, attrs): pass
    def Ellipsis(self, attrs): pass
    def OperatorMethod(self, attrs): pass

    ################################
    # real element handlers

    def CPP_DUMP(self, attrs):
        name = attrs["name"]
        # Insert a new list for each named section into self.cpp_data,
        # and point self.cdata to it.  self.cdata will be set to None
        # again at the end of each section.
        self.cpp_data[name] = self.cdata = []

    def characters(self, content):
        if self.cdata is not None:
            self.cdata.append(content)

    def File(self, attrs):
        name = attrs["name"]
        if sys.platform == "win32" and " " in name:
            # On windows, convert to short filename if it contains blanks
            from ctypes import windll, create_unicode_buffer, sizeof, WinError
            buf = create_unicode_buffer(512)
            if windll.kernel32.GetShortPathNameW(name, buf, sizeof(buf)):
                name = buf.value
        return typedesc.File(name)

    def _fixup_File(self, f): pass
    
    # simple types and modifiers

    def Variable(self, attrs):
        name = attrs["name"]
        if name.startswith("cpp_sym_"):
            # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXx fix me!
            name = name[len("cpp_sym_"):]
        init = attrs.get("init", None)
        typ = attrs["type"]
        return typedesc.Variable(name, typ, init)

    def _fixup_Variable(self, t):
        t.typ = self.all[t.typ]

    def Typedef(self, attrs):
        name = attrs["name"]
        typ = attrs["type"]
        return typedesc.Typedef(name, typ)

    def _fixup_Typedef(self, t):
        t.typ = self.all[t.typ]

    def FundamentalType(self, attrs):
        name = attrs["name"]
        if name == "void":
            size = ""
        else:
            size = attrs["size"]
        align = attrs["align"]
        return typedesc.FundamentalType(name, size, align)

    def _fixup_FundamentalType(self, t): pass

    def PointerType(self, attrs):
        typ = attrs["type"]
        size = attrs["size"]
        align = attrs["align"]
        return typedesc.PointerType(typ, size, align)

    def _fixup_PointerType(self, p):
        p.typ = self.all[p.typ]

    ReferenceType = PointerType
    _fixup_ReferenceType = _fixup_PointerType

    def ArrayType(self, attrs):
        # type, min?, max?
        typ = attrs["type"]
        min = attrs["min"]
        max = attrs["max"]
        if max == "ffffffffffffffff":
            max = "-1"
        return typedesc.ArrayType(typ, min, max)

    def _fixup_ArrayType(self, a):
        a.typ = self.all[a.typ]

    def CvQualifiedType(self, attrs):
        # id, type, [const|volatile]
        typ = attrs["type"]
        const = attrs.get("const", None)
        volatile = attrs.get("volatile", None)
        return typedesc.CvQualifiedType(typ, const, volatile)

    def _fixup_CvQualifiedType(self, c):
        c.typ = self.all[c.typ]

    # callables
    
    def Function(self, attrs):
        # name, returns, extern, attributes
        name = attrs["name"]
        returns = attrs["returns"]
        attributes = attrs.get("attributes", "").split()
        extern = attrs.get("extern")
        return typedesc.Function(name, returns, attributes, extern)

    def _fixup_Function(self, func):
        func.returns = self.all[func.returns]
        func.fixup_argtypes(self.all)

    def FunctionType(self, attrs):
        # id, returns, attributes
        returns = attrs["returns"]
        attributes = attrs.get("attributes", "").split()
        return typedesc.FunctionType(returns, attributes)
    
    def _fixup_FunctionType(self, func):
        func.returns = self.all[func.returns]
        func.fixup_argtypes(self.all)

    def OperatorFunction(self, attrs):
        # name, returns, extern, attributes
        name = attrs["name"]
        returns = attrs["returns"]
        return typedesc.OperatorFunction(name, returns)

    def _fixup_OperatorFunction(self, func):
        func.returns = self.all[func.returns]

    def _Ignored(self, attrs):
        name = attrs.get("name", None)
        if not name:
            name = attrs["mangled"]
        return typedesc.Ignored(name)

    def _fixup_Ignored(self, const): pass

    Constructor = Destructor = OperatorMethod = _Ignored

    def Method(self, attrs):
        # name, virtual, pure_virtual, returns
        name = attrs["name"]
        returns = attrs["returns"]
        return typedesc.Method(name, returns)

    def _fixup_Method(self, m):
        m.returns = self.all[m.returns]
        m.fixup_argtypes(self.all)

    def Argument(self, attrs):
        parent = self.context[-1]
        if parent is not None:
            parent.add_argument(typedesc.Argument(attrs["type"], attrs.get("name")))

    # enumerations

    def Enumeration(self, attrs):
        # id, name
        name = attrs["name"]
        # If the name isn't a valid Python identifier, create an unnamed enum
        name = CHECK_NAME(name)
        size = attrs["size"]
        align = attrs["align"]
        return typedesc.Enumeration(name, size, align)

    def _fixup_Enumeration(self, e): pass

    def EnumValue(self, attrs):
        name = attrs["name"]
        value = attrs["init"]
        v = typedesc.EnumValue(name, value, self.context[-1])
        self.context[-1].add_value(v)
        return v

    def _fixup_EnumValue(self, e): pass

    # structures, unions

    def Struct(self, attrs):
        # id, name, members
        name = attrs.get("name")
        if name is None:
            name = MAKE_NAME(attrs["mangled"])
        bases = attrs.get("bases", "").split()
        members = attrs.get("members", "").split()
        align = attrs["align"]
        size = attrs.get("size")
        return typedesc.Structure(name, align, members, bases, size)

    def _fixup_Structure(self, s):
        s.members = [self.all[m] for m in s.members]
        s.bases = [self.all[b] for b in s.bases]
    _fixup_Union = _fixup_Structure

    def Union(self, attrs):
        name = attrs.get("name")
        if name is None:
            name = MAKE_NAME(attrs["mangled"])
        bases = attrs.get("bases", "").split()
        members = attrs.get("members", "").split()
        align = attrs["align"]
        size = attrs.get("size")
        return typedesc.Union(name, align, members, bases, size)

    def Field(self, attrs):
        # name, type
        name = attrs["name"]
##        if name.startswith("__") and not name.endswith("__"):
##            print "INVALID FIELD NAME", name
        typ = attrs["type"]
        bits = attrs.get("bits", None)
        offset = attrs.get("offset")
        return typedesc.Field(name, typ, bits, offset)

    def _fixup_Field(self, f):
        f.typ = self.all[f.typ]

    ################

    def _fixup_Macro(self, m):
        pass

    def get_macros(self, text):
        if text is None:
            return
        text = "".join(text)
        # preprocessor definitions that look like macros with one or more arguments
        for m in text.splitlines():
            name, body = m.split(None, 1)
            name, args = name.split("(", 1)
            args = "(%s" % args
            self.all[name] = typedesc.Macro(name, args, body)

    def get_aliases(self, text, namespace):
        if text is None:
            return
        # preprocessor definitions that look like aliases:
        #  #define A B
        text = "".join(text)
        aliases = {}
        for a in text.splitlines():
            name, value = a.split(None, 1)
            a = typedesc.Alias(name, value)
            aliases[name] = a
            self.all[name] = a

        for name, a in aliases.items():
            value = a.alias
            # the value should be either in namespace...
            if value in namespace:
                # set the type
                a.typ = namespace[value]
            # or in aliases...
            elif value in aliases:
                a.typ = aliases[value]
            # or unknown.
            else:
                # not known
##                print "skip %s = %s" % (name, value)
                pass

    def get_result(self):
        interesting = (typedesc.Typedef, typedesc.Enumeration, typedesc.EnumValue,
                       typedesc.Function, typedesc.Structure, typedesc.Union,
                       typedesc.Variable, typedesc.Macro, typedesc.Alias)

        import warnings
        if self.cvs_revision is None:
            warnings.warn("Could not determine CVS revision of GCCXML")
        elif self.cvs_revision < (1, 114):
            warnings.warn("CVS Revision of GCCXML is %d.%d" % self.cvs_revision)

        self.get_macros(self.cpp_data.get("functions"))

        remove = []
        for n, i in self.all.items():
            location = getattr(i, "location", None)
            if location:
                fil, line = location.split(":")
                i.location = self.all[fil].name, line
            # link together all the nodes (the XML that gccxml generates uses this).
            mth = getattr(self, "_fixup_" + type(i).__name__)
            try:
                mth(i)
            except KeyError: # XXX better exception catching
                remove.append(n)

        for n in remove:
            del self.all[n]

        # Now we can build the namespace.
        namespace = {}
        for i in self.all.values():
            if not isinstance(i, interesting):
                continue  # we don't want these
            name = getattr(i, "name", None)
            if name is not None:
                namespace[name] = i

        self.get_aliases(self.cpp_data.get("aliases"), namespace)

        result = []
        for i in self.all.values():
            if isinstance(i, interesting):
                result.append(i)

        return result

################################################################

def parse(xmlfile):
    # parse an XML file into a sequence of type descriptions
    parser = GCCXML_Parser()
    parser.parse(xmlfile)
    return parser.get_result()
