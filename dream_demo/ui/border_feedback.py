
"""Short-lived border feedback with one priority queue (2026-10-18 docs §9.6).

Priority: danger > interaction > reward > focus. Feedback only changes border
colors for its envelope; geometry, title strip and click areas never move. When
the envelope ends the normal theme phase resumes immediately (no frozen frame).
Events are deduplicated by source while active and bounded; they never touch
world time or the save file.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

PRIORITY = {'danger': 4, 'interaction': 3, 'reward': 2, 'focus': 1}
DURATIONS = {'danger': .55, 'interaction': .30, 'reward': 1.0, 'focus': .25}
COLORS = {'danger': '#ff5d5d', 'interaction': '#7ad0ff',
          'reward': '#ffd166', 'focus': '#c8f0e0'}
MAX_EVENTS = 8


@dataclass(frozen=True)
class BorderFeedbackEvent:
    kind: str
    start: float
    duration: float
    source: str = ''
    priority: int = 0

    def active(self, now: float) -> bool:
        return 0.0 <= now - self.start < self.duration

    def progress(self, now: float) -> float:
        return max(0.0, min(1.0, (now - self.start) / max(0.01, self.duration)))


def _envelope(kind: str, progress: float) -> float:
    if progress <= 0.0 or progress >= 1.0:
        return 0.0
    if kind == 'danger':
        # Two quick pulses, not a sustained red screen.
        pulse = 0.55 + 0.45 * math.cos(progress * math.tau * 2)
        return max(0.0, pulse * (1.0 - progress))
    if kind == 'interaction':
        return (1.0 - progress) ** .6
    if kind == 'reward':
        return math.sin(math.pi * min(1.0, progress * 1.25)) * (1.0 - progress * .35)
    return (1.0 - progress) * .8


class BorderFeedback:
    def __init__(self) -> None:
        self.events: list[BorderFeedbackEvent] = []
        self._last_source: dict[str, float] = {}

    def push(self, kind: str, now: float, *, source: str = '',
             duration: float | None = None) -> BorderFeedbackEvent | None:
        if kind not in PRIORITY:
            return None
        duration = float(DURATIONS[kind] if duration is None else duration)
        # 连续同类事件合并：同一来源在自身窗口内不叠加第二份。
        for event in self.events:
            if (event.kind == kind and event.source == source and source
                    and event.active(now)):
                return event
        born = BorderFeedbackEvent(kind=kind, start=float(now), duration=duration,
                                  source=source, priority=PRIORITY[kind])
        self.events.append(born)
        if len(self.events) > MAX_EVENTS:
            self.events = sorted(self.events, key=lambda e: (e.priority, e.start))[-MAX_EVENTS:]
        return born

    def prune(self, now: float) -> None:
        self.events = [event for event in self.events if now - event.start < event.duration]

    def sample(self, now: float) -> tuple[str, float] | None:
        """Return (kind, strength 0..1) for the highest-priority active event."""
        self.prune(now)
        active = [event for event in self.events if event.active(now)]
        if not active:
            return None
        chosen = max(active, key=lambda event: (event.priority, event.start))
        strength = _envelope(chosen.kind, chosen.progress(now))
        if strength <= 0.0:
            return None
        return chosen.kind, min(1.0, strength)

    def color(self, kind: str, now: float) -> str:
        return COLORS.get(kind, '#ffffff')

    def reset(self) -> None:
        self.events.clear()
        self._last_source.clear()


def blend_feedback_color(base: str, kind: str, strength: float) -> str:
    from .deco import mix_hex
    return mix_hex(base, COLORS.get(kind, base), max(0.0, min(.85, strength)))
