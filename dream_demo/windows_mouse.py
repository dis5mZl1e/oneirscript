from __future__ import annotations

import asyncio
from ctypes import Structure, byref, wintypes
import os
import sys
from threading import Event, Thread
from typing import Callable

from textual import constants, events
from textual._xterm_parser import XTermParser
from textual.drivers import win32
from textual.drivers._writer_thread import WriterThread
from textual.drivers.windows_driver import WindowsDriver
from textual.geometry import Size


MOUSE_MOVED = 0x0001
DOUBLE_CLICK = 0x0002
MOUSE_WHEELED = 0x0004
MOUSE_HWHEELED = 0x0008
SHIFT_PRESSED = 0x0010
CTRL_PRESSED = 0x0004 | 0x0008
ALT_PRESSED = 0x0001 | 0x0002
BUTTONS = ((0x0001, 1), (0x0004, 2), (0x0002, 3))
BUTTON_STATE_MASK = sum(mask for mask, _ in BUTTONS)
VK_MENU = 0x12


class _Coord(Structure):
    _fields_ = (("X", wintypes.SHORT), ("Y", wintypes.SHORT))


class _SmallRect(Structure):
    _fields_ = (
        ("Left", wintypes.SHORT),
        ("Top", wintypes.SHORT),
        ("Right", wintypes.SHORT),
        ("Bottom", wintypes.SHORT),
    )


class _ConsoleScreenBufferInfo(Structure):
    _fields_ = (
        ("dwSize", _Coord),
        ("dwCursorPosition", _Coord),
        ("wAttributes", wintypes.WORD),
        ("srWindow", _SmallRect),
        ("dwMaximumWindowSize", _Coord),
    )


def console_window_origin(output_handle) -> tuple[int, int]:
    """Return the visible console window origin in screen-buffer coordinates."""
    info = _ConsoleScreenBufferInfo()
    if not win32.KERNEL32.GetConsoleScreenBufferInfo(output_handle, byref(info)):
        return 0, 0
    return int(info.srWindow.Left), int(info.srWindow.Top)




def _trace_native(message: str) -> None:
    trace_path = os.environ.get("DREAM_MOUSE_TRACE")
    if not trace_path:
        return
    try:
        with open(trace_path, "a", encoding="utf-8") as stream:
            stream.write(message + "\n")
    except OSError:
        pass


def native_modifier_key_event(*, virtual_key_code: int, key_down: bool) -> events.Key | None:
    if key_down and virtual_key_code == VK_MENU:
        return events.Key("alt", None)
    return None


def native_alt_key_event(*, virtual_key: int, key_down: bool, control_state: int):
    """Native physical Alt+letter/digit; AltGr remains ordinary text input."""
    if (key_down and control_state & ALT_PRESSED and not control_state & CTRL_PRESSED
            and (0x41 <= virtual_key <= 0x5A or 0x30 <= virtual_key <= 0x39)):
        return events.Key('alt+' + chr(virtual_key).lower(), None)
    return None


CTRL_ARROW_KEYS = {
    "[1;5A": "ctrl+up",
    "[1;5B": "ctrl+down",
    "[1;5C": "ctrl+right",
    "[1;5D": "ctrl+left",
    # 2026-10-15：Alt+方向（同义缩放序列）——终端收不到 Ctrl 的迁移配套。
    "[1;3A": "alt+up",
    "[1;3B": "alt+down",
    "[1;3C": "alt+right",
    "[1;3D": "alt+left",
}


def key_record_should_feed(*, key_down: bool, unicode_char: str) -> bool:
    """按键记录是否应把字符喂给解析器。

    textual 原版条件在 ``dwControlKeyState`` 非零且 ``wVirtualKeyCode == 0``
    时整条丢弃——而 VT 输入模式下 Ctrl+方向键等组合序列正是以 VK==0、
    带控制状态的逐字符记录到达的，于是 Ctrl+↑/↓ 在真实 Windows 终端
    永远到不了解析器（缩放键失效的根因）。改为只看有没有实际字符：
    裸修饰键（uChar 为 NUL）自然丢弃，组合序列的每个字节都能通过。
    """
    return bool(key_down) and unicode_char != "\x00" and unicode_char.isascii()


def game_key_character(*, key_down: bool, unicode_char: str,
                       virtual_key: int, control_state: int) -> str:
    if not key_down:
        return ""
    if unicode_char != "\x00":
        return unicode_char if unicode_char.isascii() else ""
    # Some IMEs expose the physical key but omit its character. Recover only
    # plain English letter controls; composition commits (VK_PROCESSKEY) and
    # bare modifiers must never become gameplay commands.
    if 0x41 <= virtual_key <= 0x5A and not control_state & (CTRL_PRESSED | ALT_PRESSED):
        upper = bool(control_state & SHIFT_PRESSED) ^ bool(control_state & 0x0080)
        return chr(virtual_key if upper else virtual_key + 32)
    return ""


def classify_key_batch(chars: list[str]) -> tuple[str, str | None]:
    """判断一批按键字符是否需要拦截，原样交给解析器前先做翻译。

    终端（Windows Terminal / 启用 VT 输入的 conhost）对「按住 Alt + 任意键」
    发送 ESC 前缀序列（ESC 后紧跟该键字符），而裸 Alt 不发送任何内容；
    textual 的解析器会把 ESC+字符按超时拆成 escape + 字符两个键（escape 会
    误触保存退出），因此 Alt 组合在喂给解析器之前拦截，返回 ``("alt", None)``。

    Ctrl+方向键（``[1;5{A,B,C,D}``）是地图缩放的触发序列，直接翻译成
    对应键名返回 ``("key", "ctrl+up")`` 等——不依赖解析器与记录过滤的配合，
    保证在真实 Windows 终端上缩放键一定可达。其余返回 ``("keys", None)``
    原样交给解析器。
    """
    text = "".join(chars)
    # ⚠ 判断「是不是 Alt」**不能只看 ``chars[1] != "["``**（2026-09-16 修正）：
    # 小键盘在 **application keypad mode** 下发的是 ``ESC O <字母>``（第二个字符是
    # ``O`` 而不是 ``[``），例如小键盘 2 = ``\x1bOr``、小键盘回车 = ``\x1bOM``。
    # 旧条件 ``len(chars) >= 2 and chars[1] != "["`` 会把这些**整批当成 Alt 吞掉**——
    # 小键盘数字与小键盘回车因此全部失效，游戏侧再怎么改键位也毫无反应
    # （玩家反馈「小键盘没修复」的真正原因）。
    # 真正的 Alt 序列是 ``ESC`` + **单个**普通字符，长度**恰好 2**；
    # 长度 >= 3 的 ESC 序列（SS3 的 ``\x1bO…``、CSI 的 ``\x1b[…``）一律放行给解析器。
    if (len(chars) == 2 and chars[0] == "\x1b" and chars[1] != 'O'
            and chars[1].isascii() and chars[1].isalnum()):
        return "key", "alt+" + chars[1].lower()
    if len(chars) == 2 and chars[0] == '\x1b' and chars[1] not in ('[', 'O'):
        return 'alt', None  # Preserve the old safe suppression for unsupported combinations.
    if text in CTRL_ARROW_KEYS:
        return "key", CTRL_ARROW_KEYS[text]
    return "keys", None


def native_mouse_events(
    *,
    x: int,
    y: int,
    button_state: int,
    previous_button_state: int,
    event_flags: int,
    control_state: int,
    previous_position: tuple[int, int],
    window_origin: tuple[int, int] = (0, 0),
) -> list[events.MouseEvent]:
    """Translate Win32 console mouse records into Textual mouse events."""
    delta_x, delta_y = x - previous_position[0], y - previous_position[1]
    x -= window_origin[0]
    y -= window_origin[1]
    shift = bool(control_state & SHIFT_PRESSED)
    ctrl = bool(control_state & CTRL_PRESSED)
    alt = bool(control_state & ALT_PRESSED)

    def make(event_type: type[events.MouseEvent], button: int) -> events.MouseEvent:
        return event_type(None, x, y, delta_x, delta_y, button, shift, alt, ctrl, screen_x=x, screen_y=y)

    if event_flags & MOUSE_WHEELED:
        wheel_delta = wintypes.SHORT((button_state >> 16) & 0xFFFF).value
        event_type = events.MouseScrollUp if wheel_delta > 0 else events.MouseScrollDown
        return [make(event_type, 0)]
    if event_flags & MOUSE_HWHEELED:
        return []
    if event_flags & MOUSE_MOVED:
        button = next((number for mask, number in BUTTONS if button_state & mask), 0)
        return [make(events.MouseMove, button)]

    current = button_state & BUTTON_STATE_MASK
    previous = previous_button_state & BUTTON_STATE_MASK
    changed = current ^ previous
    translated: list[events.MouseEvent] = []
    for mask, button in BUTTONS:
        if changed & mask:
            translated.append(make(events.MouseDown if current & mask else events.MouseUp, button))
    if not translated and event_flags & DOUBLE_CLICK:
        button = next((number for mask, number in BUTTONS if current & mask), 1)
        translated.append(make(events.MouseDown, button))
    return translated


def _enable_application_mode_with_native_mouse() -> Callable[[], None]:
    terminal_in = sys.__stdin__
    terminal_out = sys.__stdout__
    original_input = win32.get_console_mode(terminal_in)
    original_output = win32.get_console_mode(terminal_out)

    def restore() -> None:
        win32.set_console_mode(terminal_in, original_input)
        win32.set_console_mode(terminal_out, original_output)

    win32.set_console_mode(
        terminal_out,
        original_output | win32.ENABLE_VIRTUAL_TERMINAL_PROCESSING,
    )
    input_mode = (
        win32.ENABLE_VIRTUAL_TERMINAL_INPUT
        | win32.ENABLE_MOUSE_INPUT
        | win32.ENABLE_WINDOW_INPUT
        | win32.ENABLE_EXTENDED_FLAGS
    )
    win32.set_console_mode(terminal_in, input_mode)
    return restore


class NativeMouseEventMonitor(Thread):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        app,
        exit_event: Event,
        process_event: Callable[[events.Event], None],
    ) -> None:
        super().__init__(name="dream-native-mouse-input")
        # 必须是守护线程：本线程的 run 阻塞在 ReadConsoleInputW 上，
        # 只有控制台真的来了输入才会返回。若不是守护线程，解释器退出时会
        # 一直等它 → 关掉窗口后进程仍然滞留（僵尸进程），既占着 exe 文件
        # 导致无法重新打包，也会继续持有存档文件，使下一次启动在写档时
        # 撞上占用而异常退出（表现为「一打开就闪退」）。
        self.daemon = True
        self.loop = loop
        self.app = app
        self.exit_event = exit_event
        self.process_event = process_event

    def run(self) -> None:
        parser = XTermParser(debug=constants.DEBUG)
        previous_buttons = 0
        previous_position = (0, 0)
        try:
            read_count = wintypes.DWORD(0)
            input_handle = win32.GetStdHandle(win32.STD_INPUT_HANDLE)
            output_handle = win32.GetStdHandle(win32.STD_OUTPUT_HANDLE)
            max_events = 1024
            records = (win32.INPUT_RECORD * max_events)()
            read_console_input = win32.KERNEL32.ReadConsoleInputW
            keys: list[str] = []

            while not self.exit_event.is_set():
                for event in parser.tick():
                    self.process_event(event)
                if win32.wait_for_handles([input_handle], 100) is None:
                    continue
                read_console_input(input_handle, byref(records), max_events, byref(read_count))
                keys.clear()
                new_size: tuple[int, int] | None = None
                for record in records[: read_count.value]:
                    _trace_native(f"record type={int(record.EventType):#06x}")
                    if record.EventType == 0x0001:
                        key_event = record.Event.KeyEvent
                        alt_event = native_alt_key_event(
                            virtual_key=int(key_event.wVirtualKeyCode), key_down=bool(key_event.bKeyDown),
                            control_state=int(key_event.dwControlKeyState))
                        if alt_event is not None and (not keys or keys[-1] != '\x1b'):
                            if keys:
                                for event in parser.feed(''.join(keys)):
                                    self.process_event(event)
                                keys.clear()
                            self.process_event(alt_event)
                            continue
                        modifier_event = native_modifier_key_event(
                            virtual_key_code=int(key_event.wVirtualKeyCode),
                            key_down=bool(key_event.bKeyDown),
                        )
                        if modifier_event is not None:
                            self.process_event(modifier_event)
                        else:
                            character = game_key_character(
                                key_down=bool(key_event.bKeyDown),
                                unicode_char=key_event.uChar.UnicodeChar,
                                virtual_key=int(key_event.wVirtualKeyCode),
                                control_state=int(key_event.dwControlKeyState),
                            )
                            if character:
                                keys.append(character)
                    elif record.EventType == 0x0002:
                        mouse = record.Event.MouseEvent
                        x, y = int(mouse.dwMousePosition.X), int(mouse.dwMousePosition.Y)
                        window_origin = console_window_origin(output_handle)
                        translated = native_mouse_events(
                            x=x,
                            y=y,
                            button_state=int(mouse.dwButtonState),
                            previous_button_state=previous_buttons,
                            event_flags=int(mouse.dwEventFlags),
                            control_state=int(mouse.dwControlKeyState),
                            previous_position=previous_position,
                            window_origin=window_origin,
                        )
                        _trace_native(
                            f"mouse x={x} y={y} buttons={int(mouse.dwButtonState):#010x} "
                            f"flags={int(mouse.dwEventFlags):#010x} window_origin={window_origin} translated="
                            f"{[(type(event).__name__, event.button) for event in translated]}"
                        )
                        for event in translated:
                            self.process_event(event)
                        previous_buttons = int(mouse.dwButtonState) & BUTTON_STATE_MASK
                        previous_position = (x, y)
                    elif record.EventType == 0x0004:
                        size = record.Event.WindowBufferSizeEvent.dwSize
                        new_size = (size.X, size.Y)
                if keys:
                    kind, payload = classify_key_batch(keys)
                    if kind == "alt":
                        # Alt 组合（ESC 前缀）：发出 alt 键并吞掉整个批次，
                        # 避免 textual 把它拆成 escape（会误触保存退出）+ 字符。
                        self.process_event(events.Key("alt", None))
                        keys.clear()
                        continue
                    if kind == "key":
                        # Ctrl+方向键：直接合成键事件（地图缩放触发器）。
                        self.process_event(events.Key(payload, None))
                        keys.clear()
                        continue
                    data = "".join(keys).encode("utf-16", "surrogatepass").decode("utf-16")
                    for event in parser.feed(data):
                        self.process_event(event)
                if new_size is not None:
                    size = Size(*new_size)
                    asyncio.run_coroutine_threadsafe(self.app._post_message(events.Resize(size, size)), self.loop)
        except Exception as error:
            self.app.log.error("WINDOWS INPUT MONITOR ERROR", error)


class NativeMouseWindowsDriver(WindowsDriver):
    """Textual Windows driver with classic PowerShell mouse-record support."""

    def start_application_mode(self) -> None:
        loop = asyncio.get_running_loop()
        self._restore_console = _enable_application_mode_with_native_mouse()
        self._writer_thread = WriterThread(self._file)
        self._writer_thread.start()
        self.write("\x1b[?1049h")
        self._enable_mouse_support()
        self.write("\x1b[?25l\x1b[?1003h\x1b[?1004h")
        self.flush()
        self._enable_bracketed_paste()
        self._event_thread = NativeMouseEventMonitor(
            loop,
            self._app,
            self.exit_event,
            self.process_message,
        )
        self._event_thread.start()
        from .windows_ime import GameImeGuard
        self._ime_guard = GameImeGuard(lambda: self._app.title)
        self._ime_guard.tick()
        self._ime_timer = self._app.set_interval(0.05, self._ime_guard.tick)

    def stop_application_mode(self) -> None:
        timer = getattr(self, "_ime_timer", None)
        if timer is not None:
            timer.stop()
        guard = getattr(self, "_ime_guard", None)
        if guard is not None:
            guard.close()
        super().stop_application_mode()

    def process_message(self, message) -> None:
        if isinstance(message, events.MouseEvent):
            _trace_native(
                f"dispatch {type(message).__name__} x={message.x} y={message.y} "
                f"screen=({message.screen_x},{message.screen_y}) button={message.button}"
            )
        super().process_message(message)
