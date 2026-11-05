"""Bounded, non-destructive facts for independent display consumers."""
from dataclasses import dataclass
from uuid import uuid4

from .message_history import MessageHistory

MAX_PRESENTATION_EVENTS = 256


class TickerHistory(MessageHistory):
    def __init__(self, values=()):
        super().__init__(values)
        self._consumers = {}

    def _changed(self, *, reset=False):
        super()._changed(reset=reset)
        if reset:
            for acknowledged in self._consumers.values():
                acknowledged.clear()

    def register_consumer(self, token, generation):
        if generation != self.generation or token in self._consumers:
            return False
        self._consumers[token] = set()
        return True

    def acknowledge(self, token, generation, identity):
        acknowledged = self._consumers.get(token)
        if (generation != self.generation or acknowledged is None
                or identity not in self._ids or identity in acknowledged):
            return False
        acknowledged.add(identity)
        self._prune_acknowledged()
        return True

    def release_consumer(self, token, generation):
        if generation != self.generation or token not in self._consumers:
            return False
        del self._consumers[token]
        self._prune_acknowledged()
        return True

    def _prune_acknowledged(self):
        # No subscribers means preserve the original lossless queue backlog.
        if not self._consumers:
            return
        amount = 0
        for identity in self._ids:
            if not all(identity in ids for ids in self._consumers.values()):
                break
            amount += 1
        if amount:
            removed = self._ids[:amount]
            del self[:amount]
            for acknowledged in self._consumers.values():
                acknowledged.difference_update(removed)


@dataclass(frozen=True)
class ExplosionEvent:
    sequence: int
    layer: str
    map_identity: int
    cells: frozenset
    blast: tuple[int, int, int]


@dataclass(frozen=True)
class ExplosionRecovery:
    map_identity: int
    layer: str
    sequence: int
    cells: tuple
    blasts: tuple


def publish_explosion(state, cells, blast):
    sequence = getattr(state, '_presentation_explosion_seq', 0) + 1
    map_identity = getattr(state, '_presentation_map_identity', None)
    if map_identity is None:
        map_identity = uuid4().int
    event = ExplosionEvent(sequence, state.layer_key(), map_identity,
                           frozenset(cells), tuple(blast))
    state._presentation_explosion_seq = sequence
    state._presentation_map_identity = map_identity
    state._presentation_explosions = (
        *getattr(state, '_presentation_explosions', ())[-(MAX_PRESENTATION_EVENTS - 1):], event)
    previous = getattr(state, '_presentation_explosion_recovery', None)
    same_map = previous is not None and (previous.map_identity, previous.layer) == (
        event.map_identity, event.layer)
    cell_sequences = dict(previous.cells) if same_map else {}
    cell_sequences.update((cell, sequence) for cell in event.cells)
    # Distances never exceed width+height. Larger radii yield the same first
    # color band at every map point, so this canonicalization bounds variants.
    radius_limit = 3 * (getattr(state, 'width', 1000) + getattr(state, 'height', 1000))
    radius = min(max(1, blast[2]), radius_limit)
    center = tuple(blast[:2])
    candidates = {(old_blast[:2], old_blast[2]): seq
                  for seq, old_blast in previous.blasts} if same_map else {}
    # A newer larger ring dominates every older smaller ring at this center,
    # for every possible consumer cursor and every possible displayed cell.
    candidates = {key: seq for key, seq in candidates.items()
                  if key[0] != center or key[1] > radius}
    candidates[(center, radius)] = sequence
    state._presentation_explosion_recovery = ExplosionRecovery(
        event.map_identity, event.layer, sequence, tuple(cell_sequences.items()),
        tuple((seq, (*point, ring_radius))
              for (point, ring_radius), seq in candidates.items()))

