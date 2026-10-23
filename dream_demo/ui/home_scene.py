"""梦境之门：不参与布局和输入的主页字符背景。"""
from __future__ import annotations

import math

import numpy as np
from rich.cells import cell_len, get_character_cell_size
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from textual.strip import Strip

from .home_title import TITLE_WIDTH, home_title_text
from .deco import flow_color, mix_hex
from .home_particles import HomeParticles

BASE = "#101018"
FOG = tuple(f"#{16+i:02x}{16+i*2:02x}{24+i*2:02x}" for i in range(16))
# 门内暖光（2026-10-08 主页景深）：同一雾梯度向暗琥珀偏移，只用于门柱之间。
FOG_WARM = tuple(mix_hex(c, "#2e2114", 0.5) for c in FOG)
FOG_DEPTH = tuple(tuple(mix_hex(cold, warm, i/8) for i in range(9))
                  for cold, warm in zip(FOG, FOG_WARM))


def dream_title_text(title: str, elapsed: float = 1.0, t: float | None = None,
                     *, width: int = TITLE_WIDTH) -> Text:
    level = min(1.0, max(0.0, elapsed / 0.9))
    color = "#{:02x}{:02x}{:02x}".format(
        int(45 + 195 * level), int(43 + 181 * level), int(55 + 132 * level))
    if cell_len(title) > TITLE_WIDTH:
        clipped = Text(title)
        clipped.truncate(TITLE_WIDTH)
        title = clipped.plain
    # 标题只占三行；不随时间改变文字尺寸。
    result = home_title_text(title, t=t, width=width)
    start = result.plain.find(title)
    if start >= 0:
        result.stylize(f"bold {color}", start, start + len(title))
        if t is not None:
            # Keep the plaque's original chase; carry a gentler highlight through
            # the title itself without changing its three-row geometry.
            for index, char in enumerate(title):
                if char.strip():
                    highlight = mix_hex(color, flow_color(index * 5, t * .65), .38 * level)
                    result.stylize(f"bold {highlight}", start+index, start+index+1)
    return result


def home_scene_text(width: int, height: int, t: float, quality: str, particles=None) -> Text:
    """确定性背景；门柱位于菜单两侧，中央留给稳定的导航。"""
    width, height = max(1, width), max(1, height)
    if quality == 'off':
        t = 0.0
    xs, ys = np.meshgrid(np.arange(width), np.arange(height))
    compact = width <= 80 or height < 22
    # Two terminal columns by one row form one square background pixel. Keep
    # grain fixed in space and animate bands at four steps per second.
    pixel_x = xs // 2
    pixel_time = math.floor(t * 4) / 4
    grain = np.array([[0, 2], [3, 1]])[ys % 2, pixel_x % 2] / 4 - .375
    fog = (np.sin(pixel_x * 0.24 + ys * 0.25 + pixel_time * 0.35)
           + np.sin(pixel_x * 0.086 - ys * 0.39 - pixel_time * 0.21) + 2) * 2
    chars = [[" "] * width for _ in range(height)]
    foreground = {}
    cx = (width - 1) / 2
    half = min((width - 7) / 2, 35 if compact else max(39, width * .43))
    top = 1
    arch_h = min(4, max(1, height // 6))
    # Quiet corners and a broad, dark doorway gradient give depth even where
    # menus leave large empty areas. Quantised palette keeps repaint costs low.
    distance = np.abs(pixel_x*2-cx) / max(1, half)
    aperture = np.maximum(0, 1-distance**2)
    depth = np.maximum(0, 1-np.abs(ys-height*.55)/max(1, height*.7))
    levels = np.clip((np.floor((fog + aperture*depth*3 + grain)/3)*3).astype(np.int8), 0, 15)
    warmth = np.clip((aperture*depth*np.clip((ys-arch_h)/max(1, height*.25),0,1)*2).astype(np.int8)*4,0,8)
    for x in range(width):
        d = abs(x - cx) / max(1, half)
        if d <= 1:
            y = top + round(arch_h * (1 - math.sqrt(max(0, 1 - d*d))))
            if y < height:
                chars[y][x] = "─" if d < .55 else "╱" if x < cx else "╲"
                foreground[(x, y)] = "#b89d68" if quality == "off" else mix_hex("#b89d68", flow_color(x, t), .65)
                if not compact and y+2 < height:
                    chars[y+2][x] = '─' if d < .55 else '╱' if x < cx else '╲'
                    foreground[(x, y+2)] = '#504c42'
    for y in range(top + arch_h + 1, max(top + arch_h + 1, height - 1)):
        for x in (round(cx - half), round(cx + half)):
            if 0 <= x < width:
                chars[y][x] = "│"
                phase = y if x < cx else width + height - y
                foreground[(x, y)] = "#766a52" if quality == "off" else mix_hex("#b89d68", flow_color(phase, t), .7)
                if y % 5 == 0:
                    chars[y][x] = '╪'
                    foreground[(x, y)] = mix_hex('#b89d68', flow_color(phase, t), .35)
        if not compact and y % 3 == 0:
            for x in (round(cx - half - 2), round(cx + half + 2)):
                if 0 <= x < width:
                    chars[y][x] = ":"
                    foreground[(x, y)] = "#394650"
    stars = (4 if compact else 8) if quality == "low" else (8 if compact else 22)
    for i in range(stars):
        x = (i * 37 + 7) % width
        # 近景粒子移动稍快、更亮；远景稍慢、更暗（2026-10-08 景深分层）。
        speed = 0.10 if i % 2 == 0 else 0.24
        y = (i * 13 + 2 + int(t * speed)) % height
        if abs(x - cx) < 31 and y >= 3:
            continue
        chars[y][x] = "." if i % 4 else "+"
        glow = int((58 if i % 2 == 0 else 75) + 35 * math.sin(t * 0.8 + i))
        foreground[(x, y)] = f"#{glow:02x}{glow+8:02x}{glow+12:02x}"
    # 内层刻纹（柱内侧）与外门廓（柱外侧短刻柱）：非紧凑布局才画。
    inner_top = top + arch_h + 1
    if not compact:
        for y in range(inner_top, max(inner_top, height - 2)):
            if y % 3 == 0:
                for x in (round(cx - half) + 2, round(cx + half) - 2):
                    if 0 <= x < width and not chars[y][x].strip():
                        chars[y][x] = "·"
                        foreground[(x, y)] = "#55482e"
            if y % 2 == 0:
                for x in (round(cx - half) - 2, round(cx + half) + 2):
                    if 0 <= x < width and y < height - 2 and not chars[y][x].strip():
                        chars[y][x] = ":"
                        foreground[(x, y)] = "#2c3140"
    # 穿门星尘：只在门内缓慢横飘（「·」不进星点计数口径）。
    dust = (2 if quality == "off" else (3 if quality == "low" else 6)) if particles is None else 0
    span = max(1, int(half) - 2)
    rows = max(1, height - inner_top - 1)
    for i in range(dust):
        x = round(cx) - span + (i * 13 + int(t * (2.0 + (i % 3)))) % (2 * span)
        y = inner_top + (i * 5 + int(t * (1.2 + (i % 2)))) % rows
        if abs(x - cx) < half - 1 and inner_top <= y < height - 1 and not chars[y][x].strip():
            chars[y][x] = "·"
            foreground[(x, y)] = "#8a7a52"
    for (x, y), (glyph, color) in (particles or {}).items():
        if 0 <= x < width and 0 <= y < height and not chars[y][x].strip():
            chars[y][x] = glyph
            foreground[(x, y)] = color
    # A small reflection at the foot of the portal; never a solid light block.
    if height >= 18:
        for row in range(height-3, height-1):
            spread = max(1, int(half*.7) - (row-height+3)*4)
            for x in range(max(0, round(cx)-spread), min(width, round(cx)+spread+1)):
                if not chars[row][x].strip() and (x+row) % 5 == 0:
                    chars[row][x] = '─' if row == height-3 else '·'
                    foreground[(x, row)] = '#534833'
    out = Text()
    for y in range(height):
        if y:
            out.append("\n")
        run, last = "", None
        for x in range(width):
            # 整个门景连续铺底；按钮由更高的控件层保留稳定底色。
            # 门柱之间的格子用暖雾梯度（门内暖光），其余维持冷雾。
            bg = FOG_DEPTH[int(levels[y,x])][int(warmth[y,x])]
            style = f"{foreground.get((x, y), '#52646d')} on {bg}"
            if last != style and run:
                out.append(run, style=last)
                run = ""
            run += chars[y][x]
            last = style
        out.append(run, style=last)
    return out


class DreamBackdropMixin:
    """Textual 的透明底仍取祖先底色；显式合成兄弟门景的空白列。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_class("dream-backdrop")

    def render_line(self, y: int) -> Strip:
        foreground = super().render_line(y)
        scene = self.app.query_one(HomeScene)
        if not scene.display or not scene.size.width:
            return foreground
        x = self.content_region.x - scene.content_region.x
        sy = self.content_region.y - scene.content_region.y + y
        if sy < 0 or sy >= scene.size.height:
            return foreground
        backdrop = scene.render_line(sy).crop(x, x + self.content_size.width)
        plain = foreground.text
        if not plain.strip(" "):
            return backdrop.adjust_cell_length(foreground.cell_length)
        # 一行文字/牌匾内部的空格属于文字间距，不能塞进门拱或星尘。
        first = cell_len(plain) - cell_len(plain.lstrip(" "))
        last = cell_len(plain.rstrip(" "))
        result = []
        column = 0
        previous_bg = Style(bgcolor=BASE)
        for segment in foreground:
            if segment.control:
                result.append(segment)
                continue
            for char in segment.text:
                width = get_character_cell_size(char)
                if char == " " and not first <= column < last:
                    result.extend(backdrop.crop(column, column + 1))
                    column += 1
                    continue
                if width:
                    sample = next(iter(backdrop.crop(column, column + width)), None)
                    previous_bg = Style(bgcolor=sample.style.bgcolor) if sample and sample.style else Style(bgcolor=BASE)
                result.append(Segment(char, (segment.style or Style()) + previous_bg))
                column += width
        return Strip(result, foreground.cell_length)


class DreamStatic(DreamBackdropMixin, Static):
    pass


class DreamVertical(DreamBackdropMixin, Vertical):
    pass


class DreamHorizontal(DreamBackdropMixin, Horizontal):
    pass


class HomeScene(Static):
    DEFAULT_CSS = """
    HomeScene {
        position: absolute;
        offset: 0 0;
        width: 100%; height: 100%;
        layer: dream;
        background: #101018;
        overflow: hidden;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(disabled=True, **kwargs)
        self._scene_key = None
        self.frames_drawn = 0
        self.particles = HomeParticles()

    def paint(self, t: float, quality: str) -> None:
        width, height = self.size
        if not width or not height:
            return
        step = 0 if quality == "off" else int(t * (10 if quality == "low" else 20))
        key = (width, height, quality, step)
        if key == self._scene_key:
            return
        self._scene_key = key
        self.frames_drawn += 1
        elapsed = step / (10 if quality == "low" else 20)
        dust = self.particles.frame(width, height, elapsed, quality)
        self.update(home_scene_text(width, height, elapsed, quality, dust))
        for widget in self.app.query(".dream-backdrop"):
            if widget.display:
                widget.refresh()

    def on_resize(self) -> None:
        # off 档没有定时器：首个布局完成或窗口缩放也必须补画静态门景。
        self.app._home_tick()
