"""§12 A：无缓存参考光场（正确性对照，不参与渲染）。

用途（docs 第十二节 §8 批次 A、§9.1 验收）：

- 给 B 批「完整缓存」提供逐格对照基准：同一组来源，参考场**不做截断、
  不按位置合并、不量化**，直接按定义逐源求和；
- 给测试提供小场景可手算的期望值（纯 Python、不依赖 NumPy）；
- 回答「某个合法来源有没有被丢掉」——生产光池只看最终底色，这里能拿到
  逐来源的衰减值。

不变量：

- 不读 ``GameState``、不缓存、不推进时间、不消耗随机流；
- 与 ``ui/effects._light_pool`` 共用同一条衰减曲线（``falloff`` / ``core_term``），
  否则对照没有意义；
- 返回**未量化** RGB 浮点贡献；显示用的上限、底色放行门槛、噪点都在渲染侧，
  参考场不复制它们。

机械照明（视距延长、显影资格）不在这里：那仍由 ``core/vision/glow.py`` 的
``source_radius()`` 决定，参考场只描述装饰彩光。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceSource:
    """参考场的一个来源（世界坐标；与视口无关）。"""

    source_id: str
    x: int
    y: int
    color: tuple[int, int, int]
    radius: float
    brightness: float
    # 该来源允许照亮的格（世界坐标）。None = 不限（等价于没有遮挡）。
    allowed: frozenset[tuple[int, int]] | None = None

    def covers(self, x: int, y: int) -> bool:
        return self.allowed is None or (x, y) in self.allowed


def parse_color(value) -> tuple[int, int, int]:
    """``#rrggbb`` 或 (r, g, b) → (r, g, b)。"""
    if isinstance(value, tuple):
        return (int(value[0]), int(value[1]), int(value[2]))
    text = str(value).lstrip("#")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def core_term(distance2: float, radius: float) -> float:
    """高光核：与光池同一条 ``max(0, 1-d²/min(r,3)²)²``。

    核只负责「近端不过曝的亮心」，不随大半径无限摊平。
    """
    inner = min(max(radius, 1e-6), 3.0)
    value = max(0.0, 1.0 - distance2 / (inner * inner))
    return value * value


def falloff(distance2: float, radius: float, brightness: float) -> float:
    """二次衰减 + 亮度系数：与光池 ``(1-d²/r²)² × 亮度`` 逐字一致。"""
    r2 = max(radius, 1e-6) ** 2
    value = max(0.0, 1.0 - distance2 / r2)
    return value * value * max(0.0, brightness)


def attenuation(source: ReferenceSource, x: int, y: int) -> float:
    """单个来源在 (x, y) 的衰减值；超出半径或被自身掩码挡住 → 0。"""
    if not source.covers(x, y):
        return 0.0
    dx = x - source.x
    dy = y - source.y
    return falloff(dx * dx + dy * dy, source.radius, source.brightness)


def source_contributions(sources, x: int, y: int) -> dict[str, float]:
    """(x, y) 上每个来源的衰减值（>0 才算参与）。

    同格多来源各自留名——「同色不同身份不能合并」在这里是天然成立的。
    重复身份（同一物理来源重复登记）取最大值，不叠加。
    """
    result: dict[str, float] = {}
    for source in sources:
        value = attenuation(source, x, y)
        if value <= 0.0:
            continue
        key = source.source_id or f"{source.x},{source.y}"
        if value > result.get(key, 0.0):
            result[key] = value
    return result


def reference_field(sources, cells) -> dict[tuple[int, int], tuple[float, float, float]]:
    """未量化 RGB 贡献：逐格把每个来源的 ``衰减 × 光色`` 相加。

    用 ``math.fsum`` 求和，因此结果与来源输入顺序无关（B 批缓存重排来源后
    才可能真的一致，不能靠「碰巧同序」通过对照）。没有来源贡献的格不出现，
    也不产生黑色条目。
    """
    sources = tuple(sources)
    field: dict[tuple[int, int], tuple[float, float, float]] = {}
    for x, y in cells:
        per_source = source_contributions(sources, x, y)
        if not per_source:
            continue
        reds: list[float] = []
        greens: list[float] = []
        blues: list[float] = []
        used: set[str] = set()
        for source in sources:
            key = source.source_id or f"{source.x},{source.y}"
            weight = per_source.get(key)
            if not weight or key in used:
                continue
            used.add(key)
            cr, cg, cb = source.color
            reds.append(weight * cr)
            greens.append(weight * cg)
            blues.append(weight * cb)
        field[(x, y)] = (math.fsum(reds), math.fsum(greens), math.fsum(blues))
    return field


def coverage_gaps(sources, cells) -> dict[str, int]:
    """统计每个来源在给定范围内照到几格（0 = 被丢掉/被完全遮挡）。

    这是 §9.1「顺序打乱、缩放和移动不能让同一合法灯随机消失」的可机器判定
    形式：B 批缓存场与参考场逐来源对照时，任何来源计数为 0 都要给出原因。
    """
    counts: dict[str, int] = {}
    for source in sources:
        key = source.source_id or f"{source.x},{source.y}"
        counts.setdefault(key, 0)
    for x, y in cells:
        for key in source_contributions(sources, x, y):
            counts[key] = counts.get(key, 0) + 1
    return counts
