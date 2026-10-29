"""Expansion choices replace existing slots; previews never spend an award.

Menu state lives in the existing per-layer realm_features snapshot. Integer
random-slot counters live in the existing run award ledger, so reloads and
revisiting a layer cannot reroll or replenish them.
"""
from __future__ import annotations

import random

from ..data.expansion.catalog import BY_ID, ENTRIES, TUNING_DEFAULTS
from ..data.expansion.sources import EVENT_FAMILIES, event_themes
from ..data.ids import stable_seed
from ..i18n import tr
from .constants import ActionKind
from .entities import ActionResult


def events_for_theme(theme):
    return EVENT_FAMILIES.get(theme, ())


def _growth_refusal(state, entry):
    if entry['category'] == 'ability':
        if entry['id'] in state.abilities:
            return tr('你已经习得这个构想。')
    elif entry['category'] == 'insight':
        if entry['name_zh'] in state.insights:
            return tr('你已经拥有这个洞察。')
        if state.pending_insight:
            return tr('请先安置或放弃待选的洞察。')
    elif entry['category'] == 'memory' and state.pending_memory:
        return tr('请先安置或放弃待选的记忆。')
    return None


def _eligible(state, entry, source):
    from .content import ABILITY_DEFINITIONS, INSIGHT_DEFINITIONS, ITEM_DEFINITIONS
    from .item_access import refusal
    key = entry['id']
    if entry.get('integration_status') != 'runtime' or key not in ITEM_DEFINITIONS:
        return False
    if entry['category'] == 'ability' and key not in ABILITY_DEFINITIONS:
        return False
    if entry['category'] == 'insight' and entry['name_zh'] not in INSIGHT_DEFINITIONS:
        return False
    return not refusal(state, key, source=source) and not _growth_refusal(state, entry)


def random_candidates(state):
    return tuple(entry['id'] for entry in ENTRIES
                 if entry['source_permission'] == 'G'
                 and int(state.item_grant_counts.get('__expansion_placed__:' + entry['id'], 0))
                 < max(1, int(entry['tuning_proposal']['max_acquisitions_per_run']))
                 and _eligible(state, entry, 'expansion.random'))


def random_choice(state, rng, *, theme=None):
    candidates = [BY_ID[key] for key in random_candidates(state)]
    if not candidates:
        return None
    sequence = state.item_grant_counts.get('__expansion_draws__', 0)
    recent_window = int(TUNING_DEFAULTS['recent_id_exclusion_window'])
    fresh = [entry for entry in candidates if sequence - int(state.item_grant_counts.get(
        '__expansion_recent__:' + entry['id'], -recent_window - 1)) > recent_window]
    candidates = fresh or candidates
    categories = tuple(category for category in TUNING_DEFAULTS['category_weights_percent']
                       if any(entry['category'] == category for entry in candidates))
    category = rng.choices(categories, weights=[TUNING_DEFAULTS['category_weights_percent'][c]
                                               for c in categories], k=1)[0]
    candidates = [entry for entry in candidates if entry['category'] == category]
    local = [entry for entry in candidates if entry['theme'] == theme]
    cross = [entry for entry in candidates if entry['theme'] != theme]
    if local and cross:
        candidates = (local if rng.randrange(100) < TUNING_DEFAULTS['local_theme_weight_percent']
                      else cross)
    return candidates[rng.randrange(len(candidates))]['id']


def record_random_slot(state, item_id):
    sequence = int(state.item_grant_counts.get('__expansion_draws__', 0))
    state.item_grant_counts['__expansion_recent__:' + item_id] = sequence
    state.item_grant_counts['__expansion_draws__'] = sequence + 1
    key = '__expansion_placed__:' + item_id
    state.item_grant_counts[key] = int(state.item_grant_counts.get(key, 0)) + 1


def keep_optional_opportunity(state, *, protected=False):
    if protected:
        return True
    key = '__expansion_optional_opportunities__'
    number = int(state.item_grant_counts.get(key, 0)) + 1
    state.item_grant_counts[key] = number
    reduction = int(TUNING_DEFAULTS['noncore_opportunity_reduction_percent'])
    return (number * reduction // 100) == ((number - 1) * reduction // 100)


def local_theme(state):
    if state.realm_id or state.depth >= 28:
        return 'realm'
    theme = str(state.theme)
    for name, hints in (('circuit', '电机'), ('light', '光镜影'),
                        ('sound', '声铃响静'), ('terrain', '潮海流湿')):
        if any(hint in theme for hint in hints):
            return name
    return None


def optional_slot(state, legacy_id, rng):
    """Replace, reduce, or retain one already-generated optional growth slot."""
    if state.depth < 4 or not random_candidates(state):
        return legacy_id
    if not keep_optional_opportunity(state):
        return None
    if rng.random() >= 0.5:
        return legacy_id
    chosen = random_choice(state, rng, theme=local_theme(state))
    if chosen:
        record_random_slot(state, chosen)
    return chosen or legacy_id


def target_choices(state, *, theme, category=None):
    return tuple(entry['id'] for entry in ENTRIES
                 if entry['source_permission'] == 'D' and entry['theme'] == theme
                 and (category is None or entry['category'] == category)
                 and _eligible(state, entry, entry['source_id']))


def _key(state, event):
    # The UID is present after opening. The fallback makes a pre-open preview
    # identical and never invokes the UID allocator from a read-only view.
    return (str(state.depth) + ':' + str(state.realm_id) + ':' + str(state.realm_depth)
            + ':' + str(event.event_id) + ':' + str(event.x) + ':' + str(event.y))


def _record(state, event):
    return state.realm_features.get('expansion_reward_choices', {}).get(_key(state, event), {})


def mark_event_claimed(state, event, item_id=''):
    if not event_themes(event.event_id) and not (state.depth >= 28
                                                and event.event_id.startswith('event.')):
        return
    state.realm_features.setdefault('expansion_reward_choices', {})[_key(state, event)] = {
        'claimed': True, 'item': item_id}


def _clues(state, event):
    local = event_themes(event.event_id)
    if state.depth >= 28 and event.event_id.startswith('event.'):
        local = tuple(dict.fromkeys(('realm', *local)))
    if not local:
        return ()
    legal = [theme for theme in EVENT_FAMILIES if target_choices(state, theme=theme)]
    chosen = [theme for theme in local if theme in legal]
    other = [theme for theme in legal if theme not in chosen]
    random.Random(stable_seed('expansion.clues', state.seed, _key(state, event))).shuffle(other)
    return tuple((chosen + other[:max(0, 2 - len(chosen))])[:3])


def event_options(state, event, original):
    if event is None or event.resolved or event.uses_left <= 0 or _record(state, event).get('claimed'):
        return original
    clues = _clues(state, event)
    if not clues:
        return original
    menu = _record(state, event).get('menu') or {}
    theme = menu.get('theme')
    category = menu.get('category')
    if theme not in clues:
        labels = {'sound': '声源线索', 'light': '光场线索', 'terrain': '地势线索',
                  'projectile': '轨迹线索', 'circuit': '电路线索', 'realm': '边界线索'}
        return tuple(original) + tuple({
            'option_id': 'expansion.clue.' + clue,
            'label': tr('追寻{clue}（与原奖励择一）', clue=tr(labels[clue])),
            'expansion_reward': {'theme': clue},
        } for clue in clues)
    if category is None:
        labels = {'equipment': '装备', 'insight': '洞察', 'memory': '记忆碎片',
                  'ability': '构想', 'consumable': '稀有消耗品'}
        options = [{'option_id': f'expansion.category.{theme}.{kind}',
                    'label': tr(label), 'expansion_reward': {'theme': theme, 'category': kind}}
                   for kind, label in labels.items()
                   if target_choices(state, theme=theme, category=kind)]
    else:
        options = [{'option_id': 'expansion.target.' + key,
                    'label': tr('{name}：{description}', name=tr(BY_ID[key]['name_zh']),
                                description=tr(BY_ID[key]['description_zh'])),
                    'expansion_reward': {'item': key}}
                   for key in target_choices(state, theme=theme, category=category)]
    return tuple(options) + ({'option_id': 'expansion.back', 'label': tr('返回原事件'),
                              'expansion_reward': {'back': True}},)


def apply_growth(state, item_id):
    entry = BY_ID[item_id]
    reason = _growth_refusal(state, entry)
    if reason:
        return ActionResult(False, reason)
    if entry['category'] == 'ability':
        state.abilities.append(item_id)
        message = tr('永久习得构想：{name}。', name=tr(entry['name_zh']))
    elif entry['category'] == 'insight':
        message = state._grant_insight(entry['name_zh'])
    else:
        return ActionResult(False, tr('这个条目不是成长内容。'))
    return ActionResult(True, message, {'growth': item_id})


def resolve_event_choice(state, event, choice):
    if (state.pending_event() is not event or event.resolved or event.uses_left <= 0
            or _record(state, event).get('claimed')):
        return ActionResult(False, tr('这次奖励机会已经结束。'))
    offered = event_options(state, event, tuple(event.options))
    if choice not in [option.get('expansion_reward') for option in offered]:
        return ActionResult(False, tr('这个目标不在当前线索中。'))
    if 'item' not in choice:
        menu = {} if choice.get('back') else dict(choice)
        state.realm_features.setdefault('expansion_reward_choices', {})[_key(state, event)] = {
            'menu': menu}
        return ActionResult(True, tr('请选择要追寻的目标。'), {'dialogue': event.event_id})
    entry = BY_ID.get(choice['item'])
    if not entry or not _eligible(state, entry, entry['source_id']):
        return ActionResult(False, tr('这个目标目前不能获得。'))
    kind = entry['category']
    if kind in ('equipment', 'consumable') and not state._reward_fits(entry['id']):
        return ActionResult(False, tr('意识行囊已满，异常地点暂时无法交付显化物。'))
    # All refusal paths above precede the award, event counter and action cost.
    if kind in ('insight', 'ability'):
        result = apply_growth(state, entry['id'])
        if not result.changed:
            return result
    elif kind == 'memory':
        state._add_memory(entry['id'])
    else:
        state._add_inventory_item(state._make_item(entry['id']))
    from .item_access import record_grant
    record_grant(state, entry['id'], source=entry['source_id'])
    mark_event_claimed(state, event, entry['id'])
    event.resolved = True
    event.uses_left = 0
    state.close_event_dialog()
    state._record_catalog_interaction(event.catalog_id, event.name, 'site', event.description)
    state._add_dissolution(event.dissolution_reward)
    state.run_stats['events'] = state.run_stats.get('events', 0) + 1
    state._action_time(1, ActionKind.USE)
    message = tr('事件线索兑现：{name}。', name=tr(entry['name_zh']))
    state.messages.append(message)
    return ActionResult(True, message, {'event': event.event_id, 'reward': entry['id']})
