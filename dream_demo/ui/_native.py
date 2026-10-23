"""原生鼠标驱动的平台分发：两端不同中间层，同一事件协议与键位。

- win32：``windows_mouse.NativeMouseWindowsDriver``（Win32 控制台记录翻译层）；
- Linux / macOS：``posix_mouse.NativeMousePosixDriver``（textual SGR 鼠标适配层）；
- 其余平台：返回 ``None``，退回 textual 自动驱动（游戏逻辑零假设）。
"""

from __future__ import annotations

import sys
from typing import Any

if sys.platform == "win32":
    from ..windows_mouse import NativeMouseWindowsDriver, _trace_native
else:
    from ..posix_mouse import NativeMousePosixDriver, _trace_native

    NativeMouseWindowsDriver = NativeMousePosixDriver  # 兼容旧引用名


def select_mouse_driver() -> Any:
    """按平台返回鼠标驱动类；无法提供的平台返回 None（textual 自动选择）。"""
    if sys.platform == "win32":
        return NativeMouseWindowsDriver
    if sys.platform in ("linux", "darwin") or sys.platform.startswith("linux"):
        return NativeMousePosixDriver
    return None


__all__ = ["NativeMouseWindowsDriver", "select_mouse_driver", "_trace_native"]
