"""Versioned legacy display facts, detached from the simulation owner.

Wire records are immutable and schema preserving. Only changed top-level facts
and journal-selected cells cross the boundary. GameState query methods operate
on a client facade; their caches are local and discarded at publication.
"""
from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass, FrozenInstanceError
from collections import deque
from enum import Enum
from copy import deepcopy
import importlib
import weakref


@dataclass(frozen=True)
class Fact:
    kind: str
    type_name: tuple[str, str] | None
    values: tuple
    attributes: tuple = ()


@dataclass(frozen=True)
class DisplayDelta:
    generation: object
    version: int
    base: int | None
    width: int
    height: int
    fields: tuple
    cells: tuple
    removed: tuple = ()
    layers: tuple = ()
    removed_layers: tuple = ()


def freeze(value):
    return _freeze(value, freeze)


def _freeze(value, recurse):
    if value is None or isinstance(value, (bool, int, float, str, bytes, Enum)):
        return value
    if isinstance(value, dict):
        return Fact('dict', None, tuple((recurse(k), recurse(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple, deque, set, frozenset)):
        kind = 'tuple' if isinstance(value, tuple) else 'set' if isinstance(value, (set, frozenset)) else 'list'
        attrs = ()
        if hasattr(value, 'occurrence_ids'):
            attrs = tuple((name, recurse(getattr(value, name))) for name in
                          ('generation', 'revision', 'occurrence_ids'))
            if hasattr(value, 'cursor'):
                attrs += (('cursor', recurse(value.cursor)),)
        return Fact(kind, None, tuple(recurse(v) for v in value), attrs)
    if is_dataclass(value):
        cls = getattr(type(value), '_unbound_cell_type', type(value))
        from .core.entities import Cell, Entity, WorldItem
        if isinstance(value, Cell):
            # A custom getter can consult its owner or neighbors. Publish the
            # observed Cell fields, never executable owner-aware descriptors.
            cls = Cell
        attributes = ()
        if isinstance(value, (Entity, WorldItem)):
            from .core.command_identity import command_object_token
            attributes = (('_command_object_token', command_object_token(value)),)
        return Fact('object', (cls.__module__, cls.__qualname__),
                    tuple((f.name, recurse(getattr(value, f.name))) for f in fields(cls)), attributes)
    raise TypeError(f'No display schema for {type(value).__module__}.{type(value).__qualname__}')


class _FreezeCache:
    """Weak identity cache of immutable wire facts, trusted by mutation tokens.

    Runtime command identities are outside saved metadata revisions. Each entry
    therefore also remembers weak identity/token dependencies of its descendants.
    Checking those reads no gameplay fields and cannot hide a changed UUID.
    """
    def __init__(self):
        from .core.entities import Entity, Item, WorldItem, WorldEvent, LayerSnapshot
        self._record_types = (Entity, Item, WorldItem, WorldEvent, LayerSnapshot)
        self.entries = {}
        self._dependencies = []

    def freeze(self, value):
        if value is None or isinstance(value, (bool, int, float, str, bytes, Enum)):
            return value
        if type(value) not in self._record_types:
            return _freeze(value, self.freeze)
        from .core.metadata_versions import revision
        from .core.entities import Entity, WorldItem
        from .core.command_identity import command_object_token
        dependencies = []
        # Container membership freezes live; descendant records still reuse
        # their immutable facts. Most owned containers are tiny scalar fields,
        # where validating every schema costs more than freezing the contents.
        # Exact registered records are the useful, bounded cache granularity.
        token = revision(value, complete=True)
        if token is None:
            self.entries.pop(id(value), None)
            return _freeze(value, self.freeze)
        if token is not None and isinstance(value, (Entity, WorldItem)):
            dependencies.append((weakref.ref(value), command_object_token(value)))
        key = id(value)
        entry = self.entries.get(key) if token is not None else None
        if (entry is not None and entry[0]() is value and entry[1] == token
                and all(owner() is not None and
                        getattr(owner(), '_command_object_token', None) == identity
                        for owner, identity in entry[3])):
            if self._dependencies:
                self._dependencies[-1].extend(entry[3])
            return entry[2]
        self._dependencies.append(dependencies)
        try:
            fact = _freeze(value, self.freeze)
        finally:
            self._dependencies.pop()
        if self._dependencies:
            self._dependencies[-1].extend(dependencies)
        if token is not None:
            # A getter may mutate observable fields while being frozen. Such
            # output is usable this publication but cannot become a cache hit.
            after = revision(value, complete=True)
            if after == token:
                cache_ref = weakref.ref(self)
                def expired(owner_ref):
                    cache = cache_ref()
                    if cache is not None and cache.entries.get(key, (None,))[0] is owner_ref:
                        cache.entries.pop(key, None)
                try:
                    owner_ref = weakref.ref(value, expired)
                except TypeError:
                    pass
                else:
                    self.entries[key] = owner_ref, token, fact, tuple(dependencies)
        else:
            self.entries.pop(key, None)
        return fact


def _denied(*args, **kwargs):
    raise TypeError('display facts are read-only; submit an owner command')


class FrozenDict(dict):
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _denied

    def __deepcopy__(self, memo):
        return {deepcopy(k, memo): deepcopy(v, memo) for k, v in self.items()}


class FrozenList(list):
    __setitem__ = __delitem__ = append = extend = insert = pop = remove = clear = reverse = sort = __iadd__ = __imul__ = _denied

    def __deepcopy__(self, memo):
        return [deepcopy(v, memo) for v in self]


_READ_TYPES = {}


def _readonly_type(cls):
    found = _READ_TYPES.get(cls)
    if found is not None:
        return found

    def write(self, name, value):
        # Runtime query caches may be populated locally; all published fields
        # (including underscore facts) remain protected.
        if name.startswith('_') and name not in self.__dict__.get('_fact_names', ()):
            object.__setattr__(self, name, value)
            return
        raise FrozenInstanceError(f'display fact {name!r} is read-only')

    def copy(self, memo):
        result = object.__new__(cls)
        memo[id(self)] = result
        for name in self.__dict__.get('_fact_names', ()):
            object.__setattr__(result, name, deepcopy(getattr(self, name), memo))
        return result

    def construct(subtype, *args, **kwargs):
        # dataclasses.replace builds via obj.__class__(**fields). Such a new
        # value is a detached query/editor copy, not a published fact. Wire thaw
        # explicitly uses object.__new__ below and still installs readonly facts.
        return cls(*args, **kwargs)

    found = type('ReadOnly' + cls.__name__, (cls,),
                 {'__setattr__': write, '__delattr__': _denied, '__deepcopy__': copy,
                  '__new__': construct})
    _READ_TYPES[cls] = found
    return found


def thaw(value, previous=None):
    if not isinstance(value, Fact):
        return value
    if getattr(previous, '_wire_fact', None) == value:
        return previous
    if value.kind == 'dict':
        prior = previous if isinstance(previous, dict) else {}
        result = FrozenDict((thaw(k), thaw(v, prior.get(thaw(k)))) for k, v in value.values)
    elif value.kind == 'tuple':
        return tuple(thaw(v, previous[i] if isinstance(previous, tuple) and i < len(previous) else None)
                     for i, v in enumerate(value.values))
    elif value.kind == 'set':
        return frozenset(thaw(v) for v in value.values)
    elif value.kind == 'list':
        # Reordering preserves unchanged entity/item identity for UI drafts.
        prior = list(previous) if isinstance(previous, list) else []
        by_fact = {getattr(v, '_wire_fact', None): v for v in prior
                   if isinstance(getattr(v, '_wire_fact', None), Fact)}
        result = FrozenList(thaw(v, by_fact.get(v) if isinstance(v, Fact) else
                                 prior[i] if i < len(prior) else None)
                            for i, v in enumerate(value.values))
        result.__dict__.update((k, thaw(v)) for k, v in value.attributes)
    else:
        module, name = value.type_name
        cls = importlib.import_module(module)
        for part in name.split('.'):
            cls = getattr(cls, part)
        result = object.__new__(_readonly_type(cls))
        result.__dict__.update((k, thaw(v, getattr(previous, k, None))) for k, v in value.values)
        result.__dict__.update((k, thaw(v)) for k, v in value.attributes)
        result.__dict__['_fact_names'] = frozenset(k for k, _ in (*value.values, *value.attributes))
    result.__dict__['_wire_fact'] = value
    return result


class _ArchivedPublisher:
    def __init__(self):
        self._freeze_cache = _FreezeCache()
        self.fields = {}
        self.cursor = None
        self.version = 0
        self._candidate_ref = None
        self._metadata_entry = None

    def _metadata(self, layer):
        from .core.entities import LayerSnapshot
        from .core.metadata_versions import revision
        if type(layer) is not LayerSnapshot:
            self._candidate_ref = self._metadata_entry = None
            return {f.name: self._freeze_cache.freeze(getattr(layer, f.name))
                    for f in fields(layer) if f.name != 'cells'}
        if self._candidate_ref is None or self._candidate_ref() is not layer:
            # First identity encounter follows reference freezing without a
            # layer revision prepass; first facts are never admitted as tracked.
            try:
                self._candidate_ref = weakref.ref(layer)
            except TypeError:
                # An authored replacement of the imported layer class can be
                # an otherwise supported dataclass without weakref storage.
                self._candidate_ref = None
            self._metadata_entry = None
            return {f.name: self._freeze_cache.freeze(getattr(layer, f.name))
                    for f in fields(layer) if f.name != 'cells'}
        token = revision(layer)
        entry = self._metadata_entry
        if (token is not None and entry is not None and entry[0]() is layer
                and entry[1] == token
                and all(owner() is not None and
                        type(current := getattr(owner(), '_command_object_token', None)) is int
                        and current == identity for owner, identity in entry[3])):
            return entry[2]
        self._metadata_entry = None
        if token is None:
            return {f.name: self._freeze_cache.freeze(getattr(layer, f.name))
                    for f in fields(layer) if f.name != 'cells'}
        dependencies = []
        self._freeze_cache._dependencies.append(dependencies)
        try:
            current = {f.name: self._freeze_cache.freeze(getattr(layer, f.name))
                       for f in fields(layer) if f.name != 'cells'}
        finally:
            self._freeze_cache._dependencies.pop()
        if revision(layer) == token:
            self._metadata_entry = (weakref.ref(layer), token, current, tuple(dependencies))
        return current

    def build(self, layer):
        from .core.material_store import MaterialStore
        store = getattr(layer.cells, 'store', None)
        height = len(layer.cells)
        width = len(layer.cells[0]) if height else 0
        if store is None:
            store = MaterialStore(layer.cells, width, height)
            layer.cells = store.cells
        batch = store.journal.changes_since(self.cursor)
        full = self.cursor is None or batch.reset
        current = self._metadata(layer)

        changed = tuple((k, v) for k, v in current.items()
                        if full or self.fields.get(k) != v)
        positions = range(width * height) if full else sorted(set(batch.positions) | store._authored_positions)
        cells = tuple((p, freeze(layer.cells[p // width][p % width])) for p in positions)
        self.cursor = batch.cursor
        if not full and not changed and not cells:
            return None
        self.version += 1
        self.fields = current
        return DisplayDelta(batch.generation, self.version, None if full else self.version - 1,
                            width, height, changed, cells)


def _archive_view(delta, previous=None):
    from .core.entities import LayerSnapshot
    if delta.base is not None and (previous is None or previous._display_version != delta.base):
        raise ValueError('archived display delta requires its matching base')
    values = {} if delta.base is None else {name: previous.__dict__[name]
                                          for name in previous._fact_names}
    values.update((name, thaw(value)) for name, value in delta.fields)
    rows = [[None] * delta.width for _ in range(delta.height)] if delta.base is None else list(previous.cells)
    changed = {}
    for position, value in delta.cells:
        y, x = divmod(position, delta.width)
        changed.setdefault(y, list(rows[y]))[x] = thaw(value)
    for y, row in changed.items():
        rows[y] = FrozenList(row)
    values['cells'] = FrozenList(rows)
    result = object.__new__(_readonly_type(LayerSnapshot))
    result.__dict__.update(values)
    result.__dict__.update(_fact_names=frozenset(values), _display_version=delta.version)
    return result


class DisplayPublisher:
    """Independent journal reader; no Cell inspection on unchanged maps.

    Trusted metadata reuses immutable facts by weak object identity and observed
    revision. Public aliases and authored policies freeze conservatively.
    """
    def __init__(self):
        self._fields = {}
        self._store = None
        self._cursor = None
        self._version = 0
        self._generation = None
        self._layers = {}
        self._freeze_cache = _FreezeCache()

    def build(self, state):
        from .core.command_context import command_context_token
        from .legacy_commands import map_identity
        store = getattr(state.cells, 'store', None)
        if store is None:
            raise ValueError('legacy independent display requires authoritative material journal')
        # Legacy rendering called developed_for_depth().setdefault implicitly.
        # Preserve its exact empty-layer bookkeeping on the owner, without
        # letting a UI query mutate exploration facts or invent developed cells.
        state.developed_cells.setdefault(str(state.depth), set())
        generation = (command_context_token(state), map_identity(state))
        full = generation != self._generation
        batch = store.journal.changes_since(None if full else self._cursor)
        full = full or batch.reset
        previous = {} if full else self._fields
        # Archived layers are separate worlds, never copied by live display
        # publication. Layer observation uses the active world facts.
        current = {f.name: self._freeze_cache.freeze(getattr(state, f.name)) for f in fields(state)
                   if f.name not in ('cells', 'layer_states', 'ui_dirty', 'ticker_notes')}
        for name in ('_combat_fx_seq', '_presentation_map_identity', '_presentation_stream',
                     '_command_context_token', '_presentation_explosions',
                     '_presentation_explosion_recovery', '_combat_fx_events', 'anomaly_intents'):
            if name in state.__dict__:
                current[name] = freeze(state.__dict__[name])
        from .core.visual_events import peek_visual_events
        current['_display_visual_events'] = freeze(peek_visual_events(state))
        current['messages'] = freeze(state.messages)
        from .core.ticker_transport import ticker_window
        ticker = ticker_window(state.ticker_notes)
        current['ticker_notes'] = Fact('list', None, ticker.notes, (
            ('generation', ticker.generation), ('revision', ticker.revision),
            ('occurrence_ids', freeze(ticker.identities)),
            ('cursor', freeze(state.ticker_notes.cursor)),
            ('_ticker_retained_ids', freeze(ticker.retained)),
            ('_ticker_backlog', ticker.backlog)))
        positions = range(state.width * state.height) if full else sorted(set(batch.positions) | store._authored_positions)
        cells = tuple((p, freeze(state.cells[p // state.width][p % state.width])) for p in positions)
        if full:
            self._layers = {}
        removed_layers = tuple(self._layers.keys() - state.layer_states.keys())
        for key in removed_layers:
            self._layers.pop(key)
        layer_deltas = []
        for key, layer in state.layer_states.items():
            change = self._layers.setdefault(key, _ArchivedPublisher()).build(layer)
            if change is not None:
                layer_deltas.append((key, change))
        self._version += 1
        result = DisplayDelta(generation, self._version, None if full else self._version - 1,
                              state.width, state.height,
                              tuple((k, v) for k, v in current.items() if previous.get(k) != v),
                              cells, tuple(previous.keys() - current.keys()),
                              tuple(layer_deltas), removed_layers)
        self._fields, self._generation, self._cursor = current, generation, batch.cursor
        return result


from .core.state import GameState


class LegacyDisplayState(GameState):
    """Stable UI identity over immutable facts, with local derived caches."""
    def __init__(self, initial):
        object.__setattr__(self, '_display_version', None)
        self.publish(initial)

    def __setattr__(self, name, value):
        if name.startswith('_') and name not in self.__dict__.get('_fact_names', ()):
            object.__setattr__(self, name, value)
            return
        raise FrozenInstanceError(f'display fact {name!r} is read-only')

    def publish(self, delta):
        if delta.base is not None and (delta.base != self._display_version or
                                      delta.generation != self._display_generation):
            raise ValueError('display delta requires its matching base')
        full = delta.base is None
        attributes = {} if full else {name: self.__dict__[name] for name in self._fact_names}
        attributes.update((name, thaw(value, attributes.get(name))) for name, value in delta.fields)
        for name in delta.removed:
            attributes.pop(name, None)
        rows = [[None] * delta.width for _ in range(delta.height)] if full else list(self.cells)
        changed_rows = {}
        for position, value in delta.cells:
            y, x = divmod(position, delta.width)
            row = changed_rows.setdefault(y, list(rows[y]))
            row[x] = thaw(value)
        for y, row in changed_rows.items():
            rows[y] = FrozenList(row)
        if full and any(cell is None for row in rows for cell in row):
            raise ValueError('initial display missing cells')
        attributes['cells'] = FrozenList(rows)
        layers = {} if full else dict(self.layer_states)
        for key in delta.removed_layers:
            layers.pop(key, None)
        for key, change in delta.layers:
            layers[key] = _archive_view(change, layers.get(key))
        attributes['layer_states'] = FrozenDict(layers)
        seen_visual = self.__dict__.get('_display_seen_visual', set()) if not full else set()
        cleared_intents = self.__dict__.get('_display_cleared_intents', set()) if not full else set()
        if cleared_intents:
            attributes['anomaly_intents'] = tuple(event for event in attributes.get('anomaly_intents', ())
                if (event.entity_id, event.action_seq, event.started) not in cleared_intents)
        self.__dict__.clear()
        self.__dict__.update(attributes)
        self.__dict__['_display_seen_visual'] = seen_visual
        self.__dict__['_display_cleared_intents'] = cleared_intents
        self.__dict__.update(_fact_names=frozenset(attributes), _display_version=delta.version,
                             _display_generation=delta.generation, ui_dirty=set())

    def __deepcopy__(self, memo):
        detached = object.__new__(GameState)
        memo[id(self)] = detached
        for name in self._fact_names:
            object.__setattr__(detached, name, deepcopy(getattr(self, name), memo))
        return detached

    def drain_visual_events(self):
        from .core.visual_events import _result_signature
        seen = self._display_seen_visual
        source = getattr(self, '_display_visual_events', ())
        events, signatures = [], set()
        for event in source:
            signature = _result_signature(event)
            if event.event_id not in seen and signature not in signatures:
                events.append(event)
                signatures.add(signature)
        live = {event.event_id for event in source}
        seen.intersection_update(live)
        seen.update(event.event_id for event in source)
        return tuple(events)

    def clear_display_intents(self):
        """Acknowledge presentation occurrences locally without altering owner facts."""
        self._display_cleared_intents.update((event.entity_id, event.action_seq, event.started)
            for event in getattr(self, 'anomaly_intents', ()))
        self.__dict__['anomaly_intents'] = ()

    def __repr__(self):
        return f'<LegacyDisplayState version={self._display_version}>'

    @property
    def spatial_index(self):
        found = self.__dict__.get('_display_spatial')
        if found is None:
            from .core.spatial_index import SpatialIndex
            found = SpatialIndex(self.enemies, self.player)
            self._display_spatial = found
        return found

    def developed_for_depth(self):
        return self.developed_cells.get(str(self.depth), frozenset())

    def visible_cells(self):
        # This pure query cache is local. Knowledge stays in owner-published
        # terrain_memory and exploration fields.
        return super().visible_cells()

    def mark_ui_dirty(self, *domains):
        self.ui_dirty.update(domains or ('status', 'body', 'panels', 'log', 'hitmap'))

    wait = _denied

