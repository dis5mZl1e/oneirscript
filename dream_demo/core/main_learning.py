"""主线基础工具选择：替换普通奖励槽，领取事实跨楼层永久保存。"""
from __future__ import annotations

EVENT_ID = "main.learning_tools"


def record(state):
    return state.world_ledger.facility(
        f"{state.run_uid}:main-learning:{state.depth}",
        layer_key=state.layer_key(), definition_id=EVENT_ID)


def enabled(state):
    return (state.difficulty_revision >= 2 and not state.realm_id
            and state.depth in (3, 5))


def reserve_tool_choice(state, rolled, pity_count):
    """先保证可达位置与合法三选一；已领取层重建仍扣除原槽，防止刷奖励。"""
    if not enabled(state) or len(rolled) <= pity_count:
        return
    if any(e.event_id == EVENT_ID for e in state.events):
        return
    from .main_difficulty import _reachable
    from .item_access import refusal
    from .entities import WorldEvent
    claimed = record(state).flags.get("claimed")
    if claimed:
        del rolled[len(rolled) - pity_count - 1]
        return
    # 三种无需装备/构想前置的现有消耗工具。不是额外的技能或永久增益。
    ids = ("coiled_spring", "clockwork_half", "clear_glass")
    if any(refusal(state, item_id, source="event:" + EVENT_ID) for item_id in ids):
        return
    occupied = {(e.x, e.y) for e in state.events}
    occupied.update((e.x, e.y) for e in state.enemies if e.integrity > 0)
    occupied.update((e.x, e.y) for e in state.world_items)
    positions = sorted(_reachable(state), key=lambda p: (
        abs(p[0] - state.player.x) + abs(p[1] - state.player.y), p[1], p[0]))
    position = next((p for p in positions if p not in occupied
                     and p != (state.player.x, state.player.y)
                     and not state.cell(*p).solid and not state.cell(*p).flame
                     and not state.cell(*p).gas and not state.cell(*p).liquid), None)
    if position is None:
        return
    labels = (
        "{item}：推开相邻目标；一次性使用，可能造成撞墙伤害。",
        "{item}：让 3 格内目标减速 3 回合；一次性使用。",
        "{item}：恢复 10 点清醒度（不超过上限）；一次性使用。",
    )
    options = tuple({"option_id": EVENT_ID + "." + item_id,
                     "label": label, "reward_id": item_id}
                    for item_id, label in zip(ids, labels))
    state.events.append(WorldEvent(
        EVENT_ID, "行前工具台", *position,
        "取一件随身工具。领取耗一次行动；之后从行囊使用，使用后消耗。第五层可以再次选择，补上此前缺少的应对方式。",
        catalog_id=EVENT_ID, kind="compound", bound=True,
        dissolution_reward=0, options=options))
    del rolled[len(rolled) - pity_count - 1]
