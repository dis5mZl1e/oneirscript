"""Learned, named environments with real turn-based lifetimes and geometry."""
from __future__ import annotations

from ..i18n import tr

KINDS = {'spark', 'echo_pulse', 'library.erase', 'mirror_stance'}
VISUALS = {
    'expansion.pin_liquid': ('~ ', '#7fd3ee', '#213247'),
    'expansion.uphill_liquid': ('^ ', '#7fd3ee', '#213247'),
    'expansion.light_curtain': ('| ', '#b7c8d8', '#213247'),
    # 「裁光」：收窄一盏灯的照明扇区（光本身还在，只是照向一侧）。
    'expansion.narrow_light': ('◤ ', '#e5e561', '#2b2b15'),
    'expansion.sound_fold': ('\\ ', '#c8a0d3', '#213247'),
    'expansion.deflector': ('/ ', '#c2e4ff', '#213247'),
    'expansion.double_mirror': ('| ', '#c2e4ff', '#213247'),
    'expansion.delay_sound': ('~ ', '#89dbe1', '#173038'),
    'spark': ('* ', '#ffb86b', '#392619'),
    'echo_pulse': ('~ ', '#89dbe1', '#173038'),
    'library.erase': ('/ ', '#d7a9ee', '#302039'),
    'mirror_stance': ('| ', '#c2e4ff', '#213247'),
    # §13：真实世界状态（入档、按层暂停）。
    'delayed_shell': ('o ', '#ffd166', '#3a2a12'),
    'paper_blades': ('x ', '#e6e0d4', '#332e26'),
    'backdraft_screen': ('> ', '#9fd6ef', '#1d2f38'),
    # §12 H2：时缓区、遗忘区、蒸腾区。
    'slow_zone': ('≈ ', '#9db7d8', '#1e2836'),
    'moth_zone': ('· ', '#d9c7a1', '#302b20'),
    'transpire_zone': ('^ ', '#a9d8c1', '#1c2f27'),
}


# 悬停「构想残留」要显示来源构想的名称，不再维护第二份标签表：
# 旧表只覆盖 §11 的四种场，第十二／十三节新增的六种场一悬停就 KeyError。
RESIDUE_SOURCE = {
    'spark': 'spark',
    'echo_pulse': 'echo_pulse',
    'library.erase': 'library.erase',
    'mirror_stance': 'mirror_stance',
    'delayed_shell': 'combat.delayed_shell',
    'paper_blades': 'combat.paper_blades',
    'backdraft_screen': 'combat.backdraft_screen',
    'slow_zone': 'slow_wave',
    'moth_zone': 'moth_dust',
    'transpire_zone': 'transpire',
    # 扩展包构想（2026-10-25）留下的八种场：`VISUALS` 先有了图标，来源表没跟上，
    # 悬停只显示「构想残留」而没有来源名。每个 kind 对应真的会 `start_field` 它的那条构想。
    'expansion.pin_liquid': 'expansion.terrain.a05',
    'expansion.uphill_liquid': 'expansion.terrain.a06',
    'expansion.light_curtain': 'expansion.light.a03',
    'expansion.narrow_light': 'expansion.light.a01',
    'expansion.sound_fold': 'expansion.sound.a03',
    'expansion.delay_sound': 'expansion.sound.a05',
    'expansion.deflector': 'expansion.projectile.a01',
    'expansion.double_mirror': 'expansion.projectile.a06',
}


def residue_name(kind):
    from .content import ABILITY_DEFINITIONS
    ability_id = RESIDUE_SOURCE.get(kind)
    if ability_id is None:
        return None
    return ABILITY_DEFINITIONS[ability_id]['name']


def start_field(state, kind, position, direction, *, cells=(), remaining=1):
    field = dict(kind=kind, layer=state.layer_key(),
                 position=list(position), direction=list(direction),
                 cells=[list(p) for p in cells] or [list(position)],
                 remaining=int(remaining))
    state.construct_environments.append(field)
    state._narrow_light_cache = None
    return field


def replace_field(state, kind, position, direction, *, cells=(), remaining=1):
    state.construct_environments[:] = [
        field for field in state.construct_environments
        if not (field['kind'] == kind and field['layer'] == state.layer_key())]
    return start_field(state, kind, position, direction,
                       cells=cells, remaining=remaining)


def carrying_surface(state, x, y):
    from .throwing import carrying_surface as impl
    return impl(state, x, y)


def screen_cells(state):
    cells = set()
    for field in active(state):
        if field['kind'] == 'backdraft_screen':
            cells.update(tuple(p) for p in field['cells'])
    return cells


def _move_screen_gas(state, field):
    """每回合把幕内气体向远离玩家的方向搬一格；放不下就留在原格。"""
    player = state.player
    moved = set()
    for x, y in field['cells']:
        if (x, y) in moved:
            continue
        cell = state.cell(x, y)
        if cell.gas <= 0 or not cell.gas_kind:
            continue
        dx = (x > player.x) - (x < player.x)
        dy = (y > player.y) - (y < player.y)
        if not (dx or dy):
            continue
        nx, ny = x + dx, y + dy
        if not (0 <= nx < state.width and 0 <= ny < state.height):
            continue
        target = state.cell(nx, ny)
        if target.solid:
            continue
        if target.gas > 0 and target.gas_kind != cell.gas_kind:
            continue
        amount = min(cell.gas, max(0, 100 - target.gas))
        if amount <= 0:
            continue
        kind = cell.gas_kind
        state._add_gas(target, kind, amount)
        cell.gas -= amount
        if cell.gas <= 0:
            cell.gas_kind = ''
        moved.add((nx, ny))


def _paper_blades_damage(state, field):
    """纸刃环每真实回合结算一次：环上异象 2 伤，玩家自伤仍 1。"""
    ring = {tuple(p) for p in field['cells']}
    for enemy in list(state.enemies):
        if enemy.integrity <= 0 or (enemy.x, enemy.y) not in ring:
            continue
        state._kill_full_reward = True
        _damage_number_before = enemy.integrity
        enemy.integrity = max(0, enemy.integrity - PAPER_BLADES_DAMAGE)
        from .hit_events import note_integrity_loss
        note_integrity_loss(state, enemy, _damage_number_before)
        if enemy.integrity <= 0:
            state._resolve_enemy(enemy)
    if (state.player.x, state.player.y) in ring:
        state._lose_mind(PAPER_BLADES_SELF_DAMAGE, combat=True)


def visible_target(state):
    hover = state.hover_target
    if hover and state.inside_board(*hover) and state.is_visible(*hover):
        return tuple(hover)
    dx, dy = state.facing
    return state.player.x + dx, state.player.y + dy


def protected_geometry(state, x, y):
    from .tamper_protection import terrain_reason, _facility_cells
    return (bool(terrain_reason(state, x, y)) or (x, y) in _facility_cells(state)
            or bool(state.circuit_node_at(x, y)) or bool(state.cell(x, y).wire)
            or any((event.x, event.y) == (x, y) for event in state.events))


# §15.6：预览与结算必须共用下面这几个口径，否则「预览说抬得动、按下却零变化」。
ELEVATION_OPS = {'raise_terrain': 1, 'sink_terrain': -1}
LIQUID_ADD_OPS = {'condense_dew': ('水', 20)}
LIQUID_CLEAR_OPS = ('draw_liquid', 'ice_bridge', 'transpire')
ELEVATION_RADIUS = 2
FAULT_RING_RADIUS = 3
FAULT_RING_OPS = ('combat.fault_ring',)
REFUSE_PINNED = '这一片地势被钉住了，抬不动也压不下。'
# §12 H2：凝露中心 20、四邻各 10，整发最多 60。
CONDENSE_CROSS = (((0, 0), 20), ((1, 0), 10), ((-1, 0), 10),
                  ((0, 1), 10), ((0, -1), 10))
CONDENSE_KIND = '水'
CONDENSE_BUDGET = 60
DRAW_LIQUID_BUDGET = 96
ICE_BRIDGE_STEPS = 8
ICE_BRIDGE_PER_CELL = 8
TRANSPIRE_BUDGET = 96
TRANSPIRE_TURNS = 3
# §12 H3：植物、控场与地形产物；预览与结算共用同一份计划。
SOW_GREEN_RADIUS = 3
SOW_GREEN_CAP = 25
SLOW_ZONE_RADIUS = 4
SLOW_ZONE_TURNS = 6
REPULSE_RADIUS = 2
REPULSE_DISTANCE = 3
# §15 平衡修复（2026-10-22）：推斥每目标 1→2 伤；纸刃环每跳 1→2 伤（玩家
# 自伤仍 1）；迟响弹爆炸威力 2→3。预览与结算都从这几个常量取，不再写死。
REPULSE_DAMAGE = 2
PAPER_BLADES_DAMAGE = 2
PAPER_BLADES_SELF_DAMAGE = 1
DELAYED_SHELL_RADIUS = 2
DELAYED_SHELL_POWER = 3
STATIC_ARC_DAMAGE = 3
STATIC_ARC_SLOW = 2
COLLAPSE_CORRIDOR = 5
COLLAPSE_WALL_INTEGRITY = 40
COLLAPSE_WALL_LIMIT = 3
COLLAPSE_DEBRIS = 3
CONJURE_WIDTH = 3
INK_RADIUS = 2
INK_CAP = 25
H3_AREA_OPS = ('sow_green', 'repulse', 'slow_wave', 'static_arc',
               'collapse', 'conjure_wall', 'ink_doodle')


def ring_cells(state, radius: int, center=None):
    """切比雪夫距离恰为 radius 的外环，越出棋盘的部分裁掉。

    裂地环的结算与预览、纸刃旋流的场格都从这里取同一份选区。
    """
    cx, cy = (state.player.x, state.player.y) if center is None else center
    return tuple((x, y)
                 for y in range(max(0, int(cy) - radius), min(state.height, int(cy) + radius + 1))
                 for x in range(max(0, int(cx) - radius), min(state.width, int(cx) + radius + 1))
                 if max(abs(x - int(cx)), abs(y - int(cy))) == radius)


def elevation_area(state, center, radius: int = ELEVATION_RADIUS):
    """隆起／陷落的实际作用区：legal 与受保护格分开返回（钳位规则同结算）。"""
    _fx, _fy = center
    legal: list[tuple[int, int]] = []
    blocked: list[tuple[int, int]] = []
    for y in range(max(1, int(_fy) - radius), min(state.height - 1, int(_fy) + radius + 1)):
        for x in range(max(1, int(_fx) - radius), min(state.width - 1, int(_fx) + radius + 1)):
            (blocked if protected_geometry(state, x, y) else legal).append((x, y))
    return tuple(legal), tuple(blocked)


def liquid_component(state, origin):
    """施放时可见的同种液体四邻连通块快照（结算与预览共用）。"""
    ox, oy = origin
    kind = state.cell(ox, oy).liquid_kind
    seen = {(ox, oy)}
    queue = [(ox, oy)]
    while queue:
        x, y = queue.pop(0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            pos = (nx, ny)
            if pos in seen or not state.inside_board(nx, ny):
                continue
            if not state.is_visible(nx, ny):
                continue
            cell = state.cell(nx, ny)
            if cell.solid or cell.liquid <= 0 or cell.liquid_kind != kind:
                continue
            if protected_geometry(state, nx, ny):
                continue
            seen.add(pos)
            queue.append(pos)
    return kind, sorted(seen, key=lambda p: (
        abs(p[0] - ox) + abs(p[1] - oy), p[1], p[0]))


def condense_plan(state, center):
    """凝露的加水清单：中心 20、四邻各 10，整发最多 60（含每格容量钳位）。"""
    cx, cy = center
    plan: list[tuple[tuple[int, int], int]] = []
    total = 0
    for (dx, dy), amount in CONDENSE_CROSS:
        x, y = cx + dx, cy + dy
        if not state.inside_board(x, y) or state.cell(x, y).solid:
            continue
        cell = state.cell(x, y)
        room = max(0, 100 - cell.liquid)
        add = min(amount, room, CONDENSE_BUDGET - total)
        if add > 0:
            plan.append(((x, y), add))
            total += add
    return plan


def draw_liquid_plan(state, origin):
    """汲取清单：按连通块由近及远，整发最多 96 点。"""
    kind, component = liquid_component(state, origin)
    remaining = DRAW_LIQUID_BUDGET
    plan: list[tuple[tuple[int, int], int]] = []
    for x, y in component:
        if remaining <= 0:
            break
        cell = state.cell(x, y)
        if cell.liquid <= 0 or cell.liquid_kind != kind:
            continue
        take = min(remaining, cell.liquid)
        if take <= 0:
            continue
        plan.append(((x, y), take))
        remaining -= take
    return kind, plan


def axis_direction(direction):
    """把方向收成四方向；斜向取主轴，零向量按东处理。"""
    dx, dy = int(direction[0]), int(direction[1])
    if dx and dy:
        return ((dx, 0) if abs(dx) >= abs(dy) else (0, dy))
    if not (dx or dy):
        return (1, 0)
    return (dx, dy)


def ice_bridge_plan(state, origin, direction):
    """冰桥清单：沿方向 8 步、宽 3，每格最多转 8 点入冻层。"""
    ox, oy = origin
    kind = state.cell(ox, oy).liquid_kind
    dx, dy = axis_direction(direction)
    perp = (-dy, dx)
    plan: list[tuple[tuple[int, int], int]] = []
    frozen = set()
    for step in range(ICE_BRIDGE_STEPS):
        cx, cy = ox + dx * step, oy + dy * step
        if not state.inside_board(cx, cy):
            break
        if state.cell(cx, cy).solid or not state.is_visible(cx, cy):
            break
        for offset in (-1, 0, 1):
            tx, ty = cx + perp[0] * offset, cy + perp[1] * offset
            if not state.inside_board(tx, ty) or not state.is_visible(tx, ty):
                continue
            if (tx, ty) in frozen:
                continue
            cell = state.cell(tx, ty)
            if (cell.solid or cell.liquid <= 0 or cell.liquid_kind != kind
                    or protected_geometry(state, tx, ty)):
                continue
            stock = dict(cell.phase_stock or dict(
                form='ice', kind=kind, amount=0,
                base_floor=cell.aggregate_variant or '普通聚合物'))
            if stock.get('form') != 'ice' or stock.get('kind') != kind:
                continue
            take = min(ICE_BRIDGE_PER_CELL, cell.liquid,
                       max(0, 100 - int(stock.get('amount', 0) or 0)))
            if take <= 0:
                continue
            plan.append(((tx, ty), take))
            frozen.add((tx, ty))
    return kind, plan


def transpire_plan(state, origin):
    """蒸腾首拍清单：每格 ≤8、整区累计 ≤96，按快照顺序推进。"""
    kind, component = liquid_component(state, origin)
    from ..materials import liquid_def

    liquid = liquid_def(kind)
    gas = liquid.evaporation_gas
    if not gas or not component:
        return kind, '', 1, []
    ratio = max(1, int(liquid.evaporation_ratio or 1))
    budget = TRANSPIRE_BUDGET
    plan: list[tuple[tuple[int, int], int, int]] = []
    for (x, y) in component:
        if budget <= 0:
            break
        cell = state.cell(x, y)
        if cell.solid or cell.liquid <= 0 or cell.liquid_kind != kind:
            continue
        take = min(8, cell.liquid, budget)
        if take <= 0:
            continue
        gas_amount = max(1, take // ratio)
        room = 100 - cell.gas
        if room <= 0:
            continue
        if gas_amount > room:
            gas_amount = room
            take = min(take, gas_amount * ratio)
        if take <= 0:
            continue
        plan.append(((x, y), take, gas_amount))
        budget -= take
    return kind, gas, ratio, plan


def sow_green_plan(state, center):
    """播绿清单：曼哈顿半径 3，内圈半径 1 高丛、其余低草，最多 25 格。"""
    cx, cy = center
    points = [(x, y)
              for y in range(max(0, cy - SOW_GREEN_RADIUS),
                             min(state.height, cy + SOW_GREEN_RADIUS + 1))
              for x in range(max(0, cx - SOW_GREEN_RADIUS),
                             min(state.width, cx + SOW_GREEN_RADIUS + 1))
              if abs(x - cx) + abs(y - cy) <= SOW_GREEN_RADIUS]
    points.sort(key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p[0], p[1]))
    plan = []
    for x, y in points:
        if len(plan) >= SOW_GREEN_CAP:
            break
        cell = state.cell(x, y)
        if (cell.solid or cell.plant or cell.liquid
                or protected_geometry(state, x, y)
                or state.entity_at(x, y)):
            continue
        plan.append((x, y, 2 if abs(x - cx) + abs(y - cy) <= 1 else 1))
    return plan


def slow_zone_cells(state, center):
    """时缓区：以落点为中心的方形半径 4；只裁棋盘边界。"""
    cx, cy = center
    return [(x, y)
            for y in range(cy - SLOW_ZONE_RADIUS, cy + SLOW_ZONE_RADIUS + 1)
            for x in range(cx - SLOW_ZONE_RADIUS, cx + SLOW_ZONE_RADIUS + 1)
            if state.inside_board(x, y)]


def repulse_plan(state, center):
    """推斥清单：半径 2 内每个存活敌对异象的落点，按列表顺序模拟占位。

    就地模拟而不是各自独立计算，才能和逐格结算一样处理「A 被推到 B 前面」
    这类连锁。被钉住的异象仍受 REPULSE_DAMAGE 点创伤，但不移动。
    """
    cx, cy = center
    occupied = {(state.player.x, state.player.y)}
    occupied.update((enemy.x, enemy.y) for enemy in state.enemies
                    if enemy.integrity > 0)
    rooted = getattr(state, '_enemy_rooted', lambda _enemy: False)
    plan = []
    for enemy in list(state.enemies):
        if enemy.integrity <= 0:
            continue
        if getattr(enemy, 'relation', '') != '失控意识':
            continue
        if max(abs(enemy.x - cx), abs(enemy.y - cy)) > REPULSE_RADIUS:
            continue
        dx = (enemy.x > cx) - (enemy.x < cx)
        dy = (enemy.y > cy) - (enemy.y < cy)
        if not (dx or dy):
            # 落点就在异象脚下时按「远离玩家」推，与结算同一口径。
            dx = (enemy.x > state.player.x) - (enemy.x < state.player.x)
            dy = (enemy.y > state.player.y) - (enemy.y < state.player.y)
            if not (dx or dy):
                dx = 1 if enemy.x >= state.player.x else -1
        tx, ty = enemy.x, enemy.y
        if not rooted(enemy):
            for _ in range(REPULSE_DISTANCE):
                nx, ny = tx + dx, ty + dy
                if not state.inside_board(nx, ny) or state.cell(nx, ny).solid:
                    break
                if (nx, ny) in occupied:
                    break
                tx, ty = nx, ny
        occupied.discard((enemy.x, enemy.y))
        occupied.add((tx, ty))
        plan.append((enemy, tx, ty))
    return plan


def static_arc_plan(state, center):
    """静电弧落点：优先命中异象，否则沿真实四邻导电介质取连通区。"""
    x, y = center
    enemy = state.entity_at(x, y)
    if (enemy is not None and enemy is not state.player
            and getattr(enemy, 'relation', '') == '失控意识'
            and getattr(enemy, 'integrity', 0) > 0):
        return ('enemy', enemy)
    zone = state._conductive_component((x, y))
    return ('zone', zone) if zone else None


def collapse_plan(state, center, direction):
    """崩落：沿方向最长 5 格走廊，取两侧完整度 ≤40 的普通墙与最多 3 格碎屑落点。"""
    from ..materials import wall_def
    from .tamper_protection import terrain_reason

    x, y = center
    dx, dy = axis_direction(direction)
    corridor = []
    for step in range(COLLAPSE_CORRIDOR):
        cx, cy = x + dx * step, y + dy * step
        if not state.inside_board(cx, cy) or state.cell(cx, cy).solid:
            break
        corridor.append((cx, cy))
    perp = (-dy, dx)
    walls = []
    for cx, cy in corridor:
        for sign in (-1, 1):
            wx, wy = cx + perp[0] * sign, cy + perp[1] * sign
            if not state.inside_board(wx, wy):
                continue
            cell = state.cell(wx, wy)
            if (not cell.solid or cell.wall_kind == '意识边界'
                    or cell.integrity > COLLAPSE_WALL_INTEGRITY
                    or wall_def(cell.wall_kind).integrity >= 9999
                    or terrain_reason(state, wx, wy)):
                continue
            walls.append((wx, wy))
    debris = [(cx, cy) for cx, cy in corridor
              if (cx, cy) != (state.player.x, state.player.y)
              and not state.entity_at(cx, cy)][:COLLAPSE_DEBRIS]
    return walls[:COLLAPSE_WALL_LIMIT], debris


def conjure_wall_plan(state, center, direction):
    """凝聚：沿方向垂线的最多 3 格合法空地。"""
    x, y = center
    dx, dy = axis_direction(direction)
    perp = (-dy, dx)
    candidates = []
    for offset in range(-(CONJURE_WIDTH // 2), CONJURE_WIDTH // 2 + 1):
        cx, cy = x + perp[0] * offset, y + perp[1] * offset
        if not state.inside_board(cx, cy):
            continue
        cell = state.cell(cx, cy)
        if (cell.solid or state.entity_at(cx, cy)
                or protected_geometry(state, cx, cy)):
            continue
        candidates.append((cx, cy))
    return candidates


def ink_doodle_plan(state, center):
    """涂鸦：5×5 内合法地面，最多 25 格；任务设施、保护地板与占用格不改。"""
    from .constants import Material

    x, y = center
    plan = []
    for yy in range(max(0, y - INK_RADIUS), min(state.height, y + INK_RADIUS + 1)):
        for xx in range(max(0, x - INK_RADIUS), min(state.width, x + INK_RADIUS + 1)):
            if len(plan) >= INK_CAP:
                break
            cell = state.cell(xx, yy)
            if (cell.solid or cell.floor is Material.SOLID_AGGREGATE
                    or protected_geometry(state, xx, yy)
                    or state.entity_at(xx, yy)):
                continue
            plan.append((xx, yy))
    return plan


def prepare(state, kind):
    x, y = state.player.x, state.player.y
    dx, dy = state.facing
    if not (dx or dy):
        dx = 1
    target = (x + dx, y + dy)
    if kind == 'echo_pulse':
        target = (x, y)
    if kind == 'spark':
        hover = state.hover_target
        if hover and state.inside_board(*hover) and state.is_visible(*hover):
            target = tuple(hover)
    if not state.inside_board(*target):
        return None, tr('这里没有可以展开构想的位置。')
    if kind == 'mirror_stance':
        from .tamper_protection import construction_reason
        reason = construction_reason(state, *target)
        if reason or state.cell(*target).solid:
            return None, tr(reason) if reason else tr('镜面需要相邻的空地。')
        if reflection(state, *target, (dx, dy)) is not None:
            return None, tr('这里已经有一面构想的镜面。')
    duration = {'spark': 2, 'echo_pulse': 8, 'library.erase': 4, 'mirror_stance': 6}[kind]
    cells = [list(target)]
    if kind == 'library.erase':
        cells = [[x + dx * i, y + dy * i] for i in range(1, 6)
                 if state.inside_board(x + dx * i, y + dy * i)]
    return dict(kind=kind, layer=state.layer_key(), position=list(target),
                direction=[dx, dy], cells=cells, remaining=duration,
                terrain_probe=(kind == 'echo_pulse')), ''


def start(state, kind, *, prepared=None):
    field, error = (prepared, '') if prepared is not None else prepare(state, kind)
    if error:
        return False, error
    if kind == 'echo_pulse':
        state.construct_environments[:] = [
            existing for existing in state.construct_environments
            if not (existing['kind'] == kind and existing['layer'] == state.layer_key())]
    state.construct_environments.append(field)
    return True, tr('构想「{name}」留在了梦境中（{turns} 回合）。',
                    name=tr({'spark': '火花', 'echo_pulse': '回响',
                             'library.erase': '删划', 'mirror_stance': '镜面'}[kind]),
                    turns=field['remaining'])


def active(state):
    return [field for field in state.construct_environments
            if field['layer'] == state.layer_key() and field['remaining'] > 0]


def narrow_light_map(state):
    """光源格 → 受限方向；按（回合, 场数量）缓存，供 ``glow`` 热路径逐格查。

    缓存键只看「回合数 + 场条数」：场到期时条数变少、起场时条数变多，两种情况
    都会换键；同一回合内不会有多于这两种的变化（`_narrow_light_cache` 也会在
    ``start_field`` 里被清掉，覆盖「同条数换内容」这种边角）。
    """
    fields = state.construct_environments
    key = (int(getattr(state, "time", 0)), len(fields))
    cache = getattr(state, "_narrow_light_cache", None)
    if cache is not None and cache[0] == key:
        return cache[1]
    layer = state.layer_key()
    table = {}
    for field in fields:
        if (field.get('kind') == 'expansion.narrow_light'
                and field.get('layer') == layer and int(field.get('remaining', 0)) > 0):
            table[(int(field['position'][0]), int(field['position'][1]))] = (
                int(field['direction'][0]), int(field['direction'][1]))
    state._narrow_light_cache = (key, table)
    return table


def narrow_light_direction(state, x, y):
    """光源格 (x, y) 上「裁光」场的受限方向；没有就返回 None。

    ``glow`` 与 ``light_allows`` 共用这一处读取：扇区只在照明判定里生效，
    灯的 ``light_radius`` / ``light_on`` 一个数都不动，所以「灯本身仍耗能」是
    字面成立的，而不是「我们决定不改耗能」。
    """
    return narrow_light_map(state).get((int(x), int(y)))


def visual_cells(state):
    cells = {}
    for field in active(state):
        for point in field['cells']:
            cells[tuple(point)] = (*VISUALS[field['kind']], field['remaining'])
    return cells


def moth_zone_tick(state, field):
    """遗忘区：未直接看见玩家的敌对异象降一档警戒并清掉目击记忆。"""
    affected = field.setdefault('affected', [])
    cells = {tuple(p) for p in field.get('cells', ())}
    ladder = ['未察觉', '怀疑', '警戒', '追踪']
    count = 0
    for enemy in state.enemies:
        if enemy.integrity <= 0 or enemy.relation != '失控意识':
            continue
        if (enemy.x, enemy.y) not in cells:
            continue
        key = getattr(enemy, 'id', id(enemy))
        if key in affected:
            continue
        if state._enemy_sees_player(enemy):
            continue
        current = enemy.alert_state
        enemy.alert_state = (ladder[max(0, ladder.index(current) - 1)]
                             if current in ladder else '未察觉')
        enemy.last_seen_x = -1
        enemy.last_seen_y = -1
        enemy.path_plan = []
        enemy.wandering = True
        affected.append(key)
        count += 1
    return count


def transpire_zone_tick(state, field):
    """蒸腾区：按快照顺序逐格相变，每格每回合 ≤8、整区累计 ≤96。"""
    budget = int(field.get('budget', 0) or 0)
    kind = str(field.get('liquid_kind', ''))
    gas = str(field.get('gas', ''))
    if budget <= 0 or not kind or not gas:
        return 0
    ratio = max(1, int(field.get('ratio', 1) or 1))
    converted = 0
    for x, y in field.get('cells', ()):
        if budget <= 0:
            break
        cell = state.cell(x, y)
        if cell.solid or cell.liquid <= 0 or cell.liquid_kind != kind:
            continue
        if cell.material_clocks.get("phase:" + kind) == state.time:
            continue  # 同格同回合已被自然挥发转换过，蒸腾不再叠一次相变。
        take = min(8, cell.liquid, budget)
        if take <= 0:
            continue
        gas_amount = max(1, take // ratio)
        room = 100 - cell.gas
        if room <= 0:
            continue  # 容量不足：暂停这一格，液体保留。
        if gas_amount > room:
            gas_amount = room
            take = min(take, gas_amount * ratio)
        if take <= 0:
            continue
        cell.liquid -= take
        if cell.liquid <= 0:
            cell.liquid = 0
            cell.liquid_kind = ''
        state._add_gas(cell, gas, gas_amount)
        budget -= take
        converted += take
    field['budget'] = budget
    return converted


def tick(state, amount):
    for _ in range(int(amount)):
        for field in list(active(state)):
            kind = field['kind']
            if field.get('persistent'):
                continue
            if int(field.get('pause_ticks', 0)) > 0:
                field['pause_ticks'] -= 1
                continue
            if kind == 'expansion.uphill_liquid':
                from .expansion_abilities import tick_uphill
                tick_uphill(state,field)
            elif kind == 'echo_pulse':
                position, direction = echo_step(state, field['position'], field['direction'])
                field['position'], field['direction'] = list(position), list(direction)
                field['cells'] = [field['position'][:]]
                from .vision.knowledge import record_terrain_outline
                x, y = field['position']
                # Saved shadows predating the rework keep their original sound
                # and remaining lifetime, without retroactively gaining scouting.
                if field.get('terrain_probe', False):
                    record_terrain_outline(state, [(x, y), (x + 1, y), (x - 1, y),
                                                   (x, y + 1), (x, y - 1)])
                state._sound_pulse(*field['position'], 10, by_player=True,
                                   category="lure", source=tr("回响"))
            elif kind == 'moth_zone':
                moth_zone_tick(state, field)
            elif kind == 'transpire_zone':
                transpire_zone_tick(state, field)
            elif kind == 'library.erase':
                from .tamper_protection import terrain_reason
                for x, y in field['cells']:
                    cell = state.cell(x, y)
                    if cell.solid and not terrain_reason(state, x, y):
                        cell.integrity = max(0, cell.integrity - 20)
                        if not cell.integrity:
                            state.destroy_wall(x, y, 'ability')
                            state.invalidate_sight_radius()
            elif kind == 'paper_blades':
                _paper_blades_damage(state, field)
            elif kind == 'backdraft_screen':
                _move_screen_gas(state, field)
            field['remaining'] -= 1
            if kind == 'spark' and field['remaining'] <= 0:
                state._ignite_cell(*field['position'], 3, by_player=True)
                state.messages.append(tr('延迟的火花落下，开始点燃真实材料。'))
            if kind == 'delayed_shell' and field['remaining'] <= 0:
                x, y = field['position']
                state.messages.append(tr('迟响弹的倒计时归零。'))
                state._explode(x, y, DELAYED_SHELL_RADIUS,
                               DELAYED_SHELL_POWER, from_player=True)
    state.construct_environments[:] = [field for field in state.construct_environments
                                      if field['remaining'] > 0]


def echo_step(state, position, direction):
    x, y = position
    dx, dy = direction
    nx, ny = x + dx, y + dy
    if not state.inside_board(nx, ny) or state.cell(nx, ny).solid:
        dx, dy = -dx, -dy
        nx, ny = x + dx, y + dy
    if not state.inside_board(nx, ny) or state.cell(nx, ny).solid:
        nx, ny = x, y
    return (nx, ny), (dx, dy)


def reflection(state, x, y, direction):
    # A projectile hits an occupant before reaching the mirror plane. Both
    # directional and assisted firing use this same collision priority.
    if state.entity_at(x, y) is not None:
        return None
    from .expansion_consumables import reflection as consumable_reflection
    redirected = consumable_reflection(state, x, y, direction)
    if redirected is not None:
        return redirected
    for field in active(state):
        if field['kind'] not in {'mirror_stance','expansion.deflector','expansion.double_mirror'}:
            continue
        if [x,y] not in field.get('cells', [field['position']]):
            continue
        dx, dy = direction
        nx, ny = field['direction']
        dot, norm = dx * nx + dy * ny, nx * nx + ny * ny
        if dot == 0:
            return None
        if field['kind'] == 'expansion.deflector':
            field['remaining'] = 0
        return (int(dx - 2 * dot * nx / norm), int(dy - 2 * dot * ny / norm))
    return None


def reflected_path(state, origin, path):
    """Apply one placed mirror to an assisted projectile's finite flight."""
    previous = origin
    for index, point in enumerate(path):
        direction = (point[0] - previous[0], point[1] - previous[1])
        outgoing = reflection(state, *point, direction)
        if outgoing:
            tail = [(point[0] + outgoing[0] * i, point[1] + outgoing[1] * i)
                    for i in range(1, len(path) - index)]
            return path[:index+1] + [p for p in tail if state.inside_board(*p)]
        previous = point
    return path



def light_curtain_cells(state):
    return {tuple(p) for f in active(state) if f['kind']=='expansion.light_curtain'
            for p in f['cells']}
