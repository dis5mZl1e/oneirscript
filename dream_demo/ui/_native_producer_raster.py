"""Private producer mirrors and immutable encoded rows; borrowed images stay live."""
from dataclasses import dataclass


@dataclass(frozen=True)
class _RasterRows:
    mode: str
    size: tuple
    rows: tuple

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]


class _OwnedRaster:
    """Exclusive pixel writer. All public pixel reads return detached values.

    Revisions record writes, never borrowed identities or claimed dirty boxes.
    This object deliberately exposes no PIL Image or ImagingCore attribute.
    """
    def __init__(self, mode, size, color=0):
        from PIL import Image
        self.__image = Image.new(mode, size, color)
        self.mode, self.size = mode, tuple(size)
        self.width, self.height = self.size
        self.__revision = 0
        self.__rows = [0] * self.height
        self.__tracking_rows = False
        self.__dirty = set(range(self.height))
        self.__snapshot = None
        self.__sources = {}
        self.serialized_bytes = 0

    def crop(self, box):
        return self.__image.crop(box)

    def copy(self):
        return self.__image.copy()

    def paste(self, source, position):
        self.__image.paste(source, position)
        x, y = position[:2]
        if source.width <= 0 or x >= self.width or x + source.width <= 0:
            return
        self.__revision += 1
        start, end = max(0, y), min(self.height, y + source.height)
        if self.__tracking_rows:
            self.__rows[start:end] = [self.__revision] * (end-start)
        if self.__snapshot is not None:
            self.__dirty.update(range(start, end))

    @property
    def row_revisions(self):
        if not self.__tracking_rows:
            # No consumer has a baseline yet; the complete initialized raster
            # is its first revision. Cold tile painting needs no per-row work.
            self.__rows = [self.__revision] * self.height
            self.__tracking_rows = True
        return tuple(self.__rows)

    def paste_owned(self, source, position, slot):
        """Copy changed rows from another exclusive writer without pixel scans."""
        revision = source.row_revisions
        key = (source, source.mode, source.size, tuple(position))
        previous = self.__sources.get(slot)
        old = previous[1] if previous is not None and previous[0] == key else None
        changed = [row for row, value in enumerate(revision)
                   if old is None or old[row] != value]
        if changed:
            # Coalesce consecutive writes; a dense update uses one PIL paste.
            start = end = changed[0]
            for row in changed[1:] + [None]:
                if row is not None and row == end + 1:
                    end = row
                    continue
                tile = source.crop((0, start, source.width, end + 1))
                self.paste(tile, (position[0], position[1] + start))
                start = end = row
        self.__sources[slot] = (key, revision)
        return tuple(position[1] + row for row in changed)

    def snapshot(self):
        self.serialized_bytes = 0
        if self.__snapshot is not None and not self.__dirty:
            return self.__snapshot
        rows = list(self.__snapshot.rows) if self.__snapshot is not None else [None] * self.height
        dirty = sorted(self.__dirty)
        stride = self.width * len(self.mode)
        start = end = dirty[0]
        for row in dirty[1:] + [None]:
            if row is not None and row == end + 1:
                end = row
                continue
            source = (self.__image if start == 0 and end + 1 == self.height else
                      self.__image.crop((0, start, self.width, end + 1)))
            raw = source.tobytes()
            self.serialized_bytes += len(raw)
            for index in range(start, end + 1):
                offset = (index-start)*stride
                rows[index] = raw[offset:offset+stride]
            start = end = row
        # Serialization failure leaves the prior immutable snapshot and dirty
        # transaction intact, so a retry still includes every pending write.
        result = _RasterRows(self.mode, self.size, tuple(rows))
        self.__snapshot = result
        self.__dirty.clear()
        return result


def _difference_box(left, right):
    # RGBA.getbbox normally consults alpha only. Hidden RGB is wire data too.
    from PIL import ImageChops
    difference = ImageChops.difference(left, right)
    bands = difference.split()
    combined = bands[0]
    for band in bands[1:]:
        combined = ImageChops.lighter(combined, band)
    return combined.getbbox(), combined


class _ProducerRaster:
    """Never expose the mirror/core. Compare borrowed pixels before reusing rows.

    Exact native Pillow comparison still scans pixels. Only changed full-width
    rows are serialized; no borrowed identity or caller dirty hint is trusted.
    """
    def __init__(self):
        self._mirror = self._snapshot = None
        self.serialized_bytes = 0

    @property
    def snapshot(self):
        return self._snapshot

    def capture(self, image):
        if image.mode not in ('RGB', 'RGBA'):
            raise ValueError('unsupported native component mode')
        self.serialized_bytes = 0
        previous = self._snapshot
        if previous is None or (previous.mode, previous.size) != (image.mode, image.size):
            raw = image.tobytes()
            stride = image.width * len(image.mode)
            rows = tuple(raw[start:start + stride] for start in range(0, len(raw), stride))
            self.serialized_bytes = len(raw)
            mirror = image.copy()
        else:
            box, difference = _difference_box(image, self._mirror)
            if box is None:
                return previous
            rows = list(previous.rows)
            changes = []
            for y in range(box[1], box[3]):
                if difference.crop((0, y, image.width, y + 1)).getbbox() is None:
                    continue
                tile = image.crop((0, y, image.width, y + 1))
                rows[y] = tile.tobytes()
                self.serialized_bytes += len(rows[y])
                changes.append((y, tile))
            # Complete all potentially failing serialization before advancing
            # the private baseline. The caller never receives this mirror.
            mirror = self._mirror
            for y, tile in changes:
                mirror.paste(tile, (0, y))
            rows = tuple(rows)
        snapshot = _RasterRows(image.mode, image.size, rows)
        self._mirror, self._snapshot = mirror, snapshot
        return snapshot


def _paste_changed_rows(destination, source, position):
    """Assemble borrowed packet canvases without rewriting unchanged rows."""
    x, y = position
    box = (x, y, x + source.width, y + source.height)
    previous = destination.crop(box)
    dirty, difference = _difference_box(previous, source)
    if dirty is None:
        return 0
    count = 0
    for row in range(dirty[1], dirty[3]):
        if difference.crop((0, row, source.width, row + 1)).getbbox() is not None:
            destination.paste(source.crop((0, row, source.width, row + 1)), (x, y + row))
            count += source.width * len(source.mode)
    return count
