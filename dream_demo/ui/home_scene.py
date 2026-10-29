"""梦境之门：不参与布局和输入的主页字符背景。"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from rich.cells import cell_len, get_character_cell_size
from rich.segment import Segment
from rich.style import Style
from rich.text import Span, Text
from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from textual.strip import Strip
from textual.geometry import Region
from textual.visual import visualize
from textual.filter import ANSIToTruecolor

from .home_title import TITLE_WIDTH, home_title_text
from .deco import flow_color, mix_hex
from .home_particles import HomeParticles

BASE = "#101018"
FOG = tuple(f"#{16+i:02x}{16+i*2:02x}{24+i*2:02x}" for i in range(16))
# 门内暖光（2026-10-08 主页景深）：同一雾梯度向暗琥珀偏移，只用于门柱之间。
FOG_WARM = tuple(mix_hex(c, "#2e2114", 0.5) for c in FOG)
FOG_DEPTH = tuple(tuple(mix_hex(cold, warm, i/8) for i in range(9))
                  for cold, warm in zip(FOG, FOG_WARM))


def dream_title_text(title: str, elapsed: float = 1.0, t: float | None = None,
                     *, width: int = TITLE_WIDTH) -> Text:
    level = min(1.0, max(0.0, elapsed / 0.9))
    color = "#{:02x}{:02x}{:02x}".format(
        int(45 + 195 * level), int(43 + 181 * level), int(55 + 132 * level))
    if cell_len(title) > TITLE_WIDTH:
        clipped = Text(title)
        clipped.truncate(TITLE_WIDTH)
        title = clipped.plain
    # 标题只占三行；不随时间改变文字尺寸。
    result = home_title_text(title, t=t, width=width)
    start = result.plain.find(title)
    if start >= 0:
        result.stylize(f"bold {color}", start, start + len(title))
        if t is not None:
            # Keep the plaque's original chase; carry a gentler highlight through
            # the title itself without changing its three-row geometry.
            for index, char in enumerate(title):
                if char.strip():
                    highlight = mix_hex(color, flow_color(index * 5, t * .65), .38 * level)
                    result.stylize(f"bold {highlight}", start+index, start+index+1)
    return result


@lru_cache(maxsize=8192)
def _frame_style(foreground, background, base):
    # Match Rich's _Styled wrapper, including its empty link metadata.
    return base + Style(color=foreground, bgcolor=background, meta={})


@lru_cache(maxsize=8)
def _fog_palette(width: int, height: int, step: int):
    """The fog already advances at 4Hz; reuse its palette between those ticks."""
    xs, ys = np.meshgrid(np.arange(width), np.arange(height))
    pixel_x = xs // 2
    pixel_time = step / 4
    grain = np.array([[0, 2], [3, 1]])[ys % 2, pixel_x % 2] / 4 - .375
    fog = (np.sin(pixel_x * 0.24 + ys * 0.25 + pixel_time * 0.35)
           + np.sin(pixel_x * 0.086 - ys * 0.39 - pixel_time * 0.21) + 2) * 2
    cx = (width - 1) / 2
    compact = width <= 80 or height < 22
    half = min((width - 7) / 2, 35 if compact else max(39, width * .43))
    arch_h = min(4, max(1, height // 6))
    distance = np.abs(pixel_x * 2 - cx) / max(1, half)
    aperture = np.maximum(0, 1 - distance**2)
    depth = np.maximum(0, 1 - np.abs(ys - height * .55) / max(1, height * .7))
    levels = np.clip((np.floor((fog + aperture * depth * 3 + grain) / 3) * 3).astype(np.int8), 0, 15)
    warmth = np.clip((aperture * depth * np.clip((ys - arch_h) / max(1, height * .25), 0, 1) * 2).astype(np.int8) * 4, 0, 8)
    return tuple(tuple(FOG_DEPTH[int(levels[y, x])][int(warmth[y, x])]
                       for x in range(width)) for y in range(height))


@lru_cache(maxsize=8)
def _fog_frame(width, height, step, base):
    palette = _fog_palette(width, height, step)
    styles = {color: _frame_style('#52646d', color, base)
              for color in {color for row in palette for color in row}}
    # These pairs are immutable. Thousands of identical tracked tuples per fog
    # tick otherwise remain alive in the frame cache and force costly GC scans.
    blank_cells = {color: (' ', style) for color, style in styles.items()}
    strips, rows = [], []
    for colors in palette:
        segments, cells = [], []
        start, last = 0, None
        for x, background in enumerate(colors):
            cells.append(blank_cells[background])
            if last is not None and background != last:
                segments.append(Segment(' ' * (x - start), styles[last]))
                start = x
            last = background
        segments.append(Segment(' ' * (width - start), styles[last]))
        strips.append(Strip(segments, width))
        rows.append(tuple(cells))
    return tuple(strips), tuple(rows)


@lru_cache(maxsize=8192)
def _scene_span_style(style):
    return f'{style.color.get_truecolor().hex} on {style.bgcolor.get_truecolor().hex}'


def _scene_text(strips):
    text_parts, spans, offset = [], [], 0
    for y, strip in enumerate(strips):
        if y:
            text_parts.append('\n')
            offset += 1
        for segment in strip:
            text_parts.append(segment.text)
            end = offset + len(segment.text)
            spans.append(Span(offset, end, _scene_span_style(segment.style)))
            offset = end
    return Text(''.join(text_parts), spans=spans)


class _SceneRenderable:
    """Keep the standard Rich fallback available without building unused spans."""

    def __init__(self, strips):
        self.strips = strips

    def __rich_console__(self, console, options):
        yield _scene_text(self.strips)


def home_scene_text(width: int, height: int, t: float, quality: str, particles=None) -> Text:
    return _home_scene_frame(width, height, t, quality, particles)[0]


def _home_scene_frame(width: int, height: int, t: float, quality: str, particles=None,
                      base: Style = Style(), *, materialize_text=True):
    """确定性背景；门柱位于菜单两侧，中央留给稳定的导航。"""
    width, height = max(1, width), max(1, height)
    if quality == 'off':
        t = 0.0
    compact = width <= 80 or height < 22
    chars = [[" "] * width for _ in range(height)]
    foreground = {}
    cx = (width - 1) / 2
    half = min((width - 7) / 2, 35 if compact else max(39, width * .43))
    top = 1
    arch_h = min(4, max(1, height // 6))
    backgrounds = _fog_palette(width, height, math.floor(t * 4))
    for x in range(width):
        d = abs(x - cx) / max(1, half)
        if d <= 1:
            y = top + round(arch_h * (1 - math.sqrt(max(0, 1 - d*d))))
            if y < height:
                chars[y][x] = "─" if d < .55 else "╱" if x < cx else "╲"
                foreground[(x, y)] = "#b89d68" if quality == "off" else mix_hex("#b89d68", flow_color(x, t), .65)
                if not compact and y+2 < height:
                    chars[y+2][x] = '─' if d < .55 else '╱' if x < cx else '╲'
                    foreground[(x, y+2)] = '#504c42'
    for y in range(top + arch_h + 1, max(top + arch_h + 1, height - 1)):
        for x in (round(cx - half), round(cx + half)):
            if 0 <= x < width:
                chars[y][x] = "│"
                phase = y if x < cx else width + height - y
                foreground[(x, y)] = "#766a52" if quality == "off" else mix_hex("#b89d68", flow_color(phase, t), .7)
                if y % 5 == 0:
                    chars[y][x] = '╪'
                    foreground[(x, y)] = mix_hex('#b89d68', flow_color(phase, t), .35)
        if not compact and y % 3 == 0:
            for x in (round(cx - half - 2), round(cx + half + 2)):
                if 0 <= x < width:
                    chars[y][x] = ":"
                    foreground[(x, y)] = "#394650"
    stars = (4 if compact else 8) if quality == "low" else (8 if compact else 22)
    for i in range(stars):
        x = (i * 37 + 7) % width
        # 近景粒子移动稍快、更亮；远景稍慢、更暗（2026-10-08 景深分层）。
        speed = 0.10 if i % 2 == 0 else 0.24
        y = (i * 13 + 2 + int(t * speed)) % height
        if abs(x - cx) < 31 and y >= 3:
            continue
        chars[y][x] = "." if i % 4 else "+"
        glow = int((58 if i % 2 == 0 else 75) + 35 * math.sin(t * 0.8 + i))
        foreground[(x, y)] = f"#{glow:02x}{glow+8:02x}{glow+12:02x}"
    # 内层刻纹（柱内侧）与外门廓（柱外侧短刻柱）：非紧凑布局才画。
    inner_top = top + arch_h + 1
    if not compact:
        for y in range(inner_top, max(inner_top, height - 2)):
            if y % 3 == 0:
                for x in (round(cx - half) + 2, round(cx + half) - 2):
                    if 0 <= x < width and not chars[y][x].strip():
                        chars[y][x] = "·"
                        foreground[(x, y)] = "#55482e"
            if y % 2 == 0:
                for x in (round(cx - half) - 2, round(cx + half) + 2):
                    if 0 <= x < width and y < height - 2 and not chars[y][x].strip():
                        chars[y][x] = ":"
                        foreground[(x, y)] = "#2c3140"
    # 穿门星尘：只在门内缓慢横飘（「·」不进星点计数口径）。
    dust = (2 if quality == "off" else (3 if quality == "low" else 6)) if particles is None else 0
    span = max(1, int(half) - 2)
    rows = max(1, height - inner_top - 1)
    for i in range(dust):
        x = round(cx) - span + (i * 13 + int(t * (2.0 + (i % 3)))) % (2 * span)
        y = inner_top + (i * 5 + int(t * (1.2 + (i % 2)))) % rows
        if abs(x - cx) < half - 1 and inner_top <= y < height - 1 and not chars[y][x].strip():
            chars[y][x] = "·"
            foreground[(x, y)] = "#8a7a52"
    for (x, y), (glyph, color) in (particles or {}).items():
        if 0 <= x < width and 0 <= y < height and not chars[y][x].strip():
            chars[y][x] = glyph
            foreground[(x, y)] = color
    # A small reflection at the foot of the portal; never a solid light block.
    if height >= 18:
        for row in range(height-3, height-1):
            spread = max(1, int(half*.7) - (row-height+3)*4)
            for x in range(max(0, round(cx)-spread), min(width, round(cx)+spread+1)):
                if not chars[row][x].strip() and (x+row) % 5 == 0:
                    chars[row][x] = '─' if row == height-3 else '·'
                    foreground[(x, row)] = '#534833'
    # Fog geometry is unchanged between its existing 4Hz ticks. Overlay only
    # the sparse pillar/star/particle cells instead of rebuilding the full grid
    # and its Rich spans on every 20Hz decoration frame.
    fog_strips, fog_rows = _fog_frame(width, height, math.floor(t * 4), base)
    by_row = {}
    for (x, y), color in foreground.items():
        by_row.setdefault(y, {})[x] = color
    strips, cell_rows = [], []
    for y in range(height):
        changes = by_row.get(y, {})
        if changes:
            cells = list(fog_rows[y])
            for x, color in changes.items():
                cells[x] = (chars[y][x], _frame_style(color, backgrounds[y][x], base))
            cuts = sorted({width, *(x for x in changes if x), *(x + 1 for x in changes)})
            segments, start = [], 0
            for end, part in zip(cuts, Segment.divide(tuple(fog_strips[y]), cuts)):
                if start in changes:
                    glyph, style = cells[start]
                    segments.append(Segment(glyph, style))
                else:
                    segments.extend(part)
                start = end
            strip = Strip(list(Segment.simplify(segments)), width)
            cells = tuple(cells)
        else:
            strip, cells = fog_strips[y], fog_rows[y]
        strips.append(strip)
        cell_rows.append(cells)
    strips = tuple(strips)
    content = _scene_text(strips) if materialize_text else _SceneRenderable(strips)
    return content, strips, tuple(cell_rows)


@lru_cache(maxsize=512)
def _backdrop_cells(segments):
    return tuple((char, segment.style) for segment in segments for char in segment.text)


@lru_cache(maxsize=8192)
def _backdrop_style(foreground, background):
    return (foreground or Style()) + Style(bgcolor=background)


@lru_cache(maxsize=512)
def _blend_backdrop(source, background, length):
    """Blend a fixed row in one pass; avoid one Strip.crop per character."""
    plain = ''.join(segment.text for segment in source if not segment.control)
    first = cell_len(plain) - cell_len(plain.lstrip(' '))
    last = cell_len(plain.rstrip(' '))
    cells = _backdrop_cells(background)
    result = []
    column = 0
    previous_bg = BASE
    run, run_style = '', None
    for segment in source:
        if segment.control:
            if run:
                result.append(Segment(run, run_style))
                run = ''
            result.append(segment)
            continue
        for char in segment.text:
            width = get_character_cell_size(char)
            sample = cells[column] if column < len(cells) else (' ', None)
            if char == ' ' and not first <= column < last:
                glyph, style = sample
            else:
                if width:
                    previous_bg = sample[1].bgcolor if sample[1] else BASE
                glyph, style = char, _backdrop_style(segment.style, previous_bg)
            if run and style != run_style:
                result.append(Segment(run, run_style))
                run = ''
            run += glyph
            run_style = style
            column += width
    if run:
        result.append(Segment(run, run_style))
    return Strip(result, length)


def _opaque_scene_lines(widget, crop):
    styles = widget.styles
    if (styles.gutter or any(edge[0] for edge in styles.outline)
            or styles.tint.a or styles.text_opacity != 1.0
            or widget.opacity != 1.0 or styles.has_rule('hatch')
            or widget.content_size != widget.region.size):
        return None
    strips = [widget.render_line(y) for y in crop.line_range]
    width = widget.content_size.width
    # Partial text rows still require Textual's padding/background handling.
    if any(strip.cell_length != width or any(
            segment.style is None or segment.style.bgcolor is None for segment in strip)
           for strip in strips):
        return None
    filters = [filter for filter in widget.app._filters if filter.enabled]
    if filters:
        background = widget._opacity_background_colors[1]
        for filter in filters:
            if type(filter) is ANSIToTruecolor and all(
                    not segment.control and ((style := segment.style) is None or (
                        (style.color is None or not style.color.is_system_defined)
                        and (style.bgcolor is None or not style.bgcolor.is_system_defined)))
                    for strip in strips for segment in strip):
                continue
            strips = [strip.apply_filter(filter, background) for strip in strips]
    strips = [strip.crop(crop.x, crop.right) for strip in strips]
    if widget.auto_links:
        hover = widget.hover_style
        if hover._link_id and hover._meta and '@click' in hover.meta:
            link_style = widget.link_style_hover
            if link_style:
                strips = [strip.style_links(hover.link_id, link_style) for strip in strips]
    return strips


class DreamBackdropMixin:
    """Textual 的透明底仍取祖先底色；显式合成兄弟门景的空白列。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_class("dream-backdrop")

    def refresh_backdrop(self, *regions: Region) -> None:
        # A sibling's new background invalidates the composite, not our text.
        # Keep any genuine content/style dirtiness already queued by Textual.
        foreground_dirty = self._dirty_regions.copy()
        self.refresh(*regions)
        self._dirty_regions.clear()
        self._dirty_regions.update(foreground_dirty)

    def render_lines(self, crop: Region) -> list[Strip]:
        scene = self.app.query_one(HomeScene)
        if scene.display and scene.size.width:
            strips = _opaque_scene_lines(self, crop)
            if strips is not None:
                return strips
        return super().render_lines(crop)

    def render_line(self, y: int) -> Strip:
        foreground = super().render_line(y)
        scene = self.app.query_one(HomeScene)
        if not scene.display or not scene.size.width:
            return foreground
        x = self.content_region.x - scene.content_region.x
        sy = self.content_region.y - scene.content_region.y + y
        if sy < 0 or sy >= scene.size.height:
            return foreground
        backdrop = scene.render_line(sy).crop(x, x + self.content_size.width)
        plain = foreground.text
        if not plain.strip(" "):
            return backdrop.adjust_cell_length(foreground.cell_length)
        # Spaces inside the plaque belong to its text spacing, not the scenery.
        return _blend_backdrop(tuple(foreground), tuple(backdrop), foreground.cell_length)


class DreamStatic(DreamBackdropMixin, Static):
    pass


class FixedFrameStatic(Static):
    """Animation content whose dimensions are entirely defined by CSS."""

    def update(self, content="") -> None:
        # Static.update always requests layout, even for a fixed-size frame.
        # Keep its content/visual contract, but only invalidate paint here.
        self._content = content
        self._visual = visualize(self, content)
        self.refresh()


class DreamTitle(DreamBackdropMixin, FixedFrameStatic):
    pass


class DreamVertical(DreamBackdropMixin, Vertical):
    pass


class DreamHorizontal(DreamBackdropMixin, Horizontal):
    pass


class HomeScene(FixedFrameStatic):
    DEFAULT_CSS = """
    HomeScene {
        position: absolute;
        offset: 0 0;
        width: 100%; height: 100%;
        layer: dream;
        background: #101018;
        overflow: hidden;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(disabled=True, **kwargs)
        self._scene_key = None
        self.frames_drawn = 0
        self.particles = HomeParticles()
        self._background_rows = {}
        self._scene_lines_key = None
        self._scene_lines = ()
        self._scene_cell_rows = ()
        self._base_style_signature = None
        self._base_style = None

    @property
    def rich_style(self) -> Style:
        # Textual resolves inherited colors/opacity afresh on every access.
        # All row consumers share that result until a style source changes.
        signature = tuple((id(node.styles), id(node.styles.base), id(node.styles.inline),
                           node.styles._cache_key) for node in self.ancestors_with_self)
        if signature != getattr(self, '_base_style_signature', None):
            self._base_style = super().rich_style
            self._base_style_signature = signature
        return self._base_style

    def render_line(self, y: int) -> Strip:
        # Several overlapping backdrop consumers can ask for the same frame
        # after independent style-cache invalidations. Content/size/style, not
        # those paint requests, determine whether Rich must lay out its text.
        key = (self._scene_key, id(self._content), self.size, self.rich_style)
        if key != self._scene_lines_key:
            self._render_content()
            self._scene_lines = tuple(self._render_cache.lines)
            self._scene_lines_key = key
        if 0 <= y < len(self._scene_lines):
            self._dirty_regions.clear()
            return self._scene_lines[y]
        return Strip.blank(self.size.width, self.rich_style)

    def render_lines(self, crop: Region) -> list[Strip]:
        # Every generated cell already has an opaque foreground/background.
        # Generic CSS adds the same inner background to every Segment again,
        # allocating thousands of identical Style/Segment pairs each frame.
        if isinstance(self._content, _SceneRenderable):
            strips = _opaque_scene_lines(self, crop)
            if strips is not None:
                return strips
        return super().render_lines(crop)

    def background_color_row(self, y: int) -> tuple[str, ...]:
        """Share a rendered backdrop row across glass buttons in this frame."""
        strip = self.render_line(y)
        cached = self._background_rows.get(y)
        if cached is not None and cached[0] is strip:
            return cached[1]
        colors = []
        for segment in strip:
            color = segment.style.bgcolor if segment.style else None
            color = color.get_truecolor().hex if color else BASE
            colors.extend([color] * segment.cell_length)
        result = tuple(colors)
        self._background_rows[y] = (strip, result)
        return result

    def paint(self, t: float, quality: str) -> None:
        width, height = self.size
        if not width or not height:
            return
        step = 0 if quality == "off" else int(t * (10 if quality == "low" else 20))
        key = (width, height, quality, step)
        if key == self._scene_key:
            return
        self._scene_key = key
        self.frames_drawn += 1
        self._background_rows.clear()
        elapsed = step / (10 if quality == "low" else 20)
        dust = self.particles.frame(width, height, elapsed, quality)
        previous = self._scene_cell_rows
        base = self.rich_style
        self._content, self._scene_lines, rows = _home_scene_frame(
            width, height, elapsed, quality, dust, base, materialize_text=False)
        self._visual = visualize(self, self._content)
        # Widget._render caches its Visual independently of Static._visual.
        # Invalidate it before comparing rows; refresh() comes after the diff.
        self._layout_cache.clear()
        self._scene_lines_key = (self._scene_key, id(self._content), self.size, base)
        regions = []
        if len(previous) != len(rows) or any(len(row) != width for row in rows):
            regions = [Region(0, 0, width, height)]
        else:
            for y, (old, new) in enumerate(zip(previous, rows)):
                if old is new:
                    continue
                if len(old) != width:
                    regions.append(Region(0, y, width, 1))
                    continue
                start = None
                for x, (before, after) in enumerate(zip(old, new)):
                    if before != after and start is None:
                        start = x
                    elif before == after and start is not None:
                        regions.append(Region(start, y, x - start, 1))
                        start = None
                if start is not None:
                    regions.append(Region(start, y, width - start, 1))
        self._scene_cell_rows = rows
        if not regions:
            return
        # Fog changes can affect most cells. Bound region bookkeeping in that
        # case; the 20Hz pillar/particle subframes stay local between fog ticks.
        if len(regions) > 256 or sum(region.area for region in regions) > width * height / 3:
            regions = [Region(0, 0, width, height)]
        self.refresh(*regions)
        origin = self.content_region.offset
        for widget in self.app.query(".dream-backdrop"):
            if not widget.display or not widget.is_on_screen:
                continue
            offset = widget.content_region.offset
            local = [clipped.translate((-offset.x, -offset.y)) for region in regions
                     if (clipped := region.translate(origin).intersection(widget.region))]
            if local:
                if isinstance(widget, DreamBackdropMixin):
                    widget.refresh_backdrop(*local)
                else:
                    widget.refresh(*local)

    def on_resize(self) -> None:
        # off 档没有定时器：首个布局完成或窗口缩放也必须补画静态门景。
        self.app._home_tick()
