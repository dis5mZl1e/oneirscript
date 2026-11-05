"""String-list compatible message history with runtime occurrence identity."""
from copy import deepcopy
from itertools import count
import operator

_GENERATIONS = count(1)


class MessageHistory(list):
    """IDs follow occurrences through moves, never equality of message bodies.

    Save encoders still see an ordinary list of strings. Reassignment, clear,
    and complete slice replacement start a fresh runtime generation.
    """
    def __init__(self, values=()):
        list.__init__(self, values)
        self.generation = next(_GENERATIONS)
        self.revision = 0
        self._next = len(self)
        self._ids = list(range(self._next))
        self._id_snapshot = None

    @property
    def occurrence_ids(self):
        if self._id_snapshot is None:
            self._id_snapshot = tuple(self._ids)
        return self._id_snapshot

    @property
    def cursor(self):
        return self.generation, self._next

    def _fresh(self, amount):
        ids = range(self._next, self._next + amount)
        self._next += amount
        return ids

    def _changed(self, *, reset=False):
        self.revision += 1
        self._id_snapshot = None
        if reset:
            self.generation = next(_GENERATIONS)

    def append(self, value):
        list.append(self, value)
        self._ids.extend(self._fresh(1))
        self._changed()

    def extend(self, values):
        if values is self:
            values = list(self)
        for value in values:
            self.append(value)

    def insert(self, index, value):
        index = operator.index(index)
        list.insert(self, index, value)
        self._ids.insert(index, next(iter(self._fresh(1))))
        self._changed()

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            values = list(value)
            start, stop, step = index.indices(len(self))
            reset = start == 0 and stop == len(self) and step == 1
            list.__setitem__(self, index, values)
            self._ids[index] = self._fresh(len(values))
        else:
            index = operator.index(index)
            list.__setitem__(self, index, value)
            self._ids[index] = next(iter(self._fresh(1)))
            reset = False
        self._changed(reset=reset)

    def __delitem__(self, index):
        list.__delitem__(self, index)
        del self._ids[index]
        self._changed()

    def pop(self, index=-1):
        index = operator.index(index)
        value = list.pop(self, index)
        self._ids.pop(index)
        self._changed()
        return value

    def remove(self, value):
        del self[self.index(value)]

    def clear(self):
        list.clear(self)
        self._ids.clear()
        self._changed(reset=True)

    def reverse(self):
        list.reverse(self)
        self._ids.reverse()
        self._changed()

    def sort(self, *, key=None, reverse=False):
        pairs = list(zip(self, self._ids))
        pairs.sort(key=(lambda pair: pair[0]) if key is None else
                   (lambda pair: key(pair[0])), reverse=reverse)
        list.__setitem__(self, slice(None), [value for value, _ in pairs])
        self._ids[:] = [identity for _, identity in pairs]
        self._changed()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, times):
        times = operator.index(times)
        original = list(self)
        if times <= 0:
            self.clear()
        elif times > 1:
            self.extend(original * (times - 1))
        return self

    def __copy__(self):
        return type(self)(self)

    def __reduce_ex__(self, protocol):
        # Default list-subclass unpickling appends before restoring attributes.
        # Reconstruct runtime identity through __init__ instead (e.g. workers).
        return type(self), (list(self),)

    def __deepcopy__(self, memo):
        result = type(self)()
        memo[id(self)] = result
        result.extend(deepcopy(value, memo) for value in self)
        return result
