"""Bounded sentence feedback, using settled world facts and real materials."""
from __future__ import annotations

from .events import (DEFAULT_COOLDOWN, FEEDBACK_PER_EVENT, FEEDBACK_PER_ROUND,
                     FeedbackResult, emit_equipment_visual,
                     forget_equipment_store)
from .runtime import condition_matches
from ..i18n import tr

FAMILIES = {"ignite": "ember", "shock": "spark", "conduct": "spark",
            "imprint": "imprint", "strike": "cut", "cover": "buffer"}


def _root_endpoint(state) -> str:
    """当前真实根事件的端点；没有根帧时归入盘面动作。"""
    frame = getattr(state, "_equipment_root_frame", None)
    facts = getattr(frame, "facts", None) if frame is not None else None
    if facts:
        return str(facts[-1].endpoint)
    return "board"


def _register_feedback_visual(state, opcode, *, cell, target, recipient, damage_kind):
    """只在 execute_feedback 已真实成功后调用；不改数值、不回调伤害。"""
    endpoint = _root_endpoint(state)
    common = (("piece", opcode), ("opcode", opcode), ("root_event", endpoint))
    if opcode == "cover":
        emit_equipment_visual(
            state, endpoint=endpoint, opcode=opcode, outcome="store",
            source=(state.player.x, state.player.y),
            store_key=("buffer", str(damage_kind or "any")),
            facts=common + (("kind", str(damage_kind or "any")),))
        return
    if opcode == "ignite":
        point = cell
        emit_equipment_visual(
            state, endpoint=endpoint, opcode=opcode, outcome="hit",
            source=point, targets=(point,), affected_cells=(point,),
            facts=common)
        return
    if recipient is None:
        return
    point = (recipient.x, recipient.y)
    emit_equipment_visual(
        state, endpoint=endpoint, opcode=opcode, outcome="hit",
        source=cell, targets=(point,), affected_cells=(point,),
        facts=common + (("damage", 1),))


def layer_identity(state):
    return [state.depth, state.realm_id, state.realm_depth]


def _budget(state):
    budget = state.equipment_event_budget
    frame = getattr(state, '_equipment_root_frame', None)
    action_id = frame.action_id if frame is not None else state.action_seq
    if budget.get("action_id") != action_id:
        budget = {"action_id": action_id, "used": 0, "families": []}
    return budget


def ready(state, opcode, *, active=False):
    family = FAMILIES.get(opcode, opcode)
    budget = _budget(state)
    return (state.imagination >= 1
            and state.time >= state.board_cooldowns.get(family, 0)
            and family not in budget.get("families", [])
            and budget.get("used", 0) < FEEDBACK_PER_EVENT
            and (active or state.board_feedback_round < FEEDBACK_PER_ROUND))


def _record(state, opcode, *, active=False):
    family = FAMILIES.get(opcode, opcode)
    budget = _budget(state)
    budget["used"] = budget.get("used", 0) + 1
    budget["families"] = [*budget.get("families", []), family]
    state.equipment_event_budget = budget
    state.board_cooldowns[family] = state.time + DEFAULT_COOLDOWN
    from ..core.settlement import REASON_ABILITY_COST, settle_delta
    settle_delta(state, 'imagination', -1, reason=REASON_ABILITY_COST,
                 source='构想代价')
    if not active:
        state.board_feedback_round += 1


def _target_ok(state, target):
    return bool(target is not None and target is not state.player
                and target.integrity > 0 and target.relation in ("失控意识", "玩偶意识体")
                and target in state.enemies and state.is_visible(target.x, target.y)
                and state._has_line_of_sight(state.player.x, state.player.y, target.x, target.y))


def execute_feedback(state, opcode, *, cell=None, target=None, damage_kind="", action_plan=None):
    if not ready(state, opcode):
        return FeedbackResult(opcode, False, "这项反馈暂不可用：想象力不足、效果仍在冷却，或本回合的触发次数已用完。")
    if cell is None or not state.inside_board(*cell) or not state.is_visible(*cell):
        return FeedbackResult(opcode, False, "落点不可见或不在场内")
    if not state._has_line_of_sight(state.player.x, state.player.y, *cell):
        return FeedbackResult(opcode, False, "落点被墙体阻隔")
    state._equipment_derived_depth = getattr(state, "_equipment_derived_depth", 0) + 1
    recipient = None
    try:
        if opcode == "ignite":
            if not state._ignite_cell(*cell, 1, by_player=False):
                return FeedbackResult(opcode, False, "这个位置没有可点燃的材料。")
            state._emit_combat_fx("fire", cell, [cell])
        elif opcode in ("shock", "strike", "conduct", "blast"):
            if not _target_ok(state, target):
                return FeedbackResult(opcode, False, "当前没有符合条件的可见目标。")
            recipient = target
            if opcode == 'conduct':
                from .events import CONDUCTIVE_LIQUIDS
                source = state.cell(*cell)
                if source.liquid <= 0 or source.liquid_kind not in CONDUCTIVE_LIQUIDS:
                    return FeedbackResult(opcode, False, '脚下没有可传导的液体。')
                recipient = next((enemy for enemy in state.enemies
                    if enemy is not target and _target_ok(state, enemy)
                    and abs(enemy.x-cell[0])+abs(enemy.y-cell[1]) <= 2
                    and state.cell(enemy.x,enemy.y).liquid > 0
                    and state.cell(enemy.x,enemy.y).liquid_kind in CONDUCTIVE_LIQUIDS
                    and state._has_line_of_sight(*cell,enemy.x,enemy.y)), None)
                if recipient is None:
                    return FeedbackResult(opcode, False, '附近没有液体接住这次传导。')
            elif opcode == 'blast':
                powers = {iid: power for row in (action_plan.rows if action_plan else ())
                          for iid, effect, power in row.action_modifiers if effect == 'blast_radius'}
                radius = min(3, 1+max(powers.values(), default=0))
                recipient = next((enemy for enemy in state.enemies
                    if enemy is not target and _target_ok(state, enemy)
                    and max(abs(enemy.x-cell[0]),abs(enemy.y-cell[1])) <= radius
                    and state._has_line_of_sight(*cell,enemy.x,enemy.y)), None)
                if recipient is None:
                    return FeedbackResult(opcode, False, '余爆附近没有可波及的目标。')
            recipient.integrity = max(0, recipient.integrity - 1)
            state._emit_combat_fx("electric" if opcode in ('shock','conduct') else 'blast' if opcode == 'blast' else "cut",
                                 cell, [cell, (recipient.x,recipient.y)] if opcode in ('conduct','blast') else [cell])
            if recipient.integrity <= 0:
                # Derived damage gets one ordinary dissolution, no root-hit,
                # siphon, reflow or recursively generated equipment rewards.
                previous = getattr(state, "_kill_full_reward", False)
                state._kill_full_reward = False
                try:
                    state._resolve_enemy(recipient)
                finally:
                    state._kill_full_reward = previous
        elif opcode == "cover":
            if state.board_buffer.get("points", 0) > 0:
                return FeedbackResult(opcode, False, "护持已满")
            state.board_buffer = {"points": 1, "kind": damage_kind or "any", "until": state.time + 3}
        else:
            return FeedbackResult(opcode, False, "没有对应的世界原语")
    finally:
        state._equipment_derived_depth -= 1
    _record(state, opcode)
    message = tr("语句反馈·{effect}：在 {x},{y} 兑现一次联想。",
                 effect=tr({"ignite": "余温", "shock": "静电", "conduct": "传导", "blast": "余爆", "strike": "刀痕", "cover": "护持"}.get(opcode, opcode)),
                 x=cell[0], y=cell[1])
    state.messages.append(message)
    # 旁路登记：世界已经改变且 _record 已落账后才抄事实，不改玩法。
    _register_feedback_visual(state, opcode, cell=cell, target=target,
                              recipient=recipient, damage_kind=damage_kind)
    return FeedbackResult(opcode, True, detail={"cell": cell})


def emit(state, endpoint, *, action_plan=None, derived=False, **kwargs):
    if derived or getattr(state, "_equipment_derived_depth", 0):
        return []
    from .root_facts import record_event
    record_event(state, endpoint, **kwargs)
    cell, target = kwargs.get("cell"), kwargs.get("target")
    operations = []
    if endpoint == "hit" and action_plan is not None:
        operations.extend(action_plan.feedback_opcodes)
    for row in state.equipment.formation().reactions:
        if row.event != endpoint or not condition_matches(
            row.condition, state, target=target, cell=cell, event=endpoint):
            continue
        if endpoint == "hurt":
            # 「被」的受击过滤：只认实际落账的创伤类型，不把每次受击都
            # 解释成火电声同时满足。damage_kind 缺失（未知来源）按不可
            # 判定处理；原生受击反应（如披风反打）不过滤创伤类型。
            if row.hurt_kind and str(kwargs.get("damage_kind") or "") != row.hurt_kind:
                continue
            if target is None and kwargs.get("source_id"):
                source_id = str(kwargs["source_id"])
                candidate = next((e for e in state.enemies
                                  if e.id == source_id and e.integrity > 0
                                  and e in state.enemies), None)
                if candidate is not None and state.is_visible(candidate.x, candidate.y):
                    target = candidate
                    cell = (candidate.x, candidate.y)
        operations.append(row.opcode)
    results = []
    for opcode in dict.fromkeys(operations):
        result = execute_feedback(state, opcode, cell=cell, target=target,
                                  damage_kind=kwargs.get("damage_kind", ""), action_plan=action_plan)
        results.append(result)
    return results


def cast_imprint(state, row, target):
    if not ready(state, "imprint", active=True) or not _target_ok(state, target):
        return False
    if max(abs(target.x-state.player.x), abs(target.y-state.player.y)) > 6:
        return False
    existing = state.equipment_marks.get(target.id)
    if existing and existing.get("location") == layer_identity(state) and existing.get("until", 0) > state.time:
        return False
    state.equipment_marks[target.id] = {"location": layer_identity(state), "until": state.time + 3,
                                       "amount": 1, "root_id": state.action_seq}
    _record(state, "imprint", active=True)
    state._emit_combat_fx("cut", (target.x, target.y), [(target.x, target.y)])
    # 储存：印记是独立事件；下一次真实命中兑现时再发 release 事件。
    point = (target.x, target.y)
    emit_equipment_visual(
        state, endpoint=_root_endpoint(state), opcode="imprint", outcome="store",
        source=point, targets=(point,), affected_cells=(point,),
        visual_key="fx.memory", store_key=("imprint", str(target.id)),
        facts=(("piece", "imprint"), ("opcode", "imprint"),
               ("until", int(state.time + 3))))
    return True


def redeem_imprint(state, target):
    mark = state.equipment_marks.pop(target.id, None)
    if (not mark or mark.get("location") != layer_identity(state)
            or state.time >= mark.get("until", 0)):
        return 0
    amount = min(1, max(0, int(mark.get("amount", 0))))
    if amount:
        point = (target.x, target.y)
        # 兑现：只观察已经执行的加成伤害；这里绝不调用伤害入口。
        emit_equipment_visual(
            state, endpoint=_root_endpoint(state), opcode="imprint_release",
            outcome="release", visual_key="fx.impact",
            source=point, targets=(point,), affected_cells=(point,),
            parent_store_key=("imprint", str(target.id)),
            facts=(("piece", "imprint"), ("opcode", "strike"),
                   ("amount", int(amount))))
        forget_equipment_store(state, ("imprint", str(target.id)))
    return amount
