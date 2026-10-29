"""新物品的落点口径：部署类物品的选点、校验与默认落点。

与 ``ability_targeting`` 同口径——悬停格 → 面朝格；都不合法就拒绝，
不做最近回退，避免预览与提交悄悄换到另一格。落点合法性只读，
不付费、不改世界。
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import Material


@dataclass(frozen=True)
class ItemAimSpec:
    form: str          # point / pair / direction / self
    range: int = 6
    kind: str = "open"  # open=可见空地，fluid=源格有材料，any=任意可见格


# P4 中后期工具 + P5 终局珍品里需要选点的物品。
ITEM_AIM_SPECS: dict[str, ItemAimSpec] = {
    "night_shift_beacon": ItemAimSpec("point", 6, "open"),
    "wax_emergency_seal": ItemAimSpec("point", 4, "open"),
    "portable_siphon": ItemAimSpec("pair", 6, "fluid"),
    "breach_spool": ItemAimSpec("direction", 12, "any"),
    "folded_escape_route": ItemAimSpec("pair", 8, "open"),
    "quiet_boundary": ItemAimSpec("self", 4, "any"),
}


def spec_for(item_id: str) -> ItemAimSpec | None:
    spec = ITEM_AIM_SPECS.get(item_id)
    if spec is not None:
        return spec
    spec = _gear_spec(item_id)
    if spec is not None:
        ITEM_AIM_SPECS[item_id] = spec
    return spec


def _gear_spec(item_id: str) -> ItemAimSpec | None:
    """扩展包装备的落点规格只从物品定义的 ``active_use`` 读，不手抄一张表。"""
    try:
        from ..data.items import ITEM_DEFINITIONS
    except Exception:
        return None
    definition = ITEM_DEFINITIONS.get(item_id) or {}
    active = definition.get("consumable_use") or definition.get("active_use")
    if not isinstance(active, dict):
        return None
    form = str(active.get("form") or "")
    if form not in ("point", "pair", "direction", "self"):
        return None
    return ItemAimSpec(form, int(active.get("range", 6) or 6),
                       str(active.get("kind", "open") or "open"))


def is_aimed(item_id: str) -> bool:
    spec = spec_for(item_id)
    return spec is not None and spec.form in ("point", "pair", "direction")


def aim_form(item_id: str) -> str | None:
    spec = spec_for(item_id)
    return spec.form if spec is not None else None


def aim_range(item_id: str) -> int:
    spec = spec_for(item_id)
    return spec.range if spec is not None else 0


def open_cell(state, x: int, y: int) -> bool:
    cell = state.cell(x, y)
    return not cell.solid and cell.floor is not Material.SOLID_AGGREGATE


def protected_cell(state, x: int, y: int) -> bool:
    from . import construct_environments
    try:
        return bool(construct_environments.protected_geometry(state, x, y))
    except Exception:
        return False


def valid_target(state, item_id: str, point) -> bool:
    """单点落点是否成立。"""
    spec = spec_for(item_id)
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
    if not state.is_visible(x, y):
        return False
    if spec.kind == "open":
        return (open_cell(state, x, y) and not protected_cell(state, x, y)
                and state.entity_at(x, y) is None)
    return True


def valid_pair(state, item_id: str, first, second) -> bool:
    """成对落点（源／出口）是否成立。"""
    spec = spec_for(item_id)
    if spec is None or spec.form != "pair" or first is None or second is None:
        return False
    try:
        ax, ay = int(first[0]), int(first[1])
        bx, by = int(second[0]), int(second[1])
    except (TypeError, ValueError, IndexError):
        return False
    if (ax, ay) == (bx, by):
        return False
    if not (state.inside_board(ax, ay) and state.inside_board(bx, by)):
        return False
    if max(abs(ax - bx), abs(ay - by)) > spec.range:
        return False
    for px, py in ((ax, ay), (bx, by)):
        if max(abs(px - state.player.x), abs(py - state.player.y)) > spec.range:
            return False
    if not (state.is_visible(ax, ay) and state.is_visible(bx, by)):
        return False
    if spec.kind == "fluid":
        source = state.cell(ax, ay)
        return (source.liquid > 0 or source.gas > 0) and open_cell(state, bx, by)
    if spec.kind == "open":
        return (open_cell(state, ax, ay) and open_cell(state, bx, by)
                and not protected_cell(state, ax, ay)
                and not protected_cell(state, bx, by)
                and state.entity_at(ax, ay) is None
                and state.entity_at(bx, by) is None)
    return True


def valid_pair_anchor(state, item_id: str, point) -> bool:
    """成对落点的第一个点是否成立（第二个点还没选，只能先校验首点）。

    ``fluid`` 的首点是材料源（源／出口里的源），``open`` 的首点是与第二点
    同等条件的空位。距离与可见性都按玩家的选取范围算，不做最近回退。
    """
    spec = spec_for(item_id)
    if spec is None or spec.form != "pair" or point is None:
        return False
    try:
        x, y = int(point[0]), int(point[1])
    except (TypeError, ValueError, IndexError):
        return False
    if not state.inside_board(x, y):
        return False
    if max(abs(x - state.player.x), abs(y - state.player.y)) > spec.range:
        return False
    if not state.is_visible(x, y):
        return False
    if spec.kind == "fluid":
        cell = state.cell(x, y)
        return cell.liquid > 0 or cell.gas > 0
    if spec.kind == "open":
        return (open_cell(state, x, y) and not protected_cell(state, x, y)
                and state.entity_at(x, y) is None)
    return True


def default_target(state, item_id: str):
    """默认落点：悬停格 → 面朝格；都不合法就拒绝，绝不改投最近目标。"""
    spec = spec_for(item_id)
    if spec is None or spec.form != "point":
        return None
    hover = getattr(state, "hover_target", None)
    if hover and valid_target(state, item_id, hover):
        return (int(hover[0]), int(hover[1]))
    dx, dy = state.facing or (1, 0)
    facing = (state.player.x + int(dx), state.player.y + int(dy))
    if valid_target(state, item_id, facing):
        return facing
    return None


def resolve_target(state, item_id: str, target=None):
    """把显式落点/默认落点解析成真实坐标；不合法返回 None。"""
    if target is not None:
        if valid_target(state, item_id, target):
            return (int(target[0]), int(target[1]))
        return None
    return default_target(state, item_id)


# ---- 通路保护：封死唯一必经路的落点 ----

def _walkable(state, x: int, y: int, blocked=None) -> bool:
    if not state.inside_board(x, y):
        return False
    if blocked is not None and (x, y) == blocked:
        return False
    cell = state.cell(x, y)
    return not cell.solid and cell.floor is not Material.SOLID_AGGREGATE


def _reachable(state, blocked=None) -> set[tuple[int, int]]:
    start = (state.player.x, state.player.y)
    if not _walkable(state, start[0], start[1], blocked):
        return set()
    seen = {start}
    queue = [start]
    while queue:
        cx, cy = queue.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not (dx or dy):
                    continue
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in seen:
                    continue
                if not _walkable(state, nx, ny, blocked):
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def _components(state, blocked=None) -> list[set[tuple[int, int]]]:
    """整幅可行走格的连通分量（用于判断「封完之后玩家被关在哪儿」）。"""
    seen: set[tuple[int, int]] = set()
    components: list[set[tuple[int, int]]] = []
    for y in range(state.height):
        for x in range(state.width):
            if (x, y) in seen or not _walkable(state, x, y, blocked):
                continue
            component: set[tuple[int, int]] = set()
            stack = [(x, y)]
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                component.add((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if not (dx or dy):
                            continue
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) in seen or not _walkable(state, nx, ny, blocked):
                            continue
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            components.append(component)
    return components


def seals_only_path(state, x: int, y: int) -> bool:
    """把这格封成墙之后，玩家会不会被切断一段路。

    判据：封住后玩家可达区域变小，且被切掉的那片里有事件、稳定意识或
    地面物品，或者那片本身就有 4 格以上——也就是「唯一必经路」被封死。
    封一条死胡同的口子不算（那片里什么都没有），因此不拦；但把玩家自己
    关进比别处还小的口袋（死胡同尽头）算封死，所以也拦。
    """
    before = _reachable(state)
    after = _reachable(state, blocked=(x, y))
    lost = before - after
    if not lost:
        return False
    if len(lost) >= 4:
        return True
    for event in state.events:
        if (event.x, event.y) in lost:
            return True
    for entity in state.enemies:
        if getattr(entity, "relation", "") == "稳定意识" and (entity.x, entity.y) in lost:
            return True
    if len(lost) >= 2:
        # 只埋掉一件地面物品不算封路——那件东西只是被压在墙底下。
        for entry in state.world_items:
            if (entry.x, entry.y) in lost:
                return True
    # 玩家被关进小口袋：封完之后他站的地方比别处还小，就是被困住了。
    mine = 0
    others: list[int] = []
    for component in _components(state, blocked=(x, y)):
        if (state.player.x, state.player.y) in component:
            mine = len(component)
        else:
            others.append(len(component))
    if others and max(others) > mine:
        return True
    return False
