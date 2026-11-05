"""Reviewed material dependencies for visibility and live path preparation.

These keys describe terrain only. Time, capabilities, occupancy, knowledge and
arbitrary callbacks remain the responsibility of their existing callers.
"""

from .entities import Cell, _bound_cell_type
from .material_store import CellField, MaterialStore

_PLAIN_OWNED_CELL = _bound_cell_type(Cell)
_PATH_DESCRIPTORS = tuple((name, _PLAIN_OWNED_CELL.__dict__[name])
                          for name in ('solid', 'wall_kind'))
_CELL_FIELD_GET = CellField.__get__
_STORE_READ = MaterialStore.read
_STORE_NAMESPACE = MaterialStore.__dict__
_FIELD_NAMESPACE = CellField.__dict__
_CELL_NAMESPACE = Cell.__dict__
_OWNED_NAMESPACE = _PLAIN_OWNED_CELL.__dict__
_STORE_MRO = MaterialStore.__mro__
_FIELD_MRO = CellField.__mro__
_OWNED_MRO = _PLAIN_OWNED_CELL.__mro__


def _plain_read_policy(store, descriptors=_PATH_DESCRIPTORS):
    """A cached fact is valid only while its original reads stay ordinary."""
    if (type(store) is not MaterialStore
            or MaterialStore.__mro__ is not _STORE_MRO
            or CellField.__mro__ is not _FIELD_MRO
            or _PLAIN_OWNED_CELL.__mro__ is not _OWNED_MRO
            or _STORE_NAMESPACE.get('__getattribute__', object.__getattribute__) is not object.__getattribute__
            or _STORE_NAMESPACE.get('read') is not _STORE_READ
            or 'read' in store.__dict__
            or _OWNED_NAMESPACE.get('__getattribute__',
                                   _CELL_NAMESPACE.get('__getattribute__', object.__getattribute__)) is not object.__getattribute__
            or _FIELD_NAMESPACE.get('__getattribute__', object.__getattribute__) is not object.__getattribute__
            or _FIELD_NAMESPACE.get('__get__') is not _CELL_FIELD_GET
            or 'name' in _FIELD_NAMESPACE):
        return False
    for name, descriptor in descriptors:
        if _OWNED_NAMESPACE.get(name) is not descriptor or type(descriptor) is not CellField:
            return False
        field_name = descriptor.__dict__.get('name')
        if type(field_name) is not str or field_name != name:
            return False
    return True

# sight obstruction/smoke; glow source radius/catalog; floor/radius modifiers.
VISION_FIELDS = (
    'solid', 'wall_kind', 'height', 'plant', 'gas', 'gas_kind',
    'light_on', 'light_radius', 'liquid', 'liquid_kind', 'flame',
    'floor', 'aggregate_variant',
)
PATH_TERRAIN_FIELDS = ('solid', 'wall_kind')
_VISION_DESCRIPTORS = tuple((name, _PLAIN_OWNED_CELL.__dict__[name])
                            for name in VISION_FIELDS)


def material_dependency_cursor(state, fields):
    store = getattr(state.cells, 'store', None)
    if store is None:
        return None
    if not _plain_read_policy(store, _VISION_DESCRIPTORS):
        # Unversioned descriptor policies can depend on external mutable data.
        # A fresh token declines both sight and glow reuse without reading them.
        return object()
    # Custom Cell getters may derive gas/light/solid from clocks or any other
    # field. Preserve the previous whole-journal invalidation for such maps.
    if store._authored_positions:
        return store.journal.cursor
    return store.journal.dependency_cursor(fields)


def prepare_live_path_terrain(state):
    """Lazily reuse plain Cell facts, never knowledge or callback decisions.

    Entries are overwritten on demand after a revision. Invalidating costs O(1)
    and does not walk/clear the map; the cache holds at most one entry per cell.
    The journal/store is runtime-only, so this adds no GameState save fields.
    """
    store = getattr(state.cells, 'store', None)
    if store is None or not _plain_read_policy(store):
        return None
    plain_owned_type = _PLAIN_OWNED_CELL
    journal = store.journal
    key = journal.dependency_cursor(PATH_TERRAIN_FIELDS)
    observed_version = journal.version
    cache = getattr(journal, '_path_terrain_cache', None)
    if cache is None:
        cache = journal._path_terrain_cache = {}
    cells = state.cells

    def read(x, y):
        nonlocal key, observed_version
        # Decline before even reading cache-only store attributes: an authored
        # access policy can make width/version reads observable or exceptional.
        if not _plain_read_policy(store):
            return None
        # Ability callbacks still run at their original point and may write
        # terrain during a search. Refresh before trusting a cross-query hit.
        if journal.version != observed_version:
            key = journal.dependency_cursor(PATH_TERRAIN_FIELDS)
            observed_version = journal.version
        position = y * store.width + x
        cell = cells[y][x]
        # Check the actual type even on a cache hit. A caller may directly
        # install an authored policy on a formerly ordinary owned instance.
        if type(cell) is not plain_owned_type:
            return None
        hit = cache.get(position)
        if hit is not None and hit[0] == key:
            return hit[1]
        # Authored accessors may depend on external mutable policy. Always ask
        # those original getters; material versions cannot describe that policy.
        values = cell.solid, cell.wall_kind
        cache[position] = key, values
        return values

    return read
