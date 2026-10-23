
"""Map display mode resolution (docs §13.2).

Unsupported terminals resolve image/auto to
the character map with a readable reason. Character mode is always respected.
The setting itself is persisted through the normal config path; this module only
turns it into an actual display mode for the current capability.
"""
from __future__ import annotations

from typing import Any
from functools import lru_cache

from ..i18n import tr

MAP_DISPLAY_CHOICES = ("auto", "image", "character")
IMAGE_BACKEND_AVAILABLE = False


@lru_cache(maxsize=1)
def _runtime_ready():
    try:
        from fontTools.ttLib import TTLibError
    except ImportError as error:
        return False, str(error)
    try:
        from .map_presentation import font_sources, glyph_mask
        font_sources()
        glyph_mask('❤',24,24)
        return True, ''
    except (ImportError,OSError,ValueError,TTLibError) as error:
        return False, str(error)


def image_backend_available(environ: dict[str, str] | None = None) -> tuple[bool, str]:
    """Whether the image output path can be used in this build/environment."""
    import os
    environment = os.environ if environ is None else environ
    if IMAGE_BACKEND_AVAILABLE or (environment.get('TERM_PROGRAM') == 'WezTerm'
                                   and environment.get('WEZTERM_PANE')
                                   and not environment.get('TMUX')):
        return _runtime_ready()
    return False, tr("当前终端不支持图像地图，请使用随包 WezTerm")



def resolve_map_display(config: Any, *,
                        image_available: bool | None = None) -> tuple[str, str]:
    """Resolve config map_display -> ('image'|'character', reason).

    - character: always honored;
    - image with unavailable backend: character + reason;
    - auto: image when available, otherwise character + reason;
    - invalid value: treated as auto.
    """
    mode = str(config.get("map_display") or "auto")
    if mode not in MAP_DISPLAY_CHOICES:
        mode = "auto"
    if mode == "character":
        return "character", tr("玩家选择字符地图")
    if image_available is None:
        image_available, reason = image_backend_available()
    else:
        reason = "" if image_available else tr("当前终端不支持图像地图，请使用随包 WezTerm")
    if image_available:
        return "image", tr("图像地图可用")
    if mode == "image":
        return "character", tr("图像不可用，已回退字符：{reason}", reason=reason)
    return "character", tr("自动回退字符地图：{reason}", reason=reason)
