"""扩展包装备的运行期行为（2026-10-25 批次一：声源与调查 + 液体被动）。

两类行为都只走既有结算：

* **被动契约**：``integration_status == "runtime"`` 的装备在联想盘上编成
  ``Ability``，本模块只提供「读」的函数；真正的挂钩点分散在声学、
  材料附着与命中/受击回调里（``core/enemies.py``、``core/acoustics.py``、
  ``core/portents.py``、``core/equipment_board.py``）。
* **主动行为**：``ITEM_DEFINITIONS[...]["active_use"]`` 描述形态（self /
  point / pair / direction）、选点范围与处理名。玩家在行囊里「使用」时复用
  既有的 ``deploy_aim`` 协议；成功才扣一次行动，物品本身不消耗（次数型
  行为由 ``state.equipment_marks`` 记）。

场地装置记录沿用 ``core/item_devices.py`` 的 ``realm_features['item_devices']``，
每回合由该模块的 ``tick`` 转交本模块的 ``tick_record``。

设计口径（docs/superpowers/specs/2026-10-25-item-diversity-catalog.md）：

* 声源一律走 ``state._sound_pulse``——不直接改敌人警戒，不绕开声路衰减、
  听觉上限与「不覆盖视觉 last_seen」。
* 「诱引」与「普通声」的差别只用 ``category``：``lure`` 吃蜂鸣回响/忙音加成，
  ``item`` / ``step`` 吃降噪。
* 液体只经 ``_grant_material_portents`` 授予，不新写一套附着层。
"""

from __future__ import annotations

from typing import Any, Callable

from ..i18n import tr
from .expansion_runtime import active_effects, claim, params, ready


# ---------------------------------------------------------------------------
# 读取被动契约
# ---------------------------------------------------------------------------

def _abilities(state: Any, effect: str) -> tuple[Any, ...]:
    return active_effects(state, effect)


def has_passive(state: Any, effect: str) -> bool:
    return bool(_abilities(state, effect))


def passive_value(state: Any, effect: str, key: str, default: int = 0) -> int:
    for ability in _abilities(state, effect):
        value = int(params(ability).get(key, default) or 0)
        if value:
            return value
    return default


def _mark_key(item: Any, name: str) -> str:
    return f"gear:{getattr(item, 'instance_id', '')}:{name}"


def _mark(state: Any, item: Any, name: str) -> dict:
    marks = getattr(state, "equipment_marks", None)
    if not isinstance(marks, dict):
        return {}
    record = marks.get(_mark_key(item, name))
    return record if isinstance(record, dict) else {}


def _set_mark(state: Any, item: Any, name: str, value: dict | None) -> None:
    key = _mark_key(item, name)
    if value:
        state.equipment_marks[key] = value
    else:
        state.equipment_marks.pop(key, None)


def _equipped(state: Any, item: Any) -> bool:
    try:
        return getattr(item, "instance_id", "") in state.equipped.values()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 声源修正：诱引改向（S-E07 铁漏斗 / S-E15 指挥棒）
# ---------------------------------------------------------------------------

def arm_funnel(state: Any, item: Any, direction: tuple[int, int], spec: dict) -> None:
    """把下一次主动诱引声导向正前方：声源前移、声径收窄。"""
    dx, dy = int(direction[0]), int(direction[1])
    _set_mark(state, item, "funnel", {
        "dx": dx, "dy": dy,
        "offset": int(spec.get("offset", 2) or 2),
        "radius_delta": int(spec.get("radius_delta", -2) or -2),
        "until": int(state.time) + int(spec.get("turns", 4) or 4),
    })


def redirect_lure(state: Any, x: int, y: int, radius: int) -> tuple[int, int, int]:
    """玩家主动诱引声的改向：指挥棒的命中刻痕优先，其次铁漏斗的朝向。"""
    # 指挥棒：一次真实命中把下一次诱引定在落点。
    for ability in _abilities(state, "lure_mark_on_hit"):
        key = f"funnel_mark:{ability.instance_id}"
        mark = state.equipment_marks.get(key)
        if not isinstance(mark, dict):
            continue
        if int(mark.get("until", 0) or 0) < int(state.time):
            state.equipment_marks.pop(key, None)
            continue
        state.equipment_marks.pop(key, None)
        return int(mark.get("x", x)), int(mark.get("y", y)), int(radius)
    # 铁漏斗：声源沿朝向挪一格，声径按方案收窄。
    for item_id, item in _carried_items(state, "arm_funnel"):
        mark = _mark(state, item, "funnel")
        if not mark or int(mark.get("until", 0) or 0) < int(state.time):
            if mark:
                _set_mark(state, item, "funnel", None)
            continue
        offset = int(mark.get("offset", 2) or 2)
        nx = int(x) + int(mark.get("dx", 0) or 0) * offset
        ny = int(y) + int(mark.get("dy", 0) or 0) * offset
        if not state.inside_board(nx, ny) or state.cell(nx, ny).solid:
            nx, ny = int(x), int(y)
        _set_mark(state, item, "funnel", None)
        return nx, ny, max(1, int(radius) + int(mark.get("radius_delta", -2) or -2))
    return int(x), int(y), int(radius)


def _carried_items(state: Any, behavior: str):
    from ..data.items import ITEM_DEFINITIONS

    for item in getattr(state, "inventory", ()):
        definition = ITEM_DEFINITIONS.get(item.definition_id, {})
        active = definition.get("active_use") or {}
        if str(active.get("behavior") or "") != behavior:
            continue
        if not _equipped(state, item):
            continue
        yield item.definition_id, item


# ---------------------------------------------------------------------------
# 声源修正：回音分账（S-E12）
# ---------------------------------------------------------------------------

def schedule_echo(state: Any, x: int, y: int, radius: int, source: str) -> None:
    """主动诱引分两回合发出：第二声从同一落点重放，不跟随玩家。

    ``passive_value`` 在没有对应能力时会返回默认值——所以这里必须先判
    ``has_passive``，否则**没带分账器的每一次诱引**都会被排成两段。
    """
    if not has_passive(state, "lure_echo_split"):
        return
    delay = passive_value(state, "lure_echo_split", "delay_turns", 0)
    if delay <= 0:
        return
    pending = getattr(state, "delayed_sounds", None)
    if not isinstance(pending, list):
        return
    pending.append({"x": int(x), "y": int(y), "due": int(state.time) + delay,
                    "radius": int(radius), "source": source or tr("回音分账器")})


# ---------------------------------------------------------------------------
# 声源修正：传声筒（S-E14）
# ---------------------------------------------------------------------------

def pipe_exit(state: Any, x: int, y: int) -> tuple[int, int] | None:
    """声源落在某个传声口旁边时，给它另一端的出口坐标。"""
    for record in _devices(state, "gear_pipe"):
        data = record.get("data") or {}
        for near, far in ((tuple(data.get("a", ())), tuple(data.get("b", ()))),
                          (tuple(data.get("b", ())), tuple(data.get("a", ())))):
            if len(near) != 2 or len(far) != 2:
                continue
            if max(abs(int(near[0]) - int(x)), abs(int(near[1]) - int(y))) <= 1:
                return int(far[0]), int(far[1])
    return None


# ---------------------------------------------------------------------------
# 声源修正：空椅吸收（S-E16）
# ---------------------------------------------------------------------------

def absorb_into_chair(state: Any, x: int, y: int, radius: int,
                      category: str, source: str) -> bool:
    """先吸一声非爆炸噪音，两回合后按原强度从椅子放出。"""
    if category == "explosion":
        return False
    for record in _devices(state, "gear_chair"):
        data = record.setdefault("data", {})
        if data.get("absorbed"):
            continue
        cx, cy = int(record.get("x", 0)), int(record.get("y", 0))
        reach = int(data.get("radius", 4) or 4)
        if max(abs(cx - int(x)), abs(cy - int(y))) > reach:
            continue
        data["absorbed"] = True
        data["due"] = int(state.time) + int(data.get("delay", 2) or 2)
        data["strength"] = int(radius)
        data["category"] = str(category)
        data["source"] = str(source)
        state.messages.append(tr("最后那排空椅把这一声吞了下去。"))
        return True
    return False


# ---------------------------------------------------------------------------
# 受击 / 命中 / 移动 回调
# ---------------------------------------------------------------------------

def on_player_hurt(state: Any, kind: str, amount: int, *, source_id: str = "") -> None:
    """S-E06 没有铃舌的铃：受击后响一次强诱引，主动摇动无效。"""
    if int(amount) <= 0:
        return
    for ability in _abilities(state, "lure_on_hurt"):
        if not ready(state, ability):
            continue
        radius = int(params(ability).get("radius", 10) or 10)
        state._sound_pulse(state.player.x, state.player.y, radius, by_player=True,
                           full_alert=True, category="lure",
                           source=tr("没有铃舌的铃"))
        claim(state, ability, int(params(ability).get("cooldown_turns", 4) or 4))
        state.messages.append(tr("铃在没有铃舌的情况下响了一声——那声音替你喊了出来。"))
        break


def note_hit_mark(state: Any, target: Any) -> None:
    """S-E15 乐池的指挥棒：真实命中后把落点留给下一次诱引。"""
    if target is None:
        return
    for ability in _abilities(state, "lure_mark_on_hit"):
        state.equipment_marks[f"funnel_mark:{ability.instance_id}"] = {
            "x": int(getattr(target, "x", 0)),
            "y": int(getattr(target, "y", 0)),
            "until": int(state.time) + int(params(ability).get("mark_turns", 3) or 3),
        }
        break


def note_player_step(state: Any, origin, destination) -> None:
    """S-E13 借来的脚步机：记录最近三步真实落脚格。

    起点与上一步的终点是同一格（走了两步就是三格），所以按「连续重复只留一次」
    合并——不然三个额度会被一格的两端重复占掉，实际只剩两步。
    """
    for _item_id, item in _carried_items(state, "record_steps"):
        mark = _mark(state, item, "steps") or {"cells": []}
        merged = [list(cell) for cell in (mark.get("cells") or ())]
        for cell in (origin, destination):
            point = [int(cell[0]), int(cell[1])]
            if not merged or merged[-1] != point:
                merged.append(point)
        _set_mark(state, item, "steps", {"cells": merged[-3:]})
    # 光类装备里唯一「移动即失效」的是摄影师的黑披布（架起来的遮光面会倒）。
    from . import gear_light

    gear_light.cancel_on_move(state)


# ---------------------------------------------------------------------------
# 液体附着抑制（H-E01 木底鞋 / H-E14 沉箱工作服）
# ---------------------------------------------------------------------------

def suit_sealed(state: Any) -> bool:
    """沉箱工作服是否处于封闭状态（封闭期不能盛取与喷射）。"""
    sealed = False
    for item in getattr(state, "inventory", ()):
        mark = _mark(state, item, "seal")
        if mark and int(mark.get("until", 0) or 0) > int(state.time):
            sealed = True
    return sealed


def block_liquid_attachment(state: Any, cell: Any) -> bool:
    """这一次液体接触是否不授予附着。返回 True 表示已挡下。

    * 沉箱工作服封闭期内一律挡下。
    * 木底鞋每层首次踏过**薄**液面挡下一次，之后需离开液体晾干。
    """
    if suit_sealed(state):
        return True
    thin = passive_value(state, "thin_liquid_step", "thin_amount", 12)
    for ability in _abilities(state, "thin_liquid_step"):
        key = f"thin_sole:{ability.instance_id}"
        mark = state.equipment_marks.get(key)
        if not isinstance(mark, dict) or int(mark.get("depth", -1)) != int(state.depth):
            mark = {"depth": int(state.depth), "used": 0}
        if int(mark.get("used", 0) or 0) > 0:
            state.equipment_marks[key] = mark
            return False
        if int(getattr(cell, "liquid", 0) or 0) >= thin:
            state.equipment_marks[key] = mark
            return False
        mark["used"] = int(mark.get("used", 0)) + 1
        state.equipment_marks[key] = mark
        state.messages.append(tr("木底鞋的槽里积了一点液面——这一下没沾上。"))
        return True
    return False


# ---------------------------------------------------------------------------
# 声学：隔音软帘（S-E11）
# ---------------------------------------------------------------------------

def curtain_cells(state: Any) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for record in _devices(state, "gear_curtain"):
        for point in (record.get("data") or {}).get("cells", ()):
            if len(point) == 2:
                cells.add((int(point[0]), int(point[1])))
    return cells


# ---------------------------------------------------------------------------
# 装置记录
# ---------------------------------------------------------------------------

def _devices(state: Any, kind: str) -> list[dict]:
    from ..core.item_devices import devices

    return [record for record in devices(state)
            if str(record.get("kind", "")) == kind]


def _register(state: Any, kind: str, x: int, y: int, turns: int, **data) -> dict:
    """登记装置的**唯一入口**：所有装备的布放都从这里过。

    返程封套（`expansion.realm.e16`）收回的装置带着原剩余回合，重新布放时
    必须按它继续，而不是给一份全新时限——所以在入口处统一问一次。
    """
    from ..core.item_devices import register_device

    instance_id = str(data.get("instance_id") or "")
    if instance_id:
        from .remaining_gear import packed_turns

        turns = packed_turns(state, instance_id, kind, turns)
    return register_device(state, kind, x, y, turns, **data)


# ---------------------------------------------------------------------------
# 主动行为（self）
# ---------------------------------------------------------------------------

def _sole_noise(state: Any, item: Any, spec: dict) -> tuple[bool, str, dict]:
    mark = _mark(state, item, "sole") or {"depth": -1, "left": 0}
    if int(mark.get("depth", -1)) != int(state.depth):
        mark = {"depth": int(state.depth),
                "left": int(spec.get("charges_per_layer", 3) or 3)}
    if int(mark.get("left", 0) or 0) <= 0:
        _set_mark(state, item, "sole", mark)
        return False, tr("这一层的鞋垫已经全踩碎了。"), {}
    mark["left"] = int(mark["left"]) - 1
    _set_mark(state, item, "sole", mark)
    radius = int(spec.get("radius", 8) or 8)
    state._sound_pulse(state.player.x, state.player.y, radius, by_player=True, category="item",
                       source=item.name)
    message = tr("鞋垫在脚下碎开——本层还剩 {n} 片。", n=mark["left"])
    return True, message, {"noise_radius": radius, "left": mark["left"]}


def _seal_suit(state: Any, item: Any, spec: dict) -> tuple[bool, str, dict]:
    # 目录里的键是 duration_turns；旧键 duration 保留为兼容回退。
    duration = int(spec.get("duration_turns", spec.get("duration", 3)) or 3)
    _set_mark(state, item, "seal", {"until": int(state.time) + duration})
    message = tr("你把工作服的外层封死了——{n} 回合内不会沾上新的液体，但也盛不了东西。",
                 n=duration)
    return True, message, {"sealed_turns": duration}


_SELF_BEHAVIORS: dict[str, Callable[..., tuple[bool, str, dict]]] = {
    "sole_noise": _sole_noise,
    "seal_suit": _seal_suit,
}


# ---------------------------------------------------------------------------
# 主动行为（point / pair / direction）
# ---------------------------------------------------------------------------

def _roll_bell(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    dx, dy = int(point[0]), int(point[1])
    if not (dx or dy):
        return False, tr("没有方向，铃轴滚不出去。"), {}
    x, y = state.player.x + dx, state.player.y + dy
    if not state.inside_board(x, y) or state.cell(x, y).solid:
        return False, tr("铃轴推不出去——那边是墙。"), {}
    turns = int(spec.get("turns", 8) or 8)
    _register(state, "gear_bell", x, y, turns,
              definition_id=item.definition_id, instance_id=item.instance_id,
              dx=dx, dy=dy, radius=int(spec.get("radius", 6) or 6))
    _detach_for_device(state, item)
    message = tr("铃轴贴着墙根滚了出去，一路都带着响。")
    return True, message, {"device": "gear_bell"}


def _arm_funnel_active(state: Any, item: Any, spec: dict,
                       point) -> tuple[bool, str, dict]:
    arm_funnel(state, item, (int(point[0]), int(point[1])), spec)
    message = tr("漏斗扣上了——下一次诱引会朝那个方向收窄。")
    return True, message, {}


def _sound_curtain(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    cells = point
    first, second = tuple(cells[0]), tuple(cells[1])
    if max(abs(first[0] - second[0]), abs(first[1] - second[1])) > 1:
        return False, tr("软帘只能挂在相邻的两格之间。"), {}
    turns = int(spec.get("turns", 8) or 8)
    _register(state, "gear_curtain", int(first[0]), int(first[1]), turns,
              definition_id=item.definition_id, instance_id=item.instance_id,
              cells=[[int(first[0]), int(first[1])], [int(second[0]), int(second[1])]])
    _detach_for_device(state, item)
    message = tr("软帘挂起来了——穿过这两格的声音会哑一分，你自己的也一样。")
    return True, message, {"device": "gear_curtain"}


def _sound_pipe(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    first, second = tuple(point[0]), tuple(point[1])
    turns = int(spec.get("turns", 10) or 10)
    _register(state, "gear_pipe", int(first[0]), int(first[1]), turns,
              definition_id=item.definition_id, instance_id=item.instance_id,
              a=[int(first[0]), int(first[1])], b=[int(second[0]), int(second[1])])
    _detach_for_device(state, item)
    message = tr("两只传声筒接好了——声音会从另一头出来，一点也不会更响。")
    return True, message, {"device": "gear_pipe"}


def _record_steps(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    x, y = int(point[0]), int(point[1])
    mark = _mark(state, item, "steps") or {"cells": []}
    cells = [list(cell) for cell in (mark.get("cells") or ())]
    if len(cells) < 2:
        return False, tr("脚步机还没记下足够的步子——先走两步再来。"), {}
    anchor = cells[-1]
    offsets = [[int(cell[0]) - anchor[0], int(cell[1]) - anchor[1]] for cell in cells]
    turns = int(spec.get("turns", 4) or 4)
    _register(state, "gear_recorder", x, y, turns,
              definition_id=item.definition_id,
              offsets=offsets, radius=int(spec.get("radius", 3) or 3), step=0)
    _detach_for_device(state, item)
    _set_mark(state, item, "steps", None)
    message = tr("脚步机在落点放下了——它会把刚才那几步重新走一遍。")
    return True, message, {"device": "gear_recorder"}


def _deploy_chair(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    x, y = int(point[0]), int(point[1])
    turns = int(spec.get("turns", 12) or 12)
    _register(state, "gear_chair", x, y, turns,
              definition_id=item.definition_id,
              radius=int(spec.get("radius", 4) or 4),
              delay=int(spec.get("delay", 2) or 2),
              absorbed=False)
    _detach_for_device(state, item)
    message = tr("空椅面向走廊放着——它先替你安静两回合。")
    return True, message, {"device": "gear_chair"}


_POINT_BEHAVIORS: dict[str, Callable[..., tuple[bool, str, dict]]] = {
    "record_steps": _record_steps,
    "deploy_chair": _deploy_chair,
}

_DIRECTION_BEHAVIORS: dict[str, Callable[..., tuple[bool, str, dict]]] = {
    "roll_bell": _roll_bell,
    "arm_funnel": _arm_funnel_active,
}

_PAIR_BEHAVIORS: dict[str, Callable[..., tuple[bool, str, dict]]] = {
    "sound_curtain": _sound_curtain,
    "sound_pipe": _sound_pipe,
}


def use_self(state: Any, item: Any, active: dict) -> tuple[bool, str, dict]:
    if not _equipped(state, item):
        return False, tr("装备须先上盘。"), {}
    if str(active.get("behavior", "")).startswith("expansion."):
        from .remaining_gear import use
        return use(state, item, active, None)
    handler = _SELF_BEHAVIORS.get(str(active.get("behavior") or ""))
    if handler is None:
        return False, tr("{item}现在没有可以直接做的动作。", item=item.name), {}
    return handler(state, item, dict(active.get("params") or {}))


def use_point(state: Any, item: Any, active: dict,
              point) -> tuple[bool, str, dict]:
    if not _equipped(state, item):
        return False, tr("装备须先上盘。"), {}
    if str(active.get("behavior", "")).startswith("expansion."):
        from .remaining_gear import use
        return use(state, item, active, point)
    handler = _POINT_BEHAVIORS.get(str(active.get("behavior") or ""))
    if handler is None:
        return False, tr("{item}不接受单点。", item=item.name), {}
    return handler(state, item, dict(active.get("params") or {}), point)


def use_pair(state: Any, item: Any, active: dict,
             first, second) -> tuple[bool, str, dict]:
    if not _equipped(state, item):
        return False, tr("装备须先上盘。"), {}
    if str(active.get("behavior", "")).startswith("expansion."):
        from .remaining_gear import use
        return use(state, item, active, (first, second))
    handler = _PAIR_BEHAVIORS.get(str(active.get("behavior") or ""))
    if handler is None:
        return False, tr("{item}不接受成对落点。", item=item.name), {}
    return handler(state, item, dict(active.get("params") or {}), (first, second))


def use_direction(state: Any, item: Any, active: dict,
                  direction) -> tuple[bool, str, dict]:
    if not _equipped(state, item):
        return False, tr("装备须先上盘。"), {}
    if str(active.get("behavior", "")).startswith("expansion."):
        from .remaining_gear import use
        return use(state, item, active, direction)
    handler = _DIRECTION_BEHAVIORS.get(str(active.get("behavior") or ""))
    if handler is None:
        return False, tr("{item}不接受方向。", item=item.name), {}
    return handler(state, item, dict(active.get("params") or {}), direction)


# ---------------------------------------------------------------------------
# 物品交接：装置接管本体，从行囊里摘下（不销毁，roll 结束落回地面）
# ---------------------------------------------------------------------------

def _detach_for_device(state: Any, item: Any) -> None:
    inventory = list(getattr(state, "inventory", ()))
    try:
        index = next(i for i, entry in enumerate(inventory) if entry is item)
    except StopIteration:
        return
    state.board.remove_item(item.instance_id)
    state.equipment.invalidate()
    state.inventory.pop(index)


def _drop_device_item(state: Any, definition_id: str, x: int, y: int) -> None:
    if not definition_id:
        return
    from ..core.entities import WorldItem

    entry = WorldItem(state._make_item(definition_id), int(x), int(y))
    entry.sync_surface(state.cell(int(x), int(y)))
    state.world_items.append(entry)


# ---------------------------------------------------------------------------
# 装置每回合结算（由 core/item_devices.tick 转交）
# ---------------------------------------------------------------------------

GEAR_DEVICE_KINDS = frozenset({"gear_bell", "gear_chair", "gear_pipe",
                               "gear_curtain", "gear_recorder",
                               "gear_light_flash", "gear_light_beam"})


def tick_record(state: Any, record: dict) -> bool | None:
    """返回 True 保留、False 结束、None 表示不是本模块的装置。"""
    kind = str(record.get("kind", ""))
    if kind not in GEAR_DEVICE_KINDS:
        return None
    from . import gear_light

    handled = gear_light.tick_record(state, record)
    if handled is not None:
        return handled
    handler = _TICKS.get(kind)
    if handler is None:
        return False
    return handler(state, record)


def _tick_bell(state: Any, record: dict) -> bool:
    record["turns"] = int(record.get("turns", 0)) - 1
    x, y = int(record.get("x", 0)), int(record.get("y", 0))
    data = record.setdefault("data", {})
    state._sound_pulse(x, y, int(data.get("radius", 6) or 6), by_player=True, category="item",
                       source=tr("沿墙滚动的铃轴"))
    dx, dy = int(data.get("dx", 0) or 0), int(data.get("dy", 0) or 0)
    nx, ny = x + dx, y + dy
    if (int(record.get("turns", 0)) <= 0 or not state.inside_board(nx, ny)
            or state.cell(nx, ny).solid or not _wall_adjacent(state, nx, ny)):
        _drop_device_item(state, str(data.get("definition_id") or ""), x, y)
        state.messages.append(tr("铃轴在墙根停住了，滚不动也响不动。"))
        return False
    record["x"], record["y"] = nx, ny
    return True


def _wall_adjacent(state: Any, x: int, y: int) -> bool:
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if state.inside_board(nx, ny) and state.cell(nx, ny).solid:
            return True
    return False


def _tick_chair(state: Any, record: dict) -> bool:
    data = record.setdefault("data", {})
    x, y = int(record.get("x", 0)), int(record.get("y", 0))
    if not data.get("absorbed"):
        # 没等到声音的椅子会到点被搬走：否则一放下去就永久占着一格。
        record["turns"] = int(record.get("turns", 0)) - 1
        if int(record.get("turns", 0)) <= 0:
            _drop_device_item(state, str(data.get("definition_id") or ""), x, y)
            state.messages.append(tr("空椅一直没等到声音，被人搬回墙角了。"))
            return False
        return True
    if int(state.time) < int(data.get("due", 0) or 0):
        return True
    state._sound_pulse(x, y, int(data.get("strength", 6) or 6), by_player=True,
                       category=str(data.get("category") or "item"),
                       source=str(data.get("source") or tr("最后一排的空椅")))
    state.messages.append(tr("空椅把那一声原样放了出来。"))
    _drop_device_item(state, str(data.get("definition_id") or ""), x, y)
    return False


def _tick_recorder(state: Any, record: dict) -> bool:
    data = record.setdefault("data", {})
    offsets = list(data.get("offsets") or ())
    step = int(data.get("step", 0) or 0)
    if step >= len(offsets):
        _drop_device_item(state, str(data.get("definition_id") or ""),
                          int(record.get("x", 0)), int(record.get("y", 0)))
        state.messages.append(tr("脚步机走完了最后一步，停在原地。"))
        return False
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) < 0:
        _drop_device_item(state, str(data.get("definition_id") or ""),
                          int(record.get("x", 0)), int(record.get("y", 0)))
        state.messages.append(tr("脚步机的发条走完了。"))
        return False
    anchor = (int(record.get("x", 0)), int(record.get("y", 0)))
    ox, oy = int(offsets[step][0]), int(offsets[step][1])
    x, y = anchor[0] + ox, anchor[1] + oy
    data["step"] = step + 1
    if state.inside_board(x, y) and not state.cell(x, y).solid:
        state._sound_pulse(x, y, int(data.get("radius", 3) or 3), by_player=True,
                           category="step", source=tr("脚步机复放的脚步"))
    return True


def _tick_curtain(state: Any, record: dict) -> bool:
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) <= 0:
        data = record.setdefault("data", {})
        _drop_device_item(state, str(data.get("definition_id") or ""),
                          int(record.get("x", 0)), int(record.get("y", 0)))
        state.messages.append(tr("软帘松脱，落了下来。"))
        return False
    return True


def _tick_pipe(state: Any, record: dict) -> bool:
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) <= 0:
        data = record.setdefault("data", {})
        _drop_device_item(state, str(data.get("definition_id") or ""),
                          int(record.get("x", 0)), int(record.get("y", 0)))
        state.messages.append(tr("传声筒的两头松开了。"))
        return False
    return True


_TICKS: dict[str, Callable[[Any, dict], bool]] = {
    "gear_bell": _tick_bell,
    "gear_chair": _tick_chair,
    "gear_recorder": _tick_recorder,
    "gear_curtain": _tick_curtain,
    "gear_pipe": _tick_pipe,
}


# ---------------------------------------------------------------------------
# 每回合清理（由 core/item_devices.tick 调用一次）
# ---------------------------------------------------------------------------

def tick_state(state: Any) -> None:
    """清掉过期的指向前提；离液后让木底鞋重新干燥；烧掉手电这一回合的电。"""
    from . import gear_light

    gear_light.tick_devices(state)
    from .remaining_gear import tick
    tick(state)
    marks = getattr(state, "equipment_marks", None)
    if not isinstance(marks, dict) or not marks:
        return
    now = int(state.time)
    for key in tuple(marks):
        if not key.startswith("gear:"):
            continue
        value = marks.get(key)
        if isinstance(value, dict) and "until" in value and int(value["until"]) < now:
            marks.pop(key, None)
    # 木底鞋：不在液体里就重新干燥（每层首次的额度按层重置）。
    if int(getattr(state.cell(state.player.x, state.player.y), "liquid", 0) or 0) <= 0:
        for key in tuple(marks):
            if not key.startswith("thin_sole:"):
                continue
            value = marks.get(key)
            if isinstance(value, dict) and int(value.get("used", 0) or 0) > 0:
                marks.pop(key, None)


# ---------------------------------------------------------------------------
# 光类装备（批次二）挂到同一张分派表
# ---------------------------------------------------------------------------

from . import gear_light as _gear_light  # noqa: E402  （放在末尾避开环形导入）

_gear_light.register(_SELF_BEHAVIORS, _POINT_BEHAVIORS, _PAIR_BEHAVIORS)
