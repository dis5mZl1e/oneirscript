"""Independent, permission-filtered observation overlays."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ObservationMark:
    key: str
    color: str
    label: str
    edge: str


MARKS = {
    'telegraph': ObservationMark('telegraph', '#ed8aa7', '技能预警', 'top'),
    'electric': ObservationMark('electric', '#91e7ef', '电场', 'right'),
    'flame': ObservationMark('flame', '#ff9c45', '火焰', 'bottom'),
    'gas': ObservationMark('gas', '#dfbd6b', '危险气体', 'left'),
    'danger': ObservationMark('danger', '#dfbd6b', '危险', 'left'),
}
EDGE_LABELS = {'top': '上边', 'right': '右边', 'bottom': '下边', 'left': '左边'}


def marks_for(cell):
    if cell.status not in ('visible', 'developed'):
        return ()
    keys = ['telegraph'] if cell.telegraph else []
    keys.extend(key for key in cell.hazards if key in MARKS)
    if cell.flame:
        keys.append('flame')
    if cell.danger and not keys:
        keys.append('danger')
    return tuple(MARKS[key] for key in dict.fromkeys(keys))


def draw_marks(draw, cell, rect):
    x, y, w, h = rect
    # Keep the outer ring free for the map cursor, path and optional grid.
    inset = 1 if min(w, h) >= 4 else 0
    x, y, w, h = x+inset, y+inset, w-2*inset, h-2*inset
    for mark in marks_for(cell):
        lines = {
            'top': (x, y, x+w-1, y),
            'right': (x+w-1, y, x+w-1, y+h-1),
            'bottom': (x, y+h-1, x+w-1, y+h-1),
            'left': (x, y, x, y+h-1),
        }
        draw.line(lines[mark.edge], fill=mark.color, width=1)
