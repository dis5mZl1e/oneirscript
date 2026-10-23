"""行动事实（重构方案 §13.3／§13.4）：只描述**已经发生**的改变。

关系（§4.4 责任归属）、任务（§7.3 战斗归属）与设施（§10.2 状态转移）要认同一份
行为记录，所以事实必须一次记清、三家共读，而不是每家在各自的结算里再猜一遍玩家
做了什么。事实不调用动作，也不递归触发效果。

帧上下文沿用装备语法已有的 ``RootFrame``（§13.3「共用上下文」）：嵌套的公开入口
共用一帧、最外层只结算一次，同一个玩家行动里派生出的 NPC 反应、环境连锁和装备
触发都带着同一个 ``root_action_uid``，各自记 ``fact_uid`` 与 ``parent_fact_uid``。
不新造第二个 root frame，也不因世界事件订阅而再次调用装备 settle。
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

#: 每条事实的最低字段（§13.3 表）。缺字段＝记账口径不一致，宁可补默认值。
FACT_FIELDS = ("fact_uid", "root_action_uid", "parent_fact_uid", "action_seq",
               "world_time", "kind", "actor_uid", "target_uid", "layer_key",
               "position", "region_ids", "owner_uid", "cause_uid", "source_kind",
               "before", "after", "amount", "witness_uids", "visibility_snapshot")

#: 首版事实类型（§13.3）。新增种类要和 §16.1 的回归用例一起补。
FACT_KINDS = frozenset({
    "move", "deliver", "transfer", "harm", "remove", "facility",
    "material", "safety", "warn", "conflict", "pact", "settle", "descend", "report",
})

#: 目击半径：事发时**能感知相关位置**的角色才算证人（§4.4「远处所有 NPC 不能
#: 同步拥有玩家的全部行为知识」）。首版用切比雪夫距离近似视野，
#: ``visibility_snapshot`` 留给后续接入真实遮挡判定。
WITNESS_RADIUS = 8

#: 订阅者自己也要记账（关系模块会写 warn/conflict/report），但因果链必须有限
#: （§10.3）：一条事实最多再引出这么多层衍生事实。
MAX_CAUSAL_DEPTH = 3

_LISTENERS: list[Callable[[Any, dict[str, Any]], None]] = []
_absorb_depth = 0


def subscribe(listener: Callable[[Any, dict[str, Any]], None]) -> None:
    """注册事实订阅者（关系、任务、设施各订一家）。

    订阅者只能**读**事实并更新自己的状态，不得再调用会记录新事实的行动入口——
    §10.3 要求因果链有限，回环由 ``RootFrame`` 的去重兜住，不靠订阅者自律。
    """
    if listener not in _LISTENERS:
        _LISTENERS.append(listener)


def reset_listeners() -> None:
    _LISTENERS.clear()


def _root_uid(state: Any, frame: Any) -> str:
    if frame is not None:
        return f"{state.run_uid}:{frame.action_id}:{frame.start_time}"
    # 没有被根动作包住的改变（世界推进、计时器）也要能归因：用「世界时刻 + 序号」
    # 组一个非玩家根，它不会冒充成一次玩家行动（§16.1「亚回合不冒充整回合」）。
    return f"{state.run_uid}:world:{state.action_seq}:{state.time}"


def witnesses(state: Any, position: tuple[int, int] | None) -> tuple[str, ...]:
    """事发时刻站得够近、因而可能看见的角色（不含玩家自己）。"""
    if position is None:
        return ()
    return tuple(
        getattr(actor, "actor_uid", "") or getattr(actor, "id", "")
        for actor in state.enemies
        if getattr(actor, "integrity", 0) > 0
        and max(abs(int(actor.x) - position[0]), int(actor.y) - position[1]) <= WITNESS_RADIUS
    )


def record(state: Any, kind: str, *, actor_uid: str = "", target_uid: str = "",
           position: tuple[int, int] | None = None, owner_uid: str = "",
           cause_uid: str = "", source_kind: str = "", before: Any = None,
           after: Any = None, amount: int = 0, region_ids: Iterable[str] = (),
           parent_fact_uid: str = "", witness_uids: Iterable[str] | None = None,
           observe: bool = True) -> dict[str, Any]:
    """登记一条行动事实，返回事实本身（调用方常要拿它的 uid 当父节点）。

    ``observe=False`` 用于纯查询/预览路径：预览不得改变世界记录（§13.4 第 2 步）。
    """
    if kind not in FACT_KINDS:
        raise ValueError(f"未知行动事实类型 {kind!r}（§13.3 只认 {sorted(FACT_KINDS)}）")
    frame = getattr(state, "_equipment_root_frame", None)
    absorbing = _absorb_depth > 0
    if frame is not None:
        claim = (kind, actor_uid, target_uid, position)
        if claim in frame.fact_claims:
            # 同一根动作里同一目标被多个派生效果打到多次，只算一次行动事实。
            return dict(frame.world_facts[-1]) if frame.world_facts else {}
        frame.fact_claims.add(claim)
    if not observe:
        return {}
    state.world_ledger.seq += 1
    fact: dict[str, Any] = {
        "fact_uid": f"{state.run_uid}#{state.world_ledger.seq}",
        "root_action_uid": _root_uid(state, frame),
        "parent_fact_uid": parent_fact_uid,
        "action_seq": int(state.action_seq),
        "world_time": int(state.time),
        "kind": kind,
        "actor_uid": actor_uid,
        "target_uid": target_uid,
        "layer_key": state.layer_key(),
        "position": tuple(position) if position else None,
        "region_ids": tuple(region_ids),
        "owner_uid": owner_uid or actor_uid,
        "cause_uid": cause_uid,
        "source_kind": source_kind,
        "before": before,
        "after": after,
        "amount": int(amount),
        "witness_uids": tuple(witnesses(state, position)) if witness_uids is None
        else tuple(witness_uids),
        "visibility_snapshot": None,
    }
    if frame is not None and not absorbing:
        # 有根动作：先挂在帧上，最外层 settle 时才并进世界记录。
        frame.world_facts.append(fact)
    else:
        # 结算途中订阅者写回的事实（警告、通报）直接入账：帧已经收过账了，
        # 再挂上去就没人来取。
        _absorb(state, [fact])
    return fact


def flush(state: Any) -> None:
    """把当前帧积累的事实并进世界记录，并分发给订阅者。"""
    frame = getattr(state, "_equipment_root_frame", None)
    if frame is None or not frame.world_facts:
        return
    pending, frame.world_facts = frame.world_facts, []
    _absorb(state, pending)


def _absorb(state: Any, facts: list[dict[str, Any]]) -> None:
    global _absorb_depth
    if _absorb_depth >= MAX_CAUSAL_DEPTH:
        # 因果链封顶：衍生事实不再往下触发订阅，超限的那条只留记录不留反应。
        for fact in facts:
            state.world_ledger.add_fact(fact)
        return
    _absorb_depth += 1
    try:
        ledger = state.world_ledger
        for fact in facts:
            ledger.add_fact(fact)
            for listener in _LISTENERS:
                listener(state, fact)
    finally:
        _absorb_depth -= 1


def facts_for(state: Any, **filters: Any) -> list[dict[str, Any]]:
    """查询已成立的事实（任务与关系都读同一个口径，不各自维护计数器）。"""
    return state.world_ledger.facts_where(**filters)


def fact_seq(fact: dict[str, Any]) -> int:
    """一条事实在世界记录里的单调序号（``fact_uid`` 的尾段）。"""
    tail = str(fact.get("fact_uid", "")).rsplit("#", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def since_accept(state: Any, accepted_mark: int, **filters: Any) -> list[dict[str, Any]]:
    """接取**之后**记下的事实（§7.3「狩猎默认为接取后针对目标 UID 的实际解决」）。

    界线取世界记录的序号而不是行动序号：行动序号要到一次行动结算完才 +1，同一次
    行动里「先杀后接」与「先接后杀」会落在同一个数上——先屠一遍图再回来补领奖励就
    又从这里漏回来了。序号由 :func:`record` 递增，写下即定，不受结算次序影响。
    """
    return [fact for fact in state.world_ledger.facts_where(**filters)
            if fact_seq(fact) > accepted_mark]
