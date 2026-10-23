"""DreamApp 应用主体（拆分后主类壳）：视图刷新、FX/装饰 tick、主页场景。"""
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
from ...materials import TRANSPARENT_WALLS, gas_def, liquid_def, wall_def, plant_height
from ...persistence import GameSession, OutdatedSaveError, SaveManager
from ...symbols import symbol

# §12 D：真实电光的装饰预算。超过就按步长降采样，保留空间分布，
# 不取前 N 格（那会让一条电路的另一端整段不亮）。
ELECTRIC_LIGHT_MAX = 16
from .._native import _trace_native, select_mouse_driver
from .. import glyphs
from ..home_title import home_title_text
from ..home_scene import HomeScene, DreamStatic, DreamVertical, DreamHorizontal, dream_title_text
from ..frame_geometry import compose_fx, projectile_color
from ..map_particles import MapParticles
from ..ornament_frame import OrnamentPane
from ..input import InputMixin
from ..qol import QoLUIMixin
from ..graphics import GraphicsMixin
from ..debug_panel import DebugPanelMixin
from ..floating_toast import FloatingToast, MapHints, MapHintText
from ..sentence_writer import SentenceWriter
from ..newgame_options import NewGameOptionsView, options_text, summary_text, detail_text
from ..tutorial_card import TutorialCard
from ..settlement import SettlementScreen
from ..effects import (FXEngine, FxSnapshot, FxSource, FxHit, FxWave, FxProjectile, FxCombatPulse, FxCast,
                      BORDER_EVENT_COLORS, RIPPLE_LIFE, RIPPLE_MAX_RADIUS,
                      RIPPLE_MIN_RADIUS, RIPPLE_RESET_TURNS, PROJECTILE_LIFE,
                      PROJECTILE_TOTAL, overlay_style, projectile_flight_time, PROJECTILE_END_LIFE,
                      projectile_repeat_delay,projectile_replay_time,
                      SOUND_WAVE_LIFE, SOUND_WAVE_MAX, light_flash_sources)
from ..render import render_map
from ...core.cast_fx import charging_casts
from ...data.anomaly_skills import FX_PROFILES
from ..transition import TOTAL, cell_off_time_a, cell_on_time_b, cell_segments, compose_frame
from ...core.tutorial import tutorial_card_text, tutorial_pump, tutorial_target_cells
from ...core.origin_course import COURSE_TEMPLATE_VERSION

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
from ..styles import MAP_ZOOM_LEVELS

# ---------------------------------------------------------------------------
# FX 写回节流（2026-09-21，性能 P0）
# ---------------------------------------------------------------------------
# 探针（scripts/perf_probe.py，120×40 / 层 24 / 空闲）实测：单帧纯计算
# （快照 + 叠加层 + 落色）只有 0.41ms，是 20fps 预算的 **0.8%**；而哪怕只是把
# **没有任何光照的纯基帧**写回地图 widget，就要吃掉 32% 单核——成本的大头根本
# 不在特效计算，在 Textual 的合成/重绘路径。所以优化方向是**少写回**，不是少算：
# 计算照旧 20fps 跑（动画连续性不受影响），只把真正的 `map_view.update` 限到
# FX_WRITEBACK_HZ 次/秒，再叠加「内容没变就完全不写」的去重。
# ⚠️ 下面的百分比请用 scripts/perf_compare.py 重新测（每用例单独进程）；
# 早期「38.0% → 15.6%」是同一进程里连跑多个 App 测出来的，系统性偏低不可信。
# ⚠️ low 档本来就有 10fps 跳帧，这里对它同样生效（两者相乘不会更慢，因为
# 跳帧时压根没走到 _fx_paint）。
FX_WRITEBACK_HZ = 10.0
FX_WRITEBACK_INTERVAL = 1.0 / FX_WRITEBACK_HZ
# 装饰帧（ui/deco.py 的牌匾流光 / 边框追逐）的时间量化频率（2026-09-21 P0+）。
# 🔴 与地图 FX 同一个道理：每写一次 `styles.border_*`，Textual 就要做一次
# **全屏合成**（实测每次 ≈14ms ≈1.4 个百分点，跟改动多少个 widget 无关）。
# 装饰帧 10fps 里有一半的更新落在同一个量化台阶上——流光 12 档/秒、48 档一圈，
# 5Hz 下每次推进 2.4 档（一圈 4 秒 → 每帧走一圈的 5%），肉眼仍是连续的 chase。
# 实测这一项就值约 3.5 个百分点（见 perf_compare 的 nodeco 与 now 之差）。
DECO_FRAME_HZ = 5.0


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
def _sentence_fragments(compiled) -> tuple[tuple[str, str], ...]:
    """CompiledBoard → 横幅着色片段：句子 fragments 顺次拼接（换行为灰）。"""
    fragments: list[tuple[str, str]] = []
    for index, sentence in enumerate(compiled.sentences):
        if index:
            fragments.append(('\n', 'filler'))
        fragments.extend(sentence.fragments or ((sentence.text, 'filler'),))
    return tuple(fragments)

from .board_editor import BoardEditorMixin
from .css import AppCssMixin
from .footer import I18nFooter  # noqa: F401  兼容旧路径 re-export
from .navigation import NavigationMixin
from .navigation import new_run_seed  # create_session 引用（模块级名字必须在定义模块可见）
from .panels import PanelsMixin
from .session import SessionMixin
from ..tamper_world import TamperWorldUIMixin
from ..self_audit import SelfAuditMixin

from ..layer_observation import LayerObservationMixin
from ..live_map import LiveMapMixin
from ..signal_status import SignalStatusMixin
from ..panel_shortcuts import PanelShortcutsMixin
from ..terrain_preview import TerrainPreviewMixin

def _to_viewport_styles(styles, viewport) -> dict:
    """把世界坐标的样式表转换成视口坐标，丢弃视口外格。

    2026-10-22：角色地图意图高亮曾直接把世界坐标塞进 compose_fx 的视口
    ranges，导致相机平移后高亮落到相邻格/玩家身上；这里统一换算。
    """
    left, top, width, height = viewport
    out = {}
    for (wx, wy), style in (styles or {}).items():
        vx, vy = wx - left, wy - top
        if 0 <= vx < width and 0 <= vy < height:
            out[(vx, vy)] = style
    return out


def _sound_visual_world_cells(pulse) -> tuple[tuple[int, int], ...]:
    """声波可视化输入：玩家自身动作、无 cells 的旧脉冲都不画。"""
    if not pulse or pulse.get("by_player"):
        return ()
    return tuple(pulse.get("cells") or ())


def _sound_visual_view_cells(cells, visible, left: int, top: int,
                             width: int, height: int) -> tuple[tuple[int, int], ...]:
    """把声波世界格过滤成「当前视野外、且在视口内」的视口格。

    2026-10-22 玩家要求：视野内所有格子不渲染声音特效；只让视野外听到
    声波的格显示当前蓝色静态标记。
    """
    out = []
    for wx, wy in cells:
        if (wx, wy) in visible:
            continue
        vx, vy = wx - left, wy - top
        if 0 <= vx < width and 0 <= vy < height:
            out.append((vx, vy))
    return tuple(out)


def _sound_visual_fog_styles(waves, styles) -> dict[tuple[int, int], str]:
    """声波格的显式底色（图像后端单独消费）。

    声波按规则只落在视野外，而图像后端的常规叠加层要求格子可见；混在
    ``backgrounds`` 里会被整片丢掉。这里按波次格拆出一份可压过迷雾的底色。
    """
    cells = {cell for wave in waves for cell in wave.cells}
    return {pos: styles[pos] for pos in cells if pos in styles}


from ..sidebar_workspaces import SidebarWorkspacesMixin
from ..sidebar_management import SidebarManagementMixin


class DreamApp(SidebarManagementMixin, SidebarWorkspacesMixin, TerrainPreviewMixin, PanelShortcutsMixin, SignalStatusMixin, LiveMapMixin, LayerObservationMixin, NavigationMixin, BoardEditorMixin, PanelsMixin, SessionMixin, AppCssMixin, QoLUIMixin, GraphicsMixin, PanelViewMixin, InputMixin, DebugPanelMixin, SelfAuditMixin, TamperWorldUIMixin, TamperUIMixin, App[None]):
    """主类：mixin 组合（拆分见 docs/megafile-refactor-plan.md）。"""

    # 主页光标的两轴地图（行 × 列），id 与 compose() 里的控件一一对应：
    # 行 0..2 = 三个存档槽（列 0 = 存档槽本体、列 1 = 删除），
    # 行 3 = 图鉴 / 设置 / 退出 三个横排选项。
    # ←→ 在行内选左右项、↑↓ 在两段之间换行，行 3 与存档槽行首尾相接（↓ 从槽 3 到
    # 图鉴、↑ 从图鉴回到槽 3），所以任何位置左右上下都有反应。
    HOME_ROWS: tuple[tuple[str, ...], ...] = (
        ("slot-1", "delete-1"),
        ("slot-2", "delete-2"),
        ("slot-3", "delete-3"),
        ("home-catalog", "home-history", "home-settings", "home-exit"),
        # 2026-09-18：测试模式入口（单行单列）——独立 test 存档，游戏内 L 键开调试面板。
        ("test-mode",),
    )
    HOME_NAV_ROW = 3
    # 测试模式行：存档永远只从这条入口进出 save-test/，不占普通存档目录。
    HOME_TEST_ROW = 4
    # 主菜单（2026-09-23 主页改版）：主页不再直接摆存档槽，改为竖排菜单——
    # 「入梦」进入原存档槽选择/删除页（home_view="saves"），测试模式垫底。
    # HOME_ROWS 保留为存档槽页的光标模型（槽行 × 槽/删除 两列）。
    HOME_MENU_ITEMS: tuple[str, ...] = (
        "home-enter", "home-catalog", "home-history", "home-settings",
        "home-exit", "test-mode",
    )
    # 底栏键位（2026-10-23 用户定稿）：I18nFooter 只把常用键排到第一行——
    # Esc / Enter / C / N / B / . / G / F / X，其余键按这里的声明顺序往下排。
    # 声明顺序仍决定展开后非常用键的先后。
    BINDINGS = [
        # （历史：2026-09-18 曾用 Shift+Esc——Windows 终端不上报，已废弃。）
        # 历史 Ctrl+Q 已迁移至 Alt+Q；当前不登记 Ctrl+Q 别名。Esc 用于取消／关闭。
        # 🔴 用户规定（2026-10-15）：退出主键位 = F10（底栏据此显示）；修饰键
        # 一律用 Alt——终端收不到 Ctrl。Alt+Q 为隐藏别名（原 Ctrl+Q 迁移）。
        Binding("f10", "save_exit", tr("保存并退出"), key_display="F10"),
    Binding("f2", "image_preview", tr("地图显示"), key_display="F2", show=False),
    Binding("f3", "cycle_map_observe", tr("分层观察"), key_display="F3"),
        Binding("alt+q", "save_exit", tr("保存退出"), show=False),
        # Esc：返回/菜单双语义（2026-09-20）。有面板/瞄准/寻路/观察等「可取消
        # 状态」时 = 逐层返回（action_cancel_ui 的取消链）；全部干净且角色静止
        # 时 = 打开全屏暂停菜单。底栏显示在 F10 右侧。
        Binding("escape", "cancel_ui", tr("返回/菜单"), key_display="Esc"),
        # Enter = 行动。key_display 显式写成 "Enter"：Textual 默认会把它美化成
        # ⏎ 符号，而那个字形在 Windows 控制台字体里常常只剩一个看不清的小框——
        # 看起来像「底栏里没有 Enter」，所以这里用明文键名。
        Binding("enter", "act_action", tr("行动"), key_display="Enter"),
        # 观察模式：把「可操作对象」从自己换成一枚白色 ?（见 InputMixin.toggle_observe）。
        Binding("x", "observe_mode", tr("观察"), key_display="X"),
        Binding("n", "descend_action", tr("下潜"), key_display="N"),
        Binding("b", "backtrack_action", tr("上浮"), key_display="B"),
        Binding("q", "context_q", tr("返回/投掷"), show=False, priority=True),
        Binding(".", "wait_turn", tr("等待")),
        Binding("g", "pickup_action", tr("捡起")),
        Binding("f", "aim_fire", tr("发射")),
        Binding("r", "reload_weapon", tr("换弹"), show=False),
        # 面板光标锁定：锁定后 wasd/方向键/小键盘只移动面板光标（键盘滚动
        # 事件记录等），~ 或 Esc 或点击地图解锁。底栏可点击进入。
        # 键位只登记「~」一条：物理键 ` 与 ~（含 Shift）在 InputMixin.on_key
        # 里归一成同一个键（终端把裸 ` 报成 grave_accent、Shift+` 报成 tilde，
        # 只绑一个键名会让另一个键毫无反应），底栏点击仍走这个 action。
        Binding("~", "toggle_cursor_lock", tr("锁定"), key_display="~"),
        # 光标区域切换（2026-10-12）：/ 在「地图 → 右侧面板 →（浮层）」之间
        # 强制切换键盘焦点；焦点在面板时方向键/WASD 都只动面板（解锁态也能
        # 用 ←→ 切页）。原「/ 开操作面板」让位给 ? 与 h（语义不变）。
        Binding("slash", "cycle_cursor_zone", tr("区域"), key_display="/"),
        # 目标辅助：非瞄准态开关悬停寻路辅助；瞄准态自动瞄准最近异像。
        Binding("o", "assist_action", tr("辅助"), key_display="O"),
    ]

    def _zoom_map(self, delta: int) -> None:
        """Ctrl+↑/↓ 或 Ctrl+滚轮：放大 / 缩小地图视野比例（档位有限）。

        [SFX挂点] 可选：极轻的相位音；高频操作易吵，也可以不挂。
        每格恒定渲染一个符号（2×1 终端列），缩放改变的是可见格数：
        delta>0 放大（可见格数变少），delta<0 缩小（可见格数变多，
        0.5 为单列主题图标的紧凑概览档，并受地图实际尺寸钳制）。只缩放地图，
        状态栏与右侧面板不受影响；缩放不移动玩家、不推进时间。
        """
        if self.home_mode:
            return
        map_view = self.query_one("#map", MapView)
        levels = list(MAP_ZOOM_LEVELS)
        try:
            index = levels.index(map_view.zoom)
        except ValueError:
            index = levels.index(1.0) if 1.0 in levels else 0
        new_index = max(0, min(len(levels) - 1, index + delta))
        if new_index == index:
            return
        map_view.zoom = levels[new_index]
        map_view._frame_key = None  # 缩放后强制重建渲染缓存
        self.refresh_view()

    def refresh_view(self) -> None:
        self._sidebar_before_refresh()
        if self.panel_mode == 'inventory' and self.panel_selection not in self._inventory_visible_indices():
            self._qol_reselect_inventory(focus=False, reset_scroll=False)
        self._refresh_view_contents()
        self._refresh_qol()
        if self.layer_observation is None:
            self.query_one('#panel-help').update(tr('完整键位表 · 点击 / Alt+H'))
        self._sync_layer_observation_ui()
        self._map_startup_notice()
        if not self.home_mode:
            self._refresh_signal_status()
            self._refresh_self_audit(self.session.state)
        elif self._inspection_active():
            self.close_signal_detail()
            self._close_self_audit(refresh=False)
        self._sidebar_after_refresh()

    def _refresh_view_contents(self) -> None:
        self._sync_music()
        if self._floor_transition is not None:
            return  # 演出期间冻结常规刷新：新层由动画一格一格露出（设计文档 §2.3）
        self._expire_attack_confirmation(refresh=False)
        # 每次刷新都同步语言：设置页切换语言后无需重启即全局生效。
        previous_language = get_language()
        set_language(str(self.config.get("language")))
        if previous_language != get_language() and self.is_running:
            self.refresh_bindings()  # 底栏键位描述随语言重排（见 I18nFooter）
        state = self.session.state
        if self.sentence_aim is not None and self.sentence_aim['context'] != self._equipment_choice_context():
            self._cancel_sentence_aim()
        if state.depth != self._hover_depth:
            # 换层后旧层的鼠标悬停/固定目标/上下文菜单坐标可能越界
            # （长廊层比常规层窄一半），残留坐标会让 state.cell 抛 IndexError
            # 打断刷新——正是「下潜后界面卡死」的根源，全部作废。
            self._hover_depth = state.depth
            self.hover_cell = None
            self.pinned_target = None
            self.context_menu_target = None
            self.pickup_goal = None
            self.shortcut_targets.clear()
            self.assist_path = []
            state.hover_target = None
            # 观察光标同理：层换了，? 的坐标未必还在新地图里，直接收回观察。
            self.observe_mode = False
            self.observe_cursor = None
            # 格子详情的目标格同样随层作废，避免读到下一层同坐标的格子。
            self.close_cell_detail()
            # 进行中的对话同理：NPC/复合事件都不在本层了，残留的 pending id
            # 只会让悬浮面板显示「对话已经结束」。直接收起。
            state.pending_npc_id = None
            state.pending_event_id = None
            state.pending_event_uid = None
        writer = self.query_one('#equipment-sentence', SentenceWriter)
        if getattr(self, '_equipment_sentence_state', id(state)) != id(state):
            writer.clear()
            self.query_one('#board-editor-sentence', SentenceWriter).clear()
        self._equipment_sentence_state = id(state)
        if self.panel_mode == 'equipment' and (not writer.full_text or writer.language != get_language()):
            compiled = state.equipment.compiled()
            writer.write(compiled.text, animate=False, force=True,
                         fragments=_sentence_fragments(compiled))
        show_sentence = (self.panel_mode == 'equipment' and not self.home_mode
                         and self.board_editor is None and bool(writer.full_text))
        if not show_sentence:
            writer.finish()
        writer.display = show_sentence
        mode = self._symbol_mode()
        # 洞察已满又获得新洞察（state.pending_insight 被置上）时，自动弹出左侧
        # 替换面板——不必玩家去翻面板找提示。面板关闭（放弃/替换）后 pending 清空，
        # 下次刷新不再打开。
        if state.pending_insight and self.insight_replace_target is None and not self.home_mode:
            self.open_insight_replace(state.pending_insight)
        elif not state.pending_insight and self.insight_replace_confirm_discard:
            self.insight_replace_confirm_discard = False
        # 记忆碎片槽满又拾到新碎片（state.pending_memory 被置上）时同理自动弹出。
        # 两个面板不会同时开：open_memory_replace 会先把洞察面板收掉，反之亦然。
        if state.pending_memory and self.memory_replace_target is None and not self.home_mode:
            self.open_memory_replace(state.pending_memory)
        elif not state.pending_memory and self.memory_replace_confirm_discard:
            self.memory_replace_confirm_discard = False
        configured_show_details = bool(self.config.get("show_details"))
        if configured_show_details != self._configured_show_details:
            self._configured_show_details = configured_show_details
            self.details_expanded = configured_show_details
        map_view = self.query_one("#map", MapView)
        map_view.symbol_mode = mode
        map_view.observe_cursor = (self.sentence_aim['cursor'] if self.sentence_aim is not None
                                   else getattr(self, '_aim_free_cursor', None) if self.aiming
                                   else self.observe_cursor if self.observe_mode else None)
        tamper = self._active_tamper_editor()
        if tamper is not None and tamper.map_preview:
            map_view.observe_cursor = tamper.preview_cursor
        if self.layer_observation is not None:
            map_view.observe_cursor = self.layer_observation.cursor
        # 目标辅助路径同步（渲染黄底高亮）。
        if (self.target_assist or self.aiming) and self.assist_path:
            map_view.assist_cells = set(self.assist_path)
        elif map_view.assist_cells:
            map_view.assist_cells = None
        self._sync_tutorial_highlight(map_view, state)
        map_view.animated_combat = self.config.get("fx_quality") != "off"
        map_view.update_state(state)
        # 基帧刚重画：立刻补回 FX 叠加层，避免先闪一帧没有光照/没有液气底色的
        # 纯基准帧（"每回合闪一下"，见 _fx_repaint 的说明）。
        self._fx_repaint(map_view, state)
        # 调试面板（测试模式 L 键）：开时显示并刷新两列内容，关时隐藏。
        debug_panel = self.query_one("#debug-panel")
        if self.debug_panel_open and not self.home_mode:
            debug_panel.styles.display = "block"
            self._refresh_debug_panel()
        elif debug_panel.styles.display != "none":
            debug_panel.styles.display = "none"
        overlay = self.query_one("#map-overlay", MapOverlayPanel)
        self._fit_map_overlay()
        if state.run_over and state.ending_id and not self.home_mode:
            # 结局演出：交给 SettlementScreen 分镜（feed 每局一次），overlay 不再占用。
            try:
                settlement = self.query_one("#settlement", SettlementScreen)
            except Exception:
                settlement = None
            if settlement is not None and not settlement.active:
                settlement.feed(state)
            elif settlement is None:
                overlay.update(self._ending_text(state))
                overlay.styles.display = "block"
            self.ending_shown = True
        elif self.ending_shown:
            self.ending_shown = False
        if self.equipment_choice is not None and not self.home_mode:
            overlay.update(self._equipment_choice_text(state))
            overlay.styles.display = 'block'
        elif self.insight_replace_target is not None and not self.home_mode:
            # 洞察已满：获取新洞察时弹出的左侧「替换 / 放弃」面板。
            overlay.update(self._insight_replace_text(state))
            overlay.styles.display = "block"
        elif self.memory_replace_target is not None and not self.home_mode:
            # 碎片槽已满：拾到新记忆碎片时弹出的左侧「替换 / 放弃」面板。
            overlay.update(self._memory_replace_text(state))
            overlay.styles.display = "block"
        elif self.panel_mode == "event_dialog" and not self.home_mode:
            # NPC 对话 / 复合事件：左侧地图上方的悬浮对话面板（2026-09-18
            # 从右侧面板迁来——对话贴着发生地点，视线不用来回跳）。
            overlay.update(self._event_dialog_text(state))
            overlay.styles.display = "block"
        elif self.item_menu_target is not None and not self.home_mode:
            # 右键物品（或选中后按 '）时才弹出的左侧物品菜单。
            overlay.update(self._item_menu_text(state))
            overlay.styles.display = "block"
        elif self.anomaly_detail_target is not None and not self.home_mode:
            # 右键观测面板里的意象名时弹出的左侧详情面板。
            overlay.update(self._anomaly_detail_text(state))
            overlay.styles.display = "block"
        elif self.cell_detail_target is not None and not self.home_mode:
            # 右键地图格子（或观察模式按 '）时弹出的左侧格子详情面板。
            overlay.update(self._cd_text(state))
            overlay.styles.display = "block"
        elif self.pickup_target is not None and not self.home_mode:
            # 本格有多件可拾取显化物时（左键/G）弹出的左键勾选面板。
            overlay.update(self._pickup_text(state))
            overlay.styles.display = "block"
        elif getattr(self, "container_index", None) is not None and not self.home_mode:
            # 容器浮层（左侧）：盛装/倒出——行囊面板保持不动，收起后留在行囊。
            overlay.update(self._container_overlay_text(state))
            overlay.styles.display = "block"
        elif getattr(self, "spray_select", None) is not None and not self.home_mode:
            # 喷射弹药选择浮层：列出非空对应容器，一次只喷一种。
            overlay.update(self._spray_select_text(state))
            overlay.styles.display = "block"
        elif getattr(self, "mirror_index", None) is not None and not self.home_mode:
            # 洞察之镜三选一浮层。
            overlay.update(self._mirror_select_text(state))
            overlay.styles.display = "block"
        elif self.lens_offer_scene and not self.home_mode:
            # §8 S23 青灯祭品选择浮层：勾选三件易逝物／摄入物喂给门。
            overlay.update(self._lens_offer_text(state))
            overlay.styles.display = "block"
        elif overlay.styles.display != "none":
            overlay.update(Text())
            overlay.styles.display = "none"
        # 篡改旁侧面板跟着对话一起刷新（规格 §4.4）：对话收起、目标失效、换层
        # 与死亡都在这里被发现并顺手收面板——刷新即校验，不留悬空草稿。
        self._refresh_tamper_overlay()
        if self._active_tamper_editor() is not None:
            self.call_after_refresh(self._refresh_tamper_overlay)
        self._refresh_nav_buttons(mode)
        if self.home_mode:
            self._close_self_audit(refresh=False)
            self._refresh_home_view(state, mode)
            return
        # 全屏暂停菜单 / 它打开的设置页：#layout 已隐藏，只刷新各自的覆盖层，
        # 不走世界视图（地图/面板不可见，省掉整块重建）。
        if self.panel_mode == "pause":
            self._refresh_pause_view(mode)
            return
        if self.panel_mode == "pause_settings":
            self._refresh_settings_rows(mode)
            return
        if self.panel_mode == "pause_codex":
            # 游戏内图鉴覆盖层：#layout 已隐藏，只刷图鉴组件（2026-10-14）。
            self._refresh_codex_components(mode)
            return
        if self.panel_mode == "board_editor":
            # 联想盘编辑器：#layout 已隐藏，只刷新覆盖层（世界视图整块跳过）。
            self._refresh_board_editor(mode)
            return
        # 兜底：主页专属的 panel_mode 绝不能带进游戏（见 _sync_home_cursor 的注释）。
        # 万一有哪条路径漏了守卫，这里也会把面板拉回事件记录，右侧不会残留
        # 「存档槽/开始新游戏」文案，按键路由也不会被卡在面板分支。
        if self.panel_mode in HOME_PANEL_MODES:
            self.panel_mode = "world"
            self.panel_selection = 0
            self.panel_scroll = 0
        self._refresh_world_view(state)
        self.query_one('#panel-help').update(tr('完整键位表 · 点击 / Alt+H'))
        self.query_one('#panel-help').display = self.sidebar_workspace == 'actions'

    def _apply_region_theme(self, depth: int, realm_id: str = "") -> None:
        """按所在区域换肤：**面板底色**、地图边框线型/颜色、顶栏底色与前景色、状态栏前景色。

        区域不变时直接返回，避免每帧重写样式。主页不显示 Header，也不换肤。

        梦中梦（realm_id 非空）使用专属边框刻纹与配色，现有面板底色及其他
        样式保持主题规则（见 region_themes.theme_for_realm）——realm 变体是缓存过的
        同一对象，「区域不变就返回」的同一性判断对它照常生效。

        2026-09-21 三改（玩家定稿）：地图底色**不再随区域变**，统一 `MAP_BG`（黑）；
        「区域识别」改由**面板底色**（`theme.panel_bg`）+ 顶栏 + 边框共同承担。
        原因是地图上色有两个实战问题：①屏幕底色一变，玩家对「自己在哪一格」的
        距离感会跟着飘，移动时容易觉得错位；②地形/墙体本身也吃到底色对比变化，
        反而更难辨认。
        """
        theme = theme_for_realm(realm_id, depth)
        if getattr(self, "_applied_theme", None) is theme:
            return
        self._applied_theme = theme
        # 地图底色（2026-09-21）：**全区域黑**，写**两处**（缺一不可，玩家实测过
        # 「只写 Screen 时地图边框那一圈留着旧底色」）：
        #   ① Screen.background —— 终端里最底层的那一层，铺满整屏（含顶栏/底栏
        #      之间的缝隙），也是「什么显式底色都没画的格子」最终透出的颜色。
        #   ② `#map-pane` 自己的 background —— 地图面板那一圈（边框 + padding）。
        #      只靠 ① 时那一圈是**间接**取色（面板透明 → 透出 Screen 底），
        #      换区时未必跟着面板一起重绘；面板自己有底色，那一圈就归面板负责。
        # 地形/液体/气体/光照/火焰各自带显式底色，会照常盖住它，所以它在图层最
        # 底部、不会影响任何上层颜色。
        # ⚠️ 离开游戏回主页时必须复位（见 _return_home），否则主页会带着上一次
        # 的值——主页不属于任何区域。
        self.screen.styles.background = MAP_BG
        map_pane = self.query_one("#map-pane")
        map_pane.styles.background = MAP_BG
        map_pane.styles.border = (theme.border_style, theme.border_color)
        # 不设 border_title——标题会嵌进上边框、把边框线断开；
        # 保持边框完整闭合，区域名只在侧栏状态行显示。
        side_pane = self.query_one("#side-pane")
        side_pane.styles.border = (theme.border_style, theme.border_color)
        quality = str(self.config.get('fx_quality') or 'off')
        for pane in (map_pane, side_pane):
            pane.paint_ornament(depth, quality, 0.0, self._symbol_mode() != 'ascii', realm_id=realm_id)
        # 面板底色随区域换（2026-09-21 三改）：右侧状态面板 / 左侧浮层 / 消息气泡
        # 三处**一起**改成当地区域的面板色——它们是同一个「框」，颜色必须同步，
        # 否则浮层与右栏会分家（tests/test_panel_backgrounds.py 盯着这条）。
        # 🔴 2026-10-18：选择器里**只能有气泡本体，不能有容器 #map-hints**。
        # 容器只是布局载体（宽度固定 42 列、贴右对齐，见 floating_toast.MapHints），
        # 给它上色等于把整条 42 列宽的底色块画到地图上，遮挡范围远超文字——
        # 玩家反馈的「气泡提示背景遮挡范围远超文字边框区域」就是这一条。
        # 背景由子件 MapHintText（#map-mode-hint）按「文本 + padding」自己画，
        # 容器保持 DEFAULT_CSS 的 transparent（2026-10-11 的收缩修复）。
        side_pane.styles.background = theme.panel_bg
        for selector in ("#map-overlay", "#tamper-overlay", "#toast", "#map-mode-hint"):
            try:
                self.query_one(selector).styles.background = theme.panel_bg
            except Exception:  # pragma: no cover - 极早期挂载中可能还没就位
                pass
        header = self.query_one(DreamHeader)
        header.styles.background = theme.header_bg
        header.styles.color = theme.header_fg
        self.query_one("#status", Static).styles.color = theme.status_fg

    def _refresh_world_view(self, state: GameState) -> None:
        self._sync_home_scene()
        """游戏内界面：只更新可见的世界组件（状态栏/悬停/事件面板），跳过主页的图鉴与设置。"""
        self._apply_region_theme(state.depth, state.realm_id)
        # 层型标签：修饰符在本层地形类型之前（如「潮湿·洞穴」；常规层只显示层型）。
        if state.layer_modifier:
            form_label = f"{tr(state.layer_modifier)}·{tr(state.map_form)}"
        else:
            form_label = tr(state.map_form)
        region = region_for_depth(state.depth)
        label_width = max(6, *(glyphs.cell_len(tr(key)) for key in ("心智", "清醒度", "想象力")))
        value_width = max(len(f"{maximum}/{maximum}") for maximum in
                          (state.max_mind, state.max_lucidity, state.max_imagination))
        suffix_width = max(glyphs.cell_len("  " + tr(STATUS_TIERS[tier]))
                           for tier in (state.mind_tier, state.lucidity_tier))
        available = self.query_one("#status", Static).content_size.width or 44
        bar_layout = dict(label_width=label_width, value_width=value_width,
                          width=max(3, min(20, available - label_width - value_width - suffix_width - 2)))
        status = Text.assemble(
            (("⚙ " + tr("测试模式") + "  ", "bold #3ddad0") if self.test_mode else ""),
            (f"{tr(region)} {state.depth}  ", "bold white"),
            # 层主题·层型。⚠️ 原来是 `italic bright_magenta`——命名色被 Textual 的
            # 主题调色板解析成偏暗的值（bright_magenta → #f4005f），在浅层梦境那块
            # 最亮的面板上只有 3.30，等于糊掉。改成显式 hex（6.51）。
            (f"{tr(state.theme)}·{form_label}\n", LAYER_LABEL_STYLE),
            self._bar(tr("心智"), state.mind, state.max_mind, BAR_MIND_STYLES, suffix=f"  {tr(STATUS_TIERS[state.mind_tier])}", **bar_layout),
            "\n",
            self._bar(tr("清醒度"), state.lucidity, state.max_lucidity, BAR_LUCIDITY_STYLES, suffix=f"  {tr(STATUS_TIERS[state.lucidity_tier])}", **bar_layout),
            "\n",
            self._bar(tr("想象力"), state.imagination, state.max_imagination, BAR_IMAGINATION_STYLES, **bar_layout),
            "\n",
            # 深层边界：崩解度隐藏（静默累计，仅作结局判定），只显示回合数。
            # 梦的起始（0 层）：没有崩解度——开局即可下潜。
            ((tr("深层边界") + f" ·  {tr('回合数')} {state.time}\n", "bold #3ddad0") if state.depth >= 28 else
             ((tr("可下潜") + f" ✦  {tr('回合数')} {state.time}\n", "bold bright_green") if (state.dissolution >= 100 or state.depth <= 0) else
              (f"{tr('崩解度')} {state.dissolution}/100  {tr('回合数')} {state.time}\n", "white"))),
        )
        status_lines = status.split('\n')
        # Core status is exactly five rows; nearby details belong to context.
        status_lines = status_lines[:5]
        for line in status_lines:
            line.truncate(available, overflow='ellipsis')
        status = Text('\n').join(status_lines)
        self.query_one("#status", Static).update(status)
        hover_widget = self.query_one("#hover-info", Static)
        # 按悬停区实际显示宽度折行；布局未就绪（宽度 0）时退回侧栏最小宽度
        hover_width = hover_widget.content_size.width or 44
        hover_widget.update(self._sidebar_context_text(state, hover_width))
        self._refresh_sidebar_tools()
        # §15.6 操作预览必须排在悬浮读数之后：`_hover_text` 顺手写下
        # state.hover_target，而预览中心正是 `visible_target(state)`——早一步就
        # 差一帧（鼠标刚移开，图上还留着上一格的黄圈）。只重叠交互层，基帧不动。
        self._apply_terrain_preview(state, self.query_one("#map", MapView))
        # Inspectors refresh after all layout modes, including the board editor.
        self._refresh_map_hints()
        self.query_one("#panel", Static).update(self._panel_text(state))

    def action_focus_next(self) -> None:
        """Tab 在 Textual 里是 Screen 绑定，进不了 on_key；补收临时气泡。"""
        self._dismiss_transient()
        self.screen.focus_next()

    def action_focus_previous(self) -> None:
        self._dismiss_transient()
        self.screen.focus_previous()

    def show_toast(self, message: str, anchor_screen_y: int | None = None) -> None:
        """所有临时反馈进入地图右上角提示栈，3 秒后消失。

        保留旧 anchor_screen_y 参数兼容调用方，布局不再跟随触发行。
        顺带刷一次模式提示（2026-10-11）：发射/投掷等动作在「瞄准中」
        状态下完成时，aiming 已复位但提示只有 refresh_view/悬停才重绘——
        玩家会看到弹已打完、气泡却还挂着「瞄准中」。
        """
        try:
            toast = self.query_one("#toast", FloatingToast)
        except Exception:
            return
        if anchor_screen_y is None:
            anchor_screen_y = self._player_row_screen_y()
        toast.show(message, int(anchor_screen_y))
        try:
            self._refresh_map_hints()
        except Exception:
            pass

    def _selected_panel_row_screen_y(self) -> int | None:
        """右侧面板当前选中条目所在的屏幕行；取不到（滚动出视窗等）返回 None。

        「条目序号 → 可视行」的口径随面板而异：行囊/洞察/操作界面在
        _panel_rows 里直接存条目序号；携带意象页存**真实行囊下标**而
        panel_selection 是过滤后的序号，要按可见条目出现顺序换算。
        """
        rows = self._panel_rows
        entry_rows = [index for index, value in enumerate(rows) if value >= 0]
        visible_row: int | None = None
        if self.panel_mode == "equipment":
            if 0 <= self.panel_selection < len(entry_rows):
                visible_row = entry_rows[self.panel_selection]
        elif rows and 0 <= self.panel_selection < self._panel_item_count():
            try:
                visible_row = rows.index(self.panel_selection)
            except ValueError:
                visible_row = None
        if visible_row is None:
            return None
        try:
            panel = self.query_one("#panel")
        except Exception:
            return None
        # #panel 无边框无内边距：可视行 1:1 对应屏幕行。
        return int(panel.region.y) + visible_row

    def _player_row_screen_y(self) -> int:
        """玩家所在地图格的屏幕行（MapView 无边框无内边距，1 格 = cell_h 行）。"""
        try:
            map_view = self.query_one("#map", MapView)
            state = self.session.state
        except Exception:
            return 6
        left, top, _width, height = map_view.viewport
        cell_h = max(1, int(getattr(map_view, "cell_h", 1)))
        row = (state.player.y - top) * cell_h + max(0, (cell_h - 1) // 2)
        row = min(max(0, row), max(0, height * cell_h - 1))
        return int(map_view.region.y) + row

    def _player_in_map_top_right(self) -> bool:
        """玩家是否落在地图子窗口右上 1/4（x 过中线且 y 未过中线）。

        气泡避让判定（2026-10-11）：命中时地图气泡从右上角换到右下角，
        免得盖住玩家自己的格子。坐标换算与 _player_row_screen_y 同口径
        （MapView 无边框无内边距，1 格 = cell_w 列 × cell_h 行，格中心
        取半格偏移）；中线按**视口内容尺寸**（可见格数 × 格尺寸）算——
        MapView widget 可能比地图内容高/宽（布局富余），按 widget 算会
        把右下角误判进上半。取不到地图/状态（主页、切层间隙）返回 False。
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
        return (px > map_view.region.x + (width * cell_w) // 2
                and py < map_view.region.y + (height * cell_h) // 2)

    def _push_header_ticker(self, message: str) -> None:
        """事件记录在顶部标题位播报；地图气泡保留独立的操作反馈。"""
        if self.home_mode:
            return
        try:
            self.query_one('#header-ticker', HeaderTicker).push(message, self)
        except Exception:
            pass

    def _refresh_birth_layout(self) -> None:
        if not self.is_running:
            return
        self.query_one('#newgame-body').set_class(self.size.width < 100, 'compact')

    def _fit_map_overlay(self) -> None:
        """左侧浮层尺寸自适应（2026-10-11）：上限钳到地图面板内容尺寸。

        CSS 侧 width/height 已是 auto（按内容收缩）；这里只把 max 钳到
        #map-pane 的内容区——字多的面板自动拉长，但浮层整体（含边框与
        padding）不超过地图长宽，再长交给 overflow-y 滚动。
        值未变化时不写回（少写回纪律）。
        """
        try:
            overlay = self.query_one("#map-overlay", MapOverlayPanel)
            pane = self.query_one("#map-pane")
        except Exception:
            return
        content = pane.content_size
        # 这里限制外框总尺寸；正文还需扣除 round 边框与 padding。
        # 普通浮层保留外部余量；对话与篡改可以用满地图宽度以保留状态和选项。
        max_w = max(1, content.width - 4)
        dialog = self.tamper_editor is not None or self.panel_mode == 'event_dialog'
        overlay.styles.padding = (1, 1) if dialog else (1, 2)
        if dialog:
            max_w = max(1, content.width)
        max_h = max(1, content.height - 2)
        key = (max_w, max_h)
        if getattr(self, "_overlay_fit_key", None) != key:
            self._overlay_fit_key = key
            overlay.styles.max_width = max_w
            overlay.styles.max_height = max_h

    def _refresh_map_hints(self) -> None:
        hint = self.query_one("#map-mode-hint", Static)
        message = ""
        if self.pending_confirmation:
            message = tr("确认攻击？Y / Enter 确认\nN / Esc / Q 取消 · 8 秒后取消\n方向键或点击地图可取消并行动")
        elif self.sentence_aim is not None:
            message = tr('语句瞄准：方向键移动光标 · Enter 施放\n鼠标左键选目标 · O 辅助 · Esc / Q 取消')
        elif self.aiming:
            from ..firing_presentation import aim_hud
            width=min(44,max(12,int(self.query_one('#map-pane').content_size.width*.55)))
            message=aim_hud(self,width)
        elif self.observe_mode:
            message = ("Observe: arrows / click\nEnter: walk · X: return\nLayers F3 · click here" if get_language() == "en"
                       else "观察：方向键 / 点击\nEnter 寻路 · X 返回\n分层观察 F3 · 点击切换")
        elif self.path:
            message = tr("寻路中：剩余 {count} 格（点击或按键可中断）").format(count=len(self.path))
        elif self.target_assist:
            message = tr("寻路辅助已开启（悬停地图显示路径）")
        hint.update(message if isinstance(message,Text) else Text(message, style="bold bright_yellow"))
        hint.styles.display = "block" if message else "none"
        self.query_one("#map-hints", MapHints).place()

    def _dismiss_transient(self) -> None:
        """提前取消地图临时气泡（点击地图/面板、按任意键时调用）。"""
        try:
            self.query_one("#toast", FloatingToast).dismiss()
        except Exception:
            pass

    def _choose_spray_ammo(self, inv_index: int) -> None:
        """选用弹药容器后进入瞄准（与 f 瞄准同一套点选/方向键流程）。"""
        if self.aim_action_choice is not None:
            option = self.aim_action_choice
            plan = self.session.state.equipment.plan_action(option['kind'], choice=option['key'])
            if plan.requires_target:
                self._begin_targeted_equipment_aim(option, inv_index)
                return
        self.spray_source = inv_index
        self.spray_select = None
        self.equipment_choice = None
        self.aiming = True
        self._capture_aim_source()
        self.panel_mode = "actions"
        self.refresh_view()

    def _clear_lens_offer(self) -> None:
        """收起青灯祭品选择浮层（取消/确认/回主页共用）。"""
        self.lens_offer_scene = ""
        self.lens_offer_items = []
        self.lens_offer_selected = set()
        self.lens_offer_cursor = 0

    def _lens_offer_toggle(self, inv_index: int) -> None:
        """勾选/取消一件祭品（键盘空格与左键点行共用）。"""
        if inv_index in self.lens_offer_selected:
            self.lens_offer_selected.discard(inv_index)
        else:
            self.lens_offer_selected.add(inv_index)

    def _confirm_lens_offer(self) -> None:
        """确认祭品：交给 ``GameState.confirm_gate_offering`` 结算，收起浮层。"""
        scene_uid = self.lens_offer_scene
        selected = sorted(int(index) for index in self.lens_offer_selected)
        self._clear_lens_offer()
        if scene_uid:
            self._apply("confirm_gate_offering", scene_uid, selected)

    def resolved_map_display(self):
        """当前设置 + 能力解析后的地图显示模式（docs §13.2）。"""
        from ..map_display import resolve_map_display
        if self._image_restore_fallback:
            return 'character', tr('图像恢复失败，暂用字符地图')
        if self.is_running and self.is_headless:
            return "character", tr("无原生终端输出")
        return resolve_map_display(self.config)

    def action_cycle_map_observe(self) -> None:
        if self._inspection_active():
            return
        """F3 enters temporary observation; subsequent presses cycle its layers."""
        from ...core.map_scene import OBSERVE_LAYERS
        if self.layer_observation is None:
            self._enter_layer_observation()
        else:
            view = self.layer_observation
            self._layer_select(OBSERVE_LAYERS[(OBSERVE_LAYERS.index(view.layer)+1) % len(OBSERVE_LAYERS)])

    def action_elevation_observe(self) -> None:
        if self._inspection_active():
            return
        """Alt+G opens the elevation view; again returns, other views switch."""
        from ...core.map_scene import OBSERVE_LAYERS  # noqa: F401
        if self.layer_observation is None:
            self._enter_layer_observation()
            if self.layer_observation is not None:
                self._layer_select('elevation')
        elif self.layer_observation.layer == 'elevation':
            self._exit_layer_observation()
        else:
            self._layer_select('elevation')

    def action_reload_weapon(self) -> None:
        if self._handled_in_on_key('r'):
            return
        state = self.session.state
        if (self.home_mode or state.run_over or self.observe_mode or self.panel_mode == 'event_dialog'
                or self._modal_menu_open() or self.layer_observation is not None
                or getattr(self, '_floor_transition', None) is not None):
            return
        if getattr(self, 'construct_aim_id', None) is not None or self.sentence_aim is not None:
            # 构想瞄准不使用弹匣；不能穿透到背景里的普通武器。
            return
        from ...core.firing_sources import (
            LEGACY_BASIC_ID, collect_firing_sources, equipment_emitters, legacy_basic_view,
            magazine_spec)
        selected = self.aim_action_choice if self.aiming else None
        weapons = []
        if self.aiming:
            if not isinstance(selected, dict):
                self.show_toast(tr('当前来源无需换弹。'), 3)
                return
            if selected.get('key') == LEGACY_BASIC_ID:
                view = legacy_basic_view(state)
                weapons = [view] if view is not None else []
            elif selected.get('key') == 'aggregate' or selected.get('kind') != 'fire':
                self.show_toast(tr('当前来源无需换弹。'), 3)
                return
            else:
                weapons = [item for item in equipment_emitters(state, 'fire', selected.get('key'))
                           if magazine_spec(item.definition_id) is not None]
        else:
            last_key = getattr(self, '_last_firing_source_key', None)
            choices = [
                dict(key=source.choice_key, source_key=source.key)
                for source in collect_firing_sources(state)
                if ((source.kind == 'equipment' and source.action_kind == 'fire')
                    or source.kind == 'legacy')]
            # The last used source comes first; every physical weapon appears once.
            choices.sort(key=lambda choice: choice['source_key'] != last_key)
            seen = set()
            for choice in choices:
                if choice['key'] == LEGACY_BASIC_ID:
                    view = legacy_basic_view(state)
                    if view is not None and LEGACY_BASIC_ID not in seen:
                        seen.add(LEGACY_BASIC_ID)
                        weapons.append(view)
                    continue
                for item in equipment_emitters(state, 'fire', choice['key']):
                    if (magazine_spec(item.definition_id) is None
                            or item.instance_id in seen):
                        continue
                    seen.add(item.instance_id)
                    weapons.append(item)
        if not weapons:
            self.show_toast(tr('没有可换弹的武器。'), 3)
            return
        if len(weapons) == 1:
            self._perform_reload(weapons[0].instance_id)
            return
        from ..firing_presentation import reload_status
        options = []
        for item in weapons:
            text, blocked = reload_status(state, item)
            options.append(dict(key=item.instance_id, kind='reload',
                                definition_ids=[item.definition_id],
                                quote_status=text, quote_blocked=blocked))
        self.equipment_choice = dict(command='reload_weapon_pick', args=(), options=options,
                                     cursor=0, context=self._equipment_choice_context())
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        self.refresh_view()

    def action_image_preview(self) -> None:
        if self._inspection_active():
            return
        """F2 opens the actual map display setting; no suspended static preview."""
        from ..map_display_screen import MapDisplayScreen
        actual, reason = self.resolved_map_display()
        def selected(value):
            if value is not None:
                self.config.set_value('map_display', value)
                self._image_output_error = ''
                self._image_restore_fallback = False
                self._layer_return_pending = None
                self._schedule_map_geometry_probe()
                self.query_one('#map')._frame_key = None
                self.refresh_view()
        actual_label = tr('图像') if actual == 'image' else tr('字符')
        self.push_screen(MapDisplayScreen(str(self.config.get('map_display') or 'auto'),
                                         tr('当前：')+actual_label+' · '+reason), selected)

    def _fx_tick(self) -> None:
        """FX 特效帧（20fps；low 档 10fps 由跳帧实现）：基帧 + 叠加样式。

        暂停语义（文档 §4.5）：主页/观察模式/终局时不推进时钟、不重绘——
        画面与时间一起静止。quality=off 时画布隐藏，整条路径零成本。
        """
        if self._floor_transition is not None:
            self._fx_last = None
            return  # 演出期间暂停 FX：光照覆盖不与演出帧叠加（含 off 档重绘分支）
        quality = str(self.config.get("fx_quality") or "off")
        # 扫描线独立开关：每帧同步，设置页改动即时生效（一次布尔赋值，零开销）。
        self.fx_engine.scanlines_disabled = not bool(self.config.get("fx_scanlines"))
        if quality == "off" or self.home_mode or self.session.state.run_over:
            self._fx_last = None
            self._clear_projectile()
            # 关闭/离场：若上一帧是特效帧，立即重绘一帧纯净基准帧。
            if getattr(self, "_fx_active", False):
                self._fx_active = False
                # 写回存档一并作废：重开特效时第一帧必须真的画上去，不能拿
                # 关闭前的旧摘要把自己去重掉（否则 reopen 后地图一片死黑）。
                self._fx_frame_digest = None
                self._fx_last_write = None
                self._fx_quick_key = None
                self._fx_ambient_key = None
                try:
                    map_view = self.query_one("#map", MapView)
                    map_view.animated_combat = False
                    map_view._frame_key = None
                    map_view.update_state(self.session.state)
                    # 状态未变时 update_state 会跳过 self.update——这里强制补画纯帧。
                    if map_view.last_base_text is not None:
                        map_view.update_scene(map_view.last_base_text)
                except Exception:
                    pass
            return
        if self.panel_mode != "world" or self.observe_mode:
            self._fx_last = None
            return  # 冻结：不推进时钟，保留上一帧
        state = self.session.state
        now = time.monotonic()
        if self._fx_last is None:
            self._fx_last = now
        self._fx_clock += min(0.25, max(0.0, now - self._fx_last))
        self._fx_last = now
        try:
            map_view = self.query_one("#map", MapView)
        except Exception:
            return
        self._fx_note_events(state, self._fx_clock)
        if self._fx_paint(map_view, state, self._fx_clock):
            self._fx_active = True

    def _clear_projectile(self) -> None:
        self._fx_projectile = None
        self._map_particles.clear()
        self._fx_combat_pulses.clear()
        self._fx_combat_seq = getattr(self.session.state, '_combat_fx_seq', 0)
        raw = self.session.state.last_projectile
        self._fx_projectile_seq = raw.get("seq") if raw else None
        self._fx_last = None

    def _capture_projectile_action(self, *, changed=True, memory_before=None, blasts_before=None, combat_before=None, visual=None) -> None:
        """动作入口同步登记回放，不等下一次定时器。"""
        raw = self.session.state.last_projectile
        if not changed or (raw and self._fx_projectile and raw.get("seq") == self._fx_projectile[0].get("seq")):
            return
        if raw is not None and visual is not None:
            raw = dict(raw,visual=visual)
        self._fx_projectile = None
        if changed:
            self._map_particles.clear()
            self._fx_combat_pulses.clear()
        self._fx_projectile_seq = raw.get("seq") if raw else None
        if not self.is_running:
            return
        state = self.session.state
        layer = (state.depth, state.realm_id, state.realm_depth)
        if layer == self._particle_layer:
            if memory_before is not None:
                if isinstance(memory_before, int):
                    self._fx_memory_count = memory_before
                else:
                    self._fx_memory_ids = set(memory_before)
                    self._fx_memory_count = len(memory_before)
            if blasts_before is not None:
                self._fx_blast_count = blasts_before
            if combat_before is not None:
                self._fx_combat_seq = combat_before
        self._fx_note_events(state, self._fx_clock)
        if (raw is not None and not self.home_mode and not self.session.state.run_over
                and self._floor_transition is None and self.config.get("fx_quality") != "off"):
            self._fx_projectile = (raw, self._fx_clock)
            self._schedule_bounce_particles(raw, self._fx_clock)
            self._fx_last = time.monotonic()
            self._fx_active = self._fx_paint(self.query_one("#map", MapView), self.session.state,
                                            self._fx_clock, force=True)
        elif (self._fx_active or self._map_particles.pending or self._fx_combat_pulses) and not self.home_mode and not self.session.state.run_over:
            if self.config.get("fx_quality") == "off":
                self._fx_tick()
            else:
                self._fx_last = time.monotonic()
                self._fx_active = self._fx_paint(self.query_one("#map", MapView), self.session.state, self._fx_clock, force=True)

    def _schedule_bounce_particles(self, raw, born):
        if self.config.get('fx_quality') == 'off':
            return
        count = len(raw.get('cells', ()))
        flight = projectile_flight_time(raw.get('kind', 'shot'), count)
        offsets = (0.,projectile_repeat_delay(raw)) if projectile_repeat_delay(raw) else (0.,)
        for offset in offsets:
            for index, x, y in raw.get('bounces', ()):
                self._map_particles.emit('spark', (x, y), born + offset + flight*(index+1)/max(1, count))
            visual=raw.get('visual')
            end=raw.get('end_cell')
            if (visual is not None and end and raw.get('end') not in ('range','land')
                    and self.session.state.is_visible(*end)):
                self._map_particles.emit('impact',tuple(end),born+offset+flight,
                    palette=(visual.highlight,visual.shade),chars=visual.impact,count=4)

    def _fx_note_events(self, state, t: float) -> None:
        """每帧一次：把「本帧新发生的受创/爆炸」记成涟漪（世界坐标）。

        🔴 只在这里记一次：旧实现在 `_fx_snapshot` 里用 `born=t` 现造 FxHit，
        于是每一帧的 age 都是 0——涟漪半径恒为 0，看起来就是爆炸格上贴了个
        不动的亮点，根本不是「环扫出去」；而且受创（心智/清醒下降）压根没有
        任何视觉反馈，只有一声音效。现在出生时刻只记一次，环才真的会扩散。
        """
        self._fx_hits = [h for h in self._fx_hits if t - h[2] <= RIPPLE_LIFE]
        self._fx_waves = [w for w in self._fx_waves if t - w[0] <= SOUND_WAVE_LIFE]
        self._fx_flashes = [f for f in self._fx_flashes
                            if 0 <= t - float(f.get("born", t)) <= float(f.get("life") or 0)]
        layer = (state.depth, state.realm_id, state.realm_depth)
        hit_layer = (id(state), *layer)
        if hit_layer != self._fx_hit_layer:
            if self._fx_hit_layer is not None and self._fx_hit_layer[0] != id(state):
                self._map_particles.clear()
                self._fx_combat_pulses.clear()
                self._fx_combat_seq = getattr(state, '_combat_fx_seq', 0)
                self._fx_projectile = None
                self._fx_projectile_seq = getattr(state, 'projectile_seq', 0)
                # §12 B2：换了 GameState（读档/新局）就必须作废环境来源缓存——
                # 键里已经不含回合数，只靠签名与层隔离；两张地图恰好同形同灯时
                # 命中旧条目虽然画面一致，但缓存归新状态所有才是明确的所有权。
                self._env_light_cache.clear()
                self._mask_cache.clear()
            self._fx_enemy_hp.clear()
            self._fx_enemy_hit_chain.clear()
            self._fx_hits.clear()
            self._fx_waves.clear()
            self._fx_flashes.clear()
            self._fx_sound_seq = None
            self._fx_flash_seq = 0
            self._fx_hit_layer = hit_layer
            # 读档/新局：旧场景的意图角标不能跟到新地图上。
            from ...core.anomaly_intents import clear as clear_intents
            clear_intents(state)
        # 声波环差分（docs §16.3）：core 侧 _sound_pulse 每次登记 seq，UI 只在
        # seq 前进时记一次出生时刻（每帧重复看到同一条不能重播）。radius=0
        # （静默协议/铁幕）core 侧本就不登记，这里再防一手。声音即时扩散，
        # 不吃弹道飞行延迟（delay 在本函数更后面才算）。off 档不登记——
        # 动画降级为日志文字（docs §16.3.5），日志的「N 个失控意识听见」
        # 每次脉冲都在，信息不丢。
        pulse = getattr(state, "last_sound_pulse", None)
        if (pulse and pulse.get("seq") != self._fx_sound_seq
                and self.config.get("fx_quality") != "off"):
            self._fx_sound_seq = pulse.get("seq")
            # 2026-10-22 玩家要求：不再画扩散环；只把「声场实际到达的标准听阈
            # 格子」交给 FX 层做视野外蓝色静态标记。玩家自身动作完全不画，
            # 避免连续脚步每步生成整屏动画。
            cells = _sound_visual_world_cells(pulse)
            if cells:
                if len(self._fx_waves) >= SOUND_WAVE_MAX:
                    self._fx_waves.pop(0)
                self._fx_waves.append((t, cells))
        # 激活短光差分（§12 D 残余）：显影方尖点亮、感应符文墙感知各压一条。
        # 只按 seq 前进拾取一次——同一条记录每帧都读得到，不能每帧重新点燃。
        # off 档同样推进 seq（关掉特效期间发生的激活，开回来不该重播）。
        for entry in (getattr(state, "light_flashes", ()) or ()):
            seq = int(entry.get("seq", 0) or 0)
            if seq <= self._fx_flash_seq:
                continue
            self._fx_flash_seq = seq
            if self.config.get("fx_quality") == "off":
                continue
            item = dict(entry)
            item["born"] = t
            self._fx_flashes.append(item)
            if len(self._fx_flashes) > 8:
                self._fx_flashes.pop(0)
        if layer != self._particle_layer:
            self._map_particles.clear()
            self._fx_combat_pulses.clear()
            self._fx_combat_seq = getattr(state, '_combat_fx_seq', 0)
            self._particle_layer = layer
            self._fx_memory_count = len(state.memory_fragments)
            self._fx_memory_ids = set(state.memory_fragments)
            self._fx_blast_count = len(getattr(state, 'explosion_blasts', ()) or ())
            # 换层：上一层的动画与角标不带过去，也不补播。
            from ...core.anomaly_intents import clear as clear_intents
            clear_intents(state)
        blasts = getattr(state, 'explosion_blasts', ()) or ()
        raw_proj = getattr(state, "last_projectile", None)
        delay = projectile_flight_time("throw", len(raw_proj.get("cells", ()))) if raw_proj and raw_proj.get("kind") == "throw" else 0.0
        self._fx_combat_pulses = [(event, born) for event, born in self._fx_combat_pulses
                                 if t-born < self._cast_event_life(event)]
        for event in getattr(state, '_combat_fx_events', ()):
            if event['seq'] <= self._fx_combat_seq:
                continue
            self._fx_combat_seq = event['seq']
            if self.config.get('fx_quality') == 'off':
                continue
            event_delay = (projectile_flight_time(raw_proj.get('kind','shot'),len(raw_proj.get('cells',())))
                           if raw_proj and event.get('projectile_seq') == raw_proj.get('seq') else 0.0)
            born = t+event_delay
            self._fx_combat_pulses.append((event, born))
            if event['kind'] == 'explosion':
                self._map_particles.emit('explosion', event['center'], born)
        if (not getattr(state, '_combat_fx_events', ()) and len(blasts) > self._fx_blast_count
                and self.config.get('fx_quality') != 'off'):
            for x, y, _radius in blasts[self._fx_blast_count:][-4:]:
                self._map_particles.emit('explosion', (x, y), t+delay)
        self._fx_blast_count = len(blasts)
        # ---- 弹道回放拾取（2026-09-23）：seq 比较只认最新一发，到期清除 ----
        raw_proj = getattr(state, "last_projectile", None)
        if raw_proj is not None and raw_proj.get("seq") != self._fx_projectile_seq:
            self._fx_projectile_seq = raw_proj.get("seq")
            self._fx_projectile = (raw_proj, t)
            self._schedule_bounce_particles(raw_proj, t)
        elif self._fx_projectile is not None:
            raw, born = self._fx_projectile
            life = projectile_replay_time(raw)
            if (t - born > life or raw_proj is None or raw_proj.get("seq") != raw.get("seq")):
                self._fx_projectile = None
        # ---- 玩家受创（心智/清醒任一下降）----
        # 2026-09-20 起：受创反馈 = 地图边框一圈红色双闪（effects.BORDER_FLASH_*），
        # 不再从玩家所在格扩散涟漪——血从视野边缘涌来，且不遮玩家格。
        # ⚠️ 换层帧必须重播种（2026-09-21）：下潜本身扣 3~4 点清醒度，旧写法
        # 把换层当受创 → 每次进新层地图边框都无故闪一记红（玩家反馈）。
        vitals = (int(getattr(state, "mind", 0)), int(getattr(state, "lucidity", 0)))
        previous = self._fx_vitals
        depth = int(getattr(state, "depth", 0))
        depth_changed = self._fx_depth is not None and depth != self._fx_depth
        self._fx_depth = depth
        if previous is not None and not depth_changed and (
            vitals[0] < previous[0] or vitals[1] < previous[1]
        ):
            self.fx_engine.note_border_hit(t)
            self._border_feedback.push('danger', t, source='vitals')
        self._fx_vitals = vitals
        # ---- 意识体受创（视野内、未致死，死了另有崩解演出）----
        world_time = float(state.time)
        live_ids = {enemy.id for enemy in state.enemies if enemy.integrity > 0}
        self._fx_enemy_hit_chain = {
            key: value for key, value in self._fx_enemy_hit_chain.items()
            if key in live_ids and world_time >= value[1]
        }
        snapshot: dict[int, int] = {}
        for enemy in state.enemies:
            if enemy.integrity <= 0:
                continue
            last = self._fx_enemy_hp.get(id(enemy))
            if last is not None and enemy.integrity < last:
                previous_count, previous_time = self._fx_enemy_hit_chain.get(enemy.id, (0, world_time))
                if world_time-previous_time > RIPPLE_RESET_TURNS:
                    previous_count = 0
                count = min(3, previous_count + 1)
                self._fx_enemy_hit_chain[enemy.id] = (count, world_time)
                radius = min(RIPPLE_MAX_RADIUS, RIPPLE_MIN_RADIUS + count - 1)
                if state.is_visible(enemy.x, enemy.y):
                    self._fx_add_hit(enemy.x, enemy.y, t+delay, radius)
            elif (enemy.id in self._fx_enemy_hit_chain
                  and world_time-self._fx_enemy_hit_chain[enemy.id][1] >= RIPPLE_RESET_TURNS):
                # A damage-bearing turn is not one of the intervening quiet
                # turns. Reset only after three completed turns without hurt.
                self._fx_enemy_hit_chain.pop(enemy.id)
            snapshot[id(enemy)] = enemy.integrity
        self._fx_enemy_hp = snapshot  # 整表替换：不会随敌人死亡无限增长
        # 爆炸只播放一圈有边界的冲击波；不对每个格子再生成重叠涟漪。
        # ---- 重要事件：边框呼吸闪（2026-09-20）----
        # 获得洞察 / 获得记忆 / 拾得稀有物品（稀有、非常稀有）。全部走差分：
        # 首帧只播种（进游戏不闪），之后数量上涨 / 出现新稀有 id 才闪。
        insights = len(getattr(state, "insights", ()) or ())
        if self._fx_insight_count is not None and insights > self._fx_insight_count:
            self.fx_engine.note_border_event(t, BORDER_EVENT_COLORS["insight"])
            self._border_feedback.push('reward', t, source=f'insight:{insights}')
        self._fx_insight_count = insights
        memories = len(getattr(state, "memory_fragments", ()) or ())
        memory_ids = set(getattr(state, 'memory_fragments', ()) or ())
        if ((self._fx_memory_count is not None and memories > self._fx_memory_count)
                or (self._fx_memory_ids is not None and memory_ids - self._fx_memory_ids)):
            self.fx_engine.note_border_event(t, BORDER_EVENT_COLORS["memory"])
            self._border_feedback.push('reward', t, source=f'memory:{memories}')
            if self.config.get('fx_quality') != 'off':
                self._map_particles.emit('memory', (state.player.x, state.player.y), t)
        self._fx_memory_count = memories
        self._fx_memory_ids = memory_ids
        rare_now = {
            item.instance_id for item in state.inventory
            if item.rarity in ("稀有", "非常稀有")
        }
        if self._fx_seen_rare is not None and (rare_now - self._fx_seen_rare):
            self.fx_engine.note_border_event(t, BORDER_EVENT_COLORS["rare"])
            self._border_feedback.push('reward', t, source='rare')
        self._fx_seen_rare = rare_now

    @staticmethod
    def _cast_event_life(event):
        preset = FX_PROFILES.get(event.get('profile'))
        return preset.entry_seconds + preset.cast_seconds + preset.tail_seconds if preset else .70

    def _fx_add_hit(self, x: int, y: int, t: float, radius: float = RIPPLE_MAX_RADIUS) -> None:
        if len(self._fx_hits) >= 16:  # 上限：连锁爆炸不至于堆出上百个波
            self._fx_hits.pop(0)
        self._fx_hits.append((x, y, t, radius))

    def _fx_repaint(self, map_view, state) -> None:
        """基帧刚被重画时补回叠加层——**不推进时钟、不跳帧**。

        每个回合结束时 `refresh_view()` 都会重画基帧，而 FX 叠加层要等下一次
        定时器（≤50ms）才补上：中间那一帧是没有光照、没有液体/气体底色的纯
        基准帧。液体/气体的叠加底色与基帧差着一个数量级，于是整片液/气就
        「亮 → 灭 → 亮」地闪一下——正是「每回合闪烁」的来源。这里在基帧重画
        后立刻补画，闪的那一下就没有了。
        """
        if not getattr(self, "_fx_active", False):
            return
        if self._floor_transition is not None or self.home_mode or state.run_over:
            return
        # ⚠️ 这里**不能**再按 panel_mode/observe_mode 提前返回（2026-09-21 修
        # 「主角周围光源渲染消失」）：面板打开时 refresh_view 照样会把基帧重画成
        # **没有光照**的纯帧，而 _fx_tick 在非 world 模式同样冻结、不会补画——
        # 于是「开面板 → 地图上的火把光整片消失」，关面板才回来。
        # _fx_repaint 用的是上一帧的**同一个时钟**（不推进时间），补上的就是冻结点
        # 那一刻的画面，所以「面板模式画面静止」的语义完全不受影响。
        # ⚠️ force=True 必写：这是回合驱动的一次性补画，走写回节流就会被
        # 吞掉，画面上那一帧没有光照的纯基帧就成了「光消失」。（去重仍然
        # 生效：基帧真变了摘要必不同，重复画面跳过无害——性能 P1，2026-10-10。）
        self._fx_paint(map_view, state, self._fx_clock, force=True)

    def _fx_paint(self, map_view, state, t: float, force: bool = False) -> bool:
        """把「基帧 + 叠加样式」写进 MapView，成功返回 True。

        🔴 返回值说的是「这一帧 FX 是开着的」，**不代表真的写了 widget**
        （2026-09-21 性能 P0）：计算每帧照跑，写回却被两道闸门拦着——

        1. 去重：本帧摘要（基帧签名 + 叠加层内容）与上次写进去的那帧完全相同
           → 屏幕上本就是这个画面，标脏纯属浪费（探针测得「标脏」才是大头）；
        2. 节流：距上次写回不足 FX_WRITEBACK_INTERVAL → 这一帧丢掉，等下一帧。

        ``force=True`` 只豁免**节流**（2026-10-10 性能 P1 收窄）：去重对 force
        照样生效——基帧真重画时摘要里的基帧签名必然变化、去重自然放行；
        同一回合内两次 force（移动结算 + refresh_view 补画）画面一致时只写
        一次。回合驱动的 `_fx_repaint()` 走这条路：基帧刚被重画成没有光照的
        纯帧，必须当帧补上，否则「打开面板 → 火把光整片消失」的回归又会回来
        （tests/test_fx.py 有这条）。
        """
        map_view.animated_combat = self.config.get("fx_quality") != "off"
        map_view.update_state(state)  # 保证基帧签名新鲜（无变化时零成本复用）
        base = map_view.last_base_text
        if base is None:
            return False
        left, top, vw, vh = map_view.viewport
        quality = str(self.config.get("fx_quality") or "off")
        # 同一动作内「回放登记」和后续 refresh 补画常以同一时钟/基帧各 force
        # 一次；第二次直接复用第一次已画出的画面，跳过 snapshot/compose。
        quick_key = (
            id(state), state.time, t, quality, map_view._frame_key,
            tuple(map_view.viewport),
            len(self._fx_hits), len(self._fx_waves),
            # §12 D 残余：短光也是叠加层内容——同 t 的重复写回不能因为它被判成相同。
            len(self._fx_flashes),
            len(self._fx_combat_pulses), self._fx_combat_seq,
            (self._fx_projectile[0].get('seq') if self._fx_projectile else None),
            bool(self._map_particles.pending),
        )
        if (quick_key == self._fx_quick_key
                and not map_view.fx_base_overwritten):
            return True
        # Gate idle ambience before building snapshots. World actions and
        # transient combat always bypass this; neither simulation nor input waits.
        transient = bool(self._fx_projectile or self._fx_combat_pulses
                         or self._map_particles.pending or self._fx_flashes
                         or self._fx_hits or self._fx_waves or charging_casts(state))
        ambient_key = (map_view._frame_key,quality,int(t*4))
        if (not force and not transient and not map_view.fx_base_overwritten
                and ambient_key == getattr(self,'_fx_ambient_key',None)):
            return True
        self._fx_ambient_key = ambient_key
        snap = self._fx_snapshot(map_view, state, t)
        frame = self.fx_engine.frame(snap, t, 2 if quality == "high" else 1)
        overlay = frame.styles
        particles = {}
        breath_sites = tuple(
            (entry.x, entry.y) for entry in state.events
            if not entry.resolved and state.is_visible(entry.x, entry.y)
        )
        if self._map_particles.pending or breath_sites:
            visible = state.visible_cells()
            protected = {(state.player.x, state.player.y)}
            protected.update((e.x, e.y) for e in state.enemies if e.integrity > 0)
            protected.update((e.x, e.y) for e in state.events if not e.resolved)
            protected.update((item.x, item.y) for item in state.world_items)
            protected.update((x, y) for x, y in visible if state.cell(x, y).solid)
            # 呼吸字符只落在干净地面上：液体/气体/植物/火焰格保留自己的
            # 材质字形，不能用装饰字符冒充环境材料。
            protected.update(
                (x, y) for x, y in visible
                if state.cell(x, y).liquid or state.cell(x, y).gas
                or state.cell(x, y).plant or state.cell(x, y).flame
            )
            particles = self._map_particles.frame(
                map_view.viewport, visible, protected, t, quality, sites=breath_sites)
        # Projectile heads and trails have priority over decorative particles.
        glyphs_frame = {**particles, **frame.glyphs}
        # 异象意图（2026-10-21）：字图模式只改异象自身字形的颜色，图像模式在
        # 同格右上角另画角标；两种后端共用同一份 core.anomaly_intents 事实。
        from ..anomaly_intent_marks import foreground_styles, intent_marks
        hints_on = self.config.get('intent_hints') is not False
        if map_view.display_mode == 'image':
            # 关闭画面特效时角标退化为相同时长的静态标记，仍然自动消失（§6.1）。
            map_view.set_intent_marks(
                intent_marks(state, animated=quality != "off", include_chase=False)
                if hints_on else {})
        elif hints_on and self.config.get('intent_large_marks') is True:
            # 整格大意图高亮默认关闭（2026-10-22 玩家要求）；开启时才走这条
            # 路径。角色地图 overlay/ranges 用视口坐标，意图事实是世界坐标，
            # 必须先换算，否则相机平移后会落到相邻格（甚至玩家身上）。
            overlay = {**overlay, **_to_viewport_styles(
                foreground_styles(state, include_chase=False), map_view.viewport)}
        # ---- 写回去重 / 节流（两道闸门，force 只豁免节流）----
        # 摘要里必须带基帧签名：玩家走一步后基帧变了，即使叠加层一字不差也要重画。
        # 🔴 去重对 force 同样生效（2026-10-10 性能 P1）：force 的语义收窄为
        # 「豁免节流」——基帧真重画时 _frame_key 必然变化、digest 必然不同，
        # 该写的一次不少；而同一步里 _capture_projectile_action 与
        # _fx_repaint 相继 force 时画面一致，重复的 compose_fx + update_scene
        # 标脏直接跳过（见 docs/perf-move-diagnosis-and-board-ux-plan.md §1.4）。
        digest = (map_view._frame_key, hash(frozenset(overlay.items())), hash(frozenset(glyphs_frame.items())))
        if digest == self._fx_frame_digest and not map_view.fx_base_overwritten:
            self._fx_quick_key = quick_key
            return True
        if not force:
            now = time.monotonic()
            # Transient animation is already driven by the 20 Hz timer. An
            # additional 50 ms wall-clock gate drops alternate ticks when the
            # timer jitters or composition consumes part of that interval.
            transient = bool(snap.projectiles or snap.casts or self._fx_combat_pulses
                             or self._map_particles.pending) and quality == 'high'
            if (self._fx_last_write is not None
                    and not transient and now - self._fx_last_write < FX_WRITEBACK_INTERVAL):
                return True
        # 直接把叠加层写进 MapView：不新增覆盖控件，鼠标路径零影响。
        if map_view.display_mode == 'image':
            # 声波按规则只落在视野外，图像后端必须单独收一份「可压过迷雾」的
            # 底色；混进常规 backgrounds 会被可见性门槛整片丢掉（WezTerm
            # 看不到声音动画，字符终端却能看到），所以这里按波次格显式拆分。
            fog_styles = _sound_visual_fog_styles(snap.waves, overlay)
            map_view.update_image_effects(overlay,glyphs_frame,force=force,
                                          fog_styles=fog_styles)
        elif self.layer_observation is None:
            styled = compose_fx(base, map_view.cell_ranges, overlay, glyphs_frame,
                                map_view.cell_w, map_view.cell_h)
            map_view.update_scene(styled)
        # 只有真的写过才记档：跳过写回的帧不能更新时间戳/摘要，否则去重会把
        # 屏幕上根本没出现的画面当成「已画」，画面就冻在这一帧不动了。
        self._fx_frame_digest = digest
        self._fx_quick_key = quick_key
        map_view.fx_base_overwritten = False
        self._fx_last_write = time.monotonic()
        return True

    def _fx_snapshot(self, map_view, state, t: float) -> FxSnapshot:
        """构建本帧 FX 快照（光照池输入，设计文档 §1.2/§1.3）。"""
        left, top, vw, vh = map_view.viewport
        px, py = state.player.x - left, state.player.y - top
        player = (px, py) if 0 <= px < vw and 0 <= py < vh else (-1, -1)
        lamps: list[tuple[int, int, str]] = []
        for entry in state.events:
            if entry.resolved:
                continue
            ex, ey = entry.x - left, entry.y - top
            if 0 <= ex < vw and 0 <= ey < vh and state.is_visible(entry.x, entry.y):
                lamps.append((ex, ey, "#ffd166"))
        # 可见性一次性取集合：逐格 is_visible 是射线检测，视口上千格 × 20fps
        # 扛不住。基帧的判据是「视野内 or 已显影」，这里照抄同一口径。
        visible = state.visible_cells()
        developed = state.developed_for_depth()
        # 与基帧（render.render_map）**同一口径**判定「这一格到底画没画出来」：
        # 逐字照抄它的 in_sight / dev_revealed / cursed_reveal，多一格少一格都会
        # 让叠加层跑到基帧没画的格子上（视野外的物质种类就漏出来了）。
        phantom_echo: set[tuple[int, int]] = set()
        if state.insight_active("残影直觉"):
            radius = state.effective_sight_radius()
            phantom_echo = {
                (enemy.x, enemy.y)
                for enemy in state.enemies
                if enemy.integrity > 0 and enemy.trait in ("phantom", "disguise")
                and max(abs(enemy.x - state.player.x),
                        abs(enemy.y - state.player.y)) <= radius
            }
        cursed_seen: set[tuple[int, int]] = set()
        if state.reveals_anomalies:
            cursed_seen = {
                (enemy.x, enemy.y)
                for enemy in state.enemies
                if enemy.integrity > 0
            }
        liquid_gas: list[tuple[int, int, str]] = []
        from ...core.realm_surface import (cached_surface_color, display_zones,
                                           normalize_bg_zones, protects_floor, surface_color)
        from ..render import _realm_zone_color
        surface_zones = display_zones(state)
        surface_cache: dict[tuple[int, int], str | None] = {}
        surface_bgs = []
        fixed_ground = set()
        shown: set[tuple[int, int]] = set()
        opaque: set[tuple[int, int]] = set()
        # §12 B2：挡视线的类墙体气体（黑烟/灰尘）—世界坐标，进遮挡签名，
        # 否则烟浓度跨过遮蔽阈值后仍会沿用旧掩码（光穿烟）。
        sight_smoke: list[tuple[int, int]] = []
        # §12 B2 第二层：真正挡视线的实心墙与高植物（世界坐标）。剔除
        # 透明墙——`_has_line_of_sight` 把 `TRANSPARENT_WALLS` 当空气，它们进
        # 遮挡签名只会制造「没挡光却作废掩码」的误重建（视口里玻璃幕墙一多，
        # 玩家每走一格都会整层重算）。`opaque` 仍保留全量墙格给光池（渲染口径）。
        sight_walls: list[tuple[int, int]] = []
        flames: list[tuple[int, int]] = []
        env_light_candidates: list = []
        for vy in range(vh):
            for vx in range(vw):
                x, y = left + vx, top + vy
                try:
                    cell = state.cell(x, y)
                except Exception:
                    continue
                if (x, y) in visible or (x, y) in developed:
                    ground = cached_surface_color(state,x,y,surface_zones,surface_cache)
                    if ground:
                        surface_bgs.append((vx, vy, ground))
                        # §12 C：只保护承担识别职责的材质（纸页/釉板），
                        # 普通聚合物走廊照常受光；不再整层锁死。
                        if (protects_floor(state, x, y) and not cell.flame):
                            fixed_ground.add((vx, vy))
                    elif cell.solid and cell.wall_kind:
                        # §12 C：普通墙面也接收光池——识别纹理（墙体字形、机关、
                        # 任务纹样）仍在受光底色之上单独绘制，不被整格光色盖掉。
                        wall_color = wall_def(cell.wall_kind).color
                        if wall_color:
                            surface_bgs.append((vx, vy, wall_color))
                    # §12 环境光源候选：植物 / 液体 / 气体 / 墙体都进登记表查询，
                    # 是否真的发光由 data/light_sources.py 决定。只收录玩家确实
                    # 看得见（或已显影）的格子，不泄露墙后灯种。
                    if (cell.plant or (cell.liquid_kind and cell.liquid > 0)
                            or (cell.gas_kind and cell.gas > 0)
                            or (cell.solid and cell.wall_kind)):
                        env_light_candidates.append((vx, vy, cell))
                # 火焰格（可见/已显影才上色，与液/气同一口径）。
                if cell.flame > 0 and ((x, y) in visible or (x, y) in phantom_echo
                                       or (x, y) in developed or (x, y) in cursed_seen):
                    flames.append((vx, vy))
                kind_color = None
                if cell.solid:
                    opaque.add((vx, vy))
                    if cell.wall_kind not in TRANSPARENT_WALLS:
                        sight_walls.append((x, y))
                if cell.plant and plant_height(cell.plant) >= 2:
                    sight_walls.append((x, y))
                if cell.gas > 0 and state._gas_sight_effect(cell)[0]:
                    # 只对气体格做这条判定（视口里绝大多数格直接跳过），
                    # 结果进遮挡签名，浓度掉下去就会让掩码重算。
                    # 世界坐标：同一个列表也用来累积 8×8 区块签名（B2 第二层）。
                    sight_smoke.append((x, y))
                if cell.liquid > 0 or cell.floor is Material.LIQUID_MEMORY:
                    kind_color = liquid_def(cell.liquid_kind).color
                elif cell.gas > 0 or cell.floor is Material.DIFFUSE_IMPRESSION:
                    kind_color = gas_def(cell.gas_kind).color
                if kind_color is None:
                    continue
                # 液/气格一律挡光（防混色，硬约束）；但只有「基帧确实画出了
                # 这一格」的才允许上叠加底色——视野外的格子基帧是记忆/未探索
                # 的暗色，照真实物质色上底色会让整张地图的液体气体亮起来。
                liquid_gas.append((vx, vy, kind_color))
                if ((x, y) in visible or (x, y) in phantom_echo
                        or (x, y) in developed or (x, y) in cursed_seen):
                    shown.add((vx, vy))
        # 呼吸光环源（2026-09-20 调整）：只保留 NPC（稳定意识）单波光环——
        # 事件点周围格子的动态发光按用户要求整个去除，视野里不再有别的动源。
        sources: list[FxSource] = []
        source_masks: list = []
        for npc in state.enemies:
            if npc.relation == "稳定意识" and npc.integrity > 0 and npc.vision >= 0                     and state.is_visible(npc.x, npc.y):
                vx, vy = npc.x - left, npc.y - top
                if 0 <= vx < vw and 0 <= vy < vh:
                    sources.append(FxSource(vx, vy, "#9ab8ff",
                                            phase=(vx * 11 + vy * 5) * 0.35,
                                            source_id=f"npc.{npc.x},{npc.y}",
                                            kind="npc"))
        if env_light_candidates:
            from ...core.vision.light_cache import (
                LOW_REGION_SAMPLES, REGION_SAMPLES, block_signatures,
                build_env_sources, covered_blocks, ensure_block_signatures,
                env_scene_key)
            from ...data.light_sources import light_spec_for_cell
            # §12 A：装饰光源一律查登记表；未登记 = 不发光，不再用材质色兜底
            # （docs §12.4.1「有材料名不等于已经接入光照」）。

            def env_light_spec(cell):
                """登记表查询（与生成报告共用同一口径）。"""
                return light_spec_for_cell(cell)

            world_colored = []
            for vx, vy, cell in env_light_candidates:
                # 装饰光源的资格只由登记表 + 存量门槛决定；机械照明半径
                # （glow.source_radius）不是前提，否则 D 批「只表现不照路」
                # 的来源会全部被挡掉。
                spec = env_light_spec(cell)
                if spec is None:
                    continue
                world_colored.append((left + vx, top + vy, spec))
            # §12 B2：来源发现 / 连片保形采样 / 逐源掩码只在「来源签名 + 遮挡
            # 签名 + 视口」变化时重算——**键里不再有 state.time**，所以世界没变
            # 时跨回合也命中缓存（静态场景每回合重跑掩码正是 §12.6.2 点名的问题）。
            low_quality = str(self.config.get('fx_quality') or 'off') == 'low'
            points = LOW_REGION_SAMPLES if low_quality else REGION_SAMPLES
            cache = self._env_light_cache
            blockers = (state._skill_sight_blockers()
                        if hasattr(state, "_skill_sight_blockers") else ())
            cache_key = env_scene_key(
                state, world_colored, left=left, top=top, width=vw, height=vh,
                points=points, opaque=sight_walls, smoke=sight_smoke,
                blockers=blockers)
            cached = cache.get(cache_key)
            if cached is None:
                # §12 B2 第二层：场景键 miss 不代表每个掩码都要重算——玩家走一格
                # 会让这次 miss（来源集合边界变化），但绝大多数采样点的位置与
                # 沿途遮挡没变，逐条命中 `_mask_cache`。
                block_occlusion, complete_blocks = block_signatures(
                    sight_walls, sight_smoke, blockers,
                    left=left, top=top, width=vw, height=vh,
                    bounds=(state.width, state.height))
                # §12 B2 第二层补丁（2026-10-21）：视口边缘的来源半径会伸出
                # 视口，那几块的签名本次没累积 → 掩码本来会退化成每帧重算。
                # 这里只把「来源包围区要用到、但还没扫完」的区块补扫一遍。
                needed = set()
                for wx, wy, spec in world_colored:
                    needed.update(covered_blocks(wx, wy, spec.radius))
                block_occlusion, complete_blocks = ensure_block_signatures(
                    state, block_occlusion, set(complete_blocks), needed,
                    bounds=(state.width, state.height))
                cached = cache.put(cache_key, build_env_sources(
                    state, world_colored, max_points=points,
                    masks=self._mask_cache, block_occlusion=block_occlusion,
                    complete_blocks=complete_blocks))
            source_masks = []
            for src in cached:
                vx, vy = src.x - left, src.y - top
                if not (0 <= vx < vw and 0 <= vy < vh):
                    continue
                sources.append(FxSource(vx, vy, src.color,
                                        phase=(vx * 7 + vy * 3) * 0.31,
                                        source_id=src.source_id,
                                        kind="environment",
                                        radius=src.radius,
                                        brightness=src.brightness))
                if src.mask:
                    source_masks.append((vx, vy, src.source_id,
                                         frozenset((ax - left, ay - top)
                                                   for ax, ay in src.mask)))
        # 真实电光（§12.4.3）：只有本回合实际通电、且玩家看得见的格才发光；
        # 断电即灭。超过预算按步长降采样，不取前 N 格。
        electric_visible = [ (ex, ey) for ex, ey in state.electric_field_cells()
                             if (ex, ey) in visible ]
        if len(electric_visible) > ELECTRIC_LIGHT_MAX:
            step = len(electric_visible) / float(ELECTRIC_LIGHT_MAX)
            electric_visible = [electric_visible[int(i * step)]
                                for i in range(ELECTRIC_LIGHT_MAX)]
        for ex, ey in electric_visible:
            vx, vy = ex - left, ey - top
            if 0 <= vx < vw and 0 <= vy < vh:
                sources.append(FxSource(vx, vy, "#bfe9ff",
                                        phase=(vx * 5 + vy * 7) * 0.27,
                                        source_id=f"electric.{ex},{ey}",
                                        kind="electric",
                                        radius=1.6, brightness=0.30))
        # 激活短光（§12 D 残余）：显影方尖点亮 / 感应符文墙感知的一次短光。
        # 只对**玩家看得见**的格给光——激活动作本身不泄露视野外的位置；
        # 未登记 kind 在 core 侧就被忽略，这里不补光色。
        sources.extend(light_flash_sources(
            self._fx_flashes, left=left, top=top, width=vw, height=vh,
            visible=visible, t=t))
        # 涟漪：读 `_fx_note_events` 记下的世界坐标队列（出生时刻只记一次，
        # 环才会真的扩散）。这里只做「世界坐标 → 视口坐标」的换算与过期剔除。
        hits: list[FxHit] = []
        for wx, wy, born, radius in self._fx_hits:
            if t - born > RIPPLE_LIFE:
                continue
            vx, vy = wx - left, wy - top
            if 0 <= vx < vw and 0 <= vy < vh:
                hits.append(FxHit(vx, vy, born, radius))
        # 声波（2026-10-22）：只保留「当前视野外」的已听见格；视野内与玩家
        # 自身动作不产生任何声音特效。这里做世界坐标→视口坐标换算与过滤。
        waves: list[FxWave] = []
        for born, cells in self._fx_waves:
            if t - born > SOUND_WAVE_LIFE:
                continue
            view_cells = _sound_visual_view_cells(cells, visible, left, top, vw, vh)
            if view_cells:
                waves.append(FxWave(view_cells, born))
        # 弹道回放（2026-09-23）：世界坐标 → 视口坐标（过期条目丢弃）。
        projectiles: list[FxProjectile] = []
        if self._fx_projectile is not None:
            raw, proj_born = self._fx_projectile
            # 「不跨回合」第二道保险（2026-09-23）：下一次已确认动作在 apply
            # 入口清空 state.last_projectile——seq 对不上就立刻停止回放。
            alive = (getattr(state, "last_projectile", None) or {}).get("seq") == raw.get("seq")
            life = projectile_replay_time(raw)
            if alive and t - proj_born <= life:
                cells = tuple(
                    (wx - left, wy - top) for wx, wy in raw.get("cells", ())
                )
                bounces = tuple(
                    (idx, wx - left, wy - top)
                    for idx, wx, wy in raw.get("bounces", ())
                )
                end_cell = raw.get("end_cell")
                projectiles.append(FxProjectile(
                    cells=cells,
                    bounces=bounces,
                    end=raw.get("end", "range"),
                    end_cell=(end_cell[0] - left, end_cell[1] - top) if end_cell else None,
                    color=projectile_color(raw.get("color") or "#ffe0b3"),
                    born=proj_born,
                    kind=raw.get("kind", "shot"),
                    visual=raw.get('visual'),
                ))
                delay = projectile_repeat_delay(raw)
                if delay:
                    projectiles.append(FxProjectile(
                        cells=cells,bounces=bounces,end=raw.get('end','range'),
                        end_cell=(end_cell[0]-left,end_cell[1]-top) if end_cell else None,
                        color=projectile_color(raw.get('color') or '#ffe0b3'),
                        born=proj_born+delay,kind='shot',visual=raw.get('visual')))
        dropped = self.fx_engine.note_lucidity(state.lucidity, t)
        return FxSnapshot(
            depth=state.depth,
            lucidity_ratio=max(0.0, min(1.0, state.lucidity / max(1, state.max_lucidity))),
            lucidity_tier=state.lucidity_tier,
            lucidity_dropped=dropped,
            sources=tuple(sources),
            hits=tuple(hits),
            waves=tuple(waves),
            viewport=(0, 0, vw, vh),
            source_masks=tuple(source_masks),
            player=player,
            # 玩家火把半径 = **本帧实际视野半径**（2026-09-21 玩家要求）：
            # 视野大 → 平滑衰减慢；视野小 → 衰减快；最亮格亮度不变；
            # 且光照范围天然不超过视野（半径就是它）。effective_sight_radius()
            # 内部已 max(1, …)，这里只是把 int 交给光池的浮点公式。
            torch_radius=float(state.effective_sight_radius()),
            # 地图底色（现在全区域统一黑）：只给光照池当放行门槛用
            # （详见 effects._light_pool）。
            base_bg=MAP_BG,
            surface_bgs=tuple(surface_bgs),
            fixed_ground=frozenset(fixed_ground),
            # 千禧园底色带：换算成视口相对坐标交给光池混色（草地绿透过光照，
            # 而不是被主梦的暖色光替换）。主梦空表零开销。
            bg_zones=tuple(
                (max(0, zone["rect"][0] - left), max(0, zone["rect"][1] - top),
                 min(vw - 1, zone["rect"][2] - left), min(vh - 1, zone["rect"][3] - top),
                 zone["color"])
                for zone in (state.realm_bg_zones or ())
                if getattr(state, "realm_id", "") == "millennium_garden"
            ) if getattr(state, "realm_id", "") == "millennium_garden" else (),
            light_walls=bool(self.config.get("fx_light_walls")),
            liquid_gas=tuple(liquid_gas),
            liquid_gas_shown=frozenset(shown),
            liquid_gas_filter=True,  # 空集也必须过滤（视野外一律不叠加）
            opaque=frozenset(opaque),
            lamps=tuple(lamps),
            flames=tuple(flames),
            electric_cells=frozenset((x-left, y-top) for x, y in state.electric_field_cells() if (x, y) in visible),
            combat_pulses=tuple(FxCombatPulse(
                event['kind'], (event['center'][0]-left, event['center'][1]-top),
                tuple((x-left, y-top) for x, y in event['cells']), born)
                for event, born in self._fx_combat_pulses if not event.get('profile')),
            casts=tuple(FxCast(
                event['profile'], event['motion'],
                (event['source'][0]-left, event['source'][1]-top),
                tuple((x-left, y-top) for x, y in event['cells']),
                tuple((x-left, y-top) for x, y in event['path']),
                born, self._cast_event_life(event), theme=event.get('theme', ''),
                center=(event['center'][0]-left, event['center'][1]-top))
                for event, born in self._fx_combat_pulses if event.get('profile'))
                + tuple(FxCast(
                    cast['profile'], cast['motion'],
                    (cast['source'][0]-left, cast['source'][1]-top),
                    tuple((x-left, y-top) for x, y in cast['cells']),
                    tuple((x-left, y-top) for x, y in cast['path']),
                    t, 1., stage='charge', progress=cast['progress'], theme=cast['theme'])
                    for cast in charging_casts(state)),
            projectiles=tuple(projectiles),
            projectile_visible=frozenset((x - left, y - top) for x, y in visible),
            ambient_visible=frozenset((x-left, y-top) for x, y in visible),
            aura_protected=frozenset(
                [(px, py)] + [(e.x-left, e.y-top) for e in state.enemies if e.integrity > 0]
                + [(i.x-left, i.y-top) for i in state.world_items]
                + [(e.x-left, e.y-top) for e in state.events if not e.resolved]),
        )

    def _sync_home_scene(self) -> None:
        visible = self.home_mode and self.panel_mode in {"home", "home_saves"}
        scene = self.query_one("#home-scene", HomeScene)
        was_visible = scene.display
        scene.display = visible
        if self._home_timer is not None:
            if visible and self.config.get("fx_quality") != "off":
                self._home_timer.resume()
            else:
                self._home_timer.pause()
        if visible:
            self._home_tick()
        else:
            scene.particles.clear()
            if was_visible:
                self.query_one("#home-title", Static).update(dream_title_text(tr("梦 层")))

    def _home_tick(self) -> None:
        if not self.is_running or not self.query(HomeScene):
            return  # 子控件卸载后，已排队的定时回调不能再查询标题。
        if not self.home_mode or self.panel_mode not in {"home", "home_saves"}:
            if self._home_timer is not None:
                self._home_timer.pause()
            return
        now = time.monotonic()
        if self._home_started is None:
            self._home_started = now
        elapsed = now - self._home_started
        quality = str(self.config.get("fx_quality") or "off")
        self.query_one("#home-scene", HomeScene).paint(elapsed, quality)
        rate = 10 if quality == "low" else 20
        phase = 1.0 if quality == "off" else min(0.9, int(elapsed * rate) / rate)
        animation_time = None if quality == "off" else int(elapsed * rate) / rate
        title_width = max(60, min(84, self.size.width - 8))
        key = (tr("梦 层"), phase, animation_time, title_width)
        if key != getattr(self, "_home_title_key", None):
            self._home_title_key = key
            title = self.query_one("#home-title", Static)
            title.styles.width = title_width
            title.update(dream_title_text(key[0], phase, animation_time, width=title_width))

    def _paint_panel_ornaments(self, quality, t):
        state = self.session.state
        feedback = self._border_feedback.sample(t) if quality != 'off' else None
        for widget in self.query('.ornament-frame'):
            if not widget.is_on_screen or not all(w.display and w.visible for w in widget.ancestors_with_self):
                continue
            # 一般受创只作用地图主框；奖励/交互可传到相关面板。
            widget_feedback = feedback
            if feedback is not None and feedback[0] == 'danger' and widget.id != 'map-pane':
                widget_feedback = None
            widget.paint_ornament(state.depth, quality, t, self._symbol_mode() != 'ascii',
                                  realm_id=state.realm_id if not self.home_mode else '',
                                  feedback=widget_feedback)

    def _deco_tick(self, t: float | None = None) -> None:
        """装饰帧（10fps，ui/deco.py）：界面镶边动效——与地图 FX 分工。

        - 主页 / 暂停菜单：标题牌匾的渐变流光边框 + ✦ 呼吸灯（这两处
          _fx_tick 是冻结的，装饰恰恰在冻结画面上最显眼）；
        - 世界视图：地图/侧栏 Pane 边框在区域主题色与亮强调色之间缓慢
          呼吸（两块反相，相位差 π，交替明灭的「边框灯」）。

        ``fx_quality=off`` 时停止流光并恢复区域静态边框；静态刻纹复用
        帧缓存，语言切换、换层照常重绘。
        ``t`` 参数供测试注入时钟。

        性能（2026-09-21 P0+）：t 先量化到 DECO_FRAME_HZ（5Hz），再拿
        「量化后的 t + 当前界面分支」当去重键——同一个键说明这次算出来的一定
        与上次逐字相同，直接返回，省一次**全屏合成**（约 14ms ≈ 1.4 个百分点，
        见模块顶部 DECO_FRAME_HZ 的说明）。
        ⚠️ 键里必须带界面分支：只比 t，从主页切进世界的那一帧会因为恰好落在
        同一个台阶上而被跳过，边框会停在主题的静态色上。
        """
        quality = str(self.config.get("fx_quality") or "off")
        if quality == "off":
            # Restore regional colors after an animated frame. Merely stopping
            # the timer leaves its last chase color frozen on the native border.
            if self._deco_frame_key is not None and self._deco_frame_key[4] != 'off':
                theme = theme_for_realm(self.session.state.realm_id, self.session.state.depth)
                for pane in self.query(OrnamentPane):
                    pane.styles.border = (theme.border_style, theme.border_color)
                self._deco_frame_key = None
            self._paint_panel_ornaments(quality, 0.0)
            return
        if t is None:
            t = time.monotonic()
        t = int(t * DECO_FRAME_HZ) / DECO_FRAME_HZ
        state = getattr(self.session, "state", None)
        key = (t, self.home_mode, self.panel_mode, getattr(state, "run_over", False),
               quality, self._symbol_mode(), getattr(state, 'depth', 0),
               getattr(state, 'realm_id', ''))
        if key == self._deco_frame_key:
            return
        self._deco_frame_key = key
        if state is None:
            return
        last_panel = self._border_last_panel
        if (last_panel is not None and self.panel_mode != last_panel
                and not self.home_mode):
            self._border_feedback.push('interaction', t, source=f'panel:{self.panel_mode}')
        self._border_last_panel = self.panel_mode
        self._paint_panel_ornaments(quality, t)
        try:
            if self.home_mode:
                return
            elif self.panel_mode == "pause":
                self.query_one("#pause-title", Static).update(home_title_text(tr("暂 停"), t=t))
            elif not self.session.state.run_over:
                # Textual 真边框的动态渐变（2026-09-20 修复「实际没有动态渐变」）：
                # 旧版是主题色↔亮色两色呼吸，幅度 35%、周期 4s，肉眼不可辨。
                # 改为四边相位差 1/4 圈的追逐流光（deco.border_flow_colors），
                # 与区域主题色对半混合——区域配色保留，光带绕框 chase 可见。
                theme = theme_for_realm(self.session.state.realm_id, self.session.state.depth)
                for pane in self.query(OrnamentPane):
                    pane.paint_ornament(state.depth, quality, t, self._symbol_mode() != 'ascii',
                                        realm_id=state.realm_id)
                top, right, bottom, left = border_flow_colors(theme.border_color, t)
                self.query_one("#map-pane").styles.border_top = (theme.border_style, top)
                self.query_one("#map-pane").styles.border_right = (theme.border_style, right)
                self.query_one("#map-pane").styles.border_bottom = (theme.border_style, bottom)
                self.query_one("#map-pane").styles.border_left = (theme.border_style, left)
                self.query_one("#side-pane").styles.border_top = (theme.border_style, left)
                self.query_one("#side-pane").styles.border_right = (theme.border_style, bottom)
                self.query_one("#side-pane").styles.border_bottom = (theme.border_style, right)
                self.query_one("#side-pane").styles.border_left = (theme.border_style, top)
        except Exception:
            pass

    def _tutorial_frame(self) -> None:
        """教程帧步进：pump 推进步骤 → 刷新教程卡与地图目标高亮。

        放在帧循环里（而非各 action 分支）保证非回合路径（观察移动/面板
        切换/瞄准）同样被评估；pump 只做字典读取与坐标比较，成本可忽略。
        """
        state = self.session.state
        # 教程埋点（每帧统一写入）：观察步的判定就是 ? 此刻停在哪格。
        # 键盘挪 ? 与鼠标点击寻路 ?（_follow_observe_path）两条路径都在这里
        # 汇合——旗标挂在 UI 状态上而非某个输入分支，不会再被改界面时漏掉。
        if self.observe_mode and self.observe_cursor is not None:
            state.tutorial_events["observe_cell"] = self.observe_cursor
        if state.tutorial.get('version') == COURSE_TEMPLATE_VERSION:
            from ...core.origin_course import observe_ui
            observe_ui(self)
        message = tutorial_pump(state)
        if message:
            self.show_toast(message, self._player_row_screen_y())
        try:
            card = self.query_one("#tutorial-card", TutorialCard)
        except Exception:
            return
        editing = self.board_editor is not None or self._active_tamper_editor() is not None or self.aiming
        card.show_step(Text() if editing or self._inspection_active() else tutorial_card_text(state))
        try:
            map_view = self.query_one("#map", MapView)
        except Exception:
            return
        targets = tutorial_target_cells(state)
        if targets:
            map_view.tutorial_cells = targets
        elif map_view.tutorial_cells:
            map_view.tutorial_cells = None

    def _sync_tutorial_highlight(self, map_view: MapView, state: GameState) -> None:
        """refresh_view 路径的高亮同步（与帧循环同一份数据）。"""
        targets = tutorial_target_cells(state) if not self.home_mode else {}
        if targets:
            map_view.tutorial_cells = targets
        elif map_view.tutorial_cells:
            map_view.tutorial_cells = None

    def _ending_text(self, state: GameState) -> Text:
        """结局演出文本：标题 + 变量化段落 + 本局统计。"""
        from ...core.content import EPILOGUE_ENDINGS

        ending = EPILOGUE_ENDINGS.get(state.ending_id) or {"title": "初醒", "lines": ["你醒了。"]}
        text = Text()
        text.append(tr("—— 结局 · ") + tr(ending["title"]) + " ——\n\n", style="bold bright_yellow")
        clues = state.epilogue_flags.get("clues", 0)
        kills = state.run_stats.get("kills", 0)
        fell_note = (
            tr("你败给了执笔者，故事被写进了它的稿纸。") if state.depth == 30 and state.epilogue_flags.get("fell_to_scribe")
            else tr("你在深层边界沉没，梦收回了它的作者。")
        )
        for line in ending["lines"]:
            text.append(
                line.format(clues=clues, kills=kills, rounds=state.time, depth=state.depth, fell_note=fell_note)
                + "\n\n",
                style="bright_white",
            )
        text.append("\n" + tr("本局统计：") +
                    tr("梦层 {depth} · 回合 {rounds} · 击杀 {kills} · 自我线索 {clues}",
                       depth=state.depth, rounds=state.time, kills=kills, clues=clues) + "\n",
                    style="grey70")
        if state.difficulty_revision >= 2 and not state.realm_id:
            from ...core.failure_review import build_review, review_lines
            lines = review_lines(build_review(state))
            for line in lines[:6]:
                text.append(line + "\n", style="grey70")
            if len(lines) > 6:
                text.append(tr("完整工具与冷却记录见主页的旧梦回忆。") + "\n", style="grey70")
        if state.run_start_choices and not self.test_mode and not self.save_disabled:
            text.append(tr("R 沿用开局快速再开（跳过教学） · T 沿用开局重做教学 · 其他键返回主页"), style="bold bright_cyan")
        else:
            text.append(tr("按任意键返回主页"), style="bold bright_cyan")
        return text

    def _newgame_text(self) -> Text:
        """Combined tuning snapshot; live widgets pin summary/actions separately."""
        content = self.query_one('#newgame-content', Static)
        text = summary_text(self)
        text.append('\n')
        text.append_text(options_text(self, content.content_size.width or 70))
        text.append_text(detail_text(self))
        return text

    def _refresh_home_view(self, state: GameState, mode: str) -> None:
        """主页界面：更新图鉴/设置/存档槽等主页组件。"""
        self.query_one("#home").styles.display = "block"
        # 标题牌匾：中英切换后重渲染（ONEIRSCRIPT 比「梦 层」长，牌匾宽度不变）。
        self._sync_home_scene()
        self.query_one("#home-subtitle").update(tr("入梦之前，先选好一段位置。"))
        self.query_one("#panel", Static).update(self._panel_text(state))
        self.query_one("#home-content", Static).update(self._panel_text(state))
        self.query_one("#home-content").display = self.panel_mode != "home"
        self._refresh_codex_components(mode)
        self._refresh_settings_rows(mode)
        self.query_one("#home-menu").styles.display = "block" if self.panel_mode in {"home", "home_saves"} else "none"
        self.query_one("#home-main").styles.display = "block" if self.home_view == "menu" else "none"
        self.query_one("#home-saves").styles.display = "block" if self.home_view == "saves" else "none"
        if self.home_view == "saves":
            self.query_one("#saves-help", Static).update(Text(
                tr("测试模式：Enter 进入/新建 · R 替换（重新调律） · ←→ 选槽或删除 · 数字 1/2/3 直选 · Esc/Q 返回")
                if getattr(self, "saves_test", False) else
                tr("Enter 进入 · ←→ 选槽/删除 · 数字 1/2/3 直选 · Esc/Q 返回")))
        self.query_one("#history-page").styles.display = "block" if self.panel_mode == "home_history" else "none"
        self.query_one("#codex-page").styles.display = "block" if self.panel_mode == "home_catalog" else "none"
        self.query_one("#settings-page").styles.display = "block" if self.panel_mode == "home_settings" else "none"
        self.query_one("#newgame-page").styles.display = "block" if self.panel_mode == "home_newgame" else "none"
        if self.panel_mode == "home_newgame":
            self._refresh_birth_layout()
            phase_names = [('options', '调律'), ('identity', '身份'), ('fragment', '记忆')]
            steps = Text()
            for index, (phase, name) in enumerate(phase_names, 1):
                if index > 1:
                    steps.append('  ──  ', style='#526781')
                steps.append(f'{index} {tr(name)}', style='bold #e5c780' if phase == self.newgame_phase else '#798aa6')
            self.query_one('#newgame-steps', Static).update(steps)
            content = self.query_one("#newgame-content", Static)
            content.update(options_text(self, content.content_size.width or 70))
            self.query_one('#newgame-summary', Static).update(summary_text(self))
            self.query_one('#newgame-detail', Static).update(detail_text(self))
            from ...core.dream_types import validate_choice
            # Keep all four button slots in place across phases. Changing
            # display can move a different button under a mouse release.
            self.query_one('#newgame-reset', Button).disabled = self.newgame_phase == 'fragment'
            self.query_one('#newgame-random', Button).disabled = self.newgame_phase != 'identity'
            self.query_one('#newgame-random', Button).label = tr('随机') + ' G'
            self.query_one('#newgame-next', Button).disabled = self.newgame_phase == 'identity' and bool(validate_choice(self.newgame_dream_type))
            self.query_one('#newgame-next', Button).label = tr('入梦' if self.newgame_phase == 'fragment' else '继续') + ' C'
            self.query_one('#newgame-back', Button).label = tr('返回') + ' Esc'
            self.query_one('#newgame-reset', Button).label = tr('默认') + ' R'
            fragment_phase = self.newgame_phase == 'fragment'
            seed_row = self.query_one("#newgame-seed-row")
            seed_row.styles.display = "block" if fragment_phase else "none"
            if fragment_phase:
                seed_input = self.query_one("#newgame-seed", Input)
                if seed_input.value != self.newgame_seed_text:
                    seed_input.value = self.newgame_seed_text
                seed_input.placeholder = tr("T/点击输入；留空随机，填整数作为本局种子")
                if self.newgame_seed_error:
                    help_text = self.newgame_seed_error
                else:
                    help_text = tr('↑↓ 选择 · ←→ 调整 · Enter/空格选中 · 鼠标点击\nR 默认 · G 随机 · C 继续/入梦 · Esc 返回；灰项不可用')
                self.query_one("#newgame-help", Static).update(Text(help_text))
            else:
                self.query_one("#newgame-help", Static).update(Text(tr('↑↓ 选择 · ←→ 调整 · Enter/空格选中 · 鼠标点击\nR 默认 · G 随机 · C 继续/入梦 · Esc 返回；灰项不可用')))
            self.call_after_refresh(self._scroll_newgame_cursor)
        # 2026-10-23：测试模式也走同一套槽位页，只是目录换成 save-test/。
        home_manager = self._saves_manager()
        for slot in range(1, home_manager.SLOT_COUNT + 1):
            exists = home_manager.for_slot(slot).slot_exists()
            # ▶ 与亮边都跟着键盘光标走（不再恒定挂在 selected_slot 上）：
            # 光标移到导航行时存档槽行不再抢视线，Enter 的落点与高亮始终一致。
            row_focused = self.home_view == "saves" and self.home_row == slot - 1
            marker = "▶" if row_focused else " "
            label = f"{marker} {tr('存档槽')} {slot} · {tr('继续') if exists else tr('新游戏')}"
            slot_button = self.query_one(f"#slot-{slot}", Button)
            slot_button.label = label
            slot_button.set_class(row_focused, "selected")
            delete_button = self.query_one(f"#delete-{slot}", Button)
            delete_button.label = tr("删除")
            delete_button.set_class(row_focused and self.home_column == 1, "selected")
        # 主菜单（2026-09-23 竖排改版）：▶ 与亮边跟上光标；存档槽页整组无高亮。
        menu_active = self.home_view == "menu"
        menu_labels = {
            "home-enter": tr("入梦"),
            "home-catalog": tr("图鉴"),
            "home-history": tr("回忆"),
            "home-settings": tr("设置"),
            "home-exit": tr("退出"),
            "test-mode": "⚙ " + tr("测试模式"),
        }
        for column, item_id in enumerate(self.HOME_MENU_ITEMS):
            selected = menu_active and self.menu_index == column
            menu_button = self.query_one(f"#{item_id}", Button)
            menu_button.set_class(selected, "selected")
            menu_button.label = Text(("▶ " if selected else "") + menu_labels[item_id])
        if self.panel_mode == "home_history":
            self._refresh_history_view()
        for category in CatalogCategory:
            selected = category is self.codex_page.category_candidate
            active = category is self.codex_page.active_category
            prefix = symbol("cursor", mode) if selected else "  "
            icon = symbol(category.symbol_key, mode)
            suffix = tr(" · 当前") if active else ""
            # 分类图标按类别着色（条目列表里的图标也用各自条目的专属色）。
            button_label = Text(prefix)
            button_label.append(icon, style=category.icon_color)
            button_label.append(f"{category.label}{suffix}")
            self.query_one(f"#catalog-category-{category.value}", Button).label = button_label

    def _refresh_history_view(self) -> None:
        """旧梦回忆页：列表/详情 + 底部常驻总计数（不受 100 条上限影响）。"""
        history = SaveManager(self.base_save_dir).load_history()
        state = self.history_page
        list_widget = self.query_one("#history-list", Static)
        if state["detail"] is not None:
            detail = render_history_detail(state["detail"])
            lines = list(detail.wrap(self.console, max(1, list_widget.content_size.width)))
            viewport = max(1, self._history_viewport_rows())
            state["detail_scroll"] = max(0, min(state["detail_scroll"], max(0, len(lines) - viewport)))
            start = state["detail_scroll"]
            list_widget.update(Text('\n').join(lines[start:start + viewport]))
            self._history_hit_rows = {}
            self.query_one("#history-help", Static).update(
                tr("滚轮/↑↓ 滚动 · Esc/Q/Enter 返回列表")
            )
        else:
            runs = history["runs"]
            state["selection"] = min(state["selection"], max(0, len(runs) - 1))
            self._history_hit_rows = {}
            list_widget.update(
                render_history_list(
                    runs, state["selection"], state["scroll"],
                    viewport_rows=self._history_viewport_rows(),
                    width=max(1, list_widget.content_size.width),
                    hit_rows=self._history_hit_rows,
                )
            )
            self.query_one("#history-help", Static).update(
                tr("↑↓/滚轮 选择 · Enter/左键 查看详情 · Esc/Q 返回")
            )
        self.query_one("#history-total", Static).update(
            tr("游玩 {runs} 次 · 通关 {wins} 次", runs=history["total_runs"], wins=history["total_wins"])
        )

    def _refresh_nav_buttons(self, mode: str) -> None:
        """Update the five text tabs and their explicit section destinations."""
        tabs_width = self.query_one('#panel-tabs').content_size.width
        cache_key = (mode, get_language(), tabs_width, self.panel_mode, self._panel_subpage_id(), self.layer_observation is not None)
        if getattr(self, "_nav_cache_key", None) == cache_key:
            return
        self._nav_cache_key = cache_key
        from ..navigation_labels import navigation_labels, navigation_widths
        labels = list(navigation_labels(tabs_width, mode))
        for (selector, label), width in zip(labels, navigation_widths(tabs_width, labels)):
            button = self.query_one(selector, Button)
            button.label = label
            button.styles.width = width
            button.set_class(selector == '#nav-' + self.sidebar_workspace, 'sidebar-active')
        from ..sidebar_workspaces import ROUTES
        group = self.sidebar_workspace
        self.query_one('#panel-sections').display = bool(ROUTES.get(group)) and self.layer_observation is None
        for workspace, routes in ROUTES.items():
            for route in routes:
                button = self.query_one('#section-' + route.key, Button)
                button.display = workspace == group
                button.label = route.english if get_language() == 'en' else tr(route.label)
                button.set_class(route.mode == self.panel_mode and (not route.subpage or route.subpage == self._panel_subpage_id()), 'sidebar-active')
        for selector, label in (
            ("#home-catalog", tr("图鉴")),
            ("#home-settings", tr("设置")),
            ("#home-exit", tr("退出")),
        ):
            self.query_one(selector, Button).label = label

def create_session(save_dir: str | Path = "save", tutorial: bool = True) -> GameSession:
    manager = SaveManager(save_dir)
    existing = True
    outdated = ""
    try:
        state = manager.load()
    except OutdatedSaveError as exc:
        # 旧格式明确拒绝（重构方案 §12.2）：不载入旧语义，但要把原因带进新局，
        # 否则启动器/EXE 双击进来只会看到「凭空开了一局新梦」。
        existing = False
        outdated = str(exc)
    except FileNotFoundError:
        existing = False
    if not existing:
        # 新开局（默认）走 0 层「梦的起始」；读档与显式关闭教程的调用方不受影响。
        # 无 UI 的入口（启动器/测试）用默认中性选项直开；交互入口走选项页。
        user_config = load_user_config()
        settings = ConfigManager(Path(save_dir) / 'config.json', file_defaults=user_config.values,
                                 file_overrides_saved=user_config.override_saved)
        # 2026-10-22：无 UI 入口也走默认开局选项，否则会绕开默认黑暗探索。
        from ...core.run_options import default_selection
        state = GameState.new(
            seed=new_run_seed(),
            tutorial=tutorial and not bool(settings.get('skip_tutorial')),
            run_options=default_selection(),
        )
        state.catalog = manager.merge_catalogs(state.catalog, manager.load_catalog())
        if outdated:
            state.messages.append(outdated)
    return GameSession(state, manager, persist_initial=existing)
