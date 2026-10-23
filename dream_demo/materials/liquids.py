"""液体目录：液态记忆的定义表。"""

from __future__ import annotations

from ..mapgen.layout import region_falloff
from .definitions import LiquidDef


# 原有通用液体不自然挥发；疗所专属挥发液使用独立周期与 1:1 转化。
# 2026-10-12 曾全表近似减半 max_flow（液体摊得太快吃不到接触效果）；
# 2026-10-15 混乱化改造：max_flow ≥10 的液体全表 ×2（撤销下调并加倍），
# ≤8 的慢浆样本（凝固的尖叫/梦醚/银盐悬液/凝胶基液/纤维蛋白胶等）保持
# 「几乎不流」档位。红酒 30（30 % 4 == 2）仍是「除 4 有余项」的流速样本，
# 逐拍流动的余项分配机制照旧有真实材料覆盖。
LIQUID_DEFINITIONS: dict[str, LiquidDef] = {
    # contact_noise 留空（−1）的液体按黏度推导接触声：稀液 R=2、黏稠 R=1。
    "水": LiquidDef("水", "#4ca6e8", 48, 1),
    # 红酒 15（而非 ÷2 的 30 减半）：保留一个「除 4 有余项」的流速样本，
    # 让逐拍流动的余项分配机制始终有真实材料可以覆盖到。
    "红酒": LiquidDef("红酒", "#8f2942", 30, 2),
    "黑墨": LiquidDef("黑墨", "#44334f", 6, 5),
    "导电液态记忆": LiquidDef("导电液态记忆", "#26d6df", 44, 1, contact_effect="传导冲击"),
    "镇静溶液": LiquidDef("镇静溶液", "#82d6a3", 20, 3, contact_effect="镇静"),
    "燃油": LiquidDef("燃油", "#d4a72c", 32, 2, flammable=True),
    "酸蚀液": LiquidDef("酸蚀液", "#c8e14b", 8, 3, contact_effect="腐蚀创伤"),
    "纸浆": LiquidDef("纸浆", "#b9a582", 6, 5, contact_effect="迟滞", flammable=True),
    "显影液": LiquidDef("显影液", "#d4b0e8", 24, 2, contact_effect="显影"),
    "稀释记忆": LiquidDef("稀释记忆", "#7ec8b4", 48, 1, contact_effect="温热"),
    "泪滴溶液": LiquidDef("泪滴溶液", "#86c7f0", 24, 2, contact_effect="心智修复"),
    "忘川水": LiquidDef("忘川水", "#8fa8c8", 44, 1, contact_effect="遗忘"),
    "流动月光": LiquidDef("流动月光", "#f5f0c8", 32, 1, contact_effect="月光"),
    "熔化的时间": LiquidDef("熔化的时间", "#c8b88a", 6, 4, contact_effect="时间熔化"),
    "彩虹牛奶": LiquidDef("彩虹牛奶", "#f0c8e0", 32, 2, contact_effect="放大"),
    "灵视之血": LiquidDef("灵视之血", "#c84040", 20, 2, contact_effect="诅咒灵视"),
    "蜂蜜": LiquidDef("蜂蜜", "#d8a827", 6, 4, contact_effect="蜜裹"),
    "以太": LiquidDef("以太", "#c8e8f0", 48, 1, contact_effect="悬浮"),
    "熔融蜡烛": LiquidDef("熔融蜡烛", "#f5e8b8", 20, 3, flammable=True),
    "水银": LiquidDef("水银", "#b0b8c0", 6, 5, contact_effect="气体易感", contact_noise=3),  # 站上：本格气体触发浓度 −5（至少 1）
    "液氮": LiquidDef("液氮", "#a8e0f5", 36, 1, contact_effect="冻僵", contact_noise=1),
    "超临界流体": LiquidDef("超临界流体", "#d8e878", 40, 1, contact_effect="剥蚀墙体"),
    # ---- 无意识领域（21–27）：极端液体（leak=6）----
    "无念黑渊": LiquidDef("无念黑渊", "#1a1a2e", 8, 4, contact_effect="失忆"),
    "熔念金属": LiquidDef("熔念金属", "#c86a2e", 28, 2, contact_effect="灼念", contact_noise=3,
                       light_radius=2, light_threshold=12),
    "静滞之泪": LiquidDef("静滞之泪", "#a8c8d8", 6, 5, contact_effect="时滞"),
    "星辉露": LiquidDef("星辉露", "#f0e8b8", 48, 1, contact_effect="星辉",
                      light_radius=1, light_threshold=8),
    "噩梦纤维": LiquidDef("噩梦纤维", "#5a3a6a", 20, 3, contact_effect="噩梦"),
    "原初混沌": LiquidDef("原初混沌", "#8a8ac8", 32, 1, contact_effect="混沌"),
    # Excel 新一批：液氦——超流体，扩散无视地势、能灭火、不赋予征兆。
    "液氦": LiquidDef("液氦", "#c8f4ff", 80, 1, contact_effect="", flammable=False,
                      ignores_terrain=True, extinguishes_fire=True, contact_noise=1),
    # ---- 反应产物批次（2026-09-18，materials/reactions.py）：只由配方混合产生，
    # 不进任何生成池/掉落表；一律不赋予征兆（接触效果为空=惰性产物）。
    "蜜酿": LiquidDef("蜜酿", "#d88a4a", 24, 2),
    "定影墨": LiquidDef("定影墨", "#2e2440", 6, 4),
    "蚀金浆": LiquidDef("蚀金浆", "#e0c84b", 8, 3),
    "血蜡膏": LiquidDef("血蜡膏", "#a84858", 8, 3, flammable=True),
    "蜜灰膏": LiquidDef("蜜灰膏", "#b89a70", 6, 5),
    # ---- 内容扩展包 v1（2026-09-20，梦层内容扩展包 v1.xlsx）----
    # 电解黏液：黏（移动变慢）且微弱导电——可燃链与电路环境的中间一环。
    "电解黏液": LiquidDef("电解黏液", "#e0c040", 8, 4, contact_effect="电解黏着"),
    # 液化的回声：站上声波脉冲半径 ×2（声音流）。
    "液化的回声": LiquidDef("液化的回声", "#90c8d8", 28, 2, contact_effect="回声放大", contact_noise=3),
    # 记忆泡沫：下一次创伤 −2（吸收后消散）。
    "记忆泡沫": LiquidDef("记忆泡沫", "#e8e0f0", 20, 3, contact_effect="缓冲"),
    # 安眠树脂：站上 2 回合进入安眠（无法行动但快速恢复想象力）。
    "安眠树脂": LiquidDef("安眠树脂", "#7a8a5a", 6, 5, contact_effect="安眠"),
    # 磁化液态记忆：被缓慢拖向最近的金属性固体。
    "磁化液态记忆": LiquidDef("磁化液态记忆", "#5a7a9a", 36, 2, contact_effect="磁引"),
    # 显像墨：视野内所有异象（含伪装/残影）显形 6 回合。
    # 2026-09-21 换色：旧 #3a2a4a 与黑墨 #44334f / 定影墨 #2e2440 / 噩梦纤维
    # #5a3a6a 同处暗紫色带（色相角差 ≤10°），地图上根本分不清是哪池液体。
    # 新 #2a6a5a（墨绿）按「双口径」判据与**全部**其它液体可分辨
    # （复用 tests/test_panel_backgrounds.py 的思路：有色比色相 ≥25°，
    #   亮度差 ≥0.30 兜底）， 且「墨绿」仍是墨的意象。
    "显像墨": LiquidDef("显像墨", "#2a6a5a", 9, 4, contact_effect="显像"),
    # 逐光溶液：向视野内最亮的光源流动（自主移动，materials_sim 后续批次）。
    "逐光溶液": LiquidDef("逐光溶液", "#f0e8a0", 48, 1),
    # 凝固的尖叫：心智 −2/回合，但视野 +1。
    "凝固的尖叫": LiquidDef("凝固的尖叫", "#c84858", 8, 5, contact_effect="惊惧"),
    "门之泪": LiquidDef("门之泪", "#b8d0e8", 6, 3, contact_effect="门之泪"),
    # Hospital sources are exclusive; carried quantities still use normal physics.
    "淋巴液": LiquidDef("淋巴液", "#d5e9b7", 6, 3, spawn_realms=("white_sanatorium",)),
    "脑脊液": LiquidDef("脑脊液", "#a8d5ed", 24, 2, spawn_realms=("white_sanatorium",)),
    "洗兆液": LiquidDef("洗兆液", "#b5e8d5", 20, 2, evaporation=1, evaporation_gas="消兆薄雾",
                      evaporation_period=4, evaporation_ratio=1, spawn_realms=("white_sanatorium",)),
    "梦醚": LiquidDef("梦醚", "#c4b0dd", 8, 3, evaporation=1, evaporation_gas="梦醚气", flammable=True,
                     evaporation_period=3, evaporation_ratio=1, spawn_realms=("white_sanatorium",)),
    "凝胶基液": LiquidDef("凝胶基液", "#d6c5ad", 1, 6, flow_period=4, spawn_realms=("white_sanatorium",)),
    "纤维蛋白胶": LiquidDef("纤维蛋白胶", "#dfd6aa", 1, 8, flow_period=6,
                         gas_flow_divisor=2, spawn_realms=("white_sanatorium",)),
    "晨醒溶液": LiquidDef("晨醒溶液", "#a4dde8", 8, 2, evaporation=1, evaporation_gas="醒素薄气",
                       evaporation_period=4, evaporation_ratio=1, spawn_realms=("white_sanatorium",)),
    "银盐悬液": LiquidDef("银盐悬液", "#bfc5db", 6, 4, light_radius=1, spawn_realms=("white_sanatorium",)),
    "注射用梦水": LiquidDef("注射用梦水", "#9ac6e0", 28, 1, evaporation=1, evaporation_gas="无垢蒸汽",
                        extinguishes_fire=True, evaporation_period=6, evaporation_ratio=1,
                        spawn_realms=("white_sanatorium",)),
    # Palace-only fluids: wet ink slowly turns into an obscuring ink mist, while
    # bookbinder's glue barely moves and briefly slows anyone crossing it.
    "湿墨": LiquidDef("湿墨", "#315b4b", 5, 5, contact_effect="书页迟滞",
                    evaporation=1, evaporation_gas="墨雾",
                    evaporation_period=5, evaporation_ratio=2, flow_period=3,
                    spawn_realms=("library_palace",)),
    "稀墨": LiquidDef("稀墨", "#6f9277", 24, 3, contact_effect="导电",
                    evaporation=1, evaporation_gas="墨雾", evaporation_period=6,
                    evaporation_ratio=1, spawn_realms=("library_palace",)),
    "书脊胶": LiquidDef("书脊胶", "#b89a61", 1, 7, contact_effect="胶迟滞", flow_period=6,
                    spawn_realms=("library_palace",)),
}

DEFAULT_LIQUID = "水"

# 无意识领域专属液体的区域登记：(起始层, 终止层, 渗出范围)。
REGION_LIQUID_RANGES: dict[str, tuple[int, int, int]] = {
    "无念黑渊": (21, 27, 6),
    "熔念金属": (21, 27, 6),
    "静滞之泪": (21, 27, 6),
    "星辉露": (21, 27, 6),
    "噩梦纤维": (21, 27, 6),
    "原初混沌": (21, 27, 6),
    "液氦": (21, 27, 5),
    "液化的回声": (11, 20, 3),
    "记忆泡沫": (1, 10, 3),
    "安眠树脂": (1, 8, 3),
    "磁化液态记忆": (13, 19, 3),
    "显像墨": (21, 26, 4),
    "凝固的尖叫": (22, 27, 4),
    # 梦中梦专属液体：主梦池排除（region_falloff 对 (0,0,0) 恒 0）
    "门之泪": (0, 0, 0),
}


def liquid_pool_for_depth(depth: int, *, realm_id: str = "") -> tuple[tuple[str, float], ...]:
    """按层取加权液体池：无意识领域液体在区域外按层数距离衰减（leak=6）。"""
    pool: list[tuple[str, float]] = []
    for kind, definition in LIQUID_DEFINITIONS.items():
        if definition.spawn_realms and realm_id not in definition.spawn_realms:
            continue
        region = REGION_LIQUID_RANGES.get(kind)
        if region is None:
            pool.append((kind, 1.0))
            continue
        lo, hi, leak = region
        weight = region_falloff(depth, lo, hi, leak)
        if weight > 0:
            pool.append((kind, weight))
    return tuple(pool)


def liquid_def(kind: str) -> LiquidDef:
    return LIQUID_DEFINITIONS.get(kind, LIQUID_DEFINITIONS[DEFAULT_LIQUID])


def liquid_contact_noise(kind: str) -> int:
    """踩入液面的接触声径：显式值优先，否则稀液 2／黏稠 1。"""
    definition = LIQUID_DEFINITIONS.get(kind)
    if definition is None:
        return 2
    if definition.contact_noise >= 0:
        return definition.contact_noise
    return 2 if definition.viscosity <= 2 else 1
