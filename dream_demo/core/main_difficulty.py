"""主线难度阶段配置：0 为原曲线，1 削弱后期，2 增加前期工具与混编。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections import deque

CURRENT_DIFFICULTY_REVISION = 3


@dataclass(frozen=True)
class MainDifficultyProfile:
    ordinary_quota: int
    ordinary_integrity: int
    strong_budget: int
    trauma_factor: float
    descent_cost: int
    core_integrity: int | None = None
    core_power: int | None = None
    roaming_range: tuple[int, int] = (0, 0)
    roaming_integrity_factor: float = 1.0


def main_difficulty_profile(depth: int, revision: int) -> MainDifficultyProfile:
    """纯查询；深度为目标层时 descent_cost 表示进入该层的基础清醒费用。"""
    quota = 10 + (4 if depth >= 11 else 0) + (2 if depth >= 21 else 0)
    integrity = max(2 if depth <= 3 else 1,
                    1 + depth // 4 if depth < 21 else 3 + depth // 9)
    budget = 1 if depth < 10 else 2 if depth <= 20 else 3
    cost = 3 if depth <= 10 else 4
    core_hp = {10: 25, 20: 45, 27: 64, 30: 80}.get(depth)
    core_power = {10: 4, 20: 5, 27: 7, 30: 4}.get(depth)
    roaming = {28: (12, 18), 29: (18, 24), 30: (8, 12)}.get(depth, (0, 0))
    roaming_scale = {28: 1.25, 29: 1.5, 30: 1.75}.get(depth, 1.0)
    factor = 1.0
    if revision >= 1:
        if depth == 10:
            quota, budget = 8, 1
        elif 11 <= depth <= 19:
            quota = 12
            if depth >= 16:
                integrity, factor = 4, .90
        elif depth == 20:
            quota, integrity, budget, factor = 9, 4, 1, .90
            core_hp, core_power = 36, 4
        elif 21 <= depth <= 26:
            quota, budget, factor, cost = 12, 2, .85, 3
        elif depth == 27:
            quota, integrity, budget, factor, cost = 8, 5, 1, .85, 3
            core_hp, core_power = 48, 6
        elif depth >= 28:
            roaming = {28: (8, 10), 29: (10, 12), 30: (6, 8)}.get(depth, (0, 0))
            budget = {28: 2, 29: 3, 30: 2}.get(depth, 2)
            roaming_scale = {28: 1.0, 29: 1.1, 30: 1.2}.get(depth, 1.2)
    return MainDifficultyProfile(quota, integrity, budget, factor, cost,
                                 core_hp, core_power, roaming, roaming_scale)


def active_profile(state: Any, depth: int | None = None) -> MainDifficultyProfile | None:
    """分支与旧局完全沿用原有管线。"""
    revision = getattr(state, "difficulty_revision", 0)
    if revision < 1 or state.realm_id:
        return None
    return main_difficulty_profile(state.depth if depth is None else depth, revision)


def effective_melee_power(state: Any, enemy: Any, base: int) -> int:
    profile = active_profile(state)
    if profile is None:
        return base
    core_id = {10: "anomaly.hollow_lighthouse", 20: "anomaly.unfinished_period",
               27: "anomaly.first_cry", 30: "anomaly.scribe"}.get(state.depth)
    if enemy.catalog_id == core_id and profile.core_power is not None:
        return profile.core_power
    return effective_skill_power(state, enemy, base)


def effective_skill_power(state: Any, enemy: Any, base: int) -> int:
    profile = active_profile(state)
    if (profile is None or enemy is None or base <= 0
            or enemy.anomaly_kind == "核心执念"):
        return base
    return max(1, int(base * profile.trauma_factor + .5))


def current_anomaly_definition(state: Any, catalog_id: str) -> dict:
    """当前目标的显示值；不改图鉴持有的基础定义与分支规则。"""
    from types import SimpleNamespace
    from .content import ANOMALY_DEFINITIONS
    definition = dict(ANOMALY_DEFINITIONS.get(catalog_id, {}))
    profile = active_profile(state)
    if profile is None:
        return definition
    proxy = SimpleNamespace(catalog_id=catalog_id,
                            anomaly_kind=definition.get("anomaly_kind", ""))
    power = effective_melee_power(state, proxy, int(definition.get("power", 1)))
    definition["damage"] = max(1, round(power * state._enemy_trauma_mult()))
    if proxy.anomaly_kind == "核心执念" and profile.core_integrity is not None:
        definition["integrity"] = max(1, round(profile.core_integrity * state._enemy_integrity_mult()))
    # 同名单位可能包含不同耐久的场景目标；聚合只取已可知个体的最高生成上限，
    # 逐个体详情仍使用各自 max_integrity，不把全局基础定义当作实际上限。
    known = [
        e.active_skill_state.get("max_integrity")
        for e in state.enemies if e.catalog_id == catalog_id and e.integrity > 0
        and (state.reveals_anomalies or state.is_visible(e.x, e.y))
    ]
    known = [value for value in known if isinstance(value, (int, float)) and value > 0]
    if known:
        definition["integrity"] = int(max(known))
    return definition


def current_skill_summaries(state: Any, catalog_id: str) -> list[dict]:
    from types import SimpleNamespace
    from ..data.anomaly_skills import skill_summaries_for
    from .content import ANOMALY_DEFINITIONS
    layer = state.entry_depth if state.realm_id else state.depth
    summaries = skill_summaries_for(catalog_id, layer)
    if active_profile(state) is None:
        return summaries
    proxy = SimpleNamespace(anomaly_kind=ANOMALY_DEFINITIONS.get(catalog_id, {}).get("anomaly_kind", ""))
    for summary in summaries:
        power = effective_skill_power(state, proxy, summary["trauma_value"])
        summary["trauma_value"] = max(0, round(power * state._enemy_trauma_mult()))
    return summaries


PROGRESS_EVENT_ID = "main.deconstruction"


def _record(state: Any):
    """设施记录不随 ±3 层快照窗口裁剪，不使用会过期的瞬时事实。"""
    return state.world_ledger.facility(
        f"{state.run_uid}:main-difficulty:{state.depth}",
        layer_key=state.layer_key(), definition_id="main_difficulty")


def _reachable(state: Any) -> set[tuple[int, int]]:
    from ..materials import DOOR_KINDS
    origin = state.player.x, state.player.y
    seen = {origin}
    queue = deque([origin])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < state.width and 0 <= ny < state.height) or (nx, ny) in seen:
                continue
            cell = state.cell(nx, ny)
            if cell.solid and cell.wall_kind not in DOOR_KINDS:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return seen


def _remaining(state: Any, reachable: set[tuple[int, int]]):
    return [e for e in state.enemies if e.integrity > 0
            and e.relation == "失控意识" and e.anomaly_kind != "核心执念"
            and not e.drop_spawned
            and not e.active_skill_state.get("summon_no_reward")
            and (e.x, e.y) in reachable]


def _credit(state: Any, amount: int) -> int:
    """保底按已结算进度补缺，不再被增速/深层耐性二次扣减。"""
    from ..i18n import tr
    amount = max(0, min(100 - state.dissolution, int(amount)))
    if amount:
        # 崩解度是层进度，不是 settlement 的三项心理资源；与 _add_dissolution
        # 使用同一 100 上限，实际领取量由设施 credited 永久记账。
        state.dissolution += amount
        if state.dissolution >= 100:
            state.messages.append(tr("崩解度已达 100：可以下潜了（按 N）。"))
    return amount


def install_progress_site(state: Any) -> None:
    """新生成常规层：还原永久进度，再安装需要的可达补缺点。"""
    if active_profile(state) is None or not 1 <= state.depth <= 26:
        return
    record = _record(state)
    if record.flags.get("cleared"):
        _credit(state, 100 - state.dissolution)
    elif record.flags.get("progress_claimed"):
        _credit(state, record.stock.get("credited", 0))
    refresh_progress_site(state)


def refresh_progress_site(state: Any) -> None:
    """击破后刷新：核心与无奖励召唤物不阻挡普通层完成保底。"""
    if active_profile(state) is None or not 1 <= state.depth <= 26:
        return
    from .entities import WorldEvent
    record = _record(state)
    reachable = _reachable(state)
    remaining = _remaining(state, reachable)
    if not remaining:
        record.flags["cleared"] = True
        if record.flags.get("progress_claimed") and not record.flags.get("clear_settled"):
            _credit(state, 100 - state.dissolution)
            record.flags["clear_settled"] = True
    if record.flags.get("progress_claimed"):
        return
    if not record.flags.get("progress_budgeted"):
        expected = sum(max(0, e.dissolution_reward) for e in remaining)
        record.stock["progress_reward"] = max(0, 110 - expected)
        record.flags["progress_budgeted"] = True
    reward = record.stock["progress_reward"]
    if not remaining:
        reward = max(reward, 100 - state.dissolution)
    if not reward or any(e.event_id == PROGRESS_EVENT_ID for e in state.events):
        return
    occupied = {(e.x, e.y) for e in state.events}
    occupied.update((e.x, e.y) for e in state.enemies if e.integrity > 0)
    ordered = sorted(reachable, key=lambda p: (
        abs(p[0] - state.player.x) + abs(p[1] - state.player.y), p[1], p[0]))
    # 只选不需要破墙/付费、无明显环境伤害的可走格，不挖穿剧情门。
    positions = [p for p in ordered if p not in occupied and not state.cell(*p).solid
                 and not state.cell(*p).flame and not state.cell(*p).gas
                 and not state.cell(*p).liquid]
    if not positions:
        return
    x, y = positions[0]
    state.events.append(WorldEvent(
        PROGRESS_EVENT_ID, "梦层解构点", x, y,
        "沿裂纹解开这一层的结。回应只补充本层崩解度，不留下显化物。",
        dissolution_reward=reward, catalog_id=PROGRESS_EVENT_ID, bound=True))


def resolve_progress_site(state: Any, event: Any):
    from ..i18n import tr
    from .constants import ActionKind
    from .entities import ActionResult
    if active_profile(state) is None or not 1 <= state.depth <= 26:
        return ActionResult(False, tr("这处裂纹已经合拢。"))
    record = _record(state)
    if event.resolved or record.flags.get("progress_claimed"):
        return ActionResult(False, tr("这处裂纹已经合拢。"))
    remaining = _remaining(state, _reachable(state))
    reward = record.stock.get("progress_reward", 0)
    if not remaining:
        reward = max(reward, 100 - state.dissolution)
        record.flags["cleared"] = True
        record.flags["clear_settled"] = True
    record.flags["progress_claimed"] = True
    event.resolved, event.uses_left = True, 0
    record.stock["credited"] = _credit(state, reward)
    state.run_stats["events"] = state.run_stats.get("events", 0) + 1
    state._action_time(1, ActionKind.USE)
    message = tr("裂纹松开了：本层崩解度增加 {amount}。", amount=record.stock["credited"])
    state.messages.append(message)
    return ActionResult(True, message, {"event": event.event_id})


def reserve_recovery_slot(state: Any, rolled: list, pity_count: int) -> bool:
    """11/21 首次到达按需替换一个普通槽，绝不覆盖稀有保底或加份数。"""
    if active_profile(state) is None or state.depth not in (11, 21):
        return False
    record = _record(state)
    if record.flags.get("recovery_checked"):
        return False
    record.flags["recovery_checked"] = True
    normal_end = len(rolled) - pity_count
    if state.max_lucidity <= 0 or state.lucidity / state.max_lucidity >= .4 or normal_end <= 0:
        return False
    from .item_access import refusal
    if refusal(state, "clear_glass", source="floor_scatter"):
        return False
    if not any(item_id == "clear_glass" for item_id, _ in rolled):
        rolled[0] = ("clear_glass", "常见")
    return True
