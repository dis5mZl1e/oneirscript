
"""属性定义注册表（2026-10-18 docs/261018方案合集.md 第 10 节第二批）。

每个条目只描述「这个数值是什么、单位、汇总约束和玩家可见性」；真实解析在
core/stats.py，结算仍由各自领域函数负责。未接通的条目不得先填一个看似合理
的数值——先登记在这里，等对应批次接入后再加 resolver。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatDefinition:
    key: str
    name: str                 # 中文显示名（渲染时经 tr）
    category: str             # persistent / derived / action / condition
    unit: str = ""
    precision: int = 0
    aggregation: str = "add"  # add / multiply / max / override / diminishing
    minimum: float | None = None
    maximum: float | None = None
    player_visible: bool = True
    source_kinds: tuple[str, ...] = ()
    note: str = ""


def _d(key: str, name: str, category: str, **kwargs) -> StatDefinition:
    return StatDefinition(key=key, name=name, category=category, **kwargs)


STAT_DEFINITIONS: dict[str, StatDefinition] = {
    defn.key: defn
    for defn in (
        # ---- 持久状态（存档里的当前事实，不是加成）----
        _d("mind.max", "心智上限", "persistent", unit="点", minimum=1),
        _d("lucidity.max", "清醒上限", "persistent", unit="点", minimum=1),
        _d("imagination.max", "想象上限", "persistent", unit="点", minimum=1),
        _d("imagination.regen_credit", "想象回流进度", "persistent", unit="点", precision=2),
        # ---- 派生属性（由基础值与有效来源得到，可只读查询）----
        _d("action.speed_scale", "行动速度倍率", "derived", unit="倍", precision=2,
           aggregation="multiply", source_kinds=("portent", "insight", "item"),
           note="征兆速度倍率叠乘并受上下限约束，限时物品另修正；行动耗时 = 基础耗时 / 该倍率"),
        _d("move.base_time", "移动基础耗时", "derived", unit="回合/格", precision=2,
           source_kinds=("rule",), note="一步的基础成本；蜂蜜等条件另结算"),
        _d("move.effective_time", "移动有效耗时", "derived", unit="回合/格", precision=2,
           source_kinds=("portent", "equipment")),
        _d("move.delay_penalty", "移动迟滞代价", "derived", unit="回合", precision=2,
           source_kinds=("portent", "equipment", "region"),
           note="积满 1 点才多花 1 回合，不直接减少每步耗时"),
        _d("attack.delay_penalty", "攻击迟滞代价", "derived", unit="回合", precision=2,
           source_kinds=("portent",)),
        _d("throw.range", "投掷距离", "derived", unit="格",
           source_kinds=("equipment",), aggregation="add",
           note="基础 6 格 + 投掷强化每级 +3 格"),
        _d("resilience", "战斗韧性", "derived", unit="倍率", precision=2,
           source_kinds=("run_option", "equipment", "portent"),
           note="仅是部分战斗来源的创伤倍率，不包含护甲/一次缓冲等其它防护"),
        _d("sight.radius", "视距", "derived", unit="格",
           source_kinds=("equipment", "insight", "portent", "memory", "region", "floor"),
           note="隔墙不可全知；黑烟/灰尘仍会截断或衰减视线"),
        _d("dissolution.bonus", "崩解收益", "derived", unit="%", minimum=0,
           source_kinds=("mind_tier",)),
        _d("loot.luck", "战利品幸度", "derived", unit="权重", precision=1,
           source_kinds=("run_option",), note="权重值，不等同掉率百分比"),
        _d("imagination.regen_rate", "想象自然回流", "derived", unit="点/回合", precision=2,
           source_kinds=("rule", "run_option", "hospital"), minimum=0,
           note="摇篮曲会暂停；留白线见底时另有额外回流"),
        # ---- 行动结果（取决于这次行动的上下文）----
        _d("melee.base_trauma", "近战基础创伤", "action", unit="点",
           source_kinds=("equipment", "rule"),
           note="无条件基础值；对具体目标的实际预览还要叠加目标条件"),
        _d("melee.base_time", "近战基础耗时", "action", unit="回合/次", precision=2,
           source_kinds=("equipment",)),
        _d("melee.effective_time", "近战有效耗时", "action", unit="回合/次", precision=2,
           source_kinds=("equipment", "portent")),
        # ---- 耐受与环境（docs §10 第四批；独特条件规则保留，不强行折算总抗性）----
        _d("portent.accumulation_factor", "征兆积累系数", "derived", unit="倍", precision=2,
           source_kinds=("memory",), aggregation="min", minimum=0, maximum=1,
           note="同类耐受取最高（负面积累降低 60%），不叠加成完全免疫"),
        _d("portent.effective_duration", "征兆新沾染时长", "derived", unit="回合",
           source_kinds=("memory", "hospital"),
           note="受耐受碎片缩短 50%、向上取整且至少 1 回合；一次性免疫会另消耗"),
        _d("environment.trauma", "环境即时创伤", "action", unit="点", minimum=0,
           source_kinds=("identity", "buffer", "rule"),
           note="按身份弱点与一次性火焰缓冲结算；不套用征兆积累耐受"),
        _d("identity.trauma_multiplier", "身份环境弱点", "derived", unit="倍率", precision=2,
           source_kinds=("identity",),
           note="只对该身份的对应环境通道生效，不冒充通用抗性"),
        _d("mind.loss_multiplier", "心智流失倍率", "derived", unit="倍率", precision=2,
           source_kinds=("portent",), aggregation="min",
           note="多个减半类征兆取最小倍率，对一切来源生效"),
        _d("mind.loss_blocked", "心智流失免疫", "condition", unit="",
           source_kinds=("portent",),
           note="镇静只拦环境来源，不拦异象战斗创伤；这是一次状态而非百分比抗性"),
        _d("lucidity.tier", "清醒档位", "derived", unit="档",
           source_kinds=("resource",)),
        _d("mind.tier", "心智档位", "derived", unit="档",
           source_kinds=("resource",)),
        # ---- 构想/篡改与一次性缓冲（docs §10 第五批）----
        _d("ability.cost_multiplier", "构想费用倍率", "derived", unit="倍", precision=2,
           source_kinds=("run_option", "equipment", "dream_type"),
           note="保留免费/最低值例外；倍率与固定修正顺序沿用现有结算"),
        _d("ability.cooldown_turns", "构想冷却", "action", unit="回合",
           source_kinds=("run_option", "insight"),
           note="按当前共用计算；思维润滑再 −1、最低 1 回合（最低值由 _scaled_ability_cooldown 保证，base=0 仍为 0）"),
        _d("tamper.pressure", "连续篡改压力", "persistent", unit="点", minimum=0,
           source_kinds=("tamper",)),
        _d("tamper.chaos_cost", "篡改最终混乱费用", "action", unit="点",
           source_kinds=("tamper",), aggregation="add",
           note="基础混乱 ×1.3 后加连续压力每点 +2；与预览使用同一报价函数"),
        _d("buffer.available", "一次性缓冲", "condition", unit="点",
           source_kinds=("equipment",), note="只抵下一次对应创伤，不恢复资源、不叠成无限盾"),
        # ---- 环境/失控派生（每项标明作用对象）----
        _d("physics.explosion_bonus", "爆炸增强", "derived", unit="点",
           source_kinds=("mind_tier",), note="作用于爆炸威力；不改变火焰传播"),
        _d("physics.fire_spread_bonus", "火焰蔓延", "derived", unit="点",
           source_kinds=("mind_tier",)),
        _d("physics.penetration_bonus", "穿透加成", "derived", unit="点",
           source_kinds=("lucidity_tier",)),
        _d("physics.solidity_penalty", "坚固度惩罚", "derived", unit="点",
           source_kinds=("lucidity_tier",)),
    )
}

# 已知但尚未接通真实结算的条目：只登记审查状态，不进入正式总览。
PENDING_STATS: dict[str, str] = {
    "unified.total_resistance": "统一总抗性：不存在跨伤害/费用/交易的总减免，继续按来源拆分",
    "tamper.final_chaos_cost": "篡改最终混乱费用：等第 8 节批量报价落地后接入",
}
