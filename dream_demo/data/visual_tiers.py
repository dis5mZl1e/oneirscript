"""显式视觉等级登记（2026-10-26，ASCII 动画扩展 Task 9）。

等级按设计 3.1 由设计者显式登记；定义里的默认/战斗档位作为推荐依据，
不在运行时凭伤害或当前数值自动升级。本模块只决定演出预算与结构，不改玩法。

- 异象技能：default_tier 0/1/2 → V1/V2/V3；Boss 招牌与高难技能逐条覆盖。
- 构想：combat.tier 1/2/3/4 → V1/V1/V2/V3；地标高难条目录覆盖。
"""
from __future__ import annotations

TIER_NAMES = ("V0", "V1", "V2", "V3")

#: 设计者显式登记的地标异象技能等级（覆盖 default_tier 推荐值）。
SKILL_TIER_OVERRIDES: dict[str, int] = {
    "core_cry": 3,          # 初啼声浪
    "core_beacon": 3,       # 灯塔转光
    "scribe_stroke": 3,     # 落笔断行
    "scribe_erase": 2,      # 局部擦除
    "scribe_draft": 2,
    "scribe_revision": 2,
    "library.last_page": 3,  # 最后一页
    "hospital.core_infusion": 2,  # 回流配液
    "space_fold": 2,
    "fold_guard": 1,
    "hospital.syringe_dash": 1,
    "hospital.ring_wash": 2,
    "library.foldstep": 2,
}

#: 设计者显式登记的构想等级；未列出的按 combat.tier / V1 推荐。
ABILITY_TIER_OVERRIDES: dict[str, int] = {
    "flame_nova": 2,        # 烈焰新星
    "rewrite_corner": 3,    # 重写一隅
    "combat.fault_ring": 2,  # 裂地环
    "pixel_surge": 1,       # 像素拆解（V1 强调特色）
    "vanish": 1,
    "blink": 1,
    "combat.delayed_shell": 2,
    "combat.arc_orb": 2,
    "library.fold": 2,
    "library.bookmark": 1,
    "library.inkline": 1,
    "library.erase": 1,
    "library.clamp": 2,
    "library.margin": 2,
}

_COMBAT_TIER_TO_VISUAL = {1: 1, 2: 1, 3: 2, 4: 3}


def _clamp(tier: int) -> int:
    return max(0, min(3, int(tier)))


def tier_label(tier: int) -> str:
    return TIER_NAMES[_clamp(tier)]


def tier_for_skill(skill_id: str) -> int:
    """异象技能的显式视觉等级（0..3）。"""
    override = SKILL_TIER_OVERRIDES.get(str(skill_id))
    if override is not None:
        return _clamp(override)
    from .anomaly_skills import SKILL_DEFINITIONS

    skill = SKILL_DEFINITIONS.get(str(skill_id))
    if skill is None:
        return 1
    return _clamp(1 + int(getattr(skill, "default_tier", 0) or 0))


def skill_tier_source(skill_id: str) -> str:
    return "explicit" if str(skill_id) in SKILL_TIER_OVERRIDES else "definition"


def tier_for_ability(ability_id: str) -> int:
    """构想的显式视觉等级（0..3）。"""
    override = ABILITY_TIER_OVERRIDES.get(str(ability_id))
    if override is not None:
        return _clamp(override)
    from .abilities import ABILITY_DEFINITIONS

    row = ABILITY_DEFINITIONS.get(str(ability_id))
    if not isinstance(row, dict):
        return 1
    combat = row.get("combat") or {}
    tier = combat.get("tier") if isinstance(combat, dict) else None
    if tier in _COMBAT_TIER_TO_VISUAL:
        return _COMBAT_TIER_TO_VISUAL[int(tier)]
    return 1


def ability_tier_source(ability_id: str) -> str:
    if str(ability_id) in ABILITY_TIER_OVERRIDES:
        return "explicit"
    from .abilities import ABILITY_DEFINITIONS

    row = ABILITY_DEFINITIONS.get(str(ability_id))
    combat = (row or {}).get("combat") if isinstance(row, dict) else None
    return "combat_tier" if isinstance(combat, dict) and combat.get("tier") else "recommended"


def tier_histogram() -> dict:
    from .abilities import ABILITY_DEFINITIONS
    from .anomaly_skills import SKILL_DEFINITIONS

    histogram = {name: 0 for name in TIER_NAMES}
    for skill_id in SKILL_DEFINITIONS:
        histogram[TIER_NAMES[tier_for_skill(skill_id)]] += 1
    for ability_id in ABILITY_DEFINITIONS:
        histogram[TIER_NAMES[tier_for_ability(ability_id)]] += 1
    return histogram
