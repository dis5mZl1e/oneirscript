"""Finite consumables using native materials, light, sound and action settlement.

All deploy records live in the layer's serializable item_devices ledger. Failed
preconditions return before recording, spending material or advancing the clock.
"""
from __future__ import annotations
from . import item_devices, item_targeting
from .entities import ActionResult
from .constants import ActionKind
from ..materials import portent_def, wall_def

PREFIX='consumable:'
FAIL=(False,'没有满足条件的已知目标，未消耗。',{})


def records(state):
    return [r for r in item_devices.devices(state) if str(r.get('kind','')).startswith(PREFIX)]


def register(state, kind, point, turns=3, **data):
    return item_devices.register_device(state,PREFIX+kind,*point,turns,**data)


def known(state, p, *, open=False):
    if p is None or not state.inside_board(*p) or not state.is_visible(*p): return False
    if max(abs(p[0]-state.player.x),abs(p[1]-state.player.y))>6: return False
    return not open or (item_targeting.open_cell(state,*p) and not item_targeting.protected_cell(state,*p))


def emit(state,p,radius):
    state._sound_pulse(*p,radius,by_player=True,category='lure',source='一次性声源',triggers_rewards=False)


def apply(state,ident,*,point=None,second=None,direction=None):
    if ident not in HANDLERS: return FAIL
    from ..data.expansion.consumable_runtime import consumable_item_rows
    spec=consumable_item_rows()[ident]['consumable_use']
    form=spec['form']
    if form=='point' and not known(state,point): return FAIL
    if form=='pair' and (not known(state,point) or not known(state,second) or point==second): return FAIL
    if form=='direction' and (direction is None or max(map(abs,direction))!=1): return FAIL
    if (point is not None and form in ('self','direction')) or (second is not None and form!='pair'):
        return FAIL
    if point is None: point=(state.player.x,state.player.y)
    return HANDLERS[ident](state,point,second,direction)


def success(**data): return True,'一次性物品已生效。',data


def use(state,index,*,point=None,second=None,direction=None,delay=None):
    if not 0<=index<len(state.inventory): return ActionResult(False,FAIL[1])
    item=state.inventory[index]
    if item.definition_id=='expansion.sound.x03' and delay is None:
        if not known(state,point,open=True):return ActionResult(False,FAIL[1])
        from .entities import WorldEvent
        state.close_event_dialog()
        event=WorldEvent('consumable.'+item.instance_id,item.name,state.player.x,state.player.y,
            '选择响铃延迟；取消不消耗。',kind='compound',catalog_id='consumable.choice',bound=True,
            options=tuple(dict(label=f'{n} 回合后响',consumable_choice=dict(instance=item.instance_id,
                point=list(point),delay=n)) for n in (2,4))+(dict(label='取消',leave=True),))
        state.events.append(event);state.open_event_dialog(event)
        return ActionResult(True,event.description,{'consumable_choice':True})
    ok,msg,data=apply(state,item.definition_id,point=point,second=second,direction=direction)
    if not ok:return ActionResult(False,msg)
    if item.definition_id=='expansion.sound.x03' and delay in (2,4):
        record=records(state)[-1];record['data']['offsets']=[delay];record['turns']=delay+1
    # A nested native action (reload/fire) already pays its own action time.
    state._consume_inventory_item(index)
    state.run_stats['items_used']=state.run_stats.get('items_used',0)+1
    if not data.pop('native_action',False): state._action_time(1,ActionKind.USE)
    state.messages.append(msg)
    return ActionResult(True,msg,{'item':item.definition_id,**data})


def sound(s,p,q,d,n):
    if n in (1,3,5):
        if not known(s,p,open=True): return FAIL
        offsets={1:[0,1,3,6],3:[2],5:[0,2,4]}[n]
        register(s,'sound',p,max(offsets)+1,offsets=offsets,elapsed=-1,radii=[8,5,11] if n==5 else [8])
    elif n==2:
        candidates=[i for i in s.inventory if i.category in ('惯用物','交互道具') and i.effect not in ('explosion','fireburst','expansion_consumable')]
        if not candidates:return FAIL
        register(s,'muffle',(s.player.x,s.player.y),999,instance=candidates[0].instance_id,used=False)
    elif n==4:
        c=s.cell(*p)
        if not (c.doorway or c.wall_kind in ('门','机关门') and not c.solid):return FAIL
        register(s,'acoustic_plug',p,999)
    else:
        points=[(p[0]+i,p[1]) for i in range(3)]
        if not all(known(s,a,open=True) for a in points):return FAIL
        register(s,'applause',p,999,points=[list(a) for a in points])
    return success()


def flash(s,p):
    # Native blindness uses LOS from the actual source and also affects player.
    absorbed=False
    for r in records(s):
        if r['kind']==PREFIX+'film' and (r['x'],r['y'])==p and not r['data'].get('absorbed'):
            r['data']['absorbed']=True;r['data']['delay']=1; absorbed=True;break
    if absorbed:return
    for e in [s.player,*s.enemies]:
        if max(abs(e.x-p[0]),abs(e.y-p[1]))<=3 and s._has_line_of_sight(*p,e.x,e.y):
            s._apply_direct_portent(e,'blinded',1,mode='max')


def light(s,p,q,d,n):
    if n==2:flash(s,p); return success()
    if n==6:
        register(s,'film',p,999,absorbed=False);return success()
    if n==3:
        # Only the carried lamp source is narrowed by the filter hook.
        if carried_lamp(s) is None:return FAIL
        register(s,'carried_hood',p,3);return success()
    c=s.cell(*p)
    if n==1 and c.light_radius<=0:return FAIL
    if n in (4,5) and not known(s,p,open=True):return FAIL
    facing=d or getattr(s,'facing',(1,0))
    if not isinstance(facing,(list,tuple)):facing=(1,0)
    radius=c.light_radius if n==1 else (1 if n==4 else 3)
    register(s,'light',p,4 if n==4 else 3,prev_radius=c.light_radius,prev_on=c.light_on,
             radius=radius,cone=n in (1,5),direction=list(facing))
    c.light_radius=radius;c.light_on=True
    if n==5:emit(s,p,8)
    return success()


def absorb(s,p,capacity,kind):
    c=s.cell(*p)
    if c.liquid<=0 or not c.liquid_kind or not known(s,p,open=True):return FAIL
    take=min(capacity,c.liquid); material=c.liquid_kind
    c.liquid-=take
    if c.liquid==0:c.liquid_kind=''
    s._sync_material_position(*p)
    register(s,kind,p,999,stored=take,capacity=capacity,material=material)
    return success(stored=take,material=material)


def terrain(s,p,q,d,n):
    if n in (1,5):return absorb(s,p,16 if n==1 else 32,'wet_brick' if n==1 else 'reservoir')
    if n==2:
        a=(s.player.x+d[0],s.player.y+d[1]); b=(a[0]+d[0],a[1]+d[1])
        if not known(s,a,open=True) or not known(s,b,open=True):return FAIL
        source=s.cell(*a); target=s.cell(*b)
        if source.gas<=0 or (target.gas and target.gas_kind!=source.gas_kind):return FAIL
        take=min(16,source.gas,100-target.gas)
        if take<=0:return FAIL
        target.gas_kind=source.gas_kind;target.gas+=take;source.gas-=take
        if source.gas==0:source.gas_kind=''
        s._sync_material_position(*a);s._sync_material_position(*b)
        return success(transferred=take)
    if n in (3,6):
        points=[(p[0]+i,p[1]) for i in range(3)]
        if not all(known(s,a,open=True) for a in points):return FAIL
        stock=[[x,y,s.cell(x,y).elevation] for x,y in points]
        for i,(x,y,old) in enumerate(stock):s.cell(x,y).elevation=old-1-(i if n==3 else 0)
        register(s,'drain',p,3,terrain=stock)
        return success()
    # Damaged physical vessels are native low walls holding real liquid.
    c=s.cell(*p)
    if c.wall_kind not in ('记忆容器','思绪容器') or not 0<c.integrity<100 or c.liquid<=0:return FAIL
    from .tamper_protection import liquid_reason, _facility_cells
    if liquid_reason(c.liquid_kind) or p in _facility_cells(s):return FAIL
    register(s,'container_seal',p,3,old_integrity=c.integrity,wall=c.wall_kind)
    c.integrity+=20
    return success()


def projectile(s,p,q,d,n,keep=0):
    from .firing_sources import reload_quote
    guns=[]
    for i in s.inventory:
        if i.effect=='expansion_consumable':continue
        if i.magazine is not None:guns.append(i)
    if n==1:
        gun=next((i for i in guns if (reload_quote(i) is not None and reload_quote(i).can_start and (i.reload_paid or s.imagination>=reload_quote(i).cost))),None)
        if gun is None:return FAIL
        result=s.reload_weapon_step(gun.instance_id)
        return (True,result.message,{'native_action':True}) if result.changed else FAIL
    if n==2:
        if not known(s,p,open=True) or s.entity_at(*p):return FAIL
        register(s,'mirror',p,999,direction=[1,0]);return success()
    if n==3:
        gun=next((i for i in guns if (i.magazine or 0)>0),None)
        if gun is None:return FAIL
        gun.magazine-=1;emit(s,(s.player.x,s.player.y),10);return success(ammunition=1)
    if n==4:
        from .ballistics import trace_path
        path=trace_path(s.player.x,s.player.y,*d,6)
        for x,y in path:
            if not s.inside_board(x,y) or not s.is_visible(x,y):break
            c=s.cell(x,y)
            if c.solid:
                if c.thickness>1 or item_targeting.protected_cell(s,x,y):return FAIL
                register(s,'paper_pin',(x,y),3);emit(s,(x,y),3);return success(mark=[x,y])
        return FAIL
    if n==5:
        gun=next((i for i in guns if (i.magazine or 0)>0),None)
        if gun is None:return FAIL
        rounds=gun.magazine
        # 留一发（洞察「不白退一发」）：只对**真实剩下的弹**生效，一支只剩一发的
        # 弹匣留不下东西（``keep`` 夹到 ``rounds - 1``，绝不会凭空多出一发）。
        held=max(0,min(int(keep or 0),rounds-1))
        fired=rounds-held
        # Fire each real remaining round through native collision rules; cap
        # branching to three rays while spending the entire actual magazine.
        from .firing_sources import collect_firing_sources
        choices=[v for v in collect_firing_sources(s) if gun.instance_id in v.instance_ids and v.can_fire]
        choice=choices[0].choice_key if choices else None
        if choice is None:return FAIL
        for dx,dy in (d,(-d[1],d[0]),(d[1],-d[0]))[:min(3,fired)]:s.fire(dx,dy,choice=choice)
        gun.magazine=held
        return success(ammunition=fired,kept=held,native_action=True)
    # Return reservation is finite and claimed by the next real shot.
    if not any((i.magazine or 0)>0 for i in guns):return FAIL
    register(s,'return',p,999)
    return success()


def circuit(s,p,q,d,n):
    if n==1:
        if max(abs(p[0]-q[0]),abs(p[1]-q[1]))!=1:return FAIL
        from .tamper_protection import _facility_cells
        if s.realm_id=='toy_memories' or any(a in _facility_cells(s) for a in (p,q)):return FAIL
        a=s.circuit_node_at(*p);b=s.circuit_node_at(*q)
        if a is None or b is None or a[0] is not b[0]:return FAIL
        # Native bridge must connect one real output to a compatible input.
        if a[2]['op']=='output' or b[2]['op'] not in ('and','or'):return FAIL
        old=list(b[2].get('inputs',[]))
        if a[1] in old:return FAIL
        b[2]['inputs']=[a[1]]
        from ..circuit_schema import validate_board
        try:order=validate_board(a[0],s.width,s.height)
        except (ValueError,KeyError):b[2]['inputs']=old;return FAIL
        a[0]['order']=order;s._settle_circuit(a[0])
        register(s,'bridge',p,3,second=list(q),old_inputs=old)
        return success()
    if n==2:return absorb(s,(s.player.x,s.player.y),12,'dry_powder')
    if n==4:
        c=s.cell(*p)
        if not known(s,p,open=True) or c.flame or c.liquid<=0 or c.liquid_kind not in ('水','稀释记忆','水银'):return FAIL
        if c.phase_stock:return FAIL
        material,amount=c.liquid_kind,c.liquid
        c.phase_stock=dict(form='ice',kind=material,amount=amount,base_floor=c.aggregate_variant)
        c.aggregate_variant='冰面';c.liquid=0;c.liquid_kind='';s._sync_material_position(*p)
        return success(crystallized=amount)
    if n==6:
        from ..materials.reactions import REACTIONS
        from .tamper_protection import liquid_reason
        c=s.cell(*p)
        if not known(s,p,open=True) or liquid_reason(c.liquid_kind):return FAIL
        if not c.liquid or not c.gas:return FAIL
        if not any({r.reactant_a,r.reactant_b}=={c.liquid_kind,c.gas_kind} for r in REACTIONS):return FAIL
        register(s,'reactor_seal',p,3,liquid=c.liquid,liquid_kind=c.liquid_kind,
                 gas=c.gas,gas_kind=c.gas_kind)
        c.liquid=c.gas=0;c.liquid_kind=c.gas_kind='';s._sync_material_position(*p)
        return success()
    hit=s.circuit_node_at(*p)
    if hit is None or s.realm_id=='toy_memories':return FAIL
    board,key,node=hit
    if n==3:
        if node['op']!='pulse':return FAIL
        # One genuine pulse lasts one extra turn; no output rewards are reset.
        board['state'].setdefault('pulses',{})[key]=s.time+2
        s._settle_circuit(board,player_inputs={key})
        return success()
    if n==5:
        if node['op'] not in ('pulse','step','toggle'):return FAIL
        s._circuit_signal(*p,by_player=True);return success()
    return FAIL


def realm(s,p,q,d,n):
    if n in (1,3):
        ids=[pid for pid,value in s.player.portent_attach.items() if value>0 and portent_def(pid) and portent_def(pid).washable]
        if not ids:return FAIL
        pid=sorted(ids)[0];amount=min(8,s.player.portent_attach[pid]);s.player.portent_attach[pid]-=amount
        register(s,'waste_bag' if n==1 else 'nursing',p,999 if n==1 else 3,material=pid,stored=amount,baseline=s.mind+s.lucidity)
        return success(material=pid,stored=amount)
    if n==2:
        c=s.cell(*p)
        from .tamper_protection import _facility_cells
        if p in _facility_cells(s) or s.circuit_node_at(*p) or not wall_def(c.wall_kind).pushable or c.height>2:return FAIL
        register(s,'brace',p,999);return success()
    if n==4:
        eligible=[]
        for pid,t in s.player.portents.items():
            spec=portent_def(pid)
            if t>0 and spec and spec.mind>=0 and spec.lucidity>=0 and 'teleport' not in pid and pid not in ('blink','free_action','invigorated'):
                eligible.append(pid)
        if len(eligible)<2:return FAIL
        a,b=sorted(eligible)[:2];s.player.portents[a]-=1;s.player.portents[b]+=1
        return success(source=a,target=b)
    if n==5:
        # Recovery-in-flight is represented by the native lucidity regen timer;
        # matching debt must be present, and paid immediately through settlement.
        turns=int(s.player.portents.get('invigorated',0))
        debt=next((r for r in s.drug_debts if r['remaining']>0 and r['resource']=='lucidity'),None)
        if turns<=0 or debt is None:return FAIL
        from .settlement import settle_delta,REASON_DRUG_DEBT
        amount=int(debt['remaining']);s.restore_resource('lucidity',turns//2,source='出院单')
        settle_delta(s,'lucidity',-amount,reason=REASON_DRUG_DEBT,source='出院单结清',channel='drug_debt')
        debt['remaining']=0;s.player.portents.pop('invigorated',None)
        return success(paid=amount)
    if s.depth<28 or not all(known(s,a,open=True) for a in (p,q)):return FAIL
    from .vision.knowledge import cell_knowledge
    if not all(cell_knowledge(s,*a).explored for a in (p,q)):return FAIL
    if any(s.entity_at(*a) for a in (p,q)):return FAIL
    item_devices.register_device(s,'escape',*p,999,a=list(p),b=list(q),uses=2)
    return success()


def block_push(s,x,y):
    for r in records(s):
        if r['kind']==PREFIX+'brace' and (r['x'],r['y'])==(x,y) and not r['data'].get('spent'):
            r['data']['spent']=True;r['turns']=0;return True
    return False


def pierce_loan(s):
    """「压膛」借给下一发的穿透：读数在，等下一发真开火时领走。"""
    return max((int(r['data'].get('amount',0)) for r in records(s)
                if r['kind']==PREFIX+'pierce_loan' and not r['data'].get('spent')),default=0)


def spend_pierce_loan(s):
    """领走借来的穿透；没有就什么都不做（每发只领一次）。"""
    for r in records(s):
        if r['kind']==PREFIX+'pierce_loan' and not r['data'].get('spent'):
            r['data']['spent']=True
            r['turns']=0
            return int(r['data'].get('amount',0))
    return 0


def reflection(s,x,y,d):
    for r in records(s):
        if r['kind']==PREFIX+'mirror' and (r['x'],r['y'])==(x,y) and not r['data'].get('spent'):
            r['data']['spent']=True;r['turns']=0;return (-d[0],d[1]) if d[0] else (d[0],-d[1])
        if r['kind']==PREFIX+'return' and max(abs(x-s.player.x),abs(y-s.player.y))>=3 and not s.cell(x,y).solid and not r['data'].get('spent'):
            r['data']['spent']=True;r['turns']=0;return (-d[0],-d[1])
    return None


def light_allows(s,sx,sy,x,y):
    for r in records(s):
        if r['kind']==PREFIX+'light' and r['data'].get('cone') and (r['x'],r['y'])==(sx,sy):
            dx,dy=r['data']['direction'];vx,vy=x-sx,y-sy
            return vx*dx+vy*dy>=abs(vx*dy-vy*dx)
        if r['kind']==PREFIX+'carried_hood' and (sx,sy)==(s.player.x,s.player.y):
            if carried_lamp(s) is not None:
                dx,dy=s.facing;vx,vy=x-sx,y-sy
                return vx*dx+vy*dy>=abs(vx*dy-vy*dx)
    # 「裁光」构想：光源格的照明被收成一条扇区。场到期即失效，照明自动恢复，
    # 灯的半径与耗能全程不动——这也是那条构想「灯本身仍耗能」的落点。
    from .construct_environments import narrow_light_direction
    direction=narrow_light_direction(s,sx,sy)
    if direction is not None:
        dx,dy=direction;vx,vy=x-sx,y-sy
        return vx*dx+vy*dy>=abs(vx*dy-vy*dx)
    return True


def carried_lamp(s):
    from ..equipment import gear_light
    for ident, mark in ((gear_light.BEAM_LAMP,'beam'),(gear_light.HALF_LAMP,'lamp')):
        item=gear_light._item_of(s,ident)
        if item is not None and gear_light._mark(s,item,mark):return item
    return None


def acoustic_cost(s,x,y):
    return 6 if any(r['kind']==PREFIX+'acoustic_plug' and (r['x'],r['y'])==(x,y) and not s.cell(x,y).flame for r in records(s)) else 0


def tool_unseal(s,item):
    for r in records(s):
        if r['kind']==PREFIX+'muffle' and r['data']['instance']==item.instance_id and r['data'].get('used'):
            r['turns']=0;r['data']['instance']=''
            s._action_time(1,ActionKind.USE)
            return ActionResult(True,'拆掉了已用的厚毡封套；工具现在可以使用。')
    return None


def tool_noise(s,item,radius):
    for r in records(s):
        if r['kind']==PREFIX+'muffle' and r['data']['instance']==item.instance_id and not r['data'].get('used'):
            r['data']['used']=True
            return max(1,int(radius)-3)
    return radius


def on_collision(s):
    for r in records(s):
        if r['kind']==PREFIX+'applause' and r['data']['points']:
            emit(s,tuple(r['data']['points'].pop(0)),10)
            if not r['data']['points']:r['turns']=0
            break


def tick_record(s,r):
    if not str(r.get('kind','')).startswith(PREFIX):return None
    k=r['kind'][len(PREFIX):];a=r['data'];p=(r['x'],r['y']);c=s.cell(*p)
    if k in ('wet_brick','reservoir','dry_powder','waste_bag','paper_pin','pierce_loan'):
        return True
    r['turns']-=1
    if k=='sound':
        a['elapsed']+=1
        if c.solid or c.flame:return False
        if a['elapsed'] in a['offsets']:
            idx=a['offsets'].index(a['elapsed']);emit(s,p,a['radii'][idx%len(a['radii'])])
    elif k=='film' and a.get('absorbed'):
        a['delay']-=1
        if a['delay']<=0:flash(s,p);return False
    elif k=='nursing':
        if s.mind+s.lucidity<a['baseline']:return False
        s.restore_resource('mind',1,source='护理包');a['baseline']=s.mind+s.lucidity
    elif k=='container_seal':
        if c.wall_kind!=a['wall']:return False
        if c.flame or r['turns']<=0:
            c.integrity=min(c.integrity,a['old_integrity']);return False
    elif k=='reactor_seal':
        for attr in ('liquid','gas'):
            if getattr(c,attr)>0 and getattr(c,attr+'_kind')==a[attr+'_kind']:
                a[attr]+=getattr(c,attr);setattr(c,attr,0);setattr(c,attr+'_kind','')
        if c.flame or r['turns']<=0:
            for attr in ('liquid','gas'):
                released=item_devices._deposit(s,*p,a[attr+'_kind'],a[attr],attr)
                a[attr]-=released
            return bool(a['liquid'] or a['gas'])
    elif k in ('acoustic_plug','mirror','brace') and c.flame:return False
    elif k=='vent':
        # 「开气窗」：这一段的气体阻力短时下降——本作把它落成真的被抽走
        # （3×3 各 2 单位/回合）。不改 `materials_sim` 的消散规则，也不碰墙。
        drained=False
        for yy in range(r['y']-1,r['y']+2):
            for xx in range(r['x']-1,r['x']+2):
                if not s.inside_board(xx,yy):continue
                other=s.cell(xx,yy)
                if other.gas<=0:continue
                other.gas-=min(2,other.gas)
                if other.gas==0:other.gas_kind=''
                drained=True
        if drained:s._material_index_ready=False
        if r['turns']<=0:return False
        return True
    if r['turns']>0:return True
    if k=='light':c.light_radius=a['prev_radius'];c.light_on=a['prev_on']
    elif k=='drain':
        for x,y,old in a['terrain']:s.cell(x,y).elevation=old
    elif k=='bridge':
        hit=s.circuit_node_at(*a['second'])
        if hit:hit[2]['inputs']=a['old_inputs'];s._settle_circuit(hit[0])
    return False


HANDLERS={f'expansion.{family}.x{n:02d}':(lambda s,p,q,d,fn=fn,n=n:fn(s,p,q,d,n))
          for family,fn in [('sound',sound),('light',light),('terrain',terrain),('projectile',projectile),('circuit',circuit),('realm',realm)] for n in range(1,7)}
