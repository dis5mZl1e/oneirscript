"""Mutation-maintained metadata revisions with conservative alias fallbacks.

Plain mutable values keep their identity and are deliberately untrusted. Only
explicit private copies and newly created defaults use observable containers.
No version query fingerprints or compares the saved object graph.
"""
from copy import deepcopy
from dataclasses import fields, is_dataclass
from itertools import count
from weakref import WeakSet, ref
import gc
import sys
import ctypes


_serial = count(1)
_records = {}
_schemas = {}
_layer_types = set()
_container_policies = {}
_policy_results = {}
_ATOMIC = (str, int, float, bool, bytes, type(None))
_COPY_FIELDS = frozenset(('logic_boards', 'logic_fences', 'enemy_skill_fields',
                          'realm_bg_zones', 'realm_features'))


class _WeakParents:
    """Single callback-free edge; mature WeakSet cleanup for real fanout."""
    __slots__ = ('_edges',)

    def __init__(self):
        self._edges = None

    def _live(self):
        edges = self._edges
        if edges is None:
            return ()
        if type(edges) is not WeakSet:
            parent = edges()
            if parent is None:
                self._edges = None
                return ()
            return (parent,)
        live = tuple(edges)
        if not live:
            self._edges = None
        elif len(live) == 1:
            self._edges = ref(live[0])
        return live

    def add(self, parent):
        edges = self._edges
        if edges is None:
            self._edges = ref(parent)
        elif type(edges) is WeakSet:
            edges.add(parent)
        else:
            previous = edges()
            if previous is None:
                self._edges = ref(parent)
            elif previous is not parent:
                self._edges = WeakSet((previous, parent))

    def discard(self, parent):
        edges = self._edges
        if edges is None:
            return
        if type(edges) is WeakSet:
            edges.discard(parent)
            self._live()
        elif edges() is parent or edges() is None:
            self._edges = None

    def __bool__(self):
        edges = self._edges
        if edges is None:
            return False
        if type(edges) is not WeakSet:
            if edges() is not None:
                return True
            self._edges = None
            return False
        return bool(edges)

    def __len__(self):
        return len(self._live())

    def __iter__(self):
        return iter(self._live())

    def __contains__(self, parent):
        return any(value is parent for value in self._live())


class _Node:
    __slots__ = ('version', 'parents', 'children', 'local_safe', 'safe',
                 'is_record', 'copy_safe', 'complete_schema', 'asdict_safe',
                 'incomplete_children', 'unsupported', 'untrusted_children',
                 'uncopyable_children', 'counts', 'cache', 'cache_version',
                 'cache_mode', '__weakref__')

    def __init__(self):
        self.version = next(_serial)
        self.parents = _WeakParents()
        self.children = {}
        self.local_safe = True
        self.safe = True
        self.is_record = False
        self.copy_safe = True
        self.complete_schema = True
        self.asdict_safe = True
        self.incomplete_children = set()
        self.unsupported = set()
        self.untrusted_children = set()
        self.uncopyable_children = set()
        self.counts = {}
        self.cache = None
        self.cache_version = None
        self.cache_mode = None

    def replace(self, children, local_safe=True):
        # Do not trust cyclic saved graphs (asdict itself cannot encode them).
        for key, child in tuple(children.items()):
            # A node without incoming edges cannot be reachable through an
            # existing child's descendants. Newly observed trees need no
            # repeated traversal of their complete subtrees at each parent.
            if child is None or (not self.parents and child is not self):
                continue
            pending, seen = [child], set()
            while pending:
                descendant = pending.pop()
                if descendant is self:
                    children[key] = None
                    local_safe = False
                    break
                if id(descendant) in seen:
                    continue
                seen.add(id(descendant))
                pending.extend(node for node in descendant.children.values() if node is not None)
        old = set(self.children.values()) - {None}
        new = set(children.values()) - {None}
        for child in old - new:
            child.parents.discard(self)
        for child in new - old:
            child.parents.add(self)
        self.children = children
        self.local_safe = local_safe
        self.counts = {}
        for child in children.values():
            if child is not None:
                self.counts[child] = self.counts.get(child, 0) + 1
        self.untrusted_children = {child for child in new if not child.safe}
        self.uncopyable_children = {child for child in new if not child.copy_safe}
        self.incomplete_children = {child for child in new if not child.asdict_safe}
        self.touch()

    def set_field(self, name, child, supported):
        pending, seen = ([child] if child is not None and
                         (self.parents or child is self) else []), set()
        while pending:
            descendant = pending.pop()
            if descendant is self:
                child, supported = None, False
                break
            if id(descendant) not in seen:
                seen.add(id(descendant))
                pending.extend(node for node in descendant.children.values() if node is not None)
        old = self.children.get(name)
        if old is not child:
            if old is not None:
                self.counts[old] -= 1
                if not self.counts[old]:
                    del self.counts[old]
                    old.parents.discard(self)
                    self.untrusted_children.discard(old)
                    self.uncopyable_children.discard(old)
                    self.incomplete_children.discard(old)
            if child is not None:
                self.counts[child] = self.counts.get(child, 0) + 1
                child.parents.add(self)
                if not child.safe:
                    self.untrusted_children.add(child)
                if not child.copy_safe:
                    self.uncopyable_children.add(child)
                if not child.asdict_safe:
                    self.incomplete_children.add(child)
        self.children[name] = child
        if supported:
            self.unsupported.discard(name)
        else:
            self.unsupported.add(name)
        self.local_safe = not self.unsupported
        self.touch()

    def touch(self, seen=None):
        previous_safe = self.safe
        previous_copy_safe = self.copy_safe
        previous_asdict_safe = self.asdict_safe
        self.safe = self.local_safe and not self.untrusted_children
        self.copy_safe = self.safe and not self.is_record and not self.uncopyable_children
        self.asdict_safe = self.safe and self.complete_schema and not self.incomplete_children
        if not self.parents:
            self.version = next(_serial)
            return
        if seen is None:
            seen = set()
        if (id(self) in seen and previous_safe == self.safe
                and previous_copy_safe == self.copy_safe and previous_asdict_safe == self.asdict_safe):
            return
        seen.add(id(self))
        self.version = next(_serial)
        for parent in tuple(self.parents):
            if self.safe:
                parent.untrusted_children.discard(self)
            else:
                parent.untrusted_children.add(self)
            if self.copy_safe:
                parent.uncopyable_children.discard(self)
            else:
                parent.uncopyable_children.add(self)
            if self.asdict_safe:
                parent.incomplete_children.discard(self)
            else:
                parent.incomplete_children.add(self)
            parent.touch(seen)


from types import MappingProxyType

_EMPTY_NODE_MAP = MappingProxyType({})
_EMPTY_NODE_SET = frozenset()


class _EmptyNode(_Node):
    """Only initially empty exact owned containers defer mutable bookkeeping."""
    __slots__ = ()

    def __init__(self):
        self.version = next(_serial)
        self.parents = _WeakParents()
        self.children = _EMPTY_NODE_MAP
        self.local_safe = True
        self.safe = True
        self.is_record = False
        self.copy_safe = True
        self.complete_schema = True
        self.asdict_safe = True
        self.incomplete_children = _EMPTY_NODE_SET
        self.unsupported = _EMPTY_NODE_SET
        self.untrusted_children = _EMPTY_NODE_SET
        self.uncopyable_children = _EMPTY_NODE_SET
        self.counts = _EMPTY_NODE_MAP
        self.cache = None
        self.cache_version = None
        self.cache_mode = None

    def _materialize(self):
        if self.children is _EMPTY_NODE_MAP:
            # Prepare all private mutable state before exposing a child edge.
            children, counts = {}, {}
            incomplete, unsupported, untrusted, uncopyable = set(), set(), set(), set()
            self.children, self.counts = children, counts
            self.incomplete_children, self.unsupported = incomplete, unsupported
            self.untrusted_children, self.uncopyable_children = untrusted, uncopyable

    def replace(self, children, local_safe=True):
        self._materialize()
        return super().replace(children, local_safe)

    def set_field(self, name, child, supported):
        self._materialize()
        return super().set_field(name, child, supported)

def _policy(cls):
    policies = (cls.__getattribute__, cls.__setattr__, cls.__delattr__, getattr(cls, '__deepcopy__', None),
                cls.__getstate__, getattr(cls, '__setstate__', None), cls.__reduce_ex__)
    return (tuple(id(policy) for policy in policies),
            tuple((name, next((id(base.__dict__[name]) for base in cls.__mro__
                               if name in base.__dict__), id(None)))
                  for name in (*[f.name for f in fields(cls)], '_command_object_token')))


def register(cls, excluded=()):
    """Register an exact built-in schema after installing its mutation hook."""
    _schemas[cls] = (frozenset(f.name for f in fields(cls) if f.name not in excluded), _policy(cls))
    if 'cells' in excluded:
        _layer_types.add(cls)


class _DictionaryHeader311(ctypes.Structure):
    _fields_ = (('references', ctypes.c_ssize_t), ('type_address', ctypes.c_void_p),
                ('used', ctypes.c_ssize_t), ('version', ctypes.c_uint64))


def _class_stamp(cls):
    # CPython 3.11's dict version covers ALL class dictionary edits, including
    # inherited descriptors. Other interpreters/layouts retain full checking.
    if (sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 11)
            or hasattr(sys, 'gettotalrefcount')):
        return None
    stamp = []
    for base in cls.__mro__:
        references = gc.get_referents(vars(base))
        if len(references) != 1 or type(references[0]) is not dict:
            return None
        dictionary = references[0]
        header = _DictionaryHeader311.from_address(id(dictionary))
        if header.type_address != id(dict) or header.used != len(dictionary) or not header.version:
            return None
        stamp.append((id(dictionary), header.version))
    return tuple(stamp)


def _record_policy_valid(cls, expected):
    stamp = _class_stamp(cls)
    if stamp is not None:
        # Field objects and their mapping can change in place without changing
        # the class dictionary. Match the live names/order used by _policy;
        # fields() also filters live Field._field_type edits.
        stamp = stamp, tuple(field.name for field in fields(cls))
    key = (cls, 'record')
    previous = _policy_results.get(key)
    if stamp is not None and previous is not None and previous[:2] == (stamp, expected):
        return previous[2]
    valid = _policy(cls) == expected
    if stamp is not None:
        _policy_results[key] = stamp, expected, valid
    return valid


def _container_policy_valid(cls, expected):
    stamp = _class_stamp(cls)
    key = (cls, 'container')
    previous = _policy_results.get(key)
    if stamp is not None and previous is not None and previous[:2] == (stamp, expected):
        return previous[2]
    valid = _container_policy(cls) == expected
    if stamp is not None:
        _policy_results[key] = stamp, expected, valid
    return valid


def _policies_valid():
    # Class edits have no instance mutation signal. Check this small fixed set
    # of schemas, never the instance graph, and fall back globally on edits.
    return (all(_record_policy_valid(cls, policy) for cls, (_, policy) in _schemas.items())
            and all(_container_policy_valid(cls, policy)
                    for cls, policy in _container_policies.items()))


def _container_policy(cls):
    names = ('__getattribute__', '__iter__', '__getitem__', '__setitem__', '__delitem__',
             '__init__', '__deepcopy__', '__reduce_ex__', 'items', 'values', 'keys',
             'append', 'extend', 'insert', 'pop', 'popitem', 'remove', 'clear',
             'reverse', 'sort', 'update', 'setdefault', '__iadd__', '__imul__', '__ior__',
             '__getstate__', '__setstate__')
    methods = tuple(id(getattr(cls, name, None)) for name in names)
    private = tuple(next((id(base.__dict__[name]) for base in cls.__mro__
                          if name in base.__dict__), id(None))
                    for name in ('_metadata_node', '_refresh', '__dict__'))
    return methods + private


def _remember(value, node):
    descriptor = _owned_node_slots.get(type(value))
    if descriptor is not None:
        descriptor.__set__(value, node)
        return
    identity = id(value)
    def expired(reference):
        entry = _records.get(identity)
        if entry is not None and entry[0] is reference:
            del _records[identity]
    _records[identity] = (ref(value, expired), node)


def _existing(value):
    descriptor = _owned_node_slots.get(type(value))
    if descriptor is not None:
        try:
            return descriptor.__get__(value, type(value))
        except AttributeError:
            return None
    entry = _records.get(id(value))
    return entry[1] if entry is not None and entry[0]() is value else None


def _child(value, stack):
    if type(value) in _ATOMIC:
        return None, True
    if type(value) is tuple:
        if id(value) in stack:
            return None, False
        children, safe = {}, True
        for i, child in enumerate(value):
            node, trusted = _child(child, stack | {id(value)})
            children[i] = node
            safe = safe and trusted
        if not any(children.values()):
            return None, safe
        node = _Node()
        node.replace(children, safe)
        return node, True
    if type(value) in (OwnedDict, OwnedList):
        if id(value) in stack:
            return None, False
        return _observe_container(value, stack), True
    if type(value) in _schemas:
        if id(value) in stack:
            return None, False
        node = _observe(value, stack)
        return node, True
    # SpatialActors supplies a node through an explicit integration. Its child
    # references retain the actors, while these subscriptions remain weak.
    if type(value) in _container_types:
        if id(value) in stack:
            return None, False
        node = _observe_container(value, stack)
        return node, True
    return None, False


_container_types = set()


def register_container(cls):
    _container_types.add(cls)
    _container_policies[cls] = _container_policy(cls)


def _observe_container(value, stack=None):
    node = _existing(value)
    if node is None:
        # Exact builtins only: no authored __len__ is called for admission.
        empty_owned = ((type(value) is OwnedDict and dict.__len__(value) == 0)
                       or (type(value) is OwnedList and list.__len__(value) == 0))
        node = _EmptyNode() if empty_owned else _Node()
        _remember(value, node)
        if not empty_owned:
            _refresh_container(value, node, (stack or set()) | {id(value)})
    return node


def _refresh_container(value, node, stack=None):
    stack = (stack or set()) | {id(value)}
    children, safe = {}, True
    pairs = value.items() if isinstance(value, dict) else enumerate(value)
    for key, child in pairs:
        child_node, trusted = _child(child, stack)
        children[key] = child_node
        safe = safe and trusted and type(key) in _ATOMIC
    node.replace(children, safe)


def container_changed(value):
    node = _existing(value)
    if node is not None:
        _refresh_container(value, node)


def _observe(value, stack=None):
    node = _existing(value)
    if node is not None:
        return node
    node = _Node()
    node.is_record = True
    node.complete_schema = len(_schemas[type(value)][0]) == len(fields(value))
    _remember(value, node)
    children, safe = {}, True
    stack = (stack or set()) | {id(value)}
    for name in _schemas[type(value)][0]:
        child, trusted = _child(getattr(value, name), stack)
        children[name] = child
        safe = safe and trusted
        if not trusted:
            node.unsupported.add(name)
    node.replace(children, safe)
    return node


def assigned(value, name):
    """Called after a schema field write; unobserved objects allocate nothing."""
    node = _existing(value)
    schema = _schemas.get(type(value))
    if node is None or schema is None or name not in schema[0]:
        return
    # An authored setter need not read its getter. Observer maintenance must
    # never introduce such reads when a registered schema policy was changed.
    if not _record_policy_valid(type(value), schema[1]):
        node.set_field(name, None, False)
        return
    child, trusted = _child(getattr(value, name), {id(value)})
    node.set_field(name, child, trusted)


class MetadataRecord:
    """Assignment hook for exact built-in Item/event/snapshot dataclasses."""
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        assigned(self, name)

    def __delattr__(self, name):
        object.__delattr__(self, name)
        deleted(self, name)


def deleted(value, name):
    try:
        assigned(value, name)
    except AttributeError:
        node = _existing(value)
        if node is not None:
            node.set_field(name, None, False)


def revision(value, *, complete=False):
    """Return a monotonic object token, or None for a conservative fallback.

    Scalar and tuple roots have no observable mutation identity. They return
    None; tuples inside owned records/containers have persistent edge nodes.
    """
    cls = type(value)
    if cls not in _schemas and cls not in (OwnedDict, OwnedList) and cls not in _container_types:
        return None
    existing = _existing(value)
    if existing is not None and not existing.safe:
        # Unsafe aliases cannot be reused under any class policy. Mutations
        # maintain this flag; policy edits can only require more fallbacks.
        return None
    if not _policies_valid():
        return None
    node, trusted = _child(value, set())
    if not trusted or (node is not None and not node.safe):
        return None
    if complete and node is not None and not node.asdict_safe:
        # Full wire facts include cells even for metadata-only layer schemas,
        # including layers nested beneath an otherwise trusted record.
        return None
    if type(value) in _layer_types and not _layer_copy_safe(node):
        # LayerSnapshot's deepcopy-only domains may contain objects whose
        # additional dynamic state is outside the saved dataclass schema.
        return None
    return node.version if node is not None else 0


class OwnedDict(dict):
    """Own membership; preserve supplied child aliases instead of wrapping them."""
    __slots__ = ('_metadata_node', '__dict__', '__weakref__')
    def __init__(self, values=(), **kwargs):
        try:
            dict.__init__(self, values, **kwargs)
        finally:
            self._refresh()

    def _refresh(self):
        container_changed(self)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self._refresh()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._refresh()

    def clear(self):
        dict.clear(self)
        self._refresh()

    def pop(self, key, *default):
        result = dict.pop(self, key, *default)
        self._refresh()
        return result

    def popitem(self):
        result = dict.popitem(self)
        self._refresh()
        return result

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def update(self, *args, **kwargs):
        # Preserve Python's partial mutation if an input iterator raises.
        try:
            dict.update(self, *args, **kwargs)
        finally:
            self._refresh()

    def __ior__(self, other):
        self.update(other)
        return self

    def __deepcopy__(self, memo):
        result = type(self)()
        memo[id(self)] = result
        for key, child in self.items():
            dict.__setitem__(result, deepcopy(key, memo), deepcopy(child, memo))
        result._refresh()
        return result

    def __getstate__(self):
        if type(self) in _owned_node_slots:
            return _owned_dict_slots[type(self)].__get__(self, type(self)) or None
        return object.__getstate__(self)

    def __reduce_ex__(self, protocol):
        return type(self), (), None, None, iter(self.items())


class OwnedList(list):
    """Observable list membership with ordinary alias-preserving insertion."""
    __slots__ = ('_metadata_node', '__dict__', '__weakref__')
    def __init__(self, values=()):
        try:
            list.__init__(self, values)
        finally:
            self._refresh()

    def _refresh(self):
        container_changed(self)

    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        self._refresh()

    def __delitem__(self, key):
        list.__delitem__(self, key)
        self._refresh()

    def append(self, value):
        list.append(self, value)
        self._refresh()

    def extend(self, values):
        try:
            list.extend(self, values)
        finally:
            self._refresh()

    def insert(self, index, value):
        list.insert(self, index, value)
        self._refresh()

    def pop(self, index=-1):
        value = list.pop(self, index)
        self._refresh()
        return value

    def remove(self, value):
        list.remove(self, value)
        self._refresh()

    def clear(self):
        list.clear(self)
        self._refresh()

    def reverse(self):
        list.reverse(self)
        self._refresh()

    def sort(self, *args, **kwargs):
        try:
            list.sort(self, *args, **kwargs)
        finally:
            self._refresh()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        list.__imul__(self, count)
        self._refresh()
        return self

    def __deepcopy__(self, memo):
        result = type(self)()
        memo[id(self)] = result
        list.extend(result, (deepcopy(child, memo) for child in self))
        result._refresh()
        return result

    def __getstate__(self):
        if type(self) in _owned_node_slots:
            return _owned_dict_slots[type(self)].__get__(self, type(self)) or None
        return object.__getstate__(self)

    def __reduce_ex__(self, protocol):
        return type(self), (), None, iter(self)


_owned_node_slots = {cls: cls.__dict__['_metadata_node'] for cls in (OwnedDict, OwnedList)}
_owned_dict_slots = {cls: cls.__dict__['__dict__'] for cls in (OwnedDict, OwnedList)}


for _owned_type in (OwnedDict, OwnedList):
    _container_policies[_owned_type] = _container_policy(_owned_type)


def owned_copy(value, memo=None):
    """Explicit transfer for private graphs only; never use on public aliases."""
    if memo is None:
        memo = {}
    if id(value) in memo:
        return memo[id(value)]
    if type(value) in (dict, OwnedDict):
        result = OwnedDict()
        memo[id(value)] = result
        for key, child in value.items():
            dict.__setitem__(result, key, owned_copy(child, memo))
        result._refresh()
        return result
    if type(value) in (list, OwnedList):
        result = OwnedList()
        memo[id(value)] = result
        list.extend(result, (owned_copy(child, memo) for child in value))
        result._refresh()
        return result
    if type(value) is tuple:
        # Cyclic tuples require Python's memo-aware deepcopy semantics; leave
        # them conservative rather than inventing a broken identity rewrite.
        result = tuple(owned_copy(child, memo) for child in value)
        if id(value) in memo:
            return memo[id(value)]
        memo[id(value)] = result
        return result
    return deepcopy(value, memo)


def adopt_private(value, memo=None):
    """Own newly decoded private graphs while retaining record identities.

    This is intentionally separate from public constructors/assignments. Never
    call it on a live graph with external plain-container aliases.
    """
    if memo is None:
        memo = {}
    if id(value) in memo:
        return memo[id(value)]
    cls = type(value)
    if cls in _schemas:
        memo[id(value)] = value
        for name in _schemas[cls][0]:
            setattr(value, name, adopt_private(getattr(value, name), memo))
        return value
    if cls in _container_types:
        memo[id(value)] = value
        for child in value:
            adopt_private(child, memo)
        return value
    if cls in (dict, OwnedDict):
        result = OwnedDict()
        memo[id(value)] = result
        for key, child in value.items():
            dict.__setitem__(result, key, adopt_private(child, memo))
        return result
    if cls in (list, OwnedList):
        result = OwnedList()
        memo[id(value)] = result
        list.extend(result, (adopt_private(child, memo) for child in value))
        return result
    if cls is tuple:
        result = tuple(adopt_private(child, memo) for child in value)
        if id(value) in memo:
            return memo[id(value)]
        memo[id(value)] = result
        return result
    return value


class _AsdictMemo(dict):
    # asdict walks each occurrence independently. Reuse internal immutable
    # cache payloads without introducing aliases in the caller's mutable tree.
    def get(self, key, default=None):
        return default


def _detach_emitted(value):
    """Detach an asdict tree, copying every mutable occurrence independently."""
    cls = type(value)
    if cls in _ATOMIC:
        return value
    if cls is dict:
        return {_detach_emitted(key): _detach_emitted(child)
                for key, child in value.items()}
    if cls is list:
        return [_detach_emitted(child) for child in value]
    if cls is tuple:
        return tuple(_detach_emitted(child) for child in value)
    # Authored values keep their original deepcopy policy. Such values cannot
    # enter a trusted shared cache, but conservative layer output supports them.
    return deepcopy(value, _AsdictMemo())


def _detach_layer(value):
    return {name: deepcopy(child) if name in _COPY_FIELDS else
            _detach_emitted(child) for name, child in value.items()}


def encode(value, asdict, *, _policies=None, _borrow=False):
    """Detached asdict-compatible encoding with per-observable-node reuse."""
    policies = _policies_valid() if _policies is None else _policies
    root, supported = _child(value, set()) if policies else (None, False)
    shared = supported and root is not None and root.asdict_safe
    if type(value) in _schemas and len(_schemas[type(value)][0]) != len(fields(value)):
        shared = False
    def visit(current):
        cls = type(current)
        if cls in _ATOMIC:
            return current
        node = None
        if policies and cls in _schemas:
            node = _observe(current)
        elif policies and cls in (OwnedDict, OwnedList):
            node = _observe_container(current)
        elif policies and cls in _container_types:
            node = _observe_container(current)
        if (node is not None and node.asdict_safe and node.cache_version == node.version
                and node.cache_mode == 'asdict'):
            return node.cache if shared else deepcopy(node.cache, _AsdictMemo())
        if is_dataclass(current):
            if not policies or cls not in _schemas:
                return asdict(current)
            result = {f.name: visit(getattr(current, f.name)) for f in fields(current)}
            if len(_schemas[cls][0]) != len(fields(current)):
                # A metadata-only schema (LayerSnapshot excludes Cell storage)
                # cannot cache a full dataclass encoding under that token.
                node = None
        elif isinstance(current, tuple) and hasattr(current, '_fields'):
            result = cls(*(visit(child) for child in current))
        elif cls is tuple:
            result = tuple(visit(child) for child in current)
        elif cls in (list, OwnedList) or cls in _container_types:
            result = [visit(child) for child in current]
        elif cls in (dict, OwnedDict):
            result = {visit(key): visit(child) for key, child in current.items()}
        elif isinstance(current, (list, tuple)):
            result = cls(visit(child) for child in current)
        elif isinstance(current, dict):
            result = cls((visit(key), visit(child)) for key, child in current.items())
        else:
            # Authored container/deepcopy policies retain the original behavior.
            return deepcopy(current)
        if node is not None and node.asdict_safe:
            node.cache = result if shared else deepcopy(result)
            node.cache_version = node.version
            node.cache_mode = 'asdict'
        return result
    result = visit(value)
    return deepcopy(result, _AsdictMemo()) if shared and not _borrow else result


def _layer_copy_safe(node):
    return all(node.children.get(name) is None or node.children[name].copy_safe
               for name in _COPY_FIELDS)


def detached_copy(value, *, _borrow=False):
    """Keep original deepcopy policies; cache only pure observable containers."""
    node, supported = _child(value, set())
    safe = supported and node is not None and node.copy_safe
    if safe and node.cache_version == node.version and node.cache_mode == 'copy':
        return node.cache if _borrow else deepcopy(node.cache)
    result = deepcopy(value)
    if safe:
        node.cache = result if _borrow else deepcopy(result)
        node.cache_version = node.version
        node.cache_mode = 'copy'
    return result


def layer_metadata(snapshot, asdict):
    """Encode a built-in LayerSnapshot's metadata, excluding material storage.

    None requests the original complete layer encoder for authored policies.
    Private metadata nodes reuse one cached result; live external plain aliases
    are serialized conservatively on every call.
    """
    schema = _schemas.get(type(snapshot))
    if type(snapshot) not in _layer_types or not _policies_valid():
        return None
    node = _observe(snapshot)
    safe = node.safe and _layer_copy_safe(node)
    if safe and node.cache_version == node.version and node.cache_mode == 'layer':
        return _detach_layer(node.cache)
    result = {}
    for definition in fields(snapshot):
        name = definition.name
        if name == 'cells':
            continue
        value = getattr(snapshot, name)
        if name == 'logic_scenarios':
            result[name] = {key: str(child) for key, child in value.items()}
        elif name == 'logic_valves':
            result[name] = {key: deepcopy(list(child)) for key, child in value.items()}
        elif name in _COPY_FIELDS:
            result[name] = detached_copy(value, _borrow=safe)
        elif name in ('enemies', 'world_items', 'events'):
            if type(value) in (list, OwnedList) or type(value) in _container_types:
                result[name] = encode(value, asdict, _policies=True, _borrow=safe)
            else:
                # The save schema always has lists here, even if an authored
                # caller supplied a tuple or custom iterable container.
                result[name] = [encode(child, asdict, _policies=True) for child in value]
        else:
            result[name] = encode(value, asdict, _policies=True, _borrow=safe)
    if safe:
        node.cache = result
        node.cache_version = node.version
        node.cache_mode = 'layer'
    return _detach_layer(result) if safe else result
