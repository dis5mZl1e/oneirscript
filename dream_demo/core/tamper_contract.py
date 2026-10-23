"""§15 map-tamper adapter: WorldSentence preview -> shared SentenceOutput."""
from __future__ import annotations

from ..i18n import get_language
from .sentence_contract import SemanticFragment, SentenceFact, build_output


def slot_fact_id(slot) -> str:
    if getattr(slot, "enemy", None) is not None:
        identity = getattr(slot.enemy, "id", None) or slot.enemy
        return "anomaly:" + str(identity)
    if getattr(slot, "region_members", ()):
        return f"region:{slot.region_kind}:{slot.x},{slot.y}"
    return f"{slot.category}:{slot.x},{slot.y}"


def build_tamper_contract(sentence, word_id: str, slot_index: int, *,
                          condition_ids=(), replacement: str = "",
                          effect: str = "", scope: tuple[str, ...] = ()):
    """Create a validated contract from the already-computed preview strings."""
    if sentence is None or not getattr(sentence, "slots", None):
        return None
    if not (0 <= int(slot_index) < len(sentence.slots)):
        return None
    slot = sentence.slots[int(slot_index)]
    target = slot_fact_id(slot)
    conditions = tuple(str(item) for item in condition_ids or ())
    member_scope = tuple(f"{x},{y}" for x, y in getattr(slot, "region_members", ()) or ())
    effects = {"word": str(word_id), "conditions": "+".join(conditions) or "none"}
    if getattr(slot, "region_amount", 0):
        effects["amount"] = round(float(slot.region_amount), 3)
    fact = SentenceFact(
        domain="map_tamper",
        fact_id=f"tamper:{word_id}:{slot_index}",
        operation=str(word_id),
        certainty=("conditional" if conditions else "certain"),
        relation=str(slot.category),
        targets=(target,), sources=(target,),
        scope=(str(slot.category),) + tuple(scope) + member_scope,
        effects=effects,
        context={"category": slot.category, "clipped": bool(getattr(slot, "region_clipped", False))},
    )
    fragments = [SemanticFragment(str(replacement or sentence.text), "result",
                                  source_ids=(target,), operation=str(word_id), editable=True)]
    if effect:
        fragments.append(SemanticFragment(str(effect), "effect", source_ids=(target,)))
    return build_output(
        (fact,), text=str(replacement or sentence.text), language=get_language(),
        syntax="zh", fragments=tuple(fragments),
        summary={"word": str(word_id), "conditions": effects["conditions"]},
    )
