"""Temporary, read-only layer observation. No GameState or config fields."""
from dataclasses import dataclass

from rich.cells import cell_len
from rich.text import Text
from textual.widgets import Static

from ..core.map_scene import OBSERVE_LAYERS, cell_layer_names
from ..i18n import tr
from .elevation import elevation_legend

LABELS = {'composite': '综合', 'floor': '地板', 'low': '低层', 'middle': '中层',
          'high': '高层', 'liquid': '液体', 'gas': '气体', 'elevation': '地势',
          'terrain': '地形', 'sound': '声音线索'}
# 面板热区：1—N 是观察层，第 N+1 行是「返回地图」。加层时只改这里。
EXIT_ROW = len(OBSERVE_LAYERS) + 1


def accessory_color_samples(cell) -> list[tuple[str, str]]:
    """Material colour swatches for the observation panel (original colours)."""
    from ..materials import gas_def, liquid_def
    samples: list[tuple[str, str]] = []
    if cell.liquid:
        samples.append((cell.liquid[0], liquid_def(cell.liquid[0]).color))
    if cell.gas:
        samples.append((cell.gas[0], gas_def(cell.gas[0]).color))
    if cell.flame:
        samples.append(('火焰', '#ff8a3d'))
    return samples


def accessory_layer_lines(cell) -> list[str]:
    """Right-column groups: objects/tasks, gas, liquid, terrain + extra count."""
    names = cell_layer_names(cell)
    if not names:
        return []
    objects = []
    if cell.events:
        objects.append(f"事件×{len(cell.events)}" if len(cell.events) > 1 else "事件")
    if cell.site:
        objects.append("地点")
    if cell.telegraph:
        objects.append("预警")
    if cell.danger:
        objects.append("危险")
    if cell.actors:
        objects.append(f"生物×{len(cell.actors)}" if len(cell.actors) > 1 else "生物")
    if cell.items:
        objects.append(f"物品×{len(cell.items)}" if len(cell.items) > 1 else "物品")
    if cell.flame:
        objects.append("火焰")
    if cell.plant:
        objects.append("植物")
    lines = [tr('同格内容')]
    if objects:
        lines.append(tr('对象与任务')+'：'+'、'.join(tr(name) for name in objects))
    if cell.gas:
        lines.append(tr('气体')+'：'+tr(cell.gas[0]))
    if cell.liquid:
        lines.append(tr('液体')+'：'+tr(cell.liquid[0]))
    if cell.terrain:
        terrain = cell.terrain.wall_kind or cell.terrain.aggregate_variant or cell.terrain.floor
        lines.append(tr('地形')+'：'+tr(terrain))
    if len(names) > 1:
        lines.append(tr('另有 {count} 层', count=len(names)-1))
    return lines


@dataclass
class LayerObservation:
    context: tuple
    cursor: tuple[int, int]
    layer: str
    previous: dict
    viewport: tuple
    zoom: float
    info_scroll: int = 0
    legend_open: bool = False


class LayerStrip(Static):
    """Left, one-line observation selector; never occupies the right column."""

    DEFAULT_CSS = """
    LayerStrip {
        display: none;
        dock: top;
        width: 100%;
        height: 1;
        padding: 0;
        background: #292930;
        color: #c8d8d8;
        text-style: bold;
    }
    """

    def on_mouse_down(self, event) -> None:
        if self.id == 'layer-status':
            self.app._layer_status_mouse(event)
        else:
            self.app._layer_strip_mouse(event)
        event.prevent_default()


class LayerStatus(LayerStrip):
    DEFAULT_CSS = 'LayerStatus { dock: bottom; height: 2; }'


class LayerObservationMixin:
    layer_observation: LayerObservation | None = None
    _layer_strip_hits: tuple = ()

    def check_action(self, action, parameters):
        if self.layer_observation is not None and action not in ('cycle_map_observe','elevation_observe','cancel_ui','image_preview'):
            return False
        return super().check_action(action, parameters)

    def _layer_context(self):
        state = self.session.state
        return id(state), state.layer_key()

    def _enter_layer_observation(self):
        if (self.home_mode or self.session.state.run_over or self._floor_transition is not None
                or self.panel_mode.startswith('pause')
                or self.panel_mode == 'board_editor' or getattr(self,'controls_help_open',False)
                or getattr(self,'qol_confirmation',None)):
            return
        try:
            map_view = self.query_one('#map')
        except Exception:
            return
        fields = ('observe_mode', 'observe_cursor', 'hover_cell', 'panel_mode',
                  'panel_selection', 'panel_scroll', 'cell_detail_target', 'item_menu_target', 'anomaly_detail_target',
                  'cell_detail_return', 'detail_cursor', 'detail_scroll')
        previous = {name: getattr(self, name, None) for name in fields}
        previous['_focused_widget'] = self.focused
        panel = self.query_one('#panel')
        previous['_widget_scroll'] = (panel.scroll_x,panel.scroll_y)
        previous['_panel_renderable'] = panel.renderable.copy()
        previous['_world_hover_target'] = self.session.state.hover_target
        previous['_disabled_controls'] = {name:self.query_one('#'+name).disabled
            for name in ('status','panel-tabs','equipment-sentence')}
        for name in previous['_disabled_controls']:
            self.query_one('#'+name).disabled=True
        editor = self._active_tamper_editor()
        cursor = (editor.preview_cursor if editor and editor.map_preview else
                  self.sentence_aim['cursor'] if self.sentence_aim else
                  (getattr(self, '_aim_free_cursor', None) or
                   getattr(self, '_aim_assist_pos', None)) if self.aiming else
                  self.observe_cursor if self.observe_mode else None)
        cursor = cursor or (self.session.state.player.x, self.session.state.player.y)
        initial = str(self.config.get('map_observe') or 'composite')
        if initial not in OBSERVE_LAYERS:
            initial = 'composite'
        self.layer_observation = LayerObservation(self._layer_context(), cursor,
                                                   initial, previous,
                                                   map_view.viewport, map_view.zoom)
        self._clear_held()
        self.set_focus(map_view)
        self.observe_mode = True
        self.observe_cursor = self.hover_cell = cursor
        self.cell_detail_target = None
        self.item_menu_target = self.anomaly_detail_target = None
        self.cell_detail_return = None
        self.refresh_view()

    def _exit_layer_observation(self, *, restore=True):
        view = self.layer_observation
        self.layer_observation = None
        if view is None:
            return
        self._layer_return_pending = None
        if (restore and view.context == self._layer_context() and not self.home_mode
                and self.resolved_map_display()[0] == 'image'):
            map_view = self.query_one('#map')
            # Retain the observation until an actual image packet succeeds.
            self._layer_return_pending = (view, map_view.viewport, map_view.zoom)
        for name,value in view.previous.get('_disabled_controls',{}).items():
            self.query_one('#'+name).disabled=value
        if restore and view.context == self._layer_context() and not self.home_mode:
            for name, value in view.previous.items():
                if name.startswith('_') and name != '_world_hover_target':
                    continue
                if name == '_world_hover_target':
                    self.session.state.hover_target = value
                else:
                    setattr(self, name, value)
            map_view = self.query_one('#map')
            map_view.viewport, map_view.zoom = view.viewport, view.zoom
        else:
            self.observe_mode = False
            self.observe_cursor = self.hover_cell = self.cell_detail_target = None
            self.item_menu_target = self.anomaly_detail_target = self.cell_detail_return = None
        self.query_one('#map-overlay').display = False
        try:
            self.query_one('#layer-strip').display = False
            self.query_one('#layer-status').display = False
        except Exception:
            pass
        self.refresh_view()
        if restore and view.context == self._layer_context() and not self.home_mode:
            self.call_after_refresh(lambda v=view: self._restore_layer_viewport(v))
            focused = view.previous.get('_focused_widget')
            if focused is not None and focused.is_mounted and not focused.disabled:
                self.set_focus(focused)
            panel = self.query_one('#panel')
            sx,sy = view.previous.get('_widget_scroll',(0,0))
            self.call_after_refresh(lambda:panel.scroll_to(x=sx,y=sy,animate=False))

    def _restore_layer_viewport(self, view, viewport=None, zoom=None):
        """Restore the exact viewport after the bottom status row leaves layout."""
        if self.layer_observation is not None and self.layer_observation is not view:
            return
        try:
            map_view = self.query_one('#map')
        except Exception:
            return
        map_view.viewport = tuple(viewport if viewport is not None else view.viewport)
        map_view.zoom = zoom if zoom is not None else view.zoom
        map_view._frame_key = None

    def _recover_layer_observation(self):
        pending = getattr(self, '_layer_return_pending', None)
        self._layer_return_pending = None
        if pending is None:
            return False
        view, viewport, zoom = pending
        if (view.context != self._layer_context() or self.home_mode
                or self.session.state.run_over):
            return False
        self._image_restore_fallback = True
        self._image_output_error = ''
        self.layer_observation = view
        for name in view.previous.get('_disabled_controls', {}):
            self.query_one('#'+name).disabled = True
        self.observe_mode = True
        self.observe_cursor = self.hover_cell = view.cursor
        self.cell_detail_target = None
        map_view = self.query_one('#map')
        map_view.viewport, map_view.zoom = viewport, zoom
        map_view._frame_key = None
        self.set_focus(map_view)
        self.refresh_view()
        self.call_after_refresh(lambda: self._restore_layer_viewport(view, viewport, zoom))
        return True

    def _layer_select(self, layer):
        if self.layer_observation and layer in OBSERVE_LAYERS:
            self.layer_observation.layer = layer
            self.refresh_view()

    def _layer_key(self, key):
        view = self.layer_observation
        if view is None:
            return False
        if key == 'f2':
            self.action_image_preview()
            return True
        if view.legend_open:
            if key in ('escape', 'q', 'backslash', '\\'):
                view.legend_open = False
                self._sync_layer_observation_ui()
            elif key in ('pageup','pagedown','home','end','up','down'):
                view.info_scroll = (0 if key == 'home' else 10**6 if key == 'end'
                                    else view.info_scroll + (-3 if key in ('up','pageup') else 3))
                self._update_layer_panel()
            elif key in ('tab','f3',']','right_square_bracket'):
                self._layer_select(OBSERVE_LAYERS[(OBSERVE_LAYERS.index(view.layer)+1)%len(OBSERVE_LAYERS)])
            elif key in ('shift+tab','[','left_square_bracket'):
                self._layer_select(OBSERVE_LAYERS[(OBSERVE_LAYERS.index(view.layer)-1)%len(OBSERVE_LAYERS)])
            elif key in ('enter','question_mark','?'):
                view.legend_open = False
                self.open_cell_detail(view.cursor)
                self._sync_layer_observation_ui()
            return True
        if (self.cell_detail_target is not None or self.anomaly_detail_target is not None
                or self.item_menu_target is not None):
            if key in ('escape', 'q'):
                self._layer_close_detail()
                self._sync_layer_observation_ui()
            elif key == 'enter':
                # 子详情/展开与主界面同一手感：这一次输入同样被吞掉（§16.6）。
                if self.cell_detail_target is not None:
                    self._cd_activate_row()
                self._sync_layer_observation_ui()
            elif key in ('up','down'):
                self._move_anomaly_detail(-1 if key == 'up' else 1)
            elif key in ('pageup','pagedown'):
                self._scroll_anomaly_detail(self._anomaly_detail_viewport()*(1 if key == 'pageup' else -1))
            return True
        if key in ('escape', 'q', 'v'):
            self._exit_layer_observation()
        elif key in ('f3', 'tab', 'right_square_bracket', ']'):
            self._layer_select(OBSERVE_LAYERS[(OBSERVE_LAYERS.index(view.layer)+1) % len(OBSERVE_LAYERS)])
        elif key in ('shift+tab', 'left_square_bracket', '['):
            self._layer_select(OBSERVE_LAYERS[(OBSERVE_LAYERS.index(view.layer)-1) % len(OBSERVE_LAYERS)])
        elif key in ('ctrl+up','alt+up','ctrl+down','alt+down'):
            self._zoom_map(1 if key.endswith('up') else -1)
        elif key in ('backslash', '\\'):
            view.legend_open = True
            view.info_scroll = 0
            self._sync_layer_observation_ui()
        elif key in ('enter', 'question_mark', '?'):
            self.open_cell_detail(view.cursor)
            self._sync_layer_observation_ui()
        else:
            directions = {'up': (0,-1), 'down': (0,1), 'left': (-1,0), 'right': (1,0),
                          '2': (0,1), '4': (-1,0), '6': (1,0), '8': (0,-1),
                          '1': (-1,1), '3': (1,1), '7': (-1,-1), '9': (1,-1),
                          'num2': (0,1), 'num4': (-1,0), 'num6': (1,0), 'num8': (0,-1),
                          'num1': (-1,1), 'num3': (1,1), 'num7': (-1,-1), 'num9': (1,-1),
                          'kp2': (0,1), 'kp4': (-1,0), 'kp6': (1,0), 'kp8': (0,-1),
                          'kp1': (-1,1), 'kp3': (1,1), 'kp7': (-1,-1), 'kp9': (1,-1),
                          'home': (-1,-1), 'end': (-1,1),
                          'pageup': (1,-1), 'pagedown': (1,1),
                          'k': (0,-1), 'j': (0,1), 'h': (-1,0), 'l': (1,0),
                          '8': (0,-1), '2': (0,1), '4': (-1,0), '6': (1,0),
                          'y': (-1,-1), 'u': (1,-1), 'b': (-1,1), 'n': (1,1)}
            if key in directions:
                dx, dy = directions[key]
                state = self.session.state
                self._layer_point((max(0,min(state.width-1,view.cursor[0]+dx)),
                                   max(0,min(state.height-1,view.cursor[1]+dy))))
        # Including bindings for movement, fire, waiting, save/load and side tabs.
        return True

    def _layer_close_detail(self):
        """Close exactly one observation-owned child; never the parked dialog."""
        if self.anomaly_detail_target is not None:
            self.close_anomaly_detail()
        elif self.item_menu_target is not None:
            self.close_item_menu()
        elif self.cell_detail_target is not None:
            self.close_cell_detail()
        elif self.layer_observation is not None:
            self.layer_observation.legend_open = False
        self._sync_layer_observation_ui()

    def _layer_point(self, pos):
        if self.layer_observation and pos is not None:
            self.layer_observation.cursor = pos
            self.observe_cursor = self.hover_cell = pos
            # Rebuild only when the cursor crosses a viewport edge.
            map_view = self.query_one('#map')
            viewport = map_view.viewport_for(self.session.state)
            if viewport != map_view.viewport:
                self.refresh_view()
            else:
                self._refresh_cursor_only()
                self._sync_layer_observation_ui()

    def _layer_panel_text(self):
        view = self.layer_observation
        text = Text(tr('分层观察')+'\n', style='bold #b5a0df')
        text.append(tr(LABELS[view.layer])+' · '+tr('关闭图例')+' · Esc\n', style='#e1bd74')
        text.append(tr('Tab / F3 切层；方向键观察；Enter 详情')+'\n', style='#a8b5bd')
        text.append(tr('PgUp/PgDn 滚动信息；Home/End 到首尾')+'\n',style='#8f9aa8')
        text.append(f'({view.cursor[0]}, {view.cursor[1]})\n')
        from .observation_marks import EDGE_LABELS, MARKS, marks_for
        text.append(tr('图像：边缘标记；字符：加粗下划线；当前危险见下方状态。')+'\n', style='#8f9aa8')
        for mark in MARKS.values():
            text.append(tr(mark.label)+' · '+tr(EDGE_LABELS[mark.edge])+'\n', style=mark.color)
        from ..core.map_scene import build_scene
        scene = build_scene(self.session.state, viewport=(*view.cursor, 1, 1),
                            legacy_terrain=not bool(self.session.state.map_memory_enabled))
        cell = scene.cell(*view.cursor)
        for mark in marks_for(cell) if cell is not None else ():
            text.append('! '+tr(mark.label)+'\n', style=mark.color)
        if view.layer == 'sound':
            from ..core.sound_markers import marker_legend, sound_markers
            marks = sound_markers(self.session.state, getattr(self, '_signal_clue_index', None))
            text.append(tr('声音线索')+f'：{len(marks)} · '+tr('只标发声格，不照亮周围地形')+'\n',
                        style='#e1bd74')
            for glyph, label in marker_legend(
                    ascii_mode=self._symbol_mode() == "ascii"):
                text.append(f'{glyph} {tr(label)}\n', style='#e1bd74')
            text.append('\n')
        if view.layer == 'elevation':
            from .elevation import elevation_display, elevation_source_label
            if cell is not None:
                text.append(tr('地势')+'：'+elevation_display(cell)+' · '+elevation_source_label(cell)+'\n')
            text.append(tr('固定图例（不随本层已知高低自动缩放）')+'\n', style='#8f9aa8')
            for span, name, color, glyph in elevation_legend():
                text.append(f'{glyph} {tr(name)} {span}\n', style=color)
            text.append('\n')
        if cell is None or cell.status == 'unknown':
            text.append(tr('未知区域'))
            return text
        for layer in ('high','middle','low'):
            text.append(tr(LABELS[layer])+'\n', style='bold #8bd6cf')
            entries = [o for o in cell.occupants if layer in o.layers]
            if cell.terrain and cell.terrain.solid and cell.terrain.height is not None:
                if cell.terrain.height >= {'low':1,'middle':2,'high':3}[layer]:
                    text.append('  '+tr(cell.terrain.wall_kind)+'\n')
            if layer == 'high' and cell.gas:
                text.append('  '+tr(cell.gas[0])+f' {cell.gas[1]}\n')
            if layer == 'low' and cell.liquid:
                text.append('  '+tr(cell.liquid[0])+f' {cell.liquid[1]}\n')
            for entry in entries:
                text.append('  '+tr(entry.name), style=entry.color)
                if entry.notes:
                    text.append(' · '+' / '.join(tr(n) for n in entry.notes), style='#a8b5bd')
                text.append('\n')
        if cell.terrain:
            text.append(tr(cell.terrain.wall_kind or cell.terrain.floor)+'\n')
        if cell.liquid:
            text.append(tr(cell.liquid[0])+(f' · {cell.liquid[1]}' if cell.status in ('visible','developed') else '')+'\n', style='#7ab8da')
        if cell.gas:
            text.append(tr(cell.gas[0])+f' · {cell.gas[1]}\n', style='#b7cda2')
        for line in accessory_layer_lines(cell):
            text.append(line+'\n', style='#c8b98d' if line.startswith(tr('同格内容')) else '#8f9aa8')
        samples = accessory_color_samples(cell)
        if samples:
            text.append(tr('原色')+'：', style='#8f9aa8')
            for name, color in samples:
                text.append('■ ', style=color)
                text.append(tr(name)+' ', style='#a8b5bd')
            text.append('\n')
        return text

    def _sync_layer_observation_ui(self):
        view = self.layer_observation
        if view is None:
            self.query_one('#layer-strip').display = False
            self.query_one('#layer-status').display = False
            return
        if self.home_mode or self.session.state.run_over or view.context != self._layer_context():
            self._exit_layer_observation(restore=False)
            return
        # Keep editor objects and pending dialogue; only their presentation is hidden.
        for identifier in ('tamper-overlay', 'self-pane', 'debug-panel', 'tutorial-card'):
            self.query_one('#'+identifier).display = False
        overlay = self.query_one('#map-overlay')
        detail_open = (self.cell_detail_target is not None
                       or self.anomaly_detail_target is not None
                       or self.item_menu_target is not None)
        if detail_open:
            # 格子详情 Enter 进的子详情（观测详情/物品菜单）用的是同一块覆盖面板，
            # 分层观察里不能顺手把它藏掉（docs §16.6：进入与返回同一上下文）。
            overlay.display = True
        else:
            # 2026-10-21 设计：层菜单、图例与本格详情留在左侧，不占用右栏。
            overlay.display = view.legend_open
            if view.legend_open:
                self._update_layer_panel()
        self._update_layer_strip()
        self._update_layer_status()
        panel = self.query_one('#panel')
        original = view.previous.get('_panel_renderable')
        if original is not None and panel.renderable != original:
            panel.update(original)
        map_view = self.query_one('#map')
        map_view.observe_cursor = view.cursor
        map_view.update_interaction()
        self.query_one('#map-mode-hint').display = False

    def _update_layer_strip(self):
        """One-line left selector; never writes into the right panel."""
        view = self.layer_observation
        if view is None:
            return
        strip = self.query_one('#layer-strip')
        pane = self.query_one('#map-pane')
        labels = [tr(LABELS[layer]) for layer in OBSERVE_LAYERS]
        total = sum(cell_len(label) for label in labels) + 3 * (len(labels) - 1)
        if total > max(8, pane.content_size.width - 4):
            index = OBSERVE_LAYERS.index(view.layer)
            indices = [i for i in range(index - 1, index + 2) if 0 <= i < len(OBSERVE_LAYERS)]
            labels = [tr(LABELS[OBSERVE_LAYERS[i]]) for i in indices]
            visible_layers = [OBSERVE_LAYERS[i] for i in indices]
        else:
            visible_layers = list(OBSERVE_LAYERS)
        if sum(cell_len(tr(LABELS[l])) for l in visible_layers)+3*(len(visible_layers)-1)+4 > pane.content_size.width:
            visible_layers = [view.layer]
        text = Text('‹ ', style='#e1bd74')
        hits = [(0, 2, 'previous')]
        col = 2
        for index, layer in enumerate(visible_layers):
            if index:
                text.append(' · ', style='#6f7d86')
                col += 3
            label = tr(LABELS[layer])
            start = col
            text.append(label, style='bold #8bd6cf' if layer == view.layer else '#a8b5bd')
            col += cell_len(label)
            hits.append((start, col, layer))
        self._layer_strip_hits = tuple(hits)
        text.append(' ›', style='#e1bd74')
        self._layer_strip_hits += ((col, col+2, 'next'),)
        text.truncate(max(1, pane.content_size.width), overflow='crop')
        strip.update(text)
        strip.display = True

    def _layer_strip_mouse(self, event):
        if self.layer_observation is None:
            event.stop()
            return
        if event.button != 1:
            event.stop()
            return
        x = int(event.offset.x)
        for start, end, layer in self._layer_strip_hits:
            if start <= x < end:
                if layer in ('previous','next'):
                    delta = -1 if layer == 'previous' else 1
                    layer = OBSERVE_LAYERS[(OBSERVE_LAYERS.index(self.layer_observation.layer)+delta)%len(OBSERVE_LAYERS)]
                self._layer_select(layer)
                break
        event.stop()

    def _update_layer_status(self):
        view = self.layer_observation
        status = self.query_one('#layer-status')
        width = max(1, self.query_one('#map-pane').content_size.width)
        summary = Text(f'({view.cursor[0]}, {view.cursor[1]}) · '+tr(LABELS[view.layer]), style='#a8b5bd')
        from .observation_marks import marks_for
        scene = self.query_one('#map').shared_scene
        cell = scene.cell(*view.cursor) if scene is not None else None
        for mark in marks_for(cell) if cell is not None else ():
            summary.append(' · '+tr(mark.label), style=mark.color)
        if view.layer == 'elevation':
            from .elevation import elevation_display
            scene = self.query_one('#map').shared_scene
            if scene is not None:
                cell = scene.cell(*view.cursor)
                if cell is not None:
                    summary.append(' · '+elevation_display(cell), style='#e1bd74')
        summary.truncate(width, overflow='ellipsis')
        actions = [(tr('图例')+' \\', 'legend'), (tr('详情')+' Enter', 'detail'),
                   (tr('返回地图')+' Esc', 'exit')]
        row = Text()
        hits = []
        for label, action in actions:
            if row.plain:
                row.append('  ')
            start = cell_len(row.plain)
            row.append(label, style='#e1bd74')
            hits.append((start, cell_len(row.plain), action))
        row.truncate(width, overflow='crop')
        if any(end > width for _, end, _ in hits):
            row = Text('\\  ?  Esc', style='#e1bd74')
            hits = [(0,1,'legend'),(3,4,'detail'),(6,9,'exit')]
        self._layer_status_hits = hits
        status.update(Text('\n').join((summary, row)))
        status.display = True

    def _layer_status_mouse(self, event):
        if self.layer_observation is not None and event.button == 1 and event.offset.y == 1:
            for start, end, action in getattr(self, '_layer_status_hits', ()):
                if start <= event.offset.x < end:
                    if action == 'exit':
                        self._exit_layer_observation()
                    elif action == 'detail':
                        self.layer_observation.legend_open = False
                        if (self.cell_detail_target is not None or self.anomaly_detail_target is not None
                                or self.item_menu_target is not None):
                            self._layer_close_detail()
                        else:
                            self.open_cell_detail(self.layer_observation.cursor)
                    else:
                        self.layer_observation.legend_open = not self.layer_observation.legend_open
                    self._sync_layer_observation_ui()
                    break
        event.stop()
        event.prevent_default()

    def _layer_panel_mouse(self, event, panel=None):
        if not self.layer_observation:
            return False
        if (self.cell_detail_target is not None or self.anomaly_detail_target is not None
                or self.item_menu_target is not None):
            return False
        default = '#map-overlay' if self.layer_observation is not None else '#panel'
        widget = panel or getattr(event, 'control', None) or self.query_one(default)
        if getattr(widget, 'id', None) != 'map-overlay' or not self.layer_observation.legend_open:
            # Cell details share EventPanel routing, but never its hit map.
            event.stop()
            return True
        y = int(event.offset.y)
        rows = getattr(self, '_layer_panel_hit_rows', ())
        row = rows[y] if 0 <= y < len(rows) else None
        if event.button == 1 and y == 0:
            self.layer_observation.legend_open = False
            self._sync_layer_observation_ui()
        event.stop()
        return True

    def _update_layer_panel(self):
        # 2026-10-21 设计：左栏浮层承载选择、图例与本格详情；右栏保持原内容。
        # EventPanel is a fixed-height Static, not a ScrollView: its ordinary
        # lists also paginate explicitly. Wrap first, then slice and derive hit
        # rows from those exact visual lines (including English wrapping).
        view = self.layer_observation
        if view is None:
            return
        if not view.legend_open:
            return
        overlay = self.query_one('#map-overlay')
        overlay.display = True
        pane = self.query_one('#map-pane')
        width = max(1, pane.content_size.width - 4)
        height = max(1, pane.content_size.height - 8)
        lines, rows = [], []
        for row, line in enumerate(self._layer_panel_text().split('\n')):
            wrapped = line.wrap(self.console, width, overflow='fold')
            lines.extend(wrapped)
            rows.extend([row if row <= EXIT_ROW else None]*len(wrapped))
        view.info_scroll = min(max(0,view.info_scroll),max(0,len(lines)-height))
        start = view.info_scroll
        self._layer_panel_hit_rows = rows[start:start+height]
        overlay.update(Text('\n').join(lines[start:start+height]))

    def _layer_scroll(self, event, delta):
        if self.layer_observation is None:
            return False
        if getattr(event, 'ctrl', False) or getattr(event, 'alt', False):
            self._zoom_map(-delta)
        elif self.cell_detail_target is not None:
            self._scroll_anomaly_detail(-delta)
        else:
            self.layer_observation.info_scroll += delta*3
            self._update_layer_panel()
        event.stop()
        event.prevent_default()
        return True
