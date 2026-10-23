"""Exploration, persisted final-battle phases and legacy deep-save repair."""
from ..data.epilogue_upgrade import TEXT
from ..i18n import tr
from .entities import ActionResult


def say(key, **values):
    return tr(TEXT[key][0], **values)


class EpilogueMixin:
    def _spawn_epilogue_exploration(self, info, add_event):
        if self.depth != 30:
            return
        existing={e.event_id for e in self.events}
        x,y=info['events']['gallery']
        if 'epilogue.gallery' not in existing:
            add_event('epilogue.gallery',TEXT['gallery'][0],x,y,TEXT['gallery_desc'][0],kind='compound',
                      dialogue=(TEXT['gallery_reply'][0],),
                      options=({'label':TEXT['listen'][0],'epilogue':{'act':'gallery'}},))
        for i in range(3):
            if f'epilogue.fragment{i}' in existing:continue
            x,y=info['events'][f'fragment{i}']
            add_event(f'epilogue.fragment{i}',TEXT[f'page{i}'][0],x,y,TEXT[f'page_text{i}'][0],kind='compound',
                      dialogue=(TEXT[f'page_text{i}'][0],),
                      options=({'label':TEXT['claim'][0],'epilogue':{'act':'fragment'}},))

    def _epilogue_npc_option(self, npc, action):
        if action=='review':
            count=0
            for record in self.epilogue_flags.get('identified',{}).values():
                if not record['correct'] and not record.get('reviewed'):
                    record['reviewed']=True;count+=1
            self.epilogue_flags['clues']=self.epilogue_flags.get('clues',0)+count
            message=say('reviewed',count=count)
        elif action=='progress':
            message=say('progress_text',clues=self.epilogue_flags.get('clues',0),
                        rooms=len(self.epilogue_flags.get('identified',{})),accept=self.epilogue_flags.get('acceptance',0))
        else:
            message=say('rules28' if self.depth==28 else 'rules29')
            if self.depth==29:
                from .content import EPILOGUE_PROFILE_RULES
                rule=next((r for r in EPILOGUE_PROFILE_RULES if r['profile']==self.epilogue_profile),None)
                if rule:message+=' '+tr(rule['hint'])
        self.messages.append(message)
        return ActionResult(True,message,{'npc':npc.id})

    def _scribe_dead(self):
        return bool(self.epilogue_flags.get('scribe_defeated')) or any(
            e.catalog_id=='anomaly.scribe' and e.integrity<=0 for e in self.enemies)

    def _scribe_defeated(self, enemy):
        if self.depth!=30 or self.epilogue_flags.get('scribe_defeated'):return
        self.epilogue_flags['scribe_defeated']=True
        self.epilogue_flags.pop('scribe_warning',None)
        for e in self.enemies:
            if e.main_id==enemy.id:e.integrity=0;e.drop_spawned=True
        self.messages.append(say('defeated'))
        desk=next((e for e in self.events if e.event_id=='epilogue.desk'),None)
        if desk:desk.dialogue=(TEXT['desk_silent'][0],)
        if desk and not self.run_over:self.open_event_dialog(desk)

    def _scribe_turn(self, enemy, amount):
        dist=max(abs(enemy.x-self.player.x),abs(enemy.y-self.player.y))
        if self.depth!=30 or self.run_over or enemy.frozen_turns>0:return
        flags=self.epilogue_flags
        maximum=flags.setdefault('scribe_max',max(80,enemy.integrity))
        phase=1 if enemy.integrity>maximum*2/3 else 2 if enemy.integrity>maximum/3 else 3
        if dist>12 or not self._has_line_of_sight(enemy.x,enemy.y,self.player.x,self.player.y):
            flags.pop('scribe_warning',None)
            return
        if flags.get('scribe_phase')!=phase:
            flags['scribe_phase']=phase
            self.messages.append(say('phase',phase=phase,name=say(f'phase{phase}')))
        warning=flags.get('scribe_warning')
        if warning:
            warning['remaining']-=amount
            if warning['remaining']<=0:
                x,y=warning['pos'];radius=warning['radius']
                if max(abs(self.player.x-x),abs(self.player.y-y))<=radius:
                    self._skill_trauma(enemy,warning['power'])
                    self._check_run_over()
                flags.pop('scribe_warning',None)
            return
        clock=enemy.skill_clocks.get('scribe',0)+amount
        if clock<max(3,7-phase):enemy.skill_clocks['scribe']=clock;return
        enemy.skill_clocks['scribe']=0
        flags['scribe_warning']={'pos':[self.player.x,self.player.y],'remaining':2,'radius':1 if phase<3 else 2,'power':2+phase}
        self.messages.append(say('warning'))
        if phase>=2:
            living=[e for e in self.enemies if e.main_id==enemy.id and e.integrity>0]
            if len(living)<2:
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    x,y=enemy.x+dx,enemy.y+dy
                    if 0<x<self.width-1 and 0<y<self.height-1 and not self.cell(x,y).solid and not self.entity_at(x,y):
                        echo=self.add_enemy('残影',x,y,integrity=3,move_time=1.5,attack_time=2,
                                            trauma_type='清醒创伤',communicates=False,drop_id=None,dissolution_reward=0)
                        echo.trait='phantom';echo.main_id=enemy.id
                        break

    def _resume_epilogue(self):
        if self.depth not in (28,29,30) or self.map_form!='深层边界' or self.run_over:return
        # New saves keep cells and phase clocks verbatim. Only repair old incomplete layers.
        if self.depth in self.epilogue_flags.get('repaired_layers',[]):return
        from ..mapgen.epilogue import generate_epilogue_layer
        from ..mapgen.epilogue_paths import connect_anchors
        _,info=generate_epilogue_layer(self.depth,self.seed)
        if info['width']!=self.width or info['height']!=self.height:return
        connect_anchors(self.cells,info)
        flags=self.epilogue_flags
        if self.depth==28 and not flags.get('identified'):
            correct=flags.get('identify_correct',0)
            for event in self.events:
                if event.event_id.startswith('epilogue.room') and event.resolved:
                    flags.setdefault('identified',{})[event.event_id]={'correct':correct>0,'truth':'','reviewed':False}
                    correct=max(0,correct-1)
        if self.depth==29:
            flags['guided']=any(e.event_id=='epilogue.stele' and e.resolved for e in self.events) or bool(flags.get('acceptance'))
            flags.setdefault('peace_kills',self.run_stats.get('kills',0))
            for event in self.events:
                if event.event_id=='epilogue.stele':event.resolved=False
        if self.depth==30:
            if not any(e.catalog_id=='anomaly.scribe' for e in self.enemies) and not self._scribe_dead():
                x,y,cid=info['enemies'][0]
                if self.entity_at(x,y):
                    x,y=next((p for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if not self.cell(*p).solid and not self.entity_at(*p)),(x,y))
                self.add_defined_enemy(cid,x,y)
            def add(event_id,name,x,y,description,**kw):
                from .entities import WorldEvent
                self.events.append(WorldEvent(event_id,name,x,y,description,catalog_id=event_id,bound=True,**kw))
            self._spawn_epilogue_exploration(info,add)
            desk=next((e for e in self.events if e.event_id=='epilogue.desk'),None)
            if desk and not any(o.get('epilogue',{}).get('act')=='challenge' for o in desk.options):
                desk.options=tuple(desk.options)+({'label':TEXT['challenge'][0],'epilogue':{'act':'challenge'}},{'label':'告辞。','leave':True})
                desk.dialogue=(TEXT['desk_silent' if self._scribe_dead() else 'desk_reply'][0],)
        self.epilogue_flags['schema']=2
        self.epilogue_flags.setdefault('repaired_layers',[]).append(self.depth)
        self._reset_material_index()

    def epilogue_progress(self):
        flags=self.epilogue_flags
        return say('progress_text',clues=flags.get('clues',0),
                   rooms=len(flags.get('identified',{})),accept=flags.get('acceptance',0))
