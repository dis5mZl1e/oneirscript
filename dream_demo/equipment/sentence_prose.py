"""Player-facing prose for compiled equipment rows.

The formation compiler owns all mechanics.  This module only turns its typed
roles, predicates and relations into text.  A render keeps its source IDs next
to each colored fragment so previews can remain readable without losing the
word or item that supplied each phrase.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
from ..i18n import tr

if TYPE_CHECKING:
    from rich.text import Text  # 仅注解用

FRAGMENT_ROLES = ("item", "manual", "filler")
# filler 是语句里的连接词（把／向／上），渲染进面板时属「次要说明」档。
# 旧值 #8b8da8 在最亮那档面板只有 3.77，第十九节 §10.4 不达标，改取注册表 muted；
# 这里不能 import ui.panel_fields（ui 包 __init__ 引回 equipment，会成环），
# 由 tests/test_panel_field_colors.py 钉住与注册表同值。
ROLE_COLORS = {
    "item": "#6fa8ff",
    "manual": "#ffffff",
    "filler": "#aab0c2",
}


@dataclass(frozen=True)
class ProseFragment:
    text: str
    role: str = "filler"
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderedSentence:
    fragments: tuple[ProseFragment, ...] = ()
    details: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return plain(self.fragments)

    @property
    def legacy_fragments(self) -> tuple[tuple[str, str], ...]:
        return tuple((part.text, part.role) for part in self.fragments)

    @property
    def fragment_sources(self) -> tuple[tuple[str, ...], ...]:
        return tuple(part.source_ids for part in self.fragments)


# Player-facing descriptions for the palace and white-sanatorium equipment.
# Values were checked against their feedback handlers; executable values remain
# in the item definitions and runtime modules.
from ..data.realm_item_prose import REALM_ITEM_PROSE, REALM_ITEM_EFFECTS
ITEM_DESCRIPTIONS = {key: prose[0] for key, prose in REALM_ITEM_PROSE.items()}


def item_description(definition_id: str, fallback: str = "") -> str:
    """Return the reviewed player description for an item, if one is registered."""
    from ..data.items import ITEM_DEFINITIONS
    from ..i18n import tr

    definition = ITEM_DEFINITIONS.get(definition_id, {})
    text = definition.get("description") or ITEM_DESCRIPTIONS.get(definition_id, fallback)
    details = definition.get('effect_description', '')
    return (tr(text) + '\n' + tr(details)) if details else tr(text)


def condition_text(predicate) -> str:
    """Readable predicate wording using the actual compiled threshold/event."""
    from ..i18n import tr

    if predicate is None:
        return tr("没有附加条件")
    if predicate.kind == "all":
        if predicate.negated:
            parts = [condition_text(child) for child in predicate.children]
            return tr("并非同时满足：{conditions}", conditions="且".join(parts))
        return "且".join(condition_text(child) for child in predicate.children)
    if predicate.negated:
        negative = {
            "low_imagination": tr("想象力高于 {n}", n=predicate.threshold),
            "empty_imagination": tr("想象力尚未耗尽"),
            "attached": tr("目标没有附着征兆"),
            "conductive": tr("作用位置不能导电"),
            "lit": tr("作用位置没有光照或视线不可达"),
            "flammable": tr("作用位置没有可燃材料"),
            "wet": tr("作用位置没有液体"),
            "marked": tr("目标没有折射印记"),
        }
        if predicate.kind == "event":
            return _event_text(predicate.event, negative=True)
        return negative.get(predicate.kind, tr("这个条件没有满足"))
    if predicate.kind == "event":
        return _event_text(predicate.event)
    labels = {
        "low_imagination": tr("想象力不超过 {n}", n=predicate.threshold),
        "empty_imagination": tr("想象力已耗尽"),
        "attached": tr("目标已有附着征兆"),
        "conductive": tr("作用位置能够导电"),
        "lit": tr("作用位置有光且视线可达"),
        "flammable": tr("作用位置有可燃材料"),
        "wet": tr("作用位置有液体"),
        "marked": tr("目标带着折射印记"),
    }
    return labels.get(predicate.kind, tr("暂不支持这个条件"))


def voice_text(voice) -> str:
    """Render one inspection-panel meaning without exposing condition opcodes."""
    from ..equipment.positional import Predicate
    from ..i18n import tr

    response = voice.response
    if response.role == "condition":
        predicate = Predicate(response.condition_kind, response.event,
                              response.secondary, voice.instance_id)
        return condition_text(predicate)
    from .lexicon import role_text
    from ..i18n import get_language
    return tr(response.meaning) if get_language() == "en" else role_text(voice.definition_id, response)


_EVENT_TEXT = {
    "hit": "命中目标后",
    "hurt": "受到创伤后",
    "ignite": "身上起火后",
    "voice": "听见声音后",
    "conceive": "展开构想后",
    "move": "完成移动后",
    "recover": "心智、清醒度或想象力恢复后",
    "touch": "发生接触后",
    "ingest": "摄入物品后",
    "settled": "环境效果结算后",
}
_EVENT_NEGATIVE = {
    "hit": "没有命中目标时",
    "hurt": "没有受到创伤时",
    "ignite": "身上没有起火时",
    "voice": "没有听见声音时",
    "conceive": "没有展开构想时",
    "move": "没有完成移动时",
    "recover": "没有恢复心智、清醒度或想象力时",
    "touch": "没有发生接触时",
    "ingest": "没有摄入物品时",
    "settled": "环境效果没有结算时",
}


def _event_text(event: str, *, negative: bool = False) -> str:
    from ..i18n import tr

    table = _EVENT_NEGATIVE if negative else _EVENT_TEXT
    label = table.get(event)
    return tr(label) if label else tr("暂不支持的事件：{event}", event=event)


def _token(text: str, role: str = "filler", *sources: str) -> ProseFragment:
    return ProseFragment(text, role, tuple(dict.fromkeys(source for source in sources if source)))


def _relation_source(relation) -> str:
    if relation.word_cells:
        x, y = relation.word_cells[0]
        return f"{relation.word_id}@{x},{y}"
    return relation.word_id


def _voice(row, instance_id: str, roles=()):
    matches = [voice for voice in row.voices if voice.instance_id == instance_id]
    if roles:
        preferred = next((voice for voice in matches if voice.response.role in roles), None)
        if preferred is not None:
            return preferred
    return min(matches, key=lambda voice: (voice.x, voice.y), default=None)


def _meaning(row, instance_id: str, roles=()) -> str:
    from ..i18n import tr

    voice = _voice(row, instance_id, roles)
    return tr(voice.response.meaning) if voice is not None else ""


def _item_name(row, instance_id: str) -> str:
    from ..data.items import ITEM_DEFINITIONS
    from ..i18n import tr

    voice = _voice(row, instance_id)
    if voice is None:
        return ""
    definition = ITEM_DEFINITIONS.get(voice.definition_id)
    if definition is not None:
        return tr(definition.get("name", voice.response.meaning))
    return tr(voice.response.meaning)


def _payload(row, source_id: str = "") -> str:
    from ..equipment.roles import PAYLOAD_LABELS
    from ..i18n import tr

    payload_type = row.operand_type
    if not payload_type and source_id:
        voice = _voice(row, source_id, ("object", "payload", "source"))
        payload_type = voice.response.payload_type if voice is not None else ""
    if payload_type.startswith("container_"):
        kind = payload_type.split("_", 1)[1]
        return tr(PAYLOAD_LABELS.get(kind, kind))
    if payload_type:
        return tr(PAYLOAD_LABELS.get(payload_type, payload_type))
    return ""


def _target(row, direction=None) -> str:
    from ..i18n import tr

    if direction is not None:
        label = _meaning(row, direction.donor_id, ("target", "payload", "object"))
        if label:
            return label
    return {
        "aimed_cell": tr("本次瞄准的位置"),
        "attached_hostile": tr("已有征兆的失控意识"),
        "empty_cell": tr("没有意识体的留白格"),
    }.get(row.target_kind, tr("目标"))


_PROPERTY_WORDS = {
    "weapon_damage": "锋利",
    "swift_strike": "轻快",
    "pierce_up": "穿透",
    "fire_affinity": "余温",
    "spray_boost": "喷射强化",
    "attach_hunt": "追迹",
    "blast_radius": "爆裂",
    "wet_conduct": "导电",
}
_MANNER_WORDS = {
    "weapon_damage": "锋利地",
    "swift_strike": "轻快地",
    "pierce_up": "以更强的穿透力",
    "fire_affinity": "带着余温",
    "spray_boost": "增加喷射量",
    "attach_hunt": "追踪已有征兆的目标",
    "blast_radius": "带着余爆",
    "repair_up": "更充分地",
    "throw_master": "借投掷的手法，",
    "wet_conduct": "借液体导电",
}
# 裸修饰（修饰列直接摆放，不经「的/地」）在句中的属性读法。
_BARE_PROPERTY_WORDS = {
    "swift_strike": "轻快节拍",
    "pierce_up": "穿透力",
    "spray_boost": "喷射强化",
    "attach_hunt": "追迹气味",
    "fire_affinity": "余温",
    "blast_radius": "余爆",
    "repair_up": "修缮手艺",
    "throw_master": "投掷手法",
    "wet_conduct": "导电力",
}
_EXCLUDED_EFFECT_TEXT = {
    "ignite_strike": "命中后点燃",
}


def _property_label(row, relation) -> str:
    from ..i18n import tr

    voice = _voice(row, relation.donor_id, ("modifier", "complement", "payload"))
    if voice is None:
        return tr("附加效果")
    if voice.response.payload_type == "cut":
        from .lexicon import HAND_WEAR
        if voice.definition_id in HAND_WEAR:
            return tr('掌心的劲道')
        return tr("锋利")
    return tr(_PROPERTY_WORDS.get(voice.response.effect, voice.response.meaning))


def _manner_phrase(row, relation) -> str:
    from ..i18n import tr

    voice = _voice(row, relation.donor_id, ("modifier", "complement", "payload"))
    if voice is None:
        return tr("以附加效果")
    if voice.response.payload_type == "cut" and voice.response.effect != "swift_strike":
        return tr("借助锋利刀锋，")
    return tr(_MANNER_WORDS.get(voice.response.effect, "以" + voice.response.meaning + "的方式"))


def _action_ending(row, direction=None, *, include_payload: bool = True) -> tuple[ProseFragment, ...]:
    from ..i18n import tr

    target = _target(row, direction)
    target_id = direction.donor_id if direction is not None else ""
    target_token = _token(target, "item", target_id)
    toward_role = "manual" if direction is not None else "filler"
    toward_source = _relation_source(direction) if direction is not None else ""
    opcode = row.opcode
    payload = _payload(row) if include_payload else ""
    payload_ids = tuple(v.instance_id for v in row.voices if v.response.role in ("object", "payload"))
    payload_token = _token(payload, "item", *payload_ids) if payload else None
    if opcode == "strike":
        return (_token("斩击", "item", row.source_id), target_token)
    if opcode == "fire":
        return (_token("向", toward_role, toward_source), target_token,
                _token("发射", "item", row.source_id))
    if opcode.startswith("spray_"):
        ending = [_token("向", toward_role, toward_source), target_token,
                  _token("喷射", "item", row.source_id)]
        if payload_token is not None:
            ending.append(payload_token)
        return tuple(ending)
    if opcode == "repair":
        return (_token("修补", "item", row.source_id), target_token)
    if opcode == "measure":
        return (_token("测量", "item", row.source_id), target_token)
    if opcode == "imprint":
        return ((_token("把", "filler"), payload_token) if payload_token else ()) + (
            _token("印在", "item", row.source_id), target_token, _token("上", "filler"))
    if opcode == "shock":
        return (_token("向", "filler"), target_token, _token("释放静电冲击", "item", row.source_id))
    if opcode == "ignite":
        return (_token("点燃", "item", row.source_id), target_token)
    if opcode == "cover":
        return (_token("护着我", "item", row.source_id),)
    if opcode == "maintain":
        return (_token("把效果维持下去", "item", row.source_id),)
    if payload_token is not None:
        return (payload_token, _token("生效", "filler"))
    return (_token("做这件事", "filler", row.source_id),)


def _action_body(row) -> tuple[ProseFragment, ...]:
    from ..i18n import tr
    from .lexicon import action_form, equipment_kind, continuous_word

    relations = row.relations
    by_operator = {relation.operator: relation for relation in relations}
    direction = by_operator.get("direction")
    origin = by_operator.get("origin")
    disposal = by_operator.get("disposal")
    attribution = by_operator.get("attribution")
    manner = by_operator.get("manner")
    coordinate = by_operator.get("coordinate")
    restriction = by_operator.get("restriction")

    out = [_token("我", "filler")]
    custom_disposal = False
    if origin is not None:
        source_name = _item_name(row, origin.donor_id)
        medium = _payload(row, origin.donor_id) or tr("其中的材料")
        out.extend((_token("从", "manual", _relation_source(origin)),
                    _token(source_name, "item", origin.donor_id),
                    _token("中取出", "filler"),
                    _token(medium, "item", origin.donor_id),
                    _token("，再", "filler")))
    elif disposal is not None and row.opcode == "imprint":
        # The "把" relation already supplies the payload and verb. Reusing the
        # general disposal wording produced "把刀痕用于…把刀痕印下…".
        out.extend(_action_ending(row, direction))
        custom_disposal = True
    elif disposal is not None:
        payload = _meaning(row, disposal.donor_id, ("object", "payload", "source"))
        donor = _voice(row, disposal.donor_id, ("object", "payload", "source"))
        if donor is not None and donor.response.payload_type.startswith("container_"):
            payload = _item_name(row, disposal.donor_id) + "中的" + _payload(row, disposal.donor_id)
        out.extend((_token("把", "manual", _relation_source(disposal)),
                    _token(payload or _item_name(row, disposal.donor_id), "item", disposal.donor_id)))
        if row.opcode.startswith("spray_"):
            out.extend((_token("喷向", "filler"),
                        _token(_target(row, direction), "item",
                               direction.donor_id if direction else "")))
            custom_disposal = True
        else:
            out.append(_token("用于", "filler"))
    if not custom_disposal:
        # The relation changes both the executed reading and its wording.
        # Keep the source of the property/manner visible, even across types.
        if restriction is None and manner is not None:
            donor_name = _item_name(row, manner.donor_id)
            donor = next((v for v in row.voices if v.instance_id == manner.donor_id), None)
            if donor is not None and donor_name:
                out.extend((_token(continuous_word(donor.definition_id), "filler"),
                            _token(donor_name, "item", manner.donor_id), _token("，", "filler")))
            out.append(_token(_manner_phrase(row, manner), "item", manner.donor_id,
                              _relation_source(manner)))
        elif restriction is None and attribution is not None:
            property_text = _property_label(row, attribution)
            property_text = {"锋利": "锋利刀锋", "轻快": "轻快节拍"}.get(property_text, property_text)
            out.extend((_token("借助", "filler"),
                        _token(_item_name(row, attribution.donor_id), "item", attribution.donor_id),
                        _token("的", "manual", _relation_source(attribution)),
                        _token(property_text, "item", attribution.donor_id), _token("，", "filler")))
        if restriction is not None:
            out.append(_token("只", "manual", _relation_source(restriction)))

        switched = bool(relations)

        def append_source(iid):
            voice = next((v for v in row.voices if v.instance_id == iid), None)
            name = _item_name(row, iid)
            if voice is None or not name:
                return
            lead, tail = action_form(voice.definition_id, switched=switched)
            out.extend((_token(lead, "item", iid), _token(name, "item", iid)))
            if tail:
                out.append(_token(tail, "filler"))

        if coordinate is not None:
            participants = tuple(dict.fromkeys(iid for iid, role in coordinate.role_bindings if role == "verb"))
            previous_kind = None
            for index, iid in enumerate(participants):
                if index:
                    out.append(_token("和", "manual", _relation_source(coordinate)))
                voice = _voice(row, iid)
                kind = equipment_kind(voice.definition_id) if voice is not None else None
                if kind is not None and kind == previous_kind:
                    out.append(_token(_item_name(row, iid), "item", iid))
                else:
                    append_source(iid)
                previous_kind = kind
            out.append(_token("共同", "filler"))
        else:
            append_source(row.source_id)
        out.extend(_action_ending(row, direction, include_payload=origin is None))
    # 2026-10-14 修饰位差异化：裸修饰（不经「的/地」）也要在句中现身——
    # 关系词已带出的来源不重复，其余按「借助某物的某属性」补出。
    relation_donors = {r.donor_id for r in relations
                       if r.operator in ("attribution", "manner")}
    for iid, effect, power in dict.fromkeys(row.action_modifiers):
        if iid in relation_donors:
            continue
        modifier_name = _item_name(row, iid)
        if not modifier_name:
            continue
        out.extend((_token("，借助", "filler"), _token(modifier_name, "item", iid),
                    _token("的", "filler"),
                    _token(_BARE_PROPERTY_WORDS.get(effect, "附加效果"), "item", iid)))
    if row.feedback_opcodes:
        feedback = {'ignite': '点燃落点', 'shock': '放出静电',
                    'conduct': '借液体传导静电', 'blast': '带出一点余爆'}
        labels = tuple(dict.fromkeys(feedback[op] for op in row.feedback_opcodes if op in feedback))
        if labels:
            out.extend((_token("，命中后可能", "filler"),
                        _token('、'.join(labels), "item", *row.instance_ids)))
    if any(relation.operator == "repetition" for relation in relations):
        out.extend((_token("；前一次确实造成创伤后，", "filler"),
                    _token("再", "manual",
                           *(_relation_source(r) for r in relations if r.operator == "repetition")),
                    _token("出手一次", "filler")))
    return tuple(out)


def _row_details(row) -> tuple[str, ...]:
    details = []
    if row.kind in ("action", "reaction") and any(
            v.response.kind == "supplement" for v in row.voices):
        details.append(tr("补语只随持续契约生效；这一句是即时行为，补语暂不参与。"))
    if row.kind == "contract":
        from .lexicon import contract_ending
        shown_supplements = set()
        for contract in row.contracts:
            voice = _voice(row, contract.instance_id)
            if voice is None or voice.response.kind != "supplement":
                continue
            key = (contract.instance_id, contract.effect)
            if key in shown_supplements:
                continue
            shown_supplements.add(key)
            details.append(tr(
                '随句补足：{item}——{ending}',
                item=_item_name(row, contract.instance_id),
                ending=tr(contract_ending(contract.effect, power=contract.power,
                                          secondary=contract.secondary))))
    if any(contract.effect == 'blank_edge' for contract in row.contracts):
        details.append(tr('留白带来的额外回流合计最多 3 点；多件装备按各自的想象力门槛生效，并沿用递减。'))
    if any(relation.operator == "repetition" for relation in row.relations):
        details.append(tr("两次出手共用一次行动的创伤上限，总创伤不会增加。"))
    for iid, effect, power in dict.fromkeys(row.action_modifiers):
        item_name = _item_name(row, iid)
        if effect == "swift_strike":
            details.append(tr('词义切换：{item}的节拍只缩短关联攻击的耗时；'
                              '同一装备已提供持续攻速时，不重复叠加。', item=item_name))
        elif effect == 'spray_boost':
            details.append(tr('{item}让本句喷射多带出材料；仅从容器取材时生效，'
                              '不超过容器余量。同一件装备的持续效果不重复计算。', item=item_name))
        elif effect == 'repair_up':
            details.append(tr('{item}让本句修缮补得更多；仍消耗原有工具，'
                              '完整度不超过墙体上限。同一件装备的持续效果不重复计算。', item=item_name))
        elif effect == 'pierce_up':
            details.append(tr('{item}让本句弹体多一分穿透；遇墙仍会耗去穿透额度，'
                              '免疫弹体的墙体不受影响。同一件装备的持续效果不重复计算。', item=item_name))
        elif effect == 'attach_hunt':
            details.append(tr('{item}让本句攻击认出残留的附着；目标仍有附着时，'
                              '创伤至多多 1 点。同一件装备的持续效果不重复计算。', item=item_name))
        elif effect == 'wet_conduct':
            details.append(tr('{item}让本句命中或喷射落点借液体传导；'
                              '落点和附近目标都须有导电液体，只多传 1 点创伤。成功消耗 1 点想象力，并受反馈冷却限制。',
                              item=item_name))
        elif effect == 'fire_affinity':
            details.append(tr('{item}让本句命中带出余温；只在有可燃材料的位置点火。'
                              '成功消耗 1 点想象力，并受反馈冷却限制；不凭空生成燃料。', item=item_name))
        elif effect == 'blast_radius':
            details.append(tr('{item}让本句命中带出余爆，最多波及附近一个可见目标 1 点创伤；'
                              '不穿墙。成功消耗 1 点想象力，并受反馈冷却限制。', item=item_name))
        elif effect == 'throw_master':
            details.append(tr('{item}借甩手的力道强化本句攻击，与武器创伤按原有规则共同计算；'
                              '只修饰本句，不额外投出或消耗一件物品。', item=item_name))
    if any(relation.operator == "restriction" for relation in row.relations):
        seen = set()
        for voice in row.voices:
            if voice.response.role != "excluded":
                continue
            effect = voice.response.effect
            modifier = (_PROPERTY_WORDS.get(effect) or _MANNER_WORDS.get(effect)
                        or _EXCLUDED_EFFECT_TEXT.get(effect))
            if not modifier:
                continue
            if modifier.endswith("地"):
                modifier = modifier[:-1]
            key = (voice.instance_id, modifier)
            if key in seen:
                continue
            seen.add(key)
            item = _item_name(row, voice.instance_id)
            label = "效果" if effect in _EXCLUDED_EFFECT_TEXT else "修饰"
            details.append(tr('未采用：{item}提供的“{modifier}”{label}不生效。',
                              item=item, modifier=tr(modifier), label=tr(label)))
    if row.kind not in ("contract", "reaction"):
        return tuple(details)
    from ..data.items import ITEM_DEFINITIONS

    ids = tuple(dict.fromkeys(c.definition_id for c in row.contracts))
    if not ids:
        ids = tuple(dict.fromkeys(v.definition_id for v in row.voices
                                  if v.definition_id.startswith(("hospital.", "library."))))
    details.extend(item_description(item_id) for item_id in ids
                   if ITEM_DEFINITIONS.get(item_id, {}).get("description"))
    return tuple(details)


_READABLE_REASONS = {
    "缺少行为": "还没有放置可执行的行为。",
    "盘面物理无效": "摆放位置有冲突，请调整意象或功能词的位置。",
    "缺少真实载体或效果载荷": "还没有放置能执行这项行为的装备。",
    "这个载体不能形成持续契约": "这个装备不能作为持续效果来源。",
    "这个行为不能改成持续契约": "这个行为不能通过“维持”持续生效。",
    "披覆需要护持载荷": "“披覆”需要搭配防护效果。",
    "载体没有可用行为": "当前装备位置没有可执行的行为。",
    "点燃不接受这种载荷": "“点燃”只能搭配热量类作用内容。",
    "持续行为与对象类型不相容": "当前持续效果不能作用于这个对象。",
    "并列需要左右各有一个合法成分": "“和”左右两侧各需要一件能共同参与的装备。",
    "并列成分存在歧义": "“和”两侧包含多个候选，无法确定要组合的装备。",
    "并列成分没有合法行为": "“和”两侧都需要提供能执行的行为。",
    "并列行为类型不相容": "这两种行为不能合成一次行动。",
    "或者需要左右各有一个候选成分": "“或者”左右两侧各需要一个可选行为。",
    "候选成分存在歧义": "“或者”每侧只能有一个明确的行为。",
    "候选成分没有可执行的主动行为": "“或者”两侧都需要有能主动执行的行为。",
    "多个功能词需要明确的组合关系": "同一行的多个功能词目前不能这样组合。",
    "从需要位于材料来源之前": "“从”应放在容器左侧。",
    "从需要一个真实来源和一个喷射行为": "“从”后需要一个容器和对应的喷射行为。",
    "材料来源与喷射行为不相容": "容器中的材料类型与喷射行为不匹配。",
    "只需要位于所限定的行为之前": "“只”应放在要保留的行为前面。",
    "只缺少后续行为": "“只”后还需要一个行为。",
    "只的行为存在歧义": "“只”后需要一个明确的行为。",
    "只需要一个明确的主动行为": "“只”只能限定一个可执行的行为。",
    "此功能词的关系求值尚未接入": "这个功能词暂时不能与当前摆放组合使用。",
    "把需要位于处置对象之前": "“把”应放在作用内容前面。",
    "把需要后接一个处置对象和一个行为": "“把”后需要作用内容和对应的行为。",
    "缺少属性或方式来源": "左侧还缺一件能出属性或方式的装备。",
    "缺少中心词或行为": "右侧还缺少要被修饰或执行的行为。",
    "同一实体不能通过自身孔洞建立修饰关系": "同一件装备不能同时提供修饰并接受自身修饰。",
    "功能词的关联成分存在歧义": "功能词关联到多件候选装备，无法确定组合对象。",
    "中心词没有合法行为": "右侧装备没有可执行的行为。",
    "方式词义与这个行为不相容": "左侧的修饰效果不能用于右侧行为。",
    "缺少合法属性或处置对象": "左侧没有提供可用的属性或作用内容。",
    "属性与中心词的行为不相容": "左侧属性不能修饰右侧行为。",
    "处置行为不能接受这个对象类型": "这个行为不能处理当前作用内容。",
    "被需要左侧承受者和右侧作用": "“被”左侧需要受击响应装备，右侧需要指定创伤类型。",
    "被的关联成分存在歧义": "“被”两侧各需要一个明确的装备。",
    "同一实体不能既是承受者又是作用": "“被”左右两侧不能使用同一件装备。",
    "这个作用还没有可观察的外界入口": "右侧装备没有当前支持的受击类型。",
    "承受者没有可被动触发的行为": "左侧装备没有可用的受击响应。",
    "这个行为还没有对应的被动响应": "左侧行为目前不能用作受击响应。",
    "向所在行的功能词组合尚不成立": "“向”暂时不能与这一行的其他功能词组合。",
    "向需要唯一目标词和定向行为": "“向”需要关联一个明确的瞄准目标和可定向行为。",
    "这个成分没有合法目标词义": "其中一件装备不能作为瞄准目标。",
    "向的中心词没有合法定向行为": "“向”关联的装备没有可瞄准的行为。",
    "再需要位于所追加的行为之前": "“再”应放在要追加的行为前面。",
    "条件分句缺少合法行为": "条件后还需要一个可执行的行为。",
    "条件分句包含旧标点或旧行为填充词": "条件句里混入了不能参与当前句式的标点或行为词。",
    "条件分句存在多个不明确的行为": "条件后有多个行为，无法确定执行哪一个。",
    "事件条件需要可执行的响应，不能暂时启用持续契约": "事件条件后需要会即时响应的行为，不能用来开启持续效果。",
    "如果缺少真实条件": "“如果”后还需要一个条件。",
    "如果需要位于条件之前": "“如果”应放在提供条件的装备前面。",
    "如果不能跨越另一个功能词寻找条件": "“如果”和条件装备之间不能隔着其他功能词。",
    "如果之后的装备没有条件词义": "“如果”后面的物品不能提供条件。",
    "否则缺少唯一相邻的如果分句": "“否则”需要紧邻一个对应的“如果”分句。",
    "否则需要位于如果分句之后": "“否则”应放在对应的“如果”分句之后。",
    "否则需要位于反分句之前": "“否则”应放在它所限定的行为之前。",
    "此成分已归于条件分句": "这个装备已用于条件句，不能在其他句子中重复使用。",
    "此成分已归于限定行为": "这个装备已用于“只”限定的行为，不能在其他句子中重复使用。",
    "再需要一个可追加的真实行为": "“再”后还需要一个可追加的行为。",
    "再需要唯一且明确的后续行为": "“再”后只能有一个明确的行为。",
    "这个行为的有界追加执行尚未接入": "这个行为暂时不支持追加一次。",
}


def readable_reason(reason: str) -> str:
    from ..i18n import get_language, tr

    if not reason:
        return tr("这行还没有组成完整意思。")
    readable = _READABLE_REASONS.get(
        reason, "这组意象暂时无法组合，请调整相关装备或功能词的位置。")
    if get_language() == "en":
        # 英文模式下优先用**原因键**的既有译文（词表译者按内部键登记）；
        # 只有该键还没有英文时才落回中文可读句，交给调用方 tr() 兜底。
        translated = tr(reason)
        if translated != reason:
            return translated
    return readable


def _unformed(row) -> RenderedSentence:
    from ..i18n import tr

    explanation = readable_reason(row.reason)
    return RenderedSentence((_token(tr("这行暂未成句。")),), (tr(explanation),))


def render_sentence(row) -> RenderedSentence:
    """Render one compiled row once for text, color and source provenance."""
    from ..i18n import get_language, tr

    if not row.voices:
        return RenderedSentence()
    if row.status != "ready":
        return _unformed(row)
    if get_language() == "en":
        fragments = _english_fragments(row)
        return RenderedSentence(tuple(_token(text, role) for text, role in fragments))

    if row.kind == "conditional_header":
        relation = next((r for r in row.relations if r.operator == "conditional"), None)
        target_row = relation.target_row + 1 if relation and relation.target_row >= 0 else row.row + 1
        label = condition_text(row.condition)
        suffix = "" if label.endswith(("时", "后")) else "时"
        parts = (_token(label, "item",
                                                    *(v.instance_id for v in row.voices)),
                 _token(suffix + "，执行第", "filler"), _token(str(target_row), "filler"),
                 _token("行的行为。", "filler"))
        return RenderedSentence(parts)
    if row.kind == "direction_header":
        relation = next((r for r in row.relations if r.operator == "direction"), None)
        target = _target(row, relation)
        return RenderedSentence((_token("这次行动的目标是", "filler"),
                                 _token(target, "item", relation.donor_id if relation else ""),
                                 _token("。", "filler")))
    if row.kind == "alternative":
        relation = next((r for r in row.relations if r.operator == "alternative"), None)
        choices = []
        for branch in row.alternatives:
            name = _item_name(branch, branch.source_id)
            choices.append((name, branch.source_id))
        if len(choices) >= 2:
            parts = [_token("我可以选择", "filler")]
            for index, (name, source) in enumerate(choices):
                if index:
                    parts.append(_token("或者", "manual", _relation_source(relation) if relation else ""))
                parts.append(_token(name, "item", source))
            parts.append(_token("行动；它只走其中一条。", "filler"))
        else:
            parts = [_token("这两个候选行为暂时没有可执行分支。", "filler")]
        return RenderedSentence(tuple(parts))

    if row.kind == "proposal":
        voice = _voice(row, row.source_id, ("verb",))
        if voice is None:
            return RenderedSentence((_token("这条装备读法尚未接入效果。"),))
        return RenderedSentence((
            _token(_item_name(row, voice.instance_id), "item", voice.instance_id),
            _token("：", "filler"),
            _token(voice.response.meaning, "item", voice.instance_id),
            _token("。", "filler"),
        ), _row_details(row))

    if row.kind == "contract":
        from .lexicon import continuous_word, contract_ending
        parts = [_token("我", "filler")]
        ids = tuple(dict.fromkeys(c.instance_id for c in row.contracts))
        if not ids:
            ids = tuple(dict.fromkeys(v.instance_id for v in row.voices
                                     if v.response.role in ("source", "verb", "modifier")))
        contracts = {c.instance_id: c for c in row.contracts}
        coordinate = next((r for r in row.relations if r.operator == "coordinate"), None)
        for index, item_id in enumerate(ids):
            if index:
                # 上一件的落句已有「；/。」时不再叠一个逗号（「；，和」是旧瑕疵）。
                previous = parts[-1].text if parts else ""
                lead = "和" if previous.endswith(("；", "。")) else "，和"
                parts.append(_token(lead, "manual" if coordinate else "filler",
                                    _relation_source(coordinate) if coordinate else ""))
            voice = next((v for v in row.voices if v.instance_id == item_id), None)
            if voice is not None:
                parts.append(_token(continuous_word(voice.definition_id), "item", item_id))
            parts.append(_token(_item_name(row, item_id), "item", item_id))
            tail = "。" if index == len(ids) - 1 else "；"
            contract = contracts.get(item_id)
            parts.append(_token("，" + contract_ending(
                contract.effect if contract else "", power=contract.power if contract else 0,
                secondary=contract.secondary if contract else 0) + tail, "filler"))
        details = _row_details(row)
    elif row.kind == "reaction" and row.hurt_kind:
        harm = {"lucidity": "清醒创伤", "mind": "心智创伤"}.get(row.hurt_kind, "创伤")
        passive = next((r for r in row.relations if r.operator == "passive"), None)
        if passive is not None:
            wound = {"lucidity": "伤及清醒", "mind": "伤及心智"}.get(row.hurt_kind, "伤到")
            parts = [_token("我", "filler"),
                     _token("被", "manual", _relation_source(passive)),
                     _token(wound, "item", passive.head_id), _token("后，", "filler"),
                     *_action_body(row)]
        else:
            parts = [_token("受到", "filler"), _token(harm, "item"), _token("后，", "filler"),
                     *_action_body(row)]
        details = _row_details(row)
    else:
        parts = list(_action_body(row))
        details = _row_details(row)

    prefix = ()
    if row.condition is not None:
        label = condition_text(row.condition)
        if row.condition.kind == "event" and not row.condition.negated:
            prefix = (_token(label + "，", "item",
                             *(v.instance_id for v in row.voices if v.response.role == "condition")),)
        else:
            control = next((r for r in row.relations
                            if r.operator in ("conditional", "alternative_condition")), None)
            if control is not None and control.operator == "conditional":
                prefix = (_token("如果", "manual", _relation_source(control)),
                          _token(label, "item",
                                 *(v.instance_id for v in row.voices if v.response.role == "condition")),
                          _token("，", "filler"))
            elif control is not None and control.operator == "alternative_condition":
                prefix = (_token("否则", "manual", _relation_source(control)),
                          _token("（", "filler"), _token(label, "item"),
                          _token("），", "filler"))
            else:
                prefix = (_token(label, "item",
                                 *(v.instance_id for v in row.voices if v.response.role == "condition")),
                          _token(("" if label.endswith(("时", "后")) else "时") + "，", "filler"))
    elif row.kind == "reaction" and row.event and not row.hurt_kind:
        prefix = (_token(_event_text(row.event) + "，", "filler"),)

    parts = list(prefix) + list(parts)
    if parts:
        final = parts[-1]
        if not final.text.endswith(("。", "！", "？")):
            parts[-1] = _token(final.text + "。", final.role, *final.source_ids)
    return RenderedSentence(tuple(parts), details)


def sentence_fragments(row) -> tuple[tuple[str, str], ...]:
    """Compatibility adapter for existing Rich UI callers."""
    return render_sentence(row).legacy_fragments


def plain(fragments) -> str:
    return "".join(text if isinstance(text, str) else text.text
                   for text, *_rest in fragments) if fragments and isinstance(fragments[0], tuple) else \
        "".join(fragment.text for fragment in fragments)


def fragments_to_text(fragments, base_style: str = "") -> "Text":
    """Color-compatible `(text, role)` fragments to a Rich Text instance."""
    from rich.text import Text

    result = Text(style=base_style) if base_style else Text()
    for text, role in fragments:
        result.append(text, style=ROLE_COLORS.get(role, role))
    return result


_EN_EVENT = {
    "hit": "after hitting the target", "hurt": "after taking damage",
    "ignite": "after catching fire", "voice": "after hearing a sound",
    "conceive": "after using a conception", "move": "after moving",
    "recover": "after recovering Mind, Lucidity or Imagination",
    "touch": "after contact", "ingest": "after ingesting an item",
    "settled": "after an environmental effect resolves",
}
_EN_EVENT_NEGATIVE = {
    "hit": "without hitting the target", "hurt": "without taking damage",
    "ignite": "without catching fire", "voice": "without hearing a sound",
    "conceive": "without using a conception", "move": "without moving",
    "recover": "without recovering Mind, Lucidity or Imagination",
    "touch": "without contact", "ingest": "without ingesting an item",
    "settled": "without an environmental effect resolving",
}
_EN_MANNER = {
    "weapon_damage": "with a sharp edge",
    "swift_strike": "swiftly",
    "pierce_up": "with greater piercing power",
    "fire_affinity": "with the remnant heat",
    "spray_boost": "with a stronger spray",
    "attach_hunt": "tracking the marked target",
    "blast_radius": "with a lingering blast",
    "repair_up": "more thoroughly",
    "throw_master": "with a practiced throw",
    "wet_conduct": "channeling through the liquid",
}


def english_manner_text(effect: str) -> str:
    """Manner-specific English; never collapse every effect to 'swiftly'."""
    return _EN_MANNER.get(str(effect or ""), "with its own manner")


def english_condition_text(predicate) -> str:
    """English counterpart of condition_text; never leaks Chinese literals."""
    if predicate is None:
        return "no extra condition"
    if predicate.kind == "all":
        parts = [english_condition_text(child) for child in predicate.children]
        joined = " and ".join(parts)
        return f"not both: {joined}" if predicate.negated else joined
    if predicate.kind == "event":
        table = _EN_EVENT_NEGATIVE if predicate.negated else _EN_EVENT
        return table.get(predicate.event, f"unsupported event: {predicate.event}")
    positive = {
        "low_imagination": f"Imagination is at most {predicate.threshold}",
        "empty_imagination": "Imagination is exhausted",
        "attached": "the target has an attached omen",
        "conductive": "the cell conducts",
        "lit": "the cell is lit and in sight",
        "flammable": "the cell has flammable material",
        "wet": "the cell contains liquid",
        "marked": "the target bears a refraction mark",
    }
    negative = {
        "low_imagination": f"Imagination is above {predicate.threshold}",
        "empty_imagination": "Imagination is not exhausted",
        "attached": "the target has no attached omen",
        "conductive": "the cell does not conduct",
        "lit": "the cell is not lit or out of sight",
        "flammable": "the cell has no flammable material",
        "wet": "the cell contains no liquid",
        "marked": "the target has no refraction mark",
    }
    return (negative if predicate.negated else positive).get(
        predicate.kind, "an unsupported condition")


def _english_manner(row, relation) -> str:
    voice = _voice(row, relation.donor_id, ("modifier", "complement", "payload"))
    return english_manner_text(voice.response.effect if voice is not None else "")


_EN_VERBS = {
    "strike": "Strike", "fire": "Fire at", "repair": "Repair",
    "measure": "Measure", "imprint": "Imprint", "shock": "Release a shock at",
    "ignite": "Ignite", "dispel": "Dispel", "lure": "Lure",
}
_EN_TARGETS = {
    "aimed_cell": "the aimed cell",
    "attached_hostile": "the omen-bearing hostile",
    "empty_cell": "the empty cell",
}
_EN_EFFECT_NOUNS = {
    "weapon_damage": "cutting edge", "swift_strike": "speed",
    "pierce_up": "piercing power", "fire_affinity": "remnant heat",
    "spray_boost": "spray strength", "attach_hunt": "hunted mark",
    "blast_radius": "lingering blast", "repair_up": "repair craft",
    "throw_master": "throwing technique", "wet_conduct": "conducted charge",
}


def _en_voice_text(row, instance_id: str, roles=()) -> str:
    from ..i18n import tr
    voice = _voice(row, instance_id, roles)
    if voice is None:
        return ""
    return tr(voice.response.meaning)


_EN_MEDIUM_NOUNS = {"container_liquid": "liquid", "container_gas": "gas"}


def _lower_first(text: str) -> str:
    """把句中的性质名词写成小写；缩写与全大写保持原样。"""
    text = str(text or "").strip()
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]


def _with_article(text: str) -> str:
    """宾语位置的名词短语补一个冠词（已有限定词时不动）。"""
    text = _lower_first(text)
    if not text or text.split()[0].lower() in ("a", "an", "the", "your", "its"):
        return text
    return ("an " if text[0] in "aeiou" else "a ") + text


def _en_payload(row) -> str:
    """The thing the action carries: a mark, a medium, or the bottle's name.

    A container is a source, not the payload — "Spray the liquid from the
    bottle", never "Spray Glass Bottle".
    """
    for voice in row.voices:
        if voice.response.role in ("object", "payload"):
            medium = _EN_MEDIUM_NOUNS.get(getattr(voice.response, "payload_type", ""))
            if medium:
                return "the " + medium
            return _en_voice_text(row, voice.instance_id, (voice.response.role,))
    return ""


def _en_target(row) -> str:
    if row.target_kind in _EN_TARGETS:
        return _EN_TARGETS[row.target_kind]
    if getattr(row, "opcode", "") == "imprint":
        return "the target"
    for voice in row.voices:
        if voice.response.role == "target":
            text = _en_voice_text(row, voice.instance_id, ("target",))
            if text:
                return text if text.startswith(("the ", "a ", "an ")) else "the " + text
    return "the target"


def _en_source(row) -> str:
    source_id = getattr(row, "source_id", "") or ""
    if source_id:
        name = _item_name(row, source_id)
        if name:
            return name
    for voice in row.voices:
        if voice.response.role in ("verb", "source", "carrier"):
            name = _item_name(row, voice.instance_id)
            if name:
                return name
    return ""


def _en_action(row) -> str:
    """Compose one English action from the row's relations.

    §15 batch 2: the phrase order comes from ``english_binding`` (English word
    order), not from the order relations happen to be registered in and not
    from the Chinese column order.  Mechanisms are untouched — this only
    decides which English function word carries each fact and where it sits.
    """
    from .english_binding import binding_for, compose

    opcode = str(getattr(row, "opcode", "") or "")
    target = _en_target(row)
    payload = _en_payload(row)
    phrases: list[tuple[str, str]] = []
    clauses: list[str] = []
    origin_text = next((_en_voice_text(row, r.donor_id) for r in row.relations
                        if r.operator == "origin"), "")
    if opcode == "imprint":
        predicate = f"Imprint {_with_article(payload) or 'a mark'} on {target}"
    elif opcode.startswith("spray"):
        # 材料来源夹在"喷什么"和"喷向哪"之间，句尾就不再重复一次瓶子。
        origin = f" from {origin_text}" if origin_text else ""
        predicate = f"Spray {payload or 'the contents'}{origin} at {target}"
    elif opcode == "strike":
        predicate = f"Strike {target}"
    elif opcode == "fire":
        predicate = f"Fire at {target}"
    elif opcode in _EN_VERBS:
        predicate = f"{_EN_VERBS[opcode]} {target}"
    else:
        source = _en_source(row)
        predicate = f"Use {source} on {target}" if source else f"Act on {target}"

    for relation in row.relations:
        binding = binding_for(relation.word_id, relation.operator)
        if binding is None:
            continue
        slot, operator = binding.slot, relation.operator
        if operator == "attribution":
            donor = _en_voice_text(row, relation.donor_id)
            voice = _voice(row, relation.donor_id,
                           ("modifier", "complement", "payload"))
            effect = voice.response.effect if voice is not None else ""
            phrase = _EN_EFFECT_NOUNS.get(effect) or _lower_first(donor)
            if phrase:
                phrases.append((slot, binding.render(phrase)))
        elif operator == "manner":
            voice = _voice(row, relation.donor_id,
                           ("modifier", "complement", "payload"))
            effect = voice.response.effect if voice is not None else ""
            phrases.append((slot, binding.render(english_manner_text(effect))))
        elif operator == "origin":
            # 喷射行为已把来源写进谓词（Spray X from Y at Z），不再重复一遍。
            if origin_text and not opcode.startswith("spray"):
                phrases.append((slot, binding.render(origin_text)))
        elif operator == "coordinate":
            donors = []
            for instance_id in (relation.donor_id, relation.head_id):
                name = _item_name(row, instance_id) or _en_voice_text(row, instance_id)
                if name:
                    donors.append(name)
            if donors:
                phrases.append((slot, binding.render(" and ".join(donors))))
        elif operator == "direction":
            # target_kind 已经把"向"的结果说成 the aimed cell，别再说第二遍。
            donor = _en_voice_text(row, relation.donor_id)
            if donor and not getattr(row, "target_kind", "") and donor not in predicate:
                phrases.append((slot, binding.render(donor)))
        elif operator in ("restriction", "repetition"):
            phrases.append((slot, binding.render()))
    return compose(predicate, phrases, clauses)


def _english_body(row) -> str:
    """Natural English for the existing Chinese column semantics."""
    from ..i18n import tr
    if row.kind == "conditional_header":
        relation = next((r for r in row.relations if r.operator == "conditional"), None)
        target_row = relation.target_row + 1 if relation and relation.target_row >= 0 else row.row + 1
        return f"If {english_condition_text(row.condition)}, execute the action on row {target_row}."
    if row.kind == "direction_header":
        relation = next((r for r in row.relations if r.operator == "direction"), None)
        target = (_en_voice_text(row, relation.donor_id) if relation is not None else "") or _en_target(row)
        return f"This action targets {target}."
    if row.kind == "alternative":
        choices = [_item_name(row, branch.source_id) for branch in row.alternatives]
        choices = [choice for choice in choices if choice]
        if len(choices) >= 2:
            return f"You may choose {choices[0]} or {choices[1]}; only one takes effect."
        return "Neither candidate has an executable branch yet."
    if row.kind == "proposal":
        voice = _voice(row, row.source_id, ("verb",))
        if voice is None:
            return "This equipment reading is not connected to an effect yet."
        return f"{_item_name(row, voice.instance_id)}: {tr(voice.response.meaning)}."
    if row.kind == "contract":
        voice = next((v for v in row.voices if v.response.role in ("verb", "source", "carrier")), None)
        item_id = voice.instance_id if voice is not None else ""
        item = _item_name(row, item_id) if item_id else ""
        meaning = tr(voice.response.meaning) if voice is not None else "maintain"
        obj = ""
        for candidate in row.voices:
            if candidate.response.role in ("object", "payload", "complement"):
                obj = tr(candidate.response.meaning)
                break
        if obj and meaning.lower() != obj.lower():
            return f"You {meaning.lower()} {obj.lower()}" + (f" from {item}." if item else ".")
        return f"You {meaning.lower()} {item}." if item else f"You {meaning.lower()}."
    parts = [_en_action(row)]
    alternative = any(r.operator == "alternative_condition" for r in row.relations)
    passive = next((r for r in row.relations if r.operator == "passive"), None)
    # 「被」的触发类型已经由 hurt_kind 说成"当你受到某类创伤"，再加一句
    # "When hurt by <物>" 会把同一件事重复两遍。
    if passive is not None and not getattr(row, "hurt_kind", ""):
        from .english_binding import binding_for
        donor = _en_voice_text(row, passive.donor_id) or "the source"
        binding = binding_for(passive.word_id, "passive")
        clause = binding.render(donor) if binding is not None else f"When hurt by {donor}"
        parts.insert(0, clause + ",")
    if row.kind == "reaction" and row.hurt_kind:
        harm = "Lucidity damage" if row.hurt_kind == "lucidity" else "Mind damage"
        parts.insert(0, f"When you take {harm},")
    elif row.kind == "reaction" and row.event and not alternative:
        event = _EN_EVENT.get(row.event, f"when {row.event} happens")
        parts.insert(0, event[0].upper() + event[1:] + ",")
    if alternative:
        parts.insert(0, "Otherwise,")
    condition_needed = row.condition is not None and not alternative
    if (condition_needed and row.kind == "reaction" and row.event
            and row.condition.kind == "event"):
        condition_needed = False
    if condition_needed:
        if row.condition.kind == "event" and not row.condition.negated:
            phrase = english_condition_text(row.condition)
        else:
            phrase = "If " + english_condition_text(row.condition)
        parts.insert(0, phrase + ",")
    if len(parts) > 1 and parts[-1]:
        parts[-1] = parts[-1][0].lower() + parts[-1][1:]
    text = " ".join(part for part in parts if part).strip()
    text = text[0].upper() + text[1:] if text else ""
    if text and text[-1] not in ".!?;":
        text += "."
    return text


def _english_fragments(row) -> tuple[tuple[str, str], ...]:
    """Natural English sentence; falls back to the legacy fragment path on failure."""
    try:
        text = _english_body(row)
        if text:
            return ((text, "item"),)
    except Exception:
        pass
    text = _legacy_body(row)
    parts = text.split(" · ") if " · " in text else [text]
    fragments = []
    for index, part in enumerate(parts):
        if index:
            fragments.append((" · ", "filler"))
        if part.strip():
            fragments.append((part.strip(), "filler" if index else "item"))
    return tuple(fragments)


def _legacy_body(row) -> str:
    """Legacy English wording; never used for Chinese player-facing prose."""
    from ..i18n import tr

    controls = tuple(r for r in row.relations
                     if r.operator in ("conditional", "alternative_condition"))
    if controls:
        relation = controls[-1]
        stripped = replace(row, relations=tuple(r for r in row.relations if r not in controls),
                           voices=tuple(v for v in row.voices if v.response.role != "condition"))
        body = _legacy_body(stripped)
        if relation.operator == "alternative_condition":
            return f"otherwise, {body}"
        return f"if {english_condition_text(row.condition)}, {body}"
    direction = next((r for r in row.relations if r.operator == "direction"), None)
    if direction is not None:
        target = _meaning(row, direction.donor_id)
        stripped = replace(row, relations=tuple(r for r in row.relations if r is not direction),
                           voices=tuple(v for v in row.voices if v.instance_id != direction.donor_id))
        return f"{_legacy_body(stripped)} toward {target}"
    if any(r.operator == "repetition" for r in row.relations):
        stripped = replace(row, relations=tuple(r for r in row.relations
                                                if r.operator != "repetition"))
        return f"{_legacy_body(stripped)} again; shared budget"
    if row.relations:
        relation = row.relations[0]
        donor, head = _meaning(row, relation.donor_id), _meaning(row, relation.head_id)
        phrases = {
            "attribution": f"{head} with {donor}",
            "manner": f"{head} {_english_manner(row, relation)}",
            "disposal": f"{head} {donor}", "coordinate": f"{donor} and {head}",
            "alternative": f"{donor} or {head}", "restriction": f"only {head}",
            "origin": f"{head} from {donor}",
            "passive": f"when hurt by {donor}, {head}",
        }
        if relation.operator in phrases:
            return phrases[relation.operator]
    words = []
    seen = set()
    for voice in sorted(row.voices, key=lambda value: (value.x, value.instance_id)):
        key = (voice.instance_id, voice.response.role, voice.response.meaning)
        if key not in seen:
            words.append(tr(voice.response.meaning))
            seen.add(key)
    return ", ".join(words)
