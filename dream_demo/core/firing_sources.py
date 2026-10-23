"""Firing-source discovery and per-instance magazine/reload facts.

Direct-fire settlement uses these magazine rules. Sprayers retain material
capacity and have no magazine; legacy migration and source unification remain partial.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from .content import ITEM_DEFINITIONS

LEGACY_BASIC_ID = "legacy_basic_fire"
LEGACY_BASIC_NAME = "基础发射（旧档继承）"


@dataclass(frozen=True)
class MagazineSpec:
    capacity: int
    reload_time: int
    reload_cost: int


# 设计文档 §5.2 初值已接入直射结算；仍待完整多来源与平衡验收。
MAGAZINE_SPECS: dict[str, MagazineSpec] = {
    "echo_emitter": MagazineSpec(4, 1, 2),
    "binder_clip_launcher": MagazineSpec(4, 1, 2),
    "voice_recorder_pen": MagazineSpec(3, 1, 2),
    "line_projector": MagazineSpec(3, 2, 3),
    "nail_gun": MagazineSpec(2, 2, 3),
    "sonic_whistle": MagazineSpec(3, 2, 3),
    "dart_gun": MagazineSpec(2, 2, 3),
    "hospital.hollow_lancet": MagazineSpec(3, 2, 3),
    "legacy_basic_fire": MagazineSpec(3, 2, 3),
}


def magazine_spec(definition_id: str) -> MagazineSpec | None:
    """Return the proposed magazine rule for one physical weapon definition."""
    return MAGAZINE_SPECS.get(str(definition_id or ""))


@dataclass(frozen=True)
class ReloadQuote:
    needed: int
    cost: int          # this step; 0 after the first step was paid
    steps: int         # remaining real actions
    can_start: bool
    paid: bool = False
    reason: str = ""
    total_cost: int = 0
    total_steps: int = 0

    @property
    def done_steps(self) -> int:
        return max(0, self.total_steps - self.steps)


def reload_quote(item) -> ReloadQuote | None:
    """Read-only reload price; never spends time, imagination or a step."""
    spec = magazine_spec(getattr(item, "definition_id", ""))
    if spec is None or getattr(item, "magazine", None) is None:
        return None
    current = max(0, int(item.magazine))
    needed = max(0, spec.capacity - current)
    done = int(getattr(item, "reload_steps", 0) or 0)
    remaining = max(0, spec.reload_time - done)
    paid = bool(getattr(item, "reload_paid", False))
    if needed <= 0:
        return ReloadQuote(0, 0, 0, False, paid=paid, reason="满弹匣")
    if remaining <= 0:
        return ReloadQuote(needed, 0, 0, False, paid=paid, reason="换弹已完成",
                           total_cost=spec.reload_cost, total_steps=spec.reload_time)
    return ReloadQuote(needed, 0 if paid else spec.reload_cost, remaining, True, paid,
                       total_cost=spec.reload_cost, total_steps=spec.reload_time)


def legacy_basic_view(state):
    """Read-only view of the migrated inherited source, or None.

    Kept as a tiny adapter so reload quotes and the magazine HUD can read the
    inherited source exactly like a physical weapon without inventing an item.
    """
    if getattr(state, "legacy_basic_magazine", None) is None:
        return None
    spec = MAGAZINE_SPECS[LEGACY_BASIC_ID]
    return SimpleNamespace(
        definition_id=LEGACY_BASIC_ID,
        instance_id=LEGACY_BASIC_ID,
        name=LEGACY_BASIC_NAME,
        magazine=max(0, min(spec.capacity, int(state.legacy_basic_magazine))),
        magazine_capacity=spec.capacity,
        reload_steps=max(0, min(spec.reload_time,
                                  int(getattr(state, "legacy_basic_reload_steps", 0) or 0))),
        reload_paid=bool(getattr(state, "legacy_basic_reload_paid", False)),
    )


def write_legacy_basic(state, view) -> None:
    state.legacy_basic_magazine = max(0, int(view.magazine))
    state.legacy_basic_reload_steps = max(0, int(view.reload_steps))
    state.legacy_basic_reload_paid = bool(view.reload_paid)


def ensure_magazine(item):
    """Initialise a weapon's per-instance magazine without refilling it later."""
    spec = magazine_spec(getattr(item, "definition_id", ""))
    if spec is None:
        return None
    if getattr(item, "magazine", None) is None:
        item.magazine = spec.capacity
        item.magazine_capacity = spec.capacity
        item.magazine_rule = 1
    elif not getattr(item, "magazine_capacity", 0):
        item.magazine_capacity = spec.capacity
    return item.magazine


def equipment_emitters(state, kind: str, choice_key: str | None) -> tuple:
    """Physical weapons a compiled action fires, in plan order.

    Shared by availability, HUD quotes and reload routing so none of them
    rebuilds the emitter list (and none of them falls back to "first source id").
    """
    try:
        plan = state.equipment.plan_action(kind, choice=choice_key)
    except Exception:
        return ()
    items = []
    for source_id, _shots in getattr(plan, "emitters", ()):
        item = state.equipment._item(source_id) if source_id else None
        if item is not None:
            items.append(item)
    return tuple(items)


@dataclass(frozen=True)
class FiringSource:
    key: str
    kind: str                 # equipment | aggregate | item
    action_kind: str          # fire / spray_liquid / spray_gas / ""
    choice_key: str
    definition_ids: tuple[str, ...]
    instance_ids: tuple[str, ...]
    count: int | None
    can_fire: bool
    reason: str = ""
    emitter_ids: tuple[str, ...] = ()
    target_pending: bool = False


def _equipment_sources(state) -> list[FiringSource]:
    sources: list[FiringSource] = []
    for kind in ("fire", "spray_liquid", "spray_gas"):
        try:
            choices = state.equipment.action_choices(kind)
        except Exception:
            continue
        for choice in choices:
            plan = state.equipment.plan_action(kind, choice=choice.key)
            # Target-only conditions must stay selectable until a target is chosen;
            # report the reason instead of hiding the source.
            can_fire = bool(plan.valid or plan.requires_target)
            reason = "" if can_fire else (plan.reason or "当前动作句不成立")
            # Availability follows the physical emitters the action really fires,
            # not whichever source id happens to be listed first.
            for source_id, _shots in getattr(plan, 'emitters', ()):
                item = state.equipment._item(source_id)
                if item is None:
                    can_fire, reason = False, "选定的发射来源已经失效。"
                    break
                ensure_magazine(item)
                if getattr(item, 'magazine', None) is not None and item.magazine < max(1,int(_shots)):
                    can_fire, reason = False, ("弹匣已空，请先换弹。" if item.magazine<=0 else "弹匣不足，请先换弹。")
                    break
            sources.append(FiringSource(
                key=f"equipment:{kind}:{choice.key}",
                kind="equipment",
                action_kind=kind,
                choice_key=choice.key,
                definition_ids=tuple(choice.definition_ids),
                instance_ids=tuple(choice.source_ids),
                count=None,
                can_fire=can_fire,
                reason=reason,
                emitter_ids=tuple(source_id for source_id, _shot in getattr(plan, 'emitters', ())),
                target_pending=bool(plan.requires_target),
            ))
    return sources


def collect_firing_sources(state) -> tuple[FiringSource, ...]:
    """Return explicit sources in stable order: equipment, inherited, aggregate, one-shot."""
    sources = _equipment_sources(state)
    legacy = legacy_basic_view(state)
    if legacy is not None:
        sources.append(FiringSource(
            key=LEGACY_BASIC_ID, kind="legacy", action_kind="fire",
            choice_key=LEGACY_BASIC_ID,
            definition_ids=(LEGACY_BASIC_ID,), instance_ids=(),
            count=legacy.magazine, can_fire=legacy.magazine > 0,
            reason="" if legacy.magazine > 0 else "弹匣已空，请先换弹。",
        ))
    charges = int(getattr(state, "projectile_charges", 0) or 0)
    if charges > 0:
        sources.append(FiringSource(
            key="aggregate", kind="aggregate", action_kind="fire", choice_key="",
            definition_ids=(), instance_ids=(), count=charges, can_fire=True,
        ))
    for item in getattr(state, "inventory", ()):
        definition = ITEM_DEFINITIONS.get(getattr(item, "definition_id", ""))
        if not definition or definition.get("effect") != "fire_once":
            continue
        quantity = int(getattr(item, "quantity", 0) or 0)
        if quantity <= 0:
            continue
        sources.append(FiringSource(
            key=f"item:{getattr(item, 'instance_id', '')}",
            kind="item", action_kind="fire_once", choice_key="",
            definition_ids=(item.definition_id,),
            instance_ids=(str(getattr(item, "instance_id", "")),),
            count=quantity, can_fire=quantity > 0,
        ))
    return tuple(sources)
