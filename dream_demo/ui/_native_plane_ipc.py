"""单槽共享内存：奇数序号写入中，偶数序号才可读，丢弃被替换的旧帧。"""
import json
import struct
import uuid
import weakref

_DATA = 16384
_CAPACITY = 32*1024*1024


def _publish(memory, sequence, metadata, chunks=(), *, patches=(), payload_length=None):
    # A replacement publisher may start its local counter at zero while the
    # mapped file still contains a committed frame. Never reuse that sequence.
    sequence = max(sequence, struct.unpack_from('<Q', memory, 0)[0] & ~1)
    header = json.dumps(metadata, separators=(',', ':')).encode('utf8')
    length = sum(map(len, chunks)) if payload_length is None else payload_length
    if len(header) > _DATA-64 or _DATA+length > len(memory):
        raise ValueError('native map frame exceeds shared slot capacity')
    if any(offset < 0 or offset+len(raw) > length for offset, raw in patches):
        raise ValueError('native map patch outside component storage')
    struct.pack_into('<Q', memory, 0, sequence+1)
    struct.pack_into('<II', memory, 8, len(header), length)
    memory[64:64+len(header)] = header
    offset = _DATA
    for chunk in chunks:
        memory[offset:offset+len(chunk)] = chunk
        offset += len(chunk)
    for offset, raw in patches:
        memory[_DATA+offset:_DATA+offset+len(raw)] = raw
    struct.pack_into('<Q', memory, 0, sequence+2)
    return sequence+2


def _read_latest(memory, previous):
    sequence = struct.unpack_from('<Q', memory, 0)[0]
    if sequence == previous or sequence & 1 or sequence == 0:
        return None
    metadata_size, length = struct.unpack_from('<II', memory, 8)
    if metadata_size > _DATA-64 or _DATA+length > len(memory):
        return None
    header = bytes(memory[64:64+metadata_size])
    payload = bytes(memory[_DATA:_DATA+length])
    if sequence != struct.unpack_from('<Q', memory, 0)[0]:
        return None
    return sequence, json.loads(header), payload


class _FramePublisher:
    """槽内始终保留完整画面；相同布局只写入改变的像素行。"""

    def __init__(self):
        self._layout = None
        self._assets = {}
        self._generation = uuid.uuid4().hex
        self.written_bytes = 0

    def publish(self, memory, sequence, metadata, images):
        sequence = max(sequence, struct.unpack_from('<Q', memory, 0)[0] & ~1)
        layout = tuple((name, image.mode, image.size) for name, image in images.items())
        length = sum(image.width*image.height*len(image.mode) for image in images.values())
        if _DATA+length > len(memory):
            raise ValueError('native map frame exceeds shared slot capacity')
        assets, descriptors, patches = {}, {}, []
        offset = 0
        for name, image in images.items():
            mode, size = image.mode, image.size
            if mode not in ('RGB', 'RGBA'):
                raise ValueError('unsupported native component mode')
            previous = self._assets.get(name) if layout == self._layout else None
            from ._native_producer_raster import _RasterRows
            if type(image) is _RasterRows:
                old = previous[0] if previous is not None else None
                old_rows = old.rows if type(old) is _RasterRows else None
                changed = [y for y, row in enumerate(image.rows)
                           if old_rows is None or row is not old_rows[y]]
                prior_version = previous[1] if previous is not None else None
                stride = image.width * len(mode)
                if changed:
                    start = end = changed[0]
                    for y in changed[1:] + [None]:
                        if y is not None and y == end + 1:
                            end = y
                            continue
                        raw = image.rows[start] if start == end else b''.join(image.rows[start:end+1])
                        patches.append((offset + start * stride, raw))
                        start = end = y
                    box = (0, changed[0], image.width, changed[-1] + 1)
                    asset = (image, sequence + 2)
                else:
                    box, asset = None, previous
                assets[name] = asset
                descriptors[name] = {'mode': mode, 'size': size, 'offset': offset,
                                     'version': asset[1], 'previous': prior_version, 'dirty': box}
                offset += image.width * image.height * len(mode)
                continue
            # PIL 对整幅图求差和 getbbox 比原传输更贵。不可假设借来的图像
            # 不变：先取精确字节，再只比较像素行，透明像素的 RGB 也不能漏。
            raw = image.tobytes()
            if previous is not None and type(previous[0]) is _RasterRows:
                previous = (b''.join(previous[0].rows), previous[1])
            stride = image.width*len(mode)
            box = (0, 0, *size)
            if previous is not None:
                if raw == previous[0]:
                    box = None
                else:
                    first, last = 0, image.height-1
                    old = previous[0]
                    while raw[first*stride:(first+1)*stride] == old[first*stride:(first+1)*stride]:
                        first += 1
                    while raw[last*stride:(last+1)*stride] == old[last*stride:(last+1)*stride]:
                        last -= 1
                    box = (0, first, image.width, last+1)
            prior_version = previous[1] if previous is not None else None
            if box is None:
                asset = previous
            else:
                # 大片变化直接写整张，避免逐行切片抵消增量收益。
                if (box[2]-box[0])*(box[3]-box[1]) > image.width*image.height//2:
                    box = (0, 0, *size)
                patches.append((offset+box[1]*stride, raw[box[1]*stride:box[3]*stride]))
                # 版本跟随槽序号，生产端缓存重置也不会与旧组件版本碰撞。
                asset = (raw, sequence+2)
            assets[name] = asset
            descriptors[name] = {'mode': mode, 'size': size, 'offset': offset,
                                 'version': asset[1], 'previous': prior_version, 'dirty': box}
            offset += image.width*image.height*len(mode)
        packet = dict(metadata, components=descriptors, generation=self._generation)
        result = _publish(memory, sequence, packet, patches=patches, payload_length=length)
        # 只有完整提交才推进缓存；拒绝的超大帧不能破坏下一帧的参考。
        self._layout, self._assets = layout, assets
        self.written_bytes = sum(len(raw) for _, raw in patches)
        return result


class _FrameReader:
    """Legacy bytes diagnostic reader; production uses _ImageFrameReader.

    copied_bytes here only counts SHM reads, not full immutable reassembly.
    """

    def __init__(self):
        self._assets = {}
        self.copied_bytes = 0

    def read(self, memory, previous):
        sequence = struct.unpack_from('<Q', memory, 0)[0]
        if sequence == previous or sequence & 1 or sequence == 0:
            return None
        header_length, length = struct.unpack_from('<II', memory, 8)
        if header_length > _DATA-64 or _DATA+length > len(memory):
            return None
        header = bytes(memory[64:64+header_length])
        # 写入中捕获的 JSON 可能不完整；先确认序号再解析。
        if sequence != struct.unpack_from('<Q', memory, 0)[0]:
            return None
        metadata = json.loads(header)
        descriptors = metadata.get('components')
        if descriptors is None:
            return _read_latest(memory, previous)
        assets, payload = {}, {}
        copied = 0
        for name, component in descriptors.items():
            mode, size = component['mode'], tuple(component['size'])
            offset, version = component['offset'], component['version']
            count = size[0]*size[1]*len(mode)
            if mode not in ('RGB', 'RGBA') or min(size) <= 0 or offset < 0 or offset+count > length:
                raise ValueError('invalid native component storage')
            old = self._assets.get(name)
            compatible = old is not None and old[1:3] == (mode, size)
            if compatible and old[0] == version:
                raw = old[3]
            elif (compatible and old[0] == component['previous'] and component['dirty']):
                left, top, right, bottom = component['dirty']
                if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
                    raise ValueError('invalid native component rectangle')
                if (left, top, right, bottom) == (0, 0, *size):
                    raw = bytes(memory[_DATA+offset:_DATA+offset+count])
                    copied += count
                elif left == 0 and right == size[0]:
                    start, end = top*size[0]*len(mode), bottom*size[0]*len(mode)
                    old_pixels = memoryview(old[3])
                    delta = memory[_DATA+offset+start:_DATA+offset+end]
                    raw = b''.join((old_pixels[:start], delta, old_pixels[end:]))
                    copied += end-start
                else:
                    pixels = bytearray(old[3])
                    row_bytes = (right-left)*len(mode)
                    for y in range(top, bottom):
                        start = (y*size[0]+left)*len(mode)
                        pixels[start:start+row_bytes] = memory[_DATA+offset+start:_DATA+offset+start+row_bytes]
                        copied += row_bytes
                    raw = bytes(pixels)
            else:
                raw = bytes(memory[_DATA+offset:_DATA+offset+count])
                copied += count
            assets[name] = (version, mode, size, raw)
            payload[name] = raw
        if sequence != struct.unpack_from('<Q', memory, 0)[0]:
            return None
        self._assets, self.copied_bytes = assets, copied
        return sequence, metadata, payload


class _PixelStore:
    """Own a Pillow core, but never the Image shell leased to a consumer.

    Pillow's _new wraps the SAME ImagingCore (no pixel copy). Each live shell
    keeps that core alive; the weak reference is an implicit release ACK from
    every holder, including the renderer's pending and active frame. readonly
    makes ordinary Pillow mutations detach rather than edit the reusable core.
    A store is writable only after its last shell has died, including shells
    replaced after consumer COW mutation or close.
    """

    def __init__(self):
        self.core = None
        self.mode = self.size = None
        self.leases = []
        self.dirty = None

    @property
    def available(self):
        self.leases[:] = [lease for lease in self.leases if lease() is not None]
        return not self.leases

    def lend(self, image, on_release):
        self.leases[:] = [lease for lease in self.leases if lease() is not None]
        self.leases.append(weakref.ref(image, on_release))

    def wrap(self):
        from PIL import Image
        return Image.Image()._new(self.core)


class _ImageFrameReader:
    """Three local reusable pixel stores/component; the SHM slot is never lent.

    No complete bytes reassembly or complete RGB decode for sparse updates.
    Free stores accumulate dirty row intervals until reused. Missed source
    versions conservatively invalidate all rows. Retained Images are leases:
    when all stores are held, read returns None, and publication still replaces
    the single shared slot. Production has at most pending + active renderer
    frames plus the reader/decoder's newest frame. Arbitrary client retention
    cannot cause pixel-store allocation growth, even across resize/generation.

    copied_bytes counts SHM -> temporary bytes; decoded_bytes counts raw
    bytes decoded directly into the free reusable core. No patch Image or
    paste is used (patched_bytes stays zero). Cold/full resync touches the
    complete component. Pillow RGB cores use four bytes per pixel.
    """

    def __init__(self, on_release=None):
        self._assets = {}
        self._pools = {}
        self._on_release = on_release
        self._generation = None
        self.copied_bytes = self.decoded_bytes = self.patched_bytes = 0
        self.reassembled_bytes = 0
        self.blocked_reads = 0
        self.frames = 0
        self.total_copied_bytes = self.total_decoded_bytes = self.total_patched_bytes = 0

    @property
    def store_count(self):
        return sum(len(pool) for pool in self._pools.values())

    def _released(self, _reference):
        if self._on_release is not None:
            self._on_release()

    @staticmethod
    def _union(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return min(a[0], b[0]), max(a[1], b[1])

    def read(self, memory, previous):
        from PIL import Image
        sequence = struct.unpack_from('<Q', memory, 0)[0]
        if sequence & 1 or not sequence:
            return None
        header_length, length = struct.unpack_from('<II', memory, 8)
        if header_length > _DATA-64 or _DATA+length > len(memory):
            return None
        header = bytes(memory[64:64+header_length])
        if sequence != struct.unpack_from('<Q', memory, 0)[0]:
            return None
        metadata = json.loads(header)
        generation = metadata.get('generation')
        if sequence == previous and (generation is None or generation == self._generation):
            return None
        descriptors = metadata.get('components')
        if descriptors is None:
            return _read_latest(memory, previous)
        if not set(descriptors).issubset({'canvas', 'sprite', 'text_overlay'}):
            raise ValueError('invalid native component name')
        assets, payload, invalidations, staged, repaired = {}, {}, [], [], []
        copied = 0
        for name, component in descriptors.items():
            mode, size = component['mode'], tuple(component['size'])
            offset, version = component['offset'], component['version']
            if mode not in ('RGB', 'RGBA') or len(size) != 2 or min(size) <= 0:
                raise ValueError('invalid native component storage')
            count = size[0]*size[1]*len(mode)
            if offset < 0 or offset+count > length:
                raise ValueError('invalid native component storage')
            old = self._assets.get(name) if generation == self._generation else None
            compatible = old is not None and old[1:3] == (mode, size)
            if compatible and old[0] == version:
                image, slot = old[3:5]
                try:
                    intact = image.im is slot.core
                except ValueError:  # Pillow rejects .im on a closed shell.
                    intact = False
                if not intact:
                    # COW protects the producer core, but its old shell may
                    # now contain consumer pixels (or be closed). Rewrap the
                    # authoritative core without copying or touching pixels.
                    image = slot.wrap()
                    image.readonly = 1
                    image._native_component = (generation, version, None, None)
                    # Only committed shells are external leases. Registering
                    # an aborted repair would self-wake every blocked retry.
                    # The old cached lease protects this core until commit.
                    repaired.append((slot, image))
                    old = (version, mode, size, image, slot)
                assets[name] = old
                payload[name] = image
                continue
            dirty = (0, size[1])
            if compatible and old[0] == component['previous'] and component['dirty']:
                left, top, right, bottom = component['dirty']
                if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
                    raise ValueError('invalid native component rectangle')
                dirty = (top, bottom)
            pool = self._pools.setdefault(name, [])
            free = [slot for slot in pool if slot.available]
            if not free and len(pool) < 3:
                slot = _PixelStore()
                pool.append(slot)
                free.append(slot)
            if not free:
                self.blocked_reads += 1
                # Stores prepared earlier in this packet are not committed.
                # Their pixel writes remain safe but need a full refresh.
                for slot in staged:
                    slot.dirty = (0, slot.size[1])
                    slot.leases.clear()  # abandoned packet must not wake-spin
                return None
            slot = min(free, key=lambda item: (
                item.mode != mode or item.size != size,
                (item.dirty[1]-item.dirty[0]) if item.dirty else 0))
            if slot.mode != mode or slot.size != size:
                # This core is private and every row is decoded before any
                # lease is published; skip a redundant initial color fill.
                slot.core = Image.new(mode, size, None).im
                slot.mode, slot.size = mode, size
                slot.dirty = (0, size[1])
            rows = self._union(slot.dirty, dirty)
            top, bottom = rows
            stride = size[0]*len(mode)
            start, end = top*stride, bottom*stride
            raw = bytes(memory[_DATA+offset+start:_DATA+offset+end])
            # Raw row bytes decode directly into a FREE core. Decoding a
            # temporary patch Image and pasting it would add an allocation
            # and pixel copy, especially costly for full/cold components.
            decoder = Image._getdecoder(mode, 'raw', (mode, 0, 1))
            try:
                decoder.setimage(slot.core, (0, top, size[0], bottom))
                consumed, error = decoder.decode(raw)
                # Match Image.Image.frombytes' raw-decoder error semantics.
                if consumed >= 0:
                    raise ValueError('not enough image data')
                if error != 0:
                    raise ValueError('cannot decode image data')
            except Exception:
                slot.dirty = (0, size[1])
                raise
            finally:
                decoder.cleanup()
            image = slot.wrap()
            image.readonly = 1
            slot.lend(image, self._released)
            image._native_component = (generation, version, component['previous'],
                                       component['dirty'])
            staged.append(slot)
            copied += end-start
            # Include abandoned seqlock/backpressure attempts in cumulative
            # work, rather than hiding retries behind committed-frame counts.
            self.total_copied_bytes += end-start
            self.total_decoded_bytes += end-start
            payload[name] = image
            assets[name] = (version, mode, size, image, slot)
            invalidations.append((pool, slot, dirty))
        if sequence != struct.unpack_from('<Q', memory, 0)[0]:
            for slot in staged:
                slot.dirty = (0, slot.size[1])
                slot.leases.clear()
            return None
        for pool, chosen, dirty in invalidations:
            for slot in pool:
                if slot is chosen:
                    slot.dirty = None
                elif slot.mode == chosen.mode and slot.size == chosen.size:
                    slot.dirty = self._union(slot.dirty, dirty)
        for slot, image in repaired:
            slot.lend(image, self._released)
        self._assets, self._generation = assets, generation
        self.copied_bytes = self.decoded_bytes = copied
        self.patched_bytes = 0
        self.frames += 1
        return sequence, metadata, payload

    def metrics(self):
        return {'frames': self.frames, 'stores': self.store_count,
                'pixel_store_bytes': sum(slot.size[0]*slot.size[1]*4
                                         for pool in self._pools.values() for slot in pool
                                         if slot.core is not None),
                'shm_read_bytes': self.total_copied_bytes,
                'raw_decode_bytes': self.total_decoded_bytes,
                'patch_decode_bytes': 0,
                'core_paste_bytes': self.total_patched_bytes,
                'byte_accounting': 'logical channel bytes: SHM slice then raw decode into free core; no patch/paste; RGB cores use 4 bytes/pixel; includes retries',
                'reassembled_bytes': 0, 'blocked_reads': self.blocked_reads}

    def close(self):
        # Consumers retain their Image/core until their own final read.
        self._on_release = None
        self._assets.clear()
        self._pools.clear()
