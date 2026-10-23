"""装备（手中意象/衣着/依附物）"""

from __future__ import annotations

from typing import Any

ITEMS = {
    # Small alternatives for the existing typed readings; no new effect opcodes.
    "paper_handle_letterknife": {
        "name": "纸柄拆信刀", "category": "携带意象", "slot": "手中意象",
        "grammar_kind": "weapon", "rarity": "少见", "color": "#c4b997",
        "effect": "swift_strike", "power": 1, "melee": {"damage": 1, "time": 1.1},
        "description": "纸柄裂缝里露出旧信笺。刀尖停在封口，像是在等里面的人醒来。",
        "effect_description": "近战创伤增量 1，基础出手耗时 1.1；占四格。“的”借出刀锋，“地”借出节拍，使关联攻击耗时减少 0.1，不额外借出刀锋。",
    },
    "frayed_sleeve": {
        "name": "磨薄的袖套", "category": "携带意象", "slot": "自我表层",
        "grammar_kind": "clothing", "rarity": "常见", "color": "#a6b4b4",
        "effect": "swift_strike", "power": 1,
        "description": "一只磨得透光的袖套。抬手时，布口比手腕先动半拍。",
        "effect_description": "占四格；持续穿着时，攻击耗时减少 0.1。“的”或“地”关联攻击时，只借出本句节拍；同一件的持续效果不重复计算。",
    },
    "broken_tooth_thimble": {
        "name": "断齿顶针", "category": "携带意象", "slot": "依附物",
        "grammar_kind": "accessory", "rarity": "常见", "color": "#b3bac7",
        "effect": "repair_up", "power": 20,
        "description": "顶针缺了一齿，凹槽里卡着蓝线。戴上后，指尖总想把断处拢到一起。",
        "effect_description": "占两格；持续佩戴时修缮量增加 20。“地”关联修缮时，只增加本次修缮量，仍需消耗实际修缮工具，不增加墙体完整度上限。",
    },
    "ember_crayon": {
        "name": "留火的蜡笔", "category": "携带意象", "slot": "惯用物",
        "grammar_kind": "tool", "rarity": "少见", "color": "#d39d76",
        "effect": "fire_affinity", "power": 1,
        "description": "纸套烫得发软，蜡芯却没有燃烧。写到句末，纸边才冒出一点焦味。",
        "effect_description": "占五格；持续使用时点燃强度增加 1。“地”关联发射时，命中后尝试点燃已有燃料，成功另付 1 点想象力，点燃反馈冷却 6 回合。",
    },
    "carbon_copy_knife": {
        "name": "复写刻刀", "category": "携带意象", "slot": "手中意象", "rarity": "少见",
        "color": "#a8a0bc", "effect": "weapon_damage", "power": 3,
        "melee": {"time": 1.1},
        "description": "沿旧刻痕再划一遍：近战创伤 +3，基础攻击耗时 1.1。稳妥而略显迟缓。",
    },
    # ---- 内容扩展包 v1（2026-09-20）：16 件新武器装备 ----
    # 新 effect（liquid_ward/shock_aura/measure/wire_safe/repair_up/wall_sense/
    # erase_strike/sleep_strike/ignite_strike/unlock_fire）的结算接线随后续批次；
    # 复用既有 effect（weapon_damage/swift_strike/dual_armor/coin_bonus）的直接生效。
    # ---- 梦中梦·门之回廊独特物品（2026-09-21）----
    "door_hinge": {
        # 2026-10-22 倒挂修复：稀有·深层独特件原为视野 +1，弱于 T1 夜灯电池
        # （+2）与 T2 虚空吊坠（+3）。升为 +4，独占视野线顶点。
        "name": "门枢齿轮", "category": "携带意象", "slot": "惯用物", "rarity": "稀有", "color": "#b0a060",
        "description": "从圣所门轴上卸下的齿轮：握着它，门开得格外顺滑（视野 +4）。",
        "effect": "vision_up", "power": 4,
    },
    "echo_ring": {
        "name": "无门之环", "category": "携带意象", "slot": "依附物", "rarity": "非常稀有", "color": "#c8d8e8",
        # 2026-10-07 档位平衡：+2 比 T1 磨亮的硬币（+3）还弱，非常稀有件
        # 反向垫底；升为 +4。
        "description": "没有门框的环。戴着它，每一次崩解都推得更深（崩解推进 +4）。",
        "effect": "coin_bonus", "power": 4,
    },
    "corridor_candle": {
        "name": "回廊烛台", "category": "易逝物", "rarity": "稀有", "color": "#f0e2c0",
        # 2026-10-22 倒挂修复：稀有独特件原为 fireburst 4 且可叠 2 份，
        # 单份威力不如 T1 投掷物、叠份又压过独特定位。改为 7 / 不叠放。
        "description": "回廊里唯一的光。掷出去，炸成一圈更旺的火。", "effect": "fireburst",
        "power": 7, "max_stack": 1,
    },
    "rusty_boxcutter": {
        "name": "生锈的美工刀", "category": "携带意象", "slot": "手中意象", "rarity": "常见", "color": "#b07040",
        "description": "推出来回拉的钝刀，胜在随手可得。", "effect": "weapon_damage", "power": 1,
    },
    "binder_clip_launcher": {
        "name": "长尾夹发射器", "category": "携带意象", "slot": "手中意象", "rarity": "少见", "color": "#8ab8d0",
        "description": "绷紧的金属夹带着轻微穿透射出去。", "effect": "unlock_fire",
        "power": 2, "penetration": 1,
    },
    "voice_recorder_pen": {
        "name": "录音笔", "category": "携带意象", "slot": "手中意象", "rarity": "少见", "color": "#9090b0",
        "description": "发射即广播：弹着点的声波把异象引向别处。", "effect": "unlock_fire",
        "power": 1, "projectile_template": "声波弹体",
    },
    "focusing_lens": {
        "name": "裂开的放大镜", "category": "携带意象", "slot": "手中意象", "rarity": "稀有", "color": "#e0d080",
        "description": "聚成一线的光：命中点燃目标格的可燃物。", "effect": "ignite_strike", "power": 2,
    },
    "dream_tapir_flute": {
        "name": "梦貘鼻烟壶", "category": "携带意象", "slot": "手中意象", "rarity": "稀有", "color": "#c090d0",
        "description": "近战创伤 +1；命中两成概率让对方直接睡去。", "effect": "sleep_strike", "power": 2,
        "melee": {"damage": 1},
    },
    "pendulum_blade": {
        "name": "节拍摆刃", "category": "携带意象", "slot": "手中意象", "rarity": "非常稀有", "color": "#70c8c0",
        "description": "跟着节拍出手：近战创伤 +2，攻击基础耗时 −0.3。", "effect": "swift_strike",
        "melee": {"damage": 2},
        "power": 3,
    },
    "null_pen": {
        "name": "没水的笔", "category": "携带意象", "slot": "手中意象", "rarity": "非常稀有", "color": "#5a5a7a",
        "description": "近战创伤 +2；命中两成概率删去对方最近获得的一条征兆。", "effect": "erase_strike", "power": 3,
        "melee": {"damage": 2},
    },
    "waxed_raincoat": {
        "name": "打蜡的雨衣", "category": "携带意象", "slot": "自我表层", "rarity": "少见", "color": "#d0c060",
        "description": "液体接触的负面征兆对你减半。", "effect": "liquid_ward", "power": 1,
    },
    "lead_lined_apron": {
        "name": "铅衬里的围裙", "category": "携带意象", "slot": "自我表层", "rarity": "稀有", "color": "#808088",
        # 2026-10-07：描述对齐实现——dual_armor 的心智与清醒减免都取 power
        # （见 lightless_cloak 注释），旧描述的「清醒 −1」是虚标。T2 双护甲档位 −2/−2。
        # 2026-10-22：删掉「代价是移动略沉」——那条惩罚读 weapon_weight，
        # 而全库没有物品提供它（读取点已移除），承诺从未生效。
        "description": "心智创伤 −2、清醒创伤 −2。", "effect": "dual_armor",
        "power": 2,
    },
    "static_poncho": {
        "name": "静电披风", "category": "携带意象", "slot": "自我表层", "rarity": "稀有", "color": "#60c8e0",
        "description": "受击时向相邻的攻击者反打一记传导冲击。", "effect": "shock_aura", "power": 1,
    },
    "metronome_pendant": {
        "name": "停摆的节拍器", "category": "携带意象", "slot": "依附物", "rarity": "少见", "color": "#c8a860",
        "description": "戴着它，攻击耗时 −0.1。", "effect": "swift_strike", "power": 1,
    },
    "surveyor_compass": {
        "name": "刻度磨损的指南针", "category": "携带意象", "slot": "依附物", "rarity": "常见", "color": "#a89070",
        "description": "悬停读数额外显示到目标的最短步数。", "effect": "measure", "power": 1,
    },
    "lucky_clover": {
        "name": "压扁的四叶草", "category": "携带意象", "slot": "依附物", "rarity": "稀有", "color": "#70c060",
        # 2026-10-07 档位平衡：+3 与 T1 磨亮的硬币同值，升为 +4。
        "description": "崩解度获取 +4，越攒越厚。", "effect": "coin_bonus", "power": 4,
    },
    "insulated_gloves": {
        # 2026-10-07：category 由「惯用物」对齐为「携带意象」：装备型效果需要
        # 先能穿上才生效（同多功能军刀/听诊器）。
        "name": "绝缘手套", "category": "携带意象", "slot": "惯用物", "rarity": "少见", "color": "#d0b060",
        "description": "徒手操作机关与电线不再触发反噬。", "effect": "wire_safe", "power": 1,
    },
    "multitool_knife": {
        # 2026-10-07：category 由「惯用物」对齐为「携带意象」（同螺丝刀/深念凿子）。
        # 旧类别会被 toggle_equip_item 路由到「使用」，装备型效果永远挂不上。
        "name": "多功能军刀", "category": "携带意象", "slot": "惯用物", "rarity": "少见", "color": "#a0a8b0",
        # 2026-10-07 档位平衡：+40 与 T1 螺丝刀同值，升为 +50（修缮线 40→50→60）。
        "description": "修缮 +50：装备更耐用。", "effect": "repair_up", "power": 50,
    },
    "stethoscope": {
        # 2026-10-07：category 由「惯用物」对齐为「携带意象」：装备型效果需要
        # 先能穿上才生效（同上）。
        "name": "听诊器", "category": "携带意象", "slot": "惯用物", "rarity": "稀有", "color": "#c0c8d0",
        "description": "隔墙一格也能听到异象的轮廓。", "effect": "wall_sense", "power": 1,
    },

    "echo_emitter": {
        "name": "小型回声发射器", "category": "携带意象", "slot": "手中意象",
        "rarity": "常见",
        "description": "把一句未说完的话压成直线弹体射出去。",
        "color": "bright_cyan", "effect": "unlock_fire", "power": 1, "projectile_template": "直线弹体",
        "fire": {"time": 1.0, "damage": 1},
    },
    "line_projector": {
        "name": "折线投影仪", "category": "携带意象", "slot": "手中意象",
        "rarity": "少见",
        "description": "弹体会记住穿过第一层阻挡后的方向。", "color": "bright_cyan",
        "effect": "unlock_fire", "power": 1, "penetration": 3, "push": 1, "projectile_template": "穿页弹体",
    },
    "headphone_coil": {
        "name": "旧耳机的线圈", "category": "携带意象", "slot": "依附物",
        "rarity": "少见",
        "description": "让远处的声音先抵达你。", "color": "bright_blue",
        # 2026-10-22 实装：quiet_steps 现在有消费端（enemies._step_noise_reduction_for）。
        "effect": "quiet_steps", "power": 1,
    },
    "unfinished_editor": {
        "name": "未完成的批注", "category": "携带意象", "slot": "自我表层",
        "rarity": "少见",
        "description": "每次读错一个词，就多看见一条路。", "color": "white",
        # 2026-10-22 实装：mind_guard 现在有消费端（portents._lose_mind）。
        "effect": "mind_guard", "power": 1,
    },
    "quiet_ticket": {
        "name": "没有日期的车票", "category": "携带意象", "slot": "依附物",
        "rarity": "少见",
        "description": "让一次追踪暂时忘记目的地。", "color": "bright_blue", "effect": "quiet_steps",
        # 2026-10-22 实装：同 headphone_coil（enemies._step_noise_reduction_for）。
        "power": 1,
    },
    "bent_hook": {
        "name": "弯曲的挂钩", "category": "携带意象", "slot": "依附物",
        "rarity": "常见",
        "description": "把一件易逝物挂在梦的墙上，让打击先落在它身上。", "color": "bright_green",
        "effect": "hang",
    },
    "single_earphone": {
        "name": "单边耳机", "category": "携带意象", "slot": "自我表层",
        "rarity": "常见",
        "description": "只有一边的声音，让你更难被声音找到；代价是听不见脚下的提示。", "color": "bright_magenta",
        "effect": "noise_cut",
    },
    "broken_watch": {
        "name": "破损的怀表", "category": "携带意象", "slot": "依附物",
        "rarity": "常见",
        "description": "指针停在某一回合，附近的梦因此走得慢一些。", "color": "bright_yellow",
        "effect": "slow_aura",
    },
    "lighthouse_lens": {
        "name": "灯塔透镜", "category": "携带意象", "slot": "依附物",
        "rarity": "稀有",
        "description": "下潜后的最初几回合，它仍替你照亮远处。", "color": "bright_white",
        "effect": "lamp",
    },
    "sketch_gloves": {
        "name": "速写手套", "category": "携带意象", "slot": "手中意象", "rarity": "少见",
        # 伤害由近战规格提供，swift 2 使基础耗时降低 0.2。
        "description": "指尖涂着防滑的石墨粉。近战创伤 +1，攻击基础耗时 −0.2。",
        "melee": {"damage": 1},
        "color": "#d8c8a0", "effect": "swift_strike", "power": 2,
    },
    "gravestone_wristband": {
        "name": "碑文护腕", "category": "携带意象", "slot": "依附物·一", "rarity": "稀有",
        "description": "刻着一整圈墓志铭的旧表带：读得越熟，越分不清自己是不是碑里的人。心智创伤与清醒创伤各 −1。",
        "color": "#9ab8ff", "effect": "dual_armor", "power": 1,
    },
    "hourglass_pendant": {
        "name": "逆行的沙漏", "category": "携带意象", "slot": "依附物·二", "rarity": "稀有",
        "description": "沙子往上落。戴它的人总觉得自己还有更多时间——清醒创伤 −2。",
        "color": "#e8d8a0", "effect": "lucidity_armor", "power": 2,
    },
    "high_pressure_pump": {
        "name": "高压水泵", "category": "携带意象", "slot": "依附物·一", "rarity": "稀有",
        "description": "给喷水枪加装的第二级压水膛：每次喷射的材料量 +6。",
        "color": "bright_cyan", "effect": "spray_boost", "power": 1,
    },
    "air_concentrator": {
        "name": "聚气喷嘴", "category": "携带意象", "slot": "依附物·二", "rarity": "稀有",
        "description": "把散风收束成一道风柱：吹风机每次喷射的材料量 +6。",
        "color": "bright_magenta", "effect": "spray_boost", "power": 1,
    },
    "water_gun": {
        "name": "喷水枪", "category": "携带意象", "slot": "手中意象", "rarity": "稀有",
        "description": "枪管里晃着半管来路不明的水。发射液态记忆：淋在墙上淌成滩，浇在意识体上留一层。有装液体的容器就抽容器，没有就只能喷少量清水；每次发射耗费一点想象力。",
        "color": "bright_cyan", "effect": "spray_liquid",
        "spray": {"medium": "liquid", "amount": 12, "builtin_kind": "水", "builtin_amount": 6, "cost": 2},
    },
    "hair_dryer": {
        "name": "吹风机", "category": "携带意象", "slot": "手中意象", "rarity": "稀有",
        "description": "热风档早坏了，冷风档吹出来的都是别人的梦。发射弥散印象：喷在墙上凝成雾，罩在意识体上散成一层。有装气的容器就抽容器，没有就只能吹少量水蒸气；每次发射耗费一点想象力。",
        "color": "bright_magenta", "effect": "spray_gas",
        "spray": {"medium": "gas", "amount": 12, "builtin_kind": "水蒸气", "builtin_amount": 6, "cost": 2},
    },
    "nail_gun": {
        "name": "钉枪", "category": "携带意象", "slot": "手中意象", "rarity": "少见",
        "description": "木工房里顺出来的大家伙。钉一发要顶两个回合的力，但钉进去了就拔不出来——穿透力极强，创伤沉重。",
        "color": "bright_yellow", "effect": "unlock_fire", "power": 1,
        "projectile_template": "直线弹体",
        "fire": {"time": 2.0, "damage": 2, "penetration": 2, "push": 0},
        # 近战规格（2026-09-22）：手持武器定义 "melee" 时，bump 攻击读它的
        # damage（伤害加成）/ segments（段数）/ time（基础耗时）。
        "melee": {"damage": 1},
    },
    "sonic_whistle": {
        "name": "音爆哨", "category": "携带意象", "slot": "手中意象", "rarity": "少见",
        "description": "吹不响的哨子改装的。半回合一声爆鸣，几乎造不成创伤，却能把命中处的对象掀出去，声响还会引来半层梦的注意。",
        "color": "bright_white", "effect": "unlock_fire", "power": 1,
        "projectile_template": "直线弹体",
        "fire": {"time": 0.5, "damage": 0, "penetration": 1, "push": 3, "pulse": 7},
    },
    "dart_gun": {
        "name": "冻凝镖枪", "category": "携带意象", "slot": "手中意象", "rarity": "稀有",
        "description": "镖尖凝着一种醒不过来的凉意。命中即冻：被射中的异象会慢慢结上一层霜，动作与出手都迟滞下来。",
        # 2026-10-22 倒挂修复：稀有件原 power 1，与常见发射件同值；升为 3。
        "color": "#9ad1ff", "effect": "unlock_fire", "power": 3,
        "projectile_template": "直线弹体",
        "fire": {"time": 1.0, "damage": 1, "penetration": 1, "push": 0, "portent": ["frozen", 3]},
    },
    "ignite_gloves": {
        "name": "点火手套", "category": "携带意象", "slot": "惯用物", "rarity": "稀有",
        "description": "指节内侧嵌着燧石：近战与弹体命中后，目标所在格被点燃。",
        "color": "#ff8c42", "effect": "ignite_strike", "power": 1,
    },
    "phoenix_robe": {
        "name": "凤凰羽衣", "category": "携带意象", "slot": "自我表层", "rarity": "稀有",
        "description": "织物里衬着不肯熄的暖意：站在火焰里不再受到清醒创伤。",
        "color": "#ff6b4a", "effect": "fire_ward", "power": 1,
    },
    "blast_ring": {
        "name": "爆破扳指", "category": "携带意象", "slot": "依附物", "rarity": "稀有",
        "description": "内侧刻着膨胀曲线的戒指：你投掷的爆炸物与烈焰新星的半径 +1。",
        "color": "#ff4fd8", "effect": "blast_radius", "power": 1,
    },
    "arsonist_watch": {
        "name": "纵火者怀表", "category": "携带意象", "slot": "依附物", "rarity": "少见",
        "description": "表盘上本该是数字的位置刻着一圈燃点。指针指向哪里，哪里的火就烧得更任性（点燃强度 +1）。",
        "color": "#e07038", "effect": "fire_affinity", "power": 1,
    },
    "pen_sharp": {
        "name": "削尖的钢笔", "category": "携带意象", "slot": "手中意象",
        "rarity": "常见",
        "description": "笔尖磨得锋利，写出的每个字都带刃。近战与弹体伤害 +1。",
        "color": "bright_cyan", "effect": "weapon_damage", "power": 1,
    },
    "heavy_stapler": {
        "name": "沉重的订书机", "category": "携带意象", "slot": "手中意象",
        "rarity": "少见",
        # 2026-10-07 档位平衡：+3 常见件与 T3 非常稀有件（初啼之牙）同值，
        # 压平了整条伤害线。降为 +2 并升到少见，T1 伤害线收敛为 +1/+2。
        # 2026-10-22：「移动额外耗时 0.2」的代价读 weapon_weight，而全库没有
        # 物品提供它（悬空读取已从 movement 移除）；power_secondary 也无消费端，
        # 一并删除。描述只保留真实生效的「伤害 +2」，不再承诺不存在的代价。
        "description": "一击钉穿三层梦。伤害 +2。",
        "color": "bright_cyan", "effect": "weapon_damage", "power": 2,
    },
    "rift_shears": {
        "name": "裂隙剪", "category": "携带意象", "slot": "手中意象", "rarity": "少见",
        "description": "双刃错开半拍落下的剪刀——一次挥动是两道口子（近战两段）。",
        "color": "#c8a0d0", "melee": {"segments": 2},
    },
    "patched_pajamas": {
        "name": "打补丁的睡衣", "category": "携带意象", "slot": "自我表层",
        "rarity": "常见",
        "description": "补丁摞着补丁，梦的爪子抓不透。受到的心智创伤 -1。",
        "color": "bright_blue", "effect": "mind_armor", "power": 1,
    },
    "leather_apron": {
        "name": "皮革围裙", "category": "携带意象", "slot": "自我表层",
        "rarity": "常见",
        "description": "工坊里带来的旧围裙，硬得像另一层皮肤。受到的清醒创伤 -1。",
        "color": "bright_yellow", "effect": "lucidity_armor", "power": 1,
    },
    "lucky_coin": {
        "name": "磨亮的硬币", "category": "携带意象", "slot": "依附物",
        "rarity": "少见",
        "description": "正面是梦，反面也是梦。每次击破失控意识，崩解度额外推进 3。",
        "color": "bright_yellow", "effect": "coin_bonus", "power": 3,
    },
    "night_battery": {
        "name": "夜灯的电池", "category": "携带意象", "slot": "依附物",
        "rarity": "少见",
        "description": "还剩一点电，够照亮两步之外。视野 +2。",
        "color": "bright_white", "effect": "vision_up", "power": 2,
    },
    "warm_gloves": {
        "name": "缺指的手套", "category": "携带意象", "slot": "依附物",
        "rarity": "常见",
        "description": "指尖露在外面，拾取东西快得像没拿过。拾取显化物不耗时。",
        "color": "bright_green", "effect": "swift_pickup",
    },
    "screwdriver": {
        "name": "小号螺丝刀", "category": "携带意象", "slot": "惯用物",
        "rarity": "少见",
        "description": "拧螺丝的手感还在。修缮效果额外 +40。",
        "color": "bright_white", "effect": "repair_up", "power": 40,
    },
    "wax_seal": {
        "name": "蜡封图章", "category": "携带意象", "slot": "惯用物",
        "rarity": "少见",
        "description": "盖在弹道上的印，谁都拦不住。弹体穿透 +2。",
        "color": "bright_magenta", "effect": "pierce_up", "power": 2,
    },
    "first_cry_fang": {
        "name": "初啼之牙", "category": "携带意象", "slot": "手中意象",
        "rarity": "非常稀有",
        # 2026-10-07 档位平衡：+3 与 T1 常见订书机同值，升为 +4 独占伤害线顶点。
        "description": "无意识领域最深处的一枚齿。伤害 +4。",
        "color": "bright_magenta", "effect": "weapon_damage", "power": 4,
    },
    "lightless_cloak": {
        "name": "无光斗篷", "category": "携带意象", "slot": "自我表层",
        "rarity": "稀有",
        # 实装里 dual_armor 的心智与清醒减免**都取 power**（enemies._take_hit
        # 的 trauma / lucidity_trauma 两处都减 _effect_power("dual_armor")）；
        # 2026-10-22 删除无人读取的装饰字段 power_secondary，真实数值 −3/−3。
        # 2026-10-07 档位平衡：−2/−2 与 T2 铅衬围裙同值，升为 −3/−3 拉开档差
        # （R3 异象 power 6–13，−2 的减免在深层已近乎不可感）。
        "description": "用无光绒织成：心智创伤 −3，清醒创伤 −3。",
        "color": "bright_blue", "effect": "dual_armor", "power": 3,
    },
    "void_pendant": {
        "name": "虚空吊坠", "category": "携带意象", "slot": "依附物",
        "rarity": "稀有",
        # 2026-10-07 档位平衡：+2 与 T1 夜灯的电池同值，升为 +3。
        "description": "悬在虚空边缘的一点光。视野 +3。",
        "color": "bright_white", "effect": "vision_up", "power": 3,
    },
    "fate_coin": {
        "name": "命运硬币", "category": "携带意象", "slot": "依附物",
        "rarity": "非常稀有",
        # 2026-10-07 档位平衡：+4 与 T2 四叶草同值，升为 +5。
        "description": "两面都刻着同一个名字。击破失控意识时崩解度额外 +5。",
        "color": "bright_yellow", "effect": "coin_bonus", "power": 5,
    },
    "deep_thought_chisel": {
        "name": "深念凿子", "category": "携带意象", "slot": "惯用物",
        "rarity": "稀有",
        "description": "能凿进念头的深处。修缮效果额外 +60。",
        "color": "bright_white", "effect": "repair_up", "power": 60,
    },
    "rift_wax_seal": {
        "name": "裂缝蜡印", "category": "携带意象", "slot": "惯用物",
        "rarity": "稀有",
        # 2026-10-07 档位平衡：+2 与 T1 蜡封图章同值，升为 +3。
        "description": "盖在裂隙上的印，弹体从缝隙里穿过去。弹体穿透 +3。",
        "color": "bright_magenta", "effect": "pierce_up", "power": 3,
    },
    "dreamweaver_gloves": {
        "name": "织梦手套", "category": "携带意象", "slot": "依附物",
        "rarity": "稀有",
        "description": "梦的丝线在指尖听话：拾取显化物不耗时。",
        "color": "bright_green", "effect": "swift_pickup",
    },
    "swift_thought_ring": {
        "name": "迅念指环", "category": "携带意象", "slot": "依附物",
        "rarity": "非常稀有",
        # 2026-10-07 档位平衡：−0.2 与 T2 速写手套同值，升为 −0.3（swift 线性
        # 折算 0.1/档）。
        "description": "念头比手快：攻击耗时 −0.3。",
        "color": "bright_cyan", "effect": "swift_strike", "power": 3,
    },

    # ---- 构筑桥接组件（2026-10-08，平衡方案 §6.1「可补的新组件」/§8 上限 6 件）----
    # 六件各自补「核心手段 ↔ 支持组件」之间缺失的那一环，结算接线见
    # core/actions.py（fire/shock/activate_ability）、core/enemies.py
    # （_player_strike/_sound_pulse）、core/materials_sim.py（_ignite_cell）。
    "prism_pendant": {
        "name": "三棱镜的吊坠", "category": "携带意象", "slot": "依附物",
        "rarity": "稀有", "color": "#d8b8f0",
        "description": "吊坠里折射过一次的光不肯回原路：弹体经跳弹改向后命中，给它刻上折射印记（3 回合）。下一次从别的方向打它，创伤 +2，印记随即消耗。",
        "effect": "refract_mark", "power": 2,
    },
    "salt_soaked_coil": {
        "name": "浸盐的线圈", "category": "携带意象", "slot": "依附物·二",
        "rarity": "稀有", "color": "#8ad8d0",
        "description": "盐把水记得很牢：你的放电在湿润目标之间多传一次——2 格内另一位浸在导电液态记忆里的意识吃 2 点完整度，每 6 回合只传得出这一次。",
        "effect": "wet_conduct", "power": 2,
    },
    "ember_boots": {
        "name": "余烬跟的靴子", "category": "携带意象", "slot": "自我表层",
        "rarity": "少见", "color": "#e08a52",
        "description": "鞋跟烧成灰烬也不着：每层你第一次亲手点燃什么时，白得一步免费移动，3 格内正追着你的意识当场跟丢。",
        "effect": "ash_retreat", "power": 1,
    },
    "hunting_lanyard": {
        "name": "追味的皮绳", "category": "携带意象", "slot": "惯用物",
        "rarity": "少见", "color": "#b8895a",
        "description": "绳结记住了材料的气味：身上还挂着附着征兆的意识，你的攻击创伤 +1（不随件数叠加），并说出它附着的是什么。",
        "effect": "attach_hunt", "power": 1,
    },
    "split_tuning_fork": {
        "name": "分岔的音叉", "category": "携带意象", "slot": "依附物·一",
        "rarity": "稀有", "color": "#9ad1ff",
        "description": "两根齿各自共鸣：一次成功的声波引诱替你把下一次脉冲变成控制——声源 3 格内的意识当场震停 1 回合。武装只在本层有效，跨层作废。",
        "effect": "echo_control", "power": 3,
    },
    "blank_half_page": {
        "name": "半页空稿", "category": "携带意象", "slot": "依附物",
        "rarity": "非常稀有", "color": "#eae4d6",
        "description": "没写过的那半页肯替你垫付：想象力归零时仍可展开一项构想，免掉它的想象成本（每层一次，冷却与行动时间照常）。洞察「留白」与它共用这一次。",
        "effect": "blank_pass", "power": 1,
    },
    # ---- 留白线（blank_edge，2026-10-08）----
    # 「以匮乏为燃料」的构筑桥接件：想象力见底时把效力当额外回流。
    # 单独几乎无强度（见 core/state.py 的 _blank_edge_threshold），
    # 只奖励长期在低想象力区间作业的构筑；不入任何四档掉落池。
    "blank_cheque_book": {
        "name": "空白支票簿", "category": "携带意象", "slot": "依附物",
        "rarity": "稀有", "color": "#e6ead8", "loot": False,
        "description": "一本从没写过数字的支票簿：想象力低到 25 点以下时，每回合多回流 1 点。",
        "effect": "blank_edge", "power": 1, "power_secondary": 25,
    },
    "faded_id_card": {
        "name": "褪色的证件", "category": "携带意象", "slot": "自我表层",
        "rarity": "稀有", "color": "#d8d2c4", "loot": False,
        "description": "证件上的字迹淡得认不出是谁：想象力低到 15 点以下时，每回合多回流 1 点。",
        "effect": "blank_edge", "power": 1, "power_secondary": 15,
    },
    "paper_clip": {
        "name": "回形针", "category": "携带意象", "slot": "惯用物",
        "rarity": "非常稀有", "color": "#c9d4e0", "loot": False,
        "description": "把两页空稿别在一起的那枚针：想象力低到 8 点以下时，每回合多回流 2 点。",
        "effect": "blank_edge", "power": 2, "power_secondary": 8,
    },
    "singed_gloves": {
        "name": "焦边的手套", "category": "携带意象", "slot": "依附物",
        "rarity": "稀有", "color": "#bca58d", "loot": False,
        "description": "布边被火烤卷了：爆炸冲击造成的清醒创伤减少 1，至少承受 1；不免疫火焰，也不阻止燃烧附着。",
        "effect": "blast_padding", "power": 1,
    },
    # ---- 投掷/弹道桥接件（2026-10-08 新增，2026-10-09 由 usables 迁入）----
    # 常驻被动件：必须有 slot 才能上联想盘（原放在 usables.py 时 category 是
    # 「惯用物」，面板 Enter 会把它们当一次性道具用掉，效果永远不生效）。
    "throwing_gloves": {
        "name": "投掷手套", "category": "携带意象", "slot": "惯用物",
        "rarity": "少见", "color": "#c8b890",
        "description": "掌心缝着防滑胶粒的手套：投掷距离 +3，投掷威力 +1。",
        "effect": "throw_master", "power": 1,
    },
    "focus_ring": {
        "name": "调焦环", "category": "携带意象", "slot": "惯用物",
        "rarity": "少见", "color": "#c8d8f0",
        "description": "套在指间旋动的黄铜环，替你的眼睛校准弹道：弹体穿透 +1。",
        "effect": "pierce_up", "power": 1,
    },
    "sling": {
        "name": "投石索", "category": "携带意象", "slot": "惯用物",
        "rarity": "少见", "color": "#c8b890",
        "description": "皮兜磨得发亮。挎上它，你扔什么都又远又稳：投掷距离 +3，投掷物的爆破与引火威力 +1。",
        "effect": "throw_master", "power": 1,
    },
    # ---- 梦中梦·千禧园（2026-10-10）----
    "unread_99": {
        "name": "未读消息 99+", "category": "携带意象", "slot": "惯用物", "rarity": "少见", "color": "#e06060",
        "description": "永远清不完的红点。焦虑推着你往前：崩解推进 +1。",
        "effect": "coin_bonus", "power": 1,
    },
    "crystal_charm": {
        "name": "水晶机箱挂饰", "category": "携带意象", "slot": "依附物", "rarity": "稀有", "color": "#a0e0f0",
        "description": "机箱前面板上的亚克力小水晶。晃一晃，静电都绕着走（心智与清醒的伤口都浅一点）。",
        "effect": "dual_armor", "power": 1,
    },
    "broadband_grail": {
        "name": "宽带圣杯", "category": "携带意象", "slot": "惯用物", "rarity": "非常稀有", "color": "#f0d060",
        # 2026-10-22 倒挂修复：非常稀有的千禧园首领奖励原 swift 1（−0.1），
        # 反而弱于 T2 速写手套（2）与 T3 迅念指环（3）；升为 4。
        # 描述里的「思维流畅」是 data/item_prose.py 的 EFFECT_START 关键词（用于
        # 拆出作用说明段），改动这段时必须保留该词，否则物品定义导入会报错。
        "description": "千年虫的巢穴深处流出的一条永远在线的带宽。思维流畅：攻击基础耗时 −0.4。",
        "effect": "swift_strike", "power": 4,
    },
}
