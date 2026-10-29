"""格子生成与层内容投放：墙体区域分配、地面容器、出生点与连通修复。"""

from __future__ import annotations
from ..materials import DOOR_KINDS

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import GameState


import random
import time
from .main_difficulty import CURRENT_DIFFICULTY_REVISION

from ..i18n import tr
from ..data.events import EVENT_MAX_PER_LAYER as _EVENT_MAX_PER_LAYER
from ..data.npcs import NPC_MAX_PER_LAYER
from ..mapgen import (
    generate_elevation,
    generate_solid_mask,
    generate_solid_mask_with_vaults,
    layer_dimensions,
    layer_form_for,
    layer_modifier_for,
    place_doors,
    region_falloff,
)
from ..materials import (
    CONTAINER_KINDS,
    SURFACE_KINDS,
    FEATURE_WALLS,
    REGION_WALL_RANGES,
    RARE_PLANT_CHANCE,
    RARE_PLANT_SINGLE_CHANCE,
    gas_pool_for_depth,
    liquid_pool_for_depth,
    rare_plant_kind,
    rare_plant_weight,
    GAS_DEFINITIONS,
    LIQUID_DEFINITIONS,
    PATCH_MAX_SIZE,
    PATCH_MIN_SIZE,
    SINGLE_PLANT_CHANCE,
    WALKABLE_FEATURE_WALLS,
    REALM_LOCAL_PLANTS,
    floor_effect_for,
    plant_def_for,
    plant_kind,
    plant_profile,
    realm_plant_kind,
    wall_def,
    wall_pool_for_depth,
    wall_spawn_budget,
)
from .constants import EXPOSED_ONLY_WALLS, Material
from .content import (
    EVENT_DEFINITIONS,
    MEMORY_RARITY,
    ITEM_DEFINITIONS,
    LAYER_THEMES,
    anomaly_pool_for_depth,
    equipment_pool_for_depth,
    event_candidates,
    items_of_rarity,
    roll_rarity,
    event_uses,
    event_spawn_kwargs,
    STRUCTURE_NPC_BINDING,
)
from .entities import Cell, Entity, WorldEvent, WorldItem
from .treasure_offers import build_options as build_treasure_options
from .treasure_offers import stage_for_depth as treasure_stage_for_depth



# 释出通道 -> 每层自然生成的株数上限（docs 2026-10-26 §9.2）。
_RELEASE_CHANNEL_CAPS: dict[str, int] = {
    "sound": 1,      # T2 巨响
    "fire": 1,       # 火
    "electric": 2,   # 电
    "integrity": 2,  # 耐久削减
    "snared": 2,     # 缚住
    "liquid": 2,     # 液体
    "push": 2,       # 搬气（不产生新材料）
    "gas": 2,        # 气体
}


# 错帧片/散页脊的 H1 收拢态（催生目标，docs §10.1）：有形态转换的那几种
# 里，生成时按这个比例落成「还没立起来」的矮态。
_YOUNG_FORM_FOR: dict[int, int] = {30: 42, 32: 43}
YOUNG_FORM_CHANCE = 0.3


def _release_channel(definition) -> str:
    """这株的释出通道（用于每层封顶）；不是释出型返回空串。"""
    release = getattr(definition, "release", None)
    if release is None:
        return ""
    if release.sound >= 6:
        return "sound"
    if release.ignite:
        return "fire"
    if release.electric:
        return "electric"
    if release.integrity:
        return "integrity"
    if release.portent:
        return "snared"
    if release.liquid:
        return "liquid"
    if release.push_gas:
        return "push"
    if release.gas:
        return "gas"
    return ""


def _stamp_plant_state(cell, definition, x: int, y: int) -> None:
    """给需要朝向的植物登记朝向（压差囊的嘴、风向标苔的风向）。

    只用坐标推导，不掷骰子：同一株在读档、上下层重建后必须还是同一个朝向，
    否则「把气推向哪一格」会跟着刷新跳。
    """
    needs_direction = bool(
        getattr(definition, "push_gas_budget", 0)
        or (definition.release is not None and definition.release.push_gas)
    )
    if not needs_direction:
        return
    cell.plant_state["direction"] = [(0, -1), (1, 0), (0, 1), (-1, 0)][(x * 7 + y * 13) % 4]


class GenerationMixin:
    @staticmethod
    def configure_wall(cell: Cell, kind: str) -> None:
        cell.creation = {}
        cell.phase_stock = {}
        definition = wall_def(kind)
        cell.doorway = definition.name in DOOR_KINDS
        cell.plant = 0
        cell.plant_fuel = cell.floor_fuel = cell.item_burn_progress = 0
        if definition.name in WALKABLE_FEATURE_WALLS:
            # 可步行特征墙（云块/枕木）：生物直接穿过，数据上不作为坚实格。
            cell.floor = Material.PLAIN_AGGREGATE
            cell.solid = False
            cell.wall_kind = definition.name
            cell.hardness = definition.hardness
            cell.height = definition.height
            cell.thickness = definition.thickness
            cell.integrity = definition.integrity
            cell.liquid = 0
            cell.liquid_kind = ""
            cell.gas = 0
            cell.gas_kind = ""
            cell.flame = 0
            return
        cell.floor = Material.SOLID_AGGREGATE
        cell.solid = True
        cell.wall_kind = definition.name
        cell.hardness = definition.hardness
        cell.height = definition.height
        cell.thickness = definition.thickness
        cell.integrity = definition.integrity
        cell.liquid = 0
        cell.liquid_kind = ""
        cell.gas = 0
        cell.gas_kind = ""
        cell.flame = 0

    @staticmethod
    def clear_wall(cell: Cell) -> None:
        cell.creation = {}
        cell.phase_stock = {}
        if cell.light_radius > 0:
            cell.light_radius = 0
            cell.light_on = False
        cell.doorway = cell.doorway or cell.wall_kind in DOOR_KINDS
        cell.floor = Material.PLAIN_AGGREGATE
        cell.solid = False
        cell.wall_kind = ""
        cell.height = 0
        cell.hardness = 0
        cell.thickness = 0
        cell.integrity = 0
        cell.plant = 0
        cell.plant_fuel = cell.floor_fuel = 0


    @staticmethod
    def _generate_cells(seed: int, width: int, height: int, map_form: str = "传统房间群", depth: int = 1, modifier: str = "", vault_sink: "dict | None" = None, realm_id: str = "", *, defer_natural_gas: bool = False) -> list[list[Cell]]:
        rng = random.Random(seed ^ 0x31F0A)
        solid_mask, vault_placements = generate_solid_mask_with_vaults(seed, width, height, map_form, modifier, depth=depth)
        if vault_sink is not None:
            # 中央石台（loot=True 模板）位置：_seed_layer_contents 用来投放稀有物品。
            vault_sink["loot_cells"] = [
                placement.loot_cell for placement in vault_placements if placement.loot_cell
            ]
            # 保护区（含边界的矩形）：出生连通修复同样要绕开模板形状。
            vault_sink["regions"] = [placement.region for placement in vault_placements]
            vault_sink["spawn_regions"] = [p.region for p in vault_placements
                                           if p.vault.circuit or p.vault.npc_anchor
                                           or (p.vault.width >= 10 and p.vault.height >= 10)]
            # 结构绑定事件（2026-09-18）：中大型结构生成时附带固定异常地点。
            # 位置优先落在 loot 石台上，否则取结构中心。2026-10-27 起与随机
            # 零散事件**共用**每层名额：盖章期由 forms 的余额先占额（同层最多
            # EVENT_MAX_PER_LAYER 栋带事件的结构），随机投放只在余额内补位。
            # 结构附属 NPC（2026-09-18）：随结构生成，同样占每层 NPC 名额。
            vault_sink["structure_npcs"] = [
                ((placement.left + anchor[1], placement.top + anchor[0]), npc_id)
                for placement in vault_placements
                if (npc_id := placement.vault.npc_id or STRUCTURE_NPC_BINDING.get(placement.vault.vid))
                for anchor in [placement.vault.npc_anchor or (placement.vault.height // 2, placement.vault.width // 2)]
            ]
            # 逻辑固体（内容扩展包 v1）：显式电线位、压力地板、陷阱场景抽签、
            # 灌注阀储备——陷阱在**盖章时**从模板 trap_pool 随机选定一种。
            logic_wires: set[tuple[int, int]] = set()
            logic_pressure: set[tuple[int, int]] = set()
            logic_chain: list[tuple[int, int]] = []
            logic_traps: dict[str, str] = {}
            logic_valves: dict[str, tuple[str, int]] = {}
            logic_boards = []
            from ..materials.logic import LOGIC_KINDS, TRAP_SCENARIO_LIBRARY, roll_trap_scenario_name
            all_names = tuple(TRAP_SCENARIO_LIBRARY)
            for placement in vault_placements:
                if placement.vault.circuit:
                    from ..circuit_schema import transform_board
                    logic_boards.append(transform_board(placement.vault.circuit,
                                        lambda x, y: (x+placement.left, y+placement.top)))
                    logic_boards[-1]["vault_id"] = placement.vault.vid
                    logic_boards[-1]["allowed_depths"] = list(placement.vault.allowed_depths)
                    logic_boards[-1]["region"] = list(placement.region)
                else:
                    logic_wires |= placement.wire_cells()
                logic_pressure |= placement.pressure_floor_cells()
                if not placement.vault.circuit:
                    for kind in sorted(LOGIC_KINDS):
                        logic_chain.extend(placement.logic_node_cells(kind))
                for (tx, ty) in placement.trap_positions():
                    name = roll_trap_scenario_name(
                        placement.vault.trap_pool or all_names, seed, depth, tx, ty,
                    )
                    logic_traps[f"{tx},{ty}"] = name
                for (vx, vy) in placement.logic_node_cells("灌注阀"):
                    logic_valves[f"{vx},{vy}"] = (
                        placement.vault.valve_material or "水", 24)
            logic_chain.extend(sorted(logic_wires))
            if logic_chain or logic_traps or logic_pressure or logic_boards:
                vault_sink["logic"] = {
                    "pressure": logic_pressure,
                    "chain": logic_chain,
                    "traps": logic_traps,
                    "valves": logic_valves,
                    "boards": logic_boards,
                }
            vault_sink["events"] = [
                {
                    "event_id": placement.vault.event,
                    "x": placement.left + placement.vault.event_anchor[1] if placement.vault.event_anchor else (placement.loot_cell or placement.center)[0],
                    "y": placement.top + placement.vault.event_anchor[0] if placement.vault.event_anchor else (placement.loot_cell or placement.center)[1],
                }
                for placement in vault_placements
                if getattr(placement.vault, "event", "")
            ]
        # 门在所有墙体生成之后再撒：把 1 格宽通道里的若干格改成实心，
        # 由 _assign_wall_kinds 染成「门」墙种（高墙、恒阻视线）。
        door_positions = place_doors(solid_mask, seed, width, height, map_form)
        # Authored passages, pressure plates and doors own their geometry.
        door_positions = {(x, y) for x, y in door_positions
                          if not any(a <= x <= c and b <= y <= d
                                     for a, b, c, d in (p.region for p in vault_placements))}
        # 门位原本是 1 格宽通道里的开放格；先逐格变成实心，门才会作为墙参与
        # 区域生长与连通修复，随后被染成「门」。门关闭时挡路、踩上即开。
        for x, y in door_positions:
            solid_mask[y][x] = True
        elevation_grid = generate_elevation(seed ^ 0x31F0A, width, height)
        # vault 指定墙种（石台/木桌子/玻璃温室整栋玻璃……）：区域生长后覆写，
        # 门位最后强制染色，优先级高于模板指定。不定模板的整栋材料也在
        # kind_overrides 里体现（盖章时抽定的那一种）。
        vault_kinds: dict[tuple[int, int], str] = {}
        vault_liquids: dict[tuple[int, int], str] = {}
        for placement in vault_placements:
            vault_kinds.update(placement.kind_overrides())
            vault_liquids.update(placement.liquid_overrides())
        wall_assignment = GenerationMixin._assign_wall_kinds(rng, solid_mask, width, height, depth, door_positions, vault_kinds,
                                                             realm_id=realm_id)
        liquid_pool = liquid_pool_for_depth(depth, realm_id=realm_id)
        gas_pool = gas_pool_for_depth(depth, realm_id=realm_id)
        liquid_total = sum(weight for _, weight in liquid_pool)
        gas_total = sum(weight for _, weight in gas_pool)

        def weighted_kind(pool, total):
            roll = rng.random() * total
            for kind, weight in pool:
                roll -= weight
                if roll < 0:
                    return kind
            return pool[-1][0]
        # 保留旧分支抽样顺序，避免气体改造改变同种子的液体与地板。
        # 主梦天然气体稍后独立聚团；专属位面仍使用既有生成规则。
        liquid_rate = 0.010 * (3.0 if modifier == "潮湿" else 1.0)
        gas_rate = 0.009 * (3.0 if modifier == "气密" else 1.0)
        cells = [[Cell() for _ in range(width)] for _ in range(height)]
        gas_protected: set[tuple[int, int]] = set()
        # 稳定意识（NPC）站位（2026-09-18）：在液体/气体/植物生成**之前**选位，
        # 生成后再清空站位的流体/植物——NPC 落脚处永远干净。
        if vault_sink is not None:
            npc_rng = random.Random(seed ^ 0x7C0DE)
            npc_candidates = [
                (x, y)
                for y in range(2, height - 2)
                for x in range(2, width - 2)
                if not solid_mask[y][x]
                and not any(p.left <= x < p.left+p.vault.width and p.top <= y < p.top+p.vault.height
                            for p in vault_placements if p.vault.circuit or p.vault.npc_anchor or p.vault.event_anchor)
            ]
            npc_rng.shuffle(npc_candidates)
            npc_spots: list[tuple[int, int]] = []
            min_gap = max(8, (width + height) // 6)
            # 2026-09-19 生成率调整：先掷骰决定本层 NPC 总数——
            # 2 名稀坐、1 名中等、0 名（其余）。
            # 之前的「每候选掷概率」在数千候选下必满员，等于没有概率。
            # 2026-10-22（E5后续 P1）：8%／25%／67% → 3%／22%／75%，
            # 期望 0.41 → 0.28（约 −32%）。E5 实测 NPC 直给只占入包 1.8%，
            # 它影响的是「每层都有可对话对象」的观感，不是物资溢出的主因，
            # 所以只降频、不删结构剧情 NPC（结构锚点走 vault_info，不经此处）。
            npc_roll = npc_rng.random()
            npc_quota = 2 if npc_roll < 0.03 else (1 if npc_roll < 0.25 else 0)
            # 2026-10-27：结构自带的 NPC 同样占每层名额（盖章期已按余额封顶
            # 结构侧），随机预留位只在余额内补位——总量不会超过
            # NPC_MAX_PER_LAYER。
            npc_quota = min(
                npc_quota,
                max(0, NPC_MAX_PER_LAYER - len(vault_sink.get("structure_npcs", ()))),
            )
            seat = 0
            if npc_quota:
                for x, y in npc_candidates:
                    if seat >= npc_quota:
                        break
                    if all(max(abs(x - ox), abs(y - oy)) >= min_gap for ox, oy in npc_spots):
                        npc_spots.append((x, y))
                        seat += 1
            vault_sink["npc_spots"] = npc_spots
            gas_protected.update(npc_spots)
        for y in range(height):
            for x in range(width):
                if x in (0, width - 1) or y in (0, height - 1):
                    GenerationMixin.configure_wall(cells[y][x], "意识边界")
                elif solid_mask[y][x]:
                    GenerationMixin.configure_wall(cells[y][x], wall_assignment[(x, y)])
        # 地面容器：独立的一趟投放。它有自己的随机流（seed ^ 0x2C07A）与自己的
        # 密度旋钮，只按「不与外露专属墙相邻」这一个条件选址——既不占用植物
        # 的名额，也不被植物的密度影响（反之亦然）。植物随后只落在没有容器的
        # 空地上，两者互不覆盖（见 _spawn_containers / _grow_plants）。
        GenerationMixin._spawn_containers(
            cells, random.Random(seed ^ 0x2C07A), wall_assignment
        )
        for y in range(height):
            for x in range(width):
                cell = cells[y][x]
                if cell.wall_kind or cell.solid:
                    # 边界 / 墙体 / 地面容器：容器已在上一趟落地，这里不再掷流体与变体。
                    continue
                cell.elevation = elevation_grid[y][x]
                if (x, y) in vault_liquids:
                    # 模板显式声明的液体位（图案字符 ~）：灌满、不再掷自然流体。
                    cell.liquid = 100
                    cell.liquid_kind = vault_liquids[(x, y)]
                    continue
                roll = rng.random()
                if roll < liquid_rate:
                    # 液体自然生成强烈偏向低洼处：地势 0/1 权重最高（必然积液），
                    # 越高越存不住水（见 LIQUID_ELEVATION_WEIGHTS）。
                    if rng.random() < GenerationMixin.LIQUID_ELEVATION_WEIGHTS[elevation_grid[y][x]]:
                        cell.liquid = 100
                        cell.liquid_kind = weighted_kind(liquid_pool, liquid_total)
                elif roll < liquid_rate + gas_rate:
                    legacy_kind = weighted_kind(gas_pool, gas_total)
                    if realm_id:
                        cell.gas = 100
                        cell.gas_kind = legacy_kind
                else:
                    cell.aggregate_variant = ("普通聚合物", "柔软聚合物", "粗糙聚合物", "反光聚合物", "吸声聚合物", "空白聚合物")[rng.randrange(6)]
        # 植物投放：在液体/气体之后、生物之前（优先级最低），只落在没有
        # 液体的开放空地上。参数按楼层修饰符取：普通层更稀疏零散，
        # 「繁茂」层覆盖率最高（见 materials.plants.plant_profile）。
        plant_plan = plant_profile(modifier)
        GenerationMixin._grow_plants(
            cells,
            random.Random(seed ^ 0x9147),
            plant_plan.coverage,
            single_chance=plant_plan.single_chance,
            patch_min=plant_plan.patch_min,
            patch_max=plant_plan.patch_max,
            depth=depth,
            realm_id=realm_id,
        )
        # 稀有地板（木质/海绵/金属/灼热聚合物）：生成率低且总是连片，
        # 不单独出现（见 _grow_rare_floors）。
        GenerationMixin._grow_rare_floors(cells, random.Random(seed ^ 0x5F100), modifier,
                                          realm_id=realm_id)
        GenerationMixin._grow_new_floors(cells, depth, random.Random(seed ^ 0x6F200), modifier,
                                         realm_id=realm_id)
        # 容器周围 5×5（半径 2）不做气体/液体的自然生成：容器封存的内容物
        # 在投放后才判定相邻，避免开局就被自然气团/液池淹没。
        containers = [
            (x, y)
            for y in range(1, height - 1)
            for x in range(1, width - 1)
            if cells[y][x].wall_kind in CONTAINER_KINDS
        ]
        for cx, cy in containers:
            for ny in range(max(1, cy - 2), min(height - 1, cy + 3)):
                for nx in range(max(1, cx - 2), min(width - 1, cx + 3)):
                    if (nx, ny) == (cx, cy):
                        continue
                    neighbor = cells[ny][nx]
                    if neighbor.solid:
                        continue
                    neighbor.liquid = 0
                    neighbor.liquid_kind = ""
                    neighbor.gas = 0
                    neighbor.gas_kind = ""
        # 暴露修复：容器可能落在贴空气墙的唯一开放邻格上把它封死——
        # 找到被封死的墙，把旁边一个容器还原为开放格。
        needs_exposure = EXPOSED_ONLY_WALLS | FEATURE_WALLS
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                cell = cells[y][x]
                if cell.wall_kind not in needs_exposure:
                    continue
                if any(
                    not cells[ny][nx].solid
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                    if 0 <= nx < width and 0 <= ny < height
                ):
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < width and 0 <= ny < height and cells[ny][nx].wall_kind in CONTAINER_KINDS:
                        GenerationMixin.clear_wall(cells[ny][nx])
                        break
        # Authored functional passages cannot acquire random containers or
        # damaging floor patches. Small decorative stamps keep their old rules.
        for placement in vault_placements:
            vault = placement.vault
            if not (vault.circuit or vault.npc_anchor or vault.event_anchor):
                continue
            for row, line in enumerate(vault.pattern):
                for col, ch in enumerate(line):
                    if ch not in ".@pw":
                        continue
                    cell = cells[placement.top + row][placement.left + col]
                    gas_protected.add((placement.left + col, placement.top + row))
                    if cell.wall_kind in CONTAINER_KINDS:
                        GenerationMixin.clear_wall(cell)
                    if vault.circuit or (row, col) == vault.npc_anchor:
                        cell.liquid, cell.liquid_kind = 0, ""
                        cell.gas, cell.gas_kind = 0, ""
                        cell.plant = 0
                        cell.aggregate_variant = "普通聚合物"
        if vault_sink is not None:
            vault_sink["natural_gas_protected"] = gas_protected
        if not realm_id and not defer_natural_gas:
            # Direct map-generation tools do not yet have a player entity.
            spawn = GenerationMixin._find_nonvault_spawn(
                cells, width//2, height//2,
                [p.region for p in vault_placements if p.vault.circuit or p.vault.npc_anchor
                 or (p.vault.width >= 10 and p.vault.height >= 10)])
            GenerationMixin._place_natural_gas(cells, seed, depth, modifier, spawn, gas_protected)
        # §12 E：光源场景组。独立随机流（seed ^ SCENE_SEED_SALT），只决定一小片
        # 同色光源落在哪；只改 Cell.plant，不新增墙体/液体/气体，也不占用唯一
        # 通路。保护格＝结构区整块、出生点 7×7、石台与 NPC 站位 5×5。
        from .light_scenes import place_light_scenes
        scene_protected: set[tuple[int, int]] = set()
        for left, top, right, bottom in (p.region for p in vault_placements):
            for sy in range(top, bottom + 1):
                for sx in range(left, right + 1):
                    scene_protected.add((sx, sy))
        spawn_hint = GenerationMixin._find_nonvault_spawn(
            cells, width // 2, height // 2,
            [p.region for p in vault_placements if p.vault.circuit or p.vault.npc_anchor
             or (p.vault.width >= 10 and p.vault.height >= 10)])
        for sy in range(spawn_hint[1] - 3, spawn_hint[1] + 4):
            for sx in range(spawn_hint[0] - 3, spawn_hint[0] + 4):
                scene_protected.add((sx, sy))
        if vault_sink is not None:
            for sx, sy in vault_sink.get("npc_spots", ()):
                for dy in (-2, -1, 0, 1, 2):
                    for dx in (-2, -1, 0, 1, 2):
                        scene_protected.add((sx + dx, sy + dy))
            for sx, sy in vault_sink.get("loot_cells", ()):
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        scene_protected.add((sx + dx, sy + dy))
        scene_report = place_light_scenes(
            cells, seed, depth, realm_id, protected=scene_protected,
        )
        if vault_sink is not None:
            vault_sink["light_scenes"] = scene_report
        # §12 F：三种环境设施（嵌壁梦灯/弧光灯架/余烬灯盏）。共用同一份保护格，
        # 额外按出生点净空与「只改造既有实心墙」两条约束落位——不改连通性。
        from .fixtures import place_light_fixtures
        fixture_report = place_light_fixtures(
            cells, seed, depth, realm_id,
            protected=scene_protected, spawn=spawn_hint,
        )
        if vault_sink is not None:
            vault_sink["light_fixtures"] = fixture_report
        return cells

    @staticmethod
    def _place_natural_gas(cells, seed, depth, modifier, spawn, protected=()):
        from .gas_generation import place_natural_gas
        # One equivalent mass budget replaces the former independent source roll.
        # Airtight has its own rate, rather than multiplying ordinary gas by three.
        return place_natural_gas(
            cells, random.Random(seed ^ 0x6A5C10), gas_pool_for_depth(depth),
            spawn=spawn, protected=protected, rate=.030 if modifier == '气密' else .012)

    @staticmethod
    def _assign_wall_kinds(
        rng: random.Random,
        solid_mask: list[list[bool]],
        width: int,
        height: int,
        depth: int,
        door_positions: "set[tuple[int, int]] | list[tuple[int, int]]" = (),
        vault_kinds: "dict[tuple[int, int], str] | None" = None,
        realm_id: str = "",
    ) -> dict[tuple[int, int], str]:
        """区域生长式墙体分配：同类墙连片，特殊墙低频。

        先把所有墙体默认为压实聚合墙，再用极低的色块预算把功能墙种成
        连通小片（外露专属墙只能在贴开放格的墙体上生长），避免逐格独立
        随机造成的椒盐式混杂。``vault_kinds`` 是模板指定的墙种覆写
        （石台/木桌子/整栋玻璃……），在色块生长之后应用、门位染色之前。
        """
        # 主墙体：1–10 压实聚合墙；11–20 坚硬聚合墙；21–27 为
        # 「70% 致密聚合物（四色各 1/4）+ 30% 梦魇岩」的逐格混合。
        if depth >= 21:
            base_pool = ("赤致密聚合墙", "黄致密聚合墙", "蓝致密聚合墙", "绿致密聚合墙", "梦魇岩")
            base_weights = (0.175, 0.175, 0.175, 0.175, 0.30)
        elif depth >= 11:
            base_pool = ("坚硬聚合墙",)
            base_weights = (1.0,)
        else:
            base_pool = ("压实聚合墙",)
            base_weights = (1.0,)
        base = base_pool[0]

        def pick_base() -> str:
            if len(base_pool) == 1:
                return base_pool[0]
            roll = rng.random()
            cursor = 0.0
            for kind, weight in zip(base_pool, base_weights):
                cursor += weight
                if roll < cursor:
                    return kind
            return base_pool[-1]

        pool = [kind for kind in wall_pool_for_depth(depth, realm_id=realm_id) if kind != "意识边界" and kind not in base_pool]
        # 《新材料》独立固体只在贴空气处生成（不埋进墙体内部）。
        exposed_required = EXPOSED_ONLY_WALLS | FEATURE_WALLS
        specials = [kind for kind in pool if kind != base]
        solid_cells = [(x, y) for y in range(1, height - 1) for x in range(1, width - 1) if solid_mask[y][x]]
        solid_set = set(solid_cells)
        for x in range(width):
            solid_set.add((x, 0))
            solid_set.add((x, height - 1))
        for y in range(height):
            solid_set.add((0, y))
            solid_set.add((width - 1, y))

        def is_exposed(x: int, y: int) -> bool:
            return any(
                (nx, ny) not in solid_set
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            )

        assigned: dict[tuple[int, int], str] = {(x, y): (pick_base() if len(base_pool) > 1 else base) for x, y in solid_cells}
        area = max(1, len(solid_cells))
        # 分配顺序：外露专属墙先播种（它们对可放置格的要求最苛刻），随后按
        # 色块预算从大到小——玻璃幕墙介于普通墙与功能墙之间，会先占满自己
        # 那份较大的预算，再轮到吸声墙与其他低频功能墙。
        prioritized = [kind for kind in specials if kind in exposed_required]
        prioritized += sorted(
            (kind for kind in specials if kind not in exposed_required),
            key=lambda kind: (-wall_spawn_budget(kind)[0], kind),
        )
        for kind in prioritized:
            allowed = solid_cells
            if kind in exposed_required:
                allowed = [cell for cell in solid_cells if is_exposed(*cell)]
            if not allowed:
                continue
            blob_cap, area_divisor, size_max = wall_spawn_budget(kind)
            blob_count = min(blob_cap, 1 + area // area_divisor)
            if kind in REGION_WALL_RANGES:
                # 条件限制：区域外按层数距离衰减（衰减到 0 不生成）。
                lo, hi, leak = REGION_WALL_RANGES[kind]
                blob_count = round(blob_count * region_falloff(depth, lo, hi, leak))
                if blob_count <= 0:
                    continue
            for _ in range(blob_count):
                if kind == "清醒石":
                    # 每次尝试只生成一个，且 5×5（切比雪夫距离 2）内不出现另一个。
                    candidates = [
                        cell for cell in allowed
                        if assigned.get(cell) in base_pool and not any(
                            abs(cell[0] - px) <= 2 and abs(cell[1] - py) <= 2
                            for (px, py), placed_kind in assigned.items()
                            if placed_kind == "清醒石"
                        )
                    ]
                    if not candidates:
                        continue
                    assigned[candidates[rng.randrange(len(candidates))]] = kind
                    continue
                size = rng.randint(min(3, max(1, size_max)), max(1, size_max))
                frontier = [allowed[rng.randrange(len(allowed))]]
                placed = 0
                while frontier and placed < size:
                    cell = frontier.pop(rng.randrange(len(frontier)))
                    if assigned.get(cell) not in base_pool:
                        continue
                    if kind in exposed_required and not is_exposed(*cell):
                        continue
                    assigned[cell] = kind
                    placed += 1
                    x, y = cell
                    neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                    rng.shuffle(neighbors)
                    frontier.extend(neighbor for neighbor in neighbors if neighbor in solid_set)
        # vault 指定墙种：整格覆写（食堂的长桌、温室的玻璃幕墙等），
        # 在色块生长之后、门位染色之前——门永远优先于模板指定。
        for position, kind in (vault_kinds or {}).items():
            if position in assigned:
                assigned[position] = kind
        # 门：在区域生长之后强制染成「门」，不被任何功能墙覆盖。
        for x, y in door_positions:
            if (x, y) in assigned:
                assigned[(x, y)] = "门"
        return assigned

    CONTAINER_KINDS = ("记忆容器", "思绪容器")
    #: 异常地点（石台/桌子上的事件）投放。
    #: 旧实现把池里的事件全部盖上，一层动辄 2–3 个台子；2026-09-15 改成
    #: 「每个候选独立掷 0.6」后，在十几个候选的池里又必然掷满，实际等于
    #: 固定 2 个。2026-10-22（E5后续 P1）改为**先抽数量再选种类**：
    #: 0／1／2 个 = 40%／50%／10%（期望 0.7），从主题池无放回选。
    #: 结构绑定事件（vault_info["events"]）先占额，随机投放只用**余额**
    #: （2026-10-27）；位面入口与珍品机会不在此口径内。
    EVENT_QUOTA_WEIGHTS = (0.40, 0.90, 1.00)
    EVENT_SPAWN_CHANCE = 0.6          # 已由 EVENT_QUOTA_WEIGHTS 取代，保留兼容
    #: 每层异常地点上限（与结构自带事件**共用**，见 ``data.events``）。
    #: 结构事件在盖章期先占额，本层的随机零散事件只在余额内补位。
    EVENT_MAX_PER_LAYER = _EVENT_MAX_PER_LAYER
    EVENT_MIN_PER_LAYER = 0           # 允许整层没有零散异常地点（40%）
    # 记忆碎片每层投放概率（2026-10-15 收紧）：旧版每层必出 2 件可拾取碎片
    # （出生远点固定一件 rain_machine_memory + 记忆池保底抽取一件）；现在每层
    # 掷一次、命中才投放、至多 1 件。NPC 交易与事件奖励的碎片不经这里，
    # 不受此约束；异象战利品的碎片另有每层同类预算（enemies 掉落预算=1）。
    MEMORY_FLOOR_CHANCE = 0.3
    #: 每层普通随机抽取次数（2026-10-22 保留 4 次；方案里「4 → 3」是后备档，
    #: 不与本轮固定件收敛同时生效，避免双重削减）。
    LOOT_ROLLS = 4
    #: 启动发射源：只在主梦首层、且行囊没有任何 ``unlock_fire`` 来源时补一次。
    SUPPLY_LAUNCHER_DEPTH = 1
    #: 启动恢复补给：只在前 3 层，按缺口挑一种。
    SUPPLY_RESTORE_MAX_DEPTH = 3
    #: 该资源占上限比例达到此值就视为「不缺」，不再补（避免满状态白送）。
    SUPPLY_RESTORE_MIN_RATIO = 0.6
    #: 恢复补给的候选表：(资源字段, 物品 ID)。三种都取既有常见件，
    #: 不为救济新增物品，也不额外三种全发。
    SUPPLY_RESTORE_TABLE = (
        ("lucidity", "clear_glass"),
        ("imagination", "warm_coffee"),
        ("mind", "warm_water"),
    )
    MEMORY_VESSEL_LIQUIDS = ("镇静溶液", "稀释记忆", "泪滴溶液", "水", "红酒")
    THOUGHT_VESSEL_GASES = ("水蒸气", "回声雾", "催眠雾", "酒气")
    # 地面容器生成率：按开放格计 0.4%（0.8% → 0.4%，两层下来容器过密，
    # 玩家几乎无处落脚）。空置率 10%：一成的容器是空壳，打开后什么也倒不出来。
    CONTAINER_SPAWN_CHANCE = 0.004
    CONTAINER_EMPTY_CHANCE = 0.10

    @staticmethod
    def _spawn_containers(
        cells: "list[list[Cell]]",
        rng: random.Random,
        wall_assignment: "dict[tuple[int, int], str]",
    ) -> None:
        """地面容器：独立的一趟投放，与植物/流体互不干扰。

        与旧实现（在流体那一趟里用同一个 rng 顺带掷出来）最大的区别是随机流
        分开了：这里由调用方传 ``random.Random(seed ^ 0x2C07A)``，容器密度与
        植物密度（``seed ^ 0x9147``）因此彻底解耦——调植物覆盖率不会平移容器
        落点，调容器密度也不会让植物位移。

        选址只看一个条件：四邻不能是「必须贴开放格」的外露专属墙，避免把必须
        露天的特殊墙围死（围死了后面还有一道暴露修复兜底）。
        """
        height, width = len(cells), len(cells[0])
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                cell = cells[y][x]
                if cell.solid or cell.wall_kind:
                    continue
                if rng.random() >= GenerationMixin.CONTAINER_SPAWN_CHANCE:
                    continue
                neighbor_kinds = {
                    wall_assignment.get((x + 1, y)),
                    wall_assignment.get((x - 1, y)),
                    wall_assignment.get((x, y + 1)),
                    wall_assignment.get((x, y - 1)),
                }
                if neighbor_kinds.isdisjoint(EXPOSED_ONLY_WALLS):
                    GenerationMixin.configure_container(cell, rng)

    @staticmethod
    def configure_container(cell: Cell, rng: random.Random) -> None:
        """地面容器：低矮固体，封存液体（记忆容器）或气体（思绪容器），
        完整度归零或徒手推倒时内容物留在原格并随流动散出。

        一成（``CONTAINER_EMPTY_CHANCE``）的容器是空壳：打开后什么也倒不出来。"""
        kind = "记忆容器" if rng.random() < 0.5 else "思绪容器"
        GenerationMixin.configure_wall(cell, kind)
        # 空置概率：一成的容器是空的（打开后什么也倒不出来），其余封存内容物。
        if rng.random() >= GenerationMixin.CONTAINER_EMPTY_CHANCE:
            amount = rng.randint(50, 90)
            if kind == "记忆容器":
                cell.liquid_kind = GenerationMixin.MEMORY_VESSEL_LIQUIDS[rng.randrange(len(GenerationMixin.MEMORY_VESSEL_LIQUIDS))]
                cell.liquid = amount
            else:
                cell.gas_kind = GenerationMixin.THOUGHT_VESSEL_GASES[rng.randrange(len(GenerationMixin.THOUGHT_VESSEL_GASES))]
                cell.gas = amount

    @staticmethod
    def _grow_plants(
        cells: "list[list[Cell]]",
        rng: random.Random,
        coverage: float,
        single_chance: float = SINGLE_PLANT_CHANCE,
        patch_min: int = PATCH_MIN_SIZE,
        patch_max: int = PATCH_MAX_SIZE,
        depth: int = 1,
        realm_id: str = "",
    ) -> None:
        """植物投放：连片为主、少量单株，只落在无液体的开放空地。

        覆盖率按可种植的开放格计算；「连片」用随机漫步生长——从一粒种子格
        出发，反复从已选集合里随机挑一格向邻格扩张，直到长满本片预算的规模。

        ``single_chance`` / ``patch_min`` / ``patch_max`` 是生成率的旋钮：
        单株概率越高、连片规模越小，地面就越零散（普通层即如此）。

        与地面容器完全独立：这一趟用 seed ^ 0x9147 的随机流，容器那趟用
        seed ^ 0x2C07A，两边的密度只决定自己那份；容器格（wall_kind 非空）
        对植物不可种植，所以植物绝不会长在容器上、更不会把容器顶掉。
        """
        height, width = len(cells), len(cells[0])

        def plantable(x: int, y: int) -> bool:
            cell = cells[y][x]
            return (
                1 <= x < width - 1 and 1 <= y < height - 1
                # 墙体与地面容器（wall_kind 非空）一律不可种植。
                and not cell.solid and not cell.wall_kind
                and cell.liquid == 0 and cell.plant == 0
                # 空白聚合物（梦还没画完的地面）不长植物——地板效果，见 materials/floors.py。
                and not floor_effect_for(cell).bare
            )

        open_cells = [
            (x, y)
            for y in range(1, height - 1)
            for x in range(1, width - 1)
            if plantable(x, y)
        ]
        target = int(len(open_cells) * coverage)
        planted = 0
        # 一次性释出株按通道封顶（docs 2026-10-26 §9.2）：按株计，不按格数分摊。
        # 超出时退回主梦白名单，不削减教学用的第 1 子层样板。
        release_used: dict[str, int] = {}
        release_total = 0
        release_limit = max(1, int(target * 0.2))
        while planted < target and open_cells:
            x, y = open_cells.pop(rng.randrange(len(open_cells)))
            if not plantable(x, y):
                continue
            # 稀有魔法植物门：逐 patch 先掷 0.8%，命中且该植物层数衰减权重 > 0
            # 才生成稀有植物——单株为主（85%），极少连成 2 格。
            # 长位面不掷稀有门：主梦那批功能植物（曼德拉草/缚魂藤…）不得
            # 跨支线混进图书馆与疗所，位面专属才是主视觉。
            rare = (None if realm_id in REALM_LOCAL_PLANTS else
                    rare_plant_kind(rng.random(), depth, region_falloff, realm_id=realm_id))
            # 2026-09-19 修复：区域衰减已经由 rare_plant_kind 的「种类筛选」
            # 承担（衰减到 0 的种类根本不会被抽中），不再二次乘到概率上——
            # 旧写法把 0.8% 的门再压到 0.2%~0.9%，多数整层颗粒无收。
            if rare is not None and rng.random() < RARE_PLANT_CHANCE:
                cells[y][x].plant = rare.code
                planted += 1
                if rng.random() < RARE_PLANT_SINGLE_CHANCE or planted >= target:
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if plantable(nx, ny) and rng.random() < 0.5:
                        cells[ny][nx].plant = rare.code
                        planted += 1
                        break
                continue
            if rng.random() < single_chance:
                patch_size = 1
            else:
                patch_size = rng.randint(min(patch_min, patch_max), patch_max)
            patch = 0
            frontier = [(x, y)]
            while frontier and patch < patch_size:
                cx, cy = frontier.pop(rng.randrange(len(frontier)))
                if not plantable(cx, cy):
                    continue
                # 长位面（千禧园/藏书宫/疗所）走本位面池：默认 90% 专属、
                # 10% 主梦白名单，跨支线专属一律为 0（docs §9.1）。
                if realm_id in REALM_LOCAL_PLANTS:
                    kind = realm_plant_kind(rng.random(), realm_id)
                    channel = _release_channel(kind)
                    if channel:
                        cap = _RELEASE_CHANNEL_CAPS.get(channel, 0)
                        if (release_total >= release_limit
                                or release_used.get(channel, 0) >= cap):
                            # 本层这一通道已经够了：换回主梦白名单的普通株。
                            kind = plant_kind(rng.random(), realm_id=realm_id)
                        else:
                            release_used[channel] = release_used.get(channel, 0) + 1
                            release_total += 1
                else:
                    kind = plant_kind(rng.random(), realm_id=realm_id)
                # 错帧片/散页脊有三成是还没立起来的 H1 收拢态（docs §10.1）：
                # 催生因此有真实用途，而立起态仍是这一层的主视觉。
                young = _YOUNG_FORM_FOR.get(kind.code)
                if young and rng.random() < YOUNG_FORM_CHANCE:
                    kind = plant_def_for(young)
                cells[cy][cx].plant = kind.code
                _stamp_plant_state(cells[cy][cx], kind, cx, cy)
                patch += 1
                planted += 1
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if plantable(nx, ny):
                        frontier.append((nx, ny))

    # 稀有地板种类与生成参数：覆盖约 2% 的开放空地（2026-09-19 自 3% 下调），
    # 每片 6~20 格连片；不足最小片规模的候选位置直接放弃（宁缺毋滥，绝不成单格散点）。
    # 「精致」修饰符按倍率放大（见 _floor_coverage_for）。
    RARE_FLOOR_VARIANTS = ("木质聚合物", "海绵聚合物", "金属聚合物", "灼热聚合物")
    RARE_FLOOR_COVERAGE = 0.02
    RARE_FLOOR_MIN_PATCH = 4

    # Excel 新一批地板（2026-09-18）：区域登记 (起始层, 终止层, 渗出)，
    # 生成走与稀有地板相同的连片算法，覆盖率更低（约 1.8%）。
    NEW_FLOOR_RANGES = {
        "梦境绒毯": (1, 12, 2),
        "冰面": (1, 20, 2),
        "星图地": (8, 20, 2),
        "书页地": (1, 12, 2),
        "月壤": (14, 27, 2),
        "棋盘格地板": (1, 27, 2),
        "绝热层": (1, 27, 2),
        "压电地板": (11, 27, 2),
        # 传送带四向（扩展包 v1）：全区域低频生成，方向随机四选一。
        "传送带·北": (1, 27, 3),
        "传送带·东": (1, 27, 3),
        "传送带·南": (1, 27, 3),
        "传送带·西": (1, 27, 3),
    }
    NEW_FLOOR_COVERAGE = 0.012

    @staticmethod
    def _floor_coverage_for(base: float, modifier: str) -> float:
        """地板覆盖率按修饰符调整：精致层大幅提升特殊/稀有地板产出。"""
        if modifier == "精致":
            return base * 3.0
        return base

    # 液体自然生成的地势权重，下标 = 地势 0/1/2/3（mapgen.elevation 生成 0–3）。
    # 最低处（1）权重拉满——液体本该汇在这一档；真正的洼底（0）反而偏低，
    # 因为 0 常与 1 连成整片水洼，压低它能让水面更像「一汪」而不是整层铺开。
    # 地势 2 几乎不存水，最高处（3）只留一丝为 0.01（不再绝对为 0，允许极偶发
    # 的高处积水，作为景观意外）。注意这是「掷中液体之后的成形概率」，不改变
    # 液体总量（liquid_rate）。
    LIQUID_ELEVATION_WEIGHTS = (0.15, 1.0, 0.06, 0.01)

    @staticmethod
    def _grow_rare_floors(cells: "list[list[Cell]]", rng: "random.Random", modifier: str = "",
                          realm_id: str = "") -> None:
        """稀有地板：整片收集后再落色，保证每片都连成规模。

        改写任何一种**非稀有**开放地面（普通/柔软/粗糙/反光/吸声/空白聚合物）
        的地板变体——它们是地毯式的地面材质而不是障碍，绝不改变通行性；变体
        各自带一点点不造成伤害的小效果（见 materials/floors.py 的 FloorDef）。生长时避开其他稀有变体的格子，片与片之间隔着原有
        地面，不会彼此粘连成杂色。

        早先这里只肯改写「普通聚合物」，而普通聚合物仅占开放地面约六分之一，
        于是 3% 的覆盖率实际被打成约 0.5%（实测每种稀有地板每层只有 1~3 格，
        玩家几乎见不到）。改为对整片开放地面取样后，覆盖率才真正落在 3% 上。
        """
        from collections import deque

        height, width = len(cells), len(cells[0])

        def reskinable(x: int, y: int, variant: str | None = None) -> bool:
            cell = cells[y][x]
            if not (
                1 <= x < width - 1 and 1 <= y < height - 1
                and not cell.solid and not cell.wall_kind
                and cell.aggregate_variant not in GenerationMixin.RARE_FLOOR_VARIANTS
            ):
                return False
            if variant is not None:
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    neighbor_variant = cells[ny][nx].aggregate_variant
                    if neighbor_variant in GenerationMixin.RARE_FLOOR_VARIANTS and neighbor_variant != variant:
                        return False
            return True

        candidates = [
            (x, y)
            for y in range(1, height - 1)
            for x in range(1, width - 1)
            if reskinable(x, y)
        ]
        target = int(
            len(candidates)
            * GenerationMixin._floor_coverage_for(GenerationMixin.RARE_FLOOR_COVERAGE, modifier)
        )
        reskinned = 0
        # 变体取用走「洗牌—轮转」：每一轮四种各取一次，取空再洗牌。
        # 旧实现每片独立掷骰，运气差时一整层只有一种（玩家实测「稀有地板
        # 全是灼热聚合物」）；轮转后同层内相邻两片必然换色，长期比例也严格
        # 均等（每四片四种各一次），不会再出现某种一家独大。
        variant_cycle: list[str] = []

        # 位面专属地板不进主梦池（FloorDef.spawn_realms 与墙/液/气同口径）。
        from ..materials.floors import FLOOR_DEFINITIONS as _FLOOR_DEFS
        rare_pool = tuple(
            v for v in GenerationMixin.RARE_FLOOR_VARIANTS
            if not _FLOOR_DEFS[v].spawn_realms or realm_id in _FLOOR_DEFS[v].spawn_realms
        )

        def next_variant() -> str:
            if not variant_cycle:
                variant_cycle.extend(rare_pool)
                rng.shuffle(variant_cycle)
            return variant_cycle.pop()

        while reskinned < target and candidates:
            x, y = candidates.pop(rng.randrange(len(candidates)))
            if not reskinable(x, y):
                continue
            variant = next_variant()
            patch_size = rng.randint(6, 20)
            # 先整片收集（只经由合法格扩散），成片才落色。
            collected: list[tuple[int, int]] = []
            seen = {(x, y)}
            queue = deque([(x, y)])
            while queue and len(collected) < patch_size:
                cx, cy = queue.popleft()
                if not reskinable(cx, cy, variant):
                    continue
                collected.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (nx, ny) not in seen and reskinable(nx, ny, variant):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if len(collected) < GenerationMixin.RARE_FLOOR_MIN_PATCH:
                continue
            for cx, cy in collected:
                cells[cy][cx].aggregate_variant = variant
            reskinned += len(collected)

    @staticmethod
    def _grow_new_floors(cells: "list[list[Cell]]", depth: int, rng: "random.Random", modifier: str = "",
                         realm_id: str = "") -> None:
        """Excel 新一批地板：与稀有地板同款的连片生长，但按区域衰减选种。

        每片从「本层可用变体」里轮转取色（与 _grow_rare_floors 的洗牌—轮转
        一致），保证同层内片与片换色；区域外（渗出范围内）权重按
        region_falloff 衰减，衰减到 0 的变体根本不会出现在本层。
        """
        from collections import deque

        from ..mapgen import region_falloff
        from ..materials.floors import FLOOR_DEFINITIONS

        height, width = len(cells), len(cells[0])
        pool: list[tuple[str, float]] = []
        for variant, (lo, hi, leak) in GenerationMixin.NEW_FLOOR_RANGES.items():
            # 位面专属地板不进主梦池（FloorDef.spawn_realms 与墙/液/气同口径）。
            floor_definition = FLOOR_DEFINITIONS.get(variant)
            if (floor_definition is not None and floor_definition.spawn_realms
                    and realm_id not in floor_definition.spawn_realms):
                continue
            weight = region_falloff(depth, lo, hi, leak)
            if weight > 0:
                pool.append((variant, weight))
        if not pool:
            return

        def reskinable(x: int, y: int, variant: str | None = None) -> bool:
            # 2026-09-19 修复：普通聚合物同样是可改写的基底地面（旧条件把它
            # 排除，导致绝大多数开放格不合格、新地板整层绝迹）。
            cell = cells[y][x]
            if not (
                1 <= x < width - 1 and 1 <= y < height - 1
                and not cell.solid and not cell.wall_kind
                and cell.aggregate_variant not in GenerationMixin.RARE_FLOOR_VARIANTS
                and cell.aggregate_variant not in GenerationMixin.NEW_FLOOR_RANGES
            ):
                return False
            if variant is not None:
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    neighbor = cells[ny][nx].aggregate_variant
                    if (
                        neighbor in GenerationMixin.RARE_FLOOR_VARIANTS
                        or neighbor in GenerationMixin.NEW_FLOOR_RANGES
                    ) and neighbor != variant:
                        return False
            return True

        candidates = [
            (x, y)
            for y in range(1, height - 1)
            for x in range(1, width - 1)
            if reskinable(x, y)
        ]
        target = int(
            len(candidates)
            * GenerationMixin._floor_coverage_for(GenerationMixin.NEW_FLOOR_COVERAGE, modifier)
        )
        reskinned = 0
        variant_cycle: list[str] = []

        def next_variant() -> str:
            if not variant_cycle:
                # 加权洗牌轮转：权重高的变体在本层出现更多片，但每种都可能出现。
                weighted: list[str] = []
                for name, weight in pool:
                    weighted.extend([name] * max(1, round(weight * 2)))
                rng.shuffle(weighted)
                variant_cycle.extend(weighted)
            return variant_cycle.pop()

        while reskinned < target and candidates:
            x, y = candidates.pop(rng.randrange(len(candidates)))
            if not reskinable(x, y):
                continue
            variant = next_variant()
            patch_size = rng.randint(6, 16)
            collected: list[tuple[int, int]] = []
            seen = {(x, y)}
            queue = deque([(x, y)])
            while queue and len(collected) < patch_size:
                cx, cy = queue.popleft()
                if not reskinable(cx, cy, variant):
                    continue
                collected.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (nx, ny) not in seen and reskinable(nx, ny, variant):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if len(collected) < GenerationMixin.RARE_FLOOR_MIN_PATCH:
                continue
            for cx, cy in collected:
                cells[cy][cx].aggregate_variant = variant
            reskinned += len(collected)

    @staticmethod
    def _find_nonvault_spawn(cells, preferred_x, preferred_y, regions=(), margin=0):
        height, width = len(cells), len(cells[0])
        if not any(a-margin <= preferred_x <= c+margin and b-margin <= preferred_y <= d+margin
                   for a,b,c,d in regions):
            return GenerationMixin._find_open_cell(cells,preferred_x,preferred_y)
        candidates = ((x,y) for y in range(1,height-1) for x in range(1,width-1)
                      if not cells[y][x].solid
                      and not any(a-margin <= x <= c+margin and b-margin <= y <= d+margin
                                  for a,b,c,d in regions))
        return min(candidates, default=GenerationMixin._find_open_cell(cells,preferred_x,preferred_y),
                   key=lambda p: (abs(p[0]-preferred_x)+abs(p[1]-preferred_y),p[1],p[0]))

    @staticmethod
    def _find_open_cell(cells: list[list[Cell]], preferred_x: int, preferred_y: int) -> tuple[int, int]:
        height = len(cells)
        width = len(cells[0])
        for radius in range(max(width, height)):
            for y in range(max(1, preferred_y - radius), min(height - 1, preferred_y + radius + 1)):
                for x in range(max(1, preferred_x - radius), min(width - 1, preferred_x + radius + 1)):
                    if not cells[y][x].solid:
                        return x, y
        return 1, 1

    def _reachable_open_cells(self) -> "set[tuple[int, int]]":
        """从玩家所在地做 4 连通洪水填充（门视为可通行），返回可走到的格。

        只服务于「普通散投必须拿得到」这一口径：E5 实测同批生成物只有 52.9%
        在入层时可达，其中多数落在被实墙封住、要破障才能进的分区里。
        **密室珍品是明确设计的不可达**，所以这里不动石台/结构锚点的落位，
        只把随机散投的候选限制在玩家当前能走到的地方。
        """
        width, height = self.width, self.height
        start = (self.player.x, self.player.y)
        cell = self.cell(*start)
        if cell.solid and cell.wall_kind != "门":
            return set()
        seen = {start}
        queue = [start]
        for x, y in queue:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 < nx < width - 1 and 0 < ny < height - 1):
                    continue
                if (nx, ny) in seen:
                    continue
                other = self.cell(nx, ny)
                if other.solid and other.wall_kind != "门":
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))
        return seen

    def _distributed_open_cells(self, count: int, seed: int, excluded=()) -> list[tuple[int, int]]:
        """Choose deterministic spawn cells spread across the reachable map.

        2026-10-22（E5后续 P1）：候选加上「从玩家可走到」的限制。可达格不足以
        放下全部物件时退回旧口径（宁可盖满也不静默少发），所以不会因为分区
        太碎而减少投放量。
        """
        open_cells = [
            (x, y)
            for y in range(1, self.height - 1)
            for x in range(1, self.width - 1)
            if not self.cell(x, y).solid
            and (x, y) not in excluded
            and max(abs(x - self.player.x), abs(y - self.player.y)) >= 4
        ]
        reachable = self._reachable_open_cells()
        reachable_cells = [position for position in open_cells if position in reachable]
        candidates = reachable_cells if len(reachable_cells) >= count else open_cells
        rng = random.Random(seed)
        rng.shuffle(candidates)
        candidates.sort(key=lambda pos: (
            max(abs(pos[0] - self.player.x), abs(pos[1] - self.player.y)),
            rng.random(),
        ), reverse=True)
        selected: list[tuple[int, int]] = []
        min_gap = max(2, min(self.width, self.height) // 5)
        for position in candidates:
            if all(max(abs(position[0] - other[0]), abs(position[1] - other[1])) >= min_gap for other in selected):
                selected.append(position)
                if len(selected) >= count:
                    return selected
        for position in candidates:
            if position not in selected:
                selected.append(position)
                if len(selected) >= count:
                    break
        return selected

    def _top_up_spawn_points(self, points, count: int, excluded=()) -> list[tuple[int, int]]:
        """开局点名落点不够时按「离出生点由近到远」补开放格，结果保持确定性。

        ``_distributed_open_cells`` 的「离玩家 ≥4 格」在边界尺寸上是硬约束：
        15×11 只有约 11 个合格格，而去重后要点 12 只（3 固定 + 9 随机）。
        小图上离得近总比少放一只强，所以这里允许更近；但墙、排除格（模板 NPC
        占位）、已占格与玩家自己所在格一律跳过，不会把异象塞进墙里、叠在同一格
        或直接站在玩家脚下。补不满就原样返回，由调用方收敛名单。
        """
        if len(points) >= count:
            return list(points)
        taken = set(points) | set(excluded) | {(self.player.x, self.player.y)}
        px, py = self.player.x, self.player.y
        ring = sorted(
            ((x, y) for y in range(1, self.height - 1) for x in range(1, self.width - 1)),
            key=lambda pos: (max(abs(pos[0] - px), abs(pos[1] - py)), pos[0], pos[1]),
        )
        filled = list(points)
        for position in ring:
            if len(filled) >= count:
                break
            if position in taken or self.cell(position[0], position[1]).solid:
                continue
            filled.append(position)
            taken.add(position)
        return filled

    @staticmethod
    def _repair_connectivity(
        cells: list[list[Cell]],
        start_x: int,
        start_y: int,
        protected: "list[tuple[int, int, int, int]] | None" = None,
        precious: "list[tuple[int, int]] | None" = None,
    ) -> None:
        """把每个与出生点不连通的开放格用最短通道接回来。

        门（``wall_kind=="门"``）被视为可通行——它本就被设计成由生物/物品
        踏上即开，所以门所连接的两侧区域应视为可达，连接修复时不应把门凿穿
        成普通地面（否则门就消失了）。

        ``protected``（vault 保护罩）内的实心格不可凿——修复通道从区域外
        绕行（或借用区域内已有的开放格），模板的封闭形状与开口被尊重；
        ``precious``（loot 石台等贵重格）任何情况下都不可凿。绕行失败时
        无法绕行的封闭模板保持原状，由机关或作者设计的入口解锁。
        """
        from collections import deque

        height, width = len(cells), len(cells[0])
        blocked: set[tuple[int, int]] = set()
        for pl, pt, pr, pb in protected or ():
            for y in range(max(0, pt), min(height, pb + 1)):
                for x in range(max(0, pl), min(width, pr + 1)):
                    blocked.add((x, y))
        precious_set = set(precious or ())

        def passable(cell: Cell) -> bool:
            return not cell.solid or cell.wall_kind == "门"

        def reachable() -> set[tuple[int, int]]:
            seen = {(start_x, start_y)}
            queue = [(start_x, start_y)]
            for x, y in queue:
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < width and 0 <= ny < height and passable(cells[ny][nx]) and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            return seen

        unrepairable: set[tuple[int, int]] = set()
        for _ in range(width * height):
            seen = reachable()
            disconnected = [
                (x, y)
                for y in range(1, height - 1)
                for x in range(1, width - 1)
                if passable(cells[y][x]) and (x, y) not in seen
                and (x, y) not in blocked and (x, y) not in unrepairable
            ]
            if not disconnected:
                return
            target = disconnected[0]
            anchor = min(seen, key=lambda pos: abs(pos[0] - target[0]) + abs(pos[1] - target[1]))
            prev: dict[tuple[int, int], tuple[int, int] | None] = {anchor: None}
            queue = deque([anchor])
            while queue:
                current = queue.popleft()
                if current == target:
                    break
                cx, cy = current
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if not (0 < nx < width - 1 and 0 < ny < height - 1):
                        continue
                    if (nx, ny) in prev:
                        continue
                    if not passable(cells[ny][nx]) and ((nx, ny) in blocked or (nx, ny) in precious_set):
                        continue  # 保护区/贵重格的实心格：不可凿。
                    prev[(nx, ny)] = current
                    queue.append((nx, ny))
            if target in prev:
                node: tuple[int, int] | None = target
                while node is not None:
                    px, py = node
                    cell = cells[py][px]
                    if cell.solid and cell.wall_kind != "门":
                        GenerationMixin.clear_wall(cell)
                    node = prev[node]
            else:
                # A locked reward wing is intentionally disconnected. Never
                # carve through its authored gate as a connectivity fallback.
                pending = [target]
                unrepairable.add(target)
                for x, y in pending:
                    for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                        if (0 < nx < width-1 and 0 < ny < height-1
                                and (nx,ny) not in unrepairable and passable(cells[ny][nx])):
                            unrepairable.add((nx,ny))
                            pending.append((nx,ny))

    @classmethod
    def new(
        cls, seed: int = 1, width: int = 60, height: int = 60,
        starting_memory: str | None = None, tutorial: bool = False,
        run_options: dict | None = None, dream_type: dict | None = None,
        difficulty_revision: int = CURRENT_DIFFICULTY_REVISION,
        run_uid: str | None = None,
    ) -> "GameState":
        # tutorial=True：新开局进入 0 层「梦的起始」（固定教学图 + 引导步骤表），
        # 下面的梦层 1 常规生成照常跑完（保证与旧档同构的初始化），随后整体被教学图替换。
        # 测试模式与既有测试默认 False，仍直接从梦层 1 开局。
        base_width, base_height = width, height
        map_form = layer_form_for(seed, 1)
        modifier = layer_modifier_for(seed, 1)
        # 第一层固定为规整层型，尺寸就是基准尺寸；这里仍走统一入口，方便将来放开首层限制。
        width, height = layer_dimensions(width, height, map_form, seed, modifier)
        vault_info: dict = {}
        cells = cls._generate_cells(seed, width, height, map_form, modifier=modifier, vault_sink=vault_info, realm_id="", defer_natural_gas=True)
        # §12 E：本层光源场景组的审计结论（生成报告/测试读；不进存档）。
        state_light_scenes = vault_info.get("light_scenes", {})
        # §12 F：本层环境设施（灯具）的投放审计结论。
        state_light_fixtures = vault_info.get("light_fixtures", {})
        px, py = width // 2, height // 2
        if any(a-1 <= px <= c+1 and b-1 <= py <= d+1
               for a,b,c,d in vault_info.get("spawn_regions", ())):
            px, py = cls._find_nonvault_spawn(cells, px, py, vault_info["spawn_regions"], margin=1)
        for y in range(max(1, py - 1), min(height - 1, py + 2)):
            for x in range(max(1, px - 1), min(width - 1, px + 2)):
                cls.clear_wall(cells[y][x])
                # 出生 3×3 同时清空气体/液体/植物：clear_wall 只清墙体与植物，
                # 不碰流体，否则玩家可能一睁眼就泡在危害里（如催眠雾），开局即被结算征兆。
                cells[y][x].gas = 0
                cells[y][x].gas_kind = ""
                cells[y][x].liquid = 0
                cells[y][x].liquid_kind = ""
        cls._repair_connectivity(
            cells, px, py,
            protected=vault_info.get("regions"),
            precious=vault_info.get("loot_cells"),
        )
        cells[py][px].liquid = 0
        cells[py][px].liquid_kind = ""
        cells[py][px].gas = 0
        cells[py][px].gas_kind = ""
        cells[py][px].plant = 0
        cls._place_natural_gas(cells, seed, 1, modifier, (px, py),
                               vault_info.get('natural_gas_protected', ()))
        player = Entity("player", "我", px, py, integrity=1, relation="受控意识", glyph="❤ ")
        state = cls(width, height, seed, cells, player, theme=LAYER_THEMES[0], map_form=map_form, layer_modifier=modifier, base_width=width, base_height=height)
        state.light_scene_report = state_light_scenes
        state.difficulty_revision = max(0, int(difficulty_revision))
        from copy import deepcopy
        state.run_start_choices = {"run_options": deepcopy(run_options or {}),
                                   "dream_type": deepcopy(dream_type),
                                   "starting_memory": starting_memory,
                                   "width": base_width, "height": base_height}
        state.light_fixture_report = state_light_fixtures
        # Generation happened at time zero, not lazily on the first player turn.
        for row in cells:
            for cell in row:
                state._prime_material_clocks(cell)
        # 本局稳定身份前缀（§13.2）：actor_uid／task_uid／fact_uid 全部以它开头。
        # 后缀取生成时刻，同一种子开两局也不会互相认成同一局；它不参与任何数值。
        # run_uid 可显式传入（网页端无头黄金测试需要同种子完全可复现，
        # 见 dream_web/shell.py）；默认取生成时刻——同种子开两局不互相认成
        # 同一局，它不参与任何数值（run_uid 派生流的消费方见
        # library_abilities / main_learning / main_difficulty / tactical_layouts）。
        state.run_uid = run_uid or f"r{seed}-{int(time.time_ns()) % 10_000_000_000:x}"
        state.world_ledger.run_uid = state.run_uid
        # 开局选项（2026-10-09）必须在敌人生成**之前**落地：异象完整度缩放读
        # run_mods，选项还没生效时生成的异象永远是中性强度。
        from .settlement import REASON_RESTORE_SCENE, settle_delta
        if run_options:
            from .run_options import apply_run_options

            apply_run_options(state, run_options)
        settle_delta(state, 'mind', state.max_mind - state.mind,
                     reason=REASON_RESTORE_SCENE, source='新局初始化', channel='new_game')
        settle_delta(state, 'lucidity', state.max_lucidity - state.lucidity,
                     reason=REASON_RESTORE_SCENE, source='新局初始化', channel='new_game')
        settle_delta(state, 'imagination', state.max_imagination - state.imagination,
                     reason=REASON_RESTORE_SCENE, source='新局初始化', channel='new_game')
        if dream_type is not None:
            from .dream_types import apply_birth_choice
            apply_birth_choice(state, dream_type)
        # 逻辑固体（内容扩展包 v1）：首层的布线/压力地板/陷阱场景在这里落地。
        state._apply_logic_layout(vault_info.get("logic"))
        # 与生俱来的洞察（双读）开局即带在身上：不占用任何授予通道，也不发提示。
        state._ensure_innate_insights()
        # First-layer enemies obey the same eligibility as later generation.
        # One extra weak creature preserves 100 dissolution under default density
        # after replacing the old, stronger fixed roster.
        extra_count = state._ordinary_anomaly_count(9) if width >= 15 and height >= 11 else 0
        pool = anomaly_pool_for_depth(1)
        opening_rng = random.Random(seed ^ 0x7A11C)
        spawn_ids = ["anomaly.page_hound", "anomaly.folded_person", "anomaly.insomniac_alarm"]
        spawn_ids += opening_rng.choices([key for key, _ in pool],
                                         weights=[weight for _, weight in pool], k=extra_count)
        struct_npc_cells = {pos for pos, _ in vault_info.get("structure_npcs", ())}
        if width < 15 or height < 11:
            spawn_points = [(max(1, px - 4), py), (min(width - 2, px + 4), min(height - 2, py + 2)), (min(width - 2, px + 6), max(1, py - 3))]
        else:
            spawn_points = state._distributed_open_cells(
                len(spawn_ids), seed ^ 0x51A7, excluded=struct_npc_cells)
        # 小图容量：15×11 这类边界尺寸归「常规生成」分支，会按 9 只随机异象点名
        # （3 固定 + 9 = 12 个落点），但离出生点 ≥4 格的开放格只有 11 个——
        # 旧代码直接 spawn_points[index] 就 IndexError（seed=101、15×11 可复现）。
        # 先按「离出生点由近到远」补开放格（小图上离得近总比少放一只强），
        # 真补不满再收敛名单：宁可少放异象，也不能让生成中途炸在数组越界上。
        spawn_points = state._top_up_spawn_points(spawn_points, len(spawn_ids), struct_npc_cells)
        if len(spawn_points) < len(spawn_ids):
            spawn_ids = spawn_ids[:len(spawn_points)]
        for index, catalog_id in enumerate(spawn_ids):
            x, y = spawn_points[index]
            # 2026-10-22 前期铺坡：首层补充异象同样抬到 2 点完整度，
            # 否则新局首层仍会与 1 血普通异象混编，3→4 层的跳档未真正抹平。
            overrides = {"integrity": 2} if index >= 3 else {}
            state.add_defined_enemy(catalog_id, x, y, **overrides)
        state._seed_layer_contents(vault_info)
        from .main_difficulty import install_progress_site
        if not tutorial:
            install_progress_site(state)
        if starting_memory and starting_memory in ITEM_DEFINITIONS and ITEM_DEFINITIONS[starting_memory]["category"] == "记忆碎片":
            state.memory_fragments.append(starting_memory)
            # 开局携带的碎片同样要落效果（上限提升必须同步抬高，见 _apply_memory_effect）。
            state._apply_memory_effect(starting_memory)
            state.messages.append(tr("你携着「{item}」的残响入梦。", item=tr(ITEM_DEFINITIONS[starting_memory]["name"])))
        # 玩家地图知识（docs §1 第一批）：新局写入规则版本并记录开局正常视野。
        from .vision.knowledge import initialize_map_knowledge
        if tutorial:
            state._start_origin_tutorial()
            state.messages.append(tr("你在梦的起始醒来。跟随左侧的引导，或随时按 N 下潜。"))
            state.observe_visible_catalog()
            state._update_doors()
            initialize_map_knowledge(state)
            return state
        state.messages.append(tr("进入梦层 {depth}。崩解度 0/100。", depth=state.depth))
        state.observe_visible_catalog()
        state._update_doors()
        initialize_map_knowledge(state)
        return state

    # vault 中央石台的稀有物品：特殊件固定入池，携带意象按层取区域池
    # （2026-10-07 数值平衡改版——旧固定表在 20 层的石台上还摆 +1 钢笔）。
    VAULT_LOOT_SPECIAL_IDS = (
        "echo_emitter", "lighthouse_lens", "mirror_shard", "clear_glass",
        "spellbook", "torn_page",
    )
    # 兼容别名：外部脚本（export_full_excel）沿此名引用石台通道。
    VAULT_LOOT_IDS = VAULT_LOOT_SPECIAL_IDS

    @staticmethod
    def _open_cells_connected(
        cells: list[list[Cell]],
        start_x: int,
        start_y: int,
        blocked: "tuple[int, int] | None" = None,
    ) -> bool:
        """从起点做 4 连通洪水填充（门视为可通行），判断是否所有开放格都可达。

        ``blocked`` 用于「假设某格变实心」的试算：把该格从可通行集合里排除后
        再判连通。石台是实心固体，若它正好压在两个区域唯一的斜向通路枢纽上，
        就会把一片区域封死——四邻全开并不能排除这种情况（四邻之间只有斜向
        相邻，绕不过去），所以落脚前必须先试算连通性。
        """
        height, width = len(cells), len(cells[0])

        def passable(x: int, y: int) -> bool:
            if blocked is not None and (x, y) == blocked:
                return False
            cell = cells[y][x]
            return not cell.solid or cell.wall_kind == "门"

        seen = {(start_x, start_y)}
        queue = [(start_x, start_y)]
        for x, y in queue:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height and passable(nx, ny) and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return not any(
            passable(x, y) and (x, y) not in seen
            for y in range(1, height - 1)
            for x in range(1, width - 1)
        )

    def _place_event_site(self, preferred_x: int, preferred_y: int, protected=()) -> tuple[int, int]:
        """Place a reachable event without sealing passages or entering vaults.

        Locked reward wings are deliberately disconnected. Check preservation
        of the player's existing component, rather than demanding a globally
        connected map. Each candidate is visited once; unsuccessful platform
        searches fall back to an ordinary floor event.
        """
        height, width = len(self.cells), len(self.cells[0])
        start = (self.player.x, self.player.y)
        regions = list(protected or ()) + [b["region"] for b in self.circuit_boards if b.get("region")]
        occupied = {(e.x,e.y) for e in self.enemies if e.integrity > 0}
        occupied.update((e.x,e.y) for e in self.events)
        occupied.update((e.x,e.y) for e in self.world_items)

        def neighbors(p):
            x,y=p
            return ((x+1,y),(x-1,y),(x,y+1),(x,y-1))

        def passable(p):
            x,y=p
            return (0 <= x < width and 0 <= y < height
                    and (not self.cells[y][x].solid or self.cells[y][x].wall_kind == "门"))

        accessible = {start}
        queue = [start]
        for p in queue:
            for q in neighbors(p):
                if q not in accessible and passable(q):
                    accessible.add(q);queue.append(q)
        floors = sorted((p for p in accessible
                         if 0 < p[0] < width-1 and 0 < p[1] < height-1
                         and not self.cell(*p).solid and not self.cell(*p).wall_kind
                         and not self.cell(*p).wire and p not in occupied
                         and not any(a <= p[0] <= c and b <= p[1] <= d for a,b,c,d in regions)),
                        key=lambda p:(max(abs(p[0]-preferred_x),abs(p[1]-preferred_y)),p[1],p[0]))
        candidates = [p for p in floors if self.cell(*p).liquid <= 0
                      and max(abs(p[0]-start[0]),abs(p[1]-start[1])) > 2]
        for p in candidates[:256]:
            adjacent = set(neighbors(p))
            if not all(q in accessible and not self.cell(*q).solid and not self.cell(*q).wall_kind
                       for q in adjacent):
                continue
            # Removing p preserves its whole connected component precisely
            # when all of its neighbors remain connected to one another.
            origin = next(iter(adjacent));seen = {origin};pending = [origin]
            needed = adjacent - seen
            for q in pending:
                for r in neighbors(q):
                    if r != p and r in accessible and r not in seen:
                        seen.add(r);pending.append(r);needed.discard(r)
                if not needed:
                    self.configure_wall(self.cell(*p), "石台")
                    return p
        return (candidates or floors or [start])[0]

    def _spawn_bound_events(self, vault_info: "dict | None") -> None:
        """结构绑定事件：vault_info["events"] 落成 WorldEvent（不占随机配额）。

        定义带 ``scene`` 的（§8 S23 青灯入口）不落成普通 WorldEvent，改交给
        ``core.scenes.install_bound_scene``：它把 vault 指定的锚点当成设施原点，
        挂出带命令面板的场景事件，门态由设施记录自己记（§12.1）。
        """
        from .scenes import install_bound_scene

        for entry in (vault_info or {}).get("events", ()):
            definition = next(
                (candidate for candidate in EVENT_DEFINITIONS if candidate["event_id"] == entry["event_id"]),
                None,
            )
            if definition is None:
                continue
            scene_id = definition.get("scene")
            if scene_id:
                install_bound_scene(self, scene_id, entry["x"], entry["y"])
                continue
            instance_id = definition["event_id"]
            if any(e.event_id == instance_id for e in self.events):
                instance_id += f"@{entry['x']},{entry['y']}"
            self.events.append(WorldEvent(
                event_id=instance_id,
                name=definition["name"],
                x=entry["x"], y=entry["y"],
                description=definition["description"],
                reward_id=definition.get("reward_id"),
                reward_count=definition.get("reward_count", 1),
                dissolution_reward=definition.get("dissolution_reward", 10),
                catalog_id=definition["catalog_id"],
                insight_id=definition.get("insight_id"),
                kind=definition.get("kind", "simple"),
                dialogue=tuple(definition.get("dialogue", ())),
                options=tuple(definition.get("options", ())),
                uses_left=event_uses(definition),
                bound=True,
            ))
            # Authored anchors are exact: never relocate or carve a circuit gate
            # while spawning its scene event. Platforms already come from the map.

    def _seed_region_weapon(self) -> None:
        """区域入口提供一件基础近战选择；不自动装备、不干预梦中梦模板。"""
        if self.realm_id or self.depth not in (1, 11, 21):
            return
        item_id, minimum = {1: ("pen_sharp", 2), 11: ("heavy_stapler", 3),
                            21: ("carbon_copy_knife", 4)}[self.depth]
        if any(entry.item.definition_id == item_id for entry in self.world_items):
            return
        for item in self.inventory:
            definition = ITEM_DEFINITIONS.get(item.definition_id, {})
            if definition.get("slot") != "手中意象":
                continue
            melee = definition.get("melee", {})
            damage = (1 + (definition.get("power", 0) if definition.get("effect") == "weapon_damage" else 0)
                      + melee.get("damage", 0)) * melee.get("segments", 1)
            tempo = max(0.2, melee.get("time", 1) -
                        (0.1 * definition.get("power", 0) if definition.get("effect") == "swift_strike" else 0))
            if damage / tempo >= minimum / (1.1 if self.depth == 21 else 1):
                return
        # 只用邻近、安全、空闲且可走的格子；不跨墙把保底藏进另一房间。
        occupied = {(entry.x, entry.y) for entry in self.world_items}
        occupied.update((enemy.x, enemy.y) for enemy in self.enemies if enemy.integrity > 0)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                x, y = self.player.x + dx, self.player.y + dy
                if (dx or dy) and 0 < x < self.width - 1 and 0 < y < self.height - 1:
                    cell = self.cell(x, y)
                    if not cell.solid and not cell.flame and not cell.liquid and not cell.gas and (x, y) not in occupied:
                        self.world_items.append(WorldItem(self._make_item(item_id), x, y))
                        return

    # ── §14.6 台面落点（2026-10-22 第九轮）──────────────────────────────
    # 台面（木桌子／石台）本来就能承载物品：`map_scene` 用
    # `support = surface == wall_kind and solid` 决定把这件东西画在台面上，
    # `take_from` 允许站邻格从台面取物。但生成侧从不为 `surface` 赋值——
    # E5 实测「台面上的东西从没被标出来过」正是这个原因（实测 0%）。
    # 这里只改落点、不改份数：搬上台面的那件原本也躺在地上。
    SURFACE_MOVE_SHARE = 0.5      # 有台面可用时搬上去的比例（不全挤在台面上）
    SURFACE_SEARCH_BUDGET = 240   # 同一连通区域里最多展开这么多格（≈一个房间）
    # 承载面＝台面 ＋ 可步行的白瓷工作台／胡桃木书架（materials.SURFACE_KINDS），
    # 再摘掉陷阱／机关石台——那两张台面「点一下就触发机关」，搬上去是陷害。
    SURFACE_SAFE_KINDS = SURFACE_KINDS - frozenset({"陷阱石台", "机关石台"})

    def _surface_spots(self, x: int, y: int, *,
                       occupied: "set[tuple[int, int]]" = frozenset()) -> list[tuple[int, int, int, str]]:
        """同一连通区域内可承载物品的台面：``(步行距离, x, y, 台面墙种)``。

        按**步行距离**（BFS 展开的层数）而不是直线距离排：直线距离会把隔壁房间
        的桌子也算进来（实测桌面离落点 12—31 格、隔着墙），那样「搬上台面」
        等于把东西搬到别的房间去——玩家看不到，也就不算「可观察」。
        """
        budget = GenerationMixin.SURFACE_SEARCH_BUDGET
        seen = {(x, y)}
        order = [(x, y)]
        head = 0
        found: list[tuple[int, int, int, str]] = []
        reach: dict[tuple[int, int], int] = {(x, y): 0}
        while head < len(order) and len(seen) < budget:
            cx, cy = order[head]
            head += 1
            depth = reach[(cx, cy)]
            # 站在 (cx,cy) 能伸手取到的台面（8 邻域）：距离记作「走到这一格」。
            for ax in (-1, 0, 1):
                for ay in (-1, 0, 1):
                    if not (ax or ay):
                        continue
                    tx, ty = cx + ax, cy + ay
                    if not (0 <= tx < self.width and 0 <= ty < self.height):
                        continue
                    kind = self.cell(tx, ty).wall_kind
                    if kind in GenerationMixin.SURFACE_SAFE_KINDS and (tx, ty) not in occupied:
                        found.append((depth, tx, ty, kind))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if (nx, ny) in seen or self.cell(nx, ny).solid:
                    continue
                seen.add((nx, ny))
                reach[(nx, ny)] = depth + 1
                order.append((nx, ny))
        found.sort()
        return found

    def stamp_surfaces(self) -> dict:
        """把台面上的显化物标出来，并把一部分地面奖励搬上台面。

        返回 ``{"stamped": 本来就站在台面上的, "moved": 搬上去的, "total": 本层件数}``
        —— 调用方（测试／跑批）用它核对「份数没变、只是换了落点」。
        """
        from ..materials import SURFACE_KINDS

        rng = random.Random(self.seed * 37 + self.depth * 7331)
        protected = self._scene_layout_cells()
        taken = {
            (entry.x, entry.y) for entry in self.world_items
            if self.cell(entry.x, entry.y).wall_kind in SURFACE_KINDS
        }
        stamped = moved = 0
        for entry in self.world_items:
            if (entry.x, entry.y) in protected:
                # 场景结构占的格子：里面的东西是机关的一部分，不是地面奖励。
                continue
            kind = self.cell(entry.x, entry.y).wall_kind
            if kind in SURFACE_KINDS:
                # 本来就落在台面格上（宝库中央石台就是这种）：补上层级标注。
                entry.surface = kind
                stamped += 1
                continue
            if entry.surface:
                continue
            if rng.random() >= GenerationMixin.SURFACE_MOVE_SHARE:
                continue
            spots = self._surface_spots(entry.x, entry.y, occupied=taken)
            if not spots:
                continue
            _, cx, cy, ckind = spots[0]
            entry.x, entry.y, entry.surface = cx, cy, ckind
            taken.add((cx, cy))
            moved += 1
        return {"stamped": stamped, "moved": moved, "total": len(self.world_items)}

    def _scene_layout_cells(self) -> set[tuple[int, int]]:
        """本层场景结构占的格子——这些格子里的东西不搬上台面。

        「引潮的低盆」的排放区开局堆着一件可搬动的杂物（挡路物）：搬走它
        排放区才通，那是**场景机关**不是地面奖励。``stamp_surfaces`` 把它
        搬到隔壁石台，机关就失效了（tests/test_world_scenes_tide_basin.py）。
        """
        cells: set[tuple[int, int]] = set()
        ledger = getattr(self, "world_ledger", None)
        if ledger is None:
            return cells
        for record in ledger.facilities.values():
            if record.layer_key != self.layer_key():
                continue
            for key in record.layout:
                cells.update(record.area(key))
        return cells

    def _award_eligible(self, ids, *, source: str) -> list[str]:
        """按 ``item_access.refusal`` 的统一资格查询过滤候选池（方案 §7.1 唯一入口）。

        `min_depth`／`grant_source`／`run_limit` 三个字段如果只在 NPC、箱子、
        击杀掉落里生效，地面散投与保底照样能把深层限定物铺在第 1 层——
        「半途只改一处等于留旁路」。凡是从池里抽实物的地方都过这一道。
        """
        from .item_access import refusal

        return [iid for iid in ids if refusal(self, iid, source=source) is None]

    def _starter_launcher(self) -> "str | None":
        """启动发射源：主梦首层、行囊没有任何可发射来源时补一件。

        旧实现「每层在出生点旁铺一台」会让带槽件长期占到全部掉落两成以上；
        2026-09-18 已改成「持有就跳过」，但仍逐层重试。E5后续 P1 再收紧为
        只补首层一次：装备跨层保留，一件已经会用的工具不需要反复再送。
        """
        if self.realm_id or self.depth > GenerationMixin.SUPPLY_LAUNCHER_DEPTH:
            return None
        if any(item.effect == "unlock_fire" for item in self.inventory):
            return None
        return "echo_emitter"

    def _starter_restore(self) -> "str | None":
        """启动恢复补给：前 3 层、缺什么补什么，一件。

        只在「该资源占上限比例 < SUPPLY_RESTORE_MIN_RATIO」时补，所以满状态
        进层不会被白送一件；三种资源各自取既有常见件，不发稀有件。
        """
        if self.realm_id or self.depth > GenerationMixin.SUPPLY_RESTORE_MAX_DEPTH:
            return None
        best: "tuple[float, str] | None" = None
        for stat, definition_id in GenerationMixin.SUPPLY_RESTORE_TABLE:
            maximum = getattr(self, f"max_{stat}", 0) or 0
            if maximum <= 0:
                continue
            ratio = (getattr(self, stat, 0) or 0) / maximum
            if ratio >= GenerationMixin.SUPPLY_RESTORE_MIN_RATIO:
                continue
            if best is None or ratio < best[0]:
                best = (ratio, definition_id)
        return best[1] if best else None

    def _seed_layer_contents(self, vault_info: "dict | None" = None) -> None:
        self._seed_region_weapon()
        # 结构自带事件先落地：它们占本层事件名额，随机零散只在余额内补位
        # （2026-10-27）。``scene`` 型条目交给场景安装器、不落成 WorldEvent，
        # 因此按「实际追加了几个事件」计数，而不是按 vault_info 的条目数。
        events_before = len(self.events)
        self._spawn_bound_events(vault_info)
        bound_events = len(self.events) - events_before
        # 珍品机会（2026-10-22 A2 P5，方案 §6.1）：22／24／26 层各一次高成本
        # 机会，**替换**本层一个高价值奖励槽——中央石台（位面中央石台同义）
        # 的稀有物槽；没有石台就顶掉一个普通散投槽（保底档不动）。两种做法
        # 都不增加本层实物份数，也不额外撒地面物。
        treasure_stage = treasure_stage_for_depth(self.depth)
        loot_cells = list((vault_info or {}).get("loot_cells", ()))
        treasure_loot_cell = loot_cells[-1] if (treasure_stage and loot_cells) else None
        # ── 供给口径（E5后续 P1，2026-10-22）────────────────────────────
        # 旧实现每层固定铺三件：出生点旁「回声发射器 + 温咖啡」，远处一件
        # 「折叠弹影」，再叠 4 次普通随机与追加式保底。E5 实测（24 种子 ×
        # 27 层）平均 8.84 件/层，且前三件占比每档恒定 34.5%–36.9%——
        # 固定件正是这个恒定值的来源。改为：
        #   ① 发射源只在主梦首层、行囊没有任何可发射来源时补一次；
        #   ② 恢复补给只在前 3 层、且该资源真的低于阈值时补一件；
        #   ③ 折叠弹影不再固定投放，回到事件／任务／普通随机渠道；
        #   ④ 保底改为替换本层最后一个（或倒数第二个）普通槽位，总量不增；
        #   ⑤ 同层同 ID 去重，被拒候选从合法池重抽。
        near_offsets = []
        launcher = self._starter_launcher()
        if launcher is not None:
            near_offsets.append((1, 0, launcher))
        restore = self._starter_restore()
        if restore is not None:
            near_offsets.append((0, 1, restore))
        fixed_far: tuple[str, ...] = ()
        for dx, dy, definition_id in near_offsets:
            x, y = self._find_open_cell(self.cells, self.player.x + dx, self.player.y + dy)
            if (x, y) == (self.player.x, self.player.y):
                continue
            self.world_items.append(WorldItem(self._make_item(definition_id), x, y))
        # 其余 4 件按深度稀有度曲线抽（2026-09-18）：先抽档位，再从该档
        # 的易逝物/摄入物/惯用物池里随机取一件。
        loot_rng = random.Random(self.seed * 7 + self.depth * 7717)
        loot_categories = ("易逝物", "摄入物", "惯用物", "交互道具")
        rolled: list[tuple[str, str]] = []
        for _ in range(GenerationMixin.LOOT_ROLLS):
            rarity = roll_rarity(self.depth, loot_rng, luck=self._loot_luck())
            candidates = self._award_eligible(
                items_of_rarity(rarity, loot_categories), source="floor_scatter")
            if not candidates:
                rarity = "常见"
                candidates = self._award_eligible(
                    items_of_rarity("常见", loot_categories),
                    source="floor_scatter")
            if not candidates:
                # 整档都被资格挡掉（深层限定／本局已领完）：本槽留空，
                # 不静默换成另一档的实物——宁可少一件，也不绕过资格。
                continue
            # 同层同 ID 去重：最多重抽 4 次，抽不到新的就退回重复（不静默少发）。
            chosen_id = candidates[loot_rng.randrange(len(candidates))]
            for _attempt in range(4):
                if chosen_id not in [entry[0] for entry in rolled]:
                    break
                chosen_id = candidates[loot_rng.randrange(len(candidates))]
            rolled.append((chosen_id, rarity))
        # 保底：每 3 层至少一件稀有、每 6 层至少一件非常稀有。
        # 2026-10-22（P1）：改为**替换**本层最后一个普通槽位，不再额外追加
        # 一件——旧口径下保底层反而比普通层多出一件，「稀有保底」自己成了
        # 供给增量。珍品不进保底（保底只从「稀有／非常稀有」现有池取）。
        self.layers_since_rare += 1
        self.layers_since_very_rare += 1
        pity: list[tuple[str, str]] = []
        if self.layers_since_very_rare >= 6:
            pool = self._award_eligible(
                items_of_rarity("非常稀有", ("携带意象",) + loot_categories),
                source="pity")
            if pool:
                pity.append((pool[loot_rng.randrange(len(pool))], "非常稀有"))
            self.layers_since_very_rare = 0
        if self.layers_since_rare >= 3:
            pool = self._award_eligible(
                items_of_rarity("稀有", ("携带意象",) + loot_categories),
                source="pity")
            if pool:
                pity.append((pool[loot_rng.randrange(len(pool))], "稀有"))
            self.layers_since_rare = 0
        for offset, entry in enumerate(pity, start=1):
            if len(rolled) >= offset:
                rolled[-offset] = entry
        from .main_difficulty import reserve_recovery_slot
        reserve_recovery_slot(self, rolled, len(pity))
        from .main_learning import reserve_tool_choice
        reserve_tool_choice(self, rolled, len(pity))
        # 珍品机会占用一个高价值奖励槽（2026-10-22 A2 P5）：有中央石台就顶掉
        # 石台那一格（下面 vault 循环跳过该格），没有石台就顶掉一个**普通**
        # 散投槽。保底档不动——「每 3／6 层至少一件稀有／非常稀有」是硬承诺，
        # 不该被珍品机会吃掉。两种做法都不增加本层实物份数。
        if treasure_stage is not None and treasure_loot_cell is None:
            normal_end = len(rolled) - len(pity)
            if normal_end > 0:
                del rolled[normal_end - 1]
        for definition_id, rarity in rolled:
            if rarity == "稀有":
                self.layers_since_rare = 0
            if rarity == "非常稀有":
                self.layers_since_very_rare = 0
        rolled_ids = [definition_id for definition_id, _ in rolled]
        # 记忆碎片投放（2026-10-15 收紧）：每层以 MEMORY_FLOOR_CHANCE 掷一次，
        # 命中才从记忆池抽 1 件落在远处——生成率由「每层必出 2 件」降到
        # 概率制，且每层至多 1 件可拾取碎片。碎片池仍覆盖全部记忆碎片
        # （test_generation_coverage 的静态渠道检查沿用）；NPC 交易与事件
        # 奖励的碎片是另行授予，不计入这个上限。
        memory_ids = sorted(key for key in MEMORY_RARITY
                            if not ITEM_DEFINITIONS.get(key, {}).get('expansion_catalog_id'))
        memory_ids = self._award_eligible(memory_ids, source="floor_scatter")
        if memory_ids:
            mem_rng = random.Random(self.seed * 13 + self.depth * 104729)
            if mem_rng.random() < GenerationMixin.MEMORY_FLOOR_CHANCE:
                from .expansion_rewards import optional_slot
                memory_id = optional_slot(self, memory_ids[mem_rng.randrange(len(memory_ids))], mem_rng)
                if memory_id is not None:
                    rolled_ids.append(memory_id)
        far_points = self._distributed_open_cells(len(fixed_far) + len(rolled_ids), self.seed * 7 + self.depth * 7717)
        for definition_id, (x, y) in zip(list(fixed_far) + rolled_ids, far_points):
            if (x, y) == (self.player.x, self.player.y):
                continue
            self.world_items.append(WorldItem(self._make_item(definition_id), x, y))
        # 异常地点投放：候选池由 data/events.event_candidates 给出（分层池／池轮转，
        # 并过一遍 §15 P1 的迁移开关——已被场景实现顶掉的族不再从池里发旧事件）。
        # 地点优先落在石台上（_place_event_site 负责把室内格改造成石台）。
        #
        # 投放频率（2026-09-15 下调，2026-10-22 P1 再改口径）：旧实现把池里
        # 的事件**全部**盖上——3 层固定 2 个、5 层固定 3 个，玩家一进屋就撞见
        # 一堆台子。2026-09-15 改成「每个候选独立掷 0.6」，但事件池已有十几个
        # 候选，独立掷签下几乎必满员，等于仍固定 2 个。
        # 2026-10-22（E5后续 P1）改为真正的两段式：**先抽本层放几个**（0／1／2
        # = 40%／50%／10%，期望 0.7），再从主题池**无放回**选种类。
        #
        # 2026-10-12 配额口径：这里只约束「零散随机事件」，且按组计数
        # （一次投放落一个点位 = 一组）。2026-10-27 收紧：结构绑定事件
        # （vault_info["events"]，见 _spawn_bound_events）**占同一份名额**，
        # 本层随机只补余额（见 bound_events）——否则一层两三栋带台子的结构
        # 再叠两个随机点，总量会翻倍。位面入口（realm gate / 青灯场景，均
        # bound=True 或走 install_bound_scene）是剧情推进所需、另行落位；
        # 本层的结构锚点在 vault 生成期优先落位，随机投放再用 protected
        # 避开结构区补零散的。
        candidates = list(event_candidates(self.depth))
        event_rng = random.Random(self.seed * 23 + self.depth * 5171)
        quota = 0
        roll = event_rng.random()
        for index, threshold in enumerate(GenerationMixin.EVENT_QUOTA_WEIGHTS):
            if roll < threshold:
                quota = index
                break
        else:
            quota = len(GenerationMixin.EVENT_QUOTA_WEIGHTS) - 1
        remaining = max(0, GenerationMixin.EVENT_MAX_PER_LAYER - bound_events)
        quota = min(quota, len(candidates), remaining)
        chosen: list[str] = []
        pool = list(candidates)
        for _ in range(quota):
            if not pool:
                break
            chosen.append(pool.pop(event_rng.randrange(len(pool))))
        for index, event_id in enumerate(chosen):
            definition = next(entry for entry in EVENT_DEFINITIONS if entry["event_id"] == event_id)
            event_x, event_y = self._place_event_site(
                min(self.width - 2, max(1, self.player.x + (index + 1) * 3)),
                min(self.height - 2, max(1, self.player.y + 3 + index * 2)),
                protected=(vault_info or {}).get("regions", ()),
            )
            kwargs = event_spawn_kwargs(definition)
            if any(e.event_id == kwargs["event_id"] for e in self.events):
                kwargs["event_id"] += f"@{event_x},{event_y}"
            self.events.append(WorldEvent(x=event_x, y=event_y, **kwargs))
        # 珍品机会（2026-10-22 A2 P5）：22／24／26 层各一次，高成本、限量。
        # 选项在**生成时**装配（按本局已领记录摆没拿过的珍品），所以不能写
        # 在定义表里——静态选项会在生成那一刻锁死，之后就永远领不到。
        # 事件本体是结构锚点（bound=True），不占随机事件配额。
        if treasure_stage is not None:
            treasure_definition = next(
                (entry for entry in EVENT_DEFINITIONS
                 if entry["event_id"] == treasure_stage["event_id"]),
                None,
            )
            if treasure_definition is not None:
                treasure_kwargs = event_spawn_kwargs(treasure_definition)
                treasure_kwargs["options"] = build_treasure_options(self, treasure_stage)
                treasure_kwargs["bound"] = True
                treasure_x, treasure_y = self._place_event_site(
                    min(self.width - 2, max(1, self.player.x + 5)),
                    min(self.height - 2, max(1, self.player.y + 5)),
                    protected=(vault_info or {}).get("regions", ()),
                )
                if any(e.event_id == treasure_kwargs["event_id"] for e in self.events):
                    treasure_kwargs["event_id"] += f"@{treasure_x},{treasure_y}"
                self.events.append(
                    WorldEvent(x=treasure_x, y=treasure_y, **treasure_kwargs))
        # vault 中央石台的稀有物品：携带意象按层取区域池，特殊件固定。
        loot_cells = (vault_info or {}).get("loot_cells", [])
        if loot_cells:
            loot_rng = random.Random(self.seed * 13 + self.depth * 6263)
            loot_pool = [key for key in equipment_pool_for_depth(self.depth)
                         if not ITEM_DEFINITIONS.get(key, {}).get('expansion_catalog_id')] + list(
                GenerationMixin.VAULT_LOOT_SPECIAL_IDS
            )
            # §7.1 统一资格入口：中央石台是最高价值的高价值奖励槽，同样
            # 必须过闸，否则「深层限定／本局唯一」的件会从石台整箱漏出。
            loot_pool = self._award_eligible(loot_pool, source="vault")
            for x, y in loot_cells if loot_pool else ():
                if not (0 <= x < self.width and 0 <= y < self.height):
                    continue
                if (x, y) == treasure_loot_cell:
                    # 这一格让给珍品机会了：不撒物，机会本身顶替这个高价值槽。
                    continue
                loot_id = loot_pool[loot_rng.randrange(len(loot_pool))]
                from .expansion_rewards import optional_slot
                loot_id = optional_slot(self, loot_id, loot_rng)
                if loot_id is not None:
                    self.world_items.append(WorldItem(self._make_item(loot_id), x, y))
        # 携带意象：低频稀有的房间刷新。
        self._spawn_equipment(random.Random(self.seed * 31 + self.depth * 9176))
        # 书卷/残页：更稀有，使用后习得主动构想。
        scroll_rng = random.Random(self.seed * 17 + self.depth * 4409)
        if scroll_rng.random() < 0.3:
            scroll_id = "spellbook" if scroll_rng.random() < 0.4 else "torn_page"
            # 书卷也过统一资格入口（当前两件无资格字段，但入口不留裸通道）。
            if not self._award_eligible([scroll_id], source="floor_scatter"):
                scroll_id = ""
            x, y = self._find_open_cell(
                self.cells,
                scroll_rng.randrange(2, max(3, self.width - 2)),
                scroll_rng.randrange(2, max(3, self.height - 2)),
            )
            if scroll_id and (x, y) != (self.player.x, self.player.y):
                self.world_items.append(WorldItem(self._make_item(scroll_id), x, y))
        self._seed_scene_anchor(vault_info)
        from .tactical_layouts import (seed_multi_solution_gate, seed_rewriting_corridor,
                                       seed_wet_archive)
        if seed_wet_archive(self,vault_info) is None:
            if seed_rewriting_corridor(self,vault_info) is None:
                seed_multi_solution_gate(self,vault_info)
        # 落点收尾：场景／结构落完之后再搬台面，免得被后来的投放挤回地面。
        # 本层「份数」不变，只换落点并写上层级标签。
        self.last_surface_report = self.stamp_surfaces()

    def _seed_scene_anchor(self, vault_info: "dict | None") -> None:
        """本层的主要互动场景（§12.1）：放在掉落投放之后，院子就会绕开已经落好的
        显化物与异常地点，而不是把它们的格子占掉。"""
        from .scenes import seed_scenes

        seed_scenes(self, vault_info)
