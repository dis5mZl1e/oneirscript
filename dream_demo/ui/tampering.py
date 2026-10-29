"""篡改的地图区编辑浮层与键鼠控制。

面板只画玩家该看见的东西：当前仍有合法位置的词与「删除」、可选位置、一处改文
预览、想象力代价、混乱度增量与提交后的档位。片段 ID、变体 ID、风险概率与事件
池都不进这块面板（§4.2）。

坐标口径与 :mod:`ui.tamper_layout` 一致：命中行列相对面板**内容区**，鼠标偏移
先扣掉控件的实际 gutter：上边框 1 行，左右边框与内距各 2 格。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Sequence

from rich.cells import cell_len
from rich.text import Text
from textual.geometry import Region, Size

from ..core.chaos import chaos_risk_tier
from ..core.tamper_views import (
    available_tamper_transitions,
    current_tamper_target,
    definitions_for_target,
    resolve_tamper_text,
)
from ..core.tampering import make_request, preview_tamper
from ..data.tamper_schema import (
    HitSpan,
    TamperPreview,
    TamperRequest,
    TamperTarget,
    TamperTransition,
)
from ..data.tampering import DELETE_WORD_ID, TAMPER_WORDS, definition_for, word_label
from ..i18n import get_language, tr
from .tamper_layout import hit_tamper_slot, layout_tamper_text
from . import tamper_presentation as presentation
from .tamper_host import TamperHostMixin
from . import tamper_animation as anim

#: 词的展示顺序（词表固定，规格 §3.2）；「删除」排最后。
WORD_ORDER: dict[str, int] = {word.word_id: index for index, word in enumerate(TAMPER_WORDS)}

#: 面板装饰占格：round 边框左右各 1 + padding 左右各 1。
INSET_X = 4
INSET_Y = 2

TITLE_STYLE = "bold #7ad0ff"
MUTED = "grey62"
SELECTED = "bold #7ad0ff"
NORMAL = "bright_white"
CONFIRM_STYLE = "bold #9dff8f"
CANCEL_STYLE = "grey70"
COST_STYLE = "#e6bd78"
RISK_STYLE = "bold #ff9f6b"


@dataclass(frozen=True)
class TamperWordGroup:
    """词表里的一行：同一句话上的同一个词，带它当前所有合法位置。"""

    text_id: str
    word_id: str
    transitions: tuple[TamperTransition, ...]

    @property
    def label(self) -> str:
        return word_label(self.word_id, get_language())

    @property
    def cost(self) -> int:
        return int(self.transitions[0].imagination_cost)

    @property
    def chaos(self) -> int:
        return int(self.transitions[0].chaos_delta)


def build_word_groups(state: Any, target: TamperTarget | None) -> tuple[TamperWordGroup, ...]:
    """把「仍然合法的变化」按 (句子, 词) 收成词表行。

    只列当前变体下确实改得动的位置（规格 §4.1「仅展示当前文字中仍有合法位置的
    操作」）：某句话全部位置用尽，它就不会出现在词表里。
    """
    if target is None:
        return ()
    rank = {definition.text_id: index
            for index, definition in enumerate(definitions_for_target(target))}
    buckets: dict[tuple[str, str], list[TamperTransition]] = {}
    for text_id, transition in available_tamper_transitions(state, target):
        key = (text_id, transition.word_id or DELETE_WORD_ID)
        buckets.setdefault(key, []).append(transition)
    keys = sorted(buckets, key=lambda key: (rank.get(key[0], len(rank)),
                                            WORD_ORDER.get(key[1], len(WORD_ORDER))))
    return tuple(TamperWordGroup(text_id, word_id, tuple(buckets[(text_id, word_id)]))
                 for text_id, word_id in keys)


@dataclass
class TamperEditorState(presentation.TamperViewState):
    """一次篡改编辑的全部临时状态；关闭对话即丢弃，不进存档。"""

    target: TamperTarget
    groups: tuple[TamperWordGroup, ...]
    phase: str = "word"                       # word → position → preview
    group_index: int = 0
    position_index: int = 0
    hover_slot: str = ""
    request: TamperRequest | None = None
    preview: TamperPreview | None = None
    scroll: int = 0
    #: 最近一次渲染的产物：命中范围、正文首行在面板里的行号、逐行标签。
    spans: tuple[HitSpan, ...] = ()
    sentence_row: int = -1
    sentence_skip: int = 0
    rows: list[Any] = field(default_factory=list)
    confirm_cols: tuple[int, int] = (0, 0)
    cancel_cols: tuple[int, int] = (0, 0)
    dialogue_region: Region | None = None
    details_expanded: bool = False
    follow_selection: bool = False
    # UI-only 短脉冲（装饰时钟）：不入存档、不推进世界。
    pulse_kind: str = ""
    pulse_born: float = 0.0
    pulse_life: float = 0.0

    @property
    def group(self) -> TamperWordGroup | None:
        if 0 <= self.group_index < len(self.groups):
            return self.groups[self.group_index]
        return None

    @property
    def transition(self) -> TamperTransition | None:
        group = self.group
        if group is None or not 0 <= self.position_index < len(group.transitions):
            return None
        return group.transitions[self.position_index]

    @property
    def slot_id(self) -> str:
        transition = self.transition
        return transition.slot_id if transition is not None else ""


class TamperUIMixin(TamperHostMixin):
    """篡改面板：打开、渲染、键盘、鼠标与提交。"""

    tamper_editor: TamperEditorState | None = None

    def _tamper_original_lines(self, state, text_id, plain, width):
        editor = self.tamper_editor
        if editor is None or editor.phase == 'word' or editor.group.text_id != text_id:
            return self._split_by_width(plain, width)
        body, spans = self._tamper_sentence(state, editor, width)
        lines = list(body.split('\n'))
        for row, line in enumerate(lines):
            self._dialog_tamper_line_spans[id(line)] = tuple(
                span for span in spans if span.row == row)
        return lines

    def _append_tamper_dialog_line(self, text, line, *, prefix='', style='bright_white'):
        row = len(self._dialog_rows)
        for span in self._dialog_tamper_line_spans.get(id(line), ()):
            self._dialog_tamper_spans.append(HitSpan(
                span.text_id, span.slot_id, row,
                span.start_col + cell_len(prefix), span.end_col + cell_len(prefix)))
        text.append(prefix, style=style)
        if isinstance(line, Text):
            text.append_text(line)
        else:
            text.append(line, style=style)
        text.append('\n')

    def _refresh_tamper_text(self):
        # 正文和侧栏共用当前槽位，任何选择变化都必须同时重建命中坐标。
        self.refresh_view()

    # ── UI 局部短脉冲（装饰时钟，不碰世界） ──────────────────────────────
    def _tamper_pulse(self, kind: str, life: float) -> None:
        editor = self.tamper_editor
        if editor is None:
            return
        editor.pulse_kind = str(kind)
        editor.pulse_born = time.monotonic()
        editor.pulse_life = float(life)
        timer = self._tamper_anim_timer()
        if timer is not None:
            timer.resume()

    def _tamper_anim_timer(self):
        timer = getattr(self, '_tamper_anim_timer_handle', None)
        if timer is None:
            try:
                timer = self.set_interval(1 / 20, self._tamper_anim_tick, pause=True)
            except Exception:
                return None
            self._tamper_anim_timer_handle = timer
        return timer

    def _tamper_pulse_stop(self) -> None:
        timer = getattr(self, '_tamper_anim_timer_handle', None)
        if timer is not None:
            timer.pause()
        editor = self.tamper_editor
        if editor is not None:
            editor.pulse_kind = ""
            editor.pulse_born = 0.0
            editor.pulse_life = 0.0

    def _tamper_anim_tick(self) -> None:
        from textual.css.query import NoMatches

        editor = self.tamper_editor
        if editor is None or not editor.pulse_kind:
            self._tamper_pulse_stop()
            return
        age = time.monotonic() - editor.pulse_born
        if age >= editor.pulse_life:
            self._tamper_pulse_stop()
        try:
            # 计时器可能在 App 退出/组件卸载的同一拍触发：此时刷新会因
            # #equipment-sentence 等控件已不在 DOM 而抛 NoMatches。停掉脉冲
            # 即可，不能把 teardown 竞态升级成整局崩溃。
            self._refresh_tamper_text()
        except NoMatches:
            self._tamper_pulse_stop()

    def _tamper_pulse_view(self) -> tuple:
        editor = self.tamper_editor
        if editor is None or not editor.pulse_kind:
            return "", 1.0
        age = time.monotonic() - editor.pulse_born
        return editor.pulse_kind, anim.pulse_progress(age, editor.pulse_life)

    # ── 入口 ────────────────────────────────────────────────────────────
    def _tamper_key_label(self) -> str:
        """玩家提示里的键名：读实际绑定（规格 §4.1），不写死 C。"""
        try:
            bound = str(self.config.get("key_tamper") or "c")
        except Exception:  # pragma: no cover - 注册表被裁剪时的兜底
            bound = "c"
        return (bound.strip().upper() or "C")

    def _tamper_hint_line(self) -> str:
        """对话面板底部的入口提示（只在该上下文里出现，Footer 不常驻）。"""
        return tr("[{key}] 篡改", key=self._tamper_key_label())

    def open_tamper_editor(self) -> bool:
        """以地图区编辑浮层替换对话；保留 pending 对话供退出时恢复。"""
        state = self.session.state
        if self.home_mode or state.run_over or self.panel_mode != "event_dialog":
            return False
        target = current_tamper_target(state)
        groups = build_word_groups(state, target)
        if not groups:
            return False
        if getattr(self,'world_tamper_editor',None) is not None:
            self.close_world_tamper_editor(refresh=False)
            self.panel_mode = 'event_dialog'
        pane = self.query_one('#map-pane')
        screen = Region(0, 0, pane.content_size.width, pane.content_size.height)
        origin = self._tamper_dialogue_region(screen)
        overlay = self.query_one('#map-overlay')
        rules = overlay.styles.get_rules() if hasattr(overlay.styles, 'get_rules') else {}
        self._tamper_dialogue_style_backup = {key: rules.get(key) for key in ('position', 'offset', 'width', 'height')}
        self.tamper_editor = TamperEditorState(target=target, groups=groups, dialogue_region=origin)
        self._tamper_pulse_stop()
        self._capture_tamper_view(self.tamper_editor)
        self.refresh_view()
        return True

    def close_tamper_editor(self, *, refresh: bool = True) -> None:
        """收起面板并丢弃草稿（规格 §4.4：Esc 逐级退，最后才关对话）。"""
        if self.tamper_editor is None:
            return
        self._restore_tamper_view(self.tamper_editor)
        self._restore_tamper_dialogue()
        self._tamper_pulse_stop()
        self.tamper_editor = None
        if refresh:
            self.refresh_view()

    def _restore_tamper_dialogue(self) -> None:
        backup = getattr(self, '_tamper_dialogue_style_backup', None)
        if backup is None:
            return
        overlay = self.query_one('#map-overlay')
        for key, value in backup.items():
            if value is not None:
                setattr(overlay.styles, key, value)
            elif hasattr(overlay.styles, 'clear_rule'):
                overlay.styles.clear_rule(key)
        self._tamper_dialogue_style_backup = None
        self._tamper_dialogue_fit_key = None

    def _tamper_target_alive(self, state: Any, target: TamperTarget) -> bool:
        """编辑目标还是不是眼前这一个实例（换对象、离层、读档错位都算失效）。"""
        live = current_tamper_target(state)
        return (live is not None
                and (live.kind, live.definition_id, live.instance_uid)
                == (target.kind, target.definition_id, target.instance_uid))

    # ── 渲染 ────────────────────────────────────────────────────────────
    def _tamper_dialogue_region(self, screen: Region) -> Region:
        """对话浮层在地图内容坐标系里的区域（拿不到就当成整块可用区）。"""
        editor = self.tamper_editor
        if editor is not None and editor.dialogue_region is not None:
            region = editor.dialogue_region
            width, height = min(region.width, screen.width), min(region.height, screen.height)
            return Region(max(0, min(region.x, screen.width - width)),
                          max(0, min(region.y, screen.height - height)), width, height)
        try:
            overlay = self.query_one("#map-overlay")
            pane = self.query_one("#map-pane")
            origin = pane.content_region.offset
            region = overlay.region
            if region.width and region.height and str(overlay.styles.display) != "none":
                return Region(region.x - origin.x, region.y - origin.y,
                              region.width, region.height)
        except Exception:  # pragma: no cover - 挂载早期
            pass
        return Region(screen.x, screen.y, max(1, screen.width // 2), max(3, screen.height - 2))


    def _tamper_sentence(self, state: Any, editor: TamperEditorState,
                         width: int) -> tuple[Text, tuple[HitSpan, ...]]:
        """当前编辑句：按阶段决定画出哪些位置（预览阶段只画选中的那一处）。"""
        group = editor.group
        definition = definition_for(group.text_id) if group is not None else None
        if definition is None:
            return Text(), ()
        language = get_language()
        fragments = resolve_tamper_text(state, editor.target, group.text_id, language=language)
        table = definition.slots(language)
        if editor.phase == "preview":
            wanted: Sequence[str] = (editor.slot_id,)
        else:
            wanted = tuple(transition.slot_id for transition in group.transitions)
        slots = {slot_id: table[slot_id] for slot_id in wanted if slot_id in table}
        selected = editor.hover_slot or editor.slot_id
        return layout_tamper_text(fragments, text_id=group.text_id, slots=slots,
                                  width=width, selected=selected)

    def _tamper_panel_text(self, state: Any, editor: TamperEditorState,
                           width: int, max_rows: int) -> Text:
        """重建整块面板：同时刷新命中范围与逐行标签（旧坐标一律作废）。"""
        group = editor.group
        entries: list[tuple[Any, Text]] = []
        # 每次重建都作废上一帧的命中范围（规格 §4.5：旧坐标不能继续提交）。
        editor.spans = ()
        editor.sentence_row = -1
        editor.rows = []

        def add(tag: Any, line: str | Text, style: str = NORMAL) -> None:
            entries.append((tag, line if isinstance(line, Text) else Text(line, style=style)))

        pulse_kind, pulse_progress = self._tamper_pulse_view()
        add(('title',), tr("篡改"),
            anim.pulse_title_style(TITLE_STYLE, pulse_kind, pulse_progress))
        # The full sentence is visible from the first word selection onward.
        # Preview shows the complete result first; the original anchors remain
        # available below for repositioning with the mouse.
        if group is not None:
            if editor.phase == 'preview' and editor.preview is not None:
                kind = anim.word_kind(editor.group.word_id) if editor.group is not None else "replace"
                line = anim.preview_result_line(
                    kind, editor.group.label if editor.group is not None else "",
                    editor.preview.after_text, pulse_progress)
                if editor.preview.available:
                    line += anim.condition_marker(True, pulse_progress)
                add(('result',), line,
                    anim.preview_result_style('bold ' + presentation.EFFECT,
                                              pulse_kind or kind, pulse_progress))
            if editor.phase != 'preview' or editor.details_expanded:
                sentence, spans = self._tamper_sentence(state, editor, width)
                editor.spans = spans
                add(('sentence',), sentence)
        if group is None:
            add(None, tr("这里已经没有可改的位置了。"), MUTED)
        elif editor.phase == "word":
            add(None, "── " + tr("选词") + " ──", 'bold ' + presentation.WORD)
            for index, entry in enumerate(editor.groups):
                if index == editor.group_index and pulse_kind == "select":
                    marker = anim.selected_marker(pulse_progress)
                else:
                    marker = "▶ " if index == editor.group_index else "  "
                style = ('bold underline ' if index == editor.group_index else '') + presentation.WORD
                from ..data.semantic_icons import icon_label
                label = Text(marker,style=style)
                label.append_text(icon_label('tamper.dialog.'+entry.word_id,entry.label,style))
                add(("word", index), label, style)
        else:
            heading = tr("预览") if editor.phase == "preview" else tr("位置")
            add(None, "── " + tr("{heading}：{word}", heading=heading, word=group.label) + " ──", presentation.WORD)
            if editor.phase == "position":
                total = len(group.transitions)
                add(None, tr("位置 {index}/{total}", index=editor.position_index + 1, total=total), MUTED)
            else:
                preview = editor.preview
                if preview is not None:
                    add(('preview_cost',), tr("想象力 −{cost} · 混乱度 +{delta} → {chaos}（{tier}）",
                                 cost=preview.imagination_cost, delta=preview.chaos_delta,
                                 chaos=preview.chaos_after, tier=tr(preview.risk_tier)), presentation.COST)
                    if preview.risk_note:
                        add(('preview_risk',), preview.risk_note,
                            anim.pulse_risk_style(presentation.RISK, pulse_kind, pulse_progress))
                    if not preview.available and preview.reason:
                        for line in self._split_by_width(preview.reason, max(8, width - 2)):
                            add(('unavailable',), line, presentation.RISK)
        if group is not None:
            if editor.phase != 'preview' and editor.transition is not None:
                quote = preview_tamper(state, make_request(state, editor.target, group.text_id,
                                                         editor.transition.transition_id))
                add(('preview_cost',), tr("想象力 −{cost} · 混乱度 +{delta} → {chaos}（{tier}）",
                    cost=quote.imagination_cost, delta=quote.chaos_delta,
                    chaos=quote.chaos_after, tier=tr(quote.risk_tier)), presentation.COST)
                if quote.risk_note:
                    add(('preview_risk',), quote.risk_note,
                        anim.pulse_risk_style(presentation.RISK, pulse_kind, pulse_progress))
                if not quote.available and quote.reason:
                    add(('unavailable',), quote.reason, presentation.RISK)
            from ..data.semantic_icons import icon_label
            add(('details',), icon_label('ui.details',presentation.details_label(editor.details_expanded),presentation.MUTED))
            if editor.details_expanded:
                add(None, tr("想象力 {imagination} · 混乱度 {chaos}（{tier}）",
                    imagination=int(state.imagination), chaos=int(state.chaos),
                    tier=tr(chaos_risk_tier(int(state.chaos)))), presentation.COST)
                if editor.preview and editor.preview.effect_note:
                    add(None, editor.preview.effect_note, presentation.EFFECT)
                add(None, self._tamper_help_line(editor), MUTED)
            confirm = icon_label('ui.confirm',"[" + tr("确认") + "]",CONFIRM_STYLE if editor.phase == 'preview' else MUTED)
            cancel = icon_label('ui.cancel',"[" + tr("取消") + "]",CANCEL_STYLE)
            confirm_width,cancel_width = cell_len(confirm.plain),cell_len(cancel.plain)
            editor.confirm_cols = (0, confirm_width)
            separate = confirm_width + 2 + cancel_width > width
            editor.cancel_cols = ((0, cancel_width) if separate else
                (confirm_width + 2, confirm_width + 2 + cancel_width))
            line = Text()
            confirm_style = CONFIRM_STYLE if editor.phase == "preview" else MUTED
            line.append_text(confirm)
            if not separate:
                line.append("  ", style=MUTED)
                line.append_text(cancel)
            add(("confirm",), line)
            if separate:
                add(('cancel',), cancel, CANCEL_STYLE)
            add(('view',), icon_label('ui.view',tr('[查看地图 V]'),presentation.CONDITION), presentation.CONDITION)
            if not editor.details_expanded:
                add(None, self._tamper_help_line(editor), MUTED)

        # 逐行摊平（正文块可能占多行），滚动与命中都按摊平后的行号算。
        # 除正文块以外，任何超宽的行都在**这里**折到排版宽度：面板宽可能被摆放
        # 逻辑压窄，超宽行会被控件重排，命中行号就与渲染行号错位了。
        flat: list[tuple[Any, Text]] = []
        for tag, chunk in entries:
            for line in chunk.split("\n"):
                if tag == ("sentence",) or cell_len(line.plain) <= width:
                    flat.append((tag, line))
                    continue
                for folded in presentation.folded_lines(line, width):
                    flat.append((tag, folded))
        editor.rows = []
        editor.sentence_row = -1
        max_rows = max(1, int(max_rows))
        tags = [tag for tag, _ in flat]
        top = {('title',), ('result',)}
        if editor.phase != 'preview':
            top.add(('sentence',))
        # Actions always have priority over long risk prose on extreme resizes.
        action_indices = [i for i, tag in enumerate(tags) if tag in (('confirm',), ('cancel',), ('view',))]
        order = [i for i in range(len(flat)) if i not in action_indices] + action_indices
        flat = [flat[i] for i in order]; tags = [tags[i] for i in order]
        indices, editor.scroll, _, _ = presentation.section_window(
            tags, top=top, bottom={('preview_cost',), ('preview_risk',), ('unavailable',), ('confirm',), ('cancel',), ('view',)},
            height=max_rows, scroll=editor.scroll,
            follow=('word', editor.group_index) if editor.follow_selection else None,
            actions={('confirm',), ('cancel',), ('view',)})
        editor.follow_selection = False
        original_spans = editor.spans
        sentence_indices = [i for i, tag in enumerate(tags) if tag == ('sentence',)]
        sentence_source_rows = {i: row for row, i in enumerate(sentence_indices)}
        editor.sentence_skip = 0
        editor.spans = ()
        visible = [flat[i] if i is not None else (None,Text()) for i in indices]
        text = Text()
        for index, (tag, line) in enumerate(visible):
            if index:
                text.append("\n")
            text.append_text(line)
            editor.rows.append(tag)
            if tag == ("sentence",) and editor.sentence_row < 0:
                editor.sentence_row = index
        if editor.sentence_row >= 0:
            # Pinning changes row order. Rebuild actual visible hit spans rather
            # than reusing an old continuous-scroll offset.
            editor.spans = tuple(HitSpan(span.text_id, span.slot_id,
                row - editor.sentence_row, span.start_col, span.end_col)
                for row, source in enumerate(indices) if source in sentence_source_rows
                for span in original_spans if span.row == sentence_source_rows[source])
        return text

    def _tamper_help_line(self, editor: TamperEditorState) -> str:
        if editor.phase == "word":
            return tr("↑↓ 选词 · Enter 看位置 · Esc 收起")
        if editor.phase == "position":
            return tr("←→ 换位置 · ↑↓ 换句子 · Enter 预览 · Esc 回词表")
        return tr("Enter 确认 · Backspace 回词表 · Esc 退回")


    def scroll_tamper(self, delta: int) -> None:
        editor = self._active_tamper_editor()
        if editor is None:
            return
        editor.scroll = max(0, int(editor.scroll) + int(delta))
        self._world_tamper_follow_selection = False
        self._refresh_tamper_overlay()

    # ── 键盘 ────────────────────────────────────────────────────────────
    def handle_tamper_key(self, key: str) -> bool:
        """编辑期间的按键：吞掉对话的数字/Enter，避免一键同时改文与交易。"""
        editor = self.tamper_editor
        if editor is None:
            return False
        if self._tamper_preview_key(key):
            return True
        state = self.session.state
        if key in ('backslash', '\\'):
            editor.details_expanded = not editor.details_expanded
            self._refresh_tamper_text()
            return True
        if key in ("up", "w", "8", "num8", "kp8"):
            if editor.phase == "word":
                self._tamper_select_group(editor.group_index - 1)
            else:
                self._tamper_select_group(editor.group_index - 1, keep_phase=True)
            return True
        if key in ("down", "s", "2", "num2", "kp2"):
            if editor.phase == "word":
                self._tamper_select_group(editor.group_index + 1)
            else:
                self._tamper_select_group(editor.group_index + 1, keep_phase=True)
            return True
        if key in ("left", "a", "4", "num4", "kp4"):
            return self._tamper_move_position(-1)
        if key in ("right", "d", "6", "num6", "kp6"):
            return self._tamper_move_position(1)
        if key in ("pageup", "9", "num9", "kp9"):
            self.scroll_tamper(-3)
            return True
        if key in ("pagedown", "3", "num3", "kp3"):
            self.scroll_tamper(3)
            return True
        if key in ("enter", "return"):
            self._tamper_advance(state)
            return True
        if key == "backspace":
            self._tamper_back(state)
            return True
        if key == "escape":
            self._tamper_escape(state)
            return True
        # 其余按键（含数字选项、Tab 等面板快捷键）一律消费：编辑期间不穿透。
        return True

    def _tamper_select_group(self, index: int, *, keep_phase: bool = False) -> None:
        editor = self.tamper_editor
        if editor is None or not editor.groups:
            return
        editor.group_index = max(0, min(len(editor.groups) - 1, int(index)))
        editor.follow_selection = True
        self._tamper_pulse("select", anim.SELECT_PULSE)
        group = editor.group
        editor.position_index = min(editor.position_index, len(group.transitions) - 1)
        editor.hover_slot = ""
        if not keep_phase:
            editor.phase = "word"
            editor.request = None
            editor.preview = None
        elif editor.phase == "preview":
            # 换句子/换词后旧预览的 request 已经指向别处：作废，回到位置阶段。
            editor.phase = "position" if len(group.transitions) > 1 else "word"
            editor.request = None
            editor.preview = None
        self._refresh_tamper_text()

    def _tamper_move_position(self, delta: int) -> bool:
        editor = self.tamper_editor
        if editor is None or editor.phase == "word":
            return True
        group = editor.group
        total = len(group.transitions)
        editor.position_index = (editor.position_index + int(delta)) % total if total else 0
        editor.hover_slot = ""
        self._tamper_pulse("move", anim.MOVE_PULSE)
        if editor.phase == "preview":
            self._tamper_enter_preview()
        else:
            self._refresh_tamper_text()
        return True

    def _tamper_enter_preview(self) -> None:
        """按当前 (句子, 词, 位置) 生成请求与预览（纯读，不扣费）。"""
        editor = self.tamper_editor
        state = self.session.state
        transition = editor.transition if editor is not None else None
        if editor is None or transition is None:
            return
        request = make_request(state, editor.target, editor.group.text_id, transition.transition_id)
        editor.request = request
        editor.preview = preview_tamper(state, request)
        editor.phase = "preview"
        editor.hover_slot = ""
        self._tamper_pulse(anim.preview_pulse_kind(
            editor.group.word_id, bool(editor.preview.available)), anim.PREVIEW_PULSE)
        self._refresh_tamper_text()

    def _tamper_advance(self, state: Any) -> None:
        """Enter：词表 → 位置（只有一个位置时直接预览）→ 提交。"""
        editor = self.tamper_editor
        if editor is None:
            return
        group = editor.group
        if group is None:
            self.close_tamper_editor()
            return
        if editor.phase == "word":
            if len(group.transitions) == 1:
                editor.position_index = 0
                self._tamper_enter_preview()
                return
            editor.phase = "position"
            editor.position_index = 0
            self._refresh_tamper_text()
            return
        if editor.phase == "position":
            self._tamper_enter_preview()
            return
        self._tamper_commit(state)

    def _tamper_back(self, state: Any) -> None:
        """Backspace：从预览回到词表（规格 §4.4）。"""
        editor = self.tamper_editor
        if editor is None:
            return
        editor.phase = "word"
        editor.request = None
        editor.preview = None
        editor.hover_slot = ""
        self._refresh_tamper_text()

    def _tamper_escape(self, state: Any) -> None:
        """Esc：预览 → 位置 → 词表 → 收起面板；对话本身留给下一次 Esc。"""
        editor = self.tamper_editor
        if editor is None:
            return
        group = editor.group
        if editor.phase == "preview":
            editor.phase = "position" if group is not None and len(group.transitions) > 1 else "word"
            editor.request = None
            editor.preview = None
            self._refresh_tamper_text()
            return
        if editor.phase == "position":
            editor.phase = "word"
            editor.hover_slot = ""
            self._refresh_tamper_text()
            return
        self.close_tamper_editor()

    def _tamper_commit(self, state: Any) -> None:
        editor = self.tamper_editor
        if editor is None or editor.request is None:
            return
        result = self._apply("commit_tamper", editor.request)
        self._tamper_pulse("commit" if bool(getattr(result, "changed", False)) else "deny",
                           anim.COMMIT_PULSE if bool(getattr(result, "changed", False)) else anim.DENY_PULSE)
        message = str(getattr(result, "message", "") or "")
        if message:
            self.show_toast(message)
        if state.run_over:
            self.close_tamper_editor(refresh=False)
            self.refresh_view()
            return
        self._tamper_rebuild(state)
        self.refresh_view()

    def _tamper_rebuild(self, state: Any) -> None:
        """提交后重算词表：这句话可能已经没有合法位置，也可能全用尽了。"""
        editor = self.tamper_editor
        if editor is None:
            return
        groups = build_word_groups(state, editor.target)
        if not groups or not self._tamper_target_alive(state, editor.target):
            self.close_tamper_editor(refresh=False)
            return
        editor.groups = groups
        editor.group_index = min(editor.group_index, len(groups) - 1)
        group = editor.group
        editor.position_index = min(editor.position_index, len(group.transitions) - 1)
        editor.phase = "word"
        editor.request = None
        editor.preview = None
        editor.hover_slot = ""

    # ── 鼠标 ────────────────────────────────────────────────────────────
    def handle_tamper_mouse(self, widget_id: str, row: int, col: int, *,
                            event_kind: str, button: int = 1) -> bool:
        """篡改期间的鼠标：面板内选位置/确认，面板外只收面板（不穿透到世界）。"""
        inspection = getattr(self, '_inspection_active', None)
        if inspection is not None and inspection():
            return True
        world_editor = getattr(self, 'world_tamper_editor', None)
        if world_editor is not None:
            if widget_id != 'tamper-overlay':
                if event_kind != 'move' and not world_editor.map_preview:
                    self.close_world_tamper_editor()
                return True
            if event_kind == 'down' and button == 1:
                key = next((hit.key for hit in getattr(self, '_world_tamper_visible_hits', ())
                            if hit.contains(row,col)), None)
                self._world_tamper_click(key)
            elif event_kind == 'down' and button == 3:
                self.handle_world_tamper_key('escape')
            return True
        editor = self.tamper_editor
        if editor is None:
            return False
        if widget_id != "tamper-overlay":
            if widget_id == 'map-overlay' and editor.phase != 'word':
                hit = hit_tamper_slot(getattr(self, '_dialog_tamper_spans', ()),
                                      row=row, col=col)
                if event_kind == 'move':
                    slot = hit[1] if hit else ''
                    if editor.hover_slot != slot:
                        editor.hover_slot = slot
                        self._refresh_tamper_text()
                    return True
                if button == 3:
                    self._tamper_escape(self.session.state)
                    return True
                if hit is not None and button == 1:
                    editor.position_index = next(index for index, transition in
                        enumerate(editor.group.transitions) if transition.slot_id == hit[1])
                    self._tamper_enter_preview()
                    return True
                # 原正文的非合法位置不执行交互，也不丢弃编辑草稿。
                return True
            if event_kind == "move":
                return True
            # 编辑区以外的点击：先退出篡改，地图/对话那一下作废（规格 §4.3）。
            self.close_tamper_editor()
            return True
        if event_kind == "move":
            return self._tamper_hover(editor, row, col)
        if button == 3:
            self._tamper_escape(self.session.state)
            return True
        if button != 1:
            return True
        return self._tamper_click(editor, row, col)

    def _tamper_hover(self, editor: TamperEditorState, row: int, col: int) -> bool:
        hit = self._tamper_hit(editor, row, col)
        slot = hit[1] if hit is not None else ""
        if slot == editor.hover_slot:
            return True
        editor.hover_slot = slot
        self._refresh_tamper_text()
        return True

    def _tamper_hit(self, editor: TamperEditorState, row: int, col: int) -> tuple[str, str] | None:
        """命中查询：正文块的行号要减掉它在面板里的起始行。"""
        if editor.sentence_row < 0 or row < editor.sentence_row:
            return None
        return hit_tamper_slot(editor.spans,
                               row=row - editor.sentence_row + editor.sentence_skip, col=col)

    def _tamper_click(self, editor: TamperEditorState, row: int, col: int) -> bool:
        state = self.session.state
        if not 0 <= row < len(editor.rows):
            return True
        tag = editor.rows[row]
        if tag is None:
            return True
        if tag[0] == 'details':
            editor.details_expanded = not editor.details_expanded
            self._refresh_tamper_text()
            return True
        if tag[0] == 'view':
            self._toggle_tamper_map()
            return True
        if tag[0] == "word":
            index = int(tag[1])
            if index == editor.group_index and editor.phase == "word":
                self._tamper_advance(state)     # 再点同一条 = 确认（与对话手感一致）
            else:
                self._tamper_select_group(index)
            return True
        if tag[0] == "sentence":
            hit = self._tamper_hit(editor, row, col)
            if hit is None or editor.phase == "word":
                return True
            group = editor.group
            index = next((position for position, transition in enumerate(group.transitions)
                          if transition.slot_id == hit[1]), -1)
            if index < 0:
                return True
            editor.position_index = index
            editor.hover_slot = hit[1]
            if editor.phase == "preview":
                self._tamper_enter_preview()
            else:
                self._refresh_tamper_text()
            return True
        if tag[0] == 'cancel':
            self._tamper_escape(state)
            return True
        if tag[0] == "confirm":
            if editor.confirm_cols[0] <= col < editor.confirm_cols[1]:
                if editor.phase == "preview":
                    self._tamper_commit(state)
                else:
                    self._tamper_advance(state)
                return True
            if editor.cancel_cols[0] <= col < editor.cancel_cols[1]:
                self._tamper_escape(state)
            return True
        return True
