"""Budget-neutral tactical arrangements on ordinary, already reachable ground."""
from __future__ import annotations

import random

from .constants import Material
from ..i18n import tr

WET_ARCHIVE = 'encounter.wet_archive'
WATER_BUDGET = 90
REWRITING_CORRIDOR = 'encounter.rewriting_corridor'
REWRITE_DELAY = 6
MULTI_SOLUTION_GATE = 'encounter.multi_solution_gate'
#: 多解门禁：三格厚的纸墙近路；打穿 / 点燃 / 篡改三条解法都成立，外圈仍可绕行。
GATE_WALL_KIND = '潮解纸墙'


def _emit_encounter(state, record, kind, stage, *, source=None, cells=(), facts=(),
                    visual_key='cast.rewrite_corner', tier=2, theme='paper',
                    outcome='release'):
    # 只登记真实遭遇状态转变；生成/checkpoint/只读 tick 不经过这里。
    from ..core.visual_events import emit_visual
    values = {'encounter_id': str(record.definition_id),
              'facility_uid': str(record.scene_uid),
              'stage': str(stage)}
    for name, value in facts:
        values[str(name)] = value
    return emit_visual(state, kind=kind, outcome=outcome, source=source,
                       targets=(), paths=(), affected_cells=tuple(cells),
                       visual_key=visual_key, tier=int(tier), theme=theme,
                       facts=tuple(values.items()), layer_key='encounter',
                       source_id=str(record.scene_uid))


def _local_encounters(state):
    return [record for record in state.world_ledger.facilities.values()
            if record.layer_key==state.layer_key() and record.definition_id.startswith('encounter.')]


def seed_wet_archive(state, vault_info=None):
    """Arrange existing loot, an ordinary anomaly and water; never add rewards.

    The marker survives save/trim, so reseeding cannot refill the room. A normal
    layer snapshot preserves the actual remaining water, loot and light state.
    """
    from .scenes import _layer_record, _origin_candidates, _protected_regions

    if state.realm_id or not 3 <= state.depth <= 12:
        return None
    uid=f'{state.run_uid}|{state.layer_key()}|{WET_ARCHIVE}'
    if uid in state.world_ledger.facilities:
        return state.world_ledger.facilities[uid]
    if _layer_record(state) is not None or _local_encounters(state):
        return None  # One major arranged encounter per layer.
    rng=random.Random(state.seed ^ (state.depth*104729) ^ 0xA4C11)
    regions=_protected_regions(state,vault_info)
    def protected(x,y):
        return any(a<=x<=c and b<=y<=d for a,b,c,d in regions)
    def away(x,y):
        return max(abs(x-state.player.x),abs(y-state.player.y))>3 and not protected(x,y)
    guards=[enemy for enemy in state.enemies
            if enemy.integrity>0 and enemy.relation=='失控意识'
            and enemy.anomaly_kind=='普通异象' and not enemy.actor_uid
            and not enemy.main_id and enemy.trait!='staircase' and away(enemy.x,enemy.y)]
    rewards=[entry for entry in state.world_items
             if entry.item.category in ('摄入物','易逝物') and away(entry.x,entry.y)]
    donors=[(x,y) for y,row in enumerate(state.cells) for x,cell in enumerate(row)
            if cell.liquid_kind in ('水','导电液态记忆') and cell.liquid>0 and not cell.solid
            and not cell.wall_kind and away(x,y)
            and not any(max(abs(x-npc.x),abs(y-npc.y))<=2
                        for npc in state.enemies if npc.relation=='稳定意识')]
    kind=next((kind for kind in ('水','导电液态记忆')
               if sum(state.cell(x,y).liquid for x,y in donors
                      if state.cell(x,y).liquid_kind==kind)>=WATER_BUDGET),None)
    if not guards or not rewards or kind is None:
        return None
    donors=[point for point in donors if state.cell(*point).liquid_kind==kind]
    definition={'footprint':(7,5),'keys':{'room':{'center':(3,2),'size':(5,3)}}}
    from ..materials import floor_effect_for
    origin=next((point for point in _origin_candidates(state,definition,vault_info)
                 if all(state.cell(point[0]+dx,point[1]+dy).floor is Material.PLAIN_AGGREGATE
                        and not floor_effect_for(state.cell(point[0]+dx,point[1]+dy)).slide
                        and not floor_effect_for(state.cell(point[0]+dx,point[1]+dy)).conveyor
                        for dy in range(1,4) for dx in range(1,6))),None)
    if origin is None:
        return None
    ox,oy=origin
    water=tuple((ox+dx,oy+2) for dx in (2,3,4))
    bypass=tuple((ox+dx,oy+3) for dx in range(1,6))
    # A shallow physical basin keeps a finite pool useful until arrival. It is
    # ordinary elevation, not paused liquid simulation or an inexhaustible source.
    banks={(x+dx,y+dy) for x,y in water for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))}-set(water)
    for x,y in banks:
        state.cell(x,y).elevation=max(2,state.cell(x,y).elevation)
        state.world_ledger.mark_terrain(state.layer_key(),x,y,elevation=state.cell(x,y).elevation)
    for x,y in water:
        state.cell(x,y).elevation=0
        state.world_ledger.mark_terrain(state.layer_key(),x,y,elevation=0)
    remaining=WATER_BUDGET
    rng.shuffle(donors)
    for x,y in donors:
        cell=state.cell(x,y)
        taken=min(cell.liquid,remaining)
        cell.liquid-=taken
        remaining-=taken
        if not cell.liquid:cell.liquid_kind=''
        if not remaining:break
    for x,y in water:
        cell=state.cell(x,y)
        cell.liquid_kind=kind;cell.liquid=WATER_BUDGET//len(water)
    guard=guards[rng.randrange(len(guards))]
    guard.x,guard.y=ox+4,oy+2
    guard.path_plan=[];guard.plan_index=0;guard.last_seen_x=guard.last_seen_y=-1
    guard.wandering=False;guard.alert_state='未察觉'
    guard.keeps_watch=True
    reward=rewards[rng.randrange(len(rewards))]
    reward.x,reward.y=ox+5,oy+2
    lamp=state.cell(ox+3,oy+1)
    lamp.light_radius=3;lamp.light_on=True
    state.world_ledger.mark_terrain(state.layer_key(),ox+3,oy+1,
                                   elevation=lamp.elevation,light_radius=3,light_on=True)
    record=state.world_ledger.facility(uid,layer_key=state.layer_key(),definition_id=WET_ARCHIVE,
                                     anchor_uid=f'{ox},{oy}',state='已布置')
    record.layout=dict(origin=origin,water=water,bypass=bypass,lamp=(ox+3,oy+1),
                       reward=(reward.x,reward.y),guard=(guard.x,guard.y))
    record.flags['constructed']=True
    state._material_index_ready=False
    from .vision import cache
    cache.invalidate(state)
    return record


def seed_rewriting_corridor(state,vault_info=None):
    """A finite, warned shortcut between existing rewards, with an outer escape.

    Only an entirely open rectangle may be used. Its boundary stays open, so
    adding interior paper walls cannot disconnect any pre-existing outside path.
    """
    from .scenes import _layer_record,_origin_candidates,_protected_regions
    if state.realm_id or not 3<=state.depth<=12:return None
    uid=f'{state.run_uid}|{state.layer_key()}|{REWRITING_CORRIDOR}'
    if uid in state.world_ledger.facilities:return state.world_ledger.facilities[uid]
    if _layer_record(state) is not None or _local_encounters(state):return None
    regions=_protected_regions(state,vault_info)
    rewards=[entry for entry in state.world_items
             if entry.item.category in ('摄入物','易逝物')
             and max(abs(entry.x-state.player.x),abs(entry.y-state.player.y))>3
             and not any(a<=entry.x<=c and b<=entry.y<=d for a,b,c,d in regions)]
    pair=next(((a,b) for a in rewards for b in rewards
               if a.item.category!=b.item.category),None)
    if pair is None:return None
    definition={'footprint':(7,5),'keys':{'room':{'center':(3,2),'size':(7,5)}}}
    from ..materials import floor_effect_for
    origin=next((point for point in _origin_candidates(state,definition,vault_info)
                 if all(state.cell(point[0]+dx,point[1]+dy).floor is Material.PLAIN_AGGREGATE
                        and state.cell(point[0]+dx,point[1]+dy).light_radius==0
                        and not floor_effect_for(state.cell(point[0]+dx,point[1]+dy)).slide
                        and not floor_effect_for(state.cell(point[0]+dx,point[1]+dy)).conveyor
                        for dy in range(5) for dx in range(7))),None)
    if origin is None:return None
    ox,oy=origin
    walls=tuple((ox+dx,oy+dy) for dy in (1,3) for dx in range(1,6))
    bypass=tuple((ox+dx,oy+dy) for dy in range(5) for dx in range(7)
                 if dx in (0,6) or dy in (0,4))
    for x,y in walls:state.configure_wall(state.cell(x,y),'潮解纸墙')
    for entry,dx in zip(pair,(2,4)):
        entry.x,entry.y=ox+dx,oy+2
    record=state.world_ledger.facility(uid,layer_key=state.layer_key(),definition_id=REWRITING_CORRIDOR,
                                     anchor_uid=f'{ox},{oy}',state='休眠')
    record.layout=dict(origin=origin,walls=walls,bypass=bypass,gate=(ox+3,oy+2),
                       entry=(ox,oy+2),exit=(ox+6,oy+2),rewards=tuple((w.x,w.y) for w in pair))
    record.flags['constructed']=True
    checkpoint_tactical_layouts(state)
    state._material_index_ready=False
    from .vision import cache
    cache.invalidate(state)
    return record


def seed_multi_solution_gate(state,vault_info=None):
    """多解门禁：用真实纸墙挡住一条近路，三条解法与外圈退路都真实存在。

    只在完全开放的矩形里布置；纸墙挡的是**新增近路**，外圈边界保持开放，
    因此不会切断任何原有通路。两件既有物品被分别放到门两侧，形成
    「打穿/点燃/篡改取近路」与「绕外圈多走路」的取舍。
    """
    from .scenes import _layer_record,_origin_candidates,_protected_regions
    if state.realm_id or not 7<=state.depth<=16:
        return None
    uid=f'{state.run_uid}|{state.layer_key()}|{MULTI_SOLUTION_GATE}'
    if uid in state.world_ledger.facilities:
        return state.world_ledger.facilities[uid]
    if _layer_record(state) is not None or _local_encounters(state):
        return None
    regions=_protected_regions(state,vault_info)
    rewards=[entry for entry in state.world_items
             if entry.item.category in ('摄入物','易逝物')
             and max(abs(entry.x-state.player.x),abs(entry.y-state.player.y))>3
             and not any(a<=entry.x<=c and b<=entry.y<=d for a,b,c,d in regions)]
    pair=next(((a,b) for a in rewards for b in rewards if a is not b),None)
    if pair is None:
        return None
    definition={'footprint':(7,5),'keys':{'room':{'center':(3,2),'size':(7,5)}}}
    from ..materials import floor_effect_for
    origin=next((point for point in _origin_candidates(state,definition,vault_info)
                 if all(state.cell(point[0]+dx,point[1]+dy).floor is Material.PLAIN_AGGREGATE
                        and not state.cell(point[0]+dx,point[1]+dy).solid
                        and not floor_effect_for(state.cell(point[0]+dx,point[1]+dy)).slide
                        and not floor_effect_for(state.cell(point[0]+dx,point[1]+dy)).conveyor
                        for dy in range(5) for dx in range(7))),None)
    if origin is None:
        return None
    ox,oy=origin
    gate=tuple((ox+3,oy+dy) for dy in (1,2,3))
    bypass=tuple((ox+dx,oy+dy) for dy in (0,4) for dx in range(6))
    for x,y in gate:
        state.configure_wall(state.cell(x,y),GATE_WALL_KIND)
    for entry,dx in zip(pair,(1,5)):
        entry.x,entry.y=ox+dx,oy+2
    record=state.world_ledger.facility(uid,layer_key=state.layer_key(),
                                       definition_id=MULTI_SOLUTION_GATE,
                                       anchor_uid=f'{ox},{oy}',state='已布置')
    record.layout=dict(origin=origin,gate=gate,bypass=bypass,
                       rewards=tuple((w.x,w.y) for w in pair),
                       entry=(ox,oy+2),exit=(ox+6,oy+2),control=(ox+5,oy+1))
    record.flags['constructed']=True
    checkpoint_tactical_layouts(state)
    state._material_index_ready=False
    from .vision import cache
    cache.invalidate(state)
    return record


def gate_control(record):
    """Old saved layouts gain the same control point without rebuilding loot."""
    point=record.cell('control')
    origin=record.cell('origin')
    return point or ((origin[0]+5,origin[1]+1) if origin else None)


def gate_control_at(state,x,y):
    return next((record for record in _local_encounters(state)
                 if record.definition_id==MULTI_SOLUTION_GATE and gate_control(record)==(x,y)),None)


def _resolve_gate(state,record,method):
    if record.flags.get('resolved'):return
    if not any(not state.cell(x,y).solid for x,y in record.area('gate')):return
    from ..world import facts
    from ..world.relations import player_uid
    record.flags['resolved']=True
    record.flags['resolution_'+method]=True
    record.state='通路已开'
    facts.record(state,'facility',actor_uid=player_uid(state) if method!='material' else '',
        target_uid=record.scene_uid,owner_uid=record.scene_uid,
        position=record.area('gate')[1],cause_uid='gate:'+method,source_kind='encounter',
        before='已布置',after={'state':'通路已开','resolution':method})
    # 一次真实开路只发一次：真实已开格是 after 事实，不再另造第二次爆散。
    opened=tuple((x,y) for x,y in record.area('gate') if not state.cell(x,y).solid)
    _emit_encounter(state,record,'encounter.open','open',
                    source=(opened[0] if opened else None),cells=opened,
                    visual_key='fx.explosion',tier=1,theme='',
                    facts=(('resolution',str(method)),('actual_amount',len(opened))))
    if any(state.is_visible(x,y) for x,y in record.area('gate')):
        state.messages.append(tr('门纹让出了通路，这一次的解法已记下。'))


def note_gate_breach(state,x,y,cause):
    method={'world_tamper':'tamper','projectile':'projectile','hand':'hand'}.get(cause,'material')
    for record in _local_encounters(state):
        if record.definition_id==MULTI_SOLUTION_GATE and (x,y) in record.area('gate'):
            _resolve_gate(state,record,method)


def operate_gate_control(state,x,y):
    """An ordinary, reachable mechanism action; no resource or reward shortcut."""
    from .entities import ActionResult
    from .constants import ActionKind
    if not (0<=x<state.width and 0<=y<state.height):return ActionResult(False,'')
    if max(abs(state.player.x-x),abs(state.player.y-y))>1 or not state.is_visible(x,y):
        return ActionResult(False,'')
    record=gate_control_at(state,x,y)
    if record is None:return ActionResult(False,'')
    if record.flags.get('resolved'):
        return ActionResult(False,tr('这道门纹已经让出了通路。'))
    points=record.area('gate')
    if state.cell(x,y).solid or any(state.cell(*p).solid and state.cell(*p).wall_kind!=GATE_WALL_KIND for p in points):
        return ActionResult(False,tr('门纹的结构已经改变，拨片带不动它。'))
    for point in points:
        cell=state.cell(*point)
        if cell.solid:state.clear_wall(cell)
    _resolve_gate(state,record,'mechanism')
    checkpoint_tactical_layouts(state)
    state._material_index_ready=False
    from .vision import cache
    cache.invalidate(state)
    state._action_time(1,kind=ActionKind.USE)
    message=tr('你拨开门纹，纸墙收进了地面。')
    state.messages.append(message)
    return ActionResult(True,message)


def checkpoint_tactical_layouts(state):
    """Keep authored walls and their later breaches structural, never refill loot."""
    for record in _local_encounters(state):
        if record.definition_id==REWRITING_CORRIDOR:
            cells=(*record.area('walls'),*record.area('gate'))
        elif record.definition_id==MULTI_SOLUTION_GATE:
            cells=record.area('gate')
        else:
            continue
        for x,y in cells:
            cell=state.cell(x,y)
            fields=dict(state.world_ledger.terrain_for(state.layer_key()).get(f'{x},{y}',{}))
            for name in ('solid','wall_kind','height','hardness','thickness','integrity',
                         'aggregate_variant','light_radius','light_on','doorway'):
                fields[name]=getattr(cell,name)
            fields['floor']=cell.floor.value
            state.world_ledger.mark_terrain(state.layer_key(),x,y,**fields)


def tick_tactical_layouts(state,amount):
    if amount<=0:return
    for record in _local_encounters(state):
        if record.definition_id==MULTI_SOLUTION_GATE:
            _resolve_gate(state,record,'material')
            continue
        if record.definition_id!=REWRITING_CORRIDOR or record.state=='已改写':continue
        gate=record.cell('gate')
        if not gate:continue
        if record.state=='休眠':
            if (max(abs(gate[0]-state.player.x),abs(gate[1]-state.player.y))>3
                    or not all(state.is_visible(x,y) for x,y in (gate,*record.area('rewards')))):
                continue
            record.state='预告';record.pending={'remaining':REWRITE_DELAY}
            state.messages.append(tr('走廊的纸纹正在合拢：{n} 个客观回合后，中央通道会变成纸墙。两端仍可退到外圈。',n=REWRITE_DELAY))
            # 首次进入预告只发一次；remaining 来自本次真实写入的 pending。
            _emit_encounter(state,record,'encounter.warning','warning',
                            source=gate,cells=(gate,),
                            facts=(('remaining',REWRITE_DELAY),),
                            outcome='entry')
            continue
        before=record.pending.get('remaining',REWRITE_DELAY)
        remaining=max(0,before-amount);record.pending['remaining']=remaining
        for threshold in (3,1):
            if before>threshold>=remaining and remaining>0:
                state.messages.append(tr('纸纹改写还剩 {n} 个客观回合；可以从任一端退到外圈。',n=remaining))
                # 跨过 3/1 阈值各一次；remaining 与阈值都取自真实倒计时。
                _emit_encounter(state,record,'encounter.countdown','countdown',
                                source=gate,cells=(gate,),
                                facts=(('remaining',remaining),('threshold',threshold)))
        if remaining>0:continue
        x,y=gate;cell=state.cell(x,y)
        occupied=((state.player.x,state.player.y)==gate or state.entity_at(x,y) is not None
                  or any((w.x,w.y)==gate for w in (*state.world_items,*state.events)))
        if occupied or cell.liquid or cell.gas or cell.flame or cell.plant:
            if not record.flags.get('deferred'):
                state.messages.append(tr('中央通道尚有占位或流动材料，纸纹暂缓合拢；移开后才会继续。'))
                record.flags['deferred']=True
                # 暂缓只发一次：断开的括框，不播成墙。
                _emit_encounter(state,record,'encounter.deferred','deferred',
                                source=gate,cells=(gate,),
                                facts=(('remaining',remaining),))
            continue
        # Do not replace a wall or feature the player has installed in the meantime.
        new_wall=()
        if not cell.solid and not cell.wall_kind:
            state.configure_wall(cell,'潮解纸墙')
            if cell.solid and cell.wall_kind==GATE_WALL_KIND:
                new_wall=((x,y),)
        record.state='已改写';record.pending={}
        state.messages.append(tr('中央通道已改写；两侧仍可各自退到外圈，也可以破开纸墙。'))
        if new_wall:
            # 只有真实新生成的纸墙格才播重构；已放其他墙体不画成被替换。
            _emit_encounter(state,record,'encounter.rewrite','rewrite',
                            source=(x,y),cells=new_wall,
                            facts=(('remaining',0),('actual_amount',len(new_wall))))
        state._material_index_ready=False
        from .vision import cache
        cache.invalidate(state)
    checkpoint_tactical_layouts(state)


def hint_at(state,x,y):
    if not state.is_visible(x,y):return ''
    for record in state.world_ledger.facilities.values():
        if record.layer_key!=state.layer_key():continue
        origin=record.cell('origin')
        if origin and origin[0]<=x<origin[0]+7 and origin[1]<=y<origin[1]+5:
            if record.definition_id==WET_ARCHIVE:
                return tr('积液通向深处的显化物；一盏灯照着那里，另一侧留着一条干路。')
            if record.definition_id==REWRITING_CORRIDOR:
                if record.state=='预告':
                    return tr('中央通道将在 {n} 个客观回合后改写；两端通向外圈，纸墙可提前破开。',n=record.pending.get('remaining',0))
                if record.state=='已改写':
                    return tr('中央通道已经改写。两端仍通向外圈；破开纸墙可另留退路。')
                return tr('纸面写着：两侧各有一件用途不同的物品；看清走廊后，中央纸纹会开始合拢。两端通向外圈。')
            if record.definition_id==MULTI_SOLUTION_GATE:
                if record.flags.get('resolved'):
                    return tr('门纹已让出通路，解法已经记下；再次处理不会重复结算。')
                if gate_control(record)==(x,y):
                    return tr('门纹拨片：相邻操作可收起纸墙。可绕行来拨开，或点燃、打穿、篡改纸墙。')
                return tr('纸墙挡住近路：另一侧的拨片能收起它；也可点着、用弹体打穿或改写。外圈始终可绕。')
    return ''
