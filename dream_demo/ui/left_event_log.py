"""Scrollable recent messages below the map, directly above the footer."""
from textual.widgets import RichLog

MAP_HIDDEN_PANEL_MODES = frozenset({'pause', 'pause_settings', 'pause_codex', 'board_editor'})


class LeftEventLog(RichLog):
    DEFAULT_CSS = """
    LeftEventLog {
        width: 1fr;
        height: 4;
        min-height: 4;
        background: #25252d;
        border-top: solid #59627a;
        padding: 0 1;
        overflow: hidden auto;
        scrollbar-size-vertical: 0;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(max_lines=500, min_width=1, wrap=True, **kwargs)
        self._messages = ()
        self._source_key = None
        self._body_cache = {}

    def set_messages(self, messages, *, message_ids=None):
        identities = message_ids if message_ids is not None else (None,) * len(messages)
        signature = tuple((identity, body.plain, tuple(body.spans))
                          for identity, body in zip(identities, messages))
        if signature == self._messages:
            return
        follow = (not self._messages or self.scroll_y == 0) and not self.is_vertical_scrollbar_grabbed
        previous_y = self.scroll_y
        prefix = len(self._messages)
        if signature[:prefix] != self._messages:
            prefix = 0
            # A bounded source window loses its oldest entries while retaining
            # the same tail. Those rows already exist in RichLog's bounded lines.
            for dropped in range(1, len(self._messages)):
                overlap = self._messages[dropped:]
                if signature[:len(overlap)] == overlap:
                    # A reorder can share a one-row suffix by accident. Only
                    # append a tail whose occurrences were not already drawn.
                    if message_ids is not None:
                        previous_ids = {entry[0] for entry in self._messages}
                        if any(entry[0] in previous_ids for entry in signature[len(overlap):]):
                            continue
                    prefix = len(overlap)
                    break
            if not prefix:
                self.clear()
        groups = []
        limit = self.max_lines
        try:
            self.max_lines = None
            for body in messages[prefix:]:
                before = len(self.lines)
                self.write(body, scroll_end=False)
                groups.append(self.lines[before:])
                del self.lines[before:]
        finally:
            self.max_lines = limit
        inserted = sum(map(len, groups))
        self.lines = [line for group in reversed(groups) for line in group] + self.lines
        if limit is not None:
            self.lines = self.lines[:limit]
        self._start_line = 0
        self._line_cache.clear()
        from textual.geometry import Size
        self.virtual_size = Size(self.virtual_size.width, len(self.lines))
        self.refresh()
        self._messages = signature
        if follow:
            self.call_after_refresh(self.scroll_home, animate=False)
        else:
            target = previous_y + inserted if prefix else previous_y
            self.call_after_refresh(self.scroll_to, y=target, animate=False)

    def on_resize(self):
        # RichLog retains physical lines: rebuild them at the new width.
        self.clear()
        self._messages = ()
        self._source_key = None
        self.app.call_after_refresh(self.app._refresh_left_event_log, self.app.session.state)

    def on_mouse_scroll_up(self, event):
        event.stop()

    def on_mouse_scroll_down(self, event):
        event.stop()


class LeftEventLogMixin:
    def _left_event_log_enabled(self):
        return bool(self.config.get('left_event_log'))

    def _refresh_left_event_log(self, state):
        log = self.query_one('#left-event-log', LeftEventLog)
        want = (self._left_event_log_enabled() and not self.home_mode
                and self.panel_mode not in MAP_HIDDEN_PANEL_MODES
                and not state.run_over)
        # 每帧重设同样的 display 也会让 Textual 重新布局/合成；只在真变化时写。
        if log.display != want:
            log.display = want
        if log.display:
            visible_count = self._visible_game_message_count(state)
            history = state.messages
            language = self.config.get('language')
            actors = tuple((actor.label, actor.relation) for actor in state.enemies)
            source_key = (id(state), history.generation, history.revision,
                          visible_count, language, actors)
            if source_key == log._source_key:
                return
            start = max(0, visible_count-200)
            messages = history[start:visible_count]
            identities = [(history.generation, identity)
                          for identity in history.occurrence_ids[start:visible_count]]
            bodies, identities_out, cache = [], [], {}
            for index, message in enumerate(messages):
                if not str(message).strip():
                    continue
                matching_actors = tuple(actor for actor in actors if actor[0] in message)
                key = (message, language, matching_actors)
                body = log._body_cache.get(key)
                if body is None:
                    body = self._message_body_text(message)
                cache[key] = body
                bodies.append(body)
                identities_out.append(identities[index])
            log.set_messages(bodies, message_ids=identities_out)
            log._body_cache = cache
            log._source_key = source_key
