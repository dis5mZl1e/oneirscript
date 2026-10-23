"""环境条件场景定义（重构方案 §9／§10.1）。

条件与效果都写成**数据**，由 :mod:`dream_demo.world.scenes` 的固定解释器执行：定义里
不允许出现任意 Python 表达式，也不能凭文字声称一个地图上不会发生的改变。这样面板
说明、结算校验与数值探针读的是同一份结构（§10.1「禁止另写一套会与实际逻辑不一致的
文案」）。

每张场景同时声明：

* ``footprint`` 与 ``keys`` —— 布局原点之上的锚点／边槽／作用区／旁路（相对坐标）。
* ``anchor`` —— 面板事件与事实上报挂在哪一个布局键上；解释器因此不需要认识
  具体场景的键名，新增一族场景只改数据。
* ``facility`` —— 有界资源与生命周期参数（自带燃料、期限、冷却世界回合）。
* ``conditions`` —— 这处设施「能不能用」的公开条件，面板照此列出已满足项与缺口。
* ``commands`` —— 玩家能下的有限命令：每条带自己的已知条件、代价、效果与状态去向。

设施一落地就是「休眠」——玩家还没看见它之前不该能被操作，所以初始状态由引擎决定，
不在定义里另写一份。
"""

from __future__ import annotations

from typing import Any

#: 场景所属的功能族（§8 的归类；旧事件短名逐批迁到这里）。
SCENE_FAMILIES: dict[str, str] = {
    "S01": "候车与旁路",
    "S03": "配对折页点",
    "S06": "声源与广播",
    "S09": "档案辨认",
    "S10": "渠道与浮桥",
    "S11": "火种与回收",
    "S14": "夜诊庇护",
    "S23": "青灯入口",
}

#: 条件原语白名单（§10.1「可组合但有限」）。新增类型必须同时补解释器与回归用例。
CONDITION_TYPES = frozenset({
    "player_near",        # 玩家与锚点（单格或区域）的切比雪夫距离
    "anchor_flame",       # 指定锚点格的火焰强度
    "anchor_flammable",   # 指定锚点格此刻点不点得着（读既有可燃规则）
    "anchor_liquid",      # 指定锚点格的液体种类与储量
    "slot_fuel",          # 区域里还有燃料的格子数
    "zone_flammable",     # 作用区里还接得住火的格子数
    "zone_flame",         # 作用区当前正在烧的格子数
    "stock",              # 设施材料储量达到／低于阈值
    "facility_state_in",  # 设施处于给定状态之一
    "facility_ready",     # 冷却已过（世界时刻）
    "outlet_open",        # 区域内没有实心阻挡
    "blockage_present",   # 区域内有可移动的地上物
    "no_zone_hazard",     # 区域内没有火与气
    "carries_item",       # 行囊里有指定物品
    "listener_audible",   # 锚点周围有听得见的失控意识（读敌人的真实察觉规则）
    "end_primed",         # 配对设施的一端是否已被玩家分别激活（§9 R04）
    "zone_occupants",     # 作用区里还站着多少失控意识（读真实占位，不读任务标记）
    "opening_sealed",     # 指定那格现在是不是一道落下来的挡板（读真实固体）
    "flag_set",           # 设施记录里具名的开关是否已经立住（§9 S01 标出的旁路／中继权限）
})

#: 效果命令白名单（§10.3「不能由事件模块另写一套伤害公式」）。
#: 每种效果只能落到注释标出的既有公共结算入口上。
EFFECT_TYPES = frozenset({
    "ignite_anchor",      # → GameState._ignite_cell
    "ignite_zone",        # → GameState._ignite_cell（逐格，经「预告」延迟落地）
    "quench_anchor",      # → GameState._set_flame（只灭火，不改地形）
    "priming_zone",       # → 重铺可燃地面 + 地形增量（装料）
    "release_liquid",     # → GameState._add_liquid（只搬运真实储量）
    "transfer_stock",     # → FacilityRecord.stock 内部转移
    "clear_blockage",     # → 把地上物搬到区域外的空格
    "gain_item",          # → GameState._add_inventory_item
    "sound_pulse",        # → GameState._sound_pulse（只改真实听觉与追击计划，不自写诱导规则）
    "prime_end",          # → core.scenes.set_floor_variant + FacilityRecord.flags（折稳一端）
    "fold_travel",        # → core.scenes.fold_player（只做既有「进入一格」落地结算，不另写移动）
    "seal_opening",       # → core.scenes.seal_opening（门洞落成实心挡板，走既有墙体材料定义）
    "mark_route",         # → core.scenes.set_floor_variant（把一条路真的标在地上，并立起具名开关）
    "open_gate",          # → 设施记录 flags（嵌透镜→「等待支付」；祭品结算交给 confirm_gate_offering）
    "enter_gate",         # → GameState.enter_realm（真正走进位面，不另写一套进入规则）
    "light_lamp",         # → core.scenes.set_floor_variant（点亮留灯＝改环线地面＋立 ``lit`` 开关）
    "grant_rest",         # → GameState 部分回复（min(max_stat, stat+amount)，带上限）
    "repair_opening",     # → core.scenes.unseal_opening（抬起侧门挡板，与 seal_opening 对称）
    "report_clue",        # → 设施记录 flags + facts.report（§7.1 模板 5 的调查线索，不改地图）
})

#: 设施生命周期（§10.2）。
FACILITY_STATES = ("休眠", "可激活", "预告", "生效", "冷却", "耗尽")

#: 青灯入口（§8 S23）专用的门态：一次性通道不套「燃料—冷却」那条曲线，而是
#: 把「付没付、进没进、关没关」写成显式状态，取代旧事件 uses=999 的伪装状态机。
#: ``FacilityRecord.state`` 存的就是这些名字，``refresh`` 按记录开关与世界事实重算。
GATE_STATES = ("未开启", "等待支付", "开启", "已进入", "已关闭")

#: 一次设施操作允许排队的效果命令上限（§13.4 首版）。
MAX_COMMANDS_PER_SETTLEMENT = 64

#: 全部命令共用的前置：没亲眼见过的设施（休眠）与已经烧空的设施（耗尽）都不接受操作。
OPERABLE = {"type": "facility_state_in", "states": ("可激活", "预告", "生效", "冷却")}
#: 装料类命令的例外：玩家带着材料时，「空了」正是该往里填的时候。休眠仍然排除——
#: 没见过的设施不接受任何东西；但把耗尽锁死会让备料路线变成一句永远按不下去的按钮。
OPERABLE_REFILL = {"type": "facility_state_in",
                   "states": ("可激活", "预告", "生效", "冷却", "耗尽")}

SCENE_DEFINITIONS: dict[str, dict[str, Any]] = {
    # ---------------------------------------------------------------- R01
    "scene.ember_ward": {
        "definition_id": "scene.ember_ward",
        "family": "S11",
        "name": "借火的小术阵",
        "description": "浅槽围着填了干纸的火盆，两处边槽还压着燃料；外侧一条不燃的地面绕开整座院子。",
        "clue": "槽边刻着一行：先有火，再谈阵。",
        "footprint": (9, 7),
        # 主梦前中段的低风险「条件→行动→地图改变」样板（§12.1）。
        "depths": tuple(range(1, 15)),
        "keys": {
            "hearth": (4, 2),
            "fuel_slots": ((1, 2), (7, 2)),
            "ward": {"center": (4, 2), "radius": 1},
            "bypass": {"row": 6},
        },
        "anchor": "hearth",
        # 生成期的地形改造（由 core/scenes.py 落到格子上）：变体名必须是
        # materials/floors.py 里真实存在的地板；``fuel`` 是可燃地面的燃料量，
        # 按既有燃烧规则每回合 −3，所以 12 点＝最多 4 回合（§10.2）。
        "terrain": {
            "hearth": {"variant": "书页地", "fuel": 12},
            "fuel_slots": {"variant": "书页地", "fuel": 12},
            "ward": {"variant": "书页地", "fuel": 12},
            "bypass": {"variant": "绝热层"},
        },
        "facility": {
            # 自带一次绘制燃料；现场燃料仓最多再支持一次，取走就没有第二次。
            "stock": {"ward": 1, "reserve": 1},
            "effect_rounds": 4,
            "cooldown_rounds": 6,
            # 火场作用区的布局键：过期时按这一片格子判「还在烧」，并把烧完的
            # 地面记成地形增量（「烧完的地面不会自己长回来」要能穿过远层重建）。
            "zone_key": "ward",
        },
        "conditions": (
            {"type": "player_near", "key": "hearth", "radius": 3},
            {"type": "anchor_flame", "key": "hearth", "min": 1},
            {"type": "slot_fuel", "key": "fuel_slots", "min": 1},
        ),
        "commands": (
            {
                "command": "light",
                "label": "借火：把火盆点亮",
                "detail": "花一点想象力引槽里的干纸。旁边已有火源时火会自己爬过来，不必花这一笔。",
                "cost": {"imagination": 2},
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "hearth", "radius": 1},
                    {"type": "anchor_flame", "key": "hearth", "max": 0},
                ),
                "effect": {"type": "ignite_anchor", "key": "hearth", "strength": 4},
            },
            {
                "command": "activate",
                "label": "启动术阵（预警一个行动后成火场）",
                "detail": "作用区在下一个实际行动后一起烧起来：干纸的燃料够撑 4 回合，之后余火还会自己拖几回合才熄；烧完的地面不会自己长回来。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "hearth", "radius": 3},
                    {"type": "anchor_flame", "key": "hearth", "min": 1},
                    {"type": "slot_fuel", "key": "fuel_slots", "min": 1},
                    {"type": "zone_flammable", "key": "ward", "min": 1},
                    {"type": "stock", "name": "ward", "min": 1},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "ignite_zone", "key": "ward", "strength": 4},
                "spends": {"ward": 1},
                "state_after": "预告",
            },
            {
                "command": "load_fuel",
                "label": "把燃料仓的干纸重新铺进术阵",
                "detail": "地面烧成灰之后，只有装料才能再画一次。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "hearth", "radius": 2},
                    {"type": "stock", "name": "reserve", "min": 1},
                    {"type": "zone_flammable", "key": "ward", "max": 0},
                    {"type": "zone_flame", "key": "ward", "max": 0},
                ),
                "effect": {"type": "priming_zone", "key": "ward", "variant": "书页地", "fuel": 12},
                "gives": {"reserve": -1, "ward": 1},
            },
            {
                "command": "take_fuel",
                "label": "取走燃料仓里的干纸",
                "detail": "带走就失去第二次用量——换两件能塞进别处的东西。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "hearth", "radius": 2},
                    {"type": "stock", "name": "reserve", "min": 1},
                ),
                "effect": {"type": "gain_item", "item": "torn_page", "count": 2},
                "gives": {"reserve": -1},
            },
            {
                "command": "add_fuel",
                "label": "把行囊里的残页塞进燃料仓",
                "detail": "一张残页够画一次。",
                "cost": {"items": ("torn_page", 1)},
                "conditions": (
                    OPERABLE_REFILL,
                    {"type": "player_near", "key": "hearth", "radius": 2},
                    {"type": "carries_item", "item": "torn_page", "min": 1},
                    {"type": "stock", "name": "reserve", "max": 0},
                ),
                "effect": {"type": "transfer_stock", "name": "reserve", "amount": 1},
            },
            {
                "command": "quench",
                "label": "踩熄火盆里的火",
                "detail": "想让这条线安静下来时，随时可以。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "hearth", "radius": 1},
                    {"type": "anchor_flame", "key": "hearth", "min": 1},
                ),
                "effect": {"type": "quench_anchor", "key": "hearth"},
            },
        ),
    },
    # ---------------------------------------------------------------- R02
    "scene.tide_basin": {
        "definition_id": "scene.tide_basin",
        "family": "S10",
        "name": "引潮的低盆",
        "description": "一只浅盆接着两条低槽，槽口通向一片排放区；上游阀门还剩多少看得见。",
        "clue": "阀体上刻着余量：放水之前先数一数盆里有多少。",
        "footprint": (7, 7),
        "depths": tuple(range(2, 15)),
        "keys": {
            "basin": (3, 2),
            "valve": (3, 0),
            "channels": ((3, 3), (3, 4)),
            "discharge": {"center": (3, 5), "size": (3, 3)},
        },
        "anchor": "basin",
        # 盆面粗糙（拖住倒进来的水，让它留在盆里可见），低槽与排放区光滑
        # （金属聚合物把流动预算放大，水自己铺开）——两处的差别就是「盆→区」
        # 这条水路在地图上看得出来的理由。
        "terrain": {
            "basin": {"variant": "粗糙聚合物"},
            "channels": {"variant": "金属聚合物"},
            "discharge": {"variant": "金属聚合物"},
        },
        # 排放区开局堆一件可搬动的杂物：不搬开就没有「排放区通着」。
        "blockage": {"item": "glass_bottle", "key": "discharge"},
        "facility": {
            # 管道余量是「上游阀」这条路的唯一来源——不打开阀门就没有凭空的水。
            # 冷却只有一回合级别：水在盆里活不过十来世界回合，六回合的开关会把
            # 「开阀两次 → 开闸交付」这条唯一通路拖死。
            "stock": {"pipe": 6},
            "effect_rounds": 0,
            "cooldown_rounds": 2,
            "allowed_liquids": ("水",),
        },
        "conditions": (
            {"type": "player_near", "key": "basin", "radius": 3},
            {"type": "anchor_liquid", "key": "basin", "min": 4},
            {"type": "outlet_open", "key": "discharge"},
        ),
        "commands": (
            {
                "command": "open_valve",
                "label": "打开上游阀（3 单位进盆）",
                "detail": "管道里只剩这些：开一次给 3 单位，开关冷却 2 世界回合。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "valve", "radius": 1},
                    {"type": "stock", "name": "pipe", "min": 3},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "release_liquid", "from_stock": "pipe",
                           "to_key": "basin", "units": 3, "kind": "水"},
                "spends": {"pipe": 3},
                "state_after": "冷却",
            },
            {
                "command": "clear_blockage",
                "label": "把排放区里的挡路物搬到外面",
                "detail": "可移动的杂物搬开，水路才算通——它还在地图上，只是不堵着了。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "discharge", "radius": 2},
                    {"type": "blockage_present", "key": "discharge"},
                ),
                "effect": {"type": "clear_blockage", "key": "discharge"},
            },
            {
                "command": "release",
                "label": "开闸：把盆里的水放进排放区",
                "detail": "至多 6 单位，按盆里实有的量给；水面按既有规则自己铺开。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "basin", "radius": 2},
                    {"type": "anchor_liquid", "key": "basin", "min": 4},
                    {"type": "outlet_open", "key": "discharge"},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "release_liquid", "from_key": "basin",
                           "to_key": "discharge", "units": 6, "kind": "auto"},
                "state_after": "冷却",
            },
        ),
    },
    # ---------------------------------------------------------------- S06
    "scene.static_console": {
        "definition_id": "scene.static_console",
        "family": "S06",
        "name": "会喊话的静电台",
        "description": "两只喇叭口一只朝着内院、一只朝着门口，旋钮边上还剩几格电，台面连着一条能走的路。",
        "clue": "机壳内侧刻着一行：喊给谁听，先选方向。",
        "footprint": (7, 5),
        # §9 S06「改变局部声源位置或开启方向性呼叫」——这一台取方向性呼叫那一支。
        "depths": tuple(range(3, 15)),
        "keys": {
            "console": (3, 2),
            "mic_yard": (1, 2),
            "mic_gate": (5, 2),
        },
        "anchor": "console",
        "terrain": {
            "console": {"variant": "金属聚合物"},
            "mic_yard": {"variant": "金属聚合物"},
            "mic_gate": {"variant": "金属聚合物"},
        },
        "facility": {
            # 电池余量就是呼叫次数：喊一次少一次，拆成电池背面就没有下一次。
            "stock": {"charge": 3},
            "effect_rounds": 0,
            "cooldown_rounds": 3,
        },
        "conditions": (
            {"type": "player_near", "key": "console", "radius": 3},
            {"type": "stock", "name": "charge", "min": 1},
            {"type": "listener_audible", "key": "mic_yard", "radius": 5},
        ),
        "commands": (
            {
                "command": "call_yard",
                "label": "把呼叫打向内院喇叭",
                "detail": "以固定半径 5 发出一次声源：这个方向听得见的失控意识会把它当作此刻知道的位置。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "console", "radius": 1},
                    {"type": "stock", "name": "charge", "min": 1},
                    {"type": "listener_audible", "key": "mic_yard", "radius": 5, "min": 1},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "sound_pulse", "key": "mic_yard", "radius": 5},
                "spends": {"charge": 1},
                "state_after": "冷却",
            },
            {
                "command": "call_gate",
                "label": "把呼叫打向门口喇叭",
                "detail": "换一只喇叭口：同一次呼叫只可能有一个落点，两个方向因此互斥。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "console", "radius": 1},
                    {"type": "stock", "name": "charge", "min": 1},
                    {"type": "listener_audible", "key": "mic_gate", "radius": 5, "min": 1},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "sound_pulse", "key": "mic_gate", "radius": 5},
                "spends": {"charge": 1},
                "state_after": "冷却",
            },
            {
                "command": "take_cell",
                "label": "取出台里的备用电池芯",
                "detail": "拆开就少一次呼叫——换一枚能装进别处的电池背面。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "console", "radius": 2},
                    {"type": "stock", "name": "charge", "min": 1},
                ),
                "effect": {"type": "gain_item", "item": "battery_back", "count": 1},
                "gives": {"charge": -1},
            },
            {
                "command": "feed_cell",
                "label": "把电池背面装回台面",
                "detail": "一枚电池芯够喊一次。",
                "cost": {"items": ("battery_back", 1)},
                "conditions": (
                    OPERABLE_REFILL,
                    {"type": "player_near", "key": "console", "radius": 2},
                    {"type": "carries_item", "item": "battery_back", "min": 1},
                ),
                "effect": {"type": "transfer_stock", "name": "charge", "amount": 1},
            },
        ),
    },
    # ---------------------------------------------------------------- S03
    "scene.fold_ferry": {
        "definition_id": "scene.fold_ferry",
        "family": "S03",
        "name": "对折的渡口",
        "description": "两张空白折页隔着一段路面对面立着，各自四周都是走得进的地面；两边都折稳之后，它们之间就成了一条固定的对折线。",
        "clue": "页脚印着一行：两边都立住了，才谈对折。",
        "footprint": (3, 3),
        # §9 R04：同层两个由生成器绑定的锚点，直线相隔 12–28 格，每端都有步行路线。
        "pair": {"spread": (12, 28), "ends": ("page_a", "page_b")},
        "depths": tuple(range(3, 15)),
        "keys": {
            "page_a": (1, 1),
            "ring_a": ((1, 0), (0, 1), (2, 1), (1, 2)),
            "page_b": (1, 1),
            "ring_b": ((1, 0), (0, 1), (2, 1), (1, 2)),
        },
        "anchor": "page_a",
        # 两端各挂一个入口事件：站在哪一侧都能读出同一个设施记录（同一个 scene_uid）。
        "entrances": ("page_a", "page_b"),
        "terrain": {
            "page_a": {"variant": "空白聚合物"},
            "page_b": {"variant": "空白聚合物"},
        },
        "facility": {
            # 本局总用量就是渡口本身：用完不随重新生成、读档或复位回充（§9 R04）。
            "stock": {"crossings": 3},
            "effect_rounds": 0,
            "cooldown_rounds": 8,
        },
        "conditions": (
            {"type": "player_near", "key": "ends", "radius": 3},
            {"type": "end_primed", "key": "page_a"},
            {"type": "end_primed", "key": "page_b"},
        ),
        "commands": (
            {
                "command": "prime_a",
                "label": "把内侧折页折稳",
                "detail": "折稳的那一格会反出光来，对折线这才少了一头的悬空。纸页贴着耳朵时有极轻的回声。",
                # §7.2「诗的下半句」的两处回声之一：折页本身就是写着诗的纸，
                # 折稳的一瞬诗人要找的那半句会漏出来（线索随 prime 落账）。
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "page_a", "radius": 0},
                    {"type": "end_primed", "key": "page_a", "max": 0},
                ),
                "effect": {"type": "prime_end", "key": "page_a", "variant": "反光聚合物",
                           "report": "echo_inner"},
            },
            {
                "command": "prime_b",
                "label": "把外侧折页折稳",
                "detail": "另一头要在另一头站上去折——两边不能隔着路一起立住。这一张的回声比内侧那张低半个音。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "page_b", "radius": 0},
                    {"type": "end_primed", "key": "page_b", "max": 0},
                ),
                "effect": {"type": "prime_end", "key": "page_b", "variant": "反光聚合物",
                           "report": "echo_outer"},
            },
            {
                "command": "cross",
                "label": "对折到另一张折页那侧",
                "detail": "只在这对端点之间折：落到对端最近的一格空地上，找不到空地就不收这一笔。敌人照样走完它们的那一拍。",
                "cost": {"imagination": 3},
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "ends", "radius": 1},
                    {"type": "end_primed", "key": "page_a", "min": 1},
                    {"type": "end_primed", "key": "page_b", "min": 1},
                    {"type": "stock", "name": "crossings", "min": 1},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "fold_travel", "ends": ("page_a", "page_b"),
                           "radius": 1, "search": 2},
                "spends": {"crossings": 1},
                "state_after": "冷却",
            },
        ),
    },
    # ---------------------------------------------------------------- S14
    "scene.pump_house": {
        "definition_id": "scene.pump_house",
        "family": "S14",
        "name": "泵房的保护区",
        "description": "泵机在走道那一头空转，保护区就是走道边的一块空地，侧门是它朝着走道的那一面，"
                       "挡板的手柄钉在门外的墙柱上；协会把这里当临时存放点，如今里头窝了一位不请自来的。",
        "clue": "门框上钉着登记条：那位解决之前，泵房不开张。",
        "footprint": (7, 7),
        # 狩猎登记的目标场所（§7.2「泵房的狩猎登记」）：目标就是院里那一只，
        # 击败与「引出来再放下挡板」两解都落在真实格子上。
        "depths": tuple(range(2, 8)),
        "keys": {
            "yard": {"center": (3, 3), "size": (3, 3)},
            "side_door": (5, 3),
            # 挡板的手柄在门外的墙柱上：站到手柄边才放得下挡板。它既贴着侧门，
            # 又贴着泵机——入口面板只在锚点旁边按得开（``interact`` 要挨着事件格），
            # 手柄离泵机超过一格，玩家就得在「看得见面板」和「够得着挡板」之间二选一。
            "winch": (6, 2),
            # 泵机摆在走道那一头，与侧门隔两格：喊声的落点要是贴着门，被引出来的
            # 那位就正好停在挡板上，「不放压下东西的那一块」便永远办不成诱离这一解。
            "pump": (6, 1),
        },
        "anchor": "pump",
        # 常驻目标：由 core/scenes.py 放在作用区中心，身份随设施而不是随实例编号。
        "threat": {"key": "yard", "anomaly": "anomaly.folded_person"},
        # 「保持泵房安全 N 世界回合」的记账对象与期限（§7.2）。
        "safe_zones": ("yard",),
        "hold_rounds": 3,
        "facility": {
            # 空转次数就是余电：泵机响一次少一次。
            "stock": {"charge": 2},
            "effect_rounds": 0,
            "cooldown_rounds": 2,
            "zone_key": "yard",
        },
        "conditions": (
            {"type": "player_near", "key": "pump", "radius": 3},
            {"type": "zone_occupants", "key": "yard", "min": 0},
        ),
        "commands": (
            {
                "command": "run_pump",
                "label": "让泵机空转一声",
                "detail": "喊声落在走道那一头空转的泵机上：那位要过来看，就得先离开庭院那几格。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "pump", "radius": 1},
                    {"type": "stock", "name": "charge", "min": 1},
                    {"type": "listener_audible", "key": "pump", "radius": 5, "min": 1},
                    {"type": "facility_ready"},
                ),
                "effect": {"type": "sound_pulse", "key": "pump", "radius": 5},
                "spends": {"charge": 1},
                "state_after": "冷却",
            },
            {
                "command": "seal_door",
                "label": "在门柱手柄边放下侧门挡板",
                "detail": "挡板落下就卡死在门槽里，要抬起来得回协会领工单——手柄在门外的墙柱上，"
                          "它封的是回院子最近的那一步；挡板上正站着东西时不放。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "winch", "radius": 1},
                    {"type": "zone_occupants", "key": "yard", "max": 0},
                    {"type": "opening_sealed", "key": "side_door", "max": 0},
                ),
                "effect": {"type": "seal_opening", "key": "side_door"},
            },
        ),
    },
    # ---------------------------------------------------------------- S01
    "scene.waiting_hall": {
        "definition_id": "scene.waiting_hall",
        "family": "S01",
        "name": "换乘站的候车厅",
        "description": "路线牌立在大厅这一头，牌上三条线都绕回同一个大厅；一条贴着窗的窄路被"
                       "杂物堵着，另一侧还剩一条没人走的旁路。牌座下压着一张没有盖章的候车票。",
        "clue": "牌座刻着一行：先把旁路认下来，再看窗边那条通不通。",
        "footprint": (7, 6),
        "depths": tuple(range(2, 15)),
        "keys": {
            "board": (4, 1),
            # 大厅是玩家站立与读牌的开阔地；左右各一条一条窄路：旁路没人走，窗边那条被堵着。
            "hall": {"center": (3, 3), "size": (3, 3)},
            "bypass": {"center": (1, 3), "size": (1, 3)},
            "window": {"center": (5, 3), "size": (1, 3)},
            # 旅人铺位（§7.2「一杯给醒着的人」）：长椅上铺出来的一块，铺好才开始
            # 计「候车厅保持安全」的账（hold_flag）。
            "bedroll": (2, 2),
        },
        "anchor": "board",
        "terrain": {
            "board": {"variant": "金属聚合物"},
            "hall": {"variant": "金属聚合物"},
            "bypass": {"variant": "空白聚合物"},
            "window": {"variant": "绝热层"},
        },
        # 窗边窄路上堆着可搬动的杂物：不搬开，票换不来中继权限（§8 S01「窗边路线受阻挡影响」）。
        "blockage": {"item": "glass_bottle", "key": "window"},
        # §7.2「一杯给醒着的人」的持续安全记账对象：铺位铺好（hold_flag）之后，
        # 大厅连着 3 个世界回合没有火、没有失控意识踩进去＝避难点恢复。
        "safe_zones": ("hall",),
        "hold_rounds": 3,
        "hold_flag": "bedroll",
        "facility": {
            # 候车票只有一张：换中继权限、带走、留给站台三选一（§8 S01）。
            "stock": {"tickets": 1},
            "effect_rounds": 0,
            "cooldown_rounds": 0,
        },
        "conditions": (
            {"type": "player_near", "key": "board", "radius": 2},
            {"type": "stock", "name": "tickets", "min": 1},
        ),
        "commands": (
            {
                "command": "read_board",
                "label": "读路线牌，把旁路标在地上",
                "detail": "认下这条没人走的旁路：标出来的那几格会反出光来。牌上也顺带指出窗边那条窄路被什么堵着。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "board", "radius": 2},
                    {"type": "flag_set", "name": "marked", "max": 0},
                ),
                "effect": {"type": "mark_route", "key": "bypass",
                           "variant": "反光聚合物", "flag": "marked"},
            },
            {
                "command": "lay_bedroll",
                "label": "把长椅铺成旅人的铺位",
                "detail": "铺好的那一格会反出光来。铺位立住之后，候车厅才开始给旅人记「连着安全」的账。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "board", "radius": 2},
                    {"type": "flag_set", "name": "bedroll", "max": 0},
                ),
                "effect": {"type": "mark_route", "key": "bedroll",
                           "variant": "反光聚合物", "flag": "bedroll"},
            },
            {
                # §7.2「遗失物有名字」的第一处证据：登记册记着丢了什么。
                "command": "check_manifest",
                "label": "查候车厅的失物登记册",
                "detail": "册子上一行墨迹未干：「一只带软木塞的玻璃瓶，失主候车时落下的。」",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "board", "radius": 2},
                    {"type": "flag_set", "name": "manifest", "max": 0},
                ),
                "effect": {"type": "report_clue", "report": "manifest"},
            },
            {
                # 第二处证据：窗边那堆杂物里的行李签（先查过册子才知道要对什么）。
                "command": "match_tag",
                "label": "对窗边杂物上的行李签",
                "detail": "签上的名字与册子那行对上了：瓶子是候车厅旅人的——归还、代管还是声明占有，你来定。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "window", "radius": 2},
                    {"type": "flag_set", "name": "manifest", "min": 1},
                    {"type": "flag_set", "name": "tag", "max": 0},
                ),
                "effect": {"type": "report_clue", "report": "tag"},
            },
            {
                "command": "clear_window",
                "label": "把堵在窗边窄路上的杂物挪开",
                "detail": "搬开之后窗边这条路才通——它还在地图上，只是不堵着了。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "window", "radius": 2},
                    {"type": "flag_set", "name": "marked", "min": 1},
                    {"type": "blockage_present", "key": "window", "min": 1},
                ),
                "effect": {"type": "clear_blockage", "key": "window"},
            },
            {
                "command": "hand_ticket",
                "label": "把票交给站台，换一次中继权限",
                "detail": "中继权限要把窗边那条路先打通：路还堵着，票换不来任何东西。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "board", "radius": 2},
                    {"type": "flag_set", "name": "marked", "min": 1},
                    {"type": "blockage_present", "key": "window", "max": 0},
                    {"type": "stock", "name": "tickets", "min": 1},
                ),
                "effect": {"type": "mark_route", "key": "window",
                           "variant": "反光聚合物", "flag": "relay"},
                "gives": {"tickets": -1},
            },
            {
                "command": "take_ticket",
                "label": "取走候车票",
                "detail": "带走就换不到中继权限，也留不下旅人补给——票只有这一张。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "board", "radius": 2},
                    {"type": "stock", "name": "tickets", "min": 1},
                ),
                "effect": {"type": "gain_item", "item": "quiet_ticket", "count": 1},
                "gives": {"tickets": -1},
            },
            {
                "command": "keep_ticket",
                "label": "把票留在站台，换一份旅人补给",
                "detail": "把票留在原处，旅人服务就照旧开着——换一份能带走的热饮。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "board", "radius": 2},
                    {"type": "flag_set", "name": "kept", "max": 0},
                    {"type": "stock", "name": "tickets", "min": 1},
                ),
                "effect": {"type": "gain_item", "item": "warm_coffee", "count": 1,
                           "flag": "kept"},
                "gives": {"tickets": -1},
            },
        ),
    },
    # ---------------------------------------------------------------- S09
    "scene.archive_desk": {
        "definition_id": "scene.archive_desk",
        "family": "S09",
        "name": "档案馆的编目台",
        "description": "编目台立在档案架这一头，架上的记录按回声而不是按年份排列；索引卡还空着，"
                       "另一侧一条通向外面的窄路从没有人标过。",
        "clue": "台面刻着一行：先认出是哪一页，再决定留、拆、还是交。",
        "footprint": (7, 6),
        # §8 S09「找到具名记录、选择保留／拆出／交付」：取记录出现的那几层。
        "depths": tuple(range(3, 18)),
        "keys": {
            "desk": (3, 1),
            # 档案架是玩家翻找与拆页的开阔地；左右各一条一条窄路：索引区等辨认后点亮，
            # 外侧那条安全路线要交付记录才标得出来。
            "stacks": {"center": (3, 3), "size": (3, 3)},
            "index": {"center": (5, 3), "size": (1, 3)},
            "route": {"center": (1, 3), "size": (1, 3)},
        },
        "anchor": "desk",
        "terrain": {
            "desk": {"variant": "金属聚合物"},
            "stacks": {"variant": "空白聚合物"},
            "index": {"variant": "空白聚合物"},
            "route": {"variant": "空白聚合物"},
        },
        "facility": {
            # 没有有界材料：这一族的作用是线索、服务与一条安全路线，不靠反复取用发奖（§8 S09）。
            "effect_rounds": 0,
            "cooldown_rounds": 0,
        },
        "conditions": (
            {"type": "player_near", "key": "desk", "radius": 2},
        ),
        "commands": (
            {
                "command": "identify",
                "label": "照编目核对，认出那页具名记录",
                "detail": "把那页从回声里挑出来：索引卡会被点亮。认出来之前，留、拆、交都无从谈起。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "desk", "radius": 2},
                    {"type": "flag_set", "name": "identified", "max": 0},
                ),
                "effect": {"type": "mark_route", "key": "index",
                           "variant": "反光聚合物", "flag": "identified"},
            },
            {
                "command": "keep_leaf",
                "label": "把记录留回架上，保留当地服务",
                "detail": "留在这里，档案馆的台面就照旧开着——换一次能带走的当地服务。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "desk", "radius": 2},
                    {"type": "flag_set", "name": "identified", "min": 1},
                    {"type": "flag_set", "name": "filed", "max": 0},
                    {"type": "flag_set", "name": "extracted", "max": 0},
                ),
                "effect": {"type": "gain_item", "item": "inspiration_coffee", "count": 1,
                           "flag": "filed"},
            },
            {
                "command": "extract_leaf",
                "label": "把那页记录拆出来带走",
                "detail": "拆走就没有服务，也标不出安全路线——要换别的，先把这一页交回去。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "stacks", "radius": 2},
                    {"type": "flag_set", "name": "identified", "min": 1},
                    {"type": "flag_set", "name": "filed", "max": 0},
                    {"type": "flag_set", "name": "extracted", "max": 0},
                ),
                "effect": {"type": "gain_item", "item": "guestbook_page", "count": 1,
                           "flag": "extracted"},
            },
            {
                "command": "deliver_leaf",
                "label": "把拆下的记录交给档案员，换一条安全路线",
                "detail": "带着那页交到台面上：外侧那条没人标过的窄路会被标成一条安全路线。",
                "cost": {"items": ("guestbook_page", 1)},
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "desk", "radius": 2},
                    {"type": "flag_set", "name": "extracted", "min": 1},
                    {"type": "carries_item", "item": "guestbook_page", "min": 1},
                ),
                "effect": {"type": "mark_route", "key": "route",
                           "variant": "反光聚合物", "flag": "routed"},
            },
        ),
    },
    # ---------------------------------------------------------------- S23
    "scene.lens_gate": {
        "definition_id": "scene.lens_gate",
        "family": "S23",
        "name": "守门的青灯",
        "description": "一盏青色的小灯悬在石台上方，灯罩里缺一块透镜；灯下的石阶通向一扇还没成形的门。",
        "clue": "灯座上刻着一行：嵌进透镜，再喂它三件会消散的东西。",
        # 作者摆放（§8 S23）：只随第 10 层的灯塔结构出现，不进随机投放池——
        # ``scene_allowed`` 见到 ``binding == "vault"`` 直接排除，落位交给
        # ``core.scenes.install_bound_scene``（锚点就是 vault 指定的 event_anchor）。
        "binding": "vault",
        "depths": (10,),
        "footprint": (3, 3),
        # 「灯」就摆在 vault 盖章时指定的那一格：单键相对坐标取 (0, 0)。
        "keys": {"lamp": (0, 0)},
        "anchor": "lamp",
        # 一次性通道的门态机与两个效果原语都在 ``world/scenes.py``：
        # ``open_gate`` 只把门推进「等待支付」并唤出选择面板，``enter_gate`` 真正进位面。
        "gate": {"realm": "toy_memories", "gift": 3},
        "facility": {"effect_rounds": 0, "cooldown_rounds": 0},
        "conditions": (
            {"type": "player_near", "key": "lamp", "radius": 2},
        ),
        "commands": (
            {
                "command": "offer_lens",
                "label": "把灯塔透镜嵌进灯座（挑三件祭品）",
                "detail": "青灯缺一块透镜：嵌进去，再从行囊里挑出三件易逝物或摄入物当祭品。",
                "conditions": (
                    {"type": "facility_state_in", "states": ("未开启", "等待支付")},
                    {"type": "player_near", "key": "lamp", "radius": 2},
                    {"type": "carries_item", "item": "lighthouse_lens", "min": 1},
                ),
                "effect": {"type": "open_gate", "realm": "toy_memories", "gift": 3},
            },
            {
                "command": "enter_gate",
                "label": "走入镜中的门（进入梦中梦·玩具的回忆）",
                "detail": "只有门开着的时候才走得进去；这一走就进了位面。",
                "conditions": (
                    {"type": "facility_state_in", "states": ("开启",)},
                    {"type": "player_near", "key": "lamp", "radius": 2},
                ),
                "effect": {"type": "enter_gate", "realm": "toy_memories"},
            },
        ),
    },
    # ---------------------------------------------------------------- R03（S14 第二处）
    "scene.lamp_refuge": {
        "definition_id": "scene.lamp_refuge",
        "family": "S14",
        "name": "留灯的避难圈",
        "description": "一圈反光的地面环着一座灯台，两侧各留一个可走的出口；灯台上压着一盏没点的留灯。",
        "clue": "灯座刻着一行：先点起来，再让圈里清干净——灯只管一件事，圈里连着的安全才作数。",
        "footprint": (9, 9),
        # 与 S14 泵房同段：R03 与登记员（npc.scrap_registrar）同层可接的概率高。
        "depths": tuple(range(2, 9)),
        "keys": {
            "lamp": (4, 4),
            "ring": {"center": (4, 4), "radius": 2},
            "door_a": (0, 4),          # 西侧出口（可放挡板）
            "door_b": (8, 4),          # 东侧出口（普通可走）
            "winch": (1, 4),           # 挡板手柄，贴在 door_a 外侧
        },
        "anchor": "lamp",
        # 未点灯时的暗地面；``light_lamp`` 会把环线换成「反光聚合物」。
        "terrain": {
            "ring": {"variant": "空白聚合物"},
            "lamp": {"variant": "金属聚合物"},
            "door_a": {"variant": "空白聚合物"},
            "door_b": {"variant": "空白聚合物"},
            "winch": {"variant": "金属聚合物"},
        },
        # 保持环线连续安全 3 世界回合；「灯亮」是计数前置（hold_flag）。
        "safe_zones": ("ring",),
        "hold_rounds": 3,
        "hold_flag": "lit",
        # 抵抗窗口：数据声明目标征兆与时长（默认中毒＝毒气，与 R03「没有高危险气体」同源）。
        "ward": {"portent": "poisoned", "turns": 6},
        "facility": {"effect_rounds": 0, "cooldown_rounds": 0},
        "conditions": (
            {"type": "player_near", "key": "lamp", "radius": 3},
        ),
        "commands": (
            {   # 点亮留灯：真实地面改造＋lit 开关
                "command": "light_lamp",
                "label": "点亮留灯（把灯台激活）",
                "detail": "花一点想象力点亮灯台：环线地面会反出光来。灯亮着，圈里的连续安全才作数。",
                "cost": {"imagination": 1},
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "lamp", "radius": 1},
                    {"type": "flag_set", "name": "lit", "max": 0},
                ),
                "effect": {"type": "light_lamp", "key": "ring", "variant": "反光聚合物"},
            },
            {   # 休息：心智 +4，本地点本局一次
                "command": "rest_mind",
                "label": "在圈里歇一会儿（心智 +4）",
                "detail": "灯亮、圈里没有火和危险气体时才能坐。只回心智，一次为限。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "lamp", "radius": 3},
                    {"type": "flag_set", "name": "lit", "min": 1},
                    {"type": "flag_set", "name": "rested", "max": 0},
                    {"type": "no_zone_hazard", "key": "ring"},
                ),
                "effect": {"type": "grant_rest", "stat": "mind", "amount": 4},
            },
            {   # 休息：清醒 +4（与上条二选一）
                "command": "rest_lucidity",
                "label": "在圈里歇一会儿（清醒 +4）",
                "detail": "与「歇一会儿（心智 +4）」二选一：哪一种先坐下就算哪一种。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "lamp", "radius": 3},
                    {"type": "flag_set", "name": "lit", "min": 1},
                    {"type": "flag_set", "name": "rested", "max": 0},
                    {"type": "no_zone_hazard", "key": "ring"},
                ),
                "effect": {"type": "grant_rest", "stat": "lucidity", "amount": 4},
            },
            {   # 放下侧门挡板：把院口堵上
                "command": "seal_door",
                "label": "在门柱手柄边放下侧门挡板",
                "detail": "挡板落下就卡死在门槽里；挡板上正站着东西时不放。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "winch", "radius": 1},
                    {"type": "opening_sealed", "key": "door_a", "max": 0},
                    {"type": "zone_occupants", "key": "ring", "max": 0},
                ),
                "effect": {"type": "seal_opening", "key": "door_a"},
            },
            {   # 修好侧门：抬起挡板（不刷新一次性休息奖励）
                "command": "repair_door",
                "label": "修好侧门门轴，抬起挡板",
                "detail": "随时可以把挡板抬回去。修门只动门，不动你歇过的那一次。",
                "conditions": (
                    OPERABLE,
                    {"type": "player_near", "key": "winch", "radius": 1},
                    {"type": "opening_sealed", "key": "door_a", "min": 1},
                ),
                "effect": {"type": "repair_opening", "key": "door_a"},
            },
        ),
    },
}

#: 逐层投放池：每层至多 1 个主要互动场景（§12.1）。
SCENE_SPAWN_IDS: tuple[str, ...] = tuple(SCENE_DEFINITIONS)


def scene_definition(definition_id: str) -> dict[str, Any] | None:
    return SCENE_DEFINITIONS.get(definition_id)


def command_names(definition: dict[str, Any]) -> tuple[str, ...]:
    return tuple(command["command"] for command in definition.get("commands", ()))


def scene_allowed(definition: dict[str, Any], depth: int, realm_id: str = "") -> bool:
    """位面内不放主梦场景：布局参数按主梦房间设计，且会挤占本层预算（§12.1）。

    ``binding == "vault"`` 的作者摆放场景（§8 S23 青灯入口）同样不进随机池：
    它的落位由 ``core.scenes.install_bound_scene`` 跟着具体结构走，随机投放会
    把它丢到没有灯塔的层上。
    """
    if definition.get("binding") == "vault":
        return False
    if realm_id:
        return False
    return depth in (definition.get("depths") or ())
