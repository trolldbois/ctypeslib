class AsDictMixin:
    @classmethod
    def as_dict(cls, self):
        result = {}
        if not isinstance(self, AsDictMixin):
            # not a structure, assume it's already a python object
            return self
        for (field, *_) in self._fields_:
            if field.startswith('PADDING_'):
                continue
            value = getattr(self, field)
            if hasattr(value, "_length_") and hasattr(value, "_type_"):
                # array
                value = [cls.as_dict(v) for v in value]
            elif hasattr(value, "contents") and hasattr(value, "_type_"):
                # pointer
                try:
                    value = cls.as_dict(value.content)
                except ValueError:
                    # nullptr
                    value = None
            elif isinstance(value, AsDictMixin):
                # other structure
                value = cls.as_dict(value)
            result[field] = value
        return result


class Structure(ctypes.Structure, AsDictMixin):

    def __init__(self, *args, **kwds):
        # We don't want to use positional arguments fill PADDING_* fields

        args = dict(zip(self.__class__._field_names_(), args))
        args.update(kwds)
        super(Structure, self).__init__(**args)

    @classmethod
    def _field_names_(cls):
        if hasattr(cls, '_fields_'):
            return (f[0] for f in cls._fields_ if not f[0].startswith('PADDING'))
        else:
            return ()

    @classmethod
    def get_type(cls, field):
        for f in cls._fields_:
            if f[0] == field:
                return f[1]
        return None

    @classmethod
    def bind(cls, bound_fields):
        fields = []
        for name, type_ in cls._fields_:
            if hasattr(type_, "restype"):
                if name in bound_fields:
                    # use a closure to capture the callback from the loop scope
                    fields.append(
                        type_((lambda callback: lambda *args: callback(*args))(bound_fields[name]))
                    )
                    del bound_fields[name]
                else:
                    # default callback implementation (does nothing)
                    try:
                        default_ = type_(0).restype().value
                    except TypeError:
                        default_ = None
                    fields.append(type_((lambda default_: lambda *args: default_)(default_)))
            else:
                # not a callback function, use default initialization
                if name in bound_fields:
                    fields.append(bound_fields[name])
                    del bound_fields[name]
                else:
                    fields.append(type_())
        if len(bound_fields) != 0:
            raise ValueError("Cannot bind the following unknown callback(s) {}.{}".format(
                cls.__name__, bound_fields.keys()
            ))
        return cls(*fields)


class Union(ctypes.Union, AsDictMixin):
    pass


