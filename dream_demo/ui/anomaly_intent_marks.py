"""Compact same-cell intent marks: one shared mapping for both map backends."""
from __future__ import annotations

from time import monotonic

from ..core.anomaly_intents import LIFETIME, PRIORITY, intent_cells

# Design §5 initial palette; text and glyph carry the meaning, colour only aids it.
COLORS = {
    "suspect": "#E7BF69",
    "investigate": "#E7BF69",
    "chase": "#ED936A",
    "lost": "#91AEC8",
    "flee": "#73C9B4",
    "windup_start": "#C4A0EA",
    "windup_broken": "#D8DFE8",
    "recover": "#A39BB5",
}

# Reuse existing semantic keys; no new private-use code point is invented here.
ICON_KEYS = {
    "suspect": "alert.suspicious",
    "investigate": "alert.suspicious",
    "chase": "alert.tracking",
    "lost": "alert.unaware",
    "flee": "portent.spooked",
    "windup_start": "portent.charged",
    "windup_broken": "tamper.break",
    "recover": "attribute.ability.cooldown_turns",
}

# The corner badge is smaller than a cell and must read without the PUA icon font.
BADGE_GLYPHS = {
    "suspect": "?",
    "investigate": "?",
    "chase": "!",
    "lost": "…",
    "flee": "»",
    "windup_start": "▲",
    "windup_broken": "×",
    "recover": "↺",
}

LABELS = {
    "suspect": "开始怀疑",
    "investigate": "开始调查",
    "chase": "开始追踪",
    "lost": "失去目标",
    "flee": "开始逃离",
    "windup_start": "开始蓄力",
    "windup_broken": "蓄力被打断",
    "recover": "恢复硬直",
}


def intent_icon(kind: str) -> str:
    """Compact badge mark; stable without the optional PUA icon font."""
    return BADGE_GLYPHS[kind]


# Design §6.1: quick brighten, brief hold, gentle fade inside one LIFETIME.
RAMP_IN = 0.15
HOLD_UNTIL = 0.6


def badge_alpha(elapsed: float, animated: bool = True) -> float:
    """Opacity for a badge that started ``elapsed`` seconds ago.

    With animation turned off the mark stays fully opaque for the same
    duration and still disappears by itself (§6.1). The ramp is quantised to
    quarter steps so one badge changes the map frame signature a handful of
    times instead of every repaint (§10.6: no whole-image rebuild per frame).
    """
    if not animated:
        return 1.0
    if elapsed <= 0.0:
        return 0.5
    if elapsed >= LIFETIME:
        return 0.0
    if elapsed < RAMP_IN:
        value = 0.35 + (elapsed / RAMP_IN) * 0.65
    elif elapsed < HOLD_UNTIL:
        value = 1.0
    else:
        value = (LIFETIME - elapsed) / (LIFETIME - HOLD_UNTIL)
    return max(0.25, round(value * 4) / 4)


# Design §6.3: when several anomalies switch in the same action, the decorative
# fade is what gets cut, never the event itself. Only this many badges keep the
# brighten/hold/fade ramp; the rest are shown as static short marks that expire
# on the same clock. Every extra animated badge makes the image frame signature
# change again, so the budget bounds how often the map has to be re-composed.
ANIMATED_BADGE_MAX = 3


def _urgency(state, cell: tuple[int, int], kind: str) -> tuple[int, int]:
    """Sort key: most dangerous first, then the one closest to the player."""
    player = getattr(state, "player", None)
    distance = 0 if player is None else max(
        abs(cell[0] - player.x), abs(cell[1] - player.y))
    return (PRIORITY[kind], distance)


def animated_cells(state, now: float | None = None,
                   budget: int = ANIMATED_BADGE_MAX) -> set[tuple[int, int]]:
    """The cells allowed to run the fade, ranked by danger then proximity."""
    cells = intent_cells(state, now)
    if budget <= 0 or not cells:
        return set()
    return set(sorted(cells,
                      key=lambda cell: _urgency(state, cell, cells[cell][0]))[:budget])


def intent_marks(state, now: float | None = None, *,
                 animated: bool = True,
                 budget: int = ANIMATED_BADGE_MAX,
                 include_chase: bool = True) -> dict[tuple[int, int], tuple[str, str, str, float]]:
    """cell -> (kind, glyph, colour, alpha) for live badges of visible anomalies.

    2026-10-22 玩家要求：追踪（chase）是最高频、实际作用最低的意图切换，
    地图上不再显示它的「!」小角标；保留其余小角标。``include_chase`` 仅给
    测试/诊断保留旧口径，产品 UI 传 False。
    """
    cells = intent_cells(state, now)
    if not include_chase:
        cells = {cell: row for cell, row in cells.items() if row[0] != "chase"}
    if not cells:
        return {}
    clock = monotonic() if now is None else now
    ramping = (animated_cells(state, clock, budget) if animated else set())
    if not include_chase:
        ramping = {cell for cell in ramping if cell in cells}
    return {cell: (kind, intent_icon(kind), COLORS[kind],
                   badge_alpha(clock - started, cell in ramping))
            for cell, (kind, started) in cells.items()}


def intent_text(state, x: int, y: int) -> tuple[str, str] | None:
    """(kind, 中文提示) for the badge currently shown on this cell, or None.

    Hover, right-click detail and keyboard observation all read this, so the
    explanation never depends on which device reached the cell first.
    """
    found = intent_cells(state).get((x, y))
    return None if found is None else (found[0], LABELS[found[0]])


def foreground_styles(state, now: float | None = None, *,
                      include_chase: bool = True) -> dict[tuple[int, int], str]:
    """Character mode: recolour the anomaly's own glyph, never replace it."""
    return {cell: f"fore:bold {colour}"
            for cell, (_kind, _glyph, colour, _alpha) in intent_marks(
                state, now, include_chase=include_chase).items()}


def priority_table() -> dict[str, int]:
    return dict(PRIORITY)
