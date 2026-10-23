"""Bounded automatic placement prefers useful sentences and keeps old pieces."""
from __future__ import annotations

from .board import EquipmentBoard, Placement
from .item_shapes import shape_for
from .positional import compile_formation
from .roles import resolve_role
from .shapes import ROTATIONS


def _ready_keys(formation):
    return {(row.source_id, row.opcode) for row in formation.rows if row.status == "ready"}


def suggest_placement(board: EquipmentBoard, instance_id: str, definition_id: str):
    """Return a shadow board. Never move or change any existing physical item."""
    shape_id = shape_for(definition_id)
    owners = board.cell_owners()
    from .syntax import board_roles
    roles = board_roles(board)
    old_keys = _ready_keys(compile_formation(board, column_roles=roles))
    native = resolve_role(definition_id, "verb")
    best, best_score = None, None
    for rotation in ROTATIONS:
        for y in range(board.height):
            for x in range(board.width):
                if not board.can_place_item(definition_id, shape_id, x, y, rotation, owners):
                    continue
                draft = board.clone()
                draft.focus_instance_id = None
                placed = Placement(instance_id, definition_id, shape_id, x, y, rotation)
                draft.place_item(placed)
                variants = [draft]
                for candidate in variants:
                    formation = compile_formation(candidate, column_roles=roles)
                    if not formation.valid:
                        continue
                    keys = _ready_keys(formation)
                    ready = [row for row in formation.rows if row.status == "ready"]
                    natural = bool(native and any(
                        row.source_id == instance_id and row.opcode == native.opcode
                        for row in ready))
                    extra = len(candidate.pieces)-len(board.pieces)
                    # Preserve prior successful meanings before improving this
                    # item. Prefer no extra words, then a compact reading order.
                    score = (len(old_keys & keys), natural, -extra,
                             sum(instance_id in row.instance_ids for row in ready), -y, -x, -rotation)
                    if best_score is None or score > best_score:
                        best, best_score = candidate, score
    return best
