"""Rich views of equipment art; two background-painted columns per cell.

No emoji or font-dependent glyph widths. Art never defines hit boxes or slots.
"""
from rich.text import Text

from ..data.icon_glyphs import ICONS as _ICONS, icon_text as _icon_text
from ..equipment.icon_art import painted_cells
from ..data.expansion.catalog import ENTRIES as _EXPANSION_ENTRIES
_EXPANSION_ART_ICONS = {e['id']: e for e in _EXPANSION_ENTRIES if e['category'] == 'equipment'}


def piece_cell_text(piece, cell, piece_glyphs):
    from ..equipment.function_words import FUNCTION_WORDS
    from ..i18n import get_language
    word = FUNCTION_WORDS.get(piece.piece_id)
    if word is None:
        return piece_glyphs.get(piece.piece_id, '?') + ' '
    dx = cell[0] - piece.x
    if get_language() == 'zh':
        return word.label[dx]
    english = {'word_de': 'of', 'word_de_manner': 'ly', 'word_ba': 'DO', 'word_bei': 'by',
               'word_and': '& ',
               'word_or': 'or', 'word_if': 'if', 'word_else': 'el', 'word_only': 'on', 'word_from': 'fr',
               'word_toward': 'to','word_again':'re'}
    return english.get(piece.piece_id, '??') if dx == 0 else '  '


def icon_cell(definition_id, x, y, rotation=0, *, emphasis="", icons_enabled=None):
    entry = next(((l, r, g) for cx, cy, l, r, g in
                  painted_cells(definition_id, rotation) if (cx, cy) == (x, y)),
                 None)
    if entry is None:
        left, right, glyphs = "#8c96a8", "#c5a778", ("", "", "", "")
    else:
        left, right, glyphs = entry
    left_glyph, left_fg, right_glyph, right_fg = glyphs
    expansion = _EXPANSION_ART_ICONS.get(definition_id)
    if expansion is not None and left_glyph == expansion['source_character']:
        # The board and inventory share the reviewed PUA drawing; system font
        # fallbacks must not substitute a different silhouette inside the board.
        #
        # 2026-10-27 A4：ICONS 开关由整张图/整块盘面的调用方解析一次传下来
        #（icons_enabled），逐格不再各读一次环境变量；调用方没传时按单格现读
        #（themed_icon 每次现读活环境，运行时切换仍立即生效）。
        icon_key = expansion['icon_key']
        if icons_enabled is None:
            from ..symbols import themed_icon
            private = themed_icon(icon_key)
        else:
            private = _icon_text(icon_key) if (icons_enabled and icon_key in _ICONS) else None
        left_glyph = private or expansion['terminal_fallback']
        right_fg = None  # The returned icon already reserves the whole two-cell slot.

    def bg_style(bg):
        return f"{emphasis} on {bg}".strip() if emphasis else f"on {bg}"

    def glyph_style(fg, bg):
        base = f"{fg} on {bg}"
        return f"{emphasis} {base}" if emphasis else base

    if left_glyph and left_fg:
        # 前景字形格：宽字形（右列 fg 为 None）独占两列；窄字形左列 + 右列补底。
        parts = [(left_glyph, glyph_style(left_fg, left))]
        if right_fg is not None:
            parts.append((" ", bg_style(right)))
    else:
        parts = [(" ", bg_style(left))]
        if right_glyph and right_fg:
            parts.append((right_glyph, glyph_style(right_fg, right)))
        else:
            parts.append((" ", bg_style(right)))
    return Text.assemble(*parts)


def icon_lines(definition_id, rotation=0):
    from ..symbols import themed_icons_enabled
    cells = painted_cells(definition_id, rotation)
    width = max(x for x, *_ in cells) + 1
    height = max(y for _, y, *_ in cells) + 1
    occupied = {(x, y) for x, y, *_ in cells}
    icons_enabled = themed_icons_enabled()
    lines = []
    for y in range(height):
        line = Text()
        for x in range(width):
            if (x, y) in occupied:
                line.append_text(icon_cell(definition_id, x, y, rotation,
                                           icons_enabled=icons_enabled))
            else:
                line.append("  ")
        lines.append(line)
    return lines


def board_art_rows(board, piece_glyphs):
    """Compact equipment panel uses the same artwork as the full editor."""
    from ..equipment.board import piece_cells
    equipment = {cell: placement for placement in board.placements for cell in placement.cells()}
    marks = {(trace.x, trace.y): ',' if trace.connector == 'straight' else ';'
             for trace in board.traces}
    marks.update({cell: piece_cell_text(piece, cell, piece_glyphs)
                  for piece in board.pieces for cell in piece_cells(piece)})
    from ..symbols import themed_icons_enabled
    icons_enabled = themed_icons_enabled()
    rows = [Text('┌' + '─' * (board.width * 2) + '┐', style='grey74')]
    for y in range(board.height):
        line = Text('│', style='grey74')
        for x in range(board.width):
            placement = equipment.get((x, y))
            if placement is not None:
                line.append_text(icon_cell(placement.definition_id, x-placement.x,
                                           y-placement.y, placement.rotation,
                                           icons_enabled=icons_enabled))
            else:
                mark = marks.get((x, y), '· ')
                line.append(mark if len(mark) != 1 or mark not in ',;' else mark+' ', style='grey62')
        line.append('│', style='grey74')
        rows.append(line)
    rows.append(Text('└' + '─' * (board.width * 2) + '┘', style='grey74'))
    return rows
