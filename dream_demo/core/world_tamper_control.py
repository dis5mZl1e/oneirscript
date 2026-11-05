"""Portable, immutable preview intents; only the owner builds execution plans."""
from dataclasses import dataclass

from .command_context import capture_command_context, matches_command_context
from .command_identity import command_object_token
from .entities import ActionResult
from ..i18n import tr


@dataclass(frozen=True)
class SlotPreview:
    category: str
    x: int
    y: int
    identity: int | None
    signature: tuple


@dataclass(frozen=True)
class WorldPreview:
    context: tuple
    layer: str
    slots: tuple[SlotPreview, ...]
    valid: bool = True


@dataclass(frozen=True)
class RangePreview:
    context: tuple
    layer: str
    word: str
    conditions: tuple
    targets: tuple[SlotPreview, ...]
    excluded: tuple
    costs: tuple


@dataclass(frozen=True)
class PreparedTamper:
    sentence: object
    word: str
    index: int
    conditions: tuple
    plan: object = None


def _portable_signature(state, slot):
    from .tamper_world import _signature
    signature = _signature(state, slot)
    if slot.region_members:
        return signature
    if slot.category == 'anomaly':
        return (command_object_token(slot.enemy), *signature[1:])
    return (*signature[:-1], tuple(command_object_token(item)
                                  for item in state.world_items
                                  if (item.x, item.y) == (slot.x, slot.y)))


def _capture_slot(state, slot):
    return SlotPreview(slot.category, slot.x, slot.y,
                       command_object_token(slot.enemy) if slot.category == 'anomaly' else None,
                       _portable_signature(state, slot))


def capture_world_preview(state, sentence):
    from .tamper_world import _preview_current
    return WorldPreview(capture_command_context(state), state.layer_key(),
                        tuple(_capture_slot(state, slot) for slot in sentence.slots),
                        not sentence.consumed and _preview_current(state, sentence, 0))


def capture_range_preview(state, plan):
    return RangePreview(capture_command_context(state), state.layer_key(),
                        plan.word_id, tuple(plan.condition_ids),
                        tuple(_capture_slot(state, target.slot) for target in plan.targets),
                        tuple(plan.excluded), (plan.imagination, plan.chaos_delta))


def submit_world_tamper(session, preview, word_id, slot_index, *, condition_ids=(),
                        gather_destination=None, range_mode='single', range_preview=None):
    command = 'commit_range_tamper' if range_mode == 'vision' else 'commit_world_tamper'
    if range_mode not in ('single', 'vision'):
        return _rejected()
    return session.apply(command, preview, word_id, slot_index, tuple(condition_ids),
                         gather_destination, range_preview)


def _rejected():
    return ActionResult(False, tr('眼前的情形已经改变，请重新选择。'))


def prepare_world_tamper(state, command, *args):
    """Validate before opening a root action or clearing projectile playback."""
    from . import tamper_world as world
    if len(args) != 6:
        return _rejected()
    preview, word, index, conditions, destination, range_preview = args
    if (type(preview) is not WorldPreview or not preview.valid
            or not matches_command_context(state, preview.context)
            or preview.layer != state.layer_key() or state.run_over
            or type(word) is not str or type(index) is not int
            or not 0 <= index < len(preview.slots)
            or type(conditions) is not tuple or any(type(c) is not str for c in conditions)
            or len(preview.slots) > 4):
        return _rejected()
    if destination is not None and (type(destination) is not tuple or len(destination) != 2
                                    or any(type(v) is not int for v in destination)):
        return _rejected()
    slots = []
    for expected in preview.slots:
        if (type(expected) is not SlotPreview or type(expected.x) is not int
                or type(expected.y) is not int
                or not (0 <= expected.x < state.width and 0 <= expected.y < state.height)
                or not state.is_visible(expected.x, expected.y)):
            return _rejected()
        if expected.category == 'anomaly':
            enemy = next((enemy for enemy in state.enemies
                          if command_object_token(enemy) == expected.identity), None)
            if (enemy is None or (enemy.x, enemy.y) != (expected.x, expected.y)
                    or enemy.integrity <= 0 or enemy.relation != '失控意识'):
                return _rejected()
            slot = world.WorldSlot('anomaly', tr(enemy.label), enemy, enemy.x, enemy.y)
        else:
            slot = world._named_cell(state, expected.x, expected.y, include_ground=True)
            if slot is None or slot.category != expected.category:
                return _rejected()
        if _portable_signature(state, slot) != expected.signature:
            return _rejected()
        slots.append(slot)
    sentence = world.build_sentence(state, slots[0], slots[1:])
    if destination is not None:
        sentence.slots[index].gather_destination = destination
    plan = None
    if command == 'commit_range_tamper':
        from .tamper_range import build_plan
        if type(range_preview) is not RangePreview:
            return _rejected()
        plan = build_plan(state, word, condition_ids=conditions)
        if isinstance(plan, str):
            return ActionResult(False, plan)
        if capture_range_preview(state, plan) != range_preview:
            return _rejected()
    return PreparedTamper(sentence, word, index, conditions, plan)


def execute_world_tamper(state, command, prepared):
    if command == 'commit_range_tamper':
        from .tamper_range import commit_range_tamper
        return commit_range_tamper(state, prepared.sentence, prepared.word,
                                   condition_ids=prepared.conditions, plan=prepared.plan)
    from .tamper_world import commit_world_tamper
    return commit_world_tamper(state, prepared.sentence, prepared.word, prepared.index,
                               condition_ids=prepared.conditions)
