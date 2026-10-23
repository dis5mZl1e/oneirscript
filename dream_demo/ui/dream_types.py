"""Identity birth draft rendering and input, independent of world difficulty."""
from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from ..i18n import tr
from ..core.dream_types import budget_breakdown
from ..data.dream_types import IDENTITIES, IDENTITY_DESCRIPTIONS, APTITUDES, APTITUDE_NAMES, TIER_PRICES


def birth_rows():
    return [('identity', key) for key in IDENTITIES] + [('aptitude', key) for key in APTITUDES] + [('confirm', '')]


def birth_summary(app):
    values = budget_breakdown(app.newgame_dream_type)
    color = '#ed8d86' if values['remaining'] < 0 else '#91ddd3'
    text = Text(tr('—— 梦中身份与梦性 ——') + '\n', style='bold #e5c780')
    text.append(tr('梦性 {remaining}/{total} · 身份 {identity} · 加点 {upgrades} · 返还 {refund}/{nominal}',
                   remaining=values['remaining'], total=values['total'], identity=values['identity'],
                   upgrades=values['upgrades'], refund=values['refund'], nominal=values['nominal_refund']), style=color)
    text.append('\n' + tr('降档最多返还 3；身份与公共加点只共用梦性。'), style='#9aa8b8')
    return text


def birth_text(app, width):
    console = Console(width=max(20, width))
    text = Text()
    app._newgame_hit_rows = {}
    app._newgame_slider_hits = {}
    app._newgame_selected_row = 0
    physical = 0
    choice = app.newgame_dream_type
    rows = birth_rows()
    app.newgame_identity_cursor = max(0, min(app.newgame_identity_cursor, len(rows)-1))

    def append(line, index=None):
        nonlocal physical
        parts = line.wrap(console, max(20, width), overflow='fold')
        for part in parts:
            if index is not None:
                app._newgame_hit_rows[physical] = index
            text.append_text(part)
            text.append('\n')
            physical += 1

    append(Text(tr('必选一个完整身份；能力档位对所有身份相同。'), style='#a2b4c7'))
    for index, (kind, key) in enumerate(rows):
        focused = index == app.newgame_identity_cursor
        if focused:
            app._newgame_selected_row = physical
        style = 'bold #91ddd3' if focused else '#d0d7df'
        prefix = '▶ ' if focused else '  '
        if kind == 'identity':
            spec = IDENTITIES[key]
            selected = key == choice['identity']
            line = Text(prefix + ('◉ ' if selected else '○ ') + tr(spec['name']) + f"  {spec['cost']}", style=style)
            append(line, index)
        elif kind == 'aptitude':
            if key == APTITUDES[0]:
                append(Text(tr('—— 独立能力加点 ——'), style='bold #e5c780'))
                if focused:
                    app._newgame_selected_row = physical
            name = tr(APTITUDE_NAMES[key])
            line = Text(prefix + name + ' ' * max(1, 20-cell_len(name)), style=style)
            start = cell_len(line.plain) + 1
            app._newgame_slider_hits[key] = (physical, start)
            line.append('[', style='#60728e')
            tier = choice['aptitudes'][key]
            for level in range(5):
                line.append('●' if level == tier else '·', style='#e5c780' if level == tier else '#60728e')
                if level < 4:
                    line.append(' ')
            line.append(f'] {tier+1}/5 ({TIER_PRICES[tier]:+d})', style=style)
            append(line, index)
        else:
            append(Text(prefix + tr('继续：择碎片'), style='bold #e5c780'), index)
    return text


def birth_detail(app):
    if budget_breakdown(app.newgame_dream_type)['remaining'] < 0:
        return Text(tr('梦性不足：保留草稿，请降低能力或改选身份。'), style='bold #ed8d86')
    kind, key = birth_rows()[app.newgame_identity_cursor]
    if kind == 'identity':
        return Text(tr(IDENTITY_DESCRIPTIONS[key]), style='#a2b4c7')
    if kind == 'aptitude':
        tier = app.newgame_dream_type['aptitudes'][key]
        values = {'mind': (.8,.9,1,1.05,1.12), 'lucidity': (.8,.9,1,1.05,1.12),
                  'imagination': (.8,.9,1,1.08,1.16)}
        factor = values.get(key, (1.15,1.07,1,.95,.9))[tier]
        label = tr('出生上限') if key in values else tr('构想成本') if key == 'conceive' else tr('基础行动耗时')
        return Text(tr(APTITUDE_NAMES[key]) + f' · {label} ×{factor:g}\n'
                    + tr('降档的名义返还与实际返还分别显示；确认不必花完。'), style='#a2b4c7')
    return Text(tr('确认身份与加点后选择记忆；此时仍不创建存档。'), style='#a2b4c7')


def birth_mouse(app, index, x, y):
    app.newgame_identity_cursor = index
    kind, key = birth_rows()[index]
    if kind == 'identity':
        app.newgame_dream_type['identity'] = key
    elif kind == 'aptitude':
        row, start = app._newgame_slider_hits[key]
        if y == row and start <= x < start + 9:
            app.newgame_dream_type['aptitudes'][key] = min(4, (x-start+1)//2)
    else:
        app._confirm_newgame_options()


def birth_key(app, key):
    rows = birth_rows()
    if key in ('up', 'w', '8', 'num8', 'kp8'):
        app.newgame_identity_cursor = (app.newgame_identity_cursor-1) % len(rows)
    elif key in ('down', 's', '2', 'num2', 'kp2'):
        app.newgame_identity_cursor = (app.newgame_identity_cursor+1) % len(rows)
    else:
        kind, name = rows[app.newgame_identity_cursor]
        if kind == 'identity' and key in ('enter', 'return', 'space'):
            app.newgame_dream_type['identity'] = name
        elif kind == 'aptitude':
            value = app.newgame_dream_type['aptitudes'][name]
            if key in ('left', 'a', '4', 'num4', 'kp4'):
                value = max(0, value-1)
            elif key in ('right', 'd', '6', 'num6', 'kp6'):
                value = min(4, value+1)
            elif key in ('enter', 'return', 'space'):
                value = (value+1) % 5
            app.newgame_dream_type['aptitudes'][name] = value
        elif kind == 'confirm' and key in ('enter', 'return', 'space'):
            app._confirm_newgame_options()
        if key in ('enter', 'return'):
            app._mark_key_handled('enter')
    app.refresh_view()
