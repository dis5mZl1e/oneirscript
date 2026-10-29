"""扩展包装备的运行期行为（批次二：光与灯具，2026-10-25）。

十件装备全部落在**既有的光照与视野结算**上，不新写一套照明模型：

* 光在世界里只有两种可结算形态——``cell.light_on / light_radius``（环境灯）与
  ``SightMixin.effective_sight_radius()``（自身携光）。所以「把光引过去」＝
  给那几格记一份**临时照亮**（``extra``），「把光挡住」＝把那几格从你能看见的
  集合里切掉（``blocked``），「照不到背后」＝背向格少一格预算（``rear_penalty``）。
* 方向只有 ``state.facing`` 一个真源。手持的灯（手电／遮片／背心）跟着朝向走；
  台灯（``expansion.light.e01``）用行动转向，方向存在自己的刻痕里；披布
  （``expansion.light.e16``）是**架起来**的，方向记在架起那一刻。
* 敌人「更容易／更不容易看见你」只改 ``can_see`` 里的那一次半径比较
  （``seen_delta``），不去改异象的通用视距——黑布背心不该让敌人看别的东西变近。

本模块不 import ``gear_tools``（避免环形导入），共用的小工具在函数里局部取。
"""

from __future__ import annotations

from typing import Any

from ..i18n import tr
from .expansion_runtime import active_effects, params

# 本批十件的稳定 id。只用于「这次调用要不要继续算」的**廉价预判**：
# 规则判定一律读被动契约与 ``active_use``，这里不是第二份规则表。
LIGHT_GEAR_IDS = frozenset({
    "expansion.light.e01",  # 遮住一半的台灯
    "expansion.light.e02",  # 磨砂护目片
    "expansion.light.e04",  # 漏光的拆信刀
    "expansion.light.e05",  # 窄缝手电
    "expansion.light.e06",  # 搬家的灯罩
    "expansion.light.e07",  # 黑布背心
    "expansion.light.e09",  # 斜口投影筒
    "expansion.light.e11",  # 焦黑遮片
    "expansion.light.e13",  # 遗失的聚光把手
    "expansion.light.e16",  # 摄影师的黑披布
})

HALF_LAMP = "expansion.light.e01"
GLARE_BUFFER = "expansion.light.e02"
STRIKE_KNIFE = "expansion.light.e04"
BEAM_LAMP = "expansion.light.e05"
SHADE_MOVER = "expansion.light.e06"
REAR_VEST = "expansion.light.e07"
PROJECTOR = "expansion.light.e09"
SOOT_SHIELD = "expansion.light.e11"
POLAR_HANDLE = "expansion.light.e13"
PHOTO_CLOTH = "expansion.light.e16"

# 刻痕名（同件装备的不同状态各占一个刻痕，键前缀由 gear_tools 统一拼）。
MARK_LAMP = "lamp"
MARK_BEAM = "beam"
MARK_SHIELD = "shield"
MARK_SCREEN = "screen"
MARK_SHADES = "shades"

# 灯光装置的种类名（每回合由 ``core/item_devices.tick`` 转交本模块）。
DEVICE_FLASH = "gear_light_flash"
DEVICE_BEAM = "gear_light_beam"
LIGHT_DEVICE_KINDS = frozenset({DEVICE_FLASH, DEVICE_BEAM})

_DIRECTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))


# ---------------------------------------------------------------------------
# 小工具：刻痕 / 预判 / 方向
# ---------------------------------------------------------------------------

def _gt():
    """局部取 ``gear_tools``：两边互相调用，模块级 import 会成环。"""
    from . import gear_tools

    return gear_tools


def _mark(state: Any, item: Any, name: str) -> dict:
    return _gt()._mark(state, item, name)


def _set_mark(state: Any, item: Any, name: str, value: dict | None) -> None:
    _gt()._set_mark(state, item, name, value)


def _bump(state: Any) -> None:
    """刻痕变了：让光照叠加表与视野缓存知道要重算。"""
    state._gear_light_rev = int(getattr(state, "_gear_light_rev", 0) or 0) + 1
    cache = getattr(state, "_gear_light_overlay", None)
    if cache is not None:
        try:
            del state._gear_light_overlay
        except AttributeError:
            pass


def _equipped_items(state: Any):
    """已上盘的扩展包装备（行囊里可能有、也可能没有）。"""
    equipped = getattr(state, "equipped", None) or {}
    worn = set(equipped.values()) if hasattr(equipped, "values") else set()
    for item in getattr(state, "inventory", ()):
        if getattr(item, "definition_id", "") not in LIGHT_GEAR_IDS:
            continue
        if getattr(item, "instance_id", "") in worn:
            yield item


def _item_of(state: Any, definition_id: str):
    for item in _equipped_items(state):
        if item.definition_id == definition_id:
            return item
    return None


def light_gear_active(state: Any) -> bool:
    return any(True for _ in _equipped_items(state))


def _facing(state: Any) -> tuple[int, int]:
    facing = getattr(state, "facing", None) or (1, 0)
    try:
        fx, fy = int(facing[0]), int(facing[1])
    except (TypeError, ValueError, IndexError):
        return (1, 0)
    if not (fx or fy):
        return (1, 0)
    return (fx, fy)


def _sector_cells(facing, origin, depth: int, half: int) -> list[tuple[int, int]]:
    """朝向扇区内的格子（``half=0`` 是一条线，``half=2`` 是五格宽的楔形）。"""
    fx, fy = int(facing[0]), int(facing[1])
    ox, oy = int(origin[0]), int(origin[1])
    px, py = -fy, fx
    cells: list[tuple[int, int]] = []
    for step in range(1, max(0, depth) + 1):
        cx, cy = ox + fx * step, oy + fy * step
        for lat in range(-half, half + 1):
            cells.append((cx + px * lat, cy + py * lat))
    return cells


def in_sector(origin, facing, depth: int, half: int, x: int, y: int) -> bool:
    """单格判断：这一格在不在朝向扇区里（``_sector_cells`` 的逐点版本）。"""
    fx, fy = int(facing[0]), int(facing[1])
    dx, dy = int(x) - int(origin[0]), int(y) - int(origin[1])
    forward = dx * fx + dy * fy
    if forward <= 0 or forward > depth:
        return False
    return abs(dx * (-fy) + dy * fx) <= half


def _behind(state: Any, facing, x: int, y: int) -> bool:
    dx, dy = int(x) - int(state.player.x), int(y) - int(state.player.y)
    if not (dx or dy):
        return False
    return dx * facing[0] + dy * facing[1] < 0


# ---------------------------------------------------------------------------
# 光照叠加：一次解析算一张表（逐格热路径只做字典查询）
# ---------------------------------------------------------------------------

def _build_overlay(state: Any) -> dict:
    now = int(getattr(state, "time", 0) or 0)
    facing = _facing(state)
    data: dict[str, Any] = {
        "facing": facing,
        "origin": (int(state.player.x), int(state.player.y)),
        "blocked": set(),
        "extra": set(),
        "front_bonus": 0,
        # 前向锥的「横向坡度」：``None`` = 半平面（照不到背后就够了），
        # 数字 = 只要 ``|横向| ≤ 坡度×纵深`` 才算在束内（手电的窄束）。
        "front_spread": None,
        "omni_bonus": 0,
        "rear_penalty": 0,
    }
    # ---- e01 遮住一半的台灯：正面 +1、背后 −1；方向由行动转向，存刻痕 ----
    lamp = _item_of(state, HALF_LAMP)
    if lamp is not None:
        mark = _mark(state, lamp, MARK_LAMP)
        if mark and (mark.get("dx") or mark.get("dy")):
            data["facing"] = (int(mark.get("dx", 0)), int(mark.get("dy", 1)))
        data["front_bonus"] = max(data["front_bonus"], 1)
        data["rear_penalty"] = max(data["rear_penalty"], 1)
    # ---- e05 窄缝手电：窄束只沿一支细楔照得更远，宽束是整圈 +1 ----
    torch = _item_of(state, BEAM_LAMP)
    if torch is not None:
        mark = _mark(state, torch, MARK_BEAM)
        mode = str(mark.get("mode") or "off")
        if mode == "narrow" and int(mark.get("left", 0) or 0) > 0:
            narrow = passive_value(state, "beam_lamp", "narrow", 0)
            data["front_bonus"] = max(data["front_bonus"], narrow or 2)
            data["front_spread"] = 1.0 / 3.0
        elif mode == "wide" and int(mark.get("left", 0) or 0) > 0:
            data["omni_bonus"] = max(data["omni_bonus"],
                                     passive_value(state, "beam_lamp", "wide", 0) or 1)
    from ..core.expansion_consumables import records as consumable_records, PREFIX
    if any(r['kind'] == PREFIX+'carried_hood' for r in consumable_records(state)):
        data['front_bonus'] = max(data['front_bonus'], data['omni_bonus'])
        data['omni_bonus'] = 0
        data['front_spread'] = min(data['front_spread'] or 1, 1)
    # ---- e07 黑布背心：背面永远少一格，正面照常 ----
    if has_passive(state, "rear_shade"):
        data["rear_penalty"] = max(data["rear_penalty"],
                                   passive_value(state, "rear_shade", "rear_sight", 0) or 1)
    # ---- e11 焦黑遮片：举着时正面窄扇区（一条线）不再是你的视野 ----
    shield = _item_of(state, SOOT_SHIELD)
    if shield is not None and _mark(state, shield, MARK_SHIELD):
        depth = passive_value(state, "soot_shield", "depth", 0) or 3
        for cell in _sector_cells(facing, (state.player.x, state.player.y), depth, 0):
            if state.inside_board(*cell):
                data["blocked"].add(cell)
    # ---- e16 摄影师的黑披布：架起来那个方向的宽扇区被遮住 ----
    cloth = _item_of(state, PHOTO_CLOTH)
    if cloth is not None:
        mark = _mark(state, cloth, MARK_SCREEN)
        if mark and int(mark.get("until", 0) or 0) >= now:
            depth = int(mark.get("depth", 4) or 4)
            half = int(mark.get("half", 2) or 2)
            for cell in _sector_cells((int(mark.get("dx", 1)), int(mark.get("dy", 0))),
                                      (state.player.x, state.player.y), depth, half):
                if state.inside_board(*cell):
                    data["blocked"].add(cell)
    # ---- e04 短闪 / e09 投影筒：临时被照亮的格（装置记录到期即消失）----
    for record in _devices(state, DEVICE_FLASH):
        data["extra"].update(_cells_of(record))
    for record in _devices(state, DEVICE_BEAM):
        data["extra"].update(_cells_of(record))
    return data


def _cells_of(record: dict) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for point in (record.get("data") or {}).get("cells", ()):
        if len(point) == 2:
            cells.add((int(point[0]), int(point[1])))
    return cells


def _devices(state: Any, kind: str) -> list[dict]:
    from ..core.item_devices import devices

    return [record for record in devices(state)
            if str(record.get("kind", "")) == kind]


def _equipped_signature(state: Any) -> tuple[str, ...]:
    """联想盘上的实例 id 表：上盘／下盘必须算进叠加表的键。

    只按时间/坐标做键会漏掉「同一回合内把灯装上去」——``visible_cells`` 与
    ``live_sight`` 都会继续读到上盘前那张空表（缓存为 ``None``）。
    """
    equipped = getattr(state, "equipped", None) or {}
    try:
        return tuple(sorted(str(value) for value in equipped.values()))
    except AttributeError:
        return ()


def overlay(state: Any) -> dict | None:
    """本回合的光照叠加表；没有任何光类装备时返回 ``None``（热路径直接跳过）。

    键里放 ``(时间, 玩家坐标, 朝向, 刻痕版本, 上盘表)``：转灯、架披布、切手电
    推进版本号，上盘／下盘改上盘表，因此同一回合内的任何改向与换装都不会读到
    过期表。命中缓存的分支只做一次元组比较——逐格热路径（``visible_cells``）
    每帧要问上百次，行囊扫描不能跟着每格跑一遍。
    """
    key = (int(getattr(state, "time", 0) or 0), state.player.x, state.player.y,
           _facing(state), int(getattr(state, "_gear_light_rev", 0) or 0),
           _equipped_signature(state))
    cached = getattr(state, "_gear_light_overlay", None)
    if cached is not None and cached[0] == key:
        return cached[1]
    if not light_gear_active(state):
        state._gear_light_overlay = (key, None)
        return None
    built = _build_overlay(state)
    state._gear_light_overlay = (key, built)
    return built


def cell_shift(state: Any, x: int, y: int) -> int | None:
    """这一格对玩家视野的加减：``None`` = 被遮住，``-1/0/+1`` = 预算修正。"""
    table = overlay(state)
    if table is None:
        return 0
    return shift_of(table, x, y)


def shift_of(table: dict, x: int, y: int) -> int | None:
    if (x, y) in table["blocked"]:
        return None
    dx = int(x) - int(table["origin"][0])
    dy = int(y) - int(table["origin"][1])
    if not (dx or dy):
        return 0
    facing = table["facing"]
    forward = dx * facing[0] + dy * facing[1]
    if table["front_bonus"] and forward > 0:
        spread = table.get("front_spread")
        lateral = abs(dx * (-facing[1]) + dy * facing[0])
        if spread is None or lateral <= spread * forward:
            return table["front_bonus"]
    if table["rear_penalty"] and forward < 0:
        return -table["rear_penalty"]
    return table["omni_bonus"]


def extra_cells(state: Any) -> set[tuple[int, int]]:
    table = overlay(state)
    return set(table["extra"]) if table else set()


def extra_span(state: Any, x: int, y: int, radius: int) -> int:
    """这一格被「引过去／闪出来的光」照亮时，需要补多少预算（否则 0）。

    ``visible_cells`` 与 ``live_sight`` 共用这一处口径：光能把你「看得见多远」
    往前推，但走的仍是同一条带预算、会被墙截断的射线——所以它只是补预算，
    不是「无视线跳格」。
    """
    table = overlay(state)
    if table is None or (x, y) not in table["extra"]:
        return 0
    span = max(abs(int(x) - table["origin"][0]), abs(int(y) - table["origin"][1])) - int(radius) + 1
    return max(1, span)


# ---------------------------------------------------------------------------
# 被动契约的读取端（由 core/vision/sight.py 与 core/vision/cache.py 调用）
# ---------------------------------------------------------------------------

def has_passive(state: Any, effect: str) -> bool:
    """本模块的被动一律先判「有没有」再读参数。

    ``gear_tools.passive_value`` 在**没有**对应能力时会返回默认值，直接把默认值
    当收益读会把规则白送给所有没带这件装备的人（批次一踩过）。
    """
    return bool(active_effects(state, effect))


def passive_value(state: Any, effect: str, key: str, default: int = 0) -> int:
    for ability in active_effects(state, effect):
        value = int(params(ability).get(key, default) or 0)
        if value:
            return value
    return default


def vision_flat(state: Any) -> int:
    """磨砂护目片：戴上就少一格（暗处辨认距离缩短），没戴 0。"""
    if not light_gear_active(state):
        return 0
    if not has_passive(state, "glare_buffer"):
        return 0
    return passive_value(state, "glare_buffer", "vision", 0)


def blind_radius(state: Any, radius: int) -> int:
    """致盲覆盖：没戴护目片时归零；戴上则「缓冲」成一半，且至少留 1 格。

    这是本作里唯一真实存在的「强光负面」（闪光／强光致盲），所以「强光缓冲」
    在这里落成「blinds 不再把普通视觉清零」。``radius`` 已为 0 时不复活。
    """
    if radius <= 0:
        return 0
    if not light_gear_active(state):
        return 0
    if not has_passive(state, "glare_buffer"):
        return 0
    return max(1, int(radius * 0.5))


def seen_delta(state: Any, observer: Any) -> int:
    """异象看向**玩家**时的视距加减（正 = 你更显眼）。"""
    if not light_gear_active(state):
        return 0
    delta = 0
    # e04 漏光的拆信刀：短闪这一回合连出手方向都亮着，你也更好认。
    if has_passive(state, "strike_flash"):
        for record in _devices(state, DEVICE_FLASH):
            if _cells_of(record) and int(record.get("turns", 0) or 0) > 0:
                delta += passive_value(state, "strike_flash", "seen_bonus", 0) or 1
                break
    # e07 黑布背心：你背后的漏光被压掉了，站在背后的异象看你也少一格。
    if has_passive(state, "rear_shade"):
        facing = _facing(state)
        if _behind(state, facing, getattr(observer, "x", 0), getattr(observer, "y", 0)):
            delta -= passive_value(state, "rear_shade", "seen", 0) or 1
    # e11 焦黑遮片：正面的光被挡住，那条线上的异象也看不清你。
    shield = _item_of(state, SOOT_SHIELD)
    if shield is not None and _mark(state, shield, MARK_SHIELD):
        depth = passive_value(state, "soot_shield", "depth", 0) or 3
        if in_sector((state.player.x, state.player.y), _facing(state), depth, 0,
                     getattr(observer, "x", -99), getattr(observer, "y", -99)):
            delta -= 1
    return delta


def tool_busy(state: Any) -> str:
    """本句的「工具行为」被谁占着（焦黑遮片举着时它占着）。返回物品名或空串。"""
    shield = _item_of(state, SOOT_SHIELD)
    if shield is not None and _mark(state, shield, MARK_SHIELD):
        return str(getattr(shield, "name", "") or "")
    return ""


# ---------------------------------------------------------------------------
# 回调：命中短闪（e04）与移动收起（e16）
# ---------------------------------------------------------------------------

def note_strike_flash(state: Any, target: Any) -> None:
    """真实命中后，沿出手方向短闪一段：那几格这一回合被照亮。"""
    if not has_passive(state, "strike_flash"):
        return
    if target is None:
        return
    depth = passive_value(state, "strike_flash", "depth", 0) or 4
    turns = passive_value(state, "strike_flash", "turns", 0) or 1
    px, py = state.player.x, state.player.y
    tx = int(getattr(target, "x", px))
    ty = int(getattr(target, "y", py))
    step = (0 if tx == px else (1 if tx > px else -1),
            0 if ty == py else (1 if ty > py else -1))
    if not (step[0] or step[1]):
        step = _facing(state)
    cells: list[list[int]] = []
    for index in range(1, depth + 1):
        x, y = px + step[0] * index, py + step[1] * index
        if not state.inside_board(x, y):
            break
        if (x, y) != (tx, ty) and not state._has_line_of_sight(px, py, x, y):
            break
        cells.append([x, y])
        if (x, y) == (tx, ty):
            break
    if not cells:
        return
    _gt()._register(state, DEVICE_FLASH, px, py, turns, cells=cells)
    _bump(state)


def cancel_on_move(state: Any) -> None:
    """摄影师的黑披布：人一动，遮光面就倒了。"""
    cloth = _item_of(state, PHOTO_CLOTH)
    if cloth is None:
        return
    if _mark(state, cloth, MARK_SCREEN):
        _set_mark(state, cloth, MARK_SCREEN, None)
        _bump(state)
        state.messages.append(tr("你一动，黑披布就滑下来了一角——那面遮光面倒了。"))


# ---------------------------------------------------------------------------
# 主动行为（self）
# ---------------------------------------------------------------------------

def _turn_lamp(state: Any, item: Any, spec: dict) -> tuple[bool, str, dict]:
    mark = _mark(state, item, MARK_LAMP)
    current = (int(mark.get("dx", 0)), int(mark.get("dy", 0))) if mark else _facing(state)
    index = _DIRECTIONS.index(current) if current in _DIRECTIONS else 0
    nxt = _DIRECTIONS[(index + 1) % len(_DIRECTIONS)]
    _set_mark(state, item, MARK_LAMP, {"dx": nxt[0], "dy": nxt[1]})
    _bump(state)
    return True, tr("你把台灯转了个方向——正面亮了一格，背后仍旧照不到。"), {
        "lamp_direction": [nxt[0], nxt[1]]}


def _switch_beam(state: Any, item: Any, spec: dict) -> tuple[bool, str, dict]:
    battery = int(spec.get("battery", 8) or 8)
    mark = _mark(state, item, MARK_BEAM) or {"mode": "off", "left": battery}
    left = int(mark.get("left", battery) or 0)
    if left <= 0:
        _set_mark(state, item, MARK_BEAM, {"mode": "off", "left": 0})
        _bump(state)
        return False, tr("手电的电量已经见底了——切哪一档都不亮。"), {}
    mode = str(mark.get("mode") or "off")
    nxt = {"off": "narrow", "narrow": "wide", "wide": "off"}.get(mode, "narrow")
    _set_mark(state, item, MARK_BEAM, {"mode": nxt, "left": left})
    _bump(state)
    words = {"narrow": tr("长窄束：前面看得更远，两侧照旧。"),
             "wide": tr("短宽束：四周各多一格，但前面不再多照。"),
             "off": tr("你把手电关上了。")}
    return True, words[nxt], {"beam_mode": nxt, "battery_left": left}


def _raise_shield(state: Any, item: Any, spec: dict) -> tuple[bool, str, dict]:
    mark = _mark(state, item, MARK_SHIELD)
    if mark:
        _set_mark(state, item, MARK_SHIELD, None)
        _bump(state)
        return True, tr("你放下遮片——正面的视线回来了。"), {"shield": False}
    _set_mark(state, item, MARK_SHIELD, {"raised": True})
    _bump(state)
    return True, tr("你举起焦黑的遮片挡住正面的光：那边你看不见，那边也看不清你。"
                    "它不会自己放下，也不腾手做别的工具动作。"), {"shield": True}


def _raise_screen(state: Any, item: Any, spec: dict) -> tuple[bool, str, dict]:
    turns = int(spec.get("turns", 3) or 3)
    depth = int(spec.get("depth", 4) or 4)
    half = int(spec.get("half", 2) or 2)
    dx, dy = _facing(state)
    _set_mark(state, item, MARK_SCREEN, {
        "dx": dx, "dy": dy, "depth": depth, "half": half,
        "until": int(state.time) + turns})
    _bump(state)
    return True, tr("你把黑披布架了起来——那一侧的视线也被它一起挡住了。"), {
        "screen_turns": turns}


# ---------------------------------------------------------------------------
# 主动行为（point / pair）
# ---------------------------------------------------------------------------

def _known(state: Any, x: int, y: int) -> bool:
    """这一格是否「已确认」：当前看得见，或地图记忆里有它。"""
    if state.is_visible(x, y):
        return True
    memory = state.terrain_memory.get(state.layer_key()) or {}
    return (int(x), int(y)) in memory


def _is_lamp(cell: Any) -> bool:
    return int(getattr(cell, "light_radius", 0) or 0) > 0


def _move_shade(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    x, y = int(point[0]), int(point[1])
    if max(abs(x - state.player.x), abs(y - state.player.y)) > 1:
        return False, tr("灯罩没法隔空够到——先站到那盏灯的旁边。"), {}
    cell = state.cell(x, y)
    if not _is_lamp(cell) or not cell.light_on:
        return False, tr("那格没有亮着的灯可以拆罩子。"), {}
    mark = _mark(state, item, MARK_SHADES) or {"cells": {}}
    cells = dict(mark.get("cells") or {})
    key = f"{x},{y}"
    if key in cells:
        cell.light_radius = int(cells.pop(key))
        _set_mark(state, item, MARK_SHADES, {"cells": cells})
        message = tr("你把灯罩装了回去——光又收拢成一圈。")
        action = "refit"
    else:
        cells[key] = int(cell.light_radius)
        cell.light_radius = min(int(cell.light_radius) + 1, 4)
        _set_mark(state, item, MARK_SHADES, {"cells": cells})
        message = tr("你把灯罩卸了下来——那盏灯散得更开，也多照出一圈。")
        action = "remove"
    _bump(state)
    return True, message, {"shade": action, "light_radius": int(cell.light_radius)}


def _project_light(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    first, second = tuple(point[0]), tuple(point[1])
    source = state.cell(int(first[0]), int(first[1]))
    if not _is_lamp(source) or not source.light_on:
        return False, tr("被引光的那格得是一盏亮着的灯。"), {}
    for record in _devices(state, DEVICE_BEAM):
        if (int(record.get("x", 0)), int(record.get("y", 0))) == (int(first[0]), int(first[1])):
            # 同一盏灯只引一条光：两条各记一次原半径，到期会把灯越还原越小。
            return False, tr("那盏灯已经引着一条光了——等它回满再引。"), {}
    length = int(spec.get("length", 3) or 3)
    turns = int(spec.get("turns", 4) or 4)
    dx = 0 if second[0] == first[0] else (1 if second[0] > first[0] else -1)
    dy = 0 if second[1] == first[1] else (1 if second[1] > first[1] else -1)
    if not (dx or dy):
        return False, tr("朝着灯自己是引不出方向来的——在另一头点一下。"), {}
    cells: list[list[int]] = []
    for index in range(1, length + 1):
        x, y = int(first[0]) + dx * index, int(first[1]) + dy * index
        if not state.inside_board(x, y):
            break
        if not state._has_line_of_sight(int(first[0]), int(first[1]), x, y):
            break
        cells.append([x, y])
    if not cells:
        return False, tr("灯前头没有可以引过去的直线。"), {}
    prev_radius = int(source.light_radius)
    source.light_radius = max(0, prev_radius - 1)
    _gt()._register(state, DEVICE_BEAM, int(first[0]), int(first[1]), turns,
                    cells=cells, prev_light_radius=prev_radius,
                    prev_light_on=bool(source.light_on))
    _bump(state)
    return True, tr("斜口把一部分光引成了一条短线——原来那一圈随之小了一圈。"), {
        "beam_cells": len(cells), "light_radius": int(source.light_radius)}


def _turn_lamp_remote(state: Any, item: Any, spec: dict, point) -> tuple[bool, str, dict]:
    from ..materials import FLAME_FIXTURE_KINDS, POWERED_FIXTURE_KINDS

    x, y = int(point[0]), int(point[1])
    cell = state.cell(x, y)
    if not _is_lamp(cell):
        return False, tr("那格没有可以转的固定灯。"), {}
    if not _known(state, x, y):
        return False, tr("你还没确认过那盏灯——把手先转不动它。"), {}
    if not state._has_line_of_sight(state.player.x, state.player.y, x, y):
        return False, tr("光被墙截住了——隔墙转不动灯。"), {}
    if cell.wall_kind in FLAME_FIXTURE_KINDS:
        return False, tr("这盏灯靠燃烧发光——点火或灭火，而不是拨开关。"), {}
    if cell.wall_kind in POWERED_FIXTURE_KINDS:
        return False, tr("灯架的电源接在电路上，把手转不动它。"), {}
    enabled = not cell.light_on
    state.set_light_enabled(x, y, enabled)
    _bump(state)
    message = (tr("把手一转，远处那盏灯亮了。") if enabled
               else tr("把手一转，远处那盏灯灭了。"))
    return True, message, {"light_on": bool(enabled)}


SELF_BEHAVIORS = {
    "turn_lamp": _turn_lamp,
    "switch_beam": _switch_beam,
    "raise_shield": _raise_shield,
    "raise_screen": _raise_screen,
}

POINT_BEHAVIORS = {
    "move_shade": _move_shade,
    "turn_lamp_remote": _turn_lamp_remote,
}

PAIR_BEHAVIORS = {
    "project_light": _project_light,
}


def register(self_table: dict, point_table: dict, pair_table: dict) -> None:
    """把本模块的处理器挂进 ``gear_tools`` 的分派表（由 gear_tools 末尾调用）。"""
    self_table.update(SELF_BEHAVIORS)
    point_table.update(POINT_BEHAVIORS)
    pair_table.update(PAIR_BEHAVIORS)


# ---------------------------------------------------------------------------
# 每回合结算（由 core/item_devices.tick → gear_tools.tick_state 转交）
# ---------------------------------------------------------------------------

def tick_devices(state: Any) -> None:
    """手电电量：亮着就烧一点，烧完自动关。"""
    torch = _item_of(state, BEAM_LAMP)
    if torch is None:
        return
    mark = _mark(state, torch, MARK_BEAM)
    if not mark or str(mark.get("mode") or "off") == "off":
        return
    left = int(mark.get("left", 0) or 0) - 1
    if left <= 0:
        _set_mark(state, torch, MARK_BEAM, {"mode": "off", "left": 0})
        _bump(state)
        state.messages.append(tr("手电闪了两下就灭了——电量用完了。"))
        return
    mark["left"] = left
    _set_mark(state, torch, MARK_BEAM, mark)


def tick_record(state: Any, record: dict) -> bool | None:
    """返回 True 保留、False 结束、None 表示不是本模块的装置。"""
    kind = str(record.get("kind", ""))
    if kind not in LIGHT_DEVICE_KINDS:
        return None
    record["turns"] = int(record.get("turns", 0) or 0) - 1
    if int(record.get("turns", 0) or 0) > 0:
        return True
    if kind == DEVICE_BEAM:
        data = record.get("data") or {}
        x, y = int(record.get("x", 0)), int(record.get("y", 0))
        if state.inside_board(x, y):
            cell = state.cell(x, y)
            cell.light_radius = int(data.get("prev_light_radius", cell.light_radius) or 0)
            cell.light_on = bool(data.get("prev_light_on", True))
    _bump(state)
    return False
