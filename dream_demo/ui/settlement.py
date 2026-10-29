"""结算画面（2026-09-19 建；2026-10-08 接入背景分镜演出）。

覆盖地图区，30FPS 帧计数驱动五个阶段：

  S0 暗场   面板合拢（0.8s）——世界隐去，只剩深色底
  S1 题名   分隔线自中心向两侧生长，题名逐字浮现 + 副题
  S2 叙事   结局正文逐行打字机
  S3 数值   本局统计逐行滑入，数字自 0 滚动到终值
  S4 尾声   记忆清单 + 呼吸的「按任意键返回主页」

背景分镜（2026-10-08）：按 ending_id 选择结局主视觉（asciimatics 离屏
管线，见 cinematic_timeline / asciimatics_bridge），正文与统计作为稳定
前景叠在其上。质量档 ``fx_quality``：high/low 接演出（20/10fps，总时长
不变），off 或 asciimatics 缺失或该结局尚无分镜时**完全回退旧行为**
（纯文本，零回归）。feed/skip/hide 与输入语义不变。

输入口径（ui.input）：S1–S3 任意键 = 快进到尾声；S4 任意键 = 返回主页。
数据装载走 :meth:`feed`（每个 state 只装一次），:meth:`tick` 由游戏的
帧定时器驱动（与 FloatingToast 同一先例）。
"""

from __future__ import annotations

from rich.text import Text
from textual.scroll_view import ScrollView
from textual.geometry import Size
from textual.strip import Strip
from textual.visual import Visual, visualize

from ..core.content import EPILOGUE_ENDINGS, ITEM_DEFINITIONS
from ..i18n import tr
from .cinematic_frame import compose_over
from .cinematic_timeline import MIN_HEIGHT, MIN_WIDTH, CinematicTimeline
from .ornament_frame import OrnamentBorderMixin

# 各阶段帧数（30fps）。
DARK_FRAMES = 24
SEP_FRAMES = 16
TITLE_FRAMES = 48
LINE_FRAMES = 24
STAT_FRAMES = 8
ROLL_FRAMES = 20


class SettlementScreen(OrnamentBorderMixin, ScrollView, can_focus=False, inherit_bindings=False):
    """结算演出面板。单实例，feed 一次，tick 推进，skip 快进。"""

    DEFAULT_CSS = """
    SettlementScreen {
        layer: overlay;
        position: absolute;
        width: 100%; height: 100%;
        background: #0b0b12 97%;
        border: round #59627a;
        padding: 1 2;
        overflow-y: auto;
        overflow-x: hidden;
        display: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.active = False
        self.frame = 0
        self._ending: dict = {}
        self._ending_id = ""
        self._narrative: list[str] = []
        self._stats: list[tuple[str, str]] = []  # (标签, 终值文本) —— 纯文本滑入
        self._rolls: list[tuple[str, int]] = []  # (标签, 数值) —— 数字滚动
        self._memory_note = ""
        self._prompt = ""
        self._review_lines = []
        self._timeline: CinematicTimeline | None = None
        self._cinema_lines = None
        self._cinema_width = 0
        self._content = Text()

    def update(self, content=""):
        self._content = content
        self._cinema_lines = None
        if self.is_mounted:
            self._layout_lines()
        self.refresh()

    def render(self):
        return self._content

    def _layout_lines(self):
        width = max(1, self.size.width)
        self._cinema_width = width
        visual = visualize(self, self._content)
        self._cinema_lines = Visual.to_strips(self, visual, width, None,
                                             self.visual_style, pad=True)
        self.virtual_size = Size(width, len(self._cinema_lines))

    def on_resize(self):
        self._cinema_lines = None
        if self.is_mounted:
            self._layout_lines()

    def render_line(self, y: int) -> Strip:
        # Static's default cache truncates at viewport height and ignores scrolling.
        # Render full wrapped text once per frame; scroll only selects its visible rows.
        width = self.size.width
        if self._cinema_lines is None or self._cinema_width != width:
            self._layout_lines()
        row = y + self.scroll_offset.y
        if 0 <= row < len(self._cinema_lines):
            return self._cinema_lines[row]
        return Strip.blank(width, self.rich_style)

    # ---- 装载 ----

    def feed(self, state, *, quality: str | None = None,
             size: tuple[int, int] | None = None) -> None:
        """从 state 装配演出内容（run_over && ending_id 时由 app 调用一次）。

        ``quality``/``size``：测试直传入口；缺省时从 app 配置与内容区取。
        """
        ending = EPILOGUE_ENDINGS.get(state.ending_id) or {"title": "初醒", "subtitle": "", "lines": ["你醒了。"]}
        self._ending = ending
        self._ending_id = state.ending_id or ""
        flags = state.epilogue_flags or {}
        fell_note = (
            tr("你败给了执笔者，故事被写进了它的稿纸。") if state.depth >= 28 and flags.get("fell_to_scribe")
            else tr("你在深层边界沉没，梦收回了它的作者。")
        )
        self._narrative = [
            tr(line).format(clues=flags.get("clues", 0), kills=state.run_stats.get("kills", 0),
                            rounds=state.time, depth=state.depth, fell_note=fell_note)
            for line in ending.get("lines", ())
        ]
        if flags.get('scribe_defeated') and state.ending_id in ('C','D'):
            from ..core.epilogue import say
            self._narrative[0]=say('after_c' if state.ending_id=='C' else 'after_d')
        stats = state.run_stats or {}
        deepest = max(getattr(state, "deepest_depth", 1) or 1, state.depth if state.depth > 0 else 1)
        self._rolls = [
            (tr("深潜回合"), int(state.time)),
            (tr("抵达最深层"), int(deepest)),
            (tr("击破异象"), int(stats.get("kills", 0))),
            (tr("复合事件"), int(stats.get("events", 0))),
            (tr("引燃次数"), int(stats.get("ignitions", 0))),
            (tr("物品使用"), int(stats.get("items_used", 0))),
            (tr("承受创伤"), int(stats.get("hits_taken", 0))),
        ]
        if state.ending_id in ("A", "B", "C", "D"):
            self._rolls.append((tr("自我线索"), int(flags.get("clues", 0))))
        memories = list(getattr(state, "memory_fragments", []) or [])
        if memories:
            names = "、".join(tr(_memory_name(mid)) for mid in memories[:3])
            more = tr("……") if len(memories) > 3 else ""
            self._memory_note = tr("{count} 段记忆沉入长夜：{names}{more}", count=len(memories), names=names, more=more)
        else:
            self._memory_note = tr("这一局没有带走任何记忆碎片。")
        self._prompt = tr("按任意键返回主页")
        if state.difficulty_revision >= 2 and not state.realm_id:
            from ..core.failure_review import build_review, review_lines
            self._review_lines = review_lines(build_review(state))
        else:
            self._review_lines = []
        if state.run_start_choices:
            self._prompt = tr("R 沿用开局快速再开 · T 独立新手教程 · 其他键返回主页")
        self.active = True
        self.frame = 0
        self.scroll_y = self.scroll_target_y = 0
        self.styles.display = "block"
        self._timeline = self._make_timeline(quality, size)
        self.update(Text())

    def hide(self) -> None:
        self.active = False
        self.styles.display = "none"
        if self._timeline is not None:
            self._timeline.cancel()
            self._timeline = None

    @property
    def finished(self) -> bool:
        """演出是否已到尾声（S4）——任意键此时返回主页。"""
        return self.active and self._stage() == "coda"

    # ---- 背景分镜 ----

    def _fx_quality(self) -> str | None:
        """fx_quality 设置；无 app 上下文（裸测试）返回 None = 不接演出。"""
        try:
            return str(self.app.config.get("fx_quality") or "off")
        except Exception:
            return None

    def _safe_content_size(self) -> tuple[int, int]:
        try:
            return self.content_size.width, self.content_size.height
        except Exception:
            return 0, 0

    def _make_timeline(self, quality: str | None,
                       size: tuple[int, int] | None) -> CinematicTimeline | None:
        quality = quality if quality is not None else self._fx_quality()
        if quality in (None, "off"):
            return None
        w, h = size if size else self._safe_content_size()
        if w < MIN_WIDTH or h < MIN_HEIGHT:
            return None
        return CinematicTimeline(self._ending_id, w, h, quality)

    def _sync_timeline(self) -> None:
        """每帧同步：内容区就绪/变化时补建或重建时间轴（feed 时尺寸可能未定型）。"""
        quality = self._fx_quality()
        if quality is None:
            return
        size = self._safe_content_size()
        if quality == 'off' or size[0] < MIN_WIDTH or size[1] < MIN_HEIGHT:
            if self._timeline is not None:
                self._timeline.cancel()
                self._timeline = None
            return
        if self._timeline is not None and self._timeline.quality != quality:
            self._timeline.cancel()
            self._timeline = None
        if self._timeline is None:
            self._timeline = CinematicTimeline(self._ending_id, size[0], size[1], quality)
            if self.finished:
                self._timeline.skip()
        elif (self._timeline.width, self._timeline.height) != size:
            self._timeline.resize(*size)

    # ---- 分镜推进 ----

    def skip(self) -> None:
        """快进：直接呈现尾声（S4），并落在呼吸提示的可见相。"""
        target = self._coda_frame()
        if (target // 30) % 2:
            target += 30 - (target % 30)
        self.frame = target
        if self._timeline is not None:
            self._timeline.skip()

    def _narrative_start(self) -> int:
        return DARK_FRAMES + SEP_FRAMES + TITLE_FRAMES

    def _stats_start(self) -> int:
        return self._narrative_start() + LINE_FRAMES * len(self._narrative)

    def _coda_frame(self) -> int:
        return self._stats_start() + STAT_FRAMES * len(self._rolls) + ROLL_FRAMES

    def _stage(self) -> str:
        if self.frame < DARK_FRAMES:
            return "dark"
        if self.frame < DARK_FRAMES + SEP_FRAMES + TITLE_FRAMES:
            return "title"
        if self.frame < self._stats_start():
            return "narrative"
        if self.frame < self._coda_frame():
            return "stats"
        return "coda"

    def tick(self) -> None:
        """帧推进：同步背景时间轴，重建当前帧的演出文本。"""
        if not self.active:
            return
        self.frame += 1
        self._sync_timeline()
        self.update(self._build_frame())

    # ---- 渲染 ----

    def _fg_lines(self) -> list[tuple[str, str | None]]:
        """前景文本行（与旧版逐行 append 的版式逐字节等价，含空行）。"""
        frame = self.frame
        stage = self._stage()
        if stage == "dark":
            return []
        lines: list[tuple[str, str | None]] = []
        # 题名区：分隔线生长 + 题名逐字浮现。
        sep_progress = min(1.0, max(0.0, (frame - DARK_FRAMES) / max(1, SEP_FRAMES)))
        half = int(18 * sep_progress)
        if half:
            lines.append(("─" * half + " ✦ " + "─" * half, "grey58"))
            lines.append(("", None))
        title_progress = min(1.0, max(0.0, (frame - DARK_FRAMES) / max(1, TITLE_FRAMES)))
        title_text = tr(self._ending.get("title", ""))
        shown = int(len(title_text) * title_progress + 1e-9)
        # 中文档名逐字空格撑出题名的重量；英译保持原样（字母空格化不可读）。
        if title_text.isascii():
            title = title_text[:shown] or " "
        else:
            title = "  ".join(title_text[:shown]) or " "
        lines.append((title, "bold bright_yellow"))
        if title_progress >= 1.0 and self._ending.get("subtitle"):
            lines.append(("—— " + tr(self._ending["subtitle"]) + " ——", "grey70"))
        lines.append(("", None))
        if stage == "title":
            return lines
        # 叙事：逐行打字机（每行 2 字/帧）。
        for index, line in enumerate(self._narrative):
            line_start = self._narrative_start() + LINE_FRAMES * index
            if frame < line_start:
                break
            chars = min(len(line), (frame - line_start) * 2)
            lines.append((line[:chars], "bright_white"))
            lines.append(("", None))
        if stage == "narrative":
            return lines
        # 数值：逐行滑入 + 数字滚动。
        for index, (label, value) in enumerate(self._rolls):
            row_start = self._stats_start() + STAT_FRAMES * index
            if frame < row_start:
                break
            progress = min(1.0, (frame - row_start) / max(1, ROLL_FRAMES))
            current = int(value * progress)
            lines.append((f"{label}　{current}",
                          "grey70" if progress < 1.0 else "bright_cyan"))
        if stage == "stats":
            return lines
        # 尾声：记忆清单 + 呼吸提示。
        lines.append(("", None))
        lines.append((self._memory_note, "italic grey58"))
        for line in self._review_lines[:6]:
            lines.append((line, "grey70"))
        if len(self._review_lines) > 6:
            lines.append((tr("完整工具与冷却记录见主页的旧梦回忆。"), "grey70"))
        lines.append(("", None))
        if (frame // 30) % 2 == 0:
            lines.append((self._prompt, "bold bright_cyan"))
        return lines

    def _build_frame(self) -> Text:
        """当前帧：背景分镜（可选）+ 前景文本。"""
        lines = self._fg_lines()
        timeline = self._timeline
        if timeline is None or not timeline.has_shots:
            text = Text()
            for index, (line, style) in enumerate(lines):
                if index:
                    text.append("\n")
                if line:
                    text.append(line, style=style)
            return text
        backdrop = timeline.advance(self.frame / 30)
        return compose_over(backdrop, lines, timeline.width)


def _memory_name(memory_id: str) -> str:
    """记忆碎片 id → 名称（定义表直查；未知 id 原样返回）。"""
    definition = ITEM_DEFINITIONS.get(memory_id)
    return definition["name"] if definition else memory_id
