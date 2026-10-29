"""逻辑固体运行时（内容扩展包 v1）：信号发射 / 电线传播 / 接收器结算 / 陷阱执行。

设计规格见《梦层内容扩展包 v1.xlsx》末四张表：
- 信号 = 离散脉冲，沿 Cell.wire 位掩码 BFS，每格强度 −1，归零即止；
- 电线可以穿墙（传播不检查通行性），导电铜网墙作放大器（+4）；
- 每格只传播一次（去重）、接收器幂等（同一信号不重复触发）；
- 信号在触发的同一回合内广播完毕，不消耗额外回合。
"""

from __future__ import annotations

from collections import deque

from ..i18n import tr
from ..materials import floor_effect_for
from ..materials.logic import (
    ALARM,
    AMPLIFIER_WALL,
    CAGE_FENCE,
    GATE_KINDS,
    LAUNCHER,
    LOGIC_DOOR,
    PENDULUM,
    REVEAL_OBELISK,
    RUNE_WALL,
    SIGNAL_MAX_STRENGTH,
    SIGNAL_STRENGTH_CAP,
    TRAP_PLATFORM,
    TRIGGER_KINDS,
    VALVE,
    WIRE_DIR,
    roll_mechanism_scenario,
)
from .entities import Cell
from .circuits import CircuitMixin
from .light_flash import note_light_flash
from .visual_events import emit_visual

# 感应符文墙的感知半径与再触发冷却（回合）；冷却存内存即可（读档清零无害）。
RUNE_SENSOR_RADIUS = 6
RUNE_SENSOR_COOLDOWN = 5
PENDULUM_INTERVAL = 10
# 意识栅栏的消散寿命数（回合）：囚笼永远有出路。
MIND_FENCE_LIFETIME = 10


class LogicMixin(CircuitMixin):
    """挂在 GameState 上：电线布设、信号传播、接收器与陷阱结算。"""

    # ---------------------------------------------------------------- 布线

    def lay_wire_path(self, path: list[tuple[int, int]]) -> None:
        """沿一条正交折线铺电线（可穿墙）：相邻两格互写方向位。"""
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            for dx, dy, bit_from, bit_to in WIRE_DIR:
                if (x2 - x1, y2 - y1) == (dx, dy):
                    self.cell(x1, y1).wire |= bit_from
                    self.cell(x2, y2).wire |= bit_to
                    break

    def wire_path_between(self, a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
        """两格间的最短正交折线（L 形：先横后纵）；电线穿墙，无需寻路。"""
        x1, y1 = a
        x2, y2 = b
        path = [(x1, y1)]
        step_x = (x2 > x1) - (x2 < x1)
        while x1 != x2:
            x1 += step_x
            path.append((x1, y1))
        step_y = (y2 > y1) - (y2 < y1)
        while y1 != y2:
            y1 += step_y
            path.append((x1, y1))
        return path

    def link_logic_nodes(self, positions: list[tuple[int, int]]) -> None:
        """把一组逻辑节点链成一张网络：按给出顺序首尾相连（vault 布线）。"""
        for a, b in zip(positions, positions[1:]):
            self.lay_wire_path(self.wire_path_between(a, b))

    # ---------------------------------------------------------------- 信号

    def emit_signal(self, x: int, y: int, strength: int = SIGNAL_STRENGTH_CAP,
                    source: str = "") -> int:
        """从 (x, y) 发射信号：沿电线 BFS，返回触发了几台接收器。

        视觉事件只记录这次 BFS 真实走过的父边、真实到达的接收器与真实接收
        结果：paths 按父边顺序给出去到每个分支末端的路径，分支保持为多条
        path；_logic_energized 是稳态显示集合，不当作路径、也不每帧重播。
        强度归零的末端接收器仍按原规则响应（「刚好够到」也算数）。
        """
        strength = min(strength, SIGNAL_STRENGTH_CAP)
        if self.circuit_node_at(x, y) is not None:
            self._circuit_signal(x, y, by_player=source == 'player')
            return 0
        receivers = ("机关门", "显影方尖", "囚笼栅栏", "弹射座", "灌注阀", "共鸣报警器")
        # (坐标, 剩余强度)；visited 去重保证有界、接收器幂等。
        queue: deque[tuple[int, int, int]] = deque([(x, y, strength)])
        visited: set[tuple[int, int]] = {(x, y)}
        visit_order: list[tuple[int, int]] = [(x, y)]
        parent: dict[tuple[int, int], tuple[int, int] | None] = {(x, y): None}
        depth: dict[tuple[int, int], int] = {(x, y): 0}
        fired = 0
        seen_receivers: set[tuple[int, int]] = set()
        receiver_results: list[tuple[tuple[int, int], int, str, tuple[tuple[int, int], ...]]] = []
        self._logic_energized.add((x, y))
        while queue:
            cx, cy, power = queue.popleft()
            cell = self.cell(cx, cy)
            # 到达接收器：同一信号只结算一次（强度归零的末端接收器仍响应——
            # 「刚好够到」也算数，这是布线距离的判断标准）。
            if cell.wall_kind in receivers and (cx, cy) not in seen_receivers:
                seen_receivers.add((cx, cy))
                resolved, affected = self._receiver_result(cx, cy, source_x=x, source_y=y)
                if resolved:
                    fired += 1
                    receiver_results.append(((cx, cy), power, cell.wall_kind, affected))
                    if source == 'player' and not (cell.wall_kind == '机关门' and cell.solid):
                        self._identity_receiver(cx, cy)
            # 门类节点（合辙/分流）：只登记本回合的一次输入，不继续传播——
            # 门在相位二（回合末 evaluate_gates）统一裁决后重新发射。
            if cell.wall_kind in GATE_KINDS and (cx, cy) != (x, y):
                # 门自身作为发射原点时（相位二的门转发）跳过登记——
                # 否则门会把自己的输出当成输入、永远走不出第一步。
                self.gate_inputs.setdefault((cx, cy), set()).add((x, y))
                if source == 'player':
                    self._identity_note_gate_source((cx, cy), (x, y))
                continue
            if power <= 0:
                continue
            for dx, dy, bit_from, bit_to in WIRE_DIR:
                if not (cell.wire & bit_from):
                    continue
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if not self.cell(nx, ny).wire & bit_to:
                    continue
                if self.circuit_node_at(nx, ny) is not None:
                    continue  # named boards cannot be shorted by a legacy pulse
                if (nx, ny) in visited:
                    continue
                visited.add((nx, ny))
                visit_order.append((nx, ny))
                parent[(nx, ny)] = (cx, cy)
                depth[(nx, ny)] = depth[(cx, cy)] + 1
                self._logic_energized.add((nx, ny))
                next_power = power - 1
                if self.cell(nx, ny).wall_kind == AMPLIFIER_WALL:
                    next_power = min(SIGNAL_MAX_STRENGTH, next_power + 4)
                next_kind = self.cell(nx, ny).wall_kind
                if next_power > 0 or next_kind in receivers or next_kind in GATE_KINDS:
                    # 强度归零也要把「刚好够到」的门/接收器入队——
                    # 到达本身就是输入（门的裁决、接收器的幂等结算都在弹出处）。
                    queue.append((nx, ny, next_power))
        self._emit_legacy_signal_events(x, y, source, strength, visit_order,
                                        parent, depth, receiver_results)
        return fired

    @staticmethod
    def _legacy_parent_path(parent, point: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        path = [point]
        while parent.get(path[-1]) is not None:
            path.append(parent[path[-1]])
        path.reverse()
        return tuple(path)

    def _legacy_branch_paths(self, parent, visit_order) -> tuple[tuple[tuple[int, int], ...], ...]:
        """按真实父边重建 BFS 树的分支路径：每个末端一条，分支不合并。"""
        children: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for point, par in parent.items():
            if par is not None:
                children.setdefault(par, []).append(point)
        paths = []
        for point in visit_order:
            if point in children:
                continue
            paths.append(self._legacy_parent_path(parent, point))
        return tuple(paths)

    def _emit_legacy_signal_events(self, x, y, source, strength, visit_order,
                                   parent, depth, receiver_results) -> None:
        """只登记本次 BFS 真实发生的传播与接收；空 BFS / 只读读取不发事件。"""
        root = self._circuit_visual_root(f"legacy:{x},{y}")
        travel = None
        if len(visit_order) > 1:
            paths = self._legacy_branch_paths(parent, visit_order)
            travel = emit_visual(
                self, kind="circuit.travel", outcome="on", source=(x, y),
                targets=tuple(point for point, _power, _kind, _cells in receiver_results),
                paths=paths, affected_cells=tuple(visit_order),
                visual_key="circuit.arc", tier=1, theme="electric",
                root_id=root, source_id=f"legacy:{x},{y}", layer_key="circuit",
                facts=(("origin", str(source or "")), ("signal_strength", int(strength)),
                       ("visited", len(visit_order)), ("branches", len(paths)),
                       ("fired", len(receiver_results))),
            )
        for (rx, ry), power, wall_kind, affected in receiver_results:
            path = self._legacy_parent_path(parent, (rx, ry))
            emit_visual(
                self, kind="circuit.receiver", outcome="fired", source=(rx, ry),
                targets=((rx, ry),),
                paths=(path,) if len(path) > 1 else (),
                affected_cells=tuple(affected),
                visual_key="circuit.arc", tier=1, theme="electric",
                root_id=travel.root_id if travel is not None else root,
                parent_id=travel.event_id if travel is not None else None,
                source_id=f"legacy-receiver:{rx},{ry}", layer_key="circuit",
                facts=(("origin", str(source or "")), ("receiver", str(wall_kind)),
                       ("power", int(power)), ("depth", int(depth.get((rx, ry), 0)))),
            )

    def _logic_fences(self) -> dict[tuple[int, int], int]:
        """在场的意识栅栏及其剩余寿命（囚笼栅栏降下 / 到期消散用）。"""
        return getattr(self, "_mind_fences", {})

    def _restore_logic_fences(self, raw: dict) -> None:
        self._mind_fences = {tuple(map(int, key.split(","))): int(value) for key,value in raw.items() if int(value)>0}
        # Old saves stored the fence tiles but lost their countdown.
        for y,row in enumerate(self.cells):
            for x,cell in enumerate(row):
                if cell.wall_kind == "意识栅栏":
                    self._mind_fences.setdefault((x,y), MIND_FENCE_LIFETIME)

    def _resolve_receiver(self, x: int, y: int, source_x: int, source_y: int) -> bool:
        """接收器动作：返回是否有可见反馈（供消息聚合）。"""
        resolved, _affected = self._receiver_result(x, y, source_x, source_y)
        return resolved

    def _receiver_result(self, x: int, y: int, source_x: int, source_y: int):
        """执行接收器动作，返回 (是否有可见反馈, 本次实际改变格)。"""
        kind = self.cell(x, y).wall_kind
        if kind == "机关门":
            # 开/关切换：开 = 通行（solid 置 False），关 = 恢复坚实。
            cell = self.cell(x, y)
            before = cell.solid
            cell.solid = not cell.solid
            self.messages.append(tr(
                "机关门转动齿轮，{state}。", state="打开" if not cell.solid else "关上"
            ))
            return True, (() if cell.solid == before else ((x, y),))
        if kind == "显影方尖":
            # 一次性：点亮后永久显影半径 3。
            self._develop_terrain_radius(x, y, 3)
            # §12 D 残余：点亮的一次短光。**只播这一下**——「永久显影」是地图
            # 知识（developed_cells），不能顺手把它变成一盏常亮灯（§4.3 末行）。
            note_light_flash(self, "develop", x, y)
            self.messages.append(tr("显影方尖亮起——周围的地形从黑暗里显形。"))
            return True, ((x, y),)
        if kind == "囚笼栅栏":
            return True, tuple(self._toggle_cage(x, y))
        if kind == "弹射座":
            return True, tuple(self._fire_launcher(x, y, source_x, source_y))
        if kind == "灌注阀":
            return True, tuple(self._open_valve(x, y))
        if kind == "共鸣报警器":
            # 全图可闻：所有失控意识被召集到报警器位置。这是独立的召集／
            # 信息机制，不按普通听觉上限 H 削减（docs 261022 §13.1）。
            for enemy in self.enemies:
                if enemy.integrity > 0 and enemy.relation == "失控意识":
                    enemy.alert_state = "追踪"
                    enemy.last_seen_x, enemy.last_seen_y = x, y
                    enemy.wandering = False
                    self._plan_chase(enemy, x, y)
            # 另发一次 R=10 物理鸣声，供玩家与普通听觉线索使用；异象不再被
            # 这条声路重复规划（召集循环已经各规划一次）。
            self._sound_pulse(x, y, 10, category="alarm", source=tr("共鸣报警器"),
                              announce=False, affect_enemies=False)
            self.messages.append(tr("共鸣报警器发出刺耳的长鸣——整层的梦都被惊动了。"))
            return True, ((x, y),)
        return False, ()

    # ---------------------------------------------------------- 接收器动作

    def _toggle_cage(self, x: int, y: int) -> tuple[tuple[int, int], ...]:
        """囚笼栅栏升降：8 邻格中「可站立的开放格」升起/清掉意识栅栏。"""
        fences = self._logic_fences()
        raised_any = False
        changed: list[tuple[int, int]] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                cell = self.cell(nx, ny)
                if cell.wall_kind == "意识栅栏":
                    # 降下：清栅栏。
                    cell.wall_kind = ""
                    cell.solid = False
                    fences.pop((nx, ny), None)
                    changed.append((nx, ny))
                    continue
                if cell.solid or self.entity_at(nx, ny):
                    continue
                # 升起：意识栅栏（可徒手破坏 + 10 回合消散——被关永远有出路）。
                cell.wall_kind = "意识栅栏"
                cell.solid = True
                fences[(nx, ny)] = MIND_FENCE_LIFETIME
                changed.append((nx, ny))
                raised_any = True
        self._mind_fences = fences
        if raised_any:
            self.messages.append(tr("囚笼栅栏升起——四周竖起了半透明的栅影。"))
        else:
            self.messages.append(tr("囚笼栅栏降下——栅影散去。"))
        return tuple(changed)

    def _fire_launcher(self, x: int, y: int, source_x: int, source_y: int) -> tuple[tuple[int, int], ...]:
        """弹射座：把格上/相邻的生物沿「远离信号源」的方向推出最多 3 格。"""
        # 朝向 = 从信号源指向弹射座的单位方向（默认向上）。
        dx, dy = x - source_x, y - source_y
        if abs(dx) >= abs(dy):
            dx, dy = (dx > 0) - (dx < 0), 0
        else:
            dx, dy = 0, (dy > 0) - (dy < 0)
        if dx == 0 and dy == 0:
            dx, dy = 0, -1
        moved_any = False
        moved_cells: list[tuple[int, int]] = []
        for entity in [self.player, *self.enemies]:
            if entity.integrity <= 0:
                continue
            if max(abs(entity.x - x), abs(entity.y - y)) > 1:
                continue
            px, py = entity.x, entity.y
            started = (px, py)
            entity_moved = False
            for _ in range(3):
                nx, ny = px + dx, py + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    break
                cell = self.cell(nx, ny)
                if cell.solid or (other := self.entity_at(nx, ny)) is not None and other is not entity:
                    break
                px, py = nx, ny
                moved_any = True
                entity_moved = True
            entity.x, entity.y = px, py
            if entity_moved:
                for point in (started, (px, py)):
                    if point not in moved_cells:
                        moved_cells.append(point)
        if moved_any:
            self.messages.append(tr("弹射座松开簧片——一股力量把人推了出去。"))
        return tuple(moved_cells)

    def _open_valve(self, x: int, y: int) -> tuple[tuple[int, int], ...]:
        """灌注阀：向 4 邻开放格释放储备材料（vault 可指定，默认水）。"""
        kind, amount = "水", 24
        stored = getattr(self, "valve_stored", {}).get(f"{x},{y}")
        if stored:
            kind, amount = stored
        poured = 0
        poured_cells: list[tuple[int, int]] = []
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            cell = self.cell(nx, ny)
            if cell.solid:
                continue
            if kind in LIQUIDS:
                self._add_liquid(cell, kind, amount)
            elif kind in GASES:
                self._add_gas(cell, kind, amount)
            poured += 1
            poured_cells.append((nx, ny))
        if poured:
            self.messages.append(tr("灌注阀开启——{material}涌了出来。", material=tr(kind)))
        return tuple(poured_cells)

    # ---------------------------------------------------------------- 陷阱

    def trigger_platform(self, x: int, y: int, *, safe_note: str = "") -> None:
        """台面被取物/回应：陷阱石台执行随机选定的场景并发射信号；
        机关石台执行良性场景并发射信号（自动门/显影等）。

        ``safe_note`` 是第二条「隔开机关」的通路（第一条是绝缘手套）：只抑制
        **陷阱**那一段场景，石台的信号照发、机关石台照旧执行——洞察「桌面不是
        地面」靠多站一回合换来这一手，所以这里的口径必须与手套一致。
        """
        kind = self.cell(x, y).wall_kind
        if self.circuit_node_at(x, y) is not None:
            self._circuit_signal(x, y, by_player=True)
            return
        safe = bool(safe_note) or self._effect_power("wire_safe") > 0
        if kind == TRAP_PLATFORM and safe:
            # 绝缘手套／多站那一回合：徒手取物隔开了机关——陷阱不触发（石台仍发信号）。
            self.messages.append(safe_note or tr("绝缘手套隔开了机关——你安全地绕过了陷阱。"))
        elif kind == TRAP_PLATFORM:
            from ..materials.logic import TRAP_SCENARIO_LIBRARY

            name = self.trap_scenarios.get(f"{x},{y}")
            scenario = TRAP_SCENARIO_LIBRARY.get(name or "", TRAP_SCENARIO_LIBRARY["dud"])
            self._execute_scenario(x, y, scenario, label=tr("陷阱石台"))
        elif kind == "机关石台":
            scenario = roll_mechanism_scenario(self.seed, self.depth, x, y)
            self._execute_scenario(x, y, scenario, label=tr("机关石台"))
        if self.cell(x, y).wire:
            self.emit_signal(x, y, source='player')

    def _execute_scenario(self, x: int, y: int, scenario: dict, label: str = "") -> None:
        kind = scenario.get("type")
        if kind == "dud":
            self.messages.append(tr(scenario.get("message", "咔哒一声——什么也没有发生。")))
            return
        if kind == "summon":
            import random

            rng = random.Random(self.seed ^ (self.time * 31) ^ (x * 7 + y * 13))
            count, radius = int(scenario.get("count", 2)), int(scenario.get("radius", 4))
            placed = 0
            pool_ids = scenario.get("pool")
            if pool_ids is not None and not self.realm_id:
                from .content import ANOMALY_DEFINITIONS
                pool_ids = tuple(key for key in pool_ids
                                 if key in ANOMALY_DEFINITIONS
                                 and ANOMALY_DEFINITIONS[key].get('pool', True)
                                 and not ANOMALY_DEFINITIONS[key].get('spawn_realms')
                                 and not ANOMALY_DEFINITIONS[key].get('spawn_only')
                                 and self.depth >= ANOMALY_DEFINITIONS[key]['layers'][0])
            candidates = [
                (cx, cy)
                for cy in range(max(1, y - radius), min(self.height - 1, y + radius + 1))
                for cx in range(max(1, x - radius), min(self.width - 1, x + radius + 1))
                if not self.cell(cx, cy).solid and self.entity_at(cx, cy) is None
            ]
            rng.shuffle(candidates)
            for cx, cy in candidates:
                if placed >= count:
                    break
                if pool_ids is not None:
                    if not pool_ids:
                        break
                    pool_id = pool_ids[rng.randrange(len(pool_ids))]
                else:
                    pool_id = self._random_region_anomaly(cx, cy, rng)
                if not pool_id:
                    continue
                enemy = self.add_defined_enemy(pool_id, cx, cy)
                enemy.alert_state = "追踪"
                enemy.last_seen_x, enemy.last_seen_y = x, y
                placed += 1
            if placed:
                self.messages.append(tr("石台下的机关咬合——{n} 个失控意识被召唤出来！", n=placed))
            else:
                self.messages.append(tr("石台震了震，但没有东西被召唤出来。"))
            return
        if kind == "cage":
            # 以玩家为中心升起意识栅栏（可破坏 + 10 回合消散：永远有出路）。
            fences = self._logic_fences()
            px, py = self.player.x, self.player.y
            raised = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = px + dx, py + dy
                    if not (0 <= nx < self.width and 0 <= ny < self.height):
                        continue
                    cell = self.cell(nx, ny)
                    if cell.solid or self.entity_at(nx, ny):
                        continue
                    cell.wall_kind = "意识栅栏"
                    cell.solid = True
                    fences[(nx, ny)] = MIND_FENCE_LIFETIME
                    raised += 1
            self._mind_fences = fences
            if raised:
                self.messages.append(tr("石台四周弹起栅栏，把你困在中间——栅影看起来撑不了多久。"))
            return
        if kind == "gas":
            gas, amount = scenario["gas"], int(scenario.get("amount", 24))
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cell = self.cell(min(self.width - 1, max(0, x + dx)), min(self.height - 1, max(0, y + dy)))
                if not cell.solid:
                    self._add_gas(cell, gas, amount)
            self.messages.append(tr("石台缝隙里涌出一团{gas}！", gas=tr(gas)))
            return
        if kind == "projectile":
            # 弹药伏击：从石台向玩家直射（直线、撞墙即止）。
            damage = int(scenario.get("damage", 3))
            px, py = self.player.x, self.player.y
            if (px, py) == (x, y):
                return  # a zero-direction ray cannot advance
            dx = (px > x) - (px < x)
            dy = (py > y) - (py < y)
            if dx and dy:
                dy = 0  # 斜向取水平分量（直线弹道）
            cx, cy = x + dx, y + dy
            hit = False
            while 0 <= cx < self.width and 0 <= cy < self.height:
                if self.cell(cx, cy).solid:
                    break
                if (cx, cy) == (px, py):
                    hit = True
                    break
                cx += dx
                cy += dy
            if hit:
                self._lose_mind(damage)
                self.messages.append(tr("石台弹出一枚弩箭，正中你：心智 −{d}。", d=damage))
            else:
                self.messages.append(tr("石台弹出一枚弩箭，擦着空气飞走了。"))
            return
        if kind == "portent":
            self._grant_portent_direct(self.player, scenario["portent"])
            self.messages.append(tr("石台上的符文亮起——一股阴冷的战栗爬上脊背。"))
            return
        if kind == "terrain":
            radius = int(scenario.get("radius", 2))
            chance = float(scenario.get("chance", 0.5))
            import random

            rng = random.Random(self.seed ^ (x * 13 + y * 7) ^ self.time)
            hardened = 0
            for cy in range(max(1, y - radius), min(self.height - 1, y + radius + 1)):
                for cx in range(max(1, x - radius), min(self.width - 1, x + radius + 1)):
                    cell = self.cell(cx, cy)
                    if not cell.solid and cell.wall_kind == "" and self.entity_at(cx, cy) is None and rng.random() < chance:
                        cell.solid = True
                        cell.wall_kind = "坚实聚合物"
                        cell.hardness = 3
                        hardened += 1
            if hardened:
                self.messages.append(tr("地面隆起凝硬——退路被堵住了几格。"))
            return
        if kind == "reveal":
            self._develop_terrain_radius(x, y, int(scenario.get("radius", 3)))
            self.messages.append(tr("{label}亮了一下，周围的地形显形了。", label=label))
            return
        if kind == "imagination":
            amount = int(scenario.get("amount", 6))
            self.restore_resource('imagination', amount)
            self.messages.append(tr("{label}里流出温热的念头：想象力 +{n}。", label=label, n=amount))
            return
        self.messages.append(tr("咔哒一声——什么也没有发生。"))

    def _random_region_anomaly(self, x: int, y: int, rng) -> str | None:
        """Main random summons obey depth limits; empty pools do not bypass them."""
        from .content import ANOMALY_DEFINITIONS, ORDINARY_ANOMALY_IDS, anomaly_pool_for_depth
        if self.realm_id:
            # Preserve the existing generic realm mechanism, independently of
            # main-depth changes; explicitly authored realm pools are handled above.
            return ORDINARY_ANOMALY_IDS[rng.randrange(len(ORDINARY_ANOMALY_IDS))] if ORDINARY_ANOMALY_IDS else None
        if self.depth >= 28:
            from ..mapgen.epilogue import EPILOGUE_ANOMALY_POOL
            pool = tuple((key, 1.0) for key in EPILOGUE_ANOMALY_POOL
                         if ANOMALY_DEFINITIONS[key]['anomaly_kind'] == '普通异象')
        else:
            pool = anomaly_pool_for_depth(self.depth)
        if not pool:
            return None
        return rng.choices([key for key, _ in pool], weights=[weight for _, weight in pool], k=1)[0]

    # ------------------------------------------------------------ 周期触发

    def seed_natural_circuits(self, depth: int, protected: list | None = None) -> None:
        """Compatibility hook; scoped templates now own all circuit placement.

        No natural components are seeded. Existing saved boards are retained.
        """
        return

    def _tick_conveyors(self, pre_positions: dict) -> None:
        """传送带：本回合没有移动的生物沿传送带方向推行一格（撞墙/有实体则留）。

        推行不耗时间（是地板在动，不是生物在走）；玩家/异象/稳定意识一视同仁。
        """
        for entity in [self.player, *self.enemies]:
            if entity is self.player and getattr(self, '_conveyor_player_walking', False):
                continue
            if entity.integrity <= 0:
                continue
            pos = (entity.x, entity.y)
            if pre_positions.get(id(entity)) != pos:
                continue  # 本回合移动过：传送带不推
            belt = floor_effect_for(self.cell(*pos)).conveyor
            if not belt:
                continue
            nx, ny = pos[0] + belt[0], pos[1] + belt[1]
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            target = self.cell(nx, ny)
            if target.solid or self.entity_at(nx, ny) is not None:
                continue
            entity.x, entity.y = nx, ny

    def evaluate_gates(self) -> None:
        """相位二：逐个评估本回合登记过输入的门类节点。

        - 合辙枢：≥2 个不同来源 → 满强度转发；
        - 分流枢：任意输入 → 满强度转发；
        - 评估期发射的门输入计入**下一轮**聚合（门→门链允许，同回合只评一轮）。
        """
        if getattr(self, "_gate_evaluating", False):
            return
        pending = self.gate_inputs
        pending_causes = self.identity_state.pop('gate_sources', {})
        self.gate_inputs = {}
        self._gate_evaluating = True
        try:
            for (x, y), sources in pending.items():
                kind = self.cell(x, y).wall_kind
                threshold = 2 if kind == "合辙枢" else 1
                if len(sources) >= threshold:
                    key = f'{self._identity_layer_key()}:{x},{y}'
                    player_caused = any(list(origin) in pending_causes.get(key, []) for origin in sources)
                    self.emit_signal(x, y, source='player' if player_caused else 'gate')
        finally:
            self._gate_evaluating = False

    _METAL_WALLS = ("铅板", "沉思铁幕", "导电铜网墙")

    def _tick_magnetized(self) -> None:
        """磁化液态记忆：站在其中每回合被拉向最近的金属墙 1 格（若可通行）。"""
        cell = self.cell(self.player.x, self.player.y)
        if cell.liquid_kind != "磁化液态记忆" or cell.liquid <= 0:
            return
        best, best_d = None, 10 ** 9
        for y in range(self.height):
            for x in range(self.width):
                c = self.cell(x, y)
                if c.solid and c.wall_kind in self._METAL_WALLS:
                    dist = max(abs(x - self.player.x), abs(y - self.player.y))
                    if dist < best_d:
                        best, best_d = (x, y), dist
        if best is None or best_d <= 1:
            return
        dx = (best[0] > self.player.x) - (best[0] < self.player.x)
        dy = (best[1] > self.player.y) - (best[1] < self.player.y)
        nx = self.player.x + dx
        ny = self.player.y + dy
        if (0 <= nx < self.width and 0 <= ny < self.height
                and not self.cell(nx, ny).solid and self.entity_at(nx, ny) is None):
            self.player.x, self.player.y = nx, ny
            self.messages.append(tr("磁力拖拽着你滑向金属。"))

    def _check_toy_sokoban(self) -> bool:
        """第 4 层推箱子：所有理念立方体都在石台上 → 解谜达成。"""
        cubes = []
        targets = set(getattr(self, "_toy_targets", []))
        for y in range(self.height):
            for x in range(self.width):
                if self.cell(x, y).wall_kind == "理念立方体":
                    cubes.append((x, y))
        if not cubes or not targets:
            return False
        return len(cubes) == len(targets) and set(cubes) == targets

    def _check_realm_puzzle(self) -> None:
        """玩具的回忆解谜检测（每回合一次）。"""
        if self.realm_id != "toy_memories" or self.realm_puzzle_solved.get(self.realm_depth):
            return
        depth = self.realm_depth
        if self.circuit_boards:
            return  # board completion is based on its actual output
        if depth == 4 and self._check_toy_sokoban():
            self._mark_toy_solved()
            return
        if depth == 1:
            # L1：三块机关石台全部触发
            lit = getattr(self, "_toy_lit", set())
            if len(lit) >= 3:
                self._mark_toy_solved()
        elif depth == 3:
            # L3：三块压力地板按序踩
            progress = getattr(self, "_toy_plate_progress", [])
            order = getattr(self, "_toy_plate_order", [])
            if order and progress == order:
                self._mark_toy_solved()

    def _tick_pack_walls(self, amount: int) -> None:
        """倦怠棉垛贴近：每 3 回合想象力 -1（玩家 4 邻有棉垛时）。"""
        px, py = self.player.x, self.player.y
        near = any(
            self.cell(px + dx, py + dy).wall_kind == "倦怠棉垛"
            for dx in (-1, 0, 1) for dy in (-1, 0, 1)
        )
        if not near:
            return
        self._cotton_tick = getattr(self, "_cotton_tick", 0) + amount
        if self._cotton_tick >= 3:
            self._cotton_tick = 0
            from .settlement import REASON_ENVIRONMENT, settle_delta
            settle_delta(self, 'imagination', -1,
                         reason=REASON_ENVIRONMENT, source='倦怠棉垛')
            self.messages.append(tr("棉絮吸走了你的念头（想象力 -1）。"))

    def _pressure_step(self, origin: tuple[int, int], landing: tuple[int, int], *, by_player: bool = False) -> None:
        """压力地板：任意生物踏上/离开各发一次信号（强度 2）。"""
        for tile in (origin, landing):
            x, y = tile
            cell = self.cell(x, y)
            hit = self.circuit_node_at(x, y)
            if hit is not None:
                if tile == landing and origin != landing and hit[2]["op"] == "step":
                    self._circuit_signal(x, y, by_player=by_player)
                elif hit[2]['op'] in {'plate', 'cube'} and by_player:
                    self._settle_circuit(hit[0], player_inputs={hit[1]})
                continue
            if cell.aggregate_variant != "压力地板":
                continue
            # 电线未接入的地板只发出「咔哒」声——玩家无法确定它是否连着机关。
            if cell.wire:
                self.emit_signal(x, y, strength=2, source='player' if by_player else '')

    def _tick_logic_triggers(self) -> None:
        """每回合一次：定时摆轮发信号、感应符文墙感知、意识栅栏到期消散。"""
        if self.time % PENDULUM_INTERVAL == 0:
            for y in range(self.height):
                for x in range(self.width):
                    if (self.cell(x, y).wall_kind == PENDULUM and self.cell(x, y).wire
                            and self.circuit_node_at(x, y) is None):
                        self.emit_signal(x, y, source="pendulum")
        # 符文墙：感知半径内出现失控意识就发信号（冷却内不重复）。
        cooldowns = getattr(self, "_rune_cooldowns", {})
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cell(x, y)
                if cell.wall_kind != RUNE_WALL or not cell.wire:
                    continue
                if self.circuit_node_at(x, y) is not None:
                    continue
                key = (x, y)
                if cooldowns.get(key, -999) + RUNE_SENSOR_COOLDOWN > self.time:
                    continue
                for enemy in self.enemies:
                    if (enemy.integrity > 0 and enemy.relation == "失控意识"
                            and max(abs(enemy.x - x), abs(enemy.y - y)) <= RUNE_SENSOR_RADIUS):
                        cooldowns[key] = self.time
                        self.emit_signal(x, y, source="rune")
                        # §12 D 残余：感知到才有的短光——没感知时这面符文墙
                        # 和普通墙一样黑，冷却内也不会再亮（§4.3 末行）。
                        note_light_flash(self, "rune", x, y)
                        break
        self._rune_cooldowns = cooldowns
        # 意识栅栏到期消散。
        fences = self._logic_fences()
        if fences:
            expired = [pos for pos, life in fences.items() if life - 1 <= 0]
            for (x, y) in expired:
                cell = self.cell(x, y)
                if cell.wall_kind == "意识栅栏":
                    cell.wall_kind = ""
                    cell.solid = False
                fences.pop((x, y), None)
            for pos in fences:
                fences[pos] -= 1


# 灌注阀默认材料查询用（避免循环导入放到函数外引用）：
from ..materials import GAS_DEFINITIONS as GASES  # noqa: E402
from ..materials import LIQUID_DEFINITIONS as LIQUIDS  # noqa: E402
