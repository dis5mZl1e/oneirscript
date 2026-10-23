"""Typed default meanings; position and bound function words select readings."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite
from typing import Iterable

from ..data.items import ITEM_DEFINITIONS

COLUMN_ROLES = ("condition", "source", "modifier", "modifier",
                "verb", "object", "complement", "complement")
ROLE_LABELS = ("条件", "载体", "修饰", "修饰", "行为", "对象", "补语", "补语")
BASIC_WORDS = {"use_word": "use", "cover_word": "cover", "maintain_word": "maintain"}
CONSUMABLE_TOOLS = frozenset(("model_screw", "stair_bolt", "tape_measure"))
WARD_EFFECTS = frozenset(("mind_armor", "lucidity_armor", "dual_armor",
                         "mind_guard", "liquid_ward", "fire_ward", "wire_safe",
                         "blast_padding", "hang"))
CONDITION_EFFECTS = {
    "shock_aura": ("event", "hurt"),
    "ignite_strike": ("event", "hit"),
    "attach_hunt": ("attached", ""),
    "wet_conduct": ("conductive", ""),
    "blank_edge": ("low_imagination", ""),
    "blank_pass": ("empty_imagination", ""),
    "ash_retreat": ("event", "ignite"),
    "echo_control": ("event", "voice"),
    # 2026-10-14 槽位差异化：条件位从 8 效果扩到 13——照明/视野件供「有光」，
    # 火亲和供「可燃」，喷液件供「有液体」，折射印记供「目标带印记」。
    # 求值器见 runtime.condition_value（flammable/wet/marked 三个新谓词）。
    "lamp": ("lit", ""),
    "vision_up": ("lit", ""),
    "fire_affinity": ("flammable", ""),
    "spray_liquid": ("wet", ""),
    "refract_mark": ("marked", ""),
}
# 能随「维持/披覆」契约常驻的效果集合——补语位（随句补足）只收这些。
# 口径：全局/被动消费端真实存在（_effect_power / effect_power 的读取点）；
# 武器动作、一次性工具与纯反应句原语（无契约消费端的）不在此列。
CONTRACT_EFFECTS = WARD_EFFECTS | frozenset((
    "quiet_steps", "noise_cut", "slow_aura", "vision_up", "lamp", "wall_sense",
    "repair_up", "swift_pickup", "spray_boost", "attach_hunt", "pierce_up",
    "fire_affinity", "blast_radius", "wet_conduct", "coin_bonus", "swift_strike",
    "echo_control", "ash_retreat", "blank_pass", "blank_edge", "refract_mark",
    "throw_master", "ignite_strike", "shock_aura", "sleep_strike", "erase_strike",
))
# 修饰列反馈映射：这些效果的修饰让命中/落点带出对应执行原语。
# relations（「地/的」路径）与 positional（裸修饰路径）共用同一张表，
# 保证两种摆法的反馈语义永远一致。
FEEDBACK_FROM_MODIFIER = {
    "fire_affinity": "ignite", "wet_conduct": "conduct", "blast_radius": "blast",
}
PAYLOADS = {
    "ignite_strike": "heat", "fire_affinity": "heat", "ash_retreat": "heat",
    "blast_radius": "blast", "shock_aura": "electric", "wet_conduct": "electric",
    "echo_control": "sound", "noise_cut": "sound", "quiet_steps": "quiet",
    "swift_strike": "tempo", "slow_aura": "tempo", "erase_strike": "blank",
    "blank_edge": "recovery", "blank_pass": "blank", "repair_up": "repair",
    "repair": "repair", "spray_liquid": "liquid", "spray_gas": "gas",
    "spray_boost": "liquid", "vision_up": "vision", "lamp": "vision",
    "measure": "measure", "wall_sense": "vision", "refract_mark": "refract",
    "attach_hunt": "hunt", "coin_bonus": "reward", "pierce_up": "pierce",
    "swift_pickup": "pickup", "throw_master": "throw",
}
PAYLOAD_LABELS = {
    "cut": "刀痕", "heat": "余温", "electric": "静电", "sound": "声音",
    "ward": "护持", "liquid": "液态记忆", "gas": "弥散印象",
    "recovery": "回流", "blank": "留白", "repair": "修缮", "vision": "照见",
    "tempo": "节拍", "quiet": "静谧", "frost": "霜意",
}
REACTION_OPS = {
    # 只有 opcode 在 execute_feedback 原语集合（ignite/shock/strike/cover）里的
    # 效果才能做反应句。ash_retreat/wet_conduct/echo_control 的消费端走
    # _effect_power（点燃奖励/放电传导/引诱武装），不在反馈预算里——
    # 它们在行为位按「维持」契约注册，否则编译成永远执行不了的死反应句。
    "shock_aura": ("shock", "hurt"),
}
ACTION_MODIFIER_EFFECTS = frozenset((
    'swift_strike', 'pierce_up', 'spray_boost', 'attach_hunt', 'fire_affinity',
    'blast_radius', 'repair_up', 'throw_master', 'wet_conduct',
))


@dataclass(frozen=True)
class RoleResponse:
    role: str
    meaning: str
    kind: str
    opcode: str = ""
    effect: str = ""
    power: int = 0
    secondary: int = 0
    payload_type: str = ""
    event: str = ""
    condition_kind: str = ""
    profile: tuple[tuple[str, object], ...] = ()
    action_modes: tuple[str, ...] = ()
    consumes_source: bool = False
    reading: str = "default"


@dataclass(frozen=True)
class DamageSource:
    instance_id: str
    definition_id: str
    value: float
    channel: str = "weapon_damage"


def damage_norm(sources: Iterable[DamageSource]) -> float:
    """Call only with context-filtered sources from one compatible action."""
    unique: dict[tuple[str, str], float] = {}
    for source in sources:
        if source.channel != "weapon_damage":
            raise ValueError("Different numeric channels cannot share a damage norm")
        value = float(source.value)
        if not isfinite(value) or value < 0:
            raise ValueError("Damage contributions must be finite and nonnegative")
        key = (source.instance_id, source.channel)
        unique[key] = max(unique.get(key, 0.0), value)
    return hypot(*unique.values())


def is_weapon(definition: dict) -> bool:
    return definition.get("slot") == "手中意象" or bool(
        definition.get("melee") or definition.get("fire")
        or definition.get("ranged") or definition.get("spray"))


def melee_increment(definition: dict) -> int:
    value = int(definition.get("melee", {}).get("damage", 0) or 0)
    # Native multi-segment weapons already carry more than one point of body
    # damage. Keep that intrinsic excess as this instance's contribution while
    # the shared root still receives its one base point exactly once.
    value += max(0,int(definition.get('melee',{}).get('segments',1))-1)
    if definition.get("effect") == "weapon_damage":
        value += int(definition.get("power", 0) or 0)
    return max(0, value)


def _profile(definition: dict) -> tuple[tuple[str, object], ...]:
    melee = definition.get("melee", {})
    fire = definition.get("fire", {})
    spray = definition.get("spray", {})
    profile: dict[str, object] = {
        "melee_damage": int(melee.get("damage", 0) or 0),
        "melee_time": float(melee.get("time", 1.0)),
        "segments": int(melee.get("segments", 1)),
    }
    for name, value in fire.items():
        profile["fire_" + name] = tuple(value) if isinstance(value, list) else value
    for name, value in spray.items():
        profile["spray_" + name] = value
    if definition.get("projectile_template"):
        profile["projectile_template"] = definition["projectile_template"]
    return tuple(sorted(profile.items()))


def resolve_role(definition_id: str, role: str,
                 operand_type: str | None = None, *, reading: str = 'default') -> RoleResponse | None:
    """Resolve a fixed role or an explicitly typed branch; no world access."""
    if role not in COLUMN_ROLES:
        return None
    definition = ITEM_DEFINITIONS.get(definition_id)
    if definition is None:
        return None
    if definition_id.startswith("library."):
        from .library import resolve_library_role
        return resolve_library_role(definition_id, role, operand_type)
    if definition_id.startswith("hospital.") and definition.get("effect", "").startswith("hospital_"):
        from .hospital import resolve_hospital_role
        return resolve_hospital_role(definition_id, role, operand_type)
    effect = str(definition.get("effect") or "")
    power = int(definition.get("power", 0) or 0)
    secondary = int(definition.get("power_secondary", 0) or 0)
    name = str(definition.get("name", definition_id))
    weapon = is_weapon(definition)
    profile = _profile(definition)
    modes = ("melee",)
    if definition.get("spray"):
        modes += ("spray_" + definition["spray"]["medium"],)
    elif definition.get("fire") or definition.get("ranged") or effect == "unlock_fire":
        modes += ("fire",)
    payload = "ward" if effect in WARD_EFFECTS else PAYLOADS.get(effect, "buff")
    if weapon:
        payload = "cut"
        if definition.get("fire", {}).get("pulse"):
            payload = "sound"
        elif definition.get("fire", {}).get("portent", [None])[0] == "frozen":
            payload = "frost"
        elif definition.get("spray"):
            payload = definition["spray"]["medium"]
    if definition_id == "air_concentrator":
        payload = "gas"

    common = dict(effect=effect, power=power, secondary=secondary,
                  profile=profile, consumes_source=definition_id in CONSUMABLE_TOOLS)
    if role == "source":
        # 2026-10-14 载体真实化：载体报出自己的载荷族（旧版恒 "carrier"，
        # 检视与文本读不出任何差异）。武器仍报 cut/弹药族；近战创伤收集
        # 口径（payload "cut" 才计）不受影响——现数据里全部近战武器的
        # 载荷都落 "cut"。
        return RoleResponse(role, name, "carrier", payload_type=payload,
                            action_modes=modes if weapon else (), **common)
    if role == "condition":
        predicate = CONDITION_EFFECTS.get(effect)
        if predicate:
            kind, event = predicate
            return RoleResponse(role, kind, "condition", condition_kind=kind,
                                event=event, **common)
        return None
    if role == "object":
        if definition.get('container'):
            return RoleResponse(role, name, 'payload', payload_type='container_' +
                                definition['container']['medium'], **common)
        return RoleResponse(role, PAYLOAD_LABELS.get(payload, name), "payload",
                            opcode=payload, payload_type=payload, **common)
    if role == "modifier":
        # The glove's heat is an operand, not a hidden heat modifier in both layouts.
        if effect == "ignite_strike" and not weapon:
            return None
        if reading == 'manner' and effect in ACTION_MODIFIER_EFFECTS:
            # A manual manner word chooses the item's way of acting. A blade's
            # rhythm is tempo here, while its attributed edge remains damage.
            manner_payload = PAYLOADS.get(effect, payload) if weapon else payload
            return RoleResponse(role, PAYLOAD_LABELS.get(manner_payload, name), 'modifier',
                                opcode=effect, payload_type=manner_payload, **common)
        if weapon and (melee_increment(definition) or definition.get("melee", {}).get("segments")):
            if reading == 'manner':
                cut = dict(common, effect='cut', power=melee_increment(definition))
                return RoleResponse(role, '锋利', 'modifier', opcode='cut', payload_type='cut', **cut)
            return RoleResponse(role, "锋利", "modifier", opcode="cut",
                                payload_type="cut", **common)
        if effect in ACTION_MODIFIER_EFFECTS:
            return RoleResponse(role, PAYLOAD_LABELS.get(payload, name), "modifier",
                                opcode=effect, payload_type=payload, **common)
        return None
    if role == "complement":
        # 2026-10-14 槽位差异化：补语位从 5 个手挑效果扩成全部可契约效果
        # （CONTRACT_EFFECTS）；武器不做随句补足——它们在任意列都按伤害/
        # 修饰参与，不充当持续契约的搭乘件。
        if not weapon and effect in CONTRACT_EFFECTS:
            return RoleResponse(role, PAYLOAD_LABELS.get(payload, name), "supplement",
                                opcode=effect, payload_type=payload, **common)
        return None
    if role == "verb":
        if definition.get('container'):
            return None  # A finite material noun needs an actual transfer verb.
        if definition_id in CONSUMABLE_TOOLS:
            opcode = "measure" if definition_id == "tape_measure" else "repair"
            return RoleResponse(role, PAYLOAD_LABELS.get(opcode, opcode), "action",
                                opcode=opcode, action_modes=("use_tool",), **common)
        if weapon:
            opcode = "strike"
            if definition.get("spray"):
                opcode = "spray_" + definition["spray"]["medium"]
            elif "fire" in modes:
                opcode = "fire"
            meaning = {"strike": "斩击", "fire": "发射", "spray_liquid": "喷射液体",
                       "spray_gas": "喷射气体"}[opcode]
            return RoleResponse(role, meaning,
                                "action", opcode=opcode, action_modes=modes, **common)
        if effect == "ignite_strike":
            if operand_type == "cut":
                return RoleResponse(role, "印下", "action", opcode="imprint",
                                    payload_type="cut", event="use_sentence",
                                    action_modes=("imprint",), **common)
            return RoleResponse(role, "点燃", "reaction", opcode="ignite",
                                payload_type="heat", event="hit", **common)
        if effect in REACTION_OPS:
            opcode, event = REACTION_OPS[effect]
            return RoleResponse(role, PAYLOAD_LABELS.get(payload, name), "reaction",
                                opcode=opcode, event=event, **common)
        return RoleResponse(role, "披覆" if effect in WARD_EFFECTS else "维持",
                            "contract", opcode="cover" if effect in WARD_EFFECTS else "maintain",
                            payload_type=payload, **common)
    return None
