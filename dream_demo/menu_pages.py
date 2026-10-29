from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .catalog_registry import (
    MATERIAL_CATEGORIES,
    STAT_REGISTRY,
    CatalogCategory,
    CatalogDiagnostic,
    CatalogDefinition,
    StatDef,
    catalog_stat_rows,
)
from .config import ConfigManager, SETTING_REGISTRY, SettingChange, SettingDef, SettingType, format_setting_value
from .i18n import tr
from .symbols import glyph_for, symbol

# 页面文字色口径（2026-10-20 第十九节改版）：图鉴 / 历史 / 设置这三个整屏页都铺在
# `Screen` 的黑底 `#101018` 上，但色值一律取第十九节面板方案表 `ui/panel_fields.py`
# 的注册值（黑底比任何面板都暗，面板安全的色在黑底必然也安全），不再写 Rich 命名色——
# 命名色会随终端主题漂移，第十九节 §2 要求显式 RGB。
# ⚠️ 别在这里 `from .ui.panel_fields import FIELD_COLORS`：`ui` 包的 __init__ 会引回
# app → menu_pages，menu_pages 自身还在初始化中就成环（`catalog_registry` 同样延迟导入）。
# 所以这里抄一份同值常量，由 `tests/test_panel_field_colors.py` 钉住与注册表一致。
INK = {
    'text': '#ffffff', 'label': '#bcc5d6', 'muted': '#aab0c2', 'heading': '#d9e7f5',
    'count': '#cfd6e6', 'degree': '#e6c46a', 'effect': '#9dce97',
}
# ⚠️ 别再用 `style="dim"`：终端把 dim 的亮度**直接折半**，黑底上实测只有约 1.4，
# 等于看不见（本项目不靠 dim 表达「次要」，靠 INK['muted'] 这个亮灰）。


def _definitions_in(
    definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
    category: CatalogCategory,
) -> list[CatalogDefinition]:
    values = definitions.values() if isinstance(definitions, Mapping) else definitions
    return [definition for definition in values if definition.category is category]


def catalog_entry_unlocked(definition: CatalogDefinition, progress: Mapping[str, Mapping]) -> bool:
    if definition.category in MATERIAL_CATEGORIES:
        return True  # 材料条目默认全解锁：图鉴即资料库，无需先遭遇
    if definition.category is CatalogCategory.REACTION:
        return True  # 环境物体反应表：资料条目，默认全解锁
    entry = progress.get(definition.catalog_id, {})
    if definition.category is CatalogCategory.CONSCIOUSNESS:
        return int(entry.get("encounters", 0)) > 0 or int(entry.get("kills", 0)) > 0
    return int(entry.get("interactions", 0)) > 0


@dataclass
class CodexPageState:
    focus_layer: str = "categories"
    category_cursor: int = 0
    active_category: CatalogCategory = CatalogCategory.CONSCIOUSNESS
    selections: dict[CatalogCategory, int] = field(
        default_factory=lambda: {category: 0 for category in CatalogCategory}
    )
    scroll_offsets: dict[CatalogCategory, int] = field(
        default_factory=lambda: {category: 0 for category in CatalogCategory}
    )

    @property
    def category_candidate(self) -> CatalogCategory:
        return tuple(CatalogCategory)[self.category_cursor]

    def move_category(self, delta: int) -> None:
        categories = tuple(CatalogCategory)
        self.category_cursor = (self.category_cursor + delta) % len(categories)

    def activate_category(self, category: CatalogCategory | None = None) -> None:
        if category is not None:
            self.category_cursor = tuple(CatalogCategory).index(category)
        self.active_category = self.category_candidate
        self.focus_layer = "entries"

    def select_category(self, delta: int) -> None:
        """←→ 切分类：分类光标与「当前分类」一起走，层级不变。

        与 ``focus_categories`` + ``activate_category`` 的区别是不动 ``focus_layer``：
        已在条目层时按 ←→ 只想换一类看看，不该被弹回分类层（也就不必再用 Tab）。
        """
        self.move_category(delta)
        self.active_category = self.category_candidate

    def focus_categories(self) -> None:
        self.focus_layer = "categories"
        self.category_cursor = tuple(CatalogCategory).index(self.active_category)

    def selected_id(
        self,
        definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
        progress: Mapping[str, Mapping],
    ) -> str | None:
        entries = _definitions_in(definitions, self.active_category)
        selected = self.selections[self.active_category]
        if 0 <= selected < len(entries) and catalog_entry_unlocked(entries[selected], progress):
            return entries[selected].catalog_id
        return None

    def _unlocked_indices(
        self,
        definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
        progress: Mapping[str, Mapping],
    ) -> tuple[list[CatalogDefinition], list[int]]:
        entries = _definitions_in(definitions, self.active_category)
        return entries, [index for index, entry in enumerate(entries) if catalog_entry_unlocked(entry, progress)]

    def move_entry(
        self,
        delta: int,
        definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
        progress: Mapping[str, Mapping],
        *,
        viewport_size: int = 10,
    ) -> None:
        entries, unlocked = self._unlocked_indices(definitions, progress)
        if not unlocked:
            return
        current = self.selections[self.active_category]
        if current not in unlocked:
            target = unlocked[0]
        else:
            target = unlocked[(unlocked.index(current) + delta) % len(unlocked)]
        self.selections[self.active_category] = target
        offset = self.scroll_offsets[self.active_category]
        if target < offset:
            offset = target
        elif target >= offset + max(1, viewport_size):
            offset = target - max(1, viewport_size) + 1
        self.scroll_offsets[self.active_category] = max(0, min(offset, max(0, len(entries) - max(1, viewport_size))))

    def scroll_entries(
        self,
        delta: int,
        definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
        *,
        viewport_size: int = 10,
    ) -> None:
        entries = _definitions_in(definitions, self.active_category)
        maximum = max(0, len(entries) - max(1, viewport_size))
        current = self.scroll_offsets[self.active_category]
        self.scroll_offsets[self.active_category] = max(0, min(maximum, current + delta))

    def select_visible_row(
        self,
        row: int,
        definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
        progress: Mapping[str, Mapping],
        column: int = 0,
    ) -> bool:
        entries = _definitions_in(definitions, self.active_category)
        index = (self.scroll_offsets[self.active_category]
                 + max(0, int(row)) * 2 + max(0, int(column)))
        if not (0 <= index < len(entries)) or not catalog_entry_unlocked(entries[index], progress):
            return False
        self.selections[self.active_category] = index
        self.focus_layer = "entries"
        return True


@dataclass
class SettingsPageState:
    selected: int = 0
    active_category: str = 'general'
    category_positions: dict = field(default_factory=dict)
    category_scrolls: dict = field(default_factory=dict)
    capture_target: str | None = None
    feedback: str = ""
    # 「删除历史统计」的两段确认：第一次激活只警告，第二次才执行。
    confirm_delete: bool = False
    # 由 DreamApp 注入的回调（需要访问存档管理器/图鉴定义）。
    delete_callback: Callable[[], SettingChange] | None = None
    unlock_catalog_callback: Callable[[], SettingChange] | None = None

    CATEGORIES = (('general', '常规'), ('display', '画面'), ('audio', '声音'),
                  ('keys', '按键'), ('data', '数据'))

    @staticmethod
    def category_for(definition):
        key = definition.key
        if key in ('skip_tutorial', 'intent_large_marks'):
            return None
        if definition.setting_type is SettingType.KEY_BIND:
            return 'keys'
        if definition.setting_type is SettingType.ACTION:
            return 'data'
        if key.startswith(('sfx_', 'music_')):
            return 'audio'
        if key.startswith(('fx_', 'map_', 'intent_')) or key in (
                'symbol_mode', 'floor_transition', 'left_event_log', 'terse_mode'):
            return 'display'
        return 'general'

    def visible_indices(self, registry=SETTING_REGISTRY):
        return [i for i, definition in enumerate(registry)
                if self.category_for(definition) == self.active_category]

    def select_category(self, category, registry=SETTING_REGISTRY):
        if self.capture_target is not None:
            return
        self.category_positions[self.active_category] = self.selected
        self.active_category = category
        rows = self.visible_indices(registry)
        selected = self.category_positions.get(category)
        self.selected = selected if selected in rows else (rows[0] if rows else 0)
        self.confirm_delete = False
        self.feedback = ''

    def cycle_category(self, delta, registry=SETTING_REGISTRY):
        keys = [key for key, _ in self.CATEGORIES]
        self.select_category(keys[(keys.index(self.active_category) + delta) % len(keys)], registry)

    def move(self, delta: int, registry: tuple[SettingDef, ...] = SETTING_REGISTRY) -> None:
        if registry and self.capture_target is None:
            rows = self.visible_indices(registry)
            if not rows:
                return
            index = rows.index(self.selected) if self.selected in rows else 0
            self.selected = rows[(index + delta) % len(rows)]
            self.confirm_delete = False

    def activate(
        self,
        manager: ConfigManager,
        registry: tuple[SettingDef, ...] = SETTING_REGISTRY,
    ) -> SettingChange:
        definition = registry[self.selected]
        if definition.setting_type is SettingType.ACTION:
            if definition.key == "unlock_catalog":
                # 一键解锁全部图鉴：立即执行，无需两段确认（不销毁任何记录）。
                if self.unlock_catalog_callback is not None:
                    result = self.unlock_catalog_callback()
                    self.feedback = result.message
                    return result
                return SettingChange(False, tr("当前没有可执行的解锁操作。"))
            # 危险操作：第一次只警告，第二次才真正删除。
            if self.confirm_delete:
                self.confirm_delete = False
                if self.delete_callback is not None:
                    result = self.delete_callback()
                    self.feedback = result.message
                    return result
                return SettingChange(False, tr("当前没有可执行的删除操作。"))
            self.confirm_delete = True
            self.feedback = tr("将删除全部历史统计且不可恢复；再次点击确认。")
            return SettingChange(False, self.feedback)
        if definition.setting_type is SettingType.KEY_BIND:
            self.capture_target = definition.key
            self.feedback = tr("等待输入新的") + tr(definition.label) + tr("；Q 或 Esc 取消。")
            return SettingChange(False, self.feedback)
        result = manager.adjust(definition.key, 1)
        self.feedback = result.message
        return result

    def adjust(
        self,
        manager: ConfigManager,
        delta: int,
        registry: tuple[SettingDef, ...] = SETTING_REGISTRY,
    ) -> SettingChange:
        definition = registry[self.selected]
        result = manager.adjust(definition.key, delta)
        self.feedback = result.message
        return result

    def capture(self, manager: ConfigManager, candidate: str) -> SettingChange:
        if self.capture_target is None:
            return SettingChange(False, tr("当前没有等待输入的按键。"))
        result = manager.capture_key(self.capture_target, candidate)
        self.feedback = result.message
        if result.changed:
            self.capture_target = None
        return result

    def cancel_capture(self) -> None:
        self.capture_target = None
        self.feedback = tr("已取消按键捕获。")


CODEX_LIST_COLUMNS = 2
_CODEX_COLUMN_GAP = 2


def _codex_entry_cell(
    definition: CatalogDefinition,
    *,
    selected: bool,
    unlocked: bool,
    symbol_mode: str,
    width: int,
) -> Text:
    """一条图鉴列表标签；宽度不足时用省略号截断（各标签统一口径）。"""
    cell = Text(no_wrap=True)
    cell.append(symbol("cursor", symbol_mode) if selected else "  ",
                style=f"bold {INK['heading']}" if selected else "")
    if unlocked:
        cell.append(glyph_for(definition.icon, definition.symbol_key, symbol_mode),
                    style=definition.color)
        cell.append(tr(definition.name),
                    style=f"bold underline {INK['text']}" if selected else INK['text'])
    else:
        # 未解锁只给中性亮灰：条目自身的 identity 色此刻是玩家还不该知道的信息。
        cell.append(symbol("locked", symbol_mode), style=INK['muted'])
        cell.append(tr("未知"), style=INK['muted'])
    cell.truncate(width, overflow="ellipsis", pad=True)
    return cell


def render_codex_list(
    state: CodexPageState,
    definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
    progress: Mapping[str, Mapping],
    symbol_mode: str,
    *,
    viewport_size: int = 10,
    width: int | None = None,
) -> RenderableType:
    """图鉴条目列表：左侧选择按两列铺排，每列标签等宽；超宽标签省略尾部文字。"""
    entries = _definitions_in(definitions, state.active_category)
    offset = state.scroll_offsets[state.active_category]
    rows = max(1, int(viewport_size))
    capacity = rows * CODEX_LIST_COLUMNS
    visible = entries[offset : offset + capacity]
    if not visible:
        return Text(tr("此分类暂无条目。"), style=INK['muted'])
    available = max(CODEX_LIST_COLUMNS * 8, int(width or 0) or 50)
    column_width = max(8, (available - _CODEX_COLUMN_GAP) // CODEX_LIST_COLUMNS)
    text = Text(no_wrap=True)
    for row_start in range(0, len(visible), CODEX_LIST_COLUMNS):
        for column in range(CODEX_LIST_COLUMNS):
            index = offset + row_start + column
            if index >= len(entries):
                break
            definition = entries[index]
            unlocked = catalog_entry_unlocked(definition, progress)
            selected = index == state.selections[state.active_category] and unlocked
            if column:
                text.append(" " * _CODEX_COLUMN_GAP)
            text.append(_codex_entry_cell(
                definition, selected=selected, unlocked=unlocked,
                symbol_mode=symbol_mode, width=column_width,
            ))
        if row_start + CODEX_LIST_COLUMNS < len(visible):
            text.append("\n")
    return text


def render_codex_detail(
    state: CodexPageState,
    definitions: Iterable[CatalogDefinition] | Mapping[str, CatalogDefinition],
    progress: Mapping[str, Mapping],
    symbol_mode: str,
    *,
    registry: Iterable[StatDef] = STAT_REGISTRY,
    diagnostics: list[CatalogDiagnostic] | None = None,
) -> RenderableType:
    by_id = {
        definition.catalog_id: definition
        for definition in (definitions.values() if isinstance(definitions, Mapping) else definitions)
    }
    selected_id = state.selected_id(by_id, progress)
    if selected_id is None:
        return Panel(Text(tr("尚未解锁此分类中的可观测资料。"), style=INK['muted']),
                     title=tr("详情"), border_style="grey58")
    definition = by_id[selected_id]
    entry = progress.get(selected_id, {})
    heading = Text.assemble(
        (glyph_for(definition.icon, definition.symbol_key, symbol_mode), definition.color),
        (tr(definition.name), f"bold {INK['heading']}"),
        (f" · {definition.category.label}", INK['label']),
    )
    table = Table(show_header=False, box=None, pad_edge=False, expand=True)
    table.add_column(style=INK['label'], no_wrap=True)
    table.add_column(style=INK['text'], ratio=1)
    if definition.category is CatalogCategory.DIFFUSE_IMPRESSION:
        table.add_row(
            tr("浓度"),
            Text.assemble(*(
                (f"{symbol(key, symbol_mode).strip()} {amount}  ", definition.color)
                for key, amount in (("gas.faint", "1–5"), ("gas.mid", "6–15"), ("gas.high", "16+"))
            )),
        )
    for label, value in catalog_stat_rows(
        definition,
        entry,
        registry=registry,
        diagnostics=diagnostics,
    ):
        table.add_row(label, value)
    if definition.category is CatalogCategory.CONSCIOUSNESS:
        table.add_row(tr("记录"), f"{tr('遭遇')} {entry.get('encounters', 0)} · {tr('解决')} {entry.get('kills', 0)}")
    else:
        table.add_row(tr("记录"), f"{tr('交互')} {entry.get('interactions', 0)}")
    details = Text(tr(definition.description) if definition.description else tr("暂无描述。"), style=INK['label'])
    if entry.get("details"):
        details.append("\n\n" + "\n".join(entry["details"]), style=INK['muted'])
    return Panel(Group(heading, Text(""), table, Text(""), details), title=tr("详情"), border_style="bright_yellow")


def render_settings(
    state: SettingsPageState,
    manager: ConfigManager,
    symbol_mode: str,
    registry: tuple[SettingDef, ...] = SETTING_REGISTRY,
) -> RenderableType:
    rows = [
        render_setting_row(state, manager, symbol_mode, index, definition)
        for index, definition in enumerate(registry)
        if index in state.visible_indices(registry)
    ]
    # feedback 由 ConfigManager / SettingsPageState 生成时已落地成当前语言的成品句
    # （模板与字段各自取词一次），这里不能再过一遍 tr，否则模板键匹配不上。
    footer = Text(state.feedback or tr("↑↓ 选择 · ←→ 调整 · Enter/Space 修改 · Q 返回"), style=INK['label'])
    return Panel(Group(*rows, Text(""), footer), title=tr("设置"), border_style="bright_cyan")


def render_setting_row(
    state: SettingsPageState,
    manager: ConfigManager,
    symbol_mode: str,
    index: int,
    definition: SettingDef,
) -> RenderableType:
    table = Table(show_header=False, box=None, pad_edge=False, expand=True)
    table.add_column(width=3, no_wrap=True)
    table.add_column(ratio=2)
    table.add_column(ratio=1, justify="right")
    selected = index == state.selected
    cursor = symbol("cursor", symbol_mode) if selected else "  "
    label = Text(tr(definition.label), style=f"bold underline {INK['text']}" if selected else INK['text'])
    if definition.description:
        label.append("\n" + tr(definition.description), style=INK['muted'])
    if definition.setting_type is SettingType.ACTION:
        if definition.key == "unlock_catalog":
            value = tr("点击解锁")
        else:
            value = tr("再次点击确认删除") if state.confirm_delete else tr("点击删除")
    else:
        value = tr(format_setting_value(definition, manager.get(definition.key)))
    if definition.setting_type in {SettingType.ENUM, SettingType.INT}:
        value = f"{symbol('previous', symbol_mode)}{value} {symbol('next', symbol_mode).rstrip()}"
    if state.capture_target == definition.key:
        value = tr("等待按键...")
    table.add_row(cursor, label, value)
    return table


def render_history_list(
    runs: list,
    selection: int,
    scroll: int,
    *,
    viewport_rows: int = 24,
    width: int | None = None,
    hit_rows: dict[int, int] | None = None,
) -> RenderableType:
    """Render history and optionally map each wrapped content row to its entry.

    runs 传完整列表（新→旧），scroll 是首条可见下标；viewport_rows 是列表
    容器的内容高度，用来换算一屏能放几条。
    """
    import time as _time

    from rich.console import Console

    if hit_rows is not None:
        hit_rows.clear()
    console = Console(width=max(1, width or 1000))
    visible = runs[scroll:]
    text = Text()
    if not visible:
        text.append(tr("还没有任何一场结束的梦。"), style=INK['muted'])
        return text
    rendered_rows: list[Text] = []
    for row, entry in enumerate(visible):
        index = scroll + row
        selected = index == selection
        victory = bool(entry.get("victory"))
        marker = symbol("cursor", "themed") if selected else "  "
        title = tr(str(entry.get("title", "")))
        badge = tr("通关") if victory else tr("陨落")
        entry_text = Text()
        entry_text.append(marker + " ", style=f"bold {INK['heading']}" if selected else "")
        entry_text.append(
            title,
            style="bold " + (INK['degree'] if victory else INK['muted']) + (" underline" if selected else ""),
        )
        entry_text.append("  〔" + badge + "〕", style=INK['effect'] if victory else INK['label'])
        entry_text.append("\n")
        entry_text.append("    " + tr(str(entry.get("summary", ""))), style=INK['text'])
        entry_text.append("\n")
        stamp = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(float(entry.get("ts", 0) or 0)))
        entry_text.append("    " + stamp + " · " + tr("梦层 {d}", d=entry.get("depth", 0)), style=INK['muted'])
        lines = list(entry_text.wrap(console, max(1, width or 1000)))
        if rendered_rows:
            rendered_rows.append(Text())
        for line in lines:
            if len(rendered_rows) >= max(1, viewport_rows):
                break
            if hit_rows is not None:
                hit_rows[len(rendered_rows)] = row
            rendered_rows.append(line)
        if len(rendered_rows) >= max(1, viewport_rows):
            break
    return Text('\n').join(rendered_rows)


def render_history_detail(entry: dict) -> RenderableType:
    """单局详情：结局句 + 本局统计 + 携带意识/洞察/构想/记忆碎片。"""
    from .core.content import ABILITY_DEFINITIONS, ITEM_DEFINITIONS

    text = Text()
    victory = bool(entry.get("victory"))
    text.append(tr(entry.get("title", "")) + "\n", style=f"bold {INK['degree']}" if victory else f"bold {INK['muted']}")
    text.append(tr(entry.get("summary", "")) + "\n\n", style=INK['text'])
    from .core.failure_review import review_lines
    for line in review_lines(entry.get("failure_review", {})):
        text.append(line + "\n", style=INK['text'])
    stats = entry.get("stats", {}) or {}
    text.append(tr("—— 本局 ——") + "\n", style=f"bold {INK['heading']}")
    rows = (
        ("深潜回合", "turns"),
        ("抵达最深层", "deepest"),
        ("击破异象", "kills"),
        ("复合事件", "events"),
        ("引燃次数", "ignitions"),
        ("物品使用", "items_used"),
        ("承受创伤", "hits_taken"),
    )
    for label, key in rows:
        text.append(f"{tr(label)}　{stats.get(key, 0)}\n", style=INK['label'])
    text.append("\n" + tr("—— 携带意识 ——") + "\n", style="bold #ffd166")
    inventory = entry.get("inventory", []) or []
    if not inventory:
        text.append(tr("空空如也。") + "\n", style=INK['muted'])
    for item in inventory:
        definition = ITEM_DEFINITIONS.get(str(item.get("id", "")))
        name = tr(definition["name"]) if definition else str(item.get("id", ""))
        slot = item.get("slot")
        suffix = tr("（{slot}）", slot=slot) if slot else ""
        text.append(f"· {name}{suffix}\n", style=INK['text'])
    text.append("\n" + tr("—— 洞察 ——") + "\n", style="bold #58e67b")
    insights = entry.get("insights", []) or []
    text.append(("、".join(tr(name) for name in insights) if insights else tr("无")) + "\n", style=INK['text'] if insights else INK['muted'])
    text.append("\n" + tr("—— 构想 ——") + "\n", style="bold #c9a0ff")
    abilities = entry.get("abilities", []) or []
    if abilities:
        names = [tr(ABILITY_DEFINITIONS[aid]["name"]) for aid in abilities if aid in ABILITY_DEFINITIONS]
        text.append(("、".join(names) if names else tr("无")) + "\n", style=INK['text'])
    else:
        text.append(tr("无") + "\n", style=INK['muted'])
    text.append("\n" + tr("—— 记忆碎片 ——") + "\n", style="bold #67e8f9")
    memories = entry.get("memories", []) or []
    if memories:
        names = [tr(ITEM_DEFINITIONS[mid]["name"]) for mid in memories if mid in ITEM_DEFINITIONS]
        text.append(("、".join(names) if names else tr("无")) + "\n", style=INK['text'])
    else:
        text.append(tr("无") + "\n", style=INK['muted'])
    return text
