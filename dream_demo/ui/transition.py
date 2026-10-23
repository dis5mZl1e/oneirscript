"""上下层进层演出（纯函数，无 IO / 无状态 / 不依赖 numpy）。

设计文档：docs/superpowers/specs/2026-09-20-floor-transition-and-light-fx-design.md §2
演出与地图生成完全解耦：只做「时刻表 → 混合帧」的纯计算；旧层帧 / 新层帧
都由调用方（app.py）以渲染文本形式传入——两条数据都动不了游戏逻辑，
因此地图生成规律与玩家落点在构造上不可能被影响。
"""

from __future__ import annotations

import hashlib
import math

from rich.text import Text
from .frame_geometry import cell_ranges

# 时间轴（秒）：总长 1.4s，两相位交叠（设计文档 §2.2）。
PHASE_A = 0.7        # 相位A：旧层崩解（远→近合拢）
PHASE_B_DELAY = 0.45  # 相位B：新层生成（近→远扩散）的起跑延迟
PHASE_B_SPAN = 0.95
TOTAL = PHASE_B_DELAY + PHASE_B_SPAN  # = 1.4
FLICKER_WINDOW = 0.10  # 熄灭前的「抖碎」窗口
ASH_WINDOW = 0.05      # 点亮前的「灰烬」窗口
JITTER_RATIO = 0.15    # 每格时刻抖动 ±15% 相位时长
SPIKE_CHANCE = 0.05    # 5% 格子独立尖刺噪点
SPIKE_EXTRA = 0.25     # 尖刺最大额外提前/延后（秒）


def compose_image_frame(old, new, t, off_times, on_times, vw, vh,
                        old_vw=None, old_vh=None):
    """Apply the same world-independent transition schedule to real map pixels."""
    from PIL import Image, ImageDraw
    width,height = new.size
    cw,ch = width//vw,height//vh
    ow,oh = old_vw or vw,old_vh or vh
    ocw,och = old.width//ow,old.height//oh
    image = Image.new('RGB',new.size,(7,7,11))
    draw = ImageDraw.Draw(image)
    for y in range(vh):
        for x in range(vw):
            box = (x*cw,y*ch,(x+1)*cw,(y+1)*ch)
            if t >= on_times[(x,y)]:
                image.paste(new.crop(box),(box[0],box[1]))
            elif t >= on_times[(x,y)]-ASH_WINDOW:
                draw.point((x*cw+cw//2,y*ch+ch//2),fill='#8e8896')
            elif x < ow and y < oh and t < off_times[(x,y)]:
                tile = old.crop((x*ocw,y*och,(x+1)*ocw,(y+1)*och))
                if tile.size != (cw,ch):
                    tile = tile.resize((cw,ch))
                image.paste(tile,(box[0],box[1]))
    return image


def hash01(x: int, y: int, seed: int) -> float:
    """确定性 [0,1) 噪声：同 (x,y,seed) 永远同值（可测、可回放）。"""
    digest = hashlib.blake2b(f"{x},{y},{seed}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def cell_off_time_a(x: int, y: int, player: tuple[int, int], d_max: float, seed: int) -> float:
    """旧层格 (x,y) 的熄灭时刻：离玩家越远越早黑（远→近合拢）+ 抖动/尖刺。"""
    d = math.hypot(x - player[0], y - player[1]) / max(1e-6, d_max)
    base = (1.0 - d) * PHASE_A
    jitter = (hash01(x, y, seed) - 0.5) * 2 * JITTER_RATIO * PHASE_A
    if hash01(x, y, seed + 90001) < SPIKE_CHANCE:
        jitter += (hash01(x, y, seed + 90002) - 0.5) * 2 * SPIKE_EXTRA
    return max(0.0, min(PHASE_A, base + jitter))


def cell_on_time_b(x: int, y: int, player: tuple[int, int], d_max: float, seed: int) -> float:
    """新层格 (x,y) 的点亮时刻：玩家脚下最先亮（近→远扩散）+ 抖动/尖刺。"""
    d = math.hypot(x - player[0], y - player[1]) / max(1e-6, d_max)
    base = PHASE_B_DELAY + d * PHASE_B_SPAN
    jitter = (hash01(x, y, seed + 31) - 0.5) * 2 * JITTER_RATIO * PHASE_B_SPAN
    if hash01(x, y, seed + 90003) < SPIKE_CHANCE:
        jitter += (hash01(x, y, seed + 90004) - 0.5) * 2 * SPIKE_EXTRA
    # 下界不是 0：尖刺可能把时刻压到 0 以下，那样 t=0 的首帧就有格子已经是
    # 「灰烬」或「新层」——动画一开场就散着几个亮点。留出一个灰烬窗的宽度。
    return max(ASH_WINDOW, min(TOTAL, base + jitter))


# ---------------------------------------------------------------------------
# 帧预切与混合帧
# ---------------------------------------------------------------------------

BLACK_STYLE = "on #06060c"    # 崩解后的「无」：与 effects.WIPE_COLOR 同族
FLICKER_STYLE = "on #0a0a12"  # 熄灭前抖碎的暗底
ASH_STYLE = "on #101018"      # 点亮前的灰烬底
NOISE_CHARS = "·:·.·"


def flatten_styles(frame: Text) -> list[str | None]:
    """把整帧展平成「每个字符位的样式串」——只做一次。

    🔴 取格子内容**绝不能**用逐格 ``frame[start:end]`` 切片：rich 的 Text 切片
    每次都要重新物化整帧的 spans（O(总 span 数)），视口 50×36 实测 **2.8 秒**
    （旧帧+新帧 ≈5.6 秒）——演出还没起来就已经超过了它自己的总时长 1.4s，
    表现就是「按 n 之后卡死，最后无动画直接换层」。改成一次展平 + 纯字符串
    /列表切片后，同样视口降到毫秒级。
    """
    plain_len = len(frame.plain)
    styles: list[str | None] = [None] * plain_len
    for span in frame.spans:
        start = max(0, min(span.start, plain_len))
        end = max(0, min(span.end, plain_len))
        if end > start:
            styles[start:end] = [span.style] * (end - start)
    return styles


# 一个格子 = cell_h 个「物理行片段」，每个片段是 (文本, 逐字符样式)。
CellRows = list[tuple[str, list[str | None]]]


def cell_segments(
    frame: Text, vw: int, vh: int, cell_w: int, cell_h: int
) -> list[list[CellRows]]:
    """把整帧预切成 [y][x][row] = (文本, 逐字符样式) 的轻量表。

    行距 = 行宽 + 1 个换行符——与 app._fx_tick 的 stride 同一公式，
    漏算换行符会让切片逐行漂移。
    """
    plain = frame.plain
    styles = flatten_styles(frame)
    ranges = cell_ranges(frame, vw, vh, cell_w, cell_h)
    segments: list[list[CellRows]] = []
    for y in range(vh):
        row: list[CellRows] = []
        for x in range(vw):
            parts: CellRows = []
            for r in range(cell_h):
                start, end = ranges[(x, y)][r]
                parts.append((plain[start:end], styles[start:end]))
            row.append(parts)
        segments.append(row)
    return segments


def _blank_cell(style: str, cell_w: int, cell_h: int, glyph: str = " ") -> CellRows:
    text = (glyph + " " * cell_w)[:cell_w]
    return [(text, [style] * len(text)) for _ in range(cell_h)]


def _flicker_cell(x: int, y: int, t: float, seed: int, cell_w: int, cell_h: int) -> CellRows:
    idx = int(hash01(x, y, seed + int(t * 20)) * len(NOISE_CHARS)) % len(NOISE_CHARS)
    return _blank_cell(FLICKER_STYLE, cell_w, cell_h, NOISE_CHARS[idx])


def _append_runs(out: Text, line: str, styles: list[str | None]) -> None:
    """把一行按「连续同样式」合并成尽量少的 span 追加进 out。"""
    n = len(line)
    i = 0
    while i < n:
        style = styles[i]
        j = i + 1
        while j < n and styles[j] == style:
            j += 1
        if style:
            out.append(line[i:j], style)
        else:
            out.append(line[i:j])
        i = j


def compose_frame(
    old_segs: list[list[list[Text]]],
    new_segs: list[list[list[Text]]],
    t: float,
    off_times: dict[tuple[int, int], float],
    on_times: dict[tuple[int, int], float],
    vw: int,
    vh: int,
    cell_w: int,
    cell_h: int,
    seed: int,
    old_vw: int | None = None,
    old_vh: int | None = None,
) -> Text:
    """t 时刻的混合帧：旧格 → 抖碎 → 黑 →（新层独立推进）灰烬 → 新格。

    相位A/B 独立计时（设计文档 §2.2）：新格到点即亮，不等旧层全黑——
    0.45~0.7s 交叠区里玩家周围「旧刚熄、新已亮」。

    ``old_vw/old_vh``：旧层的网格尺寸（默认与新层同）。层型会改写地图长宽
    （长廊/迷宫），新旧层格数常常不同——旧网格之外的格子没有旧内容可崩解，
    直接按「已熄灭」的黑格处理，等新层自己点亮。
    """
    o_w = old_vw if old_vw is not None else vw
    o_h = old_vh if old_vh is not None else vh
    # 先按格选好本帧内容（每格只判一次，不随 cell_h 重复）。
    chosen: list[list[CellRows]] = [[None] * vw for _ in range(vh)]  # type: ignore[list-item]
    for y in range(vh):
        for x in range(vw):
            on_t = on_times[(x, y)]
            if t >= on_t:
                seg = new_segs[y][x]
            elif t >= on_t - ASH_WINDOW:
                seg = _blank_cell(ASH_STYLE, cell_w, cell_h, "·")
            elif not (x < o_w and y < o_h):
                seg = _blank_cell(BLACK_STYLE, cell_w, cell_h)
            elif t >= off_times[(x, y)]:
                seg = _blank_cell(BLACK_STYLE, cell_w, cell_h)
            elif t >= off_times[(x, y)] - FLICKER_WINDOW:
                seg = _flicker_cell(x, y, t, seed, cell_w, cell_h)
            else:
                seg = old_segs[y][x]
            chosen[y][x] = seg
    # 拼装：基帧是 vh*cell_h 行 × vw*cell_w 列（render_map 的布局），
    # 放大档（cell_h>1）也必须照这个行数输出，否则整屏错位。
    out = Text()
    total_lines = vh * cell_h
    emitted = 0
    for y in range(vh):
        for r in range(cell_h):
            texts: list[str] = []
            styles: list[str | None] = []
            for x in range(vw):
                text, st = chosen[y][x][r]
                if len(text) < cell_w:
                    gap = cell_w - len(text)
                    text = text + " " * gap
                    st = list(st) + [None] * gap
                texts.append(text)
                styles.extend(st)
            _append_runs(out, "".join(texts), styles)
            emitted += 1
            if emitted < total_lines:
                out.append("\n")
    return out
