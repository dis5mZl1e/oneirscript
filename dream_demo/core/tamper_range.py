
"""全视野范围与批量报价（2026-10-18 docs 第 8 节第四批）。

范围先于结算：
- 只对「视野内」当前可见、通过既有保护/资格判定的对象建立候选集；
- 全视野是显式范围，不从单格点击自动扩大；选目标这一步不随程度与战术条件改变，
  条件只决定逐格资格与代价；
- 保护对象先排除并给出原因，不把剩余集合仍称「全部」；
- 同一格只计一次，按实例/坐标去重；
- 批量目标与单格提交走同一份条件世界校验：条件要求不满足的目标逐格排除并给出
  原因；整批没有合法目标时返回可读拒绝、零消耗（2026-10-22 平衡修复）；
- 费用在提交前一次算清：想象费用按 ceil(基础 × (1 + 0.75·log2 N)) 增长，
  混乱基础量保留，另加 2·ceil(log2 N) 的范围混乱（N=1 与原单格一致）；
- 执行前复核 plan（层、字词、条件、候选集合与逐格状态）；失效整单拒绝、
  零资源/时间消耗；成功后只累计一次连续压力、一次使用行动与一次风险判定。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..i18n import tr
from .constants import ActionKind
from .tamper_pipeline import TamperCost, advance_time, apply_risk, next_sequence, settle
from .tamper_world import (
    WorldSlot,
    _apply_word,
    _grow_requirement_reason,
    _normalize_conditions,
    _wither_requirement_reason,
    condition_combo_blocked_reason,
    resolved_word_id,
    word_blocked_reason,
    word_cost_with_conditions,
)

RANGE_VERBS = frozenset({"break", "ignite", "grow", "wither"})
RANGE_API_VERSION = 1


@dataclass
class BatchTarget:
    slot: WorldSlot
    digest: tuple


@dataclass
class RangePlan:
    word_id: str
    range_mode: str
    targets: list[BatchTarget]
    excluded: list[tuple[int, int, str]]
    imagination: int
    chaos_delta: int
    signature: tuple
    label: str
    condition_ids: tuple[str, ...] = ()
    version: int = RANGE_API_VERSION

    @property
    def count(self) -> int:
        return len(self.targets)

    def valid(self, state: Any) -> bool:
        rebuilt = build_plan(state, self.word_id, range_mode=self.range_mode,
                             condition_ids=self.condition_ids)
        if isinstance(rebuilt, str):
            return False
        return rebuilt.signature == self.signature


def _target_digest(state: Any, slot: WorldSlot, verb: str) -> tuple:
    from .tamper_world import _signature
    return (slot.category, slot.x, slot.y, _signature(state, slot))


def _slot_for_cell(state: Any, x: int, y: int, verb: str) -> WorldSlot | None:
    from ..materials import gas_def, liquid_def, plant_def_for, wall_def
    cell = state.cell(x, y)
    if verb == "break":
        if not (cell.solid and cell.wall_kind):
            return None
        return WorldSlot("terrain", tr(wall_def(cell.wall_kind).name), x=x, y=y)
    if verb == "ignite":
        if cell.solid and cell.wall_kind:
            return WorldSlot("terrain", tr(wall_def(cell.wall_kind).name), x=x, y=y)
        if cell.liquid > 0 and cell.liquid_kind:
            return WorldSlot("liquid", tr(liquid_def(cell.liquid_kind).name), x=x, y=y)
        if cell.gas > 0 and cell.gas_kind:
            return WorldSlot("gas", tr(gas_def(cell.gas_kind).name), x=x, y=y)
        if cell.plant:
            return WorldSlot("terrain", tr(plant_def_for(cell.plant).name), x=x, y=y)
        for entry in state.world_items:
            if (entry.x, entry.y) == (x, y):
                return WorldSlot("object", tr(entry.item.name), x=x, y=y)
        return None
    if cell.plant <= 0:
        return None
    return WorldSlot("terrain", tr(plant_def_for(cell.plant).name), x=x, y=y)


def _eligibility_reason(state: Any, word_id: str, slot: WorldSlot, verb: str) -> str:
    if verb == "grow":
        return _grow_requirement_reason(state, slot)
    if verb == "wither":
        return _wither_requirement_reason(state, slot)
    reason = word_blocked_reason(state, word_id, slot, None)
    if reason:
        return reason
    if verb == "ignite":
        from ..content import item_is_flammable
        cell = state.cell(slot.x, slot.y)
        flammable = state._cell_is_flammable(cell) or any(
            (entry.x, entry.y) == (slot.x, slot.y) and item_is_flammable(entry.item)
            for entry in state.world_items)
        return "" if flammable else tr("这里没有可以点燃的东西。")
    return ""


def _range_label(word_id: str, verb: str) -> str:
    if verb == "break":
        return tr("视野内可破坏的墙体")
    if verb == "ignite":
        return tr("视野内可点燃的东西")
    if verb == "grow":
        return tr("视野内可催生的植物")
    if verb == "wither":
        return tr("视野内可枯萎的植物")
    return tr("视野内的目标")


def _candidate_targets(state: Any, word_id: str, verb: str,
                       combo: tuple[str, ...]) -> tuple[list[BatchTarget], list[tuple[int, int, str]]]:
    targets: list[BatchTarget] = []
    excluded: list[tuple[int, int, str]] = []
    visible = state.visible_cells()
    for y in range(state.height):
        for x in range(state.width):
            if (x, y) not in visible:
                continue
            slot = _slot_for_cell(state, x, y, verb)
            if slot is None:
                continue
            reason = _eligibility_reason(state, word_id, slot, verb)
            if reason:
                excluded.append((x, y, reason))
                continue
            # 2026-10-22 平衡修复：批量不再跳过条件世界校验。与单格提交同源调用
            # condition_combo_blocked_reason（「趁虚」要求墙已有裂痕、「趁它未察觉」
            # 要求目标未察觉等），不满足的目标逐格排除，不静默把结果算成「全部」。
            condition_reason = condition_combo_blocked_reason(
                state, combo, slot, None, word_id=word_id)
            if condition_reason:
                excluded.append((x, y, condition_reason))
                continue
            targets.append(BatchTarget(slot, _target_digest(state, slot, verb)))
    return targets, excluded


def build_plan(state: Any, word_id: str, *, range_mode: str = "vision",
               condition_ids: Iterable[str] = ()) -> RangePlan | str:
    """建立确定的全视野计划；错误时返回可读原因（不是异常）。"""
    if range_mode != "vision":
        return tr("这个范围还没有开放。")
    combo = _normalize_conditions(None, tuple(condition_ids))
    resolved = resolved_word_id(word_id, combo)
    definition = None
    from .tamper_world import WORD_DEFS
    definition = WORD_DEFS.get(resolved) or WORD_DEFS.get(word_id)
    if definition is None:
        return tr("这个字词还没有学会。")
    verb = str(definition.get("verb", resolved))
    if verb not in RANGE_VERBS:
        return tr("这个字词不支持全视野范围。")
    if getattr(state, "run_over", False):
        return tr("这一局已经结束。")
    targets, excluded = _candidate_targets(state, word_id, verb, combo)
    if not targets:
        if combo and excluded:
            # 条件把整批目标都排除了：明确说「是条件不成立」而不是含糊的「没对象」。
            return tr("视野内的目标都不满足这个条件（{n} 处被排除：{reason}）。",
                      n=len(excluded), reason=excluded[0][2])
        return tr("视野内没有可以{action}的对象。",
                  action=tr(definition.get("name", resolved)))
    costs = [word_cost_with_conditions(state, word_id, target.slot, combo)
             for target in targets]
    base_imagination = max(int(cost[0]) for cost in costs)
    base_chaos = max(int(cost[1]) for cost in costs)
    count = len(targets)
    # 2026-10-22 平衡修复：旧曲线（0.5·log2N、+ceil(log2N)）让 N=8 时每目标成本
    # 只剩 25%、N=32 只剩 8%，批量成为纯折扣；收紧为 0.75·log2N 与 +2·ceil(log2N)。
    multiplier = 1.0 + 0.75 * math.log2(count)
    imagination = max(0, int(math.ceil(base_imagination * multiplier)))
    range_chaos = 2 * int(math.ceil(math.log2(count))) if count > 1 else 0
    chaos_delta = max(0, base_chaos + range_chaos)
    signature = (
        RANGE_API_VERSION,
        state.layer_key() if hasattr(state, "layer_key") else "",
        word_id,
        tuple(combo),
        range_mode,
        tuple((target.slot.category, target.slot.x, target.slot.y, target.digest)
              for target in targets),
        tuple(excluded),
    )
    return RangePlan(word_id=word_id, range_mode=range_mode, targets=targets,
                     excluded=excluded, imagination=imagination,
                     chaos_delta=chaos_delta, signature=signature,
                     label=_range_label(word_id, verb), condition_ids=tuple(combo))


def supports_range(word_id: str, condition_ids: Iterable[str] = ()) -> bool:
    """当前字词是否开放全视野范围（程度词按解析后的动词判断）。"""
    from .tamper_world import WORD_DEFS
    combo = _normalize_conditions(None, tuple(condition_ids))
    resolved = resolved_word_id(word_id, combo)
    definition = WORD_DEFS.get(resolved) or WORD_DEFS.get(word_id)
    if definition is None:
        return False
    return str(definition.get("verb", resolved)) in RANGE_VERBS


def range_preview(state: Any, word_id: str, *, range_mode: str = "vision",
                  condition_ids: Iterable[str] = ()) -> dict | str:
    plan = build_plan(state, word_id, range_mode=range_mode, condition_ids=condition_ids)
    if isinstance(plan, str):
        return plan
    return {
        "label": plan.label,
        "count": plan.count,
        "excluded": len(plan.excluded),
        "excluded_reasons": plan.excluded,
        "imagination": plan.imagination,
        "chaos": plan.chaos_delta,
        "targets": [(target.slot.x, target.slot.y) for target in plan.targets],
    }


def commit_range_tamper(state: Any, sentence: Any, word_id: str, *,
                        range_mode: str = "vision",
                        condition_id: str | None = None,
                        condition_ids: Iterable[str] | None = None,
                        plan: RangePlan | None = None,
                        source_uid: str = "world:range"):
    """全视野提交：先建计划、复核，再一次性扣费/推进/判定风险/逐目标生效。"""
    from .entities import ActionResult as _AR
    from ..data.tamper_schema import TamperRequest, TamperTarget

    if getattr(sentence, "consumed", False):
        return _AR(False, getattr(sentence, "result_message", ""), {"replayed": True})
    combo = _normalize_conditions(condition_id, condition_ids)
    if plan is None:
        plan = build_plan(state, word_id, range_mode=range_mode, condition_ids=combo)
        if isinstance(plan, str):
            return _AR(False, plan)
    if not plan.valid(state):
        return _AR(False, tr("眼前的情形已经改变，请重新选择。"))
    if int(state.imagination) < plan.imagination:
        return _AR(False, tr("想象力不够（需要 {n}）。", n=plan.imagination))

    notes: list[str] = []
    for target in plan.targets:
        note, error = _apply_word(state, word_id, target.slot, sentence=sentence,
                                  condition_ids=combo)
        if error:
            return _AR(False, error)
        if note:
            notes.append(note)
    sequence = next_sequence(state)
    request = TamperRequest(
        TamperTarget("event", "world_tamper_range", f"world:range:{word_id}"),
        "world_tamper", word_id, 0, f"world|range|{word_id}|{sequence}")
    chaos_after, outcome = settle(
        state, request, TamperCost(plan.imagination, plan.chaos_delta),
        sequence=sequence, reason=f"world_tamper_range:{word_id}", source_uid=source_uid)
    if sentence is not None:
        sentence.consumed = True
    from .tamper_prose import strip_terminal
    parts = []
    if notes:
        cleaned = [strip_terminal(note) for note in notes]
        shown = "；".join(cleaned[:3])
        parts.append(tr("{shown}等 {n} 处。", shown=shown, n=len(cleaned)) if len(cleaned) > 3
                     else "；".join(cleaned) + "。")
    parts.append(tr("（全视野 {n} 处；想象力 −{cost}，混乱度 {chaos}／{tier}）",
                    n=plan.count, cost=plan.imagination, chaos=chaos_after,
                    tier=tr(_chaos_tier(chaos_after))))
    advance_time(state)
    feedback = apply_risk(state, outcome, source_uid=source_uid)
    if feedback:
        parts.append(feedback)
    message = "".join(parts)
    if sentence is not None:
        sentence.result_message = message
    state.messages.append(message)
    return _AR(True, message, {"world_tamper": word_id, "range": "vision",
                               "targets": plan.count, "chaos": chaos_after})


def _chaos_tier(value: int) -> str:
    from .chaos import chaos_risk_tier
    return chaos_risk_tier(value)
