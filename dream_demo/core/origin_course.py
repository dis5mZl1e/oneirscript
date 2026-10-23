"""Versioned origin practice. Evidence is durable; practice growth stays local.

The legacy twelve-step saves keep their original map and step semantics.
New courses use this bounded, declarative checklist instead of key counters.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from ..i18n import tr

# 课程地图与子目标表的版本：旧版十二步档留在自己那张已退役的 0 层图上，
# 载入时只备份并如实告知，不会被改写成这一版。
COURSE_TEMPLATE_VERSION = 2

# Each fact denotes a successful action or an actually displayed view. Deferred
# modules are intentionally absent from the recommendation chain, never passed
# just because the player opened an unrelated panel.
_ROWS = (
 ('A1','梦的起始：行动与时间','沿入口短路走到◇，再等待一次。查看与取消不会推进时间；行动耗时随速度变化。','moved waited reached_move'),
 ('A2','右栏与焦点','打开一个右栏页签，使用 / 切换焦点。七页签分别管理行囊、征兆、装备、洞察、观测、操作与任务。','panel_opened focus_switched'),
 ('A3','查看自己的状态','分别打开自我察觉、噪音混乱、完整键位和设置。自我察觉中展开一个属性，读基础值与来源。','self_opened self_expanded signals_opened help_opened settings_opened'),
 ('A4','观察与自动行走','观察中选择◇以外的可达位置，自动前往后停止。再次开始导航并主动取消；不可达不行动。','observed autowalk_arrived path_cancelled'),
 ('B1','知道地形不等于看见','观察 B 区隔墙侧室的地形图，然后绕到墙后读取实际内容。地图全知只在本层生效。','chart_observed side_room_seen'),
 ('B2','从上到下读一格','在物品区水边打开格子详情，查看生物、物品、材料与地板的实际层次。','layered_detail_seen'),
 ('B3','分层与地势','用F3或Alt+V打开分层观察，Tab切换低、中、高层；Alt+G查看地势，Enter查看本格详情，再返回原场景。','layers_opened layer_low_seen layer_middle_seen layer_high_seen elevation_seen layer_detail_seen layers_closed'),
 ('B4','光照不是材料本色','操作 B 区的灯，比较真实照明变化。详情里的材料身份不随光色改变。','light_toggled'),
 ('C1','近战与关系','走向战斗区玩偶，命中后读取它的完整度和状态。稳定的向导不是战斗目标。','struck_doll enemy_detail_opened'),
 ('C2','先瞄准，再出手','F 瞄准，O 辅助选敌，Tab 自由落点。先取消一次，再实际命中靶；取消不扣弹药。','aim_cancelled aim_assisted aim_free fired_hit'),
 ('C3','让弹道通过','观察靶道障碍和通路，在畅通位置命中远靶。不要浪费弹药试穿墙。','blocked_aim clear_shot'),
 ('D1','寻找行囊中的物品','在物品区收纳教材，打开物品详情并尝试搜索、筛选、排序。','picked_up item_detail_opened searched filtered sorted'),
 ('D2','使用和消耗','使用一份可用教材，读取真实效果并比较余量。投掷是另外的行为。','item_used'),
 ('D3','方向与落点投掷','物品菜单 Q 进入投掷瞄准，方向键或鼠标选方向和距离，Enter／点击确认。先 Esc 取消一次，再把普通教材投到近处玩偶格、诱饵投到远处。普通无伤害物不会砸伤目标；近处不超过2格，远处至少3格。','throw_plain throw_functional throw_near throw_far throw_cancelled'),
 ('D4','容器与台面','先从水边取玻璃瓶，在水格使用并盛装、倒出。站到石台旁，在物品菜单 P／点击「放到台面」，然后用行动键取回；投掷也能落到台面，放置不会触发物品的撞击效果。','filled poured table_placed table_retrieved'),
 ('E1','联想盘：拿放与旋转','打开联想盘，按 a 拿放、R 旋转，Enter 确认整理。草稿未确认时不生效。','board_committed board_rotated'),
 ('E2','装备的句子与效果','阅读盘面整句并确认；在自我察觉中查看装备属性来源。补丁睡衣放入第3列可组成持有句。','board_committed board_sentence_seen equipment_source_seen'),
 ('E3','让条件与行为成句','盐渍线圈放在第1列，水枪放同一行第5列。确认后条件只约束同行行为；湿润导电位置才能放行。','conductive_sentence condition_compared'),
 ('E4','记忆与洞察','从日志借用被动教材，查看记忆来源与洞察规则，再投出诱饵验证回响。借用成长在离开前归还。','memory_practiced memory_seen insight_seen insight_practiced'),
 ('F1','学习与构想','使用借用书卷学习一个现有构想，在操作页查看说明并成功施放；只有成功施放才算完成。','ability_learned ability_cast'),
 ('F2','篡改：先读原句','选择实际目标、程度和条件，读准确报价。先取消一次，再成功提交一笔修改。','tamper_cancelled degree_seen conditions_seen tamper_committed'),
 ('F3','代价与时机','施放构想后提交篡改，再打开噪音混乱详情观察混乱和连续压力。不要为演示副作用反复冒险。','ability_cast tamper_committed chaos_after_tamper_seen'),
 ('F4','多个目标与地图预览','在 F 区两块液体之间选择具体来源，按 V 查看地图再返回编辑；草稿应保持不变。','tamper_regions_seen tamper_map_returned'),
 ('G1','听见自己的动作','比较 G 区的安静与发声路线，打开噪音详情读取修正来源。读数是预计声径，不是累积槽。','quiet_preview noisy_preview signals_opened'),
 ('G2','声音与调查','向导可开始声音练习：用借用诱饵把能听声的练习对手引向声源，再绕掩体离开。可在日志重置。','sound_investigated sound_disengaged'),
 ('G3','听觉与实际视野','在日志开始听闻练习，到 G 区南侧隔墙北面 (15,31) 等待真实钟声；打开噪音详情读取方向线索，再绕过隔墙看声源。地形已知不代表看见生物；借用「听声辨向」后等待，可多读远近档。','heard_hidden heard_detail_seen hearing_source_seen'),
 ('H1','征兆会结束','在环境样本获得征兆，查看后离开来源，等待它自然结束。练习有代价，可重置恢复。','portent_gained portent_seen portent_ended'),
 ('H2','有限材料的相变','向导开始环境练习后，观察隔离池的水和水蒸气；用真实火源触发一次转换，读取新材料。','phase_changed phase_detail_seen'),
 ('H3','连锁也会影响自己','在隔离池使用燃烧类教材，从安全通道观察真实点燃与材料变化；别站在落点上。','fire_started fire_observed'),
 ('I1','对话、交换与赠品','与出口纸偶聊天，完成一次付费交换和一次限领赠品；领完还可以聊天。借用品不带出教学层。','npc_talked trade_done gift_done'),
 ('I2','接取与交付','纸偶可委托你取回物品区的练习物；在任务日志看缺少项，带回后交付，也可放弃重接。','practice_accepted practice_log_seen practice_delivered'),
 ('I3','离开教程','本层随时 N 下潜，不要求站到出口。正式主梦与梦中梦各看自己的下潜条件。打开日志阅读出口说明。','exit_read'),
 ('I4','保存与恢复','F10 / Alt+Q 保存退出，再继续入梦。存档保留练习进度；离开后第1层恢复原探索设置。','course_resumed'),
)
_PENDING = {}
MODULES = tuple(dict(id=code, title=title, body=body, requires=tuple(facts.split()),
                     pending=_PENDING.get(code,''), zone=code[0])
                for code,title,body,facts in _ROWS)
BY_ID = {m['id']:m for m in MODULES}


def localized(module, field):
    from ..i18n import get_language
    if get_language()=='en':
        from .origin_course_en import COPY
        return COPY[module['id']][0 if field=='title' else 1]
    return tr(module[field])

# Only growth/resource fields are restored. World time and action IDs stay
# monotonic; exploration, UI preferences and tutorial completion are not reset.
_LOAN_FIELDS = (
 'mind','lucidity','imagination','max_mind','max_lucidity','max_imagination',
 'abilities','ability_cooldowns','redacted_abilities','ability_turns','library_bookmark',
 'memory_fragments','memory_effect_awards','insights','pending_memory','pending_insight',
 'chaos','chaos_decay_credit','tamper_pressure','tamper_pressure_gap','tamper_pressure_idle',
 'projectile_charges','fire_unlocked','board_cooldowns','board_buffer','board_pending',
 'equipment_damage_credit','equipment_event_budget','equipment_marks',
 'stasis_turns','vanish_turns','resonance_turns','quests','quest_baselines',
 'gift_claims','npc_traded_options','npc_free_claims','run_stats','book_offer_sequence',
 'map_memory_enabled','imagination_regen_credit','identity_state','world_tamper_deletes',
 'free_liquid_moves','free_actions','free_action_until','free_move_pending','parry_charges','parry_until','overclock_turns',
 'drug_debts','drug_debt_version','modem_boost_until','modem_recovery_until','item_grant_counts',
 'light_turns','portent_ward_turns','portent_ward_id','steal_cap','round_debt','viscous_debt',
 '_action_count','quiet_step_ready',
 'quiet_step_charges','quiet_step_until','echo_ward_until','masked_step_until',
 'sound_bearing_until','buzzing_echo_enabled','ash_memory_settled','heard_sound_clues',
 'delayed_sounds','delayed_fuel',
)
LOAN_DEFINITIONS = ('water_gun','spellbook','buzz_lure','molotov','warm_water')


def is_course(state):
    return (getattr(state, 'depth', 1) == 0 and not getattr(state, 'realm_id', None)
            and getattr(state, 'tutorial', {}).get('version') == COURSE_TEMPLATE_VERSION)


def protected_route(state,x,y):
    """Keep the fixed through-routes usable; exercise interiors stay mutable."""
    return is_course(state) and (x in (8,9,28,29,48,49) or y in (5,6,17,18,28,29))


def ensure_terrain_chart(state):
    """Grant the origin layer's chart without converting legacy course progress.

    All origin 0 layers are initially known, including saved legacy layouts.
    Snapshot their actual cells; never substitute the new course template or
    enable the global terrain enhancement.
    """
    if state.depth != 0 or state.realm_id or state.map_form != '梦的起始': return
    from .vision.knowledge import _cell_terrain
    layer = state.terrain_memory.setdefault(state.layer_key(),{})
    if state.tutorial.get('chart_supplied'): return
    for y,row in enumerate(state.cells):
        for x,cell in enumerate(row):
            layer.setdefault((x,y),_cell_terrain(cell, -1))
    state.tutorial['chart_supplied'] = True


def start(state):
    from ..mapgen.origin import ZONE_CENTRES
    state.tutorial.update(version=COURSE_TEMPLATE_VERSION,completed=[],facts=[],zones={k:list(v) for k,v in ZONE_CENTRES.items()},
                          paused=False,practice_quest='none')
    baseline = {k:deepcopy(getattr(state,k)) for k in _LOAN_FIELDS if hasattr(state,k)}
    baseline['inventory'] = [asdict(i) for i in state.inventory]
    baseline['board'] = state.board.to_dict()
    state.tutorial['loan_baseline'] = baseline
    state.tutorial['loan_started_time'] = state.time
    state.map_memory_enabled = True
    state.tutorial['loan_ids'] = []
    for definition in LOAN_DEFINITIONS:
        item=state._make_item(definition)
        state.inventory.append(item)
        state.tutorial['loan_ids'].append(item.instance_id)
    state.tutorial['loan_items'] = [asdict(i) for i in state.inventory
                                     if i.instance_id in state.tutorial['loan_ids']]
    from .entities import WorldItem
    state.tutorial['loan_world_items']=[]
    for definition,x,y in (('glass_bottle',10,18),('warm_water',12,18),('warm_water',8,16)):
        item=state._make_item(definition)
        state.world_items.append(WorldItem(item,x,y))
        state.tutorial['loan_ids'].append(item.instance_id)
        state.tutorial['loan_world_items'].append(dict(item=asdict(item),x=x,y=y))
    state._add_tutorial_doll(12,18).move_time=99999
    player_fields=('portents', 'frozen_turns','blind_turns','slow_turns')+tuple(
        key for key in state.player.__dataclass_fields__ if key.startswith('portent_'))
    state.tutorial['player_baseline'] = {key:deepcopy(getattr(state.player,key)) for key in player_fields}
    # Real, opt-in switchable light and platform. Their behavior is unchanged.
    lamp=state.cell(28,4); lamp.light_radius=5; lamp.light_on=True
    for x in range(26,30): state.cell(x,8).elevation=x-26
    platform=state.cell(8,16); platform.wall_kind='石台'; platform.solid=True
    platform.height=1; platform.integrity=70
    water=state.cell(12,19); water.liquid=24; water.liquid_kind='水'
    for x in range(4,16): state.cell(x,28).aggregate_variant='空鼓地板'
    state.tutorial['chart_supplied']=False
    ensure_terrain_chart(state)


def entries(state):
    if not is_course(state): return []
    done=set(state.tutorial.get('completed',())); skipped=set(state.tutorial.get('skipped',()))
    return [dict(m,status='done' if m['id'] in done else 'pending' if m['pending'] else
                 'skipped' if m['id'] in skipped else 'todo') for m in MODULES]


def current(state):
    if not state.tutorial.get('active') or state.tutorial.get('paused'): return None
    values=entries(state); index=int(state.tutorial.get('step',0))
    return values[index] if 0<=index<len(values) else None


def note(state,*facts):
    if not is_course(state): return
    old=set(state.tutorial.get('facts',()))
    state.tutorial['facts']=sorted(old.union(facts))


def pump(state):
    facts=set(state.tutorial.get('facts',()))
    # Existing engine evidence is valid regardless of recommended task order.
    flags=state.tutorial_events
    for key in ('struck_doll','fired_hit','board_committed','board_rotated','npc_talked','autowalk_arrived'):
        if key in flags: facts.add(key)
    if flags.get('panel_opened'): facts.add('panel_opened')
    if flags.get('observe_cell') is not None: facts.add('observed')
    if (state.player.x,state.player.y)==tuple(state.tutorial['stations']['move_target']): facts.add('reached_move')
    if 32<=state.player.x<=37 and state.player.y<=9: facts.add('side_room_seen')
    from .tutorial import _wet_gate_on_live_path
    if _wet_gate_on_live_path(state): facts.add('conductive_sentence')
    if {'condition_on','condition_off'}<=facts: facts.add('condition_compared')
    if state.player.portents: facts.add('portent_gained')
    elif 'portent_gained' in facts: facts.add('portent_ended')
    uid=state.tutorial.get('sound_opponent')
    opponent=next((e for e in state.enemies if e.id==uid and e.integrity>0),None) if uid else None
    if opponent is not None:
        if opponent.alert_state!='未察觉': facts.add('sound_investigated')
        elif 'sound_investigated' in facts: facts.add('sound_disengaged')
        if state.tutorial.get('sound_last_alert')=='追踪' and opponent.alert_state!='追踪':
            facts.add('sound_disengaged')
        state.tutorial['sound_last_alert']=opponent.alert_state
    # A real heard pulse is evidence even when it happened before selecting G3.
    uid=state.tutorial.get('hearing_opponent')
    source=next((e for e in state.enemies if e.id==uid and e.integrity>0),None) if uid else None
    if source is not None:
        started=state.tutorial.get('hearing_started',state.time)
        if any(not c.get('known') and c.get('time',-1)>=started
               and (c.get('x'),c.get('y'))==(source.x,source.y)
               for c in state.heard_sound_clues):
            facts.add('heard_hidden')
    if state.tutorial.get('phase_before'):
        water=sum(state.cell(x,y).liquid for y in range(28,31) for x in range(33,36)
                  if state.cell(x,y).liquid_kind=='水')
        steam=sum(state.cell(x,y).gas for y in range(28,31) for x in range(33,36)
                  if state.cell(x,y).gas_kind=='水蒸气')
        if water<24 and steam>12: facts.add('phase_changed')
    if state.run_stats.get('ignitions',0)>state.tutorial['loan_baseline']['run_stats'].get('ignitions',0):
        facts.add('fire_started')
    state.tutorial['facts']=sorted(facts)
    state.tutorial['completed']=sorted(set(state.tutorial.get('completed',())).union(
        m['id'] for m in MODULES if not m['pending'] and set(m['requires'])<=facts))
    state.tutorial_events.clear()
    _advance(state)


def _advance(state):
    unavailable=set(state.tutorial.get('completed',()))|set(state.tutorial.get('skipped',()))
    index=max(0,int(state.tutorial.get('step',0)))
    while index<len(MODULES) and (MODULES[index]['id'] in unavailable or MODULES[index]['pending']): index+=1
    state.tutorial['step']=index
    # All objectives may finish while the player keeps practicing. N still works.
    if index>=len(MODULES): state.tutorial['active']=False


def select(state,module_id):
    if not is_course(state) or module_id not in BY_ID: return False
    if BY_ID[module_id]['pending']: return False
    state.tutorial.update(active=True,paused=False,step=next(i for i,m in enumerate(MODULES) if m['id']==module_id))
    skipped=state.tutorial.get('skipped',[])
    if module_id in skipped: skipped.remove(module_id)
    return True


def skip(state):
    item=current(state)
    if not item: return ''
    state.tutorial['skipped']=list(dict.fromkeys([*state.tutorial.get('skipped',()),item['id']]))
    _advance(state)
    return tr('已跳过：{title}。',title=tr(item['title']))


def reset_practice(state):
    """Explicit top-up of the same loan instances, never a new random book."""
    if not is_course(state): return False
    from .entities import Item
    loan_ids=set(state.tutorial.get('loan_ids',()))
    baseline=state.tutorial['loan_baseline']
    # A reset of stock doesn't unlearn anything or reset stable book quote IDs.
    inventory={i.instance_id:i for i in state.inventory}
    for payload in state.tutorial.get('loan_items',()):
        uid=payload['instance_id']
        if uid in inventory:
            inventory[uid].quantity=max(inventory[uid].quantity,payload['quantity'])
        else:
            # Remove the same loan from the floor before returning it.
            state.world_items[:]=[entry for entry in state.world_items if entry.item.instance_id!=uid]
            state.inventory.append(Item(**deepcopy(payload)))
    from .entities import WorldItem
    for entry in state.tutorial.get('loan_world_items',()):
        payload=entry['item']; uid=payload['instance_id']
        # Earlier v2 courses hid the only bottle under the stationary doll.
        # An explicit refill repairs that managed spawn without moving the doll
        # or relocating an unrelated item carried in the save.
        if payload['definition_id']=='glass_bottle' and (entry['x'],entry['y'])==(12,18):
            entry['x']=10
        state.inventory[:]=[item for item in state.inventory if item.instance_id!=uid]
        state.world_items[:]=[e for e in state.world_items if e.item.instance_id!=uid]
        state.world_items.append(WorldItem(Item(**deepcopy(payload)),entry['x'],entry['y']))
    if state.tutorial.get('loan_world_items'):
        cell=state.cell(12,18)
        cell.liquid=24; cell.liquid_kind='水'
        water=state.cell(12,19)
        if not water.solid and water.liquid_kind in ('','水'):
            state._add_liquid(water,'水',max(0,24-water.liquid))
        state._reset_material_index()
    state.projectile_charges=max(state.projectile_charges,3)
    # Resource audit: values are restored through the shared settlement bridge
    # instead of direct assignments, while preserving the max(...) semantics.
    from .settlement import write_resource
    write_resource(state, 'mind', max(state.mind, min(state.max_mind, baseline['mind'])))
    write_resource(state, 'lucidity', max(state.lucidity, min(state.max_lucidity, baseline['lucidity'])))
    write_resource(state, 'imagination', max(state.imagination, min(state.max_imagination, baseline['imagination'])))
    return True


def finish_loans(state):
    if not is_course(state) or not state.tutorial.get('loan_baseline'): return
    from .entities import Item
    from ..equipment.board import EquipmentBoard
    baseline=deepcopy(state.tutorial['loan_baseline'])
    # Earlier version-2 snapshots predate these acoustic states. No such
    # practice preparation existed at entry, so do not export a borrowed one.
    for key,value in dict(quiet_step_charges=0,quiet_step_until=0,echo_ward_until=0,
                          masked_step_until=0,sound_bearing_until=0,buzzing_echo_enabled=True,
                          ash_memory_settled=[],heard_sound_clues=[],delayed_sounds=[],delayed_fuel=[],
                          drug_debts=[],drug_debt_version=0,modem_boost_until=0,modem_recovery_until=0,item_grant_counts={}).items():
        baseline.setdefault(key,value)
    elapsed = max(0, state.time - state.tutorial.get('loan_started_time', state.time))
    for deadline in ('modem_boost_until', 'modem_recovery_until'):
        if baseline[deadline] > 0:
            baseline[deadline] += elapsed
    for debt in baseline['drug_debts']:
        debt['next_due'] += elapsed
        debt['deadline'] += elapsed
    state.inventory=[Item(**payload) for payload in baseline.pop('inventory')]
    state.board=EquipmentBoard.from_dict(baseline.pop('board'))
    for name,value in baseline.items(): setattr(state,name,value)
    for key,value in state.tutorial.get('player_baseline',{}).items(): setattr(state.player,key,deepcopy(value))
    for key in ('portent_deadlines','portent_protection'):
        if key not in state.tutorial.get('player_baseline',{}): setattr(state.player,key,{})
    state.construct_environments.clear()
    state.doll_respawns.clear()
    state._sync_equipment_hooks()
    state.tutorial['loans_returned']=True


def control(state,operation):
    """Journal and guide call the same validated, tutorial-only operations."""
    from .entities import ActionResult, WorldItem
    if not is_course(state): return ActionResult(False,tr('本层没有练习场。'))
    if operation.startswith('select:'):
        changed=select(state,operation.partition(':')[2])
        return ActionResult(changed,tr('已选择教学目标。') if changed else tr('此练习尚待前置机制接入。'))
    if operation=='pause':
        state.tutorial['paused']=not state.tutorial.get('paused',False)
        return ActionResult(True,tr('教学提示已切换；任务进度保留。'))
    if operation=='reset':
        reset_practice(state)
        return ActionResult(True,tr('已归还遗失教材并补充练习资源；原有正式物品不变。'))
    if operation=='passives':
        needed=('蜂鸣回响','听声辨向')
        memory_ready=('lighthouse_keeper_memory' in state.memory_fragments
                      or state.pending_memory=='lighthouse_keeper_memory')
        if memory_ready and all(state.insight_active(key) for key in needed):
            return ActionResult(False,tr('这份练习教材已经借出。'))
        if state.pending_insight or state.pending_memory:
            return ActionResult(False,tr('请先完成或取消当前替换，再借用下一份教材。'))
        if not memory_ready: state._add_memory('lighthouse_keeper_memory')
        if state.pending_memory:
            state.tutorial['passives_borrowed']=True
            return ActionResult(True,tr('先完成记忆替换，再从日志借用洞察教材；不会同时打开两种替换。'))
        for key in needed:
            if not state.insight_active(key): state._grant_insight(key)
            if state.pending_insight: break  # never overwrite an unresolved choice
        state.tutorial['passives_borrowed']=True
        if 'lighthouse_keeper_memory' in state.memory_fragments:
            note(state,'memory_practiced')
        return ActionResult(True,tr('被动教材仅本层生效；请查看来源，并用诱饵验证回响。'))
    if operation=='hearing':
        # The existing clock pulse is the source; this command creates no clue
        # and advances no time. The player must actually be in hearing range.
        from .generation import GenerationMixin
        from .vision.cache import invalidate
        wall={(x,32) for x in range(12,18)}
        pos=(15,33)
        previous=state.tutorial.get('hearing_opponent')
        occupied={(state.player.x,state.player.y)}|{(e.x,e.y) for e in state.enemies
                  if e.integrity>0 and e.id!=previous}
        belongings={(e.x,e.y) for e in (*state.world_items,*state.events)}
        from .construct_environments import protected_geometry
        if ((wall|{pos}) & (occupied|belongings)
                or state.cell(*pos).solid
                or any(protected_geometry(state,*p) or state.cell(*p).liquid
                       or state.cell(*p).gas or state.cell(*p).plant
                       for p in wall|{pos})):
            return ActionResult(False,tr('练习位置被占用，请先让开。'))
        state.enemies[:]=[e for e in state.enemies if e.id!=previous]
        for x,y in wall: GenerationMixin.configure_wall(state.cell(x,y),'坚硬聚合墙')
        enemy=state.add_enemy(label='听闻练习声源',x=pos[0],y=pos[1],integrity=12,
                              move_time=99999,attack_time=99999,vision=0,trait='clock_pulse',
                              relation='失控意识',drop_id=None,dissolution_reward=0,
                              catalog_id='anomaly.unknown')
        enemy.pulse_clock=10
        state.tutorial['hearing_opponent']=enemy.id
        state.tutorial['hearing_started']=state.time
        state.heard_sound_clues[:]=[c for c in state.heard_sound_clues
                                   if (c.get('x'),c.get('y'))!=pos]
        invalidate(state)
        return ActionResult(True,tr('听闻练习已开始：到 G 区隔墙北面 (15,31)，等待钟声，再打开噪音详情；可从墙侧绕到声源。'))
    if operation=='noise':
        previous=state.tutorial.get('sound_opponent')
        positions=((5,29),(6,29),(5,30),(6,30))
        position=next((p for p in positions if p!=(state.player.x,state.player.y)
                       and not state.cell(*p).solid and (state.entity_at(*p) is None
                       or state.entity_at(*p).id==previous)),None)
        if position is None: return ActionResult(False,tr('练习位置被占用，请先让开。'))
        state.enemies[:]=[e for e in state.enemies if e.id!=previous]
        enemy=state.add_enemy(label='听声练习对手',x=position[0],y=position[1],integrity=12,move_time=2,
                              attack_time=99,relation='失控意识',vision=2,drop_id=None,
                              dissolution_reward=0,catalog_id='anomaly.unknown')
        state.tutorial['sound_opponent']=enemy.id
        state.tutorial['sound_last_alert']='未察觉'
        return ActionResult(True,tr('声音练习已开始；对手会调查真实声源。请在 G 区操作。'))
    if operation=='environment':
        area={(x,y) for y in range(27,32) for x in range(32,37)}
        border={p for p in area if p[0] in (32,36) or p[1] in (27,31)}
        occupied={(state.player.x,state.player.y)}|{(e.x,e.y) for e in state.enemies if e.integrity>0}
        belongings={(e.x,e.y) for e in (*state.world_items,*state.events)}
        if area & occupied or border & belongings:
            return ActionResult(False,tr('练习位置被占用，请先让开。'))
        # A small sealed basin has no infinite source and no exclusive through
        # route. Reset touches its managed material only, not player belongings.
        for y in range(27,32):
            for x in range(32,37):
                cell=state.cell(x,y)
                if x in (32,36) or y in (27,31):
                    cell.solid=True; cell.wall_kind='玻璃幕墙'; cell.integrity=40
                else:
                    cell.solid=False; cell.wall_kind=''; cell.liquid=cell.gas=cell.flame=0
                    cell.liquid_kind=cell.gas_kind=''; cell.aggregate_variant='普通聚合物'
        cell=state.cell(34,29)
        cell.liquid=24; cell.liquid_kind='水'; cell.gas=12; cell.gas_kind='水蒸气'
        cell.aggregate_variant='灼热聚合物'
        state.tutorial['phase_before']=[cell.liquid,cell.gas]
        sample=state.cell(29,28)
        sample.liquid=12; sample.liquid_kind='稀释记忆'; sample.aggregate_variant='粗糙聚合物'
        state._reset_material_index()
        from .vision.cache import invalidate
        invalidate(state)
        return ActionResult(True,tr('环境练习已开始：H 区封闭浅池有有限的水和水蒸气，受热后真实转换。'))
    if operation=='tamper_samples':
        for x,y in ((46,18),(54,18)):
            cell=state.cell(x,y)
            cell.liquid=24; cell.liquid_kind='水'; cell.aggregate_variant='粗糙聚合物'
        state._reset_material_index()
        return ActionResult(True,tr('F 区两份有限液体样本已备好。'))
    if operation=='accept':
        if state.tutorial['practice_quest'] not in ('none','abandoned'):
            return ActionResult(False,tr('这项练习委托已经接取。'))
        item=state._make_item('glass_bottle')
        state.tutorial['practice_item_uid']=item.instance_id
        state.world_items.append(WorldItem(item,14,18))
        state.tutorial['practice_quest']='active'
        note(state,'practice_accepted')
        return ActionResult(True,tr('练习委托：取回物品区的练习玻璃杯，交给出口纸偶。无正式奖励。'))
    if operation=='deliver':
        # UI proximity is insufficient: commands and stale submissions share this gate.
        guide=next((enemy for enemy in state.enemies
                    if enemy.npc_kind=='npc.origin_greeter' and enemy.integrity>0
                    and max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y))<=1),None)
        if guide is None:
            return ActionResult(False,tr('请把练习玻璃杯带回出口纸偶旁边再交付。'))
        uid=state.tutorial.get('practice_item_uid')
        item=next((i for i in state.inventory if i.instance_id==uid),None)
        if state.tutorial['practice_quest']!='active' or item is None:
            return ActionResult(False,tr('请先接取委托，并取回物品区的练习玻璃杯。'))
        state.inventory.remove(item)
        state.tutorial['practice_quest']='done'
        note(state,'practice_delivered')
        state._action_time(1)
        return ActionResult(True,tr('练习委托已交付；没有正式奖励或任务名额变动。'))
    if operation=='abandon':
        if state.tutorial['practice_quest']!='active': return ActionResult(False,tr('没有进行中的练习委托。'))
        uid=state.tutorial.get('practice_item_uid')
        state.world_items[:]=[e for e in state.world_items if e.item.instance_id!=uid]
        state.inventory[:]=[i for i in state.inventory if i.instance_id!=uid]
        state.tutorial['practice_quest']='abandoned'
        return ActionResult(True,tr('已放弃练习委托；可重新接取。'))
    return ActionResult(False,tr('没有这项练习操作。'))


def observe_ui(app):
    """Sample visible, read-only UI state. No simulated actions or key counters."""
    state=app.session.state
    if not is_course(state) or app.home_mode: return
    facts=[]
    if app.panel_mode in ('inventory','equipment','portents','insights','catalog','actions','tasks'):
        facts.append('panel_opened')
    if app.panel_mode=='tasks':
        facts.append('exit_read')
        if state.tutorial['practice_quest']=='active': facts.append('practice_log_seen')
    if app.panel_mode=='insights': facts.append('insight_seen')
    if app.panel_mode in ('pause_settings','home_settings'): facts.append('settings_opened')
    if app.controls_help_open: facts.append('help_opened')
    if app._self_audit_visible():
        facts.append('self_opened')
        if app._sa_expanded: facts.append('self_expanded')
        if app._sa_category=='sources':
            rows=app._sa_last_sections.get('sources',())
            if any(row.get('source_kind')=='memory' and row.get('source_id') in state.memory_fragments
                   for row in rows): facts.append('memory_seen')
            live={item.instance_id for item in state.equipment.items()}
            if any(row.get('source_kind')=='equipment' and row.get('source_id') in live for row in rows):
                facts.append('equipment_source_seen')
    if app.signal_detail_open:
        facts.append('signals_opened')
        if 'tamper_committed' in state.tutorial['facts']: facts.append('chaos_after_tamper_seen')
    uid=state.tutorial.get('hearing_opponent')
    source=next((e for e in state.enemies if e.id==uid and e.integrity>0),None) if uid else None
    if app.signal_detail_open and source is not None and 'heard_hidden' in state.tutorial['facts']:
        if any(not c.get('known') and (c.get('x'),c.get('y'))==(source.x,source.y)
               and state.time-int(c.get('time',0))<state._clue_retention()
               for c in state.heard_sound_clues): facts.append('heard_detail_seen')
    if source is not None and state.is_visible(source.x,source.y): facts.append('hearing_source_seen')
    if app.cell_detail_target is not None:
        facts.append('cell_detail_opened')
        x,y=app.cell_detail_target
        if (state.is_visible(x,y) and state.entity_at(x,y) is not None
                and any((e.x,e.y)==(x,y) for e in state.world_items) and state.cell(x,y).liquid>0):
            facts.append('layered_detail_seen')
        if state.is_visible(x,y) and state.cell(x,y).flame>0: facts.append('fire_observed')
        if state.is_visible(x,y) and 33<=x<=35 and 28<=y<=30 and 'phase_changed' in state.tutorial['facts']:
            facts.append('phase_detail_seen')
    if app.anomaly_detail_target is not None: facts.append('enemy_detail_opened')
    if app.item_menu_target is not None: facts.append('item_detail_opened')
    if app.qol_searching: facts.append('searched')
    if app.inventory_filter!='全部': facts.append('filtered')
    if app.inventory_sort!='原序': facts.append('sorted')
    if app.panel_mode=='portents' and state.player.portents: facts.append('portent_seen')
    if app.board_editor is not None: facts.append('board_sentence_seen')
    if getattr(app,'_aim_assist_pos',None) is not None: facts.append('aim_assisted')
    if getattr(app,'_aim_free_cursor',None) is not None: facts.append('aim_free')
    target=getattr(app,'_aim_free_cursor',None) or getattr(app,'_aim_assist_pos',None)
    if app.aiming and target is not None and state.is_visible(*target):
        from .throwing import flight_path
        path=flight_path((state.player.x,state.player.y),target)
        if any(state.is_visible(x,y) and state.cell(x,y).solid for x,y in path): facts.append('blocked_aim')
        from ..equipment.runtime import condition_matches
        for row in state.equipment.formation().rows:
            if row.condition and row.condition.kind=='conductive' and row.status=='ready':
                matches=condition_matches(row.condition,state,cell=target)
                facts.append('condition_on' if matches else 'condition_off')
    editor=app.world_tamper_editor
    if editor is not None:
        facts.append('degree_seen')
        if editor.focus=='condition' or editor.condition_ids: facts.append('conditions_seen')
        if editor.slot.region_members: facts.append('tamper_regions_seen')
    if app.observe_mode and app.observe_cursor is not None:
        facts.append('observed')
        if state.cell_knowledge(*app.observe_cursor).sources==('tutorial_chart',): facts.append('chart_observed')
    if 4<=state.player.x<=15 and state.player.y==28: facts.append('noisy_preview')
    if 4<=state.player.x<=15 and state.player.y==30: facts.append('quiet_preview')
    previous=getattr(app,'_course_ui_previous',None)
    current=(id(state),app.aiming,bool(app.path),editor is not None,app.cursor_zone,
             app.layer_observation is not None,state.action_seq,bool(editor and editor.map_preview),
             app.throw_item_index is not None)
    if previous and previous[0]==id(state):
        if previous[1] and not current[1] and previous[6]==current[6]: facts.append('aim_cancelled')
        if previous[2] and not current[2] and previous[6]==current[6]: facts.append('path_cancelled')
        if previous[3] and not current[3] and previous[6]==current[6]: facts.append('tamper_cancelled')
        if previous[4]!=current[4]: facts.append('focus_switched')
        if previous[5] and not current[5]: facts.append('layers_closed')
        if previous[7] and not current[7] and editor is not None: facts.append('tamper_map_returned')
        if len(previous)>8 and previous[8] and not current[8] and previous[6]==current[6]:
            facts.append('throw_cancelled')
    if current[5]: facts.append('layers_opened')
    if app.layer_observation is not None and app.layer_observation.layer=='elevation': facts.append('elevation_seen')
    if app.layer_observation is not None:
        if app.layer_observation.layer in ('low','middle','high'):
            facts.append('layer_'+app.layer_observation.layer+'_seen')
        if app.cell_detail_target is not None:
            facts.append('layer_detail_seen')
    app._course_ui_previous=current
    if facts: note(state,*facts)


def action_result(state,command,args,result,before):
    if not is_course(state) or not result.changed or (result.data or {}).get('refusal'): return
    if (state.tutorial.get('passives_borrowed') and
            'lighthouse_keeper_memory' in state.memory_fragments):
        note(state,'memory_practiced')
    data=result.data or {}
    if any(key in data for key in ('throw_aim','fire_once_aim')): return
    simple={'move':'moved','wait':'waited','toggle_light':'light_toggled','pickup':'picked_up',
            'collect_items':'picked_up','take_from':'picked_up','container_fill':'filled',
            'container_pour':'poured','commit_board':'board_committed',
            'throw_target':'throw_done','throw':'throw_done','put_on_table':'table_placed',
            'commit_tamper':'tamper_committed'}
    fact=simple.get(command)
    if fact: note(state,fact)
    if command in ('throw','throw_target') and data.get('position'):
        from .content import ITEM_DEFINITIONS
        effect=ITEM_DEFINITIONS.get(data.get('item'),{}).get('effect','')
        from .throwing import LANDING_EFFECTS
        note(state,'throw_functional' if effect in LANDING_EFFECTS else 'throw_plain')
        origin=before.get('position',(state.player.x,state.player.y))
        distance=max(abs(data['position'][i]-origin[i]) for i in (0,1))
        if distance>0: note(state,'throw_near' if distance<=2 else 'throw_far')
        from ..materials import TABLE_KINDS
        if data.get('landed_item_id') and data.get('surface') in TABLE_KINDS:
            note(state,'table_placed')
    if command in ('take_from','pickup'):
        from ..materials import TABLE_KINDS
        if data.get('surface') in TABLE_KINDS: note(state,'table_retrieved')
    if command=='collect_items' and data.get('table_positions'):
        note(state,'table_retrieved')
    if command in ('use','choose_event_option') and state.run_stats.get('items_used',0)>before.get('items_used',0):
        note(state,'item_used')
    if data.get('ability'): note(state,'ability_cast')
    if len(state.abilities)>before.get('abilities',len(state.abilities)): note(state,'ability_learned')
    if command=='choose_npc_option':
        option=before.get('option',{})
        if option.get('cost') and option.get('gain'): note(state,'trade_done')
        if data.get('gift'): note(state,'gift_done')
    if command.startswith('fire') and 'fired_hit' in state.tutorial_events: note(state,'clear_shot')
    if command in ('throw','throw_target') and data.get('item')=='buzz_lure' and state.insight_active('蜂鸣回响'):
        note(state,'insight_practiced')
    # Persist successful action evidence before saving, independent of render
    # cadence. View-only objectives remain tied to actual UI observations.
    pump(state)
