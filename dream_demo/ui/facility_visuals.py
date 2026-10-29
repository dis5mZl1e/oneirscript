"""特殊设施/战术阵地的只读持续视觉快照（2026-10-26，ASCII 动画扩展 Task 10 S13）。

本模块把 WorldLedger.facilities 里**当前层**的真实记录与地图状态，整理成
供持续字符层使用的不可变快照。它只读：

* 不调用 _action_time / advance / refresh / 支付 / 命令；
* 不写库存、旗标、safe_since、pending 或事实账本；
* 不消耗游戏 RNG，也不触发 emit_visual。

FacilityVisualState 只携带**已授权**的公开信息：

* anchors 是设施定义里的公开布局键 → 世界坐标集合；origin 只是参考点，
  ends 这类聚合键不再合并（配对渡口两端保持各自绝对坐标）。隐藏实体/目标
  （如湿档案室的 guard/reward、走廊奖励）不会进入快照。
* conditions 只给公开条件键与真实满足与否（布尔），不附带任何实体坐标。
* state/pending_stage/progress/remaining 全部来自真实记录与地图；未开始的
  安全段 segment_key 为 None。
* 休眠设施仍返回一条状态（state == "休眠"），但不含任何隐藏几何。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.scenes import SCENE_DEFINITIONS
from ..world import scenes as world_scenes

#: 只读快照不导出的布局键：origin 是参考点；ends 是两端聚合；
#: guard/reward/rewards 是隐藏实体或未公开目标，不参与持续字符层。
_HIDDEN_LAYOUT_KEYS = frozenset({"origin", "ends", "guard", "reward", "rewards"})

_DORMANT = "休眠"


@dataclass(frozen=True)
class FacilityVisualState:
    """一处设施/阵地在真实世界状态下的只读视觉快照（设计 §4.4）。"""

    facility_uid: str
    definition_id: str
    state: str
    anchors: tuple[tuple[str, tuple[tuple[int, int], ...]], ...] = ()
    conditions: tuple[tuple[str, bool], ...] = ()
    pending_stage: str = ""
    progress: float = 0.0
    remaining: float | None = None
    segment_key: str | None = None

    @property
    def dormant(self) -> bool:
        """未看见/未激活：没有公开几何，只保留状态本身。"""
        return self.state == _DORMANT


def _clamp01(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number != number:  # NaN
        return 0.0
    return max(0.0, min(1.0, number))


def _anchor_pairs(record) -> tuple[tuple[str, tuple[tuple[int, int], ...]], ...]:
    """公开布局键 → 绝对世界坐标集合；保持每个键独立，不合并端点。"""
    if not record.layout:
        return ()
    definition = world_scenes.definition_of(record) or {}
    order = [str(key) for key in (definition.get("keys") or ())]
    for key in record.layout:
        if str(key) not in order:
            order.append(str(key))
    anchors: list[tuple[str, tuple[tuple[int, int], ...]]] = []
    for key in order:
        if key in _HIDDEN_LAYOUT_KEYS:
            continue
        cells = record.area(key)
        if not cells:
            continue
        anchors.append((key, tuple((int(x), int(y)) for x, y in cells)))
    return tuple(anchors)


def _condition_name(condition: dict) -> str:
    """公开条件键：type:key（无 key 时退回 name/type），不含坐标。"""
    kind = str(condition.get("type") or "")
    key = condition.get("key")
    if key is None:
        key = condition.get("name")
    return f"{kind}:{key}" if key else kind


def _conditions(state, record, definition) -> tuple[tuple[str, bool], ...]:
    """逐条读真实条件是否满足；只返回布尔，不泄露隐藏目标位置。"""
    if definition is None or record.state == _DORMANT:
        return ()
    out: list[tuple[str, bool]] = []
    for condition in definition.get("conditions") or ():
        try:
            ok, _text = world_scenes._check_one(state, record, condition)
        except Exception:
            # 未知/缺失条件不应让只读快照崩掉；按未满足处理，不臆造成功。
            ok = False
        out.append((_condition_name(condition), bool(ok)))
    return tuple(out)


def _state_name(state, record, definition) -> str:
    if record.state == _DORMANT:
        return _DORMANT
    if definition is not None and definition.get("gate"):
        # 门态只读地从 flags / 位面关停表重算，不调用 refresh 写回记录。
        return world_scenes._gate_state(state, record)
    return str(record.state)


def _hold_state(state, record, definition):
    """安全段：真实世界回合派生 segment_key/progress/remaining。"""
    zones = tuple(definition.get("safe_zones") or ())
    if not zones:
        return "", 0.0, None, None
    now = int(getattr(state, "time", 0) or 0)
    need = max(1, int(definition.get("hold_rounds", 3)))
    active_zone = None
    active_since = 0
    for zone in zones:
        since = record.safe_since.get(zone)
        if since is not None:
            active_zone = zone
            active_since = int(since)
            break
    if active_zone is None:
        return "", 0.0, None, None
    held = max(0, now - active_since)
    proven = bool(record.flags.get(f"safe:{active_zone}"))
    stage = "hold_complete" if proven else "hold_begin"
    segment = f"{record.scene_uid}:{active_zone}:{active_since}"
    remaining = float(max(0, need - held))
    return stage, _clamp01(held / need), remaining, segment


def _scene_lifecycle(state, record, definition):
    """场景设施：门态 / 术阵 pending→land / 连续安全 / 其他。"""
    if definition.get("gate"):
        realm = str((definition.get("gate") or {}).get("realm", ""))
        if realm and realm in state.closed_realms:
            return "gate_closed", 1.0, None
        if record.flags.get("entered"):
            return "gate_enter", 1.0, None
        if record.flags.get("paid"):
            return "gate_paid", 1.0, None
        if record.flags.get("offered"):
            return "gate_offer", 0.0, None
        return "", 0.0, None
    if record.pending:
        # 术阵「预告」：due_seq 是真实行动序号，不是视觉计时器。
        due = int(record.pending.get("due_seq", 0) or 0)
        remaining = max(0, due - int(getattr(state, "action_seq", 0) or 0))
        return "pending", 0.0, float(remaining)
    if record.state == "生效":
        return "land", 1.0, None
    stage, progress, remaining, _segment = _hold_state(state, record, definition)
    if stage:
        return stage, progress, remaining
    return "", 0.0, None


def _encounter_lifecycle(state, record, definition_id: str):
    """战术阵地：只读真实 remaining/flags/state，不碰场景 due_seq。"""
    from ..core import tactical_layouts as layouts

    if definition_id == layouts.MULTI_SOLUTION_GATE:
        if record.flags.get("resolved"):
            return "open", 1.0, 0.0
        return "", 0.0, None
    if definition_id == layouts.WET_ARCHIVE:
        # 湿档案室没有专用仪式：只保留静态状态。
        return "", 0.0, None
    if definition_id == layouts.REWRITING_CORRIDOR:
        pending = record.pending or {}
        if record.state == "已改写":
            return "rewrite", 1.0, 0.0
        remaining = pending.get("remaining")
        if remaining is None:
            return "", 0.0, None
        remaining_value = float(remaining)
        stage = ("deferred" if record.flags.get("deferred") and remaining_value <= 0
                 else "warning")
        progress = 1.0 - remaining_value / float(layouts.REWRITE_DELAY)
        return stage, _clamp01(progress), remaining_value
    return "", 0.0, None


def _snapshot_for(state, record) -> FacilityVisualState:
    definition = world_scenes.definition_of(record)
    definition_id = str(record.definition_id)
    dormant = record.state == _DORMANT or not record.layout
    if dormant:
        return FacilityVisualState(
            facility_uid=str(record.scene_uid),
            definition_id=definition_id,
            state=_DORMANT,
            anchors=(),
            conditions=(),
            pending_stage="",
            progress=0.0,
            remaining=None,
            segment_key=None,
        )
    if definition is not None:
        stage, progress, remaining = _scene_lifecycle(state, record, definition)
    else:
        stage, progress, remaining = _encounter_lifecycle(state, record, definition_id)
    _hold_stage, _hold_progress, _hold_remaining, segment_key = (
        _hold_state(state, record, definition) if definition is not None
        else ("", 0.0, None, None))
    return FacilityVisualState(
        facility_uid=str(record.scene_uid),
        definition_id=definition_id,
        state=_state_name(state, record, definition),
        anchors=_anchor_pairs(record),
        conditions=_conditions(state, record, definition),
        pending_stage=stage,
        progress=_clamp01(progress),
        remaining=remaining,
        segment_key=segment_key,
    )


def facility_visual_states(state) -> tuple[FacilityVisualState, ...]:
    """返回当前层所有真实设施/阵地的只读快照。

    只读取 world_ledger.facilities 与地图上已经存在的真实字段；不刷新、
    不推进时间、不写旗标、不消耗 RNG。顺序按 facility_uid 稳定排序。
    """
    snapshots = []
    for record in world_scenes.records(state):
        if not record.layout:
            # 主线难度/学习工具等账本记录没有地图布局，不构成设施视觉层。
            continue
        if record.definition_id in SCENE_DEFINITIONS:
            snapshots.append(_snapshot_for(state, record))
            continue
        if str(record.definition_id).startswith("encounter."):
            snapshots.append(_snapshot_for(state, record))
            continue
        # 其他模块复用的 FacilityRecord 不在这里猜测几何。
    snapshots.sort(key=lambda entry: entry.facility_uid)
    return tuple(snapshots)


# ---------------------------------------------------------------------------
# 持续字符层：只读快照 -> turn 层 VisualFrame（设计 4.4）
# ---------------------------------------------------------------------------
_STAGE_GLYPHS = {
    "pending": ".:o",
    "warning": ".:o",
    "deferred": ".-",
    "gate_offer": "<>",
    "gate_paid": "[]",
    "gate_enter": "[]",
    "gate_closed": "][",
    "land": ".,",
    "hold_begin": "|:",
    "hold_complete": "|!",
    "rewrite": "/.-",
    "open": "=+",
}


def _stable_seed(text: str) -> int:
    import hashlib

    return int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16) & 0x7FFFFFFF


def _center(cells):
    ordered = tuple(cells)
    return ordered[len(ordered) // 2]


def _event_for(snapshot, cells, seed):
    from types import SimpleNamespace

    center = _center(cells)
    return SimpleNamespace(
        event_id="facility:" + snapshot.facility_uid,
        root_id=snapshot.facility_uid,
        layer_key="facility",
        action_seq=0,
        ordinal=0,
        world_time=0.0,
        kind="facility",
        outcome="release",
        source=center,
        targets=tuple(cells),
        paths=(),
        affected_cells=tuple(cells),
        visual_key="facility",
        tier=1,
        theme="facility",
        seed=seed,
        phase_offset_ms=0,
        facts=(),
    )


def _hold_ticks(frame, cells, progress):
    """安全段：只按真实 held/need 点亮前若干段，不用视觉秒数推进。"""
    from .visual_frame import GlyphLayer

    ordered = tuple(sorted(set(cells)))
    if not ordered:
        return frame
    lit = max(0, min(len(ordered), int(round(len(ordered) * progress))))
    for index, cell in enumerate(ordered[:lit]):
        frame = frame.add_layer(cell, GlyphLayer(
            glyph="|" if index % 2 else ":", color="#8fd8d8", z=40,
            role="ambient", event_id="facility:hold", clock_mode="turn",
            alpha=0.45 + 0.25 * progress,
        ))
    return frame


def facility_visual_frame(states):
    """把只读设施快照变成持续字符层（全部 turn 层，不随装饰时间变化）。

    没有快照、休眠设施或无法安全落格的设施不产生图层；绝不反查世界。
    """
    from .visual_frame import VisualFrame, GlyphLayer
    from .visual_primitives import sample_layer
    from ..data.visual_catalog import LayerRecipe

    frame = VisualFrame()
    if not states:
        return frame
    for snapshot in states:
        if snapshot.dormant or not snapshot.anchors:
            continue
        seed = _stable_seed(snapshot.facility_uid + snapshot.definition_id)
        stage = snapshot.pending_stage or ""
        glyph_chars = _STAGE_GLYPHS.get(stage, ".")
        primitive = "orbit_ring" if stage in (
            "pending", "warning", "deferred", "gate_offer", "hold_begin",
        ) else "steady_glyph"
        layer = LayerRecipe(
            primitive, clock_mode="turn", z=40, role="ambient",
            charset=glyph_chars, alpha=0.55,
            params=(("radius", 1.5), ("count", 8), ("life", 0.5)),
        )
        cells = tuple(cell for _key, points in snapshot.anchors for cell in points)
        if not cells:
            continue
        event = _event_for(snapshot, cells, seed)
        sampled = sample_layer(
            layer, event=event, stage="impact",
            progress=float(snapshot.progress), seed=seed, quality="high")
        if sampled is not None:
            frame = frame.merge(sampled)
        if stage.startswith("hold") or snapshot.segment_key:
            frame = _hold_ticks(frame, cells, float(snapshot.progress))
        if stage in ("gate_closed", "gate_enter"):
            ordered = tuple(sorted(cells))
            for cell, glyph in ((ordered[0], "["), (ordered[-1], "]")):
                frame = frame.add_layer(cell, GlyphLayer(
                    glyph=glyph, color="#ffe6a6", z=41, role="fx",
                    event_id="facility:" + snapshot.facility_uid,
                    clock_mode="turn", alpha=0.8,
                ))
    return frame
