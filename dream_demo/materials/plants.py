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
class PlantRelease:
    """「被破坏那一下」寄存物的释出配方（docs 2026-10-26 §3.4）。

    踩踏与拔除**共享同一次预算**：`cell.plant_state['released']` 置 1 之后，
    另一条路径不会再释出第二份。执行顺序由 `core/plant_release.py` 固定
    （移除本株 → 液体 → 点火 → 放电 → 发声 → 削耐久 → 挂征兆），这里的字段
    只声明「放什么、放多少、最多几格」，顺序不随字段声明改变。
    """

    # both / trample / uproot：哪条路径允许释出。
    trigger: str = "both"
    gas: str = ""          # 气体名（须在 GAS_DEFINITIONS 里）
    liquid: str = ""       # 液体名（须在 LIQUID_DEFINITIONS 里）
    amount: int = 0        # 材料单位；摊到最多 max_cells 格
    ignite: int = 0        # 最多点燃几格（0 = 不放火）
    electric: int = 0      # 最多电击几格（0 = 不放电）
    push_gas: int = 0      # 把本格已有的同种气体推向朝向邻格（单位数）
    integrity: int = 0     # 每格削减的地形耐久（0 = 不削）
    sound: int = 0         # 声径（1 = T1 环境短声，6 = T2 一次性巨响）
    portent: str = ""      # 追加挂上的征兆（如 snared）
    max_cells: int = 1     # R1 内最多作用格数（含本格；1 = 全落在本格）

    def allows(self, trigger: str) -> bool:
        return self.trigger == "both" or self.trigger == trigger


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

    # ---- 可穿行地形的常驻行为（docs 2026-10-26 植物地形扩展）----
    # 全部按「真实位置 + 源株状态」现算，不挂不会消失的征兆：
    # 进格加时（本格或 R1）与减声（本格或 R1）都由移动路径每次重新查询。
    move_penalty: float = 0.0      # 进入受影响格时额外耗时的世界回合
    move_penalty_radius: int = 0   # 0 = 只作用于本格；1 = 本格与相邻一圈
    step_quiet: int = 0            # 移动脚步声径减多少格（0 = 不减）
    step_quiet_radius: int = 0     # 0 = 只压本格；1 = R1（留白絮）
    step_quiet_dark: bool = False  # 仅当本格没有机械照明时生效（月光蕈）
    # 导电介质：登记后本格参与 `_conductive_cell` 的导通判定（自己不发电）。
    conductive: bool = False
    # 有限吸收：每世界回合从本格或 R1 吸 1 单位，总预算存在格子里，耗尽不恢复。
    absorb_gas: tuple[str, ...] = ()
    absorb_gas_budget: int = 0
    absorb_liquid: tuple[str, ...] = ()
    absorb_liquid_budget: int = 0
    # 定向搬气：每回合把本格 1 单位气体推向朝向邻格，总预算 push_gas_budget。
    push_gas_budget: int = 0
    # 净化：每回合把 R1 内一项目标征兆缩短 1 回合，总预算 purify_budget。
    purify_budget: int = 0
    # 机械照明视距加值修正（负值 = 削弱；0 = 不修正）。
    sight_bonus_delta: int = 0
    # 本格向四邻的气体扩散预算除数（2 = 减半）。
    gas_flow_divisor: int = 1
    # 被破坏那一下的释出配方（None = 不释出，只按 trample_to 形变/移除）。
    release: PlantRelease | None = None
    # ---- 材质（docs 2026-10-26 §3.3）----
    # 「植物」是分类，不是材质：可燃性、能不能干枯、拔除时的说法都要按材质
    # 判，不能因为字段叫 plant 就默认「是纤维、能烧、能枯萎」。
    #   fiber    纤维/纸/棉：草、散页、装订线、滤绒、留白絮 → 可燃、可枯萎
    #   plastic  聚合物软带：磁带须、错帧片 → 可燃、干不了（只会熔化）
    #   metal    金属/覆银薄片：拨号簧、导电脚线、热熔须、光阑褶 → 不可燃、不干枯
    #   fungus   菌质：蘑菇变体 → 沿用各自的免疫旗标，套不上纸类燃料
    #   membrane 膜囊/柔性耗材：气泡藻、压差囊、滴注囊、融蜡花 → 囊里有液，干不了
    material_kind: str = "fiber"

    @property
    def witherable(self) -> bool:
        """能不能走「枯萎」（把燃料抬到干枯档）。

        只有纤维/纸/棉能真的干；而且本来就点不着的株（免疫火焰）干枯了也
        没有任何后果，给它是假效果，一并拒绝。
        """
        return self.material_kind == "fiber" and not self.immune_fire

    @property
    def flammable(self) -> bool:
        """按材质与旗标判可燃，而不是「有 plant 字段就是草」。"""
        return self.material_kind not in ("metal",) and not self.immune_fire

    @property
    def has_periodic(self) -> bool:
        """是否有需要逐回合结算的常驻效果。"""
        return bool(
            self.absorb_gas_budget or self.absorb_liquid_budget
            or self.push_gas_budget or self.purify_budget
        )


# 植物码（Cell.plant）——1/2 是既有存档沿用的旧值，不要改动。
PLANT_CODE_SHORT = 1
PLANT_CODE_TALL = 2
PLANT_CODE_LICHEN = 3
PLANT_CODE_MUSHROOM = 4

# 发光地衣的图标沿用低草字形（symbols.py 里 "plant.lichen" 也是 ❀），
# 只有颜色换成亮黄——正是「低草换成亮黄色」的写法。
PLANT_SHORT = PlantDef(
    "plant.short", "低草", "#5da24a", PLANT_CODE_SHORT, 1, 7,
    # E01：踩在自己这格的低草上脚步更闷——消音沿用材料/装备那条降噪通道，
    # 但不压攻击、爆炸、机关与喊声（只作用于 "step" 类声源）。
    step_quiet=1,
)
PLANT_TALL = PlantDef("plant.tall", "高丛", "#3d8f3d", PLANT_CODE_TALL, 2, 3, trample_to=PLANT_CODE_SHORT)
PLANT_LICHEN = PlantDef(
    "plant.lichen", "发光地衣", "bright_yellow", PLANT_CODE_LICHEN, 1, 1, glow=True
)
PLANT_MUSHROOM = PlantDef(
    "plant.mushroom", "蘑菇", "#a9743f", PLANT_CODE_MUSHROOM, 1, 1,
    immune_liquid=True, immune_fire=True, material_kind="fungus",
    # E04：菌盖微孔吸雾。每回合吸 1 单位，全株共 3；只认两种有机制的气体，
    # 惰性/剧情气体不动。
    absorb_gas=("毒气", "噩梦气息"), absorb_gas_budget=3,
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
    # 2026-10-26：5 单位刚够「噩梦」门槛，扩散一拍就掉到 2–3；提到 8，
    # 并补上传说里那一声 T2 巨响（每株一次，两种触发共享预算）。
    release=PlantRelease(
        trigger="uproot", gas="噩梦气息", amount=8, sound=6,
    ),
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
    # 踩断柳枝，河水渗出来——原为 2 单位，够不到「失忆」的 8；提到 8 并走
    # 统一释出管线（踩与拔共享一次预算，踩断即移除）。
    trample_to=0,
    release=PlantRelease(liquid="无念黑渊", amount=8, max_cells=1),
)
PLANT_NIGHT_QUEEN = PlantDef(
    "plant.night_queen", "夜皇后", "#8f5cb0", PLANT_CODE_NIGHT_QUEEN, 1, 1, glow=True,
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
    # E08：从「量产贤者粉末」改成有限净化驻点——每回合洗短一项目标征兆的
    # 剩余 1 回合，全株共 3 次；不再同时发旧物品收益。
    purify_budget=3,
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
    # E09：踩碎时把预存的 12 单位晨霜清气放成一次局部气团（12 越过了吸入的
    # 3/5 门槛，扩散后仍有效）；踩碎即移除，所以「喷气」与「拔取薄荷露」互斥。
    trample_to=0,
    release=PlantRelease(trigger="trample", gas="晨霜清气", amount=12, max_cells=1),
)
PLANT_AMBER_FERN = PlantDef(
    "plant.amber_fern", "琥珀蕨", "#d8a860", PLANT_CODE_AMBER_FERN, 1, 1,
    region=PLANT_REGION_SHALLOW,
    # 6 单位扩散一拍常在 2 徘徊（门槛 3）；提到 8。
    release=PlantRelease(trigger="uproot", gas="晨霜清气", amount=8, max_cells=1),
)
PLANT_DAISY = PlantDef(
    "plant.daisy", "忘忧雏菊", "#e8e8a8", PLANT_CODE_DAISY, 1, 1,
    region=PLANT_REGION_SHALLOW,
    uproot_portent="worry_free",
)
PLANT_GLASS_SHROOM = PlantDef(
    "plant.glass_shroom", "彩玻菌", "#e070d0", PLANT_CODE_GLASS_SHROOM, 1, 1, glow=True,
    immune_fire=True, region=PLANT_REGION_HALLUC_ONLY, material_kind="fungus",
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
    # E07：不再给拔取征兆，改成有限微风——每世界回合把本格至多 1 单位气体
    # 推向固定朝向邻格，全株共 6；没有可搬量不消耗预算。
    push_gas_budget=6,
)
PLANT_WAX_BLOOM = PlantDef(
    "plant.wax_bloom", "融蜡花", "#f0d890", PLANT_CODE_WAX_BLOOM, 1, 1, glow=True,
    region=PLANT_REGION_ALL, material_kind="membrane",
    uproot_item="molten_candle",  # 拔除获得 1 件「熔融蜡烛」液体弹（可燃）
)
# 蘑菇换色变体：字形/机制与蘑菇完全一致（抗液抗火/可穿行），只换颜色。
PLANT_MOON_SHROOM = PlantDef(
    "plant.moon_shroom", "月光蕈", "#e0e8f0", PLANT_CODE_MOON_SHROOM, 1, 1,
    immune_liquid=True, immune_fire=True, region=(11, 20, 3), material_kind="fungus",
    # E05：只在本格没有机械照明时给 R1 内的移动脚步 −1（亮灯即失效）。
    step_quiet=1, step_quiet_radius=1, step_quiet_dark=True,
)
PLANT_HOLLOW_SHROOM = PlantDef(
    "plant.hollow_shroom", "空鼓菌", "#c8b890", PLANT_CODE_HOLLOW_SHROOM, 1, 1,
    immune_liquid=True, immune_fire=True, region=(1, 10, 3), material_kind="fungus",
    # E06：首次踩破或拔除时一声 T2 巨响（R6，不带 full_alert/freeze_near）。
    # 走到统一释出管线：踩与拔共用 `released`，先踩响就拔不出第二声。
    trample_to=0,
    release=PlantRelease(sound=6),
)

# ---- 梦中梦·千禧园（2026-10-10）：realm 专属植物（码 24/25）----
# 只由 millennium_park 生成器种下；不进 COMMON/RARE 池（主梦不生成），
# 但必须进 PLANT_KINDS（plant_def_for 反查：渲染/踩踏结算都要认码）。
PLANT_CODE_MILLENNIUM_GRASS = 24
PLANT_CODE_MILLENNIUM_GRASS_LOW = 26
PLANT_CODE_BUBBLE_ALGAE = 25
PLANT_MILLENNIUM_GRASS = PlantDef(
    "plant.millennium_grass", "千禧蒲草", "#7ac86a", PLANT_CODE_MILLENNIUM_GRASS, 2, 1,
    spawn_realms=("millennium_garden",),
    # E10：挺立态在本格与 R1 内每进入一次多耗 0.25 世界回合（同类取最大）；
    # 不再挂 styx_weight（那会在离开后拖尾、还能被重复叠慢）。
    move_penalty=0.25, move_penalty_radius=1,
    trample_to=PLANT_CODE_MILLENNIUM_GRASS_LOW,
)
PLANT_MILLENNIUM_GRASS_LOW = PlantDef(
    "plant.millennium_grass_low", "倒伏的千禧蒲草", "#7ac86a",
    PLANT_CODE_MILLENNIUM_GRASS_LOW, 1, 0,
    spawn_realms=("millennium_garden",),
    # 倒伏后只剩本格那一点点迟滞，覆盖范围收回到 R0。
    move_penalty=0.25,
)
PLANT_BUBBLE_ALGAE = PlantDef(
    "plant.bubble_algae", "气泡藻", "#a0d8c8", PLANT_CODE_BUBBLE_ALGAE, 1, 1,
    material_kind="membrane",
    immune_liquid=True,  # 贴水低丛，液面漫过也不散
    spawn_realms=("millennium_garden",),
    # E11：本格向四邻的气体扩散预算减半（留住有益气团，也留住毒雾）。
    gas_flow_divisor=2,
)

# ---- 三位面专属新增（2026-10-26 植物地形扩展）----
# 码 26 已被「倒伏的千禧蒲草」占用，新种从 27 起顺序登记。
MILLENNIUM_GARDEN_REALM = "millennium_garden"
LIBRARY_PALACE_REALM = "library_palace"
WHITE_SANATORIUM_REALM = "white_sanatorium"

PLANT_CODE_TAPE_TANGLE = 27
PLANT_CODE_DIAL_REED = 28
PLANT_CODE_CONTACT_WHISKER = 29
PLANT_CODE_FRAME_SHARD = 30
PLANT_CODE_HEAT_FILAMENT = 31
PLANT_CODE_PAGE_RIDGE = 32
PLANT_CODE_BINDING_TANGLE = 33
PLANT_CODE_INK_WICK = 34
PLANT_CODE_BLANK_FELT = 35
PLANT_CODE_ABRASION_TABS = 36
PLANT_CODE_SUTURE_TANGLE = 37
PLANT_CODE_FILTER_TUFT = 38
PLANT_CODE_SHUTTER_FOLD = 39
PLANT_CODE_PRESSURE_SAC = 40
PLANT_CODE_INFUSION_AMPOULE = 41

# 千禧园：电子媒介 / 软塑料 / 拨号振片。K01–K05。
PLANT_TAPE_TANGLE = PlantDef(
    "plant.millennium.tape_tangle", "磁带须", "#c48cf0", PLANT_CODE_TAPE_TANGLE, 1, 1,
    spawn_realms=(MILLENNIUM_GARDEN_REALM,), material_kind="plastic",
    # K01：贴地的软带只是「难走」，每次真实踏入本格 +0.5 世界回合。
    move_penalty=0.5,
)
PLANT_DIAL_REED = PlantDef(
    "plant.millennium.dial_reed", "拨号簧", "#e6bd45", PLANT_CODE_DIAL_REED, 1, 1,
    material_kind="metal",
    spawn_realms=(MILLENNIUM_GARDEN_REALM,),
    immune_liquid=True, immune_fire=True,
    # K02：首次踏入振响 R1 环境短声并把本体压平（之后拔除不重响）。
    trample_to=PLANT_CODE_SHORT,
    release=PlantRelease(trigger="trample", sound=1),
)
PLANT_CONTACT_WHISKER = PlantDef(
    "plant.millennium.contact_whisker", "导电脚线", "#3fd4e4", PLANT_CODE_CONTACT_WHISKER, 1, 1,
    spawn_realms=(MILLENNIUM_GARDEN_REALM,), material_kind="metal",
    immune_liquid=True, immune_fire=True,
    # K03：常驻导电介质（自己不发电）+ 首次踩/拔放出 ≤3 格、1 回合的静电场。
    conductive=True,
    release=PlantRelease(electric=3),
)
PLANT_FRAME_SHARD = PlantDef(
    "plant.millennium.frame_shard", "错帧片", "#6aa8e8", PLANT_CODE_FRAME_SHARD, 2, 1,
    material_kind="plastic",
    spawn_realms=(MILLENNIUM_GARDEN_REALM,),
    immune_liquid=True,
    # K04：H2 只挡视线、照样可穿——高度 2 就是既有「高植物遮挡」语义，
    # 不设 solid，所以不是墙。
)
PLANT_HEAT_FILAMENT = PlantDef(
    "plant.millennium.heat_filament", "热熔须", "#ff7f52", PLANT_CODE_HEAT_FILAMENT, 1, 1,
    material_kind="metal",
    spawn_realms=(MILLENNIUM_GARDEN_REALM,),
    immune_liquid=True,
    # K05：一次电热脉冲，最多点燃本格与 R1 内 3 个真有燃料的格。
    release=PlantRelease(ignite=3),
)

# 藏书宫：书页 / 装订 / 墨 / 留白 / 磨页。L01–L05。
PLANT_PAGE_RIDGE = PlantDef(
    "plant.library.page_ridge", "散页脊", "#3f5b93", PLANT_CODE_PAGE_RIDGE, 2, 1,
    spawn_realms=(LIBRARY_PALACE_REALM,),
    # L01：纸页竖起，只挡视线；纸缝可穿。可燃，遇液塌散（默认规则）。
)
PLANT_BINDING_TANGLE = PlantDef(
    "plant.library.binding_tangle", "装订须", "#6b4b8a", PLANT_CODE_BINDING_TANGLE, 1, 1,
    spawn_realms=(LIBRARY_PALACE_REALM,),
    # L02：装订线绊脚但不定身。
    move_penalty=0.5,
)
PLANT_INK_WICK = PlantDef(
    "plant.library.ink_wick", "吸墨绒", "#1a4b63", PLANT_CODE_INK_WICK, 1, 1,
    spawn_realms=(LIBRARY_PALACE_REALM,),
    immune_liquid=True,
    # L03：每回合吸 1 单位湿墨/稀墨，全株共 6；任务保护液体不动。
    absorb_liquid=("湿墨", "稀墨"), absorb_liquid_budget=6,
)
PLANT_BLANK_FELT = PlantDef(
    "plant.library.blank_felt", "留白絮", "#55606b", PLANT_CODE_BLANK_FELT, 1, 1,
    spawn_realms=(LIBRARY_PALACE_REALM,),
    # L04：R1 内移动脚步 −1（最低 0），攻击与警报声不减。
    step_quiet=1, step_quiet_radius=1,
)
PLANT_ABRASION_TABS = PlantDef(
    "plant.library.abrasion_tabs", "磨页片", "#94492c", PLANT_CODE_ABRASION_TABS, 1, 1,
    spawn_realms=(LIBRARY_PALACE_REALM,),
    # L05：踩/拔那一下刮过相邻地表，最多 3 格各 −8 耐久，只削不碎。
    release=PlantRelease(integrity=8, max_cells=3),
)

# 至白疗所：耗材 / 缝线 / 滤材 / 遮光折片 / 膜囊。H01–H05。
PLANT_SUTURE_TANGLE = PlantDef(
    "plant.hospital.suture_tangle", "缝线丛", "#3f5d75", PLANT_CODE_SUTURE_TANGLE, 1, 1,
    spawn_realms=(WHITE_SANATORIUM_REALM,),
    # H01：常态绊脚 +0.5；首次被踩时线圈收紧，1 世界回合 snared（不重复刷新）。
    move_penalty=0.5,
    release=PlantRelease(trigger="trample", portent="snared"),
)
PLANT_FILTER_TUFT = PlantDef(
    "plant.hospital.filter_tuft", "滤气绒", "#1f808c", PLANT_CODE_FILTER_TUFT, 1, 1,
    spawn_realms=(WHITE_SANATORIUM_REALM,),
    immune_liquid=True,
    # H02：每回合吸 1 单位胞尘/梦醚气，全株共 6；不吸无菌载气、醒素薄气、消兆薄雾。
    absorb_gas=("胞尘", "梦醚气"), absorb_gas_budget=6,
)
PLANT_SHUTTER_FOLD = PlantDef(
    "plant.hospital.shutter_fold", "光阑褶", "#4a6fb5", PLANT_CODE_SHUTTER_FOLD, 1, 1,
    material_kind="metal",
    spawn_realms=(WHITE_SANATORIUM_REALM,),
    immune_liquid=True, immune_fire=True,
    # H03：本格与 R1 的机械照明视距加值 −1（+3→+2、+4→+3、0 仍是 0），
    # 不改 lit 布尔、不关灯。
    sight_bonus_delta=-1,
)
PLANT_PRESSURE_SAC = PlantDef(
    "plant.hospital.pressure_sac", "压差囊", "#5b3f7e", PLANT_CODE_PRESSURE_SAC, 1, 1,
    material_kind="membrane",
    spawn_realms=(WHITE_SANATORIUM_REALM,),
    immune_liquid=True,
    # H04：首次踩压把本格最多 4 单位同种气体推向嘴朝的那一格（只此一次）。
    release=PlantRelease(trigger="trample", push_gas=4),
)
PLANT_INFUSION_AMPOULE = PlantDef(
    "plant.hospital.infusion_ampoule", "滴注囊", "#9a3f56", PLANT_CODE_INFUSION_AMPOULE, 1, 1,
    material_kind="membrane",
    spawn_realms=(WHITE_SANATORIUM_REALM,),
    immune_liquid=True,
    # H05：12 单位洗兆液摊到本格与管口相邻格（3 格各 4，刚好过单格 ≥4 的洗兆
    # 门槛）；删掉「晨醒溶液」分支——它没有接触效果，8 单位永远到不了 6 的门槛。
    release=PlantRelease(liquid="洗兆液", amount=12, max_cells=3),
)

# ---- H1 形态（docs 2026-10-26 §10.1「催生」）----------------------------
# 错帧片/散页脊的挡视线身份是 H2 立起态；它们需要一个**真实更矮**的 H1 收拢
# 态，催生才有东西可长，而且必须真的改高度/遮挡，不能只放大图标。这两态
# 不参与随机抽签（weight=0），由生成器按「三成尚未立起」下放，或由世界内
# 既有株被踩/被压之后回落——它们不是第 16、17 个新种，是形态变体（同码 26）。
PLANT_CODE_FRAME_SHARD_FLAT = 42
PLANT_CODE_PAGE_RIDGE_FLAT = 43
PLANT_FRAME_SHARD_FLAT = PlantDef(
    "plant.millennium.frame_shard_flat", "收拢的错帧片", "#6aa8e8",
    PLANT_CODE_FRAME_SHARD_FLAT, 1, 0,
    spawn_realms=(MILLENNIUM_GARDEN_REALM,), material_kind="plastic",
    immune_liquid=True,
    # 片还叠着：不挡视线，也就是「能靠催生换来一个观察口」的那一头。
)
PLANT_PAGE_RIDGE_FLAT = PlantDef(
    "plant.library.page_ridge_flat", "合上的散页脊", "#3f5b93",
    PLANT_CODE_PAGE_RIDGE_FLAT, 1, 0,
    spawn_realms=(LIBRARY_PALACE_REALM,),
    # 纸页合着：可燃、遇液塌散，与 L01 同一材质，只是没立起来。
)

MILLENNIUM_PLANTS: tuple[PlantDef, ...] = (
    PLANT_TAPE_TANGLE, PLANT_DIAL_REED, PLANT_CONTACT_WHISKER,
    PLANT_FRAME_SHARD, PLANT_HEAT_FILAMENT,
)
LIBRARY_PLANTS: tuple[PlantDef, ...] = (
    PLANT_PAGE_RIDGE, PLANT_BINDING_TANGLE, PLANT_INK_WICK,
    PLANT_BLANK_FELT, PLANT_ABRASION_TABS,
)
HOSPITAL_PLANTS: tuple[PlantDef, ...] = (
    PLANT_SUTURE_TANGLE, PLANT_FILTER_TUFT, PLANT_SHUTTER_FOLD,
    PLANT_PRESSURE_SAC, PLANT_INFUSION_AMPOULE,
)

# 形态变体：不由抽签产生（weight=0），只由生成/催生/踩踏转换得到；
# 但必须能被 plant_def_for 反查（渲染、踩踏、存档都要认码）。
PLANT_FORM_VARIANTS: tuple[PlantDef, ...] = (
    PLANT_MILLENNIUM_GRASS_LOW, PLANT_FRAME_SHARD_FLAT, PLANT_PAGE_RIDGE_FLAT,
)
REALM_PLANT_KINDS: dict[str, tuple[PlantDef, ...]] = {
    MILLENNIUM_GARDEN_REALM: MILLENNIUM_PLANTS,
    LIBRARY_PALACE_REALM: LIBRARY_PLANTS,
    WHITE_SANATORIUM_REALM: HOSPITAL_PLANTS,
}
# 三位面本地已有专属：千禧园的旧种也算本位面专属份额（docs §9.1）。
REALM_LOCAL_PLANTS: dict[str, tuple[PlantDef, ...]] = {
    MILLENNIUM_GARDEN_REALM: (PLANT_MILLENNIUM_GRASS, PLANT_MILLENNIUM_GRASS_LOW,
                              PLANT_BUBBLE_ALGAE, *MILLENNIUM_PLANTS),
    LIBRARY_PALACE_REALM: LIBRARY_PLANTS,
    WHITE_SANATORIUM_REALM: HOSPITAL_PLANTS,
}

PLANT_KINDS: tuple[PlantDef, ...] = (
    PLANT_SHORT, PLANT_TALL, PLANT_LICHEN, PLANT_MUSHROOM,
    PLANT_MANDRAKE, PLANT_DATURA, PLANT_STYX, PLANT_NIGHT_QUEEN,
    PLANT_SOUL_VINE, PLANT_SAGE_MOSS, PLANT_MIRROR_ORCHID, PLANT_LILY,
    PLANT_MINT, PLANT_AMBER_FERN, PLANT_DAISY, PLANT_GLASS_SHROOM,
    PLANT_WHISPER_FERN,
    PLANT_DREAM_GRASS, PLANT_THORN_VINE, PLANT_VANE_MOSS, PLANT_WAX_BLOOM,
    PLANT_MOON_SHROOM, PLANT_HOLLOW_SHROOM,
    PLANT_MILLENNIUM_GRASS, PLANT_BUBBLE_ALGAE, PLANT_MILLENNIUM_GRASS_LOW,
    # 三位面专属新增（2026-10-26）
    PLANT_TAPE_TANGLE, PLANT_DIAL_REED, PLANT_CONTACT_WHISKER,
    PLANT_FRAME_SHARD, PLANT_HEAT_FILAMENT,
    PLANT_PAGE_RIDGE, PLANT_BINDING_TANGLE, PLANT_INK_WICK,
    PLANT_BLANK_FELT, PLANT_ABRASION_TABS,
    PLANT_SUTURE_TANGLE, PLANT_FILTER_TUFT, PLANT_SHUTTER_FOLD,
    PLANT_PRESSURE_SAC, PLANT_INFUSION_AMPOULE,
    # H1 形态变体（催生目标，docs §10.1；不是新的第 16/17 个新种）
    PLANT_FRAME_SHARD_FLAT, PLANT_PAGE_RIDGE_FLAT,
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
    """这株植物是否可燃（见 core/materials_sim._cell_is_flammable）。

    按**材质**判（docs §3.3）：金属/覆银薄片不烧，软塑与纤维烧，菌质与膜囊
    沿用各自的免疫旗标。不能再写成「有 plant 字段就是草」。
    """
    return bool(code) and plant_def_for(code).flammable


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


# ---- 位面专属池与位面内抽签（2026-10-26 植物地形扩展 §9.1）----
def realm_plant_pool(realm_id: str) -> tuple[PlantDef, ...]:
    """某个长位面允许的植物池（本位面专属 + 主梦白名单），专属在前。"""
    local = REALM_LOCAL_PLANTS.get(realm_id)
    if not local:
        return ()
    # 主梦白名单：低草/高丛/发光地衣/蘑菇。高丛踩倒后就是低草，两者都要在，
    # 否则「先学绕过、再学踩倒」的教学样板会缺一半。
    return (*local, PLANT_SHORT, PLANT_TALL, PLANT_LICHEN, PLANT_MUSHROOM)


def realm_plant_kind(rng_roll: float, realm_id: str, *, exclusive_chance: float = 0.9) -> PlantDef:
    """长位面内的植物抽签：默认 90% 本位面专属、10% 主梦白名单。

    旧口径把主梦四种等权抽，结果「图书馆的主视觉是低草」。这里把份额写死
    在池子里：先按 `exclusive_chance` 决定走专属还是白名单，再在对应子池里
    按权重抽。没有专属登记的位面直接退回常规池。
    """
    local = REALM_LOCAL_PLANTS.get(realm_id)
    if not local:
        return plant_kind(rng_roll, realm_id=realm_id)
    shared = (PLANT_SHORT, PLANT_TALL, PLANT_LICHEN, PLANT_MUSHROOM)
    use_local = rng_roll < exclusive_chance
    pool = local if use_local else shared
    # 同一 rng_roll 既做门又做位置会系统性偏向池首，所以用小数部分重排。
    position = (rng_roll * 997.0) % 1.0 if use_local else ((rng_roll - exclusive_chance) / (1.0 - exclusive_chance))
    total = sum(definition.weight for definition in pool)
    cursor = max(0.0, min(0.999999, position)) * total
    for definition in pool:
        cursor -= definition.weight
        if cursor < 0:
            return definition
    return pool[-1]


def plant_release_for(code: int) -> PlantRelease | None:
    """这株植物被破坏时的释出配方（None = 不释出）。"""
    if not code:
        return None
    return plant_def_for(code).release


def plant_budget_key(code: int) -> str:
    """常驻预算在 `cell.plant_state` 里的键名（同一格换种即视为新株）。"""
    return f"budget:{int(code)}"


def plant_conducts(code: int) -> bool:
    """这株植物是否是常驻导电介质（K03）。"""
    return bool(code) and plant_def_for(code).conductive


def plant_step_quiet(code: int) -> int:
    """本株给出的脚步降噪格数（不含「暗处才生效」的条件判定）。"""
    return plant_def_for(code).step_quiet if code else 0


def plant_move_penalty(code: int) -> tuple[float, int]:
    """(进入耗时增量, 作用半径)：半径 0 = 只本格，1 = 本格与相邻一圈。"""
    if not code:
        return 0.0, 0
    definition = plant_def_for(code)
    return definition.move_penalty, definition.move_penalty_radius


def plant_sight_delta(code: int) -> int:
    return plant_def_for(code).sight_bonus_delta if code else 0


def plant_gas_flow_divisor(code: int) -> int:
    return max(1, plant_def_for(code).gas_flow_divisor) if code else 1


def plant_spent(code: int, state: dict | None) -> bool:
    """这株是否已经耗尽/空壳（用于满／空壳两档字符）。"""
    state = state or {}
    if state.get("released"):
        return True
    definition = plant_def_for(code) if code else None
    if definition is None:
        return False
    budget = state.get(plant_budget_key(code))
    if budget is not None:
        return int(budget) <= 0
    total = max(definition.absorb_gas_budget, definition.absorb_liquid_budget,
                definition.push_gas_budget, definition.purify_budget)
    return bool(total) and int(state.get("spent", 0)) >= total
