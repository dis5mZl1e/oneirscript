"""墙体目录：墙种定义、出场层级池与生成预算。

墙体是「坚实聚合物」类地格的填充物——高墙阻挡移动与视线，低墙（高度 1）
允许液体气体越过。门、地面容器在数据上也是墙种，但有各自的专门机制。
"""

from __future__ import annotations

from .definitions import WallDef
from dataclasses import replace


WALL_DEFINITIONS: dict[str, WallDef] = {
    "压实聚合墙": WallDef("压实聚合墙", "wall.compacted", "#707780", 3, 3, 2, 120),
    "玻璃幕墙": WallDef(
        "玻璃幕墙", "wall.glass_curtain", "#cfeff7", 1, 3, 1, 40,
        "透明隔断", "shatter", transparent=True,
    ),
    "反光玻璃墙": WallDef("反光玻璃墙", "wall.reflective", "#b9edf2", 1, 3, 1, 45, "反光刺目", "smoke"),
    "吸声聚合墙": WallDef("吸声聚合墙", "wall.absorbing", "#655e78", 2, 2, 2, 90, "声响被吸收"),
    "冷凝囊壁": WallDef("冷凝囊壁", "wall.condensing", "#4ea9d8", 1, 2, 1, 55, "表面凝水", "condense"),
    "不稳定燃料墙": WallDef("不稳定燃料墙", "wall.fuel", "#d48a2e", 2, 2, 1, 70, "燃料震颤", "explode"),
    "潮解纸墙": WallDef("潮解纸墙", "wall.deliquescent", "#c9b8a0", 1, 1, 1, 35, "纸味潮湿", "soak"),
    "蜡化记忆墙": WallDef("蜡化记忆墙", "wall.wax", "#e8c07a", 1, 2, 1, 45, "蜡味温热"),
    "尖啸瓷墙": WallDef("尖啸瓷墙", "wall.porcelain", "#dceef4", 2, 3, 2, 70, "高频尖啸", "shatter"),
    "空心积木墙": WallDef("空心积木墙", "wall.hollow", "#9a8fb8", 1, 1, 2, 25, "空响", "none", True),
    "活字字模墙": WallDef("活字字模墙", "wall.movable_type", "#7d8ba3", 2, 2, 1, 55, "字句排列变动", "ink"),
    "记忆容器": WallDef("记忆容器", "wall.memory_vessel", "#a8c8a0", 1, 1, 1, 25, "记忆沉淀的气味", "none", True),
    "思绪容器": WallDef("思绪容器", "wall.thought_vessel", "#c8a8d8", 1, 1, 1, 25, "思绪的低语", "none", True),
    "坚硬聚合墙": WallDef("坚硬聚合墙", "wall.hardened", "#5d6474", 4, 3, 2, 150),
    "清醒石": WallDef("清醒石", "wall.clarity_stone", "#bfe8f5", 3, 3, 2, 110, "清凉的石头气息"),
    "梦晶簇": WallDef("梦晶簇", "wall.dream_crystal", "#d3b8f0", 2, 2, 2, 80, "晶体嗡鸣", "dreamcrystal",
                      light_radius=1),
    "烛泪柱": WallDef("烛泪柱", "wall.candle_pillar", "#f0e2c0", 1, 2, 1, 40, "烛油的暖味"),
    "枕木": WallDef("枕木", "wall.sleeper", "#8a6f52", 1, 1, 1, 30),
    "云块": WallDef("云块", "wall.cloud", "#e8eef5", 1, 1, 1, 30, "潮湿的云絮", "none", False, True),
    "黄粱米堆": WallDef("黄粱米堆", "wall.millet", "#e8d9a0", 1, 1, 1, 20, "米香", "none", True),
    "铅板": WallDef("铅板", "wall.lead", "#8a8f9a", 3, 2, 1, 90, "沉闷的金属闷响"),
    "盐晶壁": WallDef("盐晶壁", "wall.salt", "#f0ede4", 1, 2, 1, 45, "咸涩的结晶", "none", False, True),
    # ---- 无意识领域（21–27）：常见墙。致密聚合物四色等比例替换压实/坚硬的
    # 主墙体位（同图标不同色）；梦魇岩贴近超过 3 回合授予噩梦征兆。----
    "赤致密聚合墙": WallDef("赤致密聚合墙", "wall.dense", "#7a4040", 5, 3, 2, 180),
    "黄致密聚合墙": WallDef("黄致密聚合墙", "wall.dense", "#8a7a3a", 5, 3, 2, 180),
    "蓝致密聚合墙": WallDef("蓝致密聚合墙", "wall.dense", "#3a5a8a", 5, 3, 2, 180),
    "绿致密聚合墙": WallDef("绿致密聚合墙", "wall.dense", "#3a7a4a", 5, 3, 2, 180),
    "梦魇岩": WallDef("梦魇岩", "wall.nightmare_rock", "#4a3a6a", 6, 3, 2, 220, "低语的噩梦边缘"),
    # ---- 无意识领域：区域专属特征墙（leak=3）----
    "呜咽晶柱": WallDef("呜咽晶柱", "wall.weeping_crystal", "#8ac8d8", 2, 3, 1, 90, "悲鸣（想象力流失）"),
    "沉思铁幕": WallDef("沉思铁幕", "wall.iron_curtain", "#5a5a68", 6, 3, 2, 240, "声音在此止步"),
    "无光绒墙": WallDef("无光绒墙", "wall.lightless_velvet", "#2a2438", 1, 3, 1, 50, "吞掉周围的微光"),
    "蚀梦菌毯": WallDef("蚀梦菌毯", "wall.dream_mold", "#7a8a4a", 1, 1, 1, 40, "蚀梦：贴近清醒流失", "none", True),
    "静默碑岩": WallDef("静默碑岩", "wall.silent_stone", "#8a8aa0", 4, 2, 2, 150, "碑文无人能读"),
    # ---- 无意识领域：特征固体（leak=3）----
    "无意识结晶": WallDef("无意识结晶", "wall.unconscious_crystal", "#d0a8e8", 3, 2, 2, 120, "深处气体的结晶",
                         light_radius=1),
    "悔恨之锚": WallDef("悔恨之锚", "wall.anchor_of_regret", "#6a5a4a", 4, 2, 2, 160, "沉重的水下钟声"),
    "千层叠岩": WallDef("千层叠岩", "wall.strata_rock", "#98786a", 6, 3, 2, 300, "一层是一段没做的梦"),
    "回响黑曜岩": WallDef("回响黑曜岩", "wall.echo_obsidian", "#1a1a28", 3, 3, 1, 100, "黑色的镜面", "none", False, False, True),
    # ---- 2026-09-18 Excel 新一批固体 ----
    # 石墨烯晶格：极高硬度和耐久，但能被四向推动（推箱子，无法拉回）。
    "石墨烯晶格": WallDef("石墨烯晶格", "wall.graphene", "#5a6a7a", 9, 2, 2, 400, "规整的六边形晶格", "none", False, False, False, True),
    # 玉米淀粉墙：免疫所有子弹与远程攻击伤害（非牛顿流体吞掉弹体）。
    "玉米淀粉墙": WallDef("玉米淀粉墙", "wall.cornstarch", "#e8e2d0", 2, 2, 2, 120, "受压时骤然变硬", "none", False, False, False, False, True),
    "灰烬": WallDef("灰烬", "wall.ash", "#9a938a", 1, 1, 1, 15),
    # 台子：1 格高固体，不能穿过，但台面可以承载物品/事件地点。
    # 木桌子易晃（低完整度），石台厚重；两者都不可徒手破坏——
    # 否则砸了台子，台上的事件地点/物品就被埋进普通地面了。
    # 两者都带「点击可寻路」隐藏属性：点远处台子会走到台边被挡住（不再当场放弃寻路），
    # 到地方若有未回应的异常地点就地回应、台面有显化物就取走。
    "木桌子": WallDef("木桌子", "wall.wood_table", "#b08a4a", 1, 1, 1, 30, "木头的干涩气味", path_clickable=True),
    "石台": WallDef("石台", "wall.stone_platform", "#9aa0a8", 2, 1, 1, 70, "石面的凉意", path_clickable=True),
    "意识边界": WallDef("意识边界", "wall.boundary", "#4a4d58", 999, 4, 4, 9999),
    # 门：关卡里可开合的咽喉点。关闭时为高墙（阻挡移动与流体），踏上即开、变为
    # 可通行的空气；无论开合都恒阻视线（见 core._sight_reaches）。不直接进随机墙池，
    # 由 _assign_wall_kinds 在门位强制染成「门」。
    "门": WallDef("门", "wall.door", "#d9a441", 2, 2, 2, 80),
    # ---- 内容扩展包 v1（2026-09-20）----
    "吸光苔墙": WallDef("吸光苔墙", "wall.moss_light", "#2a3a2a", 1, 3, 1, 60, "吸光（视野衰减）"),
    "回魂陶俑": WallDef("回魂陶俑", "wall.terracotta", "#c8a890", 3, 2, 1, 90, "陶土气息", "summon"),
    "镜湖板": WallDef("镜湖板", "wall.mirror_lake", "#c0d8e8", 1, 1, 1, 40, "映像", "reflect", transparent=True),
    "倦怠棉垛": WallDef("倦怠棉垛", "wall.cotton_stack", "#e0dcd0", 1, 1, 2, 50, "倦怠", "none", True),
    "导电铜网墙": WallDef("导电铜网墙", "wall.copper_mesh", "#b07040", 4, 2, 1, 110, "微麻", "conduct"),
    # 梦中梦·门之回廊（2026-09-21）：支线专属墙。
    "门扉之壁": WallDef("门扉之壁", "wall.doorframe", "#3a3a5a", 3, 3, 2, 90, "无数门的呼吸"),
    "碎屑堆": WallDef("碎屑堆", "wall.rubble", "#a89a82", 3, 2, 2, 70, "新崩落的碎屑"),
    # ---- 梦中梦·千禧园（2026-10-10）：emoji 专属墙（docs/millennium-garden-design.md §7）----
    # 全园墙体都用 emoji 字形（M0 探针 26 字形全 SAFE）；默认 ██ 墙在园内禁止出现。
    "蓝砖墙": WallDef("蓝砖墙", "wall.xp_brick", "#3a6ea5", 3, 3, 2, 120, "XP 蓝白砖缝"),
    "千禧树": WallDef("千禧树", "wall.millennium_tree", "#2a7a2a", 4, 3, 2, 160, "永远的下午四点"),
    "木门": WallDef("木门", "wall.xp_door", "#b8860b", 2, 2, 2, 80),
    "色块墙·红": WallDef("色块墙·红", "wall.block_red", "#d04040", 2, 2, 2, 60),
    "色块墙·橙": WallDef("色块墙·橙", "wall.block_orange", "#e08030", 2, 2, 2, 60),
    "色块墙·蓝": WallDef("色块墙·蓝", "wall.block_blue", "#4070d0", 2, 2, 2, 60),
    "白块窗": WallDef("白块窗", "wall.block_white", "#eef0f6", 1, 1, 1, 40, transparent=True),
    "传真墙": WallDef("传真墙", "wall.fax_machine", "#c8c8d0", 3, 2, 2, 90, "垃圾传真：贴近暴露位置"),
    "灯箱墙": WallDef("灯箱墙", "wall.lightbox", "#fff0a0", 1, 1, 1, 50, transparent=True,
                      light_radius=2),
    "弹窗墙": WallDef("弹窗墙", "wall.popup", "#d0a0d0", 2, 2, 1, 50, "关不掉的弹窗",
                      break_effect="popup_drop", hand_breakable=True),
    "磁带墙": WallDef("磁带墙", "wall.tape_wall", "#8a6a4a", 2, 2, 2, 70, "倒带迟滞：贴近移动变慢"),
    "摇杆柱": WallDef("摇杆柱", "wall.joystick_post", "#64647c", 2, 2, 1, 80, "可推动", pushable=True),
    "打印机墙": WallDef("打印机墙", "wall.printer", "#d8d8d8", 2, 2, 2, 70, "卡纸了",
                        break_effect="soak", hand_breakable=True),
    # 蓝屏终端（零点体育场中央）：极高硬度耐久；破坏 = 敌对召唤千年虫（§10.3 路径 B）。
    "蓝屏终端": WallDef("蓝屏终端", "wall.bsod_terminal", "#2050d0", 9, 3, 3, 9999,
                        "你的电脑遇到问题，需要重新启动",
                        break_effect="millennium_summon", path_clickable=True,
                        light_radius=1),
    # 理念立方体（玩具的回忆第 4 层）：推箱子固体——不可破坏、免疫爆炸/火焰/
    # 弹体，可推（撞上即推一格），不自然生成。
    "理念立方体": WallDef("理念立方体", "wall.idea_cube", "#e8e8f0",
                          999, 2, 2, 9999, "规整的纯白立方",
                          "none", False, False, False, True, projectile_immune=True),
    # 电路逻辑 v2（2026-09-21）：门类节点
    "合辙枢": WallDef("合辙枢", "gate.and", "#c87850", 3, 3, 2, 110, "两道齿轨咬合"),
    "分流枢": WallDef("分流枢", "gate.or", "#5aa878", 3, 3, 2, 100, "单向的绿色阀芯"),
    "接线枢": WallDef("接线枢", "gate.junction", "#8a8aa0", 2, 2, 1, 60, "四通的马蹄钉"),
    # 凝聚构想产物：可徒手破坏、可推的临时掩体。
    "臆造聚合墙": WallDef("臆造聚合墙", "wall.conjured", "#7ac8a8", 2, 1, 2, 60, "新凝的梦质", "none", True, False, False, True),
    # 囚笼栅栏的临时墙种：10 回合后自动消散（被关永远有出路）。
    "意识栅栏": WallDef("意识栅栏", "wall.mind_fence", "#9a8ac8", 1, 2, 1, 30, "将散的栅影", "none", True),
    # ---- 逻辑固体（内容扩展包 v1）：触发源与接收器 ----
    # 陷阱/机关石台与普通石台完全同图标同色（▣ #9aa0a8），只能靠机关嗅觉或试错识别。
    "陷阱石台": WallDef("陷阱石台", "wall.stone_platform", "#9aa0a8", 2, 1, 1, 70, "石面的凉意", path_clickable=True),
    "机关石台": WallDef("机关石台", "wall.stone_platform", "#9aa0a8", 2, 1, 1, 70, "石面的凉意", path_clickable=True),
    "感应符文墙": WallDef("感应符文墙", "wall.rune_sensor", "#7a6a9a", 3, 3, 2, 110, "符文微光流转"),
    "定时摆轮": WallDef("定时摆轮", "wall.pendulum", "#b0a060", 2, 2, 1, 80, "规律的滴答声"),
    # 机关门用灰色普通门图标（╫ #808080），与普通门外观一致、仅色差。
    "机关门": WallDef("机关门", "wall.door", "#808080", 1, 2, 1, 60, "齿轮咬合的门"),
    "显影方尖": WallDef("显影方尖", "wall.reveal_obelisk", "#d0b8f0", 2, 3, 1, 90, "方尖上的微光"),
    "囚笼栅栏": WallDef("囚笼栅栏", "wall.cage_post", "#8a8a9a", 2, 2, 1, 85, "冷硬的栅柱"),
    "弹射座": WallDef("弹射座", "wall.launcher", "#c07050", 2, 1, 1, 75, "绷紧的簧片"),
    "灌注阀": WallDef("灌注阀", "wall.valve", "#5a8ab0", 2, 2, 1, 85, "阀门的潮气"),
    "共鸣报警器": WallDef("共鸣报警器", "wall.alarm", "#c05050", 2, 2, 1, 80, "随时会啸叫的铜喇叭"),
}

# Hospital ventilation appliances are solid walls; wind never passes through them.
WALL_DEFINITIONS.update({
    "白瓷隔断": WallDef("白瓷隔断", "wall.clinic.partition", "#98a8b0", 3, 3, 2, 120, spawn_realms=("white_sanatorium",)),
    "净相壁": WallDef("净相壁", "wall.clinic.cleanse", "#8eb6bd", 3, 3, 2, 120, spawn_realms=("white_sanatorium",)),
    "日光壁": WallDef("日光壁", "wall.clinic.light", "#b5b18b", 3, 3, 2, 120,
                     spawn_realms=("white_sanatorium",), light_radius=3),
    "净玻璃隔屏": WallDef("净玻璃隔屏", "wall.clinic.glass", "#91aabd", 2, 3, 1, 90,
                       transparent=True, spawn_realms=("white_sanatorium",)),
    "罐体密封壁": WallDef("罐体密封壁", "wall.clinic.tank", "#8395ac", 5, 3, 2, 180, spawn_realms=("white_sanatorium",)),
    "白瓷工作台": WallDef("白瓷工作台", "wall.clinic.bench", "#b1aab8", 3, 2, 2, 100,
                       path_clickable=True, spawn_realms=("white_sanatorium",)),
    "封口药箱": WallDef("封口药箱", "wall.clinic.case", "#9e9c81", 2, 2, 1, 70,
                      path_clickable=True, spawn_realms=("white_sanatorium",)),
    "净衣推车": WallDef("净衣推车", "wall.clinic.cart", "#8ca8a1", 2, 2, 1, 80,
                      pushable=True, path_clickable=True, spawn_realms=("white_sanatorium",)),
})
WALL_DEFINITIONS["排气口"] = WallDef(
    "排气口", "wall.hospital_exhaust", "#7898a8", 3, 2, 1, 90,
    spawn_realms=("white_sanatorium",), gas_dissipation_multiplier=2)
for _direction, _step, _symbol in (("北", (0, -1), "n"), ("东", (1, 0), "e"),
                                  ("南", (0, 1), "s"), ("西", (-1, 0), "w")):
    _name = "换气扇·" + _direction
    WALL_DEFINITIONS[_name] = WallDef(
        _name, "wall.hospital_fan." + _symbol, "#729ca6", 3, 2, 1, 90,
        spawn_realms=("white_sanatorium",), gas_push_direction=_step)

# ---- §12 F：三种新增环境设施（2026-10-20）----
# 与「随机发光点」的区别在于完整的生命周期：有定义、有投放渠道、有开关或
# 消耗状态、破坏/断电/熄灭后立刻不再发光（判定见 data/light_sources.py：
# 墙类来源一律要求 cell.light_on，余烬灯盏额外要求 cell.flame>0）。
# 数量由 core/fixtures.py 的投放趟控制，**不进** DEPTH_WALL_POOL——它们不是
# 通用墙体材料，不该按普通墙的色块预算满地铺。
WALL_DEFINITIONS.update({
    # 浅层侧室/走廊转角的固定小灯：1 格高、可徒手打碎、站邻格可开关。
    "嵌壁梦灯": WallDef(
        "嵌壁梦灯", "wall.dream_niche_lamp", "#f2e3bd", 1, 1, 1, 30,
        "灯罩里透出一口暖息", hand_breakable=True, light_radius=2),
    # 玩具的回忆：绑定真实通电状态的灯架，断电即灭（core/fixtures.sync_powered_fixtures）。
    "弧光灯架": WallDef(
        "弧光灯架", "wall.arc_lamp_rig", "#cfe4f2", 2, 2, 1, 60,
        "臭氧与金属的焦味", "spark", light_radius=2,
        spawn_realms=("toy_memories",)),
    # 余烬廊桥：可燃灯盏，只有真实燃烧（cell.flame>0）才发光，烧尽即熄灭。
    "余烬灯盏": WallDef(
        "余烬灯盏", "wall.ember_lamp", "#d8a15e", 1, 1, 1, 45,
        "余烬的暖味", flammable=True, light_radius=2,
        spawn_realms=("ember_bridge",)),
})

# 三种设施的识别集合（生成、开关、审计共用一份名单）。
LIGHT_FIXTURE_KINDS = frozenset({"嵌壁梦灯", "弧光灯架", "余烬灯盏"})
# 其中「按 flame 发光」的设施：没有真实燃烧就不发光。
FLAME_FIXTURE_KINDS = frozenset({"余烬灯盏"})
# 其中「按通电发光」的设施：每回合由电路结算同步 light_on。
POWERED_FIXTURE_KINDS = frozenset({"弧光灯架"})

# 地面容器：只占格子表面的低矮固体（高度 1），液体气体可共存越过；
# 完整状态下内容物封存不外流，破坏后留在原格随流动散出。
CONTAINER_KINDS = frozenset({"记忆容器", "思绪容器"})

# 台子（木桌子/石台）：1 格高、不可穿过的固体，台面承载物品与事件地点。
# 玩家站相邻格点击台子即可取走台面上的东西（见 core.uproot/ take_from）。
# 台子（木桌子/石台/陷阱石台/机关石台）：1 格高、不可穿过的固体，台面承载物品
# 与事件地点。陷阱/机关石台取物或回应时会触发其逻辑（见 core/logic.py）。
TABLE_KINDS = frozenset({"木桌子", "石台", "陷阱石台", "机关石台"})

# 承载面（2026-10-22）：能放东西、能被「从台面取走」的一切台面。
# 比 TABLE_KINDS 多两类**可步行**的工作面——医院 `白瓷工作台` 与图书馆
# `胡桃木书架`：它们是摆在场上的家具、玩家可以走过去，但「东西搁在上面
# 看得见、伸手能拿」这件事跟台子完全一样。刻意**不**并进 TABLE_KINDS：
# TABLE_KINDS 的成员被 `SOLID_KINDS` 收编（会变成不可穿行的固体），
# 把这两类并进去等于顺手改了两栋建筑的碰撞与连通性。
SURFACE_KINDS = TABLE_KINDS | frozenset({"白瓷工作台", "胡桃木书架"})

# 门种集合（2026-10-10）：踏上即开/恒阻视线/「放大」挤不过等门机制一律按此集合
# 识别，不再写死 == "门"。「门」是主梦关卡门；「木门」是千禧园木屋门（🚪 emoji，
# 同机制、不同字形与硬度）——没有这条集合，木门关上千禧园木屋就永远进不去。
DOOR_KINDS = frozenset({"门", "木门"})

# 可步行特征墙：数据上记为墙种但生物可以直接穿过（solid=False）。
# 云块额外阻挡液体（见 core._simulate_liquid_pass），枕木吸收脚步声。
for _fuel_wall in ("不稳定燃料墙", "潮解纸墙", "蜡化记忆墙", "烛泪柱", "枕木",
                   "黄粱米堆", "无光绒墙", "木桌子", "吸光苔墙", "倦怠棉垛"):
    WALL_DEFINITIONS[_fuel_wall] = replace(WALL_DEFINITIONS[_fuel_wall], flammable=True)

WALKABLE_FEATURE_WALLS = frozenset({"云块", "枕木"})

# 《新材料》独立固体：贴空气生成、不埋入墙体内部（见 core._assign_wall_kinds）。
FEATURE_WALLS = frozenset({"清醒石", "梦晶簇", "烛泪柱", "枕木", "云块", "黄粱米堆"})

# 图鉴「材料三类（地面 / 墙 / 固体）」里算**固体**的墙种（2026-09-18）。
# 判据是「它是摆在场上的物件，而不是构成地形的墙」——台子与容器都是
# 1 格高的独立固体、自带交互（台面放物 / 封存内容物），图鉴里归「固体」
# 比归「墙」更贴近玩家的理解。⚠️ 这只是**分类视图**，不要拿它去参与生成：
# 生成侧「贴空气生成、不埋进墙体」用的是 FEATURE_WALLS（见 core.generation）。
SOLID_KINDS = (FEATURE_WALLS | TABLE_KINDS | CONTAINER_KINDS
                  | frozenset({"空心积木墙", "石墨烯晶格", "玉米淀粉墙"}))

# 透明墙体：坚实但不遮挡视线。
class _TransparentWalls:
    """透明墙种的实时视图，按 `WallDef.transparent` 现查。

    位面墙体模块（library 等）在walls.py 之后才把定义并入 `WALL_DEFINITIONS`，
    任何 frozenset 快照都会漏掉它们——图书馆「玻璃书障」声明透明却被视线
    当成实心墙，就是这条快照造成的。
    """

    __slots__ = ()

    def __contains__(self, kind: object) -> bool:
        definition = WALL_DEFINITIONS.get(str(kind or ""))
        return bool(definition is not None and definition.transparent)

    def __iter__(self):
        return (name for name, definition in WALL_DEFINITIONS.items()
                if definition.transparent)

    def __len__(self) -> int:
        return sum(1 for definition in WALL_DEFINITIONS.values() if definition.transparent)


TRANSPARENT_WALLS = _TransparentWalls()

DEFAULT_WALL = "压实聚合墙"

# 新墙体的出场层级（内容扩展计划 §2 层型适配）：
# 潮解纸墙 1–3 层、空心积木墙 1–2 层、蜡化记忆墙 4–6 层、
# 活字字模墙 5–6 层、尖啸瓷墙 6 层起；玻璃幕墙全层通用。
_SHALLOW_BASE = ("压实聚合墙", "玻璃幕墙", "反光玻璃墙", "吸声聚合墙", "冷凝囊壁", "不稳定燃料墙")
# 《新材料》的独立固体：低频散布在所有层（预算见 WALL_SPAWN_BUDGET）。
_FEATURE_WALLS = ("清醒石", "梦晶簇", "烛泪柱", "枕木", "云块", "黄粱米堆")

DEPTH_WALL_POOL: dict[int, tuple[str, ...]] = {
    1: (*_SHALLOW_BASE, "潮解纸墙", "空心积木墙", *_FEATURE_WALLS),
    2: (*_SHALLOW_BASE, "潮解纸墙", "空心积木墙", *_FEATURE_WALLS),
    3: (*_SHALLOW_BASE, "潮解纸墙", *_FEATURE_WALLS),
    4: (*_SHALLOW_BASE, "蜡化记忆墙", *_FEATURE_WALLS),
    5: (*_SHALLOW_BASE, "蜡化记忆墙", "活字字模墙", *_FEATURE_WALLS),
    6: (*_SHALLOW_BASE, "蜡化记忆墙", "活字字模墙", "尖啸瓷墙", *_FEATURE_WALLS,
        # 扩展包 v1 特征墙（REGION_WALL_RANGES 管深度）
        "回魂陶俑", "镜湖板", "倦怠棉垛"),
}
# 扩展包 v1：浅层 1-10 加倦怠棉垛（REGION_WALL_RANGES 管深度衰减）
for _d in range(1, 11):
    if _d in DEPTH_WALL_POOL:
        DEPTH_WALL_POOL[_d] = (*DEPTH_WALL_POOL[_d], "倦怠棉垛")

# 幻觉空间（11–20 层）：以坚硬聚合墙为主墙体。
for _depth in range(7, 21):
    DEPTH_WALL_POOL[_depth] = (*_SHALLOW_BASE, "尖啸瓷墙", "活字字模墙", "蜡化记忆墙", *_FEATURE_WALLS,
                               "石墨烯晶格", "玉米淀粉墙",
                               # 扩展包 v1 特征墙（REGION_WALL_RANGES 管深度衰减）
                               "回魂陶俑", "镜湖板", "倦怠棉垛", "吸光苔墙")
# 无意识领域（21–27 层）：主墙体（致密聚合物×4 + 梦魇岩）由
# _assign_wall_kinds 按层单独处理（70/30 混合）；这里登记的是
# 特殊墙与无意识领域专属特征墙（贴近/破坏机制见 materials_sim）。
for _depth in range(21, 28):
    DEPTH_WALL_POOL[_depth] = (
        *_SHALLOW_BASE, "尖啸瓷墙", "蜡化记忆墙", "铅板", "盐晶壁", *_FEATURE_WALLS,
        "呜咽晶柱", "沉思铁幕", "无光绒墙", "蚀梦菌毯", "静默碑岩",
        "无意识结晶", "悔恨之锚", "千层叠岩", "回响黑曜岩",
        # 扩展包 v1 特征墙
        "吸光苔墙", "回魂陶俑", "镜湖板",
    )

# ---- 区域限制登记（条件限制：主区域 + 距离衰减）----
# (起始层, 终止层, 渗出范围)。衰减权重由 mapgen.region_falloff 计算，
# 用于特征墙色块预算的缩放；主墙体的 70/30 由生成器按层切换。
REGION_WALL_RANGES: dict[str, tuple[int, int, int]] = {
    "呜咽晶柱": (21, 27, 3),
    "沉思铁幕": (21, 27, 3),
    "无光绒墙": (21, 27, 3),
    "蚀梦菌毯": (21, 27, 3),
    "静默碑岩": (21, 27, 3),
    "无意识结晶": (21, 27, 3),
    "悔恨之锚": (21, 27, 3),
    "千层叠岩": (21, 27, 3),
    "回响黑曜岩": (21, 27, 3),
    "梦魇岩": (21, 27, 6),
    "赤致密聚合墙": (21, 27, 6),
    "黄致密聚合墙": (21, 27, 6),
    "蓝致密聚合墙": (21, 27, 6),
    "绿致密聚合墙": (21, 27, 6),
    # Excel 新一批：幻觉空间起偶尔出现，越深越多。
    "石墨烯晶格": (11, 27, 4),
    # 扩展包 v1 特征墙
    "吸光苔墙": (21, 27, 3),
    "回魂陶俑": (12, 18, 3),
    "镜湖板": (1, 27, 4),
    "倦怠棉垛": (1, 10, 3),
}

# 墙体生成的「色块预算」：(色块数上限, 面积除数, 单块最大尺寸)。
# 色块数量按 1 + 墙体面积 / 面积除数 计算并取上限，功能墙默认
# (6, 240, 9)。玻璃幕墙的生成率介于普通压实墙与功能墙之间：块更多、
# 每块更大（约占内部墙体的一成）；吸声聚合墙只比同类功能墙略高一点。
DEFAULT_WALL_SPAWN_BUDGET = (6, 240, 9)
WALL_SPAWN_BUDGET: dict[str, tuple[int, int, int]] = {
    "玻璃幕墙": (14, 90, 16),
    "吸声聚合墙": (11, 170, 12),
    # 无意识领域特征墙：低频小片。
    "呜咽晶柱": (2, 350, 2),
    "沉思铁幕": (2, 300, 3),
    "无光绒墙": (3, 320, 4),
    "蚀梦菌毯": (3, 300, 3),
    "静默碑岩": (2, 350, 2),
    "无意识结晶": (2, 350, 2),
    "悔恨之锚": (2, 380, 2),
    "千层叠岩": (1, 420, 3),
    "回响黑曜岩": (2, 340, 2),
    # 无意识领域常见墙的「渗出」预算（21 层内作为主墙体不走这里）。
    "梦魇岩": (2, 200, 6),
    "赤致密聚合墙": (1, 400, 4),
    "黄致密聚合墙": (1, 400, 4),
    "蓝致密聚合墙": (1, 400, 4),
    "绿致密聚合墙": (1, 400, 4),
    # 《新材料》独立固体：低频小片散布。
    "清醒石": (1, 600, 2),
    "梦晶簇": (2, 400, 2),
    "烛泪柱": (2, 350, 2),
    "枕木": (3, 300, 3),
    "云块": (3, 320, 3),
    "黄粱米堆": (1, 500, 2),
    # Excel 新一批：低频中片。
    "石墨烯晶格": (2, 320, 4),
    "玉米淀粉墙": (3, 280, 5),
}


def wall_spawn_budget(kind: str) -> tuple[int, int, int]:
    return WALL_SPAWN_BUDGET.get(kind, DEFAULT_WALL_SPAWN_BUDGET)


def wall_pool_for_depth(depth: int, *, realm_id: str = "") -> tuple[str, ...]:
    base = DEPTH_WALL_POOL.get(max(1, min(27, depth)), DEPTH_WALL_POOL[1])
    # §12 F：三种环境设施**不进**通用墙体池。它们是有生命周期的灯具
    # （开关/通电/燃烧），数量由 core/fixtures.py 的投放趟控制；混进池里
    # 就会按普通墙的色块预算成片铺开，还绕过了通电与燃料状态。
    pool = [k for k in base if k not in LIGHT_FIXTURE_KINDS and (
            not WALL_DEFINITIONS[k].spawn_realms
            or realm_id in WALL_DEFINITIONS[k].spawn_realms)]
    pool.extend(k for k, d in WALL_DEFINITIONS.items()
                if d.spawn_realms and realm_id in d.spawn_realms
                and k not in pool and k not in LIGHT_FIXTURE_KINDS)
    return tuple(pool)


def wall_def(kind: str) -> WallDef:
    return WALL_DEFINITIONS.get(kind, WALL_DEFINITIONS[DEFAULT_WALL])
from .library import WALLS as LIBRARY_WALLS
WALL_DEFINITIONS.update(LIBRARY_WALLS)
