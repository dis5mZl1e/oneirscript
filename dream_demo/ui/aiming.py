"""Shared keyboard/mouse aiming transaction, with explicit target identity."""
from ..core.entities import ActionResult
from ..i18n import tr


class AimingMixin:
    # Class-level defaults keep direct DreamApp probes safe before the first
    # aim transaction has initialized its transient fields.
    _aim_free_cursor = None
    _aim_assist_pos = None
    _aim_assist_identity = None
    _aim_source_identity = None
    _aim_source_instance_id = None
    _aim_equipment_identity = None
    _last_firing_source_key = None
    _aim_failed = False
    construct_aim_id = None
    _construct_landing = None
    _rewire_source = None
    _aim_direction = (1, 0)
    # 部署类物品的落点草稿（2026-10-22 A2）：point／pair／direction 三种形态。
    item_aim_index = None
    _item_aim_form = None
    _item_aim_stage = 0
    _item_aim_first = None
    _item_aim_direction = (1, 0)

    def begin_construct_aim(self, ability_id):
        """§13/§12 H2：选中战斗或选点构想 → 打开零消耗瞄准草稿。

        进入、换目标、换方向、取消都不付费、不进冷却、不推进回合；真正的
        支付与弹道只在 confirm_aim 提交时发生。
        """
        from ..core.combat_constructs import aim_range, form_of, is_combat
        from ..core import ability_targeting
        from ..data.abilities import ABILITY_DEFINITIONS
        combat = is_combat(ability_id)
        if not combat and not ability_targeting.is_targeted(ability_id):
            return False
        state = self.session.state
        definition = ABILITY_DEFINITIONS.get(ability_id)
        if definition is None:
            return False
        self.throw_item_index = self.fire_once_index = self.spray_source = None
        self.sentence_aim = None
        self.aim_action_choice = None
        self.aiming = True
        self.construct_aim_id = ability_id
        self._construct_landing = None
        self._rewire_source = None
        self._capture_aim_source()
        self.panel_mode = 'world'
        self.path.clear()
        self.observe_walk_path.clear()
        dx, dy = self.facing if self.facing and any(self.facing) else (1, 0)
        self._aim_direction = (int(dx), int(dy))
        form = form_of(ability_id) if combat else ability_targeting.aim_form(ability_id)
        px, py = state.player.x, state.player.y
        if form == 'throw':
            from ..core.throwing import directional_landing
            self._aim_free_cursor = directional_landing(
                state, int(dx), int(dy), max_range=aim_range(state, ability_id),known_only=True)
        elif form in ('melee', 'area'):
            self._aim_free_cursor = (px + int(dx), py + int(dy))
        elif form == 'point':
            # 默认预览：面朝格；严格选点类若面朝格不合法就保持空光标，
            # 由玩家用方向键/鼠标明确选择，绝不自动最近。
            facing = (px + int(dx), py + int(dy))
            self._aim_free_cursor = (facing if ability_targeting.valid_target(
                state, ability_id, facing) else None)
        else:
            self._aim_free_cursor = None
        cost = state._scaled_ability_cost(int(definition['cost']))
        aim = (aim_range(state, ability_id) if combat
               else ability_targeting.aim_range(ability_id))
        self.show_toast(tr('构想瞄准：{name} · 射程 {range} · 费用 {cost} · Esc 取消不消耗。',
                           name=tr(definition['name']),
                           range=aim, cost=cost), 4)
        return True

    def _capture_aim_source(self, keep_cursor: bool = False):
        # 新一轮瞄准开始：清掉上一次的「失败待取消」标记（2026-10-18）。
        # 换源时 keep_cursor=True：锁定、自由落点和观察草稿都保留，只重算来源。
        self._aim_failed = False
        if not keep_cursor:
            self._aim_assist_pos = None
            self._aim_assist_identity = None
            self._aim_free_cursor = None
        state = self.session.state
        from ..core.origin_course import is_course
        self._aim_started_at = (state.action_seq,state.time) if is_course(state) else None
        self._aim_equipment_identity = (state.equipment.formation().semantic_signature
                                        if hasattr(state, 'equipment') else None)
        index = next((v for v in (self.throw_item_index, self.fire_once_index,
                                  self.spray_source) if v is not None and v >= 0), None)
        self._aim_source_identity = (index, state.inventory[index]) if index is not None and index < len(state.inventory) else None
        self._aim_source_instance_id = (
            str(getattr(state.inventory[index], 'instance_id', ''))
            if index is not None and index < len(state.inventory) else None)

    # ---- 统一来源事实：F 来源表、瞄准内切源与换弹共用同一份查询 ----

    def _firing_source_options(self) -> list[dict]:
        """Explicit sources in stable order, with reasons and target state.

        One query for the F picker, the in-aim source table and reload routing;
        the core fact object (``FiringSource``) stays the authority.
        """
        from ..core.firing_sources import collect_firing_sources
        state = self.session.state
        options: list[dict] = []
        for source in collect_firing_sources(state):
            entry = dict(
                definition_ids=list(source.definition_ids),
                source_key=source.key, can_fire=source.can_fire,
                reason=source.reason, target_pending=source.target_pending,
            )
            if source.kind == 'aggregate':
                entry.update(key='aggregate', kind='aggregate',
                             count=source.count, source_key='aggregate')
            elif source.kind == 'item':
                instance_id = source.instance_ids[0] if source.instance_ids else ''
                index = next((i for i, item in enumerate(state.inventory)
                              if str(getattr(item, 'instance_id', '')) == instance_id), -1)
                if index < 0:
                    continue
                entry.update(key=f'item:{index}', kind='item', index=index,
                             count=source.count)
            else:
                entry.update(key=source.choice_key, kind=source.action_kind)
            options.append(entry)
        return options

    def _current_source_key(self):
        choice = self.aim_action_choice
        if isinstance(choice, dict):
            if choice.get('key') == 'aggregate':
                return 'aggregate'
            if choice.get('key') == 'legacy_basic_fire':
                return 'legacy_basic_fire'
            return f"equipment:{choice.get('kind', 'fire')}:{choice.get('key')}"
        index = self.fire_once_index if self.fire_once_index is not None else self.spray_source
        state = self.session.state
        if index is not None and 0 <= index < len(state.inventory):
            return f"item:{getattr(state.inventory[index], 'instance_id', '')}"
        return getattr(self, '_last_firing_source_key', None)

    def _open_aim_source_table(self) -> bool:
        """F while aiming: the full source table, without losing the cursor."""
        options = self._firing_source_options()
        if len(options) <= 1:
            self.show_toast(tr('没有其他可选来源。'), 3)
            return False
        current = self._current_source_key()
        cursor = next((i for i, option in enumerate(options)
                       if option.get('source_key') == current), 0)
        self.equipment_choice = dict(
            command='aim_equipment', args=(), options=options,
            cursor=cursor, preserve_aim=True,
            context=self._equipment_choice_context())
        self.path.clear()
        self.observe_walk_path.clear()
        self._clear_held()
        self.refresh_view()
        return True

    def begin_throw_aim(self, index):
        """进入投掷瞄准（q 键与物品菜单同源）。

        「打开投掷选择」与「执行一次方向投掷」是两件事：这里只打开选择，
        出手由 Enter／落点确认完成，Esc 取消零消耗。光标预置在沿当前朝向的
        真实落点上，因此回车等于旧的方向投掷，方向键则能把距离改短或改向。
        """
        state = self.session.state
        if not (0 <= index < len(state.inventory)):
            self.show_toast(tr("意识行囊中没有这个承载位。"), 3)
            return False
        self.fire_once_index = None
        self.spray_source = None
        self.throw_item_index = index
        self.aiming = True
        self._capture_aim_source()
        from ..core.throwing import directional_landing
        dx, dy = self.facing or (1, 0)
        self._aim_free_cursor = directional_landing(state, int(dx), int(dy),known_only=True)
        self.panel_mode = "world"
        self.path.clear()
        self.observe_walk_path.clear()
        self.show_toast(tr("举起{item}——点选落点或按方向键投掷（Esc 取消，不消耗）。",
                           item=tr(state.inventory[index].name)), 4)
        return True

    def begin_item_deploy_aim(self, index):
        """部署类物品的落点草稿（2026-10-22 A2）。

        三种形态：point 选一点、pair 选两点（先源后出口）、direction 选方向。
        合法性只读 core/item_targeting.py——取消或非法提交零消耗，物品一直在行囊里。
        """
        from ..core import item_targeting
        state = self.session.state
        if not (0 <= index < len(state.inventory)):
            self.show_toast(tr("意识行囊中没有这个承载位。"), 3)
            return False
        definition_id = state.inventory[index].definition_id
        form = item_targeting.aim_form(definition_id)
        if form is None:
            self.show_toast(tr("{item}不需要选点。", item=tr(state.inventory[index].name)), 3)
            return False
        self.throw_item_index = None
        self.fire_once_index = None
        self.spray_source = None
        self.item_aim_index = index
        self._item_aim_form = form
        self._item_aim_stage = 0
        self._item_aim_first = None
        dx, dy = self.facing if self.facing and any(self.facing) else (1, 0)
        self._item_aim_direction = (int(dx), int(dy))
        self._aim_free_cursor = None
        if form in ('point', 'pair'):
            facing = (state.player.x + int(dx), state.player.y + int(dy))
            valid = (item_targeting.valid_target(state, definition_id, facing)
                     if form == 'point'
                     else item_targeting.valid_pair_anchor(state, definition_id, facing))
            self._aim_free_cursor = facing if valid else None
        self.aiming = True
        self.panel_mode = "world"
        self.path.clear()
        self.observe_walk_path.clear()
        hint = {'point': tr("点选落点 · Enter 确认 · Esc 取消"),
                'pair': tr("先选第一个落点 · 再选第二个 · Esc 取消"),
                'direction': tr("方向键选方向 · Enter 确认 · Esc 取消")}.get(form, "")
        self.show_toast(tr("举起{item}——{hint}（取消不消耗）。",
                           item=tr(state.inventory[index].name), hint=hint), 4)
        return True

    def cancel_aim(self):
        state=self.session.state
        # A successful commit also closes aim. Count only a real cancellation
        # in the same world action, even if it happened between two UI frames.
        if (self.aiming and getattr(self,'_aim_started_at',None) is not None
                and self._aim_started_at==(state.action_seq,state.time)):
            from ..core.origin_course import is_course, note, pump
            if is_course(state):
                note(state,'aim_cancelled',*(['throw_cancelled'] if self.throw_item_index is not None else []))
                pump(state)
        self._aim_started_at=None
        self.aiming = False
        self._aim_failed = False
        self.construct_aim_id = None
        self._construct_landing = None
        self._rewire_source = None
        self.throw_item_index = self.fire_once_index = self.spray_source = None
        self.item_aim_index = None
        self._item_aim_form = None
        self._item_aim_stage = 0
        self._item_aim_first = None
        self.aim_action_choice = None
        self._aim_assist_pos = self._aim_assist_identity = self._aim_free_cursor = None
        self._aim_source_identity = None
        self.assist_path = []
        self.panel_mode = 'world'
        self._clear_held()

    def _aim_range(self):
        if getattr(self, 'construct_aim_id', None):
            from ..core.combat_constructs import aim_range, is_combat
            if is_combat(self.construct_aim_id):
                return aim_range(self.session.state, self.construct_aim_id)
            from ..core import ability_targeting
            return ability_targeting.aim_range(self.construct_aim_id)
        if getattr(self, 'item_aim_index', None) is not None:
            from ..core import item_targeting
            state = self.session.state
            index = self.item_aim_index
            if 0 <= index < len(state.inventory):
                return item_targeting.aim_range(state.inventory[index].definition_id)
            return 0
        if self.throw_item_index is not None:
            from ..core.throwing import throw_range
            return throw_range(self.session.state)
        if self.fire_once_index is not None:
            return 12
        if self._aim_spray_medium() is not None:
            from ..core.weapons import SPRAY_RANGE
            return SPRAY_RANGE
        state = self.session.state
        choice = self.aim_action_choice
        plan = state.equipment.plan_action('fire', choice=choice['key'] if choice else None)
        return min(12, int(dict(plan.projectile_profile).get('range', 12)))

    def _aim_context_details(self):
        """Read the live selected action without spending or changing aim state."""
        from ..core.weapons import SPRAY_COST, SPRAY_RANGE, spray_plan
        state = self.session.state
        pending = getattr(self, 'sentence_aim', None)
        target = (pending['cursor'] if pending is not None else
                  getattr(self, '_aim_free_cursor', None) or getattr(self, '_aim_assist_pos', None))
        details = dict(action='发射', range=12, imagination_cost=0,
                       consumes_source=False, target=target, cost='')
        if getattr(self, 'item_aim_index', None) is not None:
            from ..core import item_targeting
            index = self.item_aim_index
            if 0 <= index < len(state.inventory):
                item = state.inventory[index]
                details.update(action=tr('部署 {name}', name=tr(item.name)),
                               range=item_targeting.aim_range(item.definition_id),
                               cost=tr('消耗物品 1 件'))
            return details
        if getattr(self, 'construct_aim_id', None):
            from ..core.combat_constructs import aim_range, is_combat
            from ..core import ability_targeting
            from ..data.abilities import ABILITY_DEFINITIONS
            ability_id = self.construct_aim_id
            definition = ABILITY_DEFINITIONS[ability_id]
            cost = state._scaled_ability_cost(int(definition['cost']))
            combat = is_combat(ability_id)
            details.update(action=definition['name'],
                           range=(aim_range(state, ability_id) if combat
                                  else ability_targeting.aim_range(ability_id)),
                           imagination_cost=cost)
            if ability_id == 'combat.cross_step':
                details['landing'] = self._construct_landing
            if not combat:
                if ability_id == 'rewire':
                    details['rewire_source'] = self._rewire_source
                if ability_id == 'blink' and target is not None:
                    cell = state.cell(*target)
                    details['danger'] = bool(
                        getattr(cell, 'flame', 0) or cell.liquid > 0
                        or cell.gas >= 20 or state._cell_is_flammable(cell))
                    details['path_length'] = max(
                        abs(target[0] - state.player.x),
                        abs(target[1] - state.player.y))
        elif pending is not None and pending.get('command', 'use_equipment_sentence') == 'use_equipment_sentence':
            option = next((option for option in state.equipment.active_sentence_options()
                           if option.key == pending['key']), None)
            if option is None:
                details.update(action='已失效语句', range=0)
            else:
                details.update(action={'imprint':'刻痕', 'repair':'修缮', 'measure':'测量'}.get(option.opcode, '语句'),
                               range=option.range, imagination_cost=option.cost,
                               consumes_source=option.consumes_source)
                if option.consumes_source:
                    details['cost'] = tr('消耗工具 1 件')
        elif self.throw_item_index is not None:
            details.update(action='投掷', range=self._aim_range(), cost=tr('投出物品 1 件'))
        elif self.fire_once_index is not None:
            details.update(action='一次性发射', cost=tr('消耗物品 1 件'), consumes_source=True)
        else:
            selected = self.aim_action_choice
            key = pending['key'] if pending is not None else selected['key'] if selected else None
            spray = (pending.get('command') == 'spray_target' if pending is not None
                     else self._aim_spray_medium() is not None)
            context = dict(target=state.entity_at(*target), cell=target) if target is not None else {}
            if spray:
                index = pending.get('source_index', -1) if pending is not None else self.spray_source
                index = index if index is not None and index >= 0 else None
                plan = spray_plan(state, index, choice=key, **context)
                if not plan.valid:
                    plan = spray_plan(state, index, choice=key)
                profile = dict(plan.projectile_profile)
                details.update(action='喷射', range=SPRAY_RANGE,
                               imagination_cost=int(profile.get('cost', SPRAY_COST)))
            else:
                plan = state.equipment.plan_action('fire', choice=key, **context)
                if not plan.valid:
                    plan = state.equipment.plan_action('fire', choice=key)
                details['range'] = min(12, int(dict(plan.projectile_profile).get('range', 12)))
                if plan.innate:
                    details['cost'] = (tr('消耗基础发射 1 发')
                                       if key == 'legacy_basic_fire'
                                       else tr('消耗聚合弹 1 发'))
        if details['imagination_cost']:
            details['cost'] = tr('想象力 {cost}', cost=details['imagination_cost'])
        return details

    def _throw_landing_cell(self):
        """投掷瞄准的预测落点：自由光标 > 锁定目标 > 方向投掷（真实撞墙规则）。"""
        state = self.session.state
        target = (getattr(self, '_aim_free_cursor', None)
                  or getattr(self, '_aim_assist_pos', None))
        if target is not None:
            return (int(target[0]), int(target[1]))
        from ..core.throwing import directional_landing
        facing = getattr(self, 'facing', None) or (1, 0)
        if getattr(self, 'construct_aim_id', None):
            from ..core.combat_constructs import aim_range
            return directional_landing(state, int(facing[0]), int(facing[1]),
                                       max_range=aim_range(state, self.construct_aim_id),known_only=True)
        return directional_landing(state, int(facing[0]), int(facing[1]),known_only=True)

    def _throw_landing_hint(self):
        """投掷瞄准提示：预测落点 + 落地效果类别 + 落地声响半径（静音写明）。"""
        state = self.session.state
        index = getattr(self, 'throw_item_index', None)
        if index is None or not (0 <= index < len(state.inventory)):
            return ''
        from ..core import sound_preview
        item = state.inventory[index]
        landing = self._throw_landing_cell()
        preview = sound_preview.throw_landing_preview(state, item, landing)
        effect = tr(sound_preview.throw_landing_effect(item))
        text = tr('落地({x},{y})：{effect}', x=landing[0], y=landing[1], effect=effect)
        text += self._throw_path_hint(landing)
        if preview['silent']:
            return text + ' · ' + tr('落地不发声')
        text += ' · ' + tr('落地声响半径 {n}', n=preview['radius'])
        if preview['sources']:
            text += '（' + tr('、').join(preview['sources']) + '）'
        return text

    def _throw_path_hint(self, landing):
        from ..core.throwing import trace_throw
        if trace_throw(self.session.state,*landing,known_only=True).uncertain:
            return ' · ' + tr('路径未完全可见，实际落点可能提前')
        return ''

    def _equipment_pulse_aim_hint(self, target):
        """带 ``fire.pulse`` 载荷的发射：命中该目标时目标格的实际声响半径。"""
        if (getattr(self, 'throw_item_index', None) is not None
                or getattr(self, 'fire_once_index', None) is not None
                or getattr(self, '_aim_spray_medium', lambda: None)() is not None):
            return ''
        state = self.session.state
        try:
            entity = state.entity_at(*target)
        except Exception:
            return ''
        if entity is None or entity is state.player:
            return ''
        try:
            pending = getattr(self, 'sentence_aim', None)
            selected = getattr(self, 'aim_action_choice', None)
            key = (pending['key'] if pending is not None
                   else selected['key'] if selected else None)
            plan = state.equipment.plan_action('fire', choice=key,
                                               target=entity, cell=tuple(target))
            if not plan.valid:
                return ''
            pulse = int(dict(plan.projectile_profile).get('pulse') or 0)
            if pulse <= 0:
                return ''
            from ..core.sound_preview import equipment_pulse_preview
            preview = equipment_pulse_preview(state, target, {'pulse': pulse})
            return tr('命中处声响半径 {n}', n=preview['radius'])
        except Exception:
            return ''

    def _construct_risk_hint(self, target):
        """§12 F：自伤/点燃/连锁的可计算风险，落到瞄准提示。"""
        ability_id = getattr(self, 'construct_aim_id', None)
        if not ability_id:
            return ''
        state = self.session.state
        if ability_id == 'static_arc':
            cell = state.cell(state.player.x, state.player.y)
            if cell.liquid > 0:
                return tr('你脚下的导电液体会让电弧反噬自己。')
        if ability_id == 'detonate' and target is not None:
            count = 0
            for y in range(target[1] - 1, target[1] + 2):
                for x in range(target[0] - 1, target[0] + 2):
                    if state.inside_board(x, y) and state._cell_is_flammable(state.cell(x, y)):
                        count += 1
            if count:
                return tr('落点周围有 {n} 格可燃材料，可能连锁引燃。', n=count)
        return ''

    def _aim_context_hint(self):
        details = self._aim_context_details()
        target = details['target']
        state = self.session.state
        entity = state.entity_at(*target) if target is not None else None
        name = tr(entity.label) if entity is not None and entity is not state.player else tr('自由落点' if target else '未锁定')
        text = tr('瞄准：{action} · 射程 {distance} · {name}',
                  action=tr(details['action']), distance=details['range'], name=name)
        if target is not None:
            text += f' {target}'
        if details['cost']:
            text += ' · ' + details['cost']
        if details.get('landing'):
            text += ' · ' + tr('借位落点 ({x}, {y})', x=details['landing'][0],
                               y=details['landing'][1])
        if details.get('rewire_source'):
            text += ' · ' + tr('触发源 ({x}, {y})：再选择接收端',
                               x=details['rewire_source'][0],
                               y=details['rewire_source'][1])
        if 'danger' in details:
            text += ' · ' + tr('落点危险：{state}', state=tr('是' if details['danger'] else '否'))
            text += ' · ' + tr('路径 {n} 格', n=details['path_length'])
        if getattr(self, 'construct_aim_id', None):
            risk = self._construct_risk_hint(target)
            if risk:
                text += ' · ' + risk
        if getattr(self, 'throw_item_index', None) is not None:
            landing_hint = self._throw_landing_hint()
            if landing_hint:
                text += ' · ' + landing_hint
        elif target is not None:
            pulse_hint = self._equipment_pulse_aim_hint(target)
            if pulse_hint:
                text += ' · ' + pulse_hint
        if getattr(self, 'item_aim_index', None) is not None:
            form = getattr(self, '_item_aim_form', None)
            stage = getattr(self, '_item_aim_stage', 0)
            if form == 'direction':
                controls = '方向键转向 · Enter 确认 · Esc 取消（不消耗）'
            elif form == 'pair' and stage == 0:
                controls = '方向键移落点 · Enter 选定第一个 · Esc 取消（不消耗）'
            elif form == 'pair':
                controls = '方向键移落点 · Enter 确认这一对 · Esc 取消（不消耗）'
            else:
                controls = '方向键移落点 · Enter 确认 · Esc 取消（不消耗）'
        elif getattr(self, 'construct_aim_id', None):
            from ..core.combat_constructs import form_of, is_combat
            from ..core import ability_targeting as _targeting
            if is_combat(self.construct_aim_id):
                form = form_of(self.construct_aim_id)
            else:
                form = _targeting.aim_form(self.construct_aim_id)
            if self.construct_aim_id == 'combat.cross_step':
                controls = '方向键选目标 · Tab 换借位落点 · Enter 确认 · Esc 取消'
            elif self.construct_aim_id == 'rewire' and self._rewire_source is None:
                controls = '方向键选触发源 · Enter 选定 · Esc 取消（不消耗）'
            elif self.construct_aim_id == 'rewire':
                controls = '方向键选接收端 · Enter 提交 · Esc 取消（不消耗）'
            elif form in ('melee', 'area'):
                controls = '方向键选格 · Enter 确认 · Esc 取消（不消耗）'
            elif form == 'throw':
                text += self._throw_path_hint(self._throw_landing_cell())
                controls = '方向键移落点 · Enter 确认 · Esc 取消（不消耗）'
            elif form == 'direction':
                controls = '方向键转向 · Enter 确认 · Esc 取消（不消耗）'
            elif form == 'point':
                controls = '方向键移落点 · Enter 确认 · Esc 取消（不消耗）'
            else:
                controls = '方向键发射 · Tab 自由落点 · Enter 确认 · Esc 取消'
        elif getattr(self, 'sentence_aim', None) is not None:
            controls = '方向键落点 · O 换目标 · Enter 确认 · Esc 取消'
        elif getattr(self, '_aim_free_cursor', None) is not None:
            controls = '方向键落点 · Tab 返回方向 · Enter 确认 · Esc 取消'
        else:
            controls = 'O 换敌 · Tab 自由落点 · 方向键/Enter 确认 · Esc 取消'
        text += ' · ' + tr(controls)
        return text

    def _aim_target_eligible(self, enemy):
        state = self.session.state
        if (enemy.integrity <= 0 or enemy.relation not in ('失控意识', '玩偶意识体')
                or not state.is_visible(enemy.x, enemy.y)
                or max(abs(enemy.x-state.player.x), abs(enemy.y-state.player.y)) > self._aim_range()):
            return False
        if getattr(self, 'construct_aim_id', None):
            from ..core.combat_constructs import form_of, is_combat
            from ..core import ability_targeting
            if not is_combat(self.construct_aim_id):
                return ability_targeting.valid_target(
                    state, self.construct_aim_id, (enemy.x, enemy.y))
            if form_of(self.construct_aim_id) == 'melee':
                return max(abs(enemy.x-state.player.x),
                           abs(enemy.y-state.player.y)) == 1
            return True
        if self.throw_item_index is not None:
            from ..core.throwing import is_valid_target
            return is_valid_target(state, enemy.x, enemy.y)[0]
        return state._has_line_of_sight(state.player.x, state.player.y, enemy.x, enemy.y)

    def _cancel_failed_aim(self) -> bool:
        """上一次发射/投掷被拒后，把这次输入当作「取消瞄准」。

        玩家规则（2026-10-18）：射/掷失败后左键和任意键盘键都要能退出，不能
        只剩 Esc；还没有失败过（只是刚进入瞄准）时绝不走这条，方向键/鼠标
        照常调整落点与方向。
        """
        if not getattr(self, "_aim_failed", False):
            return False
        self.cancel_aim()
        self.refresh_view()
        return True

    def _confirm_targeted_ability(self, ability_id, target=None, direction=None):
        """§12 H2 选点构想的提交：不合法目标不付费、不退出草稿。"""
        from ..core import ability_targeting
        state = self.session.state
        spec = ability_targeting.spec_for(ability_id)
        if spec is None:
            return ActionResult(False, tr('这个构想没有可用的瞄准规则。'))
        aim_dir = direction or getattr(self, '_aim_direction', None) or self.facing
        if spec.form == 'direction':
            result = state.activate_ability(ability_id, direction=aim_dir)
            self._finish_targeted_aim(result)
            return result
        point = target
        if point is None:
            point = (getattr(self, '_aim_free_cursor', None)
                     or getattr(self, '_aim_assist_pos', None))
        if point is None:
            message = tr('请先选择一个合法落点（Esc 取消，不消耗）。')
            self.show_toast(message, 4)
            self.refresh_view()
            return ActionResult(False, message)
        point = (int(point[0]), int(point[1]))
        if ability_id == 'rewire':
            from ..materials.logic import TRIGGER_KINDS, RECEIVER_KINDS
            kind = state.cell(*point).wall_kind
            if self._rewire_source is None:
                if (kind not in TRIGGER_KINDS or not state.is_visible(*point)
                        or max(abs(point[0] - state.player.x),
                               abs(point[1] - state.player.y)) > spec.range):
                    message = tr('这里不是合法的触发源（Esc 取消，不消耗）。')
                    self.show_toast(message, 4)
                    self.refresh_view()
                    return ActionResult(False, message)
                self._rewire_source = point
                self.show_toast(tr('触发源 ({x}, {y}) 已选：再选择接收端。',
                                   x=point[0], y=point[1]), 4)
                self.refresh_view()
                return ActionResult(False, '')
            if (kind not in RECEIVER_KINDS or not state.is_visible(*point)
                    or max(abs(point[0] - state.player.x),
                           abs(point[1] - state.player.y)) > spec.range):
                message = tr('这里不是合法的接收端（Esc 取消，不消耗）。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            result = state.activate_ability(
                ability_id, target=(*self._rewire_source, *point))
        else:
            if not ability_targeting.valid_target(state, ability_id, point):
                message = tr('这个落点不成立——本次不消耗。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            result = state.activate_ability(ability_id, target=point)
        self._finish_targeted_aim(result)
        return result

    def _finish_targeted_aim(self, result):
        if result.changed:
            self.cancel_aim()
        self.show_toast(result.message, 4)
        self.refresh_view()

    def _confirm_construct_aim(self, target=None, direction=None):
        """§13：把瞄准草稿提交成一次真实构想动作。

        草稿期间不付费；这里才调用 ``activate_ability``，由核心统一复核
        学习、冷却、费用、身份与目标几何。拒绝时保留草稿并允许退出。
        """
        from ..core.combat_constructs import form_of, is_combat, meta
        from ..core import ability_targeting
        state = self.session.state
        ability_id = self.construct_aim_id
        if not ability_id:
            return ActionResult(False, '')
        if not is_combat(ability_id):
            return self._confirm_targeted_ability(ability_id, target, direction)
        form = form_of(ability_id)
        point = target
        if point is None:
            point = (getattr(self, '_aim_free_cursor', None)
                     or getattr(self, '_aim_assist_pos', None))
        if point is not None:
            point = (int(point[0]), int(point[1]))
        aim_dir = direction
        if aim_dir is None and point is not None:
            dx, dy = point[0] - state.player.x, point[1] - state.player.y
            if dx or dy:
                aim_dir = ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
        if aim_dir is None:
            aim_dir = self.facing if self.facing and any(self.facing) else (1, 0)
        aim_dir = (int(aim_dir[0]), int(aim_dir[1]))
        targeting = str(meta(ability_id).get('targeting') or 'single')
        if form == 'melee' and targeting == 'single':
            if point is None:
                point = (state.player.x + aim_dir[0], state.player.y + aim_dir[1])
            if max(abs(point[0] - state.player.x),
                   abs(point[1] - state.player.y)) != 1:
                message = tr('近战构想只能选择相邻的目标。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            entity = state.entity_at(*point)
            if (entity is None or entity is state.player
                    or entity.relation not in ('失控意识', '玩偶意识体')):
                message = tr('先选择一个相邻的异象。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
        if form in ('melee', 'area'):
            # 近战与自身范围只提交方向；目标是玩家选中的格/方向，不再走远端锁定。
            call_target = None
        else:
            call_target = point
        kwargs = {}
        if (ability_id == 'combat.cross_step'
                and self._construct_landing is not None):
            kwargs['landing'] = self._construct_landing
        result = state.activate_ability(ability_id, target=call_target,
                                        direction=aim_dir, **kwargs)
        if result.changed:
            self.cancel_aim()
        else:
            self._aim_failed = True
        self.show_toast(result.message, 4)
        self.refresh_view()
        return result

    def _confirm_item_deploy_aim(self, target=None, direction=None):
        """部署类物品的落点提交（2026-10-22 A2）。

        point 一次确认；pair 两次确认（先源/先第一端，再第二点）；direction
        先定方向再确认。任何不成立的落点都只提示，不消耗物品、不花行动。
        """
        from ..core import item_targeting
        state = self.session.state
        index = getattr(self, 'item_aim_index', None)
        if index is None or not (0 <= index < len(state.inventory)):
            message = tr('意识行囊中没有这个承载位。')
            self.show_toast(message, 3)
            self.cancel_aim()
            self.refresh_view()
            return ActionResult(False, message)
        definition_id = state.inventory[index].definition_id
        form = getattr(self, '_item_aim_form', None) or item_targeting.aim_form(definition_id)
        point = target if target is not None else getattr(self, '_aim_free_cursor', None)
        if form == 'direction':
            aim_dir = (direction or getattr(self, '_item_aim_direction', None)
                       or self.facing or (1, 0))
            result = self._apply('deploy_direction', index, int(aim_dir[0]), int(aim_dir[1]))
        elif form == 'pair':
            if point is None:
                message = tr('请先选择一个合法落点（Esc 取消，不消耗）。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            point = (int(point[0]), int(point[1]))
            if getattr(self, '_item_aim_stage', 0) == 0:
                if not item_targeting.valid_pair_anchor(state, definition_id, point):
                    message = tr('这里不能作为第一个落点——本次不消耗。')
                    self.show_toast(message, 4)
                    self.refresh_view()
                    return ActionResult(False, message)
                self._item_aim_stage = 1
                self._item_aim_first = point
                self._aim_free_cursor = point
                message = tr('第一个落点 ({x}, {y}) 已选：再选第二个。',
                             x=point[0], y=point[1])
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            first = getattr(self, '_item_aim_first', None)
            if first is None or not item_targeting.valid_pair(state, definition_id,
                                                            first, point):
                message = tr('这两个落点凑不成一对——本次不消耗。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            result = self._apply('deploy_pair', index, first[0], first[1],
                                 point[0], point[1])
        else:
            if point is None:
                message = tr('请先选择一个合法落点（Esc 取消，不消耗）。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            point = (int(point[0]), int(point[1]))
            if not item_targeting.valid_target(state, definition_id, point):
                message = tr('这个落点不成立——本次不消耗。')
                self.show_toast(message, 4)
                self.refresh_view()
                return ActionResult(False, message)
            result = self._apply('deploy_target', index, point[0], point[1])
        if result.changed:
            self.cancel_aim()
        else:
            self._aim_failed = True
        self.show_toast(result.message, 4)
        self.refresh_view()
        return result

    def _item_aim_direction_key(self, dx, dy):
        """部署类物品的方向键：direction 形态转向，其余形态在射程内移光标。"""
        from ..core import item_targeting
        state = self.session.state
        index = getattr(self, 'item_aim_index', None)
        if index is None or not (0 <= index < len(state.inventory)):
            return
        definition_id = state.inventory[index].definition_id
        form = getattr(self, '_item_aim_form', None) or item_targeting.aim_form(definition_id)
        if form == 'direction':
            self._item_aim_direction = ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
            self.facing = self._item_aim_direction
            return
        reach = item_targeting.aim_range(definition_id)
        cursor = getattr(self, '_aim_free_cursor', None)
        base = cursor or (state.player.x, state.player.y)
        nx = min(state.player.x + reach, max(state.player.x - reach, base[0] + dx))
        ny = min(state.player.y + reach, max(state.player.y - reach, base[1] + dy))
        if (nx, ny) == (state.player.x, state.player.y):
            return
        self._aim_free_cursor = (nx, ny)

    def confirm_aim(self, target=None, direction=None):
        """Execute the current typed action. Rejections retain all source selection."""
        # 失败之后的下一次确认 = 取消（不再把同一发失败动作无限重试）。
        if self._cancel_failed_aim():
            return ActionResult(False, "")
        if getattr(self, 'item_aim_index', None) is not None:
            return self._confirm_item_deploy_aim(target, direction)
        state = self.session.state
        if getattr(self, 'construct_aim_id', None):
            return self._confirm_construct_aim(target, direction)
        source = getattr(self, '_aim_source_identity', None)
        lock = getattr(self, '_aim_assist_identity', None)
        reason = None
        equipment = getattr(self, '_aim_equipment_identity', None)
        if equipment is not None and equipment != state.equipment.formation().semantic_signature:
            reason = '瞄准的携带意象已经改变，请取消后重新选择。'
        instance_id = getattr(self, '_aim_source_instance_id', None)
        if instance_id:
            # Inventory may have been compacted mid-aim: resolve by instance id,
            # never trust the index captured when the aim began.
            index = next((i for i, item in enumerate(state.inventory)
                          if str(getattr(item, 'instance_id', '')) == instance_id), -1)
            if index < 0 or (source is not None and state.inventory[index] is not source[1]):
                reason = '瞄准的物品已经改变，请取消后重新选择。'
            elif self.fire_once_index is not None:
                self.fire_once_index = index
            elif self.throw_item_index is not None:
                self.throw_item_index = index
            elif self.spray_source is not None:
                self.spray_source = index
        elif source is not None and (source[0] >= len(state.inventory) or state.inventory[source[0]] is not source[1]):
            reason = '瞄准的物品已经改变，请取消后重新选择。'
        if target is None:
            target = getattr(self, '_aim_free_cursor', None) or self._aim_assist_pos
            if lock is not None and (not any(e is lock for e in state.enemies)
                    or (lock.x, lock.y) != self._aim_assist_pos or not self._aim_target_eligible(lock)):
                reason = '锁定目标已经失效，请重新选择。'
                self._aim_assist_pos = self._aim_assist_identity = None
                self.assist_path = []
        choice_before = self.aim_action_choice if isinstance(self.aim_action_choice, dict) else None
        if reason:
            result = ActionResult(False, tr(reason))
        else:
            if target is None and direction is None:
                direction = self.facing
            if target is not None:
                args = tuple(target)
                command = 'fire_assisted'
                dx, dy = target[0] - state.player.x, target[1] - state.player.y
                if dx or dy:
                    self.facing = ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
            else:
                args = tuple(direction)
                command = 'fire'
                self.facing = direction
            if self.fire_once_index is not None:
                command = 'fire_once_target' if target is not None else 'fire_once'
                args = (self.fire_once_index, *args)
            elif self.throw_item_index is not None:
                command = 'throw_target' if target is not None else 'throw'
                args = (self.throw_item_index, *args)
            elif self._aim_spray_medium() is not None:
                command = 'spray_target' if target is not None else 'spray_fire'
                args = (self.spray_source if self.spray_source is not None else -1, *args)
            result = self._apply(command, *args)
        keep_aim = (result.changed and command in ('fire', 'fire_assisted')
                    and choice_before is not None
                    and choice_before.get('kind') == 'fire'
                    and getattr(self, 'equipment_choice', None) is None)
        if keep_aim:
            # 普通武器成功开火后留在瞄准：下一发仍只由一次确认触发。
            self._stay_in_equipment_aim(choice_before)
        elif result.changed:
            self.cancel_aim()
        elif (choice_before is not None and choice_before.get('kind')=='fire'
                and result.message in (tr('弹匣已空，请先换弹。'),tr('弹匣不足，请先换弹。'),
                                       tr('旧档继承的基础发射已经用完，请先换弹。'),tr('聚合弹库存不足。'))):
            # An empty explicit magazine is a reload state, not a failed target.
            self._stay_in_equipment_aim(choice_before)
        elif getattr(self, "equipment_choice", None) is None:
            # 失败且没有弹出「换一个动作」选择时，记下失败态：下一次左键/任意
            # 键取消，避免条件缺失（无弹药/无成立动作句…）时卡在瞄准里。
            self._aim_failed = True
        self.show_toast(result.message, 4)
        self.refresh_view()
        return result

    def _stay_in_equipment_aim(self, choice):
        """Keep the aim transaction alive after a real shot from an ordinary weapon."""
        state = self.session.state
        self.aiming = True
        self.aim_action_choice = choice
        self._aim_failed = False
        self.panel_mode = 'actions'
        self._aim_equipment_identity = state.equipment.formation().semantic_signature
        self._last_firing_source_key = self._current_source_key()
        self._revalidate_aim_lock()

    def _move_construct_cursor(self, dx, dy):
        """近战／自身范围的选择限制在八邻格；不能把光标移到玩家脚下。"""
        state = self.session.state
        facing = self.facing if self.facing and any(self.facing) else (1, 0)
        cursor = (getattr(self, '_aim_free_cursor', None)
                  or getattr(self, '_aim_assist_pos', None)
                  or (state.player.x + int(facing[0]), state.player.y + int(facing[1])))
        x = min(state.player.x + 1, max(state.player.x - 1, int(cursor[0]) + int(dx)))
        y = min(state.player.y + 1, max(state.player.y - 1, int(cursor[1]) + int(dy)))
        if (x, y) == (state.player.x, state.player.y):
            return
        self._aim_assist_pos = self._aim_assist_identity = None
        self._aim_free_cursor = (x, y)
        self._construct_landing = None

    def _cycle_cross_step_landing(self):
        """借位：在目标确定后预选与双方都相邻的合法落点（Tab 循环）。"""
        from ..core.combat_constructs import cross_step_landings
        state = self.session.state
        point = (getattr(self, '_aim_free_cursor', None)
                 or getattr(self, '_aim_assist_pos', None))
        if point is None:
            dx, dy = self.facing if self.facing and any(self.facing) else (1, 0)
            point = (state.player.x + int(dx), state.player.y + int(dy))
        options = cross_step_landings(state, (int(point[0]), int(point[1])))
        if not options:
            self._construct_landing = None
            self.show_toast(tr('附近没有可供借位的合法空格。'), 3)
            return
        current = self._construct_landing
        try:
            index = next(i for i, option in enumerate(options) if option == current)
        except StopIteration:
            index = -1
        self._construct_landing = options[(index + 1) % len(options)]

    def _cycle_aim_source(self, delta: int):
        """Cycle explicit firing sources while preserving cursor/landing."""
        if getattr(self, 'construct_aim_id', None) or getattr(self, 'sentence_aim', None):
            return False
        options=self._firing_source_options()
        if not options:
            return False
        current=self._current_source_key()
        index=next((i for i,option in enumerate(options) if option.get('source_key')==current),-1)
        self._begin_equipment_aim(options[(index+delta)%len(options)],preserve_aim=True)
        return True

    def _revalidate_aim_lock(self):
        """A new source may not reach the locked enemy; keep the point, drop the lock."""
        lock = getattr(self, '_aim_assist_identity', None)
        if lock is None:
            return False
        state = self.session.state
        if any(enemy is lock for enemy in state.enemies) and self._aim_target_eligible(lock):
            return False
        self._aim_free_cursor = self._aim_assist_pos
        self._aim_assist_pos = self._aim_assist_identity = None
        self.assist_path = []
        self.show_toast(tr('锁定目标不在新来源射程内，已改为自由落点。'), 3)
        return True

    @staticmethod
    def _source_identity(source):
        if source.kind == 'aggregate':
            return 'aggregate'
        if source.kind == 'item':
            return f"item:{getattr(source, 'instance_ids', ('',))[0]}"
        return f"equipment:{source.action_kind}:{source.choice_key}"

    def aim_key(self, key, directions=None):
        if not self.aiming:
            return False
        if getattr(self, 'equipment_choice', None) is not None:
            # 瞄准中打开的来源表优先接管输入；否则方向键会同时移动落点。
            return False
        # 失败态下任意键 = 取消（方向键也不例外；正常瞄准不走这条）。
        if self._cancel_failed_aim():
            return True
        construct_id = getattr(self, 'construct_aim_id', None)
        construct_form = None
        if construct_id:
            from ..core.combat_constructs import form_of, is_combat
            if is_combat(construct_id):
                construct_form = form_of(construct_id)
            else:
                from ..core import ability_targeting
                construct_form = ability_targeting.aim_form(construct_id)
        item_form = None
        item_index = getattr(self, 'item_aim_index', None)
        if item_index is not None:
            from ..core import item_targeting
            state = self.session.state
            if 0 <= item_index < len(state.inventory):
                item_form = item_targeting.aim_form(
                    state.inventory[item_index].definition_id)
        if key == 'escape':
            self.cancel_aim(); self.refresh_view()
        elif key == 'f' and construct_id is None and item_form is None:
            # Aim -> F opens the full source table; never fires on a double press.
            self._open_aim_source_table()
        elif key in ('comma', 'shift+comma', '<', 'less_than'):
            self._cycle_aim_source(-1 if key in ('shift+comma', '<') else 1)
        elif key == 'tab':
            if construct_id == 'combat.cross_step':
                self._cycle_cross_step_landing()
            elif item_form is not None:
                pass
            elif construct_form in ('melee', 'area', 'point', 'direction'):
                pass
            else:
                self._aim_free_cursor = (None if getattr(self, '_aim_free_cursor', None) is not None
                                         else self._aim_assist_pos or (self.session.state.player.x, self.session.state.player.y))
                self._aim_assist_identity = self._aim_assist_pos = None
            self.refresh_view()
        elif key in ('enter', 'return'):
            self.confirm_aim()
        elif directions and key in directions:
            cursor = getattr(self, '_aim_free_cursor', None)
            dx, dy = directions[key]
            if item_form is not None:
                self._item_aim_direction_key(dx, dy)
                self.refresh_view()
            elif construct_form in ('melee', 'area'):
                self._move_construct_cursor(dx, dy)
                self.refresh_view()
            elif construct_form == 'direction':
                self._aim_direction = ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
                self.refresh_view()
            elif construct_form == 'point':
                state = self.session.state
                base = cursor or (state.player.x, state.player.y)
                nx = min(state.player.x + self._aim_range(),
                         max(state.player.x - self._aim_range(), base[0] + dx))
                ny = min(state.player.y + self._aim_range(),
                         max(state.player.y - self._aim_range(), base[1] + dy))
                if (nx, ny) != (state.player.x, state.player.y):
                    self._aim_free_cursor = (nx, ny)
                self._aim_assist_identity = self._aim_assist_pos = None
                self.refresh_view()
            elif cursor is not None:
                state = self.session.state
                self._aim_free_cursor = (max(0,min(state.width-1,cursor[0]+dx)), max(0,min(state.height-1,cursor[1]+dy)))
                self.refresh_view()
            else:
                self.confirm_aim(direction=directions[key])
        else:
            return False
        return True
