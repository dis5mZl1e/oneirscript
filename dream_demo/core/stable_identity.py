"""Deterministic per-object tokens for RNG seeding (headless simulation only).

The shipped game seeds several enemy behaviours with ``id(obj)`` — a memory
address. Within one process that is stable enough for play, but it differs
across processes and GC timings, so two runs of the same seed cannot be
compared action-by-action. Balance work needs exactly that comparison.

This module keeps the shipped behaviour untouched: ``token()`` returns
``id(obj)`` unless stable mode is explicitly enabled. The headless runner
enables it, and then the token is derived from data that the seed already
determines:

1. ``actor_uid`` — stable NPC identity (layer key + trade + ordinal);
2. ``id`` string — ``enemy-7`` / ``player``, assigned in deterministic spawn order;
3. a monotonic counter, assigned on first use (order is deterministic too).

Usage::

    from dream_demo.core import stable_identity
    stable_identity.enable()
    ...
    stable_identity.disable()
"""
from __future__ import annotations

import zlib
from typing import Any

_ENABLED = False
_counter = 0
_fallback: dict[int, int] = {}


def enable(value: bool = True) -> None:
    """Turn stable tokens on/off (off = the shipped ``id()`` behaviour)."""
    global _ENABLED
    _ENABLED = bool(value)


def enabled() -> bool:
    return _ENABLED


def reset() -> None:
    """Clear counter state; call once per simulated run."""
    global _counter
    _counter = 0
    _fallback.clear()


def token(obj: Any) -> int:
    """Seed component identifying ``obj`` for this run."""
    if not _ENABLED:
        return id(obj)
    uid = getattr(obj, "actor_uid", "") or ""
    if uid:
        return zlib.crc32(str(uid).encode("utf-8"))
    ident = getattr(obj, "id", "")
    if isinstance(ident, str) and ident:
        return zlib.crc32(ident.encode("utf-8"))
    global _counter
    key = id(obj)
    value = _fallback.get(key)
    if value is None:
        _counter += 1
        value = 0x10000 + _counter
        _fallback[key] = value
    return value
