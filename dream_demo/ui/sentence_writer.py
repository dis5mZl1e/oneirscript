"""Brief ASCII writing cursor, confined to one text widget; no simulation work."""
from __future__ import annotations
import time
import unicodedata
from rich.text import Text
from textual.widgets import Static


def graphemes(value: str) -> tuple[str, ...]:
    groups = []
    for char in value:
        attached = (unicodedata.combining(char) or '\ufe00' <= char <= '\ufe0f'
                    or char == '\u200d' or groups and groups[-1].endswith('\u200d'))
        if groups and attached:
            groups[-1] += char
        else:
            groups.append(char)
    return tuple(groups)


class SentenceWriter(Static):
    DEFAULT_CSS = """
    SentenceWriter { display: none; height: 4; padding: 0 1; overflow-y: auto;
                     color: #e4dbc7; border-left: solid #9b835b; }
    """
    DURATION = .60
    CURSORS = ('|', '/', '-', '\\')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_text = ''
        self.language = ''
        self.units = ()
        self.started = 0.0
        self.animation_timer = None
        self._frame_text = Text()
        # 着色片段 [(text, color|role)]：与 full_text 拼接等价；为空时退回单色。
        self._fragments: tuple[tuple[str, str], ...] = ()

    def _styled_fragments(self) -> tuple[tuple[str, str], ...]:
        """把片段的 role 解析成颜色；未知角色原样当样式用。"""
        from ..equipment.sentence_prose import ROLE_COLORS
        return tuple((text, ROLE_COLORS.get(role, role))
                     for text, role in self._fragments)

    def render(self):
        return self._frame_text

    def _finished_frame(self) -> Text:
        styled = self._styled_fragments()
        if not styled:
            return Text(self.full_text, style='#e4dbc7')
        text = Text()
        for fragment, color in styled:
            text.append(fragment, style=color or '#e4dbc7')
        return text

    def frame(self, elapsed: float) -> Text:
        if elapsed >= self.DURATION:
            return self._finished_frame()
        styled = self._styled_fragments()
        if not styled:
            count = min(len(self.units), int(len(self.units) * max(0, elapsed) / self.DURATION))
            text = Text(''.join(self.units[:count]), style='#e4dbc7')
            text.append(self.CURSORS[int(max(0, elapsed) / .05) % 4], style='bold #ffd166')
            return text
        # 多色逐字：按字素展开片段颜色，随动画进度上色。
        chars: list[tuple[str, str | None]] = []
        for fragment, color in styled:
            for unit in graphemes(fragment):
                chars.append((unit, color))
        count = min(len(chars), int(len(chars) * max(0, elapsed) / self.DURATION))
        text = Text()
        for unit, color in chars[:count]:
            text.append(unit, style=color or '#e4dbc7')
        text.append(self.CURSORS[int(max(0, elapsed) / .05) % 4], style='bold #ffd166')
        return text

    def write(self, sentence: str, *, animate: bool = True, force: bool = False,
              fragments: tuple[tuple[str, str], ...] = ()) -> None:
        if sentence == self.full_text and not force and fragments == self._fragments:
            return
        self.finish(update=False)
        self.full_text = sentence
        self._fragments = fragments
        from ..i18n import get_language
        self.language = get_language()
        self.units = graphemes(sentence)
        self.started = time.monotonic()
        self.styles.display = 'block' if sentence else 'none'
        self._frame_text = self.frame(0 if animate else self.DURATION)
        self.update(self._frame_text)
        if animate and sentence and self.is_mounted:
            self.animation_timer = self.set_interval(.05, self._tick)

    def _tick(self) -> None:
        elapsed = time.monotonic() - self.started
        if elapsed >= self.DURATION or any(not parent.display for parent in self.ancestors_with_self):
            self.finish()
            return
        self._frame_text = self.frame(elapsed)
        self.update(self._frame_text)

    def finish(self, *, update: bool = True) -> None:
        if self.animation_timer is not None:
            self.animation_timer.stop()
            self.animation_timer = None
        if update:
            self._frame_text = self._finished_frame()
            self.update(self._frame_text)

    def on_unmount(self):
        self.finish(update=False)

    def clear(self):
        self.finish(update=False)
        self.full_text, self.units, self._fragments = '', (), ()
        self._frame_text = Text()
        self.update(self._frame_text)
        self.display = False
