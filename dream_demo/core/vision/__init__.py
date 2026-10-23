"""视野子系统：视线预算、发光延长、可见集合缓存（由 GameState 继承装配）。

``GameState`` 是 ``GenerationMixin / DoorMixin / SightMixin / PathMixin /
PortentMixin / TempoMixin / MaterialSimMixin / EnemyMixin / PlayerActionMixin``
组装出来的（见 core/state.py），视野那一块全部收在本包：

- :mod:`sight`：视线（带预算的布雷森汉姆，黑烟截断 / 灰尘云衰减）、
  :meth:`SightMixin.is_visible` / :meth:`SightMixin.visible_cells`；
- :mod:`glow`：发光地衣把「没有遮挡的方向」上的视距延长一小段
  （地形属性，与征兆无关）；
- :mod:`cache`：可见集合按「依赖签名」缓存——30fps 刷新与鼠标悬停都会请求
  它，签名不变就直接复用。

寻路不在本包：玩家寻路与异象寻路统一收在 core/pathing/（``PathMixin`` /
``PursuitMixin``），与视线共用「门恒阻视线、门可通行」的判定口径。

引用约定：核心内部一律 ``from ..vision import SightMixin`` / ``from . import glow``；
``dream_demo.core`` 仍再导出 ``SightMixin`` / ``glow`` / ``vision``，方便旧脚本
从 ``dream_demo.core.glow`` 之类的路径导入。
"""

from __future__ import annotations

from . import cache, glow
from .sight import SightMixin

__all__ = ["SightMixin", "cache", "glow"]
