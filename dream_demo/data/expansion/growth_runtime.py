"""把扩展包目录里的成长条目（记忆碎片／洞察／构想）物化成运行期定义视图。

目录 ``catalog.json`` 是内容唯一来源；这里只做**读取门面**，把已经
``integration_status == "runtime"`` 的行翻译成既有 API 需要的形状，不在
Python 里复制第二份文案。仍然 ``catalog_only`` 的行一条都不注册——
「预加入但没有获取方式」正是这次接入要消灭的状态。

记忆碎片的既有形状是三层（见 ``data/items/memories.py``、``data/memory.py``）：

1. 物品行 ``ITEMS[catalog_id]``——实物，捡起来进背包；
2. ``MEMORY_RARITY[catalog_id]``——它进入地面散投池的唯一名单；
3. ``MEMORY_FRAGMENT_EFFECTS[catalog_id]``——装进槽后真正生效的规则条目。

三者同键、同生同灭，所以测试可以断言「注册即可得、可得即生效」。
"""

from __future__ import annotations

from typing import Any

from .catalog import by_category, localized_value

MEMORY_RARITY_ORDER = ("常见", "少见", "稀有", "非常稀有")


def _runtime_rows(category: str) -> tuple[dict[str, Any], ...]:
    return tuple(entry for entry in by_category(category)
                 if entry.get("integration_status") == "runtime")


def _normalize_effect_row(row: dict[str, Any]) -> dict[str, Any]:
    """目录里的裸效果 → 既有碎片效果读取方需要的字段。

    既有读取方（``memory_portent_factor`` 等）默认每条碎片都有正的 ``value``，
    缓冲类还要 ``channel`` / ``amount`` / ``scope``；这里补齐，测试才能用同一套
    字段校验覆盖新旧碎片，而不必为扩展包另开一条宽松分支。
    """
    kind = str(row.get("kind") or "")
    if kind == "buffer":
        return {
            "kind": "buffer",
            "value": 1,
            "channel": str(row.get("channel") or ""),
            "amount": int(row.get("amount", 1)),
            "scope": str(row.get("scope") or "layer"),
            "trigger": dict(row.get("trigger") or {}),
            # absorb 决定这一声是「整声没有」还是「声径少一格」，两种承诺都要保真。
            "absorb": bool(row.get("absorb")),
        }
    normalized = dict(row)
    normalized.setdefault("value", 1)
    if kind == "resistance":
        normalized["portents"] = tuple(row.get("portents") or ())
    return normalized


def _effect_entries(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """目录里的 ``effect.runtime`` → 既有碎片效果条目（含复合折叠）。"""
    runtime = (entry.get("effect") or {}).get("runtime") or []
    rows = [_normalize_effect_row(row) for row in runtime]
    rows = [row for row in rows if row.get("kind")]
    if not rows:
        return []
    if len(rows) == 1:
        return rows
    return [{"kind": "compound", "effects": tuple(rows)}]


def memory_item_rows() -> dict[str, dict[str, Any]]:
    """记忆碎片物品行；只有已经实装的条目才会出现在这里。"""
    rows: dict[str, dict[str, Any]] = {}
    for entry in _runtime_rows("memory"):
        effect = entry.get("effect") or {}
        granted = entry.get("grant_channel_zh") or ""
        rows[entry["id"]] = {
            "name": localized_value(entry, "name"),
            "category": "记忆碎片",
            "slot": "记忆槽",
            "description": localized_value(entry, "description"),
            "color": entry.get("icon_color") or "bright_cyan",
            "effect": "memory",
            "memory_effect": entry["id"],
            # 稀有度**不**写进物品定义表：记忆碎片一律走 ``MEMORY_RARITY``，
            # ``state._make_item`` 造实例时才贴上去。写在这里会让
            # ``test_items_fully_classified`` 红，也会把记忆误塞进按定义表
            # 筛稀有度的随机池。
            # G＝统一随机池（地面散投按 min_depth 过滤）；D＝只从绑定事件来。
            "loot": entry.get("source_permission") == "G",
            "grant_source": None if entry.get("source_permission") == "G"
            else _EVENT_GRANTS.get(entry["id"]),
            "min_depth": int(entry.get("min_depth", 0) or 0),
            "run_limit": int((entry.get("tuning_proposal") or {}).get(
                "max_acquisitions_per_run", 0) or 0),
            "expansion_catalog_id": entry["id"],
            "integration_status": "runtime",
            "grant_channel": granted,
        }
    return rows


def memory_effect_rows() -> dict[str, dict[str, Any]]:
    """碎片效果行（键＝目录 id，与物品行的 ``memory_effect`` 同名）。"""
    rows: dict[str, dict[str, Any]] = {}
    for entry in _runtime_rows("memory"):
        effect = entry.get("effect") or {}
        entries = _effect_entries(entry)
        if not entries:
            continue
        short_zh = effect.get("short_zh") or entry.get("name_zh") or ""
        detail_zh = localized_value(entry, "description")
        head = entries[0]
        if head.get("kind") == "compound":
            head = {**head, "short": short_zh, "detail": detail_zh}
            rows[entry["id"]] = head
        else:
            rows[entry["id"]] = {**head, "short": short_zh, "detail": detail_zh}
    return rows


def memory_rarity_rows() -> dict[str, str]:
    return {entry["id"]: (entry.get("rarity_zh") or "常见")
            for entry in _runtime_rows("memory")}


# D 权限的成长条目由哪个既有事件授予；没有绑定的行不进任何池（保持不可得）。
_EVENT_GRANTS: dict[str, str] = {
}


# ---- 构想（ability）：一条目录行喂四张表 -------------------------------------
# 一条构想要能在游戏里点得动，必须同时出现在四个互不相让的注册表里：
#
#   ABILITY_DEFINITIONS  名称／费用／冷却／说明（数据表本身）
#   ABILITY_FACTS        八项语义口径，`docs/reference/ability_facts.md` 由它导出
#   ABILITY_FX           施法表现（profile/motion/theme）
#   AIM_SPECS            落点口径（`core/ability_targeting`）
#
# 手写四遍一定漂移，所以四份视图全部从同一行生成：目录里
# ``effect.runtime[0]`` 是效果装配参数，``effect.aim``／``effect.fx``／
# ``effect.facts`` 是配套登记。少写一块（比如 facts 不全八项）就一条都不注册，
# 宁可保持「没接入」，也不要注册出半条点不动的构想。
ABILITY_FACT_FIELDS = ("target", "range", "duration", "timing",
                       "spawns", "environment", "impact", "protection")


def _ability_head(entry: dict[str, Any]) -> dict[str, Any]:
    rows = (entry.get("effect") or {}).get("runtime") or []
    return dict(rows[0]) if len(rows) == 1 and isinstance(rows[0], dict) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ability_rows() -> dict[str, dict[str, Any]]:
    """构想定义行；只有效果与八项口径都齐备的行才会出现在这里。"""
    rows: dict[str, dict[str, Any]] = {}
    for entry in _runtime_rows("ability"):
        head = _ability_head(entry)
        effect = entry.get("effect") or {}
        if not head.get("kind") or not _fact_complete(entry):
            continue
        rows[entry["id"]] = {
            "name": localized_value(entry, "name"),
            "cost": _int(effect.get("imagination_cost")),
            "cooldown": _int(effect.get("cooldown")),
            "description": localized_value(entry, "description"),
            # 扩展包构想走既有通用随机池（残页／书本／地面散投的习得入口），
            # 但带 ``min_depth``：深层条目不会在浅层被随机塞给玩家。
            "acquire_pool": "general" if entry.get("source_permission") == "G" else "expansion_event",
            "min_depth": _int(entry.get("min_depth")),
            "run_limit": _int((entry.get("tuning_proposal") or {}).get(
                "max_acquisitions_per_run")),
            "expansion_catalog_id": entry["id"],
            "grant_channel": entry.get("grant_channel_zh") or "",
            "expansion_effect_kind": str(head["kind"]),
            "expansion_effect": head,
        }
    return rows


def _fact_complete(entry: dict[str, Any]) -> bool:
    facts = (entry.get("effect") or {}).get("facts") or {}
    return all(str(facts.get(field) or "").strip() for field in ABILITY_FACT_FIELDS)


def ability_fact_rows() -> dict[str, dict[str, str]]:
    """八项语义口径（与 ``ability_rows`` 同一批行，键相同）。"""
    rows: dict[str, dict[str, str]] = {}
    for entry in _runtime_rows("ability"):
        if not _ability_head(entry).get("kind") or not _fact_complete(entry):
            continue
        facts = (entry.get("effect") or {}).get("facts") or {}
        rows[entry["id"]] = {field: str(facts[field]) for field in ABILITY_FACT_FIELDS}
    return rows


def ability_fx_rows() -> dict[str, dict[str, str]]:
    """施法表现行；缺登记的行退回「看不见动效」而不是猜一套。"""
    rows: dict[str, dict[str, str]] = {}
    for entry in _runtime_rows("ability"):
        if not _ability_head(entry).get("kind") or not _fact_complete(entry):
            continue
        fx = (entry.get("effect") or {}).get("fx") or {}
        if fx.get("profile") and fx.get("motion"):
            rows[entry["id"]] = {"profile": str(fx["profile"]),
                                 "motion": str(fx["motion"]),
                                 "theme": str(fx.get("theme") or entry.get("theme") or "")}
    return rows


def ability_aim_rows() -> dict[str, dict[str, Any]]:
    """落点口径行（``AimSpec`` 的关键字参数）。"""
    rows: dict[str, dict[str, Any]] = {}
    for entry in _runtime_rows("ability"):
        if not _ability_head(entry).get("kind") or not _fact_complete(entry):
            continue
        aim = (entry.get("effect") or {}).get("aim") or {}
        if aim.get("form"):
            rows[entry["id"]] = {"form": str(aim["form"]),
                                 "range": _int(aim.get("range"), 12),
                                 "strict": bool(aim.get("strict")),
                                 "kind": str(aim.get("kind") or "any")}
    return rows

# ---- 洞察（2026-10-25）：目录行按**中文名**进既有洞察表 ----
# 洞察的键是人读的中文名（``INSIGHT_DEFINITIONS: dict[str, str]``），三条获取通道
# （随机池／事件掉落／异象击破）都在这个名字空间里挑；因此这里用显示名做键，
# 效果口径另存一张表，由 ``core.expansion_insights`` 按 kind 分发。

def insight_rows() -> dict[str, dict[str, Any]]:
    """只有效果 kind 齐备的洞察行才注册——没有规则的洞察是空壳提示。"""
    rows: dict[str, dict[str, Any]] = {}
    for entry in _runtime_rows("insight"):
        head = _ability_head(entry)
        if not head.get("kind"):
            continue
        rows[localized_value(entry, "name")] = {
            "description": localized_value(entry, "description"),
            # 洞察只有一张名字表，随机池直接遍历它：D 权限（事件定向获取）的行必须
            # 靠这个标记挡在随机池外，否则会在残页／盲盒里被随机塞给玩家。
            "acquire_channel": "general" if entry.get("source_permission") == "G" else "event",
            "min_depth": _int(entry.get("min_depth")),
            "grant_channel": entry.get("grant_channel_zh") or "",
            "expansion_catalog_id": entry["id"],
            "expansion_effect_kind": str(head["kind"]),
            "expansion_effect": head,
        }
    return rows
