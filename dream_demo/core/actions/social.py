"""社交动作族：NPC 对话/事件/尾声选项/交易支付/容器倾倒 + join_details。"""
from __future__ import annotations

import random
from typing import Any, Iterable

from ...i18n import tr
from ...materials import DOOR_KINDS, GAS_DEFINITIONS, TABLE_KINDS, floor_effect_for, portent_def, wall_def
from ..content import ABILITY_DEFINITIONS, ACCESSORY_SLOTS, EQUIPMENT_POOL, EVENT_INSIGHT_CHANCE
from ..content import event_option_label
from ...data.insights import choose_event_insight, event_insight_candidates
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


def _event_award_source(event) -> str:
    # Repeated authored events may carry an ``@x,y`` runtime suffix. Award
    # permissions belong to the authored event family, so keep the base ID.
    event_id = str(getattr(event, "event_id", "") or "").split("@", 1)[0]
    return "event:" + event_id


class SocialActionsMixin:
    """社交动作族：NPC 对话/事件/尾声选项/交易支付/容器倾倒 + join_details。"""

    def _claim_toy_reward(self, entry):
        if self.realm_id != 'toy_memories' or self.realm_depth != 4:
            return
        info = self.realm_challenges.get('toy_rewards', {})
        item_id = entry.item.definition_id
        if list((entry.x, entry.y)) == info.get('spots', {}).get(item_id):
            claimed = info.setdefault('claimed', [])
            if item_id not in claimed:
                claimed.append(item_id)
    @root_action
    def interact(self) -> ActionResult:
        """Enter「行动」：回应相邻的未解异常地点优先，其次取走相邻台面上的东西。

        [SFX挂点] 回应异常地点：建议 interact 事件（界面上确认感的正音）。
        core 保持纯逻辑，实际播放挂 UI 层（_apply 映射 / 状态 diff），见《音效挂点索引.md》。
        与 G 明确分工：**Enter 绝不拾取脚下的显化物**（那是 G / 走过去的事），
        它只处理「相邻」的事务——异常地点与台面承载物都是相邻互动，
        这两条目前都在（地点优先，因为它更稀奇且会解算奖励）。
        """
        event = self._adjacent_unresolved_event()
        if event is not None:
            if getattr(event, "kind", "simple") == "compound":
                # 复合事件：不当场结算，唤起事件面板（对话 + 底部选项）。
                self.close_npc_dialog()
                # 打开面板即固定实例身份（规格 §8.2）：篡改记录以它为准，
                # 之后事件被重排、层被重建都不会改身份。
                self.open_event_dialog(event)
                return ActionResult(True, tr("{event}：请选择回应方式。", event=tr(event.name)), {"dialogue": event.event_id})
            return self._resolve_event(event)
        # 相邻稳定意识（NPC）：唤起交易/对话面板。
        npc = self._adjacent_npc()
        if npc is not None:
            self.close_event_dialog()
            self.pending_npc_id = npc.id
            self.talk_toy_keeper(npc)
            # 图鉴「梦中人」：打开对话即记一次交互（NPC 分类的解锁判据）。
            self._record_catalog_interaction(npc.id, npc.label, "npc", "与其交谈过。")
            return ActionResult(True, tr("{name}：「请讲。」", name=tr(npc.label)), {"dialogue": npc.id})
        # 掉线拨号（§4.1）：限时状态在响铃且没有更具体的事务时，回应键 = 摘机进入。
        if not self.realm_id and (self.dial_in or {}).get("active"):
            return self._answer_dial_in()

        surface = self.adjacent_table_with_item()
        if surface is not None:
            return self.take_from(*surface)
        for board in self.circuit_boards:
            for node in board["nodes"].values():
                x, y = node["pos"]
                if node["op"] in {"toggle", "pulse"} and max(abs(x-self.player.x), abs(y-self.player.y)) == 1:
                    return self.open_adjacent(x, y)
        if self.adjacent_table() is not None:
            return ActionResult(False, tr("台面上没有东西。"))
        return ActionResult(False, tr("附近没有可以回应的异常地点。"))

    def _adjacent_unresolved_event(self):
        """相邻（切比雪夫距离 1）的未解异常地点；没有则 None。

        8 邻域与移动/寻路/开门/取物同一口径：旧实现用曼哈顿距离，站在斜角上
        回应毫无反应——「事件无法斜向交互」的根因。
        """
        return next(
            (
                entry
                for entry in self.events
                if not entry.resolved
                and max(abs(entry.x - self.player.x), abs(entry.y - self.player.y)) <= 1
            ),
            None,
        )

    def _resolve_event(self, event) -> ActionResult:
        """结算一次异常地点回应（奖励/洞察/崩解/耗时）。"""
        from ..main_difficulty import PROGRESS_EVENT_ID, resolve_progress_site
        if event.event_id == PROGRESS_EVENT_ID:
            return resolve_progress_site(self, event)
        reward_definition = ITEM_DEFINITIONS.get(event.reward_id) if event.reward_id else None
        reward_count = max(1, int(getattr(event, "reward_count", 1) or 1))
        if reward_definition:
            from ..item_access import refusal as item_grant_refusal
            reason = item_grant_refusal(self, event.reward_id, source=_event_award_source(event), count=reward_count)
            if reason:
                return ActionResult(False, reason)
        if reward_definition and not self._reward_fits(event.reward_id, reward_count):
            return ActionResult(False, tr("意识行囊已满，异常地点暂时无法交付显化物。"))
        event.resolved = True
        self._record_catalog_interaction(event.catalog_id, event.name, "site", event.description)
        # 洞察授予：异常地点不再「回应必有洞察」。事件本来就是一层才 1–2 个，
        # 若每次都发洞察，几层下来洞察槽就顶满，稀有度荡然无存。改按
        # EVENT_INSIGHT_CHANCE 掷一次——命中才给，未命中只结算物品与崩解。
        # 随机流取自种子、时间与地点坐标（同一次回应结果稳定，不随回看变化）。
        insight_text = ""
        candidates = event_insight_candidates(
            getattr(event, "event_id", "") or "", event.insight_id)
        if candidates:
            rng = random.Random(
                self.seed ^ (self.time * 7919) ^ (event.x * 131 + event.y)
            )
            roll = rng.random()
            # 巧合收集（扩展包 v2）：事件洞察概率 50% → 75%。
            chance = 0.75 if self.insight_active("巧合收集") else EVENT_INSIGHT_CHANCE
            if roll < chance:
                insight_text = self._grant_insight(
                    choose_event_insight(candidates, self.insights, rng))
        self._add_dissolution(event.dissolution_reward)
        if event.reward_id:
            reward_texts = []
            for _ in range(reward_count):
                item = self._make_item(event.reward_id)
                if item.category == "记忆碎片":
                    self._add_memory(item.definition_id)
                    if self.pending_memory:
                        insight_text += tr("记忆碎片已满：{name} 无处安放，需要替换或放弃。", name=tr(item.name))
                else:
                    self._add_inventory_item(item)
                from ..item_access import record_grant
                record_grant(self, item.definition_id, source=_event_award_source(event))
                reward_texts.append(item.name)
            reward_text = tr("获得 {names}。", names="、".join(tr(entry) for entry in reward_texts))
        else:
            reward_text = tr("没有留下可携带的显化物。")
        self._action_time(1, ActionKind.USE)
        self.run_stats["events"] = self.run_stats.get("events", 0) + 1
        message = tr("回应异常地点：{event}。{insight}{reward}", event=tr(event.name), insight=insight_text, reward=reward_text)
        self.messages.append(message)
        return ActionResult(True, message, {"event": event.event_id, "reward": event.reward_id})

    def open_event_dialog(self, event) -> None:
        """固定当前事件实例；类型 ID 仍供现有面板分派使用。"""
        from ..tamper_views import ensure_state_event_uids
        ensure_state_event_uids(self)
        self.pending_event_id = event.event_id
        self.pending_event_uid = event.instance_uid

    def pending_event(self):
        """当前唤起对话的复合事件（没有则 None）。"""
        uid = getattr(self, "pending_event_uid", None)
        return next(
            (entry for entry in self.events
             if entry.event_id == getattr(self, "pending_event_id", None)
             and (not uid or entry.instance_uid == uid)),
            None,
        )

    def close_event_dialog(self) -> None:
        """收起事件对话（不结算，事件保持未解）。"""
        self.events[:] = [event for event in self.events
                          if event.catalog_id not in ('consumable.choice', 'hospital.medicine_choice', 'hospital.lancet_choice',
                                                      'book.learning_choice', 'event.realm.scavenge_choice')
                          and not hasattr(event, '_book_offer')]
        self.pending_event_id = None
        self.pending_event_uid = None

    @root_action
    def choose_event_option(self, index: int) -> ActionResult:
        """复合事件：结算底部第 index 个选项（0 起）。

        选项字段：``leave``=离开（不结算、对话收起）；``reward_id``/``reward_count``
        交付显化物；``dissolution`` 选项自带的崩解增量（叠加在事件基值上，可为 0）；
        ``mind``/``lucidity``/``imagination`` 三项数值增减（正恢复、负创伤）。
        """
        if self.run_over:
            return ActionResult(False, tr("这一局已经结束。"))
        event = self.pending_event()
        if event is None or event.resolved or event.uses_left <= 0:
            return ActionResult(False, tr("没有正在进行的对话。"))
        from ..main_learning import EVENT_ID as learning_event_id, enabled as learning_enabled, record as learning_record
        if event.event_id == learning_event_id:
            if not learning_enabled(self) or learning_record(self).flags.get("claimed"):
                return ActionResult(False, tr("没有正在进行的对话。"))
        if event.catalog_id == 'book.learning_choice' or hasattr(event, '_book_offer'):
            from ..book_learning import choose_option
            return choose_option(self, event, index)
        # 篡改视图（规格 §8.1）：结算读的选项与面板显示的必须是同一份——被改过的
        # 句子带着补丁（费用／奖励数量／资源增量）来结算，记账仍按原选项 ID。
        from ..content import event_effective_options
        options = event_effective_options(self, event)
        if not (0 <= index < len(options)):
            return ActionResult(False, tr("没有这个选项。"))
        option = options[index]
        if option.get('expansion_reward'):
            from ..expansion_rewards import resolve_event_choice
            return resolve_event_choice(self, event, option['expansion_reward'])
        if option.get('realm_scavenge'):
            from ..realm_enrichment import scavenge
            return scavenge(self,event)
        if option.get('scavenge_choice'):
            from ..realm_enrichment import choose_scavenge_item
            return choose_scavenge_item(self, event, option['scavenge_choice'])
        if option.get('medicine_choice'):
            from ..hospital_medicines import confirm_selection
            return confirm_selection(self, event, option['medicine_choice'])
        if option.get('consumable_choice'):
            from ..expansion_consumables import use
            choice=option['consumable_choice']
            item_index=next((i for i,item in enumerate(self.inventory)
                             if item.instance_id==choice.get('instance')),None)
            if event.catalog_id!='consumable.choice' or item_index is None:
                return ActionResult(False,tr('这份物品已经不在行囊中。'))
            result=use(self,item_index,point=tuple(choice['point']),delay=choice['delay'])
            if result.changed:self.close_event_dialog()
            return result
        if option.get('hospital_load'):
            return self.confirm_hospital_lancet_selection(option['hospital_load'])
        if option.get('hospital_scene'):
            from ..hospital_scenes import resolve_hospital_scene
            return resolve_hospital_scene(self, event, option['hospital_scene'])
        if option.get('library_command'):
            from ..library_content import respond
            result = respond(self, event, option)
            if result is not None:
                if result.changed:
                    self.close_event_dialog()
                    self._action_time(1, ActionKind.USE)
                self.messages.append(result.message)
                return result
        if option.get('hospital_control'):
            return self.control_hospital_facility(event, option['hospital_control'])
        if option.get("realm_return"):
            if not self.realm_id:
                return ActionResult(False, tr("没有正在进行的对话。"))
            self.close_event_dialog()
            self._action_time(1, ActionKind.USE)
            if self.run_over or not self.realm_id:
                return ActionResult(True, self.messages[-1])
            self._exit_realm("leave")
            return ActionResult(True, self.messages[-1], {"returned_realm": True})
        # 事件选项的稳定 ID（§13.2）：日志与探针记它，不记「第几行」。
        option_id = event_option_id(event.event_id, index, option)
        if option.get('ember_control'):
            from ..realm_challenges import control_ember
            return control_ember(self, event, option['ember_control'])
        if option.get("scene_command"):
            # 场景设施命令自己结算时间与代价（world/scenes.py）：不走下面的通用
            # 事件配额——一台设施的燃料、冷却与库存只在它的解释器里记账。
            from ..scenes import operate_scene
            result = operate_scene(self, event, option["scene_command"])
            if result.changed and result.data.get("lens_offering") is not None:
                # §8 S23：嵌镜成功 → 收起点单的命令表，改由 UI 的祭品选择浮层接手。
                self.close_event_dialog()
            return result
        if option.get("summon_y2k"):
            # 千禧园零点体育场（§10.3 路径 A）：接入 → 敌对千年虫顺着电话线爬出来。
            self.close_event_dialog()
            spawned = self._spawn_millennium_worm()
            return ActionResult(spawned, self.messages[-1], {"summon_y2k": spawned})
        if option.get("enter_realm"):
            # 梦中梦入口（退潮厅的潮汐之门等）：只挡「已在位面内」与「本局已关门」。
            # 玩具的回忆那条入口已迁到 scene.lens_gate（§8 S23），不再走事件选项。
            realm_id = option["enter_realm"]
            if self.realm_id or realm_id in self.closed_realms:
                return ActionResult(False, tr("这扇门已经关上了——本局不会再为你打开。"))
            self.close_event_dialog()
            if not self.enter_realm(realm_id):
                return ActionResult(False, tr("这扇门已经关上了——本局不会再为你打开。"))
            if realm_id in {"library_palace", "white_sanatorium"}:
                self._action_time(1, ActionKind.USE)
            return ActionResult(True, self.messages[-1], {"realm": realm_id})
        if option.get("leave"):
            self.close_event_dialog()
            self.messages.append(tr("你退出了{event}。", event=tr(event.name)))
            return ActionResult(True, self.messages[-1], {"dialogue_closed": event.event_id})
        if option.get("epilogue"):
            # 深层边界：剧情选项走专属结算（辨认/门/承担/终局）。
            return self._resolve_epilogue_option(event, option)
        if option.get("random_option"):
            # 随机选项（2026-09-19）：从类型+稀有度集合里随机抽一件。
            # 每次选择结果都可能不同——随机在结算时刻掷骰。
            return self._resolve_random_option(event, option)
        # 零份是篡改后明确放弃实物；仍按原选项身份结算资源与次数。
        reward_count = max(0, int(option.get("reward_count", 1)))
        # 行囊满：与简单回应同口径，拒付显化物（不消耗触发次数、不结算）。
        if option.get("reward_id") and reward_count:
            reward_definition = ITEM_DEFINITIONS.get(option["reward_id"])
            from ..item_access import refusal as item_grant_refusal
            reason = item_grant_refusal(self, option['reward_id'], source=_event_award_source(event), count=reward_count)
            if reason:
                return ActionResult(False, reason)
            if (
                reward_definition
                and not self._reward_fits(option["reward_id"], reward_count)
            ):
                return ActionResult(False, tr("意识行囊已满，{event} 暂时无法交付显化物。", event=tr(event.name)))
        self.close_event_dialog()
        # 触发次数（2026-09-18）：每结算一次减一，归零才算 resolved（地点消失）；
        # 还有余次就保持未解，玩家稍后可以再来回应（面板显示剩余次数）。
        from ..expansion_rewards import mark_event_claimed
        mark_event_claimed(self, event, option.get('reward_id', ''))
        event.uses_left = max(0, int(getattr(event, "uses_left", 1) or 1) - 1)
        if event.uses_left <= 0:
            event.resolved = True
        self._record_catalog_interaction(event.catalog_id, event.name, "site", event.description)
        # 洞察授予：与简单回应同口径——事件带 insight_id 时按 EVENT_INSIGHT_CHANCE
        # 掷一次（命中才给）。所有异常地点升级为复合事件后，这是洞察通道①的唯一入口。
        insight_text = ""
        candidates = event_insight_candidates(
            getattr(event, "event_id", "") or "", event.insight_id)
        if candidates:
            rng = random.Random(
                self.seed ^ (self.time * 7919) ^ (event.x * 131 + event.y)
            )
            roll = rng.random()
            # 巧合收集（扩展包 v2）：事件洞察概率 50% → 75%。
            chance = 0.75 if self.insight_active("巧合收集") else EVENT_INSIGHT_CHANCE
            if roll < chance:
                insight_text = self._grant_insight(
                    choose_event_insight(candidates, self.insights, rng))
        # 崩解：事件基值 + 选项增量（部分复合事件完成即增加崩解度）。
        self._add_dissolution(event.dissolution_reward + int(option.get("dissolution", 0)))
        from ...i18n import get_language
        english = get_language() == 'en'
        resource_labels = {'mind': '心智', 'lucidity': '清醒度', 'imagination': '想象力'}
        stat_texts: list[str] = []
        for attr, key in (("mind", "mind"), ("lucidity", "lucidity"), ("imagination", "imagination")):
            amount = int(option.get(key, 0))
            if amount:
                value = getattr(self, attr)
                maximum = getattr(self, f"max_{attr}")
                setattr(self, attr, max(0, min(maximum, value + amount)))
                stat_texts.append(f"{tr(resource_labels[key])} {'+' if amount > 0 else '−'}{abs(amount)}")
        reward_text = tr("没有留下可携带的显化物。")
        if option.get("reward_id") and reward_count:
            reward_definition = ITEM_DEFINITIONS.get(option["reward_id"])
            names: list[str] = []
            for _ in range(reward_count):
                item = self._make_item(option["reward_id"])
                if item.category == "记忆碎片":
                    self._add_memory(item.definition_id)
                else:
                    self._add_inventory_item(item)
                from ..item_access import record_grant
                record_grant(self, item.definition_id, source=_event_award_source(event))
                names.append(item.name)
            reward_text = tr("获得 {names}。", names=(", " if english else "、").join(tr(entry) for entry in names))
        exit_outcome = option.get("exit_realm")
        if event.event_id == learning_event_id:
            learning_record(self).flags["claimed"] = True
        if exit_outcome:
            # Reaching and selecting the exit commits escape before its action cost.
            # Otherwise a final tide tick can eject us and exit a second time.
            self._exit_realm(str(exit_outcome))
        self._action_time(1, ActionKind.USE)
        stats_text = ((", " if english else "、").join(stat_texts)
                      + ("." if english else "。")) if stat_texts else ""
        self.run_stats["events"] = self.run_stats.get("events", 0) + 1
        message = tr("{event}：{choice}。{details}", event=tr(event.name),
                     choice=event_option_label(option).rstrip("。."),
                     details=join_details((insight_text, reward_text, stats_text)))
        self.messages.append(message)
        # 位面出口（余烬廊桥石台 / 退潮厅中心岛）：选到带 exit_realm 的选项即离开位面。
        # 「clear」= 通关关门（本局不可再进）；失败由 core/ebbing.py 直接走 _exit_realm("fail")。
        if exit_outcome:
            return ActionResult(
                True, self.messages[-1],
                {"event": event.event_id, "option": option_id, "realm_exit": exit_outcome},
            )
        return ActionResult(True, message, {"event": event.event_id, "option": option_id})

    # ---- 深层边界（28–30）剧情选项结算（2026-09-19）----

    def _resolve_random_option(self, event, option) -> ActionResult:
        """异常地点随机选项：从规定类型+稀有度的集合随机抽一件。"""
        import random as _random

        from ..content import ITEM_DEFINITIONS, RANDOM_OPTION_ITEM_POOL
        from ...data.ids import stable_seed

        conf = option["random_option"]
        pool_type = conf["pool"]
        rarities = tuple(conf.get("rarities", ()))
        pool = RANDOM_OPTION_ITEM_POOL.get(pool_type, ())
        from ..item_access import refusal as item_grant_refusal
        candidates = [e for e in pool if (not rarities or e[1] in rarities)
                      and not item_grant_refusal(self, e[0], source='random_reward')]
        if not candidates:
            return ActionResult(False, tr("命运犹豫了一下——什么也没有发生。"))
        # 播种用事件的稳定身份（event_id + 落格 + 池类型），不用 id(event)：
        # 内存地址跨进程会变，同一存档／同一种子重放会抽到不同结果。
        rng = _random.Random(self.seed ^ (self.time * 613)
                             ^ stable_seed("random_option", event.event_id, event.x, event.y, pool_type))
        item_id, rarity, _tag = candidates[rng.randrange(len(candidates))]
        definition = ITEM_DEFINITIONS[item_id]
        if not self._reward_fits(item_id):
            return ActionResult(False, tr("意识行囊已满，异常地点暂时无法交付显化物。"))
        item = self._make_item(item_id)
        from ..expansion_rewards import mark_event_claimed
        mark_event_claimed(self, event, item_id)
        event.uses_left = max(0, event.uses_left - 1)
        event.resolved = event.uses_left == 0
        self.close_event_dialog()
        self._record_catalog_interaction(event.catalog_id, event.name, "site", event.description)
        self._add_dissolution(event.dissolution_reward)
        if item.category == "记忆碎片":
            self._add_memory(item.definition_id)
        else:
            self._add_inventory_item(item)
        from ..item_access import record_grant
        record_grant(self, item.definition_id, source='random_reward')
        self._action_time(1, ActionKind.USE)
        rarity_text = {"常见": "常见", "少见": "少见", "稀有": "稀有", "非常稀有": "非常稀有"}.get(rarity, rarity)
        message = tr(
            "{event}：命运递来{rarity}的{item}。", event=tr(event.name), rarity=tr(rarity_text), item=tr(item.name)
        )
        self.messages.append(message)
        return ActionResult(True, message, {"event": event.event_id, "item": item_id, "rarity": rarity})

    def _epilogue_rooms_resolved(self) -> int:
        return sum(
            1 for entry in self.events
            if entry.event_id.startswith("epilogue.room") and entry.resolved
        )

    def _epilogue_scribe_dead(self) -> bool:
        return self._scribe_dead()

    def _resolve_epilogue_option(self, event, option) -> ActionResult:
        """深层边界选项结算：辨认 / 门 / 承担 / 终局。

        条件不满足时事件保持未解，并给出明确缺口提示（可观察、可补救）。
        """
        act = option.get("epilogue", {})
        action = act.get("act")
        flags = self.epilogue_flags
        if self.run_over:
            from ..epilogue import say
            return ActionResult(False,say('finished'))
        if event.resolved:
            return ActionResult(False,tr("这个选项什么也没发生。"))

        if action == "archive_take":
            # 出院与归档：28 层归档门的定向交付。这一句不推进层数、不结算事件，
            # 玩家领完仍可继续选择「我看完了」推进——所以既不能 resolved，
            # 也不关对话。合法性交给 item_access（深度/授权/每局上限）。
            item_id = str(act.get("item") or "")
            if not item_id:
                return ActionResult(False, tr("归档处没有这一份。"))
            from ..item_access import record_grant
            from ..item_access import refusal as item_grant_refusal
            reason = item_grant_refusal(self, item_id, source=_event_award_source(event), count=1)
            if reason:
                return ActionResult(False, reason)
            if not self._reward_fits(item_id, 1):
                return ActionResult(False, tr("意识行囊已满，归档处暂时无法交付。"))
            item = self._make_item(item_id)
            if item.category == "记忆碎片":
                self._add_memory(item.definition_id)
            else:
                self._add_inventory_item(item)
            record_grant(self, item_id, source=_event_award_source(event))
            self._record_catalog_interaction(event.catalog_id, event.name, "site", event.description)
            self._action_time(1, ActionKind.USE)
            message = tr("归档员在册子上划掉一行，把{item}推过桌面。", item=tr(item.name))
            self.messages.append(message)
            return ActionResult(True, message, {"event": event.event_id, "reward": item_id})

        if action == "identify":
            claim = act.get("claim", "")
            truth = act.get("truth", "")
            flags.setdefault('identified',{})[event.event_id]={'correct':claim==truth,'truth':truth}
            if claim == truth:
                flags["identify_correct"] = flags.get("identify_correct", 0) + 1
                flags["clues"] = flags.get("clues", 0) + 1
                self.messages.append(tr("判断正确——这段记忆的确来自{origin}。（自我线索 +1）", origin=tr(truth)))
            else:
                self.messages.append(tr("判断错了。它其实是{origin}。", origin=tr(truth)))
            event.resolved = True
            self.close_event_dialog()
            self._record_catalog_interaction(event.catalog_id, event.name, "site", event.description)
            self._action_time(1, ActionKind.USE)
            self._add_dissolution(8)
            return ActionResult(True, self.messages[-1], {"event": event.event_id})

        if action == "gate_rooms":
            done = self._epilogue_rooms_resolved()
            if done < 3:
                message = tr("归档门沉默着——三间展室还没有被看完（{done}/3）。", done=done)
                self.messages.append(message)
                return ActionResult(False, message, {"gate": "rooms"})
            if act.get("wipe"):
                flags["wiped"] = True
                flags["clues"] = 0
                self.messages.append(tr("你把线索付之一炬。门开了。"))
            self.close_event_dialog()
            return self.epilogue_advance(act.get("advance", 29))

        if action == "stele":
            flags['guided']=True
            flags['peace_kills']=self.run_stats.get('kills',0)
            self.close_event_dialog()
            self.messages.append(tr("牵引已接受。三个承担点在等你。"))
            return ActionResult(True, self.messages[-1], {"event": event.event_id})

        if action == "accept":
            from ..epilogue import say
            if not flags.get('guided'):
                return ActionResult(False,say('guided'))
            profile=self.epilogue_profile
            if profile=='杀伐型' and self.run_stats.get('kills',0)>flags.get('peace_kills',self.run_stats.get('kills',0)):
                return ActionResult(False,say('peace'))
            if profile=='囤积型':
                from ..constants import CARRIED_IMAGE
                item=next((item for item in self.inventory if item.category==CARRIED_IMAGE and item.instance_id not in self.equipped.values()),None)
                if item is None:return ActionResult(False,say('give'))
                self.inventory.remove(item)
            if profile=='纵火型' and any(self.cell(x,y).flame>0 for y in range(max(0,event.y-5),min(self.height,event.y+6)) for x in range(max(0,event.x-5),min(self.width,event.x+6))):
                return ActionResult(False,say('ash'))
            if profile=='直面型' and any(e.event_id.startswith('epilogue.accept') and e.event_id<event.event_id and not e.resolved for e in self.events):
                return ActionResult(False,say('order'))
            flags["acceptance"] = flags.get("acceptance", 0) + 1
            self.restore_resource('lucidity', 3)
            self.close_event_dialog()
            event.resolved = True
            self._record_catalog_interaction(event.catalog_id, event.name, "site", event.description)
            self._add_dissolution(12)
            count = flags.get("acceptance", 0)
            if count==3:
                flags['clues']=flags.get('clues',0)+1
                self.messages.append(say('third'))
            message = tr("承担 {count}/3。梦记下了这个承认。", count=count)
            self.messages.append(message)
            return ActionResult(True, message, {"event": event.event_id})

        if action == "gate_accept":
            count = flags.get("acceptance", 0)
            if count < 2:
                message = tr("审判门纹丝不动——承担 {count}/3，还差得远。", count=count)
                self.messages.append(message)
                return ActionResult(False, message, {"gate": "acceptance"})
            self.close_event_dialog()
            return self.epilogue_advance(act.get("advance", 30))

        if action == "deep_dive":
            self.close_event_dialog()
            return self.enter_epilogue()

        if action == "wake":
            self.close_event_dialog()
            flags["ending"] = "A"
            self.ending_id = "A"
            self.victory = True
            self.run_over = True
            message = tr("你选择了清晨。")
            self.messages.append(message)
            return ActionResult(True, message, {"ending": "A"})

        if action == "finish":
            ending = act.get("ending", "B")
            if ending not in ('B','C','D'):
                return ActionResult(False,tr("这个选项什么也没发生。"))
            require_clues = act.get("require_clues", 0)
            if act.get("require_scribe_dead") and not self._epilogue_scribe_dead():
                message = tr("执笔者还在写着。笔没有空出来。")
                self.messages.append(message)
                return ActionResult(False, message, {"gate": "scribe"})
            if flags.get("clues", 0) < require_clues:
                message = tr("自我线索不足（{have}/{need}）——这样的你还撑不起这个结局。", have=flags.get("clues", 0), need=require_clues)
                self.messages.append(message)
                return ActionResult(False, message, {"gate": "clues"})
            need_imagination = act.get("require_imagination", 0)
            if need_imagination and self.imagination < need_imagination:
                message = tr("想象力不足（{have}/{need}）——共写是要花力气的。", have=self.imagination, need=need_imagination)
                self.messages.append(message)
                return ActionResult(False, message, {"gate": "imagination"})
            self.close_event_dialog()
            flags["ending"] = ending
            if need_imagination:
                from ..settlement import REASON_STORY, settle_delta
                settle_delta(self, 'imagination', -need_imagination,
                             reason=REASON_STORY, source='结局代价')
            event.resolved=True
            self.ending_id = ending
            self.victory = True
            self.run_over = True
            message = tr("故事到了最后一页……")
            self.messages.append(message)
            return ActionResult(True, message, {"ending": ending})

        if action in {'gallery','fragment','challenge'}:
            from ..epilogue import say
            if action=='challenge':
                boss=next((e for e in self.enemies if e.catalog_id=='anomaly.scribe' and e.integrity>0),None)
                if boss is None:return ActionResult(False,say('dead'))
                boss.alert_state='追踪'
                boss.last_seen_x,boss.last_seen_y=self.player.x,self.player.y
                message=say('challenge_text')
            else:
                event.resolved=True
                if action=='fragment':
                    flags['clues']=flags.get('clues',0)+1
                    flags.setdefault('pages',[]).append(event.event_id)
                message=say('clue' if action=='fragment' else 'gallery_reply')
            self.close_event_dialog()
            self.messages.append(message)
            self.run_stats['events']=self.run_stats.get('events',0)+1
            return ActionResult(True,message,{'event':event.event_id})

        message = tr("这个选项什么也没发生。")
        self.messages.append(message)
        return ActionResult(False, message)
    # ---- 容器物品：盛装 / 倒出（2026-09-19）----
    # 同格不变式：任何倒入都经 _mix_liquids / _resolve_material_arrivals 归一，
    # 一个格子永远只存在一种液态记忆与一种弥散印象。互不相容的材料在归一
    # 时互相排斥或部分消失（配方优先 → 强者通吃/水被同化）；可燃物遇火焰
    # 在燃烧通道起火，高浓度可燃气遇火在 _ignite_cell 引爆。

    def _separate_anomalies_at(self, x: int, y: int, exclude=None) -> int:
        """把 (x,y) 上堆叠的异象弹开到最近的空格（不消耗任何回合）。"""
        moved = 0
        for entity in list(self.enemies):
            if entity is exclude or entity.integrity <= 0:
                continue
            if (entity.x, entity.y) != (x, y):
                continue
            found = None
            for radius in range(1, 7):
                ring = [
                    (x + dx, y + dy)
                    for dy in range(-radius, radius + 1)
                    for dx in range(-radius, radius + 1)
                    if max(abs(dx), abs(dy)) == radius
                ]
                ring.sort(
                    key=lambda c: -max(abs(c[0] - self.player.x), abs(c[1] - self.player.y))
                )
                for nx, ny in ring:
                    if not (0 < nx < self.width - 1 and 0 < ny < self.height - 1):
                        continue
                    if self.cell(nx, ny).solid or self.entity_at(nx, ny) is not None:
                        continue
                    found = (nx, ny)
                    break
                if found:
                    entity.x, entity.y = found
                    moved += 1
                    self.messages.append(tr("{name}被挤开了。", name=tr(entity.label)))
                    break
        return moved

    def _container_spec(self, item) -> dict:
        return ITEM_DEFINITIONS.get(item.definition_id, {}).get("container") or {}

    @root_action
    def container_fill(self, index: int) -> ActionResult:
        """盛装：把本格子的液体/气体装入容器（受上限与种类约束）。"""
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        from ...equipment import gear_tools
        if gear_tools.suit_sealed(self):
            return ActionResult(False, tr("工作服的外层还封着——先解开再盛装。"))
        item = self.inventory[index]
        spec = self._container_spec(item)
        medium = spec.get("medium", "liquid")
        multi = bool(spec.get("multi"))
        cap = int(spec.get("cap", 30))
        px, py = self.player.x, self.player.y
        cell = self.cell(px, py)
        contents = item.contents
        if medium == "liquid":
            if cell.liquid <= 0 or not cell.liquid_kind:
                return ActionResult(False, tr("本格没有可盛装的液态记忆。"))
            kind = cell.liquid_kind
        else:
            if cell.gas <= 0 or not cell.gas_kind:
                return ActionResult(False, tr("本格没有可盛装的弥散印象。"))
            kind = cell.gas_kind
        if not multi and contents and kind not in contents:
            holder = next(iter(contents))
            return ActionResult(
                False,
                tr("{item}里已经装着{old}，先倒出再盛。", item=tr(item.name), old=tr(holder)),
            )
        left = cap - sum(contents.values())
        if left <= 0:
            return ActionResult(False, tr("{item}已经装满了。", item=tr(item.name)))
        if medium == "liquid":
            taken = min(left, cell.liquid)
            cell.liquid -= taken
            if cell.liquid <= 0:
                cell.liquid_kind = ""
        else:
            taken = min(left, cell.gas)
            self._prime_material_clocks(cell)
            self._remember_sealed_gas_age(item,kind,cell.material_clocks['decay:' + kind])
            cell.gas -= taken
            if cell.gas <= 0:
                cell.gas_kind = ""
        contents[kind] = contents.get(kind, 0) + taken
        if medium == "liquid" and self.insight_active("先让它沉下去"):
            # 洞察「先让它沉下去」：刚相变完的这一格，第一次取液不沾表面附着。
            from .. import phase_changes
            if phase_changes.settled(self, cell):
                phase_changes.arm_settled_grab(self, px, py)
        self._sync_material_position(px, py)
        self._action_time(self._dream_action_time(1, 'materials'), ActionKind.USE)
        message = tr("盛装了 {kind} ×{n}（{left}/{cap}）。", kind=tr(kind), n=taken, left=sum(contents.values()), cap=cap)
        self.messages.append(message)
        return ActionResult(True, message, {"container": index, "fill": taken})

    @root_action
    def container_pour(self, index: int) -> ActionResult:
        """倒出：把容器内的内容全部倒在本格（统一走 _add_liquid/_add_gas 全流程）。

        修复（2026-09-22）：旧版手写归一跳过了 PENDING 消费/植物淹死/索引同步——
        导致倒出引发的不稳定爆炸标记泄漏（在无关格子产生伪爆炸）以及
        倒水淹不死植物。现在统一走批量入口，与喷枪/流动/泄漏同口径。
        """
        if not (0 <= index < len(self.inventory)):
            return ActionResult(False, tr("意识行囊中没有这个承载位。"))
        item = self.inventory[index]
        spec = self._container_spec(item)
        medium = spec.get("medium", "liquid")
        contents = item.contents
        if not contents:
            return ActionResult(False, tr("{item}是空的。", item=tr(item.name)))
        px, py = self.player.x, self.player.y
        cell = self.cell(px, py)
        # 先看落差（expansion.terrain.i01）：看得见相邻更低的一格时，一次倾倒只走一半，
        # 剩下的留在容器里等下一次确认——描述里的「中途停止保留未倒材料」就是没倒的
        # 那一半。**只分两段**：接着倒的那一次把剩下的倒完（凭据按实例记，用掉即删）。
        stage = contents
        split = False
        split_memo = self.realm_features.setdefault("pour_split", {})
        if len(split_memo) > 32:      # 旧存档里的实例 id 不会自己消失，顺手收一下
            split_memo.clear()
        pending = bool(split_memo.pop(item.instance_id, None))
        if (medium == "liquid" and not pending and self.insight_active("先看落差")):
            from ..expansion_insights import pour_drop_seen, pour_stage
            if pour_drop_seen(self):
                staged = pour_stage(contents)
                total = sum(int(value) for value in contents.values())
                if 0 < sum(staged.values()) < total:
                    stage = staged
                    split = True
                    split_memo[item.instance_id] = True
        poured: list[str] = []
        for kind, amount in list(stage.items()):
            if medium == "liquid":
                self._add_liquid(cell, kind, amount)
            else:
                self._add_gas(cell, kind, amount,
                              decay_mark=self.time-item.gas_decay_age.get(kind,0))
            poured.append(tr(kind))
        if split:
            for kind, amount in stage.items():
                left = int(contents.get(kind, 0)) - int(amount)
                if left > 0:
                    contents[kind] = left
                else:
                    contents.pop(kind, None)
            for kind in list(item.gas_decay_age):
                if kind not in contents:
                    item.gas_decay_age.pop(kind, None)
        else:
            contents.clear()
            item.gas_decay_age.clear()
        self._sync_material_position(px, py)
        if cell.flame > 0:
            self._ignite_cell(px, py, by_player=True)
        self._action_time(self._dream_action_time(1, 'materials'), ActionKind.USE)
        message = tr("倒出了 {kinds}。", kinds="、".join(poured))
        if split:
            message += tr("先看落差：这一手只走了一半，剩下的还在容器里——"
                          "看过这一段的反应，再倒一次才倒完。")
        self.messages.append(message)
        return ActionResult(True, message, {"container": index, "poured": poured,
                                            "split": split})

    # ---- 稳定意识（NPC）交易与对话（2026-09-18）----

    def _adjacent_npc(self):
        """相邻（切比雪夫距离 1）的存活稳定意识；没有则 None。"""
        return next(
            (
                entry for entry in self.enemies
                if entry.relation == "稳定意识" and entry.integrity > 0
                and max(abs(entry.x - self.player.x), abs(entry.y - self.player.y)) <= 1
            ),
            None,
        )

    def pending_npc(self):
        """当前唤起对话的稳定意识（没有则 None）。"""
        return next(
            (entry for entry in self.enemies
             if entry.relation == "稳定意识" and entry.integrity > 0
             and entry.id == getattr(self, "pending_npc_id", None)),
            None,
        )

    def close_npc_dialog(self) -> None:
        self.pending_npc_id = None

    #: 代价字段的运行期实现口径：已知字段来自 data.validation（同一份表），
    #: 但「认识」不等于「会结算」——没实现的成本类型必须报错，不能默默免费。
    _IMPLEMENTED_COST_FIELDS = frozenset({
        "mind", "lucidity", "imagination", "cap", "items", "random_gear",
        "consumables", "liquid",
    })

    #: 代价里的上限名 → 人话（面板与导表共用同一口径）；下限同 run_options 的 penalties。
    CAP_FLOOR = 10

    def _assert_known_cost(self, cost: dict) -> None:
        """未知／未实现的成本类型＝数据错误（方案 §2.1：不能默默不扣）。"""
        from ...data.validation import COST_FIELDS
        unknown = set(cost) - COST_FIELDS
        if unknown:
            raise ValueError(f"NPC 交易出现了未知成本类型：{sorted(unknown)}")
        unimplemented = set(cost) - self._IMPLEMENTED_COST_FIELDS
        if unimplemented:
            raise ValueError(f"NPC 交易成本尚未实现结算：{sorted(unimplemented)}")

    def _consumable_pool(self) -> list:
        return [entry for entry in self.inventory if entry.category in ("摄入物", "易逝物")]

    def _consumable_payment_plan(self, need: int) -> list[tuple[Any, int]]:
        """按**件数**（不是按库存条目）凑出要交的消耗品：大堆先扣，少拆几组。

        旧实现是「随机挑一个条目、整组删掉」：检查按条目数、支付按整堆，
        交 3 件可能吞掉一组 12 件。这里检查、预览、扣费用同一份计划。
        """
        plan: list[tuple[Any, int]] = []
        remaining = need
        for entry in sorted(self._consumable_pool(),
                            key=lambda item: (-item.quantity, item.instance_id)):
            if remaining <= 0:
                break
            taken = min(entry.quantity, remaining)
            plan.append((entry, taken))
            remaining -= taken
        return plan

    def _tray_cell(self, npc) -> tuple[int, int]:
        """委托人脚下那格＝交付托盘（液体任务的倒入口／扣费口）。"""
        return int(npc.x), int(npc.y)

    def _take_tray_liquid(self, position: tuple[int, int], kind: str, amount: int) -> int:
        """从托盘格扣液体，返回实际扣掉的量（走材料层同一条读数与同步口径）。"""
        cell = self.cell(*position)
        if cell.liquid_kind != kind or cell.liquid <= 0:
            return 0
        taken = min(int(cell.liquid), int(amount))
        cell.liquid -= taken
        if cell.liquid <= 0:
            cell.liquid_kind = ""
        self._sync_material_position(*position)
        return taken

    def _check_npc_cost(self, cost: dict, npc=None) -> str | None:
        """校验交易代价：可支付返回 None，否则返回拒绝原因文案。

        心智/清醒度按「不足或刚好归 0 都不卖」结算（ value > cost 才放行）；
        想象力与联想盘反馈同口径（够就付得下去，可以付到 0）。
        """
        if not cost:
            return None
        self._assert_known_cost(cost)
        if "mind" in cost:
            if self.mind <= cost["mind"]:
                return tr("心智不足。")
        if "lucidity" in cost:
            if self.lucidity <= cost["lucidity"]:
                return tr("清醒度不足。")
        if "imagination" in cost:
            if self.imagination < cost["imagination"]:
                return tr("想象力不足。")
        if "cap" in cost:
            # §16.1「上限不能不足额钳制」：掉到地板以下的那部分付不出来，整笔就该拒绝，
            # 而不是写着「上限 −5」实际只减 2。
            from ..content import STAT_LABELS
            stat, amount = cost["cap"]
            if getattr(self, stat) - int(amount) < self.CAP_FLOOR:
                return tr("{stat}上限已经低到付不出这笔代价了。",
                          stat=tr(STAT_LABELS.get(stat, stat)))
        if "items" in cost:
            item_id, count = cost["items"]
            target = ITEM_DEFINITIONS.get(item_id, {}).get("name", item_id)
            owned = sum(entry.quantity for entry in self.inventory if entry.definition_id == item_id)
            if owned < count:
                return tr("{item}不足。", item=tr(target))
        if "random_gear" in cost:
            gear = [entry for entry in self.inventory if entry.slot]
            if len(gear) < cost["random_gear"]:
                return tr("可支付的携带意象不足。")
        if "consumables" in cost:
            need = int(cost["consumables"])
            owned = sum(entry.quantity for entry in self._consumable_pool())
            if owned < need:
                return tr("摄入物/易逝物不足（要 {need} 件，只有 {owned} 件）。",
                          need=need, owned=owned)
        if "liquid" in cost:
            kind, amount = cost["liquid"]
            if npc is None:
                return tr("这项交易没有可交付的托盘。")
            cell = self.cell(*self._tray_cell(npc))
            held = cell.liquid if cell.liquid_kind == kind else 0
            if held < amount:
                return tr("托盘上的{kind}不足（要 {need}，只有 {held}）。",
                          kind=tr(kind), need=amount, held=held)
        return None

    def _charge_npc_cost(self, cost: dict, rng, npc=None) -> list[str]:
        """扣除交易代价（先校验后扣），返回给界面的说明文本。"""
        texts: list[str] = []
        if not cost:
            return texts
        self._assert_known_cost(cost)
        from ..settlement import REASON_TRADE_COST, settle_delta
        if "mind" in cost:
            settle_delta(self, 'mind', -cost["mind"], reason=REASON_TRADE_COST,
                         source='交易代价')
            texts.append(tr("心智 −{n}", n=cost["mind"]))
        if "lucidity" in cost:
            settle_delta(self, 'lucidity', -cost["lucidity"], reason=REASON_TRADE_COST,
                         source='交易代价')
            texts.append(tr("清醒度 −{n}", n=cost["lucidity"]))
        if "imagination" in cost:
            # 夜药剂师一类标了想象力成本的交易过去根本不走这里——标多少就得付多少。
            settle_delta(self, 'imagination', -cost["imagination"],
                         reason=REASON_TRADE_COST, source='交易代价')
            texts.append(tr("想象力 −{n}", n=cost["imagination"]))
        if "cap" in cost:
            stat, amount = cost["cap"]
            setattr(self, stat, max(self.CAP_FLOOR, getattr(self, stat) - amount))
            setattr(self, stat.replace("max_", ""), min(getattr(self, stat), getattr(self, stat.replace("max_", ""))))
            texts.append(tr("{stat}上限 −{n}", stat=tr(stat), n=amount))
        if "items" in cost:
            item_id, count = cost["items"]
            remaining = count
            for index in range(len(self.inventory) - 1, -1, -1):
                entry = self.inventory[index]
                if entry.definition_id == item_id and remaining > 0:
                    taken = min(entry.quantity, remaining)
                    entry.quantity -= taken
                    remaining -= taken
                    if entry.quantity <= 0:
                        self.inventory.pop(index)
            texts.append(tr("{item} ×{n}", item=tr(ITEM_DEFINITIONS.get(item_id, {}).get("name", item_id)), n=count))
        if "random_gear" in cost:
            remaining = cost["random_gear"]
            while remaining > 0:
                gear = [entry for entry in self.inventory if entry.slot]
                if not gear:
                    break
                pick = gear[rng.randrange(len(gear))]
                self.inventory.remove(pick)
                if self.hang_item_id == pick.instance_id:
                    self.hang_item_id = None
                # 交出去的意象必须同时从联想盘上拆下来：否则盘面留着一条引用
                # 已不存在实例的语句（编译时被过滤掉，玩家却看不出少了什么）。
                if self.board.placement(pick.instance_id) is not None:
                    self.board_remove_instance(pick.instance_id, charge_time=False, quiet=True)
                    texts.append(tr("交出 {item}（联想盘上的语句已拆开）", item=tr(pick.name)))
                else:
                    texts.append(tr("交出 {item}", item=tr(pick.name)))
                remaining -= 1
        if "consumables" in cost:
            for entry, taken in self._consumable_payment_plan(int(cost["consumables"])):
                entry.quantity -= taken
                if entry.quantity <= 0:
                    self.inventory.remove(entry)
                texts.append(tr("交出 {item} ×{n}", item=tr(entry.name), n=taken))
        if "liquid" in cost:
            kind, amount = cost["liquid"]
            taken = self._take_tray_liquid(self._tray_cell(npc), kind, amount) if npc is not None else 0
            texts.append(tr("托盘扣除{kind} ×{n}", kind=tr(kind), n=taken))
        return texts

    def _consume_quest_delivery(self, quest_id: str, npc) -> list[str] | None:
        """兑现任务时扣掉交付物：液体任务从委托人的托盘格里扣。

        先读够不够、再扣——不做「扣了一半发现不够」的半交易。返回 None 表示
        交付物在检查与兑现之间没了（被蒸发／被舀走），此时任务保持 active。
        具名记录类交付从行囊里扣（回收／递送模板 §7.1 模板 3）。
        """
        from ..content import QUEST_DEFINITIONS
        requirement = (QUEST_DEFINITIONS.get(quest_id) or {}).get("requirement") or {}
        if requirement.get("type") == "item":
            item_id = requirement.get("item", "")
            amount = int(requirement.get("count", 1))
            held = sum(entry.quantity for entry in self.inventory
                       if entry.definition_id == item_id)
            if held < amount:
                return None
            taken = 0
            name = ""
            for entry in list(self.inventory):
                if taken >= amount:
                    break
                if entry.definition_id != item_id or entry.quantity <= 0:
                    continue
                grab = min(entry.quantity, amount - taken)
                entry.quantity -= grab
                taken += grab
                name = entry.name
                if entry.quantity <= 0:
                    self.inventory.remove(entry)
            return [tr("交付{item} ×{n}", item=tr(name), n=taken)]
        if requirement.get("type") != "liquid":
            return []
        kind = requirement.get("liquid")
        amount = int(requirement.get("count", 1))
        position = self._tray_cell(npc)
        cell = self.cell(*position)
        held = cell.liquid if cell.liquid_kind == kind else 0
        if held < amount:
            return None
        taken = self._take_tray_liquid(position, kind, amount)
        return [tr("交付{kind} ×{n}", kind=tr(kind), n=taken)]

    def _reward_fits(self, item_id: str, count: int = 1) -> bool:
        """Predict the slots needed by repeated one-item grants without mutating stacks."""
        definition = ITEM_DEFINITIONS.get(item_id) or {}
        if definition.get("category") == "记忆碎片" or count <= 0:
            return True
        max_stack = max(1, int(definition.get("max_stack", 1) or 1))
        merge_space = sum(max(0, entry.max_stack - entry.quantity)
                          for entry in self.inventory
                          if entry.definition_id == item_id and entry.max_stack > 1)
        remaining = max(0, count - merge_space)
        slots = (remaining + max_stack - 1) // max_stack
        return self.inventory_used + slots <= self.inventory_capacity

    def _gain_refusal(self, gain, *, source='reward') -> str | None:
        """提交前验证「所得装得下」：满行囊时拒绝，而不是先扣费再抛异常。

        判据与 ``state._add_inventory_item`` 完全同一条（可堆叠且现有堆没满＝
        还能并进去），所以「预检说能装」与「真发放」不会各说各话。
        """
        if not gain or not gain.get("item"):
            return None
        item_id = gain["item"]
        from ..item_access import refusal as item_grant_refusal
        count = max(0, int(gain.get('count', 1)))
        reason = item_grant_refusal(self, item_id, source=source, count=count)
        if reason:
            return reason
        definition = ITEM_DEFINITIONS.get(item_id) or {}
        if definition.get("category") == "记忆碎片":
            return None
        if not self._reward_fits(item_id, count):
            return tr("意识行囊已满，装不下 {item}。",
                      item=tr(definition.get("name", item_id)))
        return None

    def _grant_npc_gain(self, gain, rng, *, source='reward') -> list[str]:
        """发放交易所得，返回给界面的说明文本。"""
        texts: list[str] = []
        if not gain:
            return texts
        if gain.get("item"):
            reason = self._gain_refusal(gain, source=source)
            if reason:
                raise ValueError(reason)
            from ..item_access import record_grant
            for _ in range(max(0, int(gain.get('count', 1)))):
                item = self._make_item(gain["item"])
                if item.category == "记忆碎片":
                    self._add_memory(item.definition_id)
                else:
                    self._add_inventory_item(item)
                record_grant(self, item.definition_id, source=source)
                texts.append(tr("获得 {item}。", item=tr(item.name)))
        if gain.get("insight"):
            texts.append(self._grant_insight(gain["insight"]))
        if gain.get("random_insight"):
            # 盲盒洞察（小魔鬼的便宜情报）：从**还没学到**的洞察里随机给一条，
            # 谈的时候不给名字——这正是它比「说清了的那条」便宜的原因。
            from ..content import INSIGHT_DEFINITIONS
            from ..item_access import insight_learnable
            pool = [name for name in INSIGHT_DEFINITIONS
                    if name not in self.insights and insight_learnable(self, name)]
            if pool:
                texts.append(self._grant_insight(pool[rng.randrange(len(pool))]))
            else:
                texts.append(tr("他翻了半天口袋，摊手：没有你还没见过的东西了。"))
        if gain.get("restore"):
            which = gain["restore"]
            from ..settlement import REASON_RESTORE_SCENE, settle_delta
            if which == "mind":
                settle_delta(self, 'mind', self.max_mind - self.mind,
                             reason=REASON_RESTORE_SCENE, source='交易/事件奖励')
                texts.append(tr("心智恢复完全。"))
            elif which == "lucidity":
                settle_delta(self, 'lucidity', self.max_lucidity - self.lucidity,
                             reason=REASON_RESTORE_SCENE, source='交易/事件奖励')
                texts.append(tr("清醒度恢复完全。"))
            else:
                settle_delta(self, 'imagination', self.max_imagination - self.imagination,
                             reason=REASON_RESTORE_SCENE, source='交易/事件奖励')
                texts.append(tr("想象力恢复完全。"))
        if gain.get("restore_all"):
            from ..settlement import REASON_RESTORE_SCENE, settle_delta
            settle_delta(self, 'mind', self.max_mind - self.mind,
                         reason=REASON_RESTORE_SCENE, source='交易/事件奖励')
            settle_delta(self, 'lucidity', self.max_lucidity - self.lucidity,
                         reason=REASON_RESTORE_SCENE, source='交易/事件奖励')
            settle_delta(self, 'imagination', self.max_imagination - self.imagination,
                         reason=REASON_RESTORE_SCENE, source='交易/事件奖励')
            texts.append(tr("三项意识指标全部恢复。"))
        if gain.get("stat"):
            stat, amount = gain["stat"]
            setattr(self, stat, getattr(self, stat) + amount)
            if stat.startswith("max_"):
                base = stat.replace("max_", "")
                setattr(self, base, min(getattr(self, stat), getattr(self, base) + amount))
            texts.append(tr("{stat} +{n}", stat=tr(stat), n=amount))
        return texts

    @root_action
    def choose_npc_option(self, index: int) -> ActionResult:
        """稳定意识对话：结算底部第 index 个选项（0 起）。

        下标是**显示序**（= 这名 NPC 抽到的第几项，见 content.npc_options_for），
        不是整张交易表的下标。代价不足（或刚好把心智/清醒度付到 0）时交易不成立，
        对话保持打开。
        """
        from ..content import (npc_effective_options, npc_option_key, npc_trade_key,
                              quest_baseline, quest_name, quest_progress,
                              quest_requirement_text)
        if self.run_over:
            return ActionResult(False, tr("这一局已经结束。"))
        npc = self.pending_npc()
        if npc is None:
            return ActionResult(False, tr("没有正在进行的对话。"))
        # 篡改视图（规格 §8.1）：与面板同一份已求值可见选项；副本自带原 option_id，
        # 交易记账、赠品与任务口径都不受影响。
        options = npc_effective_options(self, npc)
        if not (0 <= index < len(options)):
            return ActionResult(False, tr("没有这个选项。"))
        option = options[index]
        trade_key = npc_trade_key(npc)
        if option.get('tutorial_control'):
            from ..origin_course import control
            return control(self,option['tutorial_control'])
        if option.get('hospital_scene'):
            from ..hospital_scenes import resolve_hospital_npc
            return resolve_hospital_npc(self, npc, option['hospital_scene'])
        # 记账口径（§2.1／§13.2）：一次性记录用稳定 option_id，index 只是 UI 展示序。
        option_id = npc_option_key(npc, option)
        from ..npc_offers import free_claim_refusal, record_free_claim
        refusal = free_claim_refusal(self, npc, option)
        if refusal:
            return ActionResult(False, refusal, {'npc': npc.id, 'refusal': True})
        if option.get("circuit_hint"):
            board = min(self.circuit_boards, default=None,
                        key=lambda b: min(abs(n["pos"][0]-npc.x)+abs(n["pos"][1]-npc.y)
                                          for n in b["nodes"].values()))
            hint = board.get("hint", "先观察输入与输出之间的线路。") if board else "先观察输入与输出之间的线路。"
            message = tr("{name}：{reply}", name=tr(npc.label), reply=tr(hint))
            self.messages.append(message)
            return ActionResult(True, message, {"npc": npc.id, "circuit_hint": True})
        if option.get('deep_dialogue') and self.depth in (28,29):
            return self._epilogue_npc_option(npc,option['deep_dialogue'])
        if option.get("puzzle") and self.realm_id == "toy_memories":
            operation = option["puzzle"]
            if operation == "reset":
                return self.reset_realm_puzzle()
            if operation == "return":
                self.close_npc_dialog()
                self._exit_realm()
                return ActionResult(True, self.messages[-1], {"realm_exit": True})
            self.talk_toy_keeper(npc)
            message = (tr("谜题已完成。") if self.realm_puzzle_solved.get(self.realm_depth)
                       else tr(self.circuit_boards[0].get('hint', '回路尚未闭合，请观察各输入的状态。')))
            self.messages.append(message)
            return ActionResult(True, message)
        if option.get("enter_realm"):
            # 梦中梦入口 NPC（引火人）：已在位面内 / 本局已关门时拒绝，否则进入。
            realm_id = option["enter_realm"]
            if self.realm_id or realm_id in self.closed_realms:
                return ActionResult(False, tr("这扇门已经关上了——本局不会再为你打开。"))
            self.close_npc_dialog()
            self.enter_realm(realm_id)
            return ActionResult(True, self.messages[-1], {"npc": npc.id, "realm": realm_id})
        if option.get("negotiate"):
            return self._negotiate_option(npc, option)
        if option.get("leave"):
            self.close_npc_dialog()
            self.messages.append(tr("你向{name}道别。", name=tr(npc.label)))
            return ActionResult(True, self.messages[-1], {"dialogue_closed": npc.id})
        if option.get("message") and not option.get("cost") and not option.get("gain"):
            # 纯对话选项（2026-09-19）：只说话——不交易、不记账、不耗回合。
            # 教学向导一类的纯 NPC 靠它陪聊；对话保持打开，可以接着选。
            # 部分书库台词是「多行元组」：逐行取词后合成一条消息，不能把元组的
            # repr 直接塞进日志（英文会显示成 ('…',)）。
            reply = option["message"]
            if isinstance(reply, (tuple, list)):
                reply_text = " ".join(text for text in (tr(part) for part in reply) if text)
            else:
                reply_text = tr(reply)
            self.messages.append(tr("{name}：{reply}", name=tr(npc.label), reply=reply_text))
            return ActionResult(True, self.messages[-1], {"npc": npc.id, "option": option_id})
        if option.get("accept_quest"):
            # 接取任务：登记进任务簿（已接或已完成则拒绝）。
            quest_id = option["accept_quest"]
            if quest_id in self.quests:
                refusal = tr("这项任务已经在任务簿里了。")
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            from ...world import tasks
            from ..content import QUEST_DEFINITIONS
            record = None
            if (QUEST_DEFINITIONS.get(quest_id) or {}).get("template"):
                # 目标实例任务：接活前先把实例绑到真实存在的目标与场所上，
                # 绑不上就不开单——「这一层根本没有那处泵房」不能变成一张空任务。
                record, reason = tasks.bind(self, quest_id, npc)
                if record is None:
                    self.messages.append(reason)
                    return ActionResult(False, reason, {"npc": npc.id, "refusal": True})
            self.quests[quest_id] = "active"
            # 接取瞬间的累计量快照：此后进度按差值算，接活之前杀掉的怪不计入本次狩猎
            # （§16.1「接取前击杀不计完整狩猎」）。
            self.quest_baselines[quest_id] = quest_baseline(self, quest_id)
            from ...world.transactions import record_offer
            # 接活是一次可归因的「签署」：之后任务进度只认接取之后的事实（§7.3）。
            record_offer(self, npc, option_id, kind="pact", target_uid=quest_id)
            self.close_npc_dialog()
            message = tr("接取任务「{name}」。", name=tr(quest_name(quest_id)))
            if record is not None:
                message = tr("{message}（{why}）", message=message,
                             why=tasks.status_text(self, record))
            self.messages.append(message)
            return ActionResult(True, message, {"npc": npc.id, "quest": quest_id})
        if option.get("complete_quest"):
            # 兑现任务：进度达标才成立；成立即结算所得并关闭对话。
            quest_id = option["complete_quest"]
            if self.quests.get(quest_id) != "active":
                refusal = tr("先接取这个任务再来兑现。")
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            from ...world import tasks
            from ..content import QUEST_DEFINITIONS
            # 目标实例任务：归属、销过账没有、场所够不够得先整笔问过世界记录，
            # 拒付时不扣任何东西也不耗回合（§7.3）。
            record = (tasks.lookup(self, quest_id)
                      if (QUEST_DEFINITIONS.get(quest_id) or {}).get("template") else None)
            if record is not None:
                reason = tasks.refusal(self, record, option)
                if reason:
                    self.messages.append(reason)
                    return ActionResult(False, reason, {"npc": npc.id, "refusal": True})
            have, need = quest_progress(self, quest_id)
            if have < need:
                refusal = tr("还没达成：{req}（{have}/{need}）。", req=quest_requirement_text(quest_id), have=have, need=need)
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            gain = tasks.reward_gain(self, record, option) if record is not None else option.get("gain", {})
            refusal = self._gain_refusal(gain, source='npc:' + npc.catalog_id)
            if refusal:
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            if option.get("cost"):
                refusal = self._check_npc_cost(option["cost"], npc)
                if refusal:
                    self.messages.append(refusal)
                    return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            # 交付物扣除与达标检查在同一个事务里（§2.1：报童交货过去只查不扣）。
            delivered = self._consume_quest_delivery(quest_id, npc)
            if delivered is None:
                refusal = tr("交付物已经不在了——重新把{req}备好再来。",
                             req=quest_requirement_text(quest_id))
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            self.quests[quest_id] = "done"
            rng = random.Random(self.seed ^ (self.time * 7919) ^ stable_seed(option_id))
            cost_texts = self._charge_npc_cost(option.get("cost", {}), rng, npc) if option.get("cost") else []
            gain_texts = self._grant_npc_gain(gain, rng, source='npc:' + npc.catalog_id)
            from ...world.transactions import record_offer
            record_offer(self, npc, option_id, kind="settle", target_uid=quest_id,
                         amount=len(delivered))
            settled = tasks.settle(self, record, option) if record is not None else []
            self._action_time(1, ActionKind.USE)
            detail = join_details(delivered + cost_texts + gain_texts + settled)
            message = tr("任务兑现「{name}」。{detail}", name=tr(quest_name(quest_id)), detail=detail)
            self.messages.append(message)
            return ActionResult(True, message, {"npc": npc.id, "quest": quest_id, "done": True})
        if option.get("gift_set"):
            # 免费赠品组：同一组限领一次，领完关闭对话。
            # 2026-10-12：带 cost 的礼品（引路人的「陪他站一段夜岗」并入三选一）
            # 在这条分支里也要照常收费——否则代价字段在礼品分支里被无声跳过。
            set_id = option["gift_set"]
            from ..npc_offers import gift_claimed, is_trade, original_option
            paid_offer = is_trade(original_option(npc, option))
            already_claimed = (option_id in self.npc_traded_options.get(trade_key, ())
                               if paid_offer else gift_claimed(self, npc, set_id))
            if already_claimed:
                refusal = tr("这一组赠品你已经领过了。")
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            rng = random.Random(self.seed ^ (self.time * 104729) ^ stable_seed(option_id))
            if option.get("cost"):
                refusal = self._check_npc_cost(option["cost"], npc)
                if refusal:
                    self.messages.append(refusal)
                    return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            # 先确认装得下再占用「限领一次」：否则满行囊会白吃掉这次领取资格。
            refusal = self._gain_refusal(option.get("gain"), source='npc:' + npc.catalog_id)
            if refusal:
                self.messages.append(refusal)
                return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
            self.gift_claims[set_id] = True
            self.npc_traded_options.setdefault(trade_key, []).append(option_id)
            record_free_claim(self, npc, option)
            cost_texts = self._charge_npc_cost(option["cost"], rng, npc) if option.get("cost") else []
            gain_texts = self._grant_npc_gain(option.get("gain", {}), rng, source='npc:' + npc.catalog_id)
            from ...world.transactions import record_offer
            record_offer(self, npc, option_id, kind="transfer", amount=len(gain_texts))
            self._action_time(1, ActionKind.USE)
            detail = join_details(cost_texts + gain_texts)
            if cost_texts:
                message = tr("你向{name}交清了这一件。{detail}", name=tr(npc.label), detail=detail)
            else:
                message = tr("{name}送了你一件赠品。{detail}", name=tr(npc.label), detail=detail)
            self.messages.append(message)
            self.close_npc_dialog()
            return ActionResult(True, message, {"npc": npc.id, "gift": set_id})
        if option_id in self.npc_traded_options.get(trade_key, []):
            # 一次性交易：每个交易选项只能完成一次（见 npc_traded_options）。
            refusal = tr("这项交易已经完成过了。")
            self.messages.append(refusal)
            return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
        rng = random.Random(self.seed ^ (self.time * 7919) ^ stable_seed(option_id))
        refusal = self._check_npc_cost(option.get("cost", {}), npc)
        if refusal:
            self.messages.append(refusal)
            return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
        refusal = self._gain_refusal(option.get("gain"), source='npc:' + npc.catalog_id)
        if refusal:
            self.messages.append(refusal)
            return ActionResult(False, refusal, {"npc": npc.id, "refusal": True})
        cost_texts = self._charge_npc_cost(option.get("cost", {}), rng, npc)
        gain_texts = self._grant_npc_gain(option.get("gain", {}), rng, source='npc:' + npc.catalog_id)
        # 交易成立即记账：键是稳定 option_id，不是这次的显示下标——
        # 货架重抽、show_if 过滤都会改变显示序，用下标记会把另一项标成已完成。
        self.npc_traded_options.setdefault(trade_key, []).append(option_id)
        record_free_claim(self, npc, option)
        from ...world.transactions import record_offer
        record_offer(self, npc, option_id, kind="transfer",
                     amount=len(cost_texts) + len(gain_texts))
        self._action_time(1, ActionKind.USE)
        detail = join_details(cost_texts + gain_texts)
        message = tr("{name}：{choice}。{detail}", name=tr(npc.label), choice=tr(option["label"]), detail=detail)
        self.messages.append(message)
        return ActionResult(True, message, {"npc": npc.id, "option": option_id})

    def _negotiate_option(self, npc, option: dict) -> ActionResult:
        """§4.4 的交涉分派：状态机与代价结算全在 ``world/relations.py``。

        这里只做两件事：把对话选项映射到关系入口，以及保证**拒绝也原样返回**
        （立场不变、时间不走、资源不动），因此玩家反复点开对话得不到免费冷静期。
        """
        from ...world import relations

        operation = option["negotiate"]
        if operation == "explain":
            return relations.explain(self, npc)
        if operation == "propose":
            return relations.propose_restitution(self, npc)
        return relations.pay_restitution(self, npc)

def join_details(parts: Iterable[str]) -> str:
    """把几段说明串成一句话。

    交付段不带句号、收益与结算段带句号，一律用「，」相接就会写出
    「获得 薄荷锭。，侧门的挡板…」：已经收在句末标点之后的段之间不再补逗号。
    """
    text = ""
    for part in parts:
        if not part:
            continue
        if text:
            if text.endswith((".", "!", "?")):
                text += " "
            elif not text.endswith(("。", "！", "？")):
                text += "，"
        text += part
    return text

def join_details(parts: Iterable[str]) -> str:
    """把几段说明串成一句话。

    交付段不带句号、收益与结算段带句号，一律用「，」相接就会写出
    「获得 薄荷锭。，侧门的挡板…」：已经收在句末标点之后的段之间不再补逗号。
    """
    text = ""
    for part in parts:
        if not part:
            continue
        if text:
            if text.endswith((".", "!", "?")):
                text += " "
            elif not text.endswith(("。", "！", "？")):
                text += "，"
        text += part
    return text
