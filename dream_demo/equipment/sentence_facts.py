"""§15 adapter: equipment rows -> shared SentenceFact/SentenceOutput contract."""
from __future__ import annotations

from ..i18n import get_language
from ..core.sentence_contract import SemanticFragment, SentenceFact, build_output


def build_equipment_contract(row, rendered):
    """Build/validate the language-independent facts and visible spans for one row."""
    if row.status != "ready" or not getattr(row, "voices", ()):
        return None
    effects = {}
    for contract in getattr(row, "contracts", ()):
        key = str(contract.effect or "effect")
        effects[f"power:{key}"] = int(contract.power)
        if getattr(contract, "secondary", 0):
            effects[f"secondary:{key}"] = int(contract.secondary)
    if not effects:
        effects["operation:" + str(row.opcode or row.kind)] = 1
    fact = SentenceFact(
        domain="equipment",
        fact_id=f"row:{row.row}:{getattr(row, 'branch_key', '')}",
        operation=str(row.opcode or row.kind or "sentence"),
        certainty=("conditional" if row.condition is not None or row.kind == "reaction"
                   else "certain"),
        relation=str(row.kind or ""),
        targets=tuple(dict.fromkeys(v.instance_id for v in row.voices
                                   if v.response.role in ("target", "object", "payload"))),
        sources=tuple(dict.fromkeys(v.instance_id for v in row.voices)),
        scope=((str(row.target_kind),) if getattr(row, "target_kind", "") else ()),
        effects=effects,
        context={"kind": row.kind, "status": row.status,
                 "condition": repr(row.condition) if row.condition is not None else ""},
    )
    known = fact.source_ids
    fragments = []
    source_groups = tuple(getattr(rendered, "fragment_sources", ()) or ())
    for index, part in enumerate(getattr(rendered, "fragments", ()) or ()):
        text, role = part.text, part.role
        sources = tuple(getattr(part, "source_ids", ()) or ())
        if not sources and index < len(source_groups):
            sources = tuple(source_groups[index])
        sources = tuple(source for source in sources if source in known)
        grammar_only = role == "filler" and not sources
        fragments.append(SemanticFragment(
            text=str(text), role=str(role), source_ids=sources,
            grammar_only=grammar_only,
        ))
    return build_output(
        (fact,), text=str(rendered.text), language=get_language(), syntax="zh",
        fragments=tuple(fragments), summary=effects,
    )
