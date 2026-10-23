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

# 稀有度四档。
ITEM_RARITIES = ("常见", "少见", "稀有", "非常稀有")

# ✦ 随机选项（事件选项）的候选池：按类别收集带稀有度的物品。
# 带 loot=False 的物品（容器/洞察之镜）刻意不入池。
RANDOM_OPTION_ITEM_POOL = {
    _category: tuple(
        (item_id, definition.get("rarity", ""), "")
        for item_id, definition in ITEM_DEFINITIONS.items()
        if (definition.get("category") == _category and definition.get("rarity")
            and definition.get("loot", True) is not False)
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
