"""附录 B 与后续内容：全部现有非记忆槽装备的固定形状。

只登记 `shape_id`；面积由形状计算，不另写一份容易不一致的数据。
同定义物品的形状固定，不随稀有度、掉落种子或语言改变。

与附录 B 的两处偏离（§9.3 明确授权：装箱放不下时优先调整形状方案，
不得静默卸下装备、挤满行囊或扩大盘面）。两处都**只换同面积模板**，
表示成本不变，因此不影响平衡：

- `pendulum_blade` T8 → R8：T8 外接框 5×4 是附录允许的最大值，钟摆刃
  与凤凰袍（R12）同穿时，剩余空间最多只容一个 3×3 空洞，两件空心环
  （O8）就再也塞不进去。R8 是 4×2 实心条，同样 8 格。
- `rift_shears` U7 → P7：裂隙剪是旧五栏里唯一还会把「手中＋自我表层＋
  两件依附物＋惯用物」推到 42 格的 3×3 件；换成同面积的 P7（3×3 但
  实体集中在上两行）后即可与两件 O8 共存。

判定依据：scripts/probe_equipment_board_packing.py 穷举每个槽位的全部
形状等价类（依附物取二次组合，允许同定义两件），用精确回溯装箱，
不设尝试上限——改动前后分别为 10 个失败组合与 0 个。
"""

from __future__ import annotations

EQUIPMENT_SHAPES: dict[str, str] = {
    "paper_handle_letterknife": "I4",
    "frayed_sleeve": "L4",
    "broken_tooth_thimble": "I2",
    "ember_crayon": "I5",
    "carbon_copy_knife": "I5",
    "door_hinge": "X5",
    "echo_ring": "O8",
    "rusty_boxcutter": "I3",
    "binder_clip_launcher": "L4",
    "voice_recorder_pen": "I4",
    "focusing_lens": "P7",
    "dream_tapir_flute": "U5",
    "pendulum_blade": "R8",
    "null_pen": "I4",
    "waxed_raincoat": "U9",
    "lead_lined_apron": "R9",
    "static_poncho": "H8",
    "metronome_pendant": "P5",
    "surveyor_compass": "D4",
    "lucky_clover": "X5",
    "insulated_gloves": "U5",
    "multitool_knife": "L5",
    "stethoscope": "V7",
    "echo_emitter": "R6",
    "line_projector": "S6",
    "headphone_coil": "O8",
    "unfinished_editor": "S6",
    "quiet_ticket": "I3",
    "bent_hook": "L4",
    "single_earphone": "T4",
    "broken_watch": "P5",
    "lighthouse_lens": "P7",
    "sketch_gloves": "U5",
    "gravestone_wristband": "D4",
    "hourglass_pendant": "S4",
    "high_pressure_pump": "T6",
    "air_concentrator": "L5",
    "water_gun": "L5",
    "hair_dryer": "T6",
    "nail_gun": "R8",
    "sonic_whistle": "I3",
    "dart_gun": "L4",
    "ignite_gloves": "U5",
    "phoenix_robe": "R12",
    "blast_ring": "O8",
    "arsonist_watch": "P5",
    "pen_sharp": "I4",
    "heavy_stapler": "R6",
    "rift_shears": "P7",
    "patched_pajamas": "H8",
    "leather_apron": "U7",
    "lucky_coin": "D4",
    "night_battery": "R6",
    "warm_gloves": "U5",
    "screwdriver": "I4",
    "wax_seal": "P5",
    "first_cry_fang": "L6",
    "lightless_cloak": "P10",
    "void_pendant": "P7",
    "fate_coin": "R6",
    "deep_thought_chisel": "V7",
    "rift_wax_seal": "P7",
    "dreamweaver_gloves": "U7",
    "swift_thought_ring": "O8",
    "prism_pendant": "X5",
    "salt_soaked_coil": "O8",
    "ember_boots": "S6",
    "hunting_lanyard": "L5",
    "split_tuning_fork": "T4",
    "blank_half_page": "S4",
    "blank_cheque_book": "R6",
    "faded_id_card": "D4",
    "paper_clip": "U5",
    "singed_gloves": "U5",
    "model_screw": "I3",
    "stair_bolt": "L4",
    "tape_measure": "D4",
    # 2026-10-09 由惯用物一次性工具迁来的常驻被动件（见 data/items/equipment.py）。
    "sling": "S4",
    "throwing_gloves": "U5",
    "focus_ring": "U5",
    # 千禧园新增装备原来使用 D4 兼容形状；显式登记，不改变面积或轮廓。
    "unread_99": "D4",
    "crystal_charm": "D4",
    "broadband_grail": "D4",
    # Explicit material-source nouns reuse their existing compatibility volume.
    "glass_bottle": "D4",
    "ideal_tube": "D4",
    "balloon": "D4",
    "ideal_vessel": "D4",
}

# 缺失的新形状标识应使用显式兼容形状并提示（§9.3）。
COMPAT_SHAPE = "D4"


def shape_for(definition_id: str) -> str:
    """装备定义 → 形状 id。未登记时返回兼容形状，由调用方给出提示。"""
    return EQUIPMENT_SHAPES.get(definition_id, COMPAT_SHAPE)


def is_registered(definition_id: str) -> bool:
    return definition_id in EQUIPMENT_SHAPES


def is_material_source(definition_id: str) -> bool:
    from ..data.items import ITEM_DEFINITIONS
    return ITEM_DEFINITIONS.get(definition_id, {}).get('container', {}).get('medium') in ('liquid', 'gas')

EQUIPMENT_SHAPES.update({'hospital.suture_shears': 'L3', 'hospital.hollow_lancet': 'I2', 'hospital.suture_coil': 'U5', 'hospital.lymph_filter': 'D4', 'hospital.cerebral_ampoule': 'V3', 'hospital.sterile_glove': 'T4', 'hospital.glass_rib': 'S4', 'hospital.pulse_tag': 'I2', 'hospital.marrow_spoon': 'L3', 'hospital.lumen_mask': 'P5'})

EQUIPMENT_SHAPES.update({'library.bookmark': 'V3', 'library.index': 'D4', 'library.fold': 'L3', 'library.paperweight': 'S4', 'library.lens': 'D4', 'library.quill': 'I3', 'library.card': 'I2', 'library.testimony': 'T4'})

# Expansion equipment shapes are fixed in the canonical item catalog. Keeping
# this adapter at import time preserves the board's existing lookup API.
from ..data.expansion.catalog import ENTRIES as _EXPANSION_ENTRIES
EQUIPMENT_SHAPES.update({
    entry['id']: entry['board_shape'] for entry in _EXPANSION_ENTRIES
    if entry['category'] == 'equipment' and entry.get('board_shape')
})
