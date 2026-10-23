"""Scrollable dream tuning, with a pinned difficulty meter and mouse hit map."""
from rich.cells import cell_len
from rich.console import Console
from rich.text import Text
from textual.widgets import Static
from ..i18n import tr
from ..core.run_options import (SLIDER_DEFS, TOGGLE_DEFS, option_rows,
    difficulty_score, difficulty_band, difficulty_bounds)


class NewGameOptionsView(Static):
    can_focus = True

    def on_resize(self, event):
        # A newly opened draft changes virtual height after the app's first
        # refresh callback. Scroll again once this widget has its real size.
        self.app._refresh_birth_layout()
        self.call_after_refresh(self.app._scroll_newgame_cursor)

    def on_mouse_down(self, event):
        if event.button != 1:
            return
        app = self.app
        local_x = event.offset.x - self.styles.padding.left
        local_y = event.offset.y - self.styles.padding.top
        index = app._newgame_hit_rows.get(local_y)
        if index is None:
            return
        if app.newgame_phase == 'identity':
            from .dream_types import birth_mouse
            birth_mouse(app, index, local_x, local_y)
        elif app.newgame_phase == 'fragment':
            app.newgame_fragment_cursor = index
        else:
            app.newgame_cursor = index
            kind, key = option_rows()[index]
            if kind == 'toggle':
                app._toggle_newgame_option(key)
            elif kind == 'slider':
                row, start = app._newgame_slider_hits[key]
                if local_y == row and start <= local_x < start + 9:
                    app.newgame_sliders[key] = min(4, (local_x - start + 1) // 2)
            elif kind == 'confirm':
                app._confirm_newgame_options()
                event.stop()
                return
        app.refresh_view()
        event.stop()


def summary_text(app):
    if app.newgame_phase == 'identity':
        from .dream_types import birth_summary
        return birth_summary(app)
    selection = app._newgame_selection()
    score = difficulty_score(selection)
    low, high = difficulty_bounds()
    filled = round((score-low) / max(1, high-low) * 20)
    band = difficulty_band(score)
    color = '#efb76b' if score > 3 else '#83c9c6' if score >= -2 else '#91c59b'
    text = Text(tr('—— 织梦调律 ——') + '\n', style='bold #e5c780')
    text.append(tr('难度') + '  ', style='bold white')
    text.append('━' * filled, style=color)
    text.append('─' * (20-filled), style='#47546e')
    text.append(f'  {score:+d} · {tr(band)}', style=f'bold {color}')
    text.append('\n' + tr('难度仅描述这组选择，不是固定难度档位。'), style='#9aa8b8')
    return text


def options_text(app, width):
    if app.newgame_phase == 'identity':
        from .dream_types import birth_text
        return birth_text(app, width)
    width = max(20, width)
    console = Console(width=width)
    text = Text()
    app._newgame_hit_rows = {}
    app._newgame_slider_hits = {}
    app._newgame_selected_row = 0
    physical_row = 0

    def append(line, index=None):
        nonlocal physical_row
        wrapped = line.wrap(console, width, overflow='fold')
        if index is not None:
            for y in range(physical_row, physical_row + len(wrapped)):
                app._newgame_hit_rows[y] = index
        for part in wrapped:
            text.append_text(part)
            text.append('\n')
        physical_row += len(wrapped)

    if app.newgame_phase == 'fragment':
        from ..core.content import ITEM_DEFINITIONS, MEMORY_FRAGMENT_EFFECTS
        append(Text(tr('—— 择一枚记忆碎片 ——'), style='bold #e5c780'))
        append(Text(tr('梦递来三枚残响，选其一随你入梦：'), style='#a2b4c7'))
        for index, memory in enumerate(app.newgame_fragments):
            definition = ITEM_DEFINITIONS[memory]
            focused = index == app.newgame_fragment_cursor
            if focused:
                app._newgame_selected_row = physical_row
            append(Text(('▶ ' if focused else '  ') + tr(definition['name']),
                        style='bold #91ddd3' if focused else '#d0d7df'), index)
            short = MEMORY_FRAGMENT_EFFECTS.get(definition.get('memory_effect'), {}).get('short', '')
            append(Text('  ' + tr(short), style='#a2b4c7'), index)
            append(Text(''))
        return text

    rows = option_rows()
    app.newgame_cursor = min(max(0, app.newgame_cursor), len(rows)-1)
    previous_kind = None
    for index, (kind, key) in enumerate(rows):
        group = kind if kind != 'toggle' else TOGGLE_DEFS[key]['kind']
        if group != previous_kind:
            title = {'slider': tr('梦境指标'), 'boon': tr('强化'),
                     'challenge': tr('挑战'), 'enhance': tr('增强'),
                     'confirm': ''}[group]
            append(Text('── ' + title + ' ──' if title else '', style='#798aa6'))
            previous_kind = group
        focused = index == app.newgame_cursor
        if focused:
            app._newgame_selected_row = physical_row
        style = 'bold #91ddd3' if focused else '#d0d7df'
        prefix = '▶ ' if focused else '  '
        if kind == 'slider':
            spec = SLIDER_DEFS[key]
            tier, weight, _ = spec['tiers'][app.newgame_sliders[key]]
            name = tr(spec['name'])
            line = Text(prefix + name + ' ' * max(1, 22-cell_len(name)), style=style)
            start = cell_len(line.plain) + 1
            app._newgame_slider_hits[key] = (physical_row, start)
            line.append('[', style='#60728e')
            for level in range(5):
                line.append('●' if level == app.newgame_sliders[key] else '·',
                            style='#e5c780' if level == app.newgame_sliders[key] else '#60728e')
                if level < 4:
                    line.append(' ')
            line.append('] ' + tr(tier) + f' ({weight:+d})', style=style)
        elif kind == 'toggle':
            spec = TOGGLE_DEFS[key]
            weight = spec.get('weight', 0)
            # 增强项不参与难度：不显示 ±0，改标「不改变难度」。
            suffix = f" ({weight:+d})" if weight else ' ' + tr('（不改变难度）')
            line = Text(prefix + ('[x] ' if key in app.newgame_toggles else '[ ] ')
                        + tr(spec['name']) + suffix, style=style)
        else:
            line = Text(prefix + tr('继续：选择身份'), style='bold #e5c780')
        append(line, index)
    return text


def detail_text(app):
    if app.newgame_phase == 'identity':
        from .dream_types import birth_detail
        return birth_detail(app)
    if app.newgame_phase == 'fragment':
        return Text(tr('选择一枚碎片后才创建存档；返回可继续调整。'), style='#a2b4c7')
    kind, key = option_rows()[app.newgame_cursor]
    if kind == 'confirm':
        return Text(tr('确认调律后选择身份与能力档位。'), style='#a2b4c7')
    spec = SLIDER_DEFS[key] if kind == 'slider' else TOGGLE_DEFS[key]
    text = Text(tr(spec.get('hint', spec.get('desc', ''))) + '\n', style='#a2b4c7')
    if kind == 'slider':
        effects = spec['tiers'][app.newgame_sliders[key]][2]
        labels = {'enemy_integrity': tr('完整度'), 'enemy_trauma': tr('创伤'),
                  'max_imagination': tr('想象力上限'), 'imagination_regen': tr('每回合回流'),
                  'ability_cost': tr('成本'), 'ability_power': tr('效力'),
                  'max_mind': tr('心智上限'), 'max_lucidity': tr('清醒上限'),
                  'resilience': tr('受到创伤'), 'loot_luck': tr('运气修正'),
                  'enemy_density': tr('数量'), 'ability_cooldown': tr('冷却')}
        values = []
        for name, value in effects.items():
            if name == 'imagination_regen':
                amount = f'{1+value:g}'
            elif name.startswith('max_'):
                amount = str(value)
            elif name == 'loot_luck':
                amount = f'{value:+g}'
            else:
                amount = f'×{value:g}'
            values.append(labels[name] + ' ' + amount)
        text.append(' · '.join(values), style='#e5c780')
    else:
        text.append(tr('同组强化与挑战互斥，启用一项会关闭另一项。')
                    if spec.get('group') else tr('默认关闭；仅影响这一局。'), style='#e5c780')
    return text
