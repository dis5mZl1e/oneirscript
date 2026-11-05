"""Live actor occupancy with ordered duplicate entries and immutable snapshots."""
from copy import deepcopy
from weakref import ref
from .metadata_versions import container_changed as _metadata_changed, register_container


class SpatialIndex:
    def __init__(self, enemies, player=None):
        self.enemies = enemies
        self.player = None
        self.members = {}
        self.buckets = {}
        self._bucket_cache = {}
        self._positions = None
        self._positions_with_player = None
        self.rebuild()
        self.set_player(player)

    def _watch(self, actor):
        watchers = actor.__dict__.setdefault('_spatial_watchers', {})
        identity = id(self)
        def expired(_):
            watchers.pop(identity, None)
        watchers[identity] = ref(self, expired)

    def _unwatch(self, actor):
        actor.__dict__.get('_spatial_watchers', {}).pop(id(self), None)

    def _invalidate(self, point=None):
        if point is not None:
            self._bucket_cache.pop(point, None)
        self._positions = self._positions_with_player = None

    def set_player(self, player):
        previous = self.player
        self.player = player
        if previous is not None and id(previous) not in self.members:
            self._unwatch(previous)
        if player is not None:
            self._watch(player)
        self._positions_with_player = None

    def rebuild(self):
        old = self.members
        members, buckets = {}, {}
        for rank, actor in enumerate(self.enemies):
            record = members.setdefault(id(actor), [actor, [], (actor.x, actor.y), actor.integrity > 0])
            record[1].append(rank)
            if record[3]:
                buckets.setdefault(record[2], {})[rank] = actor
        self.members, self.buckets = members, buckets
        for identity, record in old.items():
            if identity not in members and record[0] is not self.player:
                self._unwatch(record[0])
        for record in members.values():
            self._watch(record[0])
        self._bucket_cache.clear()
        self._invalidate()
        _metadata_changed(self.enemies)

    def actor_changed(self, actor):
        record = self.members.get(id(actor))
        if record is not None:
            old_point, old_alive = record[2], record[3]
            point, alive = (actor.x, actor.y), actor.integrity > 0
            if (old_point, old_alive) != (point, alive):
                if old_alive:
                    bucket = self.buckets[old_point]
                    for rank in record[1]:
                        del bucket[rank]
                    if not bucket:
                        del self.buckets[old_point]
                    self._invalidate(old_point)
                if alive:
                    bucket = self.buckets.setdefault(point, {})
                    for rank in record[1]:
                        bucket[rank] = actor
                    self._invalidate(point)
                record[2], record[3] = point, alive
        if actor is self.player:
            self._positions_with_player = None

    def enemies_at(self, x, y):
        point = (x, y)
        cached = self._bucket_cache.get(point)
        if cached is None:
            bucket = self.buckets.get(point)
            cached = tuple(bucket[rank] for rank in sorted(bucket)) if bucket else ()
            # Do not retain unbounded misses as a mover explores the world.
            if bucket:
                self._bucket_cache[point] = cached
        return cached

    def entities_at(self, x, y, include_player=True, player=None):
        actors = self.enemies_at(x, y)
        if include_player and player is not None and (player.x, player.y) == (x, y):
            return (player,) + actors
        return actors

    def occupied_positions(self, known_cells=None, include_player=True, player=None):
        if self._positions is None:
            self._positions = frozenset(self.buckets)
        positions = self._positions
        if include_player and player is not None:
            point = (player.x, player.y)
            cached = self._positions_with_player
            if cached is None or cached[0] != point:
                cached = (point, positions if point in positions else positions | {point})
                self._positions_with_player = cached
            positions = cached[1]
        return positions if known_cells is None else positions.intersection(known_cells)


class SpatialActors(list):
    """Ordinary list semantics; edits rebuild ranks, direct moves update buckets."""
    def __init__(self, values=(), player=None):
        list.__init__(self, values)
        self.spatial = SpatialIndex(self)

    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        self.spatial.rebuild()

    def __delitem__(self, key):
        list.__delitem__(self, key)
        self.spatial.rebuild()

    def append(self, value):
        list.append(self, value)
        self.spatial.rebuild()

    def extend(self, values):
        # Rebuild even if an iterator yields entries before raising.
        try:
            list.extend(self, values)
        finally:
            self.spatial.rebuild()

    def insert(self, index, value):
        list.insert(self, index, value)
        self.spatial.rebuild()

    def pop(self, index=-1):
        value = list.pop(self, index)
        self.spatial.rebuild()
        return value

    def remove(self, value):
        list.remove(self, value)
        self.spatial.rebuild()

    def clear(self):
        list.clear(self)
        self.spatial.rebuild()

    def reverse(self):
        list.reverse(self)
        self.spatial.rebuild()

    def sort(self, *args, **kwargs):
        try:
            list.sort(self, *args, **kwargs)
        finally:
            self.spatial.rebuild()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        list.__imul__(self, count)
        self.spatial.rebuild()
        return self

    def __reduce_ex__(self, protocol):
        return (type(self), (), None, iter(self))

    def __deepcopy__(self, memo):
        result = type(self)()
        memo[id(self)] = result
        result.extend(deepcopy(actor, memo) for actor in self)
        return result


register_container(SpatialActors)
