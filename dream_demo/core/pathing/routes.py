"""玩家寻路（部分信息口径）：8 向 A* 的封装入口。

``path_to`` 从视野子系统（core/vision/sight.py）迁来，归入 pathing 包——
玩家点击寻路与异象追击共用同一条 A* 核心（:mod:`.astar`）。与旧实现相比
新增 ``known_cells``：玩家只认得「看得见的格子」上的生物，视野外默认没有
不可见物体（生物不打探、也不挡路），真正撞上时在移动层停下（见
ui/input.py 的 _follow_path）。卷尺测量等全知用途不传该参数，保持旧口径。
"""

from __future__ import annotations

from ...materials import DOOR_KINDS
from .astar import find_path


class PathMixin:
    def path_to(
        self,
        target_x: int,
        target_y: int,
        start: tuple[int, int] | None = None,
        portents: dict[str, int] | None = None,
        known_cells: set[tuple[int, int]] | None = None,
        respect_map_knowledge: bool | None = None,
        passable_extra=None,
        step_cost=None,
        passable_override=None,
    ) -> list[tuple[int, int]]:
        """8 向 A* 寻最短路，不含起点格。

        斜向移动与 move_player 一致（均只耗 1 时长），因此点击斜向目标时
        走直达斜线而非 4 向阶梯绕路。目标格允许被实体占据（用于接近攻击），
        其余被实体占据或坚实的格子不可穿越。

        ``start`` 默认玩家所在格（玩家寻路）；异象追击时传入自己的坐标，
        与玩家共用同一套 8 向寻路，从而能绕过 U 形墙与死角。
        ``portents`` 默认玩家身上的征兆（「放大」要绕开 1 格宽缝隙）；
        异象传入自己的征兆字典。

        ``passable_extra`` 是本体能力约束（纸鱼亲液等）：与地形通行性叠加，
        连目标格也要满足；不传则保持旧口径。

        ``known_cells`` 是「移动者确认过内容的格子集合」（玩家寻路传当前
        可见集合）：实体只有站在已知格上才算障碍——视野外默认没有不可见
        物体（如生物），路径可以穿过那些格子，走过去真的撞上了再停下。
        传 None 则按全知口径（卷尺测量、异象追击的旧口径）。

        respect_map_knowledge（2026-10-18 docs 第 1 节第三批）：玩家寻路
        默认在打开三层信息开关时只走「已知地形」——当前视野/显影格用实时地形，
        记忆格用快照（记住可走就走，真实遇阻时由移动层停下），从未探索的格子
        一律不可规划；全图地形增强开启后按当前真实地形规划。传 False 可保留
        全知口径（任务资格/生成期检查等内部用途）；异象追击因显式传 start
        不进入该口径。
        """
        if not (0 <= target_x < self.width and 0 <= target_y < self.height):
            return []
        player_path = start is None
        if start is None:
            start = (self.player.x, self.player.y)
        if not (0 <= start[0] < self.width and 0 <= start[1] < self.height):
            return []
        mover_portents = self.portents if portents is None else portents
        target = (target_x, target_y)
        # 局部化热点引用：寻路会问上千次可通行性（大图上尤其明显）。
        cells = self.cells
        enlarged = "enlarged" in mover_portents
        too_narrow = self._cell_too_narrow_for_enlarged
        # 玩家寻路默认使用三层信息口径；显式 start（异象/篡改演员）与内部
        # 资格检查保持全知口径，避免迷雾改变 AI 通路或任务资格。
        fog_limit = (
            respect_map_knowledge
            if respect_map_knowledge is not None
            else player_path and bool(getattr(self, "map_memory_enabled", False))
        )
        known_visible: set[tuple[int, int]] = set()
        remembered: dict = {}
        terrain_known = False
        if fog_limit:
            known_visible = set(self.visible_cells()) | set(self.developed_for_depth())
            remembered = self.terrain_memory.get(self.layer_key()) or {}
            terrain_known = bool(getattr(self, "terrain_known", False))
            if known_cells is None:
                known_cells = known_visible
            else:
                known_cells = set(known_cells) | set(self.developed_for_depth())

        def _live_passable(x: int, y: int) -> bool:
            # 门（关闭时为实心高墙）在寻路里视作空气：玩家踩上去会自动开门并踏入
            # （见 move_player → open_adjacent），异象踩上去同样会开门
            # （见 _enemy_move_step 与 _update_doors）。否则唯一通路是门时，
            # 寻路会把它当墙、判定「不可达」而原地不动——远处点门也走不过去。
            live_cell = cells[y][x]
            if passable_override is not None:
                if not passable_override(x, y):
                    return False
            elif live_cell.solid and live_cell.wall_kind not in DOOR_KINDS:
                return False
            # 「放大」：寻路同样绕开 1 格宽缝隙与门。
            if enlarged and too_narrow(x, y):
                return False
            return True

        def passable(x: int, y: int) -> bool:
            # 能力覆盖只替换实墙资格，不能绕过体型、介质或地图知识约束。
            # 本体能力约束（如纸鱼只能沿液面）：与地形通行性叠加，目标格
            # 也必须满足，避免规划出上岸后才发现迈不出去的路线。
            if passable_extra is not None and not passable_extra(x, y):
                return False
            if fog_limit and not terrain_known and (x, y) not in known_visible:
                # 记忆格：只按最后确认的地形通行性规划；记忆过时造成的真实
                # 阻挡由移动层在撞墙时停下（不用实时地图反推）。
                snapshot = remembered.get((x, y))
                if snapshot is None:
                    return False  # 未探索区域不能规划路线
                return not (snapshot.solid and snapshot.wall_kind not in DOOR_KINDS)
            return _live_passable(x, y)

        # 障碍实体集合：玩家 + 存活异象。部分信息口径下只保留已知格上的——
        # 视野外默认无不可见物体（如生物），路径穿过那些格子不算违规。
        positions = [(self.player.x, self.player.y)]
        positions.extend((enemy.x, enemy.y) for enemy in self.enemies if enemy.integrity > 0)
        if known_cells is None:
            blocked = set(positions)
        else:
            blocked = {position for position in positions if position in known_cells}

        diagonal = not (self.realm_id == "toy_memories" and self.realm_depth == 4)
        path = find_path(self.width, self.height, start, target, passable, blocked,
                         diagonal=diagonal, step_cost=step_cost)
        from ...materials import floor_effect_for
        if start != (self.player.x, self.player.y) or not any(floor_effect_for(cells[y][x]).slide for x, y in path):
            return path

        def landing(x, y, dx, dy):
            x, y = x + dx, y + dy
            if (x, y) == target and target in blocked:
                return x, y
            while floor_effect_for(cells[y][x]).slide:
                nx, ny = x + dx, y + dy
                if (not (0 <= nx < self.width and 0 <= ny < self.height)
                        or not passable(nx, ny) or (nx, ny) in blocked
                        or not floor_effect_for(cells[ny][nx]).slide):
                    break
                x, y = nx, ny
            return x, y

        return find_path(self.width, self.height, start, target, passable, blocked,
                         diagonal=diagonal, landing=landing, step_cost=step_cost)
