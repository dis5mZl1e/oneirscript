"""左侧透明事件记录叠加层（2026-10-26）。

默认关闭（设置项 `left_event_log`）：开启后在**地图显示框**左下角叠一层
只有文字的事件记录——无背景、无边框、无标题、鼠标穿透；宽度约占显示框
的 1/4、高度约 1/3，按显示宽度自动折行，只保留最近能放下的若干条
（从最新消息往前累计物理行）。玩家自己站进显示框左下 1/4 象限时整块
改贴左上，避免遮住玩家格子。

坐标口径与 `DreamApp._player_in_map_top_right` 一致：`#map` 的 region +
viewport 可见格数 × 格尺寸；偏移相对 `#layout` 的 content_region 写入，
与 floating_toast.MapHints.place 的换算相同。
"""

from __future__ import annotations

from rich.console import Console
from rich.cells import get_character_cell_size
from rich.text import Text
from textual.geometry import Region
from textual.widgets import Static

from .styles import PANEL_MUTED
from .widgets import MapView

# 这些 panel_mode 下 #layout（含地图）被整块隐藏，叠加层也必须收起；
# 与 app._refresh_world_view 里 map_visible 的判定同一口径。
MAP_HIDDEN_PANEL_MODES = frozenset({"pause", "pause_settings", "pause_codex", "board_editor"})


def _wrap_lines(renderable: Text, width: int) -> list[Text]:
    """把一条消息按显示宽度折成物理行（保留颜色/高亮等 span）。

    rich Console 的 render_lines 按终端格宽折行（中日韩全角算两格），
    再把 Segment 还原成 Text，颜色与右栏事件记录完全一致。
    """
    width = max(1, int(width))
    console = Console(width=width, force_terminal=False, color_system=None,
                      legacy_windows=False)
    lines: list[Text] = []
    for segments in console.render_lines(renderable, console.options.update(width=width),
                                         pad=False):
        line = Text()
        for segment in segments:
            line.append(segment.text, segment.style)
        if line.plain:
            lines.append(line)
    return lines


def build_left_event_log_text(messages, width: int, height: int) -> Text:
    """从最新消息往前累计物理行到不超过 height，再按时间正序拼成一段 Text。

    只含条目正文与换行：没有标题、没有 ●／· 点号、没有空行。最新一条
    消息自己就超过高度时只保留它最后 height 行（叠加层贴底，结尾更可读）。
    """
    width = max(1, int(width))
    height = max(1, int(height))
    blocks: list[list[Text]] = []
    used = 0
    for message in reversed(messages):
        body = message if isinstance(message, Text) else Text(str(message))
        if not body.plain.strip():
            continue  # 空白条目不占行，也不留空行
        lines = _wrap_lines(body, width)
        if not lines:
            continue
        if used + len(lines) > height:
            if not used:
                blocks.append(lines[-height:])
            break
        blocks.append(lines)
        used += len(lines)
    if not blocks:
        return Text()
    blocks.reverse()
    return Text("\n").join(line for block in blocks for line in block)


def raster_event_log(log, image, map_region, columns: int, rows: int):
    """Rasterize only the log's ink on a transparent layer over an image map."""
    from PIL import Image
    from .map_presentation import draw_glyph

    content = log.renderable
    if not log.display or not isinstance(content, Text) or not content.plain:
        return None
    sx, sy = image.width / max(1, columns), image.height / max(1, rows)
    layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    console = Console()
    column = row = 0
    for index, char in enumerate(content.plain):
        if char == '\n':
            column, row = 0, row + 1
            continue
        width = get_character_cell_size(char)
        if width <= 0:
            continue
        if not char.isspace():
            x = round((log.region.x - map_region.x + column) * sx)
            y = round((log.region.y - map_region.y + row) * sy)
            w = max(1, round((column + width) * sx) - round(column * sx))
            h = max(1, round((row + 1) * sy) - round(row * sy))
            style = content.get_style_at_offset(console, index)
            color = ('#{:02x}{:02x}{:02x}'.format(*style.color.get_truecolor())
                     if style.color else '#d0d0d0')
            draw_glyph(layer, char, color, (x, y, w, h), scale=.88)
        column += width
    return layer


class LeftEventLog(Static):
    """透明事件记录：只画文字，绝不画背景/边框，点击与悬停全部穿透到地图。"""

    # Textual 的 transparent 只表示背景色透明，默认合成器仍会把空格画在地图上。
    # _WideCompositor 以文字占用的终端格为遮罩，其余格继续显示下层。
    transparent_text_overlay = True

    DEFAULT_CSS = """
    LeftEventLog {
        position: absolute;
        layer: toast;
        background: transparent;
        padding: 0;
        border: none;
        height: auto;
        overflow: hidden hidden;
        display: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # place 的去抖指纹：内容/尺寸/贴角任一未变就不写 styles。
        self._left_event_log_key = None

    def get_widget_at(self, x: int, y: int):
        """鼠标穿透：命中测试跳过本控件，点击/悬停落到下层 #map。

        Textual 0.89 没有 pointer-events:none，Compositor.get_widget_at 会把
        顶层可见控件当作命中目标；覆写此方法对本控件抛 NoMatches，compositor
        会继续往下找 #map（与 FloatingToast.get_widget_at 同一手法）。
        """
        from textual.css.query import NoMatches

        raise NoMatches("LeftEventLog is click-through")

    # ---- 鼠标穿透：把指针事件转发给下面真正的地图控件 ----
    # Textual 0.89 的 Compositor.get_widget_at 不查询控件的 get_widget_at，
    # 光覆写它不足以让点击穿过（FloatingToast 亦另做转发）。这里与
    # FloatingToast._forward_mouse 同一手法：事件坐标换成屏幕坐标，取合成器
    # 里本层之下的第一个控件（正常就是 #map），把同一个事件重投给它。
    def _forward_mouse(self, event, kind: str) -> None:
        from textual import events
        from textual.geometry import Region

        event.stop()
        event.prevent_default()
        x = self.region.x + event.offset.x
        y = self.region.y + event.offset.y
        if not self.screen.region.contains(x, y):
            return
        target = next(((widget, region) for widget, region in
                       self.screen._compositor.get_widgets_at(x, y)
                       if not isinstance(widget, LeftEventLog)), None)
        if target is None:
            return
        widget, region = target
        local_x, local_y = x - region.x, y - region.y
        strips = widget.render_lines(Region(0, local_y, region.width, 1))
        sample = next(iter(strips[0].crop(local_x, local_x + 1)), None) if strips else None
        event_type = {'down': events.MouseDown, 'move': events.MouseMove,
                      'scroll_up': events.MouseScrollUp,
                      'scroll_down': events.MouseScrollDown}[kind]
        forwarded = event_type(
            widget, local_x, local_y,
            getattr(event, 'delta_x', 0), getattr(event, 'delta_y', 0),
            getattr(event, 'button', 0), getattr(event, 'shift', False),
            getattr(event, 'meta', False), getattr(event, 'ctrl', False), x, y,
            sample.style if sample else None)
        if kind == 'down':
            self.app._keys_handled_in_on_key.clear()
        widget.post_message(forwarded)

    def on_mouse_down(self, event) -> None:
        self._forward_mouse(event, "down")

    def on_mouse_move(self, event) -> None:
        self._forward_mouse(event, "move")

    def on_mouse_scroll_up(self, event) -> None:
        self._forward_mouse(event, "scroll_up")

    def on_mouse_scroll_down(self, event) -> None:
        self._forward_mouse(event, "scroll_down")


class LeftEventLogMixin:
    """DreamApp 侧接线：刷新叠加层内容与位置。"""

    def _player_in_map_bottom_left(self) -> bool:
        """玩家是否落在地图显示框左下 1/4（左半且下半）。

        与 app._player_in_map_top_right 同口径：玩家格中心相对 #map 的
        region 换算，中线按**视口可见格数 × 格尺寸**算（MapView 可能比地图
        内容大，按 widget 尺寸会把边角误判进另一端）。取不到地图/状态
        （主页、切层间隙）返回 False。
        """
        try:
            map_view = self.query_one("#map", MapView)
            state = self.session.state
        except Exception:
            return False
        left, top, width, height = map_view.viewport
        cell_w = max(1, int(getattr(map_view, "cell_w", 2)))
        cell_h = max(1, int(getattr(map_view, "cell_h", 1)))
        px = map_view.region.x + (state.player.x - left) * cell_w + cell_w // 2
        py = map_view.region.y + (state.player.y - top) * cell_h + (cell_h - 1) // 2
        return (px < map_view.region.x + (width * cell_w) // 2
                and py >= map_view.region.y + (height * cell_h) // 2)

    def _left_event_log_enabled(self) -> bool:
        try:
            return bool(self.config.get("left_event_log"))
        except (KeyError, AttributeError, TypeError):
            return False

    def _hide_left_event_log(self, widget: LeftEventLog) -> None:
        widget._left_event_log_key = None
        if widget.styles.display != "none":
            widget.styles.display = "none"

    def _refresh_left_event_log(self, state) -> None:
        """刷新左侧透明事件记录（开、关、位置与内容都在这里收口）。

        只在非主页、非终局、地图可见且设置开启时显示；暂停/设置/图鉴/
        联想盘编辑器这些把 #layout 整块隐藏的界面一律收起。
        """
        try:
            widget = self.query_one("#left-event-log", LeftEventLog)
        except Exception:
            return
        panel_mode = getattr(self, "panel_mode", "")
        map_visible = not (bool(getattr(self, "home_mode", False))
                           or panel_mode in MAP_HIDDEN_PANEL_MODES)
        if (not self._left_event_log_enabled() or not map_visible
                or bool(getattr(state, "run_over", False))):
            self._hide_left_event_log(widget)
            return
        try:
            map_view = self.query_one("#map", MapView)
            messages = tuple(self._visible_game_messages(state))
        except Exception:
            self._hide_left_event_log(widget)
            return
        # 「显示框」取**可见地图区域**（region 原点 + 视口可见格数 × 格尺寸），
        # 不是 MapView 控件外框：控件可能被布局拉得比地图内容高/宽，按外框算
        # 会把叠加层放到地图下方的空白区。也不是 state.width/height 的实际地图
        # 尺寸——那是整张梦层地图，不是屏幕上看得见的那一块。
        _left, _top, visible_cols, visible_rows = map_view.viewport
        cell_w = max(1, int(getattr(map_view, "cell_w", 2)))
        cell_h = max(1, int(getattr(map_view, "cell_h", 1)))
        frame = Region(map_view.region.x, map_view.region.y,
                       min(map_view.region.width, visible_cols * cell_w),
                       min(map_view.region.height, visible_rows * cell_h))
        if frame.width <= 0 or frame.height <= 0:
            self._hide_left_event_log(widget)
            return
        # 区域：显示框左下 1/4 宽、1/3 高，且不超过显示框本身。
        width = min(frame.width, max(10, frame.width // 4))
        height = min(frame.height, max(4, frame.height // 3))
        # 玩家在显示框左下 1/4 时整块改贴左上，别盖住玩家格子。
        top_left = self._player_in_map_bottom_left()
        # 窗口/布局变化可能让显示框原点变化但宽高不变（例如右侧面板档位换挡），
        # 因此原点也进缓存键，否则叠加层会留在旧位置。
        key = (frame.x, frame.y, width, height, top_left, messages)
        if key == widget._left_event_log_key and widget.styles.display == "block":
            return
        parent = widget.parent
        if parent is None:
            return
        body_fn = getattr(self, "_message_body_text", None)
        bodies = [
            body_fn(message) if body_fn is not None else Text(message, style=PANEL_MUTED)
            for message in messages if str(message).strip()
        ]
        content = build_left_event_log_text(bodies, width, height)
        if not content.plain:
            self._hide_left_event_log(widget)
            return
        origin = parent.content_region
        x = frame.x - origin.x
        y = frame.y - origin.y if top_left else frame.bottom - origin.y - height
        widget.update(content)
        # 文字变化可能使可见字形的格子发生变化，即使控件位置和尺寸不变，
        # 合成器缓存的分段也必须重新计算。
        self.screen._compositor._cuts = None
        widget.styles.width = width
        widget.styles.height = height
        widget.styles.offset = (x, y)
        widget.styles.display = "block"
        widget._left_event_log_key = key
