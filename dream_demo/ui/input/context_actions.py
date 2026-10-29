"""上下文动作族：句子/装备瞄准、_apply 结算、对话与攻击确认、路径跟随。"""
from __future__ import annotations

import time

from textual.events import MouseDown, MouseMove, MouseScrollDown, MouseScrollUp
from textual.widgets import Static

from ...i18n import tr
from ...audio import sfx
from ...core import ABILITY_DEFINITIONS
from ...core.entities import ActionResult
from ...core.tutorial import tutorial_skip_step
from ...materials import PORTENT_DEFINITIONS, TABLE_KINDS, wall_def
from .._native import _trace_native
from ..styles import HOLD_RELEASE_TIMEOUT, MOVE_REPEAT_MIN_SECONDS, RIGHT_PANEL_MODES
from ..effects import projectile_flight_time, projectile_repeat_delay
from ..panels import MEMORY_FOOTER_ITEM_ROWS, TAMPER_ENTRY_ROW
from ..widgets import EventPanel, MapView

ATTACK_CONFIRMATION_SECONDS = 8.0

# 动作命令 → 语义音效事件（AudioBus.SOUND_MAP 同名键）；未列出的动作不发声。
# （第一批 29 个事件已全部接入，素材与触发条件见《音效挂点索引.md》。）
# [SFX挂点] 尚未挂音效的动作命令只剩 wait（等待，可不挂）；
# 新命令在 ACTION_SOUNDS 补一行映射即可接入。
ACTION_SOUNDS = {
    "move": "step",            # 移动（_apply 会按落脚格覆写为液体/植物/冰面脚步）
    "throw": "throw",
    "throw_target": "throw",  # 瞄准投掷（同一件离手声）
    "spray_fire": "fire",
    "spray_target": "fire",
    "fire": "fire",
    "fire_assisted": "fire",   # 辅助瞄准发射（同一把枪声）
    "drop": "throw",           # 放下显化物（复用落地声）
    "pickup": "pickup",
    "collect_items": "pickup",
    "take_from": "pickup",     # 台面取物
    "put_on_table": "throw",   # 放到台面（台面落物声）
    "descend": "descend",
    "backtrack": "backtrack",  # 层间返回（上浮）
    "finish_run": "finish",
    "open": "open",            # 开门/推墙
    "uproot_plant": "uproot",  # 拔植物
    "equip": "equip",          # 穿上携带意象
    "unequip": "equip",        # 脱下（同一声金属扣）
    "toggle_equip": "equip",   # 穿/脱切换
    "use": "use_potion",       # 使用易逝物
    "choose_npc_option": "interact",  # NPC 对话选项确认
    "choose_event_option": "interact",  # 事件选项确认
    # ⚠️ interact 不在此表：打开对话的音效在 _apply_interact / _apply 叠加层里
    # 按「NPC 对话 vs 事件对话」区分（npc / interact 两种）。
}



from ..aiming import AimingMixin

class ContextActionsMixin:
    """上下文动作族：句子/装备瞄准、_apply 结算、对话与攻击确认、路径跟随。"""

    def _cancel_sentence_aim(self):
        self.sentence_aim = None
        self.aiming = False
        self.aim_action_choice = None
        self._aim_assist_pos = None
        self.assist_path = []
        self.panel_mode = self._default_panel_mode()
        self._clear_held()

    def _begin_sentence_aim(self, key):
        self._aim_failed = False
        state = self.session.state
        option = next((o for o in state.equipment.active_sentence_options() if o.key == key), None)
        if option is None:
            self.show_toast(tr('本次动作选项已经失效'), 3)
            return
        self._cancel_attack_confirmation(refresh=False)
        self.equipment_choice = None
        self.aim_action_choice = None
        self.spray_select = None
        self.spray_source = self.throw_item_index = self.fire_once_index = None
        self.path.clear()
        self.observe_walk_path.clear()
        self.observe_mode = False
        self.sentence_aim = dict(key=key, row=option.row, cursor=(state.player.x, state.player.y),
                                 context=self._equipment_choice_context())
        self.aiming = True
        self.panel_mode = self._default_panel_mode()
        self.assist_path = []
        self._clear_held()
        self.refresh_view()

    def _cast_sentence_aim(self, target):
        pending = self.sentence_aim
        if pending is None:
            return
        source = pending.get('source_identity')
        state = self.session.state
        if (pending['context'] != self._equipment_choice_context()
                or source is not None and (source[0] >= len(state.inventory)
                                           or state.inventory[source[0]] is not source[1])):
            self._cancel_sentence_aim()
            self.show_toast(tr('本次动作选项已经失效'), 3)
            self.refresh_view()
            return
        command = pending.get('command', 'use_equipment_sentence')
        args = ((pending['row'], *target) if command == 'use_equipment_sentence' else
                (pending['source_index'], *target) if command == 'spray_target' else target)
        result = self._apply(command, *args, choice=pending['key'])
        if not result.changed:
            # Failed target/resource checks are free; the player can retarget.
            self.sentence_aim = pending
            self.aiming = True
        self.show_toast(result.message, 3)
        self.refresh_view()

    def _sentence_aim_key(self, key):
        directions = {'up': (0,-1), 'down': (0,1), 'left': (-1,0), 'right': (1,0),
                      'num8': (0,-1), 'num2': (0,1), 'num4': (-1,0), 'num6': (1,0)}
        for number, direction in {'1':(-1,1), '2':(0,1), '3':(1,1), '4':(-1,0),
                                  '6':(1,0), '7':(-1,-1), '8':(0,-1), '9':(1,-1)}.items():
            directions.update({number: direction, 'num'+number: direction, 'kp'+number: direction})
        for setting, direction in (('key_up',(0,-1)), ('key_down',(0,1)),
                                    ('key_left',(-1,0)), ('key_right',(1,0))):
            directions[str(self.config.get(setting)).lower()] = direction
        if key in ('escape', 'q'):
            self._cancel_sentence_aim()
        elif key in ('enter', 'return', 'space'):
            self._cast_sentence_aim(self.sentence_aim['cursor'])
        elif key == 'o':
            from ...equipment.positional_events import _target_ok
            from ...equipment.targets import target_matches
            from ...equipment.runtime import condition_matches
            state = self.session.state
            pending = self.sentence_aim
            command = pending.get('command', 'use_equipment_sentence')
            from ...equipment.active import clause_key
            tool_row = next((row for row in state.equipment.formation().actions
                             if command == 'use_equipment_sentence' and row.opcode in ('repair','measure')
                             and clause_key(state.equipment.formation(),row) == pending['key']),None)
            def eligible(enemy):
                cell = (enemy.x, enemy.y)
                if not _target_ok(state, enemy):
                    return False
                if command == 'fire_assisted':
                    plan = state.equipment.plan_action('fire', choice=pending['key'],
                                                       target=enemy, cell=cell)
                    return (plan.valid and max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y))
                            <= min(12, int(dict(plan.projectile_profile).get('range', 12))))
                if command == 'spray_target':
                    from ...core.weapons import SPRAY_RANGE, spray_plan
                    return (max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y)) <= SPRAY_RANGE
                            and spray_plan(state, pending['source_index'] if pending['source_index'] >= 0 else None,
                                      choice=pending['key'], target=enemy, cell=cell).valid
                            )
                return (max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y)) <= 6
                        and any(row.row == pending['row'] and row.opcode == 'imprint'
                                and condition_matches(row.condition, state, target=enemy, cell=cell)
                                and target_matches(row, state, target=enemy, cell=cell)
                                for row in state.equipment.formation().actions))
            if tool_row is not None:
                from ...equipment.tools import tool_assist_targets
                targets = tool_assist_targets(state,tool_row)
            else:
                targets = sorted(((enemy.x, enemy.y) for enemy in state.enemies
                                  if eligible(enemy)),
                                 key=lambda xy: (max(abs(xy[0]-state.player.x), abs(xy[1]-state.player.y)), xy))
            if targets:
                cursor = self.sentence_aim['cursor']
                current = targets.index(cursor) if cursor in targets else -1
                self.sentence_aim['cursor'] = targets[(current+1) % len(targets)]
        elif key in directions:
            state = self.session.state
            x, y = self.sentence_aim['cursor']
            dx, dy = directions[key]
            self.sentence_aim['cursor'] = (max(0, min(state.width-1, x+dx)),
                                            max(0, min(state.height-1, y+dy)))
        else:
            self._cancel_sentence_aim()
            return False
        if key in directions or key == 'o':
            self._refresh_cursor_only()
        else:
            self.refresh_view()
        return True
    def _apply_interact(self):
        """interact 的统一出口：复合事件返回 {"dialogue"} 时唤起事件对话面板。"""
        result = self._apply("interact")
        state = self.session.state
        if result.data.get('pickup_target'):
            self.open_pickup(tuple(result.data['pickup_target']))
            return result
        if result.changed and state.pending_npc() is not None and state.tutorial.get("active"):
            # 教程埋点：对话步只需「跟纸偶说上话」（对话框打开即认可）。
            state.tutorial_events["npc_talked"] = 1
        if result.changed and result.data.get("dialogue"):
            self.panel_mode = "event_dialog"
            self.panel_scroll = 0
            self.event_dialog_scroll = 0
            self.event_dialog_cursor = 0
        return result

    def _close_event_dialog_state(self) -> None:
        """收起对话面板时同步清掉 core 侧的 pending id，避免残留状态。"""
        state = self.session.state
        self._dialog_feedback = None
        # 篡改草稿随对话一起丢（规格 §4.4）：对话关了，编辑的对象就不在眼前了。
        self.close_tamper_editor(refresh=False)
        if state.pending_npc_id is not None:
            state.close_npc_dialog()
        else:
            state.close_event_dialog()

    def _toy_npc_for_depth(self) -> tuple[str, ...]:
        """玩具的回忆：当前层守门人 npc id（恒显集合，含全部三层以便判定）。"""
        from ...data.dreams import DREAM_REALM_DEFINITIONS

        definition = DREAM_REALM_DEFINITIONS.get("toy_memories")
        return tuple(definition.npc_for_layer) if definition else ()

    def _choose_dialog_option(self, index: int) -> None:
        """结算对话选项（键盘数字/Enter 与左键第二击共用）。

        NPC 交易成功后对话保持打开（还有别的选项可挑，已完成的会置灰）；
        「道别」/复合事件结算完毕才收起面板。
        """
        state = self.session.state
        self.event_dialog_cursor = index
        command = "choose_npc_option" if state.pending_npc() else "choose_event_option"
        result = self._apply(command, index)
        # 结算消息贴进对话面板（2026-10-11）：以前只进事件记录，对话里看不到反馈。
        self._dialog_feedback = (result.changed, result.message or "")
        if result.changed and state.pending_npc() is None and state.pending_event() is None:
            self.panel_mode = self._default_panel_mode()
        self.refresh_view()

    def _click_dialog_option(self, index: int) -> None:
        """左键两段式（2026-09-18 应用户要求）：首击只选中（▶ 移过去），
        已选中的项再击才触发。与键盘手感一致：↑↓ 选中、Enter 确认。"""
        if self.event_dialog_cursor != index:
            self.event_dialog_cursor = index
            self.refresh_view()
            return
        self._choose_dialog_option(index)

    def _equipment_choice_context(self):
        state = self.session.state
        # Inventory identity is part of the snapshot: a reordered/consumed stack
        # must invalidate a stale index instead of silently pointing at another item.
        return (id(state), state.action_seq, state.depth, state.realm_id, state.realm_depth,
                state.player.x, state.player.y, state.run_over,
                tuple((enemy.id, enemy.x, enemy.y, enemy.integrity) for enemy in state.enemies),
                tuple((str(getattr(item, 'instance_id', '')), int(getattr(item, 'quantity', 0)))
                      for item in state.inventory),
                int(state.projectile_charges),
                -1 if state.legacy_basic_magazine is None else int(state.legacy_basic_magazine),
                state.equipment.formation().semantic_signature)

    def _choose_equipment_action(self, index):
        pending = self.equipment_choice
        self.equipment_choice = None
        if pending is None:
            return
        if pending['context'] != self._equipment_choice_context():
            self.show_toast(tr('本次动作选项已经失效'), 3)
        elif 0 <= index < len(pending['options']):
            if pending['command'] == 'aim_equipment':
                self._begin_equipment_aim(pending['options'][index],
                                          preserve_aim=bool(pending.get('preserve_aim')))
                return
            if pending['command'] == 'reload_weapon_pick':
                self._perform_reload(pending['options'][index]['key'])
                return
            result = self._apply(pending['command'], *pending['args'],
                                 choice=pending['options'][index]['key'])
            self.show_toast(result.message, 3)
        self.refresh_view()

    def _perform_reload(self, instance_id):
        """Shared reload entry for R, the picker and the HUD button."""
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        result = self._apply('reload_weapon_step', str(instance_id))
        if self.aiming:
            self._aim_failed = False
            self._aim_equipment_identity = self.session.state.equipment.formation().semantic_signature
        self.show_toast(result.message, 3)
        self.refresh_view()
        return result

    def _aim_spray_medium(self):
        selected = self.aim_action_choice
        if selected is not None:
            return selected['kind'][6:] if selected['kind'].startswith('spray_') else None
        from ...core.weapons import hand_spray_medium
        return hand_spray_medium(self.session.state)

    def _begin_equipment_aim(self, option=None, preserve_aim=False):
        # An explicitly identified item must never fall back to a reused index.
        if option and option.get('kind')=='item' and str(option.get('source_key','')).startswith('item:'):
            source_id=option['source_key'][len('item:'):]
            if not any(str(item.instance_id)==source_id and item.quantity>0 for item in self.session.state.inventory):
                self.show_toast(tr('这个一次性来源已经失效。'),3)
                return
        # Starting an aim transaction always closes a pending source table;
        # otherwise the picker would keep swallowing aim keys.
        self.equipment_choice = None
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
        from ...core.weapons import spray_ammo_options
        state = self.session.state
        # Every source suspends queued movement before opening its aim state.
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        if option is not None:
            self._last_firing_source_key = option.get('source_key') or None
        if option is not None and option.get('kind') == 'aggregate':
            # 聚合弹是与装备平等的显式来源，不再靠旧 fire_unlocked 兜底。
            self.aim_action_choice = dict(key='aggregate',kind='fire',definition_ids=[],source_key='aggregate')
            self.fire_once_index = self.throw_item_index = self.spray_source = None
            self.aiming = True
            self.panel_mode = 'actions'
            self._capture_aim_source(keep_cursor=preserve_aim)
            self._revalidate_aim_lock()
            self.refresh_view()
            return
        if option is not None and option.get('kind') == 'item':
            self.aim_action_choice = None
            self.spray_source = None
            self.throw_item_index = None
            # Stable instance identity wins over the row's captured index.
            instance_id = str(option.get('source_key', ''))[len('item:'):] if str(option.get('source_key', '')).startswith('item:') else ''
            index = next((i for i, item in enumerate(state.inventory)
                          if str(getattr(item, 'instance_id', '')) == instance_id), -1)
            if index < 0:
                index = int(option.get('index', -1))
            if not 0 <= index < len(state.inventory):
                self.show_toast(tr('这个一次性来源已经失效。'), 3)
                self.refresh_view()
                return
            self.fire_once_index = index
            self.aiming = True
            self.panel_mode = 'actions'
            self._capture_aim_source(keep_cursor=preserve_aim)
            self._revalidate_aim_lock()
            self.refresh_view()
            return
        self.aim_action_choice = option
        self.fire_once_index = None
        self.throw_item_index = None
        self.spray_source = None
        self._capture_aim_source(keep_cursor=preserve_aim)
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        medium = self._aim_spray_medium()
        state = self.session.state
        plan = state.equipment.plan_action(option['kind'], choice=option['key']) if option else None
        if medium is not None:
            from ...core.weapons import bound_spray_source
            state = self.session.state
            plan = state.equipment.plan_action('spray_' + medium,
                                              choice=option['key'] if option else None)
            if (plan.valid or plan.requires_target) and plan.material_source_id:
                index, reason = bound_spray_source(state, plan, None)
                if reason:
                    self.aim_action_choice = None
                    self.show_toast(tr(reason), 3)
                    self.refresh_view()
                    return
                if plan.requires_target:
                    self._begin_targeted_equipment_aim(option, index, preserve_aim=preserve_aim)
                    return
                self.spray_select = None
                self.spray_source = index
                self.aiming = True
                self._capture_aim_source(keep_cursor=preserve_aim)
                self._revalidate_aim_lock()
                self.panel_mode = 'actions'
                self.refresh_view()
                return
            options = spray_ammo_options(self.session.state, medium)
            if options:
                self.spray_select = dict(cursor=0, options=options, medium=medium)
                self.panel_mode = self._default_panel_mode()
                self.refresh_view()
                return
        if plan is not None and plan.requires_target:
            self._begin_targeted_equipment_aim(option, preserve_aim=preserve_aim)
            return
        self.aiming = True
        self._revalidate_aim_lock()
        self.panel_mode = 'actions'
        self.refresh_view()

    def _begin_targeted_equipment_aim(self, option, source_index=None, preserve_aim=False):
        self._aim_failed = False
        state = self.session.state
        cursor = ((getattr(self, '_aim_free_cursor', None)
                   or getattr(self, '_aim_assist_pos', None)
                   or (state.player.x, state.player.y))
                  if preserve_aim else (state.player.x, state.player.y))
        self.aim_action_choice = None
        self.spray_select = None
        self.spray_source = self.fire_once_index = self.throw_item_index = None
        self.path.clear()
        self.observe_walk_path.clear()
        self.observe_mode = False
        self.sentence_aim = dict(key=option['key'], row=-1,
                                 command='spray_target' if option['kind'].startswith('spray_') else 'fire_assisted',
                                 source_index=source_index if source_index is not None else -1,
                                 source_identity=((source_index, state.inventory[source_index])
                                                  if source_index is not None and 0 <= source_index < len(state.inventory)
                                                  else None),
                                 cursor=cursor, context=self._equipment_choice_context())
        self.aiming = True
        self.panel_mode = self._default_panel_mode()
        self.assist_path = []
        self._clear_held()
        self.refresh_view()

    def _apply(self, command: str, *args: int, **flags):
        sidebar_action = bool(getattr(self, '_sidebar_action_active', False))
        if getattr(self,'_inspection_active',lambda:False)() and not sidebar_action:
            from ...core.entities import ActionResult
            return ActionResult(False,'')
        if (getattr(self,'layer_observation',None) is not None or
                (getattr(self,'_image_output_error','') and self.config.get('map_display') != 'character')):
            from ...core.entities import ActionResult
            return ActionResult(False, '')
        if (hasattr(self,'_active_tamper_editor') and self._active_tamper_editor() is not None
                and command != 'commit_tamper'
                and not (sidebar_action and getattr(self, 'world_tamper_editor', None) is not None)):
            from ...core.entities import ActionResult
            return ActionResult(False, '')
        # 自我察觉面板是查看态：任何世界动作（移动/出手/等待…）前自动收起。
        if not sidebar_action and getattr(self, "_self_audit_visible", None) and self._self_audit_visible():
            self._close_self_audit(refresh=False)
        """``session.apply`` 的音频包装：动作生效时按设置播放对应音效。

        ``**flags`` 目前只有一个调试开关：``ignore_dissolution=True`` 配
        ``command="descend"`` 时绕过「崩解度 ≥100」门槛（调试面板「移动·下潜」），
        见 ``core.state.GameState.descend``。终局（run_over）仍按 ``session.apply``
        的原判定拒绝——调试也不越过终局。

        所有动作调用统一走这里（UI 层触发点，core 保持纯逻辑）。native
        输入线程的事件已经路由到主循环线程，音频调用天然单线程。音效
        开关与音量每次读设置页，改完即时生效；音频模块内部全降级保护，
        缺资源/无声卡时静默跳过。

        叠加层（第一批音效 2026-09-19）：
        - move 按落脚格覆写脚步声（液体/植物/冰面/普通），撞上实体则只播命中；
        - 打中目标（result.data["hit"]）追加 hit；
        - 心智/清醒下降 → 受创（轻/重按降幅分档）；
        - 事件 resolved 数增加 → event_done（完成音）；
        - 敌人数量减少 → 异象崩解；
        - pending_insight / pending_memory 置位 → 洞察 / 记忆正音；
        - 行动中败局（run_over 翻转且非 finish_run）→ defeat；
        - fire/fire_assisted 空放（未解锁且无聚合弹）→ 只有 fire_empty 干响。
        """
        if hasattr(self, '_qol_guard_action'):
            guarded = self._qol_guard_action(command, args, flags)
            if guarded is not None:
                return guarded
        if getattr(self, "_floor_transition", None) is not None:
            # 演出期间世界冻结：底栏按钮（不经 on_key 的绑定）也拦在这里。
            return ActionResult(changed=False)
        self._panel_enter_mode = None
        self._cancel_attack_confirmation(refresh=False)
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
        self.equipment_choice = None
        aim_option = self.aim_action_choice
        if aim_option is not None and command in ('fire', 'fire_assisted', 'spray_fire', 'spray_target'):
            flags.setdefault('choice', aim_option['key'])
        state = self.session.state
        mind0 = state.mind
        from ..projectile_styles import capture_projectile_visual
        projectile_visual = capture_projectile_visual(state,command,args,flags.get('choice'))
        from ..firing_presentation import supply_levels, note_supply_feedback
        supply_before=supply_levels(state) if command in ('fire','fire_assisted','reload_weapon_step') else None
        lucidity0 = state.lucidity
        insight0 = state.pending_insight
        memory0 = state.pending_memory
        memories0 = tuple(state.memory_fragments)
        blasts0 = len(getattr(state, 'explosion_blasts', ()) or ())
        combat0 = getattr(state, '_combat_fx_seq', 0)
        run_over0 = state.run_over
        enemies0 = len(state.enemies)
        projectile_seq0 = int(getattr(state, "projectile_seq", 0) or 0)
        hit_seq0 = int(getattr(state, "hit_event_seq", 0) or 0)
        messages0 = len(state.messages)
        resolved0 = sum(1 for entry in state.events if entry.resolved)
        player0 = (state.player.x, state.player.y)
        action0 = state.action_seq
        time0 = state.time
        volume = int(self.config.get("sfx_volume")) / 10
        if command == "descend" and flags.get("ignore_dissolution") and not state.run_over:
            result = state.descend(ignore_dissolution=True)
        else:
            result = self.session.apply(command, *args, **({'choice': flags['choice']} if 'choice' in flags else {}))
        if command == "move":
            self._update_movement_presentation(player0, result.changed)
        raw_projectile = getattr(state, "last_projectile", None) or {}
        projectile_fired = bool(
            state.projectile_seq != projectile_seq0
            and raw_projectile.get("seq") == state.projectile_seq
        )
        impact_audio_delay = 0.0
        if projectile_fired:
            impact_audio_delay = projectile_flight_time(
                str(raw_projectile.get("kind") or "shot"),
                len(raw_projectile.get("cells", ())))
            impact_audio_delay += projectile_repeat_delay(raw_projectile)

        def play_action_feedback(event: str, *, at_impact: bool = False) -> None:
            if projectile_fired and at_impact:
                self._play_sfx_after(impact_audio_delay, event, volume)
            else:
                sfx.play(event, volume=volume)

        if supply_before is not None:
            note_supply_feedback(self,supply_before,result.changed)
        if result.changed and command == "container_pour":
            # §15.6：倒出落地即撤掉「本格现有／倒入／预计」的临时标记。
            self._invalidate_terrain_preview()
        if command != 'reload_weapon_step' and (result.changed or command not in ('fire', 'fire_assisted', 'spray_fire', 'spray_target')):
            self.aim_action_choice = None
        if (result.changed and not state.run_over and bool(self.config.get("auto_pickup"))
                and command not in ("drop", "throw", "throw_target", "pickup", "collect_items", "take_from", "put_on_table")
                and (state.action_seq != action0 or state.time != time0 or "position" in result.data)):
            # Recheck after actual actions too: a hostile can pause collection
            # on entry, then die while the player is still standing on the loot.
            self.session.auto_pickup()
        options = result.data.get('equipment_action_choices')
        if not result.changed and options:
            self.equipment_choice = dict(command=command, args=args, options=options,
                                         cursor=0, context=self._equipment_choice_context())
            self.path.clear()
            self.observe_walk_path.clear()
            self._clear_held()
        if result.changed and result.data.get('equipment_sentence'):
            from ..sentence_writer import SentenceWriter
            self.query_one('#equipment-sentence', SentenceWriter).write(result.data['equipment_sentence'], force=True)
        aim_request = result.data.get("throw_aim")
        fire_request = result.data.get("fire_once_aim")
        deploy_request = result.data.get("deploy_aim")
        if aim_request is not None or fire_request is not None or deploy_request is not None:
            # 瞄准请求本身就是权威：不论外层命令叫 use、Enter 装卸转调还是快捷键，
            # 都进入同一发射界面；Esc 取消不消耗（物品仍在行囊）。
            self.spray_source = None
            self._aim_assist_pos = None
            self.throw_item_index = aim_request
            self.fire_once_index = fire_request
            self.aiming = True
            if deploy_request is not None:
                # 部署类物品（2026-10-22 A2）：另开一条落点通道，点位／成对／
                # 方向三种形态各自选点，取消零消耗。
                self.throw_item_index = None
                self.fire_once_index = None
                self.begin_item_deploy_aim(deploy_request)
            self._capture_aim_source()
            self.panel_mode = self._default_panel_mode()
            self.path.clear()
            self.observe_walk_path.clear()
        if result.data.get("mirror_insight") is not None:
            # 洞察之镜：开镜掷三种候选洞察（排除已持有），选一即消耗镜子。
            self.mirror_index = result.data["mirror_insight"]
            self.mirror_rolls = self.session.state.mirror_candidates(self.mirror_index)
            self.mirror_cursor = 0
            self.panel_mode = self._default_panel_mode()
            self.path.clear()
            self.observe_walk_path.clear()
        if command == "choose_event_option" and result.data.get("lens_offering") is not None:
            # §8 S23：青灯嵌镜成功 → 打开祭品多选浮层（三件易逝物／摄入物）。
            self.lens_offer_scene = str(result.data["lens_offering"])
            self.lens_offer_items = [list(row) for row in (result.data.get("eligible") or [])]
            self.lens_offer_selected = set()
            self.lens_offer_cursor = 0
            self.panel_mode = self._default_panel_mode()
            self.path.clear()
            self.observe_walk_path.clear()
        if self.config.get("sfx_enabled"):
            if command in ("fire", "fire_assisted") and not result.changed:
                # 空放：没解锁也没有聚合弹——只有扣扳机的干响，没有后续。
                if "聚合弹" in result.message or "发射许可" in result.message:
                    sfx.play("fire_empty", volume=volume)
            elif result.changed:
                event = ACTION_SOUNDS.get(command)
                if command == "move":
                    event = self._step_sound_for(state, player0, result)
                if event:
                    if projectile_fired and event in ("fire", "throw"):
                        # Paint the first flight frame before the launch sound.
                        self._play_sfx_after(0.0, event, volume)
                    else:
                        sfx.play(event, volume=volume)
                if result.data.get("dialogue"):
                    # 对话面板唤起：NPC 与事件用不同的确认音。
                    sfx.play("npc" if state.pending_npc() is not None else "interact", volume=volume)
                new_hits = [event for event in (getattr(state, "presentation_hits", ()) or ())
                            if int(event.get("seq", 0)) > hit_seq0]
                blocked_hit = any(event.get("blocked") for event in new_hits)
                real_hit = any(not event.get("blocked")
                               and int(event.get("amount", 0)) > 0 for event in new_hits)
                # 全被挡下时不播命中音，只留 parry：两者共用会让「没掉血」听成吃满。
                if result.data.get("hit") and (real_hit or not blocked_hit):
                    # 命中音对齐命中时刻：近战/轻击当场播；本次动作真的发射了
                    # 弹道时推迟到弹道视觉抵达落点（与 FX 的 born 同一时长），
                    # 不再出现「先响命中、后看飞行」。
                    if projectile_fired:
                        play_action_feedback("hit", at_impact=True)
                    else:
                        sfx.play("hit", volume=volume)
                if blocked_hit:
                    # 格挡/替身：独立反馈，不与真实创伤共用同一层声音。
                    play_action_feedback("parry", at_impact=True)
                if state.mind < mind0 or state.lucidity < lucidity0:
                    # 创伤分两路：心智创伤减 mind，清醒创伤减 lucidity——
                    # 只盯 mind 会漏掉清醒创伤（修复 2026-09-19）。
                    heavy = (mind0 - state.mind) + (lucidity0 - state.lucidity) >= 8
                    play_action_feedback("wound_heavy" if heavy else "wound_light",
                                         at_impact=True)
                if len(state.enemies) < enemies0:
                    play_action_feedback("enemy_die", at_impact=True)
                if sum(1 for entry in state.events if entry.resolved) > resolved0:
                    # 事件完成（resolved 数增加：回应交付/触发次数耗尽/剧情房间结算）。
                    play_action_feedback("event_done", at_impact=True)
                if state.pending_insight != insight0:
                    play_action_feedback("insight", at_impact=True)
                if state.pending_memory != memory0:
                    play_action_feedback("memory", at_impact=True)
                if state.run_over and not run_over0 and command != "finish_run":
                    sfx.play("defeat", volume=volume)
        # 2026-09-22：core 侧主动唤起的对话（击败 27 层核心执念 → 深潜裂隙
        # 结局选择）不走 interact 的返回值，这里统一兜底：pending_event_id
        # 已置位而面板还停在世界视图时，直接展开事件对话面板（interact
        # 路径随后重复置位同名面板，无副作用）。
        if state.pending_event_id is not None and (self.panel_mode == "world" or result.data.get('medicine_dialogue') or result.data.get('book_dialogue')):
            self.panel_mode = "event_dialog"
            self.panel_scroll = 0
            self.event_dialog_scroll = 0
            self.event_dialog_cursor = 0
        self._capture_projectile_action(changed=result.changed, memory_before=memories0,
                                        blasts_before=blasts0, combat_before=combat0,
                                        visual=projectile_visual)
        if projectile_fired:
            self._defer_projectile_messages(messages0, raw_projectile)
            # This queue contains the launch cue at the same FX time as the
            # first forced paint; impact cues remain on the flight timeline.
            self._flush_fx_audio_after_refresh(self._fx_clock)
        return result
    @staticmethod
    def _step_sound_for(state, player0: tuple[int, int], result) -> str | None:
        """move 的脚步声按落脚格材质分派；撞上实体（近战）不播脚步。

        优先级：命中 > 对话唤起 > 液体 > 植物 > 冰面 > 普通地面。
        """
        if result.data.get("hit") or result.data.get("dialogue"):
            return None  # 命中/对话音由叠加层负责
        player = state.player
        if (player.x, player.y) == player0:
            return ACTION_SOUNDS["move"]  # 没挪动（滑行原点等），按普通处理
        cell = state.cell(player.x, player.y)
        if cell.liquid >= 5:
            return "step_water"
        if cell.plant:
            return "step_plant"
        if cell.aggregate_variant == "冰面":
            return "step_ice"
        return ACTION_SOUNDS["move"]
    def _floor_transition_skip(self) -> bool:
        """动作入口（不走 on_key 的通道）的进层演出锁。

        演出进行中时把这次触发当作「跳过」消费：清状态、常规刷新接管、
        输入解锁（设计文档 §2.3 锁输入）。键盘通道上 on_key 已经先跳过并
        打了标记，本方法看到的是空状态，随后 _handled_in_on_key 空转；
        真正会落到这里的是 priority 绑定（q，先于 on_key 且命中后不再转发）
        与面板鼠标点击。
        """
        if getattr(self, "_floor_transition", None) is not None:
            self._finish_floor_transition(suppress_wipe=False)
            return True
        return False
    def assist_key(self) -> None:
        """o 键总入口：瞄准态=瞄准辅助（循环异像），否则开关目标辅助。"""
        if self.sentence_aim is not None:
            self._sentence_aim_key('o')
            return
        if self.aiming:
            self._cycle_aim_assist()
            self._refresh_cursor_only()
            return
        self.target_assist = not self.target_assist
        self._assist_cache = None  # 开关切换后必须重算，不能沿用旧签名
        if not self.target_assist:
            self.assist_path = []
        else:
            self._refresh_assist_path(self.observe_cursor if self.observe_mode else self.hover_cell)
        self._refresh_cursor_only()

    def _refresh_assist_path(self, cell: tuple[int, int] | None = None) -> None:
        """目标辅助的寻路路径刷新（鼠标悬停 / 观察光标共用）。

        同一格且世界未变（时间、玩家位置、异象数量一致）时直接复用上次结果：
        鼠标在同一格内会持续发移动事件，重复的 A* 是「辅助开启时寻路加载慢」
        的主要来源（2026-09-17 优化）。
        """
        cell = cell if cell is not None else self.hover_cell
        if cell is None:
            return
        state = self.session.state
        signature = (
            cell,
            state.time,
            state.player.x,
            state.player.y,
            len(state.enemies),
        )
        if signature == self._assist_cache:
            return
        self._assist_cache = signature
        self.assist_path = state.path_to(*cell)

    def _cycle_aim_assist(self) -> None:
        """瞄准辅助：在视野内可见且未被遮挡的异像间循环切换目标。

        选中后自动面向它，并显示玩家 → 目标的寻路路径；视野内没有
        合法目标时清空路径并提示。
        """
        state = self.session.state
        self._aim_free_cursor = None
        targets = [enemy for enemy in state.enemies if self._aim_target_eligible(enemy)]
        if not targets:
            self.assist_path = []
            self._aim_assist_pos = self._aim_assist_identity = None
            self.session.state.messages.append(tr("视野内没有可以辅助瞄准的失控意识。"))
            return
        targets.sort(key=lambda e: max(abs(e.x - state.player.x), abs(e.y - state.player.y)))
        current = next(
            (index for index, enemy in enumerate(targets)
             if (enemy.x, enemy.y) == self._aim_assist_pos),
            -1,
        )
        target = targets[(current + 1) % len(targets)]
        self._aim_assist_identity = target
        self._aim_assist_pos = (target.x, target.y)
        dx = (target.x > state.player.x) - (target.x < state.player.x)
        dy = (target.y > state.player.y) - (target.y < state.player.y)
        self.facing = (dx, dy) if (dx or dy) else self.facing
        self.assist_path = state.path_to(target.x, target.y)
        if not self.assist_path:
            self.assist_path = [(target.x, target.y)]
    def _clear_held(self) -> None:
        """清除按住状态（松开/切换界面/被阻挡时）。"""
        self._held_key = None
        self._held_direction = None
        self._hold_repeats = 0
        cadence = getattr(self, "_move_cadence", None)
        if cadence is not None:
            cadence.reset()

    def _auto_repeat_move(self) -> None:
        """帧定时器驱动的长按移动：每个截止点至多移动一格。

        终端不发按键释放事件，松开靠 HOLD_RELEASE_TIMEOUT 超时判定；
        只有收到过重复按键（_hold_repeats > 0）才继续移动，因此单次点按
        永远不会被帧定时器补步。截止点由 MoveCadence 维护：正常迟到顺延
        一个周期，落后超过一个周期则丢弃过期机会，不循环补步。
        """
        if self._inspection_active():
            return
        if self.observe_mode:
            # 观察模式：长按方向键走的是 ?（由 on_key 逐格处理），自己绝不挪步。
            self._clear_held()
            return
        if self._held_key is None or self._held_direction is None:
            return
        if self.aiming or self.path or self.pending_confirmation or self.session.state.run_over:
            self._clear_held()
            return
        now = time.monotonic()
        if now - self._last_hold_event > HOLD_RELEASE_TIMEOUT:
            self._clear_held()
            return
        if self._hold_repeats <= 0:
            return
        cadence = getattr(self, "_move_cadence", None)
        if cadence is None or not cadence.take_due(now):
            return
        self._hold_repeats = 0
        result = self._move_player(*self._held_direction)
        if not result.changed:
            # 撞墙/被阻挡：停止自动移动，避免每个节拍空转
            self._clear_held()
        self.refresh_view()

    def _toggle_panel(self, mode: str) -> None:
        if hasattr(self,'_active_tamper_editor') and self._active_tamper_editor() is not None:
            return
        self._panel_enter_mode = None
        if self.panel_mode == "event_dialog":
            # 对话中切面板：先收掉 core 的 pending id，避免对话状态悬空。
            self._close_event_dialog_state()
        self.panel_mode = self._default_panel_mode() if self.panel_mode == mode else mode
        self.panel_selection = 0
        self.panel_scroll = 0
        if not self.home_mode and not self.panel_locked:
            self.cursor_zone = "map" if self.panel_mode == "world" else "panel"
        self.refresh_view()
    def _cancel_unreachable_path(self) -> None:
        """Discard travel and its pending interactions without a notification."""
        self.path.clear()
        self.observe_walk_path.clear()
        self.assist_path = []
        self.pickup_goal = None
        self.path_click_goal = None
        self._slide_replans = 0

    def _follow_path(self) -> None:
        if self._inspection_active():
            return
        # Textual marks the app stopped before unmounting widgets; queued timer
        # callbacks must neither advance the saved world nor query those widgets.
        if not self.is_running or self._exit:
            return
        if self.observe_mode:
            # 观察模式下同一个节拍推进的是 ? 的寻路，不是玩家的脚步。
            self._follow_observe_path()
            return
        if not self.path or self.pending_confirmation or self.session.state.run_over:
            return
        target = self.path.pop(0)
        entity = self.session.state.entity_at(*target)
        if entity and entity is not self.session.state.player:
            self.path.clear()
            self.observe_walk_path.clear()
            self._confirm_or_attack(target)
            return
        before = (self.session.state.player.x, self.session.state.player.y)
        dx = max(-1, min(1, target[0] - before[0]))
        dy = max(-1, min(1, target[1] - before[1]))
        if not self._move_player(dx, dy).changed:
            self._cancel_unreachable_path()
            self.refresh_view()
            return
        elif max(
            abs(self.session.state.player.x - before[0]),
            abs(self.session.state.player.y - before[1]),
        ) > 1 and self.path:
            # 冰面滑行：这一步沿方向滑出了好几格，路径前缀已经被越过。
            # 若按旧路径继续，下一拍的方向会指回身后——玩家被「弹回」，
            # 每步还照常耗回合。
            from ...core.throwing import ice_stoppable

            state2 = self.session.state
            destination = self.path[-1]
            after = (state2.player.x, state2.player.y)
            if after == destination:
                self.path.clear()  # 正好滑到终点：到达结算在下方照常进行
            elif not ice_stoppable(state2, *destination):
                # 目标是冰面腹地：无论从哪个方向进入都会滑过头，永远停不住。
                # 放弃寻路，玩家停在滑行终点（这一回合已正常消耗）。
                self._cancel_unreachable_path()
                self.refresh_view()
                return
            else:
                self._slide_replans = getattr(self, "_slide_replans", 0) + 1
                if self._slide_replans > 4:
                    self._cancel_unreachable_path()
                    self.refresh_view()
                    return
                else:
                    self.path = state2.path_to(*destination)
        if not self.path:
            # 教程埋点：自动行走步判定「沿路径抵达目标格」。
            if self.session.state.tutorial.get("active"):
                self.session.state.tutorial_events["autowalk_arrived"] = (
                    self.session.state.player.x, self.session.state.player.y,
                )
            # 路径走完（或被挡住停下）：结算「点击可寻路」的目标。
            self._resolve_path_click_goal()
        # 走到目的地时，若那里有掉落物就顺手捡起——解决「点了物品还得再点一次」
        # 的问题：点击远处物品本来就是「走过去 + 捡起来」一个连贯动作。
        if not self.path and self.pickup_goal is not None:
            goal = self.pickup_goal
            self.pickup_goal = None
            if (self.session.state.player.x, self.session.state.player.y) == goal:
                self.try_pickup(goal)
        self.refresh_view()

    def _move_player(self, dx: int, dy: int):
        state = self.session.state
        target = state.entity_at(state.player.x + dx, state.player.y + dy)
        if target and target is not state.player and target.relation not in ("失控意识", "稳定意识"):
            self._request_attack_confirmation((target.x, target.y))
            return ActionResult(False, tr("攻击等待确认。"))
        return self._apply("move", dx, dy)

    def _update_movement_presentation(self, previous: tuple[int, int], changed: bool) -> None:
        """Start or snap the image-only trajectory after authoritative movement."""
        movement = getattr(self, "_movement_presentation", None)
        if movement is None:
            return
        state = self.session.state
        current = (state.player.x, state.player.y)
        now = time.monotonic()
        try:
            enabled = (bool(self.config.get("smooth_movement"))
                       and not bool(self.config.get("fx_reduce_motion")))
        except (AttributeError, KeyError, TypeError):
            enabled = False
        live = getattr(self, "_world_view_live", None)
        if live is None:  # 轻量假 App（单元测试）沿用旧的 world 判定
            live = lambda: getattr(self, "panel_mode", "world") == "world"
        if (not changed or current == previous or not enabled or state.run_over
                or not live()):
            old_active = movement.is_active(now)
            viewport = getattr(getattr(self, "_frame_map", None), "viewport", (0, 0, 1, 1))
            movement.reset((current[0] - viewport[0], current[1] - viewport[1]))
            self._movement_presentation_viewport = None
            if old_active:
                self._movement_presentation_needs_final_frame = True
            return

        map_view = getattr(self, "_frame_map", None)
        if map_view is None:
            try:
                map_view = self.query_one("#map", MapView)
            except Exception:
                return
        if map_view.display_mode != "image":
            movement.reset((current[0] - map_view.viewport[0],
                            current[1] - map_view.viewport[1]))
            self._movement_presentation_viewport = None
            return

        previous_viewport = map_view.viewport
        next_viewport = map_view.viewport_for(state)
        target = (current[0] - next_viewport[0], current[1] - next_viewport[1])
        if (next_viewport != previous_viewport
                or max(abs(current[0] - previous[0]), abs(current[1] - previous[1])) != 1):
            movement.reset(target)
            self._movement_presentation_viewport = None
            return

        if (movement.is_active(now)
                and self._movement_presentation_viewport == previous_viewport):
            source = movement.sample(now)
        else:
            source = (previous[0] - previous_viewport[0],
                      previous[1] - previous_viewport[1])
        movement.begin(source, target, now, MOVE_REPEAT_MIN_SECONDS)
        self._movement_presentation_viewport = next_viewport
        self._movement_presentation_needs_final_frame = True

    def _request_attack_confirmation(self, target: tuple[int, int]) -> None:
        entity = self.session.state.entity_at(*target)
        if entity is None:
            return
        self.pending_confirmation = ("attack", target)
        self._attack_confirmation_entity_id = entity.id
        self._attack_confirmation_started = time.monotonic()
        self._attack_confirmation_layer = (
            self.session.state.depth, self.session.state.realm_id, self.session.state.realm_depth)
        self.path.clear()
        self.observe_walk_path.clear()
        self.pickup_goal = None
        self.path_click_goal = None
        self._clear_held()
        self.panel_mode = "actions"
        self.refresh_view()

    def _cancel_attack_confirmation(self, *, refresh: bool = True) -> bool:
        if not self.pending_confirmation:
            return False
        self.pending_confirmation = None
        self._attack_confirmation_entity_id = None
        self._attack_confirmation_started = None
        self._attack_confirmation_layer = None
        if self.panel_mode == "actions":
            self.panel_mode = self._default_panel_mode()
        self._clear_held()
        if refresh:
            self.refresh_view()
        return True

    def _attack_confirmation_target(self):
        if not self.pending_confirmation:
            return None
        state = self.session.state
        entity = state.entity_at(*self.pending_confirmation[1])
        if (entity is None or entity is state.player or entity.integrity <= 0
                or entity.id != self._attack_confirmation_entity_id
                or max(abs(entity.x-state.player.x), abs(entity.y-state.player.y)) > 1
                or self._attack_confirmation_layer != (state.depth, state.realm_id, state.realm_depth)):
            return None
        return entity

    def _expire_attack_confirmation(self, *, refresh: bool = True) -> None:
        if not self.pending_confirmation:
            return
        started = self._attack_confirmation_started
        if (started is None or time.monotonic() - started >= ATTACK_CONFIRMATION_SECONDS
                or self._attack_confirmation_target() is None):
            self._cancel_attack_confirmation(refresh=refresh)

    def _confirm_or_attack(self, target: tuple[int, int]) -> None:
        entity = self.session.state.entity_at(*target)
        if entity and entity.relation == "稳定意识":
            # 稳定意识（NPC）：左键不再尝试攻击（也不再弹二次确认），
            # 直接唤起对话面板——与走近后按 Enter「行动」同一条路径的结果。
            state = self.session.state
            state.talk_toy_keeper(entity)
            state.pending_npc_id = entity.id
            state.messages.append(tr("{name}：「请讲。」", name=tr(entity.label)))
            self.panel_mode = "event_dialog"
            self.panel_scroll = 0
            self.event_dialog_scroll = 0
            self.event_dialog_cursor = 0
            self.refresh_view()
            return
        if entity and entity.relation != "失控意识":
            self._request_attack_confirmation(target)
            return
        dx = max(-1, min(1, target[0] - self.session.state.player.x))
        dy = max(-1, min(1, target[1] - self.session.state.player.y))
        self._move_player(dx, dy)
        self.refresh_view()

    def _execute_confirmed_attack(self, target: tuple[int, int]) -> None:
        # Confirm the original nearby entity, never a replacement at its old cell.
        entity = self._attack_confirmation_target()
        self._cancel_attack_confirmation(refresh=False)
        if not entity:
            self.refresh_view()
            return
        dx = max(-1, min(1, target[0] - self.session.state.player.x))
        dy = max(-1, min(1, target[1] - self.session.state.player.y))
        self._apply("move", dx, dy)
        self.refresh_view()

ATTACK_CONFIRMATION_SECONDS = 8.0

# 动作命令 → 语义音效事件（AudioBus.SOUND_MAP 同名键）；未列出的动作不发声。
# （第一批 29 个事件已全部接入，素材与触发条件见《音效挂点索引.md》。）
# [SFX挂点] 尚未挂音效的动作命令只剩 wait（等待，可不挂）；
# 新命令在 ACTION_SOUNDS 补一行映射即可接入。
ACTION_SOUNDS = {
    "move": "step",            # 移动（_apply 会按落脚格覆写为液体/植物/冰面脚步）
    "throw": "throw",
    "throw_target": "throw",  # 瞄准投掷（同一件离手声）
    "spray_fire": "fire",
    "spray_target": "fire",
    "fire": "fire",
    "fire_assisted": "fire",   # 辅助瞄准发射（同一把枪声）
    "drop": "throw",           # 放下显化物（复用落地声）
    "pickup": "pickup",
    "collect_items": "pickup",
    "take_from": "pickup",     # 台面取物
    "descend": "descend",
    "backtrack": "backtrack",  # 层间返回（上浮）
    "finish_run": "finish",
    "open": "open",            # 开门/推墙
    "uproot_plant": "uproot",  # 拔植物
    "equip": "equip",          # 穿上携带意象
    "unequip": "equip",        # 脱下（同一声金属扣）
    "toggle_equip": "equip",   # 穿/脱切换
    "use": "use_potion",       # 使用易逝物
    "choose_npc_option": "interact",  # NPC 对话选项确认
    "choose_event_option": "interact",  # 事件选项确认
    # ⚠️ interact 不在此表：打开对话的音效在 _apply_interact / _apply 叠加层里
    # 按「NPC 对话 vs 事件对话」区分（npc / interact 两种）。
}
