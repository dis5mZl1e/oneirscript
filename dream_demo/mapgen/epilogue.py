"""深层边界（28–30 层）独立生成器。

三层都是「几何外层 + 内层草图模板」的双层结构：

- **外层**：固定几何轮廓（28 科赫雪花 / 29 边长 121 六边形 / 30 半径 70 圆），
  轮廓线与画布外圈为意识边界；轮廓内按 Perlin 阈值 value-noise 生成墙块；
  **vault（稀有 / 非常稀有）高密度盖章**（普通层 0–2 → 每层 6–10 位）。
- **内层**：剧情草图模板（关键结构与锚点固定，vault 内部随机）——
  **最后盖章**，覆盖范围内的一切既有地形（含越界 vault）被强制覆写；
  内层只保留模板规定的 vault 位（info["loot_inner"]，28 三展室各 1 /
  29 承担点旁 2 / 30 中环 2，位固定、内部地形每局随机），不追加任何
  未规定的大型随机 vault；开放区另有少量散墙微生长与液体/气体小团。
- 内外层之间由内层墙体上的缝隙口（1–2 格）连通。

所有几何与内容都由 ``seed ^ (depth * 常数)`` 确定性推导：同一种子同层恒定。
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.entities import Cell  # 仅注解用

from .vaults.base import (
    RARITY_RARE,
    RARITY_UNCOMMON,
    RARITY_VERY_RARE,
    regions_overlap,
    rotate_vault,
    stamp_vault,
    stamp_vault_near_open,
)
from .vaults.loader import load_vaults

# 结构墙（内层关键结构）、内层普通墙与外层 Perlin 墙池。
_STRUCTURE_WALL = "千层叠岩"
_INNER_WALL = "坚硬聚合墙"
_PERLIN_WALLS = ("坚硬聚合墙", "千层叠岩", "梦魇岩")

# 内层覆盖区尺寸（v1 草图比例）——**上限**：实际按几何轮廓能容纳的最大内接
# 正方形落位，模板再等比缩放（见 _inner_placement / _stamp_inner_template）。
_INNER_SIZE = {28: (110, 110), 29: (120, 120), 30: (96, 96)}

# 深层内容预算：外层 vault 位 / 液体池 / 气团 / 异象区间 / 小事件数。
EPILOGUE_BUDGET: dict[int, dict] = {
    28: {"vaults": 7, "liquids": 2, "gases": 3, "anomalies": (12, 18), "micro": 10,
         "liquid_kinds": ("静滞之泪", "稀释记忆", "泪滴溶液"),
         "gas_kinds": ("水蒸气", "黑烟", "清醒香气")},
    29: {"vaults": 9, "liquids": 4, "gases": 4, "anomalies": (18, 24), "micro": 10,
         "liquid_kinds": ("熔念金属", "噩梦纤维", "无念黑渊", "静滞之泪"),
         "gas_kinds": ("呢喃", "毒气", "噩梦气息", "电浆雾")},
    30: {"vaults": 7, "liquids": 1, "gases": 1, "anomalies": (8, 12), "micro": 8,
         "liquid_kinds": ("原初混沌",), "gas_kinds": ("无意识低语",)},
}

# 深层异象编成：强烈异象为主 + 无意识领域深层普通种。
EPILOGUE_ANOMALY_POOL = (
    "anomaly.nightmare_weaver", "anomaly.forgetter", "anomaly.blank_rift",
    "anomaly.primordial_impulse", "anomaly.thought_worm", "anomaly.faceless_watchman",
    "anomaly.silent_mirror", "anomaly.sunken_bell",
    "anomaly.dream_accountant", "anomaly.ink_archivist",
    "anomaly.whole_choir", "anomaly.null_witness",
)


# ---------------------------------------------------------------------------
# 几何基元
# ---------------------------------------------------------------------------

def _line4(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """4 连通线：对角差先走单轴，拐角处自然补格（轮廓不漏缝）。"""
    cells: list[tuple[int, int]] = []
    x, y = x0, y0
    dx, dy = x1 - x0, y1 - y0
    sx = 1 if dx > 0 else -1
    sy = 1 if dy > 0 else -1
    dx, dy = abs(dx), abs(dy)
    if dx >= dy:
        err = dx // 2
        while x != x1:
            cells.append((x, y))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
        while y != y1:
            cells.append((x, y))
            y += sy
    else:
        err = dy // 2
        while y != y1:
            cells.append((x, y))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    cells.append((x1, y1))
    return cells


def _koch_snowflake(cx: int, cy: int, radius: int, iterations: int = 4) -> list[tuple[int, int]]:
    """4 阶科赫雪花轮廓栅格（顶点朝上、包围盒居中、长宽接近的对称形）。"""
    angles = (90.0, 210.0, 330.0)
    verts = [
        (cx + radius * math.cos(math.radians(a)), cy - radius * math.sin(math.radians(a)))
        for a in angles
    ]
    poly = verts[:]
    for _ in range(iterations):
        new_poly: list[tuple[float, float]] = []
        count = len(poly)
        for index in range(count):
            x0, y0 = poly[index]
            x1, y1 = poly[(index + 1) % count]
            ax, ay = x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3
            bx, by = x0 + 2 * (x1 - x0) / 3, y0 + 2 * (y1 - y0) / 3
            mx, my = (ax + bx) / 2, (ay + by) / 2
            dxx, dyy = bx - ax, by - ay
            # 峰点两个候选，取离质心更远者（保证向外凸）。
            best: tuple[float, float] | None = None
            best_dist = -1.0
            for sign in (1.0, -1.0):
                px = mx + sign * dyy * math.sqrt(3) / 2
                py = my - sign * dxx * math.sqrt(3) / 2
                dist = math.hypot(px - cx, py - cy)
                if dist > best_dist:
                    best, best_dist = (px, py), dist
            new_poly.extend([(x0, y0), (ax, ay), best, (bx, by)])
        poly = new_poly
    outline: list[tuple[int, int]] = []
    count = len(poly)
    for index in range(count):
        x0, y0 = poly[index]
        x1, y1 = poly[(index + 1) % count]
        outline.extend(_line4(round(x0), round(y0), round(x1), round(y1)))
    return outline


def _hexagon_outline(cx: int, cy: int, side: int) -> list[tuple[int, int]]:
    """平顶六边形轮廓（顶点距 2×side，平边距 √3×side）。"""
    h = round(side * math.sqrt(3) / 2)
    verts = [
        (cx + side, cy), (cx + side // 2, cy - h), (cx - side // 2, cy - h),
        (cx - side, cy), (cx - side // 2, cy + h), (cx + side // 2, cy + h),
    ]
    outline: list[tuple[int, int]] = []
    count = len(verts)
    for index in range(count):
        x0, y0 = verts[index]
        x1, y1 = verts[(index + 1) % count]
        outline.extend(_line4(x0, y0, x1, y1))
    return outline


def _circle_ring(cx: int, cy: int, radius: int) -> set[tuple[int, int]]:
    """圆轮廓环带（厚度 2 格的意识边界）。"""
    cells: set[tuple[int, int]] = set()
    r_in, r_out = radius - 2, radius
    for y in range(cy - r_out - 1, cy + r_out + 2):
        for x in range(cx - r_out - 1, cx + r_out + 2):
            dist = math.hypot(x - cx, y - cy)
            if r_in <= dist <= r_out:
                cells.add((x, y))
    return cells


def _inner_placement(
    depth: int,
    inside: list[tuple[int, int]],
    cx: int,
    cy: int,
) -> tuple[int, int, int, int]:
    """内层覆盖区：以 (cx, cy) 为心的最大内接**矩形**，返回 (ox, oy, w, h)。

    上限是设计尺寸 `_INNER_SIZE[depth]`。算法三步：先二分出能完整容纳的
    最大**正方形**（与旧口径一致，保证下限），再把宽、高各自向设计上限
    伸展（内接矩形宽于内接正方形——实证 28 层雪花正方形 94×94，矩形可到
    110×94；29/30 层满幅 120×120 / 96×96），模板因此能按设计稿铺满内圈
    而不是缩在中心一小块。

    ⚠️ fits 只验证矩形**边界行列**在可玩区内：几何湾谷（如 28 层雪花底边的
    科赫湾谷）穿过矩形内部时，盖章端（_stamp_inner_template）与内层 vault
    写回对意识边界格只跳过、不覆写，轮廓不会被凿穿；模板锚点若恰好落进
    湾谷，由收尾的锚点修正就近挪离（test_geometry_outline_is_never_punctured
    与 test_inner_template_stays_inside_the_playable_area 守）。
    """
    limit_w, limit_h = _INNER_SIZE[depth]
    playable = set(inside)
    if not playable:
        return cx, cy, 0, 0

    def fits(half_w: int, half_h: int) -> bool:
        if half_w <= 0 or half_h <= 0:
            return True
        for dx in range(-half_w, half_w + 1):
            if (cx + dx, cy - half_h) not in playable or (cx + dx, cy + half_h) not in playable:
                return False
        for dy in range(-half_h, half_h + 1):
            if (cx - half_w, cy + dy) not in playable or (cx + half_w, cy + dy) not in playable:
                return False
        return True

    def bisect(start: int, cap: int, other: int, grow_w: bool) -> int:
        """在 half_other 固定时，二分 half_this 的最大值。"""
        lo, hi = start, cap
        while lo < hi:
            mid = (lo + hi + 1) // 2
            ok = fits(mid, other) if grow_w else fits(other, mid)
            if ok:
                lo = mid
            else:
                hi = mid - 1
        return lo

    # 第一步必须用完整的 fits(mid, mid) 双轴验证：若走 fits(0, mid)，
    # half_w=0 会把验证退化成「只查中列 + 顶底中点」，湾谷断面全部放行，
    # square 被高估后后续两步 lo=hi 直接返回、整个矩形零验证落位。
    square_cap = min(limit_w, limit_h) // 2
    lo, hi = 0, square_cap
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid, mid):
            lo = mid
        else:
            hi = mid - 1
    square = lo
    half_w = bisect(square, limit_w // 2, square, grow_w=True)
    half_h = bisect(square, limit_h // 2, half_w, grow_w=False)
    return cx - half_w, cy - half_h, half_w * 2, half_h * 2


def _value_noise(rng: random.Random, width: int, height: int, spacing: int = 10):
    """两倍频 value-noise：返回 (x, y) → 0..1 的确定性噪声函数。"""

    def make_grid(step: int) -> list[list[float]]:
        gw, gh = width // step + 2, height // step + 2
        return [[rng.random() for _ in range(gw)] for _ in range(gh)]

    coarse = make_grid(spacing)
    fine = make_grid(max(3, spacing // 2))

    def sample(grid: list[list[float]], x: float, y: float) -> float:
        x0, y0 = int(x), int(y)
        fx, fy = x - x0, y - y0
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        top = grid[y0][x0] * (1 - fx) + grid[y0][x0 + 1] * fx
        bottom = grid[y0 + 1][x0] * (1 - fx) + grid[y0 + 1][x0 + 1] * fx
        return top * (1 - fy) + bottom * fy

    def noise(x: int, y: int) -> float:
        return 0.7 * sample(coarse, x / spacing, y / spacing) + 0.3 * sample(
            fine, x / (spacing / 2), y / (spacing / 2)
        )

    return noise


# ---------------------------------------------------------------------------
# 生成入口
# ---------------------------------------------------------------------------

def _is_circuit_vault(vault) -> bool:
    """28–30 层规定不出现电路（2026-09-22）：图案含电线位（w）、压力地板位
    （p）或任一逻辑固体字符的模板视为电路 vault——含门类节点与放大器
    导电铜网墙。按图案内容判定而非 id 清单，后续新增电路模板自动覆盖。
    """
    from ..materials.logic import TEMPLATE_ONLY_CIRCUIT_WALLS, TRAP_PLATFORM
    from .vaults.base import PRESSURE_CHAR, VAULT_CHAR_KINDS, WIRE_CHAR

    forbidden = {
        ch for ch, kind in VAULT_CHAR_KINDS.items()
        if kind in TEMPLATE_ONLY_CIRCUIT_WALLS or kind == TRAP_PLATFORM
    } | {WIRE_CHAR, PRESSURE_CHAR}
    return any(set(row) & forbidden for row in vault.pattern)


def generate_epilogue_layer(depth: int, seed: int) -> tuple[list[list[object]], dict]:
    """生成一张深层边界地图，返回 (cells, info)。

    info：出生点、剧情事件锚点、NPC 位、异象投放清单、vault 战利品位。
    """
    from ..core.entities import Cell

    spec = EPILOGUE_BUDGET[depth]
    rng = random.Random(seed ^ (depth * 0xE91C1))
    if depth == 28:
        width, height = 210, 210
    elif depth == 29:
        width, height = 246, 214
    else:
        width, height = 144, 144

    # ---- 底板：全开放；几何轮廓线 + 轮廓外 + 画布外圈 = 意识边界 ----
    # 旧实现先把整张画布铺成意识边界再「挖空」，洪填起点 (1,1) 本身就在边界里，
    # 一格都扩不出去 → 「轮廓外」恒为空集 → 三层都退化成整片空地，几何形状消失。
    cells: list[list[Cell]] = [[Cell() for _ in range(width)] for _ in range(height)]
    if depth == 28:
        # 雪花包围盒是 2R=194 高（顶点与底边凸尖都在半径 R 上），必须按画布中心
        # 摆放；用三角形包围盒（1.5R）的居中系数 0.61 会把底部 15 行挤出画布，
        # 轮廓线被截断 → 洪填从缺口灌进内部，整层退化成空地。
        outline = set(_koch_snowflake(width // 2, height // 2, 97))
    elif depth == 29:
        outline = set(_hexagon_outline(width // 2, height // 2, 121))
    else:
        outline = _circle_ring(width // 2, height // 2, 70)

    # 意识边界集合：几何轮廓线 ∪ 画布最外一圈。一律走 configure_wall，
    # 否则这些格只挂了 wall_kind、数值仍是 Cell 默认（硬 2 / 高 0 / 厚 1 / 完 100）。
    boundary: set[tuple[int, int]] = set()
    for x, y in outline:
        if 0 <= x < width and 0 <= y < height:
            boundary.add((x, y))
    for x in range(width):
        boundary.add((x, 0))
        boundary.add((x, height - 1))
    for y in range(height):
        boundary.add((0, y))
        boundary.add((width - 1, y))
    for x, y in boundary:
        _configure(cells[y][x], "意识边界")

    # 从画布外圈内侧起洪填「轮廓外」区域（只走非边界格），全部填成意识边界。
    outside: set[tuple[int, int]] = set()
    queue: list[tuple[int, int]] = []

    def _seed(sx: int, sy: int) -> None:
        if (sx, sy) not in boundary and (sx, sy) not in outside:
            outside.add((sx, sy))
            queue.append((sx, sy))

    for x in range(1, width - 1):
        _seed(x, 1)
        _seed(x, height - 2)
    for y in range(1, height - 1):
        _seed(1, y)
        _seed(width - 2, y)
    while queue:
        x, y = queue.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (
                0 <= nx < width
                and 0 <= ny < height
                and (nx, ny) not in outside
                and (nx, ny) not in boundary
            ):
                outside.add((nx, ny))
                queue.append((nx, ny))
    for x, y in outside:
        _configure(cells[y][x], "意识边界")

    # 轮廓内 = 既非边界也非轮廓外的格 → 可玩区（先清空，再按 Perlin 撒墙）。
    inside: list[tuple[int, int]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if (x, y) not in outside and (x, y) not in boundary:
                cells[y][x] = Cell()
                inside.append((x, y))

    # ---- 外层 Perlin 阈值墙块 ----
    noise = _value_noise(rng, width, height)
    for x, y in inside:
        if noise(x, y) > 0.62:
            kind = _PERLIN_WALLS[rng.randrange(len(_PERLIN_WALLS))]
            _configure(cells[y][x], kind)

    # ---- 内层草图模板（最后盖章，覆盖一切既有地形含 vault 位）----
    # 覆盖区取「以画布中心为心、几何轮廓能完整容纳的最大内接矩形」，上限为设计尺寸。
    inner_x, inner_y, inner_w, inner_h = _inner_placement(depth, inside, width // 2, height // 2)
    info = _stamp_inner_template(cells, depth, inner_x, inner_y, inner_w, inner_h, rng)

    # ---- 外层 vault（稀有 / 非常稀有 高产，避开内层覆盖区）----
    mask = [[cells[y][x].solid for x in range(width)] for y in range(height)]
    info["scene_events"], info["structure_npcs"] = [], []
    loot_spots: list[tuple[int, int]] = []
    vault_kinds: dict[tuple[int, int], str] = {}
    vault_liquids: dict[tuple[int, int], str] = {}

    # ---- 内层固定 vault 位盖章（deep-boundary-plan §2.4）----
    # 位矩形由模板登记在 info["loot_inner"]（实际坐标含端点）。候选从非电路池里
    # 挑能放进位矩形的模板：loot 优先、面积大优先，取向与落位随机——位固定、
    # 内部地形每局随机。清空区开放比例恒为 100%，后置模板的地形门槛必满足。
    inner_pool = [
        vault for vault in load_vaults().values()
        if vault.rarity in (RARITY_UNCOMMON, RARITY_RARE, RARITY_VERY_RARE)
        and vault.available_at(depth)
        and not _is_circuit_vault(vault)
        and min(vault.width, vault.height) >= 3
    ]
    # 内层 vault 周边 1 格禁布液体/气体/散墙（保护罩语义）。
    inner_protected: list[tuple[int, int, int, int]] = []
    # 科赫湾谷会在覆盖区里留下被意识边界围死的封闭口袋：从这里开始先算一次
    # spawn 可达集，内层 vault 落位与收尾锚点修正都以此为准。
    from .epilogue_paths import reachable

    connected = reachable(cells, info["spawn"])
    zone_has_loot: list[bool] = []
    for pl, pt, pr, pb in info["loot_inner"]:
        zone_w, zone_h = pr - pl + 1, pb - pt + 1
        def fits_zone(vault) -> bool:
            # Template eligibility must use the same rotation-aware geometry as
            # the placement loop below. Filtering by the source orientation here
            # silently drops tall buildings that fit after a quarter turn.
            return any(
                (vault.height if turn % 2 else vault.width) <= zone_w
                and (vault.width if turn % 2 else vault.height) <= zone_h
                for turn in range(4)
            )

        # 「遗物库」级别的 loot 模板（≥40 格）优先；3x3 级小龛（如街边神龛）
        # 与非 loot 构造同场竞争，避免小位矩形被 3x3 龛垄断成一片空地。
        loot_first = [v for v in inner_pool if v.loot and v.width * v.height >= 40
                      and fits_zone(v)]
        others = [v for v in inner_pool
                  if (not v.loot or v.width * v.height < 40)
                  and fits_zone(v)]
        rng.shuffle(loot_first)
        rng.shuffle(others)

        def _jittered(seq: list) -> None:
            """面积降序但带随机抖动：大件优先不垄断，面积相近的候选随机洗牌。"""
            bias = {id(v): v.width * v.height + rng.randrange(0, 260) for v in seq}
            seq.sort(key=lambda v: -bias[id(v)])

        _jittered(loot_first)
        _jittered(others)
        placement = None
        for vault in loot_first + others:
            # 只在放得下的旋转朝向里挑（窄长模板只有部分朝向 fits），而不是
            # 因为一个朝向放不下就淘汰整个候选。
            fits_turns = [
                turn for turn in range(4)
                if (vault.height if turn % 2 else vault.width) <= zone_w
                and (vault.width if turn % 2 else vault.height) <= zone_h
            ]
            if not fits_turns:
                continue
            oriented = rotate_vault(vault, fits_turns[rng.randrange(len(fits_turns))])
            left = pl + rng.randrange(zone_w - oriented.width + 1)
            top = pt + rng.randrange(zone_h - oriented.height + 1)
            # 落位区内的开放格必须全部可达，否则 loot/事件锚点会被困死在口袋里
            #（connect_anchors 不凿意识边界，困死即生成失败）。
            if not all(
                (left + col, top + row) in connected
                for row in range(oriented.height)
                for col in range(oriented.width)
                if not mask[top + row][left + col]
            ):
                continue
            placement = stamp_vault(mask, oriented, left, top, rng)
            if placement is not None:
                break
        if placement is None:
            zone_has_loot.append(False)
            continue
        reg_left, reg_top, reg_right, reg_bottom = placement.region
        inner_protected.append((reg_left - 1, reg_top - 1, reg_right + 1, reg_bottom + 1))
        kinds = placement.kind_overrides()
        for row, line in enumerate(placement.vault.pattern):
            for col, ch in enumerate(line):
                x, y = placement.left + col, placement.top + row
                if cells[y][x].wall_kind == "意识边界":
                    continue  # fjord 谷底可能伸进位矩形：绝不覆写轮廓格
                if ch in ".@pw~":
                    cells[y][x] = Cell()
                elif ch != " ":
                    _configure(cells[y][x], kinds.get((x, y), _INNER_WALL))
        vault = placement.vault
        if vault.event:
            row, col = vault.event_anchor or (vault.height // 2, vault.width // 2)
            info["scene_events"].append(
                {"event_id": vault.event, "x": placement.left + col, "y": placement.top + row}
            )
        if vault.npc_id and vault.npc_anchor:
            row, col = vault.npc_anchor
            info["structure_npcs"].append(((placement.left + col, placement.top + row), vault.npc_id))
        loot = placement.loot_cell
        if loot:
            loot_spots.append(loot)
        zone_has_loot.append(loot is not None)

    # 构造类模板没有 loot 台（圣所/迷宫/几何图案）：凡是无 loot 的位，在位内
    # 剩余开放空间补一座街边神龛兜底「遗物」语义（deep-boundary-plan §2.4）。
    altar = load_vaults().get("street_altar")
    if altar is not None:
        connected = reachable(cells, info["spawn"])  # 内层 vault 落墙后重算可达集
        for (pl, pt, pr, pb), has_loot in zip(info["loot_inner"], zone_has_loot):
            if has_loot:
                continue
            zone_w, zone_h = pr - pl + 1, pb - pt + 1
            for _ in range(12):
                left = pl + rng.randrange(zone_w - 2)
                top = pt + rng.randrange(zone_h - 2)
                if regions_overlap(left, top, altar.width, altar.height, inner_protected):
                    continue
                if not all(
                    (left + col, top + row) in connected
                    for row in range(altar.height) for col in range(altar.width)
                    if not mask[top + row][left + col]
                ):
                    continue
                sub = stamp_vault(mask, altar, left, top, rng)
                if sub is None:
                    continue
                sl, st, sr, sb = sub.region
                inner_protected.append((sl - 1, st - 1, sr + 1, sb + 1))
                sub_kinds = sub.kind_overrides()
                for row, line in enumerate(altar.pattern):
                    for col, ch in enumerate(line):
                        x, y = left + col, top + row
                        if cells[y][x].wall_kind == "意识边界":
                            continue
                        if ch in ".@pw~":
                            cells[y][x] = Cell()
                        elif ch != " ":
                            _configure(cells[y][x], sub_kinds.get((x, y), _INNER_WALL))
                loot = sub.loot_cell
                if loot:
                    loot_spots.append(loot)
                break

    # ---- 内层散墙微生长：覆盖区开放格撒少量小墙簇（deep-boundary-plan §2.4）----
    # 只落在无墙种的开放格，避开锚点（切比雪夫 ≤2）与内层 vault 保护罩；
    # 即便挡路，收尾 connect_anchors 还会自动凿通。
    inner_anchors = {info["spawn"], *info["events"].values(), *info.get("accept", ())}
    inner_anchors.update((x, y) for x, y, _ in info["enemies"])
    if info["npc"]:
        inner_anchors.add(info["npc"])
    inner_anchors.update((entry["x"], entry["y"]) for entry in info["scene_events"])
    inner_anchors.update(pos for pos, _ in info["structure_npcs"])
    inner_anchors.update(loot_spots)

    def _in_inner_protected(x: int, y: int) -> bool:
        return any(pl <= x <= pr and pt <= y <= pb for pl, pt, pr, pb in inner_protected)

    def _near_anchor(x: int, y: int, margin: int = 2) -> bool:
        return any(abs(x - ax) <= margin and abs(y - ay) <= margin for ax, ay in inner_anchors)

    inner_seeds = [
        (x, y)
        for y in range(inner_y, inner_y + inner_h)
        for x in range(inner_x, inner_x + inner_w)
        if not cells[y][x].solid and not cells[y][x].wall_kind
        and not _in_inner_protected(x, y) and not _near_anchor(x, y)
    ]
    rng.shuffle(inner_seeds)
    for _ in range(max(3, inner_w * inner_h // 700)):
        if not inner_seeds:
            break
        sx, sy = inner_seeds.pop()
        if cells[sy][sx].solid or cells[sy][sx].wall_kind:
            continue
        blob = [(sx, sy)]
        seen = {(sx, sy)}
        frontier = [(sx, sy)]
        target = rng.randint(3, 8)
        while frontier and len(blob) < target:
            bx, by = frontier.pop(rng.randrange(len(frontier)))
            for nx, ny in ((bx + 1, by), (bx - 1, by), (bx, by + 1), (bx, by - 1)):
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                if not (inner_x <= nx < inner_x + inner_w and inner_y <= ny < inner_y + inner_h):
                    continue
                cell = cells[ny][nx]
                if cell.solid or cell.wall_kind or _in_inner_protected(nx, ny) or _near_anchor(nx, ny):
                    continue
                blob.append((nx, ny))
                frontier.append((nx, ny))
        for x, y in blob:
            _configure(cells[y][x], _INNER_WALL)
            mask[y][x] = True

    avoid = [(inner_x - 2, inner_y - 2, inner_x + inner_w + 1, inner_y + inner_h + 1)]
    rare_pool = [
        vault for vault in load_vaults().values()
        if vault.rarity in (RARITY_RARE, RARITY_VERY_RARE)
        and vault.available_at(depth)
        and not _is_circuit_vault(vault)  # 28–30 无电路（2026-09-22）
    ]
    stamped = 0
    for _ in range(spec["vaults"] * 3):
        if stamped >= spec["vaults"] or not rare_pool:
            break
        before = [row[:] for row in mask]
        placement = stamp_vault_near_open(
            mask, rare_pool[rng.randrange(len(rare_pool))], rng, attempts=12, avoid=avoid,
        )
        if placement is None:
            continue
        left, top, right, bottom = placement.region
        if any((x,y) in boundary or (x,y) in outside
               for y in range(top,bottom+1) for x in range(left,right+1)):
            mask = before
            continue
        stamped += 1
        avoid.append(placement.region)
        kinds = placement.kind_overrides()
        for row, line in enumerate(placement.vault.pattern):
            for col, ch in enumerate(line):
                x, y = placement.left+col, placement.top+row
                if ch in ".@pw~":
                    cells[y][x] = Cell()
                elif ch != " ":
                    _configure(cells[y][x], kinds.get((x,y), _INNER_WALL))
        vault = placement.vault
        if vault.event:
            row,col = vault.event_anchor or (vault.height//2,vault.width//2)
            info["scene_events"].append({"event_id":vault.event,"x":left+col,"y":top+row})
        if vault.npc_id and vault.npc_anchor:
            row,col = vault.npc_anchor
            info["structure_npcs"].append(((left+col,top+row),vault.npc_id))
        vault_kinds.update(placement.kind_overrides())
        vault_liquids.update(placement.liquid_overrides())
        loot = placement.loot_cell
        if loot:
            loot_spots.append(loot)
    for (x, y), kind in vault_kinds.items():
        _configure(cells[y][x], kind)
    for (x, y), kind in vault_liquids.items():
        cells[y][x].liquid, cells[y][x].liquid_kind = min(100, 40), kind
        cells[y][x].solid = False

    # 意识边界神圣不可覆写：vault 越界盖章会把轮廓格改成普通墙种，液体池还会把
    # 它挖成可通行的洞——收尾按轮廓集合（轮廓线 ∪ 轮廓外）整体复位。
    sealed = boundary | outside
    for x, y in sealed:
        if cells[y][x].wall_kind != "意识边界":
            _configure(cells[y][x], "意识边界")
    info["loot_spots"] = [spot for spot in loot_spots if spot not in sealed]
    info["inner"] = (inner_x, inner_y, inner_w, inner_h)

    # ---- 模板锚点脱离意识边界 ----
    # 覆盖区的边界行列已验证可玩，但内接矩形放宽后，几何凹陷（如 28 层雪花
    # 底边的科赫湾谷）仍会穿入矩形内部——模板锚点可能恰好落在意识边界格上。
    # 就近挪到从 spawn 可达的开放格；实在没有再挪到最近非边界格（connect_anchors
    # 会凿路接通）。锚点数 ≤ 十几个、修正通常 0~1 个，全量螺旋扫描开销可忽略。
    connected = reachable(cells, info["spawn"])

    def _off_boundary(x: int, y: int) -> tuple[int, int]:
        if cells[y][x].wall_kind != "意识边界":
            return x, y
        for want_connected in (True, False):
            for radius in range(1, 12):
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if max(abs(dx), abs(dy)) != radius:
                            continue
                        nx, ny = x + dx, y + dy
                        if not (0 < nx < width - 1 and 0 < ny < height - 1):
                            continue
                        if cells[ny][nx].wall_kind == "意识边界":
                            continue
                        if want_connected and (nx, ny) not in connected:
                            continue
                        return nx, ny
        return x, y

    info["spawn"] = _off_boundary(*info["spawn"])
    info["events"] = {key: _off_boundary(x, y) for key, (x, y) in info["events"].items()}
    info["accept"] = [_off_boundary(x, y) for x, y in info["accept"]]
    if info["npc"]:
        info["npc"] = _off_boundary(*info["npc"])
    info["enemies"] = [(*_off_boundary(x, y), kind) for x, y, kind in info["enemies"]]

    # ---- 外层内容：液体 / 气体小团 ----
    # 内层开放区也参与（deep-boundary-plan §2.4：内层也要液体/气体小团），
    # 只避开内层 vault 周边 1 格保护罩。
    open_cells = [
        (x, y)
        for y in range(2, height - 2)
        for x in range(2, width - 2)
        if not cells[y][x].solid
        and not _in_inner_protected(x, y)
    ]
    rng.shuffle(open_cells)

    def patch(kind: str, is_liquid: bool) -> None:
        if not open_cells:
            return
        sx, sy = open_cells[rng.randrange(len(open_cells))]
        frontier = [(sx, sy)]
        seen = {(sx, sy)}
        size = rng.randint(8, 20)
        placed = 0
        while frontier and placed < size:
            cx, cy = frontier.pop(rng.randrange(len(frontier)))
            cell = cells[cy][cx]
            if _in_inner_protected(cx, cy):
                continue
            if cell.solid or cell.wall_kind:
                continue
            if is_liquid:
                cell.liquid, cell.liquid_kind = rng.randint(40, 90), kind
            else:
                cell.gas, cell.gas_kind = rng.randint(40, 90), kind
            placed += 1
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 < nx < width - 1 and 0 < ny < height - 1 and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    frontier.append((nx, ny))

    for _ in range(spec["liquids"]):
        patch(spec["liquid_kinds"][rng.randrange(len(spec["liquid_kinds"]))], True)
    for _ in range(spec["gases"]):
        patch(spec["gas_kinds"][rng.randrange(len(spec["gas_kinds"]))], False)

    info["width"], info["height"] = width, height
    from .epilogue_paths import connect_anchors
    connected = connect_anchors(cells, info)
    info["open_cells"] = [p for p in open_cells if p in connected]
    return cells, info


# ---------------------------------------------------------------------------
# 内层模板（关键结构固定；最后盖章，覆盖一切）
# ---------------------------------------------------------------------------

def _stamp_inner_template(
    cells: list[list[Cell]],
    depth: int,
    ox: int,
    oy: int,
    w: int,
    h: int,
    rng: random.Random,
) -> dict:
    """把内层草图模板盖在画布上，返回 info（锚点/NPC/异象清单）。

    模板用**参考坐标系**（`_INNER_SIZE[depth]` 见方）书写，再按实际覆盖区尺寸等比
    缩放落格——几何轮廓能容纳多大的内接正方形，模板就自动缩到多大，不会因为尺寸
    不符而把意识边界轮廓凿穿。

    覆盖区先整体清空——剧情模板优先级最高，强制覆写一切既有地形。
    """
    from ..core.entities import Cell

    ref_w, ref_h = _INNER_SIZE[depth]
    kx, ky = w / ref_w, h / ref_h

    def X(rx: int) -> int:
        return ox + int(round(rx * kx))

    def Y(ry: int) -> int:
        return oy + int(round(ry * ky))

    info: dict = {"events": {}, "npc": None, "enemies": [], "accept": [], "loot_inner": []}
    # 缝隙口 / 门位集中到最后再挖：缩放后相邻参考格可能落到同一实际格，
    # 边画边挖会被后一笔墙重新填上。
    openings: set[tuple[int, int]] = set()

    # 覆盖区矩形的边界行列已由 _inner_placement 验证全在可玩区内（轮廓不可能
    # 与矩形相交），内部正常也不会有意识边界格；但内接矩形放宽后仍把「碰到
    # 意识边界只跳过」作为防御性保险丝——宁可模板缺一笔，绝不凿穿轮廓。
    def clear(x: int, y: int) -> None:
        if cells[y][x].wall_kind != "意识边界":
            cells[y][x] = Cell()

    def wall(x: int, y: int, kind: str = _STRUCTURE_WALL) -> None:
        if cells[y][x].wall_kind != "意识边界":
            _configure(cells[y][x], kind)

    def hline(rx0: int, rx1: int, ry: int, gaps: tuple[int, ...] = ()) -> None:
        for rx in range(min(rx0, rx1), max(rx0, rx1) + 1):
            if rx in gaps:
                openings.add((X(rx), Y(ry)))
            else:
                wall(X(rx), Y(ry))

    def vline(ry0: int, ry1: int, rx: int, gaps: tuple[int, ...] = ()) -> None:
        for ry in range(min(ry0, ry1), max(ry0, ry1) + 1):
            if ry in gaps:
                openings.add((X(rx), Y(ry)))
            else:
                wall(X(rx), Y(ry))

    # 覆盖区整体清空（剧情模板优先级最高）
    for y in range(oy, oy + h):
        for x in range(ox, ox + w):
            clear(x, y)
    cx = ref_w // 2
    top, bottom = 3, ref_h - 4
    left, right = 4, ref_w - 5

    if depth == 28:
        # 辨认之馆：北侧三展室（各带南门）+ 南侧中央大厅（归档门）
        room_w, room_h = 30, 32
        starts = [left + 2, left + 2 + room_w + 6, left + 2 + 2 * (room_w + 6)]
        for index, sx in enumerate(starts):
            vline(top, top + room_h, sx)
            vline(top, top + room_h, sx + room_w)
            hline(sx, sx + room_w, top)
            hline(sx, sx + room_w, top + room_h, gaps=(sx + room_w // 2,))
            info["events"][f"room{index}"] = (X(sx + room_w // 2), Y(top + room_h // 2))
            # 内层 vault 位（deep-boundary-plan §2.4：三展室各 1 个遗物 vault，
            # 内部地形每局随机）——房间内部缩进 1 格的矩形（实际坐标含端点）。
            info["loot_inner"].append(
                (X(sx + 1), Y(top + 1), X(sx + room_w - 1), Y(top + room_h - 1))
            )
        hall_top = top + room_h + 6
        hline(left, right, hall_top, gaps=(cx - 1, cx, cx + 1))
        info["events"]["gate"] = (X(cx), Y(hall_top + 3))
        info["npc"] = (X(left + 6), Y(bottom - 2))
        info["spawn"] = (X(cx), Y(bottom - 2))
        # 内层南墙缝隙口（外层 → 内层入口）
        hline(0, ref_w - 1, ref_h - 1, gaps=(cx - 4, cx, cx + 4))
    elif depth == 29:
        # 承担之野：南入口 → 三条蜿蜒路径（承担点在弯折处）→ 前庭牵引碑 → 审判庭
        vline(top, bottom, left)
        vline(top, bottom, right)
        hline(left, right, bottom, gaps=(cx - 3, cx, cx + 3))
        hline(left, right, top, gaps=(cx,))
        path_tops = []
        for offset, bends in ((-34, (18, 10)), (0, (12, 26)), (34, (20, 8))):
            x, y = cx + offset, bottom - 4
            prev_y = bottom - 4
            for bend in bends:
                y -= bend
                hline(max(left + 2, x - 14), min(right - 2, x + 14), y)
                # 竖直连接段：原实现写成 vline(y, y, x)（等价于只画 1 格），
                # 三道横阶互不相连，「蜿蜒路径」名存实亡。
                vline(prev_y, y, x)
                prev_y = y
                x = min(max(x + (8 if offset <= 0 else -8), left + 6), right - 6)
            path_tops.append((x, y))
        for ax, ay in path_tops:
            info["accept"].append((X(ax), Y(ay + 1)))
        # 内层 vault 位（deep-boundary-plan §2.4：承担点旁 2 个）——取前两条
        # 路径顶点上方的空旷矩形，避开审判庭（rows ≤45）与蜿蜒路径横线（y ≥ 74）。
        info["loot_inner"].append((X(20), Y(48), X(44), Y(76)))
        info["loot_inner"].append((X(66), Y(44), X(94), Y(72)))
        info["events"]["stele"] = (X(cx), Y(top + 6))
        # 审判庭（西北角内庭，西墙与南墙各开一门保证可达）
        c0, c1, cs = cx - 30, top + 8, 34
        vline(c1, c1 + cs, c0, gaps=(c1 + cs // 2,))
        vline(c1, c1 + cs, c0 + cs)
        hline(c0, c0 + cs, c1)
        hline(c0, c0 + cs, c1 + cs, gaps=(c0 + cs // 2,))
        info["events"]["gate"] = (X(c0 + cs // 2), Y(c1 + cs // 2))
        info["npc"] = (X(left + 8), Y(bottom - 2))
        info["spawn"] = (X(cx), Y(bottom - 2))
        hline(0, ref_w - 1, ref_h - 1, gaps=(cx - 3, cx, cx + 3))
    else:
        # 改写之台：外环走廊 → 中环记忆回廊（四缺口）→ 内坛（执笔者+终局桌）
        vline(top, bottom, left)
        vline(top, bottom, right)
        hline(left, right, bottom, gaps=(cx - 1, cx, cx + 1))
        hline(left, right, top)
        mid_top, mid_bottom = 16, bottom - 12
        mid_left, mid_right = 16, right - 11
        hline(mid_left, mid_right, mid_top, gaps=(cx - 2, cx + 2))
        hline(mid_left, mid_right, mid_bottom, gaps=(cx,))
        vline(mid_top, mid_bottom, mid_left, gaps=(mid_top + 8,))
        vline(mid_top, mid_bottom, mid_right, gaps=(mid_top + 16,))
        info["events"]["gallery"] = (X(mid_left + 8), Y(mid_top + 8))
        info["events"]["fragment0"] = (X(mid_right - 5), Y(mid_top + 8))
        info["events"]["fragment1"] = (X(mid_left + 7), Y(mid_bottom - 6))
        info["events"]["fragment2"] = (X(mid_right - 6), Y(mid_bottom - 5))
        # 内层 vault 位（deep-boundary-plan §2.4：中环 2 个）。左右侧廊加宽，
        # 让大型遗物建筑也能落位；纵向避开上方 gallery 和底部 fragment 锚点。
        info["loot_inner"].append((X(17), Y(37), X(37), Y(68)))
        info["loot_inner"].append((X(59), Y(37), X(79), Y(68)))
        # 内坛
        ch_left, ch_right = cx - 10, cx + 10
        ch_top, ch_bottom = mid_top + 14, mid_bottom - 6
        vline(ch_top, ch_bottom, ch_left, gaps=(ch_top + 5,))
        vline(ch_top, ch_bottom, ch_right)
        hline(ch_left, ch_right, ch_top, gaps=(cx,))
        info["enemies"].append((X(cx), Y(ch_top + 8), "anomaly.scribe"))
        info["events"]["desk"] = (X(cx), Y(ch_bottom - 3))
        info["spawn"] = (X(cx), Y(bottom - 2))
        hline(0, ref_w - 1, ref_h - 1, gaps=(cx - 2, cx, cx + 2))

    for x, y in openings:
        if ox <= x < ox + w and oy <= y < oy + h:
            clear(x, y)
    return info


def _configure(cell, kind: str) -> None:
    """配置一格为指定墙种（GenerationMixin.configure_wall 的薄封装）。"""
    from ..core.generation import GenerationMixin

    GenerationMixin.configure_wall(cell, kind)
