"""Region and realm ornaments painted on existing Textual borders, with identical geometry."""
from __future__ import annotations
from functools import lru_cache

from rich.cells import cell_len
from rich.segment import Segment
from rich.style import Style
from textual.containers import Vertical
from textual.geometry import Region
from textual.strip import Strip

from .border_feedback import blend_feedback_color
from .border_patterns import pattern_cells
from .deco import pulse_hex
from .deco import flow_color, mix_hex
from .realm_borders import REALM_BORDERS, realm_border_cells


_BORDER_BASE_CACHE_ENABLED = True


def set_border_base_cache_enabled(enabled: bool) -> None:
    """测试/探针用：切换边框基线条带缓存。"""
    global _BORDER_BASE_CACHE_ENABLED
    _BORDER_BASE_CACHE_ENABLED = bool(enabled)


@lru_cache(maxsize=2048)
def _ornament_row(source, length, positions):
    """Split once, rather than creating two cached Strips per border cell."""
    cells = {x: (glyph, color) for x, glyph, color in positions}
    cuts = sorted({length, *(x for x in cells if x), *(x + 1 for x in cells)})
    result = []
    start = 0
    for end, part in zip(cuts, Segment.divide(source, cuts)):
        replacement = cells.get(start)
        if replacement is None:
            result.extend(part)
        else:
            glyph, color = replacement
            sample = part[0].style if part else None
            result.append(Segment(glyph, (sample or Style()) + Style(color=color)))
        start = end
    return Strip(result, length)


def apply_feedback_color(cells, feedback):
    """Return a new cell map with the current short feedback blended in."""
    if feedback is None:
        return cells
    kind, strength = feedback
    return {position: (glyph, blend_feedback_color(color, kind, strength))
            for position, (glyph, color) in cells.items()}


def solid_right_edge(strips, crop, width: int, height: int, glyph: str = '│'):
    """把控件右边缘整列锁成同一个竖线字形，保留该格原有颜色呼吸。

    装饰珠链的竖边是按行循环的模块（如 ``│·│◇│╰│``），点、菱形与转角符号
    落在一条本该笔直的线上；当这条线紧挨另一个面板的实线边框时（图鉴左列表
    与右详情之间只隔一列），那些行看起来就像"错开了半格"。中线必须逐行同形，
    其余三边照常装饰。上下两行是圆角行，留原样。
    """
    if width < 3 or height < 3:
        return strips
    x = width - 1
    if not (crop.x <= x < crop.right):
        return strips
    offset = x - crop.x
    for row, strip in enumerate(strips):
        y = crop.y + row
        if y <= 0 or y >= height - 1:
            continue
        if strip.cell_length <= offset:
            continue
        head = strip.crop(0, offset)
        cell = strip.crop(offset, offset + 1)
        tail = strip.crop(offset + 1, strip.cell_length)
        first = next(iter(cell), None)
        style = first.style if first is not None else None
        strips[row] = Strip(list(head) + [Segment(glyph, style)] + list(tail),
                            strip.cell_length)
    return strips


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
        self._ornament = (0, 'off', 0.0, True, '', None, 1.0)
        # 边框几何/颜色按「装饰状态+尺寸+焦点」缓存；同一帧内多次 render_lines
        # （Textual 全宽、局部裁切、浮层重绘）不再重复生成整圈 pattern。
        self._ornament_cells_key = None
        self._ornament_cells_by_row: dict[int, tuple[tuple[int, str, str], ...]] = {}
        # 只有边框的裁切（装饰帧刷新的 4 条细区域）与装饰状态无关；Textual
        # 的 styles_cache 仍会为每次刷新重算边框/内边距。缓存它们的基线条带，
        # 装饰弧只是在其上替换字形，避免 5Hz 装饰/每步合成重复走整条样式链。
        self._border_base_cache: dict[tuple, list] = {}

    def paint_ornament(self, depth, quality, t, unicode=True, realm_id='',
                       feedback=None, focus_dim=1.0):
        # 反馈强度量化，避免浮点噪声每帧触发全屏重绘；kind+量化强度参与缓存键。
        # 可见边框由本 mixin 覆盖绘制，styles.border 的颜色/线型只是底稿；
        # 焦点压暗必须走 focus_dim，否则改 styles 在屏幕上没有任何效果。
        fb = None if feedback is None else (feedback[0], round(float(feedback[1]), 2))
        # Menu glyph geometry is time-independent. Glass overwrites every
        # nonblank perimeter color, so its underlying chase is invisible and
        # must not invalidate the native label at the decoration timer rate.
        glass_menu = self.has_class('glass-button') and (self.id or '').startswith(
            ('home-', 'slot-', 'delete-', 'pause-', 'test-mode', 'newgame-'))
        state = (depth, quality, 0.0 if quality == 'off' or
                 glass_menu or (realm_id in REALM_BORDERS and quality == 'low') else t,
                 unicode, realm_id, fb, round(float(focus_dim), 2))
        if state != self._ornament:
            self._ornament = state
            # 没有可绘制边框的 widget（玻璃按钮/EventPanel 等）render_lines 会
            # 直接返回原条带；旧实现仍每帧把这四条区域标脏，5Hz 装饰会在各按钮
            # 分散位置制造脏区，逼出全屏合成。这里先判边框，没有就不刷新。
            if not self._has_paintable_border():
                return
            # refresh regions are content-relative; borders live outside that
            # box (including any padding). Do not invalidate the pane body.
            width, height = self.region.size
            if width and height:
                dx, dy = self.content_offset
                self.refresh(*(region.translate((-dx, -dy)) for region in (
                    Region(0, 0, width, 1), Region(0, height - 1, width, 1),
                    Region(0, 1, 1, max(0, height - 2)),
                    Region(width - 1, 1, 1, max(0, height - 2)),
                ) if region))

    def _has_paintable_border(self) -> bool:
        # 与 render_lines 的旧守卫一致：四条边都有边框才由本 mixin 覆盖绘制；
        # 缺一条就完全交给 Textual，装饰帧也不该刷新它。
        return all(edge[0] and edge[0] not in ('none', 'hidden')
                   for edge in self.styles.border)

    def _border_base_strips(self, crop):
        """基线条带缓存：仅对「整条边框」裁切生效（装饰帧只刷这四条细区域）。"""
        if not _BORDER_BASE_CACHE_ENABLED:
            return super().render_lines(crop)
        width, height = self.region.width, self.region.height
        if not width or not height:
            return super().render_lines(crop)
        border_only = ((crop.height == 1 and crop.y in (0, height - 1))
                       or (crop.width == 1 and crop.x in (0, width - 1)))
        if not border_only:
            return super().render_lines(crop)
        key = (crop.x, crop.y, crop.width, crop.height, width, height,
               tuple(tuple(edge) for edge in self.styles.border),
               str(self.styles.background), str(self.styles.color),
               getattr(self, 'border_title', None))
        cached = self._border_base_cache.get(key)
        if cached is not None:
            return list(cached)
        strips = super().render_lines(crop)
        if len(self._border_base_cache) > 24:
            self._border_base_cache.clear()
        self._border_base_cache[key] = list(strips)
        return strips

    def render_lines(self, crop):
        strips = self._border_base_strips(crop)
        depth, quality, t, unicode, realm_id, feedback, focus_dim = self._ornament
        width, height = self.region.width, self.region.height
        # All four borders exist on these two panes. Respect any future borderless layout.
        if not self._has_paintable_border():
            return strips
        menu = (self.id or '').startswith(('home-', 'slot-', 'delete-', 'pause-', 'test-mode', 'newgame-'))
        active = self.has_class('selected') or self.has_focus or self.mouse_hover
        key = (self._ornament, width, height, active, menu)
        if key != self._ornament_cells_key:
            cells = ornament_cells(width, height, depth, quality, t, unicode,
                                   kind='menu' if menu else 'panel',
                                   active=active, realm_id=realm_id)
            if focus_dim < 1.0:
                # 先压暗再叠反馈：受创闪仍要在失焦侧看得见。
                cells = {position: (glyph, mix_hex(color, '#000000', 1.0 - focus_dim))
                         for position, (glyph, color) in cells.items()}
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
            # GlassButtonMixin replaces the foreground of every nonblank edge
            # glyph with its own glass edge color. Canonicalize that discarded
            # input so the invisible chase cannot invalidate both row caches.
            glass = self.has_class('glass-button')
            positions = tuple((x-crop.x, glyph, '#ffffff' if glass and glyph.strip() else color)
                               for x, glyph, color in self._ornament_cells_by_row.get(y, ())
                               if crop.x <= x < crop.right)
            if not positions:
                continue
            strips[row] = _ornament_row(tuple(strip), strip.cell_length, positions)
        return strips


class OrnamentPane(OrnamentBorderMixin, Vertical):
    pass
