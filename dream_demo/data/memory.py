"""记忆碎片的可拆卸效果与稀有度映射。

耐受（原「免疫」）类有四档减免。2026-10-26 平衡审计前，12 条手写耐受全是
一刀切的 60/50，16 件耐受碎片横跨四个稀有度却数值完全一致——稀有度在这个
品类上一分强度都不兑现。现在按所在碎片的稀有度分档：

    常见 45/30 · 少见 55/45 · 稀有 60/55 · 非常稀有 60/65

（积累减免封顶 60%：`core/state.py::memory_portent_factor` 有 `max(.4, …)`
下限，写超过 60 与 60 等价；所以最上面两档只靠时长拉开。）

扩展包目录行自带 ``accumulation_reduction``，走 ``growth_runtime`` 覆盖，
不受这里的分档影响。
"""

from __future__ import annotations

from typing import Any

MEMORY_FRAGMENT_EFFECTS: dict[str, dict[str, Any]] = {
    # ---- 免疫类：对应已有洞察的同类征兆，碎片是它们的「可拆卸」版本 ----
    "眩光的钝化": {
        "kind": "immunity", "portents": ("obscured",), "value": 1,
        "accumulation_reduction": 45, "duration_reduction": 30,  # 常见档
        "short": "免疫遮蔽",
        "detail": "弥散印象造成的视线遮蔽对你无效。",
    },
    "低温的迟钝": {
        # 持在「干涸的手套」（2026-10-26 由常见升为少见）与「结霜的信封」两件少见碎片上。
        "kind": "immunity", "portents": ("frozen",), "value": 1,
        "accumulation_reduction": 55, "duration_reduction": 45,  # 少见档
        "short": "免疫冻僵",
        "detail": "液氮的冻僵对你无效。",
    },
    "灼痕的硬壳": {
        "kind": "immunity", "portents": ("scalded",), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 55,  # 稀有档
        "short": "免疫灼伤",
        "detail": "灼热蒸汽的灼伤对你无效。",
    },
    "辐射的钝感": {
        "kind": "immunity", "portents": ("irradiated",), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 65,  # 非常稀有档
        "short": "免疫辐射病",
        "detail": "辐射尘埃的辐射病对你无效。",
    },
    "休止的静默": {
        "kind": "immunity", "portents": ("numb",), "value": 1,
        "accumulation_reduction": 45, "duration_reduction": 30,  # 常见档
        "short": "免疫麻痹",
        "detail": "麻痹与迟钝的征兆对你无效。",
    },
    "边缘的容差": {
        "kind": "immunity", "portents": ("sedated",), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 55,  # 稀有档
        "short": "免疫迟钝",
        "detail": "镇静类征兆无法让你陷入沉眠般的迟缓。",
    },
    # ---- 环境适应类 ----
    # 适应效果挂在**真实存在**的环境机制上（不是新造机制）：
    #   - "honey"：蜂蜜地面的双倍移动耗时对你无效
    #   - "viscous"：纸浆等造成的「迟滞」不再拖慢脚步（与洞察「液态亲和」同通道）
    #   - "noise"：声响（异象的听觉判定）对你减弱 2 点（与单边耳机同通道）
    "湿滑的经验": {
        "kind": "adapt", "adapt": "honey", "value": 1,
        "short": "适应蜂蜜",
        "detail": "蜂蜜地面不再让移动耗时翻倍。",
    },
    "空转的间隙": {
        "kind": "adapt", "adapt": "viscous", "value": 1,
        "short": "适应粘稠",
        "detail": "粘稠液体不再额外拖慢你的行动。",
    },
    "雨声的遮蔽": {
        "kind": "adapt", "adapt": "noise", "value": 2,
        "short": "脚步与道具声响 −2",
        "detail": "自身脚步与普通道具的基础声径 −2，最低 1；不减主动诱引、爆炸，也不改异象视野。",
    },
    # ---- §11 §9（2026-10-20）：8 件碎片的独立声学／测绘配置 ----
    # 范围与时效类同类取最高值（见 state.memory_stat_bonus），不同轴可并用。
    "电路的辨音": {
        "kind": "stat", "stat": "listen", "value": 3,
        "short": "听取上限 +3",
        "detail": "听取上限 12→15：能接收更远处真实发出的声音，但不扩大声源本身，也不会看见未感知的异象。",
    },
    "忙音的间距": {
        "kind": "stat", "stat": "lure_radius", "value": 2,
        "short": "主动诱引 +2",
        "detail": "主动诱引类真实声源的声径 +2，只对基础大于 0 的声音生效；广播诱敌，也可能招来更多敌人。",
    },
    "像素的寻路": {
        "kind": "compound",
        "effects": (
            {"kind": "stat", "stat": "survey", "value": 1},
            {"kind": "stat", "stat": "margin", "value": 2},
        ),
        "short": "测绘 +1／旁注 +2",
        "detail": "冲印、显影拓印的静态地形扫描半径 +1，旁注长度 +2；不提高当前视觉或任意技能攻击范围。",
    },
    "回响的储备": {
        "kind": "compound",
        "effects": (
            {"kind": "stat", "stat": "max_imagination", "value": 8},
            {"kind": "stat", "stat": "lure_cost", "value": 1},
        ),
        "short": "想象上限 +8／诱引 −1",
        "detail": "想象力上限 +8（首次获得回填 8 点），主动诱引类构想（回响）的最终想象费用 −1，最低 1。",
    },
    "气泡的卸压": {
        "kind": "compound",
        "effects": (
            {"kind": "stat", "stat": "echo_damping", "value": 60},
            {"kind": "stat", "stat": "echo_duration_reduction", "value": 50},
        ),
        "short": "回声放大减弱／时长减半",
        "detail": "自身「回声」征兆的声音倍率超出 1 的部分降低 60%，新附着时间缩短 50%（最低 1 回合）；不削回声雾、瓷墙或其他征兆。",
    },
    # ---- 属性类：少量上限提升 ----
    # 2026-10-26 平衡审计：三条上限线原先四档乱序——常见就有 +10、非常稀有反而
    # 只有 +8。现在统一成 常见 6 < 少见 8 < 稀有 10 < 非常稀有 12。
    "机械的耐性": {
        "kind": "stat", "stat": "max_mind", "value": 10,
        "short": "心智上限 +10",
        "detail": "心智上限 +10，获得时立即回填 10 点心智。",
    },
    "守夜的余温": {
        "kind": "stat", "stat": "max_mind", "value": 8,
        "short": "心智上限 +8",
        "detail": "心智上限 +8，获得时立即回填 8 点心智。",
    },
    "雨声的钝化": {
        "kind": "immunity", "portents": ("obscured", "frozen"), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 55,  # 稀有档（两系合一）
        "short": "免疫遮蔽与冻结",
        "detail": "遮蔽与冻结对你无效——那把伞下从来淋不到。",
    },
    "常亮的房间": {
        # 少见档（持在「模型房间的灯」与升档后的「油漆味的走廊」上）。
        "kind": "stat", "stat": "max_lucidity", "value": 8,
        "short": "清醒上限 +8",
        "detail": "清醒度上限 +8，获得时立即回填 8 点清醒度。",
    },
    "未尽的余韵": {
        "kind": "stat", "stat": "max_imagination", "value": 10,
        "short": "想象上限 +10",
        "detail": "想象力上限 +10，获得时立即回填 10 点想象力。",
    },
    "陈年的积累": {
        "kind": "stat", "stat": "clue_retention", "value": 4,
        "short": "线索保留 +4 回合",
        "detail": "声音线索保持时间 2→6 个真实回合；不自动更新来源位置。",
    },
    "移动的视窗": {
        "kind": "compound",
        "effects": (
            {"kind": "stat", "stat": "sight", "value": 1},
            {"kind": "stat", "stat": "listen", "value": 2},
        ),
        "short": "视野 +1／听取 +2",
        "detail": "视野 +1（与发光加成同一条通道），听取上限 +2；稳定的视觉／听觉配置。",
    },
    "扩大的肺活": {
        "kind": "stat", "stat": "max_imagination", "value": 8,
        "short": "想象上限 +8",
        "detail": "想象力上限 +8，获得时立即回填 8 点想象力。",
    },
    "扩大的清醒": {
        "kind": "stat", "stat": "max_lucidity", "value": 6,
        "short": "清醒上限 +6",
        "detail": "清醒度上限 +6，获得时立即回填 6 点清醒度。",
    },
    "扩大的想象": {
        "kind": "stat", "stat": "max_imagination", "value": 10,
        "short": "想象上限 +10",
        "detail": "想象力上限 +10，获得时立即回填 10 点想象力。",
    },
    # 核心执念·初啼之核专属（2026-09-18）：全表唯一的「免疫失忆」。
    # 无念黑渊那条线（禁行囊/装配 + 名称变问号）本来是硬惩罚，只有打赢最深处
    # 才拿得到解——这也是「碎片比洞察更珍贵」的一个落点。
    "初啼的余地": {
        "kind": "immunity", "portents": ("oblivion_strong",), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 65,  # 非常稀有档
        "short": "免疫失忆",
        "detail": "无念黑渊吞掉记忆时，你仍记得自己是谁（行囊与携带意象照常可用）。",
    },
    # ---- 内容扩展包 v2（2026-10-11）：6 条新效果（immunity 4 + stat 2）----
    # 免疫目标全是 PORTENT_DEFINITIONS 里真实存在的负面征兆（守卫测试会查）。
    "毒雾的失敏": {
        "kind": "immunity", "portents": ("poisoned",), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 55,  # 稀有档
        "short": "免疫毒气",
        "detail": "毒气的心智侵蚀对你无效——你早就尝过更怪的味道。",
    },
    "倒带的静音": {
        "kind": "immunity", "portents": ("rewind_lag",), "value": 1,
        "accumulation_reduction": 60, "duration_reduction": 55,  # 稀有档
        "short": "免疫倒带迟滞",
        "detail": "磁带墙的倒卷声拖不住你的脚步。",
    },
    "门风的驯服": {
        "kind": "immunity", "portents": ("door_vertigo",), "value": 1,
        "accumulation_reduction": 55, "duration_reduction": 45,  # 少见档
        "short": "免疫门扉眩晕",
        "detail": "门隙之风让你看什么都稳稳当当。",
    },
    "草叶的松动": {
        "kind": "immunity", "portents": ("snared",), "value": 1,
        "accumulation_reduction": 45, "duration_reduction": 30,  # 常见档
        "short": "免疫缠住",
        "detail": "捕梦草卷不住你的脚踝——你记得怎么从草叶里脱身。",
    },
    "满格的存档": {
        "kind": "stat", "stat": "max_imagination", "value": 12,
        "short": "想象上限 +12",
        "detail": "想象力上限 +12，获得时立即回填 12 点想象力。",
    },
    "醒着的顶层": {
        "kind": "stat", "stat": "max_lucidity", "value": 12,
        "short": "清醒上限 +12",
        "detail": "清醒度上限 +12，获得时立即回填 12 点清醒度。",
    },
}
MEMORY_RARITY: dict[str, str] = {
    "lighthouse_keeper_memory": "少见",
    "frost_letter_memory": "少见",
    "paint_smell_memory": "少见",
    "shared_umbrella_memory": "稀有",
    "rain_machine_memory": "少见",
    "rain_machine_memory_2": "少见",
    "model_room_memory": "少见",
    "unfinished_song_memory": "稀有",
    "draft_margin_memory": "稀有",
    "plastic_gear_memory": "常见",
    "choir_note": "常见",
    "attic_dust": "常见",
    "last_window": "少见",
    "salt_crust": "常见",
    # 2026-10-26 平衡审计：这两件原先挂在「罕见」档，却顶着 2 区/稀有档才该有的
    # 效果（与结霜的信封共用「低温的迟钝」、与模型房间的灯共用「常亮的房间」）。
    # 同一效果只能有一个强度，于是把碎片本身升到效果所在的档位。
    "dry_gloves": "少见",
    "burn_scar": "稀有",
    "leaden_marrow": "非常稀有",
    "walker_habit": "少见",
    "wide_lung": "少见",
    "calm_pulse": "常见",
    "deep_reserve": "稀有",
    "first_cry_memory": "非常稀有",
    # ---- 内容扩展包 v2（2026-10-11）：+12 条 ----
    "usb_drive_memory": "非常稀有",
    "tape_hiss_memory": "稀有",
    "dial_tone_memory": "少见",
    "pixel_pet_memory": "少见",
    "bubble_wrap_memory": "常见",
    "doorbell_memory": "少见",
    "grass_slip_memory": "常见",
    "poison_vial_memory": "稀有",
    "elevator_memory": "稀有",
    "scribe_ink_memory": "非常稀有",
    "echo_ring_memory": "稀有",
    "circuit_hum_memory": "少见",
}


# 记忆槽上限。
MEMORY_LIMIT = 3

# Fragments configure endurance. Knowledge-based insights own situational
# actions; neither channel silently suppresses all consequences of exposure.
# 每条耐受自带分档数值（见文件头），这里只做「免疫 → 耐受」的措辞改写与
# 文案生成；没写数值的退回 60/50。
for _effect in MEMORY_FRAGMENT_EFFECTS.values():
    if _effect.get('kind') == 'immunity':
        _effect['kind'] = 'resistance'
        _accumulation = int(_effect.setdefault('accumulation_reduction', 60))
        _duration = int(_effect.setdefault('duration_reduction', 50))
        _effect['short'] = _effect['short'].replace('免疫', '耐受')
        _effect['detail'] = (
            f'对应征兆的负面积累降低 {_accumulation}%，'
            f'新沾染时长缩短 {_duration}%（最低 1 回合）；仍会受到影响，同类耐受不叠加。'
        )

# 扩展包记忆碎片：效果表与稀有度池的键都是目录 id，由目录单独供数
# （integration_status 未到 runtime 的行一条都不注册）。放在免疫改写之后，
# 扩展包自己声明的减免值不会被上面那段历史口径覆盖。
from .expansion.growth_runtime import memory_effect_rows, memory_rarity_rows

MEMORY_FRAGMENT_EFFECTS.update(memory_effect_rows())
MEMORY_RARITY.update(memory_rarity_rows())
