"""A short, read-only introduction, separate from the playable tutorial."""
from rich.style import Style
from rich.text import Text

from ..i18n import tr


from ..data.game_intro import INTRO_PAGES


def intro_text(step: int) -> Text:
    step = max(0, min(len(INTRO_PAGES) - 1, step))
    title, body = INTRO_PAGES[step]
    text = Text(tr('入梦介绍') + f'  {step + 1} / {len(INTRO_PAGES)}\n', style='#9ab7ca')
    text.append('\n' + tr(title) + '\n\n', style='bold #e2c49a')
    text.append(tr(body) + '\n\n', style='#ddd2bf')
    text.append(tr('之后可在「设置 → 数据 → 入梦介绍」重新查看。') + '\n\n', style='#98a4ad')
    if step:
        text.append(tr('[上一步]'), Style(color='#a8bdca', bold=True, meta={'game_intro': 'previous'}))
        text.append('    ')
    text.append(tr('[开始探索]' if step == len(INTRO_PAGES)-1 else '[下一步]'),
                Style(color='#e2c49a', bold=True, meta={'game_intro': 'next'}))
    text.append('    ')
    text.append(tr('[关闭]'), Style(color='#a8bdca', meta={'game_intro': 'close'}))
    text.append('\n\n' + tr('← → 翻页 · Enter 继续 · Esc 关闭'), style='#98a4ad')
    return text
