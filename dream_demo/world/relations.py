"""对象立场与责任归属（重构方案 §4.4）。

「稳定意识」不再等于「打了也没后果」，但后果也不能是一句凭空的全体敌对。这里把
§4.4 的状态机落成可读、可存、可回归的一段逻辑：

* 立场存在 :class:`~dream_demo.world.ledger.ActorRecord` 上（不是层快照里），
  所以远层重建、重进地图、读档回来的那位还是同一种态度。
* 输入只有一种：``world/facts.py`` 里的行动事实。谁打了谁、谁死了、补偿付了没有，
  都读同一份记录——关系模块自己不判定伤害，也不另开一套计数器。
* 输出是立场变化 + 对应的 ``warn``／``conflict``／``report``／``safety``／``pact``
  ／``settle`` 事实，任务与之后的派系声望（§4.3）都从这些事实里读证据。

三条口径上的硬约束：

1. **蓄意要证据**（§4.4 末段）：只有确认过的直接攻击算蓄意；意外伤害先警告，
   警告之后 :data:`WARN_WINDOW` 个世界回合内**同来源**再犯才升级为严重冲突。
2. **知识有范围**：只有事发时站在目击圈里的角色才知道发生了什么，远处的人不会因为
   一次误伤就共同敌对。
3. **和解要付钱**：解释只在离开追责区域、冷静期过后、危险源移除时才管用；补偿必须
   走真实的资源扣除，不接受口头承诺。警戒状态**不能靠解释抹掉**——否则警告就成了
   白送的一次点击。
"""
from __future__ import annotations

import random
from typing import Any

from ..i18n import tr
from .facts import WITNESS_RADIUS, record, subscribe

#: 立场取值（§4.4 状态机的节点）。
STANCES = ("中立", "警戒", "敌对", "脱离", "和解中")
#: 警告只对「同来源的可避免侵害」生效 6 个世界回合。
WARN_WINDOW = 6
#: 离开追责区域后至少冷静 8 回合，且危险源已移除，才允许解释。
CALM_TURNS = 8
#: 当地追责半径：站在这个圈里当面挑衅不算「已经离开」。
PURSUIT_RADIUS = WITNESS_RADIUS
#: 补偿要价（想象力点数）：严重冲突与致死的价差开，别让杀人比打碎东西便宜。
RESTITUTION_CONFLICT = 4
RESTITUTION_FATAL = 8
#: 服务对哪些立场关闭。警戒只是「防着你」，还做得成生意。
LOCKED_STANCES = ("敌对", "脱离", "和解中")


def player_uid(state: Any) -> str:
    """玩家在世界记录里的稳定身份（跨层、跨存档不变）。"""
    run = getattr(state, "run_uid", "") or getattr(state.player, "id", "player")
    return f"{run}#player"


def uid_of(who: Any) -> str:
    if isinstance(who, str):
        return who
    return str(getattr(who, "actor_uid", "") or getattr(who, "id", ""))


def record_of(state: Any, who: Any):
    ledger = getattr(state, "world_ledger", None)
    if ledger is None:
        return None
    return ledger.actor(uid_of(who))


def stance_of(state: Any, who: Any) -> str:
    entry = record_of(state, who)
    return entry.stance if entry is not None else "中立"


def service_locked(state: Any, who: Any) -> bool:
    """这位现在还肯不肯做买卖（对话层据此挂／摘选项）。"""
    return stance_of(state, who) in LOCKED_STANCES


def dialogue_hint(state: Any, who: Any) -> str:
    """对话面板上的一行态度提示（返回**未翻译的中文模板**，由界面 ``tr()``）。

    立场必须摆在玩家面前，不能只藏在结算里：这一行排在职业台词之前。
    """
    stance = stance_of(state, who)
    if stance == "和解中":
        return "「条件摆在那儿：付了才算翻篇。」"
    if stance == "敌对":
        return "对方挡在工位前，手里掂着东西——这里的服务暂时关了。"
    if stance == "脱离":
        return "对方不再拦着门口，但也没打算做生意：先解释清楚。"
    if stance == "警戒":
        return "对方防着你手上的动作，买卖还是照做。"
    return ""


def _label(state: Any, entry) -> str:
    for actor in state.enemies:
        if getattr(actor, "actor_uid", "") == entry.actor_uid:
            return tr(actor.label)
    return tr("对方")


def _distance(state: Any, entry) -> int:
    return max(abs(int(state.player.x) - entry.x), abs(int(state.player.y) - entry.y))


#: 「危险源已移除」看的是谈话落脚的那一小片：着火半径 2、压着气半径 1。
HAZARD_RADIUS_FLAME = 2
HAZARD_RADIUS_GAS = 1


def _hazard_near(state: Any, entry) -> bool:
    """谈话落脚点还没散的东西（§4.4「危险源已移除」）。

    原先按整个追责圈（半径 8 的 17×17）判，把每一层都有的 ambient 弥散印象
    也算成火场：实玩里玩家已经退到 14 格外、店主周围只有 5 格外的水蒸气，
    解释与赔偿于是永远开不出来——§15 P1 要求「能玩到…和解」就落不了地。
    稳定意识本身不受火与气伤害（材料结算里直接跳过它们），所以这一条判的是
    「这地方还没安静下来」，落在站脚的那几格上。
    """
    for dy in range(-HAZARD_RADIUS_FLAME, HAZARD_RADIUS_FLAME + 1):
        for dx in range(-HAZARD_RADIUS_FLAME, HAZARD_RADIUS_FLAME + 1):
            if not state.inside_board(entry.x + dx, entry.y + dy):
                continue
            cell = state.cell(entry.x + dx, entry.y + dy)
            if cell.flame > 0:
                return True
            if max(abs(dx), abs(dy)) <= HAZARD_RADIUS_GAS and cell.gas > 0:
                return True
    return False


def _set_stance(state: Any, entry, stance: str) -> bool:
    if entry.stance == stance:
        return False
    entry.stance = stance
    entry.stance_since = int(state.time)
    return True


def _spend_action(state: Any) -> None:
    """交涉至少消耗一次行动（§4.4「不能通过反复打开对话停止敌人时间」）。"""
    from ..core.constants import ActionKind

    state._action_time(1, ActionKind.USE)


# ---------------------------------------------------------------- 事实订阅


def observe(state: Any, fact: dict[str, Any]) -> None:
    """事实管道进来的每一条记录都在这里过一遍（§13.1：关系是订阅者）。

    只改立场、只写事实，绝不调用任何会再次结算行动的东西——NPC 的还手、撤退属于
    行为状态（§6.1），由行为层按立场决定，不在回调里当场执行。
    """
    kind = fact.get("kind")
    if kind == "harm":
        _on_harm(state, fact)
    elif kind == "remove":
        _on_remove(state, fact)


def _on_harm(state: Any, fact: dict[str, Any]) -> None:
    entry = state.world_ledger.actor(str(fact.get("target_uid", "")))
    if entry is None or not entry.alive:
        return  # 异象与临时实体没有档案位，不参与关系
    if fact.get("actor_uid") != player_uid(state):
        return  # 不可归属给玩家的伤害（自然扩散、第三方）不记在玩家头上
    grievance = str(fact.get("cause_uid") or fact.get("source_kind") or "unattributed")
    now = int(fact.get("world_time", state.time))
    if fact.get("source_kind") == "direct_attack":
        # 确认过的直接攻击：无需等第二次警告（§4.4「明显定向的攻击」）。
        entry.restitution = max(entry.restitution, RESTITUTION_CONFLICT)
        _escalate(state, entry, fact)
        _inform_witnesses(state, entry, fact)
        return
    if entry.stance == "中立":
        _warn(state, entry, grievance, now)
    elif entry.stance == "警戒":
        repeat = (entry.last_grievance == grievance
                  and now - entry.last_grievance_time <= WARN_WINDOW)
        if repeat:
            entry.restitution = max(entry.restitution, RESTITUTION_CONFLICT)
            _escalate(state, entry, fact)
            _inform_witnesses(state, entry, fact)
        else:
            # 换了来源的另一次事故：重新警告，不直接翻脸（§4.4 只认「同来源」升级）。
            _warn(state, entry, grievance, now)
    else:
        # 已经敌对：意外伤害不再加重，也不重置冷静钟，否则永远冷不完。
        entry.last_grievance = ""


def _on_remove(state: Any, fact: dict[str, Any]) -> None:
    entry = state.world_ledger.actor(str(fact.get("target_uid", "")))
    if entry is None:
        return
    entry.alive = False
    if fact.get("actor_uid") != player_uid(state):
        return
    # 事故致死：关闭当地服务、开出补偿/调查要价，但不按「已确认谋杀」往全派系传。
    entry.restitution = RESTITUTION_FATAL
    before = entry.stance
    _set_stance(state, entry, "敌对")
    record(state, "conflict", actor_uid=entry.actor_uid, target_uid=player_uid(state),
           position=(entry.x, entry.y), owner_uid=entry.actor_uid,
           cause_uid=str(fact.get("fact_uid", "")), source_kind="relation",
           before=before, after="敌对", amount=RESTITUTION_FATAL)
    _inform_witnesses(state, entry, fact)
    state.messages.append(tr("{name}倒下了。站着的人看见了这一幕，这一笔会被人记下。",
                             name=_label(state, entry)))


def _warn(state: Any, entry, grievance: str, now: int) -> None:
    before = entry.stance
    _set_stance(state, entry, "警戒")
    entry.last_grievance = grievance
    entry.last_grievance_time = now
    record(state, "warn", actor_uid=entry.actor_uid, target_uid=player_uid(state),
           position=(entry.x, entry.y), owner_uid=entry.actor_uid, cause_uid=grievance,
           source_kind="relation", before=before, after="警戒")
    state.messages.append(
        tr("{name}把手里的活放下，挡在工位前：「那边不能碰。再有一次我就得躲着你了。」",
           name=_label(state, entry)))


def _escalate(state: Any, entry, fact: dict[str, Any]) -> None:
    before = entry.stance
    _set_stance(state, entry, "敌对")
    record(state, "conflict", actor_uid=entry.actor_uid, target_uid=player_uid(state),
           position=(entry.x, entry.y), owner_uid=entry.actor_uid,
           cause_uid=str(fact.get("fact_uid", "")), source_kind="relation",
           before=before, after="敌对", amount=entry.restitution)
    state.messages.append(
        tr("{name}掂起了防身的东西，把门口让给你——这里的服务暂时关了。",
           name=_label(state, entry)))


def _inform_witnesses(state: Any, entry, fact: dict[str, Any]) -> None:
    """只通知事发时真站在目击圈里的角色（§4.4 责任归属的范围）。"""
    told: list[str] = []
    for uid in fact.get("witness_uids", ()):
        if uid == entry.actor_uid:
            continue
        other = state.world_ledger.actor(str(uid))
        # 异象没有档案位；已经防着你的人不会因为一次通报再升一级。
        if other is None or not other.alive or other.stance != "中立":
            continue
        _set_stance(state, other, "警戒")
        told.append(other.actor_uid)
    if not told:
        return
    record(state, "report", actor_uid=entry.actor_uid, target_uid=player_uid(state),
           position=(entry.x, entry.y), owner_uid=entry.actor_uid,
           cause_uid=str(fact.get("fact_uid", "")), source_kind="relation",
           after="警戒", witness_uids=tuple(told))


# ---------------------------------------------------------------- 时间收敛


def cool_down(state: Any) -> None:
    """世界时刻走过后的立场回落：警告过期、追着你的人退回岗位。

    挂在 ``_advance`` 上按客观回合走，所以「冷静 8 回合」不看玩家按了多少下，
    也不因为读档而倒退。

    这里**不**把「脱离」自动降回中立：§4.4 的状态图是 敌对→脱离→和解中→中立，
    没有 脱离→中立 这条边。走开只能让他不再堵着门口，翻篇要么解释（花一次行动，
    且当地没有危险源）、要么付补偿。实玩探针里退开十几格、等一回合就发现生意
    已经恢复如初——那等于把整台状态机白送给「跑图」这一个动作。
    """
    ledger = getattr(state, "world_ledger", None)
    if ledger is None:
        return
    now = int(state.time)
    for entry in list(ledger.actors.values()):
        if entry.stance == "中立" or now - entry.stance_since < CALM_TURNS:
            continue
        if entry.stance == "警戒":
            name = _label(state, entry)
            _restore(state, entry)
            state.messages.append(tr("{name}重新回到工位上，像打算把这页翻过去。", name=name))
        elif entry.stance in ("敌对", "和解中") and _distance(state, entry) > PURSUIT_RADIUS:
            # 没付的和解条件随时间作废：退回「脱离」，不白送一次中立。
            _set_stance(state, entry, "脱离")
            state.messages.append(tr("{name}退回了自己的岗位，不再堵着门口。",
                                     name=_label(state, entry)))


def _restore(state: Any, entry) -> None:
    """回到中立：清空冤家记录，并留一条 ``safety`` 事实作为证据。"""
    before = entry.stance
    _set_stance(state, entry, "中立")
    entry.last_grievance = ""
    entry.last_grievance_time = 0
    entry.restitution = 0
    record(state, "safety", actor_uid=entry.actor_uid, target_uid=player_uid(state),
           position=(entry.x, entry.y), owner_uid=entry.actor_uid,
           source_kind="relation", before=before, after="中立")


# ---------------------------------------------------------------- 交涉入口


def can_explain(state: Any, who: Any) -> tuple[bool, str]:
    """「解释」这条路的条件：本人已经退出追责（脱离），且当地不再有危险源。

    警戒不可解释——否则 §4.4 的「警告后同源再犯升级」就变成一次免费点击就能抹掉。
    """
    entry = record_of(state, who)
    if entry is None:
        return False, tr("这个人已经不在这里了。")
    if entry.stance == "中立":
        return False, tr("{name}对你没什么意见。", name=_label(state, entry))
    if entry.stance == "警戒":
        return False, tr("{name}只是防着你手上那一下，没什么可解释的。",
                         name=_label(state, entry))
    if entry.stance == "和解中":
        return False, tr("{name}在等你把条件付掉，不是听你说明。",
                         name=_label(state, entry))
    if entry.stance == "敌对":
        return False, tr("{name}还在当面追着你——先离开他的追责圈，等他冷静下来。",
                         name=_label(state, entry))
    if _hazard_near(state, entry):
        return False, tr("火还在烧，{name}不肯靠近谈。先把危险源处理掉。",
                         name=_label(state, entry))
    return True, ""


def can_propose(state: Any, who: Any) -> tuple[bool, str]:
    """「赔偿」这条路的条件：气头过了（敌对满冷静期，或已经脱离），当地安全。

    敌对状态下这是一条**主动**且要付钱的出路：不用等对方自己退回岗位。
    """
    entry = record_of(state, who)
    if entry is None:
        return False, tr("这个人已经不在这里了。")
    if entry.stance in ("中立", "警戒"):
        return False, tr("{name}跟你没什么条件要谈。", name=_label(state, entry))
    if entry.stance == "和解中":
        return False, tr("条件已经开出来了——{name}在等的是付款，不是再谈一次。",
                         name=_label(state, entry))
    if entry.stance == "敌对" and int(state.time) - entry.stance_since < CALM_TURNS:
        return False, tr("{name}还在气头上，现在出价只会被他当成挑衅。",
                         name=_label(state, entry))
    if _hazard_near(state, entry):
        return False, tr("火还在烧，{name}不肯靠近谈。先把危险源处理掉。",
                         name=_label(state, entry))
    return True, ""


def explain(state: Any, who: Any):
    """安全情况下解释原委（§4.4）：脱离追责 + 冷静期后，把敌对降回中立。"""
    from ..core.entities import ActionResult

    entry = record_of(state, who)
    allowed, refusal = can_explain(state, entry)
    if not allowed:
        if refusal:
            state.messages.append(refusal)
        return ActionResult(False, refusal, {"actor": uid_of(entry)})
    name = _label(state, entry)
    _restore(state, entry)
    _spend_action(state)
    message = tr("你解释了原委，{name}点了一下头：「这次算了。」", name=name)
    state.messages.append(message)
    return ActionResult(True, message, {"actor": entry.actor_uid, "stance": "中立"})


def propose_restitution(state: Any, who: Any):
    """提出补偿（敌对/脱离 → 和解中）：开出要价并记账，付不付由玩家决定。"""
    from ..core.entities import ActionResult

    entry = record_of(state, who)
    if entry is None:
        refusal = tr("这个人已经不在这里了。")
        state.messages.append(refusal)
        return ActionResult(False, refusal)
    allowed, refusal = can_propose(state, entry)
    if not allowed:
        state.messages.append(refusal)
        return ActionResult(False, refusal, {"actor": entry.actor_uid})
    if not entry.restitution:
        entry.restitution = RESTITUTION_CONFLICT
    before = entry.stance
    _set_stance(state, entry, "和解中")
    _spend_action(state)
    record(state, "pact", actor_uid=entry.actor_uid, target_uid=player_uid(state),
           position=(entry.x, entry.y), owner_uid=entry.actor_uid,
           source_kind="relation", before=before, after="和解中",
           amount=entry.restitution)
    message = tr("{name}开出了条件：交出 {amount} 点想象力作为补偿，这一页就翻掉。",
                 name=_label(state, entry), amount=entry.restitution)
    state.messages.append(message)
    return ActionResult(True, message, {"actor": entry.actor_uid, "stance": "和解中"})


def restitution_cost(entry) -> dict[str, int]:
    return {"imagination": int(entry.restitution)}


def pay_restitution(state: Any, who: Any):
    """支付并履约（和解中 → 中立）：代价走真实扣除，付不出就整笔拒绝。"""
    from ..core.entities import ActionResult

    entry = record_of(state, who)
    if entry is None or entry.stance != "和解中":
        refusal = tr("{name}还没跟你开出条件。", name=_label(state, entry)) if entry else ""
        if refusal:
            state.messages.append(refusal)
        return ActionResult(False, refusal)
    cost = restitution_cost(entry)
    refusal = state._check_npc_cost(cost)
    if refusal:
        state.messages.append(refusal)
        return ActionResult(False, refusal, {"actor": entry.actor_uid, "refusal": True})
    from ..data.ids import stable_seed

    rng = random.Random(state.seed ^ (state.time * 7919) ^ stable_seed(entry.actor_uid))
    paid = state._charge_npc_cost(cost, rng)
    name = _label(state, entry)
    record(state, "settle", actor_uid=player_uid(state), target_uid=entry.actor_uid,
           position=(entry.x, entry.y), owner_uid=entry.actor_uid,
           source_kind="restitution", before="和解中", after="中立",
           amount=entry.restitution)
    _restore(state, entry)
    _spend_action(state)
    message = tr("补偿已付清：{detail}。{name}把账合上了。",
                 detail="，".join(paid), name=name)
    state.messages.append(message)
    return ActionResult(True, message, {"actor": entry.actor_uid, "stance": "中立"})


# ---------------------------------------------------------------- 派系声望（§4.3）

def reputation(state: Any, faction_id: str) -> int:
    """派系声望分值（本局，-6～+6）：账在 world_ledger 上，读档/远层重建不丢。"""
    ledger = getattr(state, "world_ledger", None)
    if ledger is None:
        return 0
    entry = ledger.reputations.get(faction_id)
    return int(entry["value"]) if entry else 0


def adjust_reputation(state: Any, faction_id: str, delta: int, reason: str, *,
                      once_key: str | None = None) -> str | None:
    """调整派系声望并返回可显示的消息；拒绝重复结算与越界。

    - ``once_key``：同一件事只改变一次声望（§4.3「同一任务实例只改变一次声望」）。
      重复提交同一把键直接返回 None，分值与档位都不动。
    - 跨档时消息里写明「旧档 → 新档」，没跨档只报分数变化（§14：声望变化进顶部
      事件记录，具体档位影响在对话与服务处各查各的）。
    - 分值钳制在 :data:`~dream_demo.data.factions.REPUTATION_MIN`／MAX 之内，
      钳制后若实际没变（已顶格），消息照发但不重复写档位。
    """
    from ..data import factions

    if faction_id not in factions.FACTION_DEFINITIONS:
        return None
    ledger = getattr(state, "world_ledger", None)
    if ledger is None:
        return None
    entry = ledger.reputations.setdefault(faction_id, {"value": 0, "once_keys": {}})
    if once_key:
        if entry["once_keys"].get(once_key):
            return None
        entry["once_keys"][once_key] = True
    old = int(entry["value"])
    new = max(factions.REPUTATION_MIN, min(factions.REPUTATION_MAX, old + int(delta)))
    entry["value"] = new
    definition = factions.FACTION_DEFINITIONS[faction_id]
    old_tier = factions.tier_label(old)
    new_tier = factions.tier_label(new)
    if new_tier != old_tier:
        message = tr("{faction}的账本上添了一笔（{reason}）：{old}（{old_tier}）→ "
                     "{new}（{new_tier}）。",
                     faction=definition["name"], reason=reason, old=old,
                     old_tier=old_tier, new=new, new_tier=new_tier)
    else:
        message = tr("{faction}的账本上添了一笔（{reason}）：{old} → {new}（{tier}）。",
                     faction=definition["name"], reason=reason, old=old, new=new,
                     tier=new_tier)
    state.messages.append(message)
    return message


subscribe(observe)
