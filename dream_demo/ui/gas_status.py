"""Readable inhalation state; other gas effects keep their independent rules."""

from ..i18n import tr
from ..materials import CONTAINER_KINDS, PORTENT_DEFINITIONS, material_portents


def gas_contact_threshold(state, cell) -> int | None:
    thresholds = [state._gas_portent_min(cell,PORTENT_DEFINITIONS[pid])
                  for pid in material_portents(cell.gas_kind)]
    return min(thresholds) if thresholds else None


def gas_contact_text(state, cell, *, detail: bool = False) -> str:
    if cell.wall_kind in CONTAINER_KINDS:
        return tr('封存气体')
    threshold = gas_contact_threshold(state,cell)
    if threshold is None:
        return tr('无吸入征兆')
    label = ('可见残迹' if cell.gas < threshold else
             '浓气核心' if cell.gas >= 60 else '可吸入浓度')
    if detail:
        return tr('{status} · 吸入门槛 ≥{threshold}',status=tr(label),threshold=threshold)
    return tr(label)
