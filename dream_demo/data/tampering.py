"""篡改内容：四个固定词、删除，以及 37 处接入的现有对象（规格 §3.2、§8.4）。

每处正文按片段组织；变体之间的文字差异严格等于声明过的插入／删除——
2026-10-12 起带 ``rewrite`` 的转换例外：那类转换按原意整句润顺，校验器只
要求插入词仍在正文里。功能结果写在 ``option_patches`` 里，绑定原有稳定
选项 ID，不改写内容表本身。

每处至少两个词、至少一处多位置（词表 ↑↓ 可切、位置阶段 ←→ 与鼠标可移），
这是玩家对插入光标可操作性的内容底线。
"""

from __future__ import annotations

from typing import Any, Mapping

from .tamper_schema import (
    TamperDefinition,
    TamperTransition,
    TamperVariant,
    TextFragment,
    TamperWord,
)

LANGUAGES = ("zh", "en")

#: 首批固定词汇与删除（规格 §3.2、§5.1 的默认成本）。与装备虚词各自独立注册。
TAMPER_WORDS: tuple[TamperWord, ...] = (
    TamperWord("negate", {"zh": "不", "en": "Not"}, {"zh": "不", "en": "not "}, 2, 6),
    TamperWord("only", {"zh": "只", "en": "Only"}, {"zh": "只", "en": "only "}, 3, 8),
    TamperWord("also", {"zh": "也", "en": "Also"}, {"zh": "也", "en": "also "}, 4, 10),
    TamperWord("again", {"zh": "再", "en": "Again"}, {"zh": "再", "en": " again"}, 5, 14),
    TamperWord("delete", {"zh": "删除", "en": "Delete"}, {"zh": "", "en": ""}, 2, 6),
)

WORD_BY_ID: dict[str, TamperWord] = {word.word_id: word for word in TAMPER_WORDS}
#: 可插入的词（删除单列，不进词表选择之外的语义）。
INSERT_WORD_IDS: tuple[str, ...] = ("negate", "only", "also", "again")
DELETE_WORD_ID = "delete"

#: 事件补丁允许的字段：资源增量、奖励数量与选项崩解（实施计划 Task 1 Step 4）。
EVENT_PATCH_FIELDS = frozenset({"mind", "lucidity", "imagination", "dissolution", "reward_count"})
#: NPC 补丁允许的字段：本次配置的代价／所得，不动库存身份与剧情命令。
NPC_PATCH_FIELDS = frozenset({"cost", "gain"})


def _fragments(zh: tuple[tuple[str, str], ...], en: tuple[tuple[str, str], ...]) -> Mapping[str, tuple[TextFragment, ...]]:
    return {
        "zh": tuple(TextFragment(fid, text) for fid, text in zh),
        "en": tuple(TextFragment(fid, text) for fid, text in en),
    }


def _slots(zh: Mapping[str, Any], en: Mapping[str, Any] | None = None) -> Mapping[str, Mapping[str, Mapping[str, Any]]]:
    return {"zh": zh, "en": en if en is not None else zh}


def _insert(anchor: str, fragment: str, side: str = "before") -> dict[str, Any]:
    return {"kind": "insert", "anchor": anchor, "side": side, "insert_fragment": fragment}


def _delete(*fragments: str) -> dict[str, Any]:
    return {"kind": "delete", "fragments": tuple(fragments)}


TAMPER_DEFINITIONS: tuple[TamperDefinition, ...] = (
    # 1. 精神观测家：付心智换少见装备的对白（影响 trade.3）
    #    三个词：不=免费、只=心智减价、也=额外收清醒度（改坏的例子）。
    TamperDefinition(
        text_id="tamper.mind_observer.mind_cost",
        target_kind="npc",
        definition_id="npc.mind_observer",
        region="dialogue",
        option_id="npc.mind_observer.trade.3",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "这件东西，"), ("f_cost", "收你的心智。")),
                           (("f_lead", "This piece is "), ("f_cost", "paid in mind."))),
                {},
                {"zh": "原样：这项交易照收心智 14。", "en": "Unchanged: the trade still takes 14 mind."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_lead", "这件东西，"), ("f_negate", "不"), ("f_cost", "收你的心智。")),
                           (("f_lead", "This piece is "), ("f_negate", "not "), ("f_cost", "paid in mind."))),
                {"npc.mind_observer.trade.3": {"cost": {}}},
                {"zh": "改后：这件装备不再收心智，其余所得与「每人一次」照旧。",
                 "en": "Altered: the piece costs no mind; the gain and its one-time limit are unchanged."},
            ),
            TamperVariant(
                "only_cheap",
                _fragments((("f_lead", "这件东西，"), ("f_only", "只"), ("f_rest", "收 8 点心智。")),
                           (("f_lead", "This piece "), ("f_only", "only "), ("f_rest", "costs you 8 mind."))),
                {"npc.mind_observer.trade.3": {"cost": {"mind": 8}}},
                {"zh": "改后：心智代价 14 变为 8，所得与「每人一次」照旧。",
                 "en": "Altered: the mind cost drops from 14 to 8; the gain and its one-time limit are unchanged."},
            ),
            TamperVariant(
                "also_lucidity",
                _fragments((("f_lead", "这件东西，"), ("f_also", "也"), ("f_rest", "收你的清醒度。")),
                           (("f_lead", "This piece is "), ("f_also", "also "), ("f_rest", "paid in lucidity."))),
                {"npc.mind_observer.trade.3": {"cost": {"mind": 14, "lucidity": 6}}},
                {"zh": "改后：心智 14 照收，还额外收清醒度 6——改坏了，看清楚再确认。",
                 "en": "Altered: the 14 mind still applies, plus 6 lucidity on top — a bad edit; read before confirming."},
            ),
        ),
        transitions=(
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6),
            TamperTransition("t_undo_negate", "negated", "base", "delete", "slot_drop_negate", None, 2, 6),
            TamperTransition("t_only", "base", "only_cheap", "insert", "slot_only", "only", 3, 8, rewrite=True),
            TamperTransition("t_also", "base", "also_lucidity", "insert", "slot_also", "also", 4, 10, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_negate": _insert("f_cost", "f_negate"),
            "slot_drop_negate": _delete("f_negate"),
            "slot_only": _insert("f_cost", "f_only"),
            "slot_also": _insert("f_cost", "f_also"),
        }),
    ),
    # 2. 夜药剂师：苦艾糖滴交易的对白（影响 trade.0，清醒度 6 → 0 / 3）
    #    2026-10-22（E5后续 P3）：报价从「心智 10」改为「清醒度 6」（支付药品
    #    不恢复的那种资源），三个变体的代价与文案随基础价一起改。
    TamperDefinition(
        text_id="tamper.night_pharmacist.free",
        target_kind="npc",
        definition_id="npc.night_pharmacist",
        region="dialogue",
        option_id="npc.night_pharmacist.trade.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "这片药"), ("f_not", "不"), ("f_tail", "免费。")),
                           (("f_lead", "This dose is "), ("f_not", "not "), ("f_tail", "free."))),
                {},
                {"zh": "原样：苦艾糖滴照收清醒度 6。", "en": "Unchanged: the pastille still takes 6 lucidity."},
            ),
            TamperVariant(
                "free",
                _fragments((("f_lead", "这片药"), ("f_tail", "免费。")),
                           (("f_lead", "This dose is "), ("f_tail", "free."))),
                {"npc.night_pharmacist.trade.0": {"cost": {}}},
                {"zh": "改后：这项交易的清醒度代价 6 变为 0，所得与一次性记账不变。",
                 "en": "Altered: the lucidity cost of 6 becomes 0; gain and one-time bookkeeping stay."},
            ),
            TamperVariant(
                "only_cheap",
                _fragments((("f_lead", "这片药"), ("f_only", "只"), ("f_rest", "收一点清醒度。")),
                           (("f_lead", "This dose "), ("f_only", "only "), ("f_rest", "costs a little lucidity."))),
                {"npc.night_pharmacist.trade.0": {"cost": {"lucidity": 3}}},
                {"zh": "改后：清醒度代价 6 变为 3，所得与一次性记账不变。",
                 "en": "Altered: the lucidity cost of 6 becomes 3; gain and one-time bookkeeping stay."},
            ),
            TamperVariant(
                "also_mind",
                _fragments((("f_lead", "这片药"), ("f_rest", "不免费，"), ("f_also", "也"), ("f_tail", "收一点心智。")),
                           (("f_lead", "This dose is not free; it "), ("f_also", "also "), ("f_tail", "takes a little mind."))),
                {"npc.night_pharmacist.trade.0": {"cost": {"lucidity": 6, "mind": 4}}},
                {"zh": "改后：清醒度 6 照收，另收心智 4——改坏了，看清楚再确认。",
                 "en": "Altered: the 6 lucidity stays, plus 4 mind — a bad edit; read before confirming."},
            ),
        ),
        transitions=(
            TamperTransition("t_free", "base", "free", "delete", "slot_drop_not", None, 2, 6),
            TamperTransition("t_restore_not", "free", "base", "insert", "slot_add_not", "negate", 2, 6),
            TamperTransition("t_only", "base", "only_cheap", "insert", "slot_only", "only", 3, 8, rewrite=True),
            TamperTransition("t_also", "base", "also_mind", "insert", "slot_also", "also", 4, 10, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_drop_not": _delete("f_not"),
            "slot_add_not": _insert("f_tail", "f_not"),
            "slot_only": _insert("f_tail", "f_only"),
            "slot_also": _insert("f_tail", "f_also"),
        }),
    ),
    # 3. 编辑留下的批注：规则句（影响 option.0：签名给记忆、崩解 +6）
    #    也=补想象力；只=免崩解；再=整句改写「再签一次」多拿一份（两处位置之一）。
    TamperDefinition(
        text_id="tamper.editor_note.also",
        target_kind="event",
        definition_id="event.editor_note",
        region="rule",
        option_id="event.editor_note.option.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "批注"), ("f_tail", "留给你。")),
                           (("f_lead", "The margin note is "), ("f_tail", "left to you."))),
                {},
                {"zh": "原样：签名得到批注记忆，崩解 +6。", "en": "Unchanged: signing yields the note memory, collapse +6."},
            ),
            TamperVariant(
                "also",
                _fragments((("f_lead", "批注"), ("f_also", "也"), ("f_tail", "留给你。")),
                           (("f_lead", "The margin note is "), ("f_also", "also "), ("f_tail", "left to you."))),
                {"event.editor_note.option.0": {"imagination": 3}},
                {"zh": "改后：签名仍给批注记忆与崩解 +6，另外恢复想象力 3。",
                 "en": "Altered: signing still gives the note memory and collapse +6, and also restores 3 imagination."},
            ),
            TamperVariant(
                "only",
                _fragments((("f_lead", "批注"), ("f_only", "只"), ("f_tail", "留给你。")),
                           (("f_lead", "The margin note is "), ("f_only", "only "), ("f_tail", "left to you."))),
                {"event.editor_note.option.0": {"dissolution": 0}},
                {"zh": "改后：签名仍给批注记忆，这项选择的崩解 +6 变为 +0。",
                 "en": "Altered: signing still gives the note memory; this choice's collapse +6 becomes +0."},
            ),
            TamperVariant(
                "twice",
                _fragments((("f_again", "再签一次，"), ("f_lead", "批注"), ("f_tail", "多留一份给你。")),
                           (("f_again", "Sign "), ("f_lead", "again — "), ("f_tail", "the note is left to you twice."))),
                {"event.editor_note.option.0": {"reward_count": 2}},
                {"zh": "改后：签名再给一份批注记忆（共 2 份），崩解 +6 照旧。",
                 "en": "Altered: signing yields the note memory twice; collapse +6 still applies."},
            ),
        ),
        transitions=(
            TamperTransition("t_also", "base", "also", "insert", "slot_also", "also", 4, 10),
            TamperTransition("t_only", "base", "only", "insert", "slot_only", "only", 3, 8),
            TamperTransition("t_again", "base", "twice", "insert", "slot_again", "again", 5, 14, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_also": _insert("f_tail", "f_also"),
            "slot_only": _insert("f_tail", "f_only"),
            "slot_again": _insert("f_lead", "f_again"),
        }),
    ),
    # 4. 收音机的雨声：行动选项（影响 option.1：崩解 +5、心智 +2）
    #    再=心智翻倍；只=免崩解；也=顺手把清醒度也调回来。
    TamperDefinition(
        text_id="tamper.radio_rain.tune",
        target_kind="event",
        definition_id="event.radio_rain",
        region="option",
        option_id="event.radio_rain.option.1",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_label", "调到没有雨的频率"),),
                           (("f_label", "Tune to a rainless frequency"),)),
                {},
                {"zh": "原样：心智 +2，崩解 +5，占用一次触发。", "en": "Unchanged: mind +2, collapse +5, one use spent."},
            ),
            TamperVariant(
                "again",
                _fragments((("f_again", "再"), ("f_label", "调到没有雨的频率")),
                           (("f_label", "Tune to a rainless frequency"), ("f_again", " again"))),
                {"event.radio_rain.option.1": {"mind": 4}},
                {"zh": "改后：心智恢复追加一次，合计 +4；崩解 +5 与触发次数照常。",
                 "en": "Altered: the mind restore happens twice, +4 total; collapse +5 and the use count are unchanged."},
            ),
            TamperVariant(
                "only",
                _fragments((("f_only", "只调到"), ("f_rest", "没有雨的频率")),
                           (("f_only", "Only tune to "), ("f_rest", "a rainless frequency"))),
                {"event.radio_rain.option.1": {"dissolution": 0}},
                {"zh": "改后：保留心智 +2，这项选择的崩解 +5 变为 +0；触发次数照常。",
                 "en": "Altered: keeps mind +2; this choice's collapse +5 becomes +0; the use count is unchanged."},
            ),
            TamperVariant(
                "also_lucidity",
                _fragments((("f_label", "调到没有雨的频率"), ("f_also", "，也把清醒度调回来")),
                           (("f_label", "Tune to a rainless frequency"), ("f_also", " — also bring a little lucidity back"))),
                {"event.radio_rain.option.1": {"lucidity": 2}},
                {"zh": "改后：心智 +2 照旧，清醒度也 +2；崩解 +5 与触发次数照常。",
                 "en": "Altered: keeps mind +2 and also restores lucidity +2; collapse +5 and the use count are unchanged."},
            ),
        ),
        transitions=(
            TamperTransition("t_again", "base", "again", "insert", "slot_again", "again", 5, 14),
            TamperTransition("t_only", "base", "only", "insert", "slot_only", "only", 3, 8, rewrite=True),
            TamperTransition("t_also", "base", "also_lucidity", "insert", "slot_also", "also", 4, 10, rewrite=True),
        ),
        slots_by_language=_slots(
            {"slot_again": _insert("f_label", "f_again", "before"),
             "slot_only": _insert("f_label", "f_only", "before"),
             "slot_also": _insert("f_label", "f_also", "after")},
            {"slot_again": _insert("f_label", "f_again", "after"),
             "slot_only": _insert("f_label", "f_only", "before"),
             "slot_also": _insert("f_label", "f_also", "after")},
        ),
    ),
    # 5. 干涸的许愿池：行动选项（影响 option.0：温水 2 份）
    #    「再」有两个合法位置：句首=3 份，句尾=整句改写「再捧一把」=4 份。
    TamperDefinition(
        text_id="tamper.dry_fountain.water",
        target_kind="event",
        definition_id="event.dry_fountain",
        region="option",
        option_id="event.dry_fountain.option.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_label", "拿走那点温水"),),
                           (("f_label", "Take the pool of warm water"),)),
                {},
                {"zh": "原样：得到温水 2 份，占用一次触发。", "en": "Unchanged: 2 warm water, one use spent."},
            ),
            TamperVariant(
                "again",
                _fragments((("f_again", "再"), ("f_label", "拿走那点温水")),
                           (("f_label", "Take the pool of warm water"), ("f_again", " again"))),
                {"event.dry_fountain.option.0": {"reward_count": 3}},
                {"zh": "改后：温水由 2 份变为 3 份，仍只结算一次事件使用。",
                 "en": "Altered: warm water goes from 2 to 3; the event use is still spent once."},
            ),
            TamperVariant(
                "scoop",
                _fragments((("f_label", "拿走那点温水"), ("f_tail", "，再捧一把")),
                           (("f_label", "Take the pool of warm water"), ("f_tail", ", and scoop again"))),
                {"event.dry_fountain.option.0": {"reward_count": 4}},
                {"zh": "改后：温水由 2 份变为 4 份，仍只结算一次事件使用。",
                 "en": "Altered: warm water goes from 2 to 4; the event use is still spent once."},
            ),
        ),
        transitions=(
            TamperTransition("t_again", "base", "again", "insert", "slot_again", "again", 5, 14),
            TamperTransition("t_scoop", "base", "scoop", "insert", "slot_scoop", "again", 5, 14, rewrite=True),
        ),
        slots_by_language=_slots(
            {"slot_again": _insert("f_label", "f_again", "before"),
             "slot_scoop": _insert("f_label", "f_tail", "after")},
            {"slot_again": _insert("f_label", "f_again", "after"),
             "slot_scoop": _insert("f_label", "f_tail", "after")},
        ),
    ),
    # 6. 修表匠的遗摊：规则句（影响 option.0：换表、心智 −2、崩解 +5）
    #    不=免心智；只=整句按「只会损耗心智」免崩解；也=额外收清醒度（改坏）。
    TamperDefinition(
        text_id="tamper.clock_repairs.mind_loss",
        target_kind="event",
        definition_id="event.clock_repairs",
        region="rule",
        option_id="event.clock_repairs.option.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "取走这只表，"), ("f_tail", "会损耗你的心智。")),
                           (("f_lead", "Taking this watch is "), ("f_tail", "paid in mind."))),
                {},
                {"zh": "原样：换表得到半枚齿轮，心智 −2，崩解 +5。",
                 "en": "Unchanged: the watch gives a clockwork half, mind −2, collapse +5."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_lead", "取走这只表，"), ("f_negate", "不"), ("f_tail", "会损耗你的心智。")),
                           (("f_lead", "Taking this watch is "), ("f_negate", "not "), ("f_tail", "paid in mind."))),
                {"event.clock_repairs.option.0": {"mind": 0}},
                {"zh": "改后：免除这项选择的心智损失 2，奖励与崩解 +5 照常结算。",
                 "en": "Altered: the 2 mind loss is waived; the reward and collapse +5 still settle."},
            ),
            TamperVariant(
                "only",
                _fragments((("f_lead", "取走这只表，"), ("f_only", "只"), ("f_tail", "会损耗你的心智。")),
                           (("f_lead", "Taking this watch is "), ("f_only", "only "), ("f_tail", "paid in mind."))),
                {"event.clock_repairs.option.0": {"dissolution": 0}},
                {"zh": "改后：这项选择的崩解 +5 变为 +0；心智 −2 与奖励照旧。",
                 "en": "Altered: this choice's collapse +5 becomes +0; the mind −2 and the reward stay."},
            ),
            TamperVariant(
                "also_lucidity",
                _fragments((("f_lead", "取走这只表，"), ("f_also", "也"), ("f_tail", "会损耗你的清醒度。")),
                           (("f_lead", "Taking this watch is "), ("f_also", "also "), ("f_tail", "paid in lucidity."))),
                {"event.clock_repairs.option.0": {"lucidity": -2}},
                {"zh": "改后：心智 −2 照旧，还额外清醒度 −2——改坏了，看清楚再确认。",
                 "en": "Altered: the mind −2 stays, plus lucidity −2 — a bad edit; read before confirming."},
            ),
        ),
        transitions=(
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6),
            TamperTransition("t_only", "base", "only", "insert", "slot_only", "only", 3, 8),
            TamperTransition("t_also", "base", "also_lucidity", "insert", "slot_also", "also", 4, 10, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_negate": _insert("f_tail", "f_negate"),
            "slot_only": _insert("f_tail", "f_only"),
            "slot_also": _insert("f_tail", "f_also"),
        }),
    ),
    # 7. 玻璃里的第二个房间：规则句（影响 option.1：想象 +4、崩解 +3）
    #    只=免崩解；不=想象换成清醒（整句按「不是想象」读）；也=玻璃里那位也安静下来。
    TamperDefinition(
        text_id="tamper.glass_crack.only",
        target_kind="event",
        definition_id="event.glass_crack",
        region="rule",
        option_id="event.glass_crack.option.1",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "贴上玻璃，留下的"), ("f_tail", "是想象。")),
                           (("f_lead", "Press your hand to the glass; what remains is "), ("f_tail", "imagination."))),
                {},
                {"zh": "原样：想象力 +4，这项选择另加崩解 +3。", "en": "Unchanged: imagination +4 and collapse +3 from this choice."},
            ),
            TamperVariant(
                "only",
                _fragments((("f_lead", "贴上玻璃，留下的"), ("f_only", "只"), ("f_tail", "是想象。")),
                           (("f_lead", "Press your hand to the glass; what remains is "), ("f_only", "only "), ("f_tail", "imagination."))),
                {"event.glass_crack.option.1": {"dissolution": 0}},
                {"zh": "改后：保留想象力 +4，去掉这项选择自身的崩解 +3；事件基值照常。",
                 "en": "Altered: keeps imagination +4 and drops this choice's own collapse +3; the event base still applies."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_lead", "贴上玻璃，留下的"), ("f_negate", "不"), ("f_tail", "是想象。")),
                           (("f_lead", "Press your hand to the glass; what remains is "), ("f_negate", "not "), ("f_tail", "imagination."))),
                {"event.glass_crack.option.1": {"imagination": 0, "lucidity": 4}},
                {"zh": "改后：留下的换成清醒度 +4；想象力 +4 不再给，崩解 +3 照常。",
                 "en": "Altered: what remains becomes lucidity +4; the imagination +4 is gone, collapse +3 still applies."},
            ),
            TamperVariant(
                "also_mind",
                _fragments((("f_lead", "贴上玻璃，留下的"), ("f_also", "也"), ("f_tail", "是想象。")),
                           (("f_lead", "Press your hand to the glass; what remains is "), ("f_also", "also "), ("f_tail", "imagination."))),
                {"event.glass_crack.option.1": {"mind": 2}},
                {"zh": "改后：想象力 +4 照旧，玻璃里那个房间也安静下来：心智 +2。",
                 "en": "Altered: keeps imagination +4; the room behind the glass settles too: mind +2."},
            ),
        ),
        transitions=(
            TamperTransition("t_only", "base", "only", "insert", "slot_only", "only", 3, 8),
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6),
            TamperTransition("t_also", "base", "also_mind", "insert", "slot_also", "also", 4, 10),
        ),
        slots_by_language=_slots({
            "slot_only": _insert("f_tail", "f_only"),
            "slot_negate": _insert("f_tail", "f_negate"),
            "slot_also": _insert("f_tail", "f_also"),
        }),
    ),
    # 8. 齿轮停下的午后：行动选项（影响 option.1：清醒 +3、崩解 +4）
    #    删除「再」=减量；只=整句改写「只转一圈」免崩解；也=它替你转（整句改写）。
    TamperDefinition(
        text_id="tamper.gear_afternoon.turn",
        target_kind="event",
        definition_id="event.gear_afternoon",
        region="option",
        option_id="event.gear_afternoon.option.1",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_let", "让它"), ("f_again", "再"), ("f_turn", "转一圈")),
                           (("f_let", "Let it turn"), ("f_again", " once more"), ("f_turn", ""))),
                {},
                {"zh": "原样：清醒度 +3，这项选择崩解 +4。", "en": "Unchanged: lucidity +3 and collapse +4 from this choice."},
            ),
            TamperVariant(
                "plain",
                _fragments((("f_let", "让它"), ("f_turn", "转一圈")),
                           (("f_let", "Let it turn"), ("f_turn", ""))),
                {"event.gear_afternoon.option.1": {"lucidity": 2, "dissolution": 2}},
                {"zh": "改后：清醒度恢复由 3 变为 2，这项选择的崩解由 +4 变为 +2。",
                 "en": "Altered: the lucidity restore goes from 3 to 2 and this choice's collapse from +4 to +2."},
            ),
            TamperVariant(
                "only_once",
                _fragments((("f_let", "让它"), ("f_only", "只"), ("f_turn", "转一圈")),
                           (("f_let", "Let it turn "), ("f_only", "only "), ("f_turn", "once"))),
                {"event.gear_afternoon.option.1": {"dissolution": 0}},
                {"zh": "改后：只转一圈——清醒度 +3 照旧，这项选择的崩解 +4 变为 +0。",
                 "en": "Altered: one turn only — keeps lucidity +3; this choice's collapse +4 becomes +0."},
            ),
            TamperVariant(
                "for_you",
                _fragments((("f_let", "让它"), ("f_also", "也"), ("f_turn", "替你转一圈")),
                           (("f_let", "Let it "), ("f_also", "also "), ("f_turn", "turn for you"))),
                {"event.gear_afternoon.option.1": {"mind": 2}},
                {"zh": "改后：清醒度 +3 照旧，它替你转的那一圈让你定下神来：心智 +2；崩解 +4 照常。",
                 "en": "Altered: keeps lucidity +3; the turn it makes for you steadies you: mind +2; collapse +4 still applies."},
            ),
        ),
        transitions=(
            TamperTransition("t_drop_again", "base", "plain", "delete", "slot_drop_again", None, 2, 6),
            TamperTransition("t_only", "base", "only_once", "insert", "slot_only", "only", 3, 8, rewrite=True),
            TamperTransition("t_also", "base", "for_you", "insert", "slot_also", "also", 4, 10, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_drop_again": _delete("f_again"),
            "slot_only": _insert("f_let", "f_only", "after"),
            "slot_also": _insert("f_let", "f_also", "after"),
        }),
    ),
    # 9. 拾荒者：燃烧瓶交易的对白（影响 trade.0：消耗品 3 → 燃烧瓶）
    TamperDefinition(
        text_id="tamper.scrapper.molotov_cost",
        target_kind="npc",
        definition_id="npc.scrapper",
        region="dialogue",
        option_id="npc.scrapper.trade.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "火"), ("f_cost", "要拿消耗品换。")),
                           (("f_lead", "Fire is "), ("f_cost", "traded for consumables."))),
                {},
                {"zh": "原样：这支燃烧瓶照收消耗品 3。", "en": "Unchanged: the molotov still takes 3 consumables."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_lead", "火"), ("f_negate", "不"), ("f_cost", "拿消耗品换。")),
                           (("f_lead", "Fire is "), ("f_negate", "not "), ("f_cost", "traded for consumables."))),
                {"npc.scrapper.trade.0": {"cost": {}}},
                {"zh": "改后：这支燃烧瓶不再收消耗品，其余照旧。",
                 "en": "Altered: the molotov costs no consumables; everything else stays."},
            ),
            TamperVariant(
                "only_cheap",
                _fragments((("f_lead", "火"), ("f_only", "只"), ("f_cost", "拿两件消耗品换。")),
                           (("f_lead", "Fire "), ("f_only", "only "), ("f_cost", "asks for two consumables."))),
                {"npc.scrapper.trade.0": {"cost": {"consumables": 2}}},
                {"zh": "改后：消耗品 3 变为 2，其余照旧。",
                 "en": "Altered: consumables drop from 3 to 2; everything else stays."},
            ),
        ),
        transitions=(
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6, rewrite=True),
            TamperTransition("t_only", "base", "only_cheap", "insert", "slot_only", "only", 3, 8, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_negate": _insert("f_cost", "f_negate"),
            "slot_only": _insert("f_cost", "f_only"),
        }),
    ),
    # 10. 催眠师：清醒换心智上限的对白（影响 trade.0：清醒 12 → 心智上限 +6）
    TamperDefinition(
        text_id="tamper.hypnotist.mind_cap_cost",
        target_kind="npc",
        definition_id="npc.hypnotist",
        region="dialogue",
        option_id="npc.hypnotist.trade.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "清醒"), ("f_cost", "由她收下，换心智上限。")),
                           (("f_lead", "She takes your lucidity "), ("f_cost", "for the wider mind."))),
                {},
                {"zh": "原样：这项交易照收清醒度 12。", "en": "Unchanged: the trade still takes 12 lucidity."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_lead", "清醒"), ("f_negate", "不"), ("f_cost", "由她收下——心智上限照涨。")),
                           (("f_lead", "She does "), ("f_negate", "not "), ("f_cost", "take your lucidity; the wider mind stays."))),
                {"npc.hypnotist.trade.0": {"cost": {}}},
                {"zh": "改后：清醒度 12 不再收，心智上限 +6 照涨，「每人一次」照旧。",
                 "en": "Altered: the 12 lucidity is waived; the mind-cap gain and its one-time limit stay."},
            ),
            TamperVariant(
                "only_half",
                _fragments((("f_lead", "清醒"), ("f_only", "只"), ("f_cost", "收一半——6 点换心智上限。")),
                           (("f_lead", "She takes "), ("f_only", "only "), ("f_cost", "half your lucidity for the wider mind."))),
                {"npc.hypnotist.trade.0": {"cost": {"lucidity": 6}}},
                {"zh": "改后：清醒度 12 变为 6，其余照旧。",
                 "en": "Altered: the lucidity cost drops from 12 to 6; everything else stays."},
            ),
        ),
        transitions=(
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6, rewrite=True),
            TamperTransition("t_only", "base", "only_half", "insert", "slot_only", "only", 3, 8, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_negate": _insert("f_cost", "f_negate"),
            "slot_only": _insert("f_cost", "f_only"),
        }),
    ),
    # 11. 档案员：整理档案交易的对白（影响 trade.1：消耗品 3 → 洞察「双读」）
    TamperDefinition(
        text_id="tamper.archivist.filing_cost",
        target_kind="npc",
        definition_id="npc.archivist",
        region="dialogue",
        option_id="npc.archivist.trade.1",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_lead", "档案"), ("f_cost", "要拿三件消耗品整理。")),
                           (("f_lead", "The files "), ("f_cost", "are set in order for three consumables."))),
                {},
                {"zh": "原样：这项整理照收消耗品 3。", "en": "Unchanged: the filing still takes 3 consumables."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_lead", "档案"), ("f_negate", "不"), ("f_cost", "用再拿消耗品整理。")),
                           (("f_lead", "The files are "), ("f_negate", "not "), ("f_cost", "filed for consumables anymore."))),
                {"npc.archivist.trade.1": {"cost": {}}},
                {"zh": "改后：这项整理不再收消耗品，洞察照给，「每人一次」照旧。",
                 "en": "Altered: the filing costs no consumables; the insight and its one-time limit stay."},
            ),
            TamperVariant(
                "only_cheap",
                _fragments((("f_lead", "档案"), ("f_only", "只"), ("f_cost", "用两件消耗品整理。")),
                           (("f_lead", "The files are set in order for "), ("f_only", "only "), ("f_cost", "two consumables."))),
                {"npc.archivist.trade.1": {"cost": {"consumables": 2}}},
                {"zh": "改后：消耗品 3 变为 2，其余照旧。",
                 "en": "Altered: consumables drop from 3 to 2; everything else stays."},
            ),
        ),
        transitions=(
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6, rewrite=True),
            TamperTransition("t_only", "base", "only_cheap", "insert", "slot_only", "only", 3, 8, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_negate": _insert("f_cost", "f_negate"),
            "slot_only": _insert("f_cost", "f_only"),
        }),
    ),
    # 12. 灰烬下的打火机：行动选项（影响 option.2：想象力 −5 → 燃烧瓶）
    TamperDefinition(
        text_id="tamper.ash_lighter.free_molotov",
        target_kind="event",
        definition_id="event.ash_lighter",
        region="option",
        option_id="event.ash_lighter.option.2",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_cost", "想象力 −5，"), ("f_deal", "换一支燃烧瓶（投掷引火）")),
                           (("f_cost", "5 imagination, "), ("f_deal", "for a molotov (throw to ignite)"))),
                {},
                {"zh": "原样：花想象力 5，换一支燃烧瓶，占用一次触发。",
                 "en": "Unchanged: 5 imagination for a molotov, one use spent."},
            ),
            TamperVariant(
                "negated",
                _fragments((("f_cost", "不花想象力，"), ("f_deal", "换一支燃烧瓶（投掷引火）")),
                           (("f_cost", "not a spark of imagination, "), ("f_deal", "for a molotov (throw to ignite)"))),
                {"event.ash_lighter.option.2": {"imagination": 0}},
                {"zh": "改后：想象力不再扣，燃烧瓶照给；触发次数照常。",
                 "en": "Altered: no imagination is spent; the molotov and the use count stay."},
            ),
            TamperVariant(
                "only_cheap",
                _fragments((("f_cost", "想象力只花 3 点，"), ("f_deal", "换一支燃烧瓶（投掷引火）")),
                           (("f_cost", "Only 3 imagination, "), ("f_deal", "for a molotov (throw to ignite)"))),
                {"event.ash_lighter.option.2": {"imagination": -3}},
                {"zh": "改后：想象力 −5 变为 −3，其余照旧。",
                 "en": "Altered: the imagination cost drops from 5 to 3; everything else stays."},
            ),
        ),
        transitions=(
            TamperTransition("t_negate", "base", "negated", "insert", "slot_negate", "negate", 2, 6, rewrite=True),
            TamperTransition("t_only", "base", "only_cheap", "insert", "slot_only", "only", 3, 8, rewrite=True),
        ),
        slots_by_language=_slots({
            "slot_negate": _insert("f_cost", "f_negate"),
            "slot_only": _insert("f_deal", "f_only"),
        }),
    ),
    # 13. 药盒的最后一格：行动选项（影响 option.1：过期药 ×2、心智 −2）
    #    「再」有两个合法位置：句首=3 份，句尾=整句改写「再抖出一份」=4 份；不=免心智。
    TamperDefinition(
        text_id="tamper.pill_box.more_pills",
        target_kind="event",
        definition_id="event.pill_box",
        region="option",
        option_id="event.pill_box.option.1",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_label", "把整盒收进口袋"),),
                           (("f_label", "Pocket the whole box"),)),
                {},
                {"zh": "原样：所得 2 份，心智 −2，占用一次触发。", "en": "Unchanged: 2 doses, mind −2, one use spent."},
            ),
            TamperVariant(
                "again",
                _fragments((("f_again", "再"), ("f_label", "把整盒收进口袋")),
                           (("f_label", "Pocket the whole box"), ("f_again", " again"))),
                {"event.pill_box.option.1": {"reward_count": 3}},
                {"zh": "改后：所得由 2 份变为 3 份；心智 −2 与触发次数照常。",
                 "en": "Altered: the doses go from 2 to 3; mind −2 and the use count are unchanged."},
            ),
            TamperVariant(
                "shake",
                _fragments((("f_label", "把整盒收进口袋"), ("f_tail", "，再抖出一份")),
                           (("f_label", "Pocket the whole box"), ("f_tail", " and shake it again for one more"))),
                {"event.pill_box.option.1": {"reward_count": 4}},
                {"zh": "改后：所得由 2 份变为 4 份，仍只结算一次事件使用。",
                 "en": "Altered: the doses go from 2 to 4; the event use is still spent once."},
            ),
            TamperVariant(
                "calm",
                _fragments((("f_label", "把整盒收进口袋"), ("f_tail", "，不伤心智")),
                           (("f_label", "Pocket the whole box"), ("f_tail", "; it does not touch your mind."))),
                {"event.pill_box.option.1": {"mind": 0}},
                {"zh": "改后：所得 2 份照给，这项选择的心智 −2 变为 −0。",
                 "en": "Altered: the 2 doses stay; this choice's mind −2 becomes −0."},
            ),
        ),
        transitions=(
            TamperTransition("t_again", "base", "again", "insert", "slot_again", "again", 5, 14),
            TamperTransition("t_shake", "base", "shake", "insert", "slot_shake", "again", 5, 14, rewrite=True),
            TamperTransition("t_negate", "base", "calm", "insert", "slot_negate", "negate", 2, 6, rewrite=True),
        ),
        slots_by_language=_slots(
            {"slot_again": _insert("f_label", "f_again", "before"),
             "slot_shake": _insert("f_label", "f_tail", "after"),
             "slot_negate": _insert("f_label", "f_tail", "after")},
            {"slot_again": _insert("f_label", "f_again", "after"),
             "slot_shake": _insert("f_label", "f_tail", "after"),
             "slot_negate": _insert("f_label", "f_tail", "after")},
        ),
    ),
    # 14. 倒着下的雨：行动选项（影响 option.0：接一滴，清醒 +2）
    TamperDefinition(
        text_id="tamper.rain_upside_down.also_thunder",
        target_kind="event",
        definition_id="event.rain_upside_down",
        region="option",
        option_id="event.rain_upside_down.option.0",
        initial_variant="base",
        variants=(
            TamperVariant(
                "base",
                _fragments((("f_label", "接一滴"),),
                           (("f_label", "Catch a drop"),)),
                {},
                {"zh": "原样：得到一份所得，清醒度 +2，占用一次触发。",
                 "en": "Unchanged: one reward, lucidity +2, one use spent."},
            ),
            TamperVariant(
                "also_thunder",
                _fragments((("f_label", "接一滴，"), ("f_also", "也"), ("f_tail", "接住一声闷雷")),
                           (("f_label", "Catch a drop, and "), ("f_also", "also "), ("f_tail", "a muffled rumble"))),
                {"event.rain_upside_down.option.0": {"mind": 2}},
                {"zh": "改后：清醒度 +2 照旧，那一声雷让你回过神：心智 +2；触发次数照常。",
                 "en": "Altered: keeps lucidity +2; the muffled thunder steadies you: mind +2; the use count is unchanged."},
            ),
            TamperVariant(
                "again",
                _fragments((("f_again", "再"), ("f_label", "接一滴")),
                           (("f_label", "Catch a drop"), ("f_again", " again"))),
                {"event.rain_upside_down.option.0": {"reward_count": 2}},
                {"zh": "改后：所得多一份（共 2 份）；清醒 +2 与触发次数照常。",
                 "en": "Altered: the reward doubles (2 total); lucidity +2 and the use count are unchanged."},
            ),
        ),
        transitions=(
            TamperTransition("t_again", "base", "again", "insert", "slot_again", "again", 5, 14),
            TamperTransition("t_also", "base", "also_thunder", "insert", "slot_also", "also", 4, 10, rewrite=True),
        ),
        slots_by_language=_slots(
            {"slot_again": _insert("f_label", "f_again", "before"),
             "slot_also": _insert("f_label", "f_also", "after")},
            {"slot_again": _insert("f_label", "f_again", "after"),
             "slot_also": _insert("f_label", "f_also", "after")},
        ),
    ),
)

from .tamper_combinations import extend_tamper_content

TAMPER_DEFINITIONS = extend_tamper_content(TAMPER_DEFINITIONS)

_DEFINITIONS_BY_TEXT_ID: dict[str, TamperDefinition] = {d.text_id: d for d in TAMPER_DEFINITIONS}
_DEFINITIONS_BY_TARGET: dict[tuple[str, str], tuple[TamperDefinition, ...]] = {}
for _definition in TAMPER_DEFINITIONS:
    _key = (_definition.target_kind, _definition.definition_id)
    _DEFINITIONS_BY_TARGET[_key] = _DEFINITIONS_BY_TARGET.get(_key, ()) + (_definition,)


def definition_for(text_id: str) -> TamperDefinition | None:
    """按固定文本 ID 取定义；未定义文本不进篡改解释器。"""
    return _DEFINITIONS_BY_TEXT_ID.get(text_id)


def definitions_for(target_kind: str, definition_id: str) -> tuple[TamperDefinition, ...]:
    """某个 NPC／事件类型上开放的全部篡改位置。"""
    return _DEFINITIONS_BY_TARGET.get((target_kind, definition_id), ())


def compose_text(variant: TamperVariant, language: str) -> str:
    """把变体片段拼成该语言的完整正文。"""
    return "".join(fragment.text for fragment in variant.fragments(language))


def word_label(word_id: str, language: str) -> str:
    word = WORD_BY_ID.get(word_id)
    return word.label(language) if word else word_id


_TRANSLATIONS_REGISTERED = False


def register_tamper_translations() -> None:
    """把「选项区域」改后的标签登记进英文包（实施计划 Task 2 Step 3）。

    内部仍以中文为键：改后标签由该变体的中文片段拼成，英文必须是同一变体英文
    片段的拼接结果，两边一次登记，避免翻译后的标签参与记账。
    """
    global _TRANSLATIONS_REGISTERED
    if _TRANSLATIONS_REGISTERED:
        return
    _TRANSLATIONS_REGISTERED = True
    from ..i18n import LANGUAGE_PACKS

    pack = LANGUAGE_PACKS.setdefault("en", {})
    for definition in TAMPER_DEFINITIONS:
        if definition.region != "option":
            continue
        for variant in definition.variants:
            source = compose_text(variant, "zh")
            target = compose_text(variant, "en")
            if source and target and source != target:
                pack.setdefault(source, target)
