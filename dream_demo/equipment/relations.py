"""Typed grammatical binding, independent of translated labels and the world.

Physical equipment positions stay unchanged. Relations select the head,
property, patient or manner first; virtual grammatical slots are only an
adapter to the existing row compiler, never physical cells or hit boxes.
"""
from dataclasses import dataclass, replace

from .function_words import FUNCTION_WORDS
from .roles import FEEDBACK_FROM_MODIFIER, resolve_role


@dataclass(frozen=True)
class SyntaxRelation:
    word_id: str
    operator: str
    head_id: str
    donor_id: str
    role_bindings: tuple[tuple[str, str], ...]
    word_cells: tuple[tuple[int, int], ...]
    source_row: int = -1
    target_row: int = -1


# 「地」的方式词义 → 相容的行为族（opcode 前缀匹配）。
# roles.resolve_role('modifier') 能给出的全部词义都在表里：武器「锋利」与
# 8 种效果修饰。不再只认 swift_strike——那让「地」在玩家手里几乎永远
# 编不成句子（2026-10-10 反馈：虚词基本没有适配条件）。
MANNER_FAMILIES = {
    'swift_strike': ('strike', 'fire'),
    'pierce_up': ('fire',),
    'spray_boost': ('spray_liquid', 'spray_gas'),
    'attach_hunt': ('strike', 'fire'),
    'fire_affinity': ('fire',),
    'blast_radius': ('fire',),
    'repair_up': ('repair',),
    'throw_master': ('fire', 'strike'),
    'wet_conduct': ('strike', 'fire', 'spray_liquid', 'spray_gas'),
    'cut': ('strike', 'fire'),
}


def _manner_matches(effect: str, opcode: str) -> bool:
    family = MANNER_FAMILIES.get(effect)
    if not family:
        return False
    return any(opcode == mode or opcode.startswith(mode) for mode in family)


def _coordinate_row(index, word, placements, left, right, invalid):
    from .positional import Voice, _compile_row
    if not left or not right:
        return invalid('并列需要左右各有一个合法成分')
    left_id, right_id = left[-1][1], right[0][1]
    if set(placements) != {left_id, right_id}:
        return invalid('并列成分存在歧义')
    participants = tuple(dict.fromkeys((left_id, right_id)))
    rows = []
    physical = []
    for iid in participants:
        placement = placements[iid]
        response = resolve_role(placement.definition_id, 'verb')
        if response is None:
            return invalid('并列成分没有合法行为')
        compiled = _compile_row(index, (Voice(4, index, iid, placement.definition_id, response),))
        if compiled.status != 'ready':
            return invalid('并列成分没有合法行为')
        rows.append(compiled)
        physical.extend(Voice(x, y, iid, placement.definition_id, response)
                        for x, y in placement.cells() if y == index)
    kinds = {row.kind for row in rows}
    if len(kinds) != 1 or kinds - {'action', 'contract'}:
        return invalid('并列行为类型不相容')
    modes = rows[0].action_modes
    if rows[0].kind == 'action':
        # One projectile cannot simultaneously be a pulse, a dart and a spray.
        # Melee remains independently usable even if their fire modes differ.
        def profile(row, mode):
            prefix = 'fire_' if mode == 'fire' else 'spray_'
            values = tuple((key, value) for key, value in row.action_profile
                           if key.startswith(prefix) and key not in (prefix+'damage', prefix+'time'))
            return (dict(row.action_profile).get('projectile_template', '直线弹体'), values)
        modes = tuple(mode for mode in modes if all(mode in row.action_modes for row in rows)
                      and (mode == 'melee' or all(profile(row, mode) == profile(rows[0], mode)
                                               for row in rows)))
        if not modes or any(row.consumes_source for row in rows):
            return invalid('并列行为类型不相容')
    contracts = {(c.instance_id, c.effect, c.condition): c for row in rows for c in row.contracts}
    damage = {(s.instance_id, s.channel): s for row in rows for s in row.damage_sources}
    relation = SyntaxRelation(word.piece_id, 'coordinate', right_id, left_id,
                              tuple((iid, 'verb') for iid in participants), word.cells())
    return replace(rows[0], instance_ids=participants, action_modes=modes,
                   contracts=tuple(contracts.values()), damage_sources=tuple(damage.values()),
                   feedback_opcodes=tuple(dict.fromkeys(op for row in rows for op in row.feedback_opcodes)),
                   voices=tuple(physical), relations=(relation,))


def _alternative_row(index, word, placements, left, right, invalid):
    from .positional import RowSentence, Voice, _compile_row
    if not left or not right:
        return invalid('或者需要左右各有一个候选成分')
    left_id, right_id = left[-1][1], right[0][1]
    if set(placements) != {left_id, right_id}:
        return invalid('候选成分存在歧义')
    ids = tuple(dict.fromkeys((left_id, right_id)))
    physical = []
    branches = []
    group = f'{word.piece_id}:{word.x}:{word.y}'
    for iid in ids:
        placement = placements[iid]
        response = resolve_role(placement.definition_id, 'verb')
        if response is None:
            continue
        voices = tuple(Voice(x, y, iid, placement.definition_id, response)
                       for x, y in placement.cells() if y == index)
        physical.extend(voices)
        compiled = _compile_row(index, (Voice(4, index, iid, placement.definition_id, response),))
        if compiled.status == 'ready' and compiled.kind == 'action':
            branches.append(replace(compiled, voices=voices, branch_group=group, branch_key=iid))
    relation = SyntaxRelation(word.piece_id, 'alternative', right_id, left_id,
                              tuple((iid, 'verb') for iid in ids), word.cells())
    return RowSentence(index, status='ready' if branches else 'dormant',
                       reason='' if branches else '候选成分没有可执行的主动行为', kind='alternative',
                       instance_ids=ids, voices=tuple(physical), relations=(relation,),
                       alternatives=tuple(branches))


# 「被」：作用类型 → 玩家实际承受的创伤记账类型（root facts 的 hurt.kind）。
# 刀兵之伤（cut）= 清醒/身体类创伤；留白侵蚀（blank）= 心智类创伤。
# 其余作用类型还没有可靠的外界观察入口，保持休眠，不能凭空解释每一次受击。
PASSIVE_TRIGGERS = {'cut': 'lucidity', 'blank': 'mind'}
# 反馈执行器已有的被动原语：斩击、静电、点燃、护持。
PASSIVE_RESPONSES = ('strike', 'shock', 'ignite', 'cover')


def _passive_row(index, word, board, default_row, invalid=None):
    """「X 被 Y」：X 的行为改为被动响应，Y 决定监听的外界作用类型。

    触发时必须收到真实根事件（来源、承受者、类型、结算后损失）；反应仍受
    反馈预算、家族冷却与想象力约束。X 不再主动生效，也不从其他占格行绕回。
    """
    from .positional import Voice, _compile_row, RowSentence

    def reject(reason):
        return replace(default_row, status='dormant', reason=reason,
                       contracts=(), damage_sources=(), feedback_opcodes=(),
                       action_modes=())

    placements = {}
    occupied = []
    for placement in board.placements:
        xs = [x for x, y in placement.cells() if y == index]
        if xs:
            placements[placement.instance_id] = placement
            occupied.extend((x, placement.instance_id) for x in xs)
    left = sorted((x, iid) for x, iid in occupied if x < word.x)
    right = sorted((x, iid) for x, iid in occupied if x >= word.x + len(FUNCTION_WORDS[word.piece_id].cells))
    if not left or not right:
        return reject('被需要左侧承受者和右侧作用')
    if set(placements) != {left[-1][1], right[0][1]}:
        return reject('被的关联成分存在歧义')
    patient_id, agent_id = left[-1][1], right[0][1]
    if patient_id == agent_id:
        return reject('同一实体不能既是承受者又是作用')
    patient, agent = placements[patient_id], placements[agent_id]
    agent_response = resolve_role(agent.definition_id, 'object')
    hurt_kind = PASSIVE_TRIGGERS.get(agent_response.payload_type) if agent_response else None
    if not hurt_kind:
        return reject('这个作用还没有可观察的外界入口')
    response = resolve_role(patient.definition_id, 'verb')
    if response is None:
        return reject('承受者没有可被动触发的行为')
    compiled = _compile_row(index, (Voice(4, index, patient_id, patient.definition_id, response),))
    if compiled.status != 'ready':
        return compiled
    opcode = compiled.opcode if compiled.kind != 'contract' else 'cover'
    if opcode not in PASSIVE_RESPONSES:
        return reject('这个行为还没有对应的被动响应')
    relation = SyntaxRelation(word.piece_id, 'passive', patient_id, agent_id,
                              ((patient_id, 'verb'), (agent_id, 'object')), word.cells())
    physical = tuple(Voice(x, y, p.instance_id, p.definition_id, r)
                     for p, r in ((patient, response), (agent, agent_response))
                     for x, y in p.cells() if y == index)
    return replace(compiled, kind='reaction', event='hurt', hurt_kind=hurt_kind,
                   opcode=opcode, action_modes=(), contracts=(), damage_sources=(),
                   feedback_opcodes=(), instance_ids=(patient_id, agent_id),
                   voices=physical, relations=(relation,))


def compile_relational_row(index, board, default_row, words):
    from .positional import RowSentence, Voice, _compile_row
    if any(w.piece_id == 'word_again' for w in words):
        from .repetition import compile_repetition
        return compile_repetition(index,board,default_row,words)
    if len(words) == 1 and words[0].piece_id == 'word_bei':
        return _passive_row(index, words[0], board, default_row, invalid=None)
    only = next((w for w in words if w.piece_id == 'word_only'), None)
    if len(words) == 2 and only is not None:
        other = next(w for w in words if w is not only)
        cells = [x for p in board.placements for x, y in p.cells() if y == index]
        if any(x < only.x for x in cells) or other.x < only.x:
            return replace(default_row, status='dormant', reason='只需要位于所限定的行为之前',
                           contracts=(), damage_sources=(), feedback_opcodes=(), action_modes=())
        base = compile_relational_row(index, board, default_row, [other])
        if (base.status != 'ready' or base.kind != 'action' or not base.relations
                or base.relations[0].operator not in ('attribution', 'manner')):
            return replace(default_row, status='dormant', reason='只需要一个明确的主动行为',
                           contracts=(), damage_sources=(), feedback_opcodes=(), action_modes=())
        head_id = base.relations[0].head_id
        placement = next(p for p in board.placements if p.instance_id == head_id)
        response = resolve_role(placement.definition_id, 'verb')
        compiled = _compile_row(index, (Voice(4, index, head_id, placement.definition_id, response),))
        mode = 'melee' if response.opcode == 'strike' else response.opcode
        if mode not in response.action_modes:
            return replace(default_row, status='dormant', reason='只需要一个明确的主动行为',
                           contracts=(), damage_sources=(), feedback_opcodes=(), action_modes=())
        physical = tuple(replace(v, response=response if v.instance_id == head_id else
                                 replace(v.response, role='excluded', kind='silent', meaning='未采用联想'))
                         for v in base.voices)
        relation = SyntaxRelation(only.piece_id, 'restriction', head_id, head_id,
                                  tuple((iid, 'verb' if iid == head_id else 'excluded')
                                        for iid in base.instance_ids), only.cells())
        return replace(compiled, action_modes=(mode,), voices=physical,
                       instance_ids=base.instance_ids, feedback_opcodes=(), contracts=(),
                       relations=(relation,))
    if len(words) != 1:
        return replace(default_row, status='dormant', reason='多个功能词需要明确的组合关系',
                       contracts=(), damage_sources=(), feedback_opcodes=())
    word = words[0]
    spec = FUNCTION_WORDS[word.piece_id]
    placements = {}
    occupied = []
    for placement in board.placements:
        xs = [x for x, y in placement.cells() if y == index]
        if xs:
            placements[placement.instance_id] = placement
            occupied.extend((x, placement.instance_id) for x in xs)
    left = sorted((x, iid) for x, iid in occupied if x < word.x)
    right = sorted((x, iid) for x, iid in occupied if x >= word.x + len(spec.cells))

    def invalid(reason):
        return replace(default_row, status='dormant', reason=reason,
                       contracts=(), damage_sources=(), feedback_opcodes=(), action_modes=())

    if spec.operator == 'coordinate':
        return _coordinate_row(index, word, placements, left, right, invalid)
    if spec.operator == 'alternative':
        return _alternative_row(index, word, placements, left, right, invalid)
    if spec.operator == 'origin':
        if left:
            return invalid('从需要位于材料来源之前')
        ids = tuple(dict.fromkeys(iid for _, iid in right))
        if len(ids) != 2:
            return invalid('从需要一个真实来源和一个喷射行为')
        donor_id, head_id = ids
        donor, head = placements[donor_id], placements[head_id]
        from ..data.items import ITEM_DEFINITIONS
        container = ITEM_DEFINITIONS.get(donor.definition_id, {}).get('container', {})
        medium = container.get('medium')
        response = resolve_role(head.definition_id, 'verb')
        if medium not in ('liquid', 'gas') or response is None or response.opcode != 'spray_' + medium:
            return invalid('材料来源与喷射行为不相容')
        response = replace(response, action_modes=(response.opcode,))
        compiled = _compile_row(index, (Voice(4, index, head_id, head.definition_id, response),))
        donor_response = replace(resolve_role(donor.definition_id, 'object'),
                                 payload_type='container_' + medium,
                                 meaning=ITEM_DEFINITIONS[donor.definition_id]['name'])
        relation = SyntaxRelation(word.piece_id, 'origin', head_id, donor_id,
                                  ((donor_id, 'object'), (head_id, 'verb')), word.cells())
        physical = tuple(Voice(x, y, p.instance_id, p.definition_id, r)
                         for p, r in ((donor, donor_response), (head, response))
                         for x, y in p.cells() if y == index)
        return replace(compiled, instance_ids=ids, action_modes=(response.opcode,),
                       voices=physical, relations=(relation,))
    if spec.operator == 'restriction':
        if left:
            return invalid('只需要位于所限定的行为之前')
        ids = tuple(dict.fromkeys(iid for _, iid in right))
        if not ids:
            return invalid('只缺少后续行为')
        if len(ids) != 1:
            return invalid('只的行为存在歧义')
        head_id = ids[0]
        head = placements[head_id]
        response = resolve_role(head.definition_id, 'verb')
        if response is None or response.kind != 'action':
            return invalid('只需要一个明确的主动行为')
        mode = 'melee' if response.opcode == 'strike' else response.opcode
        if mode not in response.action_modes:
            # Tool repair/measure share one executor, not a second effect.
            if response.action_modes == ('use_tool',):
                mode = 'use_tool'
            else:
                return invalid('只需要一个明确的主动行为')
        response = replace(response, action_modes=(mode,))
        compiled = _compile_row(index, (Voice(4, index, head_id, head.definition_id, response),))
        relation = SyntaxRelation(word.piece_id, 'restriction', head_id, head_id,
                                  ((head_id, 'verb'),), word.cells())
        physical = tuple(Voice(x, y, head_id, head.definition_id, response)
                         for x, y in head.cells() if y == index)
        # _compile_row resolves the native verb again; enforce the selected
        # mode afterwards without changing its native profile or consumption.
        return replace(compiled, action_modes=(mode,), voices=physical,
                       feedback_opcodes=(), contracts=(), relations=(relation,))
    if spec.operator not in ('attribution', 'manner', 'disposal'):
        return invalid('此功能词的关系求值尚未接入')
    if spec.operator == 'disposal':
        if left:
            return invalid('把需要位于处置对象之前')
        ids = tuple(dict.fromkeys(iid for _, iid in right))
        if len(ids) != 2:
            return invalid('把需要后接一个处置对象和一个行为')
        donor_id, head_id = ids
    else:
        if not left:
            return invalid('缺少属性或方式来源')
        if not right:
            return invalid('缺少中心词或行为')
        donor_id, head_id = left[-1][1], right[0][1]
    if donor_id == head_id:
        return invalid('同一实体不能通过自身孔洞建立修饰关系')
    if set(placements) != {donor_id, head_id}:
        return invalid('功能词的关联成分存在歧义')

    donor, head = placements[donor_id], placements[head_id]
    head_response = resolve_role(head.definition_id, 'verb')
    if head_response is None:
        return invalid('中心词没有合法行为')
    modifier = None
    if spec.operator == 'manner':
        donor_response = resolve_role(donor.definition_id, 'modifier', reading='manner')
        if (donor_response is None or not _manner_matches(donor_response.effect,
                                                          head_response.opcode)):
            return invalid('方式词义与这个行为不相容')
        donor_response = replace(donor_response, meaning='轻快' if donor_response.effect == 'swift_strike'
                                 else donor_response.meaning, kind='modifier')
        modifier = (donor_id, donor_response.effect, donor_response.power)
        donor_column = 2
    else:
        donor_response = resolve_role(donor.definition_id, 'object')
        if donor_response is None:
            return invalid('缺少合法属性或处置对象')
        payload = donor_response.payload_type
        if spec.operator == 'attribution':
            # A property does not become the action's patient. In particular,
            # "blade's fire" cannot silently turn into "imprint the blade".
            if head_response.opcode not in ('strike', 'fire'):
                return invalid('属性与中心词的行为不相容')
            if payload in ('heat', 'electric', 'cut'):
                donor_response = replace(donor_response, role='modifier', kind='modifier',
                                         meaning='锋利' if payload == 'cut' else donor_response.meaning)
            else:
                # The accessory's default ongoing tempo becomes a local action
                # modifier. The runtime already executes this primitive and
                # prevents double counting a live contract from the same item.
                property_response = resolve_role(donor.definition_id, 'modifier')
                if property_response is None or property_response.effect != 'swift_strike':
                    return invalid('属性与中心词的行为不相容')
                donor_response = replace(property_response, meaning='轻快')
                modifier = (donor_id, donor_response.effect, donor_response.power)
                donor_column = 2
        else:
            head_response = resolve_role(head.definition_id, 'verb', payload)
            if not (head_response is not None and head_response.opcode == 'imprint'
                    and payload == 'cut'):
                # 扩展（2026-10-10）：容器对象接对应的喷射行为——「把水喷出」。
                # 原先「把」只支持 imprint+cut 一种组合，玩家几乎凑不出来。
                native = resolve_role(head.definition_id, 'verb')
                medium = payload.split('_', 1)[1] if payload.startswith('container_') else ''
                if (not medium or native is None
                        or native.opcode != 'spray_' + medium):
                    return invalid('处置行为不能接受这个对象类型')
                head_response = replace(native, action_modes=(native.opcode,))
        if modifier is None:
            donor_column = 5

    virtual = (Voice(donor_column, index, donor_id, donor.definition_id, donor_response),
               Voice(4, index, head_id, head.definition_id, head_response))
    compiled = _compile_row(index, virtual)
    if compiled.status != 'ready':
        return compiled
    relation = SyntaxRelation(word.piece_id, spec.operator, head_id, donor_id,
                              ((donor_id, donor_response.role), (head_id, 'verb')), word.cells())
    physical_voices = []
    for placement, response in ((donor, donor_response), (head, head_response)):
        for x, y in placement.cells():
            if y == index:
                physical_voices.append(Voice(x, y, placement.instance_id, placement.definition_id, response))
    feedback = compiled.feedback_opcodes
    damage = compiled.damage_sources
    if modifier and modifier[2] > 0:
        # 裸修饰（positional._compile_row）与「地/的」共用同一张反馈映射。
        opcode = FEEDBACK_FROM_MODIFIER.get(modifier[1])
        if opcode:
            feedback = tuple(dict.fromkeys((*feedback, opcode)))
        if modifier[1] == 'throw_master':
            from .roles import DamageSource
            damage = (*damage, DamageSource(donor_id, donor.definition_id, modifier[2]))
    return replace(compiled, relations=(relation,), voices=tuple(physical_voices),
                   feedback_opcodes=feedback, damage_sources=damage,
                   action_modifiers=(modifier,) if modifier else ())


def enforce_restriction_scope(rows, board=None):
    """A tall restricted word cannot regain its discarded modes on another row."""
    from .positional import _compile_row

    def walk(row):
        yield row
        for child in row.alternatives:
            yield from walk(child)

    owners = {iid for row in rows for node in walk(row)
              for relation in node.relations if relation.operator in ('restriction', 'origin', 'direction','repetition','passive')
              for iid, _ in relation.role_bindings}
    origin_rows = set()
    if board is not None:
        # A deleted source must not reactivate the head on its lower rows.
        for word in board.pieces:
            if word.piece_id in ('word_from', 'word_toward','word_again','word_bei'):
                origin_rows.add(word.y)
                owners.update(p.instance_id for p in board.placements
                              if any(y == word.y and (x > word.x or word.piece_id == 'word_toward')
                                     for x, y in p.cells()))
    if not owners:
        return rows

    def scoped(row):
        if row.alternatives:
            return replace(row, alternatives=tuple(scoped(child) for child in row.alternatives))
        if row.row in origin_rows or any(r.operator in ('restriction', 'origin', 'direction','repetition','passive') for r in row.relations):
            return row
        if not owners.intersection(v.instance_id for v in row.voices):
            return row
        voices = tuple(v for v in row.voices if v.instance_id not in owners)
        if row.relations:
            return replace(row, status='dormant', reason='此成分已归于限定行为',
                           action_modes=(), damage_sources=(), feedback_opcodes=(), contracts=())
        return _compile_row(row.row, voices)

    return tuple(scoped(row) for row in rows)
