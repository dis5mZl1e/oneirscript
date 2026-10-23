"""Natural language rendering of typed abilities; never parse prose to evaluate."""
from __future__ import annotations
from ..i18n import get_language, tr
from .board import DESTINATION_LABELS


def item_name(placement, names):
    from ..data.items import ITEM_DEFINITIONS
    return tr(str(names.get(placement.instance_id) or
                  ITEM_DEFINITIONS.get(placement.definition_id, {}).get('name', placement.definition_id)))


def word_phrase(placement, sense, focus, names):
    name = item_name(placement, names)
    if not placement.sentence_written:
        return tr('我把{item}留作尚未写下的念头', item=name)
    if sense.kind == 'node':
        return tr('我把{item}想成{meaning}', item=name,
                  meaning=join_words([tr(s) for s in sorted(sense.semantics)]) or tr('一个安静的意象'))
    if sense.kind == 'act':
        return tr('我握着{item}', item=name) if placement.instance_id == focus else tr('我收着{item}备用', item=name)
    from ..data.items import ITEM_DEFINITIONS
    slot = ITEM_DEFINITIONS.get(placement.definition_id, {}).get('slot', '')
    verb = '我披着{item}' if slot == '自我表层' else '我系着{item}' if slot.startswith('依附物') else '我带着{item}'
    return tr(verb, item=name)


def join_words(parts):
    if get_language() == 'en':
        return ' and '.join(parts) if len(parts) < 3 else ', '.join(parts[:-1]) + ', and ' + parts[-1]
    return '、'.join(parts)


def reaction_phrase(path, board):
    english = get_language() == 'en'
    subject = {'hit': tr('当我命中目标时'), 'hurt': tr('当我受到创伤时'),
               'touch': tr('当我接触液体或气体时'), 'conceive': tr('当我展开构想时')}[path.endpoint]
    conditions = []
    if path.gated:
        conditions.append(tr('若触发位置能够导电'))
    if path.blank_gated:
        conditions.append(tr('若想象力已落入留白的范围'))
    if conditions:
        subject += (', ' if english else '，') + (' and '.join(conditions) if english else '且'.join(conditions))
    piece = next((p for p in board.pieces if p.piece_id == path.terminal_piece
                  and (p.x, p.y) == path.terminal), None)
    where = tr(DESTINATION_LABELS.get(piece.destination_policy if piece else 'event_cell', '事件格'))
    effects = {'spark': tr('我让{where}附近的湿润敌人受到微弱电击', where=where),
               'buffer': tr('我护住自己下一次受到的创伤'),
               'surge': tr('我把触发位置的液体引向较空的邻格'),
               'ember': tr('我在{where}留下一点能燃烧的余温', where=where),
               'voice': tr('我让{where}响起引人回头的轻声', where=where)}
    if path.deferred:
        from dataclasses import replace
        outputs = []
        for node in path.continuation:
            from .grammar import output_allowed
            if not output_allowed(board, node, path.semantics):
                continue
            branch_conditions = next((value for value in path.output_conditions if value[0] == node),
                                     (node, path.gated, path.blank_gated))
            effect_path = replace(path, terminal_piece=node[1], terminal=tuple(node[2:]), deferred=None,
                                  gated=branch_conditions[1], blank_gated=branch_conditions[2])
            full = reaction_phrase(effect_path, board)
            # Strip the repeated event subject only; retain each branch's conditions.
            event_subject = {'hit': tr('当我命中目标时'), 'hurt': tr('当我受到创伤时'),
                'touch': tr('当我接触液体或气体时'), 'conceive': tr('当我展开构想时')}[path.endpoint]
            outputs.append(full[len(event_subject) + 2:] if english else full[len(event_subject) + 1:])
        action = tr('我把这一刻留住，两个回合后{effects}', effects=join_words(outputs) or tr('再试着联想'))
    else:
        action = effects[path.terminal_piece]
    return subject + (', ' if english else '，') + action


def complete_sentence(parts):
    if not parts:
        return tr('我空着双手，让梦暂时保持原样。')
    return ('; ' if get_language() == 'en' else '；').join(parts) + ('.' if get_language() == 'en' else '。')
