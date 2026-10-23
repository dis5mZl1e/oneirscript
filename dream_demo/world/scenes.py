"""环境条件场景的运行时（重构方案 §10）。

边界写在 docstring 里也写在代码里：本模块只做**条件判断、状态转移与有限效果命令**，
不计算任何材料伤害——点火走 ``_ignite_cell``，倒水走 ``_add_liquid``，灭火走
``_set_flame``，代价走 ``_check_npc_cost`` / ``_charge_npc_cost``，时间走唯一入口
``_action_time``。场景模块里没有第二条伤害公式，面板说明与结算读的也是同一份
条件结构（§10.1「禁止另写一套会与实际逻辑不一致的文案」）。

设施生命周期（§10.2）：

    休眠 ──看见锚点──▶ 可激活 ──命令──▶ 预告 ──一个实际行动后──▶ 生效
                                                              │
                       可激活／耗尽 ◀──冷却期满、火已熄────────┘

「预告」存在 ``FacilityRecord.pending`` 里，由 :func:`resolve_pending` 在玩家**下一次
实际**行动结算完之后落地，所以新建立的伤害场不会在同一提交里「显示预告→扣伤→消失」。
换层时当地设施暂停模拟：记录按 ``layer_key`` 归属，回到该层时由 :func:`refresh`
按世界时刻重算显示态，不补算离线期间的火场与水量（§10.2）。
"""

from __future__ import annotations

import random
from typing import Any

from ..core.constants import ActionKind
from ..core.entities import ActionResult
from ..data.ids import stable_seed
from ..data.scenes import (
    CONDITION_TYPES,
    EFFECT_TYPES,
    MAX_COMMANDS_PER_SETTLEMENT,
    SCENE_DEFINITIONS,
)
from ..i18n import tr
from . import facts
from .relations import player_uid

#: 锚点键的显示名：条件说明与拒绝原因都从这里取名，不各自硬写。
_ANCHOR_LABELS = {
    "hearth": "火盆", "fuel_slots": "边槽", "ward": "术阵", "bypass": "旁路",
    "basin": "蓄水盆", "valve": "上游阀", "channels": "低槽", "discharge": "排放区",
    "console": "控制台", "mic_yard": "内院喇叭", "mic_gate": "门口喇叭",
    "page_a": "内侧折页", "page_b": "外侧折页", "ends": "两张折页",
    "ring_a": "内侧折页四周", "ring_b": "外侧折页四周",
    "yard": "保护区", "side_door": "侧门", "winch": "门柱手柄", "pump": "泵机",
    "board": "路线牌", "hall": "候车厅", "window": "窗边窄路",
    "desk": "编目台", "stacks": "档案架", "index": "编目索引", "route": "安全路线",
    "lamp": "青灯",
    # R03 留灯的避难圈：环线（作用区）、两侧出口与灯台手柄。
    "ring": "灯圈", "door_a": "西侧门", "door_b": "东侧门",
}
#: 库存键的显示名（§10.1「某材料储量达到阈值」）。
_STOCK_LABELS = {"ward": "术阵燃料", "reserve": "备用干纸", "pipe": "管道余量",
                 "charge": "余电", "crossings": "对折次数", "tickets": "候车票"}
#: 回复类效果的属性显示名（R03 休息）：面板与消息里都用同一份名字。
_STAT_LABELS = {"mind": "心智", "lucidity": "清醒度", "imagination": "想象力"}
#: 具名开关的显示名（§9 S01／S09／S23）：条件说明与拒绝原因都从这里取名。
#: ⚠️ 全局表，同义开关要按族另起名字（S23 用 ``offered``／``paid``／``entered``）。
_FLAG_LABELS = {"marked": "标出的旁路", "relay": "中继权限", "kept": "旅人服务",
                "identified": "认出的记录", "extracted": "拆下的记录",
                "filed": "留档的记录", "routed": "标出的安全路线",
                "offered": "嵌进灯座的透镜", "paid": "付清的祭品", "entered": "已进入的门",
                # R03 留灯的避难圈：灯亮＝保持计数前置；歇过的一次性闩；门轴修过的痕。
                "lit": "点亮留灯", "rested": "歇过的那一次", "repaired": "修好的侧门"}

#: §8 S23 青灯入口：能当祭品喂给门的两类物件——「会消散的东西」。
#: 携带意象／惯用物不算（它们是常驻件），所以灯塔透镜本身不会把自己喂掉。
GATE_GIFT_CATEGORIES = ("易逝物", "摄入物")

#: 对外公开的布局键显示名：任务面板与场景面板因此叫得出同一名字。
ANCHOR_LABELS = _ANCHOR_LABELS


# --------------------------------------------------------------- 身份与安装

def absolute_layout(definition: dict[str, Any], origin: tuple[int, int],
                    other: "tuple[int, int] | None" = None) -> dict[str, Any]:
    """定义里的相对锚点 → 绝对格子。布局键名与定义保持一致。

    配对场景（定义里有 ``pair``）多传一个原点：键名后缀 ``_a``／``_b`` 决定落在
    哪一端，并额外补一个 ``ends`` 布局键装着两张折页——「站在任一端」因此仍是
    同一个 ``player_near`` 原语，而不是解释器里的特判。
    """
    ends = (definition.get("pair") or {}).get("ends")
    if ends:
        if other is None:
            raise ValueError(f"配对场景 {definition['definition_id']} 需要两个原点")
        layout: dict[str, Any] = {}
        for index, suffix in ((0, "_a"), (1, "_b")):
            group = {name: spec for name, spec in (definition.get("keys") or {}).items()
                     if name.endswith(suffix)}
            layout.update(_relative_layout(definition, group, (origin, other)[index]))
        missing = [key for key in ends if key not in layout]
        if missing:
            raise ValueError(f"配对场景缺端点键：{missing}")
        layout["origin"] = origin
        layout["ends"] = tuple(layout[key] for key in ends)
        return layout
    layout = _relative_layout(definition, definition.get("keys") or {}, origin)
    layout["origin"] = (origin[0], origin[1])
    return layout


def _relative_layout(definition: dict[str, Any], specs: dict[str, Any],
                     origin: tuple[int, int]) -> dict[str, Any]:
    ox, oy = origin
    width, height = definition["footprint"]
    layout: dict[str, Any] = {}
    for name, spec in specs.items():
        if isinstance(spec, dict):
            if "center" in spec:
                cx, cy = ox + spec["center"][0], oy + spec["center"][1]
                if "radius" in spec:
                    radius = int(spec["radius"])
                    layout[name] = tuple(
                        (cx + dx, cy + dy)
                        for dy in range(-radius, radius + 1)
                        for dx in range(-radius, radius + 1))
                else:
                    area_w, area_h = spec.get("size", (1, 1))
                    x0, y0 = cx - area_w // 2, cy - area_h // 2
                    layout[name] = tuple(
                        (x, y) for y in range(y0, y0 + int(area_h))
                        for x in range(x0, x0 + int(area_w)))
            elif "row" in spec:
                y = oy + int(spec["row"])
                layout[name] = tuple((ox + x, y) for x in range(width))
            continue
        if isinstance(spec, tuple) and len(spec) == 2 and isinstance(spec[0], int):
            layout[name] = (ox + spec[0], oy + spec[1])
        else:
            layout[name] = tuple((ox + x, oy + y) for x, y in spec)
    return layout


def relative_cells(definition: dict[str, Any], origin: tuple[int, int]) -> dict[str, Any]:
    """按**单个**原点算出的相对布局，供落位检查逐端验证。

    配对场景只看 ``_a`` 那一组键：另一端此刻还没定下来，但每一端的形状是一样的。
    """
    specs = definition.get("keys") or {}
    if (definition.get("pair") or {}).get("ends"):
        specs = {name: spec for name, spec in specs.items() if name.endswith("_a")}
    return _relative_layout(definition, specs, origin)


def uid_for(state: Any, definition_id: str, anchor_uid: str) -> str:
    """场景实例 ID（§13.2）：本局 + 本层 + 定义 + 锚点，不用坐标当身份。"""
    return f"{state.run_uid}|{state.layer_key()}|{definition_id}|{anchor_uid}"


def install(state: Any, definition: dict[str, Any], anchor_uid: str) -> Any:
    """建好一处的持久记录。布局由 core/scenes.py 在生成期算好后写入。"""
    record = state.world_ledger.facility(
        uid_for(state, definition["definition_id"], anchor_uid),
        layer_key=state.layer_key(), anchor_uid=anchor_uid,
        definition_id=definition["definition_id"], state="休眠",
        stock=tuple((definition["facility"].get("stock") or {}).items()))
    return record


def definition_of(record: Any) -> dict[str, Any] | None:
    return SCENE_DEFINITIONS.get(record.definition_id)


def local(state: Any, record: Any) -> bool:
    return record.layer_key == state.layer_key()


def records(state: Any) -> list[Any]:
    return [entry for entry in state.world_ledger.facilities.values() if local(state, entry)]


# --------------------------------------------------------------- 条件判断

def evaluate(state: Any, record: Any,
             conditions: tuple[dict[str, Any], ...]) -> tuple[list[str], str]:
    """返回（已满足项说明，第一条未满足原因）。未满足时调用方不得扣任何东西。"""
    met: list[str] = []
    failure = ""
    for condition in conditions:
        ok, text = _check_one(state, record, condition)
        if ok:
            met.append(text)
        elif not failure:
            failure = text
    return met, failure


def _check_one(state: Any, record: Any, condition: dict[str, Any]) -> tuple[bool, str]:
    kind = condition.get("type", "")
    if kind not in CONDITION_TYPES:
        return False, tr("这条条件暂时无法确认（类型 {kind} 未知）。", kind=kind)
    key = condition.get("key", "")
    label = tr(_ANCHOR_LABELS.get(key, key or "这里"))
    if kind == "player_near":
        cells = record.area(key)
        radius = int(condition.get("radius", 1))
        if not cells:
            return False, tr("{name}不在这里。", name=label)
        near = min(max(abs(state.player.x - x), abs(state.player.y - y)) for x, y in cells)
        if near <= radius:
            return True, tr("你在{name}旁边。", name=label)
        return False, tr("离{name}太远（要 {radius} 格以内，现在 {near} 格）。",
                         name=label, radius=radius, near=near)
    if kind == "anchor_flame":
        position = record.cell(key)
        flame = state.cell(*position).flame if position else 0
        if "min" in condition and flame < int(condition["min"]):
            return False, tr("{name}还没有火。", name=label)
        if "max" in condition and flame > int(condition["max"]):
            return False, tr("{name}已经烧着了。", name=label)
        return True, tr("{name}的火势 {flame}。", name=label, flame=flame)
    if kind == "anchor_flammable":
        position = record.cell(key)
        if position is None:
            return False, tr("{name}不在这里。", name=label)
        if state._cell_is_flammable(state.cell(*position)):
            return True, tr("{name}还接得住火。", name=label)
        return False, tr("{name}已经烧穿，点不着了。", name=label)
    if kind == "slot_fuel":
        need = int(condition.get("min", 1))
        have = sum(1 for x, y in record.area(key) if state.cell(x, y).floor_fuel > 0)
        if have >= need:
            return True, tr("边槽还有 {have} 处燃料。", have=have)
        return False, tr("边槽里的燃料不够（要 {need} 处，只剩 {have} 处）。", need=need, have=have)
    if kind == "zone_flammable":
        from ..materials.floors import floor_effect_for

        have = sum(1 for x, y in record.area(key)
                   if floor_effect_for(state.cell(x, y)).burns_to)
        # 只写 max 的条件是「还剩多少可燃地面就不能再装料」，下界应当是 0；
        # 只有没给 max 时才用默认下界 1（「至少还得有一格能烧」）。
        need = int(condition.get("min", 0 if "max" in condition else 1))
        if "max" in condition and have > int(condition["max"]):
            return False, tr("术阵地面还接得住火（{have} 格），不用重新装料。", have=have)
        if have < need:
            return False, tr("术阵地面已经烧成灰——先装料。")
        return True, tr("术阵地面可接火 {have} 格。", have=have)
    if kind == "zone_flame":
        have = sum(1 for x, y in record.area(key) if state.cell(x, y).flame > 0)
        if have <= int(condition.get("max", 0)):
            return True, tr("作用区里没有火。")
        return False, tr("作用区里还有 {have} 格在烧。", have=have)
    if kind == "stock":
        name = condition["name"]
        stock_label = tr(_STOCK_LABELS.get(name, name))
        have = int(record.stock.get(name, 0))
        if "min" in condition and have < int(condition["min"]):
            return False, tr("{name}不够（要 {need}，只有 {have}）。",
                             name=stock_label, need=condition["min"], have=have)
        if "max" in condition and have > int(condition["max"]):
            return False, tr("{name}已经满了。", name=stock_label)
        return True, tr("{name}：{have}。", name=stock_label, have=have)
    if kind == "facility_ready":
        if record.ready(int(state.time)):
            return True, tr("不在冷却里。")
        return False, tr("还在冷却——要等到第 {until} 世界回合（现在 {now}）。",
                         until=record.cooldown_until, now=int(state.time))
    if kind == "facility_state_in":
        wanted = tuple(condition["states"])
        if record.state in wanted:
            return True, tr("设施：{state}。", state=tr(record.state))
        return False, tr("设施现在是「{state}」，这一步要等它回到：{want}。",
                         state=tr(record.state),
                         want=tr("／").join(tr(entry) for entry in wanted))
    if kind == "anchor_liquid":
        position = record.cell(key)
        if position is None:
            return False, tr("{name}不在这里。", name=label)
        cell = state.cell(*position)
        allowed = condition.get("kinds") or _allowed_liquids(record)
        need = int(condition.get("min", 1))
        if allowed and cell.liquid_kind not in allowed:
            return False, tr("{name}里不是允许的液体（现在是{found}）。", name=label,
                             found=tr(cell.liquid_kind or "空的"))
        if int(cell.liquid) < need:
            return False, tr("{name}只有 {amount} 单位，要到 {need}。",
                             name=label, amount=int(cell.liquid), need=need)
        return True, tr("{name}有 {kind} {amount} 单位。", name=label,
                        kind=tr(cell.liquid_kind), amount=int(cell.liquid))
    if kind == "outlet_open":
        blocked = [cell for cell in record.area(key) if state.cell(*cell).solid]
        if blocked:
            return False, tr("排放区有 {n} 格堵着。", n=len(blocked))
        return True, tr("排放区通着。")
    if kind == "blockage_present":
        entry = _blockage(state, record, key)
        have = 1 if entry is not None else 0
        # 与 zone_flammable 同一约定：只写 max 的条件是「这里已经通了」，下界取 0。
        need = int(condition.get("min", 0 if "max" in condition else 1))
        if "max" in condition and have > int(condition["max"]):
            return False, tr("{name}上还挡着 {item}。", name=label,
                             item=tr(entry.item.name))
        if have < need:
            return False, tr("{name}上没有能搬动的东西。", name=label)
        if entry is not None:
            return True, tr("{name}上挡着 {item}。", name=label, item=tr(entry.item.name))
        return True, tr("{name}上通着。", name=label)
    if kind == "no_zone_hazard":
        hazard = sum(1 for x, y in record.area(key)
                     if state.cell(x, y).flame > 0 or state.cell(x, y).gas > 0)
        if hazard:
            return False, tr("作用区里还有 {n} 格危险。", n=hazard)
        return True, tr("作用区是安全的。")
    if kind == "carries_item":
        item_id = condition["item"]
        need = int(condition.get("min", 1))
        have = sum(entry.quantity for entry in state.inventory
                   if entry.definition_id == item_id)
        name = tr(_item_name(item_id))
        if have >= need:
            return True, tr("带着 {name} ×{have}。", name=name, have=have)
        return False, tr("{name}不足（要 {need}，只有 {have}）。", name=name, need=need, have=have)
    if kind == "listener_audible":
        position = record.cell(key)
        if position is None:
            return False, tr("{name}不在这里。", name=label)
        radius = int(condition.get("radius", 5))
        have = _audible_listeners(state, position, radius)
        need = int(condition.get("min", 1))
        if have >= need:
            return True, tr("{name}方向有 {have} 个听得见的失控意识。", name=label, have=have)
        return False, tr("{name}方向没有听得见的失控意识（要 {need} 个，现在 {have} 个）。",
                         name=label, need=need, have=have)
    if kind == "end_primed":
        have = 1 if record.flags.get(key) else 0
        # 与 zone_flammable 同一约定：只写 max 的条件是「还没做过」，下界取 0。
        need = int(condition.get("min", 0 if "max" in condition else 1))
        if "max" in condition and have > int(condition["max"]):
            return False, tr("{name}已经折稳了，不用再折。", name=label)
        if have < need:
            return False, tr("{name}还没折稳——站上去才折得了。", name=label)
        return True, (tr("{name}已经折稳。", name=label) if have
                      else tr("{name}还没折稳。", name=label))
    if kind == "zone_occupants":
        have = len(_zone_hosts(state, record, key))
        need = int(condition.get("min", 0 if "max" in condition else 1))
        if "max" in condition and have > int(condition["max"]):
            return False, tr("{name}里还站着 {have} 个失控意识。", name=label, have=have)
        if have < need:
            return False, tr("{name}里没有站着的东西（要 {need} 个，现在 {have} 个）。",
                             name=label, need=need, have=have)
        return True, (tr("{name}里站着 {have} 个失控意识。", name=label, have=have) if have
                      else tr("{name}是空的。", name=label))
    if kind == "opening_sealed":
        position = record.cell(key)
        if position is None:
            return False, tr("{name}不在这里。", name=label)
        have = 1 if state.cell(*position).solid else 0
        need = int(condition.get("min", 0 if "max" in condition else 1))
        if "max" in condition and have > int(condition["max"]):
            return False, tr("{name}的挡板已经落下了，不用再放。", name=label)
        if have < need:
            return False, tr("{name}还开着。", name=label)
        return True, (tr("{name}的挡板落着。", name=label) if have
                      else tr("{name}还开着。", name=label))
    if kind == "flag_set":
        name = condition.get("name", "")
        flag_label = tr(_FLAG_LABELS.get(name, name))
        have = 1 if record.flags.get(name) else 0
        # 与 end_primed 同一约定：只写 max 的条件是「这一步还没做过」，下界取 0。
        need = int(condition.get("min", 0 if "max" in condition else 1))
        if "max" in condition and have > int(condition["max"]):
            return False, tr("{name}已经立住了，不用再来一次。", name=flag_label)
        if have < need:
            return False, tr("{name}还没着落——先把前一步做完。", name=flag_label)
        return True, (tr("{name}已经立住。", name=flag_label) if have
                      else tr("{name}还没立住。", name=flag_label))
    return False, tr("尚未辨认的条件。")


def _audible_listeners(state: Any, cell: tuple[int, int], radius: int) -> int:
    """按 :meth:`_sound_pulse` 的听觉口径数听众：曼哈顿距离、不算楼梯伪装。

    判据必须与真正会执行诱导的那段一致，否则面板说「有人听得见」而脉冲什么也没做。
    """
    x, y = cell
    return sum(1 for enemy in state.enemies
               if enemy.integrity > 0 and enemy.trait not in ("staircase",)
               and abs(enemy.x - x) + abs(enemy.y - y) <= radius)


def _zone_hosts(state: Any, record: Any, key: str) -> tuple[Any, ...]:
    """作用区里此刻还站着的失控意识（读真实占位）。

    稳定意识的 NPC 不算「踩着保护区」：登记员要的是那位异象出来或不在，不是
    恰好有位旅人在院里说话。
    """
    cells = set(record.area(key))
    return tuple(enemy for enemy in state.enemies
                 if enemy.integrity > 0 and getattr(enemy, "relation", "") == "失控意识"
                 and (enemy.x, enemy.y) in cells)


def _zone_is_safe(state: Any, record: Any, key: str) -> bool:
    """安全＝既没有失控意识站在里头，也没有火与气（全部读真实格子）。"""
    if _zone_hosts(state, record, key):
        return False
    return not any(state.cell(x, y).flame > 0 or state.cell(x, y).gas > 0
                   for x, y in record.area(key))


def threat_uid(record: Any) -> str:
    """常驻目标实例的身份：跟着设施走，层快照重建后还是同一位（§13.2）。

    异象的 ``enemy-N`` 实例编号在重建时会变，用它当任务目标等于「换层回来又能
    领一次奖」；这里按设施 uid 另铸一个稳定 id，写入敌人的 ``actor_uid``。
    """
    return f"{record.scene_uid}#threat"


def threat_target(state: Any, record: Any) -> str:
    """这处设施绑定的目标 UID（定义里没有 ``threat`` 时为空串）。"""
    definition = definition_of(record)
    if not definition or not definition.get("threat"):
        return ""
    return threat_uid(record)


def _allowed_liquids(record: Any) -> tuple[str, ...]:
    definition = definition_of(record)
    return tuple(((definition or {}).get("facility") or {}).get("allowed_liquids") or ())


def _item_name(item_id: str) -> str:
    from ..data.items import ITEM_DEFINITIONS

    return ITEM_DEFINITIONS.get(item_id, {}).get("name", item_id)


def _blockage(state: Any, record: Any, key: str):
    cells = set(record.area(key))
    return next((entry for entry in state.world_items if (entry.x, entry.y) in cells), None)


# --------------------------------------------------------------- 命令结算

def find_command(definition: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((command for command in definition.get("commands", ())
                 if command["command"] == name), None)


def preview(state: Any, record: Any, name: str) -> dict[str, Any]:
    """只读预览：不写事实、不动资源、不推进时间（§13.4 第 1–2 步）。"""
    definition = definition_of(record)
    command = find_command(definition or {}, name)
    if command is None:
        return {"ok": False, "failure": tr("这台设施不会做这个。"), "met": []}
    refresh(state, record)
    met, failure = evaluate(state, record, command.get("conditions", ()))
    if not failure and command.get("cost"):
        failure = state._check_npc_cost(command["cost"]) or ""
    if not failure:
        failure = _gain_refusal_for(state, command, record) or ""
    if not failure:
        failure = _plan(state, record, command).get("reason", "")
    return {"ok": not failure, "met": met, "failure": failure,
            "cost": command.get("cost", {}), "command": command}


def _gain_refusal_for(state: Any, command: dict[str, Any], record=None) -> str | None:
    effect = command.get("effect", {})
    if effect.get("type") != "gain_item":
        return None
    return state._gain_refusal({"item": effect["item"],
                                "count": int(effect.get("count", 1))},
                                source='scene:' + record.definition_id if record is not None else 'scene')


def operate(state: Any, record: Any, name: str) -> ActionResult:
    """执行一条设施命令：预检 → 足额支付 → 提交改变 → 记事实 → 付行动时间。

    任何一步不成立就整笔退回：不扣资源、不扣回合、不写事实（§13.4 第 2 步）。
    """
    definition = definition_of(record)
    if definition is None:
        return _refuse(state, tr("这台设施的定义已经找不到了。"))
    if not local(state, record):
        return _refuse(state, tr("那处设施不在这一层。"))
    command = find_command(definition, name)
    if command is None:
        return _refuse(state, tr("这台设施不会做这个。"))
    effect = command.get("effect", {})
    if effect.get("type") not in EFFECT_TYPES:
        return _refuse(state, tr("这道命令的效果不在允许清单里（{kind}）。",
                                 kind=effect.get("type", "")))
    refresh(state, record)
    _met, failure = evaluate(state, record, command.get("conditions", ()))
    if failure:
        return _refuse(state, failure)
    cost = command.get("cost", {})
    if cost:
        failure = state._check_npc_cost(cost) or ""
        if failure:
            return _refuse(state, failure)
    failure = _gain_refusal_for(state, command, record) or ""
    if failure:
        return _refuse(state, failure)
    queued = _plan(state, record, command)
    if not queued["ok"]:
        return _refuse(state, queued["reason"])
    if len(queued["steps"]) > MAX_COMMANDS_PER_SETTLEMENT:
        return _refuse(state, tr("这一步要改的格子太多，先停下来（上限 {limit}）。",
                                 limit=MAX_COMMANDS_PER_SETTLEMENT))

    if effect.get("type") == "open_gate":
        # 嵌镜是免费的一步：只把门推进「等待支付」并唤出祭品选择面板。真正的代价
        # （三件祭品与一个行动）落在 GameState.confirm_gate_offering——面板确认时才付。
        record.flags["offered"] = True
        record.state = "等待支付"
        message = tr("{name}：透镜嵌进灯座，青灯转向你——挑三件会消散的东西。",
                     name=tr(definition["name"]))
        state.messages.append(message)
        return ActionResult(True, message, {"scene": record.scene_uid, "command": name,
                                            "state": record.state,
                                            "lens_offering": record.scene_uid,
                                            "eligible": _gate_eligible(state),
                                            "gate_name": definition["name"]})

    # ---- 预检全部通过：以下是不可延后的事务结果 ----
    rng = random.Random(state.seed ^ (int(state.time) * 7919)
                        ^ stable_seed(record.scene_uid, name))
    texts: list[str] = []
    if cost:
        texts.extend(state._charge_npc_cost(cost, rng))
    before = record.state
    done = _apply(state, record, command, queued)
    texts.extend(done["texts"])
    # 效果可选带一个具名开关（§9 S01「标出的旁路／中继权限／旅人服务」）：真正立住
    # 才算数，随设施记录一起穿过存档与远层重建。
    flag = str(effect.get("flag") or "")
    if flag:
        record.flags[flag] = True
    # 效果可选带一条调查线索（§7.1 模板 5）：立开关的同时记一条 ``report`` 事实，
    # 任务的 ``clues`` 按 ``cause_uid=clue:<名>`` 只认接取之后立住的那几条。
    clue = str(effect.get("report") or "")
    if clue:
        record.flags[clue] = True
        facts.record(state, "report", actor_uid=player_uid(state),
                     target_uid=record.scene_uid, position=_anchor_cell(record),
                     owner_uid=record.scene_uid, cause_uid=f"clue:{clue}",
                     source_kind="scene", before="未辨认", after="已辨认", amount=1)
    for stock_name, amount in (command.get("spends") or {}).items():
        record.spend(stock_name, int(amount))
    for stock_name, amount in (command.get("gives") or {}).items():
        record.stock[stock_name] = max(0, int(record.stock.get(stock_name, 0)) + int(amount))
    if record.state == "耗尽" and any(int(value) > 0 for value in record.stock.values()):
        # 玩家亲手把材料填了回去：§10.2 说的是「还能支持一次操作」，那就该回到可激活。
        record.state = _idle_state(state, record, definition)
    _advance_lifecycle(state, record, definition, command)
    facts.record(state, "facility", actor_uid=player_uid(state), target_uid=record.scene_uid,
                 position=_anchor_cell(record), owner_uid=record.scene_uid,
                 cause_uid=f"{definition['definition_id']}#{name}", source_kind="scene",
                 before=before, after=record.state, amount=done["amount"])
    message = tr("{name}：{choice}。{detail}", name=tr(definition["name"]),
                 choice=tr(command["label"]), detail="，".join(texts))
    state.messages.append(message)
    state._action_time(1, ActionKind.USE)
    return ActionResult(True, message, {"scene": record.scene_uid, "command": name,
                                        "state": record.state})


def _refuse(state: Any, reason: str) -> ActionResult:
    """未满足／付不出：只给原因，不动资源、时间与记录。"""
    if reason:
        state.messages.append(reason)
    return ActionResult(False, reason)


def _anchor_cell(record: Any) -> tuple[int, int] | None:
    return record.cell((definition_of(record) or {}).get("anchor") or "")


def _plan(state: Any, record: Any, command: dict[str, Any]) -> dict[str, Any]:
    """把效果翻译成有限命令队列，并在这里检查「真的改变得了」——不会改变任何事就不扣费。"""
    effect = command["effect"]
    kind = effect["type"]
    if kind == "ignite_anchor":
        position = record.cell(effect["key"])
        if position is None or not state._cell_is_flammable(state.cell(*position)):
            return _no_change(tr("这里的地面接不住火——什么也不会发生。"))
        return {"ok": True, "reason": "", "steps": ({"kind": "ignite", "cell": position},)}
    if kind == "ignite_zone":
        cells = [cell for cell in record.area(effect["key"])
                 if state._cell_is_flammable(state.cell(*cell))]
        if not cells:
            return _no_change(tr("术阵地面接不住火——先装料。"))
        return {"ok": True, "reason": "", "steps": tuple({"kind": "ignite", "cell": cell}
                                                         for cell in cells)}
    if kind == "release_liquid":
        target = _release_targets(state, record, effect)
        if not target:
            return _no_change(tr("没有能落脚的格子，水过不去。"))
        if effect.get("from_stock"):
            have = int(record.stock.get(effect["from_stock"], 0))
            units = min(int(effect["units"]), have)
            if units <= 0:
                return _no_change(tr("管道余量已经空了。"))
            return {"ok": True, "reason": "", "steps": (
                {"kind": "liquid", "units": units, "liquid": effect["kind"],
                 "targets": target, "source": None, "stock": effect["from_stock"]},)}
        source = record.cell(effect["from_key"])
        cell = state.cell(*source) if source else None
        if cell is None or int(cell.liquid) <= 0:
            return _no_change(tr("盆里已经没有水了。"))
        units = min(int(effect["units"]), int(cell.liquid))
        return {"ok": True, "reason": "", "steps": (
            {"kind": "liquid", "units": units, "liquid": cell.liquid_kind,
             "targets": target, "source": source, "stock": ""},)}
    if kind == "clear_blockage":
        entry = _blockage(state, record, effect["key"])
        if entry is None:
            return _no_change(tr("排放区里没有能搬动的东西。"))
        spot = _vacant_outside(state, record, effect["key"], entry.x, entry.y)
        if spot is None:
            return _no_change(tr("搬不动——周围没有能放的地方。"))
        return {"ok": True, "reason": "", "steps": ({"kind": "blockage", "entry": entry,
                                                     "spot": spot},)}
    if kind == "sound_pulse":
        position = record.cell(effect["key"])
        radius = int(effect.get("radius", 5))
        heard = 0 if position is None else _audible_listeners(state, position, radius)
        if not heard:
            return _no_change(tr("这个方向没有听得见的失控意识——喊了也没人跟着走。"))
        return {"ok": True, "reason": "", "steps": (
            {"kind": "pulse", "cell": position, "radius": radius, "heard": heard},)}
    if kind == "fold_travel":
        ends = tuple(record.cell(key) for key in effect["ends"])
        if any(cell is None for cell in ends):
            return _no_change(tr("这对折页已经不在这一层了。"))
        radius = int(effect.get("radius", 1))
        gaps = [max(abs(state.player.x - x), abs(state.player.y - y)) for x, y in ends]
        if min(gaps) > radius:
            return _no_change(tr("你得站在某一张折页上才折得过去。"))
        index = 1 - gaps.index(min(gaps))
        landing = _fold_landing(state, ends[index], int(effect.get("search", 2)))
        if landing is None:
            return _no_change(tr("另一侧没有能落脚的格子——不把你折进墙里。"))
        return {"ok": True, "reason": "", "steps": (
            {"kind": "fold", "cell": landing, "key": effect["ends"][index]},)}
    if kind == "seal_opening":
        position = record.cell(effect["key"])
        if position is None:
            return _no_change(tr("这道门不在这一层了。"))
        x, y = position
        if state.cell(x, y).solid:
            return _no_change(tr("挡板已经落下了。"))
        if state.entity_at(x, y) is not None:
            return _no_change(tr("挡板上正站着东西——落下去会把它压进地里。"))
        return {"ok": True, "reason": "", "steps": ({"kind": "seal", "cell": position},)}
    if kind == "mark_route":
        variant = effect.get("variant", "反光聚合物")
        cells = [cell for cell in record.area(effect["key"])
                 if not state.cell(*cell).solid and not state.cell(*cell).wall_kind]
        changed = [cell for cell in cells
                   if state.cell(*cell).aggregate_variant != variant]
        if not changed:
            return _no_change(tr("这条路已经标出来了——没有新的一格会亮起来。"))
        return {"ok": True, "reason": "", "steps": (
            {"kind": "route", "cells": tuple(changed), "variant": variant},)}
    if kind == "open_gate":
        # 嵌镜只负责开门与唤面板；够不够三件祭品由这一步先判，凑不齐就不推进门态。
        gift = int(effect.get("gift", 3))
        if len(_gate_eligible(state)) < gift:
            return _no_change(tr("祭品还不够——要 {n} 件易逝物或摄入物。", n=gift))
        return {"ok": True, "reason": "", "steps": ({"kind": "gate_open"},)}
    if kind == "enter_gate":
        return {"ok": True, "reason": "", "steps": (
            {"kind": "gate_enter", "realm": str(effect.get("realm", ""))},)}
    # ---- R03 留灯的避难圈 ----
    if kind == "light_lamp":
        # 点亮留灯：真的改地面＋立 ``lit`` 开关。已经点着就不该再扣一次想象力。
        if record.flags.get("lit"):
            return _no_change(tr("留灯已经点着了，不用再点。"))
        return {"ok": True, "reason": "", "steps": ({"kind": "lamp_light"},)}
    if kind == "grant_rest":
        stat = str(effect.get("stat", "mind"))
        if record.flags.get("rested"):
            return _no_change(tr("这一处你已经歇过了——一次为限。"))
        if getattr(state, stat, 0) >= getattr(state, f"max_{stat}", 0):
            # 满血时拒绝休息：不消耗那一次名额，也不推时间（省下来以后还能歇）。
            return _no_change(tr("你此刻并不缺这些——歇着也回不了更多。"))
        return {"ok": True, "reason": "", "steps": (
            {"kind": "rest", "stat": stat, "amount": int(effect.get("amount", 4))},)}
    if kind == "repair_opening":
        position = record.cell(effect["key"])
        if position is None:
            return _no_change(tr("这道门不在这一层了。"))
        if not state.cell(*position).solid:
            return _no_change(tr("挡板本来就抬着——门没被堵上。"))
        return {"ok": True, "reason": "", "steps": ({"kind": "repair", "cell": position},)}
    if kind == "report_clue":
        # 调查／辨认类命令（§7.1 模板 5）：不改地图，只把线索立成具名开关 +
        # 一条 ``report`` 事实（线索落账在 operate 的 report 钩子里统一做）。
        clue = str(effect.get("report") or "")
        if clue and record.flags.get(clue):
            return _no_change(tr("这一条你已经在册子上记过了。"))
        return {"ok": True, "reason": "", "steps": ({"kind": kind},)}
    return {"ok": True, "reason": "", "steps": ({"kind": kind},)}


def _no_change(reason: str) -> dict[str, Any]:
    return {"ok": False, "reason": reason, "steps": ()}


def _release_targets(state: Any, record: Any, effect: dict[str, Any]) -> tuple[tuple[int, int], ...]:
    key = effect["to_key"]
    single = record.cell(key)
    cells = (single,) if single else record.area(key)
    return tuple(cell for cell in cells
                 if cell and not state.cell(*cell).solid and 0 < cell[0] < state.width - 1
                 and 0 < cell[1] < state.height - 1)


def _vacant_outside(state: Any, record: Any, key: str,
                    x: int, y: int) -> tuple[int, int] | None:
    """挡路物要搬到区域**外面**的空格：不销毁物品，只是不堵着了。"""
    inside = set(record.area(key))
    occupied = {(entry.x, entry.y) for entry in state.world_items}
    for radius in range(1, 4):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 < nx < state.width - 1 and 0 < ny < state.height - 1):
                    continue
                if (nx, ny) in inside or (nx, ny) in occupied:
                    continue
                cell = state.cell(nx, ny)
                if cell.solid or cell.wall_kind or state.entity_at(nx, ny) is not None:
                    continue
                return (nx, ny)
    return None


def _fold_landing(state: Any, cell: tuple[int, int], search: int) -> tuple[int, int] | None:
    """对端最近的合法落脚格：先试原地，再一圈圈往外找到 ``search`` 半径（§9 R04）。"""
    if _landing_ok(state, *cell):
        return cell
    for radius in range(1, search + 1):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                spot = (cell[0] + dx, cell[1] + dy)
                if _landing_ok(state, *spot):
                    return spot
    return None


def _landing_ok(state: Any, x: int, y: int) -> bool:
    """传送落点的硬检查：实体、墙、植物与线路、已知火／气、站着的东西、电路格都不能进。"""
    if not (0 <= x < state.width and 0 <= y < state.height):
        return False
    cell = state.cell(x, y)
    if cell.solid or cell.wall_kind or cell.wire or cell.plant:
        return False
    if cell.flame > 0 or cell.gas > 0:
        return False
    return state.entity_at(x, y) is None and state.circuit_node_at(x, y) is None


def _apply(state: Any, record: Any, command: dict[str, Any],
           queued: dict[str, Any]) -> dict[str, Any]:
    """提交效果。每条都落到既有公共结算入口，不在此计算任何伤害。"""
    effect = command["effect"]
    kind = effect["type"]
    if kind == "ignite_anchor":
        x, y = queued["steps"][0]["cell"]
        lit = state._ignite_cell(x, y, int(effect.get("strength", 3)), by_player=True)
        label = tr(_ANCHOR_LABELS.get(effect["key"], effect["key"]))
        return _result([tr("{name}烧起来了。", name=label)] if lit else [], int(lit))
    if kind == "ignite_zone":
        # 激活只排入「预告」；真正点火在 resolve_pending——一个实际行动之后。
        return _result([tr("术阵开始预热：下一个行动后成火场。")], 0)
    if kind == "quench_anchor":
        x, y = record.cell(effect["key"])
        state._set_flame(x, y, 0)
        state._sync_material_position(x, y)
        label = tr(_ANCHOR_LABELS.get(effect["key"], effect["key"]))
        return _result([tr("{name}的火被踩灭了。", name=label)], 1)
    if kind == "priming_zone":
        from ..core.scenes import set_floor_variant

        variant = effect.get("variant", "书页地")
        fuel = int(effect.get("fuel", 12))
        count = sum(1 for x, y in record.area(effect["key"])
                    if set_floor_variant(state, x, y, variant, fuel, persist=True))
        return _result([tr("干纸重新铺满术阵（{n} 格）。", n=count)], count)
    if kind == "prime_end":
        from ..core.scenes import set_floor_variant

        x, y = record.cell(effect["key"])
        set_floor_variant(state, x, y, effect.get("variant", "反光聚合物"), persist=True)
        record.flags[effect["key"]] = True
        label = tr(_ANCHOR_LABELS.get(effect["key"], effect["key"]))
        return _result([tr("{name}被折稳了。", name=label)], 1)
    if kind == "mark_route":
        from ..core.scenes import set_floor_variant

        step = queued["steps"][0]
        count = sum(1 for x, y in step["cells"]
                    if set_floor_variant(state, x, y, step["variant"], persist=True))
        return _result([tr("地上亮起一条路（{n} 格）。", n=count)], count)
    if kind == "fold_travel":
        from ..core.scenes import fold_player

        step = queued["steps"][0]
        fold_player(state, step["cell"][0], step["cell"][1])
        label = tr(_ANCHOR_LABELS.get(step["key"], step["key"]))
        return _result([tr("你被折到了{name}那一侧。", name=label)], 1)
    if kind == "release_liquid":
        step = queued["steps"][0]
        units = int(step["units"])
        liquid = step["liquid"]
        targets = step["targets"]
        if step["source"] is not None:
            cell = state.cell(*step["source"])
            taken = min(units, int(cell.liquid))
            cell.liquid = int(cell.liquid) - taken
            if cell.liquid <= 0:
                cell.liquid_kind = ""
        else:
            taken = units
            # 阀门进水的盆要保住「只认水」的材料口径：盆里若已有别的液体
            # （玩家倒进来的、或紧邻液池渗进来的），阀门压力先把它顶走——
            # 否则 anchor_liquid 的种类检查会永久卡死开闸（2026-10-11 修复）。
            allowed = _allowed_liquids(record)
            flush = record.cell(effect["to_key"])
            if flush and allowed:
                basin = state.cell(*flush)
                if basin.liquid > 0 and basin.liquid_kind not in allowed:
                    state.messages.append(tr(
                        "阀门的水把盆里的{kind}顶走了。", kind=tr(basin.liquid_kind)))
                    basin.liquid, basin.liquid_kind = 0, ""
        per, extra = divmod(taken, len(targets))
        for index, (x, y) in enumerate(targets):
            give = per + (1 if index < extra else 0)
            if give:
                state._add_liquid(state.cell(x, y), liquid, give)
        facts.record(state, "material", actor_uid=player_uid(state),
                     target_uid=f"{record.scene_uid}#{effect['to_key']}",
                     position=targets[0], owner_uid=record.scene_uid,
                     cause_uid=effect["to_key"], source_kind="scene",
                     before=taken, after=0, amount=taken)
        return _result([tr("放出了 {kind} ×{n}。", kind=tr(liquid), n=taken)], taken)
    if kind == "clear_blockage":
        step = queued["steps"][0]
        entry, spot = step["entry"], step["spot"]
        state.world_items.remove(entry)
        from ..core.entities import WorldItem

        state.world_items.append(WorldItem(entry.item, spot[0], spot[1]))
        return _result([tr("把 {name} 搬到了外面。", name=tr(entry.item.name))], 1)
    if kind == "sound_pulse":
        step = queued["steps"][0]
        state._sound_pulse(step["cell"][0], step["cell"][1], step["radius"])
        label = tr(_ANCHOR_LABELS.get(effect["key"], effect["key"]))
        return _result([tr("喇叭把呼叫送向{name}。", name=label)], int(step["heard"]))
    if kind == "seal_opening":
        from ..core.scenes import seal_opening as _seal

        x, y = queued["steps"][0]["cell"]
        sealed = int(_seal(state, x, y))
        label = tr(_ANCHOR_LABELS.get(effect["key"], effect["key"]))
        return _result([tr("{name}的挡板落下了。", name=label)] if sealed else [], sealed)
    if kind == "transfer_stock":
        name = effect["name"]
        record.stock[name] = int(record.stock.get(name, 0)) + int(effect["amount"])
        return _result([tr("{name} +{n}。", name=tr(_STOCK_LABELS.get(name, name)),
                                          n=effect["amount"])], int(effect["amount"]))
    if kind == "gain_item":
        count = int(effect.get("count", 1))
        for _ in range(count):
            item = state._make_item(effect["item"])
            state._add_inventory_item(item)
            from ..core.item_access import record_grant
            record_grant(state, item.definition_id, source='scene:' + record.definition_id)
        return _result([tr("收进行囊：{name} ×{n}。", name=tr(_item_name(effect["item"])),
                                           n=count)], count)
    if kind == "enter_gate":
        # 真正走进位面：交给 GameState.enter_realm，不在这里另写一套进入规则。
        into = state.enter_realm(str(queued["steps"][0]["realm"]))
        if into:
            record.flags["entered"] = True
            record.state = "已进入"
        return _result([tr("门在你身后合上了。")] if into else [], 1 if into else 0)
    # ---- R03 留灯的避难圈 ----
    if kind == "light_lamp":
        from ..core.scenes import set_floor_variant

        variant = effect.get("variant", "反光聚合物")
        count = sum(1 for x, y in record.area(effect["key"])
                    if set_floor_variant(state, x, y, variant, persist=True))
        lamp = record.cell("lamp")
        if lamp and set_floor_variant(state, lamp[0], lamp[1], variant, persist=True):
            count += 1
        record.flags["lit"] = True
        return _result([tr("留灯亮了起来，灯圈的地面反出光（{n} 格）。", n=count)], count)
    if kind == "grant_rest":
        step = queued["steps"][0]
        stat = str(step["stat"])
        before = getattr(state, stat, 0)
        cap = getattr(state, f"max_{stat}", before)
        setattr(state, stat, min(cap, before + int(step["amount"])))
        record.flags["rested"] = True
        gained = int(getattr(state, stat, 0) - before)
        return _result([tr("你靠着灯台坐了一会儿：{stat} +{n}。",
                           stat=tr(_STAT_LABELS.get(stat, stat)), n=gained)], gained)
    if kind == "repair_opening":
        from ..core.scenes import unseal_opening

        x, y = queued["steps"][0]["cell"]
        repaired = int(unseal_opening(state, x, y))
        label = tr(_ANCHOR_LABELS.get(effect["key"], effect["key"]))
        record.flags["repaired"] = True
        return _result([tr("{name}的挡板抬起来了。", name=label)] if repaired else [], repaired)
    if kind == "report_clue":
        return _result([tr("你把这一条记在了心里。")], 1)
    return _result([], 0)


def _result(texts: list[str], amount: int) -> dict[str, Any]:
    return {"texts": texts, "amount": amount}


def _advance_lifecycle(state: Any, record: Any, definition: dict[str, Any],
                       command: dict[str, Any]) -> None:
    params = definition["facility"]
    state_after = command.get("state_after")
    if state_after == "预告":
        record.state = "预告"
        # 激活自己这一笔行动会把 action_seq 推到 +1，所以 due 取 +2：
        # 玩家「又完成一次实际行动」之后火场才落地（§10.2）。
        record.pending = {"key": command["effect"]["key"],
                          "strength": int(command["effect"].get("strength", 4)),
                          "due_seq": int(state.action_seq) + 2,
                          "rounds": int(params.get("effect_rounds", 4))}
        record.cooldown_until = int(state.time) + int(params.get("cooldown_rounds", 6))
    elif state_after == "生效":
        record.state = "生效"
        record.cooldown_until = int(state.time) + int(params.get("cooldown_rounds", 6))
    elif state_after == "冷却":
        record.state = "冷却"
        record.cooldown_until = int(state.time) + int(params.get("cooldown_rounds", 6))


# --------------------------------------------------------------- 时间推进

def resolve_pending(state: Any) -> None:
    """场景的三件时间驱动的事：把「预告」落地、数「连续安全」、重算显示态（§10.2）。

    由 :meth:`tempo._action_time` 在每次行动结算**之后**调用，所以新建立的伤害场
    至少等玩家又完成一次实际行动才落地；免费行动那条路径根本不走这里。

    只处理 ``data.scenes.SCENE_DEFINITIONS`` 里登记的场景设施：``FacilityRecord``
    也被普通遭遇样板（``encounter.*``）复用，它们的 ``pending`` 是走廊改写倒计时
    之类的自有结构，不能被场景的 ``due_seq``／``_land`` 误当成伤害场落地。
    """
    from ..data.scenes import SCENE_DEFINITIONS

    for record in records(state):
        if record.definition_id not in SCENE_DEFINITIONS:
            continue
        pending = record.pending
        if pending and int(state.action_seq) >= int(pending.get("due_seq", 0)):
            _land(state, record, pending)
    _advance_holds(state)
    refresh(state)


def _advance_holds(state: Any) -> None:
    """把「连续安全」的账往前推一格——只在行动结算之后数（§13.4）。

    与 :func:`refresh` 分开是必需的：面板每帧都 ``preview``，而预览是只读的；
    把计数挂在 ``refresh`` 里会让「看一眼」也凑满三个回合。
    """
    for record in records(state):
        definition = definition_of(record)
        if definition is None or not local(state, record):
            continue
        _update_holds(state, record, definition)


def _land(state: Any, record: Any, pending: dict[str, Any]) -> None:
    """真正点火：逐格走 ``_ignite_cell``，这里没有任何伤害公式。"""
    strength = int(pending.get("strength", 4))
    lit = 0
    for x, y in record.area(pending.get("key", "")):
        if state._ignite_cell(x, y, strength, by_player=True):
            lit += 1
    before = record.state
    record.pending = {}
    record.state = "生效"
    record.cooldown_until = int(state.time) + int(pending.get("rounds", 4))
    facts.record(state, "facility", actor_uid=player_uid(state),
                 target_uid=record.scene_uid, position=_anchor_cell(record),
                 owner_uid=record.scene_uid, cause_uid="pending:ignite_zone",
                 source_kind="scene", before=before, after=record.state, amount=lit)
    state.messages.append(tr("术阵的火场起来了（{n} 格）。", n=lit))


def refresh(state: Any, record: Any | None = None) -> None:
    """按世界时刻与当前地图重算显示态；火场到期后留一条 ``safety`` 事实。"""
    targets = [record] if record is not None else records(state)
    for entry in targets:
        definition = definition_of(entry)
        if definition is None or not local(state, entry):
            continue
        gate = definition.get("gate")
        if entry.state == "休眠" and _seen(state, entry):
            entry.state = "未开启" if gate else "可激活"
            continue
        if gate:
            # 门是纯状态机，没有冷却／火场那一套：每次刷新从 flags 与位面关停表重算，
            # 所以「开启」之后远层重建回来读到的还是同一个门态（§8 S23）。
            entry.state = _gate_state(state, entry)
            continue
        if entry.state == "生效" and int(state.time) < entry.cooldown_until:
            continue
        if entry.state == "生效":
            zone = definition["facility"].get("zone_key", "")
            still = sum(1 for x, y in entry.area(zone) if state.cell(x, y).flame > 0)
            if still:
                entry.cooldown_until = int(state.time) + 1
                continue
            before = entry.state
            _note_burnt_floor(state, entry, zone)
            entry.state = _idle_state(state, entry, definition)
            facts.record(state, "safety", actor_uid="", target_uid=entry.scene_uid,
                         position=_anchor_cell(entry), owner_uid=entry.scene_uid,
                         cause_uid="facility:expired", source_kind="scene",
                         before=before, after=entry.state)
            state.messages.append(tr("{name}的火场过去了，这条路重新打通。",
                                     name=tr(definition["name"])))
        elif entry.state == "冷却" and entry.ready(int(state.time)):
            entry.state = _idle_state(state, entry, definition)


def mark_invasions(state: Any) -> None:
    """Enemy movement phase: any intrusion into a safe zone breaks that hold segment.

    ``resolve_pending`` runs after world time advances, by which point a wandering
    threat may already have left the yard again. Checking right after enemy turns
    keeps "它进来过" from being erased by "它又走了".
    """
    for record in records(state):
        definition = definition_of(record)
        if definition is None:
            continue
        for zone in definition.get("safe_zones") or ():
            if _zone_hosts(state, record, zone):
                record.safe_since.pop(zone, None)
                record.flags.pop(f"safe:{zone}", None)


def _update_holds(state: Any, record: Any, definition: dict[str, Any]) -> None:
    """按**世界回合**累计「连续安全」的时长，断了就整段重数（§7.2 保持 3 回合）。

    计数单位取世界时刻而不是 refresh 调用次数：一步免费的观察、一次亚回合结算都不
    该把三回合的把守提前凑满。达成时只记一条 ``safety`` 事实并当场播报，任务据此
    认「诱离封守」这条解法；之后再断不影响已经成立的那一次。
    """
    zones = definition.get("safe_zones") or ()
    if not zones:
        return
    now = int(state.time)
    need = int(definition.get("hold_rounds", 3))
    # 可选前置：某些场景要求先立住一个具名开关（R03「点亮留灯」）才算开始计数。
    # 不声明 ``hold_flag`` 的场景（如泵房）行为不变。
    hold_flag = str(definition.get("hold_flag") or "")
    for zone in zones:
        if hold_flag and not record.flags.get(hold_flag):
            # 灯还没亮：既不累计也不保留上一段的安全起点，等于「还没开始数」。
            record.safe_since.pop(zone, None)
            continue
        if not _zone_is_safe(state, record, zone):
            record.safe_since.pop(zone, None)
            # 断了就把「这一段报过了」的闩放下来：下一段连续安全是新的一段。
            # 实玩里那位常常在玩家赶到之前就自己溜出院子，第一段安全早在接单之前
            # 就报过了；闩不放下，诱离封守这条解法在那张图上永远凑不成。
            record.flags.pop(f"safe:{zone}", None)
            continue
        since = record.safe_since.get(zone)
        if since is None:
            record.safe_since[zone] = now
            continue
        held = now - int(since)
        if held < need or record.flags.get(f"safe:{zone}"):
            continue
        record.flags[f"safe:{zone}"] = True
        facts.record(state, "safety", actor_uid="", target_uid=record.scene_uid,
                     position=_anchor_cell(record), owner_uid=record.scene_uid,
                     cause_uid=f"hold:{zone}", source_kind="scene",
                     before="持续看住", after="连续安全", amount=held)
        state.messages.append(tr("{name}连着 {n} 个世界回合没有失控意识踩进去——这一条记在你账上。",
                                 name=tr(definition["name"]), n=held))
        # R03：这一段连续安全兑现成一段抵抗窗口（数据声明目标征兆与时长）。闩的语义
        # 即「每段连续安全只授一次」；断了重数可再授（对应「失去安全条件后不再续」）。
        ward = definition.get("ward") or {}
        if ward:
            state.portent_ward_id = str(ward.get("portent", ""))
            state.portent_ward_turns = int(ward.get("turns", 6))
            state.messages.append(tr("{name}把一圈留灯围稳了：{n} 回合内新沾染的负面征兆会轻一些。",
                                     name=tr(definition["name"]),
                                     n=state.portent_ward_turns))


def _note_burnt_floor(state: Any, record: Any, zone: str) -> None:
    """把火场过期后的地面记成地形增量（§12.2「必要格子增量」）。

    只记这一片作用区（≤9 格），不给整层火场记账；远层重建后「烧完的地面不会
    自己长回来」这句话仍然成立，而玩家也仍然要靠装料命令把它换回可燃地面。
    """
    from ..core.scenes import set_floor_variant

    if not zone:
        return
    for x, y in record.area(zone):
        cell = state.cell(x, y)
        set_floor_variant(state, x, y, cell.aggregate_variant, cell.floor_fuel, persist=True)


def _idle_state(state: Any, record: Any, definition: dict[str, Any]) -> str:
    """剩余资源还能支持一次操作就回到「可激活」，否则「耗尽」（§10.2）。

    储量见底不等于设施已经没用：上游阀把水放进盆里之后，那滩水是「开闸」要搬的
    **实体**，盆里还有水就把设施判成烧空，等于把玩家自己交付的液体锁死在原地。
    """
    if any(int(value) > 0 for value in record.stock.values()):
        return "可激活"
    if not (definition["facility"].get("stock")):
        return "可激活"
    if _deliverable_liquid(state, record, definition):
        return "可激活"
    return "耗尽"


def _deliverable_liquid(state: Any, record: Any, definition: dict[str, Any]) -> int:
    """设施进料口里还实有多少可以搬走的液体（§10.3「只搬运真实储量」的反面读法）。"""
    total = 0
    for command in definition.get("commands", ()):
        effect = command.get("effect") or {}
        if effect.get("type") != "release_liquid" or not effect.get("from_key"):
            continue
        position = record.cell(effect["from_key"])
        if position is None:
            continue
        cell = state.cell(*position)
        if int(cell.liquid) > 0:
            total += int(cell.liquid)
    return total


def _gate_state(state: Any, record: Any) -> str:
    """§8 S23 门的五态：未开启 → 等待支付 → 开启 → 已进入（位面被关停则「已关闭」）。

    只读 ``flags`` 与 ``state.closed_realms``，不引入第二份持久状态：``refresh`` 每次
    重算，门态因此随存档一起穿过远层重建。``entered`` 是终点——同一条门不再放人进去。
    """
    definition = definition_of(record) or {}
    realm = str((definition.get("gate") or {}).get("realm", ""))
    if realm and realm in state.closed_realms:
        return "已关闭"
    if record.flags.get("entered"):
        return "已进入"
    if record.flags.get("paid"):
        return "开启"
    if record.flags.get("offered"):
        return "等待支付"
    return "未开启"


def _gate_eligible(state: Any) -> list[list[Any]]:
    """行囊里能当祭品的条目：``[下标, 名称, 类别]``，供选择面板列出并回传（§8 S23）。"""
    return [[index, entry.name, entry.category]
            for index, entry in enumerate(state.inventory)
            if entry.category in GATE_GIFT_CATEGORIES]


def _seen(state: Any, record: Any) -> bool:
    """任一功能格进入视野就算「看清」：不写死某一台设施的关键格名。"""
    for key in record.layout:
        if key == "origin":
            continue
        position = record.cell(key)
        if position and state.is_visible(*position):
            return True
    return False


def describe(state: Any, record: Any) -> list[str]:
    """面板说明：状态、储量、冷却与每条命令的已知条件都读同一份结构（§10.1／§14）。

    「还没看清」的设施（休眠）只给一句范围说明——未观察的东西不能列成可操作清单，
    面板也就不会比玩家的实地知识说得更靠前。
    """
    definition = definition_of(record)
    if definition is None:
        return []
    from ..core.content import npc_cost_parts

    name = tr(definition["name"])
    if record.state == "休眠":
        return [tr("{name}还没被看清——走近到能看见它的位置，才知道现在能不能动。", name=name)]
    lines = [tr("{name}：{state}", name=name, state=tr(record.state))]
    if record.cooldown_until > int(state.time):
        lines.append(tr("冷却到第 {until} 世界回合（现在第 {now} 回合）。",
                        until=record.cooldown_until, now=int(state.time)))
    stock = tr("、").join(f"{tr(_STOCK_LABELS.get(entry, entry))} {amount}"
                          for entry, amount in sorted(record.stock.items()) if amount > 0)
    if stock:
        lines.append(tr("储量：{stock}", stock=stock))
    for command in definition.get("commands", ()):
        _met, failure = evaluate(state, record, command.get("conditions", ()))
        label = tr(command["label"])
        if failure:
            lines.append(tr("· {label}——{why}", label=label, why=failure))
            continue
        cost = tr("、").join(tr(template, **fields) for template, fields in npc_cost_parts(command))
        lines.append(tr("· {label}——现在就能做。{cost}", label=label,
                        cost=tr("（代价：{cost}）", cost=cost) if cost else ""))
    return lines
