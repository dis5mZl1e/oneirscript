"""导航动作族：action_*、楼层过渡、主页/存档/新游戏/暂停菜单、按钮分发。"""
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
from ..styles import RIGHT_PANEL_MODES
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

class NavigationMixin:
    """导航动作族：action_*、楼层过渡、主页/存档/新游戏/暂停菜单、按钮分发。"""

    def _modal_menu_open(self, *, allow_inspection: bool = False) -> bool:
        """全屏模态覆盖层是否正在遮挡世界。

        涵盖：暂停菜单（或它打开的设置页/图鉴覆盖层/旧梦回忆覆盖层）、联想盘
        编辑器、装备三选一、篡改编辑器与观察检视。on_key 的模态分支挡得住
        键盘；但 q 是 priority 绑定（先于 on_key）、Tab 走 Screen 的 priority
        绑定、底栏键位点击根本不经过 on_key——这些入口各自需要这道卫兵。
        图鉴覆盖层 pause_codex 2026-10-24 补进名单（键位治理 A3：此前它开着
        时 Tab 仍会切换右栏工作区、底栏按钮也能穿透）；home_history 同批补进
        （键位治理 B7 的游戏内旧梦回忆覆盖层与主页共用该 panel_mode，主页
        语义由 not self.home_mode 排除）。
        """
        side_tamper = (getattr(self, 'world_tamper_editor', None) is not None
                       and getattr(self.world_tamper_editor, 'host', 'map') == 'side'
                       and self.panel_mode == 'actions'
                       and self._panel_subpage_id() == 'tamper')
        return (self._inspection_active() and not allow_inspection) or ((self._active_tamper_editor() is not None and not side_tamper
                    and not (allow_inspection and getattr(self, "world_tamper_editor", None) is not None))
                    or bool(getattr(self, 'equipment_choice', None))) or (not self.home_mode and self.panel_mode in (
            "pause", "pause_settings", "pause_codex", "board_editor", "home_history",
        ))

    def action_assist_action(self) -> None:
        """底栏「辅助」按钮：与键盘 o 键同一入口（见 InputMixin.assist_key）。"""
        if self._modal_menu_open():
            return
        if self._handled_in_on_key("o"):
            return
        if self._floor_transition_skip():
            return
        self.assist_key()

    def action_toggle_cursor_lock(self) -> None:
        """底栏「~ 锁定」与键盘 ` / ~ 键的唯一切换入口（实现在 InputMixin）。

        键盘 ` / ~ 由 on_key 归一处理（两种键名都算这个键），并标记「已处理」，
        于是紧跟其后的这条绑定被吃掉、只切一次；底栏点击不经过 on_key，
        照常切一次。两条通道各切一次会互相抵消，所以必须二选一。
        """
        if self._modal_menu_open():
            return
        if self._handled_in_on_key("tilde"):
            return
        if self._floor_transition_skip():
            return
        self.toggle_cursor_lock()

    def action_cycle_cursor_zone(self) -> None:
        """底栏「/ 区域」按钮：与键盘 / 键同一入口（实现在 InputMixin.cycle_cursor_zone）。

        键盘 / 由 on_key 处理并标记「已处理」，紧跟其后的这条绑定被吃掉、
        只切一次；底栏点击不经过 on_key，照常切一次。
        """
        if self._modal_menu_open():
            return
        if self._handled_in_on_key("slash"):
            return
        if self._floor_transition_skip():
            return
        self.cycle_cursor_zone()

    def action_act_action(self) -> None:
        """底栏「Enter 行动」：等价于按下 Enter，只做不需要坐标与方向的那一种左键。

        左键要靠坐标才有意义（远处寻路、相邻格移动、指定方向发射），这些键盘上
        本来就有方向键与寻路；真正只有左键能表达的是「目标就是玩家脚下这一格」——
        脚下有显化物则拾起、有未回应的异常地点则回应、有植物则拔起。确认攻击、
        面板激活等上下文里 Enter 仍是各自的激活键，具体分支见
        InputMixin._handle_action_key。

        ⚠️ 主页**不在**上述之列：主页 Enter 不再开启/载入新游戏（2026-09-16
        玩家要求「去除此界面，enter 回归确认、类似左键功能」），想开局请鼠标
        左键点击存档槽。
        """
        if self._modal_menu_open():
            return
        if self._handled_in_on_key("enter"):
            # 这次触发紧跟在 on_key 之后（Enter 已在那里处理完），消耗掉即可。
            return
        if self._floor_transition_skip():
            return
        self._handle_action_key()

    def action_observe_mode(self) -> None:
        """底栏「观察」（x）：进入/退出观察模式。

        观察模式下自己不挪步、时间静止、视野不重算，只有一枚白色 ? 在动；
        定位与鼠标悬停一致，只是改由键盘驱动（见 InputMixin.toggle_observe）。
        """
        if self.home_mode or self.session.state.run_over:
            return
        if self._modal_menu_open():
            return
        if self._handled_in_on_key("x"):
            # on_key 已经处理过这次 x（观察模式下 x = 退出观察），别把它翻回来。
            return
        if self._floor_transition_skip():
            return
        self.toggle_observe()

    def _apply_floor_change(self, command: str, *, ignore_dissolution: bool = False):
        """下潜/上浮统一入口：先抓旧层渲染帧，再结算，按设置决定演出或直刷。

        地图生成与落点完全由 state.descend/backtrack 决定——演出只消费
        「已生成的新状态」与「旧层的渲染文本」，两条数据都动不了游戏逻辑。

        ``ignore_dissolution=True`` 只有调试面板「移动」会传：跳过崩解度门槛
        （见 ``_apply``）。返回本次的 ``ActionResult``，调用方（调试面板）靠它
        区分「真的换了层」与「被规则拒绝、只该把原因写进事件记录」。
        """
        old_frame = None
        old_image = None
        old_viewport = None
        # values.get 容错：设置项未注册时等同关闭（直刷，与现状一致）。
        if bool(self.config.config.values.get("floor_transition")):
            try:
                map_view = self.query_one("#map", MapView)
                map_view.update_state(self.session.state)  # 确保旧层帧是当前的（无变化零成本）
                old_frame = map_view.last_base_text
                # 旧帧的网格尺寸要一起带走：新层可能是长廊/迷宫（尺寸完全不同），
                # 用旧视口去切新帧会越界。
                old_viewport = tuple(map_view.viewport)
                if map_view.display_mode == 'image':
                    old_image = map_view.image_frame().copy()
            except Exception:
                old_frame = None
                old_viewport = None
        result = (self._apply(command, ignore_dissolution=True) if ignore_dissolution
                  else self._apply(command))
        if self.tutorial_session and (self.session.state.run_over
                or not self.session.state.tutorial.get('active')):
            self._finish_tutorial_session()
            return result
        if result.changed and old_frame is not None and not self.home_mode:
            try:
                self._start_floor_transition(old_frame, old_viewport, old_image)
            except Exception:
                # 演出挂了也必须把新层画出来：否则状态已经下潜、画面还停在旧层，
                # 玩家看到的就是「卡死」。
                if self._floor_transition is not None:
                    self._finish_floor_transition(suppress_wipe=True)
                else:
                    self.refresh_view()
        else:
            self.refresh_view()
        return result

    def _start_floor_transition(self, old_frame, old_viewport=None, old_image=None) -> None:
        self._clear_projectile()
        state = self.session.state
        try:
            map_view = self.query_one("#map", MapView)
        except Exception:
            self.refresh_view()
            return
        # 视口必须按**新层**的尺寸重算。层型会改写地图长宽（长廊/迷宫），
        # 沿用旧层视口去 render 新层会读到越界坐标抛 IndexError——演出起不来、
        # 画面停在旧层，就是「上下楼动画不出现且卡死」。
        left, top, vw, vh = map_view.viewport_for(state)
        map_view.viewport = (left, top, vw, vh)
        # 新层帧直接调 render_map，不走 update_state——后者会把新层整帧画出去，
        # 破坏「一格一格生成」的演出。
        new_frame = render_map(
            state,
            viewport_width=vw,
            viewport_height=vh,
            origin=(left, top),
            symbol_mode=map_view.symbol_mode,
            cell_w=map_view.cell_w,
            cell_h=map_view.cell_h,
        )
        # seed 掺 depth 与 time：同一次演出内稳定，重进同层不重复。
        seed = state.depth * 100003 + state.time * 7919 + 17
        px = min(max(0, state.player.x - left), vw - 1)
        py = min(max(0, state.player.y - top), vh - 1)
        d_max = max(math.hypot(px - cx, py - cy) for cx in (0, vw - 1) for cy in (0, vh - 1))
        off = {(x, y): cell_off_time_a(x, y, (px, py), d_max, seed) for y in range(vh) for x in range(vw)}
        on = {(x, y): cell_on_time_b(x, y, (px, py), d_max, seed) for y in range(vh) for x in range(vw)}
        # 旧帧按**它自己的**网格切：新旧层格数不同时，compose_frame 靠
        # old_vw/old_vh 决定哪些格有旧内容，其余按「已熄灭」处理。
        old_vw, old_vh = (old_viewport[2], old_viewport[3]) if old_viewport else (vw, vh)
        # Prepare pixels before publishing a state that locks world input.
        new_image = None
        if old_image is not None and map_view.display_mode == 'image':
            map_view._frame_key = None
            map_view.update_state(state)
            new_image = map_view.image_frame().copy()
        self._floor_transition = {
            "t0": time.monotonic(),
            "seed": seed,
            "old": cell_segments(old_frame, old_vw, old_vh, map_view.cell_w, map_view.cell_h),
            "new": cell_segments(new_frame, vw, vh, map_view.cell_w, map_view.cell_h),
            "off": off,
            "on": on,
            "vw": vw,
            "vh": vh,
            "old_vw": old_vw,
            "old_vh": old_vh,
            "cell_w": map_view.cell_w,
            "cell_h": map_view.cell_h,
            "ticks": 0,
        }
        if new_image is not None:
            self._floor_transition['old_image'] = old_image
            self._floor_transition['new_image'] = new_image
        if self._transition_timer is not None:
            self._transition_timer.stop()
        self._transition_timer = self.set_interval(1 / 20, self._floor_transition_tick)
        # 首帧**当场**画出去，不等第一次定时器：机器忙时 20fps 的 interval 可能
        # 被拖到几百毫秒后才第一次触发，那一整段时间画面还停在旧层——
        # 「按了 n 没反应」的一半观感就来自这里。
        try:
            self._floor_transition_tick()
        except Exception:
            self._finish_floor_transition(suppress_wipe=True)

    def _floor_transition_tick(self) -> None:
        tr = self._floor_transition
        if tr is None:
            return
        try:
            t = time.monotonic() - tr["t0"]
            tr["ticks"] += 1
            # 演出总长 1.4s；ticks 是看门狗——万一定时器被别的东西拖慢或时钟
            # 异常，也绝不能把输入永久锁在演出里（曾经的真实故障：tick 抛异常
            # 让定时器整个停摆，_floor_transition 再也清不掉）。
            if t >= TOTAL or tr["ticks"] > 200:
                self._finish_floor_transition(suppress_wipe=True)
                return
            frame = compose_frame(
                tr["old"], tr["new"], t, tr["off"], tr["on"],
                tr["vw"], tr["vh"], tr["cell_w"], tr["cell_h"], tr["seed"],
                old_vw=tr["old_vw"], old_vh=tr["old_vh"],
            )
            map_view = self.query_one("#map", MapView)
            if 'old_image' in tr:
                from ..transition import compose_image_frame
                tr['image_frame'] = compose_image_frame(
                    tr['old_image'],tr['new_image'],t,tr['off'],tr['on'],tr['vw'],tr['vh'],
                    tr['old_vw'],tr['old_vh'])
                map_view.refresh()
            else:
                map_view.update(frame)
        except Exception:
            self._finish_floor_transition(suppress_wipe=True)

    def _finish_floor_transition(self, suppress_wipe: bool) -> None:
        """收尾：停定时器、清状态、常规刷新接管。

        自然播完 → 抑制本次 dissolve_wipe（演出已表达换层）；
        被跳过 → 不抑制，擦除给一次即时反馈（设计文档 §2.3 互斥规则）。
        """
        if self._transition_timer is not None:
            self._transition_timer.stop()
            self._transition_timer = None
        self._floor_transition = None
        # 换层演出结束的补画必须无条件重算：同一步内旧快速键可能来自演出前
        # 的普通帧，跳过会把残帧留在屏幕上（transition 回归）。
        self._fx_quick_key = None
        # 演出期间 FX 时钟冻结；恢复时先让下一次定时器只重置基线，不把演出
        # 经过的整段时间一次性加进时钟（否则跳过后的首帧与直刷帧会差出一批
        # 粒子步进）。
        self._fx_last = None
        if suppress_wipe:
            self.fx_engine.skip_next_wipe()
        self.refresh_view()

    def action_descend_action(self) -> None:
        """底栏「下潜」（n）：崩解度满 100 时深入下一梦层。"""
        if self._handled_in_on_key("n"):
            return
        if self._floor_transition_skip():
            return
        if self.home_mode or self.observe_mode or self.session.state.run_over:
            return
        if self._modal_menu_open():
            return
        self.path.clear()
        self._apply_floor_change("descend")

    def action_backtrack_action(self) -> None:
        """底栏「上浮」（b）：回到更浅的一梦层。"""
        if self._handled_in_on_key("b"):
            return
        if self._floor_transition_skip():
            return
        if self.home_mode or self.observe_mode or self.session.state.run_over:
            return
        if self._modal_menu_open():
            return
        self.path.clear()
        self._apply_floor_change("backtrack")

    def action_wait_turn(self) -> None:
        """底栏「等待」：推进一回合。"""
        if self._handled_in_on_key("."):
            return
        if self._floor_transition_skip():
            return
        if self.home_mode or self.observe_mode or self.session.state.run_over:
            return
        if self._modal_menu_open():
            return
        self.path.clear()
        self._apply("wait")
        self.refresh_view()

    def action_pickup_action(self) -> None:
        """底栏「捡起」：拾取脚下显化物。

        多件时开勾选面板（见 `try_pickup`），单件直接捡。
        ``on_key`` 里已经处理过同一个 G 时这次触发是重复的（面板内的 G 就是
        这条路径），必须空转——否则「面板里按 G 结算」会被捡两次。
        """
        if self._handled_in_on_key("g"):
            return
        if self._floor_transition_skip():
            return
        if self.home_mode or self.observe_mode or self.session.state.run_over:
            return
        if self._modal_menu_open():
            return
        self.path.clear()
        self.try_pickup()
        self.refresh_view()

    def action_aim_fire(self) -> None:
        """底栏「发射」：进入选定来源瞄准；瞄准中再按打开来源表。

        来源表由 ``collect_firing_sources`` 统一给出（直射、喷射、聚合弹与
        一次性发射物）；有上次有效来源时直接沿用，空匣也照样沿用，不悄悄
        换成另一种弹药。仅一种来源时才跳过选择。
        """
        if self._handled_in_on_key("f"):
            return
        if self._floor_transition_skip():
            return
        if self.home_mode or self.observe_mode or self.session.state.run_over:
            return
        if self._modal_menu_open():
            return
        if (self.aiming
                and getattr(self, 'sentence_aim', None) is None
                and getattr(self, 'construct_aim_id', None) is None
                and self.throw_item_index is None):
            # F inside a firing-source aim is a source-table request, never a shot.
            if getattr(self, 'equipment_choice', None) is None:
                self._open_aim_source_table()
            return
        options = self._firing_source_options()
        last = getattr(self, '_last_firing_source_key', None)
        remembered = next((option for option in options
                           if option.get('source_key') == last), None)
        if len(options) > 1 and remembered is not None:
            self._begin_equipment_aim(remembered)
            return
        self.aim_action_choice = None
        if len(options) > 1:
            self.equipment_choice = dict(command='aim_equipment', args=(), options=options,
                                         cursor=0, context=self._equipment_choice_context())
            self.path.clear()
            self._clear_held()
            self.refresh_view()
        else:
            self._begin_equipment_aim(options[0] if options else None)

    def _aim_hud_click(self, offset) -> bool:
        """Mouse entries drawn on the aim bubble: switch source / reload / exit."""
        try:
            x, y = int(offset.x), int(offset.y)
        except Exception:
            return False
        for start, end, row, kind in getattr(self, '_aim_hud_zones', ()):
            # Widget offsets may or may not include the bubble's left padding;
            # accept the adjacent column without widening the hit box further.
            if row != y or not (start <= x < end or start <= x - 1 < end):
                continue
            if kind == 'sources':
                self._open_aim_source_table()
            elif kind == 'reload':
                self.action_reload_weapon()
            elif kind == 'cancel':
                self.cancel_aim()
                self.refresh_view()
            return True
        return False
    def _return_home(self) -> None:
        if self._transition_timer is not None:
            self._transition_timer.stop()
            self._transition_timer = None
        self._floor_transition = None
        if self.aiming:
            self.cancel_aim()
        self._fx_waves.clear()
        self._fx_hits.clear()
        self._fx_flashes.clear()
        self._fx_frame_digest = self._fx_quick_key = None
        try:
            map_view = self.query_one('#map', MapView)
            map_view.set_intent_marks({})
            map_view.update_image_effects({}, {}, force=True, fog_styles={})
        except Exception:
            pass
        self.sentence_aim = None
        self.equipment_choice = None
        self.aim_action_choice = None
        self.spray_select = None
        self._clear_lens_offer()
        self.aiming = False
        self._cancel_attack_confirmation(refresh=False)
        self._clear_projectile()
        self._home_started = None
        self.home_mode = True
        self.panel_mode = "home"
        # 退出存档回主页＝锁定解除（玩家规则：只有退出存档重进或手动 ~ 才解除）。
        self.panel_locked = False
        self._locked_panel_page = None
        self.home_view = "menu"
        # 回主页后存档页默认回到普通槽位；测试存档只能从「⚙ 测试模式」入口再进。
        self.saves_test = False
        self.newgame_saves_test = False
        self.test_mode = False
        self._keys_handled_in_on_key.clear()
        # 跨局特效状态作废：清醒度取样归零（下一局的第一次取样不得判「骤降」）、
        # 受创边框闪与红脉冲清空——否则带着上一局的低清醒回家再开局就闪。
        self.fx_engine.reset_run_state()
        self.path.clear()
        self.item_menu_target = None
        self.anomaly_detail_target = None
        self.close_cell_detail()
        # 篡改草稿一并丢掉：回主页后编辑对象早已不在眼前。
        self.tamper_editor = None
        self.observe_mode = False
        self.observe_cursor = None
        self._hide_pause_views()
        # 结算演出与教程卡随局收起（换局/返家不留残影）。
        try:
            self.query_one("#settlement", SettlementScreen).hide()
        except Exception:
            pass
        try:
            self.query_one("#tutorial-card", TutorialCard).show_step(Text())
        except Exception:
            pass
        # 底色复位（2026-09-21）：主页不属于任何区域，Screen / #map-pane 回中性黑、
        # 三处面板回中性面板色；同时作废 `_applied_theme`，否则再进游戏时
        # `_apply_region_theme` 会因为「主题对象没变」提前返回，把区域面板色
        # （和边框/顶栏）整批留在上一局的值上。
        # `#map-pane` 自己也带底色（地图边框那一圈），同样要复位——否则它会在下次
        # 进游戏前把上一局的值留在面板上（主页该圈不可见，但换局时会先按旧值闪一下）。
        self.screen.styles.background = MAP_BG
        try:
            self.query_one("#map-pane").styles.background = MAP_BG
        except Exception:  # pragma: no cover - 极端情况下 map-pane 尚未挂载
            pass
        # 🔴 2026-10-18：地图气泡的**本体**是 MapHintText（#map-mode-hint），
        # 容器 #map-hints 只做布局、不吃底色（见 app._apply_region_theme）。
        # 复位也要按本体复位，否则下一局首帧的气泡会留着上一区/兜底的颜色。
        for selector in ("#side-pane", "#map-overlay", "#tamper-overlay", "#toast", "#map-mode-hint"):
            try:
                self.query_one(selector).styles.background = DEFAULT_PANEL_BG
            except Exception:  # pragma: no cover - 极早期挂载中可能还没就位
                pass
        self._applied_theme = None
        # [SFX挂点] 音乐·回到主页：stop_music 淡出（或换主页短主题）。
        self.query_one("#layout").styles.display = "none"
        self.query_one("#home").styles.display = "block"
        self.query_one(Header).styles.display = "none"
        self.refresh_view()

    def _leave_home(self) -> None:
        self._clear_projectile()
        state = self.session.state
        self._particle_layer = (state.depth, state.realm_id, state.realm_depth)
        self._fx_memory_count = len(state.memory_fragments)
        self._fx_memory_ids = set(state.memory_fragments)
        self._fx_blast_count = len(getattr(state, 'explosion_blasts', ()) or ())
        self._home_started = None
        if self._home_timer is not None:
            self._home_timer.pause()
        self.home_mode = False
        self.panel_locked = False
        self._locked_panel_page = None
        self.panel_mode = self._default_panel_mode()
        # [SFX挂点] 音乐·进入游戏（读档/新开局）：play_music("theme") 淡入循环，
        # 建议 梦境音乐\snow_theme_loop.ogg 改名 theme.ogg 覆盖占位资源。
        # 主页里 Enter 由按钮绑定消费时不经过底栏，可能留下未消耗的标记；
        # 离开主页时清掉，避免进入游戏后的第一次「Enter 行动」点击被误吞。
        self._keys_handled_in_on_key.clear()
        # 进游戏第一帧不得有「周围闪烁」：清醒度取样重新播种（None=只记录），
        # 受创边框闪/红脉冲作废——载入低清醒存档时不再误判骤降闪暗角。
        self.fx_engine.reset_run_state()
        self._hide_pause_views()
        self.query_one("#layout").styles.display = "block"
        self.query_one("#home").styles.display = "none"
        self.query_one(Header).styles.display = "block"
        self.query_one(Footer).styles.display = "block"
        self.refresh_view()
    # ---- 全屏暂停菜单（2026-09-20）：Esc 的「菜单」语义 ----

    # 选项从上到下：继续 / 图鉴 / 设置 / 返回主页（用户指定顺序，不增不减）。
    PAUSE_OPTIONS = ("continue", "catalog", "settings", "home")

    def _hide_pause_views(self) -> None:
        """收起暂停菜单与设置覆盖层（返家/离家的兜底，防残影）。"""
        try:
            self.query_one("#pause-menu").styles.display = "none"
        except Exception:
            pass
        try:
            self.query_one("#settings-page").styles.display = "none"
        except Exception:
            pass
        try:
            # 图鉴覆盖层（2026-10-14 从 #home 移出）：同批收起防残影。
            self.query_one("#codex-page").styles.display = "none"
        except Exception:
            pass
        try:
            # 联想盘编辑器同样是整屏覆盖层：草稿在离家时直接作废。
            self.query_one("#board-editor").styles.display = "none"
        except Exception:
            pass
        self.board_editor = None

    def open_pause_menu(self) -> None:
        """打开全屏暂停菜单：隐藏 #layout（地图+面板整体让位），底栏保留。

        入口只有 Esc 取消链走完（见 InputMixin._can_open_pause_menu）——
        教程、对话、瞄准等特殊状态一律先被链收掉，轮不到这里。

        ⚠️ 必须清掉焦点：真机上残留焦点的按钮（导航块/底栏键位等）会把
        Enter 吃成「按下那个按钮」——事件到不了 App 的 pause 分支，菜单
        看起来「按了没反应」；更糟的是焦点按钮各自带动作，可能误开面板、
        误触主页按钮间接开新档覆盖原存档（2026-09-20 真机反馈）。
        """
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
        # 2026-10-26：从任意右侧工作区打开的暂停菜单，继续时回到原来的页面
        # （选中项与滚动位置本来就不清），而不是一律丢回事件记录页。
        self._pause_return_mode = (self.panel_mode
                                   if self.panel_mode in RIGHT_PANEL_MODES
                                   else self._default_panel_mode())
        self.pause_cursor = 0
        self.panel_mode = "pause"
        self.set_focus(None)
        self.query_one("#layout").styles.display = "none"
        self.query_one("#pause-menu").styles.display = "block"
        self.refresh_view()

    def close_pause_menu(self) -> None:
        """「继续」：收起菜单回到世界（不消耗回合，世界本来就是静止的）。

        2026-10-26：从右侧工作区打开时回到原页，保留原选中项。
        """
        self.panel_mode = (getattr(self, "_pause_return_mode", None)
                           or self._default_panel_mode())
        self._pause_return_mode = None
        self._hide_pause_views()
        self.query_one("#layout").styles.display = "block"
        self.refresh_view()

    def pause_move(self, delta: int) -> None:
        """滚轮/WS/方向键挪光标（循环）。"""
        self.pause_cursor = (self.pause_cursor + delta) % len(self.PAUSE_OPTIONS)
        self.refresh_view()

    def pause_click(self, row: int) -> None:
        """左键点击选项：选中并当场触发（与 Enter 同一路径）。"""
        if 0 <= row < len(self.PAUSE_OPTIONS):
            self.pause_cursor = row
            self.activate_pause_option()

    def activate_pause_option(self) -> None:
        """触发当前选项（Enter/左键共用）。"""
        option = self.PAUSE_OPTIONS[self.pause_cursor]
        if option == "continue":
            self.close_pause_menu()
        elif option == "catalog":
            # 图鉴：整屏覆盖层（2026-10-14 修复——旧实现把 panel_mode 置成
            # "catalog"，那其实是右侧观测面板，图鉴从未被打开过）。与设置页
            # 同构：收菜单、亮覆盖层，Q/Esc 回暂停菜单。
            self.panel_mode = "pause_codex"
            self.codex_page.focus_categories()
            self._hide_pause_views()
            self.query_one("#codex-page").styles.display = "block"
            self.refresh_view()
            self.call_after_refresh(self._focus_codex_list)
        elif option == "settings":
            # 设置：全屏覆盖层（与主页共用 #settings-page），Q/Esc 回暂停菜单。
            self.settings_from = "pause"
            self.panel_mode = "pause_settings"
            self.settings_page.capture_target = None
            self.query_one("#pause-menu").styles.display = "none"
            self.query_one("#settings-page").styles.display = "block"
            self.refresh_view()
        elif option == "home":
            # 返回主页 = 保存并回主页（与 F10 游戏内行为一致）。
            self.action_save_exit()
            # _return_home 会清「已处理键」标记（防跨界面残留）——但这次 Enter
            # 还在派发中：标记被清后，底栏 Enter 绑定会再触发一次行动分发，
            # 在主页上表现为「刚回主页就立刻载入光标所在存档槽」。补回标记。
            self._mark_key_handled("enter")

    def _pause_menu_text(self, mode: str) -> Text:
        """暂停菜单标题牌匾：复用主页同款 3 行 × 60 列边框牌匾（home_title_text），
        与存档槽行块共用一条居中轴——视觉上比裸文本大一号。"""
        return home_title_text(tr("暂 停"))

    def _refresh_pause_view(self, mode: str) -> None:
        self.query_one("#pause-title", Static).update(self._pause_menu_text(mode))
        labels = {
            "continue": tr("继续"),
            "catalog": tr("图鉴"),
            "settings": tr("设置"),
            "home": tr("返回主页"),
        }
        for index, option in enumerate(self.PAUSE_OPTIONS):
            selected = index == self.pause_cursor
            widget = self.query_one(f"#pause-option-{index}", Static)
            widget.update(
                Text(
                    (f"{symbol('cursor', mode)} " if selected else "")
                    + labels[option],
                    style="bold bright_cyan" if selected else "#ffffff",
                )
            )
            widget.set_class(selected, "selected")
        self.query_one("#pause-help", Static).update(
            tr("↑↓/W S/滚轮 选择 · Enter/左键 确认 · Esc 继续")
        )
    def _home_item_id(self) -> str:
        """光标所在的主页选项 id（与 compose() 里的控件 id 一致）。"""
        if self.home_view == "menu":
            return self.HOME_MENU_ITEMS[self.menu_index]
        if self.home_row == self.session.manager.SLOT_COUNT and not self.saves_test:
            return 'home-tutorial'
        return self.HOME_ROWS[self.home_row][self.home_column]

    def _sync_home_cursor(self) -> None:
        """把光标所在行同步到 selected_slot 与面板文案模式。

        行 0..2 是存档槽行：光标行即槽号（1 基），右侧面板显示「存档栏」文案；
        行 3 是导航行：不改 selected_slot（仍是最后停留的槽，供 D 键与「继续」用），
        面板文案回落到主页总提示。

        ⚠️ **只在主页里改 panel_mode**（2026-09-16 修正）：``panel_mode`` 同时兼任
        「右侧面板显示什么」与「按键路由走哪条分支」两职。以前这里不判断
        ``home_mode`` 就无条件写成 ``home_saves``，于是游戏内一旦有代码路径调用它
        （光标同步、窗口尺寸变化等），右侧面板就会一直渲染主页的「已选择存档槽 N /
        按 Enter 开始新游戏」，并且因为 ``panel_mode != "world"`` 让
        ``_refresh_game_frame`` 直接 return、按键落到面板分支——玩家看到的就是
        「右边这块界面去不掉」+「小键盘在动面板选择」。
        """
        if not self.home_mode:
            return
        # 主页整屏子页（图鉴/设置/回忆/开局选项）打开时，光标同步不得把
        # panel_mode 拽回 home/home_saves——否则一次窗口缩放就把玩家踢出子页。
        if self.panel_mode in ("home_catalog", "home_settings", "home_history", "home_newgame"):
            return
        if self.home_view == "menu":
            # 主菜单视图：右面板回落主页总提示，不改 selected_slot。
            self.panel_mode = "home"
            return
        if self.home_row < self.session.manager.SLOT_COUNT:
            self.selected_slot = self.home_row + 1
            self.panel_mode = "home_saves"
        else:
            self.panel_mode = "home"

    def move_home_cursor(self, vertical: int = 0, horizontal: int = 0) -> None:
        """主页方向键（2026-09-23 双视图）。

        - **主菜单视图**：竖排单列，↑↓ 在「入梦/图鉴/回忆/设置/退出/测试模式」
          之间循环（横轴同样按移动处理，循环兜底任何按键）。
        - **存档槽页视图**：只在三行槽位间循环（行内 ←→ 是「存档槽 ↔ 删除」，
          两列循环）——图鉴/测试模式等入口不在这一页，回 Esc/Q。
        - 任何移动都取消「删除」的待确认态：光标一移开就不能再删。
        """
        rows = self.HOME_ROWS
        self.home_confirm_delete = False
        if self.home_view == "menu":
            count = len(self.HOME_MENU_ITEMS)
            self.menu_index = (self.menu_index + (vertical or 0) + (horizontal or 0)) % count
            self._sync_home_cursor()
            self._refresh_home_menu_selection()
            self._refresh_tutorial_coach()
            return
        if vertical:
            self.home_row = (self.home_row + vertical) % (self.session.manager.SLOT_COUNT + (not self.saves_test))
            self.home_column = (min(self.home_column, len(rows[self.home_row]) - 1)
                                if self.home_row < self.session.manager.SLOT_COUNT else 0)
        if horizontal:
            width = len(rows[self.home_row]) if self.home_row < self.session.manager.SLOT_COUNT else 1
            self.home_column = (self.home_column + horizontal) % width
        self._sync_home_cursor()
        self.refresh_view()

    def _test_save_dir(self):
        """测试存档目录：普通存档目录旁的 `<save>-test`（默认 save/ → save-test/）。

        旧实现用相对 CWD 的 "save-test"；改成相对存档根后，测试/临时存档不会
        污染仓库根目录，而正式发行的 `<exe目录>/save/` 仍对应 `<exe目录>/save-test/`。
        """
        base = Path(self.base_save_dir)
        return base.parent / f"{base.name}-test"

    def _saves_root(self):
        """主页存档页当前根目录：普通槽或测试模式独立目录（save-test/）。"""
        return self._test_save_dir() if getattr(self, "saves_test", False) else self.base_save_dir

    def _saves_manager(self):
        """主页槽位/删档/开局用的 SaveManager（按当前存档页决定目录）。"""
        return SaveManager(self._saves_root())

    # ---- 读档预取（2026-10-26 第二轮读档提速）-------------------------
    # 打开存档页后玩家通常要看几百毫秒再按 Enter；这段时间把可安全读取的槽位
    # 在后台线程解码好，点击瞬间只剩换会话 + 首帧。实现与安全边界见
    # ui/app/save_prefetch.py（不写玩家存档；需迁移的旧档一律不预取）。
    def _get_save_prefetcher(self):
        prefetcher = getattr(self, "_save_prefetcher", None)
        if prefetcher is None:
            from .save_prefetch import SavePrefetcher
            prefetcher = self._save_prefetcher = SavePrefetcher()
        return prefetcher

    def _save_prefetch_enabled(self) -> bool:
        if getattr(self, "_save_prefetch_disabled", False):
            return False
        from ...env_compat import get as env_get
        raw = str(env_get("SAVE_PREFETCH", "1")).strip().lower()
        return raw not in ("0", "off", "false", "no")

    def _start_save_prefetch(self) -> None:
        """存档页显示后后台预取现有槽位（只读；失败静默，不影响页面）。"""
        if not self._save_prefetch_enabled():
            return
        try:
            root = self._saves_root()
            manager = SaveManager(root)
            slots = [slot for slot in range(1, manager.SLOT_COUNT + 1)
                     if manager.for_slot(slot).slot_exists()]
            if slots:
                self._get_save_prefetcher().start(root, slots)
        except Exception:
            # 预取是纯加速路径：任何异常都回落正常读档，不能影响打开存档页。
            pass

    def _open_saves(self, slot: int | None = None, *, test: bool = False) -> None:
        """进入存档槽选择/删除页（可带初始槽位）；test=True 时操作用测试存档目录。"""
        self.saves_test = test
        self.home_view = "saves"
        # 光标必须落回槽位区（行 0..2）：存档页没有主菜单的「图鉴/设置/退出」行，
        # 把主菜单行号带进来会让下一次 Enter 激活错误项——实测鼠标点「入梦」后
        # 按键盘 Enter 直接进了图鉴（mixed 键鼠矩阵 2026-10-15 复现）。
        self.home_row = max(0, min(self.session.manager.SLOT_COUNT - 1,
                                   (slot or self.selected_slot or 1) - 1))
        self.home_column = 0
        self.home_confirm_delete = False
        # 焦点管理与其他主页子页对齐（暂停菜单 set_focus(None)、开局页聚焦容器）：
        # 鼠标点击留下的旧按钮焦点会让焦点键（Enter）绕过光标模型直连图鉴等项。
        self.set_focus(None)
        self._sync_home_cursor()
        self.refresh_view()
        # 页面已排好刷新，再启动后台预取：不抢首页这一帧的合成时间。
        self._start_save_prefetch()

    def _close_saves(self) -> None:
        """存档槽页 → 回主菜单。"""
        self.home_view = "menu"
        self.home_confirm_delete = False
        self.set_focus(None)  # 同 _open_saves：别让槽位按钮的残留焦点截胡 Enter。
        self._sync_home_cursor()
        self.refresh_view()

    def select_home_slot(self, slot: int) -> None:
        """裸数字 1/2/3：直接选中对应存档槽（光标落到该行首列）。"""
        self.home_view = "saves"
        self.home_row = max(0, min(self.session.manager.SLOT_COUNT - 1, slot - 1))
        self.home_column = 0
        self.home_confirm_delete = False
        self.set_focus(None)  # 同 _open_saves。
        self._sync_home_cursor()
        self.refresh_view()
        self._start_save_prefetch()

    def _activate_home_item(self, item_id: str) -> bool:
        """激活主页上的一个选项（存档槽 / 删除 / 图鉴 / 设置 / 退出）。

        键盘 Enter 与鼠标点击共用这一条路径，返回是否认领了该 id。
        """
        if item_id == 'home-tutorial' and not self.saves_test:
            self._start_tutorial_session()
            return True
        if item_id == "home-enter":
            # 入梦：主页不直接摆存档，进入存档槽选择/删除页（2026-09-23 改版）。
            self._open_saves()
            return True
        if item_id.startswith("slot-"):
            slot = int(item_id.rsplit("-", 1)[1])
            # 已有存档：直接读档；空槽：先进开局选项页（调律 → 择碎片 → 入梦）。
            if self._saves_manager().for_slot(slot).slot_exists():
                self._load_slot(slot, test=self.saves_test)
            else:
                self._open_newgame(slot, test=self.saves_test)
            return True
        if item_id.startswith("delete-"):
            self._request_delete_slot(int(item_id.rsplit("-", 1)[1]))
            return True
        if item_id == "home-history":
            self._open_history()
            return True
        if item_id == "home-catalog":
            self._open_codex()
            return True
        if item_id == "home-settings":
            self._open_settings()
            return True
        if item_id == "home-exit":
            self.exit()
            return True
        if item_id == "test-mode":
            # 2026-10-23：与普通模式一样先进存档栏（可删档/换槽/按调律开局）。
            self._open_saves(test=True)
            return True
        return False

    def activate_home_selection(self) -> None:
        """Activate the selected item; deletion always uses the shared dialog."""
        self.home_confirm_delete = False
        self._activate_home_item(self._home_item_id())

    def _load_slot(self, slot: int, *, test: bool = False) -> None:
        root = self._test_save_dir() if test else self.base_save_dir
        manager = SaveManager(root).for_slot(slot)
        # 2026-10-26 第二轮：存档页打开后已后台解码过的状态直接复用，点击瞬间
        # 不再付 JSON 解析 + 状态解码；take() 会按主档 stat 校验，文件变过即作废。
        state = None
        if self._save_prefetch_enabled():
            try:
                state = self._get_save_prefetcher().take(root, slot)
            except Exception:
                state = None
        migrated = False
        if state is None:
            try:
                state = manager.load()
            except OutdatedSaveError as exc:
                # 旧格式**明确拒绝**（重构方案 §12.2）：留在主页并把原因说出来。
                # 不能像坏档那样默默转去新开局——那会让玩家以为存档凭空消失了。
                self.show_toast(str(exc))
                return
            except FileNotFoundError:
                self._open_newgame(slot, test=test)
                return
            migrated = bool(getattr(manager, "load_migrated", False))
        # 2026-10-26 读档性能：磁盘上本来就是这份状态，普通读档不需要在
        # GameSession 构造时立刻整局重编码写盘（玩家实测卡顿 95–160ms）。
        # 只有本次 load() 真做了旧档迁移（persist-decode 提供的 load_migrated）
        # 才立即落盘，保留「迁移后马上写回」的语义；预取命中的状态必然未迁移。
        self._adopt_slot_session(state, manager, slot, test_mode=test,
                                 persist_initial=migrated)

    def _adopt_slot_session(self, state, manager, slot: int, *, test_mode: bool = False,
                            persist_initial: bool = True) -> None:
        """载入/新建共用的收尾：换会话、记槽位、光标归位、离开主页。

        参数 persist_initial：构造 GameSession 时是否立即写盘。新开局/重试必须
        保持 True；普通读档传 False，避免把刚读出的状态原样重写一遍。
        """
        self.session = GameSession(state, manager, persist_initial=persist_initial)
        self.tutorial_session = False
        self.test_mode = bool(test_mode)  # 测试存档带调试面板
        self.selected_slot = slot
        # [SFX挂点] 读取存档·进入游戏瞬间：建议 descend 或 teleport_in（下潜入梦境的语义）。
        # 光标跟着走：从主页再回来时光标停在刚载入的槽上。
        self.home_row = max(0, min(manager.SLOT_COUNT - 1, slot - 1))
        self.home_column = 0
        self.home_confirm_delete = False
        self.save_disabled = False
        self._leave_home()

    def _start_tutorial_session(self) -> None:
        """A fresh practice world with persistence disabled at the session boundary."""
        if not self.tutorial_session:
            self._tutorial_home_session = (self.session, self.save_disabled)
        self._return_home()
        state = GameState.new(seed=20261023, tutorial=True)
        state.tutorial['coach_version'] = 1
        self._coach_hidden = self._coach_directory = False
        self._coach_drag_position = None
        self._coach_content_key = self._coach_card_geometry = None
        self.session = GameSession(state, SaveManager(self.base_save_dir),
                                   persist_initial=False, persistence_enabled=False)
        self.tutorial_session = True
        self.save_disabled = True
        self.test_mode = False
        self.ending_shown = False
        self._leave_home()

    def _finish_tutorial_session(self) -> None:
        self.tutorial_session = False
        self._return_home()
        self.session, self.save_disabled = self._tutorial_home_session
        self._tutorial_home_session = None
        self._open_saves()

    # ---- 开局选项页：调律 → 身份与梦性 → 择碎片 → 入梦 ----

    def _retry_finished_run(self, *, tutorial: bool = False) -> bool:
        from ...core.retry import retry_state
        previous = self.session.state
        if (self.test_mode or self.save_disabled or not previous.run_over
                or not previous.run_start_choices):
            return False
        if tutorial:
            self._start_tutorial_session()
            return True
        state = retry_state(previous, seed=new_run_seed(), tutorial=tutorial)
        manager = self.session.manager
        state.catalog = manager.merge_catalogs(previous.catalog, manager.load_catalog())
        self.app.ending_shown = False
        self._adopt_slot_session(state, manager, self.selected_slot or manager.slot)
        return True

    def _open_newgame(self, slot: int, *, test: bool = False) -> None:
        """空存档槽：打开开局选项页（默认中等；三层信息恒开、不占选项）。"""
        from ...core.run_options import default_selection

        selection = default_selection()
        self.newgame_slot = slot
        self.newgame_saves_test = test
        self.newgame_phase = "options"
        self.newgame_seed_text = ""
        self.newgame_seed_error = ""
        if self.is_running:
            try:
                self.query_one("#newgame-seed", Input).value = ""
            except Exception:
                pass
        self.newgame_sliders = dict(selection["sliders"])
        self.newgame_toggles = set(selection["toggles"])
        self.newgame_cursor = 0
        self.newgame_fragments = []
        self.newgame_fragment_cursor = 0
        from ...core.dream_types import default_choice
        self.newgame_dream_type = default_choice()
        self.newgame_identity_cursor = 0
        self.panel_mode = "home_newgame"
        self.refresh_view()
        self.query_one('#newgame-content').focus()

    def _newgame_selection(self) -> dict:
        return {"sliders": dict(self.newgame_sliders), "toggles": sorted(self.newgame_toggles)}

    def _toggle_newgame_option(self, key: str) -> None:
        from ...core.run_options import TOGGLE_DEFS
        if key in self.newgame_toggles:
            self.newgame_toggles.remove(key)
            return
        group = TOGGLE_DEFS[key].get('group')
        if group:
            self.newgame_toggles = {other for other in self.newgame_toggles
                                   if TOGGLE_DEFS[other].get('group') != group}
        self.newgame_toggles.add(key)

    def _scroll_newgame_cursor(self) -> None:
        if not self.is_running or self.panel_mode != 'home_newgame':
            return
        scroll = self.query_one('#newgame-scroll', VerticalScroll)
        row = self._newgame_selected_row
        view = self.query_one('#newgame-content')
        row += view.styles.padding.top
        height = max(1, scroll.content_size.height)
        if row < scroll.scroll_y:
            scroll.scroll_to(y=row, animate=False, immediate=True)
        elif row >= scroll.scroll_y + height:
            scroll.scroll_to(y=row-height+1, animate=False, immediate=True)
            if scroll.scroll_y < row-height+1 and scroll.max_scroll_y < row-height+1:
                # Virtual size can lag the draft's first content update by
                # one layout pass; retry without blocking player input.
                self.set_timer(.02, self._scroll_newgame_cursor)

    def _newgame_cancel(self) -> None:
        """Esc/Q：逐阶段返回并保留草稿，调律页取消回存档槽且不落盘。"""
        if self.panel_mode != "home_newgame":
            return
        if self.newgame_phase == "fragment":
            self.newgame_phase = "identity"
            self.refresh_view()
            return
        if self.newgame_phase == 'identity':
            self.newgame_phase = "options"
            self.refresh_view()
            return
        self.newgame_slot = None
        self.panel_mode = "home_saves"
        self.home_view = "saves"
        self.refresh_view()

    def _confirm_newgame_options(self) -> None:
        """先确认调律，再确认合法身份草稿；记忆候选只掷一次。"""
        import random as _random

        from ...core.run_options import roll_starting_memories
        from ...core.dream_types import validate_choice

        if self.newgame_phase == 'options':
            self.newgame_phase = 'identity'
            self.refresh_view()
            self.query_one('#newgame-content').focus()
            return
        if self.newgame_phase != 'identity' or validate_choice(self.newgame_dream_type):
            self.refresh_view()
            return

        if not self.newgame_fragments:
            self.newgame_fragments = roll_starting_memories(_random.SystemRandom(), 3)
            self.newgame_fragment_cursor = 0
        self.newgame_phase = "fragment"
        self.refresh_view()
        self.query_one('#newgame-content').focus()

    def _newgame_seed_value(self):
        """记忆编号输入 → 种子整数面；“invalid”= 非法，None = 留空随机。"""
        text = (self.newgame_seed_text or "").strip()
        if not text:
            return None
        try:
            value = int(text, 10)
        except ValueError:
            return "invalid"
        return value if 0 <= value <= 2147483647 else "invalid"

    def _confirm_newgame_fragment(self) -> None:
        """最终确认：按调律、身份加点和所选记忆创建新局并入梦。"""
        slot = self.newgame_slot
        from ...core.dream_types import validate_choice
        if slot is None or self.newgame_phase != 'fragment' or validate_choice(self.newgame_dream_type):
            return
        fragment = (
            self.newgame_fragments[self.newgame_fragment_cursor]
            if self.newgame_fragments
            else None
        )
        root = self._test_save_dir() if self.newgame_saves_test else self.base_save_dir
        seed = self._newgame_seed_value()
        if seed == "invalid":
            self.newgame_seed_error = tr("记忆编号需为 0–2147483647 的整数。")
            if self.is_running:
                try:
                    field = self.query_one("#newgame-seed", Input)
                    field.value = ""
                    self.newgame_seed_text = ""
                    field.focus()
                except Exception:
                    pass
                self.refresh_view()
                try:
                    self.query_one("#newgame-seed", Input).focus()
                except Exception:
                    pass
            return
        entered_seed = seed is not None
        manager = SaveManager(root).for_slot(slot)
        state = GameState.new(
            seed=seed if entered_seed else new_run_seed(), tutorial=False,
            run_options=self._newgame_selection(),
            dream_type=self.newgame_dream_type,
            starting_memory=fragment,
        )
        state.catalog = manager.merge_catalogs(state.catalog, manager.load_catalog())
        if entered_seed:
            state.messages.append(tr("记忆编号 {seed} 已作为本局种子。", seed=state.seed))
        self.newgame_slot = None
        self._adopt_slot_session(state, manager, slot, test_mode=self.newgame_saves_test)
        self.newgame_saves_test = False

    def _load_test_mode(self) -> None:
        """进入测试模式：先打开测试存档栏（槽位/删除/调律开局），不再直接开局。

        2026-10-23 用户要求：测试模式与普通模式一样允许删除、替换与进入时的调节选项。
        测试存档仍只存放在 save-test/（不占普通存档目录），核心逻辑复用普通槽位页。
        """
        self._open_saves(test=True)

    def _delete_slot_preview(self, manager: SaveManager) -> str:
        """Read only identifying fields, including from old or backup saves."""
        from ...data.dream_types import IDENTITIES

        for path in (manager.primary, manager.backup):
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
                saved = payload.get('state') if isinstance(payload, dict) else None
                if not isinstance(saved, dict):
                    continue
            except (OSError, ValueError, TypeError):
                continue
            choice = saved.get('dream_type_choice')
            identity = choice.get('identity') if isinstance(choice, dict) else None
            role = IDENTITIES.get(identity, {}).get('name', tr('身份未记录')) if isinstance(identity, str) else tr('身份未记录')
            def recorded(key):
                value = saved.get(key)
                return str(value) if isinstance(value, (str, int, float)) and not isinstance(value, bool) else tr('未记录')
            return '\n'.join((tr('角色：') + tr(role), tr('本局：') + recorded('run_uid'),
                tr('梦层：') + recorded('depth') + ' · ' + tr('回合数：') + recorded('time'),
                tr('预览来源：') + path.name))
        return tr('存档内容无法预览；请核对槽位与文件后再决定。') + '\n' + manager.primary.name

    def _delete_slot(self, slot: int) -> None:
        # [SFX挂点] 存档删除完成：建议 ui_error 或重一点的下坠音（不可恢复操作的反馈）。
        manager = self._saves_manager().for_slot(slot)
        manager.clear_run()
        # 只有删的确实是**当前会话所在**的槽（同目录同槽）才禁用退出保存——
        # 调试模式会话里删普通槽，不该禁掉 save-test 的存档。
        if manager.directory == self.session.manager.directory and manager.slot == self.session.manager.slot:
            self.save_disabled = True
        self.selected_slot = slot
        # 删完光标停在该槽（行首列），「删除」的待确认态已消费掉。
        self.home_row = max(0, min(manager.SLOT_COUNT - 1, slot - 1))
        self.home_column = 0
        self.home_confirm_delete = False
        self.panel_mode = "home_saves"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.handle_button_press(event.button)

    def handle_button_press(self, button: Button) -> None:
        sidebar_button = bool(button.id and button.id.startswith(('nav-', 'section-', 'sidebar-')))
        if sidebar_button:
            self._select_input_region('panel')
        if self._inspection_active() and not sidebar_button:
            return
        if getattr(self,"layer_observation",None) is not None:
            return
        # Win32 mouse dispatch calls this entry directly, bypassing Pressed.
        # 右栏与左编辑器相互独立（2026-10-25 定稿，见 test_independent_sidebar_261025）：
        # 地图浮层／对话篡改开着时仍可点导航切右栏；右栏宿主切页会结束这次右栏编辑，
        # 地图浮层继续存在。右栏面板内容本身的点击仍由 tamper_host 模态吞掉。
        side_tamper = (getattr(self, 'world_tamper_editor', None) is not None
                       and getattr(self.world_tamper_editor, 'host', 'map') == 'side')
        if (self._active_tamper_editor() is not None and not side_tamper
                and not (getattr(self, 'world_tamper_editor', None) is not None
                         and (button.id or '').startswith(('nav-', 'section-', 'sidebar-')))):
            return
        if button.disabled:
            return
        button_id = button.id
        if button_id and button_id.startswith('settings-category-'):
            if self.panel_mode in ('home_settings', 'pause_settings'):
                self._select_settings_category(button_id.removeprefix('settings-category-'))
            return
        if self.handle_sidebar_tool(button_id):
            return
        if self._qol_button(button_id):
            return
        _trace_native(f"DreamApp.handle_button_press id={button_id}")
        if button_id and button_id.startswith('newgame-'):
            if self.panel_mode != 'home_newgame':
                return
            if button_id == 'newgame-back':
                self._newgame_cancel()
            elif button_id == 'newgame-reset':
                if self.newgame_phase == 'identity':
                    from ...core.dream_types import default_choice
                    self.newgame_dream_type = default_choice()
                    self.refresh_view()
                    return
                from ...core.run_options import default_selection
                selection = default_selection()
                self.newgame_sliders = selection['sliders']
                self.newgame_toggles = set(selection['toggles'])
                self.newgame_cursor = 0
                self.refresh_view()
            elif button_id == 'newgame-random' and self.newgame_phase == 'identity':
                from ...core.dream_types import random_choice
                import random
                self.newgame_dream_type = random_choice(random.SystemRandom())
                self.refresh_view()
            elif button_id == 'newgame-next':
                if self.newgame_phase == 'fragment':
                    self._confirm_newgame_fragment()
                else:
                    self._confirm_newgame_options()
            return
        if button_id and button_id.startswith("nav-"):
            self.open_sidebar_workspace(button_id.removeprefix("nav-"))
            return
        if button_id and button_id.startswith('section-'):
            self.open_sidebar_route(button_id.removeprefix('section-'))
            return
        if button_id and button_id.startswith("catalog-category-"):
            category = CatalogCategory(button_id.removeprefix("catalog-category-"))
            self.codex_page.activate_category(category)
            self.codex_page.move_entry(
                0,
                self.catalog_definitions,
                self.catalog_progress(),
                viewport_size=self._codex_viewport_size(),
            )
            self.query_one("#codex-list").focus()
        elif button_id and self._activate_home_item(button_id):
            # 主页选项（存档槽/删除/图鉴/设置/退出）统一走 _activate_home_item：
            # 键盘 Enter 与鼠标点击是同一条路径，两边行为不会走偏。
            return
        self.refresh_view()

def new_run_seed() -> int:
    """为一局新梦抽一个真正随机的种子。

    层层固定的根因就在这里：``create_session``/``_load_slot`` 原先写死
    ``seed=20260908``（存档槽再 +slot），而层型计划、层修饰符计划、容器与
    植物布局全部由种子确定性推导——同一个种子当然每次都得到同一串层型
    （第 1、2 层永远「气密」）。

    种子本身仍必须是「一局固定」的：同一局里换层要能复现，读档也要能复现，
    所以随机只发生在**开局那一刻**，之后一切照旧由这个数推导。
    用 ``SystemRandom`` 而非 ``random``：不污染也没有依赖模块级随机流的状态，
    哪怕别处调用过 ``random.seed()`` 也不影响开局的随机性。
    """
    return random.SystemRandom().randrange(1, 2**31 - 1)
