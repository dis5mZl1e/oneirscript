"""任务实例（重构方案 §7.1／§7.3）：进度只认接取之后针对目标实例的真实事实。

「本局累计解决了几只」把整局统计当成了任务记录：先在别的层屠一遍图，再回到登记员
面前就能一口气补领所有完整狩猎奖励。这里改成**实例绑定**——接活时锁定一个真实存在
的 ``target_uid`` 与场所，交付时问世界记录「这一位在接取之后有没有被解决、按哪条
允许的解法解决」，问不出来就不结。

三条硬边界：

* 只读 :mod:`dream_demo.world.facts` 与设施记录，不调用任何行动入口（§10.3）；
  结算产生的改变全部走既有公共结算函数。
* 一次性结算键存在世界记录里（``ledger.settled_tasks``），回旧层、换交付口都再领
  不出第二份。
* 「事前已经解决」不等于没发生：它单独成一条**确认现场**解法，只给小额确认收益。
"""

from __future__ import annotations

from typing import Any

from ..data.quests import QUEST_DEFINITIONS, TARGET_TEMPLATES
from ..data.scenes import SCENE_DEFINITIONS
from ..i18n import tr
from . import facts
from .relations import player_uid
from .scenes import ANCHOR_LABELS as LAYOUT_LABELS, threat_target

#: 一条任务的归属（§7.3）。走通完整解法的给完整报酬，确认现场只给确认收益。
FULL_RESOLUTIONS = ("击败", "诱离封守", "环境修复", "完成交付", "调查成立")
CONFIRM_RESOLUTION = "确认现场"

#: 已实现解法器的模板。其余模板留在表里当口径，但不允许开空单。
#: ``fix_environment``（§7.1 模板 4「指定区域达到可观察状态」）复用同一套
#: ``hold:<zone>`` safety 事实作证，不引入第二套进度口径。
#: ``recover_deliver``（§7.1 模板 3「回收／递送」）认两种交付点：
#: ``delivery: "giver"``＝交付给委托人本人（液体倒托盘／具名记录进行囊），
#: 其余照 ``site`` 场所绑；进度读真实行囊与托盘，交付扣除在同一个事务里。
#: ``investigate``（§7.1 模板 5「调查／辨认」）读场所的 ``report:`` 线索事实
#: （``cause_uid=clue:<名>``），线索由场景命令的效果字段逐条立起来。
IMPLEMENTED_TEMPLATES = frozenset({"threat", "fix_environment",
                                   "recover_deliver", "investigate"})

#: 同时挂着的未完成任务上限（2026-10-12 玩家定稿）：进行中与待交付都占位。
#: 已完结（交付/放弃）不占；上限只在**接取新单**时检查，不回收存量。
ACTIVE_TASK_LIMIT = 5


def task_uid(state: Any, quest_id: str) -> str:
    """实例 ID（§13.2）：本局 + 定义。定义本身带委托人，同职业两位不会串单。"""
    return f"{state.run_uid}|{quest_id}"


def lookup(state: Any, quest_id: str) -> Any:
    """已接取任务的实例记录（没接过时返回 None）。"""
    return state.world_ledger.tasks.get(task_uid(state, quest_id))


def template_of(quest_id: str) -> str:
    return (QUEST_DEFINITIONS.get(quest_id) or {}).get("template", "")


def instance_supported(quest_id: str) -> bool:
    """这条任务是不是「目标实例」口径的任务（旧的计数型任务照原路走）。"""
    return template_of(quest_id) in IMPLEMENTED_TEMPLATES


def _site(state: Any, quest: dict[str, Any]) -> Any:
    """本层那处场所设施记录；不在本层就没有可验证的目标（§12.1）。"""
    key = state.layer_key()
    for record in state.world_ledger.facilities.values():
        if record.layer_key == key and record.definition_id == quest.get("site"):
            return record
    return None


def _site_definition(quest: dict[str, Any]) -> dict[str, Any]:
    return SCENE_DEFINITIONS.get(quest.get("site", "")) or {}


def bind(state: Any, quest_id: str, npc: Any) -> tuple[Any, str]:
    """接取时绑实例：场所与目标必须都真实存在，否则这一单不开。

    返回 ``(记录, 拒绝原因)``。已经绑过的直接给回同一条记录——同一定位在一局里
    只有一份实例，接活按钮按第二次不会又生出一只目标。

    ``recover_deliver`` 且定义声明 ``delivery: "giver"`` 的是例外：交付点就是
    委托人本人（托盘／当面点收），不要求本层恰好滚出过某处场所——报童站在哪里，
    哪里就能开单。
    """
    quest = QUEST_DEFINITIONS.get(quest_id) or {}
    if quest.get("template") not in IMPLEMENTED_TEMPLATES:
        return None, tr("这项任务的解法这里还认不出来。")
    uid = task_uid(state, quest_id)
    existing = state.world_ledger.tasks.get(uid)
    if existing is not None:
        return existing, ""
    active = sum(1 for entry in state.world_ledger.tasks.values()
                 if entry.status in ("进行中", "待交付"))
    if active >= ACTIVE_TASK_LIMIT:
        return None, tr("手头已经挂着 {n} 单没交的任务——先交付或放弃一单再来。",
                        n=ACTIVE_TASK_LIMIT)
    site = _site(state, quest)
    deliver_to_giver = (quest.get("template") == "recover_deliver"
                        and quest.get("delivery") == "giver")
    if site is None and not deliver_to_giver:
        return None, tr("这一层没有出过事的{name}——登记员不给空单。",
                        name=tr(_site_definition(quest).get("name", quest.get("site", ""))))
    record = state.world_ledger.task(uid, quest_id, npc=npc.id,
                                     target_uid=threat_target(state, site) if site is not None else "",
                                     site_uid=site.scene_uid if site is not None else "",
                                     layer_key=state.layer_key(),
                                     accepted_mark=int(state.world_ledger.seq),
                                     accepted_time=int(state.time))
    record.resolution = resolution(state, record)
    record.status = "待交付" if record.resolution else "进行中"
    return record, ""


def abandon(state: Any, task_uid: str) -> Any:
    """Close an accepted commission without rewards, world time, or realm changes."""
    from ..core.entities import ActionResult

    record = state.world_ledger.tasks.get(task_uid)
    if (record is None or record.status not in ("进行中", "待交付")
            or state.world_ledger.has_settled(task_uid)):
        return ActionResult(False, tr("这项委托已失效，不能放弃。"))
    record.status = "已放弃"
    # The dialogue compatibility cache must not offer this commission again.
    if hasattr(state, "quests"):
        state.quests[record.definition_id] = "abandoned"
    return ActionResult(True, tr("已放弃委托；腾出一个委托名额，不领取报酬。"),
                        {"task_uid": task_uid})


def resolution(state: Any, record: Any) -> str:
    """这一单现在按哪条允许的解法成立（空串＝还没成立）。

    顺序是「完整解法优先」：接取之后玩家亲手解决 → 击败；把院子看住了 → 诱离封守；
    只剩「那位确实不在了」这一条事实 → 确认现场（含接活前就被清掉、以及异象互杀）。
    环境修复任务没有「那位」，只看场所那段 ``hold:`` 安全事实是否在接取之后立住。
    回收／交付任务看真实行囊与托盘（交付扣除与达标检查在同一个事务里）；调查任务
    看场所的线索事实是否在接取之后逐条立住。
    """
    template = template_of(record.definition_id)
    if template == "fix_environment":
        return "环境修复" if _held_out(state, record) else ""
    if template == "recover_deliver":
        return "完成交付" if _delivery_ready(state, record) else ""
    if template == "investigate":
        return "调查成立" if _clues_found(state, record) else ""
    if _defeated(state, record):
        return "击败"
    if _held_out(state, record):
        return "诱离封守"
    if _removed(state, record):
        return CONFIRM_RESOLUTION
    return ""


def _defeated(state: Any, record: Any) -> bool:
    """玩家归因的解决：亲手击败与自己造成的环境伤害都算（§7.3）。"""
    if not record.target_uid:
        return False
    return bool(facts.since_accept(state, record.accepted_mark, kind="remove",
                                   target_uid=record.target_uid,
                                   actor_uid=player_uid(state)))


def _held_out(state: Any, record: Any) -> bool:
    """引出来、封住口、连着看住若干世界回合——由场所那条 ``safety`` 事实作证。"""
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    zone = quest.get("zone", "")
    if not zone:
        return False
    return bool(facts.since_accept(state, record.accepted_mark, kind="safety",
                                   target_uid=record.site_uid,
                                   cause_uid=f"hold:{zone}"))


def _removed(state: Any, record: Any) -> bool:
    """目标确实被从地图上抹掉了（不看归因，也不看时刻）。"""
    if not record.target_uid:
        return False
    return bool(state.world_ledger.facts_where(kind="remove",
                                               target_uid=record.target_uid))


def _delivery_amount(state: Any, quest_id: str) -> int:
    """交付物此刻的真实持有量（液体读委托人托盘、具名记录读行囊）。"""
    from ..core.content import quest_liquid_held

    quest = QUEST_DEFINITIONS.get(quest_id) or {}
    requirement = quest.get("requirement") or {}
    kind = requirement.get("type")
    if kind == "liquid":
        return int(quest_liquid_held(state, quest_id))
    if kind == "item":
        item_id = requirement.get("item", "")
        return sum(entry.quantity for entry in state.inventory
                   if entry.definition_id == item_id)
    return 0


def _delivery_ready(state: Any, record: Any) -> bool:
    """回收／递送：交付物此刻真实在手（§7.1 模板 3）。"""
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    requirement = quest.get("requirement") or {}
    return _delivery_amount(state, record.definition_id) >= int(requirement.get("count", 1))


def _clue_found(state: Any, record: Any, name: str) -> bool:
    """一条线索=场所的一条 ``report`` 事实（``cause_uid=clue:<名>``）。"""
    return bool(facts.since_accept(state, record.accepted_mark, kind="report",
                                   target_uid=record.site_uid,
                                   cause_uid=f"clue:{name}"))


def _clues_found(state: Any, record: Any) -> bool:
    """调查／辨认：定义列出的线索在接取之后逐条立住（§7.1 模板 5）。"""
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    clues = tuple(quest.get("clues") or ())
    if not clues:
        return False
    return all(_clue_found(state, record, name) for name in clues)


def progress(state: Any, record: Any) -> tuple[int, int]:
    """(已完成量, 需求量)：交付类读真实持有量、调查类读立住的线索数，其余一条账。"""
    template = template_of(record.definition_id)
    if template == "recover_deliver":
        quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
        need = max(1, int((quest.get("requirement") or {}).get("count", 1)))
        return min(_delivery_amount(state, record.definition_id), need), need
    if template == "investigate":
        quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
        clues = tuple(quest.get("clues") or ())
        total = max(1, len(clues))
        if record.site_uid:
            found = sum(1 for name in clues if _clue_found(state, record, name))
        else:
            found = 0
        return found, total
    return (1, 1) if resolution(state, record) else (0, 1)


def status_text(state: Any, record: Any) -> str:
    """面板/交付失败用的一句话：现在缺什么，说清楚（§14）。"""
    kind = resolution(state, record)
    if kind == CONFIRM_RESOLUTION:
        return tr("那一位已经不在了，但不是你办的——只认一次确认现场。")
    if kind:
        return tr("已成立：{kind}", kind=tr(kind))
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    site = _site_definition(quest)
    template = template_of(record.definition_id)
    if template == "recover_deliver":
        have, need = progress(state, record)
        return tr("还差：{req}（{have}/{need}）——备好了当面点收。",
                  req=tr(quest.get("requirement_text", "")), have=have, need=need)
    if template == "investigate":
        have, need = progress(state, record)
        return tr("还差：在{name}把线索一条条查清（{have}/{need}）。",
                  name=tr(site.get("name", "")), have=have, need=need)
    if template == "fix_environment":
        if quest.get("target_text"):
            # 定义里写明了「还差什么」（如候车厅铺位）：用任务自己的话，别套灯圈口径。
            return tr("还差：{req}。", req=tr(quest.get("target_text", "")))
        return tr("还差：把{name}点亮、环内清干净，让{zone}连着 {n} 个世界回合"
                  "没有火、没有失控意识踩进去。",
                  name=tr(site.get("name", "")),
                  zone=tr(LAYOUT_LABELS.get(quest.get("zone", ""), quest.get("zone", ""))),
                  n=int(site.get("hold_rounds", 3)))
    return tr("两条都还差：当场解决那一位，或把它引出院子、放下侧门挡板，"
              "让{name}连着 {n} 个世界回合没有失控意识踩进去。",
              name=tr(site.get("name", "")),
              n=int(site.get("hold_rounds", 3)))


def reward_gain(state: Any, record: Any, option: dict[str, Any]) -> dict[str, Any]:
    """所选报酬；确认现场一律换成小额确认收益（§7.3「只提供小额确认收益」）。"""
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    if record.resolution == CONFIRM_RESOLUTION:
        return dict(quest.get("confirm_gain") or {})
    rewards = quest.get("rewards") or {}
    chosen = rewards.get(option.get("reward", ""))
    return dict((chosen or {}).get("gain") or option.get("gain") or {})


def refusal(state: Any, record: Any, option: dict[str, Any]) -> str:
    """交付前的整笔检查：已经销过账、归属没成立、场所不在这层，都在这儿挡住。"""
    ledger = state.world_ledger
    if record.status == "已放弃":
        return tr("这一单已经放弃，不能交付。")
    if ledger.has_settled(record.task_uid) or record.status == "已结算":
        return tr("这一单已经销过账了——回旧层也再领不出第二份。")
    kind = resolution(state, record)
    if not kind:
        return tr("还没达成：{why}", why=status_text(state, record))
    record.resolution = kind
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    if (kind in FULL_RESOLUTIONS
            and (quest.get("site_effects") or {}).get(option.get("reward", ""))
            and _site_of(state, record) is None):
        return tr("要拿到{name}的使用权，得回到它那一层的门口——这一层办不了。",
                  name=tr(_site_definition(quest).get("name", "")))
    return ""


def settle(state: Any, record: Any, option: dict[str, Any]) -> list[str]:
    """一次性结算：记账、写事实、兑现场所效果。调用方已确认 :func:`refusal` 为空。"""
    ledger = state.world_ledger
    ledger.settled_tasks[record.task_uid] = record.resolution
    record.status = "已结算"
    record.reward = str(option.get("reward", ""))
    facts.record(state, "settle", actor_uid=player_uid(state),
                 target_uid=record.task_uid, position=(state.player.x, state.player.y),
                 owner_uid=record.giver_uid, cause_uid=record.task_uid,
                 source_kind="quest", before="待交付", after=record.resolution,
                 amount=1)
    messages = _apply_site_effects(state, record, option)
    # 声望（§4.3）：走通完整解法才算「任务完成」，委托人所在派系 +1；
    # 确认现场只是小额确认收益，不动群体账本。once_key=task_uid 保证
    # 同一实例只结算一次声望（重复兑现在 refusal/一次性键处已被挡，这里是双保险）。
    message = _reward_reputation(state, record)
    if message:
        messages.append(message)
    return messages


def _reward_reputation(state: Any, record: Any) -> str | None:
    from ..data import factions
    from . import relations

    if record.resolution not in FULL_RESOLUTIONS:
        return None
    actor = state.world_ledger.actor(record.giver_uid)
    faction_id = factions.faction_of(actor.npc_kind) if actor is not None else None
    if faction_id is None:
        return None
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    return relations.adjust_reputation(
        state, faction_id, factions.TASK_REWARD_NORMAL,
        tr("完成委托「{quest}」", quest=tr(quest.get("name", record.definition_id))),
        once_key=f"quest:{record.task_uid}",
    )


def _site_of(state: Any, record: Any) -> Any:
    site = state.world_ledger.facilities.get(record.site_uid)
    if site is None or site.layer_key != state.layer_key():
        return None
    return site


def _apply_site_effects(state: Any, record: Any, option: dict[str, Any]) -> list[str]:
    """报酬里那句「使用权」落到地图上：抬回玩家自己当年放下的那块挡板。

    确认现场只领小额确认收益，不配把人家院子的门权交出去——那一档报酬只有走通
    完整解法（§7.3）才生效。
    """
    if record.resolution not in FULL_RESOLUTIONS:
        return []
    quest = QUEST_DEFINITIONS.get(record.definition_id) or {}
    key = (quest.get("site_effects") or {}).get(option.get("reward", ""))
    if not key:
        return []
    from ..core.scenes import unseal_opening

    site = _site_of(state, record)
    if site is None:
        return []
    position = site.cell(key)
    if position is None or not unseal_opening(state, *position):
        return []
    return [tr("{name}的挡板被抬回去了——这院子现在归你用。",
               name=tr(LAYOUT_LABELS.get(key, key)))]
