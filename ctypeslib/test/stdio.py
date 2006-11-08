import os
from ctypeslib.dynamic_module import include
from ctypes import *
import logging
logging.basicConfig(level=logging.INFO)

if os.name == "nt":
    _libc = CDLL("msvcrt")
else:
    _libc = CDLL(None)

include("""\
#include <stdio.h>

#ifdef _MSC_VER
#  include <fcntl.h>
#else
#  include <sys/fcntl.h>
#endif
""",
        persist=False)
