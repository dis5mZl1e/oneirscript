"""Player-facing rules for the existing tamper editor."""
from rich.text import Text
from ..i18n import tr


def tamper_info_text():
    text = Text(tr('篡改 · 玩法说明') + '\n', style='bold #c9a0ff')
    from ..data.tamper_guide import TAMPER_SECTIONS
    sections = TAMPER_SECTIONS
    for title, body in sections:
        text.append('\n' + tr(title) + '\n', style='bold #a8bdca')
        text.append(tr(body) + '\n', style='#ddd2bf')
    return text
