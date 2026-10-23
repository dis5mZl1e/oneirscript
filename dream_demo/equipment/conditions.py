"""Pure prefix condition parsing, clause binding and explicit scope ownership."""
from dataclasses import replace

from .function_words import FUNCTION_WORDS
from .relations import SyntaxRelation, compile_relational_row
from .roles import resolve_role, COLUMN_ROLES


def compile_conditions(board, original, column_roles=None):
    from .positional import RowSentence, Voice, Predicate, _compile_row
    roles = tuple(column_roles or COLUMN_ROLES)
    verb_column = roles.index('verb') if 'verb' in roles else 4
    markers = [word for word in board.pieces if word.piece_id in ('word_if', 'word_else')]
    if not markers:
        return original
    rows = list(original)
    placements = {p.instance_id: p for p in board.placements}

    def ids_at(y, start=0, end=8, excluded=()):
        cells = sorted((x, p.instance_id) for p in placements.values() if p.instance_id not in excluded
                       for x, cy in p.cells() if cy == y and start <= x < end)
        return tuple(dict.fromkeys(iid for _, iid in cells))

    def physical(iid, response, y):
        p = placements[iid]
        return tuple(Voice(x, cy, iid, p.definition_id, response) for x, cy in p.cells() if cy == y)

    def dormant(y, reason, ids):
        return replace(original[y], status='dormant', reason=reason, kind='conditional',
                       contracts=(), damage_sources=(), feedback_opcodes=(), action_modes=(),
                       alternatives=(), guard_members=tuple(ids))

    def clause(y, ids, start, end):
        if not ids:
            return dormant(y, '条件分句缺少合法行为', ())
        words = [w for w in board.pieces if w.y == y and start <= w.x < end
                 and w.piece_id not in ('word_if', 'word_else')]
        if any(word.piece_id not in FUNCTION_WORDS for word in words):
            return dormant(y, '条件分句包含旧标点或旧行为填充词', ids)
        shadow = board.clone()
        shadow.placements = [placements[iid] for iid in ids]
        shadow.pieces = words
        voices = tuple(voice for iid in ids for x, cy in placements[iid].cells() if cy == y
                       for response in (resolve_role(placements[iid].definition_id, roles[x]),)
                       if response is not None
                       for voice in (Voice(x, cy, iid, placements[iid].definition_id, response),))
        compiled = _compile_row(y, voices)
        if words:
            return compile_relational_row(y, shadow, compiled, words)
        if len(ids) == 1:
            iid = ids[0]
            response = resolve_role(placements[iid].definition_id, 'verb')
            if response is None:
                return dormant(y, '条件分句缺少合法行为', ids)
            compiled = _compile_row(y, (Voice(verb_column, y, iid, placements[iid].definition_id, response),))
            return replace(compiled, voices=physical(iid, response, y))
        if compiled.status != 'ready' or set(ids) != set(compiled.instance_ids):
            return dormant(y, '条件分句存在多个不明确的行为', ids)
        return compiled

    def guarded(row, predicate, word, donor_id, donor_response, source_row):
        guard = predicate if row.condition is None else Predicate('all', children=(predicate, row.condition))
        relation = SyntaxRelation(word.piece_id,
                                  'conditional' if word.piece_id == 'word_if' else 'alternative_condition',
                                  row.source_id, donor_id, ((donor_id, 'condition'),), word.cells(),
                                  source_row, row.row)
        donors = physical(donor_id, donor_response, row.row)
        members = tuple(dict.fromkeys((donor_id, *row.instance_ids)))
        kind, event = row.kind, row.event
        if predicate.kind == 'event':
            if kind == 'action' or (kind == 'contract' and row.opcode == 'cover'):
                kind, event = 'reaction', predicate.event
            elif kind == 'contract':
                return dormant(row.row, '事件条件需要可执行的响应，不能暂时启用持续契约', members)
            else:
                event = predicate.event
        return replace(row, condition=guard, kind=kind, event=event,
                       contracts=() if predicate.kind == 'event' else
                                 tuple(replace(c, condition=guard) for c in row.contracts),
                       relations=(*row.relations, relation), voices=(*row.voices, *donors),
                       branch_key=row.branch_key or f'{word.piece_id}:{row.source_id}',
                       guard_members=members,
                       alternatives=tuple(guarded(child, predicate, word, donor_id, donor_response, source_row)
                                          for child in row.alternatives))

    if_word = next((w for w in markers if w.piece_id == 'word_if'), None)
    else_word = next((w for w in markers if w.piece_id == 'word_else'), None)
    main, predicate, donor_id, donor_response = None, None, None, None
    if if_word is not None:
        y = if_word.y
        end = else_word.x if else_word is not None and else_word.y == y else 8
        ids = ids_at(y, if_word.x+2, end)
        if ids_at(y, 0, if_word.x):
            rows[y] = dormant(y, '如果需要位于条件之前', ids_at(y))
        elif not ids:
            rows[y] = dormant(y, '如果缺少真实条件', ids_at(y))
        else:
            donor_id = ids[0]
            donor_response = resolve_role(placements[donor_id].definition_id, 'condition')
            first_cell = min(x for x, cy in placements[donor_id].cells() if cy == y)
            if any(w.y == y and if_word.x+2 <= w.x < first_cell for w in board.pieces):
                rows[y] = dormant(y, '如果不能跨越另一个功能词寻找条件', ids)
            elif donor_response is None:
                rows[y] = dormant(y, '如果之后的装备没有条件词义', ids)
            else:
                predicate = Predicate(donor_response.condition_kind, donor_response.event,
                                      donor_response.secondary, donor_id)
                body_ids, body_y, start = ids[1:], y, if_word.x+2
                if not body_ids and end == 8 and y+1 < board.height:
                    body_y, start = y+1, 0
                    if else_word is None or else_word.y != body_y:
                        body_ids = ids_at(body_y, excluded=(donor_id,))
                main = clause(body_y, body_ids, start, end)
                if main.status != 'ready':
                    rows[y] = dormant(y, main.reason, (donor_id, *body_ids))
                    main = None
                else:
                    main = guarded(main, predicate, if_word, donor_id, donor_response, y)
                    rows[body_y] = main
                    if body_y != y:
                        relation = main.relations[-1]
                        rows[y] = RowSentence(y, status='ready', reason='', kind='conditional_header',
                                              condition=predicate, voices=physical(donor_id, donor_response, y),
                                              relations=(relation,), guard_members=main.guard_members)

    if else_word is not None:
        y = else_word.y
        # Ignore continuing cells owned by the first clause when an independent
        # following clause exists; never guess among unrelated preceding rows.
        preceding_ids = main.guard_members if main is not None else ()
        ids = ids_at(y, else_word.x+2, excluded=preceding_ids)
        if not ids and main is not None:
            ids = ids_at(y, else_word.x+2, excluded=(donor_id,))
        if main is None or (y != main.row+1 and y != main.row):
            rows[y] = dormant(y, '否则缺少唯一相邻的如果分句', ids)
        elif y == main.row and (if_word.y != y or else_word.x <= if_word.x):
            rows[y] = dormant(y, '否则需要位于如果分句之后', ids)
        elif ids_at(y, 0, else_word.x, excluded=preceding_ids) and y != main.row:
            rows[y] = dormant(y, '否则需要位于反分句之前', ids)
        else:
            other = clause(y, ids, else_word.x+2, 8)
            if other.status != 'ready':
                rows[y] = dormant(y, other.reason, ids)
            else:
                other = guarded(other, replace(predicate, negated=True), else_word,
                                donor_id, donor_response, main.row)
                if y == main.row:
                    voices = {(v.x, v.y, v.instance_id): v for r in (main, other) for v in r.voices}
                    rows[y] = RowSentence(y, status='ready', reason='', kind='conditional',
                                          voices=tuple(voices.values()), alternatives=(main, other),
                                          guard_members=tuple(dict.fromkeys((*main.guard_members, *other.guard_members))))
                else:
                    rows[y] = other

    owned = {iid for row in rows for iid in row.guard_members}
    for y, row in enumerate(rows):
        if row.guard_members:
            continue
        if owned.intersection(v.instance_id for v in row.voices):
            filtered = tuple(v for v in row.voices if v.instance_id not in owned)
            if row.relations:
                rows[y] = dormant(y, '此成分已归于条件分句', ())
            else:
                rows[y] = _compile_row(y, filtered)
    return tuple(rows)
