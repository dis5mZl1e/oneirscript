"""POSIX（Linux / macOS）桌面鼠标适配层：与 Windows 原生层**同一事件协议**。

两端分工（2026-09-21 定稿）：
- Windows：``windows_mouse.NativeMouseWindowsDriver``——Win32 控制台记录 →
  ``native_mouse_events()`` 翻译成 Textual 鼠标事件（左1/中2/右3）；
- POSIX：textual 的 ``LinuxDriver`` 自带 SGR（?1006h）+ 任意移动（?1003h）
  鼠标上报，XTerm 解析器产出的按键编号与 Win32 层同语义（左1/中2/右3），
  ctrl/shift/alt 修饰位也随事件携带——因此本适配层只做三件事：
    ① 经 ``mouse_protocol.normalize_to_game_semantics`` 出口对齐（防御性，
       恒等或 0 基→1 基）；
    ② ``_trace_native`` 追踪与 Windows 层同格式；
    ③ 保持父类的 termios / 信号 / 焦点协议原样（键位零改动）。

游戏逻辑（ui/input.py）不感知平台：两端事件进入 ``process_message`` 后
走完全相同的分发路径。
"""

from __future__ import annotations

from textual import events
from textual.drivers.linux_driver import LinuxDriver

from .mouse_protocol import normalize_to_game_semantics


def _trace_native(message: str) -> None:
    """与 windows_mouse._trace_native 同格式：DREAM_MOUSE_TRACE 环境变量开启。"""
    import os

    trace_path = os.environ.get("DREAM_MOUSE_TRACE")
    if not trace_path:
        return
    try:
        with open(trace_path, "a", encoding="utf-8") as stream:
            stream.write(message + "\n")
    except OSError:
        pass


class NativeMousePosixDriver(LinuxDriver):
    """Linux / macOS 桌面驱动：VT SGR 鼠标 → 游戏统一事件协议。"""

    def process_message(self, message) -> None:
        if isinstance(message, events.MouseEvent):
            message = normalize_to_game_semantics(message)
            _trace_native(
                f"dispatch {type(message).__name__} x={message.x} y={message.y} "
                f"screen=({message.screen_x},{message.screen_y}) button={message.button}"
            )
        super().process_message(message)
