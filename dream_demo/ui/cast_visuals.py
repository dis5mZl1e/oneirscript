"""旧施法回放 -> 新多层字符帧（Task 4/9：替换 paint_casts 主效果）。

只读 app 侧已经登记的回放事件与真实 pending 蓄力状态；不重算、不结算、
不消耗 RNG。输出世界坐标 VisualFrame；图片/字符后端各自合成。
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import hashlib
from types import SimpleNamespace

from ..data.anomaly_skills import FX_PROFILES
from .visual_frame import VisualFrame
from .visual_primitives import sample_layer
from .visual_policy import (ACTIVE_LIMIT, DETAIL_LIMIT, budget_frame, cast_recipe, cast_tier,
                            playback_layers, static_feedback, style_frame, limit_routine_footprint)


@lru_cache(maxsize=256)
def _cast_seed(profile, motion, source):
    raw = f"{profile}|{motion}|{source}".encode("utf-8")
    return int.from_bytes(hashlib.blake2s(raw, digest_size=4).digest(), "big")


def _event(profile, motion, theme, source, cells, path, center, seed):
    return SimpleNamespace(
        event_id="cast:%s:%s:%s" % (profile, motion, source),
        root_id="cast", layer_key="cast", action_seq=0, ordinal=seed,
        world_time=0.0, kind="cast", outcome="release",
        source=tuple(source), center=tuple(center), targets=tuple(cells), paths=(tuple(path),) if len(path) > 1 else (),
        affected_cells=tuple(cells), visual_key="profile.%s.%s" % (profile, motion),
        tier=1, theme=theme, seed=seed, phase_offset_ms=0, facts=(),
    )


def _sample_recipe(recipe, event, stage, progress, quality, *, minimal=False):
    if minimal:
        fallback = static_feedback(recipe, event, stage, progress)
        if fallback is not None:
            return style_frame(fallback, recipe)
    frame = VisualFrame()
    for index, layer in enumerate(playback_layers(
            recipe, stage, tier=event.tier, minimal=minimal)):
        sampled = sample_layer(layer, event=event, stage=stage, progress=progress,
                               seed=event.seed + index * 7919, quality=quality)
        frame = frame.merge(style_frame(sampled, recipe, layer.color_role))
    return limit_routine_footprint(frame, recipe, event, stage, quality, tier=event.tier)


def release_cast_frame(combat_pulses, *, t, quality="high"):
    """app 已确认的施法回放：按装饰时钟推进，一次结算一次主效果。"""
    frame = VisualFrame()
    if quality == "off":
        return frame
    detailed = 0
    seen = set()
    for event, born in sorted(combat_pulses or (), key=lambda pulse: -cast_tier(pulse[0])):
        if detailed >= ACTIVE_LIMIT.get(quality, ACTIVE_LIMIT["low"]):
            break
        profile = str(event.get("profile") or "")
        if not profile:
            continue
        preset = FX_PROFILES.get(profile)
        if preset is None:
            continue
        recipe = cast_recipe(event)
        life = recipe.duration
        age = float(t) - float(born)
        if not 0.0 <= age < life:
            continue
        progress = min(1.0, age / max(1e-6, life))
        stage = "tail" if progress >= .78 else "impact" if progress >= .4 else "release"
        source = tuple(event.get("source") or event.get("center") or (0, 0))
        cells = tuple(tuple(p) for p in (event.get("cells") or ()))
        path = tuple(tuple(p) for p in (event.get("path") or ()))
        center = tuple(event.get("center") or source)
        motion = str(event.get("motion") or "")
        theme = str(event.get("theme") or "")
        signature = (event.get("seq"), event.get("cast_id"), source, cells, path, born)
        if signature in seen:
            continue
        seen.add(signature)
        visual = _event(profile, motion, theme, source, cells or (center,), path, center,
                        seed=_cast_seed(profile, motion, source))
        visual.tier = cast_tier(event)
        visual.event_id = "cast:%s:%s:%s" % (event.get("seq"), source, born)
        frame = frame.merge(_sample_recipe(recipe, visual, stage, progress, quality,
                            minimal=detailed >= DETAIL_LIMIT.get(quality, DETAIL_LIMIT["low"])))
        detailed += 1
    return budget_frame(frame, quality)


def charging_cast_frame(state, *, quality="high"):
    """真实 pending 蓄力：turn 层，进度来自真实 windup，不随装饰时间推进。"""
    from ..core.cast_fx import charging_casts

    frame = VisualFrame()
    if quality == "off":
        return frame
    for cast in charging_casts(state):
        profile = str(cast.get("profile") or "")
        if not profile or FX_PROFILES.get(profile) is None:
            continue
        source = tuple(cast.get("source") or (0, 0))
        cells = tuple(tuple(p) for p in (cast.get("cells") or ()))
        path = tuple(tuple(p) for p in (cast.get("path") or ()))
        motion = str(cast.get("motion") or "")
        theme = str(cast.get("theme") or "")
        recipe = cast_recipe(cast)
        visual = _event(profile, motion, theme, source, cells or (source,), path, source,
                        seed=_cast_seed(profile, motion, source))
        visual.tier = 1
        sampled = _sample_recipe(
            recipe, visual, "entry", float(cast.get("progress") or 0.0), quality)
        # This is a live pending state, not optional settled decoration.
        frame = frame.merge(VisualFrame({cell: tuple(replace(l, clock_mode="turn") for l in layers)
                                        for cell, layers in sampled.glyph_layers.items()},
                                       sampled.backgrounds))
    return frame
