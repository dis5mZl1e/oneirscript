# -*- coding: utf-8 -*-
"""地图侧语句篡改的面板（docs §15.7）：状态机、键处理与面板渲染。

面板挂在地图区的共用浮层（panel_mode="world_tamper"）：句子槽按类别着色，
字词表上下选择、非法置灰；确认段左右切槽、Enter 提交、Esc 逐级退出。
点击按可视行的条目键快照分派，支持换行后的名称槽、字词与条件行。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich.text import Text

from ..core.tamper_world import (
    condition_combinations,
    condition_combo_blocked_reason,
    condition_ids_for,
    degree_options,
    insertion_preview,
    word_allowed,
    word_blocked_reason,
    word_cost_with_conditions,
    word_ids,
)
from ..i18n import tr
from . import tamper_presentation as presentation

PANEL_MUTED = "#aab0c2"

# 条件切换键：`[` / `]` 为工作键（key_routing 已把面板模态路由提前，方括号不再
# 被携带意象页与武装左键抢走）；`,` / `.` 保留为备选，键盘说明两处都写。
_CONDITION_PREV_KEYS = ('[', 'left_square_bracket', 'bracket_left', ',', 'comma')
_CONDITION_NEXT_KEYS = (']', 'right_square_bracket', 'bracket_right', '.', 'full_stop', 'period')


@dataclass
class WorldTamperEditor(presentation.TamperViewState):
    """一次地图篡改面板的全部状态（不入存档，离层即弃）。"""

    sentence: Any  # core.tamper_world.WorldSentence
    word_index: int = 0
    slot_index: int = 0
    phase: str = "word"  # word（选字词）→ confirm（选槽确认）
    word_ids: tuple[str, ...] = field(default_factory=lambda: word_ids())
    # 条件选项：第 0 项恒为「无」，其后是当前字词＋槽允许的单条件与无冲突双条件。
    condition_options: tuple[tuple[str, ...], ...] = ()
    condition_index: int = 0
    degree_id: str | None = None
    details_expanded: bool = False
    scroll: int = 0
    focus: str = 'word'
    condition_cursor: int = 0
    # 第六批：范围（这一处/全视野）与区域聚流落点；不入存档。
    range_mode: str = 'single'
    range_plan: Any = None
    gather_destination: tuple[int, int] | None = None
    # §15：当前预览的共用事实/输出契约；只读派生，不入存档。
    preview_contract: Any = field(default=None, repr=False, compare=False)
    # 同一次编辑可住在地图浮层（'map'）或右栏篡改页（'side'）；右栏只承载常用项，
    # 范围/落点/详情仍在地图侧，靠 host 决定哪一侧显示这一个 editor 对象。
    host: str = 'map'
    side_available: bool = False

    @property
    def word_id(self) -> str:
        return self.word_ids[self.word_index % len(self.word_ids)]

    @property
    def slot(self):
        slots = self.sentence.slots
        return slots[self.slot_index % len(slots)] if slots else None

    @property
    def condition_ids(self) -> tuple[str, ...]:
        degree = (self.degree_id,) if self.degree_id in degree_options(self.word_id) and self.degree_id else ()
        if not self.condition_options:
            return degree
        return (*degree, *self.condition_options[self.condition_index % len(self.condition_options)])

    @property
    def condition_id(self) -> str | None:
        """向后兼容：只有单条件组合返回该 id；「无」或双条件组合返回 None。"""
        combo = self.condition_ids
        return combo[0] if len(combo) == 1 else None


class TamperWorldUIMixin:
    """地图篡改面板的 UI 行为（挂在 DreamApp 上）。"""

    def open_world_tamper_editor(self, host: str | None = None) -> bool:
        """C 键入口：收集目标并生成句子；眼前全空时退到视野内最近目标。

        host 未指定时按当前页判断：右栏正停在「操作界面·篡改」页就地编辑（2026-10-24
        用户定稿：这一页不再强行转入左侧），C 键与 Alt 快捷键仍是地图浮层。
        """
        from ..core.tamper_world import collect_sentence, nearest_sentence, sentence_word_ids

        if getattr(self,'tamper_editor',None) is not None:
            return False
        if self.world_tamper_editor is not None:
            if host is not None:
                self._world_tamper_set_host(host)
            return True
        if host is None:
            host = ('side' if (self.panel_mode == 'actions'
                               and self._panel_subpage_id() == 'tamper') else 'map')
        if host == 'side' and not (self.panel_mode == 'actions'
                                   and self._panel_subpage_id() == 'tamper'):
            # 右栏这一页不在眼前时不能把编辑器放在右栏：那会留下一只看不见、
            # 却把所有按键都吃进状态机的编辑器。退到地图浮层。
            host = 'map'
        if hasattr(self, '_prepare_tamper_entry') and not self._prepare_tamper_entry():
            return False
        pinned = getattr(self, "pinned_target", None)
        hover = getattr(self,'hover_cell',None)
        sentence = collect_sentence(self.session.state, pinned=pinned, hover=hover,
                                    facing=self.facing)
        if sentence is None:
            sentence = nearest_sentence(self.session.state)
        word_ids = sentence_word_ids(sentence, self.session.state) if sentence is not None else ()
        if sentence is None or not word_ids:
            # 悬停/锁定在纯地板上时句子只有地面名词、没有可用字词；继续退到
            # 视野内最近一个可改写目标，避免 C 打开空面板或直接卡住。
            fallback = nearest_sentence(self.session.state)
            if fallback is not None:
                sentence = fallback
                word_ids = sentence_word_ids(sentence, self.session.state)
        if sentence is None or not word_ids:
            self.show_toast(tr("视野里没有可以改写的名字。"), 3)
            return False
        self.world_tamper_editor = WorldTamperEditor(
            sentence=sentence,
            word_ids=word_ids,
            host=host,
            side_available=host == 'side')
        self._course_tamper_started_at = (self.session.state.action_seq, self.session.state.time)
        self._capture_tamper_view(self.world_tamper_editor)
        self._world_tamper_select_slot(self.world_tamper_editor,0)
        # 2026-10-23 用户定稿：C 键只开左侧篡改浮层，不切换右侧面板。
        if host == 'side':
            self.panel_selection = 0
            self.panel_scroll = 0
        self.cursor_zone = 'panel' if host == 'side' else 'overlay'
        self.refresh_view()
        return True

    def _world_tamper_set_host(self, host: str) -> None:
        """把同一次篡改在右栏篡改页与地图浮层之间搬；句子、字词、条件都跟着走。"""
        editor = self.world_tamper_editor
        if editor is None or editor.host == host:
            return
        if host == 'side' and not (self.panel_mode == 'actions'
                                   and self._panel_subpage_id() == 'tamper'):
            return  # 右栏那一页不在眼前：留在地图浮层，别造出看不见却吞键的编辑器。
        editor.host = host
        # 焦点区域跟着宿主走：地图浮层是 overlay，右栏编辑是 panel。否则从右栏
        # 搬到地图后 WASD/Enter 仍会先被右栏导航吃掉，浮层看起来开了却不响应。
        self.cursor_zone = 'overlay' if host == 'map' else 'panel'
        # 钉底入口随正文一起重画：先清掉，免得搬走宿主后右栏还留着上一条入口。
        # `_panel_footer_entry` 必须一起清：右栏渲染分支用同一个变量给钉底行做键，
        # 留着 903 会让别的页（构想页的键位行）钉底时被认成「转到地图侧」。
        self._tamper_side_footer = None
        self._panel_footer_entry = -1
        if host == 'map':
            editor.side_available = True
            self.refresh_view()
            return
        # 右栏不显示范围、详情与落点选择：回到右栏时把范围与详情复位，
        # 让玩家看到的就是这次提交实际生效的条件。
        editor.range_mode = 'single'
        editor.range_plan = None
        editor.details_expanded = False
        if editor.map_preview:
            editor.map_preview = False
            self.hover_cell = editor.return_context.get('hover_cell')
        self.panel_scroll = 0
        self.refresh_view()

    def _world_tamper_side_active(self) -> bool:
        editor = self.world_tamper_editor
        return (editor is not None and getattr(editor, 'host', 'map') == 'side'
                and self.panel_mode == 'actions' and self._panel_subpage_id() == 'tamper')

    def _world_tamper_side_footer_line(self) -> Text | None:
        """右栏篡改页钉底的「转到地图侧」入口；不在这一页编辑时一律没有。

        正文渲染（ui/panels.py 的 actions 分支）与滚动量上限都读这一处，
        两边扣的行数必须相同，否则滚到底时最后一条正文会被固定行顶出视野。
        """
        if not self._world_tamper_side_active():
            return None
        return getattr(self, '_tamper_side_footer', None)

    def close_world_tamper_editor(self, *, refresh: bool = True, committed: bool = False) -> None:
        editor = self.world_tamper_editor
        if editor is not None:
            state = self.session.state
            if not committed and getattr(self, '_course_tamper_started_at', None) == (state.action_seq, state.time):
                from ..core.origin_course import note
                note(state, 'tamper_cancelled')
            self._restore_tamper_view(editor)
        self.world_tamper_editor = None
        self._tamper_side_footer = None
        self._panel_footer_entry = -1
        if refresh:
            self.refresh_view()

    def _world_tamper_rebuild_side_after_commit(self) -> None:
        """右栏提交成功后就地按**提交后的世界**重建同一个右栏编辑器。

        2026-10-28 玩家定稿：右栏成功执行一次篡改后，界面必须留在完整编辑器里
        继续改下一处，而不是关掉后退回旧简版摘要页。提交会推进时间/改写环境，
        旧句子的 context 与签名已失效，所以这里用与 open_world_tamper_editor
        完全相同的收集口径（锁定/悬停/朝向 → 最近目标兜底）重建句子与字词；
        仍住右栏（host='side'）、回到字词段、重新定位滚动。
        眼前已经没有可改写目标时关闭编辑器并给可读提示（空状态页会给出重试入口）。
        """
        from ..core.tamper_world import collect_sentence, nearest_sentence, sentence_word_ids

        if self.world_tamper_editor is None:
            return
        pinned = getattr(self, "pinned_target", None)
        hover = getattr(self, "hover_cell", None)
        sentence = collect_sentence(self.session.state, pinned=pinned, hover=hover,
                                    facing=self.facing)
        if sentence is None:
            sentence = nearest_sentence(self.session.state)
        words = sentence_word_ids(sentence, self.session.state) if sentence is not None else ()
        if sentence is None or not words:
            # 与 C 键入口同一层兜底：悬停/锁定在纯地板上时句子没有可用字词。
            fallback = nearest_sentence(self.session.state)
            if fallback is not None:
                sentence = fallback
                words = sentence_word_ids(sentence, self.session.state)
        if sentence is None or not words:
            self.close_world_tamper_editor(committed=True)
            self.show_toast(tr("这次改写之后，眼前没有可以继续改写的名字了。"), 3)
            return
        editor = WorldTamperEditor(
            sentence=sentence,
            word_ids=words,
            host='side',
            side_available=True)
        self.world_tamper_editor = editor
        self._capture_tamper_view(editor)
        self._world_tamper_select_slot(editor, 0)
        self._world_tamper_focus_kind = 'word'
        self._world_tamper_follow_selection = True
        self.panel_scroll = 0
        self.panel_selection = 0
        self.cursor_zone = 'panel'
        self.refresh_view()

    def action_world_tamper(self) -> None:
        """底栏「篡改」格的动作；键盘 C 仍由 on_key 处理，避免重复入口。"""
        if self.home_mode or self.panel_mode == "event_dialog":
            return
        self.open_world_tamper_editor()

    # ---- 条件行：列表维护、键位与点击解码 ----

    def _world_tamper_reconcile_condition(self, editor: WorldTamperEditor) -> None:
        """按当前字词＋名称槽重建条件组合；原组合不再合法时回到「无」。

        以**组合元组**（不是下标）判断是否保留：同一字词下组合列表长度会变，
        按下标保留会把「趁虚」悄悄换成另一个组合。
        """
        previous = tuple(cid for cid in editor.condition_ids if cid not in ('gently', 'forcefully'))
        if editor.degree_id not in degree_options(editor.word_id):
            editor.degree_id = None
        options = condition_combinations(editor.word_id, editor.slot, editor.sentence,
                                         include_degree=False)
        editor.condition_options = options
        if previous and previous in options:
            editor.condition_index = options.index(previous)
        else:
            editor.condition_index = 0

    def _world_tamper_cycle_condition(self, editor: WorldTamperEditor,
                                      step: int = 1) -> tuple[str, ...]:
        """在「无」与当前过滤后的条件组合之间循环；返回选中后的组合。"""
        self._world_tamper_reconcile_condition(editor)
        total = len(editor.condition_options) or 1
        original = editor.condition_index
        for offset in range(1,total+1):
            candidate = (original + step*offset) % total
            combo = editor.condition_options[candidate]
            if not condition_combo_blocked_reason(self.session.state,combo,editor.slot,editor.sentence,word_id=editor.word_id):
                editor.condition_index = candidate
                break
        return editor.condition_ids

    def _world_tamper_condition_entry(self, editor: WorldTamperEditor,
                                      index: int) -> int:
        """条件行的行语义序号（100 起是名称槽区，条件接在其后）。

        ``ui/panels.py::_panel_entry_key`` 把名称槽之后的这些序号统一编码成
        ``cond:none`` / ``cond:n``；本函数只负责渲染快照与滚动定位用的序号。
        """
        return 100 + len(editor.sentence.slots) + index

    def _world_tamper_decode_click_key(
            self, editor: WorldTamperEditor,
            key: str | None) -> tuple[str | None, Any]:
        """把面板行键解码成 (word / slot / condition, 值)；未知行返回 (None, None)。"""
        if not key:
            return None, None
        if key == 'details:toggle':
            return 'details', None
        if key == 'range:toggle':
            return 'range', None
        if key.startswith('ctoggle:'):
            return 'condition_toggle', key[8:]
        if key == 'degree:cycle':
            return 'degree', None
        if key.startswith('word:'):
            return 'word', key[5:]
        if key.startswith('cond:'):
            raw = key[5:]
            try:
                return 'condition', 0 if raw == 'none' else int(raw)
            except ValueError:
                return None, None
        if key.startswith('wslot:'):
            try:
                index = int(key[6:])
            except ValueError:
                return None, None
            slot_count = len(editor.sentence.slots)
            if 0 <= index < slot_count:
                return 'slot', index
            # 兼容旧快照：规范行键是 cond:none / cond:n，这里只为防御性兼容。
            return 'condition', index - slot_count
        return None, None

    def _world_tamper_entry_key(self, editor: WorldTamperEditor, index: int) -> int:
        """语义序号 → 条件行序号（供 ``ui/panels.py`` 的条目键换算使用）。"""
        return self._world_tamper_condition_entry(editor, index)

    def _world_tamper_reveal_condition(self, editor: WorldTamperEditor) -> None:
        """把当前选中的条件行滚进视口（面板的自动跟随只认字词/名称槽）。"""
        self._world_tamper_focus_kind = 'cond'
        self._world_tamper_follow_selection = True
        singles = tuple(cid for cid in condition_ids_for(editor.sentence,editor.word_id,editor.slot)
                        if cid not in ('gently','forcefully'))
        editor.condition_cursor = next((index for index,cid in enumerate(singles) if cid in editor.condition_ids),0)

    # ---- 键处理 ----

    def handle_world_tamper_key(self, key: str) -> bool:
        """world_tamper 面板的按键状态机；返回 True 表示按键已消费。"""
        editor = self.world_tamper_editor
        if editor is None:
            return False
        side = getattr(editor, 'host', 'map') == 'side'
        if side and key in ('v', 'r', 'R', 'backslash', '\\'):
            # 范围（R）、聚流落点（V）与插入点/效果详情（\）没有移植到右栏：
            # 按到这些键就把这次编辑搬到地图侧，而不是静默无反应。
            self._world_tamper_set_host('map')
            self.show_toast(tr('范围、聚流落点与效果详情在地图侧篡改面板。'), 3)
            return True
        if side and key == self._tamper_key_label().lower():
            # 2026-10-28：右栏编辑器开着时 C 键不再被状态机静默吞掉。把同一个
            # 编辑器搬到地图浮层，左侧完整面板立刻显示（句子/字词/条件都跟着走）。
            self._world_tamper_set_host('map')
            self.show_toast(tr('已切到地图侧篡改面板。'), 3)
            return True
        if hasattr(self, '_tamper_preview_key') and self._tamper_preview_key(key):
            return True
        if key in ('backslash', '\\'):
            editor.details_expanded = not editor.details_expanded
            self._world_tamper_follow_selection = False
            self.refresh_view()
            return True
        if key in ('r', 'R'):
            self._world_tamper_toggle_range(editor)
            self.refresh_view()
            return True
        if key in ('pageup','pagedown'):
            step = 5 if key == 'pagedown' else -5
            if side:
                # 右栏按 panel_scroll 切片渲染，editor.scroll 只对地图浮层有意义。
                self.panel_scroll = max(0, self.panel_scroll + step)
            else:
                editor.scroll = max(0, editor.scroll + step)
            self._world_tamper_follow_selection = False
            self.refresh_view()
            return True
        singles = tuple(cid for cid in condition_ids_for(editor.sentence,editor.word_id,editor.slot)
                        if cid not in ('gently','forcefully'))
        if key in ('tab','shift+tab'):
            editor.focus = 'condition' if editor.focus == 'word' and singles else 'word'
            self._world_tamper_focus_kind = 'cond' if editor.focus == 'condition' else 'word'
            self._world_tamper_follow_selection = True
            self.refresh_view()
            return True
        if editor.focus == 'condition' and singles:
            if key in ('up','w','down','s'):
                editor.condition_cursor = (editor.condition_cursor + (-1 if key in ('up','w') else 1)) % len(singles)
                self._world_tamper_focus_kind = 'cond'
                self._world_tamper_follow_selection = True
                self.refresh_view()
                return True
            if key == 'space':
                self._world_tamper_click('ctoggle:' + singles[editor.condition_cursor % len(singles)])
                return True
        self._world_tamper_follow_selection=True
        if key in ('up','w','down','s'):
            self._world_tamper_focus_kind='word'
        elif key in ('left','a','right','d'):
            self._world_tamper_focus_kind='slot'
        from ..core.tamper_world import commit_world_tamper

        if key in ('-', 'minus', 'hyphen_minus', '=', 'equals', 'equal', 'equals_sign'):
            self._world_tamper_cycle_degree(editor, -1 if key in ('-', 'minus', 'hyphen_minus') else 1)
            self.refresh_view()
            return True

        if key in ("escape", "q"):
            if editor.phase == "confirm":
                editor.phase = "word"  # 逐级退出：先回字词段
                self.refresh_view()
            elif editor.host == 'map' and editor.side_available:
                # 从右栏进来的：Esc 先把编辑送回右栏，再按一次才取消整次篡改。
                self._world_tamper_set_host('side')
            else:
                self.close_world_tamper_editor()
            return True
        # 条件切换（, . 为工作键；[ ] 仅供改写行键后使用，见文件头注释）。
        if key in _CONDITION_PREV_KEYS or key in _CONDITION_NEXT_KEYS:
            step = -1 if key in _CONDITION_PREV_KEYS else 1
            self._world_tamper_cycle_condition(editor, step)
            self._world_tamper_focus_kind = 'cond'
            self._world_tamper_follow_selection = False
            self._world_tamper_reveal_condition(editor)
            self.refresh_view()
            return True
        if editor.phase == "word":
            if key in ("up", "w"):
                editor.word_index = (editor.word_index - 1) % len(editor.word_ids)
            elif key in ("down", "s"):
                editor.word_index = (editor.word_index + 1) % len(editor.word_ids)
            elif key in ("enter", "return", "space"):
                editor.slot_index = self._world_tamper_default_slot(editor)
                if (not word_allowed(editor.word_id, editor.slot,editor.sentence)
                        or word_blocked_reason(self.session.state,editor.word_id,editor.slot,editor.sentence)):
                    self.show_toast(word_blocked_reason(self.session.state, editor.word_id, editor.slot,editor.sentence)
                                    or tr("这个字词用不到这个名字上。"), 3)
                    return True
                self._world_tamper_reconcile_condition(editor)
                condition_reason = (
                    condition_combo_blocked_reason(
                        self.session.state, editor.condition_ids, editor.slot,
                        editor.sentence, word_id=editor.word_id)
                    if editor.condition_ids else '')
                if condition_reason:
                    self.show_toast(condition_reason, 3)
                    return True
                editor.slot_index = self._world_tamper_default_slot(editor)
                editor.phase = "confirm"
                self._world_tamper_focus_kind='slot'
            self._world_tamper_reconcile_condition(editor)
            self.refresh_view()
            return True
        # confirm 段：左右切槽
        slot_count = len(editor.sentence.slots)
        if key in ("left", "a"):
            self._world_tamper_select_slot(editor,(editor.slot_index-1)%slot_count)
        elif key in ("right", "d"):
            self._world_tamper_select_slot(editor,(editor.slot_index+1)%slot_count)
        elif key in ("up", "w"):
            editor.word_index = (editor.word_index - 1) % len(editor.word_ids)
        elif key in ("down", "s"):
            editor.word_index = (editor.word_index + 1) % len(editor.word_ids)
        elif key in ("enter", "return", "space"):
            # 区域聚流：把当前观察落点交给流体计划（单格旧槽不参与��。
            if (editor.word_id in ('gather_liquid', 'gather_gas')
                    and getattr(editor.slot, 'region_members', ())
                    and editor.gather_destination is not None):
                editor.slot.gather_destination = editor.gather_destination
            if editor.range_mode == 'vision':
                from ..core.tamper_range import commit_range_tamper
                plan = editor.range_plan
                if plan is None:
                    from ..core.tamper_range import build_plan
                    plan = build_plan(self.session.state, editor.word_id,
                                      condition_ids=editor.condition_ids)
                if isinstance(plan, str):
                    self.show_toast(plan, 3)
                    return True
                result = commit_range_tamper(
                    self.session.state, editor.sentence, editor.word_id,
                    condition_ids=editor.condition_ids, plan=plan)
            else:
                result = commit_world_tamper(self.session.state, editor.sentence,
                                             editor.word_id, editor.slot_index,
                                             condition_ids=editor.condition_ids)
            if result.changed:
                from ..core.origin_course import note
                note(self.session.state,'tamper_committed')
            if side and result.changed:
                # 右栏这一页成功后保持完整编辑器：按提交后的世界重建句子/字词，
                # 不关闭、更不回退到旧简版摘要页。
                self._world_tamper_rebuild_side_after_commit()
            else:
                self.close_world_tamper_editor(committed=result.changed)
                if not result.changed:
                    self.show_toast(result.message, 4)
            return True
        self._world_tamper_reconcile_condition(editor)
        self.refresh_view()
        return True

    def _world_tamper_select_slot(self,editor: WorldTamperEditor,index: int) -> None:
        from ..core.tamper_world import sentence_word_ids
        previous=editor.word_id
        editor.slot_index=index
        # 换目标槽就清掉手动落点：落点是跟「这一片区域」走的，旧槽选的落点
        # 对新槽多半不相邻，留着只会让提交报「落点没有与来源相邻」。
        editor.gather_destination = None
        candidates=tuple(word for word in sentence_word_ids(editor.sentence, self.session.state)
                         if word_allowed(word,editor.slot,editor.sentence))
        editor.word_ids=candidates
        editor.word_index=candidates.index(previous) if previous in candidates else 0
        self._world_tamper_reconcile_condition(editor)

    def _world_tamper_default_slot(self, editor: WorldTamperEditor) -> int:
        """保留当前合法槽；否则取第一个合法槽，全部非法则保持不动。"""
        if (word_allowed(editor.word_id,editor.slot,editor.sentence)
                and not word_blocked_reason(self.session.state,editor.word_id,editor.slot,editor.sentence)):
            return editor.slot_index
        for index, slot in enumerate(editor.sentence.slots):
            if word_allowed(editor.word_id, slot,editor.sentence) and not word_blocked_reason(
                    self.session.state, editor.word_id, slot,editor.sentence):
                return index
        return editor.slot_index

    def _world_tamper_click(self, key: str | None) -> None:
        """面板行点击（docs §15.7）：word:n 选字词，wslot:n 切目标槽，cond:n 选条件。"""
        editor = self.world_tamper_editor
        if editor is None or not key:
            return
        if key == 'editor:view':
            self._toggle_tamper_map()
            return
        if key == 'editor:cancel':
            self.close_world_tamper_editor()
            return
        if key == 'editor:confirm':
            self.handle_world_tamper_key('enter')
            return
        if key == 'tamper:map':
            self._world_tamper_set_host('map')
            return
        if key == 'range:toggle':
            self._world_tamper_toggle_range(editor)
            self.refresh_view()
            return
        if key == 'details:toggle':
            editor.details_expanded = not editor.details_expanded
            self._world_tamper_follow_selection = False
            self.refresh_view()
            return
        self._world_tamper_follow_selection=True
        kind, value = self._world_tamper_decode_click_key(editor, key)
        if kind == 'range':
            self._world_tamper_toggle_range(editor)
            self.refresh_view()
            return
        self._world_tamper_focus_kind = {'slot': 'slot', 'word': 'word'}.get(kind or '', 'cond')
        if kind == 'word':
            word_id = value
            if word_id in editor.word_ids:
                editor.focus = 'word'
                editor.word_index = editor.word_ids.index(word_id)
                if editor.phase == "confirm":
                    editor.slot_index = self._world_tamper_default_slot(editor)
                self._world_tamper_reconcile_condition(editor)
        elif kind == 'slot':
            index = int(value)
            if 0 <= index < len(editor.sentence.slots):
                self._world_tamper_select_slot(editor,index)
                if editor.phase == "word":
                    editor.phase = "confirm"
        elif kind == 'degree':
            self._world_tamper_cycle_degree(editor)
        elif kind == 'condition_toggle':
            singles = tuple(cid for cid in condition_ids_for(editor.sentence, editor.word_id, editor.slot)
                            if cid not in ('gently', 'forcefully'))
            if value not in singles:
                return
            current = tuple(cid for cid in editor.condition_ids if cid in singles)
            candidate = tuple(cid for cid in singles
                              if (cid in current and cid != value) or (cid == value and cid not in current))
            if candidate not in editor.condition_options:
                self.show_toast(tr('条件互斥或已选满三个，请先取消一项。'), 3)
                return
            reason = condition_combo_blocked_reason(self.session.state, candidate, editor.slot,
                                                     editor.sentence, word_id=editor.word_id)
            if reason:
                self.show_toast(reason, 3)
                return
            editor.condition_index = editor.condition_options.index(candidate)
            editor.condition_cursor = singles.index(value)
        elif kind == 'condition':
            total = len(editor.condition_options) or 1
            if 0 <= int(value) < total:
                editor.condition_index = int(value)
        self.refresh_view()

    # ---- 渲染 ----

    def _world_tamper_toggle_range(self, editor: WorldTamperEditor) -> None:
        """在「这一处/全视野」之间切换；不支持的字词保持单处并提示。"""
        from ..core.tamper_range import supports_range
        if not supports_range(editor.word_id, editor.condition_ids):
            self.show_toast(tr("这个字词不支持全视野范围。"), 3)
            editor.range_mode = 'single'
            editor.range_plan = None
            return
        editor.range_mode = 'vision' if editor.range_mode != 'vision' else 'single'
        editor.range_plan = None

    def _world_tamper_cycle_degree(self, editor: WorldTamperEditor, step: int = 1) -> None:
        options = degree_options(editor.word_id)
        current = editor.degree_id if editor.degree_id in options else None
        editor.degree_id = options[(options.index(current) + step) % len(options)]

    def _world_tamper_panel_text(self, state, width: int = 44) -> Text:
        """面板正文（行式构建，同步登记 _panel_rows 供点击定位）。

        0..n-1 为字词，100+i 为目标，900/901 为程度/详情，1000+i
        为单条件。并排区域另有二维命中表；-3/-2/-4 分别为固定句子、报价、操作。
        """
        editor = self.world_tamper_editor
        self._panel_rows = []
        hits = []
        lines: list[tuple[str | Text, str]] = []  # (内容, 样式)
        row: list[int] = []               # 与 lines 逐行对齐的条目序号

        def entry_key(entry):
            if 0 <= entry < len(editor.word_ids):
                return 'word:' + editor.word_ids[entry]
            if 100 <= entry < 100 + len(editor.sentence.slots):
                return f'wslot:{entry-100}'
            if entry == 900:
                return 'degree:cycle'
            if entry == 901:
                return 'details:toggle'
            if entry == 902:
                return 'range:toggle'
            return None

        def emit(content: str | Text, style: str, entry: int) -> None:
            if entry == -2:
                from ..data.semantic_icons import icon_label
                if isinstance(content,str):
                    content = icon_label('ui.risk' if style == presentation.RISK else 'ui.cost',content,style)
            for chunk in presentation.folded_lines(content, width, style):
                from rich.cells import cell_len
                key = entry_key(entry)
                if key:
                    hits.append(presentation.ChoiceHit(len(lines),0,cell_len(chunk.plain),key))
                lines.append((chunk, style))
                row.append(entry)

        allowed = word_allowed(editor.word_id, editor.slot, editor.sentence)
        point, after_clause, effect_note = insertion_preview(
            editor.sentence, editor.word_id, editor.slot_index,
            condition_ids=editor.condition_ids, state=state) if allowed else ('', '', '')
        if allowed and after_clause:
            # §15 第三批：改后句保留原句语篇（原句 + 变更子句），不再只给动作片段。
            from ..core.tamper_prose import compose_after
            from ..core.tamper_views import language_of
            after_sentence = compose_after(editor.sentence.text, after_clause,
                                           language=language_of())
        else:
            after_sentence = editor.sentence.text
        from ..core.tamper_contract import build_tamper_contract
        editor.preview_contract = build_tamper_contract(
            editor.sentence, editor.word_id, editor.slot_index,
            condition_ids=editor.condition_ids,
            replacement=after_sentence, effect=effect_note) if allowed else None
        # 第六批：原句固定置顶，改后句紧随其下；范围是独立选择，不占程度/条件。
        from ..core.tamper_range import build_plan, supports_range
        range_supported = supports_range(editor.word_id, editor.condition_ids)
        if editor.range_mode == 'vision' and not range_supported:
            editor.range_mode = 'single'
            editor.range_plan = None
        range_plan = None
        range_error = ''
        if allowed and range_supported and editor.range_mode == 'vision':
            built = build_plan(state, editor.word_id, condition_ids=editor.condition_ids)
            if isinstance(built, str):
                range_error = built
                editor.range_plan = None
            else:
                range_plan = built
                editor.range_plan = built
                # 全视野操作也保留原句语篇：改后句 = 原句 + 「按统一字词生效」。
                from ..core.tamper_prose import compose_after
                from ..core.tamper_views import language_of
                after_sentence = compose_after(
                    editor.sentence.text,
                    tr('{label}（{n} 处）将按当前字词统一生效。',
                       label=built.label, n=built.count),
                    language=language_of())
        else:
            editor.range_plan = None
        original_line = Text(tr('原句：'), style='bold ' + PANEL_MUTED)
        original_line.append(editor.sentence.text, style=PANEL_MUTED)
        for slot in editor.sentence.slots:
            original_line.highlight_words([slot.display_name()],
                                          _world_slot_color(slot.category))
        emit(original_line, '', -5)
        # Keep the complete result above all selectors, including during scrolling.
        sentence_line = Text(tr('改后：'), style='bold ' + presentation.EFFECT)
        sentence_line.append(after_sentence, style=presentation.EFFECT)
        for slot in editor.sentence.slots:
            sentence_line.highlight_words([slot.display_name()],
                                          _world_slot_color(slot.category))
        emit(sentence_line, '', -3)
        if range_supported:
            emit(tr('范围：{mode}（R 或点击切换）',
                    mode=tr('全视野') if editor.range_mode == 'vision' else tr('这一处')),
                 'bold ' + presentation.CONDITION, 902)
        if editor.range_mode == 'vision':
            if range_error:
                emit(range_error, presentation.RISK, -6)
            elif range_plan is not None:
                emit(tr('范围提示：{label} · {n} 处 · 排除 {excluded} 处',
                        label=range_plan.label, n=range_plan.count,
                        excluded=len(range_plan.excluded)),
                     presentation.CONDITION, -6)
        overflow = int(getattr(editor.sentence, 'overflow', 0) or 0)
        if overflow > 0:
            # 句子只点名有限处，多出来的仍在眼前：如实说明，别让玩家以为视野里
            # 只有这几处（§15 第三批：四槽截断不再静默丢弃）。
            emit(tr('另有 {n} 处同类在视野里没被点名（走近或悬停可换目标）', n=overflow),
                 presentation.CONDITION, -7)
        # 区域聚流需要明确落点：默认取距玩家最近的合法相邻格（与提交执行同一
        # 入口），V 查看地图移动观察光标即可改成别的落点。
        if (getattr(editor.slot, 'region_members', ())
                and editor.word_id in ('gather_liquid', 'gather_gas')):
            from ..core.tamper_fluid import default_gather_destination
            destination = editor.gather_destination
            if destination is not None:
                emit(tr('落点：观察格 ({x},{y})（V 查看地图可改）',
                        x=destination[0], y=destination[1]), presentation.CONDITION, -6)
            else:
                default = default_gather_destination(state, editor.slot, editor.word_id)
                if default is not None:
                    emit(tr('落点：({x},{y})（自动·V 查看地图可改）',
                            x=default[0], y=default[1]), presentation.CONDITION, -6)
                else:
                    emit(tr('落点：周围没有可用的落点'), presentation.RISK, -6)
        # 目标槽列表（点击切槽；confirm 段当前槽高亮）。
        emit(tr("── 目标 ──"), 'bold #9ab8d9', -1)
        for index, slot in enumerate(editor.sentence.slots):
            current = index == editor.slot_index
            marker = "▸ " if current else "  "
            label = tr("〔{category}〕{label}",
                       category=_category_label(slot.category),
                       label=slot.display_name())
            if getattr(slot, "region_members", ()):
                from ..core.tamper_regions import slot_range_text
                label += "  " + slot_range_text(slot)
            emit(f"{marker}{label}", ('bold underline ' if current else '') + slot.color, 100 + index)
        choices = degree_options(editor.word_id)
        if len(choices) > 1:
            names = {None: tr('通常'), 'gently': tr('轻轻'), 'forcefully': tr('用力')}
            label = ' / '.join(f'[{names[value]}]' if value == editor.degree_id else names[value] for value in choices)
            from ..data.semantic_icons import icon_label
            emit(icon_label('ui.degree',tr('程度：{value}（点击或 - = 切换）', value=label),presentation.DEGREE), presentation.DEGREE, 900)
        left = [(Text(tr('── 字词 ──'),style='bold '+presentation.WORD),-1,None)]
        right = []
        def left_emit(content, style, entry):
            left.append((content if isinstance(content,Text) else Text(content,style=style),entry,entry_key(entry)))
        singles = tuple(cid for cid in condition_ids_for(editor.sentence,editor.word_id,editor.slot)
                        if cid not in ('gently','forcefully'))
        def right_emit(content, style, entry):
            key = 'ctoggle:' + singles[entry-1000] if 1000 <= entry < 1000+len(singles) else None
            right.append((content if isinstance(content,Text) else Text(content,style=style),entry,key))
        for index, word_id in enumerate(editor.word_ids):
            current = index == editor.word_index % len(editor.word_ids)
            reason = word_blocked_reason(state, word_id, editor.slot, editor.sentence)
            usable = word_allowed(word_id, editor.slot, editor.sentence) and not reason
            from ..data.semantic_icons import semantic_icon, icon_label
            word_icons = {'negate': 'tamper.negate', 'again': 'tamper.again',
                          'delete': 'tamper.erase'}
            icon = semantic_icon(word_icons.get(word_id, '')) if word_id in word_icons else ''
            style = ('bold underline ' if current else '') + (presentation.WORD if usable else PANEL_MUTED)
            if icon:
                label = Text(('▸ ' if current else '  ') + icon + tr(_word_def(word_id)['name']),style=style)
            else:
                label = Text('▸ ' if current else '  ',style=style)
                label.append_text(icon_label('tamper.word.'+word_id,tr(_word_def(word_id)['name']),style))
            left_emit(label,style,index)
            if current and not usable:
                left_emit(reason or tr('这个字词用不到这个名字上。'), presentation.RISK, -1)
        self._world_tamper_condition_section(state, editor, right_emit)
        blocks,entries,block_hits = presentation.adjacent_choices(left,right,width)
        base = len(lines)
        lines.extend((line,'') for line in blocks); row.extend(entries)
        hits.extend(presentation.ChoiceHit(hit.row+base,hit.start_col,hit.end_col,hit.key) for hit in block_hits)
        blocked = word_blocked_reason(state,editor.word_id,editor.slot,editor.sentence)
        if not blocked:
            blocked = condition_combo_blocked_reason(state,editor.condition_ids,editor.slot,
                                                      editor.sentence,word_id=editor.word_id)
        if not blocked and editor.focus=='condition' and singles:
            from ..core.tamper_world import condition_blocked_reason
            blocked = condition_blocked_reason(state,singles[editor.condition_cursor % len(singles)],editor.slot,
                                                editor.sentence,word_id=editor.word_id)
        if blocked:
            emit(blocked,presentation.RISK,-2)
        from ..data.semantic_icons import icon_label
        emit(icon_label('ui.details',presentation.details_label(editor.details_expanded),presentation.MUTED), presentation.MUTED, 901)
        if editor.details_expanded:
            emit(tr('插入点：{name} · {point}', name=editor.slot.display_name(), point=point),
                 '#87bed6', -1)
            emit(tr('效果：{note}', note=effect_note or '—'), presentation.EFFECT, -1)
        if allowed:
            if range_plan is not None:
                cost_imagination, cost_delta = range_plan.imagination, range_plan.chaos_delta
            else:
                cost_imagination,cost_delta=word_cost_with_conditions(
                    state,editor.word_id,editor.slot,editor.condition_ids)
            # Confirmation's final quote and risks stay above the bottom edge
            # while targets, conditions and words remain independently scrollable.
            summary_entry = -2
            if range_plan is not None:
                emit(tr('代价（全视野 {n} 处）：想象力 {a} · 混乱 +{b}',
                        n=range_plan.count, a=cost_imagination, b=cost_delta),
                     presentation.COST,summary_entry)
            else:
                emit(tr('代价：想象力 {a} · 混乱 +{b}',a=cost_imagination,b=cost_delta),
                     presentation.COST,summary_entry)
            from ..core.chaos import chaos_risk_tier, clamp_chaos
            after=clamp_chaos(state.chaos+cost_delta)
            emit(tr('提交后混乱：{n}（{tier}）',n=after,tier=tr(chaos_risk_tier(after))),presentation.COST,summary_entry)
            from ..core.tamper_pipeline import risk_note
            emit(risk_note(state, after, imagination_cost=cost_imagination), presentation.RISK, summary_entry)
        if editor.phase == "confirm":
            emit(tr('Tab 切条件 · Space 勾选 · [ ] 换组合 · Enter 执行 · Esc 返回'), "#aab0c2", -1)
        else:
            emit(tr('↑↓ 选词 · Tab 切条件 · Space 勾选 · Enter 进确认 · Esc 退出'), "#aab0c2", -1)
        if editor.side_available:
            emit(tr('这一句也能在右栏改：Esc 先回右栏。'), "#aab0c2", -1)
        if editor.details_expanded and 'lure_to' in editor.word_ids:
            emit(tr('固定异象后悬停环境，可改写两者的关系。'),PANEL_MUTED,-1)
        from rich.cells import cell_len
        # Each action gets its own hit region, including after narrow wrapping.
        action = Text()
        for label,key,color in ((tr('[确认]'),'editor:confirm',presentation.EFFECT),
                                (tr('[取消]'),'editor:cancel',presentation.MUTED),
                                (tr('[查看地图 V]'),'editor:view',presentation.CONDITION)):
            from ..data.semantic_icons import icon_label
            label = icon_label('ui.'+key.split(':')[1],label,color)
            label_width = cell_len(label.plain)
            if action and cell_len(action.plain)+2+label_width > width:
                lines.append((action,'')); row.append(-4); action=Text()
            if action:
                action.append('  ')
            start = cell_len(action.plain)
            # Extremely narrow labels wrap into independently clickable pieces.
            chunks = presentation.folded_lines(label,width,color)
            if len(chunks)>1:
                if action:
                    lines.append((action,'')); row.append(-4); action=Text()
                for chunk in chunks:
                    hits.append(presentation.ChoiceHit(len(lines),0,cell_len(chunk.plain),key))
                    lines.append((chunk,'')); row.append(-4)
            else:
                hits.append(presentation.ChoiceHit(len(lines),start,start+label_width,key))
                action.append_text(label)
        if action:
            lines.append((action,'')); row.append(-4)
        self._panel_rows = row
        self._world_tamper_full_rows = list(row)
        self._world_tamper_full_hits = hits
        text = Text()
        for index, (content, style) in enumerate(lines):
            if index:
                text.append("\n")
            if isinstance(content,Text):
                text.append(content)
            else:
                text.append(content, style=style)
        return text

    def _world_tamper_visible_text(self,state,width,height):
        editor = self.world_tamper_editor
        full = self._world_tamper_panel_text(state,width)
        lines = full.split('\n'); rows = self._world_tamper_full_rows
        follow_key = None
        if getattr(self,'_world_tamper_follow_selection',False):
            focus = getattr(self,'_world_tamper_focus_kind','word')
            if focus == 'slot':
                follow_key = f'wslot:{editor.slot_index}'
            elif focus == 'cond':
                singles = tuple(cid for cid in condition_ids_for(editor.sentence,editor.word_id,editor.slot)
                                if cid not in ('gently','forcefully'))
                if singles:
                    follow_key = 'ctoggle:' + singles[editor.condition_cursor % len(singles)]
            else:
                follow_key = 'word:' + editor.word_id
        # Composite rows can contain two choices; follow the actual hit key.
        tags = [follow_key if follow_key and any(hit.row==i and hit.key==follow_key
                for hit in self._world_tamper_full_hits) else entry for i,entry in enumerate(rows)]
        visible,editor.scroll,body_height,total = presentation.section_window(
            tags,top={-5,-3,-6},bottom={-2,-4},actions={-4},height=height,
            scroll=editor.scroll,follow=follow_key)
        self._world_tamper_follow_selection = False
        mapping = {source:i for i,source in enumerate(visible) if source is not None}
        self._world_tamper_visible_hits = tuple(presentation.ChoiceHit(mapping[hit.row],hit.start_col,hit.end_col,hit.key)
            for hit in self._world_tamper_full_hits if hit.row in mapping)
        self._world_tamper_visible_rows = [rows[i] if i is not None else -1 for i in visible]
        self._world_tamper_total_lines=total; self._world_tamper_body_height=body_height
        return Text('\n').join(lines[i] if i is not None else Text() for i in visible)

    def _world_tamper_side_lines(self, state) -> tuple[list[Text], list[int]]:
        """右栏篡改页（完整编辑器，不是旧简版摘要）：把地图浮层的常用项搬来就地编辑。

        移植的是改后句、目标、字词、条件、程度、代价与确认入口；范围（R）、
        聚流落点（V）与插入点/效果详情（\\）仍只在地图侧浮层，底部那一行是把这次
        编辑搬过去的入口（钉底显示，正文再长也看得见）。原句不再单列：改后句
        就是「原句 + 变更子句」。行序号沿用浮层同一套约定（字词 0..、目标 100+、
        条件 1000+、程度 900、地图侧入口 903），点击与键盘因此共用一个状态机。
        """
        from .panels import _WRAP_CONSOLE
        editor = self.world_tamper_editor
        lines: list[Text] = []
        rows: list[int] = []
        width = max(12, self.query_one('#panel').content_size.width - 4)
        compact = self._terse_active()

        def add(content, row_index: int = -1, style: str = '') -> None:
            line = content if isinstance(content, Text) else Text(content, style=style)
            for wrapped in line.wrap(_WRAP_CONSOLE, width + 4, overflow='fold', no_wrap=False):
                lines.append(wrapped)
                rows.append(row_index)

        allowed = word_allowed(editor.word_id, editor.slot, editor.sentence)
        point, after_clause, effect_note = (
            insertion_preview(editor.sentence, editor.word_id, editor.slot_index,
                              condition_ids=editor.condition_ids, state=state)
            if allowed else ('', '', ''))
        after_sentence = editor.sentence.text
        if allowed and after_clause:
            from ..core.tamper_prose import compose_after
            from ..core.tamper_views import language_of
            after_sentence = compose_after(editor.sentence.text, after_clause,
                                           language=language_of())
        result_line = Text('AFT:' if compact else tr('改后：'), style='bold ' + presentation.EFFECT)
        result_line.append(after_sentence, style=presentation.EFFECT)
        for slot in editor.sentence.slots:
            result_line.highlight_words([slot.display_name()], _world_slot_color(slot.category))
        # 右栏不放原句行：改后句本来就是「原句 + 变更子句」的拼接（compose_after
        # 保留原句语篇），在 40 格宽的右栏里两句话要吃掉 5 行，把代价与入口顶到视野外。
        add(result_line)

        add(Text('── TGT ──' if compact else tr('── 目标 ──'), style='bold #9ab8d9'))
        for index, slot in enumerate(editor.sentence.slots):
            current = index == editor.slot_index
            label = tr('〔{category}〕{label}',
                       category=_category_label(slot.category), label=slot.display_name())
            if getattr(slot, 'region_members', ()):
                from ..core.tamper_regions import slot_range_text
                label += '  ' + slot_range_text(slot)
            add(Text(('▸ ' if current else '  ') + label,
                     style=('bold underline ' if current else '') + slot.color), 100 + index)

        left = [(Text('── WORD ──' if compact else tr('── 字词 ──'), style='bold ' + presentation.WORD), -1, None)]
        right = []
        from ..data.semantic_icons import semantic_icon, icon_label
        word_icons = {'negate': 'tamper.negate', 'again': 'tamper.again',
                      'delete': 'tamper.erase'}
        for index, word_id in enumerate(editor.word_ids):
            current = index == editor.word_index % len(editor.word_ids)
            reason = word_blocked_reason(state, word_id, editor.slot, editor.sentence)
            usable = word_allowed(word_id, editor.slot, editor.sentence) and not reason
            style = ('bold underline ' if current else '') + (presentation.WORD if usable else PANEL_MUTED)
            name = tr(_word_def(word_id)['name'])
            if word_id in word_icons:
                label = Text(('▸ ' if current else '  ') + semantic_icon(word_icons[word_id]) + name,
                             style=style)
            else:
                label = Text('▸ ' if current else '  ', style=style)
                label.append_text(icon_label('tamper.word.' + word_id, name, style))
            left.append((label, index, 'word:' + word_id))
            if current and not usable:
                left.append((Text(reason or tr('这个字词用不到这个名字上。'), style=presentation.RISK), -1, None))

        singles = tuple(cid for cid in condition_ids_for(editor.sentence, editor.word_id, editor.slot)
                        if cid not in ('gently', 'forcefully'))
        def emit(content, style, entry):
            key = 'ctoggle:' + singles[entry-1000] if 1000 <= entry < 1000+len(singles) else None
            if compact and entry == -1 and '条件' in getattr(content, 'plain', str(content)):
                content = Text('── COND ──', style=style)
            right.append((content if isinstance(content, Text) else Text(content, style=style), entry, key))
        self._world_tamper_condition_section(state, editor, emit, compact=True)

        blocks, entries, hits = presentation.adjacent_choices(left, right, width+4, split_from=24)
        base = len(lines)
        self._tamper_side_choice_range = (base, base+len(blocks))
        self._tamper_side_choice_hits = tuple(presentation.ChoiceHit(
            base+h.row, h.start_col, h.end_col, h.key) for h in hits)
        lines.extend(blocks)
        rows.extend(entries)

        choices = degree_options(editor.word_id)
        if len(choices) > 1:
            names = {None: tr('通常'), 'gently': tr('轻轻'), 'forcefully': tr('用力')}
            label = ' / '.join(f'[{names[value]}]' if value == editor.degree_id else names[value]
                               for value in choices)
            degree_label = f'DEG: {label} (-)' if compact else tr('程度：{value}（- = 切换）', value=label)
            add(icon_label('ui.degree', degree_label,
                           presentation.DEGREE), 900)

        blocked = word_blocked_reason(state, editor.word_id, editor.slot, editor.sentence)
        if not blocked:
            blocked = condition_combo_blocked_reason(state, editor.condition_ids, editor.slot,
                                                     editor.sentence, word_id=editor.word_id)
        if blocked:
            add(Text(blocked, style=presentation.RISK))
        if (getattr(editor.slot, 'region_members', ())
                and editor.word_id in ('gather_liquid', 'gather_gas')):
            from ..core.tamper_fluid import default_gather_destination
            destination = editor.gather_destination
            fallback = (default_gather_destination(state, editor.slot, editor.word_id)
                        if destination is None else None)
            if destination is not None:
                where = tr('观察格 ({x},{y})', x=destination[0], y=destination[1])
            elif fallback is not None:
                where = tr('({x},{y})（自动）', x=fallback[0], y=fallback[1])
            else:
                where = tr('周围没有可用的落点')
            add(Text(tr('落点：{where}（V 查看地图可改）', where=where),
                     style=presentation.CONDITION
                     if destination is not None or fallback is not None
                     else presentation.RISK))
        if allowed:
            cost_imagination, cost_delta = word_cost_with_conditions(
                state, editor.word_id, editor.slot, editor.condition_ids)
            cost_text = (f'COST: IMA {cost_imagination} · CHA +{cost_delta}' if compact else
                         tr('代价：想象力 {a} · 混乱 +{b}', a=cost_imagination, b=cost_delta))
            add(Text(cost_text,
                     style=presentation.COST))
        add(Text(tr('↑↓ 选词 · Enter 进确认 · Esc 退出') if editor.phase != 'confirm' else
                 tr('↑↓ 选词 · ←→ 换目标 · Tab 切条件 · Space 勾选 · Enter 执行 · Esc 退出'),
                 style=PANEL_MUTED))
        # 「转到地图侧」的入口不进正文：正文超过一屏时它会掉到折线以下，而这一行
        # 是两侧互转的唯一按钮。右栏渲染时把它钉在最后一行（ui/panels.py actions 分支）。
        self._panel_footer_entry = 903
        self._tamper_side_footer = Text(('[MAP: R / V / \\]' if compact else
                                        '[' + tr('在地图里改：范围 / 落点 / 详情') + ']'),
                                        style='bold ' + presentation.CONDITION)
        self._world_tamper_side_follow(rows)
        return lines, rows

    def _tamper_side_choice_key(self, source_row, column):
        return next((hit.key for hit in getattr(self, '_tamper_side_choice_hits', ())
                     if hit.contains(source_row, column)), None)

    def _tamper_side_pointer_key(self, visual_row, column):
        source = visual_row - len(self._panel_subtabs_lines()) - 1 + self.panel_scroll
        lo, hi = getattr(self, '_tamper_side_choice_range', (-1, -1))
        if lo <= source < hi:
            return self._tamper_side_choice_key(source, column)
        keys = getattr(self, '_panel_row_keys', ())
        return keys[visual_row] if 0 <= visual_row < len(keys) else None

    def _world_tamper_side_follow(self, rows: list[int]) -> None:
        """把选中项滚进右栏视口；跟随标记只消费一次，重复排版不会来回挪。"""
        if not getattr(self, '_world_tamper_follow_selection', False):
            return
        self._world_tamper_follow_selection = False
        editor = self.world_tamper_editor
        if editor is None:
            return
        focus = getattr(self, '_world_tamper_focus_kind', 'word')
        if focus == 'slot':
            target = 100 + editor.slot_index % max(1, len(editor.sentence.slots))
        elif focus == 'cond':
            singles = tuple(cid for cid in condition_ids_for(editor.sentence, editor.word_id, editor.slot)
                            if cid not in ('gently', 'forcefully'))
            if not singles:
                return
            target = 1000 + editor.condition_cursor % len(singles)
        else:
            target = editor.word_index % max(1, len(editor.word_ids))
        key = ('ctoggle:' + singles[editor.condition_cursor % len(singles)] if focus == 'cond'
               else 'word:' + editor.word_id if focus == 'word' else f'wslot:{editor.slot_index}')
        hit = next((h for h in getattr(self, '_tamper_side_choice_hits', ()) if h.key == key), None)
        if hit is None and target not in rows:
            return
        viewport = self._world_tamper_side_viewport()
        index = hit.row if hit is not None else rows.index(target)
        scroll = self.panel_scroll
        if index < scroll:
            self.panel_scroll = index
        elif index >= scroll + viewport:
            self.panel_scroll = max(0, index - viewport + 1)

    def _world_tamper_side_viewport(self) -> int:
        """右栏这一页正文实际能显示几行：页签条与钉底入口都要扣掉。

        与 ui/panels.py 的 actions 分支同一口径，否则「跟随选中项」会把目标
        刚好留在折线外一行。
        """
        viewport = max(1, self._portent_viewport_rows())
        strip_lines = self._panel_subtabs_lines()
        if strip_lines:
            viewport = max(1, viewport - len(strip_lines))
        if self._world_tamper_side_footer_line() is not None:
            viewport = max(1, viewport - 1)
        return viewport

    def _world_tamper_condition_section(self, state, editor: WorldTamperEditor, emit,
                                        compact: bool = False) -> None:
        """单条件勾选列表；实际选中组合仍由共用条件组合规则验证。"""
        from ..core.tamper_world import condition_blocked_reason
        from ..data.semantic_icons import icon_label
        emit(icon_label('ui.conditions',tr("── 条件 ──"),'bold '+presentation.CONDITION), 'bold ' + presentation.CONDITION, -1)
        singles = tuple(cid for cid in condition_ids_for(editor.sentence, editor.word_id, editor.slot)
                        if cid not in ('gently', 'forcefully'))
        count = sum(cid in singles for cid in editor.condition_ids)
        # 右栏一行都不浪费：没勾选时不必单独说「已选 0/3」，方框本身就是未选。
        if count or not compact:
            emit(tr('已选 {n}/3',n=count) + (' · ' + tr('无') if not count else ''), presentation.CONDITION,-1)
        for index, cid in enumerate(singles):
            selected = cid in editor.condition_ids
            reason = condition_blocked_reason(state, cid, editor.slot, editor.sentence, word_id=editor.word_id)
            cursor = editor.focus == 'condition' and index == editor.condition_cursor % max(1,len(singles))
            from ..data.semantic_icons import icon_label
            style = ('bold ' if selected else '') + (PANEL_MUTED if reason else presentation.CONDITION)
            label = Text(('▸ ' if cursor else '') + ('[✓] ' if selected else '[ ] '),style=style)
            label.append_text(icon_label('tamper.condition.'+cid,tr(_condition_def(cid)['name']),style))
            emit(label, style, 1000 + index)
            if reason and (editor.details_expanded or selected or cursor):
                emit('    ' + reason, presentation.RISK, -1)
        if not singles:
            emit(tr('无'), PANEL_MUTED, -1)



def _world_sentence_parts(sentence) -> list[tuple[str, str]]:
    """把模板句拆回（文字段, 槽类别）序列，供着色渲染。"""
    parts: list[tuple[str, str]] = []
    rest = sentence.text
    for slot in sentence.slots:
        marker = slot.display_name()
        idx = rest.find(marker)
        if idx < 0:
            continue
        if idx:
            parts.append((rest[:idx], ""))
        parts.append((marker, slot.category))
        rest = rest[idx + len(marker):]
    if rest:
        parts.append((rest, ""))
    return parts


def _world_slot_color(category: str) -> str:
    from ..data.tamper_world import SLOT_CATEGORY_COLORS
    return SLOT_CATEGORY_COLORS.get(category, "#c8c8d0")


def _word_def(word_id: str) -> dict:
    from ..data.tamper_world import WORD_DEFS
    return WORD_DEFS[word_id]

def _condition_def(condition_id: str) -> dict:
    from ..data.tamper_world import CONDITION_DEFS
    return CONDITION_DEFS[condition_id]

def _category_label(category: str) -> str:
    from ..data.tamper_world import CATEGORY_LABELS
    return tr(CATEGORY_LABELS.get(category, category))
