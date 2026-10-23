"""远程武器系统（2026-09-19，与弹道 ballistics / 投掷 throwing 并列）。

三类可装备远程武器的核心结算：

- **喷系武器**（喷水枪/吹风机，effect spray_liquid / spray_gas）：发射液态
  记忆/弥散印象。弹道沿用直线逻辑；被墙体/固体挡下时，材料沉积在**弹道的
  前一格**；撞上意识体时沉积在**其所在格**；飞满距离则沉积在最后一格。
  弹药优先取行囊中**非空**的对应容器（枪对液、吹风机对气，一次只喷一种）；
  没有可用容器时退化为少量清水/水蒸气。每次发射耗费少量想象力。
- **直射武器规格**（定义表 "fire" 字段）：发射时间 / 加伤 / 追加穿透 /
  击退 / 命中征兆 / 命中声波，逐武器刻意区分。
- **一次性发射物**（effect fire_once）：直线飞出，撞上第一个障碍或意识体后
  按定义表的 `payload` 分岔——光焰弹（flare）尝试点燃撞击格，电弧弹（arc）
  接通真实电场。两者共用弹道几何，不共用名称、消息与载荷。

本模块不依赖 textual/rich；效果结算通过传入的 state（GameState）完成。
"""

from __future__ import annotations

from typing import Any

from ..i18n import tr
from .ballistics import trace_path

# 喷射的弹道距离（格）。
SPRAY_RANGE = 8
# 每次发射的想象力消耗（少量）。
SPRAY_COST = 2
# 从容器抽取 / 自带水源的沉积量。
SPRAY_AMOUNT = 12
SPRAY_BUILTIN_AMOUNT = 6
# 沉积视为「低浓度」。
SPRAY_DEPOSIT_CAP = 20


def hand_weapon(state: Any) -> tuple[Any, dict[str, Any] | None]:
    """(手持物品, 定义表附加信息)。无手持物品时 (None, None)。"""
    item = state._active_hand_item()
    if item is None:
        return None, None
    from .content import ITEM_DEFINITIONS

    definition = ITEM_DEFINITIONS.get(item.definition_id) or {}
    return item, definition


def hand_spray_medium(state: Any) -> str | None:
    """手持喷系武器的介质（"liquid"/"gas"）；非喷系武器返回 None。"""
    modes = {mode[6:] for row in state.equipment.formation().actions
             for mode in row.action_modes if mode.startswith("spray_")}
    return next(iter(modes)) if len(modes) == 1 else None


def spray_plan(state, source_index, *, choice=None, target=None, cell=None):
    from ..equipment.runtime import ActionPlan
    medium = None
    if source_index is not None:
        if not 0 <= source_index < len(state.inventory):
            return ActionPlan("spray", False, reason="意识行囊中没有这个承载位。")
        from .content import ITEM_DEFINITIONS
        item = state.inventory[source_index]
        medium = ITEM_DEFINITIONS.get(item.definition_id, {}).get("container", {}).get("medium")
        if medium not in ("liquid", "gas") or not pick_ammo_kind(item):
            return ActionPlan("spray", False, reason="容器中没有可用的对应材料。")
    modes = sorted({mode for row in state.equipment.formation().actions
                    for mode in row.action_modes if mode.startswith("spray_")
                    and (medium is None or mode == "spray_" + medium)})
    options = [c for mode in modes for c in state.equipment.action_choices(mode, target=target, cell=cell)]
    if choice is not None:
        selected = next((c for c in options if c.key == choice), None)
        if selected is None:
            return ActionPlan("spray", False, reason="本次动作选项已经失效")
    elif len(options) == 1:
        selected = options[0]
    else:
        return ActionPlan("spray", False, reason=("请选择本次动作的发射方式" if options
                                                   else "没有成立的对应动作句"))
    plan = state.equipment.plan_action(selected.kind, choice=selected.key, target=target, cell=cell)
    _, reason = bound_spray_source(state, plan, source_index)
    if reason:
        from dataclasses import replace
        return replace(plan, valid=False, reason=reason)
    return plan


def bound_spray_source(state, plan, source_index):
    """Resolve a grammatical source by physical ID, and recheck real stock."""
    if not plan.material_source_id:
        return source_index, ''
    from .content import ITEM_DEFINITIONS
    index = next((i for i, item in enumerate(state.inventory)
                  if item.instance_id == plan.material_source_id and item.quantity > 0), None)
    if index is None:
        return None, '指定的材料来源已失效。'
    if source_index is not None and source_index != index:
        return None, '本句只能从绑定的容器取材。'
    item = state.inventory[index]
    medium = ITEM_DEFINITIONS.get(item.definition_id, {}).get('container', {}).get('medium')
    if medium != dict(plan.projectile_profile).get('medium') or not pick_ammo_kind(item):
        return None, '容器中没有可用的对应材料。'
    return index, ''


def hand_fire_spec(state: Any) -> dict[str, Any] | None:
    """手持直射武器的 "fire" 规格表；普通武器返回 None（走默认发射）。"""
    _, definition = hand_weapon(state)
    if not definition:
        return None
    return definition.get("fire")


def spray_ammo_options(state: Any, medium: str) -> list[tuple[int, str, str, int]]:
    """行囊中**非空**的对应容器：[(行囊下标, 容器名, 材料名, 数量)]。"""
    from .content import ITEM_DEFINITIONS

    options: list[tuple[int, str, str, int]] = []
    for index, item in enumerate(state.inventory):
        spec = (ITEM_DEFINITIONS.get(item.definition_id, {}) or {}).get("container", {})
        if spec.get("medium") != medium:
            continue
        for kind, amount in item.contents.items():
            if amount > 0:
                options.append((index, item.name, kind, amount))
                break  # 每只容器只列主要装的一种
    return options


def pick_ammo_kind(container_item: Any) -> tuple[str, int] | None:
    """容器内实际喷出的（材料名, 可用量）：多分装容器取存量最多的一种。"""
    best: tuple[str, int] | None = None
    for kind, amount in container_item.contents.items():
        if amount > 0 and (best is None or amount > best[1]):
            best = (kind, amount)
    return best


def resolve_spray(
    state: Any,
    medium: str,
    kind: str,
    amount: int,
    source_index: int | None,
    path_cells: list[tuple[int, int]],
    *, cost: int = SPRAY_COST, feedback_plan=None,
) -> tuple[str, dict[str, Any]]:
    """沿弹道喷射： Deposit 规则——墙前一格 / 意识体所在格 / 射程末端。

    消耗：容器（source_index 指向行囊下标）或 None=自带水源；同时扣少量想象力。
    返回 (消息, 附加 data)。
    """
    if amount <= 0 or state.imagination < cost:
        return tr("容器中没有可用的对应材料。"), {}
    source_container = None
    if source_index is not None:
        if not 0 <= source_index < len(state.inventory):
            return tr("意识行囊中没有这个承载位。"), {}
        source_container = state.inventory[source_index]
        amount = min(amount, source_container.contents.get(kind, 0))
        if amount <= 0:
            return tr("容器中没有可用的对应材料。"), {}
    deposit: tuple[int, int] | None = None
    hit_entity = None
    prev: tuple[int, int] | None = None
    flight = []
    for x, y in path_cells:
        if not state.inside_board(x, y):
            break
        cell = state.cell(x, y)
        if cell.solid:
            deposit = prev  # 挡在墙上：材料留在弹道的前一格
            break
        entity = state.entity_at(x, y)
        flight.append((x, y))
        if entity is not None and entity is not state.player:
            deposit = (x, y)  # 打在意识体上：留在其所在格
            hit_entity = entity
            break
        prev = (x, y)
        deposit = (x, y)  # 飞满距离：落在最后一格
    if deposit is None:
        return tr("水线还没成形就散了。"), {}
    dx, dy = deposit
    target_cell = state.cell(dx, dy)
    decay_mark = (state.time-source_container.gas_decay_age.get(kind,0)
                  if source_container is not None and medium == 'gas' else None)
    # 消耗容器（自带水源无容器可扣）。
    if source_container is not None:
        source_container.contents[kind] -= amount
        if source_container.contents[kind] == 0:
            del source_container.contents[kind]
            source_container.gas_decay_age.pop(kind,None)
    from .settlement import REASON_ABILITY_COST, settle_delta
    settle_delta(state, 'imagination', -cost, reason=REASON_ABILITY_COST,
                 source='武器构想')
    if medium == "liquid":
        state._add_liquid(target_cell, kind, amount)
    else:
        state._add_gas(target_cell, kind, amount, decay_mark=decay_mark)
    if hit_entity is not None and feedback_plan is not None and 'conduct' in feedback_plan.feedback_opcodes:
        from ..equipment.positional_events import execute_feedback
        execute_feedback(state, 'conduct', cell=deposit, target=hit_entity)
    state._note_projectile(flight, [], kind="shot", color="#91e7ef",
                           end="entity" if hit_entity is not None else "land", end_cell=deposit)
    medium_name = tr("液态记忆") if medium == "liquid" else tr("弥散印象")
    if hit_entity is not None:
        message = tr(
            "{medium}泼在 {entity} 身上，留下薄薄一层。",
            medium=medium_name, entity=tr(hit_entity.label),
        )
    else:
        message = tr("{medium}泼在梦的表面（{kind} {amount}）。", medium=medium_name, kind=kind, amount=amount)
    return message, {"position": [dx, dy], "amount": amount, "kind": kind}


def spray_fire(state: Any, source_index: int | None, dx: int, dy: int, *, plan=None) -> tuple[str, dict[str, Any]]:
    """定向喷射：直线弹道，最远 SPRAY_RANGE 格。"""
    from .content import ITEM_DEFINITIONS

    plan = plan or spray_plan(state, source_index)
    if not plan.valid:
        return tr(plan.reason), {}
    source_index, reason = bound_spray_source(state, plan, source_index)
    if reason:
        return tr(reason), {}
    spec = dict(plan.projectile_profile)
    medium = spec["medium"]
    path: list[tuple[int, int]] = []
    for x, y in trace_path(state.player.x, state.player.y, dx, dy):
        if max(abs(x - state.player.x), abs(y - state.player.y)) > SPRAY_RANGE:
            break
        path.append((x, y))
    kind, amount = _ammo_for(state, source_index, spec, medium)
    if source_index is not None:
        from ..equipment.runtime import action_effect_power
        amount += action_effect_power(state, "spray_boost", plan.rows) * 6
    return _resolve_spray_phases(state,plan,medium,kind,amount,source_index,path,
                                 cost=int(spec.get('cost',SPRAY_COST)))


def spray_target(state: Any, source_index: int | None, tx: int, ty: int, *, plan=None) -> tuple[str, dict[str, Any]]:
    """瞄准喷射：沿「玩家 → 目标格」的直线（与辅助发射同一路径语义）。"""
    plan = plan or spray_plan(state, source_index, target=state.entity_at(tx,ty), cell=(tx,ty))
    if not plan.valid:
        return tr(plan.reason), {}
    source_index, reason = bound_spray_source(state, plan, source_index)
    if reason:
        return tr(reason), {}
    spec = dict(plan.projectile_profile)
    medium = spec["medium"]
    path: list[tuple[int, int]] = []
    x, y = state.player.x, state.player.y
    while (x, y) != (tx, ty):
        if len(path) >= SPRAY_RANGE:
            break
        if x != tx:
            x += 1 if tx > x else -1
        if y != ty:
            y += 1 if ty > y else -1
        path.append((x, y))
    kind, amount = _ammo_for(state, source_index, spec, medium)
    if source_index is not None:
        from ..equipment.runtime import action_effect_power
        amount += action_effect_power(state, "spray_boost", plan.rows) * 6
    return _resolve_spray_phases(state,plan,medium,kind,amount,source_index,path,
                                 cost=int(spec.get('cost',SPRAY_COST)),aim_cell=(tx,ty))


def _resolve_spray_phases(state,plan,medium,kind,amount,source_index,path,*,cost,aim_cell=None):
    if not plan.repeat_source_ids or amount < 2:
        return resolve_spray(state,medium,kind,amount,source_index,path,cost=cost,feedback_plan=plan)
    from ..equipment.repetition import record_phase,claim_repeat
    origin = (state.player.x,state.player.y)
    source_id = state.inventory[source_index].instance_id if source_index is not None else None
    first_amount,first_cost = (amount+1)//2,(cost+1)//2
    message,data = resolve_spray(state,medium,kind,first_amount,source_index,path,cost=first_cost,feedback_plan=plan)
    if not data:
        return message,data
    record_phase(state,plan,plan.kind,data['amount'],cell=tuple(data['position']))
    data['equipment_repeat_phases'] = 1
    current_index = next((i for i,item in enumerate(state.inventory) if item.instance_id == source_id
                          and item.quantity > 0),None) if source_id is not None else None
    source_ok = (source_id is None or (current_index is not None
                 and state.inventory[current_index].contents.get(kind,0) > 0))
    if source_id is not None and source_ok:
        from .content import ITEM_DEFINITIONS
        source_ok = ITEM_DEFINITIONS.get(state.inventory[current_index].definition_id,{}).get(
                    'container',{}).get('medium') == medium
    cell = aim_cell or tuple(data['position'])
    target = state.entity_at(*cell)
    if (source_ok and (state.player.x,state.player.y) == origin
            and state.imagination >= cost-first_cost
            and claim_repeat(state,plan,plan.kind,cell=cell,target=target)):
        _,second = resolve_spray(state,medium,kind,amount-first_amount,current_index,path,
                                cost=cost-first_cost,feedback_plan=plan)
        if second:
            record_phase(state,plan,plan.kind,second['amount'],cell=tuple(second['position']))
            data['amount'] += second['amount']
            data['position'] = second['position']
            data['equipment_repeat_phases'] = 2
            point = tuple(second['position'])
            state._emit_combat_fx('spray',point,[point])
            return message,data
    data['equipment_repeat_reason'] = '追加已停止：资源或落点已改变。'
    return message+' '+tr(data['equipment_repeat_reason']),data


def _ammo_for(state: Any, source_index: int | None, spec: dict[str, Any], medium: str) -> tuple[str, int]:
    if source_index is not None and 0 <= source_index < len(state.inventory):
        picked = pick_ammo_kind(state.inventory[source_index])
        if picked:
            return picked[0], min(picked[1], SPRAY_AMOUNT)
    builtin_kind = spec.get("builtin_kind", "水" if medium == "liquid" else "水蒸气")
    return builtin_kind, int(spec.get("builtin_amount", SPRAY_BUILTIN_AMOUNT))


def fire_once_payload(item: Any) -> str:
    """物品级载荷身份：两种弹共用飞行基础，撞击后按定义表各走各的结算。"""
    from .content import ITEM_DEFINITIONS
    spec = ITEM_DEFINITIONS.get(getattr(item, "definition_id", ""), {}) or {}
    return str(spec.get("payload") or "flare")


def _projectile_impact(state: Any, item: Any, path_cells: list[tuple[int, int]]):
    """沿弹道求出撞击格与命中的意识体，直接创伤取物品自己的 power。"""
    prev: tuple[int, int] | None = (state.player.x, state.player.y)
    for x, y in path_cells:
        if state.cell(x, y).solid:
            return prev, None
        entity = state.entity_at(x, y)
        if entity is not None and entity is not state.player:
            state._player_strike(entity, "ranged", damage=int(item.power or 2))
            if entity.integrity <= 0:
                state._resolve_enemy(entity)
            return (x, y), entity
        prev = (x, y)
    return prev, None


def _arc_bolt_impact(state: Any, impact: tuple[int, int], hit_entity: Any) -> tuple[str, dict[str, Any]]:
    """电弧弹载荷：接通本合集真实电场，既不点火也不额外叠一份爆炸。

    电场由 ``_charge_electric_field`` 持久化，逐回合结算时玩家、稳定意识与
    失控意识都在同一批格子里受电——电流敌我共担。
    """
    extra = {"position": [impact[0], impact[1]]}
    zone = state._conductive_zone(impact)
    if not zone:
        if hit_entity is not None:
            return tr("电弧弹在 {entity} 身上跳成一道短路，这里没有可传播的导电介质。",
                      entity=tr(hit_entity.label)), extra
        return tr("电弧弹打在绝缘的表面上，电弧只闪了一下就散了。"), extra
    state._charge_electric_field(zone, source='arc_bolt', origin=impact)
    state._emit_combat_fx("electric", impact, zone)
    if hit_entity is not None:
        return tr("电弧弹在 {entity} 身上接通 {count} 格导电介质，电场留在原地等谁踩。",
                  entity=tr(hit_entity.label), count=len(zone)), extra
    return tr("电弧弹落在导电介质上，接通 {count} 格电场。", count=len(zone)), extra


def fire_once_resolve(state: Any, item: Any, path_cells: list[tuple[int, int]]) -> tuple[str, dict[str, Any]]:
    """一次性发射物：直线飞出，撞上第一个障碍/意识体后按各自载荷结算。"""
    impact, hit_entity = _projectile_impact(state, item, path_cells)
    if impact is None:
        return tr("{name}没有落点。", name=tr(item.name)), {}
    if fire_once_payload(item) == "arc":
        return _arc_bolt_impact(state, impact, hit_entity)
    ignited = state._ignite_cell(impact[0], impact[1], 3, by_player=True)
    if hit_entity is not None:
        message = tr("光焰弹在 {entity} 身上烧成一小片光。", entity=tr(hit_entity.label))
    elif ignited:
        message = tr("光焰弹炸开，火焰照亮了一小片梦。")
    else:
        message = tr("光焰弹烧尽了，什么也没有点着。")
    return message, {"position": [impact[0], impact[1]]}
