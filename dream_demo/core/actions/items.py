"""物品动作族：拾取/台面取放/行囊使用/装备切换/投掷/放下。"""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Any, Iterable

from ...i18n import tr
from ...materials import DOOR_KINDS, GAS_DEFINITIONS, SURFACE_KINDS, TABLE_KINDS, floor_effect_for, portent_def, wall_def
from ..content import ABILITY_DEFINITIONS, ACCESSORY_SLOTS, EQUIPMENT_POOL, EVENT_INSIGHT_CHANCE
from ...data.ids import event_option_id, stable_seed
from ..ballistics import angle_blocked, bounce_direction, trace_path
from .. import throwing
from .. import item_targeting
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
from ..item_access import insight_learnable, record_pickup, run_limit_refusal

# 普通眩光道具的基础时长：写入 enemy.blind_turns，之后每拍衰减（视野受限＝
# 视距减半，不是致盲）。强闪光／正面命中才挂统一的 `blinded` 征兆（docs §14.1）。
BLIND_TURNS = 5

class ItemActionsMixin:
    """物品动作族：拾取/台面取放/行囊使用/装备切换/投掷/放下。"""

    def grant_projectile(self, amount: int = 1) -> ActionResult:
        """Add one-shot aggregate projectiles, for future pickups and events."""
        if amount <= 0:
            return ActionResult(False, tr("聚合弹数量必须为正数。"))
        self.projectile_charges += amount
        message = tr("获得 {amount} 枚聚合弹。", amount=amount)
        self.messages.append(message)
        return ActionResult(True, message, {"projectile_charges": self.projectile_charges})

    @root_action
    def collect_here(self, advance_time: bool = True, *, include_equipment: bool = True) -> ActionResult:
        position = (self.player.x, self.player.y)
        # 站在台子所在的格（门被推开后玩家可以站上去）时，脚下这一格就是台面。
        if self.cell(*position).wall_kind in TABLE_KINDS:
            if not include_equipment:
                return ActionResult(False)
            return self.take_from(*position)
        found = [entry for entry in self.world_items if (entry.x, entry.y) == position
                 and (include_equipment or entry.item.category != "携带意象")]
        if not found:
            # 自动拾取（每一步都调）不该刷屏，只有手动拾取才提示。
            if advance_time:
                self.messages.append(tr("脚下没有可拾取的显化物。"))
            return ActionResult(False, tr("脚下没有可拾取的显化物。"))
        entry = found[0]
        limit_refusal = run_limit_refusal(self, entry.item.definition_id, count=entry.item.quantity)
        if limit_refusal:
            self.messages.append(limit_refusal)
            return ActionResult(False, limit_refusal)
        self.world_items.remove(entry)
        item = entry.item
        if item.category == "记忆碎片":
            self._add_memory(item.definition_id)
            if self.pending_memory:
                # 槽位已满：碎片挂在 pending 上，界面会自动弹出替换面板。
                self.messages.append(
                    tr("记忆碎片已满：{item} 无处安放，需要替换或放弃。", item=tr(item.name))
                )
            else:
                self.messages.append(tr("记忆碎片已收纳：{item}。", item=tr(item.name)))
        else:
            try:
                self._add_inventory_item(item)
            except ValueError:
                self.world_items.append(entry)
                # 失败也要留痕：只返回 ActionResult 的话界面上完全没反馈，
                # 玩家会以为「点了没反应」而反复点击。
                message = tr("背包已满，无法拾取这个显化物。")
                self.messages.append(message)
                return ActionResult(False, message)
            record_pickup(self, item.definition_id, count=item.quantity)
            if item.category == "携带意象":
                self.messages.append(tr("拾取携带意象：{item}。", item=tr(item.name)))
            else:
                self.messages.append(tr("拾取显化物：{item}。", item=tr(item.name)))
        self._claim_toy_reward(entry)
        self._record_catalog_interaction(f"item.{item.definition_id}", tr(item.name), "manifestation", "你把它拾进了行囊。")
        if advance_time and "swift_pickup" not in self.equipped_effect_ids() and not self.insight_active("疾行拾荒"):
            self._action_time(1, ActionKind.USE)  # 缺指的手套/疾行拾荒：拾取不耗时
        return ActionResult(True, self.messages[-1], {"item": item.definition_id})

    @root_action
    def take_from(self, x: int, y: int, item_id: str | None = None) -> ActionResult:
        """从相邻的台子（木桌子/石台）台面上取走物品：消耗一个行动。"""
        if max(abs(x - self.player.x), abs(y - self.player.y)) != 1:
            return ActionResult(False, tr("只能从相邻的台子上取物。"))
        if not (0 <= x < self.width and 0 <= y < self.height):
            return ActionResult(False, tr("这里没有台子。"))
        cell = self.cell(x, y)
        # 承载面含可步行的白瓷工作台／胡桃木书架（见 materials.SURFACE_KINDS）。
        if cell.wall_kind not in SURFACE_KINDS:
            return ActionResult(False, tr("这里没有台子。"))
        found = [entry for entry in self.world_items if (entry.x, entry.y) == (x, y)]
        if not found:
            return ActionResult(False, tr("台面上没有东西。"))
        if not self.is_visible(x,y):
            return ActionResult(False, tr("眼前的情形已经改变，请重新选择。"))
        if item_id is not None:
            found=[entry for entry in found if entry.item.instance_id==item_id]
            if not found:
                return ActionResult(False, tr("眼前的情形已经改变，请重新选择。"))
        elif len(found)>1:
            return ActionResult(False, '', {'pickup_target':[x,y]})
        entry = found[0]
        limit_refusal = run_limit_refusal(self, entry.item.definition_id, count=entry.item.quantity)
        if limit_refusal:
            self.messages.append(limit_refusal)
            return ActionResult(False, limit_refusal)
        # 有主的承载面（医院白瓷工作台／图书馆胡桃木书架）：先把代价付清再拿走。
        # 先付的理由：`_add_inventory_item` 可能把可堆叠件并进已有的那叠里，
        # 「先入袋再收费、付不起再退回」在堆叠情形下退不干净。
        from ..surface_terms import pay_for_take, refund_take_payment

        refusal = pay_for_take(self, cell.wall_kind)
        if refusal:
            self.messages.append(refusal)
            return ActionResult(False, refusal)
        self.world_items.remove(entry)
        item = entry.item
        try:
            self._add_inventory_item(item)
        except ValueError:
            self.world_items.append(entry)
            refund_take_payment(self, cell.wall_kind)
            message = tr("背包已满，无法拾取这个显化物。")
            self.messages.append(message)
            return ActionResult(False, message)
        record_pickup(self, item.definition_id, count=item.quantity)
        if item.category == "携带意象":
            self.messages.append(tr("从台面上取走携带意象：{item}。", item=tr(item.name)))
        else:
            self.messages.append(tr("从台面上取走：{item}。", item=tr(item.name)))
        self._record_catalog_interaction(f"item.{item.definition_id}", tr(item.name), "manifestation", "你把它拾进了行囊。")
        if "swift_pickup" not in self.equipped_effect_ids() and not self.insight_active("疾行拾荒"):
            self._action_time(1, ActionKind.USE)
        # 逻辑固体（内容扩展包 v1）：陷阱/机关石台的台面被动过——触发其逻辑。
        # 桌面不是地面（expansion.terrain.i02）：从**陷阱**石台上取物时多站一回合，
        # 这一回合把机关隔开（陷阱不响），石台照旧发信号、机关石台照旧触发。
        slow = (cell.wall_kind == "陷阱石台"
                and self.insight_active("桌面不是地面"))
        if cell.wall_kind in ("陷阱石台", "机关石台"):
            self.trigger_platform(
                x, y,
                safe_note=(tr("桌面不是地面：你多站了一回合，慢慢把东西取下来——"
                              "陷阱没踩响，石台照旧发了信号。") if slow else ""))
        if slow:
            self._action_time(1, ActionKind.USE)
        return ActionResult(True, self.messages[-1], {"item": item.definition_id,
                            "surface": cell.wall_kind, "position": [x,y]})

    @root_action
    def pickup(self) -> ActionResult:
        """G 键拾取：优先脚下，其次相邻台面（木桌子/石台）上的显化物。

        优先级由玩家的操作直觉决定——脚下能捡就先捡脚下的，脚下没有才伸手
        到旁边的台面上。**相邻地面上散落的显化物不在此列**：那需要走过去
        （``collect_here`` 本就是「脚下」口径），g 不做「隔空吸物」。
        """
        state_item = next(
            (entry for entry in self.world_items if (entry.x, entry.y) == (self.player.x, self.player.y)),
            None,
        )
        if state_item is not None or self.cell(self.player.x, self.player.y).wall_kind in TABLE_KINDS:
            return self.collect_here(advance_time=True)
        surface = self.adjacent_table_with_item()
        if surface is None:
            # 相邻有台子但台面空着：给「台面空」而不是「脚下没有」，提示更准确。
            if self.adjacent_table() is not None:
                return ActionResult(False, tr("台面上没有东西。"))
            return self.collect_here(advance_time=True)
        return self.take_from(*surface)

    def pickup_candidates(self, x: int | None = None, y: int | None = None) -> list[WorldItem]:
        """某一格上所有可拾取的显化物（按 world_items 里的自然顺序 = 从上往下）。

        拾取面板与「直接捡」共用这个清单，保证两者看到的顺序一致。
        默认取脚下这一格。
        """
        if x is None or y is None:
            x, y = self.player.x, self.player.y
        return [entry for entry in self.world_items if (entry.x, entry.y) == (x, y)]

    def can_collect_at(self, x: int, y: int) -> bool:
        if not self.inside_board(x,y) or not self.is_visible(x,y):
            return False
        distance=max(abs(x-self.player.x),abs(y-self.player.y))
        return distance==0 or (distance==1 and self.cell(x,y).wall_kind in SURFACE_KINDS)

    @root_action
    def collect_items(self, entries: list[WorldItem], advance_time: bool = True) -> ActionResult:
        """批量拾取指定的显化物（拾取面板的 Enter 结算）。

        ⚠️ 顺序语义（玩家明确要求）：**从上往下依次放入**，装不下的留在原地。
        因此这里逐件尝试、遇满即止——不跳过失败项去尝试后面的（否则玩家会
        看到「明明选了 3 件只拿到第 3 件」）。已成功的部分照常入袋，剩下的
        留在 world_items 里等下一次拾取。

        时间只结算一次（无论拿了几件）：拾取是「一次行动」。
        """
        if not entries:
            return ActionResult(False, tr("没有选中任何显化物。"))
        if self.pending_memory:
            return ActionResult(False, tr("先决定待收纳记忆碎片的去留。"))
        # A stale selection must not turn into remote pickup or target another
        # object after a table disappears. Validate the whole request first.
        entries=list({id(entry):entry for entry in entries}.values())
        tables={}
        for entry in entries:
            if not any(entry is current for current in self.world_items):
                return ActionResult(False,tr("眼前的情形已经改变，请重新选择。"))
            position=(entry.x,entry.y)
            if not self.can_collect_at(*position):
                return ActionResult(False,tr("眼前的情形已经改变，请重新选择。"))
            kind=self.cell(*position).wall_kind
            if kind in TABLE_KINDS:
                tables[position]=kind
        taken: list[str] = []
        changed_tables=set()
        full = False
        pending_full = False
        for entry in entries:
            if entry not in self.world_items:
                continue  # 已被其他途径拿走，跳过
            item = entry.item
            if item.category == "记忆碎片":
                self.world_items.remove(entry)
                self._add_memory(item.definition_id)
                taken.append(tr(item.name))
                if (entry.x,entry.y) in tables: changed_tables.add((entry.x,entry.y))
                if self.pending_memory:
                    # Preserve the remaining selected items until the player resolves
                    # this fragment; another fragment must not overwrite it.
                    pending_full = True
                    break
                continue
            try:
                self._add_inventory_item(item)
            except ValueError:
                # 装不下：停止（不跳过），余下的留在原地。
                full = True
                break
            self.world_items.remove(entry)
            if (entry.x,entry.y) in tables: changed_tables.add((entry.x,entry.y))
            self._claim_toy_reward(entry)
            self._record_catalog_interaction(
                f"item.{item.definition_id}", tr(item.name), "manifestation", "你把它拾进了行囊。"
            )
            taken.append(tr(item.name))
        if not taken:
            message = tr("背包已满，无法拾取这个显化物。")
            self.messages.append(message)
            return ActionResult(False, message)
        if pending_full:
            message = tr("拾取 {items}；先决定新记忆的去留。", items="、".join(taken))
        elif full:
            message = tr("拾取 {items}；背包已满，其余留在原地。", items="、".join(taken))
        else:
            message = tr("拾取：{items}。", items="、".join(taken))
        self.messages.append(message)
        if advance_time and "swift_pickup" not in self.equipped_effect_ids() and not self.insight_active("疾行拾荒"):
            self._action_time(1, ActionKind.USE)
        for position in sorted(changed_tables):
            if tables[position] in ("陷阱石台", "机关石台"):
                self.trigger_platform(*position)
        return ActionResult(True, message, {"items": taken, "incomplete": full or (pending_full and len(taken) < len(entries)),
                            "table_positions":[list(pos) for pos in sorted(changed_tables)]})

    def adjacent_table(self) -> tuple[int, int] | None:
        """相邻（8 邻域）的台子（木桌子/石台）；没有则 None。"""
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x, y = self.player.x + dx, self.player.y + dy
                if not (0 <= x < self.width and 0 <= y < self.height):
                    continue
                if self.cell(x, y).wall_kind in TABLE_KINDS:
                    return x, y
        return None

    def adjacent_table_with_item(self) -> tuple[int, int] | None:
        """相邻台子里，台面上真的有显化物的最近一个；没有则 None。"""
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x, y = self.player.x + dx, self.player.y + dy
                if not (0 <= x < self.width and 0 <= y < self.height):
                    continue
                if self.cell(x, y).wall_kind not in TABLE_KINDS:
                    continue
                if any((entry.x, entry.y) == (x, y) for entry in self.world_items):
                    return x, y
        return None

    def normalize_world_item_surfaces(self) -> None:
        """§14.6：把每件显化物的支撑身份对齐当前地形（台体没了就落回地面）。"""
        for entry in self.world_items:
            cell = (self.cell(entry.x, entry.y)
                    if self.inside_board(entry.x, entry.y) else None)
            entry.sync_surface(cell)

    def table_place_target(self) -> tuple[int, int] | None:
        """放物的默认台面：悬停的相邻台面 > 面朝的台面 > 最近的相邻台面。"""
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x, y = self.player.x + dx, self.player.y + dy
                if not self.inside_board(x, y):
                    continue
                if self.cell(x, y).wall_kind in TABLE_KINDS:
                    candidates.append((x, y))
        usable = [pos for pos in candidates if not self._table_placement_protected(*pos)]
        if not usable:
            return candidates[0] if candidates else None
        hover = getattr(self, "hover_target", None)
        if hover is not None and tuple(hover) in usable:
            return tuple(hover)
        facing = (self.player.x + self.facing[0], self.player.y + self.facing[1])
        if facing in usable:
            return facing
        return usable[0]

    def _table_placement_protected(self, x: int, y: int) -> bool:
        # Destruction protection also includes ordinary stone platforms. Placing
        # an item does not destroy them; retain the actual task/circuit guards.
        from ..tamper_protection import _facility_cells
        return (bool(self.cell(x,y).wire) or bool(self.circuit_node_at(x,y))
                or self.puzzle_projectile_blocked(x,y) or (x,y) in _facility_cells(self)
                or any((event.x,event.y)==(x,y) for event in self.events))

    def _table_place_reason(self, x: int, y: int) -> str:
        if max(abs(x - self.player.x), abs(y - self.player.y)) != 1:
            return tr("只能放到相邻的台面上。")
        if not self.inside_board(x, y):
            return tr("这里没有台子。")
        if self.cell(x, y).wall_kind not in TABLE_KINDS:
            return tr("这里没有台子。")
        if not self.is_visible(x,y):
            return tr("看不见那里，落点无从确认。")
        if self._table_placement_protected(x, y):
            return tr("这块台面被机关或任务占用，不能往上放东西。")
        return ""

    @root_action
    def put_on_table(self, index: int = 0, x: int | None = None,
                     y: int | None = None) -> ActionResult:
        """§14.6 放置到台面：把一件物品安置在相邻台面上，不执行撞击载荷。"""
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.instance_id in self.equipped.values():
            return ActionResult(False, tr("携带意象仍在使用中，不能放到台面上。"))
        if (x is None) != (y is None):
            return ActionResult(False, tr("这里没有台子。"))
        if x is None and y is None:
            target = self.table_place_target()
            if target is None:
                return ActionResult(False, tr("旁边没有可以放东西的台面。"))
            x, y = target
        reason = self._table_place_reason(x, y)
        if reason:
            return ActionResult(False, reason)
        placed = self._detach_one_for_action(index)
        if placed is None:
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        surface = self.cell(x, y).wall_kind
        self.world_items.append(WorldItem(placed, x, y, surface=surface))
        self._action_time(1, ActionKind.USE)
        message = tr("把 {item} 放在了台面上。", item=tr(placed.name))
        self.messages.append(message)
        # 内容确实变了：陷阱／机关台面按原有逻辑触发一次。
        if surface in ("陷阱石台", "机关石台"):
            self.trigger_platform(x, y)
        return ActionResult(True, message,
                            {"item": placed.definition_id, "position": [x, y],
                             "surface": surface, "landed_item_id": placed.instance_id})

    def toggle_equip_item(self, index: int = 0) -> ActionResult:
        """Enter / 左键的统一入口：未穿戴则穿上，已穿戴则脱下。

        无携带意象槽的物品（摄入物/易逝物/交互道具/惯用物）在此直接「使用」，
        行为与 _activate_panel_selection 一致，单条入口覆盖全部情况。
        """
        if self.equipped_slot_of(index) is not None:
            return self.unequip_item(index)
        item = self.inventory[index] if 0 <= index < len(self.inventory) else None
        if item is not None and item.category in ("摄入物", "易逝物", "交互道具", "惯用物", "记忆碎片"):
            return self.use_item(index)
        return self.equip_item(index)

    def _refresh_hang(self) -> None:
        """弯曲的挂钩：携带时自动把第一件易逝物挂到梦的墙上作为替身。

        改为能力查询：不再只在两个依附物栏里找（旧栏位不是新位置权威）。
        多挂钩只形成候选池；一次受击最多消耗一件真实挂载物。
        """
        self.hang_item_id = None
        hook = self.equipment.find_effect("hang")
        if not hook:
            return
        hanger = next((item for item in self.inventory if item.category == "易逝物"), None)
        if hanger:
            self.hang_item_id = hanger.instance_id
            self.messages.append(tr("{hanger}被挂上了梦的墙壁。", hanger=tr(hanger.name)))

    @staticmethod
    def _washable_negative_portents(holder) -> set[str]:
        """可清洗的**负面**征兆 id 集合（正面与不可清洗的一律不算）。"""
        allowed: set[str] = set()
        for pid in holder.portents:
            definition = portent_def(pid)
            if definition is not None and definition.washable and definition.kind == "负面":
                allowed.add(pid)
        return allowed

    def _emit_item_use_noise(self, item: Item, radius: int | None = None) -> None:
        """使用物品的世界噪音：摄入物轻，装置/工具重；声音来源是玩家格。

        本身已经有专属声场的物品（汽笛/诱饵/铃声）不叠加通用噪音，避免覆盖
        它们真实的声径与 full_alert 口径。
        """
        if item.effect in ("blast_lure", "sound_lure", "slow_ring"):
            return
        base = radius if radius is not None else min(10, 2 + max(0, int(item.power or 0)))
        from ..expansion_consumables import tool_noise
        base = tool_noise(self, item, base)
        self._sound_pulse(self.player.x, self.player.y, max(1, int(base)), by_player=True, category="item",
                          source=tr(item.name),
                          announce=False, triggers_rewards=False)

    @animate_consumable
    def _use_consumable_item(self, item: Item, index: int, *, tool_target=None, tool_row=None) -> ActionResult:
        """摄入物 / 易逝物 / 交互道具 / 部分惯用物的直接使用结算。"""
        # Validate before spending the item, action, or usage statistics.
        timed_only = {
            "parry": "mirror_stance",
            "lucidity_regen": "invigorated",
            "hospital_fluent": "hospital_fluent",
            "hospital_gel_buffer": "hospital_gel_buffer",
            "hospital_pain_buffer": "hospital_pain_buffer",
            "hospital_lymph_hit": "hospital_lymph_hit",
            "hospital_immune_once": "hospital_immune_once",
            "hospital_oxygen": "hospital_oxygen",
            "hospital_sensitive": "hospital_sensitive",
        }.get(item.effect)
        if timed_only and self._portent_protected(self.player, timed_only):
            # §17：唯一效果是施加该征兆的道具在保护窗口内属于无效操作，
            # 不消耗物品、行动或统计，也不解释隐藏的保护规则。
            return ActionResult(False, tr("此刻用不上它。"))
        medical_family = None
        if item.effect == 'hospital_safe_sleep' and not self.hospital_safe_rest():
            return ActionResult(False, tr('这里有可见敌对目标或环境危险，未消耗甘眠露。'))
        if item.effect == 'hospital_wake':
            from ..hospital_effects import SLEEP_FAMILY
            medical_family = SLEEP_FAMILY
        elif item.effect == 'hospital_fever':
            medical_family = frozenset(('burning', 'scalded'))
        if medical_family is not None and not self.cleanse_target(self.player, medical_family):
            return ActionResult(False, tr('没有可处理的对应征兆，未消耗药物。'))
        if (item.effect == 'hospital_gel_buffer'
                and (self.player.portents.get(item.effect, 0) > 0
                     or self.time < self.player.hospital_state.get('gel_ready', 0))):
            return ActionResult(False, tr('缓释仍在生效或尚未达到8回合间隔，未消耗药物。'))
        if item.definition_id == 'modem_56k':
            from ..timed_actions import modem_phase
            if modem_phase(self)[0]:
                return ActionResult(False, tr('56k 猫仍在缓冲，暂时不能再次启动。'))
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        tool_data = {}
        if item.effect in ('hospital_fluent', 'hospital_gel_buffer', 'hospital_pain_buffer',
                           'hospital_lymph_hit', 'hospital_immune_once', 'hospital_oxygen', 'hospital_sensitive'):
            self._grant_portent_direct(self.player, item.effect)
            if item.effect == 'hospital_gel_buffer':
                self.player.hospital_state['gel_ready'] = self.time + 8
        elif item.effect == 'hospital_safe_sleep':
            self.restore_resource('mind', 10, ingested=item.category == '摄入物')
            self.restore_resource('imagination', 6, ingested=item.category == '摄入物')
        elif medical_family is not None:
            pid = self.shorten_portent(self.player, 4, medical_family)
            tool_data['shortened_portent'] = pid
        elif item.effect == 'hospital_saline':
            self.restore_resource('mind', item.power, ingested=item.category == '摄入物')
            self.restore_resource('lucidity', item.power_secondary, ingested=item.category == '摄入物')
        elif item.effect == "restore_imagination":
            self.restore_resource('imagination', item.power, ingested=item.category == '摄入物')
        elif item.effect == "projectile_charge":
            self.projectile_charges += item.power
        elif item.effect == "restore_mind":
            self.restore_resource('mind', item.power, ingested=item.category == '摄入物')
        elif item.effect == "restore_lucidity":
            self.restore_resource('lucidity', item.power, ingested=item.category == '摄入物')
        elif item.effect == "restore_split":
            self.restore_resource('lucidity', item.power, ingested=item.category == '摄入物')
            self.restore_resource('imagination', item.power_secondary or 5, ingested=item.category == '摄入物')
        elif item.effect == "gamble":
            if random.Random(self.seed + self.time * 7919 + self.next_item_id).random() < 0.5:
                self.restore_resource('mind', 15, ingested=item.category == '摄入物')
                self.messages.append(tr("糖衣之下是救济：心智恢复了 15 点。"))
            else:
                self._lose_mind(8)
                from ..settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(self, 'lucidity', -3, reason=REASON_ENVIRONMENT,
                             source='过期药剂')
                self.messages.append(tr("过期的是药效本身：心智 −8，清醒度 −3。"))
        elif item.definition_id == "unfinished_fullstop":
            # Existing copies retain identity/quantity but adopt the new use rule.
            self.restore_resource('imagination', 35, ingested=item.category == '摄入物')
            self.restore_resource('lucidity', 12, ingested=item.category == '摄入物')
            from ..drug_debts import add_dose
            add_dose(self, item, resource='mind', total=8, duration=10)
        elif item.definition_id == "modem_56k":
            # ID compatibility also handles held legacy instances tagged overclock.
            from ..timed_actions import start_modem
            if not start_modem(self):
                return ActionResult(False, tr('56k 猫仍在缓冲，暂时不能再次启动。'))
        elif item.effect == "overclock":
            self.restore_resource('imagination', item.power, ingested=item.category == '摄入物')
            from ..drug_debts import add_overclock_dose
            add_overclock_dose(self, item)
        elif item.effect == "lucidity_regen":
            # 特浓薄荷茶：不直接恢复，授予长时「振奋」征兆（每 2 回合 +1 清醒）。
            if self._apply_direct_portent(
                    self.player, "invigorated", min(item.power or 28, PORTENT_DURATION_CAP)):
                self.messages.append(tr("薄荷的凉意渗进神志：接下来持续恢复清醒度。"))
        elif item.effect == "purge_void":
            # 虚空阻凝剂：清除无意识领域的控制类负面征兆。
            cleared = [pid for pid in ("nightmare", "nightmare_fiber", "nightmare_breath",
                                        "voidness", "oblivion_strong", "forgotten") if pid in self.portents]
            for pid in cleared:
                self._remember_portent_end(self.player, pid)
            if cleared:
                self.messages.append(tr("虚空被凝固回原处：噩梦、虚无与遗忘都散了。"))
            else:
                self.messages.append(tr("你身上没有需要凝固的东西。"))
        elif item.effect == "develop_radius":
            # 无光灯笼：以自身为中心半径 power 的地形永久显影。
            developed = self._develop_terrain_radius(self.player.x, self.player.y, item.power or 4)
            self.messages.append(tr("无光处亮起一片：{count} 格地形被永久显影。", count=developed))
        elif item.effect == "waking_reserve":
            # 留给醒来的那一口（2026-10-22 A2 P5）：清醒 30／心智 20，外加
            # 洗掉一项可清洗的**负面**附着，并让一项可清洗负面征兆缩短至多 4 回合。
            # 正面征兆、混乱、旧债与冷却一概不动。
            self.restore_resource('lucidity', item.power or 30, ingested=item.category == '摄入物')
            self.restore_resource('mind', item.power_secondary or 20, ingested=item.category == '摄入物')
            negative = self._washable_negative_portents(self.player)
            shortened = self.shorten_portent(self.player, 4, negative)
            detached = None
            for pid in list(self.player.portent_attach):
                if pid in negative and self.player.portent_attach[pid] > 0:
                    self.player.portent_attach.pop(pid, None)
                    detached = pid
                    break
            if shortened or detached:
                self.messages.append(tr("那口气把你身上黏着的东西冲淡了。"))
            else:
                self.messages.append(tr("你身上没有可洗的东西——这一口只是暖了暖。"))
        elif item.effect == "deploy_quiet_boundary":
            # 最后一圈安静（2026-10-22 A2 P5）：自身半径 4 的临时声衰减区，
            # 只挡声音，不清警戒、不挡非声音感知。
            from .. import item_devices
            ok, message, data = item_devices.deploy_quiet_boundary(self)
            if not ok:
                return ActionResult(False, message)
        elif item.effect == "warm_restore":
            self.restore_resource('mind', item.power, ingested=item.category == '摄入物')
            self.viscous_debt = 0.0
            self.messages.append(tr("迟滞与麻痹被冲开了。"))
        elif item.effect == "ignite_burst":
            strength = (item.power or 2) + self._effect_power("fire_affinity")
            px, py = self.player.x, self.player.y
            ignited = 0
            for tx, ty in ((px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                if self._ignite_cell(tx, ty, strength, by_player=True):
                    ignited += 1
            self.messages.append(tr("火星在身边迸开（点燃 {n} 格）。", n=ignited))
        elif item.effect == "ignite":
            if not self._ignite_cell(self.player.x, self.player.y, 3, by_player=True):
                return ActionResult(False, tr("这里没有足够的液态记忆或弥散印象可供点燃。"))
            self.messages.append(tr("火焰在脚下的记忆上亮起。"))
        elif item.effect == "shock":
            origin = (self.player.x, self.player.y)
            zone = self._conductive_zone(origin)
            if not zone:
                return ActionResult(False, tr("脚下的液态记忆不导电。"))
            shock_power = item.power
            static_cell = self.cell(self.player.x, self.player.y)
            if static_cell.gas_kind == "静电尘" and static_cell.gas >= 20:
                shock_power += 1
                self.messages.append(tr("静电尘里的电压叠加进了导电液态记忆。"))
            shocked = 0
            struck: list = []
            for enemy in self.enemies:
                if enemy.integrity <= 0:
                    continue
                if (enemy.x, enemy.y) in zone and enemy.relation != "稳定意识":
                    self._kill_full_reward = True  # 玩家电击道具：崩解全额
                    enemy.integrity = max(0, enemy.integrity - shock_power)
                    # 异象先衰减征兆再行动；补上道具自身结算的这一拍，
                    # 才能真正减慢一次响应，结算后的面板仍只剩一回合。
                    self._apply_direct_portent(enemy, "shocked", 2)
                    struck.append(enemy)
                    shocked += 1
                    if enemy.integrity <= 0:
                        self._resolve_enemy(enemy)
            self.messages.append(tr("导电液态记忆传递了清醒创伤，影响 {count} 个失控意识。", count=shocked))
            # 潮润传导（浸盐的线圈）：湿润目标之间多传一次，冷却与范围见
            # enemies._wet_conduct_chain。
            self._wet_conduct_chain(struck)
            self._charge_electric_field(zone, source='battery', origin=origin)
            self._emit_combat_fx("electric", origin, zone)
        elif item.effect == "free_step":
            self.free_move_pending += 1
        elif item.effect == "liquid_step":
            self.free_liquid_moves += item.power or 3
        elif item.effect == "skip_turn":
            self.dissolution = max(0, self.dissolution - (item.power or 2))
            self.messages.append(tr("你踩上空心的台阶，落空的这一次行动让崩解松了扣。"))
        elif item.effect == "free_action":
            # 2026-10-22（P3）：至多存 1 次，且限 5 回合内用掉（窗口在付完时间后盖章）。
            # 注意：这里**不能**立刻写 free_actions——否则本次使用自己就会吃掉这张
            # 底片（尾部 `_action_time` 先看到充能），物品等于什么都没做。
            definition = ITEM_DEFINITIONS.get(item.definition_id, {})
            turns = max(1, int(definition.get("free_action_turns", 5) or 5))
            self._free_action_pending = turns
            self.messages.append(
                tr("底片上的两次成像叠在一起（{turns} 回合内下一个动作不耗时）。", turns=turns))
        elif item.effect == "remote_switch":
            # 2026-10-22（P3 战术分工）：键帽不再只是一发聚合弹（与弹匣同效），
            # 改成「三格内远程按一次机关」——看得见的接收器（机关门／显影方尖／
            # 囚笼栅栏／弹射座／灌注阀／共鸣报警器）都能隔空按响。
            from ...materials.logic import RECEIVER_KINDS
            reach = max(1, int(item.power or 3))
            px, py = self.player.x, self.player.y
            candidates: list[tuple[int, int, int, str]] = []
            for ty in range(py - reach, py + reach + 1):
                for tx in range(px - reach, px + reach + 1):
                    distance = abs(tx - px) + abs(ty - py)
                    if distance == 0 or distance > reach:
                        continue
                    if not (0 <= tx < self.width and 0 <= ty < self.height):
                        continue
                    kind = self.cell(tx, ty).wall_kind
                    if kind not in RECEIVER_KINDS:
                        continue
                    if not self.is_visible(tx, ty):
                        continue
                    candidates.append((distance, tx, ty, kind))
            if not candidates:
                # 零消耗拒绝：这一下没按到东西，不该白吃一枚键帽。
                return ActionResult(False, tr("三格内没有看得见、按得响的机关。"))
            dx, dy = self.facing or (1, 0)
            candidates.sort(key=lambda row: (row[0], 0 if (row[1], row[2]) == (px + dx, py + dy) else 1,
                                             row[2], row[1]))
            _distance, tx, ty, kind = candidates[0]
            self.emit_signal(tx, ty, source="player")
            self.messages.append(tr("键帽在指下响了一声——{name}应声而动。", name=tr(kind)))
        elif item.effect == "repair":
            from ...equipment.runtime import action_effect_power
            repair_power = action_effect_power(self, 'repair_up', (tool_row,) if tool_row else ())
            repaired = (self._repair_wall_at(*tool_target,item.power or 30,repair_power=repair_power) if tool_target is not None
                        else self._repair_adjacent_wall(item.power or 30))
            if not repaired:
                return ActionResult(False, tr("相邻没有受损的坚实聚合物。"))
        elif item.effect == "measure":
            measure_target = tool_target if tool_target is not None else self.hover_target
            if not measure_target:
                return ActionResult(False, tr("先把光标悬停在一个格子上，卷尺才有可测量的距离。"))
            path = self.path_to(*measure_target)
            steps = len(path)
            tool_data['steps'] = steps
            self.messages.append(tr("卷尺读数：到悬停格最短 {steps} 步。", steps=steps))
        elif item.effect == "blast_lure":
            # 强诱引（docs §16.4）：汽笛全员径直前来（内圈待遇），不被
            # 听觉距离梯度削弱；freeze_near=1 的震停仍只作用于内圈。
            self._sound_pulse(self.player.x, self.player.y, item.power or 8,
                              freeze_near=1, by_player=True, full_alert=True,
                              category="lure", source=tr(item.name))
            self.messages.append(tr("汽笛的长鸣在梦里扩散开来。"))
        elif item.effect == "blind":
            # 闪光不是隐身：被晃到的意识只是视距减半（enemies._effective_vision），
            # 而且必须真的看得见这束光——隔墙的目标不被闪。信号焰火不限量程，
            # 范围就是「此刻玩家看得见的敌对目标」。
            scope = (ITEM_DEFINITIONS.get(item.definition_id) or {}).get("blind_scope", "radius")
            radius = item.power or 5
            blinded = immune = 0
            for enemy in self.enemies:
                if enemy.integrity <= 0 or enemy.relation == "稳定意识":
                    continue
                if scope == "sight":
                    if not self.is_visible(enemy.x, enemy.y):
                        continue
                elif max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) > radius:
                    continue
                if not self._has_line_of_sight(self.player.x, self.player.y, enemy.x, enemy.y):
                    continue
                if enemy.trait in ("relentless", "author_pace"):
                    immune += 1
                    continue
                enemy.blind_turns = BLIND_TURNS
                blinded += 1
            self.messages.append(tr("强光冲淡了视野：{count} 个失控意识的视距暂时减半。", count=blinded))
            if immune:
                self.messages.append(tr("{count} 个意识不看眼睛，光对它们没有意义。", count=immune))
        elif item.effect == "slick":
            key = str(self.depth)
            self.slick_cells.setdefault(key, set()).add((self.player.x, self.player.y))
            self.messages.append(tr("脚下的格子变得比谎言还滑。"))
        elif item.effect == "ignite_liquid":
            target = self._find_adjacent_flammable()
            if not target:
                return ActionResult(False, tr("相邻没有可以点燃的液态记忆或弥散印象。"))
            x, y = target
            self._ignite_cell(x, y, min(8, (item.power or 2) + 1), by_player=True)
            self.messages.append(tr("余热点燃了相邻的一格记忆。"))
        elif item.effect == "slow_burst":
            # 2026-10-22（P3）：只拖住**敌对关系**（失控意识）；NPC 站进圈里
            # 不该被自己的发条拖慢。持续时间按定义表的 `slow_turns` 读，
            # 且用 max 覆盖——新的一发不能把更长的既有迟缓缩短。
            # 定义字段直接查 ITEM_DEFINITIONS（与 `Item.icon` 同口径，不进存档）。
            definition = ITEM_DEFINITIONS.get(item.definition_id, {})
            duration = int(definition.get("slow_turns", 0) or 5)
            slowed = 0
            for enemy in self.enemies:
                if enemy.integrity <= 0 or getattr(enemy, "relation", "") != "失控意识":
                    continue
                if max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= (item.power or 3):
                    enemy.slow_turns = max(int(getattr(enemy, "slow_turns", 0) or 0), duration)
                    slowed += 1
            self.messages.append(tr("有 {count} 个失控意识的动作被拖住了。", count=slowed))
        elif item.effect == "slow_ring":
            # 千梦铃：铃声走真实声路（`acoustics.propagate` 带墙体衰减），
            # 只听得到的目标才慢下来，不是全图控制。
            from ..acoustics import hears as _hears, propagate
            from ...data.perception import perception_profile
            definition = ITEM_DEFINITIONS.get(item.definition_id, {})
            duration = int(definition.get("slow_turns", 0) or 5)
            radius = int(item.power or 10)
            field = propagate(self, self.player.x, self.player.y, radius)
            origin = (self.player.x, self.player.y)
            slowed = 0
            for enemy in self.enemies:
                if enemy.integrity <= 0 or getattr(enemy, "relation", "") != "失控意识":
                    continue
                profile = perception_profile(getattr(enemy, "catalog_id", ""))
                if profile is not None and profile.hearing is not None:
                    if not _hears(field, enemy.x, enemy.y, profile.hearing,
                                  profile.threshold, origin=origin):
                        continue
                elif (abs(enemy.x - origin[0]) + abs(enemy.y - origin[1])) > radius:
                    continue
                enemy.slow_turns = max(int(getattr(enemy, "slow_turns", 0) or 0), duration)
                slowed += 1
            self.messages.append(tr("铃声传到的地方，有 {count} 个失控意识慢了下来。", count=slowed))
        elif item.effect == "knockback":
            target = self.entity_at(self.player.x + 1, self.player.y) or self.entity_at(self.player.x - 1, self.player.y) or self.entity_at(self.player.x, self.player.y + 1) or self.entity_at(self.player.x, self.player.y - 1)
            if not target or target is self.player:
                return ActionResult(False, tr("相邻没有可以被弹簧推开的目标。"))
            dx = (target.x > self.player.x) - (target.x < self.player.x)
            dy = (target.y > self.player.y) - (target.y < self.player.y)
            self._kill_full_reward = True  # 玩家弹体：崩解全额
            target.integrity = max(0, target.integrity - 1)
            self._push_entity(target, dx, dy, item.power or 3)
            if target.integrity <= 0:
                self._resolve_enemy(target)
            self.messages.append(tr("弹簧折叠件把 {target} 推了出去。", target=tr(target.label)))
        elif item.effect == "parry":
            # 2026-10-22（P3 战术分工）：多份镜面碎片不能把招架叠起来。
            # 已经架好一片就拒绝，且**不消耗**这一片（返回在扣件之前）。
            if self.parry_charges > 0:
                return ActionResult(False, tr("镜面已经架好了：再叠一片不会多挡一次。"))
            # 2026-10-22（P3 第二轮）：架起来的镜面有寿命——`parry_turns` 回合内
            # 没等到打击就自己碎掉，否则一片可以一路架到本层终点。
            # 期限在下面「付完时间」之后才盖章（与无声步同口径：使用这一拍不算）。
            definition = ITEM_DEFINITIONS.get(item.definition_id, {})
            turns = max(1, int(definition.get("parry_turns", 8) or 8))
            self.parry_charges = max(int(self.parry_charges), 1)
            self._parry_pending_turns = turns
            self.messages.append(
                tr("镜面碎片架在了你和梦之间（{turns} 回合内有效）。", turns=turns))
        elif item.effect == "expansion_growth":
            from ..expansion_rewards import apply_growth
            result = apply_growth(self, item.definition_id)
            if not result.changed:
                return result
            self.messages.append(result.message)
        elif item.effect == "learn_ability":
            ability_id = self._learn_random_ability(ITEM_DEFINITIONS.get(item.definition_id, {}).get('ability_pool','general'))
            if ability_id is None:
                self.restore_resource('imagination', 10, ingested=item.category == '摄入物')
                self.messages.append(tr("构想早已全部习得，书页化作 10 点想象力。"))
            else:
                definition = ABILITY_DEFINITIONS[ability_id]
                self.messages.append(tr("你习得了主动构想「{name}」（{description}）", name=tr(definition["name"]), description=tr(definition["description"])))
        else:
            return ActionResult(False, tr("{item}的效果尚未稳定。", item=tr(item.name)))
        item.quantity -= 1
        if item.quantity <= 0:
            self.board.remove_item(item.instance_id)
            self.equipment.invalidate()
            self.inventory.pop(index)
        if self.hang_item_id and not any(entry.instance_id == self.hang_item_id for entry in self.inventory):
            self._refresh_hang()
        self._action_time(1, ActionKind.USE)
        self._emit_item_use_noise(item)
        pending_parry = int(getattr(self, "_parry_pending_turns", 0) or 0)
        if pending_parry:
            # 先付时间、再盖章：使用本身那一拍不计入 8 回合（与无声步同口径）。
            self.parry_until = int(self.time) + pending_parry
            self._parry_pending_turns = 0
        pending_free = int(getattr(self, "_free_action_pending", 0) or 0)
        if pending_free:
            # 同理：底片的免费行动与 5 回合窗口都从「用掉底片之后」开始算。
            self.free_actions = 1
            self.free_action_until = int(self.time) + pending_free
            self._free_action_pending = 0
        message = tr("使用了 {item}。", item=tr(item.name))
        self.messages.append(message)
        return ActionResult(True, message, {"item": item.definition_id,**tool_data})

    @root_action
    @animate_item_action('realm_igniter')
    def use_item(self, index: int = 0) -> ActionResult:
        if "oblivion_strong" in self.portents:
            return ActionResult(False, tr("无念黑渊吞掉了记忆，你想不起这些东西的用法。"))
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        from ..expansion_consumables import tool_unseal
        unsealed = tool_unseal(self, item)
        if unsealed is not None:
            return unsealed
        if item.category == '记忆碎片':
            from ..memory_management import equip_memory
            return equip_memory(self, item.instance_id)
        if item.effect == 'expansion_consumable':
            from .. import expansion_consumables
            spec = ITEM_DEFINITIONS[item.definition_id]['consumable_use']
            if item.definition_id == 'expansion.terrain.x05':
                return ActionResult(True, tr('选择投掷落点，取消不消耗。'), {'throw_aim': index})
            if spec['form'] in ('point', 'pair', 'direction'):
                return ActionResult(True, tr('选择已知目标，取消不消耗。'), {'deploy_aim': index})
            return expansion_consumables.use(self, index)
        if item.definition_id == 'hospital.hollow_lancet':
            return self.open_hospital_lancet_selection(index)
        active = self._gear_active_spec(item.definition_id)
        if active:
            # 扩展包装备的主动行为（2026-10-25）：必须先在联想盘上，
            # 选点形态复用 deploy_aim，自身形态直接结算。
            return self._use_gear_active(index, item, active)
        if not item.effect or item.category not in ("摄入物", "易逝物", "交互道具", "惯用物"):
            return ActionResult(False, tr("{item}当前不能直接使用。", item=tr(item.name)))
        if item.effect in ('hospital_wash_choice', 'hospital_positive_choice'):
            from ..hospital_medicines import open_selection
            return open_selection(self, item)
        if item.definition_id == 'spellbook' and item.effect == 'learn_ability':
            from ..book_learning import open_selection
            return open_selection(self, item)
        if item.effect == 'hospital_tool':
            if item.definition_id == 'hospital.filter_sac':
                return ActionResult(True, tr('选择滤膜囊的落点，取消不消耗。'), {'throw_aim': index})
            return self.use_hospital_tool(index)
        if item.effect == "container":
            # 容器：打开盛装/倒出界面（不耗时、不消耗物品）。
            return ActionResult(True, tr("打开了{item}。", item=tr(item.name)), {"container_menu": index})
        if item.effect == "mirror_insight":
            # 洞察之镜：打开三选一面板（不消耗；选定才消耗）。
            return ActionResult(
                True,
                tr("镜面泛起涟漪——三种可能的领悟浮现出来。"),
                {"mirror_insight": index},
            )
        if item.effect == "enter_realm":
            # 梦中梦入口（2026-09-21）：使用不消耗——钥匙本身就是反复开关的门。
            from ...data.dreams import DREAM_REALM_DEFINITIONS

            realm_id = str(ITEM_DEFINITIONS.get(item.definition_id, {}).get("realm_id", ""))
            if realm_id not in DREAM_REALM_DEFINITIONS:
                return ActionResult(False, tr("{item}对不上任何一扇门。", item=tr(item.name)))
            if self.realm_id:
                return ActionResult(False, tr("你已经在梦中梦里——先从第 1 层上浮出去。"))
            self._action_time(1, ActionKind.USE)
            self.enter_realm(realm_id)
            return ActionResult(True, self.messages[-1], {"realm": realm_id})
        if item_targeting.is_aimed(item.definition_id):
            # 部署类物品（2026-10-22 A2）：夜班灯／应急蜡封选一点，折叠虹吸管／
            # 折好的逃生通道选两点，拆迁线轴选一个方向。取消或非法提交零消耗。
            return ActionResult(
                True,
                tr("举起{item}——点选落点或按方向键（Esc 取消，不消耗）。", item=tr(item.name)),
                {"deploy_aim": index},
            )
        if item.effect in ("fireburst", "tar_burst", "explosion", "sound_lure",
                           "smoke_cloud", "ignite_burst", "spark_rays",
                           "winter_sample", "storm_accumulator", "bottled_sunrise"):
            # 投掷瞄准（2026-09-19）：燃烧瓶/雷管/诱饵/烟雾罐的使用=进入发射
            # 界面选择落点；Esc 取消不消耗，选定落点后由 throw_target 结算。
            # 熔融蜡烛/镁光火柴（ignite_burst）的说明写的就是「掷出去」，一并
            # 进瞄准；原地十字引燃保留在工具面板的直接使用分支里。
            # 2026-10-22（A2）：冬天的样本／未寄出的雷暴／瓶装天亮同样走投掷
            # 管线——落地后由 core/item_devices.py 按回合结算。
            return ActionResult(
                True,
                tr("举起{item}——点选落点或按方向键投掷（Esc 取消，不消耗）。", item=tr(item.name)),
                {"throw_aim": index},
            )
        if item.effect == "fire_once":
            # 一次性发射物（光焰弹）：进入瞄准，沿直线弹道射出后消耗。
            return ActionResult(
                True,
                tr("把{item}压入膛——点选方向或按方向键发射（Esc 取消，不消耗）。", item=tr(item.name)),
                {"fire_once_aim": index},
            )
        if item.effect == "realm_igniter":
            # 引火人的火柴（余烬廊桥保底火源）：点燃 8 邻域内的可燃格。
            # 非消耗（进层授予/出层回收）；近旁没有可燃物时拒绝，不耗行动。
            targets = [
                (self.player.x + dx, self.player.y + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if dx or dy
            ]
            lit = 0
            for (nx, ny) in targets:
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if self._cell_is_flammable(self.cell(nx, ny)):
                    if self._ignite_cell(nx, ny, strength=int(item.power), by_player=True):
                        lit += 1
            if not lit:
                return ActionResult(False, tr("近旁没有能引火的东西——先把燃料铺到身边。"))
            self._action_time(1, ActionKind.USE)
            self._emit_item_use_noise(item, 5)
            message = tr("火柴擦亮了——近旁的可燃物烧了起来。")
            self.messages.append(message)
            return ActionResult(True, message, {"ignite": True})
        return self._use_consumable_item(item, index)

    # ---- 部署类物品（2026-10-22 A2）----
    #
    # 落点合法性只读 core/item_targeting.py（与瞄准界面同一口径）：非法落点与
    # 取消一律不消耗物品、不留装置、不花行动。装置本体在 core/item_devices.py。

    def _consume_inventory_item(self, index: int) -> None:
        """用掉行囊里的一件（数量减一；整堆用完才出栈）。"""
        item = self.inventory[index]
        item.quantity -= 1
        if item.quantity <= 0:
            self.board.remove_item(item.instance_id)
            self.equipment.invalidate()
            self.inventory.pop(index)
        if self.hang_item_id and not any(entry.instance_id == self.hang_item_id
                                         for entry in self.inventory):
            self._refresh_hang()

    # ---- 扩展包装备的主动行为（2026-10-25 批次一）----

    def _gear_active_spec(self, definition_id: str) -> dict | None:
        """装备的主动行为规格；定义表里的 ``active_use`` 是唯一真源。"""
        definition = ITEM_DEFINITIONS.get(definition_id) or {}
        active = definition.get("active_use")
        return active if isinstance(active, dict) else None

    def _use_gear_active(self, index: int, item: Item, active: dict) -> ActionResult:
        """装备主动行为：上盘才可用；选点形态返回 deploy_aim，自身形态直接结算。"""
        from ...equipment import gear_tools
        from ...equipment import gear_light

        if item.instance_id not in self.equipped.values():
            return ActionResult(False, tr("{item}要先装到联想盘上才能这样用。",
                                          item=tr(item.name)))
        # 焦黑遮片举着时占着本句的工具行为：换不了别的工具动作，但它自己可以放下。
        busy = gear_light.tool_busy(self)
        if busy and str(active.get("behavior") or "") != "raise_shield":
            return ActionResult(False, tr("你的另一只手还举着{busy}——先放下它。", busy=busy))
        form = str(active.get("form") or "self")
        if form in ("point", "pair", "direction"):
            return ActionResult(
                True,
                tr("举起{item}——点选落点或按方向键（Esc 取消，不消耗）。",
                   item=tr(item.name)),
                {"deploy_aim": index},
            )
        ok, message, data = gear_tools.use_self(self, item, active)
        if not ok:
            return ActionResult(False, message)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._action_time(1, ActionKind.USE)
        self.messages.append(message)
        return ActionResult(True, message, {"item": item.definition_id, **data})

    def _finish_gear_deploy(self, item: Item, ok: bool, message: str,
                            data: dict, position) -> ActionResult:
        """装备部署成功才扣一次行动；本体可能已被装置接管，故不走消耗路径。"""
        if not ok:
            return ActionResult(False, message)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._action_time(1, ActionKind.USE)
        self.messages.append(message)
        return ActionResult(True, message,
                            {"item": item.definition_id, "position": position, **data})

    @root_action
    def deploy_item(self, index: int, tx: int, ty: int) -> ActionResult:
        """单点部署：误点的夜班灯、应急蜡封。"""
        from .. import item_devices
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.effect == 'expansion_consumable':
            from .. import expansion_consumables
            return expansion_consumables.use(self, index, point=(tx, ty))
        definition_id = item.definition_id
        active = self._gear_active_spec(definition_id) or {}
        if active:
            if str(active.get("form") or "") != "point":
                return ActionResult(False, tr("{item}不能这样放。", item=tr(item.name)))
            if not item_targeting.valid_target(self, definition_id, (tx, ty)):
                return ActionResult(False, tr("那个落点放不下。"))
            from ...equipment import gear_tools
            ok, message, data = gear_tools.use_point(self, item, active, (tx, ty))
            return self._finish_gear_deploy(item, ok, message, data, [tx, ty])
        if definition_id not in ("night_shift_beacon", "wax_emergency_seal"):
            return ActionResult(False, tr("{item}不能这样放。", item=tr(item.name)))
        if not item_targeting.valid_target(self, definition_id, (tx, ty)):
            return ActionResult(False, tr("那个落点放不下。"))
        if definition_id == "night_shift_beacon":
            ok, message, data = item_devices.deploy_beacon(self, tx, ty)
        else:
            ok, message, data = item_devices.deploy_wax_seal(self, tx, ty)
        if not ok:
            return ActionResult(False, message)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._consume_inventory_item(index)
        self._action_time(1, ActionKind.USE)
        self._emit_item_use_noise(item, 6)
        self.messages.append(message)
        return ActionResult(True, message,
                            {"item": definition_id, "position": [tx, ty], **data})

    @root_action
    def deploy_item_pair(self, index: int, ax: int, ay: int,
                         bx: int, by: int) -> ActionResult:
        """成对部署：折叠虹吸管（源／出口）、折好的逃生通道（两端）。"""
        from .. import item_devices
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.effect == 'expansion_consumable':
            from .. import expansion_consumables
            return expansion_consumables.use(self, index, point=(ax, ay), second=(bx, by))
        definition_id = item.definition_id
        active = self._gear_active_spec(definition_id) or {}
        if active:
            if str(active.get("form") or "") != "pair":
                return ActionResult(False, tr("{item}不能这样放。", item=tr(item.name)))
            if not item_targeting.valid_pair(self, definition_id, (ax, ay), (bx, by)):
                return ActionResult(False, tr("这两个落点凑不成一对。"))
            from ...equipment import gear_tools
            ok, message, data = gear_tools.use_pair(
                self, item, active, (ax, ay), (bx, by))
            return self._finish_gear_deploy(item, ok, message, data, [ax, ay])
        if definition_id not in ("portable_siphon", "folded_escape_route"):
            return ActionResult(False, tr("{item}不能这样放。", item=tr(item.name)))
        if not item_targeting.valid_pair(self, definition_id, (ax, ay), (bx, by)):
            return ActionResult(False, tr("这两个落点凑不成一对。"))
        if definition_id == "portable_siphon":
            ok, message, data = item_devices.deploy_siphon(self, (ax, ay), (bx, by))
        else:
            ok, message, data = item_devices.deploy_escape_route(self, (ax, ay), (bx, by))
        if not ok:
            return ActionResult(False, message)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._consume_inventory_item(index)
        self._action_time(1, ActionKind.USE)
        self._emit_item_use_noise(item, 6)
        self.messages.append(message)
        return ActionResult(True, message,
                            {"item": definition_id, "position": [ax, ay], **data})

    @root_action
    def deploy_direction(self, index: int, dx: int, dy: int) -> ActionResult:
        """方向部署：拆迁用的线轴（朝一个方向抽线）。"""
        from .. import item_devices
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.effect == 'expansion_consumable':
            from .. import expansion_consumables
            return expansion_consumables.use(self, index, direction=(dx, dy))
        active = self._gear_active_spec(item.definition_id) or {}
        if active:
            if str(active.get("form") or "") != "direction":
                return ActionResult(False, tr("{item}没有方向可指。", item=tr(item.name)))
            if max(abs(int(dx)), abs(int(dy))) != 1:
                return ActionResult(False, tr("方向无效。"))
            from ...equipment import gear_tools
            ok, message, data = gear_tools.use_direction(
                self, item, active, (int(dx), int(dy)))
            return self._finish_gear_deploy(item, ok, message, data, [int(dx), int(dy)])
        if item.definition_id != "breach_spool":
            return ActionResult(False, tr("{item}没有方向可指。", item=tr(item.name)))
        if max(abs(int(dx)), abs(int(dy))) != 1:
            return ActionResult(False, tr("方向无效。"))
        ok, message, data = item_devices.deploy_spool(self, (int(dx), int(dy)))
        if not ok:
            return ActionResult(False, message)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._consume_inventory_item(index)
        self._action_time(1, ActionKind.USE)
        self._emit_item_use_noise(item, 6)
        self.messages.append(message)
        return ActionResult(True, message, {"item": item.definition_id, **data})

    # ---- 主动构想 ----

    def _blank_pass_eligible(self, cost: int) -> bool:
        """留白险境：想象力**归零**时，每层一次免除一项构想的想象成本。

        平衡方案 §2.1 指出的兑现断点——洞察「留白」的文案早就写了「归零时仍
        可使用一次」，而 activate_ability 在付不起时直接返回失败。这里按方案
        定稿的口径补齐：每层一次、只免想象成本、冷却与行动时间照常；半页空稿
        （blank_pass 携带意象）与洞察「留白」**共用同一次**，这就是低资源收益
        的上限（不做「多件多免」）。
        """
        if self.imagination > 0 or cost <= 0:
            return False
        if self._effect_power("blank_pass") <= 0 and not self.insight_active("留白"):
            return False
        if self.blank_pass_depth == self.depth:
            return False
        self.blank_pass_depth = self.depth
        self.blank_pass_pending = True
        self.messages.append(tr("空着的那半页替你把成本垫上了——这一次不花想象力。"))
        return True

    def _pay_ability_cost(self, cost: int) -> None:
        """构想的想象成本扣费入口（普通调用与效果内部扣费共用一条口径）。"""
        if self.blank_pass_pending:
            self.blank_pass_pending = False
            return
        from ..settlement import REASON_ABILITY_COST, settle_delta
        settle_delta(self, 'imagination', -cost, reason=REASON_ABILITY_COST,
                     source='留白通行')

    def _detach_one_for_action(self, index: int) -> Item | None:
        """为一次投掷／发射从行囊取下「一件」：整堆只花掉一个单位。

        数量大于 1 时原堆留在原地、沿用它的 instance_id，被扔出去的那一只
        换一个新实例 id——否则一次性效果会吞掉整堆，而台面/地上的那一只
        仍要与剩余堆分开拾回。
        """
        item = self.inventory[index] if 0 <= index < len(self.inventory) else None
        if item is None:
            return None
        if item.quantity <= 1:
            return self.inventory.pop(index)
        item.quantity -= 1
        single = replace(item, quantity=1, instance_id=f"item-{self.next_item_id}",
                         contents=dict(item.contents), gas_decay_age=dict(item.gas_decay_age))
        self.next_item_id += 1
        return single

    def _spend_for_throw(self, index: int) -> Item | None:
        """投掷前的取件：分次部署的物品只扣一段，整件留在行囊。

        烟雾双联罐是两只罐头缠在一起（`deploy_charges=2`）：第一次投掷只放掉
        一只，第二次得再花一次行动——所以这里不摘件，只减余量。其余物品照
        `_detach_one_for_action` 的老口径整件离手。
        """
        item = self.inventory[index] if 0 <= index < len(self.inventory) else None
        if item is None:
            return None
        if int(getattr(item, "charges", 0) or 0) > 1:
            item.charges -= 1
            return item
        return self._detach_one_for_action(index)

    def _note_deploy_charges(self, item: Item) -> None:
        """分次部署：还有罐子没放完时说清楚，别让玩家以为整件用光了。"""
        left = int(getattr(item, "charges", 0) or 0)
        if left > 0:
            self.messages.append(tr("{item}还剩 {n} 只要投——每次部署各花一次行动。",
                                    item=tr(item.name), n=left))

    @root_action
    def throw_item(self, index: int = 0, dx: int = 1, dy: int = 0) -> ActionResult:
        """投掷（2026-09-18 触发机制补全）：沿 (dx,dy) 飞行至多 6 格。

        飞行遇墙/边界停在墙前；落点按物品 effect 结算——爆炸物（explosion）
        以落点为爆心引爆（半径吃 blast_radius 装备加成）、燃烧瓶（fireburst）
        在落点周围燃起火海、镁光类（ignite_burst）点燃落点十字相邻的可燃格。
        其它物品照旧落地成为 WorldItem（走过去可拾回）。
        """
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        if max(abs(dx), abs(dy)) != 1:
            return ActionResult(False, tr("投掷方向无效。"))
        item = self.inventory[index]
        if item.instance_id in self.equipped.values():
            return ActionResult(False, tr("携带意象仍在使用中，不能投掷。"))
        if item.definition_id == 'expansion.terrain.x05':
            from .. import expansion_consumables
            landing = throwing.directional_landing(self, dx, dy)
            return expansion_consumables.use(self, index, point=landing)
        thrown = self._spend_for_throw(index)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        # 几何与结算集中在 core.throwing（与弹道 ballistics 并列）。
        origin = (self.player.x, self.player.y)
        x, y = throwing.directional_landing(self, dx, dy)
        self._action_time(self._dream_action_time(1, 'throwing'), ActionKind.USE)
        # 弹道动画（2026-09-23）：投掷与发射共用飞行动画，收尾是落点一闪。
        throw_path = throwing.flight_path(origin, (x, y))
        self._note_projectile(
            throw_path, [], kind="throw", color=thrown.color or "#ffd166",
            end="land", end_cell=(x, y), origin=origin,
        )
        data: dict[str, Any] = {"item": thrown.definition_id, "position": [x, y]}
        message, extra = throwing.resolve_landing(self, thrown, x, y)
        data.update(extra)
        self.messages.append(message)
        self._note_deploy_charges(thrown)
        return ActionResult(True, message, data)

    @root_action
    def ignite_item_here(self, index: int = 0) -> ActionResult:
        """原地点燃（§14.4.1）：镁光火柴的副动作，不进入投掷瞄准。

        与落点选在脚下共用 `resolve_landing`，强度、材料要求与自身风险完全
        一致；只接受明文具备该双方式的物品，不能把所有点火物都改成原地释放。
        """
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.definition_id != "magnesium_match" or item.effect != "ignite_burst":
            return ActionResult(False, tr("{item}没有原地点燃这个用法。", item=tr(item.name)))
        if item.instance_id in self.equipped.values():
            return ActionResult(False, tr("携带意象仍在使用中，不能使用。"))
        lit = self._detach_one_for_action(index)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._action_time(self._dream_action_time(1, 'throwing'), ActionKind.USE)
        message, extra = throwing.resolve_landing(
            self, lit, self.player.x, self.player.y)
        data: dict[str, Any] = {"item": lit.definition_id,
                                "position": [self.player.x, self.player.y]}
        data.update(extra)
        self.messages.append(message)
        return ActionResult(True, message, data)

    @root_action
    @animate_item_action('mirror_insight')
    def choose_mirror_insight(self, index: int, insight_name: str) -> ActionResult:
        """洞察之镜三选一：获得选中的洞察并消耗镜子。

        只接受开镜时掷出的候选；选择即消耗，镜子不可复用。
        """
        from ..content import INSIGHT_DEFINITIONS
        import random as _random

        if insight_name not in INSIGHT_DEFINITIONS:
            return ActionResult(False, tr("镜面里没有这个映像。"))
        if not (0 <= index < len(self.inventory)) or self.inventory[index].effect != "mirror_insight":
            return ActionResult(False, tr("你没有洞察之镜。"))
        owned = set(self.insights)
        rng = _random.Random(self.seed ^ (self.time * 613) ^ index)
        pool = [name for name in INSIGHT_DEFINITIONS
                if name not in owned and insight_learnable(self, name)]
        rng.shuffle(pool)
        candidates = pool[:3]
        if insight_name not in candidates:
            return ActionResult(False, tr("镜面里没有这个映像。"))
        self.inventory.pop(index)
        grant = self._grant_insight(insight_name)
        self.run_stats["events"] = self.run_stats.get("events", 0) + 1
        message = tr("镜面碎裂——你留下了「{insight}」。", insight=tr(insight_name))
        if grant:
            self.messages.append(message)
        return ActionResult(True, message, {"mirror_used": True})

    def mirror_candidates(self, index: int) -> list[str]:
        """开镜时掷出的三种候选洞察（排除已持有的）。"""
        from ..content import INSIGHT_DEFINITIONS
        import random as _random

        rng = _random.Random(self.seed ^ (self.time * 613) ^ index)
        pool = [name for name in INSIGHT_DEFINITIONS
                if name not in self.insights and insight_learnable(self, name)]
        rng.shuffle(pool)
        return pool[:3]

    @root_action
    def throw_target(self, index: int, tx: int, ty: int) -> ActionResult:
        """瞄准投掷（2026-09-19）：把物品扔到指定落点，以落点为中心结算。

        投掷可越过低台面，但不能穿越高墙或封闭斜角。已知非法目标零消耗；
        未知路径的真实阻挡在出手后使落点提前，不退款或补扔。
        """
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.instance_id in self.equipped.values():
            return ActionResult(False, tr("携带意象仍在使用中，不能投掷。"))
        ok, reason = throwing.is_valid_target(self, tx, ty)
        if not ok:
            return ActionResult(False, reason)
        origin = (self.player.x, self.player.y)
        # Unknown intermediate obstacles are resolved only after the legal
        # submission; the actual shorter flight still spends this throw once.
        trace=throwing.trace_throw(self,tx,ty)
        tx,ty=trace.landing
        if item.definition_id == 'expansion.terrain.x05':
            from .. import expansion_consumables
            result = expansion_consumables.use(self, index, point=(tx, ty))
            if result.changed:
                self._note_projectile(list(trace.path), [], kind='throw', color=item.color,
                                      end='land', end_cell=(tx, ty), origin=origin)
            return result
        if item.definition_id == 'hospital.filter_sac':
            combat_before = getattr(self, '_combat_fx_seq', 0)
            result = self._deploy_hospital_tool(index, tx, ty)
            if result.changed:
                self.run_stats['items_used']=self.run_stats.get('items_used',0)+1
                result.data.update(item=item.definition_id,position=[tx,ty])
                self._note_projectile(list(trace.path), [],
                    kind='throw', color=item.color, end='land', end_cell=(tx, ty), origin=origin)
                for event in getattr(self, '_combat_fx_events', ()):
                    if event['seq'] > combat_before and event.get('cast_id') == 'item:'+item.definition_id:
                        event['projectile_seq'] = self.last_projectile['seq']
            return result
        thrown = self._spend_for_throw(index)
        self.run_stats["items_used"] = self.run_stats.get("items_used", 0) + 1
        self._action_time(self._dream_action_time(1, 'throwing'), ActionKind.USE)
        # 弹道动画（2026-09-23）：瞄准投掷沿「玩家 → 落点」两轴步进回放。
        aim_path = list(trace.path)
        self._note_projectile(
            aim_path, [], kind="throw", color=thrown.color or "#ffd166",
            end="land", end_cell=(tx, ty), origin=origin,
        )
        data: dict[str, Any] = {"item": thrown.definition_id, "position": [tx, ty]}
        message, extra = throwing.resolve_landing(self, thrown, tx, ty)
        data.update(extra)
        self.messages.append(message)
        self._note_deploy_charges(thrown)
        return ActionResult(True, message, data)
    @root_action
    def drop_item(self, index: int = 0) -> ActionResult:
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        if item.instance_id in self.equipped.values():
            return ActionResult(False, tr("携带意象仍在使用中，不能直接放下。"))
        self.inventory.pop(index)
        cell = self.cell(self.player.x, self.player.y)
        surface = cell.wall_kind if cell.wall_kind in TABLE_KINDS else ""
        self.world_items.append(
            WorldItem(item, self.player.x, self.player.y, surface=surface))
        self._action_time(1, ActionKind.USE)
        message = tr("放下了 {item}。", item=tr(item.name))
        self.messages.append(message)
        return ActionResult(True, message, {"item": item.definition_id})
