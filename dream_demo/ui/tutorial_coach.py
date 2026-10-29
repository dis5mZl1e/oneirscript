"""Screen-level tutorial controls, live anchors and collision-free placement."""
from __future__ import annotations

from rich.text import Text
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.geometry import Region, Size
from textual.widgets import Static

from ..core.origin_course import MODULES, BY_ID, current, is_course, localized, note
from ..core.tutorial_categories import CATEGORIES, category_for, lessons
from ..core.tutorial_guidance import instructions, next_instruction, prepare_module, replay_state, map_targets
from ..i18n import get_language, tr
from .widgets import NativeButton


def words(zh, en):
    return en if get_language() == 'en' else zh


def place_card(screen: Size, size: Size, protected, minimum_height=8, minimum_width=24):
    """Prefer a clear corner, then narrow the guide rather than cover its target."""
    protected = [r for r in protected if r.width and r.height]
    candidates = []
    widths = (min(size.width, screen.width-2), min(30, size.width), min(24, size.width))
    for width in dict.fromkeys(min(screen.width-2, max(minimum_width, w)) for w in widths):
        base_height = min(size.height, max(3, screen.height-3))
        for height in dict.fromkeys((base_height, min(base_height, 12), min(base_height, minimum_height))):
            xs = [screen.width-width-1, 1]
            ys = [screen.height-height-2, 1]
            for r in protected:
                xs += [r.right+1, r.x-width-1]
                ys += [r.bottom+1, r.y-height-1]
            for x in xs:
                for y in ys:
                    r = Region(max(0, min(x, screen.width-width)),
                               max(0, min(y, screen.height-height-1)), width, height)
                    overlap = sum(max(0, min(r.right, p.right)-max(r.x, p.x)) *
                                  max(0, min(r.bottom, p.bottom)-max(r.y, p.y)) for p in protected)
                    loss = size.width-width + 2*(base_height-height)
                    candidates.append((overlap, loss, abs(x-xs[0])+abs(y-ys[0]), r))
    return min(candidates, key=lambda item: item[:3])[-1]


class CoachButton(NativeButton):
    def on_mouse_down(self, event):
        if event.button == 1:
            coach = next(w for w in self.ancestors if isinstance(w, TutorialCoach))
            coach.begin_drag(event, self)

    def _on_click(self, event):
        # Clicks are committed on release by the panel; a drag is never a click.
        event.stop()
        event.prevent_default()

    def render(self):
        label = self.label.copy()
        label.no_wrap, label.overflow = True, 'ellipsis'
        label.stylize_before(self.rich_style)
        return label


class TutorialCoach(Vertical):
    def cancel_drag(self):
        self._drag_origin = None
        self._drag_button = None
        self._drag_moved = False
        if self.app.mouse_captured is self:
            self.release_mouse()

    def on_mouse_release(self, event):
        # Capture can be taken by another widget or released on app blur.
        self._drag_origin = None
        self._drag_button = None

    def on_unmount(self):
        self.cancel_drag()

    def begin_drag(self, event, button=None):
        self._drag_origin = (event.screen_x, event.screen_y, self.region.x, self.region.y)
        self._drag_button = button
        self._drag_moved = False
        self.capture_mouse()
        event.stop()
        event.prevent_default()

    def on_mouse_down(self, event):
        if self.app.mouse_captured is self and (event.screen_x, event.screen_y) not in self.region:
            # A new press outside the guide means the old drag lost its
            # release (e.g. the pointer left the terminal). Re-route this
            # press after releasing capture so the first click still works.
            from textual.events import MouseDown
            self.cancel_drag()
            self.app.post_message(MouseDown(None, event.screen_x, event.screen_y,
                                            event.delta_x, event.delta_y, event.button,
                                            event.shift, event.meta, event.ctrl,
                                            event.screen_x, event.screen_y))
            event.stop()
            event.prevent_default()
            return
        if event.button == 1:
            self.begin_drag(event)

    def on_mouse_move(self, event):
        origin = getattr(self, '_drag_origin', None)
        if origin is None:
            return
        sx, sy, x, y = origin
        dx, dy = event.screen_x-sx, event.screen_y-sy
        if dx or dy:
            self._drag_moved = True
        x = max(0, min(self.app.size.width-self.region.width, x+dx))
        y = max(0, min(self.app.size.height-self.region.height-1, y+dy))
        self.app._coach_drag_position = (x, y)
        self.styles.offset = (x, y)
        self.app._coach_card_geometry = None
        event.stop()
        event.prevent_default()

    def on_mouse_up(self, event):
        if getattr(self, '_drag_origin', None) is None:
            return
        button = self._drag_button
        clicked = not self._drag_moved and button is not None and (event.screen_x, event.screen_y) in button.region
        self.cancel_drag()
        if clicked:
            self.app.handle_button_press(button)
        event.stop()
        event.prevent_default()

    DEFAULT_CSS = """
    TutorialCoach { display: none; layer: tutorial; position: absolute;
        width: 40; height: auto; border: round #87bfc7; padding: 0 1;
        background: #111c25 96%; color: #e5ecef; }
    #coach-title { height: 1; color: #a5dfd1; text-style: bold; }
    #coach-body-scroll { height: auto; max-height: 12; scrollbar-size-vertical: 1; }
    #coach-body { height: auto; }
    .coach-tools { height: 1; width: 100%; }
    .coach-tools Button { height: 1; min-width: 0; width: 1fr; border: none;
        padding: 0; background: transparent; color: #b8dbe1; }
    .coach-tools Button:hover, .coach-tools Button:focus { color: #ffe1a1; text-style: underline; }
    #coach-contents { height: 12; display: none; scrollbar-size-vertical: 1; }
    #coach-contents Button { width: 100%; min-width: 0; height: 1; border: none;
        padding: 0; background: transparent; content-align: left middle; }
    #coach-contents Button.selected { color: #f2d794; text-style: bold; }
    .coach-categories { height: 1; width: 100%; }
    .coach-categories Button { height: 1; width: 1fr; min-width: 0;
        border: none; padding: 0; background: transparent; color: #b8dbe1; }
    .coach-categories Button.selected { color: #ffe1a1; text-style: bold underline; }
    #coach-show { display: none; height: 1; border: none; padding: 0;
        width: 100%; min-width: 0; background: transparent; color: #b8dbe1; }
    """

    def compose(self):
        yield CoachButton('', id='coach-show')
        yield Static(id='coach-title')
        for start in (0, 3):
            with Horizontal(classes='coach-categories', id=f'coach-categories-{start}'):
                for key, zh, en in CATEGORIES[start:start+3]:
                    yield CoachButton(words(zh, en), id='coach-category-'+key)
        with VerticalScroll(id='coach-body-scroll'):
            yield Static(id='coach-body')
        with Horizontal(classes='coach-tools', id='coach-tools-main'):
            for key in ('directory', 'previous', 'next', 'restart'):
                yield CoachButton('', id='coach-'+key)
        with Horizontal(classes='coach-tools', id='coach-tools-extra'):
            for key in ('hide', 'extra', 'exit'):
                yield CoachButton('', id='coach-'+key)
        with VerticalScroll(id='coach-contents'):
            for category, _, _ in CATEGORIES:
                for module in lessons(category):
                    yield CoachButton('', id='coach-jump-'+module['id'])

    def on_mount(self):
        self._cue_timer = self.set_interval(1/8, self.app._tutorial_cue_tick)
        self._cue_timer.pause()


class TutorialCoachMixin:
    def _coach_cancel_drag(self):
        coach = getattr(self, '_coach_frame_widget', None)
        if coach is not None and coach.is_mounted:
            coach.cancel_drag()

    def on_app_blur(self, event):
        self._coach_cancel_drag()

    def _return_home(self, *args, **kwargs):
        self._coach_cancel_drag()
        return super()._return_home(*args, **kwargs)

    def _coach_record_view(self):
        if self._coach_enabled():
            from ..core.origin_course import observe_ui, pump
            observe_ui(self)
            pump(self.session.state)

    def compose(self):
        yield from super().compose()
        from .tutorial_direction import TutorialDirectionOverlay
        yield TutorialDirectionOverlay(id='tutorial-direction')
        yield TutorialCoach(id='tutorial-coach')

    def _refresh_tutorial_direction(self):
        from .tutorial_direction import update_overlay
        update_overlay(self)

    def _coach_enabled(self):
        return (not self.home_mode and is_course(self.session.state)
                and self.session.state.tutorial.get('coach_version') == 1)

    def _coach_widget_region(self, selector):
        from textual.css.query import NoMatches
        try:
            widget = self.query_one(selector)
        except NoMatches:
            return None
        if not widget.is_on_screen or not all(w.display and w.visible for w in widget.ancestors_with_self):
            return None
        return widget.content_region if widget.content_region.width else widget.region

    def _coach_map_region(self, point):
        if self.board_editor is not None:
            return None
        from textual.css.query import NoMatches
        try:
            view = self.query_one('#map')
        except NoMatches:
            return None
        if not view.is_on_screen:
            return None
        left, top, width, height = view.viewport
        x, y = point
        if not left <= x < left+width or not top <= y < top+height:
            return None
        return Region(view.content_region.x+(x-left)*view.cell_w,
                      view.content_region.y+(y-top)*view.cell_h, view.cell_w, view.cell_h)

    def _coach_anchor(self, anchor):
        kind, _, name = anchor.partition(':')
        if kind == 'map':
            point = self.session.state.tutorial.get('stations', {}).get(name)
            if point is None:
                try:
                    point = tuple(map(int, name.split(',')))
                except ValueError:
                    return None
            rect = self._coach_map_region(point)
            if rect is not None:
                return rect
            view = self.query_one('#map')
            if not view.is_on_screen:
                return None
            left, top, width, height = view.viewport
            return Region(view.content_region.x+max(0, min(width-1, point[0]-left))*view.cell_w,
                          view.content_region.y+max(0, min(height-1, point[1]-top))*view.cell_h,
                          view.cell_w, view.cell_h)
        if kind == 'board':
            grid = self._coach_widget_region('#board-editor-grid')
            if grid and self.board_editor:
                from .board_editor import GRID_ORIGIN_X, GRID_ORIGIN_Y
                x, y = self.board_editor.cursor
                if name == 'conductive':
                    x, y = 0, 0
                return Region(grid.x+GRID_ORIGIN_X+x*2, grid.y+GRID_ORIGIN_Y+y, 2, 1)
            return (self._coach_widget_region('#section-equipment-board') or
                    self._coach_widget_region('#nav-equipment'))
        if kind == 'tamper':
            panel = self._coach_widget_region('#tamper-overlay')
            if panel:
                prefixes = {'source': ('wslot:', 'source:', 'region:', 'target:'),
                            'degree': ('degree:',), 'condition': ('ctoggle:', 'cond:', 'condition:',),
                            'submit': ('editor:confirm',), 'preview': ('editor:view',)}
                hits = getattr(self, '_world_tamper_visible_hits', ())
                hit = next((h for h in hits if str(h.key).startswith(prefixes.get(name, (name,)))), None)
                if hit:
                    return Region(panel.x+hit.start_col, panel.y+hit.row,
                                  max(1, hit.end_col-hit.start_col), 1)
                return Region(panel.x, panel.y, min(panel.width, 18), 1)
            return (self._coach_widget_region('#section-tamper') or
                    self._coach_widget_region('#nav-actions'))
        if kind == 'widget':
            if name == '#map':
                target = (getattr(self, '_aim_free_cursor', None) or
                          getattr(self, '_aim_assist_pos', None) or
                          (self.session.state.player.x, self.session.state.player.y))
                return self._coach_map_region(target)
            result = self._coach_widget_region(name)
            if result:
                if name == '#self-audit-body':
                    rows = getattr(self, '_sa_line_actions', {})
                    row = next((n for n, action in rows.items() if action and action[0] == 'row'), 2)
                    return Region(result.x, min(result.bottom-1, result.y+row), min(32, result.width), 1)
                return result
            fallbacks = {'#self-audit-body': '#nav-portents', '#settings-categories': '#panel-tabs',
                         '#board-editor-sentence': '#nav-equipment',
                         '#section-equipment-memory': '#nav-equipment', '#section-insights': '#nav-equipment',
                         '#section-portents': '#nav-portents', '#section-constructs': '#nav-actions',
                         '#section-fire': '#nav-actions', '#sidebar-search': '#nav-inventory',
                         '#sidebar-filter': '#nav-inventory', '#sidebar-sort': '#nav-inventory'}
            return self._coach_widget_region(fallbacks.get(name, '#panel-tabs'))
        return None

    def _coach_before_frame(self):
        if self._coach_enabled():
            module = current(self.session.state)
            if module:
                prepare_module(self.session.state, module['id'])

    def _coach_live_instruction(self, row):
        text = row.en if get_language() == 'en' else row.zh
        anchor = self._coach_anchor(row.anchor)
        state = self.session.state
        module = current(state)
        if module and module['id'] in state.tutorial.get('completed', ()):
            return words('本项已完成。可打开目录继续本分类其他练习，或点击标签切换分类；也可重练或退出。',
                         'Lesson complete. Open the index for other exercises, choose another category tab, replay or exit.'), self._coach_widget_region('#coach-directory')
        pending = self.equipment_choice
        if pending and pending.get('command') == 'aim_equipment':
            module = current(self.session.state)
            gun_lesson = module and module['id'] == 'J4'
            preferred = next((i for i, option in enumerate(pending['options'])
                              if ('nail_gun' in option.get('definition_ids', ()) if gun_lesson
                                  else option.get('kind') == 'aggregate')), pending.get('cursor', 0))
            key = str(preferred+1)
            return words(f'当前是发射来源表，还未进入瞄准。按 {key} 选择'+('钉枪' if gun_lesson else '聚合弹')+'，或用上下键选择后 Enter；进入瞄准后再按 Tab 选落点，Esc 才是取消瞄准。',
                         f'This is the source table, not aiming yet. Press {key} to select '+('the nail gun' if gun_lesson else 'aggregate fire')+', or use arrows then Enter. Once aiming, Tab selects a free target and Esc cancels.'), self._coach_widget_region('#map-overlay')
        if row.fact.startswith('layer_') and row.fact.endswith('_seen') and self.layer_observation is not None:
            target = row.fact[len('layer_'):-len('_seen')]
            if target in ('low', 'middle', 'high'):
                from ..core.map_scene import OBSERVE_LAYERS
                from .layer_observation import LABELS
                layer = self.layer_observation.layer
                steps = (OBSERVE_LAYERS.index(target)-OBSERVE_LAYERS.index(layer)) % len(OBSERVE_LAYERS)
                return words(f'当前为「{LABELS[layer]}」：再按 Tab {steps} 次，切到「{LABELS[target]}」。也可点击顶部对应层名。',
                             f'Current layer: {layer}. Press Tab {steps} more time(s) to reach {target}, or click its name above.'), self._coach_widget_region('#layer-strip')
        if row.fact == 'condition_compared' and not self.session.state.is_visible(12, 19):
            return words('先退出联想盘和瞄准，走到金属教材格旁 (11,19)。再按 F 瞄准、Tab 切到自由落点，分别观察①金属格与旁边干地；无需射击。',
                         'Leave the board/aim and walk to (11,19) beside the metal sample. Press F, then Tab for free aiming. Compare marker 1 with nearby dry ground; no shot is needed.'), self._coach_anchor('map:11,19')
        if row.fact == 'magazine_fired':
            return self._coach_magazine_instruction(row)
        if row.fact == 'light_toggled':
            state = self.session.state
            if max(abs(state.player.x-28), abs(state.player.y-4)) > 1:
                return text, anchor
            if self.context_menu_target != (28, 4) or self.panel_mode != 'actions':
                return words('已到灯旁：点击本框「光源操作」，先进入右侧「行动」的目标操作。下一步再切换光源。',
                             'At the lamp: click Light controls in this guide to open Act / Target actions, then toggle the lamp.'), self._coach_widget_region('#coach-extra')
            panel = self._coach_widget_region('#panel')
            if panel:
                row_index = next((i for i, key in enumerate(getattr(self, '_panel_row_keys', ())) if str(key).startswith('action:')), None)
                if row_index is not None:
                    scroll = int(self.query_one('#panel').scroll_offset.y)
                    target = Region(panel.x, panel.y+row_index-scroll, panel.width, 1)
                    if panel.contains_region(target): anchor = target
            return words('现在在「行动→目标操作」：点击「熄灭光源」或「点亮光源」，成功切换就完成本节。',
                         'In Act / Target actions, click Turn light off/on. A successful toggle completes this lesson.'), anchor
        if row.fact == 'equipment_source_seen' and self._self_audit_visible() and self._sa_category != 'sources':
            body = self._coach_widget_region('#self-audit-body')
            if body:
                for line, action in self._sa_line_actions.items():
                    if action and action[0] == 'tabs':
                        for start, end, category in action[1]:
                            if category == 'sources':
                                anchor = Region(body.x+start, body.y+line, end-start, 1)
            return words('现在在自我察觉：点击顶部「来源」分类，阅读装备提供的来源条目；仅展开属性还不算本步骤。',
                         'In self inspection, select Sources at the top and read the equipment contribution. Expanding a stat alone is not this step.'), anchor
        # Point to a visible entry first, then to its control on the actual page.
        if row.fact == 'help_opened' and not self.controls_help_open:
            if self.sidebar_workspace != 'actions':
                return words('先点击右侧大菜单「行动」。进入后，在右栏底部点击「完整键位表」；也可按 Alt+H 直接打开。',
                             'First open the right-side Act workspace, then click Controls at its bottom. Alt+H also opens it directly.'), self._coach_widget_region('#nav-actions')
            return words('现在在「行动」界面：点击右栏底部「完整键位表」，或按 Alt+H。读完按 Esc 返回。',
                         'In Act, click Controls at the bottom of the sidebar or press Alt+H. Esc returns after reading.'), self._coach_widget_region('#panel-help')
        if row.fact == 'settings_opened' and self.panel_mode not in ('pause_settings', 'home_settings'):
            if self.panel_mode == 'pause':
                return words('现在在暂停菜单：点击「设置」，或用方向键选中「设置」后 Enter。',
                             'In the pause menu, click Settings or select it with arrows and press Enter.'), self._coach_widget_region('#pause-option-2')
            return words('先按 Esc 逐层关闭详情/面板，回到地图后再按 Esc 打开暂停菜单；在暂停菜单选择「设置」。Delete 才是跳过。',
                         'Use Esc to close details and panels, then Esc on the map opens Pause. Choose Settings there. Only Delete skips lessons.'), self._coach_widget_region('#nav-actions')
        if row.fact in ('self_opened', 'self_expanded', 'equipment_source_seen') and not self._self_audit_visible():
            return words('先进入右侧「自身→详查」，或按 Alt+S 打开自我察觉；再展开一个属性，读取基础值与来源。',
                         'First open Self / Full, or press Alt+S for self inspection. Expand an attribute to read its base and sources.'), self._coach_widget_region('#nav-portents')
        routes = {'#section-equipment-memory': ('equipment', '构筑→记忆', 'Build / Memory'),
                  '#section-insights': ('equipment', '构筑→洞察', 'Build / Insights'),
                  '#section-constructs': ('actions', '行动→构想', 'Act / Cast'),
                  '#section-portents': ('portents', '自身→征兆', 'Self / Signs'),
                  '#section-fire': ('actions', '行动→射击', 'Act / Fire'),
                  '#sidebar-search': ('inventory', '行囊', 'Pack'),
                  '#sidebar-filter': ('inventory', '行囊', 'Pack'),
                  '#sidebar-sort': ('inventory', '行囊', 'Pack')}
        route = routes.get(row.anchor.partition(':')[2])
        if route and self.sidebar_workspace != route[0]:
            nav = {'equipment': 'equipment', 'actions': 'actions', 'portents': 'portents', 'inventory': 'inventory'}[route[0]]
            return words('先进入右侧「'+route[1]+'」。\n'+text,
                         'First open '+route[2]+' in the right sidebar.\n'+text), self._coach_widget_region('#nav-'+nav)
        editor = self.board_editor
        if not row.anchor.startswith('board:') or editor is None:
            return text, anchor
        if row.anchor == 'board:relation':
            return self._coach_relation_instruction(row, editor)
        placements = editor.draft.placements
        if editor.held is not None:
            if row.fact == 'board_rotated':
                return words('现在手上有意象：按 R，或点击光框中的「旋转」，再 a 放下并 Enter 确认。',
                             'An image is held. Press R or click Rotate, then place with a and commit with Enter.'), self._coach_widget_region('#board-tool-rotate')
            grid = self._coach_widget_region('#board-editor-grid')
            if grid:
                from .board_editor import GRID_ORIGIN_X, GRID_ORIGIN_Y
                x, y = editor.cursor
                if row.anchor == 'board:holding':
                    x, y = 2, 0
                elif row.anchor == 'board:conductive':
                    coil = next((p for p in placements if p.definition_id == 'salt_soaked_coil'), None)
                    x, y = (4, coil.y) if coil else (0, 0)
                anchor = Region(grid.x+GRID_ORIGIN_X+x*2, grid.y+GRID_ORIGIN_Y+y, 2, 1)
                text = words('意象已拿起：用方向键把落点移到光框，再按 a 放下。\n'+text,
                             'The image is held. Move its landing to the frame with arrows and press a to place.\n'+text)
            return text, anchor
        if placements and row.fact != 'board_rotated':
            if row.anchor != 'board:conductive' or any(p.definition_id == 'water_gun' for p in placements):
                return words('草稿已有意象：点击光框中的「确认」或按 Enter，让本次整理实际生效。',
                             'The draft contains an image. Click the framed Commit control or press Enter to apply it.'), self._coach_widget_region('#board-tool-commit')
        side = self._coach_widget_region('#board-editor-side')
        if side:
            preferred = 'board' if row.fact == 'board_rotated' and placements else 'inventory'
            target_id = None
            if row.anchor == 'board:conductive':
                target_id = ('water_gun' if any(p.definition_id == 'salt_soaked_coil' for p in placements)
                             else 'salt_soaked_coil')
            elif row.anchor == 'board:holding':
                target_id = 'patched_pajamas'
            items = {item.instance_id: item.definition_id for item in self.session.state.inventory}
            hits = [hit for hit in editor.side_hits if hit.source == preferred
                    and (target_id is None or items.get(hit.instance_id) == target_id)]
            if hits:
                hit = hits[0]
                anchor = Region(side.x+hit.start_col, side.y+hit.row, max(1, hit.end_col-hit.start_col), 1)
                if anchor.x < 0 or anchor.right > self.size.width or anchor.y < 0 or anchor.bottom >= self.size.height:
                    anchor = self._coach_widget_region('#board-editor-scroll')
                text = words('先点击光框中的意象，把它拿在手上；再根据下一条提示安置。\n'+text,
                             'First click the framed image to pick it up, then follow the placement instruction.\n'+text)
        return text, anchor

    def _coach_item_anchor(self, editor, definition):
        """Only outline the actual item if its hit is inside the scroll viewport."""
        items = {item.instance_id: item.definition_id for item in self.session.state.inventory}
        side = self._coach_widget_region('#board-editor-side')
        viewport = self._coach_widget_region('#board-editor-scroll')
        coach = getattr(self, '_coach_frame_widget', None)
        covered = coach.region if coach and coach.display else None
        for hit in editor.side_hits:
            if items.get(hit.instance_id) == definition and side:
                rect = Region(side.x+hit.start_col, side.y+hit.row, max(1, hit.end_col-hit.start_col), 1)
                if viewport and viewport.contains_region(rect) and not (covered and covered.overlaps(rect)):
                    return rect
        if viewport and covered and viewport.overlaps(covered):
            overlap = viewport.intersection(covered)
            clear = (Region(viewport.x, viewport.y, viewport.width, overlap.y-viewport.y),
                     Region(viewport.x, overlap.bottom, viewport.width, viewport.bottom-overlap.bottom),
                     Region(viewport.x, viewport.y, overlap.x-viewport.x, viewport.height),
                     Region(overlap.right, viewport.y, viewport.right-overlap.right, viewport.height))
            visible = [r for r in clear if r.width > 0 and r.height > 0]
            if visible:
                return max(visible, key=lambda r: r.width*r.height)
        return viewport

    def _coach_missing_item(self, definition):
        from ..data.items import ITEM_DEFINITIONS
        name = tr(ITEM_DEFINITIONS[definition]['name'])
        dropped = next((entry for entry in self.session.state.world_items
                        if entry.item.definition_id == definition and entry.item.quantity > 0), None)
        if dropped:
            point = f'{dropped.x},{dropped.y}'
            return words(f'「{name}」不在行囊：到 ({point}) 取回教材，或点击「重练」重新备齐。',
                         f'{name} is not in your pack. Retrieve it at ({point}), or click Redo to restore the practice kit.'), self._coach_anchor('map:'+point) or self._coach_widget_region('#coach-restart')
        return words(f'「{name}」已不在行囊。点击本框「重练」备齐教材后再继续。',
                     f'{name} is missing. Click Redo in this guide to restore the practice kit.'), self._coach_widget_region('#coach-restart')

    def _coach_magazine_instruction(self, row):
        from ..equipment.positional import compile_formation
        from ..equipment.syntax import board_roles
        from .board_editor import GRID_ORIGIN_X, GRID_ORIGIN_Y
        editor = self.board_editor
        board = editor.draft if editor else self.session.state.board
        gun = next((item for item in self.session.state.inventory if item.definition_id == 'nail_gun'), None)
        if gun is None:
            return self._coach_missing_item('nail_gun')
        placed = board.placement(gun.instance_id)
        ready = bool(placed and any(r.status == 'ready' and 'fire' in r.action_modes
                                    and gun.instance_id in r.instance_ids
                                    for r in compile_formation(board, column_roles=board_roles(board)).rows))
        if editor is None:
            if ready:
                return words('钉枪已成句：按 F；若出现来源表，选中钉枪并 Enter，才会进入瞄准。再按 Tab 切自由落点，向可见空地按 Enter 射击。',
                             'The nail gun is active. Press F; if a source table opens, select the nail gun and press Enter to start aiming. Then Tab for a free target and Enter to fire at clear ground.'), self._coach_anchor('widget:#map')
            return words('先打开「构筑→装备」的联想盘，找到「钉枪」。把它放在第2行第2列（左上角为第1行第1列），确认后再射击。',
                         'Open Build / Gear and find the nail gun. Place it at row 2, column 2 (top left is row 1, column 1), then commit before firing.'), self._coach_anchor('board:grid')
        if editor.held is not None:
            if editor.held.definition_id != 'nail_gun':
                return words('当前拿起的不是钉枪。按 Esc 放回，在列表中滚动找到「钉枪」再拿起。',
                             'The held image is not the nail gun. Press Esc to put it back, then scroll to the nail gun.'), self._coach_item_anchor(editor, 'nail_gun')
            grid = self._coach_widget_region('#board-editor-grid')
            rect = Region(grid.x+GRID_ORIGIN_X+2, grid.y+GRID_ORIGIN_Y+1, 2, 1) if grid else None
            return words('钉枪已拿起：移到第2行第2列，按 a 放下，再按 Enter 确认。',
                         'Nail gun held. Move to row 2, column 2, press a to place, then Enter to commit.'), rect
        if ready:
            return words('钉枪草稿已成句：按 Enter 确认，再按 F；在来源表选钉枪并 Enter 后，Tab 选空地、Enter 射击。',
                         'The draft is ready. Commit with Enter, press F, select the nail gun and Enter if asked, then Tab to aim at clear ground and Enter to fire.'), self._coach_widget_region('#board-tool-commit')
        return words('在意象列表中滚动找到「钉枪」，点击拿起；不要拿睡衣。将钉枪放到第2行第2列再确认。',
                     'Scroll the image list to the nail gun and pick it up. Place it at row 2, column 2 before committing.'), self._coach_item_anchor(editor, 'nail_gun')

    def _coach_relation_instruction(self, row, editor):
        """Route each component before suggesting a commit of the whole phrase."""
        from .board_editor import GRID_ORIGIN_X, GRID_ORIGIN_Y
        attribution = row.fact == 'attribution_committed'
        donor = 'ignite_gloves' if attribution else 'swift_thought_ring'
        word = 'word_de' if attribution else 'word_de_manner'
        label = words('的' if attribution else '地', 'OF' if attribution else 'BY')
        required = ((donor, 0), ('rusty_boxcutter', 4))
        missing = next(((definition, x) for definition, x in required
                        if not any(p.definition_id == definition and p.x == x and p.y == 0
                                   for p in editor.draft.placements)), None)
        grid = self._coach_widget_region('#board-editor-grid')
        if missing:
            if editor.held is not None:
                held_target = next(((definition, x) for definition, x in required
                                    if editor.held.definition_id == definition), None)
                if held_target is None:
                    return words('手上不是本节教材：按 Esc 放回，再选择点火手套/迅念指环或生锈的美工刀。',
                                 'This is not a practice image. Press Esc to put it back, then select the gloves/ring or boxcutter.'), self._coach_widget_region('#board-editor-scroll')
                missing = held_target
            definition, x = missing
            item = next((i for i in self.session.state.inventory if i.definition_id == definition), None)
            if item is None:
                return self._coach_missing_item(definition)
            item_name = tr(item.name)
            if editor.held is not None:
                anchor = Region(grid.x+GRID_ORIGIN_X+x*2, grid.y+GRID_ORIGIN_Y, 2, 1) if grid else None
                return words(f'把「{item_name}」移到第1行第{x+1}列，按 a 放下。先放齐两件意象，再加入虚词。',
                             f'Place {item_name} at row 1, column {x+1} with a. Place both images before adding the word.'), anchor
            anchor = self._coach_item_anchor(editor, definition)
            return words(f'先拿起「{item_name}」，放在第1行第{x+1}列；仍是草稿，暂不确认。',
                         f'Pick up {item_name} and place it at row 1, column {x+1}. Keep editing the draft.'), anchor
        if not any(p.piece_id == word and p.x == 3 and p.y == 0 for p in editor.draft.pieces):
            if editor.tool != ('piece', word):
                return words(f'两件意象已放齐。按 Z 或点击「功能词」循环到「{label}」。',
                             f'Both images are placed. Cycle Z or Words until {label} is selected.'), self._coach_widget_region('#board-tool-tool')
            anchor = Region(grid.x+GRID_ORIGIN_X+6, grid.y+GRID_ORIGIN_Y, 2, 1) if grid else None
            return words(f'当前工具是「{label}」：将光标移到第1行第4列，按 a 放下。',
                         f'{label} is selected. Move to row 1, column 4 and press a.'), anchor
        return words('读整句与效果：只有关联行为得到修饰，属性来源不额外行动。按 Enter 确认后才生效。',
                     'Read the sentence and effects: the modifier belongs to this linked action. Press Enter to apply it.'), self._coach_widget_region('#board-tool-commit')

    def _refresh_tutorial_coach(self):
        # 帧循环 + 每次 refresh_view 都会到这里；教练未开时它唯一的活是「确认控件
        # 在、把它藏好」。`bool(self.query('#tutorial-coach'))` 会为一次判空走完整
        # 控件树的 CSS 匹配（实测 ~1.1ms/次，30Hz 下白烧 ~3% CPU），而 id 查询的
        # query_one 是 O(1)。教练在 compose 里挂一次、生命周期同 App，缓存引用即可。
        coach = getattr(self, '_coach_frame_widget', None)
        if coach is None or not coach.is_mounted:
            try:
                coach = self.query_one('#tutorial-coach', TutorialCoach)
            except Exception:  # pragma: no cover - 早期挂载/拆卸窗口
                return
            self._coach_frame_widget = coach
        enabled = self._coach_enabled()
        if not enabled:
            self._refresh_tutorial_direction()
            coach.cancel_drag()
            if coach.display:
                coach.display = False
                self._coach_clear_cues()
            if hasattr(coach, '_cue_timer'):
                coach._cue_timer.pause()
            return
        self.query_one('#tutorial-card').show_step(Text())
        coach.display = True
        if hasattr(coach, '_cue_timer'):
            coach._cue_timer.resume()
        state = self.session.state
        module = current(state)
        if module is None:
            return
        row, index, count = next_instruction(state)
        if row is None:
            return
        self._coach_row = row
        directory = bool(getattr(self, '_coach_directory', False))
        hidden = bool(getattr(self, '_coach_hidden', False))
        category = getattr(self, '_coach_category', category_for(module['id']))
        if not directory:
            category = category_for(module['id'])
        self._coach_category = category
        labels = {'show': words('教程 · F6 目录', 'Guide · F6 contents'),
                  'directory': words('目录', 'Index'), 'previous': words('上节', 'Prev'),
                  'next': words('下节', 'Next'), 'restart': words('重练', 'Redo'),
                  'hide': words('收起提示', 'Hide'), 'exit': words('退出练习', 'Exit'),
                  'extra': words('我已读懂', 'Understood')}
        for key, label in labels.items():
            button = coach.query_one('#coach-'+key)
            if button.label.plain != label:
                button.label = label
        for selector in ('#coach-title', '#coach-body-scroll', '#coach-tools-main', '#coach-tools-extra',
                         '#coach-categories-0', '#coach-categories-3'):
            coach.query_one(selector).display = not hidden
        coach.query_one('#coach-show').display = hidden
        coach.query_one('#coach-contents').display = directory and not hidden
        done = set(state.tutorial.get('completed', ())) | set(state.tutorial.get('reviewed', ()))
        title = f"{module['id']} {index}/{count} · {localized(module, 'title')}"
        live_text, anchor = self._coach_live_instruction(row)
        body = Text(live_text, style='#edf4f5')
        if directory:
            body = Text(words('选择任意章节开始或重练。跳转会重置练习场，保留已完成记录，正式存档不变。',
                              'Choose any chapter. Jumping resets practice, retains completed history and leaves normal saves unchanged.'), style='#edf4f5')
        targets = self._coach_map_targets()
        if targets:
            positions = '  '.join(f'{number}:({point[0]},{point[1]})' for number, point in targets.items())
            body.append('\n'+words('地图编号 ', 'Map markers ')+positions, style='#e5cd92')
        if not hidden:
            body.append('\n\n'+words('按编号和光框操作；拖动面板任意位置调整。F6 目录 · Delete 跳过本节 · Esc 返回/暂停。',
                                      'Follow markers and frames. Drag anywhere to move. F6 contents · Delete skips · Esc back/pause.'), style='#a6bec5')
            if state.tutorial.get('coach_finished'):
                body.append('\n'+words('已完成全部练习，可重练或退出。', 'All exercises complete. Replay or exit.'), style='#e5cd92')
            elif state.tutorial.get('coach_category_finished') == category:
                body.append('\n'+words('本分类已练完：点击上方标签选择其他分类，或重练。',
                                       'Category complete. Choose another tab or replay.'), style='#e5cd92')
        signature = (title, body.plain, directory, hidden, tuple(sorted(done)), get_language(), category)
        if signature != getattr(self, '_coach_content_key', None):
            self._coach_content_key = signature
            coach.query_one('#coach-title').update(Text(title, style='bold #a5dfd1', no_wrap=True, overflow='ellipsis'))
            coach.query_one('#coach-body').update(body)
            for key, zh, en in CATEGORIES:
                tab = coach.query_one('#coach-category-'+key)
                tab.label = words(zh, en)
                tab.set_class(key == category, 'selected')
            for chapter in MODULES:
                button = coach.query_one('#coach-jump-'+chapter['id'])
                button.display = category_for(chapter['id']) == category
                mark = '✓' if chapter['id'] in done else '·'
                button.label = f"{mark} {chapter['id']} {localized(chapter, 'title')}"
                selected_id = (lessons(category)[getattr(self, '_coach_directory_cursor', 0)]['id']
                               if directory else module['id'])
                button.set_class(chapter['id'] == selected_id, 'selected')
        extra = coach.query_one('#coach-extra')
        extra.display = row.fact in ('exit_read', 'practice_log_seen') or module['id'] in ('I2', 'B4')
        if module['id'] == 'B4':
            extra.label = words('光源操作', 'Light controls')
        if module['id'] == 'I2' and row.fact != 'practice_log_seen':
            op = 'accept' if state.tutorial.get('practice_quest') in ('none', 'abandoned') else 'deliver'
            extra.label = words('接取练习' if op == 'accept' else '交付练习',
                                'Accept practice' if op == 'accept' else 'Deliver practice')
        protected = []
        if anchor and not row.anchor.startswith('widget:#coach-'):
            protected.append(anchor.grow((1, 1, 1, 1)))
        player = self._coach_map_region((state.player.x, state.player.y))
        if player:
            protected.append(player.grow((1, 1, 1, 1)))
        for point in self._coach_map_targets().values():
            rect = self._coach_map_region(point)
            if rect:
                protected.append(rect.grow((1, 1, 1, 1)))
        task_area = self._coach_task_region()
        if task_area and row.anchor.startswith('map:'):
            protected.append(task_area)
        width = 20 if hidden else min(42, max(36, self.size.width//3))
        layout_key = (signature, tuple(protected), self.size, self.board_editor is not None,
                      getattr(self, '_coach_drag_position', None))
        self._coach_anchor_rect = anchor
        if layout_key == getattr(self, '_coach_layout_key', None):
            self._refresh_tutorial_direction()
            return
        self._coach_layout_key = layout_key
        lines = len(body.wrap(self.console, max(1, width-4)))
        height = 3 if hidden else min(self.size.height-3, max(10, lines+8)+(12 if directory else 0))
        region = place_card(self.size, Size(width, height), protected, minimum_height=10 if directory else 8,
                            minimum_width=20 if hidden else 36)
        if self.board_editor is not None:
            # Keep the board's lower action rows and right-hand item list free.
            # The compact body remains scrollable; the directory pauses editing.
            board_height = min(height, max(10, self.size.height-8) if directory else 9)
            region = Region(self.size.width-width-1, 1, width, board_height)
        board_open = self.board_editor is not None
        if board_open != getattr(self, '_coach_was_board_open', False):
            self._coach_drag_position = None
        self._coach_was_board_open = board_open
        drag = getattr(self, '_coach_drag_position', None)
        if drag is not None:
            x = max(0, min(self.size.width-region.width, drag[0]))
            y = max(0, min(self.size.height-region.height-1, drag[1]))
            region = Region(x, y, region.width, region.height)
        geometry = tuple(region)
        if geometry != getattr(self, '_coach_card_geometry', None):
            self._coach_card_geometry = geometry
            coach.styles.width, coach.styles.height = region.width, region.height
            coach.styles.offset = (region.x, region.y)
            self._map_force_repaint = True
        directory_height = min(10, max(3, region.height-10)) if directory else 0
        coach.query_one('#coach-body-scroll').styles.height = max(1, region.height-7-directory_height)
        coach.query_one('#coach-contents').styles.height = directory_height or 10
        self._coach_anchor_rect = anchor
        self._refresh_tutorial_direction()

    def _coach_map_targets(self):
        if not self._coach_enabled():
            return {}
        module = current(self.session.state)
        if not module:
            return {}
        return map_targets(self.session.state, module['id'])

    def _coach_task_region(self):
        regions = [self._coach_map_region(point) for point in self._coach_map_targets().values()]
        regions = [r for r in regions if r]
        if not regions:
            return None
        left, top = min(r.x for r in regions), min(r.y for r in regions)
        right, bottom = max(r.right for r in regions), max(r.bottom for r in regions)
        return Region(left, top, right-left, bottom-top).grow((1, 2, 1, 2)).intersection(
            self.query_one('#map').content_region)

    def _coach_sync_map(self, map_view, state):
        map_view.tutorial_cells = {point: str(number) for number, point in self._coach_map_targets().items()}

    def _coach_select(self, module_id):
        if not self._coach_enabled() or module_id not in BY_ID:
            return
        self._coach_cancel_drag()
        from ..persistence import GameSession
        fresh = replay_state(self.session.state, module_id)
        manager = self.session.manager
        self._return_home()
        self.session = GameSession(fresh, manager, persist_initial=False, persistence_enabled=False)
        self._coach_directory = self._coach_hidden = False
        self._coach_drag_position = None
        self._coach_content_key = self._coach_card_geometry = None
        self._coach_layout_key = None
        self._coach_category = category_for(module_id)
        self._course_ui_previous = None
        self._leave_home()
        # Replaying a lesson is an immediate local reset, not a descent. Do not
        # leave a floor-intro animation temporarily rejecting inspection input.
        if getattr(self, '_floor_transition', None) is not None:
            self._finish_floor_transition(suppress_wipe=True)

    def handle_button_press(self, button):
        name = button.id or ''
        if not name.startswith('coach-'):
            return super().handle_button_press(button)
        self._coach_command(name[6:])

    def _coach_command(self, command):
        if not self._coach_enabled():
            return
        self._coach_cancel_drag()
        state = self.session.state
        module = current(state)
        if command.startswith('category-'):
            category = command[9:]
            if category not in {row[0] for row in CATEGORIES}:
                return
            self._coach_category = category
            self._coach_directory = True
            self._coach_hidden = False
            self._coach_directory_cursor = 0
            self._coach_content_key = None
            self._coach_clear_cues()
            self._refresh_tutorial_coach()
            self.call_after_refresh(self.query_one('#coach-jump-'+lessons(category)[0]['id']).scroll_visible,
                                    animate=False)
            return
        if command.startswith('jump-'):
            self._coach_select(command[5:])
            return
        if command in ('previous', 'next', 'restart'):
            group = lessons(category_for(module['id']))
            index = next(i for i, item in enumerate(group) if item['id'] == module['id'])
            delta = {'previous': -1, 'next': 1, 'restart': 0}[command]
            self._coach_select(group[(index+delta) % len(group)]['id'])
            return
        if command == 'directory':
            if getattr(self, '_coach_hidden', False) and 'guide_hidden' in state.tutorial.get('facts', ()):
                note(state, 'guide_restored')
            self._coach_directory = not getattr(self, '_coach_directory', False)
            self._coach_hidden = False
            self._coach_category = category_for(module['id'])
            self._coach_directory_cursor = next(i for i, m in enumerate(lessons(self._coach_category)) if m['id'] == module['id'])
        elif command == 'hide':
            self._coach_hidden = True
            self._coach_directory = False
            note(state, 'guide_hidden')
        elif command == 'show':
            self._coach_hidden = False
            if 'guide_hidden' in state.tutorial.get('facts', ()):
                note(state, 'guide_restored')
        elif command == 'extra':
            row, _, _ = next_instruction(state)
            if module['id'] == 'B4':
                if max(abs(state.player.x-28), abs(state.player.y-4)) <= 1:
                    self.context_menu_target = (28, 4)
                    self.open_sidebar_route('constructs', manual=False)
                else:
                    self.show_toast(words('先走到①灯旁一格内，再打开光源操作。', 'Stand within one tile of lamp 1 before opening its controls.'))
            elif row and row.fact in ('exit_read', 'practice_log_seen'):
                note(state, row.fact)
            elif module['id'] == 'I2':
                from ..core.origin_course import control
                op = 'accept' if state.tutorial.get('practice_quest') in ('none', 'abandoned') else 'deliver'
                result = control(state, op)
                if result.message:
                    self.show_toast(result.message)
        elif command == 'exit':
            self.action_save_exit()
            return
        self._coach_clear_cues()
        self._refresh_tutorial_coach()

    def _coach_handle_key(self, event):
        from textual.widgets import Input
        if (event.key == 'delete' and not self.home_mode
                and self.session.state.tutorial.get('active')
                and self.settings_page.capture_target is None and self.qol_confirmation is None
                and not isinstance(self.focused, Input) and not self.qol_searching):
            from ..core.tutorial import tutorial_skip_step
            message = tutorial_skip_step(self.session.state)
            if message:
                self.show_toast(message)
            self._mark_key_handled(event.key)
            self.refresh_view()
            event.stop()
            event.prevent_default()
            return True
        if (self._coach_enabled() and self.settings_page.capture_target is None
                and self.qol_confirmation is None):
            key = event.key
            if key == 'f6':
                self._coach_command('directory')
            elif getattr(self, '_coach_directory', False):
                group = lessons(self._coach_category)
                cursor = getattr(self, '_coach_directory_cursor', 0)
                if key in ('escape', 'q'):
                    self._coach_command('directory')
                elif key in ('enter', 'return'):
                    self._coach_select(group[cursor]['id'])
                elif key in ('left', 'right', 'tab', 'shift+tab'):
                    keys = [row[0] for row in CATEGORIES]
                    delta = -1 if key in ('left', 'shift+tab') else 1
                    self._coach_command('category-'+keys[(keys.index(self._coach_category)+delta) % len(keys)])
                elif key in ('up', 'down', 'pageup', 'pagedown'):
                    delta = -1 if key == 'up' else -8 if key == 'pageup' else 8 if key == 'pagedown' else 1
                    cursor = (cursor+delta) % len(group)
                    self._coach_directory_cursor = cursor
                    self.query_one('#coach-jump-'+group[cursor]['id']).scroll_visible(animate=False)
                    for i, module in enumerate(group):
                        self.query_one('#coach-jump-'+module['id']).set_class(i == cursor, 'selected')
                elif key in ('f10', 'alt+q'):
                    return False
            else:
                return False
            self._mark_key_handled(key)
            event.stop()
            event.prevent_default()
            return True
        return False

    def action_context_q(self):
        if self._coach_enabled() and getattr(self, '_coach_directory', False):
            self._coach_command('directory')
            return
        return super().action_context_q()

    def _coach_clear_cues(self):
        regions = getattr(self, '_coach_damage', ())
        if regions and self.is_mounted:
            self.screen.refresh(*regions)
            self._map_force_repaint = True
        self._coach_damage = ()

    def _tutorial_cue_tick(self):
        if not self._coach_enabled():
            return
        if self.is_headless:
            return
        from .tutorial_cues import cue_regions
        regions = cue_regions(self)
        old = getattr(self, '_coach_damage', ())
        self._coach_damage = regions
        if old or regions:
            from .map_image_transport import cells_to_rectangles
            view = self.query_one('#map')
            map_cells, text_cells = set(), set()
            native_map = (view.is_on_screen and self.resolved_map_display()[0] == 'image')
            for region in (*old, *regions):
                for y in range(max(0, region.y), min(self.size.height-1, region.bottom)):
                    for x in range(max(0, region.x), min(self.size.width, region.right)):
                        widget, _ = self.screen._compositor.get_widget_at(x, y)
                        on_map = (native_map and (x, y) in view.content_region
                                  and (widget is view or widget.id == 'map-hints'))
                        (map_cells if on_map else text_cells).add((x, y))
            self._coach_restore_cells = map_cells
            damage = [Region(*rect) for rect in cells_to_rectangles(text_cells)]
            # Kick one output transaction outside the map. Map cue pixels are
            # restored with tiny image patches, never a full-map text repaint.
            damage.append(Region(self.size.width-1, 0, 1, 1))
            self.screen.refresh(*damage)

    def _write_tutorial_cues(self):
        if not self._coach_enabled() or self.is_headless:
            return
        from .tutorial_cues import cue_packets
        from .tutorial_cues import repair_packets
        repairs = repair_packets(self, getattr(self, '_coach_restore_cells', ()))
        self._coach_restore_cells = ()
        self._write_map_packets(tuple(self._map_packet_for_write(p) for p in repairs))
        packets = cue_packets(self)
        self._write_map_packets(tuple(self._map_packet_for_write(p) for p in packets))
        self._tutorial_cue_packets_sent = getattr(self, '_tutorial_cue_packets_sent', 0) + len(packets)
