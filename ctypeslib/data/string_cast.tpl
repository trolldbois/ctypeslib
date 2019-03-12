def string_cast(char_pointer, encoding='utf-8'):
    value = ctypes.cast(char_pointer, ctypes.c_char_p).value
    if encoding is not None:
        value = value.decode(encoding)
    return value


def char_pointer_cast(string, encoding='utf-8'):
    if encoding is not None:
        try:
            string = string.encode(encoding)
        except AttributeError:
            # In Python3, bytes has no encode attribute
            pass
    string = ctypes.c_char_p(string)
    return ctypes.cast(string, POINTER_T(ctypes.c_char))


