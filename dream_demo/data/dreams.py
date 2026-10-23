"""梦中梦定义（2026-09-21，支线系统）：可扩展的「梦中梦」注册表。

新增一个梦中梦只需：
1. 在 ``DREAM_REALM_DEFINITIONS`` 里登记一条 ``DreamRealmDef``；
2. 实现或复用一个地形算法名（``generator``，见 core/dreams.py 的
   ``_REALM_GENERATORS`` 查表）；
3. （可选）给 ``entry_item`` 指定的物品挂 ``effect="enter_realm"``、
   ``power=realm 层数`` 之类的入口通道——入口条件天然支持三类：
   使用物品（enter_realm 效果）、与事件/NPC 交互（对 realm_id 调
   ``enter_realm``）、走进特殊地点（地图上放 ``realm_gate`` 数据）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DreamRealmDef:
    realm_id: str
    name: str                  # 显示名（地图型标记）
    layer_count: int           # 层数（realm_depth 从 1 起）
    entry_item: str = ""       # 入口物品 definition_id（使用即进入；不消耗）
    generator: str = "rings"   # 地形算法名
    anomaly_pool: tuple[str, ...] = ()   # 层内异象池（按层加权，见 core/dreams.py）
    anomaly_count: tuple[int, int, int] = (3, 4, 5)  # 每层异象数（按层号-1 取）
    sanctum_items: tuple[str, ...] = ()  # 最内圣所台面上的独特物品（按层依次投放）
    ambient_gas: str = ""      # 环境弥散印象（零星散布）
    wall_kind: str = "门扉之壁"
    npc_gate: bool = False        # 解谜达成 + 与守门人对话后才可下潜
    no_dissolution: bool = False  # 层内不推进崩解度
    npc_for_layer: tuple[str, ...] = ()  # 每层守门人 npc id  # 该 realm 的专属墙种
    # 进入时授予、离开/通关/失败时回收的物品 id（非消耗范式，如引火人的火柴）。
    entry_grant_item: str = ""
    # 位面奖励件池（三选一候选 / 散落拾取候选）；留空表示不发放。
    reward_pool: tuple[str, ...] = ()
    # 圣所物品由**地形生成器自行投放**（2026-10-10 千禧园木屋台面）：
    # True 时 _generate_realm_layer 跳过「地图中心格」通用投放，否则中心开放
    # 的层会同时拿到中心一份 + 木屋一份（双份圣所）。
    sanctum_in_generator: bool = False


# ---- 第一个梦中梦：门之回廊 ----
# 入口 =「门之钥」：累计击败 20 个强烈异象掉落，可反复使用。
# 3 层同心门廊：外环 → 中环 → 内圣所；每层比上一层多一环异象守门。
DOOR_CORRIDOR = DreamRealmDef(
    realm_id="door_corridor",
    name="门之回廊",
    layer_count=3,
    entry_item="door_key",
    generator="rings",
    anomaly_pool=(
        "anomaly.double_exposure", "anomaly.wet_choir",
        "anomaly.nightmare_weaver", "anomaly.forgetter",
        "anomaly.blank_rift", "anomaly.door_mimic",
        "anomaly.door_warden",
    ),
    anomaly_count=(5, 7, 9),
    sanctum_items=("door_hinge", "echo_ring", "corridor_candle"),
    ambient_gas="门隙之风",
    wall_kind="门扉之壁",
)

# ---- 第二个梦中梦：玩具的回忆（解谜/电路向）----
# 4 层；分级随机电路 / 确定性抽取的推箱子，无自然异象、无崩解度。
# 解谜完成后与守门人交谈开启下潜；机关与输入状态随层快照持久化。
TOY_MEMORIES = DreamRealmDef(
    realm_id="toy_memories",
    name="玩具的回忆",
    layer_count=4,
    entry_item="door_key",          # 入口物相同：门之钥（10 层交换事件开启后使用）
    generator="toy_rooms",
    anomaly_pool=(),                 # 禁止自然生成异象
    anomaly_count=(0, 0, 0),
    sanctum_items=(),
    ambient_gas="",
    wall_kind="玩具箱壁",
    npc_gate=True,
    no_dissolution=True,
    npc_for_layer=("npc.toy_bear", "npc.wind_up_soldier", "npc.marionette", "npc.calibrator"),
    reward_pool=("screwdriver", "battery_back", "night_battery", "clear_glass"),
)

# 门之回廊补充：每层守灯人 NPC 与特殊石台事件（玻璃瓶/气球均等概率二选一）。
from .events import EVENT_DEFINITIONS as _EVENT_DEFS_TUPLE

_DREAM_EVENT_DEFS = {
    e["event_id"]: e for e in _EVENT_DEFS_TUPLE
    if e["event_id"] in ("event.dream_bottle", "event.dream_balloon")
}

# 门之回廊补充：每层守灯人 NPC 与特殊石台事件（玻璃瓶/气球均等概率二选一）。
DOOR_CORRIDOR_EVENTS = ("event.dream_bottle", "event.dream_balloon")
DOOR_CORRIDOR_KEEPER = "npc.lantern_keeper"

# ---- 第三个梦中梦：余烬廊桥（2026-10-08，液气涌现向）----
# 单层手关：引液导气 → 点火 → 火沿材料链炸开隔墙 → 撤到防火安全带。
# 入口 = 11–19 层随机出现的固定 NPC「引火人」（开局一次性判定，未必刷新）。
# 进层授予「引火人的火柴」（非消耗，离开即回收），保底火源。
# 终点三选一：输出（怀表/指环）、有限防护（手套）、撤步（靴子）。
EMBER_BRIDGE = DreamRealmDef(
    realm_id="ember_bridge",
    name="余烬廊桥",
    layer_count=1,
    generator="ember_bridge",
    anomaly_pool=("anomaly.stair_echo",),
    anomaly_count=(2,),
    no_dissolution=True,
    wall_kind="门扉之壁",
    entry_grant_item="lighter_match",
    reward_pool=("arsonist_watch", "blast_ring", "singed_gloves", "ember_boots"),
)

# ---- 第四个梦中梦：退潮厅（2026-10-08，高压生存向）----
# 单层潮汐式布局：外环散落留白线件、中心岛出口，每 6 回合边界内吞一圈。
# 入口 = 主梦 12–26 层随机「潮汐之门」地点（表驱动，预留未来支线）+ 26 层保底。
# 未逃出 = 扣 5 心智 + 本局关门，**不结束游戏**（唯一的全局失败仍是双归零）。
EBBING_HALL = DreamRealmDef(
    realm_id="ebbing_hall",
    name="退潮厅",
    layer_count=1,
    generator="ebbing_hall",
    anomaly_pool=("anomaly.stair_echo",),
    anomaly_count=(3,),
    no_dissolution=True,
    wall_kind="门扉之壁",
    reward_pool=("blank_cheque_book", "faded_id_card", "paper_clip"),
)

# ---- 第五个梦中梦：千禧园（2026-10-10，开放式 + emoji 主题）----
# 5 层开放场地；难度对标主梦 20 层；进入 = 掉线拨号（descend 概率触发，
# 见 core/state.py 的 DialInMixin 与文档 §4）。地形 millennium_park。
MILLENNIUM_GARDEN = DreamRealmDef(
    realm_id="millennium_garden",
    name="千禧园",
    layer_count=5,
    entry_item="",                  # 无物品入口：掉线拨号触发
    generator="millennium_park",
    anomaly_pool=(
        # 专属异象（§10.1）
        "anomaly.bsod_warden", "anomaly.rewind_ghost", "anomaly.pager_sprite",
        "anomaly.disco_echo", "anomaly.static_viewer", "anomaly.floppy_collector",
        "anomaly.screensaver_bubble", "anomaly.cursor_hunter",
        "anomaly.startup_chorus", "anomaly.deadlink_roamer", "anomaly.popup_peddler",
        # 主梦混入（§10.2：字形偏符号/象形的**强烈异象**，hp≥11 与园内锚同档；
        # 核心执念不进池——unfinished_period hp45 曾混入被当小怪刷，难度探针逮出；
        # 低层弱怪 mirror_attendant/reverse_drummer/folded_person hp2-4 同步撤换）
        "anomaly.forgetter", "anomaly.moving_staircase",
        "anomaly.nightmare_weaver", "anomaly.blank_rift",
        "anomaly.silent_proofreader", "anomaly.primordial_impulse",
    ),
    anomaly_count=(6, 7, 8, 9, 0),  # 第 5 层 = 零点体育场（§10.3：不投普通异象，千年虫由召唤产生）
    sanctum_items=("dial_tone", "crystal_charm", "usb_drive", "pixel_scrap"),
    sanctum_in_generator=True,      # 木屋台面投放（生成器自理，通用中心投放跳过）
    ambient_gas="拨号音",           # 环境弥散印象（§3）：惰性氛围气体，生成后零星散布
    wall_kind="蓝砖墙",             # 园内默认墙种（emoji）；树/功能簇由生成器染
    no_dissolution=False,           # 崩解度照常推进
    reward_pool=("dial_tone", "screensaver_soda", "usb_drive", "pixel_scrap"),
)

# 潮汐之门的出口保底件（既有的留白线桥接件，不新增）。
EBBING_EXIT_REWARD = "blank_half_page"

# 表驱动「主梦随机门」注册表：为未来支线预留（当前只登记退潮厅）。
# key = realm_id；value 含地点 event_id 与显示名。
REALM_GATE_DEFS: dict[str, dict[str, str]] = {
    "ebbing_hall": {"event_id": "realm_gate.ebbing_hall", "name": "潮汐之门"},
}

# 固定 NPC 入口：realm_id → npc id（关门后按此清理地图上的 NPC）。
EMBER_LIGHTER_NPC = "npc.ember_lighter"
REALM_ENTRY_NPCS: dict[str, str] = {"ember_bridge": EMBER_LIGHTER_NPC}

# 余烬廊桥终点三选一的静态选项文案（保证可被 i18n 翻译、出现时固定）。
EMBER_REWARD_LABELS: dict[str, str] = {
    "arsonist_watch": "取走纵火者怀表（点燃强度 +1）",
    "blast_ring": "取走爆破指环（爆炸半径 +1）",
    "phoenix_robe": "取走凤凰羽衣（火焰免疫）",
    "singed_gloves": "取走焦边的手套（爆炸冲击 −1）",
    "ember_boots": "取走余烬跟的靴子（点燃即撤步）",
}

# 两谷（图书馆/医院）均为层间守门位面（2026-10-14）：每层需完成收集式
# 解谜（散落×2 + 一处机关/设施）才可向更深层下潜；npc_gate 挂在
# descend_realm 的既有检查上，进度记账见 library_gate / hospital_gate。
LIBRARY_PALACE = DreamRealmDef(
    realm_id="library_palace", name="未尽藏书宫", layer_count=5,
    generator="library_palace", anomaly_count=(0, 0, 0, 0, 0),
    npc_gate=True,
    no_dissolution=True, sanctum_in_generator=True,
)

DREAM_REALM_DEFINITIONS: dict[str, DreamRealmDef] = {
    DOOR_CORRIDOR.realm_id: DOOR_CORRIDOR,
    TOY_MEMORIES.realm_id: TOY_MEMORIES,
    EMBER_BRIDGE.realm_id: EMBER_BRIDGE,
    EBBING_HALL.realm_id: EBBING_HALL,
    MILLENNIUM_GARDEN.realm_id: MILLENNIUM_GARDEN,
    LIBRARY_PALACE.realm_id: LIBRARY_PALACE,
}

WHITE_SANATORIUM = DreamRealmDef(
    realm_id="white_sanatorium", name="至白疗所", layer_count=5,
    generator="white_sanatorium", wall_kind="白瓷隔断",
    anomaly_count=(4, 5, 5, 6, 1), npc_gate=True,
    no_dissolution=True, sanctum_in_generator=True,
)
DREAM_REALM_DEFINITIONS[WHITE_SANATORIUM.realm_id] = WHITE_SANATORIUM


def realm_def(realm_id: str) -> DreamRealmDef | None:
    return DREAM_REALM_DEFINITIONS.get(realm_id)

from .realm_challenges import event_definitions
_DREAM_EVENT_DEFS.update(event_definitions())
