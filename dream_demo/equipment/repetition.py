"""One additional phase from an existing root budget, never a new root."""
from dataclasses import replace
from .relations import SyntaxRelation


def compile_repetition(index,board,default_row,words):
    from .positional import Voice,_compile_row
    from .roles import resolve_role
    from .relations import compile_relational_row
    word = next(w for w in words if w.piece_id == 'word_again')
    participants = [p for p in board.placements if any(y == index for _,y in p.cells())]
    def invalid(reason):
        return replace(default_row,status='dormant',reason=reason,action_modes=(),contracts=(),
                       damage_sources=(),feedback_opcodes=())
    if any(x < word.x for p in participants for x,y in p.cells() if y == index) or any(
            other.x < word.x for other in words if other is not word):
        return invalid('再需要位于所追加的行为之前')
    others = [w for w in words if w is not word]
    if others:
        base = compile_relational_row(index,board,default_row,others)
    elif len(participants) == 1:
        head = participants[0]
        response = resolve_role(head.definition_id,'verb')
        if response is None:
            return invalid('再需要一个可追加的真实行为')
        base = _compile_row(index,(Voice(4,index,head.instance_id,head.definition_id,response),))
        base = replace(base,voices=tuple(Voice(x,y,head.instance_id,head.definition_id,response)
                                        for x,y in head.cells() if y == index))
    else:
        return invalid('再需要唯一且明确的后续行为')
    mode = 'melee' if base.opcode == 'strike' else base.opcode
    if base.status != 'ready' or base.kind != 'action' or mode not in ('melee','fire','spray_liquid','spray_gas'):
        return invalid('这个行为的有界追加执行尚未接入')
    relation = SyntaxRelation(word.piece_id,'repetition',base.source_id,base.source_id,
                              tuple((iid,'verb' if iid == base.source_id else 'bound')
                                    for iid in base.instance_ids),word.cells())
    return replace(base,action_modes=(mode,),relations=(*base.relations,relation))


def record_phase(state,plan,opcode,amount,*,cell,target=None):
    from .root_facts import record_event
    if amount > 0:
        record_event(state,'phase',cell=cell,target=target,amount=amount,damage_kind=opcode,
                     source_id=plan.primary_source_id,recipient_id=target.id if target else '')


def claim_repeat(state,plan,opcode,*,cell,target=None):
    from .runtime import condition_matches
    from .targets import target_matches
    frame = getattr(state,'_equipment_root_frame',None)
    if (not plan.repeat_source_ids or frame is None or frame.closed or state.run_over
            or getattr(state,'_equipment_derived_depth',0)
            or frame.location != (state.depth,state.realm_id,state.realm_depth)
            or plan.semantic_signature != state.equipment.formation().semantic_signature):
        return False
    key = (opcode,plan.repeat_source_ids)
    if key in frame.repeat_claims or not any(f.endpoint == 'phase' and f.damage_kind == opcode
            and f.source_id == plan.primary_source_id and f.amount > 0 for f in frame.facts):
        return False
    if not any(row.source_id in plan.repeat_source_ids and condition_matches(
               row.condition,state,cell=cell,target=target) and target_matches(
               row,state,cell=cell,target=target) for row in plan.rows):
        return False
    frame.repeat_claims.add(key)
    return True


def reserved_damage(plan,damage):
    if not plan or plan.kind not in ('melee','fire') or not plan.repeat_source_ids:
        return 0
    total = sum(source.value**2 for source in plan.damage_sources)
    repeated = sum(source.value**2 for source in plan.damage_sources
                   if source.instance_id in plan.repeat_source_ids)
    return int(damage*repeated/(2*total)) if total else 0
