"""Six full workspace titles with legacy symbols and column-aware spacing."""
from rich.cells import set_cell_size
from rich.text import Text

from ..i18n import get_language, tr
from ..data.icon_glyphs import game_icon
from .sidebar_workspaces import WORKSPACES


_SYMBOLS = {'actions': '✔', 'inventory': '▣', 'equipment': '▼', 'portents': '◈',
            'environment': '≋', 'tasks': '☷'}
_ASCII_SYMBOLS = {'actions': '>', 'inventory': '#', 'equipment': '^', 'portents': '@',
                  'environment': '~', 'tasks': '='}


def navigation_labels(width, mode='themed', terse=False):
    """六个工作区页签。

    `terse=True`（少字模式）时只保留符号、隐藏标题；普通模式仍是
    「符号 + 完整中/英文标题」。宽度分配逻辑两种模式共用。
    """
    # 注意：这里保留逐页签调用模块级 game_icon（不做批内 hoist）。
    # tests/test_rendering_world_ui.py（本任务 scope 之外）正是用
    # patch('dream_demo.ui.navigation_labels.game_icon') 注入私有图标的；
    # 把判定改到 symbols 内部会让那条测试失去注入点。六个页签每次只读六次
    # 环境变量（非逐格热路径，实测 0 次/动作），不值得为此改公共接缝。
    entries = []
    for key, label, english, default in WORKSPACES:
        title = english if get_language() == 'en' else tr(label)
        private = game_icon('nav.' + key) if mode != 'ascii' else None
        symbol = private or set_cell_size((_ASCII_SYMBOLS if mode == 'ascii' else _SYMBOLS)[key], 2)
        entries.append(('#nav-' + key, symbol, '' if terse else title))
    # 六区后窄栏可能连「符号+标题」的最小宽度都放不下（80 列紧凑右栏 32 列，
    # 六个 2 格符号+双字标题要 36 列）。标题一个不许删：先去间隔，仍溢出时把
    # 双格符号压成 1 格 ASCII 符号——只压缩装饰，不压缩信息。
    if sum(Text(symbol + title).cell_len for _, symbol, title in entries) > width:
        entries = [(selector, set_cell_size(_ASCII_SYMBOLS[row[0]], 1), title)
                   for (selector, _, title), row in zip(entries, WORKSPACES)]
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
