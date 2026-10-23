"""终端格坐标到 Rich 字符区间；宽字符和零宽选择符不等于终端列。"""
from __future__ import annotations

from functools import lru_cache

from rich.cells import get_character_cell_size
from rich.text import Text
from rich.style import Style
from rich.errors import StyleSyntaxError

CellRanges = dict[tuple[int, int], tuple[tuple[int, int], ...]]


@lru_cache(maxsize=128)
def projectile_color(value: str) -> str:
    """物品配色可能是 bright_yellow 等 Rich 样式，先转为引擎的 RGB 输入。"""
    try:
        color = Style.parse(value).color
        if color is not None:
            rgb = color.get_truecolor()
            return "#{:02x}{:02x}{:02x}".format(*rgb)
    except (ValueError, TypeError, StyleSyntaxError):
        pass
    return "#ffe0b3"


def cell_ranges(frame: Text, width: int, height: int,
                cell_w: int, cell_h: int) -> CellRanges:
    rows: list[list[tuple[int, int]]] = []
    offset = 0
    for line in frame.plain.split("\n"):
        # 每列关联整个字形；后随零宽字符属于前面的字形。
        columns: list[tuple[int, int]] = []
        for index, char in enumerate(line):
            size = get_character_cell_size(char)
            if size == 0 and columns:
                start, _ = columns[-1]
                previous = columns[-1]
                for col in range(len(columns) - 1, -1, -1):
                    if columns[col] != previous:
                        break
                    columns[col] = (start, offset + index + 1)
            elif size:
                columns.extend([(offset + index, offset + index + 1)] * size)
        ranges = []
        for x in range(width):
            lo, hi = x * cell_w, (x + 1) * cell_w
            if hi <= len(columns):
                ranges.append((columns[lo][0], columns[hi - 1][1]))
            else:
                ranges.append((offset + len(line), offset + len(line)))
        rows.append(ranges)
        offset += len(line) + 1
    return {
        (x, y): tuple(rows[y * cell_h + r][x] for r in range(cell_h)
                      if y * cell_h + r < len(rows))
        for y in range(height) for x in range(width)
    }


def compose_fx(base: Text, ranges: CellRanges, styles: dict,
               glyphs: dict, cell_w: int, cell_h: int) -> Text:
    """先样式后字形；每一帧从基帧重建，避免轨迹残留。"""
    from .effects import overlay_style

    result = base.copy()
    for cell, style in styles.items():
        for start, end in ranges.get(cell, ()):
            if end > start:
                result.stylize(overlay_style(style), start, end)
    replacements = []
    for cell, (glyph, style) in glyphs.items():
        for row, (start, end) in enumerate(ranges.get(cell, ())):
            if end <= start:
                continue
            padding = (cell_w - 1) // 2
            text = (" " * padding + glyph + " " * (cell_w - padding - 1)
                    if row == (cell_h - 1) // 2 else " " * cell_w)
            replacements.append((start, end, Text(text, style=style)))
    if not replacements:
        return result
    out = Text()
    cursor = 0
    for start, end, replacement in sorted(replacements, key=lambda item: item[0]):
        if start < cursor:
            continue
        out.append_text(result[cursor:start])
        out.append_text(replacement)
        cursor = end
    out.append_text(result[cursor:])
    return out
