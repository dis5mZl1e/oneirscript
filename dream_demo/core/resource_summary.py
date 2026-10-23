"""19-day §18: shared noise/chaos read-only summary (no new mechanics)."""
from __future__ import annotations

from dataclasses import dataclass

from ..data.tamper_schema import CHAOS_MAX

NOISE_DISPLAY_MAX = 20


@dataclass(frozen=True)
class NoiseChaosSummary:
    noise_radius: int | None
    noise_max: int
    chaos: int
    chaos_max: int
    noise_unknown: bool = False

    def noise_text(self) -> str:
        if self.noise_unknown or self.noise_radius is None:
            return f"—/{self.noise_max}"
        return f"{self.noise_radius}/{self.noise_max}"

    def chaos_text(self) -> str:
        return f"{self.chaos}/{self.chaos_max}"


def noise_chaos_summary(state, preview: dict | None = None) -> NoiseChaosSummary:
    """Read the one shared footstep preview and the settled chaos value.

    The noise denominator is a fixed display scale, not a maximum hearing range;
    chaos reads the real settled value/cap. This function never pulses sound,
    advances time, or consumes randomness.
    """
    if preview is None:
        from . import sound_preview
        preview = sound_preview.footstep_preview(state)
    radius = preview.get("radius")
    unknown = radius is None
    if preview.get("silent"):
        radius = 0
    elif radius is not None:
        radius = max(0, int(radius))
    chaos = max(0, min(int(CHAOS_MAX), int(getattr(state, "chaos", 0) or 0)))
    return NoiseChaosSummary(
        noise_radius=radius,
        noise_max=NOISE_DISPLAY_MAX,
        chaos=chaos,
        chaos_max=int(CHAOS_MAX),
        noise_unknown=unknown,
    )
