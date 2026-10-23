# -*- coding: utf-8 -*-
"""篡改的共享提交管线（对话侧与地图侧共用，docs §四「共享提交管线进一步统一」）。

两套篡改（对话文本 / 地图语句）在**顺序**上本来就是同一条：

    验证 → 写效果 → 扣想象力 → 加混乱度 → 篡改序号 +1 → 风险判定
    → 推进 1 个「使用」行动 → 存活才执行风险

差别只在「效果是什么」（写变体 vs 改世界）以及各自的持久化记录，因此这里只抽
出真正共享的六件事，效果与记录仍留在各自模块：

* :func:`next_sequence` —— 共享的 ``tamper_sequence``（旧动态世界序号已并入）；
* :func:`charge` —— 扣想象力 + 加混乱度，返回提交后混乱度；
* :func:`advance_time` —— 推进一次「使用」行动，计入混乱度衰减口径；
* :func:`roll_risk` —— 只判定风险，使用独立随机源，不扰动世界随机序列；
* :func:`apply_risk` —— 存活才执行风险，死亡时返回空串（调用方记 skipped）；
* :func:`settle` —— 把「扣费 → 判定」合成一步，给不需要中间记录的回调使用。

不在这里统一的部分（有意保留）：效果执行与失败回滚各自在调用方，因为地图侧
必须在扣费前确认「这一刀真的能落下」（目标材质/保护矩阵/路径可达），而对话侧
的效果是写一条已审核的变体，不存在同类前置失败。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

from ..data.tamper_schema import RiskOutcome, TamperRequest
from .chaos import TAMPER_SOURCE, change_chaos
from .tamper_risks import execute_tamper_risk, roll_tamper_risk


@dataclass(frozen=True)
class TamperCost:
    """一次篡改的可见代价；由调用方按字词/变体算好后交给管线。"""

    imagination: int = 0
    chaos_delta: int = 0

    def clamped(self) -> "TamperCost":
        return TamperCost(max(0, int(self.imagination)), int(self.chaos_delta))


def next_pressure(state: Any) -> int:
    pressure = max(0, min(3, int(getattr(state, 'tamper_pressure', 0))))
    return min(3, pressure + 1) if getattr(state, 'tamper_pressure_gap', 10) < 10 else pressure


def quote_cost(state: Any, cost: TamperCost) -> TamperCost:
    """Raw base cost -> final visible cost, exactly once before settlement."""
    return TamperCost(max(0, cost.imagination),
                      ceil(cost.chaos_delta * 1.3) + 2 * next_pressure(state))


def note_tamper(state: Any) -> None:
    state.tamper_pressure = next_pressure(state)
    state.tamper_pressure_gap = 0
    state.tamper_pressure_idle = 0


def note_paid_action(state: Any) -> None:
    state.tamper_pressure_gap = min(10, int(state.tamper_pressure_gap) + 1)
    state.tamper_pressure_idle += 1
    if state.tamper_pressure_idle >= 10:
        state.tamper_pressure = max(0, state.tamper_pressure - 1)
        state.tamper_pressure_idle %= 10


def risk_chaos(state: Any, chaos_after: int, *, imagination_cost: int = 0) -> int:
    vulnerable = sum(getattr(state, resource, 0) - (imagination_cost if resource == 'imagination' else 0)
                     <= max(1, getattr(state, maximum, 1)) * .3
                     for resource, maximum in (('mind', 'max_mind'), ('imagination', 'max_imagination')))
    return min(100, chaos_after + vulnerable * 20)


def risk_note(state: Any, chaos_after: int, *, imagination_cost: int = 0) -> str:
    from ..i18n import tr
    from .chaos import chaos_risk_tier
    return tr('连续压力 {pressure}/3 · 风险 {tier}；可能产生声响、余火或异象警戒变化。',
              pressure=next_pressure(state), tier=tr(chaos_risk_tier(risk_chaos(state, chaos_after, imagination_cost=imagination_cost))))


def next_sequence(state: Any) -> int:
    """共享篡改序号 +1 并返回；对话与地图提交共用同一序列。"""
    state.tamper_sequence = int(getattr(state, "tamper_sequence", 0)) + 1
    return int(state.tamper_sequence)


def charge(state: Any, cost: TamperCost, *, reason: str, source_uid: str) -> int:
    """扣想象力、加混乱度；返回提交后的混乱度（实际值，已 clamp）。"""
    cost = cost.clamped()
    note_tamper(state)
    if cost.imagination:
        from .settlement import REASON_TAMPER_COST, settle_delta
        settle_delta(state, 'imagination', -cost.imagination,
                     reason=REASON_TAMPER_COST, source='篡改提交')
    change_chaos(state, cost.chaos_delta, reason=reason, source_uid=source_uid)
    return int(state.chaos)


def advance_time(state: Any) -> None:
    """推进 1 个「使用」行动；本次行动不贡献混乱度衰减（与两套篡改一致）。"""
    from .constants import ActionKind

    state._action_time(1, ActionKind.USE, chaos_source=TAMPER_SOURCE)


def roll_risk(state: Any, request: TamperRequest, *, sequence: int,
              chaos_after: int) -> RiskOutcome | None:
    """判定风险（只判定，不执行）；随机源与归属口径沿用 ``tamper_risks``。"""
    return roll_tamper_risk(state, request, sequence=sequence, chaos_after=risk_chaos(state, chaos_after))


def apply_risk(state: Any, outcome: RiskOutcome | None, *, source_uid: str) -> str:
    """执行已确定的风险；死亡时不执行（提交本身已推进世界，不退还成本）。"""
    if outcome is None or getattr(state, "run_over", False):
        return ""
    return execute_tamper_risk(state, outcome, source_uid=source_uid)


def settle(state: Any, request: TamperRequest, cost: TamperCost, *,
           sequence: int, reason: str, source_uid: str) -> tuple[int, RiskOutcome | None]:
    """扣费 + 混乱 + 判定的常用组合；返回（提交后混乱度, 风险结果）。"""
    chaos_after = charge(state, cost, reason=reason, source_uid=source_uid)
    return chaos_after, roll_risk(state, request, sequence=sequence, chaos_after=chaos_after)
