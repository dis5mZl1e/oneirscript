"""形状模板与端口几何（设计方案附录 A、§4.1、§5.2）。

`#` 是实体，`.` 是孔／缺角，`/` 表示换行。以下为归一化初始朝向，
旋转时保持同一实体面积。模板四向连通、不镜像、不裁格。

端口属于**形状模板**：入端放在最上行最左占格的北边，出端放在最下行
最右占格的南边；旋转时格子、边和方向一起旋转。孔洞不自动导通。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

DIRECTIONS = ("N", "E", "S", "W")
DELTAS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
ROTATIONS = (0, 90, 180, 270)

# 形状版本号：入存档。改模板占格或端口必须升版本并写迁移。
SHAPE_VERSION = 1

_CLOCKWISE = {"N": "E", "E": "S", "S": "W", "W": "N"}

# 附录 A：26 个模板。
TEMPLATE_ART: dict[str, str] = {
    "I2": "##",
    "V3": "#/#/#",
    "L3": "#./##",
    "I3": "###",
    "I4": "####",
    "I5": "#####",
    "D4": "##/##",
    "L4": "#./#./##",
    "T4": "###/.#.",
    "S4": ".##/##.",
    "L5": "#../#../###",
    "U5": "#.#/###",
    "P5": "##/##/#.",
    "X5": ".#./###/.#.",
    "R6": "###/###",
    "L6": "#.../#.../####",
    "T6": "####/.#../.#..",
    "S6": ".##/.##/##.",
    "U7": "#.#/#.#/###",
    "P7": "###/###/#..",
    "V7": "#.../#.../#.../####",
    "R8": "####/####",
    "H8": "#.#/###/#../##.",
    "T8": "#####/..#../..#../..#..",
    "O8": "###/#.#/###",
    "R9": "###/###/###",
    "U9": "#...#/#...#/#####",
    "P10": "####/####/##..",
    "R12": "####/####/####",
}


@dataclass(frozen=True)
class ShapeTemplate:
    shape_id: str
    cells: tuple[tuple[int, int], ...]
    # ((格内坐标, 方向), (格内坐标, 方向))：入端在前，出端在后。
    ports: tuple[tuple[tuple[int, int], str], tuple[tuple[int, int], str]]

    @property
    def area(self) -> int:
        return len(self.cells)

    @property
    def bbox(self) -> tuple[int, int]:
        return (max(x for x, _ in self.cells) + 1, max(y for _, y in self.cells) + 1)


def _parse(art: str) -> tuple[tuple[tuple[int, int], ...], tuple[int, int], tuple[int, int]]:
    rows = art.split("/")
    cells = tuple(
        (x, y)
        for y, row in enumerate(rows)
        for x, ch in enumerate(row)
        if ch == "#"
    )
    if not cells:
        raise ValueError(f"形状 {art!r} 没有实体格")
    top_row = min(y for _, y in cells)
    in_cell = (min(x for x, y in cells if y == top_row), top_row)
    bottom_row = max(y for _, y in cells)
    out_cell = (max(x for x, y in cells if y == bottom_row), bottom_row)
    return cells, in_cell, out_cell


def _connected(cells: tuple[tuple[int, int], ...]) -> bool:
    remaining = set(cells)
    stack = [remaining.pop()]
    seen = {stack[0]}
    while stack:
        x, y = stack.pop()
        for dx, dy in DELTAS.values():
            neighbour = (x + dx, y + dy)
            if neighbour in remaining:
                remaining.discard(neighbour)
                seen.add(neighbour)
                stack.append(neighbour)
    return not remaining


def _build() -> dict[str, ShapeTemplate]:
    templates: dict[str, ShapeTemplate] = {}
    for shape_id, art in TEMPLATE_ART.items():
        cells, in_cell, out_cell = _parse(art)
        if not _connected(cells):
            raise ValueError(f"形状模板 {shape_id} 不是四向连通")
        declared = int(shape_id.lstrip("IDLTSPXUVHRO"))
        if declared and declared != len(cells):
            raise ValueError(f"形状模板 {shape_id} 面积 {len(cells)} 与命名 {declared} 不符")
        templates[shape_id] = ShapeTemplate(
            shape_id=shape_id,
            cells=cells,
            ports=((in_cell, "N"), (out_cell, "S")),
        )
    return templates


SHAPE_TEMPLATES: dict[str, ShapeTemplate] = _build()


def rotate_direction(direction: str, rotation: int) -> str:
    for _ in range((rotation // 90) % 4):
        direction = _CLOCKWISE[direction]
    return direction


@lru_cache(maxsize=None)
def shape_geometry(shape_id: str, rotation: int) -> tuple[
    tuple[tuple[int, int], ...],
    tuple[tuple[tuple[int, int], str], tuple[tuple[int, int], str]],
]:
    """返回旋转后的归一化占格与端口（入端、出端）。"""
    if rotation not in ROTATIONS:
        raise ValueError(f"只支持四向旋转，收到 {rotation}")
    template = SHAPE_TEMPLATES[shape_id]
    points = list(template.cells)
    ports = list(template.ports)
    for _ in range((rotation // 90) % 4):
        max_y = max(y for _, y in points)
        points = [(max_y - y, x) for x, y in points]
        ports = [((max_y - py, px), _CLOCKWISE[direction]) for (px, py), direction in ports]
    min_x = min(x for x, _ in points)
    min_y = min(y for _, y in points)
    cells = tuple(sorted((x - min_x, y - min_y) for x, y in points))
    shifted = tuple(
        ((px - min_x, py - min_y), direction) for (px, py), direction in ports
    )
    return cells, shifted  # type: ignore[return-value]


def shape_area(shape_id: str) -> int:
    return len(SHAPE_TEMPLATES[shape_id].cells)


def shape_bbox(shape_id: str, rotation: int = 0) -> tuple[int, int]:
    cells, _ = shape_geometry(shape_id, rotation)
    return (max(x for x, _ in cells) + 1, max(y for _, y in cells) + 1)


def occupied_cells(shape_id: str, rotation: int, x: int, y: int) -> tuple[tuple[int, int], ...]:
    cells, _ = shape_geometry(shape_id, rotation)
    return tuple((x + cx, y + cy) for cx, cy in cells)


def port_anchors(
    shape_id: str, rotation: int, x: int, y: int
) -> tuple[tuple[str, tuple[int, int], str], tuple[str, tuple[int, int], str]]:
    """盘面上的入端／出端：(角色, 所在格, 朝向)。"""
    _, ports = shape_geometry(shape_id, rotation)
    return (
        ("in", (x + ports[0][0][0], y + ports[0][0][1]), ports[0][1]),
        ("out", (x + ports[1][0][0], y + ports[1][0][1]), ports[1][1]),
    )


def rotations_that_fit(shape_id: str, width: int, height: int) -> tuple[int, ...]:
    return tuple(r for r in ROTATIONS if all(
        b <= limit for b, limit in zip(shape_bbox(shape_id, r), (width, height))
    ))
