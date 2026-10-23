"""承载面的归属与领取费用（方案 §P1「所有权与领取费用可见」）。

两栋建筑的家具是**有主的**：医院的白瓷工作台归值夜护士，图书馆的胡桃木书架
归图书馆本体。归属挂在**台面**上而不是物品上，有两个理由：

1. 同一张台子上的东西不该各写一份主人（改一处就够）；
2. 旧存档里的显化物没有这些字段，按落点推就能自动适用，不需要迁移。

领取代价用现有的资源结算（`settlement.settle_delta`）走账，因此在属性面板、
旧账迁移、跑批统计里都能看见——不另开一本账。
"""

from __future__ import annotations

from typing import Any

from ..i18n import tr

# 墙种 -> (主人, 资源字段, 单价)。没登记＝无主台面，随便拿。
SURFACE_TERMS: dict[str, tuple[str, str, int]] = {
    "白瓷工作台": ("值夜的护士", "mind", 1),
    "胡桃木书架": ("图书馆", "imagination", 1),
}

# 资源字段 -> 显示名（`tr(变量)` 形式，键已在语言包里）。
RESOURCE_LABELS: dict[str, str] = {
    "mind": "心智",
    "imagination": "想象",
    "lucidity": "清醒",
}


def terms_for(kind: str) -> "tuple[str, str, int] | None":
    """这个承载面归谁、取一件要付什么；无主返回 None。"""
    return SURFACE_TERMS.get(str(kind or ""))


def terms_note(kind: str) -> str:
    """格子详情里的一行说明；无主台面返回空串（调用方据此决定要不要加行）。"""
    terms = terms_for(kind)
    if not terms:
        return ""
    owner, resource, amount = terms
    return tr("台面归{owner}；每取一件付 {amount} 点{resource}。",
              owner=tr(owner), amount=amount,
              resource=tr(RESOURCE_LABELS.get(resource, resource)))


def terms_refusal(kind: str, state: Any) -> str:
    """付不起时的拒绝文案。"""
    terms = terms_for(kind)
    if not terms:
        return ""
    owner, resource, amount = terms
    label = tr(RESOURCE_LABELS.get(resource, resource))
    return tr("台面归{owner}：领取要先付 {amount} 点{resource}，你只剩 {have}。",
              owner=tr(owner), amount=amount, resource=label,
              have=int(getattr(state, resource, 0) or 0))


def pay_for_take(state: Any, kind: str) -> "str | None":
    """从这张台面取物先付代价；付清返回 None，付不起返回拒绝原因（并已扣费）。"""
    terms = terms_for(kind)
    if not terms:
        return None
    owner, resource, amount = terms
    if int(getattr(state, resource, 0) or 0) < amount:
        return terms_refusal(kind, state)
    from .settlement import REASON_ENVIRONMENT, settle_delta

    settle_delta(state, resource, -amount,
                 reason=REASON_ENVIRONMENT, source=f"承载面归属:{owner}")
    label = tr(RESOURCE_LABELS.get(resource, resource))
    state.messages.append(tr(
        "取走{owner}台面上的东西：{resource} −{amount}。",
        owner=tr(owner), resource=label, amount=amount))
    return None


def refund_take_payment(state: Any, kind: str) -> None:
    """入袋失败（行囊满）时把刚付的代价退回去——不让人「付了钱没拿到东西」。"""
    terms = terms_for(kind)
    if not terms:
        return
    owner, resource, amount = terms
    from .settlement import REASON_RESTORE_ITEM, settle_delta

    settle_delta(state, resource, amount,
                 reason=REASON_RESTORE_ITEM, source=f"承载面归属退回:{owner}")
