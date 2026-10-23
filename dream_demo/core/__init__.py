"""世界模拟层（原 ``dream_demo/core.py``）。

按职责拆分为子模块，本包对外导出与拆分前完全一致的公开名单：

- constants：常量与枚举（时间轴术语契约见下）
- entities：Cell / Entity / Item / WorldItem / WorldEvent / LayerSnapshot / ActionResult
- content：异象 / 物品 / 弹体 / 事件 / 洞察 / 层主题定义表
- vision：视野子系统（SightMixin 视线、glow 发光、cache 可见集合缓存）
- pathing：寻路子系统（PathMixin 玩家 A* 寻路、PursuitMixin 异象追踪、find_path 通用 A*）
- state：GameState（由 generation / doors / vision / pathing / portents / tempo /
  materials_sim / enemies / actions 九个 Mixin 组装）
"""

from .constants import (
    ACTION_COUNT_LIMIT,
    ANOMALY_REFRESH_INTERVAL,
    CREATURE_PORTENT_DAMAGE_PERIOD,
    ELEV_STEP,
    EXPOSED_ONLY_WALLS,
    GAS_DECAY_INTERVAL,
    GAS_MIN_FLOW,
    LIQ_DIV,
    LIQ_MIN_FLOW,
    LIQUID_ABSORB_INTERVAL,
    LIQUID_DECAY_INTERVAL,
    MIND_REGEN_INTERVAL,
    PORTENT_CONTACT_MIN,
    PROJECTILE_MAX_RANGE,
    REMOTE_OVERWRITE_INTERVAL,
    SIGHT_OBSCURE_MIN,
    ActionKind,
    Material,
)
from .content import (
    ABILITY_DEFINITIONS,
    ACCESSORY_SLOTS,
    ANOMALY_DEFINITIONS,
    EQUIPMENT_POOL,
    EQUIPMENT_SLOTS,
    EVENT_DEFINITIONS,
    INSIGHT_DEFINITIONS,
    ITEM_DEFINITIONS,
    LAYER_EVENT_IDS,
    LAYER_THEMES,
    MEMORY_FRAGMENT_EFFECTS,
    MEMORY_LIMIT,
    ORDINARY_ANOMALY_IDS,
    PROJECTILE_DEFINITIONS,
)
from .entities import (
    ActionResult,
    Cell,
    Entity,
    Item,
    LayerSnapshot,
    WorldEvent,
    WorldItem,
)
from .state import GameState
# 视野子系统（core/vision/）入口再导出：SightMixin 供组装/测试引用，
# glow 保留 `from dream_demo.core import glow` 这样的旧导入路径。
from .vision import SightMixin, glow
# 寻路子系统（core/pathing/）入口再导出：玩家寻路与异象寻路都收在这里。
from .pathing import PathMixin, PursuitMixin, find_path
from ..materials import (  # 原核心模块曾再导出的材料名（兼容旧导入路径）
    CONTAINER_KINDS,
    GAS_DEFINITIONS,
    LIQUID_DEFINITIONS,
    PORTENT_DEFINITIONS,
    TRANSPARENT_WALLS,
    WALL_DEFINITIONS,
    portent_def,
    wall_def,
    wall_pool_for_depth,
    wall_spawn_budget,
)
from ..mapgen import (  # 原核心模块曾再导出的地图生成名（兼容旧导入路径）
    MAP_FORMS,
    generate_elevation,
    generate_solid_mask,
    layer_dimensions,
    layer_form_for,
    normalize_map_form,
    place_doors,
)

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
