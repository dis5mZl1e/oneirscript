"""Bounded, non-destructive material mutation history for independent readers."""
from collections import deque
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class MutationBatch:
    generation: str
    version: int
    changes: tuple
    reset: bool = False

    @property
    def cursor(self):
        return (self.generation, self.version)

    @property
    def positions(self):
        return frozenset(position for position, _ in self.changes)

    @property
    def fields(self):
        return frozenset(field for _, field in self.changes)


class MutationJournal:
    def __init__(self, capacity=65536):
        if capacity < 1:
            raise ValueError("journal capacity must be positive")
        self.generation = uuid4().hex
        self.version = 0
        self._records = deque(maxlen=capacity)
        # Last revisions outlive bounded records; readers never drain these.
        self._field_versions = {}

    @property
    def cursor(self):
        return (self.generation, self.version)

    def record(self, position, field):
        self.version += 1
        self._field_versions[field] = self.version
        self._records.append((self.version, position, field))

    def dependency_cursor(self, fields):
        """Generation and latest relevant revision, independent of retention.

        Cost depends only on the fixed dependency set, never map/history size.
        A whole Cell replacement (``*``) affects every dependency set.
        """
        versions = self._field_versions
        version = versions.get('*', 0)
        for field in fields:
            revision = versions.get(field, 0)
            if revision > version:
                version = revision
        return self.generation, version

    def record_many(self, positions, fields):
        """Commit changed native-array positions after a successful batch write."""
        fields = tuple(fields)
        for position in positions:
            for field in fields:
                self.record(position, field)

    def changes_since(self, cursor=None):
        generation, version = cursor if cursor is not None else (None, -1)
        reset = generation != self.generation or version > self.version
        if not reset and version == self.version:
            return MutationBatch(self.generation, self.version, ())
        if self._records and version < self._records[0][0] - 1:
            reset = True
        changes = set()
        for revision, position, field in reversed(self._records):
            if not reset and revision <= version:
                break
            changes.add((position, field))
        return MutationBatch(self.generation, self.version, tuple(sorted(changes)), reset)
