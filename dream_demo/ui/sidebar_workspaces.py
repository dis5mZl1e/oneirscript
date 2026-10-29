"""Right-sidebar navigation, read-only workspace pages and per-route browsing state.

Business panel modes remain intact so existing left editors and action settlement
keep their contracts. No state in this module is persisted to a world save.
"""
from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.text import Text

from ..i18n import get_language, tr
from . import terse
from .panel_fields import FIELD_COLORS as C
from .panels import kv_grid
from .styles import RIGHT_PANEL_MODES


@dataclass(frozen=True)
class SidebarRoute:
    key: str
    label: str
    english: str
    mode: str
    subpage: str = ''


# 六个工作区（2026-10-24 五区改六区）：主按钮 ID 沿用既有命名，environment
# 为新增；末列是打开本区时落入的默认面板模式。tasks 默认 journal_log——
# 显式浏览事件记录（Enter 交给面板、滚动锚定生效）；未锁定成功世界行动
# 回跳的 world 模式由「记录」子路由承接，两种模式渲染同一份事件记录。
WORKSPACES = (
    ('actions', '行动', 'Act', 'actions'),
    ('inventory', '行囊', 'Pack', 'inventory'),
    ('equipment', '构筑', 'Build', 'equipment'),
    ('portents', '自身', 'Self', 'portents'),
    ('environment', '环境', 'Env', 'nearby'),
    ('tasks', '日志', 'Log', 'journal_log'),
)
ROUTES = {
    'actions': (
        SidebarRoute('constructs', '构想', 'Cast', 'actions', 'constructs'),
        SidebarRoute('fire', '发射', 'Fire', 'actions', 'fire'),
        SidebarRoute('tamper', '篡改', 'Edit', 'actions', 'tamper'),
    ),
    'inventory': (),  # The inventory's existing filters stay in its own content.
    'equipment': (
        SidebarRoute('equipment-board', '装备', 'Gear', 'equipment', 'board'),
        SidebarRoute('equipment-memory', '记忆', 'Memory', 'equipment', 'memory'),
        SidebarRoute('insights', '洞察', 'Insights', 'insights'),
    ),
    'portents': (
        SidebarRoute('portents', '征兆', 'Signs', 'portents'),
        SidebarRoute('self-stats', '数值', 'Stats', 'self_stats'),
        SidebarRoute('self-audit', '详查', 'Full', '@self'),
    ),
    'environment': (
        SidebarRoute('nearby', '周围', 'Near', 'nearby'),
    ),
    'tasks': (
        SidebarRoute('records', '记录', 'Events', 'world'),
        SidebarRoute('quests', '任务', 'Tasks', 'tasks'),
    ),
}
ROUTE_BY_KEY = {route.key: route for routes in ROUTES.values() for route in routes}
# Keep the old route callable without showing a duplicate journal tab.
ROUTE_BY_KEY['action-overview'] = ROUTE_BY_KEY['records']
SUBTAB_COLORS = ('#86c9f4', '#c9a0ff', '#ffd166', '#73dfb1', '#f39cb6', '#a9bcff', '#e5bf91')
DETAIL_MODES = {'nearby', 'self_stats'}

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

    def _default_panel_mode(self) -> str:
        """右侧面板的「默认页」。

        左侧事件记录开启时默认页是行囊——事件流已经压在地图左下，右栏再显示
        同一份记录就是重复；关闭时保持旧默认（事件记录 world）。所有「世界行动
        完成后自动回跳」的入口都读这里，不要再写死 world。
        """
        return "inventory" if bool(self.config.get("left_event_log")) else "world"

    # ---- 右侧固定（~ 锁定）的页面快照 -------------------------------------
    # 新语义（2026-10-26 玩家定稿）：~ 只负责「右栏当前页不许自动切换」。
    # 自动切换散落在行动结算、瞄准、攻击确认、教程等许多入口，逐个改容易漏；
    # 这里在每次刷新前把右栏页恢复成锁定时的快照，只有手动键鼠切换
    # （_sidebar_transition(manual=True) / 打开详情 / 返回）才更新快照。
    def _locked_page_snapshot(self):
        return (self.panel_mode, self._panel_subpage_id(),
                dict(getattr(self, "_sidebar_detail_ref", {}) or {}))

    def _lock_panel_page(self) -> None:
        if self.home_mode:
            return
        mode = self.panel_mode
        if mode in RIGHT_PANEL_MODES or mode == "world":
            self._locked_panel_page = self._locked_page_snapshot()
        else:
            self._locked_panel_page = (self._default_panel_mode(), None, {})

    def _clear_locked_panel_page(self) -> None:
        self._locked_panel_page = None

    def _update_locked_panel_page(self) -> None:
        if getattr(self, "panel_locked", False) and not self.home_mode:
            self._locked_panel_page = self._locked_page_snapshot()

    def _enforce_locked_panel_page(self) -> None:
        """锁定态把右栏页恢复成快照；模态覆盖层（对话/暂停/编辑器）不拦。"""
        if self.home_mode or not getattr(self, "panel_locked", False):
            return
        snapshot = getattr(self, "_locked_panel_page", None)
        if snapshot is None:
            return
        mode, page, detail_ref = snapshot
        current = self.panel_mode
        if current not in RIGHT_PANEL_MODES and current != "world":
            return
        if (current == mode
                and (page is None or self._panel_subpage_id() == page)
                and dict(getattr(self, "_sidebar_detail_ref", {}) or {}) == detail_ref):
            return
        self.panel_mode = mode
        self._sidebar_detail_ref = detail_ref
        if page:
            self.panel_subpages[mode] = page
        self._restore_sidebar_position()

    def _sidebar_transition(self, mode, *, subpage=None, focus=False, refresh=True,
                            manual=True):
        self._sync_sidebar_owner()
        self._remember_sidebar_position()
        self.panel_mode = mode
        if subpage is not None:
            self.panel_subpages[mode] = subpage
        self._restore_sidebar_position()
        if mode == 'journal_log':
            self._sidebar_message_count = len(self.session.state.messages)
        self._panel_enter_mode = mode if focus else None
        # 焦点只在**手动**切页时更新：世界行动后的自动默认页回跳不得顺带改
        # 焦点区域（2026-10-24：移动/鼠标点击不把区域切回地图）。
        if not self.home_mode and manual:
            if focus:
                self.cursor_zone = "panel"
            elif mode == "world":
                self.cursor_zone = "map"
        if manual:
            self._update_locked_panel_page()
        # 2026-10-24 玩家定稿：右栏「行动·篡改」直接持续显示篡改操作项，
        # 不再需要先点「就地篡改」；进入该页即开右栏简版编辑器。
        self._ensure_side_tamper_on_route(mode)
        if refresh and self.is_running:
            self.refresh_view()

    def _ensure_side_tamper_on_route(self, mode):
        if self.home_mode or self.session.state.run_over:
            return
        if not (mode == 'actions' and self._panel_subpage_id() == 'tamper'):
            return
        editor = getattr(self, 'world_tamper_editor', None)
        if editor is not None:
            return  # Keep a left draft in its region until explicitly moved.
        if self._active_tamper_editor() is not None:
            return
        if not self._sidebar_navigation_allowed():
            return
        self.open_world_tamper_editor(host='side')

    def _sidebar_navigation_allowed(self):
        # 右栏简版篡改编辑器开着时仍允许切工作区/子页：切页会由既有
        # tamper_host 守卫关闭这次编辑，不会留下不可见却吞键的编辑器。
        side_tamper = (getattr(self, 'world_tamper_editor', None) is not None
                       and getattr(self.world_tamper_editor, 'host', 'map') == 'side'
                       and self.panel_mode == 'actions'
                       and self._panel_subpage_id() == 'tamper')
        return not (self.home_mode or self.panel_mode == 'event_dialog' or self._modal_menu_open(allow_inspection=True)
                    or (self._active_tamper_editor() is not None and not side_tamper
                        and getattr(self, 'world_tamper_editor', None) is None)
                    or self.debug_panel_open
                    or self.aiming or self.sentence_aim is not None
                    or self.layer_observation is not None
                    or self.controls_help_open
                    or self.qol_confirmation is not None or self.qol_searching
                    or self.session.state.run_over or self._floor_transition is not None)

    def open_sidebar_workspace(self, workspace, *, manual: bool = True):
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
        self._sidebar_transition(mode, subpage=subpage, manual=manual)
        return True

    def open_sidebar_route(self, key, *, manual: bool = True):
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
        self._sidebar_transition(route.mode, subpage=route.subpage or None, focus=True,
                                 manual=manual)
        return True

    def _panel_text_build(self, state):
        self._sync_sidebar_owner()
        if self.panel_mode in ('world', 'journal_log'):
            count = len(self._visible_game_messages(state))
            previous = getattr(self, '_sidebar_message_count', count)
            if self.panel_scroll > 0:
                self.panel_scroll += max(0, count - previous)
            self._sidebar_message_count = count
        if self.panel_mode in DETAIL_MODES and self.tamper_editor is None:
            text = self._sidebar_detail_text(state)
            if not terse.enabled(self.config) and get_language() == 'en':
                # 英文普通模式：环境页/数值页正文长单词缩写。
                text = terse.compact_english(text)
            return text
        return super()._panel_text_build(state)

    def _panel_item_count(self):
        if self.panel_mode in DETAIL_MODES:
            return len(self._sidebar_detail_entries())
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'fire':
            return len(self._firing_source_options())
        return super()._panel_item_count()

    def _panel_entry_key(self, index):
        if self.panel_mode in DETAIL_MODES:
            entries = self._sidebar_detail_entries()
            return entries[index]['key'] if 0 <= index < len(entries) else None
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'fire':
            options = self._firing_source_options()
            return 'source:' + options[index]['source_key'] if 0 <= index < len(options) else None
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
        return super()._activate_panel_selection(key_hint=key_hint)

    def _refresh_navigation_selection(self):
        if (self._sidebar_navigation_allowed() and not self._left_panel_open()
                and self._active_tamper_editor() is None
                and self.panel_mode in {'inventory', 'equipment', 'insights', 'portents',
                                        'catalog', 'nearby', 'self_stats', 'sidebar_detail',
                                        'actions', 'tasks', 'world'}):
            self._refresh_panel_selection()
            if self.panel_mode == 'actions':
                # Construct selection also owns the map interaction preview and
                # its context text; preserve hover-target ordering from world refresh.
                state = self.session.state
                context = self.query_one('#hover-info')
                context.update(self._sidebar_context_text(state, context.content_size.width or 44))
                self._apply_terrain_preview(state, self.query_one('#map'))
                self._refresh_map_hints()
        else:
            self.refresh_view()

    def _move_panel_selection(self, delta):
        if self.panel_mode not in DETAIL_MODES:
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
        self._refresh_navigation_selection()

    def _scroll(self, amount):
        if (self.panel_mode == 'actions' and self._panel_subpage_id() == 'fire'
                and self.query_one('#panel').content_size.height < 14):
            # Short firing panels pin supply/controls and scroll their sources.
            self._move_panel_selection(-amount)
            return
        if self.panel_mode not in DETAIL_MODES:
            return super()._scroll(amount)
        height = max(1, self.query_one('#panel').content_size.height)
        limit = max(0, getattr(self, '_sidebar_overview_line_count', 0) - height)
        self.panel_scroll = max(0, min(limit, self.panel_scroll - amount))
        self._refresh_navigation_selection()


    def _sidebar_context_text(self, state, width):
        # Preserve the legacy terrain narrative, semantic colors, knowledge
        # permissions and hover-preview target without a summary/truncation layer.
        return super()._hover_text(state, width)


    def _refresh_sidebar_tools(self):
        from ..i18n import get_language
        inventory = self.panel_mode == 'inventory'
        terse_mode = terse.enabled(self.config)
        symbol_mode = self._symbol_mode()
        visible = self.layer_observation is None and (inventory or self.panel_mode in ('equipment', 'insights', 'portents', 'actions', 'catalog'))
        self.query_one('#sidebar-tools').display = visible
        # 十个按钮全给双语：此前只覆盖前六个，固定/返回/物品/折叠在英文界面里
        # 一直是 compose 时的中文（2026-10-25 玩家反馈）。tooltip 同样走 tr。
        # 显示规则仍只管原来那六个，后四个的显隐另有来源，不在这里改。
        labels = {
            'search': ('搜', 'Find', '搜索'), 'filter': ('类', 'Type', '筛选'),
            'sort': ('序', 'Sort', '排序'), 'expand': ('详情', 'More', '展开'),
            'menu': ('操作', 'Use', '操作'), 'clear': ('×', '×', '清除搜索'),
            'pin': ('固定', 'Pin', '固定'), 'back': ('返回', 'Back', '返回'),
            'related': ('物品', 'Item', '物品'), 'fold': ('折叠', 'Fold', '折叠'),
        }
        managed = ('search', 'filter', 'sort', 'expand', 'menu', 'clear')
        key = (self.panel_mode, self._panel_subpage_id(), get_language(), bool(self.inventory_query),
               self.layer_observation is not None, terse_mode, symbol_mode)
        if getattr(self, '_sidebar_tools_key', None) == key:
            return
        self._sidebar_tools_key = key
        for action, (chinese, english, tooltip) in labels.items():
            button = self.query_one('#sidebar-' + action)
            # 少字模式（terse_mode）：十个按钮只显示符号，不显示中英文；
            # 普通模式保持既有中/英双语。tooltip 仍是 tr 文案。
            button.label = (terse.tool_symbol(action, symbol_mode) if terse_mode
                            else english if get_language() == 'en' else chinese)
            button.tooltip = tr(tooltip)
            if action not in managed:
                continue
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
        return super()._update_panel_hover(offset_y)

    def _fire_actions_lines(self, state):
        # The shared renderer owns source rows and details; do not append a
        # second source list after the controls.
        return super()._fire_actions_lines(state)

    def _sidebar_detail_entries(self):
        if self.panel_mode == 'self_stats':
            return getattr(self, '_sidebar_stat_entries', [])
        state = self.session.state
        entries = []
        from ..symbols import entity_glyph, map_symbol
        mode = self._symbol_mode()

        def entity_icon(entity):
            # 与地图同一口径：优先用该异象的专属图标，缺图才退回实例字形。
            icon = map_symbol(getattr(entity, 'catalog_id', ''), mode)
            return icon if icon and icon.strip() != '??' else entity_glyph(entity.glyph, mode)

        for entity in state.enemies:
            if (entity.integrity > 0 and entity.relation in ('失控意识', '稳定意识')
                    and state.is_visible(entity.x, entity.y)):
                entries.append(dict(key='entity:' + str(entity.id), name=state.observed_entity_label(entity),
                                    icon=entity_icon(entity), color='yellow' if entity.relation == '稳定意识' else 'red',
                                    relation=entity.relation, alert=entity.alert_state,
                                    summary=tr(entity.relation) + ' · ' + tr(entity.alert_state),
                                    target=(entity.x, entity.y)))
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
            terse_mode = terse.enabled(self.config)
            english = get_language() == 'en'
            # 数值页分类在英文普通模式下也用固定代号；打开左侧「详查」时
            # 仍是完整的分类名（那个界面不经过右栏压缩）。
            category_codes = {
                'action': 'ACT', 'offense': 'ATK', 'perception': 'PER',
                'recovery': 'REC', 'ability': 'ABL', 'environment': 'ENV',
                'overview': 'OVR', 'sources': 'SRC',
            }
            def stat_label(value: str) -> str:
                # 少字模式：数值页的条目名/分类名换成英文缩写（无图标时）；
                # 英文普通模式：长单词在右栏先缩，左侧详查仍显示完整词。
                if terse_mode:
                    return terse.field_abbrev(str(value))
                if english:
                    return terse.compact_english_string(str(value))
                return str(value)
            def stat_value(value) -> str:
                value = str(value)
                if not terse_mode:
                    return value
                import re
                for source, target in (('回合/次', 'T/ACT'), ('回合/格', 'T/TL'),
                                       ('点/回合', 'PT/T'), ('回合', 'T'),
                                       ('点', 'PT'), ('格', 'TL'), ('倍', 'x')):
                    value = re.sub(r'(?<=\d)\s*' + re.escape(source), ' ' + target, value)
                return value
            entries = []
            for category, category_rows in data['sections'].items():
                if category in ('overview', 'sources'):
                    continue
                category_label = (category_codes.get(category, labels[category])
                                  if english or terse_mode else labels[category])
                for row in category_rows:
                    entries.append(dict(row, key='stat:' + category + ':' + row['key'], category=category_label))
            self._sidebar_stat_entries = entries
            add(Text(stat_label(tr('数值与来源')), style='bold ' + C['heading']))
            previous = None
            pending = None  # (index, pair) 左格等待配对的键值行（2026-10-24 D 两列化）
            def flush_pending():
                nonlocal pending
                if pending is not None:
                    for grid_row in kv_grid([pending[1]], width):
                        add(grid_row, pending[0])
                    pending = None
            for index, row in enumerate(entries):
                if row['category'] != previous:
                    flush_pending()
                    add(Text(stat_label(row['category']), style=C['condition']))
                    previous = row['category']
                selected = index == self.panel_selection
                details_on = (self._details_visible() if hasattr(self, '_details_visible')
                              else self.details_expanded)
                expanded = details_on or self.expanded_key == row['key']
                pair = (stat_label(row['label']), stat_value(row['value']), stat_color(row.get('stat_id', ''), state), selected)
                if expanded:
                    # 展开项：键值行落左格，基础值/来源/notes 等说明段落仍整行。
                    flush_pending()
                    for grid_row in kv_grid([pair], width):
                        add(grid_row, index)
                    if row['base'] is not None:
                        add(Text('  ' + stat_label(tr('基础值')) + ':' + str(row['base']), style=C['count']), index)
                    for source in row['sources']:
                        add(Text('  ' + stat_label(tr('来源')) + ':' + str(source), style=C['grammar']), index)
                    for note in row['notes']:
                        add(Text('  ' + str(note), style=C['muted']), index)
                elif pending is None:
                    pending = (index, pair)
                else:
                    # 一行两格：命中映射登记选中项所在格（否则左格），
                    # 点击/激活仍指向一个真实条目。
                    for grid_row in kv_grid([pending[1], pair], width):
                        add(grid_row, index if selected else pending[0])
                    pending = None
            flush_pending()
        else:
            # 环境单页（2026-10-24 深化）：左右分块——左块异象清单（旧观测界面
            # 口径，个体不合并），右块视野内环境概述；中间细竖线，两块用同族
            # 近似的不同纸色（paper_zones.SIBLING_ZONES）。与上方 #hover-info
            # 完全重复的「当前对象」叙述整段删除（玩家 2026-10-24 反馈）。
            from .panels import two_zone_row, zone_strip
            from .paper_zones import ZONE_ENV_ENTITIES, ZONE_ENV_SURVEY
            left_w = max(14, (width - 1) // 2)
            right_w = width - 1 - left_w
            left_lines: list[Text] = []
            left_rows: list[int] = []

            def add_left(text: Text, index: int = -1) -> None:
                for line in text.wrap(_CONSOLE, left_w, overflow='fold'):
                    left_lines.append(line)
                    left_rows.append(index)

            entries = self._sidebar_detail_entries()
            terse_mode = terse.enabled(self.config)
            english = get_language() == 'en'
            def env_title(key: str) -> str:
                if english and not terse_mode:
                    return terse.english_label(key)
                return tr(key)
            if not terse_mode:
                hostile_count = sum(entry['color'] == 'red' for entry in entries)
                add_left(zone_strip(env_title('异象') + f' {hostile_count} · ' + env_title('稳定意识') + f' {len(entries) - hostile_count}', left_w, color=C['heading']))
            if not entries:
                add_left(Text('NO OBJ' if terse_mode else tr('视野中没有可列出的对象。'), style=C['muted']))
            for index, entry in enumerate(entries):
                x, y = entry['target']
                dx, dy = x - state.player.x, y - state.player.y
                selected = index == self.panel_selection
                if terse_mode:
                    # 少字模式：生物条目只留「选中光标 + 图像 + 方向箭头」，不显示
                    # 名称由图标表达；关系与警戒状态仍用短码保留在坐标旁。
                    arrow = (('←' if dx < 0 else '→' if dx > 0 else '')
                             + ('↑' if dy < 0 else '↓' if dy > 0 else '')) or '·'
                    head = Text(('▶ ' if selected else '  '), style=C['identity'])
                    head.append(entry.get('icon') or '  ', style=entry['color'])
                    head.append(arrow, style=entry['color'] + (' bold underline' if selected else ''))
                    add_left(head, index)
                    relation = 'CALM' if entry['relation'] == '稳定意识' else 'HST'
                    alert = {'未察觉': 'UNA', '警戒': 'ALT', '追踪': 'CHS'}.get(
                        entry['alert'], terse.abbrev(entry['alert']))
                    add_left(Text(f'  {relation} {alert} ({x},{y})', style=C['muted']), index)
                    continue
                direction = (('西' if dx < 0 else '东') if dx else '') + (('北' if dy < 0 else '南') if dy else '')
                direction = tr(direction or '脚下')
                name_text = direction + ' · ' + entry['name']
                summary_text = '  ' + entry['summary'] + f' ({x},{y})'
                if english and not terse_mode:
                    name_text = terse.compact_english_string(name_text)
                    summary_text = terse.compact_english_string(summary_text)
                head = Text(('▶ ' if selected else '  '), style=C['identity'])
                head.append(entry.get('icon') or '  ', style=entry['color'])
                head.append(name_text,
                            style=entry['color'] + (' bold underline' if selected else ''))
                add_left(head, index)
                add_left(Text(summary_text, style=C['muted']), index)
            right_lines = self._environment_survey_lines(state, right_w, terse_mode=terse_mode)
            # 左右行数取齐：短的一侧用空行补底色；行命中映射只认左块条目
            # （右块是统计文本，不可选；同格两列的点击按 kv_grid 先例落左格条目）。
            for row in range(max(len(left_lines), len(right_lines), self.query_one('#panel').content_size.height)):
                left = left_lines[row] if row < len(left_lines) else Text()
                right = right_lines[row] if row < len(right_lines) else Text()
                add(two_zone_row(left, right, ZONE_ENV_ENTITIES, ZONE_ENV_SURVEY, left_w, right_w),
                    left_rows[row] if row < len(left_rows) else -1)
        viewport = max(1, self.query_one('#panel').content_size.height)
        self.panel_scroll = min(self.panel_scroll, max(0, len(lines) - viewport))
        self._sidebar_overview_rows = rows
        self._sidebar_overview_line_count = len(lines)
        self._panel_rows = rows[self.panel_scroll:self.panel_scroll + viewport]
        return Text('\n').join(lines[self.panel_scroll:self.panel_scroll + viewport])


    def _environment_survey_lines(self, state, width: int, *,
                                  terse_mode: bool = False) -> list[Text]:
        """环境页右块：视野内统计概述（2026-10-24 玩家定稿的口径）。

        墙体固体/液体/气体/植物各一条统计行 + 一条纯名称行（只列种类名，
        不带介绍）；均值精确到 2 位小数；末尾是战斗相关的「其他信息」——
        视觉遮蔽（遮蔽强度达标的气体 + 挡视线的高丛，口径同 vision.sight）、
        听觉盲区（以玩家当前位置与当前脚步声径做声传播，视野内听不到的格数）、
        火焰/可燃气/通电。只统计**可见格**，不泄露未知地形与尚未识别内容。
        """
        from ..core.acoustics import propagate
        from ..core.sound_preview import footstep_preview
        from ..materials.gases import gas_def
        from ..materials.liquids import liquid_def
        from ..materials.plants import plant_def_for
        from ..materials.walls import wall_def
        from ..symbols import symbol

        mode = self._symbol_mode()
        terse_mode = bool(terse_mode)
        out: list[Text] = []

        # 少字模式：字段名走 terse 缩写；英文普通模式：长单词在右栏先缩；
        # 中文普通模式逐字返回 tr() 原文。完整英文在左侧详情/全屏界面。
        english_language = get_language() == 'en'
        english = english_language and not terse_mode

        def label(key: str) -> str:
            if terse_mode:
                return tr(terse.field_abbrev(key))
            value = tr(key)
            return terse.compact_english_string(value) if english else value

        def word(key: str) -> str:
            return label(key)

        def emit(text: Text) -> None:
            from rich.style import Style
            from .panels import paper_pad
            from .paper_zones import ZONE_STRIP
            heading = Style.parse(text.style).bold if isinstance(text.style, str) else text.style.bold
            for line in text.wrap(_CONSOLE, width, overflow='fold'):
                if heading:
                    line.stylize('bold underline')
                    line = paper_pad(line, ZONE_STRIP, width)
                out.append(line)

        def stat_line(label: str, body: str, color: str) -> None:
            if english:
                body = terse.compact_english_string(body)
            emit(Text.assemble((label, "bold " + color), (body, color)))

        def name_row(pairs, color) -> None:
            """每种材料前用它的图像代替原来的点号；同类只列一次。

            少字模式只画图标 + 颜色，不再 append 材料名（地形只留符号）。
            """
            if not pairs:
                return
            line = Text('  ')
            for index, (name, (icon, icon_color)) in enumerate(pairs):
                if index:
                    line.append('  ')
                line.append(icon or '  ', style=icon_color)
                if not terse_mode:
                    shown = tr(name)
                    if english:
                        shown = terse.compact_english_string(shown)
                    line.append(shown, style=color)
            emit(line)

        visible = [(x, y) for y in range(state.height) for x in range(state.width)
                   if state.is_visible(x, y)]
        cells = [state.cell(x, y) for x, y in visible]
        if terse_mode:
            emit(Text(f'VIS {len(cells)} TL', style='bold ' + C['heading']))
        else:
            # 少字模式隐藏右块标题；英文普通模式标题先缩，避免标题被截断。
            if english:
                title = f"{terse.english_label('环境概述')} ({len(cells)}T)"
            else:
                title = tr('环境概述') + tr('（视野 {n} 格）', n=len(cells))
            emit(Text(title, style='bold ' + C['heading']))

        solids = [cell for cell in cells if cell.solid]
        unit = 'TL' if terse_mode else tr('格')
        stat_line(label('墙体'), f' {len(solids)} {unit} · {word("总耐久")} {sum(c.integrity for c in solids)}',
                  C['hardness'])
        wall_pairs = {}
        for cell in solids:
            if cell.wall_kind:
                definition = wall_def(cell.wall_kind)
                wall_pairs.setdefault(definition.name,
                                      (symbol(getattr(definition, 'symbol_key', None) or 'wall', mode), definition.color))
        name_row(list(wall_pairs.items()), C['hardness'])

        liquids = [cell for cell in cells if cell.liquid > 0]
        stat_line(label('液体'), f' {len(liquids)} {unit} · {word("总液量")} {sum(c.liquid for c in liquids)}',
                  C['volume'])
        liquid_pairs = {}
        for cell in liquids:
            if cell.liquid_kind:
                liquid_pairs.setdefault(liquid_def(cell.liquid_kind).name,
                                       (symbol('liquid.medium', mode), liquid_def(cell.liquid_kind).color))
        name_row(list(liquid_pairs.items()), C['volume'])

        gases = [cell for cell in cells if cell.gas > 0]
        stat_line(label('气体'), f' {len(gases)} {unit} · {word("总气量")} {sum(c.gas for c in gases)}',
                  C['concentration'])
        gas_pairs = {}
        for cell in gases:
            if cell.gas_kind:
                definition = gas_def(cell.gas_kind)
                gas_pairs.setdefault(definition.name,
                                     (symbol(getattr(definition, 'symbol_key', None) or 'gas.faint', mode), definition.color))
        name_row(list(gas_pairs.items()), C['concentration'])

        plants = [cell for cell in cells if cell.plant]
        stat_line(label('植物'), f' {len(plants)} {"PLT" if terse_mode else tr("株")}', C['effect'])
        plant_pairs = {}
        for cell in plants:
            definition = plant_def_for(cell.plant)
            plant_pairs.setdefault(definition.name,
                                   (symbol(getattr(definition, 'key', None) or 'plant', mode), definition.color))
        name_row(list(plant_pairs.items()), C['effect'])

        if solids:
            def mean(pick) -> str:
                return f'{sum(pick(c) for c in solids) / len(solids):.2f}'
            stat_line(label('均值'), f' {word("耐久")} {mean(lambda c: c.integrity)}'
                                 f' · {word("厚度")} {mean(lambda c: c.thickness)}'
                                 f' · {word("高度")} {mean(lambda c: c.height)}', C['count'])
        else:
            emit(Text(tr('视野内没有墙体固体。'), style=C['muted']))

        def gas_obscures(cell) -> bool:
            blocked, multiplier = state._gas_sight_effect(cell)
            return blocked or multiplier < 1.0

        obscured = sum(1 for cell in cells
                       if (cell.gas and gas_obscures(cell))
                       or (cell.plant and plant_def_for(cell.plant).height >= 2))
        paren_l, paren_r = ('(', ')') if english_language else ('（', '）')
        stat_line(label('视觉遮蔽'),
                  f' {obscured} {unit}{paren_l}{"GAS/COVER" if terse_mode else tr("遮蔽气/高丛")}{paren_r}',
                  C['condition'])
        step = footstep_preview(state)
        if step.get('silent'):
            audible = {(state.player.x, state.player.y)}
            probe = 'SILENT' if terse_mode else tr('静步')
        else:
            radius = int(step.get('radius') or 0)
            audible = (propagate(state, state.player.x, state.player.y, radius)
                       if radius > 0 else {(state.player.x, state.player.y)})
            probe = f'{"RNG" if terse_mode else tr("声径")} {radius}'
        others = [(x, y) for x, y in visible if (x, y) != (state.player.x, state.player.y)]
        blind = sum(1 for point in others if point not in audible)
        stat_line(label('听觉盲区'),
                  f' {blind}/{len(others)} {unit}{paren_l}{probe}{paren_r}',
                  C['risk'])
        flames = sum(1 for cell in cells if cell.flame > 0)
        flammable_gas = sum(1 for cell in gases if gas_def(cell.gas_kind).flammable)
        wired = sum(1 for cell in cells if cell.wire)
        emit(Text(''))
        emit(Text(label('环境风险'), style='bold ' + C['heading']))
        stat_line(label('火焰'), f' {flames} {unit} · {"PWR" if terse_mode else tr("通电")} {wired} {unit}', C['area'])
        fuel = sum(1 for cell in liquids if liquid_def(cell.liquid_kind).flammable)
        stat_line(label('可燃气'), f' {flammable_gas} {unit} · {word("可燃液体")} {fuel} {unit}', C['risk'])
        contact = sum(1 for cell in liquids if liquid_def(cell.liquid_kind).contact_effect)
        inhaled = sum(1 for cell in gases if gas_def(cell.gas_kind).inhalation_effect)
        stat_line(label('接触效果'), f' {contact} {unit}', C['condition'])
        stat_line(label('吸入效果'), f' {inhaled} {unit}', C['condition'])
        events = sum(not event.resolved and state.is_visible(event.x, event.y) for event in state.events)
        drops = sum(state.is_visible(drop.x, drop.y) for drop in state.world_items)
        stat_line(label('事件'), f' {events} · {word("掉落物")} {drops}', C['count'])
        return out


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
