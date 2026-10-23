"""篡改内容表的加载期校验（实施计划 Task 1 Step 4）。

不导入核心与界面模块：待校验的目标表由调用方传入，保持与 ``data.validation``
同样的「表由外部注入」约定。
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from dream_demo.data.ids import event_option_id, npc_option_id

from .tamper_schema import TamperDefinition, TamperTransition, TamperVariant, TextFragment
from .tampering import (
    DELETE_WORD_ID,
    EVENT_PATCH_FIELDS,
    INSERT_WORD_IDS,
    LANGUAGES,
    NPC_PATCH_FIELDS,
    WORD_BY_ID,
)


def _apply_operation(fragments: tuple[TextFragment, ...], transition: TamperTransition,
                     slot: Mapping[str, Any], language: str, where: str,
                     out: list[str]) -> tuple[TextFragment, ...] | None:
    """按声明的操作推导「应该变成什么」，用来和实际变体逐字对比。"""
    ids = [fragment.fragment_id for fragment in fragments]
    if transition.operation == "insert":
        anchor = str(slot.get("anchor", ""))
        if anchor not in ids:
            out.append(f"{where}: 插入锚点片段 {anchor!r} 不在起始变体里")
            return None
        insert_fragment = str(slot.get("insert_fragment", ""))
        if not insert_fragment:
            out.append(f"{where}: 插入位置缺少 insert_fragment")
            return None
        word = WORD_BY_ID.get(transition.word_id or "")
        if word is None:
            out.append(f"{where}: 插入操作引用未知词汇 {transition.word_id!r}")
            return None
        text = word.insert_text(language)
        if not text:
            out.append(f"{where}: 词汇 {word.word_id!r} 缺少 {language} 的插入文本")
            return None
        index = ids.index(anchor) + (1 if slot.get("side") == "after" else 0)
        return fragments[:index] + (TextFragment(insert_fragment, text),) + fragments[index:]
    if transition.operation == "delete":
        targets = tuple(slot.get("fragments") or ())
        if not targets:
            out.append(f"{where}: 删除位置没有声明片段范围")
            return None
        positions = []
        for fragment_id in targets:
            if fragment_id not in ids:
                out.append(f"{where}: 删除片段 {fragment_id!r} 不在起始变体里")
                return None
            positions.append(ids.index(fragment_id))
        if positions != list(range(positions[0], positions[0] + len(positions))):
            out.append(f"{where}: 删除范围必须是连续片段")
            return None
        drop = set(targets)
        return tuple(fragment for fragment in fragments if fragment.fragment_id not in drop)
    if transition.operation == "replace":
        targets = tuple(slot.get("fragments") or ())
        replacements = tuple((slot.get("texts") or {}).get(language) or ())
        if not targets or len(targets) != len(replacements):
            out.append(f"{where}: 替换位置必须给出等量的原文与译文片段")
            return None
        result: list[TextFragment] = []
        pending = list(targets)
        for fragment in fragments:
            if fragment.fragment_id in pending:
                if fragment.fragment_id == pending[0]:
                    result.extend(TextFragment(fid, text) for fid, text in zip(targets, replacements))
                pending.remove(fragment.fragment_id)
            else:
                result.append(fragment)
        if pending:
            out.append(f"{where}: 替换片段 {pending!r} 不在起始变体里")
            return None
        return tuple(result)
    out.append(f"{where}: 未知操作 {transition.operation!r}")
    return None


def validate_tamper_definitions(definitions: Sequence[TamperDefinition], *,
                                npcs: Mapping[str, Any],
                                events: Iterable[Mapping[str, Any]]) -> list[str]:
    """返回全部定义问题；空列表表示通过。"""
    out: list[str] = []
    event_list = tuple(events)
    event_ids = {str(event.get("event_id", "")): event for event in event_list}
    npc_option_ids: dict[str, set[str]] = {}
    for npc_id, definition in npcs.items():
        ids = {npc_option_id(npc_id, position, option)
               for position, option in enumerate(definition.get("options") or ())}
        npc_option_ids[npc_id] = ids
    event_option_ids: dict[str, set[str]] = {}
    for event in event_list:
        event_id = str(event.get("event_id", ""))
        event_option_ids[event_id] = {event_option_id(event_id, position, option)
                                      for position, option in enumerate(event.get("options") or ())}

    seen_text_ids: set[str] = set()
    for definition in definitions:
        where = f"tamper {definition.text_id}"
        if definition.text_id in seen_text_ids:
            out.append(f"{where}: text_id 重复")
        seen_text_ids.add(definition.text_id)
        if definition.content_version < 1:
            out.append(f"{where}: content_version 必须 ≥1")

        if definition.target_kind == "npc":
            if definition.definition_id not in npcs:
                out.append(f"{where}: 指向不存在的 NPC {definition.definition_id!r}")
            elif definition.option_id not in npc_option_ids[definition.definition_id]:
                out.append(f"{where}: option_id {definition.option_id!r} 不在该 NPC 的稳定选项身份里")
        elif definition.target_kind == "event":
            if definition.definition_id not in event_ids:
                out.append(f"{where}: 指向不存在的事件 {definition.definition_id!r}")
            elif definition.option_id not in event_option_ids[definition.definition_id]:
                out.append(f"{where}: option_id {definition.option_id!r} 不在该事件的稳定选项身份里")
        else:
            out.append(f"{where}: target_kind 必须是 npc 或 event")
        if definition.region not in ("dialogue", "rule", "option"):
            out.append(f"{where}: region {definition.region!r} 不是开放的三类入口")

        variant_ids = [variant.variant_id for variant in definition.variants]
        if len(variant_ids) != len(set(variant_ids)):
            out.append(f"{where}: variant_id 重复")
        if definition.initial_variant not in variant_ids:
            out.append(f"{where}: 初始变体 {definition.initial_variant!r} 不存在")
        base = definition.variant(definition.initial_variant)
        if base is not None and base.option_patches:
            out.append(f"{where}: 初始变体必须与原定义同效，不能带功能补丁")

        for language in LANGUAGES:
            if language not in definition.slots_by_language:
                out.append(f"{where}: 缺少 {language} 的位置定义")
            for variant in definition.variants:
                if not variant.fragments_by_language.get(language):
                    out.append(f"{where}: 变体 {variant.variant_id!r} 缺少 {language} 片段")
            if base is not None and not base.fragments(language):
                out.append(f"{where}: 初始变体在 {language} 下没有正文")

        patch_fields = EVENT_PATCH_FIELDS if definition.target_kind == "event" else NPC_PATCH_FIELDS
        for variant in definition.variants:
            if variant.option_label_by_language:
                for language in LANGUAGES:
                    if not variant.option_label_by_language.get(language):
                        out.append(f"{where}: 变体 {variant.variant_id!r} 缺少 {language} 的选项名称")
            for option_id, patch in variant.option_patches.items():
                spot = f"{where} 变体 {variant.variant_id}"
                if option_id != definition.option_id:
                    out.append(f"{spot}: 补丁挂在 {option_id!r}，与声明的影响选项 {definition.option_id!r} 不一致")
                for key in patch:
                    if key not in patch_fields:
                        out.append(f"{spot}: 补丁字段 {key!r} 不在允许范围内")

        seen_transitions: set[str] = set()
        for transition in definition.transitions:
            spot = f"{where} 转换 {transition.transition_id}"
            if transition.transition_id in seen_transitions:
                out.append(f"{spot}: transition_id 重复")
            seen_transitions.add(transition.transition_id)
            if transition.from_variant == transition.to_variant:
                out.append(f"{spot}: 起止变体相同，属于无效操作")
            source = definition.variant(transition.from_variant)
            target = definition.variant(transition.to_variant)
            if source is None or target is None:
                out.append(f"{spot}: 引用了未定义的变体")
                continue
            if transition.imagination_cost < 0 or transition.chaos_delta < 0:
                out.append(f"{spot}: 成本不能为负")
            if transition.operation == "insert":
                if transition.word_id not in INSERT_WORD_IDS:
                    out.append(f"{spot}: 插入操作必须使用首批四词之一，收到 {transition.word_id!r}")
            elif transition.word_id is not None and transition.word_id != DELETE_WORD_ID:
                out.append(f"{spot}: {transition.operation} 操作不该带词汇 {transition.word_id!r}")
            for language in LANGUAGES:
                slot = definition.slots(language).get(transition.slot_id)
                if slot is None:
                    out.append(f"{spot}: {language} 缺少位置 {transition.slot_id!r}")
                    continue
                if slot.get("kind") != transition.operation:
                    out.append(f"{spot}: {language} 位置类型 {slot.get('kind')!r} 与操作 {transition.operation!r} 不符")
                    continue
                if transition.rewrite:
                    # 整句润顺（2026-10-12）：不逐字比对片段，只做两条底线校验——
                    # 插入锚点必须真的在起始变体里（面板要靠它画位置标记），
                    # 变体正文必须保留插入词本身（改写不能把改的那个词弄丢）。
                    ids = [fragment.fragment_id for fragment in source.fragments(language)]
                    if transition.operation == "insert":
                        anchor = str(slot.get("anchor", ""))
                        if anchor not in ids:
                            out.append(f"{spot}[{language}]: 插入锚点片段 {anchor!r} 不在起始变体里")
                            continue
                        word = WORD_BY_ID.get(transition.word_id or "")
                        if word is None:
                            out.append(f"{spot}: 插入操作引用未知词汇 {transition.word_id!r}")
                            continue
                        token = word.insert_text(language).strip()
                        if not token or token.casefold() not in "".join(
                                fragment.text for fragment in target.fragments(language)).casefold():
                            out.append(f"{spot}[{language}]: 整句改写必须保留插入词"
                                       f" {word.label(language)!r}")
                    continue
                expected = _apply_operation(source.fragments(language), transition, slot,
                                            language, f"{spot}[{language}]", out)
                if expected is None:
                    continue
                actual = target.fragments(language)
                if tuple((f.fragment_id, f.text) for f in expected) != \
                        tuple((f.fragment_id, f.text) for f in actual):
                    out.append(f"{spot}[{language}]: 变体文字差异不等于声明的{transition.operation}"
                               f"（期望 {''.join(f.text for f in expected)!r}，"
                               f"实际 {''.join(f.text for f in actual)!r}）")
    return out
