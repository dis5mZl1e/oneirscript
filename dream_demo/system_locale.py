"""首次启动的系统语言判定（2026-10-23）。

游戏只有中文 / English 两套界面；装备句法（中英文列角色）随界面语言走。
优先读显式环境变量，其次 Windows 的 UI 语言，再其次 POSIX 的 LC_*/LANG。
无法判断或不是中文系统时回退 English，中文系统回退中文。
"""
from __future__ import annotations

import locale
import os
import sys

from .env_compat import get as env_get

SUPPORTED = ("zh", "en")


def normalize_language(value: object, default: str = "zh") -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if text.startswith("zh") or "chinese" in text:
        return "zh"
    if text.startswith("en") or "english" in text:
        return "en"
    if text:
        return "en"
    return default


def system_language(default: str = "zh") -> str:
    """当前系统语言对应的游戏语言（zh/en）。"""
    override = env_get("LANGUAGE")
    if override:
        return normalize_language(override, default)
    if sys.platform == "win32":
        try:
            import ctypes

            lcid = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
            # 主语言 ID 0x04 = 中文（简繁都归中文界面）。
            return "zh" if (lcid & 0x3FF) == 0x04 else "en"
        except Exception:
            pass
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable)
        if value:
            return normalize_language(value, default)
    try:
        value, _encoding = locale.getlocale()
    except Exception:
        value = None
    return normalize_language(value, default)


def first_run_defaults(default: str = "zh") -> dict[str, str]:
    """首次生成 game_config.ini 时的语言相关默认值。"""
    language = system_language(default)
    return {"language": language, "equipment_syntax": language}
