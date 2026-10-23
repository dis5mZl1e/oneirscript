# -*- coding: utf-8 -*-
"""地图侧语句篡改的内容定义（docs §15，第十五节）。

纯数据：模板池、字词 → 效果与代价映射、槽类别与颜色。不含逻辑。
句子由固定模板 + 名称槽组成（规格 §3.1「不在运行时猜测中文含义」）：
字词 → 效果是写死的映射表，运行时只做填空，不做语义解析。
"""

from __future__ import annotations

# 字词定义（初值全部待测，见文档 §15.5/§15.6）。
# kind: 合法槽类别；imagination/chaos: 代价；delete: 删除级特判。
WORD_DEFS: dict[str, dict] = {
    "call": {
        "name": "呼唤",
        "slot": "anomaly",
        "imagination": 4,
        "chaos": 10,
        "note": "它会立刻发现你，并向你走来。",
    },
    "dispel": {
        "name": "退散",
        "slot": "anomaly",
        "imagination": 5,
        "chaos": 12,
        "note": "它会失去你的踪迹，转身离开一段时间；打它一下就会醒。",
    },
    "break": {
        "name": "破坏",
        "slot": "terrain",
        "imagination": 2,
        "chaos": 4,
        "note": "它会被损坏；损坏到头就会塌。",
    },
    "delete": {
        "name": "删除",
        "slot": "both",
        "imagination": 6,
        "chaos": 14,
        "note": "这个名字会被从眼前抹去。",
    },
}

# 字词在面板里的固定顺序（↑↓ 选择顺序）。
WORD_DEFS.update({
    'whisper': dict(name='低声招引', slot='anomaly', verb='whisper', imagination=2, chaos=5,
                    note='它会起疑并前往你此刻的位置调查，不会立刻锁定你。'),
    'clamor': dict(name='尖声呼唤', slot='anomaly', verb='clamor', imagination=6, chaos=16,
                   note='它会追来；你脚下还会发出基础半径 8 的声音，附近异象也可能听见。'),
    'brief_dispel': dict(name='短暂退散', slot='anomaly', verb='dispel', duration=4, imagination=3, chaos=7,
                         note='惊散 4 回合；受击会提前解除。'),
    'deep_dispel': dict(name='深深退散', slot='anomaly', verb='dispel', duration=16, imagination=7, chaos=16,
                        note='惊散 16 回合；受击仍会提前解除。'),
    'chip': dict(name='剥落', slot='terrain', verb='break', damage=25, imagination=1, chaos=2,
                 note='削去 25 点墙体完整度；崩塌仍会触发材料后果。'),
    'shatter': dict(name='崩碎', slot='terrain', verb='break', damage=70, imagination=3, chaos=7,
                    note='削去 70 点墙体完整度；坚墙未必立即崩塌。'),
    'thin': dict(name='稀薄一半', slot='fluid', verb='thin', fraction=2, imagination=2, chaos=4,
                 note='移走所选液体或气体的一半，保留剩余部分及其原有年龄。'),
    'disperse': dict(name='消散大半', slot='fluid', verb='thin', fraction=5, imagination=4, chaos=7,
                     note='移走所选液体或气体的五分之四，保留少量残余。'),
    'lure_to': dict(name='引向此处', slot='destination', verb='lure_to', imagination=4, chaos=10,
                    note='让句子里的异象前往所选环境格调查；若它看见你，仍会重新追踪你。'),
    'echo_here': dict(name='在此鸣响', slot='environment', verb='echo_here', imagination=3, chaos=8,
                      note='所选环境格发出基础半径 6 的声音；周围异象按距离听见并调查。'),
    # 材料专属字词（docs §五/六）：效果由目标格的真实材质决定，不是换文案。
    'ignite': dict(name='点燃', slot='ignite', verb='ignite', imagination=3, chaos=7,
                   note='可燃的墙、植物、气液与地上物会被点着。'),
    'soak': dict(name='浸透', slot='soak', verb='soak', imagination=2, chaos=5,
                 note='吸水的纤维材质会被水浸透；若目标本身是墙体，完整度再降 10 点（不低于 1）。'),
    # 脆性材质专属（docs §七长尾材质）：玻璃/瓷/晶类墙体沿裂纹碎开，失去**一半**
    # 当前完整度——对高完整度的脆墙比「崩碎」更狠，对残墙又更省想象力。
    'brittle': dict(name='脆裂', slot='brittle', verb='brittle', imagination=3, chaos=8,
                    note='脆性材质沿裂纹碎开：失去当前完整度的一半；崩塌仍走材料后果。'),
    # 流体几何专属（docs §九长尾材质）：改变液/气的分布而不是数量，与「稀薄」区分。
    'spill': dict(name='泼开', slot='liquid_only', verb='spread', imagination=2, chaos=5,
                  note='把所选液态记忆的一半摊到相邻可通行格；总量不变，余量保留原有年龄。'),
    'scatter': dict(name='扬散', slot='gas_only', verb='spread', imagination=2, chaos=5,
                    note='把所选弥散印象的一半扬到相邻可流通格；总量不变，余量保留原有年龄。'),
    # 植物专属（docs §十长尾材质）：拔除走真实拔植物结算，稀有植物照样给收益。
    'uproot': dict(name='拔除', slot='plant_only', verb='uproot', imagination=2, chaos=5,
                   note='把所选植物连根拔起；稀有植物按原拔除口径结算收益。'),
    # 液/气聚拢（docs §十互动）：把相邻同类流体收进所选格，总量守恒并可能触发真实反应。
    'gather_liquid': dict(name='聚流', slot='liquid_only', verb='gather', imagination=3, chaos=6,
                          note='把相邻格的液态记忆收进所选格；总量守恒，混合同格可能当场触发反应。'),
    'gather_gas': dict(name='聚气', slot='gas_only', verb='gather', imagination=3, chaos=6,
                       note='把相邻格的弥散印象收进所选格；总量守恒，混合同格可能当场触发反应。'),
    # 植物状态（docs §十一细分材质）：催生改变植株高度，枯萎把植株变干（日后更耐烧）。
    'grow': dict(name='催生', slot='plant_only', verb='grow', imagination=2, chaos=4,
                 note='低草长成高丛（遮挡视线）；已经长到头或稀有植物长不动。'),
    'wither': dict(name='枯萎', slot='plant_only', verb='wither', imagination=2, chaos=4,
                   note='让植株提前干枯：燃烧时燃料更耐久；植物本身还在。'),
    # 液体形态（docs §十一）：蒸发走材料定义里的蒸发产物；凝固按材料表立起新墙。
    'evaporate': dict(name='蒸发', slot='liquid_only', verb='evaporate', imagination=3, chaos=6,
                      note='把部分液体按它自己的蒸发产物化为气体；不会蒸发的液体给可读拒绝。'),
    'solidify': dict(name='凝固', slot='liquid_only', verb='solidify', imagination=4, chaos=9,
                     note='把可凝固的液体立成一堵新墙（完整度取墙种定义），液体消失。'),
    # 气体沉降：按材料表凝回液体，总量按比例折算。
    'settle': dict(name='沉降', slot='gas_only', verb='settle', imagination=3, chaos=6,
                   note='把部分气体凝回对应的液体；没有沉降产物的气体给可读拒绝。'),
})
WORD_DEFS['dispel']['duration'] = 10
WORD_DEFS['dispel']['note'] = '惊散 10 回合；受击会提前解除。'
WORD_ORDER: tuple[str, ...] = ('whisper', 'call', 'clamor', 'brief_dispel', 'dispel',
    'deep_dispel', 'chip', 'break', 'shatter', 'thin', 'disperse', 'delete', 'lure_to', 'echo_here',
    'ignite', 'soak', 'brittle', 'spill', 'scatter', 'uproot', 'gather_liquid', 'gather_gas',
    'grow', 'wither', 'evaporate', 'solidify', 'settle')

# Old IDs remain valid for callers, but only distinct mechanisms appear in the
# player's vocabulary. Degree selects the original definition, not a multiplier.
DEGREE_VARIANTS = {
    'break': {'gently': 'chip', 'forcefully': 'shatter'},
    'dispel': {'gently': 'brief_dispel', 'forcefully': 'deep_dispel'},
    'thin': {'forcefully': 'disperse'},
}
DEGREE_IDS = ('gently', 'forcefully')
WORD_ORDER = tuple(word for word in WORD_ORDER
                   if word not in {'chip', 'shatter', 'brief_dispel', 'deep_dispel', 'disperse'})
WORD_DEFS['thin']['name'] = '消散'

# 可吸液／纤维材质（docs §六）：只有这些地形吃「浸透」。潮解纸墙、枕木、倦怠棉垛、
# 蚀梦菌毯、吸光苔墙都是 1 格高的吸水材质；植物另行判定。
FIBER_WALLS: frozenset[str] = frozenset({'潮解纸墙', '枕木', '倦怠棉垛', '蚀梦菌毯', '吸光苔墙'})

#: 催生：低草（码 1）长成高丛（码 2）。其它码视为已经长到头。
PLANT_GROWTH: dict[int, int] = {1: 2}
#: 枯萎：把植株的燃烧燃料抬到该值；植物本身保留。
WITHER_FUEL = 12
#: 凝固：液体 → 墙体。只登记语义成立的蜡/凝胶类；未登记液体给可读拒绝。
SOLIDIFY_WALLS: dict[str, str] = {
    '熔融蜡烛': '蜡化记忆墙',
    '血蜡膏': '蜡化记忆墙',
    '凝胶基液': '梦晶簇',
}
#: 沉降：气体 → (液体, 折算比)。水蒸气最典型；麻醉雾与毒气沿用同族液体语义。
GAS_SETTLE_LIQUIDS: dict[str, tuple[str, int]] = {
    '水蒸气': ('水', 2),
    '麻醉雾': ('镇静溶液', 2),
    '毒气': ('酸蚀液', 4),
}

# 脆性材质（docs §七长尾材质）：玻璃、瓷、晶、盐一类——受「脆裂」的一半完整度伤害。
# 名单按材料语义登记，后续新增同类墙种只需在这里补一项。
BRITTLE_WALLS: frozenset[str] = frozenset({
    '玻璃幕墙', '反光玻璃墙', '尖啸瓷墙', '梦晶簇', '镜湖板',
    '白块窗', '灯箱墙', '无意识结晶', '盐晶壁', '回响黑曜岩',
})

# ---- 条件词（docs §四/五/六）----
# 条件不是同义堆砌：每一项都改变实际结算（伤害/惊散时长/代价与声响/静音/诱引强度）。
# words 为空元组 = 对任意字词可用；requirement 是运行时要求的稳定标识；
# note_by_word 在同一个条件对不同字词有不同后果时覆盖通用 note。
CONDITION_ORDER: tuple[str, ...] = ('exploit_crack', 'catch_unaware',
                                    'pay_with_noise', 'pay_with_thought',
                                    'pay_with_chaos', 'force_lure')
CONDITION_ORDER = (*DEGREE_IDS, *CONDITION_ORDER)
#: 一笔提交最多同时挂几个条件（docs §十一：三条件组合）。
MAX_CONDITIONS_PER_COMMIT = 3
CONDITION_DEFS: dict[str, dict] = {
    'gently': dict(name='轻轻', insertion='程度', words=('break', 'dispel'),
                   requirement='', imagination_delta=0, chaos_delta=0,
                   note='使用原弱档效果与代价。'),
    'forcefully': dict(name='用力', insertion='程度', words=('break', 'dispel', 'thin'),
                       requirement='', imagination_delta=0, chaos_delta=0,
                       note='使用原强档效果与代价。'),
    'exploit_crack': dict(
        name='趁虚', insertion='完整度', words=('chip', 'break', 'shatter'),
        requirement='cracked_wall', imagination_delta=1, chaos_delta=0,
        note='这面墙已有裂痕：这一笔的完整度伤害提高到 1.5 倍。',
    ),
    'catch_unaware': dict(
        name='趁它未察觉', insertion='意志',
        words=('brief_dispel', 'dispel', 'deep_dispel', 'lure_to'),
        requirement='unaware_target', imagination_delta=1, chaos_delta=0,
        note='它还没察觉：这次惊散的时长翻倍。',
        note_by_word={'lure_to': '它还没察觉：会悄悄前往调查，不会先起疑。'},
    ),
    'pay_with_noise': dict(
        name='以声代想', insertion='行动', words=(),
        requirement='', imagination_delta=-1, chaos_delta=0,
        note='效果结算后，你所在的位置发出基础半径 8 的声音；想象力少付 1 点。',
    ),
    'pay_with_thought': dict(
        name='以想代声', insertion='声响', words=('clamor',),
        requirement='', imagination_delta=2, chaos_delta=0,
        note='这次尖声呼唤不再发出声音；想象力多付 2 点。',
    ),
    # 资源转换型条件（docs §十一）：为三条件组合提供第三个可叠维度。
    'pay_with_chaos': dict(
        name='以乱代想', insertion='行动', words=(),
        requirement='', imagination_delta=-2, chaos_delta=4,
        note='想象力少付 2 点，混乱度多涨 4 点；效果本身不变。',
    ),
    # 条件与关系词的真正组合（docs §七）：把「在此鸣响/尖声呼唤」的脉冲升级为
    # 强诱引——半径内**所有**听众直接进入追踪，不再按距离梯度只起疑。
    'force_lure': dict(
        name='强诱引', insertion='声响', words=('clamor', 'echo_here'),
        requirement='', imagination_delta=2, chaos_delta=0,
        note='这一声不再按距离分档：半径内所有听见的失控意识都会径直追来。',
    ),
}

# 删除普通异象的额外代价：想象力 + 完整度/4、混乱度 +4（文档 §15.6）。
DELETE_ANOMALY_IMAGINATION_EXTRA_DIVISOR = 4
DELETE_ANOMALY_CHAOS_EXTRA = 4

# 删除墙体／物件的额外代价（2026-10-22 平衡修复）：想象力 + ceil(完整度/60)、
# 混乱度 +4。旧口径下「一刀抹掉硬墙」比「崩碎两次」更便宜，而且墙体删除不受
# 每层额度限制；现在两者都按异象同款口径收口（完整度越高越贵）。
DELETE_WALL_IMAGINATION_EXTRA_DIVISOR = 60
DELETE_WALL_CHAOS_EXTRA = 4

# 每层「删除」成功次数上限（文档 §15.5 防滥用）：异象、墙体、物件共用同一份额度。
MAX_DELETES_PER_LAYER = 2

# 槽类别 → 面板颜色（与地图既有配色一致：异象暖色/地形冷灰蓝/物件旧纸金）。
SLOT_CATEGORY_COLORS: dict[str, str] = {
    "anomaly": "#e8a08a",
    "terrain": "#9ab8d9",
    "object": "#e8c77b",
    "ground": "#9ab8d9",
}

# 类别中文名（槽置灰时的说明用）。
CATEGORY_LABELS: dict[str, str] = {
    "anomaly": "异象",
    "terrain": "地形",
    "object": "物件",
    "liquid": "液体",
    "gas": "气体",
    "ground": "地面",
}

# 句子模板池（docs §15.4）：按「主语 × 字段数量」分桶。
# 〔n0〕〔n1〕… 是名称槽占位符；slot 元数据与槽顺序一致。
# (桶键, 模板文本, 槽类别元组)
SENTENCE_TEMPLATES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ('anomaly_only','〔n0〕的轮廓映在这层梦里。',('anomaly',)),
    ('anomaly_only','眼前这段文字提到了〔n0〕。',('anomaly',)),
    ('anomaly_terrain','你看见〔n0〕，也看见〔n1〕。',('anomaly','terrain')),
    ('anomaly_terrain','〔n0〕与〔n1〕出现在同一页梦里。',('anomaly','terrain')),
    ('anomaly_terrain','你看见〔n0〕，以及〔n1〕和〔n2〕。',('anomaly','terrain','terrain')),
    ('anomaly_terrain','这一页梦写着〔n0〕、〔n1〕与〔n2〕。',('anomaly','terrain','terrain')),
    ('anomaly_terrain','视野中有〔n0〕，还有〔n1〕、〔n2〕和〔n3〕。',('anomaly','terrain','terrain','terrain')),
    ('anomaly_terrain','这一页梦写着〔n0〕，还有〔n1〕、〔n2〕与〔n3〕。',('anomaly','terrain','terrain','terrain')),
    ('env_only','眼前的字句写着〔n0〕。',('terrain',)),
    ('env_only','〔n0〕占着这段梦的一角。',('terrain',)),
    ('env_only','眼前能看见〔n0〕与〔n1〕。',('terrain','terrain')),
    ('env_only','这段梦写下了〔n0〕，还有〔n1〕。',('terrain','terrain')),
    ('env_only','〔n0〕、〔n1〕与〔n2〕落在同一页梦里。',('terrain','terrain','terrain')),
    ('env_only','眼前依次是〔n0〕、〔n1〕和〔n2〕。',('terrain','terrain','terrain')),
    ('env_only','眼前能见到〔n0〕、〔n1〕、〔n2〕与〔n3〕。',('terrain','terrain','terrain','terrain')),
    ('env_only','〔n0〕、〔n1〕、〔n2〕和〔n3〕落在同一页梦里。',('terrain','terrain','terrain','terrain')),
)

SENTENCE_TEMPLATES_EN = tuple((bucket, text, kinds) for bucket,text,kinds in (
    ('anomaly_only','The outline of 〔n0〕 shows through this dream.',('anomaly',)),
    ('anomaly_only','The words before you mention 〔n0〕.',('anomaly',)),
    ('anomaly_terrain','You see both 〔n0〕 and 〔n1〕.',('anomaly','terrain')),
    ('anomaly_terrain','〔n0〕 shares this page of the dream with 〔n1〕.',('anomaly','terrain')),
    ('anomaly_terrain','You see 〔n0〕, as well as 〔n1〕 and 〔n2〕.',('anomaly','terrain','terrain')),
    ('anomaly_terrain','This dream names 〔n0〕, 〔n1〕, and 〔n2〕.',('anomaly','terrain','terrain')),
    ('anomaly_terrain','In view are 〔n0〕, 〔n1〕, 〔n2〕, and 〔n3〕.',('anomaly','terrain','terrain','terrain')),
    ('anomaly_terrain','This dream names 〔n0〕 alongside 〔n1〕, 〔n2〕, and 〔n3〕.',('anomaly','terrain','terrain','terrain')),
    ('env_only','The words before you describe 〔n0〕.',('terrain',)),
    ('env_only','〔n0〕 occupies a corner of this dream.',('terrain',)),
    ('env_only','Before you are 〔n0〕 and 〔n1〕.',('terrain','terrain')),
    ('env_only','This dream describes 〔n0〕 beside 〔n1〕.',('terrain','terrain')),
    ('env_only','〔n0〕, 〔n1〕, and 〔n2〕 share a page of this dream.',('terrain','terrain','terrain')),
    ('env_only','Before you are 〔n0〕, 〔n1〕, and 〔n2〕.',('terrain','terrain','terrain')),
    ('env_only','Before you are 〔n0〕, 〔n1〕, 〔n2〕, and 〔n3〕.',('terrain','terrain','terrain','terrain')),
    ('env_only','〔n0〕, 〔n1〕, 〔n2〕, and 〔n3〕 share a page of this dream.',('terrain','terrain','terrain','terrain')),
))
