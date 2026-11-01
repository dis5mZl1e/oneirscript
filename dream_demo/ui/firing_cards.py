"""Rich-only firing source cards, built from the live action plans."""
from rich.console import Console
from rich.style import Style
from rich.text import Text

from ..core.content import ITEM_DEFINITIONS
from ..core.firing_sources import (
    LEGACY_BASIC_ID, LEGACY_BASIC_NAME, collect_firing_sources,
    equipment_emitters, legacy_basic_view, magazine_spec,
)
from ..i18n import tr
from .firing_presentation import equipment_resource_text, magazine_resource_text, reload_status
from .panel_fields import FIELD_COLORS as C

_CONSOLE = Console()
CARD_BG = '#253331'
SELECTED_BG = '#35413a'


def reload_entry(source_key):
    return Text(' [' + tr('换弹') + ' R]', style=Style(
        color=C['cooldown'], bold=True, underline=True,
        meta={'fire_reload': source_key}))


def source_name(source):
    return ' + '.join(tr(LEGACY_BASIC_NAME) if key == LEGACY_BASIC_ID else
                      tr(ITEM_DEFINITIONS.get(key, {}).get('name', key))
                      for key in source.definition_ids) or tr('聚合弹')


def source_stats(state, source):
    """Quotes only: base action values, before target-specific settlement."""
    from ..core.ballistics import PROJECTILE_MAX_RANGE
    if source.kind == 'item':
        item = next((i for i in state.inventory if i.instance_id in source.instance_ids), None)
        return Text(tr('一次性发射') + ' · ' + tr('伤害') + f' {int(item.power or 2) if item else 2}',
                    style=C['damage'])
    plan = state.equipment.plan_action(source.action_kind, choice=source.choice_key or 'aggregate')
    spec = dict(plan.projectile_profile)
    if source.action_kind.startswith('spray_'):
        from ..core.weapons import SPRAY_RANGE, spray_imagination_cost, bound_spray_source
        index, reason = bound_spray_source(state, plan, None)
        cost = spray_imagination_cost(plan, index) if not reason else None
        text = Text(tr('射程') + f' {SPRAY_RANGE}', style=C['range'])
        if cost is not None:
            text.append(' · ' + tr('想象力') + f' {cost}', style=C['cost'])
    else:
        text = Text(tr('加伤') + f' +{plan.damage_increment:g}', style=C['damage'])
        text.append(' · ' + tr('射程') + f' {min(PROJECTILE_MAX_RANGE, int(spec.get("range", PROJECTILE_MAX_RANGE)))}',
                    style=C['range'])
        text.append(' · ' + tr('追加穿透') + f' {int(spec.get("penetration", 0))}', style=C['effect'])
    text.append(' · ' + tr('耗时') + f' {plan.base_time:g}', style=C['cooldown'])
    return text


def render_fire_cards(app, state):
    width = max(8, app.query_one('#panel').content_size.width)
    sources = collect_firing_sources(state)
    lines, rows = [], []

    def add(value='', index=-1, background=None, serif=False):
        text = value.copy() if isinstance(value, Text) else Text(value, style=C['muted'])
        for part in text.wrap(_CONSOLE, width, overflow='fold') or [Text()]:
            if background:
                part.pad_right(max(0, width-part.cell_len))
                part.stylize(Style(bgcolor=background))
            if serif:
                part.stylize(Style(meta={'font_role': 'serif'}))
            lines.append(part)
            rows.append(index)

    if not sources:
        add(tr('尚未解锁任何发射来源。'))
        return lines, rows
    selected = min(max(0, app.panel_selection), len(sources)-1)
    current = sources[selected]
    add(Text(tr('当前发射源') + ' · ' + source_name(current), style='bold '+C['word']))
    for key in current.definition_ids:
        description = ITEM_DEFINITIONS.get(key, {}).get('description', '')
        if description:
            add(Text(tr(description), style=C['text']), serif=True)
    add()
    add(Text('── ' + tr('发射来源') + ' ──', style='bold '+C['label']))
    for index, source in enumerate(sources):
        bg = SELECTED_BG if index == selected else CARD_BG
        prefix = '▶ ' if index == selected else '  '
        add(Text(prefix + source_name(source), style='bold '+C['word']), index, bg)
        add(Text('▎ ') + source_stats(state, source), index, bg)
        choice = dict(kind=source.action_kind, key=source.choice_key)
        weapons = ([legacy_basic_view(state)] if source.kind == 'legacy' else
                   equipment_emitters(state, source.action_kind, source.choice_key)
                   if source.kind == 'equipment' else ())
        if weapons:
            for item in weapons:
                if item is None:
                    continue
                resource = (magazine_resource_text(item, unicode=app._symbol_mode() != 'ascii')
                            if item.magazine is not None else equipment_resource_text(state, choice))
                line = Text('▎ ')
                if len(weapons) > 1:
                    line.append(tr(item.name) + ' ', style=C['word'])
                line.append_text(resource)
                if magazine_spec(item.definition_id):
                    line.append_text(reload_entry(source.key))
                add(line, index, bg)
                status, blocked = reload_status(state, item)
                if status:
                    add(Text('  ' + status, style=C['condition'] if blocked else C['cooldown']), index, bg)
        elif source.kind == 'equipment':
            add(Text('▎ ') + equipment_resource_text(state, choice), index, bg)
        else:
            add(Text('▎ ' + tr('余量 {count}', count=source.count), style=C['count']), index, bg)
        if not source.can_fire:
            add(Text('  ' + tr(source.reason or '当前不可发射'), style=C['condition']), index, bg)
        elif source.target_pending:
            add(Text('  ' + tr('待选目标判定'), style=C['condition']), index, bg)
        add()
    return lines, rows
