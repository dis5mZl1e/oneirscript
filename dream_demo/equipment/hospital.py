"""Position-bound medical feedback and finite, portable hospital tools."""
from .root_facts import root_action
from .runtime import condition_matches
from ..data.items import ITEM_DEFINITIONS
from ..core.entities import ActionResult
from ..core.constants import ActionKind
from ..i18n import tr
from ..core.cast_fx import animate_hospital_tool

def medical_result(changed, message, data=None):
    return ActionResult(changed, tr(message), data or {})

EVENTS = {'suture_shears':'hit','hollow_lancet':'hit','suture_coil':'hurt',
          'lymph_filter':'settled','cerebral_ampoule':'conceive','sterile_glove':'hurt',
          'glass_rib':'hurt','pulse_tag':'hurt','marrow_spoon':'ingest','lumen_mask':'settled'}
COOLDOWNS = {'suture_shears':7,'hollow_lancet':6,'suture_coil':8,'lymph_filter':7,
             'cerebral_ampoule':7,'sterile_glove':7,'glass_rib':8,'pulse_tag':7,'marrow_spoon':8,'lumen_mask':7}
MEANINGS = dict(zip(EVENTS, ('剪除','注入','缝合','滤过','流畅','清洗','支撑','呼应','摄入后','照见')))

def resolve_hospital_role(definition_id, role, operand_type=None):
    from .roles import RoleResponse, _profile
    d = ITEM_DEFINITIONS[definition_id]
    key = definition_id.removeprefix('hospital.')
    if key not in EVENTS:
        return None
    common = dict(effect=d['effect'],power=1,profile=_profile(d))
    if role == 'condition':
        if key in ('cerebral_ampoule','pulse_tag','marrow_spoon'):
            return RoleResponse(role,{'cerebral_ampoule':'施法后','pulse_tag':'受击后','marrow_spoon':'摄入后'}[key],'condition',condition_kind='event',event=EVENTS[key],**common)
        if key in ('glass_rib','lumen_mask'):
            return RoleResponse(role,'已照亮' if key=='lumen_mask' else '在光中','condition',condition_kind='lit',**common)
        return None
    if role == 'source':
        return RoleResponse(role,d['name'],'carrier',payload_type='carrier',action_modes=('melee','fire') if key=='hollow_lancet' else ('melee',) if key=='suture_shears' else (),**common)
    if role == 'verb':
        if key in ('suture_shears','hollow_lancet'):
            mode = 'fire' if key=='hollow_lancet' else 'melee'
            return RoleResponse(role,MEANINGS[key],'action',opcode='fire' if mode=='fire' else 'strike',action_modes=(mode,),**common)
        return RoleResponse(role,MEANINGS[key],'contract',opcode='maintain',payload_type='buff',**common)
    if role == 'object':
        return RoleResponse(role,d['name'],'payload',payload_type='buff',**common)
    if role == 'modifier' and key=='suture_coil':
        return RoleResponse(role,'相接','modifier',opcode='hospital_adjacent',payload_type='buff',**common)
    if role == 'modifier' and key=='lymph_filter':
        return RoleResponse(role,'病原体','modifier',opcode='hospital_pathogen',payload_type='buff',**common)
    return None

def active_medical_rows(state, event, target=None, cell=None, formation=None):
    formation = formation or state.equipment.formation()
    seen=set()
    for row in formation.rows:
        if row.status != 'ready' or not condition_matches(row.condition,state,target=target,cell=cell,event=event):
            continue
        for v in row.voices:
            key=v.definition_id.removeprefix('hospital.')
            if key in seen or EVENTS.get(key)!=event or v.instance_id!=row.source_id or v.response.role not in ('source','verb'):
                continue
            if any(w.response.opcode=='hospital_pathogen' for w in row.voices):
                tags=getattr(target,'biological_tags',()) or ITEM_DEFINITIONS.get(getattr(target,'definition_id',''),{}).get('tags',())
                if 'pathogen' not in tags: continue
            if any(w.response.opcode=='hospital_adjacent' for w in row.voices):
                if target is None or abs(target.x-state.player.x)+abs(target.y-state.player.y)!=1:continue
            seen.add(key)
            yield key,v.instance_id

class HospitalEquipmentMixin:
    def open_hospital_lancet_selection(self,index):
        from ..core.entities import WorldEvent
        if not 0<=index<len(self.inventory):return medical_result(False,'没有空心针。')
        needle=self.inventory[index]
        if needle.definition_id!='hospital.hollow_lancet':return medical_result(False,'不是空心针。')
        options=[]
        for source in self.inventory:
            spec=ITEM_DEFINITIONS.get(source.definition_id,{}).get('container',{})
            if source is needle or spec.get('medium')!='liquid' or not source.contents:continue
            kind=next(iter(source.contents))
            if needle.contents and kind not in needle.contents:continue
            if sum(needle.contents.values())>=6:continue
            options.append({'label':tr('{item}：{material} ×{n}',item=tr(source.name),material=tr(kind),n=source.contents[kind]),'hospital_load':{'needle':needle.instance_id,'container':source.instance_id}})
        if not options:return medical_result(False,'没有可装载的真实液体样本，或针已满。')
        event=WorldEvent('hospital.lancet_choice',tr('装载空心针'),self.player.x,self.player.y,tr('选择真实液体容器；取消不消耗。'),kind='compound',dialogue=(tr('最多装载6单位一种液体，注入真实消耗。'),),options=tuple(options),dissolution_reward=0)
        self.events=[e for e in self.events if e.event_id!='hospital.lancet_choice']
        self.events.append(event);self.pending_event_id=event.event_id
        return medical_result(True,'选择装载样本。',{'open_event_dialog':True})

    def confirm_hospital_lancet_selection(self,choice):
        if not isinstance(choice,dict):return medical_result(False,'选择已失效。')
        indices={item.instance_id:i for i,item in enumerate(self.inventory)}
        needle=indices.get(choice.get('needle'));source=indices.get(choice.get('container'))
        if needle is None or source is None:return medical_result(False,'所选容器已离开行囊。')
        result=self.load_hospital_lancet(needle,source)
        if result.changed:self.close_event_dialog()
        return result

    @root_action
    def load_hospital_lancet(self,index,source_index):
        if not (0<=index<len(self.inventory) and 0<=source_index<len(self.inventory)):
            return medical_result(False,'容器已失效。')
        needle,source=self.inventory[index],self.inventory[source_index]
        if needle.definition_id!='hospital.hollow_lancet' or needle is source:
            return medical_result(False,'请选择空心针和真实液体容器。')
        if ITEM_DEFINITIONS.get(source.definition_id,{}).get('container',{}).get('medium')!='liquid' or not source.contents:
            return medical_result(False,'容器没有液体样本。')
        kind=next(iter(source.contents))
        if needle.contents and kind not in needle.contents:return medical_result(False,'针内已有异种样本，请先注出。')
        amount=min(6-sum(needle.contents.values()),source.contents[kind])
        if amount<=0:return medical_result(False,'空心针已满。')
        needle.contents[kind]=needle.contents.get(kind,0)+amount
        source.contents[kind]-=amount
        if source.contents[kind]<=0:source.contents.pop(kind)
        self._action_time(self._dream_action_time(1,'materials'),ActionKind.USE)
        return medical_result(True,'样本已装载。',{'sample':kind,'amount':amount})

    def resolve_hospital_ampoule(self,item,x,y):
        """Break only the finite shell and release its actual sample at landing."""
        quantities={}
        cell=self.cell(x,y)
        for kind,n in list(item.contents.items()):
            transferred=min(max(0,int(n)),max(0,100-cell.liquid))
            if transferred<=0:continue
            self._add_liquid(cell,kind,transferred)
            quantities[kind]=transferred
            item.contents[kind]-=transferred
            if item.contents[kind]<=0:item.contents.pop(kind)
        if item.contents:
            from ..core.entities import WorldItem
            self.world_items.append(WorldItem(item,x,y))
        self._sync_material_position(x,y)
        target=self.entity_at(x,y)
        shell_damage=0
        if target is not None and target is not self.player and target.integrity>0:
            shell_damage=min(1,target.integrity)
            target.integrity-=shell_damage
            if target.integrity<=0:self._resolve_enemy(target)
        return tr('封口安瓿碎开，释放了瓶中的液体。'),{'released':quantities,'retained':dict(item.contents),'shell_damage':shell_damage,'position':(x,y)}

    def _medical_claim(self,key):
        family='hospital_equipment_'+key
        frame=getattr(self,'_equipment_root_frame',None)
        if self.time < self.board_cooldowns.get(family,0):return False
        if frame and family in frame.repeat_claims:return False
        self.board_cooldowns[family]=self.time+COOLDOWNS[key]
        if frame:frame.repeat_claims.add(family)
        return True

    def hospital_equipment_feedback(self,event,target=None,cell=None,formation=None,*,action_plan=None):
        if getattr(self,'_equipment_derived_depth',0):return
        for key,iid in active_medical_rows(self,event,target,cell,formation):
            if key in ('suture_shears','hollow_lancet') and action_plan is not None and iid not in action_plan.source_ids:continue
            holder=target if key=='suture_shears' else self.player
            if key in ('suture_shears','sterile_glove','lymph_filter'):
                if holder is None or holder.hospital_state.get('cleanse_left',0)>0:continue
                if key=='lymph_filter':
                    from ..materials import portent_def
                    candidates={pid for pid,n in holder.portent_attach.items() if n>0 and portent_def(pid) and portent_def(pid).washable}
                    if not self.cleanse_target(holder,candidates):continue
                elif not self.cleanse_target(holder):continue
            if key=='hollow_lancet':
                sample=next((i for i in self.inventory if i.instance_id==iid),None)
                if sample is None or not sample.contents or cell is None or target is None or self.cell(*cell).liquid>=100:continue
            if key in ('glass_rib','lumen_mask'):
                from ..core.vision.glow import lit
                if not lit(self,self.player.x,self.player.y):continue
            if key in ('suture_coil','glass_rib') and (self.time < self.player.hospital_state.get('gel_ready',0) or self.player.portents.get('hospital_gel_buffer',0)):continue
            if not self._medical_claim(key):continue
            if key in ('suture_shears','sterile_glove','lymph_filter'):
                holder=target if key=='suture_shears' else self.player
                if holder is None:continue
                allowed=None
                if key=='lymph_filter':
                    from ..materials import portent_def
                    allowed={pid for pid,n in holder.portent_attach.items() if n>0 and portent_def(pid) and portent_def(pid).washable}
                if self.shorten_portent(holder,2,allowed):holder.hospital_state['cleanse_left']=4
            elif key=='hollow_lancet' and cell and target is not None:
                item=next((i for i in self.inventory if i.instance_id==iid),None)
                # Equipped instances remain in the owned item collection.
                if item is None:
                    item=next((i for i in getattr(self,'equipped_items',()) if getattr(i,'instance_id',None)==iid),None)
                if item and item.contents:
                    kind=next(iter(item.contents));amount=min(1,item.contents[kind],max(0,100-self.cell(*cell).liquid))
                    self._add_liquid(self.cell(*cell),kind,amount)
                    item.contents[kind]-=amount
                    if not item.contents[kind]:item.contents.pop(kind)
                    self._sync_material_position(*cell)
            elif key in ('suture_coil','glass_rib'):
                from ..core.vision.glow import lit
                if key=='glass_rib' and not lit(self,self.player.x,self.player.y):continue
                if self.time >= self.player.hospital_state.get('gel_ready',0) and not self.player.portents.get('hospital_gel_buffer',0):
                    self._apply_direct_portent(self.player, 'hospital_gel_buffer', 6)
                    self.player.hospital_state['gel_ready']=self.time+8
            elif key=='cerebral_ampoule':self._apply_direct_portent(self.player, 'hospital_fluent', 6)
            # §13.4 道具侧声径（2026-10-22 收口）：心搏标签是「普通道具」声源，
            # 走 category="item" 才能吃到单边耳机／雨声遮蔽等普通降噪，不吃诱引／爆炸规则。
            elif key=='pulse_tag':self._sound_pulse(self.player.x,self.player.y,3,by_player=True,category="item")
            elif key=='lumen_mask':
                from ..core.vision.glow import lit
                if lit(self,self.player.x,self.player.y):self._hospital_diagnose(2,3)

    def consume_hospital_equipment_buffer(self,amount):
        # Shared gel settlement is handled by HospitalEffectMixin exactly once.
        return amount

    def hospital_equipment_recovery(self,resource,actual,*,ingested=False):
        if not ingested or actual<=0 or getattr(self,'_equipment_derived_depth',0):return 0
        for key,iid in active_medical_rows(self,'ingest',cell=(self.player.x,self.player.y)):
            if key!='marrow_spoon' or not self._medical_claim(key):continue
            self._equipment_derived_depth=getattr(self,'_equipment_derived_depth',0)+1
            try:return self.restore_resource(resource,2)
            finally:self._equipment_derived_depth-=1
        return 0

    def _hospital_diagnose(self,radius,duration):
        found=[]
        for enemy in self.enemies:
            if enemy.integrity>0 and max(abs(enemy.x-self.player.x),abs(enemy.y-self.player.y))<=radius and self.can_see(self.player,enemy.x,enemy.y):
                if self._apply_direct_portent(enemy, 'hospital_diagnosed', duration):
                    found.append(enemy.id)
        return found

    @root_action
    def use_hospital_tool(self,index,tx=None,ty=None):
        if not 0<=index<len(self.inventory):return medical_result(False,'没有这个工具。')
        item=self.inventory[index]
        if item.definition_id not in ('hospital.filter_sac','hospital.diagnostic_slide'):return medical_result(False,'不是医院观察或吸附工具。')
        tx=self.player.x if tx is None else tx;ty=self.player.y if ty is None else ty
        from ..core.throwing import is_valid_target
        valid,reason=is_valid_target(self,tx,ty)
        if not valid:return medical_result(False,reason)
        return self._deploy_hospital_tool(index,tx,ty)

    @animate_hospital_tool
    def _deploy_hospital_tool(self,index,tx,ty):
        """Apply a tool after the caller has validated and resolved its flight."""
        item=self.inventory[index]
        data={}
        if item.definition_id=='hospital.filter_sac':
            nodes=self.realm_features.setdefault('hospital_filters',[])
            nodes.append(dict(x=tx,y=ty,left=4,capacity=4,realm=[self.depth,self.realm_id,self.realm_depth]))
            data['filter_cell']=(tx,ty)
        else:data['diagnosed']=self._hospital_diagnose(2,3)
        item.quantity-=1
        if item.quantity<=0:self.inventory.remove(item)
        self._action_time(self._dream_action_time(1,'materials'),ActionKind.USE)
        return medical_result(True,'工具已使用。',data)

    def tick_hospital_tools(self):
        nodes=self.realm_features.get('hospital_filters',[])
        for node in list(nodes):
            if node['realm']!=[self.depth,self.realm_id,self.realm_depth]:continue
            x,y=node['x'],node['y']
            for px,py in ((x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if not self.inside_board(px,py):continue
                c=self.cell(px,py)
                if c.gas>0 and node['capacity']>0:
                    c.gas-=1;node['capacity']-=1
                    if not c.gas:c.gas_kind=''
                    self._sync_material_position(px,py)
                    break
            node['left']-=1
            if node['left']<=0 or node['capacity']<=0:nodes.remove(node)
