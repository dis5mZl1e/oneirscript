"""稳定意识（NPC）定义：交易/任务选项表与投放参数。"""

from __future__ import annotations

from typing import Any

NPC_DEFINITIONS: dict[str, dict[str, Any]] = {
    "npc.circuit_keeper": {
        "name": "回路检修员", "glyph": "⌁", "color": "#d6c79c",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "心智创伤",
        "vault_only": True,
        "dialogue": ["先看输入，再看它们怎样汇入输出。交叉的线路有绝缘，不会因为靠在一起就通电。"],
        "options": (
            {"label": "询问这张回路的检修顺序", "circuit_hint": True, "always": True},
            {"label": "怎么看输入状态？", "message": "查看机关可以读到输入名称、通断和摆轮相位。开关靠近后操作，压板要踩上去。", "always": True},
            {"label": "告辞。", "leave": True, "always": True},
        ),
    },
    # 0 层「梦的起始」的教学向导：只说话，不做任何交易（选项全是
    # message/leave，没有任何 cost/gain 字段——choose_npc_option 对
    # message 选项只追加台词，不产出不消耗）。
    # ---- 梦中梦·玩具的回忆（2026-09-22）：每层一位守门人 ----
    # ---- 梦中梦·门之回廊（2026-09-22）：守灯人 ----
    "npc.lantern_keeper": {
        "name": "提灯的门房", "glyph": "✜ ", "color": "#9ab8ff",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "清醒创伤",
        "dialogue": ["门都数过了。走廊不会骗人，骗人的是走廊尽头的光。"],
        "options": (),
    },
    # ---- 梦中梦·余烬廊桥（2026-10-08）：固定入口 NPC「引火人」 ----
    # 11–19 层随机刷新（开局一次性判定，未必出现）；全部选项 always——
    # 只有「走进去 / 不走」两条，不做交易（message 型对话不产出不消耗）。
    "npc.ember_lighter": {
        "name": "引火人", "glyph": "✷", "color": "#ff9a4f",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "心智创伤",
        "description": "蹲在一堆冷灰边的瘦长身影，手里反复擦着一根擦不着的火柴。",
        "dialogue": [
            "「火还在底下烧，只是没人替它引路。」",
            "「你要进去也行——带上这根火柴。里头的东西，只有烧穿了才肯让人过去。」",
        ],
        "options": (
            {"label": "「跟我走进火光里。」", "enter_realm": "ember_bridge", "always": True},
            {"label": "「不了，我再看看。」", "leave": True, "always": True},
        ),
    },
    "npc.calibrator": {
        "name": "校准师", "glyph": "⊞", "color": "#e8e8f0",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "心智创伤",
        "dialogue": ["每个空心方框都是压板。全部放上立方体，合辙枢才会打开校准之门。", "立方体到位后仍可移动。先留出绕行的位置，别把箱子推入没有标记的墙角。", "推错了？回来与我交谈，选择重置本层机关。"],
        "options": (
            {"label": "确认解谜进度", "puzzle": "check", "always": True},
            {"label": "重置本层机关", "puzzle": "reset", "always": True},
            {"label": "返回主梦入口", "puzzle": "return", "always": True},
            {"label": "告辞。", "leave": True, "always": True},
        ),
    },
    "npc.toy_bear": {
        "name": "缺一只眼的布偶熊", "glyph": "ღ", "color": "#c8a86a",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "心智创伤",
        "dialogue": ["门记得两盏并肩的灯，也记得第三盏灯熄灭时的安静。", "左灯与中灯经过合辙，右灯经过反相接线。观察它们怎样汇入最后的合辙枢。", "靠近开关，撞一下或按行动键操作。推错了？回来与我交谈，选择重置本层机关。"],
        "options": (
            {"label": "确认解谜进度", "puzzle": "check", "always": True},
            {"label": "重置本层机关", "puzzle": "reset", "always": True},
            {"label": "返回主梦入口", "puzzle": "return", "always": True},
            {"label": "告辞。", "leave": True, "always": True},
        ),
    },
    "npc.wind_up_soldier": {
        "name": "上弦的士兵", "glyph": "♟", "color": "#8a9ac8",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "清醒创伤",
        "dialogue": ["两只摆轮每八回合亮两拍，开局相差四拍。调相开关能让右摆轮追上左摆轮。", "让两轮同亮，再用你的重量压住同步压板。门会记住这次重合，不必抢跑。"],
        "options": (
            {"label": "确认解谜进度", "puzzle": "check", "always": True},
            {"label": "重置本层机关", "puzzle": "reset", "always": True},
            {"label": "返回主梦入口", "puzzle": "return", "always": True},
            {"label": "告辞。", "leave": True, "always": True},
        ),
    },
    "npc.marionette": {
        "name": "提线木偶", "glyph": "✃", "color": "#c9a0ff",
        "integrity": 40, "relation": "稳定意识", "trauma_type": "心智创伤",
        "dialogue": ["童谣的针脚是：低音、高音、中音、高音。每次走上压板才会记下一针。", "给玩偶上弦，再把童谣接回去。站着不动不会重复，踩错也不会受伤。"],
        "options": (
            {"label": "确认解谜进度", "puzzle": "check", "always": True},
            {"label": "重置本层机关", "puzzle": "reset", "always": True},
            {"label": "返回主梦入口", "puzzle": "return", "always": True},
            {"label": "告辞。", "leave": True, "always": True},
        ),
    },
    "npc.origin_greeter": {
        "name": "迎面的纸偶", "glyph": "☃", "color": "#e8e0ff",
        "integrity": 20, "relation": "稳定意识",
        "description": "叠得不太整齐的纸偶，站在所有梦的入口处，专门负责打招呼。",
        "dialogue": [
            "纸偶朝你歪了歪头：「欢迎。这里是所有梦开始的地方——别的我先不说，赶路要紧。」",
        ],
        "options": [
            {"label": "「这里是什么地方？」",
             "message": "「梦的起始。往后的每一层都比这里深，也比这里吵。」"},
            {"label": "「你为什么在这里？」",
             "message": "「总得有人站在门口，跟每一场新梦问声好。我叠得不够整齐，但胜在勤快。」"},
            {"label": "练习交换：1 点想象力换温水（不带出本层）", "tutorial_only": True,
             "cost": {"imagination": 1}, "gain": {"item": "warm_water"}},
            {"label": "领取一份练习赠品（限一次，不带出本层）", "tutorial_only": True,
             "gift_set": "origin_course_gift", "show_if": {"gift_available": "origin_course_gift"},
             "gain": {"item": "warm_water"}},
            {"label": "接取练习委托：取回玻璃杯", "tutorial_only": True, "tutorial_control": "accept", "always": True},
            {"label": "交付练习委托", "tutorial_only": True, "tutorial_control": "deliver", "always": True},
            {"label": "「告辞。」", "leave": True, "always": True},
        ],
    },
    "npc.mind_observer": {
        "name": "精神观测家", "glyph": "⌖", "color": "#7ad0ff",
        "integrity": 20, "relation": "稳定意识",
        "description": "提着铜制观测镜的旅人：专门收集梦里才有的罕见念头。",
        "dialogue": [
            "观测家转着黄铜镜筒打量你：「有意思……你的梦没有折痕。」",
            "「拿点我没见过的东西来，我可以付『看得见的报酬』。」",
        ],
        "options": [
      {"label": "交出消耗品，换一份洞察",
             "cost": {"consumables": 3}, "gain": {"insight": "机械迷恋"}},
            {"label": "交出携带意象，换想象上限",
             "cost": {"random_gear": 4}, "gain": {"stat": ["max_imagination", 5]}},
            {"label": "交出温咖啡，换清醒上限",
             "cost": {"items": ["warm_coffee", 2]}, "gain": {"stat": ["max_lucidity", 5]}},
            {"label": "付心智，换一件少见装备",
             "cost": {"mind": 14}, "gain": {"item": "night_battery"}},
            {"label": "付清醒度，换一份洞察",
             "cost": {"lucidity": 14}, "gain": {"insight": "局部照明"}},
            # 容器交易（2026-09-19）：多种容器=非常稀有（消耗品+资源高价）。
            {"label": "交出消耗品，换一支理想试管（多种液体）",
             "cost": {"consumables": 4}, "gain": {"item": "ideal_tube"}},
            {"label": "付清醒度，换一台理想气体容器（多种气体）",
             "cost": {"lucidity": 16}, "gain": {"item": "ideal_vessel"}},
            {"label": "只是聊聊", "leave": True, "always": True},
        ],
    },
    "npc.hypnotist": {
        "name": "催眠师", "glyph": "◔", "color": "#c9a0ff",
        "integrity": 18, "relation": "稳定意识",
        "description": "怀表在指间画圈的温和声音：她说睡眠也是一种交易。",
        "dialogue": [
            "「睡不着，还是醒不了？两种生意我都做。」",
            "「清醒一点，或者安稳一点——选一头，另一头归我。」",
        ],
        "options": [
      {"label": "清醒换心智上限",
             "cost": {"lucidity": 12}, "gain": {"stat": ["max_mind", 6]}},
            {"label": "心智换清醒上限",
             "cost": {"mind": 12}, "gain": {"stat": ["max_lucidity", 6]}},
            {"label": "交出 2 件消耗品，换薄荷露",
             "cost": {"consumables": 2}, "gain": {"item": "mint_dew"}},
            {"label": "付心智，换一份洞察",
             "cost": {"mind": 16}, "gain": {"insight": "延迟抵达"}},
            {"label": "付清醒度，换灯塔透镜",
             "cost": {"lucidity": 16}, "gain": {"item": "lighthouse_lens"}},
            {"label": "婉拒她的好意", "leave": True, "always": True},
        ],
    },
    "npc.scrapper": {
        "name": "拾荒者", "glyph": "⛑", "color": "#c8b890",
        "integrity": 18, "relation": "稳定意识",
        "description": "推着一辆吱呀作响的小车的拾荒者：车斗里全是危险又好用的东西。",
        "dialogue": [
            "「拾荒的规矩：想要就拿消耗品换。火、烟、响，管够。」",
            "「别问来路。梦里的东西没有来路，只有去处。」",
        ],
        "options": [
            {"label": "交出消耗品，换一支燃烧瓶",
             "cost": {"consumables": 3}, "gain": {"item": "molotov"}},
            {"label": "交出消耗品，换一枚雷管胶囊",
             "cost": {"consumables": 4}, "gain": {"item": "detonator_capsule"}},
            {"label": "交出消耗品，换一只蜂鸣诱饵",
             "cost": {"consumables": 2}, "gain": {"item": "buzz_lure"}},
            {"label": "交出消耗品，换一只烟雾罐",
             "cost": {"consumables": 2}, "gain": {"item": "smoke_canister"}},
            {"label": "交出一只烟雾罐，换一段灰烬里的记忆",
             "cost": {"items": ["smoke_canister", 1]}, "gain": {"insight": "灰烬记忆"}},
            {"label": "「不打扰了。」", "leave": True, "always": True},
        ],
    },
    "npc.night_pharmacist": {
        "name": "夜药剂师", "glyph": "⚱", "color": "#9ad1ff",
        "integrity": 16, "relation": "稳定意识",
        "description": "在梦的裂缝边摆摊调药的人：她的药柜抽屉里全是别人缺的东西。",
        "dialogue": [
            "「失眠的心智，透支的清醒——说吧，今晚缺哪一样？」",
            "「药钱不收梦币，收你愿意付的一切。」",
        ],
        "options": [
            # 2026-10-22（E5后续 P3）：三条「自换自损」报价（心智 10 换心智药、
            # 清醒 10 换清醒药、想象 10 换想象药）按方案改为**支付另一种资源 6 点**——
            # 补心智的收清醒度、补清醒的收想象力、补清醒+想象的收心智，形成一条
            # 闭环转换，任何一条都不再默认收取它要恢复的那种资源。
            # 与 `tamper.night_pharmacist.*` 的三个篡改片段（含代价数字）同步改动。
            {"label": "付清醒度，买苦艾糖滴",
             "cost": {"lucidity": 6}, "gain": {"item": "wormwood_pastille"}},
            {"label": "付想象力，买浓缩咖啡锭",
             "cost": {"imagination": 6}, "gain": {"item": "espresso_tablet"}},
            {"label": "付心智，买梦境电解水",
             "cost": {"mind": 6}, "gain": {"item": "dream_electrolytes"}},
            {"label": "交出消耗品，换一瓶逆行的沙漏的沙",
             "cost": {"consumables": 3}, "gain": {"stat": ["max_lucidity", 4]}},
            {"label": "交出消耗品，买一份「局部照明」的药方",
             "cost": {"consumables": 4}, "gain": {"insight": "局部照明"}},
            {"label": "「谢谢，不用。」", "leave": True, "always": True},
        ],
    },
    "npc.little_devil": {
        "name": "小魔鬼", "glyph": "♆", "color": "#ff7a4f",
        "integrity": 16, "relation": "稳定意识",
        "description": "尾巴打着节拍的小个子：合约藏在每一句玩笑里。",
        "dialogue": [
            "「呵，初次见面！做个小交易吧——拿你一件『亮闪闪的』，换我兜里的宝贝。」",
            "「放心，魔鬼的契约从不撒谎，只是从不写全。」",
        ],
        "options": [
      {"label": "交出携带意象，换命运硬币",
             "cost": {"random_gear": 2}, "gain": {"item": "fate_coin"}},
            # 「明示」与「盲盒」两条情报线：说清买的是什么就贵，不说就便宜——
            # 贵的那条按名字给（残影直觉），便宜那条给一个**随机**洞察（不给名字）。
            {"label": "付心智，买明示洞察",
             "cost": {"mind": 18}, "gain": {"insight": "残影直觉"}},
            {"label": "付心智，买随机洞察",
             "cost": {"mind": 12}, "gain": {"random_insight": True}},
            {"label": "交出消耗品，换螺丝刀",
             "cost": {"consumables": 3}, "gain": {"item": "screwdriver"}},
            {"label": "交出折叠弹影，换蜡封图章",
             "cost": {"items": ["folded_projectile", 2]}, "gain": {"item": "wax_seal"}},
            {"label": "付清醒度，换晨露药剂",
             "cost": {"lucidity": 12}, "gain": {"item": "morning_dew"}},
            # 容器交易（2026-09-19）：单种容器=少见（2 件消耗品）。
            {"label": "交出消耗品，换一只玻璃瓶（单种液体）",
             "cost": {"consumables": 2}, "gain": {"item": "glass_bottle"}},
            {"label": "交出消耗品，换一只气球（单种气体）",
             "cost": {"consumables": 2}, "gain": {"item": "balloon"}},
            # 燃烧系投掷物（2026-09-19）：使用进入投掷瞄准，点选落点。
            {"label": "交出消耗品，换一支燃烧瓶（投掷引火）",
             "cost": {"consumables": 3}, "gain": {"item": "molotov"}},
            {"label": "交出消耗品，换一枚雷管胶囊（投掷爆破）",
             "cost": {"consumables": 4}, "gain": {"item": "detonator_capsule"}},
            {"label": "「不了，谢谢。」", "leave": True, "always": True},
        ],
    },
    "npc.archivist": {
        "name": "档案员", "glyph": "§", "color": "#c8d8f0",
        "integrity": 20, "relation": "稳定意识",
        "description": "辨认之馆的登记员：她说不清自己在这里多久了，也不打算说。",
        "dialogue": [
            "「每个走进这里的人，都要去认领自己的记忆。认错了也没关系——」",
            "「馆里的规矩是：认错的人，比从不认的人，更接近清醒。」",
        ],
        "options": [
            # 三选一（2026-10-12）：认领记忆只有一次——三条共用 archivist_memory。
            {"label": "问清馆的规矩", "gift_set": "archivist_memory", "show_if": {"gift_available": "archivist_memory"}, "gain": {"item": "mint_lozenge"}},
            {"label": "替她整理一摞档案（上交 3 件消耗品）", "cost": {"consumables": 3}, "gain": {"insight": "双读"}},
            {"label": "听她讲一个借来的故事", "gift_set": "archivist_memory", "show_if": {"gift_available": "archivist_memory"}, "gain": {"item": "warm_water"}},
            {"label": "问馆里丢了什么", "gift_set": "archivist_memory", "show_if": {"gift_available": "archivist_memory"}, "gain": {"insight": "地形记忆"}},
            {"label": "只是点头致意", "leave": True, "always": True},
            {"label": "询问深层通路", "deep_dialogue": "rules", "always": True},
            {"label": "复核辨认记录", "deep_dialogue": "review", "always": True},
            {"label": "询问当前进度", "deep_dialogue": "progress", "always": True},
        ],
    },
    "npc.guide": {
        "name": "引路人", "glyph": "♨", "color": "#ffd60a",
        "integrity": 22, "relation": "稳定意识",
        "description": "站在承担之野入口的灰衣人：他举着一盏不照路、只照自己的灯。",
        "dialogue": [
            "「前面三条路，走哪条都到碑前。区别只在——」",
            "「你愿意在碑前承认什么。」",
        ],
        "options": [
            # 三选一（2026-10-12）：四条「承认」共用一个限领组——领过一条，
            # 其余三条从货架上消失（对话里「三条路走哪条都到碑前」的兑现）。
            # 夜岗那条带代价，走 gift_set 分支前会照常收费（actions 礼品分支）。
            {"label": "讨一口热水", "gift_set": "guide_road", "show_if": {"gift_available": "guide_road"}, "gain": {"item": "warm_water"}},
            {"label": "陪他站一段夜岗（上交 3 件消耗品）", "gift_set": "guide_road", "show_if": {"gift_available": "guide_road"}, "cost": {"consumables": 3}, "gain": {"insight": "深层耐性"}},
            {"label": "问灯照的是什么", "gift_set": "guide_road", "show_if": {"gift_available": "guide_road"}, "gain": {"item": "mint_lozenge"}},
            {"label": "问灯为什么照自己", "gift_set": "guide_road", "show_if": {"gift_available": "guide_road"}, "gain": {"insight": "路线依赖"}},
            {"label": "沉默走过", "leave": True, "always": True},
            {"label": "询问深层通路", "deep_dialogue": "rules", "always": True},
            {"label": "询问当前进度", "deep_dialogue": "progress", "always": True},
        ],
    },
    # ---- 2026-09-19 第三批：任务/剧情/赠品 NPC ----
    "npc.press_boy": {
        "name": "报童阿全", "glyph": "📰", "color": "#e8c84a",
        "integrity": 18, "relation": "稳定意识",
        "description": "抱着一摞空白报纸的男孩：他要印一份「醒着的报纸」。",
        "dialogue": [
            "「醒来的人看什么报？看你们这些做梦的呗！」",
            "「油墨要显影液调色。给我三份，头版就归你。」",
        ],
        "options": [
            {"label": "接取任务：头版的油墨", "accept_quest": "quest.press_ink", "show_if": {"quest_none": "quest.press_ink"}},
            {"label": "交货：显影液 ×3（要一张头版＋一份补给）", "complete_quest": "quest.press_ink", "reward": "supply", "show_if": {"quest_active": "quest.press_ink"}},
            {"label": "交货：显影液 ×3（要一次排版帮工）", "complete_quest": "quest.press_ink", "reward": "service", "show_if": {"quest_active": "quest.press_ink"}},
            {"label": "买一条行规（3 件消耗品）", "cost": {"consumables": 3}, "gain": {"insight": "灯塔共鸣"}},
            {"label": "聊聊醒着的报纸", "gift_set": "press_paper", "show_if": {"gift_available": "press_paper"}, "gain": {"item": "warm_water"}},
            {"label": "先走了", "leave": True, "always": True},
        ],
    },
    "npc.scrap_registrar": {
        "name": "拾荒协会登记员", "glyph": "▤", "color": "#a8b89a",
        "integrity": 24, "relation": "稳定意识",
        "description": "袖口磨亮的登记员：一本账、两支笔，记下每一只被解决的异象。",
        "dialogue": [
            "「协会规矩：按件计酬，凭账销账。」",
            "「账本页被纸页犬咬走了三页——你不顺手拿回来，我不认账。」",
            "「泵房那间保护区里窝了一位。当场解决也好，引出来把侧门挡板放下、连着三个回合别让它踩进去也好——两条都算数，但得先接登记单。」",
        ],
        "options": [
            {"label": "接取任务：泵房的狩猎登记", "accept_quest": "quest.pump_hunt", "show_if": {"quest_none": "quest.pump_hunt"}},
            {"label": "销账：泵房那位有了归属（要泵房使用权＋一份物资）", "complete_quest": "quest.pump_hunt", "reward": "supply", "show_if": {"quest_active": "quest.pump_hunt"}},
            {"label": "销账：泵房那位有了归属（要一次回收服务）", "complete_quest": "quest.pump_hunt", "reward": "service", "show_if": {"quest_active": "quest.pump_hunt"}},
            {"label": "接取任务：监视者的页码", "accept_quest": "quest.watcher_pages", "show_if": {"quest_none": "quest.watcher_pages"}},
            {"label": "销账：3 页协会账页（要一份线轴补给）", "complete_quest": "quest.watcher_pages", "reward": "supply", "show_if": {"quest_active": "quest.watcher_pages"}},
            {"label": "销账：3 页协会账页（要一次协会护理）", "complete_quest": "quest.watcher_pages", "reward": "service", "show_if": {"quest_active": "quest.watcher_pages"}},
            {"label": "接取任务：留灯的巡房", "accept_quest": "quest.lamp_refuge", "show_if": {"quest_none": "quest.lamp_refuge"}},
            {"label": "销账：避难圈的灯点着了（要一份补给）", "complete_quest": "quest.lamp_refuge", "reward": "supply", "show_if": {"quest_active": "quest.lamp_refuge"}},
            {"label": "销账：避难圈的灯点着了（要一次夜诊护理）", "complete_quest": "quest.lamp_refuge", "reward": "service", "show_if": {"quest_active": "quest.lamp_refuge"}},
            {"label": "随便看看", "leave": True, "always": True},
        ],
    },
    "npc.lost_found": {
        "free_claim_limit": 1,
        "name": "失物招领员", "glyph": "❑", "color": "#9ad1c9",
        "integrity": 20, "relation": "稳定意识",
        "description": "柜台后的老太太：她记得每件失物，却想不起自己的名字。",
        "dialogue": [
            "「失物认领，一件为限——这是规矩，多拿的人会忘记自己来做什么。」",
            "「挑一样吧。挑完就别回头。」",
        ],
        "options": [
            # 三选一（2026-10-12）：「一件为限」是明说的规矩——领走一件后
            # 其余两件立刻从对话里消失（此前只锁结算、不锁货架）。
            {"label": "赠品：折页影（易逝物，附赠洞察）", "gift_set": "lf_kit", "show_if": {"gift_available": "lf_kit"}, "gain": {"item": "folded_projectile", "insight": "留白"}},
            {"label": "赠品：薄荷锭（摄入物）", "gift_set": "lf_kit", "show_if": {"gift_available": "lf_kit"}, "gain": {"item": "mint_lozenge"}},
            {"label": "赠品：弯曲的挂钩（依附物）", "gift_set": "lf_kit", "show_if": {"gift_available": "lf_kit"}, "gain": {"item": "bent_hook"}},
            {"label": "听听失物的故事", "gift_set": "lf_story", "show_if": {"gift_available": "lf_story"}, "gain": {"insight": "延迟抵达"}},
            {"label": "接取任务：遗失物有名字", "accept_quest": "quest.lf_marathon", "show_if": {"quest_none": "quest.lf_marathon"}},
            {"label": "销账：物主查明了——交还失主，换一次招领服务", "complete_quest": "quest.lf_marathon", "reward": "return", "show_if": {"quest_active": "quest.lf_marathon"}},
            {"label": "销账：物主查明了——代为保管，换一条旁路情报", "complete_quest": "quest.lf_marathon", "reward": "keep", "show_if": {"quest_active": "quest.lf_marathon"}},
            {"label": "销账：物主查明了——声明占有那只瓶", "complete_quest": "quest.lf_marathon", "reward": "claim", "show_if": {"quest_active": "quest.lf_marathon"}},
            {"label": "这次不领", "leave": True, "always": True},
        ],
    },
    "npc.dream_bartender": {
        "name": "织梦酒保", "glyph": "☼", "color": "#d4a72c",
        "integrity": 22, "relation": "稳定意识",
        "description": "在梦与梦之间开酒店的调酒师：他的杯子永远温着。",
        "dialogue": [
            "「醒着的人喝酒是为了睡；你们喝酒，是为了醒。」他擦着一只永远擦不干的杯子。",
            "「早年有个常客，总坐你现在这个位置。他说他是个作家——后来他的故事连署名都丢了。」",
            "「再往深处去，别信任何替你写字的东西。它们很客气，客气得像已经替你活过一遍。」",
        ],
        "options": [
            {"label": "接取任务：一杯给醒着的人", "accept_quest": "quest.bar_wake", "show_if": {"quest_none": "quest.bar_wake"}},
            {"label": "兑现：避难点收拾好了（要避难点开放＋一份温饮）", "complete_quest": "quest.bar_wake", "reward": "supply", "show_if": {"quest_active": "quest.bar_wake"}},
            {"label": "兑现：避难点收拾好了（要一次夜班照料）", "complete_quest": "quest.bar_wake", "reward": "service", "show_if": {"quest_active": "quest.bar_wake"}},
            {"label": "用清醒换一页旧稿（清醒 −12）", "cost": {"lucidity": 12}, "gain": {"insight": "和声耐受"}},
            {"label": "问那个作家的下落", "gift_set": "bartender_writer", "show_if": {"gift_available": "bartender_writer"}, "gain": {"item": "warm_water"}},
            {"label": "今天到此为止", "leave": True, "always": True},
        ],
    },
    "npc.nameless_poet": {
        "name": "无名诗人", "glyph": "❥", "color": "#c9a0ff",
        "integrity": 16, "relation": "稳定意识",
        "description": "没有面孔的吟游者：每念一句诗，就忘掉自己的一个名字。",
        "dialogue": [
            "「梦是 Everyone 的日记，梦层是它划掉的部分。」",
            "「初啼之前没有声音，所以最深处安静。醒来之后全是声音，所以你们害怕安静。」",
            "「执笔者不是敌人。它只是比你先承认了：故事需要有人写完。」",
            "「我把名字一句一句押了韵。你若在回声里听见下半句——替我记下来。」",
        ],
        "options": [
            {"label": "接取任务：诗的下半句", "accept_quest": "quest.poet_line", "show_if": {"quest_none": "quest.poet_line"}},
            {"label": "念出回声里的下半句（要一份晨露＋他替你记下的一句）", "complete_quest": "quest.poet_line", "reward": "supply", "show_if": {"quest_active": "quest.poet_line"}},
            {"label": "念出回声里的下半句（要一次润笔）", "complete_quest": "quest.poet_line", "reward": "service", "show_if": {"quest_active": "quest.poet_line"}},
            {"label": "买他一页手稿（3 件消耗品）", "cost": {"consumables": 3}, "gain": {"item": "torn_page"}},
            {"label": "问「Everyone」是谁", "gift_set": "poet_everyone", "show_if": {"gift_available": "poet_everyone"}, "gain": {"item": "warm_water"}},
            {"label": "替他记一句诗", "gift_set": "poet_line", "show_if": {"gift_available": "poet_line"}, "gain": {"insight": "深渊回声"}},
            {"label": "静静听完", "leave": True, "always": True},
        ],
    },
    "npc.memory_pawner": {
        "name": "记忆当铺老板", "glyph": "⚖", "color": "#b8a28a",
        "integrity": 26, "relation": "稳定意识",
        "description": "当铺里挂满了贴着标签的瓶子：每瓶都是一段别人不要的记忆。",
        "dialogue": [
            "「当记忆不丢人，丢人的是当完了赎不回。」",
            "「利钱是拿上限抵的——别问我为什么，当铺的规矩比梦老。」",
        ],
        "options": [
            {"label": "当掉一段回忆（心智上限 −5）换清醒扩容", "cost": {"cap": ["max_mind", 5]}, "gain": {"stat": ["max_lucidity", 8]}},
            {"label": "当掉一段回忆（想象上限 −5）换心智扩容", "cost": {"cap": ["max_imagination", 5]}, "gain": {"stat": ["max_mind", 8]}},
            {"label": "用 3 件消耗品换定金", "cost": {"consumables": 3}, "gain": {"item": "warm_coffee", "insight": "液态亲和"}},
            {"label": "问瓶子上那些标签的来历", "gift_set": "pawner_labels", "show_if": {"gift_available": "pawner_labels"}, "gain": {"item": "mint_lozenge"}},
            {"label": "只逛逛", "leave": True, "always": True},
        ],
    },
    "npc.scavenger": {
        "name": "拾荒的委托人", "glyph": "⚑", "color": "#d8b26e",
        "integrity": 22, "relation": "稳定意识",
        "description": "背着大包裹的沉默身影：委托书写得比人话还多。",
        "dialogue": [
            "她把委托书摊在膝盖上：「下层的梦里有股味道，替我把样本带上来。」",
            "「报酬好商量。跑腿的规矩：先验货，后付账。」",
        ],
        "options": [
      {"label": "交出样本，换深念茶",
             "cost": {"consumables": 3}, "gain": {"item": "deep_thought_tea"}},
            {"label": "付清醒度，换多出的螺丝",
             "cost": {"lucidity": 10}, "gain": {"item": "model_screw"}},
            {"label": "交出携带意象，换无光斗篷",
             "cost": {"random_gear": 4}, "gain": {"item": "lightless_cloak"}},
            {"label": "付心智，换一份洞察",
             "cost": {"mind": 13}, "gain": {"insight": "疾行拾荒"}},
            {"label": "交出折叠弹影，换蜡封图章",
             "cost": {"items": ["folded_projectile", 2]}, "gain": {"item": "wax_seal"}},
            {"label": "过一会再来", "leave": True, "always": True},
        ],
    },
}
NPC_MAX_PER_LAYER = 2
NPC_TRADE_DRAW = (2, 3)
STAT_LABELS = {
    "max_mind": "心智上限",
    "max_lucidity": "清醒度上限",
    "max_imagination": "想象力上限",
    "sight": "视野",
}

# Hospital actors are authored local services, never a main-dream NPC pool.
from .hospital import HOSPITAL_NPCS
NPC_DEFINITIONS.update(HOSPITAL_NPCS)

from .library import LIBRARY_HINTS
# 每位馆员的差异化学识：两条额外问答，全部对应真实机制
# （书架可燃/推书车可推、页码机关与湿墨导电、灯光与窗口、纸堆燃料与防火面、记录与应战）。
_LIBRARY_EXTRA_DIALOGUE = (
    (('胡桃木书架挡视线也挡直线，最怕火；烧穿了，视线和弹道都跟着改道。',),
     ('推书车挪一下，遮挡跟着挪；借它打掩护，别把自己堵死。',)),
    (('错页索引柜的页码能对调；正序排好，它才肯指出收藏的位置。',),
     ('湿墨只泼在侧路上，踩了会导电；横着走索引廊，遇不上长线。',)),
    (('同一座庭院开着一排不同的窗口；换一扇窗，看到的规矩就不一样。',),
     ('黄铜阅读灯对谁都亮，敌我都算；灯体不结实，别指望它替你挡刀。',)),
    (('干纸堆是燃料，烧完就变回普通地面；防火书柱和防火石面烧不着，退路可以选它们。',),
     ('双声校勘台纯属自愿；并置两组书稿，它们会按同一阅读次序排好，给你指一条干燥回廊。',)),
    (('三份矛盾记录说的是同一件事的三个版本；都记下来，未尽目录才会认真听你说话。',),
     ('回应未尽目录就会开战。读记录不花钱；想清楚了，再去按确认。',)),
)
# 层间下潜守门提示（2026-10-14，#83/#85）：d1-d4 馆员兼任问询处；
# 第 5 层是中央誊本台所在的最深处、没有下潜，不挂这句。
LIBRARY_GATE_HINT = ('要往更深处去，得先办齐这层的手续：读一张旧借书卡，'
                     '读一段写满批注的桌角，再整理一座目录机关。')
for _i, _name in enumerate(('借阅员','索引员','窗边读者','校勘员','守页人'), 1):
    _gate_option = ({'label':'询问下潜手续','message':LIBRARY_GATE_HINT,'always':True},) if _i < 5 else ()
    NPC_DEFINITIONS[f'npc.library.{_i}'] = {
        'name':_name,'glyph':'阅','color':'#214f42','integrity':40,'relation':'稳定意识',
        'dialogue':(LIBRARY_HINTS[_i-1],), 'vault_only':True,'spawn_realms':('library_palace',),
        'options':({'label':'询问通路与规则','message':LIBRARY_HINTS[_i-1],'always':True},)
                  + _gate_option
                  + ({'label':'请教这座宫的物件','message':_LIBRARY_EXTRA_DIALOGUE[_i-1][0],'always':True},
                     {'label':'再问一句','message':_LIBRARY_EXTRA_DIALOGUE[_i-1][1],'always':True},
                     {'label':'告辞','leave':True,'always':True})}

for _i, _glyph in enumerate(("借", "索", "窗", "勘", "頁"), 1):
    NPC_DEFINITIONS[f"npc.library.{_i}"]["glyph"] = _glyph

# These questions keep their reply after the accompanying free gift is spent.
FREE_GIFT_REPLIES = {
    '问清馆的规矩': ('「借来的记忆要记着出处。东西可以带走，别把别人的名字也拿去。」',
                     'Remember where a borrowed memory came from. Take the object, but leave its owner their name.'),
    '听她讲一个借来的故事': ('「那人把故事寄存在这里，说醒来就取。可他每次来，都忘了自己寄存过。」',
                           'Someone left a story here to collect upon waking. Every time they return, they forget they left it.'),
    '问馆里丢了什么': ('「少的不是书，是读过它们的人留下的那一页记忆。」',
                       'We are missing the memories readers left between the pages, rather than the books.'),
    '问灯照的是什么': ('「照的是你还肯承认的东西。路在前面，灯只陪你站一会儿。」',
                       'It lights what you can still acknowledge. The road lies ahead; the lamp keeps you company here.'),
    '问灯为什么照自己': ('「给别人指路之前，总得看清自己站在哪里。」',
                         'Before showing someone the way, I need to see where I stand.'),
    '聊聊醒着的报纸': ('「报纸睡着了，字就会顺着折痕跑掉。我守着它们，等下一位读者来。」',
                       'When a newspaper sleeps, its words escape along the folds. I keep watch until another reader arrives.'),
    '听听失物的故事': ('「柜子里每样东西都记得主人。只有我，记不起自己叫什么。」',
                       'Every object in these drawers remembers its owner. Only I have forgotten my name.'),
    '问那个作家的下落': ('「他最后留下的只有一页没署名的稿子。再往深处找，要认他的笔迹。」',
                       'He left an unsigned page. If you look deeper, remember his handwriting.'),
    '问「Everyone」是谁': ('「我念得出这个名字，却想不起它指向谁。梦里有许多人，都像替它写过一句。」',
                         'I can speak that name but cannot remember who it belongs to. Many dreamers seem to have written a line for it.'),
    '替他记一句诗': ('「名字会忘，押过韵的半句却会留下。你在回声里听见它，就替我接下去。」',
                     'Names fade, but half a rhyme lingers. If you hear it in an echo, finish the line for me.'),
    '问瓶子上那些标签的来历': ('「每张标签都来自寄存的人。名字写在外头，舍不得的东西装在里面。」',
                             'Each label came from the person who left it here. Their name stays outside; what they could not part with stays inside.'),
}
EN_NPC_GIFT_REPLIES = {zh: en for zh, en in FREE_GIFT_REPLIES.values()}
for _npc in NPC_DEFINITIONS.values():
    for _option in _npc.get('options', ()):
        if _option.get('gift_set') and not _option.get('cost') and _option['label'] in FREE_GIFT_REPLIES:
            _option['message'] = FREE_GIFT_REPLIES[_option['label']][0]
