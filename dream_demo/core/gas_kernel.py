"""CY-4：气体扩散内核（源集合筛选 + 目标预算分配）。

只搬纯循环：**不改变**候选顺序、预算、平局顺序、RNG 调用顺序或反应规则。
``_simulate_gas_pass`` 仍在 Python 侧完成落点结算、时钟和索引同步。
"""
from __future__ import annotations

from ..materials import CONTAINER_KINDS, GAS_DEFINITIONS
from .constants import GAS_MIN_FLOW


def collect_gas_sources(grid, width: int, height: int, gas_cells, deferred,
                        sealed, budget: int):
    """返回 (sources, amounts, 下一拍延后候选)。顺序与原实现逐项一致。"""
    candidates = list(deferred or ())
    for x, y in tuple(gas_cells):
        if not (0 <= y < height and 0 <= x < width):
            continue
        cell = grid[y][x]
        if (
            cell.gas >= GAS_MIN_FLOW
            and cell.gas_kind in GAS_DEFINITIONS
            and not (cell.solid and cell.height > 1)
            and cell.wall_kind not in CONTAINER_KINDS
        ):
            candidates.append((x, y, cell.gas, cell.gas_kind))
    sources: list[tuple[int, int, int, str]] = []
    amounts: dict[tuple[int, int], int] = {}
    for x, y, amount, kind in candidates[:budget]:
        if (x, y) in sealed or not (0 < x < width - 1 and 0 < y < height - 1):
            continue
        sources.append((x, y, amount, kind))
        amounts[(x, y)] = amount
    return sources, amounts, candidates[budget:]


def plan_material_transfers(x: int, y: int, targets: list, amounts: dict,
                            reserved: dict, budget: int, equalize: bool) -> list:
    source_remaining = amounts.get((x, y), 0)
    target_levels = {
        target: amounts.get(target, 0) + reserved.get(target, 0)
        for target in targets
    }
    planned = {target: 0 for target in targets}
    while budget > 0 and source_remaining > 0:
        chosen = None
        chosen_level = 0
        for target in targets:
            level = target_levels[target]
            if level >= 100:
                continue
            if equalize and source_remaining - level < 2:
                continue
            if chosen is None or level < chosen_level:
                chosen = target
                chosen_level = level
        if chosen is None:
            break
        target_levels[chosen] += 1
        source_remaining -= 1
        planned[chosen] += 1
        budget -= 1
    return [(target, planned[target]) for target in targets if planned[target] > 0]
