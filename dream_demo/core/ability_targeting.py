"""§12 H2：主动构想的显式落点口径（结算/瞄准/预览共用）。

战斗构想有 ``combat`` 元数据；这里补上 24 条 H2 非战斗构想的选点规则。
落点一律「悬停格 → 面朝格」，都不合法就拒绝；不做最近目标回退，
避免预览与提交悄悄换到另一格。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import Material


@dataclass(frozen=True)
class AimSpec:
    form: str            # point / direction / self
    range: int = 12
    strict: bool = False  # True：没有合法默认目标就拒绝，绝不最近回退
    kind: str = "any"     # 落点类别，validation 用


# kind: open=可见空地，liquid=可见液体，node=可见触发节点，
#       enemy_or_conductor=可见异象/导电介质，flammable=可见可燃材料，
#       develop=可见或已有地形快照。
AIM_SPECS: dict[str, AimSpec] = {
    # 5.1 探索
    "develop": AimSpec("point", 10, kind="develop"),
    "wide_develop": AimSpec("self"),
    "library.margin": AimSpec("direction", 12),
    # 5.2 声源/隐蔽
    "echo_pulse": AimSpec("self"),
    "smoke_veil": AimSpec("point", 12, kind="open"),
    "mute_protocol": AimSpec("self"),
    "listen_realm": AimSpec("self"),
    "vanish": AimSpec("self"),
    "moth_dust": AimSpec("point", 12, kind="open"),
    # 5.3 液体/相变/植被
    "condense_dew": AimSpec("point", 12, kind="open"),
    "sow_green": AimSpec("point", 12, kind="open"),
    "draw_liquid": AimSpec("point", 12, kind="liquid"),
    "ice_bridge": AimSpec("point", 12, kind="liquid"),
    "transpire": AimSpec("point", 12, kind="liquid"),
    # 5.4 控场
    "repulse": AimSpec("point", 12, kind="any"),
    "static_arc": AimSpec("point", 12, kind="enemy_or_conductor"),
    "slow_wave": AimSpec("point", 12, kind="any"),
    # 5.5 地形
    "collapse": AimSpec("point", 12, kind="open"),
    "conjure_wall": AimSpec("point", 12, kind="open"),
    "ink_doodle": AimSpec("point", 12, kind="open"),
    # 5.6 目标可控性：只认明确选择，不自动最近
    "blink": AimSpec("point", 8, strict=True, kind="blink"),
    "short_circuit": AimSpec("point", 12, strict=True, kind="node"),
    "rewire": AimSpec("point", 12, strict=True, kind="node"),
    "detonate": AimSpec("point", 12, strict=True, kind="flammable"),
}

# 扩展包目录的构想落点（catalog.json 的 effect.aim）：与定义行同一批键，
# 没登记的行也不会出现在 ABILITY_DEFINITIONS 里（见 growth_runtime）。
from ..data.expansion.growth_runtime import ability_aim_rows as _expansion_aim_rows  # noqa: E402

AIM_SPECS.update({key: AimSpec(**row) for key, row in _expansion_aim_rows().items()})


def spec_for(ability_id: str) -> AimSpec | None:
    return AIM_SPECS.get(ability_id)


def aim_form(ability_id: str) -> str | None:
    spec = AIM_SPECS.get(ability_id)
    return spec.form if spec is not None else None


def is_targeted(ability_id: str) -> bool:
    spec = AIM_SPECS.get(ability_id)
    return spec is not None and spec.form in ("point", "direction")


def aim_range(ability_id: str) -> int:
    spec = AIM_SPECS.get(ability_id)
    return spec.range if spec is not None else 0


def _open_cell(state, x, y) -> bool:
    cell = state.cell(x, y)
    return not cell.solid and cell.floor is not Material.SOLID_AGGREGATE


def _is_flammable(state, x, y) -> bool:
    cell = state.cell(x, y)
    return not cell.solid and bool(state._cell_is_flammable(cell))


def _liquid_cell(state, x, y) -> bool:
    cell = state.cell(x, y)
    return not cell.solid and cell.liquid > 0 and not _protected_liquid(state, x, y)


def _protected_liquid(state, x, y) -> bool:
    from . import construct_environments
    try:
        return bool(construct_environments.protected_geometry(state, x, y))
    except Exception:
        return False


def _conductive(state, x, y) -> bool:
    return state._conductive_cell(state.cell(x, y))


def _enemy_at(state, x, y):
    entity = state.entity_at(x, y)
    return (entity is not None and entity is not state.player
            and getattr(entity, "relation", "") == "失控意识"
            and getattr(entity, "integrity", 0) > 0)


def valid_target(state, ability_id: str, point) -> bool:
    """构想的落点是否成立；只读，不付费、不改世界。"""
    spec = AIM_SPECS.get(ability_id)
    if spec is None or spec.form != "point" or point is None:
        return False
    try:
        x, y = int(point[0]), int(point[1])
    except (TypeError, ValueError, IndexError):
        return False
    if not state.inside_board(x, y):
        return False
    if max(abs(x - state.player.x), abs(y - state.player.y)) > spec.range:
        return False
    if spec.kind == "develop":
        if state.is_visible(x, y):
            return True
        from .vision.knowledge import remembered_terrain
        return remembered_terrain(state, x, y) is not None
    if not state.is_visible(x, y):
        return False
    if spec.kind == "blink":
        return (_open_cell(state, x, y) and not state.entity_at(x, y)
                and (x, y) != (state.player.x, state.player.y))
    if spec.kind == "liquid":
        return _liquid_cell(state, x, y)
    if spec.kind == "flammable":
        return _is_flammable(state, x, y)
    if spec.kind == "node":
        from ..materials.logic import LOGIC_KINDS
        return state.cell(x, y).wall_kind in LOGIC_KINDS
    if spec.kind == "enemy_or_conductor":
        return _enemy_at(state, x, y) or _conductive(state, x, y)
    if spec.kind == "open":
        return _open_cell(state, x, y)
    return True


def default_target(state, ability_id: str):
    """默认落点：悬停格 → 面朝格；都不合法就拒绝，绝不改投最近目标。

    §12 H2 的通用口径：「未选择时先给默认目标预览，不能直接跳到另一个
    最近目标提交」。``strict`` 只影响 UI 是否提示换目标，不再有最近回退。
    """
    spec = AIM_SPECS.get(ability_id)
    if spec is None or spec.form != "point":
        return None
    hover = getattr(state, "hover_target", None)
    if hover and valid_target(state, ability_id, hover):
        return (int(hover[0]), int(hover[1]))
    dx, dy = state.facing or (1, 0)
    facing = (state.player.x + int(dx), state.player.y + int(dy))
    if valid_target(state, ability_id, facing):
        return facing
    return None


def resolve_target(state, ability_id: str, target=None):
    """把显式落点/默认落点解析成真实坐标；不合法返回 None。"""
    if ability_id == "rewire":
        # 改线要两个端口（触发源 + 接收端），不参与单点默认落点。
        if target is None or len(target) != 4:
            return None
        try:
            sx, sy, rx, ry = (int(v) for v in target)
        except (TypeError, ValueError):
            return None
        if (valid_target(state, ability_id, (sx, sy))
                and valid_target(state, ability_id, (rx, ry))):
            return (sx, sy, rx, ry)
        return None
    if target is not None:
        if valid_target(state, ability_id, target):
            return (int(target[0]), int(target[1]))
        return None
    return default_target(state, ability_id)


def default_direction(state, direction=None):
    if direction is not None and any(direction):
        return ((direction[0] > 0) - (direction[0] < 0),
                (direction[1] > 0) - (direction[1] < 0))
    dx, dy = state.facing or (1, 0)
    return (int(dx), int(dy))


def margin_strip(state, direction, *, length: int | None = None, width: int = 3):
    """旁注：沿方向长 12、宽 3 的条带（含起点前一格）。

    只返回棋盘内坐标；方向轴格在前，横向 ±1 居中排列，便于结算与预览共用。
    """
    dx, dy = default_direction(state, direction)
    length = 12 if length is None else int(length)
    px, py = state.player.x, state.player.y
    if dx and dy:
        # 只支持四方向；斜向取主轴。
        if abs(dx) >= abs(dy):
            dy = 0
        else:
            dx = 0
    perp = (-dy, dx)
    half = width // 2
    cells: list[tuple[int, int]] = []
    for step in range(1, length + 1):
        cx, cy = px + dx * step, py + dy * step
        for offset in range(-half, half + 1):
            x, y = cx + perp[0] * offset, cy + perp[1] * offset
            if state.inside_board(x, y):
                cells.append((x, y))
    return cells
