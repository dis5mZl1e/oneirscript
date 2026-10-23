"""寻路子系统（core/pathing/）：玩家寻路与异象寻路共用的一套 8 向 A*。

``GameState`` 由各 Mixin 组装（见 core/state.py），寻路相关的两块收在本包：

- :mod:`astar`：通用 8 向 A*（``find_path``）——地形可通行性与障碍集合
  都由调用方注入，本模块只管搜索本身；
- :mod:`routes`：``PathMixin.path_to``——玩家点击寻路与异象追击共用的
  封装入口（门视作空气、「放大」绕窄缝），并支持 ``known_cells`` 部分
  信息口径：玩家只把「看得见的格子」上的生物当障碍，视野外默认没有
  不可见物体，撞上了才在移动层停下；
- :mod:`pursuit`：``PursuitMixin``——异象的追踪状态机（由 EnemyMixin
  继承装配）：看见玩家实时规划、丢失视野沿上次计划走、走到终点没发现
  目标就游荡、中途重新发现立即改道。

引用约定：核心内部 ``from .pathing import PathMixin, PursuitMixin``；
``dream_demo.core`` 再导出这两个 Mixin 与 ``find_path``。
"""

from __future__ import annotations

from .astar import find_path
from .pursuit import PursuitMixin
from .routes import PathMixin

__all__ = ["PathMixin", "PursuitMixin", "find_path"]
