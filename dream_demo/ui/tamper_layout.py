"""篡改面板的文本几何：折行、锚点竖线、删除高亮与命中映射（规格 §4.5）。

纯几何层：只吃片段与槽位定义，产出 Rich ``Text`` 与「屏幕行列 → (text_id,
slot_id)」的命中范围。不读游戏状态、不扣费、不改内容表。

坐标口径（与 :class:`~dream_demo.data.tamper_schema.HitSpan` 一致）：

* 行列都相对**返回的这块 Text**——已经扣掉 ``scroll``，界面拿鼠标偏移直接查；
* 列区间左闭右开，按显示单元计（双列汉字的第二列仍命中同一范围）；
* 跨行的删除范围拆成每行一个 span，点任意一段都回到同一个 slot。
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence
from dataclasses import dataclass

from rich.cells import cell_len
from rich.text import Text
from textual.geometry import Region, Size

from ..data.tamper_schema import HitSpan, TextFragment

#: 合法插入锚点的可见标记（终端 I 型光标不要求，正文内竖线是硬要求）。
INSERT_MARK = "│"

BASE_STYLE = "bright_white"
INSERT_STYLE = "bold #7ad0ff"
DELETE_STYLE = "bold #ff9f6b"
SELECTED_STYLE = "bold #ffffff on #2f5f7a"


class _Token:
    """一个显示单元：单个字符或一枚插入标记。"""

    __slots__ = ("char", "width", "fragment_id", "slot_id", "kind")

    def __init__(self, char: str, width: int, fragment_id: str,
                 slot_id: str = "", kind: str = "") -> None:
        self.char = char
        self.width = width
        self.fragment_id = fragment_id
        self.slot_id = slot_id
        self.kind = kind

    def style(self, selected: str) -> str:
        if self.slot_id and self.slot_id == selected:
            return SELECTED_STYLE
        if self.kind == "insert":
            return INSERT_STYLE
        if self.kind == "delete":
            return DELETE_STYLE
        return BASE_STYLE


def _tokenize(fragments: Iterable[TextFragment]) -> list[_Token]:
    tokens: list[_Token] = []
    for fragment in fragments:
        for char in str(fragment.text):
            tokens.append(_Token(char, max(0, cell_len(char)), fragment.fragment_id))
    return tokens


def _anchor_bounds(tokens: Sequence[_Token], fragment_id: str) -> tuple[int, int] | None:
    """锚点片段的首末 token 下标（不存在返回 None）。"""
    first = last = -1
    for index, token in enumerate(tokens):
        if token.fragment_id == fragment_id:
            if first < 0:
                first = index
            last = index
    return None if first < 0 else (first, last)


def apply_slots(tokens: Sequence[_Token], slots: Mapping[str, Mapping[str, Any]]) -> list[_Token]:
    """把槽位画到 token 流上：插入 = 竖线 token，删除 = 逐字标记。

    槽位定义见 :mod:`data.tampering`：``{"kind": "insert", "anchor": 片段 ID,
    "side": "before"/"after", "insert_fragment": 片段 ID}`` 或
    ``{"kind": "delete", "fragments": (片段 ID, ...)}``。锚点或范围在当前变体里
    不存在的槽位直接跳过——那是「这一句已经没有这个位置了」。
    """
    out = list(tokens)
    inserts: list[tuple[int, _Token]] = []
    for slot_id, slot in (slots or {}).items():
        kind = str((slot or {}).get("kind", ""))
        if kind == "insert":
            bounds = _anchor_bounds(out, str(slot.get("anchor", "")))
            if bounds is None:
                continue
            first, last = bounds
            index = first if str(slot.get("side", "before")) == "before" else last + 1
            inserts.append((index, _Token(INSERT_MARK, cell_len(INSERT_MARK),
                                          str(slot.get("anchor", "")), slot_id, "insert")))
        elif kind == "delete":
            wanted = {str(name) for name in (slot.get("fragments") or ())}
            for token in out:
                if token.fragment_id in wanted and not token.slot_id:
                    token.slot_id = slot_id
                    token.kind = "delete"
    # 倒序插入：同一段文字上多个锚点各自的位置不被前面的插入顶开。
    for index, token in sorted(inserts, key=lambda pair: pair[0], reverse=True):
        out.insert(index, token)
    return out


def wrap_tokens(tokens: Sequence[_Token], width: int) -> list[list[_Token]]:
    """按显示宽度贪心折行；双列字符不跨行拆开。"""
    limit = max(1, int(width))
    rows: list[list[_Token]] = []
    row: list[_Token] = []
    used = 0
    for token in tokens:
        if token.width and used + token.width > limit and row:
            rows.append(row)
            row, used = [], 0
        row.append(token)
        used += token.width
    rows.append(row)
    return rows


def layout_tamper_text(fragments: Sequence[TextFragment], *, text_id: str,
                       slots: Mapping[str, Mapping[str, Any]], width: int,
                       scroll: int = 0, height: int = 0,
                       selected: str = "") -> tuple[Text, tuple[HitSpan, ...]]:
    """排版一句可篡改正文，返回 (Rich Text, 命中范围)。

    ``slots`` 只放**当前阶段合法**的槽位（由调用方按变体图过滤）；``selected``
    是当前选中的 slot_id，用反白区分。``scroll`` 是首行下标，``height`` 为 0
    表示不裁剪。命中范围的行列相对返回的 Text，即已扣掉 ``scroll``。
    """
    tokens = apply_slots(_tokenize(fragments), slots)
    rows = wrap_tokens(tokens, width)
    start = max(0, min(int(scroll), max(0, len(rows) - 1)))
    stop = len(rows) if int(height) <= 0 else min(len(rows), start + int(height))
    text = Text()
    spans: list[HitSpan] = []
    last = stop - start - 1
    for row_index, row in enumerate(rows[start:stop]):
        column = 0
        run_slot = ""
        run_start = 0
        for token in row:
            if token.slot_id != run_slot:
                if run_slot:
                    spans.append(HitSpan(text_id, run_slot, row_index, run_start, column))
                run_slot, run_start = token.slot_id, column
            text.append(token.char, style=token.style(selected))
            column += token.width
        if run_slot:
            spans.append(HitSpan(text_id, run_slot, row_index, run_start, column))
        if row_index < last:
            text.append("\n")
    return text, tuple(spans)


def hit_tamper_slot(spans: Sequence[HitSpan], *, row: int, col: int) -> tuple[str, str] | None:
    """命中查询：返回 (text_id, slot_id)；点空白处返回 None。"""
    for span in spans or ():
        if span.row == int(row) and span.start_col <= int(col) < span.end_col:
            return span.text_id, span.slot_id
    return None


def layout_size(spans: Sequence[HitSpan], text: Text) -> Size:
    """这块 Text 的实测尺寸（摆放面板时算 desired 用）。"""
    lines = text.plain.splitlines() or [""]
    return Size(max(cell_len(line) for line in lines), len(lines))


def place_tamper_panel(*, screen: Region, dialogue: Region, desired: Size) -> Region:
    """完整面板优先：不动原框、移动原框、覆盖原框，始终限制在地图区。"""
    return plan_tamper_panels(screen=screen, dialogue=dialogue, desired=desired).panel


@dataclass(frozen=True)
class TamperPanelPlacement:
    dialogue: Region
    panel: Region
    overlapping: bool = False


def _clamp_region(region: Region, screen: Region) -> Region:
    width = max(1, min(region.width, screen.width))
    height = max(1, min(region.height, screen.height))
    return Region(max(screen.x, min(region.x, screen.right - width)),
                  max(screen.y, min(region.y, screen.bottom - height)), width, height)


def _free_panel(screen: Region, dialogue: Region, desired: Size) -> Region | None:
    gap = 1
    spaces = (
        Region(dialogue.right + gap, screen.y, max(0, screen.right - dialogue.right - gap), screen.height),
        Region(screen.x, screen.y, max(0, dialogue.x - screen.x - gap), screen.height),
        Region(screen.x, dialogue.bottom + gap, screen.width, max(0, screen.bottom - dialogue.bottom - gap)),
        Region(screen.x, screen.y, screen.width, max(0, dialogue.y - screen.y - gap)),
    )
    # The largest complete free area wins; ties keep right/left/below/above order.
    for space in sorted(spaces, key=lambda r: r.width * r.height, reverse=True):
        if space.width >= desired.width and space.height >= desired.height:
            return _clamp_region(Region(dialogue.x, dialogue.y, desired.width, desired.height), space)
    return None


def plan_tamper_panels(*, screen: Region, dialogue: Region, desired: Size) -> TamperPanelPlacement:
    desired = Size(max(1, min(desired.width, screen.width)),
                   max(1, min(desired.height, screen.height)))
    original = _clamp_region(dialogue, screen)
    panel = _free_panel(screen, original, desired)
    if panel is not None:
        return TamperPanelPlacement(original, panel)
    moved = []
    for x, y in ((screen.x, original.y), (screen.right - original.width, original.y),
                 (original.x, screen.y), (original.x, screen.bottom - original.height)):
        candidate = _clamp_region(Region(x, y, original.width, original.height), screen)
        panel = _free_panel(screen, candidate, desired)
        if panel is not None:
            distance = abs(candidate.x - original.x) + abs(candidate.y - original.y)
            moved.append((distance, candidate, panel))
    if moved:
        _, candidate, panel = min(moved, key=lambda entry: entry[0])
        return TamperPanelPlacement(candidate, panel)
    panel = _clamp_region(Region(original.x, original.y, desired.width, desired.height), screen)
    return TamperPanelPlacement(original, panel, overlapping=True)
