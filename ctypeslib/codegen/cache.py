import functools
import itertools
import types

from ctypeslib.codegen.hash import hashable_dict


_Tee = itertools.tee([], 1)[0].__class__


disable_cache = False


def _get_function_fullname(function):
    return f"{function.__module__}.{function.__qualname__}"


_cache_functions = {
    "ctypeslib.codegen.cindex.Config.lib",
    "ctypeslib.codegen.cindex.Cursor.get_tokens",
    "ctypeslib.codegen.cindex.SourceLocation.__contains__",
    "ctypeslib.codegen.cindex.Token.cursor",
    # # The following aren't worth caching
    # "ctypeslib.codegen.cindex.Cursor.kind",
    # "ctypeslib.codegen.cindex.Token.kind",
    # "ctypeslib.codegen.cindex.TokenGroup.get_tokens",
    # "ctypeslib.codegen.cindex.TranslationUnit.from_source",
    # "ctypeslib.codegen.cursorhandler.CursorHandler.MACRO_DEFINITION",
}


def cached(cache_key=None):
    def decorator(function):
        global disable_cache, _cache_functions
        if disable_cache or not _get_function_fullname(function) in _cache_functions:
            return function

        cache = {}
        args_names = function.__code__.co_varnames[: function.__code__.co_argcount]

        def wrapper(*args, **kwds):
            wargs = dict(zip(args_names, args))
            wargs.update(kwds)
            wargs = hashable_dict(wargs)
            if cache_key is None:
                key = hash(wargs)
            elif isinstance(cache_key, (int, slice)):
                key = tuple(wargs.values())[cache_key]
            else:
                key = cache_key(wargs)
            try:
                return cache[key]
            except KeyError:
                value = function(*args, **kwds)
                if isinstance(value, types.GeneratorType):
                    # flatten the generator
                    value = tuple(value)
                cache[key] = value
                return value

        return functools.update_wrapper(wrapper, function)

    return decorator


def cached_pure_method():
    return cached(cache_key=slice(1, None))


def cached_property():
    def decorator(function):
        return property(cached()(function))
    return decorator


def cached_classmethod():
    def decorator(function):
        return classmethod(cached()(function))
    return decorator


def cached_staticmethod():
    def decorator(function):
        return staticmethod(cached()(function))
    return decorator
