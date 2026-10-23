"""Locked local clinical casts, with finite gas, fluid and summon budgets."""
from ..data.hospital import HOSPITAL_FLOOR_POOLS, HOSPITAL_STRONG_IDS


def spawn_hospital_encounters(state, depth, rng):
    if depth == 5:
        x, y = state.realm_features['core_anchor']
        enemy = state.add_defined_enemy('hospital.core_sterile_grace', x, y)
        enemy.active_skill_state['max_integrity'] = enemy.integrity
        enemy.active_skill_state['infusion_slots'] = state.realm_features.get('infusion_slots', _local_open(state, enemy, 3))
        return
    from collections import deque
    spawn = (state.player.x, state.player.y)
    reachable, queue = {spawn}, deque([spawn])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            p = x+dx, y+dy
            if (0 <= p[0] < state.width and 0 <= p[1] < state.height
                    and p not in reachable and not state.cell(*p).solid):
                reachable.add(p)
                queue.append(p)
    facility = {(e.x, e.y) for e in getattr(state, '_pending_realm_events', ())}
    candidates = sorted(p for p in reachable if p not in facility
                        and max(abs(p[0]-spawn[0]), abs(p[1]-spawn[1])) >= 6
                        and not state.cell(*p).gas and not state.cell(*p).liquid)
    rng.shuffle(candidates)
    count = state._ordinary_anomaly_count((4, 5, 5, 6)[depth-1])
    for index, (x, y) in enumerate(candidates[:count]):
        aid = (rng.choice(HOSPITAL_STRONG_IDS) if depth > 1 and index == 0
               else rng.choice(HOSPITAL_FLOOR_POOLS[depth-1]))
        state.add_defined_enemy(aid, x, y)


def _local_open(state, enemy, limit):
    coords = [(enemy.x+dx, enemy.y+dy) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))]
    return [p for p in coords if state._sk_open(*p)][:limit]


def cast(state, enemy, skill, binding):
    key = skill.skill_id.split('.', 1)[1]
    st = enemy.active_skill_state
    distance = max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y))
    seen = state._has_line_of_sight(enemy.x, enemy.y, state.player.x, state.player.y)
    if key in ('needle', 'scan_line', 'white_cut', 'filament', 'syringe_dash', 'forceps_pull'):
        if not seen or not 1 <= distance <= skill.max_range:
            return None
        path = state._sk_ray(enemy.x, enemy.y, state.player.x, state.player.y,
                             skill.max_range if key == 'filament' else skill.max_cells)
        if key == 'filament':
            path = path[-2:]
        if not path:
            return None
        return path, path, None, {}
    if key == 'blade_arc':
        if distance > 3 or not seen:
            return None
        px, py = state.player.x, state.player.y
        horizontal = abs(px-enemy.x) < abs(py-enemy.y)
        cells = [(px+i if horizontal else px, py if horizontal else py+i) for i in (-1, 0, 1)]
        cells = [p for p in cells if state._sk_open(*p) and state._has_line_of_sight(enemy.x, enemy.y, *p)]
        return cells, None, None, {}
    if key in ('spore_dust', 'drip', 'core_infusion'):
        if key == 'core_infusion' and not state.realm_features.get('core_fluid_open', True):
            return None
        cap = 12 if key != 'drip' else 6
        if st.get(key+'_spent', 0) >= cap or distance > skill.max_range or not seen:
            return None
        count = 4 if enemy.catalog_id == 'hospital.spore_crown' else 2 if key == 'spore_dust' else 3
        if key == 'core_infusion':
            cells = st.setdefault('infusion_slots', _local_open(state, enemy, count))
        else:
            cells = _local_open(state, enemy, count)
        kind, medium = ('胞尘', 'gas') if key == 'spore_dust' else ('脑脊液', 'liquid')
        cells = [p for p in cells if state._sk_open(*p)
                 and max(abs(p[0]-enemy.x), abs(p[1]-enemy.y)) <= skill.max_range
                 and (not getattr(state.cell(*p), medium)
                 or getattr(state.cell(*p), medium+'_kind') == kind)]
        if not cells:
            return None
        return cells, None, None, {'medium': medium, 'kind': kind, 'cap': cap}
    if key == 'membrane_guard':
        if enemy.portents.get('sk_guard_fold', 0) or not seen or distance > 3:
            return None
        return [(enemy.x, enemy.y)], None, None, {}
    if key == 'listen':
        if st.get('listen_spent') or enemy.last_seen_x < 0 or enemy.last_seen_y < 0:
            return None
        return [(enemy.x, enemy.y)], None, (enemy.last_seen_x, enemy.last_seen_y), {}
    if key == 'ring_wash':
        if distance > 3:
            return None
        cells = [(enemy.x+dx, enemy.y+dy) for dx, dy in
                 ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (-1, 1), (1, -1), (1, 1))]
        cells = [p for p in cells if state._sk_open(*p) and state._has_line_of_sight(enemy.x, enemy.y, *p)]
        return cells, None, None, {}
    if key == 'reopen':
        if st.get('reopen_spent', 0) >= 2 or distance > skill.max_range:
            return None
        if any(e.integrity > 0 and e.main_id == enemy.id for e in state.enemies):
            return None
        cells = [p for p in _local_open(state, enemy, 5) if state.entity_at(*p) is None]
        if not cells:
            return None
        return cells[:1], None, cells[0], {}
    return None


def resolve(state, enemy, skill, pending):
    key = skill.skill_id.split('.', 1)[1]
    warned = [tuple(p) for p in pending.get('warning_cells', ())]
    st = enemy.active_skill_state
    if key in ('needle', 'white_cut', 'blade_arc', 'scan_line'):
        if key == 'blade_arc':
            reachable = [p for p in warned if state._sk_open(*p)
                         and state._has_line_of_sight(enemy.x, enemy.y, *p)]
        else:
            reachable = []
            for p in warned:
                if not state._sk_open(*p):
                    break
                reachable.append(p)
        state._skill_resolve_default_hit(enemy, skill, dict(pending,
            warning_cells=reachable, locked_path=reachable))
        if key == 'scan_line':
            from .realm_lights import borrow_light, release_light
            if st.get('light_pulse'):release_light(state,st['light_pulse']['pos'],enemy.id+':hospital')
            st['light_pulse'] = {'pos': (enemy.x, enemy.y), 'left': 3}
            borrow_light(state,(enemy.x,enemy.y),enemy.id+':hospital',2)
        return
    if key == 'filament':
        if (state.player.x, state.player.y) in warned and not state._identity_immune('sk_late_beat'):
            state._grant_portent_direct(state.player, 'sk_late_beat')
        return
    if key == 'syringe_dash':
        if state._enemy_rooted(enemy):
            capture=getattr(state,'_cast_fx_capture',None)
            if capture is not None:capture.resolved_path=((enemy.x,enemy.y),)
            return
        reached = []
        for p in warned[:3]:
            if not state._sk_open(*p):
                break
            occupant = state.entity_at(*p)
            reached.append(p)
            if occupant:
                break
            if len(reached) <= 2:
                enemy.x, enemy.y = p
        if (state.player.x, state.player.y) in reached:
            state._enemy_skill_trauma(enemy, state._skill_power(enemy, skill), skill.trauma_channel)
        capture = getattr(state, '_cast_fx_capture', None)
        if capture is not None:
            capture.resolved_path = tuple(reached)
        return
    if key == 'forceps_pull':
        if (state.player.x, state.player.y) in warned and not state._player_control_immune():
            state._skill_push_player(enemy, away=False)
        return
    if key in ('spore_dust', 'drip', 'core_infusion'):
        meta = pending['meta']
        if key == 'core_infusion' and not state.realm_features.get('core_fluid_open', True):
            return
        medium, kind = meta['medium'], meta['kind']
        cap = meta['cap']
        requested = 6 if enemy.catalog_id == 'hospital.spore_crown' or key == 'core_infusion' else 4 if key == 'spore_dust' else 2
        remaining = min(requested, cap-st.get(key+'_spent', 0))
        for index, p in enumerate(warned):
            cell = state.cell(*p)
            if cell.solid or (getattr(cell, medium) and getattr(cell, medium+'_kind') != kind):
                continue
            n = min(remaining, max(1, (remaining+len(warned)-index-1)//(len(warned)-index)), 100-getattr(cell, medium))
            if n <= 0:
                continue
            setattr(cell, medium, getattr(cell, medium)+n)
            setattr(cell, medium+'_kind', kind)
            state._sync_material_position(*p)
            st[key+'_spent'] = st.get(key+'_spent', 0)+n
            remaining -= n
            if not remaining:
                break
        return
    if key == 'membrane_guard':
        state._apply_direct_portent(enemy, 'sk_guard_fold', 3)
        return
    if key == 'listen':
        target = pending.get('target_cell')
        if not target:
            return
        for other in state._sk_allies_near(enemy, 6):
            other.last_seen_x, other.last_seen_y = target
            other.alert_state = '警戒'
        st['listen_spent'] = 1
        return
    if key == 'ring_wash':
        for holder in (state.player, *state.enemies):
            if holder.integrity > 0 and (holder.x, holder.y) in warned:
                state.shorten_portent(holder, 3)
                if holder is state.player:
                    state._enemy_skill_trauma(enemy, 5, '心智')
                elif holder is not enemy:
                    holder.integrity = max(0, holder.integrity-5)
        return
    if key == 'reopen':
        p = tuple(pending['target_cell'])
        if state.cell(*p).solid or state.entity_at(*p) or st.get('reopen_spent', 0) >= 2:
            return
        child = state.add_defined_enemy('hospital.membrane', *p, integrity=6, dissolution_reward=0, drop_id=None)
        child.main_id, child.mind_trauma, child.attack_time = enemy.id, 3, 1.4
        child.active_skill_state['summon_no_reward'] = True
        child.active_skill_state['strike_power'] = 3
        child.alert_state = '追踪'
        st['reopen_spent'] = st.get('reopen_spent', 0)+1


def tick_light_pulses(state, amount):
    for enemy in state.enemies:
        pulse = enemy.active_skill_state.get('light_pulse')
        if not pulse:
            continue
        pulse['left'] -= amount
        if pulse['left'] <= 0:
            from .realm_lights import release_light
            release_light(state,pulse['pos'],enemy.id+':hospital')
            enemy.active_skill_state.pop('light_pulse')
            state._visible_cache = None
