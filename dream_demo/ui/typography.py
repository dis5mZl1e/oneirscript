"""Desktop font roles, applied after Rich markup without changing hit regions.

The bundled terminal reserves SGR italic for upright sans. Ordinary terminals
never enable this adapter. The existing wide-glyph compositor calls it only
after deciding clipping and transparent-overlay ownership.
"""
from __future__ import annotations

from functools import lru_cache
from collections import OrderedDict

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widgets import Button

from ..env_compat import get as env_get


def font_role(widget) -> str:
    nodes = [widget, *widget.ancestors]
    ids = {node.id for node in nodes}
    if 'home' in ids:
        return 'serif'
    if 'side-pane' in ids:
        return 'sans'
    identifier = widget.id or ''
    if (isinstance(widget, Button) or identifier.endswith('-title')
            or type(widget).__name__ == 'MapModeOption'
            or identifier.startswith(('board-tool-', 'pause-option-'))):
        return 'sans'
    if identifier in {
        'map-overlay', 'tamper-overlay', 'self-audit-body', 'layer-info-body',
        'signal-detail-text', 'controls-help-text', 'board-editor-side',
        'board-editor-grammar', 'board-editor-status', 'board-editor-effects',
        'board-editor-inspect', 'codex-list', 'codex-detail', 'settings-list',
    } or identifier.startswith('setting-row-'):
        return 'headings'
    return 'serif'


@lru_cache(maxsize=8192)
def _font_style(style: Style | None, sans: bool) -> Style:
    return (style or Style()) + Style(italic=sans)


_strip_cache = OrderedDict()


def style_strip(strip: Strip, role: str) -> Strip:
    key = (id(strip), role)
    cached = _strip_cache.get(key)
    if cached is not None and cached[0] is strip:
        return cached[1]
    if role == 'serif' and not any(segment.style and segment.style.italic for segment in strip):
        return strip
    result = Strip((Segment(segment.text,
                          _font_style(segment.style, role == 'sans' or
                                      (role == 'headings' and bool(segment.style and segment.style.bold))),
                          segment.control)
                  for segment in strip), strip.cell_length)
    _strip_cache[key] = (strip, result)
    if len(_strip_cache) > 4096:
        _strip_cache.popitem(last=False)
    return result


def widget_strips(widget, crop):
    strips = widget.render_lines(crop)
    if env_get('UI_FONTS') != '1':
        return strips
    role = font_role(widget)
    return [style_strip(strip, role) for strip in strips]
