"""Asynchronous owner-backed session for the complete legacy widget tree.

No command waits on the UI thread. Completion callbacks publish display facts
before user-interface continuations run. A Future is deliberately not an
ActionResult: treating submission as success would lose choice/error semantics.
"""
from collections import deque
from queue import Full
from concurrent.futures import Future, CancelledError
from dataclasses import dataclass
import threading
import time
import weakref

from .core.entities import ActionResult
from .legacy_display import LegacyDisplayState


def action_result(frozen):
    if frozen.legacy_data is not None:
        from copy import deepcopy
        from .legacy_display import thaw
        return ActionResult(frozen.changed, frozen.message, deepcopy(thaw(frozen.legacy_data)))
    def unpack(value):
        if isinstance(value, tuple):
            if value and all(isinstance(row, tuple) and len(row) == 2 and
                             isinstance(row[0], str) for row in value):
                return {k: unpack(v) for k, v in value}
            return tuple(unpack(v) for v in value)
        return value
    return ActionResult(frozen.changed, frozen.message, unpack(frozen.data) or {})


class LegacyAsyncSession:
    asynchronous = True
    _dirty = False

    def __init__(self, owner, manager, *, initial=None, started=None, await_owner_ready=False):
        self.owner = owner
        self.manager = manager
        self.started = time.monotonic() if started is None else started
        self.persistence_enabled = False
        self._state = None if initial is None else LegacyDisplayState(initial.legacy_display)
        self._pending = deque()
        self._before_publish = {}
        self._lock = threading.Lock()
        self.error = None
        self._close_future = None
        self._reliable = []
        self._saves = []
        self.navigation_barrier = False
        self._ready_applied = initial is not None and not await_owner_ready
        self._completion_wakeup = None
        self._completion_wakeup_generation = 0
        self._completion_wakeup_pending = False
        self.display_changed = False
        reference = weakref.ref(self)
        def completed(future):
            session = reference()
            if session is not None:
                session._completion_finished(future)
        self._completion_callback = completed
        ready = getattr(self.owner, 'ready', None)
        if ready is not None:
            ready.add_done_callback(completed)

    def set_completion_wakeup(self, callback):
        """Bind one weak UI subscriber; completion threads only post a wake."""
        with self._lock:
            self._completion_wakeup_generation += 1
            self._completion_wakeup_pending = False
            self._completion_wakeup = None if callback is None else weakref.WeakMethod(callback)
            owner_ready = getattr(self.owner, 'ready', None)
            ready = (callback is not None and (not self._ready_applied and owner_ready is not None
                     and owner_ready.done()
                     or any(future.done() for future, _ in self._pending)
                     or any(future.done() for future in self._saves)))
        if ready:
            self._completion_finished(None)

    def acknowledge_completion_wakeup(self, generation):
        """Main-loop receipt; release coalescing before draining FIFO results."""
        with self._lock:
            if generation != self._completion_wakeup_generation or self._completion_wakeup is None:
                return False
            self._completion_wakeup_pending = False
            return True

    def _completion_finished(self, future):
        with self._lock:
            callback = None if self._completion_wakeup is None else self._completion_wakeup()
            if callback is None or self._completion_wakeup_pending:
                return
            generation = self._completion_wakeup_generation
            self._completion_wakeup_pending = True
        try:
            accepted = callback(self, generation)
        except Exception:
            accepted = False  # Periodic main-loop drain remains a fallback.
        if accepted is False:
            with self._lock:
                if generation == self._completion_wakeup_generation:
                    self._completion_wakeup_pending = False

    @property
    def state(self):
        if self._state is None:
            raise RuntimeError('owner display has not arrived')
        return self._state

    def apply(self, command, *args, choice=None):
        return self.submit(command, *args, choice=choice)

    def submit(self, command, *args, choice=None, auto_pickup=False, continuation=None, before_publish=None, expected_context=None):
        if self.navigation_barrier and command not in ('presentation_control', 'catalog_control', 'tutorial_view'):
            result = ActionResult(False, 'Saving before leaving this world; try again after saving.')
            if continuation is not None:
                continuation(result, None)
            return result
        from .legacy_commands import capture_intent
        intent = capture_intent(self.state, command, args, choice)
        if expected_context is not None:
            from dataclasses import replace
            intent = replace(intent, context=expected_context, strict=True)
        refused = None
        admission_failed = False
        with self._lock:
            try:
                future = self.owner.submit('legacy_intent', intent, auto_pickup=auto_pickup)
            except Full:
                refused = ActionResult(False, 'Simulation command queue is full')
            except Exception as error:
                self.error = error
                admission_failed = True
                refused = ActionResult(False, str(error), {'owner_error': True})
            else:
                self._pending.append((future, [] if continuation is None else [continuation]))
                if before_publish is not None:
                    def capture_before():
                        from .legacy_commands import resolve_intent
                        before_publish(resolve_intent(self.state, intent))
                    self._before_publish[future] = capture_before
        if refused is not None:
            if admission_failed:
                self._completion_finished(None)
            if continuation is not None:
                continuation(refused, None)
            return refused
        future.add_done_callback(self._completion_callback)
        return future

    def reliable_submit(self, command, *args, choice=None):
        """Teardown controls survive temporary backpressure and app lifetime."""
        result = Future()
        result.set_running_or_notify_cancel()
        with self._lock:
            if self._close_future is not None:
                result.set_exception(RuntimeError('session cleanup already closing'))
                return result
            self._reliable.append(result)
        def deliver():
            while True:
                try:
                    with self._lock:
                        accepted = self.owner.submit(command, *args, choice=choice)
                        self._pending.append((accepted, []))
                    accepted.add_done_callback(self._completion_callback)
                    completion = accepted.result()  # background helper only
                except Full:
                    time.sleep(.005)
                    continue
                except CancelledError:
                    continue
                except BaseException as error:
                    self.error = error
                    result.set_exception(error)
                    return
                else:
                    result.set_result(completion)
                    with self._lock:
                        self._reliable.remove(result)
                    return
        threading.Thread(target=deliver, name='legacy-reliable-cleanup', daemon=False).start()
        return result

    def then(self, future, continuation):
        with self._lock:
            for pending, callbacks in self._pending:
                if pending is future:
                    callbacks.append(lambda result, completion: continuation(result))
                    return future
        raise ValueError('continuation must be registered before main-loop drain')

    def drain(self):
        """Main-loop only: apply every FIFO delta, including zero-time controls."""
        self.display_changed = False
        owner_error = getattr(self.owner, 'error', None)
        if owner_error is not None:
            self.error = owner_error
        for future in tuple(self._saves):
            if future.done():
                self._saves.remove(future)
                try:
                    future.result()
                except BaseException as error:
                    self.error = error
        if not self._ready_applied:
            if not self.owner.ready.done():
                return 0
            try:
                initial = self.owner.ready.result()  # already done; never waits
            except BaseException as error:
                self.error = error
                self._ready_applied = True
                return 0
            if self._state is None:
                self._state = LegacyDisplayState(initial.legacy_display)
            else:
                self._state.publish(initial.legacy_display)
            self._ready_applied = True
            self.display_changed = True
        count = 0
        while True:
            with self._lock:
                if not self._pending or not self._pending[0][0].done():
                    break
                future, continuations = self._pending.popleft()
                before_publish = self._before_publish.pop(future, None)
            if future.cancelled():
                continue
            try:
                completion = future.result()  # guarded above; no blocking
                if before_publish is not None:
                    try:
                        before_publish()
                    except BaseException as error:
                        # Presentation feedback cannot discard an authoritative
                        # delta or break the following publication's base chain.
                        self.error = error
                delta = completion.snapshot.legacy_display
                from .core.ticker_transport import is_zero_time_control
                self.display_changed |= bool(delta.base is None or delta.fields or delta.cells
                                             or delta.removed or delta.layers or delta.removed_layers
                                             or continuations
                                             or completion.result.changed
                                             or not is_zero_time_control(completion.command, ()))
                if delta.generation != self._state._display_generation:
                    self._state = LegacyDisplayState(delta)
                else:
                    self._state.publish(delta)
            except BaseException as error:
                self.error = error
                for continuation in tuple(continuations):
                    continuation(ActionResult(False, str(error), {'owner_error': True}), None)
                continue
            for continuation in tuple(continuations):
                continuation(action_result(completion.result), completion)
            count += 1
        return count

    def start(self):
        return self.owner.start()

    def flush_pending_save(self):
        pass  # owner flushes by turn interval before publishing

    flush_pending_save_async = flush_pending_save

    def save_and_exit(self):
        """Legacy return-to-home save barrier; the owner remains available."""
        future = Future()
        future.set_running_or_notify_cancel()
        self._saves.append(future)
        future.add_done_callback(self._completion_callback)
        def save():
            while True:
                try:
                    accepted = self.owner.save()
                    accepted.result()  # durability helper only
                except (Full, CancelledError):
                    time.sleep(.005)
                    continue
                except BaseException as error:
                    self.error = error
                    future.set_exception(error)
                    return
                else:
                    future.set_result(None)
                    return
        threading.Thread(target=save, name='legacy-save-barrier', daemon=False).start()
        return future

    def close(self, *, save=True):
        """Durability runs in background; caller can await shutdown_future."""
        self.set_completion_wakeup(None)
        if self._close_future is None:
            result = self._close_future = Future()
            result.set_running_or_notify_cancel()
            def close():
                try:
                    try:
                        for cleanup in tuple(self._reliable):
                            cleanup.result()  # durability helper, never UI thread
                        for save_future in tuple(self._saves):
                            save_future.result()
                    finally:
                        self.owner.close(save=save)
                except BaseException as error:
                    self.error = error
                    result.set_exception(error)
                else:
                    result.set_result(None)
            threading.Thread(target=close, name='legacy-owner-close', daemon=False).start()
        return self._close_future


def independent_session(session, *, entered=False):
    """Transfer one initial world, keeping the actual DreamApp widget tree."""
    if isinstance(session, LegacyAsyncSession):
        return session
    from types import SimpleNamespace
    from .legacy_display import DisplayPublisher
    from .simulation_process import SimulationProcess
    if getattr(session.state.cells, 'store', None) is None:
        from .core.material_store import MaterialStore
        state = session.state
        state.cells = MaterialStore(state.cells, state.width, state.height).cells
    with session._action_lock:
        initial = SimpleNamespace(legacy_display=DisplayPublisher().build(session.state))
    owner = SimulationProcess(session.state, save_dir=session.manager.directory,
                              save_slot=session.manager.slot,
                              persistence_enabled=session.persistence_enabled,
                              include_legacy_display=True, start_entered=entered)
    return LegacyAsyncSession(owner, session.manager, initial=initial,
                              started=session.started, await_owner_ready=True)
