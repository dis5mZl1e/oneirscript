"""Typed reaction clauses, ordered by reading. No directional port traversal."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Iterable
from .board import PIECE_SPECS, EquipmentBoard, Piece, Placement
from .reading import clauses

MAX_NODES = 48
MAX_EQUIPMENT = 24
MAX_PENDING = 4
NodeKey = tuple
SemanticSource = Callable[[Placement], frozenset]
DEFAULT_EVENTS = {'buffer': 'hurt', 'surge': 'touch', 'spark': 'hit',
                  'ember': 'hit', 'voice': 'touch'}
EVENT_LABELS = {'hit': '命中', 'hurt': '受击', 'touch': '接触', 'conceive': '构想'}


@dataclass(frozen=True)
class ReactPath:
    endpoint: str
    nodes: tuple[NodeKey, ...]
    semantics: frozenset
    gated: bool
    terminal: tuple[int, int] | None
    terminal_piece: str | None
    equipment_count: int
    blank_gated: bool = False
    deferred: tuple | None = None
    continuation: tuple[NodeKey, ...] = ()
    output_conditions: tuple[tuple[NodeKey, bool, bool], ...] = ()


def compile_react_paths(board: EquipmentBoard, semantics_of: SemanticSource) -> list[ReactPath]:
    result = []
    for clause in clauses(board):
        words = [t.value for t in clause if isinstance(t.value, Placement)]
        semantics = frozenset().union(*(semantics_of(p) for p in words))
        nodes = tuple(t.node for t in clause)
        gated, blank, parallel = False, False, False
        echo, endpoint = None, None
        deferred = {}
        used_events = set()
        for token in clause:
            if not isinstance(token.value, Piece):
                continue
            piece = token.value
            spec = PIECE_SPECS[piece.piece_id]
            if spec.endpoint:
                endpoint = spec.endpoint
            elif piece.piece_id == 'wet_gate':
                gated = True
            elif piece.piece_id == 'blank_gate':
                blank = True
            elif piece.piece_id == 'echo_cell':
                echo = token
            elif piece.piece_id == 'splitter':
                parallel = True
            if not spec.feedback:
                continue
            event = endpoint or DEFAULT_EVENTS[piece.piece_id]
            if event in used_events and not parallel:
                continue
            used_events.add(event)
            path = ReactPath(event, nodes, semantics, gated, (piece.x, piece.y),
                             piece.piece_id, len(words), blank)
            if echo:
                deferred.setdefault((echo.node, echo.cell, event), []).append((token.node, gated, blank))
            else:
                result.append(path)
        for (node, cell, event), outputs in deferred.items():
            result.append(ReactPath(event, nodes, semantics, all(o[1] for o in outputs), tuple(node[2:]),
                'echo_cell', len(words), all(o[2] for o in outputs), (node, cell, 'read'),
                tuple(o[0] for o in outputs), tuple(outputs)))
    return result


def paths_from(board: EquipmentBoard, endpoint_id: str, semantics_of: SemanticSource) -> list[ReactPath]:
    return [p for p in compile_react_paths(board, semantics_of) if p.endpoint == endpoint_id]


def resume_paths(board: EquipmentBoard, path: ReactPath, semantics_of: SemanticSource) -> list[ReactPath]:
    """Keep captured meanings; require the same clause and original outputs."""
    if not path.deferred:
        return []
    current = next((p for p in compile_react_paths(board, semantics_of)
                    if p.deferred and p.endpoint == path.endpoint
                    and p.terminal == path.terminal and p.nodes == path.nodes
                    and p.gated == path.gated and p.blank_gated == path.blank_gated), None)
    if current is None:
        return []
    outputs = set(path.continuation or current.continuation)
    results = []
    for node in current.continuation:
        if node not in outputs:
            continue
        piece_id, x, y = node[1:]
        conditions = next((value for value in path.output_conditions if value[0] == node),
                          (node, path.gated, path.blank_gated))
        results.append(replace(path, terminal=(x, y), terminal_piece=piece_id,
                               gated=conditions[1], blank_gated=conditions[2],
                               deferred=None, continuation=(), output_conditions=()))
    return results


def endpoint_label(endpoint_id: str) -> str:
    return EVENT_LABELS[endpoint_id]


def trace_at(board: EquipmentBoard, x: int, y: int):
    return next((t for t in board.traces if (t.x, t.y) == (x, y)), None)


def piece_at(board: EquipmentBoard, x: int, y: int):
    from .board import piece_cells
    return next((p for p in board.pieces if (x, y) in piece_cells(p)), None)


def explain(paths: Iterable[ReactPath]) -> list[str]:
    from ..i18n import tr
    return [tr('当{event}时，尝试{effect}。', event=tr(endpoint_label(p.endpoint)),
               effect=tr(PIECE_SPECS[p.terminal_piece].label)) for p in paths]
