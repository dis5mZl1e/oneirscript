"""One map-bounded editor host and read-only map preview for both controllers."""
from rich.text import Text
from textual.geometry import Region

from ..i18n import tr
from . import tamper_presentation as p


class TamperHostMixin:
    def _active_tamper_editor(self):
        return getattr(self, 'world_tamper_editor', None) or self.tamper_editor

    def _prepare_tamper_entry(self) -> bool:
        """进入篡改前清掉会与浮层抢输入/抢显示的临时状态。

        篡改宿主是地图区的模态编辑层；瞄准、观察、物品菜单、格子详情、
        自我察觉等若继续留着，会出现「两层同时可见」或按键先落到旧状态。
        """
        if (getattr(self, 'controls_help_open', False) or getattr(self, 'qol_confirmation', None)
                or getattr(self, 'qol_searching', False) or getattr(self, 'board_editor', None) is not None):
            return False
        if (getattr(self, 'equipment_choice', None) is not None
                or getattr(self, 'lens_offer_scene', None)
                or getattr(self, 'debug_panel_open', False)
                or getattr(self, '_floor_transition', None) is not None
                or getattr(self.session.state, 'run_over', False)):
            # 完整的模态交易/演出不能在半途叠一层篡改浮层。
            return False
        if getattr(self, 'panel_mode', None) in ('pause', 'pause_settings', 'home', 'home_saves',
                                                 'home_newgame', 'home_catalog', 'home_history'):
            return False
        self._cancel_attack_confirmation(refresh=False)
        if getattr(self, 'aiming', False) or getattr(self, 'sentence_aim', None) is not None:
            self.cancel_aim()
        if getattr(self, 'sentence_aim', None) is not None:
            self._cancel_sentence_aim()
        if getattr(self, 'observe_mode', False):
            self.exit_observe()
        if getattr(self, 'item_menu_target', None) is not None:
            self.close_item_menu()
        if getattr(self, 'cell_detail_target', None) is not None:
            self.close_cell_detail()
        if getattr(self, 'anomaly_detail_target', None) is not None:
            self.close_anomaly_detail()
        if getattr(self, 'pickup_target', None) is not None:
            self.pickup_target = None
        self._panel_enter_mode = None
        self._close_self_audit(refresh=False)
        if getattr(self, 'panel_locked', False):
            self.release_cursor_lock()
        return True

    def _capture_tamper_view(self, editor):
        state = self.session.state
        editor.ui_context = (id(state), state.layer_key())
        editor.return_context = {name: getattr(self, name, None) for name in
            ('panel_mode', 'panel_scroll', 'panel_selection', 'hover_cell')}
        editor.return_context['hover_target'] = state.hover_target
        editor.preview_cursor = getattr(self,'hover_cell',None) or (state.player.x, state.player.y)

    def _restore_tamper_view(self, editor):
        state = self.session.state
        if editor.ui_context != (id(state), state.layer_key()):
            return
        for name, value in editor.return_context.items():
            if name == 'hover_target':
                state.hover_target = value
            elif name != 'panel_mode' or not (self.home_mode or state.run_over):
                setattr(self, name, value)

    def _toggle_tamper_map(self):
        editor = self._active_tamper_editor()
        if editor is None:
            return
        editor.map_preview = not editor.map_preview
        if getattr(self, 'world_tamper_editor', None) is not None:
            # 右侧面板保持原界面后，地图预览期间用气泡提示怎么回到编辑。
            self.show_toast(tr('返回编辑：V / Esc'))
        if editor.map_preview:
            editor.preview_cursor = editor.preview_cursor or (self.session.state.player.x, self.session.state.player.y)
            self.hover_cell = editor.preview_cursor
        else:
            self.hover_cell = editor.return_context.get('hover_cell')
        self.refresh_view()

    def _tamper_preview_key(self, key):
        editor = self._active_tamper_editor()
        if editor is None:
            return False
        if key.lower() == 'v':
            self._toggle_tamper_map()
            return True
        if not editor.map_preview:
            return False
        if key in ('escape', 'q'):
            self._toggle_tamper_map()
            return True
        moves = {'up': (0,-1), 'w': (0,-1), 'down': (0,1), 's': (0,1),
                 'left': (-1,0), 'a': (-1,0), 'right': (1,0), 'd': (1,0)}
        if key in moves:
            state = self.session.state
            x,y = editor.preview_cursor or (state.player.x,state.player.y)
            dx,dy = moves[key]
            self._tamper_preview_point((max(0,min(state.width-1,x+dx)), max(0,min(state.height-1,y+dy))))
        return True

    def _tamper_preview_point(self, point):
        editor = self._active_tamper_editor()
        if editor is not None and editor.map_preview and point is not None:
            editor.preview_cursor = point
            # 区域聚流的落点选择：观察光标即落点（明确、可见，不自动换源）。
            word_id = getattr(editor, "word_id", "")
            if (word_id in ('gather_liquid', 'gather_gas')
                    and getattr(editor.slot, 'region_members', ())):
                editor.gather_destination = point
            self.hover_cell = point
            self.refresh_view()

    def _tamper_observation_text(self, state, width):
        editor = self._active_tamper_editor()
        text = Text(tr('篡改 · 地图观察') + '\n', style='bold #9ab8d9')
        text.append(tr('[返回编辑 V]') if editor.map_preview else tr('[查看地图 V]'), style='bold ' + p.CONDITION)
        text.append('\n' + tr('[取消篡改]') + '\n', style=p.MUTED)
        if getattr(self, 'world_tamper_editor', None) is not None:
            slot = editor.slot
            text.append(tr('目标：{name}', name=slot.display_name()) + '\n', style=slot.color)
            if slot.enemy is not None:
                text.append(tr('完整度 {n} · {alert}', n=slot.enemy.integrity, alert=tr(slot.enemy.alert_state)) + '\n')
        elif editor.group is not None:
            text.append(tr('选词：{word}', word=editor.group.label) + '\n', style=p.WORD)
        if editor.map_preview:
            x,y = editor.preview_cursor
            text.append(tr('观察格：({x},{y})', x=x,y=y) + '\n', style=p.CONDITION)
            if state.is_visible(x,y) or (x,y) in state.developed_for_depth():
                text.append(self._hover_text(state, width))
                for line in self._hover_extra_lines(state,x,y):
                    text.append('\n')
                    text.append_text(line)
        else:
            text.append(tr('编辑不推进回合；V 查看地图。'), style=p.MUTED)
        lines = p.folded_lines(text, width)
        self._panel_rows = [-1] * len(lines)
        # The two short buttons may wrap in narrow windows. Derive row identity
        # from separately wrapped labels rather than assuming one physical row.
        title_rows = len(p.folded_lines(tr('篡改 · 地图观察'), width))
        view_rows = len(p.folded_lines(tr('[返回编辑 V]') if editor.map_preview else tr('[查看地图 V]'), width))
        cancel_rows = len(p.folded_lines(tr('[取消篡改]'), width))
        for row in range(title_rows, min(len(lines),title_rows+view_rows)):
            self._panel_rows[row] = 980
        for row in range(title_rows+view_rows,min(len(lines),title_rows+view_rows+cancel_rows)):
            self._panel_rows[row] = 981
        return Text('\n').join(lines)

    def _tamper_side_click(self, key):
        if key == 'tamper:view':
            self._toggle_tamper_map()
        elif key == 'tamper:cancel':
            if getattr(self, 'world_tamper_editor', None) is not None:
                self.close_world_tamper_editor()
            else:
                self.close_tamper_editor()

    def _refresh_tamper_overlay(self):
        try:
            widget = self.query_one('#tamper-overlay')
            pane = self.query_one('#map-pane')
            dialogue = self.query_one('#map-overlay')
        except Exception:
            return
        editor = self._active_tamper_editor()
        if editor is None:
            widget.styles.display = 'none'
            return
        state = self.session.state
        context = (id(state), state.layer_key())
        world_editor = getattr(self, 'world_tamper_editor', None) is not None
        valid = not self.home_mode and not state.run_over and (not editor.ui_context or editor.ui_context == context)
        if world_editor:
            from ..core.tamper_world import _preview_current
            # 2026-10-23：篡改浮层不占用右侧面板，是否有效只看编辑对象本身。
            valid = valid and _preview_current(state,editor.sentence,editor.slot_index)
        else:
            valid = valid and self.panel_mode == 'event_dialog' and self._tamper_target_alive(state,editor.target)
        if not valid:
            if world_editor:
                self.close_world_tamper_editor(refresh=False)
            else:
                self.close_tamper_editor(refresh=False)
                from ..core.tamper_views import current_tamper_target
                if self.panel_mode=='event_dialog' and current_tamper_target(state) is None and not (self.home_mode or state.run_over):
                    self.panel_mode='world'
            widget.styles.display = 'none'
            # The next refresh renders the restored dialogue normally.
            if self.panel_mode == 'event_dialog' and not self.home_mode and not state.run_over and hasattr(self,'_event_dialog_text'):
                dialogue.update(self._event_dialog_text(state)); dialogue.styles.display = 'block'
            if hasattr(self,'call_after_refresh'):
                self.call_after_refresh(self.refresh_view)
            return
        dialogue.styles.display = 'none'
        if editor.map_preview:
            widget.styles.display = 'none'
            return
        content = pane.content_size
        width = max(1,min(content.width,int(content.width*.9)))
        height = max(1,min(content.height,int(content.height*.9)))
        region = Region((content.width-width)//2,(content.height-height)//2,width,height)
        if world_editor:
            right_rows = getattr(self,'_panel_rows',[])
            body = self._world_tamper_visible_text(state,max(1,width-4),max(1,height-2))
            self._panel_rows = right_rows
        else:
            body = self._tamper_panel_text(state,editor,max(1,width-4),max(1,height-2))
        widget.update(body)
        widget.styles.width = width; widget.styles.height = height
        widget.styles.offset = (region.x,region.y)
        widget.styles.display = 'block'
