#!/usr/bin/env python
"""ctypes code generator
"""
import os, sys
from distutils.core import setup, Command

class test(Command):
    # Original version of this class posted
    # by Berthold Hoellmann to distutils-sig@python.org
    description = "run tests"

    user_options = [
        ('tests=', 't',
         "comma-separated list of packages that contain test modules"),
        ('use-resources=', 'u',
         "resources to use - resource names are defined by tests"),
        ('refcounts', 'r',
         "repeat tests to search for refcount leaks (requires 'sys.gettotalrefcount')"),
        ]

    boolean_options = ["refcounts"]

    def initialize_options(self):
        self.build_base = 'build'
        self.use_resources = ""
        self.refcounts = False
        self.tests = "ctypeslib.test"

    # initialize_options()

    def finalize_options(self):
        if self.refcounts and not hasattr(sys, "gettotalrefcount"):
            raise DistutilsOptionError("refcount option requires Python debug build")
        self.tests = self.tests.split(",")
        self.use_resources = self.use_resources.split(",")

    # finalize_options()

    def run(self):
        self.run_command('build')

        import ctypes.test
        ctypes.test.use_resources.extend(self.use_resources)

        for name in self.tests:
            package = __import__(name, globals(), locals(), ['*'])
            print "Testing package", name, (sys.version, sys.platform, os.name)
            ctypes.test.run_tests(package,
                                  "test_*.py",
                                  self.verbose,
                                  self.refcounts)

    # run()

# class test

setup(name="ctypeslib",
      packages = ['ctypeslib', 'ctypeslib.codegen'],
      scripts = ['scripts/h2xml.py', 'scripts/xml2py.py'],
      description="ctypes code generator",
      long_description = __doc__,
      author="Thomas Heller",
      author_email="theller@ctypes.org",
      license="MIT License",
      version = "0.5.0",

##          url="http://starship.python.net/crew/theller/ctypes.html",
##          platforms=["windows", "Linux", "MacOS X", "Solaris", "FreeBSD"],

      cmdclass = {'test': test},

      )
