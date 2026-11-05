"""Immutable snapshot deltas for an independent simulation process.

Packets contain display metadata and changed material pages. A receiver retains
its previous immutable snapshot; no GameState, Cell or whole map is sent per
command. Generation/layout changes recover with a self-contained full packet.
"""
from dataclasses import dataclass, replace

from .simulation_worker import MaterialField, SimulationSnapshot


@dataclass(frozen=True)
class SnapshotDelta:
    header: SimulationSnapshot
    layout: tuple
    pages: tuple
    full: bool
    base: tuple | None

    @property
    def material_bytes(self):
        return sum(len(page) for _, _, page in self.pages)


def _layout(snapshot):
    return tuple((field.name, field.typecode, tuple(map(len, field.pages)))
                 for field in snapshot.materials)


def _map(snapshot):
    return (snapshot.map_generation, snapshot.width, snapshot.height,
            snapshot.depth, snapshot.layer_key)


def _token(snapshot):
    return (*_map(snapshot), snapshot.sequence)


def encode_snapshot(snapshot, previous=None):
    layout = _layout(snapshot)
    full = previous is None or _map(snapshot) != _map(previous) or layout != _layout(previous)
    old = {} if full else {field.name: field for field in previous.materials}
    pages = []
    for field in snapshot.materials:
        prior = old.get(field.name)
        for index, page in enumerate(field.pages):
            if prior is None or (page is not prior.pages[index] and page != prior.pages[index]):
                pages.append((field.name, index, page))
    return SnapshotDelta(replace(snapshot, materials=()), layout, tuple(pages),
                         full, None if full else _token(previous))


def decode_snapshot(packet, previous=None):
    """Validate a complete delta before exposing any reconstructed snapshot."""
    if packet.header.materials:
        raise ValueError('snapshot header must not contain material payloads')
    if not packet.full:
        if (previous is None or packet.base != _token(previous)
                or packet.layout != _layout(previous)
                or _map(packet.header) != _map(previous)):
            raise ValueError('snapshot delta requires its matching base')
    elif packet.base is not None:
        raise ValueError('full snapshot cannot require a base')
    prior = {} if packet.full else {field.name: field for field in previous.materials}
    descriptors = {}
    buffers = {}
    for name, typecode, lengths in packet.layout:
        if name in descriptors or any(type(length) is not int or length < 0 for length in lengths):
            raise ValueError('invalid material layout')
        descriptors[name] = (typecode, lengths)
        buffers[name] = [None] * len(lengths) if packet.full else list(prior[name].pages)
    seen = set()
    for name, index, page in packet.pages:
        if (name not in descriptors or type(index) is not int
                or not 0 <= index < len(buffers[name]) or type(page) is not bytes
                or len(page) != descriptors[name][1][index] or (name, index) in seen):
            raise ValueError('invalid material page delta')
        seen.add((name, index))
        buffers[name][index] = page
    fields = []
    for name, typecode, _ in packet.layout:
        pages = tuple(buffers[name])
        if any(page is None for page in pages):
            raise ValueError('full snapshot is missing material pages')
        old = prior.get(name)
        fields.append(old if old is not None and all(a is b for a, b in zip(old.pages, pages))
                      else MaterialField(name, typecode, pages))
    return replace(packet.header, materials=tuple(fields))
