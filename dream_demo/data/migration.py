"""迁移开关（§15 P1「迁移阶段用显式内容开关禁用未转换定义，不运行新旧结算两套协议」）。

一个功能族一旦有了场景实现（`SCENE_DEFINITIONS` 里带 `family` 的定义），它那几个
还没迁走的旧事件短名就不再进主梦投放池——同一族的同一行为不能在同一层既由场景解释器
结算、又由旧事件的文字协议结算。开关的状态由「这一族有没有场景」推出，不靠人记得去翻：
新增一族场景，那一族的旧事件当场变暗；族还没转换，旧事件照常投放。

未转换**族**的旧事件不在这里变暗：它们各自只跑旧协议一条路，属于 §8 的逐批替换（P2）。
结构绑定事件（`mapgen/vaults` 的 `placement.vault.event`）与梦中梦专属事件同样不在这里
变暗——它们是随具体层型盖章的作者摆放，关掉只会留下一个没有交互的石台。它们自
2026-10-27 起与随机零散事件**共用**每层名额（结构先占额、随机补余额），但仍不经本开关。
"""

from __future__ import annotations

from typing import Any, Mapping

from .scenes import SCENE_DEFINITIONS

#: §8 功能族 → 该族待替换的旧事件短名（spec §8 表格的机器可读副本）。
#: 逐批迁移时改这张表：某族换成场景实现后，表里剩下的短名自动退出投放池。
FAMILY_LEGACY_EVENTS: dict[str, tuple[str, ...]] = {
    "S01": ("event.coffee_ring", "event.silent_ticket", "event.last_train_window",
            "event.vault_route_board"),
    "S02": ("event.attic_staircase", "event.wardrobe_door", "event.doors_within",
            "event.vault_return_loop"),
    "S03": ("event.glass_crack", "event.dream_bottle"),
    "S04": ("event.missing_screw", "event.model_lamp", "event.vault_repair_desk"),
    "S05": ("event.broken_meter", "event.gear_afternoon", "event.clock_repairs"),
    "S06": ("event.radio_rain", "event.static_radio", "event.midnight_broadcast"),
    "S07": ("event.fog_organ", "event.rain_upside_down", "event.wet_score"),
    "S08": ("event.empty_score", "event.static_choir", "event.vault_rehearsal"),
    "S09": ("event.editor_note", "event.silent_library", "event.torn_library",
            "event.vault_seed_ledger"),
    "S10": ("event.rusty_faucet", "event.bath_tide", "event.tide_clock",
            "event.swimming_furniture"),
    "S11": ("event.ash_lighter", "event.toolbox_grave"),
    "S12": ("event.polaroid_wall", "event.photo_booth", "event.blank_gallery"),
    "S13": ("event.post_to_waking", "event.wet_letterbox", "event.dream_post_office"),
    "S14": ("event.night_ward_round", "event.vault_quiet_ward", "event.pill_box"),
    "S15": ("event.tape_line", "event.stargazer_desk"),
    "S16": ("event.sunken_bell", "event.tide_of_names", "event.first_echo"),
    "S17": ("event.lost_luggage", "event.night_stand", "event.scrapper_case"),
    "S18": ("event.dry_fountain",),
    "S19": ("event.mirror_interview", "event.star_clearance", "event.wax_tea_party"),
    "S20": ("event.mirror_rehearsal", "event.puppet_rehearsal"),
    "S21": ("event.elevator_music",),
    "S22": ("event.dream_balloon", "event.paper_moon"),
    "S23": ("event.lens_exchange",),
    "S24": ("event.vault_circuit_log",),
    # S25：珍品机会一族（2026-10-22 A2 P5，方案 §6.1）。三个事件不是「待替换的
    # 旧事件」——它们是这一族**新写**的三个深度档（22／24／26 层各一次高成本
    # 机会）。这一族还没有场景实现，所以不转换、不变暗；它们也不进主梦轮转池
    # （见 data/events.py::spawnable_event_ids 的 treasure. 前缀过滤），
    # 只由 core/generation.py 在对应深度带按作者摆放投放。
    "S25": ("treasure.breach", "treasure.storm", "treasure.dawn"),
}


def converted_families() -> frozenset[str]:
    """已经有场景实现的功能族——场景定义本身就是转换证明。"""
    return frozenset(str(entry["family"]) for entry in SCENE_DEFINITIONS.values()
                     if entry.get("family"))


def held_event_ids() -> frozenset[str]:
    """转换族里尚未迁移的旧事件：主梦投放池不再产出它们。"""
    families = converted_families()
    return frozenset(event_id for family, event_ids in FAMILY_LEGACY_EVENTS.items()
                     if family in families for event_id in event_ids)


def is_held(event_id: str) -> bool:
    return event_id in held_event_ids()


#: 旧「计数型」任务（§7.2 来源改造批次，2026-10-11）：定义已删或已接实例模板。
#: 旧档里这些任务「接取时刻」的计数进度无从折算，读档时退回未接取；
#: 拾荒的账目已由「泵房的狩猎登记」接替，定义整条删除。
LEGACY_COUNTING_QUESTS = frozenset({
    "quest.scrap_tally",
    "quest.press_ink",
    "quest.watcher_pages",
    "quest.lf_marathon",
    "quest.bar_wake",
    "quest.poet_line",
})


def stale_quest_ids(quests: dict[str, Any], bound_definitions: set[str],
                    definitions: Mapping[str, Any]) -> list[str]:
    """旧档里要摘除的任务 id：真实存在过的旧计数单、且没有实例记录。"""
    stale: list[str] = []
    for quest_id, status in quests.items():
        if quest_id not in LEGACY_COUNTING_QUESTS:
            continue
        definition = definitions.get(quest_id) or {}
        if definition.get("template") and quest_id not in bound_definitions:
            stale.append(str(quest_id))
        elif not definition and str(status) == "active":
            stale.append(str(quest_id))
    return stale
