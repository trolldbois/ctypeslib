#!/usr/bin/env python

#===- cindex-dump.py - cindex/Python Source Dump -------------*- python -*--===#
#
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
#===------------------------------------------------------------------------===#

"""
A simple command line tool for dumping a source file using the Clang Index
Library.
"""
import os
import sys
from clang.cindex import Index
from clang.cindex import CursorKind, TypeKind

def get_diag_info(diag):
    return { 'severity' : diag.severity,
             'location' : diag.location,
             'spelling' : diag.spelling,
             'ranges' : diag.ranges,
             'fixits' : diag.fixits }

def get_cursor_id(cursor, cursor_list = []):
    if not opts.showIDs:
        return None

    if cursor is None:
        return None

    # FIXME: This is really slow. It would be nice if the index API exposed
    # something that let us hash cursors.
    for i,c in enumerate(cursor_list):
        if cursor == c:
            return i
    cursor_list.append(cursor)
    return len(cursor_list) - 1

def get_info(node, depth=0):
    if opts.maxDepth is not None and depth >= opts.maxDepth:
        children = None
    else:
        children = []
        for c in node.get_children():
            try:
                children.append(get_info(c, depth+1))
            except ValueError,e:
                pass
    name = node.spelling
    if name == '':
      name = node.get_usr()

    if depth != 0:
        if node.location.file is None:
            raise ValueError('non local definition debug test')
        elif node.location.file.name != os.path.abspath(sys.argv[1]):
            raise ValueError('non local definition debug test')
            #print node.location.file.name
    
    if node.kind == CursorKind.STRUCT_DECL:
        return "class %s(ctypes.Structure):\n  _fields_ = [ %s ]"%(name, ('\n%s'%(' '*15)).join([ str(child) for child in children]))
    elif node.kind == CursorKind.UNION_DECL:
        return "class %s(ctypes.Union):\n  _fields_ = [ %s ]"%(name, ('\n%s'%(' '*12)).join([ str(child) for child in children]))
    elif node.kind == CursorKind.TYPEDEF_DECL:
        return "typedef class %s(ctypes.Structure):\n  _fields...\n  pass\n%s"%(name, children)
    elif node.kind == CursorKind.TYPE_REF:
        return (node, children)
    elif node.kind == CursorKind.FIELD_DECL:
        if node.type.kind == TypeKind.POINTER:
            if node.type.get_pointee().kind == TypeKind.VOID:
                ftype = 'c_void_p'
            else:
                ftype = 'POINTER(%s)'%(node.type.get_pointee().kind.name)
        else:
          ftype = node.type.kind.name
        return "( '%s', %s),"%(node.displayname, ftype )
              #node.type.get_canonical().kind,               #node.type.get_declaration(), 
              #node.type.get_pointee().kind, 
              #node.type.get_result().kind, node.type.data, node.type.kind )
    #elif node.kind == CursorKind.ENUM_DECL:
    #    raise ValueError('ignoreme')
    elif node.kind == CursorKind.FUNCTION_DECL:
        raise ValueError('ignoreme')
    #    return "def %s():\n  pass"%(node.spelling)
#        { # see child 'kind': CursorKind.RETURN_STM
#             'kind' : node.kind,
#             'spelling' : node.spelling }   
    elif node.kind == CursorKind.TRANSLATION_UNIT:
        return children
    else: #if node.is_definition() or True:
        return [ node.kind, name, # node.spelling
             children , ]
    #else:
    #    return { 
    #    'children' : children }
        
    #else:
'''      return { 'id' : get_cursor_id(node),
             'kind' : node.kind,
             'usr' : node.get_usr(),
             'spelling' : node.spelling,
             'location' : node.location,
             'extent.start' : node.extent.start,
             'extent.end' : node.extent.end,
             'is_definition' : node.is_definition(),
             'definition id' : get_cursor_id(node.get_definition()),
             'children' : children }
'''

def main():
    from pprint import pprint

    from optparse import OptionParser, OptionGroup

    global opts

    parser = OptionParser("usage: %prog [options] {filename} [clang-args*]")
    parser.add_option("", "--show-ids", dest="showIDs",
                      help="Don't compute cursor IDs (very slow)",
                      default=False)
    parser.add_option("", "--max-depth", dest="maxDepth",
                      help="Limit cursor expansion to depth N",
                      metavar="N", type=int, default=None)
    parser.disable_interspersed_args()
    (opts, args) = parser.parse_args()

    if len(args) == 0:
        parser.error('invalid number arguments')

    index = Index.create()
    tu = index.parse(None, args)
    if not tu:
        parser.error("unable to load input")

    for node in get_info(tu.cursor):
      print node

if __name__ == '__main__':
    main()

