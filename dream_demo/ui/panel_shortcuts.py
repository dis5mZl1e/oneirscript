"""Context-aware Alt entry aliases, shared by configuration and help."""
from ..controls import PANEL_SHORTCUTS


class PanelShortcutsMixin:
    def _handle_panel_shortcut(self, event):
        if self.settings_page.capture_target is not None:
            return False
        key = event.key.lower()
        entry = next((entry for entry in PANEL_SHORTCUTS
                      if self.config.get(entry.setting) == key), None)
        if entry is None:
            return False
        self._mark_key_handled(event.key)
        event.stop()
        event.prevent_default()
        action = entry.action
        if self._floor_transition is not None or self.session.state.run_over:
            return True
        if action == 'elevation':
            if not self._inspection_active() and not self.controls_help_open and self.qol_confirmation is None:
                self.action_elevation_observe()
            return True
        if action in ('self', 'signals'):
            if action == 'self':
                self._toggle_self_audit()
            else:
                self.toggle_signal_detail()
            return True
        if action == 'detail' and self.layer_observation is not None:
            if (self.cell_detail_target is not None or self.anomaly_detail_target is not None
                    or self.item_menu_target is not None):
                self._layer_close_detail()
            else:
                self.layer_observation.legend_open = False
                self.open_cell_detail(self.layer_observation.cursor)
                self._sync_layer_observation_ui()
            return True
        if action=='detail' and (self.aiming or self.sentence_aim is not None):
            self.toggle_aim_detail()
            return True
        sidebar_navigation = action in ('inventory', 'equipment', 'portents', 'insights', 'nearby',
                                         'actions', 'tasks', 'workspace_prev', 'workspace_next')
        if ((self._inspection_active() and not sidebar_navigation)
                or self.controls_help_open or self.qol_confirmation is not None):
            return True
        if action == 'layers' and self.layer_observation is not None:
            self._layer_key('f3')
            return True
        if action == 'display':
            self.action_image_preview()
            return True
        if action == 'layers':
            self.action_cycle_map_observe()
            return True
        if not self.home_mode and action in ('codex', 'settings') and self.panel_mode in ('pause', 'pause_codex', 'pause_settings'):
            self._open_shortcut_page(action)
            return True
        if self.home_mode:
            if action == 'codex': self._open_codex()
            elif action == 'settings': self._open_settings()
            elif action == 'history': self._open_history()
            return True
        if action == 'board' and self.board_editor is not None:
            self.board_editor_action('cancel')
            return True
        if action == 'tamper' and self._active_tamper_editor() is not None:
            # Keep the same gradual Esc flow; don't drop a draft in one key.
            if self.world_tamper_editor is not None:
                self.handle_world_tamper_key('escape')
            else:
                self.handle_tamper_key('escape')
            return True
        if (self._modal_menu_open(allow_inspection=sidebar_navigation) or self.aiming or self.sentence_aim is not None
                or self.layer_observation is not None or self.qol_searching
                or self.insight_replace_target is not None or self.memory_replace_target is not None):
            return True
        if self.panel_mode == 'event_dialog':
            if action == 'tamper':
                self.open_tamper_editor()
            return True
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        if action == 'detail':
            self._shortcut_detail()
        elif action == 'context':
            target = self._shortcut_target()
            self.context_menu_target = target
            self.panel_mode = 'actions'
            self.panel_selection = 0
            self.panel_scroll = 0
            self.refresh_view()
        elif action == 'board':
            self.open_board_editor()
        elif action == 'tamper':
            self.open_world_tamper_editor()
        elif action in ('codex', 'settings'):
            self._open_shortcut_page(action)
        elif action == 'item_detail':
            self._management_open_selected()
        elif action == 'display_toggle':
            # 2026-10-24 六工作区：总览页随 ROUTES 重排退场，Alt+W 只留构想固定。
            if self.panel_mode == 'actions' and self._panel_subpage_id() == 'constructs':
                self.handle_sidebar_tool('sidebar-pin')
        elif action in ('workspace_prev', 'workspace_next'):
            self._move_panel_tab(-1 if action == 'workspace_prev' else 1)
        elif action == 'history':
            # 梦境历史（2026-10-24 键位治理 B7）：游戏内不再静默吞键——Esc 菜单
            # 门槛（_can_open_pause_menu：panel_mode 已回 world、角色静止、无任何
            # 面板/模式/动作）允许时打开暂停菜单并直达旧梦回忆页；不允许时维持
            # 原状。暂停菜单态的原入口保留（panel_shortcuts 的模态卫兵在其前，
            # 这条分支实际是兜底，不动它）。
            if self.panel_mode == 'pause':
                self._open_history()
            elif self.panel_mode == 'world' and self._can_open_pause_menu():
                # 旧梦回忆借用暂停菜单的覆盖机制；仍只允许从事件记录页进入，
                # 不因 Esc 菜单门槛放宽（2026-10-26）而改变 Alt+8 的旧语义。
                self._open_ingame_history()
        else:
            self._toggle_panel(action)
        return True

    def _open_ingame_history(self) -> None:
        """游戏内直达旧梦回忆页（2026-10-24 键位治理 B7）。

        历史页 UI（#history-page）挂在 #home 里，而 #home 在游戏内整体隐藏
        （与 codex/settings 当年移出 #home 的原因相同，但本页未迁移）——所以
        借用暂停菜单的覆盖机制：先 open_pause_menu 收起世界布局并复位焦点，
        再点亮 #home、藏起标题/副标题/主菜单行，只露出回忆页。
        Esc/Q 逐层退回暂停菜单（on_key 的 home_history 分支与
        _close_ingame_history）；panel_mode 在此期间是 home_history，
        已列入 _modal_menu_open，模态卫兵一律生效。
        """
        self.open_pause_menu()
        self._open_history()
        self.query_one("#pause-menu").styles.display = "none"
        self.query_one("#home").styles.display = "block"
        for selector in ("#home-title-row", "#home-subtitle-row", "#home-menu-row"):
            try:
                self.query_one(selector).styles.display = "none"
            except Exception:  # pragma: no cover - 极端尺寸下缺控件的兜底
                pass
        self.query_one("#history-page").styles.display = "block"
        self._refresh_history_view()

    def _close_ingame_history(self) -> None:
        """收起游戏内旧梦回忆覆盖层：回暂停菜单（B7 的返回路径）。

        只在覆盖层真的开着时动作；#home 的三行装饰恢复默认 display，
        暂停菜单重新亮出（panel_mode 回 pause，Esc 即「继续」）。
        """
        if self.panel_mode != "home_history":
            return
        self.panel_mode = "pause"
        self.query_one("#home").styles.display = "none"
        for selector in ("#home-title-row", "#home-subtitle-row", "#home-menu-row"):
            try:
                self.query_one(selector).styles.display = "block"
            except Exception:  # pragma: no cover - 极端尺寸下缺控件的兜底
                pass
        self.query_one("#history-page").styles.display = "none"
        self.query_one("#pause-menu").styles.display = "block"
        self.refresh_view()

    def _shortcut_target(self):
        """Alt+D／Alt+C 的目标解析：只认**明确**的观察对象。

        方案 §20 要求「不因上次鼠标停留残留选错对象」，所以 `context_menu_target`
        （上一次右键／菜单残留）不参与解析：观察模式取观察光标，普通地图取固定
        观察目标，两者都没有就回到脚下格。
        """
        if self.observe_mode and self.observe_cursor is not None:
            return self.observe_cursor
        return self.pinned_target or (
            self.session.state.player.x, self.session.state.player.y)

    def _shortcut_detail(self):
        state = self.session.state
        if self.cell_detail_target is not None:
            self.close_cell_detail()
        elif self.item_menu_target is not None:
            self.close_item_menu()
        elif self.anomaly_detail_target is not None:
            self.close_anomaly_detail()
        elif self.observe_mode:
            self.open_cell_detail(self._shortcut_target())
        elif self.panel_mode == 'catalog':
            self._open_anomaly_detail(self.panel_selection)
        elif self.panel_mode in ('inventory', 'equipment'):
            if self.panel_mode == 'equipment':
                indices = [i for i, item in enumerate(state.inventory) if item.slot]
                index = indices[self.panel_selection] if 0 <= self.panel_selection < len(indices) else None
            else:
                index = self.panel_selection if self.panel_selection in self._inventory_visible_indices() else None
            if index is not None:
                self._open_item_menu(index)
        else:
            self.open_cell_detail(self._shortcut_target())

    def _open_shortcut_page(self, action):
        target = 'pause_codex' if action == 'codex' else 'pause_settings'
        if self.panel_mode == target:
            if not self._restore_shortcut_page():
                self.close_pause_menu()
            return
        if getattr(self, '_shortcut_page_return', None) is None:
            self._shortcut_page_return = (self.panel_mode, self.panel_selection, self.panel_scroll,
                                          self.cursor_zone, self.focused)
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        self._hide_pause_views()
        self.open_pause_menu()
        self.pause_cursor = self.PAUSE_OPTIONS.index('catalog' if action == 'codex' else 'settings')
        self.activate_pause_option()

    def _restore_shortcut_page(self):
        saved = getattr(self, '_shortcut_page_return', None)
        if saved is None:
            return False
        self._shortcut_page_return = None
        self._hide_pause_views()
        self.query_one('#layout').display = True
        self.panel_mode, self.panel_selection, self.panel_scroll, self.cursor_zone, focus = saved
        if self.panel_mode == 'pause':
            self.query_one('#layout').display = False
            self.query_one('#pause-menu').display = True
        if focus is not None and focus.is_mounted and focus.display:
            focus.focus()
        else:
            self.set_focus(None)
        self.refresh_view()
        return True
