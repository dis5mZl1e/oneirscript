"""面板路由族：图鉴/历史/设置页的开关、滚动与行激活。"""
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

class PanelsMixin:
    """面板路由族：图鉴/历史/设置页的开关、滚动与行激活。"""

    def _toggle_panel(self, mode: str, *, manual: bool = True) -> None:
        # 暂停菜单开着时面板不可切（hidden 布局的按钮收不到点击，键盘已
        # 被模态分支吃掉；这里是兜底——万一有路径漏进来也不许破坏暂停态）。
        if self._modal_menu_open(allow_inspection=True):
            return
        self._panel_enter_mode = None
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
        state = self.session.state
        if state.tutorial.get("active"):
            # 教程埋点：面板步需要「真正打开行囊」的证据（面板切换不耗回合，
            # 完成判定只能靠这里写旗标，由教程 pump 每帧评估）。
            state.tutorial_events["panel_opened"] = mode
        # 再按一次同一页 = 收起；收起后的落点同样走默认页（左侧事件记录开启
        # 时是行囊，否则是事件记录）。manual=False 给教程等自动开页用，避免
        # 在锁定态把「锁定页」改掉。
        target = self._default_panel_mode() if self.panel_mode == mode else mode
        # 焦点必须先于 refresh_view 同步：提示条与焦点边框都在刷新里按
        # cursor_zone 取文本/线型，写在刷新之后会让它们停上一帧（80×24 实测）。
        if not self.home_mode:
            self.cursor_zone = "map" if target == "world" else "panel"
        self._sidebar_transition(target, manual=manual)

    def catalog_progress(self) -> dict[str, dict]:
        return self.session.manager.merge_catalogs(
            self.session.state.catalog,
            self.session.manager.load_catalog(),
        )

    # ---- 旧梦回忆（主页第三页，独立 history.json 数据源）----

    def _open_history(self) -> None:
        self.panel_mode = "home_history"
        # 重新打开时光标保留，但钳到当前列表长度内（记录可能被上限顶掉）。
        runs = self._history_runs()
        state = self.history_page
        state["selection"] = min(state["selection"], max(0, len(runs) - 1))
        state["detail"] = None
        state["detail_scroll"] = 0
        self.refresh_view()
        self.call_after_refresh(self._refresh_history_after_layout)

    def _refresh_history_after_layout(self) -> None:
        if self.is_running and self.panel_mode == 'home_history':
            self.refresh_view()

    def _history_runs(self) -> list:
        return SaveManager(self.base_save_dir).load_history()["runs"]

    def _history_viewport_rows(self) -> int:
        try:
            return max(1, self.query_one("#history-list").content_size.height)
        except Exception:
            return 24

    def scroll_history(self, delta: int) -> None:
        """滚轮/键盘滚动：列表态滚条目，详情态滚详情行。"""
        state = self.history_page
        if state["detail"] is not None:
            state["detail_scroll"] = max(0, state["detail_scroll"] + delta)
            self.refresh_view()
            return
        runs = self._history_runs()
        if not runs:
            return
        state["selection"] = max(0, min(len(runs) - 1, state["selection"] + delta))
        # 选中项移出可视窗口时把窗口滑过去。
        if state["selection"] < state["scroll"]:
            state["scroll"] = state["selection"]
        elif state["selection"] > state["scroll"] + max(getattr(self, '_history_hit_rows', {}).values(), default=0):
            state["scroll"] = state["selection"]
        state["scroll"] = max(0, min(state["scroll"], max(0, len(runs) - 1)))
        self.refresh_view()

    def history_list_click(self, row: int) -> None:
        """左键列表行：选中并打开该局详情。"""
        runs = self._history_runs()
        state = self.history_page
        index = state["scroll"] + row
        if not (0 <= index < len(runs)):
            return
        state["selection"] = index
        state["detail"] = runs[index]
        state["detail_scroll"] = 0
        self.refresh_view()

    def _close_history_detail(self) -> None:
        self.history_page["detail"] = None
        self.history_page["detail_scroll"] = 0
        self.refresh_view()

    def _handle_history_key(self, key: str) -> None:
        state = self.history_page
        if state["detail"] is not None:
            if key in ("escape", "q", "enter", "return"):
                self._close_history_detail()
            elif key in ('up', 'w', 'num8', 'kp8', 'pageup'):
                self.scroll_history(-max(1, self._history_viewport_rows()-1) if key == 'pageup' else -1)
            elif key in ('down', 's', 'num2', 'kp2', 'pagedown'):
                self.scroll_history(max(1, self._history_viewport_rows()-1) if key == 'pagedown' else 1)
            elif key == 'home':
                state['detail_scroll'] = 0
                self.refresh_view()
            elif key == 'end':
                state['detail_scroll'] = 10**6
                self.refresh_view()
            return
        if key in ("up", "num8", "kp8", "w"):
            self.scroll_history(-1)
        elif key in ("down", "num2", "kp2", "s"):
            self.scroll_history(1)
        elif key in ("enter", "return", "space"):
            runs = self._history_runs()
            if runs:
                state["detail"] = runs[min(state["selection"], len(runs) - 1)]
                state["detail_scroll"] = 0
                self.refresh_view()
        elif key in ("escape", "q"):
            self.panel_mode = "home"
            self.refresh_view()

    def _focus_codex_list(self) -> None:
        """图鉴覆盖层刚 display block，等一拍再 focus（立即 focus 可能不生效）。"""
        if self.panel_mode in ("home_catalog", "pause_codex"):
            try:
                self.query_one("#codex-list").focus()
            except Exception:  # pragma: no cover - 覆盖层已被收起的竞态
                pass

    def _refresh_codex_components(self, mode: str) -> None:
        """图鉴组件刷新：列表/详情/键位提示/窄终端警告（主页与游戏内覆盖层共用）。

        2026-10-14 从 _refresh_home_views 提取——pause_codex 模式下 #home 不可见，
        这段渲染必须能独立跑。
        """
        progress = self.catalog_progress()
        viewport_rows = self._codex_viewport_rows()
        self.query_one("#codex-list", Static).update(
            render_codex_list(
                self.codex_page,
                self.catalog_definitions,
                progress,
                mode,
                viewport_size=viewport_rows,
                width=self._codex_list_width(),
            )
        )
        self.catalog_diagnostics.clear()
        self.query_one("#codex-detail", Static).update(
            render_codex_detail(
                self.codex_page,
                self.catalog_definitions,
                progress,
                mode,
                diagnostics=self.catalog_diagnostics,
            )
        )
        at_categories = self.codex_page.focus_layer == "categories"
        if not at_categories:
            codex_help = tr("←→ 切换分类 · ↑↓ 选择条目 · 滚轮浏览 · Q 返回分类")
        elif self.panel_mode == "pause_codex":
            codex_help = tr("←→↑ 选择分类 · ↓/Enter 进入条目 · Q 返回菜单")
        else:
            codex_help = tr("←→↑ 选择分类 · ↓/Enter 进入条目 · Q 返回主页")
        self.query_one("#codex-help", Static).update(codex_help)
        codex_too_narrow = self.panel_mode in ("home_catalog", "pause_codex") and self.size.width < 64
        self.query_one("#codex-body").styles.display = "none" if codex_too_narrow else "block"
        self.query_one("#codex-too-small").styles.display = "block" if codex_too_narrow else "none"

    def _open_codex(self) -> None:
        # [SFX挂点] 主页打开图鉴：建议 book_open（图鉴翻页）。
        self.panel_mode = "home_catalog"
        self.codex_page.focus_categories()
        self.refresh_view()
        self.query_one("#codex-list").focus()

    def _open_settings(self) -> None:
        self.settings_from = "home"
        self.panel_mode = "home_settings"
        self.settings_page.capture_target = None
        self.refresh_view()
        self.query_one("#settings-list").focus()

    def _codex_back(self) -> None:
        if self.codex_page.focus_layer == "entries":
            self.codex_page.focus_categories()
        elif self._restore_shortcut_page():
            return
        elif self.panel_mode == "pause_codex":
            # 游戏内（暂停菜单打开的图鉴）：覆盖层换回暂停菜单。
            self.panel_mode = "pause"
            self.query_one("#codex-page").styles.display = "none"
            self.query_one("#pause-menu").styles.display = "block"
        else:
            # 回主页选项：panel_mode 复原成 "home"（主页总提示）。
            # 不改 home_row——光标仍停在进图鉴前的那一行；渲染/Enter 都跟着光标走，
            # 只有提示文案回落到通用那条，与「从图鉴退回来」的语境一致。
            self.panel_mode = "home"
        self.refresh_view()

    def _settings_back(self) -> None:
        if self.settings_page.capture_target is not None:
            self.settings_page.cancel_capture()
        elif self._restore_shortcut_page():
            return
        else:
            self.settings_page.confirm_delete = False
            if self.settings_from == "pause" and not self.home_mode:
                # 暂停菜单打开的设置页：Q/Esc 回暂停菜单（不回主页）。
                self.panel_mode = "pause"
                self.query_one("#settings-page").styles.display = "none"
                self.query_one("#pause-menu").styles.display = "block"
            else:
                self.panel_mode = "home"
        self.refresh_view()

    def _delete_history_stats(self) -> SettingChange:
        """删除全部历史统计：图鉴文件 + 各存档局内的记录，一并清空（不可恢复）。

        逐槽清空存档里的 ``state.catalog``（编码/解码往返由持久化层保证），
        最后删除共享的 catalog.json；之后任何存档再保存也不会把旧统计合回来。
        """
        if not self.session.persistence_enabled:
            return SettingChange(False, tr('教程中不修改正式记录。'))
        self.session.state.catalog = {}
        manager = self.session.manager
        try:
            if manager.catalog_file.exists():
                manager.catalog_file.unlink()
        except OSError:
            pass
        for slot in range(1, manager.SLOT_COUNT + 1):
            slot_manager = manager.for_slot(slot)
            if not (slot_manager.primary.exists() or slot_manager.backup.exists()):
                continue
            try:
                slot_state = slot_manager.load()
                slot_state.catalog = {}
                slot_manager.save(slot_state)
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return SettingChange(True, tr("历史统计已删除。"))

    def _unlock_all_catalog(self) -> SettingChange:
        """一键解锁全部图鉴：所有条目的遭遇/交互计数补到 1 并写入持久图鉴。

        只做「从无到有」的标记（已有计数取 max 不覆盖），不清除任何
        现有记录；与「删除历史统计」互不影响。
        """
        if not self.session.persistence_enabled:
            return SettingChange(False, tr('教程中不修改正式记录。'))
        manager = self.session.manager
        merged = manager.merge_catalogs(self.session.state.catalog, manager.load_catalog())
        unlocked = 0
        for definition in self.catalog_definitions.values():
            entry = merged.setdefault(
                definition.catalog_id,
                {
                    "name": definition.name,
                    "category": definition.category.value,
                    "encounters": 0,
                    "interactions": 0,
                    "kills": 0,
                    "drops_seen": [],
                    "details": [],
                },
            )
            if definition.category is CatalogCategory.CONSCIOUSNESS:
                if int(entry.get("encounters", 0)) == 0:
                    entry["encounters"] = 1
                    unlocked += 1
            elif int(entry.get("interactions", 0)) == 0:
                entry["interactions"] = 1
                unlocked += 1
        manager.save_catalog(merged)
        self.session.state.catalog = merged
        return SettingChange(True, tr("图鉴已全部解锁（新标记 {n} 条）。").format(n=unlocked))

    def _codex_viewport_rows(self) -> int:
        """列表可见行数；两列布局下每行放两条目。"""
        try:
            return max(1, self.query_one("#codex-list").content_size.height)
        except Exception:
            return 10

    def _codex_viewport_size(self) -> int:
        """列表可见**条目数**（两列 × 行数）；导航/滚动按条目下标计算。"""
        return max(2, self._codex_viewport_rows() * 2)

    def _codex_list_width(self) -> int:
        try:
            return max(8, self.query_one("#codex-list").content_size.width)
        except Exception:
            return 50

    def scroll_codex(self, delta: int) -> None:
        # [SFX挂点] 图鉴列表滚动（↑↓/滚轮）：建议 book_flip（图鉴翻页）。
        # 两列布局下一次滚轮应滚一个视觉行（两条目），而不是一条。
        self.codex_page.scroll_entries(
            int(delta) * 2,
            self.catalog_definitions,
            viewport_size=self._codex_viewport_size(),
        )
        self.refresh_view()

    def select_codex_row(self, row: int, column: int = 0) -> None:
        self.codex_page.select_visible_row(
            row, self.catalog_definitions, self.catalog_progress(), column)
        self.refresh_view()

    def activate_setting(self, index: int, x: int, width: int) -> None:
        # [SFX] 设置项调整（点击/Enter 左半减右半加）。
        if not (0 <= index < len(self.config.registry)):
            return
        if self.config.get("sfx_enabled"):
            sfx.play("ui_click", volume=int(self.config.get("sfx_volume")) / 10)
        self.settings_page.selected = index
        definition = self.config.registry[index]
        if definition.setting_type.value in {"enum", "int"}:
            self.settings_page.adjust(self.config, -1 if x < width // 2 else 1, self.config.registry)
        else:
            self.settings_page.activate(self.config, self.config.registry)
        # 语言项切换后标题栏标题换中文名/英文名（幂等，其余设置项无影响）。
        self._sync_language()
        # 装备句法项切换后同步「新盘面默认语序」（幂等，不改当前盘面）。
        self._sync_equipment_syntax()
        self.refresh_view()

    def _select_settings_category(self, category=None, *, delta=0):
        if self.settings_page.capture_target is not None:
            return
        widget = self.query_one('#settings-list')
        page = self.settings_page
        page.category_scrolls[page.active_category] = widget.scroll_y
        if category is None:
            page.cycle_category(delta, self.config.registry)
        else:
            page.select_category(category, self.config.registry)
        self.refresh_view()
        self.call_after_refresh(lambda: widget.scroll_to(
            y=page.category_scrolls.get(page.active_category, 0), animate=False))

    def _scroll_settings_cursor(self):
        self.query_one(f'#setting-row-{self.settings_page.selected}').scroll_visible(animate=False)
