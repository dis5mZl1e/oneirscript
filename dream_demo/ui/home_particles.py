"""Sparse doorway dust using isolated asciimatics particles, never terminal I/O."""
from __future__ import annotations

import random

from .asciimatics_bridge import ASCIIMATICS_AVAILABLE, Particle

SIM_FPS = 20
LIFE = 120


def _drift(p):
    p.x += p.dx
    p.y += p.dy
    return round(p.x), round(p.y)


class HomeParticles:
    def __init__(self):
        self._size = None
        self._slots = {}

    def clear(self):
        self._slots.clear()
        self._size = None

    @property
    def particle_count(self):
        return len(self._slots)

    def frame(self, width, height, t, quality):
        if quality == 'off' or not ASCIIMATICS_AVAILABLE:
            self.clear()
            return None  # Static / missing dependency retains the original dust.
        size = (width, height)
        if self._size != size:
            self.clear()
            self._size = size
        compact = width <= 80 or height <= 24
        count = 6 if compact else 12
        cells = {}
        absolute = max(0, int(t * SIM_FPS))
        for slot in range(count):
            cycle, step = divmod(absolute + slot * 11, LIFE)
            cached = self._slots.get(slot)
            if cached is None or cached[0] != cycle or cached[1].time > step + 1:
                rng = random.Random(width * 31 + height * 991 + slot * 617 + cycle * 1297)
                p = Particle('·:.', rng.uniform(0, max(0, width-1)),
                    rng.uniform(0, max(0, height-1)), rng.uniform(-.045, .045),
                    rng.uniform(-.025, -.005), [(7, 0, 0), (5, 0, 0)], LIFE, _drift)
                self._slots[slot] = (cycle, p)
            else:
                p = cached[1]
            while p.time <= step:
                p.next()
            if quality == 'low' and slot % 2:
                continue
            char, x, y, fg, _attr, _bg = p.last()
            if 0 <= x < width and 0 <= y < height:
                cells[(x, y)] = (char, '#a69568' if fg == 7 else '#655c46')
        return cells
