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


def adjacent_choices(left, right, width, *, split_from=44):
    """Rows contain (Text, semantic entry, key); empty column space is inert."""
    from rich.cells import cell_len
    split = width >= split_from
    left_width = (width - 3) // 2 if split else width
    right_width = width - left_width - 3 if split else width

    # 定义左右区域的底色（使用纸感分区的同族色）
    from .paper_zones import ZONE_CAST_LIST, ZONE_CAST_PREVIEW
    LEFT_BG = ZONE_CAST_LIST      # 字词区：灰青纸
    RIGHT_BG = ZONE_CAST_PREVIEW  # 条件区：灰紫纸
    DIVIDER_STYLE = '#5f5f5f'     # 分隔线颜色

    def wrap(entries, available, background):
        from .panels import paper_pad
        from .paper_zones import ZONE_STRIP
        out = []
        for text, entry, key in entries:
            heading = entry == -1 and text.plain.startswith(('──', '——', '━━'))
            for line in folded_lines(text, available):
                if heading:
                    line.stylize('bold underline')
                    line = paper_pad(line, ZONE_STRIP, available)
                else:
                    # 为非标题行添加背景色
                    line = paper_pad(line, background, available)
                out.append((line, entry, key))
        return out

    left = wrap(left, left_width, LEFT_BG)
    right = wrap(right, right_width, RIGHT_BG)
    lines, rows, hits = [], [], []

    if not split:
        for text, entry, key in left + right:
            if key:
                hits.append(ChoiceHit(len(lines), 0, cell_len(text.plain), key))
            lines.append(text)
            rows.append(entry)
        return lines, rows, hits

    # 分栏模式：左右两块用不同底色，中间用竖线分隔
    for row in range(max(len(left), len(right))):
        line = Text()
        entry = -1

        # 左侧字词区
        if row < len(left):
            text, entry, key = left[row]
            line.append(text)
            if key:
                hits.append(ChoiceHit(row, 0, cell_len(text.plain), key))
        else:
            # 左侧空行也需要背景色
            from .panels import paper_pad
            line.append(paper_pad(Text(''), LEFT_BG, left_width))

        # 确保左侧宽度
        line.pad_right(left_width - cell_len(line.plain))

        # 添加分隔线（带颜色）
        line.append(' │ ', style=f'bold {DIVIDER_STYLE}')

        # 右侧条件区
        if row < len(right):
            text, right_entry, key = right[row]
            line.append(text)
            if entry < 0:
                entry = right_entry
            if key:
                hits.append(ChoiceHit(row, left_width + 3, left_width + 3 + cell_len(text.plain), key))
        else:
            # 右侧空行也需要背景色
            from .panels import paper_pad
            line.append(paper_pad(Text(''), RIGHT_BG, right_width))

        lines.append(line)
        rows.append(entry)

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
