"""Transient settled action facts; never infer absence from a failed command."""
from dataclasses import dataclass, field
from functools import wraps

OBSERVED_EVENTS = frozenset(('hit','hurt','touch','conceive','use_sentence','ignite','voice','ingest','move'))


@dataclass(frozen=True)
class EventFact:
    endpoint: str
    action_id: int
    cell: tuple[int, int] | None
    source_id: str
    recipient_id: str
    damage_kind: str = ''
    amount: int = 0
    target: object = field(default=None, compare=False, repr=False)
    action_plan: object = field(default=None, compare=False, repr=False)


@dataclass
class RootFrame:
    action_id: int
    start_time: int
    start_cell: tuple[int, int]
    location: tuple
    formation: object
    facts: list[EventFact] = field(default_factory=list)
    closed: bool = False
    repeat_claims: set = field(default_factory=set)
    # 世界行动事实（重构方案 §13.3）：与装备事件共用同一帧，一次根动作结算一次。
    world_facts: list = field(default_factory=list)
    fact_claims: set = field(default_factory=set)


def record_event(state, endpoint, **context):
    frame = getattr(state, '_equipment_root_frame', None)
    if frame is None or frame.closed or getattr(state, '_equipment_derived_depth', 0):
        return
    target = context.get('target')
    frame.facts.append(EventFact(endpoint, frame.action_id, context.get('cell'),
                                context.get('source_id', ''), context.get('recipient_id', ''),
                                context.get('damage_kind', ''), int(context.get('amount', 0)), target, context.get('action_plan')))


def settled_event_value(state, endpoint):
    frame = getattr(state, '_equipment_root_frame', None)
    if frame is None or not frame.closed or endpoint not in OBSERVED_EVENTS:
        return None
    return any(fact.endpoint == endpoint for fact in frame.facts)


def settle(state):
    frame = getattr(state, '_equipment_root_frame', None)
    if frame is None or frame.closed:
        return
    if frame.location == (state.depth, state.realm_id, state.realm_depth) and (state.player.x,state.player.y) != frame.start_cell:
        record_event(state, "move", cell=(state.player.x,state.player.y))
    frame.closed = True
    from ..world import facts as world_facts
    # 世界事实先入账，再谈装备反馈：换层/结局时这一帧照样发生过，归因不能丢。
    world_facts.flush(state)
    if state.run_over or frame.location != (state.depth, state.realm_id, state.realm_depth):
        return
    from .library import library_feedback
    for event in frame.facts:
        library_feedback(state, event.endpoint, event.target, event.cell, frame.formation)
    if hasattr(state, "hospital_equipment_feedback"):
        for event in frame.facts:
            state.hospital_equipment_feedback(event.endpoint, event.target, event.cell, frame.formation, action_plan=event.action_plan)
        state.hospital_equipment_feedback("settled", cell=(state.player.x,state.player.y), formation=frame.formation)
    from .positional_events import execute_feedback
    from .runtime import condition_matches
    fact = next((fact for fact in reversed(frame.facts) if fact.target is not None), None)
    target = fact.target if fact else None
    cell = fact.cell if fact else (state.player.x, state.player.y)
    operations = tuple(dict.fromkeys(row.opcode for row in frame.formation.reactions
                       if any(r.operator == 'alternative_condition' for r in row.relations)
                       and condition_matches(row.condition, state, target=target, cell=cell, event='settled')))
    for opcode in operations:
        execute_feedback(state, opcode, cell=cell, target=target)


def root_action(function):
    """Nested public/core entry points share one frame and one finalization."""
    @wraps(function)
    def wrapped(owner, *args, **kwargs):
        state = getattr(owner, 'state', owner)
        from ..core.action_permissions import root_action_refusal
        refused=root_action_refusal(state,function.__name__,args,kwargs)
        if refused is not None:
            return refused
        if getattr(state, '_equipment_root_frame', None) is not None or getattr(state, '_equipment_derived_depth', 0):
            return function(owner, *args, **kwargs)
        frame = RootFrame(state.action_seq, state.time, (state.player.x,state.player.y),
                          (state.depth,state.realm_id,state.realm_depth), state.equipment.formation())
        state._equipment_root_frame = frame
        try:
            result = function(owner, *args, **kwargs)
            actual = (state.action_seq != frame.action_id or state.time != frame.start_time
                      or (state.player.x,state.player.y) != frame.start_cell or bool(frame.facts))
            if getattr(result, 'changed', False) and actual:
                settle(state)
            return result
        finally:
            state._equipment_root_frame = None
    return wrapped
