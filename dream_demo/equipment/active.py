"""Transient active-clause handles; localization and cooldowns stay live."""
from dataclasses import dataclass
from hashlib import sha256

from .projection import sentence_text
from .runtime import condition_value


@dataclass(frozen=True)
class ActiveSentenceOption:
    key: str
    row: int
    text: str
    opcode: str
    cost: int
    cooldown: float
    range: int
    consumes_source: bool = False
    description: str = '目标：可见失控意识；刻痕保留 3 回合，下次命中时触发一次。'


def clause_key(formation, row):
    return sha256(repr((formation.semantic_signature, row.row, row.branch_key,
                        row.opcode, row.instance_ids)).encode('utf-8')).hexdigest()[:20]


def active_sentence_options(formation, state):
    if state.run_over:
        return ()
    options = []
    seen = set()
    for row in formation.actions:
        if row.opcode not in ('imprint','repair','measure'):
            continue
        if condition_value(row.condition, state) is False:
            continue
        identity = (row.opcode,row.source_id,
                    row.operand_type if row.opcode == 'imprint' else '',row.condition,row.target_kind)
        if identity in seen:
            continue
        seen.add(identity)
        if row.opcode == 'imprint':
            options.append(ActiveSentenceOption(clause_key(formation, row), row.row,
                           sentence_text(row), row.opcode, 1,
                           max(0, state.board_cooldowns.get('imprint', 0)-state.time), 6))
        else:
            from .tools import tool_source
            if tool_source(state,row) is None:
                continue
            description = ('目标：正交相邻的受损墙体；成功消耗一件工具。' if row.opcode == 'repair'
                           else '目标：可见可达的格子；读取最短路径，成功消耗一件卷尺。')
            options.append(ActiveSentenceOption(clause_key(formation,row),row.row,
                           sentence_text(row),row.opcode,0,0,
                           1 if row.opcode == 'repair' else max(state.width,state.height),True,description))
    return tuple(options)
