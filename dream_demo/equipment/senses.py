"""词义注册表（语法核心版 §4.2）。

一件装备拥有一个有形词块，首发最多两个词义；每条句子只选择其一个词义。
词义由独立注册表映射，保留物品名称与原始定义，不从翻译文本解析。
词义不是任意选择的全能技能库：数值型原能力在适当语句里仍使用原 `power`。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .semantics import semantics_of

WEAPON_SLOT = "手中意象"

HOLD_VERBS = {
    "自我表层": "披覆",
    "依附物": "系上",
    "依附物·一": "系上",
    "依附物·二": "系上",
    "惯用物": "随手带着",
}


@dataclass(frozen=True)
class Sense:
    sense_id: str
    definition_id: str
    kind: str  # hold | act | node
    effect: str | None
    power: int
    power_secondary: int
    semantics: frozenset
    label: str
    text: str

    @property
    def registers_ability(self) -> bool:
        return self.kind in ("hold", "act")


def _definition(definition_id: str) -> dict:
    from ..data.items import ITEM_DEFINITIONS

    return ITEM_DEFINITIONS.get(definition_id, {})


@lru_cache(maxsize=None)
def senses_for(definition_id: str) -> tuple[Sense, ...]:
    definition = _definition(definition_id)
    name = str(definition.get("name", definition_id))
    effect = definition.get("effect") or None
    power = int(definition.get("power", 0) or 0)
    secondary = int(definition.get("power_secondary", 0) or 0)
    slot = str(definition.get("slot") or "")
    semantics = semantics_of(effect, definition_id)
    weapon = slot == WEAPON_SLOT or bool(
        definition.get("melee") or definition.get("ranged") or definition.get("spray")
    )
    if weapon:
        primary = Sense(
            sense_id=f"{definition_id}#原意", definition_id=definition_id, kind="act",
            effect=effect, power=power, power_secondary=secondary, semantics=semantics,
            label="本义·握持",
            text=f"我用{name}命中目标：保持它的原攻击规格与成本。",
        )
    else:
        verb = HOLD_VERBS.get(slot, "带着")
        primary = Sense(
            sense_id=f"{definition_id}#原意", definition_id=definition_id, kind="hold",
            effect=effect, power=power, power_secondary=secondary, semantics=semantics,
            label="本义",
            text=f"我{verb}{name}：{definition.get('description', '')}",
        )
    senses = [primary]
    if semantics or definition_id == 'air_concentrator':
        # 第二词义：交出原效果，只作为句中的意象词块提供语义权限。
        senses.append(Sense(
            sense_id=f"{definition_id}#意象", definition_id=definition_id, kind="node",
            effect=effect, power=power, power_secondary=secondary, semantics=semantics,
            label="借意",
            text=f"{name}在句中只作为「{'、'.join(sorted(semantics))}」的意象词块，不注册原效果。",
        ))
    return tuple(senses)


def default_sense(definition_id: str) -> Sense:
    return senses_for(definition_id)[0]


def sense(definition_id: str, sense_id: str) -> Sense | None:
    return next((s for s in senses_for(definition_id) if s.sense_id == sense_id), None)


def resolve(definition_id: str, sense_id: str) -> Sense:
    """取选定词义；空缺或非法时回落原意（迁移与旧存档安全初值）。"""
    found = sense(definition_id, sense_id) if sense_id else None
    return found or default_sense(definition_id)


def describe_sense(value: Sense, name: str) -> str:
    """Localized display; grammar never parses translated text."""
    from ..i18n import tr
    if value.kind == 'act':
        return tr('握住{item}后，用它攻击；收着备用时不会叠加攻击能力。', item=name)
    if value.kind == 'node':
        if not value.semantics:
            return tr('{item}暂时只是安静的念头，不带来原本的装备能力。', item=name)
        return tr('借{item}来表达「{semantics}」，让同一分句的标点产生联想；暂时放下它原本的能力。', item=name,
                  semantics=' / '.join(tr(s) for s in sorted(value.semantics)))
    return tr('带着{item}，便能获得它本来的能力：{effect}', item=name,
              effect=tr(str(_definition(value.definition_id).get('description', ''))))
