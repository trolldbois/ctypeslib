#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests haystack.utils ."""

import struct
import operator
import os
import unittest

from haystack.config import Config

import ctypes
from haystack import memory_mapping
from haystack.model import LoadableMembersStructure
from haystack import utils

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2012 Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__status__ = "Production"

class St(LoadableMembersStructure):
  _fields_ = [ ('a',ctypes.c_int) ]

class St2(LoadableMembersStructure):
  _fields_ = [ ('a',ctypes.c_int) ]

class SubSt2(LoadableMembersStructure):
  _fields_ = [ ('a',ctypes.c_int) ]

#
btype = ctypes.c_int
voidp = ctypes.c_void_p
stp = ctypes.POINTER(St)
stpvoid = ctypes.POINTER(None)
arra1 = (ctypes.c_long *4)
arra2 = (St *4)
arra3 = (ctypes.POINTER(St) *4)
string = ctypes.c_char_p
fptr = type(ctypes.memmove)
arra4 = (fptr*256)


class TestBasicFunctions(unittest.TestCase):

  def setUp(self):
    self.tests = [btype, voidp, St, stp, arra1, arra2, arra3, string, fptr, arra4, St2, SubSt2]
  
  def _testMe(self, fn, valids, invalids):
    for var in valids:
      self.assertTrue( fn( var ), var)
    for var in invalids:
      self.assertFalse( fn( var ), var )

  def test_isBasicType(self):
    valids = [btype]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isBasicType, valids, invalids)
    return 

  def test_isStructType(self):
    valids = [St, St2, SubSt2]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isStructType, valids, invalids)
    return 

  def test_isPointerType(self):
    valids = [voidp, stp, stpvoid, fptr]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isPointerType, valids, invalids)
    return 

  def test_isVoidPointerType(self):
    valids = [voidp, stpvoid]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isVoidPointerType, valids, invalids)
    return 

  def test_isFunctionType(self):
    valids = [fptr]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isFunctionType, valids, invalids)
    return 

  def test_isBasicTypeArray(self):
    valids = [arra1()]
    invalids = [ v for v in self.tests if v not in valids]
    invalids.extend([ arra2(), arra3(), arra4(), ] )
    for var in valids:
      self.assertTrue( utils.isBasicTypeArray( var ), var)
    for var in invalids:
      self.assertFalse( utils.isBasicTypeArray( var ), var )
    return 

  def test_isArrayType(self):
    valids = [arra1, arra2, arra3, arra4, ]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isArrayType, valids, invalids)
    return 

  def test_isCStringPointer(self):
    valids = [string ]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isCStringPointer, valids, invalids)
    return 

  def test_is_ctypes(self):
    valids = [St(), St2(), SubSt2()]
    #valids = [btype, voidp, stp, stpvoid, arra1, arra2, arra3, string, fptr, arra4 ]
    invalids = [ v for v in self.tests if v not in valids]
    self._testMe( utils.isCTypes, valids, invalids)
    return 


  def test_import(self):
    #''' replace c_char_p '''
    self.assertNotEquals( ctypes.c_char_p.__name__ , 'c_char_p', 'c_char_p is not our CString')
    #''' keep orig class '''
    self.assertNotEquals( ctypes.Structure.__name__ , 'Structure', 'Structure is not our LoadablesMembers')



if __name__ == '__main__':
    unittest.main(verbosity=0)


