from ..i18n import tr
"""Locked literary casts: all consequences occur on world actions."""
def _adjacent(state, enemy):
    return [(enemy.x+dx,enemy.y+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))
            if state._sk_open(enemy.x+dx,enemy.y+dy)]

def cast(state, enemy, skill, binding):
    key=skill.skill_id.split('.',1)[1]
    st=enemy.active_skill_state
    # 2026-10-15 混乱化改造：全部定式施法距离取「技能射程 ∪ 视野」——
    # 视野内就该打得着，不再被表上的小射程捆住。
    reach = max(skill.max_range, enemy.vision)
    if not state._sk_player_visible(enemy,reach):
        return None
    if key in ('question','stroke','index_line','last_page'):
        ray=state._sk_ray(enemy.x,enemy.y,state.player.x,state.player.y,skill.max_cells)
        if not ray: return None
        # The second beat is fixed now; never retarget after the player moves.
        return ray,ray,None,{}
    if key in ('ink','delete'):
        cells=[(state.player.x,state.player.y)]
        if key=='delete':
            cells=[p for p in state._sk_cross(state.player.x,state.player.y,1)
                   if p not in {tuple(q) for q in state.realm_features.get('main_axis',())}][:2]
        if not cells:return None
        return cells,None,None,{}
    if key=='threshold':
        # Only doors explicitly designated optional may be closed.
        cells=[tuple(p) for p in state.realm_features.get('optional_doors',())
               if max(abs(p[0]-enemy.x),abs(p[1]-enemy.y))<=2
               and not state.entity_at(*p) and not state.cell(*p).solid]
        return (cells[:1],None,cells[0],{}) if cells else None
    if key=='omit':
        pids=[pid for pid in enemy.portents if state._sk_portent_kind(pid)=='负面']
        return ([(enemy.x,enemy.y)],None,None,{'pid':pids[0]}) if pids else None
    if key in ('return','foldstep'):
        previous=st.get('library_previous')
        candidates=([tuple(previous)] if key=='return' and previous else _adjacent(state,enemy))
        candidates=[p for p in candidates if state._sk_open(*p) and not state.entity_at(*p)
                    and max(abs(p[0]-enemy.x),abs(p[1]-enemy.y))<=3]
        if key=='foldstep':
            candidates=[p for p in candidates if any(0<=p[0]+dx<state.width and 0<=p[1]+dy<state.height
                        and state.cell(p[0]+dx,p[1]+dy).wall_kind=='胡桃木书架'
                        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))]
        return ([(enemy.x,enemy.y),candidates[0]],None,candidates[0],{}) if candidates else None
    if key=='lamp':
        lamps=[tuple(p) for p in state.realm_features.get('lights',())
               if max(abs(p[0]-enemy.x),abs(p[1]-enemy.y))<=4]
        return (lamps[:1],None,lamps[0],{}) if lamps else None
    if key=='bind':
        paper=[p for p in _adjacent(state,enemy) if state.cell(*p).aggregate_variant=='干纸堆'
               and state.cell(*p).floor_fuel>0]
        if not paper or enemy.portents.get('sk_guard_fold'):return None
        return [paper[0],(enemy.x,enemy.y)],None,paper[0],{}
    if key=='revision':
        if st.get('revision_spent'):return None
        allies=state._sk_allies_near(enemy,4)
        allies=[a for a in allies if not a.portents.get('sk_guard_fold')]
        return ([(allies[0].x,allies[0].y)],None,None,{'ally':allies[0].id}) if allies else None
    if key=='echo':
        live=[e for e in state.enemies if e.main_id==enemy.id and e.integrity>0]
        if len(live)>=2:return None
        free=[p for p in _adjacent(state,enemy) if not state.entity_at(*p)][:2-len(live)]
        return (free,None,None,{}) if free else None
    if key=='blank':
        free=_adjacent(state,enemy)[:2]
        return (free,None,None,{}) if free else None
    return None

def resolve(state,enemy,skill,pending):
    key=skill.skill_id.split('.',1)[1]
    warned=[tuple(p) for p in pending.get('warning_cells',())]
    target=tuple(pending.get('target_cell') or ())
    st=enemy.active_skill_state
    if key in ('question','stroke','index_line','last_page'):
        path=[]
        for p in warned:
            if not state._sk_open(*p):break
            path.append(p)
        if key == 'last_page' and len(path)>1:
            split = max(1, len(path)//2)
            st['library_second_beat'] = {'cells':path[split:], 'path':list(path), 'action':state.action_seq, 'power':state._skill_power(enemy,skill)}
            path = path[:split]
        state._skill_resolve_default_hit(enemy,skill,dict(pending,warning_cells=path,locked_path=path))
        if key=='index_line' and (state.player.x,state.player.y) in path:
            state._grant_portent_direct(state.player, 'sk_blur')
    elif key in ('ink','delete'):
        state._sk_add_field(enemy,'ink',warned,rounds=3)
    elif key=='threshold':
        if target and not state.entity_at(*target) and not state.cell(*target).solid:
            from .generation import GenerationMixin
            GenerationMixin.configure_wall(state.cell(*target),'门')
            st['library_door']={'pos':target,'left':2}
    elif key=='omit':
        pid=pending.get('meta',{}).get('pid')
        if pid:
            for table in (enemy.portents,enemy.portent_attach,enemy.portent_debt,enemy.portent_stacks):table.pop(pid,None)
    elif key in ('return','foldstep'):
        if target and not state._enemy_rooted(enemy) and state._sk_open(*target) and not state.entity_at(*target):
            st['library_previous']=(enemy.x,enemy.y)
            enemy.x,enemy.y=target
    elif key=='lamp':
        if target:
            from .realm_lights import borrow_light
            if st.get('library_lamp'):
                from .realm_lights import release_light
                release_light(state,st['library_lamp']['pos'],enemy.id+':library')
            st['library_lamp']={'pos':target,'left':2}
            borrow_light(state,target,enemy.id+':library',3)
    elif key=='bind':
        if target and state.cell(*target).floor_fuel>0 and state.cell(*target).aggregate_variant=='干纸堆':
            cell=state.cell(*target)
            cell.floor_fuel=max(0,cell.floor_fuel-3)
            if not cell.floor_fuel:cell.aggregate_variant='普通聚合物'
            state._apply_direct_portent(enemy, 'sk_guard_fold', 2)
    elif key=='revision':
        ally=next((e for e in state.enemies if e.id==pending.get('meta',{}).get('ally') and e.integrity>0),None)
        if ally:
            state._apply_direct_portent(ally, 'sk_guard_fold', 2)
            st['revision_spent']=True
    elif key=='echo':
        live=sum(e.integrity>0 and e.main_id==enemy.id for e in state.enemies)
        for p in warned:
            if live>=2:break
            if not state._sk_open(*p) or state.entity_at(*p):continue
            echo=state.add_defined_enemy('library.reader',*p,integrity=1,drop_id=None,dissolution_reward=0)
            echo.main_id=enemy.id
            echo.active_skill_state.update(summon_no_reward=True,summon_life=8,summon_owner=enemy.id)
            echo.alert_state='追踪'
            live+=1
    elif key=='blank':
        state._sk_add_field(enemy,'library_blank',warned,rounds=2)

def tick(state,amount):
    for enemy in state.enemies:
        st=enemy.active_skill_state
        if enemy.catalog_id.startswith('library.'):
            pos=(enemy.x,enemy.y)
            old=st.get('library_current')
            if old and tuple(old)!=pos:st['library_previous']=old
            st['library_current']=pos
        second=st.get('library_second_beat')
        if second and enemy.integrity>0 and state.action_seq>second['action']:
            cells=[]
            second_cells={tuple(p) for p in second['cells']}
            for p in second.get('path',second['cells']):
                if not state._sk_open(*p):break
                if tuple(p) in second_cells:cells.append(tuple(p))
            if (state.player.x,state.player.y) in cells:
                state._enemy_skill_trauma(enemy,second['power'],'心智')
            from .cast_fx import emit_cast
            from ..data.cast_fx import skill_visual
            from ..data.anomaly_skills import effective_skill_def
            emit_cast(state, skill_visual(effective_skill_def('library.last_page', enemy.catalog_id)),
                      'skill:library.last_page:second', (enemy.x, enemy.y), cells,
                      path=cells, source_id=enemy.id)
            st.pop('library_second_beat',None)
            st['library_second_resolved_action']=state.action_seq
            st['recover_until']=max(st.get('recover_until',0),state.time+1)
        pulse=st.get('library_lamp')
        if pulse:
            pulse['left']-=amount
            if pulse['left']<=0:
                from .realm_lights import release_light
                release_light(state,pulse['pos'],enemy.id+':library')
                st.pop('library_lamp',None)
        door=st.get('library_door')
        if door:
            door['left']-=amount
            if door['left']<=0:
                from .generation import GenerationMixin
                if state.cell(*door['pos']).wall_kind=='门':GenerationMixin.clear_wall(state.cell(*door['pos']))
                st.pop('library_door',None)
    # Summons expire without death drops; no recursive skill binding.
    for enemy in state.enemies:
        if enemy.active_skill_state.get('summon_owner') and enemy.catalog_id=='library.reader':
            enemy.active_skill_state['summon_life']-=amount
            if enemy.active_skill_state['summon_life']<=0:
                enemy.integrity=0
                enemy.drop_spawned=True
