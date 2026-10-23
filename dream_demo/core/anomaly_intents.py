"""Transient anomaly intent-switch facts for map presentation.

Only a real change between two world settlements is recorded: the tracker
compares what an anomaly was observably doing before and after one player
action, keeps the most meaningful change per entity and drops the rest. It
never predicts the next move, never advances a turn and never touches AI.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

# Lower number wins when one action produces several changes for one anomaly.
PRIORITY = {
    "windup_broken": 0,
    "windup_start": 1,
    "flee": 2,
    "chase": 3,
    "lost": 4,
    "suspect": 5,
    "investigate": 5,
    "recover": 6,
}

# Same-cell badge lifetime in seconds (design §6.1).
LIFETIME = 1.0

ALERT_SUSPECT = ("怀疑", "警戒")


@dataclass(frozen=True)
class IntentEvent:
    entity_id: str
    kind: str
    action_seq: int
    started: float


def _skill_state(enemy) -> dict:
    state = getattr(enemy, "active_skill_state", None)
    return state if isinstance(state, dict) else {}


def _facts(enemy) -> tuple:
    skill = _skill_state(enemy)
    pending = skill.get("pending") if isinstance(skill.get("pending"), dict) else {}
    end = skill.get("last_windup_end")
    return (
        str(getattr(enemy, "alert_state", "") or ""),
        str(pending.get("skill_id", "") or ""),
        str(end[0]) if isinstance(end, tuple) and end else "",
        float(skill.get("recover_until", 0) or 0),
        bool(getattr(enemy, "portents", {}).get("spooked")),
        len(getattr(enemy, "investigation_tasks", ()) or ()),
    )


def _player_id(state) -> str:
    return str(getattr(getattr(state, "player", None), "id", "") or "")


def snapshot(state) -> dict[str, tuple]:
    player_id = _player_id(state)
    return {str(enemy.id): _facts(enemy) for enemy in getattr(state, "enemies", ())
            # 2026-10-22：意图状态动画只适用于异象，玩家即便异常出现在
            # enemies 容器里也不参与。
            if enemy.integrity > 0 and str(enemy.id) != player_id}


def _change(before: tuple | None, after: tuple) -> str:
    if before is None:
        return ""  # Newly seen entity: entering the board is not a switch.
    (alert_before, charging_before, end_before, recover_before,
     spooked_before, tasks_before) = before
    (alert_after, charging_after, end_after, recover_after,
     spooked_after, tasks_after) = after
    if spooked_after and not spooked_before:
        return "flee"
    if charging_after and not charging_before:
        return "windup_start"
    if charging_before and not charging_after:
        if end_after == "broken" and end_before != "broken":
            return "windup_broken"
        if recover_after > recover_before:
            return "recover"
    if alert_after != alert_before:
        if alert_after == "追踪":
            return "chase"
        if alert_before == "追踪":
            return "lost"
        if (alert_before == "未察觉" and alert_after in ALERT_SUSPECT
                or alert_before == "怀疑" and alert_after == "警戒"):
            # 同一次切换里登记了新的调查任务：真实事实是开始查找某个地点，
            # 文字不能把它说成单纯的怀疑，也不替它编造声音来源（设计 §5）。
            return "investigate" if tasks_after > tasks_before else "suspect"
    # 新登记的调查任务：真正开始查找某个地点，而不是沿同一路径继续走。
    if tasks_after > tasks_before and alert_after != "追踪":
        return "investigate"
    return ""


def begin_action(state) -> None:
    """Remember what each anomaly was doing before the world settles."""
    state._anomaly_intent_before = snapshot(state)


def end_action(state) -> None:
    """Diff one settled action, merge per entity, then publish at most one badge."""
    before = getattr(state, "_anomaly_intent_before", None)
    state._anomaly_intent_before = None
    if before is None:
        return
    after = snapshot(state)
    found: dict[str, str] = {}
    for entity_id, facts in after.items():
        kind = _change(before.get(entity_id), facts)
        if not kind:
            continue
        previous = found.get(entity_id)
        if previous is None or PRIORITY[kind] < PRIORITY[previous]:
            found[entity_id] = kind
    now = monotonic()
    seq = int(getattr(state, "action_seq", 0))
    # 上一条行动的角标还在有效期内时不能整批替换：同一异象用这次的变化顶掉旧的
    # （§6.2），其他异象的角标继续各自倒计时（§6.3 才谈得上多只同时显示）。
    published = [IntentEvent(entity_id, kind, seq, now)
                 for entity_id, kind in found.items()]
    kept = [event for event in live_intents(state, now)
            if event.entity_id not in found]
    state.anomaly_intents = tuple(sorted(
        (*kept, *published),
        key=lambda event: (event.started, PRIORITY[event.kind], event.entity_id)))


def live_intents(state, now: float | None = None) -> tuple[IntentEvent, ...]:
    """Events whose badge is still drawn; expired ones are never replayed."""
    now = monotonic() if now is None else now
    return tuple(event for event in getattr(state, "anomaly_intents", ())
                 if now - event.started <= LIFETIME)


def intent_cells(state, now: float | None = None) -> dict[tuple[int, int], tuple[str, float]]:
    """Map cell -> (kind, started) for badges whose subject is still visible.

    ``started`` is the wall-clock moment the switch was published, so the
    presentation layer can ramp the badge in and out without keeping its own
    timer.
    """
    from .map_scene import actor_display

    events = live_intents(state, now)
    if not events:
        return {}
    wanted = {event.entity_id: (event.kind, event.started) for event in events}
    player_id = _player_id(state)
    by_cell: dict[tuple[int, int], list[tuple[str, float]]] = {}
    for enemy in getattr(state, "enemies", ()):
        found = wanted.get(str(enemy.id))
        if not found or enemy.integrity <= 0:
            continue
        if player_id and str(enemy.id) == player_id:
            continue
        if not state.is_visible(enemy.x, enemy.y):
            continue
        # 伪装尚未识破时这一格显示的是「显化物」，角标会把异象身份泄漏出去。
        if actor_display(state, enemy)[0] == "显化物":
            continue
        by_cell.setdefault((enemy.x, enemy.y), []).append(found)
    # Two creatures sharing one rendered cell would attach the badge to
    # whichever happens to iterate last; stay silent rather than mislabel.
    return {cell: rows[0] for cell, rows in by_cell.items() if len(rows) == 1}


def clear(state) -> None:
    state.anomaly_intents = ()
    state._anomaly_intent_before = None
