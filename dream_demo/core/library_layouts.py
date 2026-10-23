"""Whole-floor orthogonal palace grammar; no vault assembly or connectivity carving.

Produces structure and furniture anchors. Realm content is installed separately,
so encounter/reward changes cannot alter the architectural random stream.
"""
from __future__ import annotations

from dataclasses import dataclass
import random

from .entities import Cell
from .generation import GenerationMixin


@dataclass
class LibraryLayout:
    width: int
    height: int
    cells: list[list[Cell]]
    spawn: tuple[int, int]
    exit: tuple[int, int]
    rooms: list[dict]
    furniture: list[dict]
    protected_cells: set[tuple[int, int]]
    core_anchor: tuple[int, int] | None = None
    version: int = 1


class _Palace:
    def __init__(self, width, height, seed=0, depth=1):
        self.width, self.height = width, height
        self.cells = [[Cell() for _ in range(width)] for _ in range(height)]
        for y, row in enumerate(self.cells):
            for x, cell in enumerate(row):
                outer = x < 3 or y < 3 or x >= width-3 or y >= height-3
                GenerationMixin.configure_wall(cell, "藏书宫外墙" if outer else "书库内墙")
        self.rooms = []
        self.reserved = set()
        self.furniture = []
        self.room_rng = random.Random(seed ^ 0x4C41594F ^ depth*3571)

    def carve(self, x0, y0, x1, y1, *, reserve=False):
        assert 3 <= x0 <= x1 < self.width-3 and 3 <= y0 <= y1 < self.height-3
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                GenerationMixin.clear_wall(self.cells[y][x])
                if reserve:
                    self.reserved.add((x, y))

    def room(self, purpose, rect, furnishing="shelves", vary=True):
        if vary and purpose not in ('vestibule','great_archive','catalogue'):
            from .realm_architecture import vary_room
            rect = vary_room(rect,self.room_rng,self.width,self.height,3)
        self.carve(*rect)
        self.rooms.append({"purpose": purpose, "rect": rect, "furnishing": furnishing})

    def corridor(self, start, end, width=3):
        x, y = start
        tx, ty = end
        half = width//2
        self.carve(max(3, min(x, tx)-half), max(3, y-half),
                   min(self.width-4, max(x, tx)+half), min(self.height-4, y+half), reserve=True)
        self.carve(max(3, tx-half), max(3, min(y, ty)-half),
                   min(self.width-4, tx+half), min(self.height-4, max(y, ty)+half), reserve=True)

    def ring(self, rect):
        x0, y0, x1, y1 = rect
        points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))
        for a, b in zip(points, points[1:]):
            self.corridor(a, b)

    def furnish(self, rng):
        for room_index, room in enumerate(self.rooms):
            mode = room["furnishing"]
            if mode == "none":
                continue
            x0, y0, x1, y1 = room["rect"]
            # Fixed bays with clear ends/cross aisles, not random obstacle noise.
            offset = rng.randrange(2)
            for x in range(x0+2+offset, x1-1, 4):
                for y in range(y0+2, y1-1):
                    if mode == "desks" and (y-y0) % 4 != 2:
                        continue
                    if mode == "shelves" and (y-y0) % 7 in (0, 1):
                        continue
                    if (x, y) in self.reserved or self.cells[y][x].solid:
                        continue
                    GenerationMixin.configure_wall(self.cells[y][x], "木桌子")
                    self.furniture.append({"kind": mode, "x": x, "y": y,
                                           "room": room_index, "purpose": room["purpose"]})


def generate_library_layout(seed: int, depth: int) -> LibraryLayout:
    if depth not in range(1, 6):
        raise ValueError("library depth must be 1..5")
    layout_rng = random.Random(seed ^ 0x4C494252 ^ depth*3571)
    furnish_rng = random.Random(seed ^ 0x5348454C ^ depth*3571)
    width, height = layout_rng.choice(((80, 64), (88, 72), (96, 80)))
    builder = _Palace(width, height, seed, depth)
    cx, cy = width//2, height//2
    spawn, exit_pos = (cx, height-6), (cx, 6)
    core = None

    if depth == 1:
        builder.room("vestibule", (cx-14, height-20, cx+14, height-5), "none")
        builder.room("catalogue", (cx-14, cy-12, cx+14, cy+6), "desks")
        for y in (8, cy+4):
            for x0, x1 in ((5, cx-18), (cx+18, width-6)):
                builder.room("reading_wing", (x0, y, x1, min(y+14, height-23)))
        builder.corridor((8, 7), (8, height-9))
        builder.corridor((width-9, 7), (width-9, height-9))
        builder.corridor((8, height-9), (width-9, height-9))
    elif depth == 2:
        count = layout_rng.choice((3, 5))
        for index in range(count):
            x = 10 + index*(width-21)//(count-1)
            builder.room("long_gallery", (x-5, 7, x+5, height-8))
        for y in (9, cy, height-10):
            builder.corridor((5, y), (width-6, y), width=5)
    elif depth == 3:
        columns = ((9, cx-7), (cx+7, width-10))
        rows = ((10, cy-6), (cy+6, height-11))
        for x0, x1 in columns:
            for y0, y1 in rows:
                builder.room("courtyard", (x0, y0, x1, y1), "none")
                builder.ring((x0-3, y0-3, x1+3, y1+3))
        builder.room("corner_reading", (5, 5, 16, 14), "desks")
        builder.room("corner_reading", (width-17, height-15, width-6, height-6), "desks")
    elif depth == 4:
        builder.room("scriptorium", (5, 8, cx-5, height-21), "desks")
        builder.room("scriptorium", (cx+5, 8, width-6, height-21), "desks")
        for index in range(4):
            x0 = 6 + index*(width-13)//4
            builder.room("private_study", (x0, height-16, x0+11, height-6))
        builder.corridor((7, 7), (7, height-8))
        builder.corridor((width-8, 7), (width-8, height-8))
        builder.corridor((7, height-18), (width-8, height-18), width=5)
    else:
        builder.room("great_archive", (cx-17, cy-15, cx+17, cy+15), "none")
        builder.ring((7, 7, width-8, height-8))
        builder.ring((15, 15, width-16, height-16))
        for x0 in (5, width-18):
            for y0 in (9, height-23):
                builder.room("side_reading_bay", (x0, y0, x0+12, y0+13), "desks")
        core = cx, cy

    # Connect semantic rooms explicitly before furniture. Main and secondary
    # galleries remain passable without destroying shelves or solving puzzles.
    for room in builder.rooms:
        x0, y0, x1, y1 = room["rect"]
        center = (x0+x1)//2, (y0+y1)//2
        builder.corridor(center, (cx, center[1]))
    builder.corridor(spawn, exit_pos, width=5)
    builder.corridor((5, cy), (width-6, cy))
    from .realm_architecture import add_side_rooms, validate_structure
    add_side_rooms(builder,'library_palace',seed,depth)
    validate_structure(builder,spawn,exit_pos)
    from .realm_enrichment import partition_floors
    partition_floors(builder,'library_palace',seed,depth)
    builder.furnish(furnish_rng)
    protected = builder.reserved | {(x, y) for y in range(height) for x in range(width)
                 if x < 3 or y < 3 or x >= width-3 or y >= height-3}
    return LibraryLayout(width, height, builder.cells, spawn, exit_pos,
                         builder.rooms, builder.furniture, protected, core)
