"""Primitive legacy owner intents preserve selectors while commands queue.

Inventory indices remap by instance identity. Unknown/unremappable command
families conservatively require their exact action/time context. Movement and
waiting remain FIFO inputs while the same world and map are busy.
"""
from dataclasses import dataclass
from copy import deepcopy
from uuid import uuid4

from .core.command_context import capture_command_context
from .core.command_identity import command_object_token
from .core.entities import ActionResult


ITEM_INDEX_COMMANDS = frozenset((
    'use', 'drop', 'equip', 'toggle_equip', 'throw', 'throw_target',
    'deploy_target', 'deploy_pair', 'deploy_direction', 'ignite_here',
    'fire_once', 'fire_once_target', 'container_fill', 'container_pour',
    'put_on_table', 'choose_mirror_insight', 'spray_fire', 'spray_target'))
CONTINUOUS_COMMANDS = frozenset(('move', 'wait', 'pickup', 'interact'))
ZERO_TIME_COMMANDS = frozenset(('presentation_control', 'ui_control',
                                'catalog_control', 'tutorial_view'))


def map_identity(state):
    identity = getattr(state, '_presentation_map_identity', None)
    if type(identity) is not int or identity <= 0:
        identity = uuid4().int
        state._presentation_map_identity = identity
    return identity


@dataclass(frozen=True)
class LegacyIntent:
    context: tuple
    map_identity: int
    layer: str
    command: str
    args: tuple
    choice: str | None
    selectors: tuple
    strict: bool


def _pending_signature(state):
    from .legacy_display import freeze
    npc, event = state.pending_npc(), state.pending_event()
    return (None if npc is None else command_object_token(npc),
            None if event is None else (event.instance_uid, event.event_id,
                                       event.x, event.y, freeze(event.options)))


def capture_intent(state, command, args, choice):
    args = tuple(args)
    selectors = []
    strict = command not in CONTINUOUS_COMMANDS | ZERO_TIME_COMMANDS
    if command in ITEM_INDEX_COMMANDS:
        index = args[0] if args else 0
        if type(index) is int and 0 <= index < len(state.inventory):
            item = state.inventory[index]
            selectors.append(('inventory', 0, str(item.instance_id), item.definition_id))
            args = (index, *args[1:])
            strict = command == 'choose_mirror_insight'
        elif command in ('spray_fire', 'spray_target') and index == -1:
            pass  # Hand source depends on the full equipment context.
        else:
            strict = True
    if command == 'collect_items':
        for ordinal, index in enumerate(args):
            if type(index) is not int or not 0 <= index < len(state.world_items):
                strict = True
                break
            entry = state.world_items[index]
            selectors.append(('world_item', ordinal, command_object_token(entry),
                              (entry.x, entry.y, entry.surface)))
        else:
            strict = False
    if command in ('choose_npc_option', 'choose_event_option') or (
            command == 'ui_control' and args and args[0] == 'close_dialog'):
        selectors.append(('pending', _pending_signature(state)))
    if command == 'presentation_control' and len(args) > 2 and args[1] == 'talk_npc':
        npc = next((entity for entity in state.enemies if entity.id == args[2]), None)
        selectors.append(('npc', None if npc is None else command_object_token(npc)))
    return LegacyIntent(capture_command_context(state), map_identity(state),
                        state.layer_key(), command, deepcopy(args), choice,
                        tuple(selectors), strict)


def resolve_intent(state, intent):
    """Call under the owner's action lock before root-action side effects."""
    def rejected():
        return ActionResult(False, 'This selection has changed; choose it again.',
                            {'stale_selection': True})
    if type(intent) is not LegacyIntent:
        return rejected()
    context = capture_command_context(state)
    if (intent.context[0] != context[0] or intent.map_identity != map_identity(state)
            or intent.layer != state.layer_key()
            or intent.strict and intent.context != context):
        return rejected()
    args = list(intent.args)
    for selector in intent.selectors:
        kind = selector[0]
        if kind == 'inventory':
            _, ordinal, identity, definition = selector
            index = next((index for index, item in enumerate(state.inventory)
                          if str(item.instance_id) == identity
                          and item.definition_id == definition and item.quantity > 0), None)
            if index is None:
                return rejected()
            args[ordinal] = index
        elif kind == 'world_item':
            _, ordinal, identity, provenance = selector
            index = next((index for index, entry in enumerate(state.world_items)
                          if command_object_token(entry) == identity
                          and (entry.x, entry.y, entry.surface) == provenance), None)
            if index is None:
                return rejected()
            args[ordinal] = index
        elif kind == 'pending' and _pending_signature(state) != selector[1]:
            return rejected()
        elif kind == 'npc':
            npc = next((entity for entity in state.enemies if entity.id == args[2]), None)
            if npc is None or command_object_token(npc) != selector[1]:
                return rejected()
    return intent.command, tuple(args), intent.choice
