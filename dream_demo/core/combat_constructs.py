"""§13 战斗构想：瞄准草稿、真实弹道与一次性支付。

数据侧只认 ``ABILITY_DEFINITIONS[*]['combat']``。打开瞄准不经过这里；
``release`` 只在玩家确认后调用，先复核目标几何，再支付、再让真实的弹道／
投掷／范围结算落地。取消、换目标、资源不足都在支付之前返回。
"""
from __future__ import annotations

import math

from ..data.abilities import ABILITY_DEFINITIONS
from ..i18n import tr
from . import construct_environments
from .ballistics import angle_blocked
from .constants import ActionKind
from .entities import ActionResult

FORM_MELEE = 'melee'
FORM_LAUNCH = 'launch'
FORM_THROW = 'throw'
FORM_AREA = 'area'

DELAYED_SHELL_CAP = 2
NEEDLE_DAMAGE = (3, 2, 1)
NEEDLE_WALL_BUDGET = 4


def meta(ability_id: str) -> dict:
    return dict(ABILITY_DEFINITIONS.get(ability_id, {}).get('combat') or {})


def is_combat(ability_id: str) -> bool:
    return bool(meta(ability_id))


def form_of(ability_id: str) -> str:
    return str(meta(ability_id).get('form') or '')


def aim_range(state, ability_id: str) -> int:
    base = int(meta(ability_id).get('range') or 1)
    if form_of(ability_id) not in (FORM_LAUNCH, FORM_THROW):
        return base
    from ..equipment.expansion_runtime import construct_range_bonus
    return base + construct_range_bonus(state)


def default_direction(state) -> tuple[int, int]:
    dx, dy = state.facing or (1, 0)
    if dx == 0 and dy == 0:
        dx = 1
    return int(dx), int(dy)


def normalize_target(target):
    if target is None:
        return None
    if hasattr(target, 'x') and hasattr(target, 'y'):
        return int(target.x), int(target.y)
    return int(target[0]), int(target[1])


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def _direction(state, target, direction):
    point = normalize_target(target)
    if direction is not None:
        dx, dy = int(direction[0]), int(direction[1])
        if dx or dy:
            return _sign(dx), _sign(dy)
    if point is not None:
        dx = point[0] - state.player.x
        dy = point[1] - state.player.y
        if dx or dy:
            return _sign(dx), _sign(dy)
    return default_direction(state)


def _pay(state, ability_id: str, definition: dict) -> None:
    from ..equipment.expansion_runtime import adjust_construct_cost
    cost = adjust_construct_cost(
        state, ability_id, state._scaled_ability_cost(int(definition['cost'])))
    state._pay_ability_cost(cost)
    cooldown = state._scaled_ability_cooldown(int(definition['cooldown']))
    state.ability_cooldowns[ability_id] = cooldown


def _spend_use(state) -> None:
    state._action_time(1, ActionKind.USE)


def _sound(state, x: int, y: int, radius: int) -> None:
    if radius > 0:
        from ..equipment.expansion_runtime import relocate_construct_sound
        x, y = relocate_construct_sound(state, x, y)
        state._sound_pulse(x, y, radius, by_player=True)


def _continue_budget(state, origin, dx, dy, budget: int) -> int:
    """风幕：同一条弹道只扣一次 2 格剩余射程。"""
    if budget <= 0:
        return 0
    cells = construct_environments.screen_cells(state)
    if not cells:
        return budget
    x, y = origin
    for _ in range(budget):
        x, y = x + dx, y + dy
        if (x, y) in cells:
            return max(0, budget - 2)
    return budget


def trim_path(state, path):
    """真实弹体穿过逆风幕：整段飞行只损失 2 格剩余射程。"""
    cells = construct_environments.screen_cells(state)
    if cells and any(tuple(point) in cells for point in path):
        return list(path[:-2]) if len(path) > 2 else []
    return list(path)


def _throw_valid(state, point, max_range: int, *,
                 require_visible: bool = True) -> tuple[bool, str]:
    x, y = point
    if not state.inside_board(x, y):
        return False, '那里没有落脚点。'
    if (x, y) == (state.player.x, state.player.y):
        return False, '那个落点就在脚下。'
    if max(abs(x - state.player.x), abs(y - state.player.y)) > max_range:
        return False, '那个落点超出了射程。'
    from .throwing import is_valid_target
    return is_valid_target(state,x,y,max_range=max_range,require_visible=require_visible)


def preview(state, ability_id: str, target=None, direction=None) -> dict:
    """只读草稿预览：供瞄准栏显示范围、落点与自伤风险。"""
    from . import throwing
    form = form_of(ability_id)
    point = normalize_target(target)
    dx, dy = _direction(state, target, direction)
    data = dict(form=form, target=point, direction=(dx, dy),
                range=aim_range(state, ability_id), cells=(), landing=None,
                self_risk='')
    if form == FORM_AREA:
        shape = str(meta(ability_id).get('shape') or '')
        if shape == 'ring3':
            data['cells'] = _ring_cells(state, state.player.x, state.player.y, 3)
        elif shape == 'ring2':
            data['cells'] = _ring_cells(state, state.player.x, state.player.y, 2)
        else:
            data['cells'] = _screen_cells(state, dx, dy)
        if ability_id == 'combat.paper_blades':
            data['self_risk'] = '刃环也会割伤自己。'
        return data
    if form == FORM_THROW:
        if point is None:
            point = throwing.directional_landing(
                state, dx, dy, max_range=aim_range(state, ability_id),known_only=True)
        data['landing'] = point
        data['cells'] = (point,)
        trace=throwing.trace_throw(state,*point,known_only=True)
        data['path']=trace.path
        data['uncertain']=trace.uncertain
        data['valid'],data['reason']=_throw_valid(state,point,aim_range(state,ability_id))
        return data
    if form == FORM_MELEE:
        if meta(ability_id).get('targeting') == 'arc':
            data['cells'] = _arc_cells(state, dx, dy)
        elif point is not None:
            data['cells'] = (point,)
        return data
    budget = _continue_budget(state, (state.player.x, state.player.y),
                              dx, dy, aim_range(state, ability_id))
    x, y = state.player.x, state.player.y
    cells = []
    for _ in range(budget):
        x, y = x + dx, y + dy
        if not state.inside_board(x, y):
            break
        cells.append((x, y))
        if state.cell(x, y).solid:
            break
    data['cells'] = tuple(cells)
    return data


# ---------------------------------------------------------------------------
# 近战
# ---------------------------------------------------------------------------

def _melee_corner_blocked(state, target):
    px, py = state.player.x, state.player.y
    dx, dy = target[0]-px, target[1]-py
    if not (dx and dy):
        return False
    sides = ((px+dx, py), (px, py+dy))
    solid = {point: not state.inside_board(*point) or state.cell(*point).solid
             for point in sides}
    return angle_blocked(solid, px, py, dx, dy)


def _arc_cells(state, dx: int, dy: int):
    px, py = state.player.x, state.player.y
    if dx and dy:
        cells = ((px + dx, py + dy), (px + dx, py), (px, py + dy))
    else:
        cells = ((px + dx, py + dy), (px + dx - dy, py + dy + dx),
                 (px + dx + dy, py + dy - dx))
    return tuple(cell for cell in cells if state.inside_board(*cell)
                 and not _melee_corner_blocked(state, cell))


def cross_step_landings(state, target) -> tuple[tuple[int, int], ...]:
    """借位可选落点：与玩家和目标都相邻的合法空格（目标格本身除外）。"""
    point = normalize_target(target)
    if point is None:
        return ()
    px, py = state.player.x, state.player.y
    options = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if not (dx or dy):
                continue
            x, y = px + dx, py + dy
            if not state.inside_board(x, y) or (x, y) == point:
                continue
            if max(abs(x - point[0]), abs(y - point[1])) > 1:
                continue
            if state.cell(x, y).solid or state.entity_at(x, y) is not None:
                continue
            options.append((x, y))
    return tuple(sorted(options, key=lambda cell: (cell[1], cell[0])))


def _cross_step_landing(state, target) -> tuple[int, int] | None:
    options = cross_step_landings(state, target)
    return options[0] if options else None


def _interrupt_windup(state, enemy) -> bool:
    st = getattr(enemy, 'active_skill_state', None)
    if not isinstance(st, dict):
        st = state._skill_state(enemy)
    changed = False
    if isinstance(st.get('pending'), dict):
        st.pop('pending', None)
        changed = True
    if int(getattr(enemy, 'aoe_charge', 0) or 0) > 0:
        enemy.aoe_charge = 0
        changed = True
    if changed:
        st['recover_until'] = max(float(st.get('recover_until', 0) or 0),
                                  float(state.time) + 1)
    return changed


def _melee_plan(state, enemy):
    plan = state.equipment.plan_action('melee', target=enemy)
    return plan if plan.valid else None


def _release_melee(state, ability_id: str, definition: dict, target, direction,
                   landing=None):
    explicit = target is not None
    point = normalize_target(target)
    targeting = str(meta(ability_id).get('targeting') or 'single')
    if targeting == 'arc':
        dx, dy = _direction(state, target, direction)
        cells = _arc_cells(state, dx, dy)
        plan = _melee_plan(state, None)
        base = 1.0 + (float(plan.damage_increment) if plan else 0.0)
        damage = max(1, int(math.ceil(0.7 * base)))
        _pay(state, ability_id, definition)
        hit = 0
        for enemy in list(state.enemies):
            if (enemy.integrity <= 0 or enemy.relation == '稳定意识'
                    or (enemy.x, enemy.y) not in cells):
                continue
            state._player_strike(
                enemy, 'melee', damage=damage, normal_melee=True,
                attack_dir=(_sign(enemy.x - state.player.x),
                            _sign(enemy.y - state.player.y)))
            hit += 1
            if enemy.integrity <= 0:
                state._resolve_enemy(enemy)
        state._spend_attack_time(plan.base_time if plan else 1.0, aptitude='melee')
        source = cells[0] if cells else (state.player.x, state.player.y)
        _sound(state, *source, int(meta(ability_id).get('sound') or 3))
        message = (tr('横切扫过 {n} 个目标。', n=hit) if hit
                   else tr('横切掠过三格——没有碰到目标。'))
        state.messages.append(message)
        state._note_board_conceive(ability_id)
        return ActionResult(True, message, {'ability': ability_id, 'hits': hit})

    if point is None:
        dx, dy = _direction(state, None, direction)
        point = (state.player.x + dx, state.player.y + dy)
    enemy = state.entity_at(*point)
    if enemy is not None:
        if enemy.relation == '稳定意识':
            return ActionResult(False, tr('稳定意识不在这次构想的对象里。'))
        if _melee_corner_blocked(state, point):
            return ActionResult(False, tr('斜角被两堵墙夹住了。'))
    if explicit:
        if not state.inside_board(*point) or max(
                abs(point[0] - state.player.x), abs(point[1] - state.player.y)) != 1:
            return ActionResult(False, tr('选择一个相邻的目标。'))
        if enemy is None or enemy is state.player:
            return ActionResult(False, tr('那里没有可以攻击的目标。'))
    chosen = None
    if ability_id == 'combat.cross_step' and enemy is not None:
        options = cross_step_landings(state, point)
        if landing is not None:
            chosen = normalize_target(landing)
            if chosen not in options:
                return ActionResult(False, tr('预选的借位落点已经失效。'))
        elif explicit or options:
            chosen = options[0] if options else None
        if explicit and chosen is None:
            return ActionResult(False, tr('附近没有可供借位的合法空格。'))
    plan = _melee_plan(state, enemy) if enemy is not None else None
    interrupted = False
    if explicit or enemy is not None:
        _pay(state, ability_id, definition)
        if enemy is not None:
            state._player_strike(
                enemy, 'melee', segments=plan.segments if plan else 1, damage=1,
                attack_dir=(point[0] - state.player.x, point[1] - state.player.y),
                normal_melee=True, action_plan=plan)
            if ability_id == 'combat.beat_cut':
                interrupted = _interrupt_windup(state, enemy)
            if enemy.integrity <= 0:
                state._resolve_enemy(enemy)
        if chosen is not None:
            state.player.x, state.player.y = chosen
        state._spend_attack_time(plan.base_time if plan else 1.0, aptitude='melee')
        if interrupted and enemy is not None:
            # 蓄势在耗时前取消（不能让它抢在打断前出手），恢复期从动作结束后算。
            skill_state = (enemy.active_skill_state
                           if isinstance(enemy.active_skill_state, dict)
                           else state._skill_state(enemy))
            skill_state['recover_until'] = max(
                float(skill_state.get('recover_until', 0) or 0),
                float(state.time) + 1)
    else:
        # 空挥：没有相邻目标时仍可合法挥出，费用与耗时照常。
        _pay(state, ability_id, definition)
        state._spend_attack_time(1.0, aptitude='melee')
    _sound(state, state.player.x, state.player.y, int(meta(ability_id).get('sound') or 3))
    if ability_id == 'combat.beat_cut':
        message = (tr('截拍打断了它的蓄势。') if interrupted
                   else tr('截拍挥出——目标没有可打断的动作。'))
    elif ability_id == 'combat.cross_step':
        message = (tr('借位：一击之后落到了侧后的空格。') if chosen
                   else tr('借位挥出——没有可供侧移的落点。'))
    else:
        message = tr('你对相邻的目标挥出一次近战。') if enemy else tr('近战构想挥空了。')
    state.messages.append(message)
    state._note_board_conceive(ability_id)
    return ActionResult(True, message, {
        'ability': ability_id, 'hit': enemy.id if enemy else None,
        'landing': list(chosen) if chosen else None,
    })


# ---------------------------------------------------------------------------
# 远程：发射
# ---------------------------------------------------------------------------

def _geometric_bounce(solid, cx, cy, dx, dy):
    if dx and dy:
        side_a = solid.get((cx + dx, cy), True)
        side_b = solid.get((cx, cy + dy), True)
        if side_a and not side_b:
            return -dx, dy
        if side_b and not side_a:
            return dx, -dy
        return -dx, -dy
    return (-dx, 0) if dy == 0 else (0, -dy)


def _wall_blocks_bolt(state, cell, x, y) -> bool:
    from ..materials import wall_def
    return (state.puzzle_projectile_blocked(x, y)
            or bool(wall_def(cell.wall_kind).projectile_immune))


def _release_launch(state, ability_id: str, definition: dict, target, direction):
    point = normalize_target(target)
    if point is not None:
        if not state.inside_board(*point) or point == (state.player.x, state.player.y):
            return ActionResult(False, tr('发射方向无效。'))
        if max(abs(point[0] - state.player.x), abs(point[1] - state.player.y)) > aim_range(state, ability_id):
            return ActionResult(False, tr('那个目标超出了射程。'))
        if not state.is_visible(*point):
            return ActionResult(False, tr('那里看不见，无法锁定。'))
    dx, dy = _direction(state, point, direction)
    state.facing = (dx, dy)
    budget = _continue_budget(state, (state.player.x, state.player.y), dx, dy,
                              aim_range(state, ability_id))
    _pay(state, ability_id, definition)
    if ability_id == 'combat.refracted_bolt':
        message, data = _bolt(state, dx, dy, budget)
    elif ability_id == 'combat.piercing_needle':
        message, data = _needle(state, dx, dy, budget)
    elif ability_id == 'combat.shadow_pin':
        message, data = _shadow_pin(state, dx, dy, budget)
    else:
        message, data = _tow_hook(state, dx, dy, budget)
    _spend_use(state)
    _sound(state, state.player.x, state.player.y, int(meta(ability_id).get('sound') or 3))
    message = tr(definition['name']) + '：' + message
    state.messages.append(message)
    state._note_board_conceive(ability_id)
    data.update(ability=ability_id)
    return ActionResult(True, message, data)


def _bolt(state, dx: int, dy: int, budget: int):
    flight: list[tuple[int, int]] = []
    bounces: list[tuple[int, int, int]] = []
    solid = {(x, y): state.cell(x, y).solid
             for y in range(state.height) for x in range(state.width)}
    cx, cy = state.player.x, state.player.y
    wall_bounces = mirror_bounces = 0
    hit = None
    end_kind, end_cell = 'range', None
    for _ in range(budget):
        x, y = cx + dx, cy + dy
        if not state.inside_board(x, y):
            break
        reflected = construct_environments.reflection(state, x, y, (dx, dy))
        if reflected is not None and mirror_bounces + wall_bounces < 2:
            flight.append((x, y))
            bounces.append((len(flight) - 1, x, y))
            mirror_bounces += 1
            dx, dy = reflected
            cx, cy = x, y
            continue
        cell = state.cell(x, y)
        if cell.solid:
            if (_wall_blocks_bolt(state, cell, x, y)
                    or wall_bounces >= 1 or mirror_bounces + wall_bounces >= 2):
                end_kind, end_cell = 'wall', (x, y)
                break
            dx, dy = _geometric_bounce(solid, cx, cy, dx, dy)
            wall_bounces += 1
            bounces.append((len(flight), x, y))
            continue
        entity = state.entity_at(x, y)
        if entity is state.player:
            flight.append((x, y))
            state._lose_mind(1, combat=True)
            hit, end_kind, end_cell = entity, 'entity', (x, y)
            break
        if entity is not None:
            flight.append((x, y))
            state._player_strike(entity, 'ranged', damage=3,
                                 attack_dir=(dx, dy), repeat_path=flight)
            if entity.integrity <= 0:
                state._resolve_enemy(entity)
            hit, end_kind, end_cell = entity, 'entity', (x, y)
            break
        flight.append((x, y))
        cx, cy = x, y
    state._note_projectile(flight, bounces, kind='shot', color='#cfe8ff',
                           end=end_kind, end_cell=end_cell)
    if hit is state.player:
        return tr('折返的光矢擦到了自己。'), {'self_hit': True}
    if hit is not None:
        return tr('光矢命中了目标。'), {'hit': hit.id}
    if end_kind == 'wall':
        return tr('光矢撞在墙上折落。'), {}
    return tr('光矢飞出射程后消散。'), {}


def _needle(state, dx: int, dy: int, budget: int):
    from ..materials import wall_def
    flight: list[tuple[int, int]] = []
    wall_budget = NEEDLE_WALL_BUDGET
    hits = 0
    end_kind = 'range'
    ended_at = None
    cx, cy = state.player.x, state.player.y
    for _ in range(budget):
        x, y = cx + dx, cy + dy
        if not state.inside_board(x, y):
            break
        cell = state.cell(x, y)
        if cell.solid:
            if _wall_blocks_bolt(state, cell, x, y):
                end_kind, ended_at = 'wall', (x, y)
                break
            resistance = max(1, cell.hardness * cell.thickness)
            cell.integrity = max(0, cell.integrity - 20)
            if cell.integrity == 0:
                state.destroy_wall(x, y, 'ability')
            if resistance > wall_budget:
                end_kind, ended_at = 'wall', (x, y)
                break
            wall_budget -= resistance
            flight.append((x, y))
            cx, cy = x, y
            continue
        entity = state.entity_at(x, y)
        if entity is not None:
            flight.append((x, y))
            damage = NEEDLE_DAMAGE[min(hits, len(NEEDLE_DAMAGE) - 1)]
            if entity is state.player:
                state._lose_mind(damage, combat=True)
            else:
                state._player_strike(entity, 'ranged', damage=damage,
                                     attack_dir=(dx, dy), repeat_path=flight)
                if entity.integrity <= 0:
                    state._resolve_enemy(entity)
            hits += 1
            if entity is state.player or hits >= len(NEEDLE_DAMAGE):
                end_kind, ended_at = 'entity', (x, y)
                break
            cx, cy = x, y
            continue
        flight.append((x, y))
        cx, cy = x, y
    state._note_projectile(flight, [], kind='shot', color='#e8e2ff',
                           end=end_kind, end_cell=ended_at)
    if hits:
        return tr('穿念针穿过了 {n} 个实体。', n=hits), {'hits': hits}
    if end_kind == 'wall':
        return tr('细针钉在了墙上。'), {}
    return tr('细针飞出射程后消散。'), {}


def _legal_backing_wall(state, x: int, y: int) -> bool:
    from ..materials import wall_def
    if not state.inside_board(x, y):
        return False
    cell = state.cell(x, y)
    return (cell.solid and cell.wall_kind != '意识边界'
            and not state.puzzle_projectile_blocked(x, y)
            and not wall_def(cell.wall_kind).projectile_immune)


def _shadow_pin(state, dx: int, dy: int, budget: int):
    flight: list[tuple[int, int]] = []
    end_kind, ended_at = 'range', None
    hit = None
    cx, cy = state.player.x, state.player.y
    for _ in range(budget):
        x, y = cx + dx, cy + dy
        if not state.inside_board(x, y):
            break
        cell = state.cell(x, y)
        if cell.solid:
            end_kind, ended_at = 'wall', (x, y)
            break
        entity = state.entity_at(x, y)
        if entity is not None:
            flight.append((x, y))
            end_kind, ended_at, hit = 'entity', (x, y), entity
            if entity is state.player:
                state._lose_mind(2, combat=True)
            else:
                state._player_strike(entity, 'ranged', damage=2,
                                     attack_dir=(dx, dy), repeat_path=flight)
                if entity.integrity > 0:
                    if _legal_backing_wall(state, x + dx, y + dy):
                        state._apply_direct_portent(entity, 'sk_rooted', 3)
                    else:
                        entity.slow_turns = max(float(entity.slow_turns or 0), 2.0)
                if entity.integrity <= 0:
                    state._resolve_enemy(entity)
            break
        flight.append((x, y))
        cx, cy = x, y
    state._note_projectile(flight, [], kind='shot', color='#bfd2c2',
                           end=end_kind, end_cell=ended_at)
    if hit is not None and hit is not state.player:
        rooted = int(hit.portents.get('sk_rooted', 0) or 0) > 0
        return (tr('钉影把它钉在了墙上。') if rooted
                else tr('钉影命中了目标，拖慢了它的脚步。')), {'hit': hit.id}
    if end_kind == 'wall':
        return tr('钉影枪钉进了墙里。'), {}
    return tr('钉影枪的空响散在梦里。'), {}


def _tow_hook(state, dx: int, dy: int, budget: int):
    flight: list[tuple[int, int]] = []
    target = None
    cx, cy = state.player.x, state.player.y
    for _ in range(budget):
        x, y = cx + dx, cy + dy
        if not state.inside_board(x, y):
            break
        cell = state.cell(x, y)
        if cell.solid:
            break
        entity = state.entity_at(x, y)
        if entity is not None:
            flight.append((x, y))
            if (entity is not state.player
                    and entity.relation in ('失控意识', '玩偶意识体')
                    and getattr(entity, 'trait', '') != 'staircase'):
                target = entity
            break
        flight.append((x, y))
        cx, cy = x, y
    pulled = 0
    if target is not None:
        previous = (target.x, target.y)
        for x, y in list(reversed(flight[:-1]))[:3]:
            if max(abs(x - previous[0]), abs(y - previous[1])) != 1:
                break
            if (x, y) == (state.player.x, state.player.y):
                break
            if not state.inside_board(x, y) or state.cell(x, y).solid:
                break
            if state.entity_at(x, y) is not None:
                break
            target.x, target.y = x, y
            previous = (x, y)
            pulled += 1
    state._note_projectile(flight, [], kind='shot', color='#d8c39a',
                           end='entity' if target is not None else 'range',
                           end_cell=(target.x, target.y) if target is not None else None)
    if target is None:
        return tr('钩索收回来时什么都没抓住。'), {'pulled': 0}
    return (tr('钩索把它拉近了 {n} 格。', n=pulled) if pulled
            else tr('钩索挂住了它，却拉不动。')), {'hit': target.id, 'pulled': pulled}


# ---------------------------------------------------------------------------
# 远程：投掷
# ---------------------------------------------------------------------------

def _release_throw(state, ability_id: str, definition: dict, target, direction):
    from . import throwing
    explicit = target is not None
    point = normalize_target(target)
    max_range = aim_range(state, ability_id)
    if point is None:
        point = throwing.directional_landing(state, *_direction(state, None, direction),
                                             max_range=max_range)
    valid, reason = _throw_valid(state, point, max_range, require_visible=explicit)
    if not valid:
        return ActionResult(False, tr(reason))
    path = throwing.flight_path((state.player.x, state.player.y), point)
    screen = construct_environments.screen_cells(state)
    if (screen and any(tuple(step) in screen for step in path)
            and max(abs(point[0] - state.player.x),
                    abs(point[1] - state.player.y)) > max(max_range - 2, 0)):
        return ActionResult(False, tr('逆风幕削弱了这次投掷（最远 {n} 格）。',
                                      n=max(max_range - 2, 0)))
    if ability_id == 'combat.delayed_shell':
        live = [field for field in construct_environments.active(state)
                if field['kind'] == 'delayed_shell']
        if len(live) >= DELAYED_SHELL_CAP:
            return ActionResult(False, tr('同层最多保留 2 枚未爆弹——先等旧弹炸开。'))
    dx, dy = _direction(state, point, direction)
    point=throwing.trace_throw(state,*point).landing
    state.facing = (dx, dy)
    _pay(state, ability_id, definition)
    # 先推进离手回合（第 0 回合），再落下世界状态：倒计时与持续场从下一回合起算。
    _spend_use(state)
    if ability_id == 'combat.delayed_shell':
        construct_environments.start_field(
            state, 'delayed_shell', point, (0, 0), cells=(point,), remaining=2)
        _sound(state, state.player.x, state.player.y, int(meta(ability_id).get('sound') or 2))
        _sound(state, *point, int(meta(ability_id).get('landing_sound') or 4))
        message = tr('迟响弹落在 ({x}, {y})，倒计时开始。', x=point[0], y=point[1])
    else:
        amounts = {point: 16}
        for nx, ny in ((point[0] + 1, point[1]), (point[0] - 1, point[1]),
                       (point[0], point[1] + 1), (point[0], point[1] - 1)):
            if state.inside_board(nx, ny):
                amounts[(nx, ny)] = 6
        made = 0
        for (x, y), amount in amounts.items():
            for tx, ty, share in throwing.release_targets(state, x, y, amount):
                state._add_liquid(state.cell(tx, ty), '水', share)
                made += share
        zone = state._conductive_zone(point)
        if zone:
            state._charge_electric_field(zone, source='thunder_orb', origin=point)
        _sound(state, state.player.x, state.player.y, int(meta(ability_id).get('sound') or 2))
        _sound(state, *point, int(meta(ability_id).get('landing_sound') or 4))
        message = tr('雷珠在 ({x}, {y}) 化成一摊导电的水（{n} 点）。', x=point[0], y=point[1], n=made)
    state.messages.append(message)
    state._note_board_conceive(ability_id)
    return ActionResult(True, message, {'ability': ability_id,
                                       'landing': list(point)})


# ---------------------------------------------------------------------------
# 范围
# ---------------------------------------------------------------------------

def _ring_cells(state, cx: int, cy: int, radius: int):
    return construct_environments.ring_cells(state, radius, (cx, cy))


def _screen_cells(state, dx: int, dy: int):
    px, py = state.player.x, state.player.y
    ax, ay = -dy, dx
    cells = []
    for step in range(1, 7):
        for offset in (-2, -1, 0, 1, 2):
            x = px + dx * step + ax * offset
            y = py + dy * step + ay * offset
            if state.inside_board(x, y):
                cells.append((x, y))
    return tuple(dict.fromkeys(cells))


def _release_area(state, ability_id: str, definition: dict, target, direction):
    from ..equipment.expansion_runtime import radius_bonus
    dx, dy = _direction(state, target, direction)
    state.facing = (dx, dy)
    shape = str(meta(ability_id).get('shape') or '')
    if shape == 'ring3':
        radius, _extra = radius_bonus(state, ability_id)
        cells = _ring_cells(state, state.player.x, state.player.y, 3 + radius)
    elif shape == 'ring2':
        cells = _ring_cells(state, state.player.x, state.player.y, 2)
    else:
        cells = _screen_cells(state, dx, dy)
        if not cells:
            return ActionResult(False, tr('面朝方向没有可以立起风幕的空间。'))
    _pay(state, ability_id, definition)
    if ability_id == 'combat.fault_ring':
        message = _fault_ring(state, cells)
        _spend_use(state)
    elif ability_id == 'combat.paper_blades':
        _spend_use(state)
        construct_environments.replace_field(
            state, 'paper_blades', (state.player.x, state.player.y), (0, 0),
            cells=cells, remaining=4)
        message = tr('纸刃围成一圈，在梦里转了四回合。')
        _sound(state, state.player.x, state.player.y, int(meta(ability_id).get('sound') or 4))
    else:
        _spend_use(state)
        construct_environments.replace_field(
            state, 'backdraft_screen', (state.player.x, state.player.y), (dx, dy),
            cells=cells, remaining=4)
        message = tr('逆风幕立了起来：气流开始背离你。')
    state.messages.append(message)
    state._note_board_conceive(ability_id)
    return ActionResult(True, message, {'ability': ability_id,
                                       'cells': list(cells)})


def _fault_ring(state, cells) -> str:
    from ..equipment.expansion_runtime import construct_damage_bonus, on_construct_hit
    cellset = set(cells)
    walls = ground = 0
    for x, y in cells:
        if construct_environments.protected_geometry(state, x, y):
            continue
        cell = state.cell(x, y)
        if cell.solid:
            cell.integrity = max(0, cell.integrity - 25)
            walls += 1
            if cell.integrity == 0:
                state.destroy_wall(x, y, 'ability')
        else:
            # §15.3 的档位口径同样适用于裂地环：一档就是 −1，负地势继续保留。
            cell.elevation -= 1
            ground += 1
    hurt = 0
    for entity in [state.player, *list(state.enemies)]:
        if entity is not state.player and entity.integrity <= 0:
            continue
        if (entity.x, entity.y) not in cellset:
            continue
        if entity is state.player:
            state._lose_mind(2, combat=True)
        else:
            state._kill_full_reward = True
            damage = 2 + construct_damage_bonus(state, entity)
            _damage_number_before = entity.integrity
            entity.integrity = max(0, entity.integrity - damage)
            from .hit_events import note_integrity_loss
            note_integrity_loss(state, entity, _damage_number_before)
            hurt += 1
            on_construct_hit(state, entity, killed=entity.integrity <= 0)
            if entity.integrity > 0:
                px = _sign(entity.x - state.player.x)
                py = _sign(entity.y - state.player.y)
                nx, ny = entity.x + px, entity.y + py
                if (state.inside_board(nx, ny) and not state.cell(nx, ny).solid
                        and state.entity_at(nx, ny) is None):
                    entity.x, entity.y = nx, ny
            else:
                state._resolve_enemy(entity)
    _sound(state, state.player.x, state.player.y, 8)
    return tr('裂地环塌了一圈：{walls} 面墙开裂，{ground} 格地势下沉，{hurt} 个目标受创。',
              walls=walls, ground=ground, hurt=hurt)


# ---------------------------------------------------------------------------

def release(state, ability_id: str, target=None, direction=None,
            landing=None) -> ActionResult:
    definition = ABILITY_DEFINITIONS.get(ability_id)
    if definition is None or not is_combat(ability_id):
        return ActionResult(False, tr('未知的构想。'))
    from ..equipment.expansion_runtime import (
        after_construct, begin_construct, consume_construct_range, end_construct,
    )
    form = form_of(ability_id)
    begin_construct(state, ability_id, target)
    try:
        if form == FORM_MELEE:
            result = _release_melee(state, ability_id, definition, target, direction,
                                    landing=landing)
        elif form == FORM_LAUNCH:
            result = _release_launch(state, ability_id, definition, target, direction)
        elif form == FORM_THROW:
            result = _release_throw(state, ability_id, definition, target, direction)
        else:
            result = _release_area(state, ability_id, definition, target, direction)
        after_construct(state, result)
        if result.changed and form in (FORM_LAUNCH, FORM_THROW):
            consume_construct_range(state)
        return result
    finally:
        end_construct(state)
