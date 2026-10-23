"""离屏演出桥（2026-10-08）：asciimatics 1.15.0 → CinematicFrame。

为什么不是 ``Screen.play()``：Textual 拥有终端、输入与最终显示，asciimatics
在这里只当**离屏字符画/粒子素材库**。本机 1.15.0 实测 API 事实（探针验证）：

- ``TemporaryCanvas``/``Canvas`` 都在 ``asciimatics.screen``（**没有**
  ``asciimatics.canvas`` 模块）；``TemporaryCanvas(height, width)`` 不创建
  终端、``refresh()`` 是无操作——不接管输入输出；
- ``get_from(x, y) -> (ord, colour, attr, bg)``，未写格恒为 ``(32, 7, 0, 0)``；
- ``move()``+``draw(char=...)`` 是画笔式线段；``fill_polygon`` 的填充行为
  不可靠（实测不落格），实心块改用**整行空格 + bg**；
- ``clear_buffer`` 语义与名字不符（会把颜色写成传入值），复位改为按行写
  空格（每帧 h 次 ``print_at``）；
- 内置 ``ParticleEmitter.update()`` 的擦除路径为持久缓冲设计，会把本桥
  「每帧全量重合成」的静态场景打洞——**只复用 ``Particle``**（物理/颜色
  渐进），发射循环自持（:class:`_Emitter`）。

透明语义：色号 0 = 背景色号。``bg==0`` 且空格 = 透明；``bg!=0`` = 实心
角色块（明确的覆盖）。每帧全量重合成（复位 → 静态场景 → 粒子），防残影。

RNG 隔离（方案硬约束）：内置效果用模块级 ``randint/uniform``，不可注入
RNG 的**一律不接**；粒子的 ``move``/发射闭包全部持有本桥专属
``random.Random``（种子由 ending_id 派生，确定性可复现、可测），绝不触碰
全局随机源（tests/test_cinematic.py 守）。
"""

from __future__ import annotations

import math
import random

from .cinematic_frame import CinematicFrame
from .cinematic_atmosphere import atmosphere, dissolve

try:  # 依赖锁定 asciimatics==1.15.0；缺失时桥不可用，结算自动回退纯文本。
    from asciimatics.particles import Particle
    from asciimatics.screen import TemporaryCanvas

    ASCIIMATICS_AVAILABLE = True
except ImportError:  # pragma: no cover - 环境无 asciimatics 时走静态回退
    ASCIIMATICS_AVAILABLE = False

    class Particle:  # 占位：类型注释用，运行期不会实例化
        pass


# ---------------------------------------------------------------------------
# 调色板：asciimatics 色号(0-7) → 游戏真彩 hex 角色。0 号恒为「透明/深底」。
# ---------------------------------------------------------------------------

PALETTES: dict[str, dict[int, str]] = {
    "A": {  # 初醒：靛青 → 暖金
        1: "#141a2e", 2: "#273356", 3: "#3d4d86", 4: "#5a6ab0",
        5: "#8a6f3f", 6: "#e8c47a", 7: "#f2dca0",
    },
    "B": {  # 重写：墨蓝、纸白、金色
        1: "#10131f", 2: "#1c2440", 3: "#2e3a66", 4: "#4a5f8e",
        5: "#b8a888", 6: "#e8e2d0", 7: "#d4af6a",
    },
    "C": {  # 放手：青灰、淡金
        1: "#1a2028", 2: "#28323e", 3: "#3a4a58", 4: "#54687a",
        5: "#8fa3b0", 6: "#c8d4d8", 7: "#d4c49a",
    },
    "D": {  # 共写：青色与紫金
        1: "#141c28", 2: "#1e3242", 3: "#2d5a6e", 4: "#4a9ab0",
        5: "#6a4a7e", 6: "#c8a86a", 7: "#e8d8b0",
    },
    "E": {  # 沉没：暗紫、灰蓝
        1: "#171226", 2: "#251d3d", 3: "#363054", 4: "#4a5570",
        5: "#6f7fa0", 6: "#9a7fb8", 7: "#a8b4d0",
    },
    "F": {  # 无梦：青灰逐渐褪色
        1: "#181c22", 2: "#242c36", 3: "#34404e", 4: "#4a5a6c",
        5: "#66788c", 6: "#8ea0b2", 7: "#b8c8d4",
    },
}
_DEFAULT_PALETTE = {
    1: "#14161c", 2: "#22252f", 3: "#343846", 4: "#4a4f60",
    5: "#6b7182", 6: "#9aa0b0", 7: "#c2c6d2",
}


def _palette(ending_id: str) -> dict[int, str]:
    return PALETTES.get(ending_id, _DEFAULT_PALETTE)


def _seed_for(ending_id: str) -> int:
    """ending_id → 确定性种子（str 种子受 PYTHONHASHSEED 影响不可用）。"""
    return int.from_bytes(ending_id.encode("utf-8"), "big") or 1


def _ease(p: float) -> float:
    """smoothstep：首尾静止、中段平滑。"""
    p = min(1.0, max(0.0, p))
    return p * p * (3.0 - 2.0 * p)


# ---------------------------------------------------------------------------
# 画布绘制助手（全部走 print_at；坐标画布内裁剪）
# ---------------------------------------------------------------------------

def _put(canvas, x: int, y: int, glyph: str, role: int, bg_role: int = 0) -> None:
    canvas.print_at(glyph, x, y, colour=role, bg=bg_role)


def _hline(canvas, x0: int, x1: int, y: int, glyph: str, role: int) -> None:
    if y < 0 or y >= canvas.height:
        return
    if x1 < x0:
        x0, x1 = x1, x0
    x0 = max(0, x0)
    x1 = min(canvas.width - 1, x1)
    if x1 >= x0:
        canvas.print_at(glyph * (x1 - x0 + 1), x0, y, colour=role, bg=0)


def _vline(canvas, x: int, y0: int, y1: int, glyph: str, role: int) -> None:
    if x < 0 or x >= canvas.width:
        return
    for y in range(min(y0, y1), max(y0, y1) + 1):
        if 0 <= y < canvas.height:
            canvas.print_at(glyph, x, y, colour=role, bg=0)


def _rect(canvas, x0: int, y0: int, x1: int, y1: int, role: int) -> None:
    """┌─┐│└┘ 矩形框（尺寸过小则不画）。"""
    if x1 - x0 < 2 or y1 - y0 < 2:
        return
    _hline(canvas, x0, x1, y0, "─", role)
    _hline(canvas, x0, x1, y1, "─", role)
    _vline(canvas, x0, y0 + 1, y1 - 1, "│", role)
    _vline(canvas, x1, y0 + 1, y1 - 1, "│", role)
    for cx, cy, glyph in ((x0, y0, "┌"), (x1, y0, "┐"), (x0, y1, "└"), (x1, y1, "┘")):
        _put(canvas, cx, cy, glyph, role)


def _rect_sparse(canvas, x0: int, y0: int, x1: int, y1: int, role: int,
                 density: float) -> None:
    """按确定性抖动稀疏化的残迹框（density 0..1）。"""
    if x1 - x0 < 2 or y1 - y0 < 2:
        return
    for x in range(x0, x1 + 1):
        if ((x * 7 + 3) % 97) / 97 < density:
            _put(canvas, x, y0, "─", role)
            _put(canvas, x, y1, "─", role)
    for y in range(y0 + 1, y1):
        if ((y * 11 + 5) % 97) / 97 < density:
            _put(canvas, x0, y, "│", role)
            _put(canvas, x1, y, "│", role)
    if density > 0.2:
        for cx, cy, glyph in ((x0, y0, "┌"), (x1, y0, "┐"), (x0, y1, "└"), (x1, y1, "┘")):
            _put(canvas, cx, cy, glyph, role)


# ---------------------------------------------------------------------------
# 发射器：asciimatics Particle 物理 + 自持循环（演出专属 RNG）
# ---------------------------------------------------------------------------

def _drift_move(particle):
    """匀速漂移（微尘穿缝）。"""
    particle.x += particle.dx
    particle.y += particle.dy
    return int(particle.x), int(particle.y)


def _fall_move(particle):
    """带微重力的下落（字符碎屑沉没）。"""
    particle.dy += 0.015
    particle.x += particle.dx
    particle.y += particle.dy
    return int(particle.x), int(particle.y)


class _Emitter:
    """演出专属发射器：每帧发射 ``per_frame`` 个粒子并推进一步。

    只复用 ``Particle`` 的物理与颜色渐进（``next()``/``last()``），
    擦除不做——本桥每帧全量重绘，旧位置自然被覆盖。
    """

    def __init__(self, new_particle, spawn_frames: int, per_frame: int = 1) -> None:
        self._new_particle = new_particle
        self._time_left = spawn_frames
        self._per_frame = per_frame
        self.particles: list = []

    def step(self) -> None:
        if self._time_left > 0:
            self._time_left -= 1
            for _ in range(self._per_frame):
                particle = self._new_particle()
                if particle is not None:
                    self.particles.append(particle)
        alive = []
        for particle in self.particles:
            if particle.time < particle.life_time:
                particle.next()  # 物理推进 + 字符/颜色渐进
                alive.append(particle)
        self.particles = alive

    def draw(self, canvas, width: int, height: int) -> None:
        for particle in self.particles:
            data = particle.last()
            if data is None:
                continue
            char, x, y, fg, attr, bg = data
            if 0 <= x < width and 0 <= y < height:
                canvas.print_at(char, x, y, colour=fg, attr=attr, bg=bg)


# ---------------------------------------------------------------------------
# 分镜：A 初醒 / E 沉没（方案文档 §六种结局的视觉分镜）
# ---------------------------------------------------------------------------

class _Shot:
    """一个镜头：时长（秒）+ 静态绘制 + 可选发射器/预生成工厂。

    ``prepare_fn`` 在镜头切入时调用一次，把**确定性预生成的静态数据**
    （笔迹段、雾点等）存进 ``bridge._shot_data``——绘制是每帧无状态
    重绘，静态内容不能在 draw 里用 RNG 现生成（会逐帧闪烁）。
    """

    def __init__(self, name, duration, draw_fn, emitters_fn=None, prepare_fn=None):
        self.name = name
        self.duration = duration
        self._draw_fn = draw_fn
        self._emitters_fn = emitters_fn
        self._prepare_fn = prepare_fn

    def prepare(self, bridge) -> None:
        if self._prepare_fn is not None:
            bridge._shot_data[self.name] = self._prepare_fn(bridge)

    def draw(self, canvas, local_t: float, progress: float, bridge) -> None:
        self._draw_fn(canvas, local_t, progress, bridge)

    def make_emitters(self, bridge) -> list:
        return self._emitters_fn(bridge) if self._emitters_fn else []


# ---- A 初醒：梦层轮廓退入暗处 → 中央细缝打开、微尘穿过 → 清晨门光 ----

def _a_arches(width: int, height: int) -> list[list[tuple[int, int]]]:
    """三条「梦层轮廓」倒拱（确定性的，只依赖尺寸）。"""
    cx = width // 2
    arches = []
    for spread in (0.30, 0.55, 0.80):
        pts = []
        for x in range(max(1, int(cx - width * spread)),
                       min(width - 1, int(cx + width * spread))):
            u = (x - cx) / max(1.0, width * spread)
            y = int(height * 0.14 + (1.0 - u * u) * height * 0.52)
            if 0 <= y < height:
                pts.append((x, y))
        arches.append(pts)
    return arches


def _draw_a_veil(canvas, local_t, p, bridge) -> None:
    """镜头 1（1.2s）：轮廓逐格稀疏、靛青逐级变暗。"""
    role = 4 if p < 0.35 else 3 if p < 0.7 else 2
    density = 1.0 - 0.9 * p
    for pts in _a_arches(bridge.width, bridge.height):
        for x, y in pts:
            if ((x * 7 + y * 13) % 97) / 97 < density:
                _put(canvas, x, y, "·" if (x + y) % 2 else ":", role)


def _draw_a_seam(canvas, local_t, p, bridge) -> None:
    """镜头 2（1.6s）：中央细缝自中心向上下生长，颜色靛蓝→暖金。"""
    w, h = bridge.width, bridge.height
    cx = w // 2
    half = int(h * 0.36 * _ease(p))
    role = 4 if p < 0.5 else 5
    for dy in range(-half, half + 1):
        y = h // 2 + dy
        if 0 <= y < h:
            _put(canvas, cx, y, "│", role)
    # 旧门柱遗迹：两侧对称点列，几乎熄灭。
    post_x = int(w * 0.30)
    hint = max(0, int(3 * (1.0 - p)))
    for y in range(2, h - 2, 4):
        if (y // 4) % 2 == 0 and hint > (y % 5):
            _put(canvas, cx - post_x, y, "·", 2)
            _put(canvas, cx + post_x, y, "·", 2)


def _draw_a_dawn(canvas, local_t, p, bridge) -> None:
    """镜头 3（1.2s）：门光涨满，暗金实心块 + 金色微光流动（呼吸）。"""
    w, h = bridge.width, bridge.height
    cx = w // 2
    door_w = 3 + int(9 * _ease(p))
    top = h // 2 - int(h * 0.30)
    bot = h // 2 + int(h * 0.30)
    frame = bridge.sim_frame
    left = cx - door_w // 2
    right = cx + door_w // 2
    _vline(canvas, left - 1, top, bot, "│", 6)
    _vline(canvas, right + 1, top, bot, "│", 6)
    _hline(canvas, left - 1, right + 1, top - 1, "─", 6)
    for y in range(top, bot + 1):
        for x in range(left, right + 1):
            shimmer = ((x * 3 + y * 5 + frame) % 11) < 3
            _put(canvas, x, y, " ", 6 if shimmer else 5, 5)


def _a_dust_emitters(bridge) -> list:
    """微尘：从两侧向中央细缝漂移（金→淡蓝→无的颜色渐进）。"""
    rng, fps = bridge.rng, bridge.fps
    w, h = bridge.width, bridge.height

    def new_particle():
        from_left = rng.random() < 0.5
        margin = max(2.0, w * 0.08)
        if from_left:
            x = rng.uniform(margin, w * 0.42)
            dx = 0.22 + rng.uniform(-0.04, 0.04)
        else:
            x = rng.uniform(w * 0.58, w - margin)
            dx = -0.22 - rng.uniform(-0.04, 0.04)
        return Particle("·+·", x, rng.uniform(2.0, h - 3.0), dx,
                        rng.uniform(-0.05, 0.05),
                        [(5, 0, 0), (7, 0, 0), (0, 0, 0)],
                        max(1, int(rng.uniform(0.8, 1.6) * fps)), _drift_move)

    per = 2 if bridge.quality == "high" else 1
    return [_Emitter(new_particle, int(1.6 * fps), per)]


def _a_dawn_emitters(bridge) -> list:
    """门光镜头的稀疏尘埃（飘过门面即散）。"""
    rng, fps = bridge.rng, bridge.fps
    w, h = bridge.width, bridge.height

    def new_particle():
        from_left = rng.random() < 0.5
        if from_left:
            x = rng.uniform(1.0, w * 0.45)
            dx = 0.15
        else:
            x = rng.uniform(w * 0.55, w - 2.0)
            dx = -0.15
        return Particle("·.", x, rng.uniform(2.0, h - 3.0), dx,
                        rng.uniform(-0.04, 0.04),
                        [(6, 0, 0), (5, 0, 0), (0, 0, 0)],
                        max(1, int(rng.uniform(0.7, 1.2) * fps)), _drift_move)

    return [_Emitter(new_particle, int(1.2 * fps), 1)]


# ---- E 沉没：门框收拢 → 字符碎屑下沉 → 最后一点光熄灭 ----

def _draw_e_collapse(canvas, local_t, p, bridge) -> None:
    """镜头 1（1.4s）：门框四边向内收拢。"""
    w, h = bridge.width, bridge.height
    inset = int(_ease(p) * min(w, h) * 0.20)
    x0 = int(w * 0.16) + inset
    x1 = int(w * 0.84) - inset
    y0 = int(h * 0.12) + inset
    y1 = int(h * 0.84) - inset
    role = 5 if p < 0.45 else 4
    _rect(canvas, x0, y0, x1, y1, role)


def _e_frame_bounds(bridge) -> tuple[int, int, int, int]:
    """收拢结束后的门框残迹范围（与 collapse 的终值一致）。"""
    w, h = bridge.width, bridge.height
    inset = int(min(w, h) * 0.20)
    return (int(w * 0.16) + inset, int(h * 0.12) + inset,
            int(w * 0.84) - inset, int(h * 0.84) - inset)


def _draw_e_sink(canvas, local_t, p, bridge) -> None:
    """镜头 2（1.8s）：门框残迹稀疏淡出，碎屑（发射器）下沉。"""
    x0, y0, x1, y1 = _e_frame_bounds(bridge)
    role = 3 if p < 0.5 else 2
    _rect_sparse(canvas, x0, y0, x1, y1, role, 1.0 - p)


def _draw_e_douse(canvas, local_t, p, bridge) -> None:
    """镜头 3（1.3s）：底部一点光缓慢熄灭（角色 6→5→4→2→无）。"""
    w, h = bridge.width, bridge.height
    cx = w // 2
    y0 = int(h * 0.78)
    if p > 0.92:
        return
    role = 6 if p < 0.3 else 5 if p < 0.55 else 4 if p < 0.8 else 2
    _put(canvas, cx, y0 - 1, "·", role)
    _put(canvas, cx - 1, y0, "─", role)
    _put(canvas, cx + 1, y0, "─", role)
    _put(canvas, cx, y0, "+", role)
    _put(canvas, cx, y0 + 1, "·", role)


def _e_debris_emitters(bridge) -> list:
    """字符碎屑：全屏缓慢下沉，微重力（紫→灰蓝→无）。"""
    rng, fps = bridge.rng, bridge.fps
    w, h = bridge.width, bridge.height
    chars = "·*+:/\\;,"

    def new_particle():
        return Particle(chars, rng.uniform(1.0, w - 2.0),
                        rng.uniform(-3.0, h * 0.35),
                        rng.uniform(-0.08, 0.08), rng.uniform(0.18, 0.5),
                        [(6, 0, 0), (4, 0, 0), (2, 0, 0), (0, 0, 0)],
                        max(1, int(rng.uniform(1.2, 2.4) * fps)), _fall_move)

    per = 3 if bridge.quality == "high" else 2
    return [_Emitter(new_particle, int(1.8 * fps), per)]


def _e_douse_emitters(bridge) -> list:
    """熄灭镜头的残余碎屑（低频，衬托寂静）。"""
    rng, fps = bridge.rng, bridge.fps
    w, h = bridge.width, bridge.height

    def new_particle():
        return Particle("·,", rng.uniform(1.0, w - 2.0), rng.uniform(-2.0, 4.0),
                        rng.uniform(-0.04, 0.04), rng.uniform(0.2, 0.45),
                        [(4, 0, 0), (2, 0, 0), (0, 0, 0)],
                        max(1, int(rng.uniform(1.0, 1.6) * fps)), _fall_move)

    return [_Emitter(new_particle, int(0.8 * fps), 1)]


# ---- B 重写：笔迹碎片回收 → 书写光标划过 → 题名凝定（静态为主，无粒子）----

def _b_prepare_scribbles(bridge) -> list:
    """预生成乱真笔迹段（确定性；切入镜头时一次，绘制不碰 RNG）。"""
    rng = bridge.rng
    w, h = bridge.width, bridge.height
    segments = []
    for _ in range(44):
        x0 = rng.uniform(2.0, w - 5.0)
        y0 = rng.uniform(2.0, h - 5.0)
        dx = 1 if rng.random() < 0.5 else -1
        dy = 1 if rng.random() < 0.5 else -1
        segments.append((x0, y0, dx, dy, int(rng.uniform(3, 9)),
                         3 if rng.random() < 0.6 else 2))
    return segments


def _draw_b_scribbles(canvas, local_t, p, bridge) -> None:
    """镜头 1（1.3s）：笔迹碎片逐段回收（变短、变稀）。"""
    segments = bridge._shot_data.get("scribbles") or []
    count = int(len(segments) * (1.0 - 0.85 * p))
    for x0, y0, dx, dy, length, role in segments[:count]:
        shrink = max(0, int(length * (1.0 - p * 0.8)))
        glyph = "/" if dx * dy > 0 else "\\"
        for k in range(shrink):
            x, y = int(x0) + dx * k, int(y0) + dy * k
            if 0 <= x < bridge.width and 0 <= y < bridge.height:
                _put(canvas, x, y, glyph, role)


def _draw_b_cursor(canvas, local_t, p, bridge) -> None:
    """镜头 2（1.7s）：书写光标扫过中行，身后留下稿纸线与金墨点。"""
    w, h = bridge.width, bridge.height
    cy = h // 2
    x0, x1 = int(w * 0.15), int(w * 0.85)
    _hline(canvas, x0, x1, cy - 2, "─", 5)
    _hline(canvas, x0, x1, cy + 2, "─", 5)
    x_now = x0 + int(_ease(p) * (x1 - x0))
    _hline(canvas, x0, x_now, cy, "─", 6)
    for x in range(x0, x_now + 1):
        if x % 9 == 4:
            _put(canvas, x, cy, "·", 7)
    if x0 < x_now <= x1:
        _put(canvas, x_now, cy, "║", 7)


def _draw_b_settle(canvas, local_t, p, bridge) -> None:
    """镜头 3（1.2s）：三行稿纸线凝定，金墨点缓慢明灭，墨屑熄灭。"""
    w, h = bridge.width, bridge.height
    cy = h // 2
    x0, x1 = int(w * 0.15), int(w * 0.85)
    _hline(canvas, x0, x1, cy - 2, "─", 5)
    _hline(canvas, x0, x1, cy + 2, "─", 5)
    _hline(canvas, x0, x1, cy, "─", 6)
    frame = bridge.sim_frame
    for x in range(x0, x1 + 1):
        if x % 9 == 4 and ((x // 9 + frame) % 7) < 2:
            _put(canvas, x, cy, "·", 7)
    density = (1.0 - p) * 0.12
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if ((x * 7 + y * 13) % 97) / 97 < density:
                _put(canvas, x, y, "·", 2)


# ---- C 放手：稿纸轮廓显现 → 移向远处 → 空白占据中心 ----

def _c_rect_bounds(bridge) -> tuple[int, int, int, int]:
    w, h = bridge.width, bridge.height
    return int(w * 0.18), int(h * 0.16), int(w * 0.82), int(h * 0.80)


def _draw_c_outline(canvas, local_t, p, bridge) -> None:
    """镜头 1（1.2s）：稿纸轮廓完整显现 + 内缘刻度点。"""
    x0, y0, x1, y1 = _c_rect_bounds(bridge)
    _rect(canvas, x0, y0, x1, y1, 5)
    for x in range(x0 + 3, x1 - 2, 6):
        _put(canvas, x, y0 + 2, "·", 4)
        _put(canvas, x, y1 - 2, "·", 4)


def _draw_c_recede(canvas, local_t, p, bridge) -> None:
    """镜头 2（1.6s）：轮廓向中心收拢、变淡（移向远处）。"""
    x0, y0, x1, y1 = _c_rect_bounds(bridge)
    inset = int(_ease(p) * min(bridge.width, bridge.height) * 0.26)
    role = 5 if p < 0.4 else 4 if p < 0.75 else 3
    _rect_sparse(canvas, x0 + inset, y0 + inset, x1 - inset, y1 - inset,
                 role, 1.0 - p * 0.55)


def _draw_c_blank(canvas, local_t, p, bridge) -> None:
    """镜头 3（1.4s）：空白占据中心，只留一枚淡金点缓慢呼吸。"""
    w, h = bridge.width, bridge.height
    frame = bridge.sim_frame
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if ((x * 5 + y * 11) % 211) / 211 < 0.05 * (1.0 - p):
                _put(canvas, x, y, "·", 2)
    _put(canvas, w // 2, h // 2, "·", 7 if frame % 24 < 12 else 5)


# ---- D 共写：两股笔迹从两侧出现，交错成双行，彼此保留颜色 ----

def _d_wave_char(x: int, phase: float) -> str:
    """按局部斜率取笔画方向（dx=1：下行 \\、上行 /）。"""
    return "\\" if math.cos(x * 0.35 + phase) > 0 else "/"


def _d_draw_stroke(canvas, w: int, h: int, x_from: int, x_to: int, cy: int,
                   phase: float, role: int) -> None:
    for x in range(max(0, x_from), min(w - 1, x_to) + 1):
        y = cy + round(math.sin(x * 0.35 + phase) * 1.6)
        if 0 <= y < h:
            _put(canvas, x, y, _d_wave_char(x, phase), role)


def _draw_d_converge(canvas, local_t, p, bridge) -> None:
    """镜头 1（1.5s）：左股青、右股紫金，从两侧向中心延伸。"""
    w, h = bridge.width, bridge.height
    cy = h // 2
    reach = 1 + int(_ease(p) * w * 0.48)
    _d_draw_stroke(canvas, w, h, 1, 1 + reach, cy, 0.0, 4)
    _d_draw_stroke(canvas, w, h, w - 3 - reach, w - 2, cy, math.pi, 6)


def _draw_d_interweave(canvas, local_t, p, bridge) -> None:
    """镜头 2（1.7s）：两股交错成双行，相位随时间缓慢起伏。"""
    w, h = bridge.width, bridge.height
    frame = bridge.sim_frame
    cy = h // 2
    drift = frame * 0.12
    _d_draw_stroke(canvas, w, h, 0, w - 1, cy - 2, drift, 4)
    _d_draw_stroke(canvas, w, h, 0, w - 1, cy + 2, math.pi + drift, 6)


def _draw_d_duet(canvas, local_t, p, bridge) -> None:
    """镜头 3（1.0s）：双行稳定，青金各自呼吸。"""
    w, h = bridge.width, bridge.height
    frame = bridge.sim_frame
    cy = h // 2
    drift = frame * 0.12
    _d_draw_stroke(canvas, w, h, 0, w - 1, cy - 2, drift,
                   4 if frame % 20 < 12 else 3)
    _d_draw_stroke(canvas, w, h, 0, w - 1, cy + 2, math.pi + drift,
                   6 if (frame + 10) % 20 < 12 else 5)


# ---- F 无梦：图形逐层变稀 → 雾止息 → 一条细线与静止 ----

def _f_prepare_fog(bridge) -> list:
    """预生成四层雾点（确定性）。"""
    rng = bridge.rng
    w, h = bridge.width, bridge.height
    return [(rng.uniform(1.0, w - 2.0), rng.uniform(1.0, h - 2.0), i % 4)
            for i in range(220)]


def _draw_f_thin_out(canvas, local_t, p, bridge) -> None:
    """镜头 1（1.5s）：雾点逐层变稀。"""
    w, h = bridge.width, bridge.height
    for x, y, layer in bridge._shot_data.get("thin_out") or []:
        if p < (layer + 1) / 5.0:
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h:
                _put(canvas, xi, yi, "·", 2 + layer)


def _draw_f_still(canvas, local_t, p, bridge) -> None:
    """镜头 2（1.5s）：雾止息（残点静止），中央细线生长。"""
    w, h = bridge.width, bridge.height
    for x, y, layer in bridge._shot_data.get("thin_out") or []:
        if layer == 3 and ((int(x) * 7 + int(y) * 13) % 97) / 97 < 0.5:
            _put(canvas, int(x), int(y), "·", 2)
    reach = int(_ease(p) * w * 0.28)
    _hline(canvas, w // 2 - reach, w // 2 + reach, h // 2, "─", 5)


def _draw_f_line(canvas, local_t, p, bridge) -> None:
    """镜头 3（1.2s）：只剩一条细线与极稀残余，几乎静止。"""
    w, h = bridge.width, bridge.height
    for x, y, layer in bridge._shot_data.get("thin_out") or []:
        if layer == 3 and ((int(x) * 7 + int(y) * 13) % 97) / 97 < 0.12:
            _put(canvas, int(x), int(y), "·", 2)
    role = 5 if p < 0.5 else 4
    _hline(canvas, int(w * 0.22), int(w * 0.78), h // 2, "─", role)


def _build_shots(ending_id: str) -> list[_Shot]:
    """按结局返回镜头序列；未知结局为空（回退纯文本）。"""
    if ending_id == "A":
        return [
            _Shot("veil", 1.2, _draw_a_veil),
            _Shot("seam", 1.6, _draw_a_seam, _a_dust_emitters),
            _Shot("dawn", 1.2, _draw_a_dawn, _a_dawn_emitters),
        ]
    if ending_id == "B":
        return [
            _Shot("scribbles", 1.3, _draw_b_scribbles,
                  prepare_fn=_b_prepare_scribbles),
            _Shot("cursor", 1.7, _draw_b_cursor),
            _Shot("settle", 1.2, _draw_b_settle),
        ]
    if ending_id == "C":
        return [
            _Shot("outline", 1.2, _draw_c_outline),
            _Shot("recede", 1.6, _draw_c_recede),
            _Shot("blank", 1.4, _draw_c_blank),
        ]
    if ending_id == "D":
        return [
            _Shot("converge", 1.5, _draw_d_converge),
            _Shot("interweave", 1.7, _draw_d_interweave),
            _Shot("duet", 1.0, _draw_d_duet),
        ]
    if ending_id == "E":
        return [
            _Shot("collapse", 1.4, _draw_e_collapse),
            _Shot("sink", 1.8, _draw_e_sink, _e_debris_emitters),
            _Shot("douse", 1.3, _draw_e_douse, _e_douse_emitters),
        ]
    if ending_id == "F":
        return [
            _Shot("thin_out", 1.5, _draw_f_thin_out, prepare_fn=_f_prepare_fog),
            _Shot("still", 1.5, _draw_f_still),
            _Shot("line", 1.2, _draw_f_line),
        ]
    return []


# ---------------------------------------------------------------------------
# 桥本体
# ---------------------------------------------------------------------------

class CinematicBridge:
    """离屏演出桥：给定时刻 → CinematicFrame（固定步长，与显示帧率解耦）。

    - ``advance(elapsed)``：固定 20Hz 仿真，high=20fps / low=10fps 显示，
      总时长不变；low 档减少粒子密度；同显示帧号返回缓存。
    - 演出专属 RNG（种子 = ending_id 派生）：resize/回退通过重建重演保持
      确定性；暂停冻结（``paused``）；``skip`` 由时间轴把 elapsed 推到终点。
    """

    def __init__(self, ending_id: str, width: int, height: int,
                 quality: str = "high") -> None:
        if not ASCIIMATICS_AVAILABLE:  # pragma: no cover
            raise RuntimeError("asciimatics 未安装，桥不可用")
        self.ending_id = ending_id
        self.quality = quality
        self.display_fps = 10 if quality == "low" else 20
        self.fps = 20  # Fixed physics step; quality changes display rate / density only.
        self.paused = False
        self._cancelled = False
        self._seed = _seed_for(ending_id)
        self.width = 0
        self.height = 0
        self.duration = 0.0
        self.sim_frame = 0
        self._setup(width, height)

    # ---- 生命周期 ----

    def _setup(self, width: int, height: int) -> None:
        self.width = max(8, int(width))
        self.height = max(4, int(height))
        self._canvas = TemporaryCanvas(self.height, self.width)
        self._shots: list[_Shot] = _build_shots(self.ending_id)
        self.duration = sum(shot.duration for shot in self._shots)
        self._rng = random.Random(self._seed)
        self._emitters: list = []
        self._shot_data: dict = {}
        self._shot_idx = -1
        self._sim_frame = 0
        self.sim_frame = 0
        self._frame_index = -1
        self._last_frame: CinematicFrame | None = None

    def resize(self, width: int, height: int) -> None:
        """缩放重建：确定性重演到当前帧（seed 不变 → 粒子序列一致）。"""
        if self._cancelled or (width, height) == (self.width, self.height):
            return
        target = self._frame_index
        self._setup(width, height)
        if target > 0:
            target = min(target, self._total_frames())
            while self._sim_frame < target:
                self._sim_frame += 1
                self._step_sim()
            self._frame_index = target
            self._last_frame = self._render()

    def cancel(self) -> None:
        self._cancelled = True
        self._canvas = None
        self._shots = []
        self._emitters = []
        self._last_frame = None

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def rng(self) -> random.Random:
        """演出专属随机源（发射器/粒子闭包只准用它）。"""
        return self._rng

    # ---- 推进 ----

    def _total_frames(self) -> int:
        return int(round(self.duration * self.fps))

    def _locate(self, t: float) -> tuple[int, _Shot, float, float]:
        """t 秒 → (镜头下标, 镜头, 镜头内局部时间, 进度 0..1)。"""
        t = min(max(0.0, t), self.duration) if self.duration else 0.0
        acc = 0.0
        for idx, shot in enumerate(self._shots):
            if t < acc + shot.duration or idx == len(self._shots) - 1:
                local = min(t - acc, shot.duration)
                return idx, shot, local, local / shot.duration if shot.duration else 1.0
            acc += shot.duration
        return -1, _Shot("void", 1.0, lambda *a: None), 0.0, 0.0

    def _step_sim(self) -> None:
        """仿真一步（发射 + 粒子物理），不绘制。"""
        idx, shot, _, _ = self._locate(self._sim_frame / self.fps)
        if idx != self._shot_idx:
            self._shot_idx = idx
            shot.prepare(self)
            self._emitters = shot.make_emitters(self)
        for emitter in self._emitters:
            emitter.step()

    def advance(self, elapsed: float) -> CinematicFrame:
        if self._cancelled:
            return CinematicFrame.blank(self.width, self.height)
        if self.paused and self._last_frame is not None:
            return self._last_frame
        displayed = int(max(0.0, elapsed) * self.display_fps + 1e-9) / self.display_fps
        target = min(int(round(displayed * self.fps)), self._total_frames())
        if target != self._frame_index or self._last_frame is None:
            if target < self._frame_index:  # 回退：确定性重建重演
                keep = self._last_frame
                self._setup(self.width, self.height)
                self._last_frame = keep
            while self._sim_frame < target:
                self._sim_frame += 1
                self._step_sim()
            self._frame_index = target
            self._last_frame = self._render()
        return self._last_frame

    # ---- 渲染 ----

    def _render(self) -> CinematicFrame:
        canvas = self._canvas
        w, h = self.width, self.height
        blank_row = " " * w
        for y in range(h):  # 复位（clear_buffer 语义不可靠，按行写空格）
            canvas.print_at(blank_row, 0, y, colour=7, bg=0)
        elapsed = self._sim_frame / self.fps
        idx, shot, local_t, progress = self._locate(elapsed)
        previous = None
        if idx > 0 and local_t < .22:
            last_shot = self._shots[idx-1]
            if last_shot.name not in self._shot_data:
                last_shot.prepare(self)
            last_shot.draw(canvas, last_shot.duration, 1.0, self)
            previous = atmosphere(self._read_frame(), self.ending_id, elapsed-local_t,
                                  self.duration, self.quality)
            for y in range(h):
                canvas.print_at(blank_row, 0, y, colour=7, bg=0)
        if shot.name not in self._shot_data:
            shot.prepare(self)  # t=0 首帧：_step_sim 尚未触发镜头切入
        shot.draw(canvas, local_t, progress, self)
        for emitter in self._emitters:
            emitter.draw(canvas, w, h)
        current = atmosphere(self._read_frame(), self.ending_id, elapsed, self.duration, self.quality)
        return dissolve(previous, current, local_t/.22) if previous is not None else current

    def _read_frame(self) -> CinematicFrame:
        """画布 → CinematicFrame：未写格(32,7,0,0) = 透明，不进掩码。"""
        palette = _palette(self.ending_id)
        w, h = self.width, self.height
        glyphs: dict[tuple[int, int], str] = {}
        colors: dict[tuple[int, int], tuple[str | None, str | None]] = {}
        for y in range(h):
            for x in range(w):
                cell = self._canvas.get_from(x, y)
                if cell is None:
                    continue
                code, colour, _attr, bg = cell
                if code == 32 and bg == 0:
                    continue  # 未绘制/擦除 = 透明（控件底色透出）
                glyphs[(x, y)] = chr(code)
                fg_hex = palette.get(colour) or palette.get(7, "#c2c6d2")
                bg_hex = palette.get(bg) if bg else None
                if code == 32 and bg_hex is not None:
                    fg_hex = bg_hex  # 实心块：前景=底色，渲染为纯色块
                colors[(x, y)] = (fg_hex, bg_hex)
        return CinematicFrame(width=w, height=h, glyphs=glyphs, colors=colors)
