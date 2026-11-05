"""Lossless ticker windows and admission pressure for asynchronous owners.

The limit stops NEW producers. Already accepted FIFO actions still drain, so
the retained backlog may exceed it by that finite command burst. A single
authored action can itself produce an arbitrary burst; this is not a byte cap.
"""
from dataclasses import dataclass

TICKER_PAGE_SIZE = 256
TICKER_BACKLOG_LIMIT = 1024


@dataclass(frozen=True)
class TickerWindow:
    generation: int
    revision: int
    identities: tuple
    notes: tuple
    retained: tuple
    backlog: int


def ticker_window(notes):
    return TickerWindow(notes.generation, notes.revision,
                        tuple(notes._ids[:TICKER_PAGE_SIZE]),
                        tuple(notes[:TICKER_PAGE_SIZE]),
                        notes.occurrence_ids, len(notes))


def is_zero_time_control(command, args):
    """Finite owner controls bypass gameplay admission/cadence, never FIFO."""
    if command == 'legacy_intent':
        from ..legacy_commands import LegacyIntent
        if len(args) == 1 and type(args[0]) is LegacyIntent:
            command = args[0].command
    # These finite controls do not execute normal time-advancing rule stages.
    # They must remain usable to drain/replace the world and leave the game.
    return command in ('presentation_control', 'ui_control',
                       'catalog_control', 'tutorial_view')


def ticker_backpressured(snapshot, command, args):
    if snapshot is None or snapshot.presentation is None:
        return False
    facts = snapshot.presentation
    if max(facts.ticker_backlog, len(facts.ticker_notes)) < TICKER_BACKLOG_LIMIT:
        return False
    return not is_zero_time_control(command, args)
