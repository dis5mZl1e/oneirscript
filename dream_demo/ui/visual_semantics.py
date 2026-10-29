"""Shared semantic colors and compact hit typography for character effects."""
from __future__ import annotations

import re
from functools import lru_cache


# bright, mid, deep. Colors are semantic, so the same effect stays recognizable
# across recipes, cast profiles, and damage numbers.
PALETTES = {
    "fire": ("#ff5d4f", "#f18442", "#96223a"),
    "electric": ("#76c7ff", "#4382ed", "#27449e"),
    "frost": ("#d8f2ff", "#91d8fb", "#63a8d5"),
    "water": ("#b5e7ff", "#65acd8", "#315c83"),
    "blast": ("#ff3b38", "#e22243", "#75172c"),
    "poison": ("#72b85f", "#286b3c", "#164a31"),
    "plant": ("#b4dc70", "#63ad4c", "#2e6e43"),
    "bullet": ("#ffe17a", "#f4b62d", "#a86e19"),
    "magic": ("#dcadff", "#a873eb", "#643799"),
    "light": ("#fffef2", "#e6f2ff", "#bbcbe0"),
    "sound": ("#7196cc", "#34588f", "#142b55"),
    "orange": ("#ffc078", "#e8873e", "#8e4f29"),
    "pink": ("#ffc0dc", "#df79b4", "#773d70"),
    "black": ("#9298a4", "#4f5664", "#202633"),
    "brown": ("#c99b6b", "#8a6041", "#493326"),
    "gray": ("#d4d8df", "#8e98a8", "#505967"),
    "gold": ("#ffe18a", "#c99837", "#70501c"),
    "magenta": ("#ff9be8", "#d247bd", "#711d78"),
    "hostile": ("#ff796d", "#d64b48", "#782e3a"),
}

_TOKENS = {
    "blast": ("explosion", "blast", "bomb", "爆炸", "爆破", "爆裂"),
    "poison": ("poison", "toxic", "venom", "中毒", "毒", "腐蚀气"),
    "electric": ("electric", "lightning", "static", "电", "雷", "静电"),
    "frost": ("frost", "ice", "slow", "freeze", "寒", "冰", "减速", "迟缓"),
    "fire": ("fire", "flame", "ignite", "burn", "火焰", "燃烧", "纵火"),
    "water": ("water", "liquid", "waterline", "水", "液体"),
    "plant": ("plant", "growth", "grow", "leaf", "forest", "植物", "生长", "枝叶"),
    "bullet": ("bullet", "projectile", "ranged", "shot", "子弹", "弹道", "远程"),
    "magic": ("magic", "arcane", "mystic", "fold", "summon", "hex", "法术", "魔法", "召唤", "紫"),
    "light": ("light", "holy", "healing", "heal", "光", "治疗", "圣"),
    "sound": ("sound", "sonic", "wave", "声波", "声音", "回声", "ink", "墨"),
    "pink": ("pink", "rose", "粉", "蔷薇"),
    "magenta": ("magenta", "紫红", "品红"),
    "black": ("black", "shadow", "dark", "void", "黑", "暗影", "虚空", "擦除", "erase"),
    "brown": ("brown", "earth", "stone", "soil", "土", "石", "岩"),
    "gray": ("gray", "grey", "metal", "steel", "integrity", "灰", "铁", "钢", "完整度"),
    "gold": ("gold", "beacon", "treasure", "金", "金属", "祝福"),
    "orange": ("orange", "amber", "push", "琥珀", "推击"),
}


@lru_cache(maxsize=512)
def visual_family(visual_key="", theme="", motion="", source="", kind="") -> str:
    """Resolve concrete visual meaning; specific status/effect wins over broad theme."""
    text = " ".join(str(value or "") for value in
                     (visual_key, motion, theme, source, kind)).lower()
    if "plant.release.gas" in text:
        return "poison"
    if "plant.release.snare" in text:
        return "magenta"
    for family, tokens in _TOKENS.items():
        if any(token in text for token in tokens):
            return family
    if any(token in text for token in ("enemy_strike", "hostile", "anomaly", "异象")):
        return "hostile"
    if any(token in text for token in ("melee", "近战", "撕裂", "cut", "needle")):
        return "orange"
    if any(token in text for token in ("throw", "thrown", "投掷")):
        return "brown"
    return ""


@lru_cache(maxsize=512)
def palette_for_visual(visual_key="", theme="", *, colors=(), motion=""):
    """Return semantic bright-to-deep inks, retaining authored hues as fallback."""
    family = visual_family(visual_key, theme, motion)
    if family:
        return PALETTES[family]
    authored = tuple(str(color) for color in (colors or ()) if _is_hex(color))
    if len(authored) >= 2:
        return authored[0], authored[1], authored[-1]
    return PALETTES["gold"]


def impact_origin_color(kind, *, origin="", resource="", damage_type="") -> str:
    """Color the hit by its source; trauma resource controls number typography only."""
    raw_origin = str(origin or "")
    if _is_hex(raw_origin):
        return raw_origin.lower()
    family = visual_family(source=raw_origin, kind=kind)
    if family:
        shade = 1 if family in ("poison", "sound", "black", "brown", "gray") else 0
        return PALETTES[family][shade]
    kind = str(kind or "").lower()
    if kind in ("ranged", "throw"):
        return PALETTES["bullet"][0] if kind == "ranged" else PALETTES["gold"][0]
    if kind == "melee":
        return PALETTES["orange"][1]
    if kind == "enemy_strike":
        return PALETTES["hostile"][0]
    # Environment cues keep their origin distinct from the lost resource.
    if kind == "damage":
        return PALETTES["gray"][1]
    return PALETTES["light"][1]


def impact_number_style(resource) -> str:
    """Lucidity trauma uses italic digits; bundled fonts lack math-script numerals."""
    return "italic" if str(resource or "") == "lucidity" else ""


def palette_layer_color(palette, layer, cell, index=0, *, blast=False):
    """Give one animation a restrained per-character palette and a blast gradient."""
    if blast:
        if layer.alpha >= .72:
            return palette[0]
        if layer.alpha >= .34:
            return palette[1]
        return palette[2]
    if layer.role == "ambient":
        return palette[2]
    return palette[(int(cell[0]) * 3 + int(cell[1]) * 5
                    + int(layer.z) + int(index)) % len(palette)]


def _is_hex(value):
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", str(value or "")))
