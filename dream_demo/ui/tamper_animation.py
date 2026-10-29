"""篡改面板局部 UI 动画（2026-10-26，ASCII 动画扩展 T01/T05）。

纯 UI、装饰时钟：只改 Rich 文本前缀/颜色，不改世界、不扣费、不入存档；
编辑静止时不持续刷新（只有一次短脉冲）。T03/T04 的删除/替换/条件纹样
仍属后续项。
"""
from __future__ import annotations

SELECT_PULSE = 0.18
MOVE_PULSE = 0.12
DENY_PULSE = 0.30
COMMIT_PULSE = 0.40


def pulse_progress(age: float, life: float) -> float:
    if life <= 0:
        return 1.0
    return max(0.0, min(1.0, float(age) / float(life)))


def selected_marker(progress: float) -> str:
    """候选词被选中时短移入：前导空格从 2 收到 0，静止时稳定为 '▶ '。"""
    indent = max(0, min(2, int(round((1.0 - pulse_progress(progress, 1.0)) * 2))))
    return " " * indent + "▶ "


def deny_shift(progress: float) -> int:
    """拒绝/校验失败：左—右—回中，短促一次，不循环。"""
    if progress <= 0.0 or progress >= 1.0:
        return 0
    if progress < 0.34:
        return -1
    if progress < 0.67:
        return 1
    return 0


def pulse_title_style(base: str, kind: str, progress: float) -> str:
    if kind == "deny":
        return "bold #ff9f6b"
    if kind == "commit":
        return "bold #9dff8f"
    return base


def pulse_risk_style(base: str, kind: str, progress: float) -> str:
    if kind in ("deny", "risk") and pulse_progress(progress, 1.0) < 1.0:
        return "bold #ff5c62"
    return base

PREVIEW_PULSE = 0.35

_DEGREE_WORDS = frozenset({"negate", "only", "also", "again"})


def word_kind(word_id: str) -> str:
    if word_id == "delete":
        return "delete"
    if word_id in _DEGREE_WORDS:
        return "degree"
    return "replace"


def preview_pulse_kind(word_id: str, available: bool) -> str:
    if not available:
        return "deny"
    return {"delete": "delete", "degree": "degree"}.get(word_kind(word_id), "replace")


def preview_result_line(kind: str, old_label: str, after_text: str, progress: float) -> str:
    """T03：删除为抽离留痕、替换为重组、程度词显示密度而不改范围。"""
    p = pulse_progress(progress, 1.0)
    if kind == "delete":
        if p < 0.5:
            return "→ " + after_text + "  -" + old_label
        return "→ " + after_text + "  ."
    if kind == "degree":
        marks = {"negate": 1, "only": 2, "also": 3, "again": 4}.get(old_label, 1)
        return "→ " + after_text
    if p < 0.5:
        return "→ " + after_text + "  (" + old_label + ")"
    return "→ " + after_text


def preview_result_style(base: str, kind: str, progress: float) -> str:
    if kind == "delete":
        return "dim " + base
    if kind == "degree":
        return "bold " + base
    return base


def condition_marker(available: bool, progress: float) -> str:
    """T04：条件通过/不通过的一次短标记（不新增延迟、不伪造图标）。"""
    if pulse_progress(progress, 1.0) >= 1.0:
        return ""
    return " [v]" if available else " [x]"
