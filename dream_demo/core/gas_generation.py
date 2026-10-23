"""Natural gas placement: one mass budget, connected clouds, local flow geometry."""

from __future__ import annotations

import math
import random

from ..materials import CONTAINER_KINDS, wall_def
from .entities import Cell
from .materials_sim import MaterialSimMixin

Position = tuple[int, int]


def _neighbors(pos: Position):
    x, y = pos
    return ((x+1,y), (x-1,y), (x,y+1), (x,y-1))


def _flow_cells(cells: list[list[Cell]]) -> set[Position]:
    return {(x,y) for y,row in enumerate(cells) for x,c in enumerate(row)
            if MaterialSimMixin._gas_flow_passable(c)}


def _local_space(center: Position, flow: set[Position]) -> set[Position]:
    seen = {center}
    queue = [center]
    cx, cy = center
    for pos in queue:
        for x,y in _neighbors(pos):
            if ((x,y) in flow and (x,y) not in seen
                    and abs(x-cx) <= 3 and abs(y-cy) <= 3):
                seen.add((x,y))
                queue.append((x,y))
    return seen


def gas_center_weights(cells: list[list[Cell]], eligible: set[Position]) -> dict[Position, float]:
    flow = _flow_cells(cells)
    ventilated = set()
    for y,row in enumerate(cells):
        for x,cell in enumerate(row):
            definition = wall_def(cell.wall_kind)
            if not cell.solid or not definition.gas_push_direction:
                continue
            dx,dy = definition.gas_push_direction
            for distance in range(1, definition.gas_push_range+2):
                target = (x+dx*distance,y+dy*distance)
                if target not in flow:
                    break
                ventilated.add(target)
    weights = {}
    for pos in sorted(eligible, key=lambda p: (p[1],p[0])):
        k = sum(n in flow for n in _neighbors(pos))
        if not k or pos not in flow:
            continue
        count = len(_local_space(pos, flow))
        weight = (0,4,2.8,1.6,1)[k] * (1.5 if count <= 12 else 1.2 if count <= 24 else 1)
        weights[pos] = min(6,weight) * (.5 if pos in ventilated else 1)
    return weights


def _reachable(cells: list[list[Cell]], spawn: Position) -> set[Position]:
    height,width = len(cells),len(cells[0])
    seen = {spawn}
    queue = [spawn]
    for pos in queue:
        for x,y in _neighbors(pos):
            if not (0 <= x < width and 0 <= y < height) or (x,y) in seen:
                continue
            cell = cells[y][x]
            # Ordinary doors can be opened; authored locked gates cannot.
            if not cell.solid or cell.wall_kind == '门':
                seen.add((x,y))
                queue.append((x,y))
    return seen


def place_natural_gas(
    cells: list[list[Cell]], rng: random.Random, pool: list[tuple[str,float]], *,
    spawn: Position, protected=(), rate: float = .009,
) -> dict:
    """Place new clouds only; existing authored gas and non-gas materials survive.

    ``rate`` is 100-point-equivalent mass per eligible cell, not source probability.
    A sub-60 final remainder may remain unspent rather than create ineffective haze.
    """
    blocked = set(protected)
    sx,sy = spawn
    blocked.update((sx+dx,sy+dy) for dy in range(-1,2) for dx in range(-1,2))
    for y,row in enumerate(cells):
        for x,cell in enumerate(row):
            if cell.wall_kind in CONTAINER_KINDS:
                blocked.update((x+dx,y+dy) for dy in range(-2,3) for dx in range(-2,3))
    reachable = _reachable(cells, spawn)
    eligible = {pos for pos in reachable if pos not in blocked
                and not cells[pos[1]][pos[0]].solid and not cells[pos[1]][pos[0]].wall_kind
                and not cells[pos[1]][pos[0]].liquid and not cells[pos[1]][pos[0]].gas}
    weights = gas_center_weights(cells, eligible)
    exact = len(weights) * rate * 100
    budget = math.floor(exact) + (rng.random() < exact % 1)
    result = dict(eligible=len(weights), budget=budget, spent=0, cluster_mass=0, clusters=[])
    if not pool or budget < 60:
        return result
    kinds,kind_weights = zip(*pool)
    used = set()
    centers = []
    small_spaces = set()
    flow = _flow_cells(cells)
    cluster_left = int(budget*.75)
    remaining = budget
    candidates = dict(weights)
    while cluster_left >= 100 and candidates:
        center = rng.choices(list(candidates), weights=list(candidates.values()), k=1)[0]
        candidates.pop(center)
        if (center in used or center in small_spaces
                or any(max(abs(center[0]-x),abs(center[1]-y)) < 4 for x,y in centers)):
            continue
        cloud = [center]
        visited = {center}
        # Small budgets retain a compact core instead of forfeiting all clustering.
        compact = cluster_left < 200
        size = (2 if cluster_left < 140 else 3) if compact else rng.randint(3,5)
        for pos in cloud:
            neighbors = list(_neighbors(pos))
            rng.shuffle(neighbors)
            for n in neighbors:
                if n in weights and n not in visited and n not in used:
                    visited.add(n)
                    cloud.append(n)
                    if len(cloud) == size:
                        break
            if len(cloud) == size:
                break
        if len(cloud) < (2 if compact else 3):
            continue
        upper = min(320,100+(len(cloud)-1)*90,cluster_left)
        if 0 < cluster_left-upper < 100 and upper >= 200:
            upper = max(200,cluster_left-100)
        mass = upper
        core = min(100,max(70,math.ceil(mass*.34),math.ceil(mass/len(cloud))))
        # Largest first: a stable high-concentration core with weaker edges.
        tail = mass-core
        amounts = [core] + [tail//(len(cloud)-1) + (i < tail%(len(cloud)-1))
                            for i in range(len(cloud)-1)]
        kind = rng.choices(kinds,weights=kind_weights,k=1)[0]
        for (x,y),amount in zip(cloud,amounts):
            cells[y][x].gas, cells[y][x].gas_kind = amount,kind
        used.update(cloud)
        centers.append(center)
        space = _local_space(center,flow)
        if len(space) <= 24:
            small_spaces.update(space)
        result['clusters'].append(cloud)
        result['cluster_mass'] += mass
        cluster_left -= mass
        remaining -= mass
    scattered = [p for p in weights if p not in used]
    rng.shuffle(scattered)
    for x,y in scattered:
        if remaining < 60:
            break
        amount = rng.randint(60,min(100,remaining))
        cells[y][x].gas = amount
        cells[y][x].gas_kind = rng.choices(kinds,weights=kind_weights,k=1)[0]
        remaining -= amount
    result['spent'] = budget-remaining
    return result
