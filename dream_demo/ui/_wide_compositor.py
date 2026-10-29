"""仅在实际前景控件交界处分行，避免隐藏控件的边界切掉双宽汉字。"""
from textual._compositor import Compositor
from textual.geometry import Region
from bisect import bisect_left, bisect_right
from rich.cells import get_character_cell_size
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from .typography import widget_strips


def _ink_columns(strip):
    """Return terminal-column ranges containing text, not transparent spaces."""
    column = 0
    start = None
    for segment in strip:
        for char in segment.text:
            width = get_character_cell_size(char)
            if width <= 0:
                continue
            if char.isspace():
                if start is not None:
                    yield start, column
                    start = None
            elif start is None:
                start = column
            column += width
    if start is not None:
        yield start, column


class _WideCompositor(Compositor):
    def _overlay_background(self, fragment, x, y):
        """Keep the map's background color under each overlaid character."""
        target = next(((w, r) for w, (r, _clip) in self.visible_widgets.items()
                       if getattr(w, 'id', None) == 'map'), None)
        if target is None:
            return fragment
        widget, region = target
        if not region.contains(x, y):
            return fragment
        lines = widget.render_lines(Region(x-region.x, y-region.y, fragment.cell_length, 1))
        if not lines:
            return fragment
        base = lines[0]
        segments = []
        offset = 0
        for segment in fragment:
            for char in segment.text:
                width = get_character_cell_size(char)
                sample = next(iter(base.crop(offset, offset + 1)), None)
                bg = sample.style.bgcolor if sample is not None and sample.style else None
                style = (segment.style or Style()) + Style(bgcolor=bg) if bg else segment.style
                segments.append(Segment(char, style, segment.control))
                offset += width
        return Strip(segments, fragment.cell_length)

    def _overlay_above_map(self, overlay, x, y):
        """The event text belongs above the map and below opaque panels."""
        seen = False
        for widget, _region in self.get_widgets_at(x, y):
            if widget is overlay:
                seen = True
                continue
            if not seen:
                continue
            if (getattr(widget, 'transparent_text_overlay', False)
                    or getattr(widget, 'id', None) == 'map-hints'):
                continue
            return getattr(widget, 'id', None) == 'map'
        return False

    def render_partial_update(self):
        update = super().render_partial_update()
        if update is None:
            return None
        # 脏区自身也可能仅覆盖双宽字的一半。把同一前景片段作为原子更新，
        # 不跨真实遮挡边界；合并重叠片段避免一行反复输出。
        spans = []
        for y, x1, x2 in update.spans:
            cuts = self.cuts[y]
            start = cuts[max(0, bisect_right(cuts, x1)-1)]
            end = cuts[min(len(cuts)-1, bisect_left(cuts, x2))]
            if spans and spans[-1][0] == y and start <= spans[-1][2]:
                spans[-1] = (y, spans[-1][1], max(end, spans[-1][2]))
            else:
                spans.append((y, start, end))
        update.spans = spans
        return update

    @property
    def cuts(self):
        if self._cuts is not None:
            return self._cuts
        width, height = self.size
        owners = [[None]*width for _ in range(height)]
        bounds = self.size.region
        # visible_widgets 与 _get_renders 都按从前到后排列，先到者占有像素。
        for widget, (region, clip) in self.visible_widgets.items():
            original = region
            region = region.intersection(clip).intersection(bounds)
            transparent = getattr(widget, 'transparent_text_overlay', False)
            for y in region.line_range:
                row = owners[y]
                if transparent:
                    lines = widget.render_lines(Region(region.x-original.x, y-original.y,
                                                       region.width, 1))
                    runs = _ink_columns(lines[0]) if lines else ()
                else:
                    runs = ((0, region.width),)
                for start, end in runs:
                    for x in range(region.x + start, min(region.x + end, region.right)):
                        if (row[x] is None and
                                (not transparent or self._overlay_above_map(widget, x, y))):
                            row[x] = widget
        self._wide_owners = owners
        self._cuts = [[0] + [x for x in range(1, width) if row[x] is not row[x-1]]
                      + [width] for row in owners]
        return self._cuts

    def _render_chops(self, crop, is_rendered_line):
        cuts = self.cuts
        chops = [dict.fromkeys(row[:-1]) for row in cuts]
        bounds = self.size.region
        crop = bounds if crop is None else crop.intersection(bounds)
        jobs = {}
        for y in crop.line_range:
            if not is_rendered_line(y):
                continue
            owners = self._wide_owners[y]
            for start, end in zip(cuts[y], cuts[y][1:]):
                if end <= crop.x or start >= crop.right:
                    continue
                widget = owners[start]
                if widget is not None:
                    jobs.setdefault(widget, {}).setdefault(y, []).append((start, end))
        for widget, lines in jobs.items():
            region, clip = self.visible_widgets[widget]
            visible = region.intersection(clip).intersection(bounds)
            transparent = getattr(widget, 'transparent_text_overlay', False)
            rows = list(lines)
            index = 0
            while index < len(rows):
                stop = index + 1
                while stop < len(rows) and rows[stop] == rows[stop - 1] + 1:
                    stop += 1
                top, bottom = rows[index], rows[stop - 1] + 1
                strips = widget_strips(widget, Region(visible.x - region.x, top - region.y,
                                                    visible.width, bottom - top))
                for y, strip in zip(range(top, bottom), strips):
                    for start, end in lines[y]:
                        # Keep the whole ownership span, including both cells of a wide glyph.
                        fragment = strip.crop(start - visible.x, end - visible.x)
                        if not transparent or any(segment.text.strip() for segment in fragment):
                            chops[y][start] = (self._overlay_background(fragment, start, y)
                                               if transparent else fragment)
                index = stop
        return chops
