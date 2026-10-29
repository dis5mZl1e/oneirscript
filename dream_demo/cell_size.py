"""``set_cell_size`` 垫片（网页端迁移 M0，见 docs/261024-网页端迁移方案.md）。

有 rich 时沿用其精确宽度口径（桌面版行为零变化）；无 rich 环境
（网页端 Pyodide 包不含 rich）用本地等价实现：EAW W/F 记 2 列、
组合记号记 0 列，补齐/截断到目标列数（不劈开双宽字符）。
"""
from __future__ import annotations

from unicodedata import combining, east_asian_width

try:
    from rich.cells import set_cell_size
except ImportError:
    def _cell_len(text: str) -> int:
        total = 0
        for ch in text:
            if combining(ch):
                continue
            total += 2 if east_asian_width(ch) in "WF" else 1
        return total

    def set_cell_size(text: str, size: int) -> str:  # type: ignore[misc]
        length = _cell_len(text)
        if length == size:
            return text
        if length < size:
            return text + " " * (size - length)
        out: list[str] = []
        used = 0
        for ch in text:
            if combining(ch):
                out.append(ch)
                continue
            width = 2 if east_asian_width(ch) in "WF" else 1
            if used + width > size:
                break
            out.append(ch)
            used += width
        return "".join(out) + " " * (size - used)
