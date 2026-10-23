"""Read-only sound forecast and chaos UI; never emits a sound or rolls risk."""
from __future__ import annotations

import re

from rich.cells import cell_len
from rich.text import Text
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from ..core import sound_preview
from ..core.chaos import chaos_risk_tier, clamp_chaos
from ..data.tamper_schema import CHAOS_MAX, CHAOS_DECAY_INTERVAL
from ..i18n import tr

# 第十九节 §3／§10.1：噪音／混乱／声径与次要文字全部取自面板字段注册表。
from .panel_fields import FIELD_COLORS as _PANEL_FIELDS

NOISE_COLOR = _PANEL_FIELDS['noise']
CHAOS_COLOR = _PANEL_FIELDS['chaos']
MUTED = _PANEL_FIELDS['muted']
RANGE_COLOR = _PANEL_FIELDS['range']
TRACK_COLOR = _PANEL_FIELDS['track']
NOISE_SCALE = 20


def noise_preview(app):
    """Forecast the selected action, otherwise a step on the current tile.

    Observing a remote tile or browsing inventory must not change this context.
    This is evaluated on world/UI invalidation, not the animation frame timer.
    """
    state = app.session.state
    pulses = []
    context = '本格踩踏预计'
    pending = getattr(app, 'sentence_aim', None)
    if getattr(app, 'aiming', False):
        index = getattr(app, 'throw_item_index', None)
        target = ((pending or {}).get('cursor') or getattr(app, '_aim_free_cursor', None)
                  or getattr(app, '_aim_assist_pos', None))
        if index is not None:
            context = '投掷落点预计'
            if 0 <= index < len(state.inventory):
                landing = app._throw_landing_cell()
                if landing is not None and state.is_visible(*landing):
                    pulses.append(sound_preview.throw_landing_preview(state, state.inventory[index], landing))
        elif getattr(app, 'fire_once_index', None) is not None:
            context = '一次性发射预计'
            index = app.fire_once_index
            if 0 <= index < len(state.inventory):
                # Current flare payload has no sound entry. Do not invent one.
                pulses.append(sound_preview.pulse_preview(state, (state.player.x, state.player.y), 0))
        else:
            context = '发射载荷预计'
            choice = getattr(app, 'aim_action_choice', None)
            if pending:
                key = pending.get('key')
            elif isinstance(choice, dict):
                key = choice.get('key')
            else:
                key = choice
            if pending and pending.get('command', 'use_equipment_sentence') == 'use_equipment_sentence':
                pulses.append(sound_preview.pulse_preview(state, (state.player.x, state.player.y), 0))
            else:
                plan = state.equipment.plan_action('fire', choice=key)
                spec = dict(plan.projectile_profile)
                if not spec.get('pulse'):
                    pulses.append(sound_preview.pulse_preview(state, (state.player.x, state.player.y), 0))
                elif target is not None:
                    from ..core.throwing import flight_path
                    from ..core.construct_environments import reflected_path
                    path = reflected_path(state, (state.player.x, state.player.y),
                                          flight_path((state.player.x, state.player.y), tuple(target)))
                    for x, y in path[:int(spec.get('range', 12))]:
                        # Unknown geometry and wall-break outcomes cannot be
                        # predicted by looking through the player's knowledge.
                        if not state.is_visible(x, y) or state.cell(x, y).solid:
                            break
                        entity = state.entity_at(x, y)
                        if entity is not None and entity is not state.player:
                            pulses.append(sound_preview.equipment_pulse_preview(state, (x, y), spec))
                            break
                    else:
                        # A pulse is emitted on entity impact, not in empty air.
                        pulses.append(sound_preview.pulse_preview(state, tuple(target), 0))
    else:
        path = getattr(app, 'path', ())
        if path and not getattr(app, 'observe_mode', False):
            context = '下一步踩踏预计'
            pulses.append(sound_preview.footstep_preview(state, path[0]))
        else:
            pulses.append(sound_preview.footstep_preview(state))
    radius = max((p['radius'] for p in pulses), default=None)
    return dict(context=context, radius=radius, pulses=pulses)


def summary_text(preview, chaos, *, width=44):
    radius = preview['radius']
    noise = f'{radius if radius is not None else "—"}/{NOISE_SCALE}'
    chaos = f'{clamp_chaos(chaos)}/{CHAOS_MAX}'
    from ..data.semantic_icons import semantic_icon
    noise_icon = semantic_icon('noise.pulse')
    chaos_icon = semantic_icon('stat.chaos')
    fixed = ((noise_icon + ' ') if noise_icon else '') + f'{tr("噪音")}  {noise}  ' \
        + ((chaos_icon + ' ') if chaos_icon else '') + f'{tr("混乱")} {chaos}'
    bars = min(12, max(0, width - cell_len(fixed) - 1))
    fill = min(bars, round(bars * max(0, radius or 0) / NOISE_SCALE))
    text = Text((noise_icon + ' ') if noise_icon else '', style=NOISE_COLOR, no_wrap=True)
    text.append(tr('噪音') + ' ', style=NOISE_COLOR)
    if bars:
        text.append('┃' * fill, style=NOISE_COLOR)
        text.append('┊' * (bars-fill), style=TRACK_COLOR)
        text.append(' ')
    text.append(noise, style=NOISE_COLOR if radius is not None else MUTED)
    if radius is not None and radius > NOISE_SCALE:
        text.append('›', style='#f2bd84')
    text.append('  ' + ((chaos_icon + ' ') if chaos_icon else '')
                + tr('混乱') + ' ' + chaos, style=CHAOS_COLOR)
    return text


def detail_text(app, preview):
    state = app.session.state
    text = Text(tr('本次预计声音'), style='bold ' + NOISE_COLOR)
    text.append('\n' + tr(preview['context']), style='#ffffff')
    radius = preview['radius']
    text.append('\n' + tr('最终声径：{n} 格', n=radius) if radius is not None
                else '\n' + tr('落点未确定：最终声径暂不可知。'), style=RANGE_COLOR)
    text.append('\n' + tr('20 是固定显示量程，不是声音上限，也不是统一警戒阈值。'), style=MUTED)
    for pulse in preview['pulses']:
        x, y = pulse['origin']
        text.append('\n' + tr('发声点：({x},{y}) · 基础 {base} · 最终 {radius}',
                             x=x, y=y, base=pulse['base'], radius=pulse['radius']), style='#b6cae8')
        for source in pulse['sources']:
            text.append('\n  ' + str(source), style='#70cbbb')
        if pulse.get('full_alert'):
            text.append('\n' + tr('强诱引：可能直接引起追踪。'), style='#f18e9b')
    text.append('\n' + tr('这里是行动预计，不是正在持续发声；0 只表示本次预计动作无声。'), style=MUTED)
    text.append('\n' + tr('射击、投掷与声影可在远处发声；声径不等于玩家身体的暴露距离。'), style=MUTED)
    from ..core.construct_environments import active
    echoes=[field for field in active(state) if field['kind']=='echo_pulse']
    if echoes and state.is_visible(*echoes[-1]['position']):
        echo = sound_preview.echo_ability_preview(state)
        if state.is_visible(*echo['origin']):
            text.append('\n' + tr('活动声影下一拍：({x},{y}) · 声径 {n}',
                                 x=echo['origin'][0], y=echo['origin'][1], n=echo['radius']), style=RANGE_COLOR)
    # §11 H1：听觉线索只给方向、距离档、类别与时间；未知声源不写坐标，
    # 视野内已知声源才补精确位置。线索按真实回合过期，不跟随声源移动。
    from ..core.enemies import sound_category_name
    retention = state._clue_retention()
    clues = [clue for clue in state.heard_sound_clues
             if state.time - int(clue.get("time", 0)) < retention]
    if clues:
        text.append('\n\n' + tr('听觉线索'), style='bold ' + RANGE_COLOR)
        bearing = state._sound_bearing_active()
        selected = getattr(app, '_signal_clue_index', None)
        wall_entries = 0
        for index, clue in enumerate(clues):
            where = (f"({clue['x']},{clue['y']})" if clue.get('known')
                     else tr('方向与距离可知，位置未知'))
            shown_sector = clue.get('fine_sector') or clue['sector']
            # §16.4：听诊器只在凝听时给相邻墙后的入口；只有真实近距
            # 才顺带给距离档，不把远处声音说成近在墙后。
            entry = clue.get('entry')
            near = bool(entry) and bool(clue.get('wall_near'))
            if bearing or near:
                line = tr('{sector} · {band} · {category} · {where} · 第 {turn} 回合',
                          sector=tr(shown_sector), band=tr(clue['band']),
                          category=tr(sound_category_name(clue['category'])),
                          where=where, turn=int(clue.get('time', 0)))
            else:
                line = tr('{sector} · {category} · {where} · 第 {turn} 回合',
                          sector=tr(shown_sector),
                          category=tr(sound_category_name(clue['category'])),
                          where=where, turn=int(clue.get('time', 0)))
            if entry:
                wall_entries += 1
                line += ' · ' + tr('隔墙入口：({x},{y})',
                                   x=int(entry[0]), y=int(entry[1]))
            if clue.get('strength'):
                line += ' · ' + tr('强度：{strength}', strength=tr(clue['strength']))
            if clue.get('multiple'):
                line += ' · ' + tr('多次响动')
            prefix = f'▶ {index + 1}. ' if index == selected else f'{index + 1}. '
            text.append('\n' + prefix + line,
                        style='bold bright_yellow' if index == selected else '#b6cae8')
        text.append('\n' + tr('线索保留 {n} 个真实回合；未知声源不给敌名与精确坐标。',
                             n=retention), style=MUTED)
        if wall_entries:
            text.append('\n' + tr('听诊器只对相邻实墙后的真实声音给入口与近距判断；远墙悬停不生效。'),
                        style=MUTED)
        text.append('\n' + tr('数字键或点击选择线索并在地图高亮；L 凝听一回合（确认后才会等待）。'),
                    style=MUTED)
        if not bearing:
            text.append('\n' + tr('远近档需要「听声辨向」：等待一次后四个回合内显示。'), style=MUTED)
    # 听界与循声定位是显式信息权限：只标发声格与时刻，不显示周围地形。
    from ..data.perception import (CONFIRMED_SOURCE_RETENTION,
                                   LISTEN_REALM_TURNS)
    confirmed = [entry for entry in state.confirmed_sound_sources
                 if state.time - int(entry.get('time', 0)) < CONFIRMED_SOURCE_RETENTION]
    if confirmed:
        text.append('\n\n' + tr('确认声源（循声定位）'), style='bold ' + RANGE_COLOR)
        for entry in confirmed:
            text.append('\n* ({x},{y}) · 第 {turn} 回合确认'.format(
                x=int(entry.get('x', -1)), y=int(entry.get('y', -1)),
                turn=int(entry.get('time', 0))), style='#b6cae8')
    if state.time < getattr(state, 'listen_realm_until', 0):
        markers = [entry for entry in state.precise_sound_markers
                   if state.time - int(entry.get('time', 0)) < LISTEN_REALM_TURNS]
        text.append('\n\n' + tr('听界标记（剩余 {n} 回合）',
                               n=max(0, state.listen_realm_until - state.time)),
                    style='bold ' + RANGE_COLOR)
        for entry in markers[-8:]:
            text.append('\n+ ({x},{y}) · {category} · 第 {turn} 回合'.format(
                x=int(entry.get('x', -1)), y=int(entry.get('y', -1)),
                category=tr(sound_category_name(entry.get('category', ''))),
                turn=int(entry.get('time', 0))), style='#b6cae8')
        text.append('\n' + tr('听界只记录该次声音的发生点，不检测安静目标，也不照亮周围。'),
                    style=MUTED)
    text.append('\n\n' + tr('混乱度'), style='bold ' + CHAOS_COLOR)
    value = clamp_chaos(state.chaos)
    text.append(f'\n{value}/{CHAOS_MAX} · ' + tr(chaos_risk_tier(value)), style=CHAOS_COLOR)
    credit = float(state.chaos_decay_credit) if value else 0.0
    text.append('\n' + tr('平复进度：{n}/{m} · 距降低一点还需 {remaining} 合资格耗时',
                         n=f'{credit:g}', m=f'{CHAOS_DECAY_INTERVAL:g}',
                         remaining=f'{max(0,CHAOS_DECAY_INTERVAL-credit):g}'), style='#a6cbbf')
    text.append('\n' + tr('有效移动、攻击、使用的实付耗时计入平复；等待、免费查看、篡改自身不计入。'), style=MUTED)
    text.append('\n' + tr('连续篡改压力：{n}', n=max(0, min(3, state.tamper_pressure))), style='#f18e9b')
    text.append('\n' + tr('混乱度、连续压力和崩解度分别结算；心理状态也可能影响副作用。'), style=MUTED)
    text.append('\n' + tr('篡改预览只报价，不提前增加实际混乱；这里只显示风险档位。'), style=MUTED)
    quote = tamper_quote(app)
    if quote is not None:
        cost, delta, after = quote
        text.append('\n' + tr('当前篡改报价：想象力 {cost} · 混乱 +{delta} → {after}',
                             cost=cost, delta=delta, after=after), style='#ecb487')
        from ..core.tamper_pipeline import risk_note
        text.append('\n' + risk_note(state, after, imagination_cost=cost), style='#f18e9b')
    return text


def clue_line_map(text: Text) -> dict[int, int]:
    """线索行号 → 线索下标；鼠标与数字键共用同一份列表顺序。"""
    first = Text(tr('听觉线索'))
    lines = text.plain.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line == first.plain)
    except StopIteration:
        return {}
    mapping = {}
    for index in range(start + 1, len(lines)):
        match = re.match(r'^(?:▶ )?(\d+)\. ', lines[index])
        if match:
            mapping[index] = int(match.group(1)) - 1
    return mapping


def tamper_quote(app):
    state = app.session.state
    editor = getattr(app, 'world_tamper_editor', None)
    if editor is not None:
        from ..core.tamper_world import word_allowed, word_cost_with_conditions
        if not word_allowed(editor.word_id, editor.slot, editor.sentence):
            return None
        plan = editor.range_plan
        if editor.range_mode == 'vision':
            if plan is None:
                return None
            cost, delta = plan.imagination, plan.chaos_delta
        else:
            cost, delta = word_cost_with_conditions(state, editor.word_id, editor.slot,
                                                    editor.condition_ids)
        return cost, delta, clamp_chaos(state.chaos+delta)
    editor = getattr(app, 'tamper_editor', None)
    if editor is not None and editor.group is not None and editor.transition is not None:
        from ..core.tampering import make_request, preview_tamper
        quote = preview_tamper(state, make_request(state, editor.target, editor.group.text_id,
                                                 editor.transition.transition_id))
        return quote.imagination_cost, quote.chaos_delta, quote.chaos_after
    return None


class SignalStatusLink(Static, can_focus=True):
    def on_mouse_down(self, event):
        event.stop()
        if event.button in (1, 3):
            self.app.toggle_signal_detail()

    def on_key(self, event):
        if event.key in ('enter', 'return', 'space'):
            # 底栏信号链接可聚焦。只有焦点区域已经切到面板时才用 Enter 打开
            # 信号详情；光标仍在 map 时把 Enter 让给行动键（玩家按 Enter 是
            # “行动”，不是“展开脚注”）。鼠标点击不受此限制。
            if getattr(self.app, 'cursor_zone', 'map') == 'panel':
                event.stop()
                event.prevent_default()
                self.app.toggle_signal_detail()


class SignalDetailText(Static):
    """点击线索行只选中并高亮，不移动、不投掷、不推进世界（§16.7）。"""

    def on_resize(self, event):
        # Width may settle one frame after the parent introduces its scrollbar.
        # Reflow the same existing contents; do not change this left pane's UI.
        width = self.content_size.width
        if width != getattr(self, '_settled_width', None):
            self._settled_width = width
            if getattr(self.app, 'signal_detail_open', False):
                self.call_after_refresh(self.app._refresh_signal_status)

    def on_mouse_down(self, event):
        event.stop()
        if event.button == 1:
            self.app.select_signal_clue_line(int(event.offset.y))


class InspectionPane(Vertical):
    """Screen-level host, positioned inside the left map region even in editors."""
    def on_mouse_down(self, event):
        event.stop()

    def on_mouse_move(self, event):
        event.stop()

    def on_mouse_scroll_up(self, event):
        event.stop()

    def on_mouse_scroll_down(self, event):
        event.stop()


class InspectionClose(Static):
    def on_mouse_down(self, event):
        event.stop()
        self.app.close_signal_detail()


class SignalListenLink(Static, can_focus=True):
    """鼠标／键盘确认凝听：只执行一次真实等待，不额外推进世界。"""
    def on_mouse_down(self, event):
        event.stop()
        if event.button == 1:
            self.app.confirm_listen()

    def on_key(self, event):
        if event.key in ('enter', 'return', 'space'):
            event.stop()
            event.prevent_default()
            self.app.confirm_listen()


class SignalStatusMixin:
    signal_detail_open = False
    # 左侧面板当前高亮的线索下标（按线索列表从旧到新）；None = 不高亮。
    _signal_clue_index: int | None = None
    _signal_clue_lines: dict[int, int] = {}

    def _inspection_active(self):
        return self.signal_detail_open or self._self_audit_visible()

    def _can_open_inspection(self):
        if getattr(self, 'world_tamper_editor', None) is not None:
            return False
        if getattr(self, 'tamper_editor', None) is not None:
            return False
        return not (self.home_mode or self.session.state.run_over or self._floor_transition is not None
                    or self.qol_confirmation is not None or self.controls_help_open
                    or self.settings_page.capture_target is not None)

    def toggle_signal_detail(self):
        if self.signal_detail_open:
            self.close_signal_detail()
            return
        if not self._can_open_inspection():
            return
        self._signal_kind='signals'
        if self._self_audit_visible():
            self._close_self_audit(refresh=False)
        self.signal_detail_open = True
        state = self.session.state
        self._signal_context = (id(state), state.depth, state.realm_id, state.realm_depth)
        self._signal_focus = self.focused
        self._signal_clue_index = None
        self._clear_held()
        self._refresh_signal_status()
        self.query_one('#signal-detail').display = True
        self.query_one('#signal-detail-scroll').scroll_home(animate=False)
        self.query_one('#signal-detail-scroll').focus()
        self.call_after_refresh(self._refresh_signal_status)

    def toggle_aim_detail(self):
        if self.signal_detail_open:
            self.close_signal_detail()
            return
        pending=getattr(self,'sentence_aim',None) or {}
        target=(pending.get('cursor') or getattr(self,'_aim_free_cursor',None)
                or getattr(self,'_aim_assist_pos',None))
        if target is None:
            state=self.session.state
            dx,dy=self.facing
            target=(state.player.x+dx,state.player.y+dy)
        if not self.session.state.inside_board(*target): return
        self.toggle_signal_detail()
        if self.signal_detail_open:
            self._signal_kind='cell'
            self._signal_cell_target=tuple(target)
            self._refresh_signal_status()

    def _inspection_cell_text(self):
        # Reuse the full layer/knowledge renderer. Its navigation state belongs
        # to the normal detail panel, so save and restore it around this read.
        fields=('cell_detail_target','detail_cursor','detail_scroll','_detail_line_count',
                '_detail_selectable','_detail_targets','_inspection_full_cell')
        missing=object()
        previous={name:getattr(self,name,missing) for name in fields}
        self.cell_detail_target=self._signal_cell_target
        self.detail_cursor=self.detail_scroll=0
        self._inspection_full_cell=True
        try:
            return self._cd_text(self.session.state)
        finally:
            for name,value in previous.items():
                if value is missing:
                    if hasattr(self,name): delattr(self,name)
                else: setattr(self,name,value)

    def close_signal_detail(self):
        self.signal_detail_open = False
        self._signal_clue_index = None
        self.query_one('#signal-detail').display = False
        focus = getattr(self, '_signal_focus', None)
        if focus is not None and focus.is_mounted and focus.display:
            focus.focus()
        else:
            self.set_focus(None)

    def _refresh_signal_status(self):
        preview = noise_preview(self)
        self.query_one('#signal-status').update(summary_text(
            preview, self.session.state.chaos,
            width=max(1, self.query_one('#signal-status').content_size.width or 36)))
        region = self.query_one('#map-pane').region
        if self.query_one('#layout').display and region.width:
            self._signal_region = region
        if not self.signal_detail_open:
            return
        state = self.session.state
        if (self.home_mode or state.run_over or
                self._signal_context != (id(state), state.depth, state.realm_id, state.realm_depth)):
            self.close_signal_detail()
            return
        self._fit_inspection_pane(self.query_one('#signal-detail'))
        cell_mode=getattr(self,'_signal_kind','signals')=='cell'
        self.query_one('#signal-detail-title').update(tr('当前对象详情' if cell_mode else '噪音与混乱度'))
        if cell_mode:
            self._signal_clue_lines = {}
            self.query_one('#signal-detail-text').update(self._inspection_cell_text())
        else:
            text = detail_text(self, preview)
            self._signal_clue_lines = clue_line_map(text)
            self.query_one('#signal-detail-text').update(text)
        self.query_one('#signal-listen').update(tr('凝听一回合 · L / 点击'))
        self.query_one('#signal-detail-close').update(tr('返回 · Esc / {key}',
            key=str(self.config.get('key_panel_detail' if cell_mode else 'key_panel_signals')).upper()))

    def _fit_inspection_pane(self, pane):
        region = self.query_one('#map-pane').region
        if region.width > 0 and self.query_one('#layout').display:
            self._signal_region = region
        else:
            region = getattr(self, '_signal_region', region)
        left, top = max(0, region.x), max(1, region.y)
        available = region.width or max(20, int(self.size.width*.62))
        height = min(region.height or self.size.height-3, self.query_one('Footer').region.y-top)
        pane.styles.width = max(12, available-2)
        pane.styles.height = max(4, height-2)
        pane.styles.offset = (left+1, top+1)
        from .region_themes import theme_for_realm
        pane.styles.background = theme_for_realm(self.session.state.realm_id, self.session.state.depth).panel_bg

    def begin_auto_walk(self, path):
        """自动寻路开始时离开凝听选取；设置路径本身不推进世界。"""
        if path and self.signal_detail_open:
            self.close_signal_detail()
        self.path = list(path)

    def select_signal_clue_line(self, line):
        """鼠标点中线索行：与数字键同样只改选中下标，零耗时。"""
        index = self._signal_clue_lines.get(int(line))
        if index is None or not self.signal_detail_open:
            return
        self._signal_clue_index = index
        self._refresh_signal_status()

    def confirm_listen(self):
        """凝听确认：关闭面板后真实等待一回合；打开/查看本身零耗时。"""
        if not self.signal_detail_open:
            return
        self.close_signal_detail()
        self.action_wait_turn()

    def _signal_key(self, key):
        if not self.signal_detail_open:
            return False
        if key in ('escape', 'q'):
            self.close_signal_detail()
        elif key == 'l':
            self._mark_key_handled(key)
            self.confirm_listen()
            return True
        elif key.isdigit() and key in '123456789':
            retention = self.session.state._clue_retention()
            count = sum(1 for clue in self.session.state.heard_sound_clues
                        if self.session.state.time - int(clue.get('time', 0)) < retention)
            index = int(key) - 1
            self._signal_clue_index = index if index < count else None
            self._refresh_signal_status()
        else:
            scroll = self.query_one('#signal-detail-scroll')
            if key in ('up', 'w'): scroll.scroll_relative(y=-1, animate=False)
            elif key in ('down', 's'): scroll.scroll_relative(y=1, animate=False)
            elif key == 'pageup': scroll.scroll_page_up(animate=False)
            elif key == 'pagedown': scroll.scroll_page_down(animate=False)
            elif key == 'home': scroll.scroll_home(animate=False)
            elif key == 'end': scroll.scroll_end(animate=False)
        self._mark_key_handled(key)
        return True
