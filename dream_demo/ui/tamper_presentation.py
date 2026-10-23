"""Shared semantic colors and fixed sentence / scrolling choices geometry."""
from __future__ import annotations
from dataclasses import dataclass, field

from rich.console import Console
from rich.text import Text

from ..i18n import tr

# 第十九节 §10.1：篡改编辑器的六个语义色由面板字段注册表给出，别处同语义复用同色。
from .panel_fields import FIELD_COLORS as _PANEL_FIELDS

WORD = _PANEL_FIELDS['word']
DEGREE = _PANEL_FIELDS['degree']
CONDITION = _PANEL_FIELDS['condition']
EFFECT = _PANEL_FIELDS['effect']
COST = _PANEL_FIELDS['cost']
RISK = _PANEL_FIELDS['risk']
# 旧值 #a0a1b2 是表外的第二套「暗灰」；§2 把次要说明统一为注册表的 muted。
MUTED = _PANEL_FIELDS['muted']


@dataclass(kw_only=True)
class TamperViewState:
    map_preview: bool = False
    preview_cursor: tuple[int, int] | None = None
    ui_context: tuple = ()
    return_context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ChoiceHit:
    row: int
    start_col: int
    end_col: int
    key: str

    def contains(self, row, col):
        return self.row == row and self.start_col <= col < self.end_col


def adjacent_choices(left, right, width):
    """Rows contain (Text, semantic entry, key); empty column space is inert."""
    from rich.cells import cell_len
    split = width >= 44
    left_width = (width - 3) // 2 if split else width
    right_width = width - left_width - 3 if split else width
    def wrap(entries, available):
        return [(line, entry, key) for text, entry, key in entries
                for line in folded_lines(text, available)]
    left = wrap(left, left_width); right = wrap(right, right_width)
    lines, rows, hits = [], [], []
    if not split:
        for text, entry, key in left + right:
            if key:
                hits.append(ChoiceHit(len(lines), 0, cell_len(text.plain), key))
            lines.append(text); rows.append(entry)
        return lines, rows, hits
    for row in range(max(len(left), len(right))):
        line = Text(); entry = -1
        if row < len(left):
            text, entry, key = left[row]
            line.append(text)
            if key:
                hits.append(ChoiceHit(row, 0, cell_len(text.plain), key))
        line.pad_right(left_width - cell_len(line.plain))
        line.append(' │ ', style=MUTED)
        if row < len(right):
            text, right_entry, key = right[row]
            line.append(text)
            if entry < 0:
                entry = right_entry
            if key:
                hits.append(ChoiceHit(row, left_width + 3, left_width + 3 + cell_len(text.plain), key))
        lines.append(line); rows.append(entry)
    return lines, rows, hits


def folded_lines(text: str | Text, width: int, style: str = '') -> list[Text]:
    """Wrap with Rich's cell widths while retaining all semantic spans."""
    text = text if isinstance(text, Text) else Text(text, style=style)
    lines = []
    for line in text.split('\n'):
        lines.extend(line.wrap(Console(), max(1, width), overflow='fold'))
    return lines


def details_label(expanded: bool) -> str:
    return tr('▾ 详情（\\ 收起）') if expanded else tr('▸ 详情（\\ 展开）')


def section_window(tags, *, top, bottom, height: int, scroll: int, follow=None, actions=()):
    """Return visible source indices, preserving geometry for mouse hit maps.

    In a very short window, excess fixed prose becomes scrollable rather than
    disappearing. At least one row is reserved for the editable choice list.
    """
    height = max(1, height)
    headers = [i for i, tag in enumerate(tags) if tag in top]
    footers = [i for i, tag in enumerate(tags) if tag in bottom]
    # An extreme resize still has to expose controls. Any excess quote or
    # sentence lines stay in the body and can be reached with PageUp/PageDown.
    footer_count = min(len(footers), max(0, height - 2))
    priorities = [i for i in footers if tags[i] in actions]
    pinned_footer = sorted((priorities + [i for i in footers if i not in priorities])[:footer_count])
    header_count = min(len(headers), max(0, height - footer_count - 1))
    pinned_header = headers[:header_count]
    pinned = set(pinned_footer + pinned_header)
    body = [i for i in range(len(tags)) if i not in pinned]
    body_height = height - len(pinned)
    start = max(0, min(scroll, max(0, len(body) - body_height)))
    if follow is not None:
        positions = [j for j, i in enumerate(body) if tags[i] == follow]
        if positions:
            target = positions[0]
            if target < start:
                start = target
            elif target >= start + body_height:
                start = target - body_height + 1
    selected_body = body[start:start + body_height]
    return (pinned_header + selected_body + [None] * (body_height-len(selected_body)) + pinned_footer,
            start, body_height, len(body))
