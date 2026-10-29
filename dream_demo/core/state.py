"""GameState：世界状态本体（字段与编排层），能力由各 Mixin 提供。

Mixin 分工：generation 生成 / doors 门 / vision 视野（子包：
视线、发光、可见缓存）/ pathing 寻路（子包：玩家 A* 与异象追踪）/ portents
征兆 / tempo 时间轴 / materials_sim 材料模拟 / enemies 异象 / actions 玩家动作。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import random
from typing import Any

from ..i18n import tr
from ..equipment.root_facts import root_action
from ..world import travel
from ..world.ledger import ActorRecord, WorldLedger
from ..data.anomaly_skills import skill_summaries_for
from ..mapgen import layer_dimensions, layer_form_for, layer_modifier_for, normalize_map_form, region_falloff
from ..mapgen.origin import DOLL_INTEGRITY, DOLL_MOVE_TIME, DOLL_RESPAWN_TURNS, PROJECTILE_GRANTS, generate_origin_layer
from .tutorial import tutorial_end
from .main_difficulty import active_profile, current_anomaly_definition, current_skill_summaries
from ..materials import floor_effect_for, plant_def_for, portent_def, trampled_code
from ..symbols import entity_glyph
from .actions import PlayerActionMixin
from .epilogue import EpilogueMixin
from .constants import (
    ANOMALY_REFRESH_ACTIVE_CAP,
    ANOMALY_REFRESH_INTERVAL,
    ANOMALY_REFRESH_MIN_INTERVAL,
    MIND_REGEN_INTERVAL,
    REMOTE_OVERWRITE_INTERVAL,
    Material,
)
from .content import (
    ABILITY_DEFINITIONS,
    roll_rarity,
    ANOMALY_DEFINITIONS,
    anomaly_pool_for_depth,
    strong_anomaly_ids_for_depth,
    strong_anomaly_budget_for_depth,
    STRONG_ANOMALY_SPAWN_CHANCE,
    INSIGHT_LIMIT,
    INNATE_INSIGHTS,
    EQUIPMENT_POOL,
    EQUIPMENT_SLOTS,
    equipment_pool_for_depth,
    EVENT_DEFINITIONS,
    INSIGHT_DEFINITIONS,
    ITEM_DEFINITIONS,
    items_of_rarity,
    LAYER_EVENT_IDS,
    LAYER_THEMES,
    MEMORY_FRAGMENT_EFFECTS,
    MEMORY_LIMIT,
    ORDINARY_ANOMALY_IDS,
    UNCONSCIOUS_ORDINARY_ANOMALY_IDS,
)
from .doors import DoorMixin
from .ebbing import EbbingMixin
from .enemy_skills import EnemySkillMixin
from .enemies import EnemyMixin
from .logic import LogicMixin
from .dreams import DreamRealmMixin
from .entities import ActionResult, Cell, Entity, Item, LayerSnapshot, WorldEvent, WorldItem
from ..data.dreams import EMBER_LIGHTER_NPC, REALM_ENTRY_NPCS, REALM_GATE_DEFS
from ..equipment.aggregation import diminish_int
from ..equipment.board import EquipmentBoard
from .equipment_board import EquipmentBoardMixin
from .generation import GenerationMixin
from .identity_traits import IdentityMixin
from .materials_sim import MaterialSimMixin
from .pathing import PathMixin
from .portents import (
    PortentMixin,
    emit_plant_reaction_visual,
    plant_visual_snapshot,
)
from .hospital_effects import HospitalEffectMixin
from ..equipment.hospital import HospitalEquipmentMixin
from .run_options import NEUTRAL_MODS, RunOptionsMixin
from .tempo import TempoMixin
from .vision import SightMixin
from .vision.knowledge import cell_knowledge as _cell_knowledge
from .vision.knowledge import record_visible_terrain as _record_visible_terrain


@dataclass
class GameState(
    IdentityMixin,
    EpilogueMixin,
    GenerationMixin,
    LogicMixin,
    DreamRealmMixin,
    EbbingMixin,
    DoorMixin,
    SightMixin,
    PathMixin,
    PortentMixin,
    HospitalEffectMixin,
    HospitalEquipmentMixin,
    TempoMixin,
    MaterialSimMixin,
    RunOptionsMixin,
    EnemySkillMixin,
    EnemyMixin,
    EquipmentBoardMixin,
    PlayerActionMixin,
):
    width: int
    height: int
    seed: int
    cells: list[list[Cell]]
    player: Entity
    # 本局基准尺寸：某些层型（长廊）会临时改写 width/height，基准值用于换算其它层。
    # 0 = 旧存档，回落到当前 width/height。
    base_width: int = 0
    base_height: int = 0
    enemies: list[Entity] = field(default_factory=list)
    time: int = 0
    depth: int = 1
    dissolution: int = 0
    mind: int = 100
    lucidity: int = 100
    imagination: int = 50
    max_mind: int = 100
    max_lucidity: int = 100
    max_imagination: int = 50
    # 开局选项（2026-10-09）：run_options 是原始选择（{"sliders": {k: 档}, "toggles": [k]}），
    # run_mods 是解析后的纯数值修正。旧档两字段缺省 → 空选择/中性修正，
    # 行为与旧版本完全一致（唯一权威口径见 core/run_options.py）。
    run_options: dict = field(default_factory=dict)
    run_mods: dict = field(default_factory=lambda: dict(NEUTRAL_MODS))
    # 缺字段的旧存档继续使用旧曲线；只有 new() 主动选择当前版本。
    difficulty_revision: int = 0
    run_start_choices: dict = field(default_factory=dict)
    imagination_regen_credit: float = 0.0
    # 篡改系统（2026-10-12，规格 §6、§9.1）：混乱度本局累计，跨层与跨位面共享，
    # 与崩解度分别保存、显示和结算。衰减余量按「已支付的有效行动耗时」累计，
    # 每满 5 回合降 1 点；paid_action_seq 是所有真正付了时间的行动的序号，
    # 篡改预警靠它判断「玩家又完成一次耗时行动」。
    chaos: int = 0
    chaos_decay_credit: float = 0.0
    paid_action_seq: int = 0
    tamper_sequence: int = 0
    memory_effect_awards: list[str] = field(default_factory=list)
    # 扩展包记忆碎片的「缓冲」消耗登记：碎片 id → 作用域键（层/局/遭遇）。
    # 换层、重装碎片即重新装满；见 core/memory_buffers.py。
    memory_buffers: dict[str, str] = field(default_factory=dict)
    quiet_step_ready: bool = False
    # §11 §7（2026-10-20）：无声步改为等待后 2 次移动、4 回合内有效。
    quiet_step_charges: int = 0
    quiet_step_until: int = 0
    # 噪声耐受：等待后 4 回合内，下一次自身非诱引声音忽略回声征兆放大一次。
    echo_ward_until: int = 0
    # 借声藏步：被远端实际声音掩护后，下一步脚步声 ×0.5（2 回合内，一份）。
    masked_step_until: int = 0
    # 听声辨向：等待后 4 回合内，线索显示远近档。
    sound_bearing_until: int = 0
    # 凝听（docs 261022 §16.3）：这次等待及其后一个真实回合内接收阈值 −4；
    # 重复等待只刷新期限，不叠层。
    listen_until: int = 0
    # 听界（docs 261022 §16.4）：持续 3 回合，把实际传到玩家的声音记成精确
    # 发声格标记；标记只记声音发生点与时刻，不跟随实体。
    listen_realm_until: int = 0
    precise_sound_markers: list[dict] = field(default_factory=list)
    # 循声定位：凝听期间同一地点在不同真实时刻各听见一次（余量 ≥4）才确认；
    # 最近一次确认保留 2 回合。sightings 是确认前的两次聆听记录。
    sound_sightings: list[dict] = field(default_factory=list)
    confirmed_sound_sources: list[dict] = field(default_factory=list)
    # 蜂鸣回响：广播加成可在洞察详情里关闭，开关本身不发声、不耗时。
    buzzing_echo_enabled: bool = True
    # 灰烬记忆：同一层同一墙格的碎裂奖励只结算一次（旧档缺省为空）。
    ash_memory_settled: list[str] = field(default_factory=list)
    system_roles_version: int = 1
    # Oct19 learned environments, sound insights and per-item memory revisions.
    environment_rework_version: int = 1
    # §15.3 地势档位口径：旧档缺字段 → 0，载入时体检并备份提示；新局直接写 1。
    terrain_scale_version: int = 1
    tamper_pressure: int = 0
    tamper_pressure_gap: int = 10
    tamper_pressure_idle: int = 0
    construct_environments: list[dict] = field(default_factory=list)
    book_offer_sequence: int = 0
    # Stable layer keys keep main-dream and nested-dream deletion budgets apart.
    world_tamper_deletes: dict[str, int] = field(default_factory=dict)
    tamper_records: dict = field(default_factory=dict)
    dream_type_choice: dict = field(default_factory=dict)
    dream_type_mods: dict = field(default_factory=dict)
    identity_state: dict = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    # 顶部滚动播报专用通道（2026-10-12）：异象技能蓄力/准备类预告只上标题栏
    # 跑马灯，不进事件记录——它们是「正在进行」的瞬时状态，不是发生了的事。
    # 易失队列：不持久化，读档后自然为空。
    ticker_notes: list[str] = field(default_factory=list)
    # §11 H1 听觉线索：只保存最近 2 个真实回合的方向／距离档／类别，
    # 未知声源不写敌名与精确坐标。易失队列，不持久化。
    heard_sound_clues: list[dict] = field(default_factory=list)
    # 延时声源（2026-10-22 P3）：蜂鸣诱饵落地后在第 3、6 回合各再响一次。
    # 每项 {"x","y","due","radius","source"}，due 是绝对回合坐标；到点由
    # `_tick_delayed_sounds` 走真实声路重放，然后从表里摘掉。
    delayed_sounds: list[dict] = field(default_factory=list)
    # 上一处**实际**诱引落点（扩展包构想「返场」要重放的就是它）：
    # {"x","y","radius","full_alert","turn","depth"}。重放与齿轮转发不写这里。
    last_lure: dict = field(default_factory=dict)
    # 分层燃油（2026-10-22 P3）：焦油弹的十字燃油总量 60，分三批各 20 达成。
    # 每项 {"cells": [[x,y,amount],...], "due": 绝对回合}，由 `_tick_delayed_fuel`
    # 到点泼下；只加燃油、不重复点燃（点火伤害只算落点那一次）。
    delayed_fuel: list[dict] = field(default_factory=list)
    next_enemy_id: int = 1
    fire_unlocked: bool = False
    # 「点火」许可是否由盘面授予（点火手套等）。只有盘面给的许可才随卸装收回；
    # 事件／构想习得的许可（actions.py 的 fire_unlocked = True）不会被卸装抹掉。
    fire_from_board: bool = False
    projectile_charges: int = 0
    # 统一发射源（2026-10-21）：0 = 旧存档尚未迁移；新局从 1 起。
    firing_sources_version: int = 1
    # 旧档永久发射许可迁移出的「基础发射（旧档继承）」独立来源。
    # None = 该局没有继承来源；否则只保存这颗来源自己的匣量与换弹进度。
    legacy_basic_magazine: int | None = None
    legacy_basic_reload_steps: int = 0
    legacy_basic_reload_paid: bool = False
    world_items: list[WorldItem] = field(default_factory=list)
    events: list[WorldEvent] = field(default_factory=list)
    inventory: list[Item] = field(default_factory=list)
    # 携带意象联想盘（8×6）是装备的唯一权威。旧五栏 `equipped` 只是兼容读取
    # 视图（见 EquipmentBoardMixin / EquipmentView.compat_slots），不参与结算。
    board: EquipmentBoard = field(default_factory=EquipmentBoard)
    # 联想反馈的玩家级状态：共享冷却、有限缓冲、待释放脉冲、本回合已成功次数。
    # 它们不是派生缓存——移位、卸装、换焦点、重连、另放同类插片、存读档都不刷新。
    board_cooldowns: dict = field(default_factory=dict)
    board_buffer: dict = field(default_factory=dict)
    board_pending: list = field(default_factory=list)
    board_feedback_round: int = 0
    # Fixed-point player-level damage remainder; rearrangement never resets it.
    equipment_damage_credit: dict[str, int] = field(default_factory=dict)
    equipment_event_budget: dict = field(default_factory=dict)
    equipment_marks: dict[str, dict] = field(default_factory=dict)
    # 接触端去重：上一回合站过的格、以及「本格+本材料」已经发过一次事件的记录。
    # 站着不动的每回合不重复发接触事件；换了格或换了材料才再发。
    board_previous_cell: tuple | None = None
    board_touch_cell: tuple | None = None
    board_touch_material: str = ""
    memory_fragments: list[str] = field(default_factory=list)
    # 记忆槽已满时待处理的碎片 id：由界面弹出「替换 / 放弃」面板结算
    # （与 pending_insight 同一套交互，见 ui.input 的 pending_memory 分支）。
    pending_memory: str | None = None
    # 复合事件的对话状态：唤起面板的事件 id（收起即置 None，不进存档语义）。
    pending_event_id: str | None = None
    pending_event_uid: str | None = None
    # 稳定意识（NPC）对话状态：唤起面板的实体 id。
    pending_npc_id: str | None = None
    # 深层边界（28–30）：剧情旗标 / 本局统计 / 终局结局 id。
    epilogue_flags: dict = field(default_factory=dict)
    run_stats: dict = field(default_factory=lambda: {"kills": 0, "ignitions": 0, "events": 0, "items_used": 0, "hits_taken": 0})
    # NPC 任务系统：任务 id → 状态（active/done）；击杀按异象种类计数；赠品组已领记录。
    quests: dict = field(default_factory=dict)
    # 接取瞬间的累计量快照（quest id → {计数名: 值}）。进度按
    # 「当前累计 − 接取时累计」计算：§16.1「接取前击杀不计完整狩猎」——
    # 否则在下层接了「解决 4 只」的任务，回头一看已经完成了。
    quest_baselines: dict = field(default_factory=dict)
    # 本局身份（重构方案 §13.2）：所有稳定 UID 的前缀，跨层跨存档不变。
    # 只用于命名，不参与任何数值计算，因此带一个生成时刻的后缀。
    run_uid: str = ""
    # 快照之外的持久世界记录（§12.2）：角色身份、设施状态、地形增量与行动事实。
    world_ledger: Any = field(default_factory=WorldLedger)
    # 玩家点燃的火焰格（§4.4 归因）：层键 → 格坐标集。只有「亲手点的火及其
    # 蔓延/引爆波及」才进这册——异象放的火、自然扩散不归因玩家；火熄灭即除名
    # （_set_flame 归零时清）。旁表而非 Cell 字段：不进紧凑格编码，旧档兼容。
    _ignition_owner: dict = field(default_factory=dict)
    kills_by_kind: dict = field(default_factory=dict)
    gift_claims: dict = field(default_factory=dict)
    deepest_depth: int = 1
    ending_id: str = ""
    epilogue_profile: str = ""
    # 新手引导（0 层「梦的起始」）：active/step/skipped/stations 步骤表；
    # tutorial_events 是 UI 埋点写旗标的暂存（步骤推进即清空）；
    # doll_respawns 是玩偶意识体的重生队列 [(到点回合, x, y), ...]。
    tutorial: dict = field(default_factory=dict)
    tutorial_events: dict = field(default_factory=dict)
    doll_respawns: list = field(default_factory=list)
    # 死因跟踪（旧梦回忆用）：最后一次真实命中玩家的来源与回合。
    # 异象命中写 (label, time)；环境死因（火焰/气体/液体等）在死亡判定时按
    # 现场推导。深层边界死亡直接归「沉没于深层边界」。
    last_harm_source: str = ""
    last_harm_time: int = -9999
    # 本局已写入游玩历史（防重复记录；随存档持久化）。
    history_recorded: bool = False
    # ---- 梦中梦（2026-09-21，支线系统）----
    # realm_id 非空 = 正在梦中梦里；depth 始终保持**主梦**的层号（区域/主题不乱），
    # 层内层号走 realm_depth（从 1 起）。entry_* 记录入口（返回用）。
    realm_id: str = ""
    realm_depth: int = 0
    entry_depth: int = 1
    entry_x: int = 0
    entry_y: int = 0
    # 累计击败强烈异象数 + 门之钥是否已掉落（每局一把，可反复使用）。
    strong_kills: int = 0
    key_dropped: bool = False
    # 玩具的回忆：层解谜状态（解谜随档保存）。通道是否打开改由 scene.lens_gate 的
    # 设施记录 flags（offered/paid/entered）决定（§8 S23），不再设独立布尔。
    realm_puzzle_solved: dict = field(default_factory=dict)  # depth -> True
    realm_gate_open: bool = False
    realm_plate_order: list = field(default_factory=list)
    realm_plate_progress: list = field(default_factory=list)
    # ---- 梦中梦·千禧园（2026-10-10，docs/millennium-garden-design.md）----
    # 格级显式底色带（§9）：生成器写入，渲染时命中格用 zone 色替代默认底色。
    # MAP_BG 恒黑不动——这是「地形自己带显式底色」的既有老口径。
    realm_bg_zones: list = field(default_factory=list)  # [{rect:(x0,y0,x1,y1), color:str}]
    realm_entry_state: dict = field(default_factory=dict)
    realm_features: dict = field(default_factory=dict)
    # 掉线拨号（§4）：触发判定挂 descend 入口。triggers_used 每局 2 次封顶；
    # layers_seen 记「已触发过/已挂断」的主梦层号（同层不再触发）。
    dial_in: dict = field(default_factory=dict)  # {triggers_used:int, layers_seen:[int], active:{rounds:int}|None}
    # ---- 梦中梦支线（2026-10-08：余烬廊桥 / 退潮厅）----
    # 本局已关闭（通关或失败）的位面 id：关门的入口不可再进，地图上的入口也被清理。
    closed_realms: set = field(default_factory=set)
    # 引火人（余烬廊桥固定 NPC）：开局一次性判定，存档只记这两个字段。
    # ember_npc_layer == 0 是「尚未判定」哨兵；判定后 11–19 随机。
    ember_npc_exists: bool = False
    ember_npc_layer: int = 0
    # 潮汐之门（退潮厅主梦随机门）：本局选定的宿主层号（0 = 尚未判定）。
    # 每局恰好一扇——按层号确定性安放，层快照被裁后重新生成也不会丢门。
    realm_gate_layer: int = 0
    # 退潮厅收缩进度：已吞环数（≥EBBING_MAX_RINGS 即失败）与是否已跨过出生门槛。
    ebbing_contract_rounds: int = 0
    ebbing_past_threshold: bool = False
    ebbing_elapsed: int = 0
    ebbing_warning_ring: int = -1
    realm_challenges: dict = field(default_factory=dict)
    # 位面生成器挂起的物品（与 _pending_realm_events 同构，生成后统并入）。
    _pending_realm_items: list = field(default_factory=list)
    # 构想（扩展包 v1）：凝滞 / 匿踪 / 共鸣 的剩余回合；玩家位置历史（回闪用）。
    stasis_turns: int = 0
    vanish_turns: int = 0
    resonance_turns: int = 0
    # NPC 一次性交易记账（2026-09-18）：稳定 actor_uid → 已完成的稳定 option_id 列表。
    # 每个交易选项只能买一次；「道别」等 leave 选项不记账。
    # 两端都用稳定 ID（重构方案 §2.1／§13.2）：坐标与显示下标会随 NPC 走动、
    # 货架重抽、show_if 过滤而变，拿它们记账会让「已买过」的账落到别的选项上。
    npc_traded_options: dict[str, list[str]] = field(default_factory=dict)
    # 免费赠送另记：同一 actor 最多领取 1–2 项，不能占用交易或任务名额。
    npc_free_claims: dict[str, list[str]] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)
    # 洞察已满时待处理的洞察 id：由界面弹出「替换 / 放弃」面板结算
    # （见 ui.input 的 pending_insight 分支与 _grant_insight）。
    pending_insight: str | None = None
    catalog: dict[str, dict[str, Any]] = field(default_factory=dict)
    # 旧梦层的快照缓存（depth -> LayerSnapshot）。每份快照都攥着整整一幅
    # Cell 网格（1200~3300 个对象），是运行期最大的常驻图。保留全部旧层会让
    # GC 每轮遍历的对象数随深度单调增长，表现为后期越来越卡（见
    # _trim_layer_states 的说明），因此这里只保留当前层附近的滑动窗口。
    layer_states: dict[str, LayerSnapshot] = field(default_factory=dict)
    next_item_id: int = 1
    victory: bool = False
    run_over: bool = False
    theme: str = LAYER_THEMES[0]
    map_form: str = "整齐的房间"
    # 本层修饰符（大型/小型/气密/潮湿/繁茂/古朴；空串 = 常规楼层）。
    # 由种子确定性推导（见 mapgen.layer_modifier_for），存档只是快照它，
    # 旧档缺省即"常规"，下次生成新层时会重新按种子推导。
    layer_modifier: str = ""
    layer_drop_counts: dict[str, int] = field(default_factory=dict)
    overwrite_count: int = 0
    sight_radius: int = 8
    # 内容扩展新增状态（全部带默认值，旧存档可直接载入）。
    developed_cells: dict[str, set] = field(default_factory=dict)  # depth -> 已显影格
    # ---- 玩家地图知识（2026-10-18，docs/261018方案合集.md 第 1 节）----
    # 稳定层键 -> {(x, y): TerrainMemory}；只存正常视野确认过的静态地形。
    # 与 layer_states 分开：层快照被裁掉/重建后，玩家的探索记忆不能蒸发。
    terrain_memory: dict = field(default_factory=dict)
    # §11 §7 地形记忆洞察：层键 -> {"x,y": 最近危险快照}，最多 8 处/层。
    hazard_memory: dict = field(default_factory=dict)
    # 全图地形已知增强（首版默认关闭，开局选择，随存档保存）；只授予地形，
    # 不写入普通探索快照，也不公开视野外生物/物品/环境读数。
    terrain_known: bool = False
    # 知识规则版本（旧档缺省 0 = 旧口径；新局写 1，供以后迁移）。
    map_knowledge_version: int = 0
    # 三层信息显示（2026-10-18 docs 第 1 节第二批）。2026-10-25 玩家定稿：
    # 这是默认能力、不是开局开关 —— 新局由 run_options.apply_run_options 一律
    # 置 True；字段本身保留（渲染/寻路/详情都按它分支），旧档仍按存档原值。
    # 打开后地图/悬停/详情按未知黑幕 + 暗色记忆 + 当前视野渲染，未授权格不再
    # 读取真实地形。裸构造（测试直接 GameState.new）仍是 False = 全知口径。
    map_memory_enabled: bool = False
    # 逻辑固体（内容扩展包 v1）：当前层的陷阱场景（"x,y"→名字）与灌注阀储备。
    trap_scenarios: dict[str, str] = field(default_factory=dict)
    valve_stored: dict[str, tuple] = field(default_factory=dict)
    circuit_boards: list[dict] = field(default_factory=list)
    _mind_fences: dict[tuple, int] = field(default_factory=dict)
    _rune_cooldowns: dict[tuple, int] = field(default_factory=dict)
    # 电路逻辑 v2：门类节点的本回合输入聚合（"x,y" → 来源位置集合，运行期）。
    gate_inputs: dict = field(default_factory=dict)
    _logic_energized: set = field(default_factory=set)
    _gate_evaluating: bool = False
    # 测试模式「自我增强」开关（运行期，不入档不入存档）。
    debug_full_vision: bool = False
    debug_mind_invincible: bool = False
    debug_lucidity_invincible: bool = False
    debug_imagination_infinite: bool = False
    # 异象技能 v3（2026-09-22）：敌人抛出的落点炸弹 [x, y, 引信, 半径, 威力]。
    # 运行期战斗瞬态，不入档（persistence runtime_caches 排除）。
    enemy_bombs: list = field(default_factory=list)
    # 异象主动技能（2026-10-08）：玩家动作序号——每次「行动」入口（含免费
    # 行动）递增一次；_force_end_round 不另增。它是「预警不得在同一玩家动作
    # 内创建并结算」的公平窗口门槛（见 core/enemy_skills.py）。
    action_seq: int = 0
    # 主动技能效果场（来源/寿命/实际格/渠道/每拍伤害/叠加族），随层快照。
    enemy_skill_fields: list[dict] = field(default_factory=list)
    # 弹道动画（2026-09-23）：最近一次射击/投掷的飞行路径回放缓存。FX 层按
    # seq 去重拾取、按墙钟回放 0.3s——纯装饰，回合逻辑早已结算完毕。
    # 运行期瞬态不入档（persistence runtime_caches 排除）。
    last_projectile: dict | None = None
    projectile_seq: int = 0
    # 激活短光（2026-10-20，§12 D 残余）：显影方尖点亮、感应符文墙感知时压入
    # 的带寿命演出记录（core/light_flash.note_light_flash）。UI 按 seq 差分拾取；
    # 纯装饰，不入档（persistence 的 runtime_caches 排除）。
    light_flashes: list[dict] = field(default_factory=list)
    # 命中表现事件（2026-10-24，手感方案 §3.1）：有界队列，只服务 UI 的
    # 定向抖动/伤害跳字/命中音；纯运行期事实，不入档（persistence
    # runtime_caches 排除）。
    presentation_hits: list[dict] = field(default_factory=list)
    hit_event_seq: int = 0
    # 构筑桥接组件（2026-10-08，平衡方案 §6.1）的运行期瞬态，全部不入档：
    # 折射印记：enemy_id -> {"until": 到期客观时间, "dir": 命中时的飞行方向}。
    refract_marks: dict = field(default_factory=dict)
    # 每层一次型组件的已用标记：组件名 -> 使用它的那一层（下潜/回层自然失效）。
    # 附着追猎的「已报出材料」也记在这里（键含层数与目标 id），这样这份瞬态
    # 只有 dict 一种形状——旧版的 set 字段会把 json 序列化的测试夹具炸掉。
    bridge_once: dict = field(default_factory=dict)
    # 潮润传导下次可用的客观时间（冷却）；0 = 未用过。
    wet_conduct_ready: int = 0
    # 回声控场已武装的层数（-1 = 未武装；同层的一次成功脉冲武装下一次的控制）。
    echo_armed_depth: int = -1
    # 留白免成本已用掉的层数（-1 = 本层还没用）。
    blank_pass_depth: int = -1
    # 免成本正在生效（activate_ability 与构想内部扣费共用一条口径）。
    blank_pass_pending: bool = False
    tear_drinks: dict[str, int] = field(default_factory=dict)  # depth -> 泪滴溶液已恢复量
    honey_drinks: dict[str, int] = field(default_factory=dict)  # depth -> 蜂蜜已恢复量
    # 主动构想：已习得 / 冷却剩余回合 / 持续型效果剩余回合
    abilities: list[str] = field(default_factory=list)
    # 被无字校对员「涂黑」的构想：ability_id → 剩余回合（期间不可激活）。
    redacted_abilities: dict = field(default_factory=dict)
    ability_cooldowns: dict[str, int] = field(default_factory=dict)
    library_bookmark: dict = field(default_factory=dict)
    ability_turns: dict[str, int] = field(default_factory=dict)
    slick_cells: dict[str, set] = field(default_factory=dict)  # depth -> 湿滑格
    resolved_kinds: set = field(default_factory=set)  # 已首次解决的异象 catalog_id
    developed_total: int = 0
    viscous_debt: float = 0.0
    # 加速侧的分数回合欠账：行动成本可以小于 1 回合（例如 0.5），零头先记在这里，
    # 攒满 1 才推进一次整数回合。与 viscous_debt（减速侧）对称，time 因此始终是
    # 精确整数刻度——不要改成浮点，理由见顶部「时间轴术语」。
    round_debt: float = 0.0
    # 「行动层」窗口计数：本回合内已发生的玩家行动次数。跨过回合刻度或被强制
    # 结束回合时清零，所以它是「距上一道回合刻度过去了多少次行动」。
    _action_count: int = 0
    free_liquid_moves: int = 0
    free_actions: int = 0
    # 双重曝光底片的免费行动窗口（2026-10-22 P3）：绝对回合坐标，到点自动作废。
    # 0 = 没有窗口（旧档／其它来源），行为与旧版一致。
    free_action_until: int = 0
    free_move_pending: int = 0
    parry_charges: int = 0
    # 镜面碎片的招架期限（2026-10-22 P3）：绝对回合坐标，到点这一片自己碎掉。
    # 0 = 没有设过期限（旧档／非镜面来源），此时只按次数消耗，行为与旧版一致。
    parry_until: int = 0
    overclock_turns: int = 0
    drug_debts: list[dict[str, Any]] = field(default_factory=list)
    drug_debt_version: int = 0
    item_grant_counts: dict[str, int] = field(default_factory=dict)
    modem_boost_until: float = 0.0
    modem_recovery_until: float = 0.0
    light_turns: int = 0
    # R03 留灯的避难圈「抵抗窗口」：连续安全满若干回合后授予玩家的一段限时 buff，
    # 只把 ``portent_ward_id`` 那种明示负面征兆的**新沾染**时长缩短 25%（见
    # core/portents.py）。它是玩家级限时状态、跨层保留（不同于 light_turns 的换层
    # 清零），走完即止；旧存档缺省 = 无窗口。
    portent_ward_turns: int = 0
    portent_ward_id: str = ""
    turns_since_descend: int = 0
    # 朝向（UI 的 DreamApp.facing 镜像）：移动/开火时更新，火墙构想等 core 侧效果使用。
    facing: tuple[int, int] = (1, 0)
    # 稀有度保底（2026-09-18）：距上次抽中「稀有 / 非常稀有」的层数。
    # 每 3 层保底一件稀有、每 6 层保底一件非常稀有（固定投放不计入）。
    layers_since_rare: int = 0
    layers_since_very_rare: int = 0
    hang_item_id: str | None = None
    hover_target: tuple[int, int] | None = None
    # 上次气体时间消散结算对齐到的回合数：每过 GAS_DECAY_INTERVAL 回合
    # 全图气体按各自 dissipation 扣减一次。
    gas_decay_mark: int = 0
    # 上次液体挥发结算对齐到的回合数（同气体，按 LIQUID_DECAY_INTERVAL）。
    liquid_decay_mark: int = 0
    # 上次地板吸水结算对齐到的回合数（按 LIQUID_ABSORB_INTERVAL，海绵聚合物用）。
    # 与 liquid_decay_mark 分开计时，这样吸水才能按「每 2 回合一点」的节奏渐进，
    # 而不是攒到挥发周期里一次性扣掉。
    liquid_absorb_mark: int = 0
    # 时间偷取：buff 持续期内限制玩家「每回合的行动次数」。0 = 未激活（回落到
    # ACTION_COUNT_LIMIT 保底上限），详见 _note_action / _effective_action_limit。
    steal_cap: int = 0
    # §9 近战包围位的本回合预约：enemy id -> 攻击格。每回合异象行动开头清空，
    # 只约束当前行动，不参与存档，也不把整条长路径占住。
    nav_slot_claims: dict[str, tuple[int, int]] = field(default_factory=dict)
    # §5.1 / §9 非攻击格的短时预约：enemy id -> 站位格（支援位、撤退位、
    # 距离带落点、封路位）。与 nav_slot_claims 同一生命周期（每回合清空、
    # 不写存档），作用是「同一回合别让两只异象抢同一格站位」。
    nav_hold_claims: dict[str, tuple[int, int]] = field(default_factory=dict)
    # 按行动次数结算的效果共用计数：ActionKind -> 累计次数（不看客观时间）。
    action_counts: dict[str, int] = field(default_factory=dict)
    # 植物布局的变更计数：发光（core/vision/glow.py）算出的照亮范围与视野
    # 集合都缓存着，靠这个计数失效——因此运行时改 Cell.plant 一律走
    # set_plant / trample_plant，不要直接给 cell.plant 赋值（不参与存档）。
    plant_revision: int = 0
    # 可听拓扑变更计数（门开合、墙体破坏等）：调查任务因旧路线不可达被
    # 挂起后，只有拓扑真的变了才重新尝试，避免每回合重复寻路。
    topology_revision: int = 0


    @property
    def inventory_capacity(self) -> int:
        return 20

    @property
    def inventory_used(self) -> int:
        """已占用的行囊格数：**已装备的携带意象不计入**。

        携带意象一旦挂进栏位就"穿在身上"，不再占背包位置——玩家反馈
        「已装备携带意象，带 *，不再占用背包位置」。否则五个栏位全满时
        会白白吃掉 5 格容量，且与「栏位 = 独立空间」的直觉冲突。

        判定与界面上的 * 标记同一口径：instance_id 出现在联想盘上即视为已装备。
        """
        equipped_ids = self.board.placed_instance_ids()
        return sum(
            1 for item in self.inventory
            if item.instance_id not in equipped_ids
        )

    def inside_board(self, x: int, y: int) -> bool:
        """世界格坐标是否在场内（联想反馈落点校验用）。"""
        return 0 <= x < self.width and 0 <= y < self.height

    @property
    def _material_index_ready(self) -> bool:
        """材料索引与可见集合的缓存是否仍可信。

        2026-10-22 收口：以前它是裸属性，材料结算把它置 False 时不会有任何
        版本信号；现在改成 property，每个生产侧置 False 的写点都顺带推进
        ``_sight_revision``，让 ``visible_cells()`` 能在同一世界时刻内感知
        气体／烟雾／火／墙的变化（§10.5 最后半边）。
        """
        return bool(getattr(self, "_material_index_ready_value", False))

    @_material_index_ready.setter
    def _material_index_ready(self, ready: bool) -> None:
        self._material_index_ready_value = bool(ready)
        if not ready:
            self._sight_revision = int(getattr(self, "_sight_revision", 0)) + 1


    def cell(self, x: int, y: int) -> Cell:
        return self.cells[y][x]

    def set_plant(self, x: int, y: int, code: int) -> int:
        """改写某格的植物码，返回原值（0 = 原本没有植物）。"""
        return self.set_plant_at(self.cells[y][x], code)

    def set_plant_at(self, cell: Cell, code: int) -> int:
        """按格子对象改写植物码，返回原值。

        植物在运行时只有四个变更通道：拔除、被液体淹死、被火烧尽、被踩踏。
        它们全部经这里落地（坐标形式的 :meth:`set_plant` 也走这里），好让
        ``plant_revision`` 推进一格——发光范围与视野缓存的失效全靠它
        （见 core/vision/glow.py、core/vision/sight.py）。
        """
        previous = cell.plant
        if previous != code:
            cell.plant = code
            cell.plant_fuel = 0
            # 换种即视为另一株：旧株的一次性标记与剩余预算不能跟着新株走，
            # 否则「踩倒的蒲草」会继承挺立态的方向/预算。
            cell.plant_state = {}
            self.plant_revision += 1
        return previous

    def trample_plant(self, x: int, y: int, holder: Entity | None = None) -> int:
        """踩踏某格的植物：高丛被踩折成低草，其余植物不变（无提示）。

        返回踩踏后的植物码；同一格反复踩踏不会反复触发（第二次起仍是低草），
        没有真实变化时不登记视觉事件——踩草是无声的。

        例外：**柔软聚合物**地板（软垫）护住植物，踩过不折（地板效果，
        见 materials/floors.py）。

        ``holder`` 是踩上来的生物（玩家或失控意识）：给了就顺带结算这株植物的
        **踩踏反应**（征兆挂给踩踏者、气体/液体释放到他脚下，见 PlantDef 的
        trample_* 字段）——**对异象同样成立**，不只是玩家。反应按「踩踏前」的
        植物码判定，所以高丛踩折成低草也不会把低草的反应算进来。
        """
        cell = self.cells[y][x]
        if not cell.plant:
            return 0
        if floor_effect_for(cell).protects_plants:
            return cell.plant
        previous = cell.plant
        definition = plant_def_for(previous)
        release = getattr(definition, "release", None)
        # 踩踏快照必须在形变/销毁前保存旧植物码，供视觉事件按真实反应播一次。
        visual_before = plant_visual_snapshot(self, holder, x, y) if holder is not None else None
        if holder is not None and release is not None and release.allows("trample"):
            # 释出型：统一管线自己负责「移除本株 → 液体 → 点火 → 放电 → …」，
            # 踩与拔共享 `plant_state['released']`，不会拿两份。
            from .plant_release import apply_plant_release
            done = apply_plant_release(
                self, holder, x, y, previous, "trample",
                removal_code=trampled_code(previous),
            ) or {}
            code = cell.plant
            emit_plant_reaction_visual(
                self, holder, x, y, previous, code, done, {},
                visual_before, kind="plant.trample", trigger="trample",
                materials_are_external=True,
            )
            return code
        code = trampled_code(previous)
        if code != previous:
            self.set_plant(x, y, code)
        reaction = {}
        if holder is not None:
            reaction = self.apply_plant_trample(holder, x, y, previous) or {}
            emit_plant_reaction_visual(
                self, holder, x, y, previous, code, {}, reaction,
                visual_before, kind="plant.trample", trigger="trample",
            )
        return code

    def plant_move_penalty_at(self, x: int, y: int) -> float:
        """走进 ``(x, y)`` 时植物给出的额外耗时（世界回合）。

        规则口径（docs 2026-10-26 §3.1.3）：同类取**最强值**，不叠加；半径 0
        只作用于本格，半径 1 覆盖切比雪夫 ≤1 的一圈（不含本格的斜角夹死格）。
        玩家与异象共用这一个查询，避免「玩家被拖慢、异象不受影响」的分叉。
        """
        from ..materials import plant_move_penalty
        best = 0.0
        if not (0 <= x < self.width and 0 <= y < self.height):
            return best
        penalty, _radius = plant_move_penalty(self.cells[y][x].plant)
        best = max(best, penalty)
        for ny in range(max(0, y - 1), min(self.height, y + 2)):
            for nx in range(max(0, x - 1), min(self.width, x + 2)):
                if (nx, ny) == (x, y):
                    continue
                penalty, radius = plant_move_penalty(self.cells[ny][nx].plant)
                if penalty and radius >= 1:
                    best = max(best, penalty)
        return best

    def entity_at(self, x: int, y: int) -> Entity | None:
        if (self.player.x, self.player.y) == (x, y):
            return self.player
        return next((enemy for enemy in self.enemies if (enemy.x, enemy.y) == (x, y) and enemy.integrity > 0), None)

    @property
    def lucidity_tier(self) -> int:
        return 0 if self.lucidity >= 50 else 1 if self.lucidity >= 25 else 2 if self.lucidity >= 1 else 3

    @property
    def mind_tier(self) -> int:
        return 0 if self.mind >= 50 else 1 if self.mind >= 25 else 2 if self.mind >= 1 else 3

    def physics_modifiers(self) -> dict[str, int]:
        # 2026-10-15 混乱化改造：穿墙/爆炸加成按档位翻倍（×2），把「状态越低、
        # 场面越失控」的差距拉开——健康档（0）依旧完全稳定，紧急档等于双倍威力。
        instability = self.lucidity_tier
        disorder = self.mind_tier
        return {
            "instability": instability,
            "disorder": disorder,
            "penetration_bonus": instability * 2,
            "solidity_penalty": instability,
            "explosion_bonus": disorder * 2,
            "fire_spread_bonus": disorder,
        }

    def _announce_tier_drop(self, axis: str, tier_before: int) -> None:
        """跨档广播（2026-10-15 混乱化改造）：心理轴（mind/lucidity）跌进更深
        的一档时追加一条明确的失控横幅——「状态健康时保持稳定，状态低时更加
        失控」必须让玩家看得见，而不是只在状态栏的档位字里悄悄变化。"""
        tier_after = self.lucidity_tier if axis == "lucidity" else self.mind_tier
        if tier_after <= tier_before or tier_after < 1:
            return
        label = tr("清醒") if axis == "lucidity" else tr("心智")
        wording = {
            1: tr("【{axis}·受损：环境开始不稳】"),
            2: tr("【{axis}·危险：效果开始失控】"),
            3: tr("【{axis}·紧急：梦境彻底失控！】"),
        }.get(tier_after)
        if wording:
            self.messages.append(wording.format(axis=label))

    def insight_active(self, insight_id: str) -> bool:
        return insight_id in self.insights

    def _ensure_innate_insights(self) -> list[str]:
        """补齐与生俱来的洞察（``INNATE_INSIGHTS``，目前只有「双读」）。

        它们是开局自带的能力：新游戏在生成第一层时就补上，旧存档在载入时补上，
        任何一次授予通道碰到它们都只会静默补位——「获得现实洞察」的提示因此
        永远不会为它们出现。返回这次补进来的洞察 id。
        """
        added: list[str] = []
        for insight_id in reversed(INNATE_INSIGHTS):
            if insight_id not in INSIGHT_DEFINITIONS or insight_id in self.insights:
                continue
            # 插到最前面：它们是「基础能力」，理应排在其他洞察之前。
            self.insights.insert(0, insight_id)
            added.append(insight_id)
        return added

    def _grant_insight(self, insight_id: str | None) -> str:
        """授予洞察（事件回应 / 物品使用 / 强力异象掉落三条通道共用）。

        同名洞察不可重复获得；已拥有或无效 id 返回空串，成功授予返回提示文本。
        与生俱来的洞察（双读）不走这条通道：静默补位，不报「获得」。

        上限顶满时**不再自动顶替**：把待授予的洞察挂到 ``pending_insight``，
        由界面弹出「选择一个替换 / 放弃」的左侧面板（见 ui.input 的
        pending_insight 分支）。自动顶替最旧一条会让玩家在毫无察觉的情况下
        丢掉一条自己攒来的洞察——这正是要改掉的行为。
        """
        if not insight_id or insight_id not in INSIGHT_DEFINITIONS:
            return ""
        if insight_id in INNATE_INSIGHTS:
            self._ensure_innate_insights()
            return ""
        if insight_id in self.insights:
            return ""
        if len(self.insights) >= INSIGHT_LIMIT:
            self.pending_insight = insight_id
            return tr("现实洞察已满：{name} 无处安放，需要替换或放弃。", name=tr(insight_id))
        message = tr("获得现实洞察：{name}。", name=tr(insight_id))
        self.insights.append(insight_id)
        self.messages.append(message)
        return message

    def replace_insight(self, old_id: str) -> str:
        """把 ``pending_insight`` 顶替掉 ``old_id``；返回提示文本。"""
        from .action_permissions import stasis_refusal
        refused=stasis_refusal(self)
        if refused is not None: return refused.message
        new_id = self.pending_insight
        if not new_id or new_id not in INSIGHT_DEFINITIONS:
            self.pending_insight = None
            return ""
        if new_id in self.insights:
            self.pending_insight = None
            return ""
        if old_id in self.insights:
            self.insights.remove(old_id)
        self.insights.append(new_id)
        self.pending_insight = None
        message = tr("现实洞察 {name} 取代了 {replaced}。", name=tr(new_id), replaced=tr(old_id))
        self.messages.append(message)
        return message

    def discard_pending_insight(self) -> str:
        """放弃这次洞察：清空 ``pending_insight``，身上洞察原样不动。"""
        if not self.pending_insight:
            return ""
        name = self.pending_insight
        self.pending_insight = None
        message = tr("放弃了现实洞察 {name}。", name=tr(name))
        self.messages.append(message)
        return message

    def _add_wall_break_dissolution(self, wall_name: str) -> None:
        """玩家用子弹/推动击碎高耐久墙体：崩解度固定 +1。

        这条是「击碎大结构」的直接规则，不吃局外崩解倍率，也不被「深层耐性」
        折半——规则写的是提升一点，就只提升一点。其他破坏方式与非玩家破坏
        不调用这里。
        """
        if self.dissolution >= 100:
            return
        self.dissolution += 1
        self.messages.append(tr("{name}的碎片落进梦里——崩解度 +1。",
                                name=tr(wall_name)))
        if self.dissolution >= 100:
            self.messages.append(tr("崩解度已达 100：可以下潜了（按 N）。"))

    def _add_dissolution(self, amount: int) -> None:
        if amount <= 0:
            return
        # 开局选项「异象强度/迟滞崩解/躁动之梦」：崩解度增速倍率（先进倍率，
        # 再算「深层耐性」减半，两个减益独立叠乘）。
        mult = self._dissolution_mult()
        if mult != 1.0:
            amount = max(1, int(amount * mult + 0.5))
        if self.insight_active("深层耐性") and self.dissolution >= 50:
            amount //= 2
        before = self.dissolution
        self.dissolution = min(100, self.dissolution + amount)
        if before < 100 <= self.dissolution:
            # 达到 100 的当刻立刻提示（崩解度即「可下潜」条件）。
            self.messages.append(tr("崩解度已达 100：可以下潜了（按 N）。"))

    # ---- 携带意象联想盘 ----

    def equipped_item(self, slot: str) -> Item | None:
        """兼容查询：某旧栏位名对应的盘上物品。"""
        instance_id = self.equipped.get(slot)
        if not instance_id:
            return None
        return next((item for item in self.inventory if item.instance_id == instance_id), None)

    def equipped_items(self) -> list[Item]:
        """盘上已生效语句注册的装备（未成句的词块不算，备用武器不算）。"""
        return self.equipment.items()

    def equipped_effect_ids(self) -> set:
        """已生效装备的效果 id 集合（含携带意象/惯用物）。"""
        return self.equipment.effect_ids()

    def _effect_power(self, effect: str) -> int:
        """某效果的**递减后**总效力（§7.1；共鸣在汇总后只乘一次）。"""
        return self.equipment.effect_power(effect)

    def _blank_edge_threshold(self) -> int:
        """兼容查询：已装备留白件的最大阈值；回流逐件判断，不用此值合并。"""
        return max(
            (ability.power_secondary
             for ability in self.equipment.compiled().abilities
             if ability.effect == "blank_edge"),
            default=0,
        )

    def weapon_damage(self) -> int:
        """Unconditional melee preview. Actual hits claim their context budget."""
        return 1 + int(self.equipment.plan_action("melee").damage_increment)

    # 2026-10-22 端口清理：同名重复定义曾出现两次（同体），保留一份。
    def _blank_edge_bonus(self, resonance: bool | None = None) -> int:
        """Each piece uses its own threshold; stacking caps extra reflow at three."""
        contributions = [
            (ability.power, ability.instance_id)
            for ability in self.equipment.compiled().abilities
            if ability.effect == "blank_edge"
            and self.imagination <= ability.power_secondary
        ]
        resonating = self.resonance_turns > 0 if resonance is None else resonance
        return min(3, diminish_int(contributions, resonating))

    def _note_projectile(
        self,
        cells: list[tuple[int, int]],
        bounces: list[tuple[int, int, int]],
        *,
        kind: str,
        color: str,
        end: str,
        end_cell: tuple[int, int] | None,
        repeat_delay: float = 0.0,
        origin: tuple[int, int] | None = None,
    ) -> None:
        """记录最近一次射击/投掷的飞行路径（弹道动画回放输入，2026-09-23）。

        连发只保留最新一条（覆盖式）；``bounces`` 是 (路径转向下标, 跳弹格 x,
        跳弹格 y)；``end ∈ {entity, wall, gap, range, land}`` 决定收尾演出。
        """
        self.projectile_seq += 1
        self.last_projectile = {
            "seq": self.projectile_seq,
            "cells": [[x, y] for x, y in cells],
            "bounces": [[idx, x, y] for idx, x, y in bounces],
            "kind": kind,
            "color": color,
            "end": end,
            "end_cell": [end_cell[0], end_cell[1]] if end_cell else None,
        }
        if origin is not None:
            self.last_projectile['origin'] = list(origin)
        if repeat_delay > 0:
            self.last_projectile['repeat_delay'] = min(.12,repeat_delay)
        # 命中表现事件先于弹道登记（core 先结算伤害、后回放弹道），这里把
        # 同一动作的命中事件挂到这一发上，UI 才能把命中时刻对齐飞行落点。
        from .hit_events import attach_projectile
        attach_projectile(self, self.projectile_seq)

    def _spawn_equipment(self, rng: random.Random) -> None:
        """房间低频刷新携带意象：稀有，占用本层刷新预算。

        池子按层混成：无意识领域以 T3 池为主（浅层池低频混入）；
        幻觉空间高层按距离衰减把 T3 池小概率混进来（越浅越稀有）。

        ⚠️ 出现率（2026-09-18 下调）：每层掉落物里带槽件一度占到 ~35%，
        其中这处随机刷新贡献 ~0.56 件/层（0.45 × 1.25）。既然定位是
        「低频稀有」，就按低频给：0.15 出现、10% 概率额外出第二件
        （≈0.17 件/层），把装备压回点缀的位置。数值改动前先看
        tests/test_equipment.py 与图鉴稀有度曲线是否还自洽。
        """
        if rng.random() >= 0.15:
            return
        # 区域分层池（2026-10-07 数值平衡改版）：T1 浅层 / T2 幻觉 / T3 无意识 /
        # T4 深层边界，混池规则见 content.equipment_pool_for_depth——此前 11–20 层
        # 一直沿用浅层池，21+ 层还有 2/3 概率掉 T1 破烂。
        pool = [key for key in equipment_pool_for_depth(self.depth)
                if not ITEM_DEFINITIONS.get(key, {}).get('expansion_catalog_id')]
        # §7.1 统一资格入口：房间刷新也是「从池里抽实物」，同样要过闸——
        # 否则将来任何带 min_depth／grant_source／run_limit 的带槽件都会从
        # 这条旁路漏出来（当前 T1—T4 池里暂无这类件，但不能靠「暂时没有」）。
        pool = self._award_eligible(pool, source="floor_scatter")
        if not pool:
            return
        count = 2 if rng.random() < 0.10 else 1
        for _ in range(count):
            rarity = roll_rarity(self.depth, rng, luck=self._loot_luck())
            rarity_pool = [item_id for item_id in pool if ITEM_DEFINITIONS[item_id].get("rarity") == rarity]
            # 回落顺序（2026-10-07 修正）：少见 → 稀有 → 非常稀有。旧顺序从
            # 「稀有」起回落，T2 池（少见+稀有）里抽中常见档会被直升成稀有，
            # 平白抬高一档掉落质量。
            for fallback in ("少见", "稀有", "非常稀有", "常见"):
                if rarity_pool:
                    break
                rarity_pool = [item_id for item_id in pool if ITEM_DEFINITIONS[item_id].get("rarity") == fallback]
                if rarity_pool:
                    rarity = fallback
            definition_id = rarity_pool[rng.randrange(len(rarity_pool))]
            if rarity == "稀有":
                self.layers_since_rare = 0
            if rarity == "非常稀有":
                self.layers_since_very_rare = 0
            x, y = self._find_open_cell(
                self.cells,
                rng.randrange(2, max(3, self.width - 2)),
                rng.randrange(2, max(3, self.height - 2)),
            )
            if (x, y) == (self.player.x, self.player.y):
                continue
            self.world_items.append(WorldItem(self._make_item(definition_id), x, y))

    def observed_entity_label(self, entity: Entity) -> str:
        """Temporary low-mind uncertainty; catalog and actual mechanics stay unchanged."""
        if self.mind_tier >= 2 and entity.id != "player":
            return tr("未定形轮廓")
        if self.mind_tier == 1 and entity.id != "player" and self.time % 3 == 0:
            return tr("像是") + tr(entity.label)
        return tr(entity.label)

    def _make_item(self, definition_id: str) -> Item:
        definition = ITEM_DEFINITIONS[definition_id]
        # 记忆碎片稀有度：按 MEMORY_RARITY 映射（物品定义表不写 rarity）。
        if definition.get("category") == "记忆碎片" and not definition.get("rarity"):
            from .content import MEMORY_RARITY

            rarity = MEMORY_RARITY.get(definition_id, "")
            if rarity:
                definition = {**definition, "rarity": rarity}
        item = Item(
            definition_id=definition_id,
            instance_id=f"item-{self.next_item_id}",
            name=definition["name"],
            category=definition["category"],
            slot=definition.get("slot"),
            description=definition.get("description", ""),
            color=definition.get("color", "bright_white"),
            rarity=definition.get("rarity", ""),
            max_stack=definition.get("max_stack", 1),
            effect=definition.get("effect"),
            power=definition.get("power", 0),
            power_secondary=definition.get("power_secondary", 0),
            penetration=definition.get("penetration", 0),
            push=definition.get("push", 0),
            explosion_radius=definition.get("explosion_radius", 0),
            projectile_template=definition.get("projectile_template", "直线弹体"),
            charges=int(definition.get("deploy_charges", 0) or 0),
        )
        self.next_item_id += 1
        from .firing_sources import ensure_magazine
        ensure_magazine(item)
        return item

    def _catalog_entry(self, key: str, name: str, category: str) -> dict[str, Any]:
        entry = self.catalog.setdefault(key, {})
        entry.setdefault("name", name)
        entry.setdefault("category", category)
        entry.setdefault("encounters", 0)
        entry.setdefault("interactions", 0)
        entry.setdefault("kills", 0)
        entry.setdefault("drops_seen", [])
        entry.setdefault("details", [])
        return entry

    def _record_catalog_interaction(self, key: str, name: str, category: str, detail: str) -> None:
        entry = self._catalog_entry(key, name, category)
        entry["interactions"] += 1
        if detail and detail not in entry["details"]:
            entry["details"].append(detail)

    def observe_visible_catalog(self) -> None:
        from .expansion_insights import observe
        observe(self)
        for enemy in self.enemies:
            if enemy.integrity <= 0 or enemy.catalog_observed or not self.is_visible(enemy.x, enemy.y):
                continue
            enemy.catalog_observed = True
            entry = self._catalog_entry(enemy.catalog_id, enemy.label, "consciousness")
            entry["encounters"] += 1

    def visible_anomalies(self) -> list[dict[str, Any]]:
        """视野中可见的失控意识（未死亡的），按「种类」聚合为实时观测条目。

        每条含：名称、字形、数量、属性（耐久 / 视野 / 移动耗时 / 攻速（=攻击耗时）/
        伤害 / 创伤类型 / 行为特征 / 类别）与介绍（description）。不在视野中的异象
        不计入——这是「此刻你看到了什么」，与主页图鉴（累计见闻）完全分离。

        「诅咒灵视」期间例外：灵视看见的也是看见，因此视野外的失控意识同样计入
        （它们的种类、属性与位置都会如实列出）。

        「攻速」与「伤害」是两件事：attack_time 是两次出手之间的间隔（越小越快），
        damage 是每次出手扣掉的心智/清醒点数（内容层可用 damage 键覆写，默认 1）。
        """
        groups: dict[str, dict[str, Any]] = {}
        # 2026-10-10 主动技能运行时状态：逐个体收集，聚合时蓄势取最急、
        # 等待取最长（同类多个体共用一行状态；等待=最早再起手的下界）。
        skill_statuses: dict[str, list[dict[str, Any]]] = {}
        revealed = self.reveals_anomalies
        for enemy in self.enemies:
            if enemy.integrity <= 0:
                continue
            # 2026-09-19 修正：稳定意识（NPC）不是异象，不进「观测界面」——
            # 旧实现把 NPC 也按异象聚合，导致 NPC 被描述成「失控意识/异象」。
            if enemy.relation != "失控意识":
                continue
            if not revealed and not self.is_visible(enemy.x, enemy.y):
                continue
            key = enemy.catalog_id
            grp = groups.get(key)
            if grp is None:
                definition = current_anomaly_definition(self, key)
                grp = {
                    "catalog_id": key,
                    "name": tr(enemy.label),
                    "glyph": enemy.glyph,
                    "count": 0,
                    "kind": tr(definition.get("anomaly_kind", enemy.anomaly_kind)),
                    "integrity": definition.get("integrity", enemy.integrity),
                    "vision": definition.get("vision", enemy.vision),
                    "move_time": definition.get("move_time", enemy.move_time),
                    "attack_speed": definition.get("attack_time", enemy.attack_time),
                    "damage": int(definition.get("damage", 1) or 1),
                    "trauma": tr(definition.get("trauma_type", enemy.trauma_type)),
                    "trait": definition.get("trait", enemy.trait),
                    "description": tr(definition.get("description", "")),
                    # 主动技能观测摘要（创伤渠道+当前层值、冷却）：观测展开与
                    # 右键详情共用同一份数据，见 data.anomaly_skills.skill_summaries_for。
                    "skills": current_skill_summaries(self, key),
                    "color": definition.get("color", "#cccccc"),
                }
                groups[key] = grp
            grp["count"] += 1
            skill_statuses.setdefault(key, []).append(self.skill_cooldown_status(enemy))
        entries = sorted(groups.values(), key=lambda g: g["name"])
        for entry in entries:
            collected = skill_statuses.get(entry["catalog_id"], [])
            charging = [s for s in collected if s.get("charging")]
            if charging:
                soonest = min(charging, key=lambda s: s.get("windup_left", 0))
                entry["status"] = soonest
                continue
            longest = max((int(s.get("cooldown_left", 0)) for s in collected), default=0)
            entry["status"] = {"cooldown_left": longest} if longest > 0 else None
        return entries

    def _record_catalog_kill(self, enemy: Entity, drops: list[str]) -> None:
        entry = self._catalog_entry(enemy.catalog_id, enemy.label, "consciousness")
        entry["encounters"] = max(1, entry["encounters"])
        entry["kills"] += 1
        detail = f"已解决；主要创伤：{enemy.trauma_type}。"
        if detail not in entry["details"]:
            entry["details"].append(detail)
        for drop_id in drops:
            if drop_id not in entry["drops_seen"]:
                entry["drops_seen"].append(drop_id)

    def _add_memory(self, memory_id: str) -> str:
        """收纳一条记忆碎片；返回被顶替掉的旧碎片 id（没有则空串）。

        与洞察的 ``_grant_insight`` 同一条思路：槽位顶满时**不再自动顶掉最旧的
        一条**，而是把待收纳的碎片挂到 ``pending_memory``，由界面弹出面板让玩家
        自己选替换哪条、或放弃。玩家的碎片是攒来的，静默丢弃既不可见也不公平。

        返回值语义保持向后兼容：真的发生了替换时返回被换下的 id，否则空串。
        """
        if memory_id in self.memory_fragments:
            return ""
        if memory_id not in ITEM_DEFINITIONS:
            return ""
        if len(self.memory_fragments) >= MEMORY_LIMIT + self._memory_slot_bonus():
            self.pending_memory = memory_id
            return ""
        self.memory_fragments.append(memory_id)
        self._apply_memory_effect(memory_id)
        return ""

    def replace_memory(self, old_id: str) -> str:
        """用 ``pending_memory`` 顶替 ``old_id``；返回提示文本。"""
        from .action_permissions import stasis_refusal
        refused=stasis_refusal(self)
        if refused is not None: return refused.message
        new_id = self.pending_memory
        self.pending_memory = None
        if not new_id or new_id not in ITEM_DEFINITIONS:
            return ""
        if old_id in self.memory_fragments:
            self.memory_fragments.remove(old_id)
            # 拆掉的碎片要把属性上限还回去（见 _drop_memory_effect）。
            self._drop_memory_effect(old_id)
        if new_id not in self.memory_fragments:
            self.memory_fragments.append(new_id)
            self._apply_memory_effect(new_id)
        message = tr(
            "记忆碎片 {name} 取代了 {replaced}。",
            name=tr(ITEM_DEFINITIONS[new_id]["name"]),
            replaced=tr(ITEM_DEFINITIONS.get(old_id, {}).get("name", old_id)),
        )
        self.messages.append(message)
        return message

    def discard_pending_memory(self) -> str:
        """放弃这次碎片：清空 ``pending_memory``，身上碎片原样不动。"""
        if not self.pending_memory:
            return ""
        name = ITEM_DEFINITIONS.get(self.pending_memory, {}).get("name", self.pending_memory)
        self.pending_memory = None
        message = tr("放弃了记忆碎片 {name}。", name=tr(name))
        self.messages.append(message)
        return message

    # ---- 记忆碎片效果 ----

    def memory_effect_ids(self) -> set[str]:
        """当前生效的碎片效果名集合（与 ``equipped_effect_ids`` 同构）。"""
        return {
            ITEM_DEFINITIONS[fragment_id].get("memory_effect")
            for fragment_id in self.memory_fragments
            if fragment_id in ITEM_DEFINITIONS
            and ITEM_DEFINITIONS[fragment_id].get("memory_effect")
        }

    def _memory_effect_defs(self) -> list[dict[str, Any]]:
        return [
            MEMORY_FRAGMENT_EFFECTS[name]
            for name in self.memory_effect_ids()
            if name in MEMORY_FRAGMENT_EFFECTS
        ]

    def memory_immune_portents(self) -> set[str]:
        """碎片带来的征兆免疫集合（免疫类效果汇总）。"""
        immune: set[str] = set()
        for effect in self._memory_effect_defs():
            if effect.get("kind") == "immunity":
                immune.update(effect.get("portents", ()))
        return immune

    def memory_portent_factor(self, portent_id: str) -> float:
        reduction = max((int(effect.get('accumulation_reduction', 0))
                         for entry_effect in self._memory_effect_defs()
                         for effect in self._memory_entries(entry_effect)
                         if effect.get('kind') == 'resistance'
                         and portent_id in effect.get('portents', ())), default=0)
        return max(.4, 1 - reduction / 100)

    def memory_portent_duration(self, portent_id: str, duration: int) -> int:
        import math
        reduction = max((int(entry.get('duration_reduction', 50))
                         for effect in self._memory_effect_defs()
                         for entry in self._memory_entries(effect)
                         if entry.get('kind') == 'resistance'
                         and portent_id in entry.get('portents', ())), default=0)
        if portent_id == "echoing":
            # §11 §9：气泡的卸压只缩短自身「回声」的新附着时长，与耐受取较高减免。
            reduction = max(reduction, self.memory_stat_bonus("echo_duration_reduction"))
        if reduction <= 0:
            return duration
        return max(1, math.ceil(duration * (1 - reduction / 100)))

    def memory_adapts(self, adapt_id: str) -> bool:
        """是否适应了某种环境（湿滑 / 粘稠 / 声响）。"""
        return any(
            effect.get("kind") == "adapt" and effect.get("adapt") == adapt_id
            for effect in self._memory_effect_defs()
        )

    @staticmethod
    def _memory_entries(effect: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        """把复合效果拆成逐条子效果；单条效果保持原样。

        §11 §9：碎片可以同时带两条属性（如「移动的视窗」视野＋听取），
        旧分支只认单个 ``stat``，第二条会只剩在说明里。
        """
        if effect.get("kind") == "compound":
            return tuple(effect.get("effects") or ())
        return (effect,)

    # 范围／时效类修正同类取最高值，不同轴可共同生效（docs §11 §9）。
    _NON_STACKING_MEMORY_STATS = frozenset({
        "sight", "listen", "clue_retention", "noise", "lure_radius",
        "survey", "margin", "echo_damping", "echo_duration_reduction",
    })

    def memory_stat_bonus(self, stat: str) -> int:
        """碎片给出的某项属性上限增量（属性类效果汇总）。

        属性类（kind="stat"）按其 ``stat`` 归组；适应类（kind="adapt"）里的
        数值型效果（如「雨声的遮蔽」，value=2）也一并计入，用 ``adapt`` 名当键——
        它们对调用方而言都是「某条机制上的一点点数值修正」。

        复合效果逐条读取；范围／时效类同类取最高，不因多装一件同轴碎片叠加。
        """
        values: list[int] = []
        for effect in self._memory_effect_defs():
            for entry in self._memory_entries(effect):
                kind = entry.get("kind")
                if kind == "stat" and entry.get("stat") == stat:
                    values.append(int(entry.get("value", 0)))
                elif kind == "adapt" and entry.get("adapt") == stat:
                    values.append(int(entry.get("value", 0)))
        if not values:
            return 0
        if stat in self._NON_STACKING_MEMORY_STATS:
            return max(values)
        return sum(values)

    def _apply_memory_effect(self, memory_id: str) -> None:
        """碎片刚进槽时的即时结算：属性上限抬高后立刻回填等量当前值。

        没有这一步，「清醒度上限 +10」在满值状态下完全没有体感——上限涨了，
        当前值却仍停在旧上限，玩家只会看到一条没用的数字。回填量按上限的
        实际增量算（min 保证不超过新上限）。
        """
        # 记忆碎片可带视距加成（memory_stat_bonus("sight")）——装卸即失效。
        self.invalidate_sight_radius()
        effect_name = ITEM_DEFINITIONS.get(memory_id, {}).get("memory_effect")
        effect = MEMORY_FRAGMENT_EFFECTS.get(effect_name or "")
        if not effect:
            return
        entries = [entry for entry in self._memory_entries(effect)
                   if entry.get("kind") == "stat" and int(entry.get("value", 0)) > 0]
        if not entries:
            return
        award = memory_id not in self.memory_effect_awards
        if award:
            self.memory_effect_awards.append(memory_id)
        for entry in entries:
            stat = entry.get("stat")
            value = int(entry.get("value", 0))
            if stat == "max_lucidity":
                self.max_lucidity += value
                if award:
                    self.restore_resource('lucidity', value)
            elif stat == "max_imagination":
                self.max_imagination += value
                if award:
                    self.restore_resource('imagination', value)
            elif stat == "max_mind":
                self.max_mind += value
                if award:
                    self.restore_resource('mind', value)

    def invalidate_sight_radius(self) -> None:
        """清掉 effective_sight_radius 的回合内缓存（性能 P0，2026-10-10）。

        失效点：GameSession.apply 开头（所有玩家动作兜底）、
        EquipmentView.invalidate（装备几何变化，覆盖测试/调试的直改）、
        记忆碎片装卸（_apply/_drop_memory_effect）。征兆/夜视/脚下地板/
        望远层数已在缓存键里，无需在此失效。
        """
        self._sight_radius_cache = None

    def _drop_memory_effect(self, memory_id: str) -> None:
        """碎片被替换掉时的回退：上限按原增量收回，当前值同步钳制。

        替换是「可拆卸」的代价所在——拆掉就该把好处还回去。当前值只钳到
        新上限（不额外扣），否则玩家会因为换一条碎片而白白损失数值。
        """
        self.invalidate_sight_radius()
        from . import memory_buffers
        memory_buffers.forget(self, memory_id)
        effect_name = ITEM_DEFINITIONS.get(memory_id, {}).get("memory_effect")
        effect = MEMORY_FRAGMENT_EFFECTS.get(effect_name or "")
        if not effect:
            return
        from .settlement import REASON_MAX_CHANGE, apply_max_change
        for entry in self._memory_entries(effect):
            if entry.get("kind") != "stat":
                continue
            stat = entry.get("stat")
            value = int(entry.get("value", 0))
            if value <= 0:
                continue
            if stat == "max_lucidity":
                apply_max_change(self, "lucidity", max(1, self.max_lucidity - value),
                                 reason=REASON_MAX_CHANGE, source="记忆碎片替换")
            elif stat == "max_imagination":
                apply_max_change(self, "imagination", max(0, self.max_imagination - value),
                                 reason=REASON_MAX_CHANGE, source="记忆碎片替换")
            elif stat == "max_mind":
                apply_max_change(self, "mind", max(1, self.max_mind - value),
                                 reason=REASON_MAX_CHANGE, source="记忆碎片替换")

    def _add_inventory_item(self, item: Item) -> None:
        if self.inventory_used >= self.inventory_capacity and not (
            item.max_stack > 1 and any(existing.definition_id == item.definition_id and existing.quantity < existing.max_stack for existing in self.inventory)
        ):
            raise ValueError("意识行囊已满。")
        if item.max_stack > 1:
            for existing in self.inventory:
                if existing.definition_id == item.definition_id and existing.quantity < existing.max_stack:
                    transfer = min(item.quantity, existing.max_stack - existing.quantity)
                    existing.quantity += transfer
                    item.quantity -= transfer
                    if item.quantity <= 0:
                        return
        self.inventory.append(item)

    def _active_hand_item(self) -> Item | None:
        """Obsolete query: actual actions select sources from their sentences."""
        return None

    def has_visible_hostile(self) -> bool:
        # 核心执念恒显（2026-09-22）但不参与本判定：剧情实体在场的整层
        # 不应因此永久暂停自动收纳；诅咒灵视所见的远方异象照常计入。
        return any(
            enemy.integrity > 0
            and enemy.relation == "失控意识"
            and not getattr(enemy, "always_visible", False)
            and self.is_visible(enemy.x, enemy.y)
            for enemy in self.enemies
        )

    # ---- 玩家地图知识接口（docs §1）----
    def record_visible_terrain(self) -> int:
        """把当前正常视野的地形并入玩家记忆；返回新学到/更新的格子数。"""
        return _record_visible_terrain(self)

    def cell_knowledge(self, x: int, y: int):
        """按三层信息规则返回一格的可显示内容（unknown/memory/visible/...）。"""
        return _cell_knowledge(self, x, y)

    def layer_key(self) -> str:
        """当前所在层的**稳定层键**：梦中梦是 ``R{realm_id}:{depth}``，主梦层是深度。

        层快照（layer_states）与稳定意识身份（Entity.actor_uid）共用这一个键：
        主梦层键必须是纯数字串，_trim_layer_states 靠 ``key.isdigit()`` 区分
        「走深度轴、可以裁剪」的层与「永不裁剪」的梦中梦层。
        """
        if self.realm_id:
            return f"R{self.realm_id}:{self.realm_depth}"
        return str(self.depth)

    def _archive_active_layer(self) -> None:
        from .realm_surface import normalize_bg_zones
        from .tactical_layouts import checkpoint_tactical_layouts
        checkpoint_tactical_layouts(self)
        key = self.layer_key()
        self.layer_states[key] = LayerSnapshot(
            depth=self.depth,
            seed=self.seed + self.depth * 1009,
            cells=self.cells,
            enemies=self.enemies,
            world_items=self.world_items,
            events=self.events,
            player_x=self.player.x,
            player_y=self.player.y,
            dissolution=self.dissolution,
            theme=self.theme,
            map_form=self.map_form,
            width=self.width,
            height=self.height,
            logic_scenarios=dict(self.trap_scenarios),
            logic_valves={k: tuple(v) for k, v in self.valve_stored.items()},
            logic_boards=deepcopy(self.circuit_boards),
            logic_fences={f"{x},{y}": life for (x,y), life in self._mind_fences.items()},
            enemy_skill_fields=deepcopy(self.enemy_skill_fields),
            realm_bg_zones=normalize_bg_zones(self.realm_bg_zones, self.width, self.height),
            material_time=self.time,
            realm_features=deepcopy(self.realm_features),
        )

    def _trim_layer_states(self) -> None:
        """把旧梦层快照裁到「当前层 ±LAYER_CACHE_WINDOW」的窗口内。

        每份快照都持有一整幅 Cell 网格，全部留着会让 GC 的对象图随深度线性膨胀，
        是后期卡顿的主因（玩家反馈「后期明显比前期卡」）。窗口外的层玩家需要连着
        上浮很多次才够得着，那时重新按种子生成即可（见 LAYER_CACHE_WINDOW 注释）。

        梦中梦快照（键形如 ``R{realm_id}:{depth}``）不走梦层深度轴，永远保留：
        支线总共只有寥寥数层，谈不上内存压力，而裁掉它会让回廊进度凭空蒸发。
        """
        if len(self.layer_states) <= 2 * self.LAYER_CACHE_WINDOW + 1:
            return
        low = self.depth - self.LAYER_CACHE_WINDOW
        high = self.depth + self.LAYER_CACHE_WINDOW
        for key in list(self.layer_states):
            if not key.isdigit():
                continue
            if not (low <= int(key) <= high):
                del self.layer_states[key]

    def _generate_epilogue_layer(self, depth: int) -> None:
        """深层边界（28–30）独立生成：几何外层 + Perlin + 内层剧情模板。"""
        from ..mapgen.epilogue import EPILOGUE_ANOMALY_POOL, generate_epilogue_layer

        rng = random.Random(self.seed + depth * 7919)
        cells, info = generate_epilogue_layer(depth, self.seed)
        self._apply_logic_layout(None)
        self._logic_energized, self._mind_fences, self._rune_cooldowns = set(), {}, {}
        self.width, self.height = info["width"], info["height"]
        self.cells = cells
        self._reset_material_index()
        self.map_form = "深层边界"
        self.layer_modifier = ""
        self.theme = LAYER_THEMES[min(depth - 1, len(LAYER_THEMES) - 1)]
        sx, sy = info["spawn"]
        self.player.x, self.player.y = sx, sy
        self.enemies = []
        self.world_items = []
        self.events = []
        self.dissolution = 0
        self.turns_since_descend = 0
        lo, hi = {28: (12, 18), 29: (18, 24), 30: (8, 12)}[depth]
        for x,y,cid in info.get('enemies',()):
            if not self.cell(x,y).solid and not self.entity_at(x,y):
                boss=self.add_defined_enemy(cid,x,y)
                self.epilogue_flags['scribe_max']=boss.integrity
        self.epilogue_flags['schema']=2
        self.epilogue_flags.setdefault('repaired_layers',[]).append(depth)
        # 收尾层内容向剧情内区倾斜：终局区域要「紧凑而有挑战」，不能只有
        # 一栋空楼。剧情锚点/遗物位先登记为保留格，异象与补投遗物都避开它们。
        reserved: set[tuple[int, int]] = {info["spawn"]}
        reserved.update(info["events"].values())
        reserved.update(info.get("accept", ()))
        if info.get("npc"):
            reserved.add(info["npc"])
        reserved.update(info.get("loot_spots", ()))
        reserved.update((entry["x"], entry["y"]) for entry in info.get("scene_events", ()))
        reserved.update(pos for pos, _ in info.get("structure_npcs", ()))

        inner_rect = info.get("inner")
        inner_spots: list[tuple[int, int]] = []
        outer_spots: list[tuple[int, int]] = []
        if inner_rect:
            ix, iy, iw, ih = inner_rect
        else:
            ix = iy = iw = ih = 0
        for spot in info.get("open_cells", ()):
            x, y = spot
            if self.cell(x, y).solid or self.entity_at(x, y) or spot in reserved:
                continue
            if ix <= x < ix + iw and iy <= y < iy + ih:
                inner_spots.append(spot)
            else:
                outer_spots.append(spot)
        rng.shuffle(inner_spots)
        rng.shuffle(outer_spots)

        count = min(rng.randint(lo, hi), len(inner_spots) + len(outer_spots))
        profile = active_profile(self, depth)
        specs = []
        # 深层强度缩放（2026-09-19 平衡）：越深越强——血量 ×1.25/1.5/1.75，创伤 +1/2/3。
        depth_scale = {28: 1.25, 29: 1.5, 30: 1.75}.get(depth, 1.0)
        power_bonus = {28: 1, 29: 2, 30: 3}.get(depth, 0)
        placed = 0
        used_spots: set[tuple[int, int]] = set()

        def _take_anomalies(spot_list, wanted: int) -> int:
            """从候选里取至多 wanted 个有效落点；短列表/占用格安全跳过。"""
            nonlocal placed
            taken = 0
            for x, y in spot_list:
                if placed >= count or taken >= wanted:
                    break
                spot = (x, y)
                if spot in used_spots:
                    continue
                if self.cell(x, y).solid or self.entity_at(x, y):
                    continue
                used_spots.add(spot)
                pool_id = EPILOGUE_ANOMALY_POOL[rng.randrange(len(EPILOGUE_ANOMALY_POOL))]
                specs.append((x, y, pool_id))
                placed += 1
                taken += 1
            return taken

        # 内区配额 ≥40%（向上取整）；内区候选不足时再回填外区，外区不足再补内区。
        inner_quota = (count * 2 + 4) // 5 if count else 0
        _take_anomalies(inner_spots, inner_quota)
        _take_anomalies(outer_spots, count)
        _take_anomalies(inner_spots, count)
        if profile:
            # 消费完原编成随机流，再用独立流选子集；后续实物与事件的随机序列保持。
            # 子集同样保内区配额（否则随机抽稀会把内区占比压回 30% 上下）。
            roster_rng = random.Random(self.seed + depth * 7919 + 0xD1FF)
            wanted = min(len(specs), roster_rng.randint(*profile.roaming_range))
            inner_index = [index for index, (x, y, _) in enumerate(specs)
                           if ix <= x < ix + iw and iy <= y < iy + ih]
            quota = min(len(inner_index), (wanted * 2 + 4) // 5 if wanted else 0)
            chosen = set(roster_rng.sample(inner_index, quota)) if quota else set()
            rest = [index for index in range(len(specs)) if index not in chosen]
            need = wanted - len(chosen)
            if need > 0 and rest:
                chosen |= set(roster_rng.sample(rest, min(need, len(rest))))
            specs = [entry for index, entry in enumerate(specs) if index in chosen]
            ordinary_pool = [cid for cid in EPILOGUE_ANOMALY_POOL
                             if ANOMALY_DEFINITIONS[cid]["anomaly_kind"] == "普通异象"]
            strong_count = 0
            limited = []
            for x, y, cid in specs:
                if ANOMALY_DEFINITIONS[cid]["anomaly_kind"] == "强烈异象":
                    if strong_count >= profile.strong_budget:
                        cid = roster_rng.choice(ordinary_pool)
                    else:
                        strong_count += 1
                limited.append((x, y, cid))
            specs = limited
            depth_scale = profile.roaming_integrity_factor
        for x, y, pool_id in specs:
            base = ANOMALY_DEFINITIONS[pool_id]
            enemy = self.add_defined_enemy(pool_id, x, y,
                integrity=max(1, round(base["integrity"] * depth_scale
                                       * (self._enemy_integrity_mult() if profile else 1.0))))
            if not profile:
                # 旧局保留历史字段；新局不接通原本没有伤害消费端的加值。
                enemy.power = min(13, base.get("power", 1) + power_bonus)
        def _drop_loot(loot_x: int, loot_y: int) -> bool:
            if self.cell(loot_x, loot_y).solid:
                return False
            rarity = "非常稀有" if rng.random() < 0.35 else "稀有"
            # 回落池也排除交互道具：容器只能事件/NPC 交易获取（2026-09-19）。
            # §7.1 统一资格入口：收尾层的掉落槽同样过闸——它是「非常稀有」
            # 的第三个来源（除散投保底与石台之外），不过闸就能绕过
            # grant_source／run_limit 直接把限定件铺在地上。
            pool = self._award_eligible(
                items_of_rarity(rarity, ("携带意象", "易逝物", "摄入物", "惯用物", "交互道具")),
                source="epilogue")
            if not pool:
                pool = self._award_eligible(items_of_rarity("稀有", ("易逝物",)), source="epilogue")
            if not pool:
                return False
            item_id = pool[rng.randrange(len(pool))]
            self.world_items.append(WorldItem(self._make_item(item_id), loot_x, loot_y))
            return True

        for loot_x, loot_y in info.get("loot_spots", []):
            _drop_loot(loot_x, loot_y)
        # 内区补投 4 处散落遗物：终局区域除了 vault 固定位，沿途也该有可拾取物。
        # 只落在内区开放地面，避开剧情锚点/已有遗物格；候选不足时宁缺毋滥。
        extra_loot = 0
        if inner_rect:
            for spot in inner_spots:
                if extra_loot >= 4:
                    break
                if spot in reserved or spot in used_spots:
                    continue
                if self.entity_at(*spot):
                    continue
                if _drop_loot(*spot):
                    extra_loot += 1
        self._spawn_epilogue_events(depth, rng, info)
        self._spawn_bound_events({"events": info.get("scene_events", ())})
        npc_id = {28: "npc.archivist", 29: "npc.guide"}.get(depth)
        if npc_id and info.get("npc") and not travel.suppress_random_spawn(self, npc_id):
            nx, ny = info["npc"]
            if not self.cell(nx, ny).solid:
                self._add_npc(npc_id, nx, ny)
        # 收尾层的结构 NPC（剧情推进所需）不参与每层 2 名的随机配额：
        # 全部落位，绝不用 [:1] 之类截断把收尾演出的人物挤掉。
        self._spawn_layer_npcs(self.seed + depth * 1009,
                               {"structure_npcs": info.get("structure_npcs", ())})
        # §14.6 台面落点：收尾层同样只换落点、不增份数。
        self.last_surface_report = self.stamp_surfaces()
        self.observe_visible_catalog()
        self._update_doors()

    def _generate_origin_layer(self) -> None:
        """0 层「梦的起始」独立生成：固定教学图，种子/修饰符/层型全部不参与。

        站点坐标写进 ``tutorial["stations"]`` 供引导系统取用；实体只有两只
        玩偶意识体（不还手、可重生），物资只有开局聚合弹——教学层不产 loot。
        """
        cells, info = generate_origin_layer()
        self._apply_logic_layout(None)
        self._logic_energized, self._mind_fences, self._rune_cooldowns = set(), {}, {}
        self.width, self.height = info["width"], info["height"]
        self.cells = cells
        self._reset_material_index()
        self.map_form = "梦的起始"
        self.layer_modifier = ""
        self.theme = LAYER_THEMES[0]
        self.depth = 0
        sx, sy = info["spawn"]
        self.player.x, self.player.y = sx, sy
        self.enemies = []
        self.world_items = []
        self.events = []
        self.dissolution = 0
        self.turns_since_descend = 0
        for x, y in info["dolls"]:
            self._add_tutorial_doll(x, y)
        self._add_tutorial_greeter(*info["stations"]["chat_npc"])
        self.projectile_charges = max(self.projectile_charges, PROJECTILE_GRANTS)
        # 开局预置（教程拍板）：行囊里有东西可看（面板步），容器步有瓶子可玩。
        for item_id in ("clear_glass", "magnesium_match"):
            if item_id in ITEM_DEFINITIONS:
                self.inventory.append(self._make_item(item_id))
        self.tutorial["stations"] = {name: list(pos) for name, pos in info["stations"].items()}
        self.observe_visible_catalog()
        self._update_doors()

    def _start_origin_tutorial(self) -> None:
        """新开局（教程开关开）进入 0 层：生成固定图并初始化引导步骤表。"""
        self._generate_origin_layer()
        self.tutorial = {
            "active": True,
            "step": 0,
            "skipped": [],
            "stations": dict(self.tutorial.get("stations", {})),
        }
        self._ensure_tutorial_supplies()

        from .origin_course import start
        start(self)

    def _ensure_tutorial_supplies(self) -> None:
        """一次性教学词块；也修补旧版没有装备的教程存档。"""
        if not self.tutorial.get('active') or self.tutorial.get('equipment_supplied'):
            return
        for definition in ('patched_pajamas', 'salt_soaked_coil'):
            if not any(item.definition_id == definition for item in self.inventory):
                self.inventory.append(self._make_item(definition))
        self.tutorial['equipment_supplied'] = True

    def _add_tutorial_doll(self, x: int, y: int) -> Entity:
        """玩偶意识体：教学层专用中立实体（relation=玩偶意识体）。

        不还手（attack_time 99 + 回合分支跳过）、不进图鉴、不计击杀、
        无掉落无崩解奖励；被打散后由 _tick_doll_respawns 原地重生。
        """
        doll = self.add_enemy(
            label="玩偶意识体", x=x, y=y,
            integrity=DOLL_INTEGRITY, move_time=DOLL_MOVE_TIME, attack_time=99.0,
            relation="玩偶意识体", trauma_type="心智创伤", communicates=False,
            drop_id=None, dissolution_reward=0, catalog_id="anomaly.unknown",
            anomaly_kind="普通异象", vision=0,
        )
        doll.glyph = "◍ "
        doll.catalog_observed = True
        return doll

    def _add_tutorial_greeter(self, x: int, y: int) -> Entity:
        """教学向导（0 层）：稳定意识，只陪聊天——没有任何交易选项可结算。"""
        greeter = self._add_npc("npc.origin_greeter", x, y)
        greeter.catalog_observed = True  # 教学向导不进图鉴
        return greeter

    def _schedule_doll_respawn(self, enemy: Entity) -> None:
        """玩偶被打散：登记 DOLL_RESPAWN_TURNS 回合后的原地重生。"""
        self.doll_respawns.append((self.time + DOLL_RESPAWN_TURNS, enemy.x, enemy.y))

    def _tick_doll_respawns(self) -> None:
        """到点的玩偶在原位重新叠好（位置被占则顺延 2 回合再试）。"""
        if not self.doll_respawns:
            return
        remaining = []
        for due, x, y in self.doll_respawns:
            if self.time < due:
                remaining.append((due, x, y))
                continue
            if self.cell(x, y).solid or self.entity_at(x, y) is not None:
                remaining.append((self.time + 2, x, y))
                continue
            self._add_tutorial_doll(x, y)
            self.messages.append(tr("散开的纸屑慢慢浮起——玩偶意识体重新叠好了自己。"))
        self.doll_respawns = remaining

    def _archive_gate_options(self) -> list[dict]:
        """「出院与归档」：28 层归档门可交付的条目。

        28 层起由 :meth:`_generate_epilogue_layer` 整层接管，``event_candidates``
        不再参与，因此**没有任何异常地点会落在这里**。目录里标「最低28」的条目
        （R-X06、R-E15/E16 一类边界内容）若只挂普通事件，``item_access.refusal``
        会按 ``min_depth`` 把它们永远拒掉——归档门是它们唯一合法的落点。

        判定只看目录真源：``runtime`` ＋ ``D`` 授权 ＋ ``min_depth >= 28`` ＋
        本局尚未发放过。不按名字或主题猜，因此后续再补「最低28」条目时
        无需改这里。
        """
        from ..data.expansion.catalog import BY_ID
        from ..data.items import ITEM_DEFINITIONS

        options: list[dict] = []
        for item_id, entry in BY_ID.items():
            if entry.get("integration_status") != "runtime":
                continue
            if entry.get("source_permission") != "D":
                continue
            if int(entry.get("min_depth", 0) or 0) < 28:
                continue
            if int(self.item_grant_counts.get(item_id, 0) or 0) > 0:
                continue
            definition = ITEM_DEFINITIONS.get(item_id) or {}
            options.append({
                "label": tr("在归档处领走{name}", name=tr(definition.get("name", item_id))),
                "epilogue": {"act": "archive_take", "item": item_id},
            })
        return options

    def _spawn_epilogue_events(self, depth: int, rng: "random.Random", info: dict) -> None:
        """深层边界剧情事件：展室/门/碑/承担点/回廊/终局桌 + 微事件。"""
        from .content import EPILOGUE_MICRO_EVENTS, EPILOGUE_PROFILE_RULES, EPILOGUE_ROOM_POOLS

        def add_event(event_id, name, x, y, description, *, kind="simple", dialogue=(), options=(), reward_id=None, dissolution=0):
            self.events.append(WorldEvent(
                event_id=event_id, name=name, x=x, y=y, description=description,
                reward_id=reward_id, catalog_id=event_id, kind=kind,
                dialogue=tuple(dialogue), options=tuple(options),
                dissolution_reward=dissolution, bound=True,
            ))

        profile = self.epilogue_profile or self._pick_epilogue_profile()
        if depth == 29:
            self.epilogue_profile = profile
        rule = next((r for r in EPILOGUE_PROFILE_RULES if r["profile"] == profile), EPILOGUE_PROFILE_RULES[-1])

        if depth == 28:
            from ..data.epilogue_upgrade import TEXT
            room_names = tuple(TEXT[f'room{i}'][0] for i in range(3))
            truths = ["亲历", "模仿", "外来"]
            rng.shuffle(truths)
            for index, key in enumerate(("room0", "room1", "room2")):
                truth = truths[index]
                memory = rng.choice(EPILOGUE_ROOM_POOLS[truth])
                ex, ey = info["events"][key]
                add_event(
                    "epilogue.room" + str(index), room_names[index], ex, ey,
                    "展室中央悬着一段记忆。判断它从哪里来。",
                    kind="compound",
                    dialogue=[memory["text"], "它属于——"],
                    options=[
                        {"label": "我亲历过", "epilogue": {"act": "identify", "claim": "亲历", "truth": memory["truth"]}},
                        {"label": "我模仿来的", "epilogue": {"act": "identify", "claim": "模仿", "truth": memory["truth"]}},
                        {"label": "它根本不是我", "epilogue": {"act": "identify", "claim": "外来", "truth": memory["truth"]}},
                    ],
                )
            gx, gy = info["events"]["gate"]
            add_event(
                "epilogue.gate28", "归档门", gx, gy,
                "三间展室的门在身后合拢。归档门上的铜锁等着一句话。",
                kind="compound",
                dialogue=["门后没有声音。它在等你说：我看完了。"],
                options=[
                    {"label": "「我看完了。」（推门进入承担之野）", "epilogue": {"act": "gate_rooms", "advance": 29}},
                    {"label": "「全部烧掉。」（抹去线索，强行进入）", "epilogue": {"act": "gate_rooms", "advance": 29, "wipe": True}},
                    *self._archive_gate_options(),
                ],
            )
        elif depth == 29:
            from ..data.epilogue_upgrade import TEXT
            sx, sy = info["events"]["stele"]
            add_event(
                "epilogue.stele", "承担牵引碑", sx, sy,
                "碑上刻着你的画像：" + profile + "。牵引已经写好。",
                kind="compound",
                dialogue=["牵引画像：" + profile + "。", rule["hint"]],
                options=[{"label": "接受牵引", "epilogue": {"act": "stele"}}],
            )
            for index, (ax, ay) in enumerate(info.get("accept", [])):
                add_event(
                    "epilogue.accept" + str(index), "承担点·" + str(index + 1), ax, ay,
                    rule["hint"],
                    kind="compound",
                    dialogue=[TEXT[f'burden{index}'][0],rule['hint']],
                    options=[{"label": "承担（" + profile + "）", "epilogue": {"act": "accept"}}],
                )
            gx, gy = info["events"]["gate"]
            add_event(
                "epilogue.gate29", "审判门", gx, gy,
                "门楣上刻着：承担两分，方过此门。",
                kind="compound",
                dialogue=["审判门后是改写之台。门在等你承认够了再开。"],
                options=[{"label": "推门（进入改写之台）", "epilogue": {"act": "gate_accept", "advance": 30}}],
            )
        else:
            from ..data.epilogue_upgrade import TEXT
            gx, gy = info["events"]["desk"]
            add_event(
                "epilogue.desk", "执笔者之桌", gx, gy,
                "稿纸摊在桌上，末行空着。执笔者就在不远处写着你的人生。",
                kind="compound",
                dialogue=[TEXT['desk_reply'][0]],
                options=[
                    {"label": "重写结局（需要 4 条自我线索，且执笔者已沉默）", "epilogue": {"act": "finish", "ending": "B", "require_clues": 4, "require_scribe_dead": True}},
                    {"label": "让它写完（结局：放手）", "epilogue": {"act": "finish", "ending": "C"}},
                    {"label": "与它共写（需要 3 条自我线索与 40 点想象力）", "epilogue": {"act": "finish", "ending": "D", "require_clues": 3, "require_imagination": 40}},
                    {'label':TEXT['challenge'][0],'epilogue':{'act':'challenge'}},
                    {'label':'告辞。','leave':True},
                ],
            )
        picked = rng.sample(list(EPILOGUE_MICRO_EVENTS), min(8, len(EPILOGUE_MICRO_EVENTS)))
        self._spawn_epilogue_exploration(info,add_event)
        spots = rng.sample(info["open_cells"], min(len(picked), len(info["open_cells"])))
        for (x, y), micro in zip(spots, picked):
            add_event(
                micro["event_id"], micro["name"], x, y, micro["description"],
                reward_id=micro.get("reward_id"), dissolution=6,
            )

    def _pick_epilogue_profile(self) -> str:
        """按本局统计挑承担画像（首个命中即用）。"""
        if self.run_stats.get("kills", 0) >= 40:
            return "杀伐型"
        if len(self.inventory) >= 10:
            return "囤积型"
        if self.run_stats.get("ignitions", 0) >= 60:
            return "纵火型"
        return "直面型"

    @root_action
    def enter_epilogue(self) -> ActionResult:
        """深潜裂隙：27 层进入 28 层（不查崩解度；清醒不足折算心智创伤）。"""
        if self.depth != 27:
            return ActionResult(False, tr("裂隙只在初啼之渊。"))
        self._action_time(1)
        shortage = max(0, 8 - self.lucidity)
        if self.run_over:
            return ActionResult(False,tr("意识沉没。"))
        from .settlement import REASON_STORY, settle_delta
        settle_delta(self, 'lucidity', -8, reason=REASON_STORY,
                     source='深层裂隙')
        loss = 0
        if shortage:
            loss = self._lose_mind(shortage * 2, source_id='深层裂隙折损')
            message = tr("清醒不足，裂隙强行收拢——你承受了 {amount} 点心智创伤。", amount=shortage * 2)
        else:
            message = tr("你走进裂隙。下潜至深层边界。")
        from .failure_review import record_descent
        record_descent(self, 28, shortage, loss)
        self._check_run_over()
        if self.run_over:
            return ActionResult(False,message)
        self._archive_active_layer()
        self.depth = 28
        self.deepest_depth = max(self.deepest_depth, self.depth)
        self.turns_since_descend = 0
        self._restore_or_generate_layer(28)
        self._trim_layer_states()
        self.messages.append(message)
        self._check_run_over()
        return ActionResult(True, message, {"depth": 28})

    def epilogue_advance(self, depth: int) -> ActionResult:
        """深层边界内的门事件推进（28→29→30）：不检查崩解度、不耗清醒。"""
        if self.run_over or (self.depth,depth) not in ((28,29),(29,30)):
            return ActionResult(False,tr("这个选项什么也没发生。"))
        self._archive_active_layer()
        self.depth = depth
        self.deepest_depth = max(self.deepest_depth, depth)
        self.turns_since_descend = 0
        self._restore_or_generate_layer(depth)
        self._trim_layer_states()
        message = tr("门后是梦层 {depth}。", depth=depth)
        self.messages.append(message)
        return ActionResult(True, message, {"depth": depth})

    def _spawn_layer_npcs(self, layer_seed: int, vault_info: "dict | None") -> None:
        """稳定意识（NPC）：结构自带先占座位、随机零散补剩下的位置。

        站位在地图生成期预留（vault_info["npc_spots"]，先于液体/气体/植物）；
        落地时清空该格的流体与植物，保证 NPC 脚下永远干净。

        2026-10-27 配额规则：结构自带的 NPC（vault 的 npc 锚点，随结构必定
        出现）与随机零散**共用** ``NPC_MAX_PER_LAYER``——名额在生成期就分好
        （``_generate_cells`` 把 ``npc_spots`` 裁到余额内），这里只负责按
        「结构在前、访客在后」的顺序落位，因此结构不会挤掉、总数也不会越限。
        深层边界 28–30 走 ``_generate_epilogue_layer`` 的独立口径（剧情所需
        的结构 NPC 全部落位，不受本名额约束）。
        """
        from .content import NPC_DEFINITIONS, NPC_MAX_PER_LAYER
        rng = random.Random(layer_seed ^ 0x9E4C0)
        spots = list((vault_info or {}).get("npc_spots", ()))
        ids = [key for key, definition in NPC_DEFINITIONS.items() if not definition.get("vault_only")]
        rng.shuffle(ids)
        # Authored scene NPCs take priority over optional random visitors.
        bound_npcs = list((vault_info or {}).get("structure_npcs", ()))
        seats = [((x, y), npc_id, True) for (x, y), npc_id in bound_npcs]
        seats += [((x, y), npc_id, False) for (x, y), npc_id in zip(spots, ids)]
        quota = 0
        for (x, y), npc_id, is_bound in seats:
            if not is_bound and quota >= NPC_MAX_PER_LAYER:
                break
            if travel.suppress_random_spawn(self, npc_id):
                # 有别层来的同职业旅人在场（§6.3）：本层别再生成双胞胎；
                # 「本地户走了」不在此拦——重建铸出的同 uid 实体会合并回
                # 旅人档案，再由 reconcile_layer 在物化收尾清场。
                continue
            if self.entity_at(x, y) is not None:
                continue
            cell = self.cell(x, y)
            if cell.solid and any((x, y) == pos for pos, _ in bound_npcs):
                continue  # Never destroy an authored component to place a visitor.
            if cell.solid and cell.wall_kind != "门":
                # 极少数情况下结构压过预留位：清出落脚格。
                self.destroy_wall(x, y, "carve")
            # 站位清空：液体/气体/植物一律不与 NPC 同格。
            cell.liquid = 0
            cell.liquid_kind = ""
            cell.gas = 0
            cell.gas_kind = ""
            if cell.plant:
                self.set_plant(x, y, 0)
            self._add_npc(npc_id, x, y)
            if not is_bound:
                quota += 1

    def _add_npc(self, npc_id: str, x: int, y: int, *, actor_uid: str = "") -> Entity:
        """按定义生成一名稳定意识（高血量、不受异象攻击、被打不还手）。

        同时抽定这名 NPC 这次卖什么（2–3 项）：同一职业的不同个体交易表不一样，
        没抽到的项既不显示也不能交易（见 core.content.draw_npc_options）。
        抽签用「种子+层+坐标」的独立随机流，不吃层生成的随机数序列——否则
        加一条抽签就会把整层的其它随机结果全部错位。
        """
        from .content import NPC_DEFINITIONS, draw_npc_options
        definition = NPC_DEFINITIONS[npc_id]
        npc = self.add_enemy(
            x=x, y=y,
            label=definition["name"],
            integrity=definition.get("integrity", 20),
            move_time=2.0,
            attack_time=99.0,
            relation=definition.get("relation", "稳定意识"),
            trauma_type=definition.get("trauma_type", "心智创伤"),
            communicates=True,
            drop_id=None,
            dissolution_reward=0,
            vision=0,
        )
        # ⚠️ id 保持 add_enemy 给的**实例唯一**值（enemy-N），职业另存 npc_kind：
        # 早先把 id 覆盖成职业 id，结果同职业的两位在对话/交易记账上互相串
        # （pending_npc 按 id 查、npc_traded_options 也按 id 记）。
        npc.npc_kind = npc_id
        npc.glyph = entity_glyph(definition["glyph"])
        # 行程到站投影（world.travel）带着既有 actor_uid 来落成实体：同一位
        # 角色跨层只有这一份身份；序号铸新 uid 的路只留给本层本土新生。
        npc.actor_uid = actor_uid or f"{self.layer_key()}#{npc_id}#{self._npc_ordinal(npc)}"
        # 角色注册表是世界记录的唯一身份来源（§12.2）：同一 actor_uid 全局只有一位，
        # 摊位抽过一次就定型——重进地图、远层裁剪后重建都不能刷新货架。
        record = self.world_ledger.register(ActorRecord(
            actor_uid=npc.actor_uid, npc_kind=npc_id,
            home_layer_key=self.layer_key(), layer_key=self.layer_key(),
            x=x, y=y, important=bool(definition.get("important"))))
        npc.npc_options = record.shelf or draw_npc_options(
            npc_id, random.Random(self.seed * 31 + self.depth * 1009 + x * 977 + y * 37)
        )
        from .npc_offers import limited_shelf
        npc.npc_options = limited_shelf(npc)
        record.shelf = tuple(npc.npc_options)
        return npc

    def _npc_ordinal(self, npc: Entity) -> int:
        """本层同职业 NPC 的生成序号（自己是第几个）。

        层的生成完全由种子决定，裁剪后按种子重生成会以同样的次序落同样的 NPC，
        所以序号在重建前后一致——这正是 actor_uid 能跨重建存活的原因。
        只数「本层铸 uid」的同类：外来旅人（world.travel 投影）的 uid 前缀是
        他乡层键，不能挤占本层序号，否则本土位的 uid 会随旅人进出而漂移。
        """
        prefix = f"{self.layer_key()}#"
        return sum(
            1 for other in self.enemies
            if other is not npc
            and getattr(other, "npc_kind", "") == npc.npc_kind
            and getattr(other, "actor_uid", "").startswith(prefix)
        )

    # ------------------------------------------------- 梦中梦入口安放
    def _spawn_realm_entries(self, vault_info: "dict | None" = None) -> None:
        """主梦层生成后：按种子确定性安放本局的两个梦中梦入口。

        - **引火人**（余烬廊桥入口 NPC）：开局一次性判定 ``ember_npc_exists``
          与 ``ember_npc_layer``（11–19），命中层才落地——「未必刷新」的固定 NPC。
        - **潮汐之门**（退潮厅入口地点）：开局一次性选定宿主层
          ``realm_gate_layer``（12–26，30%/层推进，26 层保底），命中层落地。

        随机数全部走**独立流**（``seed ^ 常量``），绝不吃层生成序列——否则新增
        判定会把整层的其它随机结果错位。已关门的位面不再安放（见
        :meth:`_purge_closed_realm_entries`）。只在主梦层生成时调用。
        """
        if self.realm_id:
            return
        # ---- 引火人：开局一次性判定 ----
        from .realm_entries import spawn_entries
        spawn_entries(self)
        if self.ember_npc_layer == 0:
            judge = random.Random(self.seed ^ 0xE3B0)
            self.ember_npc_exists = judge.random() < 0.65
            self.ember_npc_layer = judge.randint(11, 19)
        if (self.ember_npc_exists
                and self.depth == self.ember_npc_layer
                and "ember_bridge" not in self.closed_realms):
            spots = list((vault_info or {}).get("npc_spots", ()))
            # 预留位可能已被随机零散 NPC 先占（_spawn_layer_npcs 先跑）：挑第一个
            # 空位，否则两个实体同格叠加——那既看不见，也让每层 NPC 名额失真。
            x, y = next((spot for spot in spots if self.entity_at(*spot) is None),
                        self._find_open_cell(self.cells, self.width // 2, self.height // 2))
            cell = self.cell(x, y)
            if cell.solid and cell.wall_kind != "门":
                self.destroy_wall(x, y, "carve")
            cell.liquid, cell.liquid_kind = 0, ""
            cell.gas, cell.gas_kind = 0, ""
            if cell.plant:
                self.set_plant(x, y, 0)
            self._add_npc(EMBER_LIGHTER_NPC, x, y)
            self.messages.append(tr("一个守着火柴的人在梦层深处等你。"))
        # ---- 潮汐之门：开局一次性选定宿主层 ----
        gate = REALM_GATE_DEFS.get("ebbing_hall")
        if gate is None or "ebbing_hall" in self.closed_realms:
            return
        if self.realm_gate_layer == 0:
            host = random.Random(self.seed ^ 0x6A7E)
            chosen = 26
            for depth in range(12, 26):
                if host.random() < 0.30:
                    chosen = depth
                    break
            self.realm_gate_layer = chosen
        if self.depth != self.realm_gate_layer:
            return
        x, y = self._find_open_cell(self.cells, self.width // 2, self.height // 2)
        self.events.append(WorldEvent(
            event_id=gate["event_id"], name=gate["name"], x=x, y=y,
            description="一扇向下的门，门缝里渗出退潮的水声与咸味。",
            catalog_id=gate["event_id"], kind="compound",
            dialogue=("潮水的味道从门缝里渗出来。要走进去吗？",),
            options=(
                {"label": "走进去", "enter_realm": "ebbing_hall"},
                {"label": "离开", "leave": True},
            ),
            bound=True,
        ))
        self.messages.append(tr("地图上出现了一扇「{name}」。", name=tr(gate["name"])))

    def _purge_closed_realm_entries(self) -> None:
        """把本局已关闭位面的入口从当前主梦层上抹掉（地点与 NPC 都清）。

        只清「地点/固定 NPC」这类**主梦残留入口**：关门后不该在地图上再碰到
        一个进不去的门或一个不理人的引火人。位面自身层走快照，不受影响。
        """
        if not self.closed_realms or self.realm_id:
            return
        self.events = [
            e for e in self.events
            if not (e.event_id.startswith("realm_gate.")
                    and e.event_id.split(".", 1)[1] in self.closed_realms)
        ]
        closed_npc_ids = {
            REALM_ENTRY_NPCS[realm] for realm in self.closed_realms
            if realm in REALM_ENTRY_NPCS
        }
        if closed_npc_ids:
            self.enemies = [
                en for en in self.enemies
                if getattr(en, "npc_kind", "") not in closed_npc_ids
            ]

    def _apply_logic_layout(self, logic: dict | None) -> None:
        """生成后应用逻辑固体布设：布线、压力地板、陷阱场景、灌注阀储备。

        新模板使用独立的命名线路，交叉处绝缘；旧模板保留脉冲链兼容。
        """
        self.trap_scenarios = {}
        self.valve_stored = {}
        self.circuit_boards = []
        self.gate_inputs = {}
        if not logic:
            return
        self.trap_scenarios = {k: str(v) for k, v in logic.get("traps", {}).items()}
        self.valve_stored = {k: tuple(v) for k, v in logic.get("valves", {}).items()}
        for (x, y) in logic.get("pressure", ()):
            if 0 <= x < self.width and 0 <= y < self.height:
                cell = self.cell(x, y)
                if not cell.solid:
                    cell.aggregate_variant = "压力地板"
        chain = [pos for pos in logic.get("chain", ()) if 0 <= pos[0] < self.width and 0 <= pos[1] < self.height]
        if len(chain) >= 2:
            self.link_logic_nodes(chain)
        for board in logic.get("boards", []):
            self.install_circuit_board(board)

    def _restore_or_generate_layer(self, depth: int) -> None:
        self.library_bookmark = {}
        self.realm_bg_zones = []
        self.realm_features = {}
        self.circuit_boards = []
        self.gate_inputs = {}
        self._logic_energized = set()
        self._mind_fences = {}
        self._rune_cooldowns = {}
        # §12 E 审计结论按层重置：旧层的场景组不能跟着带进新层（生成报告按层读）。
        self.light_scene_report = {}
        # §14.6 台面落点报告同样按层重置（坐标属于本层）。
        self.last_surface_report = {}
        # §12 F 设施投放审计同样按层重置（灯具坐标属于本层）。
        self.light_fixture_report = {}
        # 主动技能效果场按层清空/还原：上一层的坐标在新层没有意义。
        self.enemy_skill_fields = []
        # 照彻只在本层生效：任何一次换层（下潜或回溯到旧层）都会收回灯塔的光，
        # 否则「全图照亮」会跟着玩家跨越梦层。
        self.light_turns = 0
        # 环境模拟的延迟源队列按层清空：上一层的坐标在新层没有意义。
        self._deferred_liquid_sources = []
        self._deferred_gas_sources = []
        # 噪音条同样按层清空：上一层的响声不能带进新层的「周围区域噪音」。
        self._ambient_noise_events = []
        # 联想盘：换层清掉指向旧世界目标的待释放脉冲与接触端去重记录，
        # 但**保留**玩家级共享冷却——不能借往返层刷新电路（设计方案 §9.3）。
        self.board_prune_on_descend()
        if depth <= 0:
            # 0 层「梦的起始」：固定教学图（mapgen/origin.py），不走层型。
            self._generate_origin_layer()
            return
        if self.realm_id:
            # 梦中梦层的还原字段与主梦完全同构，统一交给 DreamRealmMixin，
            # 避免两处还原逻辑各自漂移（早先这里少还原玩家坐标与机关状态）。
            self._restore_or_generate_realm_layer(depth)
            return
        snapshot = self.layer_states.get(str(depth))
        if snapshot:
            self.cells = snapshot.cells
            self._resume_material_clocks(snapshot)
            self.enemies = snapshot.enemies
            self.world_items = snapshot.world_items
            self.events = snapshot.events
            self.player.x, self.player.y = snapshot.player_x, snapshot.player_y
            self.dissolution = snapshot.dissolution
            self.theme = snapshot.theme
            self.map_form = normalize_map_form(snapshot.map_form)
            # 长廊等层型有自己的尺寸，回到旧层时要把边界一起还原。
            if snapshot.width > 0 and snapshot.height > 0:
                self.width, self.height = snapshot.width, snapshot.height
            # 逻辑固体：陷阱场景与阀储备随层还原（电线位在 Cell 上，已随格还原）。
            self.trap_scenarios = dict(snapshot.logic_scenarios)
            self.valve_stored = {k: tuple(v) for k, v in snapshot.logic_valves.items()}
            self.circuit_boards = deepcopy(snapshot.logic_boards)
            self._restore_logic_fences(snapshot.logic_fences)
            self.enemy_skill_fields = deepcopy(snapshot.enemy_skill_fields)
            self.realm_bg_zones = deepcopy(snapshot.realm_bg_zones)
            self.realm_features = deepcopy(snapshot.realm_features)
            self.gate_inputs = {}
            self._resume_circuit_boards()
            self._resume_epilogue()
            self._reset_material_index()
            # 已关闭位面的残留入口（门地标/固定 NPC）不该随快照复活。
            self._purge_closed_realm_entries()
            # 行程对账（§6.3）：快照里可能留下「账上已走」的旧影，也可能
            # 要迎接「账上到站」的旅人——还原收尾原子对一次账。
            travel.reconcile_layer(self)
            return
        layer_seed = self.seed + depth * 1009
        if depth >= 28:
            self._generate_epilogue_layer(depth)
            travel.reconcile_layer(self)
            return
        self.map_form = layer_form_for(self.seed, depth)
        # 修饰符（大型/小型/气密/潮湿/繁茂/古朴，50% 层为常规）：与层型一样
        # 由种子确定性推导，在生成前决定并修正本层尺寸与液/气/植物/vault 率。
        self.layer_modifier = layer_modifier_for(self.seed, depth)
        # 层型可以改写地图尺寸（长廊拉成极端长宽比），意识边界是外圈一环、跟着一起变。
        self.width, self.height = layer_dimensions(
            self.base_width or self.width,
            self.base_height or self.height,
            self.map_form,
            layer_seed,
            self.layer_modifier,
        )
        vault_info: dict = {}
        self.cells = self._generate_cells(layer_seed, self.width, self.height, self.map_form, depth, self.layer_modifier, vault_info, realm_id=self.realm_id, defer_natural_gas=True)
        # §12 E：本层光源场景组的审计结论（生成报告/测试读；不进存档）。
        self.light_scene_report = vault_info.get("light_scenes", {})
        # §14.6 台面落点报告（生成报告／测试读；不进存档）：本层有多少件
        # 显化物站在台面上、多少件被搬上台面。
        self.last_surface_report = {}
        self.light_fixture_report = vault_info.get("light_fixtures", {})
        self._reset_material_index()
        self._apply_logic_layout(vault_info.get("logic"))
        self.player.x, self.player.y = self._find_nonvault_spawn(
            self.cells, self.width // 2, self.height // 2, vault_info.get("spawn_regions", ()))
        self._repair_connectivity(
            self.cells, self.player.x, self.player.y,
            protected=vault_info.get("regions"),
            precious=vault_info.get("loot_cells"),
        )
        if not self.realm_id:
            self._place_natural_gas(
                self.cells, layer_seed, depth, self.layer_modifier,
                (self.player.x,self.player.y), vault_info.get('natural_gas_protected', ()))
            for row in self.cells:
                for cell in row:
                    self._prime_material_clocks(cell)
            self._reset_material_index()
        self.enemies = []
        self.world_items = []
        self.events = []
        self.dissolution = 0
        self.turns_since_descend = 0
        self.theme = LAYER_THEMES[min(depth - 1, len(LAYER_THEMES) - 1)]
        # ---- 异象投放（2026-09-18 层数规范化）：定义表里每条异象都有
        # "layers" 起始层是硬下限，结束后仍按 region_falloff 衰减。
        # 强烈异象从本层候选中抽签；核心执念
        # 仍按固定层镇守（10 灯塔 / 20 句号 / 27 初啼）。----
        rng_pool = random.Random(layer_seed ^ 0x7A11C)
        pool = anomaly_pool_for_depth(depth)
        spawn_ids: list[tuple[str, dict[str, int]]] = []
        # 开局保底：前两层固定纸页犬/折页人（按层奇偶）+ 失眠的闹钟，
        # 保证首层就有可交手的异象（新手引导节奏）。
        if depth <= 2:
            first_id = "anomaly.page_hound" if depth % 2 else "anomaly.folded_person"
            # 与普通异象的浅层下限一致（2026-10-22）：保底那只也至少 2 点完整度，
            # 否则 1–3 层仍会刷出 1 血普通异象，与「前 3 层完整度下限 2」矛盾。
            spawn_ids.append((first_id, {"integrity": max(2, 1 + depth // 3)}))
            spawn_ids.append(("anomaly.insomniac_alarm", {}))
        # 楼梯回声只在含楼梯结构的层型（长廊/迷宫）生成（不在通用池）。
        if depth >= 3 and self.map_form in ("长廊", "迷宫"):
            spawn_ids.append(("anomaly.stair_echo", {}))
        # 普通异象：加权抽签填满本层配额（幻觉/无意识领域压力递增）。
        profile = active_profile(self, depth)
        ordinary_count = self._ordinary_anomaly_count(
            profile.ordinary_quota if profile else
            10 + (4 if depth >= 11 else 0) + (2 if depth >= 21 else 0))
        if pool:
            ids = [anomaly_id for anomaly_id, _ in pool]
            weights = [weight for _, weight in pool]
            integrity_base = max(1, round((1 + depth // 4 if depth < 21 else 3 + depth // 9)
                                        * self._enemy_integrity_mult()))
            if profile and depth >= 10:
                integrity_base = max(1, round(profile.ordinary_integrity * self._enemy_integrity_mult()))
            if depth <= 3:
                # 前 3 层铺坡（2026-10-22 难度曲线修复）：原公式在 1–3 层恒为 1、
                # 4 层直接跳到 2（+100%），是新手遇到的第一个无预告跳档。把浅层
                # 下限抬到 2，让 1–4 层连成 2→2 的缓坡；4 层以后公式完全不变。
                integrity_base = max(2, integrity_base)
            reinforced = set()
            if profile and self.difficulty_revision >= 2 and depth in (6, 7):
                # 独立随机流不改变敌人种类、精英签或之后的场景结果。
                fraction = .25 if depth == 6 else .5
                count = int(ordinary_count * fraction + .5)
                reinforced = set(random.Random(layer_seed ^ 0x261023).sample(
                    range(ordinary_count), count))
            for ordinary_index in range(ordinary_count):
                pick = rng_pool.choices(ids, weights=weights, k=1)[0]
                hp = (max(1, round(3 * self._enemy_integrity_mult()))
                      if ordinary_index in reinforced else integrity_base)
                spawn_ids.append((pick, {"integrity": hp}))
        # 强烈异象：layers 覆盖本层的**候选**各自按概率抽签（见
        # STRONG_ANOMALY_SPAWN_CHANCE），保底至少一个。
        strong_candidates = strong_anomaly_ids_for_depth(depth)
        if strong_candidates:
            picked = [strong_id for strong_id in strong_candidates
                      if rng_pool.random() < STRONG_ANOMALY_SPAWN_CHANCE]
            # 分层数量预算（2026-10-22 难度曲线修复）：抽签命中数按层截断。
            # 候选按定义表顺序遍历，截断保留靠前的几只，结果与种子一一对应、
            # 不随候选池长度抖动。保底补上的那只也计入预算（预算最小为 1）。
            budget = profile.strong_budget if profile else strong_anomaly_budget_for_depth(depth)
            picked = picked[:budget]
            if not picked and depth >= 6:
                # 浅层（2-5）的弱强烈只「可能出现」：纯概率抽签、抽空不保底
                # （2026-10-14）；6 层起维持「至少一只」的既有节奏。
                picked = [rng_pool.choice(strong_candidates)][:budget]
            for strong_id in picked:
                spawn_ids.append((strong_id, {}))
        # 核心执念：固定层镇守。
        if depth == 10:
            # 浅梦境的尽头：空心的灯塔坐镇（核心执念，不设胜利条件）。
            spawn_ids.append(("anomaly.hollow_lighthouse", {}))
        if depth == 20:
            # 幻觉空间的核心：未完成句号镇守第 20 层。
            spawn_ids.append(("anomaly.unfinished_period", {}))
        if depth == 27:
            # 无意识领域的核心：初啼之核镇守最深处，解决它才能醒来。
            spawn_ids.append(("anomaly.first_cry", {}))
        for (catalog_id, overrides), (x, y) in zip(spawn_ids, self._distributed_open_cells(
                len(spawn_ids), layer_seed ^ 0xA11CE,
                excluded={pos for pos, _ in vault_info.get("structure_npcs", ())})):
            if profile and ANOMALY_DEFINITIONS[catalog_id].get("anomaly_kind") == "核心执念":
                overrides = {**overrides, "integrity": max(
                    1, round(profile.core_integrity * self._enemy_integrity_mult()))}
            enemy = self.add_defined_enemy(catalog_id, x, y, **overrides)
            if profile and enemy.anomaly_kind == "核心执念":
                enemy.active_skill_state["max_integrity"] = enemy.integrity
        self._spawn_layer_npcs(layer_seed, vault_info)
        self._seed_layer_contents(vault_info)
        self.observe_visible_catalog()
        self._update_doors()
        # 梦中梦入口（引火人 / 潮汐之门）：主梦层按种子确定性安放；关门位面不再安放。
        self._spawn_realm_entries(vault_info)
        self._purge_closed_realm_entries()
        # 行程对账（§6.3）：新生成的层把「账上到站」的旅人投影出来。
        travel.reconcile_layer(self)
        from .main_difficulty import install_progress_site
        install_progress_site(self)

    @root_action
    def descend(self, *, ignore_dissolution: bool = False) -> ActionResult:
        """下潜一层。

        ``ignore_dissolution=True``（调试面板「移动·下潜」专用）**只**跳过
        「崩解度 ≥100」这道发育门槛，其余限制一律照常结算：层数上限、清醒度
        消耗、清醒不足时的心智创伤、行动时间都照走——调试只免发育要求，不改规则。
        """
        if self.realm_id:
            # 梦中梦内：不查崩解度，花 1 点清醒度下穿一层门；到底被拦。
            if not self.can_descend_realm():
                return ActionResult(False, self.messages[-1])
            origin = (self.realm_id, self.realm_depth)
            self._action_time(1)
            if self.run_over or (self.realm_id, self.realm_depth) != origin:
                return ActionResult(True, self.messages[-1])
            changed = self.descend_realm()
            return ActionResult(changed, self.messages[-1])
        if self.depth == 0:
            # 梦的起始：不查崩解度、不扣清醒——离开教学层本身就是引导的终点。
            # 0 层不入快照（没有回头路可走），梦层 1 照常按种子生成。
            self._action_time(1)
            if self.run_over:
                return ActionResult(True, self.messages[-1])
            from .origin_course import finish_loans
            finish_loans(self)
            self.depth = 1
            self.deepest_depth = max(self.deepest_depth, self.depth)
            self.turns_since_descend = 0
            self._restore_or_generate_layer(self.depth)
            self._trim_layer_states()
            message = tutorial_end(self, tr("你离开了梦的起始——它在你身后合拢。"))
            self.messages.append(message)
            return ActionResult(True, message, {"depth": self.depth})
        if self.depth >= 27:
            return ActionResult(False, tr("无意识领域尽头——初啼之渊——没有更深的入口。"))
        if not ignore_dissolution and self.dissolution < 100:
            return ActionResult(False, tr("崩解度还不足以下潜（当前 {value}/100）。", value=self.dissolution))
        target_depth = self.depth + 1
        profile = active_profile(self, target_depth)
        cost = profile.descent_cost if profile else (3 if target_depth <= 10 else 4)
        # 醒梦交界（扩展包 v2）：下潜清醒消耗 -1（最低 1）——认得界线就不用力跨。
        if self.insight_active("醒梦交界"):
            cost = max(1, cost - 1)
        shortage = max(0, cost - self.lucidity)
        # 走行动时间入口而不是裸 _advance：贴身异象的蓄力按客观时间计费，
        # 任何消耗时间的玩家动作（含下潜）都要如实计入。
        self._action_time(1)
        if self.run_over:
            return ActionResult(True, self.messages[-1])
        from .settlement import REASON_ABILITY_COST, settle_delta
        settle_delta(self, 'lucidity', -cost, reason=REASON_ABILITY_COST,
                     source='下潜代价')
        loss = 0
        if shortage:
            loss = self._lose_mind(shortage * 2, source_id='下潜折损')
            message = tr("清醒度不足，强行下潜并承受 {amount} 点心智创伤。", amount=shortage * 2)
        else:
            message = tr("下潜至梦层 {depth}。", depth=target_depth)
        from .failure_review import record_descent
        record_descent(self, target_depth, shortage, loss)
        self._check_run_over()
        if self.run_over:
            return ActionResult(True, self.messages[-1])
        self._archive_active_layer()
        self.depth = target_depth
        self.deepest_depth = max(self.deepest_depth, self.depth)
        self.turns_since_descend = 0
        # 跨层行程（§6.3）：先推进一位在途角色（只动账本），随后的层物化
        # 里的 reconcile_layer 就能把「正好到站这一层」的角色直接投影出来。
        travel.on_descend(self, from_depth=self.depth - 1)
        self._restore_or_generate_layer(target_depth)
        self._trim_layer_states()
        self.messages.append(message)
        # 掉线拨号（§4.1）：主梦 ≥11 层的下潜有 12% 概率引来「网络邻居」。
        self._maybe_dial_in(target_depth)
        return ActionResult(True, message, {"depth": self.depth})

    @root_action
    def backtrack(self) -> ActionResult:
        if self.realm_id:
            # 梦中梦内：上一层；第 1 层上浮 = 回到主梦入口层。
            if self.realm_id == "ebbing_hall" and self.ebbing_past_threshold:
                return ActionResult(False, tr("潮水已经漫过门槛，回头没有路了。"))
            origin = (self.realm_id, self.realm_depth)
            self._action_time(1)
            if self.run_over or (self.realm_id, self.realm_depth) != origin:
                return ActionResult(True, self.messages[-1])
            changed = self.ascend_realm()
            return ActionResult(changed, self.messages[-1])
        if self.depth <= 1:
            if self.depth == 1 and self.tutorial.get("stations"):
                return ActionResult(False, tr("起点已经合拢，回不去了。"))
            return ActionResult(False, tr("没有可回溯的更浅梦层。"))
        if self.depth >= 28:
            return ActionResult(False, tr("深层边界没有回头路——梦到这里只向前。"))
        self._action_time(1)
        if self.run_over:
            return ActionResult(True, self.messages[-1])
        self._archive_active_layer()
        self.depth -= 1
        self.turns_since_descend = 0
        self._restore_or_generate_layer(self.depth)
        self._trim_layer_states()
        message = tr("回溯至梦层 {depth}。", depth=self.depth)
        self.messages.append(message)
        return ActionResult(True, message, {"depth": self.depth})

    def finish_run(self) -> ActionResult:
        if self.run_over:
            return ActionResult(False, tr("这次入梦已经结束。"))
        if not self.victory:
            return ActionResult(False, tr("只有意识沉没或完成第六层牵引后才能结束入梦。"))
        self.run_over = True
        # 跨局继承已删除（2026-10-09）：碎片不再留给下一局，只在本局与旧梦回忆里留痕。
        message = tr("入梦结束。已形成的记忆碎片收进了梦的夹层。")
        self.messages.append(message)
        return ActionResult(True, message)

    MAX_MESSAGES = 500  # 事件记录上限：超出后丢弃最旧消息，避免无界增长拖慢渲染与存档
    # 旧梦层快照的保留窗口：只缓存当前层 ±LAYER_CACHE_WINDOW 层。
    # 为什么可以安全丢弃：上浮（backtrack）一次只走一层、下潜（descend）在离开
    # 本层时立刻重新归档，因此玩家永远只会「就近」回到上一层；被丢弃的远层若真
    # 被返回，_restore_or_generate_layer 会按 seed+depth*1009 重新生成一幅完整
    # 可玩的地形（层型/修饰符/尺寸都由种子确定性推导，实测可站立格、异象、物品
    # 均正常）。代价只是那一层被打过的痕迹（挖开的墙、已采的植物）不再保留——
    # 换来的收益是 GC 遍历的对象数不再随深度增长。
    LAYER_CACHE_WINDOW = 3

    def _imagination_regen_suppressed(self) -> bool:
        """摇篮曲哼唱者（半径 4 光环）：想象力自然恢复暂停。

        同一份判定同时供世界结算（_advance）与自我觉察展示使用，避免面板
        另写一套条件导致「显示已恢复、实际却暂停」。
        """
        return any(
            getattr(enemy, "integrity", 0) > 0 and getattr(enemy, "trait", "") == "lullaby"
            and max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 4
            for enemy in self.enemies
        )

    def _tick_delayed_fuel(self) -> None:
        """焦油弹的分层燃油：第 1、2 回合各再淌下 20 单位（合计十字 60）。

        后续几层只加燃油、**不重新点燃**——设计写明「不额外加伤害」，
        伤害来源只有落点那一次点燃；多出来的油只让火更黏、更久。
        """
        if not self.delayed_fuel:
            return
        from ..materials import floor_fireproof
        pending: list[dict] = []
        for entry in self.delayed_fuel:
            if int(entry.get("due", 0) or 0) > int(self.time):
                pending.append(entry)
                continue
            laid = 0
            for row in entry.get("cells", []) or []:
                gx, gy, amount = int(row[0]), int(row[1]), int(row[2])
                cell = self.cell(gx, gy)
                if floor_fireproof(cell):
                    continue
                # 空地和同种燃油都能再铺一层；别种液体不被焦油顶掉。
                if cell.liquid > 0 and cell.liquid_kind != "燃油":
                    continue
                self._add_liquid(cell, "燃油", amount)
                laid += amount
            if laid:
                self.messages.append(tr("焦油又淌开一层（{n} 单位燃油）。", n=laid))
        self.delayed_fuel = pending

    def _tick_delayed_sounds(self) -> None:
        """延时声源（蜂鸣诱饵）：到点再响一次，响完即摘。

        必须走 `_sound_pulse` 而不是直接改敌人的 alert——否则这几声会绕过
        声路衰减、听觉上限与「不覆盖视觉 last_seen」这些既有口径。
        """
        if not self.delayed_sounds:
            return
        pending: list[dict] = []
        for entry in self.delayed_sounds:
            due = int(entry.get("due", 0) or 0)
            if due > int(self.time):
                pending.append(entry)
                continue
            x = int(entry.get("x", 0) or 0)
            y = int(entry.get("y", 0) or 0)
            source = entry.get("source", "") or ""
            if int(entry.get("depth", self.depth)) != self.depth:
                pending.append(entry)
                continue
            if entry.get("pulse_parameters"):
                self._sound_pulse(x, y, int(entry["radius"]), chain=True,
                                  **entry["pulse_parameters"])
                continue
            if entry.get("wall") and (
                    not self.cell(x, y).solid
                    or int(entry.get("depth", self.depth) or 0) != int(self.depth)):
                # 拍壁这类「敲墙」的延时声源：支撑墙碎了、或已经换层就停，不空敲。
                self.messages.append(tr("{item}的敲击点已经不在了，节拍停了。", item=tr(source)))
                continue
            self._sound_pulse(x, y, int(entry.get("radius", 8) or 8), by_player=True,
                              full_alert=True, category="lure", source=source,
                              chain=True)
            self.messages.append(tr("{item}又嗡了一声——声音还在原处。", item=tr(source)))
        self.delayed_sounds = pending

    def _tick_parry_deadline(self) -> None:
        """镜面碎片的招架期限（2026-10-22 P3 第二轮）。

        架起来的镜面只能在 `parry_until` 之前替你挡一次；到点还没等到打击，
        它自己碎掉——否则一片碎片可以一路架到本层终点，等于常驻减伤。
        判据只看绝对值，不看「跨了几回合」，所以慢动作（amount>1 递归成 1）
        与原地等待都不会漏判。
        """
        if self.parry_charges <= 0 or not self.parry_until:
            return
        if int(self.time) < int(self.parry_until):
            return
        self.parry_charges = 0
        self.parry_until = 0
        self._remember_portent_end(self.player, "mirror_stance")
        self.messages.append(tr("镜面碎片的光褪了——它没能等到下一记打击。"))

    def _advance(self, amount: int) -> None:
        # Slow actions still cross individual world rounds. In particular, a stored
        # board pulse must release at its due round before a later expiry boundary.
        if amount > 1:
            for _ in range(amount):
                self._advance(1)
            return
        previous = self.time
        self.time += amount
        self._logic_energized = set()
        self.turns_since_descend += amount
        # 立场回落按客观回合走（§4.4）：警告后不再犯、离开追责区域满 8 回合，
        # 人才会重新肯听你说话——不能靠玩家按下多少步来换算冷静期。
        from ..world import relations

        relations.cool_down(self)
        self._tick_doll_respawns()
        self._tick_logic_triggers()
        self._tick_magnetized_visual()
        self._tick_pack_walls(amount)
        # 掉线拨号倒计时（§4.1）：随客观回合推进，归零即挂断。
        self._tick_dial_in(amount)
        # 镜面碎片的招架期限：没等到打击就自己碎掉。
        self._tick_parry_deadline()
        # 延时声源（蜂鸣诱饵）：第 3、6 回合各再响一次。
        self._tick_delayed_sounds()
        # 分层燃油（焦油弹）：合计三批 60 单位。
        self._tick_delayed_fuel()
        # 部署类物品的回合结算（2026-10-22 A2）：夜班灯发声、应急蜡封回蜡、
        # 虹吸管搬运、拆迁线轴侵蚀、雷暴放电、安静区衰减、瓶装天亮的燃油。
        from . import item_devices
        item_devices.tick(self)
        # 指标互相侵蚀（扩展设计 2026-09-22）：
        # 心智档3（=0）→ 每5回合清醒 −1；清醒档3（=0）→ 每5回合心智 −1。
        if self.mind_tier >= 3:
            self._mind_drain_tick = getattr(self, "_mind_drain_tick", 0) + amount
            if self._mind_drain_tick >= 5:
                self._mind_drain_tick = 0
                from .settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(self, 'lucidity', -1,
                             reason=REASON_ENVIRONMENT, source='心智崩塌')
                self.messages.append(tr("心智的崩塌波及了清醒（清醒 −1）。"))
        if self.lucidity_tier >= 3:
            self._lucid_drain_tick = getattr(self, "_lucid_drain_tick", 0) + amount
            if self._lucid_drain_tick >= 5:
                self._lucid_drain_tick = 0
                from .settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(self, "mind", -1, reason=REASON_ENVIRONMENT,
                             source="清醒流失侵蚀心智")
                self.messages.append(tr("清醒的流失侵蚀了心智（心智 −1）。"))
        self._check_realm_puzzle()
        # 电路逻辑 v2：门类节点在回合末统一裁决（合辙 ≥2 源 / 分流任意）。
        self.evaluate_gates()
        for circuit_time in range(previous+1, self.time+1):
            self._tick_circuit_boards(circuit_time)
        # 无字校对员的涂黑倒计时：归零时构想恢复可用。
        for ability_id in list(self.redacted_abilities):
            self.redacted_abilities[ability_id] -= amount
            if self.redacted_abilities[ability_id] <= 0:
                del self.redacted_abilities[ability_id]
                self.messages.append(tr("墨迹干透——「{name}」重新可用了。", name=ability_id))
        # 摇篮曲哼唱者（半径 4 光环）：想象力自然恢复暂停。
        humming = self._imagination_regen_suppressed()
        # Material cooldowns advance once per world round, independent of UI passes.
        cerebral_rate = self.hospital_regeneration_rate()
        self._tick_hospital_contact(self.player, amount)
        self.tick_hospital_tools()
        from .hospital_scenes import tick_hospital_scenes
        tick_hospital_scenes(self)
        if humming:
            self.messages.append(tr("摇篮曲在你耳边打转——想象力停止回流。"))
        else:
            # 留白线（blank_edge）：想象力见底时把效力当额外回流（越空虚越补）。
            # 「想象灵感」高档位再有开局选项的额外回流（imagination_regen）。
            for offset in range(amount):
                bonus = self._blank_edge_bonus(resonance=self.resonance_turns > offset)
                self.imagination_regen_credit += max(0.0, 1 + self._imagination_regen_bonus()) * cerebral_rate
                recovered = int(self.imagination_regen_credit + 1e-9)
                self.imagination_regen_credit = max(0.0, self.imagination_regen_credit - recovered)
                self.restore_resource('imagination', recovered + bonus, natural=True)
        # 构想计时（扩展包 v1）：凝滞 / 匿踪 / 共鸣 剩余回合递减。
        if self.vanish_turns > 0:
            self.vanish_turns = max(0, self.vanish_turns - amount)
            if self.vanish_turns == 0:
                self.messages.append(tr("你的轮廓重新显形了。"))
        if self.resonance_turns > 0:
            self.resonance_turns = max(0, self.resonance_turns - amount)
        # 联想盘：每个客观回合最多成功 1 次新增反馈，回合边界清零计数；
        # 缓冲与待释放脉冲按各自过期时间失效（不靠往返层刷新）。
        self.board_round_tick()
        previous_cell = self.board_previous_cell
        current_cell = (self.player.x, self.player.y)
        if previous_cell != current_cell:
            self.board_previous_cell = current_cell
            self._note_board_touch(previous_cell)
        # 位置历史（回闪用）：每推进一回合记一次，留 12 条。
        history = getattr(self, "_position_history", None)
        if history is None:
            from collections import deque as _deque
            history = self._position_history = _deque(maxlen=12)
        history.append((self.player.x, self.player.y))

        # 心智回复：每 MIND_REGEN_INTERVAL 回合 +1（按跨过的刻度结算）。
        # 洞察「愈合梦」：心智回复间隔 5 → 4。
        regen_interval = 4 if self.insight_active("愈合梦") else MIND_REGEN_INTERVAL
        for _ in range(self._rounds_crossed(previous, self.time, regen_interval)):
            from .settlement import REASON_RESTORE_NATURAL
            # Attribute the world-clock recovery without changing the legacy
            # equipment feedback flags or granting a new derived bonus.
            self.restore_resource('mind',1,reason=REASON_RESTORE_NATURAL,source='自然心智恢复')
        # Each ingested dose keeps its own due dates; legacy remaining debt is
        # migrated once, without resetting the payment phase.
        from .drug_debts import tick as tick_drug_debts
        tick_drug_debts(self, previous)
        # 征兆管线：接触材料 → 赋予若干回合；站在其中计时冻结；离开后逐回合
        # 衰减到消失。泪滴溶液的回暖与灼热蒸汽的灼伤都由这条管线统一结算
        # （分别对应「回暖」「灼伤」两条征兆），不再有并列的散装分支。
        # 站在以太上时整条管线悬停：既不赋予、不衰减，也不结算周期效果。
        current_cell = self.cell(self.player.x, self.player.y)
        self._clear_sleep_portents(self.player, self.player.x, self.player.y)
        # 无意识领域贴近墙（梦魇岩/呜咽晶柱/蚀梦菌毯）：独立于征兆结算，
        # 以太悬浮不暂停它——地形本身的压迫不属于「身上的征兆」。
        self._tick_region_proximity(amount)
        self._tick_plant_proximity(amount)
        # 植物的常驻周期效果（吸雾/吸墨/搬气/净化）：只按真实世界回合推进，
        # 预算写进格子，暂停与菜单停留不积累；视觉只按真实消耗登记一次。
        self._tick_periodic_plants_visual(amount)
        if self._cell_holds_material(current_cell, "以太"):
            pass  # 以太悬浮：有持续时间的征兆全部失效并停止倒计时与结算
        else:
            for portent_id in self._grant_material_portents(self.player, current_cell):
                self.messages.append(tr("你沾染了「{name}」的征兆。", name=tr(portent_def(portent_id).name)))
            # 铅板屏蔽：授权后移除被铅板挡住的辐射病（邻格有铅板时不授予）。
            self._lead_shield(self.player, self.player.x, self.player.y)
            # 先结算效果、再递减到期：大步长推进（如一次等 28 回合）时，
            # 到期前的最后一段效果也必须如实结算，而不是随过期一起被吞掉。
            self._apply_player_portent_effects(amount)
            if "honeyed" in self.portents:
                self._tick_honeyed(amount)

            for portent_id in self._tick_entity_portents(self.player, current_cell, amount):
                self.messages.append(tr("「{name}」的征兆散去了。", name=tr(portent_def(portent_id).name)))
        if self.light_turns > 0:
            self.light_turns = max(0, self.light_turns - amount)
            if self.light_turns == 0:
                self.messages.append(tr("灯塔的光收了回去，梦境重新合拢。"))
        # R03 留灯的避难圈抵抗窗口：玩家级限时 buff，按世界回合递减到 0 即散。
        if self.portent_ward_turns > 0:
            self.portent_ward_turns = max(0, self.portent_ward_turns - amount)
            if self.portent_ward_turns == 0:
                self.messages.append(tr("避难圈的灯圈暗了下去，那点抵抗散了。"))
        # 主动构想的冷却与持续效果按回合递减。
        if self.ability_turns.get('wide_develop', 0) > 0:
            position = (self.player.x, self.player.y)
            if position != getattr(self, '_wide_develop_last', None):
                self._wide_develop_last = position
                from .vision import knowledge as _knowledge
                learned = _knowledge.record_terrain_snapshot(
                    self, position[0], position[1],
                    8 + self.memory_stat_bonus("survey"))
                if learned:
                    self.messages.append(tr(
                        "拓印随你移动：又记下 {n} 格地形。", n=learned))
        for ability_id in list(self.ability_cooldowns):
            self.ability_cooldowns[ability_id] = max(0, self.ability_cooldowns[ability_id] - amount)
        for ability_id in list(self.ability_turns):
            self.ability_turns[ability_id] = max(0, self.ability_turns[ability_id] - amount)
        self._simulate_materials(amount)
        from .construct_environments import tick as tick_construct_environments
        tick_construct_environments(self, amount)
        pre_belt = {id(e): (e.x, e.y) for e in (self.player, *self.enemies) if e.integrity > 0}
        from ..world import scenes as world_scenes
        # 进院子这件事在敌方行动前后各记一次：它可能本回合「先进后出」。
        world_scenes.mark_invasions(self)
        self._enemy_turns(amount)
        world_scenes.mark_invasions(self)
        from .tactical_layouts import tick_tactical_layouts
        tick_tactical_layouts(self,amount)
        # 传送带（扩展包 v1）：本回合没有移动的生物沿传送带方向推行一格。
        self._tick_conveyors_visual(pre_belt)
        # Pressure and proximity inputs also reflect the creatures' final positions.
        self._tick_circuit_boards()
        # §12 F：设施的亮灭跟随真实状态（断电的弧光灯架、熄灭的余烬灯盏）。
        # 必须排在电路结算之后：本回合刚通电/断电的结果要立刻反映到灯具上。
        from .fixtures import sync_light_fixtures
        sync_light_fixtures(self)
        self._tick_anomaly_refresh(amount)
        # 混乱/篡改召来的专属异象（2026-10-27）：每回合推进一次。实现见
        # core/chaos_anomalies.py（task-C 接管该模块，这里只固定接线）。
        from .chaos_anomalies import tick_chaos_anomalies
        tick_chaos_anomalies(self, amount)
        if self.lucidity == 0 and self.depth < 28 and not self.realm_id:
            # 深层边界禁用远域覆写：模板与剧情结构神圣不可覆写。
            for _ in range(self._rounds_crossed(previous, self.time, REMOTE_OVERWRITE_INTERVAL)):
                self._remote_overwrite()
        # 退潮厅（2026-10-08）：按客观回合推进边界收缩；失败只退出位面，不置 run_over。
        self._tick_ebbing(previous, amount)
        from .realm_challenges import tick_ember
        tick_ember(self, amount)
        # The final protected round includes its environment and enemy steps.
        if self.stasis_turns > 0:
            self.stasis_turns = max(0,self.stasis_turns-amount)
            if self.stasis_turns==0:
                self.messages.append(tr("凝滞的硬壳碎裂——你重新能动弹了。"))
        if self.mind <= 0 and self.lucidity <= 0:
            self._check_run_over()
        # 胜利：解决第 27 层核心执念（初啼之核）。2026-09-19 按 用户拍板清除
        # 「第 20 层未完成句号也算胜利」的旧设计——句号仍镇守 20 层，但击破
        # 它不再终结这一局。
        if (
            self.depth == 27
            and not self.victory
            and any(enemy.anomaly_kind == "核心执念" and enemy.integrity <= 0 for enemy in self.enemies)
        ):
            self.victory = True
            self.messages.append(tr("核心执念停止书写。你找到了醒来的条件。"))
            if self.depth == 27 and not any(
                entry.event_id == "epilogue.rift" for entry in self.events
            ):
                # 深潜裂隙：胜利后再给一个选择——醒来（A）或深潜（28 层）。
                rift_x, rift_y = self.player.x, self.player.y
                for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)):
                    cand = self.cell(self.player.x + dx, self.player.y + dy)
                    if not cand.solid:
                        rift_x, rift_y = self.player.x + dx, self.player.y + dy
                        break
                self.events.append(WorldEvent(
                    event_id="epilogue.rift", name="深潜裂隙", x=rift_x, y=rift_y,
                    description="初啼之核崩解处裂开一道向下的缝。深处有写字的声音。",
                    catalog_id="epilogue.rift", kind="compound",
                    dialogue=("裂隙里透上来的不是光，是更深的黑。黑里有笔尖划纸的沙沙声。",
                              "跳下去，就能找到那个「写字的人」。或者，就此醒来。"),
                    options=(
                        {"label": "就此醒来（结局：初醒）", "epilogue": {"act": "wake"}},
                        {"label": "深潜（清醒 -8，进入深层边界）", "epilogue": {"act": "deep_dive"}},
                    ),
                    bound=True,
                ))
                # 2026-09-22：结局选择直接送达——裂隙生成的同时置起事件对话，
                # UI 在 _apply 末尾统一检测 pending_event_id 展开左侧面板，
                # 玩家不用再去地图上找裂隙格回应。
                self.open_event_dialog(self.events[-1])
        # 测试模式「自我增强」（2026-09-22）：清醒无敌 / 想象无限。清醒与想象
        # 的扣减入口太多（敌人、征兆、材料、交易、层间移动……），逐处拦截
        # 必然漏；统一在每刻末尾回满最可靠——瞬时下降不累积，下一刻即满档。
        from .settlement import REASON_DEBUG, settle_delta
        if self.debug_lucidity_invincible and self.lucidity < self.max_lucidity:
            settle_delta(self, "lucidity", self.max_lucidity - self.lucidity,
                         reason=REASON_DEBUG, source="调试无敌")
        if self.debug_imagination_infinite and self.imagination < self.max_imagination:
            settle_delta(self, "imagination", self.max_imagination - self.imagination,
                         reason=REASON_DEBUG, source="调试无限")
        self.observe_visible_catalog()
        if len(self.messages) > self.MAX_MESSAGES:
            del self.messages[: len(self.messages) - self.MAX_MESSAGES]

    # ---- 异象自然补刷（2026-10-25）----
    # 规则：
    # - 本层当前自然异象越少，补刷间隔越短；最快 20 回合一只。
    # - 当前数量达到 ANOMALY_REFRESH_ACTIVE_CAP 后不再自然刷新。
    # - 落点从全图合法开放格中均匀抽取（视野外、离玩家至少 4 格、无生物/事件）。
    # - 定义里写 spawn_terrain 的异象只在该地形上成形（如纸鱼只认液面）。
    def _natural_anomaly_count(self) -> int:
        """本层当前自然游荡的失控意识数（不含召唤物、核心执念、NPC/玩偶）。

        定义带 spawn_only 的专属召唤异象（篡改风险召来的漏字者、混乱召来的
        专属异象）不算自然游荡：它们是机制的产物，不应抬高本层自然补刷的上限
        判断与补刷间隔（见 core.chaos_anomalies 的投放约定）。
        """
        return sum(
            1 for enemy in self.enemies
            if enemy.integrity > 0
            and enemy.relation == "失控意识"
            and not enemy.main_id
            and enemy.anomaly_kind != "核心执念"
            and enemy.catalog_id in ANOMALY_DEFINITIONS
            and not ANOMALY_DEFINITIONS[enemy.catalog_id].get("spawn_only")
        )

    def _anomaly_refresh_interval(self, active: int | None = None) -> int:
        """当前补刷间隔：数量越少越快，夹在 20–40 回合之间。"""
        if active is None:
            active = self._natural_anomaly_count()
        cap = max(1, ANOMALY_REFRESH_ACTIVE_CAP)
        ratio = min(1.0, max(0.0, active / cap))
        span = max(0, ANOMALY_REFRESH_INTERVAL - ANOMALY_REFRESH_MIN_INTERVAL)
        return max(ANOMALY_REFRESH_MIN_INTERVAL,
                   round(ANOMALY_REFRESH_MIN_INTERVAL + span * ratio))

    @staticmethod
    def _anomaly_terrain_ok(definition: dict, cell: Cell) -> bool:
        """异象定义的地形要求是否满足；未写要求则处处合法。"""
        requirement = str(definition.get("spawn_terrain", "") or "")
        if not requirement and definition.get("trait") == "liquid_swimmer":
            # 旧定义没有字段时的兼容口径：亲液异象至少要在液面上。
            requirement = "liquid"
        if not requirement:
            return True
        if requirement == "liquid":
            return cell.liquid > 0
        if requirement == "gas":
            return cell.gas > 0
        if requirement == "plant":
            return bool(cell.plant)
        # 未登记的要求按「不合法」处理，避免静默忽略。
        return False

    def _tick_anomaly_refresh(self, amount: int) -> None:
        """按世界回合推进补刷计时；间隔随当前异象数量动态变化。"""
        if amount <= 0 or self.realm_id or self.depth <= 0 or self.depth >= 28:
            return
        key = f"{self.depth}:anomaly_clock"
        clock = int(self.layer_drop_counts.get(key, 0)) + int(amount)
        for _ in range(ANOMALY_REFRESH_ACTIVE_CAP + 4):
            active = self._natural_anomaly_count()
            if active >= ANOMALY_REFRESH_ACTIVE_CAP:
                clock = 0
                break
            interval = self._anomaly_refresh_interval(active)
            if clock < interval:
                break
            clock -= interval
            self._refresh_anomalies()
        # 允许负值：测试夹具用「极负时钟」暂停自然补刷；正常局从 0 开始只增不减。
        self.layer_drop_counts[key] = int(clock)

    def _refresh_anomalies(self) -> None:
        """补刷一只异象（一次尝试；计时与上限由 _tick_anomaly_refresh 管）。"""
        if self.realm_id or self.depth <= 0 or self.depth >= 28:
            return
        if self._natural_anomaly_count() >= ANOMALY_REFRESH_ACTIVE_CAP:
            return
        pool = anomaly_pool_for_depth(self.depth)
        if not pool:
            return
        visible = self.visible_cells()
        event_cells = {(event.x, event.y) for event in self.events}
        player_x, player_y = self.player.x, self.player.y
        base_cells = []
        for y in range(2, self.height - 2):
            for x in range(2, self.width - 2):
                cell = self.cell(x, y)
                if cell.solid or cell.wall_kind:
                    continue
                if self.entity_at(x, y) is not None or (x, y) in event_cells:
                    continue
                if max(abs(x - player_x), abs(y - player_y)) < 4:
                    continue
                if (x, y) in visible:
                    continue
                base_cells.append((x, y))
        # 全图合法开放格等概率抽取：不再偏向玩家附近或某个角落。
        candidates = base_cells
        if not candidates:
            return
        ids = [catalog_id for catalog_id, _ in pool]
        weights = [weight for _, weight in pool]
        # 加入 next_enemy_id：同一回合反复补刷（测试/连续失败重试）也不会每次都抽同一点。
        rng = random.Random(self.seed ^ (self.depth * 3571) ^ (self.time * 7919)
                            ^ (self.next_enemy_id * 104729))
        # 地形要求可能排除一部分池子；最多换 8 次候选再放弃。
        for _ in range(min(8, len(ids))):
            catalog_id = rng.choices(ids, weights=weights, k=1)[0]
            definition = ANOMALY_DEFINITIONS[catalog_id]
            legal = [pos for pos in candidates
                     if self._anomaly_terrain_ok(definition, self.cell(*pos))]
            if not legal:
                continue
            x, y = legal[rng.randrange(len(legal))]
            # 本层补刷序号（2026-10-27）：第 1 只自然补刷 = 1，依此类推。掉落率
            # 从第 ANOMALY_REFRESH_FREE_DROP_WAVES + 1 只起按该序号指数衰减；
            # 记在 layer_drop_counts 里跟着本层存档走。
            seq_key = f"{self.depth}:anomaly_refresh_seq"
            seq = int(self.layer_drop_counts.get(seq_key, 0)) + 1
            self.layer_drop_counts[seq_key] = seq
            self.add_defined_enemy(catalog_id, x, y, spawn_wave=seq)
            self.messages.append(tr("梦层的边角又渗出一道轮廓——{name}在远处成形。",
                                    name=tr(definition["name"])))
            return

    # ---- 真实环境结算的视觉旁路（2026-10-26 Task 8）------------------------
    def trigger_platform(self, x: int, y: int, *, safe_note: str = "") -> None:
        """真实陷阱/机关触发后的视觉旁路；玩法完全复用 LogicMixin。"""
        table = self.cell(x, y).wall_kind
        if table not in ("陷阱石台", "机关石台") or self.circuit_node_at(x, y) is not None:
            LogicMixin.trigger_platform(self, x, y, safe_note=safe_note)
            return
        if table == "陷阱石台":
            from ..materials.logic import TRAP_SCENARIO_LIBRARY
            name = self.trap_scenarios.get(f"{x},{y}")
            scenario = TRAP_SCENARIO_LIBRARY.get(name or "", TRAP_SCENARIO_LIBRARY["dud"])
        else:
            from ..materials.logic import roll_mechanism_scenario
            scenario = roll_mechanism_scenario(self.seed, self.depth, x, y)
        safe = table == "陷阱石台" and (
            bool(safe_note) or self._effect_power("wire_safe") > 0)
        before = _environment_visual_snapshot(self, x, y, scenario)
        self._visual_scenario_active = True
        try:
            LogicMixin.trigger_platform(self, x, y, safe_note=safe_note)
        finally:
            self._visual_scenario_active = False
        _note_environment_trigger(
            self, x, y, scenario, before, safe=safe, safe_note=safe_note)

    def _execute_scenario(self, x: int, y: int, scenario: dict, label: str = "") -> None:
        """场景结果统一入口：电路/石台触发的真实结果共用一次视觉登记。"""
        if getattr(self, "_visual_scenario_active", False):
            LogicMixin._execute_scenario(self, x, y, scenario, label=label)
            return
        before = _environment_visual_snapshot(self, x, y, scenario)
        LogicMixin._execute_scenario(self, x, y, scenario, label=label)
        _note_environment_trigger(
            self, x, y, scenario, before, safe=False, safe_note="")

    def _tick_periodic_plants_visual(self, amount: int) -> None:
        """真实回合的常驻植物结算；只按预算真实消耗登记一次视觉事件。"""
        from .plant_release import tick_periodic_plants
        before = _periodic_plant_snapshot(self)
        if not before:
            tick_periodic_plants(self, amount)
            return
        actor_portents = {id(e): dict(e.portents) for e in _periodic_actors(self)}
        from .visual_events import peek_visual_events
        prior_ids = {id(event) for event in peek_visual_events(self)}
        tick_periodic_plants(self, amount)
        # 并发方 plant_release 已按真实结果显示常驻通道时，不再重复登记聚合事件。
        external = [event for event in peek_visual_events(self)
                    if id(event) not in prior_ids and event.layer_key == "plant.periodic"]
        if not external:
            _note_periodic_plant_results(self, before, actor_portents)

    def _tick_magnetized_visual(self) -> None:
        """磁化液态记忆的真实拉拽：只在玩家真的被拉动一格时登记。"""
        before = (self.player.x, self.player.y)
        self._tick_magnetized()
        after = (self.player.x, self.player.y)
        if after == before:
            return
        _emit_environment_move(self, "magnetized", before, after, "player")

    def _tick_conveyors_visual(self, pre_positions: dict) -> None:
        """传送带真实推行：只登记本回合真的被传送带走了一格的生物。"""
        before = {id(e): (e.x, e.y) for e in (self.player, *self.enemies)
                  if e.integrity > 0}
        self._tick_conveyors(pre_positions)
        for entity in (self.player, *self.enemies):
            if entity.integrity <= 0:
                continue
            start = before.get(id(entity))
            end = (entity.x, entity.y)
            if start is None or end == start:
                continue
            _emit_environment_move(
                self, "conveyor", start, end,
                "player" if entity is self.player else "anomaly")


# ---- 环境/陷阱视觉旁路（2026-10-26，ASCII 动画扩展 Task 8）-----------------
# 全部只读真实结果：触发前后仅比对石台周边与玩家 R1，不做全图差分。
_ENVIRONMENT_VISUALS = {
    "summon": ("environment.summon_seam", 1, "release"),
    "cage": ("environment.cage_lock", 1, "release"),
    "projectile": ("environment.bolt_trap", 1, "hit"),
    "gas": ("environment.gas_vent", 1, "hit"),
    "terrain": ("environment.stone_lock", 2, "hit"),
    "reveal": ("environment.reveal_scan", 1, "hit"),
    "imagination": ("fx.memory", 1, "hit"),
    "portent": ("fx.memory", 1, "hit"),
}
_PERIODIC_MAT_OFFSETS = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))


def _plant_code(cell) -> int:
    """格子植物编号（协议是 int，0 = 无植物）。

    2026-10-28：旧夹具/旧存档可能把「无植物」写成空串。常驻植物结算是每回合
    都会走的路径，这里把假值一律当 0，非数字按 0 处理——不让一个坏格子把整条
    回合结算打死（有效整数原样返回，语义不变）。
    """
    value = getattr(cell, "plant", 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _environment_cell_signature(cell) -> tuple:
    return (
        int(cell.gas), str(cell.gas_kind), int(cell.liquid), str(cell.liquid_kind),
        int(cell.flame), int(cell.integrity), str(cell.wall_kind), bool(cell.solid),
        _plant_code(cell),
    )


def _environment_projectile_path(state, x: int, y: int) -> tuple:
    """弩箭的真实直线：从石台出发，撞墙即止，不借玩家 last_projectile。"""
    px, py = int(state.player.x), int(state.player.y)
    if (px, py) == (int(x), int(y)):
        return ()
    dx = (px > x) - (px < x)
    dy = (py > y) - (py < y)
    if dx and dy:
        dy = 0
    path = []
    cx, cy = int(x) + dx, int(y) + dy
    while 0 <= cx < state.width and 0 <= cy < state.height:
        if state.cell(cx, cy).solid:
            break
        path.append((cx, cy))
        if (cx, cy) == (px, py):
            break
        cx += dx
        cy += dy
    return tuple(path)


def _environment_visual_watch_points(state, x: int, y: int, scenario: dict) -> tuple:
    radius = max(3, int(scenario.get("radius", 0) or 0))
    points: list = []
    seen: set = set()
    for ny in range(max(0, y - radius), min(state.height, y + radius + 1)):
        for nx in range(max(0, x - radius), min(state.width, x + radius + 1)):
            pos = (nx, ny)
            if pos not in seen:
                seen.add(pos)
                points.append(pos)
    px, py = int(state.player.x), int(state.player.y)
    for ny in range(max(0, py - 1), min(state.height, py + 2)):
        for nx in range(max(0, px - 1), min(state.width, px + 2)):
            pos = (nx, ny)
            if pos not in seen:
                seen.add(pos)
                points.append(pos)
    return tuple(points)


def _environment_visual_snapshot(state, x: int, y: int, scenario: dict) -> dict:
    points = _environment_visual_watch_points(state, x, y, scenario)
    # 只读已有显影集合：不用 developed_for_depth()，避免为未访问层 setdefault 新键。
    developed = state.developed_cells.get(str(state.depth), set())
    return {
        "points": points,
        "cells": {pos: _environment_cell_signature(state.cell(*pos)) for pos in points},
        "developed": {pos: pos in developed for pos in points},
        "player_pos": (int(state.player.x), int(state.player.y)),
        "mind": int(state.mind),
        "imagination": int(state.imagination),
        "portents": dict(state.player.portents),
        "enemies": {e.id: (int(e.x), int(e.y), int(e.integrity))
                    for e in state.enemies if e.integrity > 0},
        "projectile_path": (
            _environment_projectile_path(state, x, y)
            if str(scenario.get("type")) == "projectile" else ()
        ),
    }


def _environment_visual_after(state, before: dict) -> dict:
    developed = state.developed_cells.get(str(state.depth), set())
    return {
        "cells": {pos: _environment_cell_signature(state.cell(*pos))
                  for pos in before["points"]},
        "developed": {pos: pos in developed for pos in before["points"]},
        "player_pos": (int(state.player.x), int(state.player.y)),
        "mind": int(state.mind),
        "imagination": int(state.imagination),
        "portents": dict(state.player.portents),
        "enemies": {e.id: (int(e.x), int(e.y), int(e.integrity))
                    for e in state.enemies if e.integrity > 0},
    }


def _note_environment_trigger(state, x: int, y: int, scenario: dict,
                              before: dict, *, safe: bool, safe_note: str) -> None:
    """陷阱/机关一次真实触发只登记一个事件；失败分支只记空结果。"""
    from .visual_events import emit_visual

    after = _environment_visual_after(state, before)
    scenario_type = str(scenario.get("type") or "")
    if safe:
        facts = (
            ("scenario", scenario_type),
            ("isolation", "safe_note" if safe_note else "insulated_gloves"),
        )
        emit_visual(
            state, kind="environment.safe", outcome="hit", source=(x, y),
            targets=(), paths=(), affected_cells=(),
            visual_key="default", tier=0, theme="environment", facts=facts,
            layer_key="environment",
        )
        return
    if scenario_type in ("", "dud"):
        emit_visual(
            state, kind="environment.dud", outcome="hit", source=(x, y),
            targets=(), paths=(), affected_cells=(),
            visual_key="fx.spark", tier=0, theme="environment",
            facts=(("scenario", scenario_type or "dud"),),
            layer_key="environment",
        )
        return

    changed = [pos for pos in before["points"]
               if after["cells"][pos] != before["cells"][pos]]
    revealed = [pos for pos in before["points"]
                if after["developed"][pos] and not before["developed"][pos]]
    new_enemies = [(xy[0], xy[1]) for eid, xy in after["enemies"].items()
                   if eid not in before["enemies"]]
    mind_delta = max(0, before["mind"] - after["mind"])
    imagination_delta = max(0, after["imagination"] - before["imagination"])
    portent_gain = sorted(
        key for key, value in after["portents"].items()
        if int(value) > int(before["portents"].get(key, 0))
    )
    gas_cells = []
    gas_amount = 0
    for pos in changed:
        delta = int(after["cells"][pos][0]) - int(before["cells"][pos][0])
        if delta > 0:
            gas_cells.append(pos)
            gas_amount += delta
    fence_cells = [pos for pos in changed
                   if after["cells"][pos][6] == "意识栅栏"
                   and before["cells"][pos][6] != "意识栅栏"]
    hardened = [pos for pos in changed
                if after["cells"][pos][6] == "坚实聚合物"
                and before["cells"][pos][6] != "坚实聚合物"]

    facts: list = [("scenario", scenario_type)]
    affected: tuple = ()
    paths: tuple = ()
    visual_key, tier, outcome = _ENVIRONMENT_VISUALS.get(
        scenario_type, ("fx.impact", 1, "hit"))
    result = "empty"
    if scenario_type == "summon":
        count = len(new_enemies)
        result = "summoned" if count else "empty"
        affected = tuple(new_enemies)
        facts.append(("count", count))
    elif scenario_type == "projectile":
        hit = mind_delta > 0
        result = "hit" if hit else "missed"
        path = before["projectile_path"]
        paths = (path,) if path else ()
        affected = ((int(before["player_pos"][0]), int(before["player_pos"][1])),) if hit else ()
        facts.append(("hit", bool(hit)))
        facts.append(("damage", int(mind_delta)))
    elif scenario_type == "gas":
        result = "released" if gas_cells else "empty"
        affected = tuple(gas_cells)
        facts.append(("gas", str(scenario.get("gas", ""))))
        facts.append(("amount", int(gas_amount)))
        facts.append(("cells", len(gas_cells)))
    elif scenario_type == "cage":
        result = "caged" if fence_cells else "empty"
        affected = tuple(fence_cells)
        facts.append(("fences", len(fence_cells)))
    elif scenario_type == "terrain":
        result = "hardened" if hardened else "empty"
        affected = tuple(hardened)
        facts.append(("hardened", len(hardened)))
    elif scenario_type == "reveal":
        result = "revealed" if revealed else "empty"
        affected = tuple(revealed)
        facts.append(("revealed", len(revealed)))
    elif scenario_type == "imagination":
        result = "granted" if imagination_delta else "empty"
        facts.append(("amount", int(imagination_delta)))
    elif scenario_type == "portent":
        result = "granted" if portent_gain else "empty"
        affected = (after["player_pos"],) if portent_gain else ()
        facts.append(("portent", str(portent_gain[0]) if portent_gain else ""))
    else:
        result = "fired" if changed else "empty"
        affected = tuple(changed)
    facts.append(("result", result))
    emit_visual(
        state, kind="environment.trigger", outcome=outcome, source=(x, y),
        targets=affected, paths=paths, affected_cells=affected,
        visual_key=visual_key, tier=tier, theme="environment",
        facts=tuple(facts), layer_key="environment",
    )


def _periodic_actors(state) -> list:
    actors = [state.player]
    actors.extend(e for e in state.enemies if e.integrity > 0)
    return actors


def _periodic_plant_snapshot(state) -> dict:
    """常驻效果结算前：只扫角色 R1 的植株与它们能吸入/推出的五格。"""
    from .plant_release import ring_cells

    positions: set = set()
    for actor in _periodic_actors(state):
        positions.update(ring_cells(state, actor.x, actor.y, radius=1))
    data: dict = {}
    for (x, y) in sorted(positions):
        cell = state.cell(x, y)
        code = _plant_code(cell)
        if not code:
            continue
        definition = plant_def_for(code)
        if not definition.has_periodic:
            continue
        budget_key = f"budget:{int(code)}"
        state_of_cell = cell.plant_state if isinstance(cell.plant_state, dict) else {}
        total = max(definition.absorb_gas_budget, definition.absorb_liquid_budget,
                    definition.push_gas_budget, definition.purify_budget)
        raw = state_of_cell.get(budget_key)
        remaining = int(total if raw is None else raw)
        mats: dict = {}
        for dx, dy in _PERIODIC_MAT_OFFSETS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            target = state.cell(nx, ny)
            mats[(nx, ny)] = (int(target.gas), str(target.gas_kind),
                              int(target.liquid), str(target.liquid_kind))
        data[(x, y)] = {
            "code": code, "budget_key": budget_key,
            "remaining": remaining, "mats": mats,
        }
    return data


def _note_periodic_plant_results(state, before: dict, actor_portents: dict) -> None:
    """真实回合结算后：每株只按实际消耗的预算登记一次。"""
    from .visual_events import emit_visual

    for (x, y), info in before.items():
        cell = state.cell(x, y)
        if _plant_code(cell) != int(info["code"]):
            continue  # 本回合已被烧毁/淹死：不把旧预算算成新作用
        state_of_cell = cell.plant_state if isinstance(cell.plant_state, dict) else {}
        raw = state_of_cell.get(info["budget_key"])
        remaining = int(info["remaining"] if raw is None else raw)
        spent = int(info["remaining"]) - remaining
        if spent <= 0:
            continue
        channels: list = []
        points: list = []
        push_target = None
        for pos, old in info["mats"].items():
            target = state.cell(*pos)
            new = (int(target.gas), str(target.gas_kind),
                   int(target.liquid), str(target.liquid_kind))
            if new[0] < old[0]:
                channels.append("absorb_gas")
                points.append(pos)
            if new[2] < old[2]:
                channels.append("absorb_liquid")
                points.append(pos)
            if new[0] > old[0]:
                channels.append("push_gas")
                points.append(pos)
                push_target = pos
        purified = None
        purified_pos = None
        for actor in _periodic_actors(state):
            old_portents = actor_portents.get(id(actor), {})
            for portent_id, turns in old_portents.items():
                if int(actor.portents.get(portent_id, 0)) < int(turns):
                    purified = portent_id
                    purified_pos = (int(actor.x), int(actor.y))
                    break
            if purified:
                break
        if purified:
            channels.append("purify")
        ordered: list = []
        for channel in ("absorb_gas", "absorb_liquid", "push_gas", "purify"):
            if channel in channels and channel not in ordered:
                ordered.append(channel)
        if not ordered:
            continue
        affected: list = []
        for pos in points:
            if pos not in affected:
                affected.append(pos)
        if purified_pos is not None and purified_pos not in affected:
            affected.append(purified_pos)
        paths: tuple = ()
        if push_target is not None and push_target != (x, y):
            paths = (((int(x), int(y)), push_target),)
        facts: list = [
            ("plant", int(info["code"])),
            ("spent", int(spent)),
            ("left", int(remaining)),
            ("channels", "+".join(ordered)),
        ]
        if purified:
            facts.append(("portent", str(purified)))
        emit_visual(
            state, kind="plant.periodic", outcome="hit", source=(x, y),
            targets=tuple(affected), paths=paths, affected_cells=tuple(affected),
            visual_key="plant.growth", tier=0, theme="plant",
            facts=tuple(facts), layer_key="plant",
        )


def _emit_environment_move(state, motion: str, start, end, who: str) -> None:
    """真实位移（传送带/磁化）登记一段实际路径。"""
    from .visual_events import emit_visual

    start_point = (int(start[0]), int(start[1]))
    end_point = (int(end[0]), int(end[1]))
    emit_visual(
        state, kind="environment.move", outcome="release", source=start_point,
        targets=(end_point,), paths=((start_point, end_point),),
        affected_cells=(end_point,), visual_key="fold.travel", tier=1,
        theme="environment",
        facts=(("entity", str(who)), ("motion", str(motion))),
        layer_key="environment",
    )
