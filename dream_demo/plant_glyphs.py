"""Plant tile glyphs on the same verified PUA pipeline as long-dream glyphs.

The catalog in data/plant_glyphs.json is authored from original 32px artwork and
built into a dedicated font by scripts/build_plant_glyphs.py. Availability is
proven from the manifest hash and the font cmap, never from file presence, so a
missing or stale font falls back to the existing literal map icons. The
common/PUA switch is the shared ``character_style`` setting; there is no
separate plant-only mode to keep in sync.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from .cell_size import set_cell_size
from .font_assets import asset_dir

FONT_FILE = 'DreamStrataPlantIcons.ttf'
FAMILY = 'Dream Strata Plant Icons'
MANIFEST = 'plant-glyphs.json'
ENV_FLAG = 'PLANT_ICONS_FONT'


def _catalog():
    path = Path(__file__).with_name('data') / 'plant_glyphs.json'
    return json.loads(path.read_text(encoding='utf-8'))


GLYPHS = _catalog()


@lru_cache(maxsize=4)
def _verified_codes(path, stamp, size, manifest_stamp, manifest_size):
    from fontTools.ttLib import TTFont, TTLibError
    try:
        data = json.loads(path.with_name(MANIFEST).read_text(encoding='utf-8'))
        if (data['file'] != FONT_FILE or data['family'] != FAMILY
                or data.get('glyphs') != GLYPHS):
            return frozenset()
        if hashlib.sha256(path.read_bytes()).hexdigest() != data['sha256']:
            return frozenset()
        with TTFont(path, lazy=True) as font:
            return frozenset(font.getBestCmap() or {})
    except (OSError, ValueError, KeyError, TTLibError):
        return frozenset()


def available_codes():
    path = asset_dir() / FONT_FILE
    try:
        st, ms = path.stat(), path.with_name(MANIFEST).stat()
    except OSError:
        return frozenset()
    return _verified_codes(path, st.st_mtime_ns, st.st_size, ms.st_mtime_ns, ms.st_size)


@lru_cache(maxsize=8)
def _presentation_codes(style, raster, env_on):
    # Same refresh boundary as realm_glyphs: recompute only when the shared
    # presentation token changes, never stat a font per map cell.
    if style != 'pua' or not (raster or env_on):
        return frozenset()
    return available_codes()


def invalidate():
    _presentation_codes.cache_clear()
    _verified_codes.cache_clear()


def private_glyph(key):
    entry = GLYPHS.get(key)
    if entry is None:
        return None
    from .env_compat import flag
    from .realm_glyphs import presentation_token
    style, raster, _walls, _emoji = presentation_token()
    codes = _presentation_codes(style, raster, flag(ENV_FLAG))
    if entry['codepoint'] not in codes:
        return None
    return set_cell_size(chr(entry['codepoint']), 2)
