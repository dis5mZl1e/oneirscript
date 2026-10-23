"""投掷系统（2026-09-19，与弹道 ballistics 并列）。

投掷与发射的本质区别：发射（fire/fire_assisted）是**直线弹道**，必须沿线
打中；投掷是**抛物**，允许把物体扔到视野内任何没有障碍物的空地目标——
落点即爆心/火心。低台面可以投越，实墙和斜角封闭夹缝仍会截断。

本模块承载投掷的全部核心结算：
- :func:`directional_landing` —— 方向投掷（q 键）的落点推算（撞墙/出界即停）；
- :func:`is_valid_target` —— 瞄准投掷（使用进入发射界面后点选）的目标校验；
- :func:`resolve_landing` —— 落点结算：爆炸/火海/火星/普通落地。

物品的消耗与时间结算由调用方（core.actions）负责；本模块只做几何与效果。
"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from ..i18n import tr
from ..materials import TABLE_KINDS
from .cast_fx import animate_landing
from .constants import PROJECTILE_MAX_RANGE

# 投掷最大距离（格）。
THROW_MAX_RANGE = 6


def flight_path(origin: tuple[int, int], landing: tuple[int, int]) -> list[tuple[int, int]]:
    """结算前的起点到落点的均匀投影；不把行动后的位移当成飞行起点。"""
    x, y = origin
    tx, ty = landing
    dx, dy = abs(tx - x), abs(ty - y)
    sx, sy = (1 if tx > x else -1), (1 if ty > y else -1)
    error = dx - dy
    path = []
    while (x, y) != (tx, ty):
        twice = 2 * error
        if twice > -dy:
            error -= dy
            x += sx
        if twice < dx:
            error += dx
            y += sy
        path.append((x, y))
    return path

# 这些 effect 的落点会「爆/烧」，空地即可为目标；其它物品投掷=落地可拾回。
_LANDING_EFFECTS = ("explosion", "fireburst", "tar_burst", "spark_rays", "ignite_burst")
# Explicit impact mechanisms, rather than every item that has a use effect.
LANDING_EFFECTS = frozenset((*_LANDING_EFFECTS,'sound_lure','smoke_cloud'))


# 焦油弹：十字五格的一层燃油 = 20 单位，三批合计 60。
_TAR_WAVE_TOTAL = 20


def tar_wave_cells(state: Any, x: int, y: int) -> list[list[int]]:
    """一批焦油在十字上的落点清单 `[[x, y, 单位], ...]`，合计 20。

    只算真正接得住的那几格（墙格那份不追补），按格均分、余数从中心起补；
    台面存不住液，`release_targets` 会把那一份摊给四邻。五格齐全时每格 4。
    """
    usable = []
    for tx, ty in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if release_targets(state, tx, ty, 0):
            usable.append((tx, ty))
    if not usable:
        return []
    share, extra = divmod(_TAR_WAVE_TOTAL, len(usable))
    out: list[list[int]] = []
    for index, (tx, ty) in enumerate(usable):
        amount = share + (1 if index < extra else 0)
        if amount <= 0:
            continue
        for gx, gy, got in release_targets(state, tx, ty, amount):
            out.append([gx, gy, got])
    return out


def pour_tar(state: Any, cells: list[list[int]]) -> int:
    """把一批焦油泼下去，返回实际铺下的单位数。

    防火层铺不上；异种液体不被焦油顶掉；空地与自己那层旧焦油都能再叠。
    """
    from ..materials import floor_fireproof

    laid = 0
    for gx, gy, amount in cells:
        amount = int(amount)
        if amount <= 0:
            continue
        cell = state.cell(int(gx), int(gy))
        if floor_fireproof(cell):
            continue
        if cell.liquid > 0 and cell.liquid_kind != "燃油":
            continue
        state._add_liquid(cell, "燃油", amount)
        laid += amount
    return laid


def throw_range(state: Any) -> int:
    """有效投掷距离：基础 6 格 + 投石索等「投掷强化」每级 +3，封顶与弹道同距 12 格。"""
    return min(PROJECTILE_MAX_RANGE,
               THROW_MAX_RANGE + state._effect_power("throw_master") * 3)


def carrying_surface(state: Any, x: int, y: int) -> bool:
    """本格是否为「台面」——坚实得不能站人，却正是放置物品的合法承载面。"""
    return (0 <= x < state.width and 0 <= y < state.height
            and state.cell(x, y).wall_kind in TABLE_KINDS)


def flyable_over(state: Any, x: int, y: int) -> bool:
    """抛物允许越过／停驻的格：空地与台面之外才算撞墙停下。"""
    cell = state.cell(x, y)
    return not cell.solid or carrying_surface(state, x, y)


def release_targets(state: Any, x: int, y: int, amount: int) -> list[tuple[int, int, int]]:
    """一份液/气落在 (x, y) 时的实际分配。

    空地留在原地；台面自身存不下液气，但中心那份不该被吞掉——按四邻合法
    空地均分（余数从前排邻格起补），总量守恒。非承载的坚实格返回空列表。
    """
    if not (0 <= x < state.width and 0 <= y < state.height):
        return []
    cell = state.cell(x, y)
    if not cell.solid:
        return [(x, y, amount)]
    if not carrying_surface(state, x, y):
        return []
    here = [(nx, ny) for nx, ny in ((x, y + 1), (x, y - 1), (x + 1, y), (x - 1, y))
            if 0 <= nx < state.width and 0 <= ny < state.height
            and not state.cell(nx, ny).solid]
    if not here:
        return []
    share, extra = divmod(amount, len(here))
    return [(tx, ty, share + (1 if i < extra else 0)) for i, (tx, ty) in enumerate(here)]


@dataclass(frozen=True)
class ThrowTrace:
    landing: tuple[int,int]
    path: tuple[tuple[int,int],...]
    blocked: bool
    uncertain: tuple[tuple[int,int],...]=()


def trace_throw(state: Any, tx: int, ty: int, *, known_only: bool=False) -> ThrowTrace:
    """Shared geometry. Preview never reads a hidden cell's obstruction state."""
    origin=(state.player.x,state.player.y)
    last=origin; path=[]; uncertain=set()
    def blocked(point):
        x,y=point
        if not (0<=x<state.width and 0<=y<state.height): return True
        if known_only and not state.is_visible(x,y):
            uncertain.add(point)
            return None
        return not flyable_over(state,x,y)
    def finish(obstructed):
        # Passing over a task surface does not authorize landing on it when a
        # later, unseen obstacle stops the throw. Fall at the last legal spot.
        for index in range(len(path)-1,-1,-1):
            point=path[index]
            if not (known_only and not state.is_visible(*point)):
                if carrying_surface(state,*point) and state._table_placement_protected(*point):
                    continue
            return ThrowTrace(point,tuple(path[:index+1]),obstructed,tuple(sorted(uncertain)))
        return ThrowTrace(origin,(),obstructed,tuple(sorted(uncertain)))
    for point in flight_path(origin,(tx,ty)):
        x,y=point; px,py=last
        if x!=px and y!=py:
            a=blocked((x,py)); b=blocked((px,y))
            if a is True and b is True:
                return finish(True)
        if blocked(point) is True:
            return finish(True)
        path.append(point); last=point
    return finish(False)


def _directional_walk(state: Any, dx: int, dy: int, max_range: int, *, known_only=False) -> tuple[int, int]:
    return trace_throw(state,state.player.x+dx*max(0,int(max_range)),
                       state.player.y+dy*max(0,int(max_range)),known_only=known_only).landing


def directional_landing(state: Any, dx: int, dy: int, max_range: int | None = None,
                        *, known_only: bool=False) -> tuple[int, int]:
    """方向投掷的落点：从玩家出发沿 (dx,dy) 走到撞墙/出界/距离用尽。

    台面是「扔得过去、也落得上去」的承载面，不当作高墙截断。
    §13 逆风幕：穿过风幕的投掷体提前 2 格落地（从最大射程里直接扣除）。
    同一投掷体只扣一次，减程后不再重新触发风幕。
    """
    if max_range is None:
        max_range = throw_range(state)
    x, y = _directional_walk(state, dx, dy, max_range,known_only=known_only)
    if max_range > 0:
        from .construct_environments import screen_cells
        cells = screen_cells(state)
        if cells and any(point in cells for point in flight_path(
                (state.player.x, state.player.y), (x, y))):
            x, y = _directional_walk(state, dx, dy, max(0, max_range - 2),known_only=known_only)
    return x, y


def is_valid_target(state: Any, x: int, y: int, *, max_range: int | None=None,
                    require_visible: bool=True) -> tuple[bool, str]:
    """瞄准投掷的目标校验。返回 (是否有效, 拒绝原因)。

    有效目标 = 视野内、范围内、能落脚的格子（空地或台面承载；允许有生物——
    火瓶砸中异象、雷管在异象脚下炸开都是合法战术）。路径可越过低台面，
    但已确认的实墙与封闭斜角不能穿过；未知段只在实际出手后结算碰撞。
    """
    if max_range is None: max_range = throw_range(state)
    if max(abs(x - state.player.x), abs(y - state.player.y)) > max_range:
        return False, tr("太远了，扔不到（最远 {n} 格）。", n=max_range)
    if not (0 <= x < state.width and 0 <= y < state.height):
        return False, tr("那里没有落脚点。")
    if require_visible and not state.is_visible(x, y):
        return False, tr("看不见那里，落点无从确认。")
    if state.cell(x, y).solid and not carrying_surface(state, x, y):
        return False, tr("不能扔进坚实聚合物里。")
    if carrying_surface(state,x,y) and state._table_placement_protected(x,y):
        return False,tr('这块台面被机关或任务占用，不能往上放东西。')
    if trace_throw(state,x,y,known_only=True).blocked:
        return False,tr('投掷路径被墙挡住了。')
    from .construct_environments import screen_cells
    screen = screen_cells(state)
    if screen and any(point in screen for point in flight_path(
            (state.player.x, state.player.y), (x, y))):
        trimmed = max(0, max_range - 2)
        if max(abs(x - state.player.x), abs(y - state.player.y)) > trimmed:
            return False, tr("逆风幕削弱了这次投掷（最远 {n} 格）。", n=trimmed)
    return True, ""


@animate_landing
def resolve_landing(state: Any, item: Any, x: int, y: int) -> tuple[str, dict[str, Any]]:
    """落点结算：按物品效果在 (x, y) 引爆/引火/落地。

    返回 (事件记录消息, 附加 data)。调用方负责消耗物品与时间。
    """
    if item.definition_id == 'hospital.sealed_ampoule':
        return state.resolve_hospital_ampoule(item, x, y)
    boost = state._effect_power("throw_master")  # 投石索：投掷爆破/引火威力 +1/级
    # 落点就是脚下时是「原地释放」，消息不能说还在远处——镁光火柴等条目把
    # 原地点燃当作正式副动作，玩家选的正是自己站的这一格。
    here = (x, y) == (state.player.x, state.player.y)
    if item.effect == "explosion":
        state._kill_full_reward = True  # 玩家道具爆炸：崩解全额
        radius = item.explosion_radius + state._effect_power("blast_radius")
        state._explode(x, y, max(1, radius), (item.power or 1) + boost, from_player=True)
        if here:
            return tr("{item}在脚下轰然炸开。", item=tr(item.name)), {}
        return tr("{item}在远处轰然炸开。", item=tr(item.name)), {}
    if item.effect == "sound_lure":
        # 蜂鸣诱饵：落地即响，半径内异象循声追踪（发声点=落点）。
        state._sound_pulse(x, y, 8, by_player=True, full_alert=True,
                           category="lure", source=tr(item.name))
        # 2026-10-22（P3 第二轮）：铁皮虫不是只叫一声——落地那一拍算第 0 回合，
        # 第 3、6 回合各再响一次，把「引开」从一次性动作变成一段可用的窗口。
        # 登记成延时声源，由 `_tick_delayed_sounds` 走同一条真实声路重放。
        schedule = getattr(state, "delayed_sounds", None)
        if schedule is not None:
            for offset in (3, 6):
                schedule.append({"x": x, "y": y, "due": int(state.time) + offset,
                                 "radius": 8, "source": tr(item.name)})
        return tr("{item}嗡嗡作响——半层梦的注意力都被它拽了过去。", item=tr(item.name)), {}
    if item.effect == "smoke_cloud":
        # 烟量按物品配置：`power` 就是中心份量（普通罐 40、双联 80），四邻按
        # 3/8 比例跟随（15/30）——「双联」必须在落点上真的翻倍。
        center = item.power or 40
        halo = center * 3 // 8
        for tx, ty, amount in ((x, y, center), (x + 1, y, halo), (x - 1, y, halo),
                               (x, y + 1, halo), (x, y - 1, halo)):
            for gx, gy, gas in release_targets(state, tx, ty, amount):
                state._add_gas(state.cell(gx, gy), "黑烟", gas)
        return tr("罐头炸开，浓烟糊满了梦。"), {}
    if item.effect == "tar_burst":
        # 2026-10-22（P3 战术分工）：焦油弹不再只是「更强一点的燃烧瓶」。
        # 十字燃油总量 36→60，分 3 批、每批 20 单位淌出来：落地先铺一层，
        # 第 1、2 回合各再淌一层（`state.delayed_fuel`）。三批之后每格约 12 单位，
        # 火比燃烧瓶的「中心 12／四邻 6」更匀也更久。
        # `liquid_min=3`：焦油够黏，四邻每格 3 单位也挂得住火；燃烧瓶仍是 5。
        from ..materials import floor_fireproof
        strength = (item.power or 5) + state._effect_power("fire_affinity") + boost
        waves = tar_wave_cells(state, x, y)
        pour_tar(state, waves)
        ignited = 0
        burning = []
        for ty in range(y - 1, y + 2):
            for tx in range(x - 1, x + 2):
                if not (0 <= tx < state.width and 0 <= ty < state.height):
                    continue
                if state._ignite_cell(tx, ty, strength, by_player=True, liquid_min=3):
                    ignited += 1
                    burning.append((tx, ty))
        state._emit_combat_fx("fire", (x, y), burning)
        schedule = getattr(state, "delayed_fuel", None)
        if schedule is not None:
            for offset in (1, 2):
                schedule.append({"cells": waves, "due": int(state.time) + offset})
        if here:
            return tr("{item}在脚下碎开，焦油一层层淌出来（点燃 {n} 格）。",
                      item=tr(item.name), n=ignited), {}
        return tr("{item}在远处碎开，焦油一层层淌出来（点燃 {n} 格）。",
                  item=tr(item.name), n=ignited), {}
    if item.effect == "fireburst":
        from ..materials import floor_fireproof
        strength = (item.power or 4) + state._effect_power("fire_affinity") + boost
        ignited = 0
        burning = []
        for ty in range(y - 1, y + 2):
            for tx in range(x - 1, x + 2):
                if not (0 <= tx < state.width and 0 <= ty < state.height):
                    continue
                cell = state.cell(tx, ty)
                # 空地留下有限燃油，水域/防火层不被油瓶覆盖；五格十字控制通路。
                # 中心若是台面，那份燃油摊给四邻而不是消失。
                if abs(tx - x) + abs(ty - y) <= 1:
                    for lx, ly, fuel in release_targets(state, tx, ty,
                                                        12 if (tx, ty) == (x, y) else 6):
                        lcell = state.cell(lx, ly)
                        if not floor_fireproof(lcell) and lcell.liquid == 0:
                            state._add_liquid(lcell, "燃油", fuel)
                if state._ignite_cell(tx, ty, strength, by_player=True, liquid_min=5):
                    ignited += 1
                    burning.append((tx, ty))
        state._emit_combat_fx("fire", (x, y), burning)
        if here:
            return tr("{item}在脚下碎开，火焰四溅（点燃 {n} 格）。", item=tr(item.name), n=ignited), {}
        return tr("{item}在远处碎开，火焰四溅（点燃 {n} 格）。", item=tr(item.name), n=ignited), {}
    if item.effect == "spark_rays":
        # 2026-10-22（P3 战术分工）：烟花束不再与燃烧瓶共用同一个 3×3 火场＋铺油。
        # 改为落点向八个方向各抛一束火星，最远 3 格，遇**墙**即止；
        # 不凭空铺油，只点燃沿途本来就可燃的材料。
        strength = (item.power or 6) + state._effect_power("fire_affinity") + boost
        cells: list[tuple[int, int]] = [(x, y)]
        for dx, dy in ((1, 0), (1, 1), (0, 1), (-1, 1),
                       (-1, 0), (-1, -1), (0, -1), (1, -1)):
            for step in range(1, 4):
                tx, ty = x + dx * step, y + dy * step
                if not (0 <= tx < state.width and 0 <= ty < state.height):
                    break
                if state.cell(tx, ty).solid:
                    break
                cells.append((tx, ty))
        ignited = 0
        lit: list[tuple[int, int]] = []
        for tx, ty in cells:
            if state._ignite_cell(tx, ty, strength, by_player=True):
                ignited += 1
                lit.append((tx, ty))
        state._emit_combat_fx("fire", (x, y), lit)
        if here:
            return tr("{item}在脚下炸成一圈火星（点燃 {n} 格）。", item=tr(item.name), n=ignited), {}
        return tr("{item}在远处炸成一圈火星（点燃 {n} 格）。", item=tr(item.name), n=ignited), {}
    if item.effect == "ignite_burst":
        strength = (item.power or 2) + state._effect_power("fire_affinity")
        ignited = 0
        for tx, ty in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if state._ignite_cell(tx, ty, strength, by_player=True):
                ignited += 1
        if here:
            return tr("{item}在脚下迸出火星（点燃 {n} 格）。", item=tr(item.name), n=ignited), {}
        return tr("{item}在远处迸出火星（点燃 {n} 格）。", item=tr(item.name), n=ignited), {}
    if item.effect == "winter_sample":
        # 冬天的样本（2026-10-22 A2 P4）：薄壁瓶碎开，中心 8、四邻各 4 单位
        # 液氮；相变照既有冻结规则走，容不下的留在破损容器里（不放出去）。
        from . import item_devices
        message, extra = item_devices.winter_sample_landing(state, x, y, item.power or 24)
        return message, extra
    if item.effect == "storm_accumulator":
        # 未寄出的雷暴（2026-10-22 A2 P5）：落地后分四回合倒出电荷并放一次电。
        from . import item_devices
        message, extra = item_devices.storm_accumulator_landing(state, x, y)
        return message, extra
    if item.effect == "bottled_sunrise":
        # 瓶装天亮（2026-10-22 A2 P5）：两回合引信后放油点火。
        from . import item_devices
        message, extra = item_devices.bottled_sunrise_landing(state, x, y)
        return message, extra
    from .entities import WorldItem

    surface = state.cell(x, y).wall_kind if carrying_surface(state, x, y) else ""
    state.world_items.append(WorldItem(item, x, y, surface=surface))
    return tr("投掷了 {item}。", item=tr(item.name)), {
        'landed_item_id': item.instance_id, 'surface': surface}


# ---------------------------------------------------------------------------
# 冰面滑行的只读模拟（供自动寻路的「可停留」判定，避免点击冰面深处时
# 玩家被反复弹回——滑行越过目标后任何回头路都会再次滑走，形成死循环）
# ---------------------------------------------------------------------------


def _is_ice(state: Any, x: int, y: int) -> bool:
    from ..materials import floor_effect_for

    return floor_effect_for(state.cell(x, y)).slide


def slide_landing(state: Any, entry_x: int, entry_y: int, dx: int, dy: int) -> tuple[int, int]:
    """只读模拟：从 entry 走一步踏上 (entry+d)，沿 d 滑行后的停点。

    与 GameState._slide_on_ice 同一口径：脚下是冰面就沿方向滑，
    撞墙/固体/实体/离开冰面即停。不修改任何状态。
    """
    x, y = entry_x + dx, entry_y + dy
    while 0 <= x < state.width and 0 <= y < state.height and _is_ice(state, x, y):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < state.width and 0 <= ny < state.height):
            break
        if state.cell(nx, ny).solid or state.entity_at(nx, ny) is not None or not _is_ice(state, nx, ny):
            break
        x, y = nx, ny
    return x, y


def ice_stoppable(state: Any, x: int, y: int) -> bool:
    """目标冰面格是否「可停留」：存在某个进入方向，滑行停点恰为该格。

    只有冰区边缘（沿该方向下一格非冰/被挡）才停得住；冰面腹地的格子
    无论从哪边进入都会滑过头——对自动寻路而言即「不可停留目标」。
    """
    if not _is_ice(state, x, y):
        return True  # 非冰面格不存在滑行问题
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        px, py = x - dx, y - dy
        if not (0 <= px < state.width and 0 <= py < state.height):
            continue
        if state.cell(px, py).solid or state.entity_at(px, py) is not None:
            continue
        if slide_landing(state, px, py, dx, dy) == (x, y):
            return True
    return False
