"""原生地图呈现子进程；不导入或推进任何游戏规则。"""
from __future__ import annotations
import json
import mmap
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def _parent_alive(process):
    import win32event
    return win32event.WaitForSingleObject(process, 0) == win32event.WAIT_TIMEOUT


def _wait_for_publication(wake, parent, timeout_ms=500):
    """Wait for a committed slot or parent death without a polling clock.

    The auto-reset wake must never be explicitly cleared: a publication between
    the empty-slot read and this wait leaves the event signalled. Timeout only
    checks the renderer thread's health when the transport remains idle.
    """
    import win32event
    handles = [parent, wake] if parent is not None else [wake]
    result = win32event.WaitForMultipleObjects(handles, False, timeout_ms)
    return not (parent is not None and result == win32event.WAIT_OBJECT_0)


def _decode_frame(metadata, payload):
    """Decode the map, moving sprite and optional transparent text layer."""
    from PIL import Image
    pixels = memoryview(payload)
    image_size = tuple(metadata['image_size'])
    length = image_size[0] * image_size[1] * 3
    image = Image.frombytes('RGB', image_size, pixels[:length])
    raw_scene = metadata.get('scene')
    if raw_scene is None:
        return image, None
    scene = dict(raw_scene)
    sprite_size = tuple(scene.pop('sprite_size'))
    sprite_length = sprite_size[0] * sprite_size[1] * 4
    # The shared slot is already copied into immutable bytes. PIL retains this
    # owner and detaches on mutation, so RGBA layers need no second pixel copy.
    scene['sprite'] = Image.frombuffer('RGBA', sprite_size, pixels[length:length + sprite_length])
    overlay_size = scene.pop('text_overlay_size', None)
    if overlay_size is not None:
        scene['text_overlay'] = Image.frombuffer('RGBA', tuple(overlay_size),
                                                pixels[length + sprite_length:])
    scene['canvas'] = image
    return image, scene


class _FrameDecoder:
    """Bounded exact-byte reuse; every packet remains independently decodable."""

    def __init__(self):
        self._assets = {}
        self._version = 0

    def decode(self, metadata, payload):
        from PIL import Image
        versions = {}
        updates = {}

        def component(name, mode, size, start):
            size = tuple(size)
            length = size[0] * size[1] * len(mode)
            raw = payload[name] if isinstance(payload, dict) else payload[start:start + length]
            if isinstance(raw, Image.Image):
                if raw.mode != mode or raw.size != size:
                    raise ValueError('invalid leased native image component')
                previous = self._assets.get(name)
                if previous is None or previous[2] is not raw:
                    change = getattr(raw, '_native_component', None)
                    prior = getattr(previous[2], '_native_component', None) if previous else None
                    if (change and prior and change[0] == prior[0]
                            and change[2] == prior[1] and change[3]):
                        updates[name] = {'previous': previous[4], 'dirty': change[3]}
                    self._version += 1
                    previous = self._assets[name] = (mode, size, raw, raw, self._version)
                versions[name] = previous[4]
                return raw, start + length
            if len(raw) != length:
                raise ValueError('truncated native image component')
            previous = self._assets.get(name)
            if previous is None or previous[:3] != (mode, size, raw):
                image = (Image.frombuffer(mode, size, raw) if mode == 'RGBA'
                         else Image.frombytes(mode, size, raw))
                self._version += 1
                previous = self._assets[name] = (mode, size, raw, image, self._version)
            versions[name] = previous[4]
            return previous[3], start + length

        image, offset = component('canvas', 'RGB', metadata['image_size'], 0)
        raw_scene = metadata.get('scene')
        if raw_scene is None:
            self._assets.pop('sprite', None)
            self._assets.pop('text_overlay', None)
            return image, None
        scene = dict(raw_scene)
        scene['sprite'], offset = component('sprite', 'RGBA', scene.pop('sprite_size'), offset)
        overlay_size = scene.pop('text_overlay_size', None)
        if overlay_size is not None:
            scene['text_overlay'], offset = component('text_overlay', 'RGBA', overlay_size, offset)
        else:
            self._assets.pop('text_overlay', None)
        scene['canvas'] = image
        scene['_asset_versions'] = versions
        scene['_asset_updates'] = updates
        return image, scene


def main(argv=None):
    import win32con
    import win32event
    from ._native_image_plane import _NativeImagePlaneRenderer
    from ._native_plane_ipc import _CAPACITY, _ImageFrameReader
    args = list(sys.argv[1:] if argv is None else argv)
    directory, owner, traced = Path(args[0]), int(args[1]), bool(int(args[2]))
    parent = None
    if len(args) > 3:
        import win32api
        import win32con
        parent = win32api.OpenProcess(win32con.SYNCHRONIZE, False, int(args[3]))
    wake = (win32event.OpenEvent(win32con.SYNCHRONIZE | 2, False, args[4]) if len(args) > 4
            else win32event.CreateEvent(None, False, False, None))
    stream = (directory / 'frames.bin').open('r+b')
    memory = mmap.mmap(stream.fileno(), _CAPACITY)
    plane = None
    transports = []
    decodes = []
    decoder = _FrameDecoder()
    reader = _ImageFrameReader(on_release=lambda: win32event.SetEvent(wake))

    def report(sequence):
        trace_rows = []
        if plane is not None and plane.trace is not None:
            folder = directory / 'trace'
            folder.mkdir(exist_ok=True)
            for index, (row, image, thumbnail) in enumerate(list(plane.trace)):
                image.save(folder / f'{index:05d}.png')
                thumbnail.save(folder / f'{index:05d}-map.png')
                trace_rows.append(row)
        result = {'sequence': sequence, 'error': plane.error if plane else '',
                  'metrics': list(plane.metrics) if plane else [],
                  'trace': trace_rows, 'transport_ms': transports[-1200:],
                  'decode_ms': decodes[-1200:], 'image_buffers': reader.metrics()}
        temporary = directory / 'report.new'
        temporary.write_text(json.dumps(result), encoding='utf8')
        temporary.replace(directory / 'report.json')

    try:
        plane = _NativeImagePlaneRenderer(owner, trace=traced)
        (directory / 'ready.json').write_text(json.dumps({'error': ''}), encoding='utf8')
        sequence = 0
        while plane._thread.is_alive():
            if parent is not None and not _parent_alive(parent):
                break
            packet = reader.read(memory, sequence)
            if packet is None:
                if not _wait_for_publication(wake, parent):
                    break
                continue
            sequence, metadata, payload = packet
            command = metadata['command']
            if command == 'close':
                break
            if command == 'hide':
                plane.hide()
                continue
            if command == 'snapshot':
                report(sequence)
                continue
            decode_started = time.perf_counter_ns()
            image, scene = decoder.decode(metadata, payload)
            decodes.append((time.perf_counter_ns()-decode_started)/1e6)
            if len(decodes) > 1200:
                del decodes[:-1200]
            if scene is not None:
                # 输入 image_size 是保护画布，而呈现尺寸是未经缩放的视口。
                source_size = tuple(metadata['viewport_size'])
                plane.present(SimpleNamespace(size=source_size), metadata['box'],
                              metadata['rectangles'], scene=scene)
            else:
                plane.present(image, metadata['box'], metadata['rectangles'], owned=True)
            transports.append((time.perf_counter_ns()-metadata['submitted_ns'])/1e6)
            if len(transports) > 1200:
                del transports[:-1200]
    except Exception as error:
        (directory / 'ready.json').write_text(json.dumps({'error': repr(error)}), encoding='utf8')
        if plane is not None:
            plane.error = repr(error)
    finally:
        if plane is not None:
            plane.close()
        report(-1)
        reader.close()
        memory.close()
        stream.close()
        wake.Close()
        if parent is not None:
            parent.Close()


if __name__ == '__main__':
    main()
