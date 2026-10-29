"""Small, click-through pixel cues written after map and editor typography."""
from functools import lru_cache
import os
import time

from textual.geometry import Region


def _strips(rect):
    if rect.width < 2 or rect.height < 2:
        return (rect,)
    rows = [Region(rect.x, rect.y, rect.width, 1),
            Region(rect.x, rect.bottom-1, rect.width, 1)]
    if rect.height > 2:
        rows += [Region(rect.x, rect.y+1, 1, rect.height-2),
                 Region(rect.right-1, rect.y+1, 1, rect.height-2)]
    return tuple(rows)


def _geometry(app):
    if (not app._coach_enabled() or getattr(app, '_coach_hidden', False)
            or getattr(app, '_coach_directory', False) or app.qol_confirmation is not None
            or app.settings_page.capture_target is not None):
        return None, None
    anchor = getattr(app, '_coach_anchor_rect', None)
    if not anchor:
        return None, None
    screen = Region(0, 0, app.size.width, max(1, app.size.height-1))
    frame = anchor.grow((1, 1, 1, 1)).intersection(screen)
    if not frame.width or not frame.height:
        return None, None
    # A short moving chevron points into the outlined target, without drawing
    # a full-screen transparent widget that would steal map/editor hit tests.
    arrow = Region(max(0, frame.x-2), frame.y+frame.height//2, 2, 1)
    if arrow.overlaps(frame):
        arrow = Region(min(app.size.width-2, frame.right), frame.y+frame.height//2, 2, 1)
    return frame, arrow


def cue_regions(app):
    frame, arrow = _geometry(app)
    if frame is None:
        return ()
    return (*_strips(frame), arrow, *(r for _, r in _markers(app)),
            *(r for r, _ in _area_corners(app)))


def _markers(app):
    result = []
    for number, point in app._coach_map_targets().items():
        rect = app._coach_map_region(point)
        if rect and _map_visible_at(app, rect.x, rect.y):
            result.append((number, Region(rect.right-1, rect.y, 1, 1)))
    return result


def _area_corners(app):
    area = app._coach_task_region()
    if area is None or area.width < 4 or area.height < 2:
        return ()
    return tuple((Region(x, y, 2, 1), (left, top))
                 for x, left in ((area.x, True), (area.right-2, False))
                 for y, top in ((area.y, True), (area.bottom-1, False))
                 if _map_visible_at(app, x, y) and _map_visible_at(app, x+1, y))


def _map_visible_at(app, x, y):
    try:
        widget, _ = app.screen._compositor.get_widget_at(x, y)
        return widget is app.query_one('#map') or widget.id == 'map-hints'
    except Exception:
        return False


@lru_cache(maxsize=96)
def _marker_image(cw, ch, number):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    diameter = min(cw, ch)
    draw.rounded_rectangle((0, 0, cw-1, diameter-1), radius=3,
                           fill=(0, 0, 0, 0), outline=(239, 212, 144, 150), width=1)
    try:
        font = ImageFont.load_default(size=max(8, diameter-3))
    except TypeError:
        font = ImageFont.load_default()
    draw.text((cw/2, diameter/2), str(number), font=font,
              anchor='mm', fill=(255, 237, 188, 255))
    return image


@lru_cache(maxsize=32)
def _area_image(cw, ch, left, top):
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (cw*2, ch), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x, y = (1 if left else cw*2-2), (1 if top else ch-2)
    draw.line((x, y, x+(cw if left else -cw), y), fill=(90, 165, 202, 220), width=2)
    draw.line((x, y, x, y+(ch//2 if top else -ch//2)), fill=(90, 165, 202, 220), width=2)
    return image


@lru_cache(maxsize=192)
def _frame_image(width, height, cw, ch, phase):
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (max(1, width*cw), max(1, height*ch)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pulse = (0, 12, 24, 36, 44, 36, 24, 12)[phase]
    color = (126+pulse, 206+min(pulse, 35), 216+min(pulse, 30), 115)
    w, h = image.size
    # Thin rounded outline with brighter corner brackets.
    draw.rounded_rectangle((1, 1, w-2, h-2), radius=min(9, ch//3), outline=color, width=1)
    length = max(4, min(cw*2, w//3))
    for x, sign in ((2, 1), (w-3, -1)):
        for y, down in ((2, 1), (h-3, -1)):
            draw.line((x, y, x+sign*length, y), fill=(245, 220, 151, 145), width=1)
            draw.line((x, y, x, y+down*min(length, ch)), fill=(245, 220, 151, 145), width=1)
    return image


@lru_cache(maxsize=32)
def _arrow_image(cw, ch, phase, right):
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (cw*2, ch), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    shift = (phase % 4)*max(1, cw//5)
    cx = cw//2 + shift if right else cw*3//2-shift
    direction = 1 if right else -1
    draw.line((cx-direction*cw//3, ch//4, cx, ch//2,
               cx-direction*cw//3, ch*3//4), fill=(248, 222, 154, 255), width=3)
    return image


def player_safe_rectangles(app, rect):
    """Player tiles always win over tutorial ink, including arrows and badges."""
    from .map_image_transport import visible_rectangles
    state = app.session.state
    player = app._coach_map_region((state.player.x, state.player.y))
    return visible_rectangles(tuple(rect), lambda x, y: not player or (x, y) not in player)


def _cue_packets(app, picture, rect, cw, ch):
    from .map_image_transport import image_sequence, visible_rectangles
    packets = []
    view = app.query_one('#map')
    for box in player_safe_rectangles(app, rect):
        area = Region(*box)
        # Split at map boundaries so transparent ink can be composited onto
        # existing map pixels. Never send transparent replacement PNGs there:
        # some terminal implementations erase the glyph underneath them.
        def on_map(x, y):
            return view.display_mode == 'image' and (x, y) in view.content_region and _map_visible_at(app, x, y)
        for is_map in (True, False):
            parts = visible_rectangles(tuple(area), lambda x, y: on_map(x, y) == is_map)
            for x, y, width, height in parts:
                crop = picture.crop(((x-rect.x)*cw, (y-rect.y)*ch,
                                     (x-rect.x+width)*cw, (y-rect.y+height)*ch))
                if is_map:
                    base = view.image_frame()
                    ox, oy = x-view.content_region.x, y-view.content_region.y
                    background = base.crop((ox*cw, oy*ch, (ox+width)*cw, (oy+height)*ch)).convert('RGB')
                    background.paste(crop, (0, 0), crop)
                    crop = background
                packets.append(image_sequence(crop, x, y, width, height))
    return packets


def cue_packets(app):
    if not os.environ.get('WEZTERM_PANE'):
        return ()
    frame, arrow = _geometry(app)
    if frame is None:
        return ()
    from .map_image_transport import image_sequence
    cw, ch = getattr(app, '_map_terminal_cell_pixels', (12, 24))
    cw, ch = max(4, round(cw)), max(8, round(ch))
    phase = int(time.monotonic()*8) % 8
    image = _frame_image(frame.width, frame.height, cw, ch, phase)
    packets = []
    for rect in _strips(frame):
        cropped = image.crop(((rect.x-frame.x)*cw, (rect.y-frame.y)*ch,
                              (rect.right-frame.x)*cw, (rect.bottom-frame.y)*ch))
        packets.extend(_cue_packets(app, cropped, rect, cw, ch))
    image = _arrow_image(cw, ch, phase, arrow.x < frame.x)
    packets.extend(_cue_packets(app, image, arrow, cw, ch))
    for number, rect in _markers(app):
        image = _marker_image(cw, ch, number)
        packets.extend(_cue_packets(app, image, rect, cw, ch))
    for rect, (left, top) in _area_corners(app):
        image = _area_image(cw, ch, left, top)
        packets.extend(_cue_packets(app, image, rect, cw, ch))
    return tuple(packets)


def repair_packets(app, cells):
    """Restore only pixels actually covered by the previous cue frame."""
    if not cells or not os.environ.get('WEZTERM_PANE'):
        return ()
    view = app.query_one('#map')
    if not view.is_on_screen or app.resolved_map_display()[0] != 'image':
        return ()
    visible = set()
    for x, y in cells:
        if (x, y) not in view.content_region:
            continue
        widget, _ = app.screen._compositor.get_widget_at(x, y)
        if widget is view or widget.id == 'map-hints':
            visible.add((x, y))
    if not visible:
        return ()
    from .map_image_transport import cells_to_rectangles, image_region_packets
    image = view.image_frame()
    scale = (image.width/(view.viewport[2]*view.cell_w),
             image.height/(view.viewport[3]*view.cell_h))
    return tuple(packet for _, packet in image_region_packets(
        image, view.content_region, scale, cells_to_rectangles(visible)))
