"""消耗品（易逝物）：一次性使用或投掷。"""

from __future__ import annotations

from typing import Any

ITEMS = {
    "impact_fold": {
        "name": "冲击折页", "category": "易逝物",
        "rarity": "少见", "flammable": True,
        "description": "折页绷得很紧，纸缝里藏着一阵没吹出来的风。掷到落点才炸：半径 2 内造成创伤并把目标推开一格，削薄坚实聚合物、引燃可燃材料；自己站在半径里照样挨一下清醒创伤。", "color": "bright_red",
        "effect": "explosion", "power": 3, "explosion_radius": 2, "max_stack": 2,
    },
    "blue_match": {
        "name": "火柴的蓝端", "category": "易逝物",
        "rarity": "常见",
        "description": "点燃一格液态记忆或高浓度弥散印象。", "color": "bright_red", "effect": "ignite",
        "max_stack": 3, "flammable": True,
    },
    "battery_back": {
        "name": "电池的背面", "category": "易逝物",
        "rarity": "少见",
        "description": "借脚下水、导电液态记忆或金属地面的电压，沿四邻连通的介质放电：最远四格、最多二十格，被击中的失控意识这一拍慢一步。余电在介质上停留五回合，谁踩上算谁的——自己也及时离开。", "color": "bright_yellow", "effect": "shock", "power": 2, "max_stack": 3,
    },
    "folded_projectile": {
        "name": "折叠弹影", "category": "易逝物",
        "rarity": "常见",
        "description": "展开后只能维持一次发射。", "color": "bright_magenta",
        "effect": "projectile_charge", "power": 1, "max_stack": 5,
    },
    "clear_glass": {
        "name": "一小片清醒玻璃", "category": "易逝物",
        "rarity": "常见",
        "description": "短暂固定远处的形状。", "color": "bright_cyan", "effect": "restore_lucidity", "power": 10, "max_stack": 2,
    },
    "old_keycap": {
        "name": "脱落的键帽", "category": "易逝物",
        "rarity": "常见",
        # 2026-10-22（P3）：从「一发聚合弹」改成「三格内远程按一次机关」——
        # `power` 现在是够得着的格数（原本是弹量 1）。
        "description": "按下它，三格内看得见的一个机关就替你先动一次。",
        "color": "bright_magenta", "effect": "remote_switch", "power": 3, "max_stack": 5,
    },
    "wet_fold": {
        "name": "湿折页", "category": "易逝物",
        "rarity": "常见",
        "description": "贴着液面滑行，一段直线不再耗时。", "color": "bright_blue",
        "effect": "liquid_step", "power": 3, "max_stack": 3,
    },
    "hollow_step": {
        "name": "空心的台阶", "category": "易逝物",
        "rarity": "少见",
        "description": "踩上去会落空一个行动，崩解度也随之松了一点。", "color": "bright_white",
        "effect": "skip_turn", "power": 2, "max_stack": 2,
    },
    "double_frame": {
        "name": "双重曝光底片", "category": "易逝物",
        "rarity": "非常稀有",
        # 2026-10-22（P3）：只存 1 次，且 5 回合内不用就褪（`free_action_turns`）。
        "description": "两次成像叠在同一格里：下一个正式动作不消耗时间，但只存一次、5 回合内没用就褪。",
        "color": "bright_magenta",
        "effect": "free_action", "free_action_turns": 5, "max_stack": 1, "flammable": True,
    },
    "molotov": {
        "name": "燃烧瓶", "category": "易逝物", "rarity": "少见",
        "description": "瓶颈塞着布条的油瓶。使用就是投掷：落点十字五格先泼上燃油再一起点着，斜角四格只烧本来就可燃的——整片 3×3 火海。已有液体的地面不另铺油，防火层点不着。",
        "color": "bright_red", "effect": "fireburst", "power": 4, "max_stack": 2,
    },
    "detonator_capsule": {
        "name": "雷管胶囊", "category": "易逝物", "rarity": "稀有",
        "description": "胶囊在指缝间微微发烫，像一颗急着出生的雷。掷出即可引爆；爆破扳指能撑大它的脾气。",
        "color": "bright_red", "effect": "explosion", "power": 4, "explosion_radius": 2, "max_stack": 2,
    },
    "charge_clip": {
        "name": "聚合弹匣", "category": "易逝物", "rarity": "少见",
        "description": "五枚压好的聚合弹，拍进掌心就能感到发射许可在皮肤下发烫。聚合弹 +5。",
        "color": "bright_yellow", "effect": "projectile_charge", "power": 5,
    },
    "sparkler_bundle": {
        "name": "烟花束", "category": "易逝物", "rarity": "少见",
        # 2026-10-22（P3 战术分工）：不再与燃烧瓶共用 3×3 火场＋铺油。
        # 改为落点向八方向各抛火星，最远 3 格，遇墙即止；强度 6 保留。
        "description": "一把绑在一起的仙女棒。掷出去向八个方向各抛一束火星，最远三格——它不铺火海，是一条条烧过去。",
        "color": "bright_magenta", "effect": "spark_rays", "power": 6, "max_stack": 2, "flammable": True,
    },
    "micro_detonator": {
        "name": "微型雷管", "category": "易逝物", "rarity": "常见",
        "description": "迷你版雷管：威力小些，胜在便宜、常见、舍得扔。",
        "color": "bright_red", "effect": "explosion", "power": 2, "explosion_radius": 1, "max_stack": 3,
    },
    "tar_bomb": {
        "name": "焦油燃烧弹", "category": "易逝物", "rarity": "少见",
        # 2026-10-22（P3）：独立效果 `tar_burst`——十字燃油 60 分三批淌出（每批 20），
        # 火更匀更久，但不额外加伤害。
        "description": "掺了焦油的燃烧弹，火更黏、更久、更不讲道理：十字上会分三批淌出燃油，一批二十。",
        "color": "bright_red", "effect": "tar_burst", "power": 5, "max_stack": 2, "flammable": True,
    },
    "double_smoke": {
        "name": "烟雾双联罐", "category": "易逝物", "rarity": "少见",
        # 2026-10-22（P3）：不再一次扔出 80 点烟，而是两只罐头各投一次、
        # 各花一次行动（`deploy_charges=2` + 单罐 40）——两次落点可以分开选。
        "description": "两只烟雾罐用胶带缠成一枚：一次投掷只放一只，另一只留在手里，想放的时候再花一次行动。",
        "color": "grey70", "effect": "smoke_cloud", "power": 40,
        "deploy_charges": 2, "max_stack": 2,
    },
    "jumbo_charge_clip": {
        "name": "聚合弹匣·大", "category": "易逝物", "rarity": "稀有",
        "description": "十枚聚合弹排得整整齐齐，像一排等着被念出的名字。聚合弹 +10。",
        "color": "bright_yellow", "effect": "projectile_charge", "power": 10,
    },
    "arc_bolt": {
        "name": "电弧弹", "category": "易逝物", "rarity": "稀有",
        "description": "一发裹着电弧的直线弹：沿路途烙过去，撞上导电介质就接通一片电场。",
        "color": "bright_white", "effect": "fire_once", "payload": "arc",
        "power": 3, "max_stack": 2,
    },
    "buzz_lure": {
        "name": "蜂鸣诱饵", "category": "易逝物", "rarity": "少见",
        "description": "捏一下就嗡嗡作响的铁皮虫。扔出去落地即响，第 3、6 回合各再响一次：半径内的异象都会循声扑向响处——包括你想支开的那只。",
        "color": "bright_green", "effect": "sound_lure", "max_stack": 2,
    },
    "smoke_canister": {
        "name": "烟雾罐", "category": "易逝物", "rarity": "少见",
        "description": "拉环一拔就滚滚冒烟的罐头。扔到哪儿，哪儿就糊上一团浓黑的弥散印象——看不清的地方，梦也认不出你。",
        "color": "grey70", "effect": "smoke_cloud", "power": 40, "max_stack": 2,
    },
    "flare_bolt": {
        "name": "光焰弹", "category": "易逝物", "rarity": "少见",
        "description": "装填后沿直线飞出：撞上第一个障碍或意识体便尝试点燃该格可燃材料，烧成一小片光。缺燃料时只闪一下，不承诺持续火场。",
        "color": "bright_red", "effect": "fire_once", "payload": "flare",
        "power": 2, "max_stack": 2, "flammable": True,
    },
    "loose_thread": {
        "name": "松脱的缝线", "category": "易逝物",
        "rarity": "常见",
        "description": "顺着它走一步，梦还没来得及记下时间。", "color": "bright_white",
        "effect": "free_step", "max_stack": 3, "flammable": True,
    },
    "spellbook": {
        "name": "破损的书卷", "category": "易逝物", "icon": "📚",
        "rarity": "稀有",
        "description": "从最多三个未习得的通用构想中选择一个永久习得。可查看完整效果、想象力费用与冷却；取消不消耗。全部习得后恢复10点想象力。",
        "color": "bright_yellow", "effect": "learn_ability", "max_stack": 2, "flammable": True,
    },
    "torn_page": {
        "name": "断裂的残页", "category": "易逝物", "icon": "📜",
        "rarity": "少见",
        "description": "随机永久习得一个未习得的通用构想。全部习得后恢复10点想象力。",
        "color": "bright_white", "effect": "learn_ability", "max_stack": 3, "flammable": True,
    },
    # ---- 梦中梦·千禧园（2026-10-10，docs/millennium-garden-design.md §11）----
    "pixel_scrap": {
        "name": "像素碎片", "category": "易逝物",
        "rarity": "常见",
        "description": "千禧园里散落的坏点。拼起来，还能看见一点旧日的安稳。",
        "color": "bright_cyan", "effect": "restore_mind", "power": 2, "max_stack": 5,
    },
    "dial_tone": {
        "name": "拨号音", "category": "易逝物",
        "rarity": "少见",
        "description": "调制解调器的握手音。听一会儿，紧绷的神经松开了。",
        "color": "bright_green", "effect": "restore_mind", "power": 8, "max_stack": 2,
    },
    "screensaver_soda": {
        "name": "屏保气泡水", "category": "易逝物",
        "rarity": "少见",
        "description": "喝下去，气泡从脊椎往上飘——清醒 +11。",
        "color": "bright_cyan", "effect": "restore_lucidity", "power": 11, "max_stack": 2,
    },
    "modem_56k": {
        "name": "56k 猫", "category": "易逝物",
        "rarity": "稀有",
        "description": "完成握手后，8 回合内行动耗时 ×0.8，随后 4 回合 ×1.2；期间不能再次启动，不刷新构想冷却。",
        "color": "bright_white", "effect": "modem_buffer", "power": 0, "max_stack": 1,
        # §4.2（2026-10-22 收口）：跨渠道（事件／位面柜子／掉落／NPC 赠品）合计每局最多 1 份；
        # 位面实例更细的「每次实例 1 份」留待专属奖励接线时再收窄。
        "run_limit": 1,
    },
}
