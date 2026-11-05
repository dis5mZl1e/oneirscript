"""Display-local clocks and occurrence cursors; never mutate world facts."""
from collections import deque
from concurrent.futures import CancelledError, Future
from queue import Full
from uuid import uuid4

class PresentationEvents:
    def __init__(self):
        self._state = None
        self._context = None
        self._explosion_sequence = 0
        self.explosion_cells = frozenset()
        self.explosion_blasts = ()
        self.explosion_age = 0
        self._ticker_generation = None
        self._ticker_sequence = -1
        self._ticker_revision = None
        self.pending_tickers = deque()
        self._pending_ticker_ids = deque()
        self._ticker_seen = set()
        self.ticker_acknowledgement = None
        self.ticker_consumer_token = uuid4().hex
        self._ticker_registered_generation = None
        self._ticker_acknowledgements = deque()
        self._ticker_operations = {}
        self._ticker_owner_session = self._ticker_owner_state = None
        self._world_token = None
        self._ticker_values = ((), ())

    @property
    def explosion_signature(self):
        return self.explosion_cells, self.explosion_blasts, self.explosion_age

    def sync(self, state):
        from ..simulation_worker import SimulationSnapshot
        if isinstance(state, SimulationSnapshot):
            facts = state.presentation
            if facts is None:
                return
            stream = ('snapshot', facts.stream)
            if self._state != stream:
                self.__init__()
                self._state = stream
            self._sync_explosions((state.map_generation, state.layer_key),
                                  facts.map_identity, facts.explosions, facts.recovery)
            self._sync_ticker_values(facts.ticker_generation, facts.ticker_revision,
                                     facts.ticker_ids, facts.ticker_notes,
                                     facts.ticker_retained_ids)
            return
        world_token = getattr(state, '_command_context_token', None)
        if (self._state is not state or
                (self._world_token is not None and world_token != self._world_token)):
            self.__init__()
            self._state = state
        # A synchronous owner may assign its first identity during registration.
        # That initialization is not a replacement world or a new subscriber.
        self._world_token = world_token
        # Detached rows change identity on every incremental publication. Their
        # owner generation identifies the map for the entire effect lifetime.
        context = (getattr(state, '_display_generation', id(state.cells)), state.layer_key())
        self._sync_explosions(context,
                              getattr(state, '_presentation_map_identity', id(state.cells)),
                              getattr(state, '_presentation_explosions', ()),
                              getattr(state, '_presentation_explosion_recovery', None))
        self._sync_tickers(state)

    def _sync_explosions(self, context, map_identity, events, recovery):
        if self._context is not None and context != self._context:
            self.explosion_cells = frozenset()
            self.explosion_blasts = ()
            self.explosion_age = 0
            # The occurrence cursor survives map changes; old facts cannot replay,
            # while a new blast produced on the incoming map remains eligible.
        self._context = context
        if events and events[0].sequence > self._explosion_sequence + 1 and recovery is not None:
            if (recovery.map_identity, recovery.layer) == (
                    map_identity, context[1]):
                cells = frozenset(cell for cell, seq in recovery.cells
                                  if seq > self._explosion_sequence)
                blasts = tuple(blast for seq, blast in recovery.blasts
                               if seq > self._explosion_sequence)
                if cells:
                    self.explosion_cells |= cells
                    self._merge_blasts(blasts)
                    self.explosion_age = 0
                self._explosion_sequence = recovery.sequence
        for event in events:
            if event.sequence <= self._explosion_sequence:
                continue
            self._explosion_sequence = event.sequence
            if (event.map_identity, event.layer) != (
                    map_identity, context[1]):
                continue
            self.explosion_cells |= event.cells
            self._merge_blasts((event.blast,))
            self.explosion_age = 0

    def _merge_blasts(self, blasts):
        # At a shared center the largest radius wins every distance ratio,
        # including cells added by later chain events. Unique centers are
        # bounded by map area and preserve the authored nearest-ring colors.
        centers = {blast[:2]: blast for blast in self.explosion_blasts}
        for blast in blasts:
            center = blast[:2]
            if center not in centers or blast[2] > centers[center][2]:
                centers[center] = blast
        self.explosion_blasts = tuple(centers.values())

    def _sync_tickers(self, state):
        notes = state.ticker_notes
        generation = getattr(notes, 'generation', id(notes))
        revision = getattr(notes, 'revision', None)
        # Read the existing ids without populating the source's lazy tuple cache.
        identities = getattr(notes, '_ids', None)
        if identities is None:
            identities = getattr(notes, 'occurrence_ids', range(len(notes)))
        self._sync_ticker_values(generation, revision, identities, notes,
                                 getattr(notes, '_ticker_retained_ids', None))

    def _sync_ticker_values(self, generation, revision, identities, notes, retained=None):
        if generation != self._ticker_generation:
            self.pending_tickers.clear()
            self._pending_ticker_ids.clear()
            self._ticker_seen.clear()
            self.ticker_acknowledgement = None
            self._ticker_registered_generation = None
            self._ticker_acknowledgements.clear()
            # Old commands remain fenced by the owner's generation. The view
            # must not retain Futures it will never poll again.
            self._ticker_operations.clear()
            self._ticker_generation = generation
            self._ticker_sequence = -1
            self._ticker_revision = None
        if revision is not None and revision == self._ticker_revision:
            self._refill_tickers()
            return
        self._ticker_revision = revision
        identities = tuple(identities)
        # Deleted/pruned occurrences cannot reappear with the same identity.
        # Keep dedup bookkeeping proportional to the retained owner backlog.
        self._ticker_seen.intersection_update(identities if retained is None else retained)
        self._ticker_values = identities, notes
        self._refill_tickers()

    def _refill_tickers(self):
        from ..core.ticker_transport import TICKER_PAGE_SIZE
        identities, notes = self._ticker_values
        for identity, note in zip(identities, notes):
            if len(self.pending_tickers) >= TICKER_PAGE_SIZE:
                break
            if identity not in self._ticker_seen:
                self.pending_tickers.append(note)
                self._pending_ticker_ids.append(identity)
                self._ticker_seen.add(identity)
                self._ticker_sequence = max(identity, self._ticker_sequence)

    @property
    def ticker_generation(self):
        return self._ticker_generation

    @property
    def ticker_pending_acknowledgements(self):
        return tuple(self._ticker_acknowledgements)

    def confirm_ticker_acknowledgement(self, generation, identity):
        acknowledgement = (generation, identity)
        if acknowledgement in self._ticker_acknowledgements:
            self._ticker_acknowledgements.remove(acknowledgement)

    def advance(self, state):
        self.sync(state)
        active = bool(self.explosion_cells)
        if active:
            self.explosion_age += 1
            if self.explosion_age > 6:
                self.explosion_cells = frozenset()
                self.explosion_blasts = ()
                self.explosion_age = 0
        return active

    def pop_ticker(self):
        if not self.pending_tickers:
            self._refill_tickers()
            if not self.pending_tickers:
                return None
        self.ticker_acknowledgement = (self._ticker_generation,
                                       self._pending_ticker_ids.popleft())
        self._ticker_acknowledgements.append(self.ticker_acknowledgement)
        return self.pending_tickers.popleft()


def presentation_events(app, state):
    events = getattr(app, '_presentation_events', None)
    if events is not None and events._ticker_owner_state is not None:
        if (events._ticker_owner_session is not app.session
                or events._ticker_owner_state is not state):
            release_presentation_events(app)
            events = None
    if events is None:
        events = app._presentation_events = PresentationEvents()
    events.sync(state)
    return events


def display_next_ticker(app, state, events):
    """Deliver one legacy mounted notice; only the owner prunes its source.

    Failed owner commands keep their exact ACKs for a later frame. Rendering
    failure leaves the notice pending and never acknowledges its occurrence.
    """
    from ..core.presentation_control import submit_presentation

    def send(verb, *args):
        key = verb, args
        try:
            result = events._ticker_operations.get(key)
            if result is None:
                result = submit_presentation(app.session, state, verb,
                                             events.ticker_consumer_token, *args)
            if isinstance(result, Future):
                if not result.done():
                    events._ticker_operations[key] = result
                    return None
                events._ticker_operations.pop(key, None)
                result = result.result()  # done check above: never blocks
                result = getattr(result, 'result', result)
            return result
        except (CancelledError, RuntimeError, OSError, Full):
            events._ticker_operations.pop(key, None)
            return None

    def accepted(result):
        return result is not None and (result.changed or dict(result.data).get('ticker_accepted'))

    generation = events.ticker_generation
    events._ticker_owner_session, events._ticker_owner_state = app.session, state
    if events._ticker_registered_generation != generation:
        if not accepted(send('ticker_register', generation)):
            return False
        events._ticker_registered_generation = generation

    def acknowledge_pending():
        for ack_generation, identity in events.ticker_pending_acknowledgements:
            if not accepted(send('ticker_ack', ack_generation, identity)):
                break
            events.confirm_ticker_acknowledgement(ack_generation, identity)

    acknowledge_pending()
    from ..core.ticker_transport import TICKER_PAGE_SIZE
    if len(events.ticker_pending_acknowledgements) >= TICKER_PAGE_SIZE:
        # A failed/slower owner must not accumulate an unbounded set of display
        # receipts. Keep retrying existing exact ACKs before consuming more.
        return False
    if not events.pending_tickers:
        return False
    if app._push_header_ticker(events.pending_tickers[0]) is False:
        return False
    events.pop_ticker()
    acknowledge_pending()
    return True


def release_presentation_events(app):
    """Queue one atomic final ACK/release on the original owner before close.

    Async owners retain/retry cleanup through queue backpressure independently
    of the widget lifetime, and close drains these submissions before shutdown.
    No wait or authoritative list mutation occurs on the display thread.
    """
    from ..core.presentation_control import submit_presentation
    events = getattr(app, '_presentation_events', None)
    if events is None:
        return ()
    session, state = events._ticker_owner_session, events._ticker_owner_state
    futures = []
    if session is not None and state is not None and events.ticker_generation is not None:
        try:
            identities = tuple(identity for generation, identity in
                               events.ticker_pending_acknowledgements
                               if generation == events.ticker_generation)
            futures.append(submit_presentation(session, state, 'ticker_cleanup',
                getattr(state, '_command_context_token', None),
                events.ticker_consumer_token, events.ticker_generation, *identities))
        except (CancelledError, RuntimeError, OSError, Full) as error:
            # Synchronous/test owners may fail submission. Keep the view and
            # its exact ACKs available for retry and surface the failure without
            # aborting the remaining unmount/navigation cleanup.
            failure = Future()
            failure.set_exception(error)
            return (failure,)
    app._presentation_events = None
    return tuple(futures)
