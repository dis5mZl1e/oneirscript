"""地势视图与局部查看的共用口径（docs/261019方案合集.md §15.4—§15.5）。

平时地图不显示地势：只有切到「地势」观察层、鼠标悬浮或键盘观察时才读这些值。
色阶与形状阶梯都是**固定**的，不随本层已知区的最小／最大值自动缩放——否则可以
拿已知格的颜色反推未知地形。极端档位归入高／低端色阶，但精确档位永不截断：
两列格直接写数字，窄格用形状，右栏与局部示意始终给出真实值。

字符与图像后端都调用这里的同一份口径；流向提示只做与真实模拟相同的**只读**
比较（先按地势档、再按液面＝档位×ELEV_STEP＋液量），不抽随机、不推进材料。
"""
from __future__ import annotations

from rich.cells import set_cell_size

from ..core.constants import ELEV_STEP
from ..i18n import tr

# (档位下限, 名称, 颜色, 单列形状)：取「下限不超过该档位的最后一条」，于是首尾
# 两条天然成为低／高端的钳位桶，中间档位保持精确。
ELEVATION_SCALE = (
    (-99, "深洼", "#3f6f96", "▼"),
    (-2, "低地", "#6ba3c9", "▽"),
    (0, "基准", "#9aa3ad", "─"),
    (1, "高地", "#d0a95c", "△"),
    (3, "高台", "#f0d98a", "▲"),
)

# 来源键与 core.vision.knowledge 的 CellKnowledge.sources 一致，界面不重新推断权限。
SOURCE_LABELS = {
    "sight": "当前可见",
    "developed": "显影遗留",
    "terrain_known": "地形增强授权",
    "tutorial_chart": "初始图鉴",
    "memory": "上次观察",
    "always_visible": "恒显类别",
}

# 兜底：只拿到状态、拿不到来源时（例如自行构造的场景格）仍要说清是谁给的权限。
STATUS_LABELS = {
    "visible": "当前可见",
    "developed": "显影遗留",
    "terrain_known": "地形增强授权",
    "memory": "上次观察",
    "always_visible": "恒显类别",
    "unknown": "未知",
}

NEIGHBOURS = ((1, 0, "东"), (-1, 0, "西"), (0, 1, "南"), (0, -1, "北"))

CONTOUR_COLOR = "#2b2740"


def elevation_bucket(tier: int) -> tuple[str, str, str]:
    """档位 → (名称, 颜色, 单列形状)；超出首尾桶的值归入端点桶而不是自动缩放。"""
    bucket = ELEVATION_SCALE[0]
    for candidate in ELEVATION_SCALE:
        if tier >= candidate[0]:
            bucket = candidate
    return bucket[1], bucket[2], bucket[3]


def known_elevation(cell) -> int | None:
    """这一格玩家有权知道的地势档位；未知格与未记录格都是 None。"""
    if cell is None or cell.status == "unknown" or cell.elevation is None:
        return None
    return int(cell.elevation)


def elevation_display(cell) -> str:
    """右栏里的档位读数：未知、未记录与真实数值分得开。"""
    tier = known_elevation(cell)
    if tier is not None:
        return str(tier)
    if cell is None or cell.status in ("unknown", "always_visible"):
        return tr("地势未知")
    return tr("地势未记录")


def elevation_source_label(cell) -> str:
    """这一格地势的来源（当前可见／上次观察／对应增强授权）。"""
    for source in getattr(cell, "sources", ()) or ():
        if source in SOURCE_LABELS:
            return tr(SOURCE_LABELS[source])
    return tr(STATUS_LABELS.get(getattr(cell, "status", "unknown"), "未知"))


def elevation_glyph(cell, *, wide: bool) -> tuple[str, str] | None:
    """地势视图里这一格画什么；None = 由调用方保留空白（未知）或地形轮廓。"""
    tier = known_elevation(cell)
    if tier is None:
        return None
    _, color, glyph = elevation_bucket(tier)
    return (str(tier) if wide else glyph, color)


def elevation_range_labels() -> list[str]:
    """固定图例的每一档范围文字（由色阶本身推出，不会与色阶写偏）。"""
    labels = []
    for index, (low, _name, _color, _glyph) in enumerate(ELEVATION_SCALE):
        upper = (ELEVATION_SCALE[index + 1][0] - 1
                 if index + 1 < len(ELEVATION_SCALE) else None)
        if low <= -98:
            labels.append(f"≤{upper}")
        elif upper is None:
            labels.append(f"≥{low}")
        elif upper == low:
            labels.append(str(low))
        else:
            labels.append(f"{low}~{upper}")
    return labels


def elevation_legend() -> list[tuple[str, str, str, str]]:
    """图例条目：(范围, 名称, 颜色, 单列形状)，五档全部固定列出。"""
    labels = elevation_range_labels()
    return [(labels[index], bucket[1], bucket[2], bucket[3])
            for index, bucket in enumerate(ELEVATION_SCALE)]


class LocalView:
    """局部查看的只读视角：每格都按玩家知识授权取值，绝不直接偷读真实地势。

    地图帧的 shared_scene 只在视口内、且可能已经被某个观察层过滤过；悬浮与格子
    详情要的「这一格＋四邻」必须永远走知识层，于是这里现取 `cell_knowledge`。
    """

    def __init__(self, state):
        self._state = state
        self._cells: dict[tuple[int, int], object] = {}

    def cell(self, x: int, y: int):
        if not (0 <= x < self._state.width and 0 <= y < self._state.height):
            return None
        key = (int(x), int(y))
        if key not in self._cells:
            self._cells[key] = self._build(*key)
        return self._cells[key]

    def _build(self, x: int, y: int):
        from ..core.map_scene import SceneCell, SceneTerrain
        state = self._state
        info = state.cell_knowledge(x, y)
        status = info.status
        floor, solid = str(info.floor or ""), bool(info.solid)
        wall, variant = str(info.wall_kind or ""), str(info.aggregate_variant or "")
        elevation = info.elevation
        if (status not in ("visible", "developed", "always_visible")
                and not bool(getattr(state, "map_memory_enabled", False))):
            # 关闭地图记忆时整层本来就公开实时地形；地势跟随同一口径（与
            # build_scene 的 legacy_terrain 分支一致），否则悬浮会满屏「未知」。
            cell = state.cell(x, y)
            status, elevation = "terrain_known", int(getattr(cell, "elevation", 0) or 0)
            floor = str(getattr(cell.floor, "value", cell.floor) or "")
            solid = bool(cell.solid)
            wall = str(cell.wall_kind or "")
            variant = str(cell.aggregate_variant or "")
        terrain = None
        if status != "unknown":
            terrain = SceneTerrain(floor, solid, wall, variant)
        liquid = gas = None
        if status in ("visible", "developed"):
            cell = state.cell(x, y)
            if int(cell.liquid) > 0 and cell.liquid_kind:
                liquid = (str(cell.liquid_kind), int(cell.liquid))
            if int(cell.gas) > 0 and cell.gas_kind:
                gas = (str(cell.gas_kind), int(cell.gas))
        return SceneCell(x=x, y=y, status=status, terrain=terrain,
                         elevation=elevation, sources=info.sources,
                         liquid=liquid, gas=gas, site=str(info.site or ""))


def liquid_surface(cell) -> int | None:
    """液面读数＝地势档×ELEV_STEP＋液量，与材料模拟里的比较口径一致。"""
    tier = known_elevation(cell)
    if tier is None or not cell.liquid:
        return None
    return tier * ELEV_STEP + int(cell.liquid[1])


def _flow_passable(cell) -> bool:
    """真实口径的近似：场景数据不带墙高，固体邻格一律先按阻挡提示。"""
    return not (cell.terrain is not None and cell.terrain.solid)


def flow_line(scene, x: int, y: int) -> str:
    """下一拍的可能流向：先找地势档更低的邻格，没有再比液面（等高才摊平）。

    只读、只用已知格；固体邻格与未知邻格分别说明，不假装整片坡向都已知。
    """
    cell = scene.cell(x, y)
    tier = known_elevation(cell)
    if tier is None:
        return tr("地势未知，无法判断流向")
    surface = liquid_surface(cell)
    lower_tier: list[str] = []
    lower_surface: list[str] = []
    blocked = unknown = 0
    for dx, dy, name in NEIGHBOURS:
        other = scene.cell(x + dx, y + dy)
        other_tier = known_elevation(other)
        if other_tier is None:
            unknown += 1
            continue
        if not _flow_passable(other):
            blocked += 1
            continue
        if other_tier < tier:
            lower_tier.append(tr(name))
            continue
        other_surface = (other_tier * ELEV_STEP + int(other.liquid[1])
                         if other.liquid else other_tier * ELEV_STEP)
        if surface is not None and other_surface < surface:
            lower_surface.append(tr(name))
    if lower_tier:
        return tr("可能流向 {dirs}（邻格地势档更低）", dirs="、".join(lower_tier))
    if lower_surface:
        return tr("可能流向 {dirs}（地势相同，按液面摊平）", dirs="、".join(lower_surface))
    notes = [tr("可知邻格都不更低")]
    if blocked:
        notes.append(tr("{n} 格被固体挡住", n=blocked))
    if unknown:
        notes.append(tr("{n} 格地势未知", n=unknown))
    return "；".join(notes)


def local_elevation_lines(scene, x: int, y: int, player: tuple[int, int]) -> list[str]:
    """§15.5 右栏局部查看：档位与来源、相对脚下高差、四邻坡向、液面与可能流向。"""
    cell = scene.cell(x, y)
    lines = [tr("地势 {value} · 来源 {source}",
                value=elevation_display(cell), source=elevation_source_label(cell))]
    tier = known_elevation(cell)
    base = known_elevation(scene.cell(*player))
    if tier is None or base is None:
        lines.append(tr("相对脚下 {value}", value=tr("未知")))
    elif tier == base:
        lines.append(tr("相对脚下 {value}", value=tr("等高")))
    elif tier > base:
        lines.append(tr("相对脚下 {value}", value=tr("高 {n} 档", n=tier - base)))
    else:
        lines.append(tr("相对脚下 {value}", value=tr("低 {n} 档", n=base - tier)))
    higher = same = lower = unclear = 0
    for dx, dy, _name in NEIGHBOURS:
        other = known_elevation(scene.cell(x + dx, y + dy))
        if other is None or tier is None:
            unclear += 1
        elif other > tier:
            higher += 1
        elif other < tier:
            lower += 1
        else:
            same += 1
    lines.append(tr("四邻 更高 {high} · 等高 {same} · 更低 {low} · 未知 {unknown}",
                    high=higher, same=same, low=lower, unknown=unclear))
    if cell is not None and cell.liquid and tier is not None:
        lines.append(tr("液面 {surface} ＝ 地势 {tier} 档 × {step} ＋ 液量 {amount}",
                        surface=liquid_surface(cell), tier=tier, step=ELEV_STEP,
                        amount=int(cell.liquid[1])))
        lines.append(flow_line(scene, x, y))
        lines.append(tr("“较低”不等于一定马上流入：液量、实际液面、墙体、地板流速与每拍节奏都会改变结果。"))
    return lines


def local_elevation_grid(scene, x: int, y: int) -> list[str]:
    """3×3 局部示意：未知与未记录都留问号，不补全整片地图。"""
    rows = []
    for dy in (-1, 0, 1):
        slots = []
        for dx in (-1, 0, 1):
            tier = known_elevation(scene.cell(x + dx, y + dy))
            value = "?" if tier is None else str(tier)
            slots.append(set_cell_size(f"[{value}]" if (dx, dy) == (0, 0) else value, 4))
        rows.append("".join(slots))
    return [tr("局部示意（[ ] 为光标格，? 为未知或未记录）")] + rows
