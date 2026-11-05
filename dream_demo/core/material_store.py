"""One owner for Cell fields; numeric columns are contiguous exact integers.

Rare values outside an int64 column retain their exact Python value in a sparse
exception table. The simulation never silently rounds, clamps or rejects saves.
"""
from array import array
from copy import deepcopy
from dataclasses import fields
from weakref import WeakSet, ref

from .mutation_journal import MutationJournal


class _Notifier:
    """Only weak, currently reachable field owners subscribe to a container."""
    def __init__(self):
        self.owners = WeakSet()

    def __call__(self):
        for owner in tuple(self.owners):
            owner.refresh()
            journal = owner.journal()
            if journal is not None:
                journal.record(owner.position, owner.name)


class _MutableOwner:
    def __init__(self, journal, position, name, root):
        self.journal = ref(journal)
        self.position, self.name, self.root = position, name, root
        self._nodes = {}
        self.refresh()

    def refresh(self):
        nodes, seen, pending = {}, set(), [self.root]
        while pending:
            value = pending.pop()
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            if isinstance(value, (TrackedDict, TrackedList)):
                nodes[identity] = value
                pending.extend(value.values() if isinstance(value, dict) else value)
            elif isinstance(value, tuple):
                pending.extend(value)
        for identity in self._nodes.keys() - nodes.keys():
            self._nodes[identity]._changed.owners.discard(self)
        for identity in nodes.keys() - self._nodes.keys():
            nodes[identity]._changed.owners.add(self)
        self._nodes = nodes

    def close(self):
        for node in self._nodes.values():
            node._changed.owners.discard(self)
        self._nodes.clear()
        self.root = None


def _track(value, memo=None):
    if isinstance(value, (TrackedDict, TrackedList)):
        return value
    if memo is None:
        memo = {}
    if isinstance(value, (dict, list)):
        if id(value) in memo:
            original, tracked = memo[id(value)]
            return tracked
        result = TrackedDict() if isinstance(value, dict) else TrackedList()
        memo[id(value)] = (value, result)
        if isinstance(value, dict):
            for key, child in value.items():
                dict.__setitem__(result, key, _track(child, memo))
        else:
            for child in value:
                list.append(result, _track(child, memo))
        return result
    if isinstance(value, tuple):
        return tuple(_track(v, memo) for v in value)
    return value


class TrackedDict(dict):
    def __init__(self, values=()):
        self._changed = _Notifier()
        dict.__init__(self, ((k, _track(v)) for k, v in dict(values).items()))

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, _track(value))
        self._changed()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._changed()

    def clear(self):
        if self:
            dict.clear(self)
            self._changed()

    def pop(self, key, *default):
        present = key in self
        value = dict.pop(self, key, *default)
        if present:
            self._changed()
        return value

    def popitem(self):
        value = dict.popitem(self)
        self._changed()
        return value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def __ior__(self, other):
        self.update(other)
        return self

    def __deepcopy__(self, memo):
        result = {}
        memo[id(self)] = result
        result.update((deepcopy(k, memo), deepcopy(v, memo)) for k, v in self.items())
        return result

    def __reduce_ex__(self, protocol):
        return TrackedDict, (), None, None, iter(self.items())


class TrackedList(list):
    def __init__(self, values=()):
        self._changed = _Notifier()
        list.__init__(self, (_track(v) for v in values))

    def __setitem__(self, key, value):
        value = [_track(v) for v in value] if isinstance(key, slice) else _track(value)
        list.__setitem__(self, key, value)
        self._changed()

    def __delitem__(self, key):
        list.__delitem__(self, key)
        self._changed()

    def append(self, value):
        list.append(self, _track(value))
        self._changed()

    def extend(self, values):
        list.extend(self, (_track(v) for v in values))
        self._changed()

    def insert(self, index, value):
        list.insert(self, index, _track(value))
        self._changed()

    def pop(self, index=-1):
        value = list.pop(self, index)
        self._changed()
        return value

    def remove(self, value):
        list.remove(self, value)
        self._changed()

    def clear(self):
        if self:
            list.clear(self)
            self._changed()

    def reverse(self):
        list.reverse(self)
        self._changed()

    def sort(self, *args, **kwargs):
        list.sort(self, *args, **kwargs)
        self._changed()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        list.__imul__(self, count)
        self._changed()
        return self

    def __deepcopy__(self, memo):
        result = []
        memo[id(self)] = result
        result.extend(deepcopy(v, memo) for v in self)
        return result

    def __reduce_ex__(self, protocol):
        return TrackedList, (), None, iter(self)


class CellField:
    def __init__(self, name):
        self.name = name

    def __get__(self, cell, cls=None):
        if cell is None:
            return self
        data = cell.__dict__
        binding = data.get('_material_binding')
        if binding is None:
            return data[self.name]
        return binding[0].read(binding[1], self.name)

    def __set__(self, cell, value):
        data = cell.__dict__
        binding = data.get('_material_binding')
        if binding is None:
            data[self.name] = value
        else:
            binding[0].write(binding[1], self.name, value)


class MaterialStore:
    def __init__(self, cells, width, height):
        from .entities import Cell
        if len(cells) != height or any(len(row) != width for row in cells):
            raise ValueError('material store dimensions do not match cells')
        self.width, self.height = width, height
        self.journal = MutationJournal()
        self.field_names = tuple(f.name for f in fields(Cell))
        self.numeric_fields = frozenset(f.name for f in fields(Cell) if f.type in ('int', 'bool', int, bool))
        self.bool_fields = frozenset(f.name for f in fields(Cell) if f.type in ('bool', bool))
        size = width * height
        self.typecodes = {name: ('B' if name in self.bool_fields or name in ('liquid', 'gas', 'flame', 'height', 'plant') else 'h' if name == 'elevation' else 'q') for name in self.numeric_fields}
        self.columns = {name: array(self.typecodes[name], [0]) * size if name in self.numeric_fields else [None] * size for name in self.field_names}
        self.exceptions = {}
        # Authored getters may derive sight fields from any material field.
        # Maintain membership at bind/replace, avoiding a map scan per query.
        self._authored_positions = set()
        self._mutable_owners = {}
        self._binding_memo = {}
        self.cells = MaterialRows(self, [MaterialRow(self, y, row) for y, row in enumerate(cells)])
        for y, row in enumerate(self.cells):
            for x, cell in enumerate(row):
                if '_material_binding' in cell.__dict__:
                    cell = deepcopy(cell)
                    list.__setitem__(row, x, cell)
                self._bind(y * width + x, cell)
        self._binding_memo = None

    def read(self, position, name):
        exceptional = self.exceptions.get((name, position), _MISSING)
        if exceptional is not _MISSING:
            return exceptional
        value = self.columns[name][position]
        return bool(value) if name in self.bool_fields else value

    def write(self, position, name, value, *, notify=True):
        if name in self.numeric_fields:
            code = self.typecodes[name]
            low, high = (0, 256) if code == 'B' else (-32768, 32768) if code == 'h' else (-(2**63), 2**63)
            if type(value) is int and low <= value < high or name in self.bool_fields and type(value) is bool:
                self.columns[name][position] = value
                self.exceptions.pop((name, position), None)
            else:
                self.columns[name][position] = 0
                self.exceptions[name, position] = value
        else:
            previous_owner = self._mutable_owners.pop((position, name), None)
            if previous_owner is not None:
                previous_owner.close()
            owned = _track(value, self._binding_memo)
            self.columns[name][position] = owned
            if isinstance(owned, (TrackedDict, TrackedList, tuple)):
                owner = _MutableOwner(self.journal, position, name, owned)
                if owner._nodes:
                    self._mutable_owners[position, name] = owner
        if notify:
            self.journal.record(position, name)

    def _bind(self, position, cell):
        # A Cell can belong to one position only. Callers explicitly copy when
        # inserting an already owned cell, rather than creating cross-map aliasing.
        values = {name: getattr(cell, name) for name in self.field_names}
        for name, value in values.items():
            self.write(position, name, value, notify=False)
            cell.__dict__.pop(name, None)
        cell.__dict__['_material_binding'] = (self, position)
        from .entities import Cell, _bound_cell_type
        original_type = type(cell)
        cell.__class__ = _bound_cell_type(original_type)
        if original_type is Cell:
            self._authored_positions.discard(position)
        else:
            self._authored_positions.add(position)

    def replace(self, position, cell):
        from .entities import Cell
        if not isinstance(cell, Cell):
            raise TypeError('material rows require Cell instances')
        y, x = divmod(position, self.width)
        old = self.cells[y][x]
        if old is cell:
            return cell
        if '_material_binding' in cell.__dict__:
            cell = deepcopy(cell)
        # Transfer the old field bundle intact: its aliases may still belong to
        # other live Cells or callers. Rebinding closes only this position's
        # ownership edges, so detached aliases continue notifying live owners.
        values = {name: self.read(position, name) for name in self.field_names}
        old.__dict__.pop('_material_binding', None)
        old.__class__ = old._unbound_cell_type
        old.__dict__.update(values)
        self._bind(position, cell)
        self.journal.record(position, '*')
        return cell


class _FixedGeometry(list):
    def _fixed(self, *args, **kwargs):
        raise TypeError('material geometry is fixed; assign cells to replace the map')

    append = extend = insert = pop = clear = remove = _fixed
    __delitem__ = __iadd__ = __imul__ = reverse = sort = _fixed


class MaterialRow(_FixedGeometry):
    def __init__(self, store, y, values):
        self.store, self.y = store, y
        list.__init__(self, values)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            indices = list(range(len(self)))[index]
            values = list(value)
            if len(indices) != len(values):
                raise ValueError('material row shape is fixed')
            for position, cell in zip(indices, values):
                self[position] = cell
            return
        if index < 0:
            index += len(self)
        self[index]  # validate before changing owner
        list.__setitem__(self, index, self.store.replace(self.y * self.store.width + index, value))

    def __deepcopy__(self, memo):
        result = []
        memo[id(self)] = result
        result.extend(deepcopy(cell, memo) for cell in self)
        return result

    def __reduce_ex__(self, protocol):
        return list, (), None, iter(self)


class MaterialRows(_FixedGeometry):
    def __init__(self, store, rows):
        self.store = store
        list.__init__(self, rows)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            indices = list(range(len(self)))[index]
            values = list(value)
            if len(indices) != len(values):
                raise ValueError('material map shape is fixed')
            for y, row in zip(indices, values):
                self[y] = row
            return
        self[index][:] = value

    def __deepcopy__(self, memo):
        result = []
        memo[id(self)] = result
        result.extend(deepcopy(row, memo) for row in self)
        return result

    def __reduce_ex__(self, protocol):
        return _restore_material_rows, (list(self), self.store.width, self.store.height)


def _restore_material_rows(rows, width, height):
    return MaterialStore(rows, width, height).cells


_MISSING = object()
