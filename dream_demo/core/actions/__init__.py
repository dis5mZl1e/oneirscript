"""玩家动作包（自 core/actions.py 拆分，纯搬家见 docs/megafile-refactor-plan.md）。"""
from __future__ import annotations

import random
from typing import Any, Iterable

from ...i18n import tr
from ...materials import DOOR_KINDS, GAS_DEFINITIONS, TABLE_KINDS, floor_effect_for, portent_def, wall_def
from ..content import ABILITY_DEFINITIONS, ACCESSORY_SLOTS, EQUIPMENT_POOL, EVENT_INSIGHT_CHANCE
from ...data.ids import event_option_id, stable_seed
from ..ballistics import angle_blocked, bounce_direction, trace_path
from .. import throwing
from .. import weapons as weapons_pkg
from ...equipment.root_facts import root_action
from ..cast_fx import animate_ability, animate_consumable, animate_item_action

from ..constants import (
    ACTION_COUNT_LIMIT,
    PORTENT_DURATION_CAP,
    PROJECTILE_MAX_RANGE,
    ActionKind,
)
from .. import Material  # noqa: F401  (ink_doodle/blink 的 SOLID_AGGREGATE 判定)
from ..content import ITEM_DEFINITIONS, PROJECTILE_DEFINITIONS
from ..entities import ActionResult, Entity, Item, WorldItem

from .combat import CombatActionsMixin
from .items import ItemActionsMixin
from .movement import MovementActionsMixin
from .social import SocialActionsMixin, join_details  # noqa: F401  对外 re-export


def weapons_pkg_hand(state):
    from ..weapons import hand_weapon
    return hand_weapon(state)


class PlayerActionMixin(SocialActionsMixin, ItemActionsMixin, CombatActionsMixin, MovementActionsMixin):
    """玩家动作混合层：组合四个动作族子 mixin，对外接口与拆分前一致。"""

