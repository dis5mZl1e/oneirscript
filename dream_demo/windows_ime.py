"""Temporarily close IME composition in the focused game terminal only."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import os


class GameImeGuard:
    def __init__(self, title):
        self.title = title
        self.saved = {}
        self.user = None
        if sys.platform != "win32":
            return
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.imm = ctypes.WinDLL("imm32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
        self.kernel.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
        old_title = ctypes.create_unicode_buffer(1024)
        self.kernel.GetConsoleTitleW(old_title, len(old_title))
        self.original_title = old_title.value
        self.marker = f"梦层 · {os.getpid()}"
        self.kernel.SetConsoleTitleW(self.marker)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.imm.ImmGetDefaultIMEWnd.argtypes = [wintypes.HWND]
        self.imm.ImmGetDefaultIMEWnd.restype = wintypes.HWND
        self.user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
            ctypes.POINTER(ctypes.c_size_t)]
        self.user.SendMessageTimeoutW.restype = wintypes.LPARAM

    def _status(self, window, command, value=0):
        result = ctypes.c_size_t()
        # Bound cross-process calls: a frozen terminal must not freeze the game.
        ok = self.user.SendMessageTimeoutW(window, 0x0283, command, value,
                                          0x0002, 30, ctypes.byref(result))
        return result.value if ok else None

    def tick(self):
        if self.user is None:
            return
        foreground = self.user.GetForegroundWindow()
        text = ctypes.create_unicode_buffer(512)
        self.user.GetWindowTextW(foreground, text, len(text))
        title = self.marker
        # GetConsoleWindow is an invisible proxy under Windows Terminal. Use
        # the foreground host, but only while it displays our application title.
        if not title or title not in text.value:
            self.restore()
            return
        ime = self.imm.ImmGetDefaultIMEWnd(foreground)
        if not ime:
            return
        for old in list(self.saved):
            if old != ime:
                self._status(old, 6, self.saved.pop(old))
        status = self._status(ime, 5)  # IMC_GETOPENSTATUS
        if status is None:
            return
        self.saved.setdefault(ime, int(bool(status)))
        if status:
            self._status(ime, 6, 0)  # IMC_SETOPENSTATUS: ASCII mode

    def restore(self):
        for window, status in self.saved.items():
            self._status(window, 6, status)
        self.saved.clear()

    def close(self):
        self.restore()
        if self.user is not None:
            self.kernel.SetConsoleTitleW(self.original_title)
