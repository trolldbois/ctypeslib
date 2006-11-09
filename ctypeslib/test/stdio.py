import os
from ctypeslib.dynamic_module import include
from ctypes import *

if os.name == "nt":
    _libc = CDLL("msvcrt")
else:
    _libc = CDLL(None)

_gen_basename = include("""\
#include <stdio.h>

#ifdef _MSC_VER
#  include <fcntl.h>
#else
#  include <sys/fcntl.h>
#endif

/* Silly comment */
""",
        persist=False)
