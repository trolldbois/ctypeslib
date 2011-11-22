"""h2xml - convert C include file(s) into an xml file by running gccxml."""
import sys, os, ConfigParser
from ctypeslib.codegen import cparser
from optparse import OptionParser

def compile_to_xml(argv):
    def add_option(option, opt, value, parser):
        parser.values.gccxml_options.extend((opt, value))

    # Hm, should there be a way to disable the config file?
    # And then, this should be done AFTER the parameters are processed.
    config = ConfigParser.ConfigParser()
    try:
        config.read("h2xml.cfg")
    except ConfigParser.ParsingError, detail:
        print >> sys.stderr, detail
        return 1

    parser = OptionParser("usage: %prog includefile ... [options]")
    parser.add_option("-q", "--quiet",
                      dest="quiet",
                      action="store_true",
                      default=False)

    parser.add_option("-D",
                      type="string",
                      action="callback",
                      callback=add_option,
                      dest="gccxml_options",
                      help="macros to define",
                      metavar="NAME[=VALUE]",
                      default=[])

    parser.add_option("-U",
                      type="string",
                      action="callback",
                      callback=add_option,
                      help="macros to undefine",
                      metavar="NAME")

    parser.add_option("-I",
                      type="string",
                      action="callback",
                      callback=add_option,
                      dest="gccxml_options",
                      help="additional include directories",
                      metavar="DIRECTORY")

    parser.add_option("-o",
                      dest="xmlfile",
                      help="XML output filename",
                      default=None)

    parser.add_option("-c", "--cpp-symbols",
                      dest="cpp_symbols",
                      action="store_true",
                      help="try to find #define symbols - this may give compiler errors, " \
                      "so it's off by default.",
                      default=False)

    parser.add_option("-k",
                      dest="keep_temporary_files",
                      action="store_true",
                      help="don't delete the temporary files created "\
                      "(useful for finding problems)",
                      default=False)

    options, files = parser.parse_args(argv[1:])

    if not files:
        print "Error: no files to process"
        print >> sys.stderr, __doc__
        return 1

    options.flags = options.gccxml_options
    options.verbose = not options.quiet

    parser = cparser.IncludeParser(options)
    parser.parse(files)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    try:
        compile_to_xml(argv)
    except cparser.CompilerError, detail:
        print >> sys.stderr, "CompilerError:", detail
        return 1

if __name__ == "__main__":
    sys.exit(main())
