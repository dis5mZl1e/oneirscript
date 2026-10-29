"""教程卡（2026-09-19）：0 层「梦的起始」的引导步骤卡。

挂在地图底部中央。内容由 core.tutorial.tutorial_card_text
生成，引导未激活时 update 空 Text 并隐藏。
"""

from __future__ import annotations

from rich.cells import cell_len

from textual.widgets import Static
from .ornament_frame import OrnamentBorderMixin


class TutorialCard(OrnamentBorderMixin, Static):
    DEFAULT_CSS = """
    TutorialCard {
        layer: toast;
        position: absolute;
        width: auto;
        max-width: 46;
        height: auto;
        background: #141a24 92%;
        border: round #4f6b8f;
        padding: 0 1;
        display: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._visible = False

    def on_mouse_down(self, event):
        from ..core.origin_course import COURSE_TEMPLATE_VERSION
        if self.app.session.state.tutorial.get('version')==COURSE_TEMPLATE_VERSION:
            event.stop()
            self.app._toggle_panel('tasks', manual=False)
            return
        from .floating_toast import FloatingToast
        FloatingToast._forward_mouse(self, event, "down")

    def on_mouse_move(self, event):
        from .floating_toast import FloatingToast
        FloatingToast._forward_mouse(self, event, "move")

    def show_step(self, text) -> None:
        """按当前步骤刷新卡片；空 Text 表示引导未激活，收起。

        位置锚在地图区底部居中（2026-09-19 从左上角挪来——左上角正好压在
        出生点附近的地形上）。宽高在更新后按文本实测，offset 每帧重算，
        与 FloatingToast._layout_at 同一套手法。
        """
        if not text.plain.strip():
            if self._visible:
                self._visible = False
                self.styles.display = "none"
            return
        if not self._visible:
            self._visible = True
            self.styles.display = "block"
        self.update(text)
        from .floating_toast import MapHints
        if isinstance(self.parent, MapHints):
            self.parent.place()
            self.styles.width = "100%"
            self.styles.offset = (0, 0)
            return
        try:
            pane = self.app.query_one("#map-pane")
            pane_h = pane.content_size.height
            pane_w = pane.content_size.width
        except Exception:
            return
        raw_lines = text.plain.splitlines() or [""]
        longest = max(cell_len(line) for line in raw_lines)
        card_w = max(20, min(46, longest + 6, pane_w - 2))
        # 与 Static 使用同一渲染测量；单词/标点折行不能用字符总宽估算。
        inner = max(1, card_w - 4)
        visual_lines = self.get_content_height(pane.content_size, self.app.size, inner)
        card_h = visual_lines + 2  # 上下边框
        self.styles.width = card_w
        self.styles.offset = (max(0, (pane_w - card_w) // 2), max(0, pane_h - card_h))
