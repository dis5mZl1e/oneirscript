"""ASCII 字符原语采样器（2026-10-26，ASCII 动画扩展 Task 4）。

统一入口 sample_layer 把 data.visual_catalog.LayerRecipe 的运动描述采样成
世界格坐标的 VisualFrame。本模块只记录可播放的字符层，不投影、不绘制、
不读写世界、不消耗游戏 RNG：

- 环、弧、沿路径、冲击前沿、括号、括号开合和字形重排用确定性的字符几何采样；
- 爆散、内旋、碎屑复用 asciimatics.particles.Particle 的步进与字符/颜色
  渐进，绝不另写第二套粒子引擎；
- 随机扰动只用 random.Random(seed 派生) 与 math；
- quality：high 全量、low 减半、off 返回空帧；
- 单层每格最多保留 2 个字符（高）/ 1 个（低），总字符高 <= 96 / 低 <= 48；
- 所有坐标限制在 event 涉及格包围盒外扩 params.radius + 2 内，避免把
  隐藏信息画到远处；
- 缺少 asciimatics 时使用同接口的降级 Particle，仍输出简化字符主动作。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random

from .visual_frame import GlyphLayer, VisualFrame

try:  # asciimatics==1.15.0 只被 UI 层引用；缺库时走同接口降级实现。
    from asciimatics.particles import Particle as _AsciimaticsParticle

    ASCIIMATICS_AVAILABLE = True
except ImportError:  # pragma: no cover - 环境缺库时的回退分支
    _AsciimaticsParticle = None
    ASCIIMATICS_AVAILABLE = False


DEFAULT_CHARSET = ".-:+*x/\\|<>()[]{}"
# Narrow glyphs verified in the shipped unified fonts and rich's cell model.
# Each primitive gets one small Unicode accent after its first two ASCII forms;
# the ASCII skeleton stays dominant and is always available as a fallback.
_UNICODE_ACCENT = {
    "orbit_ring": "○",
    "inward_spiral": "·",
    "implosion_burst": "◇",
    "shock_front": "○",
    "arc_chain": "ϟ",
    "slash_fan": "·",
    "fracture_rebuild": "◇",
    "aperture_fold": "◇",
    "growth_reaction": "◦",
    "text_rewrite": "◇",
    "steady_glyph": "·",
    "flame_rise": "·",
    "radial_spokes": "◇",
    "resonance_arcs": "◦",
    "frost_facets": "◇",
    "falling_veil": "·",
    "directional_dash": "·",
    "beacon_signal": "◇",
}
_SAFE_UNICODE_GLYPHS = frozenset(_UNICODE_ACCENT.values())
_ASPECT_Y = 0.55          # 终端格偏高：竖向半径按比例收缩，圆环不拉长。
_MAX_RADIUS = 24.0        # 防止异常 params 把作用范围放得过大。
_MAX_TOTAL = {"high": 96, "low": 48}
_MAX_PER_CELL = {"high": 2, "low": 1}
_PARTICLE_ALPHA = {7: 1.0, 5: 0.65, 2: 0.35, 0: 0.1}
_COLOR_BY_ROLE = {
    "primary": "#f2dca0",
    "secondary": "#8a6f3f",
    "accent": "#ffce80",
    "bright": "#ffffff",
    "ambient": "#9aa6b2",
    "theme": "#a6e1dc",
    "danger": "#e6ecf2",
}
_PRIMITIVE_RADIUS = {
    "orbit_ring": 2.0,
    "inward_spiral": 4.0,
    "implosion_burst": 3.0,
    "shock_front": 3.0,
    "arc_chain": 1.0,
    "slash_fan": 2.0,
    "fracture_rebuild": 1.0,
    "aperture_fold": 1.0,
    "growth_reaction": 3.0,
    "text_rewrite": 1.0,
    "steady_glyph": 0.0,
    "flame_rise": 2.0,
    "radial_spokes": 2.5,
    "resonance_arcs": 3.0,
    "frost_facets": 2.0,
    "falling_veil": 2.0,
    "directional_dash": 3.0,
    "beacon_signal": 3.0,
}


# ---------------------------------------------------------------------------
# 降级 Particle：与 asciimatics.particles.Particle 1.15.0 同接口的最小实现。
# ---------------------------------------------------------------------------

class _FallbackParticle:
    """asciimatics 缺失时的确定性粒子替身（物理仍由调用方 move 闭包决定）。"""

    def __init__(self, chars, x, y, dx, dy, colours, life_time, move,
                 next_colour=None, next_char=None, parm=None,
                 on_create=None, on_each=None, on_destroy=None):
        self.chars = chars or "*"
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.colours = tuple(colours) or ((7, 0, 0),)
        self.time = 0
        self.life_time = max(1, int(life_time))
        self._move = move
        self._next_colour = next_colour or self._default_next_colour
        self._next_char = next_char or self._default_next_char
        self._last = None
        self.parm = parm
        self._on_create = on_create
        self._on_each = on_each
        self._on_destroy = on_destroy

    @staticmethod
    def _default_next_char(particle):
        index = (len(particle.chars) - 1) * particle.time // particle.life_time
        return particle.chars[min(index, len(particle.chars) - 1)]

    @staticmethod
    def _default_next_colour(particle):
        index = (len(particle.colours) - 1) * particle.time // particle.life_time
        return particle.colours[min(index, len(particle.colours) - 1)]

    def last(self):
        return self._last

    def next(self):
        x, y = self._move(self)
        colour = self._next_colour(self)
        char = self._next_char(self)
        fg = colour[0] if len(colour) > 0 else 7
        attr = colour[1] if len(colour) > 1 else 0
        bg = colour[2] if len(colour) > 2 else 0
        self._last = (char, x, y, fg, attr, bg)
        self.time += 1
        if self.time == 1 and self._on_create is not None:
            self._on_create(self)
        elif self.time == self.life_time and self._on_destroy is not None:
            self._on_destroy(self)
        elif self._on_each is not None:
            self._on_each(self)
        return self._last


Particle = _AsciimaticsParticle or _FallbackParticle


# ---------------------------------------------------------------------------
# 通用小工具：事件几何、确定性种子、字符/参数清洗。
# ---------------------------------------------------------------------------

def _point(value):
    if value is None:
        return None
    try:
        return int(round(float(value[0]))), int(round(float(value[1])))
    except (TypeError, ValueError, IndexError):
        return None


def _event_cells(event):
    """事件涉及的格（source/targets/affected_cells/paths），稳定去重。"""
    seen = {}
    source = _point(getattr(event, "source", None))
    if source is not None:
        seen[source] = None
    for point in getattr(event, "targets", ()) or ():
        key = _point(point)
        if key is not None:
            seen[key] = None
    for point in getattr(event, "affected_cells", ()) or ():
        key = _point(point)
        if key is not None:
            seen[key] = None
    for path in getattr(event, "paths", ()) or ():
        for point in path or ():
            key = _point(point)
            if key is not None:
                seen[key] = None
    return tuple(seen)


def _dedupe_points(points):
    seen = {}
    for point in points or ():
        key = _point(point)
        if key is not None:
            seen[key] = None
    return tuple(seen)


def _center(points):
    points = tuple(points)
    if not points:
        return (0, 0)
    return (
        int(round(sum(point[0] for point in points) / len(points))),
        int(round(sum(point[1] for point in points) / len(points))),
    )


def _origin(event, cells):
    source = _point(getattr(event, "source", None))
    if source is not None:
        return source
    targets = _dedupe_points(getattr(event, "targets", ()) or ())
    if targets:
        return _center(targets)
    if cells:
        return _center(cells)
    return (0, 0)


def _rng(seed, salt):
    digest = hashlib.sha1(f"{int(seed)}|{salt}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _hash_unit(seed, salt, index, channel=0):
    digest = hashlib.sha1(
        f"{int(seed)}|{salt}|{int(index)}|{int(channel)}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") / 4294967295.0


def _clamp(value, low, high):
    return low if value < low else (high if value > high else value)


def _clamp_offset(offset):
    return (
        round(_clamp(float(offset[0]), -0.5, 0.5), 4),
        round(_clamp(float(offset[1]), -0.5, 0.5), 4),
    )


def _jitter_offset(seed, salt, index, span=0.5):
    span = _clamp(float(span), 0.0, 1.0)
    ax = _hash_unit(seed, salt, index, 0) - 0.5
    ay = _hash_unit(seed, salt, index, 1) - 0.5
    return _clamp_offset((ax * span, ay * span))


def _particle_offset(x, y):
    """用粒子位置的小数部分做格内偏移；整数位置回到格中心。"""
    try:
        fx = float(x) - math.floor(float(x))
        fy = float(y) - math.floor(float(y))
    except (TypeError, ValueError):
        return (0.0, 0.0)
    if fx < 1e-9 or fx > 1.0 - 1e-9:
        fx = 0.5
    if fy < 1e-9 or fy > 1.0 - 1e-9:
        fy = 0.5
    return _clamp_offset(((fx - 0.5) * 0.8, (fy - 0.5) * 0.8))


def _params(layer):
    raw = getattr(layer, "params", ()) or ()
    if isinstance(raw, dict):
        return dict(raw)
    result = {}
    for item in raw:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            result[str(item[0])] = item[1]
    return result


def _number(params, key, default):
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _count(params, key, default):
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError):
        value = int(default)
    return int(_clamp(value, 1, 96))


def _radius(params, default):
    return _clamp(_number(params, "radius", default), 0.0, _MAX_RADIUS)


def _primitive_radius(primitive, params):
    if "radius" in params:
        return _radius(params, _PRIMITIVE_RADIUS.get(primitive, 2.0))
    return _PRIMITIVE_RADIUS.get(primitive, 2.0)


def _charset_for(layer):
    raw = getattr(layer, "charset", "") or DEFAULT_CHARSET
    ascii_chars = []
    unicode_chars = []
    for char in raw:
        if char == " ":
            continue
        if 0x20 <= ord(char) <= 0x7E and char not in ascii_chars:
            ascii_chars.append(char)
        elif char in _SAFE_UNICODE_GLYPHS and char not in unicode_chars:
            unicode_chars.append(char)
    if not ascii_chars:
        ascii_chars = [char for char in DEFAULT_CHARSET if char != " "]
    accent = _UNICODE_ACCENT.get(str(getattr(layer, "primitive", "")))
    if accent and accent not in unicode_chars:
        unicode_chars.insert(0, accent)
    # Keep ASCII as the main visual language, with a predictable colored-glyph
    # accent mixed into the same sequence. Unknown, wide and emoji glyphs drop.
    return tuple((*ascii_chars[:2], *unicode_chars, *ascii_chars[2:]))


def _sanitize_glyph(glyph, charset):
    """Keep printable ASCII and vetted narrow marks; reject combining/emoji."""
    for char in str(glyph or ""):
        if 0x20 < ord(char) <= 0x7E or char in _SAFE_UNICODE_GLYPHS:
            return char
    return charset[0]


def _glyph_sequence(value):
    """params里的文本 -> printable ASCII or vetted narrow glyph sequence."""
    if value is None:
        return ()
    items = list(value)
    result = []
    for item in items:
        if isinstance(item, str):
            for char in item:
                if 0x20 < ord(char) <= 0x7E or char in _SAFE_UNICODE_GLYPHS:
                    result.append(char)
        elif isinstance(item, int) and 0x20 < item <= 0x7E:
            result.append(chr(item))
    return tuple(result)


def _bounds(event, radius):
    cells = _event_cells(event) or ((0, 0),)
    pad = int(math.ceil(_clamp(float(radius), 0.0, _MAX_RADIUS) + 2.0))
    xs = [point[0] for point in cells]
    ys = [point[1] for point in cells]
    return (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)


def _in_bounds(bounds, cell):
    x, y = int(cell[0]), int(cell[1])
    return bounds[0] <= x <= bounds[1] and bounds[2] <= y <= bounds[3]


def _line_points(start, end):
    x0, y0 = int(start[0]), int(start[1])
    x1, y1 = int(end[0]), int(end[1])
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    points = []
    for index in range(steps + 1):
        x = x0 + dx * index / steps
        y = y0 + dy * index / steps
        points.append((int(round(x)), int(round(y))))
    return points


def _densify(points):
    result = []
    for index in range(len(points) - 1):
        segment = _line_points(points[index], points[index + 1])
        if result and segment:
            result.extend(segment[1:])
        else:
            result.extend(segment)
    return result or list(points)


# ---------------------------------------------------------------------------
# 采样上下文：预算、包围盒护栏与 GlyphLayer 构造。
# ---------------------------------------------------------------------------

class _FrameBuilder:
    """把候选字符落格；逐格与总量预算、包围盒护栏都集中在这里。"""

    def __init__(self, layer, event, quality, bounds):
        self.layer = layer
        self.event_id = str(getattr(event, "event_id", ""))
        self.quality = quality
        self.bounds = bounds
        self.per_cell = _MAX_PER_CELL.get(quality, 1)
        self.total = _MAX_TOTAL.get(quality, 48)
        self._glyphs = {}
        self.count = 0
        self._accent = _UNICODE_ACCENT.get(
            str(getattr(layer, "primitive", "")), "·")
        self._color = _COLOR_BY_ROLE.get(
            str(getattr(layer, "color_role", "primary")), "#f2dca0")
        self._base_alpha = _clamp(float(getattr(layer, "alpha", 1.0)), 0.0, 1.0)
        self._z = int(getattr(layer, "z", 0))
        self._role = str(getattr(layer, "role", "fx"))
        self._scale = float(getattr(layer, "scale", 1.0))
        self._clock_mode = str(getattr(layer, "clock_mode", "settled"))
        self._authored = str(getattr(layer, "primitive", "")) in (
            "flame_rise", "radial_spokes", "resonance_arcs", "frost_facets",
            "falling_veil", "directional_dash", "slash_fan", "fracture_rebuild",
            "text_rewrite", "beacon_signal") or bool(_params(layer).get("layout"))

    def add(self, cell, glyph, *, alpha=1.0, offset=(0.0, 0.0)):
        if self.count >= self.total:
            return False
        x, y = int(cell[0]), int(cell[1])
        if not _in_bounds(self.bounds, (x, y)):
            return False
        layers = self._glyphs.get((x, y))
        if layers is not None and len(layers) >= self.per_cell:
            return False
        # Keep the ASCII forms dominant, while making the Unicode half of the
        # visual language reliably visible in a short sample on both tiers.
        if self.count % 3 == 1 and not self._authored:
            glyph = self._accent
        alpha = _clamp(self._base_alpha * float(alpha), 0.0, 1.0)
        layer = GlyphLayer(
            glyph=glyph,
            color=self._color,
            offset=_clamp_offset(offset),
            scale=self._scale,
            alpha=alpha,
            z=self._z,
            role=self._role,
            event_id=self.event_id,
            clock_mode=self._clock_mode,
        )
        if layers is None:
            self._glyphs[(x, y)] = [layer]
        else:
            layers.append(layer)
        self.count += 1
        return True

    def frame(self):
        return VisualFrame(
            glyph_layers={cell: tuple(layers)
                          for cell, layers in self._glyphs.items()}
        )


@dataclass
class _Context:
    layer: object
    event: object
    stage: str
    progress: float
    seed: int
    quality: str
    params: dict
    charset: tuple
    charset_text: str
    source: tuple | None
    targets: tuple
    affected: tuple
    cells: tuple
    origin: tuple
    radius: float
    builder: _FrameBuilder


# ---------------------------------------------------------------------------
# Particle 步进与绘制（爆散/内旋/碎屑共用）。
# ---------------------------------------------------------------------------

def _step_particles(particles, steps):
    for _ in range(max(1, int(steps))):
        for particle in particles:
            if particle.time < particle.life_time:
                particle.next()


def _draw_particles(ctx, particles, *, alpha_scale=1.0):
    for particle in particles:
        data = particle.last()
        if data is None:
            continue
        char, x, y, fg, _attr, _bg = data
        glyph = _sanitize_glyph(char, ctx.charset)
        alpha = _PARTICLE_ALPHA.get(fg, 0.6) * alpha_scale
        ctx.builder.add(
            (int(round(x)), int(round(y))), glyph,
            alpha=alpha, offset=_particle_offset(x, y),
        )


def _spiral_inward_move(particle):
    center_x, center_y = particle.parm
    offset_x = particle.x - center_x
    offset_y = particle.y - center_y
    distance = math.hypot(offset_x, offset_y)
    if distance <= 0.55:
        return int(round(particle.x)), int(round(particle.y))
    angle = math.atan2(offset_y, offset_x) + 0.55
    distance *= 0.84
    particle.x = center_x + math.cos(angle) * distance
    particle.y = center_y + math.sin(angle) * distance
    return int(round(particle.x)), int(round(particle.y))


def _implosion_move(particle):
    state = particle.parm  # [cx, cy, gather_steps, angle, speed, bursting]
    center_x, center_y, gather_steps = state[0], state[1], state[2]
    if particle.time < gather_steps:
        particle.x += (center_x - particle.x) * 0.45
        particle.y += (center_y - particle.y) * 0.45
    else:
        if not state[5]:
            state[5] = True
            offset_x = particle.x - center_x
            offset_y = particle.y - center_y
            state[3] = math.atan2(offset_y, offset_x)
            state[4] = max(0.35, math.hypot(offset_x, offset_y))
        angle = state[3]
        speed = state[4] * 0.16
        particle.x += math.cos(angle) * speed
        particle.y += math.sin(angle) * speed
    return int(round(particle.x)), int(round(particle.y))


# ---------------------------------------------------------------------------
# 原语 1：环 / 双环反转 / 压扁声纹。
# ---------------------------------------------------------------------------

def _prim_orbit_ring(ctx):
    radius = _clamp(_radius(ctx.params, 2.0), 0.5, _MAX_RADIUS)
    double = bool(ctx.params.get("double", False))
    reverse = bool(ctx.params.get("reverse", False))
    squash = bool(ctx.params.get("squash", False))
    ry_factor = 0.30 if squash else _ASPECT_Y
    direction = -1.0 if reverse else 1.0
    phase = ctx.progress * math.tau * direction
    samples = max(6, int(radius * 8))
    if ctx.quality != "high":
        samples = max(4, samples // 2)
    rings = [(radius, direction, 0.0, 1.0)]
    if double and ctx.quality == "high":
        rings.append((radius * 0.62, -direction, math.pi / max(4, samples), 0.75))
    chars = ctx.charset
    for ring_index, (ring_radius, ring_direction, phase_offset, alpha_scale) in enumerate(rings):
        count = samples if ring_index == 0 else max(4, samples // 2)
        for index in range(count):
            angle = (phase * ring_direction + phase_offset
                     + math.tau * index / count)
            x = ctx.origin[0] + math.cos(angle) * ring_radius
            y = ctx.origin[1] + math.sin(angle) * ring_radius * ry_factor
            glyph = chars[(index + int(ctx.progress * len(chars))) % len(chars)]
            alpha = alpha_scale * (0.6 + 0.4 * (0.5 + 0.5 * math.cos(angle * 2)))
            ctx.builder.add(
                (int(round(x)), int(round(y))), glyph,
                alpha=alpha,
                offset=_jitter_offset(ctx.seed, "orbit", ring_index * 1000 + index, 0.35),
            )


# ---------------------------------------------------------------------------
# 原语 2：外围散字螺旋吸附到中心。
# ---------------------------------------------------------------------------

def _prim_inward_spiral(ctx):
    count = _count(ctx.params, "count", 12)
    radius = _clamp(_radius(ctx.params, 4.0), 0.75, _MAX_RADIUS)
    if ctx.quality != "high":
        count = max(1, count // 2)
    rng = _rng(ctx.seed, "inward_spiral")
    life = 10
    particles = []
    for _index in range(count):
        angle = rng.uniform(0.0, math.tau)
        spawn_radius = rng.uniform(radius * 0.6, radius * 1.05)
        particles.append(Particle(
            ctx.charset_text,
            ctx.origin[0] + math.cos(angle) * spawn_radius,
            ctx.origin[1] + math.sin(angle) * spawn_radius * _ASPECT_Y,
            0.0, 0.0,
            [(7, 0, 0), (5, 0, 0), (2, 0, 0)],
            life, _spiral_inward_move, parm=(ctx.origin[0], ctx.origin[1]),
        ))
    steps = 1 + int(ctx.progress * (life - 1))
    _step_particles(particles, steps)
    _draw_particles(ctx, particles)


# ---------------------------------------------------------------------------
# 原语 3：先聚后爆的径向散字。
# ---------------------------------------------------------------------------

def _prim_implosion_burst(ctx):
    count = _count(ctx.params, "count", 16)
    radius = _clamp(_radius(ctx.params, 3.0), 0.75, _MAX_RADIUS)
    if ctx.quality != "high":
        count = max(1, count // 2)
    rng = _rng(ctx.seed, "implosion_burst")
    life = 10
    gather_steps = max(1, int(life * 0.35))
    particles = []
    for _index in range(count):
        angle = rng.uniform(0.0, math.tau)
        spawn_radius = radius * rng.uniform(0.4, 1.0)
        particles.append(Particle(
            ctx.charset_text,
            ctx.origin[0] + math.cos(angle) * spawn_radius,
            ctx.origin[1] + math.sin(angle) * spawn_radius * _ASPECT_Y,
            0.0, 0.0,
            [(7, 0, 0), (5, 0, 0), (2, 0, 0)],
            life, _implosion_move,
            parm=[ctx.origin[0], ctx.origin[1], gather_steps,
                  angle, spawn_radius, False],
        ))
    steps = 1 + int(ctx.progress * (life - 1))
    _step_particles(particles, steps)
    _draw_particles(ctx, particles)


# ---------------------------------------------------------------------------
# 原语 4：薄前沿与短尾迹（圆环 / 切比雪夫方环）。
# ---------------------------------------------------------------------------

def _square_ring(cx, cy, radius):
    radius = int(radius)
    if radius <= 0:
        return [(cx, cy)]
    cells = []
    for dx in range(-radius, radius + 1):
        cells.append((cx + dx, cy - radius))
        cells.append((cx + dx, cy + radius))
    for dy in range(-radius + 1, radius):
        cells.append((cx - radius, cy + dy))
        cells.append((cx + radius, cy + dy))
    return cells


def _prim_shock_front(ctx):
    radius = _clamp(_radius(ctx.params, 3.0), 0.5, _MAX_RADIUS)
    square = bool(ctx.params.get("square", False))
    double_front = bool(ctx.params.get("double_front", False))
    front = bool(ctx.params.get("front", False))
    reach = radius * ctx.progress
    rings = [(reach, 1.0)]
    if double_front and reach >= 0.6:
        rings.append((reach * 0.62, 0.55))
    if front and reach >= 1.0:
        rings.append((max(0.0, reach - 0.6), 0.8))
    if 1.2 <= reach < radius * 0.95:
        rings.append((reach - 1.0, 0.35))  # 短尾迹，不是填满内部
    chars = ctx.charset
    for ring_index, (ring_radius, alpha_scale) in enumerate(rings):
        if square:
            cells = _square_ring(
                ctx.origin[0], ctx.origin[1], int(round(ring_radius)))
            for index, (x, y) in enumerate(cells):
                glyph = chars[(index + ring_index) % len(chars)]
                ctx.builder.add(
                    (x, y), glyph,
                    alpha=alpha_scale * (0.65 + 0.35 * ((index % 4) == 0)),
                    offset=_jitter_offset(ctx.seed, "front", ring_index * 1000 + index, 0.3),
                )
            continue
        if ring_radius < 0.4:
            ctx.builder.add(
                ctx.origin, chars[ring_index % len(chars)], alpha=alpha_scale)
            continue
        samples = max(8, int(math.tau * ring_radius * 1.6))
        if ctx.quality != "high":
            samples = max(6, samples // 2)
        for index in range(samples):
            angle = (math.tau * index / samples
                     + ring_index * 0.31 + ctx.progress * 0.2)
            x = ctx.origin[0] + math.cos(angle) * ring_radius
            y = ctx.origin[1] + math.sin(angle) * ring_radius * _ASPECT_Y
            glyph = chars[(index + ring_index) % len(chars)]
            alpha = alpha_scale * (0.7 + 0.3 * (0.5 + 0.5 * math.cos(angle * 3)))
            ctx.builder.add(
                (int(round(x)), int(round(y))), glyph, alpha=alpha,
                offset=_jitter_offset(ctx.seed, "front", ring_index * 1000 + index, 0.3),
            )


# ---------------------------------------------------------------------------
# 原语 5：沿真实路径的折线字符与头部亮尾迹。
# ---------------------------------------------------------------------------

def _prim_arc_chain(ctx):
    paths = tuple(getattr(ctx.event, "paths", ()) or ())
    segments = []
    for path in paths:
        points = [_point(point) for point in (path or ())]
        points = [point for point in points if point is not None]
        if len(points) >= 2:
            segments.append(points)
        elif len(points) == 1:
            segments.append([points[0], points[0]])
    if not segments:
        targets = ctx.targets or ctx.affected or (ctx.origin,)
        for target in targets:
            segments.append([target, target])
    if not segments:
        segments = [[ctx.origin, ctx.origin]]
    chars = ctx.charset
    for segment_index, raw_points in enumerate(segments):
        points = _densify(raw_points)
        total = len(points) - 1
        progress = _clamp(ctx.progress * 1.15 - 0.05 * segment_index, 0.0, 1.0)
        head = int(round(progress * total)) if total > 0 else 0
        trail_cells = max(0, int(ctx.params.get("trail_cells", total)))
        for index in range(max(0, head - trail_cells), head + 1):
            x, y = points[index]
            trail = head - index
            alpha = 1.0 if trail <= 0 else (0.6 if trail == 1 else 0.35)
            glyph = chars[(index + segment_index) % len(chars)]
            ctx.builder.add((x, y), glyph, alpha=alpha)
        if head >= 0 and int(ctx.params.get("head_count", 2)) > 1:
            head_cell = points[min(head, total)]
            ctx.builder.add(
                head_cell, chars[(head + segment_index + 1) % len(chars)],
                alpha=0.95,
                offset=_jitter_offset(ctx.seed, "arc_head", segment_index, 0.4),
            )


# ---------------------------------------------------------------------------
# 原语 6：真实目标附近的短弧 / 交叉刃影，有限尾迹，无随机碎屑。
# ---------------------------------------------------------------------------

def _result_anchors(ctx):
    """Use recorded endpoints and result cells, excluding intermediate travel."""
    candidates = _dedupe_points(tuple(ctx.targets) + tuple(ctx.affected))
    paths = tuple(tuple(cell for point in path if (cell := _point(point)) is not None)
                  for path in (getattr(ctx.event, "paths", ()) or ()))
    paths = tuple(path for path in paths if len(path) > 1)
    if not paths:
        return candidates or (ctx.origin,)
    route = {cell for path in paths for cell in path}
    endpoints = tuple(path[-1] for path in paths)
    return _dedupe_points(endpoints + tuple(cell for cell in candidates
                                            if cell not in route and cell != ctx.source)) or (ctx.origin,)


def _prim_slash_fan(ctx):
    targets = _result_anchors(ctx)
    targets = tuple(cell for cell in targets if cell != ctx.source) or targets
    if _compact_motif(ctx, "/\\", drift=(.2, -.2), cells=targets):
        return
    count = _count(ctx.params, "count", 3)
    if ctx.quality != "high":
        count = max(1, count // 2)
    targets = targets[:count]
    origin = ctx.source or ctx.origin
    span = max(.8, min(1.8, ctx.radius))
    fade = min(1.0, max(.03, (1 - ctx.progress) / .3))
    for index, (cx, cy) in enumerate(targets):
        incoming = math.atan2((cy-origin[1]) / _ASPECT_Y, cx-origin[0])
        handed = 1 if (ctx.seed + index) % 2 else -1
        angle = incoming + handed * .9
        strokes = (angle, angle + math.pi / 2) if ctx.params.get("cross") else (angle,)
        for direction in strokes:
            marks, seen = [], set()
            head = int(ctx.progress * 8)
            for step in range(head, -1, -1):
                t = step / 8
                distance = (2*t-1) * span
                bend = .25 * math.sin(t * math.pi)
                x = cx + math.cos(direction)*distance - math.sin(direction)*bend
                y = cy + (math.sin(direction)*distance + math.cos(direction)*bend) * _ASPECT_Y
                cell = (int(round(x)), int(round(y)))
                if cell in seen:
                    continue
                seen.add(cell)
                dx = 2*span*math.cos(direction) - .25*math.pi*math.sin(direction)*math.cos(t*math.pi)
                dy = (2*span*math.sin(direction) + .25*math.pi*math.cos(direction)*math.cos(t*math.pi)) * _ASPECT_Y
                glyph = "-" if abs(dx) > 2*abs(dy) else "|" if abs(dy) > 2*abs(dx) else "\\" if dx*dy > 0 else "/"
                marks.append((cell, glyph, _particle_offset(x, y)))
                if len(marks) >= (3 if ctx.quality == "high" else 2):
                    break
            for trail, (cell, glyph, offset) in enumerate(marks):
                if trail and trail == len(marks)-1:
                    glyph = "·"
                ctx.builder.add(cell, glyph, offset=offset,
                                alpha=fade * (1.0 if trail == 0 else .5 if trail == 1 else .25))


# ---------------------------------------------------------------------------
# 原语 7：真实结果格内裂解 -> 对齐 -> 落定，或擦除 -> 淡出。
# ---------------------------------------------------------------------------

def _prim_fracture_rebuild(ctx):
    cells = _result_anchors(ctx)
    limit = 6 if ctx.quality == "high" else 3
    cells = cells[::max(1, math.ceil(len(cells) / limit))][:limit]
    rebuild = bool(ctx.params.get("rebuild", True))
    chars = tuple(char for char in ctx.charset if ord(char) < 128) or ("_", "|")
    old_chars = _glyph_sequence(ctx.params.get("old_glyphs")) or chars
    p = ctx.progress
    for index, cell in enumerate(cells):
        side = 1 if index % 2 else -1
        if p < .33:
            glyph = old_chars[index % len(old_chars)]
            offset = (side * .24 * (1 - p/.33), -.15 * (1 - p/.33))
        elif p < .6:
            glyph = "◇" if rebuild else "·"
            offset = (side * .12 * (1 - (p-.33)/.27), 0)
        elif rebuild:
            glyph = chars[index % len(chars)]
            offset = (0, 0)
        else:
            glyph = "," if index % 2 else "`"
            offset = (side * .12, .28 * (p-.6)/.4)
        alpha = min(.85, max(.02, .85*(1-p)/.3))
        ctx.builder.add(cell, glyph, alpha=alpha, offset=offset)


# ---------------------------------------------------------------------------
# 原语 8：两端括号开合。
# ---------------------------------------------------------------------------

def _prim_aperture_fold(ctx):
    layout = ctx.params.get("layout")
    if layout in ("fold", "bind", "seam"):
        _prim_aperture_layout(ctx, layout)
        return
    endpoints = _dedupe_points(([ctx.source] if ctx.source else []) + list(ctx.targets))
    if not endpoints:
        endpoints = (ctx.origin,)
    corners = bool(ctx.params.get("corners", False))
    open_close = bool(ctx.params.get("open_close", True))
    if open_close:
        opening = (ctx.progress / 0.5 if ctx.progress < 0.5
                   else (1.0 - ctx.progress) / 0.5)
    else:
        opening = ctx.progress
    opening = _clamp(opening, 0.0, 1.0)
    distance = 0.6 + 1.6 * opening
    chars = ctx.charset
    for endpoint_index, (end_x, end_y) in enumerate(endpoints):
        if corners:
            positions = [
                (end_x - distance, end_y - distance),
                (end_x + distance, end_y - distance),
                (end_x - distance, end_y + distance),
                (end_x + distance, end_y + distance),
            ]
        else:
            positions = [
                (end_x - distance, end_y),
                (end_x + distance, end_y),
                (end_x, end_y - distance),
                (end_x, end_y + distance),
            ]
        for mark_index, (x, y) in enumerate(positions):
            ctx.builder.add(
                (int(round(x)), int(round(y))),
                chars[(endpoint_index * 4 + mark_index) % len(chars)],
                alpha=0.45 + 0.55 * opening,
                offset=_jitter_offset(
                    ctx.seed, "aperture", endpoint_index * 10 + mark_index, 0.3),
            )


def _prim_aperture_layout(ctx, layout):
    """Paired gates, closing restraints and vertical seams have distinct outlines."""
    p = ctx.progress
    targets = _dedupe_points(ctx.targets or ctx.affected or (ctx.origin,))
    if ctx.params.get("compact"):
        for cell in targets:
            if layout == "seam":
                marks = (("|" if p < .82 else "◇", (0, .18 - .36 * p)),)
            elif layout == "fold":
                marks = (("[", (-.28, 0)), ("]", (.28, 0)))
            else:
                left, right = ("<", ">") if p < .35 else ("(", ")")
                marks = ((left, (-.28, -.15 * (1 - p))),
                         (right, (.28, .15 * (1 - p))))
            for glyph, offset in marks[:2 if ctx.quality == "high" else 1]:
                ctx.builder.add(cell, glyph, offset=offset,
                                alpha=max(.12, .9 - .75 * p))
        return
    if layout == "fold":
        endpoints = _dedupe_points((ctx.source or ctx.origin, targets[0]))
        distance = .65 + 1.15 * math.sin(math.pi * p)
        for x, y in endpoints:
            for side, glyph in ((-1, "["), (1, "]")):
                px = x + side * distance
                ctx.builder.add((round(px), y), glyph, alpha=.9 - .45 * p,
                                offset=(_clamp(px - round(px), -.3, .3), 0))
        if p > .65:
            ctx.builder.add((targets[0][0], targets[0][1] - 1), "◇", alpha=.3)
    elif layout == "bind":
        distance = 1.85 - 1.15 * (1 - (1 - p) ** 2)
        left, right = ("[", "]") if "[" in ctx.charset_text else ("(", ")")
        for x, y in targets[:4]:
            for side, glyph in ((-1, left), (1, right)):
                px = x + side * distance
                ctx.builder.add((round(px), y), glyph, alpha=.85 - .4 * p,
                                offset=(_clamp(px - round(px), -.3, .3), 0))
            if p < .3:
                ctx.builder.add((x, y - 1), "◇", alpha=.35)
    else:
        height = 1 + int(p * 2)
        for index, (x, y) in enumerate(targets[:4]):
            for step in range(height + 1):
                glyph = "◇" if step == height and index % 2 == 0 else "|"
                ctx.builder.add((x, y - step), glyph,
                                alpha=max(.15, .8 - .5 * p - step * .08))


# ---------------------------------------------------------------------------
# 原语 9：真实改变格/目标的蔓线、喷孢与碎晶。
# ---------------------------------------------------------------------------

def _prim_growth_reaction(ctx):
    centers = _dedupe_points(
        list(ctx.affected) + list(ctx.targets)
        + ([ctx.source] if ctx.source else []))
    if not centers:
        centers = (ctx.origin,)
    radius = _clamp(_radius(ctx.params, 3.0), 0.5, _MAX_RADIUS)
    max_length = int(radius) + 2
    chars = ctx.charset
    try:
        requested_shoots = int(ctx.params.get("shoots", 3))
    except (TypeError, ValueError):
        requested_shoots = 3
    shoots = max(1, min(3, requested_shoots))
    if ctx.quality != "high":
        shoots = max(1, shoots // 2)
    spores = bool(ctx.params.get("spores", True))
    for center_index, (center_x, center_y) in enumerate(centers):
        for shoot_index in range(shoots):
            rng = _rng(ctx.seed, f"growth:{center_index}:{shoot_index}")
            angle = rng.uniform(0.0, math.tau)
            length = int(_clamp(1 + rng.randint(1, max(1, int(radius))),
                                1, max_length))
            reveal = 1 + int(ctx.progress * (length - 1)) if length > 1 else 1
            for step in range(1, reveal + 1):
                bend = rng.uniform(-0.18, 0.18)
                step_angle = angle + bend * step
                x = center_x + math.cos(step_angle) * step
                y = center_y + math.sin(step_angle) * step * _ASPECT_Y
                ctx.builder.add(
                    (int(round(x)), int(round(y))),
                    chars[(center_index * 7 + shoot_index * 3 + step) % len(chars)],
                    alpha=0.65 if step < reveal else 1.0,
                )
            tip_x = center_x + math.cos(angle) * reveal
            tip_y = center_y + math.sin(angle) * reveal * _ASPECT_Y
            if spores and ctx.quality == "high" and reveal >= 2:
                spore_angle = rng.uniform(0.0, math.tau)
                spore_radius = rng.uniform(0.3, 0.9)
                ctx.builder.add(
                    (int(round(tip_x + math.cos(spore_angle) * spore_radius)),
                     int(round(tip_y + math.sin(spore_angle) * spore_radius))),
                    chars[(center_index + shoot_index) % len(chars)],
                    alpha=0.4,
                    offset=_jitter_offset(
                        ctx.seed, "growth_spore", center_index * 10 + shoot_index, 0.5),
                )


# ---------------------------------------------------------------------------
# 原语 10：局部旧字 -> 光标 -> 新字，或页片翻转；不补画传导路径。
# ---------------------------------------------------------------------------

def _prim_text_rewrite(ctx):
    targets = _result_anchors(ctx)
    old_chars = _glyph_sequence(ctx.params.get("old_glyphs")) or ctx.charset
    new_chars = _glyph_sequence(ctx.params.get("new_glyphs")) or ctx.charset
    p = ctx.progress
    page = ctx.params.get("mode") == "page"
    for index, cell in enumerate(targets):
        if page:
            turn = .5 - .5 * math.cos(math.pi * p)
            glyph = "/" if p < .33 else "|" if p < .66 else "\\"
            if .33 <= p < .48:
                glyph = "◇"
            offset = (-.28 + .56*turn, -.06*math.sin(math.pi*p))
            alpha = min(.85, max(.02, .85*(1-p)/.25))
        elif p < .32:
            glyph = old_chars[index % len(old_chars)]
            offset = (-.28 * (p/.32), -.08 * (p/.32))
            alpha = .85 - .3 * p/.32
        elif p < .55:
            glyph = "·" if .38 <= p < .5 else "|"
            offset = (0, 0)
            alpha = .72
        else:
            arrive = (p-.55)/.45
            glyph = new_chars[index % len(new_chars)]
            offset = (.24*(1-arrive)**2, 0)
            alpha = min(.85, max(.02, .85*(1-p)/.2))
        ctx.builder.add(cell, glyph, alpha=alpha, offset=offset)


# ---------------------------------------------------------------------------
# 原语 11：低亮静态字，alpha 随进度衰减。
# ---------------------------------------------------------------------------

def _prim_steady_glyph(ctx):
    cells = _dedupe_points(
        ([ctx.source] if ctx.source else [])
        + list(ctx.targets) + list(ctx.affected))
    if not cells:
        cells = (ctx.origin,)
    chars = ctx.charset
    life = ctx.params.get("life")
    if life is None:
        fade = max(0.08, 1.0 - 0.85 * ctx.progress)
    else:
        try:
            span = max(0.05, float(life))
        except (TypeError, ValueError):
            span = 0.45
        fade = max(0.08, 1.0 - ctx.progress / span)
    for index, cell in enumerate(cells):
        ctx.builder.add(
            cell, chars[index % len(chars)], alpha=fade,
            offset=_jitter_offset(ctx.seed, "steady", index, 0.3),
        )


# ---------------------------------------------------------------------------
# Sparse semantic silhouettes. Real range and danger information remains in
# the existing world markers; these strokes are optional settled feedback.
# ---------------------------------------------------------------------------

def _motif_cells(ctx, limit=6):
    cells = _dedupe_points(ctx.affected or ctx.targets or (ctx.origin,))
    stride = max(1, math.ceil(len(cells) / limit))
    return cells[::stride][:limit]


def _compact_motif(ctx, glyphs, *, drift=(0.0, 0.0), cells=None):
    """Routine feedback stays inside the real result tiles, with no halo."""
    if not ctx.params.get("compact"):
        return False
    cells = _dedupe_points(cells if cells is not None else (ctx.affected or ctx.targets or (ctx.origin,)))
    phase = int(ctx.progress * 6)
    accent = _UNICODE_ACCENT[ctx.layer.primitive]
    for index, cell in enumerate(cells):
        glyph = accent if (index + phase) % 4 == 1 else glyphs[(index + phase) % len(glyphs)]
        ctx.builder.add(cell, glyph, alpha=max(.12, 1.0 - ctx.progress * .86),
                        offset=(drift[0] * (ctx.progress - .5),
                                drift[1] * (ctx.progress - .5)))
    return True


def _prim_flame_rise(ctx):
    if _compact_motif(ctx, "^/\\", drift=(0.0, -.32)):
        return
    phase = ctx.progress
    for index, (x, y) in enumerate(_motif_cells(ctx, 4)):
        # Staggered tongues lean in opposite directions, then leave one ember.
        lift = 2.2 * phase + (index % 2) * .35
        lean = (-1 if index % 2 else 1) * .35 * math.sin(phase * math.pi)
        py = y - .4 - lift
        glyph = "^" if phase < .82 else "·" if index % 2 else "'"
        ctx.builder.add((x, int(round(py))), glyph,
                        offset=(lean, _clamp(py - round(py), -.3, .3)),
                        alpha=max(.15, .9 - phase * .65))
        if phase < .82:
            ctx.builder.add((x + (1 if index % 2 else -1), int(round(py)) + 1),
                            "/" if index % 2 else "\\", alpha=.8 * (1 - phase * .65),
                            offset=(-lean, -.12))


def _prim_radial_spokes(ctx):
    if _compact_motif(ctx, "x/+", drift=(.15, -.12)):
        return
    center = _point(getattr(ctx.event, "center", None)) or ctx.origin
    reach = .65 + (max(1.0, min(4.0, ctx.radius)) - .65) * (1 - (1 - ctx.progress) ** 3)
    count = 8 if ctx.quality == "high" else 4
    for ray in range(count):
        angle = math.tau * ray / count + .14
        radius = reach * (1 if ray % 2 else .78)
        dx, dy = math.cos(angle), math.sin(angle) * .65
        x, y = center[0] + dx * radius, center[1] + dy * radius
        glyph = "◇" if ray == 1 else ("-" if abs(dy) < .25 else
                "|" if abs(dx) < .3 else "\\" if dx * dy > 0 else "/")
        ctx.builder.add((round(x), round(y)), glyph,
                        alpha=max(.12, 1 - ctx.progress * .9),
                        offset=_particle_offset(x, y))


def _prim_resonance_arcs(ctx):
    if _compact_motif(ctx, ")~("):
        return
    # Two open, broken shoulders pulse sideways; never close into a ring.
    reach = .8 + max(.2, min(4.0, ctx.radius) - .8) * ctx.progress
    echo = bool(ctx.params.get("echo"))
    reach += .85 if echo else 0.0
    bands = 2 if ctx.quality == "high" and not echo else 1
    seen = set()
    for band in range(bands):
        radius = max(.8, reach - band * .9)
        for side in (-1, 1):
            for sample, angle in enumerate((-.8, -.3, .3, .8)):
                if (sample + band) % 4 == int(ctx.progress * 3):
                    continue
                x = ctx.origin[0] + side * math.cos(angle) * radius
                y = ctx.origin[1] + math.sin(angle) * radius * .7
                glyph = "◦" if sample == 3 and band == 0 else ")" if side > 0 else "("
                cell = (int(round(x)), int(round(y)))
                if cell in seen:
                    continue
                seen.add(cell)
                ctx.builder.add(cell, glyph,
                                alpha=max(.12, .85 - ctx.progress * .6 - band * .16),
                                offset=_particle_offset(x, y))


def _prim_frost_facets(ctx):
    if _compact_motif(ctx, "<>/"):
        return
    reach = 1.35 - .45 * min(1, ctx.progress * 2)
    for index, (x, y) in enumerate(_motif_cells(ctx, 3)):
        # Offset diagonal facets lock inward, then chip into pale shards.
        for corner, (dx, dy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
            glyph = "◇" if corner == 1 else "/" if dx * dy < 0 else "\\"
            if ctx.progress > .7 and (corner + index) % 2:
                continue
            ctx.builder.add((x + dx, y + dy), glyph,
                            offset=(dx * (reach - 1) * .5, dy * (reach - 1) * .5),
                            alpha=max(.16, .86 - ctx.progress * .65))


def _prim_falling_veil(ctx):
    drip = bool(ctx.params.get("drip")) or "|" in ctx.charset_text
    if _compact_motif(ctx, "|:." if drip else ",;:", drift=(.12, .35)):
        return
    for index, (x, y) in enumerate(_motif_cells(ctx, 5)):
        fall = ctx.progress * 1.5 + (index % 3) * .2
        px = x + math.sin(index * 1.7 + ctx.progress * 2) * .45
        py = y - .6 + fall
        glyph = (":" if ctx.progress > .55 else "|") if drip else (
            "," if ctx.progress > .55 else ";")
        if index % 3 == 1:
            glyph = "·"
        ctx.builder.add((round(px), round(py)), glyph,
                        offset=_particle_offset(px, py),
                        alpha=max(.12, .62 - ctx.progress * .42))


def _prim_directional_dash(ctx):
    paths = tuple(getattr(ctx.event, "paths", ()) or ())
    segments = []
    for path in paths:
        points = [_point(point) for point in (path or ())]
        points = [point for point in points if point is not None]
        if len(points) >= 2:
            segments.append(_densify(points))
    if not segments:
        # An endpoint is evidence of a result, not of a traversable route.
        for index, cell in enumerate(_dedupe_points(ctx.affected or ctx.targets or (ctx.origin,))):
            ctx.builder.add(cell, "·" if index % 3 == 1 else ">",
                            alpha=max(.12, 1 - ctx.progress * .85))
        return
    for points in segments:
        if not points:
            continue
        head = max(0, min(len(points) - 1,
                          int(round(ctx.progress * (len(points) - 1)))))
        # A moving head and at most two broken tail marks, never a thick beam.
        for offset in range(min(3, head + 1)):
            point_index = head - offset
            x, y = points[point_index]
            previous = points[max(0, point_index - 1)]
            following = points[min(len(points) - 1, point_index + 1)]
            dx, dy = following[0] - previous[0], following[1] - previous[1]
            glyph = (">" if dx > 0 else "<") if abs(dx) >= abs(dy) else ("v" if dy > 0 else "^")
            if offset:
                glyph = "·" if offset == 2 else "-" if abs(dx) >= abs(dy) else "|"
            ctx.builder.add((x, y), glyph, alpha=0.95 - offset * 0.28)


def _prim_beacon_signal(ctx):
    if _compact_motif(ctx, "+|"):
        return
    bands = 3 if ctx.quality == "high" else 2
    fade = min(1.0, max(.02, (1 - ctx.progress) / .32))
    for side in (-1, 1):
        for level in range(1, bands + 1):
            pulse = .55 + .4 * math.cos(math.pi * (ctx.progress * 2 - level / bands))
            glyph = "◇" if side == -1 and level == bands else "|"
            ctx.builder.add((ctx.origin[0], ctx.origin[1] + side*level), glyph,
                            alpha=max(.08, pulse) * fade,
                            offset=(0, side * .15 * math.sin(math.pi * ctx.progress)))
    if ctx.quality == "high" and ctx.progress < .6:
        ctx.builder.add((ctx.origin[0]-1, ctx.origin[1]), "/", alpha=.45*fade)
        ctx.builder.add((ctx.origin[0]+1, ctx.origin[1]), "\\", alpha=.45*fade)


_HANDLERS = {
    "orbit_ring": _prim_orbit_ring,
    "inward_spiral": _prim_inward_spiral,
    "implosion_burst": _prim_implosion_burst,
    "shock_front": _prim_shock_front,
    "arc_chain": _prim_arc_chain,
    "slash_fan": _prim_slash_fan,
    "fracture_rebuild": _prim_fracture_rebuild,
    "aperture_fold": _prim_aperture_fold,
    "growth_reaction": _prim_growth_reaction,
    "text_rewrite": _prim_text_rewrite,
    "steady_glyph": _prim_steady_glyph,
    "flame_rise": _prim_flame_rise,
    "radial_spokes": _prim_radial_spokes,
    "resonance_arcs": _prim_resonance_arcs,
    "frost_facets": _prim_frost_facets,
    "falling_veil": _prim_falling_veil,
    "directional_dash": _prim_directional_dash,
    "beacon_signal": _prim_beacon_signal,
}

_PRIMITIVE_ORDER = (
    "orbit_ring",
    "inward_spiral",
    "implosion_burst",
    "shock_front",
    "arc_chain",
    "slash_fan",
    "fracture_rebuild",
    "aperture_fold",
    "growth_reaction",
    "text_rewrite",
    "steady_glyph",
    "flame_rise",
    "radial_spokes",
    "resonance_arcs",
    "frost_facets",
    "falling_veil",
    "directional_dash",
    "beacon_signal",
)


def primitive_names() -> tuple[str, ...]:
    """全部原语名（catalog 覆盖审计与测试用）。"""
    return _PRIMITIVE_ORDER


def sample_layer(layer, *, event, stage: str, progress: float,
                 seed: int, quality: str) -> VisualFrame:
    """把单个 LayerRecipe 采样成世界坐标的 VisualFrame。

    纯函数：同 seed 与输入永远得到相同帧；不读写世界、不碰全局 RNG。
    未知原语退化为静态字形（保留主反馈），quality='off' 返回空帧。
    """
    quality = str(quality)
    if quality == "off":
        return VisualFrame()
    if quality not in ("high", "low"):
        quality = "low"
    try:
        progress = float(progress)
    except (TypeError, ValueError):
        progress = 0.0
    progress = _clamp(progress, 0.0, 1.0)
    params = _params(layer)
    primitive = str(getattr(layer, "primitive", ""))
    radius = _primitive_radius(primitive, params)
    bounds = _bounds(event, radius)
    charset = _charset_for(layer)
    cells = _event_cells(event)
    context = _Context(
        layer=layer,
        event=event,
        stage=str(stage),
        progress=progress,
        seed=int(seed),
        quality=quality,
        params=params,
        charset=charset,
        charset_text="".join(charset),
        source=_point(getattr(event, "source", None)),
        targets=_dedupe_points(getattr(event, "targets", ()) or ()),
        affected=_dedupe_points(getattr(event, "affected_cells", ()) or ()),
        cells=cells,
        origin=_origin(event, cells),
        radius=radius,
        builder=_FrameBuilder(layer, event, quality, bounds),
    )
    handler = _HANDLERS.get(primitive, _prim_steady_glyph)
    handler(context)
    return context.builder.frame()
