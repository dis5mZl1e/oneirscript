"""Equipment readings shared by the inspector and compiled Chinese prose.

Slots describe the old loadout, not necessarily the physical kind of an item.
Function words select readings through compiled relations; no random synonyms.
"""
from ..data.items import ITEM_DEFINITIONS


KIND_OVERRIDES = {
    **dict.fromkeys(("insulated_gloves", "sketch_gloves", "ignite_gloves",
                    "warm_gloves", "dreamweaver_gloves", "singed_gloves",
                    "throwing_gloves", "hospital.sterile_glove"), "clothing"),
    **dict.fromkeys(("single_earphone", "faded_id_card", "hospital.lymph_filter",
                    "hospital.glass_rib", "hospital.pulse_tag",
                    "hospital.lumen_mask", "library.bookmark", "library.card"), "accessory"),
    'focus_ring': 'accessory',
    **dict.fromkeys(("high_pressure_pump", "air_concentrator", "unfinished_editor"), "tool"),
    "hospital.suture_shears": "weapon",
    "hospital.hollow_lancet": "weapon",
}
KIND_LABELS = {"weapon": "武器", "clothing": "衣物", "accessory": "饰品",
               "tool": "工具", "memory": "记忆"}
DEFAULT_WORDS = {"weapon": "手握", "clothing": "穿着", "accessory": "戴上",
                 "tool": "使用", "memory": "回想"}
CONTINUOUS_WORDS = {**DEFAULT_WORDS, "accessory": "佩戴着"}
HAND_WEAR = frozenset(("insulated_gloves", "sketch_gloves", "ignite_gloves",
                      "warm_gloves", "dreamweaver_gloves", "singed_gloves",
                      "throwing_gloves", "hospital.sterile_glove"))

# 「的」字句属性词的名词化读法（方案 §5：不写「提供……属性」）。
_PROPERTY_NOUNS = {
    "锋利": "锋利的刀锋", "轻快": "轻快的节拍", "穿透": "更深的穿透",
    "余温": "不散的余温", "喷射强化": "更足的喷雾", "追迹": "追迹的目光",
    "爆裂": "更宽的爆裂", "导电": "导电的水路",
}

_MANNER_READINGS = {
    'swift_strike': '轻快地出手',
    'pierce_up': '让本次弹体穿得更深',
    'spray_boost': '让本次喷射带出更多材料',
    'attach_hunt': '追着附着的气味出手',
    'fire_affinity': '让本次命中带出余温',
    'blast_radius': '让本次命中带出余爆',
    'repair_up': '把本次修缮补得更实',
    'throw_master': '借甩手的力道出招',
    'wet_conduct': '在本次命中或喷射落点借液体导电',
}

# 持续行为（contract）按效果 id 落到具体意象；机制不明的效果回退通用句。
_CONTRACT_ENDINGS = {
    "liquid_ward": "涉水时侵扰减轻",
    "swift_strike": "出手更轻快",
    "mind_armor": "心智的伤口浅一些",
    "lucidity_armor": "清醒的伤口浅一些",
    "dual_armor": "心智与清醒的伤口都浅一些",
    "mind_guard": "它替你留意着心智",
    "fire_ward": "火燎上来时轻一些",
    "wire_safe": "静电不再跳到你身上",
    "quiet_steps": "脚步声轻了",
    "noise_cut": "太吵的地方它替你挡一半",
    "slow_aura": "靠近它的东西慢半拍",
    "lamp": "照亮更远处",
    "wall_sense": "隔着墙也听得出虚实",
    "repair_up": "修补得更彻底",
    "vision_up": "看得更远",
    "shock_aura": "靠近你的静电会跳",
    "blast_radius": "爆裂波及更宽",
    "fire_affinity": "点火时火势更旺",
    "pierce_up": "针脚扎得更深",
    "swift_pickup": "捡拾更快",
    "spray_boost": "喷得更足",
    "attach_hunt": "沾过气味的逃不远",
    "wet_conduct": "湿处也照常导电",
    "coin_bonus": "散场时的收获多一分",
    "hospital_suture_coil": "下一次创伤轻一点",
    "hospital_lymph_filter": "身上的附着它一直滤着",
    "hospital_cerebral_ampoule": "构想展开后，想象力回得快",
    "hospital_sterile_glove": "挨了打，它帮你洗短征兆",
    "hospital_glass_rib": "有光时它替你挡一下",
    "hospital_pulse_tag": "挨打时它响一声",
    "hospital_marrow_spoon": "吃下的东西它补一点",
    "hospital_lumen_mask": "有光时它照出伪装",
    "blast_padding": "爆炸撞上来时，清醒的伤口浅一些",
    "library_bookmark": "跨过门后，下一次出手多一分力",
    "library_index": "再次命中认得的异象时，记起它的完整度",
    "library_fold": "迈出一步，就标出相邻能走的连接",
    "library_paperweight": "独处时，自然恢复多回来一点",
    "library_lens": "命中后，照出目标周围一格的动静",
    "library_quill": "替你拒绝一次弱控制",
    "library_card": "触到与上次不同的状态时，视野暂时开阔一格",
    "library_testimony": "命中后，指出一个相邻空位",
    "measure": "悬停时能读出到目标的最短步数",
    "hang": "把一件易逝物挂上梦的墙，替你承受一次打击",
    "refract_mark": "跳弹命中后留下折射印记，换个方向命中便能伤得更深",
    "ash_retreat": "每层首次亲手点火后，下一步可以免费走，近处追兵暂时跟丢",
    "echo_control": "一次声响引来目标后，下次声波会让声源附近的意识震停一拍",
    "blank_pass": "每层一次，想象力耗尽后可以免去一次构想的想象力消耗",
    "blank_edge": "想象力低落时，回流会多回来一点",
    "throw_master": "投得更远，落点的冲击也更重",
}


def contract_ending(effect: str, opcode: str = "", *, power: int = 0, secondary: int = 0) -> str:
    from ..i18n import tr

    if effect == 'blank_edge' and power > 0:
        return tr('想象力不超过 {threshold} 时，每回合多回流 {power} 点想象力',
                  threshold=secondary, power=power)
    if effect in _CONTRACT_ENDINGS:
        return tr(_CONTRACT_ENDINGS[effect])
    if opcode == "cover":
        return tr("护持一直都在")
    return tr("那份效果一直都在")


def continuous_word(definition_id: str) -> str:
    return "戴着" if definition_id in HAND_WEAR else CONTINUOUS_WORDS[equipment_kind(definition_id)]


def equipment_kind(definition_id: str) -> str:
    definition = ITEM_DEFINITIONS.get(definition_id, {})
    explicit = definition.get("grammar_kind") or KIND_OVERRIDES.get(definition_id)
    if explicit in KIND_LABELS:
        return explicit
    slot = definition.get("slot", "")
    if slot == "记忆槽":
        return "memory"
    if slot == "自我表层":
        return "clothing"
    if slot.startswith("依附物"):
        return "accessory"
    if slot == "手中意象" or definition.get("melee") or definition.get("fire"):
        return "weapon"
    return "tool"


def action_form(definition_id: str, *, switched: bool = False) -> tuple[str, str]:
    kind = equipment_kind(definition_id)
    if switched:
        return {"weapon": ("以", ""), "clothing": ("借助", "的效果"),
                "accessory": ("借助", "的力量"), "tool": ("用", ""),
                "memory": ("借助", "的记忆")}[kind]
    word = "戴上" if definition_id in HAND_WEAR else DEFAULT_WORDS[kind]
    return word, "，" if kind in ("weapon", "clothing", "accessory", "memory") else ""


def role_text(definition_id: str, response) -> str:
    """Explain the selected reading, including its actual effect or action."""
    kind = equipment_kind(definition_id)
    definition = ITEM_DEFINITIONS.get(definition_id, {})
    name = definition.get("name", definition_id)
    meaning = response.meaning
    mode = response.reading
    if (definition.get("expansion_catalog_id")
            and response.role in ("modifier", "verb", "complement")):
        return meaning
    if response.role == "excluded":
        return meaning
    if mode == "attribution" and response.role == "modifier":
        noun = _PROPERTY_NOUNS.get(meaning, f"{meaning}的来源")
        if response.payload_type == 'cut' and definition_id in HAND_WEAR:
            return '掌心的劲道'
        if kind == 'weapon':
            return noun
        prefix = ('掌心' if definition_id in HAND_WEAR else
                  {'clothing': '衣料', 'accessory': '饰品', 'tool': '工具', 'memory': '记忆'}[kind])
        return f'{prefix}里{noun}'
    if mode == "manner" and response.role == "modifier":
        if response.payload_type == 'cut':
            return '借锋利的刀锋出手'
        return _MANNER_READINGS.get(response.effect, f"借{meaning}出手")
    if mode == "disposal" and response.role in ("object", "payload"):
        return f"递给后一步行动的{meaning}"
    if mode == "origin" and response.role == "object":
        return f"从{name}中取用材料"
    if mode == "passive":
        return f"受到对应创伤后{meaning}" if response.role == "verb" else f"响应{meaning}类创伤"
    if response.role == "verb":
        lead = continuous_word(definition_id) if response.kind == "contract" else action_form(
            definition_id, switched=mode != "default")[0]
        if response.kind == "contract":
            meaning = contract_ending(response.effect, opcode=response.opcode,
                                      power=response.power, secondary=response.secondary)
        return f"{lead}{name}，{meaning}"
    if response.role == "source":
        # 2026-10-14 载体真实化：检视里报出载体携带的载荷族，让不同件的
        # 载体词义读得出差异（旧版只有名字）。载荷未映射（reward/hunt 等）
        # 时维持原文案。
        from .roles import PAYLOAD_LABELS
        payload = PAYLOAD_LABELS.get(response.payload_type, "")
        if payload:
            return f"{continuous_word(definition_id)}{name}，带着{payload}"
        return f"{continuous_word(definition_id)}{name}"
    if response.role == "modifier":
        if definition_id in HAND_WEAR:
            return '借助掌心的劲道' if response.payload_type == 'cut' else f'借助掌心的{meaning}'
        return {"weapon": f"借助刀锋的{meaning}", "clothing": f"借助衣物的{meaning}",
                "accessory": f"借助饰品赋予的{meaning}", "tool": f"借助工具的{meaning}",
                "memory": f"借助记忆中的{meaning}"}[kind]
    if response.role == "complement":
        # 补语检视报实际效果（与「随句补足」details 同源）；没有专属落句的
        # 效果退回载荷名词。
        ending = contract_ending(response.effect, power=response.power,
                                 secondary=response.secondary)
        if ending != "那份效果一直都在":
            return f"{KIND_LABELS[kind]}附带：{ending}"
        return f"{KIND_LABELS[kind]}附带的{meaning}"
    if response.role == "object" and not response.payload_type.startswith("container_"):
        if definition_id in HAND_WEAR:
            return f'掌心的{meaning}'
        return {"weapon": meaning, "clothing": f"衣料里的{meaning}",
                "accessory": f"饰品上的{meaning}", "tool": f"工具里的{meaning}",
                "memory": f"记忆里的{meaning}"}[kind]
    return meaning
