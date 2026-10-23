"""报价成交事务（重构方案 §13.1／§13.5）。

交易规则本身（预览→足额支付→原子提交）仍在 ``core/actions.py`` 的结算路径里，
这里先接走两件事，避免新规则继续往 ``actions.py`` 堆：

1. **成交事实**：每笔成立的报价写一条 ``transfer``/``pact``/``settle`` 事实，
   关系、任务与之后的代收点都读这一份记录（§7.3 归属、§4.4 责任）。
2. **预览与提交的口径分离**：预览调用 ``facts.record(..., observe=False)``，
   不得改变世界记录（§13.4 第 2 步）。
"""
from __future__ import annotations

from typing import Any

from .facts import record


def record_offer(state: Any, npc: Any, option_id: str, *, kind: str = "transfer",
                 target_uid: str = "", amount: int = 1,
                 witness_uids: Any = None) -> dict[str, Any]:
    """登记一笔已成立的报价成交。

    ``option_id`` 是稳定 offer ID（``content.npc_option_key``），不是显示下标：
    §13.2 要求记账与后续查询都按它走，货架重抽才不会把功劳记到别人头上。
    """
    return record(
        state, kind,
        actor_uid=getattr(npc, "actor_uid", "") or getattr(npc, "id", ""),
        target_uid=target_uid,
        position=(int(npc.x), int(npc.y)),
        source_kind="npc_offer",
        cause_uid=option_id,
        amount=amount,
        witness_uids=witness_uids,
    )
