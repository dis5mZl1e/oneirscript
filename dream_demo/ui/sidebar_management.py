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
from .panel_fields import FIELD_COLORS as C
from .sidebar_models import item_by_id, item_facts, comparison, task_items

_CONSOLE = Console(legacy_windows=False)
_DETAIL = 'sidebar_detail'


class SidebarManagementMixin:
    @property
    def sidebar_workspace(self):
        if self.panel_mode == _DETAIL:
            return getattr(self, '_sidebar_detail_ref', {}).get('workspace', 'inventory')
        return super().sidebar_workspace

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
        self.refresh_view()
        return True

    def _ui_escape_chain(self):
        if (self.panel_mode == _DETAIL and not self._modal_menu_open() and not self.aiming
                and self.sentence_aim is None and self._active_left_overlay() is None):
            return self._sidebar_back() or super()._ui_escape_chain()
        return super()._ui_escape_chain()

    def open_sidebar_workspace(self, workspace):
        if not self._sidebar_navigation_allowed():
            return False
        if self.panel_mode == _DETAIL:
            group = self.sidebar_workspace
            self._sidebar_back_stack = []
            route = {'inventory':'inventory', 'equipment':'build_overview', 'portents':'self_overview', 'tasks':'tasks', 'actions':'world'}[group]
            self.panel_mode = route
            self._restore_sidebar_position()
            if group == workspace:
                self.refresh_view()
                return True
        self._sidebar_back_stack = []
        return super().open_sidebar_workspace(workspace)

    def open_sidebar_route(self, key):
        if self._sidebar_navigation_allowed():
            self._sidebar_back_stack = []
        return super().open_sidebar_route(key)

    def _sync_sidebar_owner(self):
        state = self.session.state
        context = (id(state), state.depth, state.realm_id, state.realm_depth)
        previous = getattr(self, '_management_owner', context)
        if previous != context:
            self._sidebar_back_stack = []
            self._sidebar_live_identity = None
            if self.panel_mode == _DETAIL:
                self.panel_mode = 'world'
            self._sidebar_detail_ref = {}
        self._management_owner = context
        return super()._sync_sidebar_owner()

    def _sidebar_before_refresh(self):
        self._sync_sidebar_owner()
        old = getattr(self, '_sidebar_live_identity', None)
        token = (self.panel_mode, self._panel_subpage_id())
        if old and old[:2] == token and old[2] == self.panel_selection:
            candidates = self._sidebar_inventory_choices()
            match = next((ordinal for ordinal, identity in candidates if identity == old[3]), None)
            if match is not None:
                self.panel_selection = match
            elif candidates:
                self.panel_selection = candidates[min(max(0, self.panel_selection), len(candidates)-1)][0]
    def _sidebar_after_refresh(self):
        token = (self.panel_mode, self._panel_subpage_id())
        candidates = dict(self._sidebar_inventory_choices())
        self._sidebar_live_identity = (*token, self.panel_selection, candidates.get(self.panel_selection)) if candidates else None

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
        base, base_rows = super()._construct_actions_lines(state)
        ids = [key for key in state.abilities if key in ABILITY_DEFINITIONS]
        context = len(self._actions_for(self.context_menu_target)) if self.context_menu_target else 0
        visible = self._sidebar_ability_indices()
        width = max(8, self.query_one('#panel').content_size.width)
        lines, rows = [], []
        def add(text, row=-1):
            for part in text.wrap(_CONSOLE, width, overflow='fold'):
                lines.append(part); rows.append(row)
        add(Text(tr('—— 主动构想 ——'), style='bold '+C['word']))
        add(Text(tr('结果：{n}', n=len(visible)), style=C['count']))
        pins = self.sidebar_preferences()['favorites']
        for ordinal in visible:
            key = ids[ordinal]; definition = ABILITY_DEFINITIONS[key]; row = context + ordinal
            focused = self.panel_selection == row
            line = Text(('▶ ' if focused else '  ')+('★ ' if key in pins else '')+tr(definition['name']),
                        style=C['word']+(' bold underline' if focused else ''))
            line.append('  '+str(state._scaled_ability_cost(int(definition['cost'])))+' '+tr('想象力'), style=C['cost'])
            cooldown = state.ability_cooldowns.get(key, 0)
            if cooldown: line.append(' · '+tr('冷却 {n} 回合', n=cooldown), style=C['cooldown'])
            add(line, row)
            if focused or self._entry_expanded('ability:'+key):
                add(Text('  '+tr(definition['description']), style=C['muted']), row)
        if not visible:
            add(Text(tr('没有匹配的构想；可清除搜索或切换全部。'), style=C['muted']))
        last_kind = None; keep = False
        for text, row in zip(base, base_rows):
            if row >= 0:
                keep = not (context <= row < context + len(ids))
                if keep:
                    kind = 'context' if row < context else 'identity' if row < context+len(ids)+len(state.identity_abilities()) else 'sentence'
                    if kind != last_kind:
                        add(Text(tr({'context':'—— 目标操作 ——', 'identity':'—— 身份能力 ——', 'sentence':'—— 装备语句 ——'}[kind]), style=C['identity']))
                        last_kind = kind
            if keep:
                add(text, row)
        self._sidebar_ability_visible_rows = list(dict.fromkeys(row for row in rows if row >= 0))
        if self._sidebar_ability_visible_rows and self.panel_selection not in self._sidebar_ability_visible_rows:
            self.panel_selection = self._sidebar_ability_visible_rows[0]
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
            self.refresh_view(); return
        if self.panel_mode == 'actions' and self._panel_subpage_id() == 'constructs':
            self._construct_actions_lines(self.session.state)
            rows = self._sidebar_ability_visible_rows
            if rows:
                pos = rows.index(self.panel_selection) if self.panel_selection in rows else -1
                self.panel_selection = rows[(pos+delta) % len(rows)]
            self._panel_enter_mode = self.panel_mode
            self._follow_actions_selection(); self.refresh_view(); return
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
        self.refresh_view()

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
        def add(text, color='text'):
            body.append((Text(str(text), style=C[color]), -1))
        def action(label, command, *args):
            key = repr((command, *args))
            actions.append(dict(key=key, command=command, args=args))
            body.append((Text(label, style=C['condition']), len(actions)-1))
        add(tr('详情与操作'), 'heading')
        if kind == 'item':
            item = item_by_id(state, identity)
            facts = item_facts(state, identity)
            if facts is None:
                add(tr('这件物品已经不在行囊中。'), 'risk'); return body, actions
            add(facts['name']+' ×'+str(facts['quantity']), 'word')
            add(facts['category'], 'category'); add(facts['description'])
            for label, key in (('强度','power'), ('穿透','penetration'), ('推力','push'), ('爆炸半径','radius')):
                if facts[key]: add(tr(label)+' '+str(facts[key]), 'count')
            if facts['magazine'] is not None: add(tr('弹匣')+f" {facts['magazine']}/{facts['capacity']}", 'count')
            for name, amount in facts['contents'].items(): add(tr(name)+' '+str(amount), 'volume')
            compared = comparison(state, identity)
            if item.slot:
                add(tr('对比'), 'heading'); add(compared['note'], 'muted')
                for peer in compared['peers']:
                    other = item_facts(state, peer)
                    if other:
                        add(tr('当前配置')+' · '+other['name'], 'word'); add(other['description'], 'muted')
                        action(tr('查看')+' · '+other['name'], 'link', 'item', peer, 'inventory')
            if item.category == '记忆碎片':
                action(tr('装入记忆槽 · 1 回合'), 'equip_memory', identity)
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
            action(tr('取下至行囊 · 1 回合'), 'unequip_memory', identity)
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
        if command == 'link': self.open_sidebar_detail(*args)
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
        if command not in {entry[2] for entry in self._item_menu_actions(item)}: return False
        old_target = self.item_menu_target
        self.item_menu_target = identity
        self.activate_item_menu(command)
        if self.item_menu_target == identity: self.item_menu_target = old_target
        return True

    def _refresh_sidebar_tools(self):
        from .sidebar_workspaces import OVERVIEW_MODES
        mode = self.panel_mode
        cache_key = (mode, self._panel_subpage_id(), get_language(), self.layer_observation is not None,
                     bool(self.inventory_query), bool(getattr(self,'_sidebar_ability_query','')),
                     getattr(self,'_sidebar_only_favorites',False), getattr(self,'_sidebar_portent_filter','全部'),
                     tuple(self.sidebar_preferences()['collapsed']))
        if getattr(self,'_management_tools_key',None) == cache_key:
            return
        self._management_tools_key = cache_key
        construct = mode == 'actions' and self._panel_subpage_id() == 'constructs'
        memory = mode == 'equipment' and self._panel_subpage_id() == 'memory'
        tools = set()
        if mode == _DETAIL: tools = {'back'}
        elif mode == 'inventory': tools = {'search','filter','sort','expand','menu'} | ({'clear'} if self.inventory_query else set())
        elif construct: tools = {'search','filter','pin','expand'} | ({'clear'} if getattr(self,'_sidebar_ability_query','') else set())
        elif mode == 'portents': tools = {'filter','expand'}
        elif mode == 'tasks': tools = {'related'}
        elif mode == 'self_stats': tools = {'menu','expand'}
        elif memory: tools = {'menu'}
        elif mode in OVERVIEW_MODES: tools = {'fold'}
        elif mode in ('equipment','insights','catalog','actions'): tools = {'expand','menu'}
        if self.layer_observation is not None: tools = set()
        labels = {'search':('搜','Find'),'filter':('类','Type'),'sort':('序','Sort'),'expand':('详情','More'),'menu':('操作','Use'),'clear':('×','×'),'pin':('固定','Pin'),'back':('返回','Back'),'related':('物品','Items'),'fold':('折叠','Fold')}
        for key in ('search','filter','sort','expand','menu','clear','pin','back','related','fold'):
            button = self.query_one('#sidebar-'+key)
            button.display = key in tools
            if key in labels: button.label = labels[key][1 if get_language() == 'en' else 0]
            button.tooltip = tr({'pin':'固定／取消固定当前构想', 'back':'返回原条目', 'related':'查看任务相关物品', 'fold':'展开／折叠总览内容'}.get(key, {'search':'搜索','filter':'筛选','sort':'排序','expand':'展开','menu':'详情与操作','clear':'清除搜索'}.get(key,key)))
        self.query_one('#sidebar-tools').display = bool(tools)
        if mode == 'portents':
            self.query_one('#sidebar-filter').label = tr(getattr(self, '_sidebar_portent_filter', '全部'))
        elif construct:
            self.query_one('#sidebar-filter').label = tr('固定' if getattr(self,'_sidebar_only_favorites',False) else '全部')

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
        super().close_board_editor(committed=committed)
        if snapshot is not None:
            self._sidebar_back_stack = [*getattr(self,'_sidebar_back_stack',[]), snapshot][-8:]
            self._sidebar_back()
            self._management_board_return = None
