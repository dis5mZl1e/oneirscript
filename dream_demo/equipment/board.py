"""8×6 联想盘：占格、合法性、握持焦点、装箱迁移（§4、§9）。

盘面是逻辑格，不是终端字符列。装备、线材、插片的实体占格两两不相交，
所有占格都在边框内；旋转按完整形状验证，不只按面积验证。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from copy import deepcopy
from typing import Iterable, Sequence

from .item_shapes import shape_for
from .function_words import FUNCTION_WORDS
from .shapes import (
    DELTAS,
    OPPOSITE,
    ROTATIONS,
    SHAPE_VERSION,
    occupied_cells,
    port_anchors,
    rotate_direction,
    shape_area,
)

BOARD_WIDTH = 8
BOARD_HEIGHT = 6
BOARD_SCHEMA_VERSION = 3


def _default_board_syntax() -> str:
    """新盘面的默认语序：机器偏好（设置项），不是世界规则。"""
    from .syntax import default_syntax
    return default_syntax()


# 盘面外的四个固定事件接入端（§5.2）。它们不是装备槽，不占盘面面积。
# 记法：(事件 id, 标签, 所在盘内格, 该格上被占用的边方向)
ROOT_ENDPOINTS: tuple[tuple[str, str, tuple[int, int], str], ...] = (
    ("hit", "命中端", (1, 0), "N"),
    ("hurt", "受击端", (0, 2), "W"),
    ("touch", "接触端", (6, 5), "S"),
    ("conceive", "构想端", (7, 3), "E"),
)


@dataclass
class Placement:
    """盘上一件装备实例（所有权仍在行囊，这里只记位置与词义选择）。"""

    instance_id: str
    definition_id: str
    shape_id: str
    x: int
    y: int
    rotation: int = 0
    shape_version: int = SHAPE_VERSION
    # 语法核心版 §4.2：一个节点同一时刻只有一个选定词义。
    sense_id: str = ""
    # 是否已「写出原意」（持有句／行动句）。未成句的词块仍占地但不生效。
    sentence_written: bool = True
    spare: bool = False

    @property
    def area(self) -> int:
        return shape_area(self.shape_id)

    def cells(self) -> tuple[tuple[int, int], ...]:
        return occupied_cells(self.shape_id, self.rotation, self.x, self.y)

    def anchors(self):
        return port_anchors(self.shape_id, self.rotation, self.x, self.y)


@dataclass
class Trace:
    """接梦线：占一格，直线或转角，只允许两个端口。"""

    x: int
    y: int
    connector: str = "straight"  # straight | corner
    rotation: int = 0

    def cells(self) -> tuple[tuple[int, int], ...]:
        return ((self.x, self.y),)

    def directions(self) -> tuple[str, str]:
        base = ("W", "E") if self.connector == "straight" else ("W", "S")
        return tuple(rotate_direction(d, self.rotation) for d in base)  # type: ignore[return-value]


# 反馈插片的落点档位（§5.5）：编辑器 p 键轮换。`visible_enemy` 是「事件格附近
# 2 格内一个当前可见敌人」，只有线路上带「照」语义才解锁——执行层缺语义时直接
# 拒发，不会退回事件格，免得玩家以为打的是敌人而实际烧了别格。
DESTINATION_POLICIES: tuple[str, ...] = (
    "event_cell", "player_cell", "previous_cell", "visible_enemy",
)
DESTINATION_LABELS: dict[str, str] = {
    "event_cell": "事件格",
    "player_cell": "玩家格",
    "previous_cell": "上一移动格",
    "visible_enemy": "近处可见敌人",
}
# 移涌片的优先方向（§5.5「目的格只能在其相邻四格中选择；优先方向在编辑器设置」）。
# 这张表同时是执行层的探测顺序，编辑器和结算不许各排一次。
PRIORITY_DIRECTIONS: tuple[str, ...] = ("北", "东", "南", "西")
PRIORITY_VECTORS: tuple[tuple[int, int], ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


@dataclass
class Piece:
    """通用插片（§5.4）。第一版：湿润门、缓冲片、移涌片、电吻片。"""

    piece_id: str
    x: int
    y: int
    rotation: int = 0
    destination_policy: str = "event_cell"  # 见 DESTINATION_POLICIES
    priority: int = 0  # 移涌片优先方向：PRIORITY_DIRECTIONS 的下标

    def cells(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (self.x + dx, self.y + dy) for dx, dy in PIECE_SPECS[self.piece_id].cells
        ) if self.rotation == 0 else tuple(
            (self.x + dx, self.y + dy)
            for dx, dy in _rotate_offsets(PIECE_SPECS[self.piece_id].cells, self.rotation)
        )


@dataclass(frozen=True)
class PieceSpec:
    piece_id: str
    label: str
    cells: tuple[tuple[int, int], ...]
    in_port: tuple[tuple[int, int], str]
    requires: str | None  # 需要的语义
    feedback: bool  # 是否产生世界／护持反馈（占全盘反馈预算）
    cost: int = 1  # 想象力
    cooldown: int = 6
    capacity: int = 1  # 可存量（缓冲点数／保留事件数）
    detail: str = ""
    # 留声片：脉冲走到这里不立刻结算，先存起来，delay 个客观回合后再往下游走；
    # 超过 expire 回合仍未释放就作废。同一插片最多留一个，后来的事件不覆盖。
    delay: int = 0
    expire: int = 0
    # 分流片：一入两出。为 None 时用「入端方向 + 其反向」的普通双向导体规则；
    # 列出显式端口时按列表顺序登记，顺序同时就是资源不足时的优先次序，
    # 编辑器预览与执行读同一份表，不允许两边各排一次。
    ports: tuple[tuple[tuple[int, int], str, str], ...] | None = None
    endpoint: str | None = None


def _rotate_offsets(cells: Sequence[tuple[int, int]], rotation: int) -> tuple[tuple[int, int], ...]:
    points = list(cells)
    for _ in range((rotation // 90) % 4):
        max_y = max(y for _, y in points)
        points = [(max_y - y, x) for x, y in points]
    min_x = min(x for x, _ in points)
    min_y = min(y for _, y in points)
    return tuple(sorted((x - min_x, y - min_y) for x, y in points))


def _rotate_port(port: tuple[tuple[int, int], str], cells: Sequence[tuple[int, int]], rotation: int):
    (px, py), direction = port
    points = [(px, py), *cells]
    shifted = list(points)
    for _ in range((rotation // 90) % 4):
        max_y = max(y for _, y in shifted)
        shifted = [(max_y - y, x) for x, y in shifted]
    min_x = min(x for x, _ in shifted[1:])
    min_y = min(y for _, y in shifted[1:])
    return ((shifted[0][0] - min_x, shifted[0][1] - min_y), rotate_direction(direction, rotation))


PIECE_SPECS: dict[str, PieceSpec] = {
    "wet_gate": PieceSpec(
        "wet_gate", "湿润门", ((0, 0),), ((0, 0), "W"), None, False,
        detail="目标或触发位置有可导电液体时，这条联想才会生效。",
    ),
    "buffer": PieceSpec(
        "buffer", "缓冲片", ((0, 0), (0, 1)), ((0, 0), "N"), "护", True,
        detail="下一次对应创伤减少 1，最多存 1 点，最多保持 3 回合。",
    ),
    "surge": PieceSpec(
        "surge", "移涌片", ((0, 0), (0, 1)), ((0, 0), "N"), "湿", True,
        detail="从触发位置现有的液体中，最多移动 5 单位到有容量的相邻位置。",
    ),
    "spark": PieceSpec(
        "spark", "电吻片", ((0, 0), (0, 1)), ((0, 0), "N"), "电", True,
        detail="对一个被液体浸湿的敌人造成 1 点完整度损伤。",
    ),
    "blank_gate": PieceSpec(
        "blank_gate", "留白门", ((0, 0),), ((0, 0), "W"), None, False,
        detail="只有想象力不高于线路上留白装备的原阈值才通过；无对应装备时取系统阈值 10。",
    ),
    # I2=##：横放两格、真正的穿线继电器——入端在左格西侧，出端在右格东侧。
    # 两格都是导体自身，不能用「入端＋反向往同一格」的默认导体规则，否则出端
    # 会指回插片自己的另一格，脉冲走到这里就断路，留声片到期也接不下去。
    "echo_cell": PieceSpec(
        "echo_cell", "留声片", ((0, 0), (1, 0)), ((0, 0), "W"), "拍", False,
        cost=0, cooldown=0, capacity=1, delay=2, expire=4,
        ports=(((0, 0), "W", "in"), ((1, 0), "E", "out")),
        detail="需要拍语义：保存一个事件，2 个客观回合后释放；只留一个，后来事件不覆盖；4 回合内过期。",
    ),
    # D2=#/#：竖放两格，端口都在上格（与缓冲／移涌／电吻同一口径，下格只是占地）。
    # 一支东出（优先）、一支西出：真正的 T 形一分二。表内顺序即优先次序，
    # 编辑器预览与执行读同一份，不允许两边各排一次。
    "splitter": PieceSpec(
        "splitter", "分流片", ((0, 0), (0, 1)), ((0, 0), "N"), None, False,
        cost=0, cooldown=0,
        ports=(((0, 0), "N", "in"), ((0, 0), "E", "out"), ((0, 0), "W", "out")),
        detail="一入两出：两支共用原预算与总资源；不足时按预览中的优先次序选一支。",
    ),
    "ember": PieceSpec(
        "ember", "余温片", ((0, 0), (0, 1)), ((0, 0), "N"), "热", True,
        detail="在有可燃材料的位置引发一次点燃；初始火焰强度不超过 1，后续燃烧按原有规则进行。",
    ),
    "voice": PieceSpec(
        "voice", "传声片", ((0, 0), (0, 1)), ((0, 0), "N"), "声", True,
        detail="在事件格／上一位置产生半径不超过 2 的一次声源，复用既有引诱规则；不硬控、不伤害。",
    ),
}


# 标点沿用既有反馈数值，旧 id 可继续读档；朝向不参与语句求值。
_PUNCTUATION = {
    'wet_gate': ('冒号·湿润', '只有触发位置能够导电，这一分句的联想才会发生。'),
    'blank_gate': ('问号·留白', '想象力不高于留白意象的阈值时才联想；没有阈值意象时取 10。'),
    'buffer': ('括号·护持', '借助护的意象，护住下一次创伤：少受 1 点，保留 3 回合。'),
    'surge': ('破折号·移涌', '借助湿的意象，把触发格中最多 5 单位导电液体移向有容量的相邻位置。'),
    'spark': ('感叹号·放电', '借助电的意象，向触发位置附近的湿润敌人放出 1 点微弱电击。'),
    'ember': ('着重号·余温', '借助热的意象，点燃一个可燃位置；初始火焰强度为 1。'),
    'voice': ('引号·轻声', '借助声的意象，在落点响起半径 2 的轻声，吸引附近意识。'),
    'echo_cell': ('省略号·回响', '借助拍的意象，让这一分句的联想延后 2 回合；最多留一件事，4 回合后失效。'),
    'splitter': ('顿号·并列', '让同一事件并列多个联想，按阅读顺序尝试；没有顿号时只采用第一个。共用消耗与冷却。'),
}
for _identifier, (_label, _detail) in _PUNCTUATION.items():
    PIECE_SPECS[_identifier] = replace(PIECE_SPECS[_identifier], label=_label, detail=_detail)
PIECE_SPECS['period'] = PieceSpec(
    'period', '句号·断句', ((0, 0),), ((0, 0), 'W'), None, False,
    cost=0, cooldown=0, detail='结束这一分句。后面的词与条件从头读，不借用前面的意象。')
for _endpoint, _label in (('hit', '命中'), ('hurt', '受击'), ('touch', '接触'), ('conceive', '构想')):
    _identifier = _endpoint + '_clause'
    PIECE_SPECS[_identifier] = PieceSpec(
        _identifier, '冒号·' + _label, ((0, 0),), ((0, 0), 'W'), None, False,
        cost=0, cooldown=0, endpoint=_endpoint,
        detail={'hit': '后面的联想在你命中目标时尝试。',
                'hurt': '后面的联想在你受到实际创伤时尝试。',
                'touch': '后面的联想在你进入液体或气体时尝试。',
                'conceive': '后面的联想在你成功施放构想时尝试。'}[_endpoint])


def piece_cells(piece: Piece) -> tuple[tuple[int, int], ...]:
    spec = PIECE_SPECS[piece.piece_id]
    offsets = _rotate_offsets(spec.cells, piece.rotation)
    return tuple((piece.x + dx, piece.y + dy) for dx, dy in offsets)


def piece_in_port(piece: Piece) -> tuple[tuple[int, int], str]:
    spec = PIECE_SPECS[piece.piece_id]
    (dx, dy), direction = _rotate_port(spec.in_port, spec.cells, piece.rotation)
    return ((piece.x + dx, piece.y + dy), direction)


def piece_ports(piece: Piece) -> tuple[tuple[tuple[int, int], str, str], ...]:
    """插片的完整端口表（格、方向、角色），已按旋转落到盘内坐标。

    显式端口表（分流片）优先；否则沿用旧规则——反馈插片只有入端（终点），
    门与线材是入端方向及其反向的双向导体。列表顺序即优先次序。
    """
    if piece.piece_id in FUNCTION_WORDS:
        return ()  # Function words are syntax nodes, never circuit relays.
    spec = PIECE_SPECS[piece.piece_id]
    if spec.ports:
        out: list[tuple[tuple[int, int], str, str]] = []
        for (dx, dy), direction, role in spec.ports:
            (ox, oy), od = _rotate_port(((dx, dy), direction), spec.cells, piece.rotation)
            out.append(((piece.x + ox, piece.y + oy), od, role))
        return tuple(out)
    cell, direction = piece_in_port(piece)
    if spec.feedback:
        return ((cell, direction, "in"),)
    return ((cell, direction, "both"), (cell, OPPOSITE[direction], "both"))


for _word_id, _word_label in (("use_word", "使用"), ("cover_word", "披覆"), ("maintain_word", "维持")):
    PIECE_SPECS[_word_id] = PieceSpec(
        _word_id, _word_label, ((0, 0),), ((0, 0), "W"), None, False,
        cost=0, cooldown=0, detail="放在“行为”列，并搭配能执行这项动作的意象；单独放置不会生效。",
    )

for _word in FUNCTION_WORDS.values():
    PIECE_SPECS[_word.word_id] = PieceSpec(
        _word.word_id, _word.label, _word.cells, ((0, 0), "W"), None, False,
        cost=0, cooldown=0, detail=_word.detail,
    )

NodeKey = tuple  # ("item", instance_id) | ("trace", x, y) | ("piece", piece_id, x, y)


@dataclass
class EquipmentBoard:
    schema_version: int = BOARD_SCHEMA_VERSION
    width: int = BOARD_WIDTH
    height: int = BOARD_HEIGHT
    placements: list[Placement] = field(default_factory=list)
    traces: list[Trace] = field(default_factory=list)
    pieces: list[Piece] = field(default_factory=list)
    focus_instance_id: str | None = None
    legacy_snapshot: dict = field(default_factory=dict)
    # Declared language syntax for this board; the default follows the machine
    # preference (Settings → 装备句法) for **new** boards only. A board restored
    # from a save keeps its own value, so changing the preference never
    # reinterprets an existing build (§14.13 item 5).
    syntax: str = field(default_factory=_default_board_syntax)

    # ---- 基本查询 ----

    def placement(self, instance_id: str | None) -> Placement | None:
        if not instance_id:
            return None
        return next((p for p in self.placements if p.instance_id == instance_id), None)

    def placed_instance_ids(self) -> set[str]:
        return {p.instance_id for p in self.placements}

    def focus(self) -> Placement | None:
        return self.placement(self.focus_instance_id)

    def cell_owners(self) -> dict[tuple[int, int], NodeKey]:
        owners: dict[tuple[int, int], NodeKey] = {}
        for placement in self.placements:
            if placement.rotation not in ROTATIONS:
                continue  # 旋转非法的摆放不拥有任何格；由 errors() 报原因
            for cell in placement.cells():
                owners[cell] = ("item", placement.instance_id)
        for trace in self.traces:
            owners[(trace.x, trace.y)] = ("trace", trace.x, trace.y)
        for piece in self.pieces:
            for cell in piece_cells(piece):
                owners[cell] = ("piece", piece.piece_id, piece.x, piece.y)
        return owners

    def area_used(self) -> int:
        return (
            sum(p.area for p in self.placements)
            + len(self.traces)
            + sum(len(PIECE_SPECS[p.piece_id].cells) for p in self.pieces)
        )

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    # ---- 合法性 ----

    def in_bounds(self, cells: Iterable[tuple[int, int]]) -> bool:
        return all(self.inside(x, y) for x, y in cells)

    def is_free(self, cells: Iterable[tuple[int, int]], owners: dict | None = None) -> bool:
        owners = self.cell_owners() if owners is None else owners
        return all(cell not in owners for cell in cells)

    def can_place_item(self, definition_id: str, shape_id: str, x: int, y: int, rotation: int,
                       owners: dict | None = None) -> bool:
        if rotation not in ROTATIONS:
            return False
        cells = occupied_cells(shape_id, rotation, x, y)
        return self.in_bounds(cells) and self.is_free(cells, owners)

    def errors(self, allowed_instances: set[str] | None = None,
               equipment_ids: set[str] | None = None) -> list[str]:
        """整盘校验（§9.2 第 2 步）。返回可读原因列表，空列表表示合法。"""
        problems: list[str] = []
        if (self.width, self.height) != (BOARD_WIDTH, BOARD_HEIGHT):
            problems.append("联想盘边框必须是 8×6 格")
        seen: set[tuple[int, int]] = set()
        instance_ids: list[str] = []
        for placement in self.placements:
            if placement.rotation not in ROTATIONS:
                problems.append(f"{placement.definition_id} 旋转非法（只支持四向）")
                continue
            cells = placement.cells()
            if len(set(cells)) != shape_area(placement.shape_id):
                problems.append(f"{placement.definition_id} 占格与形状面积不符")
            if not self.in_bounds(cells):
                problems.append(f"{placement.definition_id} 越过盘面边框")
            if placement.instance_id in instance_ids:
                problems.append(f"实例 {placement.instance_id} 被摆放两次")
            instance_ids.append(placement.instance_id)
            if allowed_instances is not None and placement.instance_id not in allowed_instances:
                problems.append(f"{placement.definition_id} 不属于行囊中的所有物")
            if equipment_ids is not None and placement.definition_id not in equipment_ids:
                problems.append(f"{placement.definition_id} 不是可上盘的携带意象")
            if shape_for(placement.definition_id) != placement.shape_id:
                problems.append(f"{placement.definition_id} 的形状与目录不符")
            for cell in cells:
                if cell in seen:
                    problems.append(f"格 {cell} 上有重叠实体")
                seen.add(cell)
        for trace in self.traces:
            cell = (trace.x, trace.y)
            if not self.inside(*cell):
                problems.append(f"接梦线 {cell} 越过盘面边框")
            if trace.connector not in ("straight", "corner"):
                problems.append(f"接梦线 {cell} 形状非法")
            elif trace.rotation not in ROTATIONS:
                problems.append(f"接梦线 {cell} 旋转非法")
            if cell in seen:
                problems.append(f"格 {cell} 上有重叠实体")
            seen.add(cell)
        seen_words: set[str] = set()
        for piece in self.pieces:
            if piece.piece_id not in PIECE_SPECS:
                problems.append(f"未知插片 {piece.piece_id}")
                continue
            if piece.piece_id in FUNCTION_WORDS:
                label = FUNCTION_WORDS[piece.piece_id].label
                if piece.piece_id in seen_words:
                    problems.append(f"功能词 {label} 在全盘重复")
                seen_words.add(piece.piece_id)
                if piece.rotation != 0:
                    problems.append(f"功能词 {label} 只能保持横向，不可旋转")
            if piece.rotation not in ROTATIONS:
                problems.append(f"{PIECE_SPECS[piece.piece_id].label} 旋转非法")
            if piece.destination_policy not in DESTINATION_POLICIES:
                problems.append(f"{PIECE_SPECS[piece.piece_id].label} 落点非法")
            if type(piece.priority) is not int or not 0 <= piece.priority < len(PRIORITY_DIRECTIONS):
                problems.append(f"{PIECE_SPECS[piece.piece_id].label} 优先方向非法")
            cells = piece_cells(piece)
            if not self.in_bounds(cells):
                problems.append(f"{PIECE_SPECS[piece.piece_id].label} 越过盘面边框")
            for cell in cells:
                if cell in seen:
                    problems.append(f"格 {cell} 上有重叠实体")
                seen.add(cell)
        if self.schema_version < 3 and self.focus_instance_id and self.focus_instance_id not in instance_ids:
            problems.append("握持焦点指向盘外或缺失的实例")
        return problems

    # ---- 事务草稿 ----

    def clone(self) -> "EquipmentBoard":
        return EquipmentBoard(
            schema_version=self.schema_version,
            width=self.width,
            height=self.height,
            placements=[replace(p) for p in self.placements],
            traces=[replace(t) for t in self.traces],
            pieces=[replace(p) for p in self.pieces],
            focus_instance_id=self.focus_instance_id,
            legacy_snapshot=deepcopy(self.legacy_snapshot),
            syntax=self.syntax,
        )

    def same_layout(self, other: "EquipmentBoard") -> bool:
        def canonical(board):
            data = board.to_dict()
            for field in ('placements', 'traces', 'pieces'):
                data[field] = sorted(data[field], key=lambda entry: (entry['y'], entry['x'], repr(entry)))
            return data
        return canonical(self) == canonical(other)

    def place_item(self, placement: Placement) -> None:
        self.placements.append(placement)

    def remove_item(self, instance_id: str) -> Placement | None:
        placement = self.placement(instance_id)
        if placement is None:
            return None
        self.placements.remove(placement)
        if self.focus_instance_id == instance_id:
            self.focus_instance_id = None
        return placement

    def clear(self) -> None:
        self.placements.clear()
        self.traces.clear()
        self.pieces.clear()
        self.focus_instance_id = None

    # ---- 存档 ----

    def to_dict(self) -> dict:
        data = {
            "schema_version": self.schema_version,
            "width": self.width,
            "height": self.height,
            "placements": [
                {
                    "instance_id": p.instance_id,
                    "definition_id": p.definition_id,
                    "shape_id": p.shape_id,
                    "shape_version": p.shape_version,
                    "x": p.x,
                    "y": p.y,
                    "rotation": p.rotation,
                    "sense_id": p.sense_id,
                    "sentence_written": p.sentence_written,
                }
                for p in self.placements
            ],
            "traces": [
                {"x": t.x, "y": t.y, "connector": t.connector, "rotation": t.rotation}
                for t in self.traces
            ],
            "pieces": [
                {
                    "piece_id": p.piece_id,
                    "x": p.x,
                    "y": p.y,
                    "rotation": p.rotation,
                    "destination_policy": p.destination_policy,
                    "priority": p.priority,
                }
                for p in self.pieces
            ],
            "focus_instance_id": self.focus_instance_id,
            "syntax": self.syntax,
        }
        if self.schema_version >= 3:
            data.pop("focus_instance_id")
            for entry in data["placements"]:
                entry.pop("sense_id")
                entry.pop("sentence_written")
            if self.legacy_snapshot:
                data["legacy_snapshot"] = deepcopy(self.legacy_snapshot)
        return data

    @classmethod
    def from_dict(cls, data: dict | None) -> "EquipmentBoard":
        data = data or {}
        raw_version = int(data.get('schema_version', 1))
        legacy = raw_version < 2
        board = cls(
            schema_version=max(BOARD_SCHEMA_VERSION, int(data.get("schema_version", BOARD_SCHEMA_VERSION))),
            width=int(data.get("width", BOARD_WIDTH)),
            height=int(data.get("height", BOARD_HEIGHT)),
            focus_instance_id=None,
            legacy_snapshot=deepcopy(data if raw_version < 3 else data.get("legacy_snapshot") or {}),
            syntax=str(data.get("syntax") or "zh"),
        )
        board.placements = [
            Placement(
                instance_id=str(entry["instance_id"]),
                definition_id=str(entry["definition_id"]),
                shape_id=str(entry.get("shape_id") or shape_for(entry["definition_id"])),
                x=int(entry["x"]),
                y=int(entry["y"]),
                rotation=int(entry.get("rotation", 0)) % 360,
                shape_version=int(entry.get("shape_version", SHAPE_VERSION)),
                sense_id=str(entry.get("sense_id", "")),
                sentence_written=bool(entry.get("sentence_written", True)),
            )
            for entry in data.get("placements", [])
        ]
        board.traces = [
            Trace(int(t["x"]), int(t["y"]), 'straight' if legacy else str(t.get("connector", "straight")),
                  int(t.get("rotation", 0)) % 360)
            for t in data.get("traces", [])
        ]
        board.pieces = [
            Piece(str(p["piece_id"]), int(p["x"]), int(p["y"]), int(p.get("rotation", 0)) % 360,
                  str(p.get("destination_policy", "event_cell")), int(p.get("priority", 0)))
            for p in data.get("pieces", [])
        ]
        if raw_version < 3:
            board.traces = []
            board.pieces = [p for p in board.pieces if p.piece_id in ("use_word", "cover_word", "maintain_word")]
        for placement in board.placements:
            placement.sense_id = ""
            placement.sentence_written = True
        return board

    # ---- 自动安置（只找合法位置，不移动旧件） ----

    def auto_place(self, definition_id: str, instance_id: str, shape_id: str | None = None,
                   sense_id: str = "") -> Placement | None:
        shape_id = shape_id or shape_for(definition_id)
        owners = self.cell_owners()
        for rotation in ROTATIONS:
            for y in range(self.height):
                for x in range(self.width):
                    if self.can_place_item(definition_id, shape_id, x, y, rotation, owners):
                        placement = Placement(
                            instance_id=instance_id, definition_id=definition_id,
                            shape_id=shape_id, x=x, y=y, rotation=rotation, sense_id=sense_id,
                        )
                        self.placements.append(placement)
                        return placement
        return None

    def pack(self, entries: Sequence[tuple[str, str]], attempt_cap: int = 400_000) -> bool:
        """把 [(instance_id, definition_id), ...] 全部放进空盘。

        枚举旋转并回溯，不贪心塞入前几个（§9.3）。占位用 48 位掩码表示，
        避免迁移在读档时卡顿；`attempt_cap` 是防递归／防挂死的上限，
        触顶即视为放不下——调用方据此**中止**迁移，不静默卸下或丢弃。
        成功返回 True，失败时恢复空盘并返回 False。
        """
        self.placements.clear()
        self.focus_instance_id = None
        ordered = sorted(entries, key=lambda entry: -shape_area(shape_for(entry[1])))
        variants: list[tuple[str, str, tuple[int, ...]]] = []
        for instance_id, definition_id in ordered:
            shape_id = shape_for(definition_id)
            masks = []
            for rotation in ROTATIONS:
                base = occupied_cells(shape_id, rotation, 0, 0)
                span_x = max(x for x, _ in base)
                span_y = max(y for _, y in base)
                for y in range(self.height - span_y):
                    for x in range(self.width - span_x):
                        mask = 0
                        for cx, cy in base:
                            mask |= 1 << ((y + cy) * self.width + (x + cx))
                        masks.append((mask, x, y, rotation))
            # 同一形状旋转后可能重复（正方形/对称形），去重减少回溯分支。
            unique: dict[int, tuple[int, int, int, int]] = {}
            for mask, x, y, rotation in masks:
                unique.setdefault(mask, (mask, x, y, rotation))
            variants.append((instance_id, definition_id, tuple(unique.values())))

        attempts = 0
        found: list[Placement] = []

        def backtrack(index: int, used: int) -> bool:
            nonlocal attempts
            if index == len(variants):
                return True
            instance_id, definition_id, options = variants[index]
            for mask, x, y, rotation in options:
                attempts += 1
                if attempts > attempt_cap or used & mask:
                    continue
                found.append(Placement(
                    instance_id=instance_id, definition_id=definition_id,
                    shape_id=shape_for(definition_id), x=x, y=y, rotation=rotation,
                ))
                if backtrack(index + 1, used | mask):
                    return True
                found.pop()
            return False

        if backtrack(0, 0):
            self.placements = found
            return True
        self.placements.clear()
        return False


def neighbour(cell: tuple[int, int], direction: str) -> tuple[int, int]:
    dx, dy = DELTAS[direction]
    return (cell[0] + dx, cell[1] + dy)


def facing(cell: tuple[int, int], direction: str) -> tuple[tuple[int, int], str]:
    """某格某方向的边上，对面那一格与它回指的方向。"""
    return neighbour(cell, direction), OPPOSITE[direction]
