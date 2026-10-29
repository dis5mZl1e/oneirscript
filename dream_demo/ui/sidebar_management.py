"""Sidebar management, stable detail links and local presentation preferences.

All actions delegate to existing controllers or validated core transactions.
Browsing and preferences never consume world time or alter the world save.
"""
from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console
from rich.text import Text
from ..i18n import tr, get_language
from ..core.content import ABILITY_DEFINITIONS, ITEM_DEFINITIONS, INSIGHT_DEFINITIONS, MEMORY_FRAGMENT_EFFECTS
from ..data.semantic_icons import icon_label
from .panel_fields import FIELD_COLORS as C
from .panels import kv_grid, paper_pad, zone_strip
from .paper_zones import ZONE_CAST_LIST, ZONE_CAST_PREVIEW
from .sidebar_models import item_by_id, item_facts, comparison, task_items
from .styles import RIGHT_PANEL_MODES

_CONSOLE = Console(legacy_windows=False)
_DETAIL = 'sidebar_detail'


class SidebarManagementMixin:
    @property
    def sidebar_workspace(self):
        if self.panel_mode == _DETAIL:
            return getattr(self, '_sidebar_detail_ref', {}).get('workspace', 'inventory')
        return super().sidebar_workspace

    def _sidebar_navigation_allowed(self):
        return super()._sidebar_navigation_allowed()

    def sidebar_preferences(self):
        path = self.session.manager.directory / 'sidebar-preferences.json'
        if getattr(self, '_sidebar_preferences_path', None) != path:
            try:
                raw = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                raw = {}
            if not isinstance(raw, dict):
                raw = {}
            favorites = raw.get('favorites', [])
            collapsed = raw.get('collapsed', [])
            self._sidebar_preferences = {
                'favorites': list(dict.fromkeys(a for a in favorites if isinstance(a, str) and a in ABILITY_DEFINITIONS)) if isinstance(favorites, list) else [],
                'collapsed': [key for key in collapsed if key in ('world', 'build_overview', 'self_overview')] if isinstance(collapsed, list) else [],
            }
            self._sidebar_preferences_path = path
        return self._sidebar_preferences

    def _save_sidebar_preferences(self):
        path = self._sidebar_preferences_path
        temporary = path.with_suffix('.next.json')
        try:
            temporary.write_text(json.dumps(self.sidebar_preferences(), ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(path)
        except OSError:
            self.show_toast(tr('显示偏好仅在本次会话生效。'), 3)

    def _sidebar_route_key(self):
        if self.panel_mode == _DETAIL:
            ref = getattr(self, '_sidebar_detail_ref', {})
            return _DETAIL, (ref.get('kind', ''), ref.get('id', ''))
        return super()._sidebar_route_key()

    def _remember_sidebar_position(self):
        # Detail identity belongs to the short return stack, never to a main
        # workspace's remembered business route.
        group = self.sidebar_workspace
        previous = self.__dict__.get('_sidebar_last_routes', {}).get(group)
        super()._remember_sidebar_position()
        if self.panel_mode == _DETAIL:
            routes = self.__dict__.setdefault('_sidebar_last_routes', {})
            if previous is None: routes.pop(group, None)
            else: routes[group] = previous

    def _sidebar_snapshot(self):
        self._remember_sidebar_position()
        return (self.panel_mode, self._panel_subpage_id(), dict(getattr(self, '_sidebar_detail_ref', {})),
                self.cursor_zone, getattr(self, '_panel_enter_mode', None))

    def open_sidebar_detail(self, kind, identifier, workspace=None):
        if not self._sidebar_navigation_allowed():
            return False
        stack = self.__dict__.setdefault('_sidebar_back_stack', [])
        stack.append(self._sidebar_snapshot())
        del stack[:-8]
        group = workspace or self.sidebar_workspace or 'inventory'
        self._sidebar_detail_ref = dict(kind=kind, id=identifier, workspace=group)
        self.panel_mode = _DETAIL
        self.panel_selection = self.panel_scroll = 0
        self._panel_mode_seen = _DETAIL
        self._panel_enter_mode = _DETAIL
        self._update_locked_panel_page()
        self.path.clear(); self.observe_walk_path.clear(); self._clear_held()
        self.refresh_view()
        return True

    def open_sidebar_item(self, identity):
        if item_by_id(self.session.state, identity) is None:
            self.show_toast(tr('这件物品已经不在行囊中。'), 3)
            return False
        return self.open_sidebar_detail('item', identity, 'inventory')

    def _sidebar_back(self):
        stack = self.__dict__.get('_sidebar_back_stack', [])
        if not stack:
            return False
        self._remember_sidebar_position()
        mode, page, ref, zone, enter = stack.pop()
        self.panel_mode = mode
        self._sidebar_detail_ref = ref
        if page:
            self.panel_subpages[mode] = page
        self._restore_sidebar_position()
        self.cursor_zone, self._panel_enter_mode = zone, enter
        self._update_locked_panel_page()
        self.refresh_view()
        return True

    def _ui_escape_chain(self):
        if (self.panel_mode == _DETAIL and not self._modal_menu_open() and not self.aiming
                and self.sentence_aim is None and self._active_left_overlay() is None):
            return self._sidebar_back() or super()._ui_escape_chain()
        return super()._ui_escape_chain()

    def open_sidebar_workspace(self, workspace, *, manual: bool = True):
        if not self._sidebar_navigation_allowed():
            return False
        # 2026-10-24 六工作区：行动主按钮回归 WORKSPACES 默认页（行动·构想），
        # 不再强制跳事件记录——记录归日志工作区承接。
        if self.panel_mode == _DETAIL:
            group = self.sidebar_workspace
            from .sidebar_workspaces import MODE_WORKSPACE
            origin = next((snapshot for snapshot in reversed(getattr(self, '_sidebar_back_stack', []))
                           if MODE_WORKSPACE.get(snapshot[0]) == group), None)
            self._sidebar_back_stack = []
            route = {'actions': 'actions', 'inventory': 'inventory', 'equipment': 'equipment',
                     'portents': 'portents', 'environment': 'nearby', 'tasks': 'journal_log'}[group]
            self.panel_mode = origin[0] if origin else route
            if origin and origin[1]:
                self.panel_subpages[self.panel_mode] = origin[1]
            self._restore_sidebar_position()
            if group == workspace:
                self.refresh_view()
                return True
        self._sidebar_back_stack = []
        return super().open_sidebar_workspace(workspace, manual=manual)

    def open_sidebar_route(self, key, *, manual: bool = True):
        if self._sidebar_navigation_allowed():
            self._sidebar_back_stack = []
        return super().open_sidebar_route(key, manual=manual)

    def _sync_sidebar_owner(self):
        state = self.session.state
        context = (id(state), state.depth, state.realm_id, state.realm_depth,
                   state.run_over, self.home_mode)
        previous = getattr(self, '_management_owner', context)
        if previous != context:
            self._sidebar_back_stack = []
            self._sidebar_live_identity = None
            if self.panel_mode == _DETAIL:
                self.panel_mode = self._default_panel_mode()
            self._sidebar_detail_ref = {}
            self._management_board_return = None
            self._locked_aim_sidebar = None
        self._management_owner = context
        return super()._sync_sidebar_owner()

    def _sidebar_before_refresh(self):
        self._sync_sidebar_owner()
        parked = getattr(self, '_locked_aim_sidebar', None)
        if parked:
            context, snapshot = parked
            state = self.session.state
            if (self.panel_locked and context == (id(state), state.layer_key())
                    and not self.home_mode and not state.run_over and self.sidebar_workspace):
                mode, page, ref, zone, enter = snapshot
                self.panel_mode = mode
                self._sidebar_detail_ref = ref
                if page: self.panel_subpages[mode] = page
                self._restore_sidebar_position()
                self.cursor_zone, self._panel_enter_mode = zone, enter
            if not self.aiming and self.sentence_aim is None:
                self._locked_aim_sidebar = None
        # 2026-10-28：24 行也是常见终端下限；此前 <24 才启用短窗滚动，
        # 80x24 装备页会被句子行挤到只剩 2-4 行正文（低于方案要求的主体 6 行）。
        self.screen.set_class(self.size.height <= 24, 'sidebar-short')
        old = getattr(self, '_sidebar_live_identity', None)
        token = (self.panel_mode, self._panel_subpage_id())
        if old and old[:2] == token and old[2] == self.panel_selection:
            candidates = self._sidebar_inventory_choices()
            match = next((ordinal for ordinal, identity in candidates if identity == old[3]), None)
            if match is not None:
                self.panel_selection = match
            elif candidates:
                self.panel_selection = candidates[min(max(0, self.panel_selection), len(candidates)-1)][0]

    def _apply(self, command, *args, **flags):
        state = self.session.state
        layer = state.layer_key()
        locked = self.panel_locked
        snapshot = self._sidebar_snapshot() if locked and self.sidebar_workspace else None
        result = super()._apply(command, *args, **flags)
        # Modal conversations, aiming and layer transitions keep their original
        # controllers. Only a completed world action changes the ordinary sidebar.
        if (result.changed and state is self.session.state
                and state.layer_key() == layer and not state.run_over
                and not self.home_mode
                and (self.sidebar_workspace or self.panel_mode in RIGHT_PANEL_MODES
                     or self.panel_mode == "world")
                and not self._inspection_active()
                # 左侧容器浮层开着时（盛装/倒出）右栏必须留在行囊页：这两个是
                # 「面板上下文动作」，不是世界行动；回跳默认页会把玩家刚打开的
                # 行囊顶掉（2026-10-28 平台复测：盛装后 panel_mode 由 inventory
                # 变 world，Esc 收起浮层也回不去）。
                and getattr(self, "container_index", None) is None
                and self.board_editor is None and self._active_tamper_editor() is None):
            if locked and snapshot is not None:
                mode, page, ref, zone, enter = snapshot
                self.panel_mode = mode
                self._sidebar_detail_ref = ref
                if page: self.panel_subpages[mode] = page
                self._restore_sidebar_position()
                self.cursor_zone, self._panel_enter_mode = zone, enter
                self._locked_panel_page = (mode, page, dict(ref))
            # 未锁定：成功世界行动回跳到「默认页」。2026-10-26 起默认页由
            # _default_panel_mode() 决定——左侧事件记录开启时回到行囊，否则
            # 保持原来的事件记录（world）。锁定态不回跳（玩家要求右栏固定）。
            elif self.panel_mode != self._default_panel_mode():
                self._sidebar_transition(self._default_panel_mode(),
                                         refresh=False, manual=False)
            if locked:
                self.refresh_view()
        return result
    def _sidebar_after_refresh(self):
        token = (self.panel_mode, self._panel_subpage_id())
        candidates = dict(self._sidebar_inventory_choices())
        self._sidebar_live_identity = (*token, self.panel_selection, candidates.get(self.panel_selection)) if candidates else None

    def _remember_locked_aim_sidebar(self):
        if self.panel_locked and self.sidebar_workspace and not getattr(self, '_locked_aim_sidebar', None):
            state = self.session.state
            self._locked_aim_sidebar = ((id(state), state.layer_key()), self._sidebar_snapshot())

    def _capture_aim_source(self, keep_cursor=False):
        self._remember_locked_aim_sidebar()
        return super()._capture_aim_source(keep_cursor=keep_cursor)

    def _begin_sentence_aim(self, key):
        self._remember_locked_aim_sidebar()
        return super()._begin_sentence_aim(key)

    def _begin_targeted_equipment_aim(self, option, source_index=None, preserve_aim=False):
        self._remember_locked_aim_sidebar()
        return super()._begin_targeted_equipment_aim(option, source_index, preserve_aim)

    def _sidebar_inventory_choices(self):
        state = self.session.state
        if self.panel_mode == 'inventory':
            return [(i, state.inventory[i].instance_id) for i in self._inventory_visible_indices()]
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'board':
            return [(n, item.instance_id) for n, item in enumerate(item for item in state.inventory if item.slot)]
        return []

    def _sidebar_ability_indices(self):
        state = self.session.state
        query = getattr(self, '_sidebar_ability_query', '').strip().casefold()
        pins = self.sidebar_preferences()['favorites']
        ids = [key for key in state.abilities if key in ABILITY_DEFINITIONS]
        visible = [n for n, key in enumerate(ids)
                   if (not getattr(self, '_sidebar_only_favorites', False) or key in pins)
                   and (not query or query in (key+' '+tr(ABILITY_DEFINITIONS[key]['name'])+' '+tr(ABILITY_DEFINITIONS[key]['description'])).casefold())]
        return sorted(visible, key=lambda n: ids[n] not in pins)

    def _construct_actions_lines(self, state):
        """构想页左右分块（2026-10-24 玩家定稿）：左列表 / 右选中一发的使用信息。

        - 左列 = 目标操作 + 构想列表 + 身份能力 + 装备语句（ZONE_CAST_LIST 纸色）；
        - 右列 = 选中构想的使用预览（形态/射程/目标/流程/地形预览，ZONE_CAST_PREVIEW）；
        - 两块底色用 two_zone_row 分到左右两侧，中间一条细竖线，与「环境」页
          左右分区同构。
        - 简介默认折叠：\ 键全局展开，Shift+左键单条展开；
          普通左键走正常激活/施放路径。
        """
        from .panels import two_zone_row

        ids = [key for key in state.abilities if key in ABILITY_DEFINITIONS]
        context_actions = list(self._actions_for(self.context_menu_target)) if self.context_menu_target else []
        context = len(context_actions)
        visible = self._sidebar_ability_indices()
        identity = state.identity_abilities()
        sentence_options = state.equipment.active_sentence_options()
        width = max(8, self.query_one('#panel').content_size.width)
        left_w = max(14, (width - 1) // 2)
        right_w = width - 1 - left_w
        pins = self.sidebar_preferences()['favorites']
        preview = self._terrain_preview_for(state)
        compact = self._terse_active()

        left_lines: list[Text] = []
        left_rows: list[int] = []
        right_lines: list[Text] = []

        def add_left(text, row=-1):
            for part in text.wrap(_CONSOLE, left_w, overflow='fold'):
                left_lines.append(part)
                left_rows.append(row)

        def add_right(text):
            for part in text.wrap(_CONSOLE, right_w, overflow='fold'):
                right_lines.append(part)

        # ---- 左列：可选项列表 ----
        if self.context_menu_target:
            add_left(Text(('—— TGT ——' if compact else tr('—— 目标操作 ——')) + f' {self.context_menu_target}',
                          style='bold ' + C['identity']))
            for offset, action in enumerate(context_actions):
                selected = offset == self.panel_selection
                add_left(Text(('▶ ' if selected else '  ') + tr(action),
                              style=C['identity'] + (' bold underline' if selected else '')), offset)

        add_left(Text('—— ABL ——' if compact else tr('—— 主动构想 ——'), style='bold ' + C['word']))
        add_left(Text(f'RES: {len(visible)}' if compact else tr('结果：{n}', n=len(visible)), style=C['count']))
        for ordinal in visible:
            key = ids[ordinal]
            definition = ABILITY_DEFINITIONS[key]
            row = context + ordinal
            focused = self.panel_selection == row
            line = Text(('▶ ' if focused else '  ') + ('★ ' if key in pins else ''))
            line.append_text(icon_label('ability.' + key, tr(definition['name']),
                                       C['word'] + (' bold underline' if focused else '')))
            line.append('  ' + str(state._scaled_ability_cost(int(definition['cost']))) + ' ' + ('IMA' if compact else tr('想象力')),
                        style=C['cost'])
            cooldown = state.ability_cooldowns.get(key, 0)
            if cooldown:
                line.append(f' · CD {cooldown} T' if compact else ' · ' + tr('冷却 {n} 回合', n=cooldown), style=C['cooldown'])
            add_left(line, row)
            # 默认折叠；只有 \ 全局展开或单条点开时才显示完整简介。
            if self._entry_expanded('ability:' + key):
                add_left(Text('  ' + tr(definition['description']), style=C['muted']), row)
        if not visible:
            add_left(Text(tr('没有匹配的构想；可清除搜索或切换全部。'), style=C['muted']))

        if identity:
            add_left(Text('—— ID ——' if compact else tr('—— 身份能力 ——'), style='bold ' + C['identity']))
        for offset, ability in enumerate(identity):
            index = context + len(ids) + offset
            selected = index == self.panel_selection
            name, cost = ('借雾', 5) if ability == 'borrow_fog' else ('退稿', 4)
            cooldown = max(0, state.identity_state.get('cooldowns', {}).get(ability, 0) - state.time)
            line = Text(('▶ ' if selected else '  ') + tr(name),
                        style=C['identity'] + (' bold underline' if selected else ''))
            line.append('  ' + str(cost) + ' ' + ('IMA' if compact else tr('想象力')), style=C['cost'])
            if cooldown:
                line.append(f' · CD {cooldown} T' if compact else ' · ' + tr('冷却 {n} 回合', n=cooldown), style=C['cooldown'])
            add_left(line, index)

        if sentence_options:
            add_left(Text('—— GEAR ——' if compact else tr('—— 装备语句 ——'), style='bold ' + C['identity']))
        for offset, option in enumerate(sentence_options):
            index = context + len(ids) + len(identity) + offset
            selected = index == self.panel_selection
            status = tr('想象力 {cost} · 射程 {range} · 冷却 {cooldown}',
                        cost=option.cost, range=option.range, cooldown=round(option.cooldown, 1))
            if compact:
                status = f'IMA {option.cost} · RNG {option.range} · CD {round(option.cooldown, 1)}'
            if option.consumes_source:
                status = (f'USE 1 · T 1 · RNG {option.range}' if compact else
                          tr('消耗 1 件工具 · 耗时 1 回合 · 距离 {range}', range=option.range))
            add_left(Text(('▶ ' if selected else '  ') + option.text,
                          style=C['identity'] + (' bold underline' if selected else '')), index)
            add_left(Text('    ' + status, style=C['muted']), index)

        # ---- 右列：选中一发的使用预览 ----
        add_right(Text('—— PREVIEW ——' if compact else tr('—— 使用预览 ——'), style='bold ' + C['word']))
        focused_ordinals = [o for o in visible if context + o == self.panel_selection]
        chosen = ids[focused_ordinals[0]] if focused_ordinals else (ids[visible[0]] if visible else None)
        if chosen is None:
            add_right(Text(tr('习得构想后，这里显示选中一发的形态与施放流程。'), style=C['muted']))
        else:
            definition = ABILITY_DEFINITIONS[chosen]
            cooldown = state.ability_cooldowns.get(chosen, 0)
            head = Text(tr(definition['name']), style='bold ' + C['word'])
            head.append('  ' + str(state._scaled_ability_cost(int(definition['cost']))) + ' ' + ('IMA' if compact else tr('想象力')),
                        style=C['cost'])
            if cooldown:
                head.append(f' · CD {cooldown} T' if compact else ' · ' + tr('冷却 {n} 回合', n=cooldown), style=C['cooldown'])
            add_right(head)
            combat = definition.get('combat') or {}
            if combat:
                forms = {'melee': tr('近战'), 'launch': tr('弹道'), 'throw': tr('投掷'),
                         'area': tr('范围'), 'blink': tr('位移')}
                detail = Text(('FORM' if compact else tr('形态')) + ' ' + forms.get(str(combat.get('form')), str(combat.get('form'))),
                              style=C['grammar'])
                if combat.get('range') is not None:
                    detail.append(' · ' + ('RNG' if compact else tr('射程')) + ' ' + str(combat['range']), style=C['range'])
                if combat.get('targeting'):
                    detail.append(' · ' + ('TGT' if compact else tr('目标')) + ' ' + tr(str(combat['targeting'])), style=C['category'])
                if combat.get('sound'):
                    detail.append(' · ' + ('NOI' if compact else tr('声响')) + ' ' + str(combat['sound']), style=C['noise'])
                add_right(detail)
            # 施放流程按真实分支写：战斗/选点类先零消耗瞄准、确认才支付。
            from ..core.combat_constructs import is_combat
            from ..core.ability_targeting import is_targeted
            flow = (tr('Enter/左键 进入零消耗瞄准，确认时才支付。')
                    if is_combat(chosen) or is_targeted(chosen) else tr('Enter/左键 立即施放。'))
            add_right(Text(flow, style=C['windup']))
            # 完整描述只在展开态显示（\ 或点击单条）。
            if self._entry_expanded('ability:' + chosen):
                add_right(Text(tr(definition['description']), style=C['muted']))
            if focused_ordinals and preview is not None:
                for index, text in enumerate(preview.lines):
                    add_right(Text(text, style=('bold ' + C['word']) if index == 0 else C['muted']))

        # ---- 左右拼行：左块登记行命中，右块是只读信息 ----
        lines: list[Text] = []
        rows: list[int] = []
        for index in range(max(len(left_lines), len(right_lines), self.query_one('#panel').content_size.height - 1)):
            left = left_lines[index] if index < len(left_lines) else Text()
            right = right_lines[index] if index < len(right_lines) else Text()
            lines.append(two_zone_row(left, right, ZONE_CAST_LIST, ZONE_CAST_PREVIEW, left_w, right_w))
            rows.append(left_rows[index] if index < len(left_rows) else -1)

        self._sidebar_ability_visible_rows = list(dict.fromkeys(row for row in rows if row >= 0))
        # Filtering may hide a legitimate ability; an invalid/stale ordinal
        # must remain invalid so Enter cannot silently cast the first ability.
        if (self._sidebar_ability_visible_rows and context <= self.panel_selection < context + len(ids)
                and self.panel_selection not in self._sidebar_ability_visible_rows):
            self.panel_selection = self._sidebar_ability_visible_rows[0]
        # 键位行由 _panel_footer 钉底（不随滚动漂走），这里不再重复追加。
        return lines, rows

    def _portent_entries(self, state):
        entries = super()._portent_entries(state)
        if self.panel_mode != 'portents': return entries
        kind = getattr(self, '_sidebar_portent_filter', '全部')
        if kind == '全部': return entries
        if kind == '其他': return [e for e in entries if e['kind'] not in ('正面', '负面')]
        return [e for e in entries if e['kind'] == kind]

    def _memory_page_lines(self, state):
        from ..core.content import MEMORY_LIMIT
        header = Text(tr('记忆槽：')+f'{len(state.memory_fragments)}/{MEMORY_LIMIT+state._memory_slot_bonus()}', style=C['memory'])
        lines, rows = [], []
        width = max(8, self.query_one('#panel').content_size.width)
        for index, key in enumerate(state.memory_fragments):
            text = self._memory_fragment_line(key, max(8, width-2))
            text = Text('▶ ' if index == self.panel_selection else '  ')+text
            for line in text.wrap(_CONSOLE, width, overflow='fold'):
                lines.append(line); rows.append(index)
        if not lines:
            lines.append(Text(tr('（空）'), style=C['muted'])); rows.append(-1)
        return lines, rows, header

    def _panel_item_count(self):
        if self.panel_mode == _DETAIL: return len(self._management_cached_actions())
        if self.panel_mode == 'portents': return len(self._portent_entries(self.session.state))
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'memory': return len(self.session.state.memory_fragments)
        return super()._panel_item_count()

    def _panel_entry_key(self, index):
        if self.panel_mode == _DETAIL:
            actions = self._management_cached_actions()
            return actions[index]['key'] if 0 <= index < len(actions) else None
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'memory':
            values = self.session.state.memory_fragments
            return 'memory:'+values[index] if 0 <= index < len(values) else None
        return super()._panel_entry_key(index)

    def _sidebar_selection_candidates(self):
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'memory':
            return list(range(len(self.session.state.memory_fragments)))
        return super()._sidebar_selection_candidates()

    def _activate_panel_selection(self, key_hint=None):
        previous = getattr(self, '_sidebar_action_active', False)
        self._sidebar_action_active = True
        try:
            return self._activate_sidebar_selection(key_hint)
        finally:
            self._sidebar_action_active = previous

    def _activate_sidebar_selection(self, key_hint=None):
        if self.panel_mode == _DETAIL:
            key = key_hint or self._panel_entry_key(self.panel_selection)
            action = next((a for a in self._management_contents()[1] if a['key'] == key), None)
            if action and self._sidebar_navigation_allowed(): self._management_activate(action)
            return
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'memory':
            key = key_hint or self._panel_entry_key(self.panel_selection)
            if key and key.startswith('memory:') and key[7:] in self.session.state.memory_fragments:
                self.open_sidebar_detail('memory', key[7:], 'equipment')
            return
        return super()._activate_panel_selection(key_hint=key_hint)

    def _move_panel_selection(self, delta):
        if self.panel_mode == _DETAIL or (self.panel_mode == 'equipment' and self._panel_subpage_id() == 'memory'):
            count = self._panel_item_count()
            if count: self.panel_selection = (self.panel_selection+delta) % count
            self._panel_enter_mode = self.panel_mode
            self._management_follow()
            self._refresh_navigation_selection(); return
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'constructs':
            self._construct_actions_lines(self.session.state)
            rows = self._sidebar_ability_visible_rows
            if rows:
                pos = rows.index(self.panel_selection) if self.panel_selection in rows else -1
                self.panel_selection = rows[(pos+delta) % len(rows)]
            self._panel_enter_mode = self.panel_mode
            self._follow_actions_selection(); self._refresh_navigation_selection(); return
        return super()._move_panel_selection(delta)

    def _management_follow(self):
        rows = getattr(self, '_management_full_rows', []) if self.panel_mode == _DETAIL else []
        if self.panel_mode != _DETAIL:
            rows = self._memory_page_lines(self.session.state)[1]
        matches = [i for i, value in enumerate(rows) if value == self.panel_selection]
        if matches:
            height = max(1, self.query_one('#panel').content_size.height)
            self.panel_scroll = max(0, min(self.panel_scroll, matches[0]))
            self.panel_scroll = max(self.panel_scroll, matches[-1]-height+1)

    def _scroll(self, amount):
        if self.panel_mode != _DETAIL: return super()._scroll(amount)
        height = max(1, self.query_one('#panel').content_size.height)
        limit = max(0, len(getattr(self, '_management_full_rows', []))-height)
        self.panel_scroll = max(0, min(limit, self.panel_scroll-amount))
        self._refresh_navigation_selection()

    def _panel_text_build(self, state):
        if self.panel_mode != _DETAIL: return super()._panel_text_build(state)
        body, actions = self._management_contents()
        self._management_action_snapshot = (dict(self._sidebar_detail_ref), actions)
        width = max(8, self.query_one('#panel').content_size.width)
        lines, rows = [], []
        for text, row in body:
            if row >= 0:
                text = Text(('▶ ' if row == self.panel_selection else '  '), style=C['condition'])+text
                if row == self.panel_selection: text.stylize('bold underline')
            for part in text.wrap(_CONSOLE, width, overflow='fold'):
                lines.append(part); rows.append(row)
        height = max(1, self.query_one('#panel').content_size.height)
        self.panel_scroll = min(max(0, self.panel_scroll), max(0, len(lines)-height))
        self._management_full_rows = rows
        self._panel_rows = rows[self.panel_scroll:self.panel_scroll+height]
        return Text('\n').join(lines[self.panel_scroll:self.panel_scroll+height])

    def _management_cached_actions(self):
        snapshot = getattr(self,'_management_action_snapshot',None)
        if snapshot and snapshot[0] == self._sidebar_detail_ref:
            return snapshot[1]
        return self._management_contents()[1]

    def _management_contents(self):
        state = self.session.state
        ref = getattr(self, '_sidebar_detail_ref', {})
        kind, identity = ref.get('kind'), ref.get('id')
        body, actions = [], []
        try:
            width = max(8, self.query_one('#panel').content_size.width)
        except Exception:
            width = 40
        def add(text, color='text'):
            from .panels import zone_strip
            line = zone_strip(str(text), width, color=C[color]) if color == 'heading' else Text(str(text), style=C[color])
            body.append((line, -1))
        def add_grid(pairs):
            # 键值对两列化（2026-10-24 D）：≥44 列两列、中缝细竖线；超宽折行不截断。
            for grid_row in kv_grid(pairs, width):
                body.append((grid_row, -1))
        def action(label, command, *args):
            key = repr((command, *args))
            actions.append(dict(key=key, command=command, args=args))
            body.append((Text(label, style=C['condition']), len(actions)-1))
        action(tr('返回原条目'), 'back')
        add(tr('详情与操作'), 'heading')
        if kind == 'item':
            item = item_by_id(state, identity)
            facts = item_facts(state, identity)
            if facts is None:
                add(tr('这件物品已经不在行囊中。'), 'risk'); return body, actions
            add(facts['name']+' ×'+str(facts['quantity']), 'word')
            add(facts['category'], 'category'); add(facts['description'])
            # 键值对网格（强度/穿透/推力/爆炸半径/弹匣/内含物）；说明段落仍整行。
            pairs = [(tr(label), str(facts[key]), C['count'])
                     for label, key in (('强度','power'), ('穿透','penetration'), ('推力','push'), ('爆炸半径','radius'))
                     if facts[key]]
            if facts['magazine'] is not None:
                pairs.append((tr('弹匣'), f"{facts['magazine']}/{facts['capacity']}", C['count']))
            pairs.extend((tr(name), str(amount), C['volume']) for name, amount in facts['contents'].items())
            add_grid(pairs)
            compared = comparison(state, identity)
            if item.slot:
                add(tr('对比'), 'heading'); add(compared['note'], 'muted')
                for peer in compared['peers']:
                    other = item_facts(state, peer)
                    if other:
                        add(tr('当前配置')+' · '+other['name'], 'word'); add(other['description'], 'muted')
                        action(tr('查看')+' · '+other['name'], 'link', 'item', peer, 'inventory')
            if item.category == '记忆碎片':
                from ..core.memory_management import equip_refusal
                blocked = equip_refusal(state, identity)
                if blocked is not None: add(blocked.message, 'risk')
                else: action(tr('装入记忆槽 · 1 回合'), 'equip_memory', identity)
            else:
                for key, label, command in self._item_menu_actions(item):
                    action(tr(label), 'item', identity, command)
            action(tr('完整操作'), 'legacy_item', identity)
        elif kind == 'memory':
            definition = ITEM_DEFINITIONS.get(identity)
            if not definition or identity not in state.memory_fragments:
                add(tr('这条记忆已经不在槽中。'), 'risk'); return body, actions
            add(tr(definition['name']), 'memory')
            effect = MEMORY_FRAGMENT_EFFECTS.get(definition.get('memory_effect'), {})
            add(tr(effect.get('detail') or effect.get('short') or definition.get('description', '')))
            from ..core.memory_management import unequip_refusal
            blocked = unequip_refusal(state, identity)
            if blocked is not None: add(blocked.message, 'risk')
            else: action(tr('取下至行囊 · 1 回合'), 'unequip_memory', identity)
            action(tr('查看全部数值来源'), 'sources')
        elif kind == 'insight':
            if identity not in state.insights:
                add(tr('这项洞察已经失效。'), 'risk'); return body, actions
            add(tr(identity), 'insight'); add(tr(INSIGHT_DEFINITIONS.get(identity, '')))
            action(tr('查看全部数值来源'), 'sources')
        elif kind == 'portent':
            entry = next((entry for entry in self._portent_entries(state) if entry['id'] == identity), None)
            if entry is None:
                add(tr('这个征兆已经结束。'), 'muted'); return body, actions
            add(tr(entry['name']), 'portent'); add(tr(entry['effect']))
            add(tr('剩余 {n} 回合', n=entry['remaining']), 'duration')
        elif kind in ('stat', 'sources'):
            from ..core.self_audit import self_audit
            data = self_audit(state)
            if kind == 'stat':
                found = next((r for category, rows in data['sections'].items() for r in rows
                              if 'stat:'+category+':'+r['key'] == identity), None)
                if found is None:
                    add(tr('这项数值已经失效。'), 'risk'); return body, actions
                add(found['label']+' '+found['value'], 'word')
                if found['base'] is not None: add(tr('基础值：')+str(found['base']), 'count')
                for source in found['sources']: add(tr('来源：')+str(source), 'grammar')
                for note in found['notes']: add(str(note), 'muted')
                for source in found.get('source_refs', ()):
                    self._management_source_link(source.kind, source.identifier, add, action)
                action(tr('查看全部数值来源'), 'sources')
            else:
                add(tr('配置来源目录（不代表均影响同一属性）'), 'muted')
                for row in data['sections']['sources']:
                    self._management_source_link(row.get('source_kind'), row.get('source_id'), add, action, row['label'])
        elif kind == 'task':
            from .task_journal import journal_tasks
            task = next((t for t in journal_tasks(state) if t['task_uid'] == identity), None)
            if task is None:
                add(tr('这项委托已经不在进行中。'), 'risk'); return body, actions
            add(task['name'], 'heading'); add(task['status_line']); add(task['deliver'], 'muted')
            related = task_items(state, identity)
            if not related: add(tr('行囊中没有此任务要求的具名物品。'), 'muted')
            for item_id in related:
                item = item_by_id(state, item_id)
                action(tr('查看')+' · '+item_facts(state, item_id)['name'], 'link', 'item', item_id, 'inventory')
        else:
            add(tr('没有可显示的详情。'), 'muted')
        return body, actions

    def _management_source_link(self, kind, identity, add, action, fallback=''):
        state = self.session.state
        if kind == 'equipment':
            item = item_by_id(state, identity)
            if item: action(item_facts(state, identity)['name'], 'link', 'item', identity, 'equipment')
        elif kind == 'memory' and identity in state.memory_fragments:
            action(tr(ITEM_DEFINITIONS.get(identity, {}).get('name', identity)), 'link', 'memory', identity, 'equipment')
        elif kind == 'insight' and identity in state.insights:
            action(tr(identity), 'link', 'insight', identity, 'equipment')
        elif kind == 'portent' and identity in state.portents:
            from ..materials import portent_def
            action(tr(portent_def(identity).name), 'link', 'portent', identity, 'portents')
        elif fallback: add(fallback, 'muted')

    def _management_activate(self, action):
        command, args = action['command'], action['args']
        if command == 'back': self._sidebar_back()
        elif command == 'link': self.open_sidebar_detail(*args)
        elif command == 'sources': self.open_sidebar_detail('sources', '', 'portents')
        elif command == 'item': self._sidebar_execute_item(*args)
        elif command == 'legacy_item':
            item = item_by_id(self.session.state, args[0])
            if item: self._open_item_menu(self.session.state.inventory.index(item))
        elif command in ('equip_memory', 'unequip_memory'):
            result = self._apply(command, *args)
            self.show_toast(result.message, 3)
            if result.changed: self._sidebar_back()

    def _sidebar_execute_item(self, identity, command):
        if not self._sidebar_navigation_allowed(): return False
        state = self.session.state
        item = item_by_id(state, identity)
        if item is None:
            self.show_toast(tr('这件物品已经不在行囊中。'), 3); return False
        if command not in {entry[2] for entry in self._item_menu_actions(item)}:
            self.show_toast(tr('操作条件已经变化，请重新查看。'), 3)
            return False
        if command == 'toggle_equip' and item.effect == 'container':
            index = state.inventory.index(item)
            result = self._apply('use', index)
            if result.data.get('container_menu') is not None:
                self._open_container_overlay(result.data['container_menu'])
            return True
        old_target = self.item_menu_target
        self.item_menu_target = identity
        self.activate_item_menu(command)
        if self.item_menu_target == identity: self.item_menu_target = old_target
        return True

    def _refresh_sidebar_tools(self):
        # Categories/subpages already have their own row; avoid a second toolbar.
        # 每次 refresh_view 都跑：用子控件直读代替 `#sidebar-tools Button`
        # 后代选择器——后者每次都要走完整控件树的 CSS 匹配（实测 ~1.0ms），
        # 而这里只是把一行已经隐藏的按钮再藏一遍。
        toolbar = self.query_one('#sidebar-tools')
        if toolbar.display:
            toolbar.display = False
        for button in toolbar.children:
            if button.display:
                button.display = False

    def handle_sidebar_tool(self, button_id):
        if not button_id or not button_id.startswith('sidebar-'): return False
        if not self._sidebar_navigation_allowed(): return True
        action = button_id[8:]
        mode = self.panel_mode
        construct = mode == 'actions' and self._panel_subpage_id() == 'constructs'
        if action == 'back': self._sidebar_back()
        elif action == 'fold':
            values = self.sidebar_preferences()['collapsed']
            values.remove(mode) if mode in values else values.append(mode)
            self._save_sidebar_preferences(); self.refresh_view()
        elif action == 'related':
            from .task_journal import journal_actions
            entries = journal_actions(self.session.state)
            uid = entries[self.panel_selection] if 0 <= self.panel_selection < len(entries) else ''
            self.open_sidebar_detail('task', uid, 'tasks')
        elif action == 'menu': self._management_open_selected()
        elif action == 'filter' and mode == 'portents':
            values = ('全部','正面','负面','其他')
            self._sidebar_portent_filter = values[(values.index(getattr(self,'_sidebar_portent_filter','全部'))+1)%len(values)]
            self.panel_selection = self.panel_scroll = 0; self.refresh_view()
        elif construct and action in ('search','filter','clear','pin'):
            if action == 'search': self._open_inventory_search()
            elif action == 'filter': self._sidebar_only_favorites = not getattr(self,'_sidebar_only_favorites',False)
            elif action == 'clear': self._sidebar_ability_query = ''
            else:
                key = self._panel_entry_key(self.panel_selection)
                if key and key.startswith('ability:'):
                    ability = key[8:]; pins = self.sidebar_preferences()['favorites']
                    pins.remove(ability) if ability in pins else pins.append(ability)
                    self._save_sidebar_preferences()
            self.refresh_view()
        else: return super().handle_sidebar_tool(button_id)
        return True

    def _management_open_selected(self):
        mode, state = self.panel_mode, self.session.state
        if mode in ('inventory','equipment'):
            if mode == 'equipment' and self._panel_subpage_id() == 'memory':
                self._activate_panel_selection(); return
            choices = dict(self._sidebar_inventory_choices())
            identity = choices.get(self.panel_selection)
            if identity: self.open_sidebar_item(identity)
        elif mode == 'tasks':
            self.handle_sidebar_tool('sidebar-related')
        elif mode == 'self_stats':
            key = self._panel_entry_key(self.panel_selection)
            if key: self.open_sidebar_detail('stat', key, 'portents')
        elif mode == 'insights' and 0 <= self.panel_selection < len(state.insights):
            self.open_sidebar_detail('insight', state.insights[self.panel_selection], 'equipment')
        else: self._shortcut_detail()

    def _open_inventory_search(self):
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'constructs':
            self._sidebar_search_kind = 'abilities'
            self.qol_searching = True; self.path.clear(); self._clear_held()
            field = self.query_one('#qol-search-input')
            field.value = getattr(self, '_sidebar_ability_query', '')
            self._refresh_qol(); self.call_after_refresh(field.focus)
            return
        self._sidebar_search_kind = 'inventory'
        return super()._open_inventory_search()

    def _qol_search_changed(self, value):
        if self.qol_searching and getattr(self,'_sidebar_search_kind','inventory') == 'abilities':
            self._sidebar_ability_query = value
            self.panel_scroll = 0; self.refresh_view(); return
        return super()._qol_search_changed(value)

    def _refresh_qol(self):
        super()._refresh_qol()
        if self.qol_searching and getattr(self,'_sidebar_search_kind','inventory') == 'abilities':
            self.query_one('#qol-confirm-text').update(Text(tr('搜索已学构想：名称、说明或标识；Enter/Esc 返回列表')))

    def _handle_qol_key(self, event):
        if (self._sidebar_navigation_allowed() and event.key == 'alt+f'
                and self.panel_mode == 'actions' and self._panel_subpage_id() == 'constructs'):
            self._open_inventory_search(); self._mark_key_handled(event.key)
            event.stop(); event.prevent_default(); return True
        if (self._sidebar_navigation_allowed() and event.key == 'alt+l' and self.panel_mode == 'portents'):
            self.handle_sidebar_tool('sidebar-filter'); self._mark_key_handled(event.key)
            event.stop(); event.prevent_default(); return True
        return super()._handle_qol_key(event)

    def open_board_editor(self, instance_id=None):
        self._management_board_return = self._sidebar_snapshot() if self.sidebar_workspace else None
        return super().open_board_editor(instance_id)

    def close_board_editor(self, committed=False):
        snapshot = getattr(self, '_management_board_return', None)
        self._management_board_return = None
        super().close_board_editor(committed=committed)
        if snapshot is None:
            return
        from .sidebar_workspaces import MODE_WORKSPACE
        if MODE_WORKSPACE.get(snapshot[0]) == 'equipment':
            # 构筑工作区内打开（装备/记忆/洞察）：关闭仍回原页（设计方案 §12.4）。
            self._sidebar_back_stack = [*getattr(self, '_sidebar_back_stack', []), snapshot][-8:]
            self._sidebar_back()
        else:
            # 2026-10-24 玩家优化 4：联想盘本身就是装备页的入口——从其他
            # 工作区/事件记录关掉编辑器后直接落在构筑·装备页（成句与效果
            # 就在那里），不再弹回调用处让玩家再点一次 构筑→装备。
            self._sidebar_back_stack = []
            self.open_sidebar_route('equipment-board')
