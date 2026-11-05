"""Interruptible animation deadlines without changing the process timer period."""
from __future__ import annotations

import math
import threading


class _PrecisionWake:
    """One worker owns wait/close; producers may set from any thread.

    High-resolution timers are available on Windows 10 1803 and later. Older
    Windows retains the ordinary interruptible event wait and its coarse timing.
    No periodic timer runs while the renderer is idle or hidden.
    """

    def __init__(self, *, kernel=None):
        import ctypes
        from ctypes import wintypes as wt
        self._kernel = kernel or ctypes.WinDLL('kernel32', use_last_error=True)
        self._lock = threading.Lock()
        self._event = self._timer = None
        api = self._kernel
        signatures = {
            'CreateEventW': ([ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR], wt.HANDLE),
            'CreateWaitableTimerExW': ([ctypes.c_void_p, wt.LPCWSTR, wt.DWORD, wt.DWORD], wt.HANDLE),
            'SetWaitableTimer': ([wt.HANDLE, ctypes.POINTER(ctypes.c_longlong), wt.LONG,
                                 ctypes.c_void_p, ctypes.c_void_p, wt.BOOL], wt.BOOL),
            'CancelWaitableTimer': ([wt.HANDLE], wt.BOOL),
            'SetEvent': ([wt.HANDLE], wt.BOOL),
            'ResetEvent': ([wt.HANDLE], wt.BOOL),
            'WaitForSingleObject': ([wt.HANDLE, wt.DWORD], wt.DWORD),
            'WaitForMultipleObjects': ([wt.DWORD, ctypes.POINTER(wt.HANDLE), wt.BOOL, wt.DWORD], wt.DWORD),
            'CloseHandle': ([wt.HANDLE], wt.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(api, name, None)
            if function is not None:
                function.argtypes, function.restype = args, result
        self._event = api.CreateEventW(None, True, False, None)
        if not self._event:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            create = getattr(api, 'CreateWaitableTimerExW', None)
            self._timer = create(None, None, 2, 0x1f0003) if create else None
        except Exception:
            self.close()
            raise

    @property
    def precise(self):
        return bool(self._timer)

    def set(self):
        with self._lock:
            if self._event:
                self._kernel.SetEvent(self._event)

    def clear(self):
        with self._lock:
            if self._event:
                self._kernel.ResetEvent(self._event)

    def wait(self, timeout, *, precise=False):
        import ctypes
        from ctypes import wintypes as wt
        api = self._kernel
        if precise and self._timer and timeout > 0:
            due = ctypes.c_longlong(-max(1, math.ceil(timeout * 10_000_000)))
            if not api.SetWaitableTimer(self._timer, ctypes.byref(due), 0, None, None, False):
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                handles = (wt.HANDLE * 2)(self._event, self._timer)
                result = api.WaitForMultipleObjects(2, handles, False, 0xffffffff)
            finally:
                api.CancelWaitableTimer(self._timer)
        else:
            result = api.WaitForSingleObject(self._event, max(0, math.ceil(timeout * 1000)))
        if result == 0xffffffff:
            raise ctypes.WinError(ctypes.get_last_error())
        return result == 0

    def close(self):
        with self._lock:
            if self._timer:
                self._kernel.CancelWaitableTimer(self._timer)
                self._kernel.CloseHandle(self._timer)
                self._timer = None
            if self._event:
                self._kernel.CloseHandle(self._event)
                self._event = None
