"""失控意识：生成、感知与移动、按客观时间蓄力的贴身打击、行为特征与反伤。"""

from __future__ import annotations

import random
from typing import Any

from ..i18n import tr
from .cast_fx import animate_legacy
from .stable_identity import token as stable_token
from ..materials import DOOR_KINDS, floor_effect_for, liquid_contact_noise, portent_def
from ..symbols import entity_glyph
from .constants import (
    ANOMALY_REFRESH_ACTIVE_CAP,
    ANOMALY_REFRESH_DROP_DECAY,
    ANOMALY_REFRESH_FREE_DROP_WAVES,
    ATTACH_HUNT_BONUS_MAX,
    NOISE_AMBIENT_RADIUS,
    NOISE_AMBIENT_TURNS,
    CARRIED_IMAGE,
    CREATURE_PORTENT_DAMAGE_PERIOD,
    CORE_CONTROL_WINDOW,
    ELITE_CONTROL_WINDOW,
    CONTROL_RECOVERY_ROUNDS,
    PORTENT_EXTRA_TURN_CAP,
    LOST_TARGET_TURNS,
    REFRACT_MARK_TURNS,
    WET_CONDUCT_COOLDOWN,
    portent_scaled_amount,
)
from .content import ANOMALY_DEFINITIONS, ITEM_DEFINITIONS, equipment_pool_for_depth
from .entities import Cell, Entity, WorldItem
from .pathing import PursuitMixin


def _late_spawn_drop_multiplier(enemy: Entity) -> float:
    """本层后期补刷异象的掉落倍率（2026-10-27 玩家需求）。

    spawn_wave == 0（随地图生成的首波/非补刷）与 wave <= FREE_WAVES（每层前几次
    自然补刷）返回 1.0——掉落行为与旧版完全一致；此后每多一只补刷乘一次
    ANOMALY_REFRESH_DROP_DECAY，即 DECAY ** (wave - FREE_WAVES) 的指数衰减。
    """
    wave = int(getattr(enemy, "spawn_wave", 0) or 0)
    free = max(0, int(ANOMALY_REFRESH_FREE_DROP_WAVES))
    if wave <= 0 or wave <= free:
        return 1.0
    return float(ANOMALY_REFRESH_DROP_DECAY) ** (wave - free)


def _late_spawn_bonus_ok(rng: random.Random, multiplier: float) -> bool:
    """小概率 bonus（台阶灰尘/键帽）在后期补刷时按倍率发放。

    multiplier >= 1.0 时直接返回 True 且不消耗随机数，保证首波与前几次补刷的
    随机序列和掉落结果与旧版逐位一致；衰减档才真正掷一次。
    """
    if multiplier >= 1.0:
        return True
    return rng.random() < multiplier


def sound_sector(dx: int, dy: int) -> str:
    """八方位声向：只给扇区，不给精确落点。"""
    if dx == 0 and dy == 0:
        return "脚下"
    vertical = "北" if dy < 0 else "南" if dy > 0 else ""
    horizontal = "东" if dx > 0 else "西" if dx < 0 else ""
    return vertical + horizontal if vertical and horizontal else vertical or horizontal


FINE_SECTORS = ("东", "东东北", "东北", "北东北", "北", "北西北", "西北", "西西北",
                "西", "西西南", "西南", "南西南", "南", "南东南", "东南", "东东南")


def fine_sound_sector(dx: int, dy: int) -> str:
    """十六方位：22.5° 档，仍不返回精确坐标。"""
    if dx == 0 and dy == 0:
        return "脚下"
    import math
    angle = math.degrees(math.atan2(-dy, dx)) % 360
    return FINE_SECTORS[int(round(angle / 22.5)) % 16]


SOUND_CATEGORY_NAMES = {
    "step": "脚步",
    "lure": "主动诱引",
    "item": "道具",
    "projectile": "投射物",
    "explosion": "爆炸",
    "wall_break": "墙体破坏",
    "porcelain": "瓷墙碎裂",
    "environment": "环境",
    "voice": "呼喊",
    "ability": "构想",
    "generic": "响动",
}


def sound_category_name(category: str) -> str:
    return SOUND_CATEGORY_NAMES.get(str(category), "响动")


def sound_band(distance: int) -> str:
    """距离档：声径与听取上限都按曼哈顿距离计算。"""
    distance = abs(int(distance))
    if distance <= 3:
        return "近距"
    if distance <= 7:
        return "中距"
    if distance <= 12:
        return "远距"
    return "极远"


def sound_strength(residual: int) -> str:
    """接收强弱：只看声音到达玩家时的余量，不由隐藏源坐标推算距离。"""
    if residual >= 6:
        return "强"
    if residual >= 2:
        return "中等"
    return "弱"


_AUTO_SOUND_EMITTER = object()


class EnemyMixin(PursuitMixin):
    def _apply_reflect(self, enemy: Entity, effect_id: str) -> None:
        """把一次反伤落到玩家身上（反击与荆棘共用的收敛点）。

        effect_id 留空时回落到该异象自身的创伤类型；显式给 "mind" / "lucidity"
        可覆盖。结算完必须判终局——反伤本身可能就是致命的那一击。
        """
        kind = effect_id or ("mind" if enemy.trauma_type == "心智创伤" else "lucidity")
        previous_indirect = getattr(self, '_presentation_indirect_trauma', False)
        self._presentation_indirect_trauma = True
        try:
            if kind == "lucidity":
                from .settlement import REASON_COMBAT, settle_delta
                result = settle_delta(self, 'lucidity', -1, reason=REASON_COMBAT,
                                      source=str(getattr(enemy, 'label', enemy.id)))
                self._note_board_hurt('lucidity', -result.applied, source_id=enemy.id)
                harm = "清醒创伤"
            else:
                self._lose_mind(1, combat=True, source_id=enemy.id)  # 反伤属于战斗创伤
                harm = "心智创伤"
        finally:
            self._presentation_indirect_trauma = previous_indirect
        self.messages.append(tr("{enemy}把这一下反了回来，造成{harm}。", enemy=tr(enemy.label), harm=tr(harm)))
        self.last_harm_source = enemy.label
        self.last_harm_time = self.time
        self._check_run_over()

    def _maybe_counter(self, enemy: Entity, range_kind: str) -> None:
        """反击：只认玩家的「攻击行动」次数——一次多段攻击仍只算 1 次。

        在攻击行动收尾时调用一次；目标已死也照常判定（打死后仍反伤）。
        """
        if enemy.counter_every <= 0:
            return
        if enemy.counter_scope != "any" and enemy.counter_scope != range_kind:
            return
        enemy.attack_actions_taken += 1
        if enemy.attack_actions_taken % enemy.counter_every == 0:
            self._apply_reflect(enemy, enemy.counter_effect)

    def _maybe_thorns(self, enemy: Entity, range_kind: str) -> None:
        """荆棘：只认一次攻击的「段数」——每命中一段结算一次。

        与回合、客观时间、行动计数完全无关；调用时机与顺序由多段攻击模块决定
        （见 _player_strike：击杀即停，后续段连同其荆棘都不结算）。
        """
        if not enemy.thorns_per_segment:
            return
        if enemy.thorns_scope != "any" and enemy.thorns_scope != range_kind:
            return
        self._apply_reflect(enemy, enemy.thorns_effect)

    # ---- 构筑桥接组件（2026-10-08，平衡方案 §6.1 的六种原型各补一环）----
    # 六件的效果都在这里收敛：印记/附着读命中，回声读脉冲，潮润读放电，
    # 灰烬读点燃（materials_sim._ignite_cell），留白读构想扣费（actions）。

    def _mark_refract(self, target: Entity, direction: tuple[int, int]) -> None:
        """折射印记：跳弹改向后的命中给目标挂 3 回合标记，并记下入射方向。"""
        if self._effect_power("refract_mark") <= 0 or target.integrity <= 0:
            return
        self.refract_marks[target.id] = {
            "until": self.time + REFRACT_MARK_TURNS,
            "dir": direction,
        }
        self.messages.append(
            tr("折射印记刻在{target}身上（{turns} 回合）：换个方向打它。",
               target=tr(target.label), turns=REFRACT_MARK_TURNS)
        )

    def _refract_bonus(self, target: Entity, attack_dir: tuple[int, int] | None) -> int:
        """折射书写的收益结算：同方向不打折，印记留着等下一次角度。"""
        mark = self.refract_marks.get(target.id)
        if not mark:
            return 0
        if self.time >= mark["until"]:
            self.refract_marks.pop(target.id, None)
            return 0
        if attack_dir is None or tuple(attack_dir) == mark["dir"]:
            return 0
        self.refract_marks.pop(target.id, None)
        bonus = self._effect_power("refract_mark")
        self.messages.append(
            tr("角度换了——折射印记亮起来，这一击 +{bonus}。", bonus=bonus)
        )
        return bonus

    def _attach_hunt_bonus(self, target: Entity, action_plan=None) -> int:
        """附着追猎：认得出目标身上挂的是哪种材料，并给一次性的辨识加成。"""
        from ..equipment.runtime import action_effect_power
        power = action_effect_power(self, 'attach_hunt', action_plan.rows if action_plan else ())
        if power <= 0 or not any(amount > 0 for amount in target.portent_attach.values()):
            return 0
        key = f"attach_{self.depth}:{target.id}"
        if key not in self.bridge_once:
            self.bridge_once[key] = 1
            portent_id = next(key for key, amount in target.portent_attach.items() if amount > 0)
            definition = portent_def(portent_id)
            name = definition.name if definition else portent_id
            self.messages.append(
                tr("皮绳认出了味道：{target}身上附着的是「{name}」。",
                   target=tr(target.label), name=tr(name))
            )
        # 上限 1：多件同类件不叠伤害（方案要求「不无限叠伤害」）。
        return min(power, ATTACH_HUNT_BONUS_MAX)

    def _echo_control_pulse(self, x: int, y: int, reached: int, suspicious: int = 0) -> None:
        """回声控场：本层已有一次成功引诱时，这一次脉冲本身变成控制。

        「引诱成功」= 内圈惊醒（reached）或外圈起疑（suspicious）任一发生——
        外圈异象前往声源同样是值得记档的诱引（docs §16.4）。
        """
        power = self._effect_power("echo_control")
        if power <= 0:
            return
        if self.echo_armed_depth == self.depth:
            self.echo_armed_depth = -1
            frozen = 0
            for enemy in list(self.enemies):
                if enemy.integrity <= 0 or enemy.trait in ("staircase",):
                    continue
                if abs(enemy.x - x) + abs(enemy.y - y) > power:
                    continue
                enemy.frozen_turns = max(enemy.frozen_turns, 1.0)
                frozen += 1
            self.messages.append(
                tr("音叉的另一次分岔落下：声源 {radius} 格内 {frozen} 个失控意识当场震停。",
                   radius=power, frozen=frozen)
            )
        elif reached + suspicious > 0:
            self.echo_armed_depth = self.depth
            self.messages.append(tr("音叉有一根齿记下了这次声响——下一次脉冲会带上控制。"))

    def _wet_conduct_chain(self, struck: list) -> int:
        """潮润传导：放电在湿润目标之间**只多传一次**，冷却 6 回合。"""
        power = self._effect_power("wet_conduct")
        if power <= 0 or self.time < self.wet_conduct_ready:
            return 0
        hit_ids = {enemy.id for enemy in struck}
        for source in struck:
            for enemy in self.enemies:
                if enemy.id in hit_ids or enemy.integrity <= 0:
                    continue
                if enemy.relation != "失控意识":
                    continue
                if abs(enemy.x - source.x) + abs(enemy.y - source.y) > 2:
                    continue
                if self.cell(enemy.x, enemy.y).liquid_kind != "导电液态记忆":
                    continue
                self._kill_full_reward = True  # 玩家导电链：崩解全额
                enemy.integrity = max(0, enemy.integrity - power)
                self.wet_conduct_ready = self.time + WET_CONDUCT_COOLDOWN
                self.messages.append(
                    tr("盐把电流接了过去：湿润的{enemy}也被咬了一口。", enemy=tr(enemy.label))
                )
                if enemy.integrity <= 0:
                    self._resolve_enemy(enemy)
                return 1
        return 0

    def _player_strike(
        self,
        target: Entity,
        range_kind: str,
        segments: int = 1,
        damage: int = 1,
        attack_dir: tuple[int, int] | None = None,
        normal_melee: bool = False,
        action_plan=None,
        repeat_path=None,
        repeat_obstacles=(),
    ) -> int:
        """玩家一次攻击对单个目标的完整结算顺序（文档第 6 节的契约实现）。

        [SFX挂点] 攻击命中（近战/远程同路）：建议 attack_hit（奇幻武器\sword_hit
        或 blade_*）。core 保持纯逻辑，播放挂 UI 层（结果 diff），见《音效挂点索引.md》。
        现在的两条攻击路径都是单段，将来多段武器只需传 segments=N：逐段结算
        伤害与荆棘，一旦击杀立即停下；行动级反击在收尾时照常判定一次，最后统一
        判终局。目标要不要移除由调用方决定（_resolve_enemy 排在最后），反伤不能
        因此被跳过。
        """
        if target.integrity <= 0:
            return 0
        from .expansion_consumables import on_collision
        on_collision(self)
        if "spooked" in target.portents:
            # 惊散解除（docs §15.5）：被打一下立即惊醒并转为追踪，直奔声源
            # 之后的真实目标——玩家当前位置。
            self._remember_portent_end(target, "spooked")
            self._remember_portent_end(target, "spooked_attach")
            if target.relation == "失控意识":
                target.alert_state = "追踪"
                target.last_seen_x, target.last_seen_y = self.player.x, self.player.y
                target.wandering = False
                self._plan_chase(target, self.player.x, self.player.y)
                self.messages.append(tr("{enemy}被这一下惊醒了！", enemy=tr(target.label)))
        if action_plan is not None:
            # A real hit claims one action budget, before existing mitigation.
            # Preview, miss, extra targets and segments cannot claim it again.
            damage += self.equipment.claim_damage_bonus(action_plan)
        if not getattr(self, '_equipment_derived_depth', 0):
            from ..equipment.library import library_damage_bonus
            damage += library_damage_bonus(self, damage, target)
        from ..equipment.positional_events import redeem_imprint
        damage += redeem_imprint(self, target)
        self._kill_full_reward = True  # 近战/远程玩家攻击：崩解全额
        # 守株待兔（扩展包 v1）：等待后的下一次攻击创伤 +2，出手即消耗。
        if getattr(self, "ambush_ready", False):
            damage += 2
            self.ambush_ready = False
        # 稳定意识（NPC）：高血量且所受各种创伤大幅降低（每段 ÷4，至少 1）；
        # 被打不还手（反伤/反击规格对稳定意识一律跳过）。
        if target.relation == "稳定意识":
            damage = max(1, damage // 4)
        # 玩偶意识体（教学层）：正常承伤，命中即记入引导旗标。
        if target.relation == "玩偶意识体":
            self.tutorial_events["struck_doll"] = target.id
        # 嘲讽（无声观众）：目标身处任一存活观众的视野内时，创伤转移给观众。
        for watcher in self.enemies:
            if (
                watcher is not target and watcher.integrity > 0
                and watcher.trait == "taunt"
                and max(abs(watcher.x - target.x), abs(watcher.y - target.y)) <= watcher.vision
            ):
                target = watcher
                self.messages.append(tr("嘲讽把这一击引到了{watcher}身上！", watcher=tr(watcher.label)))
                break
        from ..equipment.expansion_runtime import construct_damage_bonus
        damage += construct_damage_bonus(self, target)
        if range_kind == 'melee' and not getattr(self, '_expansion_construct_cast', None):
            from ..equipment.expansion_runtime import consume_melee_mark
            damage += consume_melee_mark(self, target)
        # 纸折护身（折页人）：受到的创伤 −1（至少 1 点）。
        if target.trait == "paper_fold":
            damage = max(1, damage - 1)
        feedback = self._identity_melee_bonus(target, normal_melee and range_kind == 'melee')
        if ('pathogen' in target.biological_tags
                and self.player.portents.get('hospital_lymph_hit', 0) > 0
                and not getattr(self, '_equipment_derived_depth', 0) and damage > 0):
            feedback += 2
            self._clear_hospital_buff('hospital_lymph_hit')
        # 护折/护幕（异象主动技能）：下一次受击 −1（最低 1），命中即消耗。
        if target.integrity > 0:
            guard = self._enemy_skill_guard_reduce(target)
            # 抢拍（扩展包 v2）：命中蓄势中的异象，其施法倒计时被拖延 1 回合。
            if self.insight_active("抢拍"):
                self._enemy_skill_delay_windup(target)
            first_damage = max(1, damage + feedback - guard)
            damage = max(1, damage - guard)
            feedback = first_damage - damage
        # ---- 构筑桥接组件（2026-10-08，平衡方案 §6.1）----
        # 折射书写：带印记的目标被**换个方向**打到才吃加成（同方向不打折，
        # 印记留在身上等下一次角度）。
        damage += self._refract_bonus(target, attack_dir)
        # 附着追猎：身上还挂着材料附着的意识，攻击辨识加成 +1（多件不叠加）。
        damage += self._attach_hunt_bonus(target, action_plan)
        count = max(1, segments)
        before_integrity = target.integrity
        from ..equipment.repetition import reserved_damage,record_phase,claim_repeat
        impact = (target.x,target.y)
        origin = (self.player.x,self.player.y)
        path = tuple(repeat_path or ())
        pairs = tuple(zip((origin,*path),path))
        real_ray = bool(path and path[-1] == impact and all(self.inside_board(*cell) for cell in path)
                        and all(max(abs(a[0]-b[0]),abs(a[1]-b[1])) == 1 for a,b in pairs))
        footprint = tuple(dict.fromkeys((*path,*repeat_obstacles,
                         *(cell for a,b in pairs if a[0] != b[0] and a[1] != b[1]
                           for cell in ((a[0],b[1]),(b[0],a[1]))))))
        real_ray = real_ray and all(self.inside_board(*cell) for cell in footprint)
        ray_snapshot = tuple((self.cell(*cell).solid,self.cell(*cell).wall_kind) for cell in footprint) if real_ray else ()
        opcode = 'melee' if range_kind == 'melee' else 'fire'
        reserved = reserved_damage(action_plan,damage) if range_kind == 'melee' or real_ray else 0
        phases = 1
        def strike_phase(budget,first_bonus=0):
            quotient,remainder = divmod(budget,count)
            loss = 0
            for segment in range(count):
                part = quotient+(segment < remainder) if action_plan is not None else budget
                part += first_bonus if segment == 0 else 0
                if part <= 0:
                    continue
                if target.portents.get('hospital_gel_buffer', 0) > 0:
                    for table in (target.portents, target.portent_attach, target.portent_debt, target.portent_stacks):
                        table.pop('hospital_gel_buffer', None)
                    part = max(0, part - 1)
                loss += min(target.integrity,part)
                target.integrity -= part
                if target.relation != '稳定意识':
                    self._maybe_thorns(target,range_kind)
                if target.integrity <= 0:
                    break
            return loss
        first_loss = strike_phase(damage-reserved,feedback)
        if first_loss > 0 and getattr(self, "vanish_turns", 0) > 0:
            # 匿踪在命中暴露结算之后结束（不是出手前）。
            self.vanish_turns = 0
        hit_noted = False
        if reserved:
            record_phase(self,action_plan,opcode,first_loss,cell=impact,target=target)
            self._note_board_hit(target,action_plan=action_plan,amount=first_loss,damage_kind=range_kind)
            hit_noted = True
            reachable = (max(abs(impact[0]-self.player.x),abs(impact[1]-self.player.y)) <= 1
                         if range_kind == 'melee' else
                         real_ray and origin == (self.player.x,self.player.y)
                         and ray_snapshot == tuple((self.cell(*cell).solid,self.cell(*cell).wall_kind) for cell in footprint)
                         and all(self.entity_at(*cell) in (None,self.player,target) for cell in path))
            if (target.integrity > 0 and self.entity_at(*impact) is target and not self.cell(*impact).solid
                    and reachable and claim_repeat(self,action_plan,opcode,cell=impact,target=target)):
                second_loss = strike_phase(reserved)
                record_phase(self,action_plan,opcode,second_loss,cell=impact,target=target)
                from ..equipment.root_facts import record_event
                record_event(self,'hit',cell=impact,target=target,source_id=self.player.id,
                             recipient_id=target.id,amount=second_loss,damage_kind=range_kind)
                if second_loss:
                    phases = 2
                    if range_kind == 'melee':
                        self._emit_combat_fx('cut',impact,[impact])
        if target.npc_kind.startswith('hospital.') and target.integrity < before_integrity:
            from .hospital_scenes import damage_hospital_actor
            damage_hospital_actor(self, target, explicit=normal_melee and range_kind == 'melee')
        # 命中端（联想盘根事件）：一次实际命中；多段攻击归属于同一行动事件。
        if not hit_noted:
            self._note_board_hit(target, action_plan=action_plan,
                                 amount=min(before_integrity, max(0, before_integrity-target.integrity)),
                                 damage_kind=range_kind)
        # 回声抄写员：玩家每次打它，它「学会」+1 创伤，下次攻击一并倾泻。
        if target.trait == "echo_copy" and target.integrity > 0:
            target.echo_bonus = getattr(target, "echo_bonus", 0) + 1
        # 空间挪移（房间折叠体）：受击后有概率挪移到附近另一处。
        if target.integrity > 0 and target.trait == "room_shift" and self.time % 3 == 0:
            import random as _random
            shift_rng = _random.Random(self.seed ^ (self.time * 613) ^ stable_token(target))
            for _ in range(8):
                nx = target.x + shift_rng.randint(-4, 4)
                ny = target.y + shift_rng.randint(-4, 4)
                if (
                    0 < nx < self.width - 1 and 0 < ny < self.height - 1
                    and not self.cell(nx, ny).solid and self.entity_at(nx, ny) is None
                ):
                    target.x, target.y = nx, ny
                    self.messages.append(tr("房间折叠体挪到了别处。"))
                    break
        if target.relation != "稳定意识":
            self._maybe_counter(target, range_kind)
        # 攻击附燃（2026-09-18）：点火手套等装备的 ignite_strike——
        # 命中后目标所在格被点燃（走统一点燃入口，可燃气浓度高则引爆）。
        if target.integrity > 0 and self._effect_power("ignite_strike") > 0:
            self._ignite_cell(target.x, target.y, 2, by_player=True)
        # ---- 扩展包 v1 装备 effect ----
        if target.integrity > 0:
            import random as _random

            strike_rng = _random.Random(self.seed ^ (self.time * 719) ^ stable_token(target))
            sleep_power = self._effect_power("sleep_strike")
            if sleep_power and strike_rng.random() < 0.2:
                # 梦貘鼻烟壶：命中 20% 直接放倒（深眠两回合）。2026-10-07 从 30% 下调。
                target.frozen_turns = max(target.frozen_turns, 2.0)
                self.messages.append(tr("梦貘的鼻息把{target}放倒了（深眠 2 回合）。", target=tr(target.label)))
            erase_power = self._effect_power("erase_strike")
            if erase_power and target.portents and strike_rng.random() < 0.2:
                # 没水的笔：命中 20% 删去目标**最近获得的一条**征兆（2026-10-07
                # 从「全清」下调——对 buff 型强敌不再是无条件硬 counter）。
                erased_id = next(reversed(list(target.portents)))
                self._remember_portent_end(target, erased_id)
                erased_name = portent_def(erased_id).name if portent_def(erased_id) else erased_id
                self.messages.append(tr("没水的笔一划——{target}身上的「{name}」被删掉了。",
                                        target=tr(target.label), name=tr(erased_name)))
            aura_power = self._effect_power("shock_aura")
            if aura_power and range_kind == "melee" and target.integrity > 0:
                # 静电披风：被相邻攻击者击中时反打一记传导冲击。
                target.integrity = max(0, target.integrity - 1)
                self.messages.append(tr("静电披风炸出一记传导冲击，反打了{target}！"))
        # 行动事实（§13.3）：这条路径是玩家**直接攻击**的唯一汇流点，所以伤害
        # 归因在这里记账——关系模块据此判「确认过的攻击」，任务据此认战斗解法。
        dealt = max(0, before_integrity - target.integrity)
        if dealt:
            from ..equipment.expansion_runtime import action_conductive_field
            action_conductive_field(self, action_plan, impact)
            from .hit_events import note_hit
            hit_dir = attack_dir
            if real_ray and len(path) >= 2 and path[-1] == impact:
                # 跳弹后取最后一段有效轨迹的方向，不能仍用最初 facing。
                hit_dir = (impact[0] - path[-2][0], impact[1] - path[-2][1])
            note_hit(
                self,
                kind="melee" if range_kind == "melee" else "ranged",
                source=origin,
                impact=impact,
                target_id=target.id,
                amount=dealt,
                resource="integrity",
                direction=hit_dir,
                killed=target.integrity <= 0,
            )
            from ..world import facts as world_facts
            from ..world import relations

            world_facts.record(self, "harm", actor_uid=relations.player_uid(self),
                               target_uid=target.actor_uid or target.id, position=impact,
                               source_kind="direct_attack", cause_uid=f"attack:{range_kind}",
                               before=before_integrity, after=target.integrity, amount=dealt)
        if dealt:
            from ..equipment.expansion_runtime import on_construct_hit
            on_construct_hit(self, target, killed=target.integrity <= 0)
        self._check_run_over()
        return phases

    def add_enemy(
        self,
        label: str,
        x: int,
        y: int,
        integrity: int = 1,
        move_time: float = 1.0,
        attack_time: float = 1.0,
        relation: str = "失控意识",
        trauma_type: str = "心智创伤",
        communicates: bool = True,
        drop_id: str | None = None,
        dissolution_reward: int = 4,
        catalog_id: str = "anomaly.unknown",
        anomaly_kind: str = "普通异象",
        vision: int = 6,
        trait: str = "",
        counter_every: int = 0,
        counter_scope: str = "any",
        counter_effect: str = "",
        thorns_per_segment: bool = False,
        thorns_scope: str = "any",
        thorns_effect: str = "",
        spawn_wave: int = 0,
    ) -> Entity:
        x, y = self._find_open_cell(self.cells, x, y)
        # 汉字自带两列，再加空格就是三列——会把整行挤错位。一律过 entity_glyph 补齐/截断。
        glyphs = {
            "纸页犬": "犬", "折页人": "折", "倒放鼓手": "鼓", "模型搬运工": "搬",
            "无声观众": "观", "冷却人偶": "偶", "逆光读者": "读", "回声门": "门", "游荡的纸页犬": "游",
            "强烈异象·无脸编辑": "编", "强烈异象·房间折叠体": "叠", "核心执念·未完成句号": "终",
            "残影": "影",
        }
        enemy = Entity(
            f"enemy-{self.next_enemy_id}", label, x, y, integrity,
            move_time=move_time, attack_time=attack_time, relation=relation, trauma_type=trauma_type,
            communicates=communicates, drop_id=drop_id, dissolution_reward=dissolution_reward,
            catalog_id=catalog_id, anomaly_kind=anomaly_kind,
            vision=vision, glyph=entity_glyph(glyphs.get(label, "")),
            trait=trait,
            counter_every=counter_every, counter_scope=counter_scope, counter_effect=counter_effect,
            thorns_per_segment=thorns_per_segment, thorns_scope=thorns_scope, thorns_effect=thorns_effect,
            spawn_wave=spawn_wave,
        )
        self.next_enemy_id += 1
        self.enemies.append(enemy)
        return enemy

    def add_defined_enemy(self, catalog_id: str, x: int, y: int, **overrides: Any) -> Entity:
        definition = ANOMALY_DEFINITIONS[catalog_id]
        values = {
            "label": definition["name"],
            "integrity": definition["integrity"],
            "move_time": definition["move_time"],
            "attack_time": definition["attack_time"],
            "trauma_type": definition["trauma_type"],
            "communicates": definition["communicates"],
            "drop_id": definition.get("drop_id"),
            "dissolution_reward": definition["dissolution_reward"],
            "anomaly_kind": definition["anomaly_kind"],
            "vision": definition["vision"],
            "trait": definition.get("trait", ""),
            # 反伤规格（缺省即无）；将来内容只要在定义里写这几项就能挂上。
            "counter_every": definition.get("counter_every", 0),
            "counter_scope": definition.get("counter_scope", "any"),
            "counter_effect": definition.get("counter_effect", ""),
            "thorns_per_segment": definition.get("thorns_per_segment", False),
            "thorns_scope": definition.get("thorns_scope", "any"),
            "thorns_effect": definition.get("thorns_effect", ""),
        }
        # 开局选项「异象强度」：定义完整度按倍率缩放（至少 1）。显式 overrides
        # （教学图的 integrity=1 等）后生效、不被缩放——只动定义值。
        values["integrity"] = max(1, round(values["integrity"] * self._enemy_integrity_mult()))
        values.update(overrides)
        enemy = self.add_enemy(x=x, y=y, catalog_id=catalog_id, **values)
        from .main_difficulty import active_profile
        if active_profile(self):
            enemy.active_skill_state["max_integrity"] = enemy.integrity
        enemy.biological_tags = tuple(definition.get('biological_tags', ()))
        if definition.get('final_realm_stats'):
            enemy.active_skill_state['max_integrity'] = enemy.integrity
        enemy.home_x, enemy.home_y = x, y  # 折返跑者等「回出生点」机制用
        # 核心执念恒显（2026-09-22）：剧情实体永远看得见，所在格视为在视野中。
        enemy.always_visible = definition.get("anomaly_kind") == "核心执念"
        enemy.glyph = entity_glyph(definition["glyph"])
        if enemy.trait == "patrol":
            enemy.route = self._build_patrol_route(enemy.x, enemy.y)
        return enemy

    def _build_patrol_route(self, x: int, y: int) -> list[tuple[int, int]]:
        """取以出生点为中心的一圈开放格作为楼梯回声的环形巡逻路线。"""
        ring: list[tuple[int, int]] = []
        for dx, dy in ((0, -2), (1, -2), (2, -1), (2, 0), (2, 1), (1, 2), (0, 2), (-1, 2), (-2, 1), (-2, 0), (-2, -1), (-1, -2)):
            nx, ny = x + dx, y + dy
            if 0 < nx < self.width - 1 and 0 < ny < self.height - 1 and not self.cell(nx, ny).solid:
                ring.append((nx, ny))
        if len(ring) < 2:
            ring = [(x, y)]
        return ring

    def _resolve_enemy(self, enemy: Entity, *, half_reward: bool = False) -> None:
        """异象死亡结算（掉落/奖励/洞察）。

        [SFX挂点] 异象崩解死亡：建议 enemy_die（怪物生灵\creature_die_1）；
        core 纯逻辑，播放挂 UI 层（enemies 数量 diff），见《音效挂点索引.md》。
        """
        if enemy.drop_spawned:
            return
        from .main_difficulty import active_profile
        if (active_profile(self) and self.depth == 27 and enemy.integrity <= 0
                and enemy.catalog_id == "anomaly.first_cry"):
            self.run_stats["main_core_defeated"] = 1
        from .hospital_scenes import on_hospital_defeat
        on_hospital_defeat(self, enemy)
        if enemy.catalog_id == 'library.core':
            from .library_content import on_defeat
            on_defeat(self, enemy)
        # 解决事实（§13.3 remove）：谁真的把这一位从地图上抹掉了。玩家发起的
        # 击杀沿用「全额崩解」那条归因旗标；环境杀不写 actor_uid，责任不可归属
        # 给玩家（§4.4「环境来源不可归属」），但记录仍然留下，供任务与调查读。
        from ..world import facts as world_facts
        from ..world import relations

        attributed = bool(getattr(self, "_kill_full_reward", False)) and not half_reward
        world_facts.record(self, "remove",
                           actor_uid=relations.player_uid(self) if attributed else "",
                           target_uid=enemy.actor_uid or enemy.id,
                           position=(enemy.x, enemy.y), cause_uid=enemy.catalog_id or "",
                           source_kind="direct_attack" if attributed else "environment",
                           before="存活", after="移除")
        if enemy.catalog_id=='anomaly.scribe':
            self._scribe_defeated(enemy)
        # 主动技能召唤的无奖励残影：直接消散——无掉落、无崩解奖励、
        # 不计击杀、不进图鉴（见 core/enemy_skills.py::_sk_spawn_summon）。
        if (enemy.active_skill_state or {}).get("summon_no_reward"):
            enemy.drop_spawned = True
            self.messages.append(tr("{label}的残影散成了纸屑。", label=tr(enemy.label)))
            return
        # 玩偶意识体（教学层）：不产 loot、不进图鉴、不计击杀，登记原地重生。
        if enemy.relation == "玩偶意识体":
            self._schedule_doll_respawn(enemy)
            self.messages.append(tr("玩偶意识体散成一地纸屑——它过一会儿会重新叠好自己。"))
            return
        # 核心执念必掉「洞察之镜」：使用后三选一获得洞察，选完消耗。
        if (enemy.anomaly_kind == '核心执念'
                and not ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get('final_realm_stats')):
            from .entities import WorldItem as _WorldItem
            self.world_items.append(_WorldItem(self._make_item("mirror_of_insight"), enemy.x, enemy.y))
            self.messages.append(tr("核心执念的残骸里凝出一面「洞察之镜」。"))
        if enemy.catalog_id == "anomaly.core_y2k_worm" and self.realm_id == "millennium_garden":
            # 千年虫停机（§10.3 通关）：宽带圣杯走终端「关机」选项的 reward 管线
            #（行囊满时拒绝结算、可再来）——不走地面掉落，避免 realm 快照里丢奖励。
            enemy.drop_id = ""
            for terminal_event in self.events:
                if terminal_event.event_id == "event.millennium_terminal":
                    terminal_event.name = "停机的主机"
                    terminal_event.description = "屏幕黑了，只余一行小字：现在可以安全地关闭计算机了。"
                    terminal_event.options = (
                        {'label': '关掉它（通关离开）', 'exit_realm': 'clear',
                         'reward_id': 'broadband_grail'},
                    )
            self.messages.append(tr("千年虫蜷缩成一串乱码，主机「嗒」地停了机。"))
        if enemy.relation == "失控意识":
            self.run_stats["kills"] = self.run_stats.get("kills", 0) + 1
            self.kills_by_kind[enemy.catalog_id] = self.kills_by_kind.get(enemy.catalog_id, 0) + 1
            # 梦中梦（2026-09-21）：累计击败 20 个强烈异象，掉落「门之钥」
            #（每局一把，使用不消耗——钥匙本身就是反复开关的门）。
            if (not self.key_dropped
                    and ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get("anomaly_kind") == "强烈异象"):
                self.strong_kills += 1
                if self.strong_kills >= 20:
                    from .entities import WorldItem as _WorldItem
                    self.world_items.append(
                        _WorldItem(self._make_item("door_key"), enemy.x, enemy.y))
                    self.key_dropped = True
                    self.messages.append(tr(
                        "第 20 个强烈异象崩解了——它的残骸里留下一把冰冷的「门之钥」。"))
        # 循迹重生（纸页犬）：被解决后有 40% 概率在远处重新凝聚（耐久 1）。
        if (enemy.trait == "respawner"
                and self._natural_anomaly_count() < ANOMALY_REFRESH_ACTIVE_CAP
                and random.Random(self.seed ^ (self.time * 17) ^ stable_token(enemy)).random() < 0.4):
            import random as _r
            far = [
                (x, y)
                for y in range(2, self.height - 2)
                for x in range(2, self.width - 2)
                if not self.cell(x, y).solid
                and max(abs(x - self.player.x), abs(y - self.player.y)) >= 8
                and self.entity_at(x, y) is None
            ]
            if far:
                nx, ny = far[_r.Random(self.seed ^ self.time).randrange(len(far))]
                revived = self.add_defined_enemy("anomaly.page_hound", nx, ny, integrity=1)
                revived.drop_spawned = True
                self.messages.append(tr("远处的纸页又翻动起来——纸页犬重新凝聚了。"))
        # 初啼（初啼之核）：受到致命创伤时发出啼哭，惊动整层失控意识。
        if enemy.trait == "burst_liquid" and enemy.integrity <= 0:
            # 碎瓶：脚下 3×3 爆出黑墨（迟滞），站位惩罚。
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = enemy.x + dx, enemy.y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and not self.cell(nx, ny).solid:
                        self._add_liquid(self.cell(nx, ny), "黑墨", 24)
            self.messages.append(tr("墨水瓶碎了——黑墨溅了一地。"))
        if enemy.trait == "cry_alert" and enemy.integrity <= 0:
            for other in self.enemies:
                if other is not enemy and other.integrity > 0 and other.relation == "失控意识":
                    other.alert_state = "追踪"
            self.messages.append(tr("一声啼哭响彻整层梦——所有异象都听见了。"))
        full = getattr(self, "_kill_full_reward", False)
        self._kill_full_reward = False  # 读完即复位：下一次环境击杀回落减半
        # 玩家视野内的击杀一律全额：环境效果在你眼前杀死的异像也照常计入，
        # 只有视野外的环境击杀才减半（四舍五入）。
        if half_reward or (not full and not self.is_visible(enemy.x, enemy.y)):
            reward = (enemy.dissolution_reward + self._effect_power("coin_bonus") + 1) // 2
        else:
            reward = enemy.dissolution_reward + self._effect_power("coin_bonus")
        # 心智失序档额外掉落（扩展：心智越低异象崩解产物越丰富）。
        drop_bonus = {0: 0, 1: 4, 2: 3, 3: 2}.get(self.mind_tier, 0)
        if drop_bonus:
            reward += reward // drop_bonus
        if not self.realm_id:
            self._add_dissolution(reward)
        # 双重曝光：本体死亡时分身同步消散（分身无掉落、不再给奖励）。
        if enemy.trait == "split_main":
            for phantom in self.enemies:
                if phantom.trait == "phantom" and phantom.main_id == enemy.id and phantom.integrity > 0:
                    phantom.integrity = 0
                    phantom.drop_spawned = True
            self.messages.append(tr("本体崩解，它的残影随之褪成空白。"))
        # 强力异象首次解决 → 通过掉落通道授予对应洞察（同名不可重复）。
        # 强力异象洞察改为概率授予（18%）：更稀有；失败可由后续同种击杀重试
        # （未标记 resolved_kinds）。常规异象不掉落洞察。
        # 45% → 18%（2026-09-15 玩家反馈「强烈异象的掉落洞察率偏高」）：
        # 洞察总量本就受 INSIGHT_LIMIT 约束，掉落太密只会让每次击杀都弹提示。
        definition = ANOMALY_DEFINITIONS.get(enemy.catalog_id)
        # 世纪清算（扩展包 v2）：击破千禧园异象额外恢复 6 点想象力。
        if (
            self.realm_id == "millennium_garden"
            and self.insight_active("世纪清算")
            and getattr(enemy, "anomaly_kind", "") in ("普通异象", "强烈异象", "核心执念")
        ):
            gain = 6
            self.restore_resource('imagination', gain)
            self.messages.append(tr("世纪清算：过期的系统被你结清了（想象力 +{n}）。", n=gain))
        enemy_number = int(enemy.id.rsplit("-", 1)[-1]) if "-" in enemy.id else 0
        if (
            definition and definition.get("insight_id")
            and enemy.catalog_id not in self.resolved_kinds
            and random.Random(self.seed ^ (self.time * 31) ^ enemy_number).random() < 0.18
        ):
            self.resolved_kinds.add(enemy.catalog_id)
            self._grant_insight(definition["insight_id"])
        self._spawn_enemy_drop(enemy)
        from .main_difficulty import refresh_progress_site
        refresh_progress_site(self)

    def _spawn_enemy_drop(self, enemy: Entity) -> None:
        if enemy.drop_spawned:
            return
        enemy.drop_spawned = True
        # 专属召唤异象（混乱/篡改召来，见 core.chaos_anomalies）：不留任何物品。
        # 这里只补一条图鉴击杀记录；崩解奖励与击杀统计仍由 _resolve_enemy 的其他
        # 分支处理，也不消耗本层掉落预算。
        if bool((enemy.active_skill_state or {}).get("no_loot")):
            self._record_catalog_kill(enemy, [])
            return
        actual_drops: list[str] = []
        # 本层后期补刷的掉落倍率（2026-10-27）：首波/非补刷（wave=0）与前
        # ANOMALY_REFRESH_FREE_DROP_WAVES 只补刷都是 1.0（与旧版逐位一致），
        # 此后按 ANOMALY_REFRESH_DROP_DECAY 指数衰减。
        multiplier = _late_spawn_drop_multiplier(enemy)
        # 携带意象掉落：强烈异象/核心执念概率更高，普通异象小概率；
        # 受本层掉落预算（携带意象类）约束。放在普通掉落之前，无遗留物的
        # 强力异象同样可能留下携带意象。
        enemy_number = int(enemy.id.rsplit("-", 1)[-1]) if "-" in enemy.id else 0
        # 2026-09-18 下调：核心执念 0.35 / 强烈异象 0.12 / 普通 0.02
        # （旧 0.6/0.25/0.05 配合稀有度体系后装备产出过量）。
        drop_chance = {"核心执念": 0.35, "强烈异象": 0.12}.get(enemy.anomaly_kind, 0.02)
        equip_rng = random.Random(self.seed ^ (self.time * 104729) ^ enemy_number)
        budget_key = f"{self.depth}:{CARRIED_IMAGE}"
        if equip_rng.random() < drop_chance * multiplier and (
            self.layer_drop_counts.get(budget_key, 0) < 1 or (self.time + enemy_number) % 4 == 0
        ):
            self.layer_drop_counts[budget_key] = self.layer_drop_counts.get(budget_key, 0) + 1
            # 区域分层池（2026-10-07）：此前任何深度都只掉浅层 EQUIPMENT_POOL，
            # 25 层的强烈异象也会掉「削尖的钢笔」。改按层取池，与房间刷新同源。
            equip_pool = equipment_pool_for_depth(self.depth)
            equip_pool = tuple(key for key in equip_pool
                               if not ITEM_DEFINITIONS.get(key, {}).get('expansion_catalog_id'))
            equip_id = equip_pool[equip_rng.randrange(len(equip_pool))]
            self.world_items.append(WorldItem(self._make_item(equip_id), enemy.x, enemy.y))
            actual_drops.append(equip_id)
        # 书卷/残页：强力异象更高概率掉落。
        scroll_chance = {"核心执念": 0.3, "强烈异象": 0.12}.get(enemy.anomaly_kind, 0.0)
        if equip_rng.random() < scroll_chance * multiplier:
            scroll_id = "spellbook" if equip_rng.random() < 0.4 else "torn_page"
            self.world_items.append(WorldItem(self._make_item(scroll_id), enemy.x, enemy.y))
            actual_drops.append(scroll_id)
        if not enemy.drop_id:
            self._record_catalog_kill(enemy, actual_drops)
            return
        # 固定掉落（定义里 drop_id 的「必掉」）：后期补刷先按倍率过一道随机。
        # multiplier >= 1.0（首波/前几次补刷）时不消耗随机数，仍然保持必掉。
        if multiplier < 1.0 and equip_rng.random() >= multiplier:
            self._record_catalog_kill(enemy, actual_drops)
            return
        from .item_access import refusal as item_grant_refusal, record_grant
        source = 'enemy:' + enemy.catalog_id
        if item_grant_refusal(self, enemy.drop_id, source=source):
            self._record_catalog_kill(enemy, actual_drops)
            return
        item = self._make_item(enemy.drop_id)
        budget_key = f"{self.depth}:{item.category}"
        produced = self.layer_drop_counts.get(budget_key, 0)
        budget = 2 if item.category == CARRIED_IMAGE else 3 if item.category in ("摄入物", "易逝物", "交互道具") else 1
        enemy_number = int(enemy.id.rsplit("-", 1)[-1]) if "-" in enemy.id else 0
        # 核心执念的专属掉落**不受每层同类预算限制**（2026-09-18）：它是那层唯一的
        # 战利品，被配额吞掉就等于白打一场硬仗（预算本是为了防止普通异象刷爆同层）。
        if enemy.anomaly_kind != "核心执念":
            if produced >= budget and (self.time + enemy_number) % 4 != 0:
                self._record_catalog_kill(enemy, actual_drops)
                return
            self.layer_drop_counts[budget_key] = produced + 1
        record_grant(self, item.definition_id, source=source)
        self.world_items.append(WorldItem(item, enemy.x, enemy.y))
        actual_drops.append(item.definition_id)
        if (enemy.catalog_id == "anomaly.stair_echo"
                and (self.time + enemy_number) % 5 == 0
                and _late_spawn_bonus_ok(equip_rng, multiplier)):
            bonus = self._make_item("attic_dust")
            self.world_items.append(WorldItem(bonus, enemy.x, enemy.y))
            actual_drops.append(bonus.definition_id)
            self.messages.append(tr("{enemy}的台阶缝隙里落下了一撮阁楼的灰尘。", enemy=tr(enemy.label)))
        bonus_tier = self.mind_tier
        if (bonus_tier
                and (self.time + enemy_number) % 3 < bonus_tier
                and _late_spawn_bonus_ok(equip_rng, multiplier)):
            bonus = self._make_item("old_keycap")
            self.world_items.append(WorldItem(bonus, enemy.x, enemy.y))
            actual_drops.append(bonus.definition_id)
            self.messages.append(tr("失序档 {tier} 使 {enemy} 多留下了一枚脱落的键帽。", tier=bonus_tier, enemy=tr(enemy.label)))
        self._record_catalog_kill(enemy, actual_drops)
        self.messages.append(tr("{enemy}崩解，留下了 {item}。", enemy=tr(enemy.label), item=tr(item.name)))

    def _effective_attack_time(self, enemy: Entity) -> float:
        base = enemy.attack_time
        if enemy.trait == "choir":
            # 和声耐受降低敌方加速上限，不能反向强化合唱。
            adjacent = sum(
                1
                for other in self.enemies
                if other is not enemy and other.integrity > 0 and other.trait == "choir"
                and max(abs(other.x - enemy.x), abs(other.y - enemy.y)) == 1
            )
            cap = 0.4 if self.insight_active("和声耐受") else 0.5
            base = enemy.attack_time - min(cap, 0.1 * adjacent)
        if enemy.trait == "lighthouse" and self.light_turns > 0:
            base = min(base, 0.5)
        if self.depth <= 2 and enemy.anomaly_kind == "普通异象":
            base = max(1.5, base)
        # 攻击惩罚（醉意、酩酊……）：与玩家侧的 _portent_attack_penalty 同源。
        base += self._entity_portent_attack_penalty(enemy)
        # 行动速度倍率（加速 2 倍 → 攻击耗时减半）与玩家侧同一口径。
        scale = self._speed_scale(enemy.portents)
        return base / scale if scale > 0 else base

    def _entity_portent_attack_penalty(self, enemy: Entity) -> float:
        """异象身上由材料征兆带来的攻击惩罚（上限 1.0，避免彻底打不出手）。"""
        penalty = sum(
            portent_def(portent_id).attack_time
            for portent_id in enemy.portents
            if portent_def(portent_id) is not None
        )
        return min(1.0, penalty)

    def _entity_portent_extra_turn(self, enemy: Entity) -> int:
        """异象身上由征兆造成的额外沉眠回合（深眠 / 安眠香 / 褪黑素雾）。"""
        return min(PORTENT_EXTRA_TURN_CAP, sum(
            portent_def(portent_id).extra_turn
            for portent_id in enemy.portents
            if portent_def(portent_id) is not None
        ))

    def _entity_portent_move_penalty(self, enemy: Entity) -> float:
        """异象身上由材料征兆带来的移动惩罚（上限 0.8，避免被完全钉死）。

        水银已改为站位即触发（非征兆、不减速）：它只压低本格气体的触发
        浓度（见 portents._gas_portent_min），不再给移动追加惩罚。
        """
        ether = frozenset(('hospital_ether_liquid', 'hospital_ether_gas'))
        penalty = sum(
            portent_def(portent_id).move_time
            for portent_id in enemy.portents
            if portent_def(portent_id) is not None and portent_id not in ether
        )
        penalty += max((portent_def(pid).move_time for pid in ether if pid in enemy.portents), default=0)
        return min(0.5 if any(pid.startswith('hospital_') for pid in enemy.portents) else 0.8, penalty)

    def _effective_move_time(self, enemy: Entity) -> float:
        base = enemy.move_time
        if enemy.trait == "liquid_swimmer":
            # 纸鱼：液体格 0.6、干燥格 1.4。
            base = 0.6 if self.cell(enemy.x, enemy.y).liquid > 0 else 1.4
        if enemy.slow_turns > 0:
            base += 0.3
        # §12 H2 时缓区：同一格只叠一次本区修正，多个时缓区不叠加。
        try:
            from .construct_environments import active as _active_fields
            if any(field['kind'] == 'slow_zone'
                   and (enemy.x, enemy.y) in {tuple(p) for p in field['cells']}
                   for field in _active_fields(self)):
                base += 0.3
        except Exception:
            pass
        if "honeyed" in enemy.portents:
            base *= 2  # 蜂蜜：上方生物移速减半
        base += self._entity_portent_move_penalty(enemy)
        # 植物地形：拦慢追兵对异象同样成立（磁带须/装订须/缝线丛/千禧蒲草）。
        base += self.plant_move_penalty_at(enemy.x, enemy.y)
        key = str(self.depth)
        if (enemy.x, enemy.y) in self.slick_cells.get(key, set()):
            base += 0.4
        watch = self.equipment.find_effect("slow_aura")
        if watch and max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 3:
            base += 0.2
        # 行动速度倍率（加速 2 倍 → 移动耗时减半）与玩家侧同一口径。
        scale = self._speed_scale(enemy.portents)
        return base / scale if scale > 0 else base

    def _effective_vision(self, enemy: Entity) -> int:
        vision = enemy.vision
        # §22 D：已审核种类的显式基础视距；实例被测试/脚本单独改过时沿用实例值。
        from ..data.perception import perception_profile
        profile = perception_profile(getattr(enemy, "catalog_id", ""))
        if profile is not None and profile.vision is not None:
            default = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""), {}).get("vision")
            if default is None or enemy.vision == default:
                vision = profile.vision
        # 分类聚合（docs 261022 §14.1）：正修正 → 同族平减 → 比例缩视 → 致盲覆盖，
        # 与玩家侧共用 `_vision_profile`，不会一边登记一边漏。
        sight = self._vision_profile(enemy)
        vision += sight.positive
        # 开局选项「百目紧盯」：异象视野 +2（正面阶段，与降噪同通道）。
        vision += self._alert_bonus()
        vision += sight.flat
        if sight.blur:
            vision = max(vision + sight.blur, min(sight.blur_floor, vision))
        if sight.blinds:
            # 致盲只归零普通视觉：听觉、守卫与不依赖视觉的合法技能照常（§14.2）。
            return 0
        ratio = sight.ratio
        if enemy.blind_turns > 0:
            # 旧闪光保留「半视野」，与新比例取最小值而不是相乘。
            ratio = min(ratio, 0.5)
        # §11：声音类装备不串进视觉通道，单边耳机的收益在自身声径上结算。
        return max(0, int(max(0, vision) * ratio))

    # §11 H1：声音大类只用于线索措辞，不改变敌方听觉几何。
    def _listen_cap(self) -> int:
        """玩家能听见多远：基础曼哈顿 12 格，碎片可延长；不扩大声源本身。"""
        return max(0, 12 + self.memory_stat_bonus("listen"))

    def _consume_sound_preparations(self, x: int, y: int, category: str) -> None:
        """真实发声才消耗准备：预览只读，读档与开面板不会刷掉次数。"""
        if (x, y) != (self.player.x, self.player.y):
            return
        if category == "step" and self._masked_step_active():
            self.masked_step_until = 0
        if category != "lure" and self._echo_ward_active():
            self.echo_ward_until = 0

    def _maybe_grant_masked_step(self, x: int, y: int, radius: int, *, field=None) -> None:
        """借声藏步：自身格以外的实际声音至少 6 格且覆盖玩家时给一份掩护。"""
        if not self.insight_active("借声藏步"):
            return
        if (x, y) == (self.player.x, self.player.y) or radius < 6:
            return
        from .acoustics import propagate, residual_at
        if field is None:
            field = propagate(self, x, y, radius)
        if residual_at(field, self.player.x, self.player.y) < self._listen_threshold():
            return
        self.masked_step_until = max(self.masked_step_until, self.time + 2)

    def _clue_retention(self) -> int:
        """听觉线索保留的真实回合数（含记录当回合），基础 2。"""
        return max(1, 2 + self.memory_stat_bonus("clue_retention"))

    def _wall_sense_entry(self, field, x: int, y: int) -> tuple[int, int] | None:
        """凝听且带听诊器时，声音穿过哪面相邻实墙进入（docs 261022 §16.4）。

        只读玩家贴着的相邻墙格，并检查这面墙确实带余量、声源位于墙外侧；
        不返回声源坐标，也不扫描更远的墙，悬停无法借此查询整张地图。
        """
        if field is None or not self._listen_active():
            return None
        if not (self.insight_active("wall_sense")
                or self._effect_power("wall_sense") > 0):
            return None
        best = None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            wx, wy = self.player.x + dx, self.player.y + dy
            if not self.inside_board(wx, wy):
                continue
            cell = self.cell(wx, wy)
            if not cell.solid or str(cell.wall_kind) == "沉思铁幕":
                continue
            # 声源必须在这面墙的外侧，且声音确实到达墙面。
            if (x - wx) * dx + (y - wy) * dy <= 0 or (wx, wy) not in field:
                continue
            rank = ((x - wx) * dx + (y - wy) * dy, int(field[(wx, wy)]), wx, wy)
            if best is None or rank > best[0]:
                best = (rank, (wx, wy))
        return best[1] if best else None

    def _record_hearing_clue(self, x: int, y: int, category: str,
                             source: str, radius: int, field=None,
                             residual: int | None = None,
                             relay: tuple[int, int] | None = None) -> None:
        """把一次真实脉冲记成玩家可见的粗略线索。

        已知位置与未知声源分开：未知只给八方位扇区与距离档，不写坐标、
        敌名或隐藏人数；同回合同类同向同档的重复声音聚合为一条。
        主动凝听并带听诊器时，穿过相邻实墙的声音额外记下入口墙格；
        只有真实近距（≤3）才附「近距」判断，远墙不靠悬停全图查询。

        ``relay`` 是「这一声是被传声筒转过来的」那个**入口**坐标（见
        ``_sound_pulse`` 的转发链）。它照记不误，但只有洞察「一声两种来处」
        才去读（面板与等待时的读取都另按洞察判），所以关掉洞察时这条字段是死的。
        """
        if radius <= 0:
            return
        dx, dy = x - self.player.x, y - self.player.y
        distance = abs(dx) + abs(dy)
        if distance == 0:
            return
        reach = radius + (2 if self._listen_active() else 0)
        if distance > min(reach, self._listen_cap()):
            return
        retention = self._clue_retention()
        clues = self.heard_sound_clues
        clues[:] = [clue for clue in clues
                    if self.time - int(clue.get("time", 0)) < retention]
        known = bool(self.is_visible(x, y))
        sector = sound_sector(dx, dy)
        band = sound_band(distance)
        strength = sound_strength(residual) if residual is not None else None
        entry = self._wall_sense_entry(field, x, y)
        relayed = (int(relay[0]), int(relay[1])) if relay else None
        key = (sector, band, strength, category, source, known,
               x if known else None, y if known else None, entry, relayed)
        for clue in clues:
            if int(clue.get("time", -1)) != self.time:
                continue
            other = (clue.get("sector"), clue.get("band"), clue.get("strength"),
                     clue.get("category"),
                     clue.get("source"), clue.get("known"),
                     clue.get("x") if clue.get("known") else None,
                     clue.get("y") if clue.get("known") else None,
                     tuple(clue["entry"]) if clue.get("entry") else None,
                     tuple(clue["relay"]) if clue.get("relay") else None)
            if other == key:
                # 同区域多次响动只做提示，不累计成敌人数（§16.2）。
                if (int(clue.get("x", -1)), int(clue.get("y", -1))) != (x, y):
                    clue["multiple"] = True
                return
        clue = dict(time=self.time, x=x, y=y, sector=sector, band=band,
                    category=category, source=source, known=known)
        if self._sound_bearing_active():
            clue["fine_sector"] = fine_sound_sector(dx, dy)
        if strength is not None:
            clue["strength"] = strength
        if entry is not None:
            clue["entry"] = entry
            clue["wall_near"] = distance <= 3
        if relayed is not None:
            clue["relay"] = [int(relayed[0]), int(relayed[1])]
        clues.append(clue)

    def _note_listen_evidence(self, x: int, y: int, category: str,
                              source: str, residual: int) -> None:
        """听界与循声定位的精确声源记账（docs 261022 §16.4）。

        只处理实际传到玩家、且不超出听界的余量；普通听觉仍只拿粗略线索。
        """
        distance = abs(x - self.player.x) + abs(y - self.player.y)
        if distance <= 0 or distance > self._listen_cap():
            return
        from ..data.perception import (CONFIRMED_SOURCE_RESIDUAL,
                                       CONFIRMED_SOURCE_RETENTION,
                                       LISTEN_REALM_TURNS)
        if self.time < self.listen_realm_until:
            markers = self.precise_sound_markers
            if not any(m.get('x') == x and m.get('y') == y
                       and int(m.get('time', -1)) == self.time
                       and m.get('category') == category for m in markers):
                markers.append(dict(x=x, y=y, time=self.time,
                                    category=category, source=source))
            markers[:] = [m for m in markers
                          if self.time - int(m.get('time', 0)) < LISTEN_REALM_TURNS]
        if not (self._listen_active() and self.insight_active('循声定位')):
            return
        if residual < CONFIRMED_SOURCE_RESIDUAL:
            return
        sightings = self.sound_sightings
        sightings[:] = [s for s in sightings
                        if self.time - int(s.get('time', 0)) <= 8]
        if not any(s.get('x') == x and s.get('y') == y
                   and int(s.get('time', -1)) == self.time for s in sightings):
            sightings.append(dict(x=x, y=y, time=self.time))
        times = {int(s.get('time', 0)) for s in sightings
                 if s.get('x') == x and s.get('y') == y}
        if len(times) < 2:
            return
        entry = next((c for c in self.confirmed_sound_sources
                      if (c.get('x'), c.get('y')) == (x, y)), None)
        if entry is None:
            entry = dict(x=x, y=y)
            self.confirmed_sound_sources.append(entry)
        entry['time'] = self.time
        self.confirmed_sound_sources[:] = [
            c for c in self.confirmed_sound_sources
            if self.time - int(c.get('time', 0)) < CONFIRMED_SOURCE_RETENTION]

    def _sound_radius(self, x: int, y: int, base: int, category: str = "generic") -> int:
        return self._sound_radius_breakdown(x, y, base, category=category)[0]

    def _step_noise_breakdown(self, x: int, y: int, *, expose_kind: bool = True):
        """真实落脚的基础声径：地板足音与液面接触声取较大值，不叠加。

        口径与 docs 261022 §6.2 一致；返回的 sources 只解释这一次取值。
        视野外预览只给“液体”类别，不泄漏未知液体的具体种类。
        """
        cell = self.cell(x, y)
        floor = floor_effect_for(cell)
        base = max(0, int(floor.footstep))
        sources: list[str] = []
        if cell.liquid > 0:
            liquid = liquid_contact_noise(cell.liquid_kind)
            if liquid > base:
                base = liquid
                name = tr(cell.liquid_kind) if expose_kind else tr('液体')
                sources.append(tr("踩入{name}：液面接触 {n}", name=name, n=liquid))
        return base, sources

    def _plant_step_quiet(self, x: int, y: int) -> int:
        """这一格上的植物能压掉多少格脚步声（0–1，同类取最强）。

        低草只压本格；留白絮压 R1；月光蕈只在本格没有机械照明时生效——
        「亮灯反制」是设计的一部分，不能因为站在旁边就永远听不见。
        """
        from ..materials import plant_def_for, plant_step_quiet
        best = 0
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 0
        cell = self.cell(x, y)
        if cell.plant:
            definition = plant_def_for(cell.plant)
            quiet = plant_step_quiet(cell.plant)
            if quiet and (not definition.step_quiet_dark or not self._cell_is_lit(x, y)):
                best = max(best, quiet)
        for ny in range(max(0, y - 1), min(self.height, y + 2)):
            for nx in range(max(0, x - 1), min(self.width, x + 2)):
                if (nx, ny) == (x, y):
                    continue
                defender = self.cells[ny][nx].plant
                if not defender:
                    continue
                definition = plant_def_for(defender)
                if not definition.step_quiet or definition.step_quiet_radius < 1:
                    continue
                if definition.step_quiet_dark and self._cell_is_lit(nx, ny):
                    continue
                best = max(best, definition.step_quiet)
        return min(1, best)

    def _cell_is_lit(self, x: int, y: int) -> bool:
        from .vision.glow import lit as _lit
        try:
            return bool(_lit(self, x, y))
        except Exception:
            return False

    def _emit_step_noise(self, positions, *, emitter: Entity | None = None,
                         by_player: bool = False) -> None:
        """一次真实接触地面的移动，在每个新落脚点各发一次足音。

        同格的重复落脚只发一次；飞行、传送、悬浮等位移不经过这里。
        """
        seen: set[tuple[int, int]] = set()
        for x, y in positions:
            if (x, y) in seen:
                continue
            seen.add((x, y))
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            base, _ = self._step_noise_breakdown(x, y)
            if emitter is not None and emitter.anomaly_kind == "强烈异象":
                base += 1
            # 植物消音：最低到 0（真的没有声音），不与「脚步准备」那条通道
            # 相加——地表给的压制只取最强一次。
            #
            # 2026-10-26 用户实测：踏入时的「减声括号／慢行缠线」提示动画观感差、
            # 又只是把格子详情里已有的数字再演一遍，已整体下线（连同装饰层轻摆）。
            # 减声与加时本身照旧结算，只是不再有那层字。
            quiet = self._plant_step_quiet(x, y)
            base = max(0, base - quiet)
            if base <= 0:
                continue
            self._step_noise_reduction = self._step_noise_reduction_for(x, y)
            try:
                self._sound_pulse(x, y, base, by_player=by_player,
                                  category="step", source=tr("脚步"),
                                  announce=False, emitter=emitter,
                                  triggers_rewards=False)
            finally:
                self._step_noise_reduction = 0

    def _quiet_step_charges_active(self) -> bool:
        return self.quiet_step_charges > 0 and self.time < self.quiet_step_until

    def _masked_step_active(self) -> bool:
        return self.time < self.masked_step_until

    def _echo_ward_active(self) -> bool:
        return self.time < self.echo_ward_until

    def _sound_bearing_active(self) -> bool:
        return self.time < self.sound_bearing_until

    def _listen_active(self) -> bool:
        """凝听状态：本次等待及其后一个真实回合。"""
        return self.time < self.listen_until

    def _listen_threshold(self) -> int:
        """玩家接收阈值：普通 0，凝听 −4（约多听 2 格，不放大声源）。"""
        return -4 if self._listen_active() else 0

    def _terrain_snapshot_matches(self, x: int, y: int) -> bool:
        """这一格是否有完整地形快照且当前地形仍与之相符。

        只认普通探索/光照记录下来的 ``TerrainMemory``；显影集合、全图地形
        增强与纯声向轮廓都不算（§11 §7 足音消音）。
        """
        from .vision.knowledge import remembered_terrain
        snapshot = remembered_terrain(self, x, y)
        if snapshot is None:
            return False
        cell = self.cell(x, y)
        floor = str(getattr(cell.floor, 'value', cell.floor) or '')
        elevation = int(getattr(cell, 'elevation', 0) or 0)
        return (snapshot.floor == floor
                and snapshot.solid == bool(getattr(cell, 'solid', False))
                and snapshot.wall_kind == str(getattr(cell, 'wall_kind', '') or '')
                and snapshot.aggregate_variant == str(getattr(cell, 'aggregate_variant', '') or '')
                and (snapshot.elevation is None or snapshot.elevation == elevation))

    def _step_noise_reduction_for(self, x: int, y: int) -> int:
        quiet = 2 if self._quiet_step_charges_active() and self.insight_active('无声步') else 0
        if self.insight_active('足音消音') and self._terrain_snapshot_matches(x, y):
            quiet += 1
        # 悄声无息（quiet_steps，2026-10-22 实装）：旧耳机的线圈 / 没有日期的车票。
        # 只压自身脚步与普通道具声径，实际声径的最低值仍由调用方钳在 1。
        quiet += self._effect_power("quiet_steps")
        return quiet

    def _sound_radius_breakdown(self, x: int, y: int, base: int,
                                category: str = "generic", *,
                                emitter=_AUTO_SOUND_EMITTER) -> tuple[int, list[str]]:
        """声音传播半径 + 每个生效修正的可读来源（噪音可读性，docs §16.3）。

        返回 ``(radius, sources)``：sources 是按应用顺序排列的修正说明，
        口径与本函数的实际计算完全一致（UI 显示不另算一套）。
        """
        sources: list[str] = []
        if base <= 0:
            return 0, sources
        if emitter is _AUTO_SOUND_EMITTER:
            emitter = self.player if (x, y) == (self.player.x, self.player.y) else None
        if emitter is self.player:
            quiet = int(getattr(self, '_step_noise_reduction', 0))
            if quiet:
                base = max(1, base - quiet)
                sources.append(tr('脚步准备 −{n}', n=quiet))
            # 单边耳机：只压自身脚步与普通道具声径，不碰诱引/爆炸，不改视觉。
            if category in ("step", "item") and self.equipment.find_effect("noise_cut"):
                base = max(1, base - 2)
                sources.append(tr('单边耳机 −2'))
            # §11 §9：收音机里的雨只压自身脚步与普通道具的基础声径，
            # 不碰主动诱引与爆炸，也不改异象视野；普通降噪最低为 1。
            noise = self.memory_stat_bonus("noise")
            if noise > 0 and category in ("step", "item"):
                base = max(1, base - noise)
                sources.append(tr('雨声的遮蔽 −{n}', n=noise))
            # §11 §8：借声藏步在基础减免之后乘 0.5，最低 1；环境倍率随后照常。
            if category == "step" and self._masked_step_active():
                base = max(1, base * 0.5)
                sources.append(tr('借声藏步 ×0.5'))
            # §12 H2 静默协议：只封顶自身脚步与普通道具的基础声径，
            # 环境倍率（回声雾/瓷墙/征兆/地板）仍在之后照常生效。
            if (self.ability_turns.get("mute_protocol")
                    and category in ("step", "item") and base > 1):
                base = 1
                sources.append(tr('静默协议 →1'))
        # 回声雾不再放大源点（docs 261022 §5.2）：它只把途经传播边的成本
        # 2→1，延长有限声路；同一材料不得在源侧与路径侧双算。主体「回声」
        # 征兆仍在这里按倍率放大，两者是不同物理环节。
        radius = base
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < self.width and 0 <= ny < self.height and self.cell(nx, ny).wall_kind == "尖啸瓷墙":
                radius *= 2
                sources.append(tr("紧邻尖啸瓷墙 ×2"))
                break
        if emitter is not None:
            ward = emitter is self.player and self._echo_ward_active() and category != "lure"
            multiplier = self._portent_sound_multiplier(
                ignore_echoing=ward, holder=emitter, category=category)
            if multiplier != 1:
                radius *= multiplier
                sources.append(tr("回声 ×{multiplier}", multiplier=multiplier))
            elif ward and "echoing" in emitter.portents:
                sources.append(tr('噪声耐受：本次不放大'))
        # Source material applies to every subject; iron blocks actual paths only.
        reduction = floor_effect_for(self.cell(x, y)).sound_reduction
        if reduction:
            radius = max(1, radius - reduction)
            floor_name = self.cell(x, y).aggregate_variant or self.cell(x, y).floor.value
            sources.append(tr("{name} −{reduction}", name=tr(floor_name), reduction=reduction))
        import math
        return math.ceil(radius), sources

    def _pulse_radius_breakdown(self, x: int, y: int, base: int, *,
                                by_player: bool = False,
                                category: str = "generic",
                                emitter=_AUTO_SOUND_EMITTER) -> tuple[int, list[str]]:
        """Final pulse range shared by actual emitters and their previews."""
        radius, sources = self._sound_radius_breakdown(x, y, base, category=category, emitter=emitter)
        if radius <= 0:
            return 0, sources
        if by_player and category == 'lure':
            # §11 §7：蜂鸣回响只放大主动诱引，不放大脚步与爆炸；
            # 广播加成可在洞察详情关闭，关闭后不再报价。
            if self.insight_active('蜂鸣回响') and getattr(self, 'buzzing_echo_enabled', True):
                radius += 2
                sources.append(tr('蜂鸣回响 +2'))
            # §11 §9：忙音的间距只对基础大于 0 的真实诱引生效，同类取高。
            lure_bonus = self.memory_stat_bonus("lure_radius")
            if lure_bonus > 0:
                radius += lure_bonus
                sources.append(tr('忙音的间距 +{n}', n=lure_bonus))
        if by_player and self.insight_active('深渊回声') and self.depth >= 21:
            radius += 2
            sources.append(tr('深渊回声 +2'))
        return radius, sources

    def _sound_pulse(self, x: int, y: int, radius: int, freeze_near: int = 0,
                     by_player: bool = False, full_alert: bool = False,
                     category: str = "generic", source: str = "",
                     triggers_rewards: bool = True, announce: bool = True,
                     emitter: Entity | None = None,
                     affect_enemies: bool = True,
                     chain: bool = False,
                     relay: tuple[int, int] | None = None) -> None:
        """声波脉冲（docs §16.4 距离梯度）：两档听觉反应。

        - 内圈 ``≤ ⌈radius/2⌉``：未察觉/怀疑 → 追踪（原口径），freeze_near
          震停也只作用于内圈；
        - 外圈（内圈外、≤ radius）：未察觉 → 怀疑、怀疑 → 警戒，记声源为
          调查目标并前往；到达未发现后按既有降级口径（LOST_TARGET_TURNS /
          目击处降档）平息；
        - 已处于追踪态的异象不受梯度影响；
        - ``full_alert=True``：强诱引道具（汽笛等）全员内圈待遇，不被梯度削弱。
        """
        if not chain:
            from .expansion_abilities import intercept_delayed_sound
            if intercept_delayed_sound(self, x, y, radius, by_player=by_player,
                    category=category, source=source, freeze_near=freeze_near,
                    full_alert=full_alert, triggers_rewards=triggers_rewards,
                    announce=announce, affect_enemies=affect_enemies):
                return
        if emitter is None and by_player and (x, y) == (self.player.x, self.player.y):
            emitter = self.player
        # 扩展包声源装备（2026-10-25）：空椅先吸一声、铁漏斗/指挥棒改向，
        # 全部在既有传播之前完成；chain=True 表示这一声本身是转发或延迟重放，
        # 不再触发吸收、改向与分账（否则会自激）。
        from ..equipment import gear_tools
        if not chain and gear_tools.absorb_into_chair(self, x, y, radius, category, source):
            return
        if not chain and by_player and category == "lure":
            x, y, radius = gear_tools.redirect_lure(self, x, y, radius)
            # 「返场」重放的是这一声**实际**落点（齿轮改向之后），不是玩家点的坐标；
            # 重放本身（chain）不改写记录，否则一次诱引能被返场无限续命。
            self.last_lure = {"x": int(x), "y": int(y), "radius": int(radius),
                              "full_alert": bool(full_alert),
                              "turn": int(getattr(self, "time", 0) or 0),
                              "depth": int(getattr(self, "depth", 0) or 0)}
        radius, _ = self._pulse_radius_breakdown(x, y, radius, by_player=by_player,
                                                 category=category, emitter=emitter)
        # 记忆碎片的缓冲（扩展包「地毯下的一粒沙」「门缝里的晚安」）：扣在**实际声径**
        # 上，否则瓷墙／回声的倍率会把「少一格」重新放大回去。
        # 转发/延迟重放（chain）不吃额度，否则一次碎裂能喂饱多条缓冲。
        if not chain and (by_player or emitter is self.player or (
                emitter is None and (x, y) == (self.player.x, self.player.y))):
            from . import memory_buffers
            radius = memory_buffers.reduce_noise(self, category, radius)
        if radius <= 0:
            return
        if not chain and by_player and category == "lure":
            gear_tools.schedule_echo(self, x, y, radius, source)
        if not chain:
            exit_point = gear_tools.pipe_exit(self, x, y)
            if exit_point is not None:
                # ``relay`` 记的是这一声**真正进来的那一头**（传声筒入口）：
                # 线索里留下它，洞察「一声两种来处」才能说明「原声不在这一头」。
                self._sound_pulse(exit_point[0], exit_point[1], radius,
                                  freeze_near=freeze_near, by_player=by_player,
                                  full_alert=full_alert, category=category,
                                  source=source, triggers_rewards=False,
                                  announce=False, emitter=None,
                                  affect_enemies=affect_enemies, chain=True,
                                  relay=(int(x), int(y)))
        # §22 C：一个声源只算一张最大余量声场，各接收者读取同一结果。
        from .acoustics import hears as _hears, propagate, residual_at
        from ..data.perception import perception_profile
        field = propagate(self, x, y, radius)
        # §11 H1：按真实声路登记玩家线索；没传到的声音不产生线索。
        # 凝听期间接收阈值 −4（docs 261022 §16.3），不放大声源本身。
        player_residual = residual_at(field, self.player.x, self.player.y)
        # 2026-10-25 噪音条：记录这次真实声场在玩家**周围区域**的强度，
        # 供状态栏显示「我附近有多吵」——来源可以是任何生物/环境，不必是自己。
        ambient = -10 ** 9
        for (ax, ay), remaining in field.items():
            if max(abs(ax - self.player.x), abs(ay - self.player.y)) <= NOISE_AMBIENT_RADIUS:
                ambient = max(ambient, int(remaining))
        events = getattr(self, "_ambient_noise_events", None)
        if events is None:
            events = []
            self._ambient_noise_events = events
        events[:] = [event for event in events
                     if self.time - int(event[0]) < NOISE_AMBIENT_TURNS]
        events.append((int(self.time), int(x), int(y), int(ambient),
                       int(player_residual), int(radius), bool(by_player),
                       str(category)))
        if len(events) > 64:
            del events[:-64]
        if player_residual >= self._listen_threshold():
            self._record_hearing_clue(x, y, category, source or category, radius,
                                      field=field, residual=player_residual,
                                      relay=relay)
            self._note_listen_evidence(x, y, category, source or category, player_residual)
        if emitter is self.player:
            self._consume_sound_preparations(x, y, category)
        if (not by_player and category=='lure' and (x,y)!=(self.player.x,self.player.y)
                and player_residual>=self._listen_threshold() and self._masked_step_active()):
            from . import memory_buffers
            self.masked_step_until+=memory_buffers.spend(self,'preparation:masked_step')
        self._maybe_grant_masked_step(x, y, radius, field=field)
        inner = (radius + 1) // 2  # ⌈radius/2⌉
        reached = 0
        suspicious = 0
        for enemy in self.enemies:
            if not affect_enemies:
                # 独立召集（共鸣报警器）已经自行规划，物理鸣声只补玩家线索，
                # 不让同一事件被两种机制各规划／各奖励一次（docs 261022 §13.1）。
                break
            if (enemy.integrity <= 0 or enemy.trait in ("staircase",)
                    or enemy.relation != '失控意识' or enemy is emitter):
                continue
            distance = abs(enemy.x - x) + abs(enemy.y - y)
            catalog_id = getattr(enemy, "catalog_id", "")
            profile = perception_profile(catalog_id)
            if profile is None or profile.hearing is None:
                # 2026-10-22 收口：已登记目录项没有听觉档案（楼梯／空白裂隙）时
                # 不再按半径圈兜底听声——仍由它们各自的特殊机制处理。
                if catalog_id in ANOMALY_DEFINITIONS:
                    continue
                # 旧档／测试夹具里的未知目录（不在图鉴）保留 §7「未审核项保留旧行为」
                # 的最小半径兜底；它不会被当成已登记种类的第二套听觉口径。
                if distance > radius:
                    continue
            elif not _hears(field, enemy.x, enemy.y, profile.hearing,
                            profile.threshold, origin=(x, y)):
                continue
            # §22 B：听觉是独立事实，不覆盖视觉 last_seen；调查任务按地点
            # 与来源去重，重复的静态声源不会堆积。
            enemy.last_heard_x, enemy.last_heard_y = x, y
            enemy.last_heard_time = self.time
            enemy.last_heard_category = category
            self._remember_investigation(enemy, x, y, "hearing", category)
            if full_alert or distance <= inner:
                # 内圈（或强诱引）：惊醒并前来。
                reached += 1
                if enemy.alert_state in ("未察觉", "怀疑", "警戒"):
                    enemy.alert_state = "追踪"
            else:
                # 外圈：低警觉升一档并前来调查；追踪态保持不变。
                if enemy.alert_state == "未察觉":
                    enemy.alert_state = "怀疑"
                    suspicious += 1
                elif enemy.alert_state == "怀疑":
                    enemy.alert_state = "警戒"
                    suspicious += 1
            if freeze_near and distance <= min(freeze_near, inner):
                enemy.frozen_turns = max(enemy.frozen_turns, 1.0)
            # 当前确实看见目标时，普通噪音不把它从眼前目标引走。
            if self._enemy_sees_player(enemy):
                continue
            enemy.wandering = False
            # 同一地点的重复弱声只刷新任务，不每一步重规划。
            plan = enemy.path_plan
            if not (plan and plan[-1] == (x, y)):
                self._plan_chase(enemy, x, y)
        report_audible = (by_player or (player_residual >= self._listen_threshold()
                          and abs(x-self.player.x)+abs(y-self.player.y) <= self._listen_cap()))
        if announce and reached and report_audible:
            self.messages.append(tr("声波脉冲扫过，{count} 个失控意识听见了声源。", count=reached))
        if announce and suspicious and report_audible:
            self.messages.append(tr("{count} 个失控意识起了疑心，正在靠近声源。", count=suspicious))
        if radius > 0:
            # 声波（docs §16.3 可读性）：登记最近一次脉冲供 UI 做低频可视化。
            # 纯演出字段，不入存档（读档后自然消失）；seq 供 UI 差分去重。
            # UI receives only the small, actually heard patch. Tail-only waves
            # use a coarse local center instead of exposing the distant source.
            from .sound_visuals import heard_wave
            self._sound_pulse_seq = getattr(self, "_sound_pulse_seq", 0) + 1
            self.last_sound_pulse = {
                "seq": self._sound_pulse_seq,
                "x": x, "y": y, "radius": radius, "world_time": self.time,
                "by_player": bool(by_player),
                **heard_wave(self, field, x, y, by_player=by_player),
            }
        if by_player and triggers_rewards:
            if radius > 0:
                self.emit_board_event('voice', cell=(x,y), source_id=self.player.id,
                                      recipient_id='', amount=radius)
            # 回声控场（split_tuning_fork）：只有玩家亲手制造的声源才走
            # 「先引诱成功、下一次脉冲变控制」的两段式；异象自己的声响不算。
            # 外圈起疑也算被引诱（前往声源）——armed 口径随之放宽。
            self._echo_control_pulse(x, y, reached, suspicious)

    def _apply_enemy_portent_effects(self, enemy: Entity, cell: Cell, amount: int) -> None:
        """其他生物身上的材料征兆：周期性伤害 + 连续性灼伤/漏电。

        异象只有一条「完整度」，因此征兆的资源变化（mind / lucidity /
        imagination）一并折算成完整度伤害：只要沾着一条按周期扣资源（mind 或
        lucidity 或 imagination 为负）的征兆，就按其定义周期（下限为
        CREATURE_PORTENT_DAMAGE_PERIOD）扣完整度——这补上了灼热蒸汽与辐射病的
        一半。正向征兆不替异象回血（否则雾里站着的异象会打不死）。
        2026-10-07：折算量 = 最大单条负值 × 深度因子（向上取整），
        与玩家侧的深度连续函数同口径；同回合不同征兆只取最高单条伤害。
        减速 / 冻结 / 视野等连续效果不在这里，见 _effective_* 与 _enemy_turns。
        """
        # 各征兆保留自己的周期；同一回合只取最高伤害，避免混合环境叠乘。
        # 分步累计使批量推进与逐回合推进一致。沿用存档已有的 debt 字典。
        harmful = {}
        for portent_id in enemy.portents:
            definition = portent_def(portent_id)
            if definition is not None and definition.period > 0:
                harm = max(0, -definition.mind, -definition.lucidity, -definition.imagination)
                if harm:
                    harm = harm if portent_id == 'hospital_spore' else portent_scaled_amount(harm, self._portent_scale_depth())
                    harmful[portent_id] = (harm, definition.period if portent_id == 'hospital_spore' else max(CREATURE_PORTENT_DAMAGE_PERIOD, definition.period))
        for key in list(enemy.portent_debt):
            if key.startswith("__harm__:") and key[9:] not in harmful:
                enemy.portent_debt.pop(key)
        for _ in range(amount):
            due = 0
            for portent_id, (harm, period) in harmful.items():
                key = "__harm__:" + portent_id
                debt = enemy.portent_debt.get(key, 0.0) + 1
                if debt >= period:
                    debt -= period
                    due = max(due, harm)
                enemy.portent_debt[key] = debt
            if due:
                _damage_number_before = enemy.integrity
                enemy.integrity = max(0, enemy.integrity - due)
                from .hit_events import note_integrity_loss
                note_integrity_loss(self, enemy, _damage_number_before)
                enemy.alert_state = "追踪"
        # 连续性效果，与玩家侧同源：过电 + 脚下静电尘、可燃 + 紧邻火焰。
        if "charged" in enemy.portents and self._cell_holds_material(cell, "静电尘"):
            _damage_number_before = enemy.integrity
            enemy.integrity = max(0, enemy.integrity - amount)
            from .hit_events import note_integrity_loss
            note_integrity_loss(self, enemy, _damage_number_before)
            enemy.alert_state = "追踪"
        if "volatile" in enemy.portents:
            burning = any(
                self.cell(nx, ny).flame > 0
                for nx, ny in (
                    (enemy.x + 1, enemy.y),
                    (enemy.x - 1, enemy.y),
                    (enemy.x, enemy.y + 1),
                    (enemy.x, enemy.y - 1),
                )
                if 0 <= nx < self.width and 0 <= ny < self.height
            )
            if burning:
                _damage_number_before = enemy.integrity
                enemy.integrity = max(0, enemy.integrity - amount)
                from .hit_events import note_integrity_loss
                note_integrity_loss(self, enemy, _damage_number_before)
                enemy.alert_state = "追踪"

    # ------------------------------------------------------------------
    # 贴身打击：按客观时间蓄力，而不是按回合刻度采样
    # ------------------------------------------------------------------
    def _adjacent_to_player(self, enemy: Entity) -> bool:
        # 八向相邻：切比雪夫距离 1，斜向贴身同样算「贴上去」（与玩家攻击一致）。
        return max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) == 1

    def _spooked_flee_step(self, enemy: Entity) -> bool:
        """惊散移动（docs §15.5）：选使与玩家曼哈顿距离增大的可通行格。

        没有能拉开距离的格子（被堵在死角）返回 False——原地缩住，仍不攻击。
        """
        best: tuple[int, int] | None = None
        current = abs(enemy.x - self.player.x) + abs(enemy.y - self.player.y)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = enemy.x + dx, enemy.y + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            if self.cell(nx, ny).solid or self.entity_at(nx, ny) is not None:
                continue
            if abs(nx - self.player.x) + abs(ny - self.player.y) <= current:
                continue
            best = (nx, ny)
            break
        if best is None:
            return False
        enemy.x, enemy.y = best
        self._emit_step_noise([best], emitter=enemy)
        return True

    def _enemy_can_strike(self, enemy: Entity) -> bool:
        """该异象此刻是否具备贴身出手的资格。

        与 _enemy_turns 的前置跳过保持一致：被冻住的不出手，台阶与未察觉的
        人形衣架本就不参与攻击。
        """
        if enemy.integrity <= 0:
            return False
        if "spooked" in enemy.portents:
            # 惊散（docs §15.5，地图侧篡改「退散」）：征兆期间不攻击、不用技能。
            return False
        if enemy.relation != "失控意识":
            # 只有失控意识会出手：稳定意识（NPC）与玩偶意识体（教学层）都不还手。
            return False
        if self._enemy_control_active(enemy):
            return False
        if self._skill_channeling(enemy):
            # 主动技能蓄力/恢复中：贴身打击与起手互斥（双入口行动互斥）。
            return False
        if enemy.trait == "staircase":
            return False
        hides_like_disguise = enemy.trait == "disguise" or (
            enemy.trait == "gardener"
            and self.cell(enemy.x, enemy.y).plant == 2  # 站在高丛里即隐身
        )
        if hides_like_disguise and enemy.alert_state == "未察觉":
            return False
        return True

    def _enemy_control_active(self, enemy: Entity) -> bool:
        """精英/核心获得短控制窗口，之后有两回合恢复期，避免刷新式永久冻结。"""
        if enemy.anomaly_kind not in ("强烈异象", "核心执念"):
            return enemy.frozen_turns > 0
        now = self.time + self.round_debt
        until = enemy.portent_debt.get("__control_until__", -1.0)
        if now < until:
            return True
        if now < enemy.portent_debt.get("__control_ready__", -1.0):
            enemy.frozen_turns = 0.0
            return False
        if enemy.frozen_turns <= 0:
            return False
        duration = min(enemy.frozen_turns, CORE_CONTROL_WINDOW if enemy.anomaly_kind == "核心执念" else ELITE_CONTROL_WINDOW)
        enemy.frozen_turns = duration
        enemy.portent_debt["__control_until__"] = now + duration
        enemy.portent_debt["__control_ready__"] = now + duration + CONTROL_RECOVERY_ROUNDS
        return True

    def _apply_enemy_strike(self, enemy: Entity) -> None:
        """异象的一次贴身打击（格挡 / 挂载替身 / 扒窃 / 创伤四条分支）。

        [SFX挂点] 本函数四条分支各对应一个事件（core 纯逻辑，播放挂 UI 层，
        见《音效挂点索引.md》）：格挡→parry（玻璃/镜面质感）、挂载替身挡下→
        shield_block、扒窃→coin（金币落地）、末尾真实创伤→hurt（受击\hit_*）。
        调用方需已确认目标相邻、自身存活且 attack_clock 已扣减。
        """
        # 多段攻击（2026-09-22 修复）：段数 >1 时每段独立结算——镜面格挡与
        # 挂载替身各只挡一段，被挡一段不再让整次攻击落空（旧实现把段数只当
        # 乘法：折半×2 与单发等值，多段等于没有）。
        strike_stolen = False
        # 创伤量：定义表的 "power"（2026-09-18 全面上调并拉开差距）；
        # 旧档/未登记条目回落 1。
        power = 1
        definition = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""))
        if definition is not None:
            power = int(definition.get("power", 1))
        if enemy.active_skill_state.get('summon_no_reward'):
            power = int(enemy.active_skill_state.get('strike_power', power))
        from .main_difficulty import effective_melee_power
        power = effective_melee_power(self, enemy, power)
        # 开局选项「异象强度」：创伤倍率（至少 1 点）。织梦同调/回声学习等
        # 后续加值不吃倍率——它们是个体状态，不是定义强度。
        power = max(1, round(power * self._enemy_trauma_mult()))
        # 织梦同调（噩梦编织者）：身旁有同伴时创伤 +1。
        if any(
            other is not enemy and other.integrity > 0 and other.relation == "失控意识"
            and max(abs(other.x - enemy.x), abs(other.y - enemy.y)) <= 1
            for other in self.enemies
        ) and enemy.trait == "pack_weave":
            power += 1
        # 异象的贴身打击本身也有世界噪音：越重的一击传得越远。
        self._sound_pulse(enemy.x, enemy.y, 3 + min(3, power),
                          category="enemy_attack", source=tr(enemy.label),
                          announce=False, triggers_rewards=False)
        if getattr(self, "stasis_turns", 0) > 0:
            # 凝滞：时间在体表结成壳——创伤与附加征兆全部被吸收。
            self.messages.append(tr("凝滞的硬壳吸收了这一击。"))
            return
        # 回声抄写员：把你打它攒下的「学习」一次性倾泻。
        power += getattr(enemy, "echo_bonus", 0)
        enemy.echo_bonus = 0
        seg_count = int(definition.get("segments", 1) or 1) if definition else 1
        # 多段（噬念蠕虫/原初冲动）：每段创伤按 power 折半（至少 1），
        # 总量与单发持平；收益在「每段独立过防御与防具」。
        per_hit = max(1, power // 2) if seg_count > 1 else power
        landed = 0
        for _seg in range(seg_count):
            if not strike_stolen and enemy.trait == "cutpurse":
                # 扒窃（梦游裁缝）：整次攻击只偷一次。
                strike_stolen = True
                stolen = self._cutpurse_steal()
                if stolen:
                    self.messages.append(tr("{enemy}剪走了你的{stolen}，它掉在了你的脚下。", enemy=tr(enemy.label), stolen=tr(stolen)))
                    enemy.alert_state = "追踪"
                    return
            # 镜面格挡：每段各挡一次（反击震毙攻击者则剩余段作废）。
            if self.parry_charges > 0:
                self.parry_charges -= 1
                from .hit_events import note_hit
                note_hit(
                    self, kind="enemy_strike", source=(enemy.x, enemy.y),
                    impact=(self.player.x, self.player.y), target_id=self.player.id,
                    amount=0, resource="blocked", blocked=True,
                )
                if self.parry_charges <= 0:
                    # §17：次数型征兆真正用完，同样进入结束后保护。
                    self.parry_until = 0
                    self._remember_portent_end(self.player, "mirror_stance")
                reflect = 2 if self.insight_active("镜术精通") else 1  # 镜术精通：反伤 +1
                enemy.integrity = max(0, enemy.integrity - reflect)
                self.messages.append(tr("镜面碎片把 {enemy} 的打击原路退了回去。", enemy=tr(enemy.label)))
                if enemy.integrity <= 0:
                    self._resolve_enemy(enemy)
                    return
                continue
            # 挂载替身：每段各挡一次。
            if self.hang_item_id and any(entry.instance_id == self.hang_item_id for entry in self.inventory):
                hung = next(entry for entry in self.inventory if entry.instance_id == self.hang_item_id)
                self.inventory.remove(hung)
                self.hang_item_id = None
                self._refresh_hang()
                from .hit_events import note_hit
                note_hit(
                    self, kind="enemy_strike", source=(enemy.x, enemy.y),
                    impact=(self.player.x, self.player.y), target_id=self.player.id,
                    amount=0, resource="blocked", blocked=True,
                )
                self.messages.append(tr("打击落在了挂着的{hung}上，替你挡下了这次创伤。", hung=tr(hung.name)))
                enemy.alert_state = "追踪"
                continue
            trauma = per_hit if enemy.trauma_type == "心智创伤" else 0
            lucidity_trauma = per_hit if enemy.trauma_type == "清醒创伤" else 0
            # 携带意象护甲：打补丁的睡衣/皮革围裙 各自减免对应创伤（逐段）。
            # 2026-10-22：护甲改为"减免后至少 1"——否则聚合四舍五入抬高护甲后，
            # 深层普通异象 5–6 点创伤会被 6 点护甲完全归零，防御件变成无条件免疫。
            raw_trauma, raw_lucidity = trauma, lucidity_trauma
            trauma = max(0, trauma - self._effect_power("mind_armor") - self._effect_power("dual_armor"))
            lucidity_trauma = max(0, lucidity_trauma - self._effect_power("lucidity_armor") - self._effect_power("dual_armor"))
            if raw_trauma > 0:
                trauma = max(1, trauma)
            if raw_lucidity > 0:
                lucidity_trauma = max(1, lucidity_trauma)
            # 伤口结痂（扩展包 v1）：单段 ≥9 时超出 9 的部分减半。
            if self.insight_active("伤口结痂"):
                if trauma >= 9:
                    trauma = 9 + (trauma - 9) // 2
                if lucidity_trauma >= 9:
                    lucidity_trauma = 9 + (lucidity_trauma - 9) // 2
            before_mind, before_lucidity = self.mind, self.lucidity
            self._identity_direct_trauma(enemy, trauma, lucidity_trauma)
            lost_mind = max(0, before_mind - self.mind)
            lost_lucidity = max(0, before_lucidity - self.lucidity)
            if lost_mind or lost_lucidity:
                from .hit_events import note_hit
                note_hit(
                    self, kind="enemy_strike", source=(enemy.x, enemy.y),
                    impact=(self.player.x, self.player.y), target_id=self.player.id,
                    amount=lost_mind + lost_lucidity,
                    resource="mind" if lost_mind else "lucidity",
                    origin=enemy.anomaly_kind or enemy.label,
                    damage_type=enemy.trauma_type,
                    killed=bool(self.run_over),
                )
                if "电" not in str(getattr(enemy, "trauma_type", "")):
                    from ..equipment.expansion_runtime import reactive_field
                    field_cells = reactive_field(self, enemy)
                    if field_cells:
                        self.messages.append(tr("反扣的接地腕带沿导电介质接通了 {n} 格电场。",
                                                n=field_cells))
            landed += 1
            if self.run_over:
                # 玩家已沉没：不再结算剩余段。
                return
        if landed == 0:
            # 整次攻击全部被挡下：不算真实命中（与旧单段被挡行为一致）。
            return
        if enemy.trait == 'hospital_retreat':
            candidates = [(enemy.x+dx, enemy.y+dy) for dx, dy in
                          ((-1, 0), (1, 0), (0, -1), (0, 1))]
            candidates.sort(key=lambda p: (-max(abs(p[0]-self.player.x), abs(p[1]-self.player.y)), p))
            for x, y in candidates:
                if (self._sk_open(x, y) and self.entity_at(x, y) is None
                        and max(abs(x-self.player.x), abs(y-self.player.y)) > 1
                        and not self.cell(x, y).flame):
                    enemy.x, enemy.y = x, y
                    enemy.path_plan, enemy.plan_index = [], 0
                    break
        if seg_count > 1:
            self.messages.append(tr("它一连击中了 {n} 次。", n=landed))
        # ---- 命中附加征兆（改造 v2：on_hit_portent，时长以字段为准）----
        if definition and definition.get("on_hit_portent"):
            spec = definition["on_hit_portent"]
            pid, duration = spec["id"], int(spec.get("duration", 8))
            if self._apply_direct_portent(self.player, pid, duration):
                self.messages.append(tr("命中附加：{name}（{n} 回合）。", name=pid, n=duration))
        # 无字校对员：命中后随机「涂黑」你一条已习得构想（5 回合不可用）。
        # （已被主动技能绑定的异象停用旧命中行为，避免双结算。）
        if not self._uses_active_skills(enemy) and enemy.trait == "redact" and self.abilities:
            import random as _random
            rng = _random.Random(self.seed ^ (self.time * 977) ^ stable_token(enemy))
            blacked = rng.choice(list(self.abilities))
            self.redacted_abilities[blacked] = 5
            self.messages.append(tr("它涂掉了你的一个构想——墨迹 5 回合后才干透。"))
        # 查票员：25% 概率没收 1 件未装备的易逝物（掉在它脚下）。
        if not self._uses_active_skills(enemy) and enemy.trait == "toll_check":
            import random as _random
            rng = _random.Random(self.seed ^ (self.time * 131) ^ stable_token(enemy))
            if rng.random() < 0.25:
                from .entities import WorldItem as _WorldItem
                fares = [i for i, it in enumerate(self.inventory)
                         if it.category == "易逝物"]
                if fares:
                    idx = fares[rng.randrange(len(fares))]
                    taken = self.inventory.pop(idx)
                    self.world_items.append(_WorldItem(taken, enemy.x, enemy.y))
                    self.messages.append(tr("{enemy}没收了你的{item}——票根掉在它脚下。", enemy=tr(enemy.label), item=tr(taken.name)))
        # ---- 命中附加（2026-09-19）----
        if not self._uses_active_skills(enemy) and enemy.trait == "pusher":
            # 顺势推挤（模型搬运工）：33% 概率把你沿攻击方向推开一格。
            import random as _random
            push_rng = _random.Random(self.seed ^ (self.time * 31) ^ stable_token(enemy))
            if push_rng.random() < 0.33:
                dx = (self.player.x > enemy.x) - (self.player.x < enemy.x)
                dy = (self.player.y > enemy.y) - (self.player.y < enemy.y)
                nx, ny = self.player.x + dx, self.player.y + dy
                if (
                    (dx or dy)
                    and 0 <= nx < self.width and 0 <= ny < self.height
                    and not self.cell(nx, ny).solid and self.entity_at(nx, ny) is None
                ):
                    self.player.x, self.player.y = nx, ny
                    self.messages.append(tr("你被推开了！"))
        if enemy.trait == "mind_drain":
            # 噬念蠕虫：命中时抽走 2 点想象力。
            from .settlement import REASON_COMBAT, settle_delta
            settle_delta(self, 'imagination', -2, reason=REASON_COMBAT,
                         source=str(getattr(enemy, 'label', '噬念蠕虫')))
            self.messages.append(tr("它咬走了一点想象力（−2）。"))
        if not self._uses_active_skills(enemy) and enemy.trait == "forget_touch":
            # 遗忘织者：命中时随机驱散你的一个正面征兆。
            positive = [
                pid for pid, turns in self.portents.items() if turns > 0
                and portent_def(pid) is not None and portent_def(pid).kind == "正面"
            ]
            if positive:
                import random as _random
                lost = positive[_random.Random(self.seed ^ self.time).randrange(len(positive))]
                self._remember_portent_end(self.player, lost)
                self.messages.append(tr("它让你忘掉了一种感觉：{portent} 被驱散。", portent=tr(portent_def(lost).name)))
        self.messages.append(tr("{enemy}造成了{trauma}。", enemy=tr(enemy.label), trauma=tr(enemy.trauma_type)))
        # 结算统计：一次真实命中（格挡/挂载替身/扒窃都已提前 return）。
        self.run_stats["hits_taken"] = self.run_stats.get("hits_taken", 0) + 1
        # 死因跟踪：记录最后一次真实命中玩家的来源（旧梦回忆的死亡归因）。
        self.last_harm_source = enemy.label
        self.last_harm_time = self.time
        enemy.alert_state = "追踪"

    def _charge_adjacent_attacks(self, dt: float) -> None:
        """把一段客观时间计入驻足在身边的异象的攻击计时，够了立刻出手。

        旧实现只在「回合刻度落下的那一刻恰好相邻」才蓄力，并且一旦刻度落在
        拉开距离的那一步就把 attack_clock 清零。高速行动（每步只花不到 1 回合）
        正好可以把刻度甩到「已经撤开」的那一步，于是贴脸打完就撤能完全不挨打
        ——速度从「攻防都占优」变成「单向无敌」。改成按客观时间计费、且不再
        清零之后：贴身的时间不够就是攒不满，攒下的零头也不会被丢掉。速度依然
        有用（贴身窗口更短、挨打更少），但收益变成有界的，而不是无敌。

        dt 是这一段行动真实流逝的回合数（0.5、1、2……皆可），与 time 的整数
        刻度无关；免费行动（dt=0）不推进世界，自然也不给蓄力。
        """
        if dt <= 0:
            return
        for enemy in self.enemies:
            if not self._enemy_can_strike(enemy) or not self._adjacent_to_player(enemy):
                continue
            enemy.attack_clock += dt
            attack_time = self._effective_attack_time(enemy)
            while (
                enemy.attack_clock + 1e-9 >= attack_time
                and self._adjacent_to_player(enemy)
                and enemy.integrity > 0
            ):
                enemy.attack_clock -= attack_time
                enemy.attack_pending = True
                self._apply_enemy_strike(enemy)
                attack_time = self._effective_attack_time(enemy)
        # 亚回合行动可能一道回合刻度都不跨（_advance 不会被调用），致命一击的
        # 终局判定不能只挂在 _advance 的收尾里。
        self._check_run_over()

    def _enemy_turns(self, amount: int) -> None:
        # §9 短时预约只在当前这次异象行动内有效：每回合开头清空，
        # 既不写存档，也不会把整条长路径永久占住。
        self.nav_slot_claims = {}
        # §5.1 / §9 非攻击格的短时预约与攻击位同生命周期：同样是「本回合谁站哪」。
        self.nav_hold_claims = {}
        # 主动技能效果场与召唤寿命：每回合在主循环前统一结算一次。
        self._enemy_skill_fields_tick(amount)
        # 时间偷取（改造 v2）：空白裂隙（相邻）/ 梦的账房（警戒中）把你每回合
        # 的行动上限压到 2——离开范围即刻恢复。
        self.steal_cap = 0
        for enemy in self.enemies:
            if enemy.integrity <= 0 or enemy.relation != "失控意识":
                continue
            mode = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""), {}).get("time_steal")
            if not mode:
                continue
            near = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 1
            if (mode == "adjacent" and near) or (mode == "alert" and enemy.alert_state != "未察觉"):
                self.steal_cap = 2
        # ---- 匿踪只遮蔽视觉：既有声源/目击调查照常继续，不在这里重置警戒。----
        # ---- 主循环：每个失控意识正常行动（冻结/警戒/追击/攻击）----
        for enemy in self.enemies:
            if enemy.integrity <= 0:
                continue
            if enemy.relation == "稳定意识":
                # 稳定意识（NPC）：不参与异象回合——不挪步、不攻击、不被锁定。
                continue
            # §22 B：调查任务按世界回合过期；读档不重抽、不延长。
            self._prune_investigations(enemy)
            if enemy.relation == "玩偶意识体":
                # Tutorial targets are fixed props, including while spooked.
                enemy.move_clock = 0.0
                enemy.path_plan.clear()
                continue
            if "spooked" in enemy.portents:
                # 惊散（docs §15.5，地图侧篡改「退散」）：不索敌、不攻击、
                # 不用技能，每步选择使与玩家距离增大的可通行格；无路可退
                # 时原地缩住（仍不攻击）。受击解除在玩家攻击结算处。
                enemy.move_clock += amount
                move_time = self._effective_move_time(enemy)
                while enemy.move_clock + 1e-9 >= move_time:
                    enemy.move_clock -= move_time
                    if not self._spooked_flee_step(enemy):
                        break
                continue
            # ---- 主动技能（2026-10-08）：数据层绑定的异象走新机制 ----
            # 已绑定主动技能的异象：停用旧周期技能/旧 trait 主动行为，避免双结算；
            # 真正被动（taunt/tracker/paper_fold/liquid_swimmer/disguise/patrol/
            # cutpurse 等）保留。
            uses_active_skills = self._uses_active_skills(enemy)
            # ---- 周期技能（2026-09-19）：已被主动技能绑定的异象停用 ----
            if enemy.anomaly_kind == "核心执念" and not uses_active_skills:
                self._core_actives(enemy, amount)
            if not uses_active_skills and enemy.trait == "drum_alert" and self.time % 6 == 0 and enemy.alert_state != "未察觉":
                # 倒放鼓手的敲击：9×9 内的异象被告知你的位置。
                alerted = 0
                for other in self.enemies:
                    if other is enemy or other.integrity <= 0 or other.relation != "失控意识":
                        continue
                    if max(abs(other.x - enemy.x), abs(other.y - enemy.y)) <= 4:
                        other.alert_state = "追踪"
                        alerted += 1
                if alerted:
                    self.messages.append(tr("远处传来倒放的鼓点——{n} 只异象循声而动。", n=alerted))
            if not uses_active_skills and enemy.trait == "echo_pulse" and self.time % 7 == 0 and enemy.alert_state != "未察觉":
                for other in self.enemies:
                    if other is enemy or other.integrity <= 0 or other.relation != "失控意识":
                        continue
                    if max(abs(other.x - enemy.x), abs(other.y - enemy.y)) <= max(4, enemy.vision):
                        other.alert_state = "追踪"
            if not uses_active_skills and enemy.trait == "self_revise" and self.time % 5 == 0:
                cap = int(ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get("integrity", enemy.integrity))
                if enemy.integrity < cap:
                    enemy.integrity = min(cap, enemy.integrity + 1)
            if not uses_active_skills and enemy.trait == "author_pace" and enemy.catalog_id!='anomaly.scribe' and self.time % 8 == 0:
                from .settlement import REASON_COMBAT, settle_delta
                settle_delta(self, 'imagination', -2, reason=REASON_COMBAT,
                             source='执笔者')
                self.messages.append(tr("执笔者删去了你两笔想象力。"))
            # 材料征兆：身处液体/气体中的异象同样会被赋予，并在这里冻结 / 衰减。
            enemy_cell = self.cell(enemy.x, enemy.y)
            self._clear_sleep_portents(enemy, enemy.x, enemy.y)
            self._lead_shield(enemy, enemy.x, enemy.y)
            self._cleanse_material_portents(enemy, enemy_cell)
            self._grant_material_portents(enemy, enemy_cell)
            self._tick_hospital_contact(enemy, amount)
            self._apply_enemy_portent_effects(enemy, enemy_cell, amount)
            if enemy.portents.get('sk_rooted',0)>0:
                enemy.active_skill_state['rooted_turn']=self.time
            else:
                enemy.active_skill_state.pop('rooted_turn',None)
            self._tick_entity_portents(enemy, enemy_cell, amount)
            if enemy.integrity <= 0:
                self._resolve_enemy(enemy)
                continue
            # 额外沉眠（深眠 / 安眠香 / 褪黑素雾）：异象同样被冻住。
            # +1 是因为紧随其后的冻结计时会立刻扣掉当回合的 amount——
            # 不补这一回合，extra_turn=1 的征兆就等于完全没冻结（深眠原本
            # 写死的 2.0 正对应 extra_turn 1 + 1）。
            extra_turn = self._entity_portent_extra_turn(enemy)
            if extra_turn > 0:
                enemy.frozen_turns = max(enemy.frozen_turns, float(extra_turn) + 1.0)
            # 致盲／迟滞按真实时间流逝，先于冻结与一切行动入口结算：正在蓄力、
            # 被冻住、没有移动或连续施法都不能把计时卡住（docs 261022 §14.2、
            # AI §12 P0／P5）。新致盲走征兆统一时钟（_tick_entity_portents 已在上
            # 面），这里处理仍保留半视野口径的旧闪光计时。
            if enemy.blind_turns > 0:
                enemy.blind_turns = max(0.0, enemy.blind_turns - amount)
            if enemy.slow_turns > 0:
                enemy.slow_turns = max(0.0, enemy.slow_turns - amount)
            if self._enemy_control_active(enemy):
                enemy.frozen_turns = max(0.0, enemy.frozen_turns - amount)
                enemy.attack_clock = 0.0
                enemy.attack_pending = False
                continue
            # ---- 主动技能回合入口：消耗行动（起手/结算）后不再普攻/移动 ----
            if uses_active_skills and self._enemy_active_skills(enemy, amount):
                continue
            if not uses_active_skills and enemy.trait == "staircase":
                self._staircase_turn(enemy, amount)
                continue
            if not uses_active_skills and enemy.trait == "lighthouse":
                self._lighthouse_turn(enemy, amount)
            if not uses_active_skills and enemy.trait == "split_main":
                self._split_phantom_chance(enemy)
            if not uses_active_skills and enemy.trait == "clock_pulse":
                enemy.pulse_clock += amount
                if enemy.pulse_clock >= 12:
                    enemy.pulse_clock -= 12
                    _def = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""), {})
                    base = _def.get("pulse_radius", 8)
                    self._sound_pulse(enemy.x, enemy.y, base)
            if not uses_active_skills and enemy.trait == "snooze_pulse":
                # 失眠的闹钟：每 8 回合响铃（半径 4）——唤醒被冻结/迟滞的异象
                # 并把它们召向铃声（优先击杀沉睡目标的反制手段）。
                enemy.pulse_clock += amount
                if enemy.pulse_clock >= 8:
                    enemy.pulse_clock -= 8
                    woken = 0
                    for other in self.enemies:
                        if other is enemy or other.integrity <= 0:
                            continue
                        if max(abs(other.x - enemy.x), abs(other.y - enemy.y)) > 4:
                            continue
                        if getattr(other, "frozen_turns", 0) > 0 or getattr(other, "slow_turns", 0) > 0:
                            other.frozen_turns = 0
                            other.slow_turns = 0
                            other.alert_state = "追踪"
                            other.last_seen_x, other.last_seen_y = enemy.x, enemy.y
                            other.wandering = False
                            self._plan_chase(other, enemy.x, enemy.y)
                            woken += 1
                    if woken:
                        self.messages.append(tr("闹钟炸响——{n} 个沉睡的异象被震醒了！", n=woken))
            if not uses_active_skills and enemy.trait == "boomerang":
                # 折返跑者：每 3 回合无条件瞬移回出生点（脱离战斗）。
                enemy.pulse_clock += amount
                if enemy.pulse_clock >= 3:
                    enemy.pulse_clock -= 3
                    home_x = getattr(enemy, "home_x", enemy.x)
                    home_y = getattr(enemy, "home_y", enemy.y)
                    enemy.x, enemy.y = home_x, home_y
                    continue  # 脱离战斗：本回合不再追击/移动
            if not uses_active_skills and enemy.trait == "pull":
                # 深渊量尺：每 5 回合把玩家向它拉近 2 格（撞墙停下）。
                enemy.pulse_clock += amount
                if enemy.pulse_clock >= 5:
                    enemy.pulse_clock -= 5
                    for _ in range(2):
                        dx = (enemy.x > self.player.x) - (enemy.x < self.player.x)
                        dy = (enemy.y > self.player.y) - (enemy.y < self.player.y)
                        if dx == 0 and dy == 0:
                            break
                        nx = self.player.x + (dx or 0)
                        ny = self.player.y + (dy if not dx else 0)
                        if (0 <= nx < self.width and 0 <= ny < self.height
                                and not self.cell(nx, ny).solid and self.entity_at(nx, ny) is None):
                            self.player.x, self.player.y = nx, ny
                        else:
                            break
                    self.messages.append(tr("深渊收拢了它的量尺——你被拉近了。"))
            # 盆栽看守：经过的低草长成高丛。
            if enemy.trait == "gardener" and self.cell(enemy.x, enemy.y).plant == 1:
                self.cell(enemy.x, enemy.y).plant = 2
            # 回声抄写员：与玩家上一次移动同向挪一格（可通行时）。
            if not uses_active_skills and enemy.trait == "echo_copy" and getattr(self, "_last_player_move", None):
                dx, dy = self._last_player_move
                nx, ny = enemy.x + dx, enemy.y + dy
                if (0 <= nx < self.width and 0 <= ny < self.height
                        and not self.cell(nx, ny).solid and self.entity_at(nx, ny) is None):
                    enemy.x, enemy.y = nx, ny
            # 异象技能 v3（2026-09-22）：定义表驱动的远程/范围/地形技能
            # （原长镜头导演的凝视打击已迁移为通用 ranged 技能）。
            # 已被主动技能绑定的异象停用旧技能组，避免双结算。
            if not uses_active_skills:
                self._enemy_skills(enemy, amount)
            # 伪装中的人形衣架静止不动，被玩家贴近后显形。
            if enemy.trait == "disguise" and enemy.alert_state == "未察觉":
                if max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 2:
                    enemy.alert_state = "怀疑"
                    self.messages.append(tr("一件家具在你面前展开了轮廓——是人形衣架！"))
                continue
            enemy.move_clock += amount
            # 贴身出手已由 _charge_adjacent_attacks 按「客观时间」蓄力结算；这里
            # 只消费「本回合已出手」的标记，并兜底结算外部直接写满 attack_clock
            # 的情形（测试与剧情脚本会这么做）。
            attack_time = self._effective_attack_time(enemy)
            attacked = enemy.attack_pending
            enemy.attack_pending = False
            while enemy.attack_clock + 1e-9 >= attack_time and self._adjacent_to_player(enemy) and enemy.integrity > 0:
                enemy.attack_clock -= attack_time
                attacked = True
                self._apply_enemy_strike(enemy)
            if attacked:
                continue
            move_steps = 0
            move_time = self._effective_move_time(enemy)
            while enemy.move_clock + 1e-9 >= move_time and move_steps < 4:
                enemy.move_clock -= move_time
                move_steps += 1
                if not self._enemy_move_step(enemy):
                    enemy.move_clock = 0
                    break
            if self._enemy_sees_player(enemy):
                # 看得见：刷新最后目击位置，并清空「失去目标」的计时。
                if (enemy.last_seen_x, enemy.last_seen_y) != (self.player.x, self.player.y):
                    # §8.1：只保留上一次真实目击，供一格预判使用。
                    enemy.last_seen_prev_x, enemy.last_seen_prev_y = (
                        enemy.last_seen_x, enemy.last_seen_y)
                enemy.last_seen_x, enemy.last_seen_y = self.player.x, self.player.y
                enemy.last_seen_time = self.time
                enemy.lost_sight_turns = 0.0
                # §22 4.2：明确看见即进入视觉追击，不再固定等两轮警戒升级。
                enemy.alert_state = "追踪"
                if enemy.alert_state in ("警戒", "追踪"):
                    self._propagate_alert(enemy)
                    # 实时追击：以玩家当前位置为终点重新规划最短路径。
                    # 玩家每动一步都会在下一次感知时改道；中途丢失视野则
                    # 保留本计划，沿剩余路径走向最后一次目击处（见
                    # core/pathing/pursuit.py），走到终点没发现就转入游荡。
                    self._plan_chase(enemy, self.player.x, self.player.y)
            elif enemy.alert_state == "追踪":
                # 失去视野：连续超过 LOST_TARGET_TURNS 回合就丢掉原目标——
                # 降级回「怀疑」，改去最后一次目击处，不再沿实时位置紧咬。
                enemy.lost_sight_turns += amount
                if enemy.lost_sight_turns > LOST_TARGET_TURNS:
                    enemy.alert_state = "怀疑"
                    enemy.lost_sight_turns = 0.0
                    self.messages.append(tr("{enemy}失去了你的踪迹。", enemy=tr(enemy.label)))
            # §22 B：从合法位置看清调查点却没发现目标 → 该线索可排除。
            self._check_investigation_completion(enemy)
        # 落点炸弹：引信按回合递减，归零当场爆炸（与异象个体行动解耦）。
        self._tick_enemy_bombs(amount)
        # 异象移动/死亡后刷新门：踩上门的异象使其打开，离开或死亡的使其关闭。
        self._update_doors()

    # ------------------------------------------------------- 异象技能 v3

    def _skill_specs(self, enemy: Entity) -> tuple[dict, ...]:
        definition = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""), {})
        return tuple(definition.get("skills") or ())

    def _enemy_skill_spec(self, enemy: Entity, kind: str) -> dict:
        for spec in self._skill_specs(enemy):
            if spec.get("kind") == kind:
                return spec
        return {}

    def _skill_anchor(self, enemy: Entity, anchor: str) -> tuple[int, int]:
        """技能锚点：self = 自身所在格；hunt = 最后目击玩家的位置（没有则自身）。"""
        if anchor == "hunt" and enemy.last_seen_x >= 0:
            return enemy.last_seen_x, enemy.last_seen_y
        return enemy.x, enemy.y

    def _skill_trauma(self, enemy: Entity, power: int) -> None:
        """远程/震波命中的统一结算：携带意象护甲减免 → 创伤 → 命中记账。"""
        from .main_difficulty import effective_skill_power
        power = effective_skill_power(self, enemy, power)
        trauma = power if enemy.trauma_type == "心智创伤" else 0
        lucidity_trauma = power if enemy.trauma_type == "清醒创伤" else 0
        raw_trauma, raw_lucidity = trauma, lucidity_trauma
        trauma = max(0, trauma - self._effect_power("mind_armor") - self._effect_power("dual_armor"))
        lucidity_trauma = max(0, lucidity_trauma - self._effect_power("lucidity_armor") - self._effect_power("dual_armor"))
        if raw_trauma > 0:
            trauma = max(1, trauma)
        if raw_lucidity > 0:
            lucidity_trauma = max(1, lucidity_trauma)
        self._identity_direct_trauma(enemy, trauma, lucidity_trauma)
        if trauma or lucidity_trauma:
            self.run_stats["hits_taken"] = self.run_stats.get("hits_taken", 0) + 1
            self.last_harm_source = enemy.label
            self.last_harm_time = self.time

    @staticmethod
    def _enemy_skill_noise(kind: str, spec: dict) -> int:
        base = {
            "ranged": 6, "aoe_burst": 8, "ignite": 5, "bomb": 6,
            "clear_terrain": 5, "erode_walls": 7, "emanate": 4,
        }.get(kind, 5)
        return max(3, min(12, base + max(0, int(spec.get("radius", 0) or 0))))

    def _emit_enemy_skill_noise(self, enemy: Entity, kind: str, spec: dict) -> None:
        self._sound_pulse(enemy.x, enemy.y,
                          self._enemy_skill_noise(kind, spec),
                          category="enemy_skill", source=tr(enemy.label),
                          announce=False, triggers_rewards=False)

    def _enemy_skills(self, enemy: Entity, amount: int) -> None:
        """异象技能 v3（2026-09-22）：定义表 "skills" 驱动的周期技能组。

        - **ranged**：远程打击——警戒 + 视线 + 距离 (1, range] → 创伤；
        - **aoe_burst**：范围爆发——警戒且进入施法距离就蓄力 windup 回合
          （蓄力期经 :meth:`skill_telegraphs` 渲染预警范围），到点以蓄力
          锚点（自身所在格）为心震荡 radius 圈；玩家在圈内吃创伤；
        - **ignite**：纵火——周期性点燃锚点（self=自身 / hunt=最后目击格）
          周边；点燃走 ``_ignite_cell`` 统一入口（可燃气够浓会气爆）；
        - **bomb**：投掷——朝玩家当前位置抛一份引信炸弹，落点杀伤区预警，
          引信归零由 :meth:`_tick_enemy_bombs` 统一引爆；
        - **clear_terrain**：地形改造——抽干身边 (2r+1)² 的气体与液体；
        - **erode_walls**：范围蚀墙——周期性削减身边墙体完整度，归零即塌；
        - **emanate**：呼出——在身边制造特定气体/液体（地图上直接可见）。

        计时挂在 ``enemy.skill_clocks["s{下标}"]``；条件不满足时计时封顶在
        every（条件一满足立刻触发，但不会连发）。战斗类技能只在警戒态
        触发；冻结的异象走不到这里（调用点在冻结跳过之后）。
        """
        specs = self._skill_specs(enemy)
        if not specs and enemy.aoe_charge <= 0:
            return
        alert = enemy.alert_state != "未察觉"
        px, py = self.player.x, self.player.y
        for index, spec in enumerate(specs):
            kind = spec.get("kind", "")
            key = f"s{index}"
            # ---- 蓄力中的范围技能：优先倒计时，本技能不再攒新计时 ----
            if kind == "aoe_burst" and enemy.aoe_charge > 0:
                enemy.aoe_charge -= amount
                if enemy.aoe_charge <= 0:
                    enemy.aoe_charge = 0.0
                    self._detonate_aoe_burst(enemy, spec)
                continue
            clock = enemy.skill_clocks.get(key, 0.0) + amount
            every = float(spec.get("every", 5))
            if clock < every:
                enemy.skill_clocks[key]=clock
                continue
            fired = False
            if kind == "ranged":
                dist = max(abs(enemy.x - px), abs(enemy.y - py))
                fired = (
                    alert and 1 < dist <= int(spec.get("range", 4))
                    and self._has_line_of_sight(enemy.x, enemy.y, px, py)
                )
                if fired:
                    self._enemy_ranged_hit(enemy, int(spec.get("power", 1)))
            elif kind == "aoe_burst":
                dist = max(abs(enemy.x - px), abs(enemy.y - py))
                fired = alert and dist <= int(spec.get("cast_range", 4))
                if fired:
                    enemy.aoe_charge = float(spec.get("windup", 2))
                    enemy.aoe_tx, enemy.aoe_ty = enemy.x, enemy.y
                    # 蓄力预告只上顶部滚动（2026-10-12）：不进事件记录。
                    self.ticker_notes.append(tr(
                        "{enemy}开始积蓄力量——快离开它的范围！", enemy=tr(enemy.label)))
            elif kind == "ignite":
                fired = alert or spec.get("anchor") == "hunt"
                if fired:
                    self._skill_ignite(enemy, spec)
            elif kind == "bomb":
                dist = max(abs(enemy.x - px), abs(enemy.y - py))
                fired = (
                    alert and dist <= int(spec.get("cast_range", 5))
                    and self._has_line_of_sight(enemy.x, enemy.y, px, py)
                )
                if fired:
                    self.enemy_bombs.append([
                        px, py, float(spec.get("windup", 2)),
                        int(spec.get("radius", 1)), int(spec.get("power", 2)),
                    ])
                    from .cast_fx import emit_cast
                    from ..data.cast_fx import CastVisual
                    path = self._sk_ray(enemy.x, enemy.y, px, py,
                                        max(abs(enemy.x-px), abs(enemy.y-py)))
                    emit_cast(self, CastVisual('needle', 'line'), 'legacy:bomb',
                              (enemy.x, enemy.y), path, path=path, source_id=enemy.id)
                    self.messages.append(tr(
                        "{enemy}朝你扔来一份会炸的东西——快离开落点！",
                        enemy=tr(enemy.label)))
            elif kind == "clear_terrain":
                fired = True
                self._skill_clear_terrain(enemy, int(spec.get("radius", 1)))
            elif kind == "erode_walls":
                fired = True
                self._skill_erode_walls(
                    enemy, int(spec.get("radius", 2)), int(spec.get("damage", 40)))
            elif kind == "emanate":
                fired = True
                self._skill_emanate(enemy, spec)
            if fired:
                self._emit_enemy_skill_noise(enemy, kind, spec)
            enemy.skill_clocks[key] = 0.0 if fired else min(clock, every)

    @animate_legacy('ranged', 'needle', 'line')
    def _enemy_ranged_hit(self, enemy: Entity, power: int) -> None:
        self._skill_trauma(enemy, power)
        self.messages.append(tr("{enemy}的远程打击命中了你。", enemy=tr(enemy.label)))

    def _detonate_aoe_burst(self, enemy: Entity, spec: dict) -> None:
        """范围爆发结算：玩家仍在预警圈内才吃创伤（跑出去就打不中）。"""
        radius = int(spec.get("radius", 1))
        power = int(spec.get("power", 1))
        from .cast_fx import emit_cast
        from ..data.cast_fx import CastVisual
        center = (enemy.aoe_tx, enemy.aoe_ty)
        cells = [(x, y) for y in range(center[1]-radius, center[1]+radius+1)
                 for x in range(center[0]-radius, center[0]+radius+1) if self.inside_board(x, y)]
        emit_cast(self, CastVisual('blast', 'blast'), 'legacy:aoe_burst',
                  center, cells, source_id=enemy.id)
        self._sound_pulse(center[0], center[1], max(6, radius + 5),
                          category="enemy_skill", source=tr(enemy.label),
                          announce=False, triggers_rewards=False)
        if max(abs(self.player.x - enemy.aoe_tx), abs(self.player.y - enemy.aoe_ty)) <= radius:
            self._skill_trauma(enemy, power)
            self.messages.append(tr("冲击波扫过——{enemy}的震波命中了你！", enemy=tr(enemy.label)))
        else:
            self.messages.append(tr("震波在范围外散开了——你躲开了。"))

    @animate_legacy('ignite', 'fire', 'fire')
    def _skill_ignite(self, enemy: Entity, spec: dict) -> None:
        ax, ay = self._skill_anchor(enemy, spec.get("anchor", "self"))
        radius = int(spec.get("radius", 1))
        lit = 0
        for y in range(max(0, ay - radius), min(self.height, ay + radius + 1)):
            for x in range(max(0, ax - radius), min(self.width, ax + radius + 1)):
                if self._ignite_cell(x, y, strength=3):
                    lit += 1
        if lit:
            self.messages.append(tr("{enemy}点起了火！", enemy=tr(enemy.label)))

    def _tick_enemy_bombs(self, amount: int) -> None:
        """落点炸弹：引信归零当场 ``_explode``（伤害/引燃/动画统一结算）。

        炸弹是运行期瞬态（不入档）：读档即消失。
        """
        if not self.enemy_bombs:
            return
        survivors: list = []
        for bomb in self.enemy_bombs:
            x, y, fuse, radius, power = bomb
            fuse -= amount
            if fuse > 0:
                bomb[2] = fuse
                survivors.append(bomb)
                continue
            self._explode(x, y, radius, power)
        self.enemy_bombs = survivors

    def skill_telegraphs(self) -> dict[tuple[int, int], str]:
        """异象技能预警格（2026-09-22）：范围蓄力区 → "burst"，炸弹杀伤区 → "bomb"。

        「有渲染提示范围」的约定：render_map 据此垫警示底色——玩家看到的
        格子就是即将受影响的格子。可见性裁剪由渲染层负责。
        """
        tele: dict[tuple[int, int], str] = {}
        for enemy in self.enemies:
            if enemy.integrity <= 0 or enemy.aoe_charge <= 0:
                continue
            radius = int(self._enemy_skill_spec(enemy, "aoe_burst").get("radius", 1))
            for y in range(max(0, enemy.aoe_ty - radius), min(self.height, enemy.aoe_ty + radius + 1)):
                for x in range(max(0, enemy.aoe_tx - radius), min(self.width, enemy.aoe_tx + radius + 1)):
                    tele[(x, y)] = "burst"
        for bomb in self.enemy_bombs:
            bx, by, _fuse, radius, _power = bomb
            for y in range(max(0, by - radius), min(self.height, by + radius + 1)):
                for x in range(max(0, bx - radius), min(self.width, bx + radius + 1)):
                    tele[(x, y)] = "bomb"
        warning=self.epilogue_flags.get('scribe_warning') if self.depth==30 else None
        if warning and any(e.catalog_id=='anomaly.scribe' and e.integrity>0 for e in self.enemies):
            x,y=warning['pos'];r=warning['radius']
            for b in range(max(0,y-r),min(self.height,y+r+1)):
                for a in range(max(0,x-r),min(self.width,x+r+1)):tele[(a,b)]='burst'
        return tele

    @animate_legacy('clear_terrain', 'terrain', 'wash')
    def _skill_clear_terrain(self, enemy: Entity, radius: int) -> None:
        """地形改造·抽干：把身边 (2r+1)² 的气体与液体清空（火焰不在此列）。"""
        cleared = 0
        for y in range(max(0, enemy.y - radius), min(self.height, enemy.y + radius + 1)):
            for x in range(max(0, enemy.x - radius), min(self.width, enemy.x + radius + 1)):
                cell = self.cell(x, y)
                if cell.solid:
                    continue
                if cell.gas > 0:
                    cell.gas, cell.gas_kind = 0, ""
                    cleared += 1
                if cell.liquid > 0:
                    cell.liquid, cell.liquid_kind = 0, ""
                    cleared += 1
        if cleared:
            self._material_index_ready = False
            self.messages.append(tr(
                "{enemy}凝出一圈寒霜，抽干了周围的气体与液体。", enemy=tr(enemy.label)))

    # 蚀墙/碎墙的豁免墙种：意识边界神圣不可覆写；石台与记忆/思绪容器是
    # 台面承载家具；门本就会为异象自动打开——都不在可破坏之列。
    _SKILL_PROTECTED_WALLS = frozenset({"意识边界", "石台", "机关石台", "门"})

    def _protected_wall(self, wall_kind: str) -> bool:
        from ..materials.walls import CONTAINER_KINDS

        return wall_kind in self._SKILL_PROTECTED_WALLS or wall_kind in CONTAINER_KINDS

    @animate_legacy('erode_walls', 'terrain', 'erase')
    def _skill_erode_walls(self, enemy: Entity, radius: int, damage: int) -> None:
        """地形改造·范围蚀墙：身边 (2r+1)² 的墙体完整度削减，归零即塌。"""
        from ..materials.walls import CONTAINER_KINDS

        eroded = 0
        for y in range(max(0, enemy.y - radius), min(self.height, enemy.y + radius + 1)):
            for x in range(max(0, enemy.x - radius), min(self.width, enemy.x + radius + 1)):
                cell = self.cell(x, y)
                if not cell.solid or not cell.wall_kind:
                    continue
                if cell.wall_kind in self._SKILL_PROTECTED_WALLS or cell.wall_kind in CONTAINER_KINDS:
                    continue
                cell.integrity -= damage
                eroded += 1
                if cell.integrity <= 0:
                    cell.solid = False
                    cell.wall_kind = ""
                    cell.hardness = 0
                    cell.integrity = 0
        if eroded:
            self._material_index_ready = False
            self.messages.append(tr(
                "{enemy}的边缘爬上周围的墙——墙体正在剥落。", enemy=tr(enemy.label)))

    @animate_legacy('emanate', 'field', 'mist')
    def _skill_emanate(self, enemy: Entity, spec: dict) -> None:
        """地形改造·呼出：在身边 (2r+1)² 生成特定气体/液体（走统一入口）。"""
        # 载荷键是 "emit"（"kind" 已被技能类型占用，重复键会静默覆盖）。
        kind = spec.get("emit", "")
        if not kind:
            return
        radius = int(spec.get("radius", 1))
        medium = spec.get("medium", "gas")
        for y in range(max(0, enemy.y - radius), min(self.height, enemy.y + radius + 1)):
            for x in range(max(0, enemy.x - radius), min(self.width, enemy.x + radius + 1)):
                cell = self.cell(x, y)
                if cell.solid or cell.flame:
                    continue
                if medium == "gas":
                    self._add_gas(cell, kind, 18)
                else:
                    self._add_liquid(cell, kind, 12)

    def _enemy_can_break_wall(self, enemy: Entity, x: int, y: int) -> bool:
        """Read-only breach qualification shared by planning and execution."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        spec = self._enemy_skill_spec(enemy, "wall_break")
        if not spec:
            return False
        cell = self.cell(x, y)
        if not cell.solid or not cell.wall_kind:
            return False
        if cell.hardness > int(spec.get("hardness_max", 2)):
            return False
        from .tamper_protection import terrain_reason
        return not terrain_reason(self, x, y)

    def _try_wall_break(self, enemy: Entity, x: int, y: int) -> bool:
        """破墙续行：撞碎耗一次移动行动，下次行动才能进入。"""
        if max(abs(x - enemy.x), abs(y - enemy.y)) != 1:
            return False
        if not self._enemy_can_break_wall(enemy, x, y):
            return False
        # 走真实材料破坏：保留墙体自带的冷凝/潮解/碎裂后果，不凭空删内容。
        if not self.destroy_wall(x, y, 'enemy_breach'):
            return False
        self._material_index_ready = False
        self.messages.append(tr("{enemy}撞碎了挡路的墙！", enemy=tr(enemy.label)))
        return True

    # ---- 千禧园·千年虫（2026-10-10，docs/millennium-garden-design.md §10.3）----

    def _spawn_millennium_worm(self) -> bool:
        """敌对千年虫登场（接入/强拆双路径共用）：只有失控意识形态，登场即追踪。

        守卫：仅千禧园第 5 层；场上已有活千年虫时不重复召唤（终端再互动=静默）。
        落点：玩家附近 1–3 格的开放格（「它顺着电话线爬过来了」）。
        """
        if self.realm_id != "millennium_garden" or self.realm_depth != 5:
            return False
        if any(e.integrity > 0 and e.catalog_id == "anomaly.core_y2k_worm" for e in self.enemies):
            self.messages.append(tr("终端静默——它已经出来了。"))
            return False
        px, py = self.player.x, self.player.y
        spot = None
        for radius in (1, 2, 3):
            ring = [(px + dx, py + dy) for dx in range(-radius, radius + 1)
                    for dy in range(-radius, radius + 1)
                    if max(abs(dx), abs(dy)) == radius]
            for nx, ny in ring:
                if 0 <= nx < self.width and 0 <= ny < self.height \
                        and not self.cell(nx, ny).solid and self.entity_at(nx, ny) is None:
                    spot = (nx, ny)
                    break
            if spot:
                break
        if spot is None:
            spot = px, py
        self.add_defined_enemy("anomaly.core_y2k_worm", spot[0], spot[1])
        for enemy in self.enemies:
            if enemy.catalog_id == "anomaly.core_y2k_worm" and enemy.integrity > 0:
                enemy.alert_state = "追踪"
        self.messages.append(tr("你已拨入。屏幕上的进度条猛地跳完——千年虫顺着电话线爬出来了。"))
        return True

    def _y2k_open_spot_near(self, cx: int, cy: int, offset: int = 0):
        """千年虫身边的开放落点（8 邻域优先、再外扩一圈；确定性轮转）。"""
        rings = [(cx + dx, cy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 if (dx, dy) != (0, 0)]
        rings += [(cx + dx, cy + dy) for dx in (-2, -1, 0, 1, 2) for dy in (-2, 2)]
        rings += [(cx + dx, cy + dy) for dx in (-2, 2) for dy in (-1, 0, 1)]
        open_spots = [
            (x, y) for x, y in rings
            if 0 <= x < self.width and 0 <= y < self.height
            and not self.cell(x, y).solid and self.entity_at(x, y) is None
        ]
        if not open_spots:
            return None
        return open_spots[offset % len(open_spots)]

    def _y2k_summon_wave(self, worm: Entity, catalog_ids, cap: int = 4) -> int:
        """召唤一波护卫（🫧/📟/📺），全场非本核异象封顶 cap（防海战术，§10.3）。"""
        minions = sum(1 for e in self.enemies
                      if e is not worm and e.integrity > 0 and e.relation == "失控意识")
        spawned = 0
        for index, cid in enumerate(catalog_ids):
            if minions + spawned >= cap:
                break
            spot = self._y2k_open_spot_near(worm.x, worm.y, index)
            if spot is None:
                break
            minion = self.add_defined_enemy(cid, spot[0], spot[1])
            minion.alert_state = "追踪"
            spawned += 1
        return spawned

    def _y2k_teleport(self, worm: Entity) -> bool:
        """系统迁移：瞬移到距玩家 ≥7 的开放格（脱战重整，§10.3 阶段 3）。"""
        rng = random.Random(self.seed ^ (self.time * 7919) ^ stable_token(worm))
        candidates = [
            (x, y)
            for y in range(2, self.height - 2)
            for x in range(2, self.width - 2)
            if not self.cell(x, y).solid and self.entity_at(x, y) is None
            and max(abs(x - self.player.x), abs(y - self.player.y)) >= 7
        ]
        if not candidates:
            return False
        worm.x, worm.y = rng.choice(candidates)
        self.messages.append(tr("屏幕闪过一行「系统迁移中……」——千年虫挪进了机房深处。"))
        return True

    def _core_actives(self, enemy: Entity, amount: int) -> None:
        """核心执念的专属主动技能组（每个核心 2-3 个，按回合拍触发）。

        血量厚（25/45/70）但创伤与常规中段持平——威胁来自技能组合而非单发创伤。
        计时用全局回合取模，确定性触发；召唤都有场上存量上限。
        """
        cid = enemy.catalog_id
        px, py = self.player.x, self.player.y
        dist = max(abs(enemy.x - px), abs(enemy.y - py))

        if cid == "anomaly.hollow_lighthouse":
            # 光压：远距离抽取清醒；召集：补一只纸页犬（至多 2 只在场）。
            if dist <= 4 and self.time % 6 == 0:
                from .settlement import REASON_COMBAT, settle_delta
                settle_delta(self, 'lucidity', -1, reason=REASON_COMBAT,
                             source='空心的灯塔·光压')
                self.messages.append(tr("灯塔的光压碾过来——清醒度被抽走了一缕。"))
            if self.time % 14 == 0:
                hounds = sum(1 for e in self.enemies if e.catalog_id == "anomaly.page_hound" and e.integrity > 0)
                if hounds < 2:
                    self.add_defined_enemy("anomaly.page_hound", enemy.x + 1, enemy.y, integrity=2)
                    self.messages.append(tr("灯塔的光里走出一小簇新的影子。"))
        elif cid == "anomaly.unfinished_period":
            # 句号吞噬：抽想象力；顿号冻结：周期性把玩家钉在原地；召集折页人。
            if self.time % 5 == 0:
                from .settlement import REASON_COMBAT, settle_delta
                settle_delta(self, 'imagination', -2, reason=REASON_COMBAT,
                             source='未完成句号')
                self.messages.append(tr("一个巨大的句号吞掉了你两笔想象力。"))
            if self.time % 9 == 0 and self._apply_direct_portent(
                    self.player, "frozen", 2, mode="add"):
                self.messages.append(tr("句子被迫停顿——你被句号冻在原地。"))
            if self.time % 16 == 0:
                folded = sum(1 for e in self.enemies if e.catalog_id == "anomaly.folded_person" and e.integrity > 0)
                if folded < 2:
                    self.add_defined_enemy("anomaly.folded_person", enemy.x, enemy.y + 1)
                    self.messages.append(tr("未完成句号折出一只折页人，替它继续写。"))
        elif cid == "anomaly.first_cry":
            # 啼哭冲击：全层心智震荡并惊动异象；冻嚎：冻结玩家；召集：唤出思维蠕虫。
            if self.time % 5 == 0:
                self._identity_direct_trauma(enemy, 2, 0)
                for other in self.enemies:
                    if other.relation == "失控意识" and other.integrity > 0:
                        other.alert_state = "追踪"
                self.messages.append(tr("一声啼哭震荡整层梦——心智 −2，所有异象都醒了。"))
            if self.time % 8 == 0 and self._apply_direct_portent(
                    self.player, "frozen", 2, mode="add"):
                self.messages.append(tr("冻嚎掠过——你的膝盖结满了霜。"))
            if self.time % 18 == 0:
                worms = sum(1 for e in self.enemies if e.catalog_id == "anomaly.thought_worm" and e.integrity > 0)
                if worms < 2:
                    self.add_defined_enemy("anomaly.thought_worm", enemy.x, enemy.y - 1)
                    self.messages.append(tr("啼哭的回声里钻出一条思维蠕虫。"))
        elif cid == "anomaly.scribe":
            self._scribe_turn(enemy,amount)
            return
        elif cid == "anomaly.core_y2k_worm":
            # 三阶段召唤系（§10.3 v4）：完整度 <2/3 解锁「进程繁殖」、<1/3 解锁
            # 「系统迁移」（瞬移+召唤）；阶段 1「孵化请求」从登场第一拍就开始。
            # 阶段标记是运行期属性（asdict 不序列化动态字段——读档后同阶段会
            # 重触发一次；在场封顶 4 兜底，可接受的最小实装）。
            stage = 1
            if enemy.integrity < 55 / 3:
                stage = 3
            elif enemy.integrity < 55 * 2 / 3:
                stage = 2
            if stage > getattr(enemy, "y2k_stage", 0) and self.time % 4 == 0:
                if stage == 1:
                    if self._y2k_summon_wave(
                            enemy, ("anomaly.screensaver_bubble", "anomaly.screensaver_bubble")):
                        enemy.y2k_stage = 1
                        self.messages.append(tr("屏幕弹出「孵化请求」——两只屏保气泡从进程里溢了出来。"))
                elif stage == 2:
                    if self._y2k_summon_wave(
                            enemy, ("anomaly.pager_sprite", "anomaly.pager_sprite")):
                        enemy.y2k_stage = 2
                        self.messages.append(tr("「进程繁殖」——两只传呼精灵沿着数据线孵化出来。"))
                else:
                    moved = self._y2k_teleport(enemy)
                    if self._y2k_summon_wave(
                            enemy, ("anomaly.static_viewer", "anomaly.static_viewer")):
                        enemy.y2k_stage = 3
                        self.messages.append(tr("「系统迁移」——两只雪花观众随它一起搬了家。"))
                    elif moved:
                        enemy.y2k_stage = 3

    def _enemy_rooted(self, enemy: Entity) -> bool:
        return (enemy.portents.get('sk_rooted',0)>0 or
                enemy.active_skill_state.get('rooted_turn')==self.time)

    def _enemy_move_step(self, enemy: Entity) -> bool:
        """异象的一步移动：巡逻路线 / 纸鱼亲液 / 追踪计划（8 向 A*）/ 游荡。"""
        if self._enemy_rooted(enemy):
            return False
        if (enemy.keeps_watch and enemy.alert_state=='未察觉'
                and enemy.last_seen_x<0 and not self._enemy_sees_player(enemy)
                and getattr(enemy, 'trait', '') != 'staircase'):
            # 在原岗时保持不动；被诱声/追击带离后允许按 §5.1 回位。
            home = (getattr(enemy, 'home_x', None), getattr(enemy, 'home_y', None))
            if None in home or (enemy.x, enemy.y) == home:
                return False
        candidates: list[tuple[int, int]] = []
        if enemy.trait == "patrol" and enemy.alert_state in ("未察觉", "怀疑") and enemy.route:
            enemy.route_index = (enemy.route_index + 1) % len(enemy.route)
            candidates = [enemy.route[enemy.route_index]]
        else:
            candidates = self._enemy_move_candidates(enemy)
        for nx, ny in candidates:
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            # 门是唯一的例外：关闭的门虽然实心，但异象踩上去会自动打开
            # （本回合收尾的 _update_doors 看到「门上有生物」就把门打开）——
            # 否则异象追到门口就被关着的门死死挡住，只能原地徘徊。
            if self.cell(nx, ny).solid and self.cell(nx, ny).wall_kind not in DOOR_KINDS:
                # 破墙续行（技能 v3）：能撞碎的低硬度墙就地撞碎，消耗本步。
                if self._try_wall_break(enemy, nx, ny):
                    return True
                continue
            if (nx, ny) == (self.player.x, self.player.y):
                continue
            if self.entity_at(nx, ny) is not None:
                continue
            enemy.x, enemy.y = nx, ny
            enemy.nav_stall = 0
            enemy.nav_waited = False
            enemy.nav_hold = False
            enemy.nav_wait_since = -1
            enemy.nav_blocked = []
            enemy.nav_recent = (list(enemy.nav_recent) + [(nx, ny)])[-6:]
            self._emit_step_noise([(nx, ny)], emitter=enemy)
            # 迈出的正是计划里的下一步 → 推进计划游标（丢失视野后按计划走
            # 依赖这个游标；走偏了也无妨，重算会以当前坐标为起点）。
            if enemy.path_plan and enemy.plan_index < len(enemy.path_plan) and (nx, ny) == enemy.path_plan[enemy.plan_index]:
                enemy.plan_index += 1
            # 异象同样会踩折高丛，也会吃这株植物的踩踏反应（缚魂藤缠脚等）
            # ——踩坏它的不止玩家一个人。
            self.trample_plant(nx, ny, enemy)
            return True
        if enemy.nav_hold:
            # §5.1：射手守住距离带属于合法准备站位，不记作无进展。
            enemy.nav_hold = False
            enemy.nav_stall = 0
            return False
        if enemy.nav_waited:
            # 为正在离开的同伴让路一回合：符合 §5.3 的「有意义等待」，
            # 不计入无进展；堵点不变时下次直接侧移。
            return False
        if candidates and (self.player.x, self.player.y) in candidates:
            # 已站到合法攻击位：不能踩进玩家格不是“无进展”（§5.1 近战接近）。
            enemy.nav_stall = 0
            return False
        enemy.nav_stall += 1
        return False

    def _split_phantom_chance(self, enemy: Entity) -> None:
        """双重曝光「残影分裂」：每回合 25% 概率生成 1 点耐久的残影（同时至多 2 个）。"""
        rng = random.Random(self.seed ^ (self.time * 77017) ^ (enemy.x * 31 + enemy.y))
        if rng.random() >= 0.25:
            return
        alive = sum(1 for other in self.enemies if other.trait == "phantom" and other.main_id == enemy.id and other.integrity > 0)
        if alive >= 2:
            return
        phantom = self.add_enemy(
            "残影", enemy.x + 1, enemy.y,
            integrity=1, move_time=1.0, attack_time=1.0,
            trauma_type=enemy.trauma_type, communicates=False,
            drop_id=None, dissolution_reward=4,
            catalog_id="anomaly.unknown", anomaly_kind=enemy.anomaly_kind,
            vision=enemy.vision, trait="phantom",
        )
        phantom.glyph = enemy.glyph
        phantom.main_id = enemy.id
        self.messages.append(tr("底片上的第二层显影走了出来。"))

    def _cutpurse_steal(self) -> str | None:
        """梦游裁缝「剪除」：让玩家随机掉落 1 件未穿戴的易逝物在脚下。"""
        droppables = [item for item in self.inventory if item.category == "易逝物" and item.instance_id not in self.equipped.values()]
        if not droppables:
            return None
        victim = droppables[self.time % len(droppables)]
        self.inventory.remove(victim)
        self.world_items.append(WorldItem(victim, self.player.x, self.player.y))
        if self.hang_item_id == victim.instance_id:
            self.hang_item_id = None
            self._refresh_hang()
        return victim.name

    def _lighthouse_turn(self, enemy: Entity, amount: int) -> None:
        enemy.pulse_clock += amount
        if enemy.pulse_clock < 10:
            return
        enemy.pulse_clock -= 10
        self.light_turns = 2
        self.messages.append(tr("空心的灯塔发动「照彻」：全图被照亮 2 回合，所有异象都看见了你的位置。"))
        for other in self.enemies:
            if other.integrity > 0 and other.vision > 0:
                other.alert_state = "追踪"
                # 光把你的位置摊给了整层：记下并规划过去，而不是只改状态。
                other.last_seen_x, other.last_seen_y = self.player.x, self.player.y
                other.wandering = False
                self._plan_chase(other, self.player.x, self.player.y)
                if self.insight_active("灯塔共鸣"):
                    # 灯塔共鸣：光把异象钉在原地。
                    other.frozen_turns = max(other.frozen_turns, 2.0)

    def _staircase_turn(self, enemy: Entity, amount: int) -> None:
        """迁徙的楼梯：每 6 回合向**合法位置证据**推进 1 格；路径上的玩家被推开并受碾压创伤。

        §11.1-1／§10（2026-10-22 收口）：原实现方向只取玩家实时坐标，没有任何
        视线／声音证据也会追人。现在只消费 _enemy_chase_target 给出的位置事实
        （仍有效的最后目击／未过期调查任务／报信点）；没有证据就停着不动。
        碾压判定仍要求玩家确实站在推进目标格——那是物理接触结算，不是凭空定位。
        """
        enemy.move_clock += amount
        if enemy.move_clock < 6:
            return
        enemy.move_clock -= 6
        target = self._enemy_chase_target(enemy)
        if target is None:
            return
        tx, ty = int(target[0]), int(target[1])
        if (enemy.x, enemy.y) == (tx, ty):
            return
        dx = 0 if enemy.x == tx else (1 if tx > enemy.x else -1)
        dy = 0 if enemy.y == ty else (1 if ty > enemy.y else -1)
        for nx, ny in ((enemy.x + dx, enemy.y), (enemy.x, enemy.y + dy)):
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            if self.cell(nx, ny).solid:
                continue
            if (nx, ny) == (self.player.x, self.player.y):
                # 碾压：推开玩家 1 格并造成 1 点清醒创伤。
                pushed = False
                for px, py in ((self.player.x + dx, self.player.y), (self.player.x, self.player.y + dy)):
                    if (px, py) != (enemy.x, enemy.y) and 0 <= px < self.width and 0 <= py < self.height and not self.cell(px, py).solid and self.entity_at(px, py) is None:
                        self.player.x, self.player.y = px, py
                        self.trample_plant(px, py, self.player)
                        pushed = True
                        break
                self._identity_direct_trauma(enemy, 0, 1)
                self.messages.append(tr("迁徙的楼梯碾压而过，你被推开了 1 格并受到清醒创伤。"))
                if not pushed:
                    self.messages.append(tr("你被楼梯死死压在墙上。"))
                return
            if self.entity_at(nx, ny) is not None:
                continue
            enemy.x, enemy.y = nx, ny
            self.messages.append(tr("一段楼梯在梦里缓缓迁徙。"))
            return

    def _propagate_alert(self, source: Entity) -> None:
        radius = self._sound_radius(source.x, source.y, source.vision)
        for other in self.enemies:
            if other is source or other.integrity <= 0 or not other.communicates:
                continue
            distance = abs(other.x - source.x) + abs(other.y - source.y)
            if distance <= radius and other.alert_state == "未察觉" and self._has_line_of_sight(source.x, source.y, other.x, other.y):
                other.alert_state = "怀疑"
                # §22 B：传信是独立事实，只记报信点，不冒充目击，也不给
                # 玩家实时坐标；被叫醒的异象去报信者身边查看。
                other.last_reported_x, other.last_reported_y = source.x, source.y
                other.last_reported_time = self.time
                self._remember_investigation(other, source.x, source.y,
                                             "report", "report")
