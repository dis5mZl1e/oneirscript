"""气体目录：弥散印象的定义表。"""

from __future__ import annotations

from ..mapgen.layout import region_falloff
from .definitions import GasDef


# 2026-10-12 曾全表 (n+1)//2 下调 max_diffusion（云摊得太快吃不到吸入效果）；
# 2026-10-15 混乱化改造：全表 max_diffusion ×2 撤销下调并加倍——气体摊得开、
# 铺得广，引爆/吸附/吸入等环境互动更容易成气候。消散（dissipation 1~3 点/
# 周期）保持原值；全局消散周期 GAS_DECAY_INTERVAL 100→150（core/constants.py），
# 心智失序档另按 +2×档位放慢（materials_sim._apply_gas_dissipation）。
GAS_DEFINITIONS: dict[str, GasDef] = {
    "水蒸气": GasDef("水蒸气", "gas.steam", "#b8e1e8", 30, 1, 25),
    "黑烟": GasDef("黑烟", "gas.smoke", "#55565c", 10, 1, 80, blocks_sight=True),
    "毒气": GasDef("毒气", "gas.poison", "#a9c846", 24, 2, 45, "毒性吸入"),
    "麻醉雾": GasDef("麻醉雾", "gas.sedative", "#b89ac9", 8, 1, 55, "迟钝吸入"),
    "酒气": GasDef("酒气", "gas.alcohol", "#9e5964", 28, 2, 20, "醉意吸入"),
    "遮蔽弥散印象": GasDef("遮蔽弥散印象", "gas.obscuring", "#d151bd", 16, 1, 70, "遮蔽吸入"),
    "可燃气体": GasDef("可燃气体", "gas.flammable", "#e39936", 36, 2, 30, "可燃附着", flammable=True),
    "灰尘云": GasDef("灰尘云", "gas.dust", "#b7a78b", 10, 3, 35, "扬尘", sight_attenuation=0.5),
    "回声雾": GasDef("回声雾", "gas.echo", "#8fb3d9", 18, 2, 30, "回声扩散"),
    "灼热蒸汽": GasDef("灼热蒸汽", "gas.scald", "#f2b5a0", 30, 2, 25, "灼伤吸入"),
    "静电尘": GasDef("静电尘", "gas.static", "#cfe8a0", 22, 1, 20, "麻痹吸入"),
    "催眠雾": GasDef("催眠雾", "gas.hypno", "#d9c2f0", 8, 1, 60, "深度睡眠"),
    "清醒香气": GasDef("清醒香气", "gas.clarity", "#45d9c0", 30, 3, 15, "清朗吸入"),
    "安眠香": GasDef("安眠香", "gas.poppy", "#ef7ba5", 16, 2, 40, "安眠吸入"),
    "褪黑素雾": GasDef("褪黑素雾", "gas.melatonin", "#7b68ee", 16, 2, 40, "褪黑吸入"),
    "咖啡因气": GasDef("咖啡因气", "gas.caffeine", "#d0342c", 24, 2, 25, "亢奋吸入"),
    "酒精蒸气": GasDef("酒精蒸气", "gas.spirit", "#ececec", 28, 2, 20, "醉意吸入", flammable=True),
    "辐射尘埃": GasDef("辐射尘埃", "gas.radiation", "#5eff5e", 18, 1, 35, "辐射病吸入"),
    # ---- 无意识领域（21–27）：极端气体（leak=6）----
    "呢喃": GasDef("呢喃", "gas.whisper", "#98b8d8", 18, 2, 35, "呢喃吸入"),
    "虚无孢子": GasDef("虚无孢子", "gas.void_spore", "#8878a8", 12, 2, 55, "虚无吸入"),
    "溶梦酸雾": GasDef("溶梦酸雾", "gas.dream_acid", "#d8a8b8", 24, 3, 40, "溶梦吸入"),
    "噩梦气息": GasDef("噩梦气息", "gas.nightmare_breath", "#6a4a8a", 16, 2, 45, "噩梦吸入"),
    "晨霜清气": GasDef("晨霜清气", "gas.morning_frost", "#d8f0f5", 22, 3, 15, "晨霜吸入"),
    # ---- 反应产物批次（2026-09-18，materials/reactions.py）：只由配方混合产生，
    # 不赋予征兆（吸入效果为空=惰性产物），只挂既有视野衰减旗标。
    "蚀骨瘴": GasDef("蚀骨瘴", "gas.poison", "#c8d060", 18, 3, 45, "", sight_attenuation=0.6),
    "无意识低语": GasDef("无意识低语", "gas.void_spore", "#6858a0", 12, 3, 55, "", sight_attenuation=0.7),
    "电浆雾": GasDef("电浆雾", "gas.static", "#7ee8c0", 22, 1, 30, "",
                   light_radius=1, light_threshold=6),
    # ---- 内容扩展包 v1（2026-09-20）----
    "褪色雾": GasDef("褪色雾", "gas.smoke", "#b8b8c0", 10, 2, 50, "褪色吸入"),
    "记忆粉尘": GasDef("记忆粉尘", "gas.dust", "#d0c8e0", 16, 3, 30, "恍惚吸入"),
    "导电雾": GasDef("导电雾", "gas.static", "#60d8e8", 12, 1, 35, "传导吸入", flammable=True),
    "亢奋蒸汽": GasDef("亢奋蒸汽", "gas.steam", "#e8a050", 18, 2, 25, "亢奋吸入"),
    "死寂气团": GasDef("死寂气团", "gas.smoke", "#4a4a5a", 6, 1, 60, "静默吸入"),
    "虹彩雾霭": GasDef("虹彩雾霭", "gas.hypno", "#c8a0d8", 12, 2, 45, "迷幻吸入"),
    # 梦中梦·门之回廊（2026-09-21）
    "门隙之风": GasDef("门隙之风", "gas.smoke", "#a8b8d0", 14, 2, 40, "门扉眩晕吸入"),
    # 梦中梦·千禧园（2026-10-10）：环境弥散印象——老猫的握手杂音。设计标注
    # 「可选」，定位纯氛围（§3），按 2026-09-18 反应产物先例做惰性气体
    # （吸入效果为空=不挂征兆）；与同名消耗品「拨号音」（dial_tone）各归
    # 各的注册表，显示名共用一条 i18n 键。
    "拨号音": GasDef("拨号音", "gas.smoke", "#c0a880", 14, 2, 40),
}

DEFAULT_GAS = "水蒸气"

GAS_DEFINITIONS.update({
    "纸尘": GasDef("纸尘", "gas.library.paper_dust", "#b39a6c", 8, 1, 15,
                  sight_attenuation=.82, dissipation_period=4, spawn_realms=("library_palace",)),
    "墨雾": GasDef("墨雾", "gas.library.ink_mist", "#51665e", 6, 1, 35,
                  sight_attenuation=.62, dissipation_period=4, spawn_realms=("library_palace",)),
    "消兆薄雾": GasDef("消兆薄雾", "gas.steam", "#8fcbbd", 8, 1, 0,
                      dissipation_period=3, spawn_realms=("white_sanatorium",)),
    # opacity=8 时遮蔽强度门槛（SIGHT_OBSCURE_MIN=12）需要浓度 150，超出 cell.gas 上限 100，
    # 声明的 sight_attenuation=.9 永远不生效；按纸尘同档薄雾取 15（门槛 80）。
    "梦醚气": GasDef("梦醚气", "gas.sedative", "#b298c9", 12, 1, 15, flammable=True,
                    sight_attenuation=.9, dissipation_period=3, spawn_realms=("white_sanatorium",)),
    "醒素薄气": GasDef("醒素薄气", "gas.clarity", "#75bdce", 12, 1, 0,
                      dissipation_period=3, spawn_realms=("white_sanatorium",)),
    "无垢蒸汽": GasDef("无垢蒸汽", "gas.steam", "#adbcc9", 16, 1, 0,
                      dissipation_period=3, spawn_realms=("white_sanatorium",)),
    "胞尘": GasDef("胞尘", "gas.dust", "#93b781", 6, 1, 0,
                  dissipation_period=4, spawn_realms=("white_sanatorium",)),
    "无菌载气": GasDef("无菌载气", "gas.steam", "#a3bbd0", 10, 1, 0,
                      dissipation_period=4, spawn_realms=("white_sanatorium",)),
})

# 无意识领域专属气体的区域登记：(起始层, 终止层, 渗出范围)。
REGION_GAS_RANGES: dict[str, tuple[int, int, int]] = {
    "呢喃": (21, 27, 6),
    "虚无孢子": (21, 27, 6),
    "溶梦酸雾": (21, 27, 6),
    "噩梦气息": (21, 27, 6),
    "晨霜清气": (21, 27, 6),
    # ---- 内容扩展包 v1（2026-09-20）：区域气体（未登记 = 全区域）----
    "褪色雾": (11, 20, 3),
    "记忆粉尘": (1, 10, 3),
    "导电雾": (12, 18, 3),
    "死寂气团": (22, 27, 4),
    "虹彩雾霭": (14, 20, 3),
    # 梦中梦专属气体（(0,0,0)=主梦任意层权重 0，只由 realm 定义散布）
    "门隙之风": (0, 0, 0),
    "拨号音": (0, 0, 0),
}


def gas_pool_for_depth(depth: int, *, realm_id: str = "") -> tuple[tuple[str, float], ...]:
    """按层取加权气体池：无意识领域气体在区域外按层数距离衰减（leak=6）。"""
    pool: list[tuple[str, float]] = []
    for kind, definition in GAS_DEFINITIONS.items():
        if definition.spawn_realms and realm_id not in definition.spawn_realms:
            continue
        region = REGION_GAS_RANGES.get(kind)
        if region is None:
            pool.append((kind, 1.0))
            continue
        lo, hi, leak = region
        weight = region_falloff(depth, lo, hi, leak)
        if weight > 0:
            pool.append((kind, weight))
    return tuple(pool)


def gas_def(kind: str) -> GasDef:
    return GAS_DEFINITIONS.get(kind, GAS_DEFINITIONS[DEFAULT_GAS])
