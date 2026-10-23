"""Read-only ASCII identities for settled projectile playback (never ballistics)."""
from dataclasses import dataclass, replace

from .frame_geometry import projectile_color


class ProjectileGlyph(str):
    """Keep tiny ASCII marks tiny in the image backend, without changing map fonts."""
    @property
    def raster_scale(self):
        return {'.':.12, "'":.16, ':':.30, 'o':.46, '*':.52, '~':.50}.get(self,.64)


@dataclass(frozen=True)
class ProjectileVisual:
    family: str
    color: str
    highlight: str
    shade: str
    heads: str
    tails: str
    tail_length: int
    impact: str
    direction: str = ''


VISUALS = {
    'aggregate': ProjectileVisual('aggregate','#dccb9a','#fff0c7','#8d8064','o','.:',1,'*:.',),
    'echo': ProjectileVisual('echo','#6fd7d2','#c5fff1','#3f777f','*','-:',2,'+:.',),
    'clip': ProjectileVisual('clip','#9cb5ce','#e6ecf2','#596a82','>','-.',2,"+'.",'arrow'),
    'recording': ProjectileVisual('recording','#b8a3e0','#eee1ff','#695d91',':=','.:',2,':=.'),
    'projection': ProjectileVisual('projection','#7ebfe5','#d6f5ff','#466d99','-','=:.',3,'+:.' ,'line'),
    'nail': ProjectileVisual('nail','#d7bb75','#fff2bc','#8b7651','-','-.',1,"+'.",'line'),
    'sonic': ProjectileVisual('sonic','#c2e7e4','#f1fffc','#638b97','):',':.',3,'):.' ,'wave'),
    'ice': ProjectileVisual('ice','#8fc9ed','#ddf6ff','#527c9e','>','-.',2,'+:.','arrow'),
    'needle': ProjectileVisual('needle','#b6dfe5','#edf9ef','#668d98','-','.',2,':.','line'),
    'electric': ProjectileVisual('electric','#c6b4f0','#f2e9ff','#77629e','+x','/\\:',2,'+x:.',),
    'flare': ProjectileVisual('flare','#e9a15e','#ffe2a1','#9a5e54','*','*:.',3,'*:.',),
    'liquid': ProjectileVisual('liquid','#91e7ef','#d9fbff','#4a8f99','o:','o:.',3,':o.',),
    'gas': ProjectileVisual('gas','#b9c5d6','#e6ecf5','#667286','~:',':.~',3,'~:.',),
    'throw': ProjectileVisual('throw','#dccb9a','#fff0c7','#8d8064','o','.',1,'o.',),
}

SOURCE_FAMILIES = {
    'aggregate':'aggregate', 'echo_emitter':'echo', 'binder_clip_launcher':'clip',
    'voice_recorder_pen':'recording', 'line_projector':'projection', 'nail_gun':'nail',
    'sonic_whistle':'sonic', 'dart_gun':'ice', 'hospital.hollow_lancet':'needle',
    'arc_bolt':'electric', 'flare_bolt':'flare', 'water_gun':'liquid', 'hair_dryer':'gas',
}


def visual_for_source(source, *, profile=None, kind='shot', material_color=None):
    """Select identity from actual source/profile, not inventory or equipment order."""
    visual=VISUALS[SOURCE_FAMILIES.get(source, 'throw' if kind=='throw' else 'aggregate')]
    spec=dict(profile or {})
    portent=spec.get('portent') or ()
    if portent and portent[0]=='frozen':
        ice=VISUALS['ice']
        visual=replace(visual,color=ice.color,highlight=ice.highlight,shade=ice.shade)
    if material_color:
        color=projectile_color(material_color)
        visual=replace(visual,color=color,highlight=_mix(color,'#ffffff',.4),
                       shade=_mix(color,'#101018',.5))
    return visual


def capture_projectile_visual(state, command, args, choice=None):
    """Capture before inventory consumption; do not mutate state or plan payment."""
    item_commands=('fire_once','fire_once_target','throw','throw_target')
    if command in item_commands:
        index=args[0] if args else -1
        if not 0<=index<len(state.inventory):
            return None
        item=state.inventory[index]
        if command.startswith('throw'):
            return visual_for_source('',kind='throw',material_color=item.color)
        return visual_for_source(item.definition_id,kind='throw')
    if command not in ('fire','fire_assisted','spray_fire','spray_target'):
        return None
    if choice=='aggregate':
        return visual_for_source('aggregate')
    plan_args={}
    if command in ('fire_assisted','spray_target'):
        x,y=args[-2:]
        plan_args=dict(target=state.entity_at(x,y),cell=(x,y))
    if command.startswith('spray'):
        from ..core.weapons import pick_ammo_kind, spray_plan, bound_spray_source
        from ..materials import gas_def, liquid_def
        index=args[0] if args else -1
        plan=spray_plan(state,index if index>=0 else None,choice=choice,**plan_args)
        medium=dict(plan.projectile_profile).get('medium')
        if medium not in ('liquid','gas'):
            return None
        material=None
        index,_reason=bound_spray_source(state,plan,index if index>=0 else None)
        index=-1 if index is None else index
        if 0<=index<len(state.inventory):
            selected=pick_ammo_kind(state.inventory[index])
            material=selected[0] if selected else None
        if material is None:
            material='水' if medium=='liquid' else '水蒸气'
        definition=liquid_def(material) if medium=='liquid' else gas_def(material)
        return visual_for_source('water_gun' if medium=='liquid' else 'hair_dryer',
                                 material_color=definition.color)
    plan=state.equipment.plan_action('fire',choice=choice,**plan_args)
    emitters=getattr(plan,'emitters',())
    source_id=emitters[0][0] if emitters else plan.primary_source_id
    item=state.equipment._item(source_id) if source_id else None
    return visual_for_source(item.definition_id if item else 'aggregate',
                             profile=plan.projectile_profile)


def _mix(a,b,amount):
    return '#'+''.join(f'{round(int(a[i:i+2],16)*(1-amount)+int(b[i:i+2],16)*amount):02x}'
                       for i in (1,3,5))


def projectile_samples(projectile,age,quality):
    """At most four in-path glyphs; no invented AoE, path or environment light."""
    visual=projectile.visual
    if visual is None or age<0 or age>projectile.total_time or not quality:
        return ()
    flight=projectile.flight_time
    cells=projectile.cells
    result=[]
    if age<flight and cells:
        head=min(len(cells)-1,int(age/flight*len(cells)))
        beat=int(age*20)
        length=visual.tail_length if quality>=2 else min(1,visual.tail_length)
        for back in range(min(head,length),0,-1):
            index=head-back
            char=visual.tails[(beat+back)%len(visual.tails)]
            if visual.direction in ('line','arrow') and char in '-=':
                char=_direction(cells,index,'line') if char=='-' else '='
            result.append((cells[index],char,visual.shade if back>1 else visual.color))
        char=visual.heads[beat%len(visual.heads)]
        if visual.direction=='arrow' or visual.direction=='line':
            char=_direction(cells,head,visual.direction)
        elif visual.direction=='wave' and char==')':
            char=')' if _delta(cells,head)[0]>=0 else '('
        result.append((cells[head],char,visual.highlight))
    for index,x,y in projectile.bounces:
        delta=age-flight*(index+1)/max(1,len(cells))
        if 0<=delta<=.12:
            result.append(((x,y),'+',visual.highlight))
    if age>=flight and projectile.end_cell is not None and projectile.end!='range':
        progress=min(.999,(age-flight)/max(.001,projectile.total_time-flight))
        chars=visual.impact
        result.append((projectile.end_cell,chars[min(len(chars)-1,int(progress*len(chars)))],
                       visual.color if progress<.5 else visual.shade))
    return result


def _delta(cells,index):
    if len(cells)<2:
        return (1,0)
    a,b=(cells[index],cells[index+1]) if index+1<len(cells) else (cells[index-1],cells[index])
    return b[0]-a[0],b[1]-a[1]


def _direction(cells,index,kind):
    dx,dy=_delta(cells,index)
    if kind=='arrow':
        return ('>' if dx>0 else '<') if abs(dx)>abs(dy) else ('v' if dy>0 else '^') if not dx else ('\\' if dx*dy>0 else '/')
    return '-' if not dy else '|' if not dx else '\\' if dx*dy>0 else '/'
