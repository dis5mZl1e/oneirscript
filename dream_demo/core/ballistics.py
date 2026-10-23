"""弹道系统（2026-09-19）：形状、墙体阻挡、穿透、特殊墙体效果。

弹道 = 从起点到终点的格子序列。角度只有 8 向（正交 + 斜向），由
``trace_path`` 展开；斜向穿墙的判定与 move_player 的「斜向不能穿过
两面墙的夹缝」一致：两轴分量各自的目标格都是坚实时视为夹缝、被挡。

穿透：弹体有穿透力（penetration），每经过一格坚实聚合物按
``硬度 × 厚度`` 扣减；扣到负值即被阻挡。玉米淀粉墙（projectile_immune）
直接吞掉弹体；玻璃幕墙被击碎时触发 shatter；不稳定燃料墙被击碎时
走 destroy_wall 的 explode 链。

特殊墙体效果表（WALL_HIT_EFFECTS）：击中（未穿透）时触发的附加结算。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

PROJECTILE_MAX_RANGE = 12

# 命中特殊墙体时的效果 id → 描述（结算器据此分发；与 materials.walls 的
# break_effect 字段对齐：击穿失败时的「浅层命中」也走这里）。
WALL_HIT_EFFECTS: dict[str, str] = {
    "shatter": "碎裂成锋利的玻璃渣（周围 1 格受 1 点创伤）",
    "explode": "当场爆炸（半径 1、威力 2）",
    "smoke": "散出一团黑烟",
    "condense": "渗出冷凝水",
    "soak": "化开一摊纸浆",
    "ink": "淌出墨液",
}


@dataclass
class ShotResult:
    """一次弹道结算的完整结果。"""

    path: list[tuple[int, int]] = field(default_factory=list)
    hit_entity_at: tuple[int, int] | None = None
    hit_wall_at: tuple[int, int] | None = None
    wall_effect: str | None = None
    pierced: int = 0
    blocked_reason: str = ""  # wall / gap / entity / range / immune


def trace_path(
    sx: int,
    sy: int,
    dx: int,
    dy: int,
    max_range: int = PROJECTILE_MAX_RANGE,
) -> list[tuple[int, int]]:
    """按 8 向方向展开弹道格序列（不含起点，含最远点）。

    正交方向给出直线；斜向给出 45° 对角线。射界由调用方逐格判定。
    """
    cells: list[tuple[int, int]] = []
    x, y = sx, sy
    for _ in range(max_range):
        x += dx
        y += dy
        cells.append((x, y))
    return cells


def angle_blocked(
    cells: dict[tuple[int, int]],
    sx: int,
    sy: int,
    dx: int,
    dy: int,
) -> bool:
    """斜向弹道的夹缝判定：dx/dy 均非零且两轴正交邻格都是坚实 → 挡。

    ``cells`` 取 ``(x, y) -> 是否坚实``。正交方向永远不构成夹缝。
    """
    if dx == 0 or dy == 0:
        return False
    side_a = cells.get((sx + dx, sy), True)
    side_b = cells.get((sx, sy + dy), True)
    return bool(side_a and side_b)


def bounce_direction(
    solid: dict[tuple[int, int], bool],
    cx: int,
    cy: int,
    dx: int,
    dy: int,
) -> tuple[int, int]:
    """跳弹后的新方向（纯几何、零随机）。

    ``solid`` 取 ``(x, y) -> 是否坚实``；``(cx, cy)`` 是弹体当前格（被挡格的
    前一格）。反射轴沿用 angle_blocked 的两轴侧格几何：

    - 斜向 + 恰好一侧坚实（side_a=(cx+dx,cy) / side_b=(cx,cy+dy)）→ 反射
      该轴（45° 浅角掠射，§9.2 的离散格子语义）；
    - 斜向 + 两侧都坚实或都不坚实 → 原路返回（正撞/全角度面的兜底反射）；
    - 正交 → 原路返回（浅角不存在，正交反弹只属于淀粉墙的全角度规则）。
    """
    if dx == 0 and dy == 0:
        return dx, dy
    if dx != 0 and dy != 0:
        side_a = solid.get((cx + dx, cy), True)
        side_b = solid.get((cx, cy + dy), True)
        if side_a and not side_b:
            return -dx, dy
        if side_b and not side_a:
            return dx, -dy
        return -dx, -dy
    return -dx, -dy


def penetration_left(penetration: int, hardness: int, thickness: int) -> int:
    """穿过一面墙后剩余的穿透力：减去 硬度 × 厚度；负值表示被阻挡。"""
    return penetration - max(1, hardness * thickness)
