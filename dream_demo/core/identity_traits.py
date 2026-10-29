"""Dream identity rules. Rewards come from committed world facts, never UI ticks."""
from __future__ import annotations

from ..i18n import tr
from ..equipment.root_facts import root_action
from ..materials import portent_def
from .constants import ActionKind
from .entities import ActionResult
from .vision.cache import invalidate


class IdentityMixin:
    def identity_abilities(self) -> list[str]:
        return {'fog': ['borrow_fog'], 'writer': ['retract']}.get(self._identity(), [])

    def _identity(self) -> str:
        return self.dream_type_choice.get('identity', 'ordinary')

    def _identity_layer_key(self) -> str:
        return f'R{self.realm_id}:{self.realm_depth}' if self.realm_id else str(self.depth)

    def _identity_ready(self, rule: str) -> bool:
        return self.time >= self.identity_state.get('cooldowns', {}).get(rule, 0)

    def _identity_cooldown(self, rule: str, duration: int) -> None:
        self.identity_state.setdefault('cooldowns', {})[rule] = self.time + duration

    def _identity_immune(self, pid: str) -> bool:
        return (self._identity(), pid) in {('fog', 'poisoned'), ('ember', 'burning')}

    def _clear_identity_immunities(self) -> None:
        for pid in tuple(self.player.portents):
            if self._identity_immune(pid):
                for mapping in (self.player.portents, self.player.portent_debt,
                                self.player.portent_attach, self.player.portent_stacks):
                    mapping.pop(pid, None)

    def _identity_attachment(self, pid: str, cell, duration: float) -> float:
        """Keep fractional attachment so a 20% tolerance never truncates to zero."""
        definition = portent_def(pid)
        if not definition or not definition.material:
            return duration
        material = definition.material
        if cell.liquid_kind == material and cell.liquid > 0:
            category = 'liquid'
        elif cell.gas_kind == material and cell.gas > 0:
            category = 'gas'
        else:
            return duration
        self.identity_state.setdefault('attachment_sources', {})[pid] = {
            'material': material, 'category': category,
        }
        if definition.kind != '负面':
            return duration
        identity = self._identity()
        tolerant = ((identity == 'paper' and pid == 'poisoned')
                    or (identity == 'rain' and category == 'liquid')
                    or (identity == 'porcelain' and pid == 'corroded')
                    or (identity == 'mirror' and definition.vision < 0))
        return duration * 0.8 if tolerant else duration

    def _identity_ignition(self) -> None:
        if self._identity() != 'ember' or not self._identity_ready('borrowed_fire'):
            return
        self.identity_state['fire_buffer'] = {'until': self.time + 3, 'amount': 2}
        self._identity_cooldown('borrowed_fire', 12)

    # 身份环境弱点：只对本身份的对应通道生效（docs §10 第四批：独特条件规则
    # 保留，不把一个身份弱点伪装成通用抗性）。
    IDENTITY_VULNERABILITIES = {
        'paper': {'fire': .15}, 'writer': {'fire': .10},
        'rain': {'electric': .15}, 'ember': {'electric': .15},
        'mirror': {'electric': .10},
    }

    def _identity_vulnerability_factor(self, channel: str) -> float:
        return self.IDENTITY_VULNERABILITIES.get(self._identity(), {}).get(channel, 0.0)

    def _identity_trauma_preview(self, amount: int, channel: str, *,
                                 direct: bool = True) -> tuple[int, tuple[str, ...]]:
        """只读预览环境即时创伤（与结算同一套身份弱点与缓冲规则）。

        不消费火焰缓冲、不改小数弱点欠账；一次性缓冲会以说明标注「将消耗」。
        """
        if amount <= 0:
            return 0, ()
        sources: list[str] = []
        factor = self._identity_vulnerability_factor(channel)
        if factor:
            credit = (self.identity_state.get('vulnerability_debt', {}) or {}).get(channel, 0.0)
            extra = int(amount * factor + credit + 1e-9)
            amount += extra
            sources.append(tr('身份弱点 {identity} · {channel} +{n}', identity=self._identity(),
                              channel=channel, n=extra))
        if channel == 'fire' and direct:
            buffer = self.identity_state.get('fire_buffer')
            if buffer and self.time < buffer.get('until', 0):
                sources.append(tr('火焰缓冲将抵消 {n}', n=buffer.get('amount', 0)))
                amount = max(0, amount - buffer.get('amount', 0))
        return amount, tuple(sources)

    def _identity_environment_trauma(self, amount: int, channel: str, *, direct: bool = True) -> int:
        if amount <= 0:
            return 0
        # Carry small vulnerabilities across repeated hits instead of rounding
        # every one-point flame/electric tick back to one.
        factor = self._identity_vulnerability_factor(channel)
        if factor:
            credits = self.identity_state.setdefault('vulnerability_debt', {})
            credit = credits.get(channel, 0) + amount * factor
            extra = int(credit + 1e-9)
            credits[channel] = max(0, credit - extra)
            amount += extra
        if channel == 'fire' and direct:
            buffer = self.identity_state.pop('fire_buffer', None)
            if buffer and self.time < buffer['until']:
                amount = max(0, amount - buffer['amount'])
        return amount

    def _identity_mark_created_wall(self, x: int, y: int, ability: str) -> None:
        self.identity_state['wall_serial'] = self.identity_state.get('wall_serial', 0) + 1
        self.cell(x, y).creation = {'owner': self.player.id, 'ability': ability,
                                  'serial': self.identity_state['wall_serial']}

    def _identity_before_move(self) -> dict:
        cell = self.cell(self.player.x, self.player.y)
        result = {'liquid': cell.liquid_kind if cell.liquid > 0 else '', 'tracking': []}
        if self._identity() == 'paper' and self._identity_ready('late_steps'):
            result['tracking'] = [e.id for e in self.enemies
                if e.integrity > 0 and e.relation == '失控意识' and e.alert_state == '追踪'
                and max(abs(e.x-self.player.x), abs(e.y-self.player.y)) <= e.vision
                and self._has_line_of_sight(e.x, e.y, self.player.x, self.player.y)]
        return result

    def _identity_after_move(self, origin: tuple, before: dict) -> None:
        if origin == (self.player.x, self.player.y):
            return
        if self._identity() == 'rain' and self._identity_ready('water_trace') and before['liquid']:
            cell = self.cell(self.player.x, self.player.y)
            if cell.liquid <= 0:
                sources = self.identity_state.get('attachment_sources', {})
                matching = [pid for pid, attach in self.player.portent_attach.items()
                    if attach > 0 and pid in self.player.portents and portent_def(pid)
                    and portent_def(pid).kind == '负面'
                    and sources.get(pid) == {'category': 'liquid', 'material': before['liquid']}]
                if matching:
                    pid = max(matching, key=lambda p: self.player.portent_attach[p])
                    self.player.portent_attach[pid] = max(0, self.player.portent_attach[pid] - 1)
                    self._identity_cooldown('water_trace', 10)
        if self._identity() == 'paper' and before['tracking']:
            lost = any(e.id in before['tracking'] and e.integrity > 0 and not
                self._has_line_of_sight(e.x, e.y, self.player.x, self.player.y)
                for e in self.enemies)
            if lost and self._identity_ready('late_steps'):
                self._identity_cooldown('late_steps', 14)
                self.identity_state['late_sound'] = {'position': list(origin), 'until': self.time + 1}
                self._sound_pulse(*origin, 3)

    def _identity_direct_trauma(self, enemy, mind: int, lucidity: int, *, direct: bool = True) -> None:
        hostile = direct and enemy is not None and enemy.relation == '失控意识'
        if hostile:
            axis = 'mind' if self._identity() == 'fog' else 'lucidity' if self._identity() == 'porcelain' else None
            if axis:
                value = mind if axis == 'mind' else lucidity
                debts = self.identity_state.setdefault('vulnerability_debt', {})
                credit = debts.get(axis, 0) + max(0, value) * .1
                extra = int(credit + 1e-9)
                debts[axis] = max(0, credit - extra)
                if axis == 'mind':
                    mind += extra
                else:
                    lucidity += extra
        previous = self.mind + self.lucidity
        source_id = enemy.id if enemy is not None else ''
        previous_indirect = getattr(self, '_presentation_indirect_trauma', False)
        self._presentation_indirect_trauma = previous_indirect or not direct
        try:
            self._lose_mind(mind, combat=True, source_id=source_id)
            self._suffer_lucidity(lucidity, source_id=source_id)
        finally:
            self._presentation_indirect_trauma = previous_indirect
        actual = max(0, previous - self.mind - self.lucidity)
        if (hostile and actual > 0 and self._identity() == 'mirror'
                and self._identity_ready('borrowed_strike')):
            self.identity_state['borrowed_strike'] = {'amount': min(2, actual), 'until': self.time + 4}
            self._identity_cooldown('borrowed_strike', 12)

    def _identity_melee_bonus(self, target, normal: bool) -> int:
        if not normal or self._identity() != 'mirror' or target.integrity <= 0 or target.relation != '失控意识':
            return 0
        stored = self.identity_state.pop('borrowed_strike', None)
        return stored['amount'] if stored and self.time < stored['until'] else 0

    def _identity_receiver(self, x: int, y: int, instance: str = '') -> None:
        if self._identity() != 'porcelain':
            return
        key = self._identity_layer_key()
        record = self.identity_state.setdefault('circuit_layers', {}).setdefault(key, {'seen': [], 'paid': 0})
        receiver = f'{instance}:{x},{y}:{self.cell(x, y).wall_kind}'
        if receiver in record['seen']:
            return
        record['seen'].append(receiver)
        if record['paid'] >= 2 or not self._identity_ready('circuit_echo'):
            return
        record['paid'] += 1
        self._identity_cooldown('circuit_echo', 12)
        self.restore_resource('imagination', 2)

    def _identity_note_gate_source(self, gate: tuple, source: tuple) -> None:
        if self._identity() == 'porcelain':
            key = f'{self._identity_layer_key()}:{gate[0]},{gate[1]}'
            causes = self.identity_state.setdefault('gate_sources', {}).setdefault(key, [])
            if list(source) not in causes:
                causes.append(list(source))

    @root_action
    def activate_identity_ability(self, ability: str, tx: int | None = None,
                                  ty: int | None = None) -> ActionResult:
        identity, cost = {'borrow_fog': ('fog', 5), 'retract': ('writer', 4)}.get(ability, ('', 0))
        if self._identity() != identity:
            return ActionResult(False, tr('这个身份没有此项能力。'))
        if not self._identity_ready(ability):
            return ActionResult(False, tr('身份能力仍在冷却。'))
        if self.imagination < cost:
            return ActionResult(False, tr('想象力不足（需要 {cost}）。', cost=cost))
        if ability == 'retract':
            if tx is None or ty is None:
                tx = self.player.x + self.facing[0]
                ty = self.player.y + self.facing[1]
            if not (0 < tx < self.width - 1 and 0 < ty < self.height - 1
                    and max(abs(tx-self.player.x), abs(ty-self.player.y)) == 1):
                return ActionResult(False, tr('相邻没有可以退稿的墙。'))
            cell = self.cell(tx, ty)
            provenance = cell.creation
            if (not cell.solid or cell.wall_kind not in {'蜡化记忆墙', '臆造聚合墙'}
                    or provenance.get('owner') != self.player.id
                    or provenance.get('ability') not in {'wax_seal', 'conjure_wall'}
                    or not provenance.get('serial') or cell.wire
                    or self.circuit_node_at(tx, ty) is not None
                    or self.puzzle_projectile_blocked(tx, ty)):
                return ActionResult(False, tr('这面墙不属于你的可撤回构想。'))
            self.clear_wall(cell)
            self._sync_material_position(tx, ty)
            invalidate(self)
            layers = self.identity_state.setdefault('retracted_layers', {})
            key = self._identity_layer_key()
            first = not layers.get(key, False)
            layers[key] = True
            message = tr('你撤去了自己写下的墙。')
        else:
            # A small 36-unit cloud survives both casting and the first step
            # away. Material diffusion runs before hostile sight updates.
            self._add_gas(self.cell(self.player.x, self.player.y), '黑烟', 36)
            self._sync_material_position(self.player.x, self.player.y)
            invalidate(self)
            first = False
            message = tr('你在脚下留下了一小团雾。')
        from .settlement import REASON_ABILITY_COST, settle_delta
        settle_delta(self, 'imagination', -cost, reason=REASON_ABILITY_COST,
                     source='身份能力')
        if first:
            self.restore_resource('imagination', 2)
        self._identity_cooldown(ability, 14)
        self._action_time(1, ActionKind.USE)
        self.messages.append(message)
        return ActionResult(True, message, {'identity_ability': ability})
