"""视觉时间轴与播放器（2026-10-26，ASCII 动画扩展 Task 4）。

VisualClock 有三个互不推算的字段：真实回合时间、动作序号、独立视觉时间。
- turn 层只读真实回合状态/结算快照；decor_time 变化不改变 turn 层。
- settled 层在结算时起播，按 decor_time 一次播完整段，展示作用格固定。
- decorative 层只随 decor_time 变化。

播放器只消费 VisualEvent 快照，不反查世界、不推进游戏时间。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.visual_catalog import recipe_for
from .visual_frame import VisualFrame, merge_frames
from .visual_policy import (ACTIVE_LIMIT, DETAIL_LIMIT, QUALITY_BUDGET, budget_frame, playback_recipe,
                           playback_layers, static_feedback, style_frame,
                           allows_event_trigger, limit_routine_footprint)

STAGE_BY_OUTCOME = {
    "entry": "entry", "charge": "entry", "prepare": "entry", "preview": "entry",
    "release": "release", "cast": "release", "trigger": "release",
    "hit": "impact", "impact": "impact", "land": "impact", "resolve": "impact",
    "tail": "tail", "settle": "tail", "end": "tail",
}
_QUALITY_BUDGET = QUALITY_BUDGET


@dataclass(frozen=True)
class VisualClock:
    world_time: float
    action_seq: int
    decor_time: float


@dataclass
class _Instance:
    event: object
    recipe: object
    born_decor: float
    born_world: float
    stage: str
    dedupe: tuple


class VisualPlayer:
    """管理活动实例、去重与采样；不启动第二套终端刷新循环。"""

    def __init__(self, *, sampler=None, catalog_lookup=None):
        self._instances: list[_Instance] = []
        self._seen: set = set()
        self._sampler = sampler
        self._catalog = catalog_lookup or recipe_for

    # ---- 生命周期 -----------------------------------------------------
    def accept(self, events, now: VisualClock) -> int:
        accepted = 0
        for event in events:
            key = _event_dedupe(event)
            if key in self._seen:
                continue
            recipe = self._catalog(getattr(event, "visual_key", "default"))
            if not allows_event_trigger(event, recipe):
                continue
            self._seen.add(key)
            recipe = playback_recipe(recipe, getattr(event, "tier", recipe.tier),
                                     str(getattr(event, "kind", "")))
            outcome = str(getattr(event, "outcome", "release"))
            stage = STAGE_BY_OUTCOME.get(outcome, "release")
            offset = float(getattr(event, "phase_offset_ms", 0)) / 1000.0
            self._instances.append(_Instance(
                event=event,
                recipe=recipe,
                born_decor=float(now.decor_time) + offset,
                born_world=float(now.world_time),
                stage=stage,
                dedupe=key,
            ))
            accepted += 1
        return accepted

    def clear(self) -> None:
        self._instances.clear()
        self._seen.clear()

    def discard_all(self) -> None:
        """读档/换层：清实例但保留去重键？设计要求旧实例与去重一起清。"""
        self.clear()

    @property
    def pending(self) -> bool:
        return bool(self._instances)

    @property
    def instance_count(self) -> int:
        return len(self._instances)

    # ---- 采样 ---------------------------------------------------------
    def sample(self, now: VisualClock, quality: str = "high") -> VisualFrame:
        per_cell, _total = _QUALITY_BUDGET.get(str(quality), _QUALITY_BUDGET["low"])
        if not per_cell:
            self._expire(now)
            return VisualFrame()
        # 先在采样前过期：已到寿命的实例不能再画最后一帧，否则会残影一帧。
        self._expire(now)
        frames = []
        kept = []
        sampled = 0
        ordered = sorted(self._instances, key=lambda i: -i.recipe.tier)
        for instance in ordered:
            if float(now.decor_time) < instance.born_decor:
                kept.append(instance)
                continue
            has_turn = any(layer.clock_mode == "turn" for layer in instance.recipe.layers)
            if not has_turn and sampled >= ACTIVE_LIMIT.get(quality, ACTIVE_LIMIT["low"]):
                continue  # Drop optional overload now; never queue a late replay.
            kept.append(instance)
            frame = self._sample_instance(instance, now, quality,
                          minimal=sampled >= DETAIL_LIMIT.get(quality, DETAIL_LIMIT["low"]))
            if not has_turn:
                sampled += 1
            if frame is not None:
                frames.append(frame)
        self._instances = kept
        if not frames:
            return VisualFrame()
        return budget_frame(merge_frames(*frames), quality)

    def sample_event(self, event, now: VisualClock, quality: str = "high") -> VisualFrame:
        """画廊/测试用：不加入活动实例也能采样单个事件。"""
        recipe = self._catalog(getattr(event, "visual_key", "default"))
        if not allows_event_trigger(event, recipe):
            return VisualFrame()
        recipe = playback_recipe(recipe, getattr(event, "tier", recipe.tier),
                                 str(getattr(event, "kind", "")))
        outcome = str(getattr(event, "outcome", "release"))
        stage = STAGE_BY_OUTCOME.get(outcome, "release")
        instance = _Instance(
            event=event, recipe=recipe,
            born_decor=float(now.decor_time) + float(getattr(event, "phase_offset_ms", 0)) / 1000.0,
            born_world=float(now.world_time), stage=stage,
            dedupe=_event_dedupe(event),
        )
        frame = self._sample_instance(instance, now, quality)
        return frame or VisualFrame()

    def _expired(self, instance: _Instance, now: VisualClock) -> bool:
        if instance.recipe.duration <= 0:
            return True
        if all(layer.clock_mode == "turn" for layer in instance.recipe.layers):
            return False  # turn 实例由下一回合事件/显式 clear 替换
        elapsed = float(now.decor_time) - instance.born_decor
        return elapsed >= instance.recipe.duration

    def _expire(self, now: VisualClock) -> None:
        self._instances = [
            instance for instance in self._instances
            if not self._expired(instance, now)
        ]

    def _sample_instance(self, instance: _Instance, now: VisualClock, quality: str, *, minimal=False):
        recipe = instance.recipe
        layers = playback_layers(recipe, instance.stage, tier=recipe.tier, minimal=minimal)
        if not layers:
            return None
        elapsed = float(now.decor_time) - instance.born_decor
        if elapsed < 0.0:
            return None  # phase_offset 只推迟装饰起播，不移动真实阶段
        progress = 1.0 if recipe.duration <= 0 else min(1.0, elapsed / recipe.duration)
        if minimal:
            fallback = static_feedback(recipe, instance.event, instance.stage, progress)
            if fallback is not None:
                return style_frame(fallback, recipe)
        sampler = self._sampler or _default_sampler()
        frames = []
        for index, layer in enumerate(layers):
            if layer.clock_mode == "turn":
                layer_progress = 1.0
            else:
                layer_progress = progress
            frame = sampler(
                layer,
                event=instance.event,
                stage=instance.stage,
                progress=layer_progress,
                seed=int(getattr(instance.event, "seed", 0)) + index * 7919,
                quality=quality,
            )
            if frame is not None and not frame.is_empty:
                frames.append(style_frame(frame, recipe, layer.color_role))
        if not frames:
            return None
        return limit_routine_footprint(merge_frames(*frames), recipe, instance.event,
                                       instance.stage, quality)


def _event_dedupe(event) -> tuple:
    return (
        getattr(event, "layer_key", ""),
        int(getattr(event, "action_seq", 0)),
        int(getattr(event, "ordinal", 0)),
        str(getattr(event, "kind", "")),
        str(getattr(event, "root_id", "")),
    )


def _default_sampler():
    from .visual_primitives import sample_layer
    return sample_layer
