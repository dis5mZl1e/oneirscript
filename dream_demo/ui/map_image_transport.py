"""WezTerm inline images, queued through the Textual driver's single writer.

Never write to stdout directly: WindowsDriver owns an asynchronous output queue.
Cursor preservation alone is insufficient; doNotMoveCursor also prevents scroll.

C8（docs/261022-卡顿性能进一步优化方案.md 4.3 节）：PNG 压缩级别开关。
ONEIRSCRIPT_PNG_LEVEL 每次编码现读，取值 0–9，默认 2，非法值回退 2。
2026-10-22 批次 2 完成 C8：默认从 level1 切到 level2——原生 WezTerm 实测
observe 每动作 flush 字节 291747→219322（−24.8%）、idle 2s 写入 2028214→1565642
（−22.8%）、move 423077→326956（−22.7%）；无头同帧 CPU 仅 +0.13ms（6.18→6.31ms）。
PNG level 只影响压缩位流，解码仍是无损标准 PNG，视觉像素不变；
ONEIRSCRIPT_PNG_LEVEL=1 可一键回退旧档。level0 是「不压缩」（字节 +2660%，
base64 4.3–4.5 ms）、optimize=1（33–38 ms）都不作候选；level3/6 相对 level2
边际收益小、CPU 更高。

C7：叠加层脏格补丁（ONEIRSCRIPT_IMAGE_PATCHES，默认 0 关闭）。没有原生
可见帧/叠放顺序证据前不改变输出路径；这里只提供纯函数与可选路径，供
tests/test_output_frames_261022.py 在测试模型里验证「补丁序列 == 整图重发」。
"""
from __future__ import annotations

import base64
from io import BytesIO

from ..env_compat import get as env_get, name as env_name

DEFAULT_PNG_LEVEL = 2
PNG_LEVEL_ENV = env_name('PNG_LEVEL')
IMAGE_PATCHES_ENV = env_name('IMAGE_PATCHES')
# 单帧补丁脏格上限：超过它说明「少量叠加格」的前提不成立（例如大范围
# preview/FX 变化），整包重发更便宜也更接近现行路径，直接回退。
PATCH_CELL_LIMIT = 128


def png_level() -> int:
    """每次调用现读 ONEIRSCRIPT_PNG_LEVEL：0–9，默认 2，非法值回退 2。

    默认 level2：原生 WezTerm 下每动作 flush 字节约 −25%、idle 写入约 −23%，
    无头 CPU 仅 +0.13ms/帧；level1 编码略快但字节更多。设 1 可回退。
    """
    raw = env_get('PNG_LEVEL')
    if raw is None:
        return DEFAULT_PNG_LEVEL
    try:
        level = int(raw.strip())
    except (TypeError, ValueError):
        return DEFAULT_PNG_LEVEL
    return level if 0 <= level <= 9 else DEFAULT_PNG_LEVEL


def image_patches_enabled() -> bool:
    """C7 脏格补丁开关：默认关闭（未拿到原生叠放/擦除证据）。

    开启后 live_map 只在「基础栅格未变 + 仅少量叠加格变化」时发脏格小图；
    几何/裁切/缩放/换层/base 变化、过渡帧、非缓存栅格一律回退整包重发。
    """
    return (env_get('IMAGE_PATCHES', '0') or '').strip().lower() in (
        '1', 'true', 'yes', 'on')


def image_sequence(image, x: int, y: int, columns: int, rows: int) -> str:
    stream = BytesIO()
    image.save(stream, format='PNG', compress_level=png_level())
    payload = base64.b64encode(stream.getvalue()).decode('ascii')
    return (f'\x1b7\x1b[{y+1};{x+1}H\x1b]1337;File=inline=1;'
            f'size={len(stream.getvalue())};width={columns};height={rows};preserveAspectRatio=0;'
            f'doNotMoveCursor=1:{payload}\x07\x1b8')


def visible_rectangles(region, visible):
    """Coalesce equal horizontal runs; all coordinates are terminal columns/rows."""
    left, top, width, height = region
    finished, active = [], {}
    for y in range(top, top + height):
        runs, start = [], None
        for x in range(left, left + width + 1):
            show = x < left + width and visible(x, y)
            if show and start is None:
                start = x
            elif not show and start is not None:
                runs.append((start, x-start))
                start = None
        following = {}
        for run in runs:
            old = active.pop(run, None)
            following[run] = ((old[0], old[1], old[2], old[3]+1) if old
                              else (run[0], y, run[1], 1))
        finished.extend(active.values())
        active = following
    return finished + list(active.values())


def image_region_packets(image, region, scale, rectangles):
    """Crop one full-viewport map image into terminal rectangles.

    scale is (pixels per terminal column, pixels per terminal row); region is
    the terminal origin of the image.  Returns [(rect, packet)] in input order,
    with the same round() boundaries as the pre-C7 inline code, so the patch
    path and the full path share one cropping rule.
    """
    sx, sy = scale
    left, top = region[0], region[1]
    packets = []
    for x, y, w, h in rectangles:
        crop = image.crop((round((x-left)*sx), round((y-top)*sy),
                           round((x+w-left)*sx), round((y+h-top)*sy)))
        packets.append(((x, y, w, h), image_sequence(crop, x, y, w, h)))
    return packets


def cells_to_rectangles(cells):
    """Coalesce (x, y) cells into disjoint (x, y, w, h) rectangles.

    Same rule as visible_rectangles: equal horizontal runs that repeat on
    consecutive rows are merged vertically; nothing outside the input is covered.
    """
    rows = {}
    for x, y in cells:
        rows.setdefault(y, set()).add(x)
    finished, active = [], {}
    for y in sorted(rows):
        xs = sorted(rows[y])
        runs, start, previous = [], None, None
        for x in xs:
            if start is None:
                start = previous = x
            elif x == previous + 1:
                previous = x
            else:
                runs.append((start, previous-start+1))
                start = previous = x
        if start is not None:
            runs.append((start, previous-start+1))
        following = {}
        for run in runs:
            old = active.pop(run, None)
            following[run] = ((old[0], old[1], old[2], old[3]+1) if old
                              else (run[0], y, run[1], 1))
        finished.extend(active.values())
        active = following
    return finished + list(active.values())


def overlay_dirty_cells(previous, current):
    """Per-cell overlay signature diff: added, removed and changed cells.

    Removed cells matter as much as new ones: the terminal still shows the old
    overlay there, so the patch must resend that cell with its new base pixels
    (this is the "erase the old cursor" case).
    """
    dirty = set(previous) ^ set(current)
    for pos in set(previous) & set(current):
        if previous[pos] != current[pos]:
            dirty.add(pos)
    return dirty


def overlay_patch_rectangles(previous, current, *, viewport, cell_size, region,
                             visible, limit=PATCH_CELL_LIMIT):
    """Turn overlay-signature differences into terminal rectangles.

    Returns [] when nothing changed, a coalesced rectangle list for a small
    patch, or None when the frame must be resent whole (no visible dirty cell,
    or more than limit dirty terminal cells).

    visible is the current occlusion/clipping rectangle list; cells covered by
    a floating layer are skipped (geometry changes trigger a full resend, so
    they are repainted when they become visible again).
    """
    dirty = overlay_dirty_cells(previous, current)
    if not dirty:
        return []
    left, top = viewport[0], viewport[1]
    cell_w, cell_h = max(1, int(cell_size[0])), max(1, int(cell_size[1]))
    region_x, region_y = region[0], region[1]
    covered = set()
    for x, y, w, h in visible:
        for yy in range(y, y+h):
            covered.update((xx, yy) for xx in range(x, x+w))
    terminal = set()
    for cell_x, cell_y in dirty:
        base_x = region_x + (cell_x-left)*cell_w
        base_y = region_y + (cell_y-top)*cell_h
        for dx in range(cell_w):
            for dy in range(cell_h):
                if (base_x+dx, base_y+dy) in covered:
                    terminal.add((base_x+dx, base_y+dy))
    if not terminal:
        return []
    if len(terminal) > limit:
        return None
    return cells_to_rectangles(terminal)
