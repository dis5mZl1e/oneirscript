"""Tiered circuit choices and verified Sokoban boards with a reward workshop."""
import random
from ..data.circuit_templates import component, connect_board, toy_board
from ..materials import wall_def
from .entities import Cell, WorldItem

TOY_VARIANTS = {
    1: ('classic', 'interlock', 'crossbar', 'xor_gate', 'service_priority'),
    2: ('classic', 'phase_lock', 'dual_clock'),
    3: ('classic', 'sequence_lock', 'resettable_code'),
}
TOY_REWARDS = ('screwdriver', 'battery_back', 'night_battery', 'clear_glass')


def _wall(cell, kind):
    definition = wall_def(kind)
    cell.wall_kind, cell.solid = kind, True
    cell.hardness, cell.integrity = definition.hardness, definition.integrity
    cell.height, cell.thickness = definition.height, definition.thickness


def _components(cells, board):
    for node in board["nodes"].values():
        x, y = node["pos"]
        if node.get("wall"):
            _wall(cells[y][x], node["wall"])
        elif node["op"] in {"step", "plate", "cube"}:
            cells[y][x].aggregate_variant = "压力地板"


def generate_toy_board(state, definition, depth):
    choices = state.realm_challenges.setdefault('toy_variants', {})
    variant = choices.setdefault(str(depth), random.Random(state.seed*31 + depth*997).choice(TOY_VARIANTS[depth]))
    if variant == 'classic':
        pattern, board, spawn, npc = toy_board(depth)
    else:
        from ..data.advanced_circuit_vaults import advanced_board
        pattern, board = advanced_board(variant)
        spawn, npc = (2, 17), (9, 17)
        # The main-world board has an external port; realm boards are enclosed.
        pattern[-1] = '#' * len(pattern[-1])
        board['nodes']['door']['latch'] = True
    board.update(id=f"toy_{depth}_{variant}", variant=variant,
                 source_template=f"toy_memories_{depth}", allowed_realms={"toy_memories": [depth]})
    cells = [[Cell() for _ in row] for row in pattern]
    for y, row in enumerate(pattern):
        for x, char in enumerate(row):
            if char == "#":
                _wall(cells[y][x], definition.wall_kind)
    _components(cells, board)
    state._pending_circuit_board = board
    state._toy_npc_pos = npc
    state._toy_targets = []
    return len(pattern[0]), len(pattern), cells, spawn


def generate_sokoban_board(state, definition, depth):
    from ..data.sokoban_levels import SOKOBAN_LEVELS
    key = random.Random(state.seed*31 + depth*997).choice(sorted(SOKOBAN_LEVELS))
    pattern = SOKOBAN_LEVELS[key]
    arena_width, height = len(pattern[0]), len(pattern)
    width = arena_width + 14
    cells = [[Cell() for _ in range(width)] for _ in range(height)]
    targets, spawn = [], (1, 1)
    for y in range(height):
        for x in range(width):
            char = pattern[y][x] if x < arena_width else ("#" if y in (0, height-1) or x in (arena_width+5, width-1) else " ")
            if char == "#":
                _wall(cells[y][x], definition.wall_kind)
            elif char in (".", "*"):
                targets.append((x, y))
                cells[y][x].aggregate_variant = "压力地板"
            if char in ("$", "*"):
                _wall(cells[y][x], "理念立方体")
            elif char == "@":
                spawn = (x, y)
    # A low service passage links the puzzle arena to its circuit/readout panel.
    for x in range(arena_width-1, arena_width+5):
        cells[height-2][x] = Cell()
    nodes = {f"p{i}": component(x, y, "cube", "立方体压板") for i, (x, y) in enumerate(targets)}
    nodes["all"] = component(arena_width+2, 2, "and", "到位合辙", "合辙枢", tuple(nodes))
    nodes["door"] = component(arena_width+5, height-3, "output", "校准之门", "机关门", ("all",), latch=True)
    board = connect_board({"id": f"sokoban_{key}", "nodes": nodes, "completion": "door", "level": key}, width, height)
    board.update(source_template=f"toy_sokoban_{key}", allowed_realms={"toy_memories": [4]}, workshop_version=1)
    _components(cells, board)
    state._pending_circuit_board = board
    state._toy_targets = targets
    state._toy_npc_pos = (arena_width+2, height-2)
    # Existing circuit tools, not another high-tier combat reward. Kept behind
    # the latched door, with enough space to collect each piece separately.
    state._pending_realm_items = workshop_rewards(state, arena_width, height)
    return width, height, cells, spawn


def workshop_rewards(state, arena_width, height):
    rewards = TOY_REWARDS
    spots = ((arena_width+7, 2), (arena_width+11, 2),
             (arena_width+7, height-2), (arena_width+11, height-2))
    # Resetting a solved arena must not duplicate already collected rewards.
    claimed = set(state.realm_challenges.get('toy_rewards', {}).get('claimed', []))
    state.realm_challenges['toy_rewards'] = {
        'version': 1, 'claimed': sorted(claimed),
        'spots': {item: list(spot) for item, spot in zip(rewards, spots)}}
    return [WorldItem(state._make_item(item), *spot)
            for item, spot in zip(rewards, spots) if item not in claimed]


def resume_workshop(state):
    """Append a reward wing to an old fourth-layer save without moving any crate."""
    if state.realm_depth != 4 or state.circuit_boards[0].get('workshop_version') == 1:
        return
    board = state.circuit_boards[0]
    arena_width = board['nodes']['door']['pos'][0]-5
    old_width, new_width = state.width, arena_width+14
    for y, row in enumerate(state.cells):
        row.extend(Cell() for _ in range(max(0, new_width-old_width)))
        if y in (0, state.height-1):
            for x in range(arena_width+6, new_width):
                _wall(row[x], '玩具箱壁')
        else:
            for x in range(arena_width+6, new_width-1):
                row[x] = Cell()
            _wall(row[new_width-1], '玩具箱壁')
    state.width = new_width
    state.world_items.extend(workshop_rewards(state, arena_width, state.height))
    board['workshop_version'] = 1
    state._reset_material_index()
