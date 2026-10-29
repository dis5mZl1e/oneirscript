"""混乱极高专属异象的主动技能 handler（2026-10-27 玩家需求）。

数据定义在 data/chaos_anomalies.py（技能表/绑定/文案），索引在
data/anomaly_skills.py（'chaos.' 前缀）。本模块只补少量**专属**施法/结算，
其余两个技能直接复用 EnemySkillMixin 的既有 handler：

- chaos.wrath_ray      -> _cast_line / _skill_resolve_default_hit（既有）
- chaos.false_light_halo -> _cast_slow_pool / _resolve_field_only（既有）
- chaos.wrath_burst    -> 本模块：自身周围半径 2 的嗔火爆发（命中掀开一格）
- chaos.hollow_drain   -> _cast_line / 本模块：命中后吸血自愈
- chaos.hollow_gorge   -> 本模块：目标周围半径 2 的空洞（额外流失想象力）
- chaos.false_light_gaze -> 本模块：失焦征兆 + 想象流失

注册方式照 hospital/library/tamper：在 core/enemy_skills.py 文件末尾调用
:func:`register_chaos_skills`，只写 _SKILL_CASTERS/_SKILL_RESOLVERS 两张表。
"""

from __future__ import annotations

from typing import Any

from ..i18n import tr


def _hit(state: Any, pending: dict) -> bool:
    warned = {tuple(cell) for cell in pending.get("warning_cells") or ()}
    warned |= {tuple(cell) for cell in pending.get("locked_path") or ()}
    return (int(state.player.x), int(state.player.y)) in warned


def _drain_imagination(state: Any, amount: int, *, source: str) -> int:
    """抹去想象力：走既有结算（护持/免疫/死亡判定一致），返回实际扣减量。"""
    if amount <= 0:
        return 0
    from .settlement import REASON_COMBAT, settle_delta

    before = int(getattr(state, "imagination", 0) or 0)
    settle_delta(state, "imagination", -int(amount), reason=REASON_COMBAT, source=source)
    return max(0, before - int(getattr(state, "imagination", before) or 0))


# ---------------------------------------------------------------------------
# 嗔影：嗔爆（自身周围半径 2 的爆发）
# ---------------------------------------------------------------------------

def cast_wrath_burst(state: Any, enemy: Any, skill: Any, binding: Any):
    if not state._sk_player_visible(enemy, skill.max_range):
        return None
    distance = max(abs(enemy.x - state.player.x), abs(enemy.y - state.player.y))
    if distance > 3:
        # 火要够得着才起手：目标太远时先走位，不空放。
        return None
    cells = [cell for cell in state._sk_diamond(enemy.x, enemy.y, 2)
             if state._sk_open(cell[0], cell[1])]
    if not cells:
        return None
    return cells, None, None, {"overrides": dict(binding.overrides)}


def resolve_wrath_burst(state: Any, enemy: Any, skill: Any, pending: dict) -> None:
    if not _hit(state, pending):
        state._note_skill_miss(enemy, skill)
        state.messages.append(tr("嗔爆在你身边炸开——你已经在火外。"))
        return
    power = state._skill_power(enemy, skill)
    state._enemy_skill_trauma(enemy, power, skill.trauma_channel)
    state.messages.append(tr(
        "嗔影自燃了一瞬——嗔爆把你卷进去（{channel} {power}）。",
        channel=tr(skill.trauma_channel), power=power,
    ))
    if not state._player_control_immune():
        state._skill_push_player(enemy, away=True)


# ---------------------------------------------------------------------------
# 空心者：掏空之吸（命中后吸血自愈）
# ---------------------------------------------------------------------------

def resolve_hollow_drain(state: Any, enemy: Any, skill: Any, pending: dict) -> None:
    if not _hit(state, pending):
        state._note_skill_miss(enemy, skill)
        state.messages.append(tr("空心者隔空吸了一口——线已经偏了。"))
        return
    power = state._skill_power(enemy, skill)
    state._enemy_skill_trauma(enemy, power, skill.trauma_channel)
    maximum = int((enemy.active_skill_state or {}).get("max_integrity")
                  or getattr(enemy, "integrity", 0) or 0)
    healed = min(2, max(0, maximum - int(enemy.integrity)))
    if healed:
        enemy.integrity = int(enemy.integrity) + healed
    state.messages.append(tr(
        "空心者把你的力气吸了过去（心智 {power}；它补回 {healed} 点完整度）。",
        power=power, healed=healed,
    ))


# ---------------------------------------------------------------------------
# 空心者：空腹洞开（目标周围半径 2 的空洞 + 想象流失）
# ---------------------------------------------------------------------------

def cast_hollow_gorge(state: Any, enemy: Any, skill: Any, binding: Any):
    if not state._sk_player_visible(enemy, skill.max_range):
        return None
    cells = [cell for cell in state._sk_diamond(state.player.x, state.player.y, 2)
             if state._sk_open(cell[0], cell[1])]
    if not cells:
        return None
    return cells, None, None, {"overrides": dict(binding.overrides)}


def resolve_hollow_gorge(state: Any, enemy: Any, skill: Any, pending: dict) -> None:
    if not _hit(state, pending):
        state._note_skill_miss(enemy, skill)
        state.messages.append(tr("空洞在你刚才站着的地方张开，什么也没卷住。"))
        return
    power = state._skill_power(enemy, skill)
    state._enemy_skill_trauma(enemy, power, skill.trauma_channel)
    drained = _drain_imagination(state, 2, source="混乱·空腹洞开")
    state.messages.append(tr(
        "空腹洞开：周围的想象被吸进去一点（心智 {power}；想象力 −{n}）。",
        power=power, n=drained,
    ))


# ---------------------------------------------------------------------------
# 伪光者：伪光注视（失焦征兆 + 想象流失）
# ---------------------------------------------------------------------------

def cast_false_light_gaze(state: Any, enemy: Any, skill: Any, binding: Any):
    if not state._sk_player_visible(enemy, skill.max_range):
        return None
    target = (int(state.player.x), int(state.player.y))
    return [target], None, target, {"overrides": dict(binding.overrides)}


def resolve_false_light_gaze(state: Any, enemy: Any, skill: Any, pending: dict) -> None:
    target = tuple(pending.get("target_cell") or ())
    if (int(state.player.x), int(state.player.y)) != target:
        state._note_skill_miss(enemy, skill)
        state.messages.append(tr("伪光落在你刚才站的地方——光没有认住你。"))
        return
    if not state._grant_portent_direct(state.player, "sk_blur"):
        state.messages.append(tr("伪光贴上来了，但你的轮廓没有接住它。"))
        return
    drained = _drain_imagination(state, 3, source="混乱·伪光注视")
    state.messages.append(tr(
        "伪光者盯住你：视野 −1（失焦），想象力 −{n}。", n=drained,
    ))


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

def register_chaos_skills() -> None:
    """把六个混乱专属技能挂进异象技能引擎（复用既有 handler + 专属 handler）。"""
    from .enemy_skills import EnemySkillMixin

    mixin = EnemySkillMixin
    casters = {
        "chaos.wrath_ray": mixin._cast_line,
        "chaos.wrath_burst": cast_wrath_burst,
        "chaos.hollow_drain": mixin._cast_line,
        "chaos.hollow_gorge": cast_hollow_gorge,
        "chaos.false_light_gaze": cast_false_light_gaze,
        "chaos.false_light_halo": mixin._cast_slow_pool,
    }
    resolvers = {
        "chaos.wrath_ray": mixin._skill_resolve_default_hit,
        "chaos.wrath_burst": resolve_wrath_burst,
        "chaos.hollow_drain": resolve_hollow_drain,
        "chaos.hollow_gorge": resolve_hollow_gorge,
        "chaos.false_light_gaze": resolve_false_light_gaze,
        "chaos.false_light_halo": mixin._resolve_field_only,
    }
    mixin._SKILL_CASTERS.update(casters)
    mixin._SKILL_RESOLVERS.update(resolvers)
