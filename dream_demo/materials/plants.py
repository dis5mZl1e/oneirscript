"""植物：一类可穿行的固体地形（不属于墙体，见 Cell.plant 字段）。

植物是「固体」但生物可以直接穿过；大部分 1 格高，少数 2 格高（遮挡视线）。
遇到液体即消失（液面漫过、容器破出都算）；可燃植物点着后逐回合烧尽。
站在植物上左键自己所在格（或按 Enter/底栏「行动」）可以把它拔掉。

`Cell.plant` 只存一个整数「植物码」（0 = 无），名字/颜色/高度一律经
:func:`plant_def_for` 反查，避免各处重复写「== 1 就低草否则高丛」——
新植物（发光地衣 / 蘑菇）因此不必改动存档格式与渲染层。

各植物的差异集中在 :class:`PlantDef` 的旗标上：

- ``height``：2 格高的植物遮挡视线（高丛）；
- ``glow``：发光（只有发光地衣；光照规则见 core/vision/glow.py，与征兆无关）；
- ``immune_liquid`` / ``immune_fire``：不被液体淹死 / 不被火焰烧尽（蘑菇）；
- ``trample_to``：被踩踏之后变成的码（高丛踩折成低草；其余踩上去不变）。

生成：在液体/气体投放之后、生物投放之前进行，只落在没有液体的开放空地上
（掉落物在更晚的阶段投放，落在植物上互不妨碍）。大部分植物连片生长，
少量单独出现。覆盖率按层取（:func:`plant_profile`）：只有「繁茂」层保持
0.25 的高覆盖，普通层与其余带修饰符的层都已压低；种类按
:attr:`PlantDef.weight` 抽签（低草 7 : 高丛 3 : 发光地衣 1 : 蘑菇 1）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlantDef:
    key: str            # 符号键（symbols.py 的 "plant.*"）
    name: str
    color: str
    code: int           # 存档里 Cell.plant 的取值（0 = 无植物，见下方 PLANT_CODES）
    height: int         # 1 = 矮（不挡视线），2 = 高（遮挡视线）
    weight: int         # 生成权重：低草远多于其它
    glow: bool = False          # 发光（发光地衣 → core/vision/glow.py）
    immune_liquid: bool = False  # 液面漫过也不消失（蘑菇）
    immune_fire: bool = False    # 火焰点不燃（蘑菇）
    trample_to: int | None = None  # 被踩踏后变成的码；None = 踩了不变
    # 区域登记（条件限制）：(起始层, 终止层, 渗出范围)。None = 常规植物（全层）。
    region: tuple[int, int, int] | None = None
    # 位面专属登记：非空时只有这些位面（realm_id）的生成器允许种下本植物，
    # 主梦与其它位面的植物池一律排除（与 WallDef/LiquidDef/GasDef 同口径）。
    spawn_realms: tuple[str, ...] = ()
    # ---- 稀有植物的功能（2026-09-18 重做）----
    # 玩家反馈：稀有植物原本只是「拔起 → 属性 +N」，与一瓶消耗品没区别。现在
    # 每株的功能写在定义里，只允许三种形态（可以并存）：
    #   ① 获得**独特征兆**（正面或负面）→ uproot_portent
    #   ② 拔起后获得**物品形式的消耗品**→ uproot_item
    #   ③ 拔起 / 踩踏时**释放少量气体或液体**→ uproot_release / trample_release
    # 时长一律取征兆定义自己的 duration；释放量一律「少量」（默认 4）。
    uproot_portent: str | None = None
    uproot_item: str | None = None
    uproot_release: str | None = None
    uproot_amount: int = 4
    # 踩踏效果：**对任何踩上来的生物生效**（玩家与失控意识一视同仁）——
    # 「踩坏它就该被它咬一口」对异象同样成立（见 PortentMixin.apply_plant_trample）。
    trample_portent: str | None = None
    trample_release: str | None = None
    trample_amount: int = 3
    # 踩踏直接受创（荆棘藤：穿越刮擦 1 点清醒创伤）。玩家与失控意识一视同仁；
    # 对玩家扣清醒度、对异象扣完整度（走 apply_plant_trample 的既有结算）。
    trample_lucidity: int = 0
    # 实际踩碎时的一次性声响半径（docs 261022 §13.2／盘点 §5）：0 = 踩它不发声。
    # 只在「这一次真的把它踩坏」时发一次，同一格重复踩不会反复刷声源。
    trample_noise: int = 0


# 植物码（Cell.plant）——1/2 是既有存档沿用的旧值，不要改动。
PLANT_CODE_SHORT = 1
PLANT_CODE_TALL = 2
PLANT_CODE_LICHEN = 3
PLANT_CODE_MUSHROOM = 4

# 发光地衣的图标沿用低草字形（symbols.py 里 "plant.lichen" 也是 ❀），
# 只有颜色换成亮黄——正是「低草换成亮黄色」的写法。
PLANT_SHORT = PlantDef("plant.short", "低草", "#5da24a", PLANT_CODE_SHORT, 1, 7)
PLANT_TALL = PlantDef("plant.tall", "高丛", "#3d8f3d", PLANT_CODE_TALL, 2, 3, trample_to=PLANT_CODE_SHORT)
PLANT_LICHEN = PlantDef(
    "plant.lichen", "发光地衣", "bright_yellow", PLANT_CODE_LICHEN, 1, 1, glow=True
)
PLANT_MUSHROOM = PlantDef(
    "plant.mushroom", "蘑菇", "#a9743f", PLANT_CODE_MUSHROOM, 1, 1,
    immune_liquid=True, immune_fire=True,
)
# ---- 无意识领域：魔法/神秘背景稀有植物（leak=3）----
# 生成概率比发光地衣低一个量级（单独走「稀有植物门」，见 RARE_PLANT_CHANCE），
# 且 85% 单株、极少连片。机制分三类：贴近沾染（mandrake/曼陀罗/冥河柳/夜皇后/
# 缚魂藤/千梦铃兰）、拔除收益（曼德拉草/贤者之苔/镜面兰）、光照（夜皇后）。
PLANT_CODE_MANDRAKE = 5
PLANT_CODE_DATURA = 6
PLANT_CODE_STYX = 7
PLANT_CODE_NIGHT_QUEEN = 8
PLANT_CODE_SOUL_VINE = 9
PLANT_CODE_SAGE_MOSS = 10
PLANT_CODE_MIRROR_ORCHID = 11
PLANT_CODE_LILY = 12

# 区域登记：曼陀罗/冥河柳/缚魂藤放宽到幻觉空间+无意识领域（11–27），
# 其余仍严格属于无意识领域（21–27）；区域外一律按层数距离衰减。
PLANT_REGION_UNCONSCIOUS = (21, 27, 3)
PLANT_REGION_HALLUCINATION = (11, 27, 3)

PLANT_MANDRAKE = PlantDef(
    "plant.mandrake", "曼德拉草", "#b8a878", PLANT_CODE_MANDRAKE, 2, 1,
    region=PLANT_REGION_UNCONSCIOUS,
    # 拔起来是一声尖啸：散出噩梦气息（原版传说里就是「拔出来会尖叫」）。
    uproot_release="噩梦气息", uproot_amount=5,
)
PLANT_DATURA = PlantDef(
    "plant.datura", "曼陀罗", "#c8a0d8", PLANT_CODE_DATURA, 1, 1,
    region=PLANT_REGION_HALLUCINATION,
    uproot_portent="datura_sleep",  # 幻觉安眠：每一次行动多沉 1 回合
)
PLANT_STYX = PlantDef(
    "plant.styx", "冥河柳", "#6a8a7a", PLANT_CODE_STYX, 2, 1,
    region=PLANT_REGION_HALLUCINATION,
    uproot_portent="styx_weight",   # 冥河之重：移动 +0.5
    trample_release="无念黑渊", trample_amount=2,  # 踩断柳枝，河水渗出来一点点
)
PLANT_NIGHT_QUEEN = PlantDef(
    "plant.night_queen", "夜皇后", "#7a4a9a", PLANT_CODE_NIGHT_QUEEN, 1, 1, glow=True,
    region=PLANT_REGION_UNCONSCIOUS,
    uproot_portent="queen_night",   # 月下：视野翻倍
)
PLANT_SOUL_VINE = PlantDef(
    "plant.soul_vine", "缚魂藤", "#4a6a5a", PLANT_CODE_SOUL_VINE, 1, 1,
    immune_fire=True, region=PLANT_REGION_HALLUCINATION,
    uproot_portent="soul_bind",
    # 踩上去就缠脚——**对失控意识同样生效**（这条以前只对玩家成立）。
    trample_portent="soul_bind",
)
PLANT_SAGE_MOSS = PlantDef(
    "plant.sage_moss", "贤者之苔", "#d8d0a0", PLANT_CODE_SAGE_MOSS, 1, 1,
    region=PLANT_REGION_UNCONSCIOUS,
    uproot_item="sage_powder",
)
PLANT_MIRROR_ORCHID = PlantDef(
    "plant.mirror_orchid", "镜面兰", "#c0d8e8", PLANT_CODE_MIRROR_ORCHID, 1, 1,
    region=PLANT_REGION_UNCONSCIOUS,
    uproot_portent="mirror_stance",  # 镜面架势（带层数，反弹下一次打击）
)
PLANT_LILY = PlantDef(
    "plant.lily", "千梦铃兰", "#e8d8f0", PLANT_CODE_LILY, 1, 1,
    region=PLANT_REGION_UNCONSCIOUS,
    uproot_item="dream_bell",
)

# ---- 2026-09-18：浅层梦境（1–10）与幻觉空间（11–20）的区域稀有植物 ----
# 之前稀有魔法植物只落在 11–27 层，浅层完全没有「拔除收益」的惊喜；
# 这一批把稀有单株铺到前两个区域（leak=2：区域外 2 层内仍偶见）。
PLANT_REGION_SHALLOW = (1, 10, 2)
PLANT_REGION_HALLUC_ONLY = (11, 20, 2)
PLANT_CODE_MINT = 13
PLANT_CODE_AMBER_FERN = 14
PLANT_CODE_DAISY = 15
PLANT_CODE_GLASS_SHROOM = 16
PLANT_CODE_WHISPER_FERN = 17
# ---- 内容扩展包 v1（2026-09-20）：四株新稀有植物 + 两个蘑菇换色变体 ----
# 规格书写的是码 13-16，但那四个码已被铃兰薄荷/琥珀蕨/忘忧雏菊/彩玻菌占用
#（规格基于旧导出），顺延为 18-21；月光蕈/空鼓菌占 22/23。
PLANT_CODE_DREAM_GRASS = 18
PLANT_CODE_THORN_VINE = 19
PLANT_CODE_VANE_MOSS = 20
PLANT_CODE_WAX_BLOOM = 21
PLANT_CODE_MOON_SHROOM = 22
PLANT_CODE_HOLLOW_SHROOM = 23

PLANT_MINT = PlantDef(
    "plant.mint", "铃兰薄荷", "#a8d8b8", PLANT_CODE_MINT, 1, 1,
    region=PLANT_REGION_SHALLOW,
    uproot_item="mint_dew",
)
PLANT_AMBER_FERN = PlantDef(
    "plant.amber_fern", "琥珀蕨", "#d8a860", PLANT_CODE_AMBER_FERN, 1, 1,
    region=PLANT_REGION_SHALLOW,
    uproot_release="晨霜清气", uproot_amount=6,
)
PLANT_DAISY = PlantDef(
    "plant.daisy", "忘忧雏菊", "#e8e8a8", PLANT_CODE_DAISY, 1, 1,
    region=PLANT_REGION_SHALLOW,
    uproot_portent="worry_free",
)
PLANT_GLASS_SHROOM = PlantDef(
    "plant.glass_shroom", "彩玻菌", "#e070d0", PLANT_CODE_GLASS_SHROOM, 1, 1, glow=True,
    immune_fire=True, region=PLANT_REGION_HALLUC_ONLY,
    uproot_item="glass_shard",
    # 踩碎时清脆地响一声：R3 只在这一次真的踩坏时发，踩碎后换成低草，
    # 同一格再踩既不响声也不重复释放呢喃（docs 261022 §13.2）。
    trample_to=PLANT_CODE_SHORT, trample_noise=3,
    trample_release="呢喃", trample_amount=3,
)
PLANT_WHISPER_FERN = PlantDef(
    "plant.whisper_fern", "低语蕨", "#8ab8d8", PLANT_CODE_WHISPER_FERN, 2, 1,
    region=PLANT_REGION_HALLUC_ONLY,
    uproot_portent="whispering",
)
# 全区域稀有植物（规格未限定区域，登记 1-27 沿 region_falloff 衰减）。
PLANT_REGION_ALL = (1, 27, 3)
PLANT_DREAM_GRASS = PlantDef(
    "plant.dream_grass", "捕梦草", "#6a9a7a", PLANT_CODE_DREAM_GRASS, 1, 1,
    region=PLANT_REGION_ALL,
    # 踩踏：缠住——下回合无法移动（move_time=99 在 1 回合寿命内即「钉在原地」）。
    trample_portent="snared",
)
PLANT_THORN_VINE = PlantDef(
    "plant.thorn_vine", "荆棘藤", "#5a7a4a", PLANT_CODE_THORN_VINE, 2, 1,
    region=PLANT_REGION_ALL,
    trample_lucidity=1,  # 穿越：受 1 点清醒创伤（刮擦）
)
PLANT_VANE_MOSS = PlantDef(
    "plant.vane_moss", "风向标苔", "#a8c8a0", PLANT_CODE_VANE_MOSS, 1, 1,
    region=PLANT_REGION_ALL,
    uproot_portent="vane_sense",
)
PLANT_WAX_BLOOM = PlantDef(
    "plant.wax_bloom", "融蜡花", "#f0d890", PLANT_CODE_WAX_BLOOM, 1, 1, glow=True,
    region=PLANT_REGION_ALL,
    uproot_item="molten_candle",  # 拔除获得 1 件「熔融蜡烛」液体弹（可燃）
)
# 蘑菇换色变体：字形/机制与蘑菇完全一致（抗液抗火/可穿行），只换颜色。
PLANT_MOON_SHROOM = PlantDef(
    "plant.moon_shroom", "月光蕈", "#e0e8f0", PLANT_CODE_MOON_SHROOM, 1, 1,
    immune_liquid=True, immune_fire=True, region=(11, 20, 3),
)
PLANT_HOLLOW_SHROOM = PlantDef(
    "plant.hollow_shroom", "空鼓菌", "#c8b890", PLANT_CODE_HOLLOW_SHROOM, 1, 1,
    immune_liquid=True, immune_fire=True, region=(1, 10, 3),
)

# ---- 梦中梦·千禧园（2026-10-10）：realm 专属植物（码 24/25）----
# 只由 millennium_park 生成器种下；不进 COMMON/RARE 池（主梦不生成），
# 但必须进 PLANT_KINDS（plant_def_for 反查：渲染/踩踏结算都要认码）。
PLANT_CODE_MILLENNIUM_GRASS = 24
PLANT_CODE_BUBBLE_ALGAE = 25
PLANT_MILLENNIUM_GRASS = PlantDef(
    "plant.millennium_grass", "千禧蒲草", "#7ac86a", PLANT_CODE_MILLENNIUM_GRASS, 2, 1,
    # 高草拂脚：踩过沾「冥河之重」式迟滞（移动 +0.5，复用既有征兆）。
    trample_portent="styx_weight",
)
PLANT_BUBBLE_ALGAE = PlantDef(
    "plant.bubble_algae", "气泡藻", "#a0d8c8", PLANT_CODE_BUBBLE_ALGAE, 1, 1,
    immune_liquid=True,  # 贴水低丛，液面漫过也不散
)

PLANT_KINDS: tuple[PlantDef, ...] = (
    PLANT_SHORT, PLANT_TALL, PLANT_LICHEN, PLANT_MUSHROOM,
    PLANT_MANDRAKE, PLANT_DATURA, PLANT_STYX, PLANT_NIGHT_QUEEN,
    PLANT_SOUL_VINE, PLANT_SAGE_MOSS, PLANT_MIRROR_ORCHID, PLANT_LILY,
    PLANT_MINT, PLANT_AMBER_FERN, PLANT_DAISY, PLANT_GLASS_SHROOM,
    PLANT_WHISPER_FERN,
    PLANT_DREAM_GRASS, PLANT_THORN_VINE, PLANT_VANE_MOSS, PLANT_WAX_BLOOM,
    PLANT_MOON_SHROOM, PLANT_HOLLOW_SHROOM,
    PLANT_MILLENNIUM_GRASS, PLANT_BUBBLE_ALGAE,
)

# 常规抽签池（低草/高丛/地衣/蘑菇）——稀有魔法植物不走这里。
COMMON_PLANT_KINDS: tuple[PlantDef, ...] = (
    PLANT_SHORT, PLANT_TALL, PLANT_LICHEN, PLANT_MUSHROOM,
)
# 稀有魔法植物池（各自带区域登记；单独门生成）。
RARE_PLANT_KINDS: tuple[PlantDef, ...] = (
    PLANT_MANDRAKE, PLANT_DATURA, PLANT_STYX, PLANT_NIGHT_QUEEN,
    PLANT_SOUL_VINE, PLANT_SAGE_MOSS, PLANT_MIRROR_ORCHID, PLANT_LILY,
    PLANT_MINT, PLANT_AMBER_FERN, PLANT_DAISY, PLANT_GLASS_SHROOM,
    PLANT_WHISPER_FERN,
    PLANT_DREAM_GRASS, PLANT_THORN_VINE, PLANT_VANE_MOSS, PLANT_WAX_BLOOM,
    PLANT_MOON_SHROOM, PLANT_HOLLOW_SHROOM,
)

# 码 → 定义。1 格高的植物共用 height=1，因此不能用高度反查种类，
# 表是唯一的种类来源（旧存档里的 1/2 依旧落在这张表上）。
_PLANT_BY_CODE = {definition.code: definition for definition in PLANT_KINDS}

# ---- 稀有魔法植物 ----
# 稀有植物门：每个 patch 先掷这道门（0.8%），命中才从稀有池抽——
# 比发光地衣（普通抽签权重 1）再低一个量级，且 85% 单株。
# 稀有门概率：期望每层 4~5 株（目标株数 ~54 × 8%）——此前 0.8% 配上
# 「种类均匀抽 × 区域衰减二次惩罚」，实测多数整层颗粒无收（2026-09-19 调整）。
RARE_PLANT_CHANCE = 0.12
RARE_PLANT_SINGLE_CHANCE = 0.85

_PLANT_WEIGHTS = tuple(definition.weight for definition in COMMON_PLANT_KINDS)


def plant_kind(rng_roll: float, *, realm_id: str = "") -> PlantDef:
    """按权重抽一种常规植物（稀有魔法植物走 rare_plant_kind 单独门）。

    位面专属植物（spawn_realms 非空）不进主梦与其它位面的抽签池。
    """
    pool = [
        (definition, weight)
        for definition, weight in zip(COMMON_PLANT_KINDS, _PLANT_WEIGHTS)
        if not definition.spawn_realms or realm_id in definition.spawn_realms
    ]
    total = sum(weight for _, weight in pool)
    cursor = rng_roll * total
    for definition, weight in pool:
        cursor -= weight
        if cursor < 0:
            return definition
    return PLANT_SHORT


def rare_plant_kind(rng_roll: float, depth: int, falloff, *, realm_id: str = "") -> PlantDef | None:
    """按层抽一种稀有魔法植物（只在该层可生成的种类里均匀挑）。

    区域外按各植物自己的登记衰减（权重为 0 的不参与）；位面专属植物
    （spawn_realms 非空）不进主梦与其它位面的候选。全部不可生成时
    返回 None（该 patch 落空）。
    """
    eligible = [
        definition for definition in RARE_PLANT_KINDS
        if definition.region is not None and falloff(depth, *definition.region) > 0
        and (not definition.spawn_realms or realm_id in definition.spawn_realms)
    ]
    if not eligible:
        return None
    index = min(len(eligible) - 1, int(rng_roll * len(eligible)))
    return eligible[index]


def rare_plant_weight(definition: PlantDef, depth: int, falloff) -> float:
    """稀有植物在某层的衰减权重（按各自区域登记）。"""
    if definition.region is None:
        return 0.0
    return falloff(depth, *definition.region)


def plant_def_for(code: int) -> PlantDef:
    """按 Cell.plant 存的植物码反查定义（未知码回退低草）。"""
    return _PLANT_BY_CODE.get(int(code), PLANT_SHORT)


def plant_height(code: int) -> int:
    """植物占几格高（2 = 遮挡视线）。0 = 无植物时为 0。"""
    return plant_def_for(code).height if code else 0


def plant_glows(code: int) -> bool:
    """这株植物是否发光（发光地衣）。"""
    return bool(code) and plant_def_for(code).glow


def plant_survives_liquid(code: int) -> bool:
    """液面漫过时是否存活（蘑菇不被液体破坏）。"""
    return bool(code) and plant_def_for(code).immune_liquid


def plant_survives_fire(code: int) -> bool:
    """火焰烧到时是否存活（蘑菇不被火焰破坏，也不可燃）。"""
    return bool(code) and plant_def_for(code).immune_fire


def plant_burns(code: int) -> bool:
    """这株植物是否可燃（见 core/materials_sim._cell_is_flammable）。"""
    return bool(code) and not plant_def_for(code).immune_fire


def trampled_code(code: int) -> int:
    """被踩踏之后这一格该变成什么植物码（低草/地衣/蘑菇踩了不变）。"""
    if not code:
        return 0
    result = plant_def_for(code).trample_to
    return code if result is None else result


@dataclass(frozen=True)
class PlantProfile:
    """一个楼层的植物生成参数（覆盖率 + 连片/单株生成率）。"""

    coverage: float       # 目标覆盖率（占可种植开放格）
    single_chance: float  # 单株概率（越高越零散）
    patch_min: int        # 连片规模下限
    patch_max: int        # 连片规模上限


# 常规楼层的植物覆盖率：开放空地的 7%（带修饰符、但不是「繁茂」的那些层）。
PLANT_COVERAGE = 0.07
# 「繁茂」修饰符：覆盖率提到 25%（唯一的高覆盖层，不参与下调）。
LUSH_PLANT_COVERAGE = 0.25
# 连片patch的规模范围；单株概率（少量单独生成）。
PATCH_MIN_SIZE = 3
PATCH_MAX_SIZE = 14
SINGLE_PLANT_CHANCE = 0.2

# 普通层（没有任何修饰符）：植物更稀疏、更零散——覆盖率再下调一档，单株更多、
# 连片更小，避免大片绿地把空地填满。
ORDINARY_PLANT_COVERAGE = 0.045
ORDINARY_SINGLE_PLANT_CHANCE = 0.35
ORDINARY_PATCH_MIN_SIZE = 2
ORDINARY_PATCH_MAX_SIZE = 8

# 带修饰符的楼层（除繁茂外）：沿用原先的常规参数。
MODIFIED_PLANT_PROFILE = PlantProfile(
    PLANT_COVERAGE, SINGLE_PLANT_CHANCE, PATCH_MIN_SIZE, PATCH_MAX_SIZE
)
LUSH_PLANT_PROFILE = PlantProfile(
    LUSH_PLANT_COVERAGE, SINGLE_PLANT_CHANCE, PATCH_MIN_SIZE, PATCH_MAX_SIZE
)
ORDINARY_PLANT_PROFILE = PlantProfile(
    ORDINARY_PLANT_COVERAGE,
    ORDINARY_SINGLE_PLANT_CHANCE,
    ORDINARY_PATCH_MIN_SIZE,
    ORDINARY_PATCH_MAX_SIZE,
)


def plant_profile(modifier: str) -> PlantProfile:
    """按楼层修饰符取植物生成参数（空字符串 = 普通层）。"""
    if modifier == "繁茂":
        return LUSH_PLANT_PROFILE
    if modifier:
        return MODIFIED_PLANT_PROFILE
    return ORDINARY_PLANT_PROFILE
