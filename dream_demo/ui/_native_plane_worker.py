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


def _decode_frame(metadata, payload):
    """Decode the map, moving sprite and optional transparent text layer."""
    from PIL import Image
    image_size = tuple(metadata['image_size'])
    length = image_size[0] * image_size[1] * 3
    image = Image.frombytes('RGB', image_size, payload[:length])
    raw_scene = metadata.get('scene')
    if raw_scene is None:
        return image, None
    scene = dict(raw_scene)
    sprite_size = tuple(scene.pop('sprite_size'))
    sprite_length = sprite_size[0] * sprite_size[1] * 4
    scene['sprite'] = Image.frombytes('RGBA', sprite_size, payload[length:length + sprite_length])
    overlay_size = scene.pop('text_overlay_size', None)
    if overlay_size is not None:
        scene['text_overlay'] = Image.frombytes('RGBA', tuple(overlay_size),
                                                payload[length + sprite_length:])
    scene['canvas'] = image
    return image, scene


def main(argv=None):
    from ._native_image_plane import _NativeImagePlaneRenderer
    from ._native_plane_ipc import _CAPACITY, _read_latest
    args = list(sys.argv[1:] if argv is None else argv)
    directory, owner, traced = Path(args[0]), int(args[1]), bool(int(args[2]))
    parent = None
    if len(args) > 3:
        import win32api
        import win32con
        parent = win32api.OpenProcess(win32con.SYNCHRONIZE, False, int(args[3]))
    stream = (directory / 'frames.bin').open('r+b')
    memory = mmap.mmap(stream.fileno(), _CAPACITY)
    plane = None
    transports = []

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
                  'trace': trace_rows, 'transport_ms': transports[-1200:]}
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
            packet = _read_latest(memory, sequence)
            if packet is None:
                time.sleep(.001)
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
            image, scene = _decode_frame(metadata, payload)
            if scene is not None:
                # 输入 image_size 是保护画布，而呈现尺寸是未经缩放的视口。
                source_size = tuple(metadata['viewport_size'])
                plane.present(SimpleNamespace(size=source_size), metadata['box'],
                              metadata['rectangles'], scene=scene)
            else:
                plane.present(image, metadata['box'], metadata['rectangles'])
            transports.append((time.perf_counter_ns()-metadata['submitted_ns'])/1e6)
    except Exception as error:
        (directory / 'ready.json').write_text(json.dumps({'error': repr(error)}), encoding='utf8')
        if plane is not None:
            plane.error = repr(error)
    finally:
        if plane is not None:
            plane.close()
        report(-1)
        memory.close()
        stream.close()
        if parent is not None:
            parent.Close()


if __name__ == '__main__':
    main()
