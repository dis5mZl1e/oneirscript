"""摄入物：吃/喝获得即时恢复。"""

from __future__ import annotations

from typing import Any

ITEMS = {
    "warm_coffee": {
        "name": "半罐温咖啡", "category": "摄入物",
        "rarity": "常见",
        "description": "苦味仍然可靠。恢复想象力 10。", "color": "bright_yellow",
        "effect": "restore_imagination", "power": 10, "max_stack": 3,
    },
    "unlabeled_sedative": {
        "name": "没有标签的镇静剂", "category": "摄入物",
        "rarity": "少见",
        "description": "恢复少量心智，但让下一次移动迟疑。", "color": "bright_yellow", "effect": "restore_mind", "power": 12, "max_stack": 2,
    },
    "cold_tea": {
        "name": "凉的半罐茶", "category": "摄入物",
        "rarity": "常见",
        "description": "醒一半，梦一半。恢复清醒度 6 与想象力 4。", "color": "bright_blue",
        "effect": "restore_split", "power": 6, "power_secondary": 4, "max_stack": 3,
    },
    "expired_pill": {
        "name": "过期的糖衣药丸", "category": "摄入物",
        "rarity": "少见",
        "description": "糖衣之下要么是救济，要么是账单。", "color": "bright_yellow",
        "effect": "gamble", "max_stack": 2,
    },
    "espresso_shot": {
        "name": "浓缩咖啡因", "category": "摄入物",
        "rarity": "少见",
        "description": "想象力立刻沸腾，清醒度随后分期偿还。每份独立支付 5 点清醒度，10 回合还清，重复服用不覆盖旧债。", "color": "bright_magenta",
        "effect": "overclock", "power": 20, "max_stack": 2,
    },
    "warm_water": {
        "name": "温水", "category": "摄入物",
        "rarity": "常见",
        "description": "冲开迟滞与麻痹攒下的欠账，顺便暖一点心智。", "color": "bright_cyan",
        "effect": "warm_restore", "power": 3, "max_stack": 3,
    },
    "mint_lozenge": {
        "name": "薄荷锭", "category": "摄入物",
        "rarity": "常见",
        "description": "入口冰凉，瞬间压住眩晕。恢复少量清醒度。",
        "color": "bright_blue", "effect": "restore_lucidity", "power": 8, "max_stack": 3,
    },
    "strong_mint_tea": {
        "name": "特浓薄荷茶", "category": "摄入物",
        "rarity": "少见",
        "description": "薄荷的凉意直上眉心：滞留期间每两回合沁出一点清醒，共十四点。",
        "color": "bright_cyan", "effect": "lucidity_regen", "power": 28, "max_stack": 2,
    },
    "wormwood_pastille": {
        "name": "苦艾糖滴", "category": "摄入物", "rarity": "少见",
        "description": "苦得皱眉的一粒糖，含化之后，梦的边缘会清楚一点点。心智 +10。",
        "color": "#a3b18a", "effect": "restore_mind", "power": 10,
    },
    "espresso_tablet": {
        "name": "浓缩咖啡锭", "category": "摄入物", "rarity": "少见",
        "description": "压得像小石头的浓缩咖啡。舌尖一麻，睡意退散：清醒度 +12。",
        "color": "#c8a878", "effect": "restore_lucidity", "power": 12,
    },
    "inspiration_coffee": {
        "name": "灵感咖啡", "category": "摄入物", "rarity": "少见",
        "description": "苦到灵魂发抖的一小杯，喝完的瞬间脑子里多出三个没写过的开头。想象力 +16。",
        "color": "#c8a878", "effect": "restore_imagination", "power": 16,
    },
    "sleeping_lozenge": {
        # 2026-10-26（平衡审计 §11.4）：清醒度 +5 → +6。5 低于「单资源 6–12」
        # 标尺下限，常见档因此从 5 起跳成 2.0× 跨度；提到 6 后为 6·8·10。
        "name": "安眠含片", "category": "摄入物", "rarity": "常见",
        "description": "含一片，梦替你把没做完的事做完一半。清醒度 +6。",
        "color": "#a7a9c7", "effect": "restore_lucidity", "power": 6,
    },
    "dream_electrolytes": {
        "name": "梦境电解水", "category": "摄入物", "rarity": "少见",
        "description": "一瓶喝不出味道的透明液体。均衡补液：清醒度 +8、想象力 +8。",
        "color": "#7ad0ff", "effect": "restore_split", "power": 8, "power_secondary": 8,
    },
    "morning_dew": {
        "name": "晨露药剂", "category": "摄入物",
        "rarity": "稀有",
        "description": "无意识领域里最干净的东西。恢复心智 24。",
        "color": "bright_cyan", "effect": "restore_mind", "power": 24, "max_stack": 2,
    },
    "deep_thought_tea": {
        "name": "深念茶", "category": "摄入物",
        "rarity": "稀有",
        "description": "一口下去，想到很远的地方。恢复清醒 12 与想象力 12。",
        "color": "bright_blue", "effect": "restore_split", "power": 12, "power_secondary": 12, "max_stack": 2,
    },
    "unfinished_fullstop": {
        "name": "未竟的句点", "category": "摄入物",
        "rarity": "非常稀有",
        "description": "一句话的结尾被人拿走了。想象力 +35、清醒度 +12；每份在 10 回合内分 8 次支付心智 1 点，不覆盖旧债。",
        "color": "bright_magenta", "effect": "fullstop_reserve", "power": 35, "power_secondary": 12, "max_stack": 1, "loot": False, "min_depth": 18, "run_limit": 1,
        "grant_source": "enemy:anomaly.unfinished_period",
    },
    "mint_dew": {
        "name": "薄荷露", "category": "摄入物",
        "rarity": "少见",
        "description": "铃兰薄荷叶心里的一滴凉意。恢复心智 8，并冲开迟滞与麻痹的欠账。",
        "color": "bright_green", "effect": "warm_restore", "power": 8, "max_stack": 2,
    },
    "sage_powder": {
        "name": "贤者之粉", "category": "摄入物",
        "rarity": "少见",
        "description": "苔藓磨成的金粉。想象力 +24；每份在接下来 10 回合每 2 回合独立支付清醒度 1 点，不覆盖旧债。",
        "color": "bright_yellow", "effect": "overclock", "power": 24, "max_stack": 1,
    },
}
