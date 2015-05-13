# ctypeslib with libclang

[![Build Status](https://travis-ci.org/trolldbois/ctypeslib.svg?branch=master)](https://travis-ci.org/trolldbois/ctypeslib)
[![Coverage Status](https://coveralls.io/repos/trolldbois/ctypeslib/badge.svg)](https://coveralls.io/r/trolldbois/ctypeslib)
[![Code Health](https://landscape.io/github/trolldbois/ctypeslib/master/landscape.svg?style=flat)](https://landscape.io/github/trolldbois/ctypeslib/master)
[![pypi](https://img.shields.io/pypi/dm/ctypeslib.svg)](https://pypi.python.org/pypi/ctypeslib2)

[Quick usage guide](docs/ctypeslib 2.0 Introduction.ipynb) in the docs/ folder.

## Status update

2015-05-01: master branch works with libclang-3.7 HEAD

## Installation

The requirement on python-clang-3.7 means that you either need:

1. to install libclang1-dev to get libclang.so
2. create a link to libclang-3.7.so.1 named libclang.so
3. hardcode the required clang.cindex.Config.load_library_file in your code


### Pypi

Stable Distribution is available through pypi at https://pypi.python.org/pypi/ctypeslib2/

`sudo pip install ctypeslib2`

### Setting up clang >= 3.7 dependency

See the LLVM Clang instructions for dev branch 3.7 at http://llvm.org/apt/

    sudo apt-add-repository "deb http://llvm.org/apt/raring/ llvm-toolchain-raring main"
    sudo apt-get install libclang1-3.7 python-clang-3.7
    sudo echo `echo "/usr/lib/llvm-3.7/lib/" >> /etc/ld.so.conf.d/llvm-dev.conf`
    sudo ldconfig -n

## Usage
```
usage: clang2py [-h] [--debug] [-c] [-d] [-k TYPEKIND] [-l DLLS] [-o OUTPUT]
                [-r EXPRESSION] [-s SYMBOL] [-v] [-w W] [-m module]
                [--preload DLL] [--show-ids SHOWIDS] [--max-depth N]
                files [files ...]

generate python ABI code from C code

positional arguments:
  files               source filenames

optional arguments:
  -h, --help          show this help message and exit
  --debug             setLevel to DEBUG
  -c                  include source file location in comments
  -d                  include docstrings containing C prototype and source
                      file location
  -k TYPEKIND         kind of type descriptions to include: d = #defines, e =
                      enumerations, f = functions, s = structures, t =
                      typedefs
  -l DLLS             libraries to search for exported functions
  -o OUTPUT           output filename (if not specified, standard output will
                      be used)
  -r EXPRESSION       regular expression for symbols to include (if neither
                      symbols nor expressions are specified,everything will be
                      included)
  -s SYMBOL           symbol to include (if neither symbols nor expressions
                      are specified,everything will be included)
  -v                  verbose output
  -w W                add all standard windows dlls to the searched dlls list
  -m module           Python module(s) containing symbols which will be
                      imported instead of generated
  --preload DLL       dlls to be loaded before all others (to resolve symbols)
  --show-ids SHOWIDS  Don't compute cursor IDs (very slow)
  --max-depth N       Limit cursor expansion to depth N

About clang-args: You can pass modifier to clang after your file name. For
example, try "-target x86_64" or "-target i386-linux" as the last argument to
change the target CPU arch.
```

## Inner workings for memo

- clang2py is a script that calls ctypeslib/ctypeslib/clang2py.py
- clang2py.py is mostly the old xml2py.py module forked to use libclang.
- clang2py.py calls ctypeslib/ctypeslib/codegen/codegenerator.py
- codegenerator.py calls ctypeslib/ctypeslib/codegen/clangparser.py
- clangparser.py uses libclang's python binding to access the clang internal 
 representation of the C source code. 
 It then translate each child of the AST tree to python objects as listed in 
 typedesc.
- codegenerator.py then uses these python object to generate ctypes-based python
 source code.
 
Because clang is capable to handle different target architecture, this fork 
 {is/should be} able to produce cross-platform memory representation if needed.




## Credits

This fork of ctypeslib is mainly about using the libclang1>=3.7 python bindings
to generate python code from C source code, instead of gccxml.

the original ctypeslib contains these packages:
 - ``ctypeslib.codegen``       - a code generator
 - ``ctypeslib.contrib``       - various contributed modules
 - ``ctypeslib.util``          - assorted small helper functions
 - ``ctypeslib.test``          - unittests

This fork of ctypeslib is heavily patched for clang.
- https://github.com/trolldbois/ctypeslib is based on 
 rev77594 of the original ctypeslib.
- git-svn-id: http://svn.python.org/projects/ctypes/trunk/ctypeslib@77594 
 6015fed2-1504-0410-9fe1-9d1591cc4771

The original ctypeslib is written by
- author="Thomas Heller",
- author_email="theller@ctypes.org",




 
