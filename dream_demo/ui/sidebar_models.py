"""Read-only sidebar facts. No dry-run execution, name matching, or guessed bonuses."""
from ..i18n import tr
from ..core.content import ITEM_DEFINITIONS


def item_by_id(state, identity):
    return next((item for item in state.inventory if item.instance_id == identity and item.quantity > 0), None)


def item_facts(state, identity):
    item = item_by_id(state, identity)
    if item is None:
        return None
    from .panels import _item_description
    hidden = 'oblivion_strong' in state.portents
    return dict(id=identity, definition_id=item.definition_id, name='？？？' if hidden else tr(item.name),
                quantity=item.quantity, category=tr(item.category), description=tr('无念黑渊吞掉了记忆，你想不起这些东西的用法。') if hidden else _item_description(item, state),
                power=0 if hidden else item.power, penetration=0 if hidden else item.penetration, push=0 if hidden else item.push,
                radius=0 if hidden else item.explosion_radius, contents={} if hidden else dict(item.contents),
                equipped=identity in state.equipped.values(),
                magazine=item.magazine, capacity=item.magazine_capacity)


def comparison(state, identity):
    item = item_by_id(state, identity)
    if item is None:
        return None
    peers = [other.instance_id for other in state.equipped_items()
             if other.slot == item.slot and other.instance_id != identity] if item.slot else []
    board = bool(state._placeable_slot(item))
    return dict(requires_board=board, peers=peers,
                note=tr('需在联想盘中放置后确定') if board else tr('仅比较物品实际字段，不预估未触发的组合。'))


def task_items(state, uid):
    from ..data.quests import QUEST_DEFINITIONS
    record = state.world_ledger.tasks.get(uid)
    if record is None or record.status not in ('进行中', '待交付'):
        return []
    requirement = (QUEST_DEFINITIONS.get(record.definition_id) or {}).get('requirement') or {}
    if requirement.get('type') == 'liquid':
        material = requirement.get('liquid')
        return [item.instance_id for item in state.inventory if item.contents.get(material, 0) > 0]
    wanted = requirement.get('item')
    return [item.instance_id for item in state.inventory if wanted and item.definition_id == wanted]
