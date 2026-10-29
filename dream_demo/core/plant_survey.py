"""本层植物总览（docs 2026-10-26 §10.1「环境总览」）。

格子详情回答「这一格还有什么」，这里回答「这一层还剩些什么」。两处必须
同源：都读真实 ``Cell`` 与 ``plant_state``，不读渲染缓存、不按 PlantDef
的默认值假装还有余量——耗尽/已释出的株在这里必须计入「已耗尽」，否则
玩家会以为还能再去吸一次、再踩一次。

统计口径（与 §10.1 一致）：
- **按株计**，不按格数分摊；
- H2 同时占「表面」与「高处」，但在这里只算**一株**，不重复计数；
- 一次性释出株看 ``released``；周期株看格子里自己的 ``budget:<code>``。

缓存按 ``(id(state), depth, plant_revision)``：植物码变化必然推进
``plant_revision``（见 ``state.set_plant_at``），预算变化由常驻结算推进它，
所以缓存不会读到过期的余量；跨层/换存档换 key。
"""

from __future__ import annotations

from typing import Any

from ..materials.plants import plant_budget_key, plant_def_for, plant_release_for

#: 通道 -> 总览里的标签（顺序即显示顺序）。
CHANNEL_LABELS: tuple[tuple[str, str], ...] = (
    ("absorb", "可吸"),
    ("push", "可搬"),
    ("purify", "可净"),
    ("fire", "可炸"),
    ("electric", "可电"),
    ("integrity", "可削"),
    ("gas", "可放气"),
    ("liquid", "可放液"),
    ("snare", "可缠"),
)

_CACHE: dict[tuple[int, int, int], dict[str, int]] = {}


def _release_channels(release) -> tuple[str, ...]:
    """这条释出配方实际会动的通道（按 §3.4.1 的结算顺序）。"""
    if release is None:
        return ()
    names: list[str] = []
    if release.ignite:
        names.append("fire")
    if release.electric:
        names.append("electric")
    if release.integrity:
        names.append("integrity")
    if release.gas:
        names.append("gas")
    if release.liquid:
        names.append("liquid")
    if release.portent:
        names.append("snare")
    return tuple(names)


def survey_layer(state: Any, *, use_cache: bool = True) -> dict[str, int]:
    """统计本层植物：总数、高株、已耗尽，以及各通道还剩几株能做那件事。"""
    revision = int(getattr(state, "plant_revision", 0) or 0)
    key = (id(state), int(getattr(state, "depth", 0) or 0), revision)
    if use_cache:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
    counts: dict[str, int] = {"total": 0, "tall": 0, "spent": 0}
    for _, label in CHANNEL_LABELS:
        counts[label] = 0
    for row in getattr(state, "cells", ()) or ():
        for cell in row:
            code = int(getattr(cell, "plant", 0) or 0)
            if not code:
                continue
            definition = plant_def_for(code)
            if definition is None:
                continue
            state_of_cell = cell.plant_state if isinstance(cell.plant_state, dict) else {}
            counts["total"] += 1
            if int(definition.height) >= 2:
                counts["tall"] += 1
            released = bool(state_of_cell.get("released"))
            budget_left = None
            if definition.has_periodic:
                budget_left = state_of_cell.get(plant_budget_key(code))
                if budget_left is None:
                    # 还没结算过：按定义给满额（与 tick_periodic_plants 同口径）。
                    budget_left = max(
                        definition.absorb_gas_budget, definition.absorb_liquid_budget,
                        definition.push_gas_budget, definition.purify_budget,
                    )
                budget_left = int(budget_left)
            exhausted = released or (budget_left is not None and budget_left <= 0)
            if exhausted:
                counts["spent"] += 1
                continue  # 耗尽/已释出的株不再计入「还能做什么」
            if definition.has_periodic and budget_left:
                if definition.absorb_gas or definition.absorb_liquid:
                    counts["可吸"] += 1
                if definition.push_gas_budget:
                    counts["可搬"] += 1
                if definition.purify_budget:
                    counts["可净"] += 1
            for channel in _release_channels(plant_release_for(code)):
                label = dict(CHANNEL_LABELS).get(channel)
                if label:
                    counts[label] += 1
    if use_cache:
        # 缓存只留最近若干层，避免长时间游玩后无限增长。
        if len(_CACHE) > 64:
            _CACHE.clear()
        _CACHE[key] = counts
    return counts


def summary_line(state: Any, *, survey: dict[str, int] | None = None) -> str:
    """总览用的一句话；没有植物时返回空串（不显示一行「0 株」占位）。"""
    from ..i18n import tr
    data = survey if survey is not None else survey_layer(state)
    total = int(data.get("total", 0))
    if total <= 0:
        return ""
    parts: list[str] = []
    if data.get("tall"):
        parts.append(tr("高 {n}", n=int(data["tall"])))
    for _, label in CHANNEL_LABELS:
        value = int(data.get(label, 0))
        if value:
            parts.append(tr("{label} {n}", label=tr(label), n=value))
    if data.get("spent"):
        parts.append(tr("已耗尽 {n}", n=int(data["spent"])))
    body = " · ".join(parts) if parts else tr("全部完好")
    return tr("本层植物 {total} 株（{body}）", total=total, body=body)


def invalidate() -> None:
    """测试/换存档用：清掉统计缓存。"""
    _CACHE.clear()
