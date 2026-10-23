"""Whole-floor clinical architecture with aligned bays, service routes and tanks.

Structure, furnishings and content use separate streams. Closed tank interiors
are the only intentionally disconnected floor cells; no connectivity digging.
"""
from dataclasses import dataclass
import random

from .entities import Cell
from .generation import GenerationMixin as G
from .realm_architecture import ventilation_clearance


SIZES = ((65, 41), (73, 45), (73, 49), (81, 49), (65, 49))


@dataclass
class HospitalLayout:
    width: int
    height: int
    cells: list
    spawn: tuple
    exit: tuple
    rooms: list
    furniture: list
    lights: list
    tanks: list
    protected_cells: set
    core_anchor: tuple | None = None
    version: int = 1


class _Clinic:
    def __init__(self, width, height, seed=0, depth=1):
        self.width, self.height = width, height
        self.cells = [[Cell(aggregate_variant="洁白釉板") for _ in range(width)] for _ in range(height)]
        self.rooms, self.furniture, self.tanks = [], [], []
        self.reserved = set()
        self.room_rng = random.Random(seed ^ 0x484F5350 ^ depth*3571)
        for y, row in enumerate(self.cells):
            for x, cell in enumerate(row):
                outer = x < 2 or y < 2 or x >= width-2 or y >= height-2
                G.configure_wall(cell, "意识边界" if outer else "白瓷隔断")

    def carve(self, rect, reserve=False):
        x0, y0, x1, y1 = rect
        assert 2 <= x0 <= x1 < self.width-2 and 2 <= y0 <= y1 < self.height-2
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                G.clear_wall(self.cells[y][x])
                if reserve:
                    self.reserved.add((x, y))

    def room(self, purpose, rect, furnishing=True, vary=True):
        if vary and purpose not in ('reception','triage','core_nave','front_hall'):
            from .realm_architecture import vary_room
            rect = vary_room(rect,self.room_rng,self.width,self.height,2)
        self.carve(rect)
        x0, y0, x1, y1 = rect
        center = ((x0+x1)//2, (y0+y1)//2)
        self.rooms.append(dict(purpose=purpose, rect=rect, entrance=center, furnishing=furnishing))

    def corridor(self, a, b, width=3):
        x, y = a
        tx, ty = b
        half = width//2
        self.carve((max(2, min(x, tx)-half), max(2, y-half),
                    min(self.width-3, max(x, tx)+half), min(self.height-3, y+half)), True)
        self.carve((max(2, tx-half), max(2, min(y, ty)-half),
                    min(self.width-3, tx+half), min(self.height-3, max(y, ty)+half)), True)

    def ring(self, rect):
        x0, y0, x1, y1 = rect
        points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))
        for a, b in zip(points, points[1:]):
            self.corridor(a, b)

    def furnish(self, rng):
        for index, room in enumerate(self.rooms):
            if not room["furnishing"]:
                continue
            x0, y0, x1, y1 = room["rect"]
            offset = rng.randrange(2)
            for y in range(y0+2, y1-1, 4):
                for x in range(x0+2+offset, x1-1, 4):
                    if (x, y) in self.reserved or self.cells[y][x].solid:
                        continue
                    G.configure_wall(self.cells[y][x], "白瓷工作台")
                    self.furniture.append(dict(kind="bench", x=x, y=y, room=index))

    def tank(self, x, y, kind, uid):
        interior, walls = [], []
        for yy in range(y-2, y+3):
            for xx in range(x-2, x+3):
                cell = self.cells[yy][xx]
                if abs(xx-x) == 2 or abs(yy-y) == 2:
                    G.configure_wall(cell, "净玻璃隔屏" if xx == x+2 and yy == y else "罐体密封壁")
                    walls.append((xx, yy))
                else:
                    G.clear_wall(cell)
                    cell.aggregate_variant = "密封板"
                    cell.gas_kind, cell.gas = kind, 18
                    interior.append((xx, yy))
        occupied = set(interior+walls)
        G.clear_wall(self.cells[y][x+3])
        occupied.add((x+3, y))
        self.furniture = [f for f in self.furniture if (f["x"], f["y"]) not in occupied]
        self.tanks.append(dict(uid=uid, cells=interior, walls=walls, gas=kind,
                               port=(x+3, y), inventory_version=1))


def generate_hospital_layout(seed, depth):
    if depth not in range(1, 6):
        raise ValueError("hospital depth must be 1..5")
    w, h = SIZES[depth-1]
    cx, cy = w//2, h//2
    b = _Clinic(w, h, seed, depth)
    spawn, exit_pos = (cx, h-5), (cx, 6)
    if depth == 1:
        b.room("reception", (cx-12, h-15, cx+12, h-4), False)
        b.room("triage", (cx-9, 7, cx+9, cy+5))
        for x0, x1 in ((5, cx-14), (cx+14, w-6)):
            for y0, y1 in ((7, 17), (23, h-7)):
                b.room("waiting_bay", (x0, y0, x1, y1))
        b.corridor((6, 6), (6, h-8))
        b.corridor((w-7, 6), (w-7, h-8))
        b.corridor((6, h-8), (w-7, h-8))
    elif depth == 2:
        for x, purpose in ((13, "wash_band"), (cx, "mixing_band"), (w-14, "gel_band")):
            b.room(purpose, (x-7, 7, x+7, h-8))
        for y in (10, cy, h-11):
            b.corridor((5, y), (w-6, y), 5)
    elif depth == 3:
        for y in (7, 20, 33):
            b.room("gas_wing", (6, y, w-7, y+8))
        b.corridor((w-9, 8), (w-9, h-9))
    elif depth == 4:
        b.room("light_court", (cx-28, 17, cx-10, 31), False)
        b.room("light_court", (cx+10, 17, cx+28, 31), False)
        for x in (6, 24, 44, 62):
            for y in (6, h-13):
                b.room("rest_bay", (x, y, x+12, y+6))
        b.ring((5, 5, w-6, h-6))
        b.ring((cx-30, 15, cx+30, 33))
    else:
        b.room("core_nave", (cx-12, cy-10, cx+12, cy+10), False)
        b.room("front_hall", (cx-12, h-15, cx+12, h-4), False)
        b.carve((cx-5, 7, cx+5, h-8), True)
        b.carve((6, cy-5, w-7, cy+5), True)
        for x0, x1 in ((6, 17), (w-18, w-7)):
            for y0, y1 in ((7, 15), (h-17, h-9)):
                b.room("mixing_alcove", (x0, y0, x1, y1))
        b.ring((4, 4, w-5, h-5))

    # Explicit semantic-room links and a five-wide protected service spine.
    for room in b.rooms:
        x, y = room["entrance"]
        b.corridor((x, y), (cx, y))
    b.corridor(spawn, exit_pos, 5)
    b.corridor((5, cy), (w-6, cy))
    from .realm_architecture import add_side_rooms, validate_structure
    add_side_rooms(b,'white_sanatorium',seed,depth)
    validate_structure(b,spawn,exit_pos)
    from .realm_enrichment import partition_floors
    partition_floors(b,'white_sanatorium',seed,depth)
    b.furnish(random.Random(seed ^ 0x434C494E ^ depth*3571))
    if depth == 3:
        for index, (y, kind) in enumerate(((11, "无菌载气"), (24, "醒素薄气"), (37, "胞尘"))):
            b.tank(11, y, kind, f"{seed}:hospital:3:tank:{index}")

    # Finite material trays stay in work bays, away from the protected dry spine.
    materials_by_room = {
        'reception': ('注射用梦水',), 'triage': ('洗兆液', '银盐悬液'),
        'waiting_bay': ('淋巴液',), 'wash_band': ('洗兆液', '晨醒溶液', '注射用梦水'),
        'mixing_band': ('梦醚', '银盐悬液'), 'gel_band': ('凝胶基液', '纤维蛋白胶'),
        'gas_wing': ('洗兆液',), 'rest_bay': ('脑脊液',),
        'mixing_alcove': ('淋巴液', '脑脊液'),
    }
    for room in b.rooms:
        x0, y0, x1, y1 = room['rect']
        available = [(x, y) for y in range(y0+2, y1-1) for x in range(x0+2, x1-1)
                     if not b.cells[y][x].solid and (x, y) not in b.reserved
                     and abs(x-cx) > 3]
        for kind in materials_by_room.get(room['purpose'], ()):
            # 每种材料铺两处浅盘（原 1 格太少，瓶中液体几乎无法采集）。
            for _ in range(2):
                if not available:
                    break
                x, y = available.pop(0)
                b.cells[y][x].liquid_kind, b.cells[y][x].liquid = kind, 12

    # Fixed ceiling lights: aligned with the service grid, not scattered plants.
    tank_cells = {p for tank in b.tanks for p in tank["cells"]}
    lights = []
    for y in range(6, h-3, 8):
        for x in range(cx % 8, w-3, 8):
            if x < 3 or b.cells[y][x].solid or (x, y) in tank_cells:
                continue
            b.cells[y][x].light_radius = 3
            lights.append((x, y))
    for y in range(6, h-6, 8):
        for x in (cx-3, cx+3):
            if b.cells[y][x].wall_kind == "白瓷隔断":
                G.configure_wall(b.cells[y][x], "日光壁")

    # Sparse ventilation in structural edges, aimed along an actual open ray.
    rng = random.Random(seed ^ 0x414952 ^ depth*3571)
    edges = [(x, y) for y in range(3, h-3) for x in range(3, w-3)
             if b.cells[y][x].wall_kind == "白瓷隔断"
             and any(not b.cells[y+dy][x+dx].solid for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)))]
    rng.shuffle(edges)
    for x, y in edges[:depth]:
        G.configure_wall(b.cells[y][x], "排气口")
    count = 0
    for x, y in edges[depth:]:
        for direction, dx, dy in (("北", 0, -1), ("东", 1, 0), ("南", 0, 1), ("西", -1, 0)):
            if all(2 <= x+i*dx < w-2 and 2 <= y+i*dy < h-2
                   and not b.cells[y+i*dy][x+i*dx].solid for i in range(1, 7)):
                G.configure_wall(b.cells[y][x], "换气扇·"+direction)
                count += 1
                break
        if count >= 2:
            break
    vent_clearance=ventilation_clearance(b.cells)
    for x, y in [p for p in edges if b.cells[p[1]][p[0]].wall_kind == '白瓷隔断'
                 and p not in vent_clearance][:4]:
        G.configure_wall(b.cells[y][x], '净相壁')
    # 封口药箱与稀薄散气由 realm_enrichment.complete_content 统一配给
    # （box_count 6-10 + 气体 2% 目标，含 generation_report 审计），此处不再重复铺设。
    protected = b.reserved | {(x, y) for y in range(h) for x in range(w)
                              if x < 2 or y < 2 or x >= w-2 or y >= h-2}
    return HospitalLayout(w, h, b.cells, spawn, exit_pos, b.rooms, b.furniture,
                          lights, b.tanks, protected, (cx, cy) if depth == 5 else None)
