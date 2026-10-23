
# -*- coding: utf-8 -*-
"""自我察觉（个人菜单）的数据组装：状态条、效果叙述、全属性、征兆。

2026-10-18 docs 第 10 节第一批「真实展示」：只读现有系统，不新增属性；把
写死的行动/远程/恢复说明换成本次真实查询，并把基础值与条件值分开显示。
"""
from __future__ import annotations

from typing import Any

from ..i18n import tr
from .stats import resolve_stat

# 清醒叙述：暗角/扫描线是视觉，穿透与坚固度是环境失控，档 3 开始反向侵蚀心智。
_LUCIDITY_NOTES = {
    0: "视线清亮，地图四角没有暗影。穿墙与碰撞都还按梦的规矩来。",
    1: "视野边缘浮起一圈暗影。穿墙的构想开始多走一寸，坚固的东西也不再那么可靠。",
    2: "暗影压得更近，画面蒙上一层细噪。你的爆炸与构想更容易穿透阻隔，也更容易把家具震散。",
    3: "清醒见了底——每几次呼吸就要磨损一点心智，穿墙与震散都到了极限。",
}

# 心智叙述：短句 + 具体数值摘要（数值由 physics_modifiers 与 drop_bonus 实算）。
_MIND_NOTES = {
    0: "思路清明。异象的名字都还认得出来，爆炸也只烧该烧的地方。",
    1: "有些东西开始说不准——偶尔会觉得眼前的轮廓「像是」别的什么。爆裂比平时更容易脱缰。",
    2: "视野里的轮廓融成一团团未定形的东西，地图边缘也在发暗。你的爆炸与火焰明显更野，梦给的战利品也更多。",
    3: "心智见底。每几次呼吸就要被抽走一点清醒，梦彻底脱了缰。",
}


def _imagination_progress(state: Any) -> tuple[str, str]:
    """想象力的真实恢复说明：自然回流、条件暂停、留白额外回流。

    与 state._advance 的结算共用同一份条件（摇篮曲判定走
    state._imagination_regen_suppressed），不在这里另写一套。
    """
    regen = resolve_stat(state, "imagination.regen_rate")
    rate = max(0.0, regen.value)
    parts: list[str] = []
    if rate <= 0:
        parts.append(tr("摇篮曲在你耳边打转：想象力自然回流暂停。"))
    else:
        parts.append(tr("每回合自然回流约 {rate:g} 点（含医院恢复率与开局修正）。", rate=rate))
        parts.extend(note for note in regen.notes if "留白" in note)
    if int(state.imagination) <= 0:
        parts.append(tr("此刻见底：构想与改写暂时不可用，自然回流仍会把你一点点填回来。"))
    credit = float(resolve_stat(state, "imagination.regen_credit").value)
    numbers = tr(
        "当前 {value}/{maximum} · 下一回合进度 {credit:.2f}",
        value=int(state.imagination), maximum=int(state.max_imagination), credit=credit,
    )
    return " ".join(parts), numbers


_CONDITION_LABELS = {
    "mind.loss_blocked": ("是", "否"),
    "buffer.available": ("可用", "不可用"),
}


def _row(state: Any, stat_id: str, *, label: str | None = None,
         context: dict | None = None, status: str = "") -> dict:
    resolved = resolve_stat(state, stat_id, context)
    value_text = resolved.formatted()
    condition = _CONDITION_LABELS.get(stat_id)
    if condition is not None:
        active = bool(resolved.value)
        value_text = tr(condition[0] if active else condition[1])
        status = status or (tr("当前生效") if active else tr("当前未生效"))
    return {
        "key": stat_id + ("" if not context else ":" + ",".join(
            f"{key}={value}" for key, value in sorted(context.items()))),
        "label": tr(label or resolved.definition.name),
        "value": value_text,
        "base": resolved.base,
        "sources": resolved.sources,
        "source_refs": resolved.source_refs,
        "notes": resolved.notes,
        "status": status,
        "unit": tr(resolved.definition.unit) if resolved.definition.unit else "",
        "stat_id": stat_id,
    }


def _literal_row(label: str, value: str, *, sources=(), notes=(),
                 status: str = "") -> dict:
    return {
        "key": "literal:" + label,
        "label": tr(label),
        "value": value,
        "base": None,
        "sources": tuple(sources),
        "notes": tuple(notes),
        "status": status,
        "unit": "",
        "stat_id": "",
    }


def _sections(state: Any) -> dict[str, list[dict]]:
    """把统一解析结果整理成自我觉察的分类条目（docs §10.7 第六批）。"""
    from ..i18n import STATUS_TIERS
    from .settlement import recent_action_times, recent_settlements

    mind_tier = state.mind_tier
    lucidity_tier = state.lucidity_tier
    dangers: list[str] = []
    if mind_tier >= 2:
        dangers.append(tr("心智失控（{tier}）", tier=tr(STATUS_TIERS[mind_tier])))
    if lucidity_tier >= 2:
        dangers.append(tr("清醒不稳（{tier}）", tier=tr(STATUS_TIERS[lucidity_tier])))
    if state.insight_active("双读") is False:
        pass
    blocked = resolve_stat(state, "mind.loss_blocked")
    if blocked.value:
        dangers.append(tr("心智流失被镇静拦截（环境来源）"))
    if state.portents:
        dangers.append(tr("附着征兆 {n} 种", n=len(state.portents)))
    overview = [
        _literal_row("心理状态",
                     tr("心智 {mind} · 清醒 {lucidity} · 想象 {imagination}",
                        mind=tr(STATUS_TIERS[mind_tier]), lucidity=tr(STATUS_TIERS[lucidity_tier]),
                        imagination=f"{int(state.imagination)}/{int(state.max_imagination)}")),
        _literal_row("主要限制", "；".join(dangers) if dangers else tr("无显著限制"),
                     notes=(tr("限制按实际规则生成，不使用写死的档位故事"),)),
        _row(state, "mind.tier", label="心智档位"),
        _row(state, "lucidity.tier", label="清醒档位"),
        _row(state, "mind.loss_multiplier"),
        _row(state, "mind.loss_blocked"),
    ]
    action = [
        _row(state, "melee.base_trauma"),
        _row(state, "melee.base_time"),
        _row(state, "melee.effective_time"),
        _row(state, "move.base_time"),
        _row(state, "move.effective_time"),
        _row(state, "move.delay_penalty"),
        _row(state, "attack.delay_penalty"),
        _row(state, "action.speed_scale"),
        _row(state, "throw.range"),
    ]
    offense = [
        _row(state, "physics.explosion_bonus"),
        _row(state, "physics.fire_spread_bonus"),
        _row(state, "physics.penetration_bonus"),
        _row(state, "physics.solidity_penalty"),
        _row(state, "dissolution.bonus"),
        _row(state, "loot.luck"),
    ]
    perception = [_row(state, "sight.radius")]
    for channel in ("fire", "electric"):
        resolved = resolve_stat(state, "identity.trauma_multiplier", {"channel": channel})
        if resolved.value != 1.0:
            perception.append(_row(state, "identity.trauma_multiplier",
                                   label="身份环境弱点",
                                   context={"channel": channel}))
    if len(perception) == 1:
        perception.append(_literal_row("身份环境弱点", tr("无（无对应弱点）")))
    recovery = [
        _row(state, "imagination.regen_rate"),
        _row(state, "imagination.regen_credit"),
        _row(state, "imagination.max"),
        _row(state, "mind.max"),
        _row(state, "lucidity.max"),
        _row(state, "buffer.available", context={"kind": "mind"}),
    ]
    ability = [
        _row(state, "ability.cost_multiplier"),
        _row(state, "ability.cooldown_turns", context={"base": 1}),
        _row(state, "tamper.pressure"),
        _row(state, "tamper.chaos_cost", context={"chaos": 0, "imagination": 0}),
    ]
    environment = [
        _row(state, "environment.trauma", context={"channel": "fire", "amount": 1,
                                                   "direct": True}),
        _row(state, "portent.accumulation_factor", context={"portent": "scalded"}),
        _row(state, "portent.effective_duration", context={"portent": "scalded", "base": 5}),
    ]
    sources: list[dict] = []
    for item in state.equipment.items():
        source=_literal_row(tr(item.name), tr("已生效装备"), status="生效")
        source.update(source_kind='equipment',source_id=item.instance_id)
        sources.append(source)
    for fragment_id in getattr(state, "memory_fragments", ()) or ():
        from .content import ITEM_DEFINITIONS
        name = ITEM_DEFINITIONS.get(fragment_id, {}).get("name", fragment_id)
        source=_literal_row(name, tr("记忆碎片"), status="携带")
        source.update(source_kind='memory',source_id=fragment_id)
        sources.append(source)
    for insight in state.insights:
        source = _literal_row(insight, tr('洞察'), status='常驻')
        source.update(source_kind='insight', source_id=insight)
        sources.append(source)
    for portent_id, rounds in sorted(state.portents.items()):
        from ..materials import portent_def
        definition = portent_def(portent_id)
        name = tr(definition.name) if definition is not None else tr(portent_id)
        source = _literal_row(name, tr("征兆 · 剩余 {n} 回合", n=int(rounds)), status="附着")
        source.update(source_kind='portent', source_id=portent_id)
        sources.append(source)
    options = getattr(state, "run_options", None) or {}
    for toggle in (options.get("toggles") or ()) if isinstance(options, dict) else ():
        from .run_options import TOGGLE_DEFS
        spec = TOGGLE_DEFS.get(toggle)
        if spec:
            sources.append(_literal_row(spec["name"], tr("开局调律"), status="本局"))
    recent = [result.to_dict() for result in recent_settlements(state, 20)
              if abs(float(result.applied)) > 1e-9 or result.blocked][-5:]
    recent_actions = [record.to_dict() for record in recent_action_times(state, 3)]
    return {
        "sections": {
            "overview": overview,
            "action": action,
            "offense": offense,
            "perception": perception,
            "recovery": recovery,
            "ability": ability,
            "environment": environment,
            "sources": sources,
        },
        "recent": recent,
        "recent_actions": recent_actions,
    }


def self_audit(state: Any) -> dict:
    """组装自我察觉面板的全部内容。纯读，不推进时间、不改状态。"""
    mind_tier = state.mind_tier
    lucidity_tier = state.lucidity_tier
    resilience = float(state._player_resilience())
    modifiers = state.physics_modifiers()

    # 崩解收益：与 enemies._spawn_enemy_drop 的 drop_bonus 同源。
    drop_divisor = {0: 0, 1: 4, 2: 3, 3: 2}.get(mind_tier, 0)
    dissolution_bonus = int(round(100 / drop_divisor)) if drop_divisor else 0
    loot_luck = float(state._loot_luck())

    # ---- 行动与时间（统一走 core/stats 只读解析，基础值/条件分开）----
    melee_trauma = resolve_stat(state, "melee.base_trauma")
    melee_time = resolve_stat(state, "melee.base_time")
    melee_effective = resolve_stat(state, "melee.effective_time")
    move_base = resolve_stat(state, "move.base_time")
    move_effective = resolve_stat(state, "move.effective_time")
    move_delay = resolve_stat(state, "move.delay_penalty")
    attack_delay = resolve_stat(state, "attack.delay_penalty")
    speed_stat = resolve_stat(state, "action.speed_scale")
    throw_stat = resolve_stat(state, "throw.range")
    resilience_stat = resolve_stat(state, "resilience")
    explosion = resolve_stat(state, "physics.explosion_bonus")
    fire = resolve_stat(state, "physics.fire_spread_bonus")
    penetration = resolve_stat(state, "physics.penetration_bonus")
    solidity = resolve_stat(state, "physics.solidity_penalty")
    dissolution_stat = resolve_stat(state, "dissolution.bonus")
    luck_stat = resolve_stat(state, "loot.luck")
    imagination_max = resolve_stat(state, "imagination.max")
    resilience = float(resilience_stat.value)
    speed = float(speed_stat.value) or 1.0

    stats: list[tuple[str, str]] = [
        (tr("近战·基础创伤"), str(int(round(melee_trauma.value)))),
        (tr("近战·基础耗时"), tr("{n:g} 回合/次", n=melee_time.value)),
        (tr("近战·有效耗时"), tr("{n:.2f} 回合/次", n=melee_effective.value)),
        (tr("移动·基础耗时"), tr("{n:g} 回合/格", n=move_base.value)),
        (tr("移动·有效耗时"), tr("{n:.2f} 回合/格", n=move_effective.value)),
        (tr("移动·迟滞代价"),
         tr("+{n:g}（积满 1 多花 1 回合）", n=move_delay.value) if move_delay.value > 1e-9 else tr("无")),
        (tr("攻击·迟滞代价"),
         tr("+{n:g}（积满 1 多花 1 回合）", n=attack_delay.value) if attack_delay.value > 1e-9 else tr("无")),
        (tr("行动速度倍率"), tr("×{n:g}", n=speed_stat.value)),
        (tr("投掷·距离"), tr("{n} 格", n=int(round(throw_stat.value)))),
        (tr("投掷·威力"), tr("按所用物品（爆炸/火焰/落地）")),
        (tr("清醒创伤减免"), tr("{n}%（战斗韧性，未含护甲与缓冲）", n=round((1 - resilience) * 100))),
        (tr("心智创伤减免"), tr("{n}%（战斗韧性，未含护甲与缓冲）", n=round((1 - resilience) * 100))),
        (tr("爆炸增强"), tr("+{n}", n=int(round(explosion.value)))),
        (tr("火焰蔓延"), tr("+{n}", n=int(round(fire.value)))),
        (tr("穿透加成"), tr("+{n}", n=int(round(penetration.value)))),
        (tr("坚固度惩罚"), tr("−{n}", n=int(round(solidity.value)))),
        (tr("崩解收益"),
         tr("+{n}%", n=int(round(dissolution_stat.value))) if dissolution_stat.value else tr("标准")),
        (tr("战利品幸度"),
         tr("{n:+.1f}", n=luck_stat.value) if abs(luck_stat.value) > 1e-9 else tr("标准")),
        (tr("想象上限"), str(int(round(imagination_max.value)))),
    ]

    portents: list[tuple[str, int, int]] = []
    stacks = dict(getattr(state, "portent_stacks", None) or {})
    for portent_id, rounds in sorted(
        (state.portents or {}).items(), key=lambda pair: str(pair[0])
    ):
        definition = None
        try:
            from ..materials import portent_def
            definition = portent_def(portent_id)
        except Exception:
            definition = None
        name = tr(definition.name) if definition is not None else tr(str(portent_id))
        portents.append((name, int(rounds), int(stacks.get(portent_id) or 0)))

    imagination_note, imagination_numbers = _imagination_progress(state)
    return {
        "bars": [
            (tr("心智"), int(state.mind), int(state.max_mind), tr(_tier_label(mind_tier))),
            (tr("清醒度"), int(state.lucidity), int(state.max_lucidity), tr(_tier_label(lucidity_tier))),
            # 想象力没有分档（机制上只有心智/清醒度两轴分档）：档位字段留空。
            (tr("想象力"), int(state.imagination), int(state.max_imagination), ""),
        ],
        "lucidity_note": tr(_LUCIDITY_NOTES[lucidity_tier]),
        "lucidity_numbers": tr(
            "穿透加成 +{penetration} · 坚固度惩罚 −{solidity} · 心智侵蚀 {drain}",
            penetration=modifiers["penetration_bonus"],
            solidity=modifiers["solidity_penalty"],
            drain=(tr("每 5 回合 −1") if lucidity_tier >= 3 else tr("无")),
        ),
        "mind_note": tr(_MIND_NOTES[mind_tier]),
        "mind_numbers": tr(
            "爆炸 +{explosion} · 火焰蔓延 +{fire} · 崩解收益 {dissolution} · 气体消散 +{gas} 回合",
            explosion=modifiers["explosion_bonus"],
            fire=modifiers["fire_spread_bonus"],
            dissolution=(tr("+{n}%", n=dissolution_bonus) if dissolution_bonus else tr("标准")),
            gas=mind_tier * 2,
        ),
        "imagination_note": imagination_note,
        "imagination_numbers": imagination_numbers,
        "stats": stats,
        "portents": portents,
        **_sections(state),
    }


def _tier_label(tier: int) -> str:
    from ..i18n import STATUS_TIERS
    return STATUS_TIERS[tier] if 0 <= tier < len(STATUS_TIERS) else STATUS_TIERS[0]
