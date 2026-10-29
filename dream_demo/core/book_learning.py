"""Stable book offers and transactional permanent conception learning."""
import random

from ..data.abilities import ABILITY_DEFINITIONS
from ..i18n import tr
from .constants import ActionKind
from .entities import ActionResult, WorldEvent

CATALOG_ID = 'book.learning_choice'


def _is_combat_learning(key: str) -> bool:
    return bool(ABILITY_DEFINITIONS[key].get('combat'))


def _weighted_pick(rng: random.Random, ids):
    weights = [max(1, int(ABILITY_DEFINITIONS[key]['combat'].get('weight', 1)))
               for key in ids]
    return rng.choices(list(ids), weights=weights, k=1)[0]


def _eligible(state, ids):
    """书本三选一与随机习得共用同一资格口径（见 item_access.ability_learnable）。"""
    from .item_access import ability_learnable
    return [key for key in ids if ability_learnable(state, key)]


def _combat_candidates(state, pool: str) -> tuple[str, ...]:
    """§13 学习经济：旧池 ≥3 时新组最多占 1/3（40% 概率）；旧池不足时补齐。"""
    ids = _eligible(state, sorted(key for key, definition in ABILITY_DEFINITIONS.items()
                                  if definition.get('acquire_pool', 'general') == pool))
    rng = random.Random(f'{state.seed}:book:{getattr(state, "book_offer_sequence", 0)}:{pool}')
    old = [key for key in ids if not _is_combat_learning(key) and key not in state.abilities]
    new = [key for key in ids if _is_combat_learning(key) and key not in state.abilities]
    rng.shuffle(old)
    rng.shuffle(new)
    if len(old) >= 3:
        if new and rng.random() < 0.4:
            return tuple(old[:2] + [_weighted_pick(rng, new)])
        return tuple(old[:3])
    offered = list(old[:3])
    while len(offered) < 3 and new:
        pick = _weighted_pick(rng, new)
        new.remove(pick)
        offered.append(pick)
    return tuple(offered)


def candidates(state, pool='general'):
    if pool == 'general':
        return _combat_candidates(state, pool)
    ids = _eligible(state, sorted(key for key, definition in ABILITY_DEFINITIONS.items()
                                  if definition.get('acquire_pool', 'general') == pool))
    random.Random(f'{state.seed}:book:{getattr(state, "book_offer_sequence", 0)}:{pool}').shuffle(ids)
    return tuple(key for key in ids if key not in state.abilities)[:3]


def _consume(state, item, ability=None):
    if ability is None:
        state.restore_resource('imagination', 10)
        message = tr('构想已全部习得，书卷化作 10 点想象力。')
    else:
        state.abilities.append(ability)
        from .origin_course import is_course
        message = tr('练习习得构想：{name}；离开教学层时归还。' if is_course(state)
                     else '永久习得构想：{name}。', name=tr(ABILITY_DEFINITIONS[ability]['name']))
    item.quantity -= 1
    if item.quantity <= 0:
        state.board.remove_item(item.instance_id)
        state.equipment.invalidate()
        state.inventory.remove(item)
    state.book_offer_sequence = getattr(state, 'book_offer_sequence', 0) + 1
    state.close_event_dialog()
    state.run_stats['items_used'] = state.run_stats.get('items_used', 0) + 1
    state._action_time(1, ActionKind.USE)
    state.messages.append(message)
    return ActionResult(True, message, {'item': item.definition_id, 'learned_ability': ability})


def open_selection(state, item):
    if item.quantity <= 0:
        return ActionResult(False, tr('书卷已失效，未消耗。'))
    ids = candidates(state)
    if not ids:
        return _consume(state, item)
    state.close_event_dialog()
    sequence = getattr(state, 'book_offer_sequence', 0)
    options = []
    for key in ids:
        definition = ABILITY_DEFINITIONS[key]
        options.append(dict(label=tr('{name}｜想象力 {cost}｜冷却 {cooldown} 回合\n{description}',
                                    name=tr(definition['name']), cost=definition['cost'],
                                    cooldown=definition['cooldown'], description=tr(definition['description'])),
                            book_choice=dict(instance=item.instance_id, sequence=sequence,
                                             pool='general', ability=key)))
    from .origin_course import is_course
    description=tr('选择一个构想供本层练习；离开时归还，取消不消耗。' if is_course(state)
                   else '选择一个构想永久习得；取消不消耗。')
    event = WorldEvent('book.' + item.instance_id, item.name, state.player.x, state.player.y,
                       description, dissolution_reward=0,
                       catalog_id=CATALOG_ID, kind='compound', bound=True,
                       dialogue=(tr(item.description),),
                       options=tuple(options) + (dict(label=tr('取消'), leave=True),))
    # Private snapshot bypasses effective/tampered event rewards and binds this exact offer.
    event._book_offer = (item.instance_id, sequence, 'general', ids)
    state.events.append(event)
    state.open_event_dialog(event)
    return ActionResult(True, event.description, {'book_dialogue': True})


def confirm_selection(state, event, choice):
    snapshot = getattr(event, '_book_offer', None)
    if (event.catalog_id != CATALOG_ID or state.pending_event() is not event
            or event not in state.events or not snapshot or not isinstance(choice, dict)):
        return ActionResult(False, tr('书卷已失效，未消耗。'))
    instance, sequence, pool, offered = snapshot
    ability = choice.get('ability')
    item = next((item for item in state.inventory if item.instance_id == instance), None)
    if (choice != dict(instance=instance, sequence=sequence, pool=pool, ability=ability)
            or sequence != getattr(state, 'book_offer_sequence', 0)
            or item is None or item.quantity <= 0 or item.definition_id != 'spellbook'
            or item.effect != 'learn_ability' or ability not in offered
            or ability not in candidates(state, pool) or ability in state.abilities):
        return ActionResult(False, tr('书卷已失效，未消耗。'))
    return _consume(state, item, ability)


def choose_option(state, event, index):
    if not (0 <= index < len(event.options)):
        return ActionResult(False, tr('书卷已失效，未消耗。'))
    option = event.options[index]
    if option == dict(label=tr('取消'), leave=True):
        state.close_event_dialog()
        return ActionResult(False, tr('取消'))
    return confirm_selection(state, event, option.get('book_choice'))
