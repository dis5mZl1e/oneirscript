"""逻辑固体：触发源、接收器与陷阱场景定义（内容扩展包 v1）。

- 触发源：陷阱石台/机关石台（台子一族，取物/回应触发）、压力地板（踏上/离开）、
  感应符文墙（视野内出现失控意识）、定时摆轮（每 N 回合）。
- 接收器：机关门（开/关切换）、显影方尖（点亮显影）、囚笼栅栏（升降意识栅栏）、
  弹射座（推射）、灌注阀（释放材料）、共鸣报警器（全图召集）。
- 电线：Cell.wire 位掩码（N=1 E=2 S=4 W=8），可穿墙；信号沿位掩码 BFS，
  每格 −1 强度（上限 3），导电铜网墙 +4；每格只传播一次、接收器幂等。
"""

from __future__ import annotations

# 电线方向位（Cell.wire）
WIRE_N, WIRE_E, WIRE_S, WIRE_W = 1, 2, 4, 8
WIRE_ALL = WIRE_N | WIRE_E | WIRE_S | WIRE_W
WIRE_DIR = ((0, -1, WIRE_N, WIRE_S), (1, 0, WIRE_E, WIRE_W),
            (0, 1, WIRE_S, WIRE_N), (-1, 0, WIRE_W, WIRE_E))

SIGNAL_STRENGTH_CAP = 3      # 信号初始强度上限（防失控）
SIGNAL_MAX_STRENGTH = 8      # 经过放大器后的强度上限
AMPLIFIER_WALL = "导电铜网墙"

# 触发源/接收器墙种
TRAP_PLATFORM = "陷阱石台"
MECHANISM_PLATFORM = "机关石台"
RUNE_WALL = "感应符文墙"
PENDULUM = "定时摆轮"
LOGIC_DOOR = "机关门"
REVEAL_OBELISK = "显影方尖"
CAGE_FENCE = "囚笼栅栏"
LAUNCHER = "弹射座"
VALVE = "灌注阀"
ALARM = "共鸣报警器"
GATE_AND = "合辙枢"      # AND：本回合 ≥2 个不同来源 → 满强度转发
GATE_OR = "分流枢"       # OR：任意信号 → 满强度转发
JUNCTION = "接线枢"      # 直通：信号原样穿过（兼具去重）
GATE_KINDS = frozenset({GATE_AND, GATE_OR})
TRIGGER_KINDS = frozenset({TRAP_PLATFORM, MECHANISM_PLATFORM, RUNE_WALL, PENDULUM})
RECEIVER_KINDS = frozenset({LOGIC_DOOR, REVEAL_OBELISK, CAGE_FENCE, LAUNCHER, VALVE, ALARM})
LOGIC_KINDS = TRIGGER_KINDS | RECEIVER_KINDS | GATE_KINDS

# Circuit infrastructure belongs to explicitly scoped map templates, never to
# natural wall patches or loose solid features. Trap platforms remain eligible
# for their existing standalone, bounded trap placement.
TEMPLATE_ONLY_CIRCUIT_WALLS = (LOGIC_KINDS | {JUNCTION, AMPLIFIER_WALL}) - {TRAP_PLATFORM}

# 陷阱石台场景库：vault 在 logic.trap_pool 里点名，生成时按
# 「seed ^ 层 ^ 坐标」确定性随机取一种（读档不重摇、无需序列化）。
TRAP_SCENARIO_LIBRARY: dict[str, dict] = {
    # 召唤异象：固定模板点名；随机池留 None = 当前层区域加权抽。
    "summon_hounds": {"type": "summon", "pool": ("anomaly.page_hound",), "count": 2, "radius": 4},
    "summon_mixed": {"type": "summon", "pool": None, "count": 2, "radius": 4},
    "summon_swarm": {"type": "summon", "pool": None, "count": 3, "radius": 5},
    # 囚笼锁闭：以玩家为中心升起意识栅栏（10 回合消散 / 可徒手破坏——永远有出路）。
    "cage": {"type": "cage"},
    # 毒气灌注：石台相邻格灌入弥散印象。
    "gas_poison": {"type": "gas", "gas": "毒气", "amount": 30},
    "gas_hypno": {"type": "gas", "gas": "催眠雾", "amount": 24},
    "gas_static": {"type": "gas", "gas": "静电尘", "amount": 26},
    # 弹药伏击：向玩家方向射出一发（直线弹道，撞墙即止）。
    "arrow": {"type": "projectile", "damage": 3},
    "arrow_heavy": {"type": "projectile", "damage": 5},
    # 征兆诅咒：直接挂负面征兆。
    "curse_forget": {"type": "portent", "portent": "遗忘", "duration": 6},
    "curse_slow": {"type": "portent", "portent": "迟滞", "duration": 5},
    # 地形坍缩：石台周围的普通聚合物凝成坚实聚合物（堵退路）。
    "terrain_collapse": {"type": "terrain", "radius": 2, "chance": 0.5},
    # 虚惊一场：什么都不发生（Roguelike 必备的不确定性）。
    "dud": {"type": "dud"},
    # 虚惊假象：只播报一条误导消息。
    "false_alarm": {"type": "dud", "message": "石台深处传来咔哒一声——然后什么也没有发生。"},
}

# 机关石台的良性结果（开门/显影由信号驱动接收器，这里是平台自身的小奖励）。
MECHANISM_SCENARIOS: dict[str, dict] = {
    "reveal": {"type": "reveal", "radius": 3},
    "nothing": {"type": "dud", "message": "机关空转了一圈，台面亮了一下。"},
    "imagination": {"type": "imagination", "amount": 6},
}


def roll_trap_scenario_name(pool: tuple[str, ...] | list[str], seed: int, depth: int,
                            x: int, y: int) -> str:
    """确定性抽一种陷阱场景（返回名字）：盖章时定死并随层保存，读档不重摇。"""
    import random

    options = [name for name in pool if name in TRAP_SCENARIO_LIBRARY]
    if not options:
        options = ["dud"]
    rng = random.Random(seed * 7919 + depth * 104729 + x * 997 + y * 761)
    return rng.choice(options)


def roll_mechanism_scenario(seed: int, depth: int, x: int, y: int) -> dict:
    import random

    rng = random.Random(seed * 104729 + depth * 7919 + x * 761 + y * 997)
    return rng.choice(list(MECHANISM_SCENARIOS.values()))
