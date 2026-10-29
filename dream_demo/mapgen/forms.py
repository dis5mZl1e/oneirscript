"""各层型的墙体掩码生成器与统一后处理（连通 + braid 解编）。"""

from __future__ import annotations

from collections import deque
import random

from .layout import EPILOGUE_DEPTHS, MAP_FORMS, normalize_map_form
from ..data.events import EVENT_DEFINITIONS, EVENT_MAX_PER_LAYER
from ..data.npcs import NPC_MAX_PER_LAYER
from ..data.quests import STRUCTURE_NPC_BINDING
from .vaults import (
    FORM_VAULT_POOLS,
    POST_VAULTS,
    EXCLUSIVE_VAULTS,
    PRE_VAULTS,
    ROOM_DECOR_VAULTS,
    Vault,
    VaultPlacement,
    pick_by_rarity,
    stamp_vault_in_room,
    stamp_vault_near_open,
    try_stamp_vault,
)

def _new_mask(width: int, height: int, solid: bool = True) -> list[list[bool]]:
    if width < 7 or height < 7:
        raise ValueError("地图至少需要 7x7 格")
    return [[solid for _ in range(width)] for _ in range(height)]


def _carve(mask: list[list[bool]], left: int, top: int, right: int, bottom: int) -> None:
    height, width = len(mask), len(mask[0])
    for y in range(max(1, top), min(height - 1, bottom)):
        for x in range(max(1, left), min(width - 1, right)):
            mask[y][x] = False


def _carve_corridor(
    mask: list[list[bool]],
    start: tuple[int, int],
    end: tuple[int, int],
    width: int,
    horizontal_first: bool,
) -> None:
    x, y = start
    target_x, target_y = end
    half_low = (width - 1) // 2
    half_high = width // 2

    def carve_point(px: int, py: int) -> None:
        _carve(mask, px - half_low, py - half_low, px + half_high + 1, py + half_high + 1)

    axes = ("x", "y") if horizontal_first else ("y", "x")
    for axis in axes:
        target = target_x if axis == "x" else target_y
        while (x if axis == "x" else y) != target:
            if axis == "x":
                x += 1 if target > x else -1
            else:
                y += 1 if target > y else -1
            carve_point(x, y)


def _stair_cells(
    start: tuple[int, int],
    end: tuple[int, int],
    rng: random.Random,
    horizontal_first: bool | None = None,
) -> list[tuple[int, int]]:
    """从 start 到 end 的「楼梯形」斜向通道格（水平/垂直短段交替）。

    与斜直线不同：路径由 2–3 格横段与 1–2 格竖段交替组成，形如楼梯，
    在 4 向移动下同样可通行。``horizontal_first`` 指定先走横轴还是纵轴
    （None = 随机）；房间连线用它保证出口开在目标方位的墙上。
    """
    x, y = start
    tx, ty = end
    cells = [(x, y)]
    horizontal = rng.random() < 0.5 if horizontal_first is None else horizontal_first
    guard = 0
    while (x, y) != (tx, ty) and guard < 1000:
        guard += 1
        if horizontal and x != tx:
            # 横段 2–3 格，逐格雕刻保持连续。
            for _ in range(min(rng.randint(2, 3), abs(tx - x))):
                x += 1 if tx > x else -1
                cells.append((x, y))
        elif not horizontal and y != ty:
            # 竖段 1–2 格。
            for _ in range(min(rng.randint(1, 2), abs(ty - y))):
                y += 1 if ty > y else -1
                cells.append((x, y))
        elif x != tx:
            x += 1 if tx > x else -1
            cells.append((x, y))
        elif y != ty:
            y += 1 if ty > y else -1
            cells.append((x, y))
        else:
            break
        horizontal = not horizontal
    return cells


def _carve_cells(mask: list[list[bool]], cells: list[tuple[int, int]]) -> None:
    for x, y in cells:
        _carve(mask, x, y, x + 1, y + 1)


def _is_interior(mask: list[list[bool]], x: int, y: int) -> bool:
    return 1 <= x < len(mask[0]) - 1 and 1 <= y < len(mask) - 1


def _open_neighbours(mask: list[list[bool]], x: int, y: int) -> int:
    """四邻中开放格的数量（越界按墙算）。"""
    height, width = len(mask), len(mask[0])
    total = 0
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nx < width and 0 <= ny < height and not mask[ny][nx]:
            total += 1
    return total


def _open_components(mask: list[list[bool]]) -> list[set[tuple[int, int]]]:
    """内圈（不含最外圈边界）的所有开放连通块。"""
    height, width = len(mask), len(mask[0])
    seen: set[tuple[int, int]] = set()
    components: list[set[tuple[int, int]]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if mask[y][x] or (x, y) in seen:
                continue
            component = {(x, y)}
            seen.add((x, y))
            queue = deque([(x, y)])
            while queue:
                cx, cy = queue.popleft()
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 1 <= nx < width - 1 and 1 <= ny < height - 1 and not mask[ny][nx] and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        component.add((nx, ny))
                        queue.append((nx, ny))
            components.append(component)
    return components


def _despeckle(mask: list[list[bool]]) -> None:
    """清掉「噪点墙」：四面都临空的孤立墙块（规整层型用）。"""
    height, width = len(mask), len(mask[0])
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if mask[y][x] and _open_neighbours(mask, x, y) == 4:
                mask[y][x] = False


def _speckle(mask: list[list[bool]], rng: random.Random, count: int) -> None:
    """撒椒盐噪点：在开阔处放孤立墙块（破碎层型用）。"""
    if count <= 0:
        return
    height, width = len(mask), len(mask[0])
    placed = 0
    for _ in range(count * 12):
        if placed >= count:
            break
        x = rng.randrange(1, width - 1)
        y = rng.randrange(1, height - 1)
        if mask[y][x] or _open_neighbours(mask, x, y) != 4:
            continue
        mask[y][x] = True
        placed += 1


def _erode(mask: list[list[bool]], rng: random.Random, passes: int = 2, chance: float = 0.09) -> None:
    """啃噬墙体边缘：贴着开放格的墙按概率被抹掉，边缘因此变得破碎参差。"""
    height, width = len(mask), len(mask[0])
    for _ in range(max(1, passes)):
        snapshot = [row[:] for row in mask]
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if not snapshot[y][x]:
                    continue
                if _open_neighbours(snapshot, x, y) and rng.random() < chance:
                    mask[y][x] = False


def _cap_internal_wall_thickness(mask: list[list[bool]], max_thickness: int = 3) -> None:
    """在不改变外圈边界的前提下，将内部连续实心段限制为最多 ``max_thickness`` 格。

    房间生成先从整张实心图挖空，房间间距在极端随机种子下可能形成很厚的墙带。
    这里用稀疏切口把厚墙分成 1-3 格的墙段；切口属于可通行的普通聚合物，
    随后由连通性修复步骤保证所有开放区域仍可到达。
    """
    if max_thickness < 1:
        raise ValueError("墙体厚度上限必须至少为 1 格")
    height, width = len(mask), len(mask[0])

    def cap_runs(get_cell, clear_cell, length: int) -> None:
        for fixed in range(1, length - 1):
            run_start: int | None = None
            for offset in range(1, (width if get_cell is row_getter else height) - 1):
                solid = get_cell(fixed, offset)
                if solid and run_start is None:
                    run_start = offset
                elif not solid and run_start is not None:
                    for cut in range(run_start + max_thickness, offset, max_thickness + 1):
                        clear_cell(fixed, cut)
                    run_start = None
            if run_start is not None:
                end = (width if get_cell is row_getter else height) - 1
                for cut in range(run_start + max_thickness, end, max_thickness + 1):
                    clear_cell(fixed, cut)

    # Separate closures keep the scan logic identical for rows and columns.
    def row_getter(y: int, x: int) -> bool:
        return mask[y][x]

    def row_clearer(y: int, x: int) -> None:
        mask[y][x] = False

    def column_getter(x: int, y: int) -> bool:
        return mask[y][x]

    def column_clearer(x: int, y: int) -> None:
        mask[y][x] = False

    cap_runs(row_getter, row_clearer, height)
    cap_runs(column_getter, column_clearer, width)


# 房间尺寸：最小 4×4（叶子再往里留一圈墙就是 6），最大由递归二分的几何下限兜住
# （叶子短边小于 13 就停止再切，因此房间边长天然不超过 10）。
_MIN_ROOM_SIDE = 4
_MIN_LEAF_SIDE = _MIN_ROOM_SIDE + 2
_ROOM_MAX_SIDE = 13
# 小房间簇的出现概率：抽到小目标的子树会长出一窝小房间，其余长出大房间。
_SMALL_TARGET_CHANCE = 0.3
# 大小已经合格时仍继续切的概率：往小的一侧再添一点随机。
_EXTRA_SPLIT_CHANCE = 0.25
# 每个房间的通路数目标（大房间额外再加）
_ROOM_LINK_MIN = 2
_ROOM_LINK_MAX = 5
_ROOM_LINK_LARGE_SIDE = 8


def _rect_center(rect: tuple[int, int, int, int]) -> tuple[int, int]:
    x, y, w, h = rect
    return x + w // 2, y + h // 2


def _polyline(ax: int, ay: int, bx: int, by: int, horizontal_first: bool) -> list[tuple[int, int]]:
    """从 A 到 B 的直角折线（含端点），horizontal_first 决定先走横轴还是纵轴。"""
    x, y = ax, ay
    cells = [(x, y)]
    first, second = ("x", "y") if horizontal_first else ("y", "x")
    for axis in (first, second):
        target = bx if axis == "x" else by
        while (x if axis == "x" else y) != target:
            if axis == "x":
                x += 1 if target > x else -1
            else:
                y += 1 if target > y else -1
            cells.append((x, y))
    return cells


def _room_link_target(rng: random.Random, width: int, height: int) -> int:
    """这个房间想要的通路条数：至少两条，大房间更多。"""
    side = max(width, height)
    want = _ROOM_LINK_MIN
    if side >= _ROOM_LINK_LARGE_SIDE:
        want += 1
    if side >= _ROOM_LINK_LARGE_SIDE + 3:
        want += 1
    if rng.random() < 0.45:
        want += 1
    return min(_ROOM_LINK_MAX, want)


def _augment_room_links(
    mask: list[list[bool]],
    rng: random.Random,
    rooms: list[tuple[int, int, int, int]],
    links: list[set[int]],
) -> None:
    """把一棵树状的房间连通图补成网。

    规则：每个房间至少 ``_ROOM_LINK_MIN`` 条通路（房间越大越多），并且**尽量把每条
    通路开在房间的不同边上**——同一侧再开一条只会共用同一个门洞，算不上第二条通路。
    走廊避开穿越第三间房，否则补出来的路会把无关的房间串成一条通道。
    """
    if len(rooms) < 2:
        return

    def center(index: int) -> tuple[int, int]:
        x, y, w, h = rooms[index]
        return x + w // 2, y + h // 2

    def side_of(index: int, point: tuple[int, int]) -> str:
        cx, cy = center(index)
        if abs(point[0] - cx) >= abs(point[1] - cy):
            return "right" if point[0] > cx else "left"
        return "down" if point[1] > cy else "up"

    _OPPOSITE = {"left": "right", "right": "left", "up": "down", "down": "up"}

    def crosses_third_room(a: int, b: int, path: list[tuple[int, int]]) -> bool:
        for px, py in path:
            for index, (rx, ry, rw, rh) in enumerate(rooms):
                if index in (a, b):
                    continue
                if rx <= px < rx + rw and ry <= py < ry + rh:
                    return True
        return False

    used_sides: list[set[str]] = [set() for _ in rooms]
    for index, others in enumerate(links):
        for other in others:
            used_sides[index].add(side_of(index, center(other)))

    def link(a: int, b: int, respect_sides: bool) -> bool:
        ax, ay = center(a)
        bx, by = center(b)
        side = side_of(a, (bx, by))
        if respect_sides and side in used_sides[a]:
            return False
        for horizontal_first in rng.sample((True, False), 2):
            # 楼梯形通道：先走朝向目标方位的轴，出口落在选定的墙上。
            path = _stair_cells(
                (ax, ay), (bx, by), rng,
                horizontal_first=(horizontal_first == (side in ("left", "right"))),
            )
            if crosses_third_room(a, b, path):
                continue
            _carve_cells(mask, path)
            links[a].add(b)
            links[b].add(a)
            used_sides[a].add(side)
            used_sides[b].add(_OPPOSITE[side])
            return True
        return False

    # 大房间优先：先把大房间的通路开出来，避免被相邻小房间抢光可用边。
    order = sorted(range(len(rooms)), key=lambda index: -rooms[index][2] * rooms[index][3])
    for index in order:
        want = _room_link_target(rng, *rooms[index][2:])
        while len(links[index]) < want:
            cx, cy = center(index)
            candidates = sorted(
                (other for other in range(len(rooms)) if other != index and other not in links[index]),
                key=lambda other: abs(center(other)[0] - cx) + abs(center(other)[1] - cy),
            )
            if not any(link(index, other, True) for other in candidates[:8]):
                break
    # 兜底：宁可两条通路开在同一侧，也不留只有一条出路的房间。
    for index in order:
        while len(links[index]) < _ROOM_LINK_MIN:
            cx, cy = center(index)
            candidates = sorted(
                (other for other in range(len(rooms)) if other != index and other not in links[index]),
                key=lambda other: abs(center(other)[0] - cx) + abs(center(other)[1] - cy),
            )
            if not any(link(index, other, False) for other in candidates[:8]):
                break


def _bsp_rooms(rng: random.Random, width: int, height: int, tidy: bool) -> tuple[list[list[bool]], list[tuple[int, int, int, int]]]:
    """递归二分（BSP）生成房间，并把房间之间的通路补成网。

    返回 ``(掩码, 房间矩形列表)``，房间矩形为 ``(左, 上, 宽, 高)``。

    房间大小：每个节点随机抽一个「边长目标」（三成概率是小房间簇），只要当前区域
    还放得下的房间超过目标就继续切；目标向子节点传递时取最小值，所以某一支抽出小
    目标，整条分支都会长成一窝小房间。几何上叶子短边小于 13 就停止再切，房间边长
    因此天然落在 4 到 10 之间——下限守住了「至少 4×4」，上限由算法自身兜住。

    通路：兄弟房之间必有一条走廊保证连通，之后 ``_augment_room_links`` 把连通图补成
    网，让多数房间拥有 2-4 条通路（大房间更多），而不是树状的一条独路。

    ``tidy=True`` 时房间刚好填满叶子（四边各留 1 格墙），墙体是干净的直线、没有孤立
    墙块；``tidy=False`` 时房间还可以在叶子内随机缩小偏移，作为「破碎的房间」的底子。
    """

    mask = _new_mask(width, height)
    rooms: list[tuple[int, int, int, int]] = []
    links: list[set[int]] = []
    cap = max(_MIN_ROOM_SIDE + 1, min(_ROOM_MAX_SIDE, min(width, height) // 3))

    def split_at(size: int) -> int:
        """切点取中间三分之一：叶子（也就是房间）更接近方形，不会切出细长条。"""
        low = max(_MIN_LEAF_SIDE, size // 3)
        high = min(size - _MIN_LEAF_SIDE - 1, size - size // 3)
        if low > high:
            low, high = _MIN_LEAF_SIDE, size - _MIN_LEAF_SIDE - 1
        return rng.randint(low, high)

    def carve_room(x: int, y: int, w: int, h: int) -> int | None:
        max_w, max_h = w - 2, h - 2
        if max_w < 3 or max_h < 3:
            return None
        if tidy:
            room_w, room_h = max_w, max_h
        else:
            # 破碎的底子允许房间不满叶子，但仍不小于 _MIN_ROOM_SIDE。
            room_w = max_w if max_w <= _MIN_ROOM_SIDE else rng.randint(max(_MIN_ROOM_SIDE, max_w // 2), max_w)
            room_h = max_h if max_h <= _MIN_ROOM_SIDE else rng.randint(max(_MIN_ROOM_SIDE, max_h // 2), max_h)
        left = x + rng.randint(1, w - room_w - 1)
        top = y + rng.randint(1, h - room_h - 1)
        _carve(mask, left, top, left + room_w, top + room_h)
        rooms.append((left, top, room_w, room_h))
        links.append(set())
        return len(rooms) - 1

    def build(x: int, y: int, w: int, h: int, target: int, depth: int) -> int | None:
        can_split_x = w >= _MIN_LEAF_SIDE * 2 + 1
        can_split_y = h >= _MIN_LEAF_SIDE * 2 + 1
        too_big = max(w - 2, h - 2) > target
        if (can_split_x or can_split_y) and (too_big or (depth < 12 and rng.random() < _EXTRA_SPLIT_CHANCE)):
            if can_split_x and can_split_y:
                # 八成概率切较长的一边，房间更接近方形，观感更整齐。
                horizontal = (h >= w) if rng.random() < 0.8 else rng.random() < 0.5
            else:
                horizontal = can_split_y
            child_target = min(target, random_target())
            if horizontal:
                cut = split_at(h)
                first = build(x, y, w, cut, child_target, depth + 1)
                second = build(x, y + cut + 1, w, h - cut - 1, child_target, depth + 1)
            else:
                cut = split_at(w)
                first = build(x, y, cut, h, child_target, depth + 1)
                second = build(x + cut + 1, y, w - cut - 1, h, child_target, depth + 1)
            if first is not None and second is not None:
                # 楼梯形斜向通道：水平/垂直短段交替，避免斜直线。
                stair = _stair_cells(_rect_center(rooms[first]), _rect_center(rooms[second]), rng)
                _carve_cells(mask, stair)
                links[first].add(second)
                links[second].add(first)
            return first if first is not None else second
        return carve_room(x, y, w, h)

    def random_target() -> int:
        """本节点期望的房间边长上限：三成概率抽到「小房间簇」，由此拉开尺寸差距。"""
        if cap <= _MIN_ROOM_SIDE + 2:
            return cap
        if rng.random() < _SMALL_TARGET_CHANCE:
            return rng.randint(_MIN_ROOM_SIDE, min(_MIN_ROOM_SIDE + 2, cap))
        return rng.randint(min(_MIN_ROOM_SIDE + 3, cap), cap)

    build(1, 1, width - 2, height - 2, cap, 0)
    _augment_room_links(mask, rng, rooms, links)
    if tidy:
        # 只清孤立墙块；这里**不**做墙厚截断——那会在长墙上按固定间距凿出一排
        # 规则孔洞，正是「整齐」要避免的噪点。规整切分本身保证墙最厚 3 格。
        _despeckle(mask)
    return mask, rooms


def _tidy_rooms(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """整齐的房间：BSP 递归二分，房间规整、墙体基本没有噪点。"""
    return _bsp_rooms(rng, width, height, tidy=True)[0]


def _broken_rooms(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """破碎的房间：同一套房间底子，但墙体被啃噬、并撒了大量椒盐噪点。"""
    mask = _bsp_rooms(rng, width, height, tidy=False)[0]
    _erode(mask, rng, passes=2, chance=0.09)
    _cap_internal_wall_thickness(mask)
    # 破碎的缺口：随机在墙上凿出 1-3 格长的小口子，房间之间犬牙交错。
    height, width_ = len(mask), len(mask[0])
    for _ in range(max(4, (width_ - 2) * (height - 2) // 220)):
        x = rng.randrange(1, width_ - 1)
        y = rng.randrange(1, height - 1)
        if not mask[y][x]:
            continue
        horizontal = rng.random() < 0.5
        length = rng.randint(1, 3)
        for offset in range(length):
            nx, ny = (x + offset, y) if horizontal else (x, y + offset)
            if _is_interior(mask, nx, ny):
                mask[ny][nx] = False
    _speckle(mask, rng, max(3, (width_ - 2) * (height - 2) // 90))
    return mask


def _settlement(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """居民区：房间生长。从中心一间房出发，贴着已有房间向外长，形成成片街区。"""
    mask = _new_mask(width, height)
    seed_w = max(3, min(rng.randint(4, 7), width - 4))
    seed_h = max(3, min(rng.randint(3, 5), height - 4))
    x0, y0 = (width - seed_w) // 2, (height - seed_h) // 2
    rooms: list[tuple[int, int, int, int]] = [(x0, y0, seed_w, seed_h)]
    _carve(mask, x0, y0, x0 + seed_w, y0 + seed_h)
    target = max(12, min(70, (width - 2) * (height - 2) // 55))

    def overlaps(left: int, top: int, room_w: int, room_h: int) -> bool:
        for ox, oy, ow, oh in rooms:
            if left < ox + ow + 1 and left + room_w + 1 > ox and top < oy + oh + 1 and top + room_h + 1 > oy:
                return True
        return False

    for _ in range(target * 80):
        if len(rooms) >= target:
            break
        px, py, pw, ph = rng.choice(rooms)
        room_w = rng.randint(4, max(4, min(8, width // 6)))
        room_h = rng.randint(3, max(3, min(6, height // 6)))
        # 多数房子紧贴着长（gap=1），成排连成街区；偶尔留出小巷。
        gap = rng.choice((1, 1, 1, 2))
        direction = rng.choice(("left", "right", "up", "down"))
        if rng.random() < 0.65:
            # 多数时候朝远离街区重心的方向长，避免整片居民区挤在一角。
            center_x = sum(ox + ow / 2 for ox, oy, ow, oh in rooms) / len(rooms)
            center_y = sum(oy + oh / 2 for ox, oy, ow, oh in rooms) / len(rooms)
            away_x = "right" if px >= center_x else "left"
            away_y = "down" if py >= center_y else "up"
            direction = away_x if rng.random() < 0.5 else away_y
        if direction == "left":
            left = px - room_w - gap
            top = py + rng.randint(-(room_h - 1), ph - 1)
        elif direction == "right":
            left = px + pw + gap
            top = py + rng.randint(-(room_h - 1), ph - 1)
        elif direction == "up":
            top = py - room_h - gap
            left = px + rng.randint(-(room_w - 1), pw - 1)
        else:
            top = py + ph + gap
            left = px + rng.randint(-(room_w - 1), pw - 1)
        top = max(1, min(height - room_h - 1, top))
        left = max(1, min(width - room_w - 1, left))
        if overlaps(left, top, room_w, room_h):
            continue
        rooms.append((left, top, room_w, room_h))
        _carve(mask, left, top, left + room_w, top + room_h)
        _carve_cells(
            mask,
            _stair_cells(
                (px + pw // 2, py + ph // 2),
                (left + room_w // 2, top + room_h // 2),
                rng,
            ),
        )
    # 街道：每间房再连到最近的一间，街区之间形成环路而不是纯树状。
    centers = [(ox + ow // 2, oy + oh // 2) for ox, oy, ow, oh in rooms]
    for index, start in enumerate(centers):
        nearest = min(
            (other for position, other in enumerate(centers) if position != index),
            key=lambda point: abs(point[0] - start[0]) + abs(point[1] - start[1]),
            default=None,
        )
        if nearest is None:
            continue
        _carve_corridor(mask, start, nearest, 1, rng.random() < 0.5)
    return mask


def _cavern(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """洞穴：元胞自动机。随机填充后按邻居数平滑数轮，再填掉过小的空腔。

    初始填充率 0.45 会平滑出连片的巨大空腔，整层显得太空旷；提高到 0.50
    并多做一轮平滑，让洞窟之间留下更多岩体、通道更曲折，但填充率仍低于
    0.5 的临界值，不会退化成实心岩层。
    """
    mask = _new_mask(width, height)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            mask[y][x] = rng.random() < 0.50
    for _ in range(5):
        snapshot = [row[:] for row in mask]
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                walls = 0
                for ny in range(y - 1, y + 2):
                    for nx in range(x - 1, x + 2):
                        if (nx, ny) == (x, y):
                            continue
                        if nx < 1 or ny < 1 or nx > width - 2 or ny > height - 2 or snapshot[ny][nx]:
                            walls += 1
                if snapshot[y][x]:
                    mask[y][x] = walls >= 4
                else:
                    mask[y][x] = walls >= 5
    _prune_small_cavities(mask, max(6, (width - 2) * (height - 2) // 150))
    return mask


def _prune_small_cavities(mask: list[list[bool]], min_size: int) -> None:
    """填掉过小的封闭空腔，只留下主要洞窟（避免后期被硬凿出大量直线通道）。"""
    components = _open_components(mask)
    if len(components) <= 1:
        return
    largest = max(len(component) for component in components)
    for component in components:
        if len(component) < min_size and len(component) < largest:
            for x, y in component:
                mask[y][x] = True


def _maze(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """迷宫：DFS 挖墙（递归回溯），单格通道网络。

    生成后先由 braid 打通死胡同；再在墙上随机凿一批单格洞（``_maze_holes``），
    密度约等于整齐房间/居民区的通道量级，让迷宫多一圈圈短路环路。
    """
    mask = _new_mask(width, height)
    start = (1, 1)
    mask[1][1] = False
    visited = {start}
    stack = [start]
    while stack:
        x, y = stack[-1]
        candidates = [
            (nx, ny)
            for nx, ny in ((x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2))
            if 1 <= nx < width - 1 and 1 <= ny < height - 1 and (nx, ny) not in visited
        ]
        if not candidates:
            stack.pop()
            continue
        nx, ny = rng.choice(candidates)
        mask[(y + ny) // 2][(x + nx) // 2] = False
        mask[ny][nx] = False
        visited.add((nx, ny))
        stack.append((nx, ny))
    _maze_holes(mask, rng)
    return mask


# 迷宫破洞密度：洞数 ≈ 整齐房间/居民区的通道量级（60×60 实测整齐房间通路
# 65–82 条、居民区 ≈122 条），取内部面积 A//40（下限 4）——中等密度，且明显
# 低于破碎房间（那边是 erode 啃噬 + 满地 1-3 格缺口）。这些洞由 _maze 直接在
# 墙上凿出，独立于通道的尝试生成；后续 braid 只处理死胡同，不会动它们。
_MAZE_HOLE_AREA_PER_HOLE = 40


def _maze_holes(mask: list[list[bool]], rng: random.Random) -> None:
    """在迷宫的墙上随机凿单格洞，制造额外的环路开口。

    只挑「左右邻开放、上下邻是墙」的墙格（或上下镜像）——凿开后是 1 格宽通道
    之间的便捷开口。逐个试凿：若某个洞会与相邻洞/通道拼出 2×2 的开放块则放弃
    该洞（回滚），保证迷宫的单宽观感不被破坏。
    """
    height, width = len(mask), len(mask[0])
    count = max(4, ((width - 2) * (height - 2)) // _MAZE_HOLE_AREA_PER_HOLE)
    candidates: list[tuple[int, int]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if not mask[y][x]:
                continue
            open_lr = (
                not mask[y][x - 1] and not mask[y][x + 1]
                and mask[y - 1][x] and mask[y + 1][x]
            )
            open_ud = (
                not mask[y - 1][x] and not mask[y + 1][x]
                and mask[y][x - 1] and mask[y][x + 1]
            )
            if open_lr or open_ud:
                candidates.append((x, y))
    rng.shuffle(candidates)

    def makes_2x2_open(x: int, y: int) -> bool:
        """试凿 (x, y) 后，含它的四个 2×2 邻域是否出现全开放块。"""
        for top in (y - 1, y):
            for left in (x - 1, x):
                if all(
                    not mask[by][bx]
                    for by in (top, top + 1)
                    for bx in (left, left + 1)
                ):
                    return True
        return False

    dug = 0
    for x, y in candidates:
        if dug >= count:
            break
        mask[y][x] = False
        if makes_2x2_open(x, y):
            mask[y][x] = True  # 会拼出 2×2 开放块：放弃这个洞。
            continue
        dug += 1


def _long_corridor(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """长廊：沿长轴的主廊 + 两侧交替侧室 + 平行副廊与横切通道。

    调用方（GameState）已经把地图尺寸改成极端长宽比，这里只按「哪条边更长」
    决定主轴方向；即使拿到接近正方的尺寸也能退化为一条贯通的长廊。
    """
    mask = _new_mask(width, height)
    horizontal = width >= height
    if horizontal:
        axis = height // 2
        main_width = rng.randint(2, 3)
        _carve(mask, 1, axis - main_width // 2, width - 1, axis - main_width // 2 + main_width)
        room_w = max(4, min(9, width // 9))
        x, index = 2, 0
        while x < width - room_w - 2:
            room_h = rng.randint(4, max(4, min(12, height // 3 + 2)))
            top = 1 if index % 2 == 0 else height - room_h - 2
            if rng.random() < 0.35:
                top = 1 if rng.random() < 0.5 else height - room_h - 2
            _carve(mask, x, top, x + room_w, top + room_h)
            _carve_corridor(
                mask,
                (x + room_w // 2, axis),
                (x + room_w // 2, top + room_h // 2),
                rng.randint(1, 2),
                False,
            )
            index += 1
            x += room_w + rng.randint(1, 3)
        for side in (-1, 1):
            if rng.random() < 0.75:
                other = axis + side * rng.randint(3, max(3, height // 3))
                if 1 <= other < height - 1:
                    _carve(mask, 1, other, width - 1, other + 1)
        for _ in range(max(4, width // 10)):
            cross_x = rng.randrange(2, width - 2)
            _carve(mask, cross_x, 1, cross_x + 1, height - 1)
    else:
        axis = width // 2
        main_width = rng.randint(2, 3)
        _carve(mask, axis - main_width // 2, 1, axis - main_width // 2 + main_width, height - 1)
        room_h = max(4, min(9, height // 9))
        y, index = 2, 0
        while y < height - room_h - 2:
            room_w = rng.randint(4, max(4, min(12, width // 3 + 2)))
            left = 1 if index % 2 == 0 else width - room_w - 2
            if rng.random() < 0.35:
                left = 1 if rng.random() < 0.5 else width - room_w - 2
            _carve(mask, left, y, left + room_w, y + room_h)
            _carve_corridor(
                mask,
                (axis, y + room_h // 2),
                (left + room_w // 2, y + room_h // 2),
                rng.randint(1, 2),
                True,
            )
            index += 1
            y += room_h + rng.randint(1, 3)
        for side in (-1, 1):
            if rng.random() < 0.75:
                other = axis + side * rng.randint(3, max(3, width // 3))
                if 1 <= other < width - 1:
                    _carve(mask, other, 1, other + 1, height - 1)
        for _ in range(max(4, height // 10)):
            cross_y = rng.randrange(2, height - 2)
            _carve(mask, 1, cross_y, width - 1, cross_y + 1)
    return mask


def _infinite_room(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    """无限房间：网格划分的房间群——每块是一个带门口的方形房间。

    每 6×5 格划一块：四周 1 格厚墙、内部全开，形成一个个「房间」；
    相邻房间共享墙上错位开 1–2 个门，走廊感由房间串门构成。
    """
    mask = _new_mask(width, height)
    wall_xs = list(range(5, width - 3, 6))
    wall_ys = list(range(4, height - 3, 5))
    # 网格墙
    for wx in wall_xs:
        for y in range(1, height - 1):
            mask[y][wx] = True
    for wy in wall_ys:
        for x in range(1, width - 1):
            mask[wy][x] = True
    # 挖房间内部（墙之间；_carve 的 right/bottom 为开区间端点）
    starts_x = [1] + [wx + 1 for wx in wall_xs]
    ends_x = wall_xs + [width - 1]
    starts_y = [1] + [wy + 1 for wy in wall_ys]
    ends_y = wall_ys + [height - 1]
    for sy, ey in zip(starts_y, ends_y):
        for sx, ex in zip(starts_x, ends_x):
            _carve(mask, sx, sy, ex, ey)
    # 门口：每道竖墙在每个房间行带错位开 1–2 个门；横墙同理
    for wx in wall_xs:
        for sy, ey in zip(starts_y, ends_y):
            low, high = max(1, sy), min(ey, height - 2)
            if high - low < 1:
                continue
            doors = rng.randint(1, 2)
            for door_y in rng.sample(range(low, high), min(doors, high - low)):
                mask[door_y][wx] = False
    for wy in wall_ys:
        for sx, ex in zip(starts_x, ends_x):
            low, high = max(1, sx), min(ex, width - 2)
            if high - low < 1:
                continue
            doors = rng.randint(1, 2)
            for door_x in rng.sample(range(low, high), min(doors, high - low)):
                mask[wy][door_x] = False
    return mask


def _obstacle_plain(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    mask = _new_mask(width, height)
    _carve(mask, 1, 1, width - 1, height - 1)
    fixed = ((4, 4), (width - 5, 4), (4, height - 5), (width - 5, height - 5))
    for x, y in fixed:
        if 1 < x < width - 2 and 1 < y < height - 2:
            mask[y][x] = True
    for _ in range(max(4, width * height // 85)):
        x = rng.randint(2, width - 3)
        y = rng.randint(2, height - 3)
        horizontal = rng.choice((True, False))
        length = rng.randint(1, 4)
        for offset in range(length):
            nx, ny = (x + offset, y) if horizontal else (x, y + offset)
            if nx < width - 2 and ny < height - 2:
                mask[ny][nx] = True
    # 噪声墙体：大量孤立的 1 格墙，8 邻域内不与任何墙相连（保持不连片）。
    target = max(10, width * height // 30)
    placed = 0
    for _ in range(target * 20):
        if placed >= target:
            break
        x = rng.randint(2, width - 3)
        y = rng.randint(2, height - 3)
        if mask[y][x]:
            continue
        if any(
            mask[ny][nx]
            for nx, ny in (
                (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1),
            )
        ):
            continue
        mask[y][x] = True
        placed += 1
    return mask


def _hall(rng: random.Random, width: int, height: int) -> list[list[bool]]:
    mask = _new_mask(width, height)
    margin_x = max(2, width // 9)
    margin_y = max(2, height // 9)
    _carve(mask, margin_x, margin_y, width - margin_x, height - margin_y)
    for top in (2, height - 6):
        if 1 <= top < height - 3:
            _carve(mask, 2, top, min(width - 2, 9), min(height - 1, top + 4))
            _carve(mask, max(2, width - 9), top, width - 2, min(height - 1, top + 4))
    cy = height // 2
    _carve_corridor(mask, (2, cy), (width - 3, cy), rng.randint(1, 3), True)
    for x in (margin_x + 2, width - margin_x - 3):
        for y in (margin_y + 2, height - margin_y - 3):
            if not (width // 3 <= x <= width * 2 // 3 and height // 3 <= y <= height * 2 // 3):
                mask[y][x] = True
    return mask


def _connect_open_components(
    mask: list[list[bool]],
    protected: "list[tuple[int, int, int, int]] | None" = None,
) -> None:
    """把彼此不相连的开放区域用最短通道接到一起。

    ``protected`` 是保护区矩形列表（vault 盖章区域）：保护区内的**实心格**
    不可凿——连通修复只从区域外绕行（或借用区域内已有的开放格通过），
    模板围出的封闭形状与开口位置因此被尊重。找不到绕行路径时才回退到
    直线凿缝（连通性优先于形状）。
    """
    height, width = len(mask), len(mask[0])
    blocked: set[tuple[int, int]] = set()
    for pl, pt, pr, pb in protected or ():
        for y in range(max(0, pt), min(height, pb + 1)):
            for x in range(max(0, pl), min(width, pr + 1)):
                blocked.add((x, y))
    components = _open_components(mask)
    if not components:
        mask[height // 2][width // 2] = False
        return
    while len(components) > 1:
        main = max(components, key=len)
        # other 必须取自「其余连通块」：全部块等大时 max/min 会返回同一个
        # 集合，target ∈ main 会让锚点与目标重合、切口零进度而永远循环。
        other = min((component for component in components if component is not main), key=len)
        target = next(iter(other))
        anchor = min(main, key=lambda point: abs(point[0] - target[0]) + abs(point[1] - target[1]))
        if not _carve_seam(mask, anchor, target, blocked):
            # 绕行失败（保护区把两块完全隔开）：退回直线凿缝。
            x, y = anchor
            while x != target[0]:
                x += 1 if target[0] > x else -1
                mask[y][x] = False
            while y != target[1]:
                y += 1 if target[1] > y else -1
                mask[y][x] = False
        # 重新计算连通块：一道切口可能同时接通多个孤立区域。
        components = _open_components(mask)


def _carve_seam(
    mask: list[list[bool]],
    anchor: tuple[int, int],
    target: tuple[int, int],
    blocked: set[tuple[int, int]],
) -> bool:
    """BFS 找 anchor→target 的最短凿缝路径，保护区内的实心格绕行。

    开放格（含保护区内的开放格）可自由通行；实心格可凿，除非位于保护
    区内。找到路径时沿途全部凿开并返回 True。
    """
    from collections import deque

    height, width = len(mask), len(mask[0])
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
            if (nx, ny) in blocked and mask[ny][nx]:
                continue  # 保护区内的实心格：不可凿（开放格可通过）。
            prev[(nx, ny)] = current
            queue.append((nx, ny))
    if prev.get(target) is None and target != anchor:
        return False
    node: tuple[int, int] | None = target
    while node is not None:
        x, y = node
        mask[y][x] = False
        node = prev[node]
    return True


def braid_dead_ends(
    mask: list[list[bool]],
    rng: random.Random,
    ratio: float = 1.0,
    protected: "list[tuple[int, int, int, int]] | None" = None,
) -> None:
    """braid 解编：打通死胡同。

    第一轮「成环」：死胡同优先凿穿一格墙接回已有通道（对面还是开放格时最理想），
    把树枝状结构变成有环路的网。第二轮「填平」：实在接不上的死胡同逐格填成墙——
    只删叶子节点，不会破坏其余部分的连通性。

    ``protected``（vault 保护罩）内的格子不参与 braid：成环不在保护区内凿墙、
    填平不吞保护区内的开放格——模板内部的走廊与死胡同属于设计形状。
    """
    height, width = len(mask), len(mask[0])
    blocked: set[tuple[int, int]] = set()
    for pl, pt, pr, pb in protected or ():
        for y in range(max(0, pt), min(height, pb + 1)):
            for x in range(max(0, pl), min(width, pr + 1)):
                blocked.add((x, y))

    def dead_ends() -> list[tuple[int, int]]:
        return [
            (x, y)
            for y in range(1, height - 1)
            for x in range(1, width - 1)
            if not mask[y][x] and (x, y) not in blocked and _open_neighbours(mask, x, y) == 1
        ]

    for _ in range(6):
        pending = dead_ends()
        if not pending:
            return
        rng.shuffle(pending)
        carved = False
        for x, y in pending:
            if mask[y][x] or _open_neighbours(mask, x, y) != 1:
                continue
            if rng.random() > ratio:
                continue
            directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            rng.shuffle(directions)
            loops = [
                (dx, dy)
                for dx, dy in directions
                if _is_interior(mask, x + dx, y + dy)
                and (x + dx, y + dy) not in blocked
                and mask[y + dy][x + dx]
                and _is_interior(mask, x + dx * 2, y + dy * 2)
                and (x + dx * 2, y + dy * 2) not in blocked
                and not mask[y + dy * 2][x + dx * 2]
            ]
            if not loops:
                continue
            dx, dy = loops[0]
            mask[y + dy][x + dx] = False
            carved = True
        if not carved:
            break

    # 剩下的死胡同：逐轮填平，直到没有死胡同或地图被吃得太多。
    open_total = sum(1 for row in mask for solid in row if not solid)
    floor_open = max(8, open_total // 4)
    while True:
        pending = dead_ends()
        if not pending or open_total - len(pending) < floor_open:
            break
        for x, y in pending:
            mask[y][x] = True
        open_total -= len(pending)


def _ensure_anchor_connections(
    mask: list[list[bool]],
    anchors: "list[tuple[int, int]]",
    regions: "list[tuple[int, int, int, int]]",
    precious: "list[tuple[int, int]] | None" = None,
) -> None:
    """收尾保障：每个连通符号（@）都必须与主连通块（外界）联通。

    - 锚点已在主块 → 无需处理（包括「周围都是空地」的情况）；
    - 锚点不在主块 → 从锚点凿一条到主块的最短通道：本模板自己的墙可以凿
      （等于把 @ 位置的门开出去），其他模板的保护区实心格照旧绕行；
    - 实在无路可绕时忽略保护凿穿（连通性优先）。
    """
    if not anchors:
        return
    height, width = len(mask), len(mask[0])

    def protected_blocker(skip: tuple[int, int, int, int] | None) -> set[tuple[int, int]]:
        blocked: set[tuple[int, int]] = set()
        for pl, pt, pr, pb in regions:
            if (pl, pt, pr, pb) == skip:
                continue
            for y in range(max(0, pt), min(height, pb + 1)):
                for x in range(max(0, pl), min(width, pr + 1)):
                    blocked.add((x, y))
        return blocked

    for anchor in anchors:
        components = _open_components(mask)
        if not components:
            return
        main = max(components, key=len)
        if anchor in main:
            continue  # 已与外界联通（周围是空地 / 已有相邻通道继承）。
        ax, ay = anchor
        own_region = next(
            ((pl, pt, pr, pb) for pl, pt, pr, pb in regions
             if pl <= ax <= pr and pt <= ay <= pb),
            None,
        )
        blocked = protected_blocker(own_region)
        # loot 石台等贵重格任何情况下都不被凿路通过。
        blocked |= set(precious or ())
        if not _carve_seam(mask, anchor, next(iter(main)), blocked):
            # 无绕行路径：忽略保护区凿穿（保连通），但仍避开贵重格。
            _carve_seam(mask, anchor, next(iter(main)), set(precious or ()))


_GENERATORS = {
    "整齐的房间": _tidy_rooms,
    "破碎的房间": _broken_rooms,
    "居民区": _settlement,
    "洞穴": _cavern,
    "迷宫": _maze,
    "长廊": _long_corridor,
    "无限房间": _infinite_room,
    "碎影平原": _obstacle_plain,
    "回声大厅": _hall,
}

# ---- 模板数量档位 ----------------------------------------------------------
# 三元组 = (前置池次数, 公用后置池次数, 层型专属池次数)，取值都是 (下限, 上限)。
# 2026-10-11 玩家反馈模板密度偏高：点名五层型（洞穴/迷宫/平原/大厅/长廊）
# 「稍微降低」——各池上限 −1、下限保持；其余层型「降低更多」——公用后置
# 与专属池直接收到固定 1。古朴（ancient）仍按 +1 上限回补。
VAULT_COUNT_PROFILES: dict[str, tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = {
    "碎影平原": ((2, 2), (3, 3), (2, 2)),
    "长廊": ((2, 2), (3, 3), (2, 2)),
    "洞穴": ((2, 2), (3, 3), (2, 2)),
    # 迷宫：单格通道网络，模板多一圈就挤一条通路；同按「稍微降低」−1。
    "迷宫": ((1, 1), (1, 1), (1, 1)),
    # 回声大厅：中央大厅自身已是大型结构，前置只补一栋；点缀与专属池降一档。
    "回声大厅": ((1, 1), (4, 4), (3, 3)),
}
# 其余层型（整齐的房间/破碎的房间/居民区/无限房间）：降低更多——
# 公用后置与专属池的上限各 −1（原 1–2 → 固定 1），每层 3–5 栋 → 3 栋。
DEFAULT_VAULT_COUNTS = ((1, 1), (1, 1), (1, 1))


def vault_count_profile(map_form: str, ancient: bool = False) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """该层型的 ``(前置, 公用后置, 专属池)`` 次数档位；古朴再各 +1 上限。"""
    pre, generic, form = VAULT_COUNT_PROFILES.get(normalize_map_form(map_form), DEFAULT_VAULT_COUNTS)
    if not ancient:
        return pre, generic, form
    return tuple((low, high + 1) for low, high in (pre, generic, form))  # type: ignore[return-value]


def room_rects(seed: int, width: int, height: int, map_form: str = "整齐的房间") -> list[tuple[int, int, int, int]]:
    """该局的房间划分 ``(左, 上, 宽, 高)``，用于核对房间尺寸与通路数。

    只重新跑一遍生成（同样的种子必然得到同样的划分），不改动任何状态；
    传入非房间层型时返回空列表。
    """
    form = normalize_map_form(map_form)
    if form not in ("整齐的房间", "破碎的房间"):
        return []
    return _bsp_rooms(random.Random(seed), width, height, tidy=form == "整齐的房间")[1]


def generate_solid_mask(seed: int, width: int, height: int, map_form: str, modifier: str = "") -> list[list[bool]]:
    """生成墙体掩码（True = 墙）；需要模板位置信息时走 *_with_vaults 版本。

    生成顺序：层型生成器 → vault 盖章 → 连接 + braid。

    vault 按层型分三路：
    - 房间类（整齐/破碎/居民区）：房间内部盖小型装饰模板（避开门口），
      居民区额外可用自己的层型专用模板；大型功能结构在保护区内单独盖章，
      小装饰避开它们。
    - 回声大厅：不叠 PRE 大型模板（中央大厅本身就是大型结构），但照常放
      POST 点缀与层型专属模板——早先整段跳过 vault，整层一个模板都没有。
    - 其余层型：PRE 大型模板（只挑放得下的、多次尝试位置）+ 连接/braid
      之后 POST 点缀（公用池 + 该层的层型专用池）。

    各层型的专属模板（FORM_VAULT_POOLS）额外保底尝试一次，且锚点只落在
    开放格上——否则在「公用池 + 专属池」的并集里随机取 1~2 个，专属模板
    常常一整层都不出现（长廊的拱门排 / 壁龛尤其明显）。

    「古朴」修饰符把房间装饰与 POST 的数量都调高。
    """
    mask, _placements = generate_solid_mask_with_vaults(seed, width, height, map_form, modifier)
    return mask


# ---------------------------------------------------------------------------
# 每层「结构自带事件 / NPC」的余额（2026-10-27）
# ---------------------------------------------------------------------------
# 一座结构可以自带一个异常地点（``event``）与一位稳定意识（``npc_id`` 或
# ``STRUCTURE_NPC_BINDING``）。过去这些绑定完全不计数：一层若盖了前置大厅、
# 后置电路厅、装饰模板各带一组，再加上随机零散投放（事件 0–2、NPC 0–2），
# 同层就能冒出四五处台子、三四位稳定意识，直接越过每层上限。
#
# 现在的口径：**结构与随机共用每层名额**。盖章时先问余额——先盖的占额、
# 后盖的让路；余额见底时不再挑「自带绑定」的模板，同池里没有无绑定候选就
# 放弃这次盖章（宁可少盖一栋，也不越限）。随机投放侧在
# ``core/generation`` 里按同一余额补位。
#
# 深层边界 28–30 由 ``mapgen/epilogue.py`` 整层接管，不走本函数，保持原样。
_SCENE_EVENT_IDS = frozenset(
    entry["event_id"] for entry in EVENT_DEFINITIONS if entry.get("scene")
)


def vault_bound_event(vault: Vault) -> str:
    """该结构落地时真的会生成一个「异常地点」的事件 id（不占额时返回空串）。

    ``scene`` 型事件（青灯入口一类）交给 ``core.scenes.install_bound_scene``
    安装成设施，不落成 ``WorldEvent``，因此不占事件余额。
    """
    if not vault.event or vault.event in _SCENE_EVENT_IDS:
        return ""
    return vault.event


def vault_bound_npc(vault: Vault) -> str:
    """该结构自带的稳定意识 id（显式 ``npc_id`` 优先，其次 id 级绑定表）。"""
    return vault.npc_id or STRUCTURE_NPC_BINDING.get(vault.vid, "")


class _StructureBudget:
    """本层结构自带事件/NPC 的剩余名额。"""

    def __init__(
        self,
        events: int = EVENT_MAX_PER_LAYER,
        npcs: int = NPC_MAX_PER_LAYER,
    ) -> None:
        self.events = events
        self.npcs = npcs

    def allows(self, vault: Vault) -> bool:
        if vault_bound_event(vault) and self.events <= 0:
            return False
        if vault_bound_npc(vault) and self.npcs <= 0:
            return False
        return True

    def take(self, vault: Vault) -> None:
        if vault_bound_event(vault):
            self.events -= 1
        if vault_bound_npc(vault):
            self.npcs -= 1


def _pick_vault(
    pool: "list[Vault] | tuple[Vault, ...]",
    rng: random.Random,
    budget: "_StructureBudget | None" = None,
) -> "Vault | None":
    """按余额筛一遍候选，再按稀有度加权抽一个；筛空返回 ``None``。"""
    if not pool:
        return None
    if budget is not None:
        pool = [vault for vault in pool if budget.allows(vault)]
        if not pool:
            return None
    return pick_by_rarity(pool, rng)


def _take_budget(budget: "_StructureBudget | None", vault: Vault) -> None:
    if budget is not None:
        budget.take(vault)


def generate_solid_mask_with_vaults(
    seed: int,
    width: int,
    height: int,
    map_form: str,
    modifier: str = "",
    depth: int = 1,
    realm_id: str = "",
) -> tuple[list[list[bool]], list[VaultPlacement]]:
    """同 generate_solid_mask，但额外返回成功盖章的 VaultPlacement 列表。

    core 生成格子时用它做两件事：按模板覆写墙种（石台/木桌子/玻璃幕墙等）、
    把稀有物品投放到 loot=True 模板中央的石台上。

    结构自带事件/NPC 走本层的**共享余额**（结构先占额、随机补位，见
    ``_StructureBudget``）：``depth`` 落在深层边界（28–30）时不设限。
    """
    map_form = normalize_map_form(map_form)
    try:
        generator = _GENERATORS[map_form]
    except KeyError as error:
        raise ValueError(f"未知层型：{map_form}") from error
    rng = random.Random(seed)
    mask = generator(rng, width, height)
    vault_rng = random.Random(seed ^ 0x9A71C)
    ancient = modifier == "古朴"
    form_pool = [v for v in FORM_VAULT_POOLS.get(map_form, ()) if v.available_at(depth, realm_id)]
    post_pool = [v for v in POST_VAULTS if v.available_at(depth, realm_id) and v.fits(width, height)]
    placements: list[VaultPlacement] = []
    # 保护罩：任何模板盖章后其区域入列——connect/braid 不凿、后置不叠盖。
    protected: list[tuple[int, int, int, int]] = []
    pre_range, generic_range, form_range = vault_count_profile(map_form, ancient)
    # 结构自带事件/NPC 的余额：深层边界（28–30）保持原样，其余层共用每层名额。
    budget = None if depth in EPILOGUE_DEPTHS else _StructureBudget()

    # 专属层保底（电路逻辑/梦中梦入口）：10 层必盖「灯塔之厅」。
    exclusive = [v for v in EXCLUSIVE_VAULTS if v.available_at(depth, realm_id)]
    for vault in exclusive:
        if budget is not None and not budget.allows(vault):
            continue
        placement = stamp_vault_near_open(mask, vault, vault_rng, attempts=40, avoid=protected)
        if placement is not None:
            placements.append(placement)
            protected.append(placement.region)
            _take_budget(budget, vault)

    def stamp_post_vaults(generic_range: tuple[int, int], form_range: tuple[int, int], pool=None) -> None:
        """先盖公用池（整图随机），再保底盖层型专属池（锚定开放格）。

        都带 ``avoid=protected``：后置模板跳过既有保护区（不叠盖在前置
        区域上），盖章成功后自己的区域也入列保护。
        """
        candidates = post_pool if pool is None else pool
        for _ in range(vault_rng.randint(*generic_range)):
            vault = _pick_vault(candidates, vault_rng, budget)
            if vault is None:
                break
            placement = try_stamp_vault(mask, vault, vault_rng, avoid=protected)
            if placement is not None:
                placements.append(placement)
                protected.append(placement.region)
                _take_budget(budget, vault)
        if form_pool:
            for _ in range(vault_rng.randint(*form_range)):
                vault = _pick_vault(form_pool, vault_rng, budget)
                if vault is None:
                    break
                placement = stamp_vault_near_open(mask, vault, vault_rng, avoid=protected)
                if placement is not None:
                    placements.append(placement)
                    protected.append(placement.region)
                    _take_budget(budget, vault)

    # PRE：按层型档位盖若干栋。只从放得下的模板里挑，再多次尝试位置——
    # 旧实现固定单次盖章，长廊/小型层上大模板永远越界，一次失败整层就没
    # vault 了；如今「长廊/洞穴/碎影平原」这类空旷层型还要多盖几栋。
    fitting = [vault for vault in PRE_VAULTS if vault.fits(width, height) and vault.available_at(depth, realm_id)]
    if fitting:
        pre_events = vault_rng.randint(*pre_range)
        # 大图保底：首次事件优先从「稀有/非常稀有」里挑——保证它们有机会
        # 生成，不会因为常见模板的权重优势而永远轮不到。
        rare_fitting = [v for v in fitting if v.rarity in ("稀有", "非常稀有")]
        for index in range(pre_events):
            pool = rare_fitting if index == 0 and rare_fitting else fitting
            pre = _pick_vault(pool, vault_rng, budget)
            if pre is None and pool is rare_fitting:
                # 稀有候选被余额筛空（都自带绑定）时，退回全池找无绑定的。
                pre = _pick_vault(fitting, vault_rng, budget)
            if pre is None:
                break
            placement = try_stamp_vault(mask, pre, vault_rng, attempts=16, avoid=protected)
            if placement is not None:
                placements.append(placement)
                protected.append(placement.region)
                _take_budget(budget, pre)

    if map_form in ("整齐的房间", "破碎的房间", "居民区"):
        # 房间内装饰：优先按 room_rects 放进房间内部；居民区没有登记的
        # 房间矩形，退回到条件式全局放置（开放格上盖章）。
        decor_pool = [v for v in ROOM_DECOR_VAULTS if v.available_at(depth, realm_id)] + form_pool
        decor_count = vault_rng.randint(4, 6) if ancient else vault_rng.randint(2, 3)
        if decor_pool:
            rects = [
                rect for rect in room_rects(seed, width, height, map_form)
                if rect[2] >= 6 and rect[3] >= 6
            ]
            if rects:
                vault_rng.shuffle(rects)
                for rect in rects:
                    if decor_count <= 0:
                        break
                    vault = _pick_vault(decor_pool, vault_rng, budget)
                    if vault is None:
                        break
                    placement = stamp_vault_in_room(mask, vault, rect, vault_rng, avoid=protected)
                    if placement is not None:
                        placements.append(placement)
                        protected.append(placement.region)
                        _take_budget(budget, vault)
                        decor_count -= 1
            else:
                for _ in range(decor_count):
                    vault = _pick_vault(decor_pool, vault_rng, budget)
                    if vault is None:
                        break
                    placement = stamp_vault_near_open(mask, vault, vault_rng, avoid=protected)
                    if placement is not None:
                        placements.append(placement)
                        protected.append(placement.region)
                        _take_budget(budget, vault)
            # 居民区等没有登记房间矩形时，专属模板再保底一次。
            if form_pool and not rects:
                vault = _pick_vault(form_pool, vault_rng, budget)
                if vault is not None:
                    placement = stamp_vault_near_open(mask, vault, vault_rng, avoid=protected)
                    if placement is not None:
                        placements.append(placement)
                        protected.append(placement.region)
                        _take_budget(budget, vault)

        stamp_post_vaults(generic_range, (0, 0), pool=[v for v in post_pool if v.circuit])
        _connect_open_components(mask, protected)
        braid_dead_ends(mask, rng, protected=protected)
    else:
        # POST：公用池 + 层型专属池（数量同样走层型档位，回声大厅在这里补足）。
        # 后置避开前置的保护区（不叠盖）；连通修复与 braid 也绕开所有保护区，
        # 模板围出的封闭形状与开口位置由收尾的 @ 锚点接管联通。
        stamp_post_vaults(generic_range, form_range)
        _connect_open_components(mask, protected)
        braid_dead_ends(mask, rng, protected=protected)
    # 收尾：每个连通符号（@）都必须与主连通块（外界）联通。
    anchors = [cell for placement in placements for cell in placement.anchor_cells()]
    precious = [cell for cell in (p.loot_cell for p in placements) if cell]
    _ensure_anchor_connections(mask, anchors, protected, precious)
    return mask, placements
