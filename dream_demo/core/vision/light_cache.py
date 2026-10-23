"""§12 B：环境光源的缓存、区域保形采样与撤销。

本模块只处理**装饰彩光的来源层**（谁在发光、照到哪些格），不做全图 RGB
合成——合成仍在 ``ui/effects._light_pool`` 里按视口做。这样拆开的原因：

- 来源发现、连片分组与视线掩码原来在每个 FX 帧重算（30fps × 视口扫描 ×
  逐源布雷森汉姆），是 §12.9.2「静止时传播重算 0」不达标的直接原因；
- 光色、呼吸相位、玩家移动不该重跑传播（§12.6.1）——缓存键由
  :func:`env_scene_key` 给出，只含「层 + 植物版本 + 来源签名 + 遮挡签名 +
  视口矩形」，**不含回合数**，因此同一回合内与世界静止时的重复取帧都命中缓存。

缓存不序列化、不进存档；换层、读档、死亡后由调用方 ``clear()``。
"""

from __future__ import annotations

from dataclasses import dataclass

# 区块边长（§12.6.2 首轮候选 8×8，可在基准里调）。
BLOCK = 8
# 缓存条目上限：超出后按最近最少使用淘汰（§12.6.4 内存上限）。
DEFAULT_MAX_ENTRIES = 512
# 每个连片区域的保形采样点数：高质量 3（两端 + 中点），低质量 2（两端）。
REGION_SAMPLES = 3
LOW_REGION_SAMPLES = 2


@dataclass(frozen=True)
class CachedSource:
    """一个已登记的装饰来源（世界坐标）。"""

    source_id: str
    x: int
    y: int
    color: str
    radius: float
    brightness: float
    # 该来源能照亮的格（世界坐标）；None = 没有遮挡约束。
    mask: frozenset[tuple[int, int]] | None = None

    @property
    def block(self) -> tuple[int, int]:
        return (self.x // BLOCK, self.y // BLOCK)


def block_of(x: int, y: int) -> tuple[int, int]:
    return (int(x) // BLOCK, int(y) // BLOCK)


def source_signature(colored) -> tuple:
    """来源集合的稳定签名（与输入顺序无关）。

    ``colored`` 是 ``(world_x, world_y, spec)`` 候选列表。签名同时包含
    位置与表现参数——位置决定分组与采样点，光色/半径/亮度决定
    :class:`CachedSource` 的内容，任一变化都必须让缓存失效。
    """
    return tuple(sorted(
        (int(x), int(y), str(spec.source_id), str(spec.color),
         round(float(spec.radius), 3), round(float(spec.brightness), 3))
        for x, y, spec in colored
    ))


def _cells_key(cells) -> tuple[int, int]:
    """(格数, 集合哈希)：**不**把整个格集合放进缓存键。

    缓存上限 ``DEFAULT_MAX_ENTRIES`` 条，若每条键都挂一份视口大小的
    ``frozenset``，常驻内存会随「视口面积 × 条目数」增长（§12.6.4 的内存
    上限要求）。哈希碰撞的后果只是该次「本应立即重算」变成不重算，
    且只影响遮挡带来的明暗；来源本身的增删在 :func:`source_signature`
    里是逐字段精确比对，撤销仍然即时。
    """
    frozen = frozenset(cells)
    return len(frozen), hash(frozen)


def occlusion_signature(opaque, smoke=(), blockers=()) -> tuple:
    """遮挡内容签名：实心墙与高植物 / 挡视线的气体 / 临时视线阻断场。

    ``_has_line_of_sight`` 的判定口径就是这三类（`sight.py:363`）：实心且
    非透明墙与高度至少2的植物、遮蔽强度足够的类墙体气体（黑烟/灰尘）、异象技能的薄雾与
    折面场。任一变化都会改变来源掩码，因此都要进缓存键——**这是把
    ``state.time`` 从键里拿掉的前提**。
    """
    return (_cells_key(opaque), _cells_key(smoke), _cells_key(blockers))


def env_scene_key(state, colored, *, left: int, top: int, width: int, height: int,
                  points: int, opaque, smoke=(), blockers=()) -> tuple:
    """环境来源缓存的完整键：层 + 植物版本 + 来源签名 + 遮挡签名 + 视口。

    🔴 键里**没有** ``state.time``（2026-10-20 B2 批）。旧键把回合数算进去，
    等于「每回合必然 miss」：静态场景也在每回合重跑连通分组、保形采样与
    逐源布雷森汉姆掩码（§12.6.2「普通移动不使用 state.time 作为全部固定灯
    的失效条件」）。现在世界没变时同样的来源与遮挡直接命中缓存。
    """
    return (
        state.layer_key(),
        int(getattr(state, "plant_revision", 0) or 0),
        source_signature(colored),
        occlusion_signature(opaque, smoke, blockers),
        int(left), int(top), int(width), int(height), int(points),
    )


def region_samples(component, max_points: int = REGION_SAMPLES):
    """把一条连片光源（长条 / 环 / 拐角）采样成若干代表点。

    旧实现只取排序中点：一条 12 格长廊只剩中间一格亮，两端全黑；环形区域
    更是只剩一个点。这里沿**长轴**取均匀分点并保留两端（§12.6.2
    「长条、环和隔墙两侧保留各段覆盖」）。``max_points`` 只降低形状精度，
    不允许整体丢弃区域。
    """
    points = sorted(component)
    if not points:
        return []
    if len(points) == 1 or max_points <= 1:
        return [points[len(points) // 2]]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    axis = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
    ordered = sorted(points, key=lambda p: (p[axis], p[1 - axis]))
    count = min(int(max_points), len(ordered))
    if count <= 1:
        return [ordered[len(ordered) // 2]]
    # 均匀分点的下标，含首尾；四舍五入后去重（短区域不会产生重复点）。
    indexes = sorted({
        round(i * (len(ordered) - 1) / (count - 1)) for i in range(count)
    })
    return [ordered[i] for i in indexes]


class EnvLightCache:
    """环境来源缓存：按「来源集合 + 世界版本 + 视口」复用，LRU 淘汰。"""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self.max_entries = max(1, int(max_entries))
        self._entries: dict[tuple, tuple[CachedSource, ...]] = {}
        self._order: list[tuple] = []
        self.stats = {"hit": 0, "miss": 0, "evict": 0}

    def get(self, key: tuple) -> tuple[CachedSource, ...] | None:
        value = self._entries.get(key)
        if value is None:
            self.stats["miss"] += 1
            return None
        self.stats["hit"] += 1
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        return value

    def put(self, key: tuple, sources) -> tuple[CachedSource, ...]:
        value = tuple(sources)
        self._entries[key] = value
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        while len(self._entries) > self.max_entries:
            oldest = self._order.pop(0)
            self._entries.pop(oldest, None)
            self.stats["evict"] += 1
        return value

    def clear(self) -> None:
        self._entries.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._entries)


class _MissType:
    """「缓存里没有」的哨兵。

    掩码的合法值包含 ``None``（``_mask_for`` 在极端情况下返回空），所以
    ``get()`` 不能用 ``None`` 表示未命中——那样每次都会当没缓存上重算。
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - 只用于调试打印
        return "MISS"


#: ``MaskCache.get()`` 未命中时的返回值（见 :class:`_MissType`）。
MISS = _MissType()


class MaskCache:
    """逐来源视线掩码缓存（§6.2「只作废可能穿过该区域的来源传播」）。

    为什么单独一层：来源发现/分组/采样很便宜（集合运算），真正贵的是
    ``_mask_for`` —— 每个采样点扫 (2r+1)² 格、每格一次 Bresenham。而掩码只
    取决于「采样点 + 半径 + 沿途遮挡」，与「这一帧视口在哪」无关：

    - 玩家走一格 → 候选集合在视野边缘增减 → 整场景键 miss（分组重算，便宜），
      但绝大多数采样点位置没变、遮挡没变 → 掩码**命中**；
    - 一堵墙倒了 → 只有「包围区覆盖该 8×8 区块」的来源掩码失效。

    键 = ``(x, y, 半径, 地图尺寸, 覆盖区块的遮挡签名)``，见 :func:`mask_key`。
    遮挡签名由渲染侧在扫描视口时按 8×8 世界区块顺手累积（见
    :func:`occupy_block` / :func:`block_signatures`），不额外扫一遍地图。
    包围区伸出视口的来源，缺的那几块由 :func:`ensure_block_signatures` 按需
    补扫（2026-10-21），所以视口边缘的来源同样能命中缓存——补扫仍然读真实格，
    不猜；只是把「每帧重算掩码」换成「场景变了一次补扫」。
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self.max_entries = max(1, int(max_entries))
        self._entries: dict[tuple, tuple] = {}
        self._order: list[tuple] = []
        self.stats = {"hit": 0, "miss": 0, "evict": 0}

    def get(self, key: tuple):
        store = self._entries.get(key)
        if store is None:
            self.stats["miss"] += 1
            return MISS
        self.stats["hit"] += 1
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        return store[0]

    def put(self, key: tuple, mask) -> None:
        # 用单元素元组存：掩码合法值是 frozenset 或 None，包一层才能把
        # 「缓存了一条 None」与「没缓存」（get 返回 MISS）区分开。
        self._entries[key] = (mask,)
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        while len(self._entries) > self.max_entries:
            oldest = self._order.pop(0)
            self._entries.pop(oldest, None)
            self.stats["evict"] += 1

    def clear(self) -> None:
        self._entries.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._entries)


def block_span(x: int, y: int, radius: float) -> tuple[int, int, int, int]:
    """来源包围区覆盖的 8×8 世界区块范围（含两端）。"""
    reach = max(1, int(round(float(radius))))
    return ((int(x) - reach) // BLOCK, (int(y) - reach) // BLOCK,
            (int(x) + reach) // BLOCK, (int(y) + reach) // BLOCK)


def covered_blocks(x: int, y: int, radius: float) -> tuple[tuple[int, int], ...]:
    bx0, by0, bx1, by1 = block_span(x, y, radius)
    return tuple((bx, by) for bx in range(bx0, bx1 + 1) for by in range(by0, by1 + 1))


def mask_key(sx: int, sy: int, radius: float, block_occlusion, complete_blocks,
             bounds=None):
    """掩码缓存键；包围区有区块签名不完整时返回 ``None`` = 不缓存。

    键里的 ``bounds`` 是地图尺寸：``_mask_for`` 会把扫描范围裁到地图内，所以
    两个尺寸不同的层即使遮挡完全相同，同一采样点的掩码也可能不一样（视口
    伸出地图边缘时那几块「没有东西挡」的区块签名是 0，光靠签名分不出来）。
    """
    if complete_blocks is None:
        return None
    blocks = covered_blocks(sx, sy, radius)
    for block in blocks:
        if block not in complete_blocks:
            return None
    width, height = bounds if bounds is not None else (0, 0)
    return (int(sx), int(sy), round(float(radius), 3), int(width), int(height),
            tuple((block, block_occlusion.get(block, (0, 0))) for block in blocks))


def occupy_block(store: dict, x: int, y: int) -> None:
    """把一格「挡视线的东西」记进它所在的 8×8 区块签名（渲染侧顺手调用）。

    只累积 ``(格数, 异或哈希)``：纯整数运算，比给每格建元组再 hash 便宜一个
    数量级。碰撞的后果仅是「这一块本该重算掩码却没重算」，且只影响遮挡明暗。
    """
    block = (int(x) // BLOCK, int(y) // BLOCK)
    count, digest = store.get(block, (0, 0))
    store[block] = (count + 1, digest ^ ((int(x) * 73856093) ^ (int(y) * 19349663)))


def block_signatures(walls, smoke=(), blockers=(), *, left: int = 0, top: int = 0,
                     width: int = 0, height: int = 0, bounds=None):
    """一次性给出（区块遮挡签名, 签名完整的区块集合）。

    ``walls`` / ``smoke`` / ``blockers`` 都是**世界坐标**的格列表——正好是
    ``_has_line_of_sight`` 的判据（实心非透明墙/高植物、挡视线的气体、技能场）。

    「完整」的判据：这个区块里**地图内**的每一格都被本次扫描覆盖到。视口常见的
    情形是四周各有一圈半个区块露在外面，若直接按「整个区块在视口内」判，视口
    边缘 3 格内的来源会全部放弃缓存（60×30 视口下约占 28%）。区块伸到地图外的
    部分不可能有格挡光（``_mask_for`` 把扫描范围裁到地图内），所以只要「区块 ∩
    地图 ⊆ 视口」就算完整。
    """
    store: dict[tuple[int, int], tuple[int, int]] = {}
    for cells in (walls, smoke, blockers):
        if not cells:
            continue
        for x, y in cells:
            occupy_block(store, x, y)
    map_w, map_h = bounds if bounds is not None else (0, 0)
    complete: set[tuple[int, int]] = set()
    if width > 0 and height > 0 and map_w > 0 and map_h > 0:
        left, top = int(left), int(top)
        right, bottom = left + int(width) - 1, top + int(height) - 1
        # 各向外扩一个区块：视口边缘的来源，其包围区可能探进相邻区块。
        for bx in range(left // BLOCK - 1, right // BLOCK + 2):
            for by in range(top // BLOCK - 1, bottom // BLOCK + 2):
                lo_x = max(bx * BLOCK, 0)
                hi_x = min(bx * BLOCK + BLOCK - 1, map_w - 1)
                lo_y = max(by * BLOCK, 0)
                hi_y = min(by * BLOCK + BLOCK - 1, map_h - 1)
                if lo_x > hi_x or lo_y > hi_y:
                    # 整块在地图外：没有任何格能挡视线。
                    complete.add((bx, by))
                elif (lo_x >= left and hi_x <= right
                      and lo_y >= top and hi_y <= bottom):
                    complete.add((bx, by))
    return store, frozenset(complete)


def ensure_block_signatures(state, store: dict, complete, blocks, *, bounds=None):
    """把视口扫描没覆盖到的区块补扫进签名（2026-10-21）。

    为什么需要：来源发现只看视口内的格，但一个贴着视口边缘的光源，它的半径
    会伸到视口外——那几块 8×8 的遮挡签名本次扫描没累积，``mask_key`` 于是
    返回 ``None``（不缓存），这条来源每帧重算掩码。60×30 视口下边缘一圈约占
    来源的三成，正好是「静止时传播重算 0」最常破功的地方。

    做法是把「包围区盖到、但本次没扫完」的区块按需补扫一遍：读的判据与渲染
    侧完全一致（实心非透明墙/高植物 / 挡视线的气体），**不猜**。补扫只发生在场景键
    miss 时（玩家或视口真的动了），而且只补外圈那一环区块。

    ``blockers``（异象技能薄雾场）不用补：:func:`block_signatures` 收到的是
    全量列表，已经全部计入。
    """
    from ...materials.walls import TRANSPARENT_WALLS
    from ...materials import plant_height

    map_w, map_h = bounds if bounds is not None else (
        int(getattr(state, "width", 0) or 0), int(getattr(state, "height", 0) or 0))
    if map_w <= 0 or map_h <= 0:
        return store, complete
    gas_blocks = getattr(state, "_gas_sight_effect", None)
    for block in blocks:
        if block in complete:
            continue
        bx, by = int(block[0]), int(block[1])
        lo_x, hi_x = max(bx * BLOCK, 0), min(bx * BLOCK + BLOCK - 1, map_w - 1)
        lo_y, hi_y = max(by * BLOCK, 0), min(by * BLOCK + BLOCK - 1, map_h - 1)
        if lo_x > hi_x or lo_y > hi_y:
            # 整块在地图外：没有任何格能挡光，签名「完整」且为空。
            complete.add(block)
            continue
        for y in range(lo_y, hi_y + 1):
            for x in range(lo_x, hi_x + 1):
                try:
                    cell = state.cell(x, y)
                except Exception:      # 层快照比 bounds 短时不去猜，跳过这一格
                    continue
                # 与渲染侧逐句对应（两处判据必须同口径，否则签名会漏格）。
                if cell.solid and cell.wall_kind and cell.wall_kind not in TRANSPARENT_WALLS:
                    occupy_block(store, x, y)
                plant = getattr(cell, "plant", 0)
                if plant and plant_height(plant) >= 2:
                    occupy_block(store, x, y)
                if cell.gas > 0 and gas_blocks is not None and gas_blocks(cell)[0]:
                    occupy_block(store, x, y)
        complete.add(block)
    return store, complete


def _mask_for(state, wx: int, wy: int, radius: float) -> frozenset[tuple[int, int]] | None:
    """单个来源的直线可达掩码（世界坐标）。"""
    reach = max(1, int(round(radius)))
    allowed: list[tuple[int, int]] = []
    for ay in range(max(0, wy - reach), min(state.height, wy + reach + 1)):
        for ax in range(max(0, wx - reach), min(state.width, wx + reach + 1)):
            if max(abs(ax - wx), abs(ay - wy)) > reach:
                continue
            if (ax, ay) == (wx, wy) or state._has_line_of_sight(wx, wy, ax, ay):
                allowed.append((ax, ay))
    return frozenset(allowed) if allowed else None


def build_env_sources(state, colored, *, max_points: int = REGION_SAMPLES,
                      masks: MaskCache | None = None,
                      block_occlusion=None, complete_blocks=None):
    """把「候选格 + 来源登记」变成缓存用的来源列表（世界坐标）。

    ``colored`` 是 ``(world_x, world_y, spec)``。步骤：
    1. 按**身份**做四连通分组（同色不同来源不合并，§12 A）；
    2. 每组用 :func:`region_samples` 取保形采样点，长条/环不再只剩一个中点；
    3. 每个采样点算自己的视线掩码（同格不同来源互不覆盖掩码）。

    没有任何语义截断：多少组就产多少来源，数量由缓存上限与采样点数控制，
    不按「前 6 / 前 12」丢整片光区（§12.6.4）。

    传入 ``masks``（:class:`MaskCache`）时，第 3 步按「采样点 + 半径 + 包围区
    区块遮挡签名」复用掩码——这一步是真正贵的（每点 ``(2r+1)²`` 格布雷森汉姆），
    而分组与采样是集合运算，很便宜。``block_occlusion`` / ``complete_blocks``
    由渲染侧在扫描视口时顺手累积（:func:`occupy_block`）；包围区超出视口的
    采样点，其缺的区块由 :func:`ensure_block_signatures` 补扫，因此同样入缓存。
    """
    by_pos = {(int(x), int(y), spec.source_id): spec for x, y, spec in colored}
    remaining = set(by_pos)
    out: list[CachedSource] = []
    bounds = (int(getattr(state, "width", 0) or 0),
              int(getattr(state, "height", 0) or 0))
    while remaining:
        start = remaining.pop()
        source_key = start[2]
        stack = [start]
        component = [start]
        while stack:
            cx, cy, _sid = stack.pop()
            for nb in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                key = (nb[0], nb[1], source_key)
                if key in remaining:
                    remaining.discard(key)
                    component.append(key)
                    stack.append(key)
        cells = [(cell[0], cell[1]) for cell in component]
        for sx, sy in region_samples(cells, max_points):
            spec = by_pos.get((sx, sy, source_key))
            if spec is None:
                continue
            key = None
            mask = MISS
            if masks is not None:
                key = mask_key(sx, sy, spec.radius, block_occlusion,
                               complete_blocks, bounds=bounds)
                if key is not None:
                    mask = masks.get(key)
            if mask is MISS:
                mask = _mask_for(state, sx, sy, spec.radius)
                if key is not None:
                    masks.put(key, mask)
            out.append(CachedSource(
                spec.source_id, sx, sy, spec.color, spec.radius,
                spec.brightness, mask))
    out.sort(key=lambda s: (s.source_id, s.y, s.x))
    return tuple(out)
