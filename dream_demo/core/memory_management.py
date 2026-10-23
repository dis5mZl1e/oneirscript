"""Validated reversible memory-slot management using existing inventory/save fields."""
from ..i18n import tr
from .entities import ActionResult
from .content import ITEM_DEFINITIONS
from .content import MEMORY_LIMIT
from .action_permissions import stasis_refusal


def refusal(state):
    if state.run_over:
        return ActionResult(False, tr('这次入梦已经结束，不能继续行动。'))
    blocked = stasis_refusal(state)
    if blocked is not None:
        return blocked
    if 'oblivion_strong' in state.portents:
        return ActionResult(False, tr('无念黑渊吞掉了记忆，你想不起这些东西的用法。'))
    if state.pending_memory:
        return ActionResult(False, tr('请先处理待收纳的记忆碎片。'))
    return None


def unequip_memory(state, memory_id):
    blocked = refusal(state)
    if blocked is not None:
        return blocked
    if (memory_id not in state.memory_fragments or memory_id not in ITEM_DEFINITIONS
            or ITEM_DEFINITIONS[memory_id].get('category') != '记忆碎片'):
        return ActionResult(False, tr('这条记忆已经不在槽中。'))
    if state.inventory_used >= state.inventory_capacity:
        return ActionResult(False, tr('行囊已满，无法取下记忆碎片。'))
    item = state._make_item(memory_id)
    state.memory_fragments.remove(memory_id)
    state._drop_memory_effect(memory_id)
    state.inventory.append(item)
    message = tr('已取下记忆：{name}。', name=tr(item.name))
    state.messages.append(message)
    state._advance(1)
    return ActionResult(True, message)


def equip_memory(state, instance_id):
    blocked = refusal(state)
    if blocked is not None:
        return blocked
    index = next((i for i, item in enumerate(state.inventory) if item.instance_id == instance_id), None)
    if index is None:
        return ActionResult(False, tr('这件物品已经不在行囊中。'))
    item = state.inventory[index]
    if item.category != '记忆碎片' or item.quantity < 1:
        return ActionResult(False, tr('这件物品不是可装入的记忆碎片。'))
    if item.definition_id in state.memory_fragments:
        return ActionResult(False, tr('同一记忆已经装入。'))
    if len(state.memory_fragments) >= MEMORY_LIMIT + state._memory_slot_bonus():
        return ActionResult(False, tr('记忆槽已满，请先取下一条。'))
    state._consume_inventory_item(index)
    state.memory_fragments.append(item.definition_id)
    state._apply_memory_effect(item.definition_id)
    message = tr('已装入记忆：{name}。', name=tr(item.name))
    state.messages.append(message)
    state._advance(1)
    return ActionResult(True, message)
