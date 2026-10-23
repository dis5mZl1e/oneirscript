"""地图右上角气泡栈：操作模式与短时反馈。

MapHints 放在地图面板外的同级图层，以免贴齐边框的文字被内边距裁掉。
子提示使用同一流式图层避免叠字；点击与悬停转发给其下的地图。
临时反馈持续三秒，按键或点击提前收起；模式提示持续到模式结束。
2026-10-11 起角落随玩家位置：玩家站在地图右上 1/4 时整栈换到右下角。
"""

from __future__ import annotations

from rich.cells import cell_len
from textual.geometry import Offset
from rich.text import Text
from textual.widgets import Static
from textual.containers import Vertical

from .styles import highlighted_message

DISPLAY_SECONDS = 3.0


def bubble_width(text: Text) -> int:
    """气泡总宽 = 最长一行的格数 + round 边框 2 + 左右 padding 各 1。

    多行消息必须取**最长行**，不能拿整串长度：cell_len 把换行算 0 格，
    把各行相加会把三行短提示撑到 42 列（玩家反馈「气泡背景遮挡范围远超
    文字」的成因之一，2026-10-18）。宽度按最长行算，气泡才是紧贴文字的框。
    """
    lines = text.plain.split("\n")
    widest = max((cell_len(line) for line in lines), default=0)
    return widest + 4


def _toast_anchor_bottom(app) -> bool:
    """玩家站在地图子窗口右上 1/4 时，气泡让位到右下角（2026-10-11）。

    判定权威在 app._player_in_map_top_right（玩家格中心相对 #map-pane 的
    象限）；app 未就绪/取不到地图时回落 False——气泡保持右上。
    """
    try:
        return bool(app._player_in_map_top_right())
    except Exception:
        return False


class MapHintText(Static):
    def on_mouse_down(self, event):
        if self.id == 'map-mode-hint' and getattr(self.app,'aiming',False):
            # Aim bubble entries (source / reload / exit) are explicit mouse
            # targets; the rest of the bubble still swallows the click so it can
            # never fall through to a shot.
            if event.button == 1:
                self.app._aim_hud_click(event.offset)
            event.stop()
            event.prevent_default()
            return
        if getattr(self.app,'layer_observation',None) is not None:
            if event.button == 1:
                self.app._exit_layer_observation()
            event.stop()
            return
        if self.app.observe_mode and event.button == 1 and event.offset.y >= 2:
            self.app.action_cycle_map_observe()
            event.stop()
            return
        FloatingToast._forward_mouse(self, event, "down")

    def on_mouse_move(self, event):
        FloatingToast._forward_mouse(self, event, "move")


class MapHints(Vertical):
    DEFAULT_CSS = """
    MapHints {
        position: absolute;
        layer: toast;
        height: auto;
        align-horizontal: right;
        /* 容器只是布局载体，而且**不画背景**：
           2026-10-11 玩家反馈气泡背景整块铺满容器宽、遮挡地图，背景改由子件
           自己画（宽度 = 文本 + padding）；2026-10-18 第二轮再收紧——容器本身
           也只在 place() 里按**实际可见子件的最宽者**设宽（不再固定 42 列），
           所以它连"透明但 42 列宽的占位块"都不再存在，尽量不压地图。 */
        background: transparent;
        overflow: hidden hidden;
    }
    MapHints MapHintText {
        height: auto;
        width: auto;
        background: #292930;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # place() 的去抖指纹（2026-10-11）：place 现在也挂在 MapView.update_state
        # 的完整路径上（玩家移动后跟随切角），FX 有噪点时可达每 100ms 一次——
        # 指纹未变就一步 styles 都不写，守住「少写回」纪律。
        self._placed_key = None
        # 贴底布局的「布局后再复算」标记（2026-10-18）：height:auto 的容器要等
        # 布局把高度算出来，第一拍 place() 用的是旧高度，气泡会探出地图下沿。
        self._reflow_pending = False

    def _content_width(self) -> int:
        """容器应有的宽度 = 当前**可见**子件里最宽的那一个。

        - MapHintText 是 width:auto：按「最长一行 + 左右 padding 各 1」自己量；
        - FloatingToast 由它的 _place() 写死宽度，直接取。
        隐藏的子件不参与——临时消息收起后容器要立刻跟着收窄（否则会留下一条
        不可见的宽占位块，玩家规则：气泡范围尽量别压地图）。
        """
        widest = 1
        for child in self.children:
            if child.styles.display == "none":
                continue
            if not child.styles.is_auto_width:
                widest = max(widest, int(child.styles.width.value))
                continue
            content = getattr(child, "renderable", None)
            plain = getattr(content, "plain", None)
            if plain is None:
                continue
            widest = max(widest, max((cell_len(line) for line in plain.split("\n")), default=0) + 2)
        return widest

    def place(self, _reflow: bool = False):
        if self.parent is None:
            return
        try:
            pane = self.screen.query_one("#map-pane")
        except Exception:
            return  # Modal settings/teardown can temporarily hide the game screen.
        origin = self.parent.content_region
        # 2026-10-18 第二轮：容器宽度只包住真正可见的气泡，不再固定 42 列。
        width = min(max(1, self._content_width()), max(1, pane.region.width))
        max_height = max(3, pane.region.height // 3)
        # 玩家在地图右上 1/4 → 气泡换到右下角，别挡住玩家自己的格子。
        bottom = _toast_anchor_bottom(self.app)
        # Keep transient messages at the actual corner even when the permanent
        # layer entry is wider or occupies an extra line in the same host.
        toast = next((child for child in self.children if child.id == 'toast'),None)
        if toast is not None and toast.display and len(self.children) > 1:
            if bottom and self.children[-1] is not toast:
                self.move_child(toast,after=self.children[-1])
            elif not bottom and self.children[0] is not toast:
                self.move_child(toast,before=self.children[0])
        x = pane.region.right - origin.x - width
        y_top = pane.region.y - origin.y
        y_bottom = pane.region.bottom - origin.y - max(1, int(self.region.height))
        child_widths = []
        for child in self.children:
            if child.styles.display == 'none':
                continue
            if child.styles.is_auto_width:
                plain = getattr(getattr(child,'renderable',None),'plain','')
                child_width = max((cell_len(line) for line in plain.split('\n')),default=0)+2
            else:
                child_width = int(child.styles.width.value)
            child_widths.append((child,min(width,child_width)))
        key = (width, max_height, bottom, x, y_top, y_bottom,
               tuple((id(child),cw) for child,cw in child_widths))
        if key == self._placed_key:
            return
        self._placed_key = key
        self.styles.width = width
        self.styles.max_height = max_height
        self.styles.offset = (x, y_bottom if bottom else y_top)
        for child,child_width in child_widths:
            child.styles.offset = (max(0,width-child_width),0)
        # 贴底：容器高度是 auto，本拍 y_bottom 用的是上一帧高度（气泡刚出现时
        # 往往是 0/1），会在下一拍布局后探出地图下沿。布局完成后再复算一次。
        if bottom and not _reflow and not self._reflow_pending:
            self._reflow_pending = True
            try:
                self.call_after_refresh(self._reflow_after_layout)
            except Exception:  # pragma: no cover - 未挂载/退出中
                self._reflow_pending = False

    def _reflow_after_layout(self) -> None:
        """布局完成后重算一次贴底偏移（见 place() 的贴底说明）。

        只补这一拍：_reflow=True 时 place() 不再预约下一次，否则「写偏移→布局→
        再预约」会每帧自激。
        """
        self._reflow_pending = False
        try:
            self.place(_reflow=True)
        except Exception:  # pragma: no cover - 退出/卸载中
            pass

    def on_resize(self, event):
        # 容器高度（height:auto）在文本变化后由布局更新，on_resize 再进
        # place()——贴底模式靠这一拍把底边重新对齐。
        self._placed_key = None
        self.place()

    def on_mouse_down(self, event):
        FloatingToast._forward_mouse(self, event, "down")

    def on_mouse_move(self, event):
        FloatingToast._forward_mouse(self, event, "move")


class FloatingToast(Static):
    """地图右侧临时弹窗。单实例复用：同一时刻只显示一条最新消息。"""

    DEFAULT_CSS = """
    FloatingToast {
        layer: toast;
        position: relative;
        height: auto;
        # 与左右面板同一个色，且**随区域换**（口径见 region_themes.RegionTheme
        # .panel_bg；进游戏后由 app._apply_region_theme 改写）。
        # 这里的 #292930 只是主页 / 未应用主题时的兜底（= DEFAULT_PANEL_BG）。
        # 旧值 #191924 90% 贴在地图黑底上几乎隐形——气泡的目的就是「不用翻记录
        # 也能看见」，底色必须比地图亮一档；alpha 一律不写，合成器会把透明度
        # 与地图预混，透上来的地图色会让气泡深浅随画面变。
        background: #292930;
        border: round #59627a;
        padding: 0 1;
        display: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._full_text = Text()
        self._anchor_screen_y = 0  # 触发位置的屏幕行（文本行与之对齐）
        self._age = 0.0

    # ---- 显示 / 隐藏 ----

    def show(self, message: str, anchor_screen_y: int) -> None:
        """显示一条消息：anchor_screen_y = 触发位置所在的屏幕行。

        宽度首帧即按完整文本设定（2026-09-20 修复：旧伸出动画先给半宽，
        文本先折成多行再突然弹回单行）。
        2026-09-21：消息里的**物品名**按各自的定义色高亮
        （styles.highlighted_message，与事件记录同一口径）。"""
        self._full_text = highlighted_message(message)
        self._anchor_screen_y = max(0, int(anchor_screen_y))
        self._age = 0.0
        self.update(self._full_text)
        self.styles.display = "block"
        self._place()

    def dismiss(self) -> None:
        """提前取消（点击地图/面板、按任意键）。"""
        if self.styles.display != "none":
            self.hide()

    def hide(self) -> None:
        self.styles.display = "none"
        self._age = 0.0
        # 收起后容器要立刻按「剩下的可见气泡」重新收窄（2026-10-18 第二轮）：
        # 容器宽度不再固定 42，而是跟着可见子件走；不通知这一拍会留一条宽占位。
        if isinstance(self.parent, MapHints):
            try:
                self.parent.place()
            except Exception:
                pass

    # ---- 布局：地图右上/右下角（随玩家位置，2026-10-11），旧触发行参数只保留兼容 ----

    def _place(self) -> None:
        try:
            pane = self.app.query_one("#map-pane")
        except Exception:
            return
        if isinstance(self.parent, MapHints):
            # 先按消息定宽、再让容器按「最宽可见气泡」重排——顺序反过来会读到
            # 上一帧的容器宽度（旧实现因此把宽度钳在 42 列）。
            cap = min(42, max(8, int(pane.region.width)))
            self.styles.width = min(cap, max(8, bubble_width(self._full_text)))
            self.styles.offset = (0, 0)
            self.parent.place()
            return
        content_w = max(1, int(pane.content_size.width))
        # 总宽 = 文本 + 左右 padding 各 1 + round 边框各 1。
        # 首帧即完整宽度：宽度中途变化会让文本先折行再弹回（观感跳变）。
        total_w = min(content_w, max(8, bubble_width(self._full_text)))
        self.styles.width = total_w
        # 独立挂载时也贴外边框（角落随玩家位置，与 MapHints 同口径）；
        # 正常运行时由 MapHints 统一布局。
        x = pane.region.right - pane.content_region.x - total_w
        if _toast_anchor_bottom(self.app):
            y = pane.region.bottom - pane.content_region.y - max(1, int(self.region.height))
        else:
            y = pane.region.y - pane.content_region.y
        self.styles.offset = (x, y)

    # ---- 鼠标穿透：气泡不拦点击/悬停，转发给 #map ----
    def on_mouse_down(self, event) -> None:
        self._forward_mouse(event, "down")

    def on_mouse_move(self, event) -> None:
        self._forward_mouse(event, "move")

    def _forward_mouse(self, event, kind: str) -> None:
        from types import SimpleNamespace
        from .widgets import MapView

        try:
            map_view = self.app.query_one("#map", MapView)
        except Exception:
            return
        # offset 换算：地图相对 = 气泡相对 + (地图原点 - 气泡原点)。
        dx = self.region.x - map_view.region.x
        dy = self.region.y - map_view.region.y
        shim = SimpleNamespace(
            offset=type(event.offset)(event.offset.x + dx, event.offset.y + dy),
            button=getattr(event, "button", 1),
            ctrl=getattr(event, "ctrl", False),
            control=map_view,
            stop=lambda: None,
        )
        if kind == "down":
            self.app.handle_map_mouse_down(map_view, shim)
        elif kind == "move":
            self.app.handle_map_mouse_move(map_view, shim)
        event.stop()

    def get_widget_at(self, x: int, y: int):
        """鼠标穿透：命中测试跳过本控件，点击/悬停落到下层 #map。

        Textual 0.89 无 pointer-events:none，Compositor.get_widget_at 会把
        顶层可见控件当作命中目标。覆写此方法让它对本控件返回 NoMatches，
        compositor 会继续往下找 #map。"""
        from textual.css.query import NoMatches

        raise NoMatches("FloatingToast is click-through")

    def tick(self) -> bool:
        """帧推进：3 秒倒计时。返回 True 表示仍显示。"""
        if self.styles.display == "none":
            return False
        self._age += 1 / 30
        if self._age >= DISPLAY_SECONDS:
            self.hide()
            return False
        return True
