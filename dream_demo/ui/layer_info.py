"""当前层信息（2026-10-24 玩家优化 6）：状态行层标签 + 左侧层详情面板。

- **代号**：给每种层型与楼层修饰符一个 Unicode 字符代号——中文状态行放得下
  完整词，英文词太长（"Residential District·Antique·…"），状态行只放代号，
  完整名称与含义在点击顶部层信息行打开的左侧面板里给出。
- **入口**：右侧状态区的第 1 行（层信息行）可点击，与下方三行属性条
  （个人信息页入口，ClickableStatus → 自我察觉）行为分离。
- 面板只读：Esc / 再点一次入口关闭；WASD 和滚轮滚动正文。
"""
from __future__ import annotations

from rich.console import Console
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..i18n import get_language, tr
from ..mapgen import region_for_depth
from ..mapgen.layout import normalize_map_form
from .panel_fields import FIELD_COLORS

PANEL_MUTED = FIELD_COLORS['muted']

# ---- Unicode 代号（从既有字形库的安全区选取：几何/制表/杂项符号，无 emoji 表现）----
LAYER_FORM_GLYPHS = {
    "整齐的房间": "▤",
    "破碎的房间": "▨",
    "居民区": "⌂",
    "洞穴": "◍",
    "迷宫": "⌗",
    "长廊": "≡",
    "无限房间": "∞",
    "碎影平原": "⁂",
    "回声大厅": "○",
    "梦的起始": "✦",
    "深层边界": "⧗",
}
LAYER_MODIFIER_GLYPHS = {
    "大型": "▲",
    "小型": "△",
    "气密": "◌",
    "潮湿": "∿",
    "繁茂": "❀",
    "古朴": "⚱",
    "精致": "◈",
}

# ---- 含义（中文原文；英文走 i18n 表）----
LAYER_FORM_MEANING = {
    "整齐的房间": "房间被递归二分成规整的网格，墙体平直、通路端正。",
    "破碎的房间": "房间的底子上墙缘被啃噬，碎屑与噪点撒满全层。",
    "居民区": "从一间房向外成片生长的街区，房间彼此贴靠。",
    "洞穴": "天然洞窟，通路由平滑的洞腔连成。",
    "迷宫": "窄道蜿蜒的回溯迷宫，几乎每条路都通向别处。",
    "长廊": "一条极长的走廊层，长边约为短边的四倍。",
    "无限房间": "重复的房间模块与环形通路，容易迷路。",
    "碎影平原": "开阔地面上散布着短墙与墙块，视野开阔而掩体稀少。",
    "回声大厅": "中央大厅配柱列与边室。",
    "梦的起始": "一切开始的地方：没有崩解度，随时可以下潜。",
    "深层边界": "梦的尽头：崩解度在暗中累计，只显示回合数。",
}
LAYER_MODIFIER_MEANING = {
    "大型": "本层每条边放大约四分之一，地面更辽阔。",
    "小型": "本层每条边缩短约五分之一，遭遇更密集。",
    "气密": "气体的生成率与存留时间大增，留意吸入效果。",
    "潮湿": "液体生成率大增，低洼处容易积水。",
    "繁茂": "植物覆盖率大增。",
    "古朴": "埋藏的建筑模板更多，稀有模板更常见。",
    "精致": "特殊与稀有地板的覆盖率大幅提升。",
}

_CONSOLE = Console(legacy_windows=False)


def _separator() -> str:
    # 标签分隔：英文用半角冒号，中文保留全角（界面语感一致；语言运行时可切）。
    return ': ' if get_language() == 'en' else '：'


def _form_glyph(form: str) -> str:
    return LAYER_FORM_GLYPHS.get(form, form[:1] or "·")


def _modifier_glyph(modifier: str) -> str:
    return LAYER_MODIFIER_GLYPHS.get(modifier, modifier[:1] or "·")


def status_layer_label(state) -> str:
    """状态行第 1 行的层标签（区域+深度前缀之外的右半段）。

    顺序固定为「层型 修饰符 层名」；中文放完整词（层型·修饰符·层名），
    英文层型/修饰符换成 Unicode 代号（代号+层名），完整词在层详情面板。
    """
    form = normalize_map_form(state.map_form)
    modifier = state.layer_modifier or ''
    theme = tr(state.theme)
    if get_language() == 'en':
        codes = _form_glyph(form)
        if modifier:
            codes += _modifier_glyph(modifier)
        return f"{codes} {theme}"
    label = tr(form)
    if modifier:
        label += '·' + tr(modifier)
    return label + '·' + theme


def layer_info_text(state, width: int) -> Text:
    """左侧层详情面板的正文（只读，含代号图例与含义）。"""
    width = max(16, width)
    form = normalize_map_form(state.map_form)
    modifier = state.layer_modifier or ''
    lines: list[Text] = []

    def add(text: Text) -> None:
        lines.extend(text.wrap(_CONSOLE, width, overflow='fold'))

    add(Text(tr("当前层"), style="bold bright_white"))
    if state.realm_id:
        from ..data.dreams import realm_def
        realm = realm_def(state.realm_id)
        realm_name = tr(realm.name) if realm is not None else state.realm_id
        add(Text(f"{realm_name} · " + tr("第 {n} 层", n=state.realm_depth), style=PANEL_MUTED))
    else:
        region = region_for_depth(state.depth)
        add(Text(f"{tr(region)} · " + tr("第 {n} 层", n=state.depth), style=PANEL_MUTED))
    add(Text(tr("层名") + _separator() + tr(state.theme), style=FIELD_COLORS['identity']))
    form_line = Text(tr("层型") + _separator() + _form_glyph(form) + ' ' + tr(form), style=FIELD_COLORS['heading'])
    add(form_line)
    add(Text('  ' + tr(LAYER_FORM_MEANING.get(form, '')), style=PANEL_MUTED))
    if modifier:
        modifier_line = Text(
            tr("修饰符") + _separator() + _modifier_glyph(modifier) + ' ' + tr(modifier),
            style=FIELD_COLORS['condition'],
        )
        add(modifier_line)
        add(Text('  ' + tr(LAYER_MODIFIER_MEANING.get(modifier, '')), style=PANEL_MUTED))
    else:
        add(Text(tr("修饰符：无——常规层，只有层型本身起作用。"), style=PANEL_MUTED))
    add(Text(''))
    add(Text(tr('地图尺寸') + _separator() + f'{state.width} × {state.height}', style=FIELD_COLORS['count']))
    explored = sum(state.cell_knowledge(x, y).explored
                   for y in range(state.height) for x in range(state.width))
    total = state.width * state.height
    add(Text(tr('探索进度') + _separator() + f'{explored}/{total} ({explored / max(1, total):.1%})', style=FIELD_COLORS['count']))
    add(Text(tr('回合') + _separator() + str(state.time) + ' · ' + tr('本层停留') + _separator() + str(state.turns_since_descend), style=FIELD_COLORS['count']))
    if state.depth != 30 and not state.realm_id:
        add(Text(tr('崩解度') + _separator() + str(state.dissolution), style=FIELD_COLORS['condition']))
    visible_entities = [e for e in state.enemies if e.integrity > 0 and state.is_visible(e.x, e.y)]
    add(Text(tr('视野内') + _separator() + tr('异象') + f' {sum(e.relation == "失控意识" for e in visible_entities)} · ' + tr('稳定意识') + f' {sum(e.relation == "稳定意识" for e in visible_entities)}', style=PANEL_MUTED))
    add(Text(tr("WASD / 滚轮 滚动 · Esc / 点击顶部层信息行 关闭。"), style=PANEL_MUTED))
    return Text('\n').join(lines)


class LayerInfoPane(VerticalScroll):
    """左侧层详情面板本体：只读正文，点击面板不穿透到地图。"""

    DEFAULT_CSS = """
    LayerInfoPane { display: none; }
    """

    def on_mouse_down(self, event) -> None:
        self.app._select_input_region('overlay')
        event.stop()


class LayerInfoMixin:
    """层详情面板的路由与渲染（挂在 DreamApp 上）。"""

    def _layer_info_visible(self) -> bool:
        try:
            return bool(self.query_one("#layer-info-pane").display)
        except Exception:
            return False

    def _close_layer_info(self, *, refresh: bool = True) -> None:
        try:
            self.query_one("#layer-info-pane").display = False
        except Exception:
            return
        if refresh:
            self.refresh_view()

    def _toggle_layer_info(self) -> None:
        if self._layer_info_visible():
            self._close_layer_info()
            return
        if not self._can_open_inspection():
            return
        if self._self_audit_visible():
            self._close_self_audit(refresh=False)
        if self.signal_detail_open:
            self.close_signal_detail()
        state = self.session.state
        self._layer_info_context = (id(state), state.depth, state.realm_id, state.realm_depth)
        self._layer_info_focus = self.focused
        self._clear_held()
        pane = self.query_one("#layer-info-pane")
        pane.display = True
        self._select_input_region('overlay')
        pane.scroll_home(animate=False)
        self.refresh_view()

    def _refresh_layer_info(self, state) -> None:
        try:
            pane = self.query_one("#layer-info-pane")
            body = pane.query_one("#layer-info-body", Static)
        except Exception:
            return
        if not pane.display:
            return
        if (self.home_mode or state.run_over or getattr(self, '_layer_info_context', None) !=
                (id(state), state.depth, state.realm_id, state.realm_depth)):
            self._close_layer_info(refresh=False)
            return
        try:
            self._fit_inspection_pane(pane)
            pane.styles.width = max(12, int(pane.styles.width.value * .82))
            pane.styles.height = max(4, int(pane.styles.height.value * .78))
        except Exception:
            pass
        try:
            width = max(16, body.content_size.width or 56)
            body.update(layer_info_text(state, width))
        except Exception:
            body.update(Text(tr("层信息读取失败。"), style=PANEL_MUTED))

    def _scroll_layer_info(self, event, direction: int) -> bool:
        """鼠标在面板区域内时，滚轮只滚面板正文；返回 True 表示已消费。"""
        try:
            pane = self.query_one("#layer-info-pane")
        except Exception:
            return False
        if not pane.display:
            return False
        region = pane.region
        sx = getattr(event, "screen_x", None)
        sy = getattr(event, "screen_y", None)
        if sx is None or sy is None or not region.contains(sx, sy):
            return False
        pane.scroll_relative(y=direction * 3, animate=False)
        try:
            event.stop()
        except Exception:
            pass
        return True
