"""§14 language-syntax data: Chinese columns vs English 4-6 role rotation.

Two different things live here, and they must not be confused:

* ``column_roles(syntax)`` — the reviewed role table the compiler consumes. The
  English table rotates columns 4–6 (verb/object/modifier) so an English board
  reads *Action + Object + Modifier* instead of the Chinese *Modifier + Action +
  Object*.
* ``default_syntax()`` — which table **new boards** start with. It is a machine
  preference (Settings → 装备句法), never a world rule: an existing board keeps
  the syntax recorded in its own save, so switching the preference can never
  reinterpret a built board behind the player's back (§14.13 item 5).
"""
from __future__ import annotations

from .roles import COLUMN_ROLES, ROLE_LABELS

ZH_SYNTAX = "zh"
EN_SYNTAX = "en"
SYNTAXES = (ZH_SYNTAX, EN_SYNTAX)
SYNTAX_LABELS = {ZH_SYNTAX: "中文语序", EN_SYNTAX: "英文语序"}

COLUMN_ROLES_ZH = tuple(COLUMN_ROLES)
COLUMN_ROLES_EN = ("condition", "source", "modifier", "verb",
                   "object", "modifier", "complement", "complement")
COLUMN_LABELS_ZH = ("条件", "载体", "修饰", "修饰", "行为", "对象", "补语", "补语")
COLUMN_LABELS_EN = ("Condition", "Carrier", "Modifier", "Action",
                    "Object", "Modifier", "Complement", "Complement")

# 新盘面默认语序。只由设置页/开局选项通过 set_default_syntax 改动；
# 已有盘面各自带 syntax 字段，不读这个值。
_DEFAULT_SYNTAX = ZH_SYNTAX


def column_roles(syntax: str = ZH_SYNTAX) -> tuple[str, ...]:
    return COLUMN_ROLES_EN if syntax == EN_SYNTAX else COLUMN_ROLES_ZH


def board_roles(board) -> tuple[str, ...]:
    """盘面自己的列角色。**所有**编译入口都要走这里，别各写一套默认值。

    2026-10-20 修：此前只有 ``grammar.compile_board`` 读 ``board.syntax``，
    编辑器预览、占位合法性、EquipmentView 仍按中文列编译——设置项等于摆设。
    """
    return column_roles(getattr(board, "syntax", ZH_SYNTAX))


def column_labels(syntax: str = ZH_SYNTAX) -> tuple[str, ...]:
    return COLUMN_LABELS_EN if syntax == EN_SYNTAX else COLUMN_LABELS_ZH


def normalize_syntax(value: object) -> str:
    """把设置值收敛到受支持语序；未知值退回中文语序（旧配置/旧档安全）。"""
    text = str(value or "").strip().lower()
    return text if text in SYNTAXES else ZH_SYNTAX


def default_syntax() -> str:
    return _DEFAULT_SYNTAX


def set_default_syntax(value: object) -> str:
    """设置新盘面默认语序，返回生效值。已有盘面不受影响。"""
    global _DEFAULT_SYNTAX
    _DEFAULT_SYNTAX = normalize_syntax(value)
    return _DEFAULT_SYNTAX


def syntax_label(syntax: str) -> str:
    return SYNTAX_LABELS.get(syntax, SYNTAX_LABELS[ZH_SYNTAX])


# ---- 角色名（按角色而不是按列号取，换语序后列号会变）----
# 中文名沿用 ROLE_LABELS（UI 用 tr() 翻成英文，词表与其它界面一致：行为→Verb）；
# 短标识（盘面表头）按语言给：中文「条载饰行对补」，英文 C/S/M/V/O/A。
_ROLE_INDEX = {role: index for index, role in enumerate(COLUMN_ROLES)}
_SHORT_EN = {"condition": "C", "source": "S", "modifier": "M",
             "verb": "V", "object": "O", "complement": "A"}
_SHORT_ZH = {"condition": "条", "source": "载", "modifier": "饰",
             "verb": "行", "object": "对", "complement": "补"}


def role_name(role: str) -> str:
    """角色的中文名（未翻译）；未知角色原样返回。"""
    index = _ROLE_INDEX.get(role)
    return ROLE_LABELS[index] if index is not None else role


def role_short(role: str, language: str = "zh") -> str:
    table = _SHORT_EN if language == "en" else _SHORT_ZH
    return table.get(role, "?")


def column_names(syntax: str = ZH_SYNTAX) -> tuple[str, ...]:
    """该语序下每一列的角色中文名（列号→名），按语序排；调用方负责 tr()。"""
    return tuple(role_name(role) for role in column_roles(syntax))


def column_shorts(syntax: str = ZH_SYNTAX, language: str = "zh") -> tuple[str, ...]:
    return tuple(role_short(role, language) for role in column_roles(syntax))


def column_groups(syntax: str = ZH_SYNTAX) -> tuple[tuple[str, int], ...]:
    """盘面语法行的分组：(列号区间文本, 起始列)。相邻同角色列合并。

    中文语序下 3–4 都是「修饰」，英文语序下 3/4/5 分别是修饰/行为/对象——
    所以分组必须从角色表算，不能写死。
    """
    roles = column_roles(syntax)
    groups: list[tuple[str, int]] = []
    start = 0
    for index in range(1, len(roles) + 1):
        if index == len(roles) or roles[index] != roles[start]:
            if index - 1 == start:
                label = str(start + 1)
            else:
                label = f"{start + 1}–{index}"
            groups.append((label, start))
            start = index
    return tuple(groups)
