"""战斗动作族：能力激活与结算/喷洒/发射/解锁开火/修墙。"""
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
from .. import ability_targeting
from ..vision import knowledge
from ...equipment.root_facts import root_action
from ..cast_fx import animate_ability, animate_consumable, animate_item_action
from ..constants import (
    ACTION_COUNT_LIMIT,
    PORTENT_DURATION_CAP,
    PROJECTILE_MAX_RANGE,
    ActionKind,
)
from ..content import ITEM_DEFINITIONS, PROJECTILE_DEFINITIONS
from ..entities import ActionResult, Entity, Item, WorldItem

# 换弹两步各自的声音半径（金属／机括声）：完成装填更响，中途上膛较轻。
# 洞察「听出填装间隙」报的就是这两个数——**唯一真源在这里**，别在别处再写一遍。
RELOAD_SOUND_RADIUS_STEP = 4
RELOAD_SOUND_RADIUS_DONE = 6


def _pierce_loan(state) -> int:
    """「压膛」借给下一发的穿透档数；没有借据就是 0。"""
    from .. import expansion_consumables
    try:
        return int(expansion_consumables.pierce_loan(state) or 0)
    except Exception:
        return 0


class CombatActionsMixin:
    """战斗动作族：能力激活与结算/喷洒/发射/解锁开火/修墙。"""

    def _ability_imagination_cost(self, ability_id: str, definition: dict) -> int:
        """主动构想的实付想象费用；「回响的储备」只减免诱引类构想（回响）。"""
        from ...equipment.expansion_runtime import adjust_construct_cost
        cost = adjust_construct_cost(
            self, ability_id, self._scaled_ability_cost(int(definition["cost"])))
        if ability_id == "echo_pulse":
            cost = max(1, cost - self.memory_stat_bonus("lure_cost"))
        return cost

    def _emit_construct_noise(self, ability_id: str, definition: dict) -> None:
        """成功展开构想的世界噪音；战斗/高费构想更响，已有专属声音的不重复。"""
        if ability_id in ("echo_pulse", "listen_realm"):
            return
        combat = definition.get("combat") or {}
        radius = int(combat.get("sound") or 0)
        if radius <= 0:
            radius = 4 + min(4, max(0, int(definition.get("cost", 0) or 0)) // 5)
        self._sound_pulse(self.player.x, self.player.y, max(3, min(12, radius)),
                          by_player=True, category="ability",
                          source=tr(definition["name"]), announce=False,
                          triggers_rewards=False)

    @root_action
    @animate_ability
    def activate_ability(self, ability_id: str, *, target=None, direction=None,
                         landing=None) -> ActionResult:
        """激活一条已习得的主动构想：扣想象力、进冷却、结算效果。

        §13：战斗构想在瞄准确认后把真实目标/方向一并提交；借位另带预选落点。
        其余构想忽略这些关键字，保持旧调用零改动。
        """
        definition = ABILITY_DEFINITIONS.get(ability_id)
        if definition is None:
            return ActionResult(False, tr("未知的构想。"))
        if ability_id not in self.abilities:
            return ActionResult(False, tr("你还没有习得这个构想。"))
        if self.ability_cooldowns.get(ability_id, 0) > 0:
            return ActionResult(False, tr("{name}仍在冷却（剩 {turns} 回合）。", name=tr(definition["name"]), turns=self.ability_cooldowns[ability_id]))
        if ability_id in self.redacted_abilities:
            return ActionResult(False, tr("「{name}」被墨迹涂黑了（剩 {turns} 回合）。", name=tr(definition["name"]), turns=self.redacted_abilities[ability_id]))
        if getattr(self, "stasis_turns", 0) > 0:
            return ActionResult(False, tr("凝滞把你钉在了原地（剩余 {n} 回合）。",
                                          n=self.stasis_turns))
        cost = self._ability_imagination_cost(ability_id, definition)
        if self.imagination < cost and not self._blank_pass_eligible(cost):
            return ActionResult(False, tr("想象力不足（需要 {cost}）。", cost=cost))
        # Multi-resource abilities must prove they can pay every component before
        # any cooldown, time or world change. The old nightmare_fuel path only
        # checked imagination (0), then clamped an unpaid lucidity cost to zero
        # and still granted the full reward.
        for resource, amount in dict(definition.get("resource_costs") or {}).items():
            if getattr(self, resource, 0) < int(amount):
                if resource == "lucidity":
                    return ActionResult(False, tr("清醒度不足（需要 {cost}）。", cost=int(amount)))
                return ActionResult(False, tr("资源不足（需要 {cost}）。", cost=int(amount)))
        from ...equipment.expansion_runtime import (
            after_construct, begin_construct, end_construct,
        )
        from ...equipment.remaining_gear import cast_allowed
        if not cast_allowed(self,ability_id):
            return ActionResult(False,tr("装订钳还固定着同类残留，暂时不能另铺。"))
        begin_construct(self, ability_id, target)
        try:
            effect = self._resolve_ability_effect(ability_id, target=target,
                                                  direction=direction, landing=landing)
            if effect is not None:
                after_construct(self, effect)
        finally:
            end_construct(self)
        if effect is not None:
            if self.blank_pass_pending:
                # 这条构想走了「不扣费」的早退分支（落点站不下等）：
                # 免单没真正用上，把本层那一次退回去。
                self.blank_pass_pending = False
                self.blank_pass_depth = -1
            if effect.changed:
                self._emit_construct_noise(ability_id, definition)
            return effect
        self._pay_ability_cost(cost)
        self.ability_cooldowns[ability_id] = self._scaled_ability_cooldown(int(definition["cooldown"]))
        self._action_time(1, ActionKind.USE)
        self._emit_construct_noise(ability_id, definition)
        message = tr("主动构想「{name}」展开了。", name=tr(definition["name"]))
        self.messages.append(message)
        return ActionResult(True, message, {"ability": ability_id})

    def _resolve_ability_effect(self, ability_id: str, *, target=None,
                                direction=None, landing=None) -> ActionResult | None:
        """构想的效果结算；返回 None 表示「无专属效果」交由通用结算。

        设计口径：**只有写在 description 里的明文使用条件才允许拒绝激活**。
        当前所有构想的描述都没有硬性前置条件（「相邻的可燃材料」「视野内的
        异象」等都是效果落点，不是使用门槛），因此这里一律走结算：命中就结算，
        没有命中就空放——想象力照扣、冷却照进，只给一句「没有效果」的提示。
        旧实现在 spark/repulse/blur 上直接返回失败，玩家明明付得起想象力却
        按不动（「主动构想无法使用」的根因），与描述的措辞也对不上。
        """
        if ability_id.startswith('library.') and ability_id != 'library.erase':
            from ..library_abilities import resolve
            return resolve(self, ability_id, target=target, direction=direction)
        if ability_id.startswith('expansion.'):
            # 扩展包目录的构想：效果由 catalog.json 的 effect.runtime 指名既有原语，
            # 结算门面在 core/expansion_abilities.py，不再往这条手写分支链里加 if。
            from ..expansion_abilities import resolve
            return resolve(self, ability_id, target=target, direction=direction)
        from ..combat_constructs import is_combat, release
        if is_combat(ability_id):
            effect = release(self, ability_id, target=target, direction=direction,
                             landing=landing)
            if effect is not None and effect.changed and self.vanish_turns > 0:
                # 匿踪：直接攻击型构想命中后结束；环境构想不结束。
                form = str((ABILITY_DEFINITIONS[ability_id].get('combat') or {}).get('form', ''))
                if form in ('melee', 'launch', 'throw'):
                    self.vanish_turns = 0
            return effect
        definition = ABILITY_DEFINITIONS[ability_id]
        cost = self._ability_imagination_cost(ability_id, definition)
        # §12 H2：选点类构想先做一次只读落点校验——不合法/取消一律零消耗。
        spec = ability_targeting.spec_for(ability_id)
        point = None
        if spec is not None and spec.form == 'point':
            point = ability_targeting.resolve_target(self, ability_id, target)
            if point is None:
                return ActionResult(False, tr('这个构想没有合法落点——本次不消耗。'))
        aim_direction = ability_targeting.default_direction(self, direction)

        def _spend() -> None:
            self._pay_ability_cost(cost)
            self.ability_cooldowns[ability_id] = self._scaled_ability_cooldown(int(definition["cooldown"]))
            self._action_time(1, ActionKind.USE)

        def _done(message: str) -> ActionResult:
            self.messages.append(message)
            # 构想端（联想盘根事件）：只有成功展开才发事件。
            self._note_board_conceive(ability_id)
            return ActionResult(True, message, {"ability": ability_id})

        from .. import construct_environments
        terrain_target = construct_environments.visible_target(self)
        if ability_id in ('wax_seal', 'conjure_wall', 'collapse', 'dissolve_wall'):
            tx, ty = construct_environments.visible_target(self)
            if not self.inside_board(tx, ty):
                return ActionResult(False, '')
            from ..tamper_protection import construction_reason, terrain_reason
            reason = (terrain_reason(self, tx, ty) if ability_id == 'dissolve_wall'
                      else construction_reason(self, tx, ty))
            if reason:
                return ActionResult(False, tr(reason))
            if ability_id == 'dissolve_wall':
                cell = self.cell(tx, ty)
                if not cell.solid:
                    return ActionResult(False, tr('相邻没有可以融蚀的墙。'))
                if cell.hardness > 6 or '致密聚合墙' in cell.wall_kind or cell.wall_kind == '梦魇岩':
                    return ActionResult(False, tr('{wall}太硬了——融蚀对它无效。', wall=tr(cell.wall_kind)))
        if ability_id in construct_environments.KINDS:
            prepared, error = construct_environments.prepare(self, ability_id)
            if error:
                return ActionResult(False, error)
            _spend()
            _, message = construct_environments.start(self, ability_id, prepared=prepared)
            return _done(message)

        if ability_id == "listen_realm":
            from ...data.perception import LISTEN_REALM_SELF_RADIUS, LISTEN_REALM_TURNS
            _spend()
            self.listen_realm_until = max(self.listen_realm_until,
                                          self.time + LISTEN_REALM_TURNS)
            self._sound_pulse(self.player.x, self.player.y,
                              LISTEN_REALM_SELF_RADIUS, category="ability",
                              source=tr("听界"), announce=False,
                              triggers_rewards=False)
            return _done(tr("听界展开：{turns} 回合内，传到你的声音会标出发声格。",
                            turns=LISTEN_REALM_TURNS))
        if ability_id == "frost_touch":
            _spend()
            frozen = 0
            for enemy in self.enemies:
                if (
                    enemy.relation == "失控意识" and enemy.integrity > 0
                    and max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 3
                ):
                    enemy.frozen_turns = max(enemy.frozen_turns, float(self._scaled_ability_power(3)))
                    frozen += 1
            return _done(tr("霜沿着脚蔓开：冻结了 {n} 个近旁的失控意识（{turns} 回合）。", n=frozen, turns=self._scaled_ability_power(3)))
        if ability_id == "smoke_veil":
            x, y = point
            _spend()
            center_amount = self._scaled_ability_power(30)
            side_amount = self._scaled_ability_power(15)
            placed = 0
            for (cx, cy), amount in (((x, y), center_amount), ((x + 1, y), side_amount),
                                     ((x - 1, y), side_amount),
                                     ((x, y + 1), side_amount), ((x, y - 1), side_amount)):
                if not self.inside_board(cx, cy) or self.cell(cx, cy).solid:
                    continue
                cell = self.cell(cx, cy)
                room = 100 - (cell.gas if cell.gas_kind == "黑烟" else 0)
                add = max(0, min(amount, room))
                if add:
                    self._add_gas(cell, "黑烟", add)
                    placed += add
            return _done(tr("烟幕在 ({x}, {y}) 及四邻铺开：共 {n} 点黑烟。", x=x, y=y, n=placed))
        if ability_id == "wide_develop":
            self.ability_turns['wide_develop'] = 6
            self._wide_develop_last = (self.player.x, self.player.y)
            _spend()
            radius = 8 + self.memory_stat_bonus("survey")
            developed = knowledge.record_terrain_snapshot(
                self, self.player.x, self.player.y, radius)
            return _done(tr("想象力泼进黑暗：记下半径 {r} 的地形（{n} 格新记录）。",
                            r=radius, n=developed))
        if ability_id == "farsight":
            self.ability_turns["farsight"] = self._scaled_ability_power(8)
            _spend()
            return _done(tr("望远构想展开了：视野 +4，持续 {turns} 回合。", turns=self._scaled_ability_power(8)))
        if ability_id == "slow_wave":
            x, y = point
            cells = construct_environments.slow_zone_cells(self, (x, y))
            _spend()
            construct_environments.replace_field(
                self, 'slow_zone', (x, y), (0, 0), cells=cells,
                remaining=construct_environments.SLOW_ZONE_TURNS)
            return _done(tr("迟缓的泥沼铺在 ({x}, {y}) 周围：半径 4，持续 6 回合。", x=x, y=y))
        if ability_id == "develop":
            x, y = point
            radius = 5 + self.memory_stat_bonus("survey")
            newly = knowledge.record_terrain_snapshot(self, x, y, radius)
            _spend()
            return _done(tr("冲印在 ({x}, {y}) 记下半径 {r} 的地形快照（{count} 格新记录）。",
                            x=x, y=y, r=radius, count=newly))
        if ability_id == "repulse":
            x, y = point
            plan = construct_environments.repulse_plan(self, (x, y))
            pushed = 0
            for enemy, tx, ty in plan:
                self._kill_full_reward = True
                enemy.integrity = max(
                    0, enemy.integrity - construct_environments.REPULSE_DAMAGE)
                enemy.x, enemy.y = tx, ty
                pushed += 1
                if enemy.integrity <= 0:
                    self._resolve_enemy(enemy)
                self._kill_full_reward = False
            _spend()
            if pushed:
                return _done(tr("推斥构想把 {count} 个失控意识推了出去。", count=pushed))
            return _done(tr("推斥构想推开了空气——落点 2 格内没有可以被推开的失控意识。"))
        if ability_id == "blur":
            blinded = 0
            for enemy in self.enemies:
                if enemy.integrity > 0 and self.is_visible(enemy.x, enemy.y):
                    if enemy.trait not in ("relentless", "author_pace"):
                        # 曝光＝强闪光：§14.1 逐来源映射为统一致盲征兆，走单轮
                        # 硬期限与结束保护，不再用 blind_turns 表达半视野。
                        self._apply_direct_portent(
                            enemy, "blinded", self._scaled_ability_power(3))
                    blinded += 1
            _spend()
            if blinded:
                return _done(tr("曝光构想让 {count} 个失控意识过曝失明。", count=blinded))
            return _done(tr("曝光构想亮了亮——视野内没有可以曝光的失控意识。"))
        if ability_id == "detonate":
            x, y = point
            # 预读已知接续材料：只作提示，不替玩家点燃任何最近的材料。
            chained = []
            for cx, cy in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (self.inside_board(cx, cy) and self.is_visible(cx, cy)
                        and self._cell_is_flammable(self.cell(cx, cy))):
                    chained.append((cx, cy))
            _spend()
            strength = self._scaled_ability_power(3) + self._effect_power("fire_affinity")
            self._ignite_cell(x, y, strength, by_player=True)
            message = tr("引爆构想的火星当场落在 ({x}, {y})。", x=x, y=y)
            if chained:
                message += tr("已知可接续：{cells}。", cells='、'.join(
                    f"({cx},{cy})" for cx, cy in chained[:3]))
            return _done(message)
        if ability_id == "firewall":
            # 面朝方向（self.facing）的垂直一排 5 格凭空燃起：火墙不依赖燃料，
            # 靠构想本身维持，随回合自然衰减。
            fx, fy = self.facing
            # 垂直方向：(-fy, fx)。
            px, py = -fy, fx
            cx, cy = self.player.x + fx, self.player.y + fy
            strength = self._scaled_ability_power(4) + self._effect_power("fire_affinity")
            lit = 0
            for offset in (-2, -1, 0, 1, 2):
                tx, ty = cx + px * offset, cy + py * offset
                if 1 <= tx < self.width - 1 and 1 <= ty < self.height - 1 and not self.cell(tx, ty).solid:
                    cell = self.cell(tx, ty)
                    self._set_flame(tx, ty, min(8, max(cell.flame, strength)))
                    self._ignition_owner.setdefault(self.layer_key(), set()).add((tx, ty))
                    lit += 1
            _spend()
            return _done(tr("火墙构想燃起了 {n} 格火墙。", n=lit))
        if ability_id == "flame_nova":
            _spend()
            radius = 3 + self._effect_power("blast_radius")
            self._kill_full_reward = True
            self._explode(self.player.x, self.player.y, radius,
                          self._scaled_ability_power(3), from_player=True)
            return _done(tr("烈焰新星在你周围炸开。"))

        # ---- 内容扩展包 v1：8 新构想 ----
        def _facing_tile() -> tuple[int, int]:
            return terrain_target

        if ability_id == "stasis":
            self.stasis_turns = 3
            _spend()
            return _done(tr("你把自己封进了三回合的凝滞里——时间在你体表结成壳。"))
        if ability_id == "vanish":
            _spend()
            self.vanish_turns = self._scaled_ability_power(6)
            # 不再无条件重置警戒：已有的目击/声源调查会照常继续。
            return _done(tr("你的轮廓融进了梦里：{turns} 回合内异象看不见你。",
                            turns=self._scaled_ability_power(6)))
        if ability_id == "flashback":
            _spend()
            history = getattr(self, "_position_history", [])
            target = history[-3] if len(history) >= 3 else None
            if target is None or self.cell(target[0], target[1]).solid or self.entity_at(*target):
                return _done(tr("三回合前的位置已经回不去了——那里现在站不下。"))
            self.player.x, self.player.y = target
            return _done(tr("记忆倒带——你回到了三回合前的位置。"))
        if ability_id == "kindle":
            _spend()
            x, y = _facing_tile()
            lit = 0
            for tx, ty in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= tx < self.width and 0 <= ty < self.height and not self.cell(tx, ty).solid:
                    self._ignite_cell(tx, ty, self._scaled_ability_power(2), by_player=True)
                    lit += 1
            if lit:
                return _done(tr("火种落成一片十字，{n} 格烧了起来。", n=lit))
            return _done(tr("那里没有可点燃的东西——火种熄在了指尖。"))
        if ability_id == "resonance":
            _spend()
            self.resonance_turns = self._scaled_ability_power(8)
            return _done(tr("携带意象与你同频共振：{turns} 回合内效果放大 1.5 倍。", turns=self._scaled_ability_power(8)))
        if ability_id == "nightmare_fuel":
            _spend()
            from ..settlement import REASON_ABILITY_COST, settle_delta
            settle_delta(self, 'lucidity', -5, reason=REASON_ABILITY_COST,
                         source='噩梦燃料')
            gain = round(self.max_imagination * 0.4)
            self.restore_resource('imagination', gain,source='ability:'+ability_id)
            return _done(tr("你撕开一道噩梦当燃料：清醒度 −5，想象力 +{n}。", n=gain))
        if ability_id == "short_circuit":
            if self.realm_id == "toy_memories":
                return ActionResult(False, tr("玩具回路有绝缘封签，请用机关本身解谜。"))
            x, y = point
            known = []
            node = self.circuit_node_at(x, y)
            for output in (getattr(node, 'outputs', ()) or ()):
                known.append(str(output))
            _spend()
            if self.force_circuit_node(x, y, by_player=True):
                pass
            elif self.cell(x, y).wall_kind in ("陷阱石台", "机关石台"):
                self.trigger_platform(x, y)
            else:
                self.emit_signal(x, y, source='player')
            message = tr("短路成功——{kind}被强制触发了。", kind=tr(self.cell(x, y).wall_kind))
            if known:
                message += tr("已知接收端：{names}。", names='、'.join(known[:3]))
            return _done(message)
        if ability_id == "rewire":
            if self.realm_id == "toy_memories":
                return ActionResult(False, tr("玩具回路有绝缘封签，请用机关本身解谜。"))
            from ...materials.logic import TRIGGER_KINDS, RECEIVER_KINDS
            try:
                sx, sy, rx, ry = (int(v) for v in point)
            except (TypeError, ValueError):
                return ActionResult(False, tr("接线需要分别选择触发源与接收端。"))
            source, receiver = (sx, sy), (rx, ry)
            if (self.cell(*source).wall_kind not in TRIGGER_KINDS
                    or self.cell(*receiver).wall_kind not in RECEIVER_KINDS
                    or not self.is_visible(*source) or not self.is_visible(*receiver)):
                return ActionResult(False, tr("接线端口不成立——本次不消耗。"))
            # 同板校验先做：不同板的两个端口不能提交，也不扣费。
            if bool(self.circuit_node_at(*source)) != bool(self.circuit_node_at(*receiver)):
                return ActionResult(False, tr("接线失败：两个端口不在同一块电路板上。"))
            _spend()
            if not self.rewire_circuit_nodes(source, receiver, by_player=True):
                if any(self.circuit_node_at(*p) for p in (source, receiver)):
                    return _done(tr("接线失败：两个端口不在同一块电路板上。"))
                self.link_logic_nodes([source, receiver])
            return _done(tr("你改接了一条电线：{source} 与 {receiver} 之间亮起了新的连线。",
                            source=source, receiver=receiver)
                         + self._verify_wire_and_shed_charge(source, receiver))

        # ---- 内容扩展包 v1：12 地形改造构想 ----
        if ability_id == "condense_dew":
            x, y = point
            plan = construct_environments.condense_plan(self, (x, y))
            _spend()
            total = 0
            for (cx, cy), amount in plan:
                self._add_liquid(self.cell(cx, cy),
                                 construct_environments.CONDENSE_KIND, amount)
                total += amount
            return _done(tr("水汽在 ({x}, {y}) 及四邻凝出：共 {n} 点水。", x=x, y=y, n=total))
        if ability_id == "sow_green":
            x, y = point
            plan = construct_environments.sow_green_plan(self, (x, y))
            _spend()
            planted_tall = planted_low = 0
            for cx, cy, code in plan:
                self.set_plant(cx, cy, code)
                if code == 2:
                    planted_tall += 1
                else:
                    planted_low += 1
            total = planted_tall + planted_low
            if not total:
                return _done(tr("这里种不下任何东西。"))
            return _done(tr("你播下一片植物（{n} 格：高丛 {tall}、低草 {low}）。",
                            n=total, tall=planted_tall, low=planted_low))
        if ability_id == "wax_seal":
            x, y = _facing_tile()
            if self.cell(x, y).solid:
                return _done(tr("那格已经是坚实的了。"))
            self.configure_wall(self.cell(x, y), "蜡化记忆墙")
            self._identity_mark_created_wall(x, y, 'wax_seal')
            _spend()
            return _done(tr("蜡在地面上一层层堆高——封成了一格蜡化记忆墙。"))
        if ability_id == "draw_liquid":
            x, y = point
            kind, plan = construct_environments.draw_liquid_plan(self, (x, y))
            if not plan:
                return ActionResult(False, tr("这里没有可以汲取的液体——本次不消耗。"))
            for (cx, cy), take in plan:
                cell = self.cell(cx, cy)
                cell.liquid -= take
                if cell.liquid <= 0:
                    cell.liquid = 0
                    cell.liquid_kind = ""
            _spend()
            self.restore_resource('imagination', 2,source='ability:'+ability_id)
            return _done(tr("你从相连的{kind}里汲取了 {n} 点（{cells} 格，想象力 +2）。",
                            kind=tr(kind), n=sum(take for _pos, take in plan),
                            cells=len(plan)))
        if ability_id == "ice_bridge":
            x, y = point
            kind, plan = construct_environments.ice_bridge_plan(
                self, (x, y), aim_direction)
            if not plan:
                return ActionResult(False, tr("沿这个方向没有可以冻结的液体——本次不消耗。"))
            for (tx, ty), take in plan:
                cell = self.cell(tx, ty)
                stock = dict(cell.phase_stock or dict(
                    form='ice', kind=kind, amount=0,
                    base_floor=cell.aggregate_variant or '普通聚合物'))
                stock['amount'] = int(stock.get('amount', 0)) + take
                cell.phase_stock = stock
                cell.aggregate_variant = "冰面"
                cell.liquid -= take
                if cell.liquid <= 0:
                    cell.liquid = 0
                    cell.liquid_kind = ""
            _spend()
            return _done(tr("液面沿方向冻出一条冰桥：{n} 格，转入冻层 {amount} 点。",
                            n=len(plan), amount=sum(take for _pos, take in plan)))
        if ability_id == "transpire":
            x, y = point
            kind, component = construct_environments.liquid_component(self, (x, y))
            from ...materials import liquid_def
            liquid = liquid_def(kind)
            gas = liquid.evaporation_gas
            if not gas or not component:
                return ActionResult(False, tr('这种液体没有可以蒸腾的产物。'))
            _spend()
            cells = sorted(component, key=lambda p: (
                abs(p[0] - x) + abs(p[1] - y), p[1], p[0]))
            field = construct_environments.replace_field(
                self, 'transpire_zone', (x, y), (0, 0), cells=cells,
                remaining=construct_environments.TRANSPIRE_TURNS - 1)
            field.update(liquid_kind=kind, gas=gas,
                         budget=construct_environments.TRANSPIRE_BUDGET,
                         ratio=max(1, int(liquid.evaporation_ratio or 1)))
            converted = construct_environments.transpire_zone_tick(self, field)
            return _done(tr("{kind}连通块开始蒸腾：{n} 格，持续 {turns} 回合（本次转换 {m} 点）。",
                            kind=tr(kind), n=len(cells),
                            turns=construct_environments.TRANSPIRE_TURNS, m=converted))
        if ability_id == "dissolve_wall":
            x, y = _facing_tile()
            cell = self.cell(x, y)
            if not cell.solid or cell.wall_kind in ("意识边界",):
                return _done(tr("相邻没有可以融蚀的墙。"))
            if cell.hardness > 6 or "致密聚合墙" in cell.wall_kind or cell.wall_kind == "梦魇岩":
                return _done(tr("{wall}太硬了——融蚀对它无效。", wall=tr(cell.wall_kind)))
            kind = cell.wall_kind
            self.destroy_wall(x, y, 'ability')
            _spend()
            return _done(tr("{wall}在想象里融成了一摊记忆。", wall=tr(kind)))
        if ability_id in ("raise_terrain", "sink_terrain"):
            # §15.3：`elevation` 存的是整数档位，隆起/陷落各 ±1 档；只有在算液面
            # 时才乘 ELEV_STEP。旧实现把换算系数当成一档的增量（一次改 25），
            # 又用「不为负」当全局闸门，于是陷落永远改不动 0 格却照样扣费报成功。
            step = construct_environments.ELEVATION_OPS[ability_id]
            legal, _blocked = construct_environments.elevation_area(self, terrain_target)
            if not legal:
                # 提交前拒绝：合法区域为空时不扣想象力、不进冷却、不推进时间。
                return ActionResult(False, tr(construct_environments.REFUSE_PINNED))
            _spend()
            for x, y in legal:
                self.cell(x, y).elevation += step
            verb = "抬升" if step > 0 else "压低"
            return _done(tr("地势被{verb}了一个档位（{n} 格）。", verb=verb, n=len(legal)))
        if ability_id == "collapse":
            x, y = point
            walls, debris = construct_environments.collapse_plan(
                self, (x, y), aim_direction)
            if not walls or not debris:
                return ActionResult(False, tr("这里没有可坍塌的墙源或碎屑落点——本次不消耗。"))
            # 先落碎屑再推进世界：敌方回合不能踩进即将被埋的格子。
            for wx, wy in walls:
                self.clear_wall(self.cell(wx, wy))
            for cx, cy in debris:
                self.configure_wall(self.cell(cx, cy), "碎屑堆")
            _spend()
            return _done(tr("两侧的墙向内坍落：{n} 处墙源塌成 {m} 格碎屑堆。",
                            n=len(walls), m=len(debris)))
        if ability_id == "conjure_wall":
            x, y = point
            candidates = construct_environments.conjure_wall_plan(
                self, (x, y), aim_direction)
            if not candidates:
                return ActionResult(False, tr("那几格腾不出空间来凝聚墙——本次不消耗。"))
            # 墙先成形，再让世界走过这一回合：敌方不能落进刚造好的墙体。
            for cx, cy in candidates:
                self.configure_wall(self.cell(cx, cy), "臆造聚合墙")
                self._identity_mark_created_wall(cx, cy, 'conjure_wall')
            _spend()
            return _done(tr("{n} 格臆造聚合墙凭空凝聚成形。", n=len(candidates)))
        if ability_id == "rewrite_corner":
            _spend()
            import random as _random
            from ...materials import wall_pool_for_depth
            from ...materials.plants import plant_kind

            fx, fy = _facing_tile()
            rng = _random.Random(self.seed ^ (self.time * 7919) ^ (fx * 31 + fy))
            rewritten = 0
            for y in range(max(1, fy - 3), min(self.height - 1, fy + 4)):
                for x in range(max(1, fx - 3), min(self.width - 1, fx + 4)):
                    if (x, y) in ((self.player.x, self.player.y),) or self.entity_at(x, y):
                        continue
                    if construct_environments.protected_geometry(self, x, y):
                        continue
                    cell = self.cell(x, y)
                    if rng.random() < 0.30:
                        pool = wall_pool_for_depth(self.depth, realm_id=self.realm_id)
                        kind = pool[rng.randrange(len(pool))][0] if pool else "压实聚合墙"
                        self.configure_wall(cell, kind)
                    else:
                        self.clear_wall(cell)
                        if rng.random() < 0.12 and not cell.liquid:
                            self.set_plant(x, y, plant_kind(rng.random(), realm_id=self.realm_id).code)
                    rewritten += 1
            precious = [(x, y) for y in range(self.height) for x in range(self.width)
                        if construct_environments.protected_geometry(self, x, y)]
            self._repair_connectivity(self.cells, self.player.x, self.player.y, precious=precious)
            return _done(tr("梦当场重写了这个角落——{n} 格换了模样。", n=rewritten))
        # ---- 内容扩展包 v2（2026-10-11）：10 条，全部复用既有结算原语 ----
        if ability_id == "ice_chain":
            targets = sorted(
                (e for e in self.enemies
                 if e.integrity > 0 and e.relation == "失控意识" and self.is_visible(e.x, e.y)),
                key=lambda e: max(abs(e.x - self.player.x), abs(e.y - self.player.y)),
            )[:5]
            _spend()
            for enemy in targets:
                enemy.frozen_turns = max(enemy.frozen_turns, float(self._scaled_ability_power(2)))
            return _done(tr("霜顺着视线蔓延：冻结了 {n} 个失控意识（2 回合）。", n=len(targets)))
        if ability_id == "static_arc":
            plan = construct_environments.static_arc_plan(self, point)
            if plan is None:
                return ActionResult(False, tr("落点既不是异象也不是导电介质——本次不消耗。"))
            _spend()
            if plan[0] == 'enemy':
                enemy = plan[1]
                self._kill_full_reward = True
                enemy.integrity = max(0, enemy.integrity - construct_environments.STATIC_ARC_DAMAGE)
                enemy.slow_turns = max(enemy.slow_turns,
                                       float(self._scaled_ability_power(construct_environments.STATIC_ARC_SLOW)))
                if enemy.integrity <= 0:
                    self._resolve_enemy(enemy)
                self._kill_full_reward = False
                return _done(tr("静电弧咬住了 {enemy}：3 点创伤，它的动作迟了下来。", enemy=tr(enemy.label)))
            zone = plan[1]
            self._charge_electric_field(zone, source='static_arc', origin=point)
            return _done(tr("电弧顺导电介质铺开：{n} 格被充能。", n=len(zone)))
        if ability_id == "ink_doodle":
            x, y = point
            plan = construct_environments.ink_doodle_plan(self, (x, y))
            _spend()
            for xx, yy in plan:
                self.cell(xx, yy).aggregate_variant = "书页地"
            return _done(tr("你把 {n} 格地板涂成了易燃的书页地。", n=len(plan)))
        if ability_id == "blink":
            nx, ny = point
            _spend()
            self.player.x, self.player.y = nx, ny
            self.invalidate_sight_radius()
            return _done(tr("梦没来得及拦你——你已站在 ({x}, {y})。", x=nx, y=ny))
        if ability_id == "moth_dust":
            x, y = point
            cells = [(cx, cy)
                     for cy in range(max(0, y - 3), min(self.height, y + 4))
                     for cx in range(max(0, x - 3), min(self.width, x + 4))
                     if max(abs(cx - x), abs(cy - y)) <= 3]
            _spend()
            field = construct_environments.replace_field(
                self, 'moth_zone', (x, y), (0, 0), cells=cells, remaining=4)
            forgotten = construct_environments.moth_zone_tick(self, field)
            return _done(tr("蛾粉在 ({x}, {y}) 散开：{n} 个失控意识忘了你在哪。",
                            x=x, y=y, n=forgotten))
        if ability_id == "deep_breath":
            _spend()
            gain = self._scaled_ability_power(6)
            self.restore_resource('lucidity', gain,source='ability:'+ability_id)
            return _done(tr("你在梦里做了一次真正的深呼吸（清醒 +{n}）。", n=gain))
        if ability_id == "calm_incense":
            _spend()
            from ...materials.portents import portent_def

            cleared = 0
            for pid in list(self.portents):
                definition = portent_def(pid)
                if definition is not None and definition.kind == "负面":
                    self._remember_portent_end(self.player, pid)
                    cleared += 1
            self._apply_direct_portent(self.player, "calmed", 3)
            return _done(tr(
                "安神香燃起来：{n} 个负面征兆散了，镇静托住你的念头（3 回合）。",
                n=cleared,
            ))
        if ability_id == "purge_wind":
            _spend()
            swept = 0
            # The description promises "all gas in sight"; use the real visible
            # set, not a guessed 12-cell square (farsight/occlusion change it).
            for x, y in self.visible_cells():
                cell = self.cell(x, y)
                if cell.gas > 0:
                    cell.gas = 0
                    cell.gas_kind = ""
                    swept += 1
            return _done(tr("一阵风穿过梦境：{n} 格的气体被一扫而空。", n=swept))
        if ability_id == "pixel_surge":
            targets = []
            for x, y in self.visible_cells():
                kind = self.cell(x, y).wall_kind
                if kind in _MILLENNIUM_DISMANTLABLE_WALLS:
                    targets.append((x, y, kind))
            targets.sort(key=lambda t: max(abs(t[0] - self.player.x), abs(t[1] - self.player.y)))
            _spend()
            if not targets:
                return _done(tr("视野里没有可以拆成色块的千禧园墙。"))
            x, y, kind = targets[0]
            self.clear_wall(self.cell(x, y))
            self.restore_resource('imagination', 8,source='ability:'+ability_id)
            return _done(tr(
                "{kind}哗啦一声拆成色块（想象力 +8）。",
                kind=tr(kind),
            ))
        if ability_id == "mute_protocol":
            self.ability_turns["mute_protocol"] = self._scaled_ability_power(10)
            _spend()
            return _done(tr(
                "静默协议上线：{turns} 回合内你的脚步与普通道具基础声径封顶 1。",
                turns=self._scaled_ability_power(10),
            ))
        return None

    def confirm_gate_offering(self, scene_uid: str, selected: list[int]) -> ActionResult:
        """§8 S23 青灯入口：面板选定三件祭品后结算——门从「等待支付」转「开启」。

        与 ``world.scenes.operate`` 同口径：任何一步不成立就整笔退回（不吞物品、不扣
        回合）。嵌镜那一步免费；真正的代价（灯塔透镜＋恰好三件易逝物／摄入物＋一个
        行动）落在这里。门态由设施记录的 ``flags`` 派生，随存档与远层重建保持不变。
        """
        from ...world.scenes import GATE_GIFT_CATEGORIES

        record = self.world_ledger.facilities.get(scene_uid)
        if record is None or record.layer_key != self.layer_key():
            return ActionResult(False, tr("那处门已经不在这一层了。"))
        if record.flags.get("paid"):
            return ActionResult(False, tr("通道已经开着了。"))
        valid = sorted({int(index) for index in selected
                        if 0 <= int(index) < len(self.inventory)
                        and self.inventory[int(index)].category in GATE_GIFT_CATEGORIES})
        if len(valid) != 3:
            return ActionResult(False, tr("祭品必须是恰好三件易逝物或摄入物。"))
        if not any(item.definition_id == "lighthouse_lens" for item in self.inventory):
            return ActionResult(False, tr("行囊里没有灯塔透镜。"))
        for index in reversed(valid):
            self.inventory.pop(index)
        lens_index = next(index for index, item in enumerate(self.inventory)
                          if item.definition_id == "lighthouse_lens")
        self.inventory.pop(lens_index)
        record.flags.pop("offered", None)
        record.flags["paid"] = True
        record.state = "开启"
        from ...world import facts
        from ...world.relations import player_uid
        from ...world import scenes as world_scenes

        definition = world_scenes.definition_of(record) or {}
        facts.record(self, "facility", actor_uid=player_uid(self), target_uid=record.scene_uid,
                     position=record.cell(definition.get("anchor") or ""), owner_uid=record.scene_uid,
                     cause_uid=f"{record.definition_id}#offering", source_kind="scene",
                     before="等待支付", after="开启", amount=len(valid) + 1)
        world_scenes.emit_gate_paid(self, record, gifts=len(valid) + 1)
        message = tr("青灯吞下透镜与三件祭品——石台中央裂开了一道门。")
        self.messages.append(message)
        self._action_time(1, ActionKind.USE)
        return ActionResult(True, message, {"lens_paid": scene_uid, "state": record.state})

    def _learn_random_ability(self, pool_id: str = 'general') -> str | None:
        """习得一条未习得的随机构想；全部习得后返回 None。

        §13：残页把新战斗构想的总权重压到 20%（旧通用池 80%），组内按
        基础战斗/进阶战术/较稀有环境的 3／2／1 权重抽取；空组自动回退。
        """
        from ..item_access import ability_learnable
        unlearned = [ability_id for ability_id, definition in ABILITY_DEFINITIONS.items()
                     if ability_id not in self.abilities and definition.get('acquire_pool','general') == pool_id
                     # 扩展包条目带 min_depth：深层构想不会在浅层的残页里冒出来。
                     and ability_learnable(self, ability_id)]
        if not unlearned:
            return None
        rng = random.Random(self.seed ^ (self.time * 613) ^ len(self.abilities))
        if pool_id == 'general':
            new = [key for key in unlearned if ABILITY_DEFINITIONS[key].get('combat')]
            old = [key for key in unlearned if not ABILITY_DEFINITIONS[key].get('combat')]
            if new and (not old or rng.random() < 0.2):
                weights = [max(1, int(ABILITY_DEFINITIONS[key]['combat'].get('weight', 1)))
                           for key in new]
                ability_id = rng.choices(new, weights=weights, k=1)[0]
            elif old:
                ability_id = rng.choice(old)
            else:
                ability_id = rng.choice(new)
        else:
            ability_id = rng.choice(unlearned)
        self.abilities.append(ability_id)
        return ability_id

    def _repair_adjacent_wall(self, amount: int) -> bool:
        for x, y in ((self.player.x + 1, self.player.y), (self.player.x - 1, self.player.y), (self.player.x, self.player.y + 1), (self.player.x, self.player.y - 1)):
            if self._repair_wall_at(x,y,amount):
                return True
        return False

    def _repair_wall_at(self,x: int,y: int,amount: int,*,repair_power=None) -> bool:
        if not self.inside_board(x,y) or abs(x-self.player.x)+abs(y-self.player.y) != 1:
            return False
        cell = self.cell(x,y)
        if not cell.solid or cell.wall_kind == '意识边界':
            return False
        maximum = wall_def(cell.wall_kind).integrity
        if cell.integrity >= maximum:
            return False
        amount += self._effect_power('repair_up') if repair_power is None else repair_power
        cell.integrity = min(maximum,cell.integrity+amount)
        self.messages.append(tr('修缮了相邻的{wall}（完整度 {value}/{maximum}）。',
                                wall=tr(cell.wall_kind),value=cell.integrity,maximum=maximum))
        return True

    def _find_adjacent_flammable(self) -> tuple[int, int] | None:
        for x, y in ((self.player.x + 1, self.player.y), (self.player.x - 1, self.player.y), (self.player.x, self.player.y + 1), (self.player.x, self.player.y - 1)):
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            cell = self.cell(x, y)
            if cell.solid:
                continue
            if self._cell_is_flammable(cell):
                return x, y
        return None

    THROW_MAX_RANGE = 6
    # ---- 远程武器：喷射（喷水枪/吹风机）与一次性发射物（2026-09-19）----

    def _spray_cost_ok(self) -> ActionResult | None:
        if self.imagination < 2:
            return ActionResult(False, tr("想象力不足（喷射需要 2 点）。"))
        return None

    @root_action
    def spray_fire(self, source_index: int, dx: int, dy: int, *, choice=None) -> ActionResult:
        """喷射（定向）：沿直线弹道泼出液态记忆/弥散印象。"""
        from .. import weapons as weapons_mod

        if max(abs(dx), abs(dy)) != 1:
            return ActionResult(False, tr("喷射方向无效。"))
        from ...equipment import gear_tools
        if gear_tools.suit_sealed(self):
            return ActionResult(False, tr("工作服的外层还封着——先解开再喷射。"))
        cost = self._spray_cost_ok()
        if cost is not None:
            return cost
        src_index = source_index if source_index >= 0 else None
        plan = weapons_mod.spray_plan(self, src_index, choice=choice)
        if not plan.valid:
            if plan.material_source_id:
                return ActionResult(False, tr(plan.reason))
            return self._fire_choice_result(plan)
        self.facing = (dx, dy)
        message, extra = weapons_mod.spray_fire(self, src_index, dx, dy, plan=plan)
        if not extra:
            return ActionResult(False, message)
        self._action_time(self._dream_action_time(1, 'materials'), ActionKind.USE)
        self.messages.append(message)
        return ActionResult(True, message, extra)

    @root_action
    def spray_target(self, source_index: int, tx: int, ty: int, *, choice=None) -> ActionResult:
        """喷射（瞄准）：沿「玩家 → 目标」直线泼出。"""
        from .. import weapons as weapons_mod

        if not self.inside_board(tx, ty) or (tx, ty) == (self.player.x, self.player.y):
            return ActionResult(False, tr("喷射方向无效。"))
        from ...equipment import gear_tools
        if gear_tools.suit_sealed(self):
            return ActionResult(False, tr("工作服的外层还封着——先解开再喷射。"))
        cost = self._spray_cost_ok()
        if cost is not None:
            return cost
        src_index = source_index if source_index >= 0 else None
        plan = weapons_mod.spray_plan(self, src_index, choice=choice,
                                     target=self.entity_at(tx,ty), cell=(tx,ty))
        if not plan.valid:
            if plan.material_source_id:
                return ActionResult(False, tr(plan.reason))
            return self._fire_choice_result(plan)
        message, extra = weapons_mod.spray_target(self, src_index, tx, ty, plan=plan)
        if not extra:
            return ActionResult(False, message)
        self._action_time(self._dream_action_time(1, 'materials'), ActionKind.USE)
        self.messages.append(message)
        return ActionResult(True, message, extra)

    @root_action
    def fire_once(self, index: int, dx: int, dy: int) -> ActionResult:
        """一次性发射物：沿直线弹道射出，命中/撞墙即燃，物品消耗。"""
        from .. import weapons as weapons_mod

        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        if max(abs(dx), abs(dy)) != 1:
            return ActionResult(False, tr("发射方向无效。"))
        item = self._detach_one_for_action(index)
        self.facing = (dx, dy)
        origin = (self.player.x, self.player.y)
        from ..ballistics import trace_path

        path = list(trace_path(self.player.x, self.player.y, dx, dy))
        self._action_time(self._dream_action_time(1, 'shooting'), ActionKind.USE)
        self._sound_pulse(self.player.x, self.player.y, 6, by_player=True,
                          category="projectile", source=tr("发射"), announce=False,
                          triggers_rewards=False)
        message, extra = weapons_mod.fire_once_resolve(self, item, path)
        self._capture_fire_once(item, path, extra, origin=origin)
        self.messages.append(message)
        return ActionResult(True, message, extra)

    def _capture_fire_once(self, item, path: list[tuple[int, int]], extra: dict[str, Any], *, origin=None) -> None:
        """一次性发射物的弹道动画：飞行到冲击点为止，收尾按落点一闪。"""
        from .. import weapons as weapons_mod
        impact = extra.get("position")
        cells: list[tuple[int, int]] = []
        for px, py in path:
            cells.append((px, py))
            if impact and (px, py) == tuple(impact):
                break
        self._note_projectile(
            cells, [], kind="throw", color=item.color or "#ffd166",
            end="land", end_cell=tuple(impact) if impact else None, origin=origin,
        )
        from ..cast_fx import emit_cast
        from ...data.cast_fx import ITEM_EFFECT_FX
        center = tuple(impact) if impact else cells[-1] if cells else origin or (self.player.x, self.player.y)
        # 电弧弹的收尾演出走电（needle/electric），不能和光焰弹一样闪一片火。
        effect = ('shock' if weapons_mod.fire_once_payload(item) == 'arc' else 'fire_once')
        emit_cast(self, ITEM_EFFECT_FX[effect], 'item:'+item.definition_id,
                  origin or (self.player.x, self.player.y), [center], center=center, projectile=True)

    @root_action
    def fire_once_target(self, index: int, tx: int, ty: int) -> ActionResult:
        """一次性发射物（瞄准）：沿「玩家 → 目标」直线射出。"""
        from .. import weapons as weapons_mod
        from ..ballistics import PROJECTILE_MAX_RANGE

        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        if (not (0 <= tx < self.width and 0 <= ty < self.height)
                or (tx, ty) == (self.player.x, self.player.y)
                or max(abs(tx-self.player.x), abs(ty-self.player.y)) > PROJECTILE_MAX_RANGE):
            return ActionResult(False, tr("发射方向无效。"))
        item = self._detach_one_for_action(index)
        self.facing = (
            (tx > self.player.x) - (tx < self.player.x),
            (ty > self.player.y) - (ty < self.player.y),
        )
        self._sound_pulse(self.player.x, self.player.y, 6, by_player=True,
                          category="projectile", source=tr("发射"), announce=False,
                          triggers_rewards=False)
        origin = (self.player.x, self.player.y)
        from ..throwing import flight_path

        path = flight_path(origin, (tx, ty))
        self._action_time(self._dream_action_time(1, 'shooting'), ActionKind.USE)
        message, extra = weapons_mod.fire_once_resolve(self, item, path)
        self._capture_fire_once(item, path, extra, origin=origin)
        self.messages.append(message)
        return ActionResult(True, message, extra)
    def _consume_equipment_magazine(self, action_plan):
        """Spend one round from every physical emitter the compiled action fires.

        The compiled plan names the emitting instances; the first source id is not
        a stand-in for them (modifiers and voices also live in ``source_ids``).
        Every emitter is validated before any round is taken so a combined
        sentence can never fire with a partially paid magazine.
        """
        if action_plan.innate:
            return None
        from ..firing_sources import ensure_magazine
        pending = []
        for source_id, shots in getattr(action_plan, 'emitters', ()):
            item = self.equipment._item(source_id)
            if item is None:
                return tr('选定的发射来源已经失效。')
            ensure_magazine(item)
            if getattr(item, 'magazine', None) is None:
                continue
            if item.magazine < shots:
                return tr('弹匣已空，请先换弹。')
            pending.append((item, shots))
        for item, shots in pending:
            item.magazine = max(0, item.magazine - shots)
            if item.magazine <= 0:
                self._note_emptied_by_fire(item.instance_id)
        return None

    def _consume_legacy_basic(self) -> bool:
        from ..firing_sources import legacy_basic_view, write_legacy_basic
        view = legacy_basic_view(self)
        if view is None or view.magazine <= 0:
            return False
        view.magazine -= 1
        write_legacy_basic(self, view)
        if view.magazine <= 0:
            from ..firing_sources import LEGACY_BASIC_ID
            self._note_emptied_by_fire(LEGACY_BASIC_ID)
        return True

    def _verify_wire_and_shed_charge(self, source, receiver) -> str:
        """不把亮灯当通电（``expansion.circuit.i03``）：近身断线验电后泄一层积电。

        只认**近身**（贴着一个端口）与**已见**（``rewire`` 本来就要求两个端口都可见）：
        隔空接线验不了电，不白给。泄的只是压电地板那本层数账（``shed_piezo_charge``），
        地板下一回合照常继续充电——这就是描述里「仍须实际断电，不因灯灭就安全」。
        返回追加的提示（没有生效时是空串）。
        """
        if not self.insight_active("不把亮灯当通电"):
            return ""
        px, py = self.player.x, self.player.y
        if not any(max(abs(int(x) - px), abs(int(y) - py)) <= 1
                   for x, y in (source, receiver)):
            return ""
        if self.shed_piezo_charge(self.player, 1) <= 0:
            return ""
        return tr("不把亮灯当通电：你就着这条线断了电、验了一下——身上泄掉一层积电，"
                  "灯亮不亮都不算断电。")

    def _note_emptied_by_fire(self, instance_id) -> None:
        """记下「这一仓是自己打空的」（洞察「数清空响」的凭据）。

        只在**开火**扣空时写，所以主动清仓／退弹不会触发——描述里写明了
        「退弹清仓不触发」。凭据按实例记，换弹第一步用掉即删。
        """
        features = getattr(self, 'realm_features', None)
        if isinstance(features, dict):
            features.setdefault('emptied_by_fire', {})[str(instance_id)] = int(self.time)

    def _take_fast_reload_step(self, instance_id) -> bool:
        """数清空响：这一仓是自己打空的 → 本回换弹的**第一步**多走一格进度。

        只改步进，不改费用：想象力照付（描述「原费用照付」）。
        """
        if not self.insight_active('数清空响'):
            return False
        features = getattr(self, 'realm_features', None)
        if not isinstance(features, dict):
            return False
        marks = features.get('emptied_by_fire')
        if not isinstance(marks, dict) or str(instance_id) not in marks:
            return False
        marks.pop(str(instance_id), None)
        return True

    def _reload_item(self, instance_id: str):
        for item in self.inventory:
            if getattr(item, 'instance_id', None) == str(instance_id):
                return item
        return None

    @root_action
    def reload_weapon_step(self, instance_id: str) -> ActionResult:
        """One real world-action step of a paid reload; never auto-fills."""
        from ..firing_sources import (LEGACY_BASIC_ID, ensure_magazine, legacy_basic_view,
                                      magazine_spec, reload_quote, write_legacy_basic)
        legacy = str(instance_id) == LEGACY_BASIC_ID
        item = legacy_basic_view(self) if legacy else self._reload_item(instance_id)
        if item is None:
            return ActionResult(False, tr('找不到要换弹的武器。'))
        if not legacy:
            ensure_magazine(item)
        quote = reload_quote(item)
        if quote is None:
            return ActionResult(False, tr('这件物品没有弹匣。'))
        if not quote.can_start:
            return ActionResult(False, tr(quote.reason or '现在不能换弹。'))
        if quote.cost and not item.reload_paid:
            if self.imagination < quote.cost:
                return ActionResult(False, tr('想象力不足，无法换弹。'))
        # 数清空响：只有「自己打空的那一仓、换弹的第一步」多走一格，费用照付。
        fast_step = self._take_fast_reload_step(instance_id)
        self._action_time(1, ActionKind.USE)
        if quote.cost and not item.reload_paid:
            from ..settlement import REASON_ABILITY_COST, settle_delta
            settle_delta(self, 'imagination', -quote.cost, reason=REASON_ABILITY_COST,
                         source='换弹')
            item.reload_paid = True
        item.reload_steps += 2 if fast_step else 1
        spec = magazine_spec(item.definition_id)
        completed = item.reload_steps >= spec.reload_time
        if completed:
            item.magazine = item.magazine_capacity or spec.capacity
            item.reload_steps = 0
            item.reload_paid = False
            message = tr('换弹完成：{name} 装填 {n} 发。', name=tr(item.name), n=item.magazine)
        else:
            message = tr('换弹中：{name} 还需 {n} 步。', name=tr(item.name),
                         n=spec.reload_time - item.reload_steps)
        # 换弹是金属/机括声：完成装填更响，中途上膛较轻。
        self._sound_pulse(self.player.x, self.player.y,
                          RELOAD_SOUND_RADIUS_DONE if completed else RELOAD_SOUND_RADIUS_STEP,
                          by_player=True, category="item",
                          source=tr("换弹"),
                          announce=False, triggers_rewards=False)
        if legacy:
            write_legacy_basic(self, item)
        self.messages.append(message)
        return ActionResult(True, message, {'reload_steps': item.reload_steps,
                                            'magazine': item.magazine})

    @root_action
    def fire_assisted(self, tx: int, ty: int, *, choice: str | None = None) -> ActionResult:
        """辅助瞄准发射（2026-09-19）：弹体沿「你 → 锁定目标」的直线飞行。

        逐格走线（Bresenham）：撞墙按穿透规则结算，撞上第一个失控意识
        即造成武器伤害。辅助锁定的目标不再要求与你同行/同列。
        """
        if (not self.inside_board(tx, ty) or (tx, ty) == (self.player.x, self.player.y)
                or max(abs(tx - self.player.x), abs(ty - self.player.y)) > 12):
            return ActionResult(False, tr("发射方向无效。"))
        action_plan = self.equipment.plan_action("fire", target=self.entity_at(tx, ty),
                                                 cell=(tx, ty), choice=choice)
        if not action_plan.valid:
            return self._fire_choice_result(action_plan, target=self.entity_at(tx, ty), cell=(tx, ty))
        spec = dict(action_plan.projectile_profile)
        self._emit_fire_noise(spec)
        if max(abs(tx-self.player.x), abs(ty-self.player.y)) > int(spec.get('range', 12)):
            return ActionResult(False, tr("发射方向无效。"))
        magazine_error = self._consume_equipment_magazine(action_plan)
        if magazine_error:
            return ActionResult(False, magazine_error)
        if choice == 'legacy_basic_fire':
            if not self._consume_legacy_basic():
                return ActionResult(False, tr('旧档继承的基础发射已经用完，请先换弹。'))
        elif action_plan.innate:
            self.projectile_charges -= 1
        self.facing = (
            (tx > self.player.x) - (tx < self.player.x),
            (ty > self.player.y) - (ty < self.player.y),
        )
        # 走线格子：从玩家相邻格到目标格（含目标）。
        path: list[tuple[int, int]] = []
        x, y = self.player.x, self.player.y
        while (x, y) != (tx, ty):
            if x != tx:
                x += 1 if tx > x else -1
            if y != ty:
                y += 1 if ty > y else -1
            path.append((x, y))
        hit = None
        blocked = False
        bounced = False
        repeat_phases = 0
        penetration = self._shot_penetration(action_plan, spec)
        end_kind, end_cell = "range", None
        from ..construct_environments import reflected_path
        path = reflected_path(self, (self.player.x, self.player.y), path)
        from ..combat_constructs import trim_path
        path = trim_path(self, path)
        for x, y in path:
            cell = self.cell(x, y)
            if cell.solid:
                from ..expansion_consumables import on_collision
                on_collision(self)
                if self.puzzle_projectile_blocked(x, y):
                    blocked = True
                    end_kind, end_cell = 'wall', (x, y)
                    path = path[:path.index((x, y))]
                    break
                if cell.wall_kind == "镜湖板":
                    # 镜湖板（扩展包 v1）：弹体被镜面反弹——弹道反向重走，
                    # 命中判定照常（可能打回来打到自己）。
                    path.reverse()
                    continue
                if wall_def(cell.wall_kind).projectile_immune:
                    # 玉米淀粉墙（2026-09-23）：免疫不变，反弹打回（每发 1 次）；
                    # 经济耗尽按原样吞掉。
                    if not bounced:
                        bounced = True
                        path.reverse()
                        continue
                    blocked = True
                    end_kind, end_cell = "wall", (x, y)
                    break
                resistance = max(1, cell.hardness * cell.thickness)
                passes = penetration >= resistance
                integrity_before = int(cell.integrity)
                cell.integrity = max(0, cell.integrity - (35 if passes else max(10, penetration * 20)))
                if cell.integrity == 0:
                    self.destroy_wall(x, y, "projectile", integrity_before=integrity_before)
                    self.messages.append(tr("辅助弹体击碎了一处坚实聚合物。"))
                if passes:
                    penetration -= resistance
                    continue
                blocked = True
                end_kind, end_cell = "wall", (x, y)
                self.messages.append(tr("辅助弹体撞上坚实聚合物。"))
                break
            entity = self.entity_at(x, y)
            if entity is self.player and (x, y) != path[0]:
                from ..memory_buffers import spend
                self._lose_mind(max(0, 1-spend(self,"mind:self_projectile")))
                hit = self.player
                end_kind, end_cell = 'entity', (x, y)
                path = path[:path.index((x, y))+1]
                break
            if entity and entity is not self.player:
                self._kill_full_reward = True
                repeat_phases = self._player_strike(entity, "ranged", damage=1, action_plan=action_plan,
                                                    repeat_path=path[:path.index((x,y))+1])
                self._apply_fire_payload(entity, spec, self.facing)
                if entity.integrity <= 0:
                    self._resolve_enemy(entity)
                hit = entity
                end_kind, end_cell = "entity", (x, y)
                break
        self._note_projectile(
            list(path), [], kind="shot", color="#ffe0b3",
            end=end_kind, end_cell=end_cell,
            repeat_delay=.12 if repeat_phases == 2 else 0.,
        )
        self._spend_attack_time(action_plan.base_time, aptitude="shooting")
        if hit is not None:
            self.tutorial_events["fired_hit"] = hit.id
            message = tr("辅助瞄准：弹体命中失控意识。")
        elif blocked:
            message = tr("辅助弹体被坚实聚合物挡下。")
        else:
            message = tr("辅助弹体飞出视野，消失在梦的深处。")
        self.messages.append(message)
        return ActionResult(True, message, {"assisted": True, "hit": hit.id if hit else None,
                                           'equipment_repeat_phases': repeat_phases})

    def _shot_penetration(self, action_plan, spec) -> int:
        """Both input paths spend the same native and sentence-local budget."""
        from ...equipment.runtime import action_effect_power
        item = self.equipment._item(action_plan.primary_source_id)
        template = PROJECTILE_DEFINITIONS.get(item.projectile_template if item else '直线弹体',
                                               PROJECTILE_DEFINITIONS['直线弹体'])
        return (template['penetration'] + (item.penetration if item else 0)
                + self.physics_modifiers()['penetration_bonus'] + int(spec.get('penetration', 0))
                + int(self.insight_active('机械迷恋'))
                # 「压膛」借来的那一档穿透：读数挂在本层装置表里，开火时领走。
                + action_effect_power(self, 'pierce_up', action_plan.rows)
                + _pierce_loan(self))

    def _fire_choice_result(self, action_plan, *, target=None, cell=None) -> ActionResult:
        if action_plan.requires_target:
            return ActionResult(False, tr(action_plan.reason))
        if action_plan.kind == 'spray':
            modes = sorted({mode for row in self.equipment.formation().actions
                            for mode in row.action_modes if mode.startswith('spray_')})
            choices = tuple(c for mode in modes for c in self.equipment.action_choices(mode, target=target, cell=cell))
        else:
            choices = self.equipment.action_choices(action_plan.kind, target=target, cell=cell)
        return ActionResult(False, tr(action_plan.reason), {
            "equipment_action_choices": [{"key": c.key, "kind": c.kind,
                "definition_ids": list(c.definition_ids)} for c in choices],
        })

    def _emit_fire_noise(self, spec) -> None:
        """每次成功发射都有枪口/机括噪音；重武器（带 pulse）更响。"""
        base = 5 + min(5, max(0, int(spec.get("pulse") or 0)) // 2)
        self._sound_pulse(self.player.x, self.player.y, base, by_player=True,
                          category="projectile", source=tr("发射"),
                          announce=False, triggers_rewards=False)

    def _apply_fire_payload(self, target, spec, direction) -> None:
        portent_hit = spec.get("portent")
        if portent_hit and target.integrity > 0:
            if self._apply_direct_portent(target, portent_hit[0], int(portent_hit[1]),
                                          mode="add"):
                self.messages.append(tr("{target}被「{portent}」缠上了。",
                                        target=tr(target.label), portent=tr(portent_hit[0])))
        if spec.get("pulse"):
            self._sound_pulse(target.x, target.y, int(spec["pulse"]), by_player=True,
                              category="projectile", source=tr("投射物"))

    @root_action
    def fire(self, dx: int, dy: int, *, choice: str | None = None) -> ActionResult:
        if max(abs(dx), abs(dy)) != 1:
            return ActionResult(False, tr("发射方向无效。"))
        action_plan = self.equipment.plan_action("fire", choice=choice)
        if not action_plan.valid:
            return self._fire_choice_result(action_plan)
        magazine_error = self._consume_equipment_magazine(action_plan)
        if magazine_error:
            return ActionResult(False, magazine_error)
        self.facing = (dx, dy)
        spec = dict(action_plan.projectile_profile)
        self._emit_fire_noise(spec)
        consumed_charge = False
        if choice == 'legacy_basic_fire':
            if not self._consume_legacy_basic():
                return ActionResult(False, tr('旧档继承的基础发射已经用完，请先换弹。'))
        elif action_plan.innate:
            self.projectile_charges -= 1
            consumed_charge = True
        hand_item = self.equipment._item(action_plan.primary_source_id)
        template = PROJECTILE_DEFINITIONS.get(hand_item.projectile_template if hand_item else "直线弹体", PROJECTILE_DEFINITIONS["直线弹体"])
        penetration = self._shot_penetration(action_plan, spec)
        # 借来的穿透只够这一发：算进上面那个数之后立刻领走。
        from ..expansion_consumables import spend_pierce_loan
        spend_pierce_loan(self)
        push_power = template["push"] + (hand_item.push if hand_item else 0) + int(spec.get("push", 0))
        blocked_at: list[int] | None = None
        range_end: list[int] | None = None
        hit: str | None = None
        pierced = 0
        repeat_phases = 0
        # 2026-09-19：弹道形状/夹缝判定/穿透衰减统一走 core.ballistics
        # （顶层导入——打包版曾因运行期懒加载撞上损坏的归档条目而闪退）。
        # 2026-09-23：循环改为带方向变量的逐格推进（跳弹要改向），走过的格
        # 序列与跳弹点存入 last_projectile 供 FX 层回放（纯装饰，不入档）。
        flight: list[tuple[int, int]] = []
        bounce_points: list[tuple[int, int, int]] = []  # (转向下标, 跳弹格 x, y)
        placed_mirror_bounce = False
        fx_dir, fy_dir = dx, dy
        cx, cy = self.player.x, self.player.y
        end_kind, end_cell = "range", None
        steps = 0
        shot_range = min(PROJECTILE_MAX_RANGE, int(spec.get('range', PROJECTILE_MAX_RANGE)))
        from ..combat_constructs import _continue_budget
        shot_range = _continue_budget(self, (self.player.x, self.player.y),
                                      fx_dir, fy_dir, shot_range)
        while steps < shot_range:
            x, y = cx + fx_dir, cy + fy_dir
            steps += 1
            if not (0 <= x < self.width and 0 <= y < self.height):
                break
            range_end = [x, y]
            from ..construct_environments import reflection
            reflected = reflection(self, x, y, (fx_dir, fy_dir))
            if reflected is not None and not bounce_points:
                placed_mirror_bounce = True
                flight.append((x, y))
                bounce_points.append((len(flight)-1, x, y))
                fx_dir, fy_dir = reflected
                cx, cy = x, y
                continue
            if self.cell(x, y).solid:
                cell = self.cell(x, y)
                from ..expansion_consumables import on_collision
                on_collision(self)
                if self.puzzle_projectile_blocked(x, y):
                    blocked_at = [x, y]
                    end_kind, end_cell = 'wall', (x, y)
                    break
                # 斜向夹缝：两轴正交邻格均坚实 → 弹体被夹缝挡下（不弹）。
                if angle_blocked(
                    {(ax, ay): self.cell(ax, ay).solid for ay in range(self.height) for ax in range(self.width)},
                    x - fx_dir, y - fy_dir, fx_dir, fy_dir,
                ):
                    blocked_at = [x, y]
                    end_kind, end_cell = "gap", (x, y)
                    break
                if wall_def(cell.wall_kind).projectile_immune:
                    # 玉米淀粉墙（2026-09-23 改版）：非牛顿体免疫弹体伤害不变，
                    # 同时 **100% 全角度反弹**——正交打回、斜向按几何反射；
                    # 反弹经济（每发 1 次、剩余穿透 −1）耗尽才按原样吞掉。
                    if not bounce_points and penetration >= 1:
                        solid = {(ax, ay): self.cell(ax, ay).solid for ay in range(self.height) for ax in range(self.width)}
                        old_dx, old_dy = fx_dir, fy_dir
                        fx_dir, fy_dir = bounce_direction(solid, x - old_dx, y - old_dy, old_dx, old_dy)
                        penetration -= 1
                        bounce_points.append((len(flight), x, y))
                        # 从入射前的格子沿新方向继续（被挡的墙格不进入弹道）。
                        cx, cy = x - old_dx, y - old_dy
                        self.messages.append(tr("弹体从淀粉墙上弹了回来！"))
                        continue
                    blocked_at = [x, y]
                    end_kind, end_cell = "wall", (x, y)
                    self.messages.append(tr("弹体陷进墙里，无声无息地消失了。"))
                    break
                resistance = max(1, cell.hardness * cell.thickness)
                if penetration < resistance:
                    # 浅角跳弹（§9.2 实装）：斜向 45° 掠过硬面（hardness ≥ 2）
                    # 且恰好一侧坚实 → 反射该轴继续飞；不掉墙完整度、穿透 −1、
                    # 每发 1 次。软墙/正撞/夹缝一律照旧结算。
                    if (
                        not bounce_points and fx_dir != 0 and fy_dir != 0
                        and cell.hardness >= 2 and penetration >= 1
                    ):
                        solid = {(ax, ay): self.cell(ax, ay).solid for ay in range(self.height) for ax in range(self.width)}
                        side_a = solid.get((x, y - fy_dir), True)
                        side_b = solid.get((x - fx_dir, y), True)
                        if side_a != side_b:
                            old_dx, old_dy = fx_dir, fy_dir
                            fx_dir, fy_dir = bounce_direction(solid, x - old_dx, y - old_dy, old_dx, old_dy)
                            penetration -= 1
                            bounce_points.append((len(flight), x, y))
                            cx, cy = x - old_dx, y - old_dy
                            self.messages.append(tr("浅角掠过墙面——弹体跳弹了！"))
                            continue
                    blocked_at = [x, y]
                    end_kind, end_cell = "wall", (x, y)
                    integrity_before = int(cell.integrity)
                    cell.integrity = max(0, cell.integrity - max(10, penetration * 20))
                    if cell.integrity == 0:
                        self.destroy_wall(x, y, "projectile", integrity_before=integrity_before)
                        self.messages.append(tr("弹体击碎了一处坚实聚合物。"))
                    break
                penetration -= resistance
                pierced += 1
                integrity_before = int(cell.integrity)
                cell.integrity = max(0, cell.integrity - 35)
                if cell.integrity == 0:
                    self.destroy_wall(x, y, "projectile", integrity_before=integrity_before)
                cx, cy = x, y
                flight.append((x, y))
                continue
            target = self.entity_at(x, y)
            if target is self.player and placed_mirror_bounce:
                from ..memory_buffers import spend
                self._lose_mind(max(0, 1-spend(self,"mind:self_projectile")))
                hit = self.player.id
                flight.append((x, y))
                end_kind, end_cell = 'entity', (x, y)
                break
            if target and target is not self.player and target.trait == "staircase":
                # 迁徙的楼梯占据的格子视为坚实：弹道在此被挡下，不伤及它。
                blocked_at = [x, y]
                end_kind, end_cell = "wall", (x, y)
                break
            if target and target is not self.player:
                hit = target.id
                flight.append((x, y))
                end_kind, end_cell = "entity", (x, y)
                repeat_phases = self._player_strike(target, "ranged",
                                    damage=1, action_plan=action_plan,
                                    attack_dir=(fx_dir, fy_dir),repeat_path=flight,
                                    repeat_obstacles=tuple((bx,by) for _,bx,by in bounce_points))
                # 折射书写（三棱镜的吊坠）：只有**经跳弹改向**后的命中才刻印记，
                # 记下的是改向后的方向——下一次换个方向打它才吃加成。
                if bounce_points:
                    self._mark_refract(target, (fx_dir, fy_dir))
                self._apply_fire_payload(target, spec, (fx_dir, fy_dir))
                # 已被这一击解体的目标不再被推动——原实现会在它死后继续推。
                if target.integrity > 0 and push_power:
                    # 罗生门残页（2026-10-22 P3）：命中前先演一遍推离落点与碰撞。
                    from ...equipment.library import testimony_preview
                    testimony_preview(self, target, dx, dy, push_power)
                    self._push_entity(target, dx, dy, push_power)
                if target.integrity <= 0:
                    self._resolve_enemy(target)
                    if target.anomaly_kind == "强烈异象" and self.insight_active("现实洞察"):
                        self.restore_resource('mind', 2)
                break
            cx, cy = x, y
            flight.append((x, y))
        self._note_projectile(
            flight, bounce_points, kind="shot", color="#ffe0b3",
            end=end_kind, end_cell=end_cell,
            repeat_delay=.12 if repeat_phases == 2 else 0.,
        )
        self._spend_attack_time(action_plan.base_time, aptitude="shooting")
        data: dict[str, Any] = {
            "blocked_at": blocked_at,
            "hit": hit,
            "consumed_charge": consumed_charge,
            "projectile_charges": self.projectile_charges,
            "pierced": pierced,
            "remaining_penetration": penetration,
            "range_end": range_end,
            'equipment_repeat_phases': repeat_phases,
        }
        if hit:
            self.tutorial_events["fired_hit"] = hit
            self.messages.append(tr("弹体命中失控意识。"))
        elif blocked_at:
            self.messages.append(tr("弹体撞上坚实聚合物。"))
        elif range_end is not None and len(range_end) == 2 and max(abs(range_end[0] - self.player.x), abs(range_end[1] - self.player.y)) >= shot_range:
            self.messages.append(tr("弹体飞出有效距离后消散。"))
        else:
            self.messages.append(tr("弹体消失在梦境结构中。"))
        return ActionResult(True, self.messages[-1], data)

# 像素拆解（扩展包 v2）：千禧园可拆的装饰/功能墙（不含结构墙蓝砖/千禧树/木门，
# 更不含蓝屏终端——拆它 = 敌对召唤千年虫，绝不能被一个构想顺手引爆）。
_MILLENNIUM_DISMANTLABLE_WALLS = frozenset({
    "色块墙·红", "色块墙·橙", "色块墙·蓝", "白块窗", "传真墙",
    "灯箱墙", "弹窗墙", "磁带墙", "摇杆柱", "打印机墙",
})
