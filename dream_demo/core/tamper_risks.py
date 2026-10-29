"""篡改风险：一次抽取、既有创伤与场地机制的适配、专属召唤（规格 §7）。

抽取只判定不执行；执行只按已确定的结果落地。风险使用独立随机来源（本局种子 +
递增篡改序号 + 实例身份 + 位置 ID），不扰动地图生成或战利品随机序列。
"""

from __future__ import annotations

import random
from typing import Any, Mapping

from ..data.ids import stable_seed
from ..data.tamper_anomalies import (
    OMISSION_ANOMALY_ID,
    OMISSION_IMAGINATION_TRAUMA,
    OMISSION_LAYER_LIMIT,
    OMISSION_RANGE,
    OMISSION_SPAWN_DISTANCE,
)
from ..data.tamper_schema import TamperRequest, RiskOutcome
from .chaos import TAMPER_SOURCE, chaos_risk_probability, chaos_risk_tier

#: 页边余火的预警族：通用效果场倒计时跳过它，只由「下一次耗时行动」收尾处理。
FIRE_PREVIEW_FAMILY = "tamper_fire_preview"
FIRE_DURATION = 3
FIRE_DISTANCE = (2, 4)
FIRE_LIFETIME_NOTE = "页边余火烧完了。"

#: 事件池（规格 §7.2）：每次提交至多抽中一个，先判定是否发生再按权重选。
TIER_POOLS: dict[str, tuple[tuple[str, int], ...]] = {
    "微弱": (("ink_blur", 1),),
    "不稳": (("ink_blur", 1), ("glyph_scar", 1)),
    "扭曲": (("tail_echo", 1), ("margin_ember", 1)),
    "错乱": (("tail_echo", 3), ("margin_ember", 3), ("omission_visitor", 2)),
    "失序": (("tail_echo", 2), ("margin_ember", 2), ("omission_visitor", 4)),
}

#: 各档效果（清醒创伤／心智创伤／火场落点数）。想象创伤另由吞音结算。
TIER_EFFECTS: dict[str, dict[str, Mapping[str, Any]]] = {
    "微弱": {"ink_blur": {"lucidity": 1}},
    "不稳": {"ink_blur": {"lucidity": 2}, "glyph_scar": {"mind": 2}},
    "扭曲": {
        "tail_echo": {"lucidity": 3, "mind": 2},
        "margin_ember": {"cells": 1},
    },
    # 2026-10-27 玩家反馈「越接近 100 越危险」：只加重错乱／失序的数值，
    # 前三档与事件池保持原样（避免全面加难度）。
    "错乱": {
        "tail_echo": {"lucidity": 6, "mind": 4},
        "margin_ember": {"cells": 3},
        "omission_visitor": {"count": 1},
    },
    "失序": {
        "tail_echo": {"lucidity": 12, "mind": 7},
        "margin_ember": {"cells": 4},
        "omission_visitor": {"count": 1},
    },
}

EVENT_LABELS: dict[str, str] = {
    "ink_blur": "墨晕",
    "glyph_scar": "字痕",
    "tail_echo": "句尾回响",
    "margin_ember": "页边余火",
    "omission_visitor": "漏字来客",
}


def _ring_cells(state: Any, low: int, high: int, *, walkable_only: bool) -> list[tuple[int, int]]:
    """玩家周围切比雪夫距离 [low, high] 的合法落点（不同格，去重后由调用方抽样）。"""
    px, py = int(state.player.x), int(state.player.y)
    cells: list[tuple[int, int]] = []
    for x in range(px - high, px + high + 1):
        for y in range(py - high, py + high + 1):
            distance = max(abs(x - px), abs(y - py))
            if not low <= distance <= high:
                continue
            if not (0 <= x < state.width and 0 <= y < state.height):
                continue
            cell = state.cell(x, y)
            if cell.solid or cell.wall_kind:
                continue
            if walkable_only and state.entity_at(x, y) is not None:
                continue
            cells.append((x, y))
    return cells


def _fire_cells(state: Any, rng: random.Random, count: int) -> list[list[int]]:
    """页边余火的落点：**点得着的**地面，避开不可占用、液体、防火地面与已占格。

    只声明真能烧起来的格子（``_ignite_cell`` 的准入条件一致：可燃地面或地上有
    可燃物）。普通地板点不着，把它当落点等于让玩家付了想象力和混乱度却什么也不
    发生；这类情况按规格 §7.2 走「零落点→该档句尾回响」，不另开一次抽签。
    """
    from .content import item_is_flammable
    from ..materials import floor_effect_for

    candidates: list[tuple[int, int]] = []
    burning_items = [(entry.x, entry.y) for entry in getattr(state, "world_items", ())
                     if item_is_flammable(entry.item)]
    for x, y in _ring_cells(state, FIRE_DISTANCE[0], FIRE_DISTANCE[1], walkable_only=False):
        cell = state.cell(x, y)
        if cell.liquid or cell.flame or cell.plant:
            continue
        if state.entity_at(x, y) is not None:
            continue
        if floor_effect_for(cell).fireproof:
            continue
        if getattr(state, "_protected_wall", None) and state._protected_wall(cell.wall_kind):
            continue
        if not (state._cell_is_flammable(cell) or (x, y) in burning_items):
            continue
        candidates.append((x, y))
    rng.shuffle(candidates)
    # 多落点只选不同格；合法落点不足时使用实际可用数量。
    return [[x, y] for x, y in candidates[:max(0, count)]]


def alive_omission_count(state: Any) -> int:
    """当前层由篡改召唤且仍存活的漏字者数量。"""
    return sum(1 for enemy in getattr(state, "enemies", ())
               if enemy.catalog_id == OMISSION_ANOMALY_ID and enemy.integrity > 0
               and (enemy.active_skill_state or {}).get("tamper_summon"))


def spawn_omission(state: Any, rng: random.Random) -> Any | None:
    """在玩家周围 3～5 的合法空格召唤一只漏字者；无合法点或达上限返回 None。"""
    if alive_omission_count(state) >= OMISSION_LAYER_LIMIT:
        return None
    candidates = _ring_cells(state, OMISSION_SPAWN_DISTANCE[0], OMISSION_SPAWN_DISTANCE[1],
                             walkable_only=True)
    if not candidates:
        return None
    x, y = candidates[rng.randrange(len(candidates))]
    enemy = state.add_defined_enemy(OMISSION_ANOMALY_ID, x, y)
    enemy.active_skill_state = dict(enemy.active_skill_state or {})
    enemy.active_skill_state["tamper_summon"] = True
    enemy.active_skill_state["summon_no_reward"] = True
    # 出生瞬间不追加即时攻击：首次进入行动循环之后才可移动与预警。
    enemy.alert_state = "追踪"
    enemy.attack_clock = 0.0
    enemy.move_clock = 0.0
    # 它是从**你刚改的那句话**里站出来的：出生即知道你在哪，直接规划追击。
    # 只写 alert_state 不给计划的话，它会在原地转身游荡（实玩里表现为「召唤出来
    # 的东西背对着玩家走开」），追逐行为等于没有。
    enemy.last_seen_x, enemy.last_seen_y = int(state.player.x), int(state.player.y)
    state._plan_chase(enemy, int(state.player.x), int(state.player.y))
    return enemy


def roll_tamper_risk(state: Any, request: TamperRequest, *, sequence: int,
                     chaos_after: int) -> RiskOutcome | None:
    """判定这一次提交的负面事件（只判定，不执行；规格 §7.4）。"""
    from ..data.tampering import definition_for

    definition = definition_for(request.text_id)
    transition = definition.transition(request.transition_id) if definition else None
    slot_id = transition.slot_id if transition else ""
    tier = chaos_risk_tier(chaos_after)
    rng = random.Random(stable_seed("tamper-risk", state.seed, sequence,
                                    request.target.instance_uid, request.text_id, slot_id))
    if rng.random() >= chaos_risk_probability(chaos_after):
        return None
    pool = TIER_POOLS.get(tier, ())
    total = sum(weight for _event, weight in pool)
    if total <= 0:
        return None
    pick = rng.randrange(total)
    event_id = pool[0][0]
    for candidate, weight in pool:
        if pick < weight:
            event_id = candidate
            break
        pick -= weight
    effects = dict(TIER_EFFECTS.get(tier, {}).get(event_id, {}))
    payload: dict[str, Any] = {"tier": tier, "label": EVENT_LABELS.get(event_id, event_id)}
    if event_id == "margin_ember":
        cells = _fire_cells(state, rng, int(effects.get("cells", 1)))
        if not cells:
            # 零落点则换为该档的句尾回响，不进行新的「是否发生」抽签。
            event_id = "tail_echo"
            effects = dict(TIER_EFFECTS.get(tier, {}).get(event_id, {}))
            payload = {"tier": tier, "label": EVENT_LABELS[event_id], "substituted": "no_fire_cells"}
        else:
            payload["cells"] = cells
    elif event_id == "omission_visitor":
        if (alive_omission_count(state) >= OMISSION_LAYER_LIMIT
                or not _ring_cells(state, OMISSION_SPAWN_DISTANCE[0], OMISSION_SPAWN_DISTANCE[1],
                                   walkable_only=True)):
            event_id = "tail_echo"
            effects = dict(TIER_EFFECTS.get(tier, {}).get(event_id, {}))
            payload = {"tier": tier, "label": EVENT_LABELS[event_id], "substituted": "omission_limit"}
    payload.update({key: value for key, value in effects.items() if key != "cells"})
    return RiskOutcome(event_id, payload)


def _hurt(state: Any, *, lucidity: int = 0, mind: int = 0, imagination: int = 0) -> list[str]:
    """走既有创伤结算：照常受护持与免疫影响，不写负数资源、不绕过死亡判定。"""
    from ..i18n import tr

    notes: list[str] = []
    if lucidity:
        state._enemy_skill_trauma(None, int(lucidity), "清醒")
        notes.append(tr("清醒创伤 {n}", n=int(lucidity)))
    if mind:
        state._enemy_skill_trauma(None, int(mind), "心智")
        notes.append(tr("心智创伤 {n}", n=int(mind)))
    if imagination:
        from .settlement import REASON_TAMPER_COST, settle_delta
        settle_delta(state, 'imagination', -int(imagination),
                     reason=REASON_TAMPER_COST, source='篡改风险')
        notes.append(tr("想象创伤 {n}", n=int(imagination)))
    state.last_harm_source = "篡改风险"
    state.last_harm_time = int(state.time)
    state._check_run_over()
    return notes


def execute_tamper_risk(state: Any, outcome: RiskOutcome, *, source_uid: str) -> str:
    """执行已确定的风险结果，返回玩家可见反馈（不揭示概率与事件池）。"""
    from ..i18n import tr

    payload = dict(outcome.payload or {})
    label = str(payload.get("label") or EVENT_LABELS.get(outcome.event_id, outcome.event_id))
    if outcome.event_id == 'tail_echo':
        # The backlash enters the world as a real audible source; subsequent
        # creatures investigate it through the same hearing rules as any noise.
        state._sound_pulse(state.player.x, state.player.y, 10, by_player=True)
    if outcome.event_id == "margin_ember":
        cells = [list(cell) for cell in payload.get("cells") or []]
        if cells:
            state.enemy_skill_fields.append({
                "source_id": source_uid or "tamper.risk",
                "family": FIRE_PREVIEW_FAMILY,
                "cells": cells,
                "channel": "无",
                "rounds_left": 0,
                "tick_damage": 0,
                "max_ticks": 0,
                "ticks_done": 0,
                "damage_enemies": False,
                "born_paid_action_seq": int(getattr(state, "paid_action_seq", 0)),
                "note": FIRE_LIFETIME_NOTE,
            })
            return tr("页边余火：纸边泛起焦痕，{n} 处地面开始发烫。", n=len(cells))
        return ""
    if outcome.event_id == "omission_visitor":
        rng = random.Random(stable_seed("tamper-summon", state.seed, source_uid, state.time))
        enemy = spawn_omission(state, rng)
        if enemy is None:
            fallback = TIER_EFFECTS.get(str(payload.get("tier", "")), {}).get("tail_echo", {})
            notes = _hurt(state, lucidity=int(fallback.get("lucidity", 0)),
                          mind=int(fallback.get("mind", 0)))
            return tr("句尾回响在你耳边重复了一遍。") + ("（" + "、".join(notes) + "）" if notes else "")
        return tr("漏字来客：句子的空缺里站出一个人形——脚步声总少一拍。")
    notes = _hurt(state, lucidity=int(payload.get("lucidity", 0)), mind=int(payload.get("mind", 0)),
                  imagination=int(payload.get("imagination", 0)))
    detail = ("（" + "、".join(notes) + "）") if notes else ""
    return tr("{label}：改过的句子在你脑后回响。", label=tr(label)) + detail


def tamper_previews_pending(state: Any) -> bool:
    """有没有「等下一次耗时行动落地」的篡改预警。"""
    paid = int(getattr(state, "paid_action_seq", 0))
    return any(field.get("family") == FIRE_PREVIEW_FAMILY
               and int(field.get("born_paid_action_seq", 0)) < paid
               for field in getattr(state, "enemy_skill_fields", ()) or ())


def resolve_tamper_previews(state: Any) -> None:
    """耗时行动收尾：预警落地成普通火焰（持续 3 回合），预警本身没有立即伤害。"""
    from ..i18n import tr

    paid = int(getattr(state, "paid_action_seq", 0))
    fields = getattr(state, "enemy_skill_fields", None)
    if not fields:
        return
    due = [field for field in fields
           if field.get("family") == FIRE_PREVIEW_FAMILY
           and int(field.get("born_paid_action_seq", 0)) < paid]
    if not due:
        return
    for field in due:
        fields.remove(field)
        cells = [list(cell) for cell in field.get("cells") or []]
        lit: list[list[int]] = []
        for x, y in cells:
            if not (0 <= int(x) < state.width and 0 <= int(y) < state.height):
                continue
            if state.cell(int(x), int(y)).solid:
                continue
            if state._ignite_cell(int(x), int(y), strength=3, attribute_player=False):
                lit.append([int(x), int(y)])
        if not lit:
            # 落点在这几拍里变湿／被占：预警照常消耗，但要给玩家一句可观察的交代。
            state.messages.append(tr("页边的焦痕冷了下去，没有烧起来。"))
            continue
        fields.append({
            "source_id": str(field.get("source_id") or "tamper.risk"),
            "family": "ember",
            "cells": lit,
            "channel": "清醒",
            "rounds_left": FIRE_DURATION,
            "tick_damage": 0,
            "max_ticks": 0,
            "ticks_done": 0,
            "damage_enemies": False,
            "note": FIRE_LIFETIME_NOTE,
        })
        state.messages.append(tr("页边的焦痕烧起来了——{n} 处火场。", n=len(lit)))

# --- 专属技能「吞音」：预警 → 玩家下一次耗时行动后结算（规格 §7.3）---


def cast(state: Any, enemy: Any, skill: Any, binding: Any):
    """预警条件：目标可见且距离不超过 4 格。"""
    if not state._sk_player_visible(enemy, skill.max_range):
        return None
    target = (int(state.player.x), int(state.player.y))
    return ([target], None, target, {
        "warn_paid_seq": int(getattr(state, "paid_action_seq", 0)),
        "imagination": OMISSION_IMAGINATION_TRAUMA,
        "range": OMISSION_RANGE,
    })


def resolve(state: Any, enemy: Any, skill: Any, pending: dict) -> None:
    """结算：仍在距离与视线内才造成想象创伤 3。"""
    from ..i18n import tr

    meta = dict(pending.get("meta") or {})
    if int(getattr(state, "paid_action_seq", 0)) <= int(meta.get("warn_paid_seq", -1)):
        # 免费操作不能顶开「玩家已行动」窗口：把预警放回去，等下一次耗时行动。
        state._skill_state(enemy)["pending"] = pending
        return
    reach = int(meta.get("range", skill.max_range))
    distance = max(abs(int(enemy.x) - int(state.player.x)), abs(int(enemy.y) - int(state.player.y)))
    if distance > reach or not state._has_line_of_sight(enemy.x, enemy.y, state.player.x, state.player.y):
        state.messages.append(tr("{enemy}张了张口，声音没有找到你。", enemy=tr(enemy.label)))
        return
    amount = int(meta.get("imagination", OMISSION_IMAGINATION_TRAUMA))
    from .settlement import REASON_TAMPER_COST, settle_delta
    settle_delta(state, 'imagination', -amount,
                 reason=REASON_TAMPER_COST, source='篡改·吞音')
    state.last_harm_source = "篡改·吞音"
    state.last_harm_time = int(state.time)
    state.run_stats["hits_taken"] = int(state.run_stats.get("hits_taken", 0)) + 1
    state.messages.append(tr("{enemy}吞掉了你刚想起的词（想象创伤 {n}）。",
                             enemy=tr(enemy.label), n=amount))


def register_omission_skill() -> None:
    """把吞音挂进异象技能引擎（Python 定义技能，不改工作簿）。"""
    from .enemy_skills import EnemySkillMixin

    EnemySkillMixin._SKILL_CASTERS["tamper.omission_voice"] = cast
    EnemySkillMixin._SKILL_RESOLVERS["tamper.omission_voice"] = resolve
