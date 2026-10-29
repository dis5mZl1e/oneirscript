"""固定尺寸文本控件的快速 update（2026-10-26，现框架内优化）。

Textual 0.89 的 Static.update 无条件 refresh(layout=True)：即使控件是固定高度
（#status 5 行、#panel 1fr、#signal-status 1 行、#header-ticker 1 行、地图区
1fr…），每次正文更新也会让整个 Screen 重跑一遍布局。实测一次普通行动
（120×40，high 特效）里 layout 占 26–35ms、render 占 25–31ms，其中大部分
控件的内容根本没变或尺寸固定。

本模块安装一个幂等的 Static.update 包装：

1. **内容相同的更新直接跳过**。Textual 会把同一份 Text 重新 visualize+标脏；
   对 #hover-info / #panel-help / #signal-status / #equipment-sentence 这类
   每帧都会 update 但内容通常不变的控件，这是纯浪费。只对 str / rich.Text
   做相等判断（其它 Rich renderable 不猜）。
2. **标记 _fixed_layout = True 的控件不请求布局**：内容尺寸不改变控件尺寸，
   只需重绘；避免整屏 layout。标记由本模块统一写到确定固定高度的控件类上；
   自动高度/滚动条相关的控件不要标记（#hover-info、#map-mode-hint、
   SentenceWriter 等）。

注意：这里改的是 Textual 的 Static.update（依赖 0.89 的内部字段 _content /
_visual）。Textual 升级到不兼容版本时，本包装会退化为普通 update（测试
tests/test_fast_static_update_261026.py 会暴露）。安装入口在 ui/app/session.py，
让它在任何 App/控件创建之前执行。
"""
from __future__ import annotations

from textual.widgets import Static

_INSTALLED = False
_ORIGINAL_UPDATE = None
_FAST_UPDATE = None


def _same_content(old, new) -> bool:
    """只对 str / rich.Text 判等：其它 Rich renderable 的 __eq__ 不可靠且可能很贵。"""
    if old is new:
        return True
    from rich.text import Text

    if isinstance(old, (str, Text)) and type(old) is type(new):
        return old == new
    return False


def _mark_fixed_layout() -> None:
    """给确定固定高度的控件类打标记（延迟 import，避免加载期循环依赖）。"""
    from .widgets import EventPanel, HeaderTicker, MapView
    from .self_audit import ClickableStatus
    from .signal_status import SignalStatusLink
    from .controls_help import ControlsHelpLink

    for cls in (MapView, EventPanel, HeaderTicker, ClickableStatus, SignalStatusLink):
        cls._fixed_layout = True
    # #panel-help 默认固定 1 行；.panel-help-hint 变体是 auto/max-height 2，
    # 那时仍需要正常布局。
    ControlsHelpLink._fixed_layout = property(
        lambda self: not self.has_class("panel-help-hint"))


def _fast_update(self, content="") -> None:
    old = getattr(self, "_content", None)
    if _same_content(old, content):
        return
    fixed = getattr(self, "_fixed_layout", False)
    if callable(fixed):
        try:
            fixed = fixed()
        except Exception:
            fixed = False
    if fixed:
        # 与 Static.update 等价，只是不请求 layout：_visual 延迟到 render 重建。
        self._content = content
        self._visual = None
        try:
            self.clear_cached_dimensions()
        except Exception:
            pass
        self.refresh(layout=False)
        return
    return _ORIGINAL_UPDATE(self, content)


def install_fast_static_updates() -> None:
    """幂等安装包装（在 ui/app/session.py import 时调用一次）。"""
    global _INSTALLED, _ORIGINAL_UPDATE, _FAST_UPDATE
    if _INSTALLED:
        return
    from ..env_compat import get as env_get

    # 排障/A-B 开关：ONEIRSCRIPT_FAST_STATIC=0 完全退回 Textual 原生 update。
    if str(env_get("FAST_STATIC", "1")).strip().lower() in ("0", "off", "false", "no"):
        return
    _mark_fixed_layout()
    _ORIGINAL_UPDATE = Static.update
    _FAST_UPDATE = _fast_update
    Static.update = _FAST_UPDATE
    _INSTALLED = True


def set_fast_static_enabled(enabled: bool) -> bool:
    """测试/探针用：同进程切换包装开关；未安装时返回 False。"""
    if not _INSTALLED:
        return False
    Static.update = _FAST_UPDATE if enabled else _ORIGINAL_UPDATE
    return True


def fast_static_active() -> bool:
    return _INSTALLED and Static.update is _FAST_UPDATE
