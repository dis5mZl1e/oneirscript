"""0 层「梦的起始」：新手引导固定地图。

与深层边界（mapgen.epilogue）同一套「按层分流」的独立生成管线，但比它更极端：
种子完全不参与——地图、站点、实体、物资全部固定，不受修饰符、层型、区域
加权、vault、异象池、NPC 生成的影响。玩家在本层只能遇到两只「玩偶意识体」
（不还手、可重生），按教程卡的指引完成移动、观察、面板、攻击、发射与
自动行走的教学后，按 N 下潜进入梦层 1——起点随即合拢，无法折返。
"""

from __future__ import annotations

# 模板尺寸（教学层一屏可览，小于常规 60×60）。
ORIGIN_WIDTH = 60
ORIGIN_HEIGHT = 36

# 结构墙（外圈与家具块）与普通地面的材质。
_ORIGIN_WALL = "坚硬聚合墙"
_FURNITURE_WALL = "千层叠岩"

# 固定模板。字符图例：
#   # 外圈/家具墙   . 地面   ~ 静水   g 低草
#   S 出生点        M 移动目标        O 观察目标（低草格）
#   A 近战玩偶      F 射击站位        B 射击玩偶
#   W 自动行走目标  D 下潜标记
# 每行必须恰好 ORIGIN_WIDTH 个字符，行数必须恰好 ORIGIN_HEIGHT 行。
LEGACY_ORIGIN_TEMPLATE: tuple[str, ...] = (
    "############################################",
    "#..........................................#",
    "#.gg..................................D....#",
    "#..........................................#",
    "#..........................................#",
    "#..........................................#",
    "#........O.................................#",
    "#..........................................#",
    "#...##.....................................#",
    "#...##.............F.......B...............#",
    "#..........................................#",
    "#..........................................#",
    "#...##.....................................#",
    "#...##.........A........C..................#",
    "#..........................................#",
    "#...................~......................#",
    "#..........................................#",
    "#..........................................#",
    "#.....S......M.............................#",
    "#.....................................W....#",
    "#...................................gg.....#",
    "#...................................gg.....#",
    "#..........................................#",
    "############################################",
)

# Two-cell doorways form a ring; no exercise is the sole route to the exit.
ZONE_CENTRES = {'A': (9, 6), 'B': (29, 6), 'C': (49, 6),
                'D': (9, 18), 'E': (29, 18), 'F': (49, 18),
                'G': (9, 29), 'H': (29, 29), 'I': (49, 29)}


def _course_template():
    grid = [['.' for _ in range(ORIGIN_WIDTH)] for _ in range(ORIGIN_HEIGHT)]
    for y in range(ORIGIN_HEIGHT):
        for x in range(ORIGIN_WIDTH):
            if x in (0, ORIGIN_WIDTH-1, 19, 39) or y in (0, ORIGIN_HEIGHT-1, 11, 23):
                grid[y][x] = '#'
    for x in (19, 39):
        for y in (5, 6, 17, 18, 28, 29): grid[y][x] = '.'
    for y in (11, 23):
        for x in (8, 9, 28, 29, 48, 49): grid[y][x] = '.'
    # A blind side room and a blocked shot with a separate clear shooting lane.
    for y in range(2, 9): grid[y][31] = '#'
    grid[8][31] = '.'
    grid[7][47] = '#'
    for y in (15, 16):
        for x in (7, 8): grid[y][x] = '#'
    marks = {'S': (5, 6), 'M': (13, 6), 'O': (27, 6), 'A': (43, 8),
             'F': (43, 4), 'B': (53, 4), 'W': (15, 18), 'D': (54, 31),
             'C': (49, 29), '~': (12, 18)}
    for mark, (x,y) in marks.items(): grid[y][x] = mark
    grid[5][27] = 'g'
    grid[18][48] = 'g'
    return tuple(''.join(row) for row in grid)


ORIGIN_TEMPLATE = _course_template()

# 站点坐标（由模板字符推导；这里只登记名字 → 字符）。
STATION_CHARS: dict[str, str] = {
    "spawn": "S",
    "move_target": "M",
    "observe_target": "O",
    "doll_melee": "A",
    "fire_from": "F",
    "doll_ranged": "B",
    "autowalk_target": "W",
    "dive_mark": "D",
    "chat_npc": "C",
}

# 教学层里的固定物资与实体参数。
DOLL_INTEGRITY = 12
DOLL_MOVE_TIME = 2.8
DOLL_RESPAWN_TURNS = 8
PROJECTILE_GRANTS = 3  # 开局聚合弹：教学发射至少可试 3 次


def generate_origin_layer() -> tuple[list[list[object]], dict]:
    """生成「梦的起始」。返回 (cells, info)。

    info：spawn 出生点、stations 站点表（含玩偶位）、plants/water 等装饰清单——
    实体与行囊由 GameState._generate_origin_layer 落地（它持有 add_enemy 等能力）。
    """
    from ..core.entities import Cell

    if len(ORIGIN_TEMPLATE) != ORIGIN_HEIGHT:
        raise ValueError(f"梦的起始模板行数应为 {ORIGIN_HEIGHT}，实际 {len(ORIGIN_TEMPLATE)}")
    width = ORIGIN_WIDTH
    stations: dict[str, tuple[int, int]] = {}
    plants: list[tuple[int, int]] = []
    water: tuple[int, int] | None = None
    cells: list[list[Cell]] = []
    for y, row in enumerate(ORIGIN_TEMPLATE):
        if len(row) != width:
            raise ValueError(f"梦的起始模板第 {y} 行宽度应为 {width}，实际 {len(row)}")
        grid_row: list[Cell] = []
        for x, char in enumerate(row):
            cell = Cell()
            if char == "#":
                cell.floor = cell.floor.SOLID_AGGREGATE
                cell.solid = True
                cell.wall_kind = _ORIGIN_WALL
                # 家具块（左缘两个 2×2）用另一种墙色，看起来像摆设而不是边界。
                if (2 <= x <= 5) and y in (8, 9, 12, 13):
                    cell.wall_kind = _FURNITURE_WALL
            elif char == "~":
                cell.liquid, cell.liquid_kind = 60, "水"
                water = (x, y)
            elif char == "g":
                cell.plant = 1
                plants.append((x, y))
            elif char in STATION_CHARS.values():
                for name, mark in STATION_CHARS.items():
                    if char == mark:
                        stations[name] = (x, y)
                        break
                if char == "O":
                    # 观察目标本身是一株低草：? 对准它就能读到一段环境文本。
                    cell.plant = 1
                    plants.append((x, y))
            grid_row.append(cell)
        cells.append(grid_row)

    info = {
        "width": width,
        "height": ORIGIN_HEIGHT,
        "spawn": stations["spawn"],
        "stations": stations,
        "plants": plants,
        "water": water,
        "dolls": (stations["doll_melee"], stations["doll_ranged"]),
    }
    return cells, info
