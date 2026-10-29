"""Native, equal-size terminal text with safe emphasis for icon glyphs.

Panel hierarchy comes from Rich colors, background bands and emphasis. Never
rasterize UI text: the terminal owns font metrics, shaping and zoom changes.
"""
from __future__ import annotations

from functools import lru_cache
import unicodedata

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip

_ICON_STYLE = Style(bold=False, italic=False)


def _icon(char):
    return (unicodedata.category(char) in ('So', 'Co')
            or 0x1F000 <= ord(char) <= 0x1FAFF
            or char in '\u203c\u2049\u2139\u3030\u303d'
            or '\u2194' <= char <= '\u2199' or '\u21a9' <= char <= '\u21aa'
            or char in '\u200d\ufe0e\ufe0f\u20e3')


def native_segments(segments):
    """Remove only bold/italic on icons, preserving text, colors and metadata.

    Look across Rich span boundaries for keycaps; their digit/#/* base must
    retain the same unstyled face as its variation and enclosing mark.
    """
    segments = tuple(segments)
    chars = ''.join(segment.text for segment in segments if not segment.control)
    offset = 0
    for segment in segments:
        if segment.control:
            yield segment
            continue
        style = segment.style
        if style is None or not (style.bold or style.italic):
            offset += len(segment.text)
            yield segment
            continue
        run, previous = '', None
        for char in segment.text:
            keycap = char in '0123456789#*' and '\u20e3' in chars[offset+1:offset+3]
            safe = style + _ICON_STYLE if _icon(char) or keycap else style
            if run and safe != previous:
                yield Segment(run, previous)
                run = ''
            run += char
            previous = safe
            offset += 1
        if run:
            yield Segment(run, previous)


@lru_cache(maxsize=4096)
def _safe_segments(segments):
    return tuple(native_segments(segments))


def _native_strip(strip):
    # The icon pass only removes emphasis. Animated scenery has none; retaining
    # its constantly changing rows in the icon cache prolongs many Segment and
    # Style lifetimes and makes full garbage collections unnecessarily large.
    if not any(segment.style is not None and (segment.style.bold or segment.style.italic)
               for segment in strip):
        return strip
    segments = tuple(strip)
    safe = _safe_segments(segments)
    return strip if safe == segments else Strip(safe, strip.cell_length)


def native_update(update):
    """Copy compositor updates without changing cell budgets or hit geometry."""
    from textual._compositor import ChopsUpdate, InlineUpdate, LayoutUpdate
    if isinstance(update, LayoutUpdate):
        return LayoutUpdate([_native_strip(line) for line in update.strips], update.region)
    if isinstance(update, InlineUpdate):
        return InlineUpdate([_native_strip(line) for line in update.strips], update.clear)
    if isinstance(update, ChopsUpdate):
        return ChopsUpdate([{x: _native_strip(line) if line is not None else None
                             for x, line in row.items()} for row in update.chops],
                           update.spans, update.chop_ends)
    return update


def panel_packets(app, screen, update):
    """Compatibility for probes: panels never emit image protocol packets."""
    return []
