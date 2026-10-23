"""Transactional, portable medicine selections using the ordinary dialogue UI."""
from ..materials import portent_def
from ..i18n import tr
from .entities import ActionResult, WorldEvent
from .constants import ActionKind
from .cast_fx import animate_medicine


def candidates(state, positive=False):
    holder = state.player
    return tuple(pid for pid, turns in sorted(holder.portents.items())
                 if turns > 0 and portent_def(pid) and portent_def(pid).washable
                 and (not positive or (portent_def(pid).kind == '正面'
                      and turns + holder.portent_attach.get(pid, 0) >= 3)))


def open_selection(state, item):
    positive = item.effect == 'hospital_positive_choice'
    ids = candidates(state, positive)
    if not ids:
        return ActionResult(False, tr('没有满足条件的可洗征兆，未消耗药物。'))
    state.close_event_dialog()
    options = tuple(dict(label=tr('{name}：附着{a}＋持续{t} → 削短{n}回合',
                    name=tr(portent_def(pid).name), a=state.player.portent_attach.get(pid, 0),
                    t=state.player.portents[pid], n=3 if positive else 4),
                    medicine_choice=dict(instance=item.instance_id, portent=pid,
                                         positive=positive)) for pid in ids)
    event = WorldEvent('medicine.' + item.instance_id, item.name,
                       state.player.x, state.player.y,
                       tr('选择处理的征兆，取消不消耗。'), dissolution_reward=0,
                       catalog_id='hospital.medicine_choice', kind='compound',
                       dialogue=(tr(item.description),),
                       options=options + (dict(label=tr('取消'), leave=True),), bound=True)
    state.events.append(event)
    state.open_event_dialog(event)
    return ActionResult(True, event.description, {'medicine_dialogue': True})


@animate_medicine
def confirm_selection(state, event, choice):
    if event.catalog_id != 'hospital.medicine_choice':
        return ActionResult(False, tr('这不是药物选择。'))
    index = next((i for i, item in enumerate(state.inventory)
                  if item.instance_id == choice.get('instance')), None)
    if index is None:
        return ActionResult(False, tr('这份药物已不在行囊中，未结算。'))
    item = state.inventory[index]
    positive = item.effect == 'hospital_positive_choice'
    if item.effect not in ('hospital_wash_choice', 'hospital_positive_choice'):
        return ActionResult(False, tr('药物类型已改变，未结算。'))
    pid = choice.get('portent')
    if pid not in candidates(state, positive):
        return ActionResult(False, tr('征兆已不满足条件，未消耗药物。'))
    state.shorten_portent(state.player, 3 if positive else 4, {pid})
    if positive:
        state.restore_resource('lucidity', 4, ingested=True)
    item.quantity -= 1
    if item.quantity <= 0:
        state.board.remove_item(item.instance_id)
        state.equipment.invalidate()
        state.inventory.pop(index)
    state.close_event_dialog()
    state.run_stats['items_used'] = state.run_stats.get('items_used', 0) + 1
    state._action_time(1, ActionKind.USE)
    message = tr('使用了 {item}。', item=tr(item.name))
    state.messages.append(message)
    return ActionResult(True, message, {'item': item.definition_id, 'shortened_portent': pid})
