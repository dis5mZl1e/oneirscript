"""征兆管线：材料赋予 / 冻结 / 衰减、周期与连续效果、镇静拦截心智损失。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..i18n import tr
from ..materials import (
    DOOR_KINDS,
    GAS_DEFINITIONS,
    LIQUID_DEFINITIONS,
    MERCURY_GAS_THRESHOLD_REDUCTION,
    PORTENT_DEFINITIONS,
    material_cleanses,
    plant_def_for,
    portent_def,
)
from .constants import (
    ATTACH_PORTENT_ROUNDS,
    PORTENT_CONTACT_MIN,
    PORTENT_DURATION_CAP,
    PORTENT_STACK_CAP,
    PORTENT_EXTRA_TURN_CAP,
    PORTENT_STACK_SPEED_MIN,
    PORTENT_STACK_SPEED_MAX,
    ActionKind,
    portent_scaled_amount,
)
from .entities import Cell, Entity

# 异象主动技能的软控制征兆（迟拍/缝影/倦意）：玩家的移步加值总额封顶 0.5
# （调参规则「软控制总移步加值上限」= 0.5），见 _portent_move_penalty。
_SK_SOFT_CONTROL = frozenset({"sk_late_beat", "sk_seam_shadow", "sk_drowsy"})


@dataclass(frozen=True)
class VisionProfile:
    """征兆对普通视距的分类修正（docs 261022 §14.1 的聚合口径）。

    应用顺序固定：先 `positive` 与其余正面来源求基础，再 `flat`／`blur` 平减，
    然后 `ratio` 比例缩视，最后 `blinds` 覆盖为 0。`blur`／`blur_floor` 是
    失焦自己的那一项——它只允许把结果压到 `blur_floor`，别的限视照常生效。
    """

    positive: int = 0
    flat: int = 0
    ratio: float = 1.0
    blinds: bool = False
    blur: int = 0
    blur_floor: int = 0



class PortentMixin:
    PORTENT_PROTECTION_TURNS = 3

    def _portent_round_budget(self, holder: Entity, portent_id: str, definition,
                              duration: int, attach: int = 0) -> int:
        """One successful acquisition's hard lifetime, in real world rounds.

        The budget is not a new display duration; it only prevents continuous
        contact from renewing a round forever. No natural-duration definition is
        left on its existing counter mechanism.
        """
        if duration <= 0:
            return 0
        stacks = int(getattr(definition, "stacks", 0) or 0)
        if stacks > 0:
            drop = max(1, int(getattr(definition, "duration_drop", 1) or 1))
            layers = max(1, math.ceil(stacks / drop))
        else:
            layers = 1
        budget = max(1, int(duration) * layers + max(0, int(attach)))
        # 单轮硬期限上限（docs 261022 §14.1：致盲 2 回合、单轮最长 3）：
        # 只会收紧推导出的预算，永不放宽；深化的强闪光因此也不能突破 3 回合。
        cap = int(getattr(definition, "round_max", 0) or 0)
        return min(budget, cap) if cap > 0 else budget

    def _portent_round_started(self, holder: Entity, portent_id: str, definition,
                               duration: int, attach: int = 0) -> None:
        if portent_id in holder.portent_deadlines:
            return
        budget = self._portent_round_budget(holder, portent_id, definition, duration, attach)
        if budget:
            holder.portent_deadlines[portent_id] = int(self.time) + budget

    def _portent_protected(self, holder: Entity, portent_id: str) -> bool:
        return int(holder.portent_protection.get(portent_id, 0) or 0) > int(self.time)

    def _apply_direct_portent(self, holder: Entity, portent_id: str, duration: int,
                              *, mode: str = "max") -> bool:
        """Timed direct write with the same eligibility gate as material contact.

        Every non-material source funnels here so a stale ``portents[...] = n``
        cannot bypass the hidden protection window or start a new round after
        the hard deadline has already closed.
        """
        if holder is self.player and getattr(self,'stasis_turns',0)>0:
            return False
        definition = portent_def(portent_id)
        if definition is None:
            return False
        if holder is self.player and self._identity_immune(portent_id):
            return False
        if self._portent_protected(holder, portent_id):
            return False
        value = max(0, int(duration))
        current = int(holder.portents.get(portent_id, 0) or 0)
        if mode == "add":
            value = current + value
        elif mode != "set":
            value = max(current, value)
        if value <= 0:
            return False
        holder.portents[portent_id] = value
        holder.portent_debt[portent_id] = 0.0
        if int(definition.duration or 0) > 0:
            self._portent_round_started(
                holder, portent_id, definition, value,
                int(holder.portent_attach.get(portent_id, 0) or 0))
        return True

    def portent_remaining(self, holder: Entity, portent_id: str) -> int:
        """Display the actual sustainable remainder, not a frozen source timer."""
        remaining = max(0, int(holder.portents.get(portent_id, 0) or 0))
        deadline = holder.portent_deadlines.get(portent_id)
        if deadline is not None:
            remaining = min(remaining, max(0, int(deadline) - int(self.time)))
        return remaining

    def _remember_portent_end(self, holder: Entity, portent_id: str) -> None:
        """True removal starts the hidden three-round protection window."""
        holder.portents.pop(portent_id, None)
        holder.portent_debt.pop(portent_id, None)
        holder.portent_stacks.pop(portent_id, None)
        holder.portent_attach.pop(portent_id, None)
        holder.portent_deadlines.pop(portent_id, None)
        holder.portent_protection[portent_id] = (
            int(self.time) + self.PORTENT_PROTECTION_TURNS)

    def _finish_deadline_portents(self, holder: Entity) -> list[str]:
        finished = []
        for portent_id, deadline in list(holder.portent_deadlines.items()):
            if int(self.time) >= int(deadline):
                self._remember_portent_end(holder, portent_id)
                finished.append(portent_id)
        return finished

    @property
    def portents(self) -> dict[str, int]:
        """玩家的征兆计时器（唯一真源是玩家实体，其他生物各自持有）。"""
        return self.player.portents

    @property
    def portent_debt(self) -> dict[str, float]:
        """玩家征兆的周期结算欠账。"""
        return self.player.portent_debt

    @property
    def portent_attach(self) -> dict[str, int]:
        """玩家征兆的材料附着计时（与 portents 同口径：真源在玩家实体上）。"""
        return self.player.portent_attach

    def active_portents(self) -> list[dict[str, str]]:
        """当前生效的征兆（自身状态 + 材料赋予）。

        名称/性质/效果文字统一取自 materials.PORTENT_DEFINITIONS，只有需要显示
        剩余量的少数几条在这里覆盖 effect 文本。kind：正面（增益）/ 负面
        （负担）/ 中性（双刃）。

        计数口径见 `PortentDef`：`stacks` = 层（使用次数/份数，不随时间消失）、
        `remaining` = 回合（持续时间）。两者独立，面板先层后回合。
        """
        portents: list[dict[str, str]] = []

        def add(portent_id: str, effect: str | None = None, remaining: int | None = None,
                stacks: int | None = None) -> None:
            definition = portent_def(portent_id)
            if definition is None:
                return
            entry: dict[str, str] = {
                "id": portent_id,
                "name": definition.name,
                "kind": definition.kind,
                "effect": effect or definition.effect,
            }
            if remaining is not None:
                entry["remaining"] = str(remaining)
            if stacks is not None:
                entry["stacks"] = str(stacks)
            portents.append(entry)

        from .drug_debts import mind_debt_status
        mind_bill = mind_debt_status(self)
        if mind_bill is not None:
            portents.append(mind_bill)
        from .timed_actions import modem_status
        modem = modem_status(self)
        if modem is not None:
            portents.append(modem)
        if self.overclock_turns > 0:
            from .drug_debts import balance
            effect = tr("浓缩咖啡因的还款期：每 2 回合清醒度 −1（剩约 {turns} 回合）。", turns=self.overclock_turns)
            effect += ' ' + tr('尚欠清醒度 {n} 点（各份独立结算）。', n=balance(self))
            add("overclock", effect, self.overclock_turns)
        if self.viscous_debt > 0:
            add("viscous_debt")
        if self.free_actions > 0:
            # 2026-10-22（P3）：底片有 5 回合窗口，面板要给出剩余，别让人以为能一直揣着。
            if self.free_action_until:
                left = max(0, int(self.free_action_until) - int(self.time))
                add("double_exposure",
                    tr("下一个正式动作不耗时（剩 {turns} 回合内有效）。", turns=left), left)
            else:
                add("double_exposure")
        if self.free_move_pending > 0:
            add("free_move")
        if self.free_liquid_moves > 0:
            add("liquid_glide", tr("沿液体直线移动不耗时（剩 {count} 格）。", count=self.free_liquid_moves), self.free_liquid_moves)
        if self.parry_charges > 0:
            # 镜面架势：层 = 还能反弹几次（用完即消失），不随回合衰减。
            # 2026-10-22（P3 第二轮）：架起来的镜面有寿命，面板同时给出剩余回合，
            # 否则玩家会以为它能一路架到本层终点。
            if self.parry_until:
                left = max(0, int(self.parry_until) - int(self.time))
                add("mirror_stance",
                    tr("镜面碎片架在你和梦之间：下一记打击会被退回（剩 {turns} 回合）。",
                       turns=left),
                    left, stacks=self.parry_charges)
            else:
                add("mirror_stance", stacks=self.parry_charges)
        if self.hang_item_id:
            hung = next((item.name for item in self.inventory if item.instance_id == self.hang_item_id), None)
            if hung:
                add("hanged_stand_in", tr("{item}挂在梦的墙上，将替你承受下一次打击。", item=tr(hung)))
        lens = self.equipment.find_effect("lamp")
        if lens and self.turns_since_descend <= 3:
            add("lens_afterglow")
        if self.light_turns > 0:
            add("illumination", tr("全图被照亮（剩 {turns} 回合）：你看得见所有异象，它们也看得见你。", turns=self.light_turns), self.light_turns)
        if self.portent_ward_turns > 0 and self.portent_ward_id:
            ward = portent_def(self.portent_ward_id)
            add("refuge_ward",
                tr("留灯的抵抗：接下来 {n} 回合，新沾染的「{name}」时长减少 25%。",
                   n=self.portent_ward_turns,
                   name=tr(ward.name if ward else self.portent_ward_id)),
                self.portent_ward_turns)
        for portent_id in self.portents:
            definition = portent_def(portent_id)
            if definition is None:
                continue
            stacks = None
            if definition.stacks:
                # 层数从实体自己的记账取（默认取定义里的初始层数）。
                stacks = self.player.portent_stacks.get(portent_id, definition.stacks)
            add(portent_id, remaining=self.portent_remaining(self.player, portent_id),
                stacks=stacks)
        return portents

    @staticmethod
    def _cell_holds_material(cell: Cell, material: str, min_amount: int = PORTENT_CONTACT_MIN) -> bool:
        """格子是否还在提供这种材料（浓度达到征兆触发下限）。

        门槛优先取征兆定义里的 ``min_amount``（《新材料》表按材料规定），
        未登记时沿用全局接触下限。
        """
        if not material:
            return False
        if material in GAS_DEFINITIONS:
            return cell.gas >= min_amount and cell.gas_kind == material
        if material in LIQUID_DEFINITIONS:
            return cell.liquid >= min_amount and cell.liquid_kind == material
        return False

    def _gas_portent_min(self, cell: Cell, definition) -> int:
        """气体征兆在此格的触发浓度：站在水银液面上时 −5（至少 1）。

        水银是站位即触发的液体效果（非征兆、不减速）——它压低的是本格气体
        「渗进意识」的门槛；离开水银后恢复原浓度要求。
        """
        min_amount = definition.min_amount
        if definition.material in GAS_DEFINITIONS and self._cell_holds_material(cell, "水银"):
            min_amount = max(1, min_amount - MERCURY_GAS_THRESHOLD_REDUCTION)
        return min_amount

    def _material_portent_ids(self, cell: Cell) -> tuple[str, ...]:
        return tuple(
            portent_id
            for portent_id in PORTENT_DEFINITIONS
            if self._cell_holds_material(
                cell,
                PORTENT_DEFINITIONS[portent_id].material,
                self._gas_portent_min(cell, PORTENT_DEFINITIONS[portent_id]),
            )
        )

    def _grant_material_portents(self, holder: Entity, cell: Cell) -> list[str]:
        """接触材料即按 duration 赋予征兆；已存在时不叠加，只维持原计时。

        「站在其中不增加也不减少」由这里的不叠加与 _tick_entity_portents 的
        冻结共同保证。
        """
        granted: list[str] = []
        if holder is self.player and getattr(self,'stasis_turns',0)>0:
            return granted
        for portent_id in self._material_portent_ids(cell):
            definition = portent_def(portent_id)
            if definition is None or definition.duration <= 0:
                continue
            if holder is self.player and self._identity_immune(portent_id):
                continue
            if not definition.affects_creatures and holder is not self.player:
                continue
            debt = holder.portent_debt
            if self._portent_protected(holder, portent_id):
                continue
            current = holder.portents.get(portent_id, 0)
            if current > 0:
                continue
            duration = min(definition.duration, PORTENT_DURATION_CAP)
            if (
                holder is self.player and self._effect_power("liquid_ward") > 0
                and definition.material in LIQUID_DEFINITIONS
            ):
                # 打蜡的雨衣（扩展包 v1）：液体接触的负面征兆时长减半。
                duration = max(1, duration // 2)
            if (
                holder is self.player and self.portent_ward_turns > 0
                and portent_id == self.portent_ward_id
            ):
                # R03 留灯的避难圈：只缩短这一种明示负面征兆的**新沾染**时长 25%
                # （已存在的不叠加、不追改——天然满足「只对新赋予应用」）。
                duration = max(1, math.ceil(duration * 0.75))
            if holder is self.player:
                from .stats import resolve_stat
                duration = int(resolve_stat(
                    self, "portent.effective_duration",
                    {"portent": portent_id, "base": duration, "player": True}).value)
            holder.portents[portent_id] = self._hospital_initial_duration(holder, portent_id, duration)
            debt[portent_id] = 0.0
            if definition.stacks > 0:
                # 带层数的征兆：授予时按定义补满初始层数（回合归零只降层）。
                holder.portent_stacks[portent_id] = min(definition.stacks, PORTENT_STACK_CAP)
            if definition.material:
                # 附着层（2026-10-07，D3=B 环境也附着）：材料黏在意识上，离开来源后
                # 附着期内全额续效且不走衰减。打蜡的雨衣对附着同样减半。
                attach_rounds = ATTACH_PORTENT_ROUNDS
                if (
                    holder is self.player and self._effect_power("liquid_ward") > 0
                    and definition.material in LIQUID_DEFINITIONS
                ):
                    attach_rounds = max(1, attach_rounds // 2)
                if holder is self.player:
                    from .stats import resolve_stat
                    attach_rounds = int(resolve_stat(
                        self, "portent.effective_duration",
                        {"portent": portent_id, "base": attach_rounds, "player": True}).value)
                holder.portent_attach[portent_id] = (self._identity_attachment(portent_id, cell, attach_rounds)
                    if holder is self.player else attach_rounds)
            else:
                attach_rounds = 0
            self._portent_round_started(holder, portent_id, definition, duration, attach_rounds)
            granted.append(portent_id)
            if portent_id == "cursed_sight" and holder is self.player:
                # 诅咒灵视的代价：所有失控意识同时看见你的位置。
                for enemy in self.enemies:
                    if enemy.integrity > 0:
                        enemy.alert_state = "追踪"
        return granted

    def _cleanse_material_portents(self, holder: Entity, cell: Cell) -> list[str]:
        """清洗材料（水等）接触时洗掉指定征兆，且不赋予任何征兆。

        适用范围只到「液体/气体为清洗材料」的格子——浓度需达到接触下限，
        与赋予征兆共用同一把尺子。返回被洗掉的征兆 id 列表（供提示语）。
        """
        removed: list[str] = []
        cleansers: list[str] = []
        if cell.liquid >= PORTENT_CONTACT_MIN and cell.liquid_kind in LIQUID_DEFINITIONS:
            cleansers.append(cell.liquid_kind)
        if cell.gas >= PORTENT_CONTACT_MIN and cell.gas_kind in GAS_DEFINITIONS:
            cleansers.append(cell.gas_kind)
        if not cleansers:
            return removed
        washed: set[str] = set()
        for material in cleansers:
            washed |= material_cleanses(material)
        for portent_id in list(holder.portents):
            if portent_id in washed:
                self._remember_portent_end(holder, portent_id)
                removed.append(portent_id)
        return removed

    def _tick_entity_portents(self, holder: Entity, cell: Cell, amount: int) -> list[str]:
        """离开来源材料后逐回合递减；仍站在材料中则计时冻结。

        回合归零时（玩家口径）：**只降 1 层**（`duration_drop`），并把回合计时
        重置为默认时长，让下一层继续按同样的时钟衰减；层数归零才移除征兆。
        没有层数的征兆（`stacks <= 0`）维持旧行为——回合归零即消失。
        """
        expired: list[str] = []
        if holder is self.player:
            self._clear_identity_immunities()
        for portent_id in list(holder.portents):
            definition = portent_def(portent_id)
            if definition is None:
                holder.portents.pop(portent_id, None)
                holder.portent_debt.pop(portent_id, None)
                holder.portent_attach.pop(portent_id, None)
                continue
            if (portent_id not in holder.portent_deadlines
                    and int(definition.duration or 0) > 0):
                # Compatibility/backfill: old saves or direct writes without a
                # round record get one finite budget from the current remainder.
                self._portent_round_started(
                    holder, portent_id, definition,
                    int(holder.portents.get(portent_id, 0)),
                    int(holder.portent_attach.get(portent_id, 0) or 0))
            deadline = holder.portent_deadlines.get(portent_id)
            if deadline is not None and int(self.time) >= int(deadline):
                # §17: continuous contact may keep the in-round presentation,
                # but it cannot extend this hard boundary forever.
                self._remember_portent_end(holder, portent_id)
                expired.append(portent_id)
                continue
            # 气体冻结与赋予共用门槛，含水银降低；强控残气不能靠旧通用值 5 续期。
            # 液体仍保留原有的低浓度浸泡冻结规则。
            if not (holder is self.player and getattr(self,'stasis_turns',0)>0) and self._cell_holds_material(
                cell, definition.material,
                (self._gas_portent_min(cell, definition)
                 if definition.material in GAS_DEFINITIONS
                 else min(PORTENT_CONTACT_MIN, definition.min_amount)),
            ):
                # 仍在材料中：附着补满（保持「被浸透」的状态）。
                if definition.material:
                    attach = ATTACH_PORTENT_ROUNDS
                    if holder is self.player:
                        attach = self.memory_portent_duration(portent_id, attach)
                        if self._effect_power('liquid_ward') > 0 and definition.material in LIQUID_DEFINITIONS:
                            attach = max(1, attach // 2)
                        attach = self._identity_attachment(portent_id, cell, attach)
                    holder.portent_attach[portent_id] = attach
                continue
            # 附着层（2026-10-07）：离开来源材料后，黏在意识上的材料让征兆
            # 全额续效且不走衰减；附着耗尽才进入正常的回合衰减。
            decay = amount
            if definition.material:
                attach = holder.portent_attach.get(portent_id, 0)
                if attach > 0:
                    consumed = min(attach, amount)
                    holder.portent_attach[portent_id] = attach - consumed
                    decay -= consumed
                    if decay <= 0:
                        continue
                holder.portent_attach.pop(portent_id, None)
            holder.portents[portent_id] = holder.portents[portent_id] - decay
            if holder.portents[portent_id] > 0:
                continue
            # 回合走完：带层数的征兆只掉层、并重置回合计时（层还在就还在生效）。
            remaining_stacks = holder.portent_stacks.get(portent_id, definition.stacks)
            if definition.stacks > 0 and remaining_stacks > 0:
                remaining_stacks -= definition.duration_drop
                if remaining_stacks > 0:
                    holder.portent_stacks[portent_id] = remaining_stacks
                    holder.portents[portent_id] = min(
                        definition.duration, PORTENT_DURATION_CAP
                    )
                    holder.portent_debt[portent_id] = 0.0
                    continue
            self._remember_portent_end(holder, portent_id)
            expired.append(portent_id)
        return expired

    def _refresh_player_portents(self) -> None:
        self._clear_identity_immunities()
        cell = self.cell(self.player.x, self.player.y)
        for portent_id in self._cleanse_material_portents(self.player, cell):
            definition = portent_def(portent_id)
            if definition is not None:
                self.messages.append(tr("水把身上的「{name}」冲净了。", name=tr(definition.name)))
        for portent_id in self._grant_material_portents(self.player, cell):
            definition = portent_def(portent_id)
            self.messages.append(tr("你沾染了「{name}」的征兆。", name=tr(definition.name)))

    def _apply_player_portent_effects(self, amount: int) -> None:
        """征兆的周期性与连续性效果。

        周期性效果（中毒、灼伤、腐蚀、温热、醉酒等）走 portent_debt 累加器，
        每满 period 回合结算一次；连续性效果在 effective_sight_radius / _effective_*
        里读取。镇静不走周期结算，而是拦截一切心智减少（见 _lose_mind）。
        """
        if getattr(self,'stasis_turns',0)>0:
            return
        self._clear_identity_immunities()
        cell = self.cell(self.player.x, self.player.y)
        suppressed = self._suppressed_portent_ids()
        if "burning" not in self.portents:
            self.portent_debt.pop("__burning__", None)
        for portent_id in list(self.portents):
            definition = portent_def(portent_id)
            if definition is None or definition.period <= 0 or portent_id in suppressed:
                continue
            if not (definition.mind or definition.lucidity or definition.imagination):
                continue
            if portent_id == 'hospital_spore' and (
                    self.portents.get('hospital_oxygen', 0) > 0
                    or any(pid != portent_id and pid not in suppressed and portent_def(pid)
                           and portent_def(pid).material in GAS_DEFINITIONS
                           and portent_def(pid).mind < 0 and portent_def(pid).period > 0
                           for pid in self.portents)):
                self.portent_debt[portent_id] = 0
                continue
            harmful = definition.mind < 0 or definition.lucidity < 0 or definition.imagination < 0
            if harmful:
                # 积累耐受统一走属性解析（docs §10 第四批）：显示与结算同源。
                from .stats import resolve_stat
                accumulation = amount * resolve_stat(
                    self, "portent.accumulation_factor", {"portent": portent_id}).value
            else:
                accumulation = amount
            debt = self.portent_debt.get(portent_id, 0.0) + accumulation
            scale_depth = self._portent_scale_depth()
            while debt >= definition.period:
                debt -= definition.period
                if definition.mind:
                    delta = definition.mind if portent_id == 'hospital_spore' else portent_scaled_amount(definition.mind, scale_depth)
                    if delta < 0:
                        self._lose_mind(-delta)
                    else:
                        self.restore_resource('mind', delta)
                from .settlement import (
                    REASON_ENVIRONMENT as _ENV, REASON_RESTORE_NATURAL as _NATURAL,
                    settle_delta,
                )
                if definition.lucidity:
                    amount_lucidity = portent_scaled_amount(definition.lucidity, scale_depth)
                    settle_delta(
                        self, 'lucidity', amount_lucidity,
                        reason=_NATURAL if amount_lucidity > 0 else _ENV,
                        source=str(definition.name), channel='portent',
                    )
                if definition.imagination:
                    amount_imagination = portent_scaled_amount(definition.imagination, scale_depth)
                    settle_delta(
                        self, 'imagination', amount_imagination,
                        reason=_NATURAL if amount_imagination > 0 else _ENV,
                        source=str(definition.name), channel='portent',
                    )
            self.portent_debt[portent_id] = debt
        # 过电与静电尘联动：身上有电、脚下又有静电尘时，漏电更严重。
        if "charged" in self.portents and self._cell_holds_material(cell, "静电尘"):
            from .settlement import REASON_ENVIRONMENT, settle_delta
            settle_delta(
                self, 'lucidity', -self._identity_environment_trauma(amount, 'electric'),
                reason=REASON_ENVIRONMENT, source='静电尘漏电')
            self.messages.append(tr("静电尘把你身上的残余电流续上了：清醒度又掉了一点。"))
        # 燃烧征兆（2026-09-19）：火焰格沾染，每回合心智/清醒各 −1；
        # 进入水域（脚下有水）或征兆自然到期即止。
        if "burning" in self.portents and self._effect_power("fire_ward") <= 0:
            if self._cell_holds_material(self.cell(self.player.x, self.player.y), "水", 1):
                self._remember_portent_end(self.player, "burning")
                self.messages.append(tr("水浸过全身，火焰熄了。"))
            else:
                # 火焰格只走一次直接伤害；离开后余火每两回合消耗一点清醒。
                if cell.flame <= 0:
                    debt = self.portent_debt.get("__burning__", 0.0) + amount
                    ticks = int(debt // 2)
                    self.portent_debt["__burning__"] = debt % 2
                    from .settlement import REASON_ENVIRONMENT, settle_delta
                    settle_delta(
                        self, 'lucidity',
                        -self._identity_environment_trauma(ticks, 'fire', direct=False),
                        reason=REASON_ENVIRONMENT, source='余火')
        # 可燃气体附着：紧邻火焰时持续灼烧。
        if "volatile" in self.portents:
            burning = any(
                self.cell(nx, ny).flame > 0
                for nx, ny in ((self.player.x + 1, self.player.y), (self.player.x - 1, self.player.y),
                               (self.player.x, self.player.y + 1), (self.player.x, self.player.y - 1))
                if 0 <= nx < self.width and 0 <= ny < self.height
            )
            if burning:
                from .settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(
                    self, 'lucidity',
                    -self._identity_environment_trauma(amount, 'fire', direct=False),
                    reason=REASON_ENVIRONMENT, source='可燃气体引燃')
                self.messages.append(tr("身上的可燃气体被引燃了：清醒度 −1。"))
        # 诅咒灵视的另一半代价：只要征兆还在，所有失控意识就持续看得见你。
        # 授予那一刻已经拉过一次警戒，这里负责「持续期间」——本层新刷出的、
        # 或后来被清掉警戒的异象同样会重新盯上你。
        if "cursed_sight" in self.portents:
            newly_alerted = 0
            for enemy in self.enemies:
                if enemy.integrity <= 0 or enemy.alert_state == "追踪":
                    continue
                enemy.alert_state = "追踪"
                newly_alerted += 1
            if newly_alerted:
                self.messages.append(
                    tr("灵视的代价：又有 {count} 个失控意识看见了你的位置。", count=newly_alerted)
                )

    def _tick_honeyed(self, amount: int) -> None:
        """蜂蜜的滋养：每 2 回合恢复 1×深度档位 点清醒度，每层上限 6（蜜脉翻倍）。

        2026-10-07：恢复量按深度函数缩放（浅层 ×1 … 深层 ×4），与伤害类同口径。"""
        drunk = self.honey_drinks.get(str(self.depth), 0)
        cap = 12 if self.insight_active("蜜脉") else 6
        heal = portent_scaled_amount(1, self._portent_scale_depth())
        debt = self.portent_debt.get("__honey__", 0.0) + amount
        while debt >= 2 and drunk < cap and self.lucidity < self.max_lucidity:
            debt -= 2
            drunk += 1
            self.restore_resource('lucidity', heal)
            self.messages.append(tr("蜂蜜裹住伤口，清醒度回暖了一分。"))
        self.honey_drinks[str(self.depth)] = drunk
        self.portent_debt["__honey__"] = debt if (drunk < cap and self.lucidity < self.max_lucidity) else 0.0

    def _lead_shield(self, holder, x: int, y: int) -> None:
        """铅板：邻格屏蔽辐射病（移除并阻止结算）。"""
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < self.width and 0 <= ny < self.height and self.cell(nx, ny).wall_kind == "铅板":
                if holder.portents.get("irradiated", 0) > 0:
                    self._remember_portent_end(holder, "irradiated")
                return

    def _clear_sleep_portents(self, holder, x: int, y: int) -> None:
        """清醒石：相邻格上的单位被清除醉意/麻痹/迟钝/深眠/遮蔽类征兆。"""
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < self.width and 0 <= ny < self.height and self.cell(nx, ny).wall_kind == "清醒石":
                for portent_id in list(holder.portents):
                    if portent_id in self.CLARITY_SUPPRESSED:
                        self._remember_portent_end(holder, portent_id)
                return

    def _cell_too_narrow_for_enlarged(self, x: int, y: int) -> bool:
        """「放大」无法通过的格子：门，以及 1 格宽的缝隙（对边都是墙）。"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True
        if self.cell(x, y).wall_kind in DOOR_KINDS:
            return True
        solid_left = x > 0 and self.cell(x - 1, y).solid
        solid_right = x < self.width - 1 and self.cell(x + 1, y).solid
        solid_up = y > 0 and self.cell(x, y - 1).solid
        solid_down = y < self.height - 1 and self.cell(x, y + 1).solid
        return (solid_left and solid_right) or (solid_up and solid_down)

    @property
    def mind_loss_blocked(self) -> bool:
        """「环境心智免疫」（镇静）：拦截**环境来源**的心智减少——毒气、腐蚀、
        下潜反噬、燃烧等一切非战斗来源。

        2026-10-07 分级（玩家定稿）：异象造成的**战斗创伤**不再被这条拦截
        （ _lose_mind 的 combat 口径）；要减免战斗创伤用「忘忧」的倍率通道
        （见 mind_loss_multiplier）。⚠️ 判定读定义字段，加新征兆不必回来动这里。
        """
        return any(
            (definition := portent_def(portent_id)) is not None and definition.blocks_mind_loss
            for portent_id in self.portents
        )

    @property
    def mind_loss_multiplier(self) -> float:
        """「心智流失减免」倍率（忘忧 = 0.5）：对**一切**来源生效，含战斗创伤。

        多个减免征兆并存时取最小倍率；没有任何减免时返回 1.0。
        """
        factors = [
            definition.mind_loss_factor
            for portent_id in self.portents
            if (definition := portent_def(portent_id)) is not None and definition.mind_loss_factor < 1.0
        ]
        return min(factors) if factors else 1.0

    def _portent_scale_depth(self) -> int:
        """征兆深度函数的取值层：梦中梦取**进入时的主层数**（玩家定稿），
        其余取当前层。梦中梦全程 self.depth 不变（=主层数），这里显式走
        entry_depth 以免将来 depth 口径变动时 silently 偏离定稿。"""
        return self.entry_depth if self.realm_id else self.depth

    def _lose_mind(self, amount: int, *, combat: bool = False, source_id: str = '') -> int:
        """扣除心智的统一入口；返回实际扣除量。

        - ``combat=False``（默认，环境来源）：镇静期间心智不减；
        - ``combat=True``（异象战斗创伤）：镇静**不再**拦截（2026-10-07 分级），
          但忘忧的减免倍率对两种来源都生效。
        """
        from .settlement import (
            REASON_COMBAT, REASON_ENVIRONMENT, record_settled_value,
        )
        requested = float(amount)
        reason = REASON_COMBAT if combat else REASON_ENVIRONMENT
        if amount <= 0:
            return 0
        if getattr(self,'stasis_turns',0)>0:
            record_settled_value(self,'mind',requested=requested,before=self.mind,after=self.mind,
                                reason=reason,source=source_id,blocked='stasis')
            return 0
        # 开局选项「意识强度/坚韧自我」：只缩放战斗创伤（combat=True），
        # 环境来源（combat=False）保持原口径——意识强度对抗的是异象，不是梦境本身。
        if combat:
            resilience = self._player_resilience()
            if resilience != 1.0:
                amount = max(0, int(amount * resilience + 0.5))
        if not combat and self.mind_loss_blocked:
            record_settled_value(
                self, "mind", requested=requested, before=self.mind, after=self.mind,
                reason=reason, source=source_id, blocked="mind_loss_blocked",
            )
            return 0
        if getattr(self, "debug_mind_invincible", False):
            record_settled_value(
                self, "mind", requested=requested, before=self.mind, after=self.mind,
                reason=reason, source=source_id, blocked="debug_invincible",
            )
            return 0
        factor = self.mind_loss_multiplier
        if factor < 1.0:
            amount = max(0, int(amount * factor + 0.5))  # 忘忧：心智流失减半（四舍五入）
        if "enlarged" in self.portents:
            amount = amount - amount // 2  # 「放大」：受到的心智创伤减半
        # 心智守护（mind_guard，2026-10-22 实装：未完成的批注）：在征兆倍率之后、
        # 缓冲片之前按效力抵扣，但一次创伤至少仍损失 1 点——不做完全免疫。
        guard = self._effect_power("mind_guard")
        if guard > 0 and amount > 0:
            amount = max(1, amount - guard)
        # 联想盘·缓冲片：只抵扣下一次创伤，不恢复已损失的心智，不叠成无限盾。
        # 对应创伤被旧防御减到 0 时不消耗缓冲（§5.5）。
        if amount > 0:
            from ..equipment.events import consume_buffer

            amount = max(0, amount - consume_buffer(self, "mind"))
            if amount <= 0:
                record_settled_value(
                    self, "mind", requested=requested, before=self.mind,
                    after=self.mind, reason=reason, source=source_id,
                    blocked="buffer",
                )
                return 0
        amount = self._consume_hospital_buffer(amount, 'mind')
        amount = self.consume_hospital_equipment_buffer(amount)
        tier_before = self.mind_tier
        before = self.mind
        if amount <= 0:
            record_settled_value(
                self, "mind", requested=requested, before=before, after=before,
                reason=reason, source=source_id, blocked="buffered",
            )
            return 0
        from .settlement import write_resource
        write_resource(self, "mind", max(0, before - amount))
        lost = before - self.mind
        record_settled_value(
            self, "mind", requested=requested, before=before, after=self.mind,
            reason=reason, source=source_id,
        )
        if lost > 0:
            # 受击端（联想盘根事件）：结算后仍大于 0 的创伤才发事件；全免疫不触发。
            self._note_board_hurt("mind", lost, source_id=source_id)
            # 2026-10-15 混乱化改造：跌档横幅——状态越低，梦境越失控，看得见。
            self._announce_tier_drop("mind", tier_before)
        return lost

    def _tick_tear_warm(self, amount: int) -> None:
        """泪滴溶液的回暖：每回合恢复 1×深度档位 点心智，每层上限 5（沿用 tear_drinks 记账）。

        2026-10-07：恢复量按深度函数缩放，与伤害类同口径。"""
        drunk = self.tear_drinks.get(str(self.depth), 0)
        heal = portent_scaled_amount(1, self._portent_scale_depth())
        debt = self.portent_debt.get("tear_warm", 0.0) + amount
        while debt >= 1 and drunk < 5 and self.mind < self.max_mind:
            debt -= 1
            drunk += 1
            self.restore_resource('mind', heal)
            self.messages.append(tr("泪滴溶液让你的心智回暖了一分。"))
        self.tear_drinks[str(self.depth)] = drunk
        # 到达本层上限或心智已满时清空欠账，避免离开液体后一次性补发。
        self.portent_debt["tear_warm"] = debt if (drunk < 5 and self.mind < self.max_mind) else 0.0

    # 「清朗」（清醒香气）与「咖啡因」免疫的状态类征兆。
    CLARITY_SUPPRESSED = ("drunk", "numb", "sedated", "deep_sleep", "obscured", "poppy", "melatonin")
    CAFFEINE_SUPPRESSED = ("deep_sleep", "drunk")

    def _suppressed_portent_ids(self) -> set:
        """当前因免疫（清朗/咖啡因/洞察/记忆碎片）而暂时失效的征兆 id。"""
        suppressed = set()
        if getattr(self,'stasis_turns',0)>0:
            return set(self.portents)
        if "clarity" in self.portents:
            suppressed.update(self.CLARITY_SUPPRESSED)
        if "caffeinated" in self.portents:
            suppressed.update(self.CAFFEINE_SUPPRESSED)
        # Learned recovery rules are performed by waiting, rather than
        # permanently disabling these portents.
        if self._effect_power("fire_ward") > 0:
            suppressed.add("burning")
        # 记忆碎片带来的免疫：与洞察共用同一条通道，只是效果可以随时拆下来。
        suppressed.update(self.memory_immune_portents())
        return suppressed & set(self.portents)

    def _vision_profile(self, holder: Entity | None = None) -> VisionProfile:
        """按 docs 261022 §14.1 的分类口径汇总征兆的普通视觉修正。

        正面平加走同一通道登记；平减按 `vision_family` 同族取最大（未登记族名的
        以征兆 id 自成一族），不同族相加；比例缩视跨族取最小倍率，不会与另一条
        比例相乘至近零；`blinds` 不进倍率，而是在最后把普通视觉覆盖为 0。
        同一条效果只读 `vision` 或 `vision_ratio` 之一，因此不会既算 −n 又算倍率。
        耐受（清朗一类免疫、记忆碎片系数）在进通道前生效：平减按系数缩小，
        比例按系数朝 1.0 收敛。
        """
        if holder is None:
            holder = self.player
        for_player = holder is self.player
        suppressed = self._suppressed_portent_ids() if for_player else set()
        positive = 0
        flat_families: dict[str, int] = {}
        ratio = 1.0
        blinds = False
        blur = 0
        blur_floor = 0
        for portent_id in holder.portents:
            definition = portent_def(portent_id)
            if definition is None or portent_id in suppressed:
                continue
            factor = self.memory_portent_factor(portent_id) if for_player else 1.0
            if definition.blinds:
                blinds = True
                continue
            if definition.vision_ratio != 1.0:
                scaled = 1.0 + (float(definition.vision_ratio) - 1.0) * max(0.0, float(factor))
                ratio = min(ratio, max(0.0, scaled))
                continue
            if not definition.vision:
                continue
            value = math.floor(definition.vision * factor)
            if definition.vision_floor:
                # 失焦：只有本项受「最多减到 floor」约束，交给视距结算处夹取。
                blur = min(blur, value)
                blur_floor = max(blur_floor, int(definition.vision_floor))
                continue
            if value > 0:
                positive += value
            elif value < 0:
                family = definition.vision_family or portent_id
                flat_families[family] = min(flat_families.get(family, 0), value)
        return VisionProfile(
            positive=positive, flat=sum(flat_families.values()), ratio=ratio,
            blinds=blinds, blur=blur, blur_floor=blur_floor)

    def _portent_vision_delta(self, holder: Entity | None = None) -> int:
        """平减与正面两道的合计（状态面板「征兆视野」一行的旧口径）。"""
        profile = self._vision_profile(holder)
        return profile.positive + profile.flat + profile.blur

    # ---- 无意识领域：区域墙体的贴近机制（梦魇岩/呜咽晶柱/蚀梦菌毯/悔恨之锚）----
    # 计数器是运行期状态：离开墙体即清零，不进存档。
    _REGION_PROXIMITY_WALLS = ("梦魇岩", "呜咽晶柱", "蚀梦菌毯", "悔恨之锚", "传真墙", "磁带墙",
                               "沉思铁幕")

    def _adjacent_region_walls(self) -> dict[str, int]:
        """四邻中各区域贴近墙的数量（键 = 墙种）。"""
        counts: dict[str, int] = {}
        px, py = self.player.x, self.player.y
        for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
            if 0 <= nx < self.width and 0 <= ny < self.height:
                cell = self.cell(nx, ny)
                if cell.solid and cell.wall_kind in self._REGION_PROXIMITY_WALLS:
                    counts[cell.wall_kind] = counts.get(cell.wall_kind, 0) + 1
        return counts

    def _tick_region_proximity(self, amount: int) -> None:
        """贴近类墙体结算：累计贴近回合并按墙种生效。

        2026-10-07 提速（核心循环审计 S4）：旧口径要「连续贴 >3 回合」才触发一次，
        实战中几乎不发生；改为**每 2 回合**贴邻结算一次，保持 1 点量级但可感知、会累积。

        - 梦魇岩：每贴邻 2 回合 → 获得「噩梦」3 回合（心智每 2 回合 −1）；
          持续贴近则到期后再触发，离开即清零计数（征兆按剩余回合自然衰减）。
        - 呜咽晶柱：每贴邻 2 回合想象力 −1。
        - 蚀梦菌毯：每贴邻 2 回合清醒 −1。
        """
        if getattr(self,'stasis_turns',0)>0:
            return
        counts = self._adjacent_region_walls()
        exposure = getattr(self, "_region_proximity_turns", None)
        if exposure is None:
            exposure = {}
            self._region_proximity_turns = exposure
        for wall_kind in self._REGION_PROXIMITY_WALLS:
            if wall_kind in counts:
                exposure[wall_kind] = exposure.get(wall_kind, 0.0) + amount
            else:
                exposure.pop(wall_kind, None)
        if counts.get("梦魇岩"):
            if (exposure.get("梦魇岩", 0.0) >= 2 and "nightmare" not in self.portents
                    and self._apply_direct_portent(self.player, "nightmare", 3)):
                exposure["梦魇岩"] = 0.0
        from .settlement import REASON_ENVIRONMENT, settle_delta
        if exposure.get("呜咽晶柱", 0.0) >= 2:
            settle_delta(self, 'imagination', -1,
                         reason=REASON_ENVIRONMENT, source='呜咽晶柱')
            exposure["呜咽晶柱"] -= 2
        if exposure.get("蚀梦菌毯", 0.0) >= 2:
            settle_delta(self, 'lucidity', -1,
                         reason=REASON_ENVIRONMENT, source='蚀梦菌毯')
            exposure["蚀梦菌毯"] -= 2
        if exposure.get("传真墙", 0.0) >= 2:
            exposure["传真墙"] = 0.0
            alerted = 0
            for other in self.enemies:
                if (other.relation == "失控意识" and other.integrity > 0
                        and other.alert_state == "未察觉"
                        and max(abs(other.x - self.player.x), abs(other.y - self.player.y)) <= 6):
                    other.alert_state = "追踪"
                    alerted += 1
            if alerted:
                self.messages.append(tr("垃圾传真嗡鸣作响——{n} 只异象循声锁定了你的位置。", n=alerted))
        if (exposure.get("磁带墙", 0.0) >= 2 and "rewind_lag" not in self.portents
                and self._apply_direct_portent(self.player, "rewind_lag", 2)):
            exposure["磁带墙"] = 0.0
            self.messages.append(tr("磁带倒卷的吱嘎声缠上你的脚步（移动额外耗时 +0.2）。"))

    # ---- 稀有魔法植物的贴近沾染（无意识领域）----
    # 植物码 → (征兆 id, 持续回合)。曼德拉草/贤者之苔/镜面兰走拔除收益，
    # 不在这里。
    PLANT_PROXIMITY_PORTENTS = {
        6: ("datura_sleep", 4),   # 曼陀罗
        7: ("styx_weight", 4),    # 冥河柳
        8: ("queen_night", 6),    # 夜皇后
        12: ("clarity", 6),       # 千梦铃兰：清朗（免疫控制类征兆）
    }

    def _tick_plant_proximity(self, amount: int) -> None:
        """四邻有魔法植物时沾染对应征兆（刷新剩余回合）。"""
        px, py = self.player.x, self.player.y
        for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            plant_code = self.cell(nx, ny).plant
            if plant_code in self.PLANT_PROXIMITY_PORTENTS:
                portent_id, duration = self.PLANT_PROXIMITY_PORTENTS[plant_code]
                self._apply_direct_portent(self.player, portent_id, duration)

    def _trample_plant_effect(self) -> None:
        """兼容旧调用点：按脚下的植物给玩家结算踩踏反应。"""
        self.apply_plant_trample(self.player, self.player.x, self.player.y)

    def _release_plant_material(self, x: int, y: int, name: str, amount: int) -> str:
        """在 (x, y) 释放少量气体或液体（按名字在两张定义表里查），返回释放物名。

        走 `_add_gas` / `_add_liquid` 两个既有入口：材料赋予征兆、扩散、消散全都
        交给材料管线，不在这里另写一套——所以「植物释放的毒气」与「地图上本来就
        有的毒气」对玩家与失控意识完全同源，谁站在里面谁中招。
        """
        if not name or amount <= 0:
            return ""
        cell = self.cells[y][x]
        if name in GAS_DEFINITIONS:
            self._add_gas(cell, name, amount)
            return name
        if name in LIQUID_DEFINITIONS:
            self._add_liquid(cell, name, amount)
            return name
        return ""

    def _grant_portent_direct(self, holder: Entity, portent_id: str) -> bool:
        """把征兆**直接**挂到某个生物身上（不经过材料接触那条通道）。

        材料通道有 `affects_creatures` 这道闸门（增益类默认不给异象），而
        「踩坏植物被它咬一口」这类针对性效果应当对任何踩上来的生物成立，
        所以走这里。时长取征兆定义自己的 duration（仅靠层数存在的取 1，
        与既有的镜面架势写法一致）。
        """
        if holder is self.player and getattr(self,'stasis_turns',0)>0:
            return False
        if holder is self.player and self._identity_immune(portent_id):
            return False
        if holder is self.player:
            from ..equipment.library import library_reject_control
            if library_reject_control(self, portent_id):
                return False
        definition = portent_def(portent_id)
        if definition is None:
            return False
        if self._portent_protected(holder, portent_id):
            return False
        base_duration = min(definition.duration or 1, PORTENT_DURATION_CAP)
        if holder is self.player:
            from .stats import resolve_stat
            base_duration = int(resolve_stat(
                self, "portent.effective_duration",
                {"portent": portent_id, "base": base_duration, "player": True}).value)
        holder.portents[portent_id] = max(
            holder.portents.get(portent_id, 0),
            self._hospital_initial_duration(holder, portent_id, base_duration),
        )
        holder.portent_debt[portent_id] = 0.0
        if definition.stacks > 0:
            holder.portent_stacks[portent_id] = min(definition.stacks, PORTENT_STACK_CAP)
        if definition.material:
            # 材料型征兆的直接授予（踩踏植物/陷阱诅咒）同样挂附着层——
            # 与材料管道口径一致，否则「直接挂上的反而不如踩上去黏」。
            if holder is self.player:
                from .stats import resolve_stat
                attach = int(resolve_stat(
                    self, "portent.effective_duration",
                    {"portent": portent_id, "base": ATTACH_PORTENT_ROUNDS,
                     "player": True}).value)
            else:
                attach = ATTACH_PORTENT_ROUNDS
            holder.portent_attach[portent_id] = attach
        else:
            attach = 0
        # Count-only entries (no natural duration) must not get an invented
        # timeout; they still use their existing count/stack mechanism.
        round_duration = base_duration if int(definition.duration or 0) > 0 else 0
        self._portent_round_started(holder, portent_id, definition, round_duration, attach)
        return True

    def apply_plant_trample(self, holder: Entity, x: int, y: int, code: int) -> None:
        """踩踏植物的反应：对**任何**踩上来的生物生效，玩家与失控意识一视同仁。

        踩坏一株植物，它该吐的东西就吐在踩踏者脚下：征兆直接挂给踩踏者，
        气体/液体放在他站的这一格（材料管线会自己给站在里面的人上征兆）。
        植物形变（高丛→低草）由 `state.trample_plant` 负责，这里只管反应。
        """
        if not code:
            return
        definition = plant_def_for(code)
        if definition.trample_portent:
            self._grant_portent_direct(holder, definition.trample_portent)
        if definition.trample_release:
            self._release_plant_material(x, y, definition.trample_release, definition.trample_amount)
        if definition.trample_noise:
            # §13.2 彩玻菌「踩碎清脆一响」：踩踏链原本只释放气体，没有真实声源。
            # 这里按定义补一次 R=n 脉冲；植物踩碎后已换码，同一格再踩不重复发声。
            self._sound_pulse(
                x, y, definition.trample_noise,
                category="environment", source=tr(str(definition.name)),
                announce=False,
                emitter=None if holder is self.player else holder)
        if definition.trample_lucidity:
            # 荆棘藤一类的「穿越刮擦」：玩家扣清醒度，失控意识扣等量完整度。
            if holder is self.player:
                from .settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(self, 'lucidity', -definition.trample_lucidity,
                             reason=REASON_ENVIRONMENT,
                             source=str(getattr(definition, 'name', '荆棘')))
                self.messages.append(tr("荆棘刮过手臂：清醒度 −{n}。", n=definition.trample_lucidity))
            else:
                holder.integrity = max(0, holder.integrity - definition.trample_lucidity)

    def uproot_plant_reward(self, x: int | None = None, y: int | None = None) -> str | None:
        """拔除稀有植物的收益（返回提示；普通植物返回 None）。

        2026-09-18 重做：此前是一串「心智 +5 / 清醒 +4」的硬编码 if 链，稀有植物
        和一瓶消耗品没区别。现在收益写在植物定义里（up* 字段），只允许三种形态：
        独特征兆 / 物品形式的消耗品 / 释放少量气体或液体；本函数只负责按数据结算
        并生成一句提示，加新植物不必回来改这里。

        ``x``/``y`` 可选：玩家亲手拔除时默认读脚下；地图篡改「拔除」会传入句子
        选中的格子，收益仍按同一份植物定义结算（不是另写一套）。
        """
        x = self.player.x if x is None else int(x)
        y = self.player.y if y is None else int(y)
        cell = self.cell(x, y)
        if not cell.plant:
            return None
        definition = plant_def_for(cell.plant)
        parts: list[str] = []
        if definition.uproot_portent:
            if self._grant_portent_direct(self.player, definition.uproot_portent):
                portent = portent_def(definition.uproot_portent)
                if portent is not None:
                    parts.append(tr("沾染「{name}」", name=tr(portent.name)))
        if definition.uproot_item:
            item = self._make_item(definition.uproot_item)
            if item.category == "记忆碎片":
                self._add_memory(item.definition_id)
            else:
                self._add_inventory_item(item)
            parts.append(tr("获得 {item}", item=tr(item.name)))
        if definition.uproot_release:
            released = self._release_plant_material(
                x, y, definition.uproot_release, definition.uproot_amount
            )
            if released:
                parts.append(tr("散出少量{name}", name=tr(released)))
        if not parts:
            return None
        return tr("{plant}：{rewards}。", plant=tr(definition.name), rewards="，".join(parts))

    def _region_move_penalty(self) -> float:
        """悔恨之锚贴近：移动额外耗时 +0.5（离开即消失）。"""
        counts = self._adjacent_region_walls()
        return 0.5 if counts.get("悔恨之锚") else 0.0

    def _region_sight_penalty(self) -> int:
        """无光绒墙贴近：视野 −1（叠加取一次，不按数量重复扣）。"""
        counts = self._adjacent_region_walls()
        return -1 if counts.get("无光绒墙") else 0

    def _portent_move_penalty(self) -> float:
        suppressed = self._suppressed_portent_ids()
        # 异象主动技能的软控制一族（迟拍/缝影/倦意）：单独求和并封顶 0.5
        # （调参规则「软控制总移步加值上限」），材料迟滞（纸浆等）不受此上限约束。
        medical_soft = frozenset(('hospital_ether_liquid', 'hospital_ether_gas', 'hospital_fibrin'))
        sk_soft_control = sum(
            portent_def(portent_id).move_time * self.memory_portent_factor(portent_id)
            for portent_id in self.portents
            if portent_def(portent_id) is not None and portent_id not in suppressed
            and portent_id in _SK_SOFT_CONTROL
        )
        sk_soft_control += max((portent_def(pid).move_time for pid in
            ('hospital_ether_liquid', 'hospital_ether_gas') if pid in self.portents and pid not in suppressed), default=0)
        if 'hospital_fibrin' in self.portents and 'hospital_fibrin' not in suppressed:
            sk_soft_control += .15
        total = sum(
            portent_def(portent_id).move_time * self.memory_portent_factor(portent_id)
            for portent_id in self.portents
            if portent_def(portent_id) is not None and portent_id not in suppressed
            and portent_id not in _SK_SOFT_CONTROL and portent_id not in medical_soft
        )
        # 记忆碎片「空转的间隙」：适应了粘稠环境——迟滞这条不再拖慢脚步。
        # 与洞察「液态亲和」同一条减免通道，只是碎片可以随时拆下来。
        if self.memory_adapts("viscous") and "sluggish" in self.portents and "sluggish" not in suppressed:
            sluggish = portent_def("sluggish")
            total -= sluggish.move_time if sluggish else 0.0
        return max(0.0, total) + min(0.5, max(0.0, sk_soft_control))

    def _portent_attack_penalty(self) -> float:
        suppressed = self._suppressed_portent_ids()
        return sum(
            portent_def(portent_id).attack_time * self.memory_portent_factor(portent_id)
            for portent_id in self.portents
            if portent_def(portent_id) is not None and portent_id not in suppressed
        )

    def _portent_extra_turn(self) -> int:
        suppressed = self._suppressed_portent_ids()
        return min(PORTENT_EXTRA_TURN_CAP, sum(
            portent_def(portent_id).extra_turn
            for portent_id in self.portents
            if portent_def(portent_id) is not None and portent_id not in suppressed
        ))

    def _extra_turn_sources(self) -> list[str]:
        """当前造成「额外沉眠」的征兆名（供提示语用，别写死某一个来源）。"""
        suppressed = self._suppressed_portent_ids()
        names: list[str] = []
        for portent_id in self.portents:
            definition = portent_def(portent_id)
            if definition is None or portent_id in suppressed or definition.extra_turn <= 0:
                continue
            names.append(definition.name)
        return names

    def _portent_reveals_anomalies(self, portent_id: str) -> bool:
        definition = portent_def(portent_id)
        return bool(
            definition is not None
            and definition.reveal_anomalies
            and portent_id not in self._suppressed_portent_ids()
        )

    @property
    def reveals_anomalies(self) -> bool:
        """诅咒灵视：视野外的失控意识也以轮廓显形（见 render_map）。"""
        return any(self._portent_reveals_anomalies(pid) for pid in self.portents)

    def _portent_sound_multiplier(self, ignore_echoing: bool = False, *,
                                  holder=None, category: str = "generic") -> float:
        holder = self.player if holder is None else holder
        multiplier = 1.0
        resonance = 1.0
        for portent_id in holder.portents:
            definition = portent_def(portent_id)
            if definition is None:
                continue
            factor = max(0, definition.sound_multiplier)
            if portent_id == "echoing":
                if ignore_echoing:
                    continue
                damping = self.memory_stat_bonus("echo_damping") if holder is self.player else 0
                factor = 1 + (factor - 1) * (1 - damping / 100)
            if portent_id in {"echoing", "echo_amplify", "whispering", "void_murmur"}:
                resonance = max(resonance, factor)
            else:
                multiplier *= factor
        if ("dead_silence" in holder.portents
                and category not in {"lure", "explosion"}):
            multiplier *= 0.7
        return multiplier * resonance

    def _spend_attack_time(self, base: float = 1.0, *, aptitude: str | None = None) -> None:
        """攻击的时间开销：叠加醉意等征兆的攻击惩罚（与移动共用欠账折半补收）。

        走 ATTACK 这一支：次数结算要能区分「打了一下」和「走了一步」。
        ``base`` 是武器的基础耗时（钉枪 2.0 慢射、音爆哨 0.5 速射；默认 1.0）。
        """
        if aptitude is not None:
            base = self._dream_action_time(base, aptitude)
        # 慢速放映机（掉帧光环）：半径 3 内你的攻击耗时 +0.2，离开即恢复。
        for enemy in self.enemies:
            if (enemy.integrity > 0 and enemy.trait == "slow_aura"
                    and max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 3):
                base += 0.2
                break
        penalty = self._portent_attack_penalty()
        if penalty > 0:
            self.viscous_debt += penalty
        if self.viscous_debt >= 1.0:
            self.viscous_debt -= 1.0
            self.messages.append(tr("发飘的手拖慢了这次出手。"))
            base = 2.0
        # 迅念指环：念头比手快——每 2 点效力把攻击的**基础耗时**压掉 0.2 回合。
        # 亚回合成本交给 _action_time 记进 round_debt，凑满 1 才真的推一格时钟，
        # 所以体感是「平均每 5 次攻击少花 1 回合」（等效 −0.2 回合 / 次），
        # 而不是每次出手都省一点。下限 0.2 是防「0 回合行动」绕过时间轴。
        # ⚠️ 旧实现把这笔账记反了（每 4 次攻击反而多结算 1 回合，比不装备更慢，
        # 与注释自称的 −0.2 相反），2026-09-17 修正。
        swift = self._effect_power("swift_strike")
        if swift > 0:
            # 2026-09-22 修复：线性折算——每 1 点效力把基础耗时压掉 0.1 回合
            #（停摆的节拍器 power 1 = −0.1，迅念指环 power 2 = −0.2，与描述
            # 一致）。旧实现要求 swift ≥2 才折算，而节拍器 power 1 永远不生效，
            # 「攻击耗时低于 1 回合」的攻速流整条失效——攻击恒为一击一回合。
            # 亚回合成本由 _action_time 记入 round_debt，攒满 1 才推进时钟：
            # 0.9 回合/击 = 十次攻击省出一整回合，多出来的出手是真的。
            base = max(0.2, base - 0.1 * swift)
        self._action_time(base, ActionKind.ATTACK)

    @staticmethod
    def _speed_scale(portents: dict[str, int]) -> float:
        """行动速度倍率（>1 = 更快）。2.0 即「加速 2 倍」，行动耗时减半。"""
        scale = 1.0
        fastest, slowest = PORTENT_STACK_SPEED_MAX, PORTENT_STACK_SPEED_MIN
        for portent_id in portents:
            definition = portent_def(portent_id)
            if definition is not None and definition.speed_multiplier > 0:
                scale *= definition.speed_multiplier
                fastest = max(fastest, definition.speed_multiplier)
                slowest = min(slowest, definition.speed_multiplier)
        # 限制叠加收益，保留单一征兆自身约定的倍率（含模组/探针）。
        return max(slowest, min(fastest, scale))
