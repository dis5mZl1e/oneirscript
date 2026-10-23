"""主动构想（技能）定义：消耗想象力、按回合冷却。"""

# ---- 战斗构想数值分级（2026-10-22 平衡修复）----
# 12 条 `combat` 构想按「费用／冷却／输出预算」分四档；档位写进每条
# `combat.tier`，区间由 tests/test_balance_fix_constructs.py 校验：
#   T1 基础     cost 5–6  / cooldown 5–6   单体近战与打断，学习权重 2–3
#   T2 战术     cost 6–8  / cooldown 6–8   一次位移、弹体或控场，T1 的量级放大
#   T3 环境重击 cost 9–10 / cooldown 8–12  真实爆炸／地形产物，敌我共担
#   T4 领域     cost 12   / cooldown 12    半径 2–3 的常驻域或全场域效果
# 对照卡（无 combat 元数据、不参与 tier 校验）：repulse 8/8 与 static_arc
# 8/8 是同价位的两条旧战斗构想——前者用「多目标推 3 格」换伤害，后者用
# 「3 伤 + 迟缓 2」换单点强度；支配矩阵同样在 balance 测试里。

from __future__ import annotations

from typing import Any

LIBRARY_ABILITY_ROWS = (
    ('library.fold','折页',8,6,'把眼前折成一道窄缝：沿面朝方向挪出最多5格，墙会挡住折痕。'),
    ('library.bookmark','书签',6,4,'在脚下夹一枚书签；再次展开时回到这里，只认同一层的页码。落点被占据时书签留下。'),
    ('library.inkline','墨线',8,6,'向前划一道墨：8格内沿线异象的眼睛被蒙住2回合，墨线不过墙。'),
    ('library.erase','删划',12,8,'划去面前一处薄弱障碍：硬度不超过2，边界、机关、柜箱和任务设施不能删去。'),
    ('library.clamp','夹页',10,8,'把最近的异象夹在页间：5格内一个可见敌对异象2回合不能移动，仍可出手。'),
    ('library.margin','旁注',6,8,'沿面朝方向补出长 12、宽 3 的地形轮廓；只标开放/阻挡，不提供材料，可穿普通墙，遇边界停止。'),
)

ABILITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "spark": {
        "name": "火花", "cost": 8, "cooldown": 4,
        # ---- 内容扩展包 v1（2026-09-20）：8 新构想 + 12 地形改造构想见文件尾 ----
        "description": "在想象里划一根火柴：点燃相邻的可燃材料。",
    },
    "farsight": {
        "name": "望远", "cost": 6, "cooldown": 10,
        "description": "把视平线推向远处：视野 +4，持续 8 回合。",
    },
    "frost_touch": {
        "name": "冻凝", "cost": 6, "cooldown": 6,
        "description": "想象一场悄无声息的霜：冻结近旁 3 格内所有失控意识 3 回合。",
    },
    "smoke_veil": {
        "name": "烟幕", "cost": 6, "cooldown": 10,
        "description": "在可见空地选点：中心 30 点、四邻各 15 点黑烟（最多 90）；容量不足时减量。",
    },
    "wide_develop": {
        "name": "显影拓印", "cost": 12, "cooldown": 14,
        "description": "留下持续 6 回合的拓印：随移动每回合记录自身周围半径 8 的地形快照；站着不动不报新发现，也不揭示暗处的人和物。",
    },
    "slow_wave": {
        "name": "迟缓", "cost": 10, "cooldown": 12,
        "description": "在可见中心铺开半径 4、持续 6 回合的时缓区：区内所有生物移动耗时 +0.3，玩家也一样；离开即失效，多个时缓区不叠加。",
    },
    "develop": {
        "name": "冲印", "cost": 6, "cooldown": 6,
        "description": "选择 10 格内当前可见或已有地形快照的格子：记录其周围半径 5 的地形快照；不扫描人、物、液气与任务。",
    },
    "echo_pulse": {
        "name": "回响", "cost": 6, "cooldown": 8,
        "description": "留下持续 8 回合的声影：每回合基础声径 10，走到一格时记录该格及四邻的开放/阻挡轮廓；同时最多一枚，重施替换。",
    },
    "listen_realm": {
        "name": "听界", "cost": 5, "cooldown": 10,
        "description": "持续 3 回合：把实际传到你的声音临时标成发声格，只记该次声音的位置与时刻；不检测安静对象，也不照亮周围地形。起手自身产生 3 格声响。",
    },
    "repulse": {
        "name": "推斥", "cost": 8, "cooldown": 8,
        "description": "以可见中心半径 2 内的敌对异象为目标，沿径向推开最多 3 格并造成 2 点创伤；逐格检查实体、墙体与位移免疫，不追加撞墙伤害。",
    },
    "mirror_stance": {
        "name": "镜面", "cost": 8, "cooldown": 10,
        "description": "在身前立一面不存在的镜子：下一次指向你的打击被原路退回。",
    },
    "blur": {
        "name": "曝光", "cost": 15, "cooldown": 12,
        "description": "让所有看得见的异象过曝：视野内异象的视野减半 3 回合。",
    },
    # ---- 2026-09-18 火焰爆炸触发批次 ----
    "detonate": {
        "name": "引爆", "cost": 10, "cooldown": 8,
        "description": "明确选择视野内的可燃材料：当场触发真实点燃/爆炸，并提示可能接续的已知材料；不会擅自点燃最近的材料。",
    },
    "firewall": {
        "name": "火墙", "cost": 8, "cooldown": 6,
        "description": "在身前立起一排凭空燃烧的火墙（5 格），烧退追上来的影子。",
    },
    "flame_nova": {
        "name": "烈焰新星", "cost": 14, "cooldown": 10,
        "description": "想象自己在梦的中心点燃——火以你为圆心开花，半径三、威力三。花瓣落尽，你仍站在火里；爆炸与点燃敌我共担，注意自身清醒与灼烧风险。",
    },
}

# ---- 内容扩展包 v1（2026-09-20）：8 新构想 ----
ABILITY_DEFINITIONS.update({
    "short_circuit": {
        "name": "短路", "cost": 8, "cooldown": 8,
        "description": "明确选择视野内一个合法触发节点：显示将触发的已知接收端与效果；不自动选择最近的节点，也不绕过玩具回路的禁用。",
    },
    "rewire": {
        "name": "接线", "cost": 10, "cooldown": 12,
        "description": "分两步选择可见的合法触发源与接收端口：预览新连线、被替换的连线与已知影响后再提交；不自动拼最近两端，任一步取消都零消耗。",
    },
    "stasis": {
        "name": "凝滞", "cost": 12, "cooldown": 14,
        "description": "立即冻结自身 3 个世界回合（含施放回合）：免疫创伤与征兆，不能执行行动；仍可查看、取消、等待和保存。",
    },
    "vanish": {
        "name": "匿踪", "cost": 12, "cooldown": 18,
        "description": "6 回合内视觉隐蔽：异象看不见你，但仍会调查真实声音与最后目击点。移动、查看不结束；成功近战、发射或投掷后结束（环境构想不结束）。",
    },
    "flashback": {
        "name": "回闪", "cost": 12, "cooldown": 16,
        "description": "回到 3 回合前所在的那一格（若仍可通行）。",
    },
    "kindle": {
        "name": "火种", "cost": 6, "cooldown": 6,
        "description": "在面朝格及其四邻种下一圈火（十字 5 格），引燃可燃物与气体。",
    },
    "resonance": {
        "name": "共鸣", "cost": 9, "cooldown": 10,
        "description": "与一件携带意象共鸣：其效果 ×1.5，持续 8 回合。",
    },
    "nightmare_fuel": {
        "name": "梦魇燃料", "cost": 0, "cooldown": 24,
        "resource_costs": {"lucidity": 5},
        "description": "以 5 点清醒度为代价，回复想象力上限的 40%（四舍五入）。",
    },
})

ABILITY_DEFINITIONS.update({key:dict(name=name,cost=cost,cooldown=cd,
    description=prose,acquire_pool='library') for key,name,cost,cd,prose in LIBRARY_ABILITY_ROWS})

# ---- 内容扩展包 v1（2026-09-20）：12 地形改造构想（复用既有实装挂点）----
ABILITY_DEFINITIONS.update({
    "condense_dew": {
        "name": "凝露", "cost": 4, "cooldown": 5,
        "description": "在可见落点及四邻凝水：中心 20 点、四邻各 10 点（最多 60）；容量不足时减量，不挤掉已有液气。",
    },
    "sow_green": {
        "name": "播绿", "cost": 8, "cooldown": 10,
        "description": "以可见格为中心、曼哈顿半径 3 播种：内圈半径 1 为高丛，其余为低草，最多 25 格；复用既有植物，不生成稀有奖励植物。",
    },
    "wax_seal": {
        "name": "蜡封", "cost": 6, "cooldown": 8,
        "description": "把脚下或相邻一格封成蜡化记忆墙（完整度 45，可徒手破坏）。",
    },
    "draw_liquid": {
        "name": "汲引", "cost": 6, "cooldown": 8,
        "description": "选定液体：汲取其同种四邻连通块中当前可见的部分，每次最多 96 点，固定回复 2 点想象力；不跨未知格，也不碰任务液体。",
    },
    "ice_bridge": {
        "name": "冰桥", "cost": 10, "cooldown": 10,
        "description": "选可见液体落点，沿方向冻出最长 8、宽 3 的冰桥：每格最多 8 点转入冻层、剩余保留，融化按真实存量；普通墙与视野边缘截断。",
    },
    "transpire": {
        "name": "蒸腾", "cost": 10, "cooldown": 10,
        "description": "选定液体可见同种连通块，持续 3 回合蒸腾：每格每回合最多 8、总量最多 96，按材料表比例生成气体；同格同回合最多一次相变。",
    },
    "dissolve_wall": {
        "name": "融蚀", "cost": 12, "cooldown": 12,
        "description": "溶解相邻一面硬度 ≤6 的墙；硬墙（致密/梦魇岩）无效。",
    },
    "raise_terrain": {
        "name": "隆起", "cost": 14, "cooldown": 20,
        "description": "抬升目标 5×5 的地势（+1 档）：液体将流走，造出高地。",
    },
    "sink_terrain": {
        "name": "陷落", "cost": 14, "cooldown": 20,
        "description": "使目标 5×5 地势下陷（−1 档）：造洼地引液体、挖陷阱坑。",
    },
    "collapse": {
        "name": "崩落", "cost": 12, "cooldown": 14,
        "description": "以可见目标为中心，沿方向选最长 5 格的走廊：破坏两侧完整度 ≤40 的合法普通墙，最多生成 3 格碎屑堆；没有合法墙源不能提交，任务通路、占用格与边界受保护。",
    },
    "conjure_wall": {
        "name": "凝聚", "cost": 12, "cooldown": 14,
        "description": "以可见中心沿方向垂线凝聚最多 3 格臆造聚合墙（可推动、可破坏）；占用、任务设施与保护格先检查。",
    },
    "rewrite_corner": {
        "name": "重写一隅", "cost": 25, "cooldown": 30,
        "description": "以目标格为中心 7×7 的地形被梦境当场重写——可能把好事改坏。",
    },
})

# ---- 内容扩展包 v2（2026-10-11）：10 条，全部复用既有结算原语 ----
ABILITY_DEFINITIONS.update({
    "ice_chain": {
        "name": "急冻链", "cost": 10, "cooldown": 8,
        "description": "霜顺着视线蔓延：视野内最近的 5 个失控意识被冻结 2 回合。",
    },
    "static_arc": {
        "name": "静电弧", "cost": 8, "cooldown": 8,
        "description": "选择视野内敌对异象或合法导电落点：命中异象造成 3 点创伤并迟缓 2 回合；命中导电介质则沿真实四邻连通区充能，不越绝缘、断流也阻断，自己与稳定意识同样危险。",
    },
    "ink_doodle": {
        "name": "涂鸦", "cost": 6, "cooldown": 8,
        "description": "以可见格为中心，把 5×5 内的合法地面涂成真实书页地（最多 25 格）：不点火，也不改任务设施、保护地板或占用格。",
    },
    "blink": {
        "name": "闪现", "cost": 9, "cooldown": 8,
        "description": "明确选择视野内 8 格以内的合法空地：预览落点、危险与路径；取消或目标失效零消耗，不自动选择最近空地。",
    },
    "moth_dust": {
        "name": "遗忘喷剂", "cost": 8, "cooldown": 12,
        "description": "在可见目标格喷出半径 3、持续 4 回合的遗忘区：区内未直接看见你的敌对异象清除目击记忆并降一档警戒；每实例每施放每敌最多触发一次。",
    },
    "deep_breath": {
        "name": "深呼吸", "cost": 5, "cooldown": 12,
        "description": "在梦里做一次真正的深呼吸：回复 6 点清醒度。",
    },
    "calm_incense": {
        "name": "安神香", "cost": 12, "cooldown": 14,
        "description": "点起一支不存在的香：清除你身上全部负面征兆，并镇静 3 回合。",
    },
    "purge_wind": {
        "name": "净化风", "cost": 7, "cooldown": 8,
        "description": "想象一阵穿过梦境的风：视野内所有气体被一扫而空。",
    },
    "pixel_surge": {
        "name": "像素拆解", "cost": 8, "cooldown": 10,
        "description": "把视野内一面千禧园的装饰墙拆成色块，回收 8 点想象力（结构墙除外）。",
    },
    "mute_protocol": {
        "name": "静默协议", "cost": 8, "cooldown": 12,
        "description": "10 回合内自身格脚步与普通道具的基础声径封顶 1，之后仍受环境放大；不吞远端回响、诱饵、主动诱引与爆炸。",
    },
})

for _key, _description in {
    'spark': '在视野内指向格（否则面朝格）留下可见火种，2 回合后点燃真实材料；火焰与爆炸敌我共担。',
    'echo_pulse': '生成沿面朝方向逐回合移动、遇墙折返的声影，持续 8 回合；每回合基础声径 10，吸引附近异象调查，并记下经过格及四邻的开放／阻挡轮廓。',
    'library.erase': '向面朝方向划出最多 5 格墨痕，持续 4 回合；每回合侵蚀合法墙体 20 完整度，边界、机关、柜箱与任务设施受保护。',
    'mirror_stance': '在面朝相邻空格立起有朝向的镜面，持续 6 回合，按镜面法线反射实际投射物；返程弹体也有危险。',
    'wide_develop': '留下持续 6 回合的拓印，随移动每回合记录自身周围半径 8 的地形快照；站着不动不报新发现，也不揭示暗处的人和物。',
    'draw_liquid': '选定液体：汲取其同种四邻连通块中当前可见的部分，每次最多 96 点，固定回复 2 点想象力；不跨未知格，也不碰任务液体。',
    'transpire': '选定液体可见同种连通块，持续 3 回合蒸腾：每格每回合最多 8、总量最多 96，按材料表比例生成气体；同格同回合最多一次相变。',
    'ice_bridge': '选可见液体落点，沿方向冻出最长 8、宽 3 的冰桥：每格最多 8 点转入冻层、剩余保留，融化按真实存量；普通墙与视野边缘截断。',
    'condense_dew': '在可见落点及四邻凝水：中心 20 点、四邻各 10 点（最多 60）；容量不足时减量，不挤掉已有液气。',
    'sow_green': '以可见格为中心、曼哈顿半径 3 播种：内圈半径 1 为高丛，其余为低草，最多 25 格；复用既有植物，不生成稀有奖励植物。',
    'wax_seal': '在视野内指向空地（否则面朝格）凝成蜡化记忆墙；不能覆盖生物、物品、机关或任务设施。',
    'dissolve_wall': '融蚀视野内指向墙体（否则面朝格），硬度不超过 6；致密墙、梦魇岩、边界和任务设施受保护，并触发真实材料后果。',
    'raise_terrain': '以视野内指向格（否则面朝格）为中心抬升 5×5 地势，驱动真实液体流动；任务设施与机关受保护。',
    'sink_terrain': '以视野内指向格（否则面朝格）为中心压低 5×5 地势，形成汇流洼地；任务设施与机关受保护。',
    'collapse': '以可见目标为中心，沿方向选最长 5 格的走廊：破坏两侧完整度 ≤40 的合法普通墙，最多生成 3 格碎屑堆；没有合法墙源不能提交，任务通路、占用格与边界受保护。',
    'conjure_wall': '以可见中心沿方向垂线凝聚最多 3 格臆造聚合墙（可推动、可破坏）；占用、任务设施与保护格先检查。',
    'rewrite_corner': '以视野内指向格（否则面朝格）为中心重写 7×7 地形；生物、任务设施和机关受保护，结果可能不利。',
}.items():
    ABILITY_DEFINITIONS[_key]['description'] = _description

# ---- 内容扩展包 v3（2026-10-20，§13）：12 个战斗构想 ----
# `combat` 元数据是瞄准事务与学习权重的唯一口径；这些条目绝不进入
# 书库专属池，也不在开局自动习得。
ABILITY_DEFINITIONS.update({
    "combat.beat_cut": {
        "name": "截拍", "cost": 6, "cooldown": 6,
        "description": "对相邻的一个异象执行一次当前近战；若它正在蓄势，打断这次蓄势并令其停顿 1 回合。没有可打断动作时仍可当作普通近战挥出。",
        "combat": {"form": "melee", "targeting": "single", "range": 1,
                   "sound": 3, "learn_group": "进阶战术", "weight": 2, "tier": 1},
    },
    "combat.cross_step": {
        "name": "借位", "cost": 7, "cooldown": 7,
        "description": "对相邻的一个异象执行一次当前近战，随后落进一个同时贴近原站位与目标的合法空格，最多移动 1 格。没有合法落点时不能出手。",
        "combat": {"form": "melee", "targeting": "single", "range": 1,
                   "sound": 3, "learn_group": "进阶战术", "weight": 2, "tier": 2},
    },
    "combat.arc_slash": {
        "name": "横切", "cost": 8, "cooldown": 8,
        "description": "扫过面朝方向与两侧相邻的三格；每个异象只承受一次当前近战基础伤害的 70%（向上取整，至少 1）。",
        "combat": {"form": "melee", "targeting": "arc", "range": 1,
                   "sound": 3, "learn_group": "基础战斗", "weight": 3, "tier": 2},
    },
    "combat.refracted_bolt": {
        "name": "折光矢", "cost": 7, "cooldown": 6,
        "description": "射出一支真实弹体，路径总长 12：命中首个实体造成 3 点创伤；可在普通墙面几何折返一次，也遵循构想镜面的反射，整条路径最多反射两次。返程会伤到自己。",
        "combat": {"form": "launch", "range": 12,
                   "sound": 3, "learn_group": "基础战斗", "weight": 3, "tier": 2},
    },
    "combat.piercing_needle": {
        "name": "穿念针", "cost": 8, "cooldown": 6,
        "description": "射出一根细针，路径总长 12：最多穿过 3 个实体，创伤依次为 3／2／1；可穿透硬度×厚度合计不超过 4 的普通薄墙并削去 20 完整度，任务、边界与抗弹墙仍会挡下。",
        "combat": {"form": "launch", "range": 12,
                   "sound": 3, "learn_group": "进阶战术", "weight": 2, "tier": 2},
    },
    "combat.delayed_shell": {
        "name": "迟响弹", "cost": 9, "cooldown": 8,
        "description": "朝视野内最远 10 格的落点投出一枚虚构弹体；落地留下可见倒计时弹，离手后 2 个真实回合引爆（半径 2、威力 3，敌我共担）。同层最多保留 2 枚未爆弹。",
        "combat": {"form": "throw", "range": 10, "sound": 2, "landing_sound": 4,
                   "learn_group": "较稀有环境战斗", "weight": 1, "tier": 3},
    },
    "combat.shadow_pin": {
        "name": "钉影枪", "cost": 8, "cooldown": 7,
        "description": "朝最远 10 格射出钉影：首个实体受 2 点创伤；若沿实际入射方向其后一格是合法实墙，则驻足 3 回合，否则迟缓 2 回合。",
        "combat": {"form": "launch", "range": 10,
                   "sound": 3, "learn_group": "进阶战术", "weight": 2, "tier": 2},
    },
    "combat.tow_hook": {
        "name": "牵引钩", "cost": 6, "cooldown": 7,
        "description": "朝最远 8 格抛出钩索：命中可移动的敌对异象时，沿实际飞行路径把它逆向拉近最多 3 格，停在玩家相邻格之前；无直接伤害。没有目标也可合法释放。",
        "combat": {"form": "launch", "range": 8,
                   "sound": 3, "learn_group": "基础战斗", "weight": 3, "tier": 2},
    },
    "combat.arc_orb": {
        "name": "雷珠", "cost": 10, "cooldown": 10,
        "description": "把雷珠投到最远 8 格：实际落点生成 16 点水、四邻各 6 点（最多 40 点），随后对相连的导电介质充能，沿用真实电场规则；没有额外爆炸伤害。",
        "combat": {"form": "throw", "range": 8, "sound": 2, "landing_sound": 4,
                   "learn_group": "较稀有环境战斗", "weight": 1, "tier": 3},
    },
    "combat.fault_ring": {
        "name": "裂地环", "cost": 12, "cooldown": 12,
        "description": "以自身为中心，作用切比雪夫距离恰好为 3 的外环：合法墙体完整度 −25，开放地面降低一档，环上生物受 2 点创伤并被径向推开 1 格；中心不受这次冲击。",
        "combat": {"form": "area", "shape": "ring3", "range": 3,
                   "sound": 8, "learn_group": "进阶战术", "weight": 2, "tier": 4},
    },
    "combat.paper_blades": {
        "name": "纸刃旋流", "cost": 12, "cooldown": 12,
        "description": "在施放位置立起半径 2 的固定刃环，持续 4 回合：每个真实回合结束时环上生物受 2 点创伤，同实例每回合最多一次；自己也一样，重施会替换旧刃环。",
        "combat": {"form": "area", "shape": "ring2", "range": 2,
                   "sound": 4, "learn_group": "较稀有环境战斗", "weight": 1, "tier": 4},
    },
    "combat.backdraft_screen": {
        "name": "逆风幕", "cost": 10, "cooldown": 12,
        "description": "从面朝格起立起长 6、宽 5 的风幕，持续 4 回合：气体每回合沿远离玩家的方向移动一格；首个穿过风幕的真实弹体剩余射程 −2，投掷体按实际提前落地。自身弹体同样受影响。",
        "combat": {"form": "area", "shape": "screen", "range": 6,
                   "sound": 0, "learn_group": "进阶战术", "weight": 2, "tier": 3},
    },
})
