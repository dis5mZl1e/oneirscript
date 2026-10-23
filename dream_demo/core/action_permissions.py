"""Shared player-action permission checks, before root-frame/world mutation."""
from ..i18n import tr


def stasis_refusal(state):
    if getattr(state,'stasis_turns',0)<=0:
        return None
    from .entities import ActionResult
    return ActionResult(False,tr('凝滞把你钉在了原地（剩余 {n} 回合）。',n=state.stasis_turns))


def root_action_refusal(state, action, args=(), kwargs=None):
    if getattr(state,'stasis_turns',0)<=0 or action in ('wait','_dispatch_apply'):
        return None
    if getattr(state,'_equipment_derived_depth',0):
        return None  # passive/world feedback is not a fresh player command
    if action=='commit_board':
        draft=args[0] if args else (kwargs or {}).get('draft')
        if draft is not None and state.board.same_layout(draft):
            return None
    if action=='use_item':
        index=args[0] if args else (kwargs or {}).get('index',0)
        item=state.inventory[index] if isinstance(index,int) and 0<=index<len(state.inventory) else None
        if item is not None and (
                item.effect in ('container','mirror_insight','hospital_wash_choice',
                                'hospital_positive_choice','fireburst','tar_burst','explosion',
                                'sound_lure','smoke_cloud','ignite_burst','spark_rays','fire_once')
                or item.definition_id in ('spellbook','hospital.hollow_lancet','hospital.filter_sac')):
            return None  # quotation/target/contents only; submissions are guarded
    return stasis_refusal(state)
