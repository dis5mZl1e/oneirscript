"""FX 特效层引擎（渲染特效计划 docs/render-fx-dev-plan.md 路线 A）。

把地图视口当成低分辨率画布，每个特效按帧计算「单元格 → 覆盖样式」的叠加层，
由 FxCanvasWidget 套在基准帧（render.py 的 render_map）之上着色。

设计契约（对应文档 §4）：
- 本模块**不依赖 textual/rich**：输入输出都是纯数据（dict / tuple / str），
  可独立单测与基准。
- 纯函数语义：shader 不改状态、无随机（呼吸相位由源坐标推导，扫描相位由 t 推导）。
- 输出是「叠加样式」而非绝对覆盖：只对受影响的格产出样式串，其余格不动；
  颜色全部经预生成渐变 LUT 取得（避免逐帧字符串格式化）。
- 实现选型：**numpy**（2026-09-20 升级注记）。初版为纯 Python（视口 ≤5×10³ 格、
  光源个位数时够用），M2 光照池引入后改为 numpy 向量化：多光源/大面积噪点下
  复杂度与光源数解耦，实测远低于 4ms/帧预算；缺失 numpy 时整条光照路径自动
  降级关闭（HAS_NUMPY=False），其余效果不受影响。引擎结构（能量源→叠加层→LUT）
  与文档一致。

质量档（fx_quality）：0=off（不调用）、1=low（呼吸/暗角，10fps）、2=high（全特效 20fps）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # numpy 光照池（设计文档 §1）：缺失时整条光照路径自动降级关闭。
    import numpy as _np

    HAS_NUMPY = True
except ImportError:  # pragma: no cover - 打包环境必装，本分支只在裸环境触发
    _np = None
    HAS_NUMPY = False

# ---------------------------------------------------------------------------
# 颜色工具：hex 渐变 LUT（预生成，运行期只查表）
# ---------------------------------------------------------------------------

_LUT_STEPS = 64


def _parse_hex(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _mix_lut(color: str, target: str, steps: int = _LUT_STEPS) -> list[str]:
    """从 color 到 target 的线性渐变表（index 越大越接近 target）。"""
    c0, c1 = _parse_hex(color), _parse_hex(target)
    return [
        _to_hex(tuple(round(a + (b - a) * i / (steps - 1)) for a, b in zip(c0, c1)))
        for i in range(steps)
    ]


_GLOW_LUT_CACHE: dict[str, list[str]] = {}


def glow_lut(color: str) -> list[str]:
    """辉光渐变：index 0=原色淡出 → steps-1=饱和辉光。"""
    lut = _GLOW_LUT_CACHE.get(color)
    if lut is None:
        lut = _mix_lut(_darken(color, 0.45), color)
        _GLOW_LUT_CACHE[color] = lut
    return lut


def _darken(color: str, factor: float) -> str:
    r, g, b = _parse_hex(color)
    return _to_hex((round(r * factor), round(g * factor), round(b * factor)))


def hash01(x: int, y: int, seed: int) -> float:
    """确定性 [0,1) 噪声（与 ui/transition.py 各自独立实现：两模块互不依赖）。"""
    import hashlib

    digest = hashlib.blake2b(f"{x},{y},{seed}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def jitter_color(base: str, x: int, y: int, t: float) -> str:
    """液体/气体微抖动（硬约束，设计文档 §1.3）：

    - 三通道**同乘** k：hue 数学上不动，只剩每通道 ≤0.5 的舍入误差
      （曾试过每通道独立 ±3 噪声——对低饱和色 hue 漂移可达 1°+，弃用）；
    - k 预算受「最大通道 |Δ| ≤ 3（含舍入 ≤ 4）」封顶，亮色自动收紧；
    - 只依赖 (x, y, t) 噪声，**与浓度零相关**（浓度只由图标档位表达）。
    """
    r, g, b = _parse_hex(base)
    k_budget = min(0.03, 3.0 / max(r, g, b, 1))
    k = 1.0 + (hash01(x, y, int(t * 3)) - 0.5) * 2 * k_budget
    return _to_hex((
        min(255, max(0, round(r * k))),
        min(255, max(0, round(g * k))),
        min(255, max(0, round(b * k))),
    ))


def flame_glow(x: int, y: int, t: float) -> str:
    """火焰格的暖橙底：亮度按 (x, y) 的固有相位缓慢呼吸。

    与液/气同一条约束：**不闪**——幅度封在 LUT 的 35%~85% 之间，且每格相位
    由 `hash01(x, y)` 决定（同一片火里各格错开，不会整片同步跳变）。
    火本身也是光源（见 `_light_pool` 的 flames 项），这里只负责它自己那一格。
    """
    lut = glow_lut(_darken(FLAME_COLOR, .4))
    phase = hash01(x, y, 4242) * math.tau
    swing = 0.5 + 0.5 * math.sin(t * 5.5 + phase)
    level = FLAME_LEVEL_MIN + (FLAME_LEVEL_MAX - FLAME_LEVEL_MIN) * swing
    index = int(level * (_LUT_STEPS - 1))
    return lut[max(0, min(_LUT_STEPS - 1, index))]


def liquid_gas_color(base: str, x: int, y: int, t: float) -> str:
    """液体/气体叠加色：基色**先压暗**再走微抖动。

    2026-09-20 修「全图液体/气体每回合闪烁」：叠加层原来直接写满饱和底色
    （`on #4da8eb` 这种），于是每一片液体/气体都变成一块抢戏的实心亮块——
    它与基帧差着一个数量级（基帧自己的液体底色是 `darken(0.25~0.6)`，
    纯液体格甚至根本没有底色），基帧一重画就「亮→灭→亮」地闪。压暗后：

    - 叠加层只是给液体/气体一层淡底，观感回到基帧量级；
    - 抖动仍是「三通道同乘」的那一条硬约束，hue 不动、每通道 |Δ| ≤ 3；
    - 亮度变化仍在（k 同乘 = 整体明暗呼吸），只是幅度不再刺眼。
    """
    return jitter_color(_darken(base, LIQUID_GAS_TINT), x, y, t)


# ---------------------------------------------------------------------------
# 快照：引擎只吃快照，不碰 GameState
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FxSource:
    """呼吸光环源：视口格坐标 + 辉光色 + 相位偏移（由坐标推导，免随机）。

    §12 A（2026-10-20）：光环源不再共用一套「灯半径 / 灯亮度」。``radius``
    与 ``brightness`` 由 ``data.light_sources`` 按来源登记；两者留 None 时
    退回旧的 ``LAMP_RADIUS`` / ``NPC_LAMP_BRIGHTNESS``，因此旧调用方与旧测试
    零迁移。``source_id`` 只用于「同格是否同一物理来源」的去重与调试，
    ``kind`` 决定是否套用该来源自己的遮挡掩码。
    """

    x: int
    y: int
    color: str
    phase: float
    compound: bool = False  # 复合事件：双 sin 叠加，呼吸带不稳定感
    source_id: str = ""
    kind: str = ""              # environment / npc / flame / lamp / electric / flash
    radius: float | None = None
    brightness: float | None = None


def light_flash_sources(entries, *, left: int, top: int, width: int, height: int,
                        visible, t: float) -> tuple[FxSource, ...]:
    """把 core 侧压入的**激活短光**转成本帧可用的光环源（§12 D 残余）。

    ``entries`` 来自 ``state.light_flashes``（``core/light_flash.note_light_flash``
    写的原始字典，世界坐标 + 出生墙钟 ``born``）。三条硬约束：

    1. **看不见就不给光**：激活动作本身不泄露位置，短光只对视野内的玩家播
       （与电光同一口径，§12.4.3「看不见的通电格不发光」）；
    2. **按寿命衰完**：半径从满值收到 55%，亮度线性落到 0 后整条消失——
       短光不是「灯亮了一下就常亮」；
    3. **不猜光色**：颜色/半径/亮度全部来自登记表，未登记的 kind 在 core 侧
       就已被忽略，这里也不做兜底。

    只返回本帧参数，不改 ``entries``（过期剔除由调用方按 ``life`` 做）。
    """
    out: list[FxSource] = []
    for entry in entries or ():
        if not isinstance(entry, dict):
            continue
        life = float(entry.get("life") or 0.0)
        born = float(entry.get("born", t))
        age = t - born
        if life <= 0.0 or age < 0.0 or age > life:
            continue
        wx, wy = int(entry.get("x", -1)), int(entry.get("y", -1))
        if visible is not None and (wx, wy) not in visible:
            continue
        vx, vy = wx - left, wy - top
        if not (0 <= vx < width and 0 <= vy < height):
            continue
        fade = max(0.0, 1.0 - age / life)
        out.append(FxSource(
            vx, vy, str(entry.get("color") or "#ffffff"),
            phase=(vx * 3 + vy * 5) * 0.21,
            source_id=str(entry.get("source_id") or f"flash.{entry.get('seq')}"),
            kind="flash",
            radius=max(0.5, float(entry.get("radius") or 1.0) * (0.55 + 0.45 * fade)),
            brightness=max(0.0, float(entry.get("brightness") or 0.0) * fade),
        ))
    return tuple(out)


@dataclass(frozen=True)
class FxHit:
    """受创涟漪：视口格坐标 + 触发时刻（秒）。"""

    x: int
    y: int
    born: float
    radius: float | None = None  # None preserves the previous maximum reach.


@dataclass(frozen=True)
class FxWave:
    """声波静态标记（2026-10-22）：视口格坐标集合 + 触发时刻（秒）。

    玩家要求去掉声波涟漪，只在视野外听到声波的格子叠一层当前蓝色静态
    底色；扩散半径与逐环计算已删除。
    """

    cells: tuple[tuple[int, int], ...]
    born: float

@dataclass(frozen=True)
class FxProjectile:
    """一发弹道的回放输入（2026-09-23）：结算已完成，这里只做装饰性回放。

    ``cells`` 是**视口格坐标**的飞行序列（不含起点、含终点）；``bounces``
    是 (路径转向下标, 跳弹格视口坐标)；``end ∈ {entity, wall, gap, range,
    land}`` 决定收尾演出；``color`` 拖尾/亮点基色（射击暖白、投掷物品色）。
    """

    cells: tuple[tuple[int, int], ...]
    bounces: tuple[tuple[int, int, int], ...] = ()
    end: str = "range"
    end_cell: tuple[int, int] | None = None
    color: str = "#ffe0b3"
    born: float = 0.0
    kind: str = "shot"
    # UI-only identity captured before the source can be consumed or rearranged.
    visual: object | None = None

    @property
    def flight_time(self) -> float:
        return projectile_flight_time(self.kind, len(self.cells))

    @property
    def total_time(self) -> float:
        return self.flight_time + PROJECTILE_END_LIFE


def projectile_flight_time(kind: str, count: int) -> float:
    if kind == "throw":
        return min(0.85, max(0.45, count * 0.06))
    return min(0.60, max(0.30, count * 0.035))


def projectile_repeat_delay(raw) -> float:
    """Only a settled two-packet shot may extend its decorative playback."""
    return .12 if raw.get('kind') == 'shot' and raw.get('repeat_delay',0) > 0 else 0.


def projectile_replay_time(raw) -> float:
    return (projectile_flight_time(raw.get('kind','shot'),len(raw.get('cells',())))
            + PROJECTILE_END_LIFE + projectile_repeat_delay(raw))


@dataclass(frozen=True)
class FxCombatPulse:
    kind: str
    center: tuple[int, int]
    cells: tuple[tuple[int, int], ...]
    born: float
    life: float = 0.70


@dataclass(frozen=True)
class FxCast:
    profile: str
    motion: str
    source: tuple[int, int]
    cells: tuple[tuple[int, int], ...]
    path: tuple[tuple[int, int], ...]
    born: float
    life: float
    stage: str = 'release'
    progress: float = 0.
    theme: str = ''
    center: tuple[int, int] | None = None


@dataclass(frozen=True)
class FxFrame:
    styles: dict[tuple[int, int], str]
    glyphs: dict[tuple[int, int], tuple[str, str]]


@dataclass(frozen=True)
class FxSnapshot:
    depth: int
    lucidity_ratio: float  # 0..1
    lucidity_tier: int  # 0 健康 .. 3 紧急
    lucidity_dropped: bool  # 本帧相对上帧清醒度骤降（红脉冲已删，字段留作兼容）
    sources: tuple[FxSource, ...]
    hits: tuple[FxHit, ...]
    viewport: tuple[int, int, int, int]  # left, top, width, height（地图格坐标）
    # ---- 渲染升级扩展（2026-09-20，全部带默认值：旧调用/旧存档零迁移）----
    player: tuple[int, int] = (-1, -1)  # 玩家火把（视口格坐标）；(-1,-1)=无
    # 玩家火把的光池半径（2026-09-21）：由调用方传**玩家实际视野半径**，
    # 于是衰减速度随视野变化，且光照范围天然不超过视野（详见 TORCH_RADIUS 注释）。
    # None = 用旧的定值 ``TORCH_RADIUS``——老调用方/老测试零迁移。
    # （常量块在本文件靠后的位置，类默认值没法引用它，所以用 None 当哨兵。）
    torch_radius: float | None = None
    # 地图底色（2026-09-21；二改后**全区域统一黑** = `region_themes.MAP_BG`）。
    # 光照池只拿它当**放行门槛**：底色比旧黑底亮时，光池外圈的微弱光会比底色更暗，
    # 照旧放行就会在地图上套一圈暗环。颜色计算本身不受它影响。
    # ⚠️ 阈值公式保留着（`max(LIGHT_MIN_SUM, sum(base_bg))`）：现在传进来的恒为
    # 黑底，等价于退回 LIGHT_MIN_SUM，但一旦将来又有亮底色，这条保护仍然有效。
    base_bg: str = "#101018"
    surface_bgs: tuple[tuple[int, int, str], ...] = ()
    fixed_ground: frozenset[tuple[int, int]] = frozenset()
    waves: tuple[FxWave, ...] = ()  # 声波静态蓝色标记；空 = 无标记（旧调用方兼容）
    light_walls: bool = True             # False = 光照只落非墙体格（设置 fx_light_walls）
    liquid_gas: tuple[tuple[int, int, str], ...] = ()  # (vx, vy, 基色)：微抖动作用域
    # 允许做微抖动的液/气格（视野内或已显影）。
    liquid_gas_shown: frozenset[tuple[int, int]] = frozenset()
    # 🔴 是否启用上面的白名单。默认 False = 不过滤（旧调用方/存档兼容）。
    # 启用后**空集也必须当作「一个都不许上色」**，绝不能退化成「不过滤」：
    # 视口里有液/气、但恰好一格都没显影时 shown 就是空集，旧写法
    # `if shown and (x, y) not in shown` 会整段跳过过滤，于是整张地图视野外的
    # 液体气体一起亮起来——正是「**有时候**视野外的气体/液体格异常显色」的来源
    # （"有时候" = 恰好没有可见液/气的那些帧）。
    liquid_gas_filter: bool = False
    flames: tuple[tuple[int, int], ...] = ()  # 火焰格（视口坐标，已按可见性过滤）
    opaque: frozenset[tuple[int, int]] = frozenset()   # 视口内墙体格（light_walls=False 时挡光）
    lamps: tuple[tuple[int, int, str], ...] = ()       # 事件光池 (vx, vy, color)
    projectiles: tuple[FxProjectile, ...] = ()         # 弹道回放（2026-09-23）
    projectile_visible: frozenset[tuple[int, int]] | None = None
    ambient_visible: frozenset[tuple[int, int]] | None = None
    aura_protected: frozenset[tuple[int, int]] = frozenset()
    combat_pulses: tuple[FxCombatPulse, ...] = ()
    casts: tuple[FxCast, ...] = ()
    electric_cells: frozenset[tuple[int, int]] = frozenset()
    # 千禧园底色带（2026-10-11）：视口相对 (x0,y0,x1,y1,color)。非空时光池
    # 不再「替换」基帧背景，而是把光强**加在 zone 基色上**——否则玩家火把
    # 会把视野内的草地绿一律换成主梦光照的暖色（玩家报告「视野内仍然是
    # 主层地板底色」的根因）。主梦空表 → 行为与旧版逐字节一致。
    bg_zones: tuple = ()
    # 环境光源的局部传播掩码：(视口 x, 视口 y, 允许照亮的视口格集合)。
    # 玩家视野掩码不能替代光源自身遮挡；只对环境光源生效，旧调用默认空。
    # 逐来源遮挡掩码：(x, y, allowed) 旧写法 / (x, y, source_id, allowed) 新写法。
    # 新写法让同格多个环境来源各自保留自己的传播范围（§12 A）。
    source_masks: tuple = ()


# 辉光/暗角颜色（全区域通用；主题差异由基准帧自身呈现）。
AURA_COLOR = "#ffd166"  # 事件点：暖黄
NPC_GLOW_ALPHA = 0.55  # NPC 光环相对事件点更收敛
VIGNETTE_COLOR = "#0a0a18"  # 低清醒暗角：深靛
RIPPLE_COLOR = "#f05c62"  # 意识体受创：红色
WIPE_COLOR = "#06060c"  # 换层溶解：近黑
AURA_RADIUS = 3  # 曼哈顿距离
AURA_CELL_BUDGET = 8
LIGHT_MAX_CHANNEL = 64  # Ambient light never stacks into an opaque white wash.
# 光环环带偏移（dx, dy, 曼哈顿距离）预计算：每帧 16 光源 × 49 格不再重算 abs。
_AURA_RING = tuple(
    (dx, dy, abs(dx) + abs(dy))
    for dy in range(-AURA_RADIUS, AURA_RADIUS + 1)
    for dx in range(-AURA_RADIUS, AURA_RADIUS + 1)
    if 0 < abs(dx) + abs(dy) <= AURA_RADIUS
)
# 涟漪（2026-09-20 收敛）：原来 9 格/秒 × 0.8s = 半径 7.2 的一圈大波，配上
# 满档橙色几乎等于半屏闪一下——既不是「少量」，也踩到光敏约束。改成 5 格/秒
# × 0.55s ≈ 半径 2.7 的一圈收敛脉冲，看得见、不晃眼。
RIPPLE_SPEED = 5.0  # 格/秒
RIPPLE_WIDTH = 1.2
RIPPLE_LIFE = 0.55
RIPPLE_MAX_RADIUS = RIPPLE_SPEED * RIPPLE_LIFE
RIPPLE_MIN_RADIUS = 1.0
RIPPLE_RESET_TURNS = 3.0
# 声波（2026-10-22）：不再扩散成环；只在视野外听到声波的格子叠当前青灰静态底色。
# off 档由调用方不登记 waves 实现降级（动画缺席时日志仍是完整信息源）。
SOUND_WAVE_COLOR = "#8fd8d8"  # 声波：青灰
SOUND_WAVE_LIFE = 1.6  # 标记保留时长（秒），不再用于扩散速度
SOUND_WAVE_MAX = 8  # 同屏声波标记上限（连发不堆屏）
# 弹道回放（2026-09-23）：飞行 0.3s + 收尾 ≤0.2s，总时长 ≤0.32s 是
# 「不跨回合」的第一道保险（第二道：下一次已确认动作清空缓存）。
PROJECTILE_LIFE = 0.3
PROJECTILE_END_LIFE = 0.2
PROJECTILE_TOTAL = PROJECTILE_LIFE + PROJECTILE_END_LIFE
# 收尾配色：命中异象=白亮一闪、撞墙=橙红（爆炸色板同族、暗一档）、
# 夹缝再暗一档、投掷落点用物品基色；射程耗尽 = 空中淡出、无闪。
PROJECTILE_END_COLORS = {
    "entity": "#ffffff",
    "wall": "#ff7028",
    "gap": "#b85018",
}
PROJECTILE_SPARK_LIFE = 0.12  # 跳弹格硬面火花时长
# 受创边框闪（2026-09-20）：玩家受创 = 地图边框一圈红色**双闪**（替代以玩家
# 为中心的扩散涟漪——血是从身体外侧的「世界边缘」涌来的反馈，不再遮玩家格）。
# 2026-09-21：清醒骤降红脉冲（PULSE_COLOR/PULSE_LIFE）已随「受伤红色涟漪去除」删除。
BORDER_FLASH_LIFE = 0.9
BORDER_FLASH_COLOR = "#ff4530"
# 双闪的两个波峰时刻与高斯宽度（≈2.2Hz 的两次明灭，仍在光敏安全线内）。
BORDER_FLASH_PEAKS = (0.05, 0.45)
BORDER_FLASH_WIDTH = 0.13
# 重要事件边框呼吸闪（2026-09-20 二次扩充）：获得洞察/获得记忆/
# 拾得稀有物品——各占一色（与底栏/导航的界面配色语言一致），
# 包络是两个平滑呼吸波（sin 半波），比受创的硬双闪柔和。
# ⚠️ 2026-09-21 玩家要求去掉了「释放构想」一档（构想不再有动画反馈）。
BORDER_EVENT_LIFE = 1.4
BORDER_EVENT_SWELL = 0.7  # 单个呼吸波的时长；1.4s 总寿命 = 两次呼吸
BORDER_EVENT_COLORS = {
    "insight": "#58e67b",    # 获得洞察：洞察绿
    "memory": "#c9a0ff",     # 获得记忆：紫（✦ 装饰灯同源）
    "rare": "#ffd166",       # 稀有/非常稀有物品：稀有金
}
WIPE_LIFE = 0.6
TORCH_COLOR = "#ffe0b3"   # 玩家火把：暖白（设计文档 §1.2）
# 玩家火把光池半径：**不再是一个定值**（2026-09-21 玩家要求）。
#
# 现在的取法是「跟随玩家的实际视野半径」（``state.effective_sight_radius()``，
# 由 ``_fx_snapshot`` 传进来，见 ``FxSnapshot.torch_radius``）：
# - 视野变大 → 同一个「距离/R」比值变小 → 平滑衰减**变慢**（远处更亮）；
# - 视野变小 → 衰减**变快**（近处就更暗）；
# - ``d = 0`` 处 att 恒为 1.0，再乘 ``TORCH_BRIGHTNESS`` —— **最亮格亮度不变**；
# - 光照非零范围是 ``d < R``，而 R 就取视野半径 ⇒ **光照范围不会大于视野范围**。
#
# TORCH_RADIUS 因此退化成「没有快照时的兜底值」（旧调用方 / 单元测试仍可用它
# 拿到从前的观感）；真实渲染一律走快照字段。
TORCH_RADIUS = 4.5
# 光池半径下限：只为挡住 ``rad * rad == 0`` 的除零（``effective_sight_radius()``
# 本身已 ``max(1, …)``，正常路径不会碰到）。
TORCH_RADIUS_MIN = 1.0
LAMP_RADIUS = 2.5         # 事件/NPC 光池半径
# 火焰：既是光源也是着色格（2026-09-20）。半径/亮度都压得比火把小一档——
# 火是**点缀**，不该盖过玩家自身的照明，也不该把整片地图照成白天。
FLAME_COLOR = "#ff8a3a"
FLAME_RADIUS = 2.2
FLAME_BRIGHTNESS = 0.42
FLAME_LEVEL_MIN = 0.35    # 火焰格底色的明暗呼吸下/上界（占辉光 LUT 的比例）
FLAME_LEVEL_MAX = 0.85
FLAME_LIGHT_MAX = 24      # 进光照池的火焰格上限（着色不受此限）
# 光源亮度（2026-09-20 整体调低一档：原本玩家火把按 1.0 全额输出、事件灯 0.8，
# 在暗色地图上偏抢戏、也压住了地形可读性。三个系数集中在这里方便再调。）
TORCH_BRIGHTNESS = 0.75   # 自身火把（原 1.0）
LAMP_BRIGHTNESS = 0.56    # 事件光池（原 0.8）
NPC_LAMP_BRIGHTNESS = 0.38  # 稳定意识 NPC 光池（原 0.55）
LIGHT_FLOOR = 0.50        # 光照折算成背景色的浓度（原 0.55，避免压过地形可读性）
# 合成效果：玩家脚下从 0.55 降到 0.375（约 −32%），事件灯从 0.44 降到 0.28。
LIGHT_MIN_SUM = 24        # 三通道和低于此值不产出（省 dict 体积）
# 光池噪点的时间量化频率（2026-09-21 性能 P0）：
# 🔴 噪点里的时间项必须**量化**成台阶，不能直接用连续 t。noise 每帧都变 →
# 叠加层每帧都不同 → app 侧 `_fx_paint` 的「内容未变就跳过写回」永远命中不了，
# 写回节流形同虚设（实测「每帧把地图 widget 标脏」才是大头）。
# 值取 1Hz（P0+ 从 5Hz 下调）：光晕的起伏本来就在 ±6% 亮度上、肉眼看不出在动，
# 而**这唯一一个每 0.2s 变化一次的量**，在玩家站着不动时把整張地图每 0.2s 重绘
# 一次——实测它就是空闲时写回最贵的一份（约 7Hz 写回 = 10 个百分点）。
# 想再省约 1.5 点就把这里改成 0（噪点完全静态 —— 仍是「有起伏的不规则光晕」，
# 只是不再漂移；视觉上分辨不出差别）。
LIGHT_NOISE_HZ = 1.0
# 液体/气体叠加底色的浓度：与基帧 layered_background 的 darken(0.25~0.6) 同族。
# 修「液/气闪烁」前这里是 1.0（满饱和实心块），见 liquid_gas_color 的说明。
LIQUID_GAS_TINT = 0.30
# 0-255 → 两位十六进制查表：光照池千级亮格的格式化走查表而非 str.format。
_HEX02 = tuple(f"{i:02x}" for i in range(256))
# 光敏硬上限：任何全屏明暗跳变频率远低于 3Hz；扫描线只压暗不增亮。
CRT_DIM = "dim"
# 扫描线滚动速率（相位翻转频率 = CRT_ROLL_HZ / 2 Hz）：旧值 6（= 3Hz 方波）
# 正好踩在光敏上限上，且每翻转一次火把光晕就整行明灭——看上去就是「主角周围
# 的光在闪/没了」。降到 2.4（≈1.2Hz 翻转）保留 CRT 滚动感，同时远低于上限。
CRT_ROLL_HZ = 0.8
# 扫描线落在一格**已有底色**（光照池/火焰/涟漪/暗角/液气）上时，把底色压到
# 这个比例——只压暗、绝不整格删掉。见 feed() 里扫描线段的说明。
CRT_LIGHT_FACTOR = 0.45


# ---------------------------------------------------------------------------
# 叠加层取值 → Rich 样式串（**唯一转换入口**，渲染侧只准调这个）
# ---------------------------------------------------------------------------

def overlay_style(value: str) -> str:
    """把叠加层的一个取值翻成可直接交给 ``Text.stylize`` 的样式串。

    取值只有三种形态：
    - ``"dim"``：只压暗字形，不设底色（没有底色的格子，主要来自扫描线）；
    - ``"#rrggbb"``：只设底色（光照池 / 暗角 / 光环 / 涟漪 / 液气 / 换层溶解）；
    - ``"dim on #rrggbb"``：字形与底色一起压暗（扫描线落在有底色的格子上）。

    渲染侧绝不能自己拼 ``f"on {value}"``——那会把第三种形态拼成
    ``"on dim on #rrggbb"``（非法样式，整格退化成默认色，光照看起来就没了）。
    """
    if value == CRT_DIM or value.startswith(f"{CRT_DIM} ") or value.startswith('on ') or ' on ' in value:
        return value
    if value.startswith(FOREGROUND_PREFIX):
        # 前景强调（异象意图角标）：不改底色，只改字形样式。
        return value[len(FOREGROUND_PREFIX):]
    return f"on {value}"


FOREGROUND_PREFIX = 'fore:'


# ---------------------------------------------------------------------------
# 引擎：快照 → 叠加层（cell → 样式串）
# ---------------------------------------------------------------------------


def _ripple_path_clear(origin: tuple[int, int], target: tuple[int, int], walls) -> bool:
    """A short grid ray; walls and closed wall corners stop the wave."""
    x, y = origin
    tx, ty = target
    dx, dy = abs(tx-x), -abs(ty-y)
    sx, sy = (1 if x < tx else -1), (1 if y < ty else -1)
    error = dx + dy
    while (x, y) != target:
        twice = 2 * error
        nx, ny = x, y
        if twice >= dy:
            error += dy
            nx += sx
        if twice <= dx:
            error += dx
            ny += sy
        if nx != x and ny != y and ((nx, y) in walls or (x, ny) in walls):
            return False
        x, y = nx, ny
        if (x, y) in walls:
            return False
    return True


class FXEngine:
    """帧无关的叠加层计算器：每次 feed(快照, t) 返回本帧的格子样式表。"""

    def __init__(self) -> None:
        self.last_depth: int | None = None
        self.wipe_born: float | None = None
        # None = 尚未取样：第一帧只记录不判定「骤降」——否则载入低清醒存档的
        # 第一帧会拿 100 的默认值对比出虚假骤降。
        self.last_lucidity: int | None = None
        # 受创/事件边框闪（2026-09-20）：地图边框一圈的瞬时反馈队列。
        # 每项 (born, color, kind)：kind="hit"（受创硬双闪）/ "event"（事件呼吸）。
        self.border_flashes: list[tuple[float, str, str]] = []
        self.scanlines_disabled: bool = False  # 设置页 fx_scanlines=False 时由 app 侧设 True
        self._skip_wipe = False  # 进层演出抑制一次溶解（演出取代它，见设计文档 §2.3）
        self._grids: dict[tuple[int, int], tuple] = {}  # (width,height) → meshgrid 缓存

    def skip_next_wipe(self) -> None:
        """下一次 depth 变化不触发 dissolve_wipe（进层演出自然播完时调用）。"""
        self._skip_wipe = True

    def note_border_hit(self, t: float) -> None:
        """玩家受创：地图边框一圈红色双闪（BORDER_FLASH_LIFE 秒）。"""
        self._push_border_flash(t, BORDER_FLASH_COLOR, "hit")

    def note_border_event(self, t: float, color: str) -> None:
        """重要事件（洞察/记忆/稀有物品）：边框一圈按事件色呼吸闪烁。"""
        self._push_border_flash(t, color, "event")

    def _push_border_flash(self, t: float, color: str, kind: str) -> None:
        if len(self.border_flashes) >= 4:  # 上限：连锁事件不至于叠成彩条
            self.border_flashes.pop(0)
        self.border_flashes.append((t, color, kind))

    def reset_run_state(self) -> None:
        """换局/返家时清跨局状态：清醒度取样归零（重进游戏不得误判骤降）、
        边框闪队列作废。溶解（wipe）不动——它由 depth 变化自驱。"""
        self.last_lucidity = None
        self.border_flashes.clear()

    def frame(self, snap: FxSnapshot, t: float, quality: int) -> FxFrame:
        """兼容旧样式接口；字符层最后绘制，不受环境扫描线压暗。"""
        styles = self.feed(snap, t, quality)
        hit_styles = {cell: styles[cell] for cell in getattr(self, "_last_hit_styles", {})}
        glyphs: dict[tuple[int, int], tuple[str, str]] = {}
        if not quality:
            return FxFrame(styles,glyphs)
        _, _, width, height = snap.viewport

        def put(cell, char, color):
            x, y = cell
            if (0 <= x < width and 0 <= y < height
                    and (snap.projectile_visible is None or cell in snap.projectile_visible)):
                glyphs[cell] = (char, f"bold {color} on {_darken(color, 0.18)}")

        # 火舌、余电只点亮本格，用单列符号保留原有地图格宽。
        if quality:
            flame_budget = min(8 if quality >= 2 else 4, max(1, width*height//40))
            for x, y in snap.flames:
                if flame_budget <= 0:
                    break
                if (x, y) not in snap.aura_protected and (x*3+y+int(t*6)) % 3 == 0:
                    put((x, y), "^" if int(t*8+x+y) % 2 else "*", "#ffb653")
                    flame_budget -= 1
            for x, y in snap.electric_cells:
                if (x, y) not in snap.aura_protected and (x+y+int(t*7)) % 3 == 0:
                    put((x, y), "+" if int(t*9) % 2 else "=", "#85deef")
        budget = 24 if quality >= 2 else 12
        for pulse in snap.combat_pulses:
            age = t-pulse.born
            if not 0 <= age < pulse.life:
                continue
            radius = max((abs(x-pulse.center[0])+abs(y-pulse.center[1])
                          for x, y in pulse.cells), default=0)
            ring = min(radius, int(age/pulse.life*(radius+1)))
            hue = {"explosion": "#ffbf69", "fire": "#ff9c45", "electric": "#91e7ef",
                   'spray':'#91e7ef'}.get(pulse.kind, "#ffbf69")
            for x, y in pulse.cells:
                cell = (x, y)
                if (budget <= 0 or not (0 <= x < width and 0 <= y < height)
                        or snap.ambient_visible is not None and cell not in snap.ambient_visible):
                    continue
                distance = abs(x-pulse.center[0])+abs(y-pulse.center[1])
                if pulse.kind == "explosion" and distance != ring:
                    continue
                if pulse.kind != "explosion" and (x+y+int(age*10)) % 2:
                    continue
                styles[cell] = f"{hue} on {_darken(hue, .13*(1-age/pulse.life))}"
                if cell not in snap.aura_protected and cell not in snap.opaque:
                    glyph = '≈' if pulse.kind == 'spray' else '+' if pulse.kind == 'electric' else '*'
                    put(cell,glyph,_darken(hue,max(.3,1-age/pulse.life)))
                budget -= 1

        for proj in snap.projectiles:
            if proj.visual is not None:
                from .projectile_styles import projectile_samples, ProjectileGlyph
                for cell, char, color in projectile_samples(proj,t-proj.born,quality):
                    x,y=cell
                    if (0<=x<width and 0<=y<height
                            and (snap.projectile_visible is None or cell in snap.projectile_visible)):
                        # Keep the floor background and lighting intact.
                        glyphs[cell]=(ProjectileGlyph(char),f'bold {color}')
                continue
            age = t - proj.born
            if not 0 <= age <= proj.total_time:
                continue
            flight = proj.flight_time
            if proj.cells:
                head = min(len(proj.cells) - 1, int(age / flight * len(proj.cells)))
                if age < flight:
                    for back in (2, 1):
                        idx = head - back
                        if idx < 0:
                            continue
                        x, y = proj.cells[idx]
                        nx, ny = proj.cells[min(idx + 1, len(proj.cells) - 1)]
                        char = "." if proj.kind == "throw" else (
                            "-" if ny == y else "|" if nx == x else
                            "\\" if (nx - x) * (ny - y) > 0 else "/")
                        put((x, y), char, _darken(proj.color, 0.45 if back == 1 else 0.25))
                    put(proj.cells[head], "o" if proj.kind == "throw" else "*",
                        "#fff0ce" if proj.kind == "throw" else proj.color)
            for idx, x, y in proj.bounces:
                spark_age = age - flight * (idx + 1) / max(1, len(proj.cells))
                if 0 <= spark_age <= PROJECTILE_SPARK_LIFE:
                    put((x, y), "+", "#ffce80")
            if age >= flight and proj.end_cell is not None and proj.end != "range":
                put(proj.end_cell, "+" if proj.end in ("wall", "gap", "entity") else "o",
                    _darken(PROJECTILE_END_COLORS.get(proj.end, proj.color),
                            max(0.2, 1 - (age - flight) / PROJECTILE_END_LIFE)))
        from .cast_fx import paint_casts
        cast_styles, cast_glyphs = paint_casts(snap, t, quality)
        styles.update(cast_styles)
        glyphs.update(cast_glyphs)
        # Character particles can carry their own background. Preserve their
        # foreground glyphs while keeping the hurt ring above that background.
        from rich.style import Style
        styles.update(hit_styles)
        for cell, background in hit_styles.items():
            if cell in glyphs:
                glyph, style = glyphs[cell]
                glyphs[cell] = (glyph, str(Style.parse(style) + Style.parse(overlay_style(background))))
        return FxFrame(styles, glyphs)

    def feed(self, snap: FxSnapshot, t: float, quality: int) -> dict[tuple[int, int], str]:
        """计算一帧叠加层：{视口格: 样式串}。quality 0 时不该被调用。"""
        overlay: dict[tuple[int, int], str] = {}
        left, top, width, height = snap.viewport

        # ---- 光照池（numpy 路径；设计文档 §1.2）----
        self._light_pool(snap, t, width, height, overlay)

        # ---- 暗角（清醒度 <70% 渐入，<30% 封顶）----
        # ⚠️ 2026-09-21 玩家要求：去掉受伤时的红色涟漪/边缘红脉冲——
        # 受创反馈只保留地图边框一圈红色双闪（BORDER_FLASH_*，见 note_border_hit）。
        # 旧的「清醒骤降红脉冲」（PULSE_COLOR，edge ring 一圈红）已删除。
        if snap.lucidity_ratio < 0.7:
            ring = 1 if snap.lucidity_ratio >= 0.3 else 2
            shade = glow_lut(VIGNETTE_COLOR)
            level = int((0.7 - snap.lucidity_ratio) / 0.7 * (_LUT_STEPS - 1))
            base = shade[min(_LUT_STEPS - 1, level + 4)]
            for x, y in _edge_cells(width, height, ring):
                if (x, y) in snap.fixed_ground:
                    continue
                overlay[(x, y)] = base

        # ---- 呼吸光环（事件点 / NPC）----
        aura_cells = set()
        aura_budget = min(AURA_CELL_BUDGET, max(4, width*height//12))
        for source in snap.sources:
            # §12 D 残余（2026-10-20）：激活短光只走光池，不叠呼吸光环。
            # 光环是 NPC / 事件点的身份标记（0.75±0.25 呼吸 + `_darken(.24)`），
            # 短光寿命 <1s 根本「呼吸」不起来；更要命的是半径 3 的暗色环正好
            # 盖在它自己刚照亮的地板上——实测把短光变成「一亮就黑一圈」。
            if source.kind not in ('', 'npc', 'event'):
                continue
            aura_t = int(t * 2) / 2
            pulse = (aura_t + source.phase) % 12.0
            if pulse >= 3.0:
                continue
            # Keep a faint first frame: the breathing envelope must not vanish
            # exactly at phase 0 (tests and the first rendered frame rely on it).
            intensity_top = .45 * (0.2 + 0.8 * math.sin(math.pi * pulse / 3.0))
            if source.compound:
                intensity_top *= .8 + .2 * math.sin(pulse * math.pi)
            falloff = _darken(source.color, .24)
            lut = glow_lut(falloff)
            for dx, dy, dist in _AURA_RING:
                # Two slow glints, separated by a long quiet interval.
                axis = int(source.phase + aura_t//12) % 2
                if dist != 1 or (dx != 0 if axis else dy != 0):
                    continue
                x, y = source.x + dx, source.y + dy
                if not (0 <= x < width and 0 <= y < height):
                    continue
                # Sparse outer rays, reduced low-quality reach, and a hard total
                # budget bound glow coverage even in rooms with many events.
                if dist == AURA_RADIUS and (quality < 2 or dx and dy):
                    continue
                if ((x, y) in snap.aura_protected or (x, y) in snap.fixed_ground or
                        snap.ambient_visible is not None and (x, y) not in snap.ambient_visible or
                        not snap.light_walls and (x, y) in snap.opaque):
                    continue
                if (x, y) not in aura_cells and len(aura_cells) >= aura_budget:
                    continue
                fall = 1.0 - dist / (AURA_RADIUS + 1)
                level = int(fall * intensity_top * (_LUT_STEPS - 1))
                if level <= 1:
                    continue
                style = lut[level]
                # NPC 光环收敛一档，避免盖过事件点。
                if not source.compound and source.color != AURA_COLOR:
                    pass
                overlay[(x, y)] = style
                aura_cells.add((x, y))

        # ---- 火焰格：暖橙底 + 有界的明暗呼吸（设计文档 §1.5）----
        # 每格相位由坐标决定（hash01），整片火不会同步闪；亮度只在
        # [FLAME_LEVEL_MIN, FLAME_LEVEL_MAX] 之间摆，远低于满饱和——
        # 「少量特效」，不抢地形可读性。写在光照之后：火焰格最终由它定色。
        for fx, fy in snap.flames:
            if not (0 <= fx < width and 0 <= fy < height):
                continue
            overlay[(fx, fy)] = flame_glow(fx, fy, t)

        # ---- 弹道回放（2026-09-23）：移动亮点 + 拖尾 + 跳弹火花 + 收尾 ----
        # 速度随路径长度缩放：进度 = age/PROJECTILE_LIFE，当前下标 =
        # floor(进度 × len(cells))。到期后自然从快照消失，无残留状态。
        for proj in snap.projectiles:
            if proj.visual is not None:
                # Styled ASCII glyphs carry foreground highlights, not floor paint.
                continue
            age = t - proj.born
            if age < 0 or age > proj.total_time:
                continue
            lut = glow_lut(proj.color)
            total = len(proj.cells)
            progress = min(1.0, age / proj.flight_time)
            head = min(total - 1, int(progress * total))
            # 亮点 + 前 1~2 格拖尾（100% / 40% / 20% 渐弱）。
            for back, level in (
                (0, _LUT_STEPS - 1),
                (1, max(2, int(_LUT_STEPS * 0.4))),
                (2, max(1, int(_LUT_STEPS * 0.2))),
            ):
                idx = head - back
                if idx < 0 or not proj.cells:
                    continue
                vx, vy = proj.cells[idx]
                if (0 <= vx < width and 0 <= vy < height
                        and (snap.projectile_visible is None or (vx, vy) in snap.projectile_visible)):
                    overlay[(vx, vy)] = lut[level]
            # 跳弹格：亮点越过转向点后，硬面火花短闪一记。
            for idx, vx, vy in proj.bounces:
                spark = age - proj.flight_time * (idx + 1) / max(1, total)
                if (0.0 <= spark <= PROJECTILE_SPARK_LIFE and 0 <= vx < width and 0 <= vy < height
                        and (snap.projectile_visible is None or (vx, vy) in snap.projectile_visible)):
                    overlay[(vx, vy)] = lut[min(_LUT_STEPS - 1, max(1, int(_LUT_STEPS * 0.9)))]
            # 收尾：飞行结束后终点格一记三角包络短闪（range = 空中淡出，无闪）。
            if progress >= 1.0 and proj.end != "range" and proj.end_cell is not None:
                tail = age - proj.flight_time
                env = max(0.0, 1.0 - abs(tail - PROJECTILE_END_LIFE / 2) / (PROJECTILE_END_LIFE / 2))
                if env > 0.05:
                    ex, ey = proj.end_cell
                    flash = PROJECTILE_END_COLORS.get(proj.end, proj.color)
                    flut = glow_lut(flash)
                    if (0 <= ex < width and 0 <= ey < height
                            and (snap.projectile_visible is None or (ex, ey) in snap.projectile_visible)):
                        overlay[(ex, ey)] = flut[max(1, int(env * (_LUT_STEPS - 1)))]

        # ---- 低清醒扫描线（紧急档）：隔行压暗，相位随 t 滚动 ----
        # 由 app 侧通过 fx_scanlines 设置独立控制（默认 True）。
        # ⚠️ 只压暗、**不抹掉**已有底色（2026-09-21 修「主角周围光源渲染消失」）：
        # 旧写法是无条件 `overlay[(x, y)] = CRT_DIM`，而光照池的底色就是
        # `overlay[(x, y)]` 这个值——凡落在扫描行上的光照格，底色被整个删掉，
        # 只剩没有底色的 dim。玩家所在行（以及上下相邻行）一旦是扫描行，
        # 火把光晕就被拦腰截断成黑条；相位每次翻转（旧值 6Hz）光晕整片明灭，
        # 看到的正是「主角周围的光没了」。
        # 现在：有底色的格子改写成 `dim on <压暗后的底色>`——字形和底色一起
        # 压暗（仍是「隔行压暗」的观感），光晕连成一片不再断行。
        if snap.lucidity_tier >= 3 and not getattr(self, "scanlines_disabled", False):
            phase = int(t * CRT_ROLL_HZ) % 2
            for y in range(phase, height, 2):
                for x in range(width):
                    if (x, y) in snap.fixed_ground:
                        continue
                    current = overlay.get((x, y))
                    if current is None or current == CRT_DIM:
                        overlay[(x, y)] = CRT_DIM
                    elif current.startswith(f"{CRT_DIM} "):
                        continue  # 已经是合成样式，别重复压暗
                    else:
                        overlay[(x, y)] = (
                            f"{CRT_DIM} on {_darken(current, CRT_LIGHT_FACTOR)}"
                        )

        # ---- 换层溶解（一次性：检测深度变化，自上而下暗场扫过）----
        if self.last_depth is not None and snap.depth != self.last_depth:
            if self._skip_wipe:
                self._skip_wipe = False
            else:
                self.wipe_born = t
        self.last_depth = snap.depth
        if self.wipe_born is not None:
            age = t - self.wipe_born
            if age <= WIPE_LIFE:
                progress = age / WIPE_LIFE
                front = int((1.0 - abs(0.5 - progress) * 2) * height)  # 先合拢再退场
                lut = glow_lut(WIPE_COLOR)
                for y in range(max(0, front - 3), min(height, front + 1)):
                    for x in range(width):
                        if (x, y) in snap.fixed_ground:
                            continue
                        overlay[(x, y)] = lut[_LUT_STEPS - 1 - abs(front - y)]
            else:
                self.wipe_born = None

        # ---- 液体/气体微抖动（最后写入：硬约束保护区，设计文档 §1.3）----
        # 视野外 / 未显影的格子不上叠加色：那里的基帧是记忆暗色，照真实物质色
        # 上底色会让整张地图的液体气体一起亮起来（"全图液/气"）。
        shown = snap.liquid_gas_shown
        filt = snap.liquid_gas_filter
        for lx, ly, base in snap.liquid_gas:
            if (lx, ly) in snap.fixed_ground:
                continue
            if not (0 <= lx < width and 0 <= ly < height):
                continue
            # 白名单之外的格子直接跳过：它的底色由基帧（记忆/未探索的暗色）决定，
            # 恒定不变——叠加层一介入就既泄漏了视野外的物质种类、又会闪。
            if filt and (lx, ly) not in shown:
                continue
            overlay[(lx, ly)] = liquid_gas_color(base, lx, ly, t)

        # Hurt rings sit above every environmental background. Only walls
        # obstruct propagation; liquid, gas, plants and fixed floors do not.
        self._last_hit_styles = self._hit_ripples(snap, t, width, height)
        overlay.update(self._last_hit_styles)
        # 声波（2026-10-22）：不再扩散成环，只在视野外听到声波的格子叠静态蓝色。
        if snap.waves:
            overlay.update(self._sound_waves(snap, t, width, height))

        # ---- 受创/事件边框闪（最后写入：反馈优先级最高，压过液/气底色与暗角）----
        # 地图边框一圈：受创 = 红色硬双闪（0.9s 两个高斯波峰）；重要事件 =
        # 事件色两次平滑呼吸（1.4s 两个 sin 半波）。多事件并发取包络最强者。
        if self.border_flashes:
            self.border_flashes = [
                entry for entry in self.border_flashes
                if 0.0 <= t - entry[0] <= (
                    BORDER_EVENT_LIFE if entry[2] == "event" else BORDER_FLASH_LIFE
                )
            ]
            winner = None
            winner_level = 0
            for born, color, kind in self.border_flashes:
                age = t - born
                if kind == "event":
                    envelope = abs(math.sin(math.pi * age / BORDER_EVENT_SWELL))
                    envelope *= envelope
                else:
                    envelope = max(
                        math.exp(-((age - peak) ** 2) / (BORDER_FLASH_WIDTH ** 2))
                        for peak in BORDER_FLASH_PEAKS
                    )
                level = int(envelope * (_LUT_STEPS - 1))
                if level > winner_level:
                    winner, winner_level = color, level
            if winner is not None and winner_level > 1:
                flash_lut = glow_lut(winner)
                for x, y in _edge_cells(width, height, 1):
                    overlay[(x, y)] = flash_lut[winner_level]

        # 清醒骤降检测（供下次红脉冲）：骤降本身由调用方比较后写入快照。
        _ = self.last_lucidity
        return overlay

    @staticmethod
    def _sound_waves(snap: FxSnapshot, t: float, width: int, height: int) -> dict:
        """声波静态蓝色标记（2026-10-22）。

        输入快照里的 ``waves`` 已经由调用方过滤成「当前视野之外、声场标准
        听阈能听到」的视口格；这里**不再**按半径扫描、不再做逐环衰减，
        只给这些格叠当前声波蓝色，避免连续移动时每步生成整屏涟漪。

        视野内过滤、玩家自身动作抑制在 App._fx_snapshot / _fx_note_events
        完成——FX 层只负责画点，不自行推断可见性。
        """
        styles: dict[tuple[int, int], str] = {}
        for wave in snap.waves:
            age = t - wave.born
            if not 0 <= age <= SOUND_WAVE_LIFE:
                continue
            for x, y in wave.cells:
                if 0 <= x < width and 0 <= y < height:
                    styles[(x, y)] = SOUND_WAVE_COLOR
        return styles

    @staticmethod
    def _hit_ripples(snap: FxSnapshot, t: float, width: int, height: int) -> dict:
        lut = glow_lut(RIPPLE_COLOR)
        levels = {}
        for hit in snap.hits:
            age = t - hit.born
            if not 0 <= age <= RIPPLE_LIFE:
                continue
            maximum = min(RIPPLE_MAX_RADIUS, max(0.0,
                RIPPLE_MAX_RADIUS if hit.radius is None else hit.radius))
            if not maximum:
                continue
            scale = maximum / RIPPLE_MAX_RADIUS
            radius = age / RIPPLE_LIFE * maximum
            band_width = RIPPLE_WIDTH * scale
            # Scale the soft edge with the wave, so even its faint outer
            # fringe cannot exceed the old full-size ripple's reach.
            reach = math.ceil(radius + band_width * math.sqrt(math.log((_LUT_STEPS - 1) / 3)))
            for y in range(max(0, hit.y-reach), min(height, hit.y+reach+1)):
                for x in range(max(0, hit.x-reach), min(width, hit.x+reach+1)):
                    cell = (x, y)
                    if cell in snap.opaque:
                        continue
                    distance = math.hypot(x-hit.x, y-hit.y)
                    level = int(math.exp(-((distance-radius) / band_width)**2) * (_LUT_STEPS-1))
                    if level <= 2 or not _ripple_path_clear((hit.x, hit.y), cell, snap.opaque):
                        continue
                    levels[cell] = max(levels.get(cell, 0), level)
        return {cell: lut[level] for cell, level in levels.items()}

    def _grids_for(self, width: int, height: int):
        key = (width, height)
        grids = self._grids.get(key)
        if grids is None:
            xs, ys = _np.meshgrid(_np.arange(width, dtype=_np.float32),
                                  _np.arange(height, dtype=_np.float32))
            grids = (xs, ys)
            self._grids[key] = grids
        return grids

    def _light_pool(self, snap: FxSnapshot, t: float, width: int, height: int,
                    overlay: dict[tuple[int, int], str]) -> None:
        """Brogue 式光照池（numpy 向量化；设计文档 §1.2）。

        复杂度与光源数解耦：每个光源只是一次 C 级数组运算；缺 numpy 时
        整条路径关闭（降级=现状）。液体/气体格被 mask 掉——它们只走
        jitter_color 的微抖动（硬约束：不进混色管线）。
        """
        if not HAS_NUMPY or width <= 0 or height <= 0:
            return
        torches: list[tuple] = []
        if snap.player != (-1, -1):
            # 半径 = 玩家视野半径（快照传入）：视野变大 → 衰减变慢；变小 → 变快；
            # d=0 处仍是 1.0×TORCH_BRIGHTNESS，最亮格亮度与半径无关。
            # 快照没给（None）时退回旧的定值 TORCH_RADIUS。
            raw_radius = TORCH_RADIUS if snap.torch_radius is None else float(snap.torch_radius)
            torch_radius = max(TORCH_RADIUS_MIN, raw_radius)
            torches.append((snap.player[0], snap.player[1], torch_radius,
                            TORCH_BRIGHTNESS, TORCH_COLOR))
        for lx, ly, color in snap.lamps:
            torches.append((lx, ly, LAMP_RADIUS, LAMP_BRIGHTNESS, color))
        # 火焰：暖橙小光源。上限保护——一场大火可能上百格，全量进池会造出
        # (L,H,W) 的巨型中间量；超过上限的只着色不发光（视觉上几乎看不出）。
        # §12.6.4：火焰不再「取前 24 格」——那会让火场另一端整片不亮。
        # 超过预算时按步长**均匀降采样**（保留空间分布与两端），预算只降低
        # 装饰采样密度，不改变哪些格在燃烧。
        flames = snap.flames
        if len(flames) > FLAME_LIGHT_MAX:
            step = len(flames) / float(FLAME_LIGHT_MAX)
            flames = tuple(flames[int(i * step)] for i in range(FLAME_LIGHT_MAX))
        for fx, fy in flames:
            torches.append((fx, fy, FLAME_RADIUS, FLAME_BRIGHTNESS, FLAME_COLOR))
        source_start = len(torches)
        for src in snap.sources:  # 稳定意识 NPC 的蓝光池 + 登记过的环境来源
            # §12 A：逐源表现参数。None = 旧行为（灯半径 / NPC 亮度），
            # 因此未改造的调用方与历史快照保持原样。
            radius = LAMP_RADIUS if src.radius is None else max(0.5, float(src.radius))
            brightness = (NPC_LAMP_BRIGHTNESS if src.brightness is None
                          else max(0.0, float(src.brightness)))
            torches.append((src.x, src.y, radius, brightness, src.color,
                            src.kind or "npc"))
        if not torches:
            return
        xs, ys = self._grids_for(width, height)
        # 全光源一次批处理（性能预算 §6：41 光源逐个走 Python 循环时，
        # 每光源 ~8 次 numpy 调用的调度开销就把单帧推到 5ms+）。
        cx = _np.array([tr[0] for tr in torches], dtype=_np.float32)[:, None, None]
        cy = _np.array([tr[1] for tr in torches], dtype=_np.float32)[:, None, None]
        rad = _np.array([tr[2] for tr in torches], dtype=_np.float32)[:, None, None]
        scale = _np.array([tr[3] for tr in torches], dtype=_np.float32)[:, None, None]
        colors = _np.array([_parse_hex(tr[4]) for tr in torches], dtype=_np.float32)  # (L, 3)
        d2 = xs[None, :, :] - cx               # (L, H, W)
        _np.multiply(d2, d2, out=d2)           # in-place：衰减全程只留 2 个大临时量
        ty = ys[None, :, :] - cy
        _np.multiply(ty, ty, out=ty)
        d2 += ty
        del ty
        # Strong highlights stay near their source. A large sight radius retains
        # faint illumination, rather than turning its whole area into a light slab.
        core = _np.maximum(0.0, 1.0-d2 / _np.minimum(rad, 3.0)**2)
        _np.multiply(core, core, out=core)
        core_peak = core.max(axis=0)
        del core
        _np.divide(d2, rad * rad, out=d2)
        _np.subtract(1.0, d2, out=d2)
        _np.maximum(d2, 0.0, out=d2)
        _np.multiply(d2, d2, out=d2)           # 二次衰减
        _np.multiply(d2, scale, out=d2)
        att = d2
        if snap.source_masks:
            # 兼容两种条目：(x, y, allowed) 旧写法与 (x, y, source_id, allowed)
            # 新写法。按身份挂掩码后，同格两个环境来源各自保留传播范围。
            mask_lookup: dict[tuple[int, int, str], frozenset] = {}
            legacy_masks: dict[tuple[int, int], frozenset] = {}
            for entry in snap.source_masks:
                if len(entry) == 4:
                    mx, my, sid, allowed = entry
                    mask_lookup[(mx, my, str(sid))] = allowed
                else:
                    mx, my, allowed = entry
                    legacy_masks[(mx, my)] = allowed
            for index, src in enumerate(snap.sources, start=source_start):
                # 掩码只属于环境来源：同格 NPC/火焰不能被植物灯的掩码削掉
                # （§12 A「同格多来源不能互相吞掉」）。
                if src.kind and src.kind != "environment":
                    continue
                allowed = mask_lookup.get((src.x, src.y, src.source_id))
                if allowed is None:
                    allowed = legacy_masks.get((src.x, src.y))
                if allowed is None:
                    continue
                visible_mask = _np.zeros((height, width), dtype=bool)
                for ax, ay in allowed:
                    if 0 <= ax < width and 0 <= ay < height:
                        visible_mask[ay, ax] = True
                att[index] *= visible_mask
        # The faint outer limit still follows sight falloff; a fixed cap would
        # flatten narrow and wide sight into the same brightness plateau.
        strength = _np.clip(att.max(axis=0)/TORCH_BRIGHTNESS, 0.0, 1.0)
        distant_cap = 22.0 + 2.0*strength
        cap = distant_cap + (LIGHT_MAX_CHANNEL-distant_cap)*core_peak*strength
        # 颜色累积走 BLAS 矩阵乘（(L,H·W)ᵀ × (L,3)）：避免 (L,3,H,W)
        # 这个 L×3 倍大中间量的逐元素广播。
        lum = (att.reshape(len(torches), -1).T @ colors).T.reshape(3, height, width)
        # 噪点扰动 ±6%（随 t 缓慢漂移）：光晕不是完美同心圆。
        # 🔴 t 走 LIGHT_NOISE_HZ 的台阶（见该常量的说明）——连续 t 会让叠加层
        # 每帧都变，下游的内容去重与写回节流就全都失效了。
        if LIGHT_NOISE_HZ > 0:
            t_noise = int(t * LIGHT_NOISE_HZ) / LIGHT_NOISE_HZ
        else:  # 0/负 = 完全静态的噪点场（想再省那点写回时用）
            t_noise = 0.0
        noise = _np.sin(xs * 12.9898 + ys * 78.233 + t_noise * 0.7)
        lum *= 1.0 + 0.06 * noise
        # Keep the bounded core alive too: normalization must not cancel every
        # noise step on saturated cells. Leave the faint rim stable/readable.
        cap = distant_cap + (cap-distant_cap)*(0.94+0.06*noise)
        blocked = _np.zeros((height, width), dtype=bool)
        # 受光表面（地面 + §12 C 的普通墙面）先占位：这些格是要被照亮的，
        # 不能因为同格是墙就被 opaque 挡掉。
        surfaces = {(x, y): _parse_hex(color) for x, y, color in snap.surface_bgs}
        for lx, ly, _base in snap.liquid_gas:
            if 0 <= lx < width and 0 <= ly < height:
                blocked[ly, lx] = True
        if not snap.light_walls:
            for ox, oy in snap.opaque:
                if 0 <= ox < width and 0 <= oy < height:
                    if (ox, oy) in surfaces:
                        continue  # §12 C：受光墙面照常接收彩光
                    blocked[oy, ox] = True
        if snap.ambient_visible is not None:
            hidden = _np.ones((height, width), dtype=bool)
            for vx, vy in snap.ambient_visible:
                if 0 <= vx < width and 0 <= vy < height:
                    hidden[vy, vx] = False
            blocked |= hidden
        for xx, yy in snap.fixed_ground:
            if 0 <= xx < width and 0 <= yy < height:
                blocked[yy, xx] = True
        lum *= LIGHT_FLOOR
        # Scale all three channels together so overlapping warm/cool lights keep
        # their hue. The cap affects ambience, not impacts, flames or projectiles.
        peak = lum.max(axis=0)
        lum *= _np.minimum(1.0, cap / _np.maximum(peak, 1.0))
        ints = _np.clip(lum.round().astype(_np.int32), 0, LIGHT_MAX_CHANNEL)
        # 🔴 放行门槛必须≥底色（2026-09-21，区域底色上线后新增）：
        # 光池写的是**绝对底色**，光本身是暖色、越往外越弱。底色不再恒等于近黑
        # （1 区灰 / 2 区深蓝）后，「微弱光」的三通道和会**低于底色**——照旧放行
        # 就等于在主角周围画一圈比地图底更暗的暗环。这里把门槛提到
        # 「至少不比底色暗」，颜色公式一字未改，只是不再用光去压暗底色。
        # 3 区（底色仍是原来的黑）只有门槛从 24 抬到 56，外圈本就更暗的那几格
        # 现在正确地露出底色，观感只会更干净。
        base_sum = sum(_parse_hex(snap.base_bg))
        # 只写「亮且未被 mask」的格子：逐格 numpy 标量索引（~200ns×3/格）
        # 会把千级亮格推到毫秒级——一次性 tolist + 十六进制查表代替。
        keep = (~blocked) & (ints.sum(axis=0) >= max(LIGHT_MIN_SUM, base_sum))
        coords = _np.argwhere(keep).tolist()
        vals = ints[:, keep].T.tolist()
        h02 = _HEX02
        if snap.bg_zones:
            # 底色带模式（千禧园）：光强加在 zone 基色上（相加、cap 255）——
            # 草地绿透过光池可见，光只负责「照亮」而非「换成主梦的暖色」。
            # zone 色值有限（≤6 条），先解析成元组再逐格查。
            parsed = tuple((x0, y0, x1, y1, _parse_hex(color))
                           for x0, y0, x1, y1, color in snap.bg_zones)
            for (yy, xx), (r, g, b) in zip(coords, vals):
                base = (0, 0, 0)  # zone 外：基色为黑，混合结果=纯光色（旧行为）
                for x0, y0, x1, y1, (zr, zg, zb) in parsed:
                    if x0 <= xx <= x1 and y0 <= yy <= y1:
                        base = (zr, zg, zb)
                        break
                cr = min(255, base[0] + r)
                cg = min(255, base[1] + g)
                cb = min(255, base[2] + b)
                overlay[(xx, yy)] = "#" + h02[cr] + h02[cg] + h02[cb]
        else:
            for (yy, xx), (r, g, b) in zip(coords, vals):
                if (xx, yy) in surfaces:
                    base = surfaces[(xx, yy)]
                    r, g, b = tuple(min(255, c + round(light * (255-c) / 255 * .35))
                                    for c, light in zip(base, (r, g, b)))
                overlay[(xx, yy)] = "#" + h02[r] + h02[g] + h02[b]

    def note_lucidity(self, lucidity: int, t: float) -> bool:
        """比较清醒度：骤降（单帧 −8 以上）返回 True。

        🔴 2026-09-21 起骤降**不再触发任何特效**（红脉冲已删，玩家要求
        「受伤时的红色涟漪去除」）；本方法只保留取样与判定语义——
        首次取样只记录不判定：引擎初值不是「上一次的清醒度」，拿它对比
        会在载入存档/重进游戏的第一帧制造虚假骤降。
        """
        if self.last_lucidity is None:
            self.last_lucidity = lucidity
            return False
        dropped = self.last_lucidity - lucidity >= 8
        self.last_lucidity = lucidity
        return dropped


_EDGE_CELLS_CACHE: dict[tuple[int, int, int], list[tuple[int, int]]] = {}


def _edge_cells(width: int, height: int, ring: int) -> list[tuple[int, int]]:
    """视口外圈第 1/2 环的格子（暗角作用域；按尺寸+环缓存）。"""
    key = (width, height, ring)
    cells = _EDGE_CELLS_CACHE.get(key)
    if cells is None:
        cells = []
        for y in range(height):
            for x in range(width):
                edge = min(x, y, width - 1 - x, height - 1 - y)
                if 0 <= edge < ring:
                    cells.append((x, y))
        _EDGE_CELLS_CACHE[key] = cells
    return cells


