"""Portable reading gestures; their learning sources remain palace exclusive."""
from ..i18n import tr
from ..data.abilities import ABILITY_DEFINITIONS
from .constants import ActionKind, Material
from .entities import ActionResult


def _layer(state):
    return (state.run_uid,state.depth,state.realm_id,state.realm_depth)


def resolve(state,key,*,target=None,direction=None):
    if key == 'library.erase':
        return state._resolve_ability_effect(key)
    clamp_target = None
    if key == 'library.clamp':
        x, y = state.player.x, state.player.y
        enemies = [enemy for enemy in state.enemies
                   if enemy.integrity > 0 and enemy.relation == '失控意识'
                   and max(abs(enemy.x-x), abs(enemy.y-y)) <= 5
                   and state.is_visible(enemy.x, enemy.y)]
        if enemies:
            clamp_target = min(enemies, key=lambda enemy: (
                max(abs(enemy.x-x), abs(enemy.y-y)), enemy.id))
            if state._portent_protected(clamp_target, 'sk_rooted'):
                return ActionResult(False, tr('页边合拢时，它已经挣脱了。'))
    definition=ABILITY_DEFINITIONS[key]
    state._pay_ability_cost(state._scaled_ability_cost(definition['cost']))
    state.ability_cooldowns[key]=state._scaled_ability_cooldown(definition['cooldown'])
    state._action_time(1,ActionKind.USE)
    x,y=state.player.x,state.player.y
    dx,dy=state.facing
    capture=getattr(state,'_cast_fx_capture',None)
    message=tr('书页翻过去了，空白仍是空白。')
    if key=='library.fold':
        path=[]
        for i in range(1,int(state._scaled_ability_power(5))+1):
            p=x+dx*i,y+dy*i
            if not state.inside_board(*p):break
            c=state.cell(*p)
            if c.solid or c.floor is Material.SOLID_AGGREGATE:break
            if not state.is_visible(*p):break
            if state.entity_at(*p):break
            path.append(p)
        if path:
            state.player.x,state.player.y=path[-1]
            state.invalidate_sight_radius()
            message=tr('你沿折痕跨到了另一侧。')
        if capture is not None:capture.resolved_path=tuple([(x,y),*path])
    elif key=='library.bookmark':
        mark=state.library_bookmark
        if mark and tuple(mark.get('layer',()))!=_layer(state):
            mark=state.library_bookmark={}
        if not mark:
            state.library_bookmark={'layer':_layer(state),'position':(x,y)}
            message=tr('书签夹住了脚下这一页。')
        else:
            p=tuple(mark.get('position',()))
            if len(p)==2 and state.inside_board(*p) and not state.cell(*p).solid and not state.entity_at(*p):
                state.player.x,state.player.y=p
                state.library_bookmark={};state.invalidate_sight_radius()
                message=tr('你回到了夹着书签的地方。')
                if capture is not None:capture.resolved_path=((x,y),p)
            elif p==(x,y):
                state.library_bookmark={};message=tr('你收起了脚下的书签。')
            else:message=tr('书签那一页被压住了；它还留在那里。')
    elif key=='library.inkline':
        path=[];count=0
        for i in range(1,9):
            p=x+dx*i,y+dy*i
            if not state.inside_board(*p) or state.cell(*p).solid:break
            path.append(p)
            enemy=state.entity_at(*p)
            if enemy and enemy.relation=='失控意识' and enemy.integrity>0:
                # 正面命中（墨线掠过眼睛）：§14.1 映射为致盲征兆，不再只是减半。
                state._apply_direct_portent(
                    enemy, "blinded", state._scaled_ability_power(2));count+=1
        if capture is not None:capture.resolved_path=tuple(path)
        if count:message=tr('墨线掠过眼睛，目光暗下去了。')
    elif key=='library.erase':
        p=x+dx,y+dy
        if state.inside_board(*p):
            c=state.cell(*p)
            from ..materials.walls import wall_def,CONTAINER_KINDS
            from ..materials.common import RARE_WALLS
            fixtures={tuple(v['position']) for v in state.realm_features.get('scavenge_stock',{}).values()}
            anchored=any((e.x,e.y)==p for e in state.events)
            protected=(c.wall_kind in CONTAINER_KINDS or c.wall_kind in RARE_WALLS
                       and c.wall_kind not in ('胡桃木书架','推书车'))
            if (c.solid and c.hardness<=2 and wall_def(c.wall_kind).integrity<9999
                    and not protected and not anchored and p not in fixtures):
                state.clear_wall(c);state.invalidate_sight_radius()
                message=tr('那处薄障被划掉了，后面露出空地。')
    elif key=='library.clamp':
        # Lock the pre-payment instance. World advancement may kill/move it;
        # a released cast stays paid but must never jump to a different enemy.
        if clamp_target is not None:
            valid = (any(enemy is clamp_target for enemy in state.enemies)
                     and clamp_target.integrity > 0
                     and clamp_target.relation == '失控意识'
                     and max(abs(clamp_target.x-x), abs(clamp_target.y-y)) <= 5
                     and state.is_visible(clamp_target.x, clamp_target.y))
            if valid and state._apply_direct_portent(
                    clamp_target, 'sk_rooted', state._scaled_ability_power(2)):
                message=tr('页边合拢，夹住了它的脚步。')
            else:
                message=tr('页边合拢时，它已经挣脱了。')
    elif key=='library.margin':
        from .ability_targeting import margin_strip
        from .vision.knowledge import record_terrain_outline
        length=int(state._scaled_ability_power(12))+state.memory_stat_bonus('margin')
        cells=margin_strip(state,direction,length=length,width=3)
        learned=record_terrain_outline(state,cells)
        message=tr('旁注沿方向补出 {learned} 格地形轮廓（长 {length}、宽 3）；只标开放与阻挡。', learned=learned, length=length)
    state.messages.append(message)
    state._note_board_conceive(key)
    return ActionResult(True,message,{'ability':key})
