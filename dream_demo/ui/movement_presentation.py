"""Pure presentation-time interpolation for grid movement.

The world position remains integral and authoritative. This helper only samples
where the image renderer should draw the player between two committed moves.
"""
from __future__ import annotations


class MovementPresentation:
    """Sample one replaceable, clamped linear transition between map positions."""

    def __init__(self) -> None:
        self._source = (0.0, 0.0)
        self._target = (0.0, 0.0)
        self._started_at = 0.0
        self._duration = 0.0

    def begin(self, source: tuple[float, float], target: tuple[int, int],
              started_at: float, duration: float) -> None:
        self._source = (float(source[0]), float(source[1]))
        self._target = (float(target[0]), float(target[1]))
        self._started_at = float(started_at)
        self._duration = max(0.0, float(duration))

    def sample(self, now: float) -> tuple[float, float]:
        """Return the clamped linear display position at monotonic time ``now``."""
        if self._duration <= 0.0:
            return self._target
        fraction = min(1.0, max(0.0, (float(now) - self._started_at) / self._duration))
        return tuple(
            self._source[index]
            + (self._target[index] - self._source[index]) * fraction
            for index in range(2)
        )

    def is_active(self, now: float) -> bool:
        return self._duration > 0.0 and float(now) < self._started_at + self._duration

    @property
    def target(self) -> tuple[float, float]:
        return self._target

    def reset(self, position: tuple[int, int]) -> None:
        """Drop interpolation and align directly with the authoritative location."""
        self._source = (float(position[0]), float(position[1]))
        self._target = self._source
        self._started_at = 0.0
        self._duration = 0.0
