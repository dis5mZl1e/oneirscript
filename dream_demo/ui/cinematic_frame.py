"""统一演出帧（2026-10-08）：离屏效果 → Textual 控件之间的纯数据帧协议。

管线（docs/asciimatics-integration-plan.md）：

    演出事件/已结算快照 → 分镜时间轴（cinematic_timeline）
      → 离屏效果（asciimatics_bridge）→ **统一帧适配（本模块）**
      → Rich/Textual 控件

CinematicFrame 是纯数据：不依赖 Textual、不依赖 asciimatics，坐标一律是
**终端列行**（x=列、y=行、0 起），与世界地图格无关——地图格走 effects.py
的 FxFrame，两条通道互不掺和。

透明语义（覆盖掩码独立于空格，方案文档硬约束）：

- 某格不在 ``glyphs`` 里          = 未绘制，完全透明（控件底色透出）；
- 在 ``glyphs`` 里且 bg 为 None   = 前景字符，背景透明；
- 在 ``glyphs`` 里且 bg 为 hex    = 实心底色块——**明确的擦除/色块是一次
  覆盖**，不是「粒子清理产生的空格写成黑块」。

asciimatics 的索引色（0–7 色号）由 asciimatics_bridge 按各结局调色板
翻译成 hex 再进本模块；本模块只认真彩 hex。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.cells import get_character_cell_size
from rich.text import Text


@dataclass(frozen=True)
class CinematicFrame:
    """一帧演出：字符掩码 + 颜色掩码（键都是 (x, y) 终端列行）。"""

    width: int
    height: int
    glyphs: dict[tuple[int, int], str] = field(default_factory=dict)
    colors: dict[tuple[int, int], tuple[str | None, str | None]] = field(
        default_factory=dict)  # (fg, bg)；None = 该侧透明

    @classmethod
    def blank(cls, width: int, height: int) -> "CinematicFrame":
        """全透明空帧。"""
        return cls(width=width, height=height)

    @property
    def painted_cells(self) -> int:
        """已绘制的格数（性能探针用）。"""
        return len(self.glyphs)

    def put(self, x: int, y: int, glyph: str,
            fg: str | None = None, bg: str | None = None) -> None:
        """写一格（构建侧便捷方法；宽字符请调用方自行保证占 1 格）。"""
        self.glyphs[(x, y)] = glyph
        self.colors[(x, y)] = (fg, bg)

    def row_cells(self, y: int) -> list[tuple[str, str | None, str | None]]:
        """第 y 行逐格展开：(glyph, fg, bg)；未绘制格 = (" ", None, None)。"""
        row: list[tuple[str, str | None, str | None]] = []
        for x in range(self.width):
            glyph = self.glyphs.get((x, y))
            if glyph is None:
                row.append((" ", None, None))
            else:
                fg, bg = self.colors.get((x, y), (None, None))
                row.append((glyph, fg, bg))
        return row

    def to_rich_text(self) -> Text:
        """整帧渲染为 Rich Text（行合并同款式段；行数 = height）。"""
        out = Text()
        for y in range(self.height):
            if y:
                out.append("\n")
            run: list[str] = []
            last: str | None = None
            for x in range(self.width):
                glyph = self.glyphs.get((x, y))
                if glyph is None:
                    style = None
                else:
                    fg, bg = self.colors.get((x, y), (None, None))
                    style = _cell_style(fg, bg)
                if style != last and run:
                    out.append("".join(run), style=last)
                    run = []
                run.append(glyph if glyph is not None else " ")
                last = style
            if run:
                out.append("".join(run), style=last)
        return out


def _cell_style(fg: str | None, bg: str | None) -> str | None:
    """(fg, bg) → Rich 样式串。实心空格块 = fg 取 bg（渲染为纯色块）。"""
    if bg is not None:
        return f"{fg or bg} on {bg}"
    if fg is not None:
        return fg
    return None


def compose_over(frame: CinematicFrame | None, lines: list[tuple[str, str | None]],
                 width: int) -> Text:
    """把前景文本行（settlement 正文）叠进演出帧（背景分镜）。

    - ``lines``：[(文本, Rich样式或None)]，从第 0 行开始铺（与旧版
      SettlementScreen 逐行 append 的版式完全一致，含空行）；
    - ``frame`` 为 None：等价于旧行为——纯文本输出（零回归路径）；
    - 有帧：未覆盖的列/行铺帧底（透明格落到控件底色），前景字符采样
      所在列的帧底色并追加 ``on {bg}``（与 home_scene.DreamBackdropMixin
      同一手法：文字自带前景色、底色随背景），宽字符按终端列宽跨列。
    """
    out = Text()
    rows = max(len(lines), frame.height if frame else 0)
    for y in range(rows):
        if y:
            out.append("\n")
        bg_row = frame.row_cells(y) if frame is not None and y < frame.height else None
        text, style = lines[y] if y < len(lines) else ("", None)
        for run_text, run_style in _compose_row(bg_row, text, style, width):
            out.append(run_text, style=run_style)
    return out


def _compose_row(bg_row: list[tuple[str, str | None, str | None]] | None,
                 line_text: str, line_style: str | None,
                 width: int) -> list[tuple[str, str | None]]:
    """单行合成：返回 [(文本, 样式)] 游程。见 :func:`compose_over`。"""
    if bg_row is None:
        return [(line_text, line_style)] if line_text else []
    # 前景字符 → 起始列映射（宽字符占 cw 列）。
    covers: dict[int, tuple[str, str | None, int]] = {}
    col = 0
    for ch in line_text:
        cw = get_character_cell_size(ch)
        if cw == 0:
            # Variation selectors / combining marks belong to the previous glyph.
            if covers:
                previous = next(reversed(covers))
                glyph, style, size = covers[previous]
                covers[previous] = (glyph + ch, style, size)
            continue
        covers[col] = (ch, line_style, cw)
        col += cw
    total = max(width, col)
    runs: list[tuple[str, str | None]] = []

    def push(text: str, style: str | None) -> None:
        if not text:
            return
        if runs and runs[-1][1] == style:
            runs[-1] = (runs[-1][0] + text, style)
        else:
            runs.append((text, style))

    c = 0
    while c < total:
        cover = covers.get(c)
        if cover is not None:
            ch, st, cw = cover
            bg = bg_row[c][2] if c < len(bg_row) else None
            if bg:
                st = f"{st} on {bg}" if st else f"on {bg}"
            push(ch, st)
            c += cw
            continue
        if c < len(bg_row):
            glyph, fg, bg = bg_row[c]
            push(glyph, _cell_style(fg, bg) if glyph != " " or bg else None)
        else:
            push(" ", None)
        c += 1
    return runs
