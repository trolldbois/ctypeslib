import os
from ctypeslib.dynamic_module import include
from ctypes import *

_gen_basename = include("#include <windows.h>",
                        persist=False,
                        compilerflags=["-DWIN32_LEAN_AND_MEAN"])
