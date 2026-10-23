"""Finite, locally observed clinic scenes. All ledgers live in realm_features."""
from .entities import WorldEvent, WorldItem, ActionResult
from .constants import ActionKind
from ..i18n import tr
from ..data.hospital import HOSPITAL_NPCS
from .content import ITEM_DEFINITIONS

SCENES = {
 1: (('first_sample', '第一份干净样本'),),
 2: (('open_label', '没写完的标签'), ('wash_what', '洗掉什么')),
 3: (('closed_vessel', '封死的气室'), ('quiet_duct', '安静的回风口')),
 4: (('long_daylight', '过长的白昼'), ('unused_bay', '尚未使用的静养湾')),
 5: (('after_sterile', '停机后的恩典'),),
}
# 散落风味事件文案（每层各一段）：读一次的小奖励，与场景/药箱配给分开。
CHART_TEXTS = (
    '「入院原因：不肯醒来。处置：继续观察。」',
    '「处方栏写着：每天少想一点。签名被划掉过三次。」',
    '「病历记录：患者坚称自己是别人写的批注。结论：无异常。」',
    '「护理记录：白昼延长了四小时，患者要求关灯，被驳回。」',
    '「最后一页：患者痊愈。痊愈的定义由本院保留。」',
)
QUEUE_TEXTS = (
    '叫号屏停在 077。下面一行小字：请 078 号自行入梦。',
    '屏幕滚动着：现在的号码是——闪了闪——还是刚才那个。',
    '屏上只有一句：请叫到名字的就诊者不要回应。',
    '叫号屏排着一长串「无」，偶尔夹一个被划掉的名字。',
    '屏幕黑了一半，剩下半边写着：本日全部就诊完毕。',
)
NPCS = {1: ('triage_bell',), 2: ('dispenser',), 3: ('linen_cart',),
        4: ('linen_cart', 'dispenser'), 5: ('infusion_keeper',)}
NAMES = {'triage_bell': '分诊铃', 'dispenser': '无手药柜',
         'linen_cart': '净衣护理车', 'infusion_keeper': '滴瓶看守'}


def _option(label, operation, **kw):
    return {'label': label, 'hospital_scene': dict(operation=operation, **kw), 'always': True}


def _event(state, key, name, pos, options, description, dialogue):
    uid = f'{state.seed}:hospital:{state.realm_depth}:{key}'
    return WorldEvent(uid, name, *pos, description, dissolution_reward=0,
        catalog_id='event.hospital.scene.'+key, kind='compound', bound=True,
        dialogue=(dialogue,), options=tuple(options)+({'label': '暂不操作', 'leave': True},))


def install_hospital_scenes(state, plan, depth):
    """Call after realm_features and pending events have been initialized."""
    from .realm_architecture import ventilation_clearance
    state.realm_features.setdefault('scene_states', {})
    state.realm_features.setdefault('reward_claims', {})
    state.realm_features['hospital_actor_specs'] = []
    occupied = {(e.x, e.y) for e in state._pending_realm_events}
    occupied.update((tuple(t['port']) for t in plan.tanks))
    occupied.update(tuple(p) for t in plan.tanks for p in (*t['cells'],*t['walls']))
    # Furniture stays clear of dry transit and exits; scenes occupy passable bays.
    vent_clearance=ventilation_clearance(plan.cells)
    candidates = [(x, y) for room in plan.rooms for y in range(room['rect'][1]+1, room['rect'][3])
        for x in range(room['rect'][0]+1, room['rect'][2])
        if not plan.cells[y][x].solid and (x,y) not in plan.protected_cells
        and not plan.cells[y][x].liquid and (x,y) not in occupied
        and (x,y) not in vent_clearance]
    if not candidates:
        candidates = [(plan.spawn[0]+3, plan.spawn[1]-2)]
    def position(near=None):
        # #84（2026-10-14）：设施/事件之间留出空隙——优先取距所有已占点
        # ≥3 格的候选，挤不下逐级放宽（≥2→≥1），绝不因间距耗尽候选池。
        # near：守门人 NPC 钉在出生点附近（入口旁的第一问询处）——取候选池
        # 里离 spawn 最近的一格（spawn 常在走廊，不在房间候选集内）。
        if near is not None and candidates:
            point = min(candidates,
                        key=lambda p: (max(abs(p[0]-near[0]), abs(p[1]-near[1])), p[1], p[0]))
            candidates.remove(point)
            occupied.add(point)
            return point
        for gap in (3, 2, 1):
            for index, point in enumerate(candidates):
                if all(max(abs(point[0]-q[0]), abs(point[1]-q[1])) >= gap
                       for q in occupied):
                    candidates.pop(index)
                    occupied.add(point)
                    return point
        point = candidates.pop(0)
        occupied.add(point)
        return point
    def add(key, name, options, desc, dlg, near=None):
        event = _event(state, key, name, position(near), options, desc, dlg)
        # realm_depth is not necessarily assigned during generation.
        event.event_id = f'{state.seed}:hospital:{depth}:{key}'
        state._pending_realm_events.append(event)
        return event
    for key, name in SCENES[depth]:
        if key == 'first_sample':
            e = add(key,name, [_option('取样并选择载氧棉糖','sample', reward='hospital.oxygen_sugar'),
                _option('取样并选择淋巴素软胶囊','sample',reward='hospital.lymph_capsule')],
                '一只浅槽盛着半槽乳白的淋巴液，水面浮着细小的絮。',
                '淋巴液只伤病原体，不伤人。把它引进槽里、击败它，或沿干路绕行，都算完成观察。')
            p = (e.x+1,e.y)
            if not plan.cells[p[1]][p[0]].solid:
                c=plan.cells[p[1]][p[0]]; c.liquid_kind,c.liquid='淋巴液',8
            state.realm_features['scene_states'][e.event_id]={'sample_pos':p}
            state.realm_features['sample_pathogen_pos']=(e.x,e.y+1)
        elif key == 'open_label':
            e=add(key,name,[_option('封装蓝绿淋巴样本（2单位）','label',material='淋巴液',reward='hospital.diagnostic_slide'),
                _option('封装透明洗兆样本（2单位）','label',material='洗兆液',reward='hospital.filter_sac')],
                '两只空采样管并排躺着，一管贴蓝绿标签，一管透明。',
                '蓝绿管等着「膜边收缩」的样本，透明管等着「计时缩短」的。封装消耗对应样本各2单位，贴错了可以重贴。')
        elif key == 'closed_vessel':
            add(key,name,[_option('阅读实际罐内容与剩余量','vessel')],
                '几只封死的气罐立在架上，玻璃后各有一只取液口，刻度还看得清。',
                '端口可以抽取、定量排放，或者留着不动。读一读余量，什么都不消耗。')
        elif key == 'quiet_duct':
            e=add(key,name,[_option('检查回风服务格','duct')],
                '墙角一扇回风口，灰白的胞尘把格栅糊住了。',
                '排掉胞尘、贴滤膜，或用洗兆液冲一冲，风口都能重新通风。主路上的干路不受这里影响。')
            c=plan.cells[e.y][e.x]; c.gas_kind,c.gas='胞尘',6
            state.realm_features['scene_states'][e.event_id]={'source':(e.x,e.y),'initial_gas':6}
        elif key == 'long_daylight':
            add(key,name,[_option('关闭本地灯段并记录侧室路线','daylight')],
                '这一段的灯全亮着，白光把每条走廊照得发亮。',
                '灯一亮，谁都看得清你。关掉本地灯段后，可以借不透明的侧室藏身；这里只记下这一处路线。')
        elif key == 'wash_what':
            add(key,name,[_option('用洗兆液洗短一项并选洗忆泡腾片','wash',reward='hospital.memory_fizz'),
                _option('用洗兆液洗短一项并选晨醒含片','wash',reward='hospital.morning_lozenge')],
                '一只广口瓶盛着浅蓝的洗兆液，瓶口搁着一支玻璃搅拌棒。',
                '洗掉一项征兆要花2单位洗兆液；正负面征兆都洗得动。')
        elif key == 'unused_bay':
            add(key,name,[_option('使用静养设备：心智+4','rest',resource='mind'),
                _option('使用静养设备：清醒+4','rest',resource='lucidity')],
                '一张静养椅靠着白墙，安全带叠得整整齐齐。',
                '在旁边安稳待上三回合，就能用一次。设备只存着一份恢复，不会提高上限。')
        else:
            add(key,name,[_option('容许差异：缝合线圈','core',reward='hospital.suture_coil',interpretation='容许差异'),
                _option('带走未完成的配液：无垢银剪','core',reward='hospital.suture_shears',interpretation='带走未完成的配液'),
                _option('保持纯净：白昼面罩','core',reward='hospital.lumen_mask',interpretation='保持纯净')],
                '核心停了。无影灯垂在半空，托盘里躺着三件擦净的器械。',
                '三件里只能带走一件：缝合线圈管状态，无垢银剪管材料，白昼面罩管照明。这里和首领奖励共用同一份记录。')
    for event in state._pending_realm_events:
        if event.catalog_id=='event.hospital.scene.after_sterile':
            from ..equipment.shapes import shape_geometry
            previews=[]
            for option in event.options:
                reward=option.get('hospital_scene',{}).get('reward')
                definition=ITEM_DEFINITIONS.get(reward,{})
                if definition.get('shape_id'):
                    cells,_=shape_geometry(definition['shape_id'],0)
                    width=max(x for x,y in cells)+1; height=max(y for x,y in cells)+1
                    pattern='/'.join(''.join('■' if (x,y) in cells else '·' for x in range(width)) for y in range(height))
                    previews.append(tr(definition['name'])+' '+pattern+' '+tr(definition.get('description','')))
            event.dialogue=event.dialogue+tuple(previews)
    for kind in NPCS[depth]:
        pos=position(near=plan.spawn)  # 守门人贴入口（#84）
        spec={'kind':'hospital.'+kind, 'position':pos, 'uid':f'{state.seed}:hospital:{depth}:actor:{kind}'}
        state.realm_features['hospital_actor_specs'].append(spec)
        if kind=='infusion_keeper':
            record=add('record_desk','配液记录台',[_option('阅读已观察的材料效果','record')],
                '一台记录台，屏幕上滚着配液流水。',
                '看守不在了也能读。这里只记观察，不发东西。')
            record.catalog_id='event.hospital.record_desk'
        if kind=='dispenser':
            # 药柜 NPC 会被 spec['position'] 钉到场景格——场景本身贴入口，
            # 守门人才算贴入口（d2 唯一守门人 = 无手药柜）。
            e=add('dispenser',NAMES[kind],[_option('配制洗忆泡腾片：洗兆液2，心智1/清醒1/想象2','fabricate',reward='hospital.memory_fizz',material='洗兆液'),
                _option('配制淋巴胶囊：淋巴液2，心智1/清醒1/想象2','fabricate',reward='hospital.lymph_capsule',material='淋巴液')],
                '一只没有手的药柜，抽屉自己开了又合。',
                '里面只剩一份药材。配制要花对应的液体2单位和一些心智、清醒度、想象——选项上写得明白。行囊满了就先寄存在旁边的药箱。',
                near=plan.spawn)
            e.catalog_id='event.hospital.dispenser'
            spec['service_uid']=e.event_id
            spec['position']=(e.x,e.y)
    if depth in (2,4):
        gear_ids={2:('hospital.hollow_lancet','hospital.lymph_filter','hospital.cerebral_ampoule','hospital.sterile_glove'),
                  4:('hospital.glass_rib','hospital.pulse_tag','hospital.marrow_spoon','hospital.lymph_filter')}[depth]
        gear=add('equipment_case','有限器械柜',[_option('领取'+ITEM_DEFINITIONS[iid]['name'],'box',rewards=(iid,)) for iid in gear_ids],
                 '玻璃柜里摆着四件器械，标签一律朝外。',
                 '四件里挑一件。行囊放不下的话，东西会留在柜旁等你。')
        gear.catalog_id='event.hospital.equipment_case'
    # Three finite medicine units per floor; immediate recovery across five floors = 40.
    supply={1:('hospital.saline' if state.seed%2==0 else 'hospital.marrow_sugar','hospital.oxygen_sugar'),2:('hospital.slow_gel','hospital.memory_fizz'),
            3:('hospital.cerebral_drops','hospital.lymph_capsule'),4:('hospital.porcelain_vitamin','hospital.gentle_sleep'),
            5:('hospital.oral_morning','hospital.immunoglobulin')}[depth]
    tactical={1:'hospital.dream_sensitive',2:'hospital.fever_snow',3:'hospital.morning_lozenge',4:'hospital.pain_sugar',5:'hospital.sterile_chew'}
    supply=supply+(tactical[depth],)
    for event in state._pending_realm_events:
        if event.catalog_id=='event.hospital.scene.unused_bay':
            state.realm_features['scene_states'][event.event_id]={'last_time':state.time,'safe_turns':0}
    box=add('medicine_box','封口药箱',[_option('领取封存药物（满行囊留在箱内）','box',rewards=supply)],
        '一只上了封条的药箱，胶带压得平整。',
        '箱里封着三份药。开箱只此一次，没拿走的会一直留在这里。')
    box.catalog_id='event.hospital.medicine_box'
    if depth==1:
        alternate=('hospital.marrow_sugar' if supply[0]=='hospital.saline' else 'hospital.saline',)+supply[1:]
        box.options=(box.options[0],_option('改选另一份恢复药与两份战术药（仍仅领取三份）','box',rewards=alternate),box.options[-1])
    e=add('liquid_store','有限储液架',[_option('向兼容容器抽取至多6单位','liquid')],
        '架上立着一只标着刻度的储液袋，管子垂下来。',
        '袋里还剩12单位，倒完就没了。装不下的部分会留在袋里。')
    e.catalog_id='event.hospital.liquid_store'
    state.realm_features['scene_states'][e.event_id]={'volume':12,'material':'脑脊液' if depth>=4 else '洗兆液'}
    # A movable one-cell opaque cart, with a logical record rather than NPC collision.
    p=position(); state.configure_wall(plan.cells[p[1]][p[0]],'净衣推车')
    state.realm_features.setdefault('hospital_carts',[]).append({'uid':f'{state.seed}:hospital:{depth}:cart','position':p})
    # 散落风味事件：每层两处，读一次的小奖励（不挤占场景/药箱配给）。
    chart=add('lost_chart','散落的病历夹',[_option('读一遍病历','chart')],
        '一只病历夹掉在推车旁，纸页散开，夹子还咬着最后一页。',
        CHART_TEXTS[depth-1])
    chart.catalog_id='event.hospital.scatter.chart'
    screen=add('queue_screen','停摆的叫号屏',[_option('看一眼最后的号码','queue')],
        '叫号屏斜挂在墙上，一半亮着，号码停了很久。',
        QUEUE_TEXTS[depth-1])
    screen.catalog_id='event.hospital.scatter.queue'
    # 层间下潜守门（2026-10-14）：读病历夹 + 看叫号屏 + 完成一处设施手续，
    # 集齐才可向更深层下潜（npc_gate）。三处每层恒有配给。
    state.realm_features['hospital_gate']={'required':['chart','queue','scene'],'done':[]}


def install_hospital_actors(state):
    from .entities import Entity
    sample=state.realm_features.get('sample_pathogen_pos')
    if sample and not state.realm_features.get('sample_pathogen_installed'):
        if not state.cell(*sample).solid and not state.entity_at(*sample):
            pathogen = next((e for e in state.enemies if e.relation == '失控意识'
                             and 'pathogen' in e.biological_tags), None)
            if pathogen is not None:
                pathogen.x, pathogen.y = sample
                state.realm_features['sample_pathogen_uid']=pathogen.id
        state.realm_features['sample_pathogen_installed']=True
    for spec in state.realm_features.get('hospital_actor_specs',()):
        if any(e.id==spec['uid'] for e in state.enemies):
            continue
        kind=spec['kind'].split('.',1)[1]
        e=Entity(spec['uid'],NAMES[kind],*spec['position'], integrity=20, relation='稳定意识',
                 glyph=HOSPITAL_NPCS[spec['kind']]['glyph'],
                 vision=0, attack_time=99, dissolution_reward=0, npc_kind=spec['kind'])
        e.hospital_state={'anchor':spec['position'],'service_uid':spec.get('service_uid'),'warning':0}
        if state.entity_at(e.x,e.y):
            alternatives=[(e.x+dx,e.y+dy) for dx,dy in ((1,0),(0,1),(-1,0),(0,-1))]
            free=next((p for p in alternatives if not state.cell(*p).solid and not state.entity_at(*p)),None)
            if free: e.x,e.y=free; e.hospital_state['anchor']=free
        state.enemies.append(e)


def _ledger(state,event):
    return state.realm_features.setdefault('scene_states',{}).setdefault(event.event_id,{})


def ensure_hospital_gate(state):
    """层间守门账本：install 时建立；旧存档缺字段时按当前层实况懒重建。"""
    features=state.realm_features
    gate=features.get('hospital_gate')
    done=[]
    for event in state.events:
        if not features.get('scene_states',{}).get(event.event_id,{}).get('claimed'):continue
        if event.catalog_id=='event.hospital.scatter.chart':done.append('chart')
        elif event.catalog_id=='event.hospital.scatter.queue':done.append('queue')
        else:done.append('scene')
    if gate is None:
        gate={'required':['chart','queue','scene'],'done':[]}
    gate['done']=list(dict.fromkeys([*gate['done'], *done]))
    features['hospital_gate']=gate
    state.realm_gate_open=all(k in gate['done'] for k in gate['required'])
    if state.realm_gate_open:
        state.realm_puzzle_solved[state.realm_depth]=True
    return gate


def _note_hospital_gate(state,key):
    """记账一项下潜手续；集齐即写 realm_puzzle_solved 并点亮本层门纹。"""
    was_open=state.realm_gate_open
    gate=ensure_hospital_gate(state)
    if key not in gate['required'] or was_open:return
    if key not in gate['done']:gate['done'].append(key)
    ensure_hospital_gate(state)
    if state.realm_gate_open:
        state.messages.append(tr('本层的手续齐了——下潜的门纹亮起来了。'))
    else:
        state.messages.append(tr('下潜手续：{have}/{total}；还差 {n} 项。',
            have=len(gate['done']),total=len(gate['required']),
            n=len(gate['required'])-len(gate['done'])))


def _material(state,kind,n,commit=False):
    stores=[i for i in state.inventory if i.contents.get(kind,0)>0]
    if sum(i.contents[kind] for i in stores)<n:
        return False
    if commit:
        for i in stores:
            take=min(n,i.contents[kind]); i.contents[kind]-=take; n-=take
            if not i.contents[kind]:
                i.contents.pop(kind)
                i.gas_decay_age.pop(kind,None)
            if not n: break
    return True


def _reward(state,event,ids):
    for iid in ids:
        item=state._make_item(iid)
        try: state._add_inventory_item(item)
        except ValueError: state.world_items.append(WorldItem(item,event.x,event.y))


def resolve_hospital_scene(state,event,op):
    def fail(msg): return ActionResult(False,tr(msg))
    scene_done = {
        'sample': '样本封进了载管。',
        'label': '标签贴好，样本封存。',
        'fabricate': '药片在托盘里落定。',
        'core': '你取走了那件器械。',
        'rest': '你靠着静养椅歇了一回。',
        'box': '你取走了药物。',
        'duct': '回风口重新通风了。',
        'daylight': '灯段熄灭了。',
        'chart': '病历读完了。',
        'queue': '号码看清楚了。',
    }
    if state.realm_id!='white_sanatorium' or event not in state.events:
        return fail('此设施不在当前疗所。')
    if max(abs(event.x-state.player.x),abs(event.y-state.player.y))>1:
        return fail('请先接近设施。')
    ledger=_ledger(state,event); operation=op.get('operation')
    if operation=='fabricate' and any(e.hospital_state.get('service_uid')==event.event_id and
            (e.integrity<=0 or e.hospital_state.get('stopped')) for e in state.enemies):
        return fail('药柜已停止服务；药箱与主路仍可使用。')
    if ledger.get('claimed') and operation not in ('vessel',): return fail('此处库存或奖励已经领取。')
    rewards=[]
    if operation in ('fabricate','sample','label','wash'):
        if operation=='sample':
            pos=ledger.get('sample_pos')
            if not ledger.get('observed') and not (pos and state.can_see(state.player,*pos)):
                return fail('先观察入口浅槽；可以沿干路绕行，不要求击败病原体。')
        kind=op.get('material','洗兆液' if operation=='wash' else '淋巴液')
        if not _material(state,kind,2): return fail(tr('容器里的{material}还差2单位。',material=tr(kind)))
        if operation=='fabricate' and (state.mind<=1 or state.lucidity<=1 or state.imagination<2):
            return fail('心智、清醒度或想象力不够。')
        if operation=='wash' and not state.cleanse_target(state.player): return fail('目前没有可洗征兆。')
        reward=op.get('reward')
        if reward not in ITEM_DEFINITIONS: return fail('物品尚未登记，未支付。')
        if operation=='wash': state.shorten_portent(state.player,3)
        _material(state,kind,2,True)
        if operation=='fabricate':
            from .settlement import REASON_ABILITY_COST, settle_delta
            settle_delta(state, 'mind', -1, reason=REASON_ABILITY_COST, source='配液操作')
            settle_delta(state, 'lucidity', -1, reason=REASON_ABILITY_COST, source='配液操作')
            settle_delta(state, 'imagination', -2, reason=REASON_ABILITY_COST, source='配液操作')
        rewards=[reward]
    elif operation=='core':
        claims=state.realm_features.setdefault('reward_claims',{})
        if not state.realm_features.get('core_defeated'): return fail('核心仍在运行；奖励尚未开放。')
        if claims.get('hospital.core'): return fail('这里的奖励已经领过了；记录仍可阅读。')
        if op['reward'] not in ITEM_DEFINITIONS: return fail('装备尚未登记，未领取。')
        claims['hospital.core']=op['reward']; ledger['interpretation']=op.get('interpretation')
        rewards=[op['reward']]
    elif operation=='rest':
        if ledger.get('safe_turns',0)<3 or not state.hospital_safe_rest(): return fail('尚未连续保持三回合安全。')
        state.restore_resource(op['resource'],4)
    elif operation=='chart':
        state.restore_resource('mind',1)
    elif operation=='queue':
        state.restore_resource('lucidity',1)
    elif operation=='box': rewards=list(op['rewards'])
    elif operation=='duct':
        p=ledger['source']; c=state.cell(*p)
        if c.gas_kind=='胞尘' and c.gas>=6: return fail('胞尘仍堵住服务格；先排气、吸附、洗液处理或沿干路绕行。')
        ledger['guard_available']=1
        for actor in state.enemies:
            if actor.npc_kind=='hospital.linen_cart': actor.hospital_state['guard_available']=1
    elif operation=='daylight':
        sources=sorted(state.realm_features.get('lights',()),key=lambda p:abs(p[0]-event.x)+abs(p[1]-event.y))[:4]
        if not sources: return fail('此处没有灯段。')
        for p in sources: state.set_light_enabled(*p,False)
        ledger['known_route']=[r['rect'] for r in state.realm_features.get('rooms',()) if r['purpose']=='rest_bay'][:1]
    elif operation=='record':
        message=tr('材料观察记录：{records}',records=', '.join(tr(k) for k in state.realm_features.get('hospital_observations',{})) or tr('空'))
        state.messages.append(message)
        return ActionResult(True,message)
    elif operation=='vessel':
        volumes={t['uid']:sum(state.cell(*p).gas for p in t['cells']) for t in state.realm_features.get('tanks',())}
        state.messages.append(tr('气罐实际剩余：{volumes}',volumes=', '.join(tr(t['gas'])+' '+str(volumes[t['uid']]) for t in state.realm_features.get('tanks',()))))
        return ActionResult(True,state.messages[-1],{'tank_volumes':volumes})
    elif operation=='liquid':
        volume=ledger.get('volume',0); kind=ledger['material']
        if not volume: return fail('储液已耗尽。')
        for item in state.inventory:
            spec=state._container_spec(item)
            cap=spec.get('cap',0)-sum(item.contents.values())
            if spec.get('medium')=='liquid' and cap>0 and (spec.get('multi') or not item.contents or kind in item.contents):
                amount=min(6,volume,cap); item.contents[kind]=item.contents.get(kind,0)+amount
                ledger['volume']-=amount
                state.close_event_dialog(); state._action_time(1,ActionKind.USE)
                return ActionResult(True,tr('转移{material}×{amount}；剩余{volume}。',material=tr(kind),amount=amount,volume=ledger['volume']))
        return fail('没有装得下的容器；储液没有动。')
    else: return fail('未知当地操作。')
    _reward(state,event,rewards)
    ledger['claimed']=True; event.resolved=True; event.uses_left=0
    # 层间守门记账（2026-10-14）：散落两件按 catalog_id 归项，其余设施完成
    # 都折算成「一处设施」；claimed 已在上方置位，重复操作会被入口拦下。
    _note_hospital_gate(state, {'event.hospital.scatter.chart':'chart',
        'event.hospital.scatter.queue':'queue'}.get(event.catalog_id,'scene'))
    state.close_event_dialog()
    state.run_stats['events']=state.run_stats.get('events',0)+1
    state._record_catalog_interaction(event.catalog_id,event.name,'site',event.description)
    state._action_time(1,ActionKind.USE)
    message=tr('{name}：{done}',name=tr(event.name),done=tr(scene_done.get(operation,'操作完成。')))
    state.messages.append(message)
    return ActionResult(True,message,{'scene':event.event_id,'rewards':rewards})


def resolve_hospital_npc(state,npc,op):
    if (state.realm_id!='white_sanatorium' or not any(e is npc for e in state.enemies)
            or max(abs(state.player.x-npc.x),abs(state.player.y-npc.y))>1):
        return ActionResult(False,tr('请先接近设备。'))
    if npc.integrity<=0 or npc.hospital_state.get('stopped'): return ActionResult(False,tr('设备已停服；当地记录与撤离仍可使用。'))
    operation=op.get('operation')
    if operation=='service':
        event=next((e for e in state.events if e.event_id==npc.hospital_state.get('service_uid')),None)
        if not event: return ActionResult(False,tr('服务记录不存在。'))
        # Counter access through actor delegates to the same finite ledger.
        choice=dict(op); choice.update(operation='fabricate')
        return resolve_hospital_scene(state,event,choice)
    if operation=='borrow':
        key=npc.id+':borrow'; claims=state.realm_features.setdefault('reward_claims',{})
        if claims.get(key): return ActionResult(False,tr('基础容器已经拿过了。'))
        event=WorldEvent(key,'分诊借用盒',npc.x,npc.y,'')
        _reward(state,event,op.get('rewards',('hospital.sealed_ampoule','hospital.clean_air_bottle')))
        claims[key]=True
    elif operation=='prepare':
        key=npc.id+':prepare'; claims=state.realm_features.setdefault('reward_claims',{})
        if claims.get(key): return ActionResult(False,tr('准备盒已经空了。'))
        _reward(state,WorldEvent(key,'准备盒',npc.x,npc.y,''),[op.get('reward','hospital.slow_gel')]); claims[key]=True
    elif operation=='restore_light':
        key=npc.id+':lamp'; claims=state.realm_features.setdefault('reward_claims',{})
        if claims.get(key): return ActionResult(False,tr('本地灯段已检修，耗材已用完。'))
        sources=sorted(state.realm_features.get('lights',()),key=lambda p:abs(p[0]-npc.x)+abs(p[1]-npc.y))[:4]
        broken=[p for p in sources if not state.cell(*p).light_on]
        if not broken: return ActionResult(False,tr('标示灯段仍然亮着，无需检修。'))
        for p in broken: state.set_light_enabled(*p,True)
        claims[key]=True; npc.hospital_state['guard_available']=1
    elif operation=='guard':
        if not npc.hospital_state.get('guard_available'): return ActionResult(False,tr('请先恢复回风服务格。'))
        if not state.hospital_safe_rest(): return ActionResult(False,tr('当地仍有可见危险。'))
        state.restore_resource('mind',4); npc.hospital_state['guard_available']=0
    elif operation=='record':
        state.messages.append(tr('材料观察记录：{records}',records=', '.join(tr(k) for k in state.realm_features.get('hospital_observations',{})) or tr('空')))
        return ActionResult(True,state.messages[-1])
    else: return ActionResult(False,tr('未知服务。'))
    state.close_npc_dialog(); state._action_time(1,ActionKind.USE)
    npc_done = {
        'borrow': '你取走了容器。',
        'prepare': '药品收进了行囊。',
        'restore_light': '灯段重新亮了起来。',
        'guard': '它守着你歇了一回。',
    }
    return ActionResult(True,tr(npc_done.get(operation,'服务完成。')))


def tick_hospital_scenes(state):
    if state.realm_id!='white_sanatorium': return
    now=state.time
    for event in state.events:
        if event.catalog_id=='event.hospital.scene.first_sample':
            ledger=_ledger(state,event)
            pos=ledger.get('sample_pos')
            if pos and state.can_see(state.player,*pos): ledger['observed']=True
        if event.catalog_id!='event.hospital.scene.unused_bay': continue
        ledger=_ledger(state,event); before=ledger.get('last_time',now-1)
        if now<=before: continue
        near=max(abs(event.x-state.player.x),abs(event.y-state.player.y))<=1
        ledger['safe_turns']=min(3,ledger.get('safe_turns',0)+int(now-before)) if near and state.hospital_safe_rest() else 0
        ledger['last_time']=now
    observations=state.realm_features.setdefault('hospital_observations',{})
    for holder in [state.player]+state.enemies:
        c=state.cell(holder.x,holder.y)
        st=holder.hospital_state
        if st.get('cerebral_left',0)>0: observations['脑脊液：流畅']=True
        if st.get('cleanse_left',0)>0: observations['净化：计时缩短']=True
        previous=st.get('scene_prev_integrity',holder.integrity)
        if ('pathogen' in holder.biological_tags and c.liquid_kind=='淋巴液' and c.liquid>=4
                and holder.integrity<previous): observations['淋巴液：病原体损伤']=True
        st['scene_prev_integrity']=holder.integrity
    for npc in state.enemies:
        if npc.npc_kind!='hospital.linen_cart' or npc.integrity<=0: continue
        c=state.cell(npc.x,npc.y)
        if c.flame or (c.gas_kind=='胞尘' and c.gas>=6):
            x,y=npc.hospital_state['anchor']; anchor=state.cell(x,y)
            if not anchor.solid and not anchor.flame and not (anchor.gas_kind=='胞尘' and anchor.gas>=6): npc.x,npc.y=x,y
        elif int(now)//4>npc.hospital_state.get('patrol_tick',-1):
            npc.hospital_state['patrol_tick']=int(now)//4
            ax,ay=npc.hospital_state['anchor']
            route=[(ax,ay),(ax+1,ay),(ax,ay+1)]
            target=route[(int(now)//4)%3]
            x,y=target
            if (0<=x<state.width and 0<=y<state.height and not state.cell(x,y).solid
                and not state.cell(x,y).flame and state.cell(x,y).gas<6
                and (x,y)!=(state.player.x,state.player.y)
                and not any(e is not npc and e.integrity>0 and (e.x,e.y)==(x,y) for e in state.enemies)):
                npc.x,npc.y=target


def on_hospital_defeat(state,enemy):
    if state.realm_id=='white_sanatorium' and enemy.catalog_id=='hospital.core_sterile_grace':
        state.realm_features['core_defeated']=True
        state.messages.append(tr('核心停机了。记录台的三选一主要报酬已开放。'))


def damage_hospital_actor(state,npc,explicit=False):
    """Call on NPC damage: first accidental hit warns, repeat/explicit stops service."""
    if not npc.npc_kind.startswith('hospital.'): return
    st=npc.hospital_state; st['warning']=st.get('warning',0)+1
    if explicit or st['warning']>=2: st['stopped']=True
    state.messages.append(tr('设备停止可选服务。') if st.get('stopped') else tr('设备发出警告；再次破坏将停止服务。'))


def push_hospital_cart(state,x,y,dx,dy):
    carts=state.realm_features.get('hospital_carts',())
    cart=next((c for c in carts if tuple(c['position'])==(x,y)),None)
    if not cart: return None
    tx,ty=x+dx,y+dy
    protected={tuple(p) for p in state.realm_features.get('protected',())}
    reserved={(e.x,e.y) for e in state.events}|{(e.x,e.y) for e in state.enemies if e.integrity>0}
    if abs(dx)+abs(dy)!=1 or not(0<=tx<state.width and 0<=ty<state.height) or state.cell(tx,ty).solid or (tx,ty) in protected|reserved:
        return ActionResult(False,tr('推车不能推入主路、出口或目标锚点。'))
    source=state.cell(x,y)
    integrity=source.integrity
    state.clear_wall(source); state.configure_wall(state.cell(tx,ty),'净衣推车')
    state.cell(tx,ty).integrity=integrity
    cart['position']=(tx,ty)
    state.player.x,state.player.y=x,y
    state._visible_cache=None
    state._action_time(1,ActionKind.MOVE)
    return ActionResult(True,tr('推车移了一格。'),{'cart':cart['uid'],'position':(tx,ty)})
