"""行囊格子的纯 Rich Text 排版。

这里不碰 Textual 控件：调用方仍是 ``#panel`` 里的整块 Rich Text。本模块只负责
「槽位 → 5 列方格」的几何、格子边框、图标/数量/装备标记，以及供鼠标命中的
「可视行 → 每格 x 区间」映射。

正方形口径（2026-10-31）：当前 WezTerm 阅读字体的半角字宽 = 0.5 em，
cell_width = 1.18，line_height = 1.0，所以一格宽（列）× 0.59 ≈ 方格高（行）。
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict

from rich.cells import cell_len
from rich.style import Style
from rich.text import Text

from ..symbols import drop_glyph
from .panel_fields import FIELD_COLORS as FC, panel_color
from .paper_zones import ZONE_BODY
from .styles import item_name_color

GRID_COLUMNS = 5
# 半角字宽 0.5 em × cell_width 1.18 ÷ line_height 1.0。
CELL_ASPECT = 0.59
MIN_CELL_W = 6
MAX_CELL_W = 20

# Dark category tints retain the surrounding paper palette and keep icons legible.
from ..data.inventory_styles import CATEGORY_BACKGROUNDS, RARITY_BORDERS


def _slot_background(item) -> str:
    return CATEGORY_BACKGROUNDS.get(getattr(item, 'category', ''), ZONE_BODY)


def _item_frame(item) -> Style:
    return Style(color=RARITY_BORDERS.get(getattr(item, 'rarity', ''), '#b6a18a'),
                 bgcolor=_slot_background(item), bold=True, italic=False,
                 meta={'font_role': 'serif'})

_SELECTED_TOP = Style(color="#ffd166", bgcolor="#33271f", bold=True)
_SELECTED_SIDE = Style(color="#ffd166", bgcolor="#33271f", bold=True)
_SELECTED_CORNER = Style(color="#ffd166", bgcolor="#33271f", bold=True)
_WOOD_GRAIN = Style(color="#ffd166", bgcolor="#33271f", bold=True)
_EMPTY_SIDE = Style(color="#998673", bgcolor=ZONE_BODY, meta={'font_role': 'serif'})
_EMPTY_TOP = _EMPTY_SIDE
_EMPTY_CORNER = _EMPTY_SIDE


def _border_style(style: Style, part: str, selected: bool, ascii_art: bool) -> Style:
    # The existing graphics plane draws thin rules on exact cell coordinates.
    # Rich box characters remain a native fallback when graphics is unavailable.
    if ascii_art:
        return style
    return style + Style(meta={'inventory_border': ('selected:' if selected else '') + part, 'font_role': 'serif'})


@dataclass(frozen=True)
class GridMetrics:
    panel_width: int
    columns: int
    inner_w: int
    cell_w: int
    cell_h: int
    grid_w: int
    left_pad: int
    right_pad: int
    gap: int


@dataclass
class GridRender:
    lines: list[Text]
    # 与 lines 逐行对齐：每行是 (x0, x1, 真实行囊下标) 的元组列表；非格子行为空。
    cell_hits: list[tuple[tuple[int, int, int], ...]]
    metrics: GridMetrics
    grid_rows: int
    slots: int


def grid_metrics(panel_width: int) -> GridMetrics:
    width = max(8, int(panel_width))
    # 每格含两列边框；宽面板加一列间隙，剩余留白用于居中。
    gap = 1 if width >= 44 else 0
    inner_w = max(4, min(MAX_CELL_W - 2, (width - gap * (GRID_COLUMNS - 1)) // GRID_COLUMNS - 2))
    cell_w = inner_w + 2
    cell_w = max(MIN_CELL_W, min(MAX_CELL_W, cell_w))
    inner_w = cell_w - 2
    cell_h = max(4, round(cell_w * CELL_ASPECT))
    grid_w = cell_w * GRID_COLUMNS + gap * (GRID_COLUMNS - 1)
    spare = max(0, width - grid_w)
    left_pad = spare // 2
    right_pad = spare - left_pad
    return GridMetrics(width, GRID_COLUMNS, inner_w, cell_w, cell_h,
                       grid_w, left_pad, right_pad, gap)


def slot_count(inventory_count: int, capacity: int) -> int:
    """总格数：容量与当前物品数取大，再向上取整到 5 的倍数。"""
    total = max(int(inventory_count), int(capacity), GRID_COLUMNS)
    return ((total + GRID_COLUMNS - 1) // GRID_COLUMNS) * GRID_COLUMNS


# A few recently used layouts cover selection/size changes without retaining items
# or app instances. Cached Text never escapes: callers append and stylize rows.
_GRID_CACHE: OrderedDict[tuple, GridRender] = OrderedDict()
_GRID_CACHE_LIMIT = 4


def _copy_grid(grid: GridRender) -> GridRender:
    return GridRender([line.copy() for line in grid.lines], list(grid.cell_hits),
                      grid.metrics, grid.grid_rows, grid.slots)


def build_grid(
    inventory: list,
    indices: list[int],
    capacity: int,
    panel_width: int,
    selection: int,
    mode: str,
    equipped_ids: set[str] | frozenset[str] = frozenset(),
    *, border_style: str = 'creased', icon_style: str = 'outline',
) -> GridRender:
    """Reuse stable layout by its rendered content, including mutable item fields."""
    from ..i18n import get_language

    mode = 'themed' if mode == 'unicode' else mode
    # Resolve glyphs/colors rather than keying on item identity: both depend on
    # mutable content registries and character/font fallback configuration.
    contents = []
    for index in indices:
        item = inventory[index] if 0 <= index < len(inventory) else None
        if item is None:
            contents.append(None)
            continue
        contents.append((getattr(item, 'instance_id', None),
                         getattr(item, 'name', ''),
                         int(getattr(item, 'quantity', 1) or 1),
                         drop_glyph(item, mode),
                         panel_color(item_name_color(item), _slot_background(item)),
                         _item_frame(item)))
    key = (len(inventory), tuple(indices), tuple(contents), int(capacity),
           int(panel_width), selection, mode, frozenset(equipped_ids),
           border_style, icon_style, get_language(), ZONE_BODY, FC['count'], FC['effect'],
           _SELECTED_TOP, _SELECTED_SIDE, _SELECTED_CORNER, _WOOD_GRAIN,
           _EMPTY_SIDE, _EMPTY_TOP, _EMPTY_CORNER)
    cached = _GRID_CACHE.get(key)
    if cached is None:
        cached = _build_grid(inventory, indices, capacity, panel_width, selection,
                             mode, equipped_ids, border_style=border_style,
                             icon_style=icon_style)
        _GRID_CACHE[key] = cached
        if len(_GRID_CACHE) > _GRID_CACHE_LIMIT:
            _GRID_CACHE.popitem(last=False)
    else:
        _GRID_CACHE.move_to_end(key)
    return _copy_grid(cached)


def _build_grid(
    inventory: list,
    indices: list[int],
    capacity: int,
    panel_width: int,
    selection: int,
    mode: str,
    equipped_ids: set[str] | frozenset[str] = frozenset(),
    *, border_style: str = 'creased', icon_style: str = 'outline',
) -> GridRender:
    """把可见物品排成 5 列格子；空槽继续往后画到容量。"""
    # Rich/preview callers may use "unicode" for the game's themed glyph mode.
    # Passing it through to drop_glyph would silently select ASCII placeholders.
    if mode == 'unicode':
        mode = 'themed'
    metrics = grid_metrics(panel_width)
    slots = slot_count(len(inventory), capacity)
    grid_rows = slots // GRID_COLUMNS
    used_cells = [inventory[index] if 0 <= index < len(inventory) else None
                  for index in indices]
    ascii_art = mode == "ascii"
    lines: list[Text] = []
    cell_hits: list[tuple[tuple[int, int, int], ...]] = []

    for row in range(grid_rows):
        row_cells = []
        for column in range(GRID_COLUMNS):
            position = row * GRID_COLUMNS + column
            if position < len(indices):
                real_index = indices[position]
                item = used_cells[position]
            else:
                real_index = -1
                item = None
            row_cells.append((real_index, item))

        hits = []
        for column, (real_index, _item) in enumerate(row_cells):
            x0 = metrics.left_pad + column * (metrics.cell_w + metrics.gap)
            hits.append((x0, x0 + metrics.cell_w, real_index))
        hits_tuple = tuple(hits)

        # 上边框
        line = Text(" " * metrics.left_pad)
        for column, (real_index, item) in enumerate(row_cells):
            if column:
                line.append(' ' * metrics.gap)
            selected = real_index >= 0 and real_index == selection
            border = _top_border(metrics, selected, real_index < 0, ascii_art, item)
            if item is not None and getattr(item, 'instance_id', None) in equipped_ids:
                # Put the badge on the upper-right frame, outside the item art.
                position = metrics.cell_w - 2
                badge = Text('*' if ascii_art else '★', style=Style(
                    color=FC['effect'], bgcolor=_slot_background(item), bold=True,
                    meta={} if ascii_art else {'inventory_count': '★', 'font_role': 'serif'}))
                border = Text.assemble(border[:position], badge, border[position+1:])
            line.append_text(border)
        line.append(" " * metrics.right_pad)
        lines.append(line)
        cell_hits.append(hits_tuple)

        # 内部行：图标、数量、装备标记
        inner_rows = [_cell_inner_rows(item, metrics, real_index == selection,
                                       real_index < 0, mode, ascii_art, equipped_ids)
                      for real_index, item in row_cells]
        for inner in range(metrics.cell_h - 2):
            line = Text(" " * metrics.left_pad)
            for column, (real_index, item) in enumerate(row_cells):
                if column:
                    line.append(' ' * metrics.gap)
                selected = real_index >= 0 and real_index == selection
                line.append_text(_side_border(selected, real_index < 0, ascii_art, left=True, item=item))
                line.append_text(inner_rows[column][inner])
                line.append_text(_side_border(selected, real_index < 0, ascii_art, left=False, item=item))
            line.append(" " * metrics.right_pad)
            lines.append(line)
            cell_hits.append(hits_tuple)

        # 下边框
        line = Text(" " * metrics.left_pad)
        for column, (real_index, item) in enumerate(row_cells):
            if column:
                line.append(' ' * metrics.gap)
            selected = real_index >= 0 and real_index == selection
            line.append_text(_bottom_border(metrics, selected, real_index < 0, ascii_art, item))
        line.append(" " * metrics.right_pad)
        lines.append(line)
        cell_hits.append(hits_tuple)

    # Apply options to the same Rich layout and reservations used by graphics.
    from rich.text import Span
    for line in lines:
        spans = []
        for span in line.spans:
            style = span.style
            if not isinstance(style, Style):
                spans.append(span)
                continue
            meta = dict(style.meta)
            part = meta.get('inventory_border')
            corner = part and part.split(':')[-1] in ('tl', 'tr', 'bl', 'br')
            if part and border_style == 'straight':
                meta['inventory_border'] = 'straight:' + part
            if icon_style == 'native':
                for key in ('inventory_icon', 'inventory_reservation', 'inventory_icon_offset', 'inventory_icon_size'):
                    meta.pop(key, None)
            spans.append(Span(span.start, span.end, Style(
                color='#70523c' if corner and 'selected:' not in part else style.color, bgcolor=style.bgcolor,
                bold=style.bold, italic=style.italic, meta=meta)))
        line.spans = spans
    return GridRender(lines, cell_hits, metrics, grid_rows, slots)


def _frame_chars(ascii_art: bool) -> dict[str, str]:
    if ascii_art:
        return {"tl": "+", "tr": "+", "bl": "+", "br": "+",
                "h": "-", "v": "|"}
    return {"tl": "┏", "tr": "┓", "bl": "┗", "br": "┛",
            "h": "─", "v": "│"}


def _heavy_chars(ascii_art: bool) -> dict[str, str]:
    if ascii_art:
        return {"tl": "#", "tr": "#", "bl": "#", "br": "#",
                "h": "=", "bottom": "=", "left": "#", "right": "#"}
    # Solid block corners and half-block rails form a continuous wooden surround.
    return {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟",
            "h": "▀", "bottom": "▄", "left": "▌", "right": "▐"}


def _top_border(metrics: GridMetrics, selected: bool, empty: bool, ascii_art: bool, item=None) -> Text:
    chars = _heavy_chars(ascii_art) if selected else _frame_chars(ascii_art)
    if selected:
        corner_style, edge_style = _SELECTED_CORNER, _SELECTED_TOP
    elif empty:
        corner_style, edge_style = _EMPTY_CORNER, _EMPTY_TOP
    else:
        corner_style = edge_style = _item_frame(item)
    edge = Text()
    for column in range(metrics.inner_w):
        grain = column in (metrics.inner_w // 3, metrics.inner_w * 3 // 4)
        edge.append(chars['h'], _border_style(_WOOD_GRAIN if selected and grain else edge_style,
                                              'top', selected, ascii_art))
    return Text.assemble((chars["tl"], _border_style(corner_style, 'tl', selected, ascii_art)), edge,
                         (chars["tr"], _border_style(corner_style, 'tr', selected, ascii_art)))


def _bottom_border(metrics: GridMetrics, selected: bool, empty: bool, ascii_art: bool, item=None) -> Text:
    chars = _heavy_chars(ascii_art) if selected else _frame_chars(ascii_art)
    if selected:
        corner_style, edge_style = _SELECTED_CORNER, _SELECTED_SIDE
    elif empty:
        corner_style, edge_style = _EMPTY_CORNER, _EMPTY_TOP
    else:
        corner_style = edge_style = _item_frame(item)
    return Text.assemble((chars["bl"], _border_style(corner_style, 'bl', selected, ascii_art)),
                         (chars.get("bottom", chars["h"]) * metrics.inner_w,
                          _border_style(edge_style, 'bottom', selected, ascii_art)),
                         (chars["br"], _border_style(corner_style, 'br', selected, ascii_art)))


def _side_border(selected: bool, empty: bool, ascii_art: bool, *, left: bool, item=None) -> Text:
    chars = _heavy_chars(ascii_art) if selected else _frame_chars(ascii_art)
    style = _SELECTED_SIDE if selected else (_EMPTY_SIDE if empty else _item_frame(item))
    return Text(chars['left' if left else 'right'] if selected else chars['v'],
                style=_border_style(style, 'left' if left else 'right', selected, ascii_art))


def _cell_inner_rows(
    item,
    metrics: GridMetrics,
    selected: bool,
    empty: bool,
    mode: str,
    ascii_art: bool,
    equipped_ids: set[str] | frozenset[str],
) -> list[Text]:
    """一格内部的 (cell_h-2) 行；宽字符按显示列宽居中，数量贴右下角。"""
    inner_h = max(1, metrics.cell_h - 2)
    buffers: list[list[tuple[str, object] | None]] = [
        [None] * metrics.inner_w for _ in range(inner_h)
    ]

    def put(row: int, column: int, value: str, style) -> bool:
        if not value:
            return True
        width = cell_len(value)
        if column < 0 or column + width > metrics.inner_w:
            return False
        if any(buffers[row][column + offset] is not None for offset in range(width)):
            return False
        for offset in range(width):
            buffers[row][column + offset] = (value, style) if offset == 0 else ("", style)
        return True

    if item is not None:
        quantity = ("x" if ascii_art else "×") + str(int(getattr(item, "quantity", 1) or 1))
        count_style = Style(color=FC['count'], meta={} if ascii_art else {'inventory_count': quantity})
        put(inner_h - 1, metrics.inner_w - cell_len(quantity), quantity, count_style)
        icon = drop_glyph(item, mode)
        if icon:
            icon_row = (inner_h - 1) // 2
            icon_width = cell_len(icon)
            icon_column = max(0, (metrics.inner_w - icon_width) // 2)
            # The actual configured character remains in Rich for terminal
            # fallback. The image plane consumes its reserved area metadata.
            inset = 1
            icon_style = Style(color=panel_color(item_name_color(item), _slot_background(item)),
                               bgcolor=_slot_background(item), meta={} if ascii_art else {
                                   'inventory_icon': icon.strip(),
                                   'inventory_icon_offset': (inset-icon_column, -icon_row),
                                   'inventory_icon_size': (max(2, metrics.inner_w-2*inset), inner_h),
                               })
            if not put(icon_row, icon_column, icon, icon_style):
                for candidate in (0, metrics.inner_w - icon_width):
                    if put(icon_row, candidate, icon, icon_style):
                        break
            if not ascii_art:
                # Keep reservations on every visible icon row, so a partially
                # scrolled glyph still has its full outline and clipping box.
                for y in range(inner_h):
                    if buffers[y][inset] is None:
                        meta = dict(icon_style.meta)
                        meta['inventory_reservation'] = meta.pop('inventory_icon')
                        meta['inventory_icon_offset'] = (0, -y)
                        buffers[y][inset] = (' ', Style(color=icon_style.color,
                            bgcolor=icon_style.bgcolor, meta=meta))

    rows: list[Text] = []
    for buffer in buffers:
        row = Text(style=Style(bgcolor=_slot_background(item)))
        for entry in buffer:
            if entry is None:
                row.append(" ")
            elif entry[0]:
                row.append(entry[0], style=entry[1])
        rows.append(row)
    return rows
