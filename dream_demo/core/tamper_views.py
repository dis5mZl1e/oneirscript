"""篡改求值：实例身份、当前变体、改文与选项视图（规格 §8、实施计划 Task 2）。

纯求值层：只读取本局记录，不扣费、不抽签、不写世界。原始内容表不被修改——
需要改动的选项一律深复制，并携带原选项 ID，记账仍按稳定身份走。
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ..data.ids import event_definition_id, event_option_id, npc_option_id
from ..data.npcs import NPC_DEFINITIONS
from ..data.tamper_schema import (
    TamperDefinition,
    TamperTarget,
    TamperTransition,
    TamperVariant,
    TextFragment,
    decode_record_key,
)
from ..data.tampering import compose_text, definitions_for, definition_for


def language_of() -> str:
    from ..i18n import get_language

    return get_language() or "zh"


def ensure_event_uids(events: Sequence[Any], *, run_uid: str, layer_key: str) -> None:
    """给事件补稳定实例身份（规格 §8.2、§9.3）。

    只给空身份赋值：身份一旦写下就不因移动、重排或界面排序重算。内容为本局、
    层／位面、类型、初始坐标与同位置序号，旧存档因此也能得到兼容身份。
    """
    counters: dict[tuple[str, int, int], int] = {}
    for event in events:
        key = (str(event.event_id), int(event.x), int(event.y))
        index = counters.get(key, 0)
        counters[key] = index + 1
        if not getattr(event, "instance_uid", ""):
            event.instance_uid = f"{run_uid}|{layer_key}|{key[0]}|{key[1]},{key[2]}|{index}"


def ensure_state_event_uids(state: Any) -> None:
    """当前层事件的实例身份兜底（对话面板曝光前调用）。"""
    events = tuple(getattr(state, "events", ()) or ())
    if events and all(getattr(event, "instance_uid", "") for event in events):
        return
    ensure_event_uids(events, run_uid=str(getattr(state, "run_uid", "") or ""),
                      layer_key=str(state.layer_key()))


def target_for_event(state: Any, event: Any) -> TamperTarget:
    ensure_state_event_uids(state)
    return TamperTarget("event", event_definition_id(event.event_id), str(getattr(event, "instance_uid", "") or ""))


def target_for_npc(state: Any, npc: Any) -> TamperTarget:
    from .content import npc_trade_key

    kind = getattr(npc, "npc_kind", "") or getattr(npc, "id", "")
    return TamperTarget("npc", str(kind), str(npc_trade_key(npc)))


def current_tamper_target(state: Any) -> TamperTarget | None:
    """当前对话面板指向的对象；背包与个人面板没有篡改入口（规格 §4.1）。"""
    npc = state.pending_npc() if getattr(state, "pending_npc_id", None) else None
    if npc is not None:
        return target_for_npc(state, npc)
    event = state.pending_event() if getattr(state, "pending_event_id", None) else None
    if event is not None:
        return target_for_event(state, event)
    return None


def definitions_for_target(target: TamperTarget | None) -> tuple[TamperDefinition, ...]:
    if target is None:
        return ()
    return definitions_for(target.kind, target.definition_id)


def _blank_record(definition: TamperDefinition) -> dict[str, Any]:
    return {
        "variant_id": definition.initial_variant,
        "version": 0,
        "content_version": definition.content_version,
        "last_request_id": "",
        "sequence": 0,
        "risk": None,
        "risk_status": "",
        "result": "",
        # 结算语的结构化事实（语言中立，2026-10-20 §15 第五批）：重放时按当前
        # 语言重新渲染，旧档没有这一项就退回已存的那句 ``result``。
        "result_facts": None,
    }


def record_of(state: Any, target: TamperTarget, text_id: str) -> dict[str, Any]:
    """该实例 × 该文本的当前改文记录（不存在则给初始值，不写状态）。"""
    definition = definition_for(text_id)
    if definition is None:
        return {}
    records = getattr(state, "tamper_records", None)
    if not isinstance(records, dict):
        return _blank_record(definition)
    entry = records.get(target.record_key(text_id))
    if not isinstance(entry, dict):
        return _blank_record(definition)
    base = _blank_record(definition)
    base.update(entry)
    if definition.variant(str(base.get("variant_id"))) is None:
        # 未知／已删除变体（规格 §9.3）：恢复原始功能，保留已支付的混乱度与历史。
        base["variant_id"] = definition.initial_variant
        base["migrated"] = True
    return base


def current_variant(state: Any, target: TamperTarget, text_id: str) -> TamperVariant | None:
    definition = definition_for(text_id)
    if definition is None:
        return None
    record = record_of(state, target, text_id)
    return definition.variant(str(record.get("variant_id"))) or definition.variant(definition.initial_variant)


def resolve_tamper_text(state: Any, target: TamperTarget, text_id: str, *,
                        language: str | None = None) -> tuple[TextFragment, ...]:
    """当前已确认变体在该语言下的片段（显示与命中映射共用）。"""
    variant = current_variant(state, target, text_id)
    if variant is None:
        return ()
    return variant.fragments(language or language_of())


def resolve_tamper_lines(state: Any, target: TamperTarget, *,
                         language: str | None = None) -> tuple[tuple[str, str], ...]:
    """该对象上「对白／规则句」区域的当前正文，按 text_id 顺序。"""
    language = language or language_of()
    lines: list[tuple[str, str]] = []
    offered = None
    if target.kind == 'npc':
        from .content import npc_option_key, npc_trade_key, npc_visible_options
        npc = next((e for e in state.enemies if npc_trade_key(e) == target.instance_uid), None)
        if npc is not None:
            offered = {npc_option_key(npc, option) for option in npc_visible_options(state, npc)}
    for definition in definitions_for_target(target):
        if definition.region == "option":
            continue
        if offered is not None and definition.option_id not in offered:
            continue
        variant = current_variant(state, target, definition.text_id)
        if variant is None:
            continue
        lines.append((definition.text_id, compose_text(variant, language)))
    return tuple(lines)


def _stable_option_id(target: TamperTarget, position: int, option: Mapping[str, Any]) -> str:
    explicit = option.get("option_id")
    if explicit:
        return str(explicit)
    if target.kind == "event":
        return event_option_id(target.definition_id, position, option)
    table = NPC_DEFINITIONS.get(target.definition_id, {}).get("options", ())
    identity = next((index for index, entry in enumerate(table) if entry is option), position)
    return npc_option_id(target.definition_id, identity, option)


def resolve_tamper_options(state: Any, target: TamperTarget | None,
                           options: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """把改文结果落到可见选项上：只在确有变化时复制，副本带原 option_id。

    原始定义不被改写；复制出来的视图不参与身份查找（规格 §8.1「不能依赖复制
    字典在原表中的对象身份定位」）。
    """
    options = tuple(options or ())
    if target is None:
        return tuple(dict(option) for option in options)
    overrides: dict[str, dict[str, Any]] = {}
    labels: dict[str, str] = {}
    language = language_of()
    for definition in definitions_for_target(target):
        variant = current_variant(state, target, definition.text_id)
        if variant is None or variant.variant_id == definition.initial_variant:
            continue
        patch = dict(variant.option_patches.get(definition.option_id) or {})
        if definition.region == "option":
            patch["label"] = compose_text(variant, "zh")
            labels[definition.option_id] = compose_text(variant, language)
        elif variant.option_label_by_language:
            patch['label'] = (variant.option_label_by_language.get(language)
                              or variant.option_label_by_language['zh'])
        if patch or definition.option_id in labels:
            overrides[definition.option_id] = patch
    if not overrides and not labels:
        return options
    resolved: list[dict[str, Any]] = []
    for position, option in enumerate(options):
        option_id = _stable_option_id(target, position, option)
        patch = overrides.get(option_id)
        if patch is None:
            resolved.append(dict(option) if option_id in labels else option)  # type: ignore[arg-type]
            continue
        view = dict(option)
        view.update(patch)
        view["option_id"] = option_id
        resolved.append(view)
    return tuple(resolved)


def tamper_unavailable_reason(state: Any, target: TamperTarget, definition: TamperDefinition) -> str:
    """Apply the same live interaction limits to prose and option edits."""
    from ..i18n import tr
    from .content import npc_option_key, npc_trade_key, npc_visible_options

    if state.run_over:
        return tr("这一局已经结束。")
    if target.kind == "npc":
        npc = state.pending_npc()
        if (npc is None or npc.integrity <= 0
                or npc_trade_key(npc) != target.instance_uid):
            return tr("这段文字不在眼前。")
        traded = state.npc_traded_options.get(npc_trade_key(npc), ())
        if definition.option_id in traded:
            return tr("这笔交易已经完成，改不动了。")
        from .npc_offers import free_claim_refusal
        original = next((option for option in NPC_DEFINITIONS.get(target.definition_id, {}).get('options', ())
                         if npc_option_key(npc, option) == definition.option_id), None)
        if original is not None:
            reason = free_claim_refusal(state, npc, original)
            if reason:
                return reason
        if not any(npc_option_key(npc, option) == definition.option_id
                   for option in npc_visible_options(state, npc)):
            return tr("这句话已经不在货架上了。")
    else:
        event = state.pending_event()
        if event is None or getattr(event, "instance_uid", "") != target.instance_uid:
            return tr("这段文字不在眼前。")
        if event.resolved or int(getattr(event, "uses_left", 1) or 0) <= 0:
            return tr("这个地点已经没有可改的句子了。")
        if not any(_stable_option_id(target, index, option) == definition.option_id
                   for index, option in enumerate(event.options)):
            return tr("这个改动不合法。")
    return ""


def available_tamper_transitions(state: Any, target: TamperTarget | None) -> tuple[tuple[str, TamperTransition], ...]:
    """从当前变体出发仍然合法的变化（text_id, transition）。"""
    out: list[tuple[str, TamperTransition]] = []
    for definition in definitions_for_target(target):
        if tamper_unavailable_reason(state, target, definition):
            continue
        record = record_of(state, target, definition.text_id)
        from_variant = str(record.get("variant_id") or definition.initial_variant)
        for transition in definition.transitions:
            if transition.from_variant == from_variant:
                out.append((definition.text_id, transition))
    return tuple(out)


def tampered_definitions(state: Any, target: TamperTarget | None) -> tuple[TamperDefinition, ...]:
    """已经改过文的定义（面板要在正文里替换掉原句）。"""
    out: list[TamperDefinition] = []
    for definition in definitions_for_target(target):
        record = record_of(state, target, definition.text_id)
        if str(record.get("variant_id")) != definition.initial_variant:
            out.append(definition)
    return tuple(out)


def definitions_by_option(target: TamperTarget | None) -> dict[str, TamperDefinition]:
    return {definition.option_id: definition for definition in definitions_for_target(target)}


#: 内容修订的显式迁移表（规格 §9.3）：{text_id: {存档里的 content_version: {旧变体: 新变体}}}。
#: 改名或删除变体时先在这里登记映射；没登记的未知变体一律退回原始功能。
VARIANT_MIGRATIONS: dict[str, dict[int, dict[str, str]]] = {}


def migrate_tamper_records(state: Any) -> tuple[str, ...]:
    """读档迁移：把记录对齐当前内容表，返回需要提示一次的兼容消息（规格 §9.3）。

    只动改文记录，不动资源：已经支付的想象力、混乱度与风险历史一律保留，
    也不在加载时补触发任何惩罚。未知变体退回 ``initial_variant`` 并递增
    ``version``，让存档里的旧预览与旧 ``request_id`` 自然失效。
    """
    from ..i18n import tr

    records = getattr(state, "tamper_records", None)
    if not isinstance(records, dict):
        return ()
    notes: list[str] = []
    for key, entry in records.items():
        if not isinstance(entry, dict) or entry.get("retired"):
            continue
        try:
            text_id = decode_record_key(str(key))[1]
        except ValueError:
            continue
        definition = definition_for(text_id)
        if definition is None:
            # 整段文字已随内容修订消失：记录留作历史，改文本身作废。
            entry["retired"] = True
            notes.append(tr("有一处改动引用的句子已不在这一版梦里，它恢复了原样。"))
            continue
        stored_version = int(entry.get("content_version", definition.content_version) or 0)
        variant_id = str(entry.get("variant_id") or definition.initial_variant)
        remap = VARIANT_MIGRATIONS.get(text_id, {}).get(stored_version, {}).get(variant_id, "")
        if remap and definition.variant(remap) is not None:
            entry["variant_id"] = remap
            entry["content_version"] = definition.content_version
            continue
        if definition.variant(variant_id) is not None:
            # 变体仍在，只是正文措辞随内容版本更新过：按变体 ID 重新求值即可。
            entry["content_version"] = definition.content_version
            continue
        entry["variant_id"] = definition.initial_variant
        entry["content_version"] = definition.content_version
        entry["version"] = int(entry.get("version", 0)) + 1
        notes.append(tr("有一处改动引用的写法已不在这一版梦里，那句话恢复了原样。"))
    return tuple(dict.fromkeys(notes))
