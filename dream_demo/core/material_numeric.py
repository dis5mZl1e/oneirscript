"""Opt-in authoritative-array flow/boiling and legacy allocator fallback.

Rows retain source/proposal order. Levels are the legacy *source snapshot*, not
the live liquid/gas quantity: missing sources deliberately have level zero.
Authored heterogeneous/stock rules and dynamic barriers retain exact fallbacks.
"""
from array import array
from functools import wraps
from threading import local

from ..env_compat import flag
from .entities import Cell, _bound_cell_type

_BASE_OWNED_CELL = _bound_cell_type(Cell)
_boundary_cadence = local()


def owned_boundary_cadence(function):
    """Sample native boundary options at each complete cadence's entry.

    Environment changes during callbacks apply on the next cadence. Store
    identity, sparse exceptions and native function availability remain live.
    Thread-local frames never become state/save/deepcopy data; nested calls
    sample their own options and restore the suspended caller even on failure.
    """
    @wraps(function)
    def scoped(state, *args, **kwargs):
        previous = getattr(_boundary_cadence, 'frame', None)
        frame = (state, getattr(state.cells, 'store', None),
                 flag('MATERIAL_NUMERIC_KERNEL', False), flag('MATERIAL_GRID', False))
        _boundary_cadence.frame = frame
        try:
            return function(state, *args, **kwargs)
        finally:
            if previous is None:
                del _boundary_cadence.frame
            else:
                _boundary_cadence.frame = previous
    return scoped


def cadence_grid_enabled(state):
    frame = getattr(_boundary_cadence, 'frame', None)
    if frame is not None and frame[0] is state:
        return frame[3]
    return flag('MATERIAL_GRID', False)

try:
    from ._material_numeric import allocate as _allocate_native
except ImportError:
    _allocate_native = None

try:
    from ._material_numeric import (prime_owned_clocks as _prime_owned_clocks,
                                  project_owned_position as _project_owned_position,
                                  sync_owned_grid as _sync_owned_grid)
except ImportError:
    _prime_owned_clocks = _project_owned_position = _sync_owned_grid = None


def _owned_boundary_enabled(store):
    if _allocate_native is None or store is None or store.exceptions:
        return False
    frame = getattr(_boundary_cadence, 'frame', None)
    if frame is not None and frame[1] is store:
        return frame[2] and frame[3]
    return flag('MATERIAL_NUMERIC_KERNEL', False) and flag('MATERIAL_GRID', False)


def try_prime_owned(state, cell, context):
    if _prime_owned_clocks is None:
        return False
    # Only the generated base Cell has an established column-equivalent read
    # contract. Authored subclasses may override reads, including __dict__ or
    # clock access; let the original Python body observe those policies.
    if type(cell) is not _BASE_OWNED_CELL:
        return False
    binding = cell.__dict__.get('_material_binding')
    if binding is None:
        return False
    store, position = binding
    if store is not getattr(state.cells, 'store', None) or not _owned_boundary_enabled(store):
        return False
    _prime_owned_clocks(state, store, position, context)
    return True


def try_project_owned(state, x, y, store, context):
    if (_project_owned_position is None or not _owned_boundary_enabled(store)
            or store is not getattr(state.cells, 'store', None)
            or type(x) is not int or type(y) is not int
            or not 0 <= x < state.width or not 0 <= y < state.height):
        return False
    _project_owned_position(state, x, y, store, context)
    return True


def try_sync_owned(mirror, position, context):
    if _sync_owned_grid is None or not _owned_boundary_enabled(mirror.store):
        return False
    _sync_owned_grid(mirror, position, context)
    return True


def enabled(mirror):
    if mirror is None:
        return False
    frame = getattr(_boundary_cadence, 'frame', None)
    if frame is not None and frame[1] is not None and frame[1] is getattr(mirror, 'store', None):
        return frame[2]
    return flag('MATERIAL_NUMERIC_KERNEL', False)


def _pack(rows):
    # Each row: source index, budget, equalize, target count, four target indices.
    return array('q', (value for source, budget, equalize, targets in rows
                      for value in (source, budget, int(equalize), len(targets),
                                    *targets, *([0] * (4 - len(targets))))))


def _allocate_python(levels, packed):
    reserved = [0] * len(levels)
    output = array('q', [0]) * (len(packed) // 8 * 4)
    for row in range(len(packed) // 8):
        offset = row * 8
        source, budget, equalize, count = packed[offset:offset + 4]
        targets = packed[offset + 4:offset + 4 + count]
        current = [levels[t] + reserved[t] for t in targets]
        remaining = levels[source]
        while budget > 0 and remaining > 0:
            chosen = -1
            for i, level in enumerate(current):
                if level >= 100 or (equalize and remaining - level < 2):
                    continue
                if chosen < 0 or level < current[chosen]:
                    chosen = i
            if chosen < 0:
                break
            current[chosen] += 1
            output[row * 4 + chosen] += 1
            remaining -= 1
            budget -= 1
        for i, target in enumerate(targets):
            reserved[target] += output[row * 4 + i]
    return output


def _distribute(levels, rows, allocator):
    packed = _pack(rows)
    result = allocator(levels, packed)
    return [[(target, result[r * 4 + i]) for i, target in enumerate(targets)
             if result[r * 4 + i] > 0]
            for r, (_, _, _, targets) in enumerate(rows)]


def distribute_python(levels, rows):
    return _distribute(levels, rows, _allocate_python)


def proposals(mirror, amounts, prepared, canonical=False):
    """Bridge ordered Cell-rule rows to contiguous numeric buffers once per pass."""
    if not prepared:
        return []
    width = mirror.width
    levels = array('q', [0]) * (width * mirror.rows)
    for (x, y), amount in amounts.items():
        levels[y * width + x] = amount
    rows = [(y * width + x, budget, equalize,
             [ny * width + nx for nx, ny in (sorted(targets) if canonical else targets)])
            for x, y, kind, targets, budget, equalize in prepared]
    plans = _distribute(levels, rows, _allocate_native or _allocate_python)
    return [((x, y), (target % width, target // width), kind, amount)
            for (x, y, kind, _, _, _), plan in zip(prepared, plans)
            for target, amount in plan]


def run_array_pass(state, mirror, channel):
    """Dispatch the complete array pass, or preserve the exact dynamic fallback."""
    if _allocate_native is None:
        return False, None
    try:
        from ._material_numeric import flow_pass
    except ImportError:
        return False, None
    if mirror.store is None or mirror.store.exceptions:
        return False, None
    if type(state.time) is not int or not -(1 << 62) <= state.time < (1 << 62):
        return None, None
    from .expansion_abilities import liquid_pinned_cells
    from .realm_challenges import sealed_gas_cells
    if channel == 'liquid':
        from ..equipment.remaining_gear import liquid_edge_index
        barriers = liquid_edge_index(state)
        if barriers is None or barriers:
            return False, None
    sealed = sealed_gas_cells(state) if channel == 'gas' else ()
    pinned = liquid_pinned_cells(state)
    positions = getattr(state, '_'+channel+'_pass_cells')()
    # Rules depend on the small material registry, not map size. Rebuilding this
    # table also honors authored/modded definitions changed between passes.
    from ..materials import LIQUID_DEFINITIONS, GAS_DEFINITIONS
    from ..materials.floors import FLOOR_DEFINITIONS, PLAIN_FLOOR
    from ..materials.plants import plant_gas_flow_divisor
    definitions = LIQUID_DEFINITIONS if channel == 'liquid' else GAS_DEFINITIONS
    deferred = getattr(state, '_deferred_'+channel+'_sources', ()) or ()
    for x, y, amount, name in deferred:
        if (type(x) is not int or type(y) is not int or type(amount) is not int
                or not 0 <= amount <= 255 or name not in definitions):
            # Exact reference arithmetic also bypasses the legacy int64
            # allocator: deferred snapshots are unrestricted Python values.
            return None, None
        mirror.intern(name)
    maximum, periods, bonuses, divisors, thresholds, gas_divisors, plant_divisors = _flow_rules(mirror, channel)
    result = flow_pass(state, mirror, channel == 'gas', positions, deferred,
                       sealed, pinned, state._material_awake_filter(channel),
                       maximum, periods, bonuses, divisors, thresholds, gas_divisors,
                       plant_divisors)
    return True, result


def run_array_phase(state, mirror, candidates):
    """Native phase decisions/deposits with exact tracked stock and callbacks."""
    if _allocate_native is None or mirror.store is None or mirror.store.exceptions:
        return False
    try:
        from ._material_numeric import phase_pass
    except ImportError:
        return False
    from . import phase_changes as phase
    from .tamper_protection import liquid_reason
    for name in (*phase.VAPOR.values(), '灼热聚合物', '灼热蒸汽', '熔念金属', '冰面'):
        mirror.intern(name)
    vapor = array('q', [0])*len(mirror.names)
    special = bytearray(len(mirror.names))
    for i, name in enumerate(mirror.names):
        if name in phase.VAPOR and not liquid_reason(name):
            vapor[i] = mirror._ids[phase.VAPOR[name]]
        if name in phase.CONDENSATE or name in phase.FREEZE_BY_LIQUID or name in phase.WAX:
            special[i] = 1
    phase_pass(state, mirror, sorted(candidates), vapor, special)
    return True


def _flow_rules(mirror, channel):
    """Reuse integer rules until interned names or immutable registry entries change.

    Material definitions are frozen dataclasses. Snapshotting mapping entries
    observes replacement, addition and removal without full-map reads.
    """
    from ..materials import LIQUID_DEFINITIONS, GAS_DEFINITIONS
    from ..materials.floors import FLOOR_DEFINITIONS, PLAIN_FLOOR
    from ..materials.plants import _PLANT_BY_CODE, PLANT_SHORT, plant_def_for, plant_gas_flow_divisor
    definitions = LIQUID_DEFINITIONS if channel == 'liquid' else GAS_DEFINITIONS
    key = (tuple(mirror.names), tuple(definitions.items()),
           tuple(LIQUID_DEFINITIONS.items()), tuple(FLOOR_DEFINITIONS.items()), PLAIN_FLOOR,
           tuple(_PLANT_BY_CODE.items()), PLANT_SHORT, plant_def_for, plant_gas_flow_divisor)
    cache = getattr(mirror, '_flow_rule_cache', None)
    if cache is None:
        cache = mirror._flow_rule_cache = {}
    previous = cache.get(channel)
    if previous is not None and previous[0] == key:
        return previous[1]
    names = mirror.names
    maximum = array('q', [0]) * len(names)
    periods = array('q', [1]) * len(names)
    bonuses = array('q', [1]) * len(names)
    divisors = array('q', [1]) * len(names)
    thresholds = array('q', [0]) * len(names)
    gas_divisors = array('q', [0]) * len(names)
    for i, name in enumerate(names):
        definition = definitions.get(name)
        if definition is not None:
            maximum[i] = definition.max_flow if channel == 'liquid' else definition.max_diffusion
            if channel == 'liquid':
                periods[i] = max(1, definition.flow_period)
        floor = FLOOR_DEFINITIONS.get(name, PLAIN_FLOOR)
        bonuses[i], divisors[i] = 1+floor.flow_bonus, max(1, floor.flow_divisor)
        liquid = LIQUID_DEFINITIONS.get(name)
        if liquid is not None:
            thresholds[i] = liquid.gas_flow_threshold
            gas_divisors[i] = max(1, liquid.gas_flow_divisor)
    plant_divisors = array('q', (plant_gas_flow_divisor(i) for i in range(256)))
    rules = maximum, periods, bonuses, divisors, thresholds, gas_divisors, plant_divisors
    cache[channel] = key, rules
    return rules

# Keep optional full stages independent of older installed extension versions.
try:
    from ._material_numeric import (recipe_owned_stage as _recipe_owned_stage,
                                   special_owned_stage as _special_owned_stage)
except ImportError:
    _recipe_owned_stage = _special_owned_stage = None


def try_rule_stage_owned(state, stage):
    """Run the entire ordered rule loop over the owning array columns.

    Authored Cell getters and initially exceptional values keep the Python
    reference path. Native reads also check exceptions live: callbacks can
    introduce exact values outside the compact columns during the stage.
    """
    function = _recipe_owned_stage if stage == 'recipe' else _special_owned_stage
    store = getattr(state.cells, 'store', None)
    if (function is None or not _owned_boundary_enabled(store)
            or store._authored_positions):
        return False
    function(state)
    return True

try:
    from ._material_numeric import (ensure_owned_index as _ensure_owned_index,
                                   sync_owned_position as _sync_owned_position)
except ImportError:
    _ensure_owned_index = _sync_owned_position = None

# Preserve live monkeypatch/override hooks while allowing native helpers to fuse
# ordinary calls. Only exact original functions are eligible for internal calls.
_boundary_methods = {}
_boundary_dispatch = {}
_boundary_kernels = (_prime_owned_clocks, _project_owned_position, _sync_owned_grid)


def register_owned_boundary_methods(cls):
    _boundary_methods.update((name, getattr(cls, name)) for name in (
        '_ensure_material_index', '_sync_material_position',
        '_prime_material_clocks', '_project_material_arrays'))
    _boundary_dispatch['sync'] = try_sync_position_owned


def _fused_boundary_store(state):
    store = getattr(state.cells, 'store', None)
    if (not _owned_boundary_enabled(store) or store._authored_positions
            or (_prime_owned_clocks, _project_owned_position, _sync_owned_grid) != _boundary_kernels):
        return None
    for name, function in _boundary_methods.items():
        if getattr(getattr(state, name), '__func__', None) is not function:
            return None
    return store


def try_ensure_index_owned(state, context):
    if _ensure_owned_index is None:
        return False
    store = _fused_boundary_store(state)
    return store is not None and _ensure_owned_index(state, store, context)


def try_sync_position_owned(state, x, y, prime, index_current, context):
    if _sync_owned_position is None:
        return False
    store = _fused_boundary_store(state)
    if (store is None or type(x) is not int or type(y) is not int
            or not 0 <= x < state.width or not 0 <= y < state.height):
        return False
    return _sync_owned_position(state, x, y, store, prime, index_current, context)
