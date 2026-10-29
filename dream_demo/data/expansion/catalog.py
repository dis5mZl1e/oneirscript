"""Canonical catalog for the six-theme content expansion.

The JSON file is the source of truth for names, item behavior, Unicode glyph
provenance, source permissions, and the fixed item identity. Runtime systems
can build their existing definition views from this module without copying
the underlying content into multiple registries.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..cell_size_compat import cell_len


CATALOG_PATH = Path(__file__).with_name("catalog.json")
THEMES = ("sound", "light", "terrain", "projectile", "circuit", "realm")
CATEGORIES = ("equipment", "insight", "memory", "ability", "consumable")
EQUIPMENT_POSITION_ROLES = ("modifier", "verb", "complement")


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported item expansion schema: {payload.get('schema_version')!r}")
    entries = tuple(payload.get("entries", ()))
    tuning_defaults = payload.get("tuning_defaults") or {}
    _validate(entries, tuning_defaults)
    return tuning_defaults, entries


def _validate(entries: tuple[dict[str, Any], ...],
              tuning_defaults: dict[str, Any]) -> None:
    required_tuning = {
        "unquantified_effect_magnitude", "max_applications_per_matching_trigger",
        "brief_duration_turns", "temporary_duration_turns",
        "several_turn_duration_turns", "consumable_uses_per_copy",
        "rare_consumable_acquisitions_per_run",
        "very_rare_consumable_acquisitions_per_run", "category_weights_percent",
        "local_theme_weight_percent", "cross_theme_weight_percent",
        "recent_id_exclusion_window", "noncore_opportunity_reduction_percent",
        "opportunity_reduction_fallback_percent", "event_clues_per_opportunity",
        "equipment_targets_per_event_category", "other_targets_per_event_category",
        "event_awards_per_opportunity",
    }
    missing_tuning = required_tuning - tuning_defaults.keys()
    if missing_tuning:
        raise ValueError(f"Missing numeric tuning defaults: {sorted(missing_tuning)}")
    if sum(tuning_defaults["category_weights_percent"].values()) != 100:
        raise ValueError("Category weights must sum to 100 percent")
    if (tuning_defaults["local_theme_weight_percent"]
            + tuning_defaults["cross_theme_weight_percent"] != 100):
        raise ValueError("Theme weights must sum to 100 percent")
    if tuning_defaults["event_clues_per_opportunity"] != {"min": 2, "max": 3}:
        raise ValueError("Event clues must be tuned to two or three choices")
    ids = [entry.get("id") for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Item expansion IDs must be unique")
    pua = [entry.get("icon_codepoint") for entry in entries]
    if len(pua) != len(set(pua)):
        raise ValueError("Item expansion PUA codepoints must be unique")
    source_chars = [entry.get("source_character") for entry in entries]
    if any(not isinstance(char, str) or len(char) != 1 for char in source_chars):
        raise ValueError("Each expansion source character must be one Unicode codepoint")
    required = {
        "id", "theme", "category", "name_zh", "name_en", "description_zh",
        "description_en", "intro_zh", "intro_en", "effect", "rarity",
        "source_permission", "source_id", "min_depth", "source_character",
        "source_kind", "source_font", "license_key", "terminal_fallback", "fallback",
        "icon_codepoint", "icon_color", "tuning_proposal",
    }
    for entry in entries:
        missing = required - entry.keys()
        if missing:
            raise ValueError(f"{entry.get('id', '<unknown>')} is missing {sorted(missing)}")
        if entry["theme"] not in THEMES or entry["category"] not in CATEGORIES:
            raise ValueError(f"Invalid theme/category for {entry['id']}")
        if entry["source_permission"] not in {"G", "D"}:
            raise ValueError(f"Invalid source permission for {entry['id']}")
        tuning = entry["tuning_proposal"]
        if tuning.get("unlock_depth") != entry["min_depth"]:
            raise ValueError(f"Tuning depth disagrees with catalog depth: {entry['id']}")
        if not isinstance(tuning.get("max_acquisitions_per_run"), int):
            raise ValueError(f"Missing numeric run cap: {entry['id']}")
        if entry["category"] == "consumable" and tuning.get("uses_per_copy") != 1:
            raise ValueError(f"Consumables must be finite one-use items: {entry['id']}")
        if entry["category"] == "ability" and (
                tuning.get("imagination_cost") != entry["effect"].get("imagination_cost")
                or tuning.get("cooldown_turns") != entry["effect"].get("cooldown")):
            raise ValueError(f"Ability tuning disagrees with its fixed cost/cooldown: {entry['id']}")
        if cell_len(entry["terminal_fallback"]) != 2:
            raise ValueError(f"Terminal fallback must occupy two cells: {entry['id']}")
        if entry["category"] == "equipment":
            readings = entry.get("position_readings") or {}
            values_by_language = {language: [] for language in ("zh", "en")}
            for role in EQUIPMENT_POSITION_ROLES:
                phrase = readings.get(role) or {}
                for language in values_by_language:
                    value = phrase.get(language)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            f"{entry['id']} lacks {language} {role} reading")
                    values_by_language[language].append(value.strip())
            if any(len(set(values)) != len(EQUIPMENT_POSITION_ROLES)
                   for values in values_by_language.values()):
                raise ValueError(f"{entry['id']} repeats a sentence-position reading")
        codepoint = entry["icon_codepoint"]
        if isinstance(codepoint, str):
            codepoint = int(codepoint, 16)
        if not 0xE588 <= codepoint <= 0xE677:
            raise ValueError(f"Expansion icon is outside its reserved PUA band: {entry['id']}")


TUNING_DEFAULTS, ENTRIES = _load()
BY_ID: dict[str, dict[str, Any]] = {entry["id"]: entry for entry in ENTRIES}


def get_entry(entry_id: str) -> dict[str, Any] | None:
    """Return one catalog row by its stable expansion ID."""
    return BY_ID.get(entry_id)


def localized_value(entry: dict[str, Any], field: str, language: str = "zh") -> str:
    """Read one localized name, description, intro, or category label."""
    suffix = "en" if language == "en" else "zh"
    value = entry.get(f"{field}_{suffix}")
    if value:
        return str(value)
    fallback = entry.get(f"{field}_zh")
    return str(fallback or "")


def equipment_position_reading(entry_id: str, role: str,
                               language: str = "zh") -> str:
    """Return a reviewed phrase for one equipment sentence role.

    These phrases describe how a fixed item can be read in the equipment
    sentence language. They do not themselves grant or execute an effect.
    """
    entry = BY_ID.get(entry_id)
    if not entry or entry.get("category") != "equipment":
        return ""
    reading = (entry.get("position_readings") or {}).get(role) or {}
    suffix = "en" if language == "en" else "zh"
    return str(reading.get(suffix) or "")


def by_category(category: str) -> tuple[dict[str, Any], ...]:
    """Return rows in the source-file order for a content type."""
    return tuple(entry for entry in ENTRIES if entry["category"] == category)


def by_theme(theme: str) -> tuple[dict[str, Any], ...]:
    """Return rows in the source-file order for a theme."""
    return tuple(entry for entry in ENTRIES if entry["theme"] == theme)


def catalog_counts() -> dict[str, Counter[str]]:
    """Return type, theme, permission, and source-family counts for audits."""
    return {
        "category": Counter(entry["category"] for entry in ENTRIES),
        "theme": Counter(entry["theme"] for entry in ENTRIES),
        "permission": Counter(entry["source_permission"] for entry in ENTRIES),
        "source_kind": Counter(entry["source_kind"] for entry in ENTRIES),
    }
