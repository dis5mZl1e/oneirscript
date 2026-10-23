
"""只读属性解析（2026-10-18 docs/261018方案合集.md 第 10 节第二批）。

定义在 data/stat_definitions.py；本模块只负责把「一次明确上下文中的最终值、
基础值、实际参与的来源、未生效原因」查询出来，不抽随机、不消费触发器、不推进
回合。领域结算（行动时间、创伤、恢复、费用）仍由各自函数执行，后续批次再逐步
改为消费同一份来源解析，避免新旧两套修正同时生效。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..i18n import tr
from ..data.stat_definitions import STAT_DEFINITIONS, StatDefinition
from .stat_sources import SourceRef, SourceText, source_text, references


@dataclass(frozen=True)
class ResolvedStat:
    stat_id: str
    value: float
    base: float
    definition: StatDefinition
    sources: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    context: tuple[tuple[str, str], ...] = ()

    @property
    def source_refs(self):
        return references(self.sources)

    def formatted(self, *, with_unit: bool = True) -> str:
        precision = max(0, self.definition.precision)
        if precision:
            text = f"{self.value:.{precision}f}"
        else:
            text = f"{self.value:g}"
        if with_unit and self.definition.unit:
            text += " " + tr(self.definition.unit)
        return text


def format_stat(stat: ResolvedStat, *, with_unit: bool = True) -> str:
    return stat.formatted(with_unit=with_unit)


def _item(state: Any, instance_id: str):
    return next((item for item in state.inventory if item.instance_id == instance_id), None)


def _equipment_sources(state: Any, plan) -> tuple[str, ...]:
    grouped = {}
    for instance_id in getattr(plan, 'source_ids', ()) or ():
        item = _item(state, instance_id)
        if item is not None:
            grouped.setdefault(tr(item.name), []).append(SourceRef('equipment', instance_id))
    return tuple(SourceText(name, refs) for name, refs in grouped.items())


def _portent_names(state: Any, predicate: Callable[[Any], bool]) -> tuple[str, ...]:
    from ..materials import portent_def
    if getattr(state,'stasis_turns',0)>0:
        return ()
    names: list[str] = []
    for portent_id in state.portents:
        definition = portent_def(portent_id)
        if definition is not None and predicate(definition):
            name = tr(definition.name)
            if name not in names:
                names.append(source_text(name, 'portent', portent_id))
    return tuple(names)


def _melee_plan(state: Any):
    try:
        return state.equipment.plan_action("melee")
    except Exception:  # pragma: no cover - 直接构造的最小对象
        return None


def _speed_scale(state: Any) -> float:
    if getattr(state,'stasis_turns',0)>0:
        return 1.0
    try:
        return float(state._player_speed_scale()) or 1.0
    except Exception:  # pragma: no cover
        return 1.0


def _action_speed_sources(state):
    from .timed_actions import modem_source
    sources = _portent_names(state, lambda definition: definition.speed_multiplier > 0)
    source = modem_source(state)
    return sources + ((source,) if source else ())


def _resolve_melee_trauma(state, context):
    plan = _melee_plan(state)
    increment = float(getattr(plan, "damage_increment", 0.0) or 0.0)
    base = 1.0
    return base, base + increment, _equipment_sources(state, plan), ()


def _resolve_melee_time(state, context):
    plan = _melee_plan(state)
    value = float(getattr(plan, "base_time", 1.0) or 1.0)
    return 1.0, value, _equipment_sources(state, plan), ()


def _resolve_melee_effective_time(state, context):
    base_plan = _resolve_melee_time(state, context)
    speed = _speed_scale(state)
    sources = base_plan[2] + _action_speed_sources(state)
    return base_plan[1], base_plan[1] / speed, sources, ()


def _resolve_move_base_time(state, context):
    return 1.0, 1.0, (), (tr("蜂蜜/传送带/免费步等条件另结算"),)


def _resolve_move_effective_time(state, context):
    speed = _speed_scale(state)
    sources = _action_speed_sources(state)
    return 1.0, 1.0 / speed, sources, ()


def _resolve_move_delay(state, context):
    # 2026-10-22：weapon_weight 的悬空读取已从结算移除（全库无物品提供该效果），
    # 展示端也同步删掉，避免面板显示一个不会发生的迟滞来源。
    try:
        portent = float(state._portent_move_penalty())
        region = float(state._region_move_penalty())
    except Exception:  # pragma: no cover
        portent = region = 0.0
    sources = list(_portent_names(state, lambda definition: definition.move_time > 0))
    if region:
        sources.append(tr("贴近悔恨之锚"))
    notes = (tr("迟滞按欠账累计：积满 1 点才多花 1 回合"),) if portent + region else ()
    return 0.0, portent + region, tuple(dict.fromkeys(sources)), notes


def _resolve_attack_delay(state, context):
    try:
        penalty = float(state._portent_attack_penalty())
    except Exception:  # pragma: no cover
        penalty = 0.0
    return 0.0, penalty, _portent_names(
        state, lambda definition: definition.attack_time > 0), ()


def _resolve_speed_scale(state, context):
    speed = _speed_scale(state)
    sources = _action_speed_sources(state)
    notes = (tr("速度征兆按既定上下限汇总，限时物品额外修正"),) if sources else ()
    return 1.0, speed, sources, notes


def _resolve_throw_range(state, context):
    from . import throwing
    base = float(throwing.THROW_MAX_RANGE)
    value = float(throwing.throw_range(state))
    sources = tuple(tr(item.name) for item in state.equipment.items_with_effect("throw_master"))
    return base, value, sources, ()


def _resolve_resilience(state, context):
    from .run_options import SLIDER_DEFS, TOGGLE_DEFS
    value = float(state._player_resilience())
    sources: list[str] = []
    options = getattr(state, "run_options", None) or {}
    sliders = options.get("sliders") if isinstance(options, dict) else None
    if isinstance(sliders, dict):
        index = sliders.get("consciousness", 2)
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = 2
        if 0 <= index < len(SLIDER_DEFS["consciousness"]["tiers"]) and index != 2:
            sources.append(tr("开局调律·意识强度（{tier}）",
                              tier=tr(SLIDER_DEFS["consciousness"]["tiers"][index][0])))
    toggles = options.get("toggles") if isinstance(options, dict) else None
    for toggle in toggles or ():
        spec = TOGGLE_DEFS.get(toggle)
        if spec and "resilience" in (spec.get("mods") or {}):
            sources.append(tr(spec["name"]))
    return 1.0, value, tuple(sources), ()


def _resolve_sight_radius(state, context):
    base = float(state.sight_radius)
    value = float(state.effective_sight_radius())
    sources: list[str] = []
    if state.insight_active("夜视"):
        sources.append(source_text(tr("夜视 +1"), "insight", "夜视"))
    if state.insight_active("边界脚本") and state.depth >= 28:
        sources.append(source_text(tr("边界脚本 +1"), "insight", "边界脚本"))
    equipped_ids = {item.definition_id for item in state.equipped_items()}
    if "lighthouse_lens" in equipped_ids and state.turns_since_descend <= 3:
        sources.append(tr("灯塔透镜 +3"))
    if state._effect_power("vision_up"):
        sources.append(tr("夜灯电池 +{n}", n=state._effect_power("vision_up")))
    memory_bonus = state.memory_stat_bonus("sight")
    if memory_bonus:
        sources.append(SourceText(tr("记忆碎片 +{n}", n=memory_bonus), _memory_stat_refs(state, "sight")))
    region_penalty = state._region_sight_penalty()
    if region_penalty:
        sources.append(tr("无光绒墙 {n}", n=region_penalty))
    floor_bonus = state._floor_sight_bonus()
    if floor_bonus:
        sources.append(tr("脚下反光地面 +{n}", n=floor_bonus))
    if state.ability_turns.get("farsight", 0) > 0:
        sources.append(tr("望远 +4"))
    # 视觉通道按 §14.1 分类展示：正面平加、同族平减、失焦自身项、比例、致盲。
    sight = state._vision_profile()
    if sight.positive:
        sources.append(tr("征兆视野 +{n}", n=sight.positive))
    if sight.flat:
        sources.append(tr("征兆视野 {n}", n=sight.flat))
    if sight.blur:
        sources.append(tr("失焦 {n}（本项下限 {floor}）",
                         n=sight.blur, floor=sight.blur_floor))
    if sight.ratio < 1.0:
        sources.append(tr("征兆缩视 ×{ratio}", ratio=round(sight.ratio, 2)))
    if sight.blinds:
        sources.append(tr("致盲：普通视觉归零"))
    return base, value, tuple(sources), ()


def _resistance_sources(state: Any, portent_id: str) -> tuple[str, ...]:
    """耐受碎片来源（只列真正对该征兆生效的已装入碎片）。"""
    try:
        from .content import ITEM_DEFINITIONS, MEMORY_FRAGMENT_EFFECTS
    except Exception:  # pragma: no cover
        return ()
    sources: list[str] = []
    for fragment_id in getattr(state, "memory_fragments", ()) or ():
        definition = ITEM_DEFINITIONS.get(fragment_id, {})
        effect = MEMORY_FRAGMENT_EFFECTS.get(definition.get("memory_effect", ""))
        if (effect and effect.get("kind") == "resistance"
                and portent_id in effect.get("portents", ())):
            sources.append(source_text(tr(definition.get("name", fragment_id)), "memory", fragment_id))
    return tuple(sources)


def _resolve_portent_accumulation(state, context):
    portent_id = str((context or {}).get("portent", ""))
    factor = float(state.memory_portent_factor(portent_id)) if portent_id else 1.0
    sources = _resistance_sources(state, portent_id)
    notes = (tr("同类耐受取最高，不叠加成完全免疫"),) if sources else ()
    return 1.0, factor, sources, notes


def _resolve_portent_duration(state, context):
    ctx = context or {}
    portent_id = str(ctx.get("portent", ""))
    base = max(0, int(ctx.get("base", 1) or 0))
    player = bool(ctx.get("player", True))
    duration = state.memory_portent_duration(portent_id, base) if player else base
    sources = _resistance_sources(state, portent_id)
    notes: list[str] = []
    if base and duration < base:
        notes.append(tr("耐受使新沾染时长缩短 50%、向上取整且至少 1 回合"))
    try:
        if player and state.player.portents.get("hospital_immune_once", 0) > 0:
            notes.append(tr("若恰好触发一次免疫，会再缩短并消耗该资格"))
    except Exception:  # pragma: no cover
        pass
    return float(base), float(duration), sources, tuple(notes)


def _resolve_environment_trauma(state, context):
    ctx = context or {}
    channel = str(ctx.get("channel", "fire"))
    amount = int(ctx.get("amount", 0) or 0)
    direct = bool(ctx.get("direct", True))
    preview, sources = state._identity_trauma_preview(amount, channel, direct=direct)
    notes: list[str] = []
    if amount <= 0:
        notes.append(tr("没有基础创伤"))
    return float(amount), float(preview), sources, tuple(notes)


def _resolve_identity_trauma_multiplier(state, context):
    channel = str((context or {}).get("channel", "fire"))
    factor = state._identity_vulnerability_factor(channel)
    sources = (tr("身份 {identity}", identity=state._identity()),) if factor else ()
    notes = (tr("只对本身份的对应环境通道生效"),) if factor else ()
    return 1.0, 1.0 + factor, sources, notes


def _resolve_mind_loss_multiplier(state, context):
    value = float(state.mind_loss_multiplier)
    from ..materials import portent_def
    sources = tuple(
        tr(portent_def(pid).name)
        for pid in state.portents
        if portent_def(pid) is not None and portent_def(pid).mind_loss_factor < 1.0
    )
    notes = (tr("多个减半类征兆取最小倍率，对一切来源生效"),) if sources else ()
    return 1.0, value, sources, notes


def _resolve_mind_loss_blocked(state, context):
    blocked = bool(state.mind_loss_blocked)
    from ..materials import portent_def
    sources = tuple(
        tr(portent_def(pid).name) for pid in state.portents
        if portent_def(pid) is not None and portent_def(pid).blocks_mind_loss
    )
    notes = (tr("镇静只拦环境来源，不拦异象战斗创伤"),) if blocked else ()
    return 0.0, 1.0 if blocked else 0.0, sources, notes


def _resolve_tier(key: str):
    def resolve(state, context):
        value = float(getattr(state, key))
        return 0.0, value, (), ()
    return resolve


def _resolve_ability_cost_multiplier(state, context):
    from .run_options import TOGGLE_DEFS
    value = float(state._ability_cost_mult())
    sources: list[str] = []
    options = getattr(state, "run_options", None) or {}
    sliders = options.get("sliders") if isinstance(options, dict) else None
    if isinstance(sliders, dict):
        try:
            inspiration = int(sliders.get("inspiration", 2))
        except (TypeError, ValueError):
            inspiration = 2
        if inspiration != 2:
            sources.append(tr("开局调律·想象灵感"))
    toggles = options.get("toggles") if isinstance(options, dict) else None
    for toggle in toggles or ():
        spec = TOGGLE_DEFS.get(toggle) if isinstance(toggle, str) else None
        if spec and "ability_cost" in (spec.get("mods") or {}):
            sources.append(tr(spec["name"]))
    aptitude = float(getattr(state, "_dream_aptitude_mult", lambda _axis: 1.0)("conceive"))
    if abs(aptitude - 1.0) > 1e-9:
        sources.append(tr("出生梦性·构想"))
    return 1.0, value, tuple(sources), ()


def _resolve_ability_cooldown(state, context):
    ctx = context or {}
    base = max(0, int(ctx.get("base", 1) or 0))
    value = state._scaled_ability_cooldown(base)
    sources: list[str] = []
    options = getattr(state, "run_options", None) or {}
    sliders = options.get("sliders") if isinstance(options, dict) else None
    if isinstance(sliders, dict):
        try:
            tempo = int(sliders.get("tempo", 2))
        except (TypeError, ValueError):
            tempo = 2
        if tempo != 2:
            sources.append(tr("开局调律·构想节律"))
    if state.insight_active("思维润滑"):
        sources.append(source_text(tr("思维润滑 −1"), "insight", "思维润滑"))
    notes = (tr("保留最低 1 回合；冷却进度不因查看面板刷新"),) if sources else ()
    return float(base), float(value), tuple(sources), notes


def _resolve_tamper_pressure(state, context):
    value = float(getattr(state, "tamper_pressure", 0) or 0)
    return 0.0, value, (), ()


def _resolve_tamper_chaos_cost(state, context):
    from .tamper_pipeline import TamperCost, next_pressure, quote_cost
    ctx = context or {}
    base_chaos = max(0, int(ctx.get("chaos", 0) or 0))
    imagination = max(0, int(ctx.get("imagination", 0) or 0))
    quote = quote_cost(state, TamperCost(imagination=imagination, chaos_delta=base_chaos))
    pressure = next_pressure(state)
    sources = (tr("连续压力 {n}/3", n=pressure),) if pressure else ()
    notes = (tr("最终值 = ceil(基础混乱 × 1.3) + 压力 × 2；预览不判定风险"),)
    return float(base_chaos), float(quote.chaos_delta), sources, notes


def _resolve_buffer_available(state, context):
    ctx = context or {}
    kind = str(ctx.get("kind", "any"))
    data = getattr(state, "board_buffer", None) or {}
    effective = bool(data.get("points")) and int(data.get("until", 0)) >= state.time
    matches = kind in ("any",) or data.get("kind") in ("any", kind)
    value = 1.0 if effective and matches else 0.0
    sources = (tr("缓冲类型：{kind}", kind=str(data.get("kind", "any"))),) if value else ()
    notes = (tr("只抵下一次对应创伤，不恢复资源"),) if value else ()
    return 0.0, value, sources, notes


def _memory_stat_refs(state, stat):
    from .content import ITEM_DEFINITIONS, MEMORY_FRAGMENT_EFFECTS
    refs = []
    for mid in state.memory_fragments:
        effect = MEMORY_FRAGMENT_EFFECTS.get(ITEM_DEFINITIONS.get(mid, {}).get('memory_effect'), {})
        if any((entry.get('kind') == 'stat' and entry.get('stat') == stat
                or entry.get('kind') == 'adapt' and entry.get('adapt') == stat)
               for entry in state._memory_entries(effect)):
            refs.append(SourceRef('memory', mid))
    return tuple(refs)


def _resolve_mind_max(state, context):
    value = float(state.max_mind)
    sources = (tr("出生/记忆/开局调律"),) if abs(value - 100.0) > 1e-9 else ()
    return 100.0, value, tuple(SourceText(text, _memory_stat_refs(state, "max_mind")) for text in sources), ()


def _resolve_lucidity_max(state, context):
    # Do not reuse the mind cap resolver: the two maxima can diverge (memory,
    # identity, debug and equipment effects), and the old shared resolver
    # reported max_mind as max_lucidity.
    value = float(state.max_lucidity)
    sources = (tr("出生/记忆/开局调律"),) if abs(value - 100.0) > 1e-9 else ()
    return 100.0, value, tuple(SourceText(text, _memory_stat_refs(state, "max_lucidity")) for text in sources), ()


def _resolve_imagination_max(state, context):
    value = float(state.max_imagination)
    sources = (tr("出生/记忆/开局调律"),) if abs(value - 50.0) > 1e-9 else ()
    return 50.0, value, tuple(SourceText(text, _memory_stat_refs(state, "max_imagination")) for text in sources), ()


def _resolve_imagination_credit(state, context):
    value = float(getattr(state, "imagination_regen_credit", 0.0) or 0.0)
    return 0.0, value, (), ()


def _resolve_imagination_regen(state, context):
    from .self_audit import _imagination_progress
    try:
        rate = max(0.0, 1.0 + float(state._imagination_regen_bonus()))
        rate *= float(state.hospital_regeneration_rate())
    except Exception:  # pragma: no cover
        rate = 1.0
    suppressed = bool(state._imagination_regen_suppressed())
    bonus = int(state._blank_edge_bonus())
    notes: list[str] = []
    if suppressed:
        notes.append(tr("摇篮曲使自然回流暂停"))
    if bonus:
        notes.append(tr("留白线见底时额外 +{n}", n=bonus))
    sources = [tr("基础规则 +1")]
    if state._imagination_regen_bonus():
        sources.append(tr("开局调律·想象灵感"))
    return 1.0, 0.0 if suppressed else rate, tuple(sources), tuple(notes)


def _resolve_dissolution_bonus(state, context):
    tier = state.mind_tier
    divisor = {0: 0, 1: 4, 2: 3, 3: 2}.get(tier, 0)
    value = float(round(100 / divisor)) if divisor else 0.0
    sources = (tr("心智档位 {n}", n=tier),) if value else ()
    return 0.0, value, sources, ()


def _resolve_loot_luck(state, context):
    value = float(state._loot_luck())
    sources = (tr("开局调律·思维流畅"),) if abs(value) > 1e-9 else ()
    return 0.0, value, sources, ()


def _physics_resolver(key: str, source_name: str):
    def resolve(state, context):
        value = float(state.physics_modifiers()[key])
        sources = (tr(source_name),) if value else ()
        return 0.0, value, sources, ()
    return resolve


_RESOLVERS: dict[str, Callable[[Any, dict | None], tuple[float, float, tuple[str, ...], tuple[str, ...]]]] = {
    "melee.base_trauma": _resolve_melee_trauma,
    "melee.base_time": _resolve_melee_time,
    "melee.effective_time": _resolve_melee_effective_time,
    "move.base_time": _resolve_move_base_time,
    "move.effective_time": _resolve_move_effective_time,
    "move.delay_penalty": _resolve_move_delay,
    "attack.delay_penalty": _resolve_attack_delay,
    "action.speed_scale": _resolve_speed_scale,
    "throw.range": _resolve_throw_range,
    "resilience": _resolve_resilience,
    "sight.radius": _resolve_sight_radius,
    "portent.accumulation_factor": _resolve_portent_accumulation,
    "portent.effective_duration": _resolve_portent_duration,
    "environment.trauma": _resolve_environment_trauma,
    "identity.trauma_multiplier": _resolve_identity_trauma_multiplier,
    "mind.loss_multiplier": _resolve_mind_loss_multiplier,
    "mind.loss_blocked": _resolve_mind_loss_blocked,
    "ability.cost_multiplier": _resolve_ability_cost_multiplier,
    "ability.cooldown_turns": _resolve_ability_cooldown,
    "tamper.pressure": _resolve_tamper_pressure,
    "tamper.chaos_cost": _resolve_tamper_chaos_cost,
    "buffer.available": _resolve_buffer_available,
    "lucidity.tier": _resolve_tier("lucidity_tier"),
    "mind.tier": _resolve_tier("mind_tier"),
    "mind.max": _resolve_mind_max,
    "lucidity.max": _resolve_lucidity_max,
    "imagination.max": _resolve_imagination_max,
    "imagination.regen_credit": _resolve_imagination_credit,
    "imagination.regen_rate": _resolve_imagination_regen,
    "dissolution.bonus": _resolve_dissolution_bonus,
    "loot.luck": _resolve_loot_luck,
    "physics.explosion_bonus": _physics_resolver("explosion_bonus", "心智档位"),
    "physics.fire_spread_bonus": _physics_resolver("fire_spread_bonus", "心智档位"),
    "physics.penetration_bonus": _physics_resolver("penetration_bonus", "清醒档位"),
    "physics.solidity_penalty": _physics_resolver("solidity_penalty", "清醒档位"),
}


def resolve_stat(state: Any, stat_id: str, context: dict | None = None) -> ResolvedStat:
    """在明确上下文中解析一个属性的最终值（纯只读）。

    未登记或尚未接入真实结算的属性抛 KeyError，避免界面先填一个看似合理
    的数值；context 只作为说明/缓存键的一部分返回，不改变解析器选择。
    """
    definition = STAT_DEFINITIONS.get(stat_id)
    if definition is None:
        raise KeyError(f"未登记的属性：{stat_id}")
    resolver = _RESOLVERS.get(stat_id)
    if resolver is None:
        raise KeyError(f"属性尚未接入真实结算：{stat_id}")
    base, value, sources, notes = resolver(state, context)
    if definition.minimum is not None:
        value = max(definition.minimum, value)
    if definition.maximum is not None:
        value = min(definition.maximum, value)
    return ResolvedStat(
        stat_id=stat_id,
        value=float(value),
        base=float(base),
        definition=definition,
        sources=sources,
        notes=notes,
        context=tuple(sorted((str(key), str(val)) for key, val in (context or {}).items())),
    )


def definition_for(stat_id: str) -> StatDefinition:
    definition = STAT_DEFINITIONS.get(stat_id)
    if definition is None:
        raise KeyError(f"未登记的属性：{stat_id}")
    return definition
