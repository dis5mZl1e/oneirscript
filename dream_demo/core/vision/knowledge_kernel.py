"""CY-6：知识运行时内核（cell_knowledge）。

与 core.vision.knowledge.cell_knowledge 逐字段同义（2026-10-27）：只把
每帧上千次的热函数体搬进编译单元，分支顺序、默认值、返回类型完全一致，
不改变感知/记忆规则、不缓存跨帧结果。

可验证的等价接缝：
- _cell_terrain 仍从 knowledge 模块上动态取，因此
  tests/test_knowledge_snapshot_cost.py 对 knowledge._cell_terrain 的
  monkeypatch 计数在开关两端都成立；
- _as_knowledge / _with_site / _always_visible_category 在此内联为等价的
  单次 CellKnowledge 构造，返回值逐字段相同（site 默认空串，只有地点标记
  存在时才写入，等价于 _with_site 的 replace）。
"""
from __future__ import annotations

from . import knowledge as _knowledge
from .knowledge import (ALWAYS_VISIBLE_LIQUID_KINDS,
                        ALWAYS_VISIBLE_WALL_KINDS, CellKnowledge)


def _make(snapshot, x, y, status, live, sources, elevation, site):
    """等价的 _with_site(_as_knowledge(...))：一次构造，字段完全相同。"""
    return CellKnowledge(
        x=x, y=y, status=status,
        floor=snapshot.floor, solid=snapshot.solid, wall_kind=snapshot.wall_kind,
        aggregate_variant=snapshot.aggregate_variant, seen_turn=snapshot.seen_turn,
        live=live, sources=sources, elevation=elevation,
        site=site,
        height=None if status == "always_visible" else snapshot.height,
    )


def _always_visible_category(cell):
    """knowledge._always_visible_category 的等价内联（查表集合不变）。"""
    if bool(getattr(cell, "solid", False)):
        if str(getattr(cell, "wall_kind", "") or "") in ALWAYS_VISIBLE_WALL_KINDS:
            return "意识边界"
    if int(getattr(cell, "liquid", 0) or 0) > 0:
        if str(getattr(cell, "liquid_kind", "") or "") in ALWAYS_VISIBLE_LIQUID_KINDS:
            return "显影液"
    return ""


def cell_knowledge(state, x, y, visible=None,
                   memory_layer=None,
                   developed=None) -> CellKnowledge:
    """按三层信息规则合并一格的可显示内容（不修改状态）。语义同纯 Python 版。"""
    x, y = int(x), int(y)
    if not (0 <= x < state.width and 0 <= y < state.height):
        return CellKnowledge(x=x, y=y, status="unknown")
    cell = state.cell(x, y)
    turn = int(getattr(state, "time", 0) or 0)
    if memory_layer is None:
        memory_layer = state.terrain_memory.get(state.layer_key()) or {}
    if developed is None:
        developed = state.developed_for_depth()

    if ((x, y) in visible if visible is not None else state.is_visible(x, y)):
        # 快照按需构造；这里必须走 knowledge 模块属性，保留 monkeypatch 接缝。
        current = _knowledge._cell_terrain(cell, turn)
        return _make(current, x, y, "visible", True, ("sight",),
                     current.elevation, "")
    if (x, y) in developed:
        current = _knowledge._cell_terrain(cell, turn)
        return _make(current, x, y, "developed", True, ("developed",),
                     current.elevation, "")
    if (bool(getattr(state, "terrain_known", False))
            or getattr(state, "realm_id", "") == "toy_memories"):
        current = _knowledge._cell_terrain(cell, turn)
        remembered = memory_layer.get((x, y))
        return _make(current, x, y, "terrain_known", True, ("terrain_known",),
                     current.elevation,
                     remembered.site if remembered is not None else "")
    category = _always_visible_category(cell)
    if category:
        current = _knowledge._cell_terrain(cell, turn)
        remembered = memory_layer.get((x, y))
        return _make(current, x, y, "always_visible", True,
                     ("always_visible", category), None,
                     remembered.site if remembered is not None else "")
    memory = memory_layer.get((x, y))
    if memory is not None:
        source = ("tutorial_chart" if memory.seen_turn == -1
                  and state.depth == 0 and not state.realm_id else "memory")
        return _make(memory, x, y, "memory", False, (source,),
                     memory.elevation, memory.site)
    return CellKnowledge(x=x, y=y, status="unknown")
