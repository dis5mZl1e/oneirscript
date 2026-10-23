"""篡改预警的收尾入口（薄封装）。

单独成模块是为了让时间轴（core/tempo.py）能在不导入异象技能与风险实现的前提下
挂上「下一次耗时行动」的钩子；真正的实现在 :mod:`core.tamper_risks`。
"""

from __future__ import annotations

from typing import Any


def resolve_tamper_previews(state: Any) -> None:
    """有篡改预警时才落地：页边余火生火、吞音结算。"""
    if not getattr(state, "enemy_skill_fields", None) and not getattr(state, "enemies", None):
        return
    from .tamper_risks import tamper_previews_pending

    if not tamper_previews_pending(state):
        return
    from .tamper_risks import resolve_tamper_previews as _resolve

    _resolve(state)
