"""Opt-in cached-strip rendering for the hybrid world view.

- ``canvas``：WorldCanvas 复用未变化的 Strip 帧，只替换逐行样式合成。
- ``painter``：在 canvas 之上由 WorldPainter 直接写终端（行差量 + 光标归位），
  仅接管 character 后端的世界控件；装饰帧/浮层仍回退 Textual compositor。
- 快路径 ``WorldCanvas.render_world_lines``：对无边框/内边距/透明背景的满幅
  控件直接拼装 Strip，跳过 StylesCache 的逐行样式流水线；其它布局返回
  ``None`` 交给原路径。

库与测试默认仍是 ``textual``（既有 ``run_test`` 契约）；发布入口按 2026-10-27 的
WezTerm 实测改为 ``painter``，见 docs/2026-10-27-hybrid-world-renderer-development.md
第 17 节。图像后端、观察模式、浮层与装饰帧控件自动回退 Textual。
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MethodType
import time

from rich.cells import get_character_cell_size
from rich.control import Control
from rich.segment import Segment
from rich.style import Style
from textual.filter import ANSIToTruecolor, DimFilter, Monochrome, NoColor
from textual.geometry import Region, Spacing
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static

from ..env_compat import get as env_get
from ..i18n import tr
from .styles import RIGHT_PANEL_MODES

_VALID_MODES = frozenset({"textual", "canvas", "painter"})
_mode_override: str | None = None

# --- A1（2026-10-27）：世界邻接控件的直写覆盖 -------------------------------
# 实测（docs/2026-10-27-perf-baseline-refresh.md 第 3.2 节）：high 画质下 move
# 只有一半动作真正直写，另一半因为同一拍变脏的 #hover-info 让 world_only=False
# 而整帧回退 Textual compositor。这里把「与地图同步刷新、几何稳定」的少数邻接
# 控件也纳入直写集合；其余控件（面板帮助、装饰帧、浮层等）仍照旧回退。
# 注意：#hover-info 在 #side-pane 的普通流里，**不覆盖世界视图**；它只是与地图
# 同一拍变脏。真正「被别的控件盖住」的情形见 overlap_enabled()（默认关闭）。
# ONEIRSCRIPT_PAINTER_COVERAGE=0 可整体回退到「只接管 WorldCanvas」。
_EXTRA_PAINTABLE_IDS = frozenset({"hover-info"})


def coverage_enabled() -> bool:
    """A1 覆盖扩展（**默认关闭**，opt-in）。

    实测结论（2026-10-27 收尾）：
    - **动作首帧口径收益为 0**：move 的首个负载来自 paint_early，它只画 WorldCanvas。
    - **收尾帧只在「内容变、几何不变」时才有收益**：只要 #hover-info 的高度变了，
      Textual 会进入 layout + 整屏 repaint（screen._layout_required / _repaint_required），
      painter 必须让路。独立验证在特定窗口测到过 23 帧 vs 0 帧的差异，但本机
      收尾采样稳定命中 layout 帧，**未能稳定复现**。
    - 像素级等价：scripts/verify_a1_pixel_equiv_261027.py 已把 painter 写出行与
      Compositor.render_strips() 逐格比较（272/352/544 行，0 不匹配），但采样到的
      都是**单控件（地图）**直写帧，尚未覆盖「地图 + 侧栏邻接控件」的多控件路径。

    因此默认保持关闭：收益不稳定、且多控件路径的像素安全还没有证据。
    打开方式：ONEIRSCRIPT_PAINTER_COVERAGE=1（可选叠加 ONEIRSCRIPT_PAINTER_OVERLAP=1）。
    """
    return str(env_get("PAINTER_COVERAGE", "0") or "0").strip().lower() in (
        "1", "true", "yes", "on")


def overlap_enabled() -> bool:
    """A1 进阶（**默认关闭**）：允许「被本拍同样变脏的控件盖住」的直写。

    按 z 序后→前写、并对被覆盖行强制整行重写。当前生产布局里 #hover-info 并不
    覆盖世界视图，这条路径只在合成测试里被触发；由于它还缺少很多渲染细节
    （opacity/tint/行过滤器/滚动裁剪），默认不启用，等真机目视验收后再开。
    """
    return str(env_get("PAINTER_OVERLAP", "0") or "0").strip().lower() in (
        "1", "true", "yes", "on")


def is_opaque(widget) -> bool:
    """直写是整行覆盖：盖在上面的控件必须完全不透明才与 compositor 等价。

    除了背景 alpha，还要排除 opacity / text-opacity / tint：这些都会让 compositor
    把下层混进来，而逐行直写做不到。
    """
    if getattr(widget, "_world_plain_layout", False):
        return True
    try:
        styles = widget.styles
        background = styles.background
        if getattr(styles, "opacity", 1.0) < 1.0:
            return False
        if getattr(styles, "text_opacity", 1.0) < 1.0:
            return False
        tint = getattr(styles, "tint", None)
        if tint is not None and getattr(tint, "a", 0) != 0:
            return False
    except Exception:
        return False
    return background is not None and getattr(background, "a", 1.0) >= 1.0


def subtract_region(region: Region, other: Region) -> list[Region]:
    """region - other 的矩形分解（最多 4 块），用于「并集是否覆盖脏区」判定。"""
    if not region.overlaps(other):
        return [region]
    if other.contains_region(region):
        return []
    pieces: list[Region] = []
    top = max(region.y, other.y)
    if region.y < top:
        pieces.append(Region(region.x, region.y, region.width, top - region.y))
    bottom = min(region.y + region.height, other.y + other.height)
    if bottom < region.y + region.height:
        pieces.append(Region(region.x, bottom, region.width,
                             region.y + region.height - bottom))
    middle_top = top
    middle_height = bottom - top
    if middle_height > 0:
        left = max(region.x, other.x)
        if region.x < left:
            pieces.append(Region(region.x, middle_top, left - region.x, middle_height))
        right = min(region.x + region.width, other.x + other.width)
        if right < region.x + region.width:
            pieces.append(Region(right, middle_top,
                                 region.x + region.width - right, middle_height))
    return pieces


def regions_covered(dirty_regions, widgets) -> bool:
    """compositor 的每个脏区是否被这些控件的**并集**覆盖。

    旧判定要求脏区被**单个**控件完全包含；多控件同拍变脏时 compositor 会把脏区
    并成更大的矩形，于是永远不满足（实测 A1 就是卡在这里）。
    """
    remaining = [region for region in dirty_regions if region.area]
    for widget in widgets:
        if not remaining:
            return True
        region = widget.region
        if not region:
            continue
        next_remaining: list[Region] = []
        for piece in remaining:
            next_remaining.extend(subtract_region(piece, region))
        remaining = next_remaining
    return not remaining


def is_world_paintable(widget) -> bool:
    """WorldCanvas，或登记过的世界邻接控件（见 _EXTRA_PAINTABLE_IDS）。"""
    if isinstance(widget, WorldCanvas):
        return True
    if not coverage_enabled():
        return False
    return (widget.id or "") in _EXTRA_PAINTABLE_IDS


# --- 第二步（2026-10-28）：图像模式受控直绘周围 UI -------------------------
# 图像+原生层下地图由独立窗口画；周围 UI（状态栏/事件面板/边框/悬停信息）仍
# 走 Textual 合成。这里把「地形稳定、未被遮挡、类型受控」的脏控件直接写终端，
# 从而跳过整屏合成；地图本身不写（原生层负责），只把它的脏区视为已消费。
# 任何不认识/被遮挡/浮层可见/布局重排的帧一律回退 compositor。
# ONEIRSCRIPT_IMAGE_DIRECT_UI=0 整体回退（排障/录屏/A-B）。
_IMAGE_EXTRA_IDS = frozenset({"hover-info", "header-ticker"})
_IMAGE_EXTRA_TYPES = frozenset({"RunClock", "HeaderTicker", "ClickableHoverInfo"})


def image_direct_ui_enabled() -> bool:
    return str(env_get("IMAGE_DIRECT_UI", "1") or "1").strip().lower() not in (
        "0", "off", "false", "no")


def set_image_direct_ui(enabled: bool) -> None:
    """测试/探针用：同进程切换图像模式受控直绘。"""
    global _IMAGE_DIRECT_UI_OVERRIDE
    _IMAGE_DIRECT_UI_OVERRIDE = None if enabled is None else bool(enabled)


_IMAGE_DIRECT_UI_OVERRIDE: bool | None = None


def _image_direct_ui_on() -> bool:
    if _IMAGE_DIRECT_UI_OVERRIDE is not None:
        return _IMAGE_DIRECT_UI_OVERRIDE
    return image_direct_ui_enabled()


def is_border_pane(widget) -> bool:
    """带自定义边框绘制的 Pane（OrnamentPane 一族；不是 WorldCanvas）。"""
    return (not isinstance(widget, WorldCanvas)
            and callable(getattr(widget, "paint_ornament", None)))


def is_image_paintable(widget) -> bool:
    """图像模式直绘允许的控件类型（窄白名单，宁缺勿滥）。"""
    if isinstance(widget, WorldCanvas):
        return True
    if is_border_pane(widget):
        return True
    widget_id = getattr(widget, "id", None)
    if widget_id in _IMAGE_EXTRA_IDS:
        return True
    return type(widget).__name__ in _IMAGE_EXTRA_TYPES


# --- A3（2026-10-27）：直接 cell→ANSI 编码 ---------------------------------
# Textual 的 Strip.render 对每个 Segment 都发一次 SGR 并在段尾复位。世界帧相邻
# 段同色的情况极多，这里改成「样式变了才发前缀、整行只在行尾复位一次」。
# ONEIRSCRIPT_PAINTER_ANSI=0 可回退到 Rich 原路径。
_ANSI_PREFIX_CACHE: dict[tuple[Style, object], str] = {}
_ANSI_CACHE_LIMIT = 4096


def ansi_encoding_enabled() -> bool:
    return str(env_get("PAINTER_ANSI", "1") or "1").strip().lower() not in (
        "0", "false", "no", "off")


def strip_to_ansi(strip: Strip, console) -> str | None:
    """把 Strip 编码成 ANSI；返回 None 表示调用方应回退 Rich 原路径。

    与 Textual 的 Strip.render 保持可见等价：跳过 style=None 的段（Rich 同样的
    过滤），带链接的样式直接回退（Rich 会额外发 OSC 8）。
    """
    color_system = getattr(console, "_color_system", None)
    if color_system is None:
        return None
    parts: list[str] = []
    current: Style | None = None
    first = True
    append = parts.append
    cache = _ANSI_PREFIX_CACHE
    cache_get = cache.get
    for text, style, _link in strip._segments:
        if style is None:
            continue
        if style._link:
            return None
        if style is not current:
            cache_key = (style, color_system)
            attrs = cache_get(cache_key)
            if attrs is None:
                # Rich stores one ANSI string on each Style, regardless of the
                # console's color system. Generate on a copy so a standard-color
                # console cannot poison a later truecolor console (or vice versa).
                if style._null:
                    attrs = ""
                else:
                    fresh_style = style.copy()
                    fresh_style._ansi = None
                    attrs = fresh_style._make_ansi_codes(color_system)
                if len(cache) >= _ANSI_CACHE_LIMIT:
                    cache.clear()
                cache[cache_key] = attrs
            # Rich 在每个段尾发一次复位；这里改成进入新样式前复位一次即可
            # （相邻同样式段因此可以合并），避免 Bold/Dim 等属性泄漏到下一段。
            # 缓存只存 attrs：首段不需要复位，后续段需要，不能把两种形态一起缓存。
            if attrs:
                append(f"\x1b[{attrs}m" if first else f"\x1b[0m\x1b[{attrs}m")
            elif not first:
                append("\x1b[0m")
            first = False
            current = style
        append(text)
    return "".join(parts)


def world_render_mode() -> str:
    if _mode_override is not None:
        return _mode_override
    value = str(env_get("WORLD_RENDER", "textual") or "textual").strip().lower()
    return value if value in _VALID_MODES else "textual"


def set_world_render_mode(mode: str | None) -> None:
    global _mode_override
    if mode is not None and mode not in _VALID_MODES:
        raise ValueError(f"unknown world render mode: {mode}")
    _mode_override = mode


@dataclass(frozen=True)
class WorldFrame:
    key: tuple
    source: object
    lines: tuple[Strip, ...]

    def line(self, y: int, width: int, style: Style) -> Strip:
        if 0 <= y < len(self.lines):
            return self.lines[y]
        return Strip.blank(width, style)


class WorldCanvas(Static):
    """A Static whose unchanged content bypasses repeated Rich line layout."""

    def _world_styles_changed(self) -> bool:
        signature = tuple(
            (id(node.styles), id(node.styles.base), id(node.styles.inline),
             node.styles._cache_key)
            for node in self.ancestors_with_self
        )
        if signature == getattr(self, "_world_style_signature", None):
            return False
        self._world_style_signature = signature
        self._world_rich_style = super().rich_style
        self._world_visual_style = super().visual_style
        styles = self.styles
        border = styles.border
        outline = styles.outline
        hatch_plain = True
        if styles.has_rule("hatch"):
            hatch_plain = styles.hatch == "none"
        # 只接受无装饰的满幅内容：这样 StylesCache 的逐行合成可以等价手写。
        self._world_plain_layout = (
            not any(edge[0] for edge in border)
            and not any(edge[0] for edge in outline)
            and styles.padding == Spacing()
            and hatch_plain
            and self.opacity == 1.0
            and styles.text_opacity == 1.0
            and styles.tint.a == 0
        )
        return True

    @property
    def rich_style(self) -> Style:
        self._world_styles_changed()
        return self._world_rich_style

    @property
    def visual_style(self):
        self._world_styles_changed()
        return self._world_visual_style

    def _world_frame_key(self, rich_style: Style, visual_style) -> tuple:
        return (
            id(self._content),
            self.size,
            rich_style,
            visual_style,
            self.styles.content_align,
        )

    def _world_frame_for(self, rich_style: Style, visual_style) -> WorldFrame:
        key = self._world_frame_key(rich_style, visual_style)
        frame = getattr(self, "_world_frame", None)
        if frame is None or frame.key != key or frame.source is not self._content:
            self._render_content()
            frame = WorldFrame(key, self._content, tuple(self._render_cache.lines))
            self._world_frame = frame
        else:
            self._dirty_regions.clear()
        return frame

    def render_line(self, y: int) -> Strip:
        if world_render_mode() not in ("canvas", "painter"):
            return super().render_line(y)
        # 每行只解析一次祖先样式：rich_style/visual_style 在 Textual 0.89 是
        # 逐次重算的 property，未缓存时一行扫描 3 次会抵消掉缓存收益。
        rich_style = self.rich_style
        visual_style = self.visual_style
        frame = self._world_frame_for(rich_style, visual_style)
        return frame.line(y, self.size.width, rich_style)

    def render_world_lines(self, crop: Region) -> tuple[Strip, ...] | None:
        """Compose full-widget strips without Textual's per-row style pipeline.

        Mirrors :meth:`StylesCache.render` for the undecorated full-bleed case
        (no border/padding/opacity/filter-visible tint). Returns ``None`` for
        any layout this mirror does not reproduce, so the caller can fall back
        to :meth:`render_lines`.
        """
        if world_render_mode() not in ("canvas", "painter"):
            return None
        # 子类若覆盖了 render_lines（装饰边框等），快路径无法复现其额外处理。
        if type(self).render_lines is not Widget.render_lines:
            return None
        rich_style = self.rich_style
        visual_style = self.visual_style
        if not getattr(self, "_world_plain_layout", False):
            return None
        if crop != Region(0, 0, *self.size) or self.content_region.size != self.size:
            return None
        # Scrolled content is cropped by the compositor before reaching
        # render_lines; the mirror only covers the unscrolled full viewport.
        if self.scroll_offset:
            return None
        if self.auto_links:
            hover_style = self.hover_style
            if (hover_style._link_id and hover_style._meta
                    and "@click" in hover_style.meta):
                return None
        frame = self._world_frame_for(rich_style, visual_style)
        width = self.size.width
        base_background, background = self._opacity_background_colors
        bgcolor = (base_background + background).rich_color
        inner = Style.from_color(bgcolor=bgcolor)
        filters = tuple(line_filter for line_filter in self.app._filters if line_filter.enabled)
        # Textual's built-in filters have stable identity, apart from the dim
        # factor; custom filters may depend on arbitrary mutable external state.
        cacheable = all(type(item) in (ANSIToTruecolor, DimFilter, Monochrome, NoColor)
                        for item in filters)
        filter_key = tuple((item, getattr(item, "dim_factor", None)) for item in filters)
        cached = getattr(self, "_world_composed_cache", None)
        if (cacheable and cached is not None and cached[0] is frame
                and cached[1:4] == (bgcolor, background, filter_key)):
            return cached[4]
        strips: list[Strip] = []
        for y in crop.line_range:
            # render_line also applies the widget's inherited foreground to
            # blank content rows. Preserve it before adding the background.
            line = frame.line(y, width, rich_style)
            if line.cell_length != width:
                line = line.adjust_cell_length(width)
            # 背景为透明时 inner 是空样式：跳过整行 Segment 重建。
            if bgcolor is not None:
                line = Segment.apply_style(line, inner)
            strip = Strip(line, width)
            for line_filter in filters:
                strip = strip.apply_filter(line_filter, background)
            strips.append(strip)
        result = tuple(strips)
        if cacheable:
            self._world_composed_cache = (frame, bgcolor, background, filter_key, result)
        return result


def _cell_signature(strip: Strip):
    """逐终端格 (char, style) 序列；含宽字符的行返回 None（交给整行写）。"""
    cells: list[tuple[str, object]] = []
    for text, style, _link in strip._segments:
        for char in text:
            size = get_character_cell_size(char)
            if size == 0 and cells:
                previous, previous_style = cells[-1]
                cells[-1] = (previous + char, previous_style)
            elif size == 1:
                cells.append((char, style))
            else:
                return None
    return cells


def _changed_span(previous: Strip, current: Strip, width: int):
    """返回该行相对上一帧变化的最小终端格区间 (start, end)；整行返回 (0, width)。"""
    before = _cell_signature(previous)
    after = _cell_signature(current)
    if before is None or after is None or len(before) != len(after):
        return 0, width
    limit = min(width, len(before), len(after))
    first = 0
    while first < limit and before[first] == after[first]:
        first += 1
    if first >= limit:
        return None
    last = limit - 1
    while last >= first and before[last] == after[last]:
        last -= 1
    if first == 0 and last + 1 >= width:
        return 0, width
    return first, last + 1


class WorldPainter:
    """Write unchanged-geometry world widgets without a Textual compositor pass."""

    _OVERLAYS = (
        "#map-overlay", "#tamper-overlay", "#settlement", "#debug-panel",
        "#toast", "#map-mode-hint", "#left-event-log", "#tutorial-card",
        "#self-pane", "#layer-info-pane", "#signal-detail", "#qol-confirm-dialog",
        "#controls-help", "#board-editor", "#pause-menu", "#codex-page",
        "#settings-page",
    )

    def __init__(self, app) -> None:
        self.app = app
        self._legacy_refresh = None
        self._screen = None
        self._previous: dict[WorldCanvas, tuple[Region, tuple[Strip, ...]]] = {}
        # A1：邻接控件的「上一次看到的几何」。即使在回退帧也要记录，否则第一次
        # 见到它必然不稳、永远拿不到稳定的第二拍，直写会一直被打回。
        self._seen_regions: dict = {}
        self.last_order_reason = ""
        self.active = False
        self.failed = False
        self.frames = 0
        self.rows = 0
        self.early_paints = 0
        self.last_early_ms = 0.0
        self.last_early_at = 0.0
        self.fallbacks = 0
        self.last_fallback: dict = {}
        self.last_paint_ms = 0.0
        self.last_render_ms = 0.0
        self.last_encode_ms = 0.0
        self.last_write_ms = 0.0
        self.last_bytes = 0
        self.last_rows = 0
        self.last_eligible_ms = 0.0
        self.last_hook_ms = 0.0
        # 第二步：图像模式受控直绘的状态
        self.image_mode = False
        self.image_frames = 0
        self.image_border_rows = 0
        self.last_image_reason = ""
        self._border_previous: dict[tuple, Strip] = {}
        self.last_painted_widgets: list = []
        self.last_border_writes: list = []

    def install(self, screen) -> None:
        if self._screen is not None:
            return
        self._screen = screen
        self._legacy_refresh = screen._compositor_refresh
        screen._compositor_refresh = MethodType(self._compositor_refresh, screen)

    def close(self) -> None:
        if self._screen is not None and self._legacy_refresh is not None:
            self._screen._compositor_refresh = self._legacy_refresh
        self._screen = None
        self._legacy_refresh = None
        self.suspend()

    def suspend(self) -> None:
        self.active = False
        self._previous.clear()
        # 直写缓存描述的是「我们写出去的像素」；一旦交回 compositor，屏幕内容
        # 可能被 Textual 改写，缓存不再可信，下次必须重写。
        self._border_previous.clear()

    def _widgets_unobscured(self, screen, widgets) -> bool:
        """Direct output is safe only when Textual would show each whole widget.

        ``widget.region`` is not a clipping region: it can extend beyond its
        parent or underneath a higher layer. In either case writing whole rows
        would erase pixels that belong to another widget or to the terminal.
        """
        compositor = screen._compositor
        visible = compositor.visible_widgets
        screen_region = compositor.size.region
        for widget in widgets:
            geometry = visible.get(widget)
            if geometry is None or not widget.visible:
                return False
            region, clip = geometry
            if (region != widget.region or not clip.contains_region(region)
                    or not screen_region.contains_region(region)):
                return False
            # visible_widgets is ordered front to back, just like the
            # compositor's row layers. Anything before this widget may cover it.
            for other, (other_region, other_clip) in visible.items():
                if other is widget:
                    break
                covered = other_region.intersection(other_clip)
                if other.visible and covered and region.overlaps(covered):
                    return False
        return True

    def _geometry_stable(self, widgets) -> bool:
        """邻接控件（非 WorldCanvas）必须与上一拍几何一致或只是变大才可直写。

        自动高度控件（#hover-info）**收缩**时，Textual 会擦掉腾出来的行；直接写
        最新内容不会，所以收缩/移动必须交回 compositor。「变大」不留下无人认领的
        行（旧区域被新区域完全包含），可以直接接管。
        """
        stable = True
        for widget in widgets:
            if isinstance(widget, WorldCanvas):
                continue
            region = widget.region
            seen = self._seen_regions.get(widget)
            self._seen_regions[widget] = region
            if seen is None or not region.contains_region(seen):
                stable = False
        return stable

    def _paint_order(self, screen, widgets):
        """返回「后→前」的直写顺序；任何前提不满足返回 None。

        直写是整行覆盖，与 compositor 的逐格合成等价的前提是：每个会盖住
        dirty 控件的控件本身也在本拍 dirty 集合里、完全不透明，并且在它之后
        写出来（后→前）。生产布局里真实出现的是「父容器 #panel 与它的子控件
        #hover-info 同拍变脏」这一类；任何未被本拍重画的遮挡控件都会导致拒绝，
        避免擦掉别的控件。本路径默认关闭（见 overlap_enabled）。
        """
        dirty = set(widgets)
        compositor = screen._compositor
        visible = compositor.visible_widgets
        screen_region = compositor.size.region
        indexed = {widget: index for index, widget in enumerate(visible)}
        for widget in widgets:
            geometry = visible.get(widget)
            if geometry is None or not widget.visible:
                self.last_order_reason = f"geometry:{widget.id}"
                return None
            region, clip = geometry
            if region != widget.region:
                self.last_order_reason = f"region-mismatch:{widget.id}"
                return None
            if not clip.contains_region(region):
                self.last_order_reason = f"clip:{widget.id}"
                return None
            if not screen_region.contains_region(region):
                self.last_order_reason = f"offscreen:{widget.id}"
                return None
            for other, (other_region, other_clip) in visible.items():
                if other is widget:
                    break
                covered = other_region.intersection(other_clip)
                if not (other.visible and covered and region.overlaps(covered)):
                    continue
                if other not in dirty:
                    self.last_order_reason = f"covered-by-clean:{widget.id}<-{other.id}"
                    return None
                if not is_opaque(other):
                    self.last_order_reason = f"not-opaque:{other.id}"
                    return None
        self.last_order_reason = "ok"
        order = sorted(widgets, key=lambda item: indexed.get(item, 0), reverse=True)
        # 先写的控件可能被后写的控件覆盖：后写者与先写者重叠的那些行必须整行重写，
        # 否则「被盖住的行里只有一部分变化」时，先写者擦掉的像素没人补回来。
        forced: dict = {}
        for position, widget in enumerate(order):
            region = widget.region
            rows: set[int] | None = None
            for earlier in order[:position]:
                other = earlier.region
                if not region.overlaps(other):
                    continue
                if rows is None:
                    rows = set()
                top = max(region.y, other.y)
                bottom = min(region.y + region.height, other.y + other.height)
                rows.update(range(top - region.y, bottom - region.y))
            if rows:
                forced[widget] = rows
        return order, forced

    def _eligible(self, screen) -> bool:
        app = self.app
        reasons = []
        painter_mode = world_render_mode() == "painter"
        image_mode = False
        if self.failed:
            reasons.append("failed")
        if not painter_mode:
            if not _image_direct_ui_on():
                reasons.append("mode")
            else:
                image_mode = True
        if app.is_headless:
            reasons.append("headless")
        if app.is_inline or app.screen is not screen:
            reasons.append("screen")
        if not app._running or app._closed or app._driver is None:
            reasons.append("not-running")
        if app.home_mode:
            reasons.append("home")
        elif painter_mode:
            if app.panel_mode != "world":
                reasons.append(f"panel:{app.panel_mode}")
        else:
            # 第二步：右栏工作区（含 ~ 锁定页）下世界仍可行动，周围 UI 也走
            # 同一条受控直绘；全屏模态/观察/层观测仍整帧回退 compositor。
            if app.panel_mode != "world" and app.panel_mode not in RIGHT_PANEL_MODES:
                reasons.append(f"panel:{app.panel_mode}")
        if getattr(app, "layer_observation", None) is not None:
            reasons.append("layer-observation")
        # 观察模式每帧只移动光标：实测 painter 的整帧写比 Textual 的单元格
        # 差量更贵，交回 Textual；移动/结算帧仍由 painter 接管。
        if getattr(app, "observe_mode", False):
            reasons.append("observe-mode")
        if getattr(app, "_native_prompt_suppressed", False):
            reasons.append("native-prompt")
        try:
            display_mode = app.query_one("#map", WorldCanvas).display_mode
            if painter_mode:
                if display_mode != "character":
                    reasons.append(f"display:{display_mode}")
            elif display_mode != "image":
                reasons.append(f"display:{display_mode}")
            for selector in self._OVERLAYS:
                widget = app.query_one(selector)
                if widget.display and not widget.has_class("hidden"):
                    reasons.append(selector)
        except Exception:
            reasons.append("query")
        self.image_mode = bool(image_mode and not reasons)
        self.last_ineligible = reasons
        return not reasons

    def _compositor_refresh(self, screen) -> None:
        hook_started = time.perf_counter()
        dirty = screen._dirty_widgets
        eligible_started = time.perf_counter()
        eligible = self._eligible(screen)
        self.last_eligible_ms = (time.perf_counter() - eligible_started) * 1000.0
        if self.image_mode:
            if eligible and self._image_paint(screen, list(dirty)):
                self.last_hook_ms = (time.perf_counter() - hook_started) * 1000.0
                return
            self.fallbacks += 1
            self.last_fallback = {
                "image": True,
                "eligible": eligible,
                "ineligible": list(getattr(self, "last_ineligible", ())),
                "reason": self.last_image_reason,
                "dirty": [(type(widget).__name__, widget.id,
                           is_image_paintable(widget)) for widget in dirty],
            }
            self.suspend()
            self._legacy_refresh()
            self.last_hook_ms = (time.perf_counter() - hook_started) * 1000.0
            return
        world_only = bool(dirty) and all(is_world_paintable(widget) for widget in dirty)
        # 默认（A1 关闭）沿用既有口径：脏区必须被**单个** dirty 控件包含。
        # 打开 A1 后才改用「并集覆盖」——并集口径更宽松，需要原生目视验收。
        if coverage_enabled():
            owned_regions = regions_covered(screen._compositor._dirty_regions, dirty)
        else:
            owned_regions = all(
                any(widget.region.contains_region(region) for widget in dirty)
                for region in screen._compositor._dirty_regions)
        geometry_stable = self._geometry_stable(dirty)
        forced: dict = {}
        if overlap_enabled():
            painted = self._paint_order(screen, dirty)
            if painted is None:
                order = None
            else:
                order, forced = painted
        elif self._widgets_unobscured(screen, dirty):
            order = list(dirty)
        else:
            order = None
        # 挂载中的布局尚未跑完时 widget.region 可能是旧几何，必须回退。
        # 行过滤器（dim/monochrome/ANSI 降级）不在这里拒绝：走 render_lines 的控件
        # 由 _apply_line_filters 按 compositor 同样的口径补上（见 paint_widgets）。
        if order is not None and screen._layout_required:
            order = None
        unobscured = (eligible and world_only and owned_regions and geometry_stable
                      and order is not None
                      and not screen._repaint_required)
        if unobscured:
            try:
                self.paint_widgets(order, ordered=True, forced_rows=forced)
            except Exception:
                self.failed = True
                self.suspend()
                self.last_fallback = {
                    "eligible": eligible,
                    "world_only": world_only,
                    "geometry_stable": geometry_stable,
                    "owned_regions": owned_regions,
                    "unobscured": unobscured,
                    "screen_repaint": screen._repaint_required,
                    "ineligible": list(getattr(self, "last_ineligible", ())) + ["failed"],
                    "widgets": [type(widget).__name__ for widget in dirty
                                if not isinstance(widget, WorldCanvas)],
                    "dirty": [(type(widget).__name__, widget.id,
                               is_world_paintable(widget)) for widget in dirty],
                    "order_reason": self.last_order_reason,
                }
                self.app.call_after_refresh(
                    self.app.show_toast, tr("世界直写失败，已回退 Textual 渲染。"))
            else:
                self.active = True
                screen._dirty_widgets.clear()
                screen._compositor._dirty_regions.clear()
                self.app._update_mouse_over(screen)
                self.last_hook_ms = (time.perf_counter() - hook_started) * 1000.0
                return
        self.fallbacks += 1
        self.last_fallback = {
            "eligible": eligible,
            "world_only": world_only,
            "owned_regions": owned_regions,
            "geometry_stable": geometry_stable,
            "unobscured": unobscured,
            "screen_repaint": screen._repaint_required,
            "ineligible": list(getattr(self, "last_ineligible", ())),
            "widgets": [type(widget).__name__ for widget in dirty
                        if not isinstance(widget, WorldCanvas)],
            "dirty": [(type(widget).__name__, widget.id,
                       is_world_paintable(widget)) for widget in dirty],
            "order_reason": self.last_order_reason,
        }
        self.suspend()
        self._legacy_refresh()
        self.last_hook_ms = (time.perf_counter() - hook_started) * 1000.0

    # ---- 第二步：图像模式受控直绘 -----------------------------------------
    @staticmethod
    def _is_border_region(pane, region: Region) -> bool:
        """脏区是否只落在 pane 的边框行/列上（绝不碰内部内容）。"""
        pane_region = pane.region
        if not pane_region.contains_region(region):
            return False
        x = region.x - pane_region.x
        y = region.y - pane_region.y
        return (y == 0 or y == pane_region.height - 1
                or x == 0 or x == pane_region.width - 1)

    def _paint_border_regions(self, screen, targets) -> int:
        """只重写 OrnamentPane 的边框脏区（不整块重写，内部子控件不受影响）。

        targets 是 [(pane, Region)]，Region 来自 compositor 的脏区，通常是
        一行或一列。逐行渲染 pane.render_lines 的对应裁切，按 strip 去重后写
        终端；返回实际写出的行数。
        """
        app = self.app
        ansi_fast = ansi_encoding_enabled()
        output: list[str] = []
        rows = 0
        self.last_border_writes = []
        for pane, region in targets:
            relative = Region(region.x - pane.region.x, region.y - pane.region.y,
                              region.width, 1)
            for offset in range(region.height):
                crop = Region(relative.x, relative.y + offset, relative.width, 1)
                try:
                    strips = list(pane.render_lines(crop))
                except Exception:
                    self.last_image_reason = "border-render"
                    return -1
                if not strips:
                    continue
                strips = list(self._apply_line_filters(pane, tuple(strips)))
                strip = strips[0]
                key = (id(pane), region.x, region.y + offset, region.width)
                if self._border_previous.get(key) == strip:
                    continue
                encoded = strip_to_ansi(strip, app.console) if ansi_fast else None
                output.append(Control.move_to(region.x, region.y + offset).segment.text)
                output.append(strip.render(app.console) if encoded is None else encoded)
                output.append("\x1b[0m")
                self._border_previous[key] = strip
                self.last_border_writes.append(key)
                rows += 1
        if output:
            app._begin_update()
            try:
                app._driver.write("".join(output))
            finally:
                app._end_update()
            app._driver.flush()
        return rows

    def _image_paint(self, screen, dirty) -> bool:
        """图像模式的直绘判定与执行；False 表示本帧交回 compositor。

        只接管窄白名单：WorldCanvas 子类（状态栏/事件面板）、OrnamentPane 的
        边框行、以及固定的 hover-info/header 小组件。地图本身不写（原生层
        负责），但它的脏区算作已消费；只变地图的帧仍会触发一次本地图发布。
        任何未知控件、浮层、布局重排、几何不稳定、互相遮挡未知的帧都回退。
        """
        app = self.app
        compositor = screen._compositor
        self.last_image_reason = ""
        if not dirty:
            self.last_image_reason = "no-dirty"
            return False
        if screen._layout_required or screen._repaint_required:
            self.last_image_reason = "layout-or-repaint"
            return False
        if not all(is_image_paintable(widget) for widget in dirty):
            unknown = [f"{type(w).__name__}:{w.id}" for w in dirty
                       if not is_image_paintable(w)]
            self.last_image_reason = "type:" + ",".join(unknown[:3])
            return False
        panes = [widget for widget in dirty if is_border_pane(widget)]
        if panes:
            # 2026-10-28：边框直绘在第一轮像素等价核验里发现「同一拍里
            # pane.render_lines 返回的边框色与 compositor 最终色不一致」
            # （主题/focus 样式更新与装饰帧同拍时）。边框已由第一步把频率
            # 降到 2Hz，这里先整帧回退 compositor，宁可少赚也不输出错色。
            self.last_image_reason = "pane-dirty"
            return False
        maps = [widget for widget in dirty
                if isinstance(widget, WorldCanvas) and (widget.id or "") == "map"]
        others = [widget for widget in dirty if widget not in maps]
        # 每个 compositor 脏区都必须归属某个 dirty 控件；否则可能擦掉未重画的区域。
        for region in compositor._dirty_regions:
            if not any(widget.region.contains_region(region) for widget in dirty):
                self.last_image_reason = "owned-region"
                return False
        if others and not self._geometry_stable(others):
            self.last_image_reason = "geometry"
            return False
        if others and not self._widgets_unobscured(screen, others):
            self.last_image_reason = "obscured"
            return False
        border_targets = []
        for region in compositor._dirty_regions:
            # 脏区可能被 Textual 合并成跨控件的大矩形：先判归属，取「能覆盖它
            # 的 dirty 控件」中最小的一类——地图/普通控件整块重画就能覆盖该区，
            # 只有真正落在 pane 边框行/列上的部分才走边框直绘。
            if any(widget.region.contains_region(region) for widget in maps):
                continue
            if any(widget.region.contains_region(region) for widget in others):
                continue
            pane = next((item for item in panes
                         if item.region.contains_region(region)), None)
            if pane is None:
                self.last_image_reason = "owned-region"
                return False
            if not self._is_border_region(pane, region):
                # 边框 pane 内部还有别的脏内容却没出现在 dirty 集合里：回退。
                self.last_image_reason = "not-border"
                return False
            if any(widget.region.overlaps(region) for widget in others):
                self.last_image_reason = "border-overlap"
                return False
            border_targets.append((pane, region))
        # 所有前提通过：先画普通控件（内容区），再画边框行，互不重叠。
        try:
            if others:
                self.paint_widgets(others, ordered=True)
            if border_targets:
                written = self._paint_border_regions(screen, border_targets)
                if written < 0:
                    return False
                self.image_border_rows += written
            if not others and not border_targets:
                # 只变地图：让原生层照常发布一次，避免画面停在上一步。
                app._begin_update()
                try:
                    app._end_update()
                finally:
                    pass
        except Exception:
            self.failed = True
            self.last_image_reason = "failed"
            return False
        self.image_frames += 1
        self.active = True
        dirty.clear()
        compositor._dirty_regions.clear()
        app._update_mouse_over(screen)
        return True

    def paint_early(self, widgets=()) -> bool:
        """动作内提前写世界区域：地图就绪即输出，不等 Textual 合成时机。

        在 refresh_view_contents 的 _fx_repaint 之后调用：此时地图基帧与 FX 叠加层
        都已就绪，而右侧面板/状态栏内容还在后面更新。先把地图行写出去，玩家看到
        的世界帧提前约 15–20ms；随后 _compositor_refresh 仍会补画其余 WorldCanvas
        （未变的行不会重复写）。
        """
        if world_render_mode() != "painter" or self.failed:
            return False
        screen = self._screen
        if screen is None:
            screen = getattr(self.app, "screen", None)
            if screen is None:
                return False
            self.install(screen)
        if not self._eligible(screen):
            return False
        targets = [widget for widget in (widgets or screen._dirty_widgets)
                   if isinstance(widget, WorldCanvas) and widget.display and widget.region]
        if (not targets or screen._layout_required or screen._repaint_required
                or not self._widgets_unobscured(screen, targets)):
            return False
        started = time.perf_counter()
        frames_before = self.frames
        try:
            self.paint_widgets(targets)
        except Exception:
            self.failed = True
            self.suspend()
            return False
        if self.frames == frames_before:
            return False
        self.early_paints += 1
        self.last_early_ms = (time.perf_counter() - started) * 1000.0
        self.last_early_at = time.perf_counter()
        self.active = True
        return True

    def _apply_line_filters(self, widget, strips):
        """按 compositor 的口径给 render_lines 的结果补上行过滤器。

        这里**绝不能抛**：paint_widgets 的异常会把 painter 永久停用，宁可少一层
        滤镜也不能让整条直写路径挂掉。
        """
        try:
            active = tuple(item for item in (getattr(self.app, "_filters", ()) or ())
                           if getattr(item, "enabled", False))
            if not active:
                return strips
            _base, background = widget._opacity_background_colors
            filtered = []
            for strip in strips:
                for item in active:
                    strip = strip.apply_filter(item, background)
                filtered.append(strip)
            return tuple(filtered)
        except Exception:
            return strips

    def paint_widgets(self, widgets, ordered: bool = False,
                      forced_rows: dict | None = None) -> None:
        app = self.app
        ansi_fast = ansi_encoding_enabled()
        self.last_painted_widgets = []
        paint_started = time.perf_counter()
        changes: list[tuple[WorldCanvas, Region, tuple[Strip, ...], tuple[int, ...]]] = []
        output: list[str] = []
        render_ms = 0.0
        encode_ms = 0.0
        targets = list(widgets) if ordered else sorted(
            widgets, key=lambda item: (item.region.y, item.region.x))
        for widget in targets:
            region = widget.region
            if not region or not widget.display:
                continue
            started = time.perf_counter()
            render_world_lines = getattr(widget, "render_world_lines", None)
            strips = (render_world_lines(Region(0, 0, region.width, region.height))
                      if render_world_lines is not None else None)
            if strips is None:
                style = widget.rich_style
                strips = tuple(
                    strip.extend_cell_length(region.width, style).simplify()
                    for strip in widget.render_lines(Region(0, 0, region.width, region.height))
                )
                # 走 render_lines 的**普通控件**不会经过 WorldCanvas 的过滤链，这里
                # 按 compositor 的口径补上（dim/monochrome/ANSI 降级），否则直写会漏
                # 滤镜。WorldCanvas 维持原行为不变。
                if not isinstance(widget, WorldCanvas):
                    strips = self._apply_line_filters(widget, strips)
            else:
                # Keep render_world_lines identical to Textual's styled output;
                # only the terminal encoder needs adjacent segments coalesced.
                cached = getattr(widget, "_world_simplified_cache", None)
                if cached is not None and cached[0] is strips:
                    strips = cached[1]
                else:
                    simplified = tuple(strip.simplify() for strip in strips)
                    widget._world_simplified_cache = (strips, simplified)
                    strips = simplified
            render_ms += (time.perf_counter() - started) * 1000.0
            previous = self._previous.get(widget)
            if previous is not None and previous[0] == region:
                changed_rows = tuple(y for y, strip in enumerate(strips)
                                     if y >= len(previous[1]) or strip != previous[1][y])
            else:
                changed_rows = tuple(range(len(strips)))
            forced = (forced_rows or {}).get(widget) or ()
            if forced:
                # 被后写控件覆盖的行：即使内容没变也要整行重写（先写者可能擦掉了）
                changed_rows = tuple(sorted(set(changed_rows) | set(forced)))
            if not changed_rows:
                continue
            changes.append((widget, region, strips, changed_rows))
            started = time.perf_counter()
            for y in changed_rows:
                start, end = 0, region.width
                if (y not in forced and previous is not None
                        and previous[0] == region and y < len(previous[1])):
                    span = _changed_span(previous[1][y], strips[y], region.width)
                    if span is None:
                        continue
                    start, end = span
                strip = strips[y] if start == 0 and end == region.width else strips[y].crop(start, end)
                encoded = strip_to_ansi(strip, app.console) if ansi_fast else None
                output.append(Control.move_to(region.x + start, region.y + y).segment.text)
                output.append(strip.render(app.console) if encoded is None else encoded)
                output.append("\x1b[0m")
            encode_ms += (time.perf_counter() - started) * 1000.0
        self.last_painted_widgets = [widget for widget, _region, _strips, _rows
                                     in changes]
        if not changes:
            self.last_paint_ms = (time.perf_counter() - paint_started) * 1000.0
            return
        output.append(Control.move_to(*app.cursor_position).segment.text)
        payload = "".join(output)
        write_started = time.perf_counter()
        app._begin_update()
        try:
            app._driver.write(payload)
        finally:
            app._end_update()
        app._driver.flush()
        write_ms = (time.perf_counter() - write_started) * 1000.0
        row_count = 0
        for widget, region, strips, changed_rows in changes:
            self._previous[widget] = (region, strips)
            row_count += len(changed_rows)
        self.rows += row_count
        self.frames += 1
        self.last_paint_ms = (time.perf_counter() - paint_started) * 1000.0
        self.last_render_ms = render_ms
        self.last_encode_ms = encode_ms
        self.last_write_ms = write_ms
        self.last_bytes = len(payload.encode("utf-8", "replace"))
        self.last_rows = row_count
        app._previous_cursor_position = app.cursor_position
        app.post_display_hook()
