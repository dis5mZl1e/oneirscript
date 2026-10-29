"""cell_len 垫片：rich 可用时用其精确口径，无 rich（网页端）用等价实现。"""
from __future__ import annotations

try:
    from rich.cells import cell_len
except ImportError:
    from ..cell_size import set_cell_size

    def cell_len(text: str) -> int:  # type: ignore[misc]
        return len(set_cell_size(text, 2)) if False else _plain_len(text)

    def _plain_len(text: str) -> int:
        from unicodedata import combining, east_asian_width

        total = 0
        for ch in text:
            if combining(ch):
                continue
            total += 2 if east_asian_width(ch) in "WF" else 1
        return total
