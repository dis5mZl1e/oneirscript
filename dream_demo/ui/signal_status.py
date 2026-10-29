"""Read-only sound forecast and chaos UI; never emits a sound or rolls risk."""
from __future__ import annotations

import re

from rich.cells import cell_len
from rich.text import Text
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from ..core import sound_preview
from ..core.chaos import chaos_risk_tier, clamp_chaos
from ..data.tamper_schema import CHAOS_MAX, CHAOS_DECAY_INTERVAL, RISK_TIERS
from ..i18n import get_language, tr

from . import terse as _terse

# 第十九节 §3／§10.1：噪音／混乱／声径与次要文字全部取自面板字段注册表。
from .panel_fields import FIELD_COLORS as _PANEL_FIELDS

NOISE_COLOR = _PANEL_FIELDS['noise']
CHAOS_COLOR = _PANEL_FIELDS['chaos']
MUTED = _PANEL_FIELDS['muted']
RANGE_COLOR = _PANEL_FIELDS['range']
TRACK_COLOR = _PANEL_FIELDS['track']
NOISE_SCALE = 20
# 噪音条最大格数：两行档（#signal-status）与宽屏合并行共用同一上限，
# 口径一致才不会出现「缩窗后条突然变长」的错觉。
NOISE_BAR_MAX = 12


def ambient_noise(app):
    """噪音条：玩家**周围区域**最近的声场强度（来源不必是自己）。

    每条真实脉冲在 core 记录「玩家周围 NOISE_AMBIENT_RADIUS 格内的最大余量」；
    这里取最近 NOISE_AMBIENT_TURNS 回合内的最大值，换算成同一 20 格显示量程。
    没有近期声音时返回 0，而不是把下一动作的预计声径当成环境噪音。
    """
    from ..core.constants import NOISE_AMBIENT_TURNS

    state = app.session.state
    now = int(getattr(state, "time", 0))
    best = -10 ** 9
    events = getattr(state, "_ambient_noise_events", ()) or ()
    for event in events:
        try:
            recorded, _x, _y, local, _player, _radius, _by_player, _category = event
        except (TypeError, ValueError):
            continue
        if now - int(recorded) >= NOISE_AMBIENT_TURNS:
            continue
        best = max(best, int(local))
    radius = 0 if best < 0 else max(0, int(round(best / 2)))
    return {"radius": radius, "context": "周围区域噪音", "pulses": (),
            "sources": (), "silent": radius <= 0}


def noise_preview(app):
    """Forecast the selected action, otherwise a step on the current tile.

    Observing a remote tile or browsing inventory must not change this context.
    This is evaluated on world/UI invalidation, not the animation frame timer.
    """
    state = app.session.state
    pulses = []
    context = '本格踩踏预计'
    pending = getattr(app, 'sentence_aim', None)
    if getattr(app, 'aiming', False):
        index = getattr(app, 'throw_item_index', None)
        target = ((pending or {}).get('cursor') or getattr(app, '_aim_free_cursor', None)
                  or getattr(app, '_aim_assist_pos', None))
        if index is not None:
            context = '投掷落点预计'
            if 0 <= index < len(state.inventory):
                landing = app._throw_landing_cell()
                if landing is not None and state.is_visible(*landing):
                    pulses.append(sound_preview.throw_landing_preview(state, state.inventory[index], landing))
        elif getattr(app, 'fire_once_index', None) is not None:
            context = '一次性发射预计'
            index = app.fire_once_index
            if 0 <= index < len(state.inventory):
                # Current flare payload has no sound entry. Do not invent one.
                pulses.append(sound_preview.pulse_preview(state, (state.player.x, state.player.y), 0))
        else:
            context = '发射载荷预计'
            choice = getattr(app, 'aim_action_choice', None)
            if pending:
                key = pending.get('key')
            elif isinstance(choice, dict):
                key = choice.get('key')
            else:
                key = choice
            if pending and pending.get('command', 'use_equipment_sentence') == 'use_equipment_sentence':
                pulses.append(sound_preview.pulse_preview(state, (state.player.x, state.player.y), 0))
            else:
                plan = state.equipment.plan_action('fire', choice=key)
                spec = dict(plan.projectile_profile)
                if not spec.get('pulse'):
                    pulses.append(sound_preview.pulse_preview(state, (state.player.x, state.player.y), 0))
                elif target is not None:
                    from ..core.throwing import flight_path
                    from ..core.construct_environments import reflected_path
                    path = reflected_path(state, (state.player.x, state.player.y),
                                          flight_path((state.player.x, state.player.y), tuple(target)))
                    for x, y in path[:int(spec.get('range', 12))]:
                        # Unknown geometry and wall-break outcomes cannot be
                        # predicted by looking through the player's knowledge.
                        if not state.is_visible(x, y) or state.cell(x, y).solid:
                            break
                        entity = state.entity_at(x, y)
                        if entity is not None and entity is not state.player:
                            pulses.append(sound_preview.equipment_pulse_preview(state, (x, y), spec))
                            break
                    else:
                        # A pulse is emitted on entity impact, not in empty air.
                        pulses.append(sound_preview.pulse_preview(state, tuple(target), 0))
    else:
        path = getattr(app, 'path', ())
        if path and not getattr(app, 'observe_mode', False):
            context = '下一步踩踏预计'
            pulses.append(sound_preview.footstep_preview(state, path[0]))
        else:
            pulses.append(sound_preview.footstep_preview(state))
    radius = max((p['radius'] for p in pulses), default=None)
    return dict(context=context, radius=radius, pulses=pulses)


def merged_tail_text(base, state, radius, width, *, terse: bool = False):
    """把状态第 5 行与信号行并成一行四项（2026-10-24 纸感分区·状态区合并）。

    ``base`` 是已排好的第 5 行（崩解度／深层边界／可下潜 · 回合数，语义
    原样保留），在其后接「 · 噪音 ┃┃┊ n/m · 混乱 c/m」凑成一行四项；用
    cell_len 对 ``width``（#status 实测可用宽）判断放不放得下——放不下
    （中窄档或数值变宽后）返回 ``(None, None)``，调用方保持两行并恢复
    #signal-status 显示。命中表记录噪音/混乱两段各自在合并行上的列区，
    供 ClickableStatus 平移 #signal-status 的点击（打开共用详情）。

    2026-10-26：合并行自带迷你噪音条。宽屏（全屏最大化）时 #signal-status
    整行被隐藏，那条 ``┃┊`` 噪音条原本也跟着消失，只剩一个数字——全屏反而
    看不到噪音强度。条长按行内剩余列数自适应（最多 12 格、最少 3 格），
    剩余列不够 3 格才退回纯文字，判据仍是「合并后总宽 <= width」。
    """
    hits = {}
    tail = Text()
    tail.append_text(base)
    noise = f'{radius if radius is not None else "—"}/{NOISE_SCALE}'
    chaos = f'{clamp_chaos(state.chaos)}/{CHAOS_MAX}'
    overflow = radius is not None and radius > NOISE_SCALE
    from ..data.semantic_icons import semantic_icon
    markers = {'noise': semantic_icon('noise.pulse'), 'chaos': semantic_icon('stat.chaos')}
    if terse:
        # 少字模式：去掉「噪音」「混乱」中文标签，只留各自图标（语义图标缺失
        # 时用 terse 的两列回退字形，绝不留空）；条与数值照旧。
        markers = {key: (markers[key] or _terse.stat_glyph(key)) for key in markers}
        labels = {'noise': '', 'chaos': ''}
    else:
        labels = {'noise': tr('噪音'), 'chaos': tr('混乱')}
    values = {'noise': noise, 'chaos': chaos}

    def separator(key):
        # 合并行是图标终端里噪音／混乱唯一可见的地方（#signal-status 整行这时被
        # 隐藏），所以把分隔点号的位置换成它们本来的图标：' · ' 三格，' ' + 双格
        # 图标也三格。没有图标的终端退回点号。
        icon = markers[key]
        return (' ' + icon, True) if icon else (' · ', False)

    def plain_width(key):
        # 量程溢出标记 › 只在噪音段、只在超过 20 格时多占 1 格。
        extra = 1 if key == 'noise' and overflow else 0
        return cell_len(separator(key)[0]) + cell_len(labels[key] + ' ' + values[key]) + extra

    # 条占「bars 格 + 1 个空格」；剩余列不够 4 格就不硬塞短条，退回纯文字。
    spare = (width - cell_len(tail.plain) - plain_width('noise') - plain_width('chaos'))
    bars = min(NOISE_BAR_MAX, spare - 1) if spare >= 4 else 0
    for key, color in (('noise', NOISE_COLOR), ('chaos', CHAOS_COLOR)):
        text, has_icon = separator(key)
        tail.append(text, style=color if has_icon else '#ffffff')
        start = cell_len(tail.plain)
        tail.append(labels[key] + ' ', style=color)
        if key == 'noise' and bars:
            fill = min(bars, round(bars * max(0, radius or 0) / NOISE_SCALE))
            tail.append('┃' * fill, style=NOISE_COLOR)
            tail.append('┊' * (bars - fill), style=TRACK_COLOR)
            tail.append(' ', style=NOISE_COLOR)
        tail.append(values[key], style=MUTED if key == 'noise' and radius is None else color)
        if key == 'noise' and overflow:
            tail.append('›', style='#f2bd84')
        hits[key] = (start, cell_len(tail.plain))
    if cell_len(tail.plain) > width:
        return None, None
    hits['row'] = 4  # 合并行固定是 #status 的第 5 行
    return tail, hits


def summary_text(preview, chaos, *, width=44, terse: bool = False):
    radius = preview['radius']
    noise = f'{radius if radius is not None else "—"}/{NOISE_SCALE}'
    chaos = f'{clamp_chaos(chaos)}/{CHAOS_MAX}'
    from ..data.semantic_icons import semantic_icon
    noise_icon = semantic_icon('noise.pulse')
    chaos_icon = semantic_icon('stat.chaos')
    if terse:
        # 少字模式：去掉「噪音」「混乱」中文标签，只留图标（语义图标缺失时
        # 用 terse 的两列回退字形）+ 条 + 数值；宽窄判定仍按实际宽度算。
        noise_lead = (noise_icon + ' ') if noise_icon else _terse.stat_glyph('noise')
        chaos_lead = (chaos_icon + ' ') if chaos_icon else _terse.stat_glyph('chaos')
        fixed = noise_lead + f'{noise}  ' + chaos_lead + f'{chaos}'
    else:
        noise_lead = (noise_icon + ' ') if noise_icon else ''
        chaos_lead = (chaos_icon + ' ') if chaos_icon else ''
        fixed = noise_lead + f'{tr("噪音")}  {noise}  ' + chaos_lead + f'{tr("混乱")} {chaos}'
    bars = min(NOISE_BAR_MAX, max(0, width - cell_len(fixed) - 1))
    fill = min(bars, round(bars * max(0, radius or 0) / NOISE_SCALE))
    text = Text(noise_lead, style=NOISE_COLOR, no_wrap=True)
    if not terse:
        text.append(tr('噪音') + ' ', style=NOISE_COLOR)
    if bars:
        text.append('┃' * fill, style=NOISE_COLOR)
        text.append('┊' * (bars-fill), style=TRACK_COLOR)
        text.append(' ')
    text.append(noise, style=NOISE_COLOR if radius is not None else MUTED)
    if radius is not None and radius > NOISE_SCALE:
        text.append('›', style='#f2bd84')
    if terse:
        text.append('  ' + chaos_lead + chaos, style=CHAOS_COLOR)
    else:
        text.append('  ' + chaos_lead + tr('混乱') + ' ' + chaos, style=CHAOS_COLOR)
    return text


def chaos_tier_effects_text(tier: str) -> str:
    """该档可能副作用的摘要：事件与数值现读 TIER_POOLS／TIER_EFFECTS。

    数值不写死在文案里，平衡调整后说明面板自动跟着变，避免玩家看到旧数字。
    """
    from ..core.tamper_risks import EVENT_LABELS, TIER_EFFECTS, TIER_POOLS

    effects = TIER_EFFECTS.get(tier, {})
    pieces: list[str] = []
    for event_id, _weight in TIER_POOLS.get(tier, ()):
        values = effects.get(event_id) or {}
        label = tr(EVENT_LABELS.get(event_id, event_id))
        if event_id == "ink_blur":
            pieces.append(tr('{label}（清醒创伤 {n}）', label=label,
                             n=int(values.get("lucidity", 0))))
        elif event_id == "glyph_scar":
            pieces.append(tr('{label}（心智创伤 {n}）', label=label,
                             n=int(values.get("mind", 0))))
        elif event_id == "tail_echo":
            pieces.append(tr('{label}（清醒 {lucidity}／心智 {mind}）', label=label,
                             lucidity=int(values.get("lucidity", 0)),
                             mind=int(values.get("mind", 0))))
        elif event_id == "margin_ember":
            pieces.append(tr('{label}（{n} 处）', label=label,
                             n=int(values.get("cells", 1))))
        elif event_id == "omission_visitor":
            pieces.append(tr('{label}（可能现身）', label=label))
        else:
            pieces.append(label)
    # 分隔符随语言走：英文面板里不能残留中文顿号（i18n 覆盖率会查）。
    separator = "、" if get_language() == "zh" else ", "
    return separator.join(pieces)


def chaos_tier_lines(value: int) -> list[tuple[str, bool]]:
    """逐档说明行：(文本, 是否当前档)。范围读 RISK_TIERS，数值读 TIER_EFFECTS。"""
    current = chaos_risk_tier(value)
    rows: list[tuple[str, bool]] = []
    for low, high, tier, _probability in RISK_TIERS:
        line = tr('{tier} {low}–{high}：{effects}', tier=tr(tier), low=low, high=high,
                  effects=chaos_tier_effects_text(tier))
        rows.append((line, tier == current))
    return rows


def detail_text(app, preview):
    state = app.session.state
    text = Text()
    from ..core.constants import NOISE_AMBIENT_TURNS
    ambient = ambient_noise(app)
    text.append(tr('周围区域噪音：{n}/20（最近 {turns} 回合）',
                   n=ambient['radius'], turns=NOISE_AMBIENT_TURNS),
                style='bold ' + NOISE_COLOR)
    text.append('\n' + tr('来自你周围区域的真实声音，来源不一定是自己。'), style=MUTED)
    text.append('\n\n' + tr('本次预计声音'), style='bold ' + NOISE_COLOR)
    text.append('\n' + tr(preview['context']), style='#ffffff')
    radius = preview['radius']
    text.append('\n' + tr('最终声径：{n} 格', n=radius) if radius is not None
                else '\n' + tr('落点未确定：最终声径暂不可知。'), style=RANGE_COLOR)
    text.append('\n' + tr('20 是固定显示量程，不是声音上限，也不是统一警戒阈值。'), style=MUTED)
    for pulse in preview['pulses']:
        x, y = pulse['origin']
        text.append('\n' + tr('发声点：({x},{y}) · 基础 {base} · 最终 {radius}',
                             x=x, y=y, base=pulse['base'], radius=pulse['radius']), style='#b6cae8')
        for source in pulse['sources']:
            text.append('\n  ' + str(source), style='#70cbbb')
        if pulse.get('full_alert'):
            text.append('\n' + tr('强诱引：可能直接引起追踪。'), style='#f18e9b')
    text.append('\n' + tr('这里是行动预计，不是正在持续发声；0 只表示本次预计动作无声。'), style=MUTED)
    text.append('\n' + tr('射击、投掷与声影可在远处发声；声径不等于玩家身体的暴露距离。'), style=MUTED)
    from ..core.construct_environments import active
    echoes=[field for field in active(state) if field['kind']=='echo_pulse']
    if echoes and state.is_visible(*echoes[-1]['position']):
        echo = sound_preview.echo_ability_preview(state)
        if state.is_visible(*echo['origin']):
            text.append('\n' + tr('活动声影下一拍：({x},{y}) · 声径 {n}',
                                 x=echo['origin'][0], y=echo['origin'][1], n=echo['radius']), style=RANGE_COLOR)
    # §11 H1：听觉线索只给方向、距离档、类别与时间；未知声源不写坐标，
    # 视野内已知声源才补精确位置。线索按真实回合过期，不跟随声源移动。
    from ..core.enemies import sound_category_name
    retention = state._clue_retention()
    clues = [clue for clue in state.heard_sound_clues
             if state.time - int(clue.get("time", 0)) < retention]
    if clues:
        text.append('\n\n' + tr('听觉线索'), style='bold ' + RANGE_COLOR)
        bearing = state._sound_bearing_active()
        selected = getattr(app, '_signal_clue_index', None)
        wall_entries = 0
        for index, clue in enumerate(clues):
            where = (f"({clue['x']},{clue['y']})" if clue.get('known')
                     else tr('方向与距离可知，位置未知'))
            shown_sector = clue.get('fine_sector') or clue['sector']
            # §16.4：听诊器只在凝听时给相邻墙后的入口；只有真实近距
            # 才顺带给距离档，不把远处声音说成近在墙后。
            entry = clue.get('entry')
            near = bool(entry) and bool(clue.get('wall_near'))
            if bearing or near:
                line = tr('{sector} · {band} · {category} · {where} · 第 {turn} 回合',
                          sector=tr(shown_sector), band=tr(clue['band']),
                          category=tr(sound_category_name(clue['category'])),
                          where=where, turn=int(clue.get('time', 0)))
            else:
                line = tr('{sector} · {category} · {where} · 第 {turn} 回合',
                          sector=tr(shown_sector),
                          category=tr(sound_category_name(clue['category'])),
                          where=where, turn=int(clue.get('time', 0)))
            if entry:
                wall_entries += 1
                line += ' · ' + tr('隔墙入口：({x},{y})',
                                   x=int(entry[0]), y=int(entry[1]))
            if clue.get('strength'):
                line += ' · ' + tr('强度：{strength}', strength=tr(clue['strength']))
            if clue.get('multiple'):
                line += ' · ' + tr('多次响动')
            # 一声两种来处（expansion.sound.i06）：转发来的那一声只注明入口；
            # 入口没亲眼见过就只说「经传声筒转发」，不替玩家追另一头。
            relay = clue.get('relay')
            if relay and state.insight_active('一声两种来处'):
                try:
                    rx, ry = int(relay[0]), int(relay[1])
                except (TypeError, ValueError, IndexError):
                    rx = ry = None
                if rx is not None and state.is_visible(rx, ry):
                    line += ' · ' + tr('经传声筒转发，入口：({x},{y})', x=rx, y=ry)
                else:
                    line += ' · ' + tr('经传声筒转发（入口未见）')
            prefix = f'▶ {index + 1}. ' if index == selected else f'{index + 1}. '
            text.append('\n' + prefix + line,
                        style='bold bright_yellow' if index == selected else '#b6cae8')
        text.append('\n' + tr('线索保留 {n} 个真实回合；未知声源不给敌名与精确坐标。',
                             n=retention), style=MUTED)
        if wall_entries:
            text.append('\n' + tr('听诊器只对相邻实墙后的真实声音给入口与近距判断；远墙悬停不生效。'),
                        style=MUTED)
        text.append('\n' + tr('数字键或点击选择线索并在地图高亮；L 凝听一回合（确认后才会等待）。'),
                    style=MUTED)
        if not bearing:
            text.append('\n' + tr('远近档需要「听声辨向」：等待一次后四个回合内显示。'), style=MUTED)
    # 听界与循声定位是显式信息权限：只标发声格与时刻，不显示周围地形。
    from ..data.perception import (CONFIRMED_SOURCE_RETENTION,
                                   LISTEN_REALM_TURNS)
    confirmed = [entry for entry in state.confirmed_sound_sources
                 if state.time - int(entry.get('time', 0)) < CONFIRMED_SOURCE_RETENTION]
    if confirmed:
        text.append('\n\n' + tr('确认声源（循声定位）'), style='bold ' + RANGE_COLOR)
        for entry in confirmed:
            text.append('\n* ({x},{y}) · 第 {turn} 回合确认'.format(
                x=int(entry.get('x', -1)), y=int(entry.get('y', -1)),
                turn=int(entry.get('time', 0))), style='#b6cae8')
    if state.time < getattr(state, 'listen_realm_until', 0):
        markers = [entry for entry in state.precise_sound_markers
                   if state.time - int(entry.get('time', 0)) < LISTEN_REALM_TURNS]
        text.append('\n\n' + tr('听界标记（剩余 {n} 回合）',
                               n=max(0, state.listen_realm_until - state.time)),
                    style='bold ' + RANGE_COLOR)
        for entry in markers[-8:]:
            text.append('\n+ ({x},{y}) · {category} · 第 {turn} 回合'.format(
                x=int(entry.get('x', -1)), y=int(entry.get('y', -1)),
                category=tr(sound_category_name(entry.get('category', ''))),
                turn=int(entry.get('time', 0))), style='#b6cae8')
        text.append('\n' + tr('听界只记录该次声音的发生点，不检测安静目标，也不照亮周围。'),
                    style=MUTED)
    text.append('\n\n' + tr('混乱度'), style='bold ' + CHAOS_COLOR)
    value = clamp_chaos(state.chaos)
    text.append(f'\n{value}/{CHAOS_MAX} · ' + tr(chaos_risk_tier(value)), style=CHAOS_COLOR)
    credit = float(state.chaos_decay_credit) if value else 0.0
    text.append('\n' + tr('平复进度：{n}/{m} · 距降低一点还需 {remaining} 合资格耗时',
                         n=f'{credit:g}', m=f'{CHAOS_DECAY_INTERVAL:g}',
                         remaining=f'{max(0,CHAOS_DECAY_INTERVAL-credit):g}'), style='#a6cbbf')
    text.append('\n' + tr('有效移动、攻击、使用的实付耗时计入平复；等待、免费查看、篡改自身不计入。'), style=MUTED)
    text.append('\n' + tr('连续篡改压力：{n}', n=max(0, min(3, state.tamper_pressure))), style='#f18e9b')
    text.append('\n' + tr('混乱度、连续压力和崩解度分别结算；心理状态也可能影响副作用。'), style=MUTED)
    text.append('\n' + tr('篡改预览只报价，不提前增加实际混乱；这里只显示风险档位。'), style=MUTED)
    # 2026-10-27 玩家反馈「分档惩罚不明确」：逐档写出可能副作用与该档数值。
    # 档位名与范围来自 RISK_TIERS，数值来自 TIER_EFFECTS；不写死、不公开概率，
    # 当前混乱所在档用 ▶ 前缀高亮（中英文一致）。
    text.append('\n\n' + tr('风险分档'), style='bold ' + CHAOS_COLOR)
    text.append('\n' + tr('档位只描述副作用的强度，具体触发概率不公开；混乱越高，同一类副作用的数值越大。'),
                style=MUTED)
    for line, is_current in chaos_tier_lines(value):
        text.append('\n' + ('▶ ' if is_current else '   ') + line,
                    style='bold bright_yellow' if is_current else '#b6cae8')
    text.append('\n' + tr('混乱极高时，篡改可能召来专属混乱异象，它们也可能自行靠近。'),
                style='#f18e9b')
    quote = tamper_quote(app)
    if quote is not None:
        cost, delta, after = quote
        text.append('\n' + tr('当前篡改报价：想象力 {cost} · 混乱 +{delta} → {after}',
                             cost=cost, delta=delta, after=after), style='#ecb487')
        from ..core.tamper_pipeline import risk_note
        text.append('\n' + risk_note(state, after, imagination_cost=cost), style='#f18e9b')
    return text


def clue_line_map(text: Text) -> dict[int, int]:
    """线索行号 → 线索下标；鼠标与数字键共用同一份列表顺序。"""
    first = Text(tr('听觉线索'))
    lines = text.plain.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line == first.plain)
    except StopIteration:
        return {}
    mapping = {}
    for index in range(start + 1, len(lines)):
        match = re.match(r'^(?:▶ )?(\d+)\. ', lines[index])
        if match:
            mapping[index] = int(match.group(1)) - 1
    return mapping


def tamper_quote(app):
    state = app.session.state
    editor = getattr(app, 'world_tamper_editor', None)
    if editor is not None:
        from ..core.tamper_world import word_allowed, word_cost_with_conditions
        if not word_allowed(editor.word_id, editor.slot, editor.sentence):
            return None
        plan = editor.range_plan
        if editor.range_mode == 'vision':
            if plan is None:
                return None
            cost, delta = plan.imagination, plan.chaos_delta
        else:
            cost, delta = word_cost_with_conditions(state, editor.word_id, editor.slot,
                                                    editor.condition_ids)
        return cost, delta, clamp_chaos(state.chaos+delta)
    editor = getattr(app, 'tamper_editor', None)
    if editor is not None and editor.group is not None and editor.transition is not None:
        from ..core.tampering import make_request, preview_tamper
        quote = preview_tamper(state, make_request(state, editor.target, editor.group.text_id,
                                                 editor.transition.transition_id))
        return quote.imagination_cost, quote.chaos_delta, quote.chaos_after
    return None


from .world_renderer import WorldCanvas


class SignalStatusLink(WorldCanvas, can_focus=True):
    def on_mouse_down(self, event):
        event.stop()
        if event.button in (1, 3):
            self.app.toggle_signal_detail()

    def on_key(self, event):
        if event.key in ('enter', 'return', 'space'):
            # 底栏信号链接可聚焦。只有焦点区域已经切到面板时才用 Enter 打开
            # 信号详情；光标仍在 map 时把 Enter 让给行动键（玩家按 Enter 是
            # “行动”，不是“展开脚注”）。鼠标点击不受此限制。
            if getattr(self.app, 'cursor_zone', 'map') == 'panel':
                event.stop()
                event.prevent_default()
                self.app.toggle_signal_detail()


class SignalDetailText(Static):
    """点击线索行只选中并高亮，不移动、不投掷、不推进世界（§16.7）。"""

    def on_resize(self, event):
        # Width may settle one frame after the parent introduces its scrollbar.
        # Reflow the same existing contents; do not change this left pane's UI.
        width = self.content_size.width
        if width != getattr(self, '_settled_width', None):
            self._settled_width = width
            if getattr(self.app, 'signal_detail_open', False):
                self.call_after_refresh(self.app._refresh_signal_status)

    def on_mouse_down(self, event):
        self.app._select_input_region('overlay')
        event.stop()
        if event.button == 1:
            self.app.select_signal_clue_line(int(event.offset.y))


class InspectionPane(Vertical):
    """Screen-level host, positioned inside the left map region even in editors."""
    def on_mouse_down(self, event):
        self.app._select_input_region('overlay')
        event.stop()

    def on_mouse_move(self, event):
        event.stop()

    def on_mouse_scroll_up(self, event):
        event.stop()

    def on_mouse_scroll_down(self, event):
        event.stop()


class InspectionClose(Static):
    def on_mouse_down(self, event):
        event.stop()
        self.app.close_signal_detail()


class SignalListenLink(Static, can_focus=True):
    """鼠标／键盘确认凝听：只执行一次真实等待，不额外推进世界。"""
    def on_mouse_down(self, event):
        event.stop()
        if event.button == 1:
            self.app.confirm_listen()

    def on_key(self, event):
        if event.key in ('enter', 'return', 'space'):
            event.stop()
            event.prevent_default()
            self.app.confirm_listen()


class SignalStatusMixin:
    signal_detail_open = False
    # 左侧面板当前高亮的线索下标（按线索列表从旧到新）；None = 不高亮。
    _signal_clue_index: int | None = None
    _signal_clue_lines: dict[int, int] = {}

    def _inspection_active(self):
        # 层详情面板（2026-10-24 玩家优化 6）与自我察觉同属左侧检视层：
        # 打开期间世界输入一律让位，Esc/点击入口关闭。
        return self.signal_detail_open or self._self_audit_visible() or (
            getattr(self, '_layer_info_visible', None) is not None and self._layer_info_visible())

    def _can_open_inspection(self):
        if getattr(self, 'world_tamper_editor', None) is not None:
            return False
        if getattr(self, 'tamper_editor', None) is not None:
            return False
        return not (self.home_mode or self.session.state.run_over or self._floor_transition is not None
                    or self.qol_confirmation is not None or self.controls_help_open
                    or self.settings_page.capture_target is not None)

    def toggle_signal_detail(self):
        if self.signal_detail_open:
            self.close_signal_detail()
            return
        if not self._can_open_inspection():
            return
        self._signal_kind='signals'
        if self._self_audit_visible():
            self._close_self_audit(refresh=False)
        if getattr(self, '_layer_info_visible', None) and self._layer_info_visible():
            self._close_layer_info(refresh=False)
        self.signal_detail_open = True
        self._select_input_region('overlay')
        state = self.session.state
        self._signal_context = (id(state), state.depth, state.realm_id, state.realm_depth)
        self._signal_focus = self.focused
        self._signal_clue_index = None
        self._clear_held()
        self._refresh_signal_status()
        self.query_one('#signal-detail').display = True
        self.query_one('#signal-detail-scroll').scroll_home(animate=False)
        self.query_one('#signal-detail-scroll').focus()
        getattr(self, '_coach_record_view', lambda: None)()
        self.call_after_refresh(self._refresh_signal_status)

    def toggle_aim_detail(self):
        if self.signal_detail_open:
            self.close_signal_detail()
            return
        pending=getattr(self,'sentence_aim',None) or {}
        target=(pending.get('cursor') or getattr(self,'_aim_free_cursor',None)
                or getattr(self,'_aim_assist_pos',None))
        if target is None:
            state=self.session.state
            dx,dy=self.facing
            target=(state.player.x+dx,state.player.y+dy)
        if not self.session.state.inside_board(*target): return
        self.toggle_signal_detail()
        if self.signal_detail_open:
            self._signal_kind='cell'
            self._signal_cell_target=tuple(target)
            self._refresh_signal_status()

    def _inspection_cell_text(self):
        # Reuse the full layer/knowledge renderer. Its navigation state belongs
        # to the normal detail panel, so save and restore it around this read.
        fields=('cell_detail_target','detail_cursor','detail_scroll','_detail_line_count',
                '_detail_selectable','_detail_targets','_inspection_full_cell')
        missing=object()
        previous={name:getattr(self,name,missing) for name in fields}
        self.cell_detail_target=self._signal_cell_target
        self.detail_cursor=self.detail_scroll=0
        self._inspection_full_cell=True
        try:
            return self._cd_text(self.session.state)
        finally:
            for name,value in previous.items():
                if value is missing:
                    if hasattr(self,name): delattr(self,name)
                else: setattr(self,name,value)

    def close_signal_detail(self):
        self.signal_detail_open = False
        self._signal_clue_index = None
        self.query_one('#signal-detail').display = False
        focus = getattr(self, '_signal_focus', None)
        if focus is not None and focus.is_mounted and focus.display:
            focus.focus()
        else:
            self.set_focus(None)

    def _refresh_signal_status(self):
        # 宽屏档 _refresh_world_view 刚算过同一份预计（供合并状态行用），
        # 这里直接复用；其余路径（凝听、线索选择、详情面板重排）照常现算。
        preview = getattr(self, '_status_noise_preview', None)
        if preview is None or not getattr(self, '_status_noise_preview_fresh', False):
            preview = noise_preview(self)
        self._status_noise_preview_fresh = False
        # 噪音条 = 玩家周围的实时环境噪音（可能来自任何来源），不是下一动作预计；
        # 动作预计仍在详情面板中显示。
        ambient = getattr(self, '_status_ambient_noise', None) or ambient_noise(self)
        terse_mode = _terse.enabled(self.config)
        summary = summary_text(
            ambient, self.session.state.chaos,
            width=max(1, self.query_one('#signal-status').content_size.width or 36),
            terse=terse_mode)
        if not terse_mode and get_language() == 'en':
            # 英文普通模式：右栏长单词缩写（少字模式已只留图标）。
            summary = _terse.compact_english(summary)
        from .static_updates import update_static_if_changed
        update_static_if_changed(self.query_one('#signal-status'), summary)
        region = self.query_one('#map-pane').region
        if self.query_one('#layout').display and region.width:
            self._signal_region = region
        if not self.signal_detail_open:
            return
        state = self.session.state
        if (self.home_mode or state.run_over or
                self._signal_context != (id(state), state.depth, state.realm_id, state.realm_depth)):
            self.close_signal_detail()
            return
        self._fit_inspection_pane(self.query_one('#signal-detail'))
        cell_mode=getattr(self,'_signal_kind','signals')=='cell'
        self.query_one('#signal-detail-title').update(tr('当前对象详情' if cell_mode else '噪音与混乱度'))
        if cell_mode:
            self._signal_clue_lines = {}
            self.query_one('#signal-detail-text').update(self._inspection_cell_text())
        else:
            text = detail_text(self, preview)
            self._signal_clue_lines = clue_line_map(text)
            self.query_one('#signal-detail-text').update(text)
        self.query_one('#signal-listen').update(tr('凝听一回合 · L / 点击'))
        self.query_one('#signal-detail-close').update(tr('返回 · Esc / {key}',
            key=str(self.config.get('key_panel_detail' if cell_mode else 'key_panel_signals')).upper()))

    def _fit_inspection_pane(self, pane):
        region = self.query_one('#map-pane').region
        if region.width > 0 and self.query_one('#layout').display:
            self._signal_region = region
        else:
            region = getattr(self, '_signal_region', region)
        left, top = max(0, region.x), max(1, region.y)
        available = region.width or max(20, int(self.size.width*.62))
        height = min(region.height or self.size.height-3, self.query_one('Footer').region.y-top)
        pane.styles.width = max(12, available-2)
        pane.styles.height = max(4, height-2)
        pane.styles.offset = (left+1, top+1)
        from .region_themes import theme_for_realm
        pane.styles.background = theme_for_realm(self.session.state.realm_id, self.session.state.depth).panel_bg

    def begin_auto_walk(self, path):
        """自动寻路开始时离开凝听选取；设置路径本身不推进世界。"""
        if path and self.signal_detail_open:
            self.close_signal_detail()
        self.path = list(path)

    def select_signal_clue_line(self, line):
        """鼠标点中线索行：与数字键同样只改选中下标，零耗时。"""
        index = self._signal_clue_lines.get(int(line))
        if index is None or not self.signal_detail_open:
            return
        self._signal_clue_index = index
        self._refresh_signal_status()

    def confirm_listen(self):
        """凝听确认：关闭面板后真实等待一回合；打开/查看本身零耗时。"""
        if not self.signal_detail_open:
            return
        self.close_signal_detail()
        self.action_wait_turn()

    def _signal_key(self, key):
        if not self.signal_detail_open:
            return False
        if key in ('escape', 'q'):
            self.close_signal_detail()
        elif key == 'l':
            self._mark_key_handled(key)
            self.confirm_listen()
            return True
        elif key.isdigit() and key in '123456789':
            retention = self.session.state._clue_retention()
            count = sum(1 for clue in self.session.state.heard_sound_clues
                        if self.session.state.time - int(clue.get('time', 0)) < retention)
            index = int(key) - 1
            self._signal_clue_index = index if index < count else None
            self._refresh_signal_status()
        else:
            scroll = self.query_one('#signal-detail-scroll')
            if key in ('up', 'w'): scroll.scroll_relative(y=-1, animate=False)
            elif key in ('down', 's'): scroll.scroll_relative(y=1, animate=False)
            elif key == 'pageup': scroll.scroll_page_up(animate=False)
            elif key == 'pagedown': scroll.scroll_page_down(animate=False)
            elif key == 'home': scroll.scroll_home(animate=False)
            elif key == 'end': scroll.scroll_end(animate=False)
        self._mark_key_handled(key)
        return True
