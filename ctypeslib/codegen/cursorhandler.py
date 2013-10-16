"""Handler for Cursor nodes from the clang AST tree."""

from clang.cindex import CursorKind, TypeKind, TokenKind

from ctypeslib.codegen import typedesc
from ctypeslib.codegen.util import log_entity
from ctypeslib.codegen.handler import ClangHandler
from ctypeslib.codegen.handler import InvalidDefinitionError
from ctypeslib.codegen.handler import CursorKindException
from ctypeslib.codegen.handler import DuplicateDefinitionException

import logging
log = logging.getLogger('cursorhandler')

## DEBUG
import code 

class CursorHandler(ClangHandler):
    """
    Handles Cursor Kind and transform them into typedesc.
    
    # clang.cindex.CursorKind
    ## Declarations: 1-39
    ## Reference: 40-49
    ## Invalids: 70-73
    ## Expressions: 100-143
    ## Statements: 200-231
    ## Root Translation unit: 300
    ## Attributes: 400-403
    ## Preprocessing: 500-503
    """
    def __init__(self, parser):
        ClangHandler.__init__(self, parser)

    def parse_cursor(self, cursor):
        mth = getattr(self, cursor.kind.name)
        return mth(cursor)

    ##########################################################################
    ##### CursorKind handlers#######
    ##########################################################################

    ###########################################
    # ATTRIBUTES
    
    @log_entity
    def UNEXPOSED_ATTR(self, cursor): 
        parent = cursor.semantic_parent
        #print 'parent is',parent.displayname, parent.location, parent.extent
        # TODO until attr is exposed by clang:
        # readlines()[extent] .split(' ') | grep {inline,packed}
        pass

    @log_entity
    def PACKED_ATTR(self, cursor): 
        parent = cursor.semantic_parent
        #print 'parent is',parent.displayname, parent.location, parent.extent
        # TODO until attr is exposed by clang:
        # readlines()[extent] .split(' ') | grep {inline,packed}
        pass

    ################################
    # real element handlers

    #def File(self, attrs):
    #    name = attrs["name"]
    #    if sys.platform == "win32" and " " in name:
    #        # On windows, convert to short filename if it contains blanks
    #        from ctypes import windll, create_unicode_buffer, sizeof, WinError
    #        buf = create_unicode_buffer(512)
    #        if windll.kernel32.GetShortPathNameW(name, buf, sizeof(buf)):
    #            name = buf.value
    #    return typedesc.File(name)
    #
    #def _fixup_File(self, f): pass

    ################################
    # EXPRESSIONS handlers

    '''clang does not expose some types for some expression.
    Example: the type of a token group in a Char_s or char variable.
    Counter example: The type of an integer literal to a (int) variable.'''
    @log_entity
    def UNEXPOSED_EXPR(self, cursor):
        ret = []
        for child in cursor.get_children():
            ret.append( self.parse_cursor(child) )
        if len(ret) == 1:
            return ret[0]
        return ret

    @log_entity
    def DECL_REF_EXPR(self, cursor):
        return cursor.displayname

    @log_entity
    def INIT_LIST_EXPR(self, cursor):
        """Returns a list of literal values."""
        values = [self.parse_cursor(child)
                    for child in list(cursor.get_children())]
        return values

    @log_entity
    def GNU_NULL_EXPR(self, cursor):
        return None

    ################################
    # STATEMENTS handlers

    # Do not traverse into function bodies and other compound statements
    # now fixed by TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    COMPOUND_STMT = ClangHandler._do_nothing

    ################################
    # TYPE REFERENCES handlers
    
    @log_entity
    def TYPE_REF(self, cursor):
        name = self.get_unique_name(cursor)
        if self.is_registered(name):
            return self.get_registered(name)
        #log.warning('TYPE_REF with no saved decl in self.all')
        #return None
        # Should probably never get here.
        # I'm a field. ?
        _definition = cursor.get_definition() 
        if _definition is None: 
            #log.warning('no definition in this type_ref ?')
            #code.interact(local=locals())
            #raise IOError('I doubt this case is possible')
            _definition = cursor.type.get_declaration() 
        return None #self.parse_cursor(_definition)   

    ################################
    # DECLARATIONS handlers
    #
    # UNEXPOSED_DECL are unexposed by clang. Go through the node's children.
    # VAR_DECL are Variable declarations. Initialisation value(s) are collected 
    #          within _get_var_decl_init_value
    #

    UNEXPOSED_DECL = ClangHandler._pass_through_children
    """Undexposed declaration. Go and see children. """
    
    @log_entity
    def ENUM_CONSTANT_DECL(self, cursor):
        """Gets the enumeration values"""
        name = cursor.displayname
        value = cursor.enum_value
        pname = self.get_unique_name(cursor.semantic_parent)
        parent = self.get_registered(pname)        
        obj = typedesc.EnumValue(name, value, parent)
        parent.add_value(obj)
        return obj

    @log_entity
    def ENUM_DECL(self, cursor):
        """Gets the enumeration declaration."""
        name = self.get_unique_name(cursor)
        if self.is_registered(name):
            return self.get_registered(name)
        align = cursor.type.get_align() 
        size = cursor.type.get_size() 
        obj = self.register(name, typedesc.Enumeration(name, size, align))
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def FUNCTION_DECL(self, cursor):
        """Handles function declaration"""
        # FIXME to UT
        name = self.get_unique_name(cursor)
        if self.is_registered(name):
            return self.get_registered(name)
        returns = self.parse_cursor_type(cursor.type.get_result())
        attributes = []
        extern = False
        obj = typedesc.Function(name, returns, attributes, extern)
        for arg in cursor.get_arguments():            
            arg_obj = self.parse_cursor(arg)
            #if arg_obj is None:
            #    code.interact(local=locals())
            obj.add_argument(arg_obj)
        #code.interact(local=locals())
        self.register(name,obj)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def PARM_DECL(self, cursor):
        """Handles parameter declarations."""
        # try and get the type. If unexposed, The canonical type will work.
        _type = cursor.type 
        _name = cursor.spelling
        if ( self.is_array_type(_type) or
             self.is_fundamental_type(_type) or
             self.is_pointer_type(_type) or
             self.is_unexposed_type(_type) ):
            _argtype = self.parse_cursor_type(_type)
        else: # FIXME which UT/case ?
            _argtype_decl = _type.get_declaration()
            _argtype_name = self.get_unique_name(_argtype_decl)
            if not self.is_registered(_argtype_name):
                log.error('this param type is not declared')
                #code.interact(local=locals())
                _argtype = self.parse_cursor_type(_type)
            else:
                _argtype = self.get_registered(_argtype_name)
        obj = typedesc.Argument(_name, _argtype)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def TYPEDEF_DECL(self, cursor):
        """
        Handles typedef statements. 
        Gets Type from cache if we known it. Add it to cache otherwise.
        """
        name = self.get_unique_name(cursor)
        # if the typedef is known, get it from cache
        if self.is_registered(name):
            return self.get_registered(name)
        # use the canonical type directly.
        _type = cursor.type.get_canonical()
        log.debug("TYPEDEF_DECL: name:%s"%(name))
        log.debug("TYPEDEF_DECL: typ.kind.displayname:%s"%(_type.kind))
        #FIXME: check if this can be useful to filter internal declaration
        #_decl_cursor = _type.get_declaration()
        #if _decl_cursor.kind == CursorKind.NO_DECL_FOUND:
        #    log.warning('TYPE %s has no declaration. Builtin type?'%(name))
        #    code.interact(local=locals())        
        
        # For all types (array, fundament, pointer, others), get the type
        p_type = self.parse_cursor_type(_type)
        if not isinstance(p_type, typedesc.T):
            log.error('Bad TYPEREF parsing in TYPEDEF_DECL: %s'%(_type))
            raise TypeError('Bad TYPEREF parsing in TYPEDEF_DECL: %s'%(_type))
        # register the type
        obj = self.register(name, typedesc.Typedef(name, p_type))
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj
               
    @log_entity
    def VAR_DECL(self, cursor):
        """Handles Variable declaration."""
        # get the name
        name = self.get_unique_name(cursor)
        # double declaration ?
        if self.is_registered(name):
            return self.get_registered(name)
        # Get the type
        _ctype = cursor.type.get_canonical()
        # FIXME: Need working int128, long_double, etc...
        if self.is_fundamental_type(_ctype):
            ctypesname = self.get_ctypes_name(_ctype.kind)
            _type = typedesc.FundamentalType( ctypesname, 0, 0 )
            # FIXME: because c_long_double_t or c_unint128 are not real ctypes
            # we can make variable with them.
            # just write the value as-is.
            ### if literal_kind != CursorKind.DECL_REF_EXPR:
            ###    init_value = '%s(%s)'%(ctypesname, init_value)
        elif self.is_unexposed_type(_ctype): # string are not exposed
            # FIXME recurse on child
            log.error('PATCH NEEDED: %s type is not exposed by clang'%(name))
            raise RuntimeError('')
            ctypesname = self.get_ctypes_name(TypeKind.UCHAR)
            _type = typedesc.FundamentalType( ctypesname, 0, 0 )
        elif self.is_array_type(_ctype) or _ctype.kind == TypeKind.RECORD:
            _type = self.parse_cursor_type(_ctype)
        elif self.is_pointer_type(_ctype):
            # extern Function pointer 
            if self.is_unexposed_type(_ctype.get_pointee()): 
                _type = self.parse_cursor_type( _ctype.get_canonical().get_pointee() )
            elif _ctype.get_pointee().kind == TypeKind.FUNCTIONPROTO:
                # Function pointers
                # cursor.type.get_pointee().kind == TypeKind.UNEXPOSED BUT
                # cursor.type.get_canonical().get_pointee().kind == TypeKind.FUNCTIONPROTO
                _type = self.parse_cursor_type( _ctype.get_pointee() )
                #_type = mth(_ctype.get_pointee())
            else: # Fundamental types, structs....
                _type = self.parse_cursor_type(_ctype )
        else:
            # What else ?
            raise NotImplementedError('What other type of variable? %s'%(_ctype.kind))
        ## get the init_value and special cases
        init_value = self._get_var_decl_init_value(cursor.type, 
                                                   list(cursor.get_children()))
        if self.is_unexposed_type(_ctype): 
            # string are not exposed
            init_value = '%s # UNEXPOSED TYPE. PATCH NEEDED.'%(init_value)
        elif ( self.is_pointer_type(_ctype) and 
                _ctype.get_pointee().kind == TypeKind.FUNCTIONPROTO):
            # Function pointers argument are handled inside
            if type(init_value) != list:
                init_value = [init_value]
            _type.arguments = init_value
            init_value = _type
        # finished
        log.debug('VAR_DECL: %s _ctype:%s _type:%s _init:%s location:%s'%(name, 
                    _ctype.kind.name, _type.name, init_value,
                    getattr(cursor, 'location')))
        obj = self.register(name, typedesc.Variable(name, _type, init_value) )
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return True # dont parse literals again

    def _get_var_decl_init_value(self, _ctype, children_iter):
        """
        Gathers initialisation values by parsing children nodes of a VAR_DECL.
        """
        init_value = None
        children = list(children_iter)
        # get the value of this variable 
        if len(children) == 0:
            log.debug('0 children in a var_decl')
            if self.is_array_type(_ctype):
                return []
            return None
        # seen in function pointer with args, 
        if (len(children) != 1):
            # test_codegen.py test_extern_function_pointer_multiarg
            log.debug('Multiple children in a var_decl')
            init_value = []
            for child in children:
                # early stop cases.
                _tmp = None
                try:
                    _tmp = self._get_var_decl_init_value_single(_ctype, child)
                except CursorKindException,e:
                    log.debug('children init value skip on %s'%(child.kind))
                    continue
                if self.is_array_type(_ctype):
                    # the only working child is an INIT_LIST_EXPR
                    init_value = _tmp
                else:                    
                    init_value.append( _tmp )
            if isinstance(init_value, list) and len(init_value) == 0:
                init_value = None
        else:
            child = children[0]
            # get the init value if possible
            try:
                init_value = self._get_var_decl_init_value_single(_ctype, child)
            except CursorKindException,e:
                log.debug('single init value skip on %s'%(child.kind))
                init_value = None
        return init_value
    
    def _get_var_decl_init_value_single(self, _ctype, child):
        """
        Handling of a single child for initialization value.
        Accepted types are expressions and declarations
        """
        log.debug('_ctype: %s Child.kind: %s'%(_ctype.kind, child.kind))
        # shorcuts.
        if not child.kind.is_expression() and not child.kind.is_declaration():
            raise CursorKindException(child.kind)
        if child.kind == CursorKind.CALL_EXPR:
            raise CursorKindException(child.kind)
        ## POD init values handling.
        # As of clang 3.3, int, double literals are exposed.
        # float, long double, char , char* are not exposed directly in level1.
        # but really it depends... 
        if self.is_array_type(_ctype):
            if child.kind == CursorKind.INIT_LIST_EXPR:
                # init value will use INIT_LIST_EXPR
                init_value = self.parse_cursor(child)
            else:
                # probably the literal that indicates the size of the array
                # UT: test_char_p, with "char x[10];"
                init_value = []
            return init_value
        elif child.kind.is_unexposed():
            # recurse until we find a literal kind
            init_value = self._get_var_decl_init_value(_ctype, child.get_children())
        else: # literal or others
            init_value = self.parse_cursor(child)
        return init_value


    @log_entity
    def _literal_handling(self, cursor):
        """Parse all literal associated with this cursor.

        Literal handling is usually useful only for initialization values.
        
        We can't use a shortcut by getting tokens
            ## init_value = ' '.join([t.spelling for t in children[0].get_tokens() 
            ##                         if t.spelling != ';'])
        because some literal might need cleaning."""
        tokens = list(cursor.get_tokens())
        log.debug('literal has %d tokens.[ %s ]'%(len(tokens), 
            str([str(t.spelling) for t in tokens])))
        final_value = []
        #code.interact(local=locals())
        log.debug('cursor.type:%s'%(cursor.type.kind.name))
        for token in tokens:
            value = token.spelling
            log.debug('token:%s tk.kd:%11s tk.cursor.kd:%15s cursor.kd:%15s'%(
                token.spelling, token.kind.name, token.cursor.kind.name, 
                cursor.kind.name))
            # Punctuation is probably not part of the init_value, 
            # but only in specific case: ';' endl, or part of list_expr
            if ( token.kind == TokenKind.PUNCTUATION and 
                 ( token.cursor.kind == CursorKind.INVALID_FILE or
                   token.cursor.kind == CursorKind.INIT_LIST_EXPR)):
                log.debug('IGNORE token %s'%(value))
                continue
            elif token.kind == TokenKind.COMMENT:
                log.debug('Ignore comment %s'%(value))
                continue
            #elif token.cursor.kind == CursorKind.VAR_DECL:
            elif token.location not in cursor.extent:
                log.debug('FIXME BUG: token.location not in cursor.extent %s'%(value))
                # FIXME
                # there is most probably a BUG in clang or python-clang
                # when on #define with no value, a token is taken from 
                # next line. Which break stuff.
                # example:
                #   #define A
                #   extern int i;
                # // this will give "extern" the last token of Macro("A")
                # Lexer is choking ?
                # FIXME BUG: token.location not in cursor.extent
                #code.interact(local=locals())
                continue
            # Cleanup specific c-lang or c++ prefix/suffix for POD types.
            if token.cursor.kind == CursorKind.INTEGER_LITERAL:
                # strip type suffix for constants 
                value = value.replace('L','').replace('U','')
                value = value.replace('l','').replace('u','')
                if value[:2] == '0x' or value[:2] == '0X' :
                    value = '0x%s'%value[2:] #"int(%s,16)"%(value)
                else:
                    value = int(value)
            elif token.cursor.kind == CursorKind.FLOATING_LITERAL:
                # strip type suffix for constants 
                value = value.replace('f','').replace('F','')
                value = float(value)
            elif (token.cursor.kind == CursorKind.CHARACTER_LITERAL or
                  token.cursor.kind == CursorKind.STRING_LITERAL):
                # strip wchar_t type prefix for string/character
                # indicatively: u8 for utf-8, u for utf-16, U for utf32
                # assume that the source file is utf-8
                # utf-32 not supported in 2.7, lets keep all in utf8
                # FIXME python 3
                # max prefix len is 3 char
                if token.cursor.kind == CursorKind.CHARACTER_LITERAL:
                    prefix = value[:3].split("'")[0]
                elif token.cursor.kind == CursorKind.STRING_LITERAL:
                    prefix = value[:3].split('"')[0]
                value = value[len(prefix)+1:-1] # strip delimitors
                # string literal only: R for raw strings
                # we need to remove the raw-char-sequence prefix,suffix
                if 'R' in prefix:
                    # if there is no '(' in the 17 first char, its not valid
                    offset = value[:17].index('(')
                    value = value[offset+1:-offset-1]
                # then we strip encoding
                for encoding in ['u8','L','u','U']:
                    if encoding in prefix: # could be Ru ou uR
                        value = unicode(value,'utf-8')
                        break # just one prefix is possible 
            # add token
            final_value.append(value)
        # return the EXPR    
        #code.interact(local=locals())
        if len(final_value) == 1:
            return final_value[0]
        return final_value

    INTEGER_LITERAL = _literal_handling
    FLOATING_LITERAL = _literal_handling
    IMAGINARY_LITERAL = _literal_handling
    STRING_LITERAL = _literal_handling
    CHARACTER_LITERAL = _literal_handling

    @log_entity
    def _operator_handling(self, cursor):
        """Returns a string with the literal that are part of the operation."""
        values = self._literal_handling(cursor)
        retval = ''.join([str(val) for val in values])
        return retval
    
    UNARY_OPERATOR = _operator_handling
    BINARY_OPERATOR = _operator_handling

    @log_entity
    def STRUCT_DECL(self, cursor):
        """
        Handles Structure declaration.
        Its a wrapper to _record_decl.
        """
        return self._record_decl(cursor, typedesc.Structure)

    @log_entity
    def UNION_DECL(self, cursor):
        """
        Handles Union declaration.
        Its a wrapper to _record_decl.
        """
        return self._record_decl(cursor, typedesc.Union)

    def _record_decl(self, cursor, _output_type):
        """
        Handles record type declaration.
        Structure, Union...
        """
        name = self.get_unique_name(cursor)
        # TODO unittest: try redefinition.
        # check for definition already parsed 
        if (self.is_registered(name) and
            self.get_registered(name).members is not None):
            log.debug('_record_decl: %s is already registered with members'%(name))
            return self.get_registered(name)
        # FIXME: lets ignore bases for now.
        #bases = attrs.get("bases", "").split() # that for cpp ?
        bases = [] # FIXME: support CXX
        size = cursor.type.get_size()
        align = cursor.type.get_align() 
        if align < 0 :
            log.error('invalid structure %s %s align:%d size:%d'%(
                        name, cursor.location, align, size))
            raise InvalidDefinitionError('invalid structure %s %s align:%d size:%d'%(
                                            name, cursor.location, align, size))
        log.debug('_record_decl: name: %s size:%d'%(name, size))
        # Declaration vs Definition point
        # when a struct decl happen before the definition, we have no members
        # in the first declaration instance.
        if not self.is_registered(name) and not cursor.is_definition():
            # juste save the spot, don't look at members == None
            log.debug('XXX cursor %s is not on a definition'%(name))
            obj = _output_type(name, align, None, bases, size, packed=False)
            return self.register(name, obj)
        log.debug('XXX cursor %s is a definition'%(name))
        # save the type in the registry. Useful for not looping in case of 
        # members with forward references
        obj = None
        declared_instance = False
        if not self.is_registered(name): 
            obj = _output_type(name, align, None, bases, size, packed=False)
            self.register(name, obj)
            self.set_location(obj, cursor)
            self.set_comment(obj, cursor)
            declared_instance = True
        # capture members declaration
        members = []
        # Go and recurse through children to get this record member's _id
        # Members fields will not be "parsed" here, but later.
        prev_child_offset = prev_child_size = 0
        fields = list(cursor.type.get_fields())
        log.debug('Fields: %s'%(str(['%s/%s'%(f.kind.name, f.spelling) for f in fields])))
        for childnum, child in enumerate(fields):
            if child.kind == CursorKind.FIELD_DECL:
                members.append( self.FIELD_DECL(child) )
            elif child.kind == CursorKind.PACKED_ATTR:
                obj.packed = True
                continue # dont mess with field calculations
            else: ## could be others....
                log.error('Unhandled field %s in record %s'%(child.kind, name))
                continue
            prev_child_size = members[-1].bits
            prev_child_offset = members[-1].offset+prev_child_size
            
        if self.is_registered(name): 
            # STRUCT_DECL as a child of TYPEDEF_DECL for example
            # FIXME: make a test case for that.
            if not declared_instance:
                log.debug('_record_decl: %s was previously registered'%(name))
            obj = self.get_registered(name)
            obj.members = members
            # final fixup
            self._fixup_record(obj)
        return obj

    def _fixup_record(self, s):
        """Fixup padding on a record"""
        log.debug('FIXUP_STRUCT: %s %d bits'%(s.name,s.size*8))
        if s.members is None:
            log.debug('FIXUP_STRUCT: no members')
            s.members = []
            return
        ## No need to lookup members in a global var.
        ## Just fix the padding        
        members = []
        member = None
        offset = 0
        padding_nb = 0
        # create padding fields
        for member in s.members: 
            log.debug('FIXUP_STRUCT: field:%s offset:%d->%d expecting offset:%d'%(
                    member.name, member.offset, member.offset + member.bits, offset))
            if member.offset > offset:
                #create padding
                length = member.offset - offset
                p_name = 'PADDING_%d'%padding_nb
                log.debug('FIXUP_STRUCT: create %s for %d bits %d bytes'%(p_name, length, length/8))
                padding = self._make_padding(p_name, offset, length)
                members.append(padding)
                padding_nb+=1
            if member.type is None:
                log.error('FIXUP_STRUCT: %s.type is None'%(member.name))
            members.append(member)
            offset = member.offset + member.bits
        # tail padding if necessary and last field is NOT a bitfield
        # FIXME: this isn't right. Why does Union.size returns 1.
        # Probably because of sizeof returning standard size instead of real size
        if member and member.is_bitfield:
            pass
        elif s.size*8 > offset:                
            length = s.size*8 - offset
            log.debug('FIXUP_STRUCT: s:%d create tail padding for %d bits %d bytes'%(s.size, length, length/8))
            p_name = 'PADDING_%d'%padding_nb
            padding = self._make_padding(p_name, offset, length)
            members.append(padding)
        elif s.size*8 < offset:
            log.debug('FIXUP_STRUCT: s:%d final_offset:%d '%(s.size*8, offset))
            #raise RuntimeError('bad calcs for offset')
        if len(members) > 0:
            offset = members[-1].offset + members[-1].bits
        # go
        s.members = members
        log.debug("FIXUP_STRUCT: size:%d offset:%d"%(s.size*8, offset))
        # FIXME:
        #if member and not member.is_bitfield:
        #    assert offset == s.size*8 #, assert that the last field stop at the size limit
        return

    _fixup_Structure = _fixup_record
    _fixup_Union = _fixup_record

    def _make_padding(self, name, offset, length):
        """Make padding Fields for a specifed size."""
        log.debug("_make_padding: for %d bits"%(length))
        if (length % 8) != 0:
            # FIXME
            log.warning('_make_padding: FIXME we need sub-bytes padding definition')
        if length > 8:
            bytes = length/8
            return typedesc.Field(name,
                     typedesc.ArrayType(
                       typedesc.FundamentalType(
                         self.get_ctypes_name(TypeKind.CHAR_U), length, 1 ),
                       bytes),
                     offset, length)
        return typedesc.Field(name,
                 typedesc.FundamentalType( self.get_ctypes_name(TypeKind.CHAR_U), 1, 1 ),
                 offset, length)


    # FIXME
    CLASS_DECL = STRUCT_DECL
    _fixup_Class = _fixup_record

    @log_entity
    def FIELD_DECL(self, cursor):
        """
        Handles Field declarations.
        Some specific treatment for a bitfield.
        """
        # name, type
        name = self.get_unique_name(cursor)
        parent = cursor.semantic_parent
        #record_name = parent.spelling
        record_name = self.get_unique_name(cursor.semantic_parent)
        #_id = cursor.get_usr()
        # anonymous fields
        if cursor.displayname == '': # cursor.is_anonymous()
            is_anonymous = True
            # get offset by iterating all fields of parent
            offset = cursor.get_field_offsetof()
            for i,_f in enumerate(parent.type.get_fields()):
                if _f == cursor:
                    fieldnum = i
                    break
            # make a name
            name = "_%d"%(fieldnum)
            log.warning("Cursor has no displayname - anonymous field renamed to %s"%(name))
        else:
            offset = parent.type.get_offset(name)
            if offset < 0:
                log.error('BAD RECORD, Bad offset: %d for %s'%(offset, name))
                # FIXME if c++ class ?
            is_anonymous = False
        # bitfield
        bits = None
        if cursor.is_bitfield():
            bits = cursor.get_bitfield_width()
            name = "anonymous_bitfield"
        else:
            #code.interact(local=locals())
            bits = cursor.type.get_size() * 8
            if bits < 0:
                log.warning('Bad source code, bitsize == %d <0 on %s'%(bits, name))
                bits = 0
        # after dealing with anon bitfields
        if name == '': 
            raise ValueError("Field has no displayname")
        # try to get a representation of the type
        ##_canonical_type = cursor.type.get_canonical()
        # t-t-t-t-
        _type = None
        _canonical_type = cursor.type.get_canonical()
        _decl = cursor.type.get_declaration()
        if ( self.is_array_type(_canonical_type) or
             self.is_fundamental_type(_canonical_type) or
             self.is_pointer_type(_canonical_type)):
            _type = self.parse_cursor_type(_canonical_type)
        else:
            children = list(cursor.get_children())
            if len(children) > 0 and _decl.kind == CursorKind.NO_DECL_FOUND:
                # constantarray of typedef of pointer , and other cases ?
                _decl_name = self.get_unique_name(list(cursor.get_children())[0])
            else:
                _decl_name = self.get_unique_name(cursor.type.get_declaration()) # .spelling ??
            # rename anonymous field type name
            if is_anonymous:
                _decl_name += name
            if self.is_registered(_decl_name):
                log.debug('FIELD_DECL: used type from cache: %s'%(_decl_name))
                _type = self.get_registered(_decl_name)
                # then we shortcut
            else:
                # is it always the case ?
                log.debug("FIELD_DECL: name:'%s'"%(_decl_name))
                log.debug("FIELD_DECL: %s: nb children:%s"%(cursor.type.kind, 
                                len(children)))
                # recurse into the right function
                _type = self.parse_cursor_type(_canonical_type)
                if _type is None:
                    log.warning("Field %s is an %s type - ignoring field type"%(
                                name,_canonical_type.kind.name))
                    return None
        if is_anonymous:
            # we have to unregister the _type and register a alternate named type.
            self.parser.remove_registered(_type.name)
            _type.name = _decl_name
            self.register(_decl_name, _type)
        return typedesc.Field(name, _type, offset, bits, 
                              is_bitfield=cursor.is_bitfield(),
                              is_anonymous=is_anonymous)
                              #is_anonymous=cursor.is_anonymous())

    #############################
    # PREPROCESSING

    @log_entity
    def MACRO_DEFINITION(self, cursor):
        """
        Parse MACRO_DEFINITION, only present if the TranslationUnit is 
        used with TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD.
        """
        # TODO: optionalize macro parsing. It takes a LOT of time.
        name = self.get_unique_name(cursor)
        #if name == 'A':
        #    code.interact(local=locals())
        # Tokens !!! .kind = {IDENTIFIER, KEYWORD, LITERAL, PUNCTUATION, 
        # COMMENT ? } etc. see TokenKinds.def
        comment = None
        tokens = self._literal_handling(cursor)
        # Macro name is tokens[0]
        # get Macro value(s)
        value = True
        if isinstance(tokens, list):
            if len(tokens) == 2 :
                value = tokens[1]
            else:
                value = tokens[1:]
        # macro comment maybe in tokens. Not in cursor.raw_comment
        for t in cursor.get_tokens():
            if t.kind == TokenKind.COMMENT:
                comment = t.spelling
        # special case. internal __null
        # FIXME, there are probable a lot of others.
        # why not Cursor.kind GNU_NULL_EXPR child instead of a token ?
        if name == 'NULL' or value == '__null':
            value = None
        log.debug('MACRO: #define %s %s'%(tokens[0], value))
        obj = typedesc.Macro(name, None, value)
        try:
            self.register(name, obj)
        except DuplicateDefinitionException, e:
            log.info('Redefinition of %s %s->%s'%(name, self.parser.all[name].args, value))
            # HACK 
            self.parser.all[name] = obj
            pass
        self.set_location(obj, cursor)
        # set the comment in the obj 
        obj.comment = comment
        return True


    

