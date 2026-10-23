"""DreamApp 应用包（自 ui/app.py 拆分，纯搬家见 docs/megafile-refactor-plan.md）。"""
import time  # noqa: F401  兼容历史 patch("dream_demo.ui.app.time.monotonic")

from .app import (
    DreamApp, create_session, _sentence_fragments, MapView,
    FX_WRITEBACK_HZ, FX_WRITEBACK_INTERVAL, DECO_FRAME_HZ,
)
from .board_editor import BoardEditorMixin
from .css import AppCssMixin
from .footer import I18nFooter
from .navigation import NavigationMixin, new_run_seed
from .panels import PanelsMixin
from .session import SessionMixin

__all__ = [
    "DreamApp", "I18nFooter", "create_session", "new_run_seed", "_sentence_fragments",
    "MapView", "FX_WRITEBACK_HZ", "FX_WRITEBACK_INTERVAL", "DECO_FRAME_HZ",
    "AppCssMixin", "NavigationMixin", "BoardEditorMixin",
    "PanelsMixin", "SessionMixin",
]
