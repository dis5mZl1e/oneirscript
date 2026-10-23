"""内容定义表的加载期校验（NPC／事件重构方案 §2.1、§15 P0）。

两类检查缺一不可：

* :func:`duplicate_literal_keys` —— 静态 AST 扫描源码里的字典字面量重复键。
  Python 只会静默保留最后一个：``event.dry_fountain`` 写过三次 ``uses``，
  运行期读到的表根本看不出「其实写了 2」，导表也只能导出 3。
* :func:`validate_tables` —— 运行期字段校验：未知字段、未知成本／收益类型、
  指向不存在物品／液体／任务／洞察的目标，一律当数据错误报出来，
  而不是等到玩家在货架前付不出钱才发现。

本模块不导入 core／data 的任何表（要校验的表由调用方传入），
以免和 ``core.content`` 这个门面形成循环导入。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable, Mapping

from dream_demo.data.ids import event_option_id, npc_option_id
from dream_demo.data.quests import TARGET_TEMPLATES
from dream_demo.data.scenes import SCENE_DEFINITIONS

DATA_DIR = Path(__file__).resolve().parent

NPC_FIELDS = frozenset({
    "name", "glyph", "color", "integrity", "relation", "trauma_type",
    "vault_only", "description", "dialogue", "options", "spawn_realms",
    # 重构新增（方案 §4.1 身份／派系／立场／能力分开定义）
    "faction", "post", "behavior", "combat", "escort", "itinerary", "important", "free_claim_limit",
})
NPC_OPTION_FIELDS = frozenset({
    'tutorial_only', 'tutorial_control',
    "option_id", "label", "always", "leave", "message", "circuit_hint", "puzzle",
    "enter_realm", "deep_dialogue", "cost", "gain", "accept_quest",
    "complete_quest", "show_if", "gift_set", "service", "intel", "scene_command",
    "reward", "hospital_scene",
})
COST_FIELDS = frozenset({
    "mind", "lucidity", "imagination", "cap", "items", "random_gear",
    "consumables", "liquid", "gear_choice",
})
GAIN_FIELDS = frozenset({
    "item", "insight", "random_insight", "stat", "service", "intel",
    "restore", "restore_all",
})
SHOW_IF_FIELDS = frozenset({"quest_none", "quest_active", "quest_done", "gift_available"})
STAT_FIELDS = frozenset({"max_mind", "max_lucidity", "max_imagination"})
#: §11.3 首版任务扩容预算：心智/清醒 +2～+3，想象 +1～+2。
QUEST_CAP_BUDGET = {"max_mind": 3, "max_lucidity": 3, "max_imagination": 2}
#: 「白给一次」的合法锚点：挂上这些字段的选项由运行期保证只结算一次。
ONE_TIME_GAIN_ANCHORS = ("gift_set", "accept_quest", "complete_quest", "enter_realm",
                         "deep_dialogue", "scene_command", "service")
EVENT_FIELDS = frozenset({
    "event_id", "name", "description", "reward_id", "reward_count", "catalog_id",
    "insight_id", "kind", "uses", "dissolution_reward", "dialogue", "options",
    "family", "scene",
})
EVENT_OPTION_FIELDS = frozenset({
    "option_id", "label", "reward_id", "reward_count", "dissolution", "mind",
    "lucidity", "imagination", "leave", "random_option",
    "enter_realm", "ember_control", "summon_y2k", "epilogue", "scene_command",
})
QUEST_FIELDS = frozenset({"name", "giver", "requirement", "hint", "reward", "scope",
                          "template", "target", "site", "zone", "target_text",
                          "requirement_text", "delivery", "clues",
                          "rewards", "site_effects", "confirm_gain"})
REQUIREMENT_TYPES = frozenset({"item", "liquid", "kill_any", "kill_kind", "events",
                               "depth", "fact", "target_resolve"})
RANDOM_POOLS = frozenset({"摄入物", "易逝物", "交互道具", "携带意象"})


def duplicate_literal_keys(source: str, filename: str = "<source>") -> list[str]:
    """找出源码里字典字面量的重复常量键（含嵌套）。"""
    problems: list[str] = []
    for node in ast.walk(ast.parse(source, filename)):
        if not isinstance(node, ast.Dict):
            continue
        first_seen: dict[Any, int] = {}
        for key in node.keys:
            if key is None or not isinstance(key, ast.Constant):
                continue
            if key.value in first_seen:
                problems.append(
                    f"{filename}:{key.lineno}: 字典键 {key.value!r} 重复"
                    f"（首次出现在第 {first_seen[key.value]} 行；Python 只保留最后一个）"
                )
            else:
                first_seen[key.value] = key.lineno
    return problems


def data_source_files() -> tuple[Path, ...]:
    return tuple(sorted(DATA_DIR.rglob("*.py")))


def scan_data_duplicates(paths: Iterable[Path] | None = None) -> list[str]:
    """扫描 ``dream_demo/data`` 全部源码文件的重复字典键。"""
    problems: list[str] = []
    for path in paths if paths is not None else data_source_files():
        problems.extend(duplicate_literal_keys(path.read_text(encoding="utf-8"), str(path)))
    return sorted(problems)


def _unknown(found: Iterable[str], allowed: frozenset[str], where: str, out: list[str]) -> None:
    for field in found:
        if field not in allowed:
            out.append(f"{where}: 未知字段 {field!r}")


def _check_cost(cost: Mapping[str, Any], where: str, items: Mapping[str, Any],
                liquids: Iterable[str], out: list[str]) -> None:
    liquid_kinds = set(liquids)
    _unknown(cost, COST_FIELDS, where + " cost", out)
    if "items" in cost:
        entry = cost["items"]
        if not (isinstance(entry, (list, tuple)) and len(entry) == 2):
            out.append(f"{where} cost.items 必须是 [物品 id, 数量]")
        elif entry[0] not in items:
            out.append(f"{where} cost.items 指向不存在的物品 {entry[0]!r}")
    if "liquid" in cost:
        entry = cost["liquid"]
        if not (isinstance(entry, (list, tuple)) and len(entry) == 2):
            out.append(f"{where} cost.liquid 必须是 [液体名, 数量]")
        elif entry[0] not in liquid_kinds:
            out.append(f"{where} cost.liquid 指向不存在的液体 {entry[0]!r}")
    if "cap" in cost:
        entry = cost["cap"]
        if not (isinstance(entry, (list, tuple)) and len(entry) == 2 and entry[0] in STAT_FIELDS):
            out.append(f"{where} cost.cap 必须是 {sorted(STAT_FIELDS)} 之一加数量")
    for field in ("random_gear", "consumables", "gear_choice"):
        if field in cost and not (isinstance(cost[field], int) and cost[field] >= 1):
            out.append(f"{where} cost.{field} 必须是 ≥1 的整数")
    for field in ("mind", "lucidity", "imagination"):
        if field in cost and not (isinstance(cost[field], int) and cost[field] >= 1):
            out.append(f"{where} cost.{field} 必须是 ≥1 的整数")


def _check_gain(gain: Mapping[str, Any], where: str, items: Mapping[str, Any],
                insights: Iterable[str], out: list[str], *, paid: bool,
                quest_reward: bool = False) -> None:
    _unknown(gain, GAIN_FIELDS, where + " gain", out)
    if "item" in gain and gain["item"] not in items:
        out.append(f"{where} gain.item 指向不存在的物品 {gain['item']!r}")
    if "insight" in gain and gain["insight"] not in set(insights):
        out.append(f"{where} gain.insight 指向不存在的洞察 {gain['insight']!r}")
    if "stat" in gain:
        entry = gain["stat"]
        if not (isinstance(entry, (list, tuple)) and len(entry) == 2 and entry[0] in STAT_FIELDS):
            out.append(f"{where} gain.stat 必须是 {sorted(STAT_FIELDS)} 之一加数量")
        elif not paid:
            # §11.3：普通对话全部取消永久上限奖励——免费选项只能给情报／服务。
            out.append(f"{where} 免费选项不得给永久上限（{entry[0]} +{entry[1]}）")
        elif quest_reward and int(entry[1]) > QUEST_CAP_BUDGET.get(entry[0], 0):
            # §11.3：重要任务的扩容是「主要报酬之一」，首版心智/清醒 +2～+3、想象 +1～+2。
            out.append(f"{where} 任务报酬的永久上限超出 §11.3 预算"
                       f"（{entry[0]} +{entry[1]}，上限 {QUEST_CAP_BUDGET[entry[0]]}）")


def validate_tables(*, npcs: Mapping[str, Any], events: Iterable[Mapping[str, Any]],
                    quests: Mapping[str, Any], items: Mapping[str, Any],
                    insights: Iterable[str], liquids: Iterable[str] = (),
                    anomaly_ids: Iterable[str] = ()) -> list[str]:
    """校验三张表的字段与目标引用，返回错误列表（空列表＝通过）。"""
    out: list[str] = []
    liquid_kinds = set(liquids)
    insight_names = set(insights)
    anomaly_set = set(anomaly_ids)
    # 任务的两端都得有人开门：接取与兑现由**声明的委托人**自己提供，
    # 否则任务写在簿上却永远接不到／交不掉（§2.1 任务行）。
    quest_accept: dict[str, set[str]] = {}
    quest_complete: dict[str, set[str]] = {}

    for npc_id, definition in npcs.items():
        where = f"npc {npc_id}"
        _unknown(definition, NPC_FIELDS, where, out)
        options = definition.get("options") or ()
        if ('free_claim_limit' in definition and
                (type(definition['free_claim_limit']) is not int or definition['free_claim_limit'] not in (1, 2))):
            out.append(f'{where} free_claim_limit 必须是 1 或 2')
        seen_ids: set[str] = set()
        for position, option in enumerate(options):
            spot = f"{where} 选项[{position}]"
            _unknown(option, NPC_OPTION_FIELDS, spot, out)
            option_id = npc_option_id(npc_id, position, option)
            if option_id in seen_ids:
                out.append(f"{spot} 稳定 ID {option_id!r} 与同一职业的另一项重复"
                           "（记账会串：一次性交易会被当成已完成）")
            else:
                seen_ids.add(option_id)
            if "cost" in option:
                _check_cost(option["cost"], spot, items, liquid_kinds, out)
            if "gain" in option:
                _check_gain(option["gain"], spot, items, insight_names, out,
                            paid=bool(option.get("cost")) or bool(option.get("complete_quest")),
                            quest_reward=bool(option.get("complete_quest")))
            if (option.get("gain") and not option.get("cost")
                    and not any(f in option for f in ONE_TIME_GAIN_ANCHORS)):
                # §2.1「一次性收益不能重复获得」：白给的实物/洞察必须挂在某种
                # 「限领一次」的锚点上（赠品组／任务），否则点一次给一次，
                # 一名向导就能无限印热水。
                out.append(f"{spot} 免费所得没有一次性锚点"
                           "（要么标 gift_set／任务，要么改成纯对话 message）")
            for field in ("accept_quest", "complete_quest"):
                if field in option and option[field] not in quests:
                    out.append(f"{spot} {field} 指向不存在的任务 {option[field]!r}")
            if option.get("accept_quest"):
                quest_accept.setdefault(option["accept_quest"], set()).add(npc_id)
            if option.get("complete_quest"):
                quest_complete.setdefault(option["complete_quest"], set()).add(npc_id)
            show = option.get("show_if") or {}
            _unknown(show, SHOW_IF_FIELDS, spot + " show_if", out)
            for key, quest_id in show.items():
                if key.startswith("quest") and quest_id not in quests:
                    out.append(f"{spot} show_if.{key} 指向不存在的任务 {quest_id!r}")

    seen_events: set[str] = set()
    for event in events:
        event_id = event.get("event_id", "<缺 event_id>")
        where = f"event {event_id}"
        if event_id in seen_events:
            out.append(f"{where}: event_id 重复")
        seen_events.add(event_id)
        _unknown(event, EVENT_FIELDS, where, out)
        seen_event_options: set[str] = set()
        for field in ("reward_id",):
            if event.get(field) and event[field] not in items:
                out.append(f"{where} {field} 指向不存在的物品 {event[field]!r}")
        if event.get("insight_id") and event["insight_id"] not in insight_names:
            out.append(f"{where} insight_id 指向不存在的洞察 {event['insight_id']!r}")
        if "uses" in event and not (isinstance(event["uses"], int) and event["uses"] >= 1):
            out.append(f"{where} uses 必须是 ≥1 的整数")
        for position, option in enumerate(event.get("options") or ()):
            spot = f"{where} 选项[{position}]"
            _unknown(option, EVENT_OPTION_FIELDS, spot, out)
            option_id = event_option_id(event_id, position, option)
            if option_id in seen_event_options:
                out.append(f"{spot} 稳定 ID {option_id!r} 与同一事件的另一项重复")
            seen_event_options.add(option_id)
            if option.get("reward_id") and option["reward_id"] not in items:
                out.append(f"{spot} reward_id 指向不存在的物品 {option['reward_id']!r}")
            pool = (option.get("random_option") or {}).get("pool")
            if pool is not None and pool not in RANDOM_POOLS:
                out.append(f"{spot} random_option.pool {pool!r} 不是已知类别")

    for quest_id, quest in quests.items():
        where = f"quest {quest_id}"
        _unknown(quest, QUEST_FIELDS, where, out)
        requirement = quest.get("requirement") or {}
        kind = requirement.get("type")
        if kind not in REQUIREMENT_TYPES:
            out.append(f"{where} requirement.type {kind!r} 不是已知类型")
        if kind == "item" and requirement.get("item") not in items:
            out.append(f"{where} requirement.item 指向不存在的物品 {requirement.get('item')!r}"
                       "（液体不是物品，请用 type=liquid）")
        if kind == "liquid" and requirement.get("liquid") not in liquid_kinds:
            out.append(f"{where} requirement.liquid 指向不存在的液体 {requirement.get('liquid')!r}")
        if kind == "kill_kind" and anomaly_set and requirement.get("target") not in anomaly_set:
            out.append(f"{where} requirement.target 指向不存在的异象 {requirement.get('target')!r}")
        if kind == "depth" and not isinstance(requirement.get("depth"), int):
            # 深度目标是**绝对层号**；漏写 depth 会被当成 count=1，在第 1 层直接白送。
            out.append(f"{where} requirement.type=depth 必须给出整数 requirement.depth")
        if quest.get("template"):
            # 目标实例任务（§7.1）：场所与解法口径都要指得出真东西，开不了空单。
            if quest["template"] not in TARGET_TEMPLATES:
                out.append(f"{where} template {quest['template']!r} 不是 §7.1 的六类目标模板")
            if quest["template"] == "investigate" and not quest.get("clues"):
                out.append(f"{where} template=investigate 必须给出 clues（线索名单）")
            # 回收／递送允许「交付给委托人本人」（delivery: giver）不开场所；
            # 其余模板的验证、结算与进度都挂在场景设施上，必须有 site。
            needs_site = not (quest["template"] == "recover_deliver"
                              and quest.get("delivery") == "giver")
            site = SCENE_DEFINITIONS.get(quest.get("site", ""))
            if needs_site and site is None:
                out.append(f"{where} site 指向不存在的场景定义 {quest.get('site')!r}")
            elif site is not None and quest.get("zone") and quest["zone"] not in (site.get("safe_zones") or ()):
                out.append(f"{where} zone {quest['zone']!r} 不在该场景的持续安全记账里")
            for name, entry in (quest.get("rewards") or {}).items():
                _check_gain(entry.get("gain") or {}, f"{where} rewards.{name}",
                            items, insight_names, out, paid=True, quest_reward=True)
            if quest.get("confirm_gain"):
                _check_gain(quest["confirm_gain"], f"{where} confirm_gain",
                            items, insight_names, out, paid=True, quest_reward=True)
        giver = quest.get("giver")
        if giver:
            if giver not in quest_accept.get(quest_id, set()):
                out.append(f"{where} 无人接取：委托人 {giver} 的选项表里没有 accept_quest")
            if giver not in quest_complete.get(quest_id, set()):
                out.append(f"{where} 无人兑现：委托人 {giver} 的选项表里没有 complete_quest")
        if quest.get("giver") and quest["giver"] not in npcs:
            out.append(f"{where} giver 指向不存在的 NPC {quest['giver']!r}")

    return out


def validate_or_raise(**tables: Any) -> None:
    """有数据错误就直接抛出来——不带着坏表进游戏，也不带着坏表导总表。"""
    problems = scan_data_duplicates() + validate_tables(**tables)
    problems.extend(validate_tamper_tables(tables.get("npcs") or {}, tables.get("events") or ()))
    if problems:
        raise ValueError("内容定义表校验未通过：\n" + "\n".join(f"  - {line}" for line in problems))


def validate_tamper_tables(npcs: Mapping[str, Any], events: Iterable[Mapping[str, Any]]) -> list[str]:
    """篡改表单独校验：变体、位置与影响选项都必须指得出真东西。"""
    from dream_demo.data.tamper_validation import validate_tamper_definitions
    from dream_demo.data.tampering import TAMPER_DEFINITIONS

    return validate_tamper_definitions(TAMPER_DEFINITIONS, npcs=npcs, events=events)

