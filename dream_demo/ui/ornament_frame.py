"""Region and realm ornaments painted on existing Textual borders, with identical geometry."""
from __future__ import annotations

from rich.cells import cell_len
from rich.segment import Segment
from rich.style import Style
from textual.containers import Vertical
from textual.strip import Strip

from .border_feedback import blend_feedback_color
from .border_patterns import pattern_cells
from .deco import pulse_hex
from .deco import flow_color, mix_hex
from .realm_borders import REALM_BORDERS, realm_border_cells


def apply_feedback_color(cells, feedback):
    """Return a new cell map with the current short feedback blended in."""
    if feedback is None:
        return cells
    kind, strength = feedback
    return {position: (glyph, blend_feedback_color(color, kind, strength))
            for position, (glyph, color) in cells.items()}


def ornament_cells(width, height, depth, quality='high', t=0.0, unicode=True,
                   kind='panel', active=False, realm_id=''):
    if width < 6 or height < 3:
        return {}
    # Prototype patterns (docs §9 first delivery): stable geometry, theme-specific
    # static modules and motion. Other regions continue on the legacy ornaments
    # until they get their own pass, so existing layouts/tests keep working.
    prototype = pattern_cells(width, height, depth, quality, t, unicode,
                              active, kind=kind, realm_id=realm_id)
    if prototype is not None:
        assert all(cell_len(glyph) == 1 for glyph, _ in prototype.values())
        return prototype
    if kind != 'menu' and realm_id in REALM_BORDERS:
        return realm_border_cells(width, height, realm_id, quality, t, unicode, active)
    region = 0 if depth <= 10 else 1 if depth <= 20 else 2
    corners = (('╭', '╮', '╰', '╯'), ('╔', '╗', '╚', '╝'), ('┏', '┓', '┗', '┛'))[region]
    marks = (('·', '─', '·'), ('╪', '═', '╪'), ('╱', '━', '╲'))[region]
    if not unicode:
        corners = ('+', '+', '+', '+')
        marks = (('.', '-', '.'), ('|', '=', '|'), ('/', '#', '\\'))[region]
    accent = ('#84b9c8', '#c89bd9', '#929cc9')[region]
    color = accent if quality == 'off' else pulse_hex(accent, '#e5d8b4', t, depth=.28)
    if kind == 'menu':
        corners = ('╭', '╮', '╰', '╯') if unicode else ('+',)*4
        marks = ('─', '┬', '─') if unicode else ('-', '+', '-')
        color = '#f1d9a0' if active else '#44505b'
    elif active:
        color = mix_hex(color, '#f2dfad', .35)
    cells = {(0, 0): corners[0], (width-1, 0): corners[1],
             (0, height-1): corners[2], (width-1, height-1): corners[3]}
    if kind == 'menu':
        for x in range(1,width-1):
            cells[(x,0)] = cells[(x,height-1)] = '─' if unicode else '-'
        for y in range(1,height-1):
            cells[(0,y)] = cells[(width-1,y)] = '│' if unicode else '|'
    else:
        horizontal = ('─', '═', '━')[region] if unicode else ('-', '=', '#')[region]
        vertical = ('│', '║', '┃')[region] if unicode else '|'
        for x in range(1, width-1):
            cells[(x, 0)] = cells[(x, height-1)] = horizontal
        for y in range(1, height-1):
            cells[(0, y)] = cells[(width-1, y)] = vertical
    compact = width < 45 or height < 24 or quality == 'low'
    for y in (0, height-1):
        for x, glyph in zip(range(2, min(5, width//2)), marks):
            cells[(x, y)] = glyph
            cells[(width-1-x, y)] = glyph
    if not compact:
        for y in range(5, height-3, 7):
            cells[(0, y)] = ':' if not unicode else ('┆', '╫', '┇')[region]
            cells[(width-1, y)] = cells[(0, y)]
    # Bright joints travel around the existing border. Never use extra rows or
    # insert ornaments into labels/content, even for three-row menu buttons.
    if width >= 18:
        mark = ('┬' if unicode else '+') if kind == 'menu' else marks[1]
        for y in (0, height-1):
            cells[(width//2, y)] = '┴' if unicode and kind == 'menu' and y else mark
    assert all(cell_len(glyph) == 1 for glyph in cells.values())
    return {position: (glyph, color if quality != 'high' else
                       mix_hex(color, flow_color(x+y*2, t), .62 if not active else .78))
            for position, glyph in cells.items() for x, y in (position,)}


class OrnamentBorderMixin:
    """Paint after Textual's border pass, never inside the content or mouse grid."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_class('ornament-frame')
        self._ornament = (0, 'off', 0.0, True, '', None)
        # 边框几何/颜色按「装饰状态+尺寸+焦点」缓存；同一帧内多次 render_lines
        # （Textual 全宽、局部裁切、浮层重绘）不再重复生成整圈 pattern。
        self._ornament_cells_key = None
        self._ornament_cells_by_row: dict[int, tuple[tuple[int, str, str], ...]] = {}

    def paint_ornament(self, depth, quality, t, unicode=True, realm_id='',
                       feedback=None):
        # 反馈强度量化，避免浮点噪声每帧触发全屏重绘；kind+量化强度参与缓存键。
        fb = None if feedback is None else (feedback[0], round(float(feedback[1]), 2))
        state = (depth, quality, 0.0 if quality == 'off' or
                 (realm_id in REALM_BORDERS and quality == 'low') else t,
                 unicode, realm_id, fb)
        if state != self._ornament:
            self._ornament = state
            self.refresh()

    def render_lines(self, crop):
        strips = super().render_lines(crop)
        depth, quality, t, unicode, realm_id, feedback = self._ornament
        width, height = self.region.width, self.region.height
        # All four borders exist on these two panes. Respect any future borderless layout.
        if any(not edge[0] or edge[0] in ('none', 'hidden') for edge in self.styles.border):
            return strips
        menu = (self.id or '').startswith(('home-', 'slot-', 'delete-', 'pause-', 'test-mode', 'newgame-'))
        active = self.has_class('selected') or self.has_focus or self.mouse_hover
        key = (self._ornament, width, height, active, menu)
        if key != self._ornament_cells_key:
            cells = ornament_cells(width, height, depth, quality, t, unicode,
                                   kind='menu' if menu else 'panel',
                                   active=active, realm_id=realm_id)
            if feedback is not None and quality != 'off':
                # 短时反馈暂替主题光色，结束后下一帧立即回到主题相位，不冻结末帧。
                cells = apply_feedback_color(cells, feedback)
            by_row: dict[int, list[tuple[int, str, str]]] = {}
            for (x, cy), (glyph, color) in cells.items():
                by_row.setdefault(cy, []).append((x, glyph, color))
            self._ornament_cells_by_row = {
                cy: tuple(sorted(row, key=lambda item: item[0]))
                for cy, row in by_row.items()
            }
            self._ornament_cells_key = key
        for row, strip in enumerate(strips):
            y = crop.y + row
            positions = sorted((x-crop.x, glyph, color)
                               for x, glyph, color in self._ornament_cells_by_row.get(y, ())
                               if crop.x <= x < crop.right)
            if not positions:
                continue
            segments, cursor = [], 0
            for x, glyph, color in positions:
                segments.extend(strip.crop(cursor, x))
                sample = next(iter(strip.crop(x, x+1)), None)
                style = (sample.style if sample and sample.style else Style()) + Style(color=color)
                segments.append(Segment(glyph, style))
                cursor = x+1
            segments.extend(strip.crop(cursor, strip.cell_length))
            strips[row] = Strip(segments, strip.cell_length)
        return strips


class OrnamentPane(OrnamentBorderMixin, Vertical):
    pass
