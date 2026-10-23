"""Bounded semantic reassembly; no inventory item is created or discarded."""
from copy import deepcopy

from .board import EquipmentBoard
from .placement import suggest_placement
from .positional import compile_formation
from .roles import is_weapon
from .item_shapes import shape_for
from .shapes import shape_area
from ..data.items import ITEM_DEFINITIONS


def assemble(entries, *, snapshot=None):
    entries = list(dict.fromkeys(entries))
    area = lambda entry: shape_area(shape_for(entry[1]))
    weapon = lambda entry: is_weapon(ITEM_DEFINITIONS.get(entry[1], {}))
    orders = [entries, sorted(entries, key=lambda e: (-weapon(e), -area(e), e[0])),
              sorted(entries, key=lambda e: (-area(e), e[0])),
              sorted(entries, key=lambda e: (weapon(e), -area(e), e[0]))]
    best, best_score = None, -1
    for order in orders:
        board = EquipmentBoard()
        for instance_id, definition_id in order:
            board = suggest_placement(board, instance_id, definition_id)
            if board is None:
                break
        if board is not None:
            formation = compile_formation(board)
            active = {r.source_id for r in formation.rows if r.status == "ready"}
            score = len(active)
            if score > best_score:
                best, best_score = board, score
            if score == len(entries):
                break
    if best is None:
        # Exact physical packing is a fallback, not a claim that all old
        # capabilities survive. Dormant meanings are reported to the player.
        best = EquipmentBoard()
        if not best.pack(entries):
            return None
    best.legacy_snapshot = deepcopy(snapshot or {})
    return best
