"""Bounded realm surface, fixture and finite loot generation with coverage reports."""
from collections import Counter, deque
import random
from .entities import WorldEvent, WorldItem, ActionResult
from .generation import GenerationMixin as G
from .realm_architecture import reachable,ventilation_clearance
from ..data.items import ITEM_DEFINITIONS

PALETTES = {
    'library_palace': ('普通聚合物','木质聚合物','书页地','吸声聚合物','干纸堆','防火石面'),
    'white_sanatorium': ('洁白釉板','密封板','反光聚合物','海绵聚合物','金属聚合物','粗糙聚合物','绝热层','吸声聚合物'),
}


def _patch(pool, start, limit, rng):
    out, queue = [],deque([start])
    queued = {start}
    while queue and len(out)<limit:
        p = queue.popleft()
        if p not in pool: continue
        out.append(p)
        x,y = p
        adjacent = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        rng.shuffle(adjacent)
        for q in adjacent:
            if q in pool and q not in queued:
                queue.append(q);queued.add(q)
    return out


def _floor(cell, kind):
    cell.aggregate_variant = kind
    cell.floor_fuel = 9 if kind in ('干纸堆','书页地') else 0


def partition_floors(builder, realm, seed, depth):
    rng = random.Random(seed ^ 0x464C4F52 ^ depth*3571)
    palette = PALETTES[realm]
    opened = {(x,y) for y,row in enumerate(builder.cells) for x,c in enumerate(row) if not c.solid}
    pool = opened - builder.reserved
    target = round(len(opened)*.32)
    filled, index = 0,0
    while pool and filled<target:
        start = rng.choice(sorted(pool))
        kind = palette[1+index % (len(palette)-1)]
        patch = _patch(pool,start,min(rng.randint(18,55),target-filled),rng)
        for x,y in patch: _floor(builder.cells[y][x],kind)
        pool.difference_update(patch);filled+=len(patch);index+=1


def _balance_floors(plan, realm, seed, depth):
    """Furniture changes the denominator; preserve the final coverage contract."""
    rng = random.Random(seed ^ 0x42414C41 ^ depth*3571)
    palette = PALETTES[realm]
    opened = {(x,y) for y,row in enumerate(plan.cells) for x,c in enumerate(row) if not c.solid}
    specials = {p for p in opened if plan.cells[p[1]][p[0]].aggregate_variant != palette[0]}
    wanted = round(len(opened)*.32)
    # Reserved lanes protect topology and hazards, not harmless floor texture.
    pool = {p for p in opened-specials if p not in (plan.spawn,plan.exit)}
    index = 0
    while pool and len(specials)<wanted:
        patch = _patch(pool,rng.choice(sorted(pool)),min(35,wanted-len(specials)),rng)
        kind = palette[1+index%(len(palette)-1)]
        for x,y in patch: _floor(plan.cells[y][x],kind)
        pool.difference_update(patch);specials.update(patch);index+=1
    if len(specials)>wanted:
        candidates = [p for p in sorted(specials) if plan.cells[p[1]][p[0]].aggregate_variant != '密封板']
        # Retain each type's seed; trim patch edges rather than entire types.
        rng.shuffle(candidates)
        counts = Counter(plan.cells[y][x].aggregate_variant for x,y in specials)
        for x,y in candidates:
            if len(specials)<=wanted:break
            kind = plan.cells[y][x].aggregate_variant
            if counts[kind]<=12:continue
            counts[kind]-=1;_floor(plan.cells[y][x],palette[0]);specials.remove((x,y))


def _walls(plan, realm, rng):
    """Place functional runs on actual boundaries, before reserving loot anchors."""
    report = []
    if realm == 'library_palace':
        kinds = ('玻璃书障','胡桃木书架','防火书柱','黄铜阅读灯','推书车')
    else:
        kinds = ('净相壁','日光壁','净玻璃隔屏','净衣推车')
    structural = '书库内墙' if realm == 'library_palace' else '白瓷隔断'
    vent_clearance=ventilation_clearance(plan.cells) if realm=='white_sanatorium' else set()
    edges = [(x,y) for y in range(4,plan.height-4) for x in range(4,plan.width-4)
             if plan.cells[y][x].wall_kind == structural and
             (x,y) not in vent_clearance and
             any(not plan.cells[y+dy][x+dx].solid for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))]
    rng.shuffle(edges)
    for kind in kinds:
        quota = 4 if kind != '胡桃木书架' else 12
        for _ in range(quota):
            if not edges:report.append('wall:'+kind);break
            x,y = edges.pop()
            G.configure_wall(plan.cells[y][x],kind)
    if realm != 'white_sanatorium': return report
    # Single units and horizontal/vertical short banks; fans share an open ray.
    for kind,axis,length in [('排气口',(1,0),1),('排气口',(1,0),rng.randint(2,4)),
                              ('排气口',(0,1),rng.randint(2,4)),
                              ('换气扇',(1,0),1),('换气扇',(1,0),rng.randint(2,4)),
                              ('换气扇',(0,1),rng.randint(2,4))]:
        choices=[]
        for x,y in edges:
            run=[(x+axis[0]*i,y+axis[1]*i) for i in range(length)]
            if not all(2<=xx<plan.width-2 and 2<=yy<plan.height-2
                       and plan.cells[yy][xx].wall_kind == structural for xx,yy in run):continue
            for name,dx,dy in [('北',0,-1),('东',1,0),('南',0,1),('西',-1,0)]:
                reach = 3 if kind == '换气扇' else 1
                if all(2<=xx+i*dx<plan.width-2 and 2<=yy+i*dy<plan.height-2
                       and not plan.cells[yy+i*dy][xx+i*dx].solid
                       for xx,yy in run for i in range(1,reach+1)):
                    choices.append((run,name));break
        if not choices:
            report.append(f'{kind}:{axis}:{length}');continue
        run,name = rng.choice(choices)
        for x,y in run:
            G.configure_wall(plan.cells[y][x],kind if kind=='排气口' else kind+'·'+name)
        if kind=='换气扇':
            dx,dy={'北':(0,-1),'东':(1,0),'南':(0,1),'西':(-1,0)}[name]
            vent_clearance.update((x+dx*i,y+dy*i) for x,y in run for i in range(1,4))
        edges=[p for p in edges if p not in run and p not in vent_clearance]
    return report


def _scatter_materials(plan, realm, depth, pool, rng):
    cells = plan.cells
    opened = [c for row in cells for c in row if not c.solid]
    target_liquid,target_gas = round(len(opened)*.03),round(len(opened)*.02)
    liquids = ('湿墨','书脊胶','稀墨') if realm=='library_palace' else (
        '注射用梦水','洗兆液','淋巴液','晨醒溶液','银盐悬液','凝胶基液','纤维蛋白胶','脑脊液','梦醚')
    gases = ('纸尘','墨雾') if realm=='library_palace' else ('醒素薄气','无菌载气','胞尘')
    missing=[]
    for attr,target,kinds,amount in [('liquid',target_liquid,liquids,8),('gas',target_gas,gases,8)]:
        existing=sum(getattr(c,attr)>0 for c in opened)
        eligible={p for p in pool if not cells[p[1]][p[0]].liquid and not cells[p[1]][p[0]].gas}
        index=depth-1
        while eligible and existing<target:
            patch=_patch(eligible,rng.choice(sorted(eligible)),min(rng.randint(3,9),target-existing),rng)
            for x,y in patch:
                setattr(cells[y][x],attr,amount)
                setattr(cells[y][x],attr+'_kind',kinds[index%len(kinds)])
            existing+=len(patch);index+=1;eligible.difference_update(patch)
        pool.difference_update({p for p in pool if cells[p[1]][p[0]].liquid or cells[p[1]][p[0]].gas})
        if existing<target:missing.append(attr)
    return missing


def _loot(realm,rng,state=None):
    if realm=='white_sanatorium':
        category = rng.choices(('摄入物','易逝物','工具','携带意象'),(40,40,15,5))[0]
        categories = ('惯用物','交互道具') if category=='工具' else (category,)
        pool=[k for k,v in ITEM_DEFINITIONS.items() if v.get('category') in categories and
              ('white_sanatorium' in v.get('spawn_realms',()) or
               (v.get('loot',True) and not v.get('spawn_realms')))]
    else:
        pool=[k for k,v in ITEM_DEFINITIONS.items() if
              v.get('category') in ('摄入物','易逝物','惯用物') and v.get('loot',True)
              and not v.get('spawn_realms') and v.get('effect')!='learn_ability']
    if state is not None:
        # 限定件（珍品、只从特定挑战拿到的物品）不能进位面柜子：生成时抽中、
        # 开柜时又被资格查询拒掉，柜子就成了永远打不开的空壳。
        from .item_access import refusal
        eligible=[k for k in pool if not refusal(state,k,source='realm_stock')]
        if not eligible:
            eligible=[k for k in pool if not ITEM_DEFINITIONS[k].get('grant_source')]
        pool=eligible or pool
    return rng.choice(sorted(pool))


# §5.1 P1 位面供给试验（2026-10-22）：散物与搜刮柜收敛为「首轮试验值」。
# 独立开关只改四个数量档，随机流抽取顺序与旧实现一致，便于固定种子对照；
# False 时完全回到旧档（12–18/8–12 散物、6–10/4–8 柜、每柜 1–3、学习物 2–4）。
REALM_SUPPLY_TRIAL = True
_LEGACY_SUPPLY = {
    'white_sanatorium': {'loose': (12, 18), 'boxes': (6, 10), 'per_box': (1, 3), 'books': (0, 0)},
    'library_palace': {'loose': (8, 12), 'boxes': (4, 8), 'per_box': (1, 3), 'books': (2, 4)},
}
_TRIAL_SUPPLY = {'loose': (6, 9), 'boxes': (3, 4), 'per_box': (1, 2), 'books': (1, 2)}


def realm_supply_ranges(realm, trial=None):
    """位面散物／柜子／学习物的数量档；trial=None 读模块开关。

    只返回范围，不抽随机数——调用方仍在原位置抽签，固定种子可逐层对照。
    """
    trial = REALM_SUPPLY_TRIAL if trial is None else trial
    if trial:
        if realm == 'library_palace':
            return dict(_TRIAL_SUPPLY)
        return {**_TRIAL_SUPPLY, 'books': (0, 0)}
    return dict(_LEGACY_SUPPLY.get(realm, _LEGACY_SUPPLY['library_palace']))


def complete_content(state,plan,depth,realm):
    _balance_floors(plan,realm,state.seed,depth)
    wall_rng=random.Random(state.seed ^ 0x57414C4C ^ depth*3571)
    missing=_walls(plan,realm,wall_rng)
    events=state._pending_realm_events
    occupied={(e.x,e.y) for e in events}|{(e.x,e.y) for e in getattr(state,'_pending_realm_entities',())}
    occupied|={plan.spawn,plan.exit}
    safe=reachable(plan.cells,plan.spawn)
    pool={p for p in safe if not plan.cells[p[1]][p[0]].solid and p not in plan.protected_cells
          and p not in occupied and max(abs(p[0]-plan.spawn[0]),abs(p[1]-plan.spawn[1]))>=5
          and all(max(abs(p[0]-x),abs(p[1]-y))>1 for x,y in occupied)}
    if plan.core_anchor:
        pool={p for p in pool if max(abs(p[0]-plan.core_anchor[0]),abs(p[1]-plan.core_anchor[1]))>8}
    missing+=_scatter_materials(plan,realm,depth,pool,random.Random(state.seed ^ 0x4C495147 ^ depth*3571))
    rng=random.Random(state.seed ^ 0x4C4F4F54 ^ depth*3571)
    supply = realm_supply_ranges(realm)
    loose_count=rng.randint(*supply['loose'])
    box_count=rng.randint(*supply['boxes'])
    # Each box replaces a reachable fixture, never a passage.
    wall_kind='封口药箱' if realm=='white_sanatorium' else '胡桃木书架'
    boxes=state.realm_features.setdefault('scavenge_stock',{})
    vent_clearance=ventilation_clearance(plan.cells) if realm=='white_sanatorium' else set()
    for i in range(box_count):
        # Replacing an existing solid cannot split even a one-cell side passage.
        sites=[(x,y) for y in range(4,plan.height-4) for x in range(4,plan.width-4)
                    if plan.cells[y][x].wall_kind in ('书库内墙','白瓷隔断') and (x,y) not in occupied
                    and (x,y) not in vent_clearance
                    and (x,y) not in plan.protected_cells
                    and any((x+dx,y+dy) in pool for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))]
        p=rng.choice(sites) if sites else None
        if p is None:missing.append('scavenge');break
        G.configure_wall(plan.cells[p[1]][p[0]],wall_kind)
        uid=f'{state.seed}:{realm}:{depth}:scavenge:{i}'
        stock=[_loot(realm,rng,state) for _ in range(rng.randint(*supply['per_box']))]
        boxes[uid]={'remaining':stock,'wall':wall_kind,'position':p}
        event=WorldEvent(uid,'封存药柜' if realm=='white_sanatorium' else '旧书柜',*p,
                         '柜门松了一线，里面还有几样没有带走的东西。',catalog_id='event.realm.scavenge',
                         kind='compound',dialogue=('抽屉拉开了一半。里面的东西各有各的位置。',),bound=True,dissolution_reward=0,
                         options=({'label':'搜刮柜内物品','realm_scavenge':True},{'label':'留在这里','leave':True}))
        events.append(event);occupied.add(p);pool.discard(p)
    state._pending_realm_items=[]
    positions=sorted(pool);rng.shuffle(positions)
    library_books=rng.randint(*supply['books']) if realm=='library_palace' else 0
    for i,p in enumerate(positions[:loose_count]):
        iid='library.unbound_page' if i==0 and library_books else ('spellbook' if i%2 else 'torn_page') if i<library_books else _loot(realm,rng,state)
        state._pending_realm_items.append(WorldItem(state._make_item(iid),*p))
    if len(state._pending_realm_items)<loose_count:missing.append('loose_items')
    floors=Counter(c.aggregate_variant for row in plan.cells for c in row if not c.solid)
    walls=Counter(c.wall_kind for row in plan.cells for c in row if c.solid)
    state.realm_features['generation_report']={'version':2,'floors':dict(floors),'walls':dict(walls),
        'liquid_cells':sum(c.liquid>0 for row in plan.cells for c in row if not c.solid),
        'gas_cells':sum(c.gas>0 for row in plan.cells for c in row if not c.solid),
        'loose_items':len(state._pending_realm_items),'scavenge':len(boxes),'missing':missing,
        'supply':{'trial':bool(REALM_SUPPLY_TRIAL),'loose':list(supply['loose']),
                  'boxes':list(supply['boxes']),'per_box':list(supply['per_box']),
                  'learning_items':library_books}}
    if missing:raise ValueError(f'{realm}:{depth} incomplete generation: {missing}')


def _stock_item(state, ledger, iid):
    from .item_access import refusal
    from .entities import Item
    legacy = ledger.get('legacy_limited_items', {}).get(iid, [])
    if legacy:
        # Already rolled before migration: retain the existing reserved copy.
        return Item(**legacy[0]), True, None
    reason = refusal(state, iid, source='realm_stock')
    if reason:
        return None, False, reason
    return state._make_item(iid), False, None


def _commit_stock_item(state, ledger, iid, legacy):
    if legacy:
        ledger['legacy_limited_items'][iid].pop(0)
    else:
        from .item_access import record_grant
        record_grant(state, iid, source='realm_stock')
    ledger['remaining'].remove(iid)


def scavenge(state,event):
    """搜刮柜：一次只带走一件（§5.1 P1「柜内二选一」）。

    柜里有多件时先开一个选择面板让玩家挑一件——不是「全拿」，也不是
    「随机给一件」。没被选中的那件仍留在柜内（ledger['remaining']），
    柜子被拆掉时按 tick_scavenge 掉到地上，不会凭空消失。
    """
    from ..i18n import tr
    if event not in state.events or max(abs(event.x-state.player.x),abs(event.y-state.player.y))>1:
        return ActionResult(False,tr('柜子还在远处。'))
    ledger=state.realm_features.get('scavenge_stock',{}).get(event.event_id)
    if not ledger or not ledger['remaining']:return ActionResult(False,tr('柜里已经空了。'))
    eligible=[]
    refused=None
    for iid in list(ledger['remaining']):
        item, legacy, reason = _stock_item(state, ledger, iid)
        if reason:
            refused = reason
            continue
        eligible.append((iid,item,legacy))
    if not eligible:return ActionResult(False,refused or tr('行囊装不下了，东西仍留在柜里。'))
    if len(eligible)>1:
        return _open_scavenge_choice(state,event,eligible)
    iid,item,legacy = eligible[0]
    return _take_scavenge_item(state,ledger,iid,item,legacy)


def _open_scavenge_choice(state,event,eligible):
    """柜内多件时开一个选择面板：玩家挑一件带走。

    同一种东西有几份只列一行（玩家挑的是「哪一样」，不是「第几份」）。
    """
    from ..i18n import tr
    options=[]
    seen=set()
    for iid,item,_legacy in eligible:
        if iid in seen:continue
        seen.add(iid)
        options.append({'label':tr('取走：{name}',name=tr(item.name)),
                         'scavenge_choice':{'cabinet':event.event_id,'item':iid}})
    options.append({'label':tr('先不拿'),'leave':True})
    choice_event=WorldEvent('scavenge.'+event.event_id,event.name,event.x,event.y,
                             tr('柜里有几样东西，你只拿得走一样。'),dissolution_reward=0,
                             catalog_id='event.realm.scavenge_choice',kind='compound',
                             dialogue=(tr('抽屉拉开了一半。里面的东西各有各的位置。'),),
                             options=tuple(options),bound=True)
    state.events.append(choice_event)
    state.open_event_dialog(choice_event)
    return ActionResult(True,choice_event.description,{'scavenge_choice':event.event_id})


def choose_scavenge_item(state,event,choice):
    """结算柜内选择：只带走选中的那一件，其余留在柜里。"""
    from ..i18n import tr
    cabinet_id=choice.get('cabinet')
    iid=choice.get('item')
    ledger=state.realm_features.get('scavenge_stock',{}).get(cabinet_id)
    if not ledger or iid not in ledger['remaining']:
        state.close_event_dialog()
        return ActionResult(False,tr('柜里已经空了。'))
    item,legacy,reason = _stock_item(state,ledger,iid)
    if reason:
        return ActionResult(False,reason)
    result=_take_scavenge_item(state,ledger,iid,item,legacy)
    if not result.changed:return result
    state.close_event_dialog()
    return result


def _take_scavenge_item(state,ledger,iid,item,legacy):
    from ..i18n import tr
    from .constants import ActionKind
    try:state._add_inventory_item(item)
    except ValueError:
        return ActionResult(False,tr('行囊装不下了，东西仍留在柜里。'))
    _commit_stock_item(state, ledger, iid, legacy)
    state._action_time(1,ActionKind.USE)
    message=tr('你把{name}收进行囊。',name=tr(item.name))
    left=len(ledger['remaining'])
    if left:
        message+=tr('柜里还剩 {count} 件，没拿的仍留在原处。',count=left)
    return ActionResult(True,message,{'scavenge':[iid]})


def tick_scavenge(state):
    for ledger in state.realm_features.get('scavenge_stock',{}).values():
        if not ledger['remaining']:continue
        x,y=ledger['position']
        if state.cell(x,y).wall_kind!=ledger['wall'] or not state.cell(x,y).solid:
            for iid in list(ledger['remaining']):
                item, legacy, reason = _stock_item(state, ledger, iid)
                if reason:
                    continue
                _commit_stock_item(state, ledger, iid, legacy)
                state.world_items.append(WorldItem(item,x,y))
