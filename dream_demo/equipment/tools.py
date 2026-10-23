"""Finite native tools: explicit targets without changing their original effect."""
from .roles import CONSUMABLE_TOOLS
from ..materials.walls import wall_def


def tool_source(state,row):
    if not row.consumes_source or 'use_tool' not in row.action_modes:
        return None
    return next((item for item in state.inventory if item.instance_id == row.source_id
                 and item.definition_id in CONSUMABLE_TOOLS and item.quantity > 0),None)


def tool_target_valid(state,row,cell):
    if tool_source(state,row) is None or not state.inside_board(*cell) or not state.is_visible(*cell):
        return False
    x,y=cell
    px,py=state.player.x,state.player.y
    if row.opcode == 'repair':
        wall=state.cell(x,y)
        return (abs(x-px)+abs(y-py) == 1 and wall.solid and wall.wall_kind != '意识边界'
                and wall.integrity < wall_def(wall.wall_kind).integrity)
    if row.opcode == 'measure':
        if cell == (px,py) or state.cell(x,y).solid:
            return False
        path=state.path_to(x,y)
        return bool(path and path[-1] == cell)
    return False


def tool_assist_targets(state,row):
    """A bounded shortlist; measuring never runs a search for every map cell."""
    from .runtime import condition_matches
    from .targets import target_matches
    px,py=state.player.x,state.player.y
    cells=[(px+1,py),(px-1,py),(px,py+1),(px,py-1)]
    if row.opcode == 'measure':
        cells=[(e.x,e.y) for e in state.events if not e.resolved][:16]+cells
        if state.hover_target:
            cells.insert(0,state.hover_target)
    return sorted((cell for cell in dict.fromkeys(cells) if tool_target_valid(state,row,cell)
                   and condition_matches(row.condition,state,cell=cell,target=state.entity_at(*cell))
                   and target_matches(row,state,cell=cell,target=state.entity_at(*cell))),
                  key=lambda cell:(max(abs(cell[0]-px),abs(cell[1]-py)),cell))
