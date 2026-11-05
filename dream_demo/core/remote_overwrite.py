"""Deterministic, structured remote-overwrite world events."""

from __future__ import annotations

import random
from collections import Counter, deque

from ..data.anomalies import ANOMALY_DEFINITIONS
from ..materials import CONTAINER_KINDS, LIQUID_DEFINITIONS, GAS_DEFINITIONS, WALL_DEFINITIONS

ALGORITHM_IDS = ("compact_patch", "winding_band", "broken_ring", "branching_veins")


def _safe_radius(state) -> int:
    return max(4, min(state.width, state.height) // 3)


def _protected(state, x: int, y: int) -> bool:
    from .item_targeting import protected_cell

    cell = state.cells[y][x]
    return ((x, y) in {(event.x, event.y) for event in state.events}
            or bool(cell.creation) or cell.doorway or cell.wall_kind == "意识边界"
            or cell.wall_kind in CONTAINER_KINDS or protected_cell(state, x, y))


def _connected(cells: set[tuple[int, int]]) -> bool:
    if not cells:
        return False
    seen = {next(iter(cells))}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for point in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                      (x + 1, y + 1), (x - 1, y + 1), (x + 1, y - 1), (x - 1, y - 1)):
            if point in cells and point not in seen:
                seen.add(point)
                queue.append(point)
    return seen == cells


def _shape(algorithm_id: str, rng: random.Random) -> set[tuple[int, int]]:
    if algorithm_id == "compact_patch":
        points = {(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)}
    elif algorithm_id == "winding_band":
        direction = rng.choice((-1, 1))
        points = {(x, (x // 2) * direction) for x in range(-4, 5)}
    elif algorithm_id == "broken_ring":
        points = {(x, y) for x in range(-3, 4) for y in range(-2, 3)
                  if 7 <= x * x + y * y <= 13}
        points.discard((0, -3))
    elif algorithm_id == "branching_veins":
        branch = rng.choice((-1, 1))
        points = {(x, 0) for x in range(-4, 5)}
        points.update((branch * x, x) for x in range(1, 5))
        points.update((-branch * x, -x) for x in range(1, 4))
    else:
        raise ValueError(f"unknown overwrite algorithm: {algorithm_id}")
    return points


def terrain_candidates(state, rng: random.Random, algorithm_id: str) -> set[tuple[int, int]]:
    """Return one safe, connected shape, chosen solely with the event RNG."""
    shape = _shape(algorithm_id, rng)
    radius = _safe_radius(state)
    anchors = [(x, y) for y in range(1, state.height - 1)
               for x in range(1, state.width - 1)
               if abs(x - state.player.x) + abs(y - state.player.y) > radius]
    rng.shuffle(anchors)
    for ax, ay in anchors:
        points = {(ax + dx, ay + dy) for dx, dy in shape}
        candidates = {(x, y) for x, y in points
                      if 0 < x < state.width - 1 and 0 < y < state.height - 1
                      and abs(x - state.player.x) + abs(y - state.player.y) > radius
                      and not _protected(state, x, y)}
        if len(candidates) >= 2 and _connected(candidates):
            return candidates
    return set()


def _areas(state):
    yield state.cells
    for snapshot in state.layer_states.values():
        if snapshot.cells:
            yield snapshot.cells


def _eligible_wall(state, kind: str) -> bool:
    definition = WALL_DEFINITIONS.get(kind)
    return bool(definition and kind != "意识边界" and kind not in CONTAINER_KINDS
                and (not definition.spawn_realms or state.realm_id in definition.spawn_realms))


def choose_donor_wall_pool(state, rng: random.Random) -> tuple[str, ...]:
    """Choose one active or retained layer and return its eligible wall distribution."""
    areas = list(_areas(state))
    area = rng.choice(areas)
    counts = Counter(cell.wall_kind for row in area for cell in row
                     if cell.wall_kind and _eligible_wall(state, cell.wall_kind))
    if counts:
        return tuple(kind for kind in sorted(counts) for _ in range(counts[kind]))
    return tuple(kind for kind in WALL_DEFINITIONS if _eligible_wall(state, kind))


def _spawn_anomalies(state, rng: random.Random) -> None:
    from .content import anomaly_pool_for_depth

    pool = anomaly_pool_for_depth(state.depth)
    if not pool:
        return
    event_cells = {(event.x, event.y) for event in state.events}
    radius = _safe_radius(state)
    legal = [(x, y) for y in range(1, state.height - 1) for x in range(1, state.width - 1)
             if abs(x - state.player.x) + abs(y - state.player.y) > radius
             and (x, y) not in event_cells and not _protected(state, x, y)
             and not state.cells[y][x].solid and not state.cells[y][x].wall_kind
             and state.entity_at(x, y) is None]
    count = min(rng.randint(1, 2), len(legal))
    for _ in range(count):
        options = [(catalog_id, weight) for catalog_id, weight in pool
                   if any(state._anomaly_terrain_ok(ANOMALY_DEFINITIONS[catalog_id],
                                                    state.cells[y][x]) for x, y in legal)]
        if not options:
            return
        catalog_id = rng.choices([entry[0] for entry in options],
                                 weights=[entry[1] for entry in options], k=1)[0]
        anomaly_definition = ANOMALY_DEFINITIONS[catalog_id]
        placements = [pos for pos in legal if state._anomaly_terrain_ok(
            anomaly_definition, state.cells[pos[1]][pos[0]])]
        x, y = placements[rng.randrange(len(placements))]
        legal.remove((x, y))
        state.add_defined_enemy(catalog_id, x, y)


def run_remote_overwrite(state) -> int:
    """Apply one deterministic terrain event without adding persistent state."""
    rng = random.Random(state.seed + state.depth * 1009 + state.overwrite_count * 9176)
    algorithm_id = rng.choice(ALGORITHM_IDS)
    candidates = terrain_candidates(state, rng, algorithm_id)
    wall_pool = choose_donor_wall_pool(state, rng)
    liquids = tuple(k for k, d in LIQUID_DEFINITIONS.items()
                    if not d.spawn_realms or state.realm_id in d.spawn_realms)
    gases = tuple(k for k, d in GAS_DEFINITIONS.items()
                  if not d.spawn_realms or state.realm_id in d.spawn_realms)
    changed = 0
    for x, y in sorted(candidates):
        if rng.random() < 0.7:
            state._overwrite_cell(x, y, wall_kind=rng.choice(wall_pool))
        else:
            liquid = rng.choice(liquids) if liquids and rng.random() < 0.08 else ""
            gas = rng.choice(gases) if gases and rng.random() < 0.08 else ""
            state._overwrite_cell(x, y, wall_kind=None, liquid_kind=liquid, gas_kind=gas)
        changed += 1
    _spawn_anomalies(state, rng)
    return changed
