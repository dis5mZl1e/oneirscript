
"""Static border patterns for main-dream regions and realms (docs §9).

Each theme has a distinct static skeleton (corners, horizontal/vertical modules,
seal, palette, motion family) and keeps the existing Textual perimeter geometry:
one single-column glyph per border cell, no extra rows/columns, title strip
reserved. Motion only changes colors in this delivery, so layout and hit areas
cannot move; glyph-frame animation can be added per theme later.
"""
from __future__ import annotations

from dataclasses import dataclass

from .border_motion import intensity, palette_sample
from .deco import mix_hex


@dataclass(frozen=True)
class BorderPattern:
    key: str
    name: str
    corners: str
    horizontal: str
    vertical: str
    accent: str
    highlight: str
    seal: str
    motion: str
    ascii_horizontal: str
    ascii_vertical: str


PATTERNS = {
    # ---- 五类主梦（docs §9.3）----
    'start': BorderPattern(
        key='start', name='梦的起始·纸框', corners='╭╮╰╯',
        horizontal='─·─◇─·─╭─', vertical='│·│◇│╰│',
        accent='#cbb7e8', highlight='#f4ecdf', seal='◇', motion='start',
        ascii_horizontal='-.-o-.-+-', ascii_vertical='|.|o|+|'),
    'shallow': BorderPattern(
        key='shallow', name='浅层纸框', corners='╭╮╰╯',
        horizontal='─┄─┬┆─┄─', vertical='│┆│┬┆│',
        accent='#84b9c8', highlight='#e8f4f3', seal='◇', motion='paper',
        ascii_horizontal='-~-+-~-', ascii_vertical='|.|:||'),
    'hallucination': BorderPattern(
        key='hallucination', name='幻觉双轨框', corners='╭╮╰╯',
        horizontal='═─◇─═─◇─', vertical='║│◇│║│',
        accent='#c86fa8', highlight='#8f7de0', seal='◇', motion='hallucination',
        ascii_horizontal='=-o-=-o-', ascii_vertical='||o|||'),
    'unconscious': BorderPattern(
        key='unconscious', name='无意识厚框', corners='┏┓┗┛',
        horizontal='━┿━╋━┿━', vertical='┃╫┃╋┃',
        accent='#d0806a', highlight='#8c6a5a', seal='▣', motion='unconscious',
        ascii_horizontal='#+#+#+#+#', ascii_vertical='|+|+|'),
    'deep': BorderPattern(
        key='deep', name='深层封条框', corners='┌┐└┘',
        horizontal='─╴─╶─╵─╴─', vertical='│╵│╷│',
        accent='#9aa0a6', highlight='#d8d8d8', seal='□', motion='deep',
        ascii_horizontal='-.-.-.-.', ascii_vertical='|.|:|'),
    # ---- 七个位面（docs §9.4）----
    'door_corridor': BorderPattern(
        key='door_corridor', name='黄铜门扉', corners='╔╗╚╝',
        horizontal='═╤═╪═╤═', vertical='║╫║',
        accent='#d4b477', highlight='#94bab2', seal='╪', motion='door',
        ascii_horizontal='=+=+=+=', ascii_vertical='|+|'),
    'toy_memories': BorderPattern(
        key='toy_memories', name='彩色积木', corners='┌┐└┘',
        horizontal='─□─┬─◇─', vertical='│○│□│',
        accent='#efa2b3', highlight='#99dac0', seal='□', motion='toy',
        ascii_horizontal='-o-+-o-', ascii_vertical='|o|o|'),
    'ember_bridge': BorderPattern(
        key='ember_bridge', name='铜金裂纹', corners='╒╕╘╛',
        horizontal='━╱━╲━╱━', vertical='│╱│╲│',
        accent='#ee9562', highlight='#efce8c', seal='◇', motion='ember',
        ascii_horizontal='#/#\\#/#', ascii_vertical='|/|\\|'),
    'ebbing_hall': BorderPattern(
        key='ebbing_hall', name='青蓝潮纹', corners='╭╮╰╯',
        horizontal='─≈─~─≈─', vertical='│≈│~│',
        accent='#64bdd6', highlight='#a7dfce', seal='≈', motion='tide',
        ascii_horizontal='-~-~-~-', ascii_vertical='|~|~|'),
    'millennium_garden': BorderPattern(
        key='millennium_garden', name='千禧像素窗', corners='┌┐└┘',
        horizontal='─░─▒─┬', vertical='│░│▒┬',
        accent='#a3df8e', highlight='#e0a1d5', seal='▣', motion='pixel',
        ascii_horizontal='-.-+-', ascii_vertical='|.|:'),
    'library_palace': BorderPattern(
        key='library_palace', name='金色书脊', corners='╓╖╙╜',
        horizontal='─┤◇├─§─', vertical='║§║┊║',
        accent='#d8bf86', highlight='#b89bc9', seal='§', motion='library',
        ascii_horizontal='-]o[-.-', ascii_vertical='|:|;|'),
    'white_sanatorium': BorderPattern(
        key='white_sanatorium', name='银白净环', corners='╭╮╰╯',
        horizontal='─┄┼┄─○─', vertical='│○│┼│',
        accent='#d2e8ec', highlight='#93bed2', seal='○', motion='sanatorium',
        ascii_horizontal='--+--o-', ascii_vertical='|o|+|'),
}

REALM_PATTERN_IDS = ('door_corridor', 'toy_memories', 'ember_bridge', 'ebbing_hall',
                     'millennium_garden', 'library_palace', 'white_sanatorium')


def theme_for(depth: int, realm_id: str = '') -> BorderPattern | None:
    if realm_id in PATTERNS:
        return PATTERNS[realm_id]
    if realm_id:
        # 未知/未登记的位面回退主梦深度主题（与旧实现一致）。
        return theme_for(depth, '')
    depth = int(depth)
    if depth <= 0:
        return PATTERNS['start']
    if depth <= 10:
        return PATTERNS['shallow']
    if depth <= 20:
        return PATTERNS['hallucination']
    if depth <= 27:
        return PATTERNS['unconscious']
    if depth <= 30:
        return PATTERNS['deep']
    return None


def title_reserved_columns(width: int, height: int) -> set[int]:
    if width < 18:
        return set()
    center = width // 2
    return set(range(max(2, center - 6), min(width - 2, center + 7)))


def _perimeter_positions(width: int, height: int):
    total = max(1, 2 * (width + height) - 4)
    index = 0
    for x in range(1, width - 1):
        yield x, 0, index / total, index, total
        index += 1
    for y in range(1, height - 1):
        yield width - 1, y, index / total, index, total
        index += 1
    for x in range(width - 2, 0, -1):
        yield x, height - 1, index / total, index, total
        index += 1
    for y in range(height - 2, 0, -1):
        yield 0, y, index / total, index, total
        index += 1


def pattern_cells(width: int, height: int, depth: int, quality: str, t: float,
                  unicode: bool, active: bool, kind: str = 'panel',
                  realm_id: str = '') -> dict | None:
    if kind == 'menu' or width < 6 or height < 3:
        return None
    theme = theme_for(depth, realm_id)
    if theme is None:
        return None
    reserved = title_reserved_columns(width, height)
    cells: dict[tuple[int, int], tuple[str, str]] = {}
    low = quality != 'high'
    base = mix_hex(theme.accent, theme.highlight, .22) if active else theme.accent
    horizontal = theme.horizontal if unicode else theme.ascii_horizontal
    vertical = theme.vertical if unicode else theme.ascii_vertical
    # 颜色按 16 级量化后缓存：高动态边缘最多几百格，逐格解析 hex 会成为瓶颈。
    palette: dict[int, str] = {}

    def tone(value: float) -> str:
        level = max(0, min(16, int(round(value * 16))))
        color = palette.get(level)
        if color is None:
            color = palette_sample(base, theme.highlight, level / 16, low=False)
            palette[level] = color
        return color
    for x, y, position, index, total in _perimeter_positions(width, height):
        if unicode:
            glyph = horizontal[(x - 1) % len(horizontal)] if y in (0, height - 1) else \
                vertical[(y - 1) % len(vertical)]
        else:
            glyph = '-' if y in (0, height - 1) else '|'
        if y == 0 and x in reserved:
            glyph = '─' if unicode else '-'
            color = base
        elif low:
            color = base
        else:
            value = intensity(theme.motion, t, position, index, total,
                              x=x, y=y, width=width, height=height)
            color = tone(value)
        cells[(x, y)] = (glyph, color)
    corners = theme.corners if unicode else '++++'
    for position, glyph in zip(((0, 0), (width - 1, 0), (0, height - 1),
                                (width - 1, height - 1)), corners):
        cells[position] = (glyph if unicode else '+',
                           theme.highlight if active else theme.accent)
    if width >= 12 and unicode:
        seal_x = width // 2
        if seal_x not in reserved:
            cells[(seal_x, height - 1)] = (theme.seal, theme.highlight)
    return cells
