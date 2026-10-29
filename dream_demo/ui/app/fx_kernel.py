"""CY-2：FX 快照的视口扫描内核。

把 ``_fx_snapshot`` 里「逐格收集底色/光源候选/火焰/遮挡/液气色」的纯循环
搬进编译单元；返回与原实现同序的 9 个集合/列表，后续的缓存、光池、
呼吸光环逻辑仍留在 Python 侧，口径不变。
"""
from __future__ import annotations

from ...core.realm_surface import cached_surface_color, display_zones, protects_floor
from ...materials import (TRANSPARENT_WALLS, gas_def, liquid_def, plant_height,
                          wall_def)
from ...core.constants import Material


def scan_viewport(state, left: int, top: int, vw: int, vh: int, visible,
                  developed, phantom_echo, cursed_seen):
    surface_zones = display_zones(state)
    surface_cache: dict[tuple[int, int], str | None] = {}
    surface_bgs = []
    fixed_ground = set()
    shown: set[tuple[int, int]] = set()
    opaque: set[tuple[int, int]] = set()
    sight_smoke: list[tuple[int, int]] = []
    sight_walls: list[tuple[int, int]] = []
    flames: list[tuple[int, int]] = []
    env_light_candidates: list = []
    liquid_gas: list[tuple[int, int, str]] = []
    for vy in range(vh):
        for vx in range(vw):
            x, y = left + vx, top + vy
            try:
                cell = state.cell(x, y)
            except Exception:
                continue
            if (x, y) in visible or (x, y) in developed:
                ground = cached_surface_color(state, x, y, surface_zones, surface_cache)
                if ground:
                    surface_bgs.append((vx, vy, ground))
                    if (protects_floor(state, x, y) and not cell.flame):
                        fixed_ground.add((vx, vy))
                elif cell.solid and cell.wall_kind:
                    wall_color = wall_def(cell.wall_kind).color
                    if wall_color:
                        surface_bgs.append((vx, vy, wall_color))
                if (cell.plant or (cell.liquid_kind and cell.liquid > 0)
                        or (cell.gas_kind and cell.gas > 0)
                        or (cell.solid and cell.wall_kind)):
                    env_light_candidates.append((vx, vy, cell))
            if cell.flame > 0 and ((x, y) in visible or (x, y) in phantom_echo
                                   or (x, y) in developed or (x, y) in cursed_seen):
                flames.append((vx, vy))
            kind_color = None
            if cell.solid:
                opaque.add((vx, vy))
                if cell.wall_kind not in TRANSPARENT_WALLS:
                    sight_walls.append((x, y))
            if cell.plant and plant_height(cell.plant) >= 2:
                sight_walls.append((x, y))
            if cell.gas > 0 and state._gas_sight_effect(cell)[0]:
                sight_smoke.append((x, y))
            if cell.liquid > 0 or cell.floor is Material.LIQUID_MEMORY:
                kind_color = liquid_def(cell.liquid_kind).color
            elif cell.gas > 0 or cell.floor is Material.DIFFUSE_IMPRESSION:
                kind_color = gas_def(cell.gas_kind).color
            if kind_color is None:
                continue
            liquid_gas.append((vx, vy, kind_color))
            if ((x, y) in visible or (x, y) in phantom_echo
                    or (x, y) in developed or (x, y) in cursed_seen):
                shown.add((vx, vy))
    return (surface_bgs, fixed_ground, env_light_candidates, flames, opaque,
            sight_walls, sight_smoke, liquid_gas, shown)
