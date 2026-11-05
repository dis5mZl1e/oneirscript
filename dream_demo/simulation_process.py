"""Independent simulation process with FIFO requests and snapshot page deltas.

The initial world crosses once. Normal commands return immutable display data;
export_state is an explicitly expensive compatibility barrier, never rendering.
"""
from collections import deque
from concurrent.futures import Future
from copy import deepcopy
from dataclasses import replace
import multiprocessing
import os
from queue import Full
import threading
import time

from .simulation_worker import SimulationWorker, WorkerMetrics, _fence_tutorial_command
from .snapshot_transport import encode_snapshot, decode_snapshot


def _serve(connection, state, settings):
    """Spawn entry: no UI objects or live client references enter the owner."""
    worker = None
    try:
        from .persistence import SaveManager
        save_dir = settings.pop('save_dir')
        save_slot = settings.pop('save_slot', 1)
        factory = None if save_dir is None else lambda: SaveManager(save_dir, slot=save_slot)
        worker = SimulationWorker(state, manager_factory=factory, **settings)
        previous = worker.ready.result()
        connection.send(('ready', encode_snapshot(previous)))
        while True:
            kind, payload = connection.recv()
            if kind == 'close':
                worker.close(save=payload)
                connection.send(('closed', None))
                return
            if kind == 'command':
                command, args, choice, pickup = payload
                completion = worker._submit_admitted(command, *args, choice=choice,
                                                     auto_pickup=pickup).result()
                packet = encode_snapshot(completion.snapshot, previous)
                previous = completion.snapshot
                connection.send(('completion', (replace(completion, snapshot=None), packet,
                                                 worker.metrics)))
                worker.poll()
            elif kind == 'start':
                worker.start().result()
                connection.send(('result', None))
            elif kind == 'save':
                worker.save().result()
                connection.send(('result', None))
            elif kind == 'export':
                connection.send(('result', worker.export_state().result()))
            else:
                raise ValueError(f'unknown process request: {kind}')
    except BaseException as error:
        try:
            connection.send(('error', f'{type(error).__name__}: {error}'))
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        if worker is not None:
            try:
                worker.close(save=False)
            except BaseException:
                pass
        connection.close()


class SimulationProcess:
    """Bounded asynchronous owner implementing the snapshot client worker API."""
    def __init__(self, state, *, save_dir=None, persistence_enabled=False,
                 tick_seconds=1 / 30, queue_capacity=64, page_bytes=4096,
                 include_legacy_display=False, start_entered=True, save_slot=1):
        if type(queue_capacity) is not int or queue_capacity < 1:
            raise ValueError('queue_capacity must be positive')
        if persistence_enabled and save_dir is None:
            raise ValueError('persistent simulation requires save_dir')
        self.ready = Future()
        self._condition = threading.Condition()
        self._capacity = queue_capacity
        self._requests = deque()
        self._completions = deque(maxlen=queue_capacity)
        self._pair = (None, None)
        self._metrics = WorkerMetrics(0, 0, 0, 0)
        self._dropped = 0
        self._error = None
        self._closing = False
        self._close_future = None
        self.client_pid = os.getpid()
        context = multiprocessing.get_context('spawn')
        self._connection, remote = context.Pipe()
        settings = dict(save_dir=None if save_dir is None else str(save_dir),
                        persistence_enabled=persistence_enabled, tick_seconds=tick_seconds,
                        queue_capacity=queue_capacity, page_bytes=page_bytes,
                        include_legacy_display=include_legacy_display,
                        start_entered=start_entered, save_slot=save_slot)
        self._process = context.Process(target=_serve, args=(remote, state, settings),
                                        name='simulation-process')
        try:
            self._process.start()
        except BaseException:
            self._connection.close()
            raise
        finally:
            remote.close()
        self.owner_pid = self._process.pid
        self._thread = threading.Thread(target=self._communicate,
                                        name='simulation-process-transport', daemon=False)
        self._thread.start()

    def _enqueue(self, kind, payload=None, *, block=False, timeout=None):
        future = Future()
        deadline = None if timeout is None else time.perf_counter() + timeout
        with self._condition:
            while True:
                if self._error is not None:
                    raise self._error
                if self._closing:
                    raise RuntimeError('simulation process is closed')
                from .core.ticker_transport import ticker_backpressured
                pressure = (kind == 'command' and
                            ticker_backpressured(self._pair[1], payload[0], payload[1]))
                if len(self._requests) < self._capacity and not pressure:
                    break
                remaining = None if deadline is None else deadline - time.perf_counter()
                if not block or remaining is not None and remaining <= 0:
                    raise Full('ticker backlog is full' if pressure else
                               'simulation command queue is full')
                self._condition.wait(remaining)
            self._requests.append((kind, payload, future, time.perf_counter()))
            self._condition.notify_all()
        return future

    def submit(self, command, *args, choice=None, auto_pickup=False, block=False, timeout=None):
        args = _fence_tutorial_command(command, args, self.snapshot_pair()[1])
        return self._enqueue('command', deepcopy((command, args, choice, auto_pickup)),
                             block=block, timeout=timeout)

    def start(self):
        return self._enqueue('start')

    def save(self, *, block=False, timeout=None):
        return self._enqueue('save', block=block, timeout=timeout)

    def export_state(self, *, block=False, timeout=None):
        return self._enqueue('export', block=block, timeout=timeout)

    def _receive(self):
        kind, payload = self._connection.recv()
        if kind == 'error':
            raise RuntimeError(f'simulation process failed: {payload}')
        return kind, payload

    def _communicate(self):
        active = None
        try:
            kind, packet = self._receive()
            if kind != 'ready':
                raise RuntimeError('simulation process did not publish initial snapshot')
            initial = decode_snapshot(packet)
            with self._condition:
                self._pair = (None, initial)
                self._condition.notify_all()
            self.ready.set_result(initial)
            while True:
                with self._condition:
                    while not self._requests:
                        # A dead idle child cannot send another notification.
                        # Bound the health wait without advancing simulation.
                        self._condition.wait(.5)
                        if not self._requests and self._process.exitcode is not None:
                            raise RuntimeError('simulation process exited while idle')
                    request = self._requests.popleft()
                    self._condition.notify_all()
                kind, payload, active, submitted_at = request
                if not active.set_running_or_notify_cancel():
                    active = None
                    continue
                self._connection.send((kind, payload))
                response, value = self._receive()
                if kind == 'close':
                    if response != 'closed':
                        raise RuntimeError('simulation shutdown acknowledgement missing')
                    active.set_result(None)
                    active = None
                    return
                if kind == 'command':
                    if response != 'completion':
                        raise RuntimeError('simulation command response missing')
                    completion, packet, metrics = value
                    with self._condition:
                        snapshot = decode_snapshot(packet, self._pair[1])
                        completion = replace(completion, snapshot=snapshot, submitted_at=submitted_at)
                        self._pair = (self._pair[1], snapshot)
                        self._metrics = metrics
                        if len(self._completions) == self._capacity:
                            self._dropped += 1
                        self._completions.append(completion)
                        self._condition.notify_all()
                    active.set_result(completion)
                elif response == 'result':
                    active.set_result(value)
                else:
                    raise RuntimeError('invalid simulation process response')
                active = None
        except BaseException as error:
            with self._condition:
                self._error = error
                self._closing = True
                queued = tuple(self._requests)
                self._requests.clear()
                self._condition.notify_all()
            if not self.ready.done():
                self.ready.set_exception(error)
            if active is not None and not active.done():
                active.set_exception(error)
            for _, _, future, _ in queued:
                if future.set_running_or_notify_cancel():
                    future.set_exception(error)
        finally:
            self._connection.close()

    def poll(self):
        with self._condition:
            result = tuple(self._completions)
            self._completions.clear()
            return result

    def snapshot_pair(self):
        with self._condition:
            return self._pair

    @property
    def error(self):
        """Terminal owner failure, observable without issuing another command."""
        with self._condition:
            return self._error

    @property
    def metrics(self):
        with self._condition:
            return self._metrics

    @property
    def dropped_completions(self):
        with self._condition:
            return self._dropped

    @property
    def is_alive(self):
        return self._process.is_alive()

    def close(self, *, save=True, timeout=None):
        if threading.current_thread() is self._thread:
            raise RuntimeError('cannot close process from its transport thread')
        started = time.perf_counter()
        with self._condition:
            if not self._closing:
                self._closing = True
                self._close_future = Future()
                # Closing is a durability barrier after every accepted request.
                self._requests.append(('close', save, self._close_future, started))
                self._condition.notify_all()
        self._thread.join(timeout)
        remaining = None if timeout is None else max(0, timeout - (time.perf_counter() - started))
        self._process.join(remaining)
        if self._thread.is_alive() or self._process.is_alive():
            raise TimeoutError('simulation process shutdown timed out; drain remains active')
        if self._error is not None:
            raise self._error

