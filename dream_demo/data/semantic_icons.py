"""Semantic icon registry for the section 16 subsets.

The packaged manifest is the single source of truth: codepoint, font source,
license. Business code asks for stable semantic keys; it never builds a PUA
codepoint by hand. Without the game WezTerm icon environment the helper returns
an empty string, so ordinary terminals and tests keep their text fallback.

2026-10-21（§16 专属补批）：前 32 项征兆用首批专属字形，其余 84 项原先只按
效果复用语义族（32 专属 + 84 复用）；现在 84 项各有**独有图形**，清单里
`second_batch` 记 84，115→116 项征兆全部直接命中 `portent.<id>`。
`_portent_fallback_icon` 保留为**兜底**：新增征兆还没配图时仍有个可读的族图标，
而不是空白——它不再承担「覆盖」职能。
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from ..cell_size import set_cell_size
from ..env_compat import flag as env_flag

FIRST_BATCH = 69
SECOND_BATCH = 85
RESERVE_COUNT = 32


def _manifest_path() -> Path | None:
    try:
        from ..terminal_launch import bundled_font_path
        base = bundled_font_path()
    except Exception:
        base = None
    if base is not None:
        candidate = base.parent / "semantic-icons.json"
        if candidate.is_file(): return candidate
    fallback = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "semantic-icons.json"
    return fallback if fallback.is_file() else None


@lru_cache(maxsize=1)
def manifest() -> dict:
    path = _manifest_path()
    if path is None: return {"fonts": [], "glyphs": [], "reserve_glyphs": []}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def icons() -> dict[str, dict]:
    original = {entry["key"]: entry for entry in manifest().get("glyphs", [])}
    result = dict(original)
    path = _manifest_path()
    aliases_path = path.parent/'semantic-icon-aliases.json' if path else None
    if aliases_path is not None and aliases_path.is_file():
        for alias in json.loads(aliases_path.read_text(encoding='utf8')).get('aliases', []):
            source = original.get(alias.get('reuse'))
            if source is not None and alias['key'] not in result:
                result[alias['key']] = {**source, **alias}
    # Growth pages request semantic keys, while expansion drawings live in the
    # main game font. Register the actual call-site aliases, including both
    # localized insight names, without copying or renumbering their outlines.
    from .expansion.catalog import ENTRIES
    for item in ENTRIES:
        if item['category'] not in ('ability', 'insight', 'memory'):
            continue
        keys = (('ability.' + item['id'],) if item['category'] == 'ability' else
                ('memory.' + item['id'],) if item['category'] == 'memory' else (
            'insight.' + item['name_zh'], 'insight.' + item['name_en'],
            'insight.' + item['id']))
        for key in keys:
            result[key] = dict(key=key, codepoint=f"U+{item['icon_codepoint']:04X}",
                               font='Dream Strata Icons', color=item['icon_color'],
                               source_character=item['source_character'],
                               reason=item['icon_reason'])
    return result


def semantic_icon(key: str) -> str:
    """Two-column PUA icon for a stable semantic key, or an empty string."""
    if not env_flag('ICONS'):
        return ""
    entry = icons().get(str(key or ""))
    if entry is None:
        return ""
    try:
        point = int(str(entry["codepoint"]).replace("U+", ""), 16)
    except (KeyError, TypeError, ValueError):
        return ""
    return set_cell_size(chr(point), 2)


_PORTENT_FALLBACK_RULES = (
    ("火", "portent.burning"), ("烧", "portent.burning"), ("灼", "portent.burning"),
    ("冻", "portent.frozen"), ("冰", "portent.frozen"), ("寒", "portent.frozen"),
    ("毒", "portent.poisoned"), ("酸", "portent.corroded"), ("蚀", "portent.corroded"),
    ("电", "portent.charged"), ("雷", "portent.charged"),
    ("烟", "portent.obscured"), ("尘", "portent.dusty"), ("雾", "portent.obscured"),
    ("惧", "portent.scream_fear"), ("恐", "portent.scream_fear"), ("惊", "portent.scream_fear"),
    ("眠", "portent.sedated"), ("睡", "portent.sedated"), ("镇静", "portent.sedated"),
    ("迟", "portent.sluggish"), ("粘", "portent.sluggish"), ("黏", "portent.sluggish"),
    ("麻", "portent.numb"), ("瘫", "portent.numb"), ("辐", "portent.irradiated"),
    ("忘", "portent.forgotten"), ("失忆", "portent.forgotten"),
    ("缠", "portent.snared"), ("钉", "portent.snared"), ("根", "portent.snared"),
    ("眩", "portent.door_vertigo"), ("门", "portent.door_vertigo"),
    ("声", "portent.whispering"), ("耳", "portent.whispering"),
    ("静", "portent.stillness"), ("寂", "portent.stillness"),
    ("清", "portent.clarity"), ("明", "portent.clarity"),
    ("暖", "portent.warmed"), ("温", "portent.warmed"),
    ("湿", "portent.moist"), ("水", "portent.moist"), ("液", "portent.moist"),
    ("月", "portent.moonlit"), ("星", "portent.starlit"),
    ("力", "portent.invigorated"), ("快", "portent.free_move"),
    ("滑", "portent.liquid_glide"), ("镜", "portent.lens_afterglow"),
    ("庇护", "portent.refuge_ward"), ("护", "portent.refuge_ward"),
    ("咖啡", "portent.caffeinated"), ("咒", "portent.cursed_sight"),
    ("双", "portent.double_exposure"), ("忧", "portent.worry_free"),
)


def _portent_fallback_icon(portent_id: str) -> str:
    """Family fallback for portents that have no dedicated glyph yet.

    Since the §16 supplementary batch every known portent has its own drawing,
    so this path is only reached by newly added portents that were not yet
    assigned one. It reuses the closest licensed semantic family rather than
    inventing a PUA codepoint; this is coverage, not a unique drawing.
    """
    try:
        from ..materials import PORTENT_DEFINITIONS
    except Exception:
        return ""
    definition = PORTENT_DEFINITIONS.get(str(portent_id or ""))
    if definition is None:
        return ""
    text = f"{definition.name}{definition.effect}{definition.material}"
    for keyword, icon_key in _PORTENT_FALLBACK_RULES:
        if keyword in text:
            return semantic_icon(icon_key)
    return semantic_icon("portent.double_exposure")


def portent_icon(portent_id: str) -> str:
    # Finite item phases reuse already shipped glyphs without adding font ranges.
    portent_id = {"modem_buffer": "caffeinated", "modem_recovery": "viscous_debt", "drug_mind_debt": "overclock"}.get(portent_id, portent_id)
    icon = semantic_icon("portent." + str(portent_id or ""))
    return icon or _portent_fallback_icon(portent_id)


def font_families() -> list[str]:
    return [face["family"] for face in manifest().get("fonts", [])]


def entry(key: str) -> dict | None:
    return icons().get(str(key or ""))


def icon_color(key: str, fallback: str = '#c7a6ed') -> str:
    return (entry(key) or {}).get('color', fallback)


def icon_label(key: str, label: str, style: str = ''):
    """Colour only the reused icon; retain field colour and readable fallback."""
    from rich.text import Text
    result = Text(style=style)
    icon = semantic_icon(key)
    if icon:
        result.append(icon, style=icon_color(key))
    result.append(label)
    return result
