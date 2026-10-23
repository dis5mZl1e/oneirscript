"""混乱度服务：统一增减、风险档位与「实际行动耗时」衰减（规格 §6）。

混乱度与崩解度分别保存、显示与结算；变化本身不抽负面事件——风险判定是
:mod:`core.tamper_risks` 的独立入口，避免将来接入时一次变化触发两遍。
"""

from __future__ import annotations

from typing import Any

from ..data.tamper_schema import CHAOS_DECAY_INTERVAL, CHAOS_MAX, CHAOS_MIN, RISK_TIERS
from .constants import ActionKind

#: 有资格累计衰减的行动类型：移动／攻击／物品或场地交互。等待（MISC）不算。
DECAY_KINDS = frozenset({ActionKind.MOVE, ActionKind.ATTACK, ActionKind.USE})
#: 衰减来源标记：篡改自身与其风险事件不贡献衰减。
WORLD_SOURCE = "world"
TAMPER_SOURCE = "tamper"


def clamp_chaos(value: float) -> int:
    return max(CHAOS_MIN, min(CHAOS_MAX, int(value)))


def change_chaos(state: Any, amount: int, *, reason: str, source_uid: str = "") -> int:
    """统一的增减入口（规格 §6.3）：返回**实际**增减量，负责 0～100 钳制。

    后续事件、道具、环境与其他行为都走这里；`reason`／`source_uid` 只用于日志
    与扩展，不参与结算。混乱度已经为 0 时余量清零，不预存「平复额度」。
    """
    if not amount:
        return 0
    before = clamp_chaos(getattr(state, "chaos", 0))
    after = clamp_chaos(before + int(amount))
    state.chaos = after
    if after <= CHAOS_MIN:
        state.chaos_decay_credit = 0.0
    return after - before


def chaos_risk_tier(chaos: int) -> str:
    """玩家可见的风险档位（规格 §7.1）。"""
    value = clamp_chaos(chaos)
    for low, high, tier, _probability in RISK_TIERS:
        if low <= value <= high:
            return tier
    return RISK_TIERS[-1][2]


def chaos_risk_probability(chaos: int) -> float:
    """内部概率：只进开发配置与调试信息，玩家面板不显示。"""
    value = clamp_chaos(chaos)
    for low, high, _tier, probability in RISK_TIERS:
        if low <= value <= high:
            return probability
    return RISK_TIERS[-1][3]


def note_chaos_action(state: Any, paid_rounds: float, *, kind: ActionKind,
                      source: str, effective: bool) -> None:
    """一次行动收尾：记付费序号，并按资格累计混乱度衰减（规格 §6.2）。

    `paid_rounds` 是这次行动**实际支付**的耗时（速度缩放后的主耗时＋征兆额外
    耗时），不是按键次数。免费行动、强制补齐回合与篡改自身都不进这里。
    """
    if paid_rounds <= 0:
        return
    # 付费行动序号：预警（页边余火、吞音）用它判断「玩家又完成一次耗时行动」。
    # 与 action_seq 分开——那个连免费行动也计数，会让免费操作顶开公平窗口。
    state.paid_action_seq = int(getattr(state, "paid_action_seq", 0)) + 1
    if source != WORLD_SOURCE or not effective:
        return
    if kind not in DECAY_KINDS:
        return
    credit = float(getattr(state, "chaos_decay_credit", 0.0)) + float(paid_rounds)
    chaos = clamp_chaos(getattr(state, "chaos", 0))
    while credit >= CHAOS_DECAY_INTERVAL and chaos > CHAOS_MIN:
        credit -= CHAOS_DECAY_INTERVAL
        chaos -= 1
    state.chaos = chaos
    state.chaos_decay_credit = 0.0 if chaos <= CHAOS_MIN else credit
