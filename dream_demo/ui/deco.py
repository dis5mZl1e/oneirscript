"""界面装饰特效（2026-09-20）：numpy 调色板驱动的「镶边」动效。

与地图 FX（effects.py，作用于地图格叠加）分工：这里只管**界面镶边**——
- 渐变流光：牌匾边框逐字符取渐变色，相位随时间流动（主页/暂停标题共用）；
- 闪烁灯：✦ 装饰灯与边框整体做**平滑呼吸**（正弦明暗，不是硬闪）；
- 边框呼吸：世界视图里地图/侧栏边框在区域主题色与亮强调色之间缓慢过渡。

numpy 用在两处：色标插值生成渐变 LUT（导入期一次性）、呼吸相位的波形计算。
逐帧成本只是「查表 + 拼 Rich Text」（牌匾 3×60 字符，10fps），可忽略。

光敏安全：所有动效都是 ≥3.5s 周期的平滑正弦，无硬闪、无整帧反转；
``fx_quality=off`` 时全部回到静态（``t=None`` 即静态渲染）。
"""

from __future__ import annotations
from functools import lru_cache

import numpy as np

# 渐变 LUT 的档数：颜色数目远超字符数，流动时才足够平滑。
_LUT_STEPS = 48
_PALETTE_CACHE: dict[tuple, list[str]] = {}


@lru_cache(maxsize=4096)
def _parse_hex(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _to_hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(v)))) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def glow_palette(stops: tuple[str, ...], steps: int = _LUT_STEPS) -> list[str]:
    """hex 色标序列 → 首尾相接的环形渐变 LUT（numpy 线性插值，结果缓存）。

    环形（首尾同色相接）是为了流光绕回来时不跳变：调用方给的首尾色标
    应当相同（例如 深蓝→青→浅蓝→深蓝）。
    """
    key = (stops, steps)
    cached = _PALETTE_CACHE.get(key)
    if cached is not None:
        return cached
    rgb = np.array([_parse_hex(stop) for stop in stops], dtype=float)
    # 每个色标占 LUT 的一段；首尾相接（不含终点色标本身，endpoint=False）。
    lut = np.zeros((steps, 3), dtype=float)
    seg = np.linspace(0.0, float(len(stops) - 1), num=steps, endpoint=False)
    for i, u in enumerate(seg):
        j = int(u)
        frac = u - j
        lut[i] = rgb[j] * (1.0 - frac) + rgb[(j + 1) % len(stops)] * frac
    palette = [_to_hex(row) for row in lut]
    _PALETTE_CACHE[key] = palette
    return palette


def mix_hex(color_a: str, color_b: str, u: float) -> str:
    """两色线性混合（u=0 → a，u=1 → b）。呼吸/脉冲的基本算子。"""
    # Three scalar channels cost less than creating two tiny ndarrays for every
    # glass/border pixel. Keep the same operation order and banker rounding.
    a, b = _parse_hex(color_a), _parse_hex(color_b)
    return _to_hex(left * (1.0 - u) + right * u for left, right in zip(a, b))


def breathe_u(t: float, period: float, phase: float = 0.0) -> float:
    """0..1 的正弦呼吸包络：周期 period 秒，0 相时取谷值、半相峰值。

    平方后再取值（u*u）让「亮」的时间比「暗」的略短——灯的呼吸感。
    """
    wave = 0.5 - 0.5 * np.cos(2.0 * np.pi * (t / period) + phase)
    return float(wave * wave)


def pulse_hex(base: str, accent: str, t: float, period: float = 4.0,
              depth: float = 0.35, phase: float = 0.0) -> str:
    """整段边框的呼吸变色：base ↔ accent 之间缓慢往复（不逐字符渐变）。"""
    return mix_hex(base, accent, breathe_u(t, period, phase) * depth)


# 牌匾边框的流光色标：深靛 → 青 → 冰蓝 → 青 → 深靛（首尾相接成环）。
PLAQUE_FLOW_STOPS = ("#1e3a5f", "#67e8f9", "#bfe9ff", "#67e8f9", "#1e3a5f")
# 流速：每秒沿边框移动的 LUT 档数（48 档绕一圈 ≈ 6 秒，舒缓）。
PLAQUE_FLOW_SPEED = 8.0
# ✦ 装饰灯：暗态/亮态与呼吸周期（两枚灯相位差 π，交替明灭）。
ORNAMENT_DIM = "#4a4468"
ORNAMENT_BRIGHT = "#c9a0ff"
ORNAMENT_PERIOD = 3.5
# 边框呼吸的亮强调色：区域主题边框色向它缓慢过渡再回来（地图/侧栏反相）。
DECO_ACCENT = "#9ad1ff"


def flow_color(column: int, t: float, stops: tuple[str, ...] = PLAQUE_FLOW_STOPS,
               speed: float = PLAQUE_FLOW_SPEED, phase: float = 0.0) -> str:
    """第 column 个边框字符在 t 时刻的流光色。"""
    palette = glow_palette(stops)
    index = (int(column + t * speed + phase)) % len(palette)
    return palette[index]


def ornament_color(t: float, phase: float = 0.0) -> str:
    """✦ 装饰灯在 t 时刻的颜色（暗↔亮平滑呼吸）。"""
    return mix_hex(ORNAMENT_DIM, ORNAMENT_BRIGHT, breathe_u(t, ORNAMENT_PERIOD, phase))


# Textual 真边框（地图/侧栏 Pane）的追逐流光色标：比牌匾稍沉，绕框看得清
# 色相推移又不至于喧宾夺主。首尾相接成环。
BORDER_FLOW_STOPS = ("#24406b", "#4fb3e8", "#a8e4ff", "#4fb3e8", "#24406b")
# 流速：每秒推进的 LUT 档数（48 档绕一圈 ≈ 4 秒；四边各差 1/4 圈相位）。
BORDER_FLOW_SPEED = 12.0
# 流光与区域主题边框色的混合比例：主题色相保留，流光位移肉眼可辨。
BORDER_FLOW_MIX = 0.55


def border_flow_colors(base: str, t: float) -> tuple[str, str, str, str]:
    """Textual 边框四边（上/右/下/左）的动态渐变追逐色。

    同一条环形渐变 LUT，四边各差 1/4 圈相位，相位随时间推进——看上去
    一圈光沿边框顺时针 chase。每边再与区域主题边框色对半混合：
    纯 LUT 会盖掉区域配色，纯主题色又动不起来（旧版只有两色呼吸，
    幅度 35%、周期 4s，肉眼基本看不出来，用户反馈「实际没有动态渐变」）。
    """
    palette = glow_palette(BORDER_FLOW_STOPS)
    count = len(palette)
    head = int(t * BORDER_FLOW_SPEED)
    step = count // 4
    return tuple(
        mix_hex(base, palette[(head + k * step) % count], BORDER_FLOW_MIX)
        for k in range(4)
    )
