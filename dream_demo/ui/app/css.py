"""DreamApp 的样式表（CSS 类属性）。"""
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

class AppCssMixin:
    """DreamApp 的样式表（CSS 类属性）。"""

    CSS = """
    Screen { background: #101018; layers: default overlay tamper toast confirmation help inspection; }
    #signal-status { height: 1; width: 100%; }
    #signal-status:focus { text-style: underline; }
    #signal-detail { display: none; layer: inspection; position: absolute;
        border: round #8297a7; padding: 0 1; background: #292930; }
    #signal-detail-title { height: 1; color: #d9e7f5; text-style: bold; }
    #signal-detail-scroll { height: 1fr; scrollbar-size-vertical: 1; }
    #signal-detail-text { height: auto; }
    #signal-listen { height: 1; color: #dfcfaa; text-style: underline; }
    #signal-listen:hover, #signal-listen:focus { color: #f1dfad; }
    #signal-detail-close { height: 1; color: #70cbbb; text-style: underline; }
    # 键位表 / 确认层（2026-10-21 E3）：宽高与位置由 `_overlay_stage` +
    # `_fit_controls_help` / `_refresh_qol` 在打开时按可用区写入——游戏内是地图区，
    # 右栏与底栏因此保持可见；全屏页则退到页面自身区域。这里只留「还没算过」时
    # 的兜底几何，不要在这写 90% 全屏尺寸（旧的 90% 会把右栏整块盖住）。
    # 中文宽字：合成器会按背景控件边界切行，跨切口的双宽字变成两个空白半格；
    # 浮层整个落在一个背景控件里 + `_occlude_under` 只隐藏面板下面那点背景，
    # 两条一起保证字符不断裂（不要改回「隐藏全部同级控件」）。
    #controls-help { display: none; layer: help; position: absolute; width: 100%; height: 100%;
        offset: 0 0; padding: 1 2; border: solid #8297a7; background: #181b24; }
    #controls-help-title { height: 2; color: #dfcfaa; text-style: bold; }
    #controls-help-scroll { height: 1fr; }
    #controls-help-text { height: auto; }
    #controls-help-close { height: 1; width: 100%; min-width: 0; padding: 0;
        border: none; background: #181b24; color: #c8b478; }
    #controls-help-close:hover, #controls-help-close:focus { background: #252a35; color: #f1dfad; }
    #layout { height: 1fr; }
    # 左侧面板（格子详情 / 物品菜单 / 意象详情，都是下面那个 #map-overlay 浮层）
    # 要在左边框里居中，靠的是容器自己的 align：Textual 对齐的是「同一 layer 内
    # 所有子节点并集的包围盒」。浮层带 layer: overlay、单独成层，那一层只有它
    # 自己，于是 align 精确地把浮层居中；#map 在 default 层且占满整块内容区，
    # 包围盒=内容区，对齐对它没有任何位移。
    # 浮层因此不能再写 position: absolute——那会让 Textual 把它的包围盒归零回
    # (0,0)，align 算出的居中位移被直接丢掉（旧实现就是这样一直靠左的）。
    # 🔴 面板底色（2026-09-21 三改，玩家定稿）：右侧面板 / 左侧浮层 / 消息气泡
    # **共用同一个色**，且**随所在区域换**（`RegionTheme.panel_bg`）——
    # 这是现在唯一的「区域识别色」：地图已经统一黑（见下面 #map-pane 的说明），
    # 玩家靠面板色 + 顶栏色 + 边框色判断自己到了哪一区。
    # 必须是**不透明**纯色：Textual 的合成器会把 alpha 与下层预混，写 92% 之类
    # 反而会把地图的颜色透上来，最后既不是面板色、深浅还随地图内容变。
    # 这里写的 #292930 只是**主页 / 未应用主题时的兜底**（= region_themes
    # .DEFAULT_PANEL_BG）：进游戏后 `_apply_region_theme` 会把三处一起改成
    # 当地区域的面板色，所以别指望这里的值在游戏内可见。
    # 五档取值与亮度/对比度的验收口径都记在 `region_themes.RegionTheme.panel_bg`。
    # ⚠️ 面板边框**不在这里定**：进游戏后由 _apply_region_theme 按区域主题重写
    # （round/#8a7ac8 等），改这里的 border 只在主页生效、游戏内看不出变化。
    # ⚠️ #map-pane 的底色**也不在这里**写：它由 _apply_region_theme 统一写成
    # `MAP_BG`（全区域黑）。那一圈（边框 + padding）必须由地图面板**自己**上色，
    # 不能靠「透明 → 透出 Screen 底色」间接得到——见 `_apply_region_theme` 的注释。
    #map-pane { width: 2fr; border: round #44445c; padding: 1; align-horizontal: center; align-vertical: middle; layers: default self_audit overlay tamper toast; }
    # 自我察觉：地图内居中悬浮（map-pane 的 align 负责居中；layer 独立成层
    # 不挤压地图——不写 position: absolute，见 #map-overlay 的同类注释）。
    #self-pane { layer: inspection; position: absolute; width: 92%; max-height: 88%;
                 border: round #44445c; padding: 1; background: #292930;
                 scrollbar-size-vertical: 1; }
    #self-audit-body { width: 100%; }
    #side-pane { width: 1fr; min-width: 55; border: round #44445c; padding: 1; background: #292930; }
    Screen.qol-medium #side-pane { width: 44; min-width: 44; padding: 0 1; }
    Screen.qol-compact #side-pane { width: 36; min-width: 36; padding: 0 1; }
    Screen.qol-compact #map-pane { padding: 0; }
    Screen.qol-compact #panel-tabs, Screen.qol-compact #panel-tabs Button { height: 1; padding: 0; border: none; }
    Screen.qol-compact #panel-help { max-height: 2; overflow: hidden; }
    #nav-tasks { color: #67e8f9; background: #132a30 55%; border: none; }
    #nav-tasks:hover, #nav-tasks:focus { background: #132a30 85%; border: none; }
    #qol-confirm-dialog { display: none; layer: confirmation; position: absolute; width: 100%; height: 100%;
        offset: 0 0; padding: 1 2; align: center middle; border: solid #8297a7; background: #181b24; }
    #qol-confirm-text { width: 100%; height: 1fr; text-align: center; overflow-y: auto; }
    #qol-confirm-buttons { width: 100%; height: 1; margin-top: 1; align-horizontal: center; }
    #qol-confirm-buttons Button { width: 1fr; min-width: 0; height: 1; padding: 0;
        border: none; background: #181b24; color: #b3beca; }
    #qol-confirm-buttons Button:hover, #qol-confirm-buttons Button:focus { background: #252a35; }
    #qol-confirm-yes { color: #d99587; }
    #qol-search-input { display: none; width: 100%; height: 3; }
    #map { height: 1fr; content-align: left top; }
    #debug-panel {
        layer: overlay;
        width: 92%;
        height: 78%;
        padding: 1 2;
        background: #101018 96%;
        border: round #3ddad0;
        color: #ffffff;
        display: none;
    }
    #debug-left { width: 1fr; overflow-y: auto; }
    #debug-right { width: 2fr; overflow-y: auto; }
    #debug-divider { width: auto; color: #3ddad0; }
    #map-overlay {
        layer: overlay;
        # 2026-10-11 自适应：宽高按内容收缩（auto），上限由 _fit_map_overlay
        # 按 #map-pane 的内容尺寸动态钳制——字多的面板自动拉长，但整个浮层
        # （含边框与 padding）不超过地图长宽，超出部分交给 overflow-y 滚动。
        width: auto;
        height: auto;
        max-width: 100%;
        max-height: 100%;
        padding: 1 2;
        # 同 #side-pane 的面板色（旧值 #101018 92% 与地图底几乎同色，且带 alpha
        # 会被合成器预混成地图色，浮层看不出边界）。
        # 这里只是兜底值（= region_themes.DEFAULT_PANEL_BG）：进游戏后由
        # `_apply_region_theme` 改成当地区域的面板色。
        background: #292930;
        border: round #59627a;
        color: #ffffff;
        overflow-y: auto;
        display: none;
    }
    # 篡改旁侧面板（规格 §4.2）：与 #map-overlay 同主题同边框，但**自己算位置**
    # ——先选完整放得下的较大空闲区，再移原框，最后叠放；使用显式位置和尺寸
    # （与 TutorialCard 同一套手法）。内容按 ui.tamper_layout 的宽度排好再写回，
    # 命中映射才与屏幕行列对得上；padding 固定 0 1，横向装饰共 4 格、纵向 2 格。
    #tamper-overlay {
        layer: tamper;
        position: absolute;
        padding: 0 1;
        background: #292930;
        border: round #59627a;
        color: #ffffff;
        overflow: hidden;
        display: none;
    }
    #status { height: 5; color: #ffffff; }
    # 五个文字导航按钮共占一行；业务快捷键保留原目标。
    #panel-sections { height: 1; }
    #panel-sections Button {
        width: auto; min-width: 0; height: 1; padding: 0; border: none;
        background: transparent; color: #bcc5d6;
    }
    #panel-tabs Button.sidebar-active, #panel-sections Button.sidebar-active {
        text-style: bold underline; background: #30354b;
    }
    #panel-tabs { height: 1; }
    #panel-tabs Button { width: 1fr; min-width: 0; height: 1; margin: 0; padding: 0; content-align: center middle; text-align: center; }
    # 五区沿用既有类别色，用底色亮度区分悬停和聚焦。
    #nav-inventory { color: #44aaff; background: #132534 55%; border: none; }
    #nav-equipment { color: #ffd166; background: #2b2413 55%; border: none; }
    #nav-portents { color: #c9a0ff; background: #241a33 55%; border: none; }
    #nav-actions { color: #ff8c42; background: #2f2117 55%; border: none; }
    # 悬停/聚焦时同色底色提到 85%。
    # Button 自带的 :hover/:focus 会换成主题色，这里按 id 覆盖回来。
    #nav-inventory:hover, #nav-inventory:focus { background: #132534 85%; border: none; }
    #nav-equipment:hover, #nav-equipment:focus { background: #2b2413 85%; border: none; }
    #nav-portents:hover, #nav-portents:focus { background: #241a33 85%; border: none; }
    #nav-actions:hover, #nav-actions:focus { background: #2f2117 85%; border: none; }
    # 当前对象沿用旧版完整地形叙述，按实际列宽自动换行。
    #layout { layers: default overlay toast; }
    #map-hints > * { layer: default; }
    #hover-info { height: auto; color: #ffffff; }
    #sidebar-tools { height: 1; }
    #sidebar-tools Button { width: auto; min-width: 0; height: 1; padding: 0; border: none; background: transparent; color: #bcc5d6; }
    #sidebar-tools Button:hover { text-style: bold underline; }
    #panel { height: 1fr; color: #ffffff; overflow-y: auto; }
    # 键位提示高度自适应：操作界面的长提示自动折行完整显示。
    # ⚠️ 「次要文字」的灰是**三档对比度色阶**（口径 = 对**最亮的那档面板**
    # `#242e35` 也 ≥4.5；取值与实测都记在 styles.py 的对比度色阶一节）：
    #   · 面板上的正文 → `#ffffff` 13.8（亮白，与面板底色一眼分得开）；
    #     次要说明/键位提示 → `#aab0c2`（第十九节注册表 `muted`，最亮面板 5.65）；
    #   · 黑底整屏页（主页/暂停/设置/图鉴/历史）上的次要文字 → 同一个 `#aab0c2`；
    # 🔴 旧的 `#696b82` 在黑底上只有 3.63、在面板上 2.75 —— 两处都不够，已弃用；
    # 它当年被留在主页/暂停只是「黑底上凑合」，玩家反馈读不清后一并提到 4.5 以上。
    #panel-help { height: 1; overflow: hidden; color: #aab0c2; text-align: center; }
    #panel-help:hover { color: #eeeeff; text-style: underline; }
    #home { display: none; height: 1fr; align: center middle; color: #ffffff; layers: dream content buttons; }
    #home-title, #home-subtitle, #home-menu, #history-page, #newgame-page { layer: content; }
    .home-center-row { width: 100%; height: auto; align-horizontal: center; layer: content; }
    #home Button { layer: buttons; }
    # 全屏暂停菜单（2026-09-20）：与 #home 同构的整屏容器——打开时隐藏 #layout，
    # 地图与左右面板整体让位；底栏（Footer）保留，键位常驻是硬要求。
    # 二次修订：标题用主页同款 60 列边框牌匾、选项改成 3 行高的按钮块并留
    # 空行间距——终端字号改不了，用「块大 + 加粗 + 空隙」放大视觉。
    #pause-menu { display: none; height: 1fr; align: center middle; color: #ffffff; }
    #pause-box { width: 60; height: auto; align-horizontal: center; }
    #pause-title { width: 60; height: 3; }
    #pause-list { width: 60; height: auto; margin-top: 2; align-horizontal: center; }
    # 选项块：宽 36 高 3（与主页按钮同构——边框常驻占位、选中才亮边），
    # 块间距 1 行空隙；hover/selected 用同一套亮边，键鼠光标共用。
    .pause-option { width: 36; height: 3; margin-bottom: 1; content-align: center middle; text-align: center; background: #101018; border: round #101018; color: #ffffff; }
    .pause-option:hover { background: #1a1a27; border: round #5b67a0; }
    .pause-option.selected { border: round #3ddad0; text-style: bold; color: #ffffff; }
    #pause-help { width: 60; height: 1; text-align: center; color: #aab0c2; margin-top: 1; }
    #home-title { width: 60; height: 3; text-align: left; text-style: bold; color: #67e8f9; content-align: left middle; }
    #home-subtitle { width: 60; height: 1; text-align: center; color: #aab0c2; }
    Screen.qol-short-home #home-menu { margin-top: 0; }
    # 标题与菜单共用 60 列居中轴，左右留给独立背景层的门柱与雾流。
    #home-menu { width: 60; height: auto; margin-top: 1; align-horizontal: center; }
    #home-content { width: 60; height: auto; min-height: 3; text-align: center; margin-bottom: 1; }
    .slot-row { width: 60; height: 3; margin-bottom: 1; }
    # 46 + 14 = 60。Button 默认只有上下边框（无左右边框），内容区宽 = width，
    # 「删除」占 4 格，取偶数宽 14 才能左右各留 5 格，真正居中。
    # 主页选项默认无边框（边框颜色 = 背景色，占位不显形），选中/悬停才亮边。
    # 边框始终占位（而不是 none↔round 切换），避免悬停时按钮文字抖动。
    # 背景与主页底色（Screen #101018）一致：存档槽融进页面，不靠色块抢视线，
    # 选中与否只由边框表达。
    .slot-main { width: 46; height: 3; margin: 0; content-align: center middle; text-align: center; background: #101018; border: round #101018; color: #ffffff; }
    .slot-main:hover, .slot-main:focus { background: #1a1a27; border: round #5b67a0; }
    .slot-main.selected { border: round #5b67a0; }
    # Button 默认 min-width:16，会顶掉这里的 width:14 并把整行撑到 62 列（超出 60 的部分被裁切），
    # 使「删除」看起来偏右。显式归零 min-width 后宽度才是真正的 14。
    # 删除键不占边框位（60 列行宽与「内容 14 列」的居中断言都按无边框设计），
    # 悬停/聚焦时才临时加边框（内容轻微回缩可接受）。
    .slot-delete { width: 14; min-width: 0; height: 3; margin: 0; content-align: center middle; text-align: center; border: none; }
    .slot-delete:hover, .slot-delete:focus { border: round #a0453a; }
    .home-nav-row { width: 60; height: 3; }
    .home-nav-row Button { width: 1fr; min-width: 0; height: 3; margin: 0; padding: 0 1; content-align: center middle; text-align: center; }
    # 主页导航按钮按功能着色（与游戏内右侧面板的界面色一致，2026-10-09 消重：
    # 回忆原与入梦同为 #9ad1c9，改用记忆碎片紫 #b18cff，六项两两可辨）。
    #home-history { background: #251b31; color: #c5a3df; border: round #251b31; }
    #home-history:hover, #home-history:focus { border: round #c5a3df; }
    #home-catalog { background: #2b2516; color: #e8c77b; border: round #2b2516; }
    #home-catalog:hover, #home-catalog:focus { border: round #e8c77b; }
    #home-settings { background: #172432; color: #94bdd9; border: round #172432; }
    #home-settings:hover, #home-settings:focus { border: round #94bdd9; }
    #home-exit { background: #2c1b1b; color: #d99587; border: round #2c1b1b; }
    #home-exit:hover, #home-exit:focus { border: round #d99587; }
    # 键盘光标（home_row/home_column）所在的主页选项：亮边 + 加粗，规则写在 hover
    # 之后同权重时后者生效；选择器带 id 故优先级高于上面的默认底色边框。
    .slot-delete.selected { border: round #a0453a; }
    #home-main { width: 60; height: auto; }
    #home-main Button { width: 100%; }
    #home-enter { background: #162820; color: #9ad1b3; border: round #162820; }
    #home-enter:hover, #home-enter:focus { border: round #9ad1b3; }
    #home-enter.selected { border: round #9ad1b3; text-style: bold; }
    #home-saves { width: 60; height: auto; }
    #saves-help { width: 100%; text-align: center; color: #aab0c2; }
    #home-catalog.selected, #home-settings.selected, #home-exit.selected { text-style: bold; }
    #home-catalog.selected { border: round #e8c77b; }
    #home-settings.selected { border: round #94bdd9; }
    #home-exit.selected { border: round #d99587; }
    # 测试模式行键盘选中态（与导航行同款：亮边 + ▶ 前缀）。
    #test-mode { border: round #2a2a3a; }
    #test-mode.selected { border: round #3ddad0; text-style: bold; }
    #codex-page { display: none; position: absolute; width: 100%; height: 100%; padding: 1 2; layer: overlay; }
    # 旧梦回忆页：列表占满、底部常驻「游玩 N 次 · 通关 M 次」（总计数不受列表上限影响）。
    #history-page { display: none; width: 100%; height: 1fr; padding: 1 2; }
    # 开局选项页（2026-10-09）：与历史/图鉴同构的整屏文本页；内容是一块居中的
    # 静态文本（滑条/开关/难度条全靠文本渲染，键位操作，不做鼠标行命中）。
    #newgame-page { display: none; width: 100%; height: 1fr; padding: 0 2; }
    #newgame-steps { height: 1; color: #9aa8b8; text-align: center; }
    #newgame-summary { width: 100%; height: auto; min-height: 3; max-height: 5; padding: 0 1; background: #101724; }
    #newgame-body { width: 100%; height: 1fr; layout: horizontal; }
    #newgame-scroll { width: 100%; height: 1fr; border: round #526781; background: #142031; }
    #newgame-body #newgame-scroll { width: 2fr; height: 100%; }
    #newgame-content { width: 100%; height: auto; padding: 0 1; }
    #newgame-detail { height: 100%; width: 1fr; padding: 0 1; border: round #526781; background: #101724; overflow-y: auto; }
    #newgame-body.compact { layout: vertical; }
    #newgame-body.compact #newgame-scroll { width: 100%; height: 1fr; }
    #newgame-body.compact #newgame-detail { width: 100%; height: auto; min-height: 3; max-height: 6; }
    #newgame-actions { height: 3; width: 100%; }
    #newgame-actions Button { width: 1fr; min-width: 0; height: 3; margin: 0; padding: 0 1; content-align: center middle; background: #10222a; color: #9ad1c9; border: round #364d5f; }
    #newgame-actions Button:hover, #newgame-actions Button:focus { background: #1a2937; border: round #9ad1c9; text-style: bold; }
    #newgame-actions #newgame-next { background: #241f10; color: #e5c780; border: round #786744; }
    #newgame-actions #newgame-next:hover, #newgame-actions #newgame-next:focus { background: #302817; border: round #f1d9a0; }
    #newgame-actions Button:disabled { color: #637184; background: #101724; border: round #263343; }
    #newgame-help { height: 2; color: #9aa8b8; text-align: center; }
#newgame-seed-row { height: 3; display: none; padding: 0 2; align-vertical: middle; }
#newgame-seed-label { width: auto; color: #c8b98d; padding: 1 2 0 0; }
#newgame-seed { width: 1fr; max-width: 36; }
#newgame-seed-row.-visible { display: block; }
    #history-list { width: 100%; height: 1fr; overflow: hidden; }
    #history-total { width: 100%; height: 1; color: #3ddad0; text-align: center; }
    #history-help { width: 100%; height: 1; color: #aab0c2; text-align: center; }
    # 设置页从 #home 里移出、挂到 Screen 顶层（2026-09-20）：暂停菜单也要打开它，
    # 而 #home 在游戏内是隐藏的。改为 overlay 层的全屏覆盖——主页打开时盖住标题
    # （主页/暂停共用同一份设置 UI，视觉一致），游戏内打开时盖住整个界面。
    # display 与 panel_mode 的同步在 refresh（_refresh_home_view / 暂停路径）里。
    #settings-page { display: none; position: absolute; width: 100%; height: 100%; padding: 1 2; layer: overlay; }
    #catalog-categories { height: 3; }
    #catalog-categories Button { width: 1fr; min-width: 0; height: 3; margin: 0; padding: 0 1; }
    #codex-body { height: 1fr; }
    #codex-list { width: 2fr; height: 1fr; min-width: 24; border: round #625f36; padding: 1; overflow: hidden; }
    #codex-detail { width: 3fr; height: 1fr; min-width: 36; padding-left: 1; overflow-y: auto; }
    #codex-help { height: 1; color: #aab0c2; text-align: center; }
    #codex-too-small { display: none; height: 1fr; content-align: center middle; color: #d6a94d; }
    #settings-list { width: 100%; height: 1fr; border: round #365d62; padding: 1 2; overflow-y: auto; }
    .setting-row { width: 100%; height: auto; min-height: 1; }
    #settings-feedback { width: 100%; height: auto; min-height: 1; margin-top: 1; color: #aab0c2; }
    # 携带意象·联想盘的独立编辑器（2026-10-09，设计方案 §8.2/§8.4）：与设置页
    # 同构的整屏 overlay——打开时 #layout 隐藏，地图与左右面板整体让位，键鼠输入
    # 全部被编辑器模态吃掉，一步都不会串到地图上。底栏（Footer）保留。
    # 高度预算：标题 1 + 盘面/说明 1fr + 工具栏 auto + 键位提示 auto；80×24 下
    # 完整 6 行盘面与「确认整理／取消」都可见，说明区自己滚动。
    #board-editor { display: none; position: absolute; width: 100%; height: 100%; padding: 0 1; layer: overlay; }
    #board-editor-title { width: 100%; height: 2; color: #ffd166; text-style: bold; }
    #board-editor-body { width: 100%; height: 1fr; }
    # 盘面控件自带命中表，宽度按内容（每逻辑格两终端列，见 board_editor.GRID_ORIGIN_X）。
    #board-editor-grid { width: auto; height: auto; }
    #board-editor-map { width: 22; height: 1fr; }
    #board-editor-inspect { width: 100%; height: 1fr; overflow-y: auto; color: #b2bacb; }
    #board-editor-main { width: 1fr; height: 1fr; }
    #board-editor-grammar { height: auto; margin-bottom: 1; }
    #board-editor-status { height: auto; margin-bottom: 1; }
    #board-editor-scroll { width: 100%; height: 1fr; border: round #365d62; }
    #board-editor-side { width: 100%; height: auto; padding: 0 1; }
    #board-editor-effects { width: 100%; height: auto; padding: 1; }
    #board-editor-tools { width: 100%; height: 4; }
    .board-tool-row { width: 100%; height: 2; }
    .board-tool { width: 1fr; min-width: 0; height: 2; margin: 0; padding: 0 1; content-align: center middle; background: #101018; border-bottom: solid #365d62; color: #ffffff; }
    .board-tool:hover { background: #1a1a27; border-bottom: solid #5b67a0; }
    .board-tool.accent { color: #ffd166; }
    .board-tool.accent:hover { border-bottom: solid #ffd166; }
    #board-editor-help { width: 100%; height: 2; color: #aab0c2; text-align: center; }
    """
