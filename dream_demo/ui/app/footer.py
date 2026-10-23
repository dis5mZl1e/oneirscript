"""DreamApp 底栏：随界面语言重排键位描述。"""
from __future__ import annotations

import math
import json
import random
import time
from pathlib import Path

from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Static

from ...audio import sfx
from ...music import music_scene
from ...config import ConfigManager, SettingChange
from ...user_config import load_user_config
from ...i18n import STATUS_TIERS, get_language, set_language, tr
from ...core import GameState, Material
from ...catalog_registry import CatalogCategory, CatalogDiagnostic, build_catalog_definitions
from ...menu_pages import CodexPageState, SettingsPageState, render_codex_detail, render_codex_list, render_history_detail, render_history_list, render_setting_row
from ...mapgen import region_for_depth
from ...materials import gas_def, liquid_def
from ...persistence import GameSession, OutdatedSaveError, SaveManager
from ...symbols import symbol
from .._native import _trace_native, select_mouse_driver
from .. import glyphs
from ..home_title import home_title_text
from ..home_scene import HomeScene, DreamStatic, DreamVertical, DreamHorizontal, dream_title_text
from ..frame_geometry import compose_fx, projectile_color
from ..map_particles import MapParticles
from ..ornament_frame import OrnamentPane
from ..input import InputMixin
from ..qol import QoLUIMixin
from ..debug_panel import DebugPanelMixin
from ..floating_toast import FloatingToast, MapHints, MapHintText
from ..sentence_writer import SentenceWriter
from ..newgame_options import NewGameOptionsView, options_text, summary_text, detail_text
from ..tutorial_card import TutorialCard
from ..settlement import SettlementScreen
from ..effects import (FXEngine, FxSnapshot, FxSource, FxHit, FxProjectile, FxCombatPulse, FxCast,
                      BORDER_EVENT_COLORS, RIPPLE_LIFE, RIPPLE_MAX_RADIUS,
                      RIPPLE_MIN_RADIUS, RIPPLE_RESET_TURNS, PROJECTILE_LIFE,
                      PROJECTILE_TOTAL, overlay_style, projectile_flight_time, PROJECTILE_END_LIFE,
                      projectile_repeat_delay,projectile_replay_time)
from ..render import render_map
from ...core.cast_fx import charging_casts
from ...data.anomaly_skills import FX_PROFILES
from ..transition import TOTAL, cell_off_time_a, cell_on_time_b, cell_segments, compose_frame
from ...core.tutorial import tutorial_card_text, tutorial_pump, tutorial_target_cells

try:
    # textual 0.89 的分区竖线（真正的 Rule 控件在私有模块 _rule 里）。
    from textual.widgets._rule import Rule
except Exception:  # pragma: no cover - 版本升级兜底
    Rule = None
from ..panels import PanelViewMixin
from ..region_themes import DEFAULT_PANEL_BG, MAP_BG, RegionTheme, theme_for_depth, theme_for_realm
from ..deco import border_flow_colors
from ..styles import BAR_IMAGINATION_STYLES
from ..styles import BAR_LUCIDITY_STYLES
from ..styles import BAR_MIND_STYLES
from ..styles import CARRIED_IMAGE_STYLE
from ..styles import GAME_FRAME_SECONDS
from ..styles import HOME_PANEL_MODES
from ..styles import LAYER_LABEL_STYLE
from ..widgets import (
    CodexListView,
    HistoryListView,
    DebugListWidget,
    DreamHeader,
    EventPanel,
    HeaderTicker,
    MapView,
    MapOverlayPanel,
    NativeButton,
    QolConfirmButton,
    PauseOptionView,
    SettingRowView,
    SettingsListView,
    TamperOverlayPanel,
)
from ..tampering import TamperUIMixin
from ..board_editor import (
    FIELD_COLORS,
    BoardEditorController,
    BoardEditorView,
    BoardGridView,
    BoardSideView,
    BoardToolButton,
)

class FooterToggle(Button):
    def on_mouse_down(self, event):
        if event.button == 1 and event.control is None:
            self.suppress_click()
            self.parent.toggle()
            event.stop()


class I18nFooter(Footer):
    """底栏：键位描述在 compose 时**重新过一遍 tr()**。

    App.BINDINGS 的描述在 import（类定义）时就经 tr() 固化成了字符串——而语言
    是运行时才从配置读的，import 时刻恒为中文原文，于是英文模式下底栏永远显示
    中文。这里在 Footer 每次重排（compose）时把每个键位的描述重新取词：语言
    切换后由 _sync_language / refresh_view 调 refresh_bindings() 触发重排即换语言。
    描述在英文下已是英文键值，tr() 查不到原样返回，幂等安全。
    """

    DEFAULT_CSS = '''
    I18nFooter { overflow-y: auto; }
    I18nFooter #footer-toggle {
        dock: right; width: 10; min-width: 10; height: 1;
        padding: 0; border: none; background: #303047; color: #eeeeff;
    }
    I18nFooter #footer-toggle:hover { background: #50506a; }
    '''
    expanded = False
    # 常驻第一行的常用键（2026-10-23 用户定稿）。初始化与重排都按这份顺序
    # 把对应 FooterKey 排到最前，其余键保持绑定声明顺序排在后面。
    PREFERRED_KEYS = ('escape', 'enter', 'c', 'n', 'b', 'full_stop', 'g', 'f', 'x')
    TOGGLE_WIDTH = 10
    KEY_FOOTPRINT = 14
    KEY_MIN_WIDTH = 10

    def compose(self) -> ComposeResult:
        nodes = list(super().compose())
        # 地图篡改键不是 Textual Binding（避免新游戏里按 C 前进时误触发世界面板）；
        # 这里手工放一个 FooterKey，点击走 action_world_tamper，键盘仍由 on_key 处理。
        from textual.widgets._footer import FooterKey
        nodes.append(FooterKey('c', 'C', tr('篡改'), 'world_tamper'))
        nodes = self._order_nodes(nodes)
        self._fit_grid(nodes=nodes)
        for node in nodes:
            description = getattr(node, "description", "")
            if description:
                node.description = tr(description)
                tooltip = getattr(node, "tooltip", "")
                if tooltip:
                    node.tooltip = tr(tooltip)
            yield node
        toggle = FooterToggle(tr('收起 ▲') if self.expanded else tr('展开 ▼'), id='footer-toggle')
        toggle.styles.offset = (0, int(self.styles.height.value) - 1)
        yield toggle

    def _order_nodes(self, nodes):
        """常用键按 PREFERRED_KEYS 置顶，其余键保持传入的声明顺序。"""
        order = {key: index for index, key in enumerate(self.PREFERRED_KEYS)}
        return sorted(nodes, key=lambda node: order.get(getattr(node, "key", None), len(order)))

    def _common_prefix(self, nodes) -> int:
        """最前面连续命中常用键表的键数（排序后即第一行优先保留的数量）。"""
        preferred = set(self.PREFERRED_KEYS)
        count = 0
        for node in nodes:
            if getattr(node, "key", None) in preferred:
                count += 1
            else:
                break
        return count

    def _grid_columns(self, count: int, common: int) -> int:
        """每个键约 14 列；常用键只要每格还留得住 10 列，就优先塞满第一行。"""
        available = max(1, self.app.size.width - self.TOGGLE_WIDTH)
        columns = available // self.KEY_FOOTPRINT
        if common:
            columns = max(columns, min(common, available // self.KEY_MIN_WIDTH))
        return max(1, min(count or 1, columns))

    def _fit_grid(self, count: int | None = None, nodes=None) -> int:
        """Reserve the right edge for the toggle; keep the default footprint one row.

        收起时只显示第一行（常用键优先），展开后其余键按同一列数往下排；
        描述过长时由 Textual 截断，仍可展开看全。
        """
        keys = list(nodes) if nodes is not None else [
            child for child in self.children if child.id != 'footer-toggle']
        count = len(keys) if count is None else count
        columns = self._grid_columns(count, self._common_prefix(keys))
        self.styles.grid_size_columns = columns
        self.styles.grid_columns = '1fr'
        self.styles.grid_rows = '1'
        self.styles.height = min(max(1, self.app.size.height // 3), max(1, math.ceil(count / columns))) if self.expanded else 1
        for toggle in self.query('#footer-toggle'):
            toggle.styles.offset = (0, int(self.styles.height.value) - 1)
        for index, key in enumerate(keys):
            key.display = self.expanded or index < columns
        return columns

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.query_one('#footer-toggle', Button).label = tr('收起 ▲') if self.expanded else tr('展开 ▼')
        self.scroll_home(animate=False)
        self._fit_grid()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'footer-toggle':
            event.stop()
            self.toggle()

    def on_resize(self, event) -> None:
        self._fit_grid()

    async def bindings_changed(self, screen) -> None:
        await super().bindings_changed(screen)
        self._fit_grid()
