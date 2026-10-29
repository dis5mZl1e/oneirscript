"""携带意象·联想盘的独立编辑器（设计方案 §8.2、§8.3、§8.4）。

整屏覆盖层：打开时 `#layout` 隐藏，键盘输入全部被本模态吃掉，一步都不会
走到地图上。编辑器只改**草稿**——移动、旋转、拿起、放下都不结算时间；
只有「确认整理」（Enter 或按钮）走一次 `commit_board`，那才算一次行动。

盘面格是**逻辑格**，渲染时每格两终端列 × 一行（§8.3）。命中表按局部列
坐标直接换算 `x = (column - GRID_ORIGIN_X) // 2`，不从混合中英文文本反推。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.text import Text
from rich.console import Console
from rich.cells import cell_len
from textual.events import MouseDown, MouseMove
from textual.widgets import Static
from textual.containers import Vertical

from ..equipment.board import (
    DESTINATION_LABELS,
    DESTINATION_POLICIES,
    PIECE_SPECS,
    Piece,
    Placement,
    Trace,
    piece_cells,
)
from ..equipment.grammar import ACTIVE, DORMANT, PENDING, SATISFIED, UNFORMED
from ..equipment.item_shapes import shape_for
from ..equipment.links import endpoint_label
from ..equipment.senses import default_sense, resolve, senses_for, describe_sense
from ..equipment.shapes import ROTATIONS, occupied_cells, shape_area
from ..equipment.reading import scan
from ..equipment.roles import COLUMN_ROLES, ROLE_LABELS, resolve_role
from ..equipment.syntax import (board_roles, column_groups, column_names,
                                column_shorts, role_name)
from ..i18n import get_language, tr
from .styles import CARRIED_IMAGE_STYLE
from .equipment_art import icon_cell, icon_lines, piece_cell_text
from ..equipment.function_words import FUNCTION_WORDS

# 每逻辑格两终端列、一行（§8.3）。盘面左边框在 GRID_ORIGIN_X 列，
# 第一行盘面正文在 GRID_ORIGIN_Y 行（第 0 行是列号、第 1 行是上边框）。
CELL_COLUMNS = 2
GRID_ORIGIN_X = 4
GRID_ORIGIN_Y = 2

# 插片在格子里用**单列 ASCII 字母 + `*`**：中文标签、emoji、全角字只出现在
# 盘外图例，不充当拼图格正文（§8.3）。`*` 后缀把插片与装备字母区分开。
PIECE_GLYPHS = {
    'use_word': 'U', 'cover_word': 'C', 'maintain_word': 'M',
    'wet_gate': ':', 'buffer': '(', 'surge': '-', 'spark': '!',
    'blank_gate': '?', 'echo_cell': '.', 'splitter': ',', 'ember': '^', 'voice': '"',
    'period': '.', 'hit_clause': ':', 'hurt_clause': ':', 'touch_clause': ':', 'conceive_clause': ':',
}
TRACE_GLYPHS = {(connector, rotation): ',' if connector == 'straight' else ';'
                for connector in ('straight', 'corner') for rotation in ROTATIONS}

# 工具抽屉：第 0 项是空手（只搬装备），其余按 z 循环取用（§C.3 的工具抽屉）。
TOOLS: tuple[None | tuple[str, str], ...] = (
    None,
    ("piece", "word_de"),
    ("piece", "word_de_manner"),
    ("piece", "word_ba"),
    ("piece", "word_bei"),
    ("piece", "word_and"),
    ("piece", "word_or"),
    ("piece", "word_if"),
    ("piece", "word_else"),
    ("piece", "word_only"),
    ("piece", "word_from"),
    ("piece", "word_toward"),
    ("piece", "word_again"),
)

# 只有这三块插片会在盘面之外挑一格当落点（§5.5）：缓冲片抵扣的是自己身上的
# 创伤，移涌片抽水的水源固定是事件格，湿润门与留白门只做信息处理。
POLICY_PIECES = ("spark", "ember", "voice")

STYLE_CURSOR = "reverse"
STYLE_LEGAL = "on #1d3a24"
STYLE_ILLEGAL = "on #4a1d1d"
STYLE_FOCUS_EDGE = "bold " + CARRIED_IMAGE_STYLE

# 第十九节 §6／§10.1：盘外六字段色继续独立，但取色一律走面板字段注册表。
from .panel_fields import FIELD_COLORS as _PANEL_FIELDS

FIELD_COLORS = {
    'held': _PANEL_FIELDS['held'], 'tool': _PANEL_FIELDS['tool'],
    'effects': _PANEL_FIELDS['board_effects'],
    'cursor': _PANEL_FIELDS['board_cursor'], 'rotation': _PANEL_FIELDS['rotation'],
    'grammar': _PANEL_FIELDS['grammar'],
    'effect_row': _PANEL_FIELDS['degree'], 'sentence_effect': _PANEL_FIELDS['effect'],
    'selected': _PANEL_FIELDS['word'],
}


@dataclass(frozen=True)
class BoardListHit:
    row: int
    start_col: int
    end_col: int
    source: str
    instance_id: str
    list_position: int


@dataclass
class Held:
    """手上拿着的东西：装备实例、一段接梦线或一块插片。

    `from_board` 为真时 `origin` 记着它在草稿里被拿起前的样子，Esc 原样放回；
    为假时它是刚从行囊列表拿起的**新件**，Esc 只是松手（它仍留在行囊里）。
    """

    kind: str  # item | trace | piece
    instance_id: str = ""
    definition_id: str = ""
    shape_id: str = ""
    connector: str = "straight"
    piece_id: str = ""
    sense_id: str = ""
    sentence_written: bool = True
    was_focus: bool = False
    from_board: bool = False
    origin: Placement | Trace | Piece | None = field(default=None, repr=False)
    destination_policy: str = 'event_cell'
    priority: int = 0
    origin_index: int = 0

    @property
    def label(self) -> str:
        if self.kind == "item":
            return self.definition_id
        if self.kind == "trace":
            return self.connector
        return PIECE_SPECS[self.piece_id].label

    def cells(self, x: int, y: int, rotation: int) -> tuple[tuple[int, int], ...]:
        if self.kind == "item":
            return occupied_cells(self.shape_id, rotation, x, y)
        if self.kind == "trace":
            return ((x, y),)
        offsets = piece_cells(Piece(self.piece_id, 0, 0, rotation))
        return tuple((x + dx, y + dy) for dx, dy in offsets)


def tool_label(tool: None | tuple[str, str]) -> str:
    if tool is None:
        return tr("空手（搬动意象）")
    kind, identifier = tool
    if kind == "trace":
        return tr('逗号·连词') if identifier == 'straight' else tr('分号·断句')
    return tr(PIECE_SPECS[identifier].label)


class BoardEditorController:
    """编辑器的全部状态与规则。不依赖 Textual，可独立单测。"""

    def __init__(self, state):
        self.state = state
        self.draft = state.board_draft()
        self.cursor: tuple[int, int] = (0, 0)
        self.rotation: int = 0
        self.view: str = "equipment"  # equipment | links
        self.held: Held | None = None
        self.tool_index: int = 0
        self.message: str = ""
        self.list_rows: list[tuple[int, object]] = self._collect_rows()
        self.list_cursor: int = 0
        # 「说明区行号 → 行囊列表位置」命中表，render_side 每次重建（§8.1：
        # 盘面与列表各用自己的命中表，不混用）。
        self.side_row_map: list[int | None] = []
        self.side_hits: list[BoardListHit] = []

    # ---- 行囊列表 ----

    def _collect_rows(self) -> list[tuple[int, object]]:
        """可上盘的行囊条目：(行囊下标, 物品)。记忆槽不在这里（它钉在页底）。"""
        state = self.state
        return [
            (index, item) for index, item in enumerate(state.inventory)
            if state._placeable_slot(item)
        ]

    def refresh_rows(self) -> None:
        self.list_rows = self._collect_rows()
        self.list_cursor = min(self.list_cursor, max(0, len(self.list_rows) - 1))

    # ---- 查询 ----

    @property
    def tool(self) -> None | tuple[str, str]:
        return TOOLS[self.tool_index]

    def owner_at(self, cell: tuple[int, int]):
        return self.draft.cell_owners().get(cell)

    def preview_cells(self) -> tuple[tuple[int, int], ...]:
        if self.held is None:
            tool = self.tool
            if tool is None:
                return ()
            kind, identifier = tool
            probe = Held(kind=kind, connector=identifier, piece_id=identifier,
                         shape_id="D4")
            return probe.cells(*self.cursor, self.rotation)
        return self.held.cells(*self.cursor, self.rotation)

    def preview_legal(self) -> bool:
        word_id = (self.held.piece_id if self.held and self.held.kind == 'piece' else
                   self.tool[1] if self.tool and self.tool[0] == 'piece' else '')
        if word_id in FUNCTION_WORDS and (self.rotation != 0 or
                any(piece.piece_id == word_id for piece in self.draft.pieces)):
            return False
        cells = self.preview_cells()
        if not cells:
            return False
        return (self.draft.in_bounds(cells)
                and self.draft.is_free(cells, self.draft.cell_owners()))

    def item_name(self, definition_id: str, instance_id: str) -> str:
        if "oblivion_strong" in self.state.portents:
            return "？？？"
        item = next((it for it in self.state.inventory
                     if it.instance_id == instance_id), None)
        if item is not None:
            return tr(item.name)
        return tr(definition_id)

    # ---- 光标 ----

    def move(self, dx: int, dy: int) -> None:
        board = self.draft
        self.cursor = (
            max(0, min(board.width - 1, self.cursor[0] + dx)),
            max(0, min(board.height - 1, self.cursor[1] + dy)),
        )

    def move_list(self, delta: int) -> None:
        if not self.list_rows:
            return
        self.list_cursor = (self.list_cursor + delta) % len(self.list_rows)
        _, item = self.list_rows[self.list_cursor]
        placement = self.draft.placement(item.instance_id)
        if placement is not None:
            self.cursor = (placement.x, placement.y)

    def rotate(self) -> None:
        word_id = (self.held.piece_id if self.held and self.held.kind == 'piece' else
                   self.tool[1] if self.tool and self.tool[0] == 'piece' else '')
        if word_id in FUNCTION_WORDS:
            self.rotation = 0
            self.message = tr('功能词只允许横向摆放。')
            return
        self.rotation = ROTATIONS[(ROTATIONS.index(self.rotation) + 1) % len(ROTATIONS)] \
            if self.rotation in ROTATIONS else 0

    def cycle_tool(self, delta: int = 1) -> None:
        self.tool_index = (self.tool_index + delta) % len(TOOLS)
        if TOOLS[self.tool_index] is not None and self.held is not None:
            # 拿起工具时先把手上的东西放回原位：不能既拿装备又拿线材。
            self.cancel_held()
        self.message = tr("工具：{tool}", tool=tool_label(self.tool))
        if self.tool:
            self.rotation = 0

    def _piece_at_cursor(self) -> Piece | None:
        owner = self.owner_at(self.cursor)
        if owner is None or owner[0] != "piece":
            return None
        return next(
            (p for p in self.draft.pieces if (p.piece_id, p.x, p.y) == owner[1:]), None
        )

    def _line_semantics(self, piece: Piece) -> tuple[bool, set[str]]:
        """草稿口径：这块插片当前是否被线路接到、那些线路攒了哪些语义。"""
        wired = False
        semantics: set[str] = set()
        for path in self._preview_compiled().react_paths:
            if path.terminal_piece == piece.piece_id and path.terminal == (piece.x, piece.y):
                wired = True
                semantics |= set(path.semantics)
        return wired, semantics

    def policy_options(self, piece: Piece) -> list[str]:
        """落点档位表。「近处可见敌人」要照语义才解锁（§5.5）：已经接上线却没有
        照语义时，这一档根本不该出现在轮盘里；还没接线则允许先设好，接上之后执行
        层会因缺语义明确拒发，不会误打别的位置。"""
        wired, semantics = self._line_semantics(piece)
        options = list(DESTINATION_POLICIES)
        if wired and "照" not in semantics:
            options.remove("visible_enemy")
        return options

    def cycle_policy(self) -> None:
        """p：轮换光标下反馈插片的落点档位。"""
        piece = self._piece_at_cursor()
        if piece is None:
            self.message = tr("光标下没有插片：先按 z 取用工具，再按 a 把它铺在光标格。")
            return
        spec = PIECE_SPECS[piece.piece_id]
        if piece.piece_id not in POLICY_PIECES:
            self.message = tr("{tool} 没有落点档位：它不在盘面之外挑格子。", tool=tr(spec.label))
            return
        options = self.policy_options(piece)
        index = (options.index(piece.destination_policy)
                 if piece.destination_policy in options else 0)
        piece.destination_policy = options[(index + 1) % len(options)]
        self.message = tr("落点：{policy}", policy=tr(DESTINATION_LABELS[piece.destination_policy]))

    def cycle_priority(self) -> None:
        self.message = tr('旋转只改变形状；液体自动流向较空的合法邻格。')

    def piece_note(self) -> str:
        piece = self._piece_at_cursor()
        if piece is None:
            return ""
        spec = PIECE_SPECS[piece.piece_id]
        parts = [tr("{label} ({x},{y})", label=tr(spec.label), x=piece.x, y=piece.y)]
        if piece.piece_id in FUNCTION_WORDS:
            from ..equipment.positional import compile_formation
            row = compile_formation(self.draft, column_roles=board_roles(self.draft)).rows[piece.y]
            parts.append(tr('关系成立') if row.relations else tr(row.reason))
            return ' · '.join(parts)
        if piece.piece_id in POLICY_PIECES:
            parts.append(tr("落点 {policy}（p）",
                            policy=tr(DESTINATION_LABELS[piece.destination_policy])))
        elif piece.piece_id == "surge":
            parts.append(tr('水源是触发位置，流向较空的合法邻格'))
        wired, _semantics = self._line_semantics(piece)
        parts.append(tr('已读入句子') if wired else tr('分句标点'))
        return " · ".join(parts)

    def toggle_view(self) -> None:
        self.view = "links" if self.view == "equipment" else "equipment"

    # ---- 拿起 / 放下 ----

    def activate(self) -> None:
        """a／左键：手上有东西就放下，空手就拿起光标下的实体或取用工具。"""
        if self.held is not None:
            self._place_held(self.held)
            return
        tool = self.tool
        if tool is not None:
            kind, identifier = tool
            self._place_held(Held(kind=kind, connector=identifier, piece_id=identifier))
            return
        self._lift()

    def _lift(self) -> None:
        cell = self.cursor
        owner = self.owner_at(cell)
        if owner is None:
            self.message = tr("这一格是空的：用 , / . 选中下方列表里的一件再按空格拿起，"
                              "或按 z 取用工具后 a 铺线。")
            return
        board = self.draft
        if owner[0] == "item":
            placement = board.placement(owner[1])
            origin_index = board.placements.index(placement)
            board.placements.remove(placement)
            was_focus = board.focus_instance_id == placement.instance_id
            if was_focus:
                board.focus_instance_id = None
            self.held = Held(
                kind="item", instance_id=placement.instance_id,
                definition_id=placement.definition_id, shape_id=placement.shape_id,
                sense_id=placement.sense_id,
                sentence_written=placement.sentence_written,
                was_focus=was_focus, from_board=True, origin=placement, origin_index=origin_index,
            )
            self.rotation = placement.rotation if placement.rotation in ROTATIONS else 0
            self.message = tr("拿起了 {item}：方向键移动，r 旋转，a 放下。",
                              item=self.item_name(placement.definition_id,
                                                  placement.instance_id))
        elif owner[0] == "trace":
            trace = next(t for t in board.traces if (t.x, t.y) == cell)
            origin_index = board.traces.index(trace)
            board.traces.remove(trace)
            self.held = Held(kind="trace", connector=trace.connector, from_board=True,
                             origin=trace, origin_index=origin_index)
            self.rotation = trace.rotation
            self.message = tr("拿起了 {tool}。", tool=tool_label(("trace", trace.connector)))
        else:
            piece = next(p for p in board.pieces
                         if (p.piece_id, p.x, p.y) == owner[1:])
            origin_index = board.pieces.index(piece)
            board.pieces.remove(piece)
            self.held = Held(kind="piece", piece_id=piece.piece_id, from_board=True,
                             origin=piece, destination_policy=piece.destination_policy,
                             priority=piece.priority, origin_index=origin_index)
            self.rotation = piece.rotation
            self.message = tr("拿起了 {tool}。",
                              tool=tool_label(("piece", piece.piece_id)))

    def _place_held(self, held: Held) -> None:
        board = self.draft
        x, y = self.cursor
        if held.kind == 'piece' and held.piece_id in FUNCTION_WORDS:
            if any(piece.piece_id == held.piece_id for piece in board.pieces):
                self.message = tr('盘中已有这个功能词，请移动原词块。')
                return
            if self.rotation != 0:
                self.message = tr('功能词只允许横向摆放。')
                return
        cells = held.cells(x, y, self.rotation)
        if not board.in_bounds(cells):
            self.message = tr("越过盘面边框：{held} 放不进这个位置。",
                              held=self._held_name(held))
            return
        if not board.is_free(cells, board.cell_owners()):
            self.message = tr("这些格已经被占了：{held} 放不下（不自动挤掉其他件）。",
                              held=self._held_name(held))
            return
        if held.kind == "item":
            sense_id = (held.sense_id if held.from_board else
                        held.sense_id or default_sense(held.definition_id).sense_id)
            placement = Placement(
                instance_id=held.instance_id, definition_id=held.definition_id,
                shape_id=held.shape_id, x=x, y=y, rotation=self.rotation,
                sense_id=sense_id, sentence_written=held.sentence_written,
            )
            board.placements.append(placement)
            board.focus_instance_id = None
        elif held.kind == "trace":
            board.traces.append(Trace(x, y, held.connector, self.rotation))
        else:
            board.pieces.append(Piece(held.piece_id, x, y, self.rotation,
                                      held.destination_policy, held.priority))
        self.held = None
        self.message = ""
        self.refresh_rows()

    def _held_name(self, held: Held) -> str:
        if held.kind == "item":
            return self.item_name(held.definition_id, held.instance_id)
        return tool_label((held.kind, held.connector if held.kind == "trace"
                           else held.piece_id))

    def hold_from_list(self, position: int | None = None) -> None:
        """从行囊列表拿起一件（数字键或左键）：已上盘的件改为把它从盘上拿起。"""
        if not self.list_rows:
            self.message = tr("行囊里没有可上盘的携带意象。")
            return
        position = self.list_cursor if position is None else position
        if not 0 <= position < len(self.list_rows):
            return
        self.list_cursor = position
        index, item = self.list_rows[position]
        if self.held is not None:
            self.cancel_held()
        self.tool_index = 0
        placement = self.draft.placement(item.instance_id)
        if placement is not None:
            self.cursor = (placement.x, placement.y)
            self.held = None
            self._lift()
            return
        self.held = Held(
            kind="item", instance_id=item.instance_id,
            definition_id=item.definition_id, shape_id=shape_for(item.definition_id),
            sense_id=default_sense(item.definition_id).sense_id,
        )
        self.rotation = 0
        self.message = tr("拿起了 {item}（{area} 格）：方向键移动，r 旋转，a 放下。",
                          item=tr(item.name), area=shape_area(self.held.shape_id))

    def cancel_held(self) -> bool:
        """Esc 的第一层语义：把手上的东西放回原处。返回是否消费了这次 Esc。"""
        held = self.held
        if held is None:
            return False
        board = self.draft
        if held.from_board and held.origin is not None:
            if held.kind == "item":
                board.placements.insert(held.origin_index, held.origin)
                if held.was_focus:
                    board.focus_instance_id = held.instance_id
            elif held.kind == "trace":
                board.traces.insert(held.origin_index, held.origin)
            else:
                board.pieces.insert(held.origin_index, held.origin)
            self.message = tr("放回原位。")
        else:
            self.message = tr("松手了：{held} 仍在行囊里。", held=self._held_name(held))
        self.held = None
        self.refresh_rows()
        return True

    def discard(self) -> None:
        """x：丢掉手上的东西（装备退回行囊、线材／插片拆除）；空手时拆光标下的。"""
        if self.held is not None:
            name = self._held_name(self.held)
            self.held = None
            self.message = tr("已卸下 {held}。", held=name)
            self.refresh_rows()
            return
        cell = self.cursor
        owner = self.owner_at(cell)
        if owner is None:
            self.message = tr("这一格没有可拆除的东西。")
            return
        board = self.draft
        if owner[0] == "item":
            placement = board.placement(owner[1])
            board.placements.remove(placement)
            if board.focus_instance_id == placement.instance_id:
                board.focus_instance_id = None
            self.message = tr("已卸下 {item}。",
                              item=self.item_name(placement.definition_id,
                                                  placement.instance_id))
        elif owner[0] == "trace":
            board.traces = [t for t in board.traces if (t.x, t.y) != cell]
            self.message = tr("拆掉了这段接梦线。")
        else:
            board.pieces = [p for p in board.pieces
                            if (p.piece_id, p.x, p.y) != owner[1:]]
            self.message = tr("拆掉了这块插片。")
        self.refresh_rows()

    def auto_place(self) -> None:
        """自动安置：给选中的这一件找合法位置，不移动旧件（§8.4）。"""
        if not self.list_rows:
            self.message = tr("行囊里没有可上盘的携带意象。")
            return
        held = self.held if self.held is not None and self.held.kind == 'item' else None
        if self.held is not None and held is None:
            self.cancel_held()
        _, item = self.list_rows[self.list_cursor]
        if held is not None:
            item = next(it for _, it in self.list_rows if it.instance_id == held.instance_id)
        placement = self.draft.placement(item.instance_id)
        if placement is not None:
            self.message = tr("{item}已经在盘上了。", item=tr(item.name))
            return
        shape_id = shape_for(item.definition_id)
        from ..equipment.placement import suggest_placement
        draft = suggest_placement(self.draft, item.instance_id, item.definition_id)
        if draft is not None:
            placement = draft.placement(item.instance_id)
            self.draft = draft
            self.cursor = (placement.x, placement.y)
            self.rotation = placement.rotation
            self.held = None
            self.message = tr("自动安置 {item} 到 ({x},{y})，旋转 {rotation}°。",
                              item=tr(item.name), x=placement.x, y=placement.y,
                              rotation=placement.rotation)
            return
        self.message = tr("这里放不下 {item}：{area} 格的形状和现有摆放冲突，"
                          "先挪开或拆掉一些实体再试。",
                          item=tr(item.name), area=shape_area(shape_id))

    def set_focus(self) -> None:
        """握持：光标下的武器成为握持件。只改草稿，确认后才算一次行动。"""
        owner = self.owner_at(self.cursor)
        if owner is None or owner[0] != "item":
            self.message = tr("把光标移到盘上一件意象上再切换握持。")
            return
        placement = self.draft.placement(owner[1])
        sense = resolve(placement.definition_id, placement.sense_id)
        if not placement.sentence_written:
            self.message = tr("{item}还没有写出原意，不能握持。",
                              item=self.item_name(placement.definition_id,
                                                  placement.instance_id))
            return
        if sense.kind != "act":
            self.message = tr("{item}不是可握持的行动意象。",
                              item=self.item_name(placement.definition_id,
                                                  placement.instance_id))
            return
        if self.draft.focus_instance_id == placement.instance_id:
            self.message = tr("已经握着它了。")
            return
        self.draft.focus_instance_id = placement.instance_id
        self.message = tr("握持 {item}：按 Enter 确认后生效（一次行动）。",
                          item=self.item_name(placement.definition_id,
                                              placement.instance_id))

    def commit(self, session=None):
        """全盘确认：一次事务、一次行动。返回 ActionResult。"""
        if self.held is not None:
            self.cancel_held()
        return session.apply('commit_board', self.draft) if session is not None else self.state.commit_board(self.draft)

    def _selected_word(self):
        if self.held is not None and self.held.kind == 'item':
            return self.held
        owner = self.owner_at(self.cursor)
        return self.draft.placement(owner[1]) if owner and owner[0] == 'item' else None

    def cycle_sense(self):
        word = self._selected_word()
        if word is None:
            self.message = tr('先选中盘上或手中的意象，再切换词义。')
            return
        choices = senses_for(word.definition_id)
        current = resolve(word.definition_id, word.sense_id)
        word.sense_id = choices[(choices.index(current) + 1) % len(choices)].sense_id
        if resolve(word.definition_id, word.sense_id).kind != 'act':
            if self.draft.focus_instance_id == word.instance_id:
                self.draft.focus_instance_id = None
            if isinstance(word, Held):
                word.was_focus = False
        self.message = tr('词义：{meaning}', meaning=tr(resolve(word.definition_id, word.sense_id).label))

    def toggle_original(self):
        word = self._selected_word()
        if word is None:
            self.message = tr('先选中盘上或手中的意象，再写出或撤回原意。')
            return
        word.sentence_written = not word.sentence_written
        if not word.sentence_written:
            if self.draft.focus_instance_id == word.instance_id:
                self.draft.focus_instance_id = None
            if isinstance(word, Held):
                word.was_focus = False
        self.message = tr('原意已写出，确认后生效。') if word.sentence_written else tr('原意已撤回：只占空间，不提供效果或语义。')

    def render_inspect(self, width=40):
        word = self._selected_word()
        from .panels import zone_strip
        text = zone_strip(tr('选中意象'), width, color=FIELD_COLORS['selected'])
        if word is not None:
            text.append('\n' + self.item_name(word.definition_id, word.instance_id), style=CARRIED_IMAGE_STYLE)
            rotation = self.rotation if isinstance(word, Held) else word.rotation
            for line in icon_lines(word.definition_id, rotation):
                text.append('\n')
                text.append_text(line)
            from ..equipment.positional import compile_formation
            formation = compile_formation(self.draft, column_roles=board_roles(self.draft))
            voices = [v for v in formation.voices if v.instance_id == word.instance_id]
            from ..equipment.sentence_prose import voice_text
            for voice in sorted(voices, key=lambda v: (v.y, v.x)):
                role_label = (role_name(voice.response.role)
                              if voice.response.role in COLUMN_ROLES else '未采用联想')
                text.append('\n' + tr('({x},{y}) {role}：{meaning}',
                                      x=voice.x, y=voice.y, role=tr(role_label),
                                      meaning=voice_text(voice)), style=_PANEL_FIELDS['condition'])
            if not voices:
                text.append('\n' + tr('移动或旋转后，按占据的列自动解释。'), style=_PANEL_FIELDS['condition'])
            text.append('\n' + tr('同一实例多格发声，数值只计一次。'), style=_PANEL_FIELDS['condition'])
        else:
            piece = self._piece_at_cursor()
            tool = self.tool
            piece_id = piece.piece_id if piece else tool[1] if tool and tool[0] == 'piece' else ''
            if piece_id:
                spec = PIECE_SPECS[piece_id]
                text.append('\n' + tr(spec.label) + '\n' + tr(spec.detail), style=_PANEL_FIELDS['condition'])
                if spec.delay:
                    text.append('\n' + tr('存下这一刻不耗想象力；释放时采用后续标点的消耗与冷却。'), style=_PANEL_FIELDS['condition'])
                elif spec.feedback:
                    text.append('\n' + tr('想象 {cost} · 冷却 {cd}', cost=spec.cost,
                                          cd=spec.cooldown), style=_PANEL_FIELDS['condition'])
            else:
                text.append('\n' + tr('移动或旋转后，按占据的列自动解释。'), style=_PANEL_FIELDS['condition'])
        return text

    # ---- 渲染 ----

    @staticmethod
    def _wrap_fields(text: Text, width: int) -> Text:
        console = Console(width=max(1, width))
        return Text('\n').join(text.wrap(console, max(1, width), overflow='fold'))

    def render_grammar(self, width=80) -> Text:
        # 列角色按盘面语序取（英文语序把行为前移到第 4 列），不能写死中文分组。
        syntax = getattr(self.draft, 'syntax', 'zh')
        names = [tr(name) for name in column_names(syntax)]
        text = Text(' · '.join(number + ' ' + names[index]
                               for number, index in column_groups(syntax)),
                    style=FIELD_COLORS['grammar'])
        if syntax != 'zh':
            text.append('  ' + tr('（{syntax}）', syntax=tr('英文语序')),
                        style=FIELD_COLORS['grammar'])
        return self._wrap_fields(text, width)

    def render_status(self, width=80) -> Text:
        held = self._held_name(self.held) if self.held else tr('空手')
        text = Text()
        text.append(tr('手上：{held}', held=held), style=FIELD_COLORS['held'])
        text.append('\n')
        text.append(tr('工具：{tool}', tool=tool_label(self.tool)), style=FIELD_COLORS['tool'])
        text.append('\n')
        text.append(tr('光标 ({x},{y})', x=self.cursor[0], y=self.cursor[1]), style=FIELD_COLORS['cursor'])
        text.append('  ')
        text.append(tr('旋转 {rotation}°', rotation=self.rotation), style=FIELD_COLORS['rotation'])
        return self._wrap_fields(text, width)

    def sentence_fragments(self, compiled=None) -> tuple[tuple[str, str], ...]:
        """Main editor only: real board row coordinates and colored sentences."""
        compiled = self._preview_compiled() if compiled is None else compiled
        colors = (_PANEL_FIELDS['grammar'], _PANEL_FIELDS['word'],
                  _PANEL_FIELDS['effect'], _PANEL_FIELDS['identity'])
        fragments = []
        for index, sentence in enumerate(compiled.sentences):
            if index:
                fragments.append(('\n', _PANEL_FIELDS['text']))
            if sentence.source_rows:
                rows = tr('、').join(str(row) for row in sentence.source_rows)
                fragments.append((rows + ' ', _PANEL_FIELDS['text']))
            fragments.append((sentence.text, colors[index % len(colors)]))
        return tuple(fragments) or ((compiled.text, _PANEL_FIELDS['muted']),)

    def render_effects(self, width=80) -> Text:
        """Separate each sentence's effects, keeping heading and row colors distinct."""
        width = max(1, width)
        compiled = self._preview_compiled()
        from .panels import zone_strip
        text = zone_strip(tr('效果明细（确认后生效）'), width, color=FIELD_COLORS['effects'])

        def add(value, color=FIELD_COLORS['sentence_effect']):
            text.append('\n')
            text.append(value, style=color)

        from ..equipment.positional import compile_formation
        from ..equipment.runtime import plan_action
        preview = plan_action(compile_formation(self.draft, column_roles=board_roles(self.draft)), self.state, 'melee')
        if preview.valid:
            add(tr('近战：基础 1 + 装备 {bonus} · 耗时 {time}',
                   bonus=f'{preview.damage_increment:.3f}', time=f'{preview.base_time:g}'))
        for sentence in compiled.sentences:
            rows = tr('、').join(str(row) for row in sentence.source_rows)
            add(tr('第 {rows} 行 · {status}', rows=rows, status=tr(sentence.status)),
                'bold ' + FIELD_COLORS['effect_row'])
            for detail in sentence.details:
                add(tr(detail))
            if sentence.reason:
                add(tr(sentence.reason), _PANEL_FIELDS['muted'])
            if sentence.cost:
                add(tr(sentence.cost), _PANEL_FIELDS['cost'])
            add('─' * width, _PANEL_FIELDS['track'])
        effects = set()
        for placement in self.draft.placements:
            sense = default_sense(placement.definition_id)
            if sense.effect not in effects:
                note = self._diminish_note(compiled, sense)
                if note:
                    add(note)
                effects.add(sense.effect)
        if not compiled.sentences:
            add(tr('逐行成句；位置与旋转改变含义，缺少行为则休眠。'), _PANEL_FIELDS['muted'])
        note = self.piece_note()
        if note:
            add(note, _PANEL_FIELDS['muted'])
        if self.message:
            add(self.message, _PANEL_FIELDS['muted'])
        return self._wrap_fields(text, width)

    def hit_side(self, row: int, column: int) -> BoardListHit | None:
        return next((hit for hit in self.side_hits
                     if hit.row == row and hit.start_col <= column < hit.end_col), None)

    def _render_comparison(self, width: int) -> Text:
        width = max(5, width)
        left_width = (width - 3) // 2
        right_width = width - left_width - 3
        right_start = left_width + 3
        compiled = self._preview_compiled()
        self.side_hits, self.side_row_map = [], []
        text = Text(no_wrap=True)

        def folded(line, budget):
            return list(line.wrap(Console(width=budget), budget, overflow='fold'))

        def pair(left, right, left_target=None, right_target=None):
            row = len(self.side_row_map)
            if row:
                text.append('\n')
            lsize, rsize = cell_len(left.plain), cell_len(right.plain)
            text.append_text(left)
            text.append(' ' * (left_width - lsize) + ' │ ', style=FIELD_COLORS['grammar'])
            text.append(' ' * (right_width - rsize))
            text.append_text(right)
            self.side_row_map.append(right_target[1] if right_target else None)
            for source, target, start, length in (
                ('board', left_target, 0, lsize),
                ('inventory', right_target, right_start + right_width - rsize, rsize),
            ):
                if target and length:
                    self.side_hits.append(BoardListHit(row, start, start + length, source, target[0], target[1]))

        from .panels import zone_strip
        left_heading = [zone_strip(tr('盘上意象'), left_width, color=FIELD_COLORS['grammar'])]
        right_heading = [zone_strip(tr('行囊意象'), right_width, color=FIELD_COLORS['grammar'])]
        for row in range(max(len(left_heading), len(right_heading))):
            pair(left_heading[row] if row < len(left_heading) else Text(),
                 right_heading[row] if row < len(right_heading) else Text())
        pair(Text('─' * left_width, style=FIELD_COLORS['grammar']),
             Text('─' * right_width, style=FIELD_COLORS['grammar']))
        positions = {item.instance_id: index for index, (_, item) in enumerate(self.list_rows)}
        board_items = [node.value for node in scan(self.draft) if isinstance(node.value, Placement)]
        for index in range(max(len(board_items), len(self.list_rows), 1)):
            left, right, left_target, right_target = [], [], None, None
            if index < len(board_items):
                placement = board_items[index]
                left += folded(Text(self.item_name(placement.definition_id, placement.instance_id),
                                    style=CARRIED_IMAGE_STYLE), left_width)
                left += folded(Text(f'({placement.x},{placement.y}) · ' + self._status_of(compiled, placement.instance_id),
                                    style=FIELD_COLORS['rotation']), left_width)
                if self.view == 'links':
                    names = [tr(name) for name in column_names(getattr(self.draft, 'syntax', 'zh'))]
                    roles = dict.fromkeys(names[x] for x, _ in placement.cells() if 0 <= x < len(names))
                    left += folded(Text(' · '.join(roles), style=FIELD_COLORS['grammar']), left_width)
                if placement.instance_id in positions:
                    left_target = (placement.instance_id, positions[placement.instance_id])
            elif not board_items and index == 0:
                left = folded(Text(tr('（空）'), style='grey58'), left_width)
            if index < len(self.list_rows):
                _, item = self.list_rows[index]
                selected = index == self.list_cursor
                name = f"{'▶ ' if selected else ''}{index + 1}. {tr(item.name)}"
                right += folded(Text(name, style=('bold ' if selected else '') + CARRIED_IMAGE_STYLE), right_width)
                label = tr('已上盘') if self.draft.placement(item.instance_id) else tr('在行囊')
                right += folded(Text(tr('{area} 格', area=shape_area(shape_for(item.definition_id))) + ' · ' + label,
                                     style=FIELD_COLORS['rotation']), right_width)
                right_target = (item.instance_id, index)
            elif not self.list_rows and index == 0:
                right = folded(Text(tr('（无）'), style='grey58'), right_width)
            for row in range(max(len(left), len(right))):
                pair(left[row] if row < len(left) else Text(), right[row] if row < len(right) else Text(),
                     left_target if row < len(left) else None, right_target if row < len(right) else None)
            if index + 1 < max(len(board_items), len(self.list_rows)):
                pair(Text(), Text())
        return text

    def render_grid(self) -> Text:
        board = self.draft
        owners = board.cell_owners()
        ports = self._port_marks()
        preview = set(self.preview_cells()) if self.held is not None or self.tool else set()
        legal = self.preview_legal()
        text = Text(no_wrap=True)
        from ..i18n import get_language
        headings = tuple(short + ' ' for short in column_shorts(getattr(board, 'syntax', 'zh'), get_language()))
        text.append("    " + "".join(headings) + "\n", style="#a7c4c8")
        text.append("   ┌" + "─" * (board.width * CELL_COLUMNS) + "┐\n", style="grey62")
        from ..equipment.positional import compile_formation
        scope_formation = compile_formation(board, column_roles=board_roles(board))
        starts, ends = set(), set()
        for node in scope_formation.nodes:
            for relation in node.relations:
                if relation.source_row >= 0 and relation.source_row != relation.target_row:
                    starts.add(relation.source_row)
                    ends.add(relation.target_row)
        for y in range(board.height):
            mark = '↕' if y in starts and y in ends else '↘' if y in starts else '↖' if y in ends else ''
            gutter = f'{y}{mark} ' if mark else f'{y:>2} '
            text.append(gutter + '│', style="#c9a0ff" if y in starts or y in ends else "grey62")
            for x in range(board.width):
                cell = (x, y)
                owner = owners.get(cell)
                if (owner is None and cell in preview and self.held is not None
                        and self.held.kind == 'item'):
                    text.append_text(icon_cell(
                        self.held.definition_id, x-self.cursor[0], y-self.cursor[1],
                        self.rotation, emphasis='underline bold ' + ('#6fd39b' if legal else '#ff6e70')))
                    continue
                if owner is not None and owner[0] == 'item':
                    placement = board.placement(owner[1])
                    selected = owners.get(self.cursor) == owner
                    emphasis = 'underline #f3dea0' if selected else ''
                    if cell in preview:
                        emphasis = 'underline bold ' + ('#6fd39b' if legal else '#ff6e70')
                    if cell == self.cursor:
                        emphasis = 'underline bold #ffffff'
                    text.append_text(icon_cell(
                        placement.definition_id, x-placement.x, y-placement.y,
                        placement.rotation, emphasis=emphasis))
                    continue
                glyph, style = self._cell_glyph(cell, owners, ports)
                if cell in preview:
                    style = (style + " " if style else "") + (
                        STYLE_LEGAL if legal else STYLE_ILLEGAL)
                if cell == self.cursor:
                    style = (style + " " if style else "") + STYLE_CURSOR
                text.append(glyph, style=style or None)
            text.append("│\n", style="grey62")
        text.append("   └" + "─" * (board.width * CELL_COLUMNS) + "┘", style="grey62")
        return text

    def _port_marks(self) -> dict[tuple[int, int], str]:
        return {}

    def _cell_glyph(self, cell, owners, ports) -> tuple[str, str]:
        owner = owners.get(cell)
        if owner is None:
            glyph, style = "· ", "grey50"
        elif owner[0] == "trace":
            trace = next((t for t in self.draft.traces if (t.x, t.y) == cell), None)
            mark = TRACE_GLYPHS.get((trace.connector, trace.rotation), "─") \
                if trace is not None else "─"
            glyph = mark + " "
            style = "#7fb3d5"
        else:
            piece = next((p for p in self.draft.pieces
                          if (p.piece_id, p.x, p.y) == owner[1:]), None)
            letter = PIECE_GLYPHS.get(piece.piece_id if piece else "", "?")
            glyph = piece_cell_text(piece, cell, PIECE_GLYPHS) if piece else letter+' '
            style = "#c9a0ff"
        if cell in ports:
            glyph = glyph[0] + ports[cell]
        return glyph, style

    def render_side(self, width=80, *, comparison_only=False) -> Text:
        """说明区：盘面图例、根事件端、通路短状态、行囊列表。

        同时填 :attr:`side_row_map`——「输出行号 → 行囊列表位置」的命中表，
        只有「行囊中的携带意象」那几行登记，其余为 None（§8.1：盘面和列表
        两套命中表不混用）。
        """
        if comparison_only:
            return self._render_comparison(width)
        board = self.draft
        total = board.width * board.height
        compiled = self.state.equipment.compiled() \
            if board.same_layout(self.state.board) else self._preview_compiled()
        rows: list[list[tuple[str, str]]] = [[]]
        self.side_row_map = []

        def put(text: str, style: str = "") -> None:
            rows[-1].append((text, style))

        def newline() -> None:
            rows.append([])
            self.side_row_map.append(None)

        put(tr("联想盘 {used}/{total} 格", used=board.area_used(), total=total),
            "bold " + CARRIED_IMAGE_STYLE)
        newline()
        put(tr('免费预览；确认后耗一次整理行动。'), '#e5c780')
        newline()
        put(self._held_summary(), "grey78")
        newline()
        put(tr("工具 {tool}（z 切换）", tool=tool_label(self.tool)), "grey78")
        newline()
        put(tr("光标 ({x},{y}) · 旋转 {rotation}°", x=self.cursor[0], y=self.cursor[1],
               rotation=self.rotation), "grey62")
        note = self.piece_note()
        if note:
            newline()
            put(note, "bright_yellow")
        if self.message:
            newline()
            put(self.message, "#ffd166")

        newline()
        put(' | '.join(tr(label) for label in ROLE_LABELS), '#a7c4c8')
        newline()
        put(tr('逐行成句；位置与旋转改变含义，缺少行为则休眠。'), 'grey66')

        newline()
        put(tr("盘上意象："), "bold bright_cyan")
        if not board.placements:
            newline()
            put(tr("（空）"), "grey58")
        for placement in (t.value for t in scan(board) if isinstance(t.value, Placement)):
            sense = default_sense(placement.definition_id)
            # 显示规则（2026-10-10）：侧栏「盘上意象」列表不再逐件画完整图案
            # （icon_lines 每件占多行，装备一多列表就顶走行囊），改成单行
            # 「名字 · N 格 · 状态」。想看图案走盘面网格或点选后的检视浮层。
            newline()
            put(f"{self.item_name(placement.definition_id, placement.instance_id)}"
                f" {tr('{area} 格', area=shape_area(placement.shape_id))}",
                CARRIED_IMAGE_STYLE)
            put(f" {self._status_of(compiled, placement.instance_id)}",
                "grey66")
            if self.view == 'links':
                newline()
                roles = [ROLE_LABELS[x] for x, _ in placement.cells() if 0 <= x < 8]
                put('  ' + ' · '.join(dict.fromkeys(tr(role) for role in roles)), 'grey78')
            diminish = self._diminish_note(compiled, sense)
            if diminish:
                newline()
                put(f"  {diminish}", "grey58")

        for line in self._react_lines(compiled):
            newline()
            for chunk, style in line:
                put(chunk, style)

        from ..equipment.runtime import plan_action
        from ..equipment.positional import compile_formation
        preview = plan_action(compile_formation(board, column_roles=board_roles(board)), self.state, 'melee')
        if preview.valid:
            newline()
            put(tr('近战：基础 1 + 装备 {bonus} · 耗时 {time}',
                   bonus=f'{preview.damage_increment:.3f}', time=f'{preview.base_time:g}'), '#e5c780')

        newline()
        put(tr("行囊中的携带意象（, / . 选中，空格拿起）："), "bold bright_cyan")
        if not self.list_rows:
            newline()
            put(tr("（无）"), "grey58")
        for position, (_, item) in enumerate(self.list_rows):
            selected = position == self.list_cursor
            on_board = board.placement(item.instance_id) is not None
            newline()
            self.side_row_map[-1] = position
            put(f"{'▶ ' if selected else '  '}{tr(item.name)}"
                f" {tr('（{area} 格）', area=shape_area(shape_for(item.definition_id)))}"
                f" · {tr('已上盘') if on_board else tr('在行囊')}",
                ("bold " if selected else "") + CARRIED_IMAGE_STYLE
                + (" reverse" if selected else ""))

        logical_map = [None] + self.side_row_map
        self.side_row_map = []
        text = Text(no_wrap=True)
        console = Console(width=max(8, width))
        for index, segments in enumerate(rows):
            line = Text()
            for chunk, style in segments:
                line.append(chunk, style=style or None)
            for part in line.wrap(console, max(8, width), overflow='fold'):
                if self.side_row_map:
                    text.append('\n')
                text.append_text(part)
                self.side_row_map.append(logical_map[index])
        return text

    def _held_summary(self) -> str:
        if self.held is not None:
            return tr("手上：{held} · a 放下 · Esc 放回 · x 卸下",
                      held=self._held_name(self.held))
        if self.tool is not None:
            return tr("手上：{tool} · a 铺在光标格", tool=tool_label(self.tool))
        return tr("空手：a 拿起光标下的意象")

    def _preview_compiled(self):
        """草稿的语句预览：不写回 state.board，也不碰世界（§8.4 只冻结输入）。"""
        from ..equipment.grammar import compile_board

        names = {
            item.instance_id: str(item.name) for item in self.state.inventory
        }
        return compile_board(self.draft, names)

    def _diminish_note(self, compiled, sense) -> str:
        """§8.1：预览要把原效果与**递减后**的贡献一起摆出来，不能只报相加值。

        读的是草稿的 compiled，所以「挪一件上去会少多少」在确认之前就看到。
        """
        if not sense.effect:
            return ""
        sources = self.state.equipment.effect_sources(sense.effect, compiled=compiled)
        if len(sources) < 2:
            return ""
        raw = sum(value for value, _ in sources)
        after = self.state.equipment.effect_power(sense.effect, compiled=compiled)
        return tr("同效果 {n} 件：原值 {raw} → 递减后 {after}（−{loss}）",
                  n=len(sources), raw=raw, after=after, loss=max(0, raw - after))

    def _status_of(self, compiled, instance_id: str) -> str:
        for sentence in compiled.sentences:
            if instance_id in sentence.instance_ids:
                return {
                    ACTIVE: tr("生效"), DORMANT: tr("备用"), PENDING: tr("待触发"),
                    UNFORMED: tr("未成句"), SATISFIED: tr("条件未满足"),
                }.get(sentence.status, tr(sentence.status))
        return tr("未成句")

    def _react_lines(self, compiled) -> list[list[tuple[str, str]]]:
        """预览语句行：句子按生成器片段三色着色，其余说明仍是单色段。"""
        from ..equipment.events import cooldown_remaining
        from ..equipment.sentence_prose import fragments_to_text

        def segments(line: str, style: str = "grey66") -> list[tuple[str, str]]:
            return [(line, style)]

        out: list[list[tuple[str, str]]] = []
        for sentence in compiled.sentences:
            path = sentence.path
            if path is None:
                sentence_line = fragments_to_text(sentence.fragments) \
                    if sentence.fragments else Text(sentence.text)
                out.append([(sentence_line.plain[span.start:span.end],
                             str(span.style) if span.style else "grey66")
                            for span in sentence_line.spans])
                if len(sentence.source_rows) > 1:
                    row_numbers = tr('、').join(str(row + 1) for row in sentence.source_rows)
                    source_label = ("这项持续效果" if sentence.kind == "contract" else
                                    "这条反应" if sentence.kind == "reaction" else "这条语句")
                    out.append(segments('  ' + tr('{source}来自盘面第 {rows} 行',
                                    source=tr(source_label), rows=row_numbers)))
                for detail in sentence.details:
                    out.append(segments('  ' + tr('效果详情：') + tr(detail)))
                out.append(segments('  ' + tr(sentence.status)))
                if sentence.reason:
                    out.append(segments('  ' + sentence.reason))
                if sentence.kind == 'reaction':
                    out.append(segments('  ' + tr('成功反馈：想象 1 · 同类反馈冷却 6 回合')))
                continue
            spec = PIECE_SPECS[path.terminal_piece]
            from ..equipment.grammar import feedback_specs
            remaining = max((cooldown_remaining(self.state, value.piece_id) for value in feedback_specs(path)), default=0)
            tail = tr('还需 {n} 回合', n=remaining) if remaining else tr("就绪")
            if sentence.status == SATISFIED:
                tail = sentence.reason
            sentence_line = fragments_to_text(sentence.fragments) \
                if sentence.fragments else Text(sentence.text)
            out.append([(sentence_line.plain[span.start:span.end],
                         str(span.style) if span.style else "grey66")
                        for span in sentence_line.spans])
            out.append(segments('  ' + tr(spec.label) + ' · ' + tail))
            out.append(segments('  ' + sentence.cost))
        if not out:
            out.append(segments(tr('逐行成句；位置与旋转改变含义，缺少行为则休眠。')))
        return out

    def render_help(self) -> Text:
        return Text(tr('方向移动 · a拿放 · 空格取选中 · ,/.换项 · r旋转\n'
                       'x拆除 · z功能词 · v详情 · A安置 · Enter确认 · Esc放回/取消'),
                    style="grey70")


class BoardGridView(Static):
    """盘面控件：自带命中表（§8.1 要求盘面不再挤进原列表的 `_panel_rows`）。"""

    can_focus = False

    def cell_from_offset(self, offset) -> tuple[int, int] | None:
        x = (offset.x - GRID_ORIGIN_X) // CELL_COLUMNS
        y = offset.y - GRID_ORIGIN_Y
        editor = getattr(self.app, "board_editor", None)
        if editor is None:
            return None
        board = editor.draft
        if not (0 <= x < board.width and 0 <= y < board.height):
            return None
        return (x, y)

    def on_mouse_move(self, event: MouseMove) -> None:
        cell = self.cell_from_offset(event.offset)
        if cell is None:
            return
        self.app.board_editor_move_cursor(cell)
        event.stop()

    def on_mouse_down(self, event: MouseDown) -> None:
        app = self.app
        cell = self.cell_from_offset(event.offset)
        if event.button == 2:
            # 中键：先落光标再旋转（与 r 同路）。
            if cell is not None:
                app.board_editor_move_cursor(cell)
            app.board_editor_action("rotate")
            event.stop()
            return
        if event.button == 3:
            # 右键：先落光标再拆除（与 x 同路）。
            if cell is not None:
                app.board_editor_move_cursor(cell)
            app.board_editor_action("discard")
            event.stop()
            return
        if event.button != 1:
            return
        if cell is None:
            return
        app.board_editor_click(cell)
        event.stop()


class BoardSideView(Static):
    """说明区：可滚动，不与盘面争高度（§8.2）。"""

    can_focus = False

    def on_resize(self, event):
        if self.app.board_editor is not None:
            self.call_after_refresh(self.app._refresh_board_editor, self.app._symbol_mode())

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button != 1:
            return
        self.app.board_editor_click_list(event.offset.y - self.styles.gutter.top,
                                         event.offset.x - self.styles.gutter.left)
        event.stop()

    def on_mouse_scroll_up(self, event) -> None:
        self.app.board_editor_scroll(-1)
        event.stop()

    def on_mouse_scroll_down(self, event) -> None:
        self.app.board_editor_scroll(1)
        event.stop()


class BoardEditorView(Vertical):
    """Reflow the whole editor even when its scrollable child starts clipped."""
    def on_resize(self, event):
        if self.app.board_editor is not None:
            self.call_after_refresh(self.app._refresh_board_editor, self.app._symbol_mode())


class BoardToolButton(Static):
    """工具栏按钮：每个是独立控件，点哪个触发哪个（同暂停菜单的做法）。"""

    can_focus = False

    def __init__(self, action: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_action = action

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button != 1:
            return
        self.app.board_editor_action(self.board_action)
        event.stop()
