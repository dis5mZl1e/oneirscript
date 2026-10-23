"""§12 F：三种环境设施（嵌壁梦灯 / 弧光灯架 / 余烬灯盏）的完整生命周期。

docs/261018方案合集.md 第十二节 §4.4、§5 的要求是：**没有完整生命周期的设施，
不得先靠随机摆一个发光点代替**。因此这三件不是一个「发光装饰」，而是三套状态机：

===========  ======================  ==========================  ==================
设施         亮灭由什么决定          开关反馈                    消耗/破坏后果
===========  ======================  ==========================  ==================
嵌壁梦灯     玩家开关（邻格切换）    切一次花 1 个动作，有提示    徒手可打碎，碎后不再发光
弧光灯架     电路真实通电            **不给**手动开关（见下）     打碎即灭，不额外供能
余烬灯盏     只有 ``cell.flame>0``   不给开关，点火/灭火就是操作   烧尽→原地留空，熄火即暗
===========  ======================  ==========================  ==================

三条硬约束（写在这里防止以后「顺手放开」）：

1. **数量极少**：本模块的投放趟按层给配额（嵌壁梦灯 1—2、弧光灯架 1—2、
   余烬灯盏 1—3），且与既有灯具拉开 ``FIXTURE_SPACING``。三种设施**不进**
   ``DEPTH_WALL_POOL``（见 materials/walls.py 的 wall_pool_for_depth 注释），
   否则会按普通墙的色块预算成片铺开。
2. **不改连通性**：投放只把**既有实心墙格**改造成灯具（仍是实心），既不拆墙
   也不新开通道；嵌壁梦灯还要求「只贴着一个开放格」（壁龛），所以打碎后原地
   只多出一个 1 格深的凹龛，既不开捷径也不堵退路。余烬灯盏允许挂在 1—2 面
   朝外的隔墙上，但余烬廊桥的三道蜡门由调用方列入 ``protected``——烧穿闸门
   等于绕过整个谜题。
3. **不免费**：弧光灯架不生成电场、不发电、不给伤害；余烬灯盏复用既有的
   燃料/点燃/灭火规则；嵌壁梦灯只是「站邻格花 1 个动作」的开关。

**玩具的回忆的例外**：那一层的墙是谜题箱体（`玩具箱壁`，解谜期间不可摧毁），
弧光灯架会改造箱体墙格，所以 ``materials_sim.destroy_wall`` 在玩具位面把
``LIGHT_FIXTURE_KINDS`` 一并列为不可拆——否则「把箱壁换成灯架」就成了破墙捷径。
它在别的位面/主梦里是可以打碎的（打碎即灭）。

状态同步的入口只有一个：``sync_light_fixtures(state)``，每世界回合在电路结算
**之后**调用（state._advance_world 的电路 tick 之后）。它只写 ``cell.light_on``，
不碰 ``light_radius``（半径是设施定义的一部分，破坏时由 ``clear_wall`` 归零）。
"""

from __future__ import annotations

import random

from ..materials import (
    CONTAINER_KINDS,
    DOOR_KINDS,
    FLAME_FIXTURE_KINDS,
    LIGHT_FIXTURE_KINDS,
    POWERED_FIXTURE_KINDS,
    TABLE_KINDS,
    WALL_DEFINITIONS,
)
from ..materials.logic import LOGIC_KINDS, TEMPLATE_ONLY_CIRCUIT_WALLS

# 设施布局专用随机流（与植物 0x9147、容器 0x2C07A、场景 0x9C3A1 都不同）。
FIXTURE_SEED_SALT = 0x5F1A7

# 嵌壁梦灯只出现在浅层（深层的常驻光交给晶体与熔念材料，避免整层被点亮）。
NICHE_LAMP_LAST_DEPTH = 10
# 与出生点的切比雪夫净空：灯具不会落在开局就能摸到的地方（浅层尤其重要）。
SPAWN_CLEARANCE = 4
# 同层设施之间的最小间距：两盏灯挤在一起只会重复照亮同一小片。
FIXTURE_SPACING = 4
# 8 邻域里允许出现的可燃邻格数（余烬灯盏）：位面本来就有燃料链，但一盏灯
# 旁边堆满可燃物 = 一落地就连片烧穿。超过这个数就不落。
EMBER_MAX_FLAMMABLE_NEIGHBOURS = 2

# 有专属状态、机制或可推/可点的墙种：绝不能被改造成灯具。
# 电路节点必须用 TEMPLATE_ONLY_CIRCUIT_WALLS（含接线枢／导电铜网墙），
# 只写 LOGIC_KINDS 会漏掉它们——实测会把「接线枢」改成灯架，电路直接断路。
_BLOCKED_KINDS = frozenset(
    DOOR_KINDS | CONTAINER_KINDS | TABLE_KINDS | LIGHT_FIXTURE_KINDS
    | LOGIC_KINDS | TEMPLATE_ONLY_CIRCUIT_WALLS
    | {"意识边界", "理念立方体", "蓝屏终端"}
)

# 未登记的位面箱体墙（只在玩具的回忆里用；没有独立 WallDef，故不在
# WALL_DEFINITIONS 里，只能按「允许名单」逐个放行）。
_BOX_WALL_KINDS = frozenset({"玩具箱壁"})

_NEIGHBOURS_4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
_NEIGHBOURS_8 = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0))


def _convertible(kind: str, *, boundary_ok: bool = False,
                 box_ok: bool = False) -> bool:
    """这种墙能不能被改造成灯具：要求它是「没有额外行为的普通实心墙」。

    ``boundary_ok`` 只给余烬廊桥这种「整层由意识边界围出的箱体」用：那里除
    边界与蜡门之外没有任何可挂灯的墙，而壁龛式的 1 格灯盏烧掉后只多出一个
    1 格凹龛，不改可达区域（见模块开头的连通性约束）。``box_ok`` 同理只给
    玩具的回忆：箱体墙没登记成材料，但弧光灯架就该挂在有电线的箱体上。
    """
    if kind == "意识边界":
        return boundary_ok
    if kind in _BOX_WALL_KINDS:
        return box_ok
    if not kind or kind in _BLOCKED_KINDS:
        return False
    definition = WALL_DEFINITIONS.get(kind)
    if definition is None:
        return False
    return (
        not definition.flammable
        and not definition.transparent
        and not definition.pushable
        and not definition.path_clickable
        and not definition.projectile_immune
        and definition.light_radius == 0
        and definition.break_effect in ("", "none")
        and definition.gas_dissipation_multiplier == 1
        and not definition.gas_push_direction
        and definition.integrity >= 30
    )


def _openings(cells, x: int, y: int) -> int:
    """8 邻域里的开放格数（用来区分「房间/廊桥」与「1 格宽缝」）。"""
    height, width = len(cells), len(cells[0])
    opened = 0
    for ny in range(y - 1, y + 2):
        for nx in range(x - 1, x + 2):
            if (nx, ny) == (x, y) or not (0 <= nx < width and 0 <= ny < height):
                continue
            if not cells[ny][nx].solid:
                opened += 1
    return opened


def _flammable_neighbours(cells, x: int, y: int, offsets=_NEIGHBOURS_8) -> int:
    """邻域里的可燃格数（墙/植物/液体/气体/现成的火）。"""
    height, width = len(cells), len(cells[0])
    count = 0
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < width and 0 <= ny < height):
            continue
        cell = cells[ny][nx]
        if cell.flame > 0 or cell.plant or cell.liquid or cell.gas:
            count += 1
            continue
        definition = WALL_DEFINITIONS.get(cell.wall_kind)
        if definition is not None and definition.flammable:
            count += 1
    return count


def _has_wire(cells, x: int, y: int) -> bool:
    """灯具自身或 4 邻格上有没有电线（弧光灯架只装在真实的配电位置上）。"""
    height, width = len(cells), len(cells[0])
    if cells[y][x].wire:
        return True
    for dx, dy in _NEIGHBOURS_4:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and cells[ny][nx].wire:
            return True
    return False


def _plan(depth: int, realm_id: str) -> tuple[tuple[str, tuple[int, int]], ...]:
    """本层要投放哪些设施、各多少件（配额是「最多几件」，找不到位置就少放）。"""
    plan: list[tuple[str, tuple[int, int]]] = []
    if realm_id == "toy_memories":
        plan.append(("弧光灯架", (1, 2)))
    elif realm_id == "ember_bridge":
        plan.append(("余烬灯盏", (1, 3)))
    if not realm_id and 1 <= depth <= NICHE_LAMP_LAST_DEPTH:
        plan.append(("嵌壁梦灯", (1, 2)))
    return tuple(plan)


def _site_candidates(cells, kind: str, protected, spawn,
                     *, boundary_ok: bool = False,
                     box_ok: bool = False) -> list[tuple[int, int]]:
    """这一层能改成 ``kind`` 的墙格。"""
    height, width = len(cells), len(cells[0])
    sites: list[tuple[int, int]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if (x, y) in protected:
                continue
            cell = cells[y][x]
            if not cell.solid or not _convertible(
                    cell.wall_kind, boundary_ok=boundary_ok, box_ok=box_ok):
                continue
            if spawn is not None and max(abs(x - spawn[0]), abs(y - spawn[1])) < SPAWN_CLEARANCE:
                continue
            neighbours = [
                (x + dx, y + dy) for dx, dy in _NEIGHBOURS_4
                if 0 <= x + dx < width and 0 <= y + dy < height
            ]
            open_cells = [(nx, ny) for nx, ny in neighbours if not cells[ny][nx].solid]
            if not open_cells:
                continue
            # 灯不往流体里照：旁边就是水/气时先不落，免得一装好就被浇灭或点着气体。
            if any(cells[ny][nx].liquid or cells[ny][nx].gas for nx, ny in neighbours):
                continue
            if kind == "嵌壁梦灯":
                # 壁龛式：只贴着一个开放格。这样「打碎」之后原地只多出一个
                # 1 格深的凹龛，既不开捷径、也不堵死退路。
                if len(open_cells) != 1:
                    continue
            elif kind == "余烬灯盏":
                # 廊桥上的灯只能挂在 1—2 面朝外的隔墙上；三道蜡门由调用方
                # 放进 protected（烧穿闸门等于绕过谜题）。嵌进意识边界壁的
                # 必须是壁龛（只贴一个开放格），烧尽后原地只留 1 格凹龛。
                limit = 1 if cell.wall_kind == "意识边界" else 2
                if len(open_cells) > limit:
                    continue
            if any(_openings(cells, nx, ny) < 2 for nx, ny in open_cells):
                # 邻格得是房间或廊桥，不是 1 格宽缝。
                continue
            if kind == "余烬灯盏" and _flammable_neighbours(cells, x, y) > EMBER_MAX_FLAMMABLE_NEIGHBOURS:
                continue
            if kind == "弧光灯架" and not _has_wire(cells, x, y):
                continue
            sites.append((x, y))
    return sites


def _install(cells, x: int, y: int, kind: str, *, lit: bool) -> None:
    """把墙格改造成设施：走统一的 configure_wall，再补灯字段。"""
    from .generation import GenerationMixin

    cell = cells[y][x]
    GenerationMixin.configure_wall(cell, kind)
    definition = WALL_DEFINITIONS[kind]
    cell.light_radius = definition.light_radius
    if kind in FLAME_FIXTURE_KINDS:
        # 余烬灯盏：发光资格由火焰给，初始亮着的先点起来（燃料归既有燃烧规则）。
        cell.flame = 1 if lit else 0
        cell.light_on = cell.flame > 0
    else:
        cell.light_on = bool(lit)


def _energized_at(energized, x: int, y: int) -> bool:
    """这一格或它的 4 邻格是否在已通电的电线上。"""
    if not energized:
        return False
    if (x, y) in energized:
        return True
    return any((x + dx, y + dy) in energized for dx, dy in _NEIGHBOURS_4)


def place_light_fixtures(
    cells,
    seed: int,
    depth: int,
    realm_id: str = "",
    *,
    protected=(),
    spawn=None,
    energized=(),
) -> dict:
    """把本层配额内的环境设施落进 ``cells``（只改造既有墙格）。

    返回审计结论，供生成报告与测试读取::

        {"targets": {"嵌壁梦灯": 2}, "counts": {"嵌壁梦灯": 1},
         "placed": [{"kind": ..., "x": ..., "y": ..., "lit": True}],
         "skipped": [{"kind": ..., "reason": ..., "detail": ...}]}
    """
    report: dict = {"targets": {}, "counts": {}, "placed": [], "skipped": []}
    plan = _plan(depth, realm_id)
    if not plan:
        report["skipped"].append(
            {"kind": "", "reason": "no_plan", "detail": f"{realm_id or 'main'}#{depth}"}
        )
        return report

    height, width = len(cells), len(cells[0])
    if width < 12 or height < 12:
        report["skipped"].append(
            {"kind": "", "reason": "map_too_small", "detail": f"{width}×{height}"}
        )
        return report

    rng = random.Random(seed ^ FIXTURE_SEED_SALT)
    taken: list[tuple[int, int]] = []

    for kind, (low, high) in plan:
        target = rng.randint(low, high)
        report["targets"][kind] = target
        sites = _site_candidates(
            cells, kind, protected, spawn,
            boundary_ok=(realm_id == "ember_bridge"),
            box_ok=(realm_id == "toy_memories"),
        )
        if not sites:
            report["skipped"].append(
                {"kind": kind, "reason": "no_candidate", "detail": f"{realm_id or 'main'}#{depth}"}
            )
            continue
        rng.shuffle(sites)
        placed = 0
        for x, y in sites:
            if placed >= target:
                break
            if any(max(abs(x - px), abs(y - py)) < FIXTURE_SPACING for px, py in taken):
                continue
            if kind == "余烬灯盏":
                # 只有四周（4 邻格）没有可燃物时才允许「一落地就烧着」——
                # 否则等于预先点燃了任务燃料，与「不预先点燃」冲突。
                lit = rng.random() < 0.5 and _flammable_neighbours(cells, x, y, _NEIGHBOURS_4) == 0
            elif kind == "弧光灯架":
                lit = _energized_at(energized, x, y)
            else:
                lit = True
            _install(cells, x, y, kind, lit=lit)
            taken.append((x, y))
            placed += 1
            report["placed"].append({"kind": kind, "x": x, "y": y, "lit": bool(lit)})
        report["counts"][kind] = placed
        if placed < target:
            report["skipped"].append(
                {"kind": kind, "reason": "spacing_or_sites", "detail": f"目标 {target}，实放 {placed}"}
            )
    return report


# --------------------------------------------------------------- 运行时同步


def _fixture_index(state) -> dict[str, list[tuple[int, int]]]:
    """本层三种设施的坐标索引（第一次同步时扫一遍，之后按 cells 对象复用）。

    被打破/烧尽的设施仍留在索引里——同步时会按 ``cell.wall_kind`` 复核并跳过，
    这样「破坏后撤销来源」不依赖任何清理回调。
    """
    stamp = (state.layer_key(), id(state.cells), len(state.cells))
    cached = getattr(state, "_light_fixture_index", None)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    index: dict[str, list[tuple[int, int]]] = {kind: [] for kind in LIGHT_FIXTURE_KINDS}
    for y in range(state.height):
        row = state.cells[y]
        for x in range(state.width):
            kind = row[x].wall_kind
            if kind in index:
                index[kind].append((x, y))
    state._light_fixture_index = (stamp, index)
    return index


def sync_light_fixtures(state) -> int:
    """让三种设施的 ``light_on`` 跟随真实状态；返回本次翻转的格数。

    调用位置只有一处：``state._advance_world`` 里电路结算（``_tick_circuit_boards``）
    之后。断电即灭、火熄即暗、烧尽即消失都因此只靠这一条路径成立。
    """
    changed = 0
    index = _fixture_index(state)
    for kind, positions in index.items():
        if kind not in POWERED_FIXTURE_KINDS and kind not in FLAME_FIXTURE_KINDS:
            continue
        for x, y in positions:
            cell = state.cell(x, y)
            if cell.wall_kind != kind or cell.light_radius <= 0:
                continue
            if kind in POWERED_FIXTURE_KINDS:
                wanted = _energized_at(getattr(state, "_logic_energized", ()), x, y)
            else:
                wanted = cell.flame > 0
            if cell.light_on != wanted:
                cell.light_on = wanted
                changed += 1
    if changed:
        from .vision import cache
        cache.invalidate(state)
    return changed


def fixture_summary(report: dict) -> dict:
    """把投放审计压成报告里的一行。"""
    reasons: dict[str, int] = {}
    for entry in report.get("skipped", ()):
        reason = entry.get("reason", "?")
        reasons[reason] = reasons.get(reason, 0) + 1
    placed = report.get("placed", ())
    return {
        "fixtures_placed": len(placed),
        "fixture_counts": dict(sorted(report.get("counts", {}).items())),
        "fixtures_lit_at_spawn": sum(1 for entry in placed if entry.get("lit")),
        "skipped": reasons,
    }
