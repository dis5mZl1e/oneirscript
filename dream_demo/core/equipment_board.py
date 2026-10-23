"""携带意象联想盘的运行期接线：事务、握持焦点、根事件与旧存档迁移。

盘面是唯一权威：`equipped` 只作为迁移期的兼容读取视图暴露，不参与结算，
也不会与盘面各算一遍。整理是一次事务——验证整盘后原子提交，无效操作和
取消不耗时。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.items import ITEM_DEFINITIONS
from ..equipment import events as board_events
from ..equipment.board import EquipmentBoard, Placement
from ..equipment.item_shapes import is_registered, shape_for, is_material_source
from ..equipment.senses import default_sense, resolve
from ..equipment.shapes import ROTATIONS
from ..equipment.view import EquipmentView
from ..equipment.root_facts import root_action
from ..i18n import tr

MEMORY_SLOT = "记忆槽"


class LegacyEquipmentSlots:
    """旧五栏名的写通视图：读是派生快照，写落到联想盘。

    盘面始终是唯一权威——这里不会另存一份栏位状态，也不会与盘面各算一遍。
    保留它只为旧调用点（含测试夹具）在迁移期继续可用；玩家侧的整理入口是
    :meth:`EquipmentBoardMixin.equip_item` / :meth:`unequip_item` /
    :meth:`switch_focus`，它们要付一次行动。
    """

    def __init__(self, state):
        self._state = state

    def _snapshot(self) -> dict[str, str]:
        return self._state.equipment.compat_slots()

    def __getitem__(self, slot: str) -> str:
        return self._snapshot()[slot]

    def __contains__(self, slot: object) -> bool:
        return slot in self._snapshot()

    def __iter__(self):
        return iter(self._snapshot())

    def __len__(self) -> int:
        return len(self._snapshot())

    def __repr__(self) -> str:  # pragma: no cover - 调试可读性
        return f"<联想盘兼容视图 {self._snapshot()}>"

    def get(self, slot: str, default=None):
        return self._snapshot().get(slot, default)

    def keys(self):
        return self._snapshot().keys()

    def values(self):
        return self._snapshot().values()

    def items(self):
        return self._snapshot().items()

    def __setitem__(self, slot: str, instance_id: str | None) -> None:
        if not instance_id:
            self.pop(slot, None)
            return
        state = self._state
        focus = slot == "手中意象"
        if state.board.placement(instance_id) is None:
            state.board_place_instance(instance_id, focus=focus, charge_time=False, quiet=True)

    def pop(self, slot: str, default=None):
        instance_id = self._snapshot().get(slot)
        if not instance_id:
            return default
        self._state.board_remove_instance(instance_id, charge_time=False, quiet=True)
        return instance_id

    def clear(self) -> None:
        self._state.board.clear()
        self._state.equipment.invalidate()


class EquipmentBoardMixin:
    """盘面事务与事件入口。字段声明在 GameState 本体（见 core/state.py）。"""

    # ---- 视图 ----

    @property
    def equipment(self) -> EquipmentView:
        view = getattr(self, "_equipment_view", None)
        if view is None:
            view = EquipmentView(self)
            self._equipment_view = view
        return view

    @property
    def equipped(self) -> LegacyEquipmentSlots:
        """旧五栏兼容视图（读派生、写落盘）。新代码一律走 :attr:`equipment`。"""
        view = getattr(self, "_legacy_slots", None)
        if view is None:
            view = LegacyEquipmentSlots(self)
            self._legacy_slots = view
        return view

    @equipped.setter
    def equipped(self, value) -> None:
        """整体赋值 = 用一份旧五栏字典重排盘面（清空后逐件自动安置）。

        盘面仍是唯一权威：这里不另存字典，只做一次「按旧栏位名重摆」的
        事务性写入，不消耗行动时间（迁移与测试夹具的路径）。
        """
        mapping = dict(value.items()) if hasattr(value, "items") else dict(value or {})
        self.board.clear()
        self.equipment.invalidate()
        for slot, instance_id in mapping.items():
            if instance_id:
                self.board_place_instance(
                    instance_id, focus=slot == "手中意象",
                    charge_time=False, quiet=True,
                )

    def item_slot(self, definition_id: str) -> str | None:
        definition = ITEM_DEFINITIONS.get(definition_id)
        return str(definition.get("slot") or "") or None if definition else None

    def _placeable_slot(self, item) -> str | None:
        """这件物品能不能上盘：先看定义表，再看实例自带的 slot（合成物品用）。"""
        slot = self.item_slot(item.definition_id)
        if is_material_source(item.definition_id):
            return '材料来源'
        if slot is None:
            slot = str(getattr(item, "slot", "") or "") or None
        return None if slot == MEMORY_SLOT else slot

    def is_board_equipment(self, definition_id: str) -> bool:
        slot = self.item_slot(definition_id)
        return (bool(slot) and slot != MEMORY_SLOT) or is_material_source(definition_id)

    def _equipment_ids(self) -> set[str]:
        ids = {
            definition_id for definition_id in ITEM_DEFINITIONS
            if self.is_board_equipment(definition_id)
        }
        for item in self.inventory:
            if self._placeable_slot(item):
                ids.add(item.definition_id)
        return ids

    # ---- 事务 ----

    def board_draft(self) -> EquipmentBoard:
        """免费预览用的影子状态：渲染、旋转、悬停都不改属性、RNG 或世界时间。"""
        return self.board.clone()

    def draft_errors(self, draft: EquipmentBoard) -> list[str]:
        items = {item.instance_id: item for item in self.inventory if item.quantity > 0}
        owned = set(items)
        problems = draft.errors(allowed_instances=owned,
                                equipment_ids=self._equipment_ids())
        for placement in draft.placements:
            item = items.get(placement.instance_id)
            if item is not None and (placement.definition_id != item.definition_id or not self._placeable_slot(item)):
                problems.append("盘上词块与行囊实例不符")
            if placement.rotation not in ROTATIONS:
                problems.append(f"{placement.definition_id} 旋转非法")
        return problems

    @root_action
    def commit_board(self, draft: EquipmentBoard, *, charge_time: bool = True,
                     quiet: bool = False):
        """验证整盘后原子提交；相同布局的确认是无变化操作，不扣时间、不发事件。"""
        from .actions import ActionResult

        unchanged = self.board.same_layout(draft)
        problems = self.draft_errors(draft)
        if problems:
            return ActionResult(False, tr("这副联想盘放不下：{reason}", reason=tr(problems[0])))
        # Preview final capacity without activating draft effects or hooks.
        previous = self.board
        draft = draft.clone()
        def over_capacity():
            ids = draft.placed_instance_ids()
            return sum(1 for item in self.inventory if item.instance_id not in ids
                       and item.quantity > 0) > self.inventory_capacity
        if over_capacity():
            return ActionResult(False, tr("行囊装不下卸回来的意象，整理没有发生。"))
        if charge_time and not unchanged:
            # The old board remains authoritative throughout the existing
            # action, including enemy attacks and delayed material simulation.
            self._action_time(1, self._use_action_kind())
            from ..equipment.root_facts import settle
            settle(self)  # Settle the old board before atomic installation.
            problems = self.draft_errors(draft)
            if self.run_over or problems or over_capacity():
                message = tr("整理行动已经结束，但盘面条件改变，新布局未启用。")
                if not quiet:
                    self.messages.append(message)
                return ActionResult(True, message, {"board_applied": False})
        self.board = draft
        self.equipment.invalidate()
        self._sync_equipment_hooks()
        if len(draft.placements) > len(previous.placements):
            self.tutorial_events["board_committed"] = 1
        if not unchanged and any(p.rotation != (previous.placement(p.instance_id).rotation
                        if previous.placement(p.instance_id) else 0) for p in draft.placements):
            self.tutorial_events['board_rotated'] = 1
        message = tr("联想盘已整理：占地 {used}/{total} 格。",
                     used=draft.area_used(), total=draft.width * draft.height)
        sentence = self.equipment.compiled().text
        data = {'used': draft.area_used(), 'board_applied': True}
        if not unchanged:
            data['equipment_sentence'] = sentence
        if unchanged:
            message = tr("盘面没有变化，不消耗行动。")
        if not quiet:
            self.messages.append(message)
            if not unchanged:
                self.messages.append(sentence)
        return ActionResult(True, message, data)

    def board_place_instance(self, instance_id: str, *, focus: bool = False,
                             charge_time: bool = True, quiet: bool = False):
        """把一个行囊实例放上盘面（自动安置：单件找合法位置，不移动旧件）。"""
        from .actions import ActionResult

        item = next(
            (it for it in self.inventory if it.instance_id == instance_id), None
        )
        if item is None:
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        if not self._placeable_slot(item):
            return ActionResult(False, tr("{item}不能作为携带意象。", item=tr(item.name)))
        if self.board.placement(instance_id) is not None:
            return ActionResult(False, tr("{item}已经在联想盘上了。", item=tr(item.name)))
        from ..equipment.placement import suggest_placement
        draft = suggest_placement(self.board, instance_id, item.definition_id)
        if draft is None:
            return ActionResult(False, tr("联想盘上放不下 {item}。",
                                          item=tr(item.name)))
        return self.commit_board(draft, charge_time=charge_time, quiet=quiet)

    def board_remove_instance(self, instance_id: str, *, charge_time: bool = True,
                              quiet: bool = False, new_focus: str | None = None):
        from .actions import ActionResult

        placement = self.board.placement(instance_id)
        if placement is None:
            item = next((it for it in self.inventory
                         if it.instance_id == instance_id), None)
            return ActionResult(False, tr("{item}并未穿戴在身上。",
                                          item=tr(item.name) if item else instance_id))
        draft = self.board_draft()
        was_focus = draft.focus_instance_id == instance_id
        draft.remove_item(instance_id)
        if was_focus:
            # §4.3：卸下焦点件时新焦点要由调用方在预览里点名，没点名就落到「空手」，
            # 绝不能提交后悄悄换成另一件武器。点名的件不在盘上、或不是可握持的 act
            # 词块，同样按空手处理——那是「没得选」，不是「替你选一件」。
            chosen = None
            target = draft.placement(new_focus) if new_focus else None
            if target is not None and resolve(target.definition_id, target.sense_id).kind == "act":
                chosen = target.instance_id
            draft.focus_instance_id = chosen
        return self.commit_board(draft, charge_time=charge_time, quiet=quiet)

    def _use_action_kind(self):
        from .actions import ActionKind

        return ActionKind.USE

    def _sync_equipment_hooks(self) -> None:
        """Refresh derived equipment views after a board change.

        Firing no longer carries a global license flag: a weapon is a source only
        while it is physically on the board, so there is nothing to toggle here.
        """
        if hasattr(self, "_refresh_hang"):
            self._refresh_hang()

    # ---- 单件装卸（沿用原列表的操作入口） ----

    @root_action
    def equip_item(self, index: int = 0):
        """从原装备列表装配：自动找合法位置，不移动旧件（§8.4 自动安置）。"""
        from .actions import ActionResult

        if "oblivion_strong" in self.portents:
            return ActionResult(False, tr("无念黑渊吞掉了记忆，你想不起怎么穿戴它。"))
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if not self._placeable_slot(item):
            return ActionResult(False, tr("{item}不能作为携带意象。", item=tr(item.name)))
        if self.board.placement(item.instance_id) is not None:
            return ActionResult(False, tr("{item}已经在联想盘上了。", item=tr(item.name)))
        return self.board_place_instance(item.instance_id, charge_time=True)

    @root_action
    def unequip_item(self, index: int = 0):
        """把盘上这件携带意象卸下来（它本身仍留在行囊里）。"""
        from .actions import ActionResult

        if "oblivion_strong" in self.portents:
            return ActionResult(False, tr("无念黑渊吞掉了记忆，你想不起怎么脱下它。"))
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        return self.board_remove_instance(item.instance_id, charge_time=True)

    def equipped_slot_of(self, index: int) -> str | None:
        if not (0 <= index < len(self.inventory)):
            return None
        instance_id = self.inventory[index].instance_id
        if self.board.placement(instance_id) is None:
            return None
        return self.equipment.slot_of(instance_id) or "携带意象"

    def switch_focus(self, instance_id: str | None):
        """Obsolete API retained for old callers; never establishes hidden state."""
        from .actions import ActionResult
        return ActionResult(False, tr("位置决定含义，不再切换握持或词义。"))

    def write_default_sentence(self, instance_id: str, written: bool = True):
        from .actions import ActionResult
        return ActionResult(False, tr("位置决定含义，不再切换握持或词义。"))

    def select_sense(self, instance_id: str, sense_id: str):
        from .actions import ActionResult
        return ActionResult(False, tr("位置决定含义，不再切换握持或词义。"))

    # ---- 根事件 ----

    def emit_board_event(self, endpoint: str, **kwargs) -> list:
        from ..equipment.positional_events import emit
        return emit(self, endpoint, **kwargs)

    @root_action
    def use_equipment_sentence(self, row_index: int, x: int, y: int, *, choice=None):
        from .actions import ActionResult
        if self.run_over:
            return ActionResult(False, tr("这一局已经结束。"))
        from ..equipment.positional_events import cast_imprint
        from ..equipment.runtime import condition_matches
        from ..equipment.active import clause_key
        from ..equipment.projection import sentence_text
        formation = self.equipment.formation()
        rows = [r for r in formation.actions if r.row == row_index and r.opcode in ('imprint','repair','measure')
                and (choice is None or choice == clause_key(formation, r))]
        row = rows[0] if len(rows) == 1 else None
        if (row is None or not self.inside_board(x, y)
                or not condition_matches(row.condition, self, target=self.entity_at(x, y), cell=(x, y))):
            return ActionResult(False, tr("没有合法的装备语句目标。"))
        from ..equipment.targets import target_matches
        if not target_matches(row, self, cell=(x,y), target=self.entity_at(x,y)):
            return ActionResult(False, tr('目标不符合定向语句。'))
        if row.opcode in ('repair','measure'):
            from ..equipment.tools import tool_source,tool_target_valid
            if not tool_target_valid(self,row,(x,y)):
                return ActionResult(False,tr('工具语句的目标或来源不满足条件。'))
            item = tool_source(self,row)
            index = next(i for i,entry in enumerate(self.inventory) if entry is item)
            result = self._use_consumable_item(item,index,tool_target=(x,y),tool_row=row)
            if result.changed:
                target = self.entity_at(x,y)
                self.emit_board_event('use_sentence',cell=(x,y),target=target,
                                      source_id=item.instance_id,recipient_id=target.id if target else '')
                result.data['equipment_sentence_row'] = row_index
                result.data['equipment_sentence'] = sentence_text(row)
            return result
        if not cast_imprint(self, row, self.entity_at(x, y)):
            return ActionResult(False, tr("装备语句的目标、消耗或冷却条件不满足。"))
        self.emit_board_event('use_sentence', cell=(x,y), target=self.entity_at(x,y),
                              source_id=self.player.id, recipient_id=self.entity_at(x,y).id)
        self._action_time(1, self._use_action_kind())
        message = tr("刀痕印在目标上：下一次合法命中兑现一次，保留 3 回合。")
        self.messages.append(message)
        return ActionResult(True, message, {"equipment_sentence_row": row_index,
                                           'equipment_sentence': sentence_text(row)})

    def _note_board_hit(self, target, action_plan=None, *, amount=None, damage_kind='') -> None:
        """命中端：玩家一次实际攻击或射击成功命中。"""
        if target is None or (amount is not None and amount <= 0):
            return
        self.emit_board_event(
            "hit", cell=(target.x, target.y), target=target,
            previous_cell=self.board_previous_cell, action_id=self.action_seq,
            action_plan=action_plan,
            source_id=self.player.id, recipient_id=target.id,
            amount=amount or 0, damage_kind=damage_kind,
        )

    def _note_board_hurt(self, kind: str, amount: int, *, source_id='') -> None:
        """受击端：玩家本次遭受结算后仍大于 0 的创伤；受击链默认玩家脚下。"""
        if amount <= 0:
            return
        self.emit_board_event(
            "hurt", cell=(self.player.x, self.player.y), damage_kind=kind,
            previous_cell=self.board_previous_cell, action_id=self.time,
            amount=amount, source_id=source_id, recipient_id=self.player.id,
        )

    def _note_board_touch(self, previous: tuple[int, int] | None) -> None:
        """接触端：进入新的有效材料接触。站着不动的每回合不重复发事件。"""
        cell = (self.player.x, self.player.y)
        if previous == cell:
            return
        material = ""
        if self.inside_board(*cell):
            current = self.cell(*cell)
            material = current.liquid_kind or current.gas_kind or ""
        if not material:
            # 离开有效材料就清掉记录：再走回同一格水是一次**新的**接触。
            self.board_touch_material = ""
            self.board_touch_cell = None
            return
        if self.board_touch_material == material and self.board_touch_cell == cell:
            return
        self.board_touch_material = material
        self.board_touch_cell = cell
        self.emit_board_event("touch", cell=cell, material=material,
                              previous_cell=previous, action_id=self.time)

    def _note_board_conceive(self, ability_id: str) -> None:
        """构想端：玩家成功展开一次主动构想；失败、预览、按键重复不触发。"""
        self.emit_board_event(
            "conceive", cell=(self.player.x, self.player.y), material=ability_id,
            previous_cell=self.board_previous_cell, action_id=self.time,
        )

    def board_round_tick(self) -> None:
        board_events.start_round(self)

    def board_prune_on_descend(self) -> None:
        # 换局的线路清零不需要钩子：每局都是新建 GameState，字段默认值即空。
        board_events.prune_on_descend(self)

    # ---- 旧存档无损迁移 ----

    def migrate_slots_to_board(self, equipped: dict[str, str]) -> tuple[bool, str]:
        """按实例 id 读取旧五栏，自动寻位（枚举旋转并回溯，不贪心）。

        失败时不写新格式、不静默卸下、不丢弃、不挤满行囊：返回原因，
        调用方保留备份与原五栏兼容状态。
        """
        entries: list[tuple[str, str]] = []
        focus_id: str | None = None
        for slot, instance_id in (equipped or {}).items():
            item = next(
                (it for it in self.inventory if it.instance_id == instance_id), None
            )
            if item is None or not self._placeable_slot(item):
                continue
            entries.append((instance_id, item.definition_id))
            if slot == "手中意象":
                focus_id = instance_id
        if not entries:
            self.board = EquipmentBoard()
            return True, ""
        draft = EquipmentBoard()
        if not draft.pack(entries):
            return False, tr("旧五栏的这副组合在 8×6 盘面上放不下，迁移已中止（原存档保留）。")
        for placement in draft.placements:
            placement.sense_id = default_sense(placement.definition_id).sense_id
            placement.sentence_written = True
        if focus_id is None:
            focus_id = next(
                (p.instance_id for p in draft.placements
                 if resolve(p.definition_id, p.sense_id).kind == "act"), None
            )
        draft.focus_instance_id = focus_id if draft.placement(focus_id) else None
        self.board = draft
        self.equipment.invalidate()
        self._sync_equipment_hooks()
        return True, ""
