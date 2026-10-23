
"""液气区域的可见连通域（2026-10-18 docs 第 8 节第三批）。

区域定义（docs §8.5）：
- 相同物态、相同具体材料、四向连通；仅对角接触不合并；
- 气体/液体分别建区域，同格共存时两层各有一个候选；
- 只使用可见且可参与篡改的格子，不穿过不可见格推断连通；
- 墙体/保护容器/任务储液格不参与，不能把受保护材料搬空；
- 区域标识 = 层键 + 物态 + 材料 + 排序成员集合 + 草稿版本（不写存档）；
- 默认显示不把每格数量塞进材料名，区域格数与存量放范围提示/详情。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..i18n import tr
from .tamper_compass import direction_label
from .tamper_protection import liquid_reason

_STATE_LABELS = {"liquid": "液态", "gas": "气态"}


def _quantifier(state_kind: str, total: float) -> str:
    """材料适配的量词；液体按可见存量分池/滩/洼，气体统一为片。"""
    if state_kind == "gas":
        return tr("一片")
    if total >= 120:
        return tr("一池")
    if total >= 20:
        return tr("一滩")
    return tr("一洼")


@dataclass(frozen=True)
class FluidRegion:
    state_kind: str
    material: str
    members: tuple[tuple[int, int], ...]
    amount: float
    clipped: bool = False

    def signature(self, state: Any) -> tuple:
        amounts = []
        for x, y in self.members:
            cell = state.cell(x, y)
            amounts.append(cell.liquid if self.state_kind == "liquid" else cell.gas)
        return (state.layer_key() if hasattr(state, "layer_key") else "",
                self.state_kind, self.material, self.members, tuple(amounts))


def _fluid_amount(cell: Any, state_kind: str) -> float:
    return float(cell.liquid if state_kind == "liquid" else cell.gas)


def _fluid_kind(cell: Any, state_kind: str) -> str:
    return str(cell.liquid_kind if state_kind == "liquid" else cell.gas_kind)


def _participates(state: Any, x: int, y: int, state_kind: str, material: str) -> bool:
    if not (0 <= x < state.width and 0 <= y < state.height):
        return False
    if not state.is_visible(x, y):
        return False
    cell = state.cell(x, y)
    if _fluid_kind(cell, state_kind) != material or _fluid_amount(cell, state_kind) <= 0:
        return False
    if cell.solid:
        return False
    if state_kind == "liquid" and liquid_reason(material):
        return False
    return True


def _facility_cells(state: Any) -> set[tuple[int, int]]:
    try:
        from .tamper_protection import _facility_cells as facility_cells
        return set(facility_cells(state))
    except Exception:
        return set()


def region_at(state: Any, x: int, y: int, state_kind: str) -> FluidRegion | None:
    """从 (x,y) 出发的可见四向连通区域；不含受保护/不可见格。"""
    if state_kind not in ("liquid", "gas"):
        raise ValueError(state_kind)
    facility = _facility_cells(state)
    if (x, y) in facility:
        return None
    if not _participates(state, x, y, state_kind, _fluid_kind(state.cell(x, y), state_kind)):
        return None
    material = _fluid_kind(state.cell(x, y), state_kind)
    members: list[tuple[int, int]] = []
    stack = [(x, y)]
    seen = {(x, y)}
    while stack:
        cx, cy = stack.pop()
        members.append((cx, cy))
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if (nx, ny) in seen or (nx, ny) in facility:
                continue
            if not _participates(state, nx, ny, state_kind, material):
                continue
            seen.add((nx, ny))
            stack.append((nx, ny))
    members.sort()
    clipped = any(
        not (0 <= nx < state.width and 0 <= ny < state.height) or not state.is_visible(nx, ny)
        for mx, my in members
        for nx, ny in ((mx + 1, my), (mx - 1, my), (mx, my + 1), (mx, my - 1))
    )
    total = sum(_fluid_amount(state.cell(mx, my), state_kind) for mx, my in members)
    return FluidRegion(state_kind, material, tuple(members), total, clipped)


def all_regions(state: Any, state_kind: str) -> list[FluidRegion]:
    """可见区域内所有同材料四向连通块；对角/墙隔/不可见都断开。"""
    facility = _facility_cells(state)
    seen: set[tuple[int, int]] = set()
    regions: list[FluidRegion] = []
    for y in range(state.height):
        for x in range(state.width):
            if (x, y) in seen or (x, y) in facility:
                continue
            if not state.is_visible(x, y):
                continue
            cell = state.cell(x, y)
            if _fluid_amount(cell, state_kind) <= 0:
                continue
            region = region_at(state, x, y, state_kind)
            if region is None:
                continue
            seen.update(region.members)
            regions.append(region)
    return regions


def region_directions(state: Any, region: FluidRegion) -> tuple[str, ...]:
    seen: list[str] = []
    for x, y in region.members:
        label = direction_label(x - state.player.x, y - state.player.y)
        if label not in seen:
            seen.append(label)
    return tuple(seen)


def _direction_span(state: Any, region: FluidRegion) -> str:
    directions = region_directions(state, region)
    if not directions:
        return tr("脚下")
    if len(directions) == 1:
        return directions[0]
    # 按八方向顺序取首尾；不连续时用顿号并列，不硬凑成「A 至 B」。
    from .tamper_compass import _SECTOR_ORDER
    ordered = sorted(directions, key=lambda label: _SECTOR_ORDER.get(label.replace("侧", ""), 9))
    indices = [_SECTOR_ORDER.get(label.replace("侧", ""), 9) for label in ordered]
    # 方位是环形列表：西北(7)、北(0)、东北(1) 实际连续，不能因排序断点误判。
    gaps = [(b - a, index) for index, (a, b) in enumerate(zip(indices, indices[1:]))]
    wrap_gap = 8 - indices[-1] + indices[0]
    big_gap = max([(gap, index) for gap, index in gaps] + [(wrap_gap, len(indices) - 1)],
                  key=lambda item: item[0])
    if len(indices) > 1 and big_gap[0] > 1:
        rotate_at = big_gap[1] + 1
        ordered = ordered[rotate_at:] + ordered[:rotate_at]
        indices = indices[rotate_at:] + indices[:rotate_at]
    contiguous = all((b - a) % 8 in (0, 1) for a, b in zip(indices, indices[1:]))
    if contiguous:
        return tr("{first}至{last}", first=ordered[0], last=ordered[-1])
    return "、".join(ordered)


def region_reference(state: Any, region: FluidRegion, material_label: str) -> str:
    span = _direction_span(state, region)
    quantifier = _quantifier(region.state_kind, region.amount)
    suffix = tr("的可见部分") if region.clipped else ""
    return tr("{span}的{quantifier}{material}{suffix}",
              span=span, quantifier=quantifier, material=material_label, suffix=suffix)


def region_range_text(region: FluidRegion) -> str:
    """范围提示：格数 + 可作用存量（不塞进材料名）。"""
    return tr("可见 {cells} 格 · 存量 {amount:g}",
              cells=len(region.members), amount=region.amount)


def slot_range_text(slot: Any) -> str:
    return tr("可见 {cells} 格 · 存量 {amount:g}",
              cells=len(slot.region_members), amount=slot.region_amount)
