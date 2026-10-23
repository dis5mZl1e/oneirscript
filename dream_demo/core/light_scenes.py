"""§12 E：光源场景模板与独立布局随机流（2026-10-20）。

「丰富来源不能只停留在目录」——本节把光源做成**场景组**落进可玩空间，
而不是全图随机撒发光点。规则全部来自 docs/261018方案合集.md 第十二节第 5 项：

- 一组 = 一小片同色光源（2—4 格连片），不是「一个点」，也不是「几十格一片算
  几十组」。组与组之间拉开 ``GROUP_SPACING``，因此总有大片未点亮的路线。
- 独立随机流：``random.Random(seed ^ SCENE_SEED_SALT)``，只决定光源布局。
  渲染、预览、重开显示都不重新抽样——布局随真实环境存档（写入 ``Cell.plant``）。
- 保护：出生点、结构区（含任务锚）、中央石台、NPC 站位一律不进候选；1 格宽
  走廊与门廊因「房间感」阈值被排除，所以不会占用唯一通路。不新增墙体、
  不额外开墙、不改动液体与气体存量。
- 没有合法位置就跳过并记录原因，不强行补足配额。

**内容供给口径（重要）**：新增格只用「拔除无收益」的发光地衣（码 3），每组
最多 ``max_new_cells`` 格；带奖励的发光植物（彩玻菌/融蜡花/夜皇后）只**升级
邻域里已有的普通植物**（低草/高丛），因此不增加植物总格数、也不额外增加
拔除奖励总量。这两条是平衡闸门，不要为了「颜色更丰富」直接放开。

位面侧（``realm:*``）一律只用无收益填充色，因为位面已有专用光源（灯箱墙、
日光壁、阅读灯、通电电路、门灯），这里只补一点弱光植物；白疗所刻意不投放
（洁白釉板 + 日光壁 + 银盐悬液已足够，加绿光反而破坏主题）。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..materials import floor_effect_for
from ..materials.plants import (
    PLANT_CODE_GLASS_SHROOM,
    PLANT_CODE_LICHEN,
    PLANT_CODE_NIGHT_QUEEN,
    PLANT_CODE_SHORT,
    PLANT_CODE_TALL,
    PLANT_CODE_WAX_BLOOM,
    plant_def_for,
)
from ..mapgen import region_falloff

# 场景布局专用随机流（与植物 seed ^ 0x9147、容器 seed ^ 0x2C07A 都不同）。
SCENE_SEED_SALT = 0x9C3A1

# 生成率：组 / 1000 个可通行格（文档：主梦 3—6 组，位面设备区 4—8 组）。
DEFAULT_DENSITY = 4.0
REALM_DENSITY = 5.0
MAX_GROUPS = 12
# 组间最小切比雪夫距离：保证每层都留着「没被常驻灯照亮的普通路线」。
GROUP_SPACING = 7
# 8 邻域至少这么多格开放才算「房间/厅」，否则视为走廊（不落灯）。
ROOM_OPENNESS = 5
# 片段外缘的下限：低于此值就是 1 格宽通道（两侧墙），弱光不往通道里伸展。
CLUSTER_MIN_OPENNESS = 3
# 片段搜索半径（切比雪夫）：一组只在一小块局部空间里成形。
CLUSTER_RADIUS = 2

# 浅层/幻觉/无意识/深层边界：与 LAYER_THEMES 的四档同口径。
STAGE_ORDER = (
    (1, 10, "awakening"),
    (11, 20, "hallucination"),
    (21, 27, "unconscious"),
    (28, 30, "boundary"),
)


@dataclass(frozen=True)
class LightSceneTemplate:
    """一条场景模板：一小片同色光源 + 可选的邻域升格点缀。

    ``fill_code`` 是主体光源的植物码（必须是「拔除无收益」的种类，
    见模块开头的内容供给口径）；``accent_code`` 只在**该片段里已经存在**
    普通植物时把那 1 格升格成带奖励的发光植物，绝不新增格子。
    """

    scene_id: str
    stage: str                 # awakening / hallucination / … / realm:<realm_id>
    fill_code: int
    accent_code: int | None
    group_min: int
    group_max: int
    max_new_cells: int
    weight: float
    note: str = ""


TEMPLATES: tuple[LightSceneTemplate, ...] = (
    # ---- 主梦：浅层 1—10（保留无灯岔路；不放深层晶体/熔念材料）----
    LightSceneTemplate(
        "awakening.lichen_patch", "awakening", PLANT_CODE_LICHEN,
        PLANT_CODE_WAX_BLOOM, 2, 4, 3, 3.0,
        "地衣小片，边上偶尔一朵融蜡花作暖点（只升格已有植物）",
    ),
    LightSceneTemplate(
        "awakening.lichen_pure", "awakening", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 2.0,
        "纯地衣弱光：只有黄绿一种色，大半房间仍然不亮",
    ),
    # ---- 幻觉空间 11—20（冷紫晶体与暖灯相邻，不用全层紫色滤镜）----
    LightSceneTemplate(
        "hallucination.glass_nook", "hallucination", PLANT_CODE_LICHEN,
        PLANT_CODE_GLASS_SHROOM, 2, 4, 2, 3.0,
        "地衣打底 + 一朵彩玻菌（粉紫）：局部两色，不是整层灯罩",
    ),
    LightSceneTemplate(
        "hallucination.lichen_vein", "hallucination", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 1.2,
        "只有地衣的低亮边角，留给无光源的房间与岔路",
    ),
    # ---- 无意识领域 21—27（既有晶体/熔念金属之外的一点植被光）----
    LightSceneTemplate(
        "unconscious.night_edge", "unconscious", PLANT_CODE_LICHEN,
        PLANT_CODE_NIGHT_QUEEN, 2, 4, 2, 3.0,
        "地衣 + 夜皇后（紫）：与既有熔念金属岸边、结晶形成冷暖交错",
    ),
    LightSceneTemplate(
        "unconscious.wax_remnant", "unconscious", PLANT_CODE_LICHEN,
        PLANT_CODE_WAX_BLOOM, 2, 3, 2, 1.0,
        "地衣 + 融蜡花：少量暖残光，不新增危险材料",
    ),
    # ---- 位面：只补无收益填充色，专用光源仍由位面自身生成器负责 ----
    LightSceneTemplate(
        "door_corridor.cold_low", "realm:door_corridor", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 1.0,
        "门廊角落的冷弱光；门本身不因金色发光",
    ),
    LightSceneTemplate(
        "ember_bridge.ash_edge", "realm:ember_bridge", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 1.0,
        "廊桥边缘弱光；真实火光仍只来自燃料链与点燃",
    ),
    LightSceneTemplate(
        "ebbing_hall.island_edge", "realm:ebbing_hall", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 1.0,
        "中心岛外缘少量稳定低亮，不做「最佳路线导航」",
    ),
    LightSceneTemplate(
        "library_palace.side_moss", "realm:library_palace", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 1.0,
        "侧室少量植物弱光；阅读灯灯段与书架遮光仍走原规则",
    ),
    LightSceneTemplate(
        "toy_memories.cold_dot", "realm:toy_memories", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 0.8,
        "器械区旁的冷点；开关仍只改变真实电路来源",
    ),
    LightSceneTemplate(
        "millennium_garden.verge", "realm:millennium_garden", PLANT_CODE_LICHEN,
        None, 2, 3, 2, 0.8,
        "灯箱墙与通电节点之外的一点草地弱光，不给每个图标发光",
    ),
)

# 明确「本批不投放」的位面：写在这里，生成报告会照实列出原因。
NO_TEMPLATE_REASON = {
    "realm:white_sanatorium": "至白疗所用日光壁灯段与银盐悬液泄漏；不额外加植物弱光",
    "boundary": "深层边界保留原生成池与大片暗区，不强制加入候选材料",
}

_BY_STAGE: dict[str, tuple[LightSceneTemplate, ...]] = {}
for _template in TEMPLATES:
    _BY_STAGE.setdefault(_template.stage, ())
    _BY_STAGE[_template.stage] += (_template,)


def stage_key(depth: int, realm_id: str = "") -> str:
    """本层用哪一组模板：位面按 realm_id，主梦按四档深度。"""
    if realm_id:
        return f"realm:{realm_id}"
    for low, high, name in STAGE_ORDER:
        if low <= depth <= high:
            return name
    return "boundary"


def templates_for(key: str) -> tuple[LightSceneTemplate, ...]:
    return _BY_STAGE.get(key, ())


def _open_for_plant(cell) -> bool:
    """可落植物光的格子：开阔、无液体、无墙体/容器、不是空白聚合物。"""
    return (
        not cell.solid
        and not cell.wall_kind
        and cell.liquid == 0
        and not floor_effect_for(cell).bare
    )


def _ordinary_plant(code: int) -> bool:
    """可被升格的普通植物（低草/高丛）：拔除没有任何奖励，升格不改总格数。"""
    return code in (PLANT_CODE_SHORT, PLANT_CODE_TALL)


def _free_plant_slot(code: int) -> bool:
    """空位（码 0），或者会被覆盖的普通植物。字面上「可写」但不代表会用掉配额。"""
    return code == 0 or _ordinary_plant(code)


def _openness(cells, x: int, y: int) -> tuple[int, int]:
    """(8 邻域开放格数, 其中实实在在的墙体/固体数)。"""
    height, width = len(cells), len(cells[0])
    opened = 0
    walls = 0
    for ny in range(y - 1, y + 2):
        for nx in range(x - 1, x + 2):
            if (nx, ny) == (x, y) or not (0 <= nx < width and 0 <= ny < height):
                continue
            if cells[ny][nx].solid:
                walls += 1
            else:
                opened += 1
    return opened, walls


def _accent_allowed(code: int, depth: int, realm_id: str) -> bool:
    """点缀植物必须本来就允许出现在这一层（区域登记不满足就不升格）。"""
    if realm_id:
        return False
    definition = plant_def_for(code)
    if definition.code != code:      # 未知码回退低草，不要拿它当点缀
        return False
    if definition.region is None:
        return True
    return region_falloff(depth, *definition.region) > 0


def _cluster(cells, ax: int, ay: int, blocked: set) -> list[tuple[int, int]]:
    """从锚格出发的 4 连通片段（切比雪夫半径内），只收可落植物光的格。"""
    height, width = len(cells), len(cells[0])
    seen = {(ax, ay)}
    stack = [(ax, ay)]
    out: list[tuple[int, int]] = []
    while stack:
        x, y = stack.pop()
        out.append((x, y))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in seen:
                continue
            if abs(nx - ax) > CLUSTER_RADIUS or abs(ny - ay) > CLUSTER_RADIUS:
                continue
            if (nx, ny) in blocked:
                continue
            cell = cells[ny][nx]
            if not _open_for_plant(cell) or not _free_plant_slot(cell.plant):
                continue
            # 片段边缘也不许伸进 1 格宽走廊（开放邻格 < 3 = 通道而非房间）。
            if _openness(cells, nx, ny)[0] < CLUSTER_MIN_OPENNESS:
                continue
            seen.add((nx, ny))
            stack.append((nx, ny))
    return out


def place_light_scenes(
    cells,
    seed: int,
    depth: int,
    realm_id: str = "",
    *,
    protected=(),
    density: float | None = None,
) -> dict:
    """把本层的光源场景组落进 ``cells``（只改 ``Cell.plant``）。

    返回一份审计结论，供生成报告与测试读取::

        {"stage": "awakening", "target": 8, "groups": [...], "skipped": [...],
         "new_cells": 9, "upgraded_cells": 4}

    ``protected`` 是绝不能碰的格（出生点、结构区、石台、NPC 站位）。
    """
    key = stage_key(depth, realm_id)
    templates = templates_for(key)
    report = {
        "stage": key,
        "target": 0,
        "groups": [],
        "skipped": [],
        "new_cells": 0,
        "upgraded_cells": 0,
    }
    if not templates:
        report["skipped"].append(
            {"reason": "no_template", "detail": NO_TEMPLATE_REASON.get(key, "本层未登记模板")}
        )
        return report

    height, width = len(cells), len(cells[0])
    if width < 12 or height < 10:
        report["skipped"].append({"reason": "map_too_small", "detail": f"{width}×{height}"})
        return report

    walkable = sum(
        1 for y in range(height) for x in range(width) if not cells[y][x].solid
    )
    rate = density if density is not None else (REALM_DENSITY if realm_id else DEFAULT_DENSITY)
    # 组数配额：density=0 表示「这一层不投放」（对照/测试与极窄地图共用）。
    target = min(MAX_GROUPS, max(0, int(round(walkable * rate / 1000.0))))
    if rate <= 0:
        target = 0
    report["target"] = target
    if target <= 0:
        report["skipped"].append({"reason": "budget_zero", "detail": "本层不投放场景"})
        return report

    rng = random.Random(seed ^ SCENE_SEED_SALT)
    blocked = set(protected)

    anchors: list[tuple[int, int]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if (x, y) in blocked:
                continue
            cell = cells[y][x]
            if not _open_for_plant(cell) or not _free_plant_slot(cell.plant):
                continue
            opened, walls = _openness(cells, x, y)
            # 走廊（开放邻格太少）不落灯；贴着墙体/固体 → 光沿边缘走，房心留暗。
            if opened < ROOM_OPENNESS or walls < 1:
                continue
            anchors.append((x, y))
    if not anchors:
        report["skipped"].append({"reason": "no_candidate", "detail": "没有房间感的开放格"})
        return report

    rng.shuffle(anchors)
    weights = [template.weight for template in templates]
    picked: list[tuple[int, int]] = []

    for ax, ay in anchors:
        if len(report["groups"]) >= target:
            break
        if any(max(abs(ax - gx), abs(ay - gy)) < GROUP_SPACING for gx, gy in picked):
            continue
        pool = _cluster(cells, ax, ay, blocked)
        template = rng.choices(templates, weights=weights, k=1)[0]
        if len(pool) < template.group_min:
            report["skipped"].append(
                {"reason": "cluster_too_small", "detail": f"{template.scene_id}@{ax},{ay}",
                 "size": len(pool)}
            )
            continue

        # 片段内排序：已有的普通植物优先（升格不增加格数），其次靠近锚点。
        pool.sort(key=lambda pos: (not _ordinary_plant(cells[pos[1]][pos[0]].plant),
                                  abs(pos[0] - ax) + abs(pos[1] - ay)))
        # 本片最多能点亮几格 = 升格（不增格数）+ 新增配额。先按预算收窄，
        # 免得「挑满 3 格、填到第 2 格才发现配额用光」这种半途而废。
        upgrades = sum(1 for pos in pool if _ordinary_plant(cells[pos[1]][pos[0]].plant))
        budget = upgrades + template.max_new_cells
        size = min(len(pool), rng.randint(template.group_min, template.group_max), budget)
        if size < template.group_min:
            report["skipped"].append(
                {"reason": "quota_exhausted", "detail": f"{template.scene_id}@{ax},{ay}",
                 "size": size}
            )
            continue
        chosen = pool[:size]

        accent_cell = None
        if template.accent_code is not None and _accent_allowed(
            template.accent_code, depth, realm_id
        ):
            accent_cell = next(
                (pos for pos in chosen if _ordinary_plant(cells[pos[1]][pos[0]].plant)),
                None,
            )

        new_cells = 0
        filled: list[tuple[int, int]] = []
        if accent_cell is not None:
            cells[accent_cell[1]][accent_cell[0]].plant = template.accent_code
            filled.append(accent_cell)
        for pos in chosen:
            if pos == accent_cell:
                continue
            cell = cells[pos[1]][pos[0]]
            if cell.plant == 0:
                if new_cells >= template.max_new_cells:
                    continue
                new_cells += 1
            cell.plant = template.fill_code
            filled.append(pos)
        if len(filled) < 2:      # 点不成片：退回去，不留孤点（宁缺毋滥）
            for pos in filled:
                cells[pos[1]][pos[0]].plant = 0
            report["skipped"].append(
                {"reason": "cluster_too_small", "detail": f"{template.scene_id}@{ax},{ay}",
                 "size": len(filled)}
            )
            continue

        picked.append((ax, ay))
        report["new_cells"] += new_cells
        report["upgraded_cells"] += len(filled) - new_cells
        report["groups"].append(
            {
                "scene_id": template.scene_id,
                "x": ax,
                "y": ay,
                "cells": filled,
                "fill_code": template.fill_code,
                "accent_code": template.accent_code if accent_cell else None,
                "accent_cell": accent_cell,
                "new_cells": new_cells,
            }
        )

    if len(report["groups"]) < target:
        report["skipped"].append(
            {"reason": "budget_unmet", "detail": f"目标 {target} 组，实际 {len(report['groups'])} 组"}
        )
    return report


def group_summary(report: dict) -> dict:
    """把审计结论压成报告里够用的一行（组数/格数/跳过原因计数）。"""
    reasons: dict[str, int] = {}
    for entry in report.get("skipped", ()):
        reason = entry.get("reason", "?")
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "stage": report.get("stage", ""),
        "target_groups": report.get("target", 0),
        "scene_groups": len(report.get("groups", ())),
        "lit_cells_from_scenes": report.get("new_cells", 0) + report.get("upgraded_cells", 0),
        "new_cells": report.get("new_cells", 0),
        "upgraded_cells": report.get("upgraded_cells", 0),
        "scene_ids": sorted({g["scene_id"] for g in report.get("groups", ())}),
        "skipped": reasons,
    }
