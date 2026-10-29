"""Physical tools for the six expansion themes.

All durable operation records live in the existing equipment mark/realm ledgers.
Queries reject unknown cells; material operations debit a real source only after
the destination has been validated. Active tools still require board placement
and spend an action through actions.items, never here.
"""
from __future__ import annotations

from dataclasses import asdict
from ..i18n import tr


def _key(item):
    return 'remaining_gear:' + item.instance_id


def _record(s, item):
    return s.equipment_marks.get(_key(item), {})


def _put(s, item, **data):
    s.equipment_marks[_key(item)] = {**_record(s, item), **data}


def _p(item, key, default):
    """逐件数值来自目录 ``tuning_proposal.equipment_roles.primary``。

    代码里的数字只是**默认值**：调平衡改目录，不改逻辑。缺键、非数字、
    目录还没接线的旧存档一律退回默认值，绝不因为一条数值抛异常。
    """
    from ..data.items import ITEM_DEFINITIONS
    params = ITEM_DEFINITIONS.get(item.definition_id, {}).get('runtime_primary_params') or {}
    try:
        return int(params.get(key, default))
    except (TypeError, ValueError):
        return default


def _by_instance(s, instance_id):
    return next((obj for obj in s.inventory if obj.instance_id == instance_id), None)


def _passive(item, text):
    """被动件被点「使用」时给出确切原因，而不是笼统的「没有符合条件的对象」。"""
    return False, tr(text, item=tr(item.name)), {}


# 能靠铸模凝成障碍的熔料 → 目标墙种。表里没有的熔料，铸模**当场拒绝**，
# 不接住再静默失败（描述写的是「接住后缓慢凝固为障碍」，凝不成就没接住）。
MOLD_WALLS = {'熔融蜡烛': '蜡化记忆墙'}

# 真实恢复品类：拆分/封存只认这些 effect，免得把增益也拆成分期剂量。
RESTORE_EFFECTS = frozenset({'restore_mind', 'restore_lucidity',
                             'restore_imagination', 'restore_split'})


def _yes(item, **data):
    return True, tr('{item}完成了操作。', item=tr(item.name)), data


def _no():
    return False, tr('这里没有符合条件的真实对象；没有消耗。'), {}


def _near(s, p, reach=1):
    return (s.inside_board(*p) and s.is_visible(*p)
            and max(abs(p[0]-s.player.x), abs(p[1]-s.player.y)) <= reach)


def _protected(s, p):
    from ..core.item_targeting import protected_cell
    from ..data.tamper_protection import MECHANISM_WALL_KINDS
    return (protected_cell(s, *p) or s.cell(*p).wall_kind in MECHANISM_WALL_KINDS
            or s.cell(*p).wall_kind=='意识边界')


def _mutable(s, p):
    return _near(s,p) and not _protected(s,p)


def _container(s, exclude=None, *, filled=False):
    from ..data.items import ITEM_DEFINITIONS
    for obj in s.inventory:
        if obj is exclude: continue
        spec=ITEM_DEFINITIONS.get(obj.definition_id,{}).get('container') or {}
        if spec.get('medium','liquid')!='liquid' or not spec: continue
        if filled and not obj.contents: continue
        if not filled and sum(obj.contents.values())>=int(spec.get('cap',30)): continue
        return obj, spec
    return None, {}


def _take_liquid(s, p, holder, cap, amount):
    c=s.cell(*p)
    if c.liquid<=0 or not c.liquid_kind: return 0
    kind=c.liquid_kind
    if holder.contents and kind not in holder.contents: return 0
    amount=min(amount,c.liquid,max(0,cap-sum(holder.contents.values())))
    if amount<=0: return 0
    c.liquid-=amount
    if not c.liquid: c.liquid_kind=''
    holder.contents[kind]=holder.contents.get(kind,0)+amount
    s._sync_material_position(*p)
    return amount


def _transfer(s,a,b,amount,*,gas=False):
    ca,cb=s.cell(*a),s.cell(*b)
    field,kindfield=('gas','gas_kind') if gas else ('liquid','liquid_kind')
    kind=getattr(ca,kindfield); count=getattr(ca,field)
    if cb.solid or not kind or count<=0: return 0
    if getattr(cb,field)>0 and getattr(cb,kindfield)!=kind: return 0
    amount=min(amount,count,max(0,100-getattr(cb,field)))
    if amount<=0:return 0
    getattr(s,'_add_gas' if gas else '_add_liquid')(cb,kind,amount)
    setattr(ca,field,count-amount)
    if count==amount:setattr(ca,kindfield,'')
    s._sync_material_position(*a);s._sync_material_position(*b)
    return amount


def _store_item(s, tool, obj, *, name='stored'):
    """Move an actual item into a serializable holder, retaining its identity."""
    if obj is tool or obj.instance_id in s.equipped.values():return False
    state=dict(_record(s,tool)); entries=list(state.get(name,[]))
    entries.append(asdict(obj)); state[name]=entries
    s.equipment_marks[_key(tool)]=state
    s.inventory.remove(obj)
    return True


def _release(s, tool, *, name='stored', ground=None):
    from ..core.entities import Item,WorldItem
    state=dict(_record(s,tool)); entries=list(state.get(name,[]))
    if not entries:return None
    obj=Item(**entries.pop(0)); state[name]=entries
    s.equipment_marks[_key(tool)]=state
    if ground is None:s.inventory.append(obj)
    else:
        w=WorldItem(obj,*ground);w.sync_surface(s.cell(*ground));s.world_items.append(w)
    return obj


def _ground_of(s, tool):
    """这件东西现在真的落在哪一格：掉在地上就用自己的位置，否则用脚下。"""
    for entry in getattr(s,'world_items',()) or ():
        if getattr(getattr(entry,'item',None),'instance_id',None)==tool.instance_id:
            return (entry.x,entry.y)
    return (s.player.x,s.player.y)


def _spill_tray(s, item):
    """护理员的托盘不在盘上时，把里面托着的件按真实位置倒出来。

    行囊里的托盘和**掉在地上的**托盘都要扫：只扫行囊时，掉在地上的那只
    会让两件永远卡在刻痕里——既不在行囊也不在场地上。
    """
    if str(item.definition_id or '')[-3:]!='e06':return
    if not str(item.definition_id or '').startswith('expansion.realm.'):return
    record=_record(s,item)
    if not record.get('stored') or item.instance_id in s.equipped.values():return
    ground=_ground_of(s,item)
    for _ in range(len(tuple(record.get('stored') or ()))):
        _release(s,item,ground=ground)


def use(s,item,active,target):
    if int(_record(s,item).get('recovery_until',0))>int(s.time):return _no()
    family=item.definition_id.split('.')[1]; n=int(item.definition_id[-2:])
    if target is not None:
        pair=isinstance(target[0],(list,tuple))
        points=target if pair else (target,)
        if any(not _near(s,tuple(p),12) for p in points): return _no()
    handler={'terrain':_terrain,'circuit':_circuit,'realm':_realm,
             'projectile':_projectile}.get(family)
    if handler is None:return _no()
    result=handler(s,item,n,target)
    if result[0] and family=='circuit':
        s.equipment_marks['gear_circuit_operation_until']=int(s.time)+1
    return result


def _terrain(s,item,n,p):
    if n in {2,8,10}:
        if not _near(s,p):return _no()
        holder,spec=(item,{'cap':_p(item,'cap',24)}) if n==10 else _container(s,item,filled=n==8)
        if holder is None:return _no()
        if n==8:
            # Straw transfers only the currently accessible, already mixed liquid.
            if len(holder.contents)>1:
                # 目录契约：容器里混了两种以上就不动，不做混合前的凭空分离。
                return False, tr('{item}只吸得到最上面那一种——瓶里混着好几种，它分不开。',
                                 item=tr(item.name)), {}
            kind=next(iter(holder.contents),None)
            if kind is None:return _no()
            c=s.cell(*p)
            if c.solid or (c.liquid and c.liquid_kind!=kind):return _no()
            amount=min(_p(item,'amount',4),holder.contents[kind],100-c.liquid)
            if amount<=0:return _no()
            s._add_liquid(c,kind,amount);holder.contents[kind]-=amount
            if not holder.contents[kind]:del holder.contents[kind]
        else:
            amount=_take_liquid(s,p,holder,int(spec.get('cap',30)),
                                _p(item,'amount',4) if n==2 else _p(item,'fill',24))
            if not amount:return _no()
        return _yes(item,amount=amount,container=holder.instance_id)
    if n==3:
        if not _near(s,p):return _no()
        delta=s.cell(*p).elevation-s.cell(s.player.x,s.player.y).elevation
        return _yes(item,elevation_delta=delta)
    if n in {4,11}:
        if not _near(s,p):return _no()
        if _record(s,item).get('stored'):
            pos=_record(s,item).get('mount')
            if pos!=list(p):return _no()
            obj=_release(s,item);return _yes(item,retrieved=obj.instance_id)
        from ..materials import SURFACE_KINDS
        if s.cell(*p).wall_kind not in SURFACE_KINDS:return _no()
        if n==4:obj,_=_container(s,item)
        else:obj=next((o for o in s.inventory if o is not item and o.slot=='惯用物'
                       and o.instance_id not in s.equipped.values()),None)
        if obj is None or not _store_item(s,item,obj):return _no()
        _put(s,item,mount=list(p),support=s.cell(*p).wall_kind,layer=s.layer_key())
        return _yes(item,mounted=obj.instance_id)
    if n==5:
        return _passive(item,'{item}是被动的：脚更沉（每次移动多付时间），'
                             '没有可以直接做的动作。')
    if n==6:
        a,b=map(tuple,p)
        steps=_p(item,'steps',1)
        if a==b or not all(_mutable(s,pos) and not s.cell(*pos).solid for pos in (a,b)):
            return _no()
        if s.cell(*a).elevation-steps<-2 or s.cell(*b).elevation+steps>2:return _no()
        s.cell(*a).elevation-=steps;s.cell(*b).elevation+=steps
        return _yes(item,soil_moved=steps)
    if n in {7,9,13,15}:
        a,b=map(tuple,p)
        if not all(_mutable(s,pos) for pos in (a,b)) or max(abs(a[0]-b[0]),abs(a[1]-b[1]))>1:
            return _no()
        if n==7:
            from ..materials import SURFACE_KINDS
            if s.cell(*a).wall_kind not in SURFACE_KINDS:return _no()
            if s.cell(*b).elevation>=s.cell(*a).elevation+s.cell(*a).height:return _no()
        if n==13:
            cost=_p(item,'cost',1)
            if s.imagination<cost or s.cell(*b).elevation<=s.cell(*a).elevation:return _no()
            moved=_transfer(s,a,b,_p(item,'amount',8))
            if not moved:return _no()
            s._pay_ability_cost(cost);return _yes(item,amount=moved)
        _put(s,item,flow=dict(source=list(a),outlet=list(b),gas=n==9,
                             split=n==15,layer=s.layer_key(),
                             remaining=_p(item,'flow_turns',6),
                             amount=_p(item,'amount',2 if n==15 else 4)))
        return _yes(item,outlet=list(b))
    if n==12:
        target=s.entity_at(*p)
        if not _near(s,p) or target is None or target is s.player:return _no()
        return _needle(s,item,target)
    if n==16:
        a,b=map(tuple,p)
        if max(abs(a[0]-b[0]),abs(a[1]-b[1]))!=1:return _no()
        if not all(_mutable(s,pos) and not s.cell(*pos).solid for pos in (a,b)):return _no()
        record=_record(s,item)
        if record.get('barrier'):
            if record.get('layer')!=s.layer_key() or record.get('barrier')!=[list(a),list(b)]:return _no()
            _put(s,item,barrier=None);return _yes(item,recovered=not record.get('damaged',False))
        # 承压损坏是**这件东西**的损失，不是这一段的：重立一段也收不回完整的。
        _put(s,item,barrier=[list(a),list(b)],layer=s.layer_key(),pressure=0,
             damaged=bool(record.get('damaged',False)))
        return _yes(item,boundary=[list(a),list(b)])
    return _no()


def _needle(s,item,target):
    from ..materials import PORTENT_DEFINITIONS
    for name,amount in list(target.portent_attach.items()):
        definition=PORTENT_DEFINITIONS.get(name)
        material=getattr(definition,'material','') if definition else ''
        if not material or amount<=0:continue
        from ..materials import LIQUID_DEFINITIONS
        if material not in LIQUID_DEFINITIONS:continue
        dest=(s.player.x,s.player.y)
        flung=min(_p(item,'portents',1),amount)
        target.portent_attach[name]=amount-flung
        s._add_liquid(s.cell(*dest),material,flung)
        s._grant_material_portents(s.player,s.cell(*dest))
        s._player_strike(target,'melee',damage=1)
        return _yes(item,material=material,amount=flung)
    return _no()


def _circuit(s,item,n,p):
    if n in {2}:return _passive(item,'{item}是被动的：只在你操作电路那一次少沾一份液面。')
    if n==14:
        p=(s.player.x,s.player.y) if p is None else tuple(p)
        if not _near(s,p) or s.cell(*p).solid:return _no()
        if item.contents:
            if int(_record(s,item).get('closed_until',0))>s.time:return _no()
            for kind,amount in tuple(item.contents.items()):s._add_liquid(s.cell(*p),kind,amount)
            item.contents.clear();return _yes(item,opened=True)
        holder,_=_container(s,item,filled=True)
        if holder is None:return _no()
        cap=_p(item,'cap',8);total=0
        for kind,amount in tuple(holder.contents.items()):
            taken=min(cap-total,amount)
            if taken<=0:break
            item.contents[kind]=taken;holder.contents[kind]-=taken;total+=taken
            if holder.contents[kind]==0:del holder.contents[kind]
        _put(s,item,closed_until=int(s.time)+_p(item,'seal_turns',1))
        return _yes(item,isolated=total)
    if n in {8,15}:
        a,b=map(tuple,p)
        if not all(_near(s,pos) for pos in (a,b)):return _no()
        if abs(a[0]-b[0])+abs(a[1]-b[1])!=1:return _no()
        if any(s.circuit_node_at(*pos) for pos in (a,b)):return _no()
        if not (s._conductive_cell(s.cell(*a)) and s._conductive_cell(s.cell(*b))):return _no()
        if n==8:
            solder=int(_record(s,item).get('solder',_p(item,'solder',6)))
            if solder<=0:return _no()
            s.lay_wire_path([a,b]);_put(s,item,solder=solder-1)
            return _yes(item,solder_spent=1)
        # One physical fork chooses exactly one outgoing neighboring branch.
        record=_record(s,item); old=record.get('fork')
        if old and old.get('layer')==s.layer_key():
            _remove_wire_edge(s,tuple(old['a']),tuple(old['b']))
        s.lay_wire_path([a,b]);_put(s,item,fork=dict(a=list(a),b=list(b),layer=s.layer_key()))
        return _yes(item,connected=[list(a),list(b)])
    if p is None:p=(s.player.x,s.player.y)
    p=tuple(p)
    if not _near(s,p):return _no()
    from ..core.tamper_protection import _facility_cells
    if p in _facility_cells(s) and n in {3,9,11,16}:return _no()
    c=s.cell(*p)
    if n==1:
        if not s._conductive_cell(c):return _no()
        seen=[list(pos) for pos in ((p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1))
              if _near(s,pos,2) and s._conductive_cell(s.cell(*pos))]
        if p in s.electric_field_cells():
            # 接触风险走真实征兆（过电），不另造状态：电场里的针柄会把手也带进去。
            s._apply_direct_portent(s.player,'charged',_p(item,'shock_turns',1),mode='max')
            return True, tr('{item}探到一跳——电场顺着针柄过了一遍手。',item=tr(item.name)), {
                'connected':seen,'shocked':True}
        return _yes(item,connected=seen)
    if n==3:
        if not c.wire or s.circuit_node_at(*p):return _no()
        # Named nets are protected, including their intermediate traces.
        if any(list(p) in net['path'] for board in s.circuit_boards for net in board['nets']):return _no()
        old=c.wire
        for bit,dx,dy,back in ((1,0,-1,4),(2,1,0,8),(4,0,1,1),(8,-1,0,2)):
            q=(p[0]+dx,p[1]+dy)
            if old&bit and s.inside_board(*q):s.cell(*q).wire &= ~back
        c.wire=0;item.contents['导线']=item.contents.get('导线',0)+1
        return _yes(item,salvaged=1)
    if n==5:
        node=s.circuit_node_at(*p)
        if not node or node[2]['op'] not in {'pulse','step','toggle'}:return _no()
        if not s._circuit_signal(*p,by_player=True):return _no()
        return _yes(item,signal=list(p))
    if n in {6,13}:
        node=s.circuit_node_at(*p)
        if not node or node[2]['op'] not in {'pulse','step','toggle'}:return _no()
        _put(s,item,relay=dict(pos=list(p),layer=s.layer_key(),mode='delay' if n==6 else 'rhythm',
                             remaining=_p(item,'remaining',8),observations=[]))
        return _yes(item,armed=list(p))
    if n==9:
        if _protected(s,p) or not c.solid or c.integrity<=1:return _no()
        from ..materials import wall_def
        if wall_def(c.wall_kind).projectile_immune:return _no()
        c.integrity-=1;item.contents['固体碎屑']=item.contents.get('固体碎屑',0)+1
        return _yes(item,salvaged=1)
    if n==10:
        cap=_p(item,'cap',8)
        if sum(item.contents.values())>=cap:return _no()
        holder,_=_container(s,item,filled=True)
        if holder is None:return _no()
        committed=_record(s,item).get('filter_kind')
        if committed is None:
            if len(holder.contents)<2:
                return False, tr('{item}还没定下要滤哪一种杂质——容器里至少要有两种液体。',
                                 item=tr(item.name)), {}
            committed=sorted(holder.contents)[-1]
            _put(s,item,filter_kind=committed)
        amount=holder.contents.get(committed,0)
        if amount<=0:return _no()
        holder.contents[committed]-=1
        if holder.contents[committed]<=0:del holder.contents[committed]
        item.contents[committed]=item.contents.get(committed,0)+1
        return _yes(item,filtered=committed)
    if n in {11,16}:
        if _protected(s,p):return _no()
        holder,_=_container(s,item,filled=True)
        if not holder:return _no()
        kind=next((k for k in holder.contents if '熔' in k),None)
        if not kind:return _no()
        if n==11:
            if kind not in MOLD_WALLS:
                return False, tr('{item}接不住{material}——它凝不成障碍，所以没有接住。',
                                 item=tr(item.name), material=tr(kind)), {}
            if c.solid or s.entity_at(*p) or c.liquid:return _no()
            amount=min(_p(item,'amount',10),holder.contents[kind]);holder.contents[kind]-=amount
            if not holder.contents[kind]:del holder.contents[kind]
            s._add_liquid(c,kind,amount)
            _put(s,item,mold=dict(pos=list(p),material=kind,amount=amount,
                                  remaining=_p(item,'turns',2),layer=s.layer_key()))
            return _yes(item,molten=amount)
        target=s.entity_at(*p)
        if target is None or target is s.player:return _no()
        holder.contents[kind]-=1
        if not holder.contents[kind]:del holder.contents[kind]
        s._add_liquid(c,kind,1);s._player_strike(target,'melee',damage=_p(item,'damage',2))
        return _yes(item,deposited=1)
    return _no()


def _remove_wire_edge(s,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    bits={(0,-1):(1,4),(1,0):(2,8),(0,1):(4,1),(-1,0):(8,2)}
    if (dx,dy) in bits:
        u,v=bits[(dx,dy)];s.cell(*a).wire &= ~u;s.cell(*b).wire &= ~v


def _realm(s,item,n,p):
    here=(s.player.x,s.player.y)
    if n in {1,5}:
        from ..materials import PORTENT_DEFINITIONS
        if n==5 and sum(item.contents.values())>=_p(item,'cap',8):
            # 废料格不是容器（这件 effect 不是 container，开不出倒出浮层），
            # 所以这里不能叫玩家「先倒掉」——那一趟的容量就是终局。
            return False, tr('{item}的废料格满了——这一趟夹不了新的了。',
                             item=tr(item.name)), {}
        # 只剥「带真实材料」的负面附着：纯状态类（致盲等）没有可剥离物。
        for key in sorted(s._washable_negative_portents(s.player)):
            amount=s.player.portent_attach.get(key,0)
            definition=PORTENT_DEFINITIONS.get(key)
            material=getattr(definition,'material','') if definition else ''
            if amount<=0 or not material:continue
            s.player.portent_attach[key]=amount-1
            if n==1:s.lucidity=max(1,s.lucidity-_p(item,'cost',1))
            else:item.contents[material]=item.contents.get(material,0)+1
            return _yes(item,peeled=key)
        return False, tr('{item}没有可剥离的负面附着——只有带真实材料的那种刮得下来。',
                         item=tr(item.name)), {}
    if n in {4,6,8,13}:
        record=_record(s,item)
        entries=list(record.get('stored',[]))
        slots=_p(item,'slots',2)
        if n==13 and len(entries)>=slots:
            dose=entries[0]
            resource='imagination' if 'imagination' in (dose.get('effect') or '') else 'mind' if 'mind' in (dose.get('effect') or '') else 'lucidity'
            _put(s,item,delayed_dose=dict(resource=resource,amount=max(1,int(dose['power'])),
                                         due=int(s.time)+_p(item,'delay',2),layer=s.layer_key()))
            dose['quantity']-=1
            if dose['quantity']<=0:entries.pop(0)
            _put(s,item,stored=entries)
            return _yes(item,delayed=True)
        if entries and (n==4 or (n==6 and len(entries)>=slots)):
            obj=_release(s,item);return _yes(item,retrieved=obj.instance_id)
        if n==6 and len(entries)>=slots:
            return False, tr('{item}只托得住 {n} 件——先取走一件。',
                             item=tr(item.name), n=slots), {}
        from ..data.items import ITEM_DEFINITIONS
        candidates=[]
        for obj in s.inventory:
            if obj is item or obj.instance_id in s.equipped.values():continue
            d=ITEM_DEFINITIONS.get(obj.definition_id,{})
            if n==4 and d.get('effect')!='learn_ability':continue
            if n in {8,13} and obj.effect not in RESTORE_EFFECTS:continue
            candidates.append(obj)
        if not candidates:
            text=('{item}包不住——行囊里没有可包的学习物。' if n==4
                  else '{item}里没有可拆的恢复品——得先有一份真实的。')
            return False, tr(text, item=tr(item.name)), {}
        obj=candidates[0]
        if n==8:
            # One unit, one total dose, split without creating a second item.
            resource='imagination' if 'imagination' in obj.effect else 'mind' if 'mind' in obj.effect else 'lucidity'
            dose=max(1,int(obj.power));_put(s,item,infusion=dict(resource=resource,total=dose,
                remaining=dose,turns=_p(item,'turns',3),origin=list(here),layer=s.layer_key()))
            if obj.quantity>1:obj.quantity-=1
            else:s.inventory.remove(obj)
            return _yes(item,infusion=dose)
        if not _store_item(s,item,obj):return _no()
        return _yes(item,stored=obj.instance_id)
    if n==9:
        from ..data.abilities import ABILITY_DEFINITIONS
        known=[a for a in s.abilities if a in ABILITY_DEFINITIONS]
        if len(known)<2:return _no()
        index=(int(_record(s,item).get('index',-1))+1)%len(known)
        _put(s,item,index=index)
        pair=[known[index],known[(index+1)%len(known)]]
        rows=[dict(id=a,cost=ABILITY_DEFINITIONS[a].get('cost',0),
                   cooldown=s.ability_cooldowns.get(a,0)) for a in pair]
        left,right=rows
        # 这件的作用就是「给出成本对照」——对照必须出现在玩家看得见的那句话里，
        # 只塞进 data 等于什么都没给。
        return True, tr('{item}翻到背面：{a}（费 {ca}／冷 {cda}）对 {b}（费 {cb}／冷 {cdb}）。',
                        item=tr(item.name),
                        a=tr(ABILITY_DEFINITIONS[left['id']]['name']),
                        ca=left['cost'], cda=left['cooldown'],
                        b=tr(ABILITY_DEFINITIONS[right['id']]['name']),
                        cb=right['cost'], cdb=right['cooldown']), {'comparison':rows}
    if n==3:
        length=_p(item,'length',5)
        if p is None or not _near(s,p,length):return _no()
        # Use the canonical ray if available, without ever marking hidden terrain.
        cells=[];dx=(p[0]>here[0])-(p[0]<here[0]);dy=(p[1]>here[1])-(p[1]<here[1])
        for j in range(1,length+1):
            q=(here[0]+j*dx,here[1]+j*dy)
            if not _near(s,q,length):break
            cells.append(list(q))
            if q==tuple(p):break
        if not cells:return _no()
        _put(s,item,notes=cells,layer=s.layer_key())
        return True, tr('{item}沿直线标出了 {n} 格已见地形。',
                        item=tr(item.name), n=len(cells)), {'marked':cells}
    if n==2:
        if not _near(s,p):return _no()
        # 「设施」是真的有可抄的交互条件：电路读数或场景设施格，普通墙不算。
        from ..core.tamper_protection import _facility_cells
        info=s.circuit_details(*p)
        if not info and tuple(p) not in _facility_cells(s):
            return False, tr('{item}只抄得下真实的交互条件——这一格既不是设施，也没有节点读数。',
                             item=tr(item.name)), {}
        _put(s,item,facility=dict(pos=list(p),kind=s.cell(*p).wall_kind,
                                  details=list(info),layer=s.layer_key()))
        # 抄下来的东西必须当场读得出来，否则这件只是「按了有反应」。
        message = (tr('{item}抄下了一处交互条件：{n} 条读数。', item=tr(item.name), n=len(info))
                   if info else tr('{item}抄下了一处设施的交互条件。', item=tr(item.name)))
        return True, message, {'notes':list(info)}
    if n==7:
        target=s.entity_at(*p)
        if not _near(s,p) or target is None or target is s.player or target.relation!='失控意识':return _no()
        from ..core.tamper_protection import threat_reason
        if threat_reason(s,target):
            # 与其它篡改同一道保护口径：牵着一单没走完的梦的目标不吃这一针。
            return False, tr('{item}收住了——这一下会牵动一单还没走完的梦。',
                             item=tr(item.name)), {}
        s._player_strike(target,'melee',damage=_p(item,'damage',1))
        if target.integrity>0:
            # 牵制是实体属性（enemies 每回合按它扣移动），不是征兆——写征兆会被静默丢弃。
            target.slow_turns=max(target.slow_turns,float(_p(item,'slow_turns',1)))
        _put(s,item,recovery_until=int(s.time)+2)
        return _yes(item,restrained=target.id)
    if n==10:
        a,b=map(tuple,p)
        if not all(_mutable(s,pos) for pos in (a,b)):return _no()
        source,dest=s.cell(*a),s.cell(*b)
        if (not source.solid or source.height>_p(item,'max_height',1)
                or dest.solid or s.entity_at(*b)):return _no()
        if not source.creation or source.wall_kind in {'机关门','意识边界'}:return _no()
        fields=('wall_kind','solid','height','hardness','thickness','integrity','creation')
        for name in fields:setattr(dest,name,getattr(source,name))
        source.wall_kind='';source.solid=False;source.height=0;source.creation={}
        _put(s,item,cart=list(a),layer=s.layer_key())
        s._visible_cache=None
        return _yes(item,moved=[list(a),list(b)])
    if n in {11,12,14}:
        reach=_p(item,'reach',5)
        if not _near(s,p,reach):return _no()
        fields=[f for f in s.construct_environments if f.get('layer')==s.layer_key()
                and list(p) in f.get('cells',[]) and f.get('kind') in {'paper_blades','library.erase'}]
        if not fields:return _no()
        f=fields[0]
        if n==11:
            if len(f['cells'])<2:return _no()
            # Only a perimeter cell may be trimmed, never a protected cell.
            if _protected(s,p):return _no()
            f['cells'].remove(list(p));return _yes(item,trimmed=list(p))
        if n==12:
            if _record(s,item).get('fixed'):return _no()
            extend=_p(item,'extend',2)
            f['remaining']+=extend;f['gear_fixed_by']=item.instance_id
            _put(s,item,fixed=dict(kind=f['kind'],layer=s.layer_key()))
            return _yes(item,extended=extend)
        if f['remaining']!=1 or f.get('gear_deferred'):return _no()
        f['pause_ticks']=1;f['gear_deferred']=True
        return _yes(item,deferred=1)
    if n==15:
        if not _near(s,p,_p(item,'reach',8)):return _no()
        c=s.cell(*p)
        if c.wall_kind!='意识边界':return _no()
        _put(s,item,anchor=dict(pos=list(p),layer=s.layer_key()))
        return _yes(item,anchor=list(p))
    if n==16:
        if not _near(s,p,_p(item,'reach',6)):return _no()
        from ..core import item_devices
        for device in item_devices.devices(s):
            data=device.get('data',{})
            if (device.get('x'),device.get('y'))!=tuple(p):continue
            definition=data.get('definition_id')
            if not definition or not device.get('kind','').startswith('gear_'):continue
            if device.get('turns',0)<=0:return _no()
            obj=s._make_item(definition);s.inventory.append(obj)
            # 保留原剩余回合：重新布放时由 `packed_turns()` 取回，不是全新时限。
            _put(s,obj,recovered_device=dict(kind=device['kind'],turns=device['turns'],data=data))
            item_devices.devices(s).remove(device)
            return _yes(item,recovered=obj.instance_id,remaining=device['turns'])
        return _no()
    return _no()


def packed_turns(s,instance_id,kind,default):
    """返程封套收回的装置按原剩余回合重新布放（一次性，取走即清）。"""
    mark=s.equipment_marks.get('remaining_gear:'+str(instance_id))
    if not isinstance(mark,dict):return default
    packed=mark.get('recovered_device')
    if not packed or packed.get('kind')!=kind:return default
    mark.pop('recovered_device',None)
    return max(1,int(packed.get('turns') or default))


def _projectile(s,item,n,p):
    here=(s.player.x,s.player.y)
    if n==2:return _passive(item,'{item}是被动的：换弹时掉出的实弹落在脚下，可以再捡回来。')
    if n==12:return _passive(item,'{item}是被动的：换弹中允许走一小步，一次换弹只给一步。')
    if n in {4,7,8}:
        gun=next((o for o in s.inventory if o is not item and o.definition_id.startswith('expansion.projectile.')
                  and int(o.definition_id[-2:]) in GUNS and o.instance_id in s.equipped.values()),None)
        if gun is None:return _no()
        if n==4:
            if (gun.magazine or 0)<=0:return _no()
            _put(s,gun,heavy=item.instance_id);return _yes(item,armed=gun.instance_id)
        if n==7:
            rec=_record(s,item)
            _put(s,item,brace=None if rec.get('brace') else list(here))
            return _yes(item,braced=not bool(rec.get('brace')))
        if (gun.magazine or 0)<=0 or gun.definition_id.endswith('e16'):return _no()
        gun.magazine-=1
        _put(s,gun,unloaded=True)
        # Refund one real unloaded round, not a newly full magazine.
        rounds=s.realm_features.setdefault('gear_rounds',[])
        rounds.append(dict(owner=gun.instance_id,pos=list(here),amount=1,layer=s.layer_key()))
        return _yes(item,unloaded=1)
    if n==3:
        if tuple(p)==here:return _no()
        path=_ray(s,here,tuple(p),_p(item,'range',8))
        first=next((q for q in path if s.cell(*q).solid or s.entity_at(*q)),None)
        # An invisible interceptor is reported only as an unknown obstruction.
        return _yes(item,interceptor=list(first) if first and s.is_visible(*first) else None,
                    obstructed=first is not None)
    if n==13:
        rounds=s.realm_features.setdefault('gear_rounds',[])
        for record in tuple(rounds):
            q=tuple(record['pos'])
            if record.get('layer')!=s.layer_key() or not _near(s,q,_p(item,'reach',6)):continue
            gun=next((o for o in s.inventory if o.instance_id==record['owner']),None)
            if gun is None or (gun.magazine or 0)>=GUNS.get(int(gun.definition_id[-2:]),(0,0))[0]:continue
            gun.magazine=(gun.magazine or 0)+1
            record['amount']-=1
            if record['amount']<=0:rounds.remove(record)
            _put(s,gun,unloaded=True) # Recovered rounds never counterfeit last-shot streaks.
            return _yes(item,recovered=1)
        return _no()
    if n not in GUNS:return _no()
    capacity=_p(item,'capacity',GUNS[n][0]);reload_steps=_p(item,'reload_steps',GUNS[n][1])
    record=_record(s,item)
    if tuple(p)==here:
        # Clicking oneself reloads; two-mouth weapons switch only while full.
        if n==5 and item.magazine==capacity and not item.reload_steps:
            slots=list(record.get('chambers',[capacity,capacity]));current=int(record.get('mouth',0))
            slots[current]=item.magazine;new=1-current
            _put(s,item,chambers=slots,mouth=new);item.magazine=slots[new]
            return _yes(item,mouth=new)
        if n==16 and item.magazine==capacity and not record.get('charged'):
            _put(s,item,charged=True);return _yes(item,charged=True)
        if item.magazine is None:item.magazine=0
        if item.magazine>=capacity:return _no()
        if not item.reload_paid:
            if s.imagination<1:return _no()
            s._pay_ability_cost(1);item.reload_paid=True
            if item.magazine:
                if equipped(s,'expansion.projectile.e02'):
                    s.realm_features.setdefault('gear_rounds',[]).append(dict(
                        owner=item.instance_id,pos=list(here),amount=item.magazine,layer=s.layer_key()))
                item.magazine=0
        item.reload_steps+=1
        brace=next((o for o in s.inventory
                   if o.definition_id=='expansion.projectile.e07'
                   and o.instance_id in s.equipped.values()
                   and _record(s,o).get('brace')==list(here)),None)
        saving=_p(brace,'reload_saving',1) if brace is not None else 0
        if item.reload_steps>=max(1,reload_steps-saving):
            # Existing rounds remain real; only missing rounds are purchased.
            item.magazine=capacity;item.magazine_capacity=capacity
            item.reload_steps=0;item.reload_paid=False
            _put(s,item,unloaded=False,streak=0,reload_step_used=False)
        return _yes(item,magazine=item.magazine,steps=item.reload_steps)
    if item.reload_steps:return _no()
    if n==6 and not item.magazine:
        target=s.entity_at(*p)
        if not _near(s,p) or target is None or target is s.player:return _no()
        s._player_strike(target,'melee',damage=_p(item,'melee_damage',2))
        _put(s,item,recovery_until=int(s.time)+2)
        return _yes(item,melee=target.id)
    needed=_p(item,'rounds',2) if n==10 else capacity if n==16 else 1
    if (item.magazine or 0)<needed or (n==16 and not record.get('charged')):return _no()
    if int(record.get('recovery_until',0))>s.time:return _no()
    start=here
    if n==14:
        from ..core.construct_environments import reflection
        mirrors=[]
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q=(here[0]+dx,here[1]+dy)
            if _near(s,q) and reflection(s,*q,(dx,dy)) is not None:mirrors.append(q)
        if not mirrors:return _no()
        start=mirrors[0]
    # 推重的来源件本身带着射程与伤害；只记实例，不记一个无法追溯的 True。
    # 旧存档里的 heavy=True 没有来源件：仍按推重算，但退回目录默认值。
    heavy_mark=record.get('heavy')
    heavy=_by_instance(s,heavy_mark) if heavy_mark else None
    if n==10:shot_range=_p(item,'range',4)
    elif heavy_mark:shot_range=_p(heavy,'range',4)
    else:shot_range=_p(item,'range',8)
    paths=[_ray(s,start,tuple(p),shot_range)]
    if n==10:
        fork_range=_p(item,'range',4)
        dx=(p[0]>start[0])-(p[0]<start[0]);dy=(p[1]>start[1])-(p[1]<start[1])
        paths=[_ray_direction(s,start,dx,dy,fork_range),
               _ray_direction(s,start,-dy if dx else 1,dx if dy else 1,fork_range)]
    item.magazine-=needed
    record['streak']=int(record.get('streak',0))+needed
    push=_p(item,'push',3) if n==15 and item.magazine==0 and not record.get('unloaded') and record['streak']==capacity else 0
    damage=_p(heavy,'damage',3) if heavy_mark else 1
    if n==16:damage=capacity
    hit=[];flight=[]
    for path in paths:
        reflected=False
        for q in path:
            flight.append(q);c=s.cell(*q)
            if c.solid:
                if n==9 and not reflected:
                    from ..core.ballistics import bounce_direction
                    dx=(q[0]>start[0])-(q[0]<start[0]);dy=(q[1]>start[1])-(q[1]<start[1])
                    solid={(x,y):s.cell(x,y).solid for y in range(s.height) for x in range(s.width)}
                    bx,by=bounce_direction(solid,q[0]-dx,q[1]-dy,dx,dy)
                    bounce=_ray_direction(s,(q[0]-dx,q[1]-dy),bx,by,max(0,8-len(flight)))
                    for r in bounce:
                        if s.cell(*r).solid:break
                        flight.append(r)
                        if r==here:
                            # 反折弹打回自己格：先问专用缓冲「靶心背后的墙」，再由
                            # 统一资源结算扣清醒度——两条通道各有其位，不互相顶替。
                            from ..core import memory_buffers
                            if not memory_buffers.spend(s,'lucidity:self_projectile'):
                                from ..core.settlement import REASON_COMBAT, settle_delta
                                settle_delta(s,'lucidity',-1,reason=REASON_COMBAT,
                                             source='expansion.projectile.e09')
                            break
                        enemy=s.entity_at(*r)
                        if enemy and enemy is not s.player:s._player_strike(enemy,'ranged',damage=damage);hit.append(enemy.id);break
                    reflected=True
                break
            if n==16:s._add_liquid(c,'熔融蜡烛',1)
            enemy=s.entity_at(*q)
            if enemy and enemy is not s.player:
                s._player_strike(enemy,'ranged',damage=damage);hit.append(enemy.id)
                if push and enemy.integrity>0:
                    dx=(q[0]>start[0])-(q[0]<start[0]);dy=(q[1]>start[1])-(q[1]<start[1])
                    for _ in range(push):
                        dest=(enemy.x+dx,enemy.y+dy)
                        if not s.inside_board(*dest) or s.cell(*dest).solid or s.entity_at(*dest):break
                        enemy.x,enemy.y=dest
                break
    record.update(heavy=False,charged=False)
    s.equipment_marks[_key(item)]=record
    s.last_projectile=dict(path=[list(q) for q in flight],kind='gear',hit=hit)
    s._sound_pulse(*here,8,by_player=True,category='item',source=item.name)
    if n!=16:
        # The spent recoverable round exists at its landing cell, never in an enemy.
        q=flight[-1] if flight else here
        if not s.entity_at(*q):s.realm_features.setdefault('gear_rounds',[]).append(
            dict(owner=item.instance_id,pos=list(q),amount=needed,layer=s.layer_key()))
    return _yes(item,hits=hit,push=push,magazine=item.magazine,path=[list(q) for q in flight])


GUNS={1:(1,1),5:(2,1),6:(2,2),9:(2,2),10:(4,2),14:(2,2),15:(4,2),16:(4,3)}


def _ray_direction(s,start,dx,dy,length):
    out=[]
    for step in range(1,length+1):
        p=(start[0]+step*dx,start[1]+step*dy)
        if not s.inside_board(*p):break
        out.append(p)
    return out


def _ray(s,start,end,length):
    """Bresenham cells, finite range; obstacles are resolved by each caller."""
    x,y=start;ex,ey=end;dx=abs(ex-x);dy=-abs(ey-y)
    sx=1 if x<ex else -1;sy=1 if y<ey else -1;err=dx+dy;out=[]
    while (x,y)!=(ex,ey) and len(out)<length:
        e=2*err
        if e>=dy:err+=dy;x+=sx
        if e<=dx:err+=dx;y+=sy
        if not s.inside_board(x,y):break
        out.append((x,y))
    return out


def tick(s):
    """Conserved flows and mounted objects; called by the existing device clock."""
    for item in tuple(s.inventory):
        n=int(item.definition_id[-2:]) if item.definition_id.startswith('expansion.') and item.definition_id[-2:].isdigit() else 0
        family=item.definition_id.split('.')[1] if item.definition_id.startswith('expansion.') else ''
        record=_record(s,item)
        relay=record.get('relay')
        if relay and relay['layer']==s.layer_key() and relay.get('due',10**15)<=s.time:
            relay.pop('due',None);relay['remaining']=0
            s._gear_relay_replay=True
            try:s._circuit_signal(*relay['pos'],by_player=True)
            finally:s._gear_relay_replay=False
        if family=='terrain' and n==10 and item.contents:
            kind=next(iter(item.contents));amount=min(_p(item,'leak',1),item.contents[kind])
            s._add_liquid(s.cell(s.player.x,s.player.y),kind,amount)
            item.contents[kind]-=amount
            if item.contents[kind]<=0:del item.contents[kind]
        if record.get('mount') and record.get('stored') and record.get('layer')==s.layer_key():
            p=tuple(record['mount'])
            if s.cell(*p).wall_kind!=record.get('support'):_release(s,item,ground=p)
        # 护理员的托盘：一旦不在盘上（掉落或收起），里面托着的两件按真实位置落地，
        # 不跟着刻痕一起消失。
        if family=='realm' and n==6:_spill_tray(s,item)
        flow=record.get('flow')
        if flow and flow.get('layer')==s.layer_key() and flow['remaining']>0:
            a,b=tuple(flow['source']),tuple(flow['outlet']);flow['remaining']-=1
            share=int(flow.get('amount',2 if flow['split'] else 4))
            if flow['gas'] or s.cell(*a).elevation+s.cell(*a).height>s.cell(*b).elevation:
                _transfer(s,a,b,share,gas=flow['gas'])
                if flow['split']:
                    other=(a[0]-(b[0]-a[0]),a[1]-(b[1]-a[1]))
                    if s.inside_board(*other) and s.cell(*a).elevation>s.cell(*other).elevation:
                        _transfer(s,a,other,share)
        infusion=record.get('infusion')
        if infusion and infusion['remaining']>0 and infusion['layer']==s.layer_key():
            if list((s.player.x,s.player.y))!=infusion['origin']:
                # 「凌晨的输液声」：中断时用掉一次缓冲，把未结算的份额留住——
                # 但给药仍要回到起点格才继续，不凭空到账、也不改总量。
                from ..core import memory_buffers
                if not memory_buffers.spend(s,'infusion:staged_dose'):
                    infusion['remaining']=0 # Interrupted doses are lost, never duplicated.
            else:
                amount=(infusion['remaining']+infusion['turns']-1)//infusion['turns']
                s.restore_resource(infusion['resource'],amount)
                infusion['remaining']-=amount;infusion['turns']-=1
        dose=record.get('delayed_dose')
        if dose and dose['layer']==s.layer_key() and int(s.time)>=dose['due']:
            # 「不能预付死亡后复活」：一局已经失败就不再兑现这笔分期剂量。
            # 判据用全局失败口径（`run_over`），不是「任一资源为 0」——清醒见底
            # 但心智还在时仍是可救的，那时这笔药正该生效。
            if not getattr(s,'run_over',False):s.restore_resource(dose['resource'],dose['amount'])
            record.pop('delayed_dose',None)
        if record.get('fixed') and not any(f.get('gear_fixed_by')==item.instance_id
                                          for f in s.construct_environments):record.pop('fixed',None)
        if record.get('dry_cloth_wet') and s.cell(s.player.x,s.player.y).liquid<=0:
            record.pop('dry_cloth_wet',None)
        mold=record.get('mold')
        if mold and mold['layer']==s.layer_key() and mold['remaining']>0:
            mold['remaining']-=1
            if mold['remaining']==0:
                c=s.cell(*mold['pos'])
                wall=MOLD_WALLS.get(mold['material'])
                if (wall and not c.solid and c.liquid_kind==mold['material']
                        and c.liquid>=mold['amount']):
                    c.liquid-=mold['amount']
                    if not c.liquid:c.liquid_kind=''
                    s.configure_wall(c,wall)
                    c.phase_stock=dict(form='wall',kind=mold['material'],amount=mold['amount'],
                        initial_amount=mold['amount'],initial_integrity=c.integrity,
                        wall=c.wall_kind,base_floor=c.aggregate_variant)
                    s._sync_material_position(*mold['pos'])
    # 掉在地上的托盘也要扫：只遍历行囊会漏掉它，里面两件就永远卡在刻痕里。
    for entry in tuple(getattr(s,'world_items',()) or ()):
        if getattr(entry,'item',None) is not None:_spill_tray(s,entry.item)


def equipped(s,definition):
    return any(o.definition_id==definition and o.instance_id in s.equipped.values() for o in s.inventory)


def before_move(s):
    """A braced reload cannot move; the sling allows one real step per reload."""
    guns=[o for o in s.inventory if o.definition_id.startswith('expansion.projectile.') and o.reload_steps>0]
    if not guns:return True
    if any(_record(s,o).get('brace') for o in s.inventory
           if o.definition_id=='expansion.projectile.e07' and o.instance_id in s.equipped.values()):return False
    return equipped(s,'expansion.projectile.e12') and all(not _record(s,o).get('reload_step_used') for o in guns)


def after_move(s):
    for o in s.inventory:
        if o.definition_id.startswith('expansion.projectile.') and o.reload_steps>0:
            _put(s,o,reload_step_used=True)
        if o.definition_id=='expansion.projectile.e07' and _record(s,o).get('brace'):
            _put(s,o,brace=None)


def move_cost(s,cost):
    sole=next((o for o in s.inventory if o.definition_id=='expansion.terrain.e05'
               and o.instance_id in s.equipped.values()),None)
    return cost+(_p(sole,'move_cost',1) if sole is not None else 0)


def attachment_duration(s,duration):
    if int(s.equipment_marks.get('gear_circuit_operation_until',-1))<int(s.time):return duration
    for o in s.inventory:
        if o.definition_id=='expansion.circuit.e02' and o.instance_id in s.equipped.values():
            if not _record(s,o).get('dry_cloth_wet'):
                _put(s,o,dry_cloth_wet=True);return max(0,duration-1)
    return duration


def liquid_edge_allowed(s,a,b):
    for key,record in s.equipment_marks.items():
        if not key.startswith('remaining_gear:') or not isinstance(record,dict):continue
        edge=record.get('barrier')
        if not edge or record.get('layer')!=s.layer_key():continue
        if {tuple(edge[0]),tuple(edge[1])}=={tuple(a),tuple(b)}:
            item=_by_instance(s,key.split(':',1)[1])
            limit=_p(item,'pressure',60) if item is not None else 60
            pressure=abs(s.cell(*a).liquid-s.cell(*b).liquid)
            if pressure>limit:
                record['damaged']=True;record['barrier']=None
                return True
            return False
    return True


def cast_allowed(s,ability_id):
    from ..core.construct_environments import RESIDUE_SOURCE
    for record in s.equipment_marks.values():
        if not isinstance(record,dict):continue
        fixed=record.get('fixed')
        if fixed and fixed['layer']==s.layer_key() and RESIDUE_SOURCE.get(fixed['kind'])==ability_id:return False
    return True


def circuit_signal_gate(s,x,y,*,replaying=False):
    """A physical relay intercepts an observed signal, once, on its actual port."""
    if replaying or getattr(s,'_gear_relay_replay',False):return True
    for obj in s.inventory:
        r=_record(s,obj).get('relay')
        if (not r or r['layer']!=s.layer_key() or r['pos']!=[x,y] or r['remaining']<=0
                or obj.instance_id not in s.equipped.values()):continue
        r['remaining']-=1
        if r['mode']=='delay':
            r['due']=int(s.time)+1;return False
        observations=r['observations']
        if len(observations)<2:
            observations.append(int(s.time));return True
        gap=observations[1]-observations[0]
        if int(s.time)-observations[-1]==gap:
            r['remaining']=0;return True
        return False
    return True
