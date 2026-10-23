"""Right-sidebar navigation, read-only overviews and per-route browsing state.

Business panel modes remain intact so existing left editors and action settlement
keep their contracts. No state in this module is persisted to a world save.
"""
from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.text import Text

from ..i18n import tr
from .panel_fields import FIELD_COLORS as C


@dataclass(frozen=True)
class SidebarRoute:
    key: str
    label: str
    english: str
    mode: str
    subpage: str = ''


# IDs of the five existing buttons are retained; their labels are workspaces.
WORKSPACES = (
    ('actions', '行动', 'Act', 'world'),
    ('inventory', '行囊', 'Pack', 'inventory'),
    ('equipment', '构筑', 'Build', 'build_overview'),
    ('portents', '自身', 'Self', 'self_overview'),
    ('tasks', '日志', 'Log', 'tasks'),
)
ROUTES = {
    'actions': (
        SidebarRoute('action-overview', '总览', 'All', 'world'),
        SidebarRoute('constructs', '构想', 'Cast', 'actions', 'constructs'),
        SidebarRoute('fire', '发射', 'Fire', 'actions', 'fire'),
        SidebarRoute('tamper', '篡改', 'Edit', 'actions', 'tamper'),
        SidebarRoute('nearby', '周围', 'Near', 'nearby'),
    ),
    'inventory': (),  # The inventory's existing filters stay in its own content.
    'equipment': (
        SidebarRoute('build-overview', '总览', 'All', 'build_overview'),
        SidebarRoute('equipment-board', '装备', 'Gear', 'equipment', 'board'),
        SidebarRoute('equipment-memory', '记忆', 'Memory', 'equipment', 'memory'),
        SidebarRoute('insights', '洞察', 'Insights', 'insights'),
    ),
    'portents': (
        SidebarRoute('self-overview', '总览', 'All', 'self_overview'),
        SidebarRoute('portents', '征兆', 'Signs', 'portents'),
        SidebarRoute('self-stats', '数值', 'Stats', 'self_stats'),
        SidebarRoute('self-audit', '详查', 'Full', '@self'),
    ),
    'tasks': (
        SidebarRoute('quests', '任务', 'Tasks', 'tasks'),
        SidebarRoute('records', '记录', 'Events', 'journal_log'),
    ),
}
ROUTE_BY_KEY = {route.key: route for routes in ROUTES.values() for route in routes}
DETAIL_MODES = {'nearby', 'self_stats'}

OVERVIEW_MODES = {'world', 'build_overview', 'self_overview'}
MODE_WORKSPACE = {
    route.mode: key for key, routes in ROUTES.items() for route in routes
    if not route.mode.startswith('@')
} | {'inventory': 'inventory', 'catalog': 'actions'}
_CONSOLE = Console(legacy_windows=False)


@dataclass(frozen=True)
class BrowsePosition:
    selection: int = 0
    identity: str | None = None
    scroll: int = 0
    memory_scroll: int = 0
    query: str = ''
    sort: str = '原序'
    expanded_key: str | None = None
    details_expanded: bool = False
    message_count: int = 0


class SidebarWorkspacesMixin:
    @property
    def sidebar_workspace(self):
        return MODE_WORKSPACE.get(self.panel_mode, '')

    def _sidebar_route_key(self):
        return self.panel_mode, self._panel_subpage_id()

    def _remember_sidebar_position(self):
        if not self.sidebar_workspace:
            return
        positions = self.__dict__.setdefault('_sidebar_positions', {})
        selected = self.panel_selection
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'board':
            indices = self._sidebar_selection_candidates()
            selected_key = self._panel_entry_key(indices[selected]) if 0 <= selected < len(indices) else None
        else:
            selected_key = self._panel_entry_key(selected)
        positions[self._sidebar_route_key()] = BrowsePosition(
            selected, selected_key, self.panel_scroll,
            self.memory_scroll, getattr(self, 'inventory_query', ''),
            getattr(self, 'inventory_sort', '原序'),
            self.expanded_key, self.details_expanded, len(self.session.state.messages))
        self.__dict__.setdefault('_sidebar_last_routes', {})[self.sidebar_workspace] = self._sidebar_route_key()

    def _sidebar_selection_candidates(self):
        state = self.session.state
        if self.panel_mode == 'inventory':
            return list(self._inventory_visible_indices())
        if self.panel_mode == 'equipment':
            if self._panel_subpage_id() == 'memory':
                return []
            return [i for i, item in enumerate(state.inventory) if item.slot]
        if self.panel_mode == 'portents':
            return list(range(len(self._portent_entries(state))))
        return list(range(self._panel_item_count()))

    def _restore_sidebar_position(self):
        saved = self.__dict__.get('_sidebar_positions', {}).get(self._sidebar_route_key())
        self.panel_selection = saved.selection if saved else 0
        self.panel_scroll = saved.scroll if saved else 0
        if saved and self.panel_mode == 'journal_log' and saved.scroll:
            self.panel_scroll += max(0, len(self.session.state.messages) - saved.message_count)
        self.memory_scroll = saved.memory_scroll if saved else 0
        self.expanded_key = saved.expanded_key if saved else None
        self.details_expanded = saved.details_expanded if saved else False
        if self.panel_mode == 'inventory':
            self.inventory_filter = self._panel_subpage_id()
            if saved:
                self.inventory_query = saved.query
                self.inventory_sort = saved.sort
        candidates = self._sidebar_selection_candidates()
        if saved and saved.identity is not None:
            match = next((i for i in candidates if self._panel_entry_key(i) == saved.identity), None)
            if match is not None:
                self.panel_selection = match
            elif candidates:
                self.panel_selection = min(candidates, key=lambda i: abs(i - saved.selection))
        if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'board':
            match = next((i for i, source_index in enumerate(candidates)
                          if saved and self._panel_entry_key(source_index) == saved.identity), None)
            self.panel_selection = match if match is not None else min(self.panel_selection, max(0, len(candidates) - 1))
            candidates = list(range(len(candidates)))
        if candidates and self.panel_selection not in candidates:
            self.panel_selection = candidates[0]
        elif not candidates:
            self.panel_selection = -1 if self.panel_mode == 'inventory' else 0
        # The old renderer resets every mode change. This transition has already
        # restored the correct route, so it must not clear it again while drawing.
        self._panel_mode_seen = self.panel_mode

    def _sidebar_transition(self, mode, *, subpage=None, focus=False, refresh=True):
        self._sync_sidebar_owner()
        self._remember_sidebar_position()
        self.panel_mode = mode
        if subpage is not None:
            self.panel_subpages[mode] = subpage
        self._restore_sidebar_position()
        if mode == 'journal_log':
            self._sidebar_message_count = len(self.session.state.messages)
        self._panel_enter_mode = mode if focus else None
        if refresh and self.is_running:
            self.refresh_view()

    def _sidebar_navigation_allowed(self):
        return not (self.home_mode or self.panel_mode == 'event_dialog' or self._modal_menu_open()
                    or self._active_tamper_editor() is not None
                    or self.aiming or self.sentence_aim is not None
                    or self.layer_observation is not None
                    or self._inspection_active() or self.controls_help_open
                    or self.qol_confirmation is not None or self.qol_searching
                    or self.session.state.run_over or self._floor_transition is not None)

    def open_sidebar_workspace(self, workspace):
        if not self._sidebar_navigation_allowed():
            return False
        default = next((row[3] for row in WORKSPACES if row[0] == workspace), None)
        if default is None:
            return False
        if self.sidebar_workspace == workspace:
            return True
        mode, subpage = self.__dict__.get('_sidebar_last_routes', {}).get(workspace, (default, None))
        state = self.session.state
        if state.tutorial.get('active'):
            state.tutorial_events['panel_opened'] = mode
        self._sidebar_transition(mode, subpage=subpage)
        return True

    def open_sidebar_route(self, key):
        route = ROUTE_BY_KEY.get(key)
        if route is None or not self._sidebar_navigation_allowed():
            return False
        if route.mode == '@self':
            self._toggle_self_audit()
            return True
        if route.mode == self.panel_mode and (not route.subpage or route.subpage == self._panel_subpage_id()):
            return True
        state = self.session.state
        if state.tutorial.get('active'):
            state.tutorial_events['panel_opened'] = route.mode
        self._sidebar_transition(route.mode, subpage=route.subpage or None, focus=True)
        return True

    def _sidebar_overview_entries(self):
        return tuple(route for route in ROUTES[self.sidebar_workspace]
                     if route.mode != self.panel_mode)

    def _sidebar_overview_text(self, state):
        from ..core.content import ABILITY_DEFINITIONS
        from .firing_presentation import current_source, current_resource_text
        label = next(row[1] for row in WORKSPACES if row[0] == self.sidebar_workspace)
        width = max(8, self.query_one('#panel').content_size.width)
        lines = []
        rows = []

        def add(text, item=-1):
            text = text if isinstance(text, Text) else Text(text, style=C['text'])
            for line in text.wrap(_CONSOLE, width, overflow='fold'):
                lines.append(line)
                rows.append(item)

        add(Text(tr(label), style='bold ' + C['heading']))
        if self.panel_mode in self.sidebar_preferences()['collapsed']:
            add(tr('总览内容已收起；可用上方按钮展开。'))
        elif self.panel_mode == 'world':
            name, resource = current_source(self)
            if name == tr('当前发射源：无'):
                name = tr('无')
            add(Text(tr('当前发射源') + ': ' + tr(name), style=C['word']))
            if resource:
                add(tr(resource))
            current = current_resource_text(self)
            if current.plain:
                add(current)
            abilities = [tr(ABILITY_DEFINITIONS[a]['name']) for a in state.abilities if a in ABILITY_DEFINITIONS]
            add(tr('已学构想：{n}', n=len(abilities)), -1)
            pinned = [key for key in self.sidebar_preferences()['favorites'] if key in state.abilities]
            add(tr('固定构想：{n}', n=len(pinned)))
            if pinned:
                add(' · '.join(tr(ABILITY_DEFINITIONS[key]['name']) for key in pinned))
            else:
                add(tr('可在构想列表中手动固定常用构想。'))
            from ..core.realm_challenges import challenge_status
            challenge = challenge_status(state)
            if challenge:
                add(challenge)
            if state.depth in (28, 29, 30) and state.map_form == '深层边界':
                add(state.epilogue_progress())
            add(tr('选择下方内容，或直接在地图行动。'))
        elif self.panel_mode == 'build_overview':
            by_id = {item.instance_id: item for item in state.inventory}
            equipped = [by_id[i] for i in state.equipped.values() if i in by_id]
            add(tr('已装备 {n} 件', n=len(equipped)))
            compiled = state.equipment.compiled()
            for sentence in compiled.sentences[:3]:
                add(Text(sentence.text, style=C['effect']))
                if sentence.reason:
                    add(Text(tr(sentence.reason), style=C['risk']))
            add(tr('盘面占用：{used}/{total}', used=state.board.area_used(), total=state.board.width * state.board.height))
            for item in equipped:
                add(Text('  ' + tr(item.name), style=C['word']))
            add(tr('记忆碎片：{n}', n=len(state.memory_fragments)))
            for key in state.memory_fragments:
                from ..core.content import ITEM_DEFINITIONS
                add('  ' + tr(ITEM_DEFINITIONS.get(key, {}).get('name', key)))
            add(tr('已学洞察：{n}', n=len(state.insights)))
            for key in state.insights[:3]:
                add('  ' + tr(key))
        else:
            from ..core.self_audit import self_audit
            audit = self_audit(state)
            for name, value, maximum, tier in audit['bars']:
                add(f'{name} {value}/{maximum}  {tier}')
            entries = self._portent_entries(state)
            add(tr('当前征兆：{n}', n=len(entries)))
            for entry in entries[:3]:
                add(tr(entry['name']) + ' · ' + tr(entry.get('effect', '')))
            add(tr('完整效果与数值来源可从下方查看。'))
        for index, route in enumerate(self._sidebar_overview_entries()):
            prefix = '▶ ' if index == self.panel_selection else '  '
            add(Text(prefix + tr(route.label), style=C['condition'] + (' bold underline' if index == self.panel_selection else '')), index)
        viewport = max(1, self.query_one('#panel').content_size.height)
        self.panel_scroll = min(self.panel_scroll, max(0, len(lines) - viewport))
        start = self.panel_scroll
        self._sidebar_overview_rows = rows
        self._sidebar_overview_line_count = len(lines)
        self._panel_rows = rows[start:start + viewport]
        return Text('\n').join(lines[start:start + viewport])

    def _panel_text_build(self, state):
        self._sync_sidebar_owner()
        if self.panel_mode == 'journal_log':
            count = len(state.messages)
            previous = getattr(self, '_sidebar_message_count', count)
            if self.panel_scroll > 0:
                self.panel_scroll += max(0, count - previous)
            self._sidebar_message_count = count
        if self.panel_mode in DETAIL_MODES and self.tamper_editor is None:
            return self._sidebar_detail_text(state)
        if self.panel_mode in OVERVIEW_MODES and self.tamper_editor is None:
            return self._sidebar_overview_text(state)
        return super()._panel_text_build(state)

    def _panel_item_count(self):
        if self.panel_mode in DETAIL_MODES:
            return len(self._sidebar_detail_entries())
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'fire':
            return len(self._firing_source_options())
        if self.panel_mode in OVERVIEW_MODES:
            return len(self._sidebar_overview_entries())
        return super()._panel_item_count()

    def _panel_entry_key(self, index):
        if self.panel_mode in DETAIL_MODES:
            entries = self._sidebar_detail_entries()
            return entries[index]['key'] if 0 <= index < len(entries) else None
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'fire':
            options = self._firing_source_options()
            return 'source:' + options[index]['source_key'] if 0 <= index < len(options) else None
        if self.panel_mode in OVERVIEW_MODES:
            entries = self._sidebar_overview_entries()
            return 'sidebar:' + entries[index].key if 0 <= index < len(entries) else None
        return super()._panel_entry_key(index)

    def _activate_panel_selection(self, key_hint=None):
        if self.panel_mode in DETAIL_MODES:
            key = key_hint or self._panel_entry_key(self.panel_selection)
            entry = next((entry for entry in self._sidebar_detail_entries() if entry['key'] == key), None)
            if entry and self._sidebar_navigation_allowed():
                if self.panel_mode == 'nearby':
                    self.open_cell_detail(entry['target'])
                else:
                    self.expanded_key = None if self.expanded_key == key else key
                    self.refresh_view()
            return
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'fire':
            key = key_hint or self._panel_entry_key(self.panel_selection)
            valid = {option['source_key'] for option in self._firing_source_options()}
            if key and key.startswith('source:') and key[7:] in valid:
                self._last_firing_source_key = key[7:]
                self.refresh_view()
            return
        if self.panel_mode in OVERVIEW_MODES:
            key = key_hint or self._panel_entry_key(self.panel_selection)
            if key and key.startswith('sidebar:'):
                self.open_sidebar_route(key.partition(':')[2])
            return
        return super()._activate_panel_selection(key_hint=key_hint)

    def _move_panel_selection(self, delta):
        if self.panel_mode not in OVERVIEW_MODES | DETAIL_MODES:
            return super()._move_panel_selection(delta)
        count = self._panel_item_count()
        if count:
            self.panel_selection = (self.panel_selection + delta) % count
        self._panel_enter_mode = self.panel_mode
        rows = getattr(self, '_sidebar_overview_rows', [])
        selected = [i for i, value in enumerate(rows) if value == self.panel_selection]
        if selected:
            height = max(1, self.query_one('#panel').content_size.height)
            self.panel_scroll = max(0, min(self.panel_scroll, selected[0]))
            self.panel_scroll = max(self.panel_scroll, selected[-1] - height + 1)
        self.refresh_view()

    def _scroll(self, amount):
        if self.panel_mode not in OVERVIEW_MODES | DETAIL_MODES:
            return super()._scroll(amount)
        height = max(1, self.query_one('#panel').content_size.height)
        limit = max(0, getattr(self, '_sidebar_overview_line_count', 0) - height)
        self.panel_scroll = max(0, min(limit, self.panel_scroll - amount))
        self.refresh_view()


    def _sidebar_context_text(self, state, width):
        # Preserve the legacy terrain narrative, semantic colors, knowledge
        # permissions and hover-preview target without a summary/truncation layer.
        return super()._hover_text(state, width)


    def _refresh_sidebar_tools(self):
        from ..i18n import get_language
        inventory = self.panel_mode == 'inventory'
        visible = self.layer_observation is None and (inventory or self.panel_mode in ('equipment', 'insights', 'portents', 'actions', 'catalog'))
        self.query_one('#sidebar-tools').display = visible
        labels = {
            'search': ('搜', 'Find', '搜索'), 'filter': ('类', 'Type', '筛选'),
            'sort': ('序', 'Sort', '排序'), 'expand': ('详情', 'More', '展开'),
            'menu': ('操作', 'Use', '操作'), 'clear': ('×', '×', '清除搜索'),
        }
        key = (self.panel_mode, self._panel_subpage_id(), get_language(), bool(self.inventory_query), self.layer_observation is not None)
        if getattr(self, '_sidebar_tools_key', None) == key:
            return
        self._sidebar_tools_key = key
        for action, (chinese, english, tooltip) in labels.items():
            button = self.query_one('#sidebar-' + action)
            button.label = english if get_language() == 'en' else chinese
            button.tooltip = tr(tooltip)
            button.display = visible and (inventory or action in ('expand', 'menu'))
            if action == 'clear':
                button.display = inventory and bool(self.inventory_query)
            if action == 'menu':
                button.display = visible and (inventory or self.panel_mode in ('equipment', 'catalog'))
                if self.panel_mode == 'equipment' and self._panel_subpage_id() == 'memory':
                    button.display = False

    def handle_sidebar_tool(self, button_id):
        if not button_id or not button_id.startswith('sidebar-'):
            return False
        if not self._sidebar_navigation_allowed():
            return True
        action = button_id.removeprefix('sidebar-')
        if action == 'menu':
            self._shortcut_detail()
        elif action == 'clear':
            self.inventory_query = ''
            self._qol_reselect_inventory()
            self.refresh_view()
        elif action in ('search', 'filter', 'sort', 'expand'):
            self._qol_button('qol-' + action)
        return True


    def _update_panel_hover(self, offset_y):
        # Left floating windows use their own hover controllers.
        return

    def _fire_actions_lines(self, state):
        from ..core.content import ITEM_DEFINITIONS
        lines, rows = super()._fire_actions_lines(state)
        options = self._firing_source_options()
        width = max(8, self.query_one('#panel').content_size.width)
        for index, option in enumerate(options):
            name = ' + '.join(tr(ITEM_DEFINITIONS[key]['name']) for key in option.get('definition_ids', ()) if key in ITEM_DEFINITIONS)
            if not name:
                name = tr('聚合弹') if option['source_key'] == 'aggregate' else tr('基础发射（旧档继承）')
            chosen = option['source_key'] == getattr(self, '_last_firing_source_key', None)
            body = Text(('▶ ' if index == self.panel_selection else '  ') + name,
                        style=C['word'] + (' bold underline' if chosen else ''))
            if chosen:
                body.append(' ' + tr('已选择'), style=C['effect'])
            if option.get('reason'):
                body.append(' · ' + tr(option['reason']), style=C['risk'])
            for line in body.wrap(_CONSOLE, width, overflow='fold'):
                lines.append(line)
                rows.append(index)
        return lines, rows


    def _sidebar_detail_entries(self):
        if self.panel_mode == 'self_stats':
            return getattr(self, '_sidebar_stat_entries', [])
        state = self.session.state
        entries = []
        for entity in state.enemies:
            if entity.integrity > 0 and state.is_visible(entity.x, entity.y):
                entries.append(dict(key='entity:' + str(entity.id), name=state.observed_entity_label(entity),
                                    summary=tr(entity.relation) + ' · ' + tr(entity.alert_state),
                                    target=(entity.x, entity.y)))
        for event in state.events:
            if not event.resolved and state.is_visible(event.x, event.y):
                entries.append(dict(key=f'event:{event.event_id}:{event.x},{event.y}', name=tr(event.name),
                                    summary=tr('事件'), target=(event.x, event.y)))
        for drop in state.world_items:
            if state.is_visible(drop.x, drop.y):
                name = '？？？' if 'oblivion_strong' in state.portents else tr(drop.item.name)
                entries.append(dict(key='drop:' + drop.item.instance_id, name=name,
                                    summary=f'×{drop.item.quantity}', target=(drop.x, drop.y)))
        return entries

    def _sidebar_detail_text(self, state):
        from .panel_fields import stat_color
        width = max(8, self.query_one('#panel').content_size.width)
        lines, rows = [], []

        def add(text, index=-1):
            for line in text.wrap(_CONSOLE, width, overflow='fold'):
                lines.append(line)
                rows.append(index)

        if self.panel_mode == 'self_stats':
            from ..core.self_audit import self_audit
            from .self_audit import SA_CATEGORIES
            data = self_audit(state)
            labels = dict(SA_CATEGORIES)
            entries = []
            for category, category_rows in data['sections'].items():
                if category in ('overview', 'sources'):
                    continue
                for row in category_rows:
                    entries.append(dict(row, key='stat:' + category + ':' + row['key'], category=labels[category]))
            self._sidebar_stat_entries = entries
            add(Text(tr('数值与来源'), style='bold ' + C['heading']))
            previous = None
            for index, row in enumerate(entries):
                if row['category'] != previous:
                    add(Text(tr(row['category']), style=C['condition']))
                    previous = row['category']
                selected = index == self.panel_selection
                add(Text(('▶ ' if selected else '  ') + row['label'] + '  ' + row['value'],
                         style=stat_color(row.get('stat_id', ''), state) + (' bold underline' if selected else '')), index)
                if self.details_expanded or self.expanded_key == row['key']:
                    if row['base'] is not None:
                        add(Text('  ' + tr('基础值：') + str(row['base']), style=C['count']), index)
                    for source in row['sources']:
                        add(Text('  ' + tr('来源：') + str(source), style=C['grammar']), index)
                    for note in row['notes']:
                        add(Text('  ' + str(note), style=C['muted']), index)
        else:
            entries = self._sidebar_detail_entries()
            add(Text(tr('周围对象') + f'  {len(entries)}', style='bold ' + C['heading']))
            if not entries:
                add(Text(tr('视野中没有可列出的对象。'), style=C['muted']))
            for index, entry in enumerate(entries):
                x, y = entry['target']
                dx, dy = x - state.player.x, y - state.player.y
                direction = (('西' if dx < 0 else '东') if dx else '') + (('北' if dy < 0 else '南') if dy else '')
                direction = tr(direction or '脚下')
                selected = index == self.panel_selection
                add(Text(('▶ ' if selected else '  ') + direction + ' · ' + entry['name'] + f' ({x},{y})',
                         style=C['identity'] + (' bold underline' if selected else '')), index)
                add(Text('  ' + entry['summary'], style=C['muted']), index)
        viewport = max(1, self.query_one('#panel').content_size.height)
        self.panel_scroll = min(self.panel_scroll, max(0, len(lines) - viewport))
        self._sidebar_overview_rows = rows
        self._sidebar_overview_line_count = len(lines)
        self._panel_rows = rows[self.panel_scroll:self.panel_scroll + viewport]
        return Text('\n').join(lines[self.panel_scroll:self.panel_scroll + viewport])


    def _sync_sidebar_owner(self):
        owner = id(self.session.state)
        if getattr(self, '_sidebar_owner', owner) != owner:
            self._sidebar_positions = {}
            self._sidebar_last_routes = {}
            self._sidebar_stat_entries = []
            self.panel_selection = self.panel_scroll = self.memory_scroll = 0
            self.expanded_key = None
            self._panel_enter_mode = None
        self._sidebar_owner = owner
