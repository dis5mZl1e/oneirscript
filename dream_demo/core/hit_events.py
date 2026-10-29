"""运行期命中表现事件（docs/手感与键盘操作优化分析-2026-10-24.md §3.1）。

只服务表现层：定向抖动、伤害跳字、命中强调、命中音。**不进存档、不参与
回合推进、命中判定或伤害公式**。事件在伤害已经落账之后登记，``amount``
永远是实际损失，不是攻击面板数值。
"""
from __future__ import annotations

HIT_EVENT_MAX = 64
HIT_KINDS = frozenset({"melee", "ranged", "throw", "enemy_strike", "damage"})


def note_damage(state, *, target, amount, resource: str, origin="", damage_type="") -> dict | None:
    """Actual non-attack trauma: floating number only, with no invented origin."""
    if target is not getattr(state, "player", None) and not state.is_visible(target.x, target.y):
        return None
    return note_hit(
        state, kind="damage", source=None, impact=(target.x, target.y),
        target_id=target.id, amount=amount, resource=resource,
        origin=origin, damage_type=damage_type or resource,
    )


def note_integrity_loss(state, target, before) -> dict | None:
    """Publish an environmental actor injury before it moves or is removed."""
    return note_damage(state, target=target, amount=max(0, before - target.integrity),
                       resource="integrity", origin="environment", damage_type="integrity")


def _unit(value: int) -> int:
    return (int(value) > 0) - (int(value) < 0)


def note_hit(
    state,
    *,
    kind: str,
    source,
    impact,
    target_id,
    amount,
    resource,
    direction=None,
    blocked: bool = False,
    killed: bool = False,
    projectile_seq=None,
    origin="",
    damage_type="",
) -> dict | None:
    """登记一条命中表现事件；没有实际损失且未被挡下时返回 None。"""
    amount = max(0, int(amount or 0))
    if amount <= 0 and not blocked:
        return None
    if kind not in HIT_KINDS:
        return None
    seq = int(getattr(state, "hit_event_seq", 0) or 0) + 1
    state.hit_event_seq = seq
    source = tuple(int(v) for v in source) if source else None
    impact = tuple(int(v) for v in impact) if impact else None
    dx = _unit(impact[0] - source[0]) if source and impact else 0
    dy = _unit(impact[1] - source[1]) if source and impact else 0
    if direction is not None:
        dx, dy = _unit(direction[0]), _unit(direction[1])
    event = {
        "seq": seq,
        "action_seq": int(getattr(state, "action_seq", 0) or 0),
        "kind": kind,
        "source": source,
        "impact": impact,
        "target_id": str(target_id or ""),
        "direction": (dx, dy),
        "amount": amount,
        "resource": str(resource),
        "origin": str(origin or kind),
        "damage_type": str(damage_type or resource),
        "blocked": bool(blocked),
        "killed": bool(killed),
        "projectile_seq": projectile_seq,
    }
    queue = list(getattr(state, "presentation_hits", ()) or ())
    queue.append(event)
    state.presentation_hits = queue[-HIT_EVENT_MAX:]
    return event


def attach_projectile(state, seq: int) -> int:
    """给同一动作里尚未挂弹道的命中事件补上 ``projectile_seq``。

    core 的顺序是「先结算命中、后登记弹道」（``_note_projectile`` 在
    ``_player_strike`` 之后），所以只能事后回填；UI 据此把命中时刻推迟到
    弹道视觉抵达目标的那一帧，而不是另猜一套时长。
    """
    action_seq = int(getattr(state, "action_seq", 0) or 0)
    attached = 0
    for event in getattr(state, "presentation_hits", ()) or ():
        if (event.get("kind") != "damage" and event.get("projectile_seq") is None
                and event.get("action_seq") == action_seq):
            event["projectile_seq"] = int(seq)
            attached += 1
    return attached
