
# -*- coding: utf-8 -*-
"""自我察觉面板（个人菜单）：分类数值 + 来源展开 + 近期变化（2026-10-18 §10.6）。

- 顶部固定：标题、三条状态条、分类页签；
- 中部按分类显示真实解析值（总览/行动/攻防/感知/恢复/构想篡改/环境/来源）；
- 选中条目可展开基础值、来源、条件说明；总览末尾显示最近资源结算与行动耗时；
- 键盘 ←→ 切换分类、↑↓ 选择、Enter/空格展开、Esc 关闭；鼠标点击页签/条目同样生效；
- 滚轮只作用于面板；所有数值来自 core/stats 与 self_audit，不在这里另算。
"""

from __future__ import annotations

from rich.cells import cell_len
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..core.self_audit import self_audit
from ..i18n import get_language, tr
from .styles import BAR_IMAGINATION_STYLES, BAR_LUCIDITY_STYLES, BAR_MIND_STYLES
from .panel_fields import FIELD_COLORS, rich_lines, stat_color
from .home_scene import FixedFrameStatic
from .world_renderer import WorldCanvas

PANEL_MUTED = FIELD_COLORS['muted']
BAR_STYLE_SETS = (BAR_MIND_STYLES, BAR_LUCIDITY_STYLES, BAR_IMAGINATION_STYLES)

SA_CATEGORIES = (
    ("overview", "总览"),
    ("action", "行动"),
    ("offense", "攻防"),
    ("perception", "感知"),
    ("recovery", "恢复"),
    ("ability", "构想/篡改"),
    ("environment", "环境"),
    ("sources", "来源"),
)
_CATEGORY_IDS = tuple(key for key, _ in SA_CATEGORIES)
_CATEGORY_LABELS = dict(SA_CATEGORIES)

# 分类页签逐类取色：只从第十九节 §10.1 的注册表键取，面板里不留 hex 字面量。
# 八色两两按纸感分区的可分判据成立（色相差 ≥20° 或 亮度比 ≥1.25 或 饱和度比 ≥1.6），
# 对自我察觉面板底 #292930 与四套区域主题底都 ≥4.5。激活/焦点仍由「〔〕＋粗体」
# 承担，识别不只靠颜色（tests/test_panel_field_colors.py 的既有口径）。
SA_CATEGORY_STYLES = {
    "overview": FIELD_COLORS['heading'],      # 总览：最亮的中性色，落在默认页
    "action": FIELD_COLORS['time'],           # 行动：与行动耗时/动作时间同族
    "offense": FIELD_COLORS['damage'],        # 攻防
    "perception": FIELD_COLORS['lucidity'],   # 感知
    "recovery": FIELD_COLORS['effect'],       # 恢复
    "ability": FIELD_COLORS['puppet'],        # 构想/篡改：紫色系，与构想页一致
    "environment": FIELD_COLORS['condition'], # 环境
    "sources": FIELD_COLORS['identity'],      # 来源
}


class ClickableStatus(WorldCanvas, FixedFrameStatic):
    """顶部状态区：点整块区域（三行属性条）开合自我察觉面板。

    2026-10-24 纸感分区·状态区合并：宽屏档第 5 行并进了「噪音 / 混乱」
    两项（#signal-status 整行隐藏），行上这两段的列区由 _refresh_world_view
    记在 app 的 ``_status_signal_hits``——命中时走 #signal-status 的现有
    链路（toggle_signal_detail），点其余区域维持整块开合自我察觉。
    窄屏两行档（_status_signal_hits 为 None）点击行为与旧版完全一致。

    2026-10-24 玩家优化 6：**第 1 行是层信息入口**——点击打开左侧层详情
    面板（层名/修饰符/层型含义），与下方属性条（个人信息页入口）行为分离。
    """

    DEFAULT_CSS = "ClickableStatus { width: 100%; height: 5; }"

    def on_mouse_down(self, event) -> None:
        row = int(getattr(event, 'y', -1))
        if row == 0:
            # 2026-10-27 玩家需求：第 1 行最右 2 列是本帧画出的锁图标
            # （列区由 _refresh_world_view 记在 _status_lock_hits）。命中时
            # 复用 ~ 键的开关（toggle_cursor_lock），其余列仍是层详情入口。
            lock_hits = getattr(self.app, '_status_lock_hits', None)
            column = int(getattr(event, 'x', -1))
            if lock_hits and lock_hits[0] <= column < lock_hits[1]:
                toggle = getattr(self.app, 'toggle_cursor_lock', None)
                if toggle is not None:
                    toggle()
                event.stop()
                return
            handler = getattr(self.app, "_toggle_layer_info", None)
            if handler is not None:
                handler()
            event.stop()
            return
        hits = getattr(self.app, '_status_signal_hits', None)
        if hits and row == hits.get('row', 4):
            column = int(getattr(event, 'x', -1))
            for key in ('noise', 'chaos'):
                start, end = hits[key]
                if start <= column < end:
                    opener = getattr(self.app, 'toggle_signal_detail', None)
                    if opener is not None:
                        opener()
                    event.stop()
                    return
        handler = getattr(self.app, "_toggle_self_audit", None)
        if handler is not None:
            handler()
        event.stop()


class SelfAuditPane(VerticalScroll):
    """左侧栏本体：可滚动容器；点击正文由 app 做命中测试。"""

    def on_mount(self) -> None:
        self.display = False

    def on_mouse_down(self, event) -> None:
        self.app._select_input_region('overlay')
        handler = getattr(self.app, "_self_audit_click", None)
        if handler is not None and self.display:
            try:
                line = int(event.y) + int(getattr(self, "scroll_y", 0) or 0)
                handler(line, int(event.x))
                event.stop()
                return
            except Exception:
                pass
        try:
            event.stop()
        except Exception:
            pass


class SelfAuditMixin:
    """自我察觉面板的路由与渲染（挂在 DreamApp 上）。"""

    def _self_audit_visible(self) -> bool:
        try:
            return bool(self.query_one("#self-pane").display)
        except Exception:
            return False

    def _self_audit_ensure_state(self) -> None:
        if not hasattr(self, "_sa_category"):
            self._sa_category = "overview"
        if not hasattr(self, "_sa_cursor"):
            self._sa_cursor = 0
        if not hasattr(self, "_sa_expanded"):
            self._sa_expanded = set()
        if not hasattr(self, "_sa_line_actions"):
            self._sa_line_actions = {}
        if not hasattr(self, "_sa_last_sections"):
            self._sa_last_sections = {}
        if not hasattr(self, "_sa_last_data"):
            self._sa_last_data = None

    def _close_self_audit(self, *, refresh: bool = True) -> None:
        try:
            self.query_one("#self-pane").display = False
        except Exception:
            return
        focus=getattr(self,'_self_audit_focus',None)
        if focus is not None and focus.is_mounted and focus.display:
            focus.focus()
        else:
            self.set_focus(None)
        if refresh:
            self.refresh_view()

    def _toggle_self_audit(self) -> None:
        if self._self_audit_visible():
            self._close_self_audit()
            return
        if not self._can_open_inspection():
            return
        if self.signal_detail_open:
            self.close_signal_detail()
        # 层详情面板与自我察觉互斥（2026-10-24 玩家优化 6）：同是左侧悬浮层。
        if getattr(self, '_layer_info_visible', None) and self._layer_info_visible():
            self._close_layer_info(refresh=False)
        self._self_audit_ensure_state()
        self._self_audit_focus=self.focused
        state = self.session.state
        self._self_context = (id(state), state.depth, state.realm_id, state.realm_depth)
        pane = self.query_one('#self-pane')
        pane.display = True
        self._select_input_region('overlay')
        self._sa_cursor = 0
        self._clear_held()
        pane.scroll_home(animate=False)
        self.refresh_view()

    def _refresh_self_audit(self, state) -> None:
        try:
            pane = self.query_one("#self-pane")
            body = pane.query_one("#self-audit-body", Static)
        except Exception:
            return
        if not pane.display:
            return
        if (self.home_mode or state.run_over or getattr(self, '_self_context', None) !=
                (id(state), state.depth, state.realm_id, state.realm_depth)):
            self._close_self_audit(refresh=False)
            return
        self._fit_inspection_pane(pane)
        try:
            body.update(self._self_audit_text(state, body))
        except Exception:
            body.update(Text(tr("状态读取失败。"), style=PANEL_MUTED))

    def _scroll_self_audit(self, event, direction: int) -> bool:
        """鼠标在面板区域内时，滚轮只滚面板文字；返回 True 表示已消费。"""
        try:
            pane = self.query_one("#self-pane")
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

    # ---- 键盘 / 鼠标命中 ----

    def _self_audit_key(self, key: str) -> bool:
        """面板打开时的按键：分类/选择/展开/关闭；返回是否消费。"""
        if not self._self_audit_visible():
            return False
        self._self_audit_ensure_state()
        if key in ("escape",):
            self._close_self_audit()
            return True
        if key in ("left", "right", "tab", "shift+tab"):
            index = _CATEGORY_IDS.index(self._sa_category) if self._sa_category in _CATEGORY_IDS else 0
            step = -1 if key in ("left", "shift+tab") else 1
            self._sa_category = _CATEGORY_IDS[(index + step) % len(_CATEGORY_IDS)]
            self._sa_cursor = 0
            self.refresh_view()
            return True
        rows = self._sa_last_sections.get(self._sa_category, [])
        if key in ("up", "down") and rows:
            step = -1 if key == "up" else 1
            self._sa_cursor = max(0, min(len(rows) - 1, self._sa_cursor + step))
            self.refresh_view()
            self._self_audit_scroll_to_cursor()
            return True
        if key in ("enter", "return", "space") and rows:
            row = rows[max(0, min(len(rows) - 1, self._sa_cursor))]
            token = (self._sa_category, row["key"])
            if token in self._sa_expanded:
                self._sa_expanded.discard(token)
            else:
                self._sa_expanded.add(token)
            self.refresh_view()
            self._self_audit_scroll_to_cursor()
            return True
        return False

    def _self_audit_click(self, line: int, x: int = 0) -> bool:
        """鼠标点击页签或条目：切换分类 / 选中并展开。"""
        if not self._self_audit_visible():
            return False
        self._self_audit_ensure_state()
        action = self._sa_line_actions.get(int(line))
        if not action:
            return False
        kind = action[0]
        if kind == "tabs":
            for start, end, category in action[1]:
                if start <= x < end:
                    self._sa_category = category
                    self._sa_cursor = 0
                    self.refresh_view()
                    return True
            return False
        if kind == "row":
            index = int(action[1])
            rows = self._sa_last_sections.get(self._sa_category, [])
            if not rows:
                return False
            self._sa_cursor = max(0, min(len(rows) - 1, index))
            row = rows[self._sa_cursor]
            token = (self._sa_category, row["key"])
            if token in self._sa_expanded:
                self._sa_expanded.discard(token)
            else:
                self._sa_expanded.add(token)
            self.refresh_view()
            return True
        return False

    def _self_audit_scroll_to_cursor(self) -> None:
        try:
            pane = self.query_one("#self-pane")
            line = next((index for index, action in self._sa_line_actions.items()
                         if action and action[0] == "row" and action[1] == self._sa_cursor),
                        None)
            if line is not None:
                pane.scroll_to(y=max(0, line - 2), animate=False)
        except Exception:
            pass

    # ---- 渲染 ----

    def _self_audit_text(self, state, body=None) -> Text:
        data = self_audit(state)
        self._self_audit_ensure_state()
        self._sa_last_data = data
        sections = data.get("sections") or {}
        self._sa_last_sections = sections
        if self._sa_category not in sections and sections:
            self._sa_category = next(iter(sections))
        rows = sections.get(self._sa_category, [])
        self._sa_cursor = max(0, min(self._sa_cursor, max(0, len(rows) - 1)))

        width = 0
        if body is not None:
            width = body.content_size.width or 0
        width = max(24, (width or 56) - 1)

        lines: list[Text] = []
        actions: dict[int, tuple] = {}

        def add(line: Text, action: tuple | None = None) -> None:
            if action is not None:
                actions[len(lines)] = action
            lines.append(line)

        def wrapped(content: str, style: str = "", prefix: str = "") -> list[str]:
            return [prefix + part for part in _wrap(content, max(8, width - cell_len(prefix)))]

        # ---- 顶部固定：标题、状态条 ----
        title = Text(tr("自我察觉"), style="bold bright_white")
        title.append("  " + tr("（我的状态·来源·近期变化）"), style="#aab0c2")
        add(title)
        from ..data.semantic_icons import semantic_icon
        bar_icons = ("stat.mind", "stat.lucidity", "stat.imagination")
        icons = [semantic_icon(key) for key in bar_icons]
        icon_pad = 2 if any(icons) else 0
        # 标签取实际的（可能已英译）显示文字量宽：英文 Mind/Lucidity/Imagination
        # 比中文标签宽得多，用中文键量宽会让三条的条起点各走各的。
        label_width = max(6, *(cell_len(str(row[0])) for row in data["bars"])) + icon_pad
        value_width = max(cell_len(f"{maximum}/{maximum}") for _, _, maximum, _ in data["bars"])
        suffix_width = max([cell_len(tr(label)) for _, _, _, label in data["bars"] if label] or [0])
        bar_width = max(4, min(20, width - label_width - value_width - suffix_width - 2))
        for index, (label, value, maximum, tier_label) in enumerate(data["bars"]):
            if index < len(icons) and icons[index]:
                label = icons[index] + label
            styles = BAR_STYLE_SETS[min(index, len(BAR_STYLE_SETS) - 1)]
            suffix = f"  {tier_label}" if tier_label else ""
            line = Text()
            line.append(self._bar(label, value, maximum, styles, width=bar_width,
                                  suffix=suffix, label_width=label_width,
                                  value_width=value_width))
            add(line)

        # ---- 分类页签 ----
        tab_line = Text()
        tab_hits: list[tuple[int, int, str]] = []
        col = 0
        for category, label in SA_CATEGORIES:
            active = category == self._sa_category
            # EN 用 ASCII 方括号；中文保留〔〕（2026-10-28 全界面审计）。
            bracket = ("[", "]") if get_language().startswith("en") else ("〔", "〕")
            token = ((bracket[0] + tr(label) + bracket[1]) if active
                     else (" " + tr(label) + " "))
            token_width = cell_len(token)
            if col and col + token_width > width:
                actions[len(lines)] = ("tabs", tab_hits)
                add(tab_line)
                tab_line = Text()
                tab_hits = []
                col = 0
            start = col
            tab_line.append(token, style=("bold " if active else "")
                            + SA_CATEGORY_STYLES.get(category, FIELD_COLORS['muted']))
            col += token_width
            tab_hits.append((start, col, category))
        add(tab_line, ("tabs", tab_hits))
        add(Text(tr("←→ 切换分类 · ↑↓ 选择 · Enter/空格 展开 · Esc 关闭"), style="#aab0c2"))

        # ---- 分类内容 ----
        if not rows:
            add(Text(tr("这个分类暂时没有可显示的内容。"), style=PANEL_MUTED))
        for index, row in enumerate(rows):
            focused = index == self._sa_cursor
            marker = "▸ " if focused else "  "
            label = str(row.get("label", ""))
            value = str(row.get("value", ""))
            status = str(row.get("status", ""))
            head = f"{marker}{label}"
            pad = max(1, min(18, 18 - cell_len(head)))
            line = Text()
            line.append(marker, style="bold bright_cyan" if focused else "#aab0c2")
            color = stat_color(row.get('stat_id', ''), state)
            from ..data.semantic_icons import semantic_icon, icon_color, entry as icon_entry
            stat_prefix = str(row.get('stat_id', '') or '').split('.', 1)[0]
            icon_key = {
                'mind': 'stat.mind', 'lucidity': 'stat.lucidity',
                'imagination': 'stat.imagination', 'chaos': 'stat.chaos',
                'integrity': 'stat.integrity', 'collapse': 'stat.collapse',
                'endurance': 'stat.endurance',
            }.get(stat_prefix, '')
            attribute_key = 'attribute.' + str(row.get('stat_id', '') or '')
            if icon_entry(attribute_key):
                icon_key = attribute_key
            stat_icon = semantic_icon(icon_key)
            if stat_icon:
                line.append(stat_icon + ' ', style=icon_color(icon_key, color))
            line.append(label, style=('bold ' if focused else '') + color)
            line.append(" " * pad)
            line.append(value, style=color)
            if status:
                line.append("  [" + tr(status) + "]", style="#e5c780")
            for part in rich_lines(line, width, continuation='    '):
                add(part, ('row', index))
            token = (self._sa_category, row.get("key"))
            if token in self._sa_expanded:
                base = row.get("base")
                if base is not None:
                    add(Text('      ' + tr('基础值：') + _number(base), style=FIELD_COLORS['count']), ('row', index))
                for source in row.get("sources", ()):
                    for part in wrapped(str(source), style="#aab0c2", prefix="      " + tr("来源：")):
                        add(Text(part, style=FIELD_COLORS['grammar']), ("row", index))
                for note in row.get("notes", ()):
                    for part in wrapped(str(note), style="#aab0c2", prefix="      " + tr("说明：")):
                        add(Text(part, style=FIELD_COLORS['condition']), ("row", index))
                if not row.get("sources") and not row.get("notes") and base is None:
                    add(Text("      " + tr("无额外来源或条件。"), style="#aab0c2"), ("row", index))

        # ---- 总览底部：近期变化 ----
        if self._sa_category == "overview":
            add(Text(""))
            add(Text(tr("近期变化（有界内存，不写存档）"), style="bold bright_white"))
            recent = data.get("recent") or []
            if not recent:
                add(Text("  " + tr("尚无资源结算记录。"), style=PANEL_MUTED))
            # 旧档可能保存的是已经格式化好的整句，而不是 source/reason ID。
            # 这类文本不能按新语言重译，明确提示“保留原文”，避免玩家误以为漏翻。
            if any(any("\u4e00" <= ch <= "\u9fff" for ch in _recent_text(entry))
                   for entry in recent[-5:]):
                add(Text("  " + tr("旧版格式化记录保留原文，不自动重译。"), style=PANEL_MUTED))
            for entry in recent[-5:]:
                add(_recent_rich(entry))
            actions_recent = data.get("recent_actions") or []
            for record in actions_recent[-3:]:
                add(Text("  " + _action_time_text(record), style=FIELD_COLORS['time']))

        text = Text()
        for index, line in enumerate(lines):
            if index:
                text.append("\n")
            text.append_text(line)
        self._sa_line_actions = actions
        return text


def _number(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:g}"


def _wrap(content: str, width: int) -> list[str]:
    try:
        from rich.cells import cell_len
    except Exception:
        return [content]
    lines: list[str] = []
    current = ""
    used = 0
    for char in content:
        cost = 2 if cell_len(char) > 1 else 1
        if used + cost > width and current:
            lines.append(current)
            current, used = char, cost
        else:
            current += char
            used += cost
    if current:
        lines.append(current)
    return lines or [content]


_RESOURCE_LABELS = {"mind": "心智", "lucidity": "清醒", "imagination": "想象"}
_SETTLEMENT_REASONS = {
    'combat':'战斗创伤','environment':'环境影响','ability_cost':'构想费用',
    'tamper_cost':'篡改费用','trade_cost':'交易费用','restore_natural':'自然恢复',
    'restore_item':'物品恢复','restore_scene':'场景恢复','restore_derived':'派生恢复',
    'story':'剧情变化','max_change':'上限变化','debug':'调试变化',
}
_SETTLEMENT_BLOCKS = {'at_zero':'资源已归零','at_max':'达到上限',
                      'mind_loss_blocked':'心智流失免疫','stasis':'凝滞','no_amount':'没有可恢复量'}


def _recent_source(entry):
    source=str(entry.get('source') or '')
    if source.startswith('ability:'):
        from ..data.abilities import ABILITY_DEFINITIONS
        definition=ABILITY_DEFINITIONS.get(source.partition(':')[2])
        if definition is not None: return tr(definition['name'])
    return tr(source) if source else tr(_SETTLEMENT_REASONS.get(entry.get('reason'),entry.get('reason') or ''))


def _recent_rich(entry):
    resource=str(entry.get('resource',''))
    color=FIELD_COLORS.get(resource,FIELD_COLORS['count'])
    amount=float(entry.get('applied',0))
    text=Text('  '+tr(_RESOURCE_LABELS.get(resource,resource)),style=color)
    text.append(f' {amount:+g}' if amount else ' 0',style=color)
    opening, closing = (('(', ')') if get_language().startswith('en')
                        else ('（', '）'))
    text.append(opening,style=FIELD_COLORS['muted'])
    text.append(_recent_source(entry),style=FIELD_COLORS['grammar'])
    if entry.get('blocked'):
        text.append(' · '+tr(_SETTLEMENT_BLOCKS.get(entry['blocked'],entry['blocked'])),style=FIELD_COLORS['risk'])
    text.append(closing,style=FIELD_COLORS['muted'])
    return text


def _recent_text(entry: dict) -> str:
    return _recent_rich(entry).plain.strip()


_ACTION_KIND_LABELS = {
    "MOVE": "移动", "ATTACK": "攻击", "USE": "使用", "FREE": "免费", "MISC": "杂项",
}


def _action_time_text(record: dict) -> str:
    raw_kind = str(record.get("kind", ""))
    kind = _ACTION_KIND_LABELS.get(raw_kind.rsplit(".", 1)[-1], raw_kind)
    base = float(record.get("base", 0) or 0)
    paid = float(record.get("paid", 0) or 0)
    extra = float(record.get("extra", 0) or 0)
    extra_text = f" + " + tr("额外 {n:g}", n=extra) if extra else ""
    return tr("行动 {kind}：基础 {base:g} → 实付 {paid:g}{extra}",
              kind=tr(kind), base=base, paid=paid, extra=extra_text)
