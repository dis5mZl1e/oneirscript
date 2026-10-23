"""Bounded asciimatics particles replay settled events in world coordinates.

Only the UI imports this module. No terminal ownership, combat calls, or global RNG.
Simulation uses 20 fixed steps/second; rendering may use 10 or 20 FPS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from .asciimatics_bridge import ASCIIMATICS_AVAILABLE, Particle

SIM_FPS = 20
MAX_BURSTS = 6
MAX_PARTICLES = 96
LIFETIMES = {'spark': .35, 'explosion': .65, 'memory': .8, 'impact': .18}
COLORS = {'spark': ('#ffce80', '#b27b42'),
          'explosion': ('#dfa77c', '#7d6f88'),
          'memory': ('#dbc4ff', '#8763ad'), 'impact': ('#e6ecf2','#596a82')}
# 异常地点 8 邻格的呼吸动画（与记忆碎片拾取同一套字符语言）。
BREATH_PERIOD = 12.0
BREATH_NEIGHBORS = ((-1, -1), (0, -1), (1, -1), (-1, 0),
                    (1, 0), (-1, 1), (0, 1), (1, 1))
BREATH_GLYPHS = ('.', '·', '*', '+')


def _move_outward(particle):
    particle.x += particle.dx
    particle.y += particle.dy
    # Gravity only affects explosion debris, never gameplay entities.
    particle.dy += particle.parm or 0
    return round(particle.x), round(particle.y)


def _move_inward(particle):
    cx, cy = particle.parm
    remaining = max(1, particle.life_time - particle.time)
    particle.x += (cx - particle.x) / remaining
    particle.y += (cy - particle.y) / remaining
    return round(particle.x), round(particle.y)


@dataclass
class _Burst:
    kind: str
    x: int
    y: int
    born: float
    seed: int
    particles: list = field(default_factory=list)
    step: int = 0
    started: bool = False
    palette: tuple[str,str] | None = None
    chars: str | None = None
    count: int | None = None


class MapParticles:
    def __init__(self):
        self._bursts: list[_Burst] = []
        self._sequence = 0

    def clear(self):
        self._bursts.clear()

    @property
    def pending(self):
        return bool(self._bursts)

    @property
    def particle_count(self):
        return sum(len(b.particles) for b in self._bursts)

    def emit(self, kind, position, born, *, palette=None, chars=None, count=None):
        if not ASCIIMATICS_AVAILABLE or kind not in LIFETIMES:
            return
        self._sequence += 1
        x, y = position
        seed = self._sequence * 991 + x * 31 + y * 617
        self._bursts.append(_Burst(kind, x, y, float(born), seed,
                                  palette=palette,chars=chars,count=count))
        self._bursts = self._bursts[-MAX_BURSTS:]

    def _start(self, burst, quality):
        rng = random.Random(burst.seed)
        count = burst.count if burst.count is not None else {'spark': 8, 'explosion': 16, 'memory': 20, 'impact': 4}[burst.kind]
        count = count if quality == 'high' else count // 2
        count = min(count, max(0, MAX_PARTICLES - self.particle_count))
        life = round(LIFETIMES[burst.kind] * SIM_FPS)
        for index in range(count):
            angle = rng.uniform(0, math.tau)
            if burst.kind == 'memory':
                radius = rng.uniform(1.5, 4)
                x, y = burst.x + math.cos(angle)*radius, burst.y + math.sin(angle)*radius
                move, parameter = _move_inward, (burst.x, burst.y)
                dx = dy = 0
            else:
                speed = rng.uniform(.04,.12) if burst.kind=='impact' else rng.uniform(.12, .36 if burst.kind == 'spark' else .48)
                x, y = burst.x, burst.y
                dx, dy = math.cos(angle)*speed, math.sin(angle)*speed
                move, parameter = _move_outward, .012 if burst.kind == 'explosion' else 0
            chars=burst.chars or ('+*.' if burst.kind == 'spark' else '*:.')
            burst.particles.append(Particle(chars,
                x, y, dx, dy, [(7, 0, 0), (5, 0, 0)], life, move, parm=parameter))
        burst.started = True

    def frame(self, viewport, visible, protected, now, quality='high', sites=()):
        """Return viewport glyphs; unseen cells and important objects are never overwritten.

        ``sites`` = 未回应异常地点的世界坐标。每个地点周围 8 格按同一个
        ``BREATH_PERIOD`` 呼吸出字符：被墙/物品/生物/其它事件占住的格子直接
        跳过，绝不覆盖可交互内容。低画质档只保留一半邻格，off 档不动。
        """
        if quality == 'off':
            self.clear()
            return {}
        left, top, width, height = viewport
        glyphs = {}
        alive = []
        # Release expired capacity before starting any scheduled future burst.
        self._bursts = [b for b in self._bursts if now-b.born < LIFETIMES[b.kind]]
        for burst in self._bursts:
            age = now - burst.born
            if age >= LIFETIMES[burst.kind]:
                continue
            alive.append(burst)
            if age < 0:
                continue
            if not burst.started:
                self._start(burst, quality)
            target = min(round(LIFETIMES[burst.kind]*SIM_FPS), int(age*SIM_FPS)+1)
            while burst.step < target:
                for particle in burst.particles:
                    if particle.time < particle.life_time:
                        particle.next()
                burst.step += 1
            # Lower quality limits density immediately, including mid-burst switches.
            particles = burst.particles if quality == 'high' else burst.particles[::2]
            for particle in particles:
                data = particle.last()
                if data is None:
                    continue
                char, x, y, fg, _attr, _bg = data
                wx, wy = int(x), int(y)
                vx, vy = wx-left, wy-top
                if ((wx, wy) in visible and (wx, wy) not in protected
                        and 0 <= vx < width and 0 <= vy < height):
                    color = (burst.palette or COLORS[burst.kind])[0 if fg == 7 else 1]
                    if burst.kind=='impact':
                        from .projectile_styles import ProjectileGlyph
                        char=ProjectileGlyph(char)
                    glyphs[(vx, vy)] = (char, f'bold {color}')
        self._bursts = alive
        glyphs.update(self._breath_glyphs(
            sites, viewport, visible, protected, round(float(now) * 10) / 10, quality))
        return glyphs

    @staticmethod
    def _breath_glyphs(sites, viewport, visible, protected, now, quality):
        """异常地点 8 邻格的呼吸字符；返回视口坐标 → (字符, 样式)。"""
        if not sites:
            return {}
        left, top, width, height = viewport
        result = {}
        now = int(now * 2) / 2  # decorative motion, never combat timing
        step = int(now * 2)
        for sx, sy in sites:
            phase_time = (now + ((sx*7+sy*3) % 2)) % BREATH_PERIOD
            if phase_time >= 3.0:
                continue
            selected = (sx+sy+int(now*4)) % len(BREATH_NEIGHBORS)
            for index, (dx, dy) in enumerate(BREATH_NEIGHBORS):
                if index not in (selected, (selected+4) % len(BREATH_NEIGHBORS)):
                    continue
                if quality != 'high' and index != selected:
                    continue
                wx, wy = sx + dx, sy + dy
                if (wx, wy) not in visible or (wx, wy) in protected:
                    continue
                vx, vy = wx - left, wy - top
                if not (0 <= vx < width and 0 <= vy < height):
                    continue
                # 每个方向错开一点相位，像一圈缓慢呼吸，而不是整块同步闪烁。
                phase = (now / BREATH_PERIOD) * math.tau + index * 0.32 + (sx - sy) * 0.17
                wave = 0.5 + 0.5 * math.sin(phase)
                if wave < 0.18:
                    continue
                band = min(len(BREATH_GLYPHS) - 1, int(wave * len(BREATH_GLYPHS)))
                glyph = BREATH_GLYPHS[band]
                color = ('#ffd166', '#e5c46a', '#c9a85a', '#a38b4c')[band]
                result[(vx, vy)] = (glyph, f'bold {color}')
        return result
