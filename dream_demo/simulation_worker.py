"""Experimental, single-owner simulation with immutable UI publications.

Only gameplay commands advance game rules. The monotonic cadence limits their starts;
idle ticks do not call ``wait`` or advance world time. This Python thread is an
ownership boundary, not a claim of CPU parallelism under the GIL.

The caller transfers a detached copy of its initial state. ``manager_factory``
runs on the owner thread and must return a manager dedicated to this worker.
Normal snapshots contain no GameState/Cell/Entity references. ``export_state``
is an explicitly expensive FIFO barrier returning a detached compatibility copy.
``poll`` is a bounded notification ring; futures are the reliable completion
channel when a client cannot poll promptly (see ``dropped_completions``).
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import Future
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import math
from queue import Full
import threading
import time
from uuid import uuid4

from .core.material_grid import MaterialGrid
from .core.state import GameState as _VisibilityGameState
from .core.ticker_transport import is_zero_time_control
from .persistence import GameSession


_VISIBILITY_STATE_DICT = next(cls.__dict__['__dict__']
                              for cls in _VisibilityGameState.__mro__
                              if '__dict__' in cls.__dict__)


def _freeze(value):
    if value is None or type(value) in (bool, int, float, str, bytes):
        return value
    if isinstance(value, Enum):
        return _freeze(value.value)
    if isinstance(value, dict):
        return tuple((_freeze(key), _freeze(item)) for key, item in value.items())
    if isinstance(value, (list, tuple, deque)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    if is_dataclass(value):
        return tuple((field.name, _freeze(getattr(value, field.name)))
                     for field in fields(value))
    raise TypeError(f'Cannot publish mutable value of type {type(value).__name__}')


@dataclass(frozen=True)
class EntitySnapshot:
    id: str
    label: str
    x: int
    y: int
    glyph: str
    integrity: int

    @property
    def entity_id(self):
        return self.id

    @property
    def name(self):
        return self.label


@dataclass(frozen=True)
class MaterialField:
    name: str
    typecode: str
    pages: tuple[bytes, ...]


@dataclass(frozen=True)
class PresentationSnapshot:
    """Owner identities are opaque values, never addresses dereferenced by UI."""
    stream: str
    map_identity: int
    explosions: tuple
    recovery: object
    ticker_generation: int
    ticker_revision: int
    ticker_ids: tuple[int, ...]
    ticker_notes: tuple[str, ...]
    ticker_retained_ids: tuple[int, ...] | None = None
    ticker_backlog: int = 0


@dataclass(frozen=True)
class SimulationSnapshot:
    sequence: int
    width: int
    height: int
    depth: int
    world_time: int
    published_at: float
    materials: tuple[MaterialField, ...]
    material_names: tuple[str, ...]
    entities: tuple[EntitySnapshot, ...]
    status: tuple[tuple[str, object], ...]
    messages: tuple[str, ...]
    visibility: bytes
    map_generation: int
    layer_key: str
    presentation: PresentationSnapshot | None = None
    command_context_token: int = 0
    legacy_display: object = None

    @property
    def player(self):
        return self.entities[0]


@dataclass(frozen=True)
class FrozenActionResult:
    changed: bool
    message: str
    data: tuple
    legacy_data: object = None

    @classmethod
    def from_result(cls, result, *, legacy=False):
        if legacy:
            from .legacy_display import freeze
        return cls(result.changed, result.message, _freeze(result.data),
                   freeze(result.data) if legacy else None)


@dataclass(frozen=True)
class Completion:
    sequence: int
    command: str
    result: FrozenActionResult | None
    snapshot: SimulationSnapshot
    submitted_at: float
    started_at: float
    completed_at: float
    auto_pickup_result: FrozenActionResult | None = None


@dataclass(frozen=True)
class WorkerMetrics:
    """Busy command cadence counters; notification-ring drops are separate.

    An overrun takes longer than one configured tick from command start through
    immutable publication. missed_busy_slots counts whole tick durations spent
    busy (floor(duration/tick)), excluding idle waits and FIFO control barriers.
    """
    commands_started: int = 0
    commands_completed: int = 0
    overrun_commands: int = 0
    missed_busy_slots: int = 0


@dataclass(frozen=True)
class _Request:
    kind: str
    sequence: int
    command: str
    args: tuple
    choice: str | None
    auto_pickup: bool
    submitted_at: float
    future: Future


def interpolate_entities(previous, current, alpha):
    """Return immutable (id, (x, y)) pairs; alpha belongs to presentation only.

    Births and map changes snap to current positions. Coordinates never feed
    back into simulation. Clients may retain either snapshot indefinitely.
    """
    alpha = float(alpha)
    if not math.isfinite(alpha):
        raise ValueError('alpha must be finite')
    alpha = max(0.0, min(1.0, alpha))
    same_map = (previous.layer_key, previous.width, previous.height, previous.map_generation) == (
        current.layer_key, current.width, current.height, current.map_generation)
    old = {entity.id: entity for entity in previous.entities} if same_map else {}
    return tuple((entity.id, (
        old[entity.id].x + (entity.x - old[entity.id].x) * alpha,
        old[entity.id].y + (entity.y - old[entity.id].y) * alpha))
        if (entity.id in old
            and max(abs(entity.x - old[entity.id].x), abs(entity.y - old[entity.id].y)) <= 1)
        else (entity.id, (float(entity.x), float(entity.y)))
        for entity in current.entities)


def _fence_tutorial_command(command, args, snapshot):
    """Capture the caller's published world before a FIFO replay can replace it."""
    if command != 'tutorial_view' or not args:
        return args
    if len(args) > 1 and type(args[1]) is tuple:
        return args
    if snapshot is None:
        raise RuntimeError('tutorial commands require an initial snapshot')
    context = (snapshot.command_context_token, dict(snapshot.status)['action_seq'],
               snapshot.world_time)
    return (args[0], context, *args[1:])


class _Publisher:
    def __init__(self, page_bytes, *, include_legacy_display=False):
        from .legacy_display import DisplayPublisher
        self.display_publisher = DisplayPublisher() if include_legacy_display else None
        self.page_bytes = page_bytes
        self.grid = None
        self.previous = None
        self.map_generation = 0
        self.stream = uuid4().hex
        self.context_token = None
        self._visibility_cache = None

    def _visibility_bytes(self, state, visible, context_token):
        GameState = _VisibilityGameState
        # Only ordinary dimensions and built-in membership have no authored
        # callbacks whose per-cell order the original scan must preserve.
        ordinary = (type(state) is GameState
                    and all(cls.__dict__.get('__getattribute__', object.__getattribute__)
                            is object.__getattribute__ for cls in GameState.__mro__)
                    and not any('width' in cls.__dict__ or 'height' in cls.__dict__
                                for cls in GameState.__mro__)
                    and next((cls.__dict__['__dict__'] for cls in GameState.__mro__
                              if '__dict__' in cls.__dict__), None) is _VISIBILITY_STATE_DICT
                    and type(state.__dict__.get('width')) is int
                    and type(state.__dict__.get('height')) is int
                    and state.__dict__['width'] > 0
                    and state.__dict__['height'] > 0
                    and type(visible) in (set, frozenset))
        if ordinary:
            # Bound Python validation/copy/scatter work to sparse footprints.
            # Dense illumination already suits the original contiguous scan.
            ordinary = len(visible) <= state.width * state.height // 8
        if ordinary:
            ordinary = all(type(point) is tuple and len(point) == 2
                           and type(point[0]) is int and type(point[1]) is int
                           for point in visible)
        if not ordinary:
            self._visibility_cache = None
            return bytes(int((x, y) in visible) for y in range(state.height)
                         for x in range(state.width))
        # visible_cells exposes a mutable alias. Copy its actual membership on
        # every publication; neither object identity nor sight's key proves it.
        membership = frozenset(visible)
        scope = (context_token, self.map_generation, state.width, state.height)
        cached = self._visibility_cache
        if cached is not None and cached[0] == scope and cached[1] == membership:
            return cached[2]
        width, height = scope[2:]
        encoded = bytearray(width * height)
        for x, y in membership:
            if 0 <= x < width and 0 <= y < height:
                encoded[y * width + x] = 1
        visibility = bytes(encoded)
        self._visibility_cache = (scope, membership, visibility)
        return visibility

    def build(self, state, sequence):
        # Sight queries populate this derived field, but the current save schema
        # includes it. Publication must not change a serial command/save digest.
        missing = object()
        saved_radius_cache = state.__dict__.get('_sight_radius_cache', missing)
        try:
            return self._build(state, sequence)
        finally:
            if saved_radius_cache is missing:
                state.__dict__.pop('_sight_radius_cache', None)
            else:
                state._sight_radius_cache = saved_radius_cache

    def _build(self, state, sequence):
        from .core.command_context import command_context_token
        if self.display_publisher is not None:
            from .legacy_commands import map_identity
            map_identity(state)
        context_token = command_context_token(state)
        if context_token != self.context_token:
            # A replay replaces the session world and restarts event counters.
            # Ordinary map changes retain the session's occurrence chronology.
            self.stream = uuid4().hex
            self.context_token = context_token
        grid = self.grid
        same_map = grid is not None and grid.matches(state.cells, state.width, state.height)
        if not same_map:
            self.map_generation += 1
            grid = MaterialGrid.from_cells(state.cells, state.width, state.height)
            self.grid = grid
            batch = None
        elif grid.store is not None:
            batch = grid.refresh_changes()
        else:
            # Authoritative Cell writes are deliberately not trusted to have
            # updated a runtime mirror. P6 publication is valid with P4 disabled.
            for y, row in enumerate(state.cells):
                for x, cell in enumerate(row):
                    grid.sync_cell(x, y, cell)
            batch = None
        old_fields = {field.name: field for field in self.previous.materials} if (
            same_map and self.previous is not None) else {}
        material_fields = []
        for name in grid.BYTE_FIELDS + grid.SIGNED_FIELDS + grid.ID_FIELDS:
            values = getattr(grid, name)
            raw = memoryview(values).cast('B')
            old = old_fields.get(name)
            if old is not None and batch is not None and not batch.reset:
                # Only pages intersecting journal positions can differ. Keep
                # every other immutable byte object without touching its data.
                itemsize = getattr(values, 'itemsize', 1)
                dirty_pages = set()
                for position in batch.positions:
                    first = position * itemsize // self.page_bytes
                    last = ((position + 1) * itemsize - 1) // self.page_bytes
                    dirty_pages.update(range(first, last + 1))
                if not dirty_pages:
                    material_fields.append(old)
                    continue
                pages = list(old.pages)
                for index in sorted(dirty_pages):
                    offset = index * self.page_bytes
                    chunk = raw[offset:offset + self.page_bytes]
                    if chunk != pages[index]:
                        pages[index] = bytes(chunk)
                material_fields.append(MaterialField(name, old.typecode, tuple(pages)))
                continue
            pages = []
            for index, offset in enumerate(range(0, len(raw), self.page_bytes)):
                chunk = raw[offset:offset + self.page_bytes]
                if old is not None and index < len(old.pages) and chunk == old.pages[index]:
                    pages.append(old.pages[index])
                else:
                    pages.append(bytes(chunk))
            material_fields.append(MaterialField(name, getattr(values, 'typecode', 'B'), tuple(pages)))
        actors = (state.player, *state.enemies)
        entities = tuple(EntitySnapshot(actor.id, actor.label, actor.x, actor.y,
                                        actor.glyph, actor.integrity) for actor in actors)
        visible = state.visible_cells()
        visibility = self._visibility_bytes(state, visible, context_token)
        status = tuple((key, _freeze(getattr(state, key))) for key in (
            'mind', 'max_mind', 'lucidity', 'max_lucidity', 'imagination',
            'max_imagination', 'run_over', 'action_seq'))
        notes = state.ticker_notes
        from .core.ticker_transport import ticker_window
        ticker = ticker_window(notes)
        presentation = PresentationSnapshot(
            self.stream, getattr(state, '_presentation_map_identity', id(state.cells)),
            tuple(getattr(state, '_presentation_explosions', ())),
            getattr(state, '_presentation_explosion_recovery', None),
            ticker.generation, ticker.revision, ticker.identities, ticker.notes,
            ticker.retained, ticker.backlog)
        snapshot = SimulationSnapshot(sequence, state.width, state.height, state.depth,
            state.time, time.perf_counter(), tuple(material_fields), tuple(grid.names),
            entities, status, tuple(state.messages), visibility, self.map_generation, state.layer_key(),
            presentation, context_token,
            self.display_publisher.build(state) if self.display_publisher is not None else None)
        self.previous = snapshot
        return snapshot


class SimulationWorker:
    """Bounded FIFO; one thread owns GameSession, state, manager and publisher.

    A failed command/save/publication is fatal: its future and all queued
    futures fail, and close re-raises the cause. Partially applied actions are
    never continued or silently saved. Cancellation only skips queued commands.
    """
    def __init__(self, state, *, manager_factory=None, persistence_enabled=False,
                 tick_seconds=1 / 30, queue_capacity=64, page_bytes=4096,
                 include_legacy_display=False, start_entered=True):
        if not math.isfinite(tick_seconds) or tick_seconds <= 0:
            raise ValueError('tick_seconds must be positive and finite')
        if type(queue_capacity) is not int or queue_capacity < 1:
            raise ValueError('queue_capacity must be positive')
        if type(page_bytes) is not int or page_bytes < 1:
            raise ValueError('page_bytes must be positive')
        if persistence_enabled and manager_factory is None:
            raise ValueError('persistence requires manager_factory')
        detached = deepcopy(state)
        self.ready = Future()
        self._condition = threading.Condition()
        self._requests = deque()
        self._completions = deque(maxlen=queue_capacity)
        self._capacity = queue_capacity
        self._dropped = 0
        self._sequence = 0
        self._closing = False
        self._save_on_close = True
        self._error = None
        self._pair = (None, None)
        self._metrics = WorkerMetrics()
        self._thread = threading.Thread(target=self._run,
            args=(detached, manager_factory, persistence_enabled, tick_seconds, page_bytes, include_legacy_display, start_entered),
            name='simulation-owner', daemon=False)
        self._thread.start()

    def _enqueue(self, kind, command='', args=(), choice=None, auto_pickup=False,
                 block=False, timeout=None, _admitted=False):
        # Capture mutable argument payloads before they cross the ownership boundary.
        args = deepcopy(args)
        future = Future()
        condition = self._condition
        def cancelled(completed):
            # A queued gameplay head may be sleeping until its cadence slot.
            # Cancellation removes that barrier and must wake trailing work.
            # Keep only the condition alive, not the worker, via this callback.
            if completed.cancelled():
                with condition:
                    condition.notify_all()
        future.add_done_callback(cancelled)
        deadline = None if timeout is None else time.perf_counter() + timeout
        with self._condition:
            while True:
                if self._error is not None:
                    raise self._error
                if self._closing:
                    raise RuntimeError('simulation worker is closed')
                from .core.ticker_transport import ticker_backpressured
                pressure = (kind == 'command' and not _admitted
                            and ticker_backpressured(self._pair[1], command, args))
                if len(self._requests) < self._capacity and not pressure:
                    break
                remaining = None if deadline is None else deadline - time.perf_counter()
                if not block or (remaining is not None and remaining <= 0):
                    raise Full('ticker backlog is full' if pressure else
                               'simulation command queue is full')
                self._condition.wait(remaining)
            if kind == 'command':
                self._sequence += 1
            self._requests.append(_Request(kind, self._sequence, command, args, choice,
                                            auto_pickup, time.perf_counter(), future))
            self._condition.notify_all()
        return future

    def submit(self, command, *args, choice=None, auto_pickup=False, block=False, timeout=None):
        args = _fence_tutorial_command(command, args, self.snapshot_pair()[1])
        return self._enqueue('command', command, args, choice, auto_pickup, block, timeout)

    def _submit_admitted(self, command, *args, choice=None, auto_pickup=False):
        # The process client already accepted this request into its bounded
        # FIFO. Rechecking producer pressure here could reject accepted input
        # or deadlock its single-flight transport before it can deliver ACKs.
        args = _fence_tutorial_command(command, args, self.snapshot_pair()[1])
        return self._enqueue('command', command, args, choice, auto_pickup,
                             _admitted=True)

    def start(self):
        return self._enqueue('start')

    def export_state(self, *, block=False, timeout=None):
        return self._enqueue('export', block=block, timeout=timeout)

    def save(self, *, block=False, timeout=None):
        return self._enqueue('save', block=block, timeout=timeout)

    def poll(self):
        with self._condition:
            completions = tuple(self._completions)
            self._completions.clear()
            return completions

    @property
    def dropped_completions(self):
        with self._condition:
            return self._dropped

    @property
    def error(self):
        """Terminal owner failure, observable without issuing another command."""
        with self._condition:
            return self._error

    @property
    def metrics(self):
        with self._condition:
            return self._metrics

    def snapshot_pair(self):
        with self._condition:
            return self._pair

    def close(self, *, save=True, timeout=None):
        if threading.current_thread() is self._thread:
            raise RuntimeError('cannot close worker from its owner thread')
        with self._condition:
            if not self._closing:
                self._closing = True
                self._save_on_close = save
            self._condition.notify_all()
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise TimeoutError('simulation worker shutdown timed out; drain remains active')
        if self._error is not None:
            raise self._error

    def _publish(self, snapshot):
        with self._condition:
            self._pair = (self._pair[1], snapshot)
            self._condition.notify_all()

    def _run(self, state, manager_factory, persistence_enabled, tick_seconds, page_bytes, include_legacy_display, start_entered):
        request = None
        try:
            manager = manager_factory() if manager_factory else None
            session = GameSession(state, manager, persist_initial=False,
                                  persistence_enabled=persistence_enabled)
            state = session.state
            # Creating this explicit client means the player has entered the
            # session, including when they quit before issuing their first action.
            if start_entered and not state.run_over:
                session.start()
            publisher = _Publisher(page_bytes, include_legacy_display=include_legacy_display)
            with session._action_lock:
                initial = publisher.build(state, 0)
            self._publish(initial)
            self.ready.set_result(initial)
            next_tick = time.perf_counter()
            while True:
                with self._condition:
                    while True:
                        # Canceled heads own no work and reserve no gameplay
                        # slot. Discard them before considering a timed wait.
                        while self._requests and self._requests[0].future.cancelled():
                            # Executor acknowledgement also releases wait()
                            # and as_completed() waiters on canceled Futures.
                            self._requests[0].future.set_running_or_notify_cancel()
                            self._requests.popleft()
                            self._condition.notify_all()
                        if self._requests or self._closing:
                            break
                        self._condition.wait()
                    if not self._requests:
                        break
                    head = self._requests[0]
                    paced = (head.kind == 'command'
                             and not is_zero_time_control(head.command, head.args))
                    delay = next_tick - time.perf_counter()
                    if paced and delay > 0:
                        self._condition.wait(delay)
                        continue
                    request = self._requests.popleft()
                    self._condition.notify_all()
                if not request.future.set_running_or_notify_cancel():
                    request = None
                    continue
                started_at = time.perf_counter()
                state = session.state
                if request.kind == 'export':
                    request.future.set_result(deepcopy(state))
                elif request.kind == 'start':
                    session.start()
                    request.future.set_result(None)
                elif request.kind == 'save':
                    if session.persistence_enabled and not state.run_over:
                        manager.save(state)
                        session._dirty = False
                        session._last_saved_turn = state.time
                    request.future.set_result(None)
                else:
                    with self._condition:
                        measured = self._metrics
                        self._metrics = WorkerMetrics(measured.commands_started + 1,
                            measured.commands_completed, measured.overrun_commands,
                            measured.missed_busy_slots)
                    action_before = state.action_seq, state.time
                    command, command_args, command_choice = request.command, request.args, request.choice
                    if command == 'legacy_intent':
                        from .core.entities import ActionResult
                        from .legacy_commands import resolve_intent
                        with session._action_lock:
                            resolved = resolve_intent(state, command_args[0] if command_args else None)
                            if isinstance(resolved, ActionResult):
                                result = resolved
                            else:
                                command, command_args, command_choice = resolved
                                result = session.apply(command, *command_args, choice=command_choice)
                    else:
                        result = session.apply(command, *command_args, choice=command_choice)
                    state = session.state
                    pickup_allowed = request.auto_pickup and (not include_legacy_display or (
                        result.changed and not state.run_over and
                        ((state.action_seq, state.time) != action_before or 'position' in result.data)))
                    pickup = session.auto_pickup() if pickup_allowed else None
                    state = session.state
                    # Use synchronous owner-thread saving; GameSession's regular
                    # flush catches errors, which would hide them from this API.
                    if (session.persistence_enabled and not state.run_over and session._dirty
                            and state.time - session._last_saved_turn >= session.SAVE_TURN_INTERVAL):
                        manager.save(state)
                        session._dirty = False
                        session._last_saved_turn = state.time
                    with session._action_lock:
                        snapshot = publisher.build(state, request.sequence)
                    completion = Completion(request.sequence, command,
                        FrozenActionResult.from_result(result, legacy=include_legacy_display), snapshot, request.submitted_at,
                        started_at, time.perf_counter(),
                        FrozenActionResult.from_result(pickup, legacy=include_legacy_display) if pickup is not None else None)
                    self._publish(snapshot)
                    with self._condition:
                        busy_seconds = completion.completed_at - started_at
                        measured = self._metrics
                        self._metrics = WorkerMetrics(measured.commands_started,
                            measured.commands_completed + 1,
                            measured.overrun_commands + int(busy_seconds > tick_seconds),
                            measured.missed_busy_slots + math.floor(busy_seconds / tick_seconds))
                        if len(self._completions) == self._capacity:
                            self._dropped += 1
                        self._completions.append(completion)
                    request.future.set_result(completion)
                    if paced:
                        # Skip missed gameplay slots instead of a catch-up
                        # burst. Zero-time controls publish in FIFO without
                        # waiting for or consuming a gameplay cadence slot.
                        now = time.perf_counter()
                        next_tick += (max(1, math.floor((now - next_tick) / tick_seconds) + 1)
                                      * tick_seconds)
                request = None
            if self._save_on_close and session.persistence_enabled and not session.state.run_over:
                session.save_and_exit()
        except BaseException as error:
            with self._condition:
                self._error = error
                self._closing = True
                queued = tuple(self._requests)
                self._requests.clear()
                self._condition.notify_all()
            if not self.ready.done():
                self.ready.set_exception(error)
            if request is not None and not request.future.done():
                request.future.set_exception(error)
            for entry in queued:
                if entry.future.set_running_or_notify_cancel():
                    entry.future.set_exception(error)

