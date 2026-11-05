"""测试模式调试面板（2026-09-18）：L 键唤起的左侧宽面板。

左右两列（textual 的 Horizontal 分区 + ``Rule(orientation="vertical")`` 竖线
隔开）：左列 13 个分类，右列该分类下的全部条目——右列**自身再分两列**
（2026-10-12 用户要求）：偶数下标在左半靠左边界、奇数下标在右半靠右边界，
一屏看两倍条目；点击点哪半选哪半，键盘 ↑↓ 仍按逻辑下标逐个移动。两列
都支持鼠标点击与 ws/↑↓ 键选中滚动。确认（左键/Enter）后按小写 l 在鼠标
悬停格（或观察模式的 ? 格）释放；洞察/构想确认即直接给自己；征兆只能
释放在自己或意识体所在格。底部提供清空洞察/构想/征兆/行囊四个快捷项，
征兆可选回合数与层数。

「移动」分类（2026-09-21，追加在末尾）：下潜 / 上浮 / 传送。选中后按小写 l
执行——上下楼**无视崩解度**（走 ``app._apply_floor_change(ignore_dissolution=True)``，
演出/视口重算照常），传送落在 l 指向的空地（观察 ? 优先 > 鼠标悬停），
越界 / 实心 / 已有意识体一律拒绝并写明原因。
"""

from __future__ import annotations
from .action_completion import after_action

from rich.cells import cell_len
from rich.text import Text

from ..core.content import (
    ABILITY_DEFINITIONS,
    ANOMALY_DEFINITIONS,
    INSIGHT_DEFINITIONS,
    ITEM_DEFINITIONS,
    NPC_DEFINITIONS,
)
from ..i18n import tr
from ..materials import (
    FLOOR_DEFINITIONS,
    GAS_DEFINITIONS,
    LIQUID_DEFINITIONS,
    PORTENT_DEFINITIONS,
    SOLID_KINDS,
    WALL_DEFINITIONS,
    portent_def,
)
from .styles import PORTENT_HINT_STYLE as DEBUG_HINT_STYLE

# 分类顺序即左列显示顺序。
# ⚠️ 「移动」**必须追加在末尾**（2026-09-21）：既有的键位导航与测试都是按
# 「按几次 ↓ 到第几个分类」定位的（液体 3 / 异象 5 / 构想 9 / 征兆 11…），
# 插到中间会把它们的下标整体推后。新增分类一律追加。
DEBUG_CATEGORIES: tuple[str, ...] = (
    "地板", "墙体", "固体", "液体", "气体",
    "异象", "其他意识体", "携带意象", "其他物品",
    "构想", "洞察", "征兆",
    "移动", "自我增强",
)

# 「移动」类目的条目：上下楼无视崩解度；传送只落空地。
# 扩展：梦中梦（门之回廊/玩具的回忆/余烬廊桥/退潮厅/千禧园各层）+ 深层边界（28-30）。
# ⚠️ 新 realm 条目一律追加在末尾（与 DEBUG_CATEGORIES 同一纪律：测试按下标定位）。
DEBUG_MOVES: tuple[str, ...] = (
    "下潜", "上浮", "传送",
    "门之回廊·第1层", "门之回廊·第2层", "门之回廊·第3层",
    "玩具的回忆·第1层", "玩具的回忆·第2层", "玩具的回忆·第3层", "玩具的回忆·第4层",
    "深层边界·28", "深层边界·29", "深层边界·30",
    "余烬廊桥·第1层", "退潮厅·第1层",
    "千禧园·第1层", "千禧园·第2层", "千禧园·第3层", "千禧园·第4层", "千禧园·第5层",
    "未尽藏书宫·第1层", "未尽藏书宫·第2层", "未尽藏书宫·第3层", "未尽藏书宫·第4层", "未尽藏书宫·第5层",
    "至白疗所·第1层", "至白疗所·第2层", "至白疗所·第3层", "至白疗所·第4层", "至白疗所·第5层",
)

# 「自我增强」类目的条目：前 4 个 l 键开关，后 3 个 l 键触发。
DEBUG_BOOSTS: tuple[str, ...] = (
    "全图视野", "心智无敌", "清醒无敌", "想象无限",
    "回满心智", "回满清醒", "回满想象",
)

# 「固体」= 独立固体/地面容器/台子（木桌子/石台）/新式固体（其余墙种归「墙体」；
# 门/意识边界/灰烬由机制产生，不进面板）。2026-09-19：改用 materials.walls 的
# SOLID_KINDS 单一来源——旧硬编码清单漏掉了木桌子/石台，测试界面里它们被错挂在「墙体」。
DEBUG_SOLID_KINDS: tuple[str, ...] = tuple(
    name for name in SOLID_KINDS if name in WALL_DEFINITIONS
)

# 每列可见行数：右列放宽到 26 行，减少下方留白、一次看到更多条目。
DEBUG_VIEW_ROWS = 26


def debug_items_for(category: str) -> list[str]:
    """分类 → 可选条目清单（名称或 id）。"""
    if category == "地板":
        return list(FLOOR_DEFINITIONS)
    if category == "墙体":
        return [
            name for name in WALL_DEFINITIONS
            if name not in DEBUG_SOLID_KINDS and name not in ("门", "意识边界", "灰烬")
        ]
    if category == "固体":
        return list(DEBUG_SOLID_KINDS)
    if category == "液体":
        return list(LIQUID_DEFINITIONS)
    if category == "气体":
        return list(GAS_DEFINITIONS)
    if category == "异象":
        return list(ANOMALY_DEFINITIONS)
    if category == "其他意识体":
        return list(NPC_DEFINITIONS)
    if category == "携带意象":
        return [item_id for item_id, definition in ITEM_DEFINITIONS.items()
                if definition.get("slot") or definition.get("category") == "携带意象"]
    if category == "其他物品":
        return [item_id for item_id, definition in ITEM_DEFINITIONS.items()
                if not definition.get("slot") and definition.get("category") != "携带意象"]
    if category == "构想":
        return list(ABILITY_DEFINITIONS)
    if category == "洞察":
        return list(INSIGHT_DEFINITIONS)
    if category == "征兆":
        return list(PORTENT_DEFINITIONS)
    if category == "移动":
        return list(DEBUG_MOVES)
    if category == "自我增强":
        return list(DEBUG_BOOSTS)
    return []


class DebugPanelMixin:
    """调试面板的状态、渲染与交互（挂到 DreamApp 上，仅测试模式生效）。"""

    # ---- 面板开关与释放 ----

    def _debug_toggle_or_spawn(self, *, spawn: bool = False) -> None:
        """调试键总入口（大小写区分，2026-09-18）：

        - 大写 L → 纯开关面板（开↔关；关时不保留待释放物）；
        - 小写 l → 放置：有待释放物才在目标格（观察 ? 优先 > 鼠标悬停）释放。
        """
        if not self.test_mode:
            return
        if spawn:
            self._debug_spawn_from_target()
            return
        self.debug_panel_open = not self.debug_panel_open
        if not self.debug_panel_open:
            self.debug_pending = None
        self.refresh_view()

    def _debug_spawn_from_target(self) -> None:
        """小写 l：在目标格（观察 ? 或鼠标悬停）释放待释放物。

        「移动」类目复用同一入口（用户要求「选中下潜和上浮后按 l 即可」）：
        上下楼不看目标格，传送才要（见 :meth:`_debug_move`）。
        """
        if self.debug_pending is None:
            return
        category, item = self.debug_pending
        target = self.observe_cursor if self.observe_mode else self.hover_cell
        if category == "移动":
            self._debug_move(item, target)
        elif category == "自我增强":
            self._debug_boost(item)
        elif target is None:
            self.session.apply('ui_control', 'debug_notice', 'no_spawn_target')
        else:
            self._debug_spawn_at(target[0], target[1])
        self.refresh_view()

    def _debug_adjust_param(self, delta: int) -> None:
        """-= 调整当前选中的征兆参数（选中哪个调哪个；未选征兆时不生效）。

        上下限：回合数 1–99，层数 1–9。
        """
        if self.debug_pending is None or self.debug_pending[0] != "征兆":
            return
        if self.debug_param == 0:
            self.debug_portent_rounds = max(1, min(99, self.debug_portent_rounds + delta))
        else:
            self.debug_portent_stacks = max(1, min(9, self.debug_portent_stacks + delta))
        self.refresh_view()

    def _debug_spawn_at(self, x: int, y: int) -> bool:
        """Submit a placement to the session owner, preserving the UI selection."""
        if self.debug_pending is None:
            return False
        category, item = self.debug_pending
        result = self.session.apply('ui_control', 'debug_spawn', category, item, x, y,
                                    self.debug_portent_rounds, self.debug_portent_stacks)
        return after_action(self, result, lambda actual: actual.changed)

    # ---- 移动（上下楼 / 传送，2026-09-21）----

    def _debug_move(self, item: str, target: tuple[int, int] | None) -> bool:
        """「移动」类目的执行体（由小写 l 触发）。

        - **下潜 / 上浮**：无视崩解度。只跳过「崩解度 ≥100」那道发育门槛，
          层数上限、清醒度消耗与不足时的心智创伤、行动时间照常结算；被规则
          拒绝时把原因写进事件记录（state 自己只放在 ActionResult.message 里，
          不写进记录，不转述就会「按了没反应」）。
        - **传送**：落在 l 指向的空地（观察 ? 优先 > 鼠标悬停），非法目标
          一律拒绝并说明原因。
        - **梦中梦/深层边界**（2026-09-22 扩展）：直跳指定层，见 :meth:`_debug_jump`。
        """
        if item in ("下潜", "上浮"):
            command = "descend" if item == "下潜" else "backtrack"
            # 走 _apply_floor_change：演出/视口重算/区域主题全都照正常上下楼走。
            result = self._apply_floor_change(command, ignore_dissolution=True)
            def finish(result):
                self.session.apply('ui_control', 'debug_notice', 'floor_result',
                                   item, result.changed, result.message)
                return result.changed
            return after_action(self, result, finish)
        if item == "传送":
            if target is None:
                self.session.apply('ui_control', 'debug_notice', 'no_teleport_target')
                return False
            return self._debug_teleport(target[0], target[1])
        # ---- 梦中梦各层 / 深层边界（2026-09-22 扩展）----
        return self._debug_jump(item)

    def _debug_jump(self, item: str) -> bool:
        """Jump/archive/generate entirely under the session's mutation lock."""
        result = self.session.apply('ui_control', 'debug_jump', item)
        return after_action(self, result, lambda actual: actual.changed)

    def _debug_boost(self, item: str) -> bool:
        result = self.session.apply('ui_control', 'debug_boost', item)
        return after_action(self, result, lambda actual: actual.changed)

    def _debug_teleport(self, x: int, y: int) -> bool:
        result = self.session.apply('ui_control', 'debug_teleport', x, y)
        return after_action(self, result, lambda actual: actual.changed)

    # ---- 确认选择 ----

    def _debug_confirm(self) -> None:
        """Keep selection in the UI and send grants/feedback to the owner."""
        category = DEBUG_CATEGORIES[self.debug_category]
        items = debug_items_for(category)
        if not items:
            return
        item = items[min(self.debug_item, len(items) - 1)]
        if category in ('构想', '洞察'):
            self.debug_pending = None
            self.session.apply('ui_control', 'debug_grant', category, item)
        else:
            self.debug_pending = category, item
            code = 'selected_execute' if category in ('移动', '自我增强') else 'selected_spawn'
            self.session.apply('ui_control', 'debug_notice', code, item)
        self.refresh_view()

    # ---- 光标与滚动 ----

    def _debug_move_cursor(self, delta: int) -> None:
        if self.debug_side == "left":
            count = len(DEBUG_CATEGORIES)
            self.debug_category = max(0, min(count - 1, self.debug_category + delta))
            self.debug_item = 0
            self.debug_right_scroll = 0
            self.debug_left_scroll = self._debug_clamp_scroll(self.debug_left_scroll, self.debug_category, count)
        else:
            count = len(debug_items_for(DEBUG_CATEGORIES[self.debug_category]))
            self.debug_item = max(0, min(count - 1, self.debug_item + delta))
            # 右列是两列布局：一屏条目数是行数的两倍（2026-10-12）。
            self.debug_right_scroll = self._debug_clamp_scroll(
                self.debug_right_scroll, self.debug_item, count,
                rows=DEBUG_VIEW_ROWS * 2)
        self.refresh_view()

    @staticmethod
    def _debug_clamp_scroll(scroll: int, cursor: int, count: int,
                            rows: int = DEBUG_VIEW_ROWS) -> int:
        """把滚动钳到「光标落在可视窗口内」；``rows`` 是一屏能看到的**条目数**。"""
        if cursor < scroll:
            return cursor
        if cursor >= scroll + rows:
            return cursor - rows + 1
        return max(0, min(scroll, max(0, count - rows)))

    def _debug_scroll_side(self, side: str, delta: int) -> None:
        """滚轮分区滚动：左列滚分类光标、右列滚条目光标（互不串扰）。"""
        self.debug_side = side
        self._debug_move_cursor(delta)

    def _debug_switch_side(self) -> None:
        self.debug_side = "right" if self.debug_side == "left" else "left"
        self.refresh_view()

    # ---- 一键清空 ----

    def _debug_clear(self, which: int) -> None:
        self.session.apply('ui_control', 'debug_clear', which)
        self.refresh_view()

    # ---- 渲染 ----

    def _refresh_debug_panel(self) -> None:
        """把左右两列写进 #debug-left / #debug-right（面板未开时跳过）。"""
        if not self.debug_panel_open or not self.test_mode:
            return
        from textual.widgets import Static

        state = self.session.state
        left = Text()
        left.append(tr("分类") + "\n", style="bold #3ddad0")
        for index, category in enumerate(DEBUG_CATEGORIES):
            marker = "▶ " if (index == self.debug_category and self.debug_side == "left") else "  "
            style = "bold bright_yellow" if index == self.debug_category else "bright_cyan"
            if index == self.debug_category:
                style += " reverse" if self.debug_side == "left" else ""
            shown = tr(category) + (f" ({len(debug_items_for(category))})" if index == self.debug_category else "")
            left.append(f"{marker}{shown}\n", style=style)
        left.append("\n" + tr("Tab/←→ 换列 · ↑↓/wasd 移动"), style=DEBUG_HINT_STYLE)

        right = Text()
        category = DEBUG_CATEGORIES[self.debug_category]
        items = debug_items_for(category)
        right.append(f"{tr(category)} · {len(items)}\n", style="bold #3ddad0")
        # 右列两列布局（2026-10-12 用户要求）：偶数下标在左半、奇数下标在右半，
        # 左列靠左边界、右列靠右边界——一屏看两倍条目，扫视不串行。
        right_width = self._debug_right_width()
        visible = DEBUG_VIEW_ROWS * 2
        window = items[self.debug_right_scroll:self.debug_right_scroll + visible]
        for row_start in range(0, len(window), 2):
            segments: list[tuple[Text, int] | None] = []
            for column in range(2):
                index = self.debug_right_scroll + row_start + column
                if index >= len(items):
                    segments.append(None)
                    continue
                marker = "▶ " if (index == self.debug_item and self.debug_side == "right") else "  "
                style = "bright_white" if index == self.debug_item else "grey85"
                if index == self.debug_item:
                    style += " reverse" if self.debug_side == "right" else ""
                label = self._debug_item_label(category, items[index], state)
                cell = Text(f"{marker}{label}", style=style)
                segments.append((cell, cell_len(f"{marker}{label}")))
            line = Text()
            left_seg, right_seg = segments
            if left_seg is not None:
                line.append_text(left_seg[0])
            if right_seg is not None:
                pad = max(1, right_width - (left_seg[1] if left_seg is not None else 0) - right_seg[1])
                line.append(" " * pad)
                line.append_text(right_seg[0])
            right.append_text(line)
            right.append("\n")
        # 待释放提示 + 征兆参数 + 清空快捷项。
        if self.debug_pending is not None:
            pend_cat, pend_item = self.debug_pending
            # 「移动」不看光标格（只有传送才要），提示语与释放类分开。
            hint = ("已选择：{item}（{cat}）· 按 l 执行" if pend_cat in ("移动", "自我增强")
                    else "已选择：{item}（{cat}）· l 在光标格释放")
            right.append(
                "\n" + tr(hint, item=tr(pend_item), cat=tr(pend_cat)),
                style="bold bright_yellow",
            )
        if category == "征兆" and self.debug_pending is not None and self.debug_pending[0] == "征兆":
            current = portent_def(self.debug_pending[1])
            stack_note = tr("（无层数，层数无效）") if current is not None and current.stacks <= 0 else ""
            mark_rounds = "▶ " if self.debug_param == 0 else "  "
            mark_stacks = "▶ " if self.debug_param == 1 else "  "
            right.append(
                f"\n{mark_rounds}{tr('回合数')} {self.debug_portent_rounds}"
                f"   {mark_stacks}{tr('层数')} {self.debug_portent_stacks} {stack_note}",
                style="bold bright_yellow",
            )
            right.append(tr("-/= 调整（回合 1–99 · 层 1–9） · l 放置"), style=DEBUG_HINT_STYLE)
        if category == "移动":
            right.append(
                "\n" + tr("下潜/上浮无视崩解度 · 传送落 l 指向的空地（观察 ? 或鼠标光标），非法目标拒绝"),
                style=DEBUG_HINT_STYLE,
            )
        if category == "自我增强":
            right.append(
                "\n" + tr("前四项按 l 开/关（条目旁标注当前状态），后三项按 l 立即回满"),
                style=DEBUG_HINT_STYLE,
            )
        right.append(
            "\n[1] " + tr("清空洞察") + "  [2] " + tr("清空构想") + "  [3] " + tr("清空征兆") + "  [4] " + tr("清空行囊"),
            style="bold #ff8c69",
        )
        self.query_one("#debug-left", Static).update(left)
        self.query_one("#debug-right", Static).update(right)

    def _debug_right_width(self) -> int:
        """#debug-right 的内容宽度（格）；挂载前/取不到时退回保守值 64。

        两列布局靠它把右半条目 padding 到行尾（靠右边界）。
        """
        try:
            from textual.widgets import Static

            width = int(self.query_one("#debug-right", Static).size.width)
            if width > 8:
                return width
        except Exception:
            pass
        return 64

    @staticmethod
    def _debug_item_label(category: str, item: str, state) -> str:
        """右列条目的显示名：异象/物品/构想等用可读名称，材料用原名。"""
        if category == "异象":
            return tr(ANOMALY_DEFINITIONS[item]["name"])
        if category == "其他意识体":
            return tr(NPC_DEFINITIONS[item]["name"])
        if category == "构想":
            return tr(ABILITY_DEFINITIONS[item]["name"])
        if category == "洞察":
            return tr(item)
        if category == "征兆":
            definition = portent_def(item)
            return tr(definition.name if definition else item)
        if category in ("携带意象", "其他物品"):
            return tr(ITEM_DEFINITIONS[item]["name"])
        if category == "自我增强":
            flags = {
                "全图视野": state.debug_full_vision,
                "心智无敌": state.debug_mind_invincible,
                "清醒无敌": state.debug_lucidity_invincible,
                "想象无限": state.debug_imagination_infinite,
            }
            if item in flags:
                return f"{tr(item)}（{'开' if flags[item] else '关'}）"
        return tr(item)

    # ---- 键盘 ----

    def _handle_debug_key(self, key: str, character: str | None) -> None:
        """调试面板打开时的按键：吃掉一切游戏键（面板即模态）。

        键位：↑↓/ws 移动光标 · ←→/ad/Tab 换列 · PgUp/PgDn 翻页 ·
        Enter 确认 · Esc 取消/关面板 · 小写 l 放置 · 大写 L 关面板 ·
        数字 1-4 一键清空 · 选中征兆后 ↑↓ 选参数、-= 调当前项。数字键在此**只**作清空用——
        移动不占数字（与小键盘约定无关，面板内键盘优先）。
        """
        # 2026-09-19 修订：↑↓/ws 一律逐个移动光标（征兆参数不再占用方向键，
        # 选中征兆后用 -/= 调节，带上下限）。Esc 一律退出面板。
        if key in ("up", "w", "num8", "kp8"):
            self._debug_move_cursor(-1)
            return
        if key in ("down", "s", "num2", "kp2"):
            self._debug_move_cursor(1)
            return
        if key in ("left", "right", "a", "d", "tab"):
            self._debug_switch_side()
            return
        if key in ("pageup", "num9", "kp9"):
            for _ in range(5):
                self._debug_move_cursor(-1)
            return
        if key in ("pagedown", "num3", "kp3"):
            for _ in range(5):
                self._debug_move_cursor(1)
            return
        if key in ("enter", "return"):
            self._mark_key_handled("enter")
            self._debug_confirm()
            return
        if key == "space":
            # 2026-09-19：空格选中征兆参数（回合数/层数）——选中哪个 -= 调哪个。
            if (
                self.debug_pending is not None and self.debug_pending[0] == "征兆"
                and self.debug_side == "right"
            ):
                self.debug_param = 1 if self.debug_param == 0 else 0
                self.refresh_view()
            return
        if key == "escape":
            # 2026-09-19 修订：Esc 只退出面板，保留选中（下次打开还能继续放置）。
            self._mark_key_handled("escape")
            self.debug_panel_open = False
            self.refresh_view()
            return
        if key == "l":
            # 小写 l = 放置（待释放物落在光标格）。
            self._mark_key_handled("l")
            self._debug_spawn_from_target()
            return
        if key == "L":
            # 大写 L = 调试面板开关（与放置分离）。
            self._mark_key_handled("L")
            self.debug_panel_open = False
            self.refresh_view()
            return
        if key in ("1", "num1", "kp1"):
            self._debug_clear(1)
            return
        if key in ("2", "num2", "kp2"):
            self._debug_clear(2)
            return
        if key in ("3", "num3", "kp3"):
            self._debug_clear(3)
            return
        if key in ("4", "num4", "kp4"):
            self._debug_clear(4)
            return
        if key in ("-", "minus"):
            self._debug_adjust_param(-1)
            return
        if key in ("=", "equal", "equals_sign", "+"):
            self._debug_adjust_param(1)
            return
        # （其余按键：面板为模态，一律吞掉。）
        # （无其他键处理：面板为模态，吞掉一切剩余按键。）

    # ---- 鼠标 ----

    def handle_debug_panel_mouse(self, side: str, event) -> None:
        """左列/右列的行点击：第 0 行是标题，其后是条目。

        2026-09-19：右列点击还会命中「参数行」（回合数/层数）——点哪行选哪个。
        """
        row = event.offset.y - 1
        if row < 0:
            return
        self.debug_side = side
        if side == "left":
            if row < len(DEBUG_CATEGORIES):
                self.debug_category = row
                self.debug_item = 0
                self.debug_right_scroll = 0
                self.debug_left_scroll = self._debug_clamp_scroll(self.debug_left_scroll, row, len(DEBUG_CATEGORIES))
        else:
            items = debug_items_for(DEBUG_CATEGORIES[self.debug_category])
            # 两列布局（2026-10-12）：一行两个条目（左半偶数、右半奇数），
            # 点哪一半选哪一半；条目区占的行数是可见条目数的一半（向上取整）。
            right_width = self._debug_right_width()
            index = (self.debug_right_scroll + row * 2
                     + (0 if event.offset.x < right_width // 2 else 1))
            entry_rows = max(1, -(-min(len(items) - self.debug_right_scroll,
                                       DEBUG_VIEW_ROWS * 2) // 2))
            if 0 <= index < len(items):
                self.debug_item = index
                self._debug_confirm()
            elif (
                self.debug_pending is not None and self.debug_pending[0] == "征兆"
                and row >= entry_rows
            ):
                # 参数行：条目区之后第 0 行=回合数、第 1 行=层数。
                rel = row - entry_rows
                if rel in (0, 1):
                    self.debug_param = rel
        self.refresh_view()
