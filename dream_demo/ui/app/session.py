"""会话生命周期：构造、compose、挂载/卸载、语言/音乐同步与游戏帧刷新。"""
from __future__ import annotations

import gc
import math
import json
import os
import random
import time
from pathlib import Path

from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.geometry import Region
from textual.widgets import Button, Footer, Header, Input, Static

from ...audio import sfx
from ...env_compat import get as env_get
from ...music import music_scene
from ...config import ConfigManager, SettingChange
from ...user_config import load_user_config
from ...i18n import STATUS_TIERS, get_language, set_language, tr
from ...core import GameState, Material
from ...core.vision.light_cache import EnvLightCache, MaskCache
from ...catalog_registry import CatalogCategory, CatalogDiagnostic, build_catalog_definitions
from ...menu_pages import CodexPageState, SettingsPageState, render_codex_detail, render_codex_list, render_history_detail, render_history_list, render_setting_row
from ...mapgen import region_for_depth
from ...materials import gas_def, liquid_def
from ...persistence import GameSession, OutdatedSaveError, SaveManager
from ...symbols import symbol
from .._native import _trace_native, select_mouse_driver
from .. import glyphs
from ..home_title import home_title_text
from ..home_scene import HomeScene, DreamStatic, DreamTitle, DreamVertical, DreamHorizontal, dream_title_text
from ..frame_geometry import compose_fx, projectile_color
from ..map_particles import MapParticles
from ..visual_timeline import VisualClock, VisualPlayer
from ...core.visual_events import drain_visual_events
from ..ornament_frame import OrnamentPane
from ..self_audit import ClickableStatus, SelfAuditPane
from ..layer_observation import LayerStrip, LayerStatus
from ..signal_status import (SignalStatusLink, InspectionPane, InspectionClose,
                             SignalDetailText, SignalListenLink)
from ..input import InputMixin
from ..movement_timing import MoveCadence
from ..movement_presentation import MovementPresentation
from ..qol import QoLUIMixin
from ..debug_panel import DebugPanelMixin
from ..floating_toast import FloatingToast, MapHints, MapHintText
from ..left_event_log import LeftEventLog
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
from ..styles import MOVE_REPEAT_MIN_SECONDS
from ..styles import RIGHT_PANEL_MODES
from ..styles import HOME_PANEL_MODES
from ..styles import LAYER_LABEL_STYLE
from ..widgets import (
    ClickableHoverInfo,
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
from ..fast_static import install_fast_static_updates
from ..world_renderer import (WorldPainter, image_direct_ui_enabled,
                              world_render_mode)

# 固定尺寸正文控件 update 不请求整屏布局（见 ui/fast_static.py）：
# 必须在任何 App/控件创建之前安装；放在所有 UI import 之后，避免循环依赖。
install_fast_static_updates()

from .footer import I18nFooter

# P3：独立采样定时器周期（40Hz）。它只写平滑轨迹的中间帧，不决定行动节拍。
PRESENTATION_TICK_SECONDS = 1 / 40

# C6+（2026-10-28）：默认 GC 阈值。默认 (700,10,10) 在连续移动中约每 1.2s
# 触发一次 gen2（单次 7–50ms），就是玩家感到的「短暂卡顿」；放宽后 gen2 频率
# 降到约 1/5.7。配合启动时的 gc.freeze()，gen2 只扫本局新对象。
# ONEIRSCRIPT_GC_TUNE=0 回退旧阈值，ONEIRSCRIPT_GC_THRESHOLD 仍可精确覆盖。
GC_TUNED_THRESHOLD = (1000, 20, 20)


def _idle_frame_divisor() -> int:
    """空闲帧分频系数（性能 C9）：默认 2 帧刷一次地图，1 = 关闭（恢复 30Hz）。

    ONEIRSCRIPT_IDLE_FRAME_DIV 每次启动可调；非法值回落到默认 2。
    只有「确认没有任何动态来源」的帧才会按这个系数跳帧，判定见
    _idle_frame_skips_map_refresh / _map_frame_is_dynamic。
    """
    raw = env_get("IDLE_FRAME_DIV", "2")
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 2
    return value if value >= 1 else 1


class SessionMixin:
    """会话生命周期：构造、compose、挂载/卸载、语言/音乐同步与游戏帧刷新。"""

    def __init__(self, session: GameSession, start_at_home: bool = True):
        # 鼠标驱动按平台分发（ui/_native.select_mouse_driver）：Windows=原生记录翻译层，
        # Linux/macOS=textual SGR 适配层——两端同一事件协议（左1/中2/右3），
        # 游戏逻辑与键位完全相同，只有这一层中间层不同。
        from ...terminal_keys import install_alt_sequences
        install_alt_sequences()
        super().__init__(driver_class=select_mouse_driver())
        self.session = session
        # 主页三张存档槽永远归属**普通存档目录**：调试模式（save-test/）虽然
        # 会把 session 换成它的 SaveManager，但主页的读档/删档/槽位状态显示
        # 一律认这个根目录——测试存档只能从「⚙ 测试模式」入口进出。
        self.base_save_dir = session.manager.directory
        # FX 特效层：引擎持有跨帧状态（换层溶解/清醒骤降脉冲），时钟只在
        # 世界视图中推进（暂停/主界面/观察模式冻结，文档 §4.5）。
        # 扫描线开关（fx_scanlines）在下方 ConfigManager 建好后初始化，
        # 并在 _fx_tick 里每帧同步（设置页改动即时生效）。
        self.fx_engine = FXEngine()
        # §12 B：环境光源缓存（来源发现/保形采样/逐源掩码）。纯派生，不入存档。
        self._env_light_cache = EnvLightCache()
        # §12 B2（第二层）：逐来源掩码缓存。场景键 miss（走一格、来源增减）时
        # 掩码仍按「采样点 + 半径 + 包围区块遮挡签名」逐条命中，不必整层重算
        # 布雷森汉姆。同样纯派生，与来源缓存一起作废。
        self._mask_cache = MaskCache()
        # §8 S23 青灯祭品选择面板（运行期）：lens_offer_scene 非空 = 浮层打开。
        self.lens_offer_scene: str = ""
        self.lens_offer_items: list = []
        self.lens_offer_selected: set = set()
        self.lens_offer_cursor: int = 0
        self._lens_offer_rows: list[tuple[int, int]] = []
        self._fx_clock = 0.0
        # 进层演出状态（None = 未在演出）：设计文档 §2.3。
        self._floor_transition: dict | None = None
        self._transition_timer = None
        # 全屏暂停菜单：光标（0=继续 1=图鉴 2=设置 3=返回主页）与设置页来源
        # （settings_from：home=主页进入 pause=暂停菜单进入，决定 Q/Esc 返回哪）。
        self.pause_cursor = 0
        self.settings_from = "home"
        # 联想盘编辑器（2026-10-09）：None = 未打开；打开时是 BoardEditorController。
        # 它是**界面态**，不入存档：草稿只在编辑期间存在，退出即丢弃。
        self.board_editor: BoardEditorController | None = None
        self.board_editor_return = 0
        # 编辑器说明区的「行 → 列表位置」命中表与滚动量（渲染时写入）。
        self._board_side_rows: list[int | None] = []
        self._board_side_scroll = 0
        self._fx_last = None
        # 上一帧是特效帧吗（off 档 / 离场时置 False，决定是否要补画纯净基准帧）。
        self._fx_active = False
        # 写回节流的两个存档（性能 P0，见模块顶部 FX_WRITEBACK_HZ）：
        # _fx_last_write = 上次真正把叠加帧写进 widget 的墙钟时刻；
        # _fx_frame_digest = 上次写进去的那帧的摘要（基帧签名 + 叠加层内容）。
        # 两者都只在「真的写了」时才更新——跳过写回的帧不留痕。
        self._fx_last_write: float | None = None
        self._fx_frame_digest: tuple | None = None
        # 装饰帧去重键：(量化后的 t, home_mode, panel_mode, run_over)。None=尚未画过。
        self._deco_frame_key: tuple | None = None
        # 受创涟漪的世界坐标队列：(x, y, 出生时刻, 最大半径)。存世界坐标而不是
        # 视口坐标——玩家会走动、视口会平移，存视口坐标的涟漪会跟着画面漂。
        self._fx_hits: list[tuple[int, int, float, float]] = []
        self._fx_enemy_hit_chain: dict[str, tuple[int, float]] = {}
        self._fx_hit_layer = None
        # 地图侧语句篡改面板（docs §15.7）：面板态不入存档，离层即弃。
        self.world_tamper_editor = None
        self._world_tamper_seen_mode: str | None = None
        # 声波（2026-10-22）：世界坐标队列 (出生时刻, 已听见格集合)。
        # 数据源 = state.last_sound_pulse（core 侧 _sound_pulse 登记，seq 差分）；
        # 只保留非玩家来源、标准听阈能听到的格，UI 再按当前视野过滤。
        self._fx_waves: list[tuple[float, tuple[tuple[int, int], ...]]] = []
        self._fx_sound_seq: int | None = None
        # 激活短光（§12 D 残余）：世界坐标事件字典队列（core 侧原样字典 + born）。
        # 数据源 = state.light_flashes（note_light_flash 登记，seq 差分）；
        # 寿命 <1s，故不跨层保留、不入档。
        self._fx_flashes: list[dict] = []
        self._fx_flash_seq: int = 0
        # 命中表现（2026-10-24，手感方案 §3.2/§4）：state.presentation_hits
        # 按 seq 差分拾取；born = FX 时钟 + 弹道飞行时间，抖动/跳字/强调/
        # 命中音共用同一时刻。全部是世界坐标 + FX 时钟，不跨层、不入档。
        self._fx_hit_seq: int = int(getattr(session.state, "hit_event_seq", 0) or 0)
        self._fx_impact_cues: list[dict] = []
        self._fx_shake_offset: tuple[int, int] = (0, 0)
        # 弹道回放（2026-09-23）：拾取到的最新一发（原始缓存 + 出生墙钟时刻）。
        self._fx_projectile: tuple[dict, float] | None = None
        self._fx_projectile_seq: int | None = None
        # Projectile-related action audio and prose use the same presentation
        # clock as the flight; neither is driven by independent wall timers.
        self._fx_audio_cues: list[tuple[float, str, float]] = []
        self._fx_audio_flush_pending = False
        self._fx_deferred_message_until: dict[int, float] = {}
        self._fx_deferred_message_owner = id(session.state)
        # 同一次动作里 _capture_projectile_action 与 refresh 的 force 补画
        # 可能用同一个时钟与基帧：记录上次真正画过的快速键，直接跳过重复
        # 快照/compose（docs §11 P1）。
        self._fx_quick_key = None
        self._map_particles = MapParticles()
        # 多层 ASCII 动画（2026-10-26 扩展）：旁路事件 -> 播放器 -> 字符层。
        # 与旧 FX/粒子并存，未接系统前事件为空，旧画面逐像素不变。
        self._visual_player = VisualPlayer()
        self._visual_frame_key = 0
        self._particle_layer = (session.state.depth, session.state.realm_id, session.state.realm_depth)
        self._fx_blast_count = len(getattr(session.state, 'explosion_blasts', ()) or ())
        self._fx_combat_seq = getattr(session.state, '_combat_fx_seq', 0)
        self._fx_combat_pulses: list[tuple[dict, float]] = []
        self._home_started: float | None = None
        self._home_timer = None
        # 装饰帧空闲降频（2026-10-26）：最近一次真实输入时刻。无输入 2s 后
        # 边框流光从 5Hz 降到 2Hz，按键/鼠标一恢复立刻回到 5Hz。
        self._last_activity = time.monotonic()
        self._fx_vitals: tuple[int, int] | None = None   # 上帧 (mind, lucidity)
        # 边框短时反馈（docs §9.6）：危险/交互/奖励统一优先级，只改颜色。
        from ..border_feedback import BorderFeedback
        self._border_feedback = BorderFeedback()
        self._border_last_panel: str | None = None
        self._fx_enemy_hp: dict[int, int] = {}           # id(enemy) → 上帧完整度
        self._fx_explosion_seen: set[tuple[int, int]] = set()
        # 上帧所在层号：**换层时重播种**——下潜本身要扣 3~4 点清醒度
        # （state.descend），旧写法把这当成「玩家受创」→ 每次进新层地图边框
        # 都无故闪一记红（2026-09-21 玩家反馈）。换层帧只记录不判定。
        self._fx_depth: int | None = None
        # 重要事件边框呼吸闪的差分取样（2026-09-20）：洞察/记忆条数与行囊里的
        # 稀有物品 id 集。None = 首帧只播种不判定（进游戏第一帧不闪）。
        self._fx_insight_count: int | None = None
        self._fx_memory_count: int | None = None
        self._fx_memory_ids: set[str] | None = None
        self._fx_seen_rare: set[str] | None = None
        # 旧梦回忆页光标：selection/scroll 是列表态；detail 是当前打开的条目
        # （None=列表态），detail_scroll 是详情的滚窗首行。
        self.history_page = {"selection": 0, "scroll": 0, "detail": None, "detail_scroll": 0}
        # 玩家配置文件（主文件夹 game_config.ini）→ 设置页记录（save/config.json）。
        # 配置文件缺失时自动生成带注释的模板，解析失败一律回退（绝不挡住开局）。
        self.user_config = load_user_config()
        # 首次启动/配置缺失：语言与装备句法按系统语言预置。已有 game_config.ini
        # 永远优先（它是玩家或发行包明确给出的默认值）。
        file_defaults = dict(self.user_config.values)
        if "language" not in file_defaults:
            from ...system_locale import system_language
            detected = system_language()
            file_defaults["language"] = detected
            file_defaults.setdefault("equipment_syntax", detected)
        self.config = ConfigManager(
            session.manager.directory / "config.json",
            file_defaults=file_defaults,
            file_overrides_saved=self.user_config.override_saved,
        )
        self.fx_engine.scanlines_disabled = not bool(self.config.get("fx_scanlines"))
        self.catalog_definitions = build_catalog_definitions()
        self.catalog_diagnostics: list[CatalogDiagnostic] = []
        self.codex_page = CodexPageState()
        self.settings_page = SettingsPageState()
        self.settings_page.feedback = '\n'.join(self.config.migration_messages)
        # 「删除历史统计」的危险动作回调：设置页只做两段确认，删除在这里落地。
        self.settings_page.delete_callback = self._delete_history_stats
        # 「一键解锁全部图鉴」：立即执行（只补标记，不清记录）。
        self.settings_page.unlock_catalog_callback = self._unlock_all_catalog
        self.facing = (1, 0)
        # 右侧默认页：左侧事件记录开启时是行囊，否则保持事件记录（world）。
        self.panel_mode = self._default_panel_mode()
        self.panel_scroll = 0
        # ~ 锁定（右侧固定）时的页面快照：见 sidebar_workspaces._enforce_locked_panel_page。
        self._locked_panel_page = None
        # 携带意象页底部「记忆碎片独立滚动区」的滚动偏移（2026-10-14）。
        self.memory_scroll = 0
        self.hover_cell: tuple[int, int] | None = None
        # 悬停坐标所属的梦层：换层即作废悬停/固定/上下文目标（层尺寸会变）。
        self._hover_depth = session.state.depth
        self.pinned_target: tuple[int, int] | None = None
        self.context_menu_target: tuple[int, int] | None = None
        self.pending_confirmation: tuple[str, tuple[int, int]] | None = None
        self._attack_confirmation_entity_id: str | None = None
        self._attack_confirmation_started: float | None = None
        self._attack_confirmation_layer: tuple | None = None
        self.path: list[tuple[int, int]] = []
        # 点击远处掉落物时的「走到就捡起」目标格；到达 destination 后自动拾取。
        self.pickup_goal: tuple[int, int] | None = None
        # 点击「点击可寻路」的固体（石台/木桌子）时的目标格：走到它旁边被挡住后，
        # 就地回应它上面的异常地点、或取走台面上的显化物（见 _resolve_path_click_goal）。
        self.path_click_goal: tuple[int, int] | None = None
        self.shortcut_targets: list[tuple[int, int]] = []
        self.aiming = False
        # 默认启动进入主页选择存档，而非直接恢复上次游玩的存档
        self.home_mode = start_at_home
        # 主页两视图（2026-09-23）：menu = 竖排主菜单；saves = 存档槽页。
        # 不变式：home_mode 下 home_view == "menu" ⟺ panel_mode == "home"，
        # home_view == "saves" ⟺ panel_mode == "home_saves"。
        self.home_view = "menu"
        self.menu_index = 0
        self.save_disabled = False
        self.tutorial_session = False
        # 开局选项页（2026-10-09）的会话内状态：选空存档槽时打开，
        # phase: options（调律）→ fragment（择碎片）。全部选项无锁定。
        self.newgame_slot: int | None = None
        self.newgame_phase = "options"
        self.newgame_sliders: dict[str, int] = {}
        self.newgame_toggles: set[str] = set()
        self.newgame_cursor = 0
        self.newgame_fragments: list[str] = []
        self.newgame_fragment_cursor = 0
        # 记忆编号（选填）：第三阶段填整数即作为本局种子；空 = 随机。
        self.newgame_seed_text = ""
        from ...core.dream_types import default_choice
        self.newgame_dream_type = default_choice()
        self.newgame_identity_cursor = 0
        self.panel_selection = 0
        # 右侧面板「第几行 → 第几个条目」的映射：每次渲染面板时重算，
        # 供鼠标左键点击（使用物品 / 展开收起）定位到具体条目（-1 = 装饰行）。
        self._panel_rows: list[int] = []
        # 与 _panel_rows **逐行对齐**的条目键快照（渲染时定格）。点击必须用它
        # 而不是重算：操作界面的「目标操作」条数会随目标格变化（异象走开/死亡
        # 就少一条），渲染与点击之间一旦对不上，构想行就解析不出键 → 左键点了
        # 没反应（2026-09-20 修）。None = 装饰行。
        self._panel_row_keys: list[str | None] = []
        # 单条展开：一次只展开一个条目（键 = 面板内唯一标识；None = 全收）。
        # details_expanded 仍是 \ 键的全局开/关；左键点击某条时覆盖为单条模式。
        self.expanded_key: str | None = None
        self.item_menu_target: str | None = None
        # 洞察替换面板（左侧覆盖面板）：洞察已满又获得新洞察时打开。
        # insight_replace_target 存待替换进来的洞察 id（与 state.pending_insight 同步），
        # insight_replace_cursor 是「替换掉哪一条已有洞察」的光标行，
        # insight_replace_confirm_discard = 玩家已按 Esc/Q 请求放弃，正在二次确认。
        self.insight_replace_target: str | None = None
        self.insight_replace_cursor = 0
        self.insight_replace_confirm_discard = False
        # 替换面板的「可视行 → 洞察下标」映射（-1 = 装饰行）。
        self._insight_replace_rows: list[int] = []
        # 记忆碎片替换面板：与洞察替换同构（碎片槽满时弹出）。
        # memory_replace_target 存待收纳的碎片 definition id（与 state.pending_memory 同步）。
        self.memory_replace_target: str | None = None
        self.memory_replace_cursor = 0
        self.memory_replace_confirm_discard = False
        self._memory_replace_rows: list[int] = []
        # 观测详情（左侧覆盖面板）：右键观测条目里的意象名打开，target = catalog_id。
        # 与物品菜单同为左侧覆盖面板，二者互斥。
        self.anomaly_detail_target: str | None = None
        self.detail_cursor = 0
        self.detail_scroll = 0
        self._detail_line_count = 0
        self._detail_selectable: list[bool] = []
        # 与 _detail_selectable 逐行对齐的「Enter 能进入哪个对象」（格子详情用）；
        # None = 装饰/环境行。渲染时定格，键盘读到的是当前这一帧的映射。
        self._detail_targets: list = []
        # 物品菜单的行映射与悬停行：渲染时重算/重置，这里给默认值防止
        # 首次渲染（鼠标尚未移动过）读到未定义属性。
        self._menu_rows: list = []
        self._menu_hover_row: int | None = None
        # 观察模式：把「可操作对象」从自己换成一枚白色 ?（见 InputMixin.toggle_observe）。
        # observe_cursor 是 ? 所在格；None 表示未在观察。
        self.observe_mode = False
        self.observe_cursor: tuple[int, int] | None = None
        # 格子详情（左侧覆盖面板）：右键格子或观察模式按 ' 打开，target = (x, y)。
        # 与物品菜单/观测详情互斥；\ 键在面板打开时改收放「介绍」行。
        self.cell_detail_target: tuple[int, int] | None = None
        # 从格子详情按 Enter 进子详情时记下的返回上下文（本格, 光标行, 滚动行）；
        # 子详情关闭后原样恢复（docs §16.5／§16.6）。None = 不是子详情进来的。
        self.cell_detail_return: tuple | None = None
        self.cell_detail_intros = True
        self._bracket_armed = False
        # 拾取面板（左侧覆盖面板）：本格有多件可拾取显化物时，左键/G 打开它
        # 让玩家勾选想拿哪些。target = 拾取来源格 (x, y)；picked = 已勾选的
        # world_items 下标（在 `_pickup_candidates` 给出的列表里的位置）。
        # cursor = 光标所在行；scroll = 首行偏移（滚轮/上下键滚动）。
        self.pickup_target: tuple[int, int] | None = None
        self.pickup_picked: set[int] = set()
        self.pickup_cursor = 0
        self.pickup_scroll = 0
        # 面板光标锁定（~ 键 / 底栏「锁定」）：锁定后只有 WASD 留在面板光标上；
        # 方向键与小键盘数字始终归地图（2026-10-24 第四次定稿）。
        self.panel_locked = False
        # 右侧面板**同一按钮界面内部**的分层页签（2026-10-23）：按按钮记住当前页；
        # 行囊页直接复用物品分类筛选值。切换按钮不丢各按钮自己的页。
        from ..styles import PANEL_SUBPAGE_DEFAULTS as _subpage_defaults
        self.panel_subpages = dict(_subpage_defaults)
        self._panel_subtab_hits: list[tuple[int, int, str]] = []
        # 2026-10-27：#status 第 1 行最右 2 列锁图标的点击列区 (start, end)，
        # 每次 _refresh_world_view 按当前宽度/panel_locked 重算；None = 本帧
        # 没画图标（宽度太小或尚未布局）。ClickableStatus 据此路由 toggle_cursor_lock。
        self._status_lock_hits: tuple[int, int] | None = None
        # 光标焦点区域（/ 键 / 底栏「区域」按钮，2026-10-24 定稿）：
        # 方向键与数字键**始终**移动角色；WASD 恒控右栏，只有 `/` 把焦点交给
        # 左侧面板（overlay）时才改为在左面板内移动。map/panel 只在提示与焦点边框上有差别。
        self.cursor_zone = "map"
        # o 键目标辅助：开启后悬停格画玩家→目标的寻路路径（黄底高亮）；
        # 瞄准时 o 变为瞄准辅助（自动指向视野内最近异像，可循环切换）。
        self.target_assist = False
        self._applied_theme: RegionTheme | None = None
        self.assist_path: list[tuple[int, int]] = []
        # 目标辅助路径的缓存签名（格 + 世界状态）：鼠标在同一格内会连发大量
        # 移动事件，签名相同就跳过 A*（辅助寻路的加载速度，2026-09-17）。
        self._assist_cache: tuple | None = None
        self.observe_walk_path: list[tuple[int, int]] = []
        self.event_dialog_scroll = 0
        # 对话面板的「最近一次选项结果」（2026-10-11）：NPC 对话/事件/交易的
        # 结算消息以前只进事件记录，玩家在对话里点了选项却看不到反馈——
        # (changed, message) 存这里，_event_dialog_text 渲染在选项区上方。
        self._dialog_feedback: tuple[bool, str] | None = None
        # 测试模式（主页「测试模式」入口进入）：L 键开左侧调试面板。
        self.test_mode = False
        # 主页存档页当前操作的是不是测试存档目录（save-test/）：
        # 2026-10-23 起测试模式与普通模式一样有槽位页、删除与开局调律选项。
        self.saves_test = False
        self.newgame_saves_test = False
        self.debug_panel_open = False
        self.ending_shown = False
        self.container_index = None
        # 投掷瞄准（2026-09-19）：使用燃烧瓶/雷管后进入发射界面，记录待投物品；
        # Esc 取消不消耗，落点确认后由 throw_target 结算。
        self.throw_item_index: int | None = None
        # 喷系武器（喷水枪/吹风机）：弹药选择浮层与已选容器（None=自带清水/水蒸气）。
        self.spray_source: int | None = None
        self.spray_select: dict | None = None
        self.equipment_choice: dict | None = None
        self.aim_action_choice: dict | None = None
        self.sentence_aim: dict | None = None
        self._spray_rows: list[tuple[int, int]] = []
        # 一次性发射物（光焰弹）：瞄准中的物品下标。
        self.fire_once_index: int | None = None
        # 上一次发射/投掷已被拒绝（2026-10-18）：失败后不再反复重试同一动作，
        # 左键或任意键盘键 = 取消这次瞄准（见 aiming.confirm_aim / aim_key）。
        self._aim_failed = False
        # 洞察之镜：开镜时的三选一（候选在开镜时掷定），mirror_cursor 当前行。
        self.mirror_index: int | None = None
        self.mirror_rolls: list[str] = []
        self.mirror_cursor = 0
        self.debug_side = "left"
        self.debug_category = 0
        self.debug_item = 0
        self.debug_pending: tuple[str, str] | None = None
        self.debug_portent_rounds = 8
        self.debug_portent_stacks = 1
        self.debug_param = 0  # 征兆参数子光标：0=回合数，1=层数
        self.debug_left_scroll = 0
        self.debug_right_scroll = 0
        self.event_dialog_cursor = 0
        self._dialog_rows: list[int] = []
        self._aim_assist_pos: tuple[int, int] | None = None
        # Enter/n/b 既由 on_key 处理、又出现在底栏绑定里（Textual 的派发顺序：
        # on_key 先于非 priority 绑定），用这个集合吃掉那次重复触发——
        # 否则一次按键会结算两次（Enter 拔一次草再拔一次、n 连下两层）。
        # 每次按键都会重置，确保底栏点击（不经过 on_key）永远能正常生效。
        self._keys_handled_in_on_key: set[str] = set()
        self.selected_slot = session.manager.slot
        # 主页光标（行/列）：行 0..2 = 存档槽 1..3，行 3 = 图鉴/设置/退出；
        # 列 = 行内的左右项（存档槽 ↔ 删除，图鉴 ↔ 设置 ↔ 退出）。
        # 方向键改由 move_home_cursor 驱动它；Enter 在主页**不**落地
        # （2026-09-16 起 Enter 不再开启新游戏/载入存档，只保留「删除」两段确认）。
        self.home_row = max(0, min(self.session.manager.SLOT_COUNT - 1, self.selected_slot - 1))
        self.home_column = 0
        # 「删除」不可恢复：Enter / 鼠标点击 / D 键三条路统一走
        # _request_delete_slot 的 _ask_qol 两段确认（默认取消，带存档签名守卫）。
        self.home_confirm_delete = False
        self._configured_show_details = bool(self.config.get("show_details"))
        self.details_expanded = self._configured_show_details
        self._game_frame_timer = None
        self._presentation_timer = None
        self._presentation_timer_running = False
        # 空闲帧分频 + 帧内控件引用缓存（2026-10-22 性能 C9）：
        # 30Hz 的 _refresh_game_frame 里每帧 3 次 App.query 会走一遍整个控件树
        # （实测空闲帧 ~2.0ms 中约 1.8ms 花在 selectors 匹配），而 toast/结算/
        # 地图三个控件在 compose 里一次性挂载、生命周期同 App，按需缓存即可。
        # 地图 update_state 只在确认无动态来源时按 ONEIRSCRIPT_IDLE_FRAME_DIV
        # 降频（默认 2 = 15Hz，1 = 关闭）。
        self._idle_frame_div = _idle_frame_divisor()
        self._idle_frame_phase = 0
        self._frame_toast = None
        self._frame_settlement = None
        self._frame_map = None
        self._last_move_key: str | None = None
        self._last_move_time = 0.0
        self._held_key: str | None = None
        self._held_direction: tuple[int, int] | None = None
        self._last_hold_event = 0.0
        self._hold_repeats = 0
        # M1：长按移动的统一下一次期限（按单调秒计）。按键事件只提供「仍按住」
        # 证据，帧回调按截止点结算；转向/阻断/松键一律 reset。
        self._move_cadence = MoveCadence(MOVE_REPEAT_MIN_SECONDS)
        self._movement_presentation = MovementPresentation()
        self._movement_presentation_viewport = None
        self._movement_presentation_needs_final_frame = False
        set_language(str(self.config.get("language")))
        # 标题栏标题按语言取中文名/英文名（此前从未初始化，Header 一直显示
        # Textual 默认的类名 "DreamApp"，2026-09-19 修复）。
        self._sync_language()
        # 装备句法决定「新建盘面」默认用哪套列角色（已有盘面随存档自带）。
        self._sync_equipment_syntax()
        # 标题栏播报去重缓存：记录「已看过的最近一条事件消息」。气泡播报会把
        # 它推进到当前事件记录的末条（气泡消息本身未必进记录，不能拿气泡文本
        # 当水位——否则帧循环 diff 会拿旧记录消息反复盖掉播报）。
        self._seen_event_message = ""
        self._init_qol()

    def _sync_language(self) -> None:
        """把配置中的语言同步到 i18n；切换后整个界面在下一次刷新即换语言。"""
        previous = get_language()
        set_language(str(self.config.get("language")))
        title = tr("梦 层")
        if self.title != title:
            self.title = title
        # 语言真的变了才重排底栏：Footer 的键位描述由 I18nFooter 在 compose
        # 时取词（import 时刻语言未定，BINDINGS 里固化的永远是中文原文）。
        if previous != get_language() and self.is_running:
            self.refresh_bindings()

    def _sync_equipment_syntax(self) -> None:
        """把「装备句法」设置同步成新盘面的默认语序（docs §14.13 第 5 项）。

        只改**今后新建**盘面的默认值：已有盘面把 syntax 存在自己的存档里，
        改设置不会重解当前构筑——那属于整理事务，不是设置项的副作用。
        """
        from ...equipment.syntax import default_syntax, normalize_syntax, set_default_syntax
        wanted = normalize_syntax(self.config.get("equipment_syntax"))
        # 老配置文件/旧发行包没有 equipment_syntax：未在游戏内改过时跟随界面语言，
        # 避免英文玩家拿到中文列角色。配置文件若显式写了 equipment_syntax，则尊重它。
        explicit = ("equipment_syntax" in self.user_config.values
                    or self.config.has_record("equipment_syntax"))
        if not explicit:
            wanted = normalize_syntax(self.config.get("language"))
            # 设置页也要显示实际生效的语序；不落盘、不标 touched，下次启动仍按
            # 当前语言重新推导，玩家之后改语言也能继续跟随。
            if normalize_syntax(self.config.get("equipment_syntax")) != wanted:
                self.config.values["equipment_syntax"] = wanted
        if default_syntax() != wanted:
            set_default_syntax(wanted)

    def compose(self) -> ComposeResult:
        yield DreamHeader()
        with Horizontal(id="layout"):
            with MapHints(id="map-hints"):
                # 提示气泡在上、临时消息在下：瞄准/观察提示首行必须贴地图上沿
                # （cursor-fuel 回归）。分层观察入口已移到底栏可展开键位条，
                # 不再常驻一格气泡遮挡地图。
                yield MapHintText(id="map-mode-hint")
                yield FloatingToast(id="toast")
            # 左侧透明事件记录（2026-10-26）：默认关闭，开启时叠在地图显示框
            # 左下/左上，只有文字、无背景无边框、鼠标穿透。
            yield LeftEventLog(id="left-event-log")
            with OrnamentPane(id="map-pane"):
                # 提示层是 layout 的兄弟节点，贴边时不会被地图内边距裁剪。
                yield MapView(id="map")
                yield LayerStrip(id="layer-strip")
                yield LayerStatus(id="layer-status")
                yield TutorialCard(id="tutorial-card")
                yield MapOverlayPanel(id="map-overlay")
                # 自我察觉（个人菜单）：地图内居中悬浮层（独立 layer，不挤压地图）。
                yield TamperOverlayPanel(id="tamper-overlay")
                yield SettlementScreen(id="settlement")
                with Horizontal(id="debug-panel"):
                    yield DebugListWidget(id="debug-left")
                    if Rule is not None:
                        yield Rule(orientation="vertical", id="debug-divider")
                    else:  # pragma: no cover - Rule 不可用时退化为静态竖线
                        yield Static("│", id="debug-divider")
                    yield DebugListWidget(id="debug-right")
            with OrnamentPane(id="side-pane"):
                yield ClickableStatus(id="status")
                yield SignalStatusLink(id='signal-status')
                yield ClickableHoverInfo(id="hover-info")
                with Horizontal(id="panel-tabs"):
                    from ..sidebar_workspaces import WORKSPACES, ROUTES
                    from ..widgets import SidebarTabButton
                    for key, label, english, mode in WORKSPACES:
                        yield SidebarTabButton(tr(label), id='nav-' + key)
                    # 2026-10-24 玩家定稿：六个页签后不再挂「盘」按钮。联想盘入口
                    # 改为「构筑 · 装备」页里可点击的盘面示意图（见 panels/mouse_routing）。
                with Horizontal(id='panel-sections'):
                    for routes in ROUTES.values():
                        for route in routes:
                            yield NativeButton(tr(route.label), id='section-' + route.key)
                with Horizontal(id='sidebar-tools'):
                    for key, label in (('search', '搜'), ('filter', '类'), ('sort', '序'),
                                       ('expand', '详情'), ('menu', '操作'), ('clear', '×'),
                                       ('pin', '固定'), ('back', '返回'), ('related', '物品'), ('fold', '折叠')):
                        yield NativeButton(tr(label), id='sidebar-' + key)
                yield EventPanel(id="panel")
                yield SentenceWriter(id='equipment-sentence')
                # 🔴 用户规定（2026-10-15）：侧栏底部只允许 panel-help 这 1 行。
                # 此前的 qol-context（注释，最多 2 行）与两条 qol 工具栏按钮行
                # 直接压在面板内容上遮挡游戏画面，已整体移除——搜索/排序/筛选、
                # 展开/注释、全图/原大等功能全部由快捷键承担（Alt+F/L/R/E、
                # Alt+0/9，见 qol.py 路由）。并行会话勿恢复多行底部 UI。
                # Enter（行动）、x（观察）、n/b（下潜/上浮）都不在这一行：它们是
                # 底栏可点击的键位（见 BINDINGS）。这里只列没有底栏按钮的键位。
                from ..controls_help import ControlsHelpLink
                yield ControlsHelpLink(tr('完整键位表 · 点击 / Alt+H'), id='panel-help')
        with Vertical(id="home"):
            yield HomeScene(id="home-scene")
            # Each full-width row centers its own child. Vertical's group
            # alignment otherwise left-aligns the 60-column menu with an
            # expanded 84-column title, visibly shifting the buttons left.
            with DreamVertical(id="home-title-row", classes="home-center-row"):
                yield DreamTitle(id="home-title")
            with DreamVertical(id="home-subtitle-row", classes="home-center-row"):
                yield DreamStatic(tr("入梦之前，先选好一段位置。"), id="home-subtitle")
            with DreamVertical(id="home-menu-row", classes="home-center-row"):
                with DreamVertical(id="home-menu"):
                    yield DreamStatic(id="home-content")
                    # 竖排主菜单：入梦在上、测试模式垫底。
                    with DreamVertical(id="home-main"):
                        yield NativeButton(tr("入梦"), id="home-enter", classes="home-entry")
                        yield NativeButton(tr("图鉴"), id="home-catalog")
                        yield NativeButton(tr("回忆"), id="home-history")
                        yield NativeButton(tr("设置"), id="home-settings")
                        yield NativeButton(tr("退出"), id="home-exit", variant="error")
                        yield NativeButton("⚙ " + tr("测试模式"), id="test-mode", classes="slot-main")
                    with DreamVertical(id="home-saves"):
                        with DreamHorizontal(classes="slot-row"):
                            yield NativeButton(tr("存档槽") + " 1", id="slot-1", classes="slot-main")
                            yield NativeButton(tr("删除"), id="delete-1", classes="slot-delete", variant="warning")
                        with DreamHorizontal(classes="slot-row"):
                            yield NativeButton(tr("存档槽") + " 2", id="slot-2", classes="slot-main")
                            yield NativeButton(tr("删除"), id="delete-2", classes="slot-delete", variant="warning")
                        with DreamHorizontal(classes="slot-row"):
                            yield NativeButton(tr("存档槽") + " 3", id="slot-3", classes="slot-main")
                            yield NativeButton(tr("删除"), id="delete-3", classes="slot-delete", variant="warning")
                        with DreamHorizontal(id='tutorial-slot-row', classes='slot-row'):
                            yield NativeButton(tr('新手教程'), id='home-tutorial', classes='slot-main')
                        yield DreamStatic(tr("Enter 进入 · ←→ 选槽/删除 · 数字 1/2/3 直选 · Esc/Q 返回"), id="saves-help")
            with Vertical(id="history-page"):
                yield HistoryListView(id="history-list")
                yield Static(id="history-total")
                yield Static(id="history-help")
            # 开局选项页（2026-10-09）：选空存档槽后进入——调律（滑条+开关+
            # 难度条）→ 择一枚记忆碎片 → 创建新局。文本渲染，键位操作。
            with Vertical(id="newgame-page"):
                yield Static(id="newgame-steps")
                yield Static(id="newgame-summary")
                with Horizontal(id="newgame-body"):
                    with VerticalScroll(id="newgame-scroll"):
                        yield NewGameOptionsView(id="newgame-content")
                    yield Static(id="newgame-detail")
                # 记忆编号（选填）：第三阶段择碎片时显示，填整数即作为本局种子。
                with Horizontal(id="newgame-seed-row"):
                    yield Static(tr("记忆编号（选填）"), id="newgame-seed-label")
                    yield Input(placeholder=tr("T/点击输入；留空随机，填整数作为本局种子"),
                                id="newgame-seed")
                with Horizontal(id="newgame-actions"):
                    yield NativeButton(tr("重置居中"), id="newgame-reset")
                    yield NativeButton(tr("随机"), id="newgame-random")
                    yield NativeButton(tr("继续：择碎片"), id="newgame-next", variant="primary")
                    yield NativeButton(tr("返回"), id="newgame-back")
                yield Static(id="newgame-help")
        # 图鉴页同样挂在 Screen 顶层（2026-10-14，从 #home 移出）：暂停菜单也要
        # 打开它，而 #home 在游戏内是隐藏的——旧实现 Esc 菜单选「图鉴」只能
        # 错误地落到观测面板（panel_mode="catalog"），图鉴从未被打开过。
        # 与设置页同构：position:absolute 全屏覆盖，主页与游戏内共用一份 UI。
        with Vertical(id="codex-page"):
            with Horizontal(id="catalog-categories"):
                for category in CatalogCategory:
                    yield NativeButton(category.label, id=f"catalog-category-{category.value}")
            with Horizontal(id="codex-body"):
                yield CodexListView(id="codex-list")
                yield Static(id="codex-detail")
            yield Static(tr("终端尺寸不足，请扩大窗口后查看图鉴。"), id="codex-too-small")
            yield Static(id="codex-help")
        # 设置页挂在 Screen 顶层（不在 #home 里）：overlay 层全屏覆盖，
        # 主页与暂停菜单共用同一份（见 CSS 注释）。
        with Vertical(id="settings-page"):
            with Horizontal(id='settings-categories'):
                for category, label in SettingsPageState.CATEGORIES:
                    yield NativeButton(tr(label), id=f'settings-category-{category}')
            with SettingsListView(id="settings-list"):
                for index in range(len(self.config.registry)):
                    yield SettingRowView(index, id=f"setting-row-{index}", classes="setting-row")
            yield Static(id="settings-feedback")
        # 全屏暂停菜单（2026-09-20）：Esc 在「无可取消状态 + 角色静止」时打开。
        # 选项从上到下：继续 / 图鉴 / 设置 / 返回主页；WS·方向键·滚轮选择，
        # Enter/左键触发，Esc = 继续。每个选项是独立控件（PauseOptionView），
        # 点击命中谁就触发谁，不做行号换算。
        with Vertical(id="pause-menu"):
            with Vertical(id="pause-box"):
                yield Static(id="pause-title")
                with Vertical(id="pause-list"):
                    for option_index in range(len(self.PAUSE_OPTIONS)):
                        yield PauseOptionView(option_index, id=f"pause-option-{option_index}", classes="pause-option")
                yield Static(id="pause-help")
        # 携带意象·联想盘编辑器（2026-10-09）：整屏覆盖层，只在打开时显示。
        # 工具栏每个按钮是独立控件（同暂停菜单），点谁触发谁，不做列号换算。
        with BoardEditorView(id="board-editor"):
            yield Static(id="board-editor-title")
            with Horizontal(id="board-editor-body"):
                with Vertical(id='board-editor-map'):
                    yield BoardGridView(id="board-editor-grid")
                    yield Static(id='board-editor-inspect')
                with Vertical(id='board-editor-main'):
                    yield Static(id='board-editor-grammar')
                    yield Static(id='board-editor-status')
                    with VerticalScroll(id='board-editor-scroll'):
                        yield BoardSideView(id="board-editor-side")
                        yield SentenceWriter(id='board-editor-sentence')
                        yield Static(id='board-editor-effects')
            with Vertical(id="board-editor-tools"):
                for group in (self.BOARD_TOOL_ACTIONS[:3], self.BOARD_TOOL_ACTIONS[3:]):
                    with Horizontal(classes='board-tool-row'):
                        for action in group:
                            yield BoardToolButton(action, id=f"board-tool-{action}", classes="board-tool")
            yield Static(id="board-editor-help")
        with OrnamentPane(id="qol-confirm-dialog"):
            yield Static(id="qol-confirm-text")
            yield Input(id="qol-search-input", placeholder=tr("输入物品名称；Enter 确定，Esc 取消"))
            with Horizontal(id="qol-confirm-buttons"):
                yield QolConfirmButton(tr("取消"), id="qol-confirm-no")
                yield QolConfirmButton(tr("确认"), id="qol-confirm-yes", variant="warning")
        from ..controls_help import ControlsHelpPanel
        with ControlsHelpPanel(id='controls-help'):
            yield Static(tr('完整键位表'), id='controls-help-title')
            with VerticalScroll(id='controls-help-scroll'):
                yield Static(id='controls-help-text')
            yield NativeButton(tr('关闭 · Esc / Q'), id='controls-help-close')
        with SelfAuditPane(id="self-pane"):
            yield Static(id="self-audit-body")
        from ..layer_info import LayerInfoPane
        with LayerInfoPane(id="layer-info-pane"):
            yield Static(id="layer-info-body")
        with InspectionPane(id='signal-detail'):
            yield Static(tr('噪音与混乱度'), id='signal-detail-title')
            with VerticalScroll(id='signal-detail-scroll'):
                yield SignalDetailText(id='signal-detail-text')
            yield SignalListenLink(tr('凝听一回合 · L / 点击'), id='signal-listen')
            yield InspectionClose(tr('返回 · Esc / Alt+N'), id='signal-detail-close')
        yield I18nFooter(show_command_palette=False)

    def on_mount(self) -> None:
        from ..sidebar_workspaces import WORKSPACES, ROUTES
        for key, label, english, mode in WORKSPACES:
            button = self.query_one('#nav-' + key, Button)
            button.tooltip = tr(label)
            button.can_focus = False
        for routes in ROUTES.values():
            for route in routes:
                self.query_one('#section-' + route.key, Button).can_focus = False
        for button in self.query('#sidebar-tools Button'):
            button.can_focus = False
            button.active_effect_duration = 0
        if self.home_mode:
            # 启动即主页：隐藏游戏布局，显示存档槽选择页。
            # 底栏（Footer）不隐藏——键位常驻是硬要求，不能随界面条件触发；
            # 主页上点这些键位各自有守卫（见 action_observe_mode 等），不会误触发。
            self.panel_mode = "home"
            self.query_one("#layout").styles.display = "none"
            self.query_one("#home").styles.display = "block"
            self.query_one(Header).styles.display = "none"
        else:
            self.session.start()
        self._path_timer = self.set_interval(0.12, self._follow_path)
        self._fx_timer = self.set_interval(1 / 20, self._fx_tick)
        # 装饰帧（10fps，ui/deco.py）：牌匾流光/呼吸灯 + 世界边框呼吸。
        # 与 _fx_tick 分开：fx_tick 冻结于暂停/主页，而装饰恰恰在那里最显眼。
        self._deco_timer = self.set_interval(0.1, self._deco_tick)
        self._home_timer = self.set_interval(1 / 20, self._home_tick, pause=True)
        self._game_frame_timer = self.set_interval(GAME_FRAME_SECONDS, self._refresh_game_frame)
        # P3：独立采样定时器，只负责平滑轨迹里的中间帧直写。默认暂停；
        # 平滑开始 resume、轨迹结束 pause，不参与节拍与规则结算。
        self._presentation_timer = self.set_interval(
            PRESENTATION_TICK_SECONDS, self._presentation_tick, pause=True)
        self._audio_timer = self.set_interval(1 / 20, sfx.tick)
        self._set_qol_layout_classes()
        self._ensure_world_painter()
        self.refresh_view()
        self.call_after_refresh(self._freeze_gc_once)
        self.call_after_refresh(self._graphics_startup_notice)
        if self.config.migration_messages:
            self.call_after_refresh(self.show_toast, '\n'.join(self.config.migration_messages))

    def _ensure_world_painter(self) -> None:
        """按当前配置惰性装载直写 painter（painter 模式或图像模式受控直绘）。

        painter 模式下它接管世界帧；图像模式（第二步）下它只接管周围 UI，
        地图由原生图像层负责。角色/纯 Textual 模式不装载，避免给默认路径
        增加任何钩子开销（test_deco_painter_throttle 也用这个口径）。
        """
        if getattr(self, "_world_painter", None) is not None:
            return
        install = world_render_mode() == "painter"
        if not install:
            # 图像受控直绘只给真实终端装：无头测试/探针的 driver 不是终端，
            # 直写没有语义，还会打乱既有的「终端写包」断言
            # （test_image_dirty_261022 等）。painter 模式的既有测试仍需在
            # 无头下拿到 painter 实例，所以那一支照旧安装。
            if getattr(self, "is_headless", False):
                return
            if not image_direct_ui_enabled():
                return
            # 只看玩家显式配置，不看 resolved：无头测试/拍照补丁会把
            # resolved 改成 image，但它们并不是真实终端。配置切到图像的
            # 运行期切换需要重启后启用受控直绘（回退路径仍正常）。
            try:
                install = str(self.config.get("map_display") or "").strip().lower() == "image"
            except Exception:
                return
        if not install:
            return
        self._world_painter = WorldPainter(self)
        self._world_painter.install(self.screen)

    def _freeze_gc_once(self) -> None:
        """把「启动时就已存在」的常驻对象移出 GC 扫描（2026-10-21 性能 P95）。

        实测（`build/performance/move-open-*.json`）：移动 `apply_ms` 中位 27–31 ms，
        但 P95 是 82–90 ms，且**有 gen2 回收的那几步全部慢**（6/6，中位 85.1 ms 对
        31.1 ms）——8% 的慢步正好等于 gen2 的发生率。gen2 是唯一会扫全堆的回收，
        而这一堆里绝大部分是启动后就不再变的东西（世界数据、字形缓存、控件树）。

        `gc.freeze()` 把它们移进「永久代」，之后 gen2 只扫本回合新建的对象。
        新建对象照常按引用计数与循环回收处理，所以不改变任何可见行为；环境变量
        `ONEIRSCRIPT_GC_FREEZE=0` 可以关掉它做对照。

        只做一次：重复 freeze 会把「本回合的中间垃圾」也钉成永久对象。
        """
        # C6（2026-10-22 实测，默认关闭）：可选 GC 阈值开关。A/B 见
        # build/performance/gc-ab-261022-interleaved.json——
        # ONEIRSCRIPT_GC_THRESHOLD=1000,20,20 把每 80 步的 gen2 从约 7 次降到 0、
        # apply p95 82→64ms、GC 自身开销 6.4→2.3ms/步，峰值 RSS 不变；但外部
        # 负载噪声大、长局内存未验证，所以只做环境开关：不设变量时完全不碰
        # 阈值（默认仍是 700,10,10），不改现有行为。
        self._apply_gc_threshold_once()
        # 两个标记分工：「试过没有」与「这次真的冻上了」。开关关掉时只置前者——
        # 否则退出时会对别人的永久代调 `gc.unfreeze()`（它是全局的）。
        if getattr(self, "_gc_freeze_attempted", False):
            return
        self._gc_freeze_attempted = True
        if env_get("GC_FREEZE", "1") == "0":
            return
        try:
            gc.freeze()
        except Exception:
            return
        self._gc_frozen = True

    def _apply_gc_threshold_once(self) -> None:
        """C6：GC 阈值。2026-10-28 起默认放宽到 (1000,20,20)。

        证据（outputs/stutter-261028/summary-quick.md，玩家配置 image+平滑+high）：
        默认 (700,10,10) 下连续移动约每 1.2s 一次 gen2，单次 7–50ms——
        对应玩家报告的「连续移动一会就短暂卡一下」；gen1 56 次累计 168ms、
        gen0 59 次累计 125ms。放宽后同一探针 gen2 8→1 次、可见间隔 p95
        210→160ms。配合 _freeze_gc_once 的 gc.freeze()（启动常驻对象进永久代），
        gen2 只扫本局新对象，峰值 RSS 在既有 A/B 中未变。

        优先级（只做一次，避免每次重建界面重复写全局阈值）：
        1. ONEIRSCRIPT_GC_THRESHOLD="gen0,gen1,gen2"（旧名 DREAM_STRATA_ 兼容）
           合法时原样生效；非法值不回退到旧行为，而是继续走下面的默认放宽；
        2. ONEIRSCRIPT_GC_TUNE=0 一键回退到 (700,10,10)，对照测量/排障用；
        3. 否则写入默认放宽值。
        """
        if getattr(self, "_gc_threshold_attempted", False):
            return
        self._gc_threshold_attempted = True
        raw = (env_get("GC_THRESHOLD", "") or "").strip()
        if raw:
            try:
                values = tuple(int(part) for part in raw.split(","))
            except ValueError:
                values = ()
            if len(values) == 3 and all(value > 0 for value in values):
                try:
                    gc.set_threshold(*values)
                except Exception:
                    pass
                return
        if str(env_get("GC_TUNE", "1") or "1").strip().lower() in (
                "0", "false", "no", "off"):
            return
        try:
            gc.set_threshold(*GC_TUNED_THRESHOLD)
        except Exception:
            return

    def _set_qol_layout_classes(self) -> None:
        width = self.size.width
        self.screen.set_class(width < 95, 'qol-compact')
        self.screen.set_class(self.size.height < 28,'qol-short-home')
        self.screen.set_class(95 <= width < 120, 'qol-medium')
        self._sync_map_task_focus()

    def _sync_map_task_focus(self) -> None:
        """标记瞄准/拾取等地图任务状态，**不改右栏几何**。

        2026-10-24 玩家反馈：左栏或气泡出现时右栏若临时收窄（改宽/改内边距），
        内容会整体重排、左右边缘跳动。现在只维护语义类（`map-task-focus`），
        右栏宽度始终按屏幕档位取，退出任务也不会有任何几何变化。
        """
        focused = bool(
            not self.home_mode
            and (self.aiming or self.sentence_aim is not None
                 or getattr(self, 'spray_select', None) is not None
                 or self._active_left_overlay() is not None)
        )
        if focused == self.screen.has_class('map-task-focus'):
            return
        self.screen.set_class(focused, 'map-task-focus')

    def on_resize(self, event) -> None:
        pixels = getattr(event, 'pixel_size', None)
        if pixels is not None and pixels.width > 0 and pixels.height > 0:
            self._map_terminal_pixels = pixels
            self._map_terminal_cell_pixels = (pixels.width/max(1,event.size.width),
                                              pixels.height/max(1,event.size.height))
        self._schedule_map_geometry_probe()
        self._set_qol_layout_classes()
        self.call_after_refresh(self._refresh_after_resize)

    def _refresh_after_resize(self) -> None:
        if self.is_running and self.query('#panel'):
            self.refresh_view()
        # 键位表的尺寸/位置是按打开时的可用区算的，窗口缩放后要跟着重排。
        self._fit_controls_help()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'qol-search-input':
            self._qol_search_changed(event.input.value)
        elif event.input.id == 'newgame-seed':
            # 记忆编号（选填，开局第三阶段）：只记文本，真正解析在确认入梦时。
            self.newgame_seed_text = event.input.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != 'newgame-seed':
            return
        self._mark_key_handled("enter")
        self.set_focus(None)
        self._confirm_newgame_fragment()

    def _sync_music(self) -> None:
        """Scene requests are idempotent; no per-action restarting of the stream."""
        sfx.set_volume(sfx=int(self.config.get('sfx_volume')) / 10,
                       music=int(self.config.get('music_volume')) / 10)
        if not self.config.get('music_enabled'):
            sfx.stop_music(fade_ms=0)
            return
        state = self.session.state
        scene = music_scene(state, home=self.home_mode)
        context = None if self.home_mode else id(state)
        if self.home_mode or not state.run_over:
            self._audio_skipped_run = None
        elif getattr(self, '_audio_skipped_run', None) is state:
            sfx.stop_music(fade_ms=150)
            return
        if not sfx.request_music(scene.track, loops=scene.loops, context=context) and scene.fallback:
            sfx.request_music(scene.fallback, loops=scene.loops, context=context)

    async def on_event(self, event) -> None:
        # 关窗确认框被取消后 WezTerm 的标题不会自动恢复；用玩家下一次真实
        # 键鼠输入作为「提示已消失」的信号，恢复地图图像层。
        if getattr(self, '_native_prompt_suppressed', False):
            from textual import events
            if isinstance(event, (events.Key, events.MouseEvent)):
                self._release_native_prompt_suppression()
        await super().on_event(event)

    def _world_view_live(self) -> bool:
        """世界画面是否仍然「活着」：可见、可交互，时间可以推进。

        2026-10-26 的 ~ 锁定语义只冻结右栏当前页，世界行动照旧——方向键与
        小键盘数字始终移动角色（key_routing._should_move_map_with_keys），
        点击地图寻路/攻击也不再把 panel_mode 改回 world（mouse_routing），
        锁定时面板页更不会因为行动自动回跳。所以 RIGHT_PANEL_MODES 下的世界
        必须继续推进 FX 时钟、长按自动移动与平滑采样；旧实现把
        「panel_mode != "world"」一律当成冻结，命中跳字/涟漪/施法波就会在
        锁定页里永远停在屏幕上。

        真正的冻结只有全屏模态：panel_mode 不在 RIGHT_PANEL_MODES（暂停 /
        设置 / 图鉴 / 联想盘 / 主页子页 / 事件对话 / 左浮层等）、观察模式
        与层观测。观察与层观测的指令不落地、时间静止，所以不能算「活着」。

        ⚠️ 终局与进层演出不在这里判：_fx_tick 顶部已有 _floor_transition
        早退、run_over 在 FX 分支里清场；_refresh_game_frame 在结算演出
        期间仍要推进地图刷新。调用方各自保持原来的语义。
        """
        if self.home_mode or self.observe_mode:
            return False
        if getattr(self, "layer_observation", None) is not None:
            return False
        mode = getattr(self, "panel_mode", "world")
        return mode == "world" or mode in RIGHT_PANEL_MODES

    def _refresh_game_frame(self) -> None:
        self._expire_attack_confirmation()
        # 节流自动存档：动作标记的脏状态按回合间隔（10 回合）落盘（30fps 下检查成本可忽略）
        was_dirty = self.session._dirty
        if getattr(getattr(self, "_driver", None), "is_headless", False):
            # 测试/无头环境保持同步，避免文件断言与后台线程竞态。
            self.session.flush_pending_save()
        else:
            self.session.flush_pending_save_async()
        if not self.is_running:
            # 拆卸窗口：Textual 的 `_shutdown` 第一件事就是 `_running = False`，然后
            # 逐个卸载子控件，最后才派发 App.on_unmount（那里停表）。定时器可能在这
            # 段窗口里进来一次：存档照常落盘（卸载时 save_and_exit 还会兜底），
            # 但任何 DOM 访问都不做。
            return
        # 关窗确认框期间地图图像层必须收起；30fps 检查一次，不等下一次地图重绘。
        self._guard_native_close_prompt()
        if getattr(self, '_native_prompt_suppressed', False):
            return
        if was_dirty != self.session._dirty:
            self._refresh_qol()
        # 临时弹窗动画/倒计时。（控件引用缓存：见 __init__ 的 C9 说明）
        toast = self._frame_widget("_frame_toast", FloatingToast)
        toast_shown = False
        if toast is not None:
            toast_shown = bool(toast.tick())
        state = self.session.state
        # 标题栏播报：事件记录出现新消息 → 顶部滚动播报 3 秒（2026-09-19）。
        # 3 秒内再来新消息立即切入；结束后没有其他事件则还原标题。
        visible_messages = self._visible_game_messages(state)
        new_message = bool(visible_messages and visible_messages[-1] != self._seen_event_message)
        if new_message:
            self._seen_event_message = visible_messages[-1]
            self._push_header_ticker(self._seen_event_message)
        # 异象蓄力/准备类提示的独立通道（2026-10-12）：不进事件记录，只上顶部
        # 滚动。每帧最多播一条：连发时逐帧切入，跑马灯不会把前一条瞬间顶掉。
        pending_ticker = bool(state.ticker_notes)
        if pending_ticker:
            self._push_header_ticker(state.ticker_notes.pop(0))
        # 结算演出（run_over && ending_id）：帧推进；教程卡/地图高亮随帧同步。
        settlement = self._frame_widget("_frame_settlement", SettlementScreen)
        settlement_active = bool(settlement is not None and settlement.active)
        if settlement_active:
            settlement.tick()
        tutorial_active = bool(getattr(state, "tutorial", {}).get("active"))
        if not self.home_mode and self.panel_mode != "home" and not getattr(state, "run_over", False):
            self._tutorial_frame()
        # 爆炸动画老化：每帧 +1，6 帧后清除（黄→橙红→深红→消失）。
        explosion = bool(getattr(state, "explosion_cells", None))
        if explosion:
            state.explosion_age += 1
            if state.explosion_age > 6:
                state.explosion_cells = set()
                state.explosion_age = 0
        if not self.is_running or not self.is_mounted or not self._world_view_live():
            # 全屏模态/观察/层观测才停：右栏面板（含 ~ 锁定页）下世界仍可行动，
            # 长按自动移动与平滑采样必须继续（2026-10-28 修复面板冻结）。
            self._sync_presentation_timer(False)
            if self._held_key is not None:
                self._clear_held()
            movement = getattr(self, "_movement_presentation", None)
            if movement is not None and movement.is_active(time.monotonic()):
                map_view = getattr(self, "_frame_map", None)
                viewport = getattr(map_view, "viewport", (0, 0, 1, 1))
                player = self.session.state.player
                movement.reset((player.x - viewport[0], player.y - viewport[1]))
                self._movement_presentation_viewport = None
                self._movement_presentation_needs_final_frame = False
            return
        self._auto_repeat_move()
        map_view = self._frame_widget("_frame_map", MapView)
        if map_view is None:
            return
        movement = getattr(self, "_movement_presentation", None)
        try:
            smooth_enabled = (bool(self.config.get("smooth_movement"))
                              and not bool(self.config.get("fx_reduce_motion"))
                              and map_view.display_mode == "image")
        except (AttributeError, KeyError, TypeError):
            smooth_enabled = False
        now = time.monotonic()
        smooth_active = bool(
            smooth_enabled and movement is not None and movement.is_active(now)
            and self._movement_presentation_viewport == map_view.viewport)
        if movement is not None and movement.is_active(now) and not smooth_active:
            player = self.session.state.player
            movement.reset((player.x - map_view.viewport[0],
                            player.y - map_view.viewport[1]))
            self._movement_presentation_viewport = None
            self._movement_presentation_needs_final_frame = True
        self._sync_presentation_timer(smooth_active)
        force_presentation_frame = bool(
            smooth_active or self._movement_presentation_needs_final_frame)
        if self._movement_presentation_needs_final_frame and not smooth_active:
            self._movement_presentation_needs_final_frame = False
        # C9 空闲帧分频：上面的簿记（存档 flush/攻击确认/toast/结算/爆炸老化/
        # 教程/跑马灯/auto_repeat）始终每帧跑；只有「确认没有动态来源」时才把
        # 地图 update_state 降到 1/DIV。动作后的 refresh_view 不受影响。
        if (not force_presentation_frame and self._idle_frame_skips_map_refresh(
                toast_shown=toast_shown, settlement_active=settlement_active,
                new_message=new_message, pending_ticker=pending_ticker,
                explosion=explosion, tutorial_active=tutorial_active,
                map_view=map_view)):
            return
        map_view.symbol_mode = self._symbol_mode()
        # 目标辅助路径同步（每帧；帧签名含路径集合，未变化时不会重渲染）。
        if (self.target_assist or self.aiming) and self.assist_path:
            map_view.assist_cells = set(self.assist_path)
        elif map_view.assist_cells:
            map_view.assist_cells = None
        map_view.update_state(self.session.state)
        if force_presentation_frame:
            # update_state 的同场景快捷路径可能因 interaction signature 未变而
            # 不调用 Static.update；动画采样本身虽变，需显式调度一次地图重绘。
            # 平滑中间帧只需要一次「有序显示事务」把新采样位置通过图像写出：
            # 整块地图重排（52×29 格）每帧要 ~28ms，而脏格补丁只依赖
            # _map_damage 与本帧图像。仅当采样帧补丁路由开着时才只标一格的脏区
            # （补丁会把图像补回来）；路由关着必须整块刷新，否则文字层留半旧。
            native_plane = getattr(self, '_native_image_plane', None)
            if (smooth_active and native_plane is not None
                    and not getattr(native_plane, 'error', '')):
                # 原生图像层在 worker 侧按 duration 与 _PlaneMotion 自行插值，
                # 显示采样帧不需要经过 Textual 事务。旧实现每 1/30 秒整块
                # refresh 一次空白占位层，等于让合成器每步多排 3–4 次整张地图
                # （2026-10-26 实测：移动步内 map refresh 3–4 次、_render_chops
                # 16–30ms/次）。worker 已有本步画布，直接跳过即可。
                return
            if smooth_active and (self.smooth_patch_routes_enabled()
                                  or map_view.display_mode == 'image'):
                # M3：先试 mini 事务直接贴采样补丁（完全绕开整屏合成周期）；
                # 任何 guard 不满足再退回「一格脏区」的常规显示事务。
                if map_view.try_emit_presentation_frame():
                    return
                # 用内容区左上角的一格作为脏区：装饰边框本身不在图内，标错了
                # _display 会判成「无地图 damage」而丢掉这次采样。
                content = map_view.content_region
                widget = map_view.region
                map_view.refresh(Region(
                    max(0, content.x - widget.x), max(0, content.y - widget.y), 1, 1))
            else:
                map_view.refresh()

    def _sync_presentation_timer(self, smooth_active: bool) -> None:
        """P3：平滑轨迹期间 resume 独立采样定时器，轨迹结束时 pause。"""
        timer = getattr(self, "_presentation_timer", None)
        if timer is None:
            return
        try:
            wanted = bool(smooth_active and self.presentation_timer_enabled())
        except (AttributeError, KeyError, TypeError):
            wanted = False
        if wanted == self._presentation_timer_running:
            return
        if wanted:
            # reset() 同时恢复调度：暂停期间累积的错过的周期必须丢弃，
            # 否则 Timer 会按 25ms 步长逐个补跑（长时间空闲后是上千次空转）。
            timer.reset()
        else:
            timer.pause()
        self._presentation_timer_running = wanted

    def _presentation_tick(self) -> None:
        """P3：独立采样回调——只写采样帧，不推进节拍、不结算规则、不碰 _display。

        回调里唯一的重活是 ``image_frame`` + 直写；任何 guard 不满足就直接
        返回，让常规 30Hz 帧回调负责这一帧，不在这里兜底刷新。
        """
        movement = getattr(self, "_movement_presentation", None)
        if (not self.is_running or not self.is_mounted
                or not self._world_view_live()
                or movement is None or not movement.is_active(time.monotonic())):
            self._sync_presentation_timer(False)
            return
        map_view = self._frame_widget("_frame_map", MapView)
        if map_view is None or map_view.display_mode != "image":
            self._sync_presentation_timer(False)
            return
        if getattr(self, "_movement_presentation_viewport", None) != map_view.viewport:
            return
        map_view.try_emit_presentation_frame()

    def _frame_widget(self, cache_attr: str, widget_type):
        """帧循环里的控件引用（带缓存）：三个控件在 compose 里一次挂载、生命周期同 App。"""
        widget = getattr(self, cache_attr, None)
        # 缓存外复核 is_mounted：将来若页面被 recompose，旧引用不能把动画
        # 静默卡死（_home_tick 会一直拿到已卸载控件）。失配时回退重新查询。
        if widget is not None and not widget.is_mounted:
            widget = None
            setattr(self, cache_attr, None)
        if widget is None:
            widget = next(iter(self.query(widget_type)), None)
            if widget is not None:
                setattr(self, cache_attr, widget)
        return widget

    def _idle_frame_skips_map_refresh(self, *, toast_shown: bool, settlement_active: bool,
                                      new_message: bool, pending_ticker: bool,
                                      explosion: bool, tutorial_active: bool,
                                      map_view) -> bool:
        """C9：这一帧是否可以跳过地图 update_state。

        只有确认没有动态来源时才按 DIV 分频；任何动态来源都立即复位相位，
        让下一帧立刻刷新（不会出现「刚有变化却仍按旧相位跳过」）。
        """
        divisor = self._idle_frame_div
        if divisor <= 1 or self._map_frame_is_dynamic(
                toast_shown=toast_shown, settlement_active=settlement_active,
                new_message=new_message, pending_ticker=pending_ticker,
                explosion=explosion, tutorial_active=tutorial_active,
                map_view=map_view):
            self._idle_frame_phase = 0
            return False
        self._idle_frame_phase = (self._idle_frame_phase + 1) % divisor
        return self._idle_frame_phase != 0

    def _map_frame_is_dynamic(self, *, toast_shown: bool, settlement_active: bool,
                              new_message: bool, pending_ticker: bool,
                              explosion: bool, tutorial_active: bool,
                              map_view) -> bool:
        """地图这一帧是否有动态来源（C9 的「不跳过」白名单）。

        注意 _fx_active 不在这里：它是「FX 画布开着」的常驻标记，正常游玩中
        20Hz 的 _fx_tick 每帧都会把它置真（实测空闲时也为 True）。真正的动态
        来源是下面的瞬时 FX 队列（弹道/粒子/战斗脉冲/波纹/短光/命中涟漪）。
        """
        if self.home_mode or self.panel_mode != "world":
            # 面板/主页帧一律按动态处理，不参与 C9 分频（既有语义：面板内容
            # 可能随世界状态变化；tests/test_idle_gc_261022.py 钉住这一点）。
            return True
        if self._held_key is not None or getattr(self, "_held_direction", None) is not None:
            return True
        if self.aiming or self.observe_mode or self.target_assist:
            return True
        if getattr(self, "sentence_aim", None) is not None:
            return True
        if (self.path or getattr(self, "observe_walk_path", None)
                or getattr(self, "assist_path", None)):
            return True
        if (getattr(self, "_fx_projectile", None) or self._map_particles.pending
                or getattr(self, "_fx_combat_pulses", None)
                or getattr(self, "_fx_hits", None)
                or getattr(self, "_fx_waves", None)
                or getattr(self, "_fx_flashes", None)):
            return True
        if getattr(self, "_floor_transition", None) is not None:
            return True
        if getattr(self, "pending_confirmation", None):
            return True
        if toast_shown or settlement_active or new_message or pending_ticker:
            return True
        if explosion or tutorial_active:
            return True
        if getattr(self.session.state, "run_over", False):
            return True
        if (getattr(map_view, "preview_tints", None)
                or getattr(map_view, "preview_marks", None)
                or getattr(map_view, "preview_boundary", None)):
            return True
        return False

    def on_unmount(self) -> None:
        painter = getattr(self, "_world_painter", None)
        if painter is not None:
            painter.close()
            self._world_painter = None
        plane = getattr(self, '_native_image_plane', None)
        if plane is not None:
            plane.close()
            self._native_image_plane = None
        layer = getattr(self,'layer_observation',None)
        if layer is not None and layer.context == self._layer_context():
            self.session.state.hover_target = layer.previous.get('_world_hover_target')
        self.layer_observation = None
        self._map_packets = []
        self._map_packet_image = None
        audio_timer = getattr(self, '_audio_timer', None)
        if audio_timer is not None:
            audio_timer.stop()
        if self._home_timer is not None:
            self._home_timer.stop()
        if self._game_frame_timer is not None:
            self._game_frame_timer.stop()
        if self._presentation_timer is not None:
            self._presentation_timer.stop()
            self._presentation_timer_running = False
        if not self.home_mode and not self.session.state.run_over and not self.save_disabled:
            self.session.save_and_exit()
        # 停掉音乐并释放音频设备（内部全降级，未初始化时是空操作）。
        sfx.shutdown()
        # 取消启动时的 `gc.freeze()`：永久代里的对象不再参与回收，进程若继续活着
        # （测试是同一进程连开多个 App，真实场景是退出）会把旧控件树一直钉在内存里。
        if getattr(self, "_gc_frozen", False):
            self._gc_frozen = False
            try:
                gc.unfreeze()
            except Exception:
                pass
