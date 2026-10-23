"""Shared semantic contract for the three bilingual sentence pipelines.

docs/261018方案合集.md §15 first batch: the equipment board, map tamper and
dialogue tamper generators must share identity, relation, operation, scope,
effect and certainty facts. Language output may add grammar only; it must not
add a capability, consume randomness or reverse-extract numbers from prose.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping

DOMAINS = ("equipment", "map_tamper", "dialogue_tamper")
CERTAINTIES = ("certain", "conditional", "possible", "display")
LANGUAGES = ("zh", "en")
SYNTAXES = ("zh", "en")


def _frozen(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True)
class SentenceFact:
    """One language-independent fact consumed by all three generators."""

    domain: str
    fact_id: str
    operation: str
    certainty: str = "certain"
    relation: str = ""
    targets: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    effects: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    context: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.domain not in DOMAINS:
            raise ValueError(f"unknown fact domain: {self.domain}")
        if not str(self.fact_id or "").strip():
            raise ValueError("fact_id is required")
        if not str(self.operation or "").strip():
            raise ValueError(f"{self.fact_id}: operation is required")
        if self.certainty not in CERTAINTIES:
            raise ValueError(f"{self.fact_id}: unknown certainty {self.certainty}")
        object.__setattr__(self, "targets", tuple(str(v) for v in self.targets))
        object.__setattr__(self, "sources", tuple(str(v) for v in self.sources))
        object.__setattr__(self, "scope", tuple(str(v) for v in self.scope))
        object.__setattr__(self, "effects", _frozen(self.effects))
        object.__setattr__(self, "context", _frozen(self.context))

    @property
    def source_ids(self) -> frozenset[str]:
        return frozenset(self.sources) | frozenset(self.targets) | frozenset(self.scope)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain, "fact_id": self.fact_id,
            "operation": self.operation, "certainty": self.certainty,
            "relation": self.relation, "targets": list(self.targets),
            "sources": list(self.sources), "scope": list(self.scope),
            "effects": dict(self.effects), "context": dict(self.context),
        }


@dataclass(frozen=True)
class SemanticFragment:
    """A visible span mapped back to a fact; grammar spans own no capability."""

    text: str
    role: str
    source_ids: tuple[str, ...] = ()
    operation: str = ""
    editable: bool = False
    grammar_only: bool = False
    certainty: str = "certain"
    anchor_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.text or ""):
            raise ValueError("fragment text is required")
        if not str(self.role or "").strip():
            raise ValueError("fragment role is required")
        if self.certainty not in CERTAINTIES:
            raise ValueError(f"unknown fragment certainty {self.certainty}")
        object.__setattr__(self, "source_ids", tuple(str(v) for v in self.source_ids))
        object.__setattr__(self, "anchor_ids", tuple(str(v) for v in self.anchor_ids))
        if self.grammar_only and self.source_ids:
            raise ValueError("grammar-only fragment cannot own semantic sources")
        if self.editable and not str(self.operation or "").strip():
            raise ValueError("editable fragment requires its operation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text, "role": self.role,
            "source_ids": list(self.source_ids), "operation": self.operation,
            "editable": self.editable, "grammar_only": self.grammar_only,
            "certainty": self.certainty, "anchor_ids": list(self.anchor_ids),
        }


@dataclass(frozen=True)
class SentenceOutput:
    """Complete prose plus provenance, interactive spans and exact summary."""

    facts: tuple[SentenceFact, ...]
    text: str
    language: str
    syntax: str
    fragments: tuple[SemanticFragment, ...] = ()
    summary: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    status: str = "ok"
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts", tuple(self.facts))
        object.__setattr__(self, "fragments", tuple(self.fragments))
        object.__setattr__(self, "summary", _frozen(self.summary))
        object.__setattr__(self, "reasons", tuple(str(v) for v in self.reasons))

    def validate(self) -> "SentenceOutput":
        if self.language not in LANGUAGES:
            raise ValueError(f"unsupported language: {self.language}")
        if self.syntax not in SYNTAXES:
            raise ValueError(f"unsupported syntax: {self.syntax}")
        if not str(self.text or "").strip():
            raise ValueError("complete text is required")
        if not self.facts:
            raise ValueError("at least one semantic fact is required")
        fact_ids = [fact.fact_id for fact in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("duplicate fact ids")
        known = set().union(*(fact.source_ids for fact in self.facts))
        operations = {fact.operation for fact in self.facts}
        effect_keys = set().union(*(fact.effects.keys() for fact in self.facts)) if self.facts else set()
        for fragment in self.fragments:
            unknown = set(fragment.source_ids) - known
            if unknown:
                raise ValueError(f"fragment source is not in facts: {sorted(unknown)}")
            if fragment.operation and fragment.operation not in operations:
                raise ValueError(f"fragment operation is not in facts: {fragment.operation}")
        for key in self.summary:
            if key not in effect_keys:
                raise ValueError(f"summary key not present in facts: {key}")
        if self.status != "ok" and not self.reasons:
            raise ValueError("non-ok output requires a concrete reason")
        return self

    @property
    def grammar_only_fragments(self) -> tuple[SemanticFragment, ...]:
        return tuple(fragment for fragment in self.fragments if fragment.grammar_only)

    def same_facts(self, other: "SentenceOutput") -> bool:
        return self.facts == other.facts

    def with_language(self, language: str, *, text: str,
                      fragments: tuple[SemanticFragment, ...] = (),
                      syntax: str | None = None) -> "SentenceOutput":
        """Re-render only language/wording; facts and summary stay identical."""
        if language not in LANGUAGES:
            raise ValueError(f"unsupported language: {language}")
        return replace(self, language=language, syntax=syntax or self.syntax,
                       text=text, fragments=tuple(fragments)).validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": [fact.to_dict() for fact in self.facts],
            "text": self.text, "language": self.language, "syntax": self.syntax,
            "fragments": [fragment.to_dict() for fragment in self.fragments],
            "summary": dict(self.summary), "status": self.status,
            "reasons": list(self.reasons),
        }


def build_output(facts, *, text: str, language: str, syntax: str,
                 fragments=(), summary: Mapping[str, Any] | None = None,
                 status: str = "ok", reasons=()) -> SentenceOutput:
    return SentenceOutput(tuple(facts), text, language, syntax, tuple(fragments),
                          _frozen(summary), status, tuple(reasons)).validate()


def fact_identity(fact: SentenceFact) -> tuple:
    """Stable, hashable identity used before any language rendering."""
    return (fact.domain, fact.fact_id, fact.operation, fact.certainty,
            fact.relation, fact.targets, fact.sources, fact.scope,
            tuple(sorted(fact.effects.items())), tuple(sorted(fact.context.items())))
