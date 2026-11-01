"""Presentation taxonomy by primary effect, independent of source and tier.

Categories describe mechanics; they never grant damage bonuses or resistances.
Every registered ability must have an explicit assignment (checked in tests).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AbilityCategory:
    name: str
    effect: str
    ink: str
    background: str


CATEGORIES = {
    'strike': AbilityCategory('直接打击', '以近战、弹体或范围冲击造成创伤；命中、穿透与敌我影响由具体构想决定。', '#f1a393', '#402724'),
    'control': AbilityCategory('行动控制', '改变异象的移动、感知或警戒，制造行动窗口；不保证阻止出手。', '#c2aff5', '#342943'),
    'space': AbilityCategory('空间位移', '改变自身位置或建立短途通路；落点、墙体与任务边界仍需合法。', '#91c9fa', '#23364a'),
    'perception': AbilityCategory('感知记录', '扩大感知或记录地形、声源与路径；只提供该构想授权的信息，不自动揭示未知对象。', '#9cddd7', '#203c3b'),
    'sound': AbilityCategory('声音干预', '制造、延迟或衰减真实声音，影响调查与追踪；传播仍受介质和环境约束。', '#e1b5dc', '#402b3b'),
    'light': AbilityCategory('光照干预', '改变光源、遮光与照明范围，影响双方视线；不直接阻挡气体或弹体。', '#f0d98e', '#40391f'),
    'material': AbilityCategory('材料转化', '生成、转移、相变或激发真实材料；存量、容量、反应与敌我风险按具体构想结算。', '#efbd8b', '#403121'),
    'terrain': AbilityCategory('地形塑造', '改变墙体、地面或地势，重塑通路与流向；保护设施和占用检查仍然有效。', '#b7d594', '#303c24'),
    'circuit': AbilityCategory('回路信号', '触发、连接或延迟真实端口信号；不绕过机关保护、次数与接收条件。', '#96b9f5', '#2c2e45'),
    'support': AbilityCategory('自身支援', '恢复资源、清除负面状态或强化防护与携带效果；代价、期限和适用目标各自独立。', '#a2dfb7', '#253b30'),
    'residue': AbilityCategory('构想维护', '撤销、暂停、移动或延长已有构想残留；不返还已消耗材料，也不无限刷新期限。', '#c8bec0', '#383035'),
}

GROUPS = {
    'strike': 'repulse combat.beat_cut combat.arc_slash combat.refracted_bolt combat.piercing_needle combat.delayed_shell combat.fault_ring combat.paper_blades',
    'control': 'frost_touch slow_wave blur ice_chain moth_dust library.inkline library.clamp combat.shadow_pin combat.tow_hook',
    'space': 'flashback blink library.fold library.bookmark combat.cross_step expansion.realm.a06',
    'perception': 'farsight wide_develop develop listen_realm library.margin expansion.light.a02 expansion.projectile.a04',
    'sound': 'echo_pulse mute_protocol expansion.sound.a01 expansion.sound.a02 expansion.sound.a03 expansion.sound.a04 expansion.sound.a05 expansion.sound.a06 expansion.projectile.a05',
    'light': 'expansion.light.a01 expansion.light.a03 expansion.light.a04 expansion.light.a05 expansion.light.a06',
    'material': 'spark smoke_veil detonate firewall flame_nova kindle condense_dew draw_liquid ice_bridge transpire static_arc purge_wind combat.arc_orb combat.backdraft_screen expansion.terrain.a02 expansion.terrain.a03 expansion.terrain.a05 expansion.terrain.a06 expansion.circuit.a02 expansion.circuit.a04 expansion.circuit.a06',
    'terrain': 'library.erase sow_green wax_seal dissolve_wall raise_terrain sink_terrain collapse conjure_wall rewrite_corner ink_doodle pixel_surge expansion.terrain.a01 expansion.terrain.a04',
    'circuit': 'short_circuit rewire expansion.circuit.a01 expansion.circuit.a03 expansion.circuit.a05',
    'support': 'mirror_stance stasis vanish resonance nightmare_fuel deep_breath calm_incense expansion.projectile.a01 expansion.projectile.a02 expansion.projectile.a03 expansion.projectile.a06 expansion.realm.a03',
    'residue': 'expansion.realm.a01 expansion.realm.a02 expansion.realm.a04 expansion.realm.a05',
}

ABILITY_CATEGORIES = {ability: category for category, abilities in GROUPS.items()
                      for ability in abilities.split()}


def ability_category(ability_id: str) -> AbilityCategory:
    return CATEGORIES[ABILITY_CATEGORIES[ability_id]]
