"""Exact provenance attached to string-compatible stat explanations."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRef:
    kind: str
    identifier: str


class SourceText(str):
    def __new__(cls, text, references=()):
        value = super().__new__(cls, text)
        value.references = tuple(references)
        return value


def source_text(text, kind, identifier):
    return SourceText(text, (SourceRef(kind, str(identifier)),))


def references(sources):
    return tuple(dict.fromkeys(ref for source in sources for ref in getattr(source, 'references', ())))
