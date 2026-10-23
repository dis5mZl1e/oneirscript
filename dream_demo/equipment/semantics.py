"""语义注册表（§5.3）：由现有 `effect` 统一推导，不改装备定义的效果。

语义是**权限**而非额外倍率：同一语义经过三件装备仍只出现一次。
注册表必须可审计——没有列入的效果可以传递脉冲，但不提供语义。
共用效果 id 的装备以明确定义的词义区分：高压水泵提供湿意象，
聚气喷嘴不提供湿意象；实际液体是否存在仍由反馈执行器检查。
"""

from __future__ import annotations

SEMANTICS = ("湿", "电", "热", "声", "护", "照", "拍", "空")

EFFECT_SEMANTICS: dict[str, frozenset[str]] = {
    # 湿
    "spray_liquid": frozenset({"湿"}),
    "spray_boost": frozenset({"湿"}),
    "wet_conduct": frozenset({"湿", "电"}),
    "liquid_ward": frozenset({"湿", "护"}),
    # 电
    "shock_aura": frozenset({"电"}),
    "wire_safe": frozenset({"电"}),
    # 热
    "ignite_strike": frozenset({"热"}),
    "fire_affinity": frozenset({"热"}),
    "fire_ward": frozenset({"热", "护"}),
    "fireburst": frozenset({"热"}),
    "blast_padding": frozenset({"热", "护"}),
    "blast_radius": frozenset({"热"}),
    "unlock_fire": frozenset({"热"}),
    "ash_retreat": frozenset({"热"}),
    # 声
    "noise_cut": frozenset({"声"}),
    "echo_control": frozenset({"声"}),
    # 护
    "mind_armor": frozenset({"护"}),
    "lucidity_armor": frozenset({"护"}),
    "dual_armor": frozenset({"护"}),
    "mind_guard": frozenset({"护"}),
    "hang": frozenset({"护"}),
    # 照
    "vision_up": frozenset({"照"}),
    "lamp": frozenset({"照"}),
    "measure": frozenset({"照"}),
    "wall_sense": frozenset({"照"}),
    # 拍
    "swift_strike": frozenset({"拍"}),
    "slow_aura": frozenset({"拍"}),
    "quiet_steps": frozenset({"拍"}),
    # 空
    "blank_edge": frozenset({"空"}),
    "blank_pass": frozenset({"空"}),
    "erase_strike": frozenset({"空"}),
}


DEFINITION_SEMANTICS = {"air_concentrator": frozenset()}


def semantics_of(effect: str | None, definition_id: str = "") -> frozenset[str]:
    if definition_id in DEFINITION_SEMANTICS:
        return DEFINITION_SEMANTICS[definition_id]
    if not effect:
        return frozenset()
    return EFFECT_SEMANTICS.get(effect, frozenset())
