"""Authored casting motions. Workbook profiles remain the timing/budget authority."""
from dataclasses import dataclass
from .anomaly_skills import FX_PROFILES


@dataclass(frozen=True)
class CastVisual:
    profile: str
    motion: str
    theme: str = ''


PROFILE_MOTIONS = dict(needle='line', push='push', hex='bind', boon='gather',
                       sound='wave', terrain='terrain', fold='fold',
                       field='spread', fire='fire', blast='blast')

ABILITY_FX = {}
for profile, motion, ids in (
    ('fire', 'fire', 'spark kindle firewall'),
    ('blast', 'blast', 'detonate flame_nova'),
    ('field', 'frost', 'frost_touch ice_chain ice_bridge'),
    ('field', 'mist', 'smoke_veil moth_dust transpire'),
    ('sound', 'wave', 'echo_pulse slow_wave calm_incense listen_realm'),
    ('push', 'push', 'repulse purge_wind'),
    ('boon', 'gather', 'mirror_stance stasis resonance deep_breath'),
    ('boon', 'reveal', 'farsight wide_develop develop'),
    ('hex', 'bind', 'blur mute_protocol nightmare_fuel'),
    ('fold', 'fold', 'vanish flashback blink'),
    ('needle', 'electric', 'short_circuit rewire static_arc'),
    ('terrain', 'grow', 'sow_green'),
    ('terrain', 'terrain', 'wax_seal ink_doodle condense_dew draw_liquid dissolve_wall raise_terrain sink_terrain collapse conjure_wall rewrite_corner pixel_surge'),
    # §13 战斗构想：近战的接触、远程的真实射线、延迟弹与范围场各自有署名。
    ('needle', 'cut', 'combat.beat_cut combat.cross_step combat.arc_slash combat.paper_blades'),
    ('needle', 'line', 'combat.refracted_bolt combat.piercing_needle combat.shadow_pin'),
    ('push', 'pull', 'combat.tow_hook'),
    ('blast', 'blast', 'combat.delayed_shell combat.fault_ring'),
    ('needle', 'electric', 'combat.arc_orb'),
    ('field', 'mist', 'combat.backdraft_screen'),
):
    for key in ids.split():
        ABILITY_FX[key] = CastVisual(profile, motion)

ITEM_EFFECT_FX = {}
for key,profile,motion in (
    ('library.fold','fold','fold'),('library.bookmark','fold','fold'),
    ('library.inkline','needle','ink'),('library.erase','terrain','erase'),
    ('library.clamp','hex','bind'),('library.margin','boon','reveal')):
    ABILITY_FX[key]=CastVisual(profile,motion,'library')
for profile, motion, ids in (
    ('blast', 'blast', 'explosion'),
    ('fire', 'fire', 'fireburst tar_burst spark_rays ignite ignite_burst ignite_liquid fire_once realm_igniter'),
    ('needle', 'electric', 'shock projectile_charge'),
    ('field', 'mist', 'smoke_cloud blind'),
    ('sound', 'wave', 'sound_lure blast_lure slow_burst slow_ring remote_switch'),
    ('push', 'push', 'knockback'),
    ('terrain', 'terrain', 'slick liquid_step repair measure'),
    ('boon', 'reveal', 'develop_radius learn_ability mirror_insight'),
    ('boon', 'gather', 'restore_mind restore_lucidity restore_imagination restore_split warm_restore gamble overclock modem_buffer fullstop_reserve lucidity_regen free_step free_action skip_turn parry purge_void hospital_safe_sleep hospital_oxygen hospital_sensitive hospital_lymph_hit hospital_immune_once hospital_fluent hospital_gel_buffer hospital_pain_buffer hospital_saline hospital_wake hospital_fever hospital_wash_choice hospital_positive_choice'),
    ('field', 'scan', 'hospital_tool'),
):
    for key in ids.split():
        ITEM_EFFECT_FX[key] = CastVisual(profile, motion,
                                       'hospital' if key.startswith('hospital_') else '')


_SKILL_VARIANTS = {
    'split_echo': ('fold', 'summon'), 'core_summon': ('fold', 'summon'),
    'scribe_draft': ('blast', 'summon'), 'electric_stitch': ('field', 'electric'),
    'vine_grow': ('terrain', 'grow'), 'fog_veil': ('field', 'mist'),
    'hospital.syringe_dash': ('needle', 'push'),
    'hospital.forceps_pull': ('push', 'pull'),
    'hospital.blade_arc': ('needle', 'cut'),
    'hospital.scan_line': ('needle', 'scan'),
    'hospital.membrane_guard': ('boon', 'gather'),
    'hospital.drip': ('boon', 'drip'), 'hospital.listen': ('sound', 'wave'),
    'hospital.ring_wash': ('field', 'wash'),
    'hospital.core_infusion': ('field', 'drip'),
    'hospital.reopen': ('fold', 'summon'),
    'library.question': ('needle', 'page'), 'library.stroke': ('needle', 'line'),
    'library.index_line': ('needle', 'page'), 'library.last_page': ('needle', 'page'),
    'library.ink': ('field', 'ink'), 'library.delete': ('terrain', 'erase'),
    'library.omit': ('boon', 'erase'), 'library.return': ('fold', 'fold'),
    'library.foldstep': ('fold', 'fold'), 'library.bind': ('boon', 'page'),
    'library.revision': ('boon', 'page'), 'library.echo': ('fold', 'summon'),
    'library.blank': ('fold', 'summon'), 'library.threshold': ('terrain', 'page'),
    'library.lamp': ('boon', 'reveal'), 'abyss_pull': ('push', 'pull'),
    'core_chill': ('field', 'frost'),
}


def skill_visual(skill):
    profile, motion = _SKILL_VARIANTS.get(
        skill.skill_id, (skill.fx_profile, PROFILE_MOTIONS[skill.fx_profile]))
    theme = skill.skill_id.split('.')[0] if '.' in skill.skill_id else ''
    return CastVisual(profile, motion, theme)


def visual_duration(visual):
    preset = FX_PROFILES[visual.profile]
    return preset.entry_seconds + preset.cast_seconds + preset.tail_seconds


# 扩展包目录的构想：施法表现随目录行登记（effect.fx），与定义行同一批键。
from .expansion.growth_runtime import ability_fx_rows as _expansion_fx_rows  # noqa: E402

ABILITY_FX.update({key: CastVisual(**row)
                   for key, row in _expansion_fx_rows().items()})
