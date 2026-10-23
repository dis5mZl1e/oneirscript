"""Presentation-only item identities. Authored definition icons always win.

Families describe an object's silhouette, never its rarity. Abstract memories
instead describe their actual endurance, attribute, or recovery effect.
"""

# Source characters are single OFL Noto outlines, imported only under PUA keys.
# Stable explicit offsets are permanent; append new entries, never reorder slots.
ITEM_FAMILIES = {
    'blade': (0xE240, '🔪', '† ', '刃具'),
    'glove': (0xE241, '🧤', '⊓ ', '手套'),
    'candle': (0xE242, '🕯', '♨ ', '烛火'),
    'ring': (0xE243, '💍', '○ ', '戒环'),
    'lens': (0xE244, '🔍', '⌕ ', '透镜'),
    'flute': (0xE245, '🎵', '♪ ', '吹奏与声响器具家族'),
    'pen': (0xE246, '🖊', '✎ ', '书写工具'),
    'coat': (0xE247, '🧥', '♖ ', '外衣与披覆家族'),
    'compass': (0xE248, '🧭', '⊕ ', '测向'),
    'clover': (0xE249, '🍀', '♧ ', '四叶草'),
    'tool': (0xE24A, '🔧', '⚒ ', '工具家族'),
    'medical': (0xE24B, '🩺', '+ ', '诊疗器具家族'),
    'speaker': (0xE24C, '📢', '≋ ', '发声器'),
    'projector': (0xE24D, '📽', '▷ ', '投影与影像家族'),
    'headphone': (0xE24E, '🎧', '∩ ', '耳机与线圈家族'),
    'ticket': (0xE24F, '🎫', '▱ ', '票证'),
    'hook': (0xE250, '🪝', '⌝ ', '钩具'),
    'watch': (0xE251, '⌚', '◷ ', '钟表'),
    'hourglass': (0xE252, '⌛', '⧖ ', '沙漏'),
    'pump': (0xE253, '🚿', '↥ ', '泵送与喷洒家族'),
    'wind': (0xE254, '🌬', '≋ ', '送风器具家族'),
    'launcher': (0xE255, '🏹', '➶ ', '发射器家族；不暗示现实枪械'),
    'coin': (0xE256, '🪙', '⊙ ', '硬币'),
    'battery': (0xE257, '🔋', '▣ ', '电池'),
    'seal': (0xE258, '🔖', '◈ ', '印记与封签家族'),
    'tooth': (0xE259, '🦷', '∨ ', '牙齿'),
    'gem': (0xE25A, '💎', '◇ ', '晶体与棱镜家族'),
    'clip': (0xE25B, '📎', '⌇ ', '夹件'),
    'page': (0xE25C, '📄', '▤ ', '纸页'),
    'card': (0xE25D, '🪪', '▯ ', '身份卡'),
    'message': (0xE25E, '💬', '… ', '消息'),
    'cup': (0xE25F, '🏆', '∪ ', '杯器'),
    'blast': (0xE260, '💣', '※ ', '爆破消耗家族'),
    'match': (0xE261, '🔥', '♨ ', '点火消耗家族'),
    'bolt': (0xE262, '⚡', 'ϟ ', '电弧与能量弹家族'),
    'glass': (0xE263, '🔹', '◇ ', '碎片家族；不暗示完整器物'),
    'keycap': (0xE264, '⌨', '▣ ', '键盘零件'),
    'step': (0xE265, '👣', '∴ ', '步行动作消耗家族'),
    'bottle': (0xE266, '🧴', '♙ ', '瓶装消耗家族'),
    'cartridge': (0xE267, '📦', '▣ ', '弹药盒家族'),
    'smoke': (0xE268, '☁', '≋ ', '烟雾消耗家族'),
    'thread': (0xE269, '🧵', '⌁ ', '线与缝合家族'),
    'phone': (0xE26A, '☎', '⌕ ', '电话声消耗家族'),
    'drink': (0xE26B, '☕', '∪ ', '饮品家族'),
    'pill': (0xE26C, '💊', '+ ', '片剂糖锭家族'),
    'powder': (0xE26D, '🧂', '∴ ', '粉末消耗家族'),
    'key': (0xE26E, '🔑', '⚿ ', '钥匙'),
    'bulb': (0xE26F, '💡', '☼ ', '光源家族'),
    'soap': (0xE270, '🧼', '▱ ', '皂片'),
    'spring': (0xE271, '🌀', '⌁ ', '弹簧与盘绕家族'),
    'lantern': (0xE272, '🏮', '☼ ', '灯笼'),
    'bell': (0xE273, '🔔', '♧ ', '铃铛'),
    'ruler': (0xE274, '📏', '╱ ', '测量尺'),
    'storage': (0xE275, '💾', '▣ ', '数据储存家族'),
    'shears': (0xE276, '✂', '⋈ ', '剪具'),
    'spoon': (0xE277, '🥄', '⌕ ', '勺具'),
    'mask': (0xE278, '😷', '⊟ ', '面罩家族'),
    'memory.endurance': (0xE279, '🛡', '⌑ ', '记忆：耐受与环境适应'),
    'memory.attribute': (0xE27A, '📈', '↗ ', '记忆：属性与上限'),
    'memory.recovery': (0xE27B, '🌱', '♧ ', '记忆：恢复'),
    'crayon': (0xE27C, '🖍', '✎ ', '蜡笔'),
    'hinge': (0xE27D, '🚪', '╫ ', '门构件家族'),
    'pendulum': (0xE27E, '🕰', '◷ ', '摆钟构件家族'),
    'robe': (0xE27F, '👘', '♖ ', '长袍'),
    'boot': (0xE280, '🥾', '⌊ ', '靴'),
    'bone': (0xE281, '🦴', '⌁ ', '骨形器具'),
    'syringe': (0xE282, '💉', '╱ ', '针具'),
    'filter': (0xE283, '🕸', '⊞ ', '过滤与网膜家族'),
}

_GROUPS = {
    'blade': 'paper_handle_letterknife carbon_copy_knife rusty_boxcutter multitool_knife',
    'glove': 'broken_tooth_thimble insulated_gloves sketch_gloves ignite_gloves warm_gloves dreamweaver_gloves singed_gloves throwing_gloves hospital.sterile_glove',
    'crayon': 'ember_crayon', 'hinge': 'door_hinge',
    'ring': 'echo_ring blast_ring swift_thought_ring focus_ring',
    'candle': 'corridor_candle molten_candle lighthouse_ember',
    'launcher': 'binder_clip_launcher echo_emitter nail_gun dart_gun sling',
    'pen': 'voice_recorder_pen null_pen pen_sharp',
    'lens': 'focusing_lens lighthouse_lens', 'flute': 'dream_tapir_flute sonic_whistle whistle split_tuning_fork',
    'pendulum': 'pendulum_blade metronome_pendant',
    'coat': 'frayed_sleeve waxed_raincoat lead_lined_apron static_poncho patched_pajamas leather_apron lightless_cloak unfinished_editor',
    'compass': 'surveyor_compass', 'clover': 'lucky_clover',
    'medical': 'stethoscope hospital.diagnostic_slide',
    'projector': 'line_projector double_frame',
    'headphone': 'headphone_coil single_earphone salt_soaked_coil',
    'ticket': 'quiet_ticket', 'hook': 'bent_hook',
    'watch': 'broken_watch arsonist_watch clockwork_half',
    'seal': 'gravestone_wristband wax_seal rift_wax_seal hospital.pulse_tag wax_emergency_seal',
    'hourglass': 'hourglass_pendant', 'pump': 'high_pressure_pump water_gun portable_siphon',
    'wind': 'air_concentrator hair_dryer', 'robe': 'phoenix_robe',
    'clip': 'heavy_stapler paper_clip', 'shears': 'rift_shears hospital.suture_shears',
    'coin': 'lucky_coin fate_coin', 'battery': 'night_battery battery_back',
    'tool': 'screwdriver deep_thought_chisel model_screw stair_bolt',
    'tooth': 'first_cry_fang', 'gem': 'void_pendant prism_pendant crystal_charm',
    'boot': 'ember_boots', 'thread': 'hunting_lanyard loose_thread hospital.suture_coil breach_spool',
    'page': 'blank_half_page blank_cheque_book impact_fold folded_projectile wet_fold guestbook_page',
    'card': 'faded_id_card', 'cup': 'broadband_grail',
    'match': 'blue_match sparkler_bundle flare_bolt lighter_match magnesium_match thermal_residue bottled_sunrise',
    'glass': 'clear_glass mirror_shard glass_shard pixel_scrap', 'keycap': 'old_keycap',
    'step': 'hollow_step folded_escape_route', 'bottle': 'molotov morning_dew mint_dew winter_sample hospital.cerebral_drops hospital.sealed_ampoule hospital.clean_air_bottle hospital.cerebral_ampoule',
    'blast': 'detonator_capsule micro_detonator tar_bomb',
    'cartridge': 'charge_clip jumbo_charge_clip', 'bolt': 'arc_bolt storm_accumulator',
    'speaker': 'buzz_lure quiet_boundary', 'smoke': 'double_smoke smoke_canister',
    'phone': 'dial_tone modem_56k',
    'drink': 'screensaver_soda warm_coffee cold_tea espresso_shot warm_water strong_mint_tea inspiration_coffee dream_electrolytes deep_thought_tea waking_reserve hospital.gentle_sleep',
    'pill': 'unlabeled_sedative expired_pill mint_lozenge wormwood_pastille espresso_tablet sleeping_lozenge hospital.oxygen_sugar hospital.dream_sensitive hospital.lymph_capsule hospital.immunoglobulin hospital.memory_fizz hospital.sterile_chew hospital.slow_gel hospital.pain_sugar hospital.saline hospital.marrow_sugar hospital.oral_morning hospital.porcelain_vitamin hospital.morning_lozenge',
    'powder': 'sage_powder void_coagulant hospital.fever_snow',
    'key': 'door_key', 'bulb': 'flash_bulb signal_flare night_shift_beacon', 'soap': 'soap_film',
    'spring': 'coiled_spring', 'lantern': 'night_lantern', 'bell': 'dream_bell',
    'ruler': 'tape_measure', 'storage': 'usb_drive',
    'bone': 'hospital.glass_rib', 'syringe': 'hospital.hollow_lancet',
    'filter': 'hospital.lymph_filter hospital.filter_sac',
    'spoon': 'hospital.marrow_spoon', 'mask': 'hospital.lumen_mask',
    # A punctuation mark has no honest physical silhouette: semantic action family.
    'message': 'unread_99 unfinished_fullstop',
}
ITEM_ICON_KEYS = {item: 'item.' + family for family, items in _GROUPS.items() for item in items.split()}

# Kept independent from the aggregated item table, avoiding a content import cycle.
from .items.memories import ITEMS as _MEMORIES
from .memory import MEMORY_FRAGMENT_EFFECTS as _EFFECTS
for _item, _definition in _MEMORIES.items():
    _kind = _EFFECTS.get(_definition.get('memory_effect'), {}).get('kind', '')
    _family = 'attribute' if _kind == 'stat' else 'recovery' if _kind in ('regen', 'recovery', 'restore') else 'endurance'
    ITEM_ICON_KEYS[_item] = 'item.memory.' + _family


def item_icon(definition_id, definition):
    """Literal authored glyphs retain their original font fallback path."""
    return str(definition.get('icon') or ITEM_ICON_KEYS.get(definition_id, ''))
