"""Verified, identity-specific long-dream glyphs; never rewrite literal emoji."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from .cell_size import set_cell_size
from .font_assets import asset_dir

FONT_FILE = 'DreamStrataLongDream.ttf'
FAMILY = 'Dream Strata Long Dream'
MANIFEST = 'long-dream-glyphs.json'
_active_codes = frozenset()
_active_emoji_codes = frozenset()
_raster = False
_style = None  # None preserves legacy callers outside a configured game session.


def set_character_style(value, *, raster=None, refresh=True, font_coverage=None):
    global _style, _raster, _active_codes, _active_emoji_codes
    if raster is not None:
        _raster = bool(raster)
    if value is None:
        _raster = False
    style = value if value in ('common', 'pua') else None
    # Frame/panel queries only synchronize settings. Explicit presentation
    # boundaries retain the default refresh, including same-style font changes.
    if not refresh and style == _style:
        return
    _style = style
    # Refresh once at the presentation boundary, never stat fonts per map cell.
    _active_codes = (frozenset(font_coverage['long']) if font_coverage is not None
                     else available_codes()) if _style == 'pua' else frozenset()
    _active_emoji_codes = (frozenset(font_coverage['emoji']) if font_coverage is not None
                           else available_emoji_codes()) if _style is not None else frozenset()


def character_style():
    return _style


def presentation_token():
    return _style, _raster, _active_codes, _active_emoji_codes


def _catalog():
    path = Path(__file__).with_name('data') / 'long_dream_glyphs.json'
    return json.loads(path.read_text(encoding='utf-8'))


GLYPHS = _catalog()
OBJECT_ROUTES = json.loads((Path(__file__).with_name('data') / 'object_glyph_routes.json').read_text(encoding='utf-8'))
EMOJI_BY_KEY = {r['legacy_key']:r['character'] for r in OBJECT_ROUTES.values() if r['kind']=='emoji'}
EMOJI_CHARACTERS = frozenset(c for r in OBJECT_ROUTES.values() if r['kind']=='emoji' for c in (r['character'],r['fallback']))
EMOJI_EDITS = {ord(r['character']) for r in OBJECT_ROUTES.values() if r.get('path')}
EMOJI_ROUTES = {r['legacy_key']:r for r in OBJECT_ROUTES.values() if r['kind']=='emoji'}


def emoji_character(route):
    from .env_compat import flag
    if route.get('path') and not ((_raster or flag('OBJECT_EMOJI_FONT')) and ord(route['character']) in _active_emoji_codes):
        return route['fallback']
    return route['character']


def emoji_for_key(key):
    route = EMOJI_ROUTES.get(key)
    return emoji_character(route) if route else key


def object_route(definition_id, definition):
    route = OBJECT_ROUTES.get(definition_id)
    if route is None:
        return None
    literal = definition.get('icon', '')
    if literal != route.get('authored_icon', ''):
        return None  # A newly authored icon remains authoritative.
    return emoji_character(route) if route['kind']=='emoji' else route['key']


@lru_cache(maxsize=4)
def _verified_emoji_codes(path, stamp, size, manifest_stamp, manifest_size):
    from fontTools.ttLib import TTFont, TTLibError
    try:
        data = json.loads(path.with_name('object-emoji.json').read_text(encoding='utf-8'))
        if data.get('file') != path.name or data.get('family') != 'Dream Strata Object Emoji':
            return frozenset()
        if hashlib.sha256(path.read_bytes()).hexdigest() != data.get('sha256'):
            return frozenset()
        with TTFont(path,lazy=True) as font:
            codes = frozenset(font.getBestCmap() or {})
        return codes if not any(0xe000<=cp<=0xf8ff or 0xf0000<=cp<=0x10fffd for cp in codes) else frozenset()
    except (OSError,ValueError,KeyError,TTLibError):
        return frozenset()


def available_emoji_codes():
    path=asset_dir()/'DreamStrataObjectEmoji.ttf'
    try:
        st,ms=path.stat(),path.with_name('object-emoji.json').stat()
        return _verified_emoji_codes(path,st.st_mtime_ns,st.st_size,ms.st_mtime_ns,ms.st_size)
    except OSError:
        return frozenset()


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
        return _verified_codes(path, st.st_mtime_ns, st.st_size, ms.st_mtime_ns, ms.st_size)
    except OSError:
        return frozenset()


def private_glyph(key):
    from .env_compat import flag
    if _style != 'pua' or not (_raster or flag('LONG_DREAM_FONT')):
        return None
    entry = GLYPHS.get(key)
    if entry and entry['codepoint'] in _active_codes:
        return set_cell_size(chr(entry['codepoint']), 2)
    return None


def item_key(definition_id, definition):
    # Explicit emoji/literal icons remain authoritative unless this exact identity
    # was reviewed in the catalog (only non-emoji authored icons are registered).
    key = 'realm-item:' + definition_id
    entry = GLYPHS.get(key)
    if not entry:
        return None
    literal = definition.get('icon')
    if literal and literal != entry.get('legacy_icon'):
        return None
    return key
