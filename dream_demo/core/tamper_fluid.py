
"""流体搬运计划：先算清楚再执行（2026-10-18 docs 第 8 节第五批）。

守恒原则：
- 一份计划同时列出「从哪些格取多少」「往哪些格放多少」；执行只消费这份计划；
- 目的地容量不足时只搬可容纳部分，剩余留在来源，绝不先删源再丢弃产物；
- 首批自动计划只处理同材料/空格目的地，不同材料相邻保持原状（混合反应仍可
  由真实机制触发，但不纳入自动搬运预算）；
- 气体目的地受单格 100 上限约束；液体按真实混合入口处理；
- 预览与执行共用同一份 FluidPlan；计划失效（成员/存量/目的地变化）时拒绝，
  不静默换源或缩水。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..i18n import tr
from .tamper_regions import region_at

FLUID_VERBS = {"spill": ("liquid", "spread"), "scatter": ("gas", "spread"),
               "gather_liquid": ("liquid", "gather"), "gather_gas": ("gas", "gather")}
GAS_CELL_CAP = 100


@dataclass
class FluidPlan:
    word_id: str
    state_kind: str
    material: str
    source_cells: tuple[tuple[int, int], ...]
    destination: tuple[int, int] | None
    removals: tuple[tuple[int, int, int], ...]
    moves: tuple[tuple[int, int, str, int], ...]
    requested: int
    moved: int
    residual: int
    signature: tuple = ()
    blocked_reason: str = ""

    def valid(self, state: Any) -> bool:
        return _fluid_signature(state, self) == self.signature


def _amount(state: Any, x: int, y: int, kind: str) -> int:
    cell = state.cell(x, y)
    return int(cell.liquid if kind == "liquid" else cell.gas)


def _material(state: Any, x: int, y: int, kind: str) -> str:
    cell = state.cell(x, y)
    return str(cell.liquid_kind if kind == "liquid" else cell.gas_kind)


def _headroom(state: Any, x: int, y: int, kind: str, material: str) -> int:
    cell = state.cell(x, y)
    if cell.solid:
        return 0
    existing = _amount(state, x, y, kind)
    existing_kind = _material(state, x, y, kind)
    if existing > 0 and existing_kind != material:
        return 0
    if kind == "gas":
        return max(0, GAS_CELL_CAP - existing)
    return 10 ** 9


def _fluid_signature(state: Any, plan: FluidPlan) -> tuple:
    sources = tuple((x, y, _material(state, x, y, plan.state_kind),
                     _amount(state, x, y, plan.state_kind))
                    for x, y in plan.source_cells)
    dest = ()
    if plan.destination is not None:
        dx, dy = plan.destination
        dest = ((dx, dy, _material(state, dx, dy, plan.state_kind),
                 _amount(state, dx, dy, plan.state_kind)),)
    move_cells = tuple(sorted({(x, y) for x, y, _material_, _amount in plan.moves}))
    move_dest = tuple((x, y, _material(state, x, y, plan.state_kind),
                       _amount(state, x, y, plan.state_kind)) for x, y in move_cells)
    return (plan.word_id, plan.state_kind, plan.material, sources, dest, move_dest,
            plan.requested, plan.moved)


def _same_material_sources(state: Any, slot: Any, kind: str) -> tuple[tuple[int, int], ...]:
    members = tuple(getattr(slot, "region_members", ()) or ())
    if members:
        return tuple(sorted(members))
    return ((slot.x, slot.y),)


def _distribute(requested: int, destinations: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """按目的地容量均分请求量；返回 [(x,y,amount)]，不足时留 residual。"""
    remaining = requested
    out: dict[tuple[int, int], int] = {}
    active = [(x, y, cap) for x, y, cap in destinations if cap > 0]
    while remaining > 0 and active:
        progressed = False
        share = max(1, remaining // len(active))
        next_active = []
        for x, y, cap in active:
            if remaining <= 0:
                next_active.append((x, y, cap))
                continue
            give = min(cap, share, remaining)
            if give <= 0:
                continue
            out[(x, y)] = out.get((x, y), 0) + give
            remaining -= give
            cap -= give
            progressed = True
            if cap > 0:
                next_active.append((x, y, cap))
        if not progressed:
            break
        active = next_active
    return [(x, y, amount) for (x, y), amount in sorted(out.items())]


def build_fluid_plan(state: Any, word_id: str, slot: Any,
                     *, destination: tuple[int, int] | None = None) -> FluidPlan | str:
    """建立确定计划；返回原因字符串表示不可执行（不抛异常）。"""
    if word_id not in FLUID_VERBS:
        return tr("这个字词不支持流体搬运。")
    kind, verb = FLUID_VERBS[word_id]
    region_members = tuple(getattr(slot, "region_members", ()) or ())
    dest: tuple[int, int] | None = None

    if verb == "gather":
        dest = destination
        if dest is None and not region_members:
            dest = (slot.x, slot.y)
        if dest is None:
            return tr("聚流需要先选定一个明确落点。")
        dx, dy = dest
        if not (0 <= dx < state.width and 0 <= dy < state.height):
            return tr("落点不在地图内。")
        if region_members and not state.is_visible(dx, dy):
            return tr("落点不在视野内。")
        if dest in region_members:
            return tr("落点不能就在来源里。")
        if region_members:
            sources = tuple(sorted(region_members))
        else:
            sources = tuple(sorted(
                (nx, ny) for nx, ny in ((dx + 1, dy), (dx - 1, dy), (dx, dy + 1), (dx, dy - 1))
                if 0 <= nx < state.width and 0 <= ny < state.height))
        if not sources:
            return tr("这里没有可以搬运的流体。")
        source_materials = {_material(state, x, y, kind) for x, y in sources
                            if _amount(state, x, y, kind) > 0}
        source_materials.discard("")
        if not source_materials:
            return tr("相邻没有可以聚拢的东西。")
        if len(source_materials) > 1:
            return tr("来源里有不同材料，不能一次搬运。")
        material = source_materials.pop()
        sources = tuple((x, y) for x, y in sources
                        if _amount(state, x, y, kind) > 0
                        and _material(state, x, y, kind) == material)
        if not any(abs(x - dx) + abs(y - dy) == 1 for x, y in sources):
            return tr("落点没有与来源相邻。")
        cap = _headroom(state, dx, dy, kind, material)
        if cap <= 0:
            return tr("落点放不下这种材料。")
        requested = sum(_amount(state, x, y, kind) for x, y in sources)
        destinations = [(dx, dy, cap)]
    else:
        sources = tuple(sorted(region_members)) if region_members else ((slot.x, slot.y),)
        material = _material(state, sources[0][0], sources[0][1], kind)
        if not material:
            return tr("这里没有可以搬运的流体。")
        if any(_material(state, x, y, kind) != material for x, y in sources):
            return tr("这个区域里有不同材料，不能一次搬运。")
        total = sum(_amount(state, x, y, kind) for x, y in sources)
        if total < 2:
            return tr("这里的分量太少，搬不开。")
        requested = max(1, total // 2)
        seen: set[tuple[int, int]] = set(sources)
        destinations: list[tuple[int, int, int]] = []
        for x, y in sources:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in seen or not (0 <= nx < state.width and 0 <= ny < state.height):
                    continue
                if region_members and not state.is_visible(nx, ny):
                    continue
                seen.add((nx, ny))
                cap = _headroom(state, nx, ny, kind, material)
                if cap > 0:
                    destinations.append((nx, ny, cap))
        if not destinations:
            return tr("周围没有可以摊开的格子。")

    if kind == "liquid":
        from .tamper_protection import liquid_reason
        if liquid_reason(material):
            return tr(liquid_reason(material))
    moves = _distribute(requested, destinations)
    moved = sum(amount for _x, _y, amount in moves)
    if moved <= 0:
        return tr("目的地容量不够，搬不过去。")
    remaining = moved
    removals: list[tuple[int, int, int]] = []
    for x, y in sources:
        amount = _amount(state, x, y, kind)
        if amount <= 0:
            continue
        take = min(amount, remaining)
        if take > 0:
            removals.append((x, y, take))
            remaining -= take
        if remaining <= 0:
            break
    if remaining > 0:
        return tr("来源存量不足，计划不可执行。")
    move_tuples = tuple((x, y, material, amount) for x, y, amount in moves)
    plan = FluidPlan(word_id=word_id, state_kind=kind, material=material,
                     source_cells=tuple(sources), destination=dest,
                     removals=tuple(removals), moves=move_tuples,
                     requested=requested, moved=moved, residual=requested - moved)
    plan.signature = _fluid_signature(state, plan)
    return plan


def apply_fluid_plan(state: Any, plan: FluidPlan) -> tuple[str, str]:
    """按计划执行；计划失效或容量变化时拒绝，不先删源。"""
    if not isinstance(plan, FluidPlan):
        return "", tr("没有可以执行的搬运计划。")
    if not plan.valid(state):
        return "", tr("眼前的情形已经改变，请重新选择。")
    kind = plan.state_kind
    # 二次核对目的地仍能放下全部搬运量（计划有效签名已含存量，这里是防御）。
    for x, y, material, amount in plan.moves:
        if _headroom(state, x, y, kind, material) < amount:
            return "", tr("落点已经放不下，请重新预览。")
    for x, y, amount in plan.removals:
        cell = state.cell(x, y)
        current = int(cell.liquid if kind == "liquid" else cell.gas)
        after = max(0, current - amount)
        if kind == "liquid":
            cell.liquid = after
            if after <= 0:
                cell.liquid_kind = ""
        else:
            cell.gas = after
            if after <= 0:
                cell.gas_kind = ""
    for x, y, material, amount in plan.moves:
        cell = state.cell(x, y)
        if kind == "liquid":
            state._add_liquid(cell, material, amount)
        else:
            state._add_gas(cell, material, amount)
    state._material_index_ready = False
    return tr("搬运完成：移动 {moved}，来源剩余 {residual}。",
              moved=plan.moved, residual=plan.residual), ""


def fluid_plan_preview(plan: FluidPlan) -> dict:
    return {
        "moved": plan.moved,
        "residual": plan.residual,
        "requested": plan.requested,
        "sources": plan.source_cells,
        "removals": plan.removals,
        "moves": plan.moves,
        "destination": plan.destination,
        "material": plan.material,
    }
