"""Palace grammar words, bounded by root actions and their sentence positions."""
from ..i18n import tr
from ..data.items import ITEM_DEFINITIONS
from .runtime import condition_matches

WORDS={'bookmark':'跨门后','index':'记起','fold':'折返','paperweight':'独处','lens':'汇聚','quill':'拒绝','card':'变化后','testimony':'存疑'}
EVENTS={'bookmark':'move','index':'hit','fold':'move','paperweight':'recover','lens':'hit','quill':'hurt','card':'touch','testimony':'hit'}

def resolve_library_role(definition_id,role,operand_type=None):
    from .roles import RoleResponse, _profile
    d=ITEM_DEFINITIONS[definition_id];key=definition_id.removeprefix('library.')
    if key not in WORDS:return None
    common=dict(effect=d['effect'],power=1,profile=_profile(d))
    if role=='source':return RoleResponse(role,d['name'],'carrier',payload_type='carrier',**common)
    if role=='condition':return RoleResponse(role,WORDS[key],'condition',condition_kind='event',event=EVENTS[key],**common)
    if role=='verb':return RoleResponse(role,WORDS[key],'contract',opcode='maintain',payload_type='buff',**common)
    if role=='object':return RoleResponse(role,d['grammar_word'],'payload',payload_type='buff',**common)
    if role=='modifier' and key in ('lens','testimony'):
        return RoleResponse(role,WORDS[key],'modifier',opcode='library_'+key,payload_type='buff',**common)
    return None

def _active(state,key,event='',target=None,cell=None,formation=None):
    formation=formation or state.equipment.formation()
    for row in formation.rows:
        if row.status!='ready' or not condition_matches(row.condition,state,target=target,cell=cell,event=event):continue
        if any(v.definition_id=='library.'+key and v.response.role=='verb' for v in row.voices):return True
    return False

_FRONT_STEPS=((1,0),(-1,0),(0,1),(0,-1))

def _bearing(dx,dy):
    """八方位中文词，与 i18n 的「东北／东南／西南／西北」键保持同一写法。"""
    ns='南' if dy>0 else '北' if dy<0 else ''
    ew='东' if dx>0 else '西' if dx<0 else ''
    return ew+ns if ew and ns else (ns or ew)

def frontier_edges(state,limit=2):
    """已探索地形里「再往外一步就是没记过的地方」的边界格，按远近取前 ``limit`` 个。

    只读 ``terrain_memory``（玩家真正记下的那一层），不读棋盘本身：
    边界格一定是**走过／记过的可通行格**，未知那一侧一格都不碰——因此这段
    信息不会因为「旁边恰好是墙」而多报，也不揭示未知格上有什么。

    返回 ``[(边界格, 未知所在方向, 曼哈顿距离), ...]``，按 ``(距离, y, x)`` 排序。
    方向是「未知在那一边」，留给以后的地图叠层；播报里的方位用的是
    **玩家→边界格**（与距离同一基准），两套不混。
    """
    memory=state.terrain_memory.get(state.layer_key()) or {}
    if not memory:return []
    px,py=state.player.x,state.player.y
    found=[]
    for (x,y),snapshot in memory.items():
        if snapshot.solid:continue                     # 只从走得通的地方出发
        for dx,dy in _FRONT_STEPS:
            nx,ny=x+dx,y+dy
            if (nx,ny) in memory or not state.inside_board(nx,ny):continue
            found.append(((x,y),(dx,dy),abs(x-px)+abs(y-py)))
            break                                      # 一格只记一次，取第一个未知方向
    found.sort(key=lambda row:(row[2],row[0][1],row[0][0]))
    return found[:max(1,int(limit))]

def _claim(state,key,cooldown):
    clock='library:'+key
    seq=state.action_seq
    frame=getattr(state,'_equipment_root_frame',None)
    if seq<state.board_cooldowns.get(clock,-1) or (frame and clock in frame.repeat_claims):return False
    state.board_cooldowns[clock]=seq+cooldown
    if frame:frame.repeat_claims.add(clock)
    return True

def library_feedback(state,event,target=None,cell=None,formation=None):
    if getattr(state,'_equipment_derived_depth',0):return
    if event=='move' and _active(state,'bookmark',event,target,cell,formation):
        door=bool(cell and (getattr(state.cell(*cell),'doorway',False) or state.cell(*cell).wall_kind in ('门','木门','机关门')))
        if door and _claim(state,'bookmark',6):state.equipment_marks['library:bookmark']={'left':1,'until':state.action_seq+6}
    if event=='hit' and target:
        if _active(state,'index',event,target,cell,formation) and _claim(state,'index',1):
            # 2026-10-22（P3）：失时索引不再只报一次完整度——它替你把「最后见到它的
            # 样子」留六次行动：方位、完整度、以及这条记录还剩几次行动有效。
            # 目标离开视野就不再刷新（命中本来就要求看得见，所以「没刷新」= 它走了）。
            marks=state.equipment_marks.setdefault('library:index',{})
            key=str(target.id)
            prior=marks.get(key) or {}
            left=max(0,int(prior.get('until',0))-int(state.action_seq))
            if prior and left>0:
                state.messages.append(tr(
                    '失时索引还记着{name}：上次见到是在 {cell}，当时完整度 {integrity}（记录余 {turns} 次行动）。',
                    name=tr(target.label),cell=(prior.get('x'),prior.get('y')),
                    integrity=prior.get('integrity',0),turns=left))
            else:
                state.messages.append(tr(
                    '失时索引记下{name}：此刻在 {cell}，完整度 {integrity}；六次行动内它离开视野，这条记录也不再更新。',
                    name=tr(target.label),cell=(target.x,target.y),integrity=target.integrity))
            if state.is_visible(target.x,target.y):
                marks[key]={'x':target.x,'y':target.y,'integrity':int(target.integrity),
                            'until':int(state.action_seq)+6}
        if _active(state,'lens',event,target,cell,formation) and _claim(state,'lens',1):
            # 2026-10-22（P3）：透镜的口径是「导电／火源连接的预览」——
            # 把目标周围一格看得见的电线、火焰与燃油点定住三回合，
            # 看清楚这一发打过去会接通什么、会烧到什么；它不复制伤害。
            wired=[];burning=[]
            for tx in range(target.x-1,target.x+2):
                for ty in range(target.y-1,target.y+2):
                    if (tx,ty)==(target.x,target.y) or not state.inside_board(tx,ty):continue
                    if not state.is_visible(tx,ty):continue
                    probe=state.cell(tx,ty)
                    if getattr(probe,'wire',0):wired.append((tx,ty))
                    elif probe.flame>0 or probe.liquid_kind=='燃油':burning.append((tx,ty))
            if wired or burning:
                state.equipment_marks['library:lens']={
                    'target':str(target.id),'wired':wired,'burning':burning,
                    'until_time':int(state.time)+3}
                state.messages.append(tr(
                    '阿莱夫透镜定住{name}周围三回合：导电 {wires} 处、火源 {fires} 处（{cells}）。',
                    name=tr(target.label),wires=len(wired),fires=len(burning),
                    cells='、'.join(str(p) for p in (wired+burning)[:4])))
            else:
                state.messages.append(tr('阿莱夫透镜照过去：{name}周围一格没有可见的导电或火源连接。',
                                         name=tr(target.label)))
        if _active(state,'testimony',event,target,cell,formation) and _claim(state,'testimony',1):
            # 2026-10-22（P3）：残页不再随口报一个邻格——它记下这个目标，
            # 下一次普通攻击打到它时**先报出推离落点与碰撞**（见 `testimony_preview`）。
            state.equipment_marks['library:testimony']={
                'target':str(target.id),'name':target.label,
                'until':int(state.action_seq)+6}
            state.messages.append(tr(
                '罗生门残页留了另一种写法：下次打{name}时，会先报出它被推开几格、撞在哪里。',
                name=tr(target.label)))
    if event=='move' and _active(state,'fold',event,target,cell,formation) and _claim(state,'fold',6):
        # 2026-10-22（P3）：折页不再只报脚下四个方向能不能走——那和免费的
        # 观察重叠。它折出**已探索区域通向未知的最近两处边界**：告诉你哪两条
        # 边走一步就是没记过的地方，并且只说边界，不记那边有什么。
        edges=frontier_edges(state,2)
        if not edges:
            state.messages.append(tr('隐城折页翻过一遍：这一层通向未知的边界都已经记下了。'))
        else:
            state.equipment_marks['library:fold']={
                'cells':[edge[0] for edge in edges],'until':int(state.action_seq)+6}
            parts=[tr('{dir} {distance} 格（{cell}）',
                      dir=tr(_bearing(cell[0]-state.player.x,cell[1]-state.player.y)),
                      distance=distance,cell=cell) for cell,_step,distance in edges]
            state.messages.append(tr('隐城折页折出最近的未知边界：{edges}；只标边界，不记那边有什么。',
                                     edges='、'.join(parts)))
    if event=='touch' and _active(state,'card',event,target,cell,formation) and _claim(state,'card',6):
        # 2026-10-22（P3）：签名只看**环境本身**——液体、气体、聚合地面变体，
        # 以及别的征兆（那些都是接触环境留下的痕迹）。必须排除借阅证自己
        # 施下的 `library_observation`：否则第一次记录之后就变了签名，
        # 第二次接触同一个地方会被当成「环境变了」，同类不刷新形同虚设。
        signature=(tuple(sorted(p for p in state.player.portents if p!='library_observation')),
                   state.cell(*(cell or (state.player.x,state.player.y))).aggregate_variant,state.cell(*(cell or (state.player.x,state.player.y))).liquid_kind,state.cell(*(cell or (state.player.x,state.player.y))).gas_kind)
        prior=state.equipment_marks.get('library:card_observation',{}).get('signature')
        if prior==signature:return
        state.equipment_marks['library:card_observation']={'signature':signature}
        state._apply_direct_portent(state.player, 'library_observation', 4)
        state._visible_cache=None
        state.messages.append(tr('蝶梦借阅证记下这次环境变化：四回合内视野增加两格。'))

def testimony_preview(state,target,dx,dy,power):
    """罗生门残页（P3）：下一次普通攻击命中同一目标时，先报出推离落点与碰撞。

    只在「命中事件已经记下这个目标、且没超过六次行动」时预演一次，然后作废——
    它是**预览**：不改变推离本身，也不额外造成伤害或位移。
    """
    mark=state.equipment_marks.get('library:testimony')
    if not mark or str(mark.get('target'))!=str(target.id):return
    state.equipment_marks.pop('library:testimony',None)
    if int(state.action_seq)>int(mark.get('until',-1)):return
    x,y=target.x,target.y
    moved=0;stop=''
    for _step in range(max(0,int(power))):
        nx,ny=x+dx,y+dy
        if not state.inside_board(nx,ny):stop=tr('推出边缘');break
        probe=state.cell(nx,ny)
        if probe.solid:stop=tr('撞上{thing}',thing=tr(probe.wall_kind) or tr('墙'));break
        if state.entity_at(nx,ny):stop=tr('撞上另一个意识');break
        x,y=nx,ny;moved+=1
    if stop:
        state.messages.append(tr('残页先演了一遍：这一击把它推开 {moved} 格，{stop}，停在 {cell}。',
                                 moved=moved,stop=stop,cell=(x,y)))
    else:
        state.messages.append(tr('残页先演了一遍：这一击把它推开 {moved} 格，停在 {cell}，一路没撞到东西。',
                                 moved=moved,cell=(x,y)))


def library_damage_bonus(state,base,target=None):
    mark=state.equipment_marks.get('library:bookmark')
    if not mark or mark.get('until',-1)<state.action_seq or mark.get('left',0)<=0:return 0
    mark['left']=0
    credit=state.equipment_damage_credit.get('library:bookmark',0)+max(0,base)*12
    bonus,credit=divmod(credit,100)
    state.equipment_damage_credit['library:bookmark']=credit
    return bonus

def library_recovery_bonus(state,resource,actual,natural=False):
    if not natural or actual<=0 or not _active(state,'paperweight','recover'):return 0
    if any(e.integrity>0 and e.relation=='失控意识' and max(abs(e.x-state.player.x),abs(e.y-state.player.y))<=3 for e in state.enemies):return 0
    return 1 if _claim(state,'paperweight',8) else 0

def library_reject_control(state,portent_id):
    weak={'sk_late_beat','sk_seam_shadow','sk_drowsy','sk_blur','sk_field_hamper'}
    ward=state.equipment_marks.get('library:quill_ward',{})
    if ward.get('portent')==portent_id and ward.get('until',-1)>=state.action_seq:return True
    if portent_id not in weak or not _active(state,'quill','hurt') or not _claim(state,'quill',10):return False
    state.equipment_marks['library:quill_ward']={'until':state.action_seq+2,'portent':portent_id}
    state.messages.append(tr('拒誊羽笔拒绝了一次弱控制；这两行动内耐受同类控制。'))
    return True
