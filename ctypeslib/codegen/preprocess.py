import textwrap
import itertools
import logging
import re
import ctypes
from collections.abc import Iterable


log = logging.getLogger(__name__)

_c_hexint_literal = r"\b0x[0-9a-fA-F]+"
_c_hexint_literal_regex = re.compile(f"({_c_hexint_literal})(([uU])?([lL])?([lL])?)")
_c_octint_literal = r"\b0[0-7]*"
_c_octint_literal_regex = re.compile(f"({_c_octint_literal})(([uU])?([lL])?([lL])?)")
_c_decint_literal = r"\b[1-9][0-9]*"
_c_decint_literal_regex = re.compile(f"({_c_decint_literal})(([uU])?([lL])?([lL])?)")
_c_int_literal = f"((?:{_c_hexint_literal})|(?:{_c_octint_literal})|(?:{_c_decint_literal}))[uUlL]?[lL]?"
_c_int_literal_regex = re.compile(_c_int_literal)

_c_decimal_literal = r"((?:(?<![xX])\d+(?:e|E)[+-]?\d+)|(?:(?<![xX])\d+(?:\.\d*)?(?:(?:e|E)[+-]?\d+)?)|(?:(?<![xX])\.\d+(?:(?:e|E)[+-]?\d+)?))(?:f|F|l|L)?(?![xX])"

_c_decimal_literal_regex = re.compile(_c_decimal_literal)
_c_numeric_literal = f"(?:{_c_int_literal})|(?:{_c_decimal_literal})"


def _from_c_literal(literal_regex, value):
    if (
        not isinstance(value, str)
        and isinstance(value, Iterable)
        and all(map(lambda v: isinstance(v, str), value))
    ):
        value = "".join(value)
    if not isinstance(value, str):
        return None
    match = literal_regex.match(value)
    if not match:
        return None
    return match.group(1)


def from_c_int_literal(value, pointer_width):
    for (base, m) in zip(
        (16, 8, 10),
        map(
            lambda r: r.match(value),
            (
                _c_hexint_literal_regex,
                _c_octint_literal_regex,
                _c_decint_literal_regex,
            ),
        ),
    ):
        if m:
            return _process_c_int_matched_literal(m, pointer_width, base)

    raise ValueError(f"{value} not is not a valid integer")


def from_c_float_literal(value):
    return float(_from_c_literal(_c_decimal_literal_regex, value))


def _process_c_literal(literal_regex, value, repl=r"\1"):
    if (
        not isinstance(value, str)
        and isinstance(value, Iterable)
        and all(map(lambda v: isinstance(v, str), value))
    ):
        value = "".join(value)
    if not isinstance(value, str):
        return None
    return literal_regex.sub(repl, value)


def _int_limits(c_int_type):
    signed = c_int_type(-1).value < c_int_type(0).value
    bit_size = ctypes.sizeof(c_int_type) * 8
    signed_limit = 2 ** (bit_size - 1)
    return (-signed_limit, signed_limit - 1) if signed else (0, 2 * signed_limit - 1)


def _get_c_int_type(suffix, unsigned, _long):
    if not suffix:
        _type = ctypes.c_int
    elif unsigned:
        if _long:
            _type = ctypes.c_ulonglong
        else:
            _type = ctypes.c_uint
    elif _long:
        _type = ctypes.c_longlong
    else:
        _type = ctypes.c_long
    return (_type,) + _int_limits(_type)


_c_int_type_map = {
    k: _get_c_int_type(*k)
    for k in itertools.product(
        [False, True], [False, True], [False, True],  # suffix  # unsigned  # long
    )
}


def _process_c_int_matched_literal(match, pointer_width, base):
    str_value = match.group(1)
    value = int(str_value, base)
    suffix = match.group(2)
    unsigned = match.group(3) is not None
    _long = match.group(4) is not None
    _long_long = match.group(5) is not None
    if pointer_width != 64:
        _long = _long_long
    _type, _min, _max = _c_int_type_map[(bool(suffix), unsigned, _long)]
    if not (_min <= value <= _max):
        if suffix:
            log.warning(f"Invalid literal suffix '{str_value}{suffix}'")
        if unsigned:
            _type = ctypes.c_uint64
        elif value > _int_limits(ctypes.c_int64)[1]:
            _type = ctypes.c_uint64
        else:
            _type = ctypes.c_int64
    return _type(value).value


def process_c_int_literal(value, pointer_width=64):
    value = _process_c_literal(
        _c_hexint_literal_regex,
        value,
        repl=lambda m: str(_process_c_int_matched_literal(m, pointer_width, 16)),
    )
    value = _process_c_literal(
        _c_octint_literal_regex,
        value,
        repl=lambda m: str(_process_c_int_matched_literal(m, pointer_width, 8)),
    )
    value = _process_c_literal(
        _c_decint_literal_regex,
        value,
        repl=lambda m: str(_process_c_int_matched_literal(m, pointer_width, 10)),
    )
    return value


def process_c_float_literal(value):
    return _process_c_literal(_c_decimal_literal_regex, value)


def from_c_literal(value):
    ret = from_c_int_literal(value)
    if ret is not None:
        return ret
    ret = from_c_float_literal(value)
    if ret is not None:
        return ret
    return value


_c_string_literal = r"(?:L|u8|u|U)?(R)?(\"|')((?:(?!\2).)*)\2"
_c_string_literal_regex = re.compile(_c_string_literal)
_c_raw_string_literal = r"([^()\\s]{0,16})\(((?:(?!\1).)*)\)\1?"
_c_raw_string_literal_regex = re.compile(_c_raw_string_literal)


def _process_c_string_literal(match, quote=False):
    raw_string = match.group(1) is not None
    value = match.group(3)
    if raw_string:
        value = _c_raw_string_literal_regex.sub(r"\2", value)
    if not quote:
        return value
    else:
        return f'"{value}"'


def from_c_string_literal(value):
    return _c_string_literal_regex.sub(_process_c_string_literal, value)


def process_c_string_literals(value):
    return _c_string_literal_regex.sub(
        lambda m: _process_c_string_literal(m, quote=True), value
    )


def process_c_literals(value, pointer_width=64):
    value = process_c_int_literal(value, pointer_width=64)
    value = process_c_float_literal(value)
    value = process_c_string_literals(value)
    return value


_macro_operators = [
    r"##",
    r"#",
    r"\(",
    r"\)",
    r"{",
    r"}",
    r",",
    r"!=",
    r"\|=",
    r"&=",
    r"\+=",
    r"\*=",
    r"/=",
    r"%=",
    r"\+",
    r"-",
    r"\*",
    r"/",
    r">>",
    r"<<",
    r">>=",
    r"<<=",
    r":",
    r"\?",
    r">=",
    r"<=",
    r"<",
    r">",
    r"==",
    r"=",
    r"\"",
    r"'",
    r"&&",
    r"&",
    r"\|\|",
    r"\|",
]

_macro_operators_regexes = list(map(lambda r: re.compile(r), _macro_operators))

_macro_identifier = r"([_a-zA-Z][_a-zA-Z0-9]*)"
_macro_identifier_regex = re.compile("^" + _macro_identifier + "$")


def is_identifier(expr):
    return _macro_identifier_regex.match(expr) is not None


_macro_tokens = "|".join(
    [_c_numeric_literal, _macro_identifier]
    + list(map(lambda t: f"({t})", _macro_operators))
)

_macro_tokenizer = re.compile(_macro_tokens)

_builtins_map = {
    r"const": "",
    r"typedef": "",
    r"sizeof": "ctypes.sizeof",
    r"bool": "ctypes.c_bool",
    r"unsigned\s+char": "ctypes.c_ubyte",
    r"char": "ctypes.c_byte",
    r"wchar": "ctypes.c_wchar",
    r"unsigned\s+short\s+int": "ctypes.c_ushort",
    r"unsigned\s+short": "ctypes.c_ushort",
    r"short\s+int": "ctypes.c_short",
    r"short": "ctypes.c_short",
    r"unsigned\s+int": "ctypes.c_uint",
    r"int": "ctypes.c_int",
    r"unsigned\s+long\s+long\s+int": "ctypes.c_ulonglong",
    r"unsigned\s+long\s+int": "ctypes.c_ulong",
    r"unsigned\s+long\s+long": "ctypes.c_ulonglong",
    r"unsigned\s+long": "ctypes.c_ulong",
    r"long\s+long\s+int": "ctypes.c_longlong",
    r"long\s+long": "ctypes.c_longlong",
    r"long\s+int": "ctypes.c_long",
    r"long": "ctypes.c_long",
    r"size_t": "ctypes.c_size_t",
    r"ssize_t": "ctypes.c_ssize_t",
    r"float": "ctypes.c_float",
    r"long\s+double": "ctypes.c_longdouble",
    r"double": "ctypes.c_double",
    r"typeof": "type",
}
_builtins_patterns = re.compile(
    "|".join(map(lambda p: f"(\\b{p}\\b)", _builtins_map.keys()))
)


def replace_builtins(expr):
    return _builtins_patterns.sub(lambda m: _builtins_map.get(m.group(1)), expr)


_curly_brace_escape_map = {
    "{": "{{",
    "}": "}}",
}
_curly_brace_escape_patterns = re.compile(
    "|".join(map(lambda p: f"({p})", _curly_brace_escape_map.keys()))
)


def escape_curly_brace(expr):
    return _curly_brace_escape_patterns.sub(
        lambda m: _curly_brace_escape_map.get(m.group(0)), expr
    )


_escape_quotes_regex = re.compile('(?<!^f)(?<!^)(?<!f)"(?!$)')


def escape_quotes(expr):
    return _escape_quotes_regex.sub(r"\"", expr)


_pointer_type_regex = [
    re.compile(f"({_macro_identifier})\\s*\\*(?![a-zA-Z_])"),
    re.compile(f"(?![a-zA-Z_])\\*\\s*({_macro_identifier})"),
]


def replace_pointer_types(expr):
    for pattern in _pointer_type_regex:
        expr = pattern.sub(r" ctypes.POINTER(\1) ", expr)
    return expr


def tokenize_macro(body):
    return list(
        filter(lambda t: t is not None and t.strip(), _macro_tokenizer.split(body))
    )


def process_macro(args, body):
    if body is None:
        return ""
    if isinstance(body, list):
        body = "".join(body)
    tokens = tokenize_macro(body)
    processed_tokens = []
    concat = False
    prev_token = None
    for token in tokens:
        if token.startswith("#"):
            prev_token = token
            continue
        token = escape_curly_brace(token)
        if args and is_identifier(token) and token in args:
            if token == "__VA_ARGS__":
                new_token = "*{*__VA_ARGS__,}"
            elif prev_token == "#":
                new_token = f"{token}"
            else:
                new_token = f"{{{token}}}"
        else:
            token = replace_builtins(token)
            new_token = f"{token}"
        if new_token != "##":
            if concat:
                if new_token == " ":
                    continue
                else:
                    concat = False
                    processed_tokens[-1] += f"{new_token}"
            elif new_token == "=" and is_identifier(processed_tokens[-1]):
                processed_tokens[-1] += ".value"
                processed_tokens.append(new_token)
            else:
                processed_tokens.append(new_token)
        else:
            concat = True
            while processed_tokens[-1] == " ":
                processed_tokens.pop()
        prev_token = token
    processed_macro = "".join(processed_tokens)
    return 'f"' + processed_macro + '"'


def process_macro_function(name, args, body):
    if isinstance(args, list):
        args = ", ".join(args)
    args = remove_outermost_parentheses(args)
    args = re.sub(r"\.\.\.", "*__VA_ARGS__", args)
    body = process_macro(args, body)
    body = escape_quotes(body)
    func = textwrap.dedent(
        f"""
        def {name}({args}):
            return eval_processed_macro({body}, locals())
    """
    )
    try:
        exec_processed_macro(func)
    except SyntaxError as e:
        return None
    except NameError:
        pass

    return func


def _eval_processed_macro(processed_macro, namespace, pointer_width, method):
    processed_macro = process_c_literals(processed_macro, pointer_width)
    processed_macro = replace_builtins(processed_macro)
    processed_macro = compile(processed_macro, "<ctypeslib.macro>", method)
    if namespace is None:
        namespace = {}
    return eval(processed_macro, globals(), namespace)


def eval_processed_macro(processed_macro, namespace=None, pointer_width=64):
    return _eval_processed_macro(processed_macro, namespace, pointer_width, "eval")


def exec_processed_macro(processed_macro, namespace=None, pointer_width=64):
    return _eval_processed_macro(processed_macro, namespace, pointer_width, "exec")


def remove_outermost_parentheses(macro):
    if len(macro) < 2:
        return macro
    if not macro[0] == "(" or not macro[-1] == ")":
        return macro
    balance = 0
    ret = macro[1:-1]
    for c in ret:
        if c == "(":
            balance += 1
        elif c == ")":
            balance -= 1
        if balance < 0:
            return macro
    if balance != 0:
        return macro
    else:
        return remove_outermost_parentheses(ret)


def __attribute__(expr):
    return


def __const__(expr):
    return


def __restrict(expr):
    return
