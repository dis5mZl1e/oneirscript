"""右侧面板与悬停区的文本构建：行囊/征兆/洞察/观测/操作/事件记录。"""





from __future__ import annotations





import math


import re


from typing import Any





from rich.cells import cell_len


from rich.text import Text
from ..data.semantic_icons import icon_label


from rich.style import Style


from rich.console import Console





_WRAP_CONSOLE = Console(legacy_windows=False)





# 携带意象页底部记忆碎片独立滚动区的碎片行视窗高度（不含 header 行）。


# 键盘/滚轮滚动与渲染共用这一个数（input.py 也 import 它）。


MEMORY_FOOTER_ITEM_ROWS = 3








def _dialogue_window(count: int, budget: int, scroll: int) -> tuple[int, int, bool, bool]:


    """Keep scroll indicators inside the same budget as the prose."""


    if budget <= 0:


        return 0, 0, False, False


    if count <= budget:


        return 0, count, False, False


    # At either end only one indicator is needed. Even a one-row window


    # must expose prose, rather than becoming an unscrollable arrow.


    if budget <= 2:


        offset = min(max(0, scroll), count - 1)


        return offset, 1, budget == 2 and offset == count - 1, budget == 2 and offset < count - 1


    offset = min(max(0, scroll), count - (budget - 1))


    visible = budget - int(offset > 0)


    show_down = offset + visible < count


    visible -= int(show_down)


    return offset, visible, offset > 0, show_down





from ..core import (


    ABILITY_DEFINITIONS,


    ANOMALY_DEFINITIONS,


    EQUIPMENT_SLOTS,


    EVENT_DEFINITIONS,


    GameState,


    INSIGHT_DEFINITIONS,


    ITEM_DEFINITIONS,


    MEMORY_FRAGMENT_EFFECTS,


    MEMORY_LIMIT,


    Material,


)


from ..audio import sfx


from ..i18n import get_language, tr


from ..data.anomaly_skills import skill_summaries_for
from ..core.main_difficulty import current_anomaly_definition, current_skill_summaries


from ..equipment.reading import scan


from ..equipment.board import Placement


from ..core.firing_sources import LEGACY_BASIC_ID, LEGACY_BASIC_NAME


from ..core.constants import SIGHT_OBSCURE_MIN


from ..materials import (


    CONTAINER_KINDS,


    PORTENT_DEFINITIONS,


    SOLID_KINDS,


    TABLE_KINDS,


    gas_def,


    liquid_def,


    material_description,


    material_portents,


    material_trigger_amount,


    plant_def_for,
    plant_spent,


    wall_def,


)


from ..symbols import drop_glyph, symbol


from . import glyphs, terse


from .panel_fields import FIELD_COLORS as FC, LABEL_FIELDS, field_text, panel_color, rich_lines


from .styles import (


    AGGREGATE_PANEL_STYLES,


    ALERT_STYLES,


    BAR_TRACK,


    CARRIED_IMAGE_STYLE,


    CATEGORY_STYLES,


    INSIGHT_STYLE,


    OBSERVATION_ATTR_COLORS,


    OBSERVATION_KIND_COLOR,


    PANEL_DANGER,


    PANEL_MAGENTA,


    PANEL_MUTED,


    PORTENT_HINT_STYLE,


    PORTENT_STYLE,


    RELATION_PANEL_STYLES as RELATION_STYLES,


    TRAUMA_STYLES,


    item_name_color,


)



# ---- 纸感分区排版原语（2026-10-24 批次，色板与口径见 paper_zones.py）----
# 右栏内部按「桌上的纸」分区：正文区底色由 CSS 铺（ZONE_BODY），纸上的
# 通栏条（分组标题/滚动提示）用这里的原语以 span 底色 + pad 满行宽实现。
from .paper_zones import (
    SCROLL_HINT_STYLE,
    SPLIT_DIVIDER_STYLE,
    ZONE_CAST_LIST,
    ZONE_CAST_PREVIEW,
    ZONE_STRIP,
)


def paper_pad(line: Text, zone_bg: str, width: int) -> Text:
    """把折行/截断后的**物理行**铺满整行宽的分区底色。

    末尾用空格补到 ``width`` 列并整行叠上 ``zone_bg`` 底——只在尾部加
    空格：行数不变、既有列的起点不变，``_panel_rows``/``_panel_row_keys``
    的行命中映射在 pad 之后登记照旧成立（底色 span 不携带语义）。
    """
    padded = Text(line.plain, style=line.style)
    padded.spans = list(line.spans)
    fill = width - cell_len(padded.plain)
    if fill > 0:
        padded.append(' ' * fill)
    padded.stylize_before(f'on {zone_bg}', 0, len(padded.plain))
    return padded


def two_zone_row(left: Text, right: Text, left_bg: str, right_bg: str,
                 left_w: int, right_w: int) -> Text:
    """左右分块的单个物理行（2026-10-24 深化：环境页左右分区）。

    左半行截到 ``left_w`` 列铺 ``left_bg``，中间一列细竖线（track 灰的
    「缝」，不是要读的字），右半行截到 ``right_w`` 列铺 ``right_bg``——
    合计正好整行宽。折行由调用方先做（各自列宽内 fold），本函数只组装。
    通栏行（键位行等）不走这里：竖线在通栏行截止。
    """
    def half(line: Text, limit: int, bg: str) -> Text:
        out = Text(line.plain, style=line.style)
        out.spans = list(line.spans)
        if cell_len(out.plain) > limit:
            out.truncate(limit, overflow='ellipsis')
        return paper_pad(out, bg, limit)

    row = half(left, left_w, left_bg)
    row.append(Text('│', style=SPLIT_DIVIDER_STYLE))
    row.append_text(half(right, right_w, right_bg))
    return row


def zone_strip(title: str, width: int, *, color: str = '') -> Text:
    """整行铺 ZONE_STRIP 底的通栏分组标题条（正文分组标题用）。

    ``title`` 是 tr() 之后的成品文案（沿用原「—— 标题 ——」键，不动 i18n）；
    ``color`` 传该分组原本的语义色（word/identity/condition…），它们对牛皮
    条底全部 ≥4.5（tests/test_paper_zones.py 验收），缺省用标题色。返回
    单个物理行（cell_len == width，超宽标题先截断再补底），调用方照常走
    add() 登记行映射（-1 装饰行）。
    """
    ink = color or FC['heading']
    line = Text(title)
    line.stylize(f'bold {ink}')
    line.stylize('underline')
    if cell_len(line.plain) > width:
        line.truncate(width, overflow='ellipsis')
    return paper_pad(line, ZONE_STRIP, width)


def kv_grid(pairs, width: int, *, two_from: int = 44) -> list[Text]:
    """键值对网格排版（2026-10-24 批次 D：详情页两列化）。

    - ``width`` ≥ ``two_from``（默认 44 列）时两列、列宽对半，**中间一条
      细竖线**分隔（2026-10-24 玩家优化 5）；否则单列逐行。
    - 每项是 ``(label, value, color)``，第 4 元为 True 表示选中态
      （▶ 前缀 + 加粗下划线，只作用于自己那一格，不淹没同格另一项）。
    - 超宽**折行**不截断（2026-10-24 玩家优化 5）：一格放不下的字换行
      续排，不再省略号丢字；左右格行数不齐时短的一侧补空行对齐，
      行映射登记由调用方按「选中项优先、否则左格」逐行落行。

    返回 Text 行列表，每行 cell_len ≤ width；两列时第 i 对在第 i//2 行。
    """
    col = width if width < two_from else max(1, width // 2)

    def cell_lines(pair, span: int) -> list[Text]:
        selected = len(pair) > 3 and bool(pair[3])
        line = Text(('▶ ' if selected else '') + pair[0] + '  ' + pair[1],
                    style=pair[2] + (' bold underline' if selected else ''))
        if cell_len(line.plain) <= span:
            return [line]
        return list(line.wrap(_WRAP_CONSOLE, max(1, span), overflow='fold'))

    if width < two_from:
        return [row for pair in pairs for row in cell_lines(pair, col)]
    # 两列：中缝一条细竖线（muted 色，视觉上「非常细」），两侧各留一列空隙。
    left_span = max(1, width // 2 - 2)
    right_span = max(1, width - left_span - 2)
    divider_style = PANEL_MUTED
    rows: list[Text] = []
    for index in range(0, len(pairs), 2):
        left = cell_lines(pairs[index], left_span)
        right = cell_lines(pairs[index + 1], right_span) if index + 1 < len(pairs) else []
        for line_no in range(max(len(left), len(right), 1)):
            left_line = left[line_no] if line_no < len(left) else None
            right_line = right[line_no] if line_no < len(right) else None
            row = Text()
            row.append_text(left_line if left_line is not None else Text())
            row.append(' ' * max(1, left_span - cell_len(left_line.plain if left_line is not None else '')))
            row.append('│', style=divider_style)
            if right_line is not None:
                row.append(' ' * max(1, right_span - cell_len(right_line.plain)))
                row.append_text(right_line)
            rows.append(row)
    return rows





# 同名异象在详情面板里用圈码区分（超出 20 个回退为 #n）——视觉上比纯数字轻。


_CIRCLED_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"





# 对话面板的行映射（_dialog_rows）取值：>= 0 = 选项序号，-1 = 装饰行，


# -2 = 篡改入口提示行（规格 §4.1，点击等价于按篡改键，见 ui.tampering）。


TAMPER_ENTRY_ROW = -2








def _material_token(name, color, amount=None, *, field='volume', icon=''):


    text = Text(icon + tr(name), style=panel_color(color))


    if amount is not None:


        text.append(' '+str(amount), style=FC[field])


    return text








def _labeled(label, value):


    text = Text(tr(label) + ':', style=FC[LABEL_FIELDS.get(label, 'label')])


    text.append_text(value if isinstance(value, Text) else Text(str(value), style=FC['text']))


    return text





# panel_scroll 的语义分成两派：


# - 「首行偏移」派（下列这些）：panel_scroll 是内容区的起始行号，上滚（amount=+1）


#   应当减小它。行囊/携带意象/洞察/征兆/观测都属于这一派。


# - 「回看行数」派（事件记录等）：panel_scroll 是从最新消息向上回看的行数，


#   上滚应当增加它。


SCROLL_TOP_OFFSET_MODES = frozenset(


    {"inventory", "equipment", "insights", "portents", "catalog", "tasks", "actions", "world_tamper"}


)








def _item_description(item, state=None) -> str:


    from ..equipment.sentence_prose import item_description


    description = item_description(item.definition_id, item.description)
    if state is not None:
        from ..core.drug_debts import quote
        debt = quote(state, item)
        if debt:
            description += ' ' + debt
    return description








def _item_sound_lines(state, item) -> list[str]:


    """真实发声物品的「发声点/半径」说明；不发声物品返回空列表。





    口径见 core.sound_preview：汽笛在玩家格可以给出经环境修正的**实际**半径；


    蜂鸣诱饵与带 ``fire.pulse`` 的装备的发声点在落点/命中格，详情只写基础


    半径并注明实际值按落点修正——不把基础值冒充最终值，也不给不发声物品


    添加假提示。


    """


    from ..core import sound_preview





    lines: list[str] = []


    for preview in sound_preview.item_sound_previews(state, item):


        if preview.get("silent"):


            continue


        origin_kind = preview.get("origin_kind")


        if origin_kind == "player":


            lines.append(tr("发声点：你所在格 · 声响半径 {n}", n=preview["radius"]))


        elif origin_kind == "landing":


            lines.append(tr("发声点：落点 · 基础半径 {n}（按落点环境修正）", n=preview["base"]))


        else:


            lines.append(tr("发声点：命中处 · 基础半径 {n}（按命中格环境修正）", n=preview["base"]))


        for source in preview.get("sources") or ():


            lines.append(tr("↳ {source}", source=source))


    return lines








def _react_summaries(state) -> list[Text]:


    """盘面下方的逐句状态行：所有成句（含维持/反应）都列出。





    句子部分按生成器片段三色着色（生效实词蓝/手放虚词白/衔接词灰），


    尾部的状态与冷却仍用次要灰。


    """


    from ..equipment.board import PIECE_SPECS


    from ..equipment.events import cooldown_remaining


    from ..equipment.links import endpoint_label


    from ..equipment.sentence_prose import fragments_to_text





    out: list[Text] = []


    for sentence in state.equipment.compiled().sentences:


        path = sentence.path


        line = (fragments_to_text(sentence.fragments) if sentence.fragments


                else Text(sentence.text))


        if path is not None and path.terminal_piece:


            spec = PIECE_SPECS[path.terminal_piece]


            remaining = cooldown_remaining(state, path.terminal_piece)


            tail = tr('还需 {n} 回合', n=remaining) if remaining else tr("就绪")


            if sentence.reason:


                tail = sentence.reason


        elif sentence.reason:


            tail = sentence.reason


        else:


            tail = tr(sentence.status)


        line.append(' · ' + tail, style=PANEL_MUTED)


        out.append(line)


    if not out:


        out.append(Text(tr('盘面还空着：把行囊里的携带意象摆上来就能成句。'), style=PANEL_MUTED))


    return out[:6]








def _attribute_lines(


    attributes: tuple[tuple[str, Any], ...], limit: int, indent: str = "    "


) -> list[Text]:


    """把 (标签, 值) 序列排成「一行放得下就并排、放不下就换行」的属性行。





    每个属性一个专属颜色；分隔符算窄灰色，斜体仍留给数值本身。


    观测面板与观测详情面板共用同一套排版，保证两处观感一致。


    """


    rendered: list[Text] = []


    current = Text(indent)


    used = cell_len(indent)


    first = True


    for label, value in attributes:


        style = OBSERVATION_ATTR_COLORS.get(label, PANEL_MUTED)


        piece = f"{tr(label)} {value}"


        separator = "" if first else " · "


        if not first and used + cell_len(separator) + cell_len(piece) > limit:


            rendered.append(current)


            current = Text(indent)


            used = cell_len(indent)


            first = True


            separator = ""


        if separator:


            current.append(separator, style=PANEL_MUTED)


        current.append(piece, style=style)


        used += cell_len(separator) + cell_len(piece)


        first = False


    rendered.append(current)


    return rendered








def _skill_summary_text(summary: dict[str, Any]) -> str:


    """主动技能观测摘要 → 一行数值：「技能 名：创伤 渠道 值 · 冷却 N 回合 · 蓄势 N …」。





    观测展开注释、观测详情与格子详情共用；创伤渠道为「无」时不带数值


    （创伤 无）。效果/条件两段文本由 _skill_detail_lines 另起缩进行。


    蓄势/持续/恢复/距离为 0 的参数不写（免得全技能都拖一串 0）。


    渠道/技能名走 tr——EN 词键见 i18n_ui_en（心智→mind、清醒→lucidity）。


    """


    if summary.get("trauma_channel") == "无":


        trauma = tr("创伤 无")


    else:


        trauma = tr("创伤 {channel} {value}").format(


            channel=tr(summary.get("trauma_channel", "")),


            value=summary.get("trauma_value", 0),


        )


    parts = [trauma, tr("冷却 {n} 回合").format(n=summary.get("cooldown_rounds", 0))]


    if summary.get("windup_rounds"):


        parts.append(tr("蓄势 {n}").format(n=int(summary["windup_rounds"])))


    if summary.get("duration_rounds"):


        parts.append(tr("持续 {n} 回合").format(n=int(summary["duration_rounds"])))


    if summary.get("recovery_rounds"):


        parts.append(tr("恢复 {n} 回合").format(n=int(summary["recovery_rounds"])))


    if summary.get("max_range"):


        parts.append(tr("距离 {n}").format(n=int(summary["max_range"])))


    colon = ': ' if get_language().startswith('en') else '：'
    return f"{tr('技能 ')}{tr(summary.get('name', ''))}{colon}{' · '.join(parts)}"








def _skill_summary_rich(summary):


    colon = ': ' if get_language().startswith('en') else '：'
    text = Text(tr('技能 ') + tr(summary.get('name', '')) + colon, style=FC['word'])


    channel = summary.get('trauma_channel', '')


    trauma = tr('创伤 无') if channel == '无' else tr('创伤 {channel} {value}',


        channel=tr(channel), value=summary.get('trauma_value', 0))


    text.append(trauma, style=FC['damage'])


    fields = [('冷却 {n} 回合', summary.get('cooldown_rounds', 0), 'cooldown')]


    fields.extend((label, int(summary[key]), field) for key, label, field in (


        ('windup_rounds', '蓄势 {n}', 'windup'), ('duration_rounds', '持续 {n} 回合', 'duration'),


        ('recovery_rounds', '恢复 {n} 回合', 'cooldown'), ('max_range', '距离 {n}', 'range'))


        if summary.get(key))


    for label, value, field in fields:


        text.append(' · ', style=FC['label'])


        text.append(tr(label, n=value), style=FC[field])


    return text











class PanelViewMixin:


    def _symbol_mode(self) -> str:


        """当前生效的符号档位（地图 / 面板 / 悬停共用同一条口径）。





        `themed` 档位在不支持 Unicode 的输出流上降级为 `ascii`——面板里画掉落物


        图标（📚/📜 一类）与地图必须走同一把尺子，否则会出现「地图降级了、面板


        没降级」的错位。挂在 Mixin 上而不是 DreamApp：只实例化面板做单元测试的


        桩对象（没有 config、没有 app）也能拿到合理默认值。


        """


        configured = "themed"


        config = getattr(self, "config", None)


        if config is not None:


            configured = str(config.get("symbol_mode"))


        if configured != "themed":


            return configured


        return "themed" if glyphs._unicode_mode(None) else "ascii"


    # ---- 少字模式（terse mode）右栏/悬停专用渲染原语 -------------------------
    # 只压缩右侧栏与悬停读数；左侧事件记录、全屏窗口仍走普通口径。

    def _terse_active(self) -> bool:
        """少字模式是否生效（读玩家设置 terse_mode）。"""
        return terse.enabled(getattr(self, "config", None))

    def _terse_details_collapsed(self) -> bool:
        """少字模式且玩家尚未手动按 \\ 展开时，可展开注释默认收起。"""
        return self._terse_active() and not getattr(self, "_terse_details_manual", False)

    def _details_visible(self) -> bool:
        """注释当前是否显示：普通模式看全局开关，少字模式再看手动展开位。"""
        return bool(self.details_expanded) and not self._terse_details_collapsed()

    def _terse_floor_glyph(self, aggregate_variant, floor):
        """少字地板图标：聚合物统一地板点（保留变体配色），其它地板用定义符号。"""
        from ..materials import floor_def
        mode = self._symbol_mode()
        if floor == Material.PLAIN_AGGREGATE:
            payload = floor_def(str(aggregate_variant or ""))
            if payload.symbol_key == "floor":
                return (symbol("floor", mode),
                        AGGREGATE_PANEL_STYLES.get(str(aggregate_variant or ""), PANEL_MUTED))
            return symbol(payload.symbol_key, mode), FC['text']
        return symbol(floor_def(str(getattr(floor, "value", floor) or "")).symbol_key, mode), FC['text']

    @staticmethod
    def _terse_layer_token(index: int, value: Text) -> Text:
        """「⇓/⇔/⇗/⇑:」+ 层内容（层内容只有图标，不写中文地形名）。"""
        token = Text(terse.layer_glyph(index) + ":", style=FC['label'])
        token.append_text(value)
        return token

    @staticmethod
    def _terse_merged_icons(parts) -> Text:
        """同一层并列内容（图标 + 原定义色）用 / 连接，忽略空项。"""
        result = Text()
        for index, (glyph, color) in enumerate(parts):
            if index:
                result.append("/", style=FC['label'])
            result.append(glyph, style=panel_color(color))
        return result

    @staticmethod
    def _hover_cell_entry_line(x: int, y: int, terse_mode: bool) -> Text:
        """悬停读数末尾的「当前所在格详情」点击入口。"""
        if terse_mode:
            return Text(terse.current_cell_entry(), style=FC['muted'])
        return Text(f"▸ {tr('当前格')} ({x},{y}) · {tr('点击查看')}", style=FC['muted'])

    def _terse_terrain_layers(self, state, cell, *, visible: bool, concealed: bool,
                              mode: str) -> tuple[list, list, list]:
        """少字四层地形：地板/表面/高处/空中各只留图标（'?' 表示视野外未知）。"""
        surface: list[tuple[str, str]] = []
        high: list[tuple[str, str]] = []
        sky: list[tuple[str, str]] = []
        if cell.solid and not concealed:
            definition = wall_def(cell.wall_kind)
            icon = (symbol(definition.symbol_key, mode), definition.color)
            surface.append(icon)
            if cell.height >= 2:
                high.append(icon)
            if cell.height >= 3:
                sky.append(icon)
            elif cell.gas > 0:
                if visible:
                    gas_definition = gas_def(cell.gas_kind)
                    sky.append((f"{glyphs.gas_glyph(cell.gas, mode).strip()} {cell.gas}", gas_definition.color))
                else:
                    sky.append(("?", PANEL_MUTED))
            if visible and cell.liquid > 0:
                liquid_definition = liquid_def(cell.liquid_kind)
                surface.append((f"{symbol(glyphs.liquid_depth_key(cell.liquid), mode).strip()} {cell.liquid}",
                                liquid_definition.color))
        elif visible:
            if cell.plant:
                plant = plant_def_for(cell.plant)
                icon = (symbol(plant.key, mode), plant.color)
                surface.append(icon)
                if plant.height >= 2:
                    high.append(icon)
            if cell.liquid > 0:
                liquid_definition = liquid_def(cell.liquid_kind)
                surface.append((f"{symbol(glyphs.liquid_depth_key(cell.liquid), mode).strip()} {cell.liquid}",
                                liquid_definition.color))
            if cell.gas > 0:
                gas_definition = gas_def(cell.gas_kind)
                sky.append((f"{glyphs.gas_glyph(cell.gas, mode).strip()} {cell.gas}", gas_definition.color))
        else:
            if state.insight_active("双读") and not concealed:
                if cell.liquid > 0:
                    surface.append((symbol(glyphs.liquid_depth_key(cell.liquid), mode),
                                    PANEL_MUTED))
                if cell.gas > 0:
                    sky.append((glyphs.gas_glyph(cell.gas, mode), PANEL_MUTED))
            if not surface:
                surface.append(("?", PANEL_MUTED))
            if not high:
                high.append(("?", PANEL_MUTED))
            if not sky:
                sky.append(("?", PANEL_MUTED))
        return surface, high, sky


    def _terse_known_wall_text(self, info) -> Text:
        """知识权限下的墙面图标（不是当前视野；视野外仍是记忆里的墙材）。"""
        if getattr(info, "solid", False) and getattr(info, "wall_kind", ""):
            definition = wall_def(info.wall_kind)
            return Text(symbol(definition.symbol_key, self._symbol_mode()),
                        style=panel_color(definition.color))
        return Text("?", style=PANEL_MUTED)






    def _max_panel_scroll(self) -> int:


        if self.panel_mode == 'world_tamper':


            return max(0,getattr(self,'_world_tamper_total_lines',0)


                       -getattr(self,'_world_tamper_body_height',self._portent_viewport_rows()))


        # 观测面板：按视野内失控意识排版的总行数减去视窗行数。


        if self.panel_mode == "catalog":


            anomalies = self.session.state.visible_anomalies()


            if not anomalies:


                return 0


            width = self._portent_panel_width()


            _lines, _starts, total = self._observations_layout(


                self.session.state, anomalies, width


            )


            return max(0, total - self._portent_viewport_rows())


        # 征兆面板用同一套滚动量，但单位是「行」而不是「消息」。


        if self.panel_mode == "portents":


            _lines, _starts, total = self._portent_layout(self.session.state)


            return max(0, total - self._portent_viewport_rows())


        # 行囊/携带意象/洞察：与征兆同一口径（「行」为单位，首行偏移），总行数由各自的


        # 排版函数给出。旧实现只覆盖了 catalog/portents，这三个界面落到下面的


        # 「事件记录」分支算出 0，`_scroll` 因此永远把 panel_scroll 钳在 0——


        # 「行囊无法鼠标滚动」的根因。


        if self.panel_mode in ("inventory", "equipment", "insights", "tasks"):


            lines, _row_indices, _header = self._panel_lines(self.session.state)


            viewport = self._portent_viewport_rows()


            strip_lines = self._panel_subtabs_lines()


            if strip_lines:


                viewport = max(1, viewport - len(strip_lines))


            if self.panel_mode == "tasks":


                # 未完成任务钉底行（与 _scrolled_panel_text 的扣减对齐）。


                viewport = max(1, viewport - 1)


            return max(0, len(lines) - viewport)


        # 操作界面：同一口径（2026-09-21 修「构想左键不能使用」的一部分——


        # 滚轮要能滚到视窗外的构想/目标操作行）。


        if self.panel_mode == "actions":


            lines, _row_indices = self._actions_lines(self.session.state)


            viewport = self._portent_viewport_rows()


            strip_lines = self._panel_subtabs_lines()


            if strip_lines:


                viewport = max(1, viewport - len(strip_lines))


            # 右栏篡改页把「转到地图侧」的入口钉在最后一行：这一行也要从视窗里
            # 扣掉，否则滚到底时最后一条正文会被它顶出视野（与渲染分支同一口径）。


            if self._world_tamper_side_footer_line() is not None:


                viewport = max(1, viewport - 1)


            return max(0, len(lines) - viewport)


        # 事件记录最多可回看的消息数：以最早消息置顶、恰好填满面板为准，


        # 再多滚一行就会在面板下方留出空白。


        state = self.session.state
        messages = self._visible_game_messages(state)


        try:


            panel = self.query_one("#panel")


            available_rows = max(1, panel.content_size.height - 1)


            panel_width = max(1, panel.content_size.width)


        except Exception:


            return 0


        if self.path:


            available_rows -= 1


        used_rows = 0


        fitted = 0


        for message in messages:


            message_rows = max(1, (cell_len("● " + message) + panel_width - 1) // panel_width)


            if fitted and used_rows + message_rows > available_rows:


                break


            used_rows += message_rows


            fitted += 1


        return max(0, len(messages) - fitted)





    def _scroll(self, amount: int) -> None:


        # 事件记录：panel_scroll 是从最新消息向上回看的行数，上滚（amount=+1）应增加它。


        # 其余面板（征兆/观测/行囊/携带意象/洞察）：panel_scroll 是首行偏移，上滚应减小它


        # （显示上方的内容），故取反。


        delta = -amount if self.panel_mode in SCROLL_TOP_OFFSET_MODES else amount


        self.panel_scroll = min(self._max_panel_scroll(), max(0, self.panel_scroll + delta))


        self._refresh_navigation_selection()





    @staticmethod


    def _bar(


        label: str,


        value: int,


        maximum: int,


        styles: tuple[str, str, str],


        width: int = 20,


        suffix: str = "",


        label_width: int | None = None,


        value_width: int = 0,


    ) -> Text:


        # 三档色（满 / 中 / 低）：值归 0 时沿用最低档，不再有第四个「空槽」色。


        tier = 0 if value >= 50 else 1 if value >= 25 else 2


        filled = round(width * max(0, min(value, maximum)) / maximum)


        label_width = label_width or max(6, *(cell_len(tr(key)) for key in ("心智", "清醒度", "想象力")))


        label_padding = " " * max(0, label_width - cell_len(label))


        text = Text(label + label_padding + " ")


        # 空槽刻意低对比（BAR_TRACK），但要能看出「条有多长」——旧的 grey23 只有 1.25，


        # 等于槽完全看不见，只能靠左对齐去猜。


        text.append("┃" * filled, style=styles[tier])


        text.append("┃" * (width - filled), style=BAR_TRACK)


        digits = max(1, (value_width - 1) // 2)


        fraction = f"{value:>{digits}}/{maximum:>{digits}}" if value_width else f"{value}/{maximum}"


        text.append(f" {fraction}{suffix}", style=styles[tier])


        return text





    def _hover_extra_lines(self, state, x: int, y: int) -> list:
        """扩展包 v1 悬停附加行：机关嗅觉/读唇/measure 步数/wall_sense 隔墙。
        第十九节 §10.2：交出 `Text` 行而不是裸串。次要色只作整行底色，方案
        §4 点名的字段（构想残留三段、光源状态词、吸入浓度门槛、步数、警戒
        意图、声径）各自占一个片段，宿主不再把整段染成同一种灰。
        """
        lines = []
        try:
            cell = state.cell(x, y)
        except Exception:
            return lines
        if state.is_visible(x, y):
            from ..core.construct_environments import active
            from ..core.construct_environments import residue_name
            # 标签取自来源构想登记表，十种场全部有名，不再按字典缺键报错。
            for effect in active(state):
                if [x, y] in effect['cells']:
                    name = tr(residue_name(effect['kind']) or effect['kind'])
                    residue = tr('构想残留：{name} · 剩余 {turns} 回合 · 朝向 {direction}',
                                 name=name, turns=effect['remaining'],
                                 direction=str(tuple(effect['direction'])))
                    # §4：名称／剩余／朝向三段分别着色。按渲染结果的分隔符切片取
                    # 后两段，中英文共用同一条口径，不用另加文案键。
                    *_, remaining_chunk, facing_chunk = residue.split(' · ')
                    lines.append(self._hover_field_line(
                        residue, ((name, FC['word']), (remaining_chunk, FC['duration']),
                                  (facing_chunk, FC['position']))))
        if cell.gas>0 and cell.gas_kind and state.is_visible(x,y):
            from .gas_status import gas_contact_text
            # §4：浓度与触发最低浓度同属浓度族。
            lines.append(Text(gas_contact_text(state,cell,detail=True),
                              style=FC['concentration']))
        from ..core.tactical_layouts import hint_at
        hint=hint_at(state,x,y)
        if hint:
            # §4：机关提示／侦查所得线索用线索色，不跟整片信息一起压成灰。
            lines.append(Text(tr(hint), style=FC['grammar']))
        if cell.light_radius>0 and state.is_visible(x,y):
            # §12 F：三种设施的「能怎么操作」不一样，不能一律写「可切换」。
            from ..materials import FLAME_FIXTURE_KINDS, POWERED_FIXTURE_KINDS
            if cell.wall_kind in FLAME_FIXTURE_KINDS:
                line = tr('光源：靠燃烧发光，点着与浇灭决定明暗。')
                # §4：机制词单独着色（火焰橙／电场水青），不照着灯光把整段染色。
                lines.append(self._hover_field_line(line, ((self._first_clause(line), FC['damage']),)))
            elif cell.wall_kind in POWERED_FIXTURE_KINDS:
                line = tr('光源：接在电路上，通电才亮、断电即灭。')
                lines.append(self._hover_field_line(line, ((self._first_clause(line), FC['range']),)))
            else:
                line = tr('光源：亮着，可在相邻操作中熄灭。' if cell.light_on else
                          '光源：熄灭，可在相邻操作中点亮。')
                # 开启用程度金；关闭就留在次要底色上，不再提亮。
                lines.append(self._hover_field_line(
                    line, ((self._first_clause(line), FC['degree']),) if cell.light_on else ()))
        if state.realm_id == "toy_memories" or state.insight_active("电工直觉"):
            lines.extend(state.circuit_details(x, y))
        if state.insight_active("机关嗅觉"):
            lines.extend(state.trigger_insight_details(x, y))
        if cell.solid and cell.wall_kind not in ("", "门", "机关门"):
            if state.insight_active("wall_sense") or state._effect_power("wall_sense") > 0:
                for enemy in state.enemies:
                    if enemy.integrity > 0 and max(abs(enemy.x - x), abs(enemy.y - y)) <= 1:
                        lines.append(tr("墙后传来轻微的心跳声……"))
                        break
        if not cell.solid and state._effect_power("measure") > 0:
            path = state.path_to(x, y)
            if path:
                # §4：路径步数属数量族，可达距离才用水青。
                lines.append(Text(tr("步数：{n}", n=len(path)), style=FC['count']))
        # 意图切换文字（设计 §8/§9）：与角标读同一份 core.anomaly_intents 事实，
        # 悬停、右键详情和键盘观察共用这一条，鼠标不会比键盘多知道什么。
        from .anomaly_intent_marks import COLORS, intent_text
        switched = intent_text(state, x, y)
        if switched:
            label = tr(switched[1])
            line = tr("刚才切换：{label}", label=label)
            lines.append(self._hover_field_line(line, ((label, f"bold {COLORS[switched[0]]}"),)))
        for enemy in state.enemies:
            if (enemy.integrity > 0 and enemy.communicates and enemy.x == x
                    and enemy.y == y and state.is_visible(x, y)
                    and state.insight_active("读唇")):
                intent = {"追踪": "向你扑来", "警戒": "正在犹豫", "未察觉": "尚未察觉你"}.get(
                    enemy.alert_state, "徘徊")
                lines.append(self._hover_field_line(
                    tr("意图：{intent}", intent=intent),
                    ((intent, ALERT_STYLES.get(enemy.alert_state, PANEL_MUTED)),)))
                break
        # 只描述真实发声入口：14 属于「回响」构想，不属于普通近战；蜂鸣诱饵
        # 在落点发声，不在玩家脚下。半径口径统一走 core.sound_preview，与
        # 真实 _sound_pulse 同源（不在这里另算一套修正）。
        from ..core import sound_preview
        step = sound_preview.footstep_preview(state, (x, y))
        # 非玩家格只留一行「踩踏会发声」，不再列来源明细；玩家自身格不显示脚步半径。
        if ((x, y) != (state.player.x, state.player.y)
                and step['radius'] > 0 and (cell.aggregate_variant or cell.liquid)):
            lines.append(Text(tr("踩踏会发声（半径 {n}）", n=step['radius']), style=FC['range']))
        lines.extend(self._echo_pulse_hover_lines(state, (x, y)))
        return [line if isinstance(line, Text) else Text(line, style=PANEL_MUTED)
                for line in lines]





    def _echo_pulse_hover_lines(self, state, xy: tuple[int, int]) -> list:


        """可见相邻异象（或悬停异象）时，显示「回响」构想的**实际**半径。





        旧侧栏把「近战 14」写成所有近战的声响，误导玩家：普通近战没有统一


        脉冲入口，14 只属于玩家格的「回响」构想。这里只在真的有可攻击目标


        附近时给出该构想的实际值，并保留全部生效修正来源。


        """


        px, py = state.player.x, state.player.y


        hx, hy = xy





        def hostile(enemy) -> bool:


            return (enemy.integrity > 0 and enemy.relation == '失控意识'


                    and state.is_visible(enemy.x, enemy.y))





        hovered = any(hostile(enemy) and (enemy.x, enemy.y) == (hx, hy)


                      for enemy in state.enemies)


        adjacent = any(hostile(enemy) and max(abs(enemy.x - px), abs(enemy.y - py)) <= 1


                       for enemy in state.enemies)


        if not (hovered or adjacent):


            return []


        from ..core.sound_preview import echo_ability_preview





        preview = echo_ability_preview(state)


        lines = [Text(tr('移动声影（下一拍）声响半径：{n}', n=preview['radius']),


                      style=FC['range'])]


        lines.extend(tr("↳ {source}", source=source) for source in preview['sources'])


        return lines





    def _hover_text(self, state: GameState, width: int = 44) -> Text:
        # 鼠标未悬浮任何格子时，回退显示（当前）所在位置的环境；
        # 有悬浮则始终优先显示悬浮格。当前: / 悬停: 标签区分两种来源。
        hovered = self.hover_cell is not None
        if hovered and not (0 <= self.hover_cell[0] < state.width and 0 <= self.hover_cell[1] < state.height):
            # 悬停坐标不属于本层（换层瞬间的残留）：当作未悬停处理。
            self.hover_cell = None
            hovered = False
        x, y = self.hover_cell if hovered else (state.player.x, state.player.y)
        cell = state.cell(x, y)
        state.hover_target = (x, y)
        visible = state.is_visible(x, y)
        # 显影格：液流留下的永久显影——即使视野外也公开完整环境信息。
        if not visible and (x, y) in state.developed_for_depth():
            visible = True
        # 三层信息（2026-10-18 docs 第 1 节第二批）：开关打开时，未知/记忆/
        # 全图地形/始终可见格走知识口径，不读取实时液体/气体/生物/物品读数。
        observe = bool(getattr(self, "observe_mode", False))
        # 少字模式：字段名换英文缩写/语义图标，地形四层只留图标；非少字模式保持原文。
        terse_mode = self._terse_active()
        symbol_mode = self._symbol_mode()
        fog_info = None
        if bool(getattr(state, "map_memory_enabled", False)) and not visible:
            fog_info = state.cell_knowledge(x, y)
            if fog_info.status not in ("visible", "developed"):
                return self._hover_text_fog(state, x, y, fog_info, width, hovered, observe)
        # 行1：位置与悬停坐标同行；其后环境描述按显示宽度自动折行：
        # 不固定某一项在某一行，仅当当前行放不下时才换行，直至显示完全。
        # 观察模式（x）下同一个读数改叫「观察:」——它跟着白色 ? 走，不是鼠标。
        # 少字模式只压字段名（P/O/C/H/G），坐标数字原样保留。
        if terse_mode:
            position_label = terse.abbrev("位置") + ":"
            coord_label = terse.abbrev(
                "观察" if observe else ("悬停" if hovered else "当前")) + ":"
        else:
            position_label = tr("位置:")
            coord_label = tr("观察:") if observe else (tr("悬停:") if hovered else tr("当前:"))
        text = Text.assemble((f"{position_label}({state.player.x},{state.player.y}) ", FC['position']),
                             (f'{coord_label}({x},{y})', FC['position']))
        # 地面上有掉落物时，紧跟在坐标同一行后面显示物品名（无则完全不显示）。
        ground_item = next(
            (entry.item for entry in state.world_items if (entry.x, entry.y) == (x, y)),
            None,
        )
        if ground_item is not None:
            amnesia = "oblivion_strong" in state.portents
            shown_item = "？？？" if amnesia else tr(ground_item.name)
            # 物品名 = 物品自己的定义色（2026-09-21：不同物品不同颜色）。
            ground_style = item_name_color(ground_item)
            ground_label = (terse.abbrev("地上") + ":") if terse_mode else tr('地上:')
            text.append(f" {ground_label}{drop_glyph(ground_item, symbol_mode)}{shown_item}", style=ground_style)
        text.append("\n")
        # 四层结构：地板（初始生成，与墙体无关）→ 表面（低层）→ 高处（中层）→ 空中（高层）。
        # 中墙（height=2）占表面与高处，阻碍液体、可共存气体；
        # 高墙（height>=3）占满三层，液体气体都被阻挡。
        floor_name = tr(cell.aggregate_variant) if cell.floor is Material.PLAIN_AGGREGATE else tr(cell.floor.value)
        floor_style = AGGREGATE_PANEL_STYLES.get(cell.aggregate_variant, PANEL_MUTED) if cell.floor is Material.PLAIN_AGGREGATE else FC['text']
        # 地面容器不属于墙体，视野外不保留记忆。若照常走墙体分支，玩家隔着黑暗
        # 也能读到容器名与硬度/厚度/完整度；地板材质（坚实聚合物）同样会暴露
        # 「此处埋着固体」。因此整格按未知的普通地面呈现，在视野外无法与地板区分。
        concealed_container = cell.wall_kind in CONTAINER_KINDS and not visible
        if concealed_container:
            floor_name, floor_style = tr("普通聚合物"), AGGREGATE_PANEL_STYLES["普通聚合物"]
        terse_floor = None
        terse_layers = None
        if terse_mode:
            terse_floor = self._terse_floor_glyph(
                "普通聚合物" if concealed_container else cell.aggregate_variant, cell.floor)
            terse_layers = self._terse_terrain_layers(
                state, cell, visible=visible, concealed=concealed_container, mode=symbol_mode)
        # 每一层（表面/高处/空中）都是一个「并列清单」：同一高度上可以同时存在
        # 多个东西（低矮固体 + 它承载的液体、漫过植物的液体、与低墙并存的气体……），
        # 全部用 "/" 列出，而不是后来者覆盖先来者。
        surface_parts: list[tuple[str, str]] = []
        high_parts: list[tuple[str, str]] = []
        sky_parts: list[tuple[str, str]] = []
        wall_stats = ""
        if cell.solid and not concealed_container:
            definition = wall_def(cell.wall_kind)
            # 墙体属性（硬度/厚度/完整度）跟随表面显示；高度由分层结构表达，不再重复。
            wall_stats = f" {tr('硬')}{cell.hardness} {tr('厚')}{cell.thickness} {tr('完')}{cell.integrity}"
            wall_part = (tr(definition.name), definition.color)
            surface_parts.append(wall_part)
            if cell.height >= 2:
                high_parts.append(wall_part)
            if cell.height >= 3:
                sky_parts.append(wall_part)
            elif cell.gas > 0:
                if visible:
                    gas_definition = gas_def(cell.gas_kind)
                    sky_parts.append((_material_token(gas_definition.name, gas_definition.color, cell.gas, field='concentration', icon=glyphs.gas_glyph(cell.gas, self._symbol_mode())), gas_definition.color))
                else:
                    # 视野外非墙体内容一律不可知
                    sky_parts.append(("?", PANEL_MUTED))
            if visible and cell.liquid > 0:
                # 低矮固体（高度 1）不阻断液体：同格可以「固体 + 液态记忆」并存。
                # 悬停读数求简——两者并列时不写固体的硬度/厚度/完整度，
                # 完整信息仍然看右键的格子详情。
                liquid_definition = liquid_def(cell.liquid_kind)
                surface_parts.append(
                    (_material_token(liquid_definition.name, liquid_definition.color, cell.liquid), liquid_definition.color)
                )
                wall_stats = ""
        elif visible:
            # 视野内：完整环境（表面植物/液体 + 空中气体可共存）。
            # 植物按高度分层：1 格高只占「表面」；2 格高同时占「表面」与「高处」。
            if cell.plant:
                plant = plant_def_for(cell.plant)
                surface_parts.append((tr(plant.name), plant.color))
                if plant.height >= 2:
                    high_parts.append((tr(plant.name), plant.color))
            if cell.liquid > 0:
                liquid_definition = liquid_def(cell.liquid_kind)
                surface_parts.append(
                    (_material_token(liquid_definition.name, liquid_definition.color, cell.liquid), liquid_definition.color)
                )
            if cell.gas > 0:
                gas_definition = gas_def(cell.gas_kind)
                sky_parts.append((_material_token(gas_definition.name, gas_definition.color, cell.gas, field='concentration', icon=glyphs.gas_glyph(cell.gas, self._symbol_mode())), gas_definition.color))
        else:
            # 视野外（灰色）：只有地板与记忆中的墙体可知，其余一律显示 ?
            surface_text, surface_style = "?", PANEL_MUTED
            high_text, sky_text = "?", "?"
            # 双读（开局自带的洞察）：未知格只显示类别（液态记忆 / 弥散印象），
            # 而非具体种类。地面容器是例外——它整格按未知的普通地面呈现
            # （见 concealed_container），这里若透出「这格有液体」，就等于隔墙
            # 点名「此处埋着一个可推倒的容器」，把容器保密机制从侧面拆掉。
            if state.insight_active("双读") and not concealed_container:
                if cell.liquid > 0:
                    surface_text, surface_style = tr("液态记忆"), PANEL_MUTED
                if cell.gas > 0:
                    sky_text = tr("弥散印象")
            surface_parts.append((surface_text, surface_style))
            high_parts.append((high_text, PANEL_MUTED))
            sky_parts.append((sky_text, PANEL_MUTED))

        def merged(parts):
            if not parts:
                return Text(tr('无'), style=FC['muted'])
            result = Text()
            for index, (content, color) in enumerate(parts):
                if index:
                    result.append('/', style=FC['label'])
                result.append_text(content if isinstance(content, Text) else
                                   Text(content, style=panel_color(color)))
            return result

        if terse_mode:
            surface_icons, high_icons, sky_icons = terse_layers
            surface = self._terse_merged_icons(surface_icons)
            if cell.solid and not concealed_container:
                # 少字：硬/厚/完 → H/T/I + 数字（H3 T2 I40），保留原字段配色。
                surface.append_text(Text(' '))
                for label, value, key in (('H', cell.hardness, 'hardness'),
                                          ('T', cell.thickness, 'thickness'),
                                          ('I', cell.integrity, 'integrity')):
                    surface.append_text(field_text(label, value, field=key, separator=''))
                    surface.append(' ')
            tokens = [self._terse_layer_token(0, Text(terse_floor[0], style=panel_color(terse_floor[1]))),
                      self._terse_layer_token(1, surface),
                      self._terse_layer_token(2, self._terse_merged_icons(high_icons)),
                      self._terse_layer_token(3, self._terse_merged_icons(sky_icons))]
            proximity = state.proximity_effects()
            if proximity:
                tokens.append(field_text('N:', tr('、').join(tr(p) for p in proximity),
                                         field='condition', separator=''))
        else:
            surface = merged(surface_parts)
            if wall_stats:
                surface.append_text(Text(' '))
                for label, value, key in (('硬', cell.hardness, 'hardness'),
                                          ('厚', cell.thickness, 'thickness'),
                                          ('完', cell.integrity, 'integrity')):
                    surface.append_text(field_text(label, value, field=key))
                    surface.append(' ')
            tokens = [_labeled('地板', Text(floor_name, style=panel_color(floor_style))),
                      _labeled('表面', surface), _labeled('高处', merged(high_parts)),
                      _labeled('空中', merged(sky_parts))]
            proximity = state.proximity_effects()
            if proximity:
                tokens.append(field_text('贴近：', tr('、').join(tr(p) for p in proximity),
                                         field='condition', separator=''))
        used = 0
        for content in tokens:
            for chunk in rich_lines(content, width):
                cost = cell_len(chunk.plain)
                if used and used + 1 + cost > width:
                    text.append('\n')
                    used = 0
                if used:
                    text.append(' ')
                    used += 1
                text.append_text(chunk)
                used += cost
        extra_lines = self._hover_extra_lines(state, x, y)
        if terse_mode:
            extra_lines = [terse.compress(line, symbol_mode) for line in extra_lines]
        for line in extra_lines:
            for chunk in self._split_text_by_width(line, width):
                text.append("\n")
                text.append_text(chunk)
        if not terse_mode and get_language() == "en":
            # 英文普通模式：悬停读数里的长单词缩写；入口行另行翻译，不参与。
            text = terse.compact_english(text)
        # 末尾点击入口：当前所在格详情（少字模式只留语义图标）。
        # 与正文同一条折行口径，极窄宽度下也不超宽。
        for chunk in self._split_text_by_width(self._hover_cell_entry_line(state.player.x, state.player.y, terse_mode), width):
            text.append("\n")
            text.append_text(chunk)
        return text








    def _known_floor_name(self, info) -> str:


        """知识快照/增强权限下的地板名称（不读取实时液体/气体）。"""


        if info.aggregate_variant:


            return tr(info.aggregate_variant)


        return tr(info.floor) if info.floor else "?"





    def _known_wall_name(self, info) -> str:


        """知识权限下的墙面名称；全图地形不给隐藏容器点名。"""


        if info.status == "terrain_known" and info.wall_kind in CONTAINER_KINDS:


            return tr("未知固体")


        return tr(wall_def(info.wall_kind).name) if info.wall_kind else "?"





    def _hazard_memory_line(self, state, x: int, y: int, status: str) -> str:


        """地形记忆洞察：视野外显示最近一次亲眼确认的危险快照。"""


        if status == "visible" or not state.insight_active("地形记忆"):


            return ""


        from ..core.vision.knowledge import hazard_snapshot


        snapshot = hazard_snapshot(state, x, y)


        if not snapshot:


            return ""


        parts: list[str] = []


        if snapshot["liquid"]:


            parts.append(tr("液体 {kind} {n}",


                            kind=tr(snapshot["liquid_kind"] or "?"), n=snapshot["liquid"]))


        if snapshot["gas"]:


            parts.append(tr("气体 {kind} {n}",


                            kind=tr(snapshot["gas_kind"] or "?"), n=snapshot["gas"]))


        if snapshot["flame"]:


            parts.append(tr("火焰 {n}", n=snapshot["flame"]))


        parts.append(tr("通行代价 {n}", n=snapshot["cost"]))


        return tr("上次观察（第 {turn} 回合）：{parts}",


                  turn=snapshot["turn"], parts=" · ".join(parts))





    def _hover_text_fog(self, state, x, y, info, width, hovered, observe) -> Text:
        """三层信息下的悬停读数：只显示当前授权范围内的内容，不再标注来源。"""
        terse_mode = self._terse_active()
        mode = self._symbol_mode()
        if terse_mode:
            position_label = terse.abbrev("位置") + ":"
            coord_label = terse.abbrev(
                "观察" if observe else ("悬停" if hovered else "当前")) + ":"
        else:
            position_label = tr("位置:")
            coord_label = tr("观察:") if observe else (tr("悬停:") if hovered else tr("当前:"))
        text = Text(
            f"{position_label}({state.player.x},{state.player.y}) {coord_label}({x},{y})",
            style=FC['text'],
        )
        text.append("\n")
        tokens: list[tuple[str, str]] = []
        terse_tokens: list[Text] = []
        if info.status == "unknown":
            if terse_mode:
                terse_tokens.append(Text(tr("未探索"), style=PANEL_MUTED))
                if state.insight_active("双读"):
                    cell = state.cell(x, y)
                    if cell.liquid > 0:
                        terse_tokens.append(Text(tr("液态记忆"), style=PANEL_MUTED))
                    if cell.gas > 0:
                        terse_tokens.append(Text(tr("弥散印象"), style=PANEL_MUTED))
            else:
                tokens.append((tr("未探索"), PANEL_MUTED))
                if state.insight_active("双读"):
                    # 双读只给类别，不给具体种类、数量、生物或物品。
                    cell = state.cell(x, y)
                    if cell.liquid > 0:
                        tokens.append((tr("液态记忆"), PANEL_MUTED))
                    if cell.gas > 0:
                        tokens.append((tr("弥散印象"), PANEL_MUTED))
        elif info.status == "always_visible":
            category = info.sources[-1] if info.sources else ""
            if terse_mode:
                if category:
                    terse_tokens.append(Text(tr(category), style=PANEL_MUTED))
                terse_tokens.append(self._terse_layer_token(
                    1, self._terse_known_wall_text(info)))
            else:
                tokens.append((tr("始终可见：") + tr(category), PANEL_MUTED))
                if info.solid and info.wall_kind:
                    tokens.append((tr("表面:") + self._known_wall_name(info), PANEL_MUTED))
                else:
                    tokens.append((tr("表面:") + "?", PANEL_MUTED))
        else:
            if terse_mode:
                if info.site:
                    terse_tokens.append(Text(tr("已发现地点：") + tr(info.site),
                                             style=FC['degree']))
                floor_glyph, floor_color = self._terse_floor_glyph(
                    info.aggregate_variant, info.floor)
                terse_tokens.append(self._terse_layer_token(
                    0, Text(floor_glyph, style=panel_color(floor_color))))
                terse_tokens.append(self._terse_layer_token(
                    1, self._terse_known_wall_text(info)))
                terse_tokens.append(self._terse_layer_token(2, Text("?", style=PANEL_MUTED)))
                terse_tokens.append(self._terse_layer_token(3, Text("?", style=PANEL_MUTED)))
            else:
                if info.site:
                    tokens.append((tr("已发现地点：") + tr(info.site), FC['degree']))
                tokens.append((tr("地板:") + self._known_floor_name(info), PANEL_MUTED))
                if info.solid and info.wall_kind:
                    tokens.append((tr("表面:") + self._known_wall_name(info), PANEL_MUTED))
                else:
                    tokens.append((tr("表面:") + "?", PANEL_MUTED))
                tokens.append((tr("高处:") + "?", PANEL_MUTED))
                tokens.append((tr("空中:") + "?", PANEL_MUTED))
        used = 0
        if terse_mode:
            for content in terse_tokens:
                for chunk in self._split_text_by_width(content, width):
                    cost = cell_len(chunk.plain)
                    if used > 0 and used + 1 + cost > width:
                        text.append("\n")
                        used = 0
                    if used > 0:
                        text.append(" ")
                        used += 1
                    text.append_text(chunk)
                    used += cost
        else:
            for content, style in tokens:
                for chunk in self._split_by_width(content, width):
                    cost = cell_len(chunk)
                    if used > 0 and used + 1 + cost > width:
                        text.append("\n")
                        used = 0
                    if used > 0:
                        text.append(" ")
                        used += 1
                    text.append(chunk, style=style)
                    used += cost
        if info.status != "unknown":
            # 记忆／全图地形／恒显格保留地形记忆洞察（视野外的最近一次确认快照）。
            hazard = self._hazard_memory_line(state, x, y, info.status)
            for chunk in self._split_by_width(hazard, width) if hazard else ():
                text.append("\n")
                text.append(chunk, style=PANEL_MUTED)
        if terse_mode:
            # 视野外读数里的「未探索 / 液态记忆 / 弥散印象 / 始终可见」等
            # 文字在少字模式下换成符号/缩写；入口行保持纯符号，不参与压缩。
            text = terse.compress(text, mode)
        elif get_language() == "en":
            # 英文普通模式：知识权限读数里的长单词缩写。
            text = terse.compact_english(text)
        # 末尾点击入口：当前所在格详情（少字模式只留语义图标）。
        # 与正文同一条折行口径，极窄宽度下也不超宽。
        for chunk in self._split_text_by_width(self._hover_cell_entry_line(state.player.x, state.player.y, terse_mode), width):
            text.append("\n")
            text.append_text(chunk)
        return text





    @staticmethod


    def _first_clause(content: str) -> str:


        """取「光源：亮着，…」的第一个子句，只给状态词着色，不新增文案键。"""


        clause = content.split('：', 1)[-1]


        for separator in ('，', '、'):


            clause = clause.split(separator, 1)[0]


        return clause





    @staticmethod


    def _hover_field_line(content: str, fields: tuple) -> Text:


        """整行只铺次要底色，方案点名的字段片段抬到自己的专色（§10.2）。





        片段按渲染结果里的实际文字定位，命不中（例如英文模板改写后）就整行


        留次要色，不会误染别的字；底色写成显式片段，宿主拼接后仍然在。


        """


        text = Text(content)


        text.stylize(PANEL_MUTED, 0, len(content))


        for fragment, style in fields:


            start = 0


            while fragment and (index := content.find(fragment, start)) >= 0:


                text.stylize(style, index, index + len(fragment))


                start = index + len(fragment)


        return text





    @staticmethod


    def _split_by_width(content: str, width: int) -> list[str]:


        """按显示宽度把一个项切成不超过 width 列的片段（单行放不下的长项也完整显示）。





        英文按词换行（保留词后空格）；没有空格的 CJK 串按字符硬切，


        避免 Rich 的 wrap 对长中文串不折行、极窄面板下一行超宽。


        """


        if width <= 0:


            return [content]


        tokens = re.findall(r"[^\s]+\s*|\s+", content)


        chunks: list[str] = []


        current = ""


        used = 0


        for token in tokens:


            token_width = cell_len(token)


            if used + token_width <= width:


                current += token


                used += token_width


                continue


            if current:


                chunks.append(current)


                current = ""


                used = 0


            if not token.isspace() and token_width <= width:


                current = token


                used = token_width


                continue


            for char in token:


                char_width = cell_len(char)


                if used + char_width > width and current:


                    chunks.append(current)


                    current = ""


                    used = 0


                current += char


                used += char_width


        if current:


            chunks.append(current)


        return chunks or [content]





    def _split_text_by_width(self, content: Text, width: int) -> list[Text]:


        """与 _split_by_width 同一条换行口径，但切片保住字段片段自己的着色。"""


        plain = content.plain


        chunks: list[Text] = []


        offset = 0


        for piece in self._split_by_width(plain, width):


            index = plain.find(piece, offset)


            if index < 0:


                return [content]


            chunks.append(content[index:index + len(piece)])


            offset = index + len(piece)


        return chunks or [content]





    def _panel_text(self, state: GameState) -> Text:


        """面板正文 + 行映射快照（点击定位用，见 _panel_rows/_panel_row_keys）。"""


        text = self._panel_text_build(state)


        # 行 → 条目键，与 _panel_rows **逐行对齐、渲染时定格**。


        # 点击必须查这张快照而不是重算：操作界面的「目标操作」条数会随目标格


        # 变化（异象走开/死亡就少一条），渲染与点击之间对不上时旧写法会让构想


        # 行解析不出键、整段静默 return——「左键构想无效」的根因。


        self._panel_row_keys = [


            self._panel_entry_key(index) if index >= 0 else None


            for index in self._panel_rows


        ]


        return text





    # ---- 同一按钮界面内的分层小页签（2026-10-23 用户定稿）----
    # 行囊分类筛选 / 装备盘·记忆碎片 / 操作界面的构想·发射·篡改。页签渲染在
    # 面板最顶行，点击命中走 _panel_subtab_hits；←→ 先切页，到两端才换按钮。

    def _panel_subpage_ids(self, mode: str | None = None) -> tuple[str, ...]:
        from .styles import PANEL_SUBPAGES
        return PANEL_SUBPAGES.get(mode or self.panel_mode, ())

    def _panel_subpage_id(self, mode: str | None = None) -> str:
        mode = mode or self.panel_mode
        ids = self._panel_subpage_ids(mode)
        if not ids:
            return ""
        current = getattr(self, "panel_subpages", {}).get(mode, "")
        return current if current in ids else ids[0]

    def _panel_subpage_label(self, subpage_id: str) -> str:
        from .styles import PANEL_SUBPAGE_LABELS
        return tr(PANEL_SUBPAGE_LABELS.get(subpage_id, subpage_id))

    def _panel_subtabs_lines(self) -> list[Text]:
        """面板顶部的分层页签（可能折成多行）；没有分层的界面返回空列表。"""
        from .sidebar_workspaces import SUBTAB_COLORS
        ids = self._panel_subpage_ids()
        self._panel_subtab_hits = []
        if not ids or self.panel_mode in ('equipment', 'actions'):
            return []
        active = self._panel_subpage_id()
        width = max(8, self._portent_panel_width())
        lines: list[Text] = []
        line = Text()
        column = 0
        row = 0
        terse_mode = self._terse_active()
        for index, subpage_id in enumerate(ids):
            selected = subpage_id == active
            if terse_mode:
                label = terse.subpage_symbol(subpage_id, self._symbol_mode())
            elif get_language() == 'en':
                # 英文普通模式：右栏小页签用短名，完整词在详情界面。
                label = terse.subpage_english_short(subpage_id)
            else:
                label = self._panel_subpage_label(subpage_id)
            token = ("▶" if selected else " ") + label
            token_width = cell_len(token)
            separator = 0 if index == 0 else 1
            if index and column + separator + token_width > width:
                lines.append(line)
                line = Text()
                column = 0
                row += 1
                separator = 0
            if separator:
                line.append(" ", style=PANEL_MUTED)
                column += separator
            start = column
            color = SUBTAB_COLORS[index % len(SUBTAB_COLORS)]
            line.append(token, style=(f"bold underline {color}" if selected else color))
            column += token_width
            self._panel_subtab_hits.append((row, start, column, subpage_id))
        if line.plain:
            lines.append(line)
        return lines

    def set_panel_subpage(self, subpage_id: str, *, refresh: bool = True) -> bool:
        """切到当前按钮界面内的某一层；行囊层直接同步物品分类筛选。"""
        mode = self.panel_mode
        ids = self._panel_subpage_ids(mode)
        if not ids or subpage_id not in ids:
            return False
        if self._panel_subpage_id(mode) == subpage_id:
            return True
        if not hasattr(self, "panel_subpages"):
            return False
        self._sidebar_transition(mode, subpage=subpage_id, refresh=refresh)
        return True

    def cycle_panel_subpage(self, delta: int) -> bool:
        """←→ 优先切同一按钮内的分层；到达边界返回 False，由输入层消费，不跨分区。"""
        ids = self._panel_subpage_ids()
        if not ids:
            return False
        index = ids.index(self._panel_subpage_id())
        new_index = index + delta
        if 0 <= new_index < len(ids):
            return self.set_panel_subpage(ids[new_index])
        return False

    def panel_subtab_click(self, row: int, offset_x: int) -> bool:
        """面板顶部页签的点击命中（row/x 为相对面板内容区）。"""
        for hit_row, start, end, subpage_id in getattr(self, '_panel_subtab_hits', ()):
            if hit_row == row and start <= offset_x < end:
                return self.set_panel_subpage(subpage_id)
        return False

    def _panel_text_build(self, state: GameState) -> Text:


        # 每次重绘都重建「行号 → 条目序号」映射（-1 = 无对应条目的装饰行），


        # 供鼠标左键点击右侧面板时定位条目。


        self._panel_rows = []


        self._panel_row_keys = []


        # 切换面板页时把滚动归零（2026-09-21）：右键开操作菜单、瞄准等入口


        # 各自设 panel_mode 但不重置 panel_scroll，切片渲染下会直接显示在


        # 半截内容上。集中在渲染入口统一处理，谁加新入口都不会漏。


        if getattr(self, "_panel_mode_seen", None) != self.panel_mode:


            self._panel_mode_seen = self.panel_mode


            self.panel_scroll = 0


        # 2026-10-23：地图篡改浮层不再占用右侧面板；只有事件内篡改仍借用
        # 右侧显示观察读数（它本来就属于对话流程的一部分）。
        if self.tamper_editor is not None:
            return self._tamper_observation_text(state,max(8,self._portent_panel_width()))


        if self.panel_mode.startswith("home"):


            text = Text()


            if self.panel_mode == "home":


                text.append(tr("选择一个存档槽入梦"), style=FC['text'])


                text.append("\n" + tr("←→ 选择选项 · ↑↓ 换行 · 左键点击进入 · D 删除"), style=PANEL_MUTED)


            elif self.panel_mode == "home_catalog":


                text.append(tr("图鉴") + "\n", style=f"bold {FC['degree']}")


                for entry in sorted(state.catalog.values(), key=lambda item: item.get("name", "")):


                    text.append(f"{entry['name']} ×{entry['interactions']}\n", style=FC['degree'])


            elif self.panel_mode == "home_saves":


                text.append(tr("测试存档栏" if getattr(self, "saves_test", False) else "存档栏") + "\n",


                            style=f"bold {FC['heading']}")


                if self.home_confirm_delete:


                    # 两段确认的第一段：只警告，存档文件原封不动（移动光标即取消）。


                    # 用 PANEL_DANGER（注册表 danger）而不是 bright_red：命名色会被主题解析成


                    # #f4005f，在面板上只有 3.30；这个 hex 在两处表面都达标（黑底 6.78）。


                    text.append(


                        tr("再次按 Enter 确认删除存档槽 {n}；按方向键取消。").format(n=self.selected_slot),


                        style=f"bold {PANEL_DANGER}",


                    )


                else:


                    exists = self._saves_manager().for_slot(self.selected_slot).slot_exists()


                    text.append(tr("已选择存档槽 {n}。").format(n=self.selected_slot), style=FC['condition'])


                    text.append(tr("按 Enter 进入，按 D 删除。") if exists else tr("按 Enter 开始新游戏。"), style=FC['effect'])


                    if getattr(self, "saves_test", False):


                        text.append("\n\n" + tr("测试模式：删除后可新建；R 可直接用新的调律选项替换这一局（取消则旧档不变）。"),


                                    style=PANEL_MUTED)


            elif self.panel_mode == "home_newgame":


                text.append(tr("调律这一局梦") + "\n", style=f"bold {FC['heading']}")


                text.append(tr("←→ 调整指标 · 空格/Enter 开关 · Esc 返回"), style=PANEL_MUTED)


            else:


                text.append(tr("设置") + "\n" + tr("终端输入和颜色沿用当前配置。"), style=FC['text'])


            return text


        if self.panel_mode == "inventory":


            text = self._scrolled_panel_text(state)


        elif self.panel_mode == "equipment":


            from ..equipment.reading import scan


            from ..equipment.board import Placement


            text = self._scrolled_panel_text(state)


        elif self.panel_mode == "portents":


            text = self._portents_panel_text(state)


        elif self.panel_mode == "insights":


            text = self._scrolled_panel_text(state)


        elif self.panel_mode == "tasks":


            text = self._scrolled_panel_text(state)


        elif self.panel_mode == "catalog":


            anomalies = state.visible_anomalies()


            total_count = sum(a["count"] for a in anomalies)


            text = Text.assemble((tr("观测"), f"bold {FC['degree']}"), tr("  {kinds} 种 · {total} 个", kinds=len(anomalies), total=total_count))


            if not anomalies:


                text.append("\n" + tr("视野中没有失控意识"), PANEL_MUTED)


                self._panel_rows.append(-1)


            else:


                width = self._portent_panel_width()


                lines, starts, total_lines = self._observations_layout(state, anomalies, width)


                viewport = self._portent_viewport_rows()


                max_scroll = max(0, total_lines - viewport)


                self.panel_scroll = min(self.panel_scroll, max_scroll)


                start = self.panel_scroll


                self._panel_rows.append(-1)  # 标题行


                for line in lines[start:start + viewport]:


                    text.append("\n")


                    text.append_text(line)


                for line_no in range(start, min(total_lines, start + viewport)):


                    entry_index = -1


                    for candidate, begin in enumerate(starts):


                        if begin <= line_no:


                            entry_index = candidate


                        else:


                            break


                    self._panel_rows.append(entry_index)


                if total_lines > viewport:


                    last = min(total_lines, start + viewport)


                    text.append(


                        self._panel_scroll_hint(start + 1, last, total_lines),


                        style=SCROLL_HINT_STYLE,


                    )


                    self._panel_rows.append(-1)


        elif self.panel_mode == "actions":
            strip_lines = self._panel_subtabs_lines()
            text = Text()
            for strip_line in strip_lines:
                text.append_text(strip_line)
                text.append("\n")
                self._panel_rows.append(-3)
            # 标题行的行映射必须占位——_panel_rows 是「可视行 → 条目序号」的
            # 逐行对应表（缺一行则整块点击都差一行）。标题钉住不滚动。
            heading = 'ACT' if self._terse_active() else tr("操作界面")
            text.append_text(zone_strip(heading, self._portent_panel_width(), color=FC["condition"]))
            self._panel_rows.append(-1)
            lines, row_indices = self._actions_lines(state)
            # 右栏篡改页把「转到地图侧」的入口钉在最后一行（与任务页钉底同一口径）：
            # 这行由 _world_tamper_side_lines 随正文写下，编辑器不在右栏时一律不认。
            # 构想页的键位行同样钉底（_panel_footer，2026-10-24 口径）。
            footer = self._world_tamper_side_footer_line() or self._panel_footer(state)
            viewport = self._portent_viewport_rows()
            if strip_lines:
                viewport = max(1, viewport - len(strip_lines))
            if footer is not None:
                viewport = max(1, viewport - 1)
            if self._panel_subpage_id() == 'constructs':
                # Only reserve a scroll-hint row when content actually overflows.
                viewport = max(1, self.query_one('#panel').content_size.height
                               - 1 - len(strip_lines) - int(footer is not None))
                if len(lines) > viewport:
                    viewport = max(1, viewport - 1)
            max_scroll = max(0, len(lines) - viewport)
            self.panel_scroll = min(self.panel_scroll, max_scroll)
            start = self.panel_scroll
            for offset in range(start, min(len(lines), start + viewport)):
                text.append("\n")
                text.append_text(lines[offset])
                self._panel_rows.append(row_indices[offset])
            if len(lines) > viewport:
                last = min(len(lines), start + viewport)
                text.append(
                    self._panel_scroll_hint(start + 1, last, len(lines)),
                    style=SCROLL_HINT_STYLE,
                )
                self._panel_rows.append(-1)
            if footer is not None:
                text.append("\n")
                text.append_text(footer)
                self._panel_rows.append(getattr(self, "_panel_footer_entry", -1))


        else:


            text = Text.assemble((tr("事件记录"), f"bold {FC['degree']}"))

            visible_messages = self._visible_game_messages(state)


            available_rows = max(1, self.query_one("#panel").content_size.height - 1)


            end = len(visible_messages) - self.panel_scroll


            candidates = visible_messages[:max(0, end)] if end else []


            messages: list[str] = []


            used_rows = 0


            panel_width = max(1, self.query_one("#panel").content_size.width)


            for message in reversed(candidates):


                message_rows = max(1, (cell_len("● " + message) + panel_width - 1) // panel_width)


                if messages and used_rows + message_rows > max(1, available_rows):


                    break


                messages.append(message)


                used_rows += message_rows


            messages.reverse()


            for message in messages:


                text.append("\n")


                text.append_text(self._message_text(message))


        # 少字模式（terse_mode）：右栏正文统一压缩（状态名→图标、字段名→缩写）。
        # 日志(world)与构筑(equipment)保持原文；行数不变，_panel_rows 行映射照旧。
        # 双列页先排版并建立列级命中表，不能再对整段文字做变长替换。
        # 构想和篡改各自在生成列内容时缩写，保持分隔线和命中列不变。
        column_layout = (self.panel_mode == 'actions'
                         and self._panel_subpage_id() in ('constructs', 'tamper'))
        if self._terse_active() and self.panel_mode not in ("world", "equipment") and not column_layout:
            text = terse.compress(text, self._symbol_mode())
        elif (not self._terse_active() and get_language() == "en"
              and self.panel_mode not in ("world", "equipment") and not column_layout):
            # 英文普通模式：右栏长单词缩写。环境页/数值页连正文词一起压；
            # 行囊/操作页只压字段与标题，物品名与构想名保持完整。
            text = terse.compact_english(
                text, word_level=self.panel_mode in ("nearby", "self_stats"))


        return text





    # ---- 操作界面：可滚动行列表（发射 / 构想 / 目标操作 / 附加状态行）----
    # 2026-10-23：同一按钮界面内分「构想 / 发射 / 篡改」三页；选择空间与行映射
    # 都按当前页计算，旧调用方仍只认 _actions_lines 这个入口。

    def _actions_lines(self, state: GameState) -> tuple[list[Text], list[int]]:
        page = self._panel_subpage_id()
        if page == "fire":
            return self._fire_actions_lines(state)
        if page == "tamper":
            return self._tamper_actions_lines(state)
        return self._construct_actions_lines(state)


    def _construct_actions_lines(self, state: GameState) -> tuple[list[Text], list[int]]:


        """操作界面的**完整**行列表 + 每行条目序号（-1 = 装饰行）。





        供 `_panel_text_build` 按视窗切片渲染（2026-09-21 修「构想左键不能


        使用」：内容一多视窗外既看不见也点不到），也供键盘跟随滚动


        （`_follow_actions_selection`）用同一份排版，两条路径永不错位。





        行映射口径与旧实现一致：目标操作条目存 ``offset``（0 起）、构想存


        ``context_count + offset``、装饰行存 -1——与 ``_panel_entry_key`` /


        ``_panel_item_count`` 的计数完全对齐。


        """


        lines: list[Text] = []


        row_indices: list[int] = []


        abilities = [ability_id for ability_id in state.abilities if ability_id in ABILITY_DEFINITIONS]


        context_count = len(self._actions_for(self.context_menu_target)) if self.context_menu_target else 0


        width = max(8, self._portent_panel_width() - 4)


        # 折行宽度（2026-10-07 补定义）：面板内容宽 − 4（明细行带 4 列缩进，


        # add() 里的 width + 4 正是为它预留的余量）。旧实现在此引用了


        # 未定义的 width，操作面板一渲染就 NameError。


        width = max(1, self.query_one("#panel").content_size.width - 4)





        def add(line: Text, row_index: int = -1) -> None:


            # 名称也可能跨行，必须把每个可见行登记到同一个条目，供鼠标定位。


            for wrapped in line.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):


                lines.append(wrapped)


                row_indices.append(row_index)





        # §15.6 操作预览：选中的这一发若会改地势／液面，文字钉在**它自己那行**下面。


        # 插进去的都是装饰行（row_index = -1），点击与键盘的条目映射因此不受影响。


        preview = self._terrain_preview_for(state)

        # —— 构想列表块（2026-10-24 重构：列表 + 简介常显，同族纸 ZONE_CAST_LIST）——
        # 主动构想：随操作面板一同展示，Enter 激活。
        add(zone_strip(tr("—— 主动构想 ——"), width + 4, color=FC['word']))
        if not abilities:
            add(paper_pad(Text(tr("尚未习得任何构想（书卷与残页中藏着它们）"), PANEL_MUTED),
                          ZONE_CAST_LIST, width + 4))
        for offset, ability_id in enumerate(abilities):
            definition = ABILITY_DEFINITIONS[ability_id]
            selected = (context_count + offset) == self.panel_selection
            cooldown = state.ability_cooldowns.get(ability_id, 0)
            # 消耗想象**始终**在第一位；冷却只是在它后面追加一段，不替代它——
            # 玩家反馈「冷却时看不到消耗」（要判断还差多久能用、值不值得等，
            # 两件事都要看见）。
            marker = "▶ " if selected else "  "
            head = Text.assemble(
                (marker, FC['word']),
                icon_label(
                    'ability.' + ability_id, tr(definition['name']),
                    FC['word'] + (' bold underline' if selected else '')),
                ('  ' + str(state._scaled_ability_cost(int(definition['cost']))) + ' ' + tr('想象力'), FC['cost']),
                ('　·　' + tr('冷却 {n} 回合', n=cooldown), FC['cooldown']) if cooldown else '')
            add(paper_pad(head, ZONE_CAST_LIST, width + 4), context_count + offset)
            # 简介默认折叠（2026-10-24 玩家定稿，撤回同日"常显"）：\ 全局展开
            # （details_expanded）；实际右栏由 sidebar_management 的左右分区版
            # 接管：普通点击单条展开，Shift+点击保持激活/施放。
            if self._details_visible():
                for wrapped in Text(f"    {tr(definition['description'])}", style=PANEL_MUTED).wrap(
                        _WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
                    add(paper_pad(wrapped, ZONE_CAST_LIST, width + 4), context_count + offset)

        # —— 使用预览块（2026-10-24 重构：选中构想的具体施放说明，ZONE_CAST_PREVIEW）——
        # 取代旧的「地形预览钉在选中行下面」：预览集中成第二块，写清这一发
        # 怎么放、形态射程、花多少；地形预览（§15.6）并入块尾。
        add(zone_strip(tr("—— 使用预览 ——"), width + 4, color=FC['word']))
        selected_ability = None
        if abilities:
            sel = self.panel_selection - context_count
            selected_ability = abilities[sel] if 0 <= sel < len(abilities) else abilities[0]
        if selected_ability is None:
            add(paper_pad(Text(tr("习得构想后，这里显示选中一发的形态与施放流程。"), PANEL_MUTED),
                          ZONE_CAST_PREVIEW, width + 4))
        else:
            definition = ABILITY_DEFINITIONS[selected_ability]
            cooldown = state.ability_cooldowns.get(selected_ability, 0)
            from ..core.combat_constructs import is_combat
            from ..core.ability_targeting import is_targeted
            head = Text.assemble(
                (tr(definition['name']), 'bold ' + FC['word']),
                ('  ' + str(state._scaled_ability_cost(int(definition['cost']))) + ' ' + tr('想象力'), FC['cost']),
                ('　·　' + tr('冷却 {n} 回合', n=cooldown), FC['cooldown']) if cooldown else '')
            for wrapped in head.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
                add(paper_pad(wrapped, ZONE_CAST_PREVIEW, width + 4))
            combat = definition.get('combat') or {}
            if combat:
                forms = {'melee': tr('近战'), 'launch': tr('弹道'), 'throw': tr('投掷'),
                         'area': tr('范围'), 'blink': tr('位移')}
                detail = Text(tr('形态') + ' ' + forms.get(str(combat.get('form')), str(combat.get('form'))),
                              style=FC['grammar'])
                if combat.get('range') is not None:
                    detail.append(' · ' + tr('射程') + ' ' + str(combat['range']), style=FC['range'])
                if combat.get('targeting'):
                    detail.append(' · ' + tr('目标') + ' ' + tr(str(combat['targeting'])), style=FC['category'])
                if combat.get('sound'):
                    detail.append(' · ' + tr('声响') + ' ' + str(combat['sound']), style=FC['noise'])
                for wrapped in detail.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
                    add(paper_pad(wrapped, ZONE_CAST_PREVIEW, width + 4))
            # 施放流程按真实分支写（_activate_panel_selection 的口径）：战斗/选点
            # 类先零消耗瞄准、确认才支付；其余立即施放。
            flow = (tr('Enter/左键 进入零消耗瞄准，确认时才支付。')
                    if is_combat(selected_ability) or is_targeted(selected_ability)
                    else tr('Enter/左键 立即施放。'))
            add(paper_pad(Text(flow, style=FC['windup']), ZONE_CAST_PREVIEW, width + 4))
            for wrapped in Text(tr(definition['description']), PANEL_MUTED).wrap(
                    _WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
                add(paper_pad(wrapped, ZONE_CAST_PREVIEW, width + 4))
            if preview is not None:
                for line_offset, line in enumerate(preview.lines):
                    body = Text(line, style=f"bold {FC['word']}" if line_offset == 0 else PANEL_MUTED)
                    for wrapped in body.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
                        add(paper_pad(wrapped, ZONE_CAST_PREVIEW, width + 4))


        identity_abilities = state.identity_abilities()


        if identity_abilities:


            add(zone_strip(tr('—— 身份能力 ——'), width + 4, color=FC['identity']))


        for offset, ability in enumerate(identity_abilities):


            index = context_count + len(abilities) + offset


            selected = index == self.panel_selection


            name, cost = ('借雾', 5) if ability == 'borrow_fog' else ('退稿', 4)


            cooldown = max(0, state.identity_state.get('cooldowns', {}).get(ability, 0) - state.time)


            status = f"{cost} {tr('想象力')}"


            if cooldown:


                status += ' · ' + tr('冷却 {n} 回合', n=cooldown)


            line=Text(('▶ ' if selected else '  ')+tr(name),style=FC['identity']+(' bold underline' if selected else ''))


            line.append('  '+str(cost)+' '+tr('想象力'),style=FC['cost'])


            if cooldown: line.append(' · '+tr('冷却 {n} 回合',n=cooldown),style=FC['cooldown'])


            add(line,index)


        sentence_options = state.equipment.active_sentence_options()


        if sentence_options:


            add(zone_strip(tr('—— 装备语句 ——'), width + 4, color=FC['identity']))


        for offset, option in enumerate(sentence_options):


            index = context_count + len(abilities) + len(identity_abilities) + offset


            selected = index == self.panel_selection


            status = tr('想象力 {cost} · 射程 {range} · 冷却 {cooldown}',


                        cost=option.cost, range=option.range, cooldown=round(option.cooldown, 1))


            if option.consumes_source:


                status = tr('消耗 1 件工具 · 耗时 1 回合 · 距离 {range}',range=option.range)


            add(Text(('▶ ' if selected else '  ') + option.text,


                     style=FC['identity'] + (' bold underline' if selected else '')), index)


            if option.consumes_source:


                details=Text('    '+tr('消耗 1 件工具'),style=FC['cost'])


                details.append(' · '+tr('耗时 1 回合'),style=FC['time'])


                details.append(' · '+tr('距离')+' '+str(option.range),style=FC['range'])


            else:


                details=Text('    '+tr('想象力')+' '+str(option.cost),style=FC['cost'])


                details.append(' · '+tr('射程')+' '+str(option.range),style=FC['range'])


                details.append(' · '+tr('冷却')+' '+str(round(option.cooldown,1)),style=FC['cooldown'])


            add(details,index)


            add(Text('    ' + tr(option.description),


                     style=PANEL_MUTED), index)


        if self.context_menu_target:


            # 目标操作：右键/中键选中的格子，与构想同面板展示、同键位激活。


            # 条目在选中空间里排在构想之前（_panel_item_count 的计数口径），


            # 但渲染放在构想之后，▶ 标记与选中序号始终一一对应。


            add(zone_strip(f"{tr('—— 目标操作 ——')} {self.context_menu_target}", width + 4, color=FC['condition']))


            for offset, action in enumerate(self._actions_for(self.context_menu_target)):


                selected = offset == self.panel_selection


                marker = "▶ " if selected else "  "


                add(Text(f"{marker}{tr(action)}", style=FC['condition'] + (" bold underline" if selected else "")), offset)


        if self.pending_confirmation:


            add(Text(tr("该意识属于稳定意识/受控意识，确认攻击？[Y/N]"), style=f"bold {PANEL_DANGER}"))


        if self.pinned_target:


            add(Text(f"{tr('固定观察：')}{self.pinned_target}", style=PANEL_MAGENTA))


        if self.shortcut_targets:


            add(Text(tr("快捷目标：") + tr("、").join(tr(str(item)) for item in self.shortcut_targets[-6:]), style=FC['condition']))


        # Full key reference is opened through the fixed clickable #panel-help.


        add(Text(tr('自动收纳：安全时收纳；有可见失控意识时暂停，携带意象始终手动选择。'), style=PANEL_MUTED))


        return lines, row_indices





    def _fire_actions_lines(self, state: GameState) -> tuple[list[Text], list[int]]:
        """Selectable sources, one current supply block, then contextual controls."""
        from ..core.content import ITEM_DEFINITIONS
        from ..core.firing_sources import collect_firing_sources, equipment_emitters, legacy_basic_view
        from .firing_presentation import equipment_resource_text, reload_status
        sources = collect_firing_sources(state)
        width = max(8, self.query_one('#panel').content_size.width)
        lines, rows = [], []

        def add(value='', index=-1, style=PANEL_MUTED):
            line = value.copy() if isinstance(value, Text) else Text(value, style=style)
            line.truncate(width, overflow='ellipsis')
            lines.append(line)
            rows.append(index)

        def name(source):
            return ' + '.join(tr(LEGACY_BASIC_NAME) if key == LEGACY_BASIC_ID else
                tr(ITEM_DEFINITIONS.get(key, {}).get('name', key))
                for key in source.definition_ids) or tr('聚合弹')

        # Reserve supply and controls before spending short-panel rows on the list.
        compact = self.query_one('#panel').content_size.height < 14
        if not compact:
            add(tr('发射来源'), style=f"bold {FC['word']}")
        if not sources:
            add(tr('尚未解锁任何发射来源。'))
            return lines, rows
        selected = min(max(0, self.panel_selection), len(sources) - 1)
        visible_sources = list(enumerate(sources))
        if compact:
            current = sources[selected]
            reserved = 1 + int(current.kind in ('equipment', 'legacy')) + int(not current.can_fire)
            budget = max(1, self._portent_viewport_rows() - reserved)
            start = min(max(0, selected - budget // 2), max(0, len(sources) - budget))
            visible_sources = visible_sources[start:start + budget]
        for index, source in visible_sources:
            marker = '▶ ' if index == selected else '  '
            suffix = f' ×{source.count}' if source.count is not None else ''
            label = Text(name(source), style=FC['word'])
            label.truncate(max(1, width - 2 - cell_len(suffix)), overflow='ellipsis')
            add(Text.assemble((marker, FC['grammar']), label, (suffix, FC['count'])), index)
        source = sources[selected]
        if not compact:
            add()
            add(tr('当前发射源'), style=f"bold {FC['word']}")
            add(name(source), style=FC['word'])
        if source.kind in ('equipment', 'legacy'):
            add(equipment_resource_text(state, dict(kind=source.action_kind, key=source.choice_key)))
            weapons = ([legacy_basic_view(state)] if source.kind == 'legacy' else
                       equipment_emitters(state, source.action_kind, source.choice_key))
            for item in weapons:
                if item is not None:
                    status, blocked = reload_status(state, item)
                    if status:
                        add(status, style=FC['condition'] if blocked else FC['cooldown'])
                        if compact:
                            break
        else:
            add(tr('余量 {count}', count=source.count), style=FC['count'])
        if not source.can_fire:
            add(tr(source.reason or '当前不可发射'), style=FC['condition'])
        # 键位提示统一放在右栏底部 #panel-help，与完整键位表同处；正文不再
        # 悬浮一行操作提示。
        return lines, rows


    def _tamper_actions_lines(self, state: GameState) -> tuple[list[Text], list[int]]:
        """操作界面·篡改页：编辑器在前就是完整右栏界面，否则只留兜底空状态。

        2026-10-28 玩家定稿：右栏「操作·篡改」就是完整的篡改编辑器（host ==
        'side'，见 ui/tamper_world.py::_world_tamper_side_lines）；提交成功后
        编辑器会按新环境原地重建，不关闭、也不再回退到旧版「简版摘要页」
        （目标/原句/可改写对象那套渲染已移除）。编辑器不在时只说明当前没有
        可改写目标，并保留行 0 的 ``tamper:open`` 重试入口（Enter/左键都能
        重新打开右栏编辑器）。编辑器只是被搬到地图浮层时给一句状态与回栏入口。
        """
        editor = getattr(self, "world_tamper_editor", None)
        if editor is not None and getattr(editor, "host", "map") == "side":
            return self._world_tamper_side_lines(state)
        lines: list[Text] = []
        row_indices: list[int] = []
        width = max(1, self.query_one("#panel").content_size.width - 4)

        def add(line: Text, row_index: int = -1) -> None:
            for wrapped in line.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):
                lines.append(wrapped)
                row_indices.append(row_index)

        if editor is None:
            add(Text(tr("视野里没有可以改写的名字。"), style=PANEL_MUTED))
            add(Text(tr("按 C 打开地图侧篡改面板 / Enter 重试"), style=PANEL_MUTED))
            label = tr("重试：打开篡改界面")
        else:
            add(Text(tr("正在地图侧篡改。"), style=PANEL_MUTED))
            label = tr("回到右栏继续改")
        selected = self.panel_selection == 0
        add(Text(("▶ " if selected else "  ") + label,
                 style=f"bold underline {FC['condition']}" if selected else FC["condition"]), 0)
        return lines, row_indices


    # ---- 征兆面板：全量目录 + 灰注释 + 滚轮/键盘滚动 ----





    def _panel_entry_key(self, index: int) -> str | None:


        """面板内条目序号 → 唯一展开键（与渲染时的键一致）。"""


        if index in (980,981):


            return 'tamper:view' if index == 980 else 'tamper:cancel'


        if (self.panel_mode == "world_tamper"


                or (getattr(self, "world_tamper_editor", None) is not None
                    and self.panel_mode == 'actions' and self._panel_subpage_id() == 'tamper'
                    and getattr(self.world_tamper_editor, "host", "map") == "side")):


            # 行语义序号：0..n-1 = 字词；100+i = 目标槽；100+槽数+i = 条件行


            # （i=0 是「无」）。条件行键统一成 cond:none / cond:n，供


            # ui/tamper_world.py 直接解码，不再借 wslot: 兼容映射。


            editor = self.world_tamper_editor


            word_ids = getattr(editor, "word_ids", ()) if editor else ()


            if index == 900:


                return 'degree:cycle'


            if index == 901:


                return 'details:toggle'


            if index == 903:


                return 'tamper:map'


            if index >= 1000:


                from ..core.tamper_world import condition_ids_for


                singles = tuple(cid for cid in condition_ids_for(editor.sentence, editor.word_id, editor.slot)


                                if cid not in ('gently', 'forcefully'))


                return f'ctoggle:{singles[index - 1000]}' if 0 <= index - 1000 < len(singles) else None


            if index >= 100:


                slot_count = len(editor.sentence.slots) if editor is not None else 0


                offset = index - 100


                if offset < slot_count:


                    return f"wslot:{offset}"


                condition_offset = offset - slot_count


                return "cond:none" if condition_offset == 0 else f"cond:{condition_offset}"


            return f"word:{word_ids[index]}" if 0 <= index < len(word_ids) else None


        state = self.session.state


        if self.panel_mode == "inventory":


            items = state.inventory


            return items[index].instance_id if 0 <= index < len(items) else None


        if self.panel_mode == "equipment":


            # 行映射存的是真实行囊下标：校验该下标确实是携带意象。


            item = state.inventory[index] if 0 <= index < len(state.inventory) else None


            return item.instance_id if item is not None and item.slot else None


        if self.panel_mode == "portents":


            entries = self._portent_entries(state)


            return entries[index]["id"] if 0 <= index < len(entries) else None


        if self.panel_mode == "insights":


            return state.insights[index] if 0 <= index < len(state.insights) else None


        if self.panel_mode == "catalog":


            anomalies = state.visible_anomalies()


            return anomalies[index]["catalog_id"] if 0 <= index < len(anomalies) else None


        if self.panel_mode == "actions":
            page = self._panel_subpage_id()
            if page == "tamper":
                return "tamper:open" if index == 0 else None
            if page == "fire":
                from ..core.firing_sources import collect_firing_sources
                sources = collect_firing_sources(state)
                return f'firing:{sources[index].key}' if 0 <= index < len(sources) else None
            # 构想页：目标操作条目排在构想之前（与渲染/计数同一口径）。
            context = len(self._actions_for(self.context_menu_target)) if self.context_menu_target else 0
            if 0 <= index < context:
                return f"action:{index}"
            abilities = [ability_id for ability_id in state.abilities if ability_id in ABILITY_DEFINITIONS]
            offset = index - context
            if 0 <= offset < len(abilities):
                return f"ability:{abilities[offset]}"
            offset -= len(abilities)
            identity_abilities = state.identity_abilities()
            if 0 <= offset < len(identity_abilities):
                return f'identity:{identity_abilities[offset]}'
            offset -= len(identity_abilities)
            options = state.equipment.active_sentence_options()
            if 0 <= offset < len(options):
                return f'sentence:{options[offset].key}'
            return None
        return None


    def _entry_expanded(self, key: str | None) -> bool:


        """单个条目的注释是否展开：反斜杠键全局开，或该条目被左键单独展开。

        少字模式下即使全局展开也默认收起，只保留玩家手动展开的那一条
        （_terse_details_manual 由输入层在反斜杠键上置位）。
        """


        if self._terse_details_collapsed():


            return key is not None and self.expanded_key == key


        if self.details_expanded:


            return True


        return key is not None and self.expanded_key == key





    # 物品菜单的固定功能行：键位 → (操作名, 会话动作 id)。


    # 主操作（U）随物品变化——携带意象是「携带/卸下」、消耗品是「使用」，见 _item_menu_actions。


    ITEM_MENU_TAIL_ACTIONS = (


        ("D", "放下", "drop"),


        ("Q", "投掷", "throw"),


    )





    def _item_menu_actions(self, item) -> tuple[tuple[str, str, str], ...]:


        """物品菜单的功能行（键位 / 操作名 / 会话动作 id）。





        能上盘的携带意象只有一条 U：打开联想盘编辑器整理（§8.4「从原列表装配」）。


        不能上盘的（记忆槽）仍是「携带/卸下」切换；消耗品是「使用」。


        旧版把「[U] 使用」与「[U] 脱下」并排摆出，穿戴后会同时冒出两个 U 键位，


        而携带意象的「使用」本就没有作用；现在合并为一条，也不再单列 [W] 键。


        """


        state = self.session.state


        if state._placeable_slot(item):


            primary = ("U", "整理联想盘", "board_editor")


        elif item.slot:


            wear_label = "卸下" if item.instance_id in state.equipped.values() else "携带"


            primary = ("U", wear_label, "toggle_equip")


        else:


            primary = ("U", "使用", "toggle_equip")


        extra = ()


        if item.definition_id == "magnesium_match":


            # §14.4.1：投掷点火是主使用，另给出不进入瞄准的原地点燃副动作。


            extra = (("I", "原地点燃", "ignite_here"),)


        if state.adjacent_table() is not None:


            # §14.6：相邻有台面时给出主动放置，不执行撞击载荷。


            extra += (("P", "放到台面", "put_on_table"),)


        return (primary,) + extra + self.ITEM_MENU_TAIL_ACTIONS





    def _item_menu_action_for(self, key: str) -> str | None:


        """把菜单按键或左键点下的动作 id 解析成该物品当前可用的动作。





        只认菜单此刻真实列出的行——没列出的键不能因为字符串恰好相同就执行。


        """


        state = self.session.state


        item = next((entry for entry in state.inventory


                     if entry.instance_id == self.item_menu_target), None)


        if item is None:


            return None


        for menu_key, _label, action_id in self._item_menu_actions(item):


            if key.lower() in (menu_key.lower(), action_id.lower()):


                return action_id


        return None





    def _open_item_menu(self, index: int) -> None:


        """右键行囊条目：打开该物品的左侧菜单（数量/介绍/功能）。"""


        items = self.session.state.inventory


        if 0 <= index < len(items):


            # [SFX] 打开物品菜单。


            if self.config.get("sfx_enabled"):


                sfx.play("ui_click", volume=int(self.config.get("sfx_volume")) / 10)


            self.anomaly_detail_target = None  # 与观测详情互斥：同为左侧覆盖面板


            self.item_menu_target = items[index].instance_id


            self._menu_hover_row = None  # 新菜单从无悬停开始，不继承上一张菜单的行号


            # 选中项必须与右键的那一行一致：携带意象页的 panel_selection


            # 是「列表序号」，行囊页才是真实下标（2026-10-26 玩家反馈：右键


            # 查看物品后选中项跳到别的条目）。


            if self.panel_mode == "equipment":


                equipment_indices = [i for i, entry in enumerate(items) if entry.slot]


                if index in equipment_indices:


                    self.panel_selection = equipment_indices.index(index)


            else:


                self.panel_selection = index


            self.refresh_view()





    def close_item_menu(self) -> None:


        if self.item_menu_target is not None:


            self.item_menu_target = None


            self.refresh_view()





    def _overlay_layout_size(self) -> tuple[int, int]:


        """左侧浮层的外框尺寸上限（2026-10-11 自适应后专用）。





        浮层 CSS 已改 width/height: auto（按内容收缩）——再读它自己的


        content_size 就是「用内容算内容」的自引用（首帧窄、折行崩坏）。


        以 #map-pane 的内容区为基准，保留横向 4 格、纵向 2 格的外部余量。


        对话另按 CSS gutter 扣除真实边框与内距，不能把外框宽度当正文宽度。


        内容较少时浮层仍按 width:auto 收缩。


        """


        try:


            pane = self.query_one("#map-pane")


            return (max(20, pane.content_size.width - 4),


                    max(8, pane.content_size.height - 2))


        except Exception:


            return (44, 12)





    def _item_menu_width(self) -> int:


        """物品菜单（覆盖面板）的内容宽度：描述按它折行，保证一行一映射不串位。"""


        try:


            return self._overlay_layout_size()[0]


        except Exception:


            return self._portent_panel_width()





    def _dialog_content_size(self) -> tuple[int, int]:


        """Predict the dialog's inner bounds without reading its auto-sized content."""


        width, height = self._overlay_layout_size()


        try:


            # This method lays out a dialog even when queried before it opens.


            width = max(1, self.query_one('#map-pane').content_size.width)


            editor = self.tamper_editor


            if editor is not None and editor.dialogue_region is not None:


                width = min(width, editor.dialogue_region.width)


                height = min(height, editor.dialogue_region.height)


        except Exception:


            pass


        try:


            gutter = self.query_one('#map-overlay').styles.gutter


            horizontal, vertical = 4, gutter.height  # dialog padding: 1 1


        except Exception:


            horizontal, vertical = 6, 4  # round border and padding: 1 2


        return max(1, width - horizontal), max(1, height - vertical)





    def _dialog_label_lines(self, label: str, width: int, compact: bool) -> list[str]:


        width = max(1, width - 2)  # reserve the cursor prefix


        if compact:


            text = Text(label)


            text.truncate(width, overflow='ellipsis')


            return [text.plain]


        return self._split_by_width(label, width)





    def _item_menu_text(self, state: GameState) -> Text:
        """左侧物品菜单：数量、介绍与「键位 操作名」功能按钮。

        功能按钮行悬停时叠粗体与下划线（禁止整行反色），与右侧面板视觉一致。
        行映射存入 _menu_rows，功能行的值是会话动作 id，左键点击直接执行。
        映射按**实际正文宽度**逐物理行登记：长介绍被折成两行时也登记两个 -1，
        功能行下标不会漂移。
        """
        item = next(
            (entry for entry in state.inventory if entry.instance_id == self.item_menu_target),
            None,
        )
        width = max(8, self._overlay_content_width())
        logical: list[tuple[Text, int | str]] = [
            (Text.assemble((tr("物品"), f"bold {FC['condition']}")), -1)
        ]
        if item is None:
            logical.append((Text(tr("物品已不在行囊中。"), PANEL_MUTED), -1))
            return self._render_menu_lines(logical, width)

        equipped = " *" if item.instance_id in state.equipped.values() else ""
        name_line = f"{tr(item.name)} ×{item.quantity}{equipped}"
        name_padding = max(0, (width - cell_len(name_line)) // 2)
        name_text = Text(" " * name_padding)
        name_text.append(tr(item.name), style="bold " + item_name_color(item))
        name_text.append(f" ×{item.quantity}", style=FC["count"])
        if equipped:
            name_text.append(equipped, style=FC["effect"])
        logical.append((name_text, -1))

        for chunk in self._split_by_width(_item_description(item, state), max(4, width - 4)):
            logical.append((Text("    " + chunk, style=PANEL_MUTED), -1))
        # 真实发声物品（汽笛／蜂鸣诱饵／带 pulse 的装备）才写发声点与半径。
        for line in _item_sound_lines(state, item):
            for chunk in self._split_by_width(line, max(4, width - 4)):
                logical.append((Text("    " + chunk, style=PANEL_MUTED), -1))

        logical.append((Text(""), -1))  # 空行
        for key, label, action_id in self._item_menu_actions(item):
            logical.append((Text(f"[{key}] {tr(label)}", style=FC["degree"]), action_id))
        return self._render_menu_lines(logical, width)

    def _render_menu_lines(self, logical: list[tuple[Text, int | str]], width: int) -> Text:
        """按正文宽度逐物理行渲染左侧菜单，并同步登记 _menu_rows。"""
        text = Text()
        self._menu_rows = []
        for line, row_value in logical:
            wrapped = line.wrap(_WRAP_CONSOLE, width, overflow="fold", no_wrap=False)
            if not wrapped:
                wrapped = [Text("")]
            for piece in wrapped:
                if text.plain:
                    text.append("\n")
                if isinstance(row_value, str) and self._menu_hover_row == len(self._menu_rows):
                    piece.stylize("bold underline")
                text.append_text(piece)
                self._menu_rows.append(row_value)
        return text


    def activate_item_menu(self, key: str) -> None:


        """执行物品菜单上的功能（左键点按钮行，或按对应键位）。





        功能行的行值就是会话动作 id，左键点击与键盘按键因此走同一条路径。


        主操作随物品变化：能上盘的携带意象走 ``board_editor``（打开联想盘整理），


        其余仍走 ``toggle_equip``——未穿戴则穿上、已穿戴则脱下、无槽消耗品则使用，


        与右侧面板里 Enter/左键同源，不会出现「装得上却脱不下」的半截状态。


        """


        state = self.session.state


        index = next(


            (i for i, entry in enumerate(state.inventory) if entry.instance_id == self.item_menu_target),


            None,


        )


        if index is None:


            self.close_item_menu()


            return


        item = state.inventory[index]


        action_id = self._item_menu_action_for(key) or key.lower()


        if action_id == "board_editor":


            self.close_item_menu()


            self.open_board_editor_for_item(index)


            return


        if action_id == "toggle_equip":


            self._apply("toggle_equip", index)


        elif action_id == "drop":


            self._apply("drop", index)


        elif action_id == "put_on_table":


            # Preserve the chosen adjacent surface through the shared action;


            # the core rechecks visibility, protection and the current item.


            target = self.hover_cell


            if target is not None and state.inside_board(*target) and state.cell(*target).wall_kind in TABLE_KINDS:


                self._apply("put_on_table", index, *target)


            else:


                self._apply("put_on_table", index)


        elif action_id == "throw":


            # 菜单投掷也先「打开投掷选择」，不再沿当前朝向立即扔出（§14 I3）。


            self.close_item_menu()


            self.begin_throw_aim(index)


        elif action_id == "ignite_here":


            self._apply("ignite_here", index)


        elif action_id == "put_on_table":


            self._apply("put_on_table", index)


        if not any(entry.instance_id == self.item_menu_target for entry in state.inventory):


            self.close_item_menu()


        self.refresh_view()





    # ---- 左侧悬浮对话面板（NPC 交易/对话 与 复合事件共用）----





    def _event_dialog_text(self, state: GameState) -> Text:


        """左侧地图上方的悬浮对话面板：上方文字随滚轮/键位滚动，选项固定在底部。





        与物品菜单/格子详情同一块 #map-overlay 浮层；行映射存入


        ``_dialog_rows``（内容行 → 选项序号，-1 = 装饰行），供左键点击


        选项行定位，与右面板 _panel_rows 互不覆盖。


        """


        self._dialog_rows: list[int] = []


        self._dialog_tamper_spans = []


        self._dialog_tamper_line_spans = {}


        width, height = self._dialog_content_size()


        editor = self.tamper_editor


        if editor is not None and editor.phase != 'word':


            # 选好词后让原句留在正文区；暂时收起普通选项，避免窄窗口把槽位挤掉。


            focused = Text()


            obj = state.pending_npc() or state.pending_event()


            title = getattr(obj, 'label', '') or getattr(obj, 'name', '')


            # §9：NPC 标题沿对象身份色，事件标题沿用事件色。


            title_style = (RELATION_STYLES.get(obj.relation, FC['degree'])


                           if obj is state.pending_npc() else PANEL_MAGENTA)


            for title_line in self._split_by_width(tr(title), width)[:1]:


                focused.append(title_line + '\n', style=f'bold {title_style}')


                self._dialog_rows.append(-1)


            lines = self._tamper_original_lines(state, editor.group.text_id, '', width)


            budget = max(1, height - 1)


            anchor = next((index for index, line in enumerate(lines)


                if self._dialog_tamper_line_spans.get(id(line))), 0)


            start = max(0, min(anchor - 1, len(lines) - budget))


            for line in lines[start:start + budget]:


                self._append_tamper_dialog_line(focused, line)


                self._dialog_rows.append(-1)


            return focused


        cursor = getattr(self, "event_dialog_cursor", 0)


        text = Text()


        npc = state.pending_npc()


        if npc is not None:


            from ..core.content import (


                npc_cost_parts,


                npc_definition,


                npc_gain_parts,


                npc_localized_parts,


                npc_option_visible,


                npc_option_key,


                npc_effective_options,


                npc_trade_key,


            )


            from ..core.tamper_views import (


                available_tamper_transitions,


                resolve_tamper_lines,


                target_for_npc,


            )


            definition = npc_definition(npc)


            # 只列**这名 NPC 抽到**的交易项（每次生成抽 2–3 项，见 draw_npc_options）；


            # 没抽到的项不显示也不能交易。


            # 2026-09-19：任务/赠品选项按状态过滤（接了任务隐藏接取项等）。


            options = npc_effective_options(state, npc)


            traded = set(state.npc_traded_options.get(npc_trade_key(npc), ()))


            for line in self._split_by_width(tr(npc.label), width):


                text.append(line + "\n",


                            style=f"bold {RELATION_STYLES.get(npc.relation, FC['degree'])}")


                self._dialog_rows.append(-1)


            from ..core.npc_offers import is_free_claim, free_claims_remaining


            if any(is_free_claim(option) for option in definition.get('options', ())):


                status = tr('免费赠品：还可领取 {n} 项', n=free_claims_remaining(state, npc))


                for line in self._split_by_width(status, width):


                    text.append(line + '\n', style=PANEL_MUTED)


                    self._dialog_rows.append(-1)


            title_lines = len(self._dialog_rows)


            dialogue_lines: list[str] = []


            dialogue = definition.get("dialogue", ())


            if (state.realm_id == 'toy_memories' and state.realm_depth < 4


                    and state.circuit_boards


                    and state.circuit_boards[0].get('variant', 'classic') != 'classic'):


                dialogue = (state.circuit_boards[0]['hint'],)


            for line in dialogue:


                dialogue_lines.extend(self._split_by_width(tr(line), width))


            # 态度先摆在对话第一行（§4.4）：玩家得先看见「这人现在不肯做生意」，


            # 再看见下面的解释／补偿选项，而不是点下去才发现货架空了。


            from ..world import relations


            hint = relations.dialogue_hint(state, npc)


            if hint:


                dialogue_lines = self._split_by_width(tr(hint), width) + dialogue_lines


            # 篡改（规格 §4.1、§8.4）：这名 NPC 开放的对白句按当前已确认变体渲染，


            # 改过的文字与原句同一位置；有可操作位置时才亮出键位入口。


            tamper_target = target_for_npc(state, npc)


            for _text_id, tamper_line in resolve_tamper_lines(state, tamper_target):


                dialogue_lines.extend(self._tamper_original_lines(state, _text_id, tamper_line, width))


            tamper_hint = (self._tamper_hint_line()


                           if available_tamper_transitions(state, tamper_target) else "")





            def trade_detail(option: dict) -> list[Text]:


                """「代价 → 所得」拆两行：逐段 tr()（整句先拼再 tr() 查不到表）。





                两行而不是一行，是因为一行在窄面板上会折成三四行，把选项挤出面板；


                拆开后每行大致一行放得下，占行数也可预期。


                """


                cost = tr("、").join(tr(template, **fields) for template, fields


                                         in npc_localized_parts(npc_cost_parts(option)))


                gain = tr("、").join(tr(template, **fields) for template, fields


                                         in npc_localized_parts(npc_gain_parts(option)))


                result = [Text(tr('代价 {cost}', cost=cost), style=FC['cost']),


                          Text(tr('所得 {gain}', gain=gain), style=FC['effect'])]


                # Only inspect this offer's payload, never scan the whole item


                # catalog each time the dialogue is repainted.


                pending = [option.get('cost', {}), option.get('gain', {})]


                identities = set()


                while pending:


                    value = pending.pop()


                    if isinstance(value, dict):


                        pending.extend(value.keys())


                        pending.extend(value.values())


                    elif isinstance(value, (list, tuple)):


                        pending.extend(value)


                    elif isinstance(value, str) and value in ITEM_DEFINITIONS:


                        identities.add(value)


                for identity in identities:


                    definition = ITEM_DEFINITIONS[identity]


                    for line in result:


                        line.highlight_words([tr(definition['name'])],


                            style=panel_color(definition.get('color') or FC['text']))


                return result





            # 选项固定在最底部：**先把它们的实际占行数算出来**（标签与「代价 →


            # 所得」都会按面板宽度折行，一项可能占 2~4 行），再把剩下的行留给


            # 对话。按「一项一行」估算的话，终端一窄后面的选项就被挤出面板——


            # 它们固定在底部，挤出去就既看不见也点不到。


            # 详情行的取舍：装得下就给**每笔**都摊开代价与所得；装不下（窄终端）


            # 只给光标那一项 —— 任何尺寸下「正在看的那笔」都是透明的。


            usable = height


            # 最近一次选项的结算消息（2026-10-11）：渲染在「交谈」分隔线上方，


            # 占行数计入 fixed——不随对话滚动，选项让行。


            feedback = getattr(self, "_dialog_feedback", None)


            feedback_lines = (self._split_by_width(feedback[1], width)


                              if feedback and feedback[1] else [])


            feedback_style = FC['effect'] if (feedback and feedback[0]) else PANEL_MUTED


            traded_flags = [


                npc_option_key(npc, option) in traded and not option.get("leave") and not option.get('gift_dialogue')


                for option in options


            ]





            def build_blocks(detail_for: set[int], compact: bool = False) -> list[list[str]]:


                blocks: list[list[str]] = []


                for option_index, option in enumerate(options):


                    done = traded_flags[option_index]


                    label = tr(option["label"]) + (tr("（已完成）") if done else "")


                    lines = self._dialog_label_lines(f"{option_index + 1}. {label}", width, compact)


                    if option_index in detail_for and (option.get('cost') or option.get('gain')):


                        for detail_line in trade_detail(option):


                            lines += rich_lines(Text('    ') + detail_line, max(1, width - 2))


                    blocks.append(lines)


                return blocks





            blocks = build_blocks(set(range(len(options))))


            option_budget = max(0, usable - title_lines - 1 - bool(tamper_hint))


            if sum(len(block) for block in blocks) > option_budget:


                blocks = build_blocks({cursor})


            if sum(len(block) for block in blocks) > option_budget:


                blocks = build_blocks({cursor}, compact=True)


            if sum(len(block) for block in blocks) > option_budget:


                blocks = build_blocks(set(), compact=True)


            total_option_lines = sum(len(block) for block in blocks)


            # 选项优先：对话只吃剩下的行，一行都不剩时就不画对话——选项固定在底部，


            # 被挤出去就既看不见也点不到，那才是真的坏。


            feedback_budget = max(0, option_budget - total_option_lines)


            if len(feedback_lines) > feedback_budget:


                feedback_lines = feedback_lines[:feedback_budget]


                if feedback_lines:


                    feedback_lines[-1] = '…'


            fixed_lines = title_lines + 1 + len(feedback_lines) + bool(tamper_hint)


            room = max(0, usable - total_option_lines - fixed_lines)


            help_lines = self._split_by_width(tr("左键首击选中·再击确认 · 数字/Enter 亦可 · Esc 离开"), width)


            show_help = room >= len(help_lines) + 3


            budget = room - (len(help_lines) if show_help else 0)


            offset, visible, show_up, show_down = _dialogue_window(len(dialogue_lines), budget, self.event_dialog_scroll)


            self.event_dialog_scroll = offset


            if budget:


                if show_up:


                    text.append("↑ …\n", style=PANEL_MUTED)


                    self._dialog_rows.append(-1)


                for line in dialogue_lines[offset:offset + visible]:


                    self._append_tamper_dialog_line(text, line)


                    self._dialog_rows.append(-1)


                if show_down:


                    text.append("… ↓\n", style=PANEL_MUTED)


                    self._dialog_rows.append(-1)


            for line in feedback_lines:


                text.append(line + "\n", style=feedback_style)


                self._dialog_rows.append(-1)


            if tamper_hint:


                text.append(tamper_hint + "\n", style=f"bold {FC['condition']}")


                self._dialog_rows.append(TAMPER_ENTRY_ROW)


            text.append("──" + tr("交谈") + "──\n", style=PANEL_MUTED)


            self._dialog_rows.append(-1)


            for option_index, option in enumerate(options):


                marker = "▶ " if option_index == cursor else "  "


                done = traded_flags[option_index]


                if done:


                    # 已完成的一次性交易：置灰提示，仍可选中（选中后 core 拒绝）。


                    style = PANEL_MUTED


                else:


                    style = f"bold {FC['degree']}" if option_index == cursor else FC['condition']


                lines = blocks[option_index]


                self._append_tamper_dialog_line(text, lines[0], prefix=marker, style=style)


                self._dialog_rows.append(option_index)


                for line in lines[1:]:


                    # 折行与「代价 → 所得」都归到同一选项：点它们也选中这一项。


                    text.append_text(line if isinstance(line, Text) else Text(line, style=PANEL_MUTED))


                    text.append('\n')


                    self._dialog_rows.append(option_index)


            if show_help:


                for line in help_lines:


                    text.append(line + '\n', style=PANEL_MUTED)


                    self._dialog_rows.append(-1)


            return text


        event = state.pending_event()


        if event is None:


            text.append(tr("对话已经结束。"), style=PANEL_MUTED)


            self._dialog_rows.append(-1)


            return text


        # 标题带剩余触发次数（2026-09-18）：默认 1，有的更多；归零后地点 resolved、


        # 面板自然再打不开——这里只负责把余量亮出来。


        from ..core.content import event_effective_options


        from ..core.tamper_views import (


            available_tamper_transitions,


            resolve_tamper_lines,


            target_for_event,


        )





        options = event_effective_options(state, event)


        tamper_target = target_for_event(state, event)


        uses_left = max(0, int(getattr(event, "uses_left", 1) or 1))


        title = tr("事件：") + tr(event.name) + tr("　剩余触发次数 {n}", n=uses_left)


        # 可重复操作的面板：ember 阀控与场景设施命令都不消耗「触发次数」，


        # 次数行对它们只会误导。


        repeatable = any(option.get('ember_control') or option.get('scene_command')


                         for option in options)


        if repeatable:


            title = tr("事件：") + tr(event.name) + tr("　可重复操作")


        for line in self._split_by_width(title, width):


            text.append(line + "\n", style=f"bold {PANEL_MAGENTA}")


            self._dialog_rows.append(-1)


        title_lines = len(self._dialog_rows)


        dialogue_lines = []


        if any(option.get('ember_control') for option in options):


            from ..core.realm_challenges import valve_pressure


            dialogue_lines.extend(self._split_by_width(valve_pressure(state, event), width))


        for line in event.dialogue:


            dialogue_lines.extend(self._split_by_width(tr(line), width))


        # 篡改（规格 §8.2）：规则句按当前已确认变体渲染，改文只影响声明过的那一项。


        for _text_id, tamper_line in resolve_tamper_lines(state, tamper_target):


            dialogue_lines.extend(self._tamper_original_lines(state, _text_id, tamper_line, width))


        tamper_hint = (self._tamper_hint_line()


                       if available_tamper_transitions(state, tamper_target) else "")


        if any(option.get('scene_command') for option in options):


            # 设施现状与每条命令的已知条件（world/scenes.describe）：与结算读的


            # 是同一份条件结构，面板不会说一套、结算做一套（§10.1）。


            from ..core.scenes import record_for


            from ..world import scenes as world_scenes





            record = record_for(state, event)


            if record is not None:


                for line in world_scenes.describe(state, record):


                    dialogue_lines.extend(self._split_by_width(line, width))


        # 选项固定在底部：先把选项块（标签 + 每项效果行）的真实占行数算出来，


        # 装不下就降级——先只给光标那项画效果，再不行连效果也不画（键盘照常）。


        from ..core.content import event_option_label, event_option_parts


        usable = height





        def event_effect_lines(option: dict) -> list[str]:


            if option.get('ember_control') or option.get('scene_command'):


                return []


            parts = event_option_parts(option)


            joined = tr("、").join(tr(template, **fields) for template, fields in parts)


            return self._split_by_width("    " + joined, max(1, width - 2))





        def build_event_blocks(detail_for: set[int], compact: bool = False) -> list[list[str]]:


            blocks: list[list[str]] = []


            for option_index, option in enumerate(options):


                label = f"{option_index + 1}. {event_option_label(option)}"


                from ..core.tamper_views import definitions_for_target, _stable_option_id


                editable = next((entry for entry in definitions_for_target(tamper_target)


                    if entry.region == 'option' and entry.option_id ==


                    _stable_option_id(tamper_target, option_index, option)), None)


                if editable is not None and self.tamper_editor is not None and not compact:


                    lines = self._tamper_original_lines(state, editable.text_id,


                                                       label, max(8, width - 2))


                else:


                    lines = self._dialog_label_lines(label, width, compact)


                if option_index in detail_for:


                    lines += event_effect_lines(option)


                blocks.append(lines)


            return blocks





        blocks = build_event_blocks(set(range(len(options))))


        # Reserve readable prose before deciding whether labels need compact


        # rendering. Valve pressure is gameplay state, not optional decoration.


        prose_reserve = min(3, len(dialogue_lines))


        option_budget = max(len(options), usable - title_lines - 1 - bool(tamper_hint) - prose_reserve)


        if sum(len(block) for block in blocks) > option_budget:


            blocks = build_event_blocks({cursor})


        if sum(len(block) for block in blocks) > option_budget:


            blocks = build_event_blocks({cursor}, compact=True)


        if sum(len(block) for block in blocks) > option_budget:


            blocks = build_event_blocks(set(), compact=True)


        total_option_lines = sum(len(block) for block in blocks)


        # 最近一次选项的结算消息（2026-10-11）：渲染在「回应」分隔线上方，


        # 占行数计入 fixed——不随对话滚动，选项让行。


        feedback = getattr(self, "_dialog_feedback", None)


        feedback_lines = (self._split_by_width(feedback[1], width)


                          if feedback and feedback[1] else [])


        feedback_style = FC['effect'] if (feedback and feedback[0]) else PANEL_MUTED


        feedback_budget = max(0, option_budget - total_option_lines)


        if len(feedback_lines) > feedback_budget:


            feedback_lines = feedback_lines[:feedback_budget]


            if feedback_lines:


                feedback_lines[-1] = '…'


        fixed_lines = title_lines + 1 + len(feedback_lines) + bool(tamper_hint)


        room = max(0, usable - total_option_lines - fixed_lines)


        help_lines = self._split_by_width(tr("左键首击选中·再击确认 · 数字/Enter 亦可 · Esc 离开"), width)


        show_help = room >= len(help_lines) + 3


        budget = room - (len(help_lines) if show_help else 0)


        offset, visible, show_up, show_down = _dialogue_window(len(dialogue_lines), budget, self.event_dialog_scroll)


        self.event_dialog_scroll = offset


        if show_up:


            text.append("↑ …\n", style=PANEL_MUTED)


            self._dialog_rows.append(-1)


        for line in dialogue_lines[offset:offset + visible]:


            self._append_tamper_dialog_line(text, line)


            self._dialog_rows.append(-1)


        if show_down:


            text.append("… ↓\n", style=PANEL_MUTED)


            self._dialog_rows.append(-1)


        # 选项固定在底部


        for line in feedback_lines:


            text.append(line + "\n", style=feedback_style)


            self._dialog_rows.append(-1)


        if tamper_hint:


            text.append(tamper_hint + "\n", style=f"bold {FC['condition']}")


            self._dialog_rows.append(TAMPER_ENTRY_ROW)


        text.append("──" + tr("回应") + "──\n", style=PANEL_MUTED)


        self._dialog_rows.append(-1)


        for option_index, option in enumerate(options):


            marker = "▶ " if option_index == cursor else "  "


            style = f"bold {FC['degree']}" if option_index == cursor else FC['condition']


            lines = blocks[option_index]


            self._append_tamper_dialog_line(text, lines[0], prefix=marker, style=style)


            self._dialog_rows.append(option_index)


            for line in lines[1:]:


                # 效果行与标签同属一个选项：点它们也选中这一项。


                self._append_tamper_dialog_line(text, line, style=PANEL_MUTED)


                self._dialog_rows.append(option_index)


        if show_help:


            for line in help_lines:


                text.append(line + '\n', style=PANEL_MUTED)


                self._dialog_rows.append(-1)


        return text





    # ---- 洞察替换（左侧覆盖面板）----





    def open_insight_replace(self, insight_id: str) -> None:


        """洞察已满时打开替换面板：换掉一条已有的，或放弃这条新洞察。





        与物品菜单/意象详情/格子详情同层互斥（都是 #map-overlay 浮层），


        打开时先关掉其它三个，避免叠在一起。


        """


        # [SFX挂点] 洞察槽满弹出替换面板：建议 heal/insight 正向音（治疗传送\heal_1）。


        self.item_menu_target = None


        self.anomaly_detail_target = None


        self.cell_detail_target = None


        self.insight_replace_target = insight_id


        self.insight_replace_cursor = 0


        self.insight_replace_confirm_discard = False


        self.refresh_view()





    def close_insight_replace(self) -> None:


        """关闭替换面板（不动洞察，也不改 pending）——供放弃确认后调用。"""


        if self.insight_replace_target is not None:


            self.insight_replace_target = None


            self.insight_replace_confirm_discard = False


            self.refresh_view()





    def _insight_replace_text(self, state: GameState) -> Text:


        """替换面板正文：新洞察 + 现有洞察列表（光标行 = 将被替换掉的那条）。





        放弃确认态（insight_replace_confirm_discard）覆盖掉列表，只显示


        「确定放弃替换吗？ 是/否」——直接关面板不再等于静默丢弃。


        """


        rows: list[int] = []


        if self.insight_replace_confirm_discard:


            text = Text.assemble((tr("确定放弃替换吗？"), f"bold {PANEL_DANGER}"))


            text.append("\n")


            text.append(tr("Enter / Y = 放弃这次洞察　　其它键 = 返回"), style=PANEL_MUTED)


            self._insight_replace_rows = rows


            return text


        incoming = self.insight_replace_target


        text = Text.assemble(


            (tr("现实洞察已满"), f"bold {PANEL_DANGER}"),


            (f"  {len(state.insights)}/15", FC['text']),


        )


        text.append("\n")


        text.append(tr("获得：") + (tr(incoming) if incoming else "？"), style="bold " + INSIGHT_STYLE)


        text.append("\n")


        text.append(tr("选择一条替换，或按 Esc 放弃这条新洞察："), style=PANEL_MUTED)


        rows.append(-1); rows.append(-1); rows.append(-1)


        for index, insight in enumerate(state.insights):


            selected = index == self.insight_replace_cursor


            marker = "▶ " if selected else "  "


            text.append("\n")


            text.append(


                f"{marker}{tr(insight)}",


                style=INSIGHT_STYLE + (" bold underline" if selected else ""),


            )


            rows.append(index)


            note = INSIGHT_DEFINITIONS.get(insight, "")


            if note:


                for chunk in self._split_by_width(tr(note), max(8, self._item_menu_width() - 6)):


                    text.append("\n    " + chunk, style=PANEL_MUTED)


                    rows.append(-1)


        text.append("\n")


        rows.append(-1)


        text.append(tr("↑↓ 选择 · Enter 替换 · Esc/Q 放弃"), style=PORTENT_HINT_STYLE)


        rows.append(-1)


        self._insight_replace_rows = rows


        return text





    def _max_insight_replace_scroll(self) -> int:


        return 0





    def activate_insight_replace(self) -> None:


        """Enter：确认替换（把光标那条换掉）或确认放弃。"""


        state = self.session.state


        if self.insight_replace_confirm_discard:


            self._apply('discard_pending_insight')


            self.close_insight_replace()


            return


        if not (0 <= self.insight_replace_cursor < len(state.insights)):


            return


        old_id = state.insights[self.insight_replace_cursor]


        new_id = state.pending_insight


        def commit():


            self._apply('replace_pending_insight', old_id)


            self.close_insight_replace()


        self._ask_qol(tr('确认替换现实洞察？'), tr(old_id) + ' → ' + tr(new_id or '') + '\n' + tr('原有洞察会被替换。取消保留待选内容，不消耗行动。'),


            commit, lambda: state.pending_insight == new_id and old_id in state.insights)





    def request_discard_insight(self) -> None:


        """Esc/Q：不直接退出，先切到「确定放弃替换吗？」二次确认。"""


        if self.insight_replace_target is None:


            return


        self.insight_replace_confirm_discard = True


        self.refresh_view()





    def cancel_discard_insight(self) -> None:


        """二次确认里选「否」＝返回替换列表（面板保持打开）。"""


        if self.insight_replace_target is None:


            return


        self.insight_replace_confirm_discard = False


        self.refresh_view()





    def move_insight_replace_cursor(self, delta: int) -> None:


        state = self.session.state


        if not state.insights:


            return


        self.insight_replace_cursor = (


            self.insight_replace_cursor + delta


        ) % len(state.insights)


        self.refresh_view()





    # ---- 记忆碎片替换（左侧覆盖面板，与洞察替换同构）----





    def open_memory_replace(self, memory_id: str) -> None:


        """碎片槽满时打开替换面板：换掉一条已有的，或放弃这条新碎片。





        与洞察替换共用同一套交互骨架（#map-overlay 浮层、光标行、二次确认放弃），


        区别只在数据源是 ``state.memory_fragments``（存 definition id，显示时翻名字）。


        """


        self.item_menu_target = None


        self.anomaly_detail_target = None


        self.cell_detail_target = None


        self.insight_replace_target = None


        self.memory_replace_target = memory_id


        self.memory_replace_cursor = 0


        self.memory_replace_confirm_discard = False


        self.refresh_view()





    def close_memory_replace(self) -> None:


        """关闭替换面板（不动碎片，也不改 pending）——供放弃确认后调用。"""


        if self.memory_replace_target is not None:


            self.memory_replace_target = None


            self.memory_replace_confirm_discard = False


            self.refresh_view()





    def _memory_pending_name(self, memory_id: str) -> str:


        """碎片 id → 显示名（面板正文里不出现内部 id）。"""


        return tr(ITEM_DEFINITIONS.get(memory_id, {}).get("name", memory_id))





    def _memory_effect_short(self, memory_id: str) -> str:


        """碎片的「一句效果」——取效果表的 short 字段（没有就退回 detail 首句）。"""


        effect_name = ITEM_DEFINITIONS.get(memory_id, {}).get("memory_effect")


        effect = MEMORY_FRAGMENT_EFFECTS.get(effect_name or "")


        if not effect:


            return ""


        return tr(str(effect.get("short", "")))





    def _memory_replace_text(self, state: GameState) -> Text:


        """替换面板正文：新碎片 + 现有碎片列表（光标行 = 将被替换掉的那条）。"""


        rows: list[int] = []


        if self.memory_replace_confirm_discard:


            text = Text.assemble((tr("确定放弃替换吗？"), f"bold {PANEL_DANGER}"))


            text.append("\n")


            text.append(tr("Enter / Y = 放弃这片碎片　　其它键 = 返回"), style=PANEL_MUTED)


            self._memory_replace_rows = rows


            return text


        incoming = self.memory_replace_target


        text = Text.assemble(


            (tr("记忆碎片已满"), f"bold {PANEL_DANGER}"),


            (f"  {len(state.memory_fragments)}/{MEMORY_LIMIT + state._memory_slot_bonus()}", FC['text']),


        )


        text.append("\n")


        text.append(tr("获得：") + (self._memory_pending_name(incoming) if incoming else "？"), style=f"bold {FC['effect']}")


        short = self._memory_effect_short(incoming) if incoming else ""


        if short:


            text.append(f"（{short}）", style=PANEL_MUTED)


        text.append("\n")


        text.append(tr("选择一片替换，或按 Esc 放弃这片新碎片："), style=PANEL_MUTED)


        rows.append(-1); rows.append(-1); rows.append(-1)


        for index, memory_id in enumerate(state.memory_fragments):


            selected = index == self.memory_replace_cursor


            marker = "▶ " if selected else "  "


            text.append("\n")


            text.append(


                f"{marker}{self._memory_pending_name(memory_id)}",


                style=FC['effect'] + (" bold underline" if selected else ""),


            )


            rows.append(index)


            own_short = self._memory_effect_short(memory_id)


            if own_short:


                text.append(f"  {own_short}", style=PANEL_MUTED)


        text.append("\n")


        rows.append(-1)


        text.append(tr("↑↓ 选择 · Enter 替换 · Esc/Q 放弃"), style=PORTENT_HINT_STYLE)


        rows.append(-1)


        self._memory_replace_rows = rows


        return text





    def activate_memory_replace(self) -> None:


        """Enter：确认替换（把光标那条换掉）或确认放弃。"""


        state = self.session.state


        if self.memory_replace_confirm_discard:


            self._apply('discard_pending_memory')


            self.close_memory_replace()


            return


        if not (0 <= self.memory_replace_cursor < len(state.memory_fragments)):


            return


        old_id = state.memory_fragments[self.memory_replace_cursor]


        new_id = state.pending_memory


        def commit():


            self._apply('replace_pending_memory', old_id)


            self.close_memory_replace()


        self._ask_qol(tr('确认替换记忆碎片？'), self._memory_pending_name(old_id) + ' → ' + self._memory_pending_name(new_id or '') + '\n' + tr('原有碎片及其效果会被替换。取消保留待选内容，不消耗行动。'),


            commit, lambda: state.pending_memory == new_id and old_id in state.memory_fragments)





    def request_discard_memory(self) -> None:


        """Esc/Q：不直接退出，先切到「确定放弃替换吗？」二次确认。"""


        if self.memory_replace_target is None:


            return


        self.memory_replace_confirm_discard = True


        self.refresh_view()





    def cancel_discard_memory(self) -> None:


        """二次确认里选「否」＝返回替换列表（面板保持打开）。"""


        if self.memory_replace_target is None:


            return


        self.memory_replace_confirm_discard = False


        self.refresh_view()





    def move_memory_replace_cursor(self, delta: int) -> None:


        state = self.session.state


        if not state.memory_fragments:


            return


        self.memory_replace_cursor = (


            self.memory_replace_cursor + delta


        ) % len(state.memory_fragments)


        self.refresh_view()





    def _panel_scroll_hint(self, first: int, last: int, total: int) -> str:


        """Keep the footer on its own physical row, including narrow English panels.


        2026-10-24 纸感分区：滚动提示改「细牛皮条」——调用方以 SCROLL_HINT_STYLE
        （muted 字 + 通栏 ZONE_STRIP 底）附加样式，这里用 paper_pad 把物理行
        pad 满行宽。只补尾部空格：行数不变、列起点不变，行命中映射照旧。
        """


        if self._world_tamper_side_active():
            # 右栏篡改页的 ↑↓ 是选字词，不是滚动；提示必须说这一页真能用的键。
            hint = tr("第 {a}-{b}/{c} 行 · 滚轮或 PgUp/PgDn 滚动").format(a=first, b=last, c=total)
        else:
            hint = tr("第 {a}-{b}/{c} 行 · 滚轮或 ↑↓ 滚动").format(a=first, b=last, c=total)


        width = self._portent_panel_width()


        if cell_len(hint) > width:


            hint = f"{first}-{last}/{total} · ↑↓"


        line = Text(hint)


        line.truncate(width, overflow="ellipsis")


        return "\n" + paper_pad(line, ZONE_STRIP, width).plain





    def _portent_viewport_rows(self) -> int:


        """征兆面板可用内容行数：扣掉标题行与底部提示行。"""


        try:


            height = self.query_one("#panel").content_size.height


        except Exception:


            return 0


        return max(1, height - 2)





    def _portent_panel_width(self) -> int:


        try:


            return max(8, self.query_one("#panel").content_size.width)


        except Exception:


            return 40





    def _portent_entries(self, state: GameState) -> list[dict[str, Any]]:
        """Render active state, retaining runtime counts/effects over catalog defaults."""
        entries: list[dict[str, Any]] = []
        for entry in state.active_portents():
            pid = entry["id"]
            definition = PORTENT_DEFINITIONS.get(pid)
            # Modem phases are finite item timers, not material-granted portents.
            if definition is None and pid not in {"modem_buffer", "modem_recovery", "drug_mind_debt"}:
                continue
            entries.append({
                "id": pid,
                "name": entry.get("name") or definition.name,
                "kind": entry.get("kind") or definition.kind,
                "effect": entry.get("effect") or definition.effect,
                "remaining": int(entry.get("remaining", 0) or 0),
                "stacks": int(entry.get("stacks", 0) or 0),
            })
        entries.sort(key=lambda entry: entry["name"])
        return entries

    def _portent_layout(self, state: GameState) -> tuple[list[Text], list[int], int]:


        """把征兆目录排成行：返回（行列表, 每条起始行, 总行数），供分页滚动使用。"""


        entries = self._portent_entries(state)


        width = self._portent_panel_width()


        lines: list[Text] = []


        starts: list[int] = []


        for index, entry in enumerate(entries):


            starts.append(len(lines))


            selected = index == self.panel_selection


            head = Text("▶ " if selected else "  ", style=PORTENT_HINT_STYLE)


            # 语义图标只在游戏专用 WezTerm 配置中启用；普通终端/测试保持文字回退。


            from ..data.semantic_icons import portent_icon


            icon = portent_icon(entry["id"])


            if icon:


                icon_style = {'modem_buffer': FC['effect'], 'modem_recovery': FC['cost'],
                              'drug_mind_debt': FC['risk']}.get(entry['id'], PORTENT_STYLE)
                head.append(icon, style=icon_style + (" bold underline" if selected else ""))


            # 名称一律用按钮同款紫色；性质、层数、回合、效果说明都用灰色注释。


            head.append(tr(entry["name"]), style=PORTENT_STYLE + (" bold underline" if selected else ""))


            kind_color = FC['risk'] if entry['kind'] == '负面' else FC['effect'] if entry['kind'] == '正面' else FC['label']


            head.append(f"  {tr(entry['kind'])}", style=kind_color)


            # 层在前、回合在后；各自为 0 就不写（条件/范围/永久触发的征兆两个都不写）。


            if entry["stacks"]:


                head.append(f"  · {entry['stacks']} {tr('层')}", style=FC['count'])


            if entry["remaining"]:


                head.append(f"  · {entry['remaining']} {tr('回合')}", style=FC['duration'])


            lines.append(head)


            if self._entry_expanded(entry["id"]):


                for chunk in self._split_by_width(tr(entry["effect"]), max(8, width - 4)):


                    lines.append(Text("    " + chunk, style=FC['label']))


        return lines, starts, len(lines)





    def _observations_layout(


        self, state: GameState, anomalies: list[dict[str, Any]], width: int


    ) -> tuple[list[Text], list[int], int]:


        """把视野内失控意识排成行，供分页滚动使用。





        顺序固定为：名称 × 数量 → 介绍（仅在展开时显示，灰色注释）→ 种类（例：


        普通异象）→ 属性行（每个属性一个颜色）→ 空行。类别标签排在介绍之后，


        属性行不再混入类别，避免"种类"被当成一个数值属性。


        """


        lines: list[Text] = []


        starts: list[int] = []


        for index, entry in enumerate(anomalies):


            starts.append(len(lines))


            selected = index == self.panel_selection


            prefix = "▶ " if selected else "  "


            head = Text(prefix + entry['name'], style=FC['degree'] + (' bold underline' if selected else ''))


            head.append(f" ×{entry['count']}", style=FC['count'])


            lines.append(head)


            # 运行时技能状态（2026-10-10）：不折叠，一眼看到「它现在是不是


            # 在冷却、最早几回合后再放技能」。聚合条目按种类合并——蓄势取


            # 最急的一个，等待取最长（同类多个体的口径写在 visible_anomalies）。


            status = entry.get("status")


            if status:


                if status.get("charging"):


                    lines.append(Text(


                        "    " + tr("技能 蓄势中：「{skill}」剩 {n} 回合").format(


                            skill=tr(status["charging_name"]), n=status["windup_left"]),


                        style=FC['condition'],


                    ))


                elif status.get("cooldown_left"):


                    lines.append(Text(


                        "    " + tr("技能 冷却中：最早 {n} 回合后再起手").format(n=status["cooldown_left"]),


                        style=FC['condition'],


                    ))


            if entry.get("description") and self._entry_expanded(entry["catalog_id"]):


                for chunk in self._split_by_width(entry["description"], max(8, width - 4)):


                    lines.append(Text("    " + chunk, style=PANEL_MUTED))


            # 主动技能数值（创伤/冷却/蓄势/持续/恢复/距离）与效果/条件


            # 注释：与介绍同规矩，仅在展开时显示，默认收起——观测首屏仍以


            # 耐久/伤害等硬属性为主。


            if entry.get("skills") and self._entry_expanded(entry["catalog_id"]):


                for summary in entry["skills"]:


                    lines.append(Text('    ') + _skill_summary_rich(summary))


                    lines.extend(self._skill_detail_lines(summary, width, indent="      "))


            lines.append(Text("    " + str(entry.get("kind", "")), style=OBSERVATION_KIND_COLOR))


            lines.extend(self._observation_attribute_lines(entry, width))


            lines.append(Text(""))  # 条目间留一空行


        return lines, starts, len(lines)





    @staticmethod


    def _observation_attribute_lines(entry: dict[str, Any], width: int) -> list[Text]:


        """属性行：耐久 / 伤害 / 攻速 / 移动 / 视野 / 创伤，各自一个颜色。





        「攻击」在观测里曾是一串攻击耗时——那是攻速而非伤害，容易误读；


        现在伤害与攻速分开列：伤害 = 每次出手扣掉的心智/清醒点数，


        攻速 = 两次出手之间的间隔（数字越小越快）。太长时按宽度折行。


        """


        attributes = (


            ("耐久", entry.get("integrity")),


            ("伤害", entry.get("damage")),


            ("攻速", entry.get("attack_speed")),


            ("移动", entry.get("move_time")),


            ("视野", entry.get("vision")),


            ("创伤", entry.get("trauma")),


        )


        return _attribute_lines(attributes, max(8, width - 4))





    # ---- 观测详情（左侧覆盖面板）：右键观测条目中的意象名打开 ----





    def _open_anomaly_detail(self, index: int) -> None:


        """右键观测面板中的意象条目：在左侧覆盖面板逐个体展开它的信息。





        观测面板按「种类」聚合（纸页犬 ×3）；详情面板则按「个体」展开——


        同一名的每个异象单列一份完整度与征兆，因此能一眼看出群体里谁受了伤、


        谁被环境染上了什么（同名不代表同样的状态）。


        """


        anomalies = self.session.state.visible_anomalies()


        if not (0 <= index < len(anomalies)):


            return


        self.item_menu_target = None  # 与物品菜单互斥：同为左侧覆盖面板


        self.anomaly_detail_target = anomalies[index]["catalog_id"]


        self.panel_selection = index


        self.detail_cursor = 0


        self.detail_scroll = 0


        self.refresh_view()





    def close_anomaly_detail(self) -> None:


        if self.anomaly_detail_target is not None:


            self.anomaly_detail_target = None


            self.detail_cursor = 0


            self.detail_scroll = 0


            self._detail_line_count = 0


            self._detail_selectable = []


            # 从格子详情 Enter 进来的子详情：回到本格、原滚动位置与原选中行


            # （docs §16.5），不把玩家扔回地图重新找一个格子。


            restore = self.cell_detail_return


            if restore is not None:


                self.cell_detail_return = None


                self.cell_detail_target = restore[0]


                self.detail_cursor = restore[1]


                self.detail_scroll = restore[2]


            self.refresh_view()





    def _skill_detail_lines(


        self, summary: dict[str, Any], width: int, indent: str = "      ", style: str = PANEL_MUTED


    ) -> list[Text]:


        """技能说明段：效果与条件合成一段不带标签的普通句子（按宽度折行）。





        两段文本来自 data.anomaly_skills 的 SkillDef（xlsx 导入的完整效果/


        合法施放条件），缺失段直接跳过；观测面板、观测详情与格子详情共用


        同一套排版。**「玩家反制」段已按玩家要求移除（2026-10-12）**：


        反制思路属于剧透，图鉴详情不再展示。主梦文本使用审读后的玩家说明；


        英文显示已有的翻译，缺翻译的专属内容暂时跳过该段。


        """


        lines: list[Text] = []


        sentences: list[str] = []


        for key in ("effect_text", "condition_text"):


            text = str(summary.get(key, "") or "").strip()


            if not text:


                continue


            translated = tr(text)


            if get_language() != 'zh' and translated == text:


                continue


            if get_language() != 'zh':


                if translated[-1] not in ".!?":


                    translated += "."


                sentences.append(translated)


            else:


                if translated[-1] not in "。！？；":


                    translated += "。"


                sentences.append(translated)


        joined = " ".join(sentences) if get_language() != 'zh' else "".join(sentences)


        if joined:


            for chunk in self._split_by_width(joined, max(8, width - 6)):


                lines.append(Text(indent + chunk, style=style))


        return lines





    def _anomaly_detail_instances(self, state: GameState) -> list[dict[str, Any]]:


        """当前视野内所有同名异象的逐个体快照（按坐标排序，顺序稳定）。"""


        catalog_id = self.anomaly_detail_target


        if not catalog_id:


            return []


        definition = current_anomaly_definition(state, catalog_id)


        base_integrity = int(definition.get("integrity", 1) or 1)


        revealed = state.reveals_anomalies


        instances: list[dict[str, Any]] = []


        for enemy in state.enemies:


            if enemy.integrity <= 0 or enemy.catalog_id != catalog_id:


                continue


            # 与观测面板同一条可见性规则：诅咒灵视下视野外也照样列出。


            if not revealed and not state.is_visible(enemy.x, enemy.y):


                continue


            portents: list[dict[str, Any]] = []


            for portent_id in enemy.portents:


                portent = PORTENT_DEFINITIONS.get(portent_id)


                if portent is None:


                    continue


                portents.append({


                    "name": portent.name,


                    "kind": portent.kind,


                    "effect": portent.effect,


                    "remaining": state.portent_remaining(enemy, portent_id),


                })


            portents.sort(key=lambda entry: entry["name"])


            instances.append({


                "label": enemy.label,


                "x": enemy.x,


                "y": enemy.y,


                "integrity": int(enemy.integrity),


                # 上限取定义值（衍生个体如分裂残影也一样），实体超出时以实体为准。


                "max_integrity": max(base_integrity, int(enemy.integrity)),


                # 警戒状态（未察觉/怀疑/警戒/追踪）——配合「失去目标」降级一起看。


                "alert": enemy.alert_state,


                "portents": portents,


                # 主动技能运行时状态（蓄势中/冷却剩余回合数，2026-10-10）。


                "status": state.skill_cooldown_status(enemy),


            })


        instances.sort(key=lambda entry: (entry["y"], entry["x"]))


        return instances





    def _anomaly_definition_lines(


        self, definition: dict[str, Any], limit: int, skills: Any = ()


    ) -> list[Text]:


        """定义级属性行（不含耐久——耐久按个体以「完整度 n/m」呈现）。





        ``skills`` 是 data.anomaly_skills.skill_summaries_for 的观测摘要：


        每个绑定技能一行数值（创伤/冷却/蓄势/持续/恢复/距离），其下按宽度


        折行补「效果/条件」两段注释；有主动绑定时不追加已经停用的旧技能说明。


        """


        attributes = (


            ("伤害", int(definition.get("damage", 1) or 1)),


            ("攻速", definition.get("attack_time", 1.0)),


            ("移动", definition.get("move_time", 1.0)),


            ("视野", definition.get("vision", 6)),


            ("创伤", tr(definition.get("trauma_type", ""))),


        )


        lines = _attribute_lines(attributes, limit, indent="  ")


        if skills:


            for summary in skills:


                lines.append(Text('  ') + _skill_summary_rich(summary))


                lines.extend(self._skill_detail_lines(summary, limit, indent="    ", style=PANEL_MUTED))


        else:


            # 兜底：无数据层绑定时保留旧的整段文本行（2026-09-19 行为）。


            skill = definition.get("skill")


            if skill:


                name, _, detail = str(skill).partition("｜")


                lines.append(Text("  " + tr("技能 ") + tr(name) + "：" + tr(detail), style=FC['condition']))


        passive = definition.get("passive")


        if passive:


            name, _, detail = str(passive).partition("｜")


            lines.append(Text("  " + tr("特性 ") + tr(name) + "：" + tr(detail), style=PANEL_MAGENTA))


        return lines





    def _overlay_content_width(self) -> int:
        """左侧浮层的**正文**可用列数。

        旧实现返回 ``_overlay_layout_size()[0]``（外框上限），比真实正文宽了
        边框 2 列 + 左右内边距 4 列。按外框宽度预折行后，Textual 还会再折一次，
        可视行数比逻辑行数多，鼠标行→对象就整体错位（2026-10-26 玩家反馈：
        左侧悬浮页鼠标位置和选中项对不上）。这里直接按 #map-pane 内容宽扣掉
        浮层 gutter，返回真正能放下文字的列数。
        """
        if getattr(self, '_inspection_full_cell', False):
            width = self.query_one('#signal-detail-text').content_size.width
            scroll_width = self.query_one('#signal-detail-scroll').content_size.width
            if width and scroll_width:
                # Reserve the vertical scrollbar before Textual decides that
                # the newly rendered full detail needs it, avoiding reflow drift.
                return max(8, min(width, scroll_width - 1))
        try:
            pane = self.query_one('#map-pane')
            pane_width = pane.content_size.width
            if pane_width > 0:
                # 非对话浮层：round 边框 2 列 + padding 左右各 2 列 = 6 列 gutter。
                # _fit_map_overlay 把外框上限钳在 pane_width - 4，正文即再减 6。
                return max(8, pane_width - 10)
        except Exception:
            pass
        try:
            return max(8, self._overlay_layout_size()[0] - 6)
        except Exception:
            return max(8, self._portent_panel_width() - 6)


    def _anomaly_detail_viewport(self) -> int:


        """覆盖面板可用内容行数：扣掉底部一行滚动提示。"""


        return max(1, self._overlay_layout_size()[1] - 1)





    def _anomaly_detail_text(self, state: GameState) -> Text:


        """左侧异象详情：定义级信息一次，逐个体完整度与征兆各一份。"""


        catalog_id = self.anomaly_detail_target


        if not catalog_id:


            self._detail_line_count = 1


            self._detail_selectable = [False]


            return Text(tr("未选择意象。"), PANEL_MUTED)


        definition = ANOMALY_DEFINITIONS.get(catalog_id, {})


        instances = self._anomaly_detail_instances(state)


        name = tr(definition.get("name", catalog_id))


        width = self._overlay_content_width()


        lines: list[Text] = []


        selectable: list[bool] = []





        title = Text()


        title.append(tr("观测详情"), style=f"bold {FC['degree']}")


        title.append(f"  {name} ×{len(instances)}", style=FC['degree'])


        lines.append(title); selectable.append(False)





        kind_line = Text("  ")


        kind_line.append(tr(definition.get("anomaly_kind", "")), style=OBSERVATION_KIND_COLOR)


        lines.append(kind_line); selectable.append(False)


        # 属性行：随覆盖面板宽度折行（窄面板下不再溢出被裁掉）。


        # 技能摘要按当前层算创伤值（同层异象，值即实战值）。


        for attribute_line in self._anomaly_definition_lines(


            current_anomaly_definition(state, catalog_id), max(8, width - 2),
            skills=current_skill_summaries(state, catalog_id)


        ):


            lines.append(attribute_line); selectable.append(False)





        description = tr(definition.get("description", ""))


        if description and self._details_visible():


            # 介绍与观测面板同规矩：归在「注释」里，\ 键展开时才出现，


            # 默认视图优先给逐个体的完整度与征兆。


            for chunk in self._split_by_width(description, max(8, width - 2)):


                lines.append(Text("  " + chunk, style=PANEL_MUTED)); selectable.append(False)


        lines.append(Text("")); selectable.append(False)





        if not instances:


            lines.append(Text("  " + tr("该意象此刻不在视野中。"), PANEL_MUTED))


            selectable.append(False)


        for order, instance in enumerate(instances, start=1):


            marker = _CIRCLED_NUMBERS[order - 1] if order <= len(_CIRCLED_NUMBERS) else f"#{order}"


            head = Text()


            head.append("▍", style=FC['degree'])


            head.append(f"{name} {marker}", style=f"bold {FC['text']}")


            head.append(f"  ({instance['x']},{instance['y']})", style=PANEL_MUTED)


            lines.append(head); selectable.append(True)





            integrity, maximum = instance["integrity"], instance["max_integrity"]


            integrity_line = Text("   ")


            integrity_line.append(tr("完整度") + " ", style=PANEL_MUTED)


            integrity_line.append(


                f"{integrity}/{maximum}",


                style=PANEL_DANGER if integrity * 2 <= maximum else FC['effect'],


            )


            integrity_line.append(" · " + tr("状态") + " ", style=PANEL_MUTED)


            integrity_line.append(tr(instance["alert"]), style=ALERT_STYLES.get(instance["alert"], PANEL_MUTED))


            lines.append(integrity_line); selectable.append(True)





            # 主动技能运行时状态（2026-10-10）：逐个体写，谁在蓄势/谁在


            # 等冷却一眼分清——蓄力中的异象不普攻不移动，是玩家下决断的


            # 关键读数；等待值是「最早再起手」的下界（各技能独立 CD）。


            status = instance.get("status") or {}


            if status.get("charging"):


                status_line = Text("   ")


                status_line.append(tr("技能 "), style=PANEL_MUTED)


                status_line.append(


                    tr("蓄势中：「{skill}」剩 {n} 回合").format(


                        skill=tr(status["charging_name"]), n=status["windup_left"]


                    ),


                    style=FC['condition'],


                )


                lines.append(status_line); selectable.append(True)


            elif status.get("cooldown_left"):


                status_line = Text("   ")


                status_line.append(tr("技能 "), style=PANEL_MUTED)


                status_line.append(


                    tr("冷却中：最早 {n} 回合后再起手").format(n=status["cooldown_left"]),


                    style=FC['condition'],


                )


                lines.append(status_line); selectable.append(True)





            if instance["portents"]:


                for position, portent in enumerate(instance["portents"]):


                    entry = Text("   ")


                    entry.append((tr("征兆") if position == 0 else "　　　") + " ", style=PANEL_MUTED)


                    entry.append(tr(portent["name"]), style=PORTENT_STYLE)


                    entry.append(tr('（{n} 回合）', n=portent['remaining']),
                                 style=PANEL_MUTED)


                    lines.append(entry); selectable.append(True)


                    if self._details_visible():


                        for chunk in self._split_by_width(tr(portent["effect"]), max(8, width - 8)):


                            lines.append(Text("        " + chunk, style=PANEL_MUTED)); selectable.append(False)


            else:


                empty = Text("   ")


                empty.append(tr("征兆") + " ", style=PANEL_MUTED)


                empty.append(tr("无"), style=PANEL_MUTED)


                lines.append(empty); selectable.append(True)


            lines.append(Text("")); selectable.append(False)





        # 长行会由 Textual 在浮层里再折成多个物理行；先把物理行显式摊平，
        # 否则 _detail_line_count 比实际显示行少，鼠标行→条目整体错位。
        physical_lines: list[Text] = []
        physical_selectable: list[bool] = []
        for line, selected in zip(lines, selectable):
            wrapped = rich_lines(line, max(8, width)) or [Text("")]
            physical_lines.extend(wrapped)
            physical_selectable.extend([selected] * len(wrapped))
        lines, selectable = physical_lines, physical_selectable

        self._detail_line_count = len(lines)


        self._detail_selectable = selectable


        viewport = self._anomaly_detail_viewport()


        self.detail_scroll = min(max(0, self.detail_scroll), max(0, len(lines) - viewport))


        low = self.detail_scroll


        high = min(low + viewport - 1, max(0, len(lines) - 1))


        # 光标始终落在视窗内的可选行上（标题/介绍/空行不可选）；


        # 越出视窗或落在装饰行时，就近吸附到窗口内最近的可选行。


        if not (low <= self.detail_cursor <= high) or not selectable[self.detail_cursor]:


            window = [index for index in range(low, high + 1) if selectable[index]]


            self.detail_cursor = (


                min(window, key=lambda index: (abs(index - self.detail_cursor), index))


                if window else low


            )


        start = self.detail_scroll


        text = Text()


        for offset, line in enumerate(lines[start:start + viewport]):


            if offset:


                text.append("\n")


            if start + offset == self.detail_cursor:


                line.stylize("bold underline")


            text.append_text(line)


        text.append("\n")


        if len(lines) > viewport:


            last = min(len(lines), start + viewport)


            text.append(


                tr("第 {a}-{b}/{c} 行 · 滚轮或 ↑↓ 滚动 · Q/Esc 关闭").format(a=start + 1, b=last, c=len(lines)),


                style=PORTENT_HINT_STYLE,


            )


        else:


            text.append(tr("滚轮或 ↑↓ 滚动 · Q/Esc 关闭"), style=PORTENT_HINT_STYLE)


        return text





    def _follow_anomaly_detail(self) -> None:


        """把光标所在行滚进视窗（键盘滑动）。"""


        viewport = self._anomaly_detail_viewport()


        if self.detail_cursor < self.detail_scroll:


            self.detail_scroll = self.detail_cursor


        elif self.detail_cursor >= self.detail_scroll + viewport:


            self.detail_scroll = self.detail_cursor - viewport + 1





    def _move_anomaly_detail(self, delta: int) -> None:


        """↑↓ 在可选字段间移动光标（跳过介绍/空行），并随之滚动。"""


        selectable = [index for index, ok in enumerate(self._detail_selectable) if ok]


        if not selectable:


            return


        if self.detail_cursor in selectable:


            position = selectable.index(self.detail_cursor)


        else:


            position = 0


        position = min(max(0, position + delta), len(selectable) - 1)


        self.detail_cursor = selectable[position]


        self._follow_anomaly_detail()


        self.refresh_view()





    def _scroll_anomaly_detail(self, amount: int) -> None:


        """滚轮 / 翻页：只滑动视窗；光标越出视窗时由渲染就近吸附回窗口内。"""


        viewport = self._anomaly_detail_viewport()


        total = max(1, self._detail_line_count)


        self.detail_scroll = min(max(0, total - viewport), max(0, self.detail_scroll - amount))


        self.refresh_view()





    # ---- 格子详情（左侧覆盖面板）：右键格子或观察模式按 ' 打开 ----





    def open_cell_detail(self, target: tuple[int, int]) -> None:


        """打开某一格的完整信息面板（与物品菜单/意象详情互斥的左侧覆盖面板）。"""


        state = self.session.state


        if not (0 <= target[0] < state.width and 0 <= target[1] < state.height):


            return


        self.item_menu_target = None


        self.anomaly_detail_target = None


        self.cell_detail_target = target


        self.cell_detail_return = None


        self.detail_cursor = 0


        self.detail_scroll = 0


        self.refresh_view()





    def close_cell_detail(self) -> None:


        if self.cell_detail_target is not None:


            self.cell_detail_target = None


            self.cell_detail_return = None


            self.detail_cursor = 0


            self.detail_scroll = 0


            self._detail_line_count = 0


            self._detail_selectable = []


            self.refresh_view()





    # ---- 拾取面板（左侧覆盖面板）：本格有多件显化物时勾选拾取 ----





    def open_pickup(self, target: tuple[int, int]) -> None:


        """打开「本格可拾取物」面板：空格勾选、Enter 一起捡起。





        只在目标格真有 ≥1 件可拾取物时才开——单件直接捡更省事（调用方负责


        判断），空列表开一个空面板只会打扰玩家。


        与其它左侧覆盖面板互斥；默认全不勾选，玩家自己决定拿哪几件。


        """


        state = self.session.state


        if not state.can_collect_at(*target) or not self.pickup_candidates(*target):


            return


        self.item_menu_target = None


        self.anomaly_detail_target = None


        self.cell_detail_target = None


        self.insight_replace_target = None


        self.memory_replace_target = None


        self.pickup_target = target
        # 2026-10-28：拾取面板是左侧覆盖面板，打开即把键盘焦点交给它。
        # 旧实现只设 pickup_target 不改 cursor_zone；焦点仍在地图时，下一次
        # G/↑↓ 会先被「面板之外的按键只关面板」兜底吃掉，面板看起来按键无反应。
        self.cursor_zone = 'overlay'


        self.pickup_picked = set()


        self.pickup_cursor = 0


        self.pickup_scroll = 0


        self._pickup_snapshot=tuple(e.item.instance_id for e in self.pickup_candidates(*target))


        self.refresh_view()





    def close_pickup(self) -> None:


        if self.pickup_target is not None:


            self.pickup_target = None


            self.pickup_picked = set()


            self.pickup_cursor = 0


            self.pickup_scroll = 0


            self.refresh_view()





    def try_pickup(self, target: tuple[int, int] | None = None) -> None:


        """「尝试拾取」统一入口（左键点自己那格 / G 键 / 右键菜单「拾取」）。





        玩家明确要求：**本格有多件时**先开勾选面板（空格多选、Enter 一起捡）；


        只有一件时直接捡——为一件开面板纯属多余。


        拾取面板已经开着时再按 G：不外开，直接结算（＝把面板里的勾选捡起来），


        免得 G 在面板打开时反而被面板吞掉、变成什么都不做。


        """


        state = self.session.state


        if target is None:


            target = (state.player.x, state.player.y)


            if not self.pickup_candidates(*target):


                target=state.adjacent_table_with_item() or target


        if self.pickup_target is not None:


            self.activate_pickup()


            return


        if not state.can_collect_at(*target):


            return


        if len(self.pickup_candidates(*target)) > 1:


            self.open_pickup(target)


            return


        entries=self.pickup_candidates(*target)


        if entries:


            self._apply("collect_items",state.world_items.index(entries[0]))


        elif target==(state.player.x,state.player.y):


            self._apply("pickup")


        self.refresh_view()





    def pickup_candidates(self, x: int, y: int):


        """委托给 state（顺序与「从上往下放入」的结算口径一致）。"""


        return self.session.state.pickup_candidates(x, y)





    def toggle_pickup_selection(self) -> None:


        """空格：勾选/取消光标所在的显化物。"""


        entries = self.pickup_candidates(*self.pickup_target) if self.pickup_target else []


        index = self.pickup_cursor


        if not (0 <= index < len(entries)):


            return


        if index in self.pickup_picked:


            self.pickup_picked.discard(index)


        else:


            self.pickup_picked.add(index)


        self.refresh_view()





    def select_all_pickups(self) -> None:


        """A 键：全选/全不选（多件时省得一件件按空格）。"""


        entries = self.pickup_candidates(*self.pickup_target) if self.pickup_target else []


        if not entries:


            return


        if len(self.pickup_picked) == len(entries):


            self.pickup_picked.clear()


        else:


            self.pickup_picked = set(range(len(entries)))


        self.refresh_view()





    def move_pickup_cursor(self, delta: int) -> None:


        """↑↓ 移动光标（不跟随勾选，勾选是空格的事）。"""


        entries = self.pickup_candidates(*self.pickup_target) if self.pickup_target else []


        if not entries:


            return


        self.pickup_cursor = min(max(0, self.pickup_cursor + delta), len(entries) - 1)


        viewport = self._pickup_viewport_rows()


        if self.pickup_cursor < self.pickup_scroll:


            self.pickup_scroll = self.pickup_cursor


        elif self.pickup_cursor >= self.pickup_scroll + viewport:


            self.pickup_scroll = self.pickup_cursor - viewport + 1


        self.refresh_view()





    def scroll_pickup(self, amount: int) -> None:


        """滚轮：只滑视窗。"""


        entries = self.pickup_candidates(*self.pickup_target) if self.pickup_target else []


        viewport = self._pickup_viewport_rows()


        total = max(1, len(entries))


        self.pickup_scroll = min(max(0, total - viewport), max(0, self.pickup_scroll - amount))


        self.refresh_view()





    def _pickup_viewport_rows(self) -> int:


        """Reserve actual wrapped header/footer rows before sizing item rows."""


        entries=self.pickup_candidates(*self.pickup_target) if self.pickup_target else []


        if not entries:


            return 1


        try:


            pane=self.query_one('#map-pane')


            overlay=self.query_one('#map-overlay')


            height=max(1,pane.content_size.height-2-overlay.styles.gutter.height)


        except Exception:


            return 12


        width=max(1,self._overlay_content_width())


        def rows(value):


            return len(Text(value).wrap(_WRAP_CONSOLE,width))


        x,y=self.pickup_target


        header=rows(tr('拾取')+f'  ({x},{y}) · '+tr('共 {n} 件').format(n=len(entries)))


        help_rows=rows(tr('空格勾选 · A 全选 · Enter 捡起 · Esc/Q 关闭'))


        footer=rows(tr('捡起所选')+'    '+tr('关闭'))


        selected=(rows(tr('已选 {n} 件 · ').format(n=len(self.pickup_picked))+


                       tr('行囊 {a}/{b}').format(a=self.session.state.inventory_used,


                                              b=self.session.state.inventory_capacity))


                  if self.pickup_picked else 0)


        item_rows=max(rows('▶ [×] '+tr(e.item.name)+f' ×{e.item.quantity}'+


                           (f' [{tr(e.item.rarity)}]' if e.item.rarity else '')+


                           '  '+tr(e.item.category)) for e in entries)


        # One further line is reserved for the scroll-position indicator.


        return min(12,max(1,(height-header-help_rows-footer-selected-1)//max(1,item_rows)))





    def activate_pickup(self) -> None:


        """Enter：把勾选的显化物按「从上往下」顺序一起捡起。





        一件都没勾时，把光标那一件当作隐式选择——比「什么都不做」更符合直觉


        （玩家打开面板、方向键挪到某件、直接回车）。


        """


        if self.pickup_target is None:


            return


        entries = self.pickup_candidates(*self.pickup_target)


        if not entries:


            self.close_pickup()


            return


        snapshot=tuple(e.item.instance_id for e in entries)


        if snapshot!=getattr(self,'_pickup_snapshot',snapshot):


            target=self.pickup_target


            self.open_pickup(target)


            self.show_toast(tr("眼前的情形已经改变，请重新选择。"))


            return


        picked = sorted(self.pickup_picked) if self.pickup_picked else [self.pickup_cursor]


        positions = [index for index in picked if 0 <= index < len(entries)]


        if not positions:


            self.close_pickup()


            return


        # 结算按 world_items 的全局下标：面板条目顺序与 state.world_items 一致。


        state_items = self.session.state.world_items


        global_positions = [


            state_items.index(entries[index])


            for index in positions


            if entries[index] in state_items


        ]


        self.close_pickup()


        if global_positions:


            self._apply("collect_items", *global_positions)


        self.refresh_view()





    def _pickup_text(self, state: GameState) -> Text:


        """拾取面板正文：本格全部可拾取物 + 勾选框 + 操作提示。"""


        target = self.pickup_target


        if not target:


            return Text(tr("未选择格子。"), PANEL_MUTED)


        x, y = target


        entries = self.pickup_candidates(x, y)


        width = self._overlay_content_width()


        text = Text()


        text.append("▍", style=FC['condition'])


        text.append(tr("拾取"), style=f"bold {FC['condition']}")


        text.append(f"  ({x},{y})", style=PANEL_MUTED)


        text.append(" · " + tr("共 {n} 件").format(n=len(entries)), style=PANEL_MUTED)


        text.append("\n")


        text.append(tr("空格勾选 · A 全选 · Enter 捡起 · Esc/Q 关闭"), style=PORTENT_HINT_STYLE)


        if not entries:


            text.append("\n")


            text.append(tr("这里没有可拾取的显化物。"), PANEL_MUTED)


            return text


        viewport = self._pickup_viewport_rows()


        start = min(self.pickup_scroll, max(0, len(entries) - viewport))


        layout_key=(width,viewport)


        if layout_key!=getattr(self,'_pickup_layout_key',None):


            start=min(start,self.pickup_cursor)


            if self.pickup_cursor>=start+viewport:


                start=self.pickup_cursor-viewport+1


            self.pickup_scroll=start


            self._pickup_layout_key=layout_key


        end = min(len(entries), start + viewport)


        for index in range(start, end):


            entry = entries[index]


            item = entry.item


            marked = index in self.pickup_picked


            at_cursor = index == self.pickup_cursor


            text.append("\n")


            row_start=len(text)


            text.append("▶ " if at_cursor else "  ", style=PORTENT_HINT_STYLE)


            text.append("[×] " if marked else "[ ] ", style=FC['effect'] if marked else PANEL_MUTED)


            name = tr(item.name)


            style = item_name_color(item)


            rarity_tag = f" [{tr(item.rarity)}]" if item.rarity else ""


            text.append(f"{name} ×{item.quantity}{rarity_tag}", style=style + (" bold underline" if at_cursor else ""))


            text.append("  " + tr(item.category), style=PANEL_MUTED)


            text.stylize(Style(meta={'pickup_index':index}),row_start,len(text))


        if len(entries) > viewport:


            text.append("\n")


            text.append(


                tr("第 {a}-{b}/{c} 件 · 滚轮或 ↑↓ 滚动").format(a=start + 1, b=end, c=len(entries)),


                style=PORTENT_HINT_STYLE,


            )


        # 勾选了就预告一下背包代价：装不下时结算会留在原地（见 collect_items）。


        if self.pickup_picked:


            text.append("\n")


            text.append(


                tr("已选 {n} 件 · ").format(n=len(self.pickup_picked))


                + tr("行囊 {a}/{b}").format(a=state.inventory_used, b=state.inventory_capacity),


                style=FC['effect'],


            )


        text.append('\n')


        text.append(tr('捡起所选'),style=Style(color=FC['effect'],bold=True,underline=True,


                                           meta={'pickup_action':'confirm'}))


        text.append('    ')


        text.append(tr('关闭'),style=Style(color=PANEL_MUTED,underline=True,


                                         meta={'pickup_action':'cancel'}))


        return text





    def _cd_row(self, label, name, color, lines, selectable, width, extra="", icon=""):


        """「标签 名称 [补充]」一行 + 一句介绍（cell_detail_intros 开时）。"""


        line = Text("  ")


        line.append(tr(label) + " ", style=FC[LABEL_FIELDS.get(label, 'label')])


        if icon:


            line.append(icon, style=panel_color(color))


        if name:


            line.append(tr(name), style=FC[LABEL_FIELDS.get(label, 'label')] if label in ('高度', '地势') else panel_color(color))


        else:


            line.append(tr("无"), style=PANEL_MUTED)


        if extra:


            line.append(' ')


            line.append_text(extra if isinstance(extra, Text) else Text(extra, style=FC['label']))


        lines.append(line)


        selectable.append(bool(name))


        if name and self.cell_detail_intros:


            intro = material_description(name)


            if intro:


                for chunk in self._split_by_width(tr(intro), max(8, width - 6)):


                    lines.append(Text("      " + chunk, style=PANEL_MUTED))


                    selectable.append(False)





    def _cd_trigger_text(self, name: str, gas: Any = None, *, state=None, cell=None) -> str:


        """材料「触发浓度」的显示文本。





        优先取征兆定义的最低门槛（material_trigger_amount）；没有征兆的


        遮蔽类气体（黑烟/灰尘云）按「遮蔽强度达标」折算出等效浓度


        （SIGHT_OBSCURE_MIN × 100 / opacity）；两者皆无则显示「无」。


        """


        threshold = material_trigger_amount(name)


        if gas is not None and state is not None and cell is not None:


            from .gas_status import gas_contact_threshold


            threshold=gas_contact_threshold(state,cell)


        if threshold is None and gas is not None and (gas.blocks_sight or gas.sight_attenuation < 1.0):


            threshold = math.ceil(SIGHT_OBSCURE_MIN * 100 / gas.opacity)


        return tr("无") if threshold is None else str(threshold)





    def _cd_fog_rows(self, state, info, lines, selectable, width) -> None:
        """三层信息下的格子详情行：未探索/记忆/全图地形/始终可见。
        没有当前视野授权时只给类型与来源，不给硬度/厚度/完整度、液气读数、
        生物/物品/事件；记忆层不显示实时变化（documented in docs 第 1 节）。
        层序与视野内一致：地板 → 表面 → 液体 → 高处 → 空中。
        """
        def add(line: Text) -> None:
            lines.append(line)
            selectable.append(False)

        def band(label: str, value: str) -> None:
            """层位行：标签＋该高度可知内容（未知写 ?）。"""
            line = Text("  ")
            line.append_text(_labeled(label, Text(tr(value), style=PANEL_MUTED)))
            add(line)

        if info.status == "unknown":
            add(Text("  " + tr("未探索：这里没有留下确认过的地形。"), style=PANEL_MUTED))
            if state.insight_active("双读"):
                cell = state.cell(info.x, info.y)
                if cell.liquid > 0:
                    band("液体", "液态记忆")
                if cell.gas > 0:
                    band("空中", "弥散印象")
            return
        if info.status == "always_visible":
            category = info.sources[-1] if info.sources else ""
            band("表面", self._known_wall_name(info) if (info.solid and info.wall_kind) else "?")
            add(Text("  " + tr("始终可见：") + tr(category), style=PANEL_MUTED))
            return
        if info.site:
            add(Text("  " + tr("已发现地点：") + tr(info.site), style=FC['degree']))
        band("地板", self._known_floor_name(info))
        band("表面", self._known_wall_name(info) if (info.solid and info.wall_kind) else "?")
        band("液体", "?")
        band("高处", "?")
        band("空中", "?")
        if info.status == "memory":
            add(Text("  " + tr("实时变化不会改写记忆；再次看见才会更新。"), style=PANEL_MUTED))
        hazard = self._hazard_memory_line(state, info.x, info.y, info.status)
        if hazard:
            add(Text("  " + hazard, style=PANEL_MUTED))





    def _cd_creature_rows(self, state: GameState, entries, lines, selectable, width,


                          targets) -> None:


        """§16.4 逐生物状态摘要：与观测详情同一份口径，并补齐它缺的独立计时。





        每只生物一条（同名实例靠 ①②… 稳定编号区分，不合并），玩家自己也是


        其中一条、不顶掉同格其他生物。``observed`` 为假的授权（残影直觉那类


        「只到知道是谁」的侦查）只报身份，不报完整度/征兆/技能。


        """


        from . import cell_detail





        def push(line: Text, sel: bool = True, target: Any = None) -> None:


            lines.append(line)


            selectable.append(sel)


            targets.append(target)





        total = len(entries)


        for order, entry in enumerate(entries, start=1):


            entity = entry["entity"]


            marker = " " + _CIRCLED_NUMBERS[order - 1] if total > 1 else ""


            if entity is state.player:


                head = Text("  ")


                head.append(tr("生物") + " ", style=PANEL_MUTED)


                head.append(tr("你自己"), style=FC['text'])


                if marker:


                    head.append(marker, style=PANEL_MUTED)


                push(head, True, entity)


                timers = cell_detail.control_timers(entity)


                if timers:


                    line = Text("   ")


                    line.append(tr("计时") + " ", style=PANEL_MUTED)


                    line.append(" · ".join(


                        f"{tr(name)} {left} {tr('回合')}" for name, left in timers),


                        style=FC['duration'])


                    push(line, True, entity)


                continue





            shown, disguised = cell_detail.display_identity(state, entity)


            definition = ANOMALY_DEFINITIONS.get(getattr(entity, "catalog_id", ""), {})
            kind = definition.get("anomaly_kind", "")
            head = Text("  ")


            head.append(tr("生物") + " ", style=PANEL_MUTED)


            head.append(shown, style=FC['degree'])


            if kind:


                head.append(tr("（{kind}）", kind=tr(kind)), style=PANEL_MUTED)


            if marker:


                head.append(marker, style=PANEL_MUTED)


            # 常态是「失控意识」不重复写；只有中立/友方与特殊感知来源才补注。
            if entity.relation not in ("失控意识", ""):


                head.append(" · " + tr(entity.relation), style=PANEL_MUTED)


            if entry["sense"] != cell_detail.SENSE_SIGHT:


                head.append(" · " + tr(entry["sense"]), style=PANEL_MUTED)


            if disguised:


                head.append(" · " + tr("表面身份"), style=PANEL_MUTED)


            push(head, True, entity)





            if not entry["observed"]:


                push(Text("   " + tr("只感知到存在：完整度、征兆与技能未经观察。"),


                          style=PANEL_MUTED), True, entity)


                continue





            bounds = cell_detail.integrity_bounds(state, entity)


            maximum = str(bounds["max"]) if bounds["confirmed"] else f"{bounds['max']}?"


            # 一行读全：视野 / 听觉 / 完整度 / 状态；上限来源不再写给玩家。
            from ..data.perception import perception_profile
            perception = perception_profile(getattr(entity, "catalog_id", ""))
            vision = (perception.vision if perception and perception.vision is not None
                      else definition.get("vision"))
            stats: list[tuple[str, str, str]] = []
            if vision is not None:
                stats.append((tr("视野"), str(vision), PANEL_MUTED))
            hearing = perception.hearing if perception else None
            stats.append((tr("听觉"), "—" if hearing is None else str(hearing), PANEL_MUTED))
            stats.append((tr("完整度"), f"{bounds['current']}/{maximum}",
                          PANEL_DANGER if bounds["current"] * 2 <= bounds["max"] else FC['effect']))


            from ..data.semantic_icons import semantic_icon
            alert_icon = semantic_icon({
                "未察觉": "alert.unaware", "怀疑": "alert.suspicious",
                "警戒": "alert.wary", "追踪": "alert.tracking",
            }.get(entity.alert_state, ""))
            alert_value = (alert_icon + " " if alert_icon else "") + tr(entity.alert_state)
            stats.append((tr("状态"), alert_value,
                          ALERT_STYLES.get(entity.alert_state, PANEL_MUTED)))


            stat_line = Text("   ")
            for position, (label, value, style) in enumerate(stats):
                if position:
                    stat_line.append(" · ", style=PANEL_MUTED)
                stat_line.append(label + " ", style=PANEL_MUTED)
                stat_line.append(value, style=style)


            # 与悬停同一份切换事实：右键详情与键盘观察读到同一句说明。
            from .anomaly_intent_marks import intent_text
            switched = intent_text(state, entity.x, entity.y)
            if switched:
                stat_line.append(" · " + tr("刚才切换：{label}", label=tr(switched[1])),
                                      style=PANEL_MUTED)
            push(stat_line, True, entity)





            timers = cell_detail.control_timers(entity)


            if timers:


                line = Text("   ")


                line.append(tr("计时") + " ", style=PANEL_MUTED)


                line.append(" · ".join(


                    f"{tr(name)} {left} {tr('回合')}" for name, left in timers),


                    style=FC['duration'])


                push(line, True, entity)





            notes = cell_detail.portent_notes(state, entity)


            if notes:


                for position, note in enumerate(notes):


                    entry_line = Text("   ")


                    entry_line.append(


                        (tr("征兆") if position == 0 else "　　　") + " ", style=PANEL_MUTED)


                    entry_line.append(tr(note["name"]), style=PORTENT_STYLE)


                    kind_color = (FC['risk'] if note["kind"] == "负面"


                                  else FC['effect'] if note["kind"] == "正面"


                                  else FC['label'])


                    entry_line.append(f"  {tr(note['kind'])}", style=kind_color)


                    details = []


                    if note["stacks"]:


                        details.append(f"{note['stacks']} {tr('层')}")


                    if note["remaining"]:


                        details.append(f"{note['remaining']} {tr('回合')}")


                    if note["attach"]:


                        details.append(tr("附着 {n} 回合", n=note["attach"]))


                    if details:


                        entry_line.append("（" + " · ".join(details) + "）", style=PANEL_MUTED)


                    push(entry_line, True, entity)


                    if self.cell_detail_intros:


                        for chunk in self._split_by_width(tr(note["effect"]), max(8, width - 8)):


                            push(Text("        " + chunk, style=PANEL_MUTED), False)


            else:


                empty = Text("   ")


                empty.append(tr("征兆") + " ", style=PANEL_MUTED)


                empty.append(tr("无"), style=PANEL_MUTED)


                push(empty, True, entity)





            definition = ANOMALY_DEFINITIONS.get(entity.catalog_id, {})


            description = definition.get("description", "")


            if description and self.cell_detail_intros:


                for chunk in self._split_by_width(tr(description), max(8, width - 6)):


                    push(Text("      " + chunk, style=PANEL_MUTED), False)


            # 主动技能（2026-10-10）：数值行 + 效果/条件注释 + 运行时状态，


            # 逐个体写清谁在蓄势、谁在等冷却。


            for summary in current_skill_summaries(state, entity.catalog_id):


                push(Text('    ') + _skill_summary_rich(summary), True, entity)


                if self.cell_detail_intros:


                    for detail_line in self._skill_detail_lines(summary, width):


                        push(detail_line, False)


            status = state.skill_cooldown_status(entity)


            if status.get("charging"):


                push(Text(


                    "    " + tr("技能 蓄势中：「{skill}」剩 {n} 回合",


                                skill=tr(status["charging_name"]), n=status["windup_left"]),


                    style=FC['condition']), True, entity)


            elif status.get("cooldown_left"):


                push(Text(


                    "    " + tr("技能 冷却中：最早 {n} 回合后再起手", n=status["cooldown_left"]),


                    style=FC['condition']), True, entity)





    def _cd_item_rows(self, state: GameState, entries, lines, selectable, width,


                      amnesia, targets) -> None:


        """§16.5 逐件显化物：名称、数量、类别、台面／地面、使用方式与拾取条件。





        全部列出、不用「另有若干」代替；暂时拿不动（距离不够、行囊已满、需要


        从台面取下）也照样列出并写明原因——那不等于物品不存在（§16.5）。


        """


        from . import cell_detail





        def push(line: Text, sel: bool = True, target: Any = None) -> None:


            lines.append(line)


            selectable.append(sel)


            targets.append(target)





        same_name: dict[str, int] = {}


        for entry in entries:


            key = str(entry["item"].name)


            same_name[key] = same_name.get(key, 0) + 1


        seen: dict[str, int] = {}


        for entry in entries:


            item = entry["item"]


            name = str(item.name)


            expand_key = str(item.instance_id or name)


            line = Text("  ")


            line.append(tr("掉落物") + " ", style=PANEL_MUTED)


            shown = "？？？" if amnesia else tr(name)


            if same_name[name] > 1:


                position = seen.get(name, 0) + 1


                seen[name] = position


                shown = f"{shown} {_CIRCLED_NUMBERS[position - 1]}"


            line.append(f"{shown} ×{item.quantity}", style=item_name_color(item))


            line.append(f"  {tr(item.category)}", style=PANEL_MUTED)


            line.append(" · " + tr(entry["surface"]), style=FC['position'])


            push(line, True, item)


            if amnesia:


                continue


            for blocker in entry["blockers"]:


                push(Text("      " + tr("拾取条件：") + tr(blocker), style=PANEL_MUTED),


                     True, item)


            # 承载面归属（2026-10-22）：有主的台面在每件物品下面写清「归谁、
            # 每取一件付什么」——方案 §P1 的「所有权与领取费用可见」。
            note = entry.get("surface_note") or ""


            if note:
                push(Text("      " + note, style=PANEL_MUTED), True, item)


            if entry["usable_now"]:


                push(Text("      " + tr("拾取条件：") + tr("现在就能取（G）"),


                          style=FC['effect']), True, item)


            push(Text("      " + tr("用法：") + cell_detail.usage_hint(state, item),


                      style=PANEL_MUTED), True, item)


            # 构件类配方提示（2026-10-22）：单列一行讲「跟哪套打法配起来才成立」。
            pair_hint = cell_detail.construct_hint(item)


            if pair_hint:
                push(Text("      " + pair_hint, style=PANEL_MUTED), True, item)


            if item.description and (self.cell_detail_intros or self._entry_expanded(expand_key)):


                for chunk in self._split_by_width(_item_description(item, state), max(8, width - 6)):


                    push(Text("      " + chunk, style=PANEL_MUTED), False, item)


                # 观测/格子详情与物品菜单同一口径：只给真实发声物品写发声点/半径。


                for sound_line in _item_sound_lines(state, item):


                    for chunk in self._split_by_width(sound_line, max(8, width - 6)):


                        push(Text("      " + chunk, style=PANEL_MUTED), False, item)





    def _cd_text(self, state: GameState) -> Text:
        """左侧格子详情：逐项列出本格全部可知对象。

        版面按物理高度从下到上分组，和右栏悬停共用同一套分层口径：
        地势 → 地板 → 表面（层位标题，随后是生物／台面物品／承载固体／
        植物／火焰／地面物品等表面对象及其读数）→ 液体 → 高处 → 空中
        （气体与读数）。事件提示固定在标题下，不属于物理层序。

        权限按对象分别判定（§16.6）：本格**实时环境**是否可见（``live``）与这一
        格里哪些**生物**被单独授权（``cell_detail.authorized_creatures``）是两件
        事。恒显核心执念、诅咒灵视与残影直觉只点亮那一只生物，不顺带公开同格
        的液、气、掉落物与事件；反过来，被点亮的生物也不会被「视野外提前返回」
        整段跳过。

        可知性仍沿用悬停那一条规则：视野外（未显影）只公开地板与记忆中的
        墙体，其余内容一律按「?」（双读给类别）——观察模式的 ? 也拿不到
        视野外的完整信息。
        """
        from . import cell_detail
        target = self.cell_detail_target
        if not target:
            self._detail_line_count = 1
            self._detail_selectable = [False]
            self._detail_targets = []
            return Text(tr("未选择格子。"), PANEL_MUTED)
        x, y = target
        cell = state.cell(x, y)
        width = self._overlay_content_width()
        intro_width = max(8, width - 6)
        lines: list[Text] = []
        selectable: list[bool] = []
        targets: list[Any] = []
        def add(line: Text, sel: bool = False, target_row: Any = None) -> None:
            lines.append(line)
            selectable.append(sel)
            targets.append(target_row)
        def row(*args: Any, **kwargs: Any) -> None:
            """``_cd_row`` 自己往 lines 里塞（还带介绍行），这里把 targets 补齐等长。"""
            before = len(lines)
            self._cd_row(*args, **kwargs)
            targets.extend([None] * (len(lines) - before))
        live = cell_detail.environment_authorized(state, x, y)
        creatures = cell_detail.authorized_creatures(state, x, y)
        hidden_container = cell.wall_kind in CONTAINER_KINDS and not live
        # 三层信息（2026-10-18 docs 第 1 节第二批）：未知/记忆/全图地形/始终可见格
        # 只展示授权范围内的内容；没有视野授权时不显示实时读数、数值和对象。
        fog_info = None
        if bool(getattr(state, "map_memory_enabled", False)) and not live:
            fog_info = state.cell_knowledge(x, y)
            if fog_info.status in ("visible", "developed"):
                fog_info = None
        title = Text()
        title.append("▍", style=FC['condition'])
        title.append(tr("格子详情"), style=f"bold {FC['condition']}")
        title.append(f"  ({x},{y})", style=PANEL_MUTED)
        title.append(" · " + tr("第 {n} 层").format(n=state.depth), style=PANEL_MUTED)
        if not live:
            status_label = {
                "unknown": tr("未探索"), "memory": tr("记忆"),
                "terrain_known": tr("全图地形"), "always_visible": tr("始终可见"),
            }.get(fog_info.status if fog_info is not None else "", tr("视野外"))
            title.append("  " + status_label, style=PANEL_MUTED)
        add(title)
        # 环境总览读数（docs 2026-10-26 §13.2）：格子详情管「这一格」，这里补
        # 「这一层还剩什么」。只在有实时视野时显示——未探索层不该透出还剩几株。
        if live:
            from ..core import plant_survey
            overview = plant_survey.summary_line(state)
            if overview:
                add(Text("  " + overview, style=PANEL_MUTED))
        # 提示区（§16.3 末段）：事件属于任务提示，固定在标题下，不混进物理层序。
        if live:
            for event in state.events:
                if event.resolved or (event.x, event.y) != (x, y):
                    continue
                line = Text("  ")
                line.append(tr("事件") + " ", style=PANEL_MUTED)
                line.append(tr(event.name), style=PANEL_MAGENTA)
                add(line, True, event)
                if event.description and self.cell_detail_intros:
                    for chunk in self._split_by_width(tr(event.description), intro_width):
                        add(Text("      " + chunk, style=PANEL_MUTED))
        # The compact legacy height summary belongs to cell inspection. Keep
        # detailed flow/slope analysis confined to its dedicated map view.
        from ..core.map_scene import build_scene
        known = build_scene(state, viewport=(x,y,1,1),
                            legacy_terrain=not bool(state.map_memory_enabled)).cell(x,y)
        # 地势：本格在全层的高度档位，排在物理层序最前。
        if known is not None and known.elevation is not None:
            add(field_text('地势', known.elevation, field='height'))
        if not live and fog_info is None:
            add(Text("  " + tr("凭记忆只能认出地面与墙体，其余内容以 ? 代替。"), style=PANEL_MUTED))
        # 视野外走知识口径：地板也是记忆里的地板，整块交给 _cd_fog_rows。
        # 不能先铺一行实时地板，否则会把离开视野后的变化泄露出去。
        if not live and fog_info is not None:
            # 记忆／全图地形格：环境按知识层给（不补实时读数）。被单独授权列出
            # 的生物已经在上面出现过，这里不能把它一起跳过（§16.6 末段）。
            self._cd_creature_rows(state, creatures, lines, selectable, width, targets)
            before = len(lines)
            self._cd_fog_rows(state, fog_info, lines, selectable, width)
            targets.extend([None] * (len(lines) - before))
            add(Text(""))
            return self._cd_finish(lines, selectable, targets)
        # 地板基底（§16.3 层序：地板 → 表面 → 液体 → 高处 → 空中）。
        if hidden_container:
            floor_name, floor_style = "普通聚合物", AGGREGATE_PANEL_STYLES["普通聚合物"]
        elif cell.floor is Material.PLAIN_AGGREGATE:
            floor_name, floor_style = cell.aggregate_variant, AGGREGATE_PANEL_STYLES.get(cell.aggregate_variant, PANEL_MUTED)
        else:
            floor_name, floor_style = cell.floor.value, FC['text']
        row("地板", floor_name, floor_style, lines, selectable, width)
        if self.cell_detail_intros:
            from ..materials.descriptions import material_effect_description
            detail = material_effect_description(floor_name)
            for chunk in self._split_by_width(detail, intro_width) if detail else ():
                add(Text('      ' + chunk, style=PANEL_MUTED))
        if not live:
            # 关闭地图记忆的旧口径：地板与记忆中的墙体可知，其余分层以 ? 占位。
            self._cd_creature_rows(state, creatures, lines, selectable, width, targets)
            surface, liquid_text, high, sky = "?", "?", "?", "?"
            if state.insight_active("双读") and not hidden_container:
                if cell.liquid > 0:
                    liquid_text = "液态记忆"
                if cell.gas > 0:
                    sky = "弥散印象"
            row("表面", surface, PANEL_MUTED, lines, selectable, width)
            row("液体", liquid_text, PANEL_MUTED, lines, selectable, width)
            row("高处", high, PANEL_MUTED, lines, selectable, width)
            row("空中", sky, PANEL_MUTED, lines, selectable, width)
            add(Text(""))
            return self._cd_finish(lines, selectable, targets)
        # 表面（低层）：先给层位标题，随后逐对象排列该层内容。悬停与详情共用
        # 同一份「地板／表面／高处／空中」分层口径，不再把空中的读数提到标题下。
        surface_parts: list[tuple[Any, str]] = []
        high_parts: list[tuple[Any, str]] = []
        sky_parts: list[tuple[Any, str]] = []
        if cell.solid:
            definition = wall_def(cell.wall_kind)
            wall_part = (tr(definition.name), definition.color)
            surface_parts.append(wall_part)
            if cell.height >= 2:
                high_parts.append(wall_part)
            if cell.height >= 3:
                sky_parts.append(wall_part)
        if cell.plant:
            plant_band = plant_def_for(cell.plant)
            plant_part = (tr(plant_band.name), plant_band.color)
            surface_parts.append(plant_part)
            if plant_band.height >= 2:
                high_parts.append(plant_part)
        gas = gas_def(cell.gas_kind) if (cell.gas > 0 and not (cell.solid and cell.height >= 3)) else None
        if gas is not None:
            sky_parts.append((_material_token(
                gas.name, gas.color, cell.gas, field='concentration',
                icon=glyphs.gas_glyph(cell.gas, self._symbol_mode())), gas.color))

        def band_line(label: str, parts) -> Text:
            """层位标题行：标签＋本层并列对象，没有内容就写「无」。"""
            line = Text("  ")
            line.append_text(_labeled(label, Text()))
            if not parts:
                line.append(tr("无"), style=FC['muted'])
                return line
            for index, (content, color) in enumerate(parts):
                if index:
                    line.append(" / ", style=FC['label'])
                line.append_text(content if isinstance(content, Text)
                                 else Text(content, style=panel_color(color)))
            return line

        add(band_line("表面", surface_parts))
        # 生物占据层：视野内列出本格全部可知生物。
        self._cd_creature_rows(state, creatures, lines, selectable, width, targets)
        items = cell_detail.item_entries(state, x, y)
        amnesia = "oblivion_strong" in state.portents
        tabletop = cell_detail.is_tabletop(state, x, y)
        # 台面承载层：台面上的物品排在承载它的固体之前（§16.3／§16.5）；同一面板
        # 一次只讲一格，不同台面天然分组，跨格支撑等第十四节落地。
        if tabletop:
            self._cd_item_rows(state, items, lines, selectable, width, amnesia, targets)
        # 承载固体层：石台、桌体等实际固体，并写明它的高度档位。
        wall = wall_def(cell.wall_kind) if cell.solid else None
        if wall is not None and not hidden_container:
            stats = (field_text('硬', cell.hardness, field='hardness') + Text(' ')
                     + field_text('厚', cell.thickness, field='thickness') + Text(' ')
                     + field_text('完', cell.integrity, field='integrity'))
            if wall.hand_breakable:
                stats += " · " + tr("可徒手推倒")
            if wall.transparent:
                stats += " · " + tr("不遮挡视线")
            row(
                "固体" if wall.name in SOLID_KINDS else "墙",
                wall.name, wall.color, lines, selectable, width, extra=stats,
            )
            if wall.proximity_effect:
                add(Text("      " + tr("贴近：") + tr(wall.proximity_effect), style=PANEL_MUTED))
            row("高度", str(cell.height), PANEL_MUTED, lines, selectable, width)
        # 地表对象层：植物、贴地的火焰，以及不在台面上的可拾取物。
        plant = plant_def_for(cell.plant) if cell.plant else None
        if plant is not None:
            traits = " · ".join(
                part for part in (
                    tr("发光") if plant.glow else "",
                    tr("抗液抗火") if plant.immune_liquid and plant.immune_fire else "",
                ) if part
            )
            row("植物", plant.name, plant.color, lines, selectable, width, extra=traits)
            # 常驻效果与「踩踏／拔除会放出什么」必须在触发前读得到（§3.4.4）：
            # 这里与篡改预览共用 core.plant_notes 的同一份文案。
            from ..core.plant_notes import plant_lines
            for note in plant_lines(
                plant, depleted=plant_spent(cell.plant, cell.plant_state),
            ):
                add(Text("      " + note, style=PANEL_MUTED))
        if cell.flame > 0:
            line = Text("  ")
            line.append(tr("火焰") + " ", style=PANEL_MUTED)
            line.append(str(cell.flame), style=panel_color(FC['damage']))
            line.append(" · " + tr("强度"), style=PANEL_MUTED)
            line.append(" · " + tr("地表"), style=FC['position'])
            add(line, True)
        if not tabletop:
            self._cd_item_rows(state, items, lines, selectable, width, amnesia, targets)
        # 液体：表面层的独立字段，排在表面对象之后、高处之前。液量写在液体行里，
        # 不当成地势（§16.3 末行）。
        liquid = liquid_def(cell.liquid_kind) if (cell.liquid > 0 and cell.liquid_kind) else None
        if liquid is not None:
            extra = (Text(str(cell.liquid), style=FC['volume']) + Text(' · ')
                     + field_text('流动速度', liquid.max_flow, field='flow') + Text(' · ')
                     + field_text('触发浓度', self._cd_trigger_text(liquid.name), field='concentration'))
            row("液体", liquid.name, liquid.color, lines, selectable, width, extra=extra)
            if self.cell_detail_intros:
                for portent_id in material_portents(liquid.name):
                    portent = PORTENT_DEFINITIONS[portent_id]
                    add(Text(f"      {tr('接触')} → " + tr(portent.name), style=PORTENT_STYLE))
        # 高处（中层）与空中（高层）：先给层位标题，气体读数排在空中标题之后。
        add(band_line("高处", high_parts))
        add(band_line("空中", sky_parts))
        if gas is not None:
            from .gas_status import gas_contact_text
            extra = (Text(str(cell.gas), style=FC['concentration']) + Text(' · ')
                     + field_text('扩散速度', gas.max_diffusion, field='flow') + Text(' · ')
                     + field_text('消散速度', gas.dissipation, field='flow') + Text(' · ')
                     + field_text('触发浓度', self._cd_trigger_text(gas.name, gas, state=state, cell=cell), field='concentration'))
            extra += ' · ' + gas_contact_text(state, cell)
            row("气体", gas.name, gas.color, lines, selectable, width, extra=extra,
                icon=glyphs.gas_glyph(cell.gas, self._symbol_mode()))
            if self.cell_detail_intros:
                for portent_id in material_portents(gas.name):
                    portent = PORTENT_DEFINITIONS[portent_id]
                    add(Text(f"      {tr('吸入')} → " + tr(portent.name), style=PORTENT_STYLE))
        if target in state.electric_field_cells():
            expiry = state.player.portent_debt[f"{state._electric_prefix()}{target[0]}:{target[1]}"]
            info = tr("余电还会持续 {n} 回合，每回合创伤 1；离开导电格可避开。", n=max(0, int(expiry-state.time)))
            for chunk in self._split_by_width(tr("电场") + "：" + info, intro_width):
                add(Text("      " + chunk, style=FC['condition']))
        add(Text(""))
        return self._cd_finish(lines, selectable, targets)





    def _cd_activate_row(self) -> bool:


        """Enter：把格子详情光标行「进入子详情」，并保证这次输入零消耗。





        生物行 → 已有的观测详情（逐个体展开那份），关闭时回到本格、原滚动位置


        与原选中行；显化物行 → 就地展开长说明／载荷／发声（沿用 \\ 的展开口径，


        不开物品菜单——那是行囊内物品的操作面板，从详情里进去就可能顺手


        使用/放下，违反 §16.6「不因查看便拾取或使用」）。其余行只吞键。


        """


        target = self.cell_detail_target


        if target is None:


            return False


        row_index = self.detail_cursor


        targets = getattr(self, "_detail_targets", [])


        payload = targets[row_index] if 0 <= row_index < len(targets) else None


        if payload is None:


            return True


        state = self.session.state


        if (payload is not state.player and getattr(payload, "relation", None)


                and getattr(payload, "catalog_id", None)):


            self.cell_detail_return = (target, self.detail_cursor, self.detail_scroll)


            self.anomaly_detail_target = payload.catalog_id


            self.cell_detail_target = None


            self.detail_cursor = 0


            self.detail_scroll = 0


            self.refresh_view()


            return True


        instance_id = getattr(payload, "instance_id", None)


        if instance_id is not None:


            key = str(instance_id)


            self.expanded_key = None if self.expanded_key == key else key


            self.refresh_view()


            return True


        return True





    def _cd_finish(self, lines: list[Text], selectable: list[bool],


                   targets: list[Any] | None = None) -> Text:


        """视窗裁剪 + 光标吸附 + 底部滚动提示（与意象详情同一套手感）。





        ``targets`` 与 ``lines`` 等长（每行一个可进入子详情的对象或 None）：


        Enter 靠它把光标行认回那一只生物／那一件显化物。折行会把一行拆成多


        个物理行，所以映射要和 ``selectable`` 一样按同样的份数复制。


        """


        physical_lines, physical_selectable, physical_targets = [], [], []


        for position, (line, selected) in enumerate(zip(lines, selectable)):


            wrapped = rich_lines(line, max(8, self._overlay_content_width()))


            physical_lines.extend(wrapped)


            physical_selectable.extend([selected] * len(wrapped))


            if targets is not None:


                physical_targets.extend([targets[position]] * len(wrapped))


        lines, selectable = physical_lines, physical_selectable


        self._detail_line_count = len(lines)


        self._detail_selectable = selectable


        self._detail_targets = physical_targets if targets is not None else []


        self.detail_cursor = min(max(0, self.detail_cursor), max(0, len(lines)-1))


        viewport = len(lines) if getattr(self,'_inspection_full_cell',False) else self._anomaly_detail_viewport()


        self.detail_scroll = min(max(0, self.detail_scroll), max(0, len(lines) - viewport))


        low = self.detail_scroll


        high = min(low + viewport - 1, max(0, len(lines) - 1))


        if not (low <= self.detail_cursor <= high) or not selectable[self.detail_cursor]:


            window = [index for index in range(low, high + 1) if selectable[index]]


            self.detail_cursor = (


                min(window, key=lambda index: (abs(index - self.detail_cursor), index))


                if window else low


            )


        text = Text()


        for offset, line in enumerate(lines[self.detail_scroll:self.detail_scroll + viewport]):


            if offset:


                text.append("\n")


            if self.detail_scroll + offset == self.detail_cursor:


                line.stylize("bold underline")


            text.append_text(line)


        text.append("\n")


        if len(lines) > viewport:


            last = min(len(lines), self.detail_scroll + viewport)


            text.append(


                tr("第 {a}-{b}/{c} 行 · 滚轮或 ↑↓ 滚动 · Q/Esc 关闭").format(


                    a=self.detail_scroll + 1, b=last, c=len(lines)


                ),


                style=PORTENT_HINT_STYLE,


            )


        else:


            text.append(tr("滚轮或 ↑↓ 滚动 · Q/Esc 关闭"), style=PORTENT_HINT_STYLE)


        return text





    def _scrolled_panel_text(self, state: GameState) -> Text:
        """行囊/携带意象/洞察/记忆碎片共用的「首行偏移 + 视窗切片」渲染。

        顶部页签行与本页标题钉住不滚动，条目按 ``panel_scroll`` 切片。装备盘的
        记忆碎片已独立成「记忆碎片」分层页，不再钉在列表底部。
        """
        lines, row_indices, header = self._panel_lines(state)
        footer = self._panel_footer(state)
        viewport = self._portent_viewport_rows()
        strip_lines = self._panel_subtabs_lines()
        if strip_lines:
            viewport = max(1, viewport - len(strip_lines))
        if footer is not None:
            viewport = max(1, viewport - 1)
        max_scroll = max(0, len(lines) - viewport)
        self.panel_scroll = min(self.panel_scroll, max_scroll)
        start = self.panel_scroll
        text = Text()
        rows: list[int] = []
        for strip_line in strip_lines:
            text.append_text(strip_line)
            text.append("\n")
            rows.append(-3)
        header.stylize("bold underline")
        text.append_text(paper_pad(header, ZONE_STRIP, self._portent_panel_width()))
        rows.append(-1)
        for offset in range(start, min(len(lines), start + viewport)):
            text.append("\n")
            text.append_text(lines[offset])
            rows.append(row_indices[offset])
        if len(lines) > viewport:
            last = min(len(lines), start + viewport)
            text.append(self._panel_scroll_hint(start + 1, last, len(lines)),
                        style=SCROLL_HINT_STYLE)
            rows.append(-1)
        if footer is not None:
            text.append("\n")
            text.append_text(footer)
            rows.append(-1)
        self._panel_rows = rows
        return text


    def _panel_footer(self, state: GameState) -> Text | None:


        """右侧面板底部**钉住**的一行（不随滚动移动）；没有则返回 None。





        任务日志页放未完成任务统计，洞察页不再重复。


        记忆碎片已独立成分层页（2026-10-23），装备盘页不再有钉底记忆区。


        """


        if self.panel_mode == "tasks":


            return self._active_tasks_footer(state)


        # 2026-10-24 玩家反馈：构想/环境/发射的键位行不再留在正文下方，
        # 统一交给右栏底部 #panel-help（紧邻完整键位表入口）。
        return None


    def _panel_context_hint(self) -> str:
        """右栏底部 #panel-help 本页键位提示；空串走「完整键位表」默认文案。"""
        if self.home_mode:
            return ''
        # 瞄准/语句瞄准时提示行回到「完整键位表」：本页键位此时不适用，
        # 也不能顶掉 Alt+H 入口。
        if self.aiming or self.sentence_aim is not None:
            return ''
        if self.panel_mode == 'actions':
            page = self._panel_subpage_id()
            if page == 'constructs':
                return tr('↑↓ 选构想 · Enter 施放 · Esc 返回 · 键位表')
            if page == 'fire':
                return tr('↑↓ 选来源 · Enter 设为当前 · F 瞄准 · R 换弹 · 键位表')
        if self.panel_mode == 'nearby':
            return tr('Enter 详情 · F3/Alt+V 分层 · ↑↓ 选异象 · 键位表')
        return ''





    def _active_tasks_footer(self, state: GameState) -> Text:


        """任务日志钉底的未完成任务行：进行中 + 待交付，上限见 tasks.ACTIVE_TASK_LIMIT。"""


        from ..data.quests import QUEST_DEFINITIONS


        from ..world import tasks as world_tasks





        active = [entry for entry in state.world_ledger.tasks.values()


                  if entry.status in ("进行中", "待交付")]


        header = tr("未完成任务：") + f"{len(active)}/{world_tasks.ACTIVE_TASK_LIMIT}"


        if not active:


            return Text(header + tr("　") + tr("（无）"), style=PANEL_MUTED)


        parts = []


        for entry in active:


            quest = QUEST_DEFINITIONS.get(entry.definition_id) or {}


            name = tr(quest.get("name", entry.definition_id))


            parts.append(f"{name}·{tr(entry.status)}")


        return Text(header + tr("　") + tr("、").join(parts), style=INSIGHT_STYLE)





    def _memory_slot_text(self, state: GameState, limit: int | None = None) -> str:


        """行囊下方那一行「记忆槽」的文本。





        ⚠️ 旧实现直接把 ``state.memory_fragments`` 里的 **id** 交给 ``tr()``：


        ``tr("rain_machine_memory")`` 查不到词条，原样返回——中文界面下因此


        显示成一串英文 id（玩家反馈的「背包下方记忆碎片显示英文」）。碎片列表


        存的是 definition id，必须先用 ``ITEM_DEFINITIONS`` 换成名字再翻译。





        每条碎片带上效果摘要（括号内），否则玩家看不出它到底在做什么——


        碎片是「可拆卸的洞察」，不写效果就等于没有。摘要用效果表里的


        ``short``（如「清醒上限 +10」），完整说明留给图鉴，不占满这一行。


        """


        limit = MEMORY_LIMIT + state._memory_slot_bonus() if limit is None else limit


        header = tr("记忆槽：") + f"{len(state.memory_fragments)}/{limit}"


        if not state.memory_fragments:


            return header + tr("　") + tr("空")


        parts = []


        for fragment_id in state.memory_fragments:


            definition = ITEM_DEFINITIONS.get(fragment_id)


            name = tr(definition["name"]) if definition else fragment_id


            effect_name = (definition or {}).get("memory_effect")


            effect = MEMORY_FRAGMENT_EFFECTS.get(effect_name) if effect_name else None


            summary = effect.get("short") if effect else None


            if summary:


                # 括号与名/效之间的分隔都走 tr()：中文全角、英文半角。


                parts.append(tr("（") + name + tr("｜") + tr(summary) + tr("）"))


            else:


                parts.append(name)


        return header + tr("　") + tr("、").join(parts)





    def _memory_footer_region(self, state: GameState) -> tuple[Text, list[Text]]:


        """携带意象页钉底的「记忆碎片独立滚动区」（2026-10-14）。





        旧实现把全部碎片拼成一行（footer 单行预算），碎片一多就被视窗截断——


        玩家反馈的「记忆碎片显示不全」。改为独立小视窗：header（记忆槽 n/m +


        滚动区间提示）+ 每条碎片一行，超出 MEMORY_FOOTER_ITEM_ROWS 行用


        ``memory_scroll`` 滚动。调用方把这些行的 row_index 记 **-2**——


        滚轮悬停判定（_memory_region_row_at）的专属标记。





        键盘光标（panel_selection == 携带意象条目数）选中整区时 header 反白，


        ↑↓ 走 _move_equipment_selection 的记忆区分支滚动。


        """


        limit = MEMORY_LIMIT + state._memory_slot_bonus()


        fragments = state.memory_fragments


        selected = bool(fragments) and self.panel_selection == self._panel_item_count()


        header = Text(tr('记忆槽：'), style=FC['memory'])


        header.append(f'{len(fragments)}/{limit}', style=FC['count'])


        if selected:


            header.stylize("bold underline")


        if not fragments:


            header.append(tr("　") + tr("空"))


            return header, []


        total = len(fragments)


        max_scroll = max(0, total - MEMORY_FOOTER_ITEM_ROWS)


        self.memory_scroll = min(max(0, self.memory_scroll), max_scroll)


        start = self.memory_scroll


        end = min(total, start + MEMORY_FOOTER_ITEM_ROWS)


        if max_scroll:


            header.append(


                tr("　") + tr("第 {a}-{b}/{c} 条").format(a=start + 1, b=end, c=total),


                style=PORTENT_HINT_STYLE,


            )


        width = max(8, self._portent_panel_width() - 4)


        lines = [self._memory_fragment_line(fragment_id, width)


                 for fragment_id in fragments[start:end]]


        return header, lines





    def _memory_fragment_line(self, fragment_id: str, width: int) -> Text:


        """记忆碎片的一行：名字（碎片紫）+ 效果摘要（灰）。





        每条碎片**恰好一行**（超宽截断）——行映射 -2 标记按可视行记，


        wrap 出来的续行不在映射里，悬停判定会错位。


        """


        definition = ITEM_DEFINITIONS.get(fragment_id)


        name = tr(definition["name"]) if definition else fragment_id


        effect_name = (definition or {}).get("memory_effect")


        effect = MEMORY_FRAGMENT_EFFECTS.get(effect_name) if effect_name else None


        summary = effect.get("short") if effect else None


        line = Text("  ")


        from ..data.semantic_icons import icon_label
        line.append_text(icon_label('memory.'+str(effect_name or ''),name,CATEGORY_STYLES.get("记忆碎片", FC['memory'])))


        if summary:


            line.append(tr("｜") + tr(summary), style=PANEL_MUTED)


        if cell_len(line.plain) > width:


            line.truncate(width, pad=False)


        return line





    def _memory_page_lines(self, state: GameState):
        """记忆碎片分层页：独立列表，不再钉在装备盘底部（2026-10-23）。

        碎片不占行囊下标：整页只读，碎片槽满时拾到新碎片才自动弹出替换面板。
        """
        width = max(8, self._portent_panel_width() - 4)
        limit = MEMORY_LIMIT + state._memory_slot_bonus()
        fragments = state.memory_fragments
        header = Text(tr('记忆槽：'), style=FC['memory'])
        header.append(f'{len(fragments)}/{limit}', style=FC['count'])
        lines: list[Text] = []
        rows: list[int] = []

        def add(line: Text, row: int = -1) -> None:
            for wrapped in line.wrap(_WRAP_CONSOLE, width + 4, overflow='fold', no_wrap=False):
                lines.append(wrapped)
                rows.append(row)

        if not fragments:
            add(Text(tr('（空）'), style=PANEL_MUTED))
        for fragment_id in fragments:
            add(self._memory_fragment_line(fragment_id, width))
        add(Text(tr('碎片槽满时拾到新碎片，会自动弹出替换界面。'), style=PANEL_MUTED))
        return lines, rows, header

    def _panel_lines(


        self, state: GameState


    ) -> tuple[list[Text], list[int], Text]:


        """行囊/携带意象/洞察的完整排版：返回（行列表, 每行对应的条目序号, 标题行）。





        「条目序号」与 ``_panel_rows`` 的口径一致（-1 = 装饰行）：行囊/洞察是


        列表下标，携带意象页是**真实行囊下标**（右键菜单/左键使用都直接按行囊定位）。


        """


        lines: list[Text] = []


        row_indices: list[int] = []


        amnesia = "oblivion_strong" in state.portents


        width = max(8, self._portent_panel_width() - 4)





        def add(line: Text, row_index: int = -1) -> None:


            for wrapped in line.wrap(_WRAP_CONSOLE, width + 4, overflow="fold", no_wrap=False):


                lines.append(wrapped)


                row_indices.append(row_index)





        if self.panel_mode == "inventory":


            header = Text.assemble(


                ('PACK' if self._terse_active() else tr("意识行囊"), f"bold {FC['condition']}"),


                (f"  {state.inventory_used}/{state.inventory_capacity}", FC['text']),


            )


            visible = self._inventory_visible_indices() if hasattr(self, '_inventory_visible_indices') else range(len(state.inventory))


            if getattr(self, 'inventory_query', '') or getattr(self, 'inventory_sort', '原序') != '原序':


                add(Text.assemble((tr('搜索')+'：',FC['label']),


                    (self.inventory_query or '—',FC['degree']),(' · ',FC['muted']),


                    (tr(self.inventory_filter),FC['condition']),(' · ',FC['muted']),


                    (tr(self.inventory_sort),FC['position'])))


            if getattr(self, 'inventory_query', ''):
                add(Text(tr('结果：{n}', n=len(visible)), style=FC['count']))
            if not visible:
                add(Text(tr('没有匹配物品；按 Alt+F 修改搜索，或切换分类。')
                         if getattr(self, 'inventory_query', '') else tr('（空）'), style=PANEL_MUTED))
            for index in visible:


                item = state.inventory[index]


                equipped = " *" if item.instance_id in state.equipped.values() else ""


                selected = index == self.panel_selection


                prefix = "▶ " if selected else "  "


                # 物品名 = 物品自己的定义色（2026-09-21：不同物品不同颜色，


                # 左右面板/气泡/播报同一口径），稀有度仍走四档微调。


                style = item_name_color(item) + (" bold underline" if selected else "")


                shown_name = "？？？" if amnesia else tr(item.name)


                # 物品自带图标（书卷 📚 / 残页 📜）：行囊里也按同一把尺子画出来，


                # 与地图、悬停的图标一致；没登记的物品不打前缀（保持列表清爽）。


                # 装备（有栏位）也显示图标：四种栏位 emoji 与地图/携带意象页一致。


                mark = f"{drop_glyph(item, self._symbol_mode())} " if (item.icon or item.slot) else ""


                line = Text(f'{prefix}{index + 1}. ', style=FC['count'])


                line.append(f'{mark}{shown_name}', style=item_name_color(item) + (' bold underline' if selected else ''))


                line.append(f' ×{item.quantity}', style=FC['count'])


                if equipped:


                    line.append(equipped, style=FC['effect'])


                add(line, index)


                if not amnesia and self._entry_expanded(item.instance_id):


                    for chunk in self._split_by_width(_item_description(item, state), width):


                        add(Text("    " + chunk, style=PANEL_MUTED))


                    for line in _item_sound_lines(state, item):


                        for chunk in self._split_by_width(line, width):


                            add(Text("    " + chunk, style=PANEL_MUTED))


        elif self.panel_mode == "equipment":

            if self._panel_subpage_id() == "memory":
                return self._memory_page_lines(state)

            from ..equipment.board import piece_cells


            from ..equipment.grammar import ACTIVE, DORMANT, PENDING, UNFORMED





            board = state.board


            ordered_words = [t.value for t in scan(board) if isinstance(t.value, Placement)]


            compiled = state.equipment.compiled()


            total_cells = board.width * board.height


            header = Text.assemble(


                (tr("携带意象 · 联想盘"), "bold " + CARRIED_IMAGE_STYLE),


                (f"  {board.area_used()}/{total_cells}", FC['text']),


                (f"  {tr('成句')} {len(compiled.sentences)}", FC['mind']),


            )


            # ⚠️ header 由返回值单独交给 _scrolled_panel_text 拼在首行——


            # 这里不能再 add()，否则标题画两遍（2026-10-09 修复）。





            def board_glyphs() -> list[Text]:


                from .board_editor import PIECE_GLYPHS


                from .equipment_art import board_art_rows


                return board_art_rows(board, PIECE_GLYPHS)





            # 渲染预算按面板实际内容高度算（§8.2），但**盘面与装备图形永远画出**：


            # 窄面板（<20 行）不再折叠成两行摘要——2026-10-10 玩家反馈「装上盘


            # 之后右侧看不到盘和图形」。内容超高时交给面板滚动兜底。


            if True:


                paths = len(compiled.react_paths)


                broken = sum(1 for s in compiled.sentences if s.status == UNFORMED)


                for row in board_glyphs():


                    # -4 = 盘面示意图：鼠标左键点它直接进入联想盘编辑器
                    # （2026-10-24 玩家定稿：页签行不再挂「盘」按钮）。
                    add(row, -4)


                if board.pieces:


                    from .board_editor import PIECE_GLYPHS


                    from ..equipment.board import PIECE_SPECS


                    from ..equipment.function_words import FUNCTION_WORDS





                    def piece_label(piece_id: str) -> str:


                        word = FUNCTION_WORDS.get(piece_id)


                        return word.label if word else tr(PIECE_SPECS[piece_id].label)





                    add(Text("  ".join(


                        f"{PIECE_GLYPHS.get(piece_id, '?')}={piece_label(piece_id)}"


                        for piece_id in {piece.piece_id for piece in board.pieces}


                    ), style=PANEL_MUTED))


                hint = Text(tr("[ 编辑联想盘"))


                hint.append(f" · {paths}/{broken}", style=PANEL_MUTED)


                hint.truncate(max(1, width - 4), overflow="ellipsis")


                add(Text.assemble(("└ ", PANEL_MUTED), hint, (" ┘", PANEL_MUTED)), -4)


                for position, placement in enumerate(ordered_words):


                    item = next(


                        (it for it in state.inventory


                         if it.instance_id == placement.instance_id), None,


                    )


                    name = tr(item.name) if item is not None else placement.definition_id


                    if amnesia:


                        name = "？？？"


                    tag = ""


                    sentence = next(


                        (s for s in compiled.sentences


                         if placement.instance_id in s.instance_ids), None,


                    )


                    status = ""


                    if sentence is not None and not amnesia:


                        status = {


                            ACTIVE: tr("生效"), DORMANT: tr("备用"),


                            PENDING: tr("待触发"), UNFORMED: tr("未成句"),


                        }.get(sentence.status, "")


                    # 编辑联想盘下方不再画装备图案（2026-10-12 玩家反馈）：


                    # 上盘件只留「名字 + 句位状态」一行，盘面图形本身照画。


                    add(Text(f"  {name}{tag} {status}".rstrip(),


                             style=FC['mind'] if tag else PANEL_MUTED))


                for line in _react_summaries(state):


                    add(line)


            equipment_indices = [index for index, item in enumerate(state.inventory) if item.slot]


            add(zone_strip(tr("行囊中的携带意象："), width+4, color=FC["condition"]))


            if not equipment_indices:


                add(Text(tr("（无）"), style=PANEL_MUTED))


            for position, index in enumerate(equipment_indices):


                item = state.inventory[index]


                selected = position == self.panel_selection


                shown = "？？？" if amnesia else tr(item.name)


                # 已装备的带 * 标记（与行囊页同一口径），玩家一眼分辨


                # 「在行囊里」和「已挂在栏位上」。


                equipped = " *" if item.instance_id in state.equipped.values() else ""


                # 行映射存真实行囊下标（口径见函数文档）：右键菜单/左键使用都按行囊定位。


                add(


                    Text(f"{'▶ ' if selected else '  '}{shown}{equipped}", style=CARRIED_IMAGE_STYLE + (" bold underline" if selected else "")),


                    index,


                )


                if not amnesia and self._entry_expanded(item.instance_id):


                    for chunk in self._split_by_width(_item_description(item, state), width):


                        add(Text("    " + chunk, style=PANEL_MUTED))


                    for line in _item_sound_lines(state, item):


                        for chunk in self._split_by_width(line, width):


                            add(Text("    " + chunk, style=PANEL_MUTED))


            # 记忆槽不在这里排——2026-10-23 起它是装备按钮内的独立分层页


            # （_memory_page_lines），与装备盘彻底分开。


        else:  # insights


            header = Text.assemble((tr("现实洞察"), "bold " + INSIGHT_STYLE), f"  {len(state.insights)}/15")


            if state.insights:


                for index, insight in enumerate(state.insights):


                    selected = index == self.panel_selection


                    add(


                        Text.assemble(('▶ ' if selected else '  ',INSIGHT_STYLE),
                            icon_label(
                                'insight.'+insight,tr(insight),INSIGHT_STYLE + (' bold underline' if selected else ''))),


                        index,


                    )


                    note = INSIGHT_DEFINITIONS.get(insight, "")


                    if note and self._entry_expanded(insight):


                        for chunk in self._split_by_width(tr(note), width):


                            add(Text("    " + chunk, style=PANEL_MUTED))


                        if insight == "蜂鸣回响":


                            toggle = tr("广播加成：开启（Enter 关闭）") if getattr(


                                state, "buzzing_echo_enabled", True) else tr(


                                "广播加成：关闭（Enter 开启）")


                            add(Text("    " + toggle, style=PANEL_MUTED))


            else:


                add(Text(tr("尚未形成洞察"), PANEL_MUTED))


        if self.panel_mode == "tasks":


            # 任务日志（§14）：只读面板，行序号全 -1（点击不做事）；放弃与


            # 交付仍走对话页，不在这里复制一套操作。


            from .task_journal import journal_lines


            return journal_lines(state, width=width, actionable=True, selection=self.panel_selection)


        return lines, row_indices, header





    def _portents_panel_text(self, state: GameState) -> Text:


        lines, starts, total = self._portent_layout(state)


        active_count = len(self._portent_entries(state))


        header = Text.assemble((tr("征兆") + f" {active_count}", "bold " + PORTENT_STYLE))


        if not lines:


            header.append("\n" + tr("此刻没有萦绕在你身上的征兆"), PANEL_MUTED)


            self._panel_rows = [-1, -1]


            return header


        viewport = self._portent_viewport_rows()


        max_scroll = max(0, total - viewport)


        self.panel_scroll = min(self.panel_scroll, max_scroll)


        start = self.panel_scroll


        window = lines[start:start + viewport]


        text = header


        for line in window:


            text.append("\n")


            text.append_text(line)


        self._panel_rows = [-1]  # 标题行


        for line_no in range(start, min(total, start + viewport)):


            entry_index = -1


            for candidate, begin in enumerate(starts):


                if begin <= line_no:


                    entry_index = candidate


                else:


                    break


            self._panel_rows.append(entry_index)


        if total > viewport:


            last = min(total, start + viewport)


            text.append(


                self._panel_scroll_hint(start + 1, last, total),


                style=SCROLL_HINT_STYLE,


            )


            self._panel_rows.append(-1)


        return text





    def _message_marker(self, message: str) -> tuple[str, str]:


        for entity in self.session.state.enemies:


            if entity.label in message:


                return "● ", RELATION_STYLES.get(entity.relation, FC['text'])


        if "失控意识" in message or "创伤" in message:


            return "● ", PANEL_DANGER


        if "稳定意识" in message or "异常地点" in message:


            return "● ", FC['degree']


        if "受控意识" in message or "拾取" in message or "获得" in message:


            return "● ", FC['effect']


        for definition in ITEM_DEFINITIONS.values():


            if definition["name"] in message:


                # 红点 = 物品自己的定义色（2026-09-21：不同物品不同颜色）。


                return "● ", definition.get("color") or CATEGORY_STYLES.get(definition["category"], FC['text'])


        return "· ", PANEL_MUTED





    def _message_body_text(self, message: str) -> Text:
        """事件记录条目的正文（不含行首 ●／· 点号），与右栏同色同高亮。

        右侧事件记录、左侧透明事件记录、顶部播报都复用这一份取词/染色口径；
        左侧叠加层要求「除了文字无任何遮挡」，因此点号也由调用方决定是否加。
        """
        rendered = Text(message, style=PANEL_MUTED)
        for entity in self.session.state.enemies:
            if entity.label in message:
                color = RELATION_STYLES.get(entity.relation, FC['text'])
                rendered.highlight_words([entity.label], style=color)
        for trauma, color in TRAUMA_STYLES.items():
            if trauma in message:
                rendered.highlight_words([trauma], style=color)
        if "现实洞察" in message:
            rendered.highlight_words(["现实洞察"], style=INSIGHT_STYLE)
        insight_names = [event["insight_id"] for event in EVENT_DEFINITIONS if event.get("insight_id")]
        rendered.highlight_words(insight_names, style=INSIGHT_STYLE)
        for definition in ITEM_DEFINITIONS.values():
            if definition["name"] in message:
                # 物品名 = 物品自己的定义色（2026-09-21：不同物品不同颜色）。
                rendered.highlight_words(
                    [definition["name"]],
                    style=definition.get("color") or CATEGORY_STYLES.get(definition["category"], FC['text']),
                )
        return rendered


    def _message_text(self, message: str) -> Text:


        marker, marker_style = self._message_marker(message)


        rendered = Text(marker, style=marker_style)


        rendered.append(message, style=PANEL_MUTED)


        for entity in self.session.state.enemies:


            if entity.label in message:


                color = RELATION_STYLES.get(entity.relation, FC['text'])


                rendered.highlight_words([entity.label], style=color)


        for trauma, color in TRAUMA_STYLES.items():


            if trauma in message:


                rendered.highlight_words([trauma], style=color)


        if "现实洞察" in message:


            rendered.highlight_words(["现实洞察"], style=INSIGHT_STYLE)


        insight_names = [event["insight_id"] for event in EVENT_DEFINITIONS if event.get("insight_id")]


        rendered.highlight_words(insight_names, style=INSIGHT_STYLE)


        for definition in ITEM_DEFINITIONS.values():


            if definition["name"] in message:


                # 物品名 = 物品自己的定义色（2026-09-21：不同物品不同颜色）。


                rendered.highlight_words(


                    [definition["name"]],


                    style=definition.get("color") or CATEGORY_STYLES.get(definition["category"], FC['text']),


                )


        return rendered





    def _container_overlay_text(self, state: GameState) -> Text:


        """容器浮层（左侧）：内容 + 本格材料 + 盛装/倒出。





        行号登记进 ``_container_action_rows``（(盛装行, 倒出行)），供左键点击


        直接执行对应操作——内容行 = 点击 offset.y - 2（边框+内边距各 1）。


        """


        from ..core.content import ITEM_DEFINITIONS





        item = (


            state.inventory[self.container_index]


            if getattr(self, "container_index", None) is not None


            and 0 <= self.container_index < len(state.inventory)


            else None


        )


        text = Text()


        if item is None:


            text.append(tr("容器不在行囊里。"), style=PANEL_MUTED)


            self._container_action_rows = None


            return text


        spec = ITEM_DEFINITIONS.get(item.definition_id, {}).get("container", {})


        cap = int(spec.get("cap", 25))


        used = sum(item.contents.values())
        text.append(tr(item.name) + tr("（{n}/{capacity}）", n=used, capacity=cap) + "\n",
                    style=f"bold {FC['condition']}")


        if item.contents:


            for kind, amount in item.contents.items():


                text.append("  " + tr(kind) + f" ×{amount}\n", style=FC['text'])


        else:


            text.append("  " + tr("（空的）") + "\n", style=PANEL_MUTED)


        px, py = state.player.x, state.player.y


        cell = state.cell(px, py)


        cell_liquid = f"{tr(cell.liquid_kind)} {cell.liquid}" if cell.liquid > 0 else tr("无")


        cell_gas = f"{tr(cell.gas_kind)} {cell.gas}" if cell.gas > 0 else tr("无")


        text.append(tr("本格液体：") + cell_liquid + "\n", style=FC['volume'])


        text.append(tr("本格气体：") + cell_gas + "\n", style=FC['concentration'])


        text.append("──" + tr("操作") + "──\n", style=PANEL_MUTED)


        fill_line = len(text.plain.splitlines())


        text.append("1. " + tr("盛装（从本格装入容器）") + "\n", style=FC['condition'])


        pour_line = len(text.plain.splitlines())


        text.append("2. " + tr("倒出（倒在本格并就地反应）") + "\n", style=FC['condition'])


        self._container_action_rows = (fill_line, pour_line)


        preview = self._terrain_preview_for(state)


        if preview is not None and preview.center == (px, py):


            # §15.6 倒出落在自己脚下这一格：登记完可点行号再追加预览，


            # 否则点击映射会整块下移。预览行不占条目。


            for line in preview.lines[1:]:


                text.append("  " + line + "\n", style=PANEL_MUTED)


        text.append(tr("1/左键 盛装 · 2/左键 倒出 · Esc 收起（留在行囊）"), style=PANEL_MUTED)


        return text





    def _equipment_choice_text(self, state: GameState) -> Text:


        text = Text(style=f'bold {FC["heading"]}')


        command = self.equipment_choice.get('command')
        title = ('选择发射来源' if command == 'aim_equipment'
                 else '选择换弹武器' if command == 'reload_weapon_pick'
                 else '本次语句')
        text.append(tr(title) + '\n\n')


        pending = self.equipment_choice


        self._equipment_choice_rows = {}


        for index, option in enumerate(pending['options']):


            line = len(text.plain.splitlines())


            self._equipment_choice_rows[line] = index


            selected = index == pending['cursor']


            emphasis = ' bold underline' if selected else ''


            mark = '▶ ' if selected else '  '


            kind = tr({'melee': '近战', 'fire': '发射', 'spray_liquid': '喷射液体',


                       'spray_gas': '喷射气体', 'aggregate': '聚合弹', 'item': '一次性发射',
                       'reload': '换弹'}.get(option['kind'], option['kind']))


            # §6／§9：序号、机制名与物品名分片着色，名称沿自身身份色。


            text.append(mark, style=FC['condition'] + emphasis)


            text.append(f'{index + 1}. ', style=FC['count'] + emphasis)


            text.append(kind, style=FC['label'] + emphasis)


            text.append(' · ', style=FC['label'] + emphasis)


            for slot, iid in enumerate(option['definition_ids']):


                definition = ITEM_DEFINITIONS.get(iid, {})


                if slot:


                    text.append(' + ', style=FC['label'] + emphasis)


                text.append(tr(LEGACY_BASIC_NAME if iid == LEGACY_BASIC_ID
                               else definition.get('name', iid)),


                            style=panel_color(definition.get('color') or FC['text'])


                            + emphasis)


            if pending.get('command') == 'reload_weapon_pick':
                status = option.get('quote_status') or ''
                if status:
                    text.append(' · ' + status, style=(FC['condition'] if option.get('quote_blocked')
                                                       else FC['count']) + emphasis)
            elif pending.get('command') == 'aim_equipment':
                count = option.get('count')
                if count is not None:
                    text.append(' ×' + str(count), style=FC['count'] + emphasis)
                elif option['kind'] == 'fire' or option['kind'].startswith('spray_'):
                    from .firing_presentation import equipment_resource_text
                    text.append(' · ',style=FC['count']+emphasis)
                    text.append_text(equipment_resource_text(state,option))
                # Disabled sources stay selectable but must state why.
                notes = []
                if option.get('target_pending'):
                    notes.append(tr('待选目标判定'))
                if not option.get('can_fire', True) and option.get('reason'):
                    notes.append(tr(option['reason']))
                if notes:
                    text.append(' · ' + ' · '.join(notes),
                                style=FC['condition'] + emphasis)

            text.append('\n')


        text.append('\n' + tr('↑↓ 选择 · Enter/左键 执行 · 数字直选 · Esc/Q 取消（不耗时）'), style=PANEL_MUTED)


        return text





    def _spray_select_text(self, state: GameState) -> Text:


        """喷射弹药选择浮层（左侧）：列出非空对应容器，一次只喷一种。"""


        text = Text()


        text.append(tr("喷射弹药") + "\n\n", style=f"bold {FC['condition']}")


        rows: list[tuple[int, int]] = []


        selection = self.spray_select.get("cursor", 0)


        for i, (inv_idx, name, kind, amount) in enumerate(self.spray_select.get("options", [])):


            line = len(text.plain.splitlines())


            marker = "▶ " if i == selection else "  "


            style = f"bold underline {FC['condition']}" if i == selection else FC['text']


            text.append(f"{marker}{tr(name)}：{tr(kind)} {amount}\n", style=style)


            rows.append((line, inv_idx))


        self._spray_rows = rows


        text.append("\n" + tr("↑↓ 选择 · Enter/左键 选用 · Esc 取消"), style=PANEL_MUTED)


        return text





    def _lens_offer_text(self, state: GameState) -> Text:


        """§8 S23 青灯祭品浮层（左侧）：从行囊里勾三件易逝物／摄入物喂给门。"""


        text = Text()


        text.append(tr("青灯祭品") + "\n\n", style=f"bold {FC['condition']}")


        text.append(tr("挑三件会消散的东西，喂给守门的青灯。") + "\n\n", style=PANEL_MUTED)


        rows: list[tuple[int, int]] = []


        selected = self.lens_offer_selected


        cursor = self.lens_offer_cursor


        for i, (inv_idx, name, category) in enumerate(self.lens_offer_items):


            line = len(text.plain.splitlines())


            pointer = "▶ " if i == cursor else "  "


            check = "☑ " if inv_idx in selected else "☐ "


            style = f"bold underline {FC['condition']}" if i == cursor else FC['text']


            text.append(f"{pointer}{check}{tr(name)}（{tr(category)}）\n", style=style)


            rows.append((line, inv_idx))


        self._lens_offer_rows = rows


        text.append("\n" + tr("已选 {n}/3", n=len(selected)), style=FC['degree'])


        text.append("\n" + tr("↑↓ 选择 · 空格勾选 · Enter 确认 · Esc 取消"), style=PANEL_MUTED)


        return text





    def _mirror_select_text(self, state: GameState) -> Text:


        """洞察之镜三选一面板：左键点行 / ↑↓+Enter 选定，选完镜子消耗。"""


        text = Text()


        text.append(tr("洞察之镜") + chr(10) + chr(10), style=f"bold {PANEL_MAGENTA}")


        app = self.app


        for i, name in enumerate(app.mirror_rolls):


            marker = "> " if i == app.mirror_cursor else "  "


            style = f"bold underline {PANEL_MAGENTA}" if i == app.mirror_cursor else FC['text']


            text.append(marker + tr(name) + chr(10), style=style)


            text.append("    " + tr(INSIGHT_DEFINITIONS.get(name, "")) + chr(10), style=PANEL_MUTED)


        text.append(chr(10) + tr("↑↓ 选择 · Enter/左键 选定（消耗镜） · Esc 收回"), style=PANEL_MUTED)


        return text
