"""内容定义门面：定义表本体已拆分到 dream_demo/data/ 父文件夹。

本模块只保留基于定义表的**派生函数与查询接口**（稀有度曲线、异常地点池、
NPC 选项/代价/任务文本、事件选项文本等），并转发全部定义表名字——历史导入
（from .content import X）继续可用。新增定义请改 dream_demo/data/ 对应文件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    import random  # 仅注解用（draw_npc_options 的 rng 参数）

from dream_demo.data.anomalies import (
    ANOMALY_DEFINITIONS,
    ORDINARY_ANOMALY_IDS,
    UNCONSCIOUS_ORDINARY_ANOMALY_IDS,
    UNCONSCIOUS_STRONG_ANOMALY_IDS,
)
from dream_demo.data.abilities import ABILITY_DEFINITIONS
from dream_demo.data.events import EVENT_DEFINITIONS, LAYER_EVENT_IDS, event_candidates
from dream_demo.data.insights import EVENT_INSIGHT_CHANCE, INNATE_INSIGHTS, INSIGHT_DEFINITIONS, INSIGHT_LIMIT
from dream_demo.data.items import (
    ACCESSORY_SLOTS,
    EQUIPMENT_SLOTS,
    ITEM_DEFINITIONS,
    ITEM_RARITIES,
    PROJECTILE_DEFINITIONS,
    RANDOM_OPTION_ITEM_POOL,
)
from dream_demo.data.memory import MEMORY_FRAGMENT_EFFECTS, MEMORY_LIMIT, MEMORY_RARITY
from dream_demo.data.npcs import NPC_DEFINITIONS, NPC_MAX_PER_LAYER, NPC_TRADE_DRAW, STAT_LABELS
from dream_demo.data.quests import QUEST_DEFINITIONS, STRUCTURE_NPC_BINDING
from dream_demo.data.endings import (
    EPILOGUE_ENDINGS,
    EPILOGUE_MICRO_EVENTS,
    EPILOGUE_PROFILE_RULES,
    EPILOGUE_ROOM_POOLS,
)
from dream_demo.data.themes import LAYER_THEMES
from dream_demo.data.validation import validate_or_raise

_content_validated = False


def ensure_content_validated() -> None:
    """加载即校验（重构方案 §2.1、§15 P0），整个进程只做一次。

    源码里的重复字典键、未知字段、指向不存在的物品／液体／任务／洞察、
    免费对话送永久上限、任务扩容超预算，全部报错——不让坏表进游戏，
    也不让同一份坏表被导出到数值总表。

    液体表要延到调用时才导入：``materials`` 与 ``mapgen`` 之间有既有的
    循环导入，在 content 门面里直接 import 会撞上「部分初始化」。
    """
    global _content_validated
    if _content_validated:
        return
    _content_validated = True
    from dream_demo.materials.liquids import LIQUID_DEFINITIONS
    validate_or_raise(
        npcs=NPC_DEFINITIONS,
        events=EVENT_DEFINITIONS,
        quests=QUEST_DEFINITIONS,
        items=ITEM_DEFINITIONS,
        insights=INSIGHT_DEFINITIONS,
        liquids=LIQUID_DEFINITIONS,
        anomaly_ids=tuple(ANOMALY_DEFINITIONS),
    )




def anomaly_pool_for_depth(depth: int, kinds: tuple[str, ...] = ("普通异象",)) -> tuple[tuple[str, float], ...]:
    """按层取加权异象池：登记起始层是硬下限，结束后保留衰减。

    只返回 kinds 指定的 anomaly_kind（默认普通异象；核心执念由固定点位
    生成，不进池）。层数规范化后这里是异象分层投放的唯一来源。
    """
    from ..mapgen import region_falloff
    pool: list[tuple[str, float]] = []
    for anomaly_id, definition in ANOMALY_DEFINITIONS.items():
        if definition.get("anomaly_kind") not in kinds:
            continue
        if not definition.get("pool", True) or definition.get('spawn_realms'):
            # 层型专属（楼梯回声）与镇守核心（灯塔/句号/初啼）不进通用池。
            continue
        if definition.get("spawn_only"):
            # 只由专属机制召唤的异象（漏字者＝篡改风险）：不进任何投放池。
            continue
        layers = definition.get("layers")
        if layers is None or depth < layers[0]:
            continue
        weight = region_falloff(depth, layers[0], layers[1], 2)
        if weight > 0:
            pool.append((anomaly_id, weight))
    return tuple(pool)


# 强烈异象的投放概率（2026-09-21 玩家反馈「强烈异象太多」下调）。
# 旧规则：layers 覆盖本层的**每一个**都必然出现一次，而 band 还带 leak=2 的外溢，
# 于是 12 层往后每层固定 4~6 个、27 层高达 8 个——16 条强烈异象里有小半同时在场，
# 压迫感远超过设计意图（强烈异象本该是「这一层的招牌怪」）。
# 新规则：候选者各自按此概率抽签，命中才投放；**保底至少一个**（见 state 的调用处），
# 免得整层一只都没有、强烈异象的存在感又归零。
# 实测期望值：12 层 6→约 2.1、20 层 6→约 2.1、27 层 8→约 2.8，整体约降 65%。
STRONG_ANOMALY_SPAWN_CHANCE = 0.35

# 强烈异象分层数量预算（2026-10-22 难度曲线修复）：35% 抽签只回答「命中哪些
# 候选」，命中数还要按层截断——浅层（<10）最多 1 只、中段（10–20）最多 2 只、
# 深段（21+，24–27 同样）最多 3 只。截断顺序按候选定义顺序（即
# strong_anomaly_ids_for_depth 的输出顺序）稳定截取；保底补上的那只也计入
# 预算，不会因为保底而超上限。这样同层总完整度的波动从 ±20 压到可控范围，
# 「这一层该有多强」有了稳定预期（审计见 docs/balance-20261022/lead-difficulty.md §1）。
STRONG_ANOMALY_BUDGETS: tuple[tuple[int, int], ...] = ((9, 1), (20, 2), (27, 3))


def strong_anomaly_budget_for_depth(depth: int) -> int:
    """本层强烈异象最多同时投放几只（分层数量预算）。"""
    for max_depth, budget in STRONG_ANOMALY_BUDGETS:
        if depth <= max_depth:
            return budget
    # 深层边界（28+）沿用最末档，避免将来加层时静默变成 0。
    return STRONG_ANOMALY_BUDGETS[-1][1]


def strong_anomaly_ids_for_depth(depth: int) -> tuple[str, ...]:
    """本层的强烈异象**候选**（layers 覆盖当前层，核心执念除外）。

    ⚠️ 这只回答「哪些有可能出现」，**不是最终投放名单**——实际投放由
    ``state`` 按 ``STRONG_ANOMALY_SPAWN_CHANCE`` 抽签决定（见该常量）。
    ``pool=False``（位面专属/深层专属编成）同样不进这里：千禧园专属强烈
    异象的 layers 写 [11,30] 只是「位面内全程在场」的占位，曾经漏进主梦
    中后段的强烈候选（2026-10-11 玩家报告修复）；深层专属由
    ``mapgen/epilogue.EPILOGUE_ANOMALY_POOL`` 自行投放，不依赖本候选。
    """
    return tuple(anomaly_id for anomaly_id, _ in anomaly_pool_for_depth(depth, ('强烈异象',)))




# 物品稀有度（2026-09-18 全面加入）：四档；记忆碎片/交互道具等
# 唯一、剧情或中间材料条目不设稀有度（rarity 缺省 ""）。

# 深度线性：越深越容易见到稀有；非常稀有只有小幅增长、始终低位。
def rarity_weights_for_depth(depth: int) -> tuple[float, float, float, float]:
    """(常见, 少见, 稀有, 非常稀有) 在该层的抽中权重（线性函数）。"""
    steps = max(0, depth - 1)
    common = max(20.0, 100.0 - 3.0 * steps)
    uncommon = 30.0 + 1.5 * steps
    rare = 12.0 + 0.9 * steps
    very_rare = 4.0 + 0.15 * steps
    return (common, uncommon, rare, very_rare)


def roll_rarity(depth: int, rng, luck: float = 0.0) -> str:
    """按深度曲线随机抽一档稀有度。

    ``luck`` 是开局选项「思维流畅」的权重偏移（正 = 更幸运）：把权重从常见
    挪向稀有/非常稀有。权重整体平移而不改形状——深度曲线照旧主导。
    """
    weights = rarity_weights_for_depth(depth)
    if luck:
        common, uncommon, rare, very_rare = weights
        shift = luck * 3.0
        rare = max(1.0, rare + shift)
        very_rare = max(1.0, very_rare + shift * 0.6)
        common = max(5.0, common - shift * 2.0)
        weights = (common, uncommon, rare, very_rare)
    total = sum(weights)
    cursor = rng.random() * total
    for rarity, weight in zip(ITEM_RARITIES, weights):
        cursor -= weight
        if cursor < 0:
            return rarity
    return "常见"


# 各稀有度的候选池（登记了 rarity 的物品按档位聚合）。
def item_is_flammable(item: Any) -> bool:
    """这个物品是否可燃（设计文档 §9.4「火源点燃可燃显化物」）。

    判据只看定义表里的 ``flammable`` 标记——内容数据留在 data/items/ 里，
    这里只做一次查询。未登记 = 不可燃（默认不烧，免得随手一条掉落物被烧没）。
    记忆碎片一律不烧：那是推进内容，被火吃掉不可接受。
    """
    definition_id = getattr(item, "definition_id", None)
    if not definition_id:
        return False
    definition = ITEM_DEFINITIONS.get(definition_id)
    if not definition:
        return False
    if definition.get("category") == "记忆碎片":
        return False
    return bool(definition.get("flammable"))


def items_of_rarity(rarity: str, categories: tuple[str, ...] | None = None) -> tuple[str, ...]:
    return tuple(
        item_id for item_id, definition in ITEM_DEFINITIONS.items()
        if definition.get("rarity") == rarity
        and definition.get("loot", True) is not False
        and (categories is None or definition["category"] in categories)
    )



# 携带意象栏位（依附物有两个栏位；旧存档的"依附物"迁移到第一个）。

# 主动构想（主动技能）：消耗想象力、按回合冷却；书卷/残页使用后随机习得。

# 携带意象掉落池（2026-10-07 数值平衡改版：按区域分四档，T1→T4 数值递进）。
# 取池唯一入口是 equipment_pool_for_depth()；区域交界按混池规则过渡（见该函数）。
#
# T1 浅层梦境（1–10）：基准件，伤害 +1/+2、单侧护甲 −1。
EQUIPMENT_POOL: tuple[str, ...] = (
    "pen_sharp", "heavy_stapler", "patched_pajamas", "leather_apron",
    "rift_shears",
    "lucky_coin", "night_battery", "warm_gloves", "screwdriver", "wax_seal",
    "paper_handle_letterknife", "frayed_sleeve", "broken_tooth_thimble",
)
# T2 幻觉空间（11–20）：效果件为主（点燃/催眠/传导/喷洒），护甲 −2/−2、
# 崩解 +4、修缮 +50。此前 11–20 层沿用 T1 池，扩展包 16 件武器装备
# 也没有自然投放渠道——本池就是为补上这一档而设。
HALLUCINATION_EQUIPMENT_POOL: tuple[str, ...] = (
    "sketch_gloves", "binder_clip_launcher", "voice_recorder_pen",
    "focusing_lens", "dream_tapir_flute", "nail_gun", "dart_gun",
    "water_gun", "hair_dryer",
    "waxed_raincoat", "lead_lined_apron", "phoenix_robe", "static_poncho",
    "metronome_pendant", "lucky_clover", "blast_ring",
    "multitool_knife", "stethoscope",
    # 构筑桥接组件（2026-10-08）：跟着各自的核心件投放——喷水枪/吹风机与
    # 火源、声源件都在 T2，所以这一档先见到「关系件」而不是更多面板件。
    # 四档池必须互不重叠（tests/test_equipment_tiers.py 守着这条规则），
    # 折射流的三棱镜吊坠因此只进 T3（与 null_pen/节拍摆刃同池）。
    "salt_soaked_coil", "ember_boots",
    "hunting_lanyard", "split_tuning_fork",
    "ember_crayon",
)
# T3 无意识领域（21–27）：伤害 +4、双重护甲 −3/−3、视野 +3、崩解 +5、穿透 +3。
UNCONSCIOUS_EQUIPMENT_POOL: tuple[str, ...] = (
    "first_cry_fang", "lightless_cloak", "void_pendant", "fate_coin",
    "deep_thought_chisel", "rift_wax_seal", "dreamweaver_gloves", "swift_thought_ring",
    "null_pen", "pendulum_blade", "carbon_copy_knife",
    # 桥接件的深层续供（2026-10-08）：折射流在 T3 才有趁手的发射件，留白免成本
    # 是「非常稀有」档，只在 21+ 层与门之回廊混池里出现。
    "prism_pendant", "blank_half_page",
)
# T4 深层边界（28–30）：T3 全池 + 门之回廊独特件（低权重混入）。
DEEP_BOUNDARY_EQUIPMENT_POOL: tuple[str, ...] = (
    "door_hinge", "echo_ring",
)


def equipment_pool_for_depth(depth: int) -> tuple[str, ...]:
    """按层混成的携带意象掉落池（区域分层投放的唯一口径）。

    混池规则（元组重复 = 抽中权重）：

    - 1–10  ：T1；
    - 11–17 ：T2×2 为主 + T1 保底（刚进幻觉空间还能见到熟悉的小件）；
    - 18–20 ：T2×2 为主 + T3 混入（交界带提前见到深层装备，约 1/7）；
    - 21–27 ：T3×2 为主 + T2 保底（深层不再掉 T1 破烂——旧实现 21+ 层
      仍有 2/3 概率掉浅层件，是「越深装备越没用」的根源之一）；
    - 28–30 ：T3×2 为主 + 门之回廊独特件（约 2/22）。
    """
    if depth >= 28:
        return DEEP_BOUNDARY_EQUIPMENT_POOL + UNCONSCIOUS_EQUIPMENT_POOL * 2
    if depth >= 21:
        return UNCONSCIOUS_EQUIPMENT_POOL * 2 + HALLUCINATION_EQUIPMENT_POOL
    if depth >= 18:
        return HALLUCINATION_EQUIPMENT_POOL * 2 + UNCONSCIOUS_EQUIPMENT_POOL
    if depth >= 11:
        return HALLUCINATION_EQUIPMENT_POOL * 2 + EQUIPMENT_POOL
    return EQUIPMENT_POOL


# 无意识领域异象池：普通（4）/ 强烈（4）。核心执念（初啼之核）严格限制于 27 层。

# 现实洞察持有上限（原 4，扩至 15）。
# 回应异常地点时授予洞察的概率（2026-09-15 新增）。
# 旧实现「回应必有洞察」，而事件一层只有 1–2 个、洞察池却有几十条，
# 几层就把槽顶满——「降低洞察的出现频率」即由此而来。命中才给，
# 未命中只结算物品与崩解度（事件本身仍是值得跑一趟的资源点）。
# 与生俱来的洞察：开局就带在身上，不经过任何授予通道，也不会产生「获得」提示。
# 上限顶满时它们同样不会被顶替掉（见 GameState._grant_insight）。

# 记忆槽上限（原 2，2026-09-16 扩至 3）。
# 碎片是「可拆卸的洞察」：不占携带意象栏，只挂记忆槽，所以槽位本身就是稀缺资源。

# 记忆碎片效果表：效果名 -> 定义。
#
# 定位（玩家原话）：辅助效果、特定征兆的免疫或正面效果增强、对环境的适应、
# 少量属性提升（如清醒度上限 +10），类似「可以拆卸的洞察或部分携带意象」。
#
# kind 决定效果挂到哪条既有机制上，不改写任何核心结算：
#   - "immunity"：免疫某个征兆。在 _suppressed_portent_ids 里加一条，
#     与已有的「抗灼 / 冷韧 / 抗辐射体质」洞察同一条通道，不另开分支。
#   - "adapt"：环境适应。压掉某种环境造成的迟滞/额外耗时。
#   - "stat"：少量属性提升。提高某个上限（max_lucidity / max_imagination /
#     max_mind），拿到的当下立即回填等量当前值——否则「上限 +10」在满值
#     状态下毫无体感。
# value 一律是正整数，语义随 kind 而定（免疫类不用，适应类=减免强度，
# 属性类=上限增量）。

# ---- 稳定意识（NPC，2026-09-18）----
# 不会被异象锁定与攻击；受到的创伤大幅减免；被攻击不还手。
# 每层最多 NPC_MAX_PER_LAYER 名，生成概率低（平均 2–3 层见到一位）；
# 结构附属 NPC 随结构生成并计入该层名额。
# 图标（2026-09-18 换成各自职业的标志性符号，颜色不变，一眼可辨）：
#   ⌖ 观测镜准星 / ◔ 怀表表盘 / ♆ 魔鬼干草叉 / ⚑ 委托旗帜。
# 交易选项**每项只能完成一次**（state.npc_traded_options 记账）。
#
# 2026-09-18 改版（玩家反馈「买卖太划算」+「交易不透明」）：
#   * **付费交易抽 2–3 项**（NPC_TRADE_DRAW）：同一职业的不同个体卖的东西不一样，
#     对话、赠品、任务与离开独立保留；always 不免除交易上限。货架记在 Entity.npc_options，
#     没抽到的项**既不显示也不能交易**。
#   * **代价下限**：扣心智/清醒度的项一律 ≥10 点；**不再有「完全回复」类兑换**
#     （{"restore": ...}/{"restore_all": True} 在 NPC 表里已禁用，改上限提升或实物）。
#   * 每张表都混着洞察 / 装备 / 消耗品三类所得，单笔交易的性价比因此被摊薄。
#
# 选项字段（与复合事件共用 label/leave/...），另加：
#   cost: {"mind": n} / {"lucidity": n} 消耗心智/清醒度（不足或刚好归 0 时拒绝）；
#         {"cap": ["max_mind", n]} 永久降低上限（高价值）；{"items": [item_id, n]} 消耗指定物品；
#         {"random_gear": n} 随机收走身上（含已装备）n 件携带意象；
#         {"consumables": n} 随机收走 n 件摄入物/易逝物。
#   gain: {"item": id} 给一件实物 / {"insight": 名} 指定洞察 /
#         {"random_insight": True} 随机洞察（不给名字）/ {"stat": ["max_lucidity", n]} 上限提升。
#: 每位稳定意识生成时从交易表里抽几项（含 always 项之外的数量）。



def draw_npc_options(npc_id: str, rng: "random.Random") -> tuple[int, ...]:
    """只抽 2–3 项付费交易；赠品、任务、对话与离开不参与交易名额。"""
    from .npc_offers import is_trade

    table = NPC_DEFINITIONS.get(npc_id, {}).get("options", ())
    if not table:
        return ()
    pool = [index for index, option in enumerate(table) if is_trade(option)]
    count = min(len(pool), rng.randint(*NPC_TRADE_DRAW))
    drawn = set(rng.sample(pool, count)) if count else set()
    drawn.update(index for index, option in enumerate(table) if not is_trade(option))
    return tuple(sorted(drawn))


def npc_definition(npc: Any) -> dict[str, Any]:
    """稳定意识的职业定义。

    职业存在 ``npc_kind`` 上（``npc.id`` 是实例唯一的 enemy-N）；旧存档没有
    ``npc_kind``，那时 ``npc.id`` 就是职业 id，退回按 id 查即可。
    """
    kind = getattr(npc, "npc_kind", "") or getattr(npc, "id", "")
    return NPC_DEFINITIONS.get(kind, {})


def npc_options_for(npc: Any) -> tuple[dict[str, Any], ...]:
    """固定货架；旧档缺失或超额货架按稳定身份抽取，不随显示刷新。"""
    from .npc_offers import limited_shelf

    table = npc_definition(npc).get("options", ())
    drawn = limited_shelf(npc)
    return tuple(table[index] for index in drawn if 0 <= index < len(table))


def npc_trade_key(npc: Any) -> str:
    """一次性交易的记账键：**稳定身份 actor_uid**。

    ⚠️ 别拿职业 id 当键——同一个职业的两位会共用一份「已完成」记录：跟甲做完
    第 1 项，乙那笔（抽到的完全是另一笔交易）也会被标成做过了。
    ⚠️ 也别把坐标拼进键里（旧口径 ``{id}@{x},{y}``）——NPC 会走动，一走就把
    「已完成」的账甩在原地，玩家追上去能再买一遍。actor_uid 由层键＋职业＋
    本层同职业序号推出，走动与层重建都不影响它（见 Entity.actor_uid）。
    """
    uid = getattr(npc, "actor_uid", "")
    if uid:
        return uid
    # 旧存档里生成的 NPC 没有 uid，退回实例 id（至少同层内不会串账）。
    return getattr(npc, "id", "")


def npc_option_key(npc: Any, option: dict[str, Any]) -> str:
    """一条交易选项的**稳定 option_id**（记账、日志、探针都用它，不用显示下标）。

    下标只是 UI 展示序：货架重抽（Entity.npc_options）、show_if 过滤
    （npc_visible_options）都会改变它，用下标记「这项已经买过」会把另一项误标。
    这里拿选项对象在职业交易表里的**身份位置**还原定义序，再交给
    data.ids.npc_option_id 折成语义化 id。
    """
    from ..data.ids import npc_option_id

    kind = getattr(npc, "npc_kind", "") or getattr(npc, "id", "")
    table = NPC_DEFINITIONS.get(kind, {}).get("options", ())
    position = next((i for i, entry in enumerate(table) if entry is option), -1)
    return npc_option_id(kind, position, option)



#: 代价里的上限名 → 人话（面板与导表共用同一口径）。


def quest_name(quest_id: str) -> str:
    """任务可读名（未知 id 原样返回）。"""
    return QUEST_DEFINITIONS.get(quest_id, {}).get("name", quest_id)


def npc_option_visible(state: Any, option: dict[str, Any], npc: Any = None) -> bool:
    """选项可见性（show_if 全部满足才显示）：任务状态 / 赠品组是否已领。"""
    if option.get('deep_dialogue') and state.depth not in (28,29):
        return False
    show = option.get("show_if") or {}
    if "quest_none" in show and state.quests.get(show["quest_none"]):
        return False
    if "quest_active" in show and state.quests.get(show["quest_active"]) != "active":
        return False
    if "quest_done" in show and state.quests.get(show["quest_done"]) != "done":
        return False
    if 'gift_available' in show:
        from .npc_offers import gift_claimed, is_trade
        if (not is_trade(option) and gift_claimed(state, npc, show['gift_available']) if npc is not None
                else state.gift_claims.get(show['gift_available'])):
            return False
    return True


def negotiation_options(state: Any, npc: Any) -> tuple[dict[str, Any], ...]:
    """按立场给出的交涉出路（§4.4）：解释、提出补偿、付补偿，外加一条离开。

    这些是**运行时构造**的选项，不在职业定义表里：它们属于关系状态机的出口，
    而不是某个职业的货架商品，所以每条都自带稳定 ``option_id``（不靠表内位置），
    并在 ``negotiate`` 字段上挂结算入口，由 ``choose_npc_option`` 直接分派。
    """
    from ..world import relations

    entry = relations.record_of(state, npc)
    if entry is None or entry.stance == "中立":
        return ()
    options: list[dict[str, Any]] = []
    if relations.can_explain(state, entry)[0]:
        options.append({"label": "解释：那一下不是冲着你在做的",
                        "option_id": "npc.relation.explain", "negotiate": "explain"})
    if relations.can_propose(state, entry)[0]:
        options.append({"label": "提出补偿（把想象力交出来）",
                        "option_id": "npc.relation.propose", "negotiate": "propose",
                        "cost": {"imagination": entry.restitution
                                 or relations.RESTITUTION_CONFLICT}})
    if entry.stance == "和解中":
        options.append({"label": "按开出的条件付补偿",
                        "option_id": "npc.relation.pay", "negotiate": "pay",
                        "cost": {"imagination": entry.restitution}})
    if not options:
        # 面板要说的是**这一刻具体卡在哪一条**，不是永远同一句「退开几回合」：
        # 实玩里玩家已经退到 24 格外，拦住解释的是店主周围没散的气，
        # 一句「过几回合再来」会把人引向一条怎么走都不通的路。
        reason = (relations.can_propose(state, entry)[1]
                  or relations.can_explain(state, entry)[1]
                  or "先离开，等对方冷静下来")
        options.append({"label": reason, "option_id": "npc.relation.wait", "message": reason})
    options.append({"label": "结束对话", "option_id": "npc.relation.leave", "leave": True})
    return tuple(options)


def npc_visible_options(state: Any, npc: Any) -> tuple[dict[str, Any], ...]:
    """npc_options_for 的可见性过滤版（面板/结算/键位三处共用同一口径）。

    立场敌对／脱离／和解中时货架整体让位给交涉（§4.4「这里的服务暂时关了」）：
    过滤只在这一处做，面板、结算、按键计数因此不可能各说一套。
    """
    from ..world import relations
    from .npc_offers import free_claim_refusal, is_free_claim, gift_dialogue_option, gift_claimed

    options = []
    for option in npc_options_for(npc):
        if option.get('tutorial_only'):
            from .origin_course import is_course
            if not is_course(state): continue
        free_spent = is_free_claim(option) and (free_claim_refusal(state, npc, option)
                     or (option.get('gift_set') and gift_claimed(state, npc, option['gift_set'])))
        if free_spent:
            if not option.get('message'):
                continue
            option = gift_dialogue_option(npc, option)
        if npc_option_visible(state, option, npc):
            options.append(option)
    options = tuple(options)
    if relations.stance_of(state, npc) not in relations.LOCKED_STANCES:
        return options
    # 敌对／脱离／和解中：交涉项就是这一刻的全部选项（至少带一条「结束对话」）。
    return negotiation_options(state, npc) or options


def event_effective_options(state: Any, event: Any) -> tuple[dict[str, Any], ...]:
    """事件当前生效的选项视图（面板与结算共用同一口径，篡改规格 §8）。

    没有改文时直接返回原 ``event.options``（同一批对象，身份查找照旧可用）；
    有改文时返回带原 ``option_id`` 的副本，原定义表不被修改。
    """
    from .tamper_views import resolve_tamper_options, target_for_event

    options = tuple(getattr(event, "options", ()) or ())
    return resolve_tamper_options(state, target_for_event(state, event), options)


def npc_effective_options(state: Any, npc: Any) -> tuple[dict[str, Any], ...]:
    """稳定意识当前生效的可见选项（货架抽取、态度与任务过滤之后再套改文）。"""
    from .tamper_views import resolve_tamper_options, target_for_npc

    return resolve_tamper_options(state, target_for_npc(state, npc), npc_visible_options(state, npc))


def quest_tray_cell(state: Any, quest_id: str) -> tuple[int, int] | None:
    """液体交付类任务的托盘格＝委托人当前站的那一格（方案 §7.2「倒进印版托盘」）。

    找不到委托人（不在本层／已离场）就返回 None：进度读 0，不会拿别处的液体充数。
    """
    quest = QUEST_DEFINITIONS.get(quest_id) or {}
    if (quest.get("requirement") or {}).get("type") != "liquid":
        return None
    giver = quest.get("giver")
    for entity in getattr(state, "enemies", ()):
        if getattr(entity, "npc_kind", "") == giver and entity.integrity > 0:
            return int(entity.x), int(entity.y)
    return None


def quest_liquid_held(state: Any, quest_id: str) -> int:
    """托盘上已交付的液体量：种类对不上就算 0（「容器存在」不等于交付成功）。"""
    position = quest_tray_cell(state, quest_id)
    if position is None:
        return 0
    requirement = (QUEST_DEFINITIONS.get(quest_id) or {}).get("requirement") or {}
    cell = state.cell(*position)
    if cell.liquid_kind != requirement.get("liquid") or cell.liquid <= 0:
        return 0
    return int(cell.liquid)


#: 「计数型」任务需求 → (基线键名, 读数函数)。接取瞬间把读数存成基线。
_COUNTED_REQUIREMENTS = {
    "kill_any": ("kills", lambda state, req: int(state.run_stats.get("kills", 0))),
    "kill_kind": ("kill_kind", lambda state, req: int(state.kills_by_kind.get(req.get("target", ""), 0))),
    "events": ("events", lambda state, req: int(state.run_stats.get("events", 0))),
}


def quest_baseline(state: Any, quest_id: str) -> dict[str, int]:
    """接取任务那一刻的累计量快照。

    进度按「当前累计 − 接取时累计」算（§16.1「接取前击杀不计完整狩猎」）：
    在下层才接的「解决 4 只」不能靠上面攒下的击杀直接兑现。计数型需求之外
    的类型（实物/液体/深度）读的是当下世界状态，不需要基线。
    """
    requirement = (QUEST_DEFINITIONS.get(quest_id) or {}).get("requirement") or {}
    counter = _COUNTED_REQUIREMENTS.get(requirement.get("type"))
    if counter is None:
        return {}
    key, read = counter
    return {key: read(state, requirement)}


def quest_progress(state: Any, quest_id: str) -> tuple[int, int]:
    """任务进度：(已完成量, 需求量)。"""
    quest = QUEST_DEFINITIONS.get(quest_id)
    if quest is None:
        return 0, 1
    if quest.get("template"):
        # 目标实例任务（§7.3）：进度问世界记录，不吃本局累计计数器。
        from ..world import tasks

        record = tasks.lookup(state, quest_id)
        return tasks.progress(state, record) if record is not None else (0, 1)
    requirement = quest["requirement"]
    kind = requirement.get("type")
    if kind == "depth":
        # 绝对目标：需求就是「到第 N 层」，不是「再往下 N 层」。
        return int(state.deepest_depth), int(requirement.get("depth", 1))
    need = int(requirement.get("count", 1))
    base = (getattr(state, "quest_baselines", {}) or {}).get(quest_id) or {}
    if kind == "item":
        have = sum(
            entry.quantity for entry in state.inventory
            if entry.definition_id == requirement.get("item")
        )
    elif kind == "liquid":
        have = quest_liquid_held(state, quest_id)
    elif kind in _COUNTED_REQUIREMENTS:
        key, read = _COUNTED_REQUIREMENTS[kind]
        have = max(0, read(state, requirement) - int(base.get(key, 0)))
    else:
        have = 0
    return have, need


def quest_requirement_text(quest_id: str) -> str:
    """任务需求的可读文本（中文；面板/导表逐段 tr()）。"""
    quest = QUEST_DEFINITIONS.get(quest_id)
    if quest is None:
        return "无"
    # 实例任务（§7.1）的需求口径各模板一套，定义里直接给可读全文；
    # pump_hunt/lamp_refuge 走下面的 target_resolve 分支（target_text）。
    if quest.get("requirement_text"):
        return quest["requirement_text"]
    requirement = quest["requirement"]
    kind = requirement.get("type")
    count = int(requirement.get("count", 1))
    if kind == "item":
        item_name = ITEM_DEFINITIONS.get(requirement.get("item"), {}).get("name", requirement.get("item"))
        return "{item} ×{n}".format(item=item_name, n=count)
    if kind == "liquid":
        return "把{liquid} ×{n}倒进委托人的托盘".format(liquid=requirement.get("liquid"), n=count)
    if kind == "kill_any":
        return "解决失控意识 ×{n}".format(n=count)
    if kind == "kill_kind":
        target = ANOMALY_DEFINITIONS.get(requirement.get("target"), {}).get("name", requirement.get("target"))
        return "解决{target} ×{n}".format(target=target, n=count)
    if kind == "events":
        return "回应异常地点 ×{n}".format(n=count)
    if kind == "depth":
        return "到达第 {n} 层".format(n=requirement.get("depth", 1))
    if kind == "target_resolve":
        # 目标实例任务：把两条允许解法一次说清（§14「明确警告」的同一条口径）。
        return quest.get("target_text", "解决指定的那一位")
    return "无"


def npc_cost_parts(option: dict[str, Any]) -> tuple[tuple[str, dict[str, Any]], ...]:
    """一条交易选项的「代价」拆成 ``(模板, 字段)`` 序列。

    拆开是为了让调用方**逐段 tr()**：面板要英文时逐段查表，导表要中文时
    直接拼。整句拼好再 tr() 会查不到表、只能原样吐中文（i18n 覆盖测试会抓）。
    """
    cost = option.get("cost") or {}
    parts: list[tuple[str, dict[str, Any]]] = []
    if "mind" in cost:
        parts.append(("心智 −{n}", {"n": cost["mind"]}))
    if "lucidity" in cost:
        parts.append(("清醒度 −{n}", {"n": cost["lucidity"]}))
    if "imagination" in cost:
        parts.append(("想象力 −{n}", {"n": cost["imagination"]}))
    if "liquid" in cost:
        liquid, amount = cost["liquid"]
        parts.append(("{liquid} ×{n}（从托盘扣除）", {"liquid": liquid, "n": amount}))
    if "cap" in cost:
        stat, amount = cost["cap"]
        parts.append(("{stat} −{n}", {"stat": STAT_LABELS.get(stat, stat), "n": amount}))
    if "items" in cost:
        item_id, count = cost["items"]
        parts.append(("{item} ×{n}", {"item": ITEM_DEFINITIONS.get(item_id, {}).get("name", item_id), "n": count}))
    if "random_gear" in cost:
        parts.append(("携带意象 ×{n}（含已装备）", {"n": cost["random_gear"]}))
    if "consumables" in cost:
        parts.append(("消耗品或易逝物 ×{n}", {"n": cost["consumables"]}))
    if option.get("accept_quest"):
        parts.append(("要求：{req}", {"req": quest_requirement_text(option["accept_quest"])}))
    if option.get("complete_quest"):
        parts.append(("要求：{req}", {"req": quest_requirement_text(option["complete_quest"])}))
    if option.get("gift_set"):
        parts.append(("三选一赠品（限领一次）", {}))
    return tuple(parts)


def npc_gain_parts(option: dict[str, Any]) -> tuple[tuple[str, dict[str, Any]], ...]:
    """一条交易选项的「所得」拆成 ``(模板, 字段)`` 序列（理由同代价）。"""
    gain = option.get("gain") or {}
    parts: list[tuple[str, dict[str, Any]]] = []
    if gain.get("item"):
        parts.append(("获得 {item}", {"item": ITEM_DEFINITIONS.get(gain["item"], {}).get("name", gain["item"])}))
    if gain.get("insight"):
        parts.append(("洞察「{name}」", {"name": gain["insight"]}))
    if gain.get("random_insight"):
        parts.append(("随机洞察（事前不知道是哪条）", {}))
    if gain.get("restore"):
        which = {"mind": "心智", "lucidity": "清醒度", "imagination": "想象力"}.get(gain["restore"], gain["restore"])
        parts.append(("{name}恢复完全", {"name": which}))
    if gain.get("restore_all"):
        parts.append(("心智、清醒度与想象力全部恢复", {}))
    if gain.get("stat"):
        stat, amount = gain["stat"]
        parts.append(("{stat} +{n}", {"stat": STAT_LABELS.get(stat, stat), "n": amount}))
    return tuple(parts)


def _join_parts(parts: tuple[tuple[str, dict[str, Any]], ...]) -> str:
    if not parts:
        return "无"
    return "、".join(template.format(**fields) for template, fields in parts)


def npc_localized_parts(parts: tuple[tuple[str, dict[str, Any]], ...]):
    """Localize payload fields once, at the display boundary.

    Templates are static keys; item/insight/stat names are stable IDs resolved to
    display names by the caller. Never translate the joined sentence (that loses
    the nested fields and can double verbs such as Gain/Receive).
    """
    from dream_demo.i18n import tr
    localized = []
    for template, fields in parts:
        localized.append((template, {
            key: (tr(value) if key in ("item", "name", "stat", "req")
                  and isinstance(value, str) else value)
            for key, value in fields.items()
        }))
    return tuple(localized)


def npc_cost_text(option: dict[str, Any]) -> str:
    """一条交易选项的「代价」人话（导表 / 日志用；面板请逐段 tr）。"""
    return _join_parts(npc_cost_parts(option))


def npc_gain_text(option: dict[str, Any]) -> str:
    """一条交易选项的「所得」人话（导表 / 日志用；面板请逐段 tr）。"""
    return _join_parts(npc_gain_parts(option))

# ---- 任务系统（2026-09-19）：NPC 可接取/兑现的任务 ----
# requirement.type: item（持有物品×数量）/ kill_any（累计解决失控意识数）/
#                  kill_kind（解决指定异象数）/ events（累计回应事件数）/
#                  depth（到达过的最深层数）。
# ---- 记忆碎片稀有度（2026-09-19）：按碎片 id 分四档，颜色随稀有度 ----
# 随机选项（✦ 事件选项）的候选池：按类别收集带稀有度的物品。
# 交互道具（容器等）刻意不入池——容器只能通过事件与 NPC 交易获取。


# 结构附属 NPC：随结构生成、计入每层名额。


# ---- 深层边界（28–30）：剧情文本池与事件模板 ----

# 三展室记忆池：(记忆文本, 真实来源)。每层按种子从各类各抽一段。

# 深层边界专属微事件（简单事件，落点在外层与内层开放区）。

# 终局五结局：标题与正文段落（{clues}/{kills}/{rounds}/{depth} 等占位）。

# 承担牵引规则：按本局画像生成 29 层专属承担条件。





# ---- 异常地点（事件）的工具函数（2026-09-18）----
# 定义里的 ``uses`` = 这个地点还能触发几次（默认 1，个别更多）；生成时落到
# WorldEvent.uses_left，每结算一次减一，归零即 resolved（不能再回应）。
# 选项字段与 NPC 交易共用一套渲染口径：拆成 (模板, 字段) 序列，调用方逐段 tr()，
# 面板要英文时逐段查表、导表要中文时直接拼。


def event_uses(definition: Mapping[str, Any]) -> int:
    """这个地点的可触发次数（定义没写就是 1，写 0/负数按 1 处理）。"""
    return max(1, int(definition.get("uses", 1) or 1))


def event_spawn_kwargs(definition: Mapping[str, Any]) -> dict[str, Any]:
    """把定义展开成 WorldEvent 的构造参数（``uses`` → ``uses_left``）。

    ⚠️ 定义里的 ``uses`` 不是 WorldEvent 的字段，直接 ``**definition`` 会 TypeError；
    生成路径一律走这里，别在两处各写一遍映射。
    """
    fields = {key: value for key, value in definition.items() if key != "uses"}
    fields["uses_left"] = event_uses(definition)
    return fields


def event_option_label(option: Mapping[str, Any]) -> str:
    """一条事件选项的最终标签（面板与结算共用）。

    标签里可以带 ``{item}``——珍品机会每次摆出来的件不同（按本局已领
    记录挑），所以物品名只能在**渲染时**从 ``reward_id`` 解出来，不能写死
    在定义表里。字段值不参与翻译，必须自己先 ``tr()`` 一次。
    """
    from dream_demo.i18n import tr

    fields: dict[str, Any] = {}
    if option.get("reward_id"):
        name = ITEM_DEFINITIONS.get(option["reward_id"], {}).get("name")
        if name:
            fields["item"] = tr(name)
    return tr(str(option.get("label", "")), **fields)


def event_option_parts(option: Mapping[str, Any]) -> tuple[tuple[str, dict[str, Any]], ...]:
    """一条事件选项的**效果**拆成 ``(模板, 字段)`` 序列（面板/导表共用）。"""
    from dream_demo.i18n import tr

    if option.get("leave"):
        return (("离开（不结算）", {}),)
    parts: list[tuple[str, dict[str, Any]]] = []
    count = max(0, int(option.get("reward_count", 1)))
    if option.get("reward_id") and count:
        name = ITEM_DEFINITIONS.get(option["reward_id"], {}).get("name", option["reward_id"])
        name = tr(name)
        parts.append(("获得 {item} ×{n}", {"item": name, "n": count}) if count > 1
                     else ("获得 {item}", {"item": name}))
    if option.get("dissolution"):
        parts.append(("崩解度 +{n}", {"n": int(option["dissolution"])}))
    for key, label in (("mind", "心智"), ("lucidity", "清醒度"), ("imagination", "想象力")):
        amount = int(option.get(key, 0) or 0)
        if amount:
            parts.append(("{label} {sign}{n}", {"label": label, "sign": "+" if amount > 0 else "−", "n": abs(amount)}))
    return tuple(parts) if parts else (("无额外结算", {}),)


def event_option_text(option: Mapping[str, Any]) -> str:
    """一条事件选项的效果人话（导表 / 日志用；面板请逐段 tr）。"""
    parts = event_option_parts(option)
    return "、".join(template.format(**fields) for template, fields in parts)



# 各层异常地点投放池（§6 事件分布：3–4 层 3 个、5 层 3 个、6 层 2 个；
# 1–2 层沿用既有池的轮转）。新事件集中投放在 3 层以后。




LAYER_THEMES = (
    # 浅梦境 1–10
    "可辨认的房间",
    "拼接的走廊",
    "回声平台",
    "无窗工作室",
    "退色的展馆",
    "未完成的边界",
    "发潮的卧室",
    "重叠的阳台",
    "倒悬的图书馆",
    "无声的剧场",
    # 幻觉空间 11–20
    "幻觉空间·凝胶回廊",
    "幻觉空间·熔化的钟表店",
    "幻觉空间·倒放的花园",
    "幻觉空间·悬浮的楼梯井",
    "幻觉空间·吞声的湖底",
    "幻觉空间·蜡质的剧场",
    "幻觉空间·错位的电梯",
    "幻觉空间·无限镜像",
    "幻觉空间·崩解的边界",
    "幻觉空间·梦的核心",
    # 无意识领域 21–27
    "无意识领域·静默之海",
    "无意识领域·倒悬的深渊",
    "无意识领域·无声的摇篮",
    "无意识领域·巨梦的脊椎",
    "无意识领域·被遗忘的画廊",
    "无意识领域·原初的潮汐",
    "无意识领域·初啼之渊",
)
