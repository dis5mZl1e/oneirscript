"""物品定义聚合：把分文件 ITEMS 合并为全量 ITEM_DEFINITIONS。

类别 → 文件：携带意象=equipment · 易逝物=consumables · 摄入物=ingestibles ·
交互道具=interactives · 惯用物=usables。
容器与洞察之镜带 loot=False：不进自然掉落，只走事件/NPC 交易/核心必掉。
"""

from __future__ import annotations

from typing import Any

from .consumables import ITEMS as CONSUMABLE_ITEMS
from .deployables import ITEMS as DEPLOYABLE_ITEMS
from .equipment import ITEMS as EQUIPMENT_ITEMS
from .ingestibles import ITEMS as INGESTIBLE_ITEMS
from .interactives import ITEMS as INTERACTIVE_ITEMS
from .memories import ITEMS as MEMORY_ITEMS
from .usables import ITEMS as USABLE_ITEMS
from .hospital import ITEMS as HOSPITAL_ITEMS
from .hospital_equipment import ITEMS as HOSPITAL_EQUIPMENT_ITEMS
from ..expansion import by_category as expansion_entries

ITEM_DEFINITIONS = {
    **EQUIPMENT_ITEMS,
    **CONSUMABLE_ITEMS,
    **DEPLOYABLE_ITEMS,
    **INGESTIBLE_ITEMS,
    **INTERACTIVE_ITEMS,
    **USABLE_ITEMS,
    **MEMORY_ITEMS,
    **HOSPITAL_ITEMS,
    **HOSPITAL_EQUIPMENT_ITEMS,
}

# Expansion equipment is registered here so the existing board, inspector and
# sentence compiler can resolve each stable catalog ID. Only entries whose
# catalog status is ``runtime`` enter their designated acquisition route.
_EXPANSION_GEAR_SLOTS = {
    "手中意象": "手中意象",
    "自我表层": "自我表层",
    "依附物": "依附物·一",
    "惯用物": "惯用物",
}
_EXPANSION_EVENT_GRANTS = {
    # This D-permission item is offered by the existing depth-19 photo-booth
    # event. It never enters a floor or random-option pool.
    "expansion.event.light": "event:event.photo_booth",
}
# 逐件事件绑定（2026-10-25 声源批）：同一主题的 D 件分属两个深层事件，
# 因为 E13/E14 的解锁深度是 18、E15/E16 是 24，硬塞进同一个浅层事件会被
# ``item_access.refusal`` 按深度拒绝。
_EXPANSION_ITEM_EVENT_GRANTS = {
    "expansion.sound.e13": "event:event.first_echo",
    "expansion.sound.e14": "event:event.first_echo",
    "expansion.sound.e15": "event:event.blank_gallery",
    "expansion.sound.e16": "event:event.blank_gallery",
    "expansion.terrain.e14": "event:event.tide_of_names",
    # 光主题的浅层 D 件（E14，18 层）仍走快照亭；E15 要 24 层才解锁，
    # 而快照亭只出现在 19 层带——留在那里会被 ``item_access.refusal``
    # 按深度拒掉，等于永远拿不到。改挂 25 层带的「被遗忘的画廊」。
    "expansion.light.e15": "event:event.blank_gallery",
    # 光主题两件 D 件（2026-10-25 批次二）：E13 要 18 层，挂在 21/25 层带的
    # 「初啼的回声」；E16 要 24 层，与 E15 同挂「被遗忘的画廊」。
    "expansion.light.e13": "event:event.first_echo",
    "expansion.light.e16": "event:event.blank_gallery",
}
for _entry in expansion_entries("equipment"):
    _mechanic = _entry.get("mechanic_proposal") or {}
    _implemented = _entry.get("integration_status") == "runtime"
    _roles = (_entry.get("tuning_proposal") or {}).get("equipment_roles") or {}
    _primary = _roles.get("primary") or {}
    _feedback = _roles.get("feedback") or {}
    ITEM_DEFINITIONS[_entry["id"]] = {
        "name": _entry["name_zh"],
        "category": "携带意象",
        "slot": _EXPANSION_GEAR_SLOTS[_entry["slot"]],
        "grammar_kind": _entry["gear_kind"],
        "rarity": _entry["rarity_zh"],
        "color": _entry["icon_color"],
        "description": _entry["description_zh"],
        "effect_description": _entry["description_zh"],
        "loot": bool(_implemented and _entry.get("source_permission") == "G"),
        "grant_source": (
            _EXPANSION_ITEM_EVENT_GRANTS.get(_entry["id"])
            or _EXPANSION_EVENT_GRANTS.get(_entry.get("source_id"))
        ) if _implemented else None,
        "min_depth": int(_entry.get("min_depth", 0) or 0),
        "run_limit": int((_entry.get("tuning_proposal") or {}).get(
            "max_acquisitions_per_run", 0) or 0) if _implemented else 0,
        "integration_status": _entry["integration_status"],
        "expansion_catalog_id": _entry["id"],
        "position_readings": _entry["position_readings"],
        "proposal_payload_type": _mechanic.get("payload_type"),
        "runtime_primary_effect": _mechanic.get("primary_key") if _implemented else "",
        "runtime_feedback_effect": _mechanic.get("feedback_key") if _implemented else "",
        "runtime_primary_params": _primary if _implemented else {},
        "runtime_feedback_params": _feedback if _implemented else {},
        "effect": _mechanic.get("primary_key") if _implemented else "",
        "power": 1 if _implemented else 0,
        # 主动行为规格（形态/范围/处理名）：由 core/actions/items.py 与
        # core/item_targeting.py 读取，装备必须先上盘才能用。
        "active_use": (_mechanic.get("active") or None) if _implemented else None,
    }

from ..expansion.sources import growth_token_rows
from ..expansion.consumable_runtime import consumable_item_rows
from ..expansion.catalog import ENTRIES as _EXPANSION_ENTRIES
ITEM_DEFINITIONS.update(growth_token_rows())
_consumable_rows = consumable_item_rows()
for _entry in expansion_entries("consumable"):
    if _entry.get("integration_status") != "runtime":
        continue
    ITEM_DEFINITIONS[_entry["id"]] = {
        "name": _entry["name_zh"], "category": "易逝物",
        "description": _entry["description_zh"], "color": _entry["icon_color"],
        "rarity": _entry["rarity_zh"], "expansion_catalog_id": _entry["id"],
        "integration_status": "runtime", **_consumable_rows.get(_entry["id"], {}),
    }
for _entry in _EXPANSION_ENTRIES:
    if (_entry.get("integration_status") != "runtime"
            or _entry["id"] not in ITEM_DEFINITIONS):
        continue
    ITEM_DEFINITIONS[_entry["id"]].update(
        loot=_entry["source_permission"] == "G",
        grant_source=_entry["source_id"] if _entry["source_permission"] == "D" else None,
        min_depth=_entry["min_depth"],
        run_limit=_entry["tuning_proposal"]["max_acquisitions_per_run"],
    )

# 稀有度四档。
ITEM_RARITIES = ("常见", "少见", "稀有", "非常稀有")

# ✦ 随机选项（事件选项）的候选池：按类别收集带稀有度的物品。
# 带 loot=False 的物品（容器/洞察之镜）刻意不入池。
RANDOM_OPTION_ITEM_POOL = {
    _category: tuple(
        (item_id, definition.get("rarity", ""), "")
        for item_id, definition in ITEM_DEFINITIONS.items()
        if (definition.get("category") == _category and definition.get("rarity")
            and definition.get("loot", True) is not False
            and not definition.get("expansion_catalog_id"))
    )
    for _category in ("易逝物", "摄入物", "携带意象", "交互道具")
}

# 弹体模板（发射武器的穿透/击退基准）。
PROJECTILE_DEFINITIONS = {
    "直线弹体": {"penetration": 1, "push": 0, "description": "最稳定的直线弹体。"},
    "穿页弹体": {"penetration": 3, "push": 0, "description": "穿过第一层坚实聚合物后仍保持方向。"},
    "冲击弹体": {"penetration": 1, "push": 2, "description": "命中后把对象沿弹道方向推出。"},
    "折返弹体": {"penetration": 2, "push": 1, "description": "撞击低硬度表面后保留一次折返机会。"},
}

# 装备栏位。
EQUIPMENT_SLOTS = ("手中意象", "自我表层", "依附物·一", "依附物·二", "惯用物")
ACCESSORY_SLOTS = ("依附物·一", "依附物·二")
from .library import ITEMS as LIBRARY_ITEMS
ITEM_DEFINITIONS.update(LIBRARY_ITEMS)
from ..item_prose import ITEM_PROSE, EFFECT_START, EFFECT_TEXT
for _item_id, (_prose, _english) in ITEM_PROSE.items():
    _original = ITEM_DEFINITIONS[_item_id]
    _effect_text = _original.get('effect_description', _original['description'])
    if _item_id in EFFECT_START:
        _effect_text = _effect_text[_effect_text.index(EFFECT_START[_item_id]):]
    _effect_text = EFFECT_TEXT.get(_item_id, _effect_text)
    ITEM_DEFINITIONS[_item_id] = dict(
        _original, description=_prose, effect_description=_effect_text)

from ..realm_item_prose import REALM_ITEM_PROSE, REALM_ITEM_EFFECTS
for _item_id, (_prose, _english) in REALM_ITEM_PROSE.items():
    ITEM_DEFINITIONS[_item_id] = dict(ITEM_DEFINITIONS[_item_id],
        description=_prose, effect_description=REALM_ITEM_EFFECTS[_item_id])
