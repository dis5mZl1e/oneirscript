"""通用环境填充：为独立生成器的地图补上常规地形内容。

主梦走 GenerationMixin._generate_cells，会生成地板变体、植物、地面容器、
液体、气体与功能墙。梦中梦与深层边界有自己的地形生成器（同心环廊 / 深层
几何外圈等），它们只搭了"骨架"，没有接这条内容流水线：于是出现"地板只有
一种、没有变体、没有植物与液气"的空场。

本模块把常规内容流水线里与骨架无关的那部分抽出来，作用在已经生成好的
cells 上，供这些独立生成器在收尾时调用：

- 基础地板变体（按调色板连片铺设，不改变通行性）；
- 稀有地板 / 扩展地板（复用主梦的连片算法）；
- 植物（复用主梦的连片算法与位面植物池）；
- 地面容器（默认避开 1 格宽通道与门位，防止把唯一通路堵死）；
- 液体小团 / 气体云（复用主梦的液气池与成团规则）。

所有随机流都由 seed 独立派生，不改变调用方已有的随机序列。
protected 内的格子（剧情锚点、出生点、机关、NPC 站位等）在填充前后
保持原样。
"""

from __future__ import annotations

from collections import deque
import random

from .constants import EXPOSED_ONLY_WALLS
from .generation import GenerationMixin as G
from ..materials import (
    gas_pool_for_depth,
    liquid_pool_for_depth,
    plant_profile,
)

# 通用地板调色板：不含位面专属地板（那些由 spawn_realms 过滤）。
COMMON_FLOOR_PALETTE = (
    "普通聚合物", "普通聚合物", "柔软聚合物", "粗糙聚合物",
    "反光聚合物", "吸声聚合物",
)

# 位面专属基础地板调色板（只影响地面材质，不改变通行性）。
REALM_FLOOR_PALETTES: dict[str, tuple[str, ...]] = {
    "door_corridor": (
        "普通聚合物", "普通聚合物", "反光聚合物", "吸声聚合物",
        "柔软聚合物", "粗糙聚合物",
    ),
    "ebbing_hall": (
        "普通聚合物", "普通聚合物", "粗糙聚合物", "反光聚合物", "吸声聚合物",
    ),
    "millennium_garden": (
        "普通聚合物", "普通聚合物", "反光聚合物", "金属聚合物", "粗糙聚合物",
    ),
    "epilogue": (
        "普通聚合物", "普通聚合物", "反光聚合物", "吸声聚合物",
        "粗糙聚合物", "金属聚合物",
    ),
}

# 位面专属地板变体只允许在位面对应时出现（与材料定义同口径）。
_GENERIC_FLOOR_VARIANTS = frozenset(COMMON_FLOOR_PALETTE) | {
    "普通聚合物", "木质聚合物", "海绵聚合物", "金属聚合物", "灼热聚合物",
    "梦境绒毯", "冰面", "星图地", "书页地", "月壤", "棋盘格地板",
    "绝热层", "压电地板", "空鼓地板", "压力地板",
    "传送带·北", "传送带·东", "传送带·南", "传送带·西",
}


def _open_cells(cells, protected, margin: int = 1):
    """可填充的开放格：非实心、无墙体/容器、非保护格。"""
    height, width = len(cells), len(cells[0])
    return [
        (x, y)
        for y in range(margin, height - margin)
        for x in range(margin, width - margin)
        if (not cells[y][x].solid and not cells[y][x].wall_kind
            and (x, y) not in protected)
    ]


def _snapshot(cells, cells_to_keep):
    snapshot = {}
    for x, y in cells_to_keep:
        cell = cells[y][x]
        snapshot[(x, y)] = (
            cell.aggregate_variant, cell.plant, cell.liquid, cell.liquid_kind,
            cell.gas, cell.gas_kind,
        )
    return snapshot


def _restore(cells, snapshot):
    for (x, y), values in snapshot.items():
        cell = cells[y][x]
        (cell.aggregate_variant, cell.plant, cell.liquid, cell.liquid_kind,
         cell.gas, cell.gas_kind) = values


def _palette_variants(palette, realm_id: str):
    """把调色板里不允许在本位面出现的地板变体过滤掉。"""
    from ..materials.floors import FLOOR_DEFINITIONS

    out = []
    for variant in (palette or COMMON_FLOOR_PALETTE):
        definition = FLOOR_DEFINITIONS.get(variant)
        if definition is not None and definition.spawn_realms and realm_id not in definition.spawn_realms:
            continue
        out.append(variant)
    return tuple(out) or COMMON_FLOOR_PALETTE


def _paint_base_floors(cells, candidates, palette, coverage, rng):
    """按连片方式给开放格铺基础地板变体，保留一部分空地留白。"""
    if not palette or coverage <= 0 or not candidates:
        return 0
    remaining = set(candidates)
    target = int(len(candidates) * coverage)
    painted = 0
    variants = list(palette)
    rng.shuffle(variants)
    cursor = 0
    while remaining and painted < target:
        start = rng.choice(tuple(remaining))
        hint = variants[cursor % len(variants)]
        cursor += 1
        patch = []
        seen = {start}
        queue = deque([start])
        cap = rng.randint(8, 26)
        while queue and len(patch) < cap:
            x, y = queue.popleft()
            if (x, y) not in remaining:
                continue
            patch.append((x, y))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in remaining and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        if not patch:
            remaining.discard(start)
            continue
        for x, y in patch:
            cells[y][x].aggregate_variant = hint
            if hint in ("干纸堆", "书页地"):
                cells[y][x].floor_fuel = 9
            remaining.discard((x, y))
        painted += len(patch)
    return painted


def _spawn_containers(cells, candidates, rng, chance, wall_kinds, min_open_neighbors, doorway_guard):
    """地面容器：环境道具，落点必须留有绕行空间。"""
    placed = 0
    height, width = len(cells), len(cells[0])
    for x, y in candidates:
        if rng.random() >= chance:
            continue
        cell = cells[y][x]
        if cell.solid or cell.wall_kind or cell.liquid or cell.gas:
            continue
        if doorway_guard and any(
            wall_kinds.get((x + dx, y + dy)) == "门"
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            continue
        open_dirs = [
            (dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= x + dx < width and 0 <= y + dy < height
            and not cells[y + dy][x + dx].solid
            and not cells[y + dy][x + dx].wall_kind
        ]
        open_neighbors = len(open_dirs)
        if open_neighbors < min_open_neighbors:
            continue
        # 1 格宽通道的中段：两侧都是墙、只有前后两口——容器会堵死唯一通路。
        if (open_neighbors == 2
                and open_dirs[0] == (-open_dirs[1][0], -open_dirs[1][1])):
            continue
        neighbor_kinds = {
            wall_kinds.get((x + 1, y)), wall_kinds.get((x - 1, y)),
            wall_kinds.get((x, y + 1)), wall_kinds.get((x, y - 1)),
        }
        if not neighbor_kinds.isdisjoint(EXPOSED_ONLY_WALLS):
            continue
        G.configure_container(cell, rng)
        placed += 1
    return placed


def _grow_liquid_patches(cells, candidates, rng, pool, patch_count):
    """液体小团（每团 4–14 格）；只在开放空地，不碰保护格与容器。"""
    if not pool or patch_count <= 0:
        return 0
    available = set(candidates)
    total = sum(weight for _, weight in pool)

    def pick_kind():
        roll = rng.random() * total
        for kind, weight in pool:
            roll -= weight
            if roll < 0:
                return kind
        return pool[-1][0]

    painted = 0
    height, width = len(cells), len(cells[0])
    for _ in range(patch_count):
        if not available:
            break
        start = rng.choice(tuple(available))
        kind = pick_kind()
        patch = []
        seen = {start}
        queue = deque([start])
        cap = rng.randint(4, 14)
        while queue and len(patch) < cap:
            x, y = queue.popleft()
            if (x, y) not in available:
                continue
            cell = cells[y][x]
            # 液体不落在植物上：常规流水线里液体先于植物，植物不会长在水里。
            if cell.solid or cell.wall_kind or cell.liquid or cell.gas or cell.plant:
                continue
            patch.append((x, y))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in available and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        for x, y in patch:
            cells[y][x].liquid = rng.randint(40, 90)
            cells[y][x].liquid_kind = kind
            available.discard((x, y))
        painted += len(patch)
        for x, y in patch:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                available.discard((nx, ny))
    return painted


def _grow_gas_patches(cells, candidates, rng, pool, patch_count):
    """气体小团（每团 5–16 格）；与液体同款的轻量成团，替代大图上的全图气权计算。"""
    if not pool or patch_count <= 0:
        return 0
    available = set(candidates)
    total = sum(weight for _, weight in pool)

    def pick_kind():
        roll = rng.random() * total
        for kind, weight in pool:
            roll -= weight
            if roll < 0:
                return kind
        return pool[-1][0]

    painted = 0
    for _ in range(patch_count):
        if not available:
            break
        start = rng.choice(tuple(available))
        kind = pick_kind()
        patch = []
        seen = {start}
        queue = deque([start])
        cap = rng.randint(5, 16)
        while queue and len(patch) < cap:
            x, y = queue.popleft()
            if (x, y) not in available:
                continue
            cell = cells[y][x]
            if cell.solid or cell.wall_kind or cell.liquid or cell.gas:
                continue
            patch.append((x, y))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in available and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        for x, y in patch:
            cells[y][x].gas = rng.randint(40, 100)
            cells[y][x].gas_kind = kind
            available.discard((x, y))
        painted += len(patch)
        for x, y in patch:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                available.discard((nx, ny))
    return painted


def fill_environment(
    cells,
    *,
    seed: int,
    depth: int,
    realm_id: str = "",
    protected=(),
    palette=None,
    base_coverage: float = 0.55,
    preserve_existing_floors: bool = False,
    rare_floors: bool = True,
    new_floors: bool = True,
    plants: bool = True,
    plant_coverage: float | None = None,
    containers: bool = True,
    container_chance: float = 0.004,
    container_min_open_neighbors: int = 3,
    doorway_guard: bool = True,
    liquids: bool = True,
    gases: bool = True,
    liquid_patch_count: int | None = None,
    gas_rate: float = 0.012,
    spawn: tuple[int, int] | None = None,
):
    """给独立生成器的地图补常规环境内容，返回投放统计。

    调用方负责在填充后重建材料索引（如有液体/气体落地）。
    """
    height, width = len(cells), len(cells[0])
    protected_set = {(int(x), int(y)) for x, y in protected
                     if 0 <= int(x) < width and 0 <= int(y) < height}
    snapshot = _snapshot(cells, protected_set)
    floor_snapshot = {(x, y): (c.aggregate_variant, c.floor_fuel)
                      for y, row in enumerate(cells) for x, c in enumerate(row)
                      if preserve_existing_floors and c.aggregate_variant != "普通聚合物"}
    candidates = _open_cells(cells, protected_set)
    stats = {"base_floor": 0, "plants": 0, "containers": 0, "liquid": 0, "gas": 0}

    variants = _palette_variants(palette, realm_id)

    # ---- 1. 基础地板变体 ----
    stats["base_floor"] = _paint_base_floors(
        cells, candidates, variants, base_coverage,
        random.Random(seed ^ 0x0F100),
    )

    # ---- 2. 稀有 / 扩展地板（复用主梦连片算法；最后恢复保护格）----
    if rare_floors:
        G._grow_rare_floors(cells, random.Random(seed ^ 0x5F100), "", realm_id=realm_id)
    if new_floors:
        G._grow_new_floors(cells, depth, random.Random(seed ^ 0x6F200), "", realm_id=realm_id)

    for (x, y), (variant, fuel) in floor_snapshot.items():
        cells[y][x].aggregate_variant = variant
        cells[y][x].floor_fuel = fuel

    # ---- 3. 植物 ----
    if plants:
        profile = plant_profile("")
        coverage = profile.coverage if plant_coverage is None else plant_coverage
        before = sum(1 for row in cells for cell in row if cell.plant)
        G._grow_plants(
            cells, random.Random(seed ^ 0x9147), coverage,
            single_chance=profile.single_chance,
            patch_min=profile.patch_min,
            patch_max=profile.patch_max,
            depth=depth, realm_id=realm_id,
        )
        stats["plants"] = sum(1 for row in cells for cell in row if cell.plant) - before

    # ---- 4. 地面容器 ----
    if containers:
        wall_kinds = {
            (x, y): cells[y][x].wall_kind
            for y in range(height) for x in range(width)
            if cells[y][x].solid and cells[y][x].wall_kind
        }
        shuffled = list(candidates)
        container_rng = random.Random(seed ^ 0x2C07A)
        container_rng.shuffle(shuffled)
        stats["containers"] = _spawn_containers(
            cells, shuffled, container_rng, container_chance,
            wall_kinds, container_min_open_neighbors, doorway_guard,
        )

    # ---- 5. 液体小团 ----
    if liquids:
        liquid_pool = liquid_pool_for_depth(depth, realm_id=realm_id)
        if liquid_patch_count is None:
            liquid_patch_count = max(1, round(len(candidates) * 0.010 / 8))
        stats["liquid"] = _grow_liquid_patches(
            cells, candidates, random.Random(seed ^ 0x61A55),
            liquid_pool, liquid_patch_count,
        )

    # ---- 6. 气体云 ----
    # 小图走主梦的「全图气权 + 成团」投放；深层边界这类超大图逐格算气权
    # （每格一次 BFS 局部空间）代价太高，改用同款的轻量团生长，密度口径一致。
    if gases:
        gas_pool = gas_pool_for_depth(depth, realm_id=realm_id)
        if len(candidates) > 4000:
            patch_count = max(2, round(len(candidates) * 0.0012))
            stats["gas"] = _grow_gas_patches(
                cells, candidates, random.Random(seed ^ 0x6A5C10),
                gas_pool, patch_count,
            )
        else:
            origin = spawn or (width // 2, height // 2)
            wet = {(x, y) for x, y in candidates if cells[y][x].liquid}
            result = G._place_natural_gas(
                cells, seed, depth, "", origin,
                protected=protected_set | wet,
            )
            stats["gas"] = int(result.get("spent", 0))

    # 保护格恢复原状（锚点/出生点/机关不被环境内容覆盖）。
    _restore(cells, snapshot)
    return stats


def fill_long_realm_environment(state, depth, spawn, protected):
    """Fill exploration realms while preserving authored floors and puzzle lanes."""
    from collections import Counter
    from .entities import WorldItem
    from .realm_enrichment import _loot
    from ..materials.floors import FLOOR_DEFINITIONS

    realm = state.realm_id
    keep = set(protected)
    keep.update(tuple(p) for p in state.realm_features.get('protected', ()))
    keep.update(tuple(p) for p in state.realm_features.get('millennium_cabin', {}).get('main_path', ()))
    # Preserve authored surfaces independently, allowing plants on those floors.
    for y, row in enumerate(state.cells):
        for x, cell in enumerate(row):
            if cell.plant:
                keep.add((x, y))
    exclusive = tuple(k for k, d in FLOOR_DEFINITIONS.items() if realm in d.spawn_realms)
    palette = exclusive * 10 + COMMON_FLOOR_PALETTE if exclusive else (
        '木质聚合物', '金属聚合物', '反光聚合物', '柔软聚合物', '吸声聚合物', '粗糙聚合物')
    report = fill_environment(
        state.cells, seed=state.seed + depth * 1009, depth=depth,
        realm_id=realm, protected=keep, palette=palette, base_coverage=1.0,
        plant_coverage=.05, containers=False, spawn=spawn, preserve_existing_floors=True,
        liquids=realm == 'millennium_garden', gases=realm == 'millennium_garden',
    )
    if realm == 'millennium_garden':
        rng = random.Random(state.seed ^ 0x4C4F4F54 ^ depth * 3571)
        from .realm_architecture import reachable
        occupied = {(e.x, e.y) for e in [*state.enemies, *state.events, *state.world_items]}
        spots = sorted(p for p in reachable(state.cells, spawn)
                       if p not in keep and p not in occupied
                       and not state.cell(*p).wall_kind and not state.cell(*p).liquid
                       and max(abs(p[0]-spawn[0]), abs(p[1]-spawn[1])) >= 5)
        rng.shuffle(spots)
        for x, y in spots[:max(0, 7-len(state.world_items))]:
            state.world_items.append(WorldItem(state._make_item(_loot(realm, rng, state)), x, y))
    for row in state.cells:
        for cell in row:
            if cell.liquid or cell.gas:
                state._prime_material_clocks(cell)
    state._reset_material_index()
    state.realm_features['environment_report'] = report
    generation = state.realm_features.get('generation_report')
    if generation is not None:
        generation['floors'] = dict(Counter(c.aggregate_variant for row in state.cells for c in row if not c.solid))
