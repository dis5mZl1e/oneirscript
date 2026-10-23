"""界面层（原 ``dream_demo/app.py``）。

按职责拆分：styles（配色）/ glyphs（字形与几何）/ render（地图渲染）/
widgets（控件）/ panels（面板文本）/ input（输入路由）/ app（应用主体）。
"""

from .app import DreamApp, create_session, new_run_seed
from .glyphs import (
    _unicode_mode,
    darken,
    compact_tile_glyph,
    layered_background,
    liquid_depth_key,
    normalize_tile_glyph,
    viewport_origin,
    with_background,
)
from .render import render_map
from .styles import (
    AGGREGATE_PANEL_STYLES,
    AGGREGATE_STYLES,
    CATEGORY_STYLES,
    GAME_FRAME_SECONDS,
    HOLD_RELEASE_TIMEOUT,
    INSIGHT_STYLE,
    MOVE_REPEAT_MIN_SECONDS,
    OBSERVATION_ATTR_COLORS,
    OBSERVATION_KIND_COLOR,
    PORTENT_HINT_STYLE,
    PORTENT_STYLE,
    RELATION_STYLES,
    RIGHT_PANEL_MODES,
    TRAUMA_STYLES,
)
from .widgets import (
    CodexListView,
    DreamHeader,
    EventPanel,
    HeaderTicker,
    MapOverlayPanel,
    MapView,
    NativeButton,
    RunClock,
    SettingRowView,
    SettingsListView,
)

__all__ = [
    "AGGREGATE_PANEL_STYLES",
    "AGGREGATE_STYLES",
    "CATEGORY_STYLES",
    "CodexListView",
    "DreamApp",
    "DreamHeader",
    "EventPanel",
    "GAME_FRAME_SECONDS",
    "HOLD_RELEASE_TIMEOUT",
    "HeaderTicker",
    "INSIGHT_STYLE",
    "MapOverlayPanel",
    "MapView",
    "MOVE_REPEAT_MIN_SECONDS",
    "NativeButton",
    "OBSERVATION_ATTR_COLORS",
    "OBSERVATION_KIND_COLOR",
    "PORTENT_HINT_STYLE",
    "PORTENT_STYLE",
    "RELATION_STYLES",
    "RIGHT_PANEL_MODES",
    "RunClock",
    "SettingRowView",
    "SettingsListView",
    "TRAUMA_STYLES",
    "_unicode_mode",
    "create_session",
    "new_run_seed",
    "darken",
    "compact_tile_glyph",
    "layered_background",
    "liquid_depth_key",
    "normalize_tile_glyph",
    "render_map",
    "viewport_origin",
    "with_background",
]
