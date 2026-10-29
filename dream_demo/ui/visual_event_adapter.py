"""旧战斗/施法演出到 VisualEvent 的过渡适配（设计 5.2，方案 Task 4）。

只把已经存在的结算快照（casts）转成新事件；不重放、不重算、不触碰世界。
同一段施法只在阶段变化时登记一次，避免每帧重复播放。
"""
from __future__ import annotations

from ..core.visual_events import emit_visual
from ..data.visual_catalog import tier_from_seconds


def visual_key_for(profile: str, motion: str = "", theme: str = "") -> str:
    key = f"profile.{profile}" if profile else "default"
    if motion:
        key += f".{motion}"
    return key


def _cast_signature(cast) -> tuple:
    cells = tuple(getattr(cast, "cells", ()) or ())
    path = tuple(getattr(cast, "path", ()) or ())
    return (
        str(getattr(cast, "profile", "")),
        str(getattr(cast, "motion", "")),
        str(getattr(cast, "theme", "")),
        tuple(getattr(cast, "source", ()) or ()),
        cells,
        path,
        round(float(getattr(cast, "born", 0.0) or 0.0), 3),
        str(getattr(cast, "stage", "")),
    )


class CastEventAdapter:
    """把一个 FxSnapshot.casts 列表增量转换成新视觉事件。"""

    def __init__(self):
        self._emitted: set = set()

    def clear(self) -> None:
        self._emitted.clear()

    def collect(self, state, snapshot) -> tuple:
        casts = tuple(getattr(snapshot, "casts", ()) or ())
        current = {_cast_signature(cast) for cast in casts}
        self._emitted &= current  # 离开快照的施法下次可以重新登记
        events = []
        for cast in casts:
            signature = _cast_signature(cast)
            if signature in self._emitted:
                continue
            self._emitted.add(signature)
            profile = str(getattr(cast, "profile", ""))
            motion = str(getattr(cast, "motion", ""))
            theme = str(getattr(cast, "theme", ""))
            stage = str(getattr(cast, "stage", "release"))
            outcome = "entry" if stage == "charge" else "release"
            path = tuple(getattr(cast, "path", ()) or ())
            cells = tuple(getattr(cast, "cells", ()) or ())
            source = getattr(cast, "source", None)
            targets = cells[-1:] if cells else ()
            life = float(getattr(cast, "life", 0.0) or 0.0)
            visual_key = visual_key_for(profile, motion, theme)
            events.append(emit_visual(
                state,
                kind="cast." + ("charge" if stage == "charge" else "release"),
                outcome=outcome,
                source=source,
                targets=targets,
                paths=(path,) if len(path) > 1 else (),
                affected_cells=cells,
                visual_key=visual_key,
                tier=tier_from_seconds(life),
                theme=theme,
                root_id=str(getattr(cast, "root_id", "") or ""),
                facts=(
                    ("profile", profile),
                    ("motion", motion),
                    ("life", life),
                    ("stage", stage),
                    ("progress", round(float(getattr(cast, "progress", 0.0) or 0.0), 3)),
                ),
                layer_key="cast",
            ))
        return tuple(events)


def events_from_casts(state, casts) -> tuple:
    """一次性（画廊/测试用）转换；真实接入请用 CastEventAdapter 保持增量。"""
    adapter = CastEventAdapter()
    snapshot = type("_Snapshot", (), {"casts": tuple(casts)})()
    return adapter.collect(state, snapshot)
