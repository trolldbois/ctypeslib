import collections.abc
import functools
import abc


class HashCombinable(abc.ABC):
    @abc.abstractmethod
    def hash_combine(self, combiner):
        pass


def hash_value(value):
    return HashCombiner().hash_value(value)


def hash_combine(args):
    return HashCombiner().hash_combine(args)


class HashCombiner:
    def __init__(self):
        self._seen = set()

    def hash_value(self, value):
        if isinstance(value, int):
            return value
        elif isinstance(value, str):
            return hash(value)
        elif isinstance(value, list):
            value = tuple(value)
        seen_key = id(value)
        if seen_key in self._seen:
            return 0
        self._seen.add(seen_key)
        if isinstance(value, collections.abc.Mapping):
            return self.hash_combine(
                self.hash_value(k) ^ self.hash_value(v)
                for k, v in sorted(value.items())
            )
        elif isinstance(value, collections.abc.Collection):
            return self.hash_combine(value)
        elif isinstance(value, HashCombinable):
            return value.hash_combine(self)
        else:
            return hash(value)

    def hash_combine(self, args):
        return functools.reduce(
            lambda h, v: h ^ self.hash_value(v),
            filter(lambda a: id(a) not in self._seen, args),
            0,
        )


class hashable_dict(HashCombinable, collections.abc.Mapping):
    def __init__(self, mapping):
        self._mapping = mapping
        self._hash = None

    def hash_combine(self, combiner):
        return combiner.hash_value(self._mapping)

    def __hash__(self):
        if self._hash is None:
            self._hash = self.hash_combine(HashCombiner())
        return self._hash

    def __getitem__(self, key):
        return self._mapping[key]

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)
