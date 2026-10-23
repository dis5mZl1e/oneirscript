"""模拟层的公共常量与枚举。

回合（Round）与行动（Action）的完整术语契约见包顶 core/__init__.py 的注释。
"""

from __future__ import annotations

import math
from enum import Enum

# ---------------------------------------------------------------------------
# 时间轴术语（务必区分，见 terminology-zh-en.md）
#
#   回合（Round）= 客观时间。它是 GameState.time 的刻度，世界按它推进；
#       所有持续效果——征兆计时、周期性伤害/恢复、气体消散、液体挥发、
#       异象刷新与远程覆写——一律按「回合」结算。一次行动消耗几个回合，
#       就结算几个回合的刻度：减速（迟滞、醉意、深眠令行动多耗回合）会如实
#       多结算，亚回合加速把零头累计到 round_debt、攒满 1 回合才结算一次，
#       免费行动（0 回合）则一律不结算。因此效果吃到的是客观时间，而不是
#       「行动次数」。
#
#   time 必须始终是精确的整数刻度——_rounds_crossed 的 // 对齐、
#       异象刷新与远程覆写的 time % N、随机种子 self.seed ^ (self.time * k)、
#       存档 JSON 全都依赖它。亚回合的行动成本请一律走 _spend_action_time()，
#       零头记在 round_debt；**不要**把 time 改成浮点数。
#
#   行动（Action）= 该生物一次行动的时间结算，即 _action_time() 推进的那一段。
#       它**只用于「按行动次数」结算**（_settle_action_effects → action_counts
#       与 _action_count），例如反击（每 N 次攻击行动）、时间偷取（每回合的行
#       动数上限）。要做这类机制就挂在这层，不要另起一套计时；持续效果则一律
#       按「回合」结算，两层不要混用。
#
# 结算方式：一律用 _rounds_crossed(prev, new, interval) 统计「这次行动跨过了
# 几道 interval 刻度」，而不是 self.time % interval == 0。后者在一次行动推进
# 多个回合（amount > 1）时会漏掉被跳过的刻度。
# ---------------------------------------------------------------------------
ANOMALY_REFRESH_INTERVAL = 40
# 补生上限：每个梦层最多这样凭空补生 N 只（纸页犬只在它的登记层数内补生）。
ANOMALY_REFRESH_SPAWN_CAP = 3
MIND_REGEN_INTERVAL = 5
REMOTE_OVERWRITE_INTERVAL = 20
ELEV_STEP = 25
LIQ_MIN_FLOW = 8
LIQ_DIV = 4
GAS_MIN_FLOW = 4
# 普通气体逐格按自身时钟消散，每个周期扣其 dissipation（常见1—3）。
# 有效寿命同时取决于扩散、反应及各用途门槛，不能从单格浓度推算整团寿命。
# 专属气体的 dissipation_period 不使用此普通周期。见术语表「消散」。
# 2026-10-12 50→100：再拉一倍——玩家要走到云边需要回合数，消散不该抢在
# 到达之前把效果抽走；扩散（max_diffusion 同日减半）仍是主稀薄通道。
# 2026-10-15 混乱化改造：100→150，气团存留更久（心智失序档另按 +2×档位
# 放慢）；max_diffusion 同日全表 ×2 撤销下调，扩散重新成为铺开环境的主通道。
# 2026-10-17 天然气体可用窗口：150→240，年龄按各格时钟随扩散传递。
GAS_DECAY_INTERVAL = 240
# 液体挥发周期：现有液体一律不挥发（materials.LIQUID_DEFINITIONS 里 evaporation
# 全为 0），这套「按类型挥发成气团」的机制保留给将来的特殊液体使用。
# 完整容器内的内容物处于封存状态，不挥发。
LIQUID_DECAY_INTERVAL = 20
# 地板吸水周期（海绵聚合物）：每 2 回合吸走 FloorDef.liquid_absorb 点，**不产气**。
# 刻意与 LIQUID_DECAY_INTERVAL 分开：挥发是「隔一阵蒸发一截」，吸水是「一点点渗
# 下去」——用 20 回合的周期会让海绵上的液体每 20 回合突然少一截，观感很突兀。
LIQUID_ABSORB_INTERVAL = 2
# 液体与未登记材料的通用接触下限。气体按 PortentDef.min_amount 独立判定：
# 2026-10-17 普通吸入门槛 3，强控制保留 5/6；气体赋予与冻结使用同一门槛。
# GAS_MIN_FLOW=4 仅控制扩散，不能当成吸入下限；普通浓度 3 的残雾仍可起效。
# 没有「接触时间」条件——踩进去的那一步立即赋予，站在其中计时冻结，离开后
# 逐回合衰减。旧值 20 是「征兆在实战里几乎从不触发」的元凶：一格 100 浓度的
# 材料出生后两回合内就被扩散摊薄到 4–11，远低于 20，于是图鉴/Excel 里写明会
# 给予征兆的液体与气体在游戏里实际上从不给予（实测 8 种子摊薄后仅 2–4% 的格子 ≥20）。
PORTENT_CONTACT_MIN = 5
# 征兆回合计时与层数的硬上限：所有赋值/续期入口统一钳制，防止异常数值
# （道具 power 直写、调试面板注入、存档改码）把计时或层数顶成天文数字。
# 999 回合 ≈ 远超一局的时长，视为「本局常驻」；99 层同理。
PORTENT_DURATION_CAP = 999
PORTENT_STACK_CAP = 99
# 类墙体气体（黑烟 / 灰尘云）起效的「遮蔽强度」下限。
# 强度 = 格内浓度 × 该气体 opacity / 100（见 materials.GasDef.opacity），
# 因此遮挡感重的气体（黑烟 opacity 80）薄薄一层就能挡视线，轻的（灰尘云 35）
# 需要更浓。旧实现直接拿浓度与 20 比：气团扩散摊薄后几乎再没有格子达标，
# 遮蔽就形同虚设。改用强度后，薄而广的烟云照样生效。
SIGHT_OBSCURE_MIN = 12
# 其他生物被侵蚀类征兆灼蚀的节奏（每 N 回合结算一次完整度）。
# 2026-10-07 从 4 提到 2：材料战术（毒/酸/辐射喷洒）的杀伤效率对齐火流的一半，
# 且结算量本身已随深度函数缩放（见 core.enemies._apply_enemy_portent_effects）。
CREATURE_PORTENT_DAMAGE_PERIOD = 2
# 材料「附着」回合数（2026-10-07）：材料征兆被授予时挂上，离开来源材料后
# 附着期内征兆全额续效且不走衰减；站在材料中补满。打蜡的雨衣（liquid_ward）减半。
ATTACH_PORTENT_ROUNDS = 2
# 构筑桥接组件（2026-10-08，平衡方案 §6.1/§8 的六件新组件）用的四个常量。
# 折射印记在目标身上停留的客观回合数（期间从**别的方向**命中才吃加成）。
REFRACT_MARK_TURNS = 3
# 潮润传导的冷却：每 N 客观回合只允许多传一次（方案要求「限定范围与冷却」）。
WET_CONDUCT_COOLDOWN = 6
# 附着追猎的辨识加成上限：无论叠几件、共鸣与否，一次攻击最多加这么多点。
ATTACH_HUNT_BONUS_MAX = 1
# 征兆数值的**深度连续函数**（2026-10-08 玩家定稿，替代昨日的离散档位）：
# 1 区 = ×1、2 区（幻觉）= ×1.5、3 区（无意识）= ×2、4 区（深层）= ×2.5；
# 锚点之间线性插值——连续平滑曲线，不是一档一档跳；结算量 = ceil(定义值 × 因子)，
# **向上取整**（梦中梦取进入时的主层数，见 core.portents._portent_scale_depth）。
PORTENT_SCALE_ANCHORS = ((1, 1.0), (11, 1.5), (21, 2.0), (28, 2.5))


def portent_depth_factor(depth: int) -> float:
    """深度 → 征兆数值因子（锚点间线性插值，连续平滑）。

    depth ≤ 1 取 ×1；超过最后一个锚点（28）钳到 ×2.5。
    """
    first_depth, first_value = PORTENT_SCALE_ANCHORS[0]
    if depth <= first_depth:
        return first_value
    for (d0, v0), (d1, v1) in zip(PORTENT_SCALE_ANCHORS, PORTENT_SCALE_ANCHORS[1:]):
        if depth <= d1:
            return v0 + (v1 - v0) * (depth - d0) / (d1 - d0)
    return PORTENT_SCALE_ANCHORS[-1][1]


def portent_scaled_amount(base: float, depth: int) -> int:
    """征兆结算量 = ceil(|定义值| × 深度因子)，**向上取整**（至少 1），符号不变。"""
    if base == 0:
        return 0
    magnitude = max(1, math.ceil(abs(base) * portent_depth_factor(depth)))
    return magnitude if base > 0 else -magnitude
# 异象追击（追踪态）连续多少回合看不见玩家就丢掉目标：降级回「怀疑」，
# 不再沿实时位置紧咬（转而去最后一次看见玩家的地方）。单位是回合刻度，
# 与 _enemy_turns(amount) 的 amount 同口径。
LOST_TARGET_TURNS = 3
PROJECTILE_MAX_RANGE = 12
# 一个回合内允许的玩家行动次数上限，超过则强行结束回合。
ACTION_COUNT_LIMIT = 3



class Material(str, Enum):
    PLAIN_AGGREGATE = "普通聚合物"
    SOLID_AGGREGATE = "坚实聚合物"
    LIQUID_MEMORY = "液态记忆"
    DIFFUSE_IMPRESSION = "弥散印象"


# 只能出现在墙体外层（贴开放格）的墙材。
EXPOSED_ONLY_WALLS = frozenset({"反光玻璃墙", "冷凝囊壁", "不稳定燃料墙"})

# 物品分类名：**凡能装进栏位的物品，分类名一律是它**。
CORE_CONTROL_WINDOW = 1.0
ELITE_CONTROL_WINDOW = 2.0
CONTROL_RECOVERY_ROUNDS = 2.0
PORTENT_EXTRA_TURN_CAP = 1
PORTENT_STACK_SPEED_MIN = 0.5
PORTENT_STACK_SPEED_MAX = 2.0

# 2026-09-16 由「装备」改名而来，原「携带意象」9 件也已并入（共用一个分类）。
# 判断某件物品能否携带**只看 `item.slot` 真假**，不要拿这个字符串当条件；
# 需要按分类分档时（如掉落预算）用本常量，避免字符串散落多处。
CARRIED_IMAGE = "携带意象"


class ActionKind(str, Enum):
    """一次「行动」的分类：只用于按行动次数结算的效果，不参与时间计算。

    时间成本仍然只由 amount / 速度倍率决定；这一层只回答「这是一次什么行动」。
    """

    MOVE = "move"        # 移动（含撞墙拆墙、上下层）
    ATTACK = "attack"    # 攻击（近战 bump / 远程 fire）
    USE = "use"          # 使用物品 / 材料交互
    FREE = "free"        # 免费行动（dt = 0，双重曝光底片）
    MISC = "misc"        # 其他（等待等）
