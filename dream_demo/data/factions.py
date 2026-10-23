"""三派系与声望档位（重构方案 §4.2／§4.3）。

派系是**本局**对一群角色的态度账本：同一个 faction_id 下的成员共享声望分值，
但声望改变的是「开放哪些委托与服务」，不制造普遍战斗倍率，也不让低声望成员
见面即攻击——武装追责必须来自 §4.4 的明确事件状态（立场状态机管对象，
这里管群体账本，两条线互不替代）。

职业与派系不是一一绑定：没有列进成员表的职业（夜药剂师、催眠师、小魔鬼、
当铺老板、报童、回路检修员等）保持独立；「松散关联」者（诗人、提灯门房）
共享派系身份但不享受完整服务（首版先同账本，差异留待服务解锁落地时再分）。
"""
from __future__ import annotations

from typing import Any

#: 声望分值范围（§4.3）。
REPUTATION_MIN = -6
REPUTATION_MAX = 6

#: 普通任务完成 +1，重要阶段完成 +2（§4.3「同一任务实例只改变一次声望」
#: 由运行时的一次性结算键保证，见 world.relations.adjust_reputation）。
TASK_REWARD_NORMAL = 1
TASK_REWARD_MAJOR = 2

FACTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "faction.scavengers": {
        "name": "拾荒协会",
        "creed": "安全回收、清理威胁、保全可用物。",
        # §4.2：拾荒者、登记员、拾荒的行动委托人。
        "members": ("npc.scrapper", "npc.scrap_registrar", "npc.scavenger"),
        "loose": (),
        "services": "可选择的委托、标记猎场、回收服务、附近巡卫协助。",
    },
    "faction.memory_keepers": {
        "name": "守忆会",
        "creed": "记录、辨认、保留不可替代的记忆。",
        # §4.2：档案员、精神观测家；诗人松散关联。
        "members": ("npc.archivist", "npc.mind_observer"),
        "loose": ("npc.nameless_poet",),
        "services": "未知地点情报、设施鉴定、显影服务、重要故事线。",
    },
    "faction.dream_paths": {
        "name": "梦路同盟",
        "creed": "路线、庇护、互助与重逢。",
        # §4.2：引路人、失物招领员、织梦酒保；普通门房可关联。
        "members": ("npc.guide", "npc.lost_found", "npc.dream_bartender"),
        "loose": ("npc.lantern_keeper",),
        "services": "中继点、渡口、旅人消息、临时庇护和迁移地点。",
    },
}

#: 声望档位表（§4.3）：(下限, 上限, 名称, 默认影响)。区间闭闭、互斥、覆盖全域。
REPUTATION_TIERS: tuple[tuple[int, int, str, str], ...] = (
    (-6, -4, "失信", "拒绝高风险委托与非必要支援，关键安全出口仍可用。"),
    (-3, -2, "戒备", "服务条件更严格，先进行说明或补偿。"),
    (-1, 1, "陌生", "正常服务和基础委托。"),
    (2, 3, "可信", "增加一条情报、服务选择或一次当地支援。"),
    (4, 6, "托付", "开放少数重要委托、特殊设施权限；不增加普遍战斗倍率。"),
)


def faction_of(npc_kind: str) -> str | None:
    """职业 → 派系 ID；独立职业返回 None。松散关联者也算入册（共享账本）。"""
    for faction_id, definition in FACTION_DEFINITIONS.items():
        if npc_kind in definition["members"] or npc_kind in definition["loose"]:
            return faction_id
    return None


def tier_of(reputation: int) -> dict[str, Any]:
    """声望分值 → 档位信息（label／范围／影响）。越界值先钳制再查表。"""
    value = max(REPUTATION_MIN, min(REPUTATION_MAX, int(reputation)))
    for low, high, label, effect in REPUTATION_TIERS:
        if low <= value <= high:
            return {"label": label, "low": low, "high": high, "effect": effect}
    raise AssertionError(f"声望档位表没有覆盖 {value}")  # pragma: no cover - 表覆盖全域


def tier_label(reputation: int) -> str:
    return tier_of(reputation)["label"]
