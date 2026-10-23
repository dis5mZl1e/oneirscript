"""Context-filtered action budgets. Compiling or planning never spends time."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import product
from typing import Any

from ..data.items import ITEM_DEFINITIONS
from .positional import FormationResult, Predicate, RowSentence
from .roles import DamageSource, damage_norm, is_weapon

CREDIT_SCALE = 1_000_000


@dataclass(frozen=True)
class ActionPlan:
    kind: str
    valid: bool
    rows: tuple[RowSentence, ...] = ()
    source_ids: tuple[str, ...] = ()
    damage_sources: tuple[DamageSource, ...] = ()
    damage_increment: float = 0.0
    base_time: float = 1.0
    segments: int = 1
    feedback_opcodes: tuple[str, ...] = ()
    innate: bool = False
    reason: str = ""
    semantic_signature: tuple = ()
    projectile_profile: tuple[tuple[str, object], ...] = ()
    primary_source_id: str = ""
    material_source_id: str = ""
    requires_target: bool = False
    repeat_source_ids: tuple[str,...] = ()
    # Physical emitters this action really fires: (instance_id, rounds per shot).
    # Modifiers, voices and sentence decorations never appear here.
    emitters: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class ActionChoice:
    key: str
    kind: str
    definition_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    rows: tuple[int, ...]
    members: tuple[tuple[int, str], ...] = ()


def _native_profile(row: RowSentence, kind: str) -> tuple:
    if kind != "fire" and not kind.startswith("spray_"):
        return ()
    prefix = "fire_" if kind == "fire" else "spray_"
    result = tuple((key[len(prefix):], value) for key, value in row.action_profile
                   if key.startswith(prefix))
    return result


def _emitter_instances(row) -> set[str]:
    """Physical weapons this row actually fires, ignoring decorative voices."""
    heads = {v.instance_id for v in row.voices
             if ITEM_DEFINITIONS.get(v.definition_id, {}).get('fire')}
    return heads or {row.source_id}


def _action_variants(formation, state, kind, target, cell):
    from .positional import _compile_row
    from .targets import target_matches
    eligible = tuple(row for row in formation.actions
                     if kind in row.action_modes and condition_matches(
                         row.condition, state, target=target, cell=cell)
                     and (cell is None or target_matches(row, state, target=target, cell=cell)))
    members = formation.alternative_members
    groups = {}
    for row in eligible:
        if row.branch_group:
            groups.setdefault(row.branch_group, []).append(row)
    candidates = []
    from ..core.firing_sources import magazine_spec
    for branches in groups.values():
        # Mechanically identical copies need no arbitrary permanent focus.
        unique = {}
        for row in branches:
            definition = next(v.definition_id for v in row.voices if v.instance_id == row.source_id)
            identity = (definition, row.action_profile, row.condition, row.feedback_opcodes)
            if magazine_spec(definition) is not None and len(_emitter_instances(row)) <= 1:
                # Each physical magazine is its own alternative; merging equal
                # specs would silently drain one weapon and leave the other full.
                # A coordinated row already names every head it fires, so its
                # alternative roots are the same combined action, not a choice.
                identity = (*identity, row.source_id)
            unique.setdefault(identity, row)
        candidates.append(tuple(unique.values()))
    normal = tuple(row for row in eligible if not row.branch_group)
    variants = []
    for selected in product(*candidates):
        blocked = members - {row.source_id for row in selected}
        rows = []
        for row in normal:
            if blocked.intersection(row.instance_ids):
                if row.source_id in blocked or row.relations:
                    continue
                row = _compile_row(row.row, tuple(v for v in row.voices if v.instance_id not in blocked))
                if row.status != 'ready' or kind not in row.action_modes:
                    continue
            rows.append(row)
        variants.append(tuple((*selected, *rows)))
    return tuple(variants)


def _choice_groups(formation, state, kind, target, cell):
    from ..core.firing_sources import magazine_spec
    choices = []
    for variant in _action_variants(formation, state, kind, target, cell):
        groups = {}
        for row in variant:
            # Different damage/time may share a shape. Pulse, status, material,
            # push and penetration specifications may not be silently substituted.
            profile = tuple((k, v) for k, v in _native_profile(row, kind)
                            if k not in ("damage", "time"))
            template = dict(row.action_profile).get("projectile_template", "直线弹体")
            origin = next((r.donor_id for r in row.relations if r.operator == 'origin'), '')
            repeated = any(r.operator == 'repetition' for r in row.relations)
            identity = (kind, template, tuple(sorted(profile)), origin, row.target_kind,repeated) if kind != 'melee' else (kind,)
            head_definition = next((v.definition_id for v in row.voices
                                    if v.instance_id == row.source_id), '')
            if (kind != 'melee' and magazine_spec(head_definition) is not None
                    and len(_emitter_instances(row)) <= 1):
                # Display grouping must not merge separate physical magazines,
                # but a coordinated row is one combined source with its own
                # per-head charge list.
                identity = (*identity, row.source_id)
            groups.setdefault(identity, []).append(row)
        for identity, rows in groups.items():
            members = tuple((row.row, row.branch_key) for row in rows)
            key = sha256(repr((formation.semantic_signature, identity, members)).encode("utf-8")).hexdigest()[:20]
            ids = tuple(dict.fromkeys(r.source_id for r in rows))
            definitions = tuple(dict.fromkeys(v.definition_id for r in rows for v in r.voices
                                             if v.instance_id == r.source_id))
            choices.append((ActionChoice(key, kind, definitions, ids,
                                         tuple(r.row for r in rows), members), tuple(rows)))
    return tuple({option.key: (option, rows) for option, rows in choices}.values())


def action_choices(formation: FormationResult, state, kind: str, *,
                   target=None, cell=None) -> tuple[ActionChoice, ...]:
    if not formation.valid:
        return ()
    return tuple(option for option, _ in _choice_groups(formation, state, kind, target, cell))


def action_effect_power(state: Any, effect: str, rows=()) -> int:
    """Combine live contracts with this action's words, once per physical source.

    Callers pass only the selected and validated rows. This never registers a
    continuous effect or changes the board, so unrelated actions cannot inherit it.
    """
    from .aggregation import EFFECT_DECAY, diminish_int

    sources = {}
    for power, iid in state.equipment.effect_sources(effect):
        sources[iid] = max(power, sources.get(iid, 0))
    for row in rows:
        for iid, modifier_effect, power in row.action_modifiers:
            if modifier_effect == effect:
                sources[iid] = max(power, sources.get(iid, 0))
    return diminish_int(((power, iid) for iid, power in sources.items()),
                        resonating=getattr(state, 'resonance_turns', 0) > 0,
                        ratio=EFFECT_DECAY.get(effect, .5))


def condition_value(predicate: Predicate | None, state: Any, *,
                    target=None, cell=None, event: str = "") -> bool | None:
    if predicate is None:
        return True
    if predicate.kind == 'all':
        values = tuple(condition_value(child, state, target=target, cell=cell, event=event)
                       for child in predicate.children)
        result = None if not values or None in values else all(values)
    elif predicate.kind == "event":
        if event == 'settled':
            from .root_facts import settled_event_value
            result = settled_event_value(state, predicate.event)
        elif predicate.negated:
            # A different event, resource failure or preview does not prove
            # that this event will never occur later in the same root action.
            result = None
        else:
            result = predicate.event == event if event and predicate.event else None
    elif predicate.kind == "lit":
        point = cell or (state.player.x, state.player.y)
        from ..core.vision.glow import lit
        # Compilation cannot query equipment-derived sight, which recompiles this condition.
        result = lit(state, *point) and state._has_line_of_sight(state.player.x, state.player.y, *point)
    elif predicate.kind == "attached":
        result = any(
            amount > 0 for amount in getattr(target, "portent_attach", {}).values())
        if target is None:
            result = None
    elif predicate.kind == "low_imagination":
        result = state.imagination <= predicate.threshold
    elif predicate.kind == "empty_imagination":
        result = state.imagination <= 0
    elif predicate.kind == "conductive":
        if cell is None and target is not None:
            cell = (target.x, target.y)
        result = bool(state._conductive_cell(state.cell(*cell))) if cell is not None and state.inside_board(*cell) else None
    elif predicate.kind == "flammable":
        # 2026-10-14 条件位差异化：作用位置有可燃材料（燃油/植物/可燃墙体等，
        # 判据与点火同源）。没有瞄准格时落到玩家脚下（与 lit 同口径）。
        if cell is None and target is not None:
            cell = (target.x, target.y)
        if cell is None:
            cell = (state.player.x, state.player.y)
        result = bool(state._cell_is_flammable(state.cell(*cell))) \
            if state.inside_board(*cell) else None
    elif predicate.kind == "wet":
        # 作用位置有液体（液体量 > 0）。缺省落玩家脚下（与 lit 同口径）。
        if cell is None and target is not None:
            cell = (target.x, target.y)
        if cell is None:
            cell = (state.player.x, state.player.y)
        result = bool(state.cell(*cell).liquid) \
            if state.inside_board(*cell) else None
    elif predicate.kind == "marked":
        # 目标带着折射印记（跳弹命中留下的 refract_marks）。
        if target is None:
            result = None
        else:
            marks = getattr(state, "refract_marks", {})
            result = getattr(target, "id", None) in marks
    else:
        result = None
    return (not result if predicate.negated else result) if result is not None else None


def condition_matches(predicate: Predicate | None, state: Any, *,
                      target=None, cell=None, event: str = "") -> bool:
    return condition_value(predicate, state, target=target, cell=cell, event=event) is True


def plan_action(formation: FormationResult, state: Any, kind: str, *,
                target=None, cell=None, choice: str | None = None) -> ActionPlan:
    if not formation.valid:
        return ActionPlan(kind, False, reason="盘面物理无效",
                          semantic_signature=formation.semantic_signature)
    if kind == 'fire' and choice == 'legacy_basic_fire':
        from ..core.firing_sources import legacy_basic_view
        view = legacy_basic_view(state)
        available = view is not None and view.magazine > 0
        return ActionPlan(kind,available,innate=True,
                          reason='' if available else '旧档继承的基础发射已经用完，请先换弹。',
                          semantic_signature=formation.semantic_signature)
    if kind == 'fire' and choice == 'aggregate':
        available = int(getattr(state,'projectile_charges',0) or 0) > 0
        return ActionPlan(kind,available,innate=True,
                          reason='' if available else '聚合弹库存不足。',
                          semantic_signature=formation.semantic_signature)
    options = _choice_groups(formation, state, kind, target, cell)
    if choice is not None:
        selected = next((rows for option, rows in options if option.key == choice), None)
        if selected is None:
            return ActionPlan(kind, False, reason="本次动作选项已经失效")
        rows = selected
    elif len(options) > 1:
        return ActionPlan(kind, False, reason=("请选择本次动作的分支" if kind == 'melee'
                                             else "请选择本次动作的发射方式"))
    else:
        rows = options[0][1] if options else ()
    if not rows:
        if any(row.target_kind and kind in row.action_modes and condition_matches(
               row.condition, state, target=target, cell=cell) for row in formation.actions):
            return ActionPlan(kind, False, reason='目标不符合定向语句。', requires_target=True)
        innate = kind == "melee" or (kind == "fire" and
                 state.projectile_charges > 0)
        return ActionPlan(kind, innate, innate=innate,
                          reason="" if innate else "没有成立的对应动作句",
                          semantic_signature=formation.semantic_signature)
    sources: dict[str, DamageSource] = {}
    actual_attackers: dict[str, dict] = {}
    for row in rows:
        for source in row.damage_sources:
            if kind == "melee":
                sources[source.instance_id] = source
            elif kind == "fire":
                definition = ITEM_DEFINITIONS[source.definition_id]
                force = any(iid == source.instance_id and effect in ('throw_master', 'cut')
                            for iid, effect, _ in row.action_modifiers)
                value = source.value if force else int(definition.get("fire", {}).get("damage", 0) or 0)
                if not force and definition.get("effect") == "weapon_damage":
                    value += int(definition.get("power", 0) or 0)
                if value:
                    sources[source.instance_id] = DamageSource(
                        source.instance_id, source.definition_id, value)
        for voice in row.voices:
            definition = ITEM_DEFINITIONS.get(voice.definition_id, {})
            if voice.response.role in ('source', 'verb') and is_weapon(definition):
                actual_attackers[voice.instance_id] = definition
                if kind == "fire" and voice.instance_id not in sources:
                    value = int(definition.get("fire", {}).get("damage", 0) or 0)
                    if value:
                        sources[voice.instance_id] = DamageSource(
                            voice.instance_id, voice.definition_id, value)
    times = {}
    segment_counts = [1]
    for iid, definition in actual_attackers.items():
        if kind == "melee":
            profile = definition.get("melee", {})
            times[iid] = float(profile.get("time", 1.0))
            segment_counts.append(max(1, int(profile.get("segments", 1))))
        elif kind == "fire":
            times[iid] = float(definition.get("fire", {}).get("time", 1.0))
        else:
            times[iid] = 1.0
    ids = tuple(dict.fromkeys((*actual_attackers, *sources)))
    if not ids:
        ids = tuple(dict.fromkeys(row.source_id for row in rows))
    feedback = tuple(dict.fromkeys(op for row in rows for op in row.feedback_opcodes))
    # Manner is local to these selected rows. A physical source already granting
    # the same live global contract must not be counted again here.
    live_swift = {contract.instance_id for contract in formation.contracts
                  if contract.effect == 'swift_strike' and condition_matches(
                      contract.condition, state, cell=(state.player.x, state.player.y))}
    local_swift = {}
    for row in rows:
        for iid, effect, power in row.action_modifiers:
            if effect == 'swift_strike' and iid not in live_swift:
                head_modifiers = local_swift.setdefault(row.source_id, {})
                head_modifiers[iid] = max(power, head_modifiers.get(iid, 0))
    from .aggregation import diminish
    for head_id, modifiers in local_swift.items():
        if head_id in times:
            bonus = .1 * diminish((power, iid) for iid, power in modifiers.items())
            times[head_id] = max(.2, times[head_id]-bonus)
    # Only a head that authors damage actually emits a projectile. Voices that
    # merely colour the sentence and modifiers never count as another shot.
    emitters: tuple[tuple[str, int], ...] = ()
    if kind == 'fire':
        heads = tuple(actual_attackers)
        if not heads and rows:
            head = rows[0].source_id
            definition = next((v.definition_id for v in rows[0].voices
                               if v.instance_id == head), '')
            if ITEM_DEFINITIONS.get(definition, {}).get('fire'):
                heads = (head,)
        emitters = tuple((head, 1) for head in heads if head)
    result = ActionPlan(
        kind=kind, valid=True, rows=rows, source_ids=ids,
        damage_sources=tuple(sources.values()), damage_increment=damage_norm(sources.values()),
        base_time=max(times.values(), default=1.0), segments=max(segment_counts),
        feedback_opcodes=feedback, semantic_signature=formation.semantic_signature,
        projectile_profile=_native_profile(rows[0], kind),
        primary_source_id=rows[0].source_id,
        material_source_id=next((relation.donor_id for row in rows for relation in row.relations
                                 if relation.operator == 'origin'), ''),
        requires_target=any(row.target_kind or any(v.response.opcode in ('hospital_pathogen','hospital_adjacent')
                            for v in row.voices) for row in rows),
        repeat_source_ids=tuple(dict.fromkeys(relation.head_id for row in rows for relation in row.relations
                                             if relation.operator == 'repetition')),
        emitters=emitters,
    )
    if result.requires_target and cell is None:
        from dataclasses import replace
        return replace(result, valid=False, reason='请选择定向语句的目标。')
    return result


def claim_damage_bonus(state: Any, plan: ActionPlan,
                       channel: str = "weapon_damage") -> int:
    """Claim the one-action integer budget after a real hit, never for preview."""
    if not plan.valid or plan.damage_increment <= 0:
        return 0
    if channel != "weapon_damage":
        raise ValueError("This action only carries the weapon damage channel")
    epoch = state.action_seq
    if getattr(state, "_equipment_claim_epoch", None) != epoch:
        state._equipment_claim_epoch = epoch
        state._equipment_claimed_channels = set()
    if channel in state._equipment_claimed_channels:
        return 0
    state._equipment_claimed_channels.add(channel)
    credit = int(state.equipment_damage_credit.get(channel, 0))
    amount, remainder = divmod(
        credit + round(plan.damage_increment * CREDIT_SCALE), CREDIT_SCALE)
    state.equipment_damage_credit[channel] = remainder
    return amount
