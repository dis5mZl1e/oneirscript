"""单槽共享内存：奇数序号写入中，偶数序号才可读，丢弃被替换的旧帧。"""
import json
import struct

_DATA = 16384
_CAPACITY = 32*1024*1024


def _publish(memory, sequence, metadata, chunks=()):
    header = json.dumps(metadata, separators=(',', ':')).encode('utf8')
    length = sum(map(len, chunks))
    if len(header) > _DATA-64 or _DATA+length > len(memory):
        raise ValueError('native map frame exceeds shared slot capacity')
    struct.pack_into('<Q', memory, 0, sequence+1)
    struct.pack_into('<II', memory, 8, len(header), length)
    memory[64:64+len(header)] = header
    offset = _DATA
    for chunk in chunks:
        memory[offset:offset+len(chunk)] = chunk
        offset += len(chunk)
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
