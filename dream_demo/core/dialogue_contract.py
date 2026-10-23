"""§15 dialogue-tamper adapter: TamperPreview -> shared SentenceOutput."""
from __future__ import annotations

from ..i18n import tr
from .sentence_contract import SemanticFragment, SentenceFact, build_output


def build_dialogue_contract(request, transition, definition, *,
                            before_text: str, after_text: str,
                            imagination_cost: int, chaos_delta: int,
                            chaos_after: int, risk_tier: str,
                            available: bool, reason: str = "",
                            effect_note: str = "", language: str = "zh"):
    """Build/validate the language-independent dialogue-tamper contract."""
    if request is None or transition is None or definition is None:
        return None
    target = request.target.record_key(request.text_id)
    fact = SentenceFact(
        domain="dialogue_tamper",
        fact_id=f"{request.text_id}:{transition.transition_id}",
        operation=str(transition.operation),
        certainty="certain",
        relation=str(getattr(definition, "region", "")),
        targets=(target,),
        sources=(str(request.target.definition_id),),
        scope=(str(request.text_id),),
        effects={
            "imagination": int(imagination_cost),
            "chaos": int(chaos_delta),
            "risk": str(risk_tier),
        },
        context={
            "text_id": str(request.text_id),
            "from_variant": str(transition.from_variant),
            "to_variant": str(transition.to_variant),
            "slot_id": str(transition.slot_id),
            "word_id": str(transition.word_id or ""),
        },
    )
    fragments = [SemanticFragment(str(after_text), "result",
                                  source_ids=(target,),
                                  operation=str(transition.operation),
                                  editable=True)] if after_text else []
    if effect_note:
        fragments.append(SemanticFragment(str(effect_note), "effect",
                                          source_ids=(target,)))
    status = "ok" if available else "blocked"
    summary = {"imagination": int(imagination_cost), "chaos": int(chaos_delta),
               "risk": str(risk_tier)}
    return build_output(
        (fact,), text=str(after_text or before_text), language=str(language),
        syntax="zh", fragments=tuple(fragments), summary=summary,
        status=status, reasons=(str(reason or "unavailable"),) if not available else (),
    )
