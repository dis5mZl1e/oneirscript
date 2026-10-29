"""Windows 实验地图图像层；文字/输入仍由原终端处理，始终只保留最新帧。"""
from __future__ import annotations

from collections import deque
import threading
import time


def _find_owner(owner_file=None):
    """只选择显式 QA 句柄或本进程祖先中的 WezTerm，绝不覆盖任意前台应用。"""
    import os
    import win32gui
    import win32process
    if owner_file:
        from pathlib import Path
        try:
            hwnd = int(Path(owner_file).read_text(encoding='utf8').strip())
            name = win32gui.GetClassName(hwnd).lower()
            if 'wezterm' in name or name.startswith(('oneirscriptholdqa', 'oneirscriptplaneprobe')):
                return hwnd
        except (OSError, ValueError):
            return None
        return None
    import ctypes
    from ctypes import wintypes as wt
    class Entry(ctypes.Structure):
        _fields_ = [('size', wt.DWORD), ('usage', wt.DWORD), ('pid', wt.DWORD),
                    ('heap', ctypes.c_size_t), ('module', wt.DWORD), ('threads', wt.DWORD),
                    ('parent', wt.DWORD), ('priority', wt.LONG), ('flags', wt.DWORD),
                    ('exe', wt.WCHAR*260)]
    kernel = ctypes.windll.kernel32
    kernel.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wt.HANDLE
    kernel.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    parents = {}
    try:
        entry = Entry()
        entry.size = ctypes.sizeof(Entry)
        okay = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while okay:
            parents[entry.pid] = (entry.parent, entry.exe.lower())
            okay = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    pid, ancestors = os.getpid(), set()
    seen = set()
    while pid in parents and pid not in seen:
        seen.add(pid)
        parent, executable = parents[pid]
        if 'wezterm' in executable:
            ancestors.add(pid)
        pid = parent
    found = []
    def collect(hwnd, _):
        if win32process.GetWindowThreadProcessId(hwnd)[1] in ancestors and win32gui.IsWindowVisible(hwnd):
            found.append(hwnd)
    win32gui.EnumWindows(collect, None)
    return found[-1] if len(found) == 1 else None


def _owner_should_show(foreground, owner, *, iconic=False, visible=True,
                       enabled=True, root=None):
    """终端窗口是否可以露出地图图像层。

    关闭窗口时系统/终端会弹确认框：那是一个新的前台窗口（或让终端窗口失焦/
    禁用）。此时地图层必须收起，否则它会作为终端的 owned popup 一直盖在
    提示框上面——玩家看到“提示出现了，地图还留着”。只在终端本身真正位于
    前台（或前台是它的子窗口）时显示。
    """
    if iconic or not visible or not enabled or not foreground:
        return False
    return int(foreground) == int(owner) or int(root or 0) == int(owner)



class _NativeImagePlaneRenderer:
    """终端所属的不可激活、鼠标穿透窗口，由专用线程维护 GDI/DWM 资源。"""

    def __init__(self, owner, *, trace=False):
        self.owner = int(owner)
        self.error = ''
        self.metrics = deque(maxlen=1200)
        self.trace = deque(maxlen=900) if trace else None
        self._pending = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name='native-map-plane', daemon=True)
        self._thread.start()
        if not self._ready.wait(3):
            self.close()
            raise RuntimeError('native map plane startup timed out')
        if self.error:
            raise RuntimeError(self.error)

    def present(self, image, client_box, rectangles, *, scene=None):
        """提交物理客户区框与相对可见矩形；被新帧替换的旧帧不会排队播放。"""
        if self.error or self._stop.is_set():
            return False
        if not self._thread.is_alive():
            self.error = 'native map plane thread ended'
            return False
        enqueued = time.perf_counter_ns()
        from PIL import Image
        x0, y0, x1, y1 = map(round, client_box)
        size = (x1-x0, y1-y0)
        if min(size) <= 0:
            self.hide()
            return False
        if image.size != size:
            if scene is None:
                image = image.resize(size, Image.Resampling.BILINEAR)
        # 输入图像可能随后被场景缓存复用；跨线程传独立不可变 BGRA 数据。
        payload = image.copy() if scene is None else None
        if scene is not None:
            scene = {**scene, 'viewport_size': image.size}
        with self._lock:
            self._pending = (payload, size, (x0, y0), tuple(rectangles), enqueued, scene)
        self._wake.set()
        return True

    def hide(self):
        with self._lock:
            self._pending = False
        self._wake.set()

    def close(self):
        self._stop.set()
        self._wake.set()
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        import ctypes
        from ctypes import wintypes as wt
        import win32api
        import win32con as wc
        import win32gui as wg

        class Header(ctypes.Structure):
            _fields_ = [('size', wt.DWORD), ('width', wt.LONG), ('height', wt.LONG),
                        ('planes', wt.WORD), ('bits', wt.WORD), ('compression', wt.DWORD),
                        ('image_size', wt.DWORD), ('xp', wt.LONG), ('yp', wt.LONG),
                        ('used', wt.DWORD), ('important', wt.DWORD)]

        class Blend(ctypes.Structure):
            _fields_ = [('op', wt.BYTE), ('flags', wt.BYTE),
                        ('alpha', wt.BYTE), ('format', wt.BYTE)]

        user32, gdi = ctypes.windll.user32, ctypes.windll.gdi32
        try:
            user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        except AttributeError:
            pass
        user32.GetDC.argtypes = [wt.HWND]
        user32.GetDC.restype = wt.HDC
        user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
        gdi.CreateCompatibleDC.argtypes = [wt.HDC]
        gdi.CreateCompatibleDC.restype = wt.HDC
        gdi.CreateDIBSection.argtypes = [wt.HDC, ctypes.POINTER(Header), wt.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD]
        gdi.CreateDIBSection.restype = wt.HANDLE
        gdi.SelectObject.argtypes = [wt.HDC, wt.HANDLE]
        gdi.SelectObject.restype = wt.HANDLE
        gdi.DeleteObject.argtypes = [wt.HANDLE]
        gdi.DeleteDC.argtypes = [wt.HDC]
        user32.UpdateLayeredWindow.argtypes = [wt.HWND, wt.HDC, ctypes.POINTER(wt.POINT),
                                              ctypes.POINTER(wt.SIZE), wt.HDC,
                                              ctypes.POINTER(wt.POINT), wt.COLORREF,
                                              ctypes.POINTER(Blend), wt.DWORD]
        user32.UpdateLayeredWindow.restype = wt.BOOL
        gdi.BitBlt.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              wt.HDC, ctypes.c_int, ctypes.c_int, wt.DWORD]
        gdi.BitBlt.restype = wt.BOOL
        alpha_blend = ctypes.windll.msimg32.AlphaBlend
        alpha_blend.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.DWORD]
        alpha_blend.restype = wt.BOOL
        hwnd = dc = bitmap = old_bitmap = None
        source_contexts = {}

        def upload(name, image, bpp):
            from PIL import Image, ImageChops
            width, height = image.size
            stride = (width*(bpp//8)+3)//4*4
            context = source_contexts.get(name)
            if context is None or context[0] != (width, height, bpp):
                if context:
                    _key, source_dc, source_bitmap, source_old, _bits = context
                    gdi.SelectObject(source_dc, source_old)
                    gdi.DeleteObject(source_bitmap)
                    gdi.DeleteDC(source_dc)
                source_dc = gdi.CreateCompatibleDC(None)
                source_bits = ctypes.c_void_p()
                header = Header(ctypes.sizeof(Header), width, -height, 1, bpp,
                                0, stride*height, 0, 0, 0, 0)
                source_bitmap = gdi.CreateDIBSection(source_dc, ctypes.byref(header), 0,
                                                    ctypes.byref(source_bits), None, 0)
                if not source_bitmap:
                    raise ctypes.WinError()
                source_old = gdi.SelectObject(source_dc, source_bitmap)
                context = source_contexts[name] = ((width, height, bpp), source_dc,
                                                   source_bitmap, source_old, source_bits)
            if bpp == 32:
                r, green, blue, alpha = image.convert('RGBA').split()
                image = Image.merge('RGBA', (ImageChops.multiply(r, alpha),
                                             ImageChops.multiply(green, alpha),
                                             ImageChops.multiply(blue, alpha), alpha))
                payload = image.tobytes('raw', 'BGRA')
            else:
                payload = image.tobytes('raw', 'BGR', stride, 1)
            ctypes.memmove(context[4], payload, len(payload))
            return context[1]
        instance = win32api.GetModuleHandle(None)
        class_name = 'OneirscriptNativeMapPlane-' + str(id(self))
        registered = False
        try:
            def procedure(window, message, wp, lp):
                if message == wc.WM_NCHITTEST:
                    return wc.HTTRANSPARENT
                if message == wc.WM_MOUSEACTIVATE:
                    return wc.MA_NOACTIVATE
                if message == wc.WM_ERASEBKGND:
                    return 1
                return wg.DefWindowProc(window, message, wp, lp)
            window_class = wg.WNDCLASS()
            window_class.hInstance, window_class.lpszClassName = instance, class_name
            window_class.lpfnWndProc = procedure
            wg.RegisterClass(window_class)
            registered = True
            hwnd = wg.CreateWindowEx(
                wc.WS_EX_LAYERED | wc.WS_EX_TRANSPARENT | wc.WS_EX_NOACTIVATE | wc.WS_EX_TOOLWINDOW,
                class_name, '', wc.WS_POPUP, 0, 0, 1, 1, self.owner, 0, instance, None)
            dc = gdi.CreateCompatibleDC(None)
            from ._native_map_scene import _PlaneMotion, _compose_frame
            motion = _PlaneMotion()
            self._ready.set()
            current_size = None
            frame = None
            previous_origin = previous_clip = None
            hidden = True
            needs_final = False
            next_present = 0.
            while not self._stop.is_set() and wg.IsWindow(self.owner):
                if wg.PumpWaitingMessages():
                    break
                with self._lock:
                    update, self._pending = self._pending, None
                if update is False:
                    frame = None
                    wg.ShowWindow(hwnd, wc.SW_HIDE)
                    hidden = True
                elif update is not None:
                    frame = update
                    packet = frame[5]
                    if packet is not None:
                        motion.update(packet['layer'], packet['player'], packet['camera'],
                                      packet['cell_px'], time.perf_counter(),
                                      packet['duration'], packet['animate'])
                        needs_final = motion.active(time.perf_counter())
                    else:
                        motion = _PlaneMotion()
                        needs_final = False
                if frame is not None:
                    foreground = wg.GetForegroundWindow()
                    root = wg.GetAncestor(foreground, wc.GA_ROOT) if foreground else 0
                    if not _owner_should_show(
                            foreground, self.owner,
                            iconic=bool(wg.IsIconic(self.owner)),
                            visible=bool(wg.IsWindowVisible(self.owner)),
                            enabled=bool(wg.IsWindowEnabled(self.owner)),
                            root=root):
                        wg.ShowWindow(hwnd, wc.SW_HIDE)
                        hidden = True
                    else:
                        image, size, offset, clip, enqueued, packet = frame
                        origin = wg.ClientToScreen(self.owner, offset)
                        now = time.perf_counter()
                        sampled = packet is not None and motion.active(now)
                        if update is not None or origin != previous_origin or hidden or ((sampled or needs_final) and now >= next_present):
                            started = time.perf_counter_ns()
                            stride = (size[0]*3+3)//4*4
                            if size != current_size:
                                if bitmap:
                                    gdi.SelectObject(dc, old_bitmap)
                                    gdi.DeleteObject(bitmap)
                                header = Header(ctypes.sizeof(Header), size[0], -size[1], 1, 24,
                                                0, stride*size[1], 0, 0, 0, 0)
                                bits = ctypes.c_void_p()
                                bitmap = gdi.CreateDIBSection(dc, ctypes.byref(header), 0,
                                                              ctypes.byref(bits), None, 0)
                                if not bitmap:
                                    raise ctypes.WinError()
                                old_bitmap = gdi.SelectObject(dc, bitmap)
                                current_size = size
                            player = camera = None
                            if packet is not None:
                                player, camera = motion.sample(now)
                                left = round((camera[0]-packet['origin'][0])*packet['cell_px'][0])
                                top = round((camera[1]-packet['origin'][1])*packet['cell_px'][1])
                                can_blit = (packet['viewport_size'] == size and left >= 0 and top >= 0
                                            and left+size[0] <= packet['canvas'].width
                                            and top+size[1] <= packet['canvas'].height)
                                if can_blit:
                                    if update is not None or 'canvas' not in source_contexts:
                                        upload('canvas', packet['canvas'], 24)
                                        upload('sprite', packet['sprite'], 32)
                                        if packet.get('text_overlay') is not None:
                                            upload('text_overlay', packet['text_overlay'], 32)
                                    if not gdi.BitBlt(dc, 0, 0, *size, source_contexts['canvas'][1], left, top, wc.SRCCOPY):
                                        raise ctypes.WinError()
                                    px = round((player[0]-camera[0])*packet['cell_px'][0])
                                    py = round((player[1]-camera[1])*packet['cell_px'][1])
                                    sw, sh = packet['sprite'].size
                                    if not alpha_blend(dc, px, py, sw, sh, source_contexts['sprite'][1],
                                                       0, 0, sw, sh, 0x01ff0000):
                                        raise ctypes.WinError()
                                    overlay = packet.get('text_overlay')
                                    if overlay is not None and not alpha_blend(
                                            dc, 0, 0, *size, source_contexts['text_overlay'][1],
                                            0, 0, *overlay.size, 0x01ff0000):
                                        raise ctypes.WinError()
                                    image = None
                                else:
                                    try:
                                        image = _compose_frame(packet['canvas'], packet['origin'],
                                                               packet['sprite'], packet['cell_px'],
                                                               player, camera, packet['viewport_size'])
                                    except ValueError:
                                        motion.update(packet['layer'], packet['player'], packet['camera'],
                                                      packet['cell_px'], now, 0., False)
                                        player, camera = motion.sample(now)
                                        image = _compose_frame(packet['canvas'], packet['origin'],
                                                               packet['sprite'], packet['cell_px'],
                                                               player, camera, packet['viewport_size'])
                                    if image.size != size:
                                        from PIL import Image
                                        image = image.resize(size, Image.Resampling.BILINEAR)
                                    overlay = packet.get('text_overlay')
                                    if overlay is not None:
                                        from PIL import Image
                                        if overlay.size != size:
                                            overlay = overlay.resize(size, Image.Resampling.BILINEAR)
                                        image = image.convert('RGBA')
                                        image.alpha_composite(overlay)
                            if image is not None:
                                if image.mode != 'RGB':
                                    image = image.convert('RGB')
                                payload = image.tobytes('raw', 'BGR', stride, 1)
                                ctypes.memmove(bits, payload, len(payload))
                            prepared = time.perf_counter_ns()
                            target, extent, source = wt.POINT(*origin), wt.SIZE(*size), wt.POINT(0, 0)
                            blend = Blend(0, 0, 255, 0)
                            if not user32.UpdateLayeredWindow(hwnd, None, ctypes.byref(target),
                                                             ctypes.byref(extent), dc,
                                                             ctypes.byref(source), 0,
                                                             ctypes.byref(blend), 4):
                                raise ctypes.WinError()
                            if clip != previous_clip:
                                region = wg.CreateRectRgnIndirect((0, 0, 0, 0))
                                for x, y, width, height in clip:
                                    part = wg.CreateRectRgnIndirect((round(x), round(y), round(x+width), round(y+height)))
                                    wg.CombineRgn(region, region, part, wc.RGN_OR)
                                    wg.DeleteObject(part)
                                wg.SetWindowRgn(hwnd, region, False)
                                previous_clip = clip
                            wg.ShowWindow(hwnd, wc.SW_SHOWNOACTIVATE)
                            finished = time.perf_counter_ns()
                            timestamp = time.time_ns()
                            self.metrics.append({'t_ns': timestamp,
                                                 'present_ms': (finished-prepared)/1e6,
                                                 'compose_ms': (prepared-started)/1e6,
                                                 'total_ms': (finished-(enqueued if update is not None else started))/1e6,
                                                 'queue_ms': max(0., (started-enqueued)/1e6) if update is not None else 0.,
                                                 'position': player, 'camera': camera, 'size': size})
                            if self.trace is not None and player is not None:
                                import math
                                if image is None:
                                    from PIL import Image
                                    image = Image.frombytes('RGB', size, ctypes.string_at(bits, stride*size[1]),
                                                            'raw', 'BGR', stride, 1)
                                sx = packet['cell_px'][0]*size[0]/packet['viewport_size'][0]
                                sy = packet['cell_px'][1]*size[1]/packet['viewport_size'][1]
                                px, py = player[0]-camera[0], player[1]-camera[1]
                                box = (max(0, math.floor((px-.15)*sx)), max(0, math.floor((py-.15)*sy)),
                                       min(size[0], math.ceil((px+1.15)*sx)), min(size[1], math.ceil((py+1.15)*sy)))
                                if box[2] > box[0] and box[3] > box[1]:
                                    from PIL import Image
                                    self.trace.append(({'t_ns': timestamp, 'position': list(player),
                                                        'box': list(box), 'image_size': list(size)},
                                                       image.crop(box), image.resize((96, 112), Image.Resampling.NEAREST)))
                            previous_origin = origin
                            next_present = now+1/60
                            needs_final = sampled
                            hidden = False
                if frame is not None and frame[5] is not None and motion.active(time.perf_counter()):
                    # Present is capped at 60Hz below. Polling every 5ms wakes
                    # this worker about 200 times per second to discover that
                    # most frames are still early; sleep until the next slot,
                    # while the event still wakes immediately for a new packet.
                    delay = max(.001, min(.02, next_present - time.perf_counter()))
                else:
                    delay = .02
                self._wake.wait(delay)
                self._wake.clear()
        except Exception as error:
            self.error = repr(error)
        finally:
            self._ready.set()
            if hwnd and wg.IsWindow(hwnd):
                wg.DestroyWindow(hwnd)
            if bitmap:
                gdi.SelectObject(dc, old_bitmap)
                gdi.DeleteObject(bitmap)
            if dc:
                gdi.DeleteDC(dc)
            for _key, source_dc, source_bitmap, source_old, _bits in source_contexts.values():
                gdi.SelectObject(source_dc, source_old)
                gdi.DeleteObject(source_bitmap)
                gdi.DeleteDC(source_dc)
            if registered:
                wg.UnregisterClass(class_name, instance)


class _NativeImagePlane:
    """独立呈现进程的代理；共享内存为单槽，控制命令与帧都不会积压。"""

    def __init__(self, owner, *, trace=False):
        import json
        import mmap
        import os
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        from ._native_plane_ipc import _CAPACITY
        self.owner = int(owner)
        self._error, self._sequence, self._closed = '', 0, False
        self._report = {}
        self._temporary = tempfile.TemporaryDirectory(prefix='oneirscript-map-plane-')
        self._directory = Path(self._temporary.name)
        self._stream = (self._directory / 'frames.bin').open('w+b')
        self._stream.truncate(_CAPACITY)
        self._memory = mmap.mmap(self._stream.fileno(), _CAPACITY)
        self._log = (self._directory / 'worker.log').open('wb')
        arguments = [str(self._directory), str(owner), str(int(trace)), str(os.getpid())]
        command = ([sys.executable, '--native-map-worker', *arguments]
                   if getattr(sys, 'frozen', False) else
                   [sys.executable, '-X', 'utf8', '-m', 'dream_demo.ui._native_plane_worker', *arguments])
        self._worker = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2],
                                        stdin=subprocess.DEVNULL, stdout=self._log, stderr=self._log,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        ready = self._directory / 'ready.json'
        deadline = time.monotonic()+8
        while not ready.exists() and self._worker.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        try:
            status = json.loads(ready.read_text(encoding='utf8'))
            if status.get('error'):
                raise RuntimeError(status['error'])
        except Exception as error:
            self.close()
            raise RuntimeError('native map worker startup failed: '+str(error)) from error

    @property
    def error(self):
        if not self._closed and self._worker.poll() is not None:
            self._error = 'native map worker exited: '+str(self._worker.returncode)
        return self._error

    def _publish(self, metadata, chunks=()):
        from ._native_plane_ipc import _publish
        self._sequence = _publish(self._memory, self._sequence, metadata, chunks)

    def present(self, image, client_box, rectangles, *, scene=None):
        if self._closed or self.error:
            return False
        started = time.perf_counter_ns()
        metadata = {'command': 'frame', 'box': client_box, 'rectangles': rectangles,
                    'viewport_size': image.size, 'submitted_ns': started}
        if scene is None:
            source = image.convert('RGB') if image.mode != 'RGB' else image
            metadata['image_size'] = source.size
            chunks = [source.tobytes()]
        else:
            source, sprite = scene['canvas'], scene['sprite']
            metadata['image_size'] = source.size
            metadata['scene'] = {k:v for k,v in scene.items()
                                 if k not in ('canvas', 'sprite', 'text_overlay')}
            metadata['scene']['sprite_size'] = sprite.size
            chunks = [source.tobytes(), sprite.tobytes()]
            overlay = scene.get('text_overlay')
            if overlay is not None:
                overlay = overlay.convert('RGBA')
                metadata['scene']['text_overlay_size'] = overlay.size
                chunks.append(overlay.tobytes())
        try:
            self._publish(metadata, chunks)
            return True
        except Exception as error:
            self._error = repr(error)
            return False

    def hide(self):
        if not self._closed and self._worker.poll() is None:
            self._publish({'command': 'hide'})

    def snapshot(self):
        import json
        if self._closed or self.error:
            return
        self._publish({'command': 'snapshot'})
        expected = self._sequence
        path = self._directory / 'report.json'
        deadline = time.monotonic()+8
        while time.monotonic() < deadline:
            try:
                report = json.loads(path.read_text(encoding='utf8'))
                if report['sequence'] == expected:
                    self._report = report
                    return
            except (OSError, ValueError):
                pass
            if self._worker.poll() is not None:
                return
            time.sleep(.01)

    @property
    def metrics(self):
        return self._report.get('metrics', [])

    @property
    def trace(self):
        from PIL import Image
        result = []
        for index, row in enumerate(self._report.get('trace', [])):
            with Image.open(self._directory / 'trace' / f'{index:05d}.png') as image:
                crop = image.copy()
            with Image.open(self._directory / 'trace' / f'{index:05d}-map.png') as image:
                thumbnail = image.copy()
            result.append((row, crop, thumbnail))
        return result

    def close(self):
        if self._closed:
            return
        if self._worker.poll() is None:
            self._publish({'command': 'close'})
            try:
                self._worker.wait(timeout=4)
            except Exception:
                self._worker.kill()
                self._worker.wait(timeout=3)
        self._closed = True
        self._memory.close()
        self._stream.close()
        self._log.close()
        self._temporary.cleanup()
