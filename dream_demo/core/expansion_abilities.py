"""扩展包目录构想的结算门面（2026-10-25）。

目录行的 ``effect.runtime[0]`` 用 ``kind`` 指名一个**已经存在的原语**，这里只做
参数装配、落点校验与文案，不再往 ``combat._resolve_ability_effect`` 的手写
``if`` 链上堆第 64 个分支：只有真正需要新机制的构想才进那个函数，其余走这份表。
付款口径与书库构想一致——先过只读落点校验，不合法就零消耗。

已实装的 ``kind``：

- ``noise_pulse``         在可见空格发一声，走真实声路（投声）
- ``wall_knock``          把相邻墙格变成持续几回合的敲击点（拍壁）
- ``replay_last_lure``    让自己上一处实际诱引落点再响一次（返场）
- ``lit_area_snapshot``   记录当前真实光照区的地形轮廓（留影）
- ``narrow_lamp``         把相邻亮灯的照明收成朝自己一侧的扇区（裁光）
- ``move_own_light``      把自己布下的临时光源搬到可见格，期限不续（移灯）
- ``borrow_light``        从相邻亮灯借三回合光，原灯同时变暗，到期一起还（借昼）
- ``stagger_lights``      可见范围内至多三盏可操控灯，每回合熄一盏（逐格熄灯）
- ``furrow``              沿瞄准方向三格各降一档，土按格数抬到两侧（犁沟）
- ``raise_rim``           从朝自己那侧的邻格取一档土，把落点抬成低沿（抬沿）
- ``end_own_construct_field`` 收掉落在指定格上的自己的构想场（收稿）

每条都必须由既有结算函数完成；认不出的 kind 返回 ``None``（交回通用结算＝空放
照付），而不是在这里另造一套效果。
"""
from __future__ import annotations

from typing import Any, Callable

from ..i18n import tr
from ..data.abilities import ABILITY_DEFINITIONS
from . import ability_targeting
from .constants import ActionKind
from .entities import ActionResult

_NO_POINT = "这个构想没有合法落点——本次不消耗。"


def effect_for(ability_id: str) -> dict[str, Any]:
    return dict((ABILITY_DEFINITIONS.get(ability_id) or {}).get("expansion_effect") or {})


def _pay(state, ability_id: str, definition: dict[str, Any]) -> None:
    cost = state._ability_imagination_cost(ability_id, definition)
    state._pay_ability_cost(cost)
    state.ability_cooldowns[ability_id] = state._scaled_ability_cooldown(
        int(definition["cooldown"]))
    state._action_time(1, ActionKind.USE)


def _done(state, ability_id: str, message: str) -> ActionResult:
    state.messages.append(message)
    state._note_board_conceive(ability_id)
    return ActionResult(True, message, {"ability": ability_id})


def _refuse(message: str) -> ActionResult:
    """付款前拒绝：描述里写明的前提不成立时零消耗。"""
    return ActionResult(False, tr(message))


def _aim_point(state, ability_id: str, target):
    spec = ability_targeting.spec_for(ability_id)
    if spec is None or spec.form != "point":
        return None
    return ability_targeting.resolve_target(state, ability_id, target)


def _noise_pulse(state, ability_id, definition, effect, target) -> ActionResult:
    """投声：在可见的空格上放一声，走完整声路（衰减、听觉上限、梯度）。"""
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    radius = int(effect.get("radius", 8) or 8)
    _pay(state, ability_id, definition)
    state._sound_pulse(x, y, radius, by_player=True,
                       category=str(effect.get("category") or "lure"),
                       triggers_rewards=False)
    return _done(state, ability_id, tr("你把声音投到 ({x}, {y})：那边响了一声。", x=x, y=y))


def _wall_knock(state, ability_id, definition, effect, target) -> ActionResult:
    """拍壁：把相邻墙格登记成延时声源，每回合一响；墙不在了就停。"""
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    if not state.cell(x, y).solid:
        return _refuse("相邻没有可以敲的墙。")
    turns = max(1, int(effect.get("turns", 3) or 3))
    radius = int(effect.get("radius", 6) or 6)
    _pay(state, ability_id, definition)
    now = int(getattr(state, "time", 0) or 0)
    source = str(definition.get("name") or "")
    layer = int(getattr(state, "depth", 0) or 0)
    for step in range(1, turns + 1):
        state.delayed_sounds.append({"x": x, "y": y, "due": now + step, "radius": radius,
                                     "source": source, "wall": True, "depth": layer})
    return _done(state, ability_id,
                 tr("你在 ({x}, {y}) 的墙上敲出节拍：接下来 {n} 回合每回合一响，墙碎即止。",
                    x=x, y=y, n=turns))


def _replay_last_lure(state, ability_id, definition, effect, target) -> ActionResult:
    """返场：重放自己上一处**实际**诱引落点；跨层或过期直接拒绝。"""
    lure = dict(getattr(state, "last_lure", {}) or {})
    within = int(effect.get("within_turns", 12) or 12)
    if (not lure or int(lure.get("depth", -1)) != int(getattr(state, "depth", 0))
            or int(getattr(state, "time", 0) or 0) - int(lure.get("turn", 0) or 0) > within):
        return _refuse("上一次诱引已经过期，或不在本层。")
    x = int(lure.get("x", 0) or 0)
    y = int(lure.get("y", 0) or 0)
    radius = int(lure.get("radius", 8) or 8)
    _pay(state, ability_id, definition)
    # chain=True：这一声是重放，不再喂齿轮吸／改向与记忆缓冲，也不改写 last_lure。
    state._sound_pulse(x, y, radius, by_player=True,
                       full_alert=bool(lure.get("full_alert")), category="lure",
                       source=str(definition.get("name") or ""), chain=True)
    return _done(state, ability_id, tr("返场把 ({x}, {y}) 的那声诱引又放了一遍。", x=x, y=y))


def _lit_area_snapshot(state, ability_id, definition, effect, target) -> ActionResult:
    """留影：把当前被真实照亮、且此刻看得见的格的地形轮廓记进记忆。"""
    from .vision import glow
    from .vision.knowledge import record_terrain_cells
    reach = max(1, int(effect.get("radius", 10) or 10))
    px, py = state.player.x, state.player.y
    cells = [(x, y)
             for y in range(max(0, py - reach), min(state.height, py + reach + 1))
             for x in range(max(0, px - reach), min(state.width, px + reach + 1))
             if glow.lit(state, x, y) and state.is_visible(x, y)]
    if not cells:
        return _refuse("身边没有被真实照亮的格。")
    _pay(state, ability_id, definition)
    learned = record_terrain_cells(state, cells)
    return _done(state, ability_id,
                 tr("留影把当前光照区的 {n} 格地形轮廓记进了记忆。", n=learned))


def _end_own_construct_field(state, ability_id, definition, effect, target) -> ActionResult:
    """收稿：结束落在指定格上的自己的构想场；已投下的材料不返。"""
    from . import construct_environments
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    matches = [field for field in construct_environments.active(state)
               if any((int(cx), int(cy)) == (x, y)
                      for cx, cy in (field.get("cells") or ()))]
    if not matches:
        return _refuse("那一格上没有你自己的构想场。")
    _pay(state, ability_id, definition)
    names = []
    for field in matches:
        # remaining 归零 + 摘出队列：tick 再也看不到它，延迟弹不再落地、刃环不再割。
        field["remaining"] = 0
        names.append(str(construct_environments.residue_name(field["kind"]) or field["kind"]))
        if field in state.construct_environments:
            state.construct_environments.remove(field)
    return _done(state, ability_id,
                 tr("你收回了 {name}：场不再继续生效，已投下的材料不返。",
                    name="、".join(tr(name) for name in names)))


RESOLVERS: dict[str, Callable] = {
    "noise_pulse": _noise_pulse,
    "wall_knock": _wall_knock,
    "replay_last_lure": _replay_last_lure,
    "lit_area_snapshot": _lit_area_snapshot,
    "end_own_construct_field": _end_own_construct_field,
}


def resolve(state, ability_id: str, *, target=None, direction=None) -> ActionResult | None:
    """按目录登记的 kind 结算扩展包构想；行不认识时返回 None。"""
    definition = ABILITY_DEFINITIONS.get(ability_id) or {}
    kind = str(definition.get("expansion_effect_kind") or "")
    if not kind:
        return None
    handler = RESOLVERS.get(kind)
    if handler is None:
        return None
    return handler(state, ability_id, definition, effect_for(ability_id), target)


# Only fields with no automatic damage or material conversion qualify. The
# whitelist deliberately excludes spark, erase, blades and transpiration.
NON_DAMAGE_FIELDS = frozenset({'mirror_stance', 'backdraft_screen', 'slow_zone', 'moth_zone'})


def pause_field(state, field):
    if (field.get('kind') not in NON_DAMAGE_FIELDS or field.get('paused_once')
            or field.get('remaining', 0) <= 0):
        return False
    field['pause_ticks'] = 1
    field['paused_once'] = True
    return True


def extend_field(state, field):
    if (field.get('kind') not in NON_DAMAGE_FIELDS or field.get('extended_once')
            or field.get('remaining', 0) <= 0):
        return False
    field['remaining'] += 1
    field['extended_once'] = True
    return True


def _residue_edit(state, ability_id, definition, effect, target):
    from . import construct_environments as fields
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    candidates = [f for f in fields.active(state) if list(point) in f.get('cells', ())
                  and f.get('kind') in NON_DAMAGE_FIELDS]
    operation = effect['kind']
    flag = 'paused_once' if operation == 'pause_residue' else 'extended_once'
    field = next((f for f in candidates if not f.get(flag)), None)
    if field is None:
        return _refuse(_NO_POINT)
    (pause_field if operation == 'pause_residue' else extend_field)(state, field)
    _pay(state, ability_id, definition)
    return _done(state, ability_id, str(definition['name']))


def sound_sequence_points(state, point):
    x, y = point
    choices = [point, (x+1,y), (x,y+1), (x-1,y), (x,y-1)]
    return [p for p in choices if state.inside_board(*p) and state.is_visible(*p)
            and not state.cell(*p).solid][:3]


def queue_sound_sequence(state, points, source):
    for step, (x, y) in enumerate(points, 1):
        state.delayed_sounds.append(dict(x=x, y=y, due=state.time+step, radius=8,
            source=source, depth=state.depth, category='lure'))


def _sequence(state, ability_id, definition, effect, target):
    point = _aim_point(state, ability_id, target)
    points = sound_sequence_points(state, point) if point is not None else []
    if len(points) != 3:
        return _refuse(_NO_POINT)
    _pay(state, ability_id, definition)
    queue_sound_sequence(state, points, str(definition['name']))
    return _done(state, ability_id, str(definition['name']))


def _delay_own_sound(state, ability_id, definition, effect, target):
    from . import construct_environments as fields
    if any(f['kind'] == 'expansion.delay_sound' for f in fields.active(state)):
        return _refuse(_NO_POINT)
    _pay(state, ability_id, definition)
    preparation=fields.start_field(state, 'expansion.delay_sound', (state.player.x,state.player.y),
                       (0,0), remaining=1)
    preparation['persistent']=True
    return _done(state, ability_id, str(definition['name']))


def intercept_delayed_sound(state, x, y, radius, **parameters):
    from . import construct_environments as fields
    if not parameters.get('by_player') or parameters.get('category') == 'explosion':
        return False
    # Only active sound, never incidental footsteps or an environmental crack.
    if parameters.get('category') not in {'lure', 'ability', 'item'}:
        return False
    field = next((f for f in fields.active(state) if f['kind'] == 'expansion.delay_sound'),None)
    if field is None:
        return False
    field['remaining'] = 0
    state.delayed_sounds.append(dict(x=x, y=y, radius=radius, due=state.time+2,
         depth=state.depth, pulse_parameters=parameters, source=parameters.get('source','')))
    return True


RESOLVERS.update({'pause_residue': _residue_edit, 'extend_residue': _residue_edit,
                  'sound_sequence': _sequence, 'delay_own_sound': _delay_own_sound})



def _place_mirrors(state, ability_id, definition, effect, target):
    from . import construct_environments as fields
    point = _aim_point(state, ability_id, target)
    if point is None or state.cell(*point).solid or state.entity_at(*point):
        return _refuse(_NO_POINT)
    dx,dy = state.facing
    normal = (dx,dy) if dx or dy else (1,0)
    cells = [point]
    if effect['kind'] == 'double_mirror':
        second = (point[0]-normal[1],point[1]+normal[0])
        if (not state.inside_board(*second) or not state.is_visible(*second)
                or state.cell(*second).solid or state.entity_at(*second)):
            return _refuse(_NO_POINT)
        cells.append(second)
    _pay(state, ability_id, definition)
    fields.start_field(state, 'expansion.'+effect['kind'], point,normal,
                       cells=cells,remaining=1 if effect['kind']=='double_mirror' else 2)
    return _done(state,ability_id,str(definition['name']))


def _paper_plan(state,field,target):
    if field.get('kind') != 'paper_blades' or field.get('remaining',0)<=0:
        return None
    ox,oy=field['position']; tx,ty=target
    dx,dy=tx-ox,ty-oy
    if abs(dx)+abs(dy)!=1:
        return None
    cells=[(int(x)+dx,int(y)+dy) for x,y in field['cells']]
    if any(not state.inside_board(x,y) or not state.is_visible(x,y)
           or state.cell(x,y).solid for x,y in cells):
        return None
    return cells


def move_paper_field(state,field,target):
    cells=_paper_plan(state,field,target)
    if cells is None:
        return False
    field['position']=list(target)
    field['cells']=[list(p) for p in cells]
    return True


def _move_paper(state,ability_id,definition,effect,target):
    from . import construct_environments as fields
    point=_aim_point(state,ability_id,target)
    if point is None:
        return _refuse(_NO_POINT)
    # Context is a real realm constraint, rather than a title-only qualifier.
    if not str(getattr(state,'realm_id','')).startswith('library'):
        return _refuse(_NO_POINT)
    field=next((f for f in fields.active(state) if _paper_plan(state,f,point) is not None),None)
    if field is None:
        return _refuse(_NO_POINT)
    move_paper_field(state,field,point)
    _pay(state,ability_id,definition)
    return _done(state,ability_id,str(definition['name']))


def _narrow_lamp(state, ability_id, definition, effect, target):
    """裁光：把相邻一盏亮着的灯的照明扇区收窄，灯光本身与耗能都不动。

    「收窄」不改 ``light_radius``，只在 ``light_allows`` 上加一段扇形判定——
    半径照旧、耗能照旧，唯一变化是这盏灯只照向施法者这一侧；到期记录被删，
    照明自动恢复（没有第二处状态要还原）。
    """
    from . import construct_environments as fields
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    cell = state.cell(x, y)
    if int(cell.light_radius) <= 0 or not cell.light_on:
        return _refuse("那一格没有正在亮着的灯。")
    if fields.narrow_light_direction(state, x, y) is not None:
        return _refuse("这盏灯已经被裁过——同一次不叠加。")
    dx = (state.player.x > x) - (state.player.x < x)
    dy = (state.player.y > y) - (state.player.y < y)
    if not (dx or dy):
        dx, dy = state.facing or (1, 0)
    turns = max(1, int(effect.get("turns", 3) or 3))
    _pay(state, ability_id, definition)
    fields.start_field(state, "expansion.narrow_light", point, (dx, dy),
                       remaining=turns)
    state.invalidate_sight_radius()
    return _done(state, ability_id,
                 tr("你挡住 ({x}, {y}) 的灯，把它收成朝自己这一侧的扇区，{n} 回合内照不到别处。",
                    x=x, y=y, n=turns))


def _move_own_light(state, ability_id, definition, effect, target):
    """移灯：把自己布下的临时光源搬到可见格，剩余期限原样带走。

    「期限不重置」是这条构想的全部价值所在：搬的是同一份光，不是重新点一次，
    所以 ``turns`` 一个数都不碰。旧格的光属性按记录里存的原值还原。
    """
    from . import expansion_consumables as consumables
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    target_cell = state.cell(x, y)
    if target_cell.solid:
        return _refuse("那一格放不下光——墙里没有照出去的路。")
    if int(target_cell.light_radius) > 0:
        return _refuse("那一格本来就有光，换过去会把原来的灯弄丢。")
    records = [record for record in consumables.records(state)
               if record["kind"] == consumables.PREFIX + "light"]
    if not records:
        return _refuse("你没有自己布下的临时光源可搬。")
    record = min(records, key=lambda row: abs(row["x"] - state.player.x)
                 + abs(row["y"] - state.player.y))
    old_cell = state.cell(record["x"], record["y"])
    data = record.setdefault("data", {})
    if (record["x"], record["y"]) == (x, y):
        return _refuse("光本来就在那一格。")
    _pay(state, ability_id, definition)
    old_cell.light_radius = int(data.get("prev_radius", 0) or 0)
    old_cell.light_on = bool(data.get("prev_on", old_cell.light_on))
    data["prev_radius"] = int(target_cell.light_radius)
    data["prev_on"] = bool(target_cell.light_on)
    target_cell.light_radius = int(data.get("radius", 1) or 1)
    target_cell.light_on = True
    old_x, old_y = record["x"], record["y"]
    record["x"], record["y"] = x, y
    state.invalidate_sight_radius()
    return _done(state, ability_id,
                 tr("你把光从 ({ox}, {oy}) 搬到 ({x}, {y})：剩下的 {n} 回合照旧，没有续期。",
                    ox=old_x, oy=old_y, x=x, y=y, n=int(record.get("turns", 0) or 0)))


RESOLVERS.update({'deflector':_place_mirrors,'double_mirror':_place_mirrors,
                  'move_paper':_move_paper})



def _light_curtain(state,ability_id,definition,effect,target):
    from . import construct_environments as fields
    point=_aim_point(state,ability_id,target)
    if point is None:
        return _refuse(_NO_POINT)
    dx,dy=state.facing
    side=(-dy,dx) if dx or dy else (0,1)
    cells=[(point[0]+side[0]*i,point[1]+side[1]*i) for i in (-1,0,1)]
    if any(not state.inside_board(*p) or not state.is_visible(*p)
            or state.cell(*p).solid for p in cells):
        return _refuse(_NO_POINT)
    _pay(state,ability_id,definition)
    fields.start_field(state,'expansion.light_curtain',point,side,cells=cells,remaining=2)
    state.invalidate_sight_radius()
    return _done(state,ability_id,str(definition['name']))


def _sound_fold(state, ability_id, definition, effect, target):
    """静音折线：沿面朝方向立两段跨缝衰减；只吃声路，视线与其他感知一概不动。"""
    from . import construct_environments as fields
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    dx, dy = state.facing
    normal = (dx, dy) if dx or dy else (1, 0)
    side = (-normal[1], normal[0])
    seam = [point, (point[0] + side[0], point[1] + side[1])]
    far = [(p[0] + normal[0], p[1] + normal[1]) for p in seam]
    if (any(not state.inside_board(*q) or state.cell(*q).solid for q in seam + far)
            or any(not state.is_visible(*q) for q in seam)):
        return _refuse(_NO_POINT)
    turns = max(1, int(effect.get("turns", 3) or 3))
    _pay(state, ability_id, definition)
    field = fields.start_field(state, 'expansion.sound_fold', point, normal,
                               cells=seam, remaining=turns)
    # 衰减记在「格间缝」上，不记在格子上：这样跨缝才对称，绕开缝的声音不受影响。
    field['edges'] = [list(pair) for pair in zip(seam, far)]
    return _done(state, ability_id,
                 tr("静音折线落在 ({x}, {y})：跨过这两段缝的声音都少一格余量，视线照旧。",
                    x=point[0], y=point[1]))


RESOLVERS['light_curtain']=_light_curtain
RESOLVERS['sound_fold']=_sound_fold
RESOLVERS['narrow_lamp']=_narrow_lamp
RESOLVERS['move_own_light']=_move_own_light



def _liquid_transfer_plan(state,source,target,amount):
    from .tamper_protection import liquid_reason
    if source==target or not all(state.inside_board(*p) for p in (source,target)):
        return None
    a,b=state.cell(*source),state.cell(*target)
    if (a.liquid<=0 or not a.liquid_kind or liquid_reason(a.liquid_kind)
            or b.solid or b.liquid>=100 or (b.liquid and b.liquid_kind!=a.liquid_kind)):
        return None
    take=min(max(0,int(amount)),int(a.liquid),max(0,100-int(b.liquid)))
    return (a.liquid_kind,take) if take else None


def transfer_liquid(state,source,target,amount):
    plan=_liquid_transfer_plan(state,source,target,amount)
    if plan is None:
        return 0
    kind,take=plan
    a=state.cell(*source)
    a.liquid-=take
    if not a.liquid:
        a.liquid_kind=''
    state._add_liquid(state.cell(*target),kind,take,position=target)
    state._material_index_ready=False
    return take


def _move_liquid(state,ability_id,definition,effect,target):
    point=_aim_point(state,ability_id,target)
    dx,dy=state.facing
    source=(state.player.x+dx,state.player.y+dy)
    if (point is None or not state.is_visible(*source)
            or _liquid_transfer_plan(state,source,point,1) is None):
        return _refuse(_NO_POINT)
    if effect['kind']=='uphill_liquid':
        from . import construct_environments as fields
        _pay(state,ability_id,definition)
        field=fields.start_field(state,'expansion.uphill_liquid',source,(dx,dy),remaining=3)
        field.update(destination=list(point),reach=12,budget=3)
    else:
        transfer_liquid(state,source,point,1)
        _pay(state,ability_id,definition)
    return _done(state,ability_id,str(definition['name']))


def _pin_liquid(state,ability_id,definition,effect,target):
    from . import construct_environments as fields
    from .tamper_protection import liquid_reason
    point=_aim_point(state,ability_id,target)
    if point is None:
        return _refuse(_NO_POINT)
    cell=state.cell(*point)
    if not cell.liquid or liquid_reason(cell.liquid_kind):
        return _refuse(_NO_POINT)
    fields.start_field(state,'expansion.pin_liquid',point,(0,0),remaining=3)
    _pay(state,ability_id,definition)
    return _done(state,ability_id,str(definition['name']))


def liquid_pinned_cells(state):
    from . import construct_environments as fields
    return {tuple(p) for f in fields.active(state) if f['kind']=='expansion.pin_liquid'
            for p in f['cells']}


def tick_uphill(state,field):
    source=tuple(field['position']);target=tuple(field['destination'])
    if (max(abs(state.player.x-source[0]),abs(state.player.y-source[1]))>field['reach']
            or field.get('budget',0)<=0):
        field['remaining']=0
        return
    moved=transfer_liquid(state,source,target,1)
    field['budget']-=moved


RESOLVERS.update({'move_liquid':_move_liquid,'uphill_liquid':_move_liquid,
                  'pin_liquid':_pin_liquid})


# ---------------------------------------------------------------------------
# 光与土（2026-10-25 第二批）：借昼 / 逐格熄灯 / 犁沟 / 抬沿
# ---------------------------------------------------------------------------
#
# 四行都**不新造机制**：
#
# * 借昼、逐格熄灯 用的仍是 ``consumable:light`` 那条装置记录（``item_devices``
#   每回合 −1，到期把格子的 ``light_radius`` / ``light_on`` 还原）。借昼登记两笔
#   ——灯上一笔（``prev_radius`` 是原亮度）、脚下一笔；逐格熄灯给每盏灯错开到期
#   回合（1/2/3），于是"每回合一盏"就是三条记录的到期顺序，不需要新 tick 分支。
# * 犁沟、抬沿 只改 ``cell.elevation``（自然边界 −2..2，与装备「移土」同口径），
#   并照 ``tactical_layouts`` 的做法往 ``world_ledger.mark_terrain`` 记一笔，
#   重建本层时才回放得出同一片地势。

SOIL_FLOOR = -2
SOIL_CEILING = 2


def _aim_axis(state, point):
    """玩家 → 落点的四向主轴；同格或落点为空时返回 None。"""
    if point is None:
        return None
    dx = int(point[0]) - state.player.x
    dy = int(point[1]) - state.player.y
    if not dx and not dy:
        return None
    if abs(dx) >= abs(dy):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dy > 0 else -1)


def _locked_surface(state, x: int, y: int) -> bool:
    """机关面与设施面：构想的"保护端口/机关灯"都按这一条挡。"""
    from ..data.tamper_protection import MECHANISM_WALL_KINDS
    from .item_targeting import protected_cell
    cell = state.cell(x, y)
    return (cell.wall_kind in MECHANISM_WALL_KINDS or cell.wall_kind == '意识边界'
            or protected_cell(state, x, y))


def _soil_free(state, x: int, y: int) -> bool:
    """这一格能不能动土：看得见、不是实体、不在保护面上。"""
    if not state.inside_board(x, y) or not state.is_visible(x, y):
        return False
    if state.cell(x, y).solid:
        return False
    return not _locked_surface(state, x, y)


def _soil_shift(state, x: int, y: int, delta: int) -> bool:
    """改一格地势；越出自然边界就整笔作废（不夹到边上）。"""
    cell = state.cell(x, y)
    value = int(cell.elevation) + int(delta)
    if value < SOIL_FLOOR or value > SOIL_CEILING:
        return False
    cell.elevation = value
    state.world_ledger.mark_terrain(state.layer_key(), x, y, elevation=value)
    return True


def _soil_free_light(state, x: int, y: int) -> bool:
    """借光/熄灯只要求"看得见且不是机关灯"，不要求地面可动土。"""
    if not state.inside_board(x, y) or not state.is_visible(x, y):
        return False
    return not _locked_surface(state, x, y)


def _borrow_light(state, ability_id, definition, effect, target) -> ActionResult:
    """借昼：从相邻亮灯借三回合光，那盏灯同时变暗，到期一起还。"""
    from . import expansion_consumables
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    if (x, y) == (state.player.x, state.player.y) or state.entity_at(x, y) is not None:
        return _refuse("那不是一盏灯。")
    if not _soil_free_light(state, x, y):
        return _refuse("那盏灯不在你能碰的地方。")
    lamp = state.cell(x, y)
    if not lamp.light_on or int(lamp.light_radius) <= 0:
        return _refuse("那一格没有亮着的灯。")
    here = state.cell(state.player.x, state.player.y)
    # 灯要留一口亮：借到只剩黑，就不是"变暗"而是"熄灭"了。
    take = min(3, int(lamp.light_radius) - 1)
    if take <= 0:
        return _refuse("那盏灯已经暗到借不出光。")
    if here.light_on and int(here.light_radius) >= take:
        return _refuse("你脚下本来就比那盏灯亮。")
    turns = max(1, int(effect.get("turns", 3) or 3))
    _pay(state, ability_id, definition)
    # 同一套还原路径两笔：到期把灯还亮，也把脚下的光收回去。
    expansion_consumables.register(state, "light", (x, y), turns,
                                   prev_radius=int(lamp.light_radius),
                                   prev_on=bool(lamp.light_on),
                                   radius=int(lamp.light_radius) - take,
                                   cone=False, direction=[0, 0])
    lamp.light_radius = max(1, int(lamp.light_radius) - take)
    expansion_consumables.register(state, "light", (state.player.x, state.player.y), turns,
                                   prev_radius=int(here.light_radius),
                                   prev_on=bool(here.light_on),
                                   radius=take, cone=False, direction=[0, 0])
    here.light_radius = take
    here.light_on = True
    return _done(state, ability_id,
                 tr("你从 ({x}, {y}) 那盏灯借了三回合光：脚下亮起来，那盏灯暗了一档。",
                    x=x, y=y))


def _stagger_lights(state, ability_id, definition, effect, target) -> ActionResult:
    """逐格熄灯：可见范围内最近的至多三盏可操控灯，每回合熄一盏。"""
    from . import expansion_consumables
    px, py = state.player.x, state.player.y
    lamps = []
    for y in range(state.height):
        for x in range(state.width):
            if (x, y) == (px, py):
                continue
            cell = state.cell(x, y)
            if not cell.light_on or int(cell.light_radius) <= 0:
                continue
            if not _soil_free_light(state, x, y):
                continue
            lamps.append((max(abs(x - px), abs(y - py)), x, y))
    lamps.sort()
    picks = lamps[:max(1, int(effect.get("max_lamps", 3) or 3))]
    if not picks:
        return _refuse("可见范围里没有你能碰的灯。")
    _pay(state, ability_id, definition)
    for step, (_distance, x, y) in enumerate(picks, 1):
        # 到期回合错开成 1/2/3：到期那一下把格子还原成"关着"，就是熄灯本身。
        expansion_consumables.register(state, "light", (x, y), step,
                                       prev_radius=0, prev_on=False,
                                       radius=int(state.cell(x, y).light_radius),
                                       cone=False, direction=[0, 0])
    return _done(state, ability_id,
                 tr("你记下 {n} 盏灯：接下来每回合熄一盏，机关灯不在此列。", n=len(picks)))


def _furrow(state, ability_id, definition, effect, target) -> ActionResult:
    """犁沟：沿瞄准方向三格各降一档，挖出来的土按格数抬到两侧。"""
    point = _aim_point(state, ability_id, target)
    axis = _aim_axis(state, point)
    if axis is None:
        return _refuse(_NO_POINT)
    dx, dy = axis
    cells = [(int(point[0]) + dx * i, int(point[1]) + dy * i) for i in range(3)]
    if not all(_soil_free(state, x, y) for x, y in cells):
        return _refuse("这条沟要三格都看得见，且都不在保护面上。")
    if any(int(state.cell(x, y).elevation) <= SOIL_FLOOR for x, y in cells):
        return _refuse("那一段已经到底了。")
    sx, sy = -dy, dx
    spots = []
    for x, y in cells:
        spot = next((p for p in ((x + sx, y + sy), (x - sx, y - sy))
                     if _soil_free(state, *p)
                     and int(state.cell(*p).elevation) < SOIL_CEILING), None)
        if spot is None:
            return _refuse("挖出来的土没地方放——两侧都接不下这一档。")
        spots.append(spot)
    _pay(state, ability_id, definition)
    lowered = sum(1 for x, y in cells if _soil_shift(state, x, y, -1))
    raised = sum(1 for spot in spots if _soil_shift(state, *spot, 1))
    return _done(state, ability_id,
                 tr("你在这一段犁出三格沟，挖出的 {n} 档土堆到两侧。", n=min(lowered, raised)))


def _raise_rim(state, ability_id, definition, effect, target) -> ActionResult:
    """抬沿：从朝自己那一侧的邻格取一档土，把落点抬成一道低沿。"""
    point = _aim_point(state, ability_id, target)
    axis = _aim_axis(state, point)
    if axis is None:
        return _refuse("你脚下这一格没有可以取土的邻格。")
    dx, dy = axis
    source = (int(point[0]) - dx, int(point[1]) - dy)
    if source == (state.player.x, state.player.y):
        return _refuse("你脚下这一格不能挖。")
    if not _soil_free(state, *point) or not _soil_free(state, *source):
        return _refuse("取土和落沿的两格都得看得见、且不在保护面上。")
    if int(state.cell(*point).elevation) >= SOIL_CEILING:
        return _refuse("那一格已经是最高的低沿了。")
    if int(state.cell(*source).elevation) <= SOIL_FLOOR:
        return _refuse("取土那一格已经到底了。")
    _pay(state, ability_id, definition)
    _soil_shift(state, *source, -1)
    _soil_shift(state, *point, 1)
    return _done(state, ability_id,
                 tr("你从 ({sx}, {sy}) 取了一档土，把 ({x}, {y}) 抬成一道低沿。",
                    sx=source[0], sy=source[1], x=int(point[0]), y=int(point[1])))


RESOLVERS.update({'borrow_light': _borrow_light,
                  'stagger_lights': _stagger_lights,
                  'furrow': _furrow, 'raise_rim': _raise_rim})


# ---------------------------------------------------------------------------
# 电路与边界（2026-10-25 第三批）：短接 / 析出 / 复核脉冲 / 边界回折
# ---------------------------------------------------------------------------
#
# 四行都接在既有原语上：
#
# * ``短接`` 与一次性物品的 ``circuit`` n==1 同一条路：真的改
#   ``node['inputs']``，过 ``validate_board``，再登记一条 ``consumable:bridge``
#   记录（到期把 ``inputs`` 还原）。保护端口与玩具回路照旧拒绝。
# * ``析出`` 走装备「容器」那一套（``remaining_gear._container`` /
#   ``_take_liquid``）：只把格子里**已经存在**的组分搬进空容器，不碰
#   ``materials.reactions``，所以「不逆转任意反应」是字面成立。
# * ``复核脉冲`` 读 ``_circuit_signal`` 刚写下的 ``realm_features['last_signal']``，
#   只把脉冲重新点亮并重结算——``sequences``／``switches`` 一个数都不动，
#   「原机关次数限制不重置」因此可被断言。
# * ``边界回折`` 用的是既有的 ``escape`` 通道装置（``try_escape`` 踏上去即送），
#   两头都要求亲自走到过（``cell_knowledge(...).explored``）。


def _port_short(state, ability_id, definition, effect, target) -> ActionResult:
    """短接：把一个可见端口短接到通，三回合里它自己说了算。"""
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    if state.circuit_node_at(*point) is None:
        return _refuse("那一格上没有可以短接的端口。")
    if state.realm_id == 'toy_memories':
        return _refuse("玩具回路有绝缘封签，请用机关本身解谜。")
    from .tamper_protection import _facility_cells
    if point in _facility_cells(state):
        return _refuse("那是设施自己的接线，不归你改。")
    _pay(state, ability_id, definition)
    # 短接＝这台既有原语：``forced_until`` 记三回合，期间该端口一律判通。
    state.force_circuit_node(int(point[0]), int(point[1]), by_player=True)
    return _done(state, ability_id,
                 tr("你把 ({x}, {y}) 那个端口短接了三回合：这段时间它一直是通的。",
                    x=int(point[0]), y=int(point[1])))


def _draw_component(state, ability_id, definition, effect, target) -> ActionResult:
    """析出：把可见格里既有的一组分接进自己手上的空容器。"""
    from ..equipment.remaining_gear import _container, _take_liquid
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    cell = state.cell(*point)
    if cell.liquid <= 0 or not cell.liquid_kind:
        return _refuse("那一格里没有能接出来的东西。")
    holder, spec = _container(state, filled=False)
    if holder is None:
        return _refuse("你手上没有能接住它的空容器。")
    cap = int(spec.get('cap', 30) or 30)
    if holder.contents and cell.liquid_kind not in holder.contents:
        return _refuse("容器里已经装了别的东西。")
    room = cap - sum(int(value) for value in holder.contents.values())
    if room <= 0:
        return _refuse("容器已经满了。")
    want = min(max(1, int(effect.get("amount", 12) or 12)), room, int(cell.liquid))
    # 先搬再付款：这一步之后 `_action_time` 会推进世界（液体会摊开），
    # 放在付款之后就会「先摊薄再按摊薄后的量取」——手快也没用。
    took = _take_liquid(state, point, holder, cap, want)
    if not took:
        return _refuse("接不出来了——这一格里的东西不归你动。")
    _pay(state, ability_id, definition)
    return _done(state, ability_id,
                 tr("你把 ({x}, {y}) 里的一组分接进 {item}，反应不会被倒着走。",
                    x=int(point[0]), y=int(point[1]), item=str(holder.name)))


def _resend_signal(state, ability_id, definition, effect, target) -> ActionResult:
    """复核脉冲：复送本层刚发出的一次脉冲；机关自己的计数一个数都不动。"""
    features = getattr(state, 'realm_features', None)
    last = dict((features or {}).get('last_signal') or {})
    if (not last or int(last.get('depth', -1)) != int(getattr(state, 'depth', 0) or 0)):
        return _refuse("本层还没有你自己发出的信号可复核。")
    x, y = int(last.get('x', 0) or 0), int(last.get('y', 0) or 0)
    hit = state.circuit_node_at(x, y)
    if hit is None:
        return _refuse("那个端口已经不在了。")
    board, key, node = hit
    if node['op'] not in ('pulse', 'step'):
        return _refuse("那处端口不是能复送的脉冲。")
    _pay(state, ability_id, definition)
    # 只重放电平：pulses 重新点亮，sequences／switches 原样。
    board['state'].setdefault('pulses', {})[key] = state.time + 1
    state._settle_circuit(board)
    return _done(state, ability_id,
                 tr("你把 ({x}, {y}) 那一次脉冲又送了一遍：机关自己的次数限制没有回到起点。",
                    x=x, y=y))


def _realm_passage(state, ability_id, definition, effect, target) -> ActionResult:
    """边界回折：在你面朝的那格与落点之间接一条只够走几趟的短路。"""
    from . import item_devices
    from .vision.knowledge import cell_knowledge
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    dx, dy = state.facing or (1, 0)
    near = (state.player.x + int(dx), state.player.y + int(dy))
    far = (int(point[0]), int(point[1]))
    reach = int(effect.get("reach", 6) or 6)
    distance = max(abs(far[0] - near[0]), abs(far[1] - near[1]))
    if distance < 2 or distance > reach:
        return _refuse("两头得隔开一点：太近了不用折，太远了折不过去。")
    for x, y in (near, far):
        if state.cell(x, y).solid or state.entity_at(x, y) is not None:
            return _refuse("两头都得是空位。")
        if not cell_knowledge(state, x, y).explored:
            return _refuse("那一头你还没亲自走到过。")
        if _locked_surface(state, x, y):
            return _refuse("那一头压在机关面上——折不通。")
    _pay(state, ability_id, definition)
    item_devices.register_device(state, 'escape', near[0], near[1],
                                 max(1, int(effect.get("turns", 3) or 3)),
                                 a=list(near), b=list(far), uses=0)
    return _done(state, ability_id,
                 tr("你把边界折了一道：({ax}, {ay}) 与 ({bx}, {by}) 之间只隔一步。",
                    ax=near[0], ay=near[1], bx=far[0], by=far[1]))


RESOLVERS.update({'port_short': _port_short, 'draw_component': _draw_component,
                  'resend_signal': _resend_signal, 'realm_passage': _realm_passage})


# ---------------------------------------------------------------------------
# 第四批（2026-10-25）：剩下九行，全部接在**一次性物品**那张处理表上
# ---------------------------------------------------------------------------
#
# 这九行原文各自承诺了一套本作没有的模型（换热、延时弹道、弹体逐格拦截预算、
# 友方单位资源……）。按裁定「能顺应现有系统的接系统，其余改描述」：
#
# * ``开气窗`` / ``压膛`` / ``退壳`` / ``缓拍`` / ``封炉`` / ``冷铸`` / ``代为护理``
#   直接复用 ``expansion_consumables`` 与 ``circuits`` 里已有的那一条（排气／
#   装置记录／脉冲表／相变／护理），只改口径文字，不复制一份实现。
# * ``排线`` / ``迟发`` 原有的机制在本作不存在（没有弹体拦截预算表，也没有
#   延时弹道队列），于是把承诺收到真做得到的一侧：``排线`` 改成「把这一条弹道
#   上的格子记进记忆」（不发射）；``迟发`` 改成「两回合后从那一格响一枪」——
#   真声、走完整声路、不造成伤害，也不跟着谁走。
# * ``压膛`` 的「借来的一档穿透」是本批唯一动到战斗结算的地方：读的是
#   ``expansion_consumables.pierce_loan``，开火时由 ``_shot_penetration`` 领走。


def _vent_window(state, ability_id, definition, effect, target) -> ActionResult:
    """开气窗：把一段已有开口的气体阻力短时压低三回合。"""
    from . import expansion_consumables
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    x, y = point
    cell = state.cell(x, y)
    if not (cell.doorway or (cell.wall_kind in ('门', '机关门') and not cell.solid)):
        return _refuse("那一格不是已经有的开口。")
    if _locked_surface(state, x, y):
        return _refuse("那是保护面——气窗不开在保护墙上。")
    if any(record.get('kind') == expansion_consumables.PREFIX + 'vent'
           and (record['x'], record['y']) == (x, y)
           for record in expansion_consumables.records(state)):
        return _refuse("这一段已经开过气窗了。")
    turns = max(1, int(effect.get("turns", 3) or 3))
    _pay(state, ability_id, definition)
    expansion_consumables.register(state, 'vent', (x, y), turns)
    return _done(state, ability_id,
                 tr("你在 ({x}, {y}) 开了个气窗：这一段的气会散得更快，{n} 回合后自己合上。",
                    x=x, y=y, n=turns))


def _load_pierce(state, ability_id, definition, effect, target) -> ActionResult:
    """压膛：多压一发弹药，换下一发打得穿。"""
    from . import expansion_consumables
    guns = [item for item in state.inventory
            if item.magazine is not None and item.effect != 'expansion_consumable']
    gun = next((item for item in guns if int(item.magazine or 0) > 0), None)
    if gun is None:
        return _refuse("弹匣是空的——压不了膛。")
    if expansion_consumables.pierce_loan(state):
        return _refuse("上一发还压在里面没打出去。")
    amount = max(1, int(effect.get("amount", 2) or 2))
    gun.magazine = int(gun.magazine) - 1          # 这一发是被压进去的，先扣
    _pay(state, ability_id, definition)
    expansion_consumables.register(state, 'pierce_loan',
                                  (state.player.x, state.player.y), 999, amount=amount)
    return _done(state, ability_id,
                 tr("你多压了一发：下一发打出去会多穿 {n} 档。", n=amount))


def _dump_magazine(state, ability_id, definition, effect, target) -> ActionResult:
    """退壳：把弹匣里剩下的弹一次打空，方向散开，不回费用。

    洞察「不白退一发」在这一步留一发在膛里（``keep=1``）：只留**真实剩下的**那一发，
    弹匣只剩一发时留不下任何东西；想把弹匣装满仍要走完整轮装填与全额费用。
    """
    from . import expansion_consumables
    keep = 1 if state.insight_active("不白退一发") else 0
    ok, _message, data = expansion_consumables.projectile(
        state, (state.player.x, state.player.y), None, state.facing, 5, keep=keep)
    if not ok:
        return _refuse("手上没有能打空的弹匣。")
    _pay(state, ability_id, definition)
    fired = int(data.get('ammunition', 0) or 0)
    kept = int(data.get('kept', 0) or 0)
    if kept:
        return _done(state, ability_id,
                     tr("你把弹匣里剩下的 {n} 发一次打空，地上落了一层壳——"
                        "最后那一发留在膛里，随时能打出去。", n=fired))
    return _done(state, ability_id,
                 tr("你把弹匣里剩下的 {n} 发一次打空，地上落了一层壳。",
                    n=fired))


def _trace_line(state, ability_id, definition, effect, target) -> ActionResult:
    """排线：沿选定方向把这一条弹道排出来，沿途看得见的格子记进记忆。"""
    from .ballistics import trace_path
    from .vision.knowledge import record_terrain_cells
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    dx = int(point[0]) - state.player.x
    dy = int(point[1]) - state.player.y
    if not dx and not dy:
        return _refuse("你脚下这一格没有方向可量。")
    step = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dy) else (0, 1 if dy > 0 else -1)
    reach = max(1, int(effect.get("reach", 6) or 6))
    path = trace_path(state.player.x, state.player.y, *step, reach)
    cells = [(x, y) for x, y in path
             if state.inside_board(x, y) and state.is_visible(x, y)]
    if not cells:
        return _refuse("这一向上没有看得见的格子。")
    _pay(state, ability_id, definition)
    learned = record_terrain_cells(state, cells)
    return _done(state, ability_id,
                 tr("你沿这一向把弹道排出来：{n} 格记进了记忆，一枪没开。", n=learned))


def _delayed_shot(state, ability_id, definition, effect, target) -> ActionResult:
    """迟发：先付一发弹药，两回合后从那一格响一枪（真声，不伤人）。"""
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    guns = [item for item in state.inventory
            if item.magazine is not None and item.effect != 'expansion_consumable']
    gun = next((item for item in guns if int(item.magazine or 0) > 0), None)
    if gun is None:
        return _refuse("没有可以压进膛的弹。")
    gun.magazine = int(gun.magazine) - 1
    delay = max(1, int(effect.get("delay", 2) or 2))
    radius = max(4, int(effect.get("radius", 14) or 14))
    _pay(state, ability_id, definition)
    # `pulse_parameters` 是 `_tick_delayed_sounds` 留的口子：不写它的话，
    # 到点一律按 `category='lure'` 派发——那就不是枪声了。
    state.delayed_sounds.append(dict(x=int(point[0]), y=int(point[1]),
                                     due=state.time + delay, radius=radius,
                                     source=str(definition.get('name') or ''),
                                     depth=state.depth,
                                     pulse_parameters=dict(by_player=True, full_alert=True,
                                                           category='projectile')))
    return _done(state, ability_id,
                 tr("你先把这一发压在那里：({x}, {y}) 会在 {n} 回合后响一枪，那里没有人。",
                    x=int(point[0]), y=int(point[1]), n=delay))


def _hold_pulse(state, ability_id, definition, effect, target) -> ActionResult:
    """缓拍：让一处端口上还没走完的那次信号多留一回合。"""
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    hit = state.circuit_node_at(*point)
    if hit is None:
        return _refuse("那一格上没有端口。")
    board, key, node = hit
    if node['op'] not in ('pulse', 'step'):
        return _refuse("那处端口不是能缓一缓的脉冲。")
    pending = int((board['state'].get('pulses') or {}).get(key, -1))
    if pending <= state.time:
        return _refuse("那处端口上没有还没走完的信号。")
    _pay(state, ability_id, definition)
    # 付款已把时钟推进一回合：原先"这一回合就没了"的信号，再留一回合。
    board['state'].setdefault('pulses', {})[key] = pending + 1
    state._settle_circuit(board)
    return _done(state, ability_id,
                 tr("你把 ({x}, {y}) 那一次信号压慢了一拍，它多留了一回合。",
                    x=int(point[0]), y=int(point[1])))


def _seal_vessel(state, ability_id, definition, effect, target) -> ActionResult:
    """封炉：把一个已经破口的容器临时封住三回合。"""
    from . import expansion_consumables
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    ok, _message, _data = expansion_consumables.terrain(state, point, None, None, 4)
    if not ok:
        return _refuse("那一格上没有能临时封住的破口容器。")
    _pay(state, ability_id, definition)
    return _done(state, ability_id, str(definition['name']))


def _cold_set(state, ability_id, definition, effect, target) -> ActionResult:
    """冷铸：把可见格里的一份液体就地凝住。"""
    from . import expansion_consumables
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    ok, _message, data = expansion_consumables.circuit(state, point, None, None, 4)
    if not ok:
        return _refuse("那一格里的东西凝不住——要么没有液体，要么已经在凝了。")
    _pay(state, ability_id, definition)
    return _done(state, ability_id,
                 tr("你把 ({x}, {y}) 里的 {n} 单位就地凝住了，那块地方现在走不过人。",
                    x=int(point[0]), y=int(point[1]),
                    n=int(data.get('crystallized', 0) or 0)))


def _tend_other(state, ability_id, definition, effect, target) -> ActionResult:
    """代为护理：把一份真实恢复品施给相邻的稳定意识，恢复归它，债还是你的。"""
    point = _aim_point(state, ability_id, target)
    if point is None:
        return _refuse(_NO_POINT)
    entity = state.entity_at(*point)
    if (entity is None or entity is state.player
            or str(getattr(entity, 'relation', '')) != '稳定意识'):
        return _refuse("那一格上不是能接受护理的人。")
    if max(abs(entity.x - state.player.x), abs(entity.y - state.player.y)) != 1:
        return _refuse("得挨着才施得了手。")
    index = next((i for i, item in enumerate(state.inventory)
                  if str(item.effect or '').startswith('restore_')
                  or str(item.effect or '') == 'warm_restore'), None)
    if index is None:
        return _refuse("你身上没有可以递过去的恢复品。")
    item = state.inventory[index]
    power = max(1, int(item.power or 1))
    _pay(state, ability_id, definition)
    state._consume_inventory_item(index)
    entity.integrity = min(100, int(entity.integrity) + power)
    return _done(state, ability_id,
                 tr("你把 {item} 递给了 {name}：恢复算在它身上，账还记在你名下。",
                    item=str(item.name), name=str(entity.label or '稳定意识')))


RESOLVERS.update({'vent_window': _vent_window, 'load_pierce': _load_pierce,
                  'dump_magazine': _dump_magazine, 'trace_line': _trace_line,
                  'delayed_shot': _delayed_shot, 'hold_pulse': _hold_pulse,
                  'seal_vessel': _seal_vessel, 'cold_set': _cold_set,
                  'tend_other': _tend_other})
