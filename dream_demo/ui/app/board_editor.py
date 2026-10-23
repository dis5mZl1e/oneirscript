"""联想盘编辑器：开关、提交、光标/点击/滚动与刷新。"""
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

class BoardEditorMixin:
    """联想盘编辑器：开关、提交、光标/点击/滚动与刷新。"""

    # ---- 携带意象·联想盘编辑器（2026-10-09，设计方案 §8.4） ----

    # 工具栏按钮的动作 id（也是控件 id 后缀）。顺序即视觉顺序：
    # 视图切换与旋转在前，握持/自动安置居中，「确认整理」「取消」收尾。
    BOARD_TOOL_ACTIONS = ('view', 'rotate', 'discard', 'tool', 'auto', 'commit', 'cancel')

    def open_board_editor(self, instance_id: str | None = None) -> None:
        """打开编辑器：隐藏 #layout，只留覆盖层与底栏。

        `instance_id` 是「从原列表装配」的入口（§8.4）：带着这件进编辑器并直接
        拿在手上，不自动挤掉其他件——放不放得下由玩家自己看预览。
        """
        state = self.session.state
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
        if self.board_editor is not None:
            return
        self.board_editor_return = self.panel_selection
        self.query_one('#equipment-sentence', SentenceWriter).finish()
        self.board_editor = BoardEditorController(state)
        if instance_id:
            position = next(
                (index for index, (_, item) in enumerate(self.board_editor.list_rows)
                 if item.instance_id == instance_id),
                None,
            )
            if position is not None:
                self.board_editor.hold_from_list(position)
        self.panel_mode = "board_editor"
        self._board_follow_selection = (id(self.board_editor), self.board_editor.list_cursor, self.screen.size)
        self._panel_enter_mode = None
        self.set_focus(None)
        self.query_one("#layout").styles.display = "none"
        self.query_one("#board-editor").styles.display = "block"
        self.refresh_view()
        # Reopening begins with the comparison headings, even after scrolling
        # down to the effect details in an earlier editing session.
        self.query_one('#board-editor-scroll').scroll_home(animate=False)

    def open_board_editor_for_item(self, inventory_index: int) -> bool:
        """「从原列表装配」（§8.4）：原条目操作入口改为打开盘面预览。

        旧的 ``toggle_equip`` 会静默穿上/脱下；现在携带意象的位置权威是盘面，
        所以沿用同一个入口，但落到编辑器里，由玩家看着预览自己决定放不放。
        返回是否真的打开了（不可上盘的条目退回旧入口，调用方据此走原逻辑）。
        """
        state = self.session.state
        if self.home_mode or self.board_editor is not None or self._modal_menu_open():
            return False
        if not 0 <= inventory_index < len(state.inventory):
            return False
        item = state.inventory[inventory_index]
        if not state._placeable_slot(item):
            return False
        self.open_board_editor(item.instance_id)
        return True

    def close_board_editor(self, *, committed: bool = False) -> None:
        """关闭编辑器：草稿整体丢弃（committed=True 时已在 commit 里落盘）。

        关闭后回到携带意象页，并把列表选中项还原成打开前的那一行（§8.2）。
        """
        if self.board_editor is None:
            return
        self.board_editor = None
        self.query_one('#board-editor-sentence', SentenceWriter).clear()
        self.query_one('#board-editor-help', Static).update(Text())
        self.query_one("#board-editor").styles.display = "none"
        self.query_one("#layout").styles.display = "block"
        self.panel_mode = "equipment"
        self._panel_enter_mode = None
        self.panel_selection = self.board_editor_return
        self.panel_scroll = 0
        if not committed:
            # 草稿作废：派生视图可能已经被预览改脏，重算一次。
            self.session.state.equipment.invalidate()
        self.refresh_view()

        self.query_one(Footer).styles.display = 'block'
        self.refresh_bindings()
        self.screen.refresh(layout=True)

    def commit_board_editor(self) -> None:
        """「确认整理」：一次事务、一次行动。失败则留在编辑器里，不弹安全确认层。"""
        editor = self.board_editor
        if editor is None:
            return
        if editor.held is not None:
            editor.cancel_held()
        changed_layout = not editor.draft.same_layout(self.session.state.board)
        result = editor.commit(self.session)
        if not result.changed:
            # ActionResult 用 changed 当成功位：commit_board 失败时给出原因，
            # 布局没变的「空确认」则是 changed=True 且不扣时间。
            editor.message = result.message
            self.refresh_view()
            return
        if changed_layout:
            self._capture_projectile_action(changed=True)
        self.close_board_editor(committed=True)
        sentence = result.data.get('equipment_sentence')
        if sentence:
            self.query_one('#equipment-sentence', SentenceWriter).write(sentence, force=True)

    def board_editor_action(self, action: str) -> None:
        if self._inspection_active():
            return
        editor = self.board_editor
        if editor is None:
            return
        if action == "view":
            editor.toggle_view()
        elif action == "rotate":
            editor.rotate()
        elif action == "discard":
            editor.discard()
        elif action == "tool":
            editor.cycle_tool()
        elif action == "auto":
            editor.auto_place()
        elif action == "commit":
            self.commit_board_editor()
            return
        elif action == "cancel":
            if not editor.cancel_held():
                self.close_board_editor()
                return
        self.refresh_view()

    def board_editor_move_cursor(self, cell: tuple[int, int]) -> None:
        if self._inspection_active():
            return
        editor = self.board_editor
        if editor is None or editor.cursor == cell:
            return
        editor.cursor = cell
        self._refresh_board_editor(self._symbol_mode())

    def board_editor_click(self, cell: tuple[int, int]) -> None:
        if self._inspection_active():
            return
        editor = self.board_editor
        if editor is None:
            return
        editor.cursor = cell
        editor.activate()
        self.refresh_view()

    def board_editor_click_list(self, offset_y: int, offset_x: int | None = None) -> None:
        """说明区左键：命中「行囊中的携带意象」某一行就把它拿在手上。

        行号按渲染时记下的 `_board_side_rows` 换算（与盘面命中表分开，
        §8.1 要求两套命中表不混用）。
        """
        if self._inspection_active():
            return
        editor = self.board_editor
        rows = getattr(self, "_board_side_rows", None) or []
        if editor is None or not rows:
            return
        if offset_x is not None:
            hit = editor.hit_side(offset_y, offset_x)
            if hit is not None:
                editor.hold_from_list(hit.list_position)
                self.refresh_view()
            return
        row = offset_y
        if not 0 <= row < len(rows) or rows[row] is None:
            return
        editor.hold_from_list(rows[row])
        self.refresh_view()

    def board_editor_scroll(self, delta: int) -> None:
        if self._inspection_active():
            return
        try:
            side = self.query_one("#board-editor-scroll")
        except Exception:
            return
        side.scroll_y = max(0, side.scroll_y + delta)
        self._board_side_scroll = int(side.scroll_y)

    def handle_board_editor_key(self, key: str) -> bool:
        """编辑器模态的键盘路由。返回 True 表示按键已被消费。

        这里是**唯一**入口：InputMixin.on_key 的 board_editor 分支无条件 return，
        所以任何键都不会落到世界（走一步／发射一次）或原面板上。底栏键位点击
        与 priority 绑定 q 另由 `_modal_menu_open()` 拦死。

        只用局部键，不新增 F1—F12、不借用 Tab（Tab 是行囊快捷键）。WASD 也不
        参与：世界里的 WASD 是移动，编辑器内改成方向键＋小键盘，避免同一组
        字母在两个界面里表示两件事。
        """
        editor = self.board_editor
        if editor is None:
            return False
        # 模态吃掉**每一个**键：不只 on_key 里 return，还要打上「已处理」标记。
        # Textual 的绑定动作（x 观察 / f 发射 / n 下潜 / b 上浮 / g 捡起 / o 辅助 /
        # . 等待 / ~ 锁定）在 on_key 之后仍会各跑一次，只有 _handled_in_on_key
        # 能把那次重复触发吃掉——漏标一个就等于「整理盘面时顺手开了一枪」。
        # 终端收不到 Ctrl 组合（2026-10-10 玩家反馈）：确认走 Enter，
        # 拿放/安置走 a（自动安置保留在大写 A）。
        self._mark_key_handled(key)
        if key in ("enter", "return"):
            self.commit_board_editor()
            return True
        if key == "escape":
            # q 不在这里：它是 priority 绑定（先于 on_key 触发），语义统一由
            # InputMixin.action_context_q 承担，避免两条路径各取消一次。
            if not editor.cancel_held():
                self.close_board_editor()
            else:
                self.refresh_view()
            return True
        if key in ("up", "8", "num8", "kp8"):
            editor.move(0, -1)
        elif key in ("down", "2", "num2", "kp2"):
            editor.move(0, 1)
        elif key in ("left", "4", "num4", "kp4"):
            editor.move(-1, 0)
        elif key in ("right", "6", "num6", "kp6"):
            editor.move(1, 0)
        elif key in ("pageup", ",", "comma"):
            editor.move_list(-1)
        elif key in ("pagedown", ".", "period", "full_stop"):
            editor.move_list(1)
        elif key == "r":
            editor.rotate()
        elif key == "z":
            editor.cycle_tool()
        elif key == "p":
            editor.cycle_policy()
        elif key == "j":
            return True
        elif key == "x":
            editor.discard()
        elif key == "v":
            editor.toggle_view()
        elif key == "a":
            editor.activate()
        elif key == "A":
            editor.auto_place()
        elif key == "space":
            editor.hold_from_list()
        else:
            # 未匹配的键同样什么都不做——但不能让它继续往下走到世界或原面板。
            return True
        self.refresh_view()
        return True

    def _refresh_board_editor(self, mode: str) -> None:
        editor = self.board_editor
        if editor is None:
            return
        footer = self.query_one(Footer)
        height = max(1, self.screen.size.height - max(1, footer.outer_size.height))
        root = self.query_one('#board-editor')
        if getattr(self, '_board_editor_height', None) != height:
            self._board_editor_height = height
            root.styles.height = height
        total = editor.draft.width * editor.draft.height
        self.query_one("#board-editor-title", Static).update(Text(
            tr("携带意象 · 联想盘") + f"  {editor.draft.area_used()}/{total}"
            + tr("（草稿：确认整理前不生效、不耗时）"),
            style="bold " + CARRIED_IMAGE_STYLE,
        ))
        self.query_one("#board-editor-grid", Static).update(editor.render_grid())
        # Predict initial widths from the fixed grid column and screen. Reading
        # an auto-sized, still-hidden child yields zero and can freeze narrow
        # wrapping before that child ever receives a visible resize event.
        width = max(5, self.screen.size.width - root.styles.gutter.width - 22)
        content_width = max(5, width - 6)  # frame, padding and vertical scrollbar
        self.query_one('#board-editor-grammar', Static).update(editor.render_grammar(width))
        self.query_one('#board-editor-status', Static).update(editor.render_status(width))
        compiled = editor._preview_compiled()
        self.query_one('#board-editor-sentence', SentenceWriter).write(
            compiled.text, fragments=((compiled.text, FIELD_COLORS['effects']),))
        self.query_one('#board-editor-inspect', Static).update(editor.render_inspect())
        side = self.query_one("#board-editor-side", Static)
        side.update(editor.render_side(width=content_width, comparison_only=True))
        effects = self.query_one('#board-editor-effects', Static)
        effects.update(editor.render_effects(width=content_width))
        labels = {
            "view": tr('读句 v') if editor.view == 'equipment' else tr('摆放 v'),
            "rotate": tr("旋转 r/中键"),
            "discard": tr("拆除 x/右键"),
            "tool": tr("功能词 z"),
            "auto": tr("安置 A"),
            "commit": tr('确认 Enter'),
            "cancel": tr("取消 Esc"),
        }
        for action in self.BOARD_TOOL_ACTIONS:
            widget = self.query_one(f"#board-tool-{action}", Static)
            widget.update(Text(labels[action],
                               style="bold #ffd166" if action == "commit" else "#ffffff"))
            widget.set_class(action == "commit", "accent")
        self.query_one("#board-editor-help", Static).update(editor.render_help())
        # 说明区的行 → 列表位置命中表（只给「行囊中的携带意象」那几行登记）。
        self._board_side_rows = editor.side_row_map
        self._board_side_scroll = int(self.query_one("#board-editor-scroll").scroll_y)
        selection_key = (id(editor), editor.list_cursor, self.screen.size)
        if getattr(self, '_board_follow_selection', None) != selection_key:
            self._board_follow_selection = selection_key
            self.call_after_refresh(self._follow_board_selection)

    def _follow_board_selection(self) -> None:
        editor = self.board_editor
        if editor is None or self.panel_mode != 'board_editor':
            return
        rows = [row for row, selected in enumerate(self._board_side_rows)
                if selected == editor.list_cursor]
        if not rows:
            return
        scroll = self.query_one('#board-editor-scroll')
        side = self.query_one('#board-editor-side')
        # Region coordinates already include current scrolling; request only
        # enough movement to reveal the item's first wrapped line.
        y = side.content_region.y + rows[0]
        if y < scroll.content_region.y:
            scroll.scroll_relative(y=y - scroll.content_region.y, animate=False)
        elif y >= scroll.content_region.bottom:
            scroll.scroll_relative(y=y - scroll.content_region.bottom + 1, animate=False)
        self._board_side_scroll = int(scroll.scroll_y)

    def _refresh_settings_rows(self, mode: str) -> None:
        """设置页行渲染：主页（home_settings）与暂停菜单（pause_settings）共用。"""
        for index, definition in enumerate(self.config.registry):
            self.query_one(f"#setting-row-{index}", Static).update(
                render_setting_row(self.settings_page, self.config, mode, index, definition)
            )
        self.query_one("#settings-feedback", Static).update(
            self.settings_page.feedback or tr("↑↓ 选择 · ←→ 调整 · Enter/Space 修改 · Q 返回")
        )
