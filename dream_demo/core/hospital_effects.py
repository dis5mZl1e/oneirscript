"""Portable hospital material effects; the same rules apply to both sides."""
from ..materials import portent_def
from ..i18n import tr
from .entities import ActionResult
from .constants import ActionKind


SLEEP_FAMILY = frozenset({'deep_sleep', 'melatonin', 'sk_drowsy'})


class HospitalEffectMixin:
    def _neutralize_hospital_dust(self, x, y):
        """One gas kind per cell: partial conversion places real carrier nearby."""
        c = self.cell(x, y)
        requested = min(c.liquid, c.gas)
        if requested <= 0:
            return 0
        if requested == c.gas:
            c.gas_kind = '无菌载气'
            transferred = requested
        else:
            transferred = 0
            for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                out = self.cell(nx, ny)
                if out.solid or (out.gas and out.gas_kind != '无菌载气'):
                    continue
                take = min(requested - transferred, 100 - out.gas)
                if take <= 0:
                    continue
                out.gas_kind, out.gas = '无菌载气', out.gas + take
                transferred += take
                self._sync_material_position(nx, ny)
                if transferred == requested:
                    break
            c.gas -= transferred
        c.liquid -= transferred
        if c.liquid == 0:
            c.liquid_kind = ''
        self._sync_material_position(x, y)
        return transferred

    def restore_resource(self, resource, amount, *, ingested=False, natural=False,
                         reason=None, source=''):
        """Settle actual recovery; derived supplements cannot trigger themselves.

        2026-10-18 docs §10 第三批：恢复也记录 SettlementResult（请求量与实际
        恢复量、是否被上限截断、原因与来源），派生补益另记一条，便于自我觉察
        回答「为什么这次只恢复了这么少」。
        """
        from .settlement import (
            REASON_RESTORE_DERIVED, REASON_RESTORE_ITEM, REASON_RESTORE_NATURAL,
            REASON_RESTORE_SCENE, record_settled_value,
        )
        if resource not in ('mind', 'lucidity', 'imagination'):
            raise ValueError(resource)
        if reason is None:
            reason = (REASON_RESTORE_ITEM if ingested
                      else REASON_RESTORE_NATURAL if natural else REASON_RESTORE_SCENE)
        before = getattr(self, resource)
        maximum = getattr(self, 'max_' + resource)
        restored = min(max(0, amount), max(0, maximum - before))
        if restored <= 0:
            record_settled_value(
                self, resource, requested=float(amount), before=float(before),
                after=float(before), reason=reason, source=source,
                blocked='at_max' if before >= maximum else 'no_amount',
            )
            return 0
        setattr(self, resource, before + restored)
        record_settled_value(
            self, resource, requested=float(amount), before=float(before),
            after=float(before + restored), reason=reason, source=source,
        )
        if ingested:
            self.hospital_equipment_recovery(resource, restored, ingested=True)
        if natural and not getattr(self, '_equipment_derived_depth', 0):
            from ..equipment.library import library_recovery_bonus
            bonus = library_recovery_bonus(self, resource, restored, natural=True)
            if bonus:
                derived_before = getattr(self, resource)
                derived_after = min(getattr(self, 'max_' + resource), derived_before + bonus)
                setattr(self, resource, derived_after)
                record_settled_value(
                    self, resource, requested=float(bonus), before=float(derived_before),
                    after=float(derived_after), reason=REASON_RESTORE_DERIVED,
                    source='图书馆/派生恢复', channel='derived',
                )
        if (self.player.portents.get('hospital_sensitive', 0) > 0
                and not getattr(self, '_equipment_derived_depth', 0)):
            other = next((r for r in ('mind', 'lucidity', 'imagination')
                          if r != resource and getattr(self, r) < getattr(self, 'max_' + r)), None)
            if other:
                self._clear_hospital_buff('hospital_sensitive')
                other_before = getattr(self, other)
                other_after = min(getattr(self, 'max_' + other), other_before + 3)
                setattr(self, other, other_after)
                record_settled_value(
                    self, other, requested=3.0, before=float(other_before),
                    after=float(other_after), reason=REASON_RESTORE_DERIVED,
                    source='疗养院敏感体质', channel='derived',
                )
        return restored

    def hospital_safe_rest(self):
        cell = self.cell(self.player.x, self.player.y)
        if cell.flame or (self.player.x, self.player.y) in self.electric_field_cells():
            return False
        if any(e.integrity > 0 and e.relation not in ('稳定意识', '玩偶意识体')
               and self.can_see(self.player, e.x, e.y) for e in self.enemies):
            return False
        from ..materials import PORTENT_DEFINITIONS
        if any(d.kind == '负面' and d.material and self._cell_holds_material(cell, d.material, d.min_amount)
               for d in PORTENT_DEFINITIONS.values()):
            return False
        return not ((cell.gas_kind in ('胞尘', '梦醚气') and cell.gas >= 6)
                    or (cell.liquid_kind == '梦醚' and cell.liquid >= 4))

    def _hospital_initial_duration(self, holder, pid, duration):
        definition = portent_def(pid)
        if (holder is self.player and not holder.portents.get(pid, 0)
                and holder.portents.get('hospital_immune_once', 0) > 0
                and definition and definition.kind == '负面' and definition.duration > 0):
            self._clear_hospital_buff('hospital_immune_once')
            return max(1, duration - 2)
        return duration

    def _clear_hospital_buff(self, pid):
        for table in (self.player.portents, self.player.portent_attach,
                      self.player.portent_debt, self.player.portent_stacks):
            table.pop(pid, None)

    def hospital_regeneration_rate(self):
        return max(self.hospital_cooldown_rate(self.player),
                   1.25 if self.player.portents.get('hospital_fluent', 0) > 0 else 1.0)

    def _consume_hospital_buffer(self, amount, kind):
        if amount <= 0:
            return amount
        for pid, reduction in (('hospital_pain_buffer', 2), ('hospital_gel_buffer', 1)):
            if pid == 'hospital_pain_buffer' and kind != 'mind':
                continue
            if self.player.portents.get(pid, 0) > 0:
                self._clear_hospital_buff(pid)
                amount = max(0, amount - reduction)
                if not amount:
                    break
        return amount

    def control_hospital_facility(self, event, control):
        if self.realm_id != 'white_sanatorium' or event not in self.events:
            return ActionResult(False, tr('此设备不在当前疗所。'))
        if max(abs(event.x-self.player.x), abs(event.y-self.player.y)) > 1:
            return ActionResult(False, tr('请先接近设备。'))
        if control.get('operation') == 'fluid_valve':
            enabled = bool(control['enabled'])
            if self.realm_features.get('core_fluid_open', True) == enabled:
                return ActionResult(False, tr('阀门已经处于所选状态。'))
            self.realm_features['core_fluid_open'] = enabled
            message = tr('配液阀已开启。' if enabled else '配液阀已关闭，设备不能继续向槽内配液。')
            data = {'core_fluid_open': enabled}
        elif control.get('operation') == 'lights':
            sources = control.get('sources', ())
            enabled = bool(control['enabled'])
            if not any(self.cell(*p).light_on != enabled for p in sources):
                return ActionResult(False, tr('这组灯已经处于所选状态。'))
            for p in sources:
                self.set_light_enabled(*p, enabled)
            message = tr('灯段已开启。' if enabled else '灯段已关闭，敌我视野同时改变。')
            data = {'light_sources': sources, 'enabled': enabled}
        else:
            tank = next((t for t in self.realm_features.get('tanks', ())
                         if t['uid'] == control.get('tank_uid')), None)
            if not tank:
                return ActionResult(False, tr('储罐记录不存在。'))
            kind = tank['gas']
            available = [(tuple(p), self.cell(*p)) for p in tank['cells']
                         if self.cell(*p).gas_kind == kind and self.cell(*p).gas > 0]
            quantity = sum(c.gas for _, c in available)
            if quantity <= 0:
                return ActionResult(False, tr('储罐已经耗尽，不会自动回充。'))
            container = None
            if control.get('operation') == 'draw':
                for item in self.inventory:
                    spec = self._container_spec(item)
                    if (spec.get('medium') == 'gas'
                            and (spec.get('multi') or not item.contents or kind in item.contents)
                            and sum(item.contents.values()) < spec.get('cap', 0)):
                        container = item
                        capacity = spec['cap'] - sum(item.contents.values())
                        break
                if container is None:
                    return ActionResult(False, tr('没有可容纳此气体的容器，请腾出容量或倒空异种气体。'))
            elif control.get('operation') == 'vent':
                outlet = self.cell(event.x, event.y)
                if outlet.solid or (outlet.gas and outlet.gas_kind != kind):
                    return ActionResult(False, tr('端口被阻挡或有异种气体，未排放。'))
                capacity = 100-outlet.gas
            else:
                return ActionResult(False, tr('没有这个设备操作。'))
            transferred = min(6, quantity, capacity)
            if transferred <= 0:
                return ActionResult(False, tr('端口或容器没有剩余容量。'))
            remaining = transferred
            decay_marks = []
            for p, cell in available:
                take = min(cell.gas, remaining)
                self._prime_material_clocks(cell)
                decay_marks.append(cell.material_clocks['decay:' + kind])
                cell.gas -= take
                remaining -= take
                if not cell.gas:
                    cell.gas_kind = ''
                self._sync_material_position(*p)
                if not remaining:
                    break
            if container:
                self._remember_sealed_gas_age(container,kind,min(decay_marks))
                container.contents[kind] = container.contents.get(kind, 0)+transferred
            else:
                self._add_gas(outlet,kind,transferred,decay_mark=min(decay_marks))
                self._sync_material_position(event.x, event.y)
            data = {'transferred': transferred, 'tank_uid': tank['uid']}
            message = tr('储罐转移了 {kind} ×{n}；剩余 {left}。', kind=tr(kind), n=transferred, left=quantity-transferred)
        self.close_event_dialog()
        self._action_time(1, ActionKind.USE)
        self.messages.append(message)
        return ActionResult(True, message, data)

    def cleanse_target(self, holder, allowed=None):
        candidates = []
        for pid, turns in holder.portents.items():
            definition = portent_def(pid)
            if (turns <= 0 or not definition or not definition.washable
                    or (allowed is not None and pid not in allowed)):
                continue
            duration = turns + max(0, holder.portent_attach.get(pid, 0))
            candidates.append((-duration, definition.kind != '负面', pid))
        return min(candidates)[2] if candidates else None

    def shorten_portent(self, holder, budget, allowed=None):
        """Spend one budget, attachment first; preserve periodic debt until expiry."""
        pid = self.cleanse_target(holder, allowed)
        if not pid or budget <= 0:
            return None
        attachment = max(0, holder.portent_attach.get(pid, 0))
        spent = min(budget, attachment)
        attachment -= spent
        if attachment:
            holder.portent_attach[pid] = attachment
        else:
            holder.portent_attach.pop(pid, None)
        holder.portents[pid] -= budget - spent
        if holder.portents[pid] <= 0:
            definition = portent_def(pid)
            stacks = holder.portent_stacks.get(pid, definition.stacks)
            if definition.stacks and stacks > definition.duration_drop:
                holder.portent_stacks[pid] = stacks - definition.duration_drop
                holder.portents[pid] = definition.duration
                holder.portent_debt[pid] = 0
            else:
                self._remember_portent_end(holder, pid)
        return pid

    def hospital_cooldown_rate(self, holder):
        cell = self.cell(holder.x, holder.y)
        contact = cell.liquid_kind == '脑脊液' and cell.liquid >= 4
        attached = holder.hospital_state.get('cerebral_left', 0) > 0
        return 1.25 if contact or attached else 1.0

    def _tick_hospital_contact(self, holder, amount):
        if holder is self.player and getattr(self,'stasis_turns',0)>0:
            holder.hospital_state['last_time']=self.time
            return
        if holder.integrity <= 0 or amount <= 0:
            return
        st = holder.hospital_state
        last = st.get('last_time', self.time - amount)
        elapsed = min(amount, max(0, self.time - last))
        if not elapsed:
            return
        st['last_time'] = self.time
        cell = self.cell(holder.x, holder.y)
        wall = any(self.cell(x, y).solid and self.cell(x, y).wall_kind == '净相壁'
                   for x, y in ((holder.x-1, holder.y), (holder.x+1, holder.y),
                                (holder.x, holder.y-1), (holder.x, holder.y+1))
                   if 0 <= x < self.width and 0 <= y < self.height)
        for _ in range(int(elapsed)):
            for key in ('cleanse_left', 'wake_left', 'cerebral_left'):
                st[key] = max(0, st.get(key, 0) - 1)
            if cell.liquid_kind == '脑脊液' and cell.liquid >= 4:
                st['cerebral_left'] = 3
            if (cell.liquid_kind == '凝胶基液' and cell.liquid >= 4
                    and self.time >= st.get('gel_ready', 0)
                    and not holder.portents.get('hospital_gel_buffer', 0)
                    and self._apply_direct_portent(holder, 'hospital_gel_buffer', 5)):
                st['gel_ready'] = self.time + 8
            if 'pathogen' in holder.biological_tags and cell.liquid_kind == '淋巴液' and cell.liquid >= 4:
                st['lymph_credit'] = st.get('lymph_credit', 0) + 1
                if st['lymph_credit'] >= 2:
                    st['lymph_credit'] -= 2
                    holder.integrity = max(0, holder.integrity - 2)
            else:
                st['lymph_credit'] = 0
            wash = cell.liquid_kind == '洗兆液' and cell.liquid >= 4
            mist = cell.gas_kind == '消兆薄雾' and cell.gas >= 6
            if not st.get('cleanse_left') and (wall or wash or mist):
                pid = self.shorten_portent(holder, 3 if wash else 2 if wall else 1)
                if pid:
                    st['cleanse_left'] = 4
                    if wash:
                        cell.liquid -= 1
                    if holder is self.player:
                        self.messages.append(tr('洁净削短了「{name}」的持续。', name=tr(portent_def(pid).name)))
            waking = ((cell.liquid_kind == '晨醒溶液' and cell.liquid >= 4)
                      or (cell.gas_kind == '醒素薄气' and cell.gas >= 6))
            if waking and not st.get('wake_left'):
                if self.shorten_portent(holder, 2, SLEEP_FAMILY):
                    st['wake_left'] = 6
