"""Independent medicine installments on the integer world clock.

Quotes are read-only. Only ingestion, legacy loading and actual world ticks
change the ledger; free inspection and fractional action tails cannot pay it.
"""
from __future__ import annotations

from ..i18n import tr
from .settlement import REASON_DRUG_DEBT, settle_delta

VERSION = 1


def migrate_legacy(state, *, now=None):
    if state.drug_debt_version >= VERSION:
        return
    now = state.time if now is None else now
    turns = max(0, int(state.overclock_turns))
    phase = min(1.999999, max(0.0, float(state.portent_debt.pop('overclock', 0))))
    remaining = int((turns + phase) // 2)
    if turns:
        state.drug_debts.append(dict(resource='lucidity', remaining=remaining,
            next_due=now + 2 - phase, interval=2, deadline=now + turns,
            source='浓缩咖啡因'))
    state.drug_debt_version = VERSION


def add_dose(state, item, *, resource='lucidity', total=5, duration=10):
    migrate_legacy(state)
    interval = duration / total
    state.drug_debts.append(dict(resource=resource, remaining=total,
        next_due=state.time + interval, interval=interval, deadline=state.time + duration,
        source=item.name))
    _sync_legacy_timer(state)


def add_overclock_dose(state, item):
    add_dose(state, item)


def _sync_legacy_timer(state):
    # Compatibility display/debug field, never used to create a second debt.
    state.overclock_turns = max((max(0, int(row['deadline'] - state.time))
                                for row in state.drug_debts if row['resource'] == 'lucidity'), default=0)


def tick(state, previous):
    migrate_legacy(state, now=previous)
    keep = []
    for row in state.drug_debts:
        while row['remaining'] > 0 and row['next_due'] <= state.time:
            settle_delta(state, row['resource'], -1, reason=REASON_DRUG_DEBT,
                         source=row['source'] + '账单', channel='drug_debt')
            row['remaining'] -= 1
            row['next_due'] += row['interval']
            state.messages.append(tr('{item}的账单到了：{resource} −1。',
                                     item=tr(row['source']),
                                     resource=tr('心智' if row['resource'] == 'mind' else '清醒度')))
        # Keep a legacy partial final period without inventing another payment.
        if row['remaining'] > 0 or row['deadline'] > state.time:
            keep.append(row)
    state.drug_debts = keep
    _sync_legacy_timer(state)


def balance(state, *, resource='lucidity'):
    total = sum(int(row['remaining']) for row in state.drug_debts if row['resource'] == resource)
    if resource == 'lucidity' and state.drug_debt_version < VERSION:
        phase = max(0.0, float(state.portent_debt.get('overclock', 0)))
        total += int((max(0, state.overclock_turns) + phase) // 2)
    return total


def prepay_one(state, *, min_floor: int = 1):
    """提前结清**一格**真实药物债务（洞察「药效不等于痊愈」的原语）。

    总债不变少（该付的格数照付），也不提前制造任何恢复：这里只是把最近一格的
    扣款从"到期时"挪到"现在"。扣款仍走 ``settle_delta`` 的同一条 ``drug_debt``
    通道，所以缓冲、记录与失败复盘看到的都是同一笔账。

    ``min_floor``：宁可这一手什么都不做，也不把"主动提前结账"变成自杀——
    付完会让该资源跌到 ≤ ``min_floor`` 时直接返回 None（让到期那笔去扣）。
    """
    migrate_legacy(state)
    rows = [row for row in state.drug_debts
            if int(row['remaining']) > 0 and float(row['next_due']) > state.time]
    if not rows:
        return None
    row = min(rows, key=lambda r: float(r['next_due']))
    if int(getattr(state, row['resource'], 0)) <= min_floor:
        return None
    settle_delta(state, row['resource'], -1, reason=REASON_DRUG_DEBT,
                 source=row['source'] + '账单', channel='drug_debt')
    # next_due 原样保留：剩下的格数仍按原来那一刻扣，提前结的那一格不会连锁提前。
    row['remaining'] = int(row['remaining']) - 1
    return row['resource'], str(row['source']), int(row['remaining'])


def quote(state, item):
    if item.definition_id == 'unfinished_fullstop':
        return tr('本次新增心智债务 8 点，10 回合分期；登记时应付心智合计 {n} 点（含旧债），不覆盖其他账单。',
                  n=balance(state, resource='mind') + 8)
    if item.effect != 'overclock' or item.definition_id == 'modem_56k':
        return ''
    return tr('本次新增清醒度债务 5 点，10 回合分期；登记时应付合计 {n} 点（含旧债），各份按原时刻独立扣款。',
              n=balance(state) + 5)


def mind_debt_status(state):
    import math
    amount = balance(state, resource='mind')
    if amount <= 0:
        return None
    remaining = max(row['deadline'] - state.time for row in state.drug_debts
                    if row['resource'] == 'mind' and row['remaining'] > 0)
    return dict(id='drug_mind_debt', name='心智账单', kind='负面',
        effect=tr('未竟的句点：尚欠心智 {n} 点，按各份原时刻独立分期支付，不可用新药覆盖。', n=amount),
        remaining=str(max(0, math.ceil(remaining))))
