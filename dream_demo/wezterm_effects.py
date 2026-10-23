"""Private terminal effects resources, kept outside onefile temporary extraction."""
from __future__ import annotations

from pathlib import Path
import sys

from .font_assets import copy_asset,private_cache_dir


def bundled_effects_dir() -> Path:
    if getattr(sys,'frozen',False):
        return Path(getattr(sys,'_MEIPASS','.'))/'wezterm'
    return Path(__file__).resolve().parents[1]/'assets/wezterm'


def install_effects(base:Path) -> Path | None:
    source=bundled_effects_dir()
    names=('dream_effects.lua','mist.png','ribbons.png','still.png')
    if not all((source/name).is_file() for name in names):
        return None
    for directory in (base/'.wezterm/effects',private_cache_dir()/'effects'):
        try:
            for name in names:
                copy_asset(source/name,directory/name)
            return directory.resolve()
        except OSError:
            continue
    # Fonts and the game remain usable when the optional appearance cache fails.
    return None
