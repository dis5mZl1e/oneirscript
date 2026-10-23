"""One-column ornamental frames on the existing dream-realm perimeter."""
from dataclasses import dataclass
from math import sin, tau

from .deco import mix_hex


@dataclass(frozen=True)
class RealmBorder:
    name: str
    color: str
    highlight: str
    corners: str
    horizontal: str
    vertical: str
    seal: str
    ascii_horizontal: str
    ascii_vertical: str
    line_style: str = 'round'


REALM_BORDERS = {
    'door_corridor': RealmBorder('黄铜门扉', '#d4b477', '#94bab2',
        '╔╗╚╝', '═╤═╪═', '║╫║', '╪', '=[=|=', '|:|', 'double'),
    'toy_memories': RealmBorder('彩色积木', '#efa2b3', '#99dac0',
        '┌┐└┘', '─□─┬─', '│○│', '□', '-o-+-', '|o|', 'solid'),
    'ember_bridge': RealmBorder('铜金裂纹', '#ee9562', '#efce8c',
        '╒╕╘╛', '━╱━╲━', '│╱│╲', '⋄', '-/-\\-', '|/|\\', 'heavy'),
    'ebbing_hall': RealmBorder('青蓝潮纹', '#64bdd6', '#a7dfce',
        '╭╮╰╯', '─≈─~─', '│≈│', '≈', '-~-~-', '|~|'),
    'millennium_garden': RealmBorder('像素霓虹', '#a3df8e', '#e0a1d5',
        '╔╗╚╝', '═░═▒═', '║░║▒', '╬', '=.=#=', '|#|.', 'double'),
    'library_palace': RealmBorder('金色书脊', '#d8bf86', '#b89bc9',
        '╓╖╙╜', '─┤◇├─', '║§║┊', '◇', '-]o[-', '|:|;', 'double'),
    'white_sanatorium': RealmBorder('银白净环', '#d2e8ec', '#93bed2',
        '╭╮╰╯', '─┄┼┄─', '│○│┼', '┼', '--+--', '|+|:'),
}


def realm_border_cells(width, height, realm_id, quality, t, unicode, active):
    theme = REALM_BORDERS[realm_id]
    corners = theme.corners if unicode else '++++'
    horizontal = theme.horizontal if unicode else theme.ascii_horizontal
    vertical = theme.vertical if unicode else theme.ascii_vertical
    base = mix_hex(theme.color, theme.highlight, .22) if active else theme.color
    # Keep the engraving, but restore a visible light travelling around the
    # entire perimeter. Similar-luminance theme colours alone hide the chase.
    phase = t * .07 if quality == 'high' else 0
    dark = mix_hex(base, '#192137', .42)
    light = mix_hex(theme.highlight, '#effaff', .72)
    palette = []
    for i in range(32):
        wave = (.5 + .5 * sin(tau * (i / 32 - phase))) ** 2
        palette.append(mix_hex(dark, light, .12 + .88 * wave)
                       if quality == 'high' else base)
    cells = {}
    for x in range(1, width - 1):
        glyph = horizontal[(x - 1) % len(horizontal)]
        cells[(x, 0)] = (glyph, palette[(x // 2) % 32])
        cells[(x, height - 1)] = (glyph, palette[((2 * width + height - x) // 2) % 32])
    for y in range(1, height - 1):
        glyph = vertical[(y - 1) % len(vertical)]
        cells[(width - 1, y)] = (glyph, palette[((width + y) // 2) % 32])
        cells[(0, y)] = (glyph, palette[((2 * width + 2 * height - y) // 2) % 32])
    if width >= 12:
        seal = theme.seal if unicode else horizontal[len(horizontal) // 2]
        for y in (0, height - 1):
            cells[(width // 2, y)] = (seal, theme.highlight)
    for position, glyph in zip(((0, 0), (width-1, 0), (0, height-1),
                                (width-1, height-1)), corners):
        cells[position] = (glyph, theme.color)
    return cells
