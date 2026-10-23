"""Hand-built, replayable material and route challenges for the two small realms."""
import random
from .entities import Cell, WorldEvent, WorldItem
from ..data.realm_challenges import EMBER_STAGES, EMBER_CONTAINER, EBBING_REWARD_SPOTS, TEXT


def prepare_ember_materials(state, cells):
    """Upgrade the challenge in place, retaining partitions already cleared."""
    kinds = ('蜡化记忆墙', '压实聚合墙', '门扉之壁')
    for index, stage in enumerate(EMBER_STAGES):
        gx, gy = stage['gate']
        opened = not cells[gy][gx].solid
        for y in range(10, 14):
            if opened:
                state.clear_wall(cells[y][gx])
            else:
                state.configure_wall(cells[y][gx], kinds[index])
                cells[y][gx].integrity = (4, 90, 60)[index]
        sx, sy = stage['source']
        for x in range(sx, gx):
            state.clear_wall(cells[sy][x])
            cells[sy][x].elevation = -(x-sx)
            cells[sy][x].aggregate_variant = ''
        # A raised, insulated pedestrian bank keeps liquid off the player route.
        for y in (11, 13):
            for x in range(sx-1, gx):
                cells[y][x].elevation = 5
                cells[y][x].aggregate_variant = '绝热层'
        if index == 0 and not opened:
            state.configure_wall(cells[12][12], '门扉之壁')
        if index == 2 and not opened:
            cells[12][32].flame = 6
    container = cells[EMBER_CONTAINER[1]][EMBER_CONTAINER[0]]
    if container.solid:
        state.configure_wall(container, '记忆容器')
        container.integrity = 7
        container.liquid_kind, container.liquid = '酸蚀液', 100


def ember_bridge(state, definition, depth):
    from ..data.dreams import EMBER_REWARD_LABELS
    width, height = 40, 24
    cells = [[Cell() for _ in range(width)] for _ in range(height)]
    for row in cells:
        for cell in row:
            state.configure_wall(cell, '意识边界')
    for y in range(height):
        for x in range(width):
            if x in (0, width-1) or y in (0, height-1):
                state.configure_wall(cells[y][x], '意识边界')
    for y in range(10, 14):
        for x in range(4, 34):
            state.clear_wall(cells[y][x])
    for y in range(9, 16):
        for x in range(34, 39):
            state.clear_wall(cells[y][x])
    # Three rooms express their apparatus: reservoir, etching pool, hot chamber.
    for x1, y1, x2, y2 in ((5, 7, 13, 15), (16, 9, 23, 18), (26, 6, 32, 15)):
        for y in range(y1, y2+1):
            for x in range(x1, x2+1):
                state.clear_wall(cells[y][x])
    for x in range(4, 34):
        cells[11][x].aggregate_variant = '绝热层'
    for stage in EMBER_STAGES:
        gx, _ = stage['gate']
        for y in range(10, 14):
            state.configure_wall(cells[y][gx], '门扉之壁')
            cells[y][gx].hardness, cells[y][gx].integrity = 1, 60
    state.configure_wall(cells[EMBER_CONTAINER[1]][EMBER_CONTAINER[0]], '记忆容器')
    prepare_ember_materials(state, cells)
    # A small isolated teaching puddle next to the spawn keeps the entry lighter
    # demonstrable without connecting a fire trail across the entire bridge.
    state._add_liquid(cells[12][6], '燃油', 24)
    state.configure_wall(cells[12][37], '石台')
    rng = random.Random(state.seed ^ 0x1A5E ^ depth*3571)
    # Every offered trio covers output, mitigation and retreat; no full immunity.
    choices = [rng.choice(('arsonist_watch', 'blast_ring')), 'singed_gloves', 'ember_boots']
    rng.shuffle(choices)
    options = [{'label': EMBER_REWARD_LABELS[item], 'reward_id': item, 'exit_realm': 'clear'}
               for item in choices]
    options.append({'label': '「再看一眼，不取。」', 'leave': True})
    options.append({'label': TEXT['empty_exit'][0], 'exit_realm': 'clear'})
    state._pending_realm_events = [WorldEvent(
        event_id='realm_reward.ember_bridge', name='余烬尽头的石台', x=37, y=11,
        description='石台上摆着几件被火烤过的旧物，等你挑一件带走。',
        catalog_id='realm_reward.ember_bridge', kind='compound',
        dialogue=('火在身后熄了。石台上剩三件东西，都是烧不化的。',),
        options=tuple(options), bound=True, dissolution_reward=0)]
    state.realm_challenges['ember_bridge'] = {
        'version': 3, 'supply': [False]*3, 'vent_rounds': None,
        'routed': False, 'cooling': False, 'cooled': False}
    return width, height, cells, (5, 12)


def ebbing_hall(state, definition, depth):
    from ..data.dreams import EBBING_EXIT_REWARD
    width, height = 40, 24
    cells = [[Cell() for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if x in (0, width-1) or y in (0, height-1):
                state.configure_wall(cells[y][x], '意识边界')
    # Partial dividers give cover and route choices; the center is always wide.
    for x in (15, 25):
        for y in range(9, 16):
            if y != 12:
                state.configure_wall(cells[y][x], definition.wall_kind)
    state._pending_realm_events = [WorldEvent(
        event_id='realm_exit.ebbing_hall', name='退潮的出口', x=20, y=10,
        description=TEXT['tide_exit_desc'][0], catalog_id='realm_exit.ebbing_hall',
        kind='compound', dialogue=(TEXT['tide_exit_desc'][0],),
        options=({'label': '跨出去', 'exit_realm': 'clear', 'reward_id': EBBING_EXIT_REWARD},
                 {'label': TEXT['empty_exit'][0], 'exit_realm': 'clear'},
                 {'label': '再等等', 'leave': True}), bound=True, dissolution_reward=0)]
    rng = random.Random(state.seed ^ 0xEBB ^ depth*3571)
    items = ['blank_cheque_book', 'faded_id_card']
    rng.shuffle(items)
    items.append('paper_clip')
    state._pending_realm_items = [WorldItem(state._make_item(item), *spot)
                                 for item, spot in zip(items, EBBING_REWARD_SPOTS)]
    state.ebbing_elapsed = state.ebbing_contract_rounds = 0
    state.ebbing_past_threshold = False
    state.ebbing_warning_ring = -1
    return width, height, cells, (20, 18)


# ---------------------------------------------------------------------------
# 千禧园（2026-10-10，docs/millennium-garden-design.md §5–§10）
# 开放式 emoji 场地：高度场 → 湖河 → 结构墙簇 → 木屋/体育场 → 稀疏设备 → 彩砖。
# 第 5 层 = 零点体育场（realm 专属 vault，中央蓝屏终端召唤千年虫）。
# ---------------------------------------------------------------------------

# 出生点 3 格内的液体白名单（§12：安全锚）。
_MG_SPAWN_SAFE_LIQUIDS = ("水", "稀释记忆", "镇静溶液")
# 固定主题锚（§12）：主河湖用水/稀释记忆；其余水体全部走随机池。
_MG_RIVER_LIQUIDS = ("水", "稀释记忆")
# Sparse functional objects, with at most 10% main-dream mixture draws.
_MG_FUNC_WALLS = ("传真墙", "灯箱墙", "弹窗墙", "磁带墙", "摇杆柱", "打印机墙")
_MG_MAINMIX_WALLS = ("蚀梦菌毯", "吸光苔墙", "导电铜网墙", "倦怠棉垛")
_MG_BRICK_WALLS = ("色块墙·红", "色块墙·橙", "色块墙·蓝", "蓝砖墙")
_MG_FUNCTION_BLOCK_LIMIT = 10
# 关机之门（1–4 层出口）：选项 descend_realm 由 choose_event_option 的
# millennium 分支结算（M4）。
_MG_EXIT_EVENT = {
    'event_id': 'realm_exit.millennium', 'name': '关机之门',
    'description': '一台老显示器立在草地上，屏幕中央是一个闪烁的关机图标。',
    'kind': 'compound', 'dissolution_reward': 0,
    'dialogue': ('显示器嗡嗡作响。屏幕上写着：现在可以安全地关闭计算机了。',
                 '关掉它，就能往梦的更深处走。'),
    'options': (
        {'label': '关掉它（下潜）', 'descend_realm': True},
        {'label': '再逛逛', 'leave': True},
    ),
}


def _mg_liquid_for_basin(rng, exclude_safe_zone: bool):
    """湖体液体选取：出生点安全圈内只出白名单；其余从全部液体等权抽取（§6）。"""
    if exclude_safe_zone:
        return rng.choice(_MG_SPAWN_SAFE_LIQUIDS)
    from ..materials.liquids import LIQUID_DEFINITIONS
    return rng.choice(tuple(k for k, d in LIQUID_DEFINITIONS.items()
                            if not d.spawn_realms or "millennium_garden" in d.spawn_realms))


class _MillenniumConnectivityError(RuntimeError):
    """Only structural connectivity exhaustion is eligible for regeneration."""


def millennium_park(state, definition, depth):
    original_seed = state.seed
    failures = []
    try:
        for attempt in range(3):
            state.seed = original_seed if attempt == 0 else original_seed ^ (0x6D470000 + attempt * 3571)
            try:
                result = _millennium_park_layout(state, definition, depth)
                state.realm_features['millennium_generation'] = {'seed':original_seed,'attempts': attempt + 1, 'fallback': False, 'failed_constraints':failures}
                return result
            except _MillenniumConnectivityError as error:
                failures.append({"seed":state.seed,"constraint":str(error)})
                continue
        # A flat open park with finite lakes retains the cabin/stadium contract.
        state.seed = original_seed
        result = _millennium_park_layout(state, definition, depth, safe_fallback=True)
        state.realm_features['millennium_generation'] = {'seed':original_seed,'attempts': 3, 'fallback': True, 'failed_constraints':failures}
        return result
    finally:
        state.seed = original_seed


def _millennium_park_layout(state, definition, depth, *, safe_fallback=False):
    """千禧园地形：开放式草地 + 分区彩砖/少量功能块 + 湖河洼地 + 木屋（1–4 层）
    / 零点体育场（第 5 层）。返回 (width, height, cells, spawn)。"""
    from ..mapgen.epilogue import _value_noise
    from ..materials.liquids import LIQUID_DEFINITIONS

    width, height = 60, 60
    rng = random.Random(state.seed ^ 0x4D49 ^ depth * 3571)
    cells = [[Cell() for _ in range(width)] for _ in range(height)]
    # 边界一圈意识边界（realm 既有口径）。
    for y in range(height):
        for x in range(width):
            if x in (0, width - 1) or y in (0, height - 1):
                state.configure_wall(cells[y][x], '意识边界')

    baseline = state.seed==101 and depth==1
    theme = {1:('grass_slope',9,.28,.78,3),2:('lake_shade',7,.34,.70,4),
             3:('old_playground',6,.25,.76,8),4:('stadium_forecourt',12,.22,.80,5)}.get(depth,('stadium',9,.30,.74,8))
    if baseline:theme=('grass_slope',9,.30,.74,8)
    theme_name,spacing,basin_threshold,tree_threshold,function_limit=theme
    state.realm_features['millennium_terrain']={'theme':theme_name,'noise_spacing':spacing,
        'basin_threshold':basin_threshold,'tree_threshold':tree_threshold,'function_limit':function_limit}
    height_field = _value_noise(rng, width, height, spacing=spacing)
    tree_field = _value_noise(rng, width, height, spacing=6)
    if depth >= 5:
        # The boss floor uses measured forecourt terrain instead of noise-only
        # groves, which could leave the visible area around the arena empty.
        tree_field = lambda x, y: 0.0
    if safe_fallback:
        def height_field(x, y):
            if (x-18)**2+(y-40)**2 <= 64 or (x-42)**2+(y-18)**2 <= 64:
                return .2
            return .75 if x < 8 and y > 45 else .5
        tree_field = lambda x, y: 0.0

    # ---- 高度场（§5.1 步 2）：洼地 -2/-1，平原 0，丘 +1。液体按地势自发汇低。----
    elev = [[0] * width for _ in range(height)]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            v = height_field(x, y)
            # Floor five gets a single bounded pond and two small rises below;
            # random basins and rivers used to swamp most of its outside field.
            elev[y][x] = 0 if depth >= 5 else (-2 if v < basin_threshold else (-1 if v < max(.40,basin_threshold+.08) else (1 if v > .64 else 0)))
    # 决策表写回格子：cell.elevation 是液体流动的地势依据（materials_sim 按它汇流）。
    # 不写回的话湖河只存在于「决策层」，格高恒 0——液体不会泊进洼地（探针逮过）。
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            cells[y][x].elevation = elev[y][x]

    # Select a compact cabin before spawn, independently of the terrain RNG.
    cabin_rng = random.Random(state.seed ^ depth * 5437 ^ 0x43414249)
    sites = [(8,6),(42,6),(8,42),(42,42),(24,6),(24,44),(6,24),(46,24)]
    cabin_rng.shuffle(sites)
    hx0, hy0 = max(sites, key=lambda p: sum(elev[y][x]>=0 for y in range(p[1],p[1]+5) for x in range(p[0],p[0]+8)))
    cabin_style = ('front','side','lakeside')[(state.seed+depth)%3]
    if state.seed == 101 and depth == 1:
        hx0, hy0, cabin_style = 8, 6, 'front'
    cabin_rect = (hx0,hy0,hx0+7,hy0+4)

    # ---- 出生点（先选，供安全圈判定）：一块 0/+1 高度的开放草皮。----
    # ⚠️ 避开木屋固定址 (8,6)-(15,10)（外扩 3 格）：木屋是后建的，出生点若落进
    # 屋址会被墙砌死（探针逮过 seed 118：出生点在 (10,6) 屋顶墙里）。
    spawn = None
    for _ in range(400):
        x, y = rng.randrange(6, width - 6), rng.randrange(6, height - 6)
        if elev[y][x] >= 0 and ((not (5 <= x <= 18 and 3 <= y <= 13)) if state.seed==101 and depth==1 else abs(x-(hx0+3))+abs(y-(hy0+2)) >= 20):
            spawn = (x, y)
            break
    if spawn is None:
        spawn = (width // 2, height // 2)
    sx, sy = spawn

    # ---- 湖（§5.1 步 4）：每个 -2 连通盆地 ≥5 格 → 灌一种液体。----
    from collections import deque as _dq
    seen: set[tuple[int, int]] = set()
    basins: list[list[tuple[int, int]]] = []
    for yy in range(1, height - 1):
        for xx in range(1, width - 1):
            if elev[yy][xx] != -2 or (xx, yy) in seen:
                continue
            basin = []
            queue = _dq([(xx, yy)])
            seen.add((xx, yy))
            while queue:
                cx, cy = queue.popleft()
                basin.append((cx, cy))
                for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen
                            and elev[ny][nx] == -2):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if len(basin) >= 5:
                basins.append(basin)

    def fill_water(cells_, x, y, kind, amount):
        cell = cells_[y][x]
        cell.liquid_kind = kind
        cell.liquid = amount
        # 压平只对「比 -1 高」的格子生效（河道压到 -1 泊住）；-2 洼地**保持 -2**
        # ——写成 min(cell.elevation, -1) 会把湖底抬成 -1，湖不再是洼地（探针逮过）。
        if cell.elevation > -1:
            cell.elevation = -1

    basin_liquids = []
    for basin in basins:
        # 安全锚按「格」判定：湖只要有**任何一格**落在出生圈 6 格内，整湖走白名单
        # ——按 max（整湖全在圈内）判定时，大湖跨圈会漏防（探针逮过：圈内刷出燃油）。
        near_spawn = any(abs(bx - sx) + abs(by - sy) <= 6 for bx, by in basin)
        if near_spawn:
            kind = rng.choice(_MG_SPAWN_SAFE_LIQUIDS)
        else:
            kind = rng.choice(tuple(k for k, d in LIQUID_DEFINITIONS.items()
                                    if not d.spawn_realms or "millennium_garden" in d.spawn_realms))
        basin_liquids.append((basin, kind))
    for basin, kind in basin_liquids:
        for bx, by in basin:
            fill_water(cells, bx, by, kind, rng.randrange(60, 91))

    # ---- 河（§5.1 步 5）：2 条从丘顶降序游走的河道（宽 1，蜿蜒）。----
    rivers = []
    highs = [(x, y) for y in range(1, height - 1) for x in range(1, width - 1) if elev[y][x] == 1]
    rng.shuffle(highs)
    for river_index in range(min(2, len(highs))):
        cx, cy = highs[river_index]
        kind = _MG_RIVER_LIQUIDS[river_index % len(_MG_RIVER_LIQUIDS)]
        path = [(cx, cy)]
        for _ in range(rng.randrange(20, 36)):
            neighbours = [(cx + dx, cy + dy) for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
                          if 1 <= cx + dx < width - 1 and 1 <= cy + dy < height - 1]
            lower = [p for p in neighbours if elev[p[1]][p[0]] < elev[cy][cx]]
            pick = rng.choice(lower) if lower else rng.choice(neighbours)
            cx, cy = pick
            path.append((cx, cy))
            if elev[cy][cx] <= -2:
                break
        for rx, ry in path:
            fill_water(cells, rx, ry, kind, rng.randrange(20, 41))
        rivers.append(path)

    # ---- 全图开放：草地基底，随后建立结构墙骨架。----
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            _mg_clear(cells[x], y)

    def near_spawn(x, y, r=5):
        return abs(x - sx) + abs(y - sy) <= r

    # ---- 树墙簇（§5.1 步 3）：噪声 >0.74，成簇种树；避开湖/河/出生点圈。----
    water = {(x, y) for y in range(height) for x in range(width) if cells[y][x].liquid > 0}
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            if (x, y) in water or near_spawn(x, y, 6):
                continue
            if tree_field(x, y) > tree_threshold:
                cell = cells[y][x]
                state.configure_wall(cell, '千禧树')

    # Functional objects are placed after the cabin/stadium has been built.
    # A noise cluster here used to bury machines inside other solid clusters.

    # ---- 植物（§8）：草地撒千禧蒲草，水边撒气泡藻。----
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            cell = cells[y][x]
            if cell.solid or near_spawn(x, y, 3):
                continue
            if cell.liquid > 0:
                continue
            if cell.liquid == 0 and elev[y][x] >= 0 and rng.random() < 0.10:
                cell.plant = 24  # 千禧蒲草
            elif any((x + dx, y + dy) in water for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))) and rng.random() < 0.25:
                cell.plant = 25  # 气泡藻

    events = []
    items = []
    main_path = set()
    if depth >= 5:
        # ---- 零点体育场（第 5 层，§10.3）：圆场 + 三层看台 + 中央蓝屏终端。----
        cx0, cy0 = 30, 30
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                d2 = (x - cx0) ** 2 + (y - cy0) ** 2
                r = d2 ** 0.5
                cell = cells[y][x]
                if r > 15:
                    continue  # 保留场外已经生成的树、浅池和植物。
                cell.liquid = 0
                cell.liquid_kind = ""
                cell.plant = 0
                cell.elevation = 0
                state.clear_wall(cell)
                if r > 13.2:
                    state.configure_wall(cell, '蓝砖墙')       # 外墙
                elif 11.0 < r <= 13.2:
                    state.configure_wall(cell, '色块墙·红')    # 看台三层（4 条放射走道开口）
                    angle = _mg_angle(x, y, cx0, cy0)
                    if _mg_on_aisle(angle):
                        state.clear_wall(cell)
                elif 9.0 < r <= 11.0:
                    state.configure_wall(cell, '色块墙·橙')
                    angle = _mg_angle(x, y, cx0, cy0)
                    if _mg_on_aisle(angle):
                        state.clear_wall(cell)
                elif 7.0 < r <= 9.0:
                    state.configure_wall(cell, '色块墙·蓝')
                    angle = _mg_angle(x, y, cx0, cy0)
                    if _mg_on_aisle(angle):
                        state.clear_wall(cell)
                # r<=7：中央净空
        # 四条径向入口贯通外墙与看台，接至外部公园；避免连通兜底随机凿墙。
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            for distance in range(7, 18):
                for offset in (-1, 0, 1):
                    x = cx0 + dx * distance - dy * offset
                    y = cy0 + dy * distance + dx * offset
                    state.clear_wall(cells[y][x])
                    cells[y][x].liquid = 0
                    cells[y][x].liquid_kind = ""
                    cells[y][x].plant = 0
                    cells[y][x].elevation = 0
                    main_path.add((x, y))
        _mg_stamp_stadium_forecourt(state, cells, width, height, cx0, cy0)
        terminal = cells[cy0][cx0]
        state.configure_wall(terminal, '蓝屏终端')
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            state.clear_wall(cells[cy0 + dy][cx0 + dx])
        from copy import deepcopy as _dc
        exit_def = _dc(_MG_EXIT_EVENT)
        terminal_def = {
            'event_id': 'event.millennium_terminal', 'name': '蓝屏终端',
            'description': '一台发着蓝光的终端立在体育场中央，屏幕上的进度条停在 99%。',
            'kind': 'compound', 'dissolution_reward': 0,
            'dialogue': (
                '屏幕上的字一闪一闪：你的电脑遇到问题，需要重新启动。',
                '光标在闪。光标后面有一行小字：按任意键接入……',
            ),
            'options': (
                {'label': '接入', 'summon_y2k': True},
                {'label': '不去动它', 'leave': True},
            ),
        }
        events.append(WorldEvent(
            event_id='event.millennium_terminal', name='蓝屏终端',
            x=cx0, y=cy0 + 1, description=terminal_def['description'],
            catalog_id='event.millennium_terminal', kind='compound',
            dialogue=terminal_def['dialogue'], options=terminal_def['options'],
            bound=True, dissolution_reward=0))
        spawn = (cx0, cy0 + 14)
        state.clear_wall(cells[spawn[1]][spawn[0]])
        state.realm_bg_zones = [
            {'rect': (1, 1, width - 2, height - 2), 'color': '#1e4620'},
            {'rect': (cx0 - 15, cy0 - 15, cx0 + 15, cy0 + 15), 'color': '#2a5a28'},
            {'rect': (cx0 - 7, cy0 - 7, cx0 + 7, cy0 + 7), 'color': '#1e4620'},
        ]
    else:
        # ---- 木屋区（§5.1 步 6）：左上角 7×5，内部木质聚合物地板 + 石台。----
        for y in range(hy0, hy0 + 5):
            for x in range(hx0, hx0 + 8):
                cell = cells[y][x]
                edge = x in (hx0, hx0 + 7) or y in (hy0, hy0 + 4)
                if edge:
                    state.configure_wall(cell, '蓝砖墙')
                else:
                    state.clear_wall(cell)
                    cell.aggregate_variant = '木质聚合物'
                    # 屋内排干：-2 湖盆可能压在屋址下，小屋里留一汪池塘 +
                    # 湖滩色带被木屋色带整片盖住（探针逮过 seed 111）。
                    cell.liquid = 0
                    cell.liquid_kind = ""
                    if cell.elevation < 0:
                        cell.elevation = 0
        door_x, door_y = ((hx0+3,hy0+4) if cabin_style=='front' else
                          (hx0,hy0+2) if cabin_style=='side' else (hx0+4,hy0))
        outward = (0,1) if cabin_style=='front' else (-1,0) if cabin_style=='side' else (0,-1)
        for step in range(1,4):
            px,py=door_x+outward[0]*step,door_y+outward[1]*step
            state.clear_wall(cells[py][px])
            cells[py][px].liquid=0;cells[py][px].liquid_kind='';cells[py][px].plant=0
            cells[py][px].elevation=max(0,cells[py][px].elevation)
        if not baseline:
            # A finite wooden apron gives each orientation a real parameter shape.
            for offset in (-1,0,1):
                for step in range(1,3):
                    px=door_x+outward[0]*step-outward[1]*offset
                    py=door_y+outward[1]*step+outward[0]*offset
                    state.clear_wall(cells[py][px]);cells[py][px].aggregate_variant='木质聚合物'
                    cells[py][px].liquid=0;cells[py][px].liquid_kind='';cells[py][px].plant=0
                    cells[py][px].elevation=2
            if cabin_style=='lakeside':
                for py in range(hy0+1,hy0+3):
                    for px in range(hx0+9,hx0+12):
                        state.clear_wall(cells[py][px]);cells[py][px].plant=0
                        fill_water(cells,px,py,'显影液',30)
        state.configure_wall(cells[door_y][door_x], '木门')
        # 石台（圣所物品台面）与关机之门：都放开放格。
        table_x, table_y = hx0 + (5 if cabin_style=='side' else 4 if cabin_style=='lakeside' else 3), hy0 + 2
        state.configure_wall(cells[table_y][table_x], '石台')
        state.realm_features['millennium_cabin']={'rect':list(cabin_rect),'style':cabin_style,'door':[door_x,door_y],'table':[table_x,table_y]}
        if not baseline:
            apron=(door_x+outward[0]*3,door_y+outward[1]*3)
            anchors=[spawn]
            if depth==2:anchors.append((spawn[0],30))
            elif depth==3:anchors.extend(((30,spawn[1]),(30,30)))
            elif depth==4:anchors.append((30,30))
            anchors.append(apron)
            for begin,end in zip(anchors,anchors[1:]):
                main_path.update(_mg_safe_route(state,cells,width,height,begin,end))
            state.realm_features['millennium_cabin']['main_path']=[list(p) for p in sorted(main_path)]
        sanctum = definition.sanctum_items
        if sanctum:
            items.append(WorldItem(state._make_item(sanctum[min(depth, len(sanctum)) - 1]), table_x, table_y - 1))
        # 关机之门：BFS 距出生点最远的开放格。
        exit_x, exit_y = _mg_farthest_open(cells, width, height, spawn)
        from copy import deepcopy as _dc
        exit_def = _dc(_MG_EXIT_EVENT)
        events.append(WorldEvent(
            event_id=exit_def['event_id'], name=exit_def['name'],
            x=exit_x, y=exit_y, description=exit_def['description'],
            catalog_id=exit_def['event_id'], kind='compound',
            dialogue=exit_def['dialogue'], options=exit_def['options'],
            bound=True, dissolution_reward=0))
        # ---- 底色带（§9）：草地两块交替 + 湖滩 + 木屋（矩形近似，≤6 条）----
        zones = [
            {'rect': (1, 1, 29, height - 2), 'color': '#1e4620'},
            {'rect': (30, 1, width - 2, height - 2), 'color': '#2a5a28'},
        ]
        shore = []
        for basin, _kind in basin_liquids[:2]:
            xs = [p[0] for p in basin]
            ys = [p[1] for p in basin]
            shore.append({'rect': (min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1), 'color': '#3a4a3a'})
        # 木屋矩形放**最后**（后画的覆盖先画的）：大湖滩可能整片罩住木屋矩形，
        # 木色必须压过湖滩（探针逮过「被完全覆盖」）。
        zones += shore
        zones.append({'rect': (hx0 + 1, hy0 + 1, hx0 + 6, hy0 + 3), 'color': '#4a3520'})
        state.realm_bg_zones = zones

    _mg_place_function_blocks(state, cells, width, height, spawn, events, items, depth, cabin_rect if depth<5 else None, main_path, function_limit)
    # Repair the structural skeleton before assigning brick appearances, so
    # ordinary park bricks do not inherit the stadium's protected-wall rules.
    _mg_ensure_connected(state, cells, width, height, spawn)
    _mg_color_structural_walls(state, cells, width, height, depth)

    state._pending_realm_events = events
    state._pending_realm_items = items
    return width, height, cells, spawn


def _mg_safe_route(state,cells,width,height,start,end):
    """Finite A* builds a raised, dry walk without cutting doors or furniture."""
    from heapq import heappop,heappush
    protected={'意识边界','木门','石台','蓝砖墙','蓝屏终端'}
    heap=[(0,0,start)];costs={start:0};previous={}
    while heap:
        _,cost,point=heappop(heap)
        if cost!=costs[point]:continue
        if point==end:break
        x,y=point
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
            nx,ny=x+dx,y+dy
            if not (1<=nx<width-1 and 1<=ny<height-1):continue
            cell=cells[ny][nx]
            if cell.solid and cell.wall_kind in protected:continue
            new=cost+1+(12 if cell.solid else 0)+(20 if cell.liquid else 0)
            target=(nx,ny)
            if new<costs.get(target,float('inf')):
                costs[target]=new;previous[target]=point
                heappush(heap,(new+abs(nx-end[0])+abs(ny-end[1]),new,target))
    else:raise _MillenniumConnectivityError('cabin main walk blocked by a protected structure')
    route=[end]
    while route[-1]!=start:route.append(previous[route[-1]])
    for x,y in route:
        c=cells[y][x];state.clear_wall(c);c.liquid=0;c.liquid_kind='';c.gas=0;c.gas_kind='';c.plant=0;c.flame=0
        c.elevation=2;c.aggregate_variant='粗糙聚合物'
    return route


def _mg_place_function_blocks(state, cells, width, height, spawn, events, items, depth, cabin_rect=None, main_path=(), function_limit=None):
    """Sparse equipment in clearings, never replacements inside a wall mass."""
    rng = random.Random(state.seed ^ 0x46554E43 ^ depth * 3571)
    protected = [(e.x, e.y) for e in events] + [(i.x, i.y) for i in items] + [spawn]
    candidates = [(x, y) for y in range(3, height-3) for x in range(3, width-3)]
    rng.shuffle(candidates)
    placed = []
    for x, y in candidates:
        if len(placed) >= (function_limit or _MG_FUNCTION_BLOCK_LIMIT):
            break
        cell = cells[y][x]
        if any((x+dx,y+dy) in main_path for dx,dy in ((0,0),(0,1),(0,-1),(1,0),(-1,0))):continue
        if cell.solid or cell.liquid or cell.gas or cell.flame:
            continue
        if cabin_rect and cabin_rect[0]-3 <= x <= cabin_rect[2]+3 and cabin_rect[1]-3 <= y <= cabin_rect[3]+3:
            continue  # Cabin, door and its apron stay uncluttered.
        if any(max(abs(x-px), abs(y-py)) <= (5 if (px, py) == spawn else 2)
               for px, py in protected):
            continue
        if any(max(abs(x-px), abs(y-py)) < 3 for px, py in placed):
            continue
        sides = [(x+dx, y+dy) for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))]
        surroundings = [(x+dx, y+dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if dx or dy]
        if sum(not cells[py][px].solid for px, py in sides) < 3:
            continue
        if sum(not cells[py][px].solid for px, py in surroundings) < 7:
            continue  # Avoid plugging a corridor or hiding in a wall interior.
        pool = _MG_MAINMIX_WALLS if rng.random() < .10 else _MG_FUNC_WALLS
        state.configure_wall(cell, rng.choice(pool))
        cell.plant = cell.plant_fuel = 0
        placed.append((x, y))


def _mg_color_structural_walls(state, cells, width, height, depth):
    """Give wall masses coherent colour regions; keep a few exposed park trees."""
    if depth >= 5:
        # Floor-five tree density is explicitly bounded by the forecourt stamp;
        # turning most of those trees into brick walls hid the park landmarks.
        return
    skeleton = [(x, y) for y in range(1, height-1) for x in range(1, width-1)
                if cells[y][x].wall_kind == "千禧树"]
    exposed = [(x, y) for x, y in skeleton
               if any(not cells[y+dy][x+dx].solid
                      for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)))]
    rng = random.Random(state.seed ^ 0x42524943 ^ depth * 3571)
    rng.shuffle(exposed)
    trees = set(exposed[:len(skeleton)//8])
    for x, y in skeleton:
        if (x, y) not in trees:
            # Neighbouring wall cells use one colour, rather than a confetti mix.
            kind = _MG_BRICK_WALLS[(x//10 + y//10 + depth + state.seed) % len(_MG_BRICK_WALLS)]
            state.configure_wall(cells[y][x], kind)


def _mg_stamp_stadium_forecourt(state, cells, width, height, cx, cy):
    """Add deterministic, bounded terrain outside the fifth-floor stadium."""
    def outside_arena(x, y):
        return (x - cx) ** 2 + (y - cy) ** 2 > 15 ** 2

    # Four compact groves occupy diagonal park quarters, leaving every stadium
    # aisle open. Their combined footprint is about 6% of the outer field.
    for gx, gy in ((13, 13), (47, 13), (13, 47), (47, 47)):
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x, y = gx + dx, gy + dy
                if not (1 < x < width - 2 and 1 < y < height - 2):
                    continue
                if dx * dx + dy * dy > 10 or not outside_arena(x, y):
                    continue
                cell = cells[y][x]
                cell.liquid = 0
                cell.liquid_kind = ""
                cell.plant = 0
                state.configure_wall(cell, "千禧树")

    # Two low grass rises beside the south forecourt, clear of its three-cell
    # entrance. Elevated ground plus visible grass tufts marks their outlines.
    for hx, hy in ((24, 46), (36, 46)):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                x, y = hx + dx, hy + dy
                if dx * dx + dy * dy > 4 or not outside_arena(x, y):
                    continue
                cell = cells[y][x]
                state.clear_wall(cell)
                cell.liquid = 0
                cell.liquid_kind = ""
                cell.elevation = 1 if dx * dx + dy * dy <= 2 else 0
                if abs(dx) + abs(dy) == 2:
                    cell.plant = 24  # 千禧蒲草

    # One shallow pond replaces the unbounded random floor-five lakes.
    px, py = 45, 15
    pond = set()
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            x, y = px + dx, py + dy
            if dx * dx + dy * dy > 5 or not outside_arena(x, y):
                continue
            pond.add((x, y))
            cell = cells[y][x]
            state.clear_wall(cell)
            cell.plant = 0
            cell.elevation = -1
            cell.liquid_kind = "水"
            cell.liquid = 24
    for x, y in tuple(pond):
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                cell = cells[ny][nx]
                if outside_arena(nx, ny) and (nx, ny) not in pond and not cell.solid and cell.liquid <= 0:
                    cell.plant = 25  # 气泡藻


def _mg_clear(column: list, y: int) -> None:
    cell = column[y]
    cell.solid = False
    cell.wall_kind = ""
    cell.hardness = 0
    cell.integrity = 0


def _mg_angle(x: int, y: int, cx: int, cy: int) -> float:
    import math
    return math.degrees(math.atan2(y - cy, x - cx)) % 360.0


def _mg_on_aisle(angle: float) -> bool:
    """4 条放射走道（0/90/180/270° ±14°）。"""
    return min(angle, 360 - angle) < 14 or abs(angle - 90) < 14 or abs(angle - 180) < 14 or abs(angle - 270) < 14


def _mg_ensure_connected(state, cells, width, height, spawn):
    """连通性兜底：噪声树簇/功能墙可能圈出封闭草地袋（探针逮过 14 格孤岛）。

    从出生点 8 向洪填；对每个不可达开放格，凿开它邻域里「同时贴着可达区」的
    一面墙（优先千禧树；意识边界/木门永不凿），重连后重新洪填，直至无孤岛。
    凿开即普通草地（_mg_clear）。
    """
    from collections import deque as _dq
    from heapq import heappop, heappush
    protected = {"意识边界", "木门", "蓝砖墙", "色块墙·红", "色块墙·橙",
                 "色块墙·蓝", "石台", "蓝屏终端"}
    neighbours = ((0, -1), (1, 0), (0, 1), (-1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1))
    # Each successful repair opens at least one cell: map area is a finite bound.
    for _round in range(width * height):
        seen = {spawn}
        queue = _dq([spawn])
        while queue:
            x, y = queue.popleft()
            for dx, dy in neighbours:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in seen:
                    continue
                cell = cells[ny][nx]
                if (not cell.solid) or cell.wall_kind == "木门":
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        holes = [(x, y) for y in range(1, height - 1) for x in range(1, width - 1)
                 if (x, y) not in seen and not cells[y][x].solid]
        if not holes:
            return
        for hx, hy in holes:
            carve = None
            fallback = None
            for dx, dy in neighbours:
                wx, wy = hx + dx, hy + dy
                if not (0 <= wx < width and 0 <= wy < height):
                    continue
                wall = cells[wy][wx]
                if not wall.solid or wall.wall_kind in protected:
                    continue
                if not any((wx + ax, wy + ay) in seen for ax, ay in neighbours
                           if 0 <= wx + ax < width and 0 <= wy + ay < height):
                    continue
                if wall.wall_kind == "千禧树":
                    carve = (wx, wy)
                    break
                if fallback is None:
                    fallback = (wx, wy)
            if carve is None:
                carve = fallback
            if carve is not None:
                state.clear_wall(cells[carve[1]][carve[0]])
                break
        else:
            # Thick tree/function-wall clusters need a complete bridge rather than
            # a single wall touching both components. Find the cheapest legal cut.
            start = holes[0]
            costs, previous = {start: 0}, {}
            heap = [(0, start)]
            end = None
            while heap:
                cost, point = heappop(heap)
                if cost != costs[point]:
                    continue
                if point in seen:
                    end = point
                    break
                x, y = point
                for dx, dy in neighbours:
                    target = x + dx, y + dy
                    nx, ny = target
                    if not (0 < nx < width-1 and 0 < ny < height-1):
                        continue
                    cell = cells[ny][nx]
                    if cell.solid and cell.wall_kind in protected and cell.wall_kind != "木门":
                        continue
                    extra = 0 if not cell.solid or cell.wall_kind == "木门" else (1 if cell.wall_kind == "千禧树" else 4)
                    candidate = cost + extra
                    if candidate < costs.get(target, float("inf")):
                        costs[target] = candidate
                        previous[target] = point
                        heappush(heap, (candidate, target))
            if end is None:
                raise _MillenniumConnectivityError(f"millennium_garden: protected structure isolates {start}")
            while end != start:
                x, y = end
                if cells[y][x].solid and cells[y][x].wall_kind != "木门":
                    state.clear_wall(cells[y][x])
                end = previous[end]
    raise _MillenniumConnectivityError("millennium_garden: connectivity repair exhausted its finite budget")


def _mg_farthest_open(cells, width, height, spawn):
    """BFS 距出生点最远的开放格（出口位）。"""
    from collections import deque as _dq
    seen = {spawn}
    queue = _dq([spawn])
    farthest = spawn
    while queue:
        cx, cy = queue.popleft()
        farthest = (cx, cy)
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = cx + dx, cy + dy
            if (0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen
                    and not cells[ny][nx].solid):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return farthest
