# cython: language_level=3, boundscheck=False, wraparound=False
"""P5 pure numeric allocator: no Cell access, Python rules or RNG in hot loop."""
from array import array
from weakref import ref as _recipe_weakref
from libc.string cimport memset
from libc.stdint cimport uint64_t, uintptr_t
from cpython.ref cimport PyObject


cdef extern from *:
    """
    static uint64_t oneir_recipe_dict_version(PyObject *value) {
    #if PY_VERSION_HEX >= 0x030B0000 && PY_VERSION_HEX < 0x030C0000 && !defined(PYPY_VERSION)
        return ((PyDictObject *)value)->ma_version_tag;
    #else
        return 0;
    #endif
    }
    """
    uint64_t oneir_recipe_dict_version(object value)


cdef uintptr_t _pair_registry_identity = 0
cdef uint64_t _pair_version = 0
cdef dict _pair_names = {}
cdef list _pair_values = []
cdef Py_ssize_t _pair_width = 0
cdef bint _pair_safe = False


cdef void _prepare_recipe_pairs(dict registry, uint64_t version) except *:
    global _pair_registry_identity, _pair_version, _pair_names, _pair_values, _pair_width, _pair_safe
    cdef dict names = {}
    cdef object key, name, value, members
    cdef Py_ssize_t left, right, width
    # A dictionary cannot be weak-referenced. Retain its numeric identity and
    # globally unique live dict version, never the registry itself. The pointer
    # is only compared; no borrowed address is subsequently dereferenced.
    _pair_registry_identity, _pair_version = <uintptr_t><PyObject*>registry, version
    _pair_safe = False
    _pair_names, _pair_values, _pair_width = {}, [], 0
    # Decline authored keys before performing any authored hash/equality work.
    # Bound the dense table for large extension registries.
    for key in registry:
        if type(key) is not frozenset or not 1 <= len(key) <= 2:
            return
        for name in key:
            if type(name) is not str:
                return
            if name not in names:
                names[name] = len(names)
                if len(names) > 64:
                    return
    width = len(names)
    values = [None] * (width * width)
    for key, value in registry.items():
        try:
            value = _recipe_weakref(value)
        except TypeError:
            # Authored non-weakrefable values must not be retained by a rule
            # cache after the registry releases its last owning reference.
            return
        members = tuple(key)
        left, right = names[members[0]], names[members[len(members) - 1]]
        values[left * width + right] = value
        values[right * width + left] = value
    _pair_names, _pair_values, _pair_width = names, values, width
    _pair_safe = True


cdef object _lookup_recipe_pair(object registry, object left, object right):
    cdef uint64_t version
    cdef Py_ssize_t a, b
    if type(registry) is dict and type(left) is str and type(right) is str:
        version = oneir_recipe_dict_version(registry)
        if version:
            if (<uintptr_t><PyObject*>registry != _pair_registry_identity
                    or version != _pair_version):
                _prepare_recipe_pairs(registry, version)
            if _pair_safe:
                a = _pair_names.get(left, -1)
                b = _pair_names.get(right, -1)
                if a < 0 or b < 0:
                    return None
                result = _pair_values[a * _pair_width + b]
                return None if result is None else result()
    getter = registry.get
    return getter(frozenset((left, right)))


def recipe_pair_lookup(registry, left, right):
    """Diagnostic entry to the same guarded integer table used by the stage."""
    return _lookup_recipe_pair(registry, left, right)


cdef dict _recipe_mechanisms = {
    'wall_melt': 1, 'wall_bust_gas': 2, 'wall_shatter': 3,
    'freeze_wall': 4, 'freeze_floor': 5, 'wall_to_liquid': 6,
    'wall_flush': 7, 'wall_retype': 8, 'floor_revert': 9,
    'floor_pulp': 10, 'gas_etch': 11,
}


cdef inline int _recipe_mechanism_code(object mechanism) except -2:
    # Authored str subclasses retain their original ordered equality callbacks.
    if type(mechanism) is not str:
        return -1
    return _recipe_mechanisms.get(mechanism, 0)


cdef object _scratch(dict buffers, str name, str code, Py_ssize_t size):
    cdef object result = buffers.get(name)
    if result is None or len(result) < size:
        result = array(code, [0]) * size
        buffers[name] = result
    return result

def allocate(const long long[::1] levels, const long long[::1] rows):
    cdef Py_ssize_t n = rows.shape[0] // 8
    cdef object result = array('q', [0]) * (n * 4)
    cdef object reservation = array('q', [0]) * levels.shape[0]
    cdef long long[::1] output = result
    cdef long long[::1] reserved = reservation
    cdef long long current[4]
    cdef Py_ssize_t r, offset, count, i, chosen, target
    cdef long long remaining, budget, equalize
    if rows.shape[0] % 8:
        raise ValueError('invalid numeric row stride')
    for i in range(levels.shape[0]):
        if levels[i] < 0 or levels[i] > 2147483647:
            raise ValueError('invalid numeric level')
    for r in range(n):
        offset = r * 8
        if rows[offset] < 0 or rows[offset] >= levels.shape[0]:
            raise ValueError('invalid source index')
        count = rows[offset + 3]
        if count < 0 or count > 4 or rows[offset + 1] < 0:
            raise ValueError('invalid numeric budget or target count')
        for i in range(count):
            target = rows[offset + 4 + i]
            if target < 0 or target >= levels.shape[0]:
                raise ValueError('invalid target index')
    with nogil:
        for r in range(n):
            offset = r * 8
            remaining = levels[rows[offset]]
            budget = rows[offset + 1]
            equalize = rows[offset + 2]
            count = rows[offset + 3]
            for i in range(count):
                target = rows[offset + 4 + i]
                current[i] = levels[target] + reserved[target]
            while budget > 0 and remaining > 0:
                chosen = -1
                for i in range(count):
                    if current[i] >= 100 or (equalize and remaining - current[i] < 2):
                        continue
                    if chosen < 0 or current[i] < current[chosen]:
                        chosen = i
                if chosen < 0:
                    break
                current[chosen] += 1
                output[r * 4 + chosen] += 1
                remaining -= 1
                budget -= 1
            for i in range(count):
                reserved[rows[offset + 4 + i]] += output[r * 4 + i]
    return result


def flow_pass(state, mirror, bint gas_channel, positions, deferred,
              sealed, pinned, bint awake,
              const long long[::1] maximum, const long long[::1] periods,
              const long long[::1] bonuses, const long long[::1] divisors,
              const long long[::1] thresholds, const long long[::1] gas_divisors,
              const long long[::1] plant_divisors):
    """Ordered candidate/neighbor/allocation/settlement directly over owned arrays.

    Only heterogeneous arrivals enter the authored Python mixing rules. Deferred
    tuples are the public queue format; source rows and proposal dicts are never
    packed in Python. Slow material clocks keep their original nested owners.
    """
    from .entities import Material
    from ..materials.plants import plant_survives_liquid
    cdef Py_ssize_t width = mirror.width, height = mirror.rows, size = width*height
    cdef Py_ssize_t capacity = len(positions)+len(deferred), nc = 0, ns, i, j, k, p, q, x, y, nx, ny
    cdef Py_ssize_t count, lowers, rotation, selected, target, event_count = 0, e, cursor
    cdef long long amount, kind, budget, remaining, best, transfer, total, old_amount, result_kind
    cdef long long now = state.time, period, source_flag, pass_flag, minimum
    cdef long long cloud = mirror._ids.get('云块', -1)
    cdef bint lower, found_mark, homogeneous, canonical = getattr(state, '_material_canonical_on', False)
    cdef Py_ssize_t neighbors[4]
    cdef Py_ssize_t ordered[4]
    cdef long long current[4]
    cdef long long planned[4]
    cdef dict scratch = getattr(mirror, '_flow_scratch', None)
    if scratch is None:
        scratch = {}
        mirror._flow_scratch = scratch
    cdef object source_storage = _scratch(scratch, 'sources', 'q', max(size*3, capacity*3))
    cdef long long[::1] sources = source_storage
    cdef object levels_storage = _scratch(scratch, 'levels', 'q', size)
    cdef object reserved_storage = _scratch(scratch, 'reserved', 'q', size)
    cdef object outgoing_storage = _scratch(scratch, 'outgoing', 'q', size)
    cdef object heads_storage = _scratch(scratch, 'heads', 'q', size)
    cdef object tails_storage = _scratch(scratch, 'tails', 'q', size)
    cdef object results_storage = _scratch(scratch, 'results', 'q', size*3)
    cdef long long[::1] levels = levels_storage, reserved = reserved_storage, outgoing = outgoing_storage
    cdef long long[::1] heads = heads_storage, tails = tails_storage, results = results_storage
    cdef object event_storage = _scratch(scratch, 'events', 'q', max(size*16, capacity*16))
    cdef list event_marks = [None]*(capacity*4) if gas_channel else None
    cdef list result_marks = [None]*size if gas_channel else None
    cdef long long[::1] events = event_storage
    cdef object mask_storage = _scratch(scratch, 'mask', 'B', size)
    cdef unsigned char[::1] mask = mask_storage
    cdef unsigned char[::1] values = mirror.gas if gas_channel else mirror.liquid
    cdef const unsigned char[::1] flags = mirror.flags
    cdef const unsigned char[::1] liquid_values = mirror.liquid
    cdef const unsigned char[::1] plants = mirror.plant
    cdef const unsigned char[::1] solid = mirror.solid
    cdef const short[::1] elevation = mirror.elevation
    cdef const unsigned short[::1] ids = mirror.gas_id if gas_channel else mirror.liquid_id
    cdef const unsigned short[::1] liquid_ids = mirror.liquid_id
    cdef const unsigned short[::1] walls = mirror.wall_id
    cdef const unsigned short[::1] variants = mirror.variant_id
    cdef object store = mirror.store
    cdef list clocks = store.columns['material_clocks']
    cdef list floors = store.columns['floor']
    cdef list kinds = store.columns['gas_kind' if gas_channel else 'liquid_kind']
    cdef object channel = 'gas' if gas_channel else 'liquid'
    cdef object names = mirror.names
    cdef object deferred_output = []
    cdef object changed, source_order = [], target_order = []
    cdef object arrivals, totals, name, clock_key, cell, position, result, mark, deferred_x, deferred_y
    cdef object exposed = set()
    source_flag = 32 if gas_channel else 16
    pass_flag = 8 if gas_channel else 4
    minimum = 4 if gas_channel else 8
    if size:
        # Fixed-size buffers belong to this map and are never shared by readers.
        # Native memory clearing avoids repeated whole-map Python allocations.
        memset(&levels[0], 0, size*sizeof(long long))
        memset(&reserved[0], 0, size*sizeof(long long))
        memset(&outgoing[0], 0, size*sizeof(long long))
        memset(&heads[0], 255, size*sizeof(long long))
        memset(&mask[0], 0, size)
    # Only sparse exceptional membership is converted to a byte mask.
    for x, y in sealed:
        if 0 <= x < width and 0 <= y < height:
            mask[y*width+x] |= 1
    for x, y in pinned:
        if 0 <= x < width and 0 <= y < height:
            mask[y*width+x] |= 2
    # Preserve queue prefix, duplicate entries and source snapshot quantities.
    for deferred_x, deferred_y, amount, name in deferred:
        # Stale out-of-map deferred records still occupy budget slots.
        # Compare unrestricted Python coordinates before narrowing to ssize_t.
        sources[nc*3] = deferred_y*width+deferred_x if 0 <= deferred_x < width and 0 <= deferred_y < height else -1
        sources[nc*3+1], sources[nc*3+2] = amount, mirror._ids[name]
        nc += 1
    for x, y in positions:
        if 0 <= x < width and 0 <= y < height:
            p = y*width+x
            if flags[p] & source_flag:
                sources[nc*3], sources[nc*3+1], sources[nc*3+2] = p, values[p], ids[p]
                nc += 1
    ns = min(nc, state.SIM_SOURCE_BUDGET)
    # Keep original stale coordinates exactly in deferred remainder.
    for i in range(ns, nc):
        if i < len(deferred):
            deferred_output.append(deferred[i])
        else:
            p = sources[i*3]
            deferred_output.append((p % width, p // width, sources[i*3+1], names[sources[i*3+2]]))
    setattr(state, '_deferred_'+channel+'_sources', deferred_output)
    for i in range(ns):
        p = sources[i*3]
        if p < 0:
            continue
        x, y = p % width, p // width
        if 0 < x < width-1 and 0 < y < height-1 and not (gas_channel and mask[p] & 1):
            levels[p] = sources[i*3+1]
            mask[p] |= 4
    for i in range(ns):
        p, amount, kind = sources[i*3], sources[i*3+1], sources[i*3+2]
        if p < 0:
            continue
        x, y = p % width, p // width
        if not (0 < x < width-1 and 0 < y < height-1) or mask[p] & 2 or (gas_channel and mask[p] & 1):
            continue
        period = periods[kind]
        if not gas_channel and period > 1:
            clock_key = 'flow:'+names[kind]
            if now-clocks[p].get(clock_key, 0) < period:
                continue
        neighbors[0], neighbors[1], neighbors[2], neighbors[3] = p+1, p-1, p+width, p-width
        count, lowers = 0, 0
        for j in range(4):
            q = neighbors[j]
            if not (flags[q] & pass_flag):
                continue
            if gas_channel:
                if mask[q] & 1 or values[q] >= amount:
                    continue
            elif walls[q] == cloud:
                continue
            ordered[count] = q
            count += 1
            if not gas_channel and elevation[q] < elevation[p]:
                lowers += 1
        selected = 0
        for j in range(count):
            q = ordered[j]
            if not gas_channel:
                if lowers:
                    if elevation[q] >= elevation[p]:
                        continue
                elif elevation[q]*25+values[q] >= elevation[p]*25+amount:
                    continue
            neighbors[selected] = q
            selected += 1
        count = selected
        if not count:
            continue
        if awake:
            for j in range(count):
                q = neighbors[j]
                nx, ny = q % width, q // width
                # Source-snapshot entries win, even if their current flag differs.
                if not (mask[q] & 4) and 0 < nx < width-1 and 0 < ny < height-1 and flags[q] & source_flag and not (gas_channel and mask[q] & 1):
                    levels[q] = values[q]
                    mask[q] |= 4
        if not gas_channel and period > 1:
            clocks[p][clock_key] = now
        rotation = (x+y+now) % count
        for j in range(count):
            ordered[j] = neighbors[(j+rotation) % count]
        if canonical:
            # Legacy canonical order sorts coordinates (x,y), not flat indices.
            for j in range(count):
                for k in range(j+1, count):
                    if (ordered[k] % width < ordered[j] % width or
                        (ordered[k] % width == ordered[j] % width and ordered[k] < ordered[j])):
                        q, ordered[j] = ordered[j], ordered[k]
                        ordered[k] = q
        budget = maximum[kind]
        if gas_channel:
            budget = min(amount, budget)
            if gas_divisors[liquid_ids[p]] and liquid_values[p] >= thresholds[liquid_ids[p]]:
                budget = max(1, budget // gas_divisors[liquid_ids[p]])
            budget = max(1, budget // plant_divisors[plants[p]]) if plant_divisors[plants[p]] > 1 else budget
        else:
            if floors[p] is Material.PLAIN_AGGREGATE:
                budget *= bonuses[variants[p]]
                if divisors[variants[p]] > 1:
                    budget = max(1, budget // divisors[variants[p]])
            budget = min(amount, budget)
        for j in range(count):
            current[j], planned[j] = levels[ordered[j]]+reserved[ordered[j]], 0
        remaining = levels[p]
        lower = not gas_channel and lowers > 0
        # This at-most-four-target loop is shorter than a useful GIL handoff.
        # The independent process provides UI concurrency; keep this tiny
        # allocation under the GIL already held by preparation/settlement.
        # The separate complete-batch allocate() kernel still releases it.
        while budget > 0 and remaining > 0:
            selected = -1
            for j in range(count):
                if current[j] >= 100 or (not lower and remaining-current[j] < 2):
                    continue
                if selected < 0 or current[j] < current[selected]:
                    selected = j
            if selected < 0:
                break
            current[selected] += 1
            planned[selected] += 1
            remaining -= 1
            budget -= 1
        mark = clocks[p].get('decay:'+names[kind], now) if gas_channel else now
        for j in range(count):
            transfer = planned[j]
            if not transfer:
                continue
            q = ordered[j]
            reserved[q] += transfer
            if not outgoing[p]:
                source_order.append((x, y))
            outgoing[p] += transfer
            e = event_count
            event_count += 1
            events[e*4], events[e*4+1], events[e*4+3] = kind, transfer, -1
            if gas_channel:
                event_marks[e] = mark
            if heads[q] < 0:
                heads[q] = e
                target_order.append((q % width, q // width))
            else:
                events[tails[q]*4+3] = e
            tails[q] = e
    # Match legacy set(outgoing) | set(incoming), including presentation order
    # when drowning plants emits events during the final commit loop.
    # CPython constructs a set from dict keys with different preallocation than
    # from a list. That table layout controls subsequent source-index insertion
    # order. Preserve the actual legacy input container types, not only keys.
    changed = set(dict.fromkeys(source_order)) | set(dict.fromkeys(target_order))
    # Compute every result/clock against the same pre-commit snapshot.
    for x, y in state._material_positions(changed):
        p = y*width+x
        old_amount = max(0, values[p]-outgoing[p])
        kind, amount = ids[p], old_amount
        e = heads[p]
        if e >= 0:
            # The common same-kind path settles in integer buffers; only
            # heterogeneous targets allocate authored rule inputs.
            result_kind = kind if kind and amount > 0 else events[e*4]
            total, homogeneous = amount if kind and amount > 0 else 0, True
            while e >= 0:
                if events[e*4] != result_kind:
                    homogeneous = False
                total += events[e*4+1]
                e = events[e*4+3]
            if homogeneous:
                kind, amount = result_kind, min(100, total)
            else:
                arrivals, totals = [], {}
                if kind and amount > 0:
                    totals[names[kind]] = amount
                e = heads[p]
                while e >= 0:
                    name, transfer = names[events[e*4]], events[e*4+1]
                    arrivals.append((name, transfer))
                    totals[name] = totals.get(name, 0)+transfer
                    e = events[e*4+3]
                result = state._resolve_material_arrivals(names[kind], amount, arrivals) if gas_channel else state._mix_liquids(totals)
                kind, amount = mirror.intern(result[0]), result[1]
        results[p*3], results[p*3+1] = kind, amount
        if gas_channel:
            found_mark = ids[p] == kind and old_amount > 0
            e = heads[p]
            mark = clocks[p].get('decay:'+names[kind], now) if found_mark else now
            while e >= 0:
                if events[e*4] == kind:
                    mark = min(mark, event_marks[e]) if found_mark else event_marks[e]
                    found_mark = True
                e = events[e*4+3]
            result_marks[p] = mark
    # Results/clocks use the pre-commit snapshot, but settlement must remain
    # per-position: index synchronization can insert new source coordinates.
    # Publishing all amounts first lets its journal consumer insert them in a
    # different order, changing the next pass even when current pixels match.
    for x, y in state._material_positions(changed):
        p = y*width+x
        kind, amount = results[p*3], results[p*3+1]
        kinds[p] = names[kind] if amount else ''
        values[p] = min(100, amount)
        store.journal.record_many((p,), (channel, channel+'_kind'))
        cell = state.cells[y][x]
        if gas_channel:
            if values[p]:
                clocks[p]['decay:'+kinds[p]] = result_marks[p]
        elif values[p] and plants[p] and not plant_survives_liquid(plants[p]):
            drowned = state.set_plant(x, y, 0)
            if drowned:
                state._note_plant_wither(x, y, drowned, 'drowned')
        _stage_sync_position(state, x, y)
        if gas_channel and values[p] and 0 < x < width-1 and 0 < y < height-1:
            if not solid[p+1] or not solid[p-1] or not solid[p+width] or not solid[p-width]:
                exposed.add((x, y))
    return exposed if gas_channel else None


def phase_pass(state, mirror, points, const long long[::1] vapor,
               const unsigned char[::1] special):
    """Array-native phase dispatch with ordered five-cell capacity reservations.

    Stock transformations use compiled rules over authoritative columns.
    All decisions observe the latest preceding point, including phase locks.
    """
    from . import phase_changes as phase
    cdef _PhaseRules rules = _PhaseRules(state, mirror)
    cdef Py_ssize_t width = mirror.width, height = mirror.rows, x, y, p, q, j, count, hot_count
    cdef Py_ssize_t neighbors[5]
    cdef Py_ssize_t targets[5]
    cdef Py_ssize_t allocated[5]
    cdef long long product, remaining, taken, amount, hot_variant = mirror._ids['灼热聚合物']
    cdef long long steam = mirror._ids['灼热蒸汽'], metal = mirror._ids['熔念金属'], ice = mirror._ids['冰面']
    cdef long long now = state.time
    cdef bint is_hot
    cdef unsigned char[::1] liquid = mirror.liquid, gas = mirror.gas
    cdef const unsigned char[::1] solid = mirror.solid, flame = mirror.flame, stock = mirror.phase_stock
    cdef const unsigned short[::1] liquid_ids = mirror.liquid_id, gas_ids = mirror.gas_id, variants = mirror.variant_id, walls = mirror.wall_id
    cdef object store = mirror.store
    cdef list clocks = store.columns['material_clocks']
    cdef list liquid_kinds = store.columns['liquid_kind'], gas_kinds = store.columns['gas_kind']
    cdef object names = mirror.names, changed
    for x, y in points:
        if not (0 <= x < width and 0 <= y < height):
            # Match authored Cell indexing/error behavior on malformed candidates.
            phase._tick_point(state, x, y)
            continue
        p = y*width+x
        if (liquid_ids[p] >= vapor.shape[0] or gas_ids[p] >= special.shape[0]
                or walls[p] >= special.shape[0]):
            rules.tick(p)
            continue
        if clocks[p].get('phase:at') == now:
            continue
        if solid[p]:
            if special[walls[p]]:
                rules.tick(p)
            continue
        if stock[p] or variants[p] == ice:
            rules.tick(p)
            continue
        product = vapor[liquid_ids[p]] if liquid[p] else 0
        if not product:
            if (liquid[p] and special[liquid_ids[p]]) or (gas[p] and special[gas_ids[p]]):
                rules.tick(p)
            continue
        hot_count = 1
        neighbors[0] = p
        if x+1 < width:
            neighbors[hot_count] = p+1
            hot_count += 1
        if x > 0:
            neighbors[hot_count] = p-1
            hot_count += 1
        if y+1 < height:
            neighbors[hot_count] = p+width
            hot_count += 1
        if y > 0:
            neighbors[hot_count] = p-width
            hot_count += 1
        is_hot = variants[p] == hot_variant
        for j in range(hot_count):
            q = neighbors[j]
            if flame[q] or (gas[q] and gas_ids[q] == steam) or (liquid[q] and liquid_ids[q] == metal):
                is_hot = True
                break
        if not is_hot:
            # Cold condensation and freeze checks keep their exact source order.
            if (liquid[p] and special[liquid_ids[p]]) or (gas[p] and special[gas_ids[p]]):
                rules.tick(p)
            continue
        remaining = min(8, liquid[p])
        count, taken = 0, 0
        for j in range(hot_count):
            q = neighbors[j]
            if solid[q] or (q != p and clocks[q].get('phase:at') == now):
                continue
            if gas[q] and gas_ids[q] != product:
                continue
            amount = min(remaining, max(0, 100-gas[q]))
            if amount:
                targets[count], allocated[count] = q, amount
                count += 1
                remaining -= amount
                taken += amount
            if not remaining:
                break
        if not taken:
            continue
        liquid[p] -= taken
        if not liquid[p]:
            liquid_kinds[p] = ''
        store.journal.record_many((p,), ('liquid', 'liquid_kind'))
        clocks[p]['phase:at'] = now
        for j in range(count):
            q = targets[j]
            gas[q] += allocated[j]
            gas_kinds[q] = names[product]
            store.journal.record_many((q,), ('gas', 'gas_kind'))
            clocks[q]['phase:at'] = now
            state._sync_material_position(q % width, q // width)
        state._sync_material_position(x, y)


cdef class _PhaseRules:
    """Compiled authored phase rules over the owner's columns, without Cell reads.

    Variable-size stock values retain Python arithmetic and tracked assignment.
    Wall and plant gameplay callbacks remain authoritative side-effect owners.
    """
    cdef object state, mirror, store, columns, phase, now
    cdef Py_ssize_t width, height

    def __init__(self, state, mirror):
        from . import phase_changes
        self.state, self.mirror, self.store = state, mirror, mirror.store
        self.columns, self.phase = mirror.store.columns, phase_changes
        self.width, self.height, self.now = mirror.width, mirror.rows, state.time

    cdef object get(self, Py_ssize_t p, str field):
        return self.columns[field][p]

    cdef void put(self, Py_ssize_t p, str field, object value):
        # Store assignment preserves sparse exact values, nested aliases and
        # mutation notification. No narrowing of authored stock integers.
        self.store.write(p, field, value)

    cdef bint locked(self, Py_ssize_t p):
        return self.columns['material_clocks'][p].get('phase:at') == self.now

    cdef void mark(self, Py_ssize_t p):
        self.columns['material_clocks'][p]['phase:at'] = self.now

    cdef void sync(self, Py_ssize_t p):
        self.state._sync_material_position(p % self.width, p // self.width)

    cdef object neighbors(self, Py_ssize_t p):
        cdef Py_ssize_t x = p % self.width, y = p // self.width
        result = [p]
        if x+1 < self.width: result.append(p+1)
        if x: result.append(p-1)
        if y+1 < self.height: result.append(p+self.width)
        if y: result.append(p-self.width)
        return result

    cdef bint hot(self, Py_ssize_t p):
        cdef Py_ssize_t q
        if self.columns['aggregate_variant'][p] == '灼热聚合物':
            return True
        for q in self.neighbors(p):
            if (self.columns['flame'][q] > 0 or
                (self.columns['gas_kind'][q] == '灼热蒸汽' and self.columns['gas'][q] > 0) or
                (self.columns['liquid_kind'][q] == '熔念金属' and self.columns['liquid'][q] > 0)):
                return True
        return False

    cdef object plan(self, Py_ssize_t p, object kind, object amount, str field):
        cdef Py_ssize_t q
        result = []
        values, kinds, solids = self.columns[field], self.columns[field+'_kind'], self.columns['solid']
        for q in self.neighbors(p):
            if solids[q] or (q != p and self.locked(q)):
                continue
            current = int(values[q])
            if current and kinds[q] != kind:
                continue
            take = min(amount, max(0, 100-current))
            if take:
                result.append((q, take))
                amount -= take
            if not amount:
                break
        return result

    cdef void deposit(self, object plan, object kind, str field):
        from ..materials.plants import plant_survives_liquid
        cdef Py_ssize_t p
        for p, amount in plan:
            self.put(p, field, self.columns[field][p]+amount)
            self.put(p, field+'_kind', kind)
            if field == 'liquid' and self.columns['plant'][p] and not plant_survives_liquid(self.columns['plant'][p]):
                self.state.set_plant_at(self.state.cells[p // self.width][p % self.width], 0)
            self.mark(p)
            self.sync(p)

    cdef object cold(self, Py_ssize_t p, object required=None):
        from .tamper_protection import liquid_reason
        cdef Py_ssize_t q
        for q in self.neighbors(p):
            kind = self.columns['liquid_kind'][q]
            if (self.columns['liquid'][q] > 0 and kind in self.phase.COLD
                    and (required is None or kind == required) and not self.locked(q)
                    and not liquid_reason(kind)):
                plan = self.plan(q, '晨霜清气', 1, 'gas')
                if sum(amount for _, amount in plan) == 1:
                    return q, plan
        return None

    cdef void consume(self, object source):
        cdef Py_ssize_t p = source[0]
        remaining = self.columns['liquid'][p]-1
        self.put(p, 'liquid', remaining)
        if not remaining: self.put(p, 'liquid_kind', '')
        self.mark(p)
        self.deposit(source[1], '晨霜清气', 'gas')
        self.sync(p)

    cdef bint freeze(self, Py_ssize_t p, object recipe):
        from .tamper_protection import construction_reason, liquid_reason
        from .constants import Material
        cdef Py_ssize_t x = p % self.width, y = p // self.width
        if (self.columns['solid'][p] or self.columns['plant'][p] or self.columns['liquid'][p] <= 0
                or self.columns['liquid_kind'][p] != recipe.reactant_a or self.locked(p)
                or liquid_reason(self.columns['liquid_kind'][p])):
            return False
        if recipe.mechanism == 'freeze_wall' and (construction_reason(self.state, x, y) or self.columns['gas'][p]):
            return False
        source = self.cold(p, recipe.reactant_b)
        if source is None: return False
        stock = dict(self.columns['phase_stock'][p])
        if stock and (stock.get('form') != 'ice' or stock.get('kind') != self.columns['liquid_kind'][p]):
            return False
        total = int(stock.get('amount', 0))+self.columns['liquid'][p]
        if total > 100: return False
        original = stock.get('base_floor', self.columns['aggregate_variant'][p])
        kind = self.columns['liquid_kind'][p]
        if recipe.mechanism == 'freeze_wall':
            self.state.configure_wall(self.state.cells[y][x], recipe.product)
            stock = dict(form='wall', kind=kind, amount=total, initial_amount=total,
                         initial_integrity=self.columns['integrity'][p], wall=recipe.product, base_floor=original)
        else:
            self.put(p, 'liquid', 0)
            self.put(p, 'liquid_kind', '')
            self.put(p, 'floor', Material.PLAIN_AGGREGATE)
            self.put(p, 'aggregate_variant', recipe.product)
            stock = dict(form='ice', kind=kind, amount=total, base_floor=original)
        self.put(p, 'phase_stock', stock)
        self.mark(p)
        self.consume(source)
        self.sync(p)
        return True

    cdef bint melt_ice(self, Py_ssize_t p):
        from .tamper_protection import liquid_reason
        if (self.columns['solid'][p] or self.columns['aggregate_variant'][p] != '冰面'
                or self.locked(p) or not self.hot(p)):
            return False
        stock = dict(self.columns['phase_stock'][p] or dict(form='ice', kind='水', amount=8, base_floor='普通聚合物'))
        if stock.get('form') != 'ice' or liquid_reason(stock.get('kind', '')):
            return False
        amount = max(0, min(100, int(stock.get('amount', 0))))
        plan = self.plan(p, stock['kind'], min(8, amount), 'liquid')
        taken = sum(q for _, q in plan)
        if not taken: return False
        stock['amount'] = amount-taken
        self.put(p, 'phase_stock', stock if stock['amount'] else {})
        if not stock['amount']:
            self.put(p, 'aggregate_variant', stock.get('base_floor', '普通聚合物'))
        self.mark(p)
        self.deposit(plan, stock['kind'], 'liquid')
        self.sync(p)
        return True

    cdef bint melt_wall(self, Py_ssize_t p):
        from .tamper_protection import terrain_reason
        from ..materials.walls import WALL_DEFINITIONS
        from math import ceil
        cdef Py_ssize_t x = p % self.width, y = p // self.width
        kind = self.columns['wall_kind'][p]
        if (not self.columns['solid'][p] or kind not in self.phase.WAX or self.locked(p)
                or not self.hot(p) or terrain_reason(self.state, x, y)):
            return False
        definition = WALL_DEFINITIONS[kind]
        stock = dict(self.columns['phase_stock'][p])
        if not stock:
            amount = max(1, self.phase.WAX[kind]*self.columns['integrity'][p]//definition.integrity)
            stock = dict(form='wall', kind='熔融蜡烛', amount=amount, initial_amount=amount,
                         initial_integrity=self.columns['integrity'][p], wall=kind, base_floor=self.columns['aggregate_variant'][p])
        if stock.get('form') != 'wall' or stock.get('kind') != '熔融蜡烛': return False
        amount = min(int(stock['amount']), ceil(int(stock['initial_amount'])*self.columns['integrity'][p]/max(1, int(stock['initial_integrity']))))
        plan = self.plan(p, '熔融蜡烛', min(8, amount), 'liquid')
        taken = sum(q for _, q in plan)
        if not taken: return False
        stock['amount'] = amount-taken
        if not stock['amount']:
            if not self.state.destroy_wall(x, y, 'phase_melt'): return False
            self.put(p, 'aggregate_variant', stock.get('base_floor', '普通聚合物'))
            self.put(p, 'phase_stock', {})
        else:
            self.put(p, 'phase_stock', stock)
            self.put(p, 'integrity', max(1, ceil(int(stock['initial_integrity'])*stock['amount']/max(1, int(stock['initial_amount'])))))
        self.mark(p)
        self.deposit(plan, '熔融蜡烛', 'liquid')
        self.sync(p)
        return True

    cdef void tick(self, Py_ssize_t p):
        from .tamper_protection import liquid_reason
        if self.locked(p): return
        if self.columns['solid'][p]:
            if self.columns['wall_kind'][p] in self.phase.WAX: self.melt_wall(p)
            return
        if (self.columns['phase_stock'][p] or self.columns['aggregate_variant'][p] == '冰面') and self.melt_ice(p):
            return
        liquid_kind = str(self.columns['liquid_kind'][p] or '')
        gas_kind = str(self.columns['gas_kind'][p] or '')
        liquid, gas = int(self.columns['liquid'][p]), int(self.columns['gas'][p])
        vapor = liquid > 0 and liquid_kind in self.phase.VAPOR
        condensate = gas > 0 and gas_kind in self.phase.CONDENSATE
        recipes = self.phase.FREEZE_BY_LIQUID.get(liquid_kind) if liquid > 0 else ()
        if not (vapor or condensate or recipes or self.columns['phase_stock'][p]): return
        is_hot = self.hot(p) if (vapor or condensate or recipes) else False
        if vapor and is_hot and not liquid_reason(liquid_kind):
            product = self.phase.VAPOR[liquid_kind]
            plan = self.plan(p, product, min(8, liquid), 'gas')
            taken = sum(q for _, q in plan)
            if taken:
                self.put(p, 'liquid', liquid-taken)
                if liquid == taken: self.put(p, 'liquid_kind', '')
                self.mark(p)
                self.deposit(plan, product, 'gas')
                self.sync(p)
            return
        if not is_hot and condensate:
            source = self.cold(p)
            product = self.phase.CONDENSATE[gas_kind]
            plan = self.plan(p, product, min(8, gas), 'liquid')
            taken = sum(q for _, q in plan)
            if source is not None and taken:
                self.put(p, 'gas', gas-taken)
                if gas == taken: self.put(p, 'gas_kind', '')
                self.mark(p)
                self.deposit(plan, product, 'liquid')
                self.consume(source)
                self.sync(p)
                return
        if not is_hot and recipes:
            for recipe in recipes:
                if self.freeze(p, recipe): break


# Per-position Python-object mutations retain the GIL and reference chronology.
def prime_owned_clocks(self, store, position, context):
    _prime_owned_clocks_impl(self, store, position, context)

cdef void _prime_owned_clocks_impl(object self, object store, object position, dict context) except *:
    LIQUID_DEFINITIONS = context['LIQUID_DEFINITIONS']
    GAS_DEFINITIONS = context['GAS_DEFINITIONS']
    columns = store.columns
    """A newly arrived material cannot accumulate time before its arrival."""
    liquid = LIQUID_DEFINITIONS.get(columns['liquid_kind'][position]) if columns['liquid'][position] > 0 else None
    gas = GAS_DEFINITIONS.get(columns['gas_kind'][position]) if columns['gas'][position] > 0 else None
    active = set()
    if liquid is not None:
        if liquid.flow_period > 1:
            active.add("flow:" + columns['liquid_kind'][position])
        if liquid.evaporation_period > 0:
            active.add("evap:" + columns['liquid_kind'][position])
    if gas is not None:
        active.add("decay:" + columns['gas_kind'][position])
    for key in list(columns['material_clocks'][position]):
        if key.startswith(("flow:", "evap:", "decay:")) and key not in active:
            del columns['material_clocks'][position][key]
    for key in active:
        columns['material_clocks'][position].setdefault(key, self.time)

def project_owned_position(self, x, y, store, context):
    _project_owned_position_impl(self, x, y, store, context)

cdef void _project_owned_position_impl(object self, object x, object y, object store, dict context) except *:
    LIQUID_DEFINITIONS = context['LIQUID_DEFINITIONS']
    GAS_DEFINITIONS = context['GAS_DEFINITIONS']
    _PHASE_WALL_KINDS = context['_PHASE_WALL_KINDS']
    wall_def = context['wall_def']
    DIAL_TONE_GAS = context['DIAL_TONE_GAS']
    FLOOR_DEFINITIONS = context['FLOOR_DEFINITIONS']
    PLAIN_FLOOR = context['PLAIN_FLOOR']
    Material = context['Material']
    CONTAINER_KINDS = context['CONTAINER_KINDS']
    heapq = context['heapq']
    """Project compact authoritative values without re-entering Cell reads."""
    columns = store.columns
    index = y * self.width + x
    point = (x, y)
    liquid, gas, flame = columns['liquid'][index], columns['gas'][index], columns['flame'][index]
    liquid_kind, gas_kind = columns['liquid_kind'][index], columns['gas_kind'][index]
    wall_kind, solid = columns['wall_kind'][index], columns['solid'][index]
    phase = bool(columns['phase_stock'][index]) or flame > 0 or columns['aggregate_variant'][index] == '冰面' or (solid and wall_kind in _PHASE_WALL_KINDS)
    liquid_definition = LIQUID_DEFINITIONS.get(liquid_kind) if liquid > 0 else None
    gas_definition = GAS_DEFINITIONS.get(gas_kind) if gas > 0 else None
    ventilation = exhaust = False
    if solid and columns['integrity'][index] > 0:
        wall = wall_def(wall_kind)
        ventilation = bool(wall.gas_push_direction)
        exhaust = wall.gas_dissipation_multiplier > 1
    flags = (("_liquid_cells", liquid > 0), ("_gas_cells", gas > 0),
             ("_periodic_liquid_cells", liquid_definition is not None and liquid_definition.evaporation_period > 0),
             ("_periodic_gas_cells", gas_definition is not None and gas_definition.dissipation_period > 0),
             ("_flame_cells", flame > 0), ("_phase_cells", phase),
             ("_special_cells", wall_kind in self._SPECIAL_WALL_KINDS),
             ("_ventilation_cells", ventilation), ("_exhaust_cells", exhaust))
    for name, active in flags:
        bucket = getattr(self, name)
        if active:
            bucket.add(point)
        else:
            bucket.discard(point)
    if getattr(self, '_material_dirty_on', False):
        step = getattr(self, '_material_step', 0)
        for nx, ny in ((x, y), (x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            neighbour = ny*self.width+nx
            p = (nx, ny)
            self._touch_tick[p] = step
            if columns['liquid'][neighbour] > 0:
                self._awake_liquid.add(p)
            if columns['gas'][neighbour] > 0:
                self._awake_gas.add(p)
            if (columns['phase_stock'][neighbour] or columns['flame'][neighbour] > 0
                    or columns['aggregate_variant'][neighbour] == '冰面'
                    or (columns['solid'][neighbour] and columns['wall_kind'][neighbour] in _PHASE_WALL_KINDS)):
                self._awake_phase.add(p)
        if gas <= 0:
            self._dial_tone_cells.discard(point)
            self._gas_absorb_cells.discard(point)
            self._drop_gas_decay(point)
        else:
            if gas_kind == DIAL_TONE_GAS:
                self._dial_tone_cells.add(point)
            else:
                self._dial_tone_cells.discard(point)
            effect = (FLOOR_DEFINITIONS.get(columns['aggregate_variant'][index], PLAIN_FLOOR)
                      if columns['floor'][index] is Material.PLAIN_AGGREGATE else PLAIN_FLOOR)
            if effect.gas_absorb > 0 and not effect.preserves_gas:
                self._gas_absorb_cells.add(point)
            else:
                self._gas_absorb_cells.discard(point)
            if gas_definition is None:
                self._drop_gas_decay(point)
            elif wall_kind in CONTAINER_KINDS or effect.preserves_gas:
                self._decay_hold.add(point)
                self._decay_due.pop(point, None)
            else:
                self._decay_hold.discard(point)
                period = gas_definition.dissipation_period or self._gas_decay_interval()
                mark = columns['material_clocks'][index].get('decay:' + gas_kind)
                due = self.time if mark is None else mark + period
                if self._decay_due.get(point) != due:
                    self._decay_due[point] = due
                    heapq.heappush(self._decay_heap, (due, point))
    mirror = getattr(self, '_material_grid', None)
    if mirror is not None:
        try:
            if (type(mirror) is _grid_class
                    and getattr(_numeric_module, '_sync_owned_grid', None) is sync_owned_grid
                    and getattr(mirror.sync_cell, '__func__', None) is _grid_sync_reference
                    and getattr(mirror._sync_owned, '__func__', None) is _grid_owned_reference
                    and getattr(mirror.index, '__func__', None) is _grid_index_reference
                    and mirror.store is store
                    and self.cells[y][x].__dict__.get('_material_binding') == (store, index)):
                # Preserve validation/custom index hooks before touching arrays.
                mirror.index(x, y)
                _sync_owned_grid_impl(mirror, index, _grid_module.__dict__)
            else:
                mirror.sync_cell(x, y, self.cells[y][x])
        except ValueError as error:
            self._material_grid = None
            self._material_grid_error = str(error)

def sync_owned_grid(self, position, context):
    _sync_owned_grid_impl(self, position, context)

cdef void _sync_owned_grid_impl(object self, object position, dict context) except *:
    CONTAINER_KINDS = context['CONTAINER_KINDS']
    FLOOR_DEFINITIONS = context['FLOOR_DEFINITIONS']
    PLAIN_FLOOR = context['PLAIN_FLOOR']
    Material = context['Material']
    LIQ_MIN_FLOW = context['LIQ_MIN_FLOW']
    GAS_MIN_FLOW = context['GAS_MIN_FLOW']
    LIQUID_DEFINITIONS = context['LIQUID_DEFINITIONS']
    GAS_DEFINITIONS = context['GAS_DEFINITIONS']
    columns = self.store.columns
    # Nonrepresentable values retain their exact Cell fallback. Validate
    # before deriving any marker; never consume the placeholder array zero.
    for field in ('liquid', 'gas', 'flame', 'height', 'plant', 'elevation', 'solid'):
        if (field, position) in self.store.exceptions:
            raise ValueError(f'{field} cannot be represented by the compact material view')
    # Owned Cell reads bool columns through bool(value), including legacy
    # integer writes such as solid=2. Match that visible contract without
    # rewriting the authoritative raw value or creating an unjournaled edit.
    solid = bool(columns['solid'][position])
    phase = columns['phase_stock'][position]
    if not isinstance(phase, dict):
        raise ValueError('phase_stock must be a dictionary')
    liquid_kind, gas_kind = columns['liquid_kind'][position], columns['gas_kind'][position]
    wall_kind = columns['wall_kind'][position]
    floor, variant = columns['floor'][position], columns['aggregate_variant'][position]
    identifiers = [self.intern(value) for value in
                   (liquid_kind, gas_kind, wall_kind, floor, variant)]
    container = wall_kind in CONTAINER_KINDS
    passable = not solid or columns['height'][position] <= 1
    effect = FLOOR_DEFINITIONS.get(variant, PLAIN_FLOOR) if floor is Material.PLAIN_AGGREGATE else PLAIN_FLOOR
    flags = self.CONTAINER if container else 0
    if effect.preserves_gas:
        flags |= self.PRESERVES_GAS
    if passable:
        flags |= self.FLOW_PASSABLE
        if not container:
            flags |= self.GAS_FLOW_PASSABLE
            if columns['liquid'][position] >= LIQ_MIN_FLOW and liquid_kind in LIQUID_DEFINITIONS:
                flags |= self.LIQUID_SOURCE
            if columns['gas'][position] >= GAS_MIN_FLOW and gas_kind in GAS_DEFINITIONS:
                flags |= self.GAS_SOURCE
    # Numeric columns already alias the owner: only derived values change.
    self.phase_stock[position] = bool(phase)
    self.flags[position] = flags
    for field, identifier in zip(self.ID_FIELDS, identifiers):
        getattr(self, field)[position] = identifier



# Full recipe and authored special-material stages. Arithmetic is Python
# whenever callbacks/rules or sparse exceptions require exact Python values.
def recipe_owned_stage(self):
    """液气反应与其他反应（墙/地板参与）的逐拍结算（materials/reactions.py）。

    混合类（液液/气气）在混合点（_mix_liquids / _resolve_material_arrivals）
    当场转化，不走这里；这里只管「液气同格全量转化」与逐拍推进的
    熔穿/崩解/脆裂/凝固/冻结。播报每种反应每层只播一次（运行期记录，
    不进存档），与超临界流体剥蚀的播报模式一致。
    """
    # Full ordered rule stage; callbacks and writes stay under the GIL.
    from . import materials_sim as rules
    cdef Py_ssize_t x, y, sx, sy, nx, ny, nx2, ny2
    cdef int _mechanism
    cdef Py_ssize_t _cell_index, _neighbor_index, _width
    self._ensure_material_index()
    _store = getattr(self.cells, 'store', None)
    _columns = _store.columns
    cdef object _column_aggregate_variant = _columns['aggregate_variant']
    cdef object _column_floor = _columns['floor']
    cdef const unsigned char[::1] _column_gas = _columns['gas']
    cdef object _column_gas_kind = _columns['gas_kind']
    cdef const long long[::1] _column_integrity = _columns['integrity']
    cdef const unsigned char[::1] _column_liquid = _columns['liquid']
    cdef object _column_liquid_kind = _columns['liquid_kind']
    cdef const unsigned char[::1] _column_plant = _columns['plant']
    cdef const unsigned char[::1] _column_solid = _columns['solid']
    cdef object _column_wall_kind = _columns['wall_kind']
    _width = self.width
    notified = getattr(self, "_recipe_notified_depths", None)
    if notified is None:
        notified = set()
        self._recipe_notified_depths = notified

    def notify(recipe: rules.ReactionDef) -> None:
        if recipe.message and (self.depth, id(recipe)) not in notified:
            notified.add((self.depth, id(recipe)))
            self.messages.append(rules.tr(recipe.message))

    grid = self.cells
    # 方案 1（2026-11-04）：编译版只做候选筛选，保持 _liquid_cells 的迭代
    # 顺序；未命中「有气体 / 有登记配方」的静态液提前剔除。落账仍在下面。
    if rules._kernel_enabled("recipe"):
        points = rules._kernel_recipe_cells(
            grid, self.width, self.height, self._liquid_pass_cells(), rules.OTHER_BY_REACTANT)
    else:
        points = self._liquid_pass_cells()
    for x, y in points:
        if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
            continue
        cell = grid[y][x]
        _cell_index = y * _width + x
        # ---- 液气反应：同格液气命中配方即全量转化（总量守恒、上限 100）----
        # 只有真有气体的格才构造 frozenset 查表：液体格远多于液气共存格。
        recipe = None
        if (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) > 0 and (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)):
            _registry = rules.LIQUID_GAS_RECIPES
            if type(_registry) is dict:
                recipe = _lookup_recipe_pair(_registry,
                    _stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind),
                    _stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind))
            else:
                # Resolve the authored .get before reading arguments, exactly
                # as the original bound-method call does.
                _get_recipe = _registry.get
                recipe = _get_recipe(frozenset((
                    _stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind),
                    _stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind))))
        if recipe and recipe.mechanism == 'lg_neutralize' and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) > 0:
            self._neutralize_hospital_dust(x, y)
            continue
        if (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= 10 and (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) >= 10 and (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)):
            if recipe is not None:
                if recipe.product_type == "液体":
                    _stage_owner_write(_store, cell, _cell_index, 'liquid_kind', recipe.product)
                    _stage_owner_write(_store, cell, _cell_index, 'liquid', min(100, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) + (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas))))
                    _stage_owner_write(_store, cell, _cell_index, 'gas', 0)
                    _stage_owner_write(_store, cell, _cell_index, 'gas_kind', "")
                else:  # 产物是气体：液量并入气量
                    _stage_owner_write(_store, cell, _cell_index, 'gas_kind', recipe.product)
                    _stage_owner_write(_store, cell, _cell_index, 'gas', min(100, (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) + (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid))))
                    _stage_owner_write(_store, cell, _cell_index, 'liquid', 0)
                    _stage_owner_write(_store, cell, _cell_index, 'liquid_kind', "")
                _stage_sync_position(self, x, y)
                self._note_seen_reaction(recipe, x, y)
                notify(recipe)
                continue
        # ---- 其他反应：液体格的邻接结算 ----
        # 没有登记配方的液体（多数静态液）连邻接表都不必构造。
        _get_other_recipe = rules.OTHER_BY_REACTANT.get
        recipes = _get_other_recipe(_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind))
        if not recipes:
            continue
        neighbors = rules._interior_neighbors(x, y)
        for recipe in recipes:
            mechanism = recipe.mechanism
            _mechanism = _recipe_mechanism_code(mechanism)
            if (_mechanism == 1 or (_mechanism < 0 and mechanism == "wall_melt")):
                # 熔念金属渗进相邻固体墙：按配方扣完整度并消耗液体，熔穿后留一洼余浆。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_a and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= recipe.min_amount:
                    for nx, ny in neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        # 不腐蚀容器、机关、边界和可推解谜固体。
                        _get_wall = rules.WALL_DEFINITIONS.get
                        definition = _get_wall(_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind))
                        if ((_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and definition is not None and definition.hardness < 999
                                and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) not in rules.CONTAINER_KINDS and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) not in rules.SOLID_KINDS
                                and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) not in rules.LOGIC_KINDS
                                and not definition.path_clickable and not definition.pushable
                                and not (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)).startswith("逻辑")):
                            _stage_owner_write(_store, neighbor, _neighbor_index, 'integrity', max(0, (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) - recipe.damage))
                            _stage_owner_write(_store, cell, _cell_index, 'liquid', max(0, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) - recipe.consumption))
                            if (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) == 0:
                                self.destroy_wall(nx, ny, "peel")
                                self._add_liquid(self.cells[ny][nx], recipe.reactant_a, 5)
                            _stage_sync_position(self, x, y)
                            notify(recipe)
                            break
            elif (_mechanism == 2 or (_mechanism < 0 and mechanism == "wall_bust_gas")):
                # 酸蚀液剧烈溶蚀盐晶壁：墙崩解并放出毒气 20 点。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) > 0:
                    for nx, ny in neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        if (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_a:
                            self.destroy_wall(nx, ny, "dissolve")
                            self._add_gas(self.cells[ny][nx], recipe.product, 20)
                            notify(recipe)
            elif (_mechanism == 3 or (_mechanism < 0 and mechanism == "wall_shatter")):
                # 寒液脆裂墙体：每拍完整度 −8，消耗液体 1。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= recipe.min_amount:
                    for nx, ny in neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        if (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_a:
                            _stage_owner_write(_store, neighbor, _neighbor_index, 'integrity', max(0, (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) - recipe.damage))
                            _stage_owner_write(_store, cell, _cell_index, 'liquid', max(0, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) - recipe.consumption))
                            if (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) == 0:
                                self.destroy_wall(nx, ny, "shatter")
                            _stage_sync_position(self, x, y)
                            notify(recipe)
                            break
            elif (_mechanism == 4 or (_mechanism < 0 and mechanism == "freeze_wall")):
                # 液态蜡与寒液相邻：当场凝固成蜡化记忆墙。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_a and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) > 0 and not (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)):
                    if any(
                        (_stage_object_read(_store, grid[ny][nx], (ny) * _width + (nx), 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, grid[ny][nx], (ny) * _width + (nx), 'liquid', _column_liquid)) > 0
                        for nx, ny in neighbors
                    ):
                        _stage_owner_write(_store, cell, _cell_index, 'liquid', 0)
                        _stage_owner_write(_store, cell, _cell_index, 'liquid_kind', "")
                        self.configure_wall(cell, recipe.product)
                        _stage_sync_position(self, x, y)
                        notify(recipe)
            elif (_mechanism == 5 or (_mechanism < 0 and mechanism == "freeze_floor")):
                # 水面与寒液相邻：整格冻成冰面（只覆盖普通聚合物地板，保留植物外的内容）。
                if (
                    (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_a and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) > 0
                    and not (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)) and not (_stage_u8_read(_store, cell, _cell_index, 'plant', _column_plant))
                ):
                    if any(
                        (_stage_object_read(_store, grid[ny][nx], (ny) * _width + (nx), 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, grid[ny][nx], (ny) * _width + (nx), 'liquid', _column_liquid)) > 0
                        for nx, ny in neighbors
                    ):
                        _stage_owner_write(_store, cell, _cell_index, 'liquid', 0)
                        _stage_owner_write(_store, cell, _cell_index, 'liquid_kind', "")
                        if (_stage_object_read(_store, cell, _cell_index, 'floor', _column_floor)) is rules.Material.PLAIN_AGGREGATE:
                            _stage_owner_write(_store, cell, _cell_index, 'aggregate_variant', recipe.product)
                        _stage_sync_position(self, x, y)
                        notify(recipe)
            elif (_mechanism == 6 or (_mechanism < 0 and mechanism == "wall_to_liquid")):
                # 墙化液：墙被相邻液体泡溶，整段墙消失、原地淌出产物液体。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= 10:
                    for nx, ny in neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        if (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_a:
                            self.destroy_wall(nx, ny, "dissolve")
                            self._add_liquid(self.cells[ny][nx], recipe.product, 20)
                            _stage_owner_write(_store, cell, _cell_index, 'liquid', max(0, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) - 10))
                            _stage_sync_position(self, x, y)
                            notify(recipe)
                            break
            elif (_mechanism == 7 or (_mechanism < 0 and mechanism == "wall_flush")):
                # 墙冲平：液体冲塌墙，原地留指定地板变体。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= 10:
                    for nx, ny in neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        if (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_a:
                            self.destroy_wall(nx, ny, "flush")
                            if (_stage_object_read(_store, neighbor, _neighbor_index, 'floor', _column_floor)) is rules.Material.PLAIN_AGGREGATE:
                                _stage_owner_write(_store, neighbor, _neighbor_index, 'aggregate_variant', recipe.product)
                                _stage_sync_position(self, nx, ny)
                            _stage_owner_write(_store, cell, _cell_index, 'liquid', max(0, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) - 10))
                            _stage_sync_position(self, x, y)
                            notify(recipe)
                            break
            elif (_mechanism == 8 or (_mechanism < 0 and mechanism == "wall_retype")):
                # 墙改型：液体改写墙种（洗蜡/去锈/淬覆），墙还在、材料换了。
                if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= 10:
                    for nx, ny in neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        if (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_a:
                            self.configure_wall(neighbor, recipe.product)
                            _stage_owner_write(_store, cell, _cell_index, 'liquid', max(0, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) - 10))
                            self._material_index_ready = False
                            notify(recipe)
                            break
            elif (_mechanism == 9 or (_mechanism < 0 and mechanism == "floor_revert")):
                # 地板退化：特殊地板浸入反应液体，退回指定地板变体（一般
                # 是普通聚合物）。同格判定——液体就淌在这块地板上。
                if (
                    not (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)) and not (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind))
                    and (_stage_object_read(_store, cell, _cell_index, 'aggregate_variant', _column_aggregate_variant)) == recipe.reactant_a
                    and (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= 10
                ):
                    _stage_owner_write(_store, cell, _cell_index, 'liquid', max(0, (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) - 10))
                    if (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) <= 0:
                        _stage_owner_write(_store, cell, _cell_index, 'liquid', 0)
                        _stage_owner_write(_store, cell, _cell_index, 'liquid_kind', "")
                    if (_stage_object_read(_store, cell, _cell_index, 'floor', _column_floor)) is rules.Material.PLAIN_AGGREGATE:
                        _stage_owner_write(_store, cell, _cell_index, 'aggregate_variant', recipe.product)
                    _stage_sync_position(self, x, y)
                    notify(recipe)
            elif (_mechanism == 10 or (_mechanism < 0 and mechanism == "floor_pulp")):
                # 地板化液：特殊地板泡烂退回普通地面，并淌出产物液体。
                # 媒介液体（reactant_b）被反应消耗：先清空再倒产物——否则
                # 产物与本格残水混合，主导方判定会翻回媒介（如 水<纸浆 字典序）。
                if (
                    not (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)) and not (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind))
                    and (_stage_object_read(_store, cell, _cell_index, 'aggregate_variant', _column_aggregate_variant)) == recipe.reactant_a
                    and (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) >= 10
                ):
                    _stage_owner_write(_store, cell, _cell_index, 'liquid', 0)
                    _stage_owner_write(_store, cell, _cell_index, 'liquid_kind', "")
                    if (_stage_object_read(_store, cell, _cell_index, 'floor', _column_floor)) is rules.Material.PLAIN_AGGREGATE:
                        _stage_owner_write(_store, cell, _cell_index, 'aggregate_variant', "普通聚合物")
                    self._add_liquid(cell, recipe.product, 20)
                    _stage_sync_position(self, x, y)
                    notify(recipe)
    # ---- 气体侧反应：气在墙上（低墙共存）与气蚀墙/气体地板退化 ----
    for x, y in self._gas_pass_cells():
        if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
            continue
        cell = grid[y][x]
        _cell_index = y * _width + x
        if (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) <= 0 or not (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)):
            continue
        _get_other_recipe = rules.OTHER_BY_REACTANT.get
        recipes = _get_other_recipe(_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind))
        if not recipes:
            continue
        gas_neighbors = None
        for recipe in recipes:
            mechanism = recipe.mechanism
            _mechanism = _recipe_mechanism_code(mechanism)
            if (_mechanism == 6 or (_mechanism < 0 and mechanism == "wall_to_liquid")):
                # 热汽闷软低墙（高度 1 的墙允许气体共存）：墙化液。
                if (
                    (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) >= 15
                    and (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)) and (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_a
                ):
                    self.destroy_wall(x, y, "dissolve")
                    self._add_liquid(cell, recipe.product, 20)
                    _stage_owner_write(_store, cell, _cell_index, 'gas', max(0, (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) - 15))
                    if (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) <= 0:
                        _stage_owner_write(_store, cell, _cell_index, 'gas_kind', "")
                    _stage_sync_position(self, x, y)
                    notify(recipe)
                    break
            elif (_mechanism == 11 or (_mechanism < 0 and mechanism == "gas_etch")):
                # 酸雾蚀墙：气体与墙相邻，每拍完整度 −6，消耗气体 1，浓度至少 15。
                if (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)) == recipe.reactant_a and (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) >= recipe.min_amount:
                    if gas_neighbors is None:
                        gas_neighbors = rules._interior_neighbors(x, y)
                    for nx, ny in gas_neighbors:
                        neighbor = self.cells[ny][nx]
                        _neighbor_index = ny * _width + nx
                        if (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) == recipe.reactant_b:
                            _stage_owner_write(_store, neighbor, _neighbor_index, 'integrity', max(0, (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) - recipe.damage))
                            _stage_owner_write(_store, cell, _cell_index, 'gas', max(0, (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) - recipe.consumption))
                            _stage_sync_position(self, x, y)
                            if (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) == 0:
                                self.destroy_wall(nx, ny, "etch")
                            notify(recipe)
                            break
            elif (_mechanism == 9 or (_mechanism < 0 and mechanism == "floor_revert")):
                # 气体地板退化：反应气体笼罩特殊地板，退回普通地面。
                if (
                    not (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)) and not (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind))
                    and (_stage_object_read(_store, cell, _cell_index, 'aggregate_variant', _column_aggregate_variant)) == recipe.reactant_a
                    and (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)) == recipe.reactant_b and (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) >= 15
                ):
                    _stage_owner_write(_store, cell, _cell_index, 'gas', max(0, (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) - 15))
                    if (_stage_u8_read(_store, cell, _cell_index, 'gas', _column_gas)) <= 0:
                        _stage_owner_write(_store, cell, _cell_index, 'gas_kind', "")
                    if (_stage_object_read(_store, cell, _cell_index, 'floor', _column_floor)) is rules.Material.PLAIN_AGGREGATE:
                        _stage_owner_write(_store, cell, _cell_index, 'aggregate_variant', recipe.product)
                    _stage_sync_position(self, x, y)
                    notify(recipe)

def special_owned_stage(self):
    """内容扩展材料反应：火+水→灼热蒸汽；蜡化记忆墙热敏融解；
    《新材料》的烛泪柱/枕木/黄粱米堆燃烧转化与梦晶簇吸储气体。"""
    # 索引由写入处增量同步；只有墙体破坏等确实使索引失效的路径才重建，
    # 不再每拍无条件全图重建（docs §11 P0）。
    # Full ordered rule stage; callbacks and writes stay under the GIL.
    from . import materials_sim as rules
    cdef Py_ssize_t x, y, sx, sy, nx, ny, nx2, ny2
    cdef Py_ssize_t _cell_index, _neighbor_index, _width
    self._ensure_material_index()
    _store = getattr(self.cells, 'store', None)
    _columns = _store.columns
    cdef const long long[::1] _column_cover = _columns['cover']
    cdef const unsigned char[::1] _column_flame = _columns['flame']
    cdef const unsigned char[::1] _column_gas = _columns['gas']
    cdef object _column_gas_kind = _columns['gas_kind']
    cdef const long long[::1] _column_integrity = _columns['integrity']
    cdef const unsigned char[::1] _column_liquid = _columns['liquid']
    cdef object _column_liquid_kind = _columns['liquid_kind']
    cdef object _column_material_clocks = _columns['material_clocks']
    cdef const unsigned char[::1] _column_solid = _columns['solid']
    cdef object _column_wall_kind = _columns['wall_kind']
    _width = self.width
    rng = rules.random.Random(self.seed ^ (self.time * 2654435761))
    # 候选集：特殊墙体自身 + 火焰格 + 特殊墙体的相邻格
    # （燃烧看邻居火焰、吸储看邻居气体、热敏看邻居火焰）。
    candidates = set(self._special_cells) | set(self._flame_cells)
    for sx, sy in self._material_positions(self._special_cells):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidates.add((sx + dx, sy + dy))
    # 超临界流体所在格也纳入候选（剥蚀相邻墙体）。
    for x, y in self._liquid_pass_cells():
        if (_stage_object_read(_store, self.cell(x, y), (y) * _width + (x), 'liquid_kind', _column_liquid_kind)) == "超临界流体":
            candidates.add((x, y))
    for x, y in tuple(candidates):
        if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
            continue
        cell = self.cell(x, y)
        _cell_index = y * _width + x
        neighbors = rules._interior_neighbors(x, y)
        if (_stage_u8_read(_store, cell, _cell_index, 'flame', _column_flame)) > 0:
            # 火+水→灼热蒸汽（30% 概率转化 10 点）。
            for nx, ny in neighbors:
                neighbor = self.cells[ny][nx]
                _neighbor_index = ny * _width + nx
                if not (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and (_stage_object_read(_store, neighbor, _neighbor_index, 'liquid_kind', _column_liquid_kind)) == "水" and (_stage_u8_read(_store, neighbor, _neighbor_index, 'liquid', _column_liquid)) >= 10 and rng.random() < 0.3:
                    _stage_owner_write(_store, neighbor, _neighbor_index, 'liquid', getattr(neighbor, 'liquid') - (10))
                    if (_stage_u8_read(_store, neighbor, _neighbor_index, 'liquid', _column_liquid)) <= 0:
                        _stage_owner_write(_store, neighbor, _neighbor_index, 'liquid_kind', "")
                    self._add_gas(neighbor, "灼热蒸汽", 10, position=(nx, ny))
                    _stage_sync_position(self, nx, ny)
        if (_stage_object_read(_store, cell, _cell_index, 'liquid_kind', _column_liquid_kind)) == "超临界流体" and (_stage_u8_read(_store, cell, _cell_index, 'liquid', _column_liquid)) > 0:
            # 超临界流体渗进墙体缝隙：直接剥蚀相邻墙体（无需生物携带）。
            eroded = False
            for nx, ny in neighbors:
                neighbor = self.cells[ny][nx]
                _neighbor_index = ny * _width + nx
                if (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) and (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) != "意识边界":
                    _stage_owner_write(_store, neighbor, _neighbor_index, 'integrity', max(0, (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) - 3))
                    eroded = True
                    if (_stage_i64_read(_store, neighbor, _neighbor_index, 'integrity', _column_integrity)) == 0:
                        self.destroy_wall(nx, ny, "peel")
            if eroded:
                # 剥蚀只改邻墙的 integrity，本格自身状态没变；不显式登记触碰
                # 的话，脏区模式会把正在持续剥蚀的格子当成静止格睡死。
                _stage_sync_position(self, x, y)
                # 事件消息每层只播一次（运行期记录，不进存档）。
                notified = getattr(self, "_superfluid_notified_depths", None)
                if notified is None:
                    notified = set()
                    self._superfluid_notified_depths = notified
                if self.depth not in notified:
                    notified.add(self.depth)
                    self.messages.append(rules.tr("超临界流体渗进墙体缝隙，石体簌簌剥落。"))
        if (_stage_u8_read(_store, cell, _cell_index, 'solid', _column_solid)) and (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind)) == "盐晶壁":
            # 盐晶壁遇水溶解：任一邻格有水即化。
            if any((_stage_object_read(_store, self.cell(nx, ny), (ny) * _width + (nx), 'liquid_kind', _column_liquid_kind)) == "水" and (_stage_u8_read(_store, self.cell(nx, ny), (ny) * _width + (nx), 'liquid', _column_liquid)) > 0 for nx, ny in neighbors):
                self.destroy_wall(x, y, "dissolve")
                self.messages.append(rules.tr("盐晶壁遇水，簌地溶掉了。"))
                continue
        if (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind)) in ("蜡化记忆墙", "烛泪柱", "枕木", "黄粱米堆"):
            if any((_stage_u8_read(_store, self.cell(nx, ny), (ny) * _width + (nx), 'flame', _column_flame)) > 0 for nx, ny in neighbors):
                self._ignite_cell(x, y, 2)
            continue
        if (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind)) in ("梦晶簇", "无意识结晶"):
            # 吸收 3×3 范围内全部气体并储存（不混合种类）。
            # 无意识结晶是深处的强化种：上限 160。
            capacity = (160 if (_stage_object_read(_store, cell, _cell_index, 'wall_kind', _column_wall_kind)) == "无意识结晶" else 100) - (_stage_i64_read(_store, cell, _cell_index, 'cover', _column_cover))
            if capacity > 0:
                for ny2 in range(max(1, y - 1), min(self.height - 1, y + 2)):
                    for nx2 in range(max(1, x - 1), min(self.width - 1, x + 2)):
                        if capacity <= 0:
                            break
                        neighbor = self.cell(nx2, ny2)
                        _neighbor_index = ny2 * _width + nx2
                        if (_stage_u8_read(_store, neighbor, _neighbor_index, 'solid', _column_solid)) or (_stage_u8_read(_store, neighbor, _neighbor_index, 'gas', _column_gas)) <= 0 or (_stage_object_read(_store, neighbor, _neighbor_index, 'gas_kind', _column_gas_kind)) not in rules.GAS_DEFINITIONS:
                            continue
                        if (_stage_object_read(_store, neighbor, _neighbor_index, 'wall_kind', _column_wall_kind)) in rules.CONTAINER_KINDS:
                            continue
                        if (_stage_i64_read(_store, cell, _cell_index, 'cover', _column_cover)) > 0 and (_stage_object_read(_store, neighbor, _neighbor_index, 'gas_kind', _column_gas_kind)) != (_stage_object_read(_store, cell, _cell_index, 'gas_kind', _column_gas_kind)):
                            continue
                        taken = min(capacity, (_stage_u8_read(_store, neighbor, _neighbor_index, 'gas', _column_gas)))
                        kind = (_stage_object_read(_store, neighbor, _neighbor_index, 'gas_kind', _column_gas_kind))
                        stored_key,decay_key = 'crystal_stored:' + kind,'crystal_decay:' + kind
                        stored = (_stage_object_read(_store, cell, _cell_index, 'material_clocks', _column_material_clocks)).get(stored_key,self.time)
                        previous_age = max(0,stored-(_stage_object_read(_store, cell, _cell_index, 'material_clocks', _column_material_clocks)).get(decay_key,stored)) if (_stage_i64_read(_store, cell, _cell_index, 'cover', _column_cover)) else 0
                        source_age = max(0,self.time-(_stage_object_read(_store, neighbor, _neighbor_index, 'material_clocks', _column_material_clocks)).get('decay:' + kind,self.time))
                        (_stage_object_read(_store, cell, _cell_index, 'material_clocks', _column_material_clocks))[stored_key] = self.time
                        (_stage_object_read(_store, cell, _cell_index, 'material_clocks', _column_material_clocks))[decay_key] = self.time-max(previous_age,source_age)
                        if (_stage_i64_read(_store, cell, _cell_index, 'cover', _column_cover)) == 0:
                            _stage_owner_write(_store, cell, _cell_index, 'gas_kind', _stage_object_read(_store, neighbor, _neighbor_index, 'gas_kind', _column_gas_kind))
                        _stage_owner_write(_store, neighbor, _neighbor_index, 'gas', getattr(neighbor, 'gas') - (taken))
                        if (_stage_u8_read(_store, neighbor, _neighbor_index, 'gas', _column_gas)) <= 0:
                            _stage_owner_write(_store, neighbor, _neighbor_index, 'gas_kind', "")
                        _stage_owner_write(_store, cell, _cell_index, 'cover', getattr(cell, 'cover') + (taken))
                        capacity -= taken
                        _stage_sync_position(self, nx2,ny2)
                        _stage_sync_position(self, x,y)


# Fused incremental ownership boundary. Cold rebuild and authored policy remain
# the Python reference path; all per-position journal/clock chronology is kept.
def ensure_owned_index(state, store, context):
    return _ensure_owned_index_impl(state, store, context)

cdef bint _ensure_owned_index_impl(object state, object store, dict context) except *:
    cdef object mirror, cursor, batch, initial, primed, positions, position
    cdef object x, y
    if not hasattr(state, '_material_grid_on'):
        return False
    mirror = getattr(state, '_material_grid', None)
    if mirror is not None:
        if (type(mirror) is not _grid_class
                or getattr(mirror.matches, '__func__', None) is not _grid_matches_reference):
            return False
        if not mirror.matches(state.cells, state.width, state.height):
            return False
    if not getattr(state, '_material_index_ready', False):
        return False
    cursor = getattr(state, '_material_index_cursor', None)
    if cursor == store.journal.cursor:
        return True
    batch = store.journal.changes_since(cursor)
    if batch.reset:
        return False
    initial = batch.positions
    for position in sorted(initial):
        if (store.exceptions or store._authored_positions
                or store is not getattr(state.cells, 'store', None)
                or getattr(state._prime_material_clocks, '__func__', None) is not _numeric_module._boundary_methods['_prime_material_clocks']
                or _numeric_module._prime_owned_clocks is not prime_owned_clocks):
            y, x = divmod(position, state.width)
            state._prime_material_clocks(state.cell(x, y))
        else:
            _prime_owned_clocks_impl(state, store, position, context)
    primed = store.journal.changes_since(batch.cursor)
    positions = (frozenset(range(state.width * state.height)) if primed.reset
                 else initial | primed.positions)
    for position in sorted(positions):
        y, x = divmod(position, state.width)
        if (store.exceptions or store._authored_positions
                or store is not getattr(state.cells, 'store', None)
                or getattr(state._sync_material_position, '__func__', None) is not _numeric_module._boundary_methods['_sync_material_position']
                or getattr(state._project_material_arrays, '__func__', None) is not _numeric_module._boundary_methods['_project_material_arrays']
                or context.get('try_sync_position_owned') is not _numeric_module._boundary_dispatch['sync']
                or _numeric_module._project_owned_position is not project_owned_position):
            state._sync_material_position(x, y, prime=False, _index_current=True)
        else:
            _sync_owned_position_impl(state, x, y, store, False, True, context)
    if (initial and state._material_grid_on
            and getattr(state, '_material_grid', None) is None):
        from .material_grid import MaterialGrid
        try:
            state._material_grid = MaterialGrid.from_cells(state.cells, state.width, state.height)
            state._material_grid_error = ''
        except ValueError as error:
            state._material_grid_error = str(error)
    state._material_index_cursor = primed.cursor
    state._material_index_projection = (
        primed.cursor, state.time, getattr(state, '_material_step', 0), positions)
    return True


def sync_owned_position(state, x, y, store, prime, index_current, context):
    _sync_owned_position_impl(state, x, y, store, prime, index_current, context)
    return True

cdef void _sync_owned_position_impl(object self, object x, object y, object store,
                                   bint prime, bint _index_current, dict context) except *:
    LIQUID_DEFINITIONS = context['LIQUID_DEFINITIONS']
    GAS_DEFINITIONS = context['GAS_DEFINITIONS']
    wall_def = context['wall_def']
    if not _index_current:
        if not _ensure_owned_index_impl(self, store, context):
            self._ensure_material_index()
        store = getattr(self.cells, 'store', None)
        projection = getattr(self, '_material_index_projection', None)
        if (store is not None and projection is not None
                and projection[:3] == (store.journal.cursor, self.time,
                                       getattr(self, '_material_step', 0))
                and y * self.width + x in projection[3]):
            # Ordinary clocks were already primed for this exact final
            # state. Shared clocks retain the legacy explicit caller prime:
            # another source may have removed its key in the same batch.
            clocks = self.cell(x, y).material_clocks
            notifier = getattr(clocks, '_changed', None)
            shared_prime = prime and notifier is not None and len(notifier.owners) > 1
            if not shared_prime:
                return
            if (store.exceptions or store._authored_positions
                    or getattr(self._prime_material_clocks, '__func__', None) is not _numeric_module._boundary_methods['_prime_material_clocks']
                    or _numeric_module._prime_owned_clocks is not prime_owned_clocks):
                self._prime_material_clocks(self.cell(x, y))
            else:
                _prime_owned_clocks_impl(self, store, y * self.width + x, context)
            if store.journal.cursor == projection[0]:
                return
            prime = False
    if hasattr(self, 'ui_dirty'):
        self.material_revision += 1
        self.ui_revision += 1
        self.ui_dirty.update(('body', 'status'))
    position = (x, y)
    cell = self.cell(x, y)
    if prime:
        if (store is None or store.exceptions or store._authored_positions
                or getattr(self._prime_material_clocks, '__func__', None) is not _numeric_module._boundary_methods['_prime_material_clocks']
                or _numeric_module._prime_owned_clocks is not prime_owned_clocks):
            self._prime_material_clocks(cell)
        else:
            _prime_owned_clocks_impl(self, store, y * self.width + x, context)
    store = getattr(self.cells, 'store', None)
    if store is not None and not store.exceptions:
        if (getattr(self._project_material_arrays, '__func__', None) is not _numeric_module._boundary_methods['_project_material_arrays']
                or _numeric_module._project_owned_position is not project_owned_position):
            self._project_material_arrays(x, y, store)
        else:
            _project_owned_position_impl(self, x, y, store, context)
        return
    liquid_definition = LIQUID_DEFINITIONS.get(cell.liquid_kind) if cell.liquid > 0 else None
    gas_definition = GAS_DEFINITIONS.get(cell.gas_kind) if cell.gas > 0 else None
    ventilation = exhaust = False
    if cell.solid and cell.integrity > 0:
        wall = wall_def(cell.wall_kind)
        ventilation = bool(wall.gas_push_direction)
        exhaust = wall.gas_dissipation_multiplier > 1
    active_flags = (
        ("_liquid_cells", cell.liquid > 0),
        ("_gas_cells", cell.gas > 0),
        ("_periodic_liquid_cells", liquid_definition is not None
         and liquid_definition.evaporation_period > 0),
        ("_periodic_gas_cells", gas_definition is not None
         and gas_definition.dissipation_period > 0),
        ("_flame_cells", cell.flame > 0),
        ("_phase_cells", self._cell_in_phase_index(cell)),
        ("_special_cells", cell.wall_kind in self._SPECIAL_WALL_KINDS),
        ("_ventilation_cells", ventilation),
        ("_exhaust_cells", exhaust),
    )
    for key, active in active_flags:
        bucket = getattr(self, key)
        if active:
            bucket.add(position)
        else:
            bucket.discard(position)
    if getattr(self, "_material_dirty_on", False):
        self._wake_material_region(x, y)
        self._sync_gas_channels(position, cell)
    mirror = getattr(self, '_material_grid', None)
    if mirror is not None:
        try:
            mirror.sync_cell(x, y, cell)
        except ValueError as error:
            self._material_grid = None
            self._material_grid_error = str(error)


from . import material_grid as _grid_module
from . import material_numeric as _numeric_module
_grid_class = _grid_module.MaterialGrid
_grid_sync_reference = _grid_class.sync_cell
_grid_owned_reference = _grid_class._sync_owned
_grid_index_reference = _grid_class.index
_grid_matches_reference = _grid_class.matches
_stage_owned_cell_class = _numeric_module._BASE_OWNED_CELL
from .material_store import MaterialStore as _store_class, CellField as _field_class
_store_write_reference = _store_class.write
_field_set_reference = _field_class.__set__
_field_get_reference = _field_class.__get__
# Mapping proxies stay live across class dictionary edits. Retain this view to
# avoid allocating another proxy on every scalar read, while checking actual
# descriptor identity, mutable name and getter policy at each access below.
_stage_field_dictionary = _stage_owned_cell_class.__dict__
_stage_field_references = dict(_stage_field_dictionary)
_stage_field_class_dictionary = _field_class.__dict__


cdef void _stage_sync_position(object state, object x, object y) except *:
    """Stay native between commits, checking live hooks at every boundary."""
    cdef object store = getattr(state.cells, 'store', None)
    cdef object name, function
    from . import materials_sim
    if (store is None or not _numeric_module._owned_boundary_enabled(store)
            or store._authored_positions
            or (_numeric_module._prime_owned_clocks,
                _numeric_module._project_owned_position,
                _numeric_module._sync_owned_grid) != _numeric_module._boundary_kernels
            or _numeric_module._sync_owned_position is not sync_owned_position
            or materials_sim.try_sync_position_owned is not _numeric_module._boundary_dispatch['sync']):
        state._sync_material_position(x, y)
        return
    for name, function in _numeric_module._boundary_methods.items():
        if getattr(getattr(state, name), '__func__', None) is not function:
            state._sync_material_position(x, y)
            return
    _sync_owned_position_impl(state, x, y, store, True, False, materials_sim.__dict__)


cdef inline bint _stage_field_matches(object field):
    cdef object descriptor = _stage_field_dictionary.get(field)
    return (descriptor is _stage_field_references[field]
            and type(descriptor) is _field_class
            and type(descriptor.name) is str and descriptor.name == field)


cdef void _stage_owner_write(object store, object cell, Py_ssize_t position,
                            object field, object value) except *:
    """Commit an ordinary scalar to its owner and publish the original event.

    Captured cells may detach during callbacks. Hooks, descriptors and sparse
    values are checked for each individual write, including between tuple
    targets. Anything outside this exact scalar contract uses Cell assignment.
    """
    cdef object code, low, high
    if (not _stage_binding_matches(store, cell, position)
            or type(store) is not _store_class
            or getattr(store.write, '__func__', None) is not _store_write_reference
            or _field_class.__set__ is not _field_set_reference
            or not _stage_field_matches(field)
            or _stage_owned_cell_class.__setattr__ is not object.__setattr__):
        setattr(cell, field, value)
        return
    if field in store.numeric_fields:
        code = store.typecodes[field]
        low, high = ((0, 256) if code == 'B' else
                     (-32768, 32768) if code == 'h' else (-(2**63), 2**63))
        if not (type(value) is int and low <= value < high):
            setattr(cell, field, value)
            return
    elif (type(value) is not str or type(store.columns[field][position]) is not str
          or (position, field) in store._mutable_owners):
        setattr(cell, field, value)
        return
    store.columns[field][position] = value
    store.journal.record(position, field)


# A captured recipe grid can remain bound to its old store; a detached Cell
# owns standalone fields. Validate the actual reference rather than current map.
cdef inline bint _stage_binding_matches(object store, object cell, Py_ssize_t position):
    cdef object binding
    if type(cell) is not _stage_owned_cell_class or store.exceptions:
        return False
    binding = cell.__dict__.get('_material_binding')
    return (binding is not None and binding[0] is store and binding[1] == position)

cdef inline object _stage_u8_read(object store, object cell, Py_ssize_t position,
                                 object field, const unsigned char[::1] column):
    if (_stage_binding_matches(store, cell, position) and _stage_field_matches(field)
            and _stage_field_class_dictionary.get('__get__') is _field_get_reference):
        return column[position]
    return getattr(cell, field)

cdef inline object _stage_i64_read(object store, object cell, Py_ssize_t position,
                                  object field, const long long[::1] column):
    if (_stage_binding_matches(store, cell, position) and _stage_field_matches(field)
            and _stage_field_class_dictionary.get('__get__') is _field_get_reference):
        return column[position]
    return getattr(cell, field)

cdef inline object _stage_object_read(object store, object cell, Py_ssize_t position,
                                     object field, object column):
    if (_stage_binding_matches(store, cell, position) and _stage_field_matches(field)
            and _stage_field_class_dictionary.get('__get__') is _field_get_reference):
        return column[position]
    return getattr(cell, field)
