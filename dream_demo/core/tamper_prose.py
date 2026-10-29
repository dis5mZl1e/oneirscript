
"""篡改句子的最终组装：统一的标点与语序（2026-10-18 docs 第 8 节第一批）。

编辑器里的原句来自模板（自带句末标点），改后句由「动作子句 + 程度 + 战术条件」
拼成。旧实现各自拼接、最后无条件补句号，产生「。。」与「崩碎：〔墙〕……」这类
菜单标签句。本模块只负责把已经生成好的子句整理成一句自然文本：

- 中英文各用各的句末标点（。 / .）与并列分隔（，、 / , ）；
- 动作子句先去句末标点，条件子句去前导逗号，避免重复标点；
- 程度不再是句尾的「用的是『X』的力道」；程度词由动作子句自己放在谓语
  中间（2026-10-28 用户要求：形容词副词在句子中间，语序符合中文习惯）；
- 名称/引用里的标点不擅自改写，只处理子句边界。
"""
from __future__ import annotations

_TERMINAL_PUNCT = "。．.!！?？;；"
_LEADING_PUNCT = "，,、;；:： \t"


def strip_terminal(text: str) -> str:
    """去掉子句末尾的句末标点与空白（保留括号/引号本身）。"""
    return str(text).rstrip().rstrip(_TERMINAL_PUNCT).rstrip()


def strip_leading_clause_punct(text: str) -> str:
    return str(text).lstrip().lstrip(_LEADING_PUNCT).lstrip()


def final_period(language: str = "zh") -> str:
    return "." if str(language).startswith("en") else "。"


def clause_separator(language: str = "zh") -> str:
    return ", " if str(language).startswith("en") else "，"


def assemble_sentence(base: str, *,
                      clauses: tuple[str, ...] | list[str] = (),
                      language: str = "zh") -> str:
    """动作子句 + 条件子句 → 恰好一个句末标点的完整句子。

    程度词不再由这里追加到句尾：它属于动作子句的谓语成分，必须和动词一起
    出现在句子中间（见 core/tamper_world.py 的 insertion_preview）。这里只负责
    条件子句的并列与统一句末标点。
    """
    text = strip_terminal(base)
    cleaned = [strip_leading_clause_punct(clause) for clause in clauses if str(clause).strip()]
    cleaned = [clause for clause in cleaned if clause]
    unique: list[str] = []
    for clause in cleaned:
        if clause not in unique:
            unique.append(clause)
    cleaned = unique
    if cleaned:
        text = strip_terminal(text) + clause_separator(language) + clause_separator(language).join(cleaned)
    return strip_terminal(text) + final_period(language)


def discourse_separator(language: str = "zh") -> str:
    """原句与变更子句之间的分隔：中文用分号，英文用分号加空格。"""
    return "; " if str(language).startswith("en") else "；"


def compose_after(original: str, change: str, *, language: str = "zh") -> str:
    """改后句 = 原句语篇 + 变更子句（§15.10.1「改后句保留未改相关信息」）。

    地图篡改面板过去只把「〔北侧的砖墙〕将被点燃」这条动作片段当改后句，
    原句里点到的其他对象与区域就整句消失了——玩家看不出这一笔到底动了哪一处。
    这里只做语篇拼接：原句照原样保留，变更子句以分号接在后面，句末标点仍只有
    一个。不改名称、不重排、不补写任何机制。
    """
    base = strip_terminal(original)
    tail = strip_leading_clause_punct(strip_terminal(change))
    if not base:
        return tail + final_period(language) if tail else ""
    if not tail:
        return base + final_period(language)
    return base + discourse_separator(language) + tail + final_period(language)

