"""Player-facing navigation, shared confirmations and context feedback."""
from hashlib import sha256

from rich.text import Text
from textual.css.query import NoMatches
from textual.geometry import Region

from ..controls import panel_for_key
from ..core.entities import ActionResult
from ..i18n import tr


class QoLUIMixin:
    # 全屏页（主页 / 图鉴 / 设置 / 联想盘 / 暂停菜单）：游戏内没有可见的地图区时，
    # 浮层退到当前页面自己的区域。见 `_overlay_stage`。
    OVERLAY_STAGE_PAGES = ('#codex-page', '#settings-page', '#board-editor',
                           '#pause-menu', '#home')

    def _overlay_stage(self):
        """Modal 可以占用的区域：游戏内是地图区，其余页面是页面自身。

        为什么要限制：Textual 合成器按**背景控件**的左右边界给每行切段
        （`Compositor.cuts`），凡是跨在切口上的双宽汉字会被切成两个空白半格。
        浮层只要整个落在同一个背景控件里，面板内部就不会出现背景切口；右栏与
        底栏都在地图区之外，因此打开期间保持可见（2026-10-21 E3）。
        """
        try:
            pane = self.query_one('#map-pane')
        except NoMatches:
            pane = None
        if pane is not None and pane.is_attached and pane.display and pane.visible \
                and pane.region.width and pane.region.height:
            return pane.region
        for selector in self.OVERLAY_STAGE_PAGES:
            nodes = self.query(selector)
            if not nodes:
                continue
            page = nodes.first()
            if page.is_attached and page.display and page.visible \
                    and page.region.width and page.region.height:
                return page.region
        return self.screen.region

    def _occlude_under(self, rect, keep):
        """只隐藏 `rect` 下会引入合成切口的背景控件，返回可恢复的清单。

        规则按控件区域与 `rect` 的关系分三种：
        - 完整落在 `rect` 内：它的边界会切到面板内部 → 隐藏；
        - 完整包住 `rect`：它自己的边界在面板之外，只递归检查其子控件；
        - 与 `rect` 相交但两边都不包含：它至少有一条边落在面板内部 → 隐藏。
        浮层本身及其祖先永不隐藏；因此右栏、底栏等面板外的东西一个都不动。
        """
        hidden = []

        def hide(widget):
            hidden.append((widget, widget.styles.visibility))
            widget.styles.visibility = 'hidden'

        def walk(node):
            for child in node.children:
                if child is keep or child in keep.ancestors:
                    continue
                if not child.is_attached or not child.display or not child.visible:
                    continue
                region = child.region
                if not region.width or not region.height or not rect.overlaps(region):
                    continue
                if region.contains_region(rect):
                    # 完整包住面板（或与面板同域）：自身边界在面板之外，只查子控件。
                    walk(child)
                elif rect.contains_region(region):
                    hide(child)
                else:
                    hide(child)

        walk(self.screen)
        return hidden

    def _restore_occluded(self, hidden):
        for widget, visibility in hidden:
            if widget.is_attached:
                widget.styles.visibility = visibility

    def action_toggle_footer(self):
        from .app.footer import I18nFooter
        self.query_one(I18nFooter).toggle()

    def action_controls_help(self):
        if self._inspection_active():
            return
        if hasattr(self, '_active_tamper_editor') and self._active_tamper_editor() is not None:
            # 篡改编辑中不打开完整键位表，避免两层浮层叠在一起或抢走按键。
            return
        if getattr(self, 'controls_help_open', False):
            self._close_controls_help()
            return
        from .controls_help import ControlsReference
        self.path.clear()
        self._clear_held()
        self.controls_help_open = True
        self._controls_help_focus = self.focused
        self.set_focus(None)
        self.query_one('#controls-help-text').update(ControlsReference(self.config))
        self.query_one('#controls-help').display = True
        self.query_one('#controls-help-scroll').scroll_home(animate=False)
        self._fit_controls_help()

    def _fit_controls_help(self):
        """把键位表放进当前可用区（地图区 / 当前页面），并按窗口变化重排。"""
        if not getattr(self, 'controls_help_open', False):
            return
        nodes = self.query('#controls-help')
        if not nodes:
            return
        panel = nodes.first()
        if not panel.is_attached:
            return
        rect = self._overlay_stage()
        key = (rect.x, rect.y, rect.width, rect.height)
        if getattr(self, '_controls_help_fit', None) == key:
            return
        self._restore_occluded(getattr(self, '_controls_help_background', []))
        panel.styles.width = rect.width
        panel.styles.height = rect.height
        panel.styles.offset = (rect.x, rect.y)
        self._controls_help_fit = key
        self._controls_help_background = self._occlude_under(rect, panel)

    def _close_controls_help(self):
        self.controls_help_open = False
        self.query_one('#controls-help').display = False
        self._restore_occluded(getattr(self, '_controls_help_background', []))
        self._controls_help_background = []
        self._controls_help_fit = None
        focus = getattr(self, '_controls_help_focus', None)
        self.set_focus(focus if focus is not None and focus.is_attached else None)

    def _init_qol(self):
        self.controls_help_open = False
        self._controls_help_background = []
        self._controls_help_fit = None
        self.qol_confirmation = None
        self.qol_searching = False
        self._qol_background = []
        self._qol_fit = None
        self.inventory_query = ''
        self.inventory_filter = '全部'
        self.inventory_sort = '原序'
        self._qol_executing = False
        self._qol_last_context = None

    def _ask_qol(self, title, detail, action, valid=lambda: True, *, confirm_label=None):
        self.path.clear()
        self._clear_held()
        self.qol_confirmation = dict(title=title, detail=detail, action=action, valid=valid,
                                     yes=False, confirm_label=confirm_label or tr('确认'))
        self.set_focus(None)
        self._refresh_qol()

    def _cancel_qol_confirmation(self):
        self.qol_confirmation = None
        self.qol_searching = False
        self.set_focus(None)
        self.refresh_view()

    def _confirm_qol_yes(self):
        pending = self.qol_confirmation
        if pending is None:
            return
        self.qol_confirmation = None
        self.set_focus(None)
        if pending['valid']():
            self._qol_executing = True
            try:
                result=pending['action']()
                if isinstance(result,ActionResult) and result.message:
                    self.show_toast(result.message,3)
            finally:
                self._qol_executing = False
        else:
            self.show_toast(tr('对象已经改变，本次确认已取消。'), 3)
        # 确认使用/丢弃可能让菜单指向的物品消失：菜单跟着关闭，避免指向空目标。
        target = getattr(self, 'item_menu_target', None)
        if target is not None and not any(
                entry.instance_id == target for entry in self.session.state.inventory):
            self.close_item_menu()
        self.refresh_view()

    def _request_delete_slot(self, slot):
        # 存档页可能正显示测试存档（save-test/）：删档必须打到同一个目录。
        manager = self._saves_manager().for_slot(slot)
        def signature():
            return tuple((p.name, sha256(p.read_bytes()).hexdigest() if p.exists() else None)
                         for p in (manager.primary, manager.backup, manager.next_file))
        identity = signature()
        if not any(value for _, value in identity):
            self.show_toast(tr('这个存档槽是空的。'), 3)
            return
        self._ask_qol(tr('删除存档槽 {slot}？', slot=slot),
            tr('此操作不可恢复。默认取消；选择确认后才删除。') + '\n' + self._delete_slot_preview(manager),
            lambda: self._delete_slot(slot), lambda: signature() == identity,
            confirm_label=tr('确认删除'))

    def _qol_priority_q(self):
        if getattr(self, 'controls_help_open', False):
            self._close_controls_help()
            return True
        if getattr(self, 'qol_searching', False):
            field = self.query_one('#qol-search-input')
            field.insert_text_at_cursor('q')
            return True
        if getattr(self, 'qol_confirmation', None) is not None:
            self._cancel_qol_confirmation()
            return True
        if self.home_mode and self.panel_mode == 'home_history':
            self._handle_history_key('q')
            return True
        return False

    def _qol_guard_action(self, command, args, flags):
        """A final aim/choice confirmation already confirms its consumption."""
        if self._qol_executing:
            return None
        if self.qol_confirmation is not None or self.qol_searching:
            return ActionResult(False, tr('请先确认或取消当前选择。'))
        state = self.session.state
        if command == 'choose_event_option' and args:
            event = state.pending_event()
            if event is not None and 0 <= args[0] < len(event.options):
                option = event.options[args[0]]
                if option.get('library_command') == 'ending' or option.get('epilogue') or option.get('hospital_scene', {}).get('operation') == 'core':
                    identity = (event, state.time, tuple(event.options))
                    self._ask_qol(tr('确认这项选择？'), tr(option.get('label', '')) + '\n' + tr('此项会留下永久结果，确认后执行。'),
                        lambda: self._apply(command, *args, **flags),
                        lambda: state.pending_event() is identity[0] and state.time == identity[1] and tuple(event.options) == identity[2])
                    return ActionResult(False, tr('请确认选择。'))
        return None

    def _inventory_visible_indices(self):
        state = self.session.state
        query = self.inventory_query.strip().casefold()
        indices = [i for i, item in enumerate(state.inventory)
                   if (self.inventory_filter == '全部' or item.category == self.inventory_filter)
                   and (not query or query in (item.name + ' ' + tr(item.name) + ' ' + item.definition_id).casefold())]
        if self.inventory_sort == '名称':
            indices.sort(key=lambda i: (tr(state.inventory[i].name), i))
        elif self.inventory_sort == '类别':
            indices.sort(key=lambda i: (state.inventory[i].category, tr(state.inventory[i].name), i))
        return indices

    def _qol_reselect_inventory(self, *, focus=True, reset_scroll=True):
        # 行囊分类筛选就是面板内部的分层页签：任何筛选入口（页签 / Alt+F）
        # 都同步到同一个值，多入口不会各记一套。
        if hasattr(self, "panel_subpages"):
            self.panel_subpages["inventory"] = self.inventory_filter
        indices = self._inventory_visible_indices()
        if self.panel_selection not in indices:
            self.panel_selection = indices[0] if indices else -1
        if reset_scroll:
            self.panel_scroll = 0
        if focus:
            self._panel_enter_mode = 'inventory'

    def _open_inventory_search(self):
        if self.panel_mode != 'inventory':
            self._toggle_panel('inventory')
        self.qol_searching = True
        self.path.clear()
        self._clear_held()
        field = self.query_one('#qol-search-input')
        field.value = self.inventory_query
        self._refresh_qol()
        self.call_after_refresh(field.focus)

    def _qol_search_changed(self, value):
        if self.qol_searching:
            self.inventory_query = value
            self._qol_reselect_inventory()
            self.refresh_view()

    def _toggle_current_note(self):
        index = self.panel_selection
        if self.panel_mode == 'equipment':
            indices = [i for i, item in enumerate(self.session.state.inventory) if item.slot]
            index = indices[index] if 0 <= index < len(indices) else -1
        key = self._panel_entry_key(index)
        if key:
            self.expanded_key = None if self.expanded_key == key else key
            self.details_expanded = False
            self.refresh_view()

    def _qol_zoom(self, fit=False):
        from .styles import MAP_ZOOM_LEVELS
        if self.home_mode:
            return
        view = self.query_one('#map')
        if fit:
            state = self.session.state
            view.zoom = max((z for z in MAP_ZOOM_LEVELS
                             if state.width * max(1, round(2*z)) <= view.content_size.width
                             and state.height * max(1, round(z)) <= view.content_size.height), default=min(MAP_ZOOM_LEVELS))
        else:
            view.zoom = 1.0
        self.refresh_view()

    def _qol_button(self, button_id):
        if button_id == 'controls-help-close':
            self._close_controls_help()
            return True
        if getattr(self, 'controls_help_open', False):
            return True
        if button_id == 'qol-confirm-no':
            self._cancel_qol_confirmation()
            return True
        if button_id == 'qol-confirm-yes':
            self._confirm_qol_yes()
            return True
        if self.qol_confirmation is not None or self.qol_searching:
            return True
        if not button_id or not button_id.startswith('qol-'):
            return False
        self.path.clear()
        self._clear_held()
        if button_id == 'qol-search':
            self._open_inventory_search()
        elif button_id == 'qol-sort':
            values = ('原序', '名称', '类别')
            self.inventory_sort = values[(values.index(self.inventory_sort)+1) % len(values)]
            self._qol_reselect_inventory()
        elif button_id == 'qol-filter':
            values = ('全部', '携带意象', '摄入物', '易逝物', '交互道具', '惯用物')
            self.set_panel_subpage(values[(values.index(self.inventory_filter)+1) % len(values)], refresh=False)
        elif button_id == 'qol-notes':
            self.details_expanded = not self.details_expanded
            self.expanded_key = None
        elif button_id == 'qol-expand':
            self._toggle_current_note()
        elif button_id in ('qol-zoom-fit', 'qol-zoom-reset'):
            self._qol_zoom(button_id == 'qol-zoom-fit')
        elif button_id == 'qol-offer-confirm':
            self._confirm_lens_offer()
        elif button_id == 'qol-offer-cancel':
            self._clear_lens_offer()
        elif button_id == 'qol-pick-all':
            # Same selection as keyboard A; final collection still requires confirmation.
            self.select_all_pickups()
        self.refresh_view()
        return True

    def _handle_qol_key(self, event):
        key = event.key
        if self.controls_help_open:
            self._mark_key_handled(key)
            if key in ('escape', 'q', 'alt+h'):
                self._close_controls_help()
            else:
                scroll = self.query_one('#controls-help-scroll')
                if key in ('up', 'w'): scroll.scroll_relative(y=-1, animate=False)
                elif key in ('down', 's'): scroll.scroll_relative(y=1, animate=False)
                elif key == 'pageup': scroll.scroll_page_up(animate=False)
                elif key == 'pagedown': scroll.scroll_page_down(animate=False)
                elif key == 'home': scroll.scroll_home(animate=False)
                elif key == 'end': scroll.scroll_end(animate=False)
            event.stop()
            event.prevent_default()
            return True
        if key in ('alt+h', 'alt+z'):
            if key == 'alt+h': self.action_controls_help()
            else: self.action_toggle_footer()
            event.stop()
            event.prevent_default()
            return True
        if self.qol_confirmation is not None:
            self._mark_key_handled(key)
            pending = self.qol_confirmation
            if key in ('escape', 'q', 'n'):
                self._cancel_qol_confirmation()
            elif key == 'y':
                self._confirm_qol_yes()
            elif key in ('left', 'right', 'tab', 'shift+tab'):
                pending['yes'] = not pending['yes']
                self._refresh_qol()
            elif key in ('enter', 'return', 'space'):
                self._confirm_qol_yes() if pending['yes'] else self._cancel_qol_confirmation()
            event.stop()
            return True
        if self.qol_searching:
            self._mark_key_handled(key)
            if key in ('escape', 'enter', 'return'):
                self.qol_searching = False
                self.set_focus(None)
                self.refresh_view()
            event.stop()
            return True
        if self.home_mode or self.board_editor is not None or self.tamper_editor is not None or self._modal_menu_open():
            return False
        # 🔴 用户规定（2026-10-15）：全部修饰键一律用 Alt——终端收不到 Ctrl。
        # Alt+0/9 缩放重置/适合屏幕、Alt+E 展开当前条目、Alt+F 行囊搜索、
        # Alt+R/L 排序/筛选（均为原 Ctrl 键位迁移，勿改回 Ctrl）。
        if key in ('alt+0', 'alt+9'):
            self._qol_zoom(key == 'alt+9')
        elif key == 'alt+e':
            self._toggle_current_note()
        elif key == 'alt+f' and self.panel_mode == 'inventory':
            self._open_inventory_search()
        elif key in ('alt+r', 'alt+l') and self.panel_mode == 'inventory':
            self._qol_button('qol-sort' if key == 'alt+r' else 'qol-filter')
        elif (not self.aiming and self.sentence_aim is None and not self.debug_panel_open
              and self.panel_mode not in ('event_dialog',)):
            mode = panel_for_key(key, getattr(event, 'character', None), getattr(event, 'aliases', ()))
            if mode:
                self._toggle_panel(mode)
            else:
                return False
        else:
            return False
        self.path.clear()
        self._clear_held()
        self._mark_key_handled(key)
        event.stop()
        return True

    def _move_panel_selection(self, delta):
        if self.panel_mode == 'inventory':
            indices = self._inventory_visible_indices()
            self.panel_selection = indices[((indices.index(self.panel_selection) if self.panel_selection in indices else -1)+delta) % len(indices)] if indices else -1
            self._panel_enter_mode = 'inventory'
            self._follow_list_selection()
            self.refresh_view()
        elif self.panel_mode == 'tasks':
            count = self._panel_item_count()
            self.panel_selection = (self.panel_selection+delta) % count if count else 0
            self._follow_list_selection()
            self.refresh_view()
        else:
            super()._move_panel_selection(delta)

    def _panel_item_count(self):
        if self.panel_mode == 'tasks':
            from .task_journal import journal_actions
            return len(journal_actions(self.session.state))
        return super()._panel_item_count()

    def _panel_entry_key(self, index):
        if self.panel_mode == 'tasks':
            from .task_journal import journal_actions
            actions = journal_actions(self.session.state)
            return actions[index] if 0 <= index < len(actions) else None
        return super()._panel_entry_key(index)

    def _activate_panel_selection(self, *args, **kwargs):
        if self.panel_mode == 'inventory' and self.panel_selection not in self._inventory_visible_indices():
            self.show_toast(tr('当前筛选没有可使用的物品。'), 3)
            return
        if self.panel_mode == 'tasks':
            from .task_journal import journal_tasks, journal_actions
            actions=journal_actions(self.session.state)
            if 0<=self.panel_selection<len(actions) and actions[self.panel_selection].startswith('course:'):
                self._apply('tutorial_control',actions[self.panel_selection].partition(':')[2])
                return
            entries = journal_tasks(self.session.state)
            if not 0 <= self.panel_selection < len(entries):
                return
            entry = entries[self.panel_selection]
            uid = entry['task_uid']
            state = self.session.state
            record = state.world_ledger.tasks.get(uid)
            self._ask_qol(tr('放弃委托？'), entry['name'] + '\n' + tr('不领取报酬，恢复一个委托名额。') +
                ('\n' + tr('这项委托已经满足交付条件。') if entry['resolved'] else ''),
                lambda: self._apply('abandon_task', uid),
                lambda: state.world_ledger.tasks.get(uid) is record and record.status in ('进行中','待交付'))
            return
        return super()._activate_panel_selection(*args, **kwargs)

    # 确认层控件在 compose 里一次装好，拆卸时子树先于 App.on_unmount（停表处）
    # 卸载，帧定时器仍可能在窗口里回调进来。这里用不抛异常的 query 做生命周期
    # 判断，缺控件就是「确认层已经不在了」，直接返回；不用 except NoMatches
    # 吞异常——那会把真正的拼写错误一起吞掉。
    _QOL_CONFIRM_SELECTORS = ('#qol-confirm-dialog', '#qol-search-input', '#qol-confirm-text',
                              '#qol-confirm-no', '#qol-confirm-yes')

    def _qol_confirm_widgets(self):
        cached = getattr(self,'_qol_confirm_cache',None)
        if (cached is not None and cached[0] is self.screen
                and all(widget.is_attached for widget in cached[1].values())):
            return cached[1]
        found = {}
        for selector in self._QOL_CONFIRM_SELECTORS:
            nodes = self.query(selector)
            if not nodes:
                return None
            found[selector] = nodes.first()
        self._qol_confirm_cache = (self.screen,found)
        return found

    def _refresh_qol(self):
        if not self.is_mounted:
            return
        pending = self.qol_confirmation
        confirm = self._qol_confirm_widgets()
        if confirm is None:
            return
        dialog = confirm['#qol-confirm-dialog']
        dialog.display = bool(pending or self.qol_searching)
        field = confirm['#qol-search-input']
        field.display = self.qol_searching
        if pending:
            confirm['#qol-confirm-text'].update(Text(pending['title'] + '\n' + pending['detail']))
            confirm['#qol-confirm-no'].label = tr('取消') + (' ◀' if not pending['yes'] else '')
            confirm['#qol-confirm-yes'].label = pending.get('confirm_label', tr('确认')) + (' ◀' if pending['yes'] else '')
        elif self.qol_searching:
            confirm['#qol-confirm-text'].update(Text(tr('搜索行囊：名称或物品标识；Enter/Esc 返回列表')))
        confirm['#qol-confirm-yes'].display = not self.qol_searching
        confirm['#qol-confirm-no'].display = not self.qol_searching
        if dialog.display:
            body = Text(pending['title'] + '\n' + pending['detail']) if pending else Text(
                tr('搜索行囊：名称或物品标识；Enter/Esc 返回列表'))
            stage = self._overlay_stage()
            width = max(12, min(88, stage.width - 4))
            lines = len(body.wrap(self.console, max(1, width - 6)))
            height = min(max(5, stage.height - 4),
                         max(9, lines + 6 + (3 if self.qol_searching else 0)))
            x = stage.x + max(0, (stage.width - width) // 2)
            y = stage.y + max(0, (stage.height - height) // 2)
            dialog.styles.width = width
            dialog.styles.height = height
            dialog.styles.offset = (x, y)
            key = (x, y, width, height, stage.x, stage.y, stage.width, stage.height)
            if getattr(self, '_qol_fit', None) != key:
                # 窗口尺寸或可用区变了：先把上一次隐藏的背景恢复，再按新位置重算。
                self._restore_occluded(getattr(self, '_qol_background', []))
                self._qol_fit = key
                self._qol_background = self._occlude_under(Region(x, y, width, height), dialog)
        elif getattr(self, '_qol_background', None):
            self._restore_occluded(self._qol_background)
            self._qol_background = []
            self._qol_fit = None
        # 🔴 用户规定（2026-10-15）：底部只留 1 行——qol-context 注释行与两条
        # qol 工具栏已从 #side-pane 整体移除（多行注释直接压在面板内容上，会遮挡
        # 游戏画面）。旧的按钮 display 切换与 context 文案逻辑一并退役；
        # 搜索/排序/筛选/展开/缩放等功能仍由 Alt 快捷键经 _qol_button 路由承担。

