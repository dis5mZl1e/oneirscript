"""Finite zero-time presentation commands executed under GameSession's lock.

Layer keys protect queued hover/dialog operations against cross-layer delivery.
UI objects, entities and arbitrary attribute names never enter the wire surface.
"""
from __future__ import annotations

from typing import Literal

from .entities import ActionResult
from ..i18n import tr

PresentationVerb = Literal['hover', 'clear_hover', 'layer_cleanup', 'buzzing_echo',
                           'toggle_buzzing_echo', 'talk_npc', 'no_assist_target',
                           'ticker_register', 'ticker_ack', 'ticker_release', 'ticker_cleanup']


def submit_presentation(session, state, verb: PresentationVerb, *args: object) -> ActionResult:
    """Adapt a legacy view's layer to the primitive owner command surface."""
    if verb == 'ticker_cleanup' and hasattr(session, 'reliable_submit'):
        return session.reliable_submit('presentation_control', state.layer_key(), verb, *args)
    return session.apply('presentation_control', state.layer_key(), verb, *args)


def apply_presentation(state, expected_layer: str | None = None,
                       verb: PresentationVerb | None = None, *args: object) -> ActionResult:
    if verb == 'ticker_cleanup':
        return _cleanup_ticker(state, expected_layer, args)
    if (type(expected_layer) is not str or expected_layer != state.layer_key()
            or type(verb) is not str
            or any(type(value) not in (str, int, bool) for value in args)):
        return ActionResult(False)
    changed = durable = False
    ticker_accepted = False
    message = ''
    if verb in ('ticker_register', 'ticker_ack', 'ticker_release'):
        expected_count = 3 if verb == 'ticker_ack' else 2
        if (len(args) != expected_count or type(args[0]) is not str or not args[0]
                or any(type(value) is not int for value in args[1:])):
            return ActionResult(False)
        from .presentation_events import TickerHistory
        notes = state.ticker_notes
        if not isinstance(notes, TickerHistory):
            return ActionResult(False)
        token, generation = args[:2]
        if generation == notes.generation:
            if verb == 'ticker_register':
                from .command_context import command_context_token
                command_context_token(state)
                ticker_accepted = True
            elif token in notes._consumers:
                ticker_accepted = (verb == 'ticker_release'
                                   or 0 <= args[2] < notes._next)
        if verb == 'ticker_register':
            changed = notes.register_consumer(*args)
        elif verb == 'ticker_ack':
            changed = notes.acknowledge(*args)
        else:
            changed = notes.release_consumer(*args)
    elif verb == 'hover' and len(args) == 2 and all(type(v) is int for v in args):
        x, y = args
        if not (0 <= x < state.width and 0 <= y < state.height):
            return ActionResult(False)
        changed = state.hover_target != (x, y)
        state.hover_target = x, y
    elif verb == 'clear_hover' and not args:
        changed = state.hover_target is not None
        state.hover_target = None
    elif verb == 'layer_cleanup' and not args:
        changed = any(value is not None for value in
                      (state.hover_target, state.pending_npc_id,
                       state.pending_event_id, state.pending_event_uid))
        state.hover_target = None
        state.pending_npc_id = None
        state.pending_event_id = None
        state.pending_event_uid = None
    elif verb == 'buzzing_echo' and len(args) == 1 and type(args[0]) is bool:
        changed = durable = state.buzzing_echo_enabled != args[0]
        state.buzzing_echo_enabled = args[0]
    elif verb == 'toggle_buzzing_echo' and not args:
        state.buzzing_echo_enabled = not state.buzzing_echo_enabled
        changed = durable = True
    elif verb == 'talk_npc' and len(args) == 1 and type(args[0]) is str:
        npc = next((entity for entity in state.enemies if entity.id == args[0]
                    and entity.relation == '稳定意识' and entity.integrity > 0), None)
        if npc is None:
            return ActionResult(False)
        # Legacy mouse dialogue has no distance or time cost. Only keeper
        # acknowledgment can modify gameplay; pending selection is transient.
        gate_before = state.realm_gate_open
        state.talk_toy_keeper(npc)
        # talk_toy_keeper acknowledges boards only on the closed -> open edge.
        durable = gate_before != state.realm_gate_open
        state.pending_npc_id = npc.id
        message = tr('{name}：「请讲。」', name=tr(npc.label))
        state.messages.append(message)
        changed = True
    elif verb == 'no_assist_target' and not args:
        message = tr('视野内没有可以辅助瞄准的失控意识。')
        state.messages.append(message)
    data = {'state_changed': bool(durable)}
    if verb in ('ticker_register', 'ticker_ack', 'ticker_release'):
        data['ticker_accepted'] = ticker_accepted
    return ActionResult(changed, message, data)


def _cleanup_ticker(state, expected_layer, args):
    """Dispose one owned subscriber atomically, even after a queued map change.

    World identity and the unguessable subscription token replace the layer
    fence only for this final cleanup. An obsolete generation cannot ACK any
    current occurrence, but its disposed subscriber must still be removed.
    """
    from .presentation_events import TickerHistory
    if (type(expected_layer) is not str or len(args) < 3
            or type(args[0]) is not int or args[0] <= 0
            or args[0] != getattr(state, '_command_context_token', None)
            or type(args[1]) is not str or not args[1]
            or any(type(value) is not int for value in args[2:])):
        return ActionResult(False)
    world_token, token, generation, *identities = args
    notes = state.ticker_notes
    if not isinstance(notes, TickerHistory) or token not in notes._consumers:
        return ActionResult(False)
    if generation == notes.generation:
        for identity in identities:
            # acknowledge validates the exact occurrence; no high-water ACK.
            notes.acknowledge(token, generation, identity)
    changed = notes.release_consumer(token, notes.generation)
    return ActionResult(changed, data={'ticker_accepted': True, 'state_changed': False})
