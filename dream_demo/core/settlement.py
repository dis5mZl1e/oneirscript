
"""资源结算事实（2026-10-18 docs/261018方案合集.md 第 10 节第三批）。

- SettlementResult：一次资源请求的实际结果（请求量、实际量、前后值、原因、
  来源、渠道、是否被上下限截断、世界时间与行动序号）。
- 资源写入统一走 settle_delta / record_settlement：先按上下限钳制，再记录事实；
  上限变化与恢复分开（apply_max_change 不计作恢复）。
- 近期结算只保留有界内存（runtime，不写存档），供自我觉察「近期变化」使用。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

RESOURCE_KEYS = ("mind", "lucidity", "imagination")

# 原因类型：不同来源不得混用（docs §10.6「必须保留的结算边界」）。
REASON_COMBAT = "combat"
REASON_ENVIRONMENT = "environment"
REASON_ABILITY_COST = "ability_cost"
REASON_TAMPER_COST = "tamper_cost"
REASON_RESTORE_NATURAL = "restore_natural"
REASON_RESTORE_ITEM = "restore_item"
REASON_RESTORE_SCENE = "restore_scene"
REASON_RESTORE_DERIVED = "restore_derived"
REASON_STORY = "story"
REASON_TRADE_COST = "trade_cost"
REASON_DRUG_DEBT = "drug_debt"   # 药物分期：不能被凝滞当作环境伤害免疫
REASON_MAX_CHANGE = "max_change"
REASON_DEBUG = "debug"
REASONS = frozenset({
    REASON_COMBAT, REASON_ENVIRONMENT, REASON_ABILITY_COST, REASON_TAMPER_COST,
    REASON_RESTORE_NATURAL, REASON_RESTORE_ITEM, REASON_RESTORE_SCENE,
    REASON_RESTORE_DERIVED, REASON_STORY, REASON_TRADE_COST, REASON_DRUG_DEBT,
    REASON_MAX_CHANGE, REASON_DEBUG,
})

RECENT_SETTLEMENTS = 50
RECENT_ACTION_TIMES = 30


@dataclass(frozen=True)
class SettlementResult:
    resource: str
    requested: float
    applied: float
    before: float
    after: float
    reason: str
    source: str = ""
    channel: str = ""
    capped: bool = False
    blocked: str = ""
    world_time: int = 0
    action_seq: int = 0

    @property
    def changed(self) -> bool:
        return abs(self.applied) > 1e-9

    def to_dict(self) -> dict:
        return {
            "resource": self.resource,
            "requested": self.requested,
            "applied": self.applied,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "source": self.source,
            "channel": self.channel,
            "capped": self.capped,
            "blocked": self.blocked,
            "world_time": self.world_time,
            "action_seq": self.action_seq,
        }


@dataclass(frozen=True)
class ActionTimeRecord:
    kind: str
    base: float
    paid: float
    extra: float = 0.0
    world_time: int = 0
    action_seq: int = 0

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "base": self.base, "paid": self.paid,
            "extra": self.extra, "world_time": self.world_time,
            "action_seq": self.action_seq,
        }


def _history(state: Any) -> deque:
    history = getattr(state, "_recent_settlements", None)
    if history is None:
        history = deque(maxlen=RECENT_SETTLEMENTS)
        setattr(state, "_recent_settlements", history)
    return history


def _action_history(state: Any) -> deque:
    history = getattr(state, "_recent_action_times", None)
    if history is None:
        history = deque(maxlen=RECENT_ACTION_TIMES)
        setattr(state, "_recent_action_times", history)
    return history


def recent_settlements(state: Any, limit: int = 10) -> tuple[SettlementResult, ...]:
    history = getattr(state, "_recent_settlements", None) or ()
    return tuple(history)[-max(0, limit):]


def recent_action_times(state: Any, limit: int = 10) -> tuple[ActionTimeRecord, ...]:
    history = getattr(state, "_recent_action_times", None) or ()
    return tuple(history)[-max(0, limit):]


def record_settlement(state: Any, result: SettlementResult) -> SettlementResult:
    _history(state).append(result)
    return result


def _apply_value(state: Any, resource: str, value: float) -> None:
    """统一写入口：保留原类型（整数资源不因一次减法变成浮点显示）。"""
    before = getattr(state, resource)
    if isinstance(before, int) and float(value).is_integer():
        value = int(value)
    setattr(state, resource, value)


def write_resource(state: Any, resource: str, value: float) -> None:
    """领域结算器已算好最终值时统一写入口（保留整数显示类型）。"""
    if resource not in RESOURCE_KEYS:
        raise ValueError(f"未知资源：{resource}")
    _apply_value(state, resource, value)


def settle_delta(
    state: Any,
    resource: str,
    delta: float,
    *,
    reason: str,
    source: str = "",
    channel: str = "",
    allow_above_max: bool = False,
) -> SettlementResult:
    """按上下限结算一次资源变化并记录事实（不参与韧性/缓冲等减免）。"""
    if resource not in RESOURCE_KEYS:
        raise ValueError(f"未知资源：{resource}")
    if reason not in REASONS:
        raise ValueError(f"未知结算原因：{reason}")
    before = float(getattr(state, resource))
    maximum = float(getattr(state, "max_" + resource))
    if delta<0 and reason in (REASON_COMBAT,REASON_ENVIRONMENT) and getattr(state,'stasis_turns',0)>0:
        return record_settlement(state,SettlementResult(
            resource=resource,requested=float(delta),applied=0.0,before=before,after=before,
            reason=reason,source=source,channel=channel,blocked='stasis',
            world_time=int(getattr(state,'time',0)),action_seq=int(getattr(state,'action_seq',0))))
    after = before + float(delta)
    capped = False
    blocked = ""
    if after < 0:
        after = 0.0
        capped = True
    if after > maximum and delta > 0 and not allow_above_max:
        # 只有「恢复/增加」被上限截断；消耗与损失保留临时高于上限的值
        # （旧直接写入同样只 max(0, x-delta)，不能因为迁移改变结算）。
        after = maximum
        capped = True
    if abs(after - before) < 1e-9:
        if delta < 0 and before <= 0:
            blocked = "at_zero"
        elif delta > 0 and before >= maximum:
            blocked = "at_max"
    elif after <= 0.0 and delta < 0:
        blocked = "at_zero"
    elif after >= maximum and delta > 0 and not allow_above_max:
        blocked = "at_max"
    _apply_value(state, resource, after)
    result = SettlementResult(
        resource=resource,
        requested=float(delta),
        applied=after - before,
        before=before,
        after=after,
        reason=reason,
        source=source,
        channel=channel,
        capped=capped,
        blocked=blocked,
        world_time=int(getattr(state, "time", 0) or 0),
        action_seq=int(getattr(state, "action_seq", 0) or 0),
    )
    return record_settlement(state, result)


def record_settled_value(
    state: Any,
    resource: str,
    requested: float,
    before: float,
    after: float,
    *,
    reason: str,
    source: str = "",
    channel: str = "",
    blocked: str = "",
) -> SettlementResult:
    """已经由领域结算器改好数值时，只登记事实（不重复写值）。"""
    if resource not in RESOURCE_KEYS or reason not in REASONS:
        raise ValueError((resource, reason))
    maximum = float(getattr(state, "max_" + resource))
    result = SettlementResult(
        resource=resource,
        requested=float(requested),
        applied=float(after) - float(before),
        before=float(before),
        after=float(after),
        reason=reason,
        source=source,
        channel=channel,
        capped=float(after) <= 0.0 or float(after) >= maximum,
        blocked=blocked,
        world_time=int(getattr(state, "time", 0) or 0),
        action_seq=int(getattr(state, "action_seq", 0) or 0),
    )
    return record_settlement(state, result)


def apply_max_change(
    state: Any,
    resource: str,
    new_maximum: float,
    *,
    reason: str = REASON_MAX_CHANGE,
    source: str = "",
    clamp_current: bool = True,
) -> SettlementResult:
    """改变上限；不恢复当前值（docs §10.6：增加上限不等于恢复资源）。"""
    if resource not in RESOURCE_KEYS:
        raise ValueError(f"未知资源：{resource}")
    if reason not in REASONS:
        raise ValueError(f"未知结算原因：{reason}")
    field = "max_" + resource
    before_max = float(getattr(state, field))
    setattr(state, field, new_maximum)
    before = float(getattr(state, resource))
    after = before
    if clamp_current and before > new_maximum:
        after = float(new_maximum)
        _apply_value(state, resource, after)
    result = SettlementResult(
        resource=field,
        requested=float(new_maximum) - before_max,
        applied=after - before,
        before=before,
        after=after,
        reason=reason,
        source=source,
        channel="max_change",
        capped=after != before,
        world_time=int(getattr(state, "time", 0) or 0),
        action_seq=int(getattr(state, "action_seq", 0) or 0),
    )
    return record_settlement(state, result)


def record_action_time(
    state: Any,
    *,
    kind: str,
    base: float,
    paid: float,
    extra: float = 0.0,
) -> ActionTimeRecord:
    """登记一次实际行动实际支付的时间（含亚回合欠账与额外沉眠）。"""
    record = ActionTimeRecord(
        kind=str(kind),
        base=float(base),
        paid=float(paid),
        extra=float(extra),
        world_time=int(getattr(state, "time", 0) or 0),
        action_seq=int(getattr(state, "action_seq", 0) or 0),
    )
    _action_history(state).append(record)
    return record
