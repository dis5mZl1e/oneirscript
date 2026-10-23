"""Stable NPC shelves and free-claim quotas, independent of paid offers and quests."""
import random
from types import SimpleNamespace

from ..data.ids import npc_option_id, stable_seed
from ..i18n import tr


def is_trade(option):
    return bool(option.get('cost')) and not any(option.get(key) for key in (
        'accept_quest', 'complete_quest', 'hospital_scene', 'enter_realm',
        'negotiate', 'puzzle', 'deep_dialogue', 'scene_command'))


def is_free_claim(option):
    return bool(option.get('gain')) and not option.get('cost') and not any(
        option.get(key) for key in ('accept_quest', 'complete_quest', 'hospital_scene',
                                   'enter_realm', 'deep_dialogue', 'scene_command'))


def limited_shelf(npc):
    from .content import draw_npc_options, npc_definition, npc_trade_key

    definition = npc_definition(npc)
    table = definition.get('options', ())
    kind = getattr(npc, 'npc_kind', '') or npc.id
    rng = random.Random(stable_seed(npc_trade_key(npc) + '|offers'))
    saved = tuple(getattr(npc, 'npc_options', ()) or ())
    if not saved:
        return draw_npc_options(kind, rng)
    trades = sorted({i for i in saved if isinstance(i, int) and 0 <= i < len(table)
                     and is_trade(table[i])})
    if len(trades) > 3:
        trades = rng.sample(trades, 3)
    others = {i for i, option in enumerate(table) if not is_trade(option)}
    return tuple(sorted(others | set(trades)))


def free_claim_limit(npc):
    from .content import npc_definition

    return max(1, min(2, int(npc_definition(npc).get('free_claim_limit', 2))))


def gift_claimed(state, npc, group):
    from .content import npc_definition, npc_option_key, npc_trade_key
    key = npc_trade_key(npc)
    claims = set(state.npc_free_claims.get(key, ())) | set(state.npc_traded_options.get(key, ()))
    if 'legacy.gift.' + group in claims:
        return True
    return any(option.get('gift_set') == group and is_free_claim(option)
               and npc_option_key(npc, option) in claims
               for option in npc_definition(npc).get('options', ()))


def original_option(npc, option):
    from .content import npc_definition, npc_option_key

    wanted = npc_option_key(npc, option)
    return next((entry for entry in npc_definition(npc).get('options', ())
                 if npc_option_key(npc, entry) == wanted), option)


def free_claim_refusal(state, npc, option):
    from .content import npc_option_key, npc_trade_key

    if option.get('gift_dialogue') or not is_free_claim(original_option(npc, option)):
        return ''
    claims = state.npc_free_claims.get(npc_trade_key(npc), ())
    if npc_option_key(npc, option) in claims:
        return tr('这份赠品已经领过了。')
    if len(claims) >= free_claim_limit(npc):
        return tr('这位稳定意识的免费赠品已经领完了，仍可交易或交谈。')
    return ''


def record_free_claim(state, npc, option):
    from .content import npc_option_key, npc_trade_key

    if is_free_claim(original_option(npc, option)):
        state.npc_free_claims.setdefault(npc_trade_key(npc), []).append(npc_option_key(npc, option))


def gift_dialogue_option(npc, option):
    """Keep authored conversation after its accompanying free reward is spent."""
    from .content import npc_option_key
    view = dict(option, option_id=npc_option_key(npc, option), gift_dialogue=True)
    view.pop('gain', None)
    view.pop('gift_set', None)
    view['show_if'] = {key: value for key, value in (option.get('show_if') or {}).items()
                       if key != 'gift_available'}
    return view


def free_claims_remaining(state, npc):
    from .content import npc_definition, npc_trade_key, npc_option_key
    left = max(0, free_claim_limit(npc) - len(state.npc_free_claims.get(npc_trade_key(npc), ())))
    choices = {option.get('gift_set') or npc_option_key(npc, option)
               for option in npc_definition(npc).get('options', ())
               if is_free_claim(option) and not free_claim_refusal(state, npc, option)
               and not (option.get('gift_set') and gift_claimed(state, npc, option['gift_set']))}
    return min(left, len(choices))


def migrate_offer_limits(state, *, legacy_free_claims=False):
    """Normalize current/history shelves and old claims without replaying settlement."""
    from .content import NPC_DEFINITIONS, npc_definition, npc_option_key, npc_trade_key

    snapshots = [state, *state.layer_states.values()]
    for snapshot in snapshots:
        for event in snapshot.events:
            if event.event_id.split('@', 1)[0] == 'event.scrapper_case':
                event.uses_left = min(event.uses_left, 2)
                if event.uses_left <= 0:
                    event.resolved = True
        for npc in snapshot.enemies:
            if not npc_definition(npc):
                continue
            npc.npc_options = limited_shelf(npc)
            actor = state.world_ledger.actor(npc.actor_uid)
            if actor is not None:
                actor.shelf = npc.npc_options
            if legacy_free_claims:
                _migrate_free_claims(state, npc)
    for actor in state.world_ledger.actors.values():
        if actor.npc_kind not in NPC_DEFINITIONS:
            continue
        npc = SimpleNamespace(id=actor.actor_uid, actor_uid=actor.actor_uid,
                              npc_kind=actor.npc_kind, npc_options=actor.shelf)
        actor.shelf = limited_shelf(npc)
        if legacy_free_claims:
            _migrate_free_claims(state, npc)


def _migrate_free_claims(state, npc):
    from .content import npc_definition, npc_option_key, npc_trade_key

    key = npc_trade_key(npc)
    claims = set(state.npc_free_claims.get(key, ()))
    groups = set()
    recorded_groups = set()
    table = npc_definition(npc).get('options', ())
    attributed = {fact.get('cause_uid') for fact in state.world_ledger.facts
                  if fact.get('source_kind') == 'npc_offer' and fact.get('kind') == 'transfer'}
    own_facts = {fact.get('cause_uid') for fact in state.world_ledger.facts
                 if fact.get('source_kind') == 'npc_offer' and fact.get('kind') == 'transfer'
                 and fact.get('actor_uid') == key}
    attributed_groups = {option.get('gift_set') for option in table
                         if npc_option_key(npc, option) in attributed and option.get('gift_set')}
    for option in table:
        option_id = npc_option_key(npc, option)
        if option.get('gift_set') and option_id in own_facts:
            traded = state.npc_traded_options.setdefault(key, [])
            if option_id not in traded:
                traded.append(option_id)
            recorded_groups.add(option['gift_set'])
        if not is_free_claim(option):
            continue
        if option_id in state.npc_traded_options.get(key, ()):
            claims.add(option_id)
            if option.get('gift_set'):
                recorded_groups.add(option['gift_set'])
        elif (option.get('gift_set') and state.gift_claims.get(option['gift_set'])
              and option['gift_set'] not in attributed_groups):
            groups.add(option['gift_set'])
    claims.update('legacy.gift.' + group for group in groups - recorded_groups)
    if claims:
        state.npc_free_claims[key] = sorted(claims)
