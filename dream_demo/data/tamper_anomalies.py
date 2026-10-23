"""篡改风险专属异象：漏字者与其专属技能「吞音」（规格 §7.3）。

只由篡改风险召唤，不进任何普通／强烈／位面／刷新投放池：定义里同时写
``pool=False`` 与 ``spawn_only='tamper'``，投放侧按后者显式排除。
"""

from __future__ import annotations

from typing import Any

#: 专属投放标记；所有池构建都要排除带这个标记的定义。
TAMPER_SPAWN_ONLY = "tamper"
OMISSION_ANOMALY_ID = "anomaly.tamper_omission"
OMISSION_SKILL_ID = "tamper.omission_voice"
#: 当前层同时最多存在几只由篡改召唤且存活的漏字者。
OMISSION_LAYER_LIMIT = 2
#: 出生点距离玩家（切比雪夫）范围。
OMISSION_SPAWN_DISTANCE = (3, 5)
#: 吞音：预警距离、想象创伤、冷却（世界回合）。
OMISSION_RANGE = 4
OMISSION_IMAGINATION_TRAUMA = 3
OMISSION_COOLDOWN = 6
OMISSION_INTEGRITY = 18
OMISSION_MELEE_MIND_TRAUMA = 2

TAMPER_ANOMALIES: dict[str, dict[str, Any]] = {
    OMISSION_ANOMALY_ID: {
        "name": "漏字者",
        "description": "一个人形站在句子的空缺里。它走近时，脚步声总少一拍。",
        "glyph": "缺",
        "anomaly_kind": "普通异象",
        "integrity": OMISSION_INTEGRITY,
        "move_time": 1.0,
        "attack_time": 1.0,
        "trauma_type": "心智创伤",
        "communicates": False,
        "drop_id": None,
        "dissolution_reward": 8,
        "vision": 8,
        "power": OMISSION_MELEE_MIND_TRAUMA,
        "layers": [1, 30],
        "pool": False,
        "spawn_only": TAMPER_SPAWN_ONLY,
        "color": "#9496b1",
        "skill": "吞音：它停住脚步，张开没有声音的口。你刚想起的词开始变淡。",
    },
}

#: (key, name, tier, cd, windup, reach, cells, power, duration)
#: power 记 0——吞音造成的是**想象创伤**，不是技能引擎的心智／清醒渠道，
#: 由 core/tamper_risks.py 的解析器按 OMISSION_IMAGINATION_TRAUMA 直接结算。
TAMPER_SKILLS: tuple[tuple[str, str, int, int, int, int, int, int, int], ...] = (
    ("omission_voice", "吞音", 0, OMISSION_COOLDOWN, 1, OMISSION_RANGE, 1, 0, 0),
)

TAMPER_BINDINGS: dict[str, tuple[str, ...]] = {
    OMISSION_ANOMALY_ID: (OMISSION_SKILL_ID,),
}

OMISSION_SKILL_TEXTS: dict[str, tuple[str, str, str]] = {
    "omission_voice": (
        "它停住脚步，张开没有声音的口。你刚想起的词开始变淡。",
        "目标在视线内且距离不超过 4 格；你又完成一次耗时行动后结算。",
        "拉开距离、走出视线，或让那句话先落地。",
    ),
}
