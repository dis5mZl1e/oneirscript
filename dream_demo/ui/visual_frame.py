"""多层字符帧数据合同（2026-10-26，ASCII 动画扩展 Task 2）。

键一律是世界地图坐标；只有最终图片/字符合成器接收 viewport 后投影一次。
GlyphLayer 的 offset 是格内归一化偏移（-0.5..0.5，0 表示中心），供同格
两个以上特效字符独立定位；纯字符终端按列/行降级。

本模块只有数据与稳定排序，不做绘制；不改动 FxFrame 旧合同。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

CLOCK_MODES = ("turn", "settled", "decorative")
STAGE_ORDER = ("entry", "release", "impact", "tail")


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return len(STAGE_ORDER)


@dataclass(frozen=True)
class GlyphLayer:
    """一个独立字符层；同一格可有多个层，不再用 dict 覆盖。"""

    glyph: str
    color: str = "#ffffff"
    offset: tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0
    alpha: float = 1.0
    z: int = 0
    role: str = "fx"
    event_id: str = ""
    clock_mode: str = "settled"

    def __post_init__(self):
        if self.clock_mode not in CLOCK_MODES:
            raise ValueError(f"未知 clock_mode: {self.clock_mode!r}")
        if not self.glyph:
            raise ValueError("GlyphLayer.glyph 不能为空")
        if not -0.5 <= self.offset[0] <= 0.5 or not -0.5 <= self.offset[1] <= 0.5:
            raise ValueError(f"格内偏移必须归一到 -0.5..0.5: {self.offset!r}")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError(f"alpha 必须在 0..1: {self.alpha!r}")
        if self.scale <= 0.0:
            raise ValueError(f"scale 必须为正: {self.scale!r}")


@dataclass(frozen=True)
class TextGlyph:
    """纯字符终端里地图格内部的字符列行位置。"""

    column: int
    row: int
    glyph: str
    style: str = ""


@dataclass(frozen=True)
class VisualFrame:
    """字符层与作用背景；不含独立像素图元（spec 5.4）。"""

    glyph_layers: dict = field(default_factory=dict)
    backgrounds: dict = field(default_factory=dict)

    def add_layer(self, cell, layer: GlyphLayer) -> "VisualFrame":
        key = (int(cell[0]), int(cell[1]))
        merged = dict(self.glyph_layers)
        merged[key] = (*merged.get(key, ()), layer)
        return replace(self, glyph_layers=merged)

    def add_background(self, cell, color: str) -> "VisualFrame":
        key = (int(cell[0]), int(cell[1]))
        merged = dict(self.backgrounds)
        merged[key] = color
        return replace(self, backgrounds=merged)

    def extend(self, cell, layers) -> "VisualFrame":
        result = self
        for layer in layers:
            result = result.add_layer(cell, layer)
        return result

    def ordered_layers(self, cell) -> tuple:
        layers = self.glyph_layers.get((int(cell[0]), int(cell[1])), ())
        return tuple(sorted(
            enumerate(layers),
            key=lambda item: (item[1].z, item[1].event_id, item[0]),
        ))

    def sorted_layers(self) -> tuple:
        """跨格稳定顺序，供栅格缓存键与确定性输出使用。"""
        items = []
        for cell in sorted(self.glyph_layers):
            for _index, layer in self.ordered_layers(cell):
                items.append((cell, layer))
        return tuple(items)

    @property
    def layer_count(self) -> int:
        return sum(len(layers) for layers in self.glyph_layers.values())

    @property
    def is_empty(self) -> bool:
        return not self.glyph_layers and not self.backgrounds

    def merge(self, other: "VisualFrame") -> "VisualFrame":
        glyphs = dict(self.glyph_layers)
        for cell, layers in other.glyph_layers.items():
            glyphs[cell] = (*glyphs.get(cell, ()), *layers)
        backgrounds = dict(self.backgrounds)
        backgrounds.update(other.backgrounds)
        return VisualFrame(glyphs, backgrounds)


def merge_frames(*frames: VisualFrame) -> VisualFrame:
    merged = VisualFrame()
    for frame in frames:
        merged = merged.merge(frame)
    return merged


def trim_to_budget(frame: VisualFrame, *, per_cell: int, total: int) -> VisualFrame:
    """按稳定顺序保留主层；超预算只裁装饰，不改变作用格含义。"""
    glyphs: dict = {}
    used = 0
    # 主层优先：先按 z 升序（背景在前）保留每格前 per_cell 个，再全局截断。
    for cell in sorted(frame.glyph_layers):
        layers = frame.glyph_layers[cell]
        kept = []
        for _index, layer in sorted(enumerate(layers), key=lambda item: (item[1].z, item[1].event_id, item[0])):
            if len(kept) >= per_cell or used >= total:
                break
            kept.append(layer)
            used += 1
        if kept:
            glyphs[cell] = tuple(kept)
    return VisualFrame(glyphs, dict(frame.backgrounds))
