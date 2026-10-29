"""CY-1 / CY-7：存档紧凑格编解码内核。

只搬纯数据编解码，不碰迁移顺序、默认值和 catalog 归一化。

- 解码（CY-1）：语义与 ``persistence.SaveManager._decode_compact_cell`` 和
  ``core.vision.knowledge.decode_terrain_memory`` 逐字段一致；后者额外把
  **完全相同的冻结快照**合并成同一个实例（TerrainMemory 是 frozen dataclass，
  共享实例不改变任何可见行为，只减少构造与内存）。
- 编码（CY-7）：语义与 ``persistence.SaveManager._encode_cell`` 逐字节一致，
  包括字符串驻留表的动态追加顺序（未知字符串按格内 floors→variants→walls→
  liquids→gases 的先后入表）与 17–26 位的尾部按位置补齐规则。调用方必须传入
  与纯 Python 路径同一个 tables/cache：**编码结果（含 tables 内容）必须完全不差**。
"""
from __future__ import annotations

from ..materials import (DEFAULT_GAS, DEFAULT_LIQUID, DEFAULT_WALL, DOOR_KINDS,
                         GAS_DEFINITIONS, LIQUID_DEFINITIONS, WALL_DEFINITIONS,
                         wall_def)
from .constants import Material
from .entities import Cell
from .vision.knowledge import TerrainMemory


def decode_compact_cell(item: list, tables: dict[str, list[str]]) -> Cell:
    length = len(item)
    (
        floor_idx, solid_int, liquid, gas, hardness, thickness,
        integrity, cover, flame, variant_idx, wall_idx, height,
        elevation, liquid_idx, gas_idx,
    ) = item[:15]
    plant = int(item[15]) if length > 15 else 0
    wire = int(item[16]) if length > 16 else 0
    solid = bool(solid_int)
    if solid and height > 1:
        liquid = 0
        gas = 0
    liquids = tables.get("liquids") or ()
    raw_liquid_kind = liquids[liquid_idx] if 0 <= liquid_idx < len(liquids) else ""
    gas_table = tables.get("gases") or ()
    raw_gas_kind = gas_table[gas_idx] if 0 <= gas_idx < len(gas_table) else ""
    liquid_kind = (raw_liquid_kind if liquid and raw_liquid_kind in LIQUID_DEFINITIONS
                   else DEFAULT_LIQUID if liquid else "")
    gas_kind = (raw_gas_kind if gas and raw_gas_kind in GAS_DEFINITIONS
                else DEFAULT_GAS if gas else "")
    walls = tables.get("walls") or ()
    raw_wall_kind = walls[wall_idx] if 0 <= wall_idx < len(walls) else ""
    known_wall = raw_wall_kind in WALL_DEFINITIONS
    wall_kind = raw_wall_kind if known_wall else DEFAULT_WALL if solid else ""
    if solid and cover > 0 and wall_def(wall_kind).break_effect == 'dreamcrystal':
        if raw_gas_kind in GAS_DEFINITIONS:
            gas_kind = raw_gas_kind  # cover stores gas; free gas may legitimately be zero.
    variants = tables.get("variants") or ()
    aggregate_variant = (variants[variant_idx] if 0 <= variant_idx < len(variants)
                         else "普通聚合物")
    cell = Cell(
        max(0, wire),
        Material.SOLID_AGGREGATE if solid else Material.PLAIN_AGGREGATE,
        solid, liquid, gas, hardness, thickness, integrity, cover, flame,
        aggregate_variant, wall_kind, height, elevation, liquid_kind, gas_kind,
        max(0, plant) if not solid else 0,
        max(0, int(item[17])) if length > 17 else 0,
        max(0, int(item[18])) if length > 18 else 0,
        max(0, int(item[19])) if length > 19 else 0,
        dict(item[20]) if length > 20 and isinstance(item[20], dict) else {},
        dict(item[21]) if length > 21 and isinstance(item[21], dict) else {},
        max(0, int(item[22])) if length > 22 else 0,
        bool(item[23]) if length > 23 else True,
        bool(item[24]) if length > 24 else wall_kind in DOOR_KINDS,
        dict(item[25]) if length > 25 and isinstance(item[25], dict) else {},
        dict(item[26]) if length > 26 and isinstance(item[26], dict) else {},
    )
    if solid and not known_wall:
        definition = wall_def(wall_kind)
        cell.hardness = definition.hardness
        cell.height = definition.height
        cell.thickness = definition.thickness
        cell.integrity = definition.integrity
    return cell


def decode_cells(rows: list, tables: dict[str, list[str]], legacy) -> list[list[Cell]]:
    """批量解码一层：紧凑格走内核，旧字典格继续用调用方传入的迁移函数。"""
    return [
        [legacy(item) if isinstance(item, dict) else decode_compact_cell(item, tables)
         for item in row]
        for row in rows
    ]


def encode_cells(rows: list, tables: dict[str, list[str]],
                 cache: dict[str, dict[str, int]]) -> list[list[list]]:
    """批量编码一层的紧凑格（CY-7），语义与 ``SaveManager._encode_cell`` 等价。

    - 必须沿用调用方的 tables 与 cache：未知字符串会像纯 Python 路径一样按
      「floors → variants → walls → liquids → gases」的格内顺序动态入表，因此
      整份存档的 tables 顺序/内容才可能与回退实现逐字节相同。
    - cache 语义同 persistence._intern：table 名 → {值: 下标}；下标 0 也必须
      命中，所以判空用 is None 而不是真值判断。
    """
    # 五张表与其值→下标映射在整层内不变：循环外取一次，避免每格 5 次 dict.get。
    # （表本身可能因未知字符串而增长，所以持有 list 引用即可，len/append 仍实时。）
    floors = tables["floors"]
    variants = tables["variants"]
    walls = tables["walls"]
    liquids = tables["liquids"]
    gases = tables["gases"]
    floors_map = cache.get("floors")
    if floors_map is None:
        floors_map = cache["floors"] = {}
    variants_map = cache.get("variants")
    if variants_map is None:
        variants_map = cache["variants"] = {}
    walls_map = cache.get("walls")
    if walls_map is None:
        walls_map = cache["walls"] = {}
    liquids_map = cache.get("liquids")
    if liquids_map is None:
        liquids_map = cache["liquids"] = {}
    gases_map = cache.get("gases")
    if gases_map is None:
        gases_map = cache["gases"] = {}
    encoded_rows = []
    append_row = encoded_rows.append
    for row in rows:
        encoded_row = []
        append_cell = encoded_row.append
        for cell in row:
            # ---- 内联 persistence._intern(tables, key, value, cache) ----
            # 下面五段的先后顺序与 _encode_cell 的列表字面量一致，不可换序。
            value = cell.floor.value
            index = floors_map.get(value)
            if index is None:
                index = len(floors)
                floors.append(value)
                floors_map[value] = index
            floor_index = index

            value = cell.aggregate_variant
            index = variants_map.get(value)
            if index is None:
                index = len(variants)
                variants.append(value)
                variants_map[value] = index
            variant_index = index

            value = cell.wall_kind
            index = walls_map.get(value)
            if index is None:
                index = len(walls)
                walls.append(value)
                walls_map[value] = index
            wall_index = index

            value = cell.liquid_kind
            index = liquids_map.get(value)
            if index is None:
                index = len(liquids)
                liquids.append(value)
                liquids_map[value] = index
            liquid_index = index

            value = cell.gas_kind
            index = gases_map.get(value)
            if index is None:
                index = len(gases)
                gases.append(value)
                gases_map[value] = index
            gas_index = index

            encoded = [
                floor_index,
                1 if cell.solid else 0,
                cell.liquid,
                cell.gas,
                cell.hardness,
                cell.thickness,
                cell.integrity,
                cell.cover,
                cell.flame,
                variant_index,
                wall_index,
                cell.height,
                cell.elevation,
                liquid_index,
                gas_index,
                cell.plant,
                cell.wire,
            ]
            progress = [cell.plant_fuel, cell.floor_fuel, cell.item_burn_progress]
            while progress and progress[-1] == 0:
                progress.pop()
            encoded.extend(progress)
            if cell.creation:
                encoded.extend([0] * (20 - len(encoded)))
                encoded.append(dict(cell.creation))
            if cell.material_clocks:
                encoded.extend([0] * (21 - len(encoded)))
                encoded.append(dict(cell.material_clocks))
            if cell.light_radius or not cell.light_on:
                encoded.extend([0] * (22 - len(encoded)))
                encoded.append(cell.light_radius)
                if not cell.light_on:
                    encoded.append(False)
            if cell.doorway:
                encoded.extend([0] * (22 - len(encoded)))
                if len(encoded) == 22:
                    encoded.append(cell.light_radius)
                if len(encoded) == 23:
                    encoded.append(cell.light_on)
                encoded.append(True)
            if cell.phase_stock:
                defaults = [cell.plant_fuel, cell.floor_fuel, cell.item_burn_progress,
                            dict(cell.creation), dict(cell.material_clocks),
                            cell.light_radius, cell.light_on, cell.doorway]
                while len(encoded) < 25:
                    encoded.append(defaults[len(encoded) - 17])
                encoded.append(dict(cell.phase_stock))
            if cell.plant_state:
                # 第 27 位（索引 26）：植物的一次性／有限状态。旧的尾部块按位置写，
                # 所以这里必须把 17–25 用真实值补齐（与 _encode_cell 完全一致）。
                defaults = [cell.plant_fuel, cell.floor_fuel, cell.item_burn_progress,
                            dict(cell.creation), dict(cell.material_clocks),
                            cell.light_radius, cell.light_on, cell.doorway,
                            dict(cell.phase_stock)]
                while len(encoded) < 26:
                    encoded.append(defaults[len(encoded) - 17])
                encoded.append(dict(cell.plant_state))
            append_cell(encoded)
        append_row(encoded_row)
    return encoded_rows


def encode_cell(cell: Cell, tables: dict[str, list[str]],
                cache: dict[str, dict[str, int]]) -> list:
    """单格编码（测试/等价校验用）；热路径走 encode_cells 的批量循环。"""
    return encode_cells([[cell]], tables, cache)[0][0]


def decode_terrain_memory(raw) -> dict:
    decoded: dict[str, dict[tuple[int, int], TerrainMemory]] = {}
    if not isinstance(raw, dict):
        return decoded
    cache: dict[tuple, TerrainMemory] = {}
    for layer, entries in raw.items():
        if not isinstance(entries, list):
            continue
        memory: dict[tuple[int, int], TerrainMemory] = {}
        for entry in entries:
            if not isinstance(entry, (list, tuple)) or len(entry) < 7:
                continue
            try:
                x, y = int(entry[0]), int(entry[1])
                elevation = None
                if len(entry) > 8 and entry[8] is not None:
                    elevation = int(entry[8])
                height = int(entry[9]) if len(entry) > 9 and entry[9] is not None else None
                key = (
                    str(entry[2] or ""),
                    bool(entry[3]),
                    str(entry[4] or ""),
                    str(entry[5] or ""),
                    int(entry[6] or 0),
                    str(entry[7] or "") if len(entry) > 7 else "",
                    elevation,
                    height,
                )
            except (TypeError, ValueError):
                continue
            snapshot = cache.get(key)
            if snapshot is None:
                snapshot = TerrainMemory(
                    floor=key[0], solid=key[1], wall_kind=key[2],
                    aggregate_variant=key[3], seen_turn=key[4], site=key[5],
                    elevation=key[6], height=key[7],
                )
                cache[key] = snapshot
            memory[(x, y)] = snapshot
        if memory:
            decoded[str(layer)] = memory
    return decoded
