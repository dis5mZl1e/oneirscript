"""Finite player item timing, shared by quotes and action settlement."""
from __future__ import annotations

import math
from ..i18n import tr


def clock(state):
    return float(state.time) + float(state.round_debt)


def modem_phase(state):
    now = clock(state)
    if now < state.modem_boost_until:
        return 'buffer', state.modem_boost_until - now
    if now < state.modem_recovery_until:
        return 'recovery', state.modem_recovery_until - now
    return '', 0.0


def start_modem(state):
    if modem_phase(state)[0]:
        return False
    now = clock(state)
    state.modem_boost_until = now + 8
    state.modem_recovery_until = now + 12
    return True


def modem_time_multiplier(state):
    if getattr(state, 'stasis_turns', 0) > 0:
        return 1.0
    phase, _ = modem_phase(state)
    return .8 if phase == 'buffer' else 1.2 if phase == 'recovery' else 1.0


def modem_source(state):
    factor = modem_time_multiplier(state)
    if factor == 1.0:
        return ''
    return tr('56k 猫：缓冲加速' if factor < 1 else '56k 猫：缓冲迟滞')


def modem_status(state):
    phase, remaining = modem_phase(state)
    if not phase:
        return None
    return dict(id='modem_' + phase,
                name='缓冲加速' if phase == 'buffer' else '缓冲迟滞',
                kind='正面' if phase == 'buffer' else '负面',
                effect=tr('56k 猫：行动耗时 ×0.8，结束后进入 4 回合缓冲迟滞。'
                          if phase == 'buffer' else '56k 猫：行动耗时 ×1.2，等待缓冲恢复。'),
                remaining=str(math.ceil(remaining)))
