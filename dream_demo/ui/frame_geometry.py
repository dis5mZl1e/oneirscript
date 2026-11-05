"""终端格坐标到 Rich 字符区间；宽字符和零宽选择符不等于终端列。"""
from __future__ import annotations

from functools import lru_cache

from rich.cells import get_character_cell_size
from rich.text import Span, Text
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
        overlay = _overlay_rich_style(style, overlay_style)
        for start, end in ranges.get(cell, ()):
            if end > start:
                result.stylize(overlay, start, end)
    replacements = []
    for cell, (glyph, style) in glyphs.items():
        for row, (start, end) in enumerate(ranges.get(cell, ())):
            if end <= start:
                continue
            padding = (cell_w - 1) // 2
            text = (" " * padding + glyph + " " * (cell_w - padding - 1)
                    if row == (cell_h - 1) // 2 else " " * cell_w)
            replacements.append((start, end,
                                 Text(text, style=_glyph_rich_style(style))))
    if not replacements:
        return result
    return _replace_cells(result, replacements)


def _replace_cells(base: Text, replacements: list[tuple[int, int, Text]]) -> Text:
    """一次扫描完成字形替换，结果逐格与「切片再拼装」等价。

    ``Text.divide`` 每切一刀都要按字符区间重排全部 span；一帧 625 格文本里
    只要有一两个字形，逐段切片就会花掉 1–2ms。这里改为：
    先按替换项拼出新纯文本，再把不重叠的 span 平移、与替换区间重叠的 span
    裁掉（该区间由 replacement 自带样式覆盖）。
    """
    ordered = []
    cursor = 0
    for start, end, replacement in sorted(replacements, key=lambda item: item[0]):
        if start < cursor or not replacement.plain:
            continue
        ordered.append((start, end, replacement))
        cursor = end
    parts: list[str] = []
    placed: list[tuple[int, int, int, int]] = []  # (new_start, old_start, old_end, delta)
    cursor = 0
    shift = 0
    for start, end, replacement in ordered:
        parts.append(base.plain[cursor:start])
        new_start = start + shift
        parts.append(replacement.plain)
        delta = len(replacement.plain) - (end - start)
        placed.append((new_start, start, end, delta))
        shift += delta
        cursor = end
    parts.append(base.plain[cursor:])
    plain = "".join(parts)
    out = Text(plain)
    spans = out._spans
    if len(placed) == 1 and not placed[0][3]:
        # 常态：只有一格字形、宽度不变。span 偏移无需平移，只需裁掉被覆盖的段。
        rep_start, rep_end = placed[0][1], placed[0][2]
        for span_start, span_end, style in base._spans:
            if span_end <= rep_start or span_start >= rep_end:
                spans.append(Span(span_start, span_end, style))
                continue
            if span_start < rep_start:
                spans.append(Span(span_start, rep_start, style))
            if span_end > rep_end:
                spans.append(Span(rep_end, span_end, style))
    else:
        for span_start, span_end, style in base._spans:
            pieces = []
            left = span_start
            for _new_start, rep_start, rep_end, _delta in placed:
                if rep_end <= span_start or rep_start >= span_end:
                    continue
                if rep_start > left:
                    pieces.append((left, rep_start))
                left = max(left, rep_end)
            if left < span_end:
                pieces.append((left, span_end))
            for piece_start, piece_end in pieces:
                if piece_end <= piece_start:
                    continue
                spans.append(Span(_shifted(piece_start, placed),
                                  _shifted(piece_end, placed), style))
    for (start, end, replacement), (new_start, _old_start, _old_end, _delta) in zip(ordered, placed):
        if replacement.style:
            spans.append(Span(new_start, new_start + len(replacement.plain),
                              replacement.style))
        else:
            for span in replacement._spans:
                spans.append(Span(new_start + span.start, new_start + span.end,
                                  span.style))
    return out


def _shifted(position: int, placed: list[tuple[int, int, int, int]]) -> int:
    """旧偏移 → 新偏移：越过已放置的替换项就累计长度差，落在替换内则截断到起点。"""
    shift = 0
    for new_start, old_start, old_end, delta in placed:
        if position >= old_end:
            shift += delta
        elif position > old_start:
            return new_start
        else:
            break
    return position + shift


# 叠加层取值是有限调色板；Rich 的 ``stylize`` 每次都重新解析样式串，逐格解析
# 在 20Hz 下是实打实的开销。按取值缓存 Style，输出的样式逐格一致。
_OVERLAY_STYLE_CACHE: dict[str, Style] = {}
_GLYPH_STYLE_CACHE: dict[str, Style] = {}


def _overlay_rich_style(value: str, translate) -> Style:
    style = _OVERLAY_STYLE_CACHE.get(value)
    if style is None:
        if len(_OVERLAY_STYLE_CACHE) > 4096:
            _OVERLAY_STYLE_CACHE.clear()
        style = Style.parse(translate(value))
        _OVERLAY_STYLE_CACHE[value] = style
    return style


def _glyph_rich_style(value: str) -> Style:
    """字形前景样式（不经 overlay_style 的“on”翻译），与逐格解析结果等价。"""
    style = _GLYPH_STYLE_CACHE.get(value)
    if style is None:
        if len(_GLYPH_STYLE_CACHE) > 4096:
            _GLYPH_STYLE_CACHE.clear()
        style = Style.parse(value)
        _GLYPH_STYLE_CACHE[value] = style
    return style
