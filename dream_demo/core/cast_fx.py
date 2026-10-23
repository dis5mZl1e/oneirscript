"""Transient, read-only effect observations; replay never performs game actions."""
from functools import wraps
from ..data.cast_fx import ABILITY_FX, ITEM_EFFECT_FX, CastVisual, skill_visual
from ..data.anomaly_skills import effective_skill_def


_CELL_FIELDS = ('floor', 'solid', 'integrity', 'liquid', 'liquid_kind', 'gas',
                'gas_kind', 'flame', 'aggregate_variant', 'wall_kind', 'elevation',
                'plant', 'wire', 'light_on')


def _effect_snapshot(state):
    cells = {(x, y): tuple(getattr(c, name) for name in _CELL_FIELDS)
             for y, row in enumerate(state.cells) for x, c in enumerate(row)}
    actors = {}
    for actor in [state.player, *state.enemies]:
        actors[actor.id] = ((actor.x, actor.y), actor.integrity,
                            tuple(sorted(actor.portents.items())),
                            actor.frozen_turns, actor.blind_turns, actor.slow_turns, actor.alert_state,
                            actor.last_seen_x, actor.last_seen_y)
    return cells, actors, frozenset(state.developed_cells.get(str(state.depth), ()))


class EffectCapture:
    """Exclude world simulation from observed use/cast changes."""
    def __init__(self, state):
        self.state = state
        self.baseline = _effect_snapshot(state)
        self.cells = set()
        self.resolved_path = None
        self.resolved_area = None

    def checkpoint(self):
        current = _effect_snapshot(self.state)
        old_cells, old_actors, old_developed = self.baseline
        self.cells.update(p for p, value in current[0].items() if old_cells.get(p) != value)
        for key, value in current[1].items():
            if old_actors.get(key) != value:
                self.cells.add(value[0])
                if key in old_actors:
                    self.cells.add(old_actors[key][0])
        self.cells.update(old_actors[key][0] for key in old_actors.keys()-current[1].keys())
        self.cells.update(current[2] - old_developed)
        self.baseline = current


def pause_fx_world_step(fn):
    @wraps(fn)
    def run(state, *args, **kwargs):
        capture = getattr(state, '_cast_fx_capture', None)
        if capture is None:
            return fn(state, *args, **kwargs)
        capture.checkpoint()
        state._cast_fx_capture = None
        try:
            return fn(state, *args, **kwargs)
        finally:
            capture.baseline = _effect_snapshot(state)
            state._cast_fx_capture = capture
    return run


def _observe(state, fn, args, kwargs, visual, cast_id, source, *, source_id=None,
             path=(), planned=(), projectile=False, center=None):
    if visual is None:
        return fn(state, *args, **kwargs)
    capture = EffectCapture(state)
    previous = getattr(state, '_cast_fx_capture', None)
    state._cast_fx_capture = capture
    layer = (state.depth, state.realm_id, state.realm_depth)
    try:
        result = fn(state, *args, **kwargs)
        capture.checkpoint()
    finally:
        if previous is None:
            state.__dict__.pop('_cast_fx_capture', None)
        else:
            state._cast_fx_capture = previous
    success = result is None or isinstance(result, tuple) or result.changed
    if visual and success and layer == (state.depth, state.realm_id, state.realm_depth):
        path = tuple(capture.resolved_path if capture.resolved_path is not None else path)
        area = capture.resolved_area if capture.resolved_area is not None else planned
        cells = capture.cells | set(path) | (set(area) if capture.resolved_path is None else set())
        emit_cast(state, visual, cast_id, source, cells or {center or source},
                  path=path, source_id=source_id, center=center, projectile=projectile)
    return result


def emit_cast(state, visual, cast_id, source, cells, *, path=(), source_id=None,
              center=None, projectile=False):
    raw = getattr(state, 'last_projectile', None) or {}
    state._emit_combat_fx('cast', center or source, cells,
        profile=visual.profile, motion=visual.motion, theme=visual.theme,
        source=source, source_id=source_id, path=path, cast_id=cast_id,
        projectile_seq=raw.get('seq') if projectile else None)


def animate_ability(fn):
    @wraps(fn)
    def run(state, ability_id, *args, **kwargs):
        visual = ABILITY_FX.get(ability_id)
        if visual is None:
            return fn(state, ability_id, *args, **kwargs)
        return _observe(state, fn, (ability_id, *args), kwargs, visual,
                        'ability:'+ability_id, (state.player.x, state.player.y),
                        source_id=state.player.id)
    return run


def animate_consumable(fn):
    @wraps(fn)
    def run(state, item, *args, **kwargs):
        return _observe(state, fn, (item, *args), kwargs, ITEM_EFFECT_FX.get(item.effect),
                        'item:'+item.definition_id, (state.player.x, state.player.y),
                        source_id=state.player.id)
    return run


def animate_item_action(effect):
    """Special confirmed actions; opening a selector never enters this hook."""
    def decorate(fn):
        @wraps(fn)
        def run(state, index=0, *args, **kwargs):
            item = state.inventory[index] if 0 <= index < len(state.inventory) else None
            if item is None or item.effect != effect:
                return fn(state, index, *args, **kwargs)
            return _observe(state, fn, (index, *args), kwargs, ITEM_EFFECT_FX[effect],
                            'item:'+item.definition_id, (state.player.x, state.player.y))
        return run
    return decorate


def animate_legacy(kind, profile, motion):
    def decorate(fn):
        @wraps(fn)
        def run(state, enemy, *args, **kwargs):
            source, path, center = (enemy.x, enemy.y), (), None
            if kind == 'ranged':
                distance = max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y))
                path = tuple(state._sk_ray(enemy.x, enemy.y, state.player.x, state.player.y, distance))
            if kind == 'ignite' and args:
                center = state._skill_anchor(enemy, args[0].get('anchor', 'self'))
            return _observe(state, fn, (enemy, *args), kwargs, CastVisual(profile, motion),
                            'legacy:'+kind, source, source_id=enemy.id, path=path, center=center)
        return run
    return decorate


def animate_landing(fn):
    @wraps(fn)
    def run(state, item, x, y):
        raw = getattr(state, 'last_projectile', None) or {}
        source = tuple(raw.get('origin') or (state.player.x, state.player.y))
        visual = CastVisual('field', 'drip', 'hospital') if item.definition_id == 'hospital.sealed_ampoule' else ITEM_EFFECT_FX.get(item.effect)
        # Throwing a recovery item merely drops it; it does not use the medicine.
        if item.effect not in ('explosion', 'fireburst', 'tar_burst', 'spark_rays', 'ignite_burst', 'smoke_cloud', 'sound_lure') and item.definition_id != 'hospital.sealed_ampoule':
            return fn(state, item, x, y)
        return _observe(state, fn, (item, x, y), {}, visual,
                        'item:'+item.definition_id, source, center=(x, y),
                        projectile=True, planned=((x, y),))
    return run


def animate_skill_resolution(fn):
    @wraps(fn)
    def run(state, enemy, pending):
        skill = effective_skill_def(pending['skill_id'], enemy.catalog_id)
        source = (enemy.x, enemy.y)
        path = tuple(tuple(p) for p in pending.get('locked_path', ()))
        return _observe(state, fn, (enemy, pending), {}, skill_visual(skill),
                        'skill:'+skill.skill_id, source, source_id=enemy.id,
                        path=path, planned=tuple(tuple(p) for p in pending.get('warning_cells', ())))
    return run


def animate_hospital_tool(fn):
    @wraps(fn)
    def run(state, index, tx=None, ty=None):
        if not 0 <= index < len(state.inventory):
            return fn(state, index, tx, ty)
        item = state.inventory[index]
        center = (state.player.x if tx is None else tx, state.player.y if ty is None else ty)
        return _observe(state, fn, (index, tx, ty), {}, ITEM_EFFECT_FX['hospital_tool'],
                        'item:'+item.definition_id, (state.player.x, state.player.y),
                        center=center, planned=(center,))
    return run


def animate_medicine(fn):
    @wraps(fn)
    def run(state, event, choice):
        item = next((i for i in state.inventory if i.instance_id == choice.get('instance')), None)
        if item is None:
            return fn(state, event, choice)
        return _observe(state, fn, (event, choice), {}, ITEM_EFFECT_FX.get(item.effect),
                        'item:'+item.definition_id, (state.player.x, state.player.y))
    return run


def charging_casts(state):
    casts = []
    for enemy in state.enemies:
        if enemy.integrity <= 0:
            continue
        skill_state = enemy.active_skill_state or {}
        pending = skill_state.get('pending')
        if pending:
            skill = effective_skill_def(pending['skill_id'], enemy.catalog_id)
            visual = skill_visual(skill)
            total = max(1., float(skill.windup_rounds))
            casts.append(dict(stage='charge', source=(enemy.x, enemy.y),
                cells=tuple(tuple(p) for p in pending.get('warning_cells', ())) or ((enemy.x, enemy.y),),
                path=tuple(tuple(p) for p in pending.get('locked_path', ())),
                profile=visual.profile, motion=visual.motion, theme=visual.theme,
                progress=max(0., min(1., 1-float(pending.get('windup_left', 0))/total))))
        second = skill_state.get('library_second_beat')
        if second:
            # The first release clears pending, but the locked second segment
            # still waits for a world action and keeps its static telegraph.
            visual = skill_visual(effective_skill_def('library.last_page', enemy.catalog_id))
            cells = tuple(tuple(p) for p in second.get('cells', ()))
            casts.append(dict(stage='charge', source=(enemy.x, enemy.y),
                cells=cells, path=cells, profile=visual.profile,
                motion=visual.motion, theme=visual.theme, progress=1.))
        if enemy.aoe_charge > 0:
            spec = next((s for s in state._skill_specs(enemy) if s.get('kind') == 'aoe_burst'), {})
            radius = int(spec.get('radius', 2))
            center = (enemy.aoe_tx, enemy.aoe_ty)
            cells = tuple((x, y) for y in range(center[1]-radius, center[1]+radius+1)
                          for x in range(center[0]-radius, center[0]+radius+1)
                          if state.inside_board(x, y))
            casts.append(dict(stage='charge', source=(enemy.x, enemy.y), cells=cells, path=(),
                              profile='blast', motion='blast', theme='',
                              progress=max(0., 1-enemy.aoe_charge/max(1., spec.get('windup', 2)))))
    for x, y, fuse, radius, power in getattr(state, 'enemy_bombs', ()):
        casts.append(dict(stage='charge', source=(x, y), cells=((x, y),), path=(),
                          profile='blast', motion='blast', theme='', progress=1/(1+max(0., fuse))))
    return casts
