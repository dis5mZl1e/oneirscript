"""世界数据类：格子、实体、物品、事件、层快照与动作结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .constants import Material


@dataclass
class Cell:
    wire: int = 0  # 电线位掩码（N=1 E=2 S=4 W=8）；可铺在墙格上，随层持久化
    floor: Material = Material.PLAIN_AGGREGATE
    solid: bool = False
    liquid: int = 0
    gas: int = 0
    hardness: int = 2
    thickness: int = 1
    integrity: int = 100
    cover: int = 0
    flame: int = 0
    aggregate_variant: str = "普通聚合物"
    wall_kind: str = ""
    height: int = 0
    elevation: int = 0
    liquid_kind: str = ""
    gas_kind: str = ""
    # 植物（一类可穿行的固体地形，不属于墙体）：0 = 无，1 = 低草，2 = 高丛
    # （遮挡视线），3 = 发光地衣（照亮周围，见 core/vision/glow.py），4 = 蘑菇
    # （液体与火焰都破坏不了）。遇液体消失、见火逐回合燃烧（蘑菇例外），
    # 被踩踏时高丛折成低草——一律见 materials/plants.py 的旗标。
    plant: int = 0
    plant_fuel: int = 0
    floor_fuel: int = 0
    item_burn_progress: int = 0
    # Only actual player-created walls carry this instance provenance.
    creation: dict = field(default_factory=dict)
    material_clocks: dict[str, int] = field(default_factory=dict)
    light_radius: int = 0
    light_on: bool = True
    doorway: bool = False
    phase_stock: dict = field(default_factory=dict)
    # 植物的一次性／有限状态（2026-10-26 植物地形扩展）：
    # released=1（释出型已经用过那一次）、budget:<code>（剩余预算）、
    # direction（朝向）。跟着格子走，所以读档、上下层、催生/枯萎之后
    # 预算都不会凭空回满。
    plant_state: dict = field(default_factory=dict)


@dataclass
class Entity:
    id: str
    label: str
    x: int
    y: int
    integrity: int = 1
    mind_trauma: int = 0
    lucidity_trauma: int = 0
    move_time: float = 1.0
    attack_time: float = 1.0
    relation: str = "失控意识"
    glyph: str = "👁️"
    anomaly_kind: str = "普通异象"
    trauma_type: str = "心智创伤"
    alert_state: str = "未察觉"
    vision: int = 6
    communicates: bool = True
    move_clock: float = 0.0
    attack_clock: float = 0.0
    # 本回合是否已经出手：出手的回合它不再移动。贴着玩家的打击由客观时间
    # 蓄力结算（见 GameState._charge_adjacent_attacks），那一瞬间不在 _enemy_turns
    # 里，所以用这个瞬态标记把「出手了就别再挪步」的旧行为带过去。
    attack_pending: bool = False
    drop_id: str | None = None
    always_visible: bool = False  # 核心执念：恒显（所在格视为在视野中）
    dissolution_reward: int = 4
    catalog_id: str = "anomaly.unknown"
    drop_spawned: bool = False
    catalog_observed: bool = False
    # 内容扩展：行为钩子与瞬时状态（序列化兼容——旧存档缺省即可）。
    trait: str = ""  # clock_pulse / mirror_step / liquid_swimmer / cutpurse / disguise / patrol / split_main / phantom / choir / staircase / lighthouse
    biological_tags: tuple[str, ...] = ()
    hospital_state: dict = field(default_factory=dict)
    pulse_clock: float = 0.0
    frozen_turns: float = 0.0
    blind_turns: float = 0.0
    slow_turns: float = 0.0
    route: list[tuple[int, int]] = field(default_factory=list)
    route_index: int = 0
    main_id: str | None = None
    # 征兆：其他生物同样会被液体/气体赋予持续状态（portent_id -> 剩余回合）。
    portents: dict[str, int] = field(default_factory=dict)
    portent_debt: dict[str, float] = field(default_factory=dict)
    # 征兆的「层」计数（portent_id -> 剩余层数/使用次数）：与 portents（回合）
    # 独立。回合走完只降层（PortentDef.duration_drop），层归零才移除征兆。
    # 挂在实体上而不是 GameState 上——每个生物各自记账。
    portent_stacks: dict[str, int] = field(default_factory=dict)
    # 材料「附着」计时（2026-10-07，portent_id -> 剩余附着回合）：材料征兆被赋予时
    # 挂上，离开来源材料后附着期内征兆**全额续效且不计衰减**（黏在身上），
    # 附着耗尽才开始走 portents 回合时钟；站在材料中会补满。仅对带 material 的
    # 征兆有意义。旧存档缺省为空 = 无附着（老征兆按原时钟自然衰减）。
    portent_attach: dict[str, float] = field(default_factory=dict)
    # 第十九节 §17：一次成功获得后的单轮硬结束边界（portent_id -> 世界时间）。
    # 持续接触可以保留本轮表现，但不能越过这个边界继续续期。
    portent_deadlines: dict[str, int] = field(default_factory=dict)
    # 真正结束后的隐藏保护（portent_id -> 世界时间）；在此之前不能再次获得同一 ID。
    portent_protection: dict[str, int] = field(default_factory=dict)
    # 稳定意识的固定货架下标：付费交易抽 2–3 项，其余交互不占交易名额。
    # 空元组代表旧档缺失，按稳定实例身份补抽，不能退回整张交易表。
    npc_options: tuple[int, ...] = ()
    # 稳定意识的**职业 id**（``npc.little_devil`` 一类）。id 是实例唯一的（enemy-N），
    # 职业另存这里：同名同职业可以同时出现两位，对话/交易记账不会串到对方身上。
    npc_kind: str = ""
    # 稳定意识的**跨层稳定身份**（``{layer_key}#{npc_kind}#{同职业序号}``）。
    # enemy-N 实例 id 在层快照被裁剪后重建时会变（同一层按种子重生成会拿到新的
    # 编号），一次性交易/赠品若按实例 id 记账就会「换层回来又能买一次」。
    # actor_uid 由「层键 + 职业 + 本层同职业生成次序」推出，三者都由种子决定，
    # 所以重建后同一名 NPC 拿到的是同一个 uid（见 core.state.layer_key）。
    # 空串 = 旧存档里生成的 NPC，退回按实例 id 记账。
    actor_uid: str = ""
    # 追击记忆：连续多少回合看不见玩家（追踪态下累加，重新看见即清零）；
    # last_seen_x/y 是最后一次看见玩家的位置（-1 = 从未看见），
    # 丢掉目标后它改去那里搜，而不是沿实时位置紧咬。旧存档缺省即「无记忆」。
    lost_sight_turns: float = 0.0
    last_seen_x: int = -1
    last_seen_y: int = -1
    # §8.1 有限预判：上一次真实目击的位置（-1 = 还没看过第二次），用来
    # 判断玩家最近一次被观察到的移动方向；不读未提交输入或隐藏轨迹。
    last_seen_prev_x: int = -1
    last_seen_prev_y: int = -1
    # §22 B：视觉、听觉、传信分开记账。last_seen 只由真实目击刷新；
    # 声音写入 last_heard，同伴报信写入 last_reported，互不覆盖。
    last_seen_time: int = -1
    last_heard_x: int = -1
    last_heard_y: int = -1
    last_heard_time: int = -1
    last_heard_category: str = ""
    last_reported_x: int = -1
    last_reported_y: int = -1
    last_reported_time: int = -1
    # 调查任务（§22 B）：按地点／来源去重的静态声源与传信点。
    # 每项：x/y、source、category、time、expires、tried、unreachable。
    investigation_tasks: list[dict] = field(default_factory=list)
    # 追踪规划（core/pathing/pursuit.py）：看见玩家时以玩家当前位置实时规划的
    # 最短路径（不含所在格）；丢失视野后沿剩余路径继续走向最后一次目击处；
    # 走到终点仍没发现目标就转入游荡（wandering），直到重新看见玩家。
    # plan_index 指向 path_plan 里下一步要走的格子；wander_nonce 只用来给
    # 游荡目标的确定性随机换种子。旧存档缺省即「无计划、未游荡」。
    path_plan: list[tuple[int, int]] = field(default_factory=list)
    plan_index: int = 0
    wandering: bool = False
    wander_nonce: int = 0
    # §5.3 动态堵塞／无进展：连续没迈出一步的真实移动次数、最近落点
    # （避免 A→B→A 往返）、当前被同伴占住的计划步，以及是否已经为
    # 「正在离开的同伴」等过一回合。旧存档缺省即无记录。
    nav_stall: int = 0
    nav_recent: list = field(default_factory=list)
    nav_blocked: list = field(default_factory=list)
    nav_waited: bool = False
    # §5.3 相向卡门：开始为对方让路的世界时间（-1 = 当前没有等待）。
    nav_wait_since: int = -1
    # §5.1：射手在距离带内主动按兵不动（合法准备站位，不算无进展）。
    nav_hold: bool = False
    # Encounter role: remain at the guarded spot until sight or sound supplies
    # a real target. Species traits and subsequent pursuit stay unchanged.
    keeps_watch: bool = False
    # 异象技能 v3（2026-09-22）：定义表驱动的远程/范围/地形技能。
    # skill_clocks：各技能（按定义表 "skills" 下标 s0/s1/...）的回合计时；
    # aoe_charge > 0 表示范围技能蓄力中（剩余回合），锚点 (aoe_tx, aoe_ty)，
    # 渲染层据此画出预警范围（state.skill_telegraphs）。
    # 旧存档缺省即可（asdict 全量落档，Entity(**payload) 兼容缺键）。
    skill_clocks: dict[str, float] = field(default_factory=dict)
    aoe_charge: float = 0.0
    aoe_tx: int = -1
    aoe_ty: int = -1
    # 异象主动技能（2026-10-08）：运行期状态（pending 蓄力/恢复/治疗预算/
    # 阶段/召唤寿命）。冷却仍用稳定技能 ID 记在 skill_clocks。
    # 旧存档缺省为空（读档走 persistence._decode_entity 的类型恢复）。
    active_skill_state: dict = field(default_factory=dict)
    # 反伤：两套互相独立的机制，可同时挂在同一个异象上。
    #   反击 —— 只认玩家的「攻击行动」次数（一次多段攻击仍算 1 次）；
    #   荆棘 —— 只认一次攻击的「段数」（每段各触发一次），与回合、行动计数无关。
    # 详见 GameState._maybe_counter / _maybe_thorns。旧存档缺省即无反伤。
    attack_actions_taken: int = 0
    counter_every: int = 0          # 每 N 次玩家攻击行动反伤一次；0 = 无
    counter_scope: str = "any"      # "melee" | "ranged" | "any"
    counter_effect: str = ""
    thorns_per_segment: bool = False  # 每命中一段反伤一次
    thorns_scope: str = "any"
    thorns_effect: str = ""
    # 本层异象补刷序号（2026-10-27）：0 = 随地图生成的首波/非补刷；n≥1 = 本层
    # 第 n 只自然补刷的异象。掉落率从第 ANOMALY_REFRESH_FREE_DROP_WAVES + 1 只起
    # 按指数衰减（见 core.enemies._late_spawn_drop_multiplier）。旧存档缺这个键
    # 走默认值 0（persistence 用 Entity(**data)，天然兼容）。
    spawn_wave: int = 0


@dataclass
class Item:
    definition_id: str
    instance_id: str
    name: str
    category: str
    slot: str | None = None
    description: str = ""
    color: str = "bright_white"
    quantity: int = 1
    max_stack: int = 1
    effect: str | None = None
    power: int = 0
    power_secondary: int = 0
    penetration: int = 0
    push: int = 0
    explosion_radius: int = 0
    projectile_template: str = "直线弹体"
    # 容器类物品的内部存储：{材料名: 数量}（玻璃瓶/试管/气球/理想气体容器）。
    contents: dict = field(default_factory=dict)
    # 稀有度（常见/少见/稀有/非常稀有）；记忆碎片、交互道具等无稀有度条目为 ""。
    rarity: str = ""
    # 已消耗的气体消散周期余量；封存在物品内时暂停，释放后续算。
    gas_decay_age: dict[str, int] = field(default_factory=dict)
    # 2026-10-21 统一发射源：逐物理实例的弹匣；None = 该物品没有弹匣。
    magazine: int | None = None
    magazine_capacity: int = 0
    reload_steps: int = 0
    reload_paid: bool = False
    magazine_rule: int = 0
    # 分次部署的剩余次数（2026-10-22 P3）：烟雾双联罐两只罐头要各投一次。
    # 0 = 一件一次性物品，投出去就没了（绝大多数消耗品如此）。
    charges: int = 0

    @property
    def icon(self) -> str:
        """定义表显式图标优先，其次使用稳定的物品家族键；未知物品返回空串。

        从定义表**实时**读取而不存快照：图标属于外观资料，改定义即全局生效，
        老存档里留下的旧图标/旧名字随之修正（名字的迁移见 persistence._decode）。
        家族键由 glyph_for 统一解析为专用字体或普通终端语义符号。
        """
        from .content import ITEM_DEFINITIONS

        definition = ITEM_DEFINITIONS.get(self.definition_id)
        from ..data.item_icons import item_icon
        return item_icon(self.definition_id, definition) if definition else ""


@dataclass
class WorldItem:
    item: Item
    x: int
    y: int
    # §14.6 落点层级：空串＝地面；否则是支撑它的台面墙种身份。
    surface: str = ""

    def sync_surface(self, cell) -> None:
        """按当前支撑物刷新落点层级；台体被毁后自动落回地面。"""
        from ..materials import SURFACE_KINDS

        kind = str(getattr(cell, "wall_kind", "") or "")
        self.surface = kind if kind in SURFACE_KINDS else ""


@dataclass
class WorldEvent:
    event_id: str
    name: str
    x: int
    y: int
    description: str
    reward_id: str | None = None
    reward_count: int = 1
    dissolution_reward: int = 10
    catalog_id: str = "event.unknown"
    insight_id: str | None = None
    resolved: bool = False
    # 复合事件（2026-09-18）：simple = 点击即触发结算；compound = 触发唤起
    # 事件面板，对话文本可滚动、选项固定在面板底部。dialogue/options 仅
    # 复合事件使用（options: {"label":..., "rewards":{...}} 结构，见 content.py）。
    kind: str = "simple"
    dialogue: tuple[str, ...] = ()
    options: tuple[dict, ...] = ()
    # 剩余触发次数（2026-09-18）：定义里的 ``uses``（默认 1）在生成时落到这里，
    # 每结算一次减一，归零即 resolved=True——此后既高亮不出选项、也不能再回应。
    # 面板会把它写出来，玩家知道这个地点还能用几次。
    uses_left: int = 1
    # 结构绑定事件：随中大型结构生成，不占每层随机事件配额（≤2）。
    bound: bool = False
    # 场景锚点事件指向的设施实例 ID（§13.2）。空 = 普通事件，不是场景入口。
    scene_uid: str = ""
    # 篡改系统（规格 §8.2）：本局内的实例身份。同层可能出现多个同类事件，
    # 因此生成时按「本局＋层／位面＋类型＋初始坐标＋同位置序号」补一个固定值；
    # 一旦赋值不因移动、重排或界面排序重算。空 = 旧存档，曝光给面板前补齐。
    instance_uid: str = ""


@dataclass
class LayerSnapshot:
    depth: int
    seed: int
    cells: list[list[Cell]]
    enemies: list[Entity]
    world_items: list[WorldItem]
    events: list[WorldEvent]
    player_x: int
    player_y: int
    dissolution: int = 0
    theme: str = ""
    map_form: str = "整齐的房间"
    # 该层自己的地图尺寸：长廊会改写长宽比，回溯时要按原尺寸还原（0 = 旧存档，沿用当前尺寸）。
    width: int = 0
    height: int = 0
    # 逻辑固体（内容扩展包 v1）："x,y" → 陷阱场景名 / 灌注阀储备材料。
    # 盖章时确定性抽定并随层保存——读档后陷阱种类不变。
    logic_scenarios: dict = field(default_factory=dict)
    logic_valves: dict = field(default_factory=dict)
    logic_boards: list = field(default_factory=list)
    logic_fences: dict = field(default_factory=dict)
    # 异象主动技能（2026-10-08）：本层的效果场（来源/寿命/实际格/渠道/每拍
    # 伤害/叠加族）。随层快照保存与还原；旧存档缺省为空。
    enemy_skill_fields: list = field(default_factory=list)
    realm_bg_zones: list = field(default_factory=list)
    material_time: int = 0
    realm_features: dict = field(default_factory=dict)


@dataclass
class ActionResult:
    changed: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
