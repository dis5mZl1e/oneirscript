"""Pure birth-draft validation and budgeting; no UI or world side effects."""
from __future__ import annotations

from ..data.dream_types import (
    APTITUDES, DREAM_BUDGET, IDENTITIES, REFUND_LIMIT, TIER_PRICES,
)


def normalize_choice(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    identity = source.get('identity')
    if not isinstance(identity, str) or identity not in IDENTITIES:
        identity = 'ordinary'
    raw_tiers = source.get('aptitudes')
    raw_tiers = raw_tiers if isinstance(raw_tiers, dict) else {}
    tiers = {}
    for key in APTITUDES:
        try:
            value = int(raw_tiers.get(key, 2))
        except (ValueError, TypeError, OverflowError):
            value = 2
        tiers[key] = min(4, max(0, value))
    return {'identity': identity, 'aptitudes': tiers}


def budget_breakdown(choice) -> dict:
    clean = normalize_choice(choice)
    prices = [TIER_PRICES[tier] for tier in clean['aptitudes'].values()]
    nominal_refund = -sum(price for price in prices if price < 0)
    refund = min(REFUND_LIMIT, nominal_refund)
    upgrades = sum(price for price in prices if price > 0)
    identity_cost = IDENTITIES[clean['identity']]['cost']
    spent = identity_cost + upgrades - refund
    return {'total': DREAM_BUDGET, 'identity': identity_cost, 'upgrades': upgrades,
            'nominal_refund': nominal_refund, 'refund': refund,
            'spent': spent, 'remaining': DREAM_BUDGET - spent}


def validate_choice(choice) -> list[str]:
    if not isinstance(choice, dict):
        return ['identity_required']
    identity = choice.get('identity')
    errors = []
    if not isinstance(identity, str) or identity not in IDENTITIES:
        errors.append('identity_required')
    tiers = choice.get('aptitudes')
    if not isinstance(tiers, dict) or any(
        type(tiers.get(key)) is not int or not 0 <= tiers[key] <= 4
        for key in APTITUDES
    ):
        errors.append('invalid_aptitudes')
    if budget_breakdown(choice)['remaining'] < 0:
        errors.append('over_budget')
    return errors


def default_choice() -> dict:
    boosted = {'mind', 'lucidity', 'imagination', 'melee', 'shooting', 'conceive'}
    return {'identity': 'ordinary',
            'aptitudes': {key: 3 if key in boosted else 2 for key in APTITUDES}}


def apply_birth_choice(state, choice) -> None:
    """Apply once at birth; loading restores the saved contribution directly."""
    errors = validate_choice(choice)
    if errors:
        raise ValueError(', '.join(errors))
    if state.dream_type_choice:
        raise ValueError('birth_choice_already_applied')
    clean = normalize_choice(choice)
    state.dream_type_choice = clean
    for key, values in (
        ('mind', (0.8, 0.9, 1.0, 1.05, 1.12)),
        ('lucidity', (0.8, 0.9, 1.0, 1.05, 1.12)),
        ('imagination', (0.8, 0.9, 1.0, 1.08, 1.16)),
    ):
        cap = max(1, int(getattr(state, 'max_' + key) * values[clean['aptitudes'][key]] + 0.5))
        setattr(state, 'max_' + key, cap)
        setattr(state, key, cap)
    values = (1.15, 1.07, 1.0, 0.95, 0.90)
    state.dream_type_mods = {key: values[clean['aptitudes'][key]]
                           for key in ('melee', 'shooting', 'throwing', 'conceive', 'materials')}
    state.identity_state = {'cooldowns': {}}


def random_choice(rng) -> dict:
    # Select once; expensive identities must never be rejected with a draft.
    identity = rng.choice(tuple(IDENTITIES))
    for _ in range(128):
        choice = {'identity': identity, 'aptitudes': dict(zip(APTITUDES,
            rng.choices(range(5), weights=(1, 2, 6, 4, 2), k=len(APTITUDES))))}
        if budget_breakdown(choice)['remaining'] >= 0:
            return choice
    # Bounded fallback remains valid for the same identity, without hidden
    # changes to its price or generating an unbounded retry loop.
    choice = {'identity': identity, 'aptitudes': {key: 2 for key in APTITUDES}}
    keys = list(APTITUDES)
    rng.shuffle(keys)
    for key in keys:
        choice['aptitudes'][key] = 3
        if budget_breakdown(choice)['remaining'] < 0:
            choice['aptitudes'][key] = 2
    return choice
