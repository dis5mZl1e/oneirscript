"""行动时间轴：亚回合记账、行动层计数、时间偷取与终局判定。"""

from __future__ import annotations

from ..i18n import tr
from ..world import scenes as world_scenes
from .chaos import note_chaos_action
from .constants import ACTION_COUNT_LIMIT, ActionKind
from .tamper_previews import resolve_tamper_previews
from .cast_fx import pause_fx_world_step



class TempoMixin:
    def _player_speed_scale(self) -> float:
        if getattr(self, 'stasis_turns', 0) > 0:
            return 1.0
        from .timed_actions import modem_time_multiplier
        return self._speed_scale(self.portents) / modem_time_multiplier(self)

    def _spend_action_time(self, rounds: float) -> bool:
        """把一次行动的时间成本折算成整数「回合」推进。

        「成本」是浮点，「时间轴」保持整数：成本的小数部分记入 round_debt，
        攒满 1 回合才真正 _advance 一次。因此：

          减速 2 回合 / 次   → 一次行动 _advance(2)，效果结算 2 次；
          加速 0.5 回合 / 次 → 两次行动才 _advance(1)，效果合计结算 1 次；
          0 回合（免费行动） → 不入账、不推进，效果不结算。

        这样持续效果吃到的始终是「客观时间」，而 time 仍是精确整数刻度
        （`%`、`//`、随机种子、存档都依赖这一点）。

        贴身的异象在同一段客观时间里按 dt 蓄力出手（见 _charge_adjacent_attacks），
        因此「时间怎么花」不会成为逃避打击的空子。

        返回：本次是否跨过了 >=1 个回合刻度。时间偷取要靠它判断「这扇窗口是否
        已经自然结束」（跨过即不该再罚），见 _note_action。
        """
        if rounds <= 0:
            return False
        # 贴身蓄力按客观时间计费：这一段耗时无论落在哪一步，都如实计入相邻
        # 异象的攻击计时。必须在 _advance 之前结算——旧行为里「出手的异象本
        # 回合不再移动」依赖它先置位 attack_pending。
        total = self.round_debt + rounds
        whole = int(total + 1e-9)
        remainder = total - whole
        first_step = 1.0 - self.round_debt
        for index in range(whole):
            self._charge_adjacent_attacks(first_step if index == 0 else 1.0)
            self.round_debt = 0.0
            self._advance(1)
        tail = remainder if whole else rounds
        if tail >= 1e-9:
            self._charge_adjacent_attacks(tail)
        self.round_debt = 0.0 if remainder < 1e-9 else remainder
        return whole > 0

    @pause_fx_world_step
    def _action_time(
        self,
        amount: float = 1.0,
        kind: ActionKind = ActionKind.MOVE,
        *,
        chaos_source: str = "world",
        chaos_effective: bool = True,
    ) -> None:
        """一次「行动」的时间入口：免费动作（双重曝光底片）不推进世界，
        深眠等征兆在此结算额外耗时。

        amount 是该行动的**基础**回合成本（常规 1，被迟滞/醉意拖慢的那一步 2），
        再按行动速度倍率整体缩放。所以：

          「加速 2 倍」的效果把 1 回合的行动压成 0.5 回合（零头记进 round_debt，
            两次行动才凑满 1 回合结算一次效果）；
          「免费行动」仍是地道的 0 回合，完全不推进世界、也不结算任何效果。

        kind 标明这次行动属于哪一类（移动 / 攻击 / 使用 / 免费 / 杂项）。它只喂给
        「按行动次数结算」的那一层（_note_action → _settle_action_effects），
        与时间成本本身无关——哑火 / 被 counters 也能顶到 cap 触发偷取。
        """
        # 主动技能公平窗口：免费行动也计一次动作（_force_end_round 不走这里，
        # 不会另增）：预警只在「玩家又行动过一次之后才」允许倒计时/结算。
        self.action_seq += 1
        from .settlement import record_action_time
        if self.free_actions > 0 and self.free_action_until and int(self.time) >= int(self.free_action_until):
            # 2026-10-22（P3）：底片有 5 回合窗口——没等到那个动作就自己褪掉，
            # 不能揣着一张底片一路走到本层终点。
            self.free_actions = 0
            self.free_action_until = 0
            self.messages.append(tr("底片上的第二次成像褪了——它没等到那个动作。"))
        if self.free_actions > 0 and amount > 0:
            self.free_actions -= 1
            self.free_action_until = 0
            self.messages.append(tr("底片上的第二次成像先于时间完成。"))
            record_action_time(self, kind=str(kind), base=amount, paid=0.0,
                               extra=0.0)
            self._note_action(ActionKind.FREE, crossed=False)
            self._tick_circuit_boards()
            return
        scale = self._player_speed_scale()
        paid = amount / scale if scale > 0 else amount
        from .anomaly_intents import begin_action, end_action
        begin_action(self)
        crossed = self._spend_action_time(paid)
        # 额外沉眠征兆（催眠雾的深眠、安眠香、褪黑素雾）：每一次行动都额外多沉
        # 若干回合。这一笔不随速度倍率缩放——它是征兆造成的额外沉眠，与行动本身
        # 的耗时不是一回事。提示语按实际来源征兆取名，别写死某一个。
        extra = self._portent_extra_turn()
        if extra:
            sources = tr("、").join(tr(name) for name in self._extra_turn_sources()) or tr("沉眠")
            self.messages.append(tr("{sources}让你多沉了 {extra} 回合。", sources=sources, extra=extra))
            paid += extra
            crossed = self._spend_action_time(extra) or crossed
        self._note_action(kind, crossed)
        if not crossed:
            # Occupancy changes even when an action consumes only fractional time.
            self._tick_circuit_boards()
        # 混乱度只认「实际支付的耗时」（篡改规格 §6.2）：免费行动在上面就 return，
        # 时间偷取的强制补齐走 _spend_action_time 不经过这里，两者都不进衰减。
        note_chaos_action(self, paid, kind=kind, source=chaos_source,
                          effective=chaos_effective)
        from .chaos import TAMPER_SOURCE
        if paid > 0 and chaos_source != TAMPER_SOURCE:
            from .tamper_pipeline import note_paid_action
            note_paid_action(self)
        # 场景设施的时间步（§10.2）：「预告」的火场在玩家又完成一次实际行动之后
        # 才真正落地，冷却/耗尽按世界时刻重算。免费行动在上面就 return 了，不走
        # 这里——0 回合的行动不该把一台设施的倒计时推过去。
        world_scenes.resolve_pending(self)
        # 篡改预警（页边余火／吞音）同样等「下一次耗时行动」才结算。
        resolve_tamper_previews(self)
        # 实际行动耗时事实（docs §10 第三批）：供自我觉察/预览核对「这次行动
        # 实际付了多少时间」，与显示用的基础耗时分开。
        record_action_time(self, kind=str(kind), base=amount, paid=paid,
                           extra=float(extra))
        end_action(self)

    def _note_action(self, kind: ActionKind, crossed: bool) -> None:
        """一次行动收尾的行动层结算：计数 → 按需效果 → 终局 → 时间偷取。

        顺序即总则里那张优先级表：先结算行动层的计数与按需效果（第 1 级），
        再由 crossed / steal_cap 决定要不要补推进时钟并强制结束回合（第 2、3 级），
        最后统一判终局（第 4 级）。
        """
        self._note_ebbing_departure()
        self._settle_action_effects(kind)
        self._check_run_over()
        if crossed:
            # 窗口自然结束——这次行动已经把时钟推过了至少一个整数刻度，
            # 偷取计数清零，本回合不再补刀。
            self._action_count = 0
            return
        self._action_count += 1
        if self._action_count >= self._effective_action_limit():
            # 到达 cap（时间偷取）或保底上限：立即把时钟补到一个整数刻度，
            # 本回合就此结束——玩家剩下的机会被抹掉，新回合从头计数。
            self._force_end_round()

    def _effective_action_limit(self) -> int:
        """本回合的行动数上限：时间偷取激活时用它，否则回落到保底上限。"""
        return self.steal_cap if self.steal_cap > 0 else ACTION_COUNT_LIMIT

    def _force_end_round(self) -> None:
        """强行结束本回合：抹除本回合剩余时间，推进到下一道刻度。

        只补上本回合还没走完的那一段（remainder），所以贴身异象按这个 remainder
        补蓄力，连同它在这几次行动里已攒下的零头，正好凑成本回合该有的那一次
        出手；世界同样推进一整格（征兆、刷新、覆写照常结算），玩家手里没花完的
        那点零头作废——这才叫「偷」。

        走 _spend_action_time 这个唯一时间入口，是为了让这一格跳过的回合也如实给
        敌人与世界上账；绕开它就会重新开出「靠强制跳回合躲刀」的风筝变体。
        """
        remainder = 1.0 - self.round_debt
        self.messages.append(tr("时间被偷走了一格，这一回合提前结束。"))
        self._spend_action_time(remainder)
        self._action_count = 0

    def _check_run_over(self) -> None:
        """终局判定：心智与清醒度同时归零即意识沉没。

        贴身打击现在发生在行动的时间入口里（_charge_adjacent_attacks），而亚回合
        行动可能一道回合刻度都不跨、也就不会走到 _advance 的收尾判定；因此这里
        独立成一个入口，两处都调用，避免「致命一击落在不推进回合的那一步」漏判。

        [SFX挂点] 意识沉没（本局失败终局）：建议 defeat——重下坠音 + 音乐淡出，
        与已有 finish（胜利收局）对称；播放挂 UI 层，见《音效挂点索引.md》。
        """
        if not self.run_over and self.mind <= 0 and self.lucidity <= 0:
            self.run_over = True
            # 死亡同样进入结算演出：深层边界沉没 = E「沉没」；正文各层 = F「无梦」。
            self.ending_id = "E" if self.depth >= 28 else "F"
            if self.depth>=28:
                self.epilogue_flags['fell_to_scribe']=(self.last_harm_source=='核心执念·执笔者' and self.last_harm_time>=self.time-1)
            self.victory = False
            self.messages.append(tr("意识沉没。"))

    def _settle_action_effects(self, kind: ActionKind) -> None:
        """「按行动次数」结算的统一入口：只累计分类计数，不推进任何时间。

        将来所有「每 N 次某类行动」的效果都挂在这里，共用 action_counts，
        不再各自另起一套计时。
        """
        key = str(kind.value)
        self.action_counts[key] = self.action_counts.get(key, 0) + 1

    @staticmethod
    def _rounds_crossed(previous: int, current: int, interval: int) -> int:
        """(previous, current] 区间内跨过了几道 interval 刻度。

        回合（客观时间）结算的统一入口。一次行动推进 1 个还是多个回合，经过的
        每一道刻度都会如实计入——减速（迟滞、醉意、深眠令行动多耗回合）因此
        全额结算，加速（免费行动不推进世界）则为 0。
        """
        if interval <= 0:
            return 0
        return current // interval - previous // interval
