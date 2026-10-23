"""层型名单、抽取权重与各层的地图尺寸换算。"""

from __future__ import annotations

import random

MAP_FORMS = (
    "整齐的房间",   # BSP 递归二分：房间规整、墙体无噪点
    "破碎的房间",   # 同为房间底子，但墙体被啃噬、撒满椒盐噪点
    "居民区",       # 房间生长：从一间房向外贴着长出成片街区
    "洞穴",         # 元胞自动机（CA）平滑出的洞窟
    "迷宫",         # DFS 挖墙（递归回溯）
    "长廊",         # 极端长宽比：面积与方形层相当，长边约为短边 4 倍
    "无限房间",     # 重复模块与环形通路
    "碎影平原",     # 开阔地散布短墙与墙块（原「障碍平原」）
    "回声大厅",     # 主大厅配柱列与边室（原「大厅」）
)
# 第 1 层固定为「整齐的房间」，其权重只是占位、不参与抽取；
# 其余 8 种层型概率全均等（每种 1）。
_FORM_WEIGHTS = (1, 1, 1, 1, 1, 1, 1, 1, 1)
_FIRST_LAYER_FORM = MAP_FORMS[0]
_SPECIAL_FORMS = MAP_FORMS[1:]

_LEGACY_FORM_ALIASES = {
    "传统房间群": "整齐的房间",
    "大厅": "回声大厅",
    "障碍平原": "碎影平原",
}

# 长廊的长宽比：面积与其它方形层保持一致，长边约为短边的这个倍数。
CORRIDOR_ASPECT = 4.0
# 地图最短边：_new_mask 拒绝小于 7 的尺寸，长廊换算后同样受此约束。
_MIN_SIDE = 7

# ---- 楼层修饰符 ----
# 每层 50% 概率带一个修饰符（其余为常规楼层），带修饰符时六种等概率。
# 修饰符只影响本层的生成参数：尺寸（大型/小型）、气体率（气密）、
# 液体率（潮湿）、植物率（繁茂）、vault 率（古朴）。
LAYER_MODIFIERS = ("大型", "小型", "气密", "潮湿", "繁茂", "古朴", "精致")
MODIFIER_CHANCE = 0.5
# 大型/小型对每条边的缩放：大型边 ×1.25（面积约 ×1.56），小型边 ×0.78。
LARGE_SIDE_SCALE = 1.25
SMALL_SIDE_SCALE = 0.78
# 大型层单边上限（防止地图大到拖慢渲染）。
_LARGE_SIDE_CAP = 96
# 小型层单边下限（守住可玩性）。
_SMALL_SIDE_FLOOR = 15


def normalize_map_form(map_form: str) -> str:
    """把旧层型名映射到现名；未登记的陌生名字原样返回。"""
    if map_form in MAP_FORMS:
        return map_form
    return _LEGACY_FORM_ALIASES.get(map_form, map_form)


def layer_modifier_plan(seed: int) -> tuple[str, ...]:
    """确定性楼层修饰符计划：50% 常规（空串），其余六种等概率。"""
    rng = random.Random(seed ^ 0x0C7F1)
    plan: list[str] = []
    for _ in range(TOTAL_LAYERS):
        if rng.random() < MODIFIER_CHANCE:
            plan.append(rng.choice(LAYER_MODIFIERS))
        else:
            plan.append("")
    return tuple(plan)


def layer_modifier_for(seed: int, depth: int) -> str:
    if not 1 <= depth <= TOTAL_LAYERS:
        raise ValueError("梦层深度必须在 1 到 20 之间")
    return layer_modifier_plan(seed)[depth - 1]


def apply_dimension_modifier(width: int, height: int, modifier: str) -> tuple[int, int]:
    """把大型/小型修饰符折算进基准尺寸（其他修饰符不改尺寸）。"""
    if modifier == "大型":
        width = min(_LARGE_SIDE_CAP, round(width * LARGE_SIDE_SCALE))
        height = min(_LARGE_SIDE_CAP, round(height * LARGE_SIDE_SCALE))
    elif modifier == "小型":
        width = max(_SMALL_SIDE_FLOOR, round(width * SMALL_SIDE_SCALE))
        height = max(_SMALL_SIDE_FLOOR, round(height * SMALL_SIDE_SCALE))
    return width, height


# 梦层总数：1–10 层为浅梦境，11–20 层为幻觉空间。
TOTAL_LAYERS = 27  # 常规层（1–27）；28–30 为「深层边界」，独立生成不走层型
EPILOGUE_DEPTHS = (28, 29, 30)
# 幻觉空间的起始层。
HALLUCINATION_START = 11
# 无意识领域的起始层。
UNCONSCIOUS_START = 21

# 区域划分：区域名 + 起始层（终止层 = 下一区域起始 − 1；末区域到 TOTAL_LAYERS）。
REGIONS: tuple[tuple[str, int], ...] = (
    ("浅层梦境", 1),
    ("幻觉空间", 11),
    ("无意识领域", 21),
)


def region_for_depth(depth: int) -> str:
    """全局层数 → 区域名（梦的起始 / 浅层梦境 / 幻觉空间 / 无意识领域 / 深层边界）。"""
    if depth >= 28:
        return "深层边界"
    if depth <= 0:
        return "梦的起始"
    name = REGIONS[0][0]
    for region_name, start in REGIONS:
        if depth >= start:
            name = region_name
    return name


def region_falloff(depth: int, lo: int, hi: int, leak: int) -> float:
    """条件限制内容的层数衰减权重。

    主区域 [lo, hi] 内恒为 1.0；区域外按到边界的层数差线性衰减
    （每差 1 层失去 1/leak 的权重），衰减到 0 即彻底不出现。
    """
    if lo <= depth <= hi:
        return 1.0
    dist = (lo - depth) if depth < lo else (depth - hi)
    return max(0.0, 1.0 - dist / max(1, leak))


def layer_form_plan(seed: int) -> tuple[str, ...]:
    """Return the deterministic layer plan selected by distribution A."""
    rng = random.Random(seed ^ 0x5A17A)
    plan = [_FIRST_LAYER_FORM, *rng.choices(MAP_FORMS, weights=_FORM_WEIGHTS, k=TOTAL_LAYERS - 1)]
    present = set(plan) & set(_SPECIAL_FORMS)
    missing = [form for form in _SPECIAL_FORMS if form not in present]
    while len(present) < 2:
        form = missing.pop(rng.randrange(len(missing)))
        replace_candidates = [index for index in range(TOTAL_LAYERS - 1, 0, -1) if plan[index] == _FIRST_LAYER_FORM]
        if not replace_candidates:
            replace_candidates = [
                index
                for index in range(TOTAL_LAYERS - 1, 0, -1)
                if plan.count(plan[index]) > 1
            ]
        replace_at = replace_candidates[0]
        plan[replace_at] = form
        present.add(form)
    return tuple(plan)


def layer_form_for(seed: int, depth: int) -> str:
    if not 1 <= depth <= TOTAL_LAYERS:
        raise ValueError("梦层深度必须在 1 到 20 之间")
    return layer_form_plan(seed)[depth - 1]


def layer_dimensions(
    base_width: int,
    base_height: int,
    map_form: str,
    seed: int = 0,
    modifier: str = "",
) -> tuple[int, int]:
    """该层实际使用的地图尺寸。

    只有「长廊」会改写长宽比：面积与基准（正方形）层保持一致，长边约为短边的
    ``CORRIDOR_ASPECT`` 倍，拉长 X 轴还是 Y 轴由层种子决定。意识边界是外圈一环，
    跟着尺寸一起变，因此不需要另外处理。大型/小型修饰符先折算基准尺寸，
    再交给层型换算（长廊的大/小型同样成立）。
    """
    base_width, base_height = apply_dimension_modifier(base_width, base_height, modifier)
    if normalize_map_form(map_form) != "长廊":
        return base_width, base_height
    area = max(_MIN_SIDE * _MIN_SIDE, base_width * base_height)
    short = max(_MIN_SIDE, round((area / CORRIDOR_ASPECT) ** 0.5))
    long = max(short, _MIN_SIDE, round(area / short))
    rng = random.Random(seed ^ 0x7A51DE)
    return (long, short) if rng.random() < 0.5 else (short, long)
