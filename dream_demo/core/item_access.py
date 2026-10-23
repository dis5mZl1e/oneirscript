"""Shared eligibility and durable award counts for explicitly limited items.

Constructing an Item is not an award: previews, legacy copies and moving an
existing item must not spend a grant. Producers validate before committing.
"""
from __future__ import annotations
from ..data.items import ITEM_DEFINITIONS
from ..i18n import tr


def refusal(state, item_id, *, source='', count=1):
    if count <= 0:
        return None
    definition = ITEM_DEFINITIONS.get(item_id, {})
    minimum = int(definition.get('min_depth', 0))
    if state.depth < minimum:
        return tr('这件显化物尚未到可获得的梦层。')
    allowed = definition.get('grant_source')
    if allowed and source != allowed:
        return tr('这件显化物只能从指定挑战获得。')
    limit = int(definition.get('run_limit', 0))
    if limit and int(state.item_grant_counts.get(item_id, 0)) + count > limit:
        return tr('本局已经获得过这件限定显化物。')
    return None


def record_grant(state, item_id, *, source='', count=1):
    reason = refusal(state, item_id, source=source, count=count)
    if reason:
        raise ValueError(reason)
    if count > 0 and ITEM_DEFINITIONS.get(item_id, {}).get('run_limit'):
        state.item_grant_counts[item_id] = int(state.item_grant_counts.get(item_id, 0)) + count


def run_limit_refusal(state, item_id, *, count=1):
    """只查 run 级上限，不做渠道匹配。

    地面与台面上的东西已经在**生成时**过了资格筛选；旧档里可能还留着
    当初合法捡到的限定件，捡它不该被 ``grant_source`` 再拒一次。
    """
    limit = int(ITEM_DEFINITIONS.get(item_id, {}).get('run_limit', 0))
    if limit and int(state.item_grant_counts.get(item_id, 0)) + count > limit:
        return tr('本局已经获得过这件限定显化物。')
    return None


def record_pickup(state, item_id, *, count=1):
    """捡到即计入 run 级上限（丢弃／损坏／用掉都不退）。

    地面散投与台面承载的实物不经过 ``record_grant``，不在这儿记一笔，
    「每局最多 N 份」就只对事件／NPC／柜子那几条渠道成立。
    """
    if count <= 0:
        return
    if int(ITEM_DEFINITIONS.get(item_id, {}).get('run_limit', 0)):
        state.item_grant_counts[item_id] = int(state.item_grant_counts.get(item_id, 0)) + count


def _limited_ids():
    return {key for key, definition in ITEM_DEFINITIONS.items() if definition.get('run_limit')}


def raw_legacy_awards(data):
    limited = _limited_ids()
    found = set()
    def inspect_item(item):
        key = item.get('definition_id')
        if key in limited and int(item.get('quantity', 1)) > 0:
            found.add(key)
    for item in data.get('inventory', []):
        inspect_item(item)
    for layer in (data, *data.get('layer_states', {}).values()):
        for entry in layer.get('world_items', []):
            inspect_item(entry.get('item', {}))
        for stock in layer.get('realm_features', {}).get('scavenge_stock', {}).values():
            found.update(limited.intersection(stock.get('remaining', [])))
    for entry in data.get('catalog', {}).values():
        found.update(limited.intersection(entry.get('drops_seen', [])))
    return found


def migrate_existing(state, *, legacy=False):
    limited = _limited_ids()
    found = set()
    for item in state.inventory:
        if item.definition_id in limited and item.quantity > 0:
            found.add(item.definition_id)
    for layer in (state, *state.layer_states.values()):
        for entry in layer.world_items:
            if entry.item.definition_id in limited and entry.item.quantity > 0:
                found.add(entry.item.definition_id)
    from dataclasses import asdict
    for layer in (state, *state.layer_states.values()):
        for stock in layer.realm_features.get('scavenge_stock', {}).values():
            bindings = stock.setdefault('legacy_limited_items', {}) if legacy else stock.get('legacy_limited_items', {})
            if legacy:
                for key in sorted(limited.intersection(stock.get('remaining', []))):
                    items = bindings.setdefault(key, [])
                    while len(items) < stock['remaining'].count(key):
                        items.append(asdict(state._make_item(key)))
            found.update(key for key, items in bindings.items() if items)
    for entry in state.catalog.values():
        found.update(limited.intersection(entry.get('drops_seen', [])))
    for key in found:
        state.item_grant_counts[key] = max(1, int(state.item_grant_counts.get(key, 0)))
