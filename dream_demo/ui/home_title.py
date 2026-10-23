"""主页标题：一块边框牌匾（3 行 × 60 列）。

主页原先只有一行裸标题，上方另有一块随时间重绘的色块动画图标；动画移除后
标题需要独自撑住主页的视觉重心，因此放大成牌匾：

- 宽度 60 列，与下方存档槽 / 导航按钮的 60 列行块左右对齐（共用一条居中轴）；
- 高度仍是 3 行——矮窗口（80×24）下标题再高就会把存档槽与导航按钮挤出屏幕，
  这正是既有布局刻意避免的情形，所以放大走「横向铺满 + 加边框」的路子，
  不额外占用行数；
- 三行都是等宽 60 列，Rich 的逐行居中因此不会错位；标题两侧各有一枚
  ✦（与旧的「梦之门」装饰同源），标题过长时自动收掉装饰。

纯函数、无状态：标题文本由调用方传入（中英切换后重新渲染即可）。

2026-09-20 装饰动效：传入 ``t``（单调秒）即渲染「流光边框 + ✦ 呼吸灯」——
边框逐字符取环形渐变色、相位随时间流动，两枚 ✦ 反相明灭；``t=None`` 保持
原静态渲染（颜色数学在 ui/deco.py，numpy 渐变 LUT）。布局两种模式完全一致。
"""

from __future__ import annotations

from math import pi

from rich.cells import cell_len
from rich.text import Text

from .deco import flow_color, ornament_color

# 与主页其它行块（.slot-row / .home-nav-row）同宽，保证共用一条居中轴。
TITLE_WIDTH = 60
ORNAMENT = "✦"
BORDER_STYLE = "#67e8f9"
ORNAMENT_STYLE = "#8a7fd4"
TITLE_STYLE = "bold bright_white"


def home_title_text(title: str, t: float | None = None, *, width: int = TITLE_WIDTH) -> Text:
    """把标题渲染成 3 行等宽（60 列）的边框牌匾。

    ``t=None``：静态（单一描边色）；``t=秒``：流光边框 + 呼吸装饰灯。
    """
    width = max(TITLE_WIDTH, width)
    inner = width - 2
    gap = _ornament_gap(title, inner)
    core = cell_len(title) + (2 * gap + 2 if gap else 0)
    pad = max(inner - core, 0)
    left = pad // 2
    right = pad - left
    text = Text()
    if t is None:
        text.append("╔" + "═" * inner + "╗\n", style=BORDER_STYLE)
        text.append("║" + " " * left, style=BORDER_STYLE)
        if gap:
            text.append(ORNAMENT + " " * gap, style=ORNAMENT_STYLE)
        text.append(title, style=TITLE_STYLE)
        if gap:
            text.append(" " * gap + ORNAMENT, style=ORNAMENT_STYLE)
        text.append(" " * right + "║\n", style=BORDER_STYLE)
        text.append("╚" + "═" * inner + "╝", style=BORDER_STYLE)
        return text
    # 流光模式：边框字符按「列号 + 时间相位」查环形渐变；四个角与竖边
    # 用同一列的颜色，绕框看就是一条连续的光带。
    text.append_text(_flow_line("╔", "═" * inner, "╗", t, 0))
    text.append("\n")
    text.append_text(_flow_row_mid(left, title, gap, right, t, width))
    text.append("\n")
    text.append_text(_flow_line("╚", "═" * inner, "╝", t, inner + 1))
    return text


def _flow_line(left: str, bar: str, right: str, t: float, phase: float) -> Text:
    """一行完整边框：╔══…═╗ / ╚══…═╝，逐字符流光。"""
    line = Text()
    line.append(left, style=flow_color(0, t, phase=phase))
    for column in range(len(bar)):
        line.append(bar[column], style=flow_color(column + 1, t, phase=phase))
    line.append(right, style=flow_color(len(bar) + 1, t, phase=phase))
    return line


def _flow_row_mid(left: int, title: str, gap: int, right: int, t: float,
                  width: int = TITLE_WIDTH) -> Text:
    """中间一行：║ 左空白 [✦] 标题 [✦] 右空白 ║——竖边随所在列流光，
    ✦ 装饰灯呼吸明灭（左右两枚相位差 π，交替亮）。"""
    line = Text()
    line.append("║", style=flow_color(0, t))
    line.append(" " * left, style=BORDER_STYLE)
    if gap:
        line.append(ORNAMENT, style=ornament_color(t, phase=0.0))
        line.append(" " * gap, style=BORDER_STYLE)
    line.append(title, style=TITLE_STYLE)
    if gap:
        line.append(" " * gap, style=BORDER_STYLE)
        line.append(ORNAMENT, style=ornament_color(t, phase=pi))
    line.append(" " * right, style=BORDER_STYLE)
    line.append("║", style=flow_color(width - 1, t))
    return line


def _ornament_gap(title: str, inner: int) -> int:
    """装饰与标题之间留几格空白；标题太长时逐级收紧，最后完全让位。"""
    for gap in (3, 2, 1):
        if cell_len(title) + 2 * gap + 2 <= inner:
            return gap
    return 0
