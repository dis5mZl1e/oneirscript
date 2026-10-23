"""Present position grammar through the shared equipment query interface.

Compilation remains pure; eligibility is evaluated against live context here.
Only sustained contracts enter global effect queries. Action/reaction payloads
must be executed by their respective plans, never leak into global passives.
"""
from __future__ import annotations

from .grammar import ACTIVE, PENDING, SATISFIED, UNFORMED, Ability, CompiledBoard, Sentence
from .positional import FormationResult
from .runtime import condition_matches
from ..i18n import tr


def condition_label(predicate):
    """Compatibility name for the shared, typed condition renderer."""
    from .sentence_prose import condition_text
    return condition_text(predicate)


def _sentence_body(row) -> str:
    """Compatibility wrapper for callers that still need the English phrase."""
    from .sentence_prose import _legacy_body
    return _legacy_body(row)


def sentence_text(row) -> str:
    """Return the exact prose used by previews, action labels and event records."""
    from .sentence_prose import render_sentence
    return render_sentence(row).text


def project(formation: FormationResult, state=None) -> CompiledBoard:
    compiled = CompiledBoard()
    unique = {}
    displayed_contracts = {}
    displayed_actions = {}
    allowed_contracts = {(c.instance_id, c.effect, c.condition) for c in formation.contracts}

    def displayed(row):
        if row.kind == "conditional" and row.alternatives:
            for child in row.alternatives:
                yield from displayed(child)
        else:
            yield row

    for row in (r for parent in formation.rows for r in displayed(parent)):
        if not row.voices:
            continue
        from .sentence_prose import render_sentence, readable_reason
        from .sentence_facts import build_equipment_contract
        rendered = render_sentence(row)
        text = rendered.text
        eligible = state is None or condition_matches(
            row.condition, state, cell=(state.player.x, state.player.y))
        status = (UNFORMED if row.status != "ready" else
                  PENDING if row.kind == "reaction" else
                  ACTIVE if eligible else SATISFIED)
        sentence = Sentence(
            f"row:{row.row}:{row.branch_key}" if row.branch_key else f"row:{row.row}",
            row.kind, text, status,
            reason=tr(readable_reason(row.reason)) if row.reason else "",
            instance_ids=row.instance_ids,
            fragments=rendered.legacy_fragments,
            fragment_sources=rendered.fragment_sources,
            details=rendered.details,
            source_rows=(row.row,),
            contract=build_equipment_contract(row, rendered),
        )
        abilities = []
        if row.status == "ready" and eligible:
            for contract in row.contracts:
                if (contract.instance_id, contract.effect, contract.condition) not in allowed_contracts:
                    continue
                key = (contract.instance_id, contract.effect)
                ability = Ability(contract.effect, contract.power, contract.secondary,
                                  contract.instance_id, contract.definition_id,
                                  "hold", sentence.sentence_id, text)
                previous = unique.get(key)
                if previous is None or previous.power < ability.power:
                    unique[key] = ability
                abilities.append(ability)
        sentence.abilities = tuple(abilities)
        if row.kind == "contract":
            contract_key = (
                row.source_id, row.instance_ids, row.opcode, repr(row.condition),
                row.target_kind, status, rendered.text, rendered.details,
                tuple((c.instance_id, c.definition_id, c.effect, c.power,
                       c.secondary, repr(c.condition)) for c in row.contracts),
            )
            previous = displayed_contracts.get(contract_key)
            if previous is not None:
                previous.source_rows = tuple(dict.fromkeys(previous.source_rows + (row.row,)))
                continue
            displayed_contracts[contract_key] = sentence
        elif row.kind in ("action", "reaction") and row.status == "ready":
            relation_key = tuple(
                (r.word_id, r.operator, r.head_id, r.donor_id, r.role_bindings,
                 r.source_row, r.target_row, r.word_cells)
                for r in row.relations
            )
            voice_key = tuple(sorted({
                (v.instance_id, v.definition_id, v.x, v.response.role,
                 v.response.kind, v.response.opcode, v.response.effect,
                 v.response.power, v.response.secondary, v.response.payload_type,
                 v.response.event, v.response.condition_kind, v.response.meaning)
                for v in row.voices
            }))
            action_key = (
                row.kind, row.source_id, row.instance_ids, row.opcode,
                row.operand_type, repr(row.condition), row.event, row.hurt_kind,
                row.target_kind, status, rendered.text, rendered.details,
                repr(row.action_profile), row.action_modes, row.consumes_source,
                row.action_modifiers, row.feedback_opcodes, relation_key, voice_key,
                tuple((c.instance_id, c.definition_id, c.effect, c.power,
                       c.secondary, repr(c.condition)) for c in row.contracts),
                tuple((s.instance_id, s.definition_id, s.value, s.channel)
                      for s in row.damage_sources),
            )
            previous = displayed_actions.get(action_key)
            if previous is not None:
                previous.source_rows = tuple(dict.fromkeys(previous.source_rows + (row.row,)))
                continue
            displayed_actions[action_key] = sentence
        compiled.sentences.append(sentence)
    compiled.abilities = list(unique.values())
    compiled.read_order = tuple(dict.fromkeys(v.instance_id for v in formation.voices))
    compiled.text = "\n".join(s.text for s in compiled.sentences)
    return compiled
