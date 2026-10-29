
"""玩家地图知识：三层信息规则的数据层（2026-10-18，docs/261018方案合集.md 第 1 节）。

本模块只负责**玩家已知信息**，不改变世界模拟：
- 普通探索：以 state.visible_cells() 为准记录上一次确认的地形快照；
- 已探索：快照按稳定层键（state.layer_key()）隔离，视野外读取快照而不是真实格子；
- 当前视野 / 已显影 / 全图地形增强：使用当前真实地形（字段级 live=True）；
- 始终可见类别：意识边界与显影液，即使从未探索也按类别显示（不揭开同格其它内容）；
- 未知：不返回真实地板/墙体，调用方应显示「未探索」。

安全边界（文档 §1.3 / §2.2）：
- 调试全视野 debug_full_vision 不得伪造普通探索进度——record_visible_terrain 直接跳过；
- 全图地形增强只授予地形，不写入普通探索快照（remembered_terrain 仍为 None）；
- 记忆只保存绘制与已知通行判断必需的静态地形；生物/物品/液气浓度/火焰/预警不进入。
- 地势档位随地形一起快照（docs/261019方案合集.md §15.7）：记忆格显示最后确认的档位；
  `None` 表示「地势未记录」（旧档没有这一列，载入时绝不扫描真实全图补历史）。
- 恒显类别（意识边界/显影液）只公开自己的类别字段，不因恒显而得知该格地势。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

# ---- 始终可见类别（docs §1.3 首批）----
# Cell.wall_kind / Cell.liquid_kind 存的是材料中文名（见 materials 定义）。
ALWAYS_VISIBLE_WALL_KINDS = frozenset({"意识边界"})
ALWAYS_VISIBLE_LIQUID_KINDS = frozenset({"显影液"})

# 知识规则版本：写入存档，便于以后迁移（旧档缺失 = 0）。
# 2 = 地形快照开始携带地势档位（docs/261019方案合集.md §15.7）。
KNOWLEDGE_VERSION = 3


@dataclass(frozen=True)
class TerrainMemory:
    """上一次在正常视野中确认的静态地形快照。"""

    floor: str
    solid: bool
    wall_kind: str
    aggregate_variant: str
    seen_turn: int
    # 已发现的固定地点/任务地点标记（地点标记与「当前内容是否可见」分开：
    # 标记一旦发现就保留，但不代表现在还能看见事件内容）。
    site: str = ""
    # 地势档位（整数档，液面比较时才乘 ELEV_STEP）。None = 地势未记录：旧存档的
    # 快照没有这一列，按「未记录」显示而不是拿当前真实值冒充历史。
    elevation: int | None = None
    height: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "floor": self.floor,
            "solid": self.solid,
            "wall_kind": self.wall_kind,
            "aggregate_variant": self.aggregate_variant,
            "seen_turn": self.seen_turn,
            "site": self.site,
            "elevation": self.elevation,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "TerrainMemory | None":
        if not isinstance(data, dict):
            return None
        try:
            elevation = data.get("elevation")
            return cls(
                floor=str(data.get("floor", "")),
                solid=bool(data.get("solid", False)),
                wall_kind=str(data.get("wall_kind", "")),
                aggregate_variant=str(data.get("aggregate_variant", "")),
                seen_turn=int(data.get("seen_turn", 0) or 0),
                site=str(data.get("site", "")),
                elevation=None if elevation is None else int(elevation),
                height=None if data.get('height') is None else int(data['height']),
            )
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class CellKnowledge:
    """一格在当前信息权限下的可显示内容。

    status 取值：
      visible       当前正常视野（live=True）
      developed     显影液永久显影格（live=True，沿用既有信息权限）
      terrain_known 全图地形增强覆盖（live=True，仅地形）
      always_visible 始终可见类别（live=True，仅该类别的公开字段）
      memory        记忆快照（live=False）
      unknown       从未探索（各字段为空）
    """

    x: int
    y: int
    status: str
    floor: str = ""
    solid: bool = False
    wall_kind: str = ""
    aggregate_variant: str = ""
    seen_turn: int = 0
    live: bool = False
    sources: tuple[str, ...] = ()
    site: str = ""
    # 已授权的地势档位；None = 这一格的地势玩家无权知道（未知、恒显类别）
    # 或旧档从未记录过地势。绝不为了显示而偷读真实格子。
    elevation: int | None = None
    height: int | None = None

    @property
    def explored(self) -> bool:
        return self.status != "unknown"

    @property
    def shows_terrain(self) -> bool:
        return self.status != "unknown"


def _cell_terrain(cell: Any, turn: int, site: str = "") -> TerrainMemory:
    floor = getattr(cell, "floor", "")
    floor_name = getattr(floor, "value", floor)
    return TerrainMemory(
        floor=str(floor_name or ""),
        solid=bool(getattr(cell, "solid", False)),
        wall_kind=str(getattr(cell, "wall_kind", "") or ""),
        aggregate_variant=str(getattr(cell, "aggregate_variant", "") or ""),
        seen_turn=int(turn),
        site=str(site),
        elevation=int(getattr(cell, "elevation", 0) or 0),
        height=int(getattr(cell, 'height', 0) or 0),
    )


def _site_labels(state: Any, layer: str) -> dict[tuple[int, int], str]:
    """当前层已发现的固定地点/任务地点（只取「此刻看得见」的未解决事件与设施）。

    地点标记一经记录就保留（见 record_visible_terrain 的 site 合并规则），
    事件解决后标记得以继续存在，但不再暴露事件当前状态。
    """
    labels: dict[tuple[int, int], str] = {}
    for event in getattr(state, "events", ()) or ():
        if getattr(event, "resolved", False):
            continue
        name = str(getattr(event, "name", "") or "")
        if name:
            labels[(int(event.x), int(event.y))] = name
    ledger = getattr(state, "world_ledger", None)
    facilities = getattr(ledger, "facilities", None) if ledger is not None else None
    if isinstance(facilities, dict):
        for record in facilities.values():
            if getattr(record, "layer_key", None) != layer:
                continue
            pos = (int(getattr(record, "x", -1)), int(getattr(record, "y", -1)))
            labels.setdefault(pos, str(getattr(record, "definition_id", "") or "设施"))
    return labels


def initialize_map_knowledge(state: Any) -> None:
    """新局初始化：写入规则版本并记录开局视野（旧档不走这里）。

    记录会用 visible_cells 的缓存；初始化后立刻作废它，避免「开局地形被
    测试/脚本直接改写后仍读到旧视野」的陈旧缓存（正式动作按时间/位置失效，
    但初始化采样不是动作）。
    """
    if int(getattr(state, "map_knowledge_version", 0) or 0) <= 0:
        state.map_knowledge_version = KNOWLEDGE_VERSION
    record_visible_terrain(state)
    try:
        from .cache import invalidate
        invalidate(state)
    except Exception:  # pragma: no cover - 字段未就绪时不影响初始化
        pass


def record_visible_terrain(state: Any) -> int:
    """把当前正常视野内的地形并入玩家记忆，返回新学到/更新的格子数。

    只在「正常视野」记录：调试全视野不入账；显影格、全图地形增强与始终可见
    类别都不算普通探索（它们各自的显示权限由 cell_knowledge 单独处理）。
    """
    if getattr(state, "debug_full_vision", False):
        return 0
    layer = state.layer_key()
    memory = state.terrain_memory.setdefault(layer, {})
    try:
        visible = state.visible_cells()
    except Exception:  # pragma: no cover - 生成/载入早期字段未就绪时静默跳过
        return 0
    turn = int(getattr(state, "time", 0) or 0)
    site_labels = _site_labels(state, layer)
    learned = 0
    for x, y in visible:
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        previous = memory.get((x, y))
        # 地点标记是「已发现」的事实：一旦记下就保留，不因事件解决而消失。
        site = previous.site if previous is not None else ""
        if not site:
            site = site_labels.get((x, y), "")
        cell = state.cell(x, y)
        floor = str(getattr(cell.floor, "value", cell.floor) or "")
        solid = bool(getattr(cell, "solid", False))
        wall = str(getattr(cell, "wall_kind", "") or "")
        variant = str(getattr(cell, "aggregate_variant", "") or "")
        elev = int(getattr(cell, "elevation", 0) or 0)
        # 地形与地点都未变时复用同一份 TerrainMemory（探索快照共享）：
        # seen_turn 仅在地形真正变化时前移，玩家可见状态完全一致。
        if (previous is not None and previous.floor == floor
                and previous.solid == solid and previous.wall_kind == wall
                and previous.aggregate_variant == variant and previous.site == site
                and previous.elevation == elev and previous.height == int(cell.height)):
            continue
        memory[(x, y)] = TerrainMemory(
            floor=floor, solid=solid, wall_kind=wall,
            aggregate_variant=variant, seen_turn=turn, site=site, elevation=elev,
            height=int(cell.height),
        )
        learned += 1
    # 地形记忆洞察：危险快照只在亲眼看见时更新（不进入普通地形记忆字段）。
    record_visible_hazards(state)
    return learned


def remembered_terrain(state: Any, x: int, y: int) -> TerrainMemory | None:
    """当前层在 (x,y) 的记忆快照；未探索返回 None。"""
    layer = state.terrain_memory.get(state.layer_key()) or {}
    return layer.get((int(x), int(y)))


# ---- §11 §7 条件洞察的地形记录（局部照明 / 静默惯习）----

def record_terrain_cells(state: Any, cells: Iterable[tuple[int, int]]) -> int:
    """把指定格的地形并入记忆；不要求这些格此刻在正常视野里。

    调用方必须先确认信息权限（光源实际照到 / 贴着铁幕振动记录）。
    """
    layer = state.layer_key()
    memory = state.terrain_memory.setdefault(layer, {})
    turn = int(getattr(state, "time", 0) or 0)
    learned = 0
    for x, y in cells:
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        snapshot = _cell_terrain(state.cell(x, y), turn)
        previous = memory.get((x, y))
        if previous is not None:
            if (previous.floor == snapshot.floor and previous.solid == snapshot.solid
                    and previous.wall_kind == snapshot.wall_kind
                    and previous.aggregate_variant == snapshot.aggregate_variant
                    and previous.elevation == snapshot.elevation
                    and previous.height == snapshot.height):
                continue
            snapshot = replace(snapshot, site=previous.site)
        memory[(x, y)] = snapshot
        learned += 1
    return learned


def record_terrain_snapshot(state: Any, cx: int, cy: int, radius: int) -> int:
    """显影类构想：记录以 (cx,cy) 为中心、切比雪夫半径内的完整地形快照。

    调用方先确认信息权限（落点当前可见，或已是已知地形快照）。只写地形，
    不揭示生物/物品/液体/气体，也不授予任何实时视野。
    """
    cells = [(x, y)
             for y in range(max(0, int(cy) - radius), min(state.height, int(cy) + radius + 1))
             for x in range(max(0, int(cx) - radius), min(state.width, int(cx) + radius + 1))]
    return record_terrain_cells(state, cells)


def record_terrain_outline(state: Any, cells: Iterable[tuple[int, int]]) -> int:
    """轮廓记录（回响／旁注）：只知道「开放或阻挡」，不公开墙/地材料。

    阻挡格统一记为默认聚合墙，开放格记为无材料地面；地点标记沿用旧记录。
    """
    from ...materials import DEFAULT_WALL
    layer = state.layer_key()
    memory = state.terrain_memory.setdefault(layer, {})
    turn = int(getattr(state, "time", 0) or 0)
    changed = 0
    for x, y in cells:
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        cell = state.cell(x, y)
        solid = bool(getattr(cell, "solid", False))
        previous = memory.get((x, y))
        site = previous.site if previous is not None else ""
        if (previous is not None and previous.solid == solid
                and previous.floor == "" and previous.elevation is None):
            continue
        memory[(x, y)] = TerrainMemory(
            floor="", solid=solid,
            wall_kind=DEFAULT_WALL if solid else "",
            aggregate_variant="", seen_turn=turn, site=site, elevation=None,
        )
        changed += 1
    return changed


def record_light_snapshot(state: Any, sx: int, sy: int) -> int:
    """局部照明：记录一个已确认开启光源本次实际照到的地形快照。

    只按该光源自己的半径与视线判定；墙后、被挡住的格不入账，也不揭示物品。
    """
    from .glow import source_radius
    sx, sy = int(sx), int(sy)
    if not (0 <= sx < state.width and 0 <= sy < state.height):
        return 0
    if not state.is_visible(sx, sy):
        return 0
    radius = source_radius(state.cell(sx, sy))
    if radius <= 0:
        return 0
    cells: list[tuple[int, int]] = []
    for y in range(max(0, sy - radius), min(state.height, sy + radius + 1)):
        for x in range(max(0, sx - radius), min(state.width, sx + radius + 1)):
            if (max(abs(sx - x), abs(sy - y)) <= radius
                    and state._has_line_of_sight(sx, sy, x, y)):
                cells.append((x, y))
    return record_terrain_cells(state, cells)


def record_iron_curtain_outline(state: Any) -> tuple[int, int]:
    """静默惯习：贴着一面已确认的沉思铁幕等待，记录最多 6 格同种连通墙
    四邻的开放入口轮廓。只入地形，不产生声音，也不越过绝对静音。
    """
    px, py = state.player.x, state.player.y
    seeds: list[tuple[int, int]] = []
    for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
        if not (0 <= nx < state.width and 0 <= ny < state.height):
            continue
        cell = state.cell(nx, ny)
        if not (cell.solid and cell.wall_kind == "沉思铁幕"):
            continue
        remembered = remembered_terrain(state, nx, ny)
        confirmed = state.is_visible(nx, ny) or (
            remembered is not None and remembered.wall_kind == "沉思铁幕")
        if confirmed:
            seeds.append((nx, ny))
    walls: list[tuple[int, int]] = []
    seen = set(seeds)
    frontier = list(seeds)
    while frontier and len(walls) < 6:
        x, y = frontier.pop(0)
        cell = state.cell(x, y)
        if not (cell.solid and cell.wall_kind == "沉思铁幕"):
            continue
        walls.append((x, y))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            if (nx, ny) in seen:
                continue
            other = state.cell(nx, ny)
            if other.solid and other.wall_kind == "沉思铁幕":
                seen.add((nx, ny))
                frontier.append((nx, ny))
    entries: set[tuple[int, int]] = set()
    for wx, wy in walls:
        for nx, ny in ((wx + 1, wy), (wx - 1, wy), (wx, wy + 1), (wx, wy - 1)):
            if not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            if not state.cell(nx, ny).solid:
                entries.add((nx, ny))
    record_terrain_cells(state, entries)
    return len(walls), len(entries)


# ---- §11 §7 地形记忆：最近 8 处亲眼确认的环境危险快照 ----
HAZARD_MEMORY_LIMIT = 8


def _hazard_cost(state: Any, cell: Any) -> int:
    cost = 1
    if (int(getattr(cell, "liquid", 0) or 0) > 0
            and getattr(cell, "liquid_kind", "") == "蜂蜜"
            and int(getattr(cell, "liquid", 0) or 0) >= 6):
        cost += 1
    if float(getattr(state, "viscous_debt", 0.0) or 0.0) >= 1.0:
        cost += 1
    return cost


def _hazard_snapshot(state: Any, cell: Any, x: int, y: int, turn: int) -> dict:
    return {
        "x": int(x), "y": int(y),
        "liquid": int(getattr(cell, "liquid", 0) or 0),
        "liquid_kind": str(getattr(cell, "liquid_kind", "") or ""),
        "gas": int(getattr(cell, "gas", 0) or 0),
        "gas_kind": str(getattr(cell, "gas_kind", "") or ""),
        "flame": int(getattr(cell, "flame", 0) or 0),
        "cost": _hazard_cost(state, cell),
        "turn": int(turn),
    }


def record_visible_hazards(state: Any) -> int:
    """亲眼看到的液体/气体/火焰格写入最近 8 处危险快照（层内）。"""
    if getattr(state, "debug_full_vision", False):
        return 0
    layer = state.layer_key()
    memory = state.hazard_memory.setdefault(layer, {})
    turn = int(getattr(state, "time", 0) or 0)
    recorded = 0
    try:
        visible = state.visible_cells()
    except Exception:  # pragma: no cover - 生成/载入早期字段未就绪时静默跳过
        return 0
    for x, y in visible:
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        cell = state.cell(x, y)
        if not (getattr(cell, "liquid", 0) or getattr(cell, "gas", 0)
                or getattr(cell, "flame", 0)):
            continue
        memory[f"{int(x)},{int(y)}"] = _hazard_snapshot(state, cell, x, y, turn)
        recorded += 1
    if len(memory) > HAZARD_MEMORY_LIMIT:
        oldest = sorted(memory.items(), key=lambda item: (int(item[1].get("turn", 0)),
                                                          item[0]))
        for key, _ in oldest[:len(memory) - HAZARD_MEMORY_LIMIT]:
            memory.pop(key, None)
    return recorded


def hazard_snapshot(state: Any, x: int, y: int) -> dict | None:
    """当前层某格的最近危险快照；没有则 None。"""
    layer = state.hazard_memory.get(state.layer_key()) or {}
    return layer.get(f"{int(x)},{int(y)}")


def decode_hazard_memory(raw: Any) -> dict:
    """旧档缺省 = 空；条目损坏时逐条跳过。"""
    if not isinstance(raw, dict):
        return {}
    decoded: dict[str, dict[str, dict]] = {}
    for layer, rows in raw.items():
        if not isinstance(rows, dict):
            continue
        kept: dict[str, dict] = {}
        for key, value in rows.items():
            if not isinstance(value, dict):
                continue
            try:
                kept[str(key)] = {
                    "x": int(value.get("x", 0)), "y": int(value.get("y", 0)),
                    "liquid": max(0, int(value.get("liquid", 0) or 0)),
                    "liquid_kind": str(value.get("liquid_kind", "") or ""),
                    "gas": max(0, int(value.get("gas", 0) or 0)),
                    "gas_kind": str(value.get("gas_kind", "") or ""),
                    "flame": max(0, int(value.get("flame", 0) or 0)),
                    "cost": max(1, int(value.get("cost", 1) or 1)),
                    "turn": max(0, int(value.get("turn", 0) or 0)),
                }
            except (TypeError, ValueError):
                continue
        if kept:
            decoded[str(layer)] = kept
    return decoded


def always_visible_category(cell: Any) -> str:
    """始终可见类别名（意识边界/显影液）；普通格返回空串。"""
    return _always_visible_category(cell)


def _always_visible_category(cell: Any) -> str:
    # 转换只在真正要查表的字段上进行（2026-10-25）：普通地板格以前每格都做
    # 两次 str() + 一次 int()，而两个集合命中都要求 solid/液体先成立。
    if bool(getattr(cell, "solid", False)):
        if str(getattr(cell, "wall_kind", "") or "") in ALWAYS_VISIBLE_WALL_KINDS:
            return "意识边界"
    if int(getattr(cell, "liquid", 0) or 0) > 0:
        if str(getattr(cell, "liquid_kind", "") or "") in ALWAYS_VISIBLE_LIQUID_KINDS:
            return "显影液"
    return ""


def _with_site(knowledge: CellKnowledge, memory: TerrainMemory | None) -> CellKnowledge:
    """把「已发现地点」标记挂到知识结果上（存在即保留，和内容可见性分开）。"""
    site = memory.site if memory is not None else ""
    if not site or knowledge.site == site:
        return knowledge
    return replace(knowledge, site=site)


def _as_knowledge(snapshot: TerrainMemory, x: int, y: int, status: str,
                  *, live: bool, sources: tuple[str, ...],
                  elevation: int | None) -> CellKnowledge:
    return CellKnowledge(
        x=x, y=y, status=status,
        floor=snapshot.floor, solid=snapshot.solid, wall_kind=snapshot.wall_kind,
        aggregate_variant=snapshot.aggregate_variant, seen_turn=snapshot.seen_turn,
        live=live, sources=sources, elevation=elevation,
        height=snapshot.height if status != 'always_visible' else None,
    )


# ---- CY-6 可选内核调度（2026-10-27）----
# cell_knowledge 每帧被调用上千次：若每次调用都读环境变量（实测 1000 次约
# 2.4ms），光是开关判断就会吃掉整步收益。因此开关在首次调用时解析一次并缓存；
# 进程内改环境（A/B 探针）后调用 refresh_kernel_switch() 重新解析即可。
_KERNEL_STATE = 0  # 0=未解析 1=纯Python回退 2=内核
_KERNEL_FN = None


def refresh_kernel_switch() -> None:
    """按 cy_kernels.enabled("knowledge") 重新解析内核开关（A/B 与测试用）。"""
    global _KERNEL_STATE, _KERNEL_FN
    _KERNEL_STATE = 0
    _KERNEL_FN = None


def _resolve_kernel_state() -> int:
    global _KERNEL_STATE, _KERNEL_FN
    kernel_fn = None
    try:
        from ...cy_kernels import enabled
        use_kernel = bool(enabled("knowledge"))
    except Exception:  # pragma: no cover - 开关异常时退回原实现
        use_kernel = False
    if use_kernel:
        try:
            from .knowledge_kernel import cell_knowledge as kernel_fn
        except Exception:  # pragma: no cover - 内核缺失时退回原实现
            kernel_fn = None
            use_kernel = False
    if use_kernel and kernel_fn is not None:
        _KERNEL_FN = kernel_fn
        _KERNEL_STATE = 2
    else:
        _KERNEL_STATE = 1
    return _KERNEL_STATE


def cell_knowledge(state: Any, x: int, y: int, visible=None,
                   memory_layer: dict | None = None,
                   developed: set | None = None) -> CellKnowledge:
    """按三层信息规则合并一格的可显示内容（不修改状态）。

    性能（2026-10-21 任务1）：``_cell_terrain`` 现场快照**按需构造**。旧写法在函数
    一进来就构造它，可「视野外记忆格」与「未知格」这两条返回路径根本不看它——
    实测一次移动里 1020 次调用（正好等于视口格数），其中七八百次的快照是当场丢掉
    的垃圾。改成惰性求值后，构造次数降到「真正要展示实时地形的格子数」。

    性能（2026-10-21 任务3）：``memory_layer`` / ``developed`` 是**一次渲染事务里
    解析一次的上下文**。旧写法每格都调 ``state.layer_key()``（有名梦中梦要拼
    ``R{realm}:{depth}``）与 ``developed_for_depth()``（每格一次 ``str(depth)`` +
    ``setdefault``）——1017 格就是 1017 次字符串构造。整帧渲染请把这两份传进来；
    单格查询（悬停、详情）照旧不传，行为完全一致。

    CY-6（2026-10-27）：函数体保持原实现不动，只在最前面加一次缓存好的开关
    判断；内核开启时走编译内核 knowledge_kernel.cell_knowledge（逐字段等价），
    关闭/缺失/未编译时执行的就是原来的这段代码。开关在首次调用时解析一次并
    缓存（每格读环境变量实测约 2.4µs/次，会吃掉整步收益）；进程内改环境后
    调用 refresh_kernel_switch() 重新解析。
    """
    global _KERNEL_STATE
    if _KERNEL_STATE == 0:
        _resolve_kernel_state()
    if _KERNEL_STATE == 2:
        return _KERNEL_FN(state, x, y, visible, memory_layer, developed)
    x, y = int(x), int(y)
    if not (0 <= x < state.width and 0 <= y < state.height):
        return CellKnowledge(x=x, y=y, status="unknown")
    cell = state.cell(x, y)
    turn = int(getattr(state, "time", 0) or 0)
    if memory_layer is None:
        memory_layer = state.terrain_memory.get(state.layer_key()) or {}
    if developed is None:
        developed = state.developed_for_depth()

    # 实时地形快照只在「真要展示实时地形」的分支里构造一次（2026-10-21 任务1）；
    # 2026-10-25 起不再为每格创建两个闭包，直接内联调用。
    if ((x,y) in visible if visible is not None else state.is_visible(x, y)):
        current = _cell_terrain(cell, turn)
        return _as_knowledge(current, x, y, "visible", live=True, sources=("sight",),
                             elevation=current.elevation)
    if (x, y) in developed:
        current = _cell_terrain(cell, turn)
        return _as_knowledge(current, x, y, "developed", live=True,
                             sources=("developed",), elevation=current.elevation)
    if (bool(getattr(state, "terrain_known", False))
            or getattr(state, "realm_id", "") == "toy_memories"):
        current = _cell_terrain(cell, turn)
        return _with_site(
            _as_knowledge(current, x, y, "terrain_known", live=True,
                          sources=("terrain_known",), elevation=current.elevation),
            memory_layer.get((x, y)),
        )
    category = _always_visible_category(cell)
    if category:
        current = _cell_terrain(cell, turn)
        # 恒显类别只公开自己的字段：看见边界或显影液标记不等于知道这一片地势。
        knowledge = _as_knowledge(current, x, y, "always_visible", live=True,
                                  sources=("always_visible", category), elevation=None)
        return _with_site(knowledge, memory_layer.get((x, y)))
    memory = memory_layer.get((x, y))
    if memory is not None:
        source = 'tutorial_chart' if memory.seen_turn == -1 and state.depth == 0 and not state.realm_id else 'memory'
        knowledge = _as_knowledge(memory, x, y, "memory", live=False,
                                  sources=(source,), elevation=memory.elevation)
        return _with_site(knowledge, memory)
    return CellKnowledge(x=x, y=y, status="unknown")


def knowledge_status(state: Any, x: int, y: int) -> str:
    """便捷查询：格子的信息状态字符串（UI 与测试共用）。"""
    return cell_knowledge(state, x, y).status


# ---- 存档编解码（persistence 只做搬运）----

def encode_terrain_memory(state: Any) -> dict[str, list[list]]:
    """层键 → [[x, y, floor, solid, wall_kind, variant, seen_turn, site, elevation], ...]。"""
    encoded: dict[str, list[list]] = {}
    for layer, memory in (getattr(state, "terrain_memory", None) or {}).items():
        entries: list[list] = []
        for (x, y), snapshot in sorted(memory.items()):
            entries.append([int(x), int(y), snapshot.floor, bool(snapshot.solid),
                            snapshot.wall_kind, snapshot.aggregate_variant,
                            int(snapshot.seen_turn), snapshot.site, snapshot.elevation,
                            snapshot.height])
        if entries:
            encoded[str(layer)] = entries
    return encoded


def decode_terrain_memory(raw: Any) -> dict[str, dict[tuple[int, int], TerrainMemory]]:
    """旧档缺字段 / 条目损坏时逐条跳过，绝不因知识数据拒绝载入整份存档。"""
    from ...cy_kernels import enabled
    if enabled("save"):
        # CY-1 内核：等价解码 + 相同冻结快照复用（frozen dataclass 不可变）。
        from ..save_kernel import decode_terrain_memory as kernel_decode
        return kernel_decode(raw)
    decoded: dict[str, dict[tuple[int, int], TerrainMemory]] = {}
    if not isinstance(raw, dict):
        return decoded
    for layer, entries in raw.items():
        if not isinstance(entries, list):
            continue
        memory: dict[tuple[int, int], TerrainMemory] = {}
        for entry in entries:
            if not isinstance(entry, (list, tuple)) or len(entry) < 7:
                continue
            try:
                x, y = int(entry[0]), int(entry[1])
                # 第 9 列是地势档位（docs §15.7）；旧档不足 9 列或该列为 null 时按
                # 「地势未记录」载入，等玩家再次正常观察才补上，不扫描真实全图。
                elevation = None
                if len(entry) > 8 and entry[8] is not None:
                    elevation = int(entry[8])
                snapshot = TerrainMemory(
                    floor=str(entry[2] or ""),
                    solid=bool(entry[3]),
                    wall_kind=str(entry[4] or ""),
                    aggregate_variant=str(entry[5] or ""),
                    seen_turn=int(entry[6] or 0),
                    # 第 8 列是「已发现地点」标记（2026-10-18 第二批补强）；
                    # 旧档 7 列照常载入，site 为空。
                    site=str(entry[7] or "") if len(entry) > 7 else "",
                    elevation=elevation,
                    height=int(entry[9]) if len(entry) > 9 and entry[9] is not None else None,
                )
            except (TypeError, ValueError):
                continue
            memory[(x, y)] = snapshot
        if memory:
            decoded[str(layer)] = memory
    return decoded
