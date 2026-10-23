"""§22 C：最大余量声路（有界最小损耗传播）。

一个声源只结算一张权威声场：每格保留 ``Q − Cmin``（接收余量），
路径成本只取最优的一条，不把多条路线相加。开放边默认耗 2；普通固体
按实际厚度 ``2 + 2t`` 计费（可穿声），沉思铁幕禁止穿声；回声雾把有限
传播边降到 1，液化的回声在两端都 ≥8 单位的连通液面上同样降到 1，死寂气团每格 +4。

本模块只读地图与墙体定义，不改世界、不消耗随机数；权威结算与预览共用。
"""

from __future__ import annotations

import heapq

from ..materials import wall_def

OPEN_COST = 2
THICKNESS_COST = 2
ABSORBING_WALL_EXTRA = 4
DEAD_AIR_EXTRA = 4
ECHO_FOG_COST = 1
IRON_CURTAIN = "沉思铁幕"
ABSORBING_WALL = "吸声聚合墙"
ECHO_FOG = "回声雾"
DEAD_AIR = "死寂气团"
ECHO_FOG_THRESHOLD = 20
# 液化的回声：沿连通液面传声，两端都要有至少 8 单位这一液体（docs §15.4）。
ECHO_LIQUID = "液化的回声"
ECHO_LIQUID_AMOUNT = 8
ECHO_LIQUID_COST = 1
# 最灵敏接收阈值（T=−3）再留 1 单位余量；传播只保留到这条下界，
# 不能因 H 或默认 T=0 截掉更灵敏听者仍能接收的弱声。
MIN_RESIDUAL = -4
# 「最后一圈安静」：穿过静音圈边界的声在既有损耗外**再多**衰减这么多，
# 且每个接收格最多只算一次（来回穿越也只扣一次）。
QUIET_EXTRA_LOSS = 6


def source_strength(radius: int) -> int:
    """显示声径 R → 声强预算 Q（正常源 Q = 2R）。无声返回 0。"""
    return max(0, int(radius)) * 2


def _cell_cost(cell) -> int | None:
    """进入该格的成本；``None`` 表示禁止穿声。"""
    if cell.solid:
        kind = str(getattr(cell, "wall_kind", "") or "")
        if kind == IRON_CURTAIN:
            return None
        height = int(getattr(cell, "height", 0) or 0)
        # 矮台、低障碍可从上越过，只收开放成本；普通全高墙按厚度计费。
        if height <= 1 and kind != "门":
            return OPEN_COST
        thickness = int(getattr(cell, "thickness", 0) or 0)
        if thickness <= 0:
            definition = wall_def(kind) if kind else None
            thickness = int(definition.thickness) if definition is not None else 1
        cost = OPEN_COST + THICKNESS_COST * max(1, thickness)
        if kind == ABSORBING_WALL:
            cost += ABSORBING_WALL_EXTRA
        return cost
    return OPEN_COST


def _edge_cost(current, neighbor) -> int | None:
    """从 current 迈入 neighbor 的声音成本；封闭特例返回 ``None``。"""
    cost = _cell_cost(neighbor)
    if cost is None:
        return None
    # 回声雾：处于雾中的传播边（任一端）2→1，只延长有限声路。
    if (getattr(current, "gas_kind", "") == ECHO_FOG
            and int(getattr(current, "gas", 0) or 0) >= ECHO_FOG_THRESHOLD
            or getattr(neighbor, "gas_kind", "") == ECHO_FOG
            and int(getattr(neighbor, "gas", 0) or 0) >= ECHO_FOG_THRESHOLD):
        cost = min(cost, ECHO_FOG_COST) if not neighbor.solid else cost
    if (getattr(neighbor, "gas_kind", "") == DEAD_AIR
            and int(getattr(neighbor, "gas", 0) or 0) > 0 and not neighbor.solid):
        cost += DEAD_AIR_EXTRA
    # 液化的回声：两端都够深（≥8）的连通液面把这一条边 2→1。
    # 与「站上液面把自身声径 ×2」是两件事：主体放大走征兆，这里只是介质传声。
    if (not current.solid and not neighbor.solid
            and _echo_liquid(current) and _echo_liquid(neighbor)):
        cost = min(cost, ECHO_LIQUID_COST)
    return max(1, cost)


def _echo_liquid(cell) -> bool:
    """这一格是否是够深的液化回声液面（两端都要满足才算连通传声）。"""
    return (getattr(cell, "liquid_kind", "") == ECHO_LIQUID
            and int(getattr(cell, "liquid", 0) or 0) >= ECHO_LIQUID_AMOUNT)


def propagate(state, x: int, y: int, radius: int) -> dict[tuple[int, int], int]:
    """返回 ``{(gx, gy): 余量}``；只包含余量 > 0 的格子。

    四邻按右、下、左、上的固定顺序推进；余量相同用坐标稳定决胜，
    结果不随容器遍历顺序变化。
    """
    strength = source_strength(radius)
    if strength <= 0 or not (0 <= x < state.width and 0 <= y < state.height):
        return {}
    start = (x, y)
    residual = {start: strength}
    source_cell = state.cell(x, y)
    if source_cell.solid:
        # 声源在固体／台面里：先付本格穿透费，不从封闭实体里免费出发。
        cost = _cell_cost(source_cell)
        if cost is None:
            return {}
        remaining = strength - cost
        if remaining < MIN_RESIDUAL:
            return {}
        residual[start] = remaining
    heap = [(-residual[start], x, y)]
    directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
    while heap:
        neg, cx, cy = heapq.heappop(heap)
        current_residual = -neg
        if residual.get((cx, cy)) != current_residual:
            continue
        current = state.cell(cx, cy)
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            neighbor = state.cell(nx, ny)
            cost = _edge_cost(current, neighbor)
            if cost is None:
                continue
            value = current_residual - cost
            if value < MIN_RESIDUAL:
                continue
            if value > residual.get((nx, ny), MIN_RESIDUAL - 1):
                residual[(nx, ny)] = value
                heapq.heappush(heap, (-value, nx, ny))
    return _dampen(state, residual, x, y)


def _dampen(state, residual: dict[tuple[int, int], int], x: int, y: int
            ) -> dict[tuple[int, int], int]:
    """静音圈（core/item_devices.py）：穿过边界的声再多损 QUIET_EXTRA_LOSS。

    判据是「这一格与声源是否分处静音圈两侧」——分处两侧说明声音必须穿过边界，
    于是按既有传播损耗再额外衰减一次；同一格里最多算一次，来回穿越也只扣一次。
    圈内声音互相传不扣（没穿过边界），也不清警戒、不挡非声音感知。
    """
    try:
        from .item_devices import quiet_zones
        zones = quiet_zones(state)
    except Exception:
        return residual
    if not zones:
        return residual
    for cx, cy, radius in zones:
        source_inside = max(abs(x - cx), abs(y - cy)) <= radius
        for (gx, gy), value in list(residual.items()):
            target_inside = max(abs(gx - cx), abs(gy - cy)) <= radius
            if target_inside != source_inside:
                residual[(gx, gy)] = value - QUIET_EXTRA_LOSS
    return residual


def residual_at(field: dict[tuple[int, int], int], x: int, y: int) -> int:
    """未传播到的格子返回 −1000；余量 0 是「刚好达到标准阈值」。"""
    return int(field.get((x, y), -1000))


def hears(field: dict[tuple[int, int], int], x: int, y: int,
          hearing: int, threshold: int = 0,
          origin: tuple[int, int] | None = None) -> bool:
    """接收者条件：在 H 格内且余量达到阈值；无声、H=0 一律听不见。"""
    if hearing <= 0:
        return False
    if origin is not None:
        distance = abs(x - origin[0]) + abs(y - origin[1])
        if distance > hearing:
            return False
    residual = residual_at(field, x, y)
    if residual < MIN_RESIDUAL:
        return False
    return residual >= int(threshold)
