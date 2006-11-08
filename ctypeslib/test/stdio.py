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
#include <io.h>
#include <fcntl.h>
""",
        persist=False)
