"""材料扫描内核（方案 1，2026-11-04）。

只做**候选筛选**，不执行任何副作用：所有落账、时钟写入、索引同步、告警与
RNG 调用仍留在 Python 侧的原路径上。筛选条件与原循环逐项一致，只把「这一拍
必然什么都不做」的格子提前剔除，因此顺序（相变按坐标排序、配方按集合迭代
顺序）完全不变。

两个函数在纯 Python 下可直接运行；``scripts/build_cython_ext.py`` 编译后
同一份源码以扩展模块生效。开关见 ``dream_demo/cy_kernels.py``。
"""
from __future__ import annotations


def phase_candidates(cells, width, height, candidates, clock_key, time,
                     vapor, condensate, freeze_by_liquid, wax):
    """相变拍里**可能**需要处理的格子；调用方仍需按坐标排序后再逐格结算。

    与 ``phase_changes.tick`` 的快速判定逐项对应：

    - 当拍已由相变锁定的格子跳过（``phase:at == time``）；
    - 固体：只有蜡墙（``WAX``）进入融化分支，其余（含岩浆/容器）不处理；
    - 有相变存量或冰面：进入 ``melt_ice`` 分支；即便它返回 False，原循环还会
      继续尝试挥发/冷凝/冻结，所以这里同样保留该格；
    - 液体可挥发（``VAPOR``）或可冻结（``FREEZE_BY_LIQUID``）、气体可冷凝
      （``CONDENSATE``）时才保留。
    """
    points = []
    for x, y in candidates:
        if not (0 <= x < width and 0 <= y < height):
            continue
        cell = cells[y][x]
        if cell.material_clocks.get(clock_key) == time:
            continue
        if cell.solid:
            if cell.wall_kind in wax:
                points.append((x, y))
            continue
        if cell.phase_stock or cell.aggregate_variant == '冰面':
            points.append((x, y))
            continue
        liquid = cell.liquid
        gas = cell.gas
        liquid_kind = cell.liquid_kind
        gas_kind = cell.gas_kind
        if ((liquid > 0 and (liquid_kind in vapor or liquid_kind in freeze_by_liquid))
                or (gas > 0 and gas_kind in condensate)):
            points.append((x, y))
    return points


def recipe_cells(cells, width, height, liquid_cells, other_by_reactant):
    """配方拍里**可能**需要处理的液体格，保持 ``_liquid_cells`` 迭代顺序。

    - 液气同格转化：只要有气体且带种类，就进原分支（是否命中配方由 Python
      侧的 ``LIQUID_GAS_RECIPES`` 决定，这里不做提前判断）；
    - 其他反应：液体种类必须登记在 ``OTHER_BY_REACTANT``。

    原实现里墙被熔穿后向**同一格**补气/补液，而那一格此前是固体、不可能在
    ``_liquid_cells`` 快照里，因此不会出现「本拍新加气体让后面的液体格命中
    配方」的漏筛。
    """
    points = []
    limit_x = width - 1
    limit_y = height - 1
    for x, y in liquid_cells:
        if not (0 < x < limit_x and 0 < y < limit_y):
            continue
        cell = cells[y][x]
        if (cell.gas > 0 and cell.gas_kind) or cell.liquid_kind in other_by_reactant:
            points.append((x, y))
    return points
