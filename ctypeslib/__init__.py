# -*- coding: utf-8 -*-
# ctypeslib package

from pkg_resources import get_distribution, DistributionNotFound
import os.path

try:
    _dist = get_distribution('ctypeslib2')
    # Normalize case for Windows systems
    # if you are in a virtualenv, ./local/* are aliases to ./*
    dist_loc = os.path.normcase(os.path.realpath(_dist.location))
    here = os.path.normcase(os.path.realpath(__file__))
    if not here.startswith(os.path.join(dist_loc, 'ctypeslib')):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = 'Please install this project with setup.py'
else:
    __version__ = _dist.version

# configure python-clang to use the local clang library
try:
    from ctypes.util import find_library
    # debug for python-haystack travis-ci
    #print 'find_library("clang-3.7")', find_library("clang-3.7")
    #print 'find_library("clang")', find_library("clang")
    if find_library("clang-3.7") is not None:
        from clang import cindex
        cindex.Config.set_library_file(find_library("clang-3.7"))
        # else, this is going to fail. Probably.
    elif find_library("clang") is not None:
        from clang import cindex
        cindex.Config.set_library_file(find_library("clang"))
except ImportError as e:
    print e


