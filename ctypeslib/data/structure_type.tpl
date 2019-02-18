class Structure(ctypes.Structure):

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
                    fields.append(type_(lambda *args: None))
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


