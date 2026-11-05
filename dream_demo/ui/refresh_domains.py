"""Conservative synchronous fallback plus frame-coalesced UI domain requests."""
from ..core.presentation_control import submit_presentation
from copy import deepcopy
from dataclasses import fields

from ..core.entities import Cell
from ..env_compat import flag
from ..i18n import get_language

UI_DOMAINS = frozenset(('status', 'body', 'panels', 'log', 'hitmap'))
_CELL_FIELDS = tuple(field.name for field in fields(Cell))
PANEL_MAPS = ('_panel_rows', '_panel_row_keys', '_panel_cell_rows',
              '_inventory_cell_rows', '_inventory_grid', '_inventory_layout_hit',
              '_equipment_region_start', '_panel_subtab_hits',
              '_sidebar_rendered_entry_keys')


class _RetainedText:
    """Own a protected baseline and reuse its unchanged published Rich model.

    Text equality omits rendering options, so compare those too. Consumers may
    still edit published text; the next read repairs it from the owned baseline.
    """
    __slots__ = ('baseline', 'published')

    def __init__(self, text):
        self.baseline = text.copy()
        self.published = text

    def get(self):
        expected, actual = self.baseline, self.published
        if (actual != expected or actual.style != expected.style
                or actual.justify != expected.justify
                or actual.overflow != expected.overflow
                or actual.no_wrap != expected.no_wrap
                or actual.end != expected.end
                or actual.tab_size != expected.tab_size):
            self.published = expected.copy()
        return self.published


def _isolate_containers(value):
    """只复制容器本身，叶子对象（命中描述等）保持共享。

    与 ``deepcopy`` 的差别只在于叶子；命中表在帧内只读，容器隔离足以防止
    缓存被追加/替换污染，同时避免每帧复制数千个叶子对象的分配与 GC 压力。
    """
    if isinstance(value, list):
        return [_isolate_containers(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_isolate_containers(item) for item in value)
    if isinstance(value, dict):
        return {key: _isolate_containers(item) for key, item in value.items()}
    return value


class RefreshDomainsMixin:
    def _incremental_ui_enabled(self):
        return flag('UI_INCREMENTAL', True)

    def request_ui_refresh(self, *domains):
        """Queue named domains; the ordinary 30Hz timer consumes their union."""
        if not self._incremental_ui_enabled():
            self.refresh_view()
            return
        self.session.state.mark_ui_dirty(*domains)
        # 请求排队自身不改变正文；core 的 mark_ui_dirty 仍会推进内容版本。
        self._ui_request_count = getattr(self, '_ui_request_count', 0) + 1

    def _ui_refresh_context(self):
        state = self.session.state
        return (id(state), state.layer_key(), self.home_mode, self.panel_mode,
                self._panel_subpage_id(), self.size, repr(self.config.values))

    def _ui_domain_needed(self, domain):
        active = getattr(self, '_ui_refresh_active', None)
        return active is None or domain in active

    def _flush_ui_refresh(self):
        if (not self._incremental_ui_enabled() or not self.is_running
                or getattr(self, '_ui_refresh_running', False)):
            return False
        dirty = set(self.session.state.ui_dirty)
        if getattr(self, '_ui_render_context', None) != self._ui_refresh_context():
            dirty.update(UI_DOMAINS)
        if not dirty:
            return False
        if dirty & {'panels', 'hitmap'}:
            dirty.update(('panels', 'hitmap'))
        self._run_ui_refresh(dirty, force=False)
        return True

    def _run_ui_refresh(self, domains=UI_DOMAINS, *, force=True):
        state = self.session.state
        if getattr(self, '_ui_refresh_running', False):
            state.mark_ui_dirty(*domains)
            return
        revision = state.ui_revision
        self._ui_refresh_running = True
        self._ui_refresh_active = set(domains)
        self._ui_refresh_force = force
        try:
            self._refresh_view_now()
        except BaseException:
            state.mark_ui_dirty(*domains)
            raise
        else:
            # A reentrant request or mutation during rendering must survive.
            if state is self.session.state and state.ui_revision == revision:
                state.ui_dirty.difference_update(domains)
            self._ui_render_context = self._ui_refresh_context()
        finally:
            self._ui_refresh_running = False
            self._ui_refresh_active = None
            self._ui_refresh_force = False

    def _inventory_ui_key(self, state):
        if self.panel_mode != 'inventory':
            return None
        panel = self.query_one('#panel')
        footer = self._panel_footer(state)
        return (id(state), state.layer_key(), panel.content_size, self.size,
                repr(self.config.values), get_language(),
                self._panel_subpage_id(),
                tuple(repr(vars(item)) for item in state.inventory),
                state.inventory_used, state.inventory_capacity,
                tuple(sorted(state.equipped.items())),
                tuple(p.instance_id for p in state.board.placements),
                'oblivion_strong' in state.portents,
                self.panel_selection, self.panel_scroll, self.inventory_layout,
                self.inventory_layout_focused, self.inventory_intro_open,
                self.inventory_filter, self.inventory_query, self.inventory_sort,
                self.expanded_key, self.details_expanded,
                None if footer is None else (footer.plain, tuple(footer.spans)))

    def _ui_panel_text(self, state):
        if not self._incremental_ui_enabled():
            return self._panel_text(state)
        key = self._inventory_ui_key(state)
        cached = getattr(self, '_ui_panel_cache', None)
        if (key is not None and cached is not None and cached[0] == key
                and not getattr(self, '_ui_refresh_force', False)):
            for name, value in cached[2].items():
                # Input paths read these maps until the next actual render.
                # Keep that published model; repair only external edits or a
                # different panel's replacement, rather than cloning every row.
                if getattr(self, name, None) != value:
                    setattr(self, name, _isolate_containers(value))
            return cached[1].get()
        text = self._panel_text(state)
        if key is not None:
            # Rendering may clamp scroll; store its final browsing position.
            key = self._inventory_ui_key(state)
            self._ui_panel_cache = (key, _RetainedText(text),
                {name: deepcopy(getattr(self, name, None)) for name in PANEL_MAPS})
        return text

    def _ui_body_text(self, state, width):
        """仅复用同一世界快照；显式全量刷新仍重读所有环境事实。"""
        enabled = self._incremental_ui_enabled()
        target = self.hover_cell or (state.player.x, state.player.y)
        cell = state.cell(*target) if (0 <= target[0] < state.width
                                       and 0 <= target[1] < state.height) else None
        key = (self._ui_refresh_context(), width, get_language(), state.time,
               state.ui_revision - getattr(self, '_ui_request_count', 0),
               state.action_seq, state.material_revision, state.plant_revision,
               state.topology_revision, repr(vars(state.player)),
               tuple(repr(vars(item)) for item in state.inventory),
               repr(state.portents), repr(state.equipped), repr(state.board),
               # Bound Cells keep their values in authoritative columns, not
               # __dict__. Read the declared display state through descriptors.
               repr(tuple(getattr(cell, name) for name in _CELL_FIELDS))
               if cell is not None else None,
               self.hover_cell, self.observe_mode,
               getattr(state, 'map_knowledge_version', 0), state.developed_total,
               bool(getattr(state, 'terrain_known', False))) if enabled else None
        cached = getattr(self, '_ui_body_cache', None)
        if (enabled and not self._ui_refresh_force and cached is not None
                and cached[0] == key):
            # _hover_text publishes this target for the terrain preview too.
            submit_presentation(self.session, state, 'hover', *target)
            return cached[1].get()
        text = self._sidebar_context_text(state, width)
        if enabled:
            self._ui_body_cache = (key, _RetainedText(text))
        return text
