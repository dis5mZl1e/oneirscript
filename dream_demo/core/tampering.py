"""篡改的预览与原子提交（规格 §5、实施计划 Task 5）。

一次提交只做一件事：验证 → 写变体 → 扣想象力 → 加混乱度 → 序号 +1 → 判定风险
→ 按一次「使用」推进世界 → 存活才执行风险。任何一步验证失败都不改记录、资源、
时间与序号；同一个 ``request_id`` 重发只回放上次结果（``changed=False``）。
"""

from __future__ import annotations

from typing import Any

from ..data.ids import event_definition_id
from ..data.tamper_schema import RiskOutcome, TamperPreview, TamperRequest, TamperTarget
from ..data.tampering import compose_text, definition_for
from ..equipment.root_facts import root_action
from . import tamper_pipeline as pipeline
from .chaos import chaos_risk_tier, clamp_chaos
from .entities import ActionResult
from .tamper_views import (
    language_of,
    record_of,
    resolve_tamper_options,
    target_for_event,
    target_for_npc,
)


def make_request(state: Any, target: TamperTarget, text_id: str, transition_id: str) -> TamperRequest:
    """按当前记录构造请求；``request_id`` 由身份与版本决定，重发即幂等。"""
    record = record_of(state, target, text_id)
    version = int(record.get("version", 0))
    return TamperRequest(
        target, text_id, transition_id, version,
        f"{target.instance_uid}|{text_id}|{transition_id}|v{version}",
    )


def _pending_object(state: Any, target: TamperTarget) -> Any | None:
    """当前面板指向的那个实例；身份对不上（换了对象、离层、读档错位）返回 None。"""
    if target.kind == "npc":
        npc = state.pending_npc() if getattr(state, "pending_npc_id", None) else None
        if npc is None or npc.integrity <= 0:
            return None
        live = target_for_npc(state, npc)
        if (live.definition_id, live.instance_uid) != (target.definition_id, target.instance_uid):
            return None
        return npc
    event = state.pending_event() if getattr(state, "pending_event_id", None) else None
    if event is None:
        return None
    live = TamperTarget("event", event_definition_id(event.event_id), str(getattr(event, "instance_uid", "") or ""))
    if (live.definition_id, live.instance_uid) != (target.definition_id, target.instance_uid):
        return None
    return event


def _text_open(state: Any, target: TamperTarget, definition: Any, obj: Any) -> str:
    """这段文字此刻还能不能改；返回空串表示可以，否则是玩家可读的原因。"""
    from .tamper_views import tamper_unavailable_reason

    return tamper_unavailable_reason(state, target, definition)


def _validate(state: Any, request: TamperRequest) -> tuple[Any, Any, dict[str, Any], Any, str]:
    """提交与预览共用的验证：返回 (定义, 变化, 记录, 实例, 原因)。原因为空即通过。"""
    from ..i18n import tr

    definition = definition_for(request.text_id)
    # 归属也要对上：只比 target_kind 的话，眼前站着甲却能替乙那句付钱——记录按
    # （实例身份 × text_id）写进存档，视图却永远读不到它，代价白花。
    if (definition is None or definition.target_kind != request.target.kind
            or definition.definition_id != request.target.definition_id):
        return None, None, {}, None, tr("没有这段文字。")
    transition = definition.transition(request.transition_id)
    if transition is None:
        return None, None, {}, None, tr("这个改动不合法。")
    obj = _pending_object(state, request.target)
    if obj is None:
        return None, None, {}, None, tr("这段文字不在眼前。")
    record = record_of(state, request.target, request.text_id)
    version = int(record.get("version", 0))
    if record.get("last_request_id") == request.request_id and version > request.expected_version:
        # 幂等重发：这一笔已经落地，只回放结果（不扣费、不再抽风险）。
        return definition, transition, record, obj, tr("这处修改已经落地了。")
    if request.expected_version != version:
        return definition, transition, record, obj, tr("这句话已经变了——重新看一下再改。")
    if transition.from_variant != str(record.get("variant_id")):
        return definition, transition, record, obj, tr("从当前这句改不出那一笔。")
    reason = _text_open(state, request.target, definition, obj)
    if reason:
        return definition, transition, record, obj, reason
    if int(state.imagination) < int(transition.imagination_cost):
        return definition, transition, record, obj, tr(
            "想象力不够（需要 {n}）。", n=int(transition.imagination_cost))
    return definition, transition, record, obj, ""


def preview_tamper(state: Any, request: TamperRequest, *, language: str | None = None) -> TamperPreview:
    """确认前的可见信息：改前改后、代价、混乱度增量与提交后档位。

    纯读：不写记录、不补事件身份、不抽风险（规格 §5.1）。
    """
    language = language or language_of()
    definition, transition, record, _obj, reason = _validate(state, request)
    if definition is None or transition is None:
        return TamperPreview(request, "", "", 0, 0, int(state.chaos),
                             chaos_risk_tier(int(state.chaos)), False, reason)
    before = compose_text(definition.variant(str(record.get("variant_id")))
                          or definition.variant(definition.initial_variant), language)
    after = compose_text(definition.variant(transition.to_variant), language)
    cost = int(transition.imagination_cost)
    delta = pipeline.quote_cost(state, pipeline.TamperCost(cost, int(transition.chaos_delta))).chaos_delta
    chaos_after = clamp_chaos(int(state.chaos) + delta)
    risk_tier = chaos_risk_tier(chaos_after)
    from .dialogue_contract import build_dialogue_contract
    contract = build_dialogue_contract(
        request, transition, definition, before_text=before, after_text=after,
        imagination_cost=cost, chaos_delta=delta, chaos_after=chaos_after,
        risk_tier=risk_tier, available=not reason, reason=reason,
        effect_note=definition.variant(transition.to_variant).effect_note(language),
        language=language)
    return TamperPreview(
        request, before, after, cost, delta, chaos_after, risk_tier,
        not reason, reason, definition.variant(transition.to_variant).effect_note(language),
        risk_note=pipeline.risk_note(state, chaos_after, imagination_cost=cost),
        contract=contract,
    )


def _compose_result(definition: Any, facts: dict[str, Any], language: str) -> str:
    """按语言重新拼「改成了什么」这句结算语（2026-10-20 §15 第五批）。

    存档里只留稳定 id 与数字（``result_facts``），正文与说明在读取时用当前语言
    渲染——否则中文档在英文环境下重放同一请求会蹦出中文。
    """
    from ..i18n import tr
    from .tamper_prose import strip_terminal

    before_variant = definition.variant(str(facts.get("before_variant") or ""))
    after_variant = definition.variant(str(facts.get("after_variant") or ""))
    if before_variant is None or after_variant is None:
        return ""
    # 引文里去掉自带的句末标点：模板自己收句，否则英文会读成 ``mind.".``。
    parts = [tr("你把「{before}」改成了「{after}」。",
                before=strip_terminal(compose_text(before_variant, language)),
                after=strip_terminal(compose_text(after_variant, language)))]
    note = after_variant.effect_note(language)
    if note:
        parts.append(tr(note))
    tail: list[str] = []
    cost = int(facts.get("cost", 0) or 0)
    if cost:
        tail.append(tr("想象力 −{n}", n=cost))
    chaos = int(facts.get("chaos", 0) or 0)
    # 分档是**由数字推出来的**，不存字符串：档名本身是中文词，存进存档就成了
    # 另一种「渲染后的文本」。
    tail.append(tr("混乱度 {chaos}（{tier}）", chaos=chaos, tier=tr(chaos_risk_tier(chaos))))
    parts.append(_clause_join(tail, language) + _stop(language))
    return _sentence_join(parts, language)


def _stop(language: str) -> str:
    return "." if language == "en" else "。"


def _clause_join(items: list[str], language: str) -> str:
    return "; ".join(items) if language == "en" else "，".join(items)


def _sentence_join(items: list[str], language: str) -> str:
    """英文分句之间要有空格；中文不加（加了就是「。 改后」这种半角空档）。"""
    return (" " if language == "en" else "").join(items)


@root_action
def commit_tamper(state: Any, request: TamperRequest) -> ActionResult:
    """一次原子提交；失败不留痕，重发同一 request_id 只回放结果。"""
    definition, transition, record, obj, reason = _validate(state, request)
    if transition is None:
        return ActionResult(False, reason)
    if reason:
        # 幂等重发：已经成功过的同一请求回放保存的结果，不再扣费、不再抽风险。
        if record.get("last_request_id") == request.request_id and int(record.get("version", 0)) > request.expected_version:
            facts = record.get("result_facts")
            stored = str(record.get("result") or "")
            # 变体已被删掉时 ``_compose_result`` 给空串，退回已存的那句（宁可混语言，也不给空白）。
            message = _compose_result(definition, facts, language_of()) if isinstance(facts, dict) else ""
            message = message or stored
            return ActionResult(False, message, {
                "tamper": request.text_id, "replayed": True,
                "risk_status": record.get("risk_status", ""),
            })
        return ActionResult(False, reason)

    language = language_of()
    key = request.target.record_key(request.text_id)
    entry = dict(record)
    state.tamper_records = dict(getattr(state, "tamper_records", None) or {})
    sequence = pipeline.next_sequence(state)
    entry.update({
        "variant_id": transition.to_variant,
        "version": int(record.get("version", 0)) + 1,
        "content_version": definition.content_version,
        "last_request_id": request.request_id,
        "sequence": sequence,
        "risk": None,
        "risk_status": "",
        "result": "",
    })
    entry.pop("migrated", None)
    state.tamper_records[key] = entry

    cost = int(transition.imagination_cost)
    quoted = pipeline.quote_cost(state, pipeline.TamperCost(cost, int(transition.chaos_delta)))
    chaos_after, outcome = pipeline.settle(
        state, request, quoted,
        sequence=sequence, reason=request.text_id,
        source_uid=request.target.instance_uid)
    if outcome is not None:
        entry["risk"] = {"event_id": outcome.event_id, "payload": dict(outcome.payload or {})}
        entry["risk_status"] = "pending"

    facts = {
        "before_variant": str(record.get("variant_id")),
        "after_variant": transition.to_variant,
        "cost": cost,
        "chaos": chaos_after,
    }
    entry["result_facts"] = facts
    message = _compose_result(definition, facts, language)

    pipeline.advance_time(state)

    if outcome is None:
        entry["risk_status"] = entry["risk_status"] or "none"
    elif state.run_over:
        # 提交本身已经推进了世界：死亡时不退还成本，也不执行风险。
        entry["risk_status"] = "skipped"
    else:
        feedback = pipeline.apply_risk(
            state, RiskOutcome(outcome.event_id, outcome.payload),
            source_uid=request.target.instance_uid)
        entry["risk_status"] = "executed"
        if feedback:
            # 风险反馈是当场渲染的句子，不进 facts（重放不重复执行风险，也不回放它）。
            message += (" " if language == "en" else "") + feedback
    entry["result"] = message
    state.tamper_records[key] = entry
    state.messages.append(message)
    return ActionResult(True, message, {
        "tamper": request.text_id,
        "option": definition.option_id,
        "variant": transition.to_variant,
        "version": entry["version"],
        "sequence": sequence,
        "chaos": chaos_after,
        "risk": outcome.event_id if outcome is not None else "",
        "risk_status": entry["risk_status"],
    })
