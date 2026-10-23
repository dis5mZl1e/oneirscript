"""Realm-only material supplies and readable, recoverable puzzle controls."""
from ..data.realm_challenges import EMBER_STAGES, EMBER_CONTAINER, TEXT, event_definitions
from ..i18n import tr
from .entities import WorldEvent, ActionResult


def say(key, **values):
    return tr(TEXT[key][0], **values)


def ensure_ember(state):
    info = state.realm_challenges.get('ember_bridge')
    if not info or info.get('version') != 3:
        from .realm_layouts import prepare_ember_materials
        prepare_ember_materials(state, state.cells)
        info = {'version': 3, 'supply': [False]*3, 'vent_rounds': None,
                'routed': False, 'cooling': False, 'cooled': False}
        state._reset_material_index()
    state.realm_challenges['ember_bridge'] = info
    existing = {e.event_id: e for e in state.events}
    for definition in event_definitions().values():
        event_id = definition['event_id']
        # 这张表现在也登记**其它 realm** 的事件定义（千禧园终端，2026-10-10）；
        # 阀台只认自己的 id、阶段号从 id 里解析——不能按下标枚举整张表，
        # 否则任何新事件一登记，EMBER_STAGES[index] 就越界。
        if not event_id.startswith('realm_valve.ember'):
            continue
        index = int(event_id.rsplit('ember', 1)[1])
        x, y = EMBER_STAGES[index]['panel']
        if state.cell(x, y).solid:
            state.clear_wall(state.cell(x, y))
        event = existing.get(definition['event_id'])
        if event is None:
            event = WorldEvent(x=x, y=y, catalog_id=definition['event_id'],
                               bound=True, **definition)
            state.events.append(event)
        else:
            # Old saves may have spent, simple or stale versions of these events.
            event.x, event.y, event.kind = x, y, 'compound'
            event.name, event.description = definition['name'], definition['description']
            event.dialogue, event.options = definition['dialogue'], definition['options']
        event.resolved = not state.cell(*EMBER_STAGES[index]['gate']).solid
    for event in state.events:
        if event.event_id == 'realm_reward.ember_bridge' and not any(
                o.get('exit_realm') and not o.get('reward_id') for o in event.options):
            event.options += ({'label': TEXT['empty_exit'][0], 'exit_realm': 'clear'},)
    return info


def tick_ember(state, amount=0):
    if state.realm_id != 'ember_bridge':
        return
    # Remember the transition before ensure_ember refreshes old event definitions.
    previous = {e.event_id: e.resolved for e in state.events}
    info = ensure_ember(state)
    if info['vent_rounds'] is not None:
        info['vent_rounds'] += amount
    for index, stage in enumerate(EMBER_STAGES):
        gate = state.cell(*stage['gate'])
        event = next(e for e in state.events if e.event_id == f'realm_valve.ember{index}')
        if not gate.solid:
            info['supply'][index] = False
            if not previous.get(event.event_id, False):
                # A material reaction releases the hinged partition; this never
                # bypasses the material simulation or computes damage a second time.
                gx, _ = stage['gate']
                for y in range(10, 14):
                    state.clear_wall(state.cell(gx, y))
                event.resolved = True
                if index == 2:
                    info['cooling'] = False
                state._reset_material_index()
                state.messages.append(say('cleared', stage=index+1))
            continue
        if info['supply'][index] and index < 2:
            source = state.cell(*stage['source'])
            kind = '燃油' if index == 0 else '酸蚀液'
            state._add_liquid(source, kind, max(0, 80-source.liquid))
        if index == 2 and info['supply'][index]:
            jet = state.cell(*stage['jet'])
            if info['cooling']:
                source = state.cell(*stage['source'])
                state._add_liquid(source, '水', max(0, 80-source.liquid))
                if jet.liquid_kind == '水' and jet.liquid >= 10 and not jet.flame:
                    info['cooled'] = True
            # Sealed local gas supply, not three identical injected oil blasts.
            if not info['cooled']:
                # A thermal interlock holds gas back until real flowing water
                # extinguishes the heater. Hot gas must not auto-clear this gate
                # through normal flame spread before the controls can be used.
                jet.gas, jet.gas_kind = 0, ''
                if jet.liquid_kind != '水' or jet.liquid < 10:
                    state._set_flame(*stage['jet'], 4)
            else:
                jet.gas_kind = '可燃气体'
                jet.gas = (max(65, round(100-12*max(0, info['vent_rounds']-1)))
                           if info['vent_rounds'] is not None else 100)
            state._sync_material_position(*stage['jet'])


def ensure_tide_exit(state):
    """Keep legacy exit locations but make a full pack unable to trap the player."""
    for event in state.events:
        if event.event_id == 'realm_exit.ebbing_hall' and not any(
                o.get('exit_realm') and not o.get('reward_id') for o in event.options):
            event.options += ({'label': TEXT['empty_exit'][0], 'exit_realm': 'clear'},)


def sealed_gas_cells(state):
    """The pressure apparatus is sealed until its partition is opened.

    Cooling water flows through the jacket, while the gas stays in its pocket;
    venting changes its pressure through the valve rather than room diffusion.
    """
    if state.realm_id != 'ember_bridge':
        return frozenset()
    stage = EMBER_STAGES[2]
    return frozenset((stage['jet'],)) if state.cell(*stage['gate']).solid else frozenset()


def valve_pressure(state, event):
    """Read actual fluid, wall and pressure state; never claim a solved puzzle."""
    index = int(event.event_id.rsplit('ember', 1)[1])
    info = ensure_ember(state)
    stage = EMBER_STAGES[index]
    jet = state.cell(*stage['jet'])
    if index == 2:
        return say('chamber', pressure=jet.gas, cooled=say('on' if info['cooled'] else 'off'),
                   vent=say('on' if info['vent_rounds'] is not None else 'off'))
    return say('flow', kind=tr(jet.liquid_kind or '空'), amount=jet.liquid,
               integrity=state.cell(*stage['gate']).integrity,
               feed=say('on' if info['supply'][index] else 'off'))


def control_ember(state, event, control):
    if state.realm_id != 'ember_bridge' or event.resolved:
        return ActionResult(False)
    index, action = control['stage'], control['action']
    stage = EMBER_STAGES[index]
    # These are local controls, even when invoked through a stale dialog.
    if max(abs(event.x-state.player.x), abs(event.y-state.player.y)) > 1:
        return ActionResult(False, say('unsafe'))
    info = ensure_ember(state)
    if action == 'feed':
        if index == 1 and state.cell(*EMBER_CONTAINER).solid:
            return ActionResult(False, say('need_can'))
        info['supply'][index] = True
        if index == 2:
            info['vent_rounds'] = None
        tick_ember(state)
        message = valve_pressure(state, event)
    elif action == 'route' and index == 0:
        state.clear_wall(state.cell(12, 12))
        info['routed'] = True
        state._reset_material_index()
        message = say('routed')
    elif action == 'mix' and index == 1:
        if not info['supply'][index]:
            return ActionResult(False, say('unprimed'))
        state._add_liquid(state.cell(*stage['source']), '水', 50)
        message = say('mixed')
    elif action == 'cool' and index == 2:
        if not info['supply'][index]:
            return ActionResult(False, say('unprimed'))
        info['cooling'] = True
        tick_ember(state)
        message = say('cooling')
    elif action == 'vent' and index == 2:
        if not info['supply'][index]:
            return ActionResult(False, say('unprimed'))
        if not info['cooled']:
            return ActionResult(False, say('too_hot'))
        if info['vent_rounds'] is None:
            info['vent_rounds'] = 0
        message = say('vented', rounds=max(0, 2-info['vent_rounds']))
    elif action == 'light' and index in (0, 2):
        if not info['supply'][index]:
            return ActionResult(False, say('unprimed'))
        if (state.player.x, state.player.y) != stage['safe']:
            return ActionResult(False, say('unsafe'))
        jet = state.cell(*stage['jet'])
        if index == 0 and (jet.liquid_kind != '燃油' or jet.liquid < 20):
            return ActionResult(False, say('not_ready'))
        if index == 2:
            if not info['cooled']:
                return ActionResult(False, say('too_hot'))
            if info['vent_rounds'] is None or info['vent_rounds'] < 2 or jet.gas >= 100:
                return ActionResult(False, say('high'))
        if not state._ignite_cell(*stage['jet'], strength=6, by_player=True):
            return ActionResult(False, say('blocked_jet'))
        message = say('lit')
    elif action == 'drain':
        info['supply'][index] = False
        for x in range(stage['source'][0], stage['gate'][0]):
            cell = state.cell(x, 12)
            cell.liquid, cell.liquid_kind, cell.gas, cell.gas_kind, cell.flame = 0, '', 0, '', 0
        if index == 2:
            info.update(cooling=False, cooled=False, vent_rounds=None)
            state.cell(*stage['jet']).flame = 6
        state._reset_material_index()
        message = say('drained')
    else:
        return ActionResult(False)
    state.close_event_dialog()
    state._action_time(1)
    tick_ember(state)
    state.messages.append(message)
    return ActionResult(True, message, {'ember_stage': index, 'ember_action': action})


def challenge_status(state):
    # 掉线拨号（M5，2026-10-10）：主梦机制借用本函数作状态栏通道——
    # _refresh_world_view 已无条件调用这里，响铃期间常驻一行倒计时提示
    # （设计 §4.1「状态栏/面板顶部出现提示行」）。realm 内不显示。
    active = (state.dial_in or {}).get("active")
    if not state.realm_id and active:
        return say('dial_status', n=max(0, int(active.get("rounds", 0))))
    if state.realm_id == 'ember_bridge':
        return say('ember_status', cleared=sum(not state.cell(*s['gate']).solid for s in EMBER_STAGES))
    if state.realm_id == 'ebbing_hall':
        from .ebbing import EBBING_GRACE, EBBING_CONTRACT_INTERVAL, EBBING_MAX_RINGS
        elapsed = state.ebbing_elapsed
        phase = max(0, elapsed-EBBING_GRACE)
        following = (EBBING_GRACE-elapsed+EBBING_CONTRACT_INTERVAL if elapsed < EBBING_GRACE
                     else EBBING_CONTRACT_INTERVAL-phase % EBBING_CONTRACT_INTERVAL)
        return say('tide_status', ring=state.ebbing_contract_rounds, next=following,
                   left=max(0, EBBING_GRACE+EBBING_MAX_RINGS*EBBING_CONTRACT_INTERVAL-elapsed))
    return ''
