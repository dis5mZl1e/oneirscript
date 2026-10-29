"""Compact source facts: real magazines, real reload quotes, two-line HUD."""
from rich.cells import cell_len
from rich.text import Text

from ..core.content import ITEM_DEFINITIONS
from ..core.firing_sources import (
    LEGACY_BASIC_ID, LEGACY_BASIC_NAME, collect_firing_sources, equipment_emitters,
    legacy_basic_view, magazine_spec, reload_quote,
)
from ..i18n import tr

COLOR_NAME = 'bold #c7a6ed'
COLOR_NUMBER = '#CFD6E6'
COLOR_CHARGE = '#70CBBB'
COLOR_COST = '#D9A56E'
COLOR_RELOAD = '#C4A7E7'
COLOR_BLOCKED = '#DB91B4'
COLOR_HELP = '#B6CAE8'

# 子弹减少的 3 帧脉冲：亮橙 → 亮白 → 正常；只改显示，不碰世界状态。
AIM_PULSE_STYLES = ('bold underline #FFB86B', 'bold underline #FFFFFF', '')
AIM_PULSE_INTERVAL = .1


def supply(count):
    return '/'*min(8,max(0,int(count)))+' '+str(count)


# 每个武器家族固定形状；数字仍给出准确余量，Unicode 只是视觉身份。
MAGAZINE_GLYPHS = {
    'echo_emitter': ('┃', '┊'), 'binder_clip_launcher': ('◆', '◇'),
    'voice_recorder_pen': ('●', '○'), 'line_projector': ('▰', '▱'),
    'nail_gun': ('╻', '╵'), 'sonic_whistle': ('≈', '·'),
    'dart_gun': ('▲', '△'), 'hospital.hollow_lancet': ('│', '┆'),
}


MAGAZINE_COLOURS = {
    'echo_emitter': ('#70CBBB','#385953'), 'binder_clip_launcher': ('#A5BDD6','#4B596B'),
    'voice_recorder_pen': ('#BD9EDE','#584A6C'), 'line_projector': ('#7FBCE7','#3E526B'),
    'nail_gun': ('#DEBB72','#63523C'), 'sonic_whistle': ('#B6DBD6','#4B6665'),
    'dart_gun': ('#9AD1FF','#455C79'), 'hospital.hollow_lancet': ('#C5E4E8','#53676C'),
}


def magazine_resource_text(item, *, unicode=True):
    spec=magazine_spec(item.definition_id)
    capacity=max(1,int(getattr(item,'magazine_capacity',0) or (spec.capacity if spec else 1)))
    rounds=max(0,int(getattr(item,'magazine',0) or 0))
    full,empty=MAGAZINE_GLYPHS.get(item.definition_id,('|','.')) if unicode else ('|','.')
    slots=min(8,capacity)
    filled=min(slots,rounds) if capacity<=8 else min(slots,rounds*slots//capacity)
    colour,dim=MAGAZINE_COLOURS.get(item.definition_id,('#70CBBB','#385953'))
    text=Text('[',style=dim)
    text.append(full*filled,style='bold '+colour)
    text.append(empty*(slots-filled),style=dim)
    text.append('] ',style=dim)
    text.append(f'{rounds}/{capacity}',style=COLOR_BLOCKED if rounds==0 else COLOR_COST if rounds==1 else COLOR_NUMBER)
    if rounds==0:
        text.append(' '+tr('空匣'),style=COLOR_BLOCKED)
    return text


def _spray_resource_text(state,plan,source_index=None,*,unicode=True):
    from ..core.weapons import bound_spray_source,pick_ammo_kind
    from ..materials import gas_def,liquid_def
    medium=dict(plan.projectile_profile).get('medium','liquid')
    index,reason=bound_spray_source(state,plan,source_index)
    if reason:
        return Text(tr(reason),style=COLOR_BLOCKED)
    item=state.inventory[index] if index is not None and 0<=index<len(state.inventory) else None
    picked=pick_ammo_kind(item) if item else None
    spec=dict(plan.projectile_profile)
    cost=int(spec.get('cost') or 0)
    text=Text()
    if item is None:
        material='水' if medium=='liquid' else '水蒸气'
        text.append(tr('内置')+' '+tr(material),style=COLOR_CHARGE)
    elif picked is None:
        return Text(tr('容器无对应材料'),style=COLOR_BLOCKED)
    else:
        material,amount=picked
        container=ITEM_DEFINITIONS.get(item.definition_id,{}).get('container',{})
        capacity=max(1,int(container.get('cap') or sum(item.contents.values()) or 1))
        colour=(liquid_def(material) if medium=='liquid' else gas_def(material)).color
        full,empty=('▰','▱') if unicode else ('|','.')
        filled=min(4,max(0,amount)*4//capacity)
        text.append(tr(material)+' ',style=colour)
        text.append('['+full*filled,style=colour)
        text.append(empty*(4-filled)+'] ',style='#536776')
        text.append(f'{amount}/{capacity}',style=COLOR_NUMBER)
        text.append(' '+tr('每次{amount}',amount=int(spec.get('amount') or 0)),style=COLOR_NUMBER)
    if cost:
        text.append(' · '+tr('想象{cost}',cost=cost),style=COLOR_COST)
    return text


def equipment_resource_text(state,choice,*,source_index=None,unicode=True):
    if choice.get('key')==LEGACY_BASIC_ID:
        view=legacy_basic_view(state)
        return magazine_resource_text(view,unicode=unicode) if view else Text()
    kind=choice.get('kind','fire')
    plan=state.equipment.plan_action(kind,choice=choice.get('key'))
    if kind.startswith('spray_'):
        return _spray_resource_text(state,plan,source_index,unicode=unicode)
    text=Text()
    emitters=tuple(getattr(plan,'emitters',()))
    if not emitters and (plan.requires_target or not plan.valid):
        return Text(tr('待选目标判定') if plan.requires_target else tr(plan.reason),style=COLOR_BLOCKED)
    for source_id,shots in emitters:
        item=state.equipment._item(source_id)
        if item is None:
            continue
        if text:
            text.append(' + ',style=COLOR_HELP)
        if len(emitters)>1:
            text.append(tr(item.name)+' ',style=COLOR_NAME)
        text.append_text(magazine_resource_text(item,unicode=unicode) if item.magazine is not None else Text(tr('供给∞'),style=COLOR_NUMBER))
        if shots>1:
            text.append(f'×{shots}',style=COLOR_COST)
        if item.definition_id=='hospital.hollow_lancet':
            amount=sum(max(0,int(n)) for n in item.contents.values())
            text.append(' · '+tr('注入{amount}/{capacity}',amount=amount,capacity=6),style=COLOR_CHARGE)
    return text or Text(tr('供给∞'),style=COLOR_NUMBER)


def equipment_resource(state,choice,**kwargs):
    return equipment_resource_text(state,choice,**kwargs).plain


def _legacy_resource(state):
    return equipment_resource_text(state,dict(key=LEGACY_BASIC_ID)).plain


def _supply_refill_rounds(app, item):
    """换弹装填动画的显示用余量（None = 不在动画中）。

    只改渲染：真实 item.magazine 在动作结算时已经是新值。这里按
    0.3s / 3 帧把旧值 → 新值分成三段，让槽条和数字逐帧补齐；不写回状态。
    """
    if app is None:
        return None
    anim = getattr(app, '_supply_refill_anim', None) or {}
    key = getattr(item, 'instance_id', None)
    pair = anim.get(key) if key is not None else None
    if pair is None:
        return None
    old, new = int(pair[0]), int(pair[1])
    if new <= old:
        return None
    phase = max(0, min(2, int(getattr(app, '_supply_feedback_phase', 0) or 0)))
    if phase <= 0:
        return old
    if phase >= 2:
        return new
    step = (new - old + 2) // 3
    return min(new, old + max(1, step))


def _aim_magazine_text(item,*,compact=False,app=None):
    """Aim bubble for magazine weapons.

    2026-10-26 玩家复核：有弹匣武器仍要右侧发射界面同款的 [┃┃┊] 槽条
    （槽条本身就是弹匣图标），只有窄宽度兜底时退成纯数字。
    换弹完成后的 0.3 秒内按旧值→新值分帧显示槽条，形成装填动画。
    """
    display_rounds = _supply_refill_rounds(app, item) if app is not None else None
    if not compact:
        if display_rounds is None:
            return magazine_resource_text(item)
        from types import SimpleNamespace
        view = SimpleNamespace(
            definition_id=getattr(item, 'definition_id', ''),
            magazine=display_rounds,
            magazine_capacity=getattr(item, 'magazine_capacity', 0),
        )
        return magazine_resource_text(view)
    definition_id=str(getattr(item,'definition_id','') or '')
    spec=magazine_spec(definition_id)
    capacity=max(1,int(getattr(item,'magazine_capacity',0) or (spec.capacity if spec else 1)))
    rounds=max(0,int(getattr(item,'magazine',0) or 0))
    if display_rounds is not None:
        rounds = display_rounds
    return Text(f'{rounds}/{capacity}',
                style=COLOR_BLOCKED if rounds==0 else COLOR_COST if rounds==1 else COLOR_NUMBER)


def _aim_projectile_text(item):
    """One projectile glyph for a source without a magazine."""
    definition_id=str(getattr(item,'definition_id','') or '')
    full,_empty=MAGAZINE_GLYPHS.get(definition_id,('•','·'))
    colour=MAGAZINE_COLOURS.get(definition_id,('#DCCB9A','#70634A'))[0]
    text=Text()
    text.append(full,style=colour)
    try:
        quantity=int(getattr(item,'quantity',0) or 0)
    except (TypeError,ValueError):
        quantity=0
    # 设备自身的 quantity 通常只是「一件东西」；只有能叠的弹药才当余量。
    text.append('×'+str(quantity) if quantity>1 else '∞',style=COLOR_NUMBER)
    return text


def _aim_emitter_text(item,*,compact=False,app=None):
    if getattr(item,'magazine',None) is not None:
        return _aim_magazine_text(item,compact=compact,app=app)
    return _aim_projectile_text(item)


def _compact_spray_text(state,choice,text):
    import re
    kind=str(choice.get('kind',''))
    counts=re.findall(r'\d+/\d+',text.plain)
    prefix=(text.plain.split(' [',1)[0]+' ') if kind.startswith('spray_') and counts else ''
    if not counts and kind.startswith('spray_') and tr('内置') in text.plain:
        plan=state.equipment.plan_action(kind,choice=choice.get('key'))
        return Text(tr('内置{cost}想',cost=int(dict(plan.projectile_profile).get('cost') or 0)),style=COLOR_COST)
    return Text(prefix+'+'.join(counts),style=COLOR_NUMBER) if counts else Text(text.plain,style=COLOR_NUMBER)


def _aim_equipment_text(app,state,choice,*,compact=False):
    """Aim-bubble rendering for the selected equipment row.

    Magazines keep their exact digits and get one family icon; sources without
    a magazine keep one projectile icon (with ∞ when there is no finite count).
    Sprayers keep the material capacity readout unchanged.
    """
    kind=str(choice.get('kind','fire'))
    if choice.get('key')==LEGACY_BASIC_ID:
        view=legacy_basic_view(state)
        return _aim_magazine_text(view,compact=compact,app=app) if view else Text()
    if kind.startswith('spray_'):
        text=equipment_resource_text(state,choice,source_index=getattr(app,'spray_source',None))
        return _compact_spray_text(state,choice,text) if compact else text
    plan=state.equipment.plan_action(kind,choice=choice.get('key'))
    emitters=tuple(getattr(plan,'emitters',()))
    if not emitters and (plan.requires_target or not plan.valid):
        return Text(tr('待选目标判定') if plan.requires_target else tr(plan.reason),style=COLOR_BLOCKED)
    pieces=[]
    injections=[]
    for source_id,shots in emitters:
        item=state.equipment._item(source_id)
        if item is None:
            continue
        pieces.append((item,_aim_emitter_text(item,compact=compact,app=app)))
        if item.definition_id=='hospital.hollow_lancet':
            amount=sum(max(0,int(n)) for n in item.contents.values())
            injections.append(tr('注入{amount}/{capacity}',amount=amount,capacity=6))
    if not pieces:
        return Text(tr('供给∞'),style=COLOR_NUMBER)
    if compact:
        return Text('+'.join(piece.plain for _item,piece in pieces),style=COLOR_NUMBER)
    text=Text()
    for offset,(item,piece) in enumerate(pieces):
        if offset:
            text.append(' + ',style=COLOR_HELP)
        if len(pieces)>1:
            text.append(tr(item.name)+' ',style=COLOR_NAME)
        text.append_text(piece)
    for injection in injections:
        text.append(' · '+injection,style=COLOR_CHARGE)
    return text


def aim_resource_text(app,*,compact=False):
    """Resource half of the aim bubble: digits + one icon, no magazine slot bar."""
    state=app.session.state
    choice=getattr(app,'aim_action_choice',None)
    index=app.throw_item_index if app.throw_item_index is not None else app.fire_once_index
    if app.fire_once_index is not None and app._aim_ammo_status() == 'exhausted':
        return Text('•×0', style=COLOR_BLOCKED)
    if isinstance(choice,dict) and choice.get('key')!='aggregate' and not getattr(app,'construct_aim_id',None):
        return _aim_equipment_text(app,state,choice,compact=compact)
    name,resource=current_source(app)
    if index is not None and 0<=index<len(state.inventory):
        item=state.inventory[index]
        mark={'arc_bolt':'ϟ','flare_bolt':'✦'}.get(item.definition_id,'•')
        colour={'arc_bolt':'#C6B4F0','flare_bolt':'#E9A15E'}.get(item.definition_id,'#DCCB9A')
        return Text(mark+'×'+str(item.quantity),style=colour)
    if (isinstance(choice,dict) and choice.get('key')=='aggregate') or name==tr('聚合弹'):
        return Text('•×'+str(state.projectile_charges),style='#DCCB9A')
    if choice is None and index is None:
        sources=_presentation_sources(app)
        if len(sources)==1 and sources[0].kind in ('equipment','legacy'):
            source=sources[0]
            if source.kind=='legacy':
                view=legacy_basic_view(state)
                return _aim_magazine_text(view,compact=compact,app=app) if view else Text()
            return _aim_equipment_text(app,state,dict(kind=source.action_kind,key=source.choice_key),compact=compact)
    return Text(resource,style=COLOR_NUMBER)


def current_resource_text(app,*,compact=False):
    """Backwards-compatible name; the aim HUD's resource renderer."""
    return aim_resource_text(app,compact=compact)


def supply_levels(state):
    """UI observation only; no magazine initialisation or payment."""
    levels={item.instance_id:int(item.magazine) for item in state.inventory if item.magazine is not None}
    levels[LEGACY_BASIC_ID]=getattr(state,'legacy_basic_magazine',None)
    return levels


def _stop_supply_pulse(app):
    for timer in getattr(app,'_supply_feedback_pulse_timers',()) or ():
        try:
            timer.stop()
        except Exception:
            pass
    app._supply_feedback_pulse_timers=()


def _set_supply_pulse_phase(app,frame):
    if not getattr(app,'is_running',False):
        return
    # 事件已过期后迟到的帧不应再把 phase 点亮。
    if not getattr(app,'_supply_feedback',None):
        return
    app._supply_feedback_phase=frame
    try:
        app._refresh_map_hints()
    except Exception:
        pass


def _start_supply_pulse(app):
    """Three display frames (~0.1s apart); never touches cost/action/world state."""
    _stop_supply_pulse(app)
    app._supply_feedback_phase=0
    timers=[]
    for frame in (1,2):
        timers.append(app.set_timer(AIM_PULSE_INTERVAL*frame,
                                    lambda frame=frame: _set_supply_pulse_phase(app,frame)))
    app._supply_feedback_pulse_timers=timers


def note_supply_feedback(app,before,changed):
    """One short emphasis after a committed shot/reload, never an idle animation."""
    if not changed or not app.is_running:
        return
    import time
    after=supply_levels(app.session.state)
    events={key:('refill' if after[key]>value else 'spent',time.monotonic()+.28)
            for key,value in before.items() if value is not None and after.get(key) is not None and after[key]!=value}
    if not events:
        return
    app._supply_feedback=events
    # 换弹回填：渲染层用旧值→新值分帧补齐槽条（不写回 item.magazine）。
    app._supply_refill_anim={
        key: (int(value), int(after[key]))
        for key, value in before.items()
        if value is not None and after.get(key) is not None and int(after[key]) > int(value)
    }
    _start_supply_pulse(app)
    old=getattr(app,'_supply_feedback_timer',None)
    if old is not None:
        old.stop()
    def expire():
        app._supply_feedback={}
        app._supply_refill_anim={}
        app._supply_feedback_phase=0
        _stop_supply_pulse(app)
        if app.is_running:
            app._refresh_map_hints()
    app._supply_feedback_timer=app.set_timer(.3,expire)


def reload_target(state, choice):
    """The one reloadable physical weapon behind a source, else None.

    A coordinated row with several weapons is deliberately not collapsed into
    "reload the first one"; the caller opens an explicit weapon list instead.
    """
    if not isinstance(choice, dict):
        return None
    if choice.get('key') == LEGACY_BASIC_ID:
        return legacy_basic_view(state)
    items = [item for item in equipment_emitters(
                 state, choice.get('kind', 'fire'), choice.get('key'))
             if magazine_spec(item.definition_id) is not None]
    return items[0] if len(items) == 1 else None


def reload_status(state, item):
    """(text, blocked) for compact rows; reads the quote, never pays it."""
    quote = reload_quote(item)
    if quote is None:
        return '', False
    if quote.total_steps and (quote.paid or int(getattr(item, 'reload_steps', 0) or 0)):
        return tr('换弹 {done}/{total} · 已付{cost}想象',
                  done=quote.done_steps, total=quote.total_steps,
                  cost=quote.total_cost), False
    if quote.needed <= 0:
        return '', False
    if state.imagination < quote.total_cost:
        return tr('想象不足：需{cost} · 换弹{steps}行动',
                  cost=quote.total_cost, steps=quote.total_steps), True
    return tr('R换弹 {cost}想象/{steps}行动',
              cost=quote.total_cost, steps=quote.total_steps), False


def _presentation_sources(app):
    """The sidebar selection is also the remembered F source, outside aiming."""
    sources = collect_firing_sources(app.session.state)
    if not getattr(app, 'aiming', False):
        selected = getattr(app, '_last_firing_source_key', None)
        remembered = next((source for source in sources if source.key == selected), None)
        if remembered is not None:
            return (remembered,)
    return sources


def current_source(app):
    state = app.session.state
    ability = getattr(app, 'construct_aim_id', None)
    if ability:
        from ..data.abilities import ABILITY_DEFINITIONS
        definition = ABILITY_DEFINITIONS[ability]
        return tr(definition['name']), tr('想象力 {cost}', cost=state._scaled_ability_cost(definition['cost']))
    index = app.throw_item_index if app.throw_item_index is not None else app.fire_once_index
    if index is not None:
        captured = getattr(app, '_aim_source_identity', None)
        if (app.fire_once_index is not None and captured is not None
                and app._aim_ammo_status() == 'exhausted'):
            return tr(captured[1].name), '×0 · ' + tr('一次性发射')
        if not 0 <= index < len(state.inventory):
            return tr('来源已失效'), ''
        item = state.inventory[index]
        captured = getattr(app, '_aim_source_identity', None)
        if captured is not None and captured[1] is not item:
            return tr('来源已失效'), ''
        return tr(item.name), ('×'+str(item.quantity)+' · '+tr('投掷' if app.throw_item_index is not None else '一次性发射'))
    choice = app.aim_action_choice
    if isinstance(choice, str):
        choice = dict(key=choice, kind='fire', definition_ids=[])
    if choice and choice.get('key') == 'aggregate':
        return tr('聚合弹'), supply(state.projectile_charges)+' '+tr('发')
    if choice and choice.get('key') == LEGACY_BASIC_ID:
        return tr(LEGACY_BASIC_NAME), _legacy_resource(state)
    if choice:
        names = [tr(ITEM_DEFINITIONS[i].get('name', i)) for i in choice.get('definition_ids', ()) if i in ITEM_DEFINITIONS]
        return ' + '.join(names) or tr('当前发射源'), equipment_resource(state, choice)
    from ..core.firing_sources import collect_firing_sources
    sources = _presentation_sources(app)
    if len(sources) > 1:
        return tr('待选择来源'), tr('{count}种', count=len(sources))
    if sources:
        source = sources[0]
        if source.kind == 'aggregate':
            return tr('聚合弹'), supply(source.count)+' '+tr('发')
        if source.kind == 'legacy':
            return tr(LEGACY_BASIC_NAME), _legacy_resource(state)
        names = [tr(ITEM_DEFINITIONS[i].get('name', i)) for i in source.definition_ids if i in ITEM_DEFINITIONS]
        return (' + '.join(names) or tr('当前发射源'),
                ('×'+str(source.count)) if source.count is not None
                else equipment_resource(state, dict(kind=source.action_kind, key=source.choice_key)))
    return tr('当前发射源：无'), ''


def _switchable_sources(state):
    try:
        return len(collect_firing_sources(state))
    except Exception:
        return 0


def _line_two(app, state, width):
    """(Text, zones) — zones are text-column spans for the mouse entries."""
    segments = []
    if _switchable_sources(state) > 1:
        segments.append(('sources', tr('‹换源›'), COLOR_RELOAD))
    selected = getattr(app, 'aim_action_choice', None)
    if isinstance(selected, dict):
        if selected.get('key') == LEGACY_BASIC_ID:
            items = [view for view in (legacy_basic_view(state),) if view is not None]
        else:
            items = [item for item in equipment_emitters(
                         state, selected.get('kind', 'fire'), selected.get('key'))
                     if magazine_spec(item.definition_id) is not None]
        if len(items) > 1:
            segments.append(('reload', tr('R换弹（先选武器）'), COLOR_COST))
        elif items:
            text, blocked = reload_status(state, items[0])
            if text:
                segments.append(('reload', text, COLOR_BLOCKED if blocked else COLOR_RELOAD))
    segments.append(('mouse', tr('鼠标左键'), COLOR_HELP))
    if width >= 26:
        segments.append(('lock', tr('O锁定') if getattr(app, '_aim_assist_identity', None) is not None
                         else tr('O换敌'), COLOR_HELP))
        segments.append(('arrows', tr('方向键'), COLOR_HELP))
    segments.append(('cancel', tr('Esc退出'), COLOR_HELP))
    if width<30:
        compact=[]
        for key,text,style in segments:
            if key=='cancel': text='Esc'
            elif key=='sources': text='F'
            elif key=='reload':
                item=reload_target(state,selected)
                quote=reload_quote(item) if item is not None else None
                if quote and width>=18:
                    text=(tr('R{done}/{total}已付',done=quote.done_steps,total=quote.total_steps) if quote.paid else
                          tr('R{cost}想/{steps}步',cost=quote.cost,steps=quote.steps))
                else:
                    text=(f'R{quote.done_steps}/{quote.total_steps}' if quote and quote.paid else
                          f'R{quote.cost}/{quote.steps}' if quote else 'R')
            elif key=='mouse': text=tr('鼠标左键')
            elif key in ('lock','arrows'): continue
            compact.append((key,text,style))
        segments=compact
    while sum(cell_len(text) for _,text,_ in segments)+2*(len(segments)-1)>width:
        removable=next((key for key in ('arrows','lock','sources','mouse') if any(p[0]==key for p in segments)),None)
        if removable is None: break
        segments=[part for part in segments if part[0]!=removable]
    line = Text()
    zones = []
    column = 0
    for index, (name, text, color_style) in enumerate(segments):
        if index:
            line.append('  ', style=COLOR_HELP)
            column += 2
        piece = Text(text, style=color_style)
        remain = width - column
        if remain <= 0:
            break
        if cell_len(text) > remain:
            piece.truncate(remain, overflow='ellipsis')
        line.append_text(piece)
        start = column
        column += cell_len(piece.plain)
        zones.append((start, column, name))
    return line, zones


def _aim_feedback_style(app, selected_ids):
    """Display-only emphasis for the active source; '' means the idle look."""
    if not getattr(app,'aiming',False) or not selected_ids:
        return ''
    import time
    now=time.monotonic()
    active=[kind for key,(kind,until) in getattr(app,'_supply_feedback',{}).items()
            if key in selected_ids and until>now]
    if not active:
        return ''
    if 'spent' in active:
        phase=max(0,int(getattr(app,'_supply_feedback_phase',0) or 0))
        return AIM_PULSE_STYLES[min(phase,len(AIM_PULSE_STYLES)-1)]
    return 'bold underline #D8F6E9'


def aim_hud(app, width):
    width = max(12, int(width))
    state = app.session.state
    name, resource = current_source(app)
    resource_text = aim_resource_text(app)
    if cell_len(resource_text.plain)>max(4,width-min(6,cell_len(name))-1):
        resource_text=aim_resource_text(app,compact=True)
    resource_text.truncate(max(1,width-3),overflow='ellipsis')
    selected=getattr(app,'aim_action_choice',None)
    if isinstance(selected,str):
        # 旧状态机/测试里仍可能塞一个裸 kind 字符串；按 fire 归一，别让 UI 崩。
        selected=dict(key=selected,kind='fire',definition_ids=[])
    selected_ids=({LEGACY_BASIC_ID} if selected and selected.get('key')==LEGACY_BASIC_ID else
                  {item.instance_id for item in equipment_emitters(state,selected.get('kind','fire'),selected.get('key'))}
                  if isinstance(selected,dict) and selected.get('key')!='aggregate' else set())
    feedback_style=_aim_feedback_style(app, selected_ids)
    if feedback_style:
        resource_text.stylize(feedback_style)
    name_text=Text(name,style=COLOR_NAME)
    name_text.truncate(max(1,width-cell_len(resource_text.plain)-1),overflow='ellipsis')
    result = Text.assemble(name_text, ' ', resource_text)
    result.append('\n')
    status = app._aim_ammo_status() if getattr(app, 'aiming', False) else 'ready'
    if status != 'ready':
        message = tr('R换弹 · 其他键退出') if status == 'reload' else tr('弹药耗尽 · 任意键退出')
        line = Text(message, style=COLOR_BLOCKED)
        line.truncate(width, overflow='ellipsis')
        zones = [(0, min(width, cell_len(message.split(' · ')[0])), 'reload')] if status == 'reload' else []
    else:
        line, zones = _line_two(app, state, width)
    result.append_text(line)
    # Padding is 0 1: widget offsets start one column left of the text.
    app._aim_hud_zones = [(start + 1, end + 1, 1, name) for start, end, name in zones]
    return result
