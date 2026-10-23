"""玩家配置文件（主文件夹的 ``game_config.ini``）读写与优先级（2026-09-20）。

为什么需要一个外部文件
----------------------
游戏内的设置页已经能把设置写进 ``save/config.json``，但要玩家先玩一局、
翻到设置页才能改。这个文件让玩家可以**开局前**用记事本直接改：语言、音效
开关与音量、画面特效、按键等都在里面，改完保存、重启游戏即生效。

优先级（从低到高）
------------------
1. 内置默认值（``SETTING_REGISTRY`` 的 default）
2. 本文件 game_config.ini 的取值
3. 游戏内设置记录（save/config.json 里玩家**亲手改过**的项）

第 3 条只对「玩家在游戏内改过」的项成立——为此 ConfigManager 会记录
``touched``（被显式改动的键）。于是「语言」天然满足需求：初次开启没有
设置记录时按本文件走，玩家在游戏内选过语言后永远按那次选择走。

想让本文件强制压过游戏内记录：把 ``[general] override_saved_settings``
改成 true（语言除外，它始终尊重游戏内记录）。

文件缺失时会自动生成一份带注释的模板；解析失败/非法取值一律忽略并回退，
绝不因为配置文件写错而让游戏起不来。
"""
from __future__ import annotations

import configparser
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .config import SETTING_REGISTRY, SettingDef, SettingType
from .i18n import LANGUAGE_PACKS

CONFIG_FILENAME = "game_config.ini"

# 模板注释一律中英双行：上面中文、下面英文（英文取自 i18n 的 EN 包，写新设置项
# 时顺手补 EN，模板与设置页就都自动双语了）。
EN: dict[str, str] = LANGUAGE_PACKS.get("en", {})


def _english(text: str) -> str:
    """取一条文案的英文版；未登记或与中文相同则返回空串（调用方跳过该行）。"""
    translated = EN.get(text, "")
    return "" if translated == text else translated


# 模板的分组与顺序；没明确归组的键落到 general。
SECTION_ORDER: tuple[tuple[str, str, str], ...] = (
    ("general", "基础", "General"),
    ("display", "画面", "Display"),
    ("audio", "音频", "Audio"),
    ("gameplay", "玩法", "Gameplay"),
    ("keys", "按键", "Keys"),
)

SECTION_KEYS: dict[str, tuple[str, ...]] = {
    "general": ("language",),
    "display": ("symbol_mode", "fx_quality", "fx_scanlines", "floor_transition",
                "fx_light_walls", "map_display", "map_observe"),
    "audio": ("sfx_enabled", "sfx_volume", "music_enabled", "music_volume"),
    "gameplay": ("auto_pickup", "show_details", "numpad5_wait"),
    "keys": ("key_up", "key_down", "key_left", "key_right", "key_tamper"),
}

from .controls import PANEL_SHORTCUTS
SECTION_KEYS['keys'] += tuple(entry.setting for entry in PANEL_SHORTCUTS)

# 个别键在模板里用更贴近玩家的说明替代注册表的 description（中 / 英）。
EXTRA_KEY_NOTES: dict[str, tuple[str, str]] = {
    "language": (
        "首选语言：初次开启、游戏内没选过语言时按这里；在游戏内选过语言后永远按那次选择。",
        "Preferred language: used on first launch / when never set in game; once you pick a "
        "language in game, that choice always wins.",
    ),
    "key_up": ("面板向上主键（WASD 面板操作，不是方向键走路）", "Panel Up key (WASD panel control, not arrow-key walking)"),
    "key_down": ("面板向下主键", "Panel Down key"),
    "key_left": ("面板向左主键", "Panel Left key"),
    "key_right": ("面板向右主键", "Panel Right key"),
    "key_tamper": ("对话中打开篡改面板的按键；只在事件/NPC 对话里生效",
                   "Key that opens the tampering panel in dialogue; only active there"),
}

# 只存在于本文件的开关（不在设置页注册表里）：(键, 默认值, 中文说明, 英文说明)。
EXTRA_BOOL_OPTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "override_saved_settings",
        "false",
        "true = 本文件的取值覆盖游戏内改过的设置；false = 游戏内改过的项保留。语言不受此项影响。",
        "true = values here override settings changed in game; false = in-game changes win. "
        "Does not apply to the language option.",
    ),
)

_TRUE_TOKENS = frozenset({"1", "true", "yes", "on", "y", "t", "开", "开启", "是", "启用"})
_FALSE_TOKENS = frozenset({"0", "false", "no", "off", "n", "f", "关", "关闭", "否", "禁用"})

_HEADER = """\
; ============================================================================
;  梦层 · 玩家配置文件  /  Oneirscript · Player Config  (game_config.ini)
; ----------------------------------------------------------------------------
;  改完保存后**重启游戏**即可生效；游戏运行中改这个文件不会被读取。
;  Save this file and restart the game to apply; edits are not read while running.
;
;  生效优先级（高 → 低）/ Priority (high -> low):
;    ① 游戏内设置页改过的项（记录在 save/config.json）
;       options changed in the in-game settings page (saved in save/config.json)
;    ② 本文件的取值 / values in this file
;    ③ 游戏内置默认值 / built-in defaults
;  也就是说：没在游戏里动过的项，一律听本文件的；在游戏里选过的项（比如
;  语言）以游戏内那次选择为准。想让本文件全部说了算，把下面
;  override_saved_settings 改成 true（语言仍然尊重游戏内记录）。
;  In short: options you never touched in game follow this file; options you did
;  change (e.g. language) keep your in-game choice. To let this file win
;  everywhere, set override_saved_settings below to true (language stays yours).
;
;  写法 / Syntax:
;    开关 booleans：true / false（也接受 1/0、开/关、yes/no、on/off）
;    数值 numbers：0~10        文本 enums：选项名 / option name
;    按键 keys：单个字符或 Alt+字母／数字 / one character or Alt+letter/digit
;    以 ; 或 # 开头的是注释，行尾注释同样会被忽略。
;    Lines starting with ; or # are comments; trailing comments are stripped too.
;    写错的项会被忽略并回退默认值，不影响其余项。
;    Bad values are ignored and fall back to defaults; other options still apply.
;  本文件为 UTF-8 编码，用记事本改完请保持编码不变（也接受 GBK）。
;  This file is UTF-8 (BOM); GBK is also accepted when reading.
; ============================================================================
"""


# ---- 路径 ---------------------------------------------------------------

def base_directory() -> Path:
    """配置文件所在的主文件夹：打包后是 exe 同目录，开发态是仓库根。"""
    if getattr(sys, "frozen", False):  # PyInstaller 打包态
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def config_path(base: str | Path | None = None) -> Path:
    directory = Path(base) if base is not None else base_directory()
    return directory / CONFIG_FILENAME


# ---- 取值解析 ------------------------------------------------------------

def _parse_bool(raw: str) -> bool | None:
    token = raw.strip().lower()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return None


def _parse_value(definition: SettingDef, raw: str) -> Any | None:
    """把配置文件里的字符串转成设置项取值；无法识别返回 None（忽略该项）。"""
    token = raw.strip().strip("\"'").strip()
    if not token:
        return None
    if definition.setting_type is SettingType.BOOL:
        return _parse_bool(token)
    if definition.setting_type is SettingType.INT:
        try:
            return int(token, 10)
        except ValueError:
            return None
    if definition.setting_type is SettingType.ENUM:
        lowered = token.lower()
        return token if token in definition.choices else (lowered if lowered in definition.choices else None)
    if definition.setting_type is SettingType.KEY_BIND:
        candidate = token.lower()
        if candidate.startswith('alt+'):
            return candidate if len(candidate) == 5 and candidate[-1].isascii() and candidate[-1].isalnum() else None
        return candidate if len(candidate) == 1 else None
    return None


def _read_text(path: Path) -> str | None:
    """按 utf-8(BOM 可选) → gbk → utf-8 顺序读；都失败返回 None。

    记事本在中文 Windows 上可能把文件存成 GBK，多试一种编码能救回手改过的文件。
    """
    for encoding in ("utf-8-sig", "gbk", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except (OSError, UnicodeDecodeError, LookupError):
            continue
    return None


# ---- 模板生成 ------------------------------------------------------------

def _hint(definition: SettingDef) -> tuple[str, str]:
    """取值写法提示（中 / 英）。"""
    if definition.setting_type is SettingType.BOOL:
        return "开关：true / false", "Boolean: true / false"
    if definition.setting_type is SettingType.INT:
        low = definition.minimum if definition.minimum is not None else 0
        high = definition.maximum if definition.maximum is not None else 10
        return f"数值：{low} ~ {high}", f"Number: {low} ~ {high}"
    if definition.setting_type is SettingType.ENUM:
        return (
            "可选：" + " / ".join(definition.choices),
            "Options: " + " / ".join(definition.choices),
        )
    if definition.setting_type is SettingType.KEY_BIND:
        return (
            "单个字符或 Alt+字母／数字（不能与 123456789 . f g e q u n b i k ? / h \\ 冲突）",
            "One character or Alt+letter/digit (must not collide with 123456789 . f g e q u n b i k ? / h \\)",
        )
    return "", ""


def _format_default(definition: SettingDef) -> str:
    default = definition.default
    if definition.setting_type is SettingType.BOOL:
        return "true" if default else "false"
    return str(default)


def _note(key: str, definition: SettingDef) -> tuple[str, str]:
    """一条设置的说明（中 / 英）：优先用模板专用文案，否则用注册表 description。

    注册表 description 是中文原文、同时是 i18n 的键，英文直接从 EN 包取；
    新加的设置项只要补了 EN，模板与设置页就都是双语的。
    """
    override = EXTRA_KEY_NOTES.get(key)
    if override is not None:
        return override
    if definition.description:
        return definition.description, _english(definition.description)
    # 没有 description 的项（比如按键）退回标签名
    return definition.label, _english(definition.label)


def render_template(registry: Iterable[SettingDef] = SETTING_REGISTRY) -> str:
    """按注册表生成带注释的模板文本（注册表新增项会自动出现在模板里）。"""
    definitions = {definition.key: definition for definition in registry}
    grouped: dict[str, list[str]] = {name: [] for name, _zh, _en in SECTION_ORDER}
    assigned: set[str] = set()
    for name, keys in SECTION_KEYS.items():
        for key in keys:
            if key in definitions:
                grouped[name].append(key)
                assigned.add(key)
    for key, definition in definitions.items():
        if key in assigned or definition.setting_type is SettingType.ACTION:
            continue
        grouped.setdefault("general", []).append(key)

    lines: list[str] = [_HEADER]
    for name, label, label_en in SECTION_ORDER:
        keys = grouped.get(name) or []
        if not keys:
            continue
        lines.append(f"\n; ---------------- {label} / {label_en} ----------------")
        lines.append(f"[{name}]")
        if name == "general":
            for option, default, note, note_en in EXTRA_BOOL_OPTIONS:
                lines.append(f"; {note}")
                lines.append(f"; {note_en}")
                lines.append(f"{option} = {default}")
        for key in keys:
            definition = definitions[key]
            note_zh, note_en = _note(key, definition)
            hint_zh, hint_en = _hint(definition)
            if note_zh:
                lines.append(f"; {note_zh}")
            if note_en:
                lines.append(f"; {note_en}")
            if hint_zh:
                lines.append(f"; {hint_zh}")
            if hint_en:
                lines.append(f"; {hint_en}")
            lines.append(f"{key} = {_format_default(definition)}")
    return "\n".join(lines) + "\n"


def write_template(path: str | Path, overwrite: bool = False) -> bool:
    """写出模板；文件已存在且不允许覆盖时返回 False。"""
    target = Path(path)
    if target.exists() and not overwrite:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_template(), encoding="utf-8-sig")
    except OSError:
        return False
    return True


# ---- 加载 ----------------------------------------------------------------

@dataclass
class UserConfigFile:
    """解析结果：取值、开关、以及解析过程中被忽略的项（供排查）。"""

    path: Path
    values: dict[str, Any] = field(default_factory=dict)
    override_saved: bool = False
    created: bool = False
    problems: list[str] = field(default_factory=list)

    def get(self, key: str, fallback: Any = None) -> Any:
        return self.values.get(key, fallback)


def _parse(path: Path, registry: Iterable[SettingDef]) -> UserConfigFile:
    result = UserConfigFile(path=path)
    definitions = {definition.key: definition for definition in registry}
    extra = {name for name, _default, _note, _note_en in EXTRA_BOOL_OPTIONS}
    text = _read_text(path)
    if text is None:
        result.problems.append("无法读取（编码或权限问题）")
        return result

    parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    try:
        parser.read_string(text)
    except configparser.Error as error:
        result.problems.append(f"格式错误：{error}")
        return result

    seen: set[str] = set()
    for section in parser.sections():
        for option, raw in parser.items(section):
            key = option.strip().lower()
            seen.add(key)
            if key in extra:
                parsed = _parse_bool(raw)
                if parsed is None:
                    result.problems.append(f"{key} 取值无法识别（已忽略）")
                    continue
                if key == "override_saved_settings":
                    result.override_saved = parsed
                continue
            definition = definitions.get(key)
            if definition is None or definition.setting_type is SettingType.ACTION:
                result.problems.append(f"未知配置项 {key}（已忽略）")
                continue
            parsed = _parse_value(definition, raw)
            if parsed is None:
                result.problems.append(f"{key} 取值无法识别（已忽略）")
                continue
            result.values[key] = parsed
    return result


def load_user_config(
    base: str | Path | None = None,
    ensure: bool = True,
    registry: Iterable[SettingDef] = SETTING_REGISTRY,
) -> UserConfigFile:
    """读取主文件夹的配置文件；缺失时先生成模板再读（模板里全是默认值）。"""
    path = config_path(base)
    created = False
    if ensure and not path.exists():
        try:
            created = write_template(path)
        except Exception:  # 只读目录（比如装在 Program Files）下不生成也不报错
            pass
    if not path.exists():
        return UserConfigFile(path=path, created=created, problems=["配置文件缺失"])
    result = _parse(path, registry)
    result.created = created
    return result
