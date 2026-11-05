"""Draw item font outlines at their final physical size, without bitmap scaling."""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=512)
def icon_image(glyph: str, width: int, height: int, foreground: str, background: str):
    from PIL import Image, ImageDraw, ImageFont
    from .map_presentation import glyph_source, font_sources
    value = glyph.strip()
    if not value or min(width, height) <= 0:
        return None
    path, bitmap_color = glyph_source(value)
    if bitmap_color:
        path = next((p for p, codes in font_sources() if 'MillenniumEmoji' not in p
                     and all(ord(c) in codes for c in value)), None)
        if path is None:
            return None
    target_w, target_h = max(1, width-4), max(1, height-4)
    size = max(8, height)
    try:
        for _ in range(5):
            font = ImageFont.truetype(path, size)
            ink_box = font.getmask(value).getbbox()
            if ink_box is None:
                return None
            iw, ih = ink_box[2]-ink_box[0], ink_box[3]-ink_box[1]
            fitted = max(1, int(size * min(target_w/iw, target_h/ih)))
            if fitted == size or (iw <= target_w and ih <= target_h and abs(fitted-size) <= 1):
                break
            size = fitted
        # Re-typeset at the chosen point size. No image.resize or tiny masks.
        box = font.getbbox(value)
        ink = Image.new('RGBA', (max(1, box[2]-box[0]), max(1, box[3]-box[1])))
        ImageDraw.Draw(ink).text((-box[0], -box[1]), value, font=font, fill=foreground)
        ink = ink.crop(ink.getbbox())
        result = Image.new('RGB', (width, height), background)
        result.paste(ink, ((width-ink.width)//2, (height-ink.height)//2), ink)
        return result
    except (OSError, ValueError):
        return None


def icon_anchors(strips):
    """Read reservations from final Rich lines, after wrapping and scrolling."""
    from rich.cells import cell_len
    anchors = []
    for row, strip in enumerate(strips):
        column = 0
        for segment in strip:
            style = segment.style
            meta = style.meta if style else {}
            glyph = meta.get('inventory_icon') or meta.get('inventory_reservation')
            if glyph and (glyph in segment.text or meta.get('inventory_reservation')):
                dx, dy = meta['inventory_icon_offset']
                width, height = meta['inventory_icon_size']
                anchors.append((column+dx, row+dy, width, height, glyph,
                                style.color.get_truecolor().hex, style.bgcolor.get_truecolor().hex))
            column += cell_len(segment.text)
    return tuple(dict.fromkeys(anchors))


def count_anchors(strips):
    """Quantity labels stay above the font-outline image plane."""
    from rich.cells import cell_len
    counts = []
    for y, strip in enumerate(strips):
        x = 0
        for segment in strip:
            style = segment.style
            text = style.meta.get('inventory_count') if style else None
            if text and text in segment.text:
                counts.append((x, y, text, style.color.get_truecolor().hex,
                               style.bgcolor.get_truecolor().hex if style.bgcolor else '#171821'))
            x += cell_len(segment.text)
    return tuple(counts)


def icon_row_areas(strips):
    """Visible reservations, not inferred full icon bounds, own image pixels.

    Scrolling removes inner rows but leaves the item's fixed description above
    them. An anchor can reconstruct the full source image for correct cropping;
    it cannot grant permission to paint those removed rows over the description.
    """
    from rich.cells import cell_len
    areas = set()
    for y, strip in enumerate(strips):
        x = 0
        for segment in strip:
            meta = segment.style.meta if segment.style else {}
            glyph = meta.get('inventory_icon') or meta.get('inventory_reservation')
            if glyph and (glyph in segment.text or meta.get('inventory_reservation')):
                dx, _dy = meta['inventory_icon_offset']
                width, _height = meta['inventory_icon_size']
                areas.add((x+dx, y, width, 1))
            x += cell_len(segment.text)
    return tuple(sorted(areas))


def draw_counts(canvas, counts, sx, sy):
    """Paint only glyph ink, with transparent margins over the underlying icon."""
    from PIL import ImageDraw, ImageFont
    from rich.cells import cell_len
    from ..font_assets import asset_dir
    font = ImageFont.truetype(str(asset_dir()/'DreamStrataInterfaceSans-Regular.ttf'),
                              max(9, round(sy*.62)))
    draw = ImageDraw.Draw(canvas)
    for x, y, text, foreground, _background in counts:
        if text == '★':
            # A large solid star, fitted directly from its outline, above icons.
            star_font = ImageFont.truetype(str(asset_dir()/'DreamStrataSongReading-Regular.ttf'),
                                           max(9, round(min(sy*.95, sx*1.15))))
            box = draw.textbbox((0, 0), text, font=star_font)
            draw.text((round((x+.5)*sx)-(box[0]+box[2])/2,
                       round((y+.5)*sy)-(box[1]+box[3])/2),
                      text, font=star_font, fill=foreground)
            continue
        box = draw.textbbox((0, 0), text, font=font)
        right, bottom = round((x+cell_len(text))*sx)-1, round((y+1)*sy)-2
        draw.text((right-box[2], bottom-box[3]), text, font=font, fill=foreground)


def border_cells(strips):
    from rich.cells import cell_len
    cells = []
    for y, strip in enumerate(strips):
        x = 0
        for segment in strip:
            style = segment.style
            part = style.meta.get('inventory_border') if style else None
            length = cell_len(segment.text)
            if part:
                cells.extend((cx, y, part, style.color.get_truecolor().hex,
                              style.bgcolor.get_truecolor().hex) for cx in range(x, x+length))
            x += length
    return tuple(cells)


def draw_borders(canvas, borders, sx, sy):
    """Continuous rules using the same cell edges as the wooden half-block frame."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(canvas)
    thickness = max(2, round(min(sx, sy)*.16))
    for x, y, part, fg, bg in borders:
        straight = part.startswith('straight:')
        part = part.removeprefix('straight:')
        selected = part.startswith('selected:')
        part = part.removeprefix('selected:')
        rail = max(2, round(min(sx, sy) * (.23 if selected else .12)))
        left, top, right, bottom = round(x*sx), round(y*sy), round((x+1)*sx), round((y+1)*sy)
        draw.rectangle((left, top, right-1, bottom-1), fill=bg)
        # Centre thin rules within the selected frame's solid half-cell rails.
        cx = round((x+(.25 if part in ('left', 'tl', 'bl') else .75))*sx)
        cy = round((y+(.25 if part in ('top', 'tl', 'tr') else .75))*sy)
        if part in ('top', 'bottom'):
            draw.line((left, cy, right-1, cy), fill=fg, width=rail)
        elif part in ('left', 'right'):
            # Small, deterministic creases, kept inside the border cell. End
            # points stay aligned with neighbouring rows and corner brackets.
            bend = 0 if straight else max(1, round(sx*.08)) * (1 if y % 3 else -1)
            draw.line((cx, top, cx+bend, (top+bottom)//2, cx, bottom-1),
                      fill=fg, width=rail)
        else:
            end_x = right-1 if part in ('tl', 'bl') else left
            end_y = bottom-1 if part in ('tl', 'tr') else top
            draw.line((end_x, cy, cx, cy, cx, end_y), fill=fg,
                      width=max(thickness+1, round(min(sx, sy)*.3)))


class InventoryIconPlane:
    """Reuse the existing mouse-through image transport; Rich owns all layout."""
    def __init__(self, widget):
        self.widget = widget
        self.plane = None
        self.key = None
        self.error = ''
        self._retry_at = 0.0

    def hide(self):
        if self.plane is not None and self.key is not None:
            self.plane.hide()
        self.key = None

    def close(self):
        if self.plane is not None:
            self.plane.close()
            self.plane = None
        self.key = None

    def refresh(self):
        import sys
        import time
        widget, app = self.widget, self.widget.app
        if (sys.platform != 'win32' or app.is_headless
                or getattr(app, 'panel_mode', '') != 'inventory'
                or app.screen is not widget.screen or getattr(app, 'home_mode', False)
                or not all(w.display and w.visible for w in widget.ancestors_with_self)):
            self.hide()
            return
        if time.monotonic() < self._retry_at:
            return
        try:
            self._present()
            if self.plane is not None:
                self.error = ''
        except Exception as error:
            self.error = repr(error)
            self.close()
            self._retry_at = time.monotonic() + 0.5

    def _present(self):
        import ctypes
        import win32gui
        from PIL import Image
        from textual.geometry import Region
        from ._native_image_plane import _NativeImagePlaneRenderer, _find_owner
        from ..env_compat import get as env_get
        from .map_image_transport import cells_to_rectangles
        widget, app = self.widget, self.widget.app
        region = widget.region
        if not region.width or not region.height:
            self.hide()
            return
        strips = widget.render_lines(Region(0, 0, widget.size.width, widget.size.height))
        anchors = icon_anchors(strips)
        borders = border_cells(strips)
        counts = count_anchors(strips)
        if not anchors and not borders and not counts:
            self.hide()
            return
        if self.plane is None:
            owner = _find_owner(env_get('NATIVE_IMAGE_PLANE_OWNER_FILE'))
            if owner is None:
                raise RuntimeError('No supported graphics terminal owner')
            self.plane = _NativeImagePlaneRenderer(owner)
        if self.plane.error:
            raise RuntimeError(self.plane.error)
        user32 = ctypes.windll.user32
        user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        old_dpi = user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        try:
            client = win32gui.GetClientRect(self.plane.owner)
        finally:
            if old_dpi:
                user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(old_dpi))
        sx, sy = (client[2]-12)/max(1, app.size.width), (client[3]-20)/max(1, app.size.height)
        box = (round(6+region.x*sx), round(12+region.y*sy),
               round(6+region.right*sx), round(12+region.bottom*sy))
        compositor = app.screen._compositor
        _ = compositor.cuts
        owners = compositor._wide_owners
        cells = set()
        areas = list(icon_row_areas(strips))
        areas.extend((x, y, 1, 1) for x, y, *_ in borders)
        from rich.cells import cell_len
        areas.extend((x, y, cell_len(text), 1) for x, y, text, *_ in counts)
        for x, y, w, h in areas:
            if y+h <= 0 or y >= region.height or x+w <= 0 or x >= region.width:
                continue
            for cy in range(max(0, y), min(region.height, y+h)):
                for cx in range(max(0, x), min(region.width, x+w)):
                    ax, ay = region.x+cx, region.y+cy
                    if 0 <= ay < len(owners) and 0 <= ax < len(owners[ay]) and owners[ay][ax] is widget:
                        cells.add((cx, cy))
        def clips_for(visible):
            return tuple((round(x*sx), round(y*sy), round((x+w)*sx)-round(x*sx),
                          round((y+h)*sy)-round(y*sy)) for x, y, w, h in cells_to_rectangles(visible))
        key = (anchors, borders, counts, box, clips_for(cells))
        if key == self.key:
            # A window hide/show may invalidate native visibility without any
            # change to Rich strips. Resubmit so the renderer restores itself.
            thread = getattr(self.plane, "_thread", None)
            if thread is not None and not thread.is_alive():
                raise RuntimeError("Inventory image thread ended")
            return
        if not cells:
            self.hide()
            return
        canvas = Image.new('RGBA', (box[2]-box[0], box[3]-box[1]))
        painted = set()
        from PIL import ImageDraw
        draw = ImageDraw.Draw(canvas)
        # Base card colour is painted before icons; count ink comes last.
        for x, y, text, _fg, bg in counts:
            w = cell_len(text)
            draw.rectangle((round(x*sx), round(y*sy), round((x+w)*sx)-1,
                            round((y+1)*sy)-1), fill=bg)
            painted.update((cx, y) for cx in range(x, x+w))
        draw_borders(canvas, borders, sx, sy)
        painted.update((x, y) for x, y, *_ in borders)
        for x, y, w, h, glyph, foreground, background in anchors:
            if y+h <= 0 or y >= region.height or x+w <= 0 or x >= region.width:
                continue
            x0, y0, x1, y1 = round(x*sx), round(y*sy), round((x+w)*sx), round((y+h)*sy)
            image = icon_image(glyph, x1-x0, y1-y0, foreground, background)
            if image is not None:
                canvas.paste(image, (x0, y0))
                painted.update((cx, cy) for cy in range(y, y+h) for cx in range(x, x+w))
        draw_counts(canvas, counts, sx, sy)
        # A missing outline never covers the native fallback with a blank tile.
        clips = clips_for(cells & painted)
        # Commit visibility as pixel alpha in the same bitmap as the artwork.
        # A separately updated native region can expose the preceding frame's
        # icon locations over unpainted (black) pixels during a scroll.
        mask = Image.new('L', canvas.size)
        mask_draw = ImageDraw.Draw(mask)
        for x, y, w, h in clips:
            mask_draw.rectangle((x, y, x+w-1, y+h-1), fill=255)
        canvas.putalpha(mask)
        clips = ((0, 0, canvas.width, canvas.height),) if clips else ()
        if clips and self.plane.present(canvas, box, clips):
            self.key = key
        else:
            self.hide()
