"""Journal-versioned Cell encodings with per-save string-table remapping."""
from copy import deepcopy
from enum import Enum

from .material_store import MaterialRows, TrackedDict, TrackedList


_TABLE_FIELDS = ((0, 'floors'), (9, 'variants'), (10, 'walls'),
                 (13, 'liquids'), (14, 'gases'))


def _tracked_graph(value, seen):
    if value is None or type(value) in (bool, int, float, str, bytes) or isinstance(value, Enum):
        return True
    if id(value) in seen:
        return True
    seen.add(id(value))
    if isinstance(value, TrackedDict):
        return all(_tracked_graph(k, seen) and _tracked_graph(v, seen)
                   for k, v in value.items())
    if isinstance(value, (TrackedList, tuple)):
        return all(_tracked_graph(v, seen) for v in value)
    return False


class _Encoding:
    def __init__(self, manager, size):
        self.tables = manager._make_tables()
        self.max_names = sum(map(len, self.tables.values())) + max(128, 2 * size)
        self.intern = {}
        self.cells = []
        self.cursor = None
        self.skipped_cursor = None
        self.supported = True


def encode_owned(rows, tables, intern, manager):
    """Return None for legacy/unsupported graphs; never reuse mutable outputs."""
    if not isinstance(rows, MaterialRows) or rows.store.exceptions:
        return None
    store = rows.store
    # Authored getters can depend on another position or external policy; a
    # journal coordinate does not describe their complete save dependencies.
    if store._authored_positions:
        return None
    previous = getattr(store, '_save_encoding', None)
    if previous is not None:
        cursor = previous.skipped_cursor or previous.cursor
        current = store.journal.cursor
        # A conservative record-count gate avoids sorting a large journal
        # merely to decide to read the whole map. It may choose a full read
        # for many writes to a single Cell; correctness is independent of it.
        if (cursor is not None and cursor[0] == current[0]
                and current[1] - cursor[1] > max(32, store.width * store.height // 4)):
            previous.skipped_cursor = current
            return None
    batch = store.journal.changes_since(
        (previous.skipped_cursor or previous.cursor) if previous else None)
    # Dense changes need the ordinary full encoder anyway. Avoid building a
    # duplicate retained representation every active frame; rebuild lazily
    # when this map next becomes mostly stable.
    if previous is not None and (batch.reset or len(batch.positions) > max(8, store.width * store.height // 4)):
        previous.skipped_cursor = batch.cursor
        return None
    if (previous is None or batch.reset or not previous.supported
            or previous.skipped_cursor is not None
            or sum(map(len, previous.tables.values())) > previous.max_names):
        encoding = _Encoding(manager, store.width * store.height)
        positions = range(store.width * store.height)
        encoding.cells = [None] * (store.width * store.height)
    else:
        encoding = previous
        positions = batch.positions
    replacements = {}
    for position in positions:
        # Numeric exceptions fall back above. Other mutable types have no
        # journal ownership hooks; preserve their ordinary full-read semantics.
        if not all(_tracked_graph(store.columns[name][position], set())
                   for name in store.field_names if name not in store.numeric_fields):
            encoding.supported = False
            store._save_encoding = encoding
            return None
        y, x = divmod(position, store.width)
        replacements[position] = deepcopy(manager._encode_cell(
            rows[y][x], encoding.tables, encoding.intern))
    for position, value in replacements.items():
        encoding.cells[position] = value
    encoding.cursor = batch.cursor
    store._save_encoding = encoding
    result = []
    for y in range(store.height):
        row = []
        for x in range(store.width):
            cached = encoding.cells[y * store.width + x]
            # The fixed numeric prefix is immutable. Optional stock/clock and
            # creation tails must be detached from both source and cache.
            cell = cached[:20]
            if len(cached) > 20:
                cell.extend(deepcopy(cached[20:]))
            for offset, name in _TABLE_FIELDS:
                cell[offset] = manager._intern(tables, name,
                    encoding.tables[name][cached[offset]], intern)
            row.append(cell)
        result.append(row)
    return result
