"""Read each polyomino once at its first occupied cell; punctuation scopes words."""
from __future__ import annotations

from dataclasses import dataclass
from .board import EquipmentBoard, Piece, Placement, Trace, piece_cells


@dataclass(frozen=True)
class Token:
    node: tuple
    value: Placement | Piece | Trace
    cell: tuple[int, int]


def scan(board: EquipmentBoard) -> tuple[Token, ...]:
    tokens = []
    for placement in board.placements:
        cell = min(placement.cells(), key=lambda p: (p[1], p[0]))
        tokens.append(Token(('item', placement.instance_id), placement, cell))
    for piece in board.pieces:
        cell = min(piece_cells(piece), key=lambda p: (p[1], p[0]))
        tokens.append(Token(('piece', piece.piece_id, piece.x, piece.y), piece, cell))
    for trace in board.traces:
        tokens.append(Token(('trace', trace.x, trace.y), trace, (trace.x, trace.y)))
    return tuple(sorted(tokens, key=lambda t: (t.cell[1], t.cell[0], repr(t.node))))


def clauses(board: EquipmentBoard) -> tuple[tuple[Token, ...], ...]:
    result, current = [], []
    for token in scan(board):
        separator = (isinstance(token.value, Trace) and token.value.connector == 'corner'
                     or isinstance(token.value, Piece) and token.value.piece_id == 'period')
        if separator:
            if current:
                result.append(tuple(current))
                current.clear()
        else:
            current.append(token)
    if current:
        result.append(tuple(current))
    return tuple(result)
