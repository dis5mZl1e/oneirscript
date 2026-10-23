"""Panel-only semantic colors; independent of map palettes and object identity."""
from __future__ import annotations
import colorsys
from functools import lru_cache
from rich.color import Color
from rich.console import Console
from rich.text import Text
from ..i18n import tr

FIELD_COLORS = {
    'text': '#ffffff', 'label': '#bcc5d6', 'muted': '#aab0c2', 'heading': '#d9e7f5',
    'count': '#cfd6e6', 'position': '#b6cae8', 'height': '#d9c2a3',
    'time': '#b8a9e8', 'cooldown': '#97b9e8', 'windup': '#f2bd84',
    'duration': '#a6cbbf', 'range': '#82d9d0', 'area': '#adcdf4',
    'effect': '#9dce97', 'cost': '#ecb487', 'risk': '#f18e9b',
    'danger': '#ff8075', 'condition': '#70cbbb', 'noise': '#c1e889',
    'chaos': '#eaa6ff', 'dissolution': '#e4be91', 'integrity': '#ff9187',
    'hardness': '#d4b8a2', 'thickness': '#b5c9d3', 'volume': '#9acbe0',
    'concentration': '#d1b2ec', 'flow': '#a9d7cb', 'accumulation': '#d7be92',
    'damage': '#ff8c42', 'word': '#c7a6ed', 'degree': '#e6c46a',
    'grammar': '#9fdaca', 'portent': '#c9a0ff', 'insight': '#58e67b',
    'memory': '#b18cff', 'mind': '#ffd166', 'lucidity': '#7cc7ff',
    'imagination': '#58e67b', 'identity': '#e5c780',
    # 第十九节 §2／§3／§5：面板上必须显式 RGB 的标记色与关系·类别色。
    'theme': '#ff8ad8', 'category': '#8ab4f8', 'puppet': '#d9a0ff',
    # 三资源条的中／低档（面板专用变体，不写回地图与资源定义）。
    'mind_mid': '#e8ab3c', 'mind_low': '#d89a45',
    'lucidity_mid': '#5aa4e8', 'lucidity_low': '#66aceb',
    'imagination_mid': '#46c266', 'imagination_low': '#51b96b',
    # 进度条空轨：故意低对比，第十九节 §10.4 明确豁免文字口径。
    'track': '#5f5f5f',
    # 第十九节 §6：联想盘盘外六字段，沿用既有独立色，只搬进同一张注册表。
    'held': '#ffb5ad', 'tool': '#b4e08c', 'board_cursor': '#e69acf',
    'rotation': '#d6c693', 'board_effects': '#91b9ff',
}

STAT_FIELDS = {
    'mind.max': 'mind', 'lucidity.max': 'lucidity', 'imagination.max': 'imagination',
    'imagination.regen_credit': 'duration', 'action.speed_scale': 'time',
    'move.base_time': 'time', 'move.effective_time': 'time',
    'move.delay_penalty': 'cost', 'attack.delay_penalty': 'cost',
    'throw.range': 'range', 'resilience': 'grammar', 'sight.radius': 'range',
    'dissolution.bonus': 'dissolution', 'loot.luck': 'degree',
    'imagination.regen_rate': 'duration', 'melee.base_trauma': 'damage',
    'melee.base_time': 'time', 'melee.effective_time': 'time',
    'portent.accumulation_factor': 'accumulation', 'portent.effective_duration': 'duration',
    'environment.trauma': 'damage', 'identity.trauma_multiplier': 'risk',
    'mind.loss_multiplier': 'mind', 'mind.loss_blocked': 'grammar',
    'lucidity.tier': 'duration', 'mind.tier': 'duration',
    'ability.cost_multiplier': 'cost', 'ability.cooldown_turns': 'cooldown',
    'tamper.pressure': 'risk', 'tamper.chaos_cost': 'cost', 'buffer.available': 'grammar',
    'physics.explosion_bonus': 'damage', 'physics.fire_spread_bonus': 'damage',
    'physics.penetration_bonus': 'range', 'physics.solidity_penalty': 'risk',
}
STAT_COLORS = {key: FIELD_COLORS[field] for key, field in STAT_FIELDS.items()}
LABEL_FIELDS = {
    '位置': 'position', '悬停': 'position', '观察': 'position', '地势': 'height',
    '高度': 'height', '地板': 'height', '表面': 'duration', '高处': 'area', '空中': 'concentration',
    '耐久': 'integrity', '完整度': 'integrity', '伤害': 'damage', '创伤': 'word',
    '攻速': 'time', '移动': 'time', '视野': 'range', '硬度': 'hardness', '厚度': 'thickness',
    '液体': 'volume', '气体': 'concentration', '冷却': 'cooldown', '蓄势': 'windup',
    '持续': 'duration', '恢复': 'cooldown', '距离': 'range', '效果': 'effect',
    '条件': 'condition', '报酬': 'effect', '地点': 'position', '委托人': 'identity',
    # 第十九节 §3／§4／§5／§8：方案点名但先前只能回退成冷灰标签的字段。
    '噪音': 'noise', '混乱度': 'chaos', '崩解度': 'dissolution',
    '射程': 'range', '视距': 'range', '声径': 'range', '听觉': 'range',
    '层数': 'count', '次数': 'count', '容量': 'count', '基础值': 'count',
    '费用': 'cost', '范围': 'area', '面积': 'area', '半径': 'area', '目标数': 'area',
}

def luminance(color):
    rgb = Color.parse(color).get_truecolor()
    def channel(v):
        v /= 255
        return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
    return sum(w*channel(v) for w, v in zip((.2126, .7152, .0722), rgb))

def contrast_ratio(a, b):
    dark, light = sorted((luminance(a), luminance(b)))
    return (light+.05)/(dark+.05)

@lru_cache(maxsize=512)
def panel_color(color, background='#2d3739'):
    """Lift only the panel copy, retaining hue; never mutate material/map data."""
    rgb = Color.parse(color or '#ffffff').get_truecolor()
    exact = '#%02x%02x%02x' % tuple(rgb)
    if contrast_ratio(exact, background) >= 4.5:
        return exact
    hue, light, saturation = colorsys.rgb_to_hls(*(v/255 for v in rgb))
    while light < 1:
        light = min(1, light+.02)
        candidate = '#%02x%02x%02x' % tuple(round(v*255) for v in colorsys.hls_to_rgb(hue, light, saturation))
        if contrast_ratio(candidate, background) >= 4.5:
            return candidate
    return '#ffffff'

def field_text(label, value='', *, field='label', separator=' ', unit=''):
    text = Text(tr(label), style=FIELD_COLORS[field])
    if value != '':
        text.append(separator+str(value), style=FIELD_COLORS[field])
    if unit:
        text.append(' '+tr(unit), style=FIELD_COLORS[field])
    return text

def rich_lines(text, width, *, continuation=''):
    """Wrap Text directly; preserve semantic spans and physical-row hit maps."""
    console = Console(width=max(1, width), legacy_windows=False)
    lines = text.wrap(console, max(1, width-len(continuation)), overflow='fold', no_wrap=False)
    return [line if i == 0 or not continuation else Text(continuation)+line
            for i, line in enumerate(lines)]

def stat_color(key, state=None):
    if key in ('mind.tier', 'lucidity.tier') and state is not None:
        tier = state.mind_tier if key == 'mind.tier' else state.lucidity_tier
        return FIELD_COLORS['danger' if tier >= 3 else 'windup' if tier else 'duration']
    return STAT_COLORS.get(key, FIELD_COLORS['text'])
