"""临时视觉事件合同（2026-10-26，ASCII 动画扩展 Task 1）。

真实结算/编辑动作在这里登记不可变事实快照；渲染层只消费这些快照，
禁止在渲染时反查世界猜结果。本模块不依赖 UI、不读写存档、不消耗游戏 RNG。

设计要点（spec 5.2）：

- VisualEvent 身份稳定：同一 (layer_key, action_seq, ordinal, kind, root_id)
  产生同一 event_id；seed 由事件身份派生，供字符发射器做确定性扰动。
- emit_visual 只入队，不推进时间、不扣费、不改世界；drain_visual_events
  原子取出并清空，重复调用第二次为空（单次事件只播放一次）。
- 队列挂在 state 的旁路表（按 id + weakref 清理），不写进 dataclass 字段，
  因此不会进入存档/快照；读档或换层由 UI 调用 reset_visual_events。
- facts 只允许不可变标量，避免把对象引用或未过滤世界快照塞进事件。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import weakref

_Scalar = str | int | float | bool
_Point = tuple[int, int]


@dataclass(frozen=True)
class VisualEvent:
    """一次真实结算的只读视觉事实（spec 5.2）。"""

    event_id: str
    root_id: str
    parent_id: str | None
    layer_key: str
    action_seq: int
    ordinal: int
    world_time: float
    kind: str
    outcome: str
    source_id: str | None
    source: _Point | None
    targets: tuple[_Point, ...]
    paths: tuple[tuple[_Point, ...], ...]
    affected_cells: tuple[_Point, ...]
    visual_key: str
    tier: int
    theme: str
    seed: int
    phase_offset_ms: int = 0
    facts: tuple[tuple[str, _Scalar], ...] = ()

    @property
    def cells(self) -> tuple[_Point, ...]:
        """All geometric cells mentioned by this event, deduplicated and stable."""
        seen: dict[_Point, None] = {}
        if self.source is not None:
            seen[self.source] = None
        for point in (*self.targets, *self.affected_cells):
            seen[point] = None
        for path in self.paths:
            seen.update(dict.fromkeys(path))
        return tuple(seen)

    def fact(self, key: str, default=None):
        for name, value in self.facts:
            if name == key:
                return value
        return default


@dataclass
class _EventQueue:
    ref: weakref.ref
    events: list
    ordinal: int = 0


_QUEUES: dict[int, _EventQueue] = {}
# 面板/冻结期间不 drain，队列必须有上限：只保留最近事件，避免无限增长。
MAX_PENDING_EVENTS = 256


def _key(state) -> int:
    return id(state)


def _purge(key: int) -> None:
    _QUEUES.pop(key, None)


def _queue_for(state) -> _EventQueue:
    key = _key(state)
    queue = _QUEUES.get(key)
    if queue is not None and queue.ref() is state:
        return queue
    queue = _EventQueue(weakref.ref(state), [])
    _QUEUES[key] = queue
    try:
        weakref.finalize(state, _purge, key)
    except TypeError:  # pragma: no cover - 极少数不可弱引用对象（测试假状态）
        pass
    return queue


def _point(value):
    if value is None:
        return None
    x, y = value
    return int(x), int(y)


def _scalar_pairs(facts):
    pairs = []
    for item in facts:
        if len(item) != 2:
            raise ValueError(f"视觉事实必须是 (key, scalar) 对: {item!r}")
        name, value = item
        if not isinstance(name, str) or not name:
            raise ValueError(f"视觉事实键必须是非空字符串: {name!r}")
        if isinstance(value, bool):
            pass
        elif isinstance(value, (int, float, str)):
            if isinstance(value, float) and value != value:
                raise ValueError("视觉事实不允许 NaN")
        else:
            raise TypeError(f"视觉事实只允许标量，收到 {type(value).__name__}")
        pairs.append((name, value))
    return tuple(sorted(pairs, key=lambda pair: pair[0]))


def _make_seed(*parts) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


def emit_visual(state, *, kind: str, outcome: str, source, targets=(),
                paths=(), affected_cells=(), visual_key: str, tier: int,
                theme: str = '', root_id=None, parent_id=None, source_id=None,
                phase_offset_ms: int = 0, facts=(), layer_key=None) -> VisualEvent:
    """登记一次真实结果；不改世界、不消耗游戏 RNG、不写存档。"""
    queue = _queue_for(state)
    world_time = float(getattr(state, "time", 0.0) or 0.0)
    action_seq = int(getattr(state, "action_seq", 0) or 0)
    root = str(root_id) if root_id is not None else ''
    layer = str(layer_key) if layer_key is not None else kind
    ordinal = queue.ordinal
    queue.ordinal += 1
    src = _point(source)
    target_tuple = tuple(_point(point) for point in targets if point is not None)
    path_tuple = tuple(tuple(_point(point) for point in path) for path in paths)
    affected = tuple(_point(point) for point in affected_cells)
    pairs = _scalar_pairs(facts)
    event_id = "v" + hashlib.sha1(
        "|".join(str(part) for part in (
            layer, action_seq, ordinal, kind, outcome, root,
            visual_key, src, target_tuple, affected,
        )).encode("utf-8")
    ).hexdigest()[:20]
    event = VisualEvent(
        event_id=event_id,
        root_id=root or event_id,
        parent_id=str(parent_id) if parent_id is not None else None,
        layer_key=layer,
        action_seq=action_seq,
        ordinal=ordinal,
        world_time=world_time,
        kind=kind,
        outcome=outcome,
        source_id=str(source_id) if source_id is not None else None,
        source=src,
        targets=target_tuple,
        paths=path_tuple,
        affected_cells=affected,
        visual_key=visual_key,
        tier=int(tier),
        theme=str(theme),
        seed=_make_seed(event_id, layer, root),
        phase_offset_ms=int(phase_offset_ms),
        facts=pairs,
    )
    queue.events.append(event)
    if len(queue.events) > MAX_PENDING_EVENTS:
        del queue.events[:len(queue.events) - MAX_PENDING_EVENTS]
    return event


def _result_signature(event: VisualEvent) -> tuple:
    """同一真实结果被两个登记点/两次调用重复压入时的折叠键。"""
    # root_id 未显式给出时会回退成 event_id，两个重复登记因此 root 不同；
    # 折叠键故意不含 root_id，只保留真实结果内容与派生父事件。
    return (event.layer_key, event.action_seq, event.kind,
            event.parent_id, event.source, event.targets, event.affected_cells,
            event.visual_key, event.facts)


def drain_visual_events(state) -> tuple:
    """原子取出本次未消费事件并清空；第二次 drain 返回空。

    同一真实结果被并发/多通道重复登记时折叠为一次（只保留首个）。
    """
    queue = _QUEUES.get(_key(state))
    if queue is None or queue.ref() is not state:
        return ()
    events = []
    seen = set()
    for event in queue.events:
        signature = _result_signature(event)
        if signature in seen:
            continue
        seen.add(signature)
        events.append(event)
    queue.events.clear()
    return tuple(events)


def peek_visual_events(state) -> tuple:
    queue = _QUEUES.get(_key(state))
    if queue is None or queue.ref() is not state:
        return ()
    return tuple(queue.events)


def reset_visual_events(state) -> None:
    """读档/换层/新游戏时清空待播与序号，避免补播历史事件。"""
    _QUEUES.pop(_key(state), None)


def dedupe_key(event: VisualEvent) -> tuple:
    """跨旧/新管线的稳定去重键：一个真实行动最多播一次。"""
    return (event.layer_key, event.action_seq, event.ordinal, event.kind, event.root_id)
