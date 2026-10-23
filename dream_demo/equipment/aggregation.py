"""同效果递减汇总（§7.1）。

对同一效果 id 的有效来源，先按原贡献值降序、再按实例 id 稳定排序，
权重 1, 0.5, 0.25, 0.125…；汇总完再做整数四舍五入，禁止逐件向上取整。
护甲与崩解收益通道使用 1, 0.25, 0.0625…，保留首件效力，约束重复来源。
共鸣在递减汇总后应用一次（同样四舍五入）。
四舍五入（2026-10-22 平衡修复）：旧实现 int() 截断把 1.75 压成 1，
使第二件在 .25 通道几乎恒为 +0；改为四舍五入后，贡献 ≥0.5 的零头不再被吞掉。
"""

from __future__ import annotations

from typing import Iterable, Sequence

WEIGHTS = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125)
EFFECT_DECAY = {'mind_armor': .25, 'lucidity_armor': .25, 'dual_armor': .25, 'coin_bonus': .25}


def weight(rank: int) -> float:
    if rank < len(WEIGHTS):
        return WEIGHTS[rank]
    return WEIGHTS[-1] / (2 ** (rank - len(WEIGHTS) + 1))


def diminish(contributions: Iterable[tuple[int, str]], *, ratio: float = .5) -> float:
    """[(原贡献值, 实例 id)] → 递减后的总贡献（未取整）。"""
    ordered = sorted(contributions, key=lambda entry: (-entry[0], entry[1]))
    return sum(value * ratio ** rank for rank, (value, _) in enumerate(ordered))


def diminish_int(contributions: Iterable[tuple[int, str]], resonating: bool = False, *, ratio: float = .5) -> int:
    # 2026-10-22 平衡修复：由 int() 截断改为四舍五入（int(x + 0.5)），
    # 免得 "第二件贡献 <1 就归零"；仅在汇总后取整一次，不逐件取整。
    total = int(diminish(contributions, ratio=ratio) + 0.5)
    if resonating:
        total = int(total * 1.5 + 0.5)
    return total


def diminishing_loss(contributions: Sequence[tuple[int, str]], *, ratio: float = .5) -> float:
    """预览用：相对逐件相加损失了多少（用于「第二件贡献不足 1」的提示）。"""
    raw = sum(value for value, _ in contributions)
    return raw - diminish(contributions, ratio=ratio)
