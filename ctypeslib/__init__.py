# -*- coding: utf-8 -*-
# ctypeslib package

__version__ = "2.0"

# configure python-clang to use the local clang library
from ctypes.util import find_library
if find_library("clang") is None:  # if not None, it will work
    if find_library("clang-3.7") is not None:
        from clang import cindex
        cindex.Config.set_library_file(find_library("clang-3.7"))
    # else, this is going to fail. Probably.
