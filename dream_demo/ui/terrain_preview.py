"""§15.6 操作预览：按下之前先把「实际会改哪几格、改完是什么高低」摊在地图上。

预览与结算共用两条口径：作用区取自 construct_environments 的那几个纯函数（隆起／
陷落真的改哪些格、液体类构想真的落在哪一格），高低与流向取自 ui.elevation 的读数
（先比地势档、再比液面）。于是「预览说抬不动」与「按下真的不动」是同一件事，
「预览说会往东摊」用的就是材料模拟那条比较。

全程只读：不扣想象力、不进冷却、不推进时间、不写任何格子。唯一沾到随机数的地方
是 `_mix_liquids` 里的不稳定分支，它自带定值种子，不摸全局 random。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ..core import ability_targeting, construct_environments
from ..core.content import ABILITY_DEFINITIONS
from ..core.materials_sim import _UnstableExplosionResult
from ..i18n import tr
from .elevation import (NEIGHBOURS, LocalView, elevation_bucket, flow_line,
                        known_elevation, liquid_surface)

# 图上标记：字形只给「会被改变、但结果读不出」的两类格子，其余靠底色——
# 与目标辅助路径（黄底）、观察光标（白 ?）的既有分工一致：区域＝底色，单点＝字形。
MARKS = {
    "raise": ("↑", "#d0a95c"),
    "sink": ("↓", "#6ba3c9"),
    "fracture": ("▨", "#c98a5b"),
    "liquid_add": ("+", "#7fd0e8"),
    "liquid_clear": ("−", "#c2a3ff"),
    "protected": ("⊘", "#8f9aa8"),
    "unknown": ("…", "#5c6470"),
    # §12 H3：植物、控场与地形产物。
    "plant_tall": ("♣", "#5f9e5a"),
    "plant_low": ("·", "#7fbf6a"),
    "push": ("»", "#e0a45e"),
    "slow": ("≈", "#9db7d8"),
    "shock": ("ϟ", "#8fd7e8"),
    "rubble": ("▚", "#8a6f52"),
    "paper": ("▤", "#c9b06a"),
}
# 接触边界：字符后端沿用地势层的做法（等高边界＝一条底色带），图像后端改画朝向区外
# 的那条边（等高线在图像层本来就是线）。
BOUNDARY_COLOR = "#241f33"
MAX_FLOW_LINES = 3

PREVIEWABLE = (frozenset(construct_environments.ELEVATION_OPS)
               | frozenset(construct_environments.LIQUID_ADD_OPS)
               | frozenset(construct_environments.LIQUID_CLEAR_OPS)
               | frozenset(construct_environments.H3_AREA_OPS)
               | frozenset(construct_environments.FAULT_RING_OPS))


@dataclass(frozen=True)
class TerrainPreview:
    """一次预览的结果。tints／marks 的键是**地图绝对坐标**，由 MapView 换成视口位置。"""

    title: str
    center: tuple[int, int]
    tints: dict[tuple[int, int], str]
    marks: dict[tuple[int, int], tuple[str, str]]
    boundary: tuple[tuple[int, int], ...]
    lines: tuple[str, ...]


class _Projected:
    """局部视角＋假设改动：`flow_line`／`liquid_surface` 读到的就是「改完之后」。

    只实现一层 `cell()`，未知格返回 None、固体不可穿这些判断全部留给 elevation.py
    里那份与悬浮／格子详情共用的实现，预览不另写一套。
    """

    def __init__(self, view: LocalView, changes: dict[tuple[int, int], dict[str, Any]]):
        self._view = view
        self._changes = changes

    def cell(self, x: int, y: int):
        cell = self._view.cell(x, y)
        change = self._changes.get((int(x), int(y)))
        return replace(cell, **change) if (cell is not None and change) else cell


def _pos(x: int, y: int) -> str:
    return f"{x},{y}"


def _name(ability_id: str) -> str:
    return tr(ABILITY_DEFINITIONS.get(ability_id, {}).get("name", ability_id))


def _ring(state, area) -> tuple[tuple[int, int], ...]:
    """作用区往外一格的邻圈；越出棋盘的格直接丢。"""
    cells = {(x + dx, y + dy) for (x, y) in area for dx, dy, _label in NEIGHBOURS
             if state.inside_board(x + dx, y + dy) and (x + dx, y + dy) not in area}
    return tuple(sorted(cells))


def _flow_lines(view, projected, positions) -> list[str]:
    """带液格改完之后的流向预测；只列前 MAX_FLOW_LINES 格，余量如实说明。"""
    wet = [(pos, view.cell(*pos)) for pos in sorted(positions)]
    wet = [(pos, cell) for pos, cell in wet if cell is not None and cell.liquid]
    lines = [tr("{kind}（{pos}）：{flow}", kind=tr(cell.liquid[0]), pos=_pos(*pos),
                flow=flow_line(projected, *pos)) for pos, cell in wet[:MAX_FLOW_LINES]]
    if len(wet) > MAX_FLOW_LINES:
        lines.append(tr("另有 {n} 格带液，未逐格预测流向", n=len(wet) - MAX_FLOW_LINES))
    if wet:
        lines.append(tr("“较低”不等于一定马上流入：液量、实际液面、墙体、地板流速与每拍节奏都会改变结果。"))
    return lines


def _mix_projection(state, view, pos, additions):
    """倒入之后的本格液体：与 `container_pour` 一样**逐种**走 `_mix_liquids`。

    一次合并与逐次倒入只在「混合不稳定」这类分支上会分岔；预览既然要说「倒完剩下
    什么」，就得按倒出的顺序算。
    """
    cell = view.cell(*pos)
    if cell is None or cell.status not in ("visible", "developed"):
        return [tr("这一格在视野外，只标出会被改变的位置。")], None
    lines: list[str] = []
    running_kind, running_amount = cell.liquid if cell.liquid else ("", 0)
    if cell.liquid:
        lines.append(tr("本格现有 {kind} ×{amount}", kind=tr(running_kind),
                        amount=running_amount))
    projected = None
    for kind, amount in additions.items():
        lines.append(tr("倒入 {kind} ×{amount}", kind=tr(kind), amount=amount))
        totals: dict[str, int] = {}
        if running_kind and running_amount > 0:
            totals[running_kind] = running_amount
        if kind and amount > 0:
            totals[kind] = totals.get(kind, 0) + amount
        result = state._mix_liquids({key: value for key, value in totals.items() if value > 0})
        if isinstance(result, _UnstableExplosionResult):
            lines.append(tr("混合不稳定：这一格不会留下一摊液体。"))
            return lines, None
        running_kind, running_amount = str(result[0]), int(result[1])
        projected = (running_kind, running_amount) if running_amount > 0 else None
    if projected:
        lines.append(tr("预计 {kind} ×{amount}", kind=tr(projected[0]), amount=projected[1]))
    return lines, projected


def _footing_line(state, view, area, changes, step: int = 0) -> str:
    """§15.6 要求预览说明自身所在位置：脚下那格跟着一起变吗。"""
    pos = (state.player.x, state.player.y)
    if pos not in area:
        return tr("脚下 {pos} 不在作用区", pos=_pos(*pos))
    if not step:
        return tr("脚下 {pos} 就在作用区里", pos=_pos(*pos))
    if pos in changes:
        tier = known_elevation(view.cell(*pos))
        return tr("脚下 {pos} 一起改变：地势 {old}→{new}", pos=_pos(*pos), old=tier, new=tier + step)
    if known_elevation(view.cell(*pos)) is None:
        return tr("脚下 {pos} 也在作用区，但这一格地势读不出", pos=_pos(*pos))
    return tr("脚下 {pos} 被钉住，不会改变", pos=_pos(*pos))


def _elevation_preview(state, ability_id: str) -> TerrainPreview:
    step = construct_environments.ELEVATION_OPS[ability_id]
    center = construct_environments.visible_target(state)
    legal, blocked = construct_environments.elevation_area(state, center)
    view = LocalView(state)
    tints: dict[tuple[int, int], str] = {}
    marks: dict[tuple[int, int], tuple[str, str]] = {}
    changes: dict[tuple[int, int], dict[str, Any]] = {}
    counts: dict[str, int] = {}
    unknown = 0
    for pos in legal:
        tier = known_elevation(view.cell(*pos))
        if tier is None:
            unknown += 1
            tints[pos] = MARKS["unknown"][1]
            marks[pos] = MARKS["unknown"]
            continue
        new_tier = tier + step
        changes[pos] = {"elevation": new_tier}
        tints[pos] = elevation_bucket(new_tier)[1]
        key = f"{tier}→{new_tier}"
        counts[key] = counts.get(key, 0) + 1
    for pos in blocked:
        tints[pos] = MARKS["protected"][1]
        marks[pos] = MARKS["protected"]
    if center in changes:
        marks[center] = MARKS["raise" if step > 0 else "sink"]
    area = set(legal) | set(blocked)
    title = tr("预览 · {name}", name=_name(ability_id))
    lines = [title, tr("作用区 {n} 格 · 中心 {pos}", n=len(legal), pos=_pos(*center))]
    if counts:
        lines.append(tr("地势 {changes}",
                        changes=" · ".join(f"{key} ×{value}" for key, value in sorted(counts.items()))))
    if blocked:
        lines.append(tr("{n} 格被钉住，不会改变", n=len(blocked)))
    if not legal:
        # 整片被钉住时逐字给出结算那一句：预览里写着什么，按下之后气泡里就是什么。
        lines.append(tr(construct_environments.REFUSE_PINNED))
    if unknown:
        lines.append(tr("{n} 格地势未知，改了也读不出档位", n=unknown))
    lines.append(_footing_line(state, view, area, changes, step))
    lines.extend(_flow_lines(view, _Projected(view, changes), area))
    return TerrainPreview(title, center, tints, marks, _ring(state, area), tuple(lines))


def _fault_ring_preview(state) -> TerrainPreview:
    """裂地环：作用环与结算共用 `construct_environments.ring_cells`。

    墙体只报「受震开裂」这条规则，不偷读隐藏完整度；未知格仍着色（效果确实
    进入那里）但只标 `…`。环心是玩家自己，画一圈、不改中心格。
    """
    center = (state.player.x, state.player.y)
    area = set(construct_environments.ring_cells(
        state, construct_environments.FAULT_RING_RADIUS, center))
    view = LocalView(state)
    tints: dict[tuple[int, int], str] = {}
    marks: dict[tuple[int, int], tuple[str, str]] = {}
    changes: dict[tuple[int, int], dict[str, Any]] = {}
    counts: dict[str, int] = {}
    walls = pinned = unknown = 0
    for pos in sorted(area):
        if construct_environments.protected_geometry(state, *pos):
            pinned += 1
            tints[pos] = MARKS["protected"][1]
            marks[pos] = MARKS["protected"]
            continue
        cell = view.cell(*pos)
        terrain = getattr(cell, "terrain", None)
        if cell is None or cell.status == "unknown" or terrain is None:
            unknown += 1
            tints[pos] = MARKS["unknown"][1]
            marks[pos] = MARKS["unknown"]
            continue
        if terrain.solid:
            walls += 1
            tints[pos] = MARKS["fracture"][1]
            marks[pos] = MARKS["fracture"]
            continue
        tier = known_elevation(cell)
        if tier is None:
            unknown += 1
            tints[pos] = MARKS["unknown"][1]
            marks[pos] = MARKS["unknown"]
            continue
        new_tier = tier - 1
        changes[pos] = {"elevation": new_tier}
        tints[pos] = elevation_bucket(new_tier)[1]
        key = f"{tier}→{new_tier}"
        counts[key] = counts.get(key, 0) + 1
    title = tr("预览 · {name}", name=_name("combat.fault_ring"))
    lines = [title, tr("作用环 {n} 格 · 中心 {pos}", n=len(area), pos=_pos(*center))]
    if counts:
        lines.append(tr("地势 {changes}",
                        changes=" · ".join(f"{key} ×{value}"
                                           for key, value in sorted(counts.items()))))
    if walls:
        lines.append(tr("{n} 面墙受震开裂（完整度 −25，归零即塌）", n=walls))
    if pinned:
        lines.append(tr("{n} 格被钉住，不会改变", n=pinned))
    if unknown:
        lines.append(tr("{n} 格在未知处，只标出会被改变的位置", n=unknown))
    lines.append(tr("脚下 {pos} 是环心：这一圈不会直接伤到你", pos=_pos(*center)))
    lines.append(tr("环上的失控意识受 2 点创伤，并被径向推开 1 格。"))
    lines.extend(_flow_lines(view, _Projected(view, changes), area))
    return TerrainPreview(title, center, tints, marks, _ring(state, area), tuple(lines))


def _liquid_add_preview(state, ability_id: str) -> TerrainPreview:
    kind, _amount = construct_environments.LIQUID_ADD_OPS[ability_id]
    center = ability_targeting.default_target(state, ability_id)
    view = LocalView(state)
    title = tr("预览 · {name}", name=_name(ability_id))
    refusal = tr('这个构想没有合法落点——本次不消耗。')
    if center is None:
        return TerrainPreview(title, (state.player.x, state.player.y), {}, {}, (),
                              (title, refusal,
                               _footing_line(state, view, set(), {})))
    plan = construct_environments.condense_plan(state, center)
    tints: dict[tuple[int, int], str] = {}
    marks: dict[tuple[int, int], tuple[str, str]] = {}
    changes: dict[tuple[int, int], dict[str, Any]] = {}
    lines = [tr("目标 {pos}", pos=_pos(*center))]
    total = neighbors = 0
    for pos, amount in plan:
        total += amount
        tints[pos] = MARKS["liquid_add"][1]
        marks[pos] = MARKS["liquid_add"]
        if pos == center:
            detail, projected = _mix_projection(state, view, pos, {kind: amount})
            lines.extend(detail)
        else:
            neighbors += amount
            _detail, projected = _mix_projection(state, view, pos, {kind: amount})
        if projected:
            changes[pos] = {"liquid": projected}
    lines.append(tr("凝出 {kind} ×{n}（中心 20、四邻各 10，整发上限 60；四邻另计 {m} 点）。",
                    kind=tr(kind), n=total, m=neighbors))
    area = set(plan_pos for plan_pos, _ in plan)
    lines.append(_footing_line(state, view, area, changes))
    lines.extend(_flow_lines(view, _Projected(view, changes), set(changes)))
    return TerrainPreview(title, center, tints, marks, _ring(state, area), tuple(lines))


def _pour_preview(state, contents: dict[str, int]) -> TerrainPreview:
    """倒出落在**自己脚下**那格（与 container_pour 同一落点口径）。"""
    center = (state.player.x, state.player.y)
    view = LocalView(state)
    title = tr("预览 · {name}", name=tr("倒出（倒在本格并就地反应）"))
    additions = {kind: int(amount) for kind, amount in contents.items() if int(amount) > 0}
    lines, projected = _mix_projection(state, view, center, additions)
    changes: dict[tuple[int, int], dict[str, Any]] = {}
    if projected:
        changes[center] = {"liquid": projected}
    body = [tr("本格 {pos}（倒在本格）", pos=_pos(*center))] + lines
    body.append(_footing_line(state, view, {center}, changes))
    body.extend(_flow_lines(view, _Projected(view, changes), {center}))
    return TerrainPreview(title, center, {center: MARKS["liquid_add"][1]},
                          {center: MARKS["liquid_add"]}, _ring(state, {center}),
                          tuple([title] + body))


def _liquid_clear_preview(state, ability_id: str) -> TerrainPreview:
    """液体清理类的预览：落点只认悬停/面朝，绝不改投最近的一摊液体。"""
    view = LocalView(state)
    title = tr("预览 · {name}", name=_name(ability_id))
    center = ability_targeting.default_target(state, ability_id)
    if center is None:
        # 落点不成立时结算在进入分支之前就拒绝了，预览必须逐字复用那一句。
        return TerrainPreview(title, (state.player.x, state.player.y), {}, {}, (),
                              (title, tr('这个构想没有合法落点——本次不消耗。'),
                               _footing_line(state, view, set(), {})))
    changes: dict[tuple[int, int], dict[str, Any]] = {}
    area: set[tuple[int, int]] = set()
    lines = [tr("目标 {pos}", pos=_pos(*center))]
    if ability_id == "draw_liquid":
        kind, plan = construct_environments.draw_liquid_plan(state, center)
        if not plan:
            return TerrainPreview(title, center, {}, {}, (),
                                  (title, tr("这里没有可以汲取的液体——本次不消耗。")))
        for pos, take in plan:
            cell = state.cell(*pos)
            left = int(cell.liquid) - take
            changes[pos] = {"liquid": (kind, left) if left > 0 else None}
            area.add(pos)
        lines.append(tr("抽干 {n} 点液态记忆（{cells} 格），想象力 +2。",
                        n=sum(take for _pos, take in plan), cells=len(plan)))
    elif ability_id == "ice_bridge":
        kind, plan = construct_environments.ice_bridge_plan(state, center, state.facing)
        if not plan:
            return TerrainPreview(title, center, {}, {}, (),
                                  (title, tr("沿这个方向没有可以冻结的液体——本次不消耗。")))
        for pos, take in plan:
            cell = state.cell(*pos)
            left = int(cell.liquid) - take
            changes[pos] = {"liquid": (kind, left) if left > 0 else None}
            area.add(pos)
        lines.append(tr("沿方向冻出 {n} 格冰桥，转入冻层 {amount} 点。",
                        n=len(plan), amount=sum(take for _pos, take in plan)))
        lines.append(tr("冰面湿滑：踏上后会沿同一方向滑到障碍前，留好落脚格。"))
    else:
        kind, gas, _ratio, plan = construct_environments.transpire_plan(state, center)
        if not gas:
            return TerrainPreview(title, center, {}, {}, (),
                                  (title, tr("这种液体没有可以蒸腾的产物。")))
        for pos, take, _gas_amount in plan:
            cell = state.cell(*pos)
            left = int(cell.liquid) - take
            changes[pos] = {"liquid": (kind, left) if left > 0 else None}
            area.add(pos)
        converted = sum(gas_amount for _pos, _take, gas_amount in plan)
        lines.append(tr("原地蒸腾成 {gas} ×{amount}（首拍，持续 {turns} 回合）。",
                        gas=tr(gas), amount=converted,
                        turns=construct_environments.TRANSPIRE_TURNS))
    if not area:
        # 首拍没有可转换的液体（例如气室已满）：作用和拒绝分开说清楚。
        lines.append(tr("首拍没有可转换的液体。"))
    tints = {pos: MARKS["liquid_clear"][1] for pos in area}
    marks = {pos: MARKS["liquid_clear"] for pos in area}
    lines.append(_footing_line(state, view, area, changes))
    lines.extend(_flow_lines(view, _Projected(view, changes), area))
    return TerrainPreview(title, center, tints, marks, _ring(state, area),
                          tuple([title] + lines))


def _h3_preview(state, ability_id: str) -> TerrainPreview:
    """H3 植物／控场／地形产物：作用区与结算共用 construct_environments 的计划。"""
    view = LocalView(state)
    title = tr("预览 · {name}", name=_name(ability_id))
    center = ability_targeting.default_target(state, ability_id)
    refusal = tr('这个构想没有合法落点——本次不消耗。')
    if center is None:
        return TerrainPreview(title, (state.player.x, state.player.y), {}, {}, (),
                              (title, refusal,
                               _footing_line(state, view, set(), {})))
    tints: dict[tuple[int, int], str] = {}
    marks: dict[tuple[int, int], tuple[str, str]] = {}
    area: set[tuple[int, int]] = set()
    lines = [tr("目标 {pos}", pos=_pos(*center))]

    if ability_id == 'sow_green':
        plan = construct_environments.sow_green_plan(state, center)
        codes = {(x, y): code for x, y, code in plan}
        tall = sum(1 for code in codes.values() if code == 2)
        low = len(codes) - tall
        for pos, code in codes.items():
            area.add(pos)
            tints[pos] = MARKS["plant_tall" if code == 2 else "plant_low"][1]
        if plan:
            lines.append(tr("播下 {n} 格植物：高丛 {tall}、低草 {low}；内圈高丛挡视线，踩踏会变矮。",
                            n=len(plan), tall=tall, low=low))
        else:
            lines.append(tr("这里种不下任何东西。"))
        if center in codes:
            marks[center] = MARKS["plant_tall" if codes[center] == 2 else "plant_low"]
        lines.append(_footing_line(state, view, area, {}))
    elif ability_id == 'repulse':
        plan = construct_environments.repulse_plan(state, center)
        radius = {(x, y)
                  for y in range(center[1] - 2, center[1] + 3)
                  for x in range(center[0] - 2, center[0] + 3)
                  if state.inside_board(x, y)}
        area = radius
        for pos in radius:
            tints[pos] = MARKS["push"][1]
        known = [(enemy, tx, ty) for enemy, tx, ty in plan
                 if state.is_visible(enemy.x, enemy.y)]
        for enemy, tx, ty in known:
            marks[(enemy.x, enemy.y)] = MARKS["push"]
            if (tx, ty) != (enemy.x, enemy.y):
                area.add((tx, ty))
                tints[(tx, ty)] = MARKS["push"][1]
                marks[(tx, ty)] = MARKS["push"]
        if known:
            lines.append(tr("半径 2 内可见的 {n} 个失控意识：各受 2 点创伤，并被径向推开最多 3 格。",
                            n=len(known)))
        else:
            lines.append(tr("半径 2 内没有可见的失控意识——按下仍会消耗。"))
        lines.append(tr("被钉住或前方受阻时只受创伤、不移动；不追加撞墙伤害。你本人不会被推开。"))
    elif ability_id == 'slow_wave':
        cells = construct_environments.slow_zone_cells(state, center)
        area = set(cells)
        for pos in area:
            tints[pos] = MARKS["slow"][1]
        marks[center] = MARKS["slow"]
        lines.append(tr("半径 4、持续 6 回合：区内所有生物移动耗时 +0.3。"))
        if (state.player.x, state.player.y) in area:
            lines.append(tr("你也在区内，移动同样变慢；离开即失效，多区不叠加。"))
        else:
            lines.append(tr("离开作用区即失效；多个时缓区不叠加。"))
    elif ability_id == 'static_arc':
        plan = construct_environments.static_arc_plan(state, center)
        if plan is None:
            return TerrainPreview(title, center, {}, {}, (),
                                  (title, tr("落点既不是异象也不是导电介质——本次不消耗。")))
        if plan[0] == 'enemy':
            enemy = plan[1]
            pos = (enemy.x, enemy.y)
            area = {pos}
            tints[pos] = MARKS["shock"][1]
            marks[pos] = MARKS["shock"]
            lines.append(tr("命中 {enemy}：3 点创伤、迟缓 2 回合。", enemy=tr(enemy.label)))
        else:
            zone = plan[1]
            known = {pos for pos in zone if state.is_visible(*pos)}
            area = known
            for pos in known:
                tints[pos] = MARKS["shock"][1]
            if center in known:
                marks[center] = MARKS["shock"]
            lines.append(tr("沿真实四邻导电区充能：已确认 {n} 格，电场持续 5 回合。",
                            n=len(known)))
            if len(known) < len(zone):
                lines.append(tr("连通区延伸到视野外，可能继续传播；预览只画出已确认部分。"))
            if (state.player.x, state.player.y) in zone:
                lines.append(tr("你在导电区内，同样会受影响；绝缘格会截断电流。"))
            else:
                lines.append(tr("自己与稳定意识同样危险；绝缘格会截断电流。"))
    elif ability_id == 'collapse':
        walls, debris = construct_environments.collapse_plan(
            state, center, state.facing)
        if not walls or not debris:
            return TerrainPreview(title, center, {}, {}, (),
                                  (title, tr("这里没有可坍塌的墙源或碎屑落点——本次不消耗。")))
        area = set(walls) | set(debris)
        for pos in walls:
            tints[pos] = MARKS["fracture"][1]
            marks[pos] = MARKS["fracture"]
        for pos in debris:
            tints[pos] = MARKS["rubble"][1]
            marks[pos] = MARKS["rubble"]
        lines.append(tr("破坏 {n} 面完整度 ≤40 的墙源，生成 {m} 格碎屑堆；任务设施与占用格受保护。",
                        n=len(walls), m=len(debris)))
        lines.append(_footing_line(state, view, area, {}))
    elif ability_id == 'conjure_wall':
        candidates = construct_environments.conjure_wall_plan(
            state, center, state.facing)
        if not candidates:
            return TerrainPreview(title, center, {}, {}, (),
                                  (title, tr("那几格腾不出空间来凝聚墙——本次不消耗。")))
        area = set(candidates)
        for pos in area:
            tints[pos] = MARKS["fracture"][1]
        if center in area:
            marks[center] = MARKS["fracture"]
        lines.append(tr("沿方向垂线凝聚 {n} 格臆造聚合墙：可推动、可破坏；占用与任务设施先检查。",
                        n=len(candidates)))
        lines.append(_footing_line(state, view, area, {}))
    else:  # ink_doodle
        plan = construct_environments.ink_doodle_plan(state, center)
        area = set(plan)
        for pos in area:
            tints[pos] = MARKS["paper"][1]
        if center in area:
            marks[center] = MARKS["paper"]
        if plan:
            lines.append(tr("把 {n} 格合法地面涂成书页地：不直接点火；任务设施、保护地板与占用格不改。",
                            n=len(plan)))
        else:
            lines.append(tr("这 5×5 里没有可涂的合法地面——按下仍会消耗。"))
        lines.append(_footing_line(state, view, area, {}))

    return TerrainPreview(title, center, tints, marks, _ring(state, area), tuple(lines))


def build(state, ability_id: str | None = None, *, contents: dict[str, int] | None = None):
    """把「现在选中的这一发」算成预览；与地形／液面无关的操作返回 None。"""
    if contents is not None:
        return _pour_preview(state, contents) if any(
            int(amount) > 0 for amount in contents.values()) else None
    if ability_id in construct_environments.FAULT_RING_OPS:
        return _fault_ring_preview(state)
    if ability_id in construct_environments.ELEVATION_OPS:
        return _elevation_preview(state, ability_id)
    if ability_id in construct_environments.LIQUID_ADD_OPS:
        return _liquid_add_preview(state, ability_id)
    if ability_id in construct_environments.LIQUID_CLEAR_OPS:
        return _liquid_clear_preview(state, ability_id)
    if ability_id in construct_environments.H3_AREA_OPS:
        return _h3_preview(state, ability_id)
    return None


class TerrainPreviewMixin:
    """宿主侧取数：现在选中的到底是哪一发，以及把结果同步给地图控件。

    提交结束就撤标记：`_invalidate_terrain_preview` 由结算点调用，标记只跟着
    「选中项 + 指点格」这份键存活，所以同一行落地后不会继续画着上一发的黄圈，
    而换选或移动鼠标会立刻按当前世界重画（新档位就是那一发已生效的证据）。
    """

    def _terrain_preview_source(self, state) -> tuple[str, object] | None:
        index = getattr(self, "container_index", None)
        if index is not None and 0 <= index < len(state.inventory):
            item = state.inventory[index]
            spec = state._container_spec(item)
            if spec and item.contents and spec.get("medium", "liquid") == "liquid":
                return ("pour", dict(item.contents))
        # 裂地环从面板进入瞄准后 panel_mode 变成 world；预览得跟着草稿存活，
        # 否则玩家按下 Enter 准备确认的那一步恰好看不到作用环。
        aim_id = getattr(self, "construct_aim_id", None)
        if aim_id in PREVIEWABLE:
            return ("ability", aim_id)
        if self.home_mode or self.panel_mode != "actions":
            return None
        key = self._panel_entry_key(self.panel_selection)
        if key is None or not key.startswith("ability:"):
            return None
        ability_id = key.split(":", 1)[1]
        return ("ability", ability_id) if ability_id in PREVIEWABLE else None

    def _terrain_preview_key(self, state, source) -> tuple:
        return (source[0],
                source[1] if source[0] == "ability" else None,
                getattr(state, "hover_target", None),
                getattr(self, "container_index", None))

    def _invalidate_terrain_preview(self) -> None:
        """那一发已经落地：撤掉临时标记，直到选中项或指点格变化才重新画。"""
        self._preview_suppressed = True

    def _terrain_preview_for(self, state) -> TerrainPreview | None:
        source = self._terrain_preview_source(state)
        if source is None:
            self._preview_suppressed = False
            self._preview_key = None
            return None
        key = self._terrain_preview_key(state, source)
        if getattr(self, "_preview_suppressed", False):
            if key == getattr(self, "_preview_key", None):
                return None
            self._preview_suppressed = False
        self._preview_key = key
        if source[0] == "pour":
            return build(state, contents=source[1])
        return build(state, ability_id=source[1])

    def _apply_terrain_preview(self, state, map_view) -> None:
        """必须在 `_hover_text` 之后调用：预览中心 = `visible_target(state)`，
        而 `state.hover_target` 正是悬浮读数顺手写下的——早一步就会差一帧。"""
        preview = self._terrain_preview_for(state)
        map_view.preview_tints = preview.tints if preview else None
        map_view.preview_marks = preview.marks if preview else None
        map_view.preview_boundary = preview.boundary if preview else ()
        map_view.update_interaction()
