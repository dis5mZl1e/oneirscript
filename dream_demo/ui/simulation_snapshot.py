"""Explicit P6 client: only immutable worker snapshots cross the UI boundary."""
from __future__ import annotations

from array import array
from collections import deque
from concurrent.futures import Future
import queue
import shlex
import time

from rich.text import Text
from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import Footer, Header, Input, Static


class SnapshotReady(Message):
    """Thread-safe wake-up; no mutable state payload crosses this message."""


def parse_command(text: str) -> tuple[str, tuple[int, ...], str | None]:
    """Parse an explicit command without eval or arbitrary object construction."""
    words = shlex.split(text)
    if not words or not words[0].isidentifier() or words[0].startswith('_'):
        raise ValueError('请输入行动名称及整数参数。')
    choice = None
    if '--choice' in words:
        position = words.index('--choice')
        if position != len(words) - 2:
            raise ValueError('--choice 后需要一个选项。')
        choice = words[-1]
        words = words[:position]
    try:
        arguments = tuple(int(value) for value in words[1:])
    except ValueError as error:
        raise ValueError('行动参数必须是整数。') from error
    arity = {'move': 2, 'fire': 2, 'open': 2, 'wait': 0, 'interact': 0,
             'pickup': 0, 'descend': 0, 'choose_npc_option': 1,
             'choose_event_option': 1, 'container_fill': 1, 'container_pour': 1}
    if words[0] in arity and len(arguments) != arity[words[0]]:
        raise ValueError(f'{words[0]} 需要 {arity[words[0]]} 个整数参数。')
    return words[0], arguments, choice


def material_values(snapshot, name):
    field = next(field for field in snapshot.materials if field.name == name)
    values = array(field.typecode)
    values.frombytes(b''.join(field.pages))
    return values


def render_snapshot(snapshot, width: int, height: int, positions=None) -> Text:
    """Render visible material facts; never call a GameState method on the UI."""
    player = snapshot.entities[0]
    columns = min(snapshot.width, max(1, width // 2))
    rows = min(snapshot.height, max(1, height))
    left = max(0, min(player.x - columns // 2, snapshot.width - columns))
    top = max(0, min(player.y - rows // 2, snapshot.height - rows))
    values = {name: material_values(snapshot, name)
              for name in ('solid', 'height', 'liquid', 'gas', 'flame', 'plant')}
    positions = positions or {entity.id: (entity.x, entity.y) for entity in snapshot.entities}
    entities = {(round(positions[entity.id][0]), round(positions[entity.id][1])): entity
                for entity in snapshot.entities}
    player_position = tuple(round(value) for value in positions[player.id])
    text = Text()
    for y in range(top, top + rows):
        for x in range(left, left + columns):
            index = y * snapshot.width + x
            if not snapshot.visibility[index] and (x, y) != (player.x, player.y):
                glyph, style = ' ', 'dim'
            elif (x, y) == player_position:
                glyph, style = '@', 'bold bright_white'
            elif (x, y) in entities:
                glyph, style = 'E', 'bright_red'
            elif values['flame'][index]:
                glyph, style = '*', 'bright_red'
            elif values['solid'][index]:
                glyph, style = ('#' if values['height'][index] > 1 else '='), 'white'
            elif values['liquid'][index]:
                glyph, style = '~', 'bright_blue'
            elif values['gas'][index]:
                glyph, style = ':', 'cyan'
            elif values['plant'][index]:
                glyph, style = '%', 'green'
            else:
                glyph, style = '.', 'dim'
            text.append(glyph + ' ', style=style)
        if y + 1 < top + rows:
            text.append('\n')
    return text


class SnapshotApp(App):
    """Small opt-in client, deliberately independent of the mutable legacy UI."""

    CSS = '''
    #snapshot-map { height: 1fr; overflow: hidden; }
    #snapshot-status { height: 2; }
    #snapshot-messages { height: 5; }
    #snapshot-feedback { height: 1; }
    Input { dock: bottom; }
    '''
    BINDINGS = [('q', 'quit', '保存退出'), ('ctrl+s', 'save', '保存')]

    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self._pending: deque[tuple[Future, float]] = deque()
        self._save_pending: deque[Future] = deque()
        self._snapshot = None
        self._previous_snapshot = None
        self._draw_key = None
        self.input_to_frame_ms: list[float] = []
        self.queue_rejections = 0
        self.coalesced_completions = 0
        self.presented_commands = 0
        self.failed_commands = 0

    @property
    def pending_count(self):
        return len(self._pending)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id='snapshot-status')
        yield Static(id='snapshot-map')
        yield Static(id='snapshot-messages')
        yield Static('方向键移动；空格等待；i 交互；g 拾取；Enter 输入行动。', id='snapshot-feedback')
        yield Input(placeholder='行动，例如 fire 1 0；Esc 返回地图', id='snapshot-command')
        yield Footer()

    def on_mount(self):
        self.query_one(Input).display = False
        self.set_interval(1 / 30, self._poll_snapshot)
        self.worker.ready.add_done_callback(self._notify_ready)

    def _notify_ready(self, _future):
        # post_message is thread-safe and does not wait for the UI loop.
        self.post_message(SnapshotReady())

    def on_snapshot_ready(self, _event):
        self._poll_snapshot()

    def submit_command(self, command, *args, choice=None):
        started = time.perf_counter()
        try:
            future = self.worker.submit(command, *args, choice=choice)
        except queue.Full:
            self.queue_rejections += 1
            self.query_one('#snapshot-feedback', Static).update('行动队列已满，请稍候。')
            return False
        except Exception as error:
            self.query_one('#snapshot-feedback', Static).update(str(error))
            return False
        self._pending.append((future, started))
        future.add_done_callback(self._notify_ready)
        return True

    def on_key(self, event):
        entry = self.query_one(Input)
        if entry.display:
            if event.key == 'escape':
                entry.display = False
                entry.blur()
                event.stop()
            return
        directions = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
        if event.key in directions:
            self.submit_command('move', *directions[event.key])
        elif event.key == 'space':
            self.submit_command('wait')
        elif event.key == 'i':
            self.submit_command('interact')
        elif event.key == 'g':
            self.submit_command('pickup')
        elif event.key == 'enter':
            entry.display = True
            entry.focus()
        else:
            return
        event.prevent_default()
        event.stop()

    def on_input_submitted(self, event: Input.Submitted):
        try:
            command, arguments, choice = parse_command(event.value)
        except ValueError as error:
            self.query_one('#snapshot-feedback', Static).update(str(error))
            return
        self.submit_command(command, *arguments, choice=choice)
        event.input.value = ''
        event.input.display = False
        event.input.blur()

    def _poll_snapshot(self):
        if self._snapshot is None and self.worker.ready.done():
            try:
                self._snapshot = self.worker.ready.result()
            except Exception as error:
                self.query_one('#snapshot-feedback', Static).update(f'模拟启动失败：{error}')
        while self._save_pending and self._save_pending[0].done():
            try:
                self._save_pending.popleft().result()
                self.query_one('#snapshot-feedback', Static).update('已保存。')
            except Exception as error:
                self.query_one('#snapshot-feedback', Static).update(f'保存失败：{error}')
        presented_at = None
        ready_count = 0
        while self._pending and self._pending[0][0].done():
            future, submitted_at = self._pending.popleft()
            try:
                completion = future.result()
                self._previous_snapshot = self._snapshot
                self._snapshot = completion.snapshot
                self.query_one('#snapshot-feedback', Static).update(completion.result.message or '')
                presented_at = submitted_at
                ready_count += 1
            except Exception as error:
                self.failed_commands += 1
                self.query_one('#snapshot-feedback', Static).update(f'行动失败：{error}')
        if presented_at is not None:
            self.coalesced_completions += ready_count - 1
            self.call_after_refresh(self._record_presented, presented_at)
        snapshot = self._snapshot
        if snapshot is None:
            return
        alpha = min(1.0, max(0.0, (time.perf_counter() - snapshot.published_at) / .11))
        key = snapshot.sequence, self.size, round(alpha * 30)
        if key == self._draw_key:
            return
        self._draw_key = key
        positions = None
        if self._previous_snapshot is not None:
            from ..simulation_worker import interpolate_entities
            positions = dict(interpolate_entities(self._previous_snapshot, snapshot, alpha))
        self.query_one('#snapshot-map', Static).update(
            render_snapshot(snapshot, self.size.width, max(1, self.size.height - 12), positions))
        self.query_one('#snapshot-status', Static).update(Text(
            f'层 {snapshot.depth}  时间 {snapshot.world_time}  '
            + '  '.join(f'{key}: {value}' for key, value in snapshot.status)))
        self.query_one('#snapshot-messages', Static).update(Text('\n'.join(snapshot.messages[-5:])))

    def _record_presented(self, submitted_at):
        self.presented_commands += 1
        self.input_to_frame_ms.append((time.perf_counter() - submitted_at) * 1000)
        # Keep diagnostics bounded in a long-running client too.
        if len(self.input_to_frame_ms) > 4096:
            del self.input_to_frame_ms[:2048]

    def action_save(self):
        try:
            future = self.worker.save()
            self._save_pending.append(future)
            future.add_done_callback(self._notify_ready)
        except Exception as error:
            self.query_one('#snapshot-feedback', Static).update(f'保存失败：{error}')

    async def action_quit(self):
        # Disk flushing and draining may block; keep the UI event loop free.
        import asyncio
        try:
            await asyncio.to_thread(self.worker.close, save=True)
        except Exception as error:
            self.query_one('#snapshot-feedback', Static).update(f'保存失败：{error}')
            self.exit(return_code=1)
            return
        self.exit()
