"""CY-3：视野射线内核（布雷森汉姆 + 预算消耗）。

与 ``SightMixin._observer_sight_reaches`` 逐格同义：遮挡判定、黑烟截断、
灰尘衰减、技能/光幕阻挡全部沿用 state 上的方法，内核只把射线循环本身
搬进编译单元，不改变规则、不改变 RNG、不缓存跨帧结果。
"""
from __future__ import annotations


def observer_sight_reaches(state, observer, x1: int, y1: int, radius: int) -> bool:
    x0, y0 = observer.x, observer.y
    if (x0, y0) == (x1, y1):
        return True
    budget = float(radius)
    if budget <= 0:
        return False
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx - dy
    x, y = x0, y0
    step = 0
    skill_blocked = state._skill_sight_blockers() if hasattr(state, "_skill_sight_blockers") else set()
    from ..construct_environments import light_curtain_cells
    skill_blocked = skill_blocked | light_curtain_cells(state)
    while (x, y) != (x1, y1):
        doubled = 2 * error
        if doubled > -dy:
            error -= dy
            x += sx
        if doubled < dx:
            error += dx
            y += sy
        step += 1
        if step > budget:
            return False
        if (x, y) == (x1, y1):
            break
        cell = state.cell(x, y)
        if (x, y) in skill_blocked:
            return False
        blocks, penalty = state._sight_obstruction(cell)
        if blocks:
            return False
        if penalty:
            budget = max(float(step), budget - penalty)
        blocked, attenuation = state._gas_sight_effect(cell)
        if blocked:
            return False
        if attenuation < 1.0:
            budget = step + (budget - step) * attenuation
    return True
