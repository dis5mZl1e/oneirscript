"""Typed target nouns, pure physical binding, and live world validation."""
from dataclasses import replace

from .relations import SyntaxRelation
from .roles import RoleResponse, resolve_role

TARGET_NOUNS = {
    'focus_ring': ('aimed_cell', '本次瞄准点'),
    'hunting_lanyard': ('attached_hostile', '已有征兆的失控意识'),
    'blank_half_page': ('empty_cell', '无意识体的留白'),
}


def target_response(definition):
    entry = TARGET_NOUNS.get(definition)
    return RoleResponse('object', entry[1], 'target', opcode=entry[0],
                        payload_type='target_'+entry[0]) if entry else None


def target_range(row,state=None):
    if row.opcode == 'repair':
        return 1
    if row.opcode == 'measure' and state is not None:
        return max(state.width,state.height)
    return 6 if row.opcode == 'imprint' else 8 if row.opcode.startswith('spray_') else 12


def target_matches(row, state, *, cell=None, target=None):
    if any(v.response.opcode == 'hospital_pathogen' for v in row.voices):
        if target is None and cell is not None:target=state.entity_at(*cell)
        if 'pathogen' not in getattr(target,'biological_tags',()):return False
    if any(v.response.opcode == 'hospital_adjacent' for v in row.voices):
        point = cell or ((target.x,target.y) if target is not None else None)
        if point is None or abs(point[0]-state.player.x)+abs(point[1]-state.player.y)!=1:return False
    if not row.target_kind:
        return True
    if cell is None or not state.inside_board(*cell) or cell == (state.player.x, state.player.y):
        return False
    if max(abs(cell[0]-state.player.x), abs(cell[1]-state.player.y)) > target_range(row,state):
        return False
    if not state.is_visible(*cell) or not state._has_line_of_sight(state.player.x, state.player.y, *cell):
        return False
    actual = state.entity_at(*cell)
    if target is not None and actual is not target:
        return False
    if row.target_kind == 'aimed_cell':
        return True
    if row.target_kind == 'empty_cell':
        return actual is None
    if row.target_kind == 'attached_hostile':
        return (actual is not None and actual is not state.player and actual.integrity > 0
                and actual.relation in ('失控意识', '玩偶意识体')
                and any(n > 0 for n in actual.portent_attach.values()))
    return False


def compile_targets(board, original):
    from .positional import RowSentence, Voice, _compile_row
    rows = list(original)
    placements = {p.instance_id: p for p in board.placements}

    def ids_at(y, start=0, end=8, excluded=()):
        return tuple(dict.fromkeys(iid for x, iid in sorted(
            (x, p.instance_id) for p in board.placements if p.instance_id not in excluded
            for x, cy in p.cells() if cy == y and start <= x < end)))

    for word in board.pieces:
        if word.piece_id != 'word_toward':
            continue
        y = word.y
        # Until a combined production exists, an extra word is an error rather
        # than an instruction that a native-head reconstruction can discard.
        if any(other is not word and any(cy == y for _, cy in other.cells())
               for other in board.pieces):
            rows[y] = replace(rows[y], status='dormant', reason='向所在行的功能词组合尚不成立',
                              action_modes=(), contracts=(), damage_sources=(), feedback_opcodes=())
            continue
        left, right = ids_at(y, end=word.x), ids_at(y, start=word.x+1)
        previous = rows[y-1] if y else None
        main = None
        target_id = ''
        cross = False
        previous_ids = previous.instance_ids if previous is not None else ()
        fresh_left = tuple(i for i in left if i not in previous_ids)
        fresh_right = tuple(i for i in right if i not in previous_ids)
        if (previous is not None and previous.status == 'ready' and previous.kind == 'action'
                and not fresh_left and len(fresh_right) == 1):
            main, target_id, cross = previous, fresh_right[0], True
        elif len(left) == 1 and len(right) == 1:
            head_id, target_id = left[0], right[0]
        elif not left and len(right) == 2:
            target_id, head_id = right
        else:
            rows[y] = replace(rows[y], status='dormant', reason='向需要唯一目标词和定向行为',
                              action_modes=(), contracts=(), damage_sources=(), feedback_opcodes=())
            continue
        response = target_response(placements[target_id].definition_id)
        if response is None:
            rows[y] = replace(rows[y], status='dormant', reason='这个成分没有合法目标词义',
                              action_modes=(), contracts=(), damage_sources=(), feedback_opcodes=())
            continue
        if not cross:
            head = placements[head_id]
            verb = resolve_role(head.definition_id, 'verb')
            if verb is not None:
                main = _compile_row(y, (Voice(4,y,head_id,head.definition_id,verb),))
                main = replace(main, voices=tuple(Voice(x,cy,head_id,head.definition_id,verb)
                                                 for x,cy in head.cells() if cy == y))
        modes = tuple(mode for mode in main.action_modes
                      if mode in ('fire','imprint','use_tool') or mode.startswith('spray_')) if main else ()
        if main is None or main.status != 'ready' or main.kind != 'action' or not modes:
            rows[y] = replace(rows[y], status='dormant', reason='向的中心词没有合法定向行为',
                              action_modes=(), contracts=(), damage_sources=(), feedback_opcodes=())
            continue
        target = placements[target_id]
        voices = tuple(Voice(x,cy,target_id,target.definition_id,response)
                       for x,cy in target.cells() if cy == y)
        members = tuple(dict.fromkeys((*main.instance_ids, target_id)))
        relation = SyntaxRelation(word.piece_id, 'direction', main.source_id, target_id,
                                  tuple((iid, 'object' if iid == target_id else 'verb') for iid in members),
                                  word.cells(), y, main.row)
        main = replace(main, target_kind=response.opcode, action_modes=modes,
                       instance_ids=members, voices=(*main.voices, *voices),
                       relations=(*main.relations, relation))
        if cross:
            rows[main.row] = main
            rows[y] = RowSentence(y, status='ready', reason='', kind='direction_header',
                                  instance_ids=(target_id,), voices=voices, relations=(relation,))
        else:
            rows[y] = main
    return tuple(rows)
