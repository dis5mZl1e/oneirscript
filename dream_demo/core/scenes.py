"""场景锚点的地图落地（重构方案 §12.1／§10.2）。

:mod:`dream_demo.world.scenes` 只解释条件与命令，**不碰地图**：真正把院子放进
地图、把地面改成可燃／绝热、把锚点事件挂到地图角色上、以及换层回来时把地形
增量回放一遍，都在这个模块里。

三条硬约束：

* 每层至多 1 个主要互动场景，且**只在已经整片开放的矩形里落位**——不凿墙、
  不改固体，通路因此不可能被场景改造封死。
* 布局是生成期按种子推导的：远层快照被裁剪后按种子重建会算出同一个原点，
  设施状态与库存另存在 ``world_ledger.facilities`` 里，所以回来时看到的是
  同一台设施，而不是重新满血的复制体（§12.2）。
* 基准地形重铺之后才回放 ``terrain`` 增量：烧穿的地面属于事实，不能因为
  「这一层重新生成过」就自己长回可燃的纸。
"""

from __future__ import annotations

import random
from itertools import islice
from typing import Any

from ..data.scenes import SCENE_DEFINITIONS, scene_allowed
from ..i18n import tr
from ..materials import wall_def
from ..materials.floors import FLOOR_DEFINITIONS
from ..world import scenes as world_scenes
from .constants import Material
from .entities import ActionResult, WorldEvent, WorldItem

#: 每层出现主要互动场景的概率（§12.1「每层至多 1 个」——稀缺是设计的一部分）。
SCENE_SPAWN_CHANCE = 0.6
#: 配对场景找一对端点时最多检查多少个候选原点（封顶生成开销，不是玩法参数）。
PAIR_CANDIDATE_CAP = 400


def seed_scenes(state: Any, vault_info: "dict | None" = None) -> None:
    """投放或还原本层的主要互动场景，并挂上它的锚点事件。"""
    record = _layer_record(state)
    if record is None:
        record = _spawn(state, vault_info)
    else:
        # 被裁剪过的层按种子重建：基准地形要重新铺出来，锚点事件也要重新挂上。
        _apply_layout(state, record)
    replay_terrain(state)
    if record is not None:
        _bind_event(state, record)


# --------------------------------------------------------------- 落位与建造

def _spawn(state: Any, vault_info: "dict | None") -> Any:
    definition = _layer_choice(state)
    if definition is None:
        return None
    origins = _find_origins(state, definition, vault_info)
    if origins is None:
        return None
    record = world_scenes.install(state, definition,
                                  anchor_uid=f"{origins[0][0]},{origins[0][1]}")
    record.layout = world_scenes.absolute_layout(definition, *origins)
    _apply_layout(state, record)
    return record


def install_bound_scene(state: Any, definition_id: str, x: int, y: int) -> Any:
    """把一处**作者摆放**的场景（§8 S23 青灯入口）落到 vault 指定的锚点格。

    与 :func:`_spawn` 的区别只在「谁决定原点」：随机池场景要扫描整片开放矩形
    找落位，而绑定场景的坐标由 ``mapgen/vaults`` 的 ``event_anchor`` 给定，锚点键
    按相对 (0, 0) 直接压在那一格上。``ledger.facility`` 幂等，所以远层重建时这里
    只是把同一条记录、同一份布局重新挂回地图，不回满血也不重铸身份（§12.2）。
    """
    definition = SCENE_DEFINITIONS.get(definition_id)
    if definition is None:
        return None
    record = world_scenes.install(state, definition, anchor_uid=f"{x},{y}")
    record.layout = world_scenes.absolute_layout(definition, (x, y))
    _apply_layout(state, record)
    _bind_event(state, record)
    return record


def _find_origins(state: Any, definition: dict[str, Any],
                  vault_info: "dict | None") -> "tuple[Any, ...] | None":
    if "pair" not in definition:
        return next(((origin,) for origin in
                     _origin_candidates(state, definition, vault_info)), None)
    return _find_pair(state, definition, vault_info)


def _find_pair(state: Any, definition: dict[str, Any],
               vault_info: "dict | None") -> "tuple[Any, ...] | None":
    """配对场景要两个相隔 ``spread`` 的原点：每一端都单独走得通、点得着。

    端点候选按同一颗种子洗牌，所以第 ``index`` 个与它之后第一个够远的组合是确定的；
    候选数封顶，避免在小地图上为找一对折页把整层格子扫穿。
    """
    low, high = definition["pair"]["spread"]
    candidates = list(islice(_origin_candidates(state, definition, vault_info),
                             PAIR_CANDIDATE_CAP))
    for index, first in enumerate(candidates):
        for second in candidates[index + 1:]:
            if low <= abs(first[0] - second[0]) + abs(first[1] - second[1]) <= high:
                return (first, second)
    return None


def _layer_choice(state: Any) -> "dict[str, Any] | None":
    """本层用哪一个场景定义（由种子决定，同一 seed+depth 永远同一个）。"""
    candidates = [entry for entry in SCENE_DEFINITIONS.values()
                  if scene_allowed(entry, state.depth, state.realm_id)]
    if not candidates:
        return None
    rng = random.Random(state.seed * 101 + state.depth * 8191)
    if rng.random() >= SCENE_SPAWN_CHANCE:
        return None
    return candidates[rng.randrange(len(candidates))]


def _layer_record(state: Any) -> Any:
    key = state.layer_key()
    for entry in state.world_ledger.facilities.values():
        if entry.layer_key == key and entry.definition_id in SCENE_DEFINITIONS:
            return entry
    return None


def _protected_regions(state: Any, vault_info: "dict | None") -> list[tuple[int, int, int, int]]:
    regions = list((vault_info or {}).get("regions", ()) or ())
    regions.extend(board["region"] for board in state.circuit_boards if board.get("region"))
    return [(int(box[0]), int(box[1]), int(box[2]), int(box[3])) for box in regions]


def _reachable(state: Any) -> set[tuple[int, int]]:
    """从出生点做 4 连通洪水填充：场景必须落在玩家真能走到的地方。"""
    start = (state.player.x, state.player.y)
    seen = {start}
    queue = [start]
    for x, y in queue:
        for point in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            px, py = point
            if point in seen:
                continue
            if not (0 <= px < state.width and 0 <= py < state.height):
                continue
            cell = state.cell(px, py)
            if cell.solid and cell.wall_kind != "门":
                continue
            seen.add(point)
            queue.append(point)
    return seen


def _origin_candidates(state: Any, definition: dict[str, Any],
                       vault_info: "dict | None"):
    """可用的落位原点，按种子洗牌后依次给出：外框不压进保险区、不贴着出生点，
    功能格全部走得通、点得着。

    只要求**功能格**（锚点、边槽、作用区、旁路／低槽、排放区）是开阔地面，不
    要求整个外框空出来——墙可以穿过外框的装饰区，但火盆与术阵脚下的格子必须
    真能站、真能烧。这样既不用凿墙，也不会出现「面板说这里有阵、地图上是一堵
    墙」的错位（§17「真实目标/设施」）。
    """
    width, height = definition["footprint"]
    regions = _protected_regions(state, vault_info)
    blocked = {(entry.x, entry.y) for entry in state.world_items}
    blocked.update((entry.x, entry.y) for entry in state.events)
    blocked.update((entry.x, entry.y) for entry in state.enemies if entry.integrity > 0)
    accessible = _reachable(state)
    cells: list[list[Any]] = state.cells
    spots = [(x, y) for y in range(1, state.height - height - 1)
             for x in range(1, state.width - width - 1)]
    random.Random(state.seed * 7 + state.depth * 31337).shuffle(spots)
    for origin_x, origin_y in spots:
        if max(abs(origin_x + width // 2 - state.player.x),
               abs(origin_y + height // 2 - state.player.y)) <= 3:
            continue
        if any(a <= x <= c and b <= y <= d for a, b, c, d in regions
               for x in range(origin_x, origin_x + width)
               for y in range(origin_y, origin_y + height)):
            continue
        layout = world_scenes.relative_cells(definition, (origin_x, origin_y))
        layout_points = _layout_cells(layout)
        if not all(_usable_cell(state.cells, accessible, blocked, point)
                   for point in layout_points):
            continue
        if any(_wet_neighbor(state.cells, px, py) for px, py in layout_points):
            continue
        yield (origin_x, origin_y)


def _layout_cells(layout: dict[str, Any]) -> set[tuple[int, int]]:
    """布局里所有**功能格**（``origin`` 只是参考点，不算）。"""
    out: set[tuple[int, int]] = set()
    for name, value in layout.items():
        if name == "origin" or not value:
            continue
        if len(value) == 2 and all(isinstance(entry, int) for entry in value):
            out.add((int(value[0]), int(value[1])))
        else:
            out.update((int(px), int(py)) for px, py in value)
    return out


def _usable_cell(cells: list[list[Any]], accessible: set[tuple[int, int]],
                 blocked: set[tuple[int, int]], point: tuple[int, int]) -> bool:
    x, y = point
    if not (1 <= x < len(cells[0]) - 1 and 1 <= y < len(cells) - 1):
        return False
    if (x, y) in blocked or (x, y) not in accessible:
        return False
    cell = cells[y][x]
    if cell.liquid > 0 or cell.gas > 0:
        # 功能格压在天然液体/气体上，设施的材料口径会被打乱（潮汐盆「只认水」
        # 被杂液顶掉、火盆泡在酸里）——这类落位直接放弃（2026-10-11 修复）。
        return False
    return (not cell.solid and not cell.wall_kind and not cell.wire and not cell.plant)


def _wet_neighbor(cells: list[list[Any]], x: int, y: int) -> bool:
    """功能格的四邻里有液体或气体：紧贴液池的落位照样会被流动均摊污染。"""
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        cell = cells[ny][nx]
        if cell.liquid > 0 or cell.gas > 0:
            return True
    return False


def set_floor_variant(state: Any, x: int, y: int, variant: str,
                      fuel: int = 0, persist: bool = False) -> bool:
    """把一格开放地面改成指定变体。固体／墙体一律不动。

    ``persist`` 只给**运行中**的改变（装料命令）用：生成期的基准地形由种子
    重放，写进 ``terrain`` 反而会把「重新生成」和「玩家改过」两笔账混在一起。
    """
    definition = FLOOR_DEFINITIONS.get(variant)
    if definition is None:
        return False
    cell = state.cell(x, y)
    if cell.solid or cell.wall_kind:
        return False
    cell.aggregate_variant = definition.variant
    cell.floor_fuel = int(fuel) if definition.burns_to else 0
    if persist:
        state.world_ledger.mark_terrain(
            state.layer_key(), x, y,
            aggregate_variant=definition.variant, floor_fuel=cell.floor_fuel)
    return True


def seal_opening(state: Any, x: int, y: int) -> bool:
    """把一处开着的门洞落成实心挡板：材料参数取既有墙体定义，不写新的阻挡规则。

    与 ``_close_door`` 的区别只在「会不会被自动抬回去」：常开门由占位每拍刷新，
    挡板落下去是要留到玩家回来处理的，所以 ``wall_kind`` 保持为空，让
    :func:`dream_demo.core.doors._update_doors` 一眼跳过它。改动走地形增量，
    远层重建后看到的还是同一道封死的门（§12.2）。
    """
    cell = state.cell(x, y)
    if cell.solid or cell.wall_kind or cell.wire or cell.plant:
        return False
    definition = wall_def("")
    cell.solid = True
    cell.floor = Material.SOLID_AGGREGATE
    cell.height = definition.height
    cell.hardness = definition.hardness
    cell.thickness = definition.thickness
    cell.integrity = definition.integrity
    cell.liquid = 0
    cell.liquid_kind = ""
    cell.gas = 0
    cell.gas_kind = ""
    cell.flame = 0
    state.world_ledger.mark_terrain(
        state.layer_key(), x, y, solid=True, wall_kind="",
        floor=cell.floor.value, height=cell.height, hardness=cell.hardness,
        thickness=cell.thickness, integrity=cell.integrity)
    return True


def unseal_opening(state: Any, x: int, y: int) -> bool:
    """抬起挡板：只认地形增量里自己封过的那格，绝不开一堵真墙。"""
    entry = state.world_ledger.terrain_for(state.layer_key()).get(f"{x},{y}") or {}
    cell = state.cell(x, y)
    if not entry.get("solid") or not cell.solid or cell.wall_kind:
        return False
    state._open_door(cell)
    state._sound_pulse(x, y, 2, category="mechanical",
                       source=tr("门"), announce=False)
    state.world_ledger.mark_terrain(
        state.layer_key(), x, y, solid=False, wall_kind="",
        floor=cell.floor.value, height=0, hardness=0, thickness=0, integrity=0)
    return True


def place_threat(state: Any, record: Any, definition: dict[str, Any]) -> None:
    """把设施自带的常驻目标放回作用区中心（生成期与重建后各走一次）。

    身份用 ``world_scenes.threat_uid`` 而不是 ``enemy-N``：任务绑的是「泵房里那一位」，
    层快照被裁剪后重建不能把它变成一个没被登记过的新目标。已经留下一条 ``remove``
    事实的就不要再放——解决过的那位不会因为回层而复生。
    """
    spec = definition.get("threat")
    if not spec:
        return
    uid = world_scenes.threat_uid(record)
    if any(getattr(enemy, "actor_uid", "") == uid for enemy in state.enemies):
        return
    if state.world_ledger.facts_where(kind="remove", target_uid=uid):
        return
    cells = record.area(spec["key"])
    if not cells:
        return
    x, y = cells[len(cells) // 2]
    enemy = state.add_defined_enemy(spec["anomaly"], x, y)
    enemy.actor_uid = uid


def fold_player(state: Any, x: int, y: int) -> None:
    """把玩家折到指定格：只做既有「进入一格」的落地结算，不另写移动规则（§10.3）。

    落点合法性由 :mod:`dream_demo.world.scenes` 在计划阶段查过。跨门那一段是这套
    次序的现成样板：身份变化前后各一次、揭穿伪装、液体接触。折页不走过中间的格子，
    所以压力地板、植物踩踏与传送带都不参与——那是「走过去」的结算，不是「被折过去」。
    """
    origin = (state.player.x, state.player.y)
    identity_before = state._identity_before_move()
    state.player.x, state.player.y = x, y
    state._reveal_disguises()
    state._separate_anomalies_at(x, y, exclude=state.player)
    state._apply_liquid_contact(x, y)
    state._identity_after_move(origin, identity_before)


def _apply_layout(state: Any, record: Any) -> None:
    definition = world_scenes.definition_of(record)
    if definition is None:
        return
    for key, spec in (definition.get("terrain") or {}).items():
        for x, y in record.area(key):
            set_floor_variant(state, x, y, spec["variant"], int(spec.get("fuel", 0)))
    _place_blockage(state, record, definition)
    place_threat(state, record, definition)


def _place_blockage(state: Any, record: Any, definition: dict[str, Any]) -> None:
    """排放区里那件可搬动的杂物：同一片格子上已经有的就不重复放。"""
    spec = definition.get("blockage")
    if not spec:
        return
    cells = record.area(spec["key"])
    if not cells or any((entry.x, entry.y) in cells for entry in state.world_items):
        return
    x, y = cells[len(cells) // 2]
    state.world_items.append(WorldItem(state._make_item(spec["item"]), x, y))


def replay_terrain(state: Any) -> None:
    """把本层记在 ``world_ledger.terrain`` 里的结构性增量放回地图（§12.2）。"""
    for raw_key, fields in state.world_ledger.terrain_for(state.layer_key()).items():
        x_text, _, y_text = raw_key.partition(",")
        if not x_text.isdigit() or not y_text.isdigit():
            continue
        x, y = int(x_text), int(y_text)
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        cell = state.cell(x, y)
        for name, value in fields.items():
            if name=='floor':
                value=Material(value)
            setattr(cell, name, value)


# --------------------------------------------------------------- 锚点事件

def _bind_event(state: Any, record: Any) -> None:
    """在设施锚点挂一个可重复操作的复合事件（选项 = 有限命令表）。

    定义里写了 ``entrances`` 的（配对渡口）每一端各挂一个：两个入口指向同一份设施
    记录，站在哪一侧读到的都是同一本账。去重按事件自己的坐标做，所以重建一层的
    时候不会长出第二个同款入口。
    """
    definition = world_scenes.definition_of(record)
    if definition is None:
        return
    keys = tuple(definition.get("entrances") or (definition.get("anchor") or "",))
    options = tuple(
        {"label": command["label"], "scene_command": command["command"]}
        for command in definition["commands"]
    ) + ({"label": tr("先不碰它"), "leave": True},)
    existing = {getattr(entry, "event_id", "") for entry in state.events}
    for key in keys:
        anchor = record.cell(key)
        if anchor is None:
            continue
        event_id = f"{definition['definition_id']}@{anchor[0]},{anchor[1]}"
        if event_id in existing:
            continue
        existing.add(event_id)
        state.events.append(WorldEvent(
            event_id=event_id,
            name=definition["name"],
            x=anchor[0], y=anchor[1],
            description=definition["description"],
            catalog_id=definition["definition_id"],
            kind="compound",
            dialogue=(definition["description"], definition["clue"]),
            options=options,
            uses_left=1,
            bound=True,
            scene_uid=record.scene_uid,
        ))


def record_for(state: Any, event: Any) -> Any:
    """事件 → 它的设施记录（不在这一层或记录已消失时返回 None）。"""
    uid = getattr(event, "scene_uid", "") or ""
    return state.world_ledger.facilities.get(uid)


def operate_scene(state: Any, event: Any, name: str) -> ActionResult:
    """锚点面板里的一条设施命令：找不到记录就整笔拒绝（不扣资源、不扣回合）。"""
    record = record_for(state, event)
    if record is None:
        return ActionResult(False, tr("这台设施已经不在这儿了。"))
    return world_scenes.operate(state, record, name)
