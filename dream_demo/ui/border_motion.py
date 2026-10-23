
"""Border motion sampling (2026-10-18 docs §9).

Used only by the UI decoration clock; never advances world time. Every theme has
its own curve instead of one shared sine:
- start/shallow paper: breathing or short head+tail band;
- hallucination: two opposing beams that meet at fixed joints;
- unconscious/deep: slow deep pulse or a band that pauses at seals;
- realms: door run, block relay, ember crawl, tide advance/retreat, page light,
  clinical scan with a deliberate pause.
"""
from __future__ import annotations

import math

THEMES = (
    'start', 'paper', 'hallucination', 'unconscious', 'deep', 'door', 'toy',
    'ember', 'tide', 'pixel', 'library', 'sanatorium',
)
TAU = math.tau


def _wrap(value: float) -> float:
    return value % 1.0


def _head(position: float, center: float, width: float) -> float:
    delta = _wrap(position - center)
    if delta > 0.5:
        delta -= 1.0
    return max(0.0, 1.0 - abs(delta) / max(0.001, width))


def paper_phase(t: float, period: float = 9.0) -> float:
    return (t / max(0.1, period)) % 1.0


def paper_intensity(t: float, position: float, period: float = 9.0) -> float:
    phase = paper_phase(t, period)
    delta = (position - phase) % 1.0
    head = max(0.0, 1.0 - delta / 0.06)
    tail = max(0.0, 1.0 - (delta - 0.06) / 0.10) if delta >= 0.06 else 0.0
    return min(1.0, head + tail * 0.35)


def pixel_phase(t: float, step: float = 0.34) -> int:
    return int(t / max(0.05, step))


def pixel_intensity(t: float, position: int, width: int, height: int,
                    step: float = 0.34) -> float:
    perimeter = 2 * (width + height) - 4
    if perimeter <= 0:
        return 0.0
    index = int(position) % perimeter
    bright = (pixel_phase(t, step) * 4) % perimeter
    distance = min((index - bright) % perimeter, (bright - index) % perimeter)
    if distance <= 2:
        return 1.0
    if distance <= 4:
        return 0.45
    return 0.0


def intensity(motion: str, t: float, position: float, index: int = 0,
              total: int = 1, *, x: int = 0, y: int = 0,
              width: int = 0, height: int = 0) -> float:
    """Sample a theme's light strength (0..1); geometry/phase are deterministic."""
    if motion == 'paper':
        return paper_intensity(t, position)
    if motion == 'pixel':
        return pixel_intensity(t, index, max(1, width), max(1, height))
    if motion == 'start':
        breath = 0.35 + 0.25 * math.sin(TAU * t / 12.0)
        spark = max(_head(position, .25, .03), _head(position, .75, .03)) * 0.6
        return min(1.0, breath + spark)
    if motion == 'hallucination':
        phase = (t / 8.0) % 1.0
        first = max(_head(position, phase, .07), _head(position, phase, .022) * .5)
        second = max(_head(position, (1 - phase) % 1.0, .07),
                     _head(position, (1 - phase) % 1.0, .022) * .5)
        joint = max(_head(position, .25, .012), _head(position, .75, .012)) * .35
        return min(1.0, max(first, second) + joint)
    if motion == 'unconscious':
        slow = 0.18 + 0.30 * (0.5 + 0.5 * math.sin(TAU * t / 14.0 - position * TAU))
        crack = max(_head(position, .12, .018), _head(position, .62, .018)) * .35
        return min(1.0, slow + crack)
    if motion == 'deep':
        phase = (t / 10.0 + .15) % 1.0
        # 封条处停顿：0.36—0.50 保持暗，不随机移走边界。
        if .36 <= phase <= .50:
            return 0.0
        band = max(0.0, 1.0 - abs(phase - .70) / .12) if phase > .50 else max(
            0.0, 1.0 - abs(phase - .20) / .12)
        seal = max(_head(position, .5, .02), _head(position, .0, .02)) * .25
        return min(1.0, band + seal)
    if motion == 'door':
        # 门楣中心 -> 两侧铰链 -> 立柱向下：按位置阶梯推进。
        step = int((t / 1.1) % 8)
        lit_positions = {.5, .35, .65, .2, .8, .1, .9, .0}
        return 1.0 if step < 6 and abs(position - list(sorted(lit_positions))[step]) < .06 else 0.12
    if motion == 'toy':
        step = int((t / .55) % 8)
        return 1.0 if index % 8 == (step * 3) % 8 else 0.08
    if motion == 'ember':
        top = y == 0
        speed = .5 if top else .28
        flicker = 0.5 + 0.5 * math.sin(TAU * (t * speed - position * 2.5))
        spark = max(_head(position, .33, .018), _head(position, .78, .018)) * .4
        return min(1.0, flicker * .8 + spark)
    if motion == 'tide':
        phase = (t / 11.0) % 1.0
        advance = 1.0 - abs(2 * phase - 1.0)  # 推进后回撤，节奏可辨
        offset = .5 if y == height - 1 else 0.0
        return max(0.0, min(1.0, advance * (0.55 + 0.45 * math.cos(
            TAU * (position - offset)))))
    if motion == 'library':
        step = int((t / .8) % 10)
        tick = index % 10
        return 1.0 if tick == step or tick == (step - 1) % 10 else 0.06
    if motion == 'sanatorium':
        phase = (t / 9.0) % 1.0
        if phase < .28:
            return 0.05  # 冷光有停顿，不是持续扫描
        band = max(0.0, 1.0 - abs(_wrap(phase - .28) - position) / .05)
        ring = max(_head(position, .08, .015), _head(position, .58, .015)) * .3
        return min(1.0, band + ring)
    return 0.0


def palette_sample(accent: str, highlight: str, value: float, low: bool = False) -> str:
    from .deco import mix_hex
    if low:
        return accent
    return mix_hex(accent, highlight, .16 + .58 * max(0.0, min(1.0, value)))


def ascii_frame(width: int, height: int, corner: str = '+') -> dict:
    cells = {}
    for x in range(1, width - 1):
        cells[(x, 0)] = cells[(x, height - 1)] = '-'
    for y in range(1, height - 1):
        cells[(0, y)] = cells[(width - 1, y)] = '|'
    for position in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        cells[position] = corner
    return cells
