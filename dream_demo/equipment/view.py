"""EquipmentView：所有旧查询经它返回装备、效果与焦点（§9.1）。

不用伪造十几个旧槽名来绕过旧函数；`compat_slots()` 只是迁移期的只读视图，
不参与任何结算——盘面是唯一权威，绝不两处各算一遍。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from .aggregation import diminish_int, diminishing_loss, EFFECT_DECAY
from .board import EquipmentBoard, Placement
from .grammar import ACTIVE, CompiledBoard, board_signature, compile_board
from .senses import resolve

if TYPE_CHECKING:  # pragma: no cover
    from ..core.entities import Item

COMPAT_SLOTS = ("手中意象", "自我表层", "依附物·一", "依附物·二", "惯用物")


class EquipmentView:
    def __init__(self, state):
        self._state = state
        self._signature: object = None
        self._compiled: CompiledBoard | None = None
        self._formation_signature: object = None
        self._formation = None

    # ---- 编译缓存 ----

    @property
    def board(self) -> EquipmentBoard:
        return self._state.board

    def compiled(self) -> CompiledBoard:
        from .projection import project
        # Geometry is cached, live conditions are not. Time/target predicates
        # cannot retain yesterday's eligibility in a board-only cache.
        return project(self.formation(), self._state)

    def invalidate(self) -> None:
        self._signature = None
        self._compiled = None
        self._formation_signature = None
        self._formation = None
        # 装备变化可能改变视距（vision_up / 灯塔透镜）——顺手失效视野缓存
        # （性能 P0，2026-10-10；覆盖测试/调试绕过 apply 的直改）。
        self._state.invalidate_sight_radius()

    def formation(self):
        """Owned position grammar; legacy modes and focus never grant authority."""
        from .positional import compile_formation
        from .syntax import board_roles
        definitions = {item.instance_id: item.definition_id
                       for item in self._state.inventory if item.quantity > 0}
        signature = (board_signature(self.board), tuple(sorted(definitions.items())))
        if self._formation is None or signature != self._formation_signature:
            owned = self.board.clone()
            owned.placements = [p for p in owned.placements
                                if definitions.get(p.instance_id) == p.definition_id]
            self._formation = compile_formation(owned, column_roles=board_roles(owned))
            self._formation_signature = signature
        return self._formation

    def action_choices(self, kind: str, *, target=None, cell=None):
        from .runtime import action_choices
        return action_choices(self.formation(), self._state, kind, target=target, cell=cell)

    def active_sentence_options(self):
        from .active import active_sentence_options
        return active_sentence_options(self.formation(), self._state)

    def plan_action(self, kind: str, *, target=None, cell=None, choice=None):
        from .runtime import plan_action
        return plan_action(self.formation(), self._state, kind, target=target, cell=cell,
                           choice=choice)

    def claim_damage_bonus(self, plan) -> int:
        from .runtime import claim_damage_bonus
        return claim_damage_bonus(self._state, plan)

    # ---- 物品与焦点 ----

    def _item(self, instance_id: str | None):
        if not instance_id:
            return None
        return next(
            (item for item in self._state.inventory if item.instance_id == instance_id),
            None,
        )

    def focus_item(self):
        return None

    def active_instance_ids(self) -> set[str]:
        compiled = self.compiled()
        registered = {a.instance_id for a in compiled.abilities}
        # 无效果的词块（原意句成立但没有 effect）仍算「已装配」。
        for sentence in compiled.sentences:
            if sentence.status == ACTIVE:
                registered.update(sentence.instance_ids)
        return registered

    def placed_items(self) -> list:
        ids = {p.instance_id for p in self.board.placements}
        return [item for item in self._state.inventory if item.instance_id in ids]

    def items(self) -> list:
        """生效句注册的装备（旧 `equipped_items()` 的替代口径）。"""
        active = self.active_instance_ids()
        return [item for item in self._state.inventory if item.instance_id in active]

    def items_with_effect(self, effect: str) -> list:
        ids = self.compiled().instances_with_effect(effect)
        return [item for item in self._state.inventory if item.instance_id in ids]

    def find_effect(self, effect: str):
        return next(iter(self.items_with_effect(effect)), None)

    def has_effect(self, effect: str) -> bool:
        return bool(self.compiled().instances_with_effect(effect))

    def effect_ids(self) -> set:
        return self.compiled().effect_ids()

    # ---- 递减汇总 ----

    def effect_power(self, effect: str, compiled=None) -> int:
        compiled = compiled or self.compiled()
        total = diminish_int(
            compiled.contributions(effect),
            resonating=getattr(self._state, "resonance_turns", 0) > 0,
            ratio=EFFECT_DECAY.get(effect, .5),
        )
        return total

    def effect_loss(self, effect: str, compiled=None) -> float:
        """预览：第二件起贡献不足原值多少（必须明确告知，不能骗玩家）。"""
        compiled = compiled or self.compiled()
        return diminishing_loss(compiled.contributions(effect), ratio=EFFECT_DECAY.get(effect, .5))

    def effect_sources(self, effect: str, compiled=None) -> list[tuple[int, str]]:
        compiled = compiled or self.compiled()
        return compiled.contributions(effect)

    # ---- 焦点与握持 ----

    def focus_placement(self) -> Placement | None:
        return None

    def can_focus(self, instance_id: str) -> bool:
        return False

    def spare_weapons(self) -> list[Placement]:
        return []

    # ---- 兼容读取视图（不参与结算） ----

    def compat_slots(self) -> dict[str, str]:
        """盘面 → 旧五栏名的只读映射（面板列表、测试夹具用；不参与结算）。

        焦点件读作「手中意象」；其余按各自定义的栏位归位，两个「依附物」
        栏位按摆放顺序依次填 依附物·一 / 依附物·二。同一栏位不会重复占用，
        装不下的件不出现在这个视图里（盘面本身仍是完整的）。
        """
        view: dict[str, str] = {}
        accessories: list[Placement] = []
        for placement in self.board.placements:
            slot = self._legacy_slot(placement)
            if slot == "依附物":
                accessories.append(placement)
                continue
            if slot in COMPAT_SLOTS and slot not in view:
                view[slot] = placement.instance_id
        for placement in accessories:
            slot = next(
                (s for s in ("依附物·一", "依附物·二") if s not in view), None
            )
            if slot:
                view[slot] = placement.instance_id
        return view

    def _legacy_slot(self, placement: Placement) -> str:
        """这件盘上物品的旧栏位名：优先看行囊里的实例（合成物品也认）。"""
        item = next(
            (it for it in self._state.inventory
             if it.instance_id == placement.instance_id),
            None,
        )
        if item is not None:
            return str(self._state._placeable_slot(item) or "")
        return str(self._state.item_slot(placement.definition_id) or "")

    def slot_of(self, instance_id: str) -> str | None:
        return next(
            (slot for slot, held in self.compat_slots().items() if held == instance_id),
            None,
        )
