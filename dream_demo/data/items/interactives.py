"""交互道具：瞄准投掷/喷射附件/特殊机关。"""

from __future__ import annotations

from typing import Any

ITEMS = {
    # 内容扩展包 v1（2026-09-20）：融蜡花的拔除产物——一管可燃的熔融蜡烛，
    # 掷出后引燃落点（复用投掷引燃管线，与镁条火柴一族）。
    # ---- 梦中梦·门之回廊（2026-09-21）----
    # 门之钥：累计击败 20 个强烈异象掉落；使用进入「门之回廊」，不消耗。
    "door_key": {
        "name": "门之钥", "category": "交互道具", "color": "#c0d8f0",
        "description": "冰冷的钥匙，齿痕像一排合拢的门。使用它，走进不存在的门。",
        "effect": "enter_realm", "power": 3, "rarity": "非常稀有", "realm_id": "door_corridor",
    },
    # 引火人的火柴（2026-10-08）：余烬廊桥的保底火源。进层授予、出层回收，
    # 非消耗、不入任何掉落池；使用点燃 8 邻域内的可燃材料（不燃则拒绝、不耗行动）。
    "lighter_match": {
        "name": "引火人的火柴", "category": "交互道具", "rarity": "非常稀有", "loot": False,
        "description": "擦一下，你近旁的可燃物就烧起来。火焰会顺着燃料一路爬下去，浓气被引到就炸开。",
        "color": "#ffb060", "effect": "realm_igniter", "power": 3,
    },
    "molten_candle": {
        "name": "熔融蜡烛", "category": "易逝物", "color": "#f5e8b8",
        "description": "还温热的一管烛泪。使用即进入投掷瞄准：落点十字五格里，本来就可燃的格子被点着，干净的地板不会自己烧起来；高浓度可燃气会被引爆。",
        "effect": "ignite_burst", "power": 2, "max_stack": 3, "rarity": "少见",
    },
    "whistle": {
        "name": "汽笛", "category": "交互道具", "rarity": "少见",
        "description": "一声长鸣把附近的梦都引向声源；近处的则被震住一回合。", "color": "bright_red",
        "effect": "blast_lure", "power": 8, "max_stack": 2,
    },
    "flash_bulb": {
        "name": "闪光灯泡", "category": "交互道具", "rarity": "常见",
        "description": "5 格内、且真能看见这束光的失控意识视距减半：墙挡住的不会被闪，贴得近的也仍能看见你——这是削弱视野，不是隐身。",
        "color": "bright_white", "effect": "blind", "power": 5, "max_stack": 2,
    },
    "soap_film": {
        "name": "肥皂片", "category": "交互道具", "rarity": "常见",
        "description": "把脚下的格子擦得比诚实还滑。", "color": "bright_blue",
        "effect": "slick", "max_stack": 3,
    },
    "thermal_residue": {
        "name": "保温杯的余热", "category": "交互道具", "rarity": "少见",
        "description": "最后一点温度刚好够点燃邻居。", "color": "bright_red",
        "effect": "ignite_liquid", "power": 2, "max_stack": 2,
    },
    "clockwork_half": {
        "name": "发条半卷", "category": "交互道具", "rarity": "常见",
        # 2026-10-22（P3 战术分工）：与千梦铃原先同效（都是 3 格／5 回合）。
        # 半卷＝拧到一半，只慢 3 回合；千梦铃改走真实声路（见 slow_ring）。
        "description": "拧到一半的发条，把附近的梦拖进慢放：3 格内的失控意识慢 3 回合。",
        "color": "bright_yellow",
        "effect": "slow_burst", "power": 3, "slow_turns": 3, "max_stack": 3,
    },
    "coiled_spring": {
        "name": "弹簧折叠件", "category": "交互道具", "rarity": "少见",
        "description": "贴身释放，把相邻的目标连同撞墙的代价一起送走。", "color": "bright_yellow",
        "effect": "knockback", "power": 3, "max_stack": 3,
    },
    "mirror_shard": {
        "name": "镜面碎片", "category": "交互道具",
        # 2026-10-22（P3 第二轮）：一片只能架 8 回合，到点自己碎掉（`parry_turns`）。
        # 之前没有期限，等于持有一片即常驻减伤。
        "description": "架在身前，8 回合内下一次指向你的打击会被原路退回。",
        "color": "bright_cyan",
        "effect": "parry", "parry_turns": 8, "max_stack": 1,
    },
    "magnesium_match": {
        "name": "镁光火柴", "category": "交互道具",
        "description": "烧起来白得刺眼的镁条：使用即进入投掷瞄准，落点十字五格点燃本来就可燃的材料；也可在物品菜单里选「原地点燃」，不经瞄准直接在脚下释放——脚下有燃料时，你自己也站在那片火中央。高浓度可燃气会被引爆。",
        "color": "bright_yellow", "effect": "ignite_burst", "power": 3, "max_stack": 3, "flammable": True,
    },
    "glass_bottle": {
        "name": "玻璃瓶", "category": "交互道具", "icon": "🧪", "rarity": "少见", "loot": False,
        "description": "一只耐热的空瓶，瓶口还留着上一位使用者的指纹。盛一种液态记忆，至多二十五点，倒在任何你想倒的地方。",
        "color": "bright_cyan", "effect": "container",
        "container": {"medium": "liquid", "multi": False, "cap": 25},
    },
    "ideal_tube": {
        "name": "理想试管", "category": "交互道具", "icon": "⚗", "rarity": "非常稀有", "loot": False,
        "description": "管腔彼此隔开，像几段互不打听的心事。多种液态记忆可同时盛放而互不沾染，合计二十五点，倒出时先后由你。",
        "color": "bright_cyan", "effect": "container",
        "container": {"medium": "liquid", "multi": True, "cap": 25},
    },
    "balloon": {
        "name": "气球", "category": "交互道具", "icon": "🎈", "rarity": "少见", "loot": False,
        "description": "气球绷得紧紧的，里面关着一口抓来的弥散印象——至多二十五点。解开扎口，它就回到你想让它去的地方。",
        "color": "bright_red", "effect": "container",
        "container": {"medium": "gas", "multi": False, "cap": 25},
    },
    "mirror_of_insight": {
        "name": "洞察之镜", "category": "交互道具", "rarity": "非常稀有", "icon": "🪞", "loot": False,
        "description": "核心执念崩解时凝成的小镜。照一照，镜中会浮现三种你可能成为的领悟——选一种留下，镜子随之碎裂。",
        "color": "bright_magenta", "effect": "mirror_insight",
    },
    "ideal_vessel": {
        "name": "理想气体容器", "category": "交互道具", "icon": "🫙", "rarity": "非常稀有", "loot": False,
        "description": "内胆一层隔一层，各装各的气，谁也不碰谁。合计二十五点，放气时一次一种，次序由你。",
        "color": "bright_red", "effect": "container",
        "container": {"medium": "gas", "multi": True, "cap": 25},
    },
    "signal_flare": {
        "name": "信号焰火", "category": "交互道具", "rarity": "少见",
        "description": "撕开封纸的一瞬，光把整片视野填满：此刻你看得见的敌对意识都会被晃得视距减半，五回合才缓过来。墙后面的不受影响，近处的仍能看见你。",
        "color": "bright_red", "effect": "blind", "power": 6, "blind_scope": "sight",
        "max_stack": 2, "flammable": True,
    },
    "void_coagulant": {
        "name": "虚空阻凝剂", "category": "交互道具",
        "description": "凝固被虚空泡软的念头：清除噩梦、虚无与遗忘。",
        "color": "bright_white", "effect": "purge_void", "max_stack": 2,
    },
    "night_lantern": {
        "name": "无光灯笼", "category": "交互道具",
        "description": "在无光处点亮一片：以自身为中心半径 4 的地形永久显影。",
        "color": "bright_yellow", "effect": "develop_radius", "power": 4, "max_stack": 2,
    },
    "lighthouse_ember": {
        "name": "灯塔的余烬", "category": "交互道具",
        "description": "空心灯塔熄灭前留下的那撮火。以自身为中心半径 7 的地形永久显影。",
        "color": "bright_yellow", "effect": "develop_radius", "power": 7, "max_stack": 1,
    },
    "glass_shard": {
        # 2026-10-26（平衡审计 §11.5）：power 5 → 6。半径 5 与常见件闪光灯泡
        # 完全同值，少见档买到的却是同一束光。抬到 6 格后与同为少见的信号焰火
        # 分工：焰火不限量程（blind_scope=sight），碎片是 6 格近旁闪光。
        # 稀有度不动——植物采集物（薄荷露/熔烛/鼠尾草粉）统一在少见档。
        "name": "彩玻碎片", "category": "交互道具", "rarity": "少见",
        "description": "彩玻菌的碎壳：6 格内真能看见这束光的失控意识视距减半，共五回合，墙挡住的不会被闪。",
        "color": "bright_magenta", "effect": "blind", "power": 6, "max_stack": 2,
    },
    "dream_bell": {
        "name": "千梦铃", "category": "交互道具", "rarity": "稀有",
        # 2026-10-22（P3 战术分工）：不再与发条半卷同效。铃声按**真实声路**
        # 传播（墙体衰减、听觉上限、阈值），声径 10，慢 5 回合。
        "description": "摇响它，一千个梦同时慢下来：铃声传得到的地方，失控意识慢 5 回合。",
        "color": "bright_white", "effect": "slow_ring", "power": 10, "slow_turns": 5,
        "max_stack": 2,
    },
}
