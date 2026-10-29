"""Palace facilities and one-time finale stored in realm_features."""
from ..i18n import tr
from ..data.npcs import NPC_DEFINITIONS
from .entities import Entity, WorldEvent, WorldItem, ActionResult
from .generation import GenerationMixin
from ..data.library import LIBRARY_FLOOR_NAMES, LIBRARY_HINTS, LIBRARY_ANOMALIES

ENDING_OPTIONS=tuple({'label':label,'library_command':'ending','ending':key} for label,key in
    (('保留目录','keep'),('留下空页','blank'),('把书借走','borrow'))) + ({'label':'稍后再决定','leave':True},)

def install(state,plan,depth):
    state.theme=LIBRARY_FLOOR_NAMES[depth-1]
    cx=plan.width//2
    axis=[(x,y) for y in range(3,plan.height-3) for x in range(cx-2,cx+3)]
    axis_set=set(axis)
    state.realm_features={'version':plan.version,'rooms':plan.rooms,'furniture':plan.furniture,
        'core_anchor':plan.core_anchor,'exit':plan.exit,'main_axis':axis,'lights':[],
        'optional_doors':[],'optional':{},'records':[],'library_material_sources':[],
        'core':{'status':'waiting','phase':1,'ending':None,'rewarded':False,'exit_unlocked':True}}
    for f in plan.furniture:
        GenerationMixin.configure_wall(plan.cells[f['y']][f['x']],
             '胡桃木书架' if f['kind']=='shelves' else '木桌子')
    # 地板分区/墙体组合/材料散落由并行落地的 realm_enrichment.complete_content
    # 统一接管（partition_floors + _balance_floors + _walls + _scatter_materials），
    # install 不再自行铺设，避免双重叠加（曾致 d2 干纸堆 223 格）。
    state.realm_bg_zones=[{'rect':(3,3,plan.width-4,plan.height-4),'color':'#e8d8a6'}]
    scenery_positions=[]
    for index,room in enumerate(plan.rooms):
        x0,y0,x1,y1=room['rect']
        if index%2==0:
            state.realm_bg_zones.append({'rect':(x0,y0,x1,y0+1),'color':'#72563b'})
        candidates=[(x,y) for y in range(y0+2,y1-1) for x in range(x0+2,x1-1)
                    if not plan.cells[y][x].solid and (x,y) not in axis_set]
        if not candidates:continue
        # Distributed finite scenery never intersects the reserved main route.
        for n,p in enumerate(candidates[:5]):
            scenery_positions.append(p)
            cell=plan.cells[p[1]][p[0]]
            if n==0:
                GenerationMixin.configure_wall(cell,'黄铜阅读灯')
                cell.light_radius=3
                state.realm_features['lights'].append(p)
            elif n==1:GenerationMixin.configure_wall(cell,'推书车')
            elif n==2:
                GenerationMixin.configure_wall(cell,'防火书柱')
            elif n==3:
                cell.aggregate_variant='干纸堆';cell.floor_fuel=9
            elif n==4:cell.aggregate_variant='防火石面'
        if len(candidates)>6:
            door=candidates[6]
            GenerationMixin.configure_wall(plan.cells[door[1]][door[0]],'门')
            state.realm_features['optional_doors'].append(door)

    # Every floor has one transparent partition and one of each new material.
    # Pick only quiet side-room cells, well clear of the central route and anchors.
    used = {(f['x'], f['y']) for f in plan.furniture}
    used.update(scenery_positions)
    used.update(state.realm_features['lights'])
    used.update(state.realm_features['optional_doors'])
    used.update((plan.spawn, plan.exit))
    if plan.core_anchor:
        used.add(plan.core_anchor)
    room_cells = []
    for room in plan.rooms:
        x0,y0,x1,y1=room['rect']
        for y in range(y0+2,y1-1):
            for x in range(x0+2,x1-1):
                p=(x,y)
                if p in used or p in axis_set or plan.cells[y][x].solid:
                    continue
                if max(abs(x-plan.spawn[0]),abs(y-plan.spawn[1])) < 5:
                    continue
                if max(abs(x-plan.exit[0]),abs(y-plan.exit[1])) < 4:
                    continue
                if plan.core_anchor and max(abs(x-plan.core_anchor[0]),abs(y-plan.core_anchor[1])) < 5:
                    continue
                room_cells.append(p)
    # Keep distinct deterministic positions even where semantic rooms overlap.
    room_cells=list(dict.fromkeys(room_cells))
    glass_candidates=[p for p in room_cells if any(
        room['purpose'] != 'great_archive'
        and room['rect'][0]+2 <= p[0] <= room['rect'][2]-2
        and room['rect'][1]+2 <= p[1] <= room['rect'][3]-2
        for room in plan.rooms)]
    if glass_candidates:
        glass=min(glass_candidates,key=lambda p: min(
            min(p[0]-room['rect'][0], room['rect'][2]-p[0],
                p[1]-room['rect'][1], room['rect'][3]-p[1])
            for room in plan.rooms if room['purpose'] != 'great_archive'
            and room['rect'][0]+2 <= p[0] <= room['rect'][2]-2
            and room['rect'][1]+2 <= p[1] <= room['rect'][3]-2))
        GenerationMixin.configure_wall(plan.cells[glass[1]][glass[0]],'玻璃书障')
        used.add(glass)

    liquid_kind = '湿墨' if depth % 2 else '书脊胶'
    gas_kind = '纸尘' if depth % 2 else '墨雾'
    available=[p for p in room_cells if p not in used and not plan.cells[p[1]][p[0]].solid]
    scattered=[]
    if available:
        # 散落风味事件吃尾部格，绝不挪动液体/气体的既有确定性取位；
        # 两件之间保持 ≥6 格切比雪夫距离（#84：事件之间留出空隙），
        # 放不下才回退到相邻格。
        p0=available.pop();used.add(p0);scattered.append(p0)
        far=[p for p in available if max(abs(p[0]-p0[0]),abs(p[1]-p0[1]))>=6]
        p1=far[-1] if far else (available.pop() if available else None)
        if p1 is not None:
            if p1 in available:available.remove(p1)
            used.add(p1);scattered.append(p1)
        liquid_pos=available.pop(0)
        liquid_cell=plan.cells[liquid_pos[1]][liquid_pos[0]]
        liquid_cell.liquid=10
        liquid_cell.liquid_kind=liquid_kind
        used.add(liquid_pos)
        # 第二处同名液源：让本层材料真正够一次篡改或一份配制，位置取远端。
        extra_candidates=[p for p in available
                          if max(abs(p[0]-liquid_pos[0]),abs(p[1]-liquid_pos[1]))>=3]
        if extra_candidates:
            extra_pos=extra_candidates[-1]
            available.remove(extra_pos)
            extra_cell=plan.cells[extra_pos[1]][extra_pos[0]]
            extra_cell.liquid=10
            extra_cell.liquid_kind=liquid_kind
            state.realm_features['library_material_sources'].append(
                {'liquid':liquid_kind,'liquid_position':extra_pos})
        gas_candidates=[p for p in available if max(abs(p[0]-liquid_pos[0]),abs(p[1]-liquid_pos[1])) >= 2]
        if gas_candidates:
            gas_pos=gas_candidates[0]
            gas_cell=plan.cells[gas_pos[1]][gas_pos[0]]
            gas_cell.gas=12
            gas_cell.gas_kind=gas_kind
            state.realm_features['library_material_sources'].append(
                {'liquid':liquid_kind,'liquid_position':liquid_pos,
                 'gas':gas_kind,'gas_position':gas_pos})
    # 稀墨/散气/干纸堆/防火石面的大面积散落由 realm_enrichment._scatter_materials
    # 与 _balance_floors 接管（3%/2% 目标 + 32% 地板覆盖）；这里不再重复。
    sx,sy=plan.spawn
    state._pending_realm_entities=[Entity(id=f'library-guide-{depth}',label=('借阅员','索引员','窗边读者','校勘员','守页人')[depth-1],
        x=sx-1,y=sy,integrity=40,relation='稳定意识',glyph=NPC_DEFINITIONS[f'npc.library.{depth}']['glyph'],npc_kind=f'npc.library.{depth}',catalog_id=f'npc.library.{depth}',
        dissolution_reward=0,drop_id=None,move_time=100)]
    return_event=WorldEvent(event_id=f'event.library.return.{depth}',catalog_id='event.library.return',
        name='返程目录台',x=sx+1,y=sy,description='返程目录台摊开着一册目录，最后一页夹着你的借阅记录。',kind='compound',bound=True,
        dialogue=('回去的路一直通着。这里的书架、材料和已借出的东西都留在原处。',),
        options=({'label':'归还借阅记录，返回主梦','realm_return':True},{'label':'继续探索','leave':True}),dissolution_reward=0)
    events=[return_event]
    # 散落风味事件：每层各一张，小奖励一次性（呼应「不白拿」口径）。
    CARD_TEXTS = (
        '借阅人：——（被撕去）。归还日期写的是「借阅之门打开之前」。',
        '借阅人栏是一片晕开的墨。备注：本人已随第七次修订合并。',
        '借阅人只画了一扇窗。管理员的批注：人不在，窗口照常开放。',
        '四行笔迹互相涂改，每一行都声称前一行是抄错的自己。',
        '借阅人栏空着。背面一行小字：目录未完成，姓名暂缺。',
    )
    MARGIN_TEXTS = (
        '页边写着：「外墙不是墙，是还没写完的封面。」',
        '「页码乱了不要紧，要紧的是有人肯把它们排回去。」',
        '「窗换了一扇，看见的庭院就换了一座——庭院其实没动。」',
        '「声音分开存放，才吵不起来；吵起来的都进了同一页。」',
        '「最后一册永远写不完。写完的那天，就没有下一页了。」',
    )
    for slot, p in enumerate(scattered[:2]):
        if slot == 0:
            events.append(WorldEvent(event_id=f'library-card-{depth}',catalog_id='event.library.card',
                name='旧借书卡',x=p[0],y=p[1],description='一张泛黄的借书卡插在书目缝里，借阅人一栏只剩半个名字。',
                kind='compound',bound=True,dissolution_reward=0,dialogue=(CARD_TEXTS[depth-1],),
                options=({'label':'读卡面残字','library_command':'read_card'},
                         {'label':'放回去','leave':True})))
        else:
            events.append(WorldEvent(event_id=f'library-margin-{depth}',catalog_id='event.library.margin',
                name='写满批注的桌角',x=p[0],y=p[1],description='桌角压着半册旧批注，页边写满不同笔迹。',
                kind='compound',bound=True,dissolution_reward=0,dialogue=(MARGIN_TEXTS[depth-1],),
                options=({'label':'顺着批注想一会儿','library_command':'read_margin'},
                         {'label':'擦掉批注','library_command':'wipe_margin'},
                         {'label':'合上','leave':True})))
    events.append(WorldEvent(event_id=f'library-lights-{depth}',catalog_id='event.library.lights',
        name='阅读灯控制台',x=sx+2,y=sy,description='一排黄铜开关嵌在木台里，标着本层各盏阅读灯的位置。',
        kind='compound',bound=True,dissolution_reward=0,dialogue=('开关对两边的眼睛一视同仁。拨一下花一行动；地上的东西不受影响。',),
        options=({'label':'关闭阅读灯','library_command':'lights','enabled':False},
                 {'label':'点亮阅读灯','library_command':'lights','enabled':True},{'label':'保持现状','leave':True})))
    # 抄写台（玩法增量）：付一点心智抄一页换清醒；scriptorium 层（4）必在，
    # 其余层若房间列表里有抄写室也放。
    script_rooms=[r for r in plan.rooms if r['purpose']=='scriptorium']
    if script_rooms:
        r0=script_rooms[0];rx0,ry0,rx1,ry1=r0['rect']
        desk_p=next(((x,y) for y in range(ry0+2,ry1-1) for x in range(rx0+2,rx1-1)
                     if not plan.cells[y][x].solid and (x,y) not in axis_set
                     and plan.cells[y][x].wall_kind in ('','木桌子','胡桃木书架')), (rx0+3,ry0+3))
        events.append(WorldEvent(event_id=f'library-scribe-{depth}',catalog_id='event.library.scribe',
            name='抄写佣金台',x=desk_p[0],y=desk_p[1],
            description='台角码着一叠待抄的公函，旁边压着佣金单：抄一页，付一点心神。',
            kind='compound',bound=True,dissolution_reward=0,
            dialogue=('抄写讲究手稳；佣金按页现结，从不拖欠。',),
            options=({'label':'付 1 点心智，抄一页（清醒+2）','library_command':'scribe'},
                     {'label':'只翻翻样张','leave':True})))
    if depth<5:
        room=plan.rooms[0];x0,y0,x1,y1=room['rect']
        p=next(((x,y) for y in range(y1,y0-1,-1) for x in range(x0,x1+1)
            if not plan.cells[y][x].solid and (x,y) not in {plan.spawn,plan.exit}
            and max(abs(x-sx),abs(y-sy))>=4), (cx,sy-5))
        events.append(WorldEvent(event_id=f'library-optional-{depth}',catalog_id=f'event.library.optional.{depth}',
            name=('目录查询台','错页索引柜','同庭异窗','双声校勘台')[depth-1],x=p[0],y=p[1],
            description='台面上的机关积着薄灰，看起来很久没人动过。',kind='compound',bound=True,dissolution_reward=0,
            dialogue=(LIBRARY_HINTS[depth-1],'随便看，不要钱；复位随时可做。'),options=(
              {'label':'观察','library_command':'observe'},
              {'label':('查询收藏位置','交换两张页码','比较两个窗口','并置两组书稿')[depth-1],'library_command':'organize'},
              {'label':'复位','library_command':'reset'}, {'label':'离开','leave':True})))
    else:
        x,y=plan.core_anchor
        events.append(WorldEvent(event_id='library-core-table',catalog_id='event.library.core',name='中央誊本台',x=x+1,y=y,
            description='誊本台摊着一部厚得反常的目录，纸页边缘全是空着的条目栏。',kind='compound',bound=True,dissolution_reward=0,
            dialogue=('未尽目录问：你愿意接受唯一、永久正确的定义吗？','只是读一读，它不会动怒。一旦应战，各条回廊都能避开它的索引线。'),
            options=({'label':'拒绝被定稿，回应未尽目录','library_command':'start'},{'label':'暂不回应','leave':True})))
        records=('秩序保护人：被保存的人不必再怕遗忘。','秩序删掉人：所有不合目录的声音都被擦去。','人主动请求被保留：并非每一次归档都是强迫。')
        for i,text in enumerate(records):
            events.append(WorldEvent(event_id=f'library-record-{i}',catalog_id=f'event.library.record.{i}',name=f'矛盾记录·{i+1}',
                x=x-4+i*4,y=y+4,description=text,kind='compound',bound=True,dissolution_reward=0,dialogue=(text,),
                options=({'label':'记下记录','library_command':'record','record':i},{'label':'离开','leave':True})))
    state._pending_realm_events=events
    state._pending_realm_items=[]
    # 层间下潜守门（2026-10-14）：读借书卡 + 读批注 + 整理目录机关，
    # 集齐才可向更深层下潜（npc_gate）。散落事件依赖房间候选格，动态登记；
    # 第 5 层没有下潜，不设防。
    required=[]
    if any(e.event_id==f'library-card-{depth}' for e in events):required.append('card')
    if any(e.event_id==f'library-margin-{depth}' for e in events):required.append('margin')
    if depth<5:required.append('optional')
    state.realm_features['library_gate']={'required':required,'done':[]}
    # Cabinets share one claim per floor, including choosing a different item.
    # Two equipment rewards across exploration plus one optional finale reward.
    if depth in (1,4):
        choices=('bookmark','index','fold','card') if depth==1 else ('paperweight','lens','quill','testimony')
        from ..data.items import ITEM_DEFINITIONS
        events.append(WorldEvent(event_id=f'library-cabinet-{depth}',catalog_id='event.library.cabinet',
            name='一次借阅的藏品柜',x=cx+2,y=sy-3,description='藏品柜的玻璃擦得很亮，四件小东西各占一格。',
            kind='compound',bound=True,dissolution_reward=0,dialogue=('只能借走一件。中途换主意不算违约，想换别的也还来得及。',),
            options=tuple({'label':'借阅'+ITEM_DEFINITIONS['library.'+k]['name'],'library_command':'borrow_item','item_id':'library.'+k} for k in choices)
            + ({'label':'稍后借阅','leave':True},)))

def spawn(state,depth,rng):
    if depth==5:return
    reserved={(e.x,e.y) for e in state._pending_realm_events}|{(e.x,e.y) for e in state._pending_realm_entities}
    pos=(state.player.x,state.player.y)
    candidates=[(x,y) for y in range(3,state.height-3) for x in range(3,state.width-3)
        if not state.cell(x,y).solid and (x,y) not in reserved and not state.entity_at(x,y)
        and max(abs(x-pos[0]),abs(y-pos[1]))>=8 and not state.cell(x,y).liquid]
    rng.shuffle(candidates)
    normal=list(LIBRARY_ANOMALIES)[:8]
    # At most one binder, and one/two intense identities; counts stay 6/7/8/8.
    binder=False
    count=(6,7,8,8)[depth-1]
    for i,p in enumerate(candidates[:count]):
        aid=rng.choice(list(LIBRARY_ANOMALIES)[8:11]) if depth>1 and i<(1 if depth<4 else 2) else rng.choice(normal if not binder else normal[:7])
        binder|=aid=='library.binder'
        e=state.add_defined_enemy(aid,*p)
        e.active_skill_state['max_integrity']=e.integrity

def on_defeat(state,enemy):
    if enemy.catalog_id!='library.core' or state.realm_id!='library_palace':return
    core=state.realm_features['core']
    if core['status']=='complete':return
    core['status']='defeated';core['exit_unlocked']=True
    state.enemy_skill_fields=[]
    for e in state.enemies:
        e.active_skill_state.pop('pending',None)
        e.active_skill_state.pop('library_second_beat',None)
        if e.main_id==enemy.id:e.integrity=0;e.drop_spawned=True
    for event in state.events:
        if event.catalog_id=='event.library.core':
            event.options=ENDING_OPTIONS
            event.resolved=False
            event.dialogue=('未尽目录散成散页。你可以保存秩序，承认未定，或带走不完整版本。',
               tr('你读过 {n} 份彼此矛盾的记录。三个选择都能返回主梦。',
                  n=len(state.realm_features.get('records',()))))
    state.messages.append(tr('未尽目录不再替你定稿。中央誊本台等待你的选择。'))

def ensure_library_gate(state):
    """层间守门账本：install 时建立；旧存档缺字段时按当前层实况懒重建。"""
    features=state.realm_features
    gate=features.get('library_gate')
    depth=state.realm_depth
    required=[]
    if any(e.event_id==f'library-card-{depth}' for e in state.events):required.append('card')
    if any(e.event_id==f'library-margin-{depth}' for e in state.events):required.append('margin')
    if depth<5 and any(e.catalog_id.startswith('event.library.optional') for e in state.events):required.append('optional')
    claims=features.get('scattered_claims',{})
    done=[v for v in claims.values() if v in ('card','margin')]
    # Old releases could erase the only reading option before recording progress.
    for e in state.events:
        if (e.catalog_id == 'event.library.margin' and e.options
                and all(o.get('leave') for o in e.options)):
            done.append('margin')
    for e in state.events:
        if e.catalog_id.startswith('event.library.optional') and features.get('optional',{}).get(e.event_id,{}).get('organized'):
            done.append('optional')
    if gate is None:
        gate={'required':required,'done':[]}
    gate['done']=list(dict.fromkeys([*gate['done'], *done]))
    features['library_gate']=gate
    state.realm_gate_open=all(k in gate['done'] for k in gate['required'])
    if state.realm_gate_open:
        state.realm_puzzle_solved[depth]=True
    return gate


def _note_library_gate(state,key):
    """记账一项下潜手续；集齐即写 realm_puzzle_solved 并点亮本层门纹。"""
    was_open=state.realm_gate_open
    gate=ensure_library_gate(state)
    if key not in gate['required'] or was_open:return
    if key not in gate['done']:gate['done'].append(key)
    ensure_library_gate(state)
    if state.realm_gate_open:
        state.messages.append(tr('本层的手续齐了——下潜的门纹亮起来了。'))
    else:
        state.messages.append(tr('下潜手续：{have}/{total}；还差 {n} 项。',
            have=len(gate['done']),total=len(gate['required']),
            n=len(gate['required'])-len(gate['done'])))


def _respond(state,event,option):
    command=option.get('library_command')
    if not command:return None
    if (state.realm_id!='library_palace' or not any(e is event for e in state.events)
            or max(abs(state.player.x-event.x),abs(state.player.y-event.y))>1):
        return ActionResult(False,'这条借阅记录不属于当前层。')
    features=state.realm_features
    if command=='lights':
        changed=False
        for p in features.get('lights',()):
            changed = state.set_light_enabled(*p,bool(option.get('enabled'))) or changed
        return ActionResult(changed,'阅读灯已点亮。' if option.get('enabled') else '阅读灯已关闭。')
    if command in ('observe','organize','reset'):
        key=event.event_id;status=features['optional'].setdefault(key,{'organized':False,'rewarded':False,'page_order':[2,1],'manuscripts':[[2,1],[1,2]]})
        if command=='observe':
            if state.realm_depth==2:
                return ActionResult(False,tr('索引柜目前页码为{pages}；相邻两页可交换，正序会指出收藏位置。',pages=status['page_order']))
            if state.realm_depth==4:
                return ActionResult(False,tr('两组书稿目前为{drafts}；并置后它们会按同一阅读次序排列。',drafts=status['manuscripts']))
            return ActionResult(False,'目录和两份页码可以互相对照。')
        if command=='reset':
            status.update(organized=False,page_order=[2,1],manuscripts=[[2,1],[1,2]])
            return ActionResult(True,'页码回到初始位置。')
        if status['organized']:return ActionResult(False,'这份目录已经整理。')
        if state.realm_depth==2:status['page_order'].reverse()
        if state.realm_depth==4:status['manuscripts']=[sorted(pages) for pages in status['manuscripts']]
        status['organized']=True
        _note_library_gate(state,'optional')
        if not status['rewarded']:
            # Information rewards cannot be swallowed by a full inventory.
            features['known_connections'] = [list(features['exit']), list(features['main_axis'][0])]
            status['rewarded']=True
            state.restore_resource('imagination',2)
        return ActionResult(True,'目录指出了一条干燥回廊；想象力也补回来两点。')
    if command=='record':
        i=option['record']
        if i not in features['records']:features['records'].append(i)
        return ActionResult(False, ('已被收录，但目录仍允许变化。' if features['core'].get('ending')=='keep' else '')+'记录已保留；你仍可提出自己的版本。')
    if command=='borrow_item':
        key=event.event_id
        claims=features.setdefault('cabinet_claims',{})
        permitted={o.get('item_id') for o in event.options if o.get('library_command')=='borrow_item'}
        item_id=option.get('item_id')
        if claims.get(key) or item_id not in permitted:return ActionResult(False,'这一次的借阅名额已经用掉了。')
        item=state._make_item(item_id)
        try:state._add_inventory_item(item)
        except ValueError:return ActionResult(False,'行囊放不下；借阅名额还留着。')
        claims[key]=item_id
        event.options=({'label':'离开藏品柜','leave':True},)
        return ActionResult(True,tr('你把{name}借走了。',name=tr(item.name)))
    if command == 'scribe':
        claims=features.setdefault('scattered_claims',{})
        if claims.get(event.event_id):
            return ActionResult(False,'今天的佣金份额已经结清；台面收拾干净了。')
        if state.mind<=1:
            return ActionResult(False,'心智不够撑过一页抄写；歇会再来。')
        claims[event.event_id]='scribe'
        from .settlement import REASON_ABILITY_COST, settle_delta
        settle_delta(state, 'mind', -1, reason=REASON_ABILITY_COST, source='图书馆手续')
        state.restore_resource('lucidity',2)
        event.options=({'label':'离开佣金台','leave':True},)
        return ActionResult(True,'一页抄完，笔画整齐；清醒补回两点。')
    if command == 'read_card':
        claims=features.setdefault('scattered_claims',{})
        if claims.get(event.event_id):
            return ActionResult(False,'这张卡你已经读过；只剩半个名字。')
        claims[event.event_id]='card'
        _note_library_gate(state,'card')
        state.restore_resource('imagination',1)
        event.options=({'label':'放回去','leave':True},)
        return ActionResult(True,'残名让你想起自己的名字也是一点点拼回来的；想象力补回一点。')
    if command == 'read_margin':
        claims=features.setdefault('scattered_claims',{})
        if claims.get(event.event_id):
            return ActionResult(False,'这条批注你已经读过；页边只剩熟悉的笔迹。')
        claims[event.event_id]='margin'
        _note_library_gate(state,'margin')
        state.restore_resource('lucidity',1)
        event.options=({'label':'擦掉批注','library_command':'wipe_margin'},
                       {'label':'合上','leave':True})
        return ActionResult(True,'批注替你把没说清的事说清了；清醒补回一点。')
    if command == 'wipe_margin':
        claims=features.setdefault('scattered_claims',{})
        claims[event.event_id]='margin'
        _note_library_gate(state,'margin')
        event.options=({'label':'合上','leave':True},)
        return ActionResult(True,'你把批注擦干净了。桌面露出原来的木色，谁的观点都没留下。')
    core=features['core']
    if command=='start':
        if core['status']!='waiting':return ActionResult(False,'未尽目录已被回应。')
        p=tuple(features['core_anchor'])
        if state.entity_at(*p):return ActionResult(False,'誊本台前被占据；腾出位置后再回应。')
        boss=state.add_defined_enemy('library.core',*p)
        boss.active_skill_state['max_integrity']=boss.integrity
        boss.alert_state='追踪';boss.last_seen_x=state.player.x;boss.last_seen_y=state.player.y
        core['status']='fighting'
        return ActionResult(True,'未尽目录开始写下你的定义；索引线会先预告落点。')
    if command=='ending':
        ending=option.get('ending')
        if ending not in ('keep','blank','borrow') or core['status']!='defeated' or core['rewarded']:
            return ActionResult(False,'目录上的选择已经保存，或战斗尚未结束。')
        if ending=='borrow':
            item=state._make_item('library.index')
            try:state._add_inventory_item(item)
            except ValueError:return ActionResult(False,'意识行囊已满；目录会保留选择，整理后再借书。')
        elif ending=='keep':
            state._apply_direct_portent(state.player, 'calmed', 6)
            features['known_connections'] = [list(features['exit']), list(features['main_axis'][0])]
        else:
            state.restore_resource('mind',6);state.restore_resource('imagination',6)
        core.update(status='complete',ending=ending,rewarded=True,exit_unlocked=True)
        event.options=({'label':'返回主梦','realm_return':True},{'label':'留在这里','leave':True})
        event.dialogue=({'keep':'你保存目录，也保留被收录者改变自己的余地。','blank':'空页不是错误；你把尚未定义的空间留给自己。','borrow':'你带走尚未写完的索引；它只辨认已遇见的人，不能替世界定稿。'}[ending],)
        return ActionResult(True,event.dialogue[0])
    return ActionResult(False,'没有可执行的借阅操作。')


def respond(state,event,option):
    result=_respond(state,event,option)
    if result is not None:result.message=tr(result.message)
    return result
