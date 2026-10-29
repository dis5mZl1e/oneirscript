"""混乱度极高时召来的专属异象（2026-10-27 玩家需求）。

公开接口（沿用 Lead 骨架的签名）：

- alive_chaos_anomaly_count：当前层仍存活的专属异象数。
- spawn_chaos_anomaly：在玩家周围 3–5 的合法空格召来一只；
  完整度 = 基础 + 当前层数 × 每层增量；无掉落（no_loot）；不占自然刷怪上限。
- maybe_tamper_chaos：一次成功篡改提交后的召唤判定（可能返回 None）。
- tick_chaos_anomalies：每个世界回合推进；混乱 > 阈值时极低概率成形。

投放/数值/技能/文案都在 data/chaos_anomalies.py；随机源用
data.ids.stable_seed 保持可复现，不扰动地图与战利品序列。
"""

from __future__ import annotations

import random
from typing import Any

from ..data.chaos_anomalies import (
    CHAOS_ANOMALIES,
    CHAOS_ANOMALY_IDS,
    CHAOS_ANOMALY_LAYER_LIMIT,
    CHAOS_ANOMALY_LAYERS,
    CHAOS_ANOMALY_THRESHOLD,
    CHAOS_INTEGRITY_BASE,
    CHAOS_INTEGRITY_PER_DEPTH,
    CHAOS_SPAWN_DISTANCE,
    CHAOS_TAMPER_SPAWN_CHANCE,
    CHAOS_TIME_SPAWN_CHANCE,
)
from ..data.ids import stable_seed
from ..i18n import tr


def _depth(state: Any) -> int:
    try:
        return max(1, int(getattr(state, "depth", 1) or 1))
    except (TypeError, ValueError):
        return 1


def _chaos(state: Any) -> int:
    try:
        return int(getattr(state, "chaos", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _realm(state: Any) -> str:
    return str(getattr(state, "realm_id", "") or "")


def _in_main_layer(state: Any) -> bool:
    """专属异象只在主梦 1–27 层成形（深层边界/位面另有专属内容）。"""
    return CHAOS_ANOMALY_LAYERS[0] <= _depth(state) <= CHAOS_ANOMALY_LAYERS[1]


def _event_cells(state: Any) -> set:
    cells = set()
    for event in getattr(state, "events", ()) or ():
        try:
            cells.add((int(event.x), int(event.y)))
        except (AttributeError, TypeError, ValueError):
            continue
    return cells


def alive_chaos_anomaly_count(state: Any) -> int:
    """当前层仍存活的专属异象数（按目录 ID 判定，兼容缺旗标的旧存档）。"""
    return sum(
        1 for enemy in getattr(state, "enemies", ()) or ()
        if getattr(enemy, "catalog_id", "") in CHAOS_ANOMALIES
        and int(getattr(enemy, "integrity", 0) or 0) > 0
    )


def _spawn_cells(state: Any) -> list:
    """玩家切比雪夫 3–5 的合法空格：避开墙、实体与事件落点。"""
    try:
        px, py = int(state.player.x), int(state.player.y)
    except (AttributeError, TypeError, ValueError):
        return []
    low, high = CHAOS_SPAWN_DISTANCE
    blocked = _event_cells(state)
    cells = []
    for x in range(px - high, px + high + 1):
        for y in range(py - high, py + high + 1):
            distance = max(abs(x - px), abs(y - py))
            if not low <= distance <= high:
                continue
            if not (0 <= x < int(state.width) and 0 <= y < int(state.height)):
                continue
            if (x, y) in blocked:
                continue
            cell = state.cell(x, y)
            if cell.solid or cell.wall_kind:
                continue
            if state.entity_at(x, y) is not None:
                continue
            cells.append((x, y))
    return cells


def _summon_rng(state: Any, reason: str) -> random.Random:
    """召唤随机源：本局种子 + 层数 + 时间 + 篡改序号 + 理由，可复现。"""
    return random.Random(stable_seed(
        "chaos-spawn",
        getattr(state, "seed", 0),
        _depth(state),
        int(getattr(state, "time", 0) or 0),
        int(getattr(state, "tamper_sequence", 0) or 0),
        reason,
    ))


def _integrity_for_depth(depth: int) -> int:
    """最大完整度随层数成长：基础值 + 每层增量 × 当前层数。"""
    return int(CHAOS_INTEGRITY_BASE + CHAOS_INTEGRITY_PER_DEPTH * max(1, int(depth)))


def spawn_chaos_anomaly(state: Any, anomaly_id: str | None = None, *,
                        reason: str = "tamper") -> Any | None:
    """在玩家周围 3–5 的合法空格召来一只专属异象；无合法点/达上限返回 None。

    完整度以 override 写入（随层数成长）；active_skill_state 记
    chaos_summon/no_loot/max_integrity；出生即知道玩家位置并规划追击。
    """
    if getattr(state, "run_over", False) or _realm(state):
        return None
    if alive_chaos_anomaly_count(state) >= CHAOS_ANOMALY_LAYER_LIMIT:
        return None
    candidates = _spawn_cells(state)
    if not candidates:
        return None
    rng = _summon_rng(state, reason)
    if anomaly_id not in CHAOS_ANOMALIES:
        anomaly_id = CHAOS_ANOMALY_IDS[rng.randrange(len(CHAOS_ANOMALY_IDS))]
    x, y = candidates[rng.randrange(len(candidates))]
    integrity = _integrity_for_depth(_depth(state))
    enemy = state.add_defined_enemy(
        anomaly_id, x, y, integrity=integrity, spawn_wave=0,
    )
    enemy.active_skill_state = dict(enemy.active_skill_state or {})
    enemy.active_skill_state["chaos_summon"] = True
    enemy.active_skill_state["no_loot"] = True
    enemy.active_skill_state["max_integrity"] = integrity
    enemy.alert_state = "追踪"
    # 出生瞬间不追加即时攻击：首次进入行动循环之后才可移动与预警。
    enemy.attack_clock = 0.0
    enemy.move_clock = 0.0
    # 它是从混乱里成形的：出生即知道玩家位置，直接规划追击（只写 alert_state
    # 不给计划的话会在原地转身游荡）。
    enemy.last_seen_x, enemy.last_seen_y = int(state.player.x), int(state.player.y)
    state._plan_chase(enemy, int(state.player.x), int(state.player.y))
    return enemy


def _summon_message(state: Any, enemy: Any, *, reason: str) -> None:
    label = tr(getattr(enemy, "label", "") or "")
    if reason == "tamper":
        template = "混乱在你改过的句子边上站起一个剪影——{name}。"
    else:
        template = "混乱在一个空处聚拢成形——{name}已经站在你附近。"
    state.messages.append(tr(template, name=label))


def maybe_tamper_chaos(state: Any) -> Any | None:
    """一次成功篡改提交后的召唤判定；混乱不达阈值/位面/死亡时不改动世界。"""
    if getattr(state, "run_over", False) or _realm(state):
        return None
    if _chaos(state) <= int(CHAOS_ANOMALY_THRESHOLD):
        return None
    if alive_chaos_anomaly_count(state) >= CHAOS_ANOMALY_LAYER_LIMIT:
        return None
    rng = random.Random(stable_seed(
        "chaos-tamper",
        getattr(state, "seed", 0),
        int(getattr(state, "tamper_sequence", 0) or 0),
        int(getattr(state, "time", 0) or 0),
    ))
    if rng.random() >= float(CHAOS_TAMPER_SPAWN_CHANCE):
        return None
    enemy = spawn_chaos_anomaly(state, reason="tamper")
    if enemy is None:
        return None
    _summon_message(state, enemy, reason="tamper")
    return enemy


def tick_chaos_anomalies(state: Any, rounds: int) -> None:
    """每真实回合推进：混乱 > 阈值时按极低概率在玩家身边成形一只。"""
    amount = int(rounds or 0)
    if amount <= 0:
        return
    if getattr(state, "run_over", False) or _realm(state) or not _in_main_layer(state):
        return
    if _chaos(state) <= int(CHAOS_ANOMALY_THRESHOLD):
        return
    counter = int(getattr(state, "_chaos_tick_counter", 0) or 0)
    for _ in range(amount):
        if alive_chaos_anomaly_count(state) >= CHAOS_ANOMALY_LAYER_LIMIT:
            state._chaos_tick_counter = counter
            return
        counter += 1
        rng = random.Random(stable_seed(
            "chaos-time",
            getattr(state, "seed", 0),
            int(getattr(state, "time", 0) or 0),
            counter,
        ))
        if rng.random() >= float(CHAOS_TIME_SPAWN_CHANCE):
            continue
        enemy = spawn_chaos_anomaly(state, reason="time")
        if enemy is None:
            continue
        # 稀有提示：低概率事件让玩家知道「这不是普通刷怪」。
        state.messages.append(tr(
            "梦层深处的混乱挤成一个人形——{name}在你身边成形。",
            name=tr(getattr(enemy, "label", "") or ""),
        ))
    state._chaos_tick_counter = counter
