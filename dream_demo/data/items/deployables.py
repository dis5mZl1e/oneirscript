"""部署类物品（2026-10-22 A2 新增十件）。

P4 四件中后期工具（12—20 层）与 P5 六件终局珍品（22—26 层）。
硬下限写在 ``min_depth``、局内上限写在 ``run_limit``、独占渠道写在
``grant_source``——三个字段都由 ``core/item_access.py`` 的统一资格查询消费，
任何渠道（地面散投、保底、宝库、事件、NPC 货架、位面柜子）都过同一道闸。
"""

from __future__ import annotations

from typing import Any

ITEMS = {
    # ---- P4 中后期工具（稀有）----
    "night_shift_beacon": {
        "name": "误点的夜班灯", "category": "交互道具",
        "rarity": "稀有", "color": "#ffd98a",
        "description": "值班表上写错了班次。灯芯一直亮着，每隔几个回合就咳一声——那声音够远，够让别的东西循着过来。",
        "effect": "deploy_beacon", "power": 12, "max_stack": 1,
        "min_depth": 12, "run_limit": 2,
    },
    "portable_siphon": {
        "name": "折叠虹吸管", "category": "交互道具",
        "rarity": "稀有", "color": "#9ad8c8",
        "description": "两截软管折在一起。展开后架在源与出口之间，它每回合替你搬一点东西，直到管子灌满或者源被抽干。",
        "effect": "deploy_siphon", "power": 8, "max_stack": 1,
        "min_depth": 16, "run_limit": 2,
    },
    "wax_emergency_seal": {
        "name": "应急蜡封", "category": "交互道具",
        "rarity": "稀有", "color": "#f0e0b0",
        "description": "一小管备用蜡。挤在门口的地上会堆成一堵墙，挡住不该进来的东西——但蜡会化，热得越快化得越快。",
        "effect": "deploy_wax_seal", "power": 60, "max_stack": 1,
        "min_depth": 18, "run_limit": 2,
    },
    "winter_sample": {
        "name": "冬天的样本", "category": "交互道具",
        "rarity": "稀有", "color": "#a8e0f5",
        "description": "装着液氮的薄壁瓶。摔碎时白雾漫开：中心冻得最实，四周只是发凉；地板不会被整层冻住。",
        "effect": "winter_sample", "power": 24, "max_stack": 1,
        "min_depth": 20, "run_limit": 2,
    },
    # ---- P5 终局珍品（非常稀有）：只走珍品机会，不进任何散投／保底／货架 ----
    "breach_spool": {
        "name": "拆迁用的线轴", "category": "交互道具",
        "rarity": "非常稀有", "color": "#e0c060",
        "description": "一卷绷紧的细线。抽出去能割开挡路的东西——一次只割三处，每回合割一点。",
        "effect": "breach_spool", "power": 180, "max_stack": 1,
        "min_depth": 22, "run_limit": 1,
        "grant_source": "event:treasure.breach",
    },
    "folded_escape_route": {
        "name": "折好的逃生通道", "category": "交互道具",
        "rarity": "非常稀有", "color": "#c8b8f0",
        "description": "两条折好的路，接在两个看得见的空位之间。走过去比绕远路近，但只够走三趟。",
        "effect": "deploy_escape_route", "power": 3, "max_stack": 1,
        "min_depth": 22, "run_limit": 1,
        "grant_source": "event:treasure.breach",
    },
    "storm_accumulator": {
        "name": "未寄出的雷暴", "category": "交互道具",
        "rarity": "非常稀有", "color": "#7ee8c0",
        "description": "一封没寄出去的雷暴信。落地之后它分四回合把攒下的电倒出来：导电的记忆液和带静电的尘。",
        "effect": "storm_accumulator", "power": 60, "max_stack": 1,
        "min_depth": 24, "run_limit": 1,
        "grant_source": "event:treasure.storm",
    },
    "quiet_boundary": {
        "name": "最后一圈安静", "category": "交互道具",
        "rarity": "非常稀有", "color": "#b8c8e8",
        "description": "一圈薄薄的静音。声音穿过它时会再哑一分——只挡声音，不挡眼睛。",
        "effect": "deploy_quiet_boundary", "power": 4, "max_stack": 1,
        "min_depth": 24, "run_limit": 1,
        "grant_source": "event:treasure.storm",
    },
    "waking_reserve": {
        "name": "留给醒来的那一口", "category": "摄入物",
        "rarity": "非常稀有", "color": "#e8d890",
        "description": "最后一口气，攒着等天亮。喝下去清醒 30、心智 20，还洗得掉一件黏在身上的东西。",
        "effect": "waking_reserve", "power": 30, "power_secondary": 20, "max_stack": 1,
        "min_depth": 26, "run_limit": 1,
        "grant_source": "event:treasure.dawn",
    },
    "bottled_sunrise": {
        "name": "瓶装天亮", "category": "交互道具",
        "rarity": "非常稀有", "color": "#ffb870",
        "description": "瓶里封着一小段早晨。摔开先亮两回合引信，然后三回合里把八十单位燃油倒出来点着。",
        "effect": "bottled_sunrise", "power": 80, "max_stack": 1,
        "min_depth": 26, "run_limit": 1,
        "grant_source": "event:treasure.dawn",
    },
}
