"""Five full workspace titles with legacy symbols and column-aware spacing."""
from rich.cells import set_cell_size
from rich.text import Text

from ..i18n import get_language, tr
from ..data.icon_glyphs import game_icon
from .sidebar_workspaces import WORKSPACES


_SYMBOLS = {'actions': '✔', 'inventory': '▣', 'equipment': '▼', 'portents': '◈', 'tasks': '☷'}
_ASCII_SYMBOLS = {'actions': '>', 'inventory': '#', 'equipment': '^', 'portents': '@', 'tasks': '='}


def navigation_labels(width, mode='themed'):
    entries = []
    for key, label, english, default in WORKSPACES:
        title = english if get_language() == 'en' else tr(label)
        private = game_icon('nav.' + key) if mode != 'ascii' else None
        symbol = private or set_cell_size((_ASCII_SYMBOLS if mode == 'ascii' else _SYMBOLS)[key], 2)
        entries.append(('#nav-' + key, symbol, title))
    minimum = sum(Text(symbol + title).cell_len for _, symbol, title in entries)
    gap = ' ' if minimum + len(entries) <= width else ''
    for selector, symbol, title in entries:
        yield selector, Text(symbol + gap + title, no_wrap=True)


def navigation_widths(width, labels):
    """Give every complete label its width, then share all remaining columns."""
    minimum = [label.cell_len for _, label in labels]
    extra = max(0, int(width) - sum(minimum))
    each, remainder = divmod(extra, len(minimum))
    return [value + each + (index < remainder) for index, value in enumerate(minimum)]
