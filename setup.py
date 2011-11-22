#!/usr/bin/env python
"""ctypeslib contains these packages:

 - ``ctypeslib.codegen``       - a code generator

 - ``ctypeslib.contrib``       - various contributed modules

 - ``ctypeslib.util``          - assorted small helper functions

 - ``ctypeslib.test``          - unittests

There is not yet an official release, but ctypeslib can be installed
directly from the subversion repository with::

    easy_install ctypeslib==dev

The SVN repository is here:

http://svn.python.org/projects/ctypes/trunk/ctypeslib/#egg=ctypeslib-dev

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

        import ctypeslib.test
        ctypeslib.test.use_resources.extend(self.use_resources)

        for name in self.tests:
            package = __import__(name, globals(), locals(), ['*'])
            print "Testing package", name, (sys.version, sys.platform, os.name)
            ctypeslib.test.run_tests(package,
                                     "test_*.py",
                                     self.verbose,
                                     self.refcounts)

    # run()

# class test

classifiers = [
    'Development Status :: 3 - Alpha',
    'Development Status :: 4 - Beta',
##    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
##    'Operating System :: Microsoft :: Windows',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules',
    ]


setup(name="ctypeslib",
      packages = ['ctypeslib',
                  'ctypeslib.codegen',
                  'ctypeslib.contrib',
                  'ctypeslib.util',
                  'ctypeslib.test'],
      scripts = ['scripts/h2xml.py', 'scripts/xml2py.py'],
      description="ctypeslib - useful additions to the ctypes FFI library",
      long_description = __doc__,
      author="Thomas Heller",
      author_email="theller@ctypes.org",
      license="MIT License",
      version = "0.5.6",

      classifiers = classifiers,

##      url="http://starship.python.net/crew/theller/ctypeswiki.cgi",
##      download_url="http://svn.python.org/projects/ctypes/trunk/ctypeslib",

      cmdclass = {'test': test},

      )
