# -*- coding: utf-8 -*-
"""关键任务对象的运行时保护（矩阵见 :mod:`dream_demo.data.tamper_protection`）。

只回答两件事：**这一刀能不能落下去**、**不能时给玩家什么可读理由**。判定读的
全是既有状态（任务记录、世界记录、墙种、格子），不写任务进度、不改地图。

设计口径（docs §二「关键任务对象保护矩阵」）：
- 保护只拦「破坏／删除／稀释」这类**不可逆抹除**；呼唤、退散、引向、鸣响不拦。
- 进行中的任务目标只拦「删除」：删除走环境归因，会把任务降成「确认现场」，
  玩家可能在不知情时把一单任务办废；正常击败仍然可以。
- 台面、门、容器、逻辑固体、场景设施布局格上的固体一律不作可破坏目标。
"""

from __future__ import annotations

from typing import Any

from ..data.tamper_protection import (
    MECHANISM_WALL_KINDS,
    QUEST_KEY_ITEMS,
    QUEST_KEY_LIQUIDS,
)


def item_reason(definition_id: str) -> str:
    """具名任务物品是否受保护；空串表示可删。"""
    if definition_id in QUEST_KEY_ITEMS:
        return "这件东西牵着尚未结束的梦，不能抹去。"
    return ""


def liquid_reason(kind: str) -> str:
    """任务要求的液体种类是否受保护；空串表示可删／可稀释。"""
    if kind in QUEST_KEY_LIQUIDS:
        return "这些液体牵着尚未结束的梦，不能抹去。"
    return ""


def threat_reason(state: Any, enemy: Any) -> str:
    """进行中任务绑定的异象目标：删除会把「击败」悄悄降成「确认现场」。"""
    uid = str(getattr(enemy, "actor_uid", "") or "")
    if not uid:
        return ""
    for record in getattr(state.world_ledger, "tasks", {}).values():
        if (record.status in ("进行中", "待交付")
                and record.target_uid
                and record.target_uid == uid):
            return "它牵着尚未结束的梦，不能抹去。"
    return ""


def _facility_cells(state: Any) -> set[tuple[int, int]]:
    """本层场景设施布局覆盖的全部格子（锚点／边槽／作用区／排放区）。"""
    cells: set[tuple[int, int]] = set()
    layer_key = state.layer_key()
    for record in getattr(state.world_ledger, "facilities", {}).values():
        if record.layer_key != layer_key:
            continue
        # 普通遭遇样板（encounter.*）是玩家可改写的局面内容：它的纸墙/门禁正是
        # 「篡改也是一条解法」的示范，不能按任务设施一并保护。任务场景设施
        # （scene.*）仍逐格保护。
        if str(record.definition_id).startswith("encounter."):
            continue
        for key in record.layout:
            cells.update(record.area(key))
    return cells


def terrain_reason(state: Any, x: int, y: int) -> str:
    """墙体／固体为什么不能被这一笔破坏或抹掉；空串表示可以。"""
    cell = state.cell(x, y)
    if not cell.solid:
        return ""
    wall_kind = str(cell.wall_kind or "")
    if wall_kind == "意识边界":
        return "这段文字太深，改不动。"
    if wall_kind in MECHANISM_WALL_KINDS:
        return "这处机关还没有走完，不能抹去。"
    if cell.wall_kind and state._protected_wall(cell.wall_kind):
        return "这段文字太深，改不动。"
    # 电路节点可能落在普通墙材上：按真实节点表再核一次。
    if state.circuit_node_at(x, y) or state.puzzle_projectile_blocked(x, y):
        return "这处机关还没有走完，不能抹去。"
    if (x, y) in _facility_cells(state):
        return "这处机关还没有走完，不能抹去。"
    return ""


def construction_reason(state: Any, x: int, y: int) -> str:
    """A new solid wall must not bury occupants or overwrite functional ground."""
    from .origin_course import protected_route
    if protected_route(state,x,y):
        return '这里是教学通路，请在练习区内改造。'
    from .tactical_layouts import gate_control_at
    cell=state.cell(x,y)
    if ((state.player.x,state.player.y)==(x,y) or state.entity_at(x,y) is not None
            or any((entry.x,entry.y)==(x,y) for entry in (*state.world_items,*state.events))):
        return '这里有人或物，不能凝成实墙。'
    if (cell.solid or cell.wall_kind or cell.wire or cell.light_radius>0
            or state.circuit_node_at(x,y) or state.puzzle_projectile_blocked(x,y)
            or gate_control_at(state,x,y) is not None
            or (x,y) in _facility_cells(state)):
        return '这里承载着设施或机关，不能凝成实墙。'
    return ''


def slot_reason(state: Any, slot: Any, word_id: str) -> str:
    """按名称槽类别与字词给出保护理由；不适用时返回空串。

    ``word_id`` 只区分「抹除类」与其它：破坏／剥落／崩碎／删除／稀薄／消散大半
    都可能永久减少任务对象，因此共用同一组判定；呼唤等不改对象的字词不查。
    """
    if word_id not in ("delete", "break", "chip", "shatter", "thin", "disperse",
                       "ignite", "soak", "brittle", "spill", "gather_liquid",
                       "evaporate", "solidify"):
        return ""
    category = getattr(slot, "category", "")
    if category == "anomaly":
        # 删除异象的能力由「每层上限／种类」等既有规则管；这里只补任务目标。
        return threat_reason(state, slot.enemy) if word_id == "delete" else ""
    if category == "object":
        entry = next((entry for entry in state.world_items
                      if (entry.x, entry.y) == (slot.x, slot.y)), None)
        return item_reason(entry.item.definition_id) if entry is not None else ""
    if category == "liquid":
        cell = state.cell(slot.x, slot.y)
        return liquid_reason(str(cell.liquid_kind or ""))
    if category == "gas":
        # 气体没有「任务交付物」口径；保留接口方便将来扩展。
        return ""
    if category == "terrain":
        return terrain_reason(state, slot.x, slot.y)
    return ""


def protected_summary(state: Any) -> dict[str, tuple[str, ...]]:
    """当前层真实存在的受保护对象摘要（测试／调试用，不参与结算）。"""
    from ..data.tamper_protection import matrix_rows

    items = tuple(entry.item.definition_id for entry in state.world_items
                  if entry.item.definition_id in QUEST_KEY_ITEMS)
    threats = tuple(str(getattr(enemy, "actor_uid", "")) for enemy in state.enemies
                    if getattr(enemy, "actor_uid", "")
                    and threat_reason(state, enemy))
    facility_cells = tuple(sorted(_facility_cells(state)))
    return {
        "items": items,
        "threats": threats,
        "facility_cells": tuple(str(cell) for cell in facility_cells),
        "matrix_categories": tuple(str(row["category"]) for row in matrix_rows()),
    }
