"""发光：照亮把「没有遮挡的方向」上的视距延长一小段（地形属性，不是征兆）。

发光地衣（materials/plants.py 的 ``PLANT_LICHEN``，``glow=True``）调用这里的
接口。规则四条：

1. 一株发光植物照亮自己所在格、以及周围 ``GLOW_RADIUS`` 格（方形，含斜角）；
2. 光照把玩家的**视距延长** ``GLOW_SIGHT_BONUS`` 格：被照亮的格子即便在视距
   半径之外，也算进入视野——远处一丛地衣于是能自己照出周围几格的地形
   （以及那里的液体/气体/生物），不必先走到跟前；
3. 延长是**有上限**的（``GLOW_SIGHT_BONUS`` 格，不是无限）：连片的地衣不会
   把视野沿着一条长廊无限推下去；
4. 光照**不能穿透遮挡**：延长走的仍是同一条带预算的布雷森汉姆射线，墙、门、
   黑烟、2 格高的高丛照样截断它。被挡住的方向上，照亮格依旧留在黑暗里。

旧写法（已废弃）是「把整片 8 向连通的照亮区域一次性拉进视野」：那会让高丛或
墙后的照亮格也跟着显形（遮挡形同虚设），并且一条地衣长廊能把视野无限蔓延。

为什么不写成征兆（portent）：征兆是挂在生物身上、按回合结算的持续状态
（见 core/portents.py），而发光纯粹是地形的属性——不随回合衰减、不参与
材料反应，所以单独成文件。将来若有别的光源（灯具、梦晶簇……）只需在
:func:`is_glowing` 里登记判定，视野规则本身不必改。
"""

from __future__ import annotations

from ...materials import plant_glows, WALL_DEFINITIONS, LIQUID_DEFINITIONS, GAS_DEFINITIONS
from ...data.light_sources import light_spec_for_cell

# 照亮半径：光源格自身 + 周围一圈（切比雪夫距离 ≤ GLOW_RADIUS）。
GLOW_RADIUS = 2
# 机械照明把视距延长多少格（docs 261022 §4.1）：普通机械光 +3，专门强光 +4；
# 多个来源照亮同一目标格时取最高、不求和。
GLOW_SIGHT_BONUS = 3
MECHANICAL_SIGHT_BONUS = GLOW_SIGHT_BONUS
STRONG_SIGHT_BONUS = 4
MAX_SIGHT_BONUS = STRONG_SIGHT_BONUS
MAX_SOURCE_RADIUS = 3


def source_radius(cell) -> int:
    if not cell.light_on:
        return 0
    radius = min(MAX_SOURCE_RADIUS, cell.light_radius)
    if is_glowing(cell.plant):
        radius = max(radius, GLOW_RADIUS)
    wall = WALL_DEFINITIONS.get(cell.wall_kind)
    if cell.solid and wall:
        radius = max(radius, wall.light_radius)
    liquid = LIQUID_DEFINITIONS.get(cell.liquid_kind)
    if liquid and cell.liquid >= liquid.light_threshold:
        radius = max(radius, liquid.light_radius)
    gas = GAS_DEFINITIONS.get(cell.gas_kind)
    if gas and cell.gas >= gas.light_threshold:
        radius = max(radius, gas.light_radius)
    return min(MAX_SOURCE_RADIUS, radius)


def is_glowing(code: int) -> bool:
    """这个植物码是不是发光植物。"""
    return plant_glows(code)


def glowing_positions(state) -> list[tuple[int, int]]:
    """全图所有发光植物所在格（调试/测试用）。"""
    return [
        (x, y)
        for y in range(state.height)
        for x in range(state.width)
        if source_radius(state.cell(x, y)) > 0
    ]


def sources_in_window(state, center: tuple[int, int], reach: int) -> list[tuple[int, int, int]]:
    """收集窗口内所有光源 (x,y,radius)；一次视野解析只扫一次（docs §11 P1）。"""
    cx, cy = center
    found: list[tuple[int, int, int]] = []
    for y in range(max(0, cy - reach), min(state.height, cy + reach + 1)):
        for x in range(max(0, cx - reach), min(state.width, cx + reach + 1)):
            radius = _radius_at(state, x, y)
            if radius:
                found.append((x, y, radius))
    return found


def any_glow(state) -> bool:
    """本层有没有任何发光植物。

    没有光源时视野集合按原半径计算即可（省掉一圈延长窗口的重算），
    因此 :meth:`SightMixin.visible_cells` 先问这一句。
    """
    # Only sources near the observer's finite sight window can extend visibility.
    reach = state.effective_sight_radius() + GLOW_SIGHT_BONUS + MAX_SOURCE_RADIUS
    px, py = state.player.x, state.player.y
    for y in range(max(0, py-reach), min(state.height, py+reach+1)):
        for x in range(max(0, px-reach), min(state.width, px+reach+1)):
            if source_radius(state.cell(x, y)) > 0:
                return True
    return False


def lit_cells(state) -> set[tuple[int, int]]:
    """全图所有被照亮的格子（含光源格自身）——调试/测试与悬停用。"""
    height, width = state.height, state.width
    lit: set[tuple[int, int]] = set()
    for y in range(height):
        for x in range(width):
            radius = source_radius(state.cell(x, y))
            if not radius:
                continue
            for ny in range(max(0, y - radius), min(height, y + radius + 1)):
                for nx in range(max(0, x - radius), min(width, x + radius + 1)):
                    if state._has_line_of_sight(x, y, nx, ny):
                        lit.add((nx, ny))
    return lit


def _radius_at(state, x: int, y: int) -> int:
    """一次视野解析内复用光源半径缓存（docs §11 P0）。"""
    cache = getattr(state, "_glow_radius_cache", None)
    if cache is None:
        return source_radius(state.cell(x, y))
    key = (x, y)
    radius = cache.get(key)
    if radius is None:
        radius = source_radius(state.cell(x, y))
        cache[key] = radius
    return radius


def sight_bonus(state, x: int, y: int) -> int:
    """照亮 ``(x, y)`` 的机械光源给出的视距延长（0 / +3 / +4）。

    只认 ``data/light_sources`` 里 ``mechanical=True`` 且真实成立的来源：
    装饰彩光（如呜咽晶柱）即便被登记为发光，也不延长视距；多个机械光源
    照同一格时取最高，不求和（docs 261022 §4.1）。视线遮挡由光源到目标格
    的同一套射线判定，墙后灯光不透墙揭示目标。
    """
    best = 0
    # 一次视野解析内复用本帧光源列表，避免每个被挡格再扫 49 格窗口。
    sources = getattr(state, "_glow_sources_cache", None)
    for cell in _lit_cells(state, x, y, sources):
        spec = light_spec_for_cell(cell)
        if spec is None:
            # 程序化投放的灯（剧情/战术布景直接写 light_radius）没有目录条目，
            # 但确实写入了机械半径，按普通机械光 +3 结算。
            best = max(best, MECHANICAL_SIGHT_BONUS)
        elif spec.mechanical:
            best = max(best, STRONG_SIGHT_BONUS if spec.strong else MECHANICAL_SIGHT_BONUS)
    return best


def _lit_cells(state, x: int, y: int, sources=None):
    """遍历照亮 ``(x, y)`` 的来源格。

    ``sources`` 可选地传入 ``sources_in_window`` 的结果；不传时按目标格周围
    一个 ``MAX_SOURCE_RADIUS`` 窗口现扫，供异象视野等热路径外调用。
    """
    if sources is None:
        sources = []
        for ny in range(max(0, y - MAX_SOURCE_RADIUS), min(state.height, y + MAX_SOURCE_RADIUS + 1)):
            for nx in range(max(0, x - MAX_SOURCE_RADIUS), min(state.width, x + MAX_SOURCE_RADIUS + 1)):
                radius = _radius_at(state, nx, ny)
                if radius:
                    sources.append((nx, ny, radius))
    for sx, sy, radius in sources:
        if max(abs(sx - x), abs(sy - y)) > radius:
            continue
        if state._has_line_of_sight(sx, sy, x, y):
            yield state.cell(sx, sy)


def sight_bonus_map(state, sources) -> dict[tuple[int, int], int]:
    """一次视野解析内的「照亮 → 视距延长」表（docs 261022 §4.1 C1）。

    规则与 :func:`sight_bonus` 逐项相同，只是把遍历方向反过来：``sight_bonus``
    对每个目标格重扫一遍来源列表，这里对每个来源铺开它照亮的格。多来源照亮
    同一格时仍取最高（+4 强光优先于 +3 普通机械光），遮挡仍是光源格到目标格
    的同一条 ``_has_line_of_sight`` 射线，因此墙/门/黑烟/高丛后面照样不会
    因光显形。

    ``sources`` 是 :func:`sources_in_window` 已取得的光源 ``(x, y, radius)``
    列表；没有光源时返回空表（调用方据此跳过整个延长窗口的重算）。非机械光源
    （纯装饰彩光）不产生延长，直接跳过，但它们仍会扩大调用方的候选窗口。
    """
    bonus_by_cell: dict[tuple[int, int], int] = {}
    if not sources:
        return bonus_by_cell
    height, width = state.height, state.width
    for sx, sy, radius in sources:
        spec = light_spec_for_cell(state.cell(sx, sy))
        if spec is None:
            # 程序化投放的灯（直接写 light_radius）没有目录条目，按普通机械光。
            bonus = MECHANICAL_SIGHT_BONUS
        elif spec.mechanical:
            bonus = STRONG_SIGHT_BONUS if spec.strong else MECHANICAL_SIGHT_BONUS
        else:
            continue
        for ny in range(max(0, sy - radius), min(height, sy + radius + 1)):
            for nx in range(max(0, sx - radius), min(width, sx + radius + 1)):
                if max(abs(sx - nx), abs(sy - ny)) > radius:
                    continue
                # 光源格自身总是被自己照亮（_has_line_of_sight 原地亦为 True）。
                if (nx, ny) != (sx, sy) and not state._has_line_of_sight(sx, sy, nx, ny):
                    continue
                if bonus > bonus_by_cell.get((nx, ny), 0):
                    bonus_by_cell[(nx, ny)] = bonus
    return bonus_by_cell


def lit(state, x: int, y: int) -> bool:
    """单格判定：这一格是否在某个发光植物的照亮范围内。

    只看周围 (2R+1)² 个格子（半径 2 时 25 格），因此可以直接在
    :meth:`SightMixin.is_visible` 的热路径上逐格调用。
    """
    sources = getattr(state, "_glow_sources_cache", None)
    if sources is not None:
        for sx, sy, radius in sources:
            if max(abs(sx - x), abs(sy - y)) <= radius and state._has_line_of_sight(sx, sy, x, y):
                return True
        return False
    for ny in range(max(0, y - MAX_SOURCE_RADIUS), min(state.height, y + MAX_SOURCE_RADIUS + 1)):
        for nx in range(max(0, x - MAX_SOURCE_RADIUS), min(state.width, x + MAX_SOURCE_RADIUS + 1)):
            radius = _radius_at(state, nx, ny)
            if radius and max(abs(nx-x), abs(ny-y)) <= radius and state._has_line_of_sight(nx, ny, x, y):
                return True
    return False


def reveals(state, x: int, y: int) -> bool:
    """这一格是否因为**机械照明**而进入视野。

    两个条件缺一不可：被已登记且真实的机械光源照亮（取 +3／+4 中最高），
    并且在「视距 + 该加值」的延长预算里视线没被遮挡（同一条带预算的射线，
    见 ``SightMixin._sight_reaches``）。被墙/门/黑烟/高丛挡住的方向因此不会
    被照亮——光照只能延伸视线，不能穿透。

    ``V=0`` 时直接返回 False：普通视距被压到 0 的异象/玩家不能靠灯光复活
    视觉（docs 261022 §4.1、§14.1）。
    """
    if state.effective_sight_radius() <= 0:
        return False
    bonus = sight_bonus(state, x, y)
    if bonus <= 0:
        return False
    return state._sight_reaches(x, y, bonus)
