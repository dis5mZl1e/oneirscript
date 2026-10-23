"""vault 基础设施：模板数据类、盖章与放置尝试。

vault 图案字符：

- ``#`` = 实心位（墙）。**固定**模板照常由常规墙体分配决定（或整栋由
  ``base_kind`` 指定墙种）；**不定**模板在盖章时从常见墙体池整栋抽一种，
  见 ``materials.common``。
- ``.`` = 开放位（不动原地地形，只保证这里是空的）。
- ``s`` = 固体位（实心）。不定模板从常见固体池抽一种；固定模板请改用写死的
  ``S``/``T``。
- ``~`` = 液体位（**开放**格，但灌入液态记忆）。不定模板从常见液体池抽一种。
- 空格 = 不关心（保留原地地形）。
- 写死的墙种字符（优先级高于 ``#`` 的整栋材料，用于「部分写死」）：
  ``S`` = 石台、``T`` = 木桌子、``G`` = 玻璃幕墙、``A`` = 吸声聚合墙、
  ``C`` = 冷凝囊壁、``F`` = 不稳定燃料墙。

两个**必有**分类轴（每个模板都同时具备，各自二选一、无第三项，故只有四种组合）：

- ``phase``：``PRE`` 前置 / ``POST`` 后置。
  前置在层型生成器跑完基础掩码后、连接/braid 之前盖章，保留区阻止普通生成器
  覆盖其形状——一般较大、有功能或形状复杂。后置在掩码完成（含连接/braid）之后、
  液体/气体/容器/生物放置之前尝试盖章；需满足地形条件（开阔/实心比例），不满足
  即失败，一般较小、点缀性质。
- ``material``：``FIXED`` 固定 / ``VARIABLE`` 不定。
  固定 = 地形组成材料全部写死；不定 = 可被替换为常见材料（允许部分写死）。

附加属性（可叠加的修饰，不属于上面两条分类）：
``decor``（房间装饰池）、``forms``（层型专属池）、``loot``（中央石台盛放稀有物品）、
``min_open`` / ``min_solid``（后置的地形门槛）、``base_kind``（整栋统一墙种，
仅固定模板可用）。

模板数据存放在同目录的四个 JSON 里（按两条分类的组合分文件），由 ``loader``
读取与校验；字段表与目录约定见 ``loader`` 的模块文档。
"""

from __future__ import annotations

import random

from ...materials import COMMON_LIQUIDS, COMMON_SOLIDS, COMMON_WALLS

# ---- 分类轴一：前置 / 后置 ----
PRE = "pre"
POST = "post"
PHASES: tuple[str, ...] = (PRE, POST)

# ---- 分类轴二：固定 / 不定 ----
FIXED = "fixed"
VARIABLE = "variable"
MATERIAL_MODES: tuple[str, ...] = (FIXED, VARIABLE)

# ---- 稀有度（所有模板必备属性之一）----
# 常见 > 少见 > 稀有 > 非常稀有；选择模板时按权重加权抽取。
RARITY_COMMON = "常见"
RARITY_UNCOMMON = "少见"
RARITY_RARE = "稀有"
RARITY_VERY_RARE = "非常稀有"
RARITIES: tuple[str, ...] = (RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_VERY_RARE)
#: 抽取权重：常见的模板约是「非常稀有」的 20 倍常见。
RARITY_WEIGHTS: dict[str, int] = {
    RARITY_COMMON: 100,
    RARITY_UNCOMMON: 40,
    RARITY_RARE: 15,
    RARITY_VERY_RARE: 5,
}

# 扩展图案字符 → 墙种。所有扩展字符都按实心墙参与掩码与连通，
# 墙种在 core._assign_wall_kinds 里覆写（门优先级更高）。
VAULT_CHAR_KINDS: dict[str, str] = {
    "S": "石台",
    "T": "木桌子",
    "G": "玻璃幕墙",
    "A": "吸声聚合墙",
    "C": "冷凝囊壁",
    "F": "不稳定燃料墙",
    # 逻辑固体（内容扩展包 v1）：触发源与接收器。
    "X": "陷阱石台",
    "M": "机关石台",
    "R": "感应符文墙",
    "O": "定时摆轮",
    "D": "机关门",
    "B": "显影方尖",
    "K": "囚笼栅栏",
    "J": "弹射座",
    "V": "灌注阀",
    "L": "共鸣报警器",
    "N": "导电铜网墙",
    # 电路逻辑 v2：门类节点
    "U": "合辙枢",
    "I": "分流枢",
    "Y": "接线枢",
}

# 占位字符（各自由「位置规则」定义，材料在盖章时才定）。
WIRE_CHAR = "w"    # 电线位：开放格 + 铺线（电线可穿墙，也可以用 w 显式走线）
PRESSURE_CHAR = "p"  # 压力地板位：开放格 + 地板变体「压力地板」（触发源）
SOLID_CHAR = "#"   # 实心位：不定 → 从常见墙体池抽；固定 → 常规分配 / base_kind
OPEN_CHAR = "."    # 开放位
BLANK_CHAR = " "   # 不关心
COMMON_SOLID_CHAR = "s"  # 固体位：不定 → 从常见固体池抽
LIQUID_CHAR = "~"  # 液体位：开放 + 灌入常见液体池抽到的一种
# 连通符号：本身是开放格，仅提醒生成器「这个位置需要与外界联通」——
# 盖章收尾时若锚点不在主连通块，就从锚点凿一条到主块的通道（避开其他
# 模板的保护区，可以在本模板自己的墙凿门）；若周围本来就是空地则不处理。
CONNECT_CHAR = "@"

VAULT_CHAR_KINDS_INVERTED = {kind: ch for ch, kind in VAULT_CHAR_KINDS.items()}

ALL_PATTERN_CHARS = frozenset(
    (SOLID_CHAR, OPEN_CHAR, BLANK_CHAR, COMMON_SOLID_CHAR, LIQUID_CHAR, CONNECT_CHAR,
     WIRE_CHAR, PRESSURE_CHAR, *VAULT_CHAR_KINDS)
)


def _pick(rng: random.Random | None, pool: tuple[str, ...], seed_text: str) -> str:
    """从池子里抽一种材料；``rng`` 为空时用可复现的字符串种子兜底。"""
    if not pool:
        return ""
    return (rng or random.Random(seed_text)).choice(pool)


class VaultPlacement:
    """一次成功盖章的记录：模板 + 左上角位置 + 本次抽中的材料。

    不定模板的材料在**盖章那一刻**定下来（整栋统一一种），并记在这里——
    同一份模板对象会在不同层被反复盖章，材料绝不能写在模板上，否则二层会
    跟着一层一起变。
    """

    def __init__(
        self,
        vault: "Vault",
        left: int,
        top: int,
        material_kind: str = "",
        solid_kind: str = "",
        liquid_kind: str = "",
    ):
        self.vault = vault
        self.left = left
        self.top = top
        # 本次盖章为不定模板抽中的材料（固定模板为空串）。
        self.material_kind = material_kind
        self.solid_kind = solid_kind
        self.liquid_kind = liquid_kind

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"VaultPlacement({self.vault.vid!r}, {self.left}, {self.top}, "
            f"material={self.material_kind!r}, solid={self.solid_kind!r}, "
            f"liquid={self.liquid_kind!r})"
        )

    @property
    def region(self) -> tuple[int, int, int, int]:
        """盖章区域（含边界的格子矩形，left/top/right/bottom）——「保护罩」。"""
        return (
            self.left,
            self.top,
            self.left + self.vault.width - 1,
            self.top + self.vault.height - 1,
        )

    @property
    def center(self) -> tuple[int, int]:
        """结构几何中心（事件台等附属内容的落点）。"""
        return (self.left + self.vault.width // 2, self.top + self.vault.height // 2)

    @property
    def loot_cell(self) -> tuple[int, int] | None:
        """战利品台面（模板中央格，旋转后跟随锚点）；vault.loot 为 False 返回 None。"""
        if not self.vault.loot:
            return None
        row, col = self.vault.loot_anchor or (self.vault.height // 2, self.vault.width // 2)
        return (self.left + col, self.top + row)

    def anchor_cells(self) -> list[tuple[int, int]]:
        """连通符号（@）的绝对坐标：生成收尾时保证它们与外界联通。"""
        return [
            (self.left + col, self.top + row)
            for row, col in self.vault.anchor_positions()
        ]

    def pattern_char(self, row: int, col: int) -> str:
        row_text = self.vault.pattern[row]
        return row_text[col] if col < len(row_text) else BLANK_CHAR

    def kind_overrides(self) -> dict[tuple[int, int], str]:
        """该盖章区域内「指定墙种」的格子 → 墙种映射。"""
        overrides: dict[tuple[int, int], str] = {}
        for row in range(self.vault.height):
            for col in range(self.vault.width):
                ch = self.pattern_char(row, col)
                kind = VAULT_CHAR_KINDS.get(ch)
                if kind is None and ch == COMMON_SOLID_CHAR:
                    kind = self.solid_kind
                if kind is None and ch == SOLID_CHAR:
                    # 固定模板：整栋墙种由 base_kind 指定（空串 = 交给常规分配）。
                    kind = (self.vault.base_kind if self.vault.material == FIXED else "") or self.material_kind
                if kind:
                    overrides[(self.left + col, self.top + row)] = kind
        return overrides

    def wire_cells(self) -> set[tuple[int, int]]:
        """显式电线位（w）的绝对坐标——显式走线优先于自动布线。"""
        return {
            (self.left + col, self.top + row)
            for row in range(self.vault.height)
            for col in range(self.vault.width)
            if self.pattern_char(row, col) == WIRE_CHAR
        }

    def pressure_floor_cells(self) -> set[tuple[int, int]]:
        """压力地板位（p）的绝对坐标（开放格 + 地板变体）。"""
        return {
            (self.left + col, self.top + row)
            for row in range(self.vault.height)
            for col in range(self.vault.width)
            if self.pattern_char(row, col) == PRESSURE_CHAR
        }

    def logic_node_cells(self, kind: str) -> list[tuple[int, int]]:
        """指定逻辑固体墙种（X/M/R/O/D/B/K/J/V/L）的绝对坐标列表。"""
        target = VAULT_CHAR_KINDS_INVERTED.get(kind)
        if target is None:
            return []
        return [
            (self.left + col, self.top + row)
            for row in range(self.vault.height)
            for col in range(self.vault.width)
            if self.pattern_char(row, col) == target
        ]

    def trap_positions(self) -> list[tuple[int, int]]:
        return self.logic_node_cells("陷阱石台")

    def liquid_overrides(self) -> dict[tuple[int, int], str]:
        """该盖章区域内液体位的格子 → 液态记忆种类映射。"""
        if not self.liquid_kind:
            return {}
        return {
            (self.left + col, self.top + row): self.liquid_kind
            for row in range(self.vault.height)
            for col in range(self.vault.width)
            if self.pattern_char(row, col) == LIQUID_CHAR
        }


class Vault:

    def __init__(
        self,
        vid: str,
        name: str,
        phase: str,
        pattern: list[str],
        material: str = VARIABLE,
        min_open: float = 0.0,
        min_solid: float = 0.0,
        base_kind: str = "",
        liquid: str = "",
        loot: bool = False,
        decor: bool = False,
        forms: tuple[str, ...] = (),
        rarity: str = RARITY_COMMON,
        event: str = "",
        trap_pool: tuple[str, ...] = (),
        valve_material: str = "",
        exclusive_layer: int = 0,
        circuit: dict | None = None,
        loot_anchor: tuple[int, int] | None = None,
        allowed_depths: tuple[int, ...] = (),
        allowed_realms: dict[str, tuple[int, ...]] | None = None,
        event_anchor: tuple[int, int] | None = None,
        npc_id: str = "",
        npc_anchor: tuple[int, int] | None = None,
    ):
        self.vid = vid
        self.name = name
        self.phase = phase
        self.material = material
        # 稀有度：影响模板在加权抽取中的权重（见 RARITY_WEIGHTS）。
        self.rarity = rarity if rarity in RARITIES else RARITY_COMMON
        self.pattern = pattern  # 见模块头部的图案字符表
        # 后置/装饰的地形门槛：两个条件相互独立，只校验显式设置的那个。
        # （默认 1.0 的旧写法会让只设 min_open 的模板隐含要求「实心比 100%」，
        # 数学上永远无法生成——那正是大批模板从不出现的原因。）
        self.min_open = min_open
        self.min_solid = min_solid
        # 全模板 '#' 统一墙种（空串 = 由常规墙体分配决定）；仅固定模板可用。
        self.base_kind = base_kind
        # 液体位（~）灌入的液态记忆：固定模板写死在这里，不定模板盖章时从常见池抽。
        self.liquid = liquid
        # 中央石台盛放稀有物品（见 VaultPlacement.loot_cell）。
        self.loot = loot
        # ---- 附加属性：池子归属（可叠加修饰，不属于分类轴）----
        # decor：房间装饰池（只在房间类层型从房间矩形内部盖章）。
        self.decor = decor
        # forms：层型专属池（只在列出的层型出现；空 = 公用池）。
        self.forms = tuple(forms)
        self.height = len(pattern)
        self.width = max(len(row) for row in pattern)
        # 结构绑定事件（2026-09-18）：中大型结构生成时附带生成的固定异常地点
        # （EVENT_DEFINITIONS 的 event_id；空 = 无）。不占每层随机事件配额。
        self.event = event
        # 逻辑固体（内容扩展包 v1）：陷阱石台的候选场景池（生成时确定性抽一种）。
        self.trap_pool = tuple(trap_pool)
        # 灌注阀释放的材料（空 = 默认水）。
        self.valve_material = valve_material
        # 专属层：非 0 = 只在该层生成（且不进随机池）。
        self.exclusive_layer = exclusive_layer
        self.circuit = circuit
        # 旋转信息：0 = 原样，1~3 = 顺时针旋转的 90° 次数（由 rotate_vault 填写）。
        self.rotation = 0
        # loot 台面在图案中的位置（行, 列）；旋转时跟随图案重算。
        self.loot_anchor: tuple[int, int] | None = loot_anchor
        self.allowed_depths = tuple(allowed_depths)
        self.allowed_realms = dict(allowed_realms or {})
        self.event_anchor = event_anchor
        self.npc_id = npc_id
        self.npc_anchor = npc_anchor

    def available_at(self, depth: int, realm_id: str = "") -> bool:
        """Decoration keeps its old pool; scoped structures match exact layers."""
        if realm_id:
            return (not self.allowed_depths and not self.allowed_realms and not self.exclusive_layer
                    or depth in self.allowed_realms.get(realm_id, ()))
        if self.allowed_realms and not (self.allowed_depths or self.exclusive_layer):
            return False
        return (not self.allowed_depths or depth in self.allowed_depths) and (
            not self.exclusive_layer or depth == self.exclusive_layer)

    @property
    def is_variable(self) -> bool:
        return self.material == VARIABLE

    @property
    def chars(self) -> set[str]:
        return {ch for row in self.pattern for ch in row}

    def uses(self, ch: str) -> bool:
        return ch in self.chars

    def cell_solid(self, row: int, col: int) -> bool | None:
        ch = self.pattern_char(row, col)
        if ch in (OPEN_CHAR, LIQUID_CHAR, CONNECT_CHAR, WIRE_CHAR, PRESSURE_CHAR):
            # 液体位是开放格（液体躺在地上）；连通符号本身也是空地，
            # 只是「这里要与外界联通」的标记，都不参与连通阻断。
            return False
        if ch in (SOLID_CHAR, COMMON_SOLID_CHAR) or ch in VAULT_CHAR_KINDS:
            return True
        return None  # 不关心，由地形决定

    def anchor_positions(self) -> list[tuple[int, int]]:
        """连通符号（@）在图案中的 (行, 列) 列表。"""
        return [
            (row, col)
            for row in range(self.height)
            for col in range(self.width)
            if self.pattern_char(row, col) == CONNECT_CHAR
        ]

    def pattern_char(self, row: int, col: int) -> str:
        row_text = self.pattern[row]
        return row_text[col] if col < len(row_text) else BLANK_CHAR

    def fits(self, width: int, height: int) -> bool:
        """该模板能否放进这张地图（四边至少各留 2 格意识边界余量）。"""
        return self.width + 4 <= width and self.height + 4 <= height


def pick_by_rarity(vaults: "list[Vault]", rng: random.Random, ancient: bool = False) -> Vault:
    """按稀有度加权挑一个模板（古朴修饰符把稀有两级权重翻倍）。"""
    weights = [
        RARITY_WEIGHTS.get(v.rarity, 100) * (2 if ancient and v.rarity in (RARITY_RARE, RARITY_VERY_RARE) else 1)
        for v in vaults
    ]
    total = sum(weights)
    roll = rng.random() * total
    for vault, weight in zip(vaults, weights):
        roll -= weight
        if roll < 0:
            return vault
    return vaults[-1]


def rotate_vault(vault: Vault, times: int) -> Vault:
    """生成模板的旋转变体（顺时针 90° × times），不在数据里另写一份。

    图案字符全部是「格位语义」（实心/开放/墙种/连通符号），没有方向性，
    因此直接旋转字符矩阵即可；loot 台面锚点跟随图案重算，保证旋转后
    仍是同一格石台。times=0 时原样返回同一对象。
    """
    times %= 4
    if times == 0:
        return vault
    rows = [list(row) for row in vault.pattern]
    anchor = vault.loot_anchor or ((vault.height // 2, vault.width // 2) if vault.loot else None)
    event_anchor = vault.event_anchor
    npc_anchor = vault.npc_anchor
    current_height = vault.height
    for _ in range(times):
        rows = [list(chars) for chars in zip(*rows[::-1])]
        if anchor is not None:
            r, c = anchor
            # 顺时针 90°：旧 (r, c) → 新 (c, H-1-r)，H 是本轮旋转前图案的高度。
            anchor = (c, current_height - 1 - r)
        current_height = len(rows)  # 旋转后的行数 = 旋转前的列数
    pattern = ["".join(row) for row in rows]
    circuit = vault.circuit
    if circuit:
        from ...circuit_schema import transform_board
        def rotate_position(x, y):
            w, h = vault.width, vault.height
            for _ in range(times):
                x, y, w, h = h-1-y, x, h, w
            return x, y
        circuit = transform_board(circuit, rotate_position)
    rotated = Vault(
        vault.vid,
        vault.name,
        vault.phase,
        pattern,
        material=vault.material,
        min_open=vault.min_open,
        min_solid=vault.min_solid,
        base_kind=vault.base_kind,
        liquid=vault.liquid,
        loot=vault.loot,
        decor=vault.decor,
        forms=vault.forms,
        rarity=vault.rarity,
        event=vault.event,
        trap_pool=vault.trap_pool,
        valve_material=vault.valve_material,
        exclusive_layer=vault.exclusive_layer,
        circuit=circuit,
    )
    def rotate_anchor(value):
        if value is None:
            return None
        row, col = value
        width, height = vault.width, vault.height
        for _ in range(times):
            row, col, width, height = col, height-1-row, height, width
        return (row, col)
    rotated.allowed_depths = vault.allowed_depths
    rotated.allowed_realms = dict(vault.allowed_realms)
    rotated.event_anchor = rotate_anchor(event_anchor)
    rotated.npc_id = vault.npc_id
    rotated.npc_anchor = rotate_anchor(npc_anchor)
    rotated.rotation = times
    rotated.loot_anchor = anchor
    return rotated


def regions_overlap(
    left: int,
    top: int,
    width: int,
    height: int,
    protected: "list[tuple[int, int, int, int]] | None",
) -> bool:
    """候选位置是否与任一保护区（含边界矩形）重叠。"""
    if not protected:
        return False
    right, bottom = left + width - 1, top + height - 1
    for pl, pt, pr, pb in protected:
        if not (right < pl or pr < left or bottom < pt or pb < top):
            return True
    return False


def _oriented(vault: Vault, rng: random.Random) -> Vault:
    """盖章前随机取向：所有模板都存在 4 个旋转变体，按 rng 现场生成。"""
    return rotate_vault(vault, rng.randrange(4))


def stamp_vault(
    mask: list[list[bool]],
    vault: Vault,
    left: int,
    top: int,
    rng: random.Random | None = None,
) -> "VaultPlacement | None":
    """把 vault 图案盖进掩码；越界或（后置时）条件不满足返回 None。

    成功返回 ``VaultPlacement``（真值，旧式 ``if stamp_vault(...)`` 写法兼容），
    供调用方记录位置以做墙种覆写、液体灌注与战利品投放。

    不定模板在**几何与条件都通过之后**才抽材料（整栋统一一种）——放在这里而不是
    入口处，是为了不因为一次失败的尝试白耗随机数，层与层的材料序列才稳定。
    """
    height, width = len(mask), len(mask[0])
    if left <= 0 or top <= 0 or left + vault.width >= width - 1 or top + vault.height >= height - 1:
        return None
    if vault.phase == POST:
        open_count = solid_count = total = 0
        for row in range(vault.height):
            for col in range(vault.width):
                if vault.cell_solid(row, col) is None:
                    continue
                total += 1
                if mask[top + row][left + col]:
                    solid_count += 1
                else:
                    open_count += 1
        if total == 0 or open_count / total < vault.min_open or solid_count / total < vault.min_solid:
            return None
    material_kind = solid_kind = liquid_kind = ""
    if vault.is_variable:
        # 整栋统一一种材料；只在实际需要时才抽（不消耗多余随机数）。
        seed_text = f"{vault.vid}|{left}|{top}"
        if vault.uses(SOLID_CHAR):
            material_kind = _pick(rng, COMMON_WALLS, seed_text + "|wall")
        if vault.uses(COMMON_SOLID_CHAR):
            solid_kind = _pick(rng, COMMON_SOLIDS, seed_text + "|solid")
        if vault.uses(LIQUID_CHAR):
            liquid_kind = _pick(rng, COMMON_LIQUIDS, seed_text + "|liquid")
    elif vault.uses(LIQUID_CHAR):
        # 固定模板的液体位用写死的种类（见 Vault.liquid）。
        liquid_kind = vault.liquid
    for row in range(vault.height):
        for col in range(vault.width):
            solid = vault.cell_solid(row, col)
            if solid is not None:
                mask[top + row][left + col] = solid
    return VaultPlacement(vault, left, top, material_kind, solid_kind, liquid_kind)


def try_stamp_vault(
    mask: list[list[bool]],
    vault: Vault,
    rng: random.Random,
    attempts: int = 14,
    avoid: "list[tuple[int, int, int, int]] | None" = None,
) -> "VaultPlacement | None":
    """在整张地图里随机找位置盖章：多次尝试，全失败返回 None。

    每次尝试先随机取向（旋转变体现场生成），再按取向后的尺寸选位；
    ``avoid`` 列出必须避开的保护区（后置模板不盖在前置区域上）。
    """
    height, width = len(mask), len(mask[0])
    for _ in range(attempts):
        oriented = _oriented(vault, rng)
        left = rng.randrange(2, max(3, width - oriented.width - 1))
        top = rng.randrange(2, max(3, height - oriented.height - 1))
        if regions_overlap(left, top, oriented.width, oriented.height, avoid):
            continue
        placement = stamp_vault(mask, oriented, left, top, rng)
        if placement is not None:
            return placement
    return None


def stamp_vault_near_open(
    mask: list[list[bool]],
    vault: Vault,
    rng: random.Random,
    attempts: int = 24,
    avoid: "list[tuple[int, int, int, int]] | None" = None,
) -> "VaultPlacement | None":
    """把模板左上角对准随机挑中的「开放格」再盖章。

    与 `try_stamp_vault` 的「整图随机取点」不同：锚点只从开放格里选，因此
    窄模板（拱门排 / 壁龛 / 柱廊）必定落在走廊、侧室或大厅里，而不是撞在
    整片实心墙上白白浪费尝试次数——那正是「层型专属模板一整层都不出现」的
    主因。窄长廊的短边往往只有 2~3 格通道，随机取点的命中率低得可怜。
    """
    height, width = len(mask), len(mask[0])
    oriented = _oriented(vault, rng)
    anchors = [
        (x, y)
        for y in range(1, height - oriented.height)
        for x in range(1, width - oriented.width)
        if not mask[y][x]
    ]
    if not anchors:
        return None
    for _ in range(attempts):
        x, y = anchors[rng.randrange(len(anchors))]
        if regions_overlap(x, y, oriented.width, oriented.height, avoid):
            continue
        placement = stamp_vault(mask, oriented, x, y, rng)
        if placement is not None:
            return placement
    return None


def stamp_vault_in_room(
    mask: list[list[bool]],
    vault: Vault,
    room: tuple[int, int, int, int],
    rng: random.Random,
    attempts: int = 8,
    avoid: "list[tuple[int, int, int, int]] | None" = None,
) -> "VaultPlacement | None":
    """把小型装饰 vault 盖进房间矩形内部（缩进 1 格，避开门口所在的墙体）。

    ``room`` 是房间矩形 ``(left, top, width, height)``（含边墙）；
    内部空间放不下或条件不满足时返回 None。
    """
    left, top, width, height = room
    oriented = _oriented(vault, rng)
    inner_left, inner_top = left + 2, top + 2
    inner_right, inner_bottom = left + width - oriented.width - 1, top + height - oriented.height - 1
    if inner_right < inner_left or inner_bottom < inner_top:
        return None
    for _ in range(attempts):
        x = rng.randrange(inner_left, inner_right + 1)
        y = rng.randrange(inner_top, inner_bottom + 1)
        if regions_overlap(x, y, oriented.width, oriented.height, avoid):
            continue
        placement = stamp_vault(mask, oriented, x, y, rng)
        if placement is not None:
            return placement
    return None
