"""Handler for Cursor nodes from the clang AST tree."""

import logging
import re

from ctypeslib.codegen.cindex import CursorKind, LinkageKind, TypeKind, TokenKind

from ctypeslib.codegen import typedesc
from ctypeslib.codegen.handler import ClangHandler
from ctypeslib.codegen.handler import CursorKindException
from ctypeslib.codegen.handler import DuplicateDefinitionException
from ctypeslib.codegen.handler import InvalidDefinitionError
from ctypeslib.codegen.cache import cached_pure_method
from ctypeslib.codegen.preprocess import (
    is_identifier,
    from_c_int_literal,
    from_c_float_literal,
    from_c_string_literal,
    process_c_literals,
    process_macro_function,
    remove_outermost_parentheses,
)
from ctypeslib.codegen.util import (
    contains_invalid_code,
    expand_macro_function,
    log_entity,
)


log = logging.getLogger('cursorhandler')


class CursorTokens:
    def __init__(self, tokens):
        self._tokens = list(tokens)
        self._index = 0

    @property
    def index(self):
        return self._index

    def __len__(self):
        return len(self._tokens)

    def __iter__(self):
        return iter(self._tokens)

    def __getitem__(self, i):
        return self._tokens[i]

    def __bool__(self):
        return self._index < len(self._tokens)

    @property
    def current(self):
        if not self:
            return None
        return self._tokens[self._index]

    def consume(self, count=1):
        if self:
            ret = self.current
            self._index += count
        return ret

    def consume_lit(self, lit):
        if self.current.spelling == lit:
            self.consume()
            return True
        return False


CharTypes = [
    TypeKind.CHAR_U,
    TypeKind.UCHAR,
    TypeKind.CHAR16,
    TypeKind.CHAR32,
    TypeKind.CHAR_S,
    TypeKind.SCHAR,
    TypeKind.WCHAR,
]

IntegerTypes = [
    TypeKind.USHORT,
    TypeKind.UINT,
    TypeKind.ULONG,
    TypeKind.ULONGLONG,
    TypeKind.UINT128,
    TypeKind.SHORT,
    TypeKind.INT,
    TypeKind.LONG,
    TypeKind.LONGLONG,
    TypeKind.INT128,
]

FloatTypes = [
    TypeKind.FLOAT,
    TypeKind.DOUBLE,
    TypeKind.LONGDOUBLE,
]


class CursorHandler(ClangHandler):
    """
    Factory objects that handles Cursor Kind and transform them into typedesc.

    # clang.cindex.CursorKind
    # Declarations: 1-39
    # Reference: 40-49
    # Invalids: 70-73
    # Expressions: 100-143
    # Statements: 200-231
    # Root Translation unit: 300
    # Attributes: 400-403
    # Preprocessing: 500-503
    """

    def __init__(self, parser):
        ClangHandler.__init__(self, parser)

    @cached_pure_method()
    def parse_cursor(self, cursor):
        name = cursor.kind.name
        mth = getattr(self, name)
        return mth(cursor)

        ##########################################################################
        ##### CursorKind handlers#######
        ##########################################################################

        ###########################################
        # ATTRIBUTES

        # @log_entity
        # def UNEXPOSED_ATTR(self, cursor):
        # FIXME: do we do something with these ?
        # parent = cursor.semantic_parent
        # print 'parent is',parent.displayname, parent.location, parent.extent
        # TODO until attr is exposed by clang:
        # readlines()[extent] .split(' ') | grep {inline,packed}
        #    return

        # @log_entity
        # def PACKED_ATTR(self, cursor):
        # FIXME: do we do something with these ?
        # parent = cursor.semantic_parent
        # print 'parent is',parent.displayname, parent.location, parent.extent
        # TODO until attr is exposed by clang:
        # readlines()[extent] .split(' ') | grep {inline,packed}

    #    return

    ################################
    # EXPRESSIONS handlers

    # clang does not expose some types for some expression.
    # Example: the type of a token group in a Char_s or char variable.
    # Counter example: The type of an integer literal to a (int) variable.
    @log_entity
    def UNEXPOSED_EXPR(self, cursor):
        ret = []
        for child in cursor.get_children():
            ret.append(self.parse_cursor(child))
        if len(ret) == 1:
            return ret[0]
        return ret

    @log_entity
    def DECL_REF_EXPR(self, cursor):
        return cursor.displayname

    def _cast_list_expr(self, type_kind, value):
        if not isinstance(value, str):
            return value
        try:
            if type_kind in IntegerTypes:
                return from_c_int_literal(value, self.parser.get_pointer_width())
            elif type_kind in FloatTypes:
                return from_c_float_literal(value)
            elif type_kind in CharTypes:
                return value
        except ValueError:
            return value

    @log_entity
    def INIT_LIST_EXPR(self, cursor):
        """Returns a list of literal values."""
        values = [self.parse_cursor(child)
                  for child in list(cursor.get_children())]
        element_type = cursor.type.get_array_element_type().kind
        values = list(map(lambda v: self._cast_list_expr(element_type, v), values))
        return values

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
        # log.warning('TYPE_REF with no saved decl in self.all')
        # return None
        # Should probably never get here.
        # I'm a field. ?
        _definition = cursor.get_definition()
        if _definition is None:
            # log.warning('no definition in this type_ref ?')
            # code.interact(local=locals())
            # raise IOError('I doubt this case is possible')
            _definition = cursor.type.get_declaration()
        return None  # self.parse_cursor(_definition)

    ################################
    # DECLARATIONS handlers
    #
    # UNEXPOSED_DECL are unexposed by clang. Go through the node's children.
    # VAR_DECL are Variable declarations. Initialisation value(s) are collected
    #          within _get_var_decl_init_value
    #

    NO_DECL_FOUND = ClangHandler._do_nothing

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
        obj = typedesc.Enumeration(name, size, align)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        obj = self.register(name, obj)
        # parse all children
        for child in cursor.get_children():
            self.parse_cursor(child)  # FIXME, where is the starElement
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
        obj = self.register(name, obj)
        for arg in cursor.get_arguments():
            arg_obj = self.parse_cursor(arg)
            # if arg_obj is None:
            #    code.interact(local=locals())
            obj.add_argument(arg_obj)
        # code.interact(local=locals())
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        obj = self.update_register(name, obj)
        return obj

    @log_entity
    def PARM_DECL(self, cursor):
        """Handles parameter declarations."""
        # try and get the type. If unexposed, The canonical type will work.
        _type = cursor.type
        name = cursor.spelling
        if (self.is_array_type(_type) or
                self.is_fundamental_type(_type) or
                self.is_pointer_type(_type) or
                self.is_unexposed_type(_type)):
            _argtype = self.parse_cursor_type(_type)
        else:  # FIXME: Which UT/case ? size_t in stdio.h for example.
            _argtype_decl = _type.get_declaration()
            _argtype_name = self.get_unique_name(_argtype_decl)
            if not self.is_registered(_argtype_name):
                log.info('This param type is not declared: %s', _argtype_name)
                _argtype = self.parse_cursor_type(_type)
            else:
                _argtype = self.get_registered(_argtype_name)
        obj = typedesc.Argument(name, _argtype)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        return obj

    @log_entity
    def TYPEDEF_DECL(self, cursor):
        """
        Handles typedef statements.
        Gets Type from cache if we known it. Add it to cache otherwise.
        # typedef of an enum
        """
        name = self.get_unique_name(cursor)
        # if the typedef is known, get it from cache
        if self.is_registered(name):
            return self.get_registered(name)
        # use the canonical type directly.
        _type = cursor.type.get_canonical()
        log.debug("TYPEDEF_DECL: name:%s", name)
        log.debug("TYPEDEF_DECL: typ.kind.displayname:%s", _type.kind)

        # For all types (array, fundament, pointer, others), get the type
        p_type = self.parse_cursor_type(_type)
        if not isinstance(p_type, typedesc.T):
            log.error(
                'Bad TYPEREF parsing in TYPEDEF_DECL: %s',
                _type.spelling)
            # import code
            # code.interact(local=locals())
            raise TypeError(
                'Bad TYPEREF parsing in TYPEDEF_DECL: %s' %
                (_type.spelling))
        # register the type
        obj = typedesc.Typedef(name, p_type)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        obj = self.register(name, obj)
        return obj

    @log_entity
    def VAR_DECL(self, cursor):
        """Handles Variable declaration."""
        # get the name
        name = self.get_unique_name(cursor)
        log.debug('VAR_DECL: name: %s', name)
        # Check for a previous declaration in the register
        if self.is_registered(name):
            return self.get_registered(name)
        # get the typedesc object
        _type, extern = self._VAR_DECL_type(cursor)
        # transform the ctypes values into ctypeslib
        init_value = self._VAR_DECL_value(cursor, _type)
        # finished
        log.debug('VAR_DECL: _type:%s', _type.name)
        log.debug('VAR_DECL: _init:%s', init_value)
        log.debug('VAR_DECL: location:%s', getattr(cursor, 'location'))
        obj = typedesc.Variable(name, _type, init_value, extern)
        self.set_location(obj, cursor)
        self.set_comment(obj, cursor)
        obj = self.register(name, obj)
        return True

    def _VAR_DECL_type(self, cursor):
        """Generates a typedesc object from a Variable declaration."""
        # Get the type
        _ctype = cursor.type.get_canonical()
        extern = cursor.linkage in (LinkageKind.EXTERNAL, LinkageKind.UNIQUE_EXTERNAL)
        log.debug('VAR_DECL: _ctype: %s ', _ctype.kind)
        # FIXME: Need working int128, long_double, etc.
        if self.is_fundamental_type(_ctype):
            ctypesname = self.get_ctypes_name(_ctype.kind)
            _type = typedesc.FundamentalType(ctypesname, 0, 0)
        elif self.is_unexposed_type(_ctype):
            st = 'PATCH NEEDED: %s type is not exposed by clang' % (
                self.get_unique_name(cursor))
            log.error(st)
            raise RuntimeError(st)
        elif self.is_array_type(_ctype) or _ctype.kind == TypeKind.RECORD:
            _type = self.parse_cursor_type(_ctype)
        elif self.is_pointer_type(_ctype):
            # for example, extern Function pointer
            if self.is_unexposed_type(_ctype.get_pointee()):
                _type = self.parse_cursor_type(
                    _ctype.get_canonical().get_pointee()
                )
            elif _ctype.get_pointee().kind == TypeKind.FUNCTIONPROTO:
                # Function pointers
                # Arguments are handled in here
                _type = self.parse_cursor_type(_ctype.get_pointee())
            else:  # Pointer to Fundamental types, structs....
                _type = self.parse_cursor_type(_ctype)
        else:
            # What else ?
            raise NotImplementedError(
                'What other type of variable? %s' %
                (_ctype.kind))
        log.debug('VAR_DECL: _type: %s ', _type)
        return _type, extern

    def _VAR_DECL_value(self, cursor, _type):
        """Handles Variable value initialization."""
        # always expect list [(k,v)] as init value.from list(cursor.get_children())
        # get the init_value and special cases
        init_value = self._get_var_decl_init_value(cursor.type,
                                                   list(cursor.get_children()))
        _ctype = cursor.type.get_canonical()
        if self.is_unexposed_type(_ctype):
            # string are not exposed
            init_value = '%s # UNEXPOSED TYPE. PATCH NEEDED.' % (init_value)
        elif (self.is_pointer_type(_ctype) and
                      _ctype.get_pointee().kind == TypeKind.FUNCTIONPROTO):
            # Function pointers argument are handled at type creation time
            # but we need to put a CFUNCTYPE as a value of the name variable
            init_value = _type
        elif self.is_array_type(_ctype):
            # an integer literal will be the size
            # a string literal will be the value
            # any list member will be children of a init_list_expr
            # FIXME Move that code into typedesc
            def countof(k, l):
                return [item[0] for item in l].count(k)

            if countof(CursorKind.INIT_LIST_EXPR, init_value) == 1:
                init_value = dict(init_value)[CursorKind.INIT_LIST_EXPR]
            elif countof(CursorKind.STRING_LITERAL, init_value) == 1:
                # we have a initialised c_array
                init_value = dict(init_value)[CursorKind.STRING_LITERAL]
            else:
                # ignore size alone
                init_value = []
            # check the array size versus elements.
            if _type.size < len(init_value):
                _type.size = len(init_value)
        elif init_value == []:
            # catch case.
            init_value = None
        else:
            log.debug('VAR_DECL: default init_value: %s', init_value)

            def cast_value(cursor_kind, value):
                if cursor_kind == CursorKind.INTEGER_LITERAL:
                    return int(value)
                elif cursor_kind == CursorKind.FLOATING_LITERAL:
                    return float(value)
                else:
                    return value
            if len(init_value) > 0:
                init_value = list(map(lambda i: cast_value(*i), init_value))
            if len(init_value) == 1:
                init_value = init_value[0]
        return init_value

    def _get_var_decl_init_value(self, _ctype, children):
        """
        Gathers initialisation values by parsing children nodes of a VAR_DECL.
        """

        # FIXME TU for INIT_LIST_EXPR
        # FIXME: always return [(child.kind,child.value),...]
        # FIXME: simplify this redondant code.
        init_value = []
        children = list(children)  # weird requirement, list iterator error.
        log.debug('_get_var_decl_init_value: children #: %d', len(children))
        for child in children:
            # early stop cases.
            _tmp = None
            try:
                _tmp = self._get_var_decl_init_value_single(_ctype, child)
            except CursorKindException:
                log.debug(
                    '_get_var_decl_init_value: children init value skip on %s',
                    child.kind)
                continue
            if _tmp is not None:
                init_value.append(_tmp)
        return init_value

    def _get_var_decl_init_value_single(self, _ctype, child):
        """
        Handling of a single child for initialization value.
        Accepted types are expressions and declarations
        """
        init_value = None
        # FIXME: always return (child.kind, child.value)
        log.debug(
            '_get_var_decl_init_value_single: _ctype: %s Child.kind: %s',
            _ctype.kind,
            child.kind)
        # shorcuts.
        if not child.kind.is_expression() and not child.kind.is_declaration():
            raise CursorKindException(child.kind)
        if child.kind == CursorKind.CALL_EXPR:
            raise CursorKindException(child.kind)
        # POD init values handling.
        # As of clang 3.3, int, double literals are exposed.
        # float, long double, char , char* are not exposed directly in level1.
        # but really it depends...
        if child.kind.is_unexposed():
            # recurse until we find a literal kind
            init_value = self._get_var_decl_init_value(_ctype, child.get_children())
            if len(init_value) == 0:
                init_value = None
            elif len(init_value) == 1:
                init_value = init_value[0]
            else:
                log.error('_get_var_decl_init_value_single: Unhandled case')
                assert len(init_value) <= 1
        # elif child.kind == CursorKind.STRING_LITERAL:
        #     _v = self._literal_handling(child)
        #     init_value = (child.kind, _v)
        else:  # literal or others
            _v = self.parse_cursor(child)
            if isinstance(_v, list) and len(_v) > 0 and child.kind not in [CursorKind.INIT_LIST_EXPR, CursorKind.STRING_LITERAL]:
                log.warning('_get_var_decl_init_value_single: TOKENIZATION BUG CHECK: %s', _v)
                _v = _v[0]
            init_value = (child.kind, _v)
        log.debug('_get_var_decl_init_value_single: returns %s', str(init_value))
        return init_value

    @cached_pure_method()
    def _clean_string_literal(self, cursor, value):
        # strip wchar_t type prefix for string/character
        # indicatively: u8 for utf-8, u for utf-16, U for utf32
        # assume that the source file is utf-8
        # utf-32 not supported in 2.7, lets keep all in utf8
        # string prefixes https://en.cppreference.com/w/cpp/language/string_literal
        # integer suffixes https://en.cppreference.com/w/cpp/language/integer_literal
        if cursor.kind in [CursorKind.CHARACTER_LITERAL, CursorKind.STRING_LITERAL]:
            return from_c_string_literal(value)
        elif cursor.kind == CursorKind.MACRO_DEFINITION:
            return process_c_literals(value)
        else:
            return value

    @cached_pure_method()
    def _macro_args_handling(self, tokens, call_args=False):
        if tokens.current is None:
            return tuple()
        args = []
        if not tokens.consume_lit("("):
            return None
        balance = 0
        while tokens:
            if balance == 0 and tokens.consume_lit(")"):
                break
            if tokens.consume_lit(","):
                continue
            if tokens.consume_lit("("):
                balance += 1
            elif tokens.consume_lit(")"):
                balance -= 1
            elif is_identifier(str(tokens.current.spelling)):
                args.append(tokens.consume().spelling)
            else:
                if call_args:
                    args.append(tokens.consume().spelling)
                else:
                    return None
        return tuple(args)

    @cached_pure_method()
    def _get_cursor_tokens(self, cursor):
        return CursorTokens(cursor.get_tokens())

    @log_entity
    @cached_pure_method()
    def _literal_handling(self, cursor):
        """Parse all literal associated with this cursor.

        Literal handling is usually useful only for initialization values.

        We can't use a shortcut by getting tokens
            # init_value = ' '.join([t.spelling for t in children[0].get_tokens()
            # if t.spelling != ';'])
        because some literal might need cleaning."""
        # FIXME #77, internal integer literal like __clang_major__ are not working here.
        # tokens == [] , because ??? clang problem ? so there is no spelling available.
        tokens = self._get_cursor_tokens(cursor)
        log.debug('literal has %d tokens.[ %s ]', len(tokens), ' '.join([str(t.spelling) for t in tokens]))

        if cursor.kind == CursorKind.STRING_LITERAL:
            if len(tokens) == 1:
                # use a shortcut that works for unicode
                value = tokens[0].spelling
                value = self._clean_string_literal(cursor, value)
                return value
            else:
                # use a shortcut - does not work on unicode var_decl
                value = cursor.displayname
                value = self._clean_string_literal(cursor, value)
                return value
        final_value = []
        # code.interact(local=locals())
        log.debug('cursor.type:%s', cursor.type.kind.name)
        while tokens:
            token = tokens.current
            value = token.spelling
            log.debug('token:%s tk.kd:%11s tk.cursor.kd:%15s cursor.kd:%15s',
                      token.spelling, token.kind.name, token.cursor.kind.name,
                      cursor.kind.name)
            # Punctuation is probably not part of the init_value,
            # but only in specific case: ';' endl, or part of list_expr
            if (token.kind == TokenKind.PUNCTUATION and
                    (token.cursor.kind == CursorKind.INVALID_FILE or
                        token.cursor.kind == CursorKind.INIT_LIST_EXPR)):
                log.debug('IGNORE token %s', value)
                # consume token
                tokens.consume()
                token = tokens.current
                continue
            elif token.kind == TokenKind.COMMENT:
                log.debug('Ignore comment %s', value)
                # consume token
                tokens.consume()
                token = tokens.current
                continue
            # elif token.cursor.kind == CursorKind.VAR_DECL:
            elif token.location not in cursor.extent:
                # log.debug('FIXME BUG: token.location not in cursor.extent %s', value)
                # 2021 clang 11, this seems fixed ?
                # there is most probably a BUG in clang or python-clang
                # when on #define with no value, a token is taken from
                # next line. Which break stuff.
                # example:
                #   #define A
                #   extern int i;
                # // this will give "extern" the last token of Macro("A")
                # Lexer is choking ?
                # FIXME BUG: token.location not in cursor.extent
                # code.interact(local=locals())
                # consume token
                tokens.consume()
                token = tokens.current
                continue
            # Cleanup specific c-lang or c++ prefix/suffix for POD types.
            if token.cursor.kind == CursorKind.INTEGER_LITERAL:
                # strip type suffix for constants
                value = str(from_c_int_literal(value, self.parser.get_pointer_width()))
                # consume token
                tokens.consume()
                token = tokens.current
            elif token.cursor.kind == CursorKind.FLOATING_LITERAL:
                # strip type suffix for constants
                value = str(from_c_float_literal(value))
                # consume token
                tokens.consume()
                token = tokens.current
            elif token.cursor.kind == CursorKind.CHARACTER_LITERAL:
                value = self._clean_string_literal(token.cursor, value)
                # consume token
                tokens.consume()
                token = tokens.current
            elif token.cursor.kind == CursorKind.STRING_LITERAL:
                value = self._clean_string_literal(token.cursor, value)
                # consume token
                tokens.consume()
                token = tokens.current
            elif token.cursor.kind == CursorKind.MACRO_INSTANTIATION:
                # get the macro value
                value = self.get_registered(value).body
                # consume token
                tokens.consume()
                token = tokens.current
                # already cleaned value = self._clean_string_literal(token.cursor, value)
            elif token.cursor.kind == CursorKind.MACRO_DEFINITION:
                tk = token.kind
                if tokens.index == 0:
                    # ignore, macro name
                    # consume token
                    tokens.consume()
                    token = tokens.current
                elif token.kind == TokenKind.LITERAL:
                    # and just clean it
                    value = self._clean_string_literal(token.cursor, value)
                    # consume token
                    tokens.consume()
                    token = tokens.current
                elif token.kind == TokenKind.IDENTIFIER:
                    # log.debug("Ignored MACRO_DEFINITION token identifier : %s", value)
                    # Identifier in Macro... Not sure what to do with that.
                    if self.is_registered(value):
                        # FIXME: if Macro is not a simple value replace, it should not be registered in the first place
                        # parse that, try to see if there is another Macro in there.
                        if hasattr(self.get_registered(value), "body"):
                            macro = self.get_registered(value)
                            if contains_invalid_code(macro):
                                log.debug("MACRO_DEFINITION contains invalid code(s) : %s", value)
                                value = typedesc.UndefinedIdentifier(value)
                                # consume token
                                tokens.consume()
                                token = tokens.current
                            else:
                                log.debug("Found MACRO_DEFINITION token identifier : %s", value)
                                if macro.args:
                                    tokens.consume()
                                    token = tokens.current
                                    call_args = self._macro_args_handling(tokens, call_args=True)
                                    expansion_limit = None
                                    if self.parser.advanced_macro:
                                        expansion_limit = 1
                                    value = expand_macro_function(
                                        macro, call_args, namespace=self.parser.interpreter_namespace, limit=expansion_limit)
                                    token = tokens.current
                                else:
                                    value = macro.body
                                    # consume token
                                    tokens.consume()
                                    token = tokens.current
                        else:
                            value = typedesc.UndefinedIdentifier(value)
                            log.debug("Undefined MACRO_DEFINITION token identifier : %s", value)
                            # consume token
                            tokens.consume()
                            token = tokens.current
                    else:
                        value = typedesc.UndefinedIdentifier(value)
                        log.debug("Undefined MACRO_DEFINITION token identifier : %s", value)
                        # consume token
                        tokens.consume()
                        token = tokens.current
                elif token.kind == TokenKind.KEYWORD:
                    log.debug("Got a MACRO_DEFINITION referencing a KEYWORD token.kind: %s", token.kind.name)
                    value = typedesc.UndefinedIdentifier(value)
                    # consume token
                    tokens.consume()
                    token = tokens.current
                elif token.kind == TokenKind.PUNCTUATION:
                    # FIXME: handle PUNCTUATION
                    # log.debug("Ignored MACRO_DEFINITION token.kind: %s", token.kind.name)
                    # consume token
                    tokens.consume()
                    token = tokens.current
                else:
                    log.warning("Unhandled token %s" % token.kind)
                    # consume token
                    tokens.consume()
                    token = tokens.current
            elif token.kind == TokenKind.PUNCTUATION:
                # consume token
                tokens.consume()
                token = tokens.current
            else:
                log.warning("Unhandled token %s" % token.kind)
                # consume token
                tokens.consume()
                token = tokens.current

            # add token
            if value is not None:
                final_value.append(value)

        # return the EXPR
        # code.interact(local=locals())
        # FIXME, that will break. We need constant type return
        if len(final_value) == 1:
            return final_value[0]
        # Macro definition of a string using multiple macro
        if isinstance(final_value, list):
            if cursor.kind == CursorKind.STRING_LITERAL:
                final_value = ''.join(final_value)
        log.debug('_literal_handling final_value: %s', final_value)
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
        log.debug('cursor.type.kind:%s', cursor.type.kind.name)
        if cursor.kind == CursorKind.UNARY_OPERATOR:
            if cursor.type.kind in [TypeKind.INT, TypeKind.LONG]:
                if '0x' in retval:
                    retval = int(retval, 16)
                else:
                    try:
                        retval = int(retval)
                    except ValueError:
                        # fall back on pass through
                        pass
            elif cursor.type.kind in [TypeKind.FLOAT, TypeKind.DOUBLE]:
                retval = float(retval)
        # Things we do not want to do:
        # elif cursor.kind == CursorKind.BINARY_OPERATOR:
        #     # cursor.kind == binary_operator, then need to make some additions
        #     retval = eval(retval)

        return retval

    UNARY_OPERATOR = _operator_handling
    BINARY_OPERATOR = _operator_handling

    @log_entity
    def STRUCT_DECL(self, cursor, num=None):
        """
        Handles Structure declaration.
        Its a wrapper to _record_decl.
        """
        return self._record_decl(cursor, typedesc.Structure, num)

    @log_entity
    def UNION_DECL(self, cursor, num=None):
        """
        Handles Union declaration.
        Its a wrapper to _record_decl.
        """
        return self._record_decl(cursor, typedesc.Union, num)

    def _record_decl(self, cursor, _output_type, num=None):
        """
        Handles record type declaration.
        Structure, Union...
        """
        name = self.get_unique_name(cursor)
        # FIXME, handling anonymous field by adding a child id.
        if num is not None:
            name = "%s_%d", name, num
        # TODO unittest: try redefinition.
        # Find if a record definition was already parsed and registered
        if (self.is_registered(name) and
                    self.get_registered(name).members is not None):
            log.debug(
                '_record_decl: %s is already registered with members',
                name)
            return self.get_registered(name)
        # FIXME: lets ignore bases for now.
        # bases = attrs.get("bases", "").split() # that for cpp ?
        bases = []  # FIXME: support CXX
        size = cursor.type.get_size()
        align = cursor.type.get_align()
        if size == -2: #
            # CXTypeLayoutError_Incomplete = -2
            # produce an empty structure declaration
            size = align = 0
            log.debug('_record_decl: name: %s CXTypeLayoutError_Incomplete', name)
            obj = _output_type(name, align, None, bases, size, packed=False)
            self.set_location(obj, cursor)
            self.set_comment(obj, cursor)
            return self.register(name, obj)

        elif size < 0 or align < 0:
            # CXTypeLayoutError_Invalid = -1,
            # CXTypeLayoutError_Dependent = -3,
            # CXTypeLayoutError_NotConstantSize = -4,
            # CXTypeLayoutError_InvalidFieldName = -5
            errs = dict([(-1, "Invalid"), (-3, "Dependent"),
                         (-4, "NotConstantSize"), (-5, "InvalidFieldName")])
            loc = "%s:%s" % (cursor.location.file, cursor.location.line)
            log.error('Structure %s is %s %s align:%d size:%d',
                      name, errs[size], loc, align, size)
            raise InvalidDefinitionError('Structure %s is %s %s align:%d size:%d',
                                         name, errs[size], loc, align, size)
        else:
            log.debug('_record_decl: name: %s size:%d', name, size)
        # Declaration vs Definition point
        # when a struct decl happen before the definition, we have no members
        # in the first declaration instance.
        obj = None
        if not self.is_registered(name):
            if not cursor.is_definition():
                # just save the spot, don't look at members == None
                log.debug('cursor %s is not on a definition', name)
                obj = _output_type(name, align, None, bases, size, packed=False)
                return self.register(name, obj)
            else:
                log.debug('cursor %s is a definition', name)
                # save the type in the registry. Useful for not looping in case of
                # members with forward references
                obj = _output_type(name, align, None, bases, size, packed=False)
                self.set_location(obj, cursor)
                self.set_comment(obj, cursor)
                declared_instance = True
                obj = self.register(name, obj)
        else:
            obj = self.get_registered(name)
            declared_instance = False
        # capture members declaration
        members = []
        # Go and recurse through fields
        fields = list(cursor.type.get_fields())
        decl_f = [f.type.get_declaration() for f in fields]
        log.debug('Fields: %s',
                  str(['%s/%s' % (f.kind.name, f.spelling) for f in fields]))
        for field in fields:
            log.debug('creating FIELD_DECL for %s/%s', field.kind.name, field.spelling)
            members.append(self.FIELD_DECL(field))
        obj.members = members
        # FIXME BUG clang: anonymous structure field with only one anonymous field
        # is not a FIELD_DECL. does not appear in get_fields() !!!
        #
        # check for other stuff
        for child in cursor.get_children():
            if child in fields:
                continue
            elif child in decl_f:
                continue
            elif child.kind == CursorKind.PACKED_ATTR:
                obj.packed = True
                log.debug('PACKED record')
                continue  # dont mess with field calculations
            else:  # could be others.... struct_decl, etc...
                log.debug(
                    'Unhandled field %s in record %s',
                    child.kind, name)
                continue
        log.debug('_record_decl: %d members', len(members))
        # by now, the type is registered.
        if not declared_instance:
            log.debug('_record_decl: %s was previously registered', name)
        # obj.packed = packed
        # final fixup
        self._fixup_record(obj)
        obj = self.update_register(name, obj)
        return obj

    def _fixup_record_bitfields_type(self, s):
        """Fix the bitfield packing issue for python ctypes, by changing the
        bitfield type, and respecting compiler alignement rules.

        This method should be called AFTER padding to have a perfect continuous
        layout.

        There is one very special case:
            struct bytes3 {
                unsigned int b1:23; // 0-23
                // 1 bit padding
                char a2; // 24-32
            };

        where we would need to actually put a2 in the int32 bitfield.

        We also need to change the member type to the smallest type possible
        that can contains the number of bits.
        Otherwise ctypes has strange bitfield rules packing stuff to the biggest
        type possible.

        ** but at the same time, if a bitfield member is from type x, we need to
        respect that
        """
        # phase 1, make bitfield, relying upon padding.
        bitfields = []
        bitfield_members = []
        current_bits = 0
        for m in s.members:
            if m.is_bitfield:
                bitfield_members.append(m)
                if m.is_padding:
                    # compiler says this ends the bitfield
                    size = current_bits
                    bitfields.append((size, bitfield_members))
                    bitfield_members = []
                    current_bits = 0
                else:
                    # size of padding is not included
                    current_bits += m.bits
            elif len(bitfield_members) == 0:
                # no opened bitfield
                continue
            else:
                # we reach the end of the bitfield. Make calculations.
                size = current_bits
                bitfields.append((size, bitfield_members))
                bitfield_members = []
                current_bits = 0
        if current_bits != 0:
            size = current_bits
            bitfields.append((size, bitfield_members))

        # compilers tend to reduce the size of the bitfield
        # to the bf_size
        # set the proper type name for the bitfield.
        for bf_size, members in bitfields:
            name = members[0].type.name
            pad_bits = 0
            if bf_size <= 8:  # use 1 byte - type = char
                # prep the padding bitfield size
                pad_bits = 8 - bf_size
            elif bf_size <= 16:  # use 2 byte
                pad_bits = 16 - bf_size
            elif bf_size <= 32:  # use 2 byte
                pad_bits = 32 - bf_size
            elif bf_size <= 64:  # use 2 byte
                name = 'c_uint64'  # also the 3 bytes + char thing
                pad_bits = 64 - bf_size
            else:
                name = 'c_uint64'
                pad_bits = bf_size % 64 - bf_size
            # change the type to harmonise the bitfield
            log.debug('_fixup_record_bitfield_size: fix type to %s', name)
            # set the whole bitfield to the appropriate type size.
            for m in members:
                m.type.name = name
                if m.is_padding:
                    # this is the last field.
                    # reduce the size of this padding field to the
                    m.bits = pad_bits
            # and remove padding if the size is 0
            if members[-1].is_padding and members[-1].bits == 0:
                s.members.remove(members[-1])

        # phase 2 - integrate the special 3 Bytes + char fix
        for bf_size, members in bitfields:
            if True or bf_size == 24:
                # we need to check for a 3bytes + char corner case
                m = members[-1]
                i = s.members.index(m)
                if len(s.members) > i + 1:
                    # has to exists, no arch is aligned on 24 bits.
                    next_member = s.members[i + 1]
                    if next_member.bits == 8:
                        # next_member field is a char.
                        # it will be aggregated in a 32 bits space
                        # we need to make it a member of 32bit bitfield
                        next_member.is_bitfield = True
                        next_member.comment = "Promoted to bitfield member and type (was char)"
                        next_member.type = m.type
                        log.info("%s.%s promoted to bitfield member and type", s.name, next_member.name)
                        continue
        #
        return

    def _fixup_record(self, s):
        """Fixup padding on a record"""
        log.debug('FIXUP_STRUCT: %s %d bits', s.name, s.size * 8)
        if s.members is None:
            log.debug('FIXUP_STRUCT: no members')
            s.members = []
            return
        if s.size == 0:
            log.debug('FIXUP_STRUCT: struct has size %d', s.size)
            return
        # try to fix bitfields without padding first
        self._fixup_record_bitfields_type(s)
        # No need to lookup members in a global var.
        # Just fix the padding
        members = []
        member = None
        offset = 0
        padding_nb = 0
        member = None
        prev_member = None
        # create padding fields
        # DEBUG FIXME: why are s.members already typedesc objet ?
        # fields = self.fields[s.name]
        for m in s.members:  # s.members are strings - NOT
            # we need to check total size of bitfield, so to choose the right
            # bitfield type
            member = m
            log.debug('Fixup_struct: Member:%s offsetbits:%d->%d expecting offset:%d',
                      member.name, member.offset, member.offset + member.bits, offset)
            if member.offset < 0:
                # FIXME INCOMPLETEARRAY (clang bindings?)
                # All fields have offset == -2. No padding will be done.
                # But the fields are ordered and code will be produces with typed info.
                # so in most cases, it will work. if there is a structure with incompletearray
                # and padding or alignement issue, it will produce wrong results
                # just exit
                return
            if member.offset > offset:
                # create padding
                length = member.offset - offset
                log.debug(
                    'Fixup_struct: create padding for %d bits %d bytes',
                    length, length // 8)
                padding_nb = self._make_padding(
                    members,
                    padding_nb,
                    offset,
                    length,
                    prev_member)
            if member.type is None:
                log.error('FIXUP_STRUCT: %s.type is None', member.name)
            members.append(member)
            offset = member.offset + member.bits
            prev_member = member
        # tail padding if necessary
        if s.size * 8 != offset:
            length = s.size * 8 - offset
            log.debug(
                'Fixup_struct: s:%d create tail padding for %d bits %d bytes',
                s.size, length, length // 8)
            padding_nb = self._make_padding(
                members,
                padding_nb,
                offset,
                length,
                prev_member)
        if len(members) > 0:
            offset = members[-1].offset + members[-1].bits
        # go
        s.members = members
        log.debug("FIXUP_STRUCT: size:%d offset:%d", s.size * 8, offset)
        # if member and not member.is_bitfield:
        ## self._fixup_record_bitfields_type(s)
        # , assert that the last field stop at the size limit
        assert offset == s.size * 8
        return

    _fixup_Structure = _fixup_record
    _fixup_Union = _fixup_record

    def _make_padding(
            self, members, padding_nb, offset, length, prev_member=None):
        """Make padding Fields for a specifed size."""
        name = 'PADDING_%d' % padding_nb
        padding_nb += 1
        log.debug("_make_padding: for %d bits", length)
        if (length % 8) != 0 or (prev_member is not None and prev_member.is_bitfield):
            if length > 32:
                typename = "c_uint64"
            elif length > 16:
                typename = "c_uint32"
            elif length > 8:
                typename = "c_uint16"
            else:
                typename = "c_uint8"
            padding = typedesc.Field(name,
                                     typedesc.FundamentalType(typename, 1, 1),
                                     offset, length, is_bitfield=True, is_padding=True)
            members.append(padding)
            return padding_nb
        elif length > 8:
            pad_bytes = length // 8
            padding = typedesc.Field(name,
                                     typedesc.ArrayType(
                                         typedesc.FundamentalType(
                                             self.get_ctypes_name(TypeKind.CHAR_U), length, 1),
                                         pad_bytes),
                                     offset, length, is_padding=True)
            members.append(padding)
            return padding_nb
        # simple char padding
        padding = typedesc.Field(name,
                                 typedesc.FundamentalType(
                                     self.get_ctypes_name(
                                         TypeKind.CHAR_U),
                                     1,
                                     1),
                                 offset, length, is_padding=True)
        members.append(padding)
        return padding_nb

    # FIXME
    CLASS_DECL = STRUCT_DECL
    _fixup_Class = _fixup_record

    # @log_entity DEBUG
    def FIELD_DECL(self, cursor):
        """
        Handles Field declarations.
        Some specific treatment for a bitfield.
        """
        # name, type
        parent = cursor.semantic_parent
        # field name:
        # either its cursor.spelling or it is an anonymous bitfield
        # we do NOT rely on get_unique_name for a bitfield name.
        # Anonymous Field:
        #    We have to create a name
        #    it will be the indice of the field (_0,_1,...)
        # offset of field:
        #    we will need it late. get the offset of the field in the record
        # Note: cursor.is_anonymous seems to be unreliable/inconsistent across
        # libclang versions so we will consider the field as anonymous if
        # cursor.spelling is empty
        name = cursor.spelling
        offset = parent.type.get_offset(name)
        if not name and not cursor.is_bitfield():
            # anonymous non-bitfield field case:
            offset = cursor.get_field_offsetof()
            name = self.get_unique_name(cursor)
        if not name:
            # anonymous bitfield case:
            # get offset by iterating all fields of parent
            # corner case for anonymous fields
            # if offset == -5: use field.get_offset_of()
            offset = cursor.get_field_offsetof()
            for i, _f in enumerate(parent.type.get_fields()):
                if _f == cursor:
                    fieldnum = i
                    break
            # make a name
            if fieldnum == -1:
                raise ValueError("Anonymous field was not found in get_fields()")
            name = "_%d" % fieldnum
            log.debug("FIELD_DECL: anonymous field renamed to %s", name)
        # some debug
        if offset < 0:
            log.error('FIELD_DECL: BAD RECORD, Bad offset: %d for %s', offset, name)
            # incomplete record definition, gives us an error here on fields.
            # BUG clang bindings ?
        # FIXME if c++ class ?
        log.debug('FIELD_DECL: field offset is %d', offset)

        # bitfield checks
        bits = None
        if cursor.is_bitfield():
            log.debug('FIELD_DECL: field is part of a bitfield')
            bits = cursor.get_bitfield_width()
        else:
            bits = cursor.type.get_size() * 8
            if bits < 0:
                log.warning('Bad source code, bitsize == %d <0 on %s', bits, name)
                bits = 0
        log.debug('FIELD_DECL: field is %d bits', bits)
        # try to get a representation of the type
        # _canonical_type = cursor.type.get_canonical()
        # t-t-t-t-
        _type = None
        _canonical_type = cursor.type.get_canonical()
        _decl = cursor.type.get_declaration()
        if (self.is_array_type(_canonical_type) or
                self.is_fundamental_type(_canonical_type) or
                self.is_pointer_type(_canonical_type)):
            _type = self.parse_cursor_type(_canonical_type)
        else:
            children = list(cursor.get_children())
            log.debug('FIELD_DECL: we now look for the declaration name.'
                      'kind %s', _decl.kind)
            if len(children) > 0 and _decl.kind == CursorKind.NO_DECL_FOUND:
                # constantarray of typedef of pointer , and other cases ?
                _decl_name = self.get_unique_name(
                    list(
                        cursor.get_children())[0])
            else:
                _decl_name = self.get_unique_name(_decl)
            log.debug('FIELD_DECL: the declaration name %s', _decl_name)
            # rename anonymous field type name
            # 2015-06-26 handled in get_name
            # if cursor.is_anonymous():
            #    _decl_name += name
            #    log.debug('FIELD_DECL: IS_ANONYMOUS the declaration name %s',_decl_name)
            if self.is_registered(_decl_name):
                log.debug(
                    'FIELD_DECL: used type from cache: %s',
                    _decl_name)
                _type = self.get_registered(_decl_name)
                # then we shortcut
            else:
                # is it always the case ?
                log.debug("FIELD_DECL: name:'%s'", _decl_name)
                log.debug("FIELD_DECL: %s: nb children:%s", cursor.type.kind,
                          len(children))
                # recurse into the right function
                _type = self.parse_cursor_type(_canonical_type)
                if _type is None:
                    log.warning("Field %s is an %s type - ignoring field type",
                                name, _canonical_type.kind.name)
                    return None
        if cursor.is_anonymous():
            # we have to unregister the _type and register a alternate named
            # type.
            self.parser.remove_registered(_type.name)
            _type.name = _decl_name
            self.register(_decl_name, _type)
        return typedesc.Field(name, _type, offset, bits,
                              is_bitfield=cursor.is_bitfield(),
                              is_anonymous=cursor.is_anonymous())

    #############################
    # PREPROCESSING

    @log_entity
    def MACRO_DEFINITION(self, cursor):
        """
        Parse MACRO_DEFINITION, only present if the TranslationUnit is
        used with TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD.
        By default, macro are not parsed. requires -k m || parser.activate_macros_parsing()
        """
        name = self.get_unique_name(cursor)
        # MACRO_DEFINITION are a list of Tokens
        # .kind = {IDENTIFIER, KEYWORD, LITERAL, PUNCTUATION, COMMENT ? }
        comment = None
        tokens = self._literal_handling(cursor)
        # Macro name is tokens[0]
        # get Macro value(s)
        value = True
        # args should be filled when () are in tokens,
        args = None
        if isinstance(tokens, list):
            if len(tokens) == 2:
                # #define key value
                value = tokens[1]
            elif len(tokens) == 3 and tokens[1] == '-':
                value = ''.join(tokens[1:])
            elif tokens[1] == '(':
                # function macro or an expression.
                tokens = remove_outermost_parentheses(tokens[1:])
                if tokens and tokens[0] == "(":
                    # function
                    str_tokens = "".join((map(str, tokens[0:tokens.index(')') + 1]))).strip()
                    str_tokens = remove_outermost_parentheses(str_tokens)
                    args = list(map(
                        lambda a: a.strip(), str_tokens.split(',')
                    ))
                    str_tokens = "".join((map(str, tokens[tokens.index(')') + 1:])))
                    if all(map(lambda a: is_identifier(a) and a not in str_tokens, args)):
                        value = "".join(map(str, tokens))
                    else:
                        value = str_tokens

                elif all(map(lambda a: a == "," or is_identifier(str(a)), tokens)):
                    # TODO FIX differentiation between function-like macro and expression in ()
                    # no-op function ?
                    args = list(map(
                        lambda a: str(a).strip(), tokens
                    ))
                    value = "''"
                else:
                    # expression
                    if not any(map(lambda t: isinstance(t, typedesc.UndefinedIdentifier), tokens)):
                        value = " ".join(map(str, tokens))
                    else:
                        value = None
            elif len(tokens) > 1:
                # #define key a b c
                if not any(map(lambda t: isinstance(t, typedesc.UndefinedIdentifier), tokens)):
                    value = " ".join(tokens[1:])
                else:
                    value = None
            else:
                # FIXME no reach ?!
                # just merge the list of tokens
                if not any(map(lambda t: isinstance(t, typedesc.UndefinedIdentifier), tokens)):
                    value = "".join(tokens[1:])
                else:
                    value = None
        elif isinstance(tokens, str):
            # #define only
            value = True
        # macro comment maybe in tokens. Not in cursor.raw_comment
        for t in cursor.get_tokens():
            if t.kind == TokenKind.COMMENT:
                comment = t.spelling
        # special case. internal __null or __thread
        # FIXME, there are probable a lot of others.
        # why not Cursor.kind GNU_NULL_EXPR child instead of a token ?
        if name in ['NULL', '__thread'] or value in ['__null', '__thread']:
            value = None
        log.debug('MACRO: #define %s%s %s', name, args or '', value)
        func = None
        if args:
            func = process_macro_function(name, args, value)
            if func is not None:
                self.parser.interprete(func)

        obj = typedesc.Macro(name, args, value, func)
        self.set_location(obj, cursor)
        # set the comment in the obj
        obj.comment = comment
        try:
            self.register(name, obj)
        except DuplicateDefinitionException:
            log.info('Redefinition of %s %s->%s', name, self.parser.all[name].args, value)
            # HACK
            self.parser.all[name] = obj
        return True

    @log_entity
    def MACRO_INSTANTIATION(self, cursor):
        """We could use this to count instantiations
        so we know, if we need to generate python code or comment for this macro ? """
        log.debug('cursor.spelling: %s', cursor.spelling)
        # log.debug('cursor.kind: %s', cursor.kind.name)
        # log.debug('cursor.type.kind: %s', cursor.type.kind.name)
        # # no children ?
        # for child in cursor.get_children():
        #     log.debug('child.spelling: %s', child.spelling)
        #     log.debug('child.kind: %s', child.kind.name)
        #     log.debug('child.type.kind: %s', child.type.kind.name)
        #
        # for token in cursor.get_tokens():
        #     log.debug('token.spelling: %s', token.spelling)
        #     log.debug('token.kind: %s', token.kind.name)
        #     #log.debug('token.type.kind: %s', token.type.kind.name)

        # ret.append(self.parse_cursor(child))
        # log.debug('cursor.type:%s', cursor.type.kind.name)
        # self.set_location(obj, cursor)
        # set the comment in the obj
        # obj.comment = comment
        return True
