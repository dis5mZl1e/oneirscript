"""混乱度极高时召来的专属异象（2026-10-27 玩家需求）。

只由混乱机制召唤，不进任何普通／强烈／位面／刷新投放池：定义里同时写
``pool=False`` 与 ``spawn_only='chaos'``，投放侧按后者显式排除。

三只异象各用两枚「字符回退版线框 emoji」（与右栏锁图标同一套单色 Emoji
字体方案：WezTerm ``assume_emoji_presentation`` + 图像地图补充字体路由）：

- ``chaos.wrath`` 嗔影 👿（U+1F47F）：高伤害直线／近身爆发；
- ``chaos.hollow`` 空心者 🖤（U+1F5A4）：掏空（重伤 + 吸血自愈 + 想象流失）；
- ``chaos.false_light`` 伪光者 😇（U+1F607）：控制／污染（失焦征兆 + 迟帧光场）。

最大完整度**随当前层数成长**：``CHAOS_INTEGRITY_BASE + CHAOS_INTEGRITY_PER_DEPTH × depth``，
在召唤时以 override 写进实体（见 core/chaos_anomalies.spawn_chaos_anomaly）。
"""

from __future__ import annotations

from typing import Any

from .tamper_schema import RISK_TIERS

#: 专属投放标记；所有池构建都要排除带这个标记的定义（core/content.py）。
CHAOS_SPAWN_ONLY = "chaos"

CHAOS_WRATH_ID = "chaos.wrath"
CHAOS_HOLLOW_ID = "chaos.hollow"
CHAOS_FALSE_LIGHT_ID = "chaos.false_light"
CHAOS_ANOMALY_IDS: tuple[str, ...] = (CHAOS_WRATH_ID, CHAOS_HOLLOW_ID, CHAOS_FALSE_LIGHT_ID)

#: 最大完整度 = BASE + PER_DEPTH × 当前层数（召唤时写入，随层数成长）。
CHAOS_INTEGRITY_BASE = 14
CHAOS_INTEGRITY_PER_DEPTH = 2

#: 触发混乱门槛：与现行最高风险档「失序」下界一致（2026-10-27 为 80）。
#: 不硬编码数字——风险档位调整时这里自动跟随。
CHAOS_ANOMALY_THRESHOLD = RISK_TIERS[-1][0]
#: 当前层同时最多存在几只由混乱召唤且存活的专属异象。
CHAOS_ANOMALY_LAYER_LIMIT = 2
#: 出生点距离玩家（切比雪夫）范围。
CHAOS_SPAWN_DISTANCE = (3, 5)
#: 一次成功篡改提交后的召唤概率（混乱 > 阈值时）。
CHAOS_TAMPER_SPAWN_CHANCE = 0.30
#: 每个真实回合的成型概率（混乱 > 阈值时；极低）。
CHAOS_TIME_SPAWN_CHANCE = 0.005
#: 专属异象只在主梦 1–27 层成形；深层边界（28–30）与位面不参与。
CHAOS_ANOMALY_LAYERS = (1, 27)

CHAOS_ANOMALIES: dict[str, dict[str, Any]] = {
    CHAOS_WRATH_ID: {
        "name": "嗔影",
        "description": "它从你没说出口的那句重话里立起来，轮廓边缘一直在发烫。",
        "glyph": "\U0001F47F",
        "anomaly_kind": "强烈异象",
        "integrity": CHAOS_INTEGRITY_BASE,
        "move_time": 0.9,
        "attack_time": 0.8,
        "trauma_type": "心智创伤",
        "communicates": False,
        "drop_id": None,
        "dissolution_reward": 4,
        "vision": 9,
        "power": 6,
        "layers": [1, 27],
        "pool": False,
        "spawn_only": CHAOS_SPAWN_ONLY,
        "color": "#d65a5a",
        "skill": "嗔线：它把没消下去的火拉成一条线，沿视线烧过来。",
    },
    CHAOS_HOLLOW_ID: {
        "name": "空心者",
        "description": "胸口的位置是一个能看见后面的洞；它靠近时，先拿走你的一小块。",
        "glyph": "\U0001F5A4",
        "anomaly_kind": "强烈异象",
        "integrity": CHAOS_INTEGRITY_BASE,
        "move_time": 1.1,
        "attack_time": 1.0,
        "trauma_type": "心智创伤",
        "communicates": False,
        "drop_id": None,
        "dissolution_reward": 4,
        "vision": 8,
        "power": 7,
        "layers": [1, 27],
        "pool": False,
        "spawn_only": CHAOS_SPAWN_ONLY,
        "color": "#8a6fa8",
        "skill": "掏空之吸：它隔空对你吸气，把自己缺的那一块补回去。",
    },
    CHAOS_FALSE_LIGHT_ID: {
        "name": "伪光者",
        "description": "它顶着一圈过亮的光，光照到的地方都变得不太可信。",
        "glyph": "\U0001F607",
        "anomaly_kind": "强烈异象",
        "integrity": CHAOS_INTEGRITY_BASE,
        "move_time": 1.0,
        "attack_time": 1.0,
        "trauma_type": "心智创伤",
        "communicates": False,
        "drop_id": None,
        "dissolution_reward": 5,
        "vision": 10,
        "power": 5,
        "layers": [1, 27],
        "pool": False,
        "spawn_only": CHAOS_SPAWN_ONLY,
        "color": "#f0d890",
        "skill": "伪光注视：它把光转到你身上，你看到的东西开始对不上号。",
    },
}

#: (key, name, tier, cd, windup, reach, cells, power, duration)
#: power 是**基础直接创伤**；实际伤害按层段倍率与阶级上限结算（data/anomaly_skills），
#: 数值偏「高基础」让深层的伤害顶到强烈阶级上限，体现专属异象的强度。
#: 每只异象 2 个技能（强烈异象槽位规则 2–3）。
CHAOS_SKILLS: tuple[tuple[str, str, int, int, int, int, int, int, int], ...] = (
    # 嗔影：远程直线 + 近身爆发
    ("wrath_ray", "嗔线", 1, 7, 2, 8, 13, 10, 0),
    ("wrath_burst", "嗔爆", 1, 9, 2, 4, 13, 11, 0),
    # 空心者：直线吸血 + 范围掏空
    ("hollow_drain", "掏空之吸", 1, 8, 2, 8, 13, 9, 0),
    ("hollow_gorge", "空腹洞开", 1, 10, 2, 8, 13, 8, 0),
    # 伪光者：失焦征兆 + 迟帧光场
    ("false_light_gaze", "伪光注视", 1, 8, 1, 8, 1, 0, 0),
    ("false_light_halo", "伪光轮", 1, 9, 1, 8, 9, 0, 4),
)

#: 每个技能 key 的 (形状, 创伤渠道, 演出预设, 恢复回合)。
#: 形状同时决定声径（EnemySkillMixin.SKILL_SOUND_RADIUS）。
CHAOS_SKILL_META: dict[str, tuple[str, str, str, int]] = {
    "wrath_ray": ("固定细线", "心智", "needle", 1),
    "wrath_burst": ("固定曼哈顿半径2", "清醒", "blast", 2),
    "hollow_drain": ("固定细线", "心智", "sound", 1),
    "hollow_gorge": ("固定曼哈顿半径2", "心智", "hex", 2),
    "false_light_gaze": ("固定单格", "无", "hex", 1),
    "false_light_halo": ("固定曼哈顿半径1", "无", "field", 2),
}

CHAOS_BINDINGS: dict[str, tuple[str, ...]] = {
    CHAOS_WRATH_ID: ("chaos.wrath_ray", "chaos.wrath_burst"),
    CHAOS_HOLLOW_ID: ("chaos.hollow_drain", "chaos.hollow_gorge"),
    CHAOS_FALSE_LIGHT_ID: ("chaos.false_light_gaze", "chaos.false_light_halo"),
}

#: 三元组 = 完整效果／合法施放条件／玩家反制（图鉴详情与观测共用）。
CHAOS_SKILL_TEXTS: dict[str, tuple[str, str, str]] = {
    "wrath_ray": (
        "沿视线拉出一条至多十三格的炽线，命中一次心智创伤；基础创伤 10，"
        "深层会顶到强烈异象的单次上限。",
        "目标在视线内，且两人之间有可以落线的直线。",
        "横移出线，或用墙体、实体遮挡。",
    ),
    "wrath_burst": (
        "以自身为中心炸开半径两格的嗔火（十三格），命中一次清醒创伤；"
        "基础创伤 11，命中后把你掀开一格。",
        "目标在视线内且距离不超过三格（火要够得着才起手）。",
        "拉开到三格以外；火起手后停两拍再靠近。",
    ),
    "hollow_drain": (
        "沿直线隔空吸气，命中一次心智创伤（基础 9），并把自己缺的完整度"
        "吸回两点。",
        "目标在视线内，且两人之间有可以落线的直线。",
        "横移出线；它吸空的那一下不会补满上限。",
    ),
    "hollow_gorge": (
        "在目标周围开一个半径两格的空洞（十三格），命中一次心智创伤"
        "（基础 8）并额外抹去两点想象力。",
        "目标在视线内。",
        "走出空洞范围；空洞只开两拍。",
    ),
    "false_light_gaze": (
        "把过亮的光转到目标身上：挂上「失焦」（视野 −1，两回合）并抹去"
        "三点想象力。",
        "目标在视线内。",
        "在它落光前离开原地；失焦最多把视野减到 3。",
    ),
    "false_light_halo": (
        "在最亮处铺下一圈半径两格的迟帧光场（五格）；踩进去的脚步会被"
        "光缠住（移动额外耗时 +0.2）。",
        "目标若在视线内；不在视线内时按最后目击位置落地。",
        "绕开光场，或等光自己灭掉（五回合）。",
    ),
}
