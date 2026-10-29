"""地图右上角气泡栈：操作模式与短时反馈。

MapHints 放在地图面板外的同级图层，以免贴齐边框的文字被内边距裁掉。
子提示使用同一流式图层避免叠字；点击与悬停转发给其下的地图。
临时反馈持续三秒，按键或点击提前收起；模式提示持续到模式结束。
2026-10-11 起角落随玩家位置：玩家站在地图右上 1/4 时整栈换到右下角。
"""

from __future__ import annotations

from functools import lru_cache

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text
from textual.widgets import Footer, Static
from textual.containers import Vertical

from .styles import highlighted_message

DISPLAY_SECONDS = 3.0

# 文本折行测量用的独立 Console（2026-10-26）：只用来算"这段文本在这么宽的
# 内容区里占几行"，不画任何东西。用它而不是 app.console，是为了让 place()
# 在挂载/卸载的任意时机都能算高度，不依赖 Textual 的 active_app 上下文。
_MEASURE_CONSOLE = Console()


@lru_cache(maxsize=256)
def _wrapped_line_count(plain: str, width: int) -> int:
    """文本在给定内容宽下的显示行数。

    与 Textual 的 RichVisual.get_height 同口径（都是 rich 的 Text.wrap），
    这样"估算的容器高度"和"布局真正算出来的高度"是同一个答案，贴底气泡
    不会因为差了半行而探进底栏。缓存按 (文本, 宽) 去重：place() 挂在
    30fps 的地图帧路径上，重复测量不重复折行。
    """
    if width <= 0 or not plain:
        return 0
    return len(Text(plain).wrap(_MEASURE_CONSOLE, width, tab_size=8))


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


def _footer_top(screen) -> int | None:
    """底栏（Textual Footer）的顶行；取不到返回 None。

    气泡的硬下界：除了地图面板内容区的下缘，再加一道底栏守卫——任何尺寸/
    布局口径变化都不允许把气泡写进 Footer 行（玩家反馈的「与下方 textual 栏
    互相遮挡」）。取不到 Footer（主页/悬浮屏/拆卸中）时只受内容区约束。

    2026-10-27 性能：原实现每次 `screen.query("Footer")`——CSS 选择器串要解析
    再对整棵树逐个匹配，330 节点的游戏屏实测 p50 **1.06ms**，而 place() 每个
    行动要调 2~3 次，占了 place() 总耗时的 95%（1.69/1.79ms），是行动期最大
    的一笔固定开销。改为「先扫屏幕直属子件（0.01ms），没有再做带类型的深度
    遍历（0.09ms）」，命中集合与 `query("Footer")` 完全一致（都是 isinstance，
    含 I18nFooter 这类子类）。
    """
    try:
        footers = [widget for widget in screen.children if isinstance(widget, Footer)]
        if not footers:  # 非直属挂载（自定义屏/测试宿主）时才走整树遍历
            footers = list(screen.walk_children(Footer))
    except Exception:
        return None
    tops = [int(widget.region.y) for widget in footers
            if widget.display and widget.region.height]
    if not tops:
        return None
    return min(tops)


class MapHintText(Static):
    def on_mouse_scroll_up(self, event):
        FloatingToast._forward_mouse(self, event, 'scroll_up')

    def on_mouse_scroll_down(self, event):
        FloatingToast._forward_mouse(self, event, 'scroll_down')

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
        # place() 的**前置指纹**（2026-10-27 A4）：在进入昂贵的宽度/高度测量
        # （_content_width 的逐子件 cell_len、_child_height 的 rich Text.wrap）
        # 之前，先用廉价输入（子件 id/display/宽度口径/文本、面板几何、贴底
        # 判定、底栏顶行）判断拍子是否真的变了；未变直接返回。_placed_key 的
        # 语义不变（仍然是「最后一次真正写回 styles 时的布局键」）。
        self._place_prekey = None
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

    # ---- 高度估算（2026-10-26）----

    def _child_height(self, child, container_width: int) -> int:
        """本拍某个可见子件会占的**外框**高度（含边框与 padding）。

        不能读 child.region.height：place() 往往在文本刚更新、布局还没跑之前
        就被调用，那里拿到的是上一拍的高度——临时消息/瞄准提示变长时，气泡
        会瞬时或持续探进下方底栏（玩家反馈的「错位、互相遮挡」）。
        这里按子件自己的 CSS 口径 + 文本折行数现算：
        - width:auto（MapHintText）：内容宽 = 最长行，行数 = 显式行数；
        - 显式宽度（FloatingToast）：内容宽 = 宽度 - padding - 边框，按字折行。
        折行与 Textual 布局用同一套 rich Text.wrap，估算 = 布局结果。
        """
        styles = child.styles
        gutter = styles.gutter
        plain = getattr(getattr(child, "renderable", None), "plain", None)
        if plain is None:  # 非文本 renderable（未来扩展）：按一行兜底
            return 1 + gutter.height
        if styles.is_auto_width:
            natural = max((cell_len(line) for line in plain.split("\n")), default=0)
            inner = max(1, natural)
        else:
            inner = max(1, int(styles.width.value) - gutter.width)
        return _wrapped_line_count(plain, inner) + gutter.height

    def _cheap_place_key(self, origin, content, bottom, footer_top):
        """place() 的前置指纹：只取廉价输入，不折行、不量宽。

        指纹包含最终布局键的**全部输入**：面板/容器内容区几何、左右下角判定、
        底栏顶行，以及每个子件的 id/display、宽度口径（auto 还是固定列数）、
        renderable 的文本（或对象身份）与 gutter。这些不变时，_content_width、
        每个 _child_height 与最终 key 必然都不变，因此可以整段跳过测量。
        文本对象被 in-place 改写也会被抓住（比较的是 plain 字符串本身）。
        """
        children = []
        for child in self.children:
            styles = child.styles
            renderable = getattr(child, "renderable", None)
            plain = getattr(renderable, "plain", None)
            text_sig = plain if plain is not None else id(renderable)
            gutter = styles.gutter
            width = styles.width
            if styles.is_auto_width:
                width_sig = ("auto", text_sig)
            elif width is None:
                # 未显式设宽的隐藏子件（如首次 show 之前的 toast）：真正测量
                # 路径会跳过 display:none 的子件，这里只登记「未设宽」这一状态，
                # 不读 .value（否则 None.value 抛 AttributeError）。
                width_sig = ("unset", text_sig)
            else:
                width_sig = ("fixed", int(width.value), text_sig)
            children.append((id(child), styles.display, width_sig,
                             gutter.width, gutter.height))
        return (origin.x, origin.y, content.x, content.y, content.width,
                content.height, bottom, footer_top, tuple(children))

    def place(self, _reflow: bool = False):
        if self.parent is None:
            return
        try:
            pane = self.screen.query_one("#map-pane")
        except Exception:
            return  # Modal settings/teardown can temporarily hide the game screen.
        origin = self.parent.content_region
        # 基准一律取地图面板的**内容区**（去掉 round 边框与 padding）：
        # 旧实现贴的是外框 region，右缘落在最右边框列上、底缘落在底边框行上，
        # 与地图边框/底栏互相遮挡（2026-10-26 玩家反馈）。用 content_region
        # 后气泡天然不会出现在边框与 padding 上。
        content = pane.content_region
        # 玩家在地图右上 1/4 → 气泡换到右下角，别挡住玩家自己的格子。
        bottom = _toast_anchor_bottom(self.app)
        # Keep transient messages at the actual corner even when the permanent
        # layer entry is wider or occupies an extra line in the same host.
        # 先做这一次（廉价的）次序修正，再取前置指纹：子件顺序本身就是指纹的
        # 一部分，顺序被修正过就一定要走完整测量。
        toast = next((child for child in self.children if child.id == 'toast'),None)
        if toast is not None and toast.display and len(self.children) > 1:
            if bottom and self.children[-1] is not toast:
                self.move_child(toast,after=self.children[-1])
            elif not bottom and self.children[0] is not toast:
                self.move_child(toast,before=self.children[0])
        # 底栏顶行是贴底偏移的输入，先解析（_footer_top 只直扫屏幕直属子件，
        # 不做 CSS 选择器匹配）。
        footer_top = _footer_top(self.screen)
        # 前置指纹命中 = 这一拍的输入与上一拍完全一致 → 宽度/高度测量与最终
        # key 必然都不变，直接返回（2026-10-27 A4）。
        prekey = self._cheap_place_key(origin, content, bottom, footer_top)
        if prekey == self._place_prekey:
            return
        self._place_prekey = prekey
        # 2026-10-18 第二轮：容器宽度只包住真正可见的气泡，不再固定 42 列。
        width = min(max(1, self._content_width()), max(1, content.width))
        child_metrics = []
        for child in self.children:
            if child.styles.display == 'none':
                continue
            if child.styles.is_auto_width:
                plain = getattr(getattr(child,'renderable',None),'plain','')
                child_width = max((cell_len(line) for line in plain.split('\n')),default=0)+2
            else:
                child_width = int(child.styles.width.value)
            child_metrics.append((child, min(width, child_width),
                                  self._child_height(child, width)))
        # 本拍容器高度 = 可见子件高度之和（Vertical 没有 gap/margin）。拿它算
        # 贴底偏移，不再读上一拍 self.region.height（文本变长时那是旧值）。
        estimated_height = sum(height for _child,_w,height in child_metrics)
        # 可用高度：到内容区下缘为止，且绝不进入底栏行。
        limit_bottom = content.bottom
        # footer_top 已在前置指纹之前解析（见上）。
        if footer_top is not None:
            limit_bottom = min(limit_bottom, footer_top)
        available = max(1, limit_bottom - content.y)
        # 估算比可用高度还高 → 容器高度钳到可用高度、y 钳到内容区顶部，超出
        # 的部分交给容器的 overflow: hidden 裁切（绝不外溢到边框/底栏上）。
        max_height = max(1, min(max(1, estimated_height), available))
        x = content.right - origin.x - width
        y_top = content.y - origin.y
        y_bottom = limit_bottom - origin.y - max_height
        if y_bottom < y_top:
            y_bottom = y_top
        key = (width, max_height, bottom, x, y_top, y_bottom,
               tuple((id(child),cw,h) for child,cw,h in child_metrics))
        if key == self._placed_key:
            return
        self._placed_key = key
        self.styles.width = width
        self.styles.max_height = max_height
        self.styles.offset = (x, y_bottom if bottom else y_top)
        for child,child_width,_height in child_metrics:
            child.styles.offset = (max(0,width-child_width),0)
        # y 已按本拍文本估算，不再依赖"等布局把高度算出来"的补拍；保留布局后
        # 的一次复算，兜住 content_region 在首拍尚未就绪（尺寸刚变）的情况。
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
        self._place_prekey = None
        self.place()

    def on_mouse_down(self, event):
        FloatingToast._forward_mouse(self, event, "down")

    def on_mouse_move(self, event):
        FloatingToast._forward_mouse(self, event, "move")

    def on_mouse_scroll_up(self, event):
        FloatingToast._forward_mouse(self, event, 'scroll_up')

    def on_mouse_scroll_down(self, event):
        FloatingToast._forward_mouse(self, event, 'scroll_down')


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
        # 基准一律取地图面板的**内容区**（见 MapHints.place 的说明）。
        content = pane.content_region
        if isinstance(self.parent, MapHints):
            # 先按消息定宽、再让容器按「最宽可见气泡」重排——顺序反过来会读到
            # 上一帧的容器宽度（旧实现因此把宽度钳在 42 列）。
            cap = min(42, max(8, int(content.width)))
            self.styles.width = min(cap, max(8, bubble_width(self._full_text)))
            self.styles.offset = (0, 0)
            self.parent.place()
            return
        # 独立挂载（测试/其它宿主）：与 MapHints 同一坐标口径——右缘贴
        # content_region.right、上缘贴 content_region.y，贴底时按**本拍文本**
        # 估算自身高度再定位，不读上一拍 region.height（2026-10-26）。
        # 总宽 = 文本 + 左右 padding 各 1 + round 边框各 1。
        # 首帧即完整宽度：宽度中途变化会让文本先折行再弹回（观感跳变）。
        total_w = min(max(1, int(content.width)), max(8, bubble_width(self._full_text)))
        self.styles.width = total_w
        gutter = self.styles.gutter
        inner = max(1, total_w - gutter.width)
        height = max(1, _wrapped_line_count(self._full_text.plain, inner) + gutter.height)
        origin = self.parent.content_region if self.parent is not None else content
        x = content.right - origin.x - total_w
        if _toast_anchor_bottom(self.app):
            limit_bottom = content.bottom
            footer_top = _footer_top(self.screen)
            if footer_top is not None:
                limit_bottom = min(limit_bottom, footer_top)
            y = max(content.y - origin.y, limit_bottom - origin.y - height)
        else:
            y = content.y - origin.y
        self.styles.offset = (x, y)

    # ---- Forward to the actual visible widget beneath the whole bubble stack. ----
    def on_mouse_down(self, event) -> None:
        self._forward_mouse(event, "down")

    def on_mouse_move(self, event) -> None:
        self._forward_mouse(event, "move")

    def on_mouse_scroll_up(self, event):
        self._forward_mouse(event, 'scroll_up')

    def on_mouse_scroll_down(self, event):
        self._forward_mouse(event, 'scroll_down')

    def _forward_mouse(self, event, kind: str) -> None:
        from textual import events
        from textual.geometry import Region
        from textual.widgets import Button

        event.stop()
        event.prevent_default()
        x = self.region.x + event.offset.x
        y = self.region.y + event.offset.y
        if not self.screen.region.contains(x, y):
            return
        target = next(((widget, region) for widget, region in
                       self.screen._compositor.get_widgets_at(x, y)
                       if not isinstance(widget, (FloatingToast, MapHintText, MapHints))
                       and not getattr(widget, 'transparent_text_overlay', False)), None)
        if target is None:
            return
        widget, region = target
        local_x, local_y = x - region.x, y - region.y
        strips = widget.render_lines(Region(0, local_y, region.width, 1))
        sample = next(iter(strips[0].crop(local_x, local_x + 1)), None) if strips else None
        event_type = {'down': events.MouseDown, 'move': events.MouseMove,
                      'scroll_up': events.MouseScrollUp, 'scroll_down': events.MouseScrollDown}[kind]
        forwarded = event_type(widget, local_x, local_y,
                               getattr(event, 'delta_x', 0), getattr(event, 'delta_y', 0),
                               getattr(event, 'button', 0), getattr(event, 'shift', False),
                               getattr(event, 'meta', False), getattr(event, 'ctrl', False), x, y,
                               sample.style if sample else None)
        if kind == 'down':
            self.app._keys_handled_in_on_key.clear()
            self.app._dismiss_transient()
            if isinstance(widget, Button) and event.button == 1:
                # Dismissing the bubble removes the original mouse-down target;
                # Textual cannot synthesize a matching Click on the button.
                widget.press()
                return
        widget.post_message(forwarded)

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
