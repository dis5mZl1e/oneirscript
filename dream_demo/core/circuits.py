"""Directed, named circuit nets. Board signals are levels, legacy wires are pulses.

Each net owns its trace: crossing traces are insulated, never implicit junctions.
Combinational gates settle in topological order in one objective turn. Only
explicit switches, sequencers and latched outputs retain state across turns.
"""
from __future__ import annotations

from copy import deepcopy

from ..i18n import tr
from .entities import ActionResult

from ..circuit_schema import INPUTS, validate_board


class CircuitMixin:
    def install_circuit_board(self, definition: dict) -> dict:
        board = deepcopy(definition)
        board["order"] = validate_board(board, self.width, self.height)
        board.setdefault("state", {})
        self.circuit_boards.append(board)
        for net in board["nets"]:
            self.lay_wire_path([tuple(p) for p in net["path"]])
        return board

    def circuit_node_at(self, x: int, y: int):
        for board in self.circuit_boards:
            for key, node in board["nodes"].items():
                if node["pos"] == [x, y]:
                    return board, key, node
        return None

    def _circuit_signal(self, x: int, y: int, *, by_player: bool = False) -> bool:
        hit = self.circuit_node_at(x, y)
        if hit is None:
            return False
        board, key, node = hit
        runtime = board["state"]
        if node["op"] == "toggle":
            switches = runtime.setdefault("switches", {})
            switches[key] = not switches.get(key, node.get("initial", False))
            self.messages.append(tr("{label}：{state}。", label=tr(node["label"]),
                                    state=tr("通电" if switches[key] else "断电")))
        elif node["op"] in {"pulse", "step"}:
            if node["op"] == "pulse":
                runtime.setdefault("pulses", {})[key] = self.time + 1
            self._circuit_sequence_event(board, key)
        self._settle_circuit(board, player_inputs={key} if by_player else None)
        return True

    def _circuit_sequence_event(self, board: dict, key: str) -> None:
        for seq_key, node in board["nodes"].items():
            if node["op"] != "sequence" or key not in node["inputs"]:
                continue
            progress = board["state"].setdefault("sequences", {}).get(seq_key, 0)
            order = node["order"]
            if progress >= len(order):
                continue
            if key == order[progress]:
                progress += 1
                self.messages.append(tr("记忆接线：{count}/{total}。", count=progress, total=len(order)))
            else:
                progress = 1 if key == order[0] else 0
                self.messages.append(tr("音序不符，接线回到起点。"))
            board["state"]["sequences"][seq_key] = progress

    def _settle_circuit(self, board: dict, at_time: int | None = None, *, player_inputs: set | None = None) -> None:
        runtime = board["state"]
        previous = runtime.get("values", {})
        values = {}
        player_inputs = player_inputs or set()
        causal = set()
        for key in board["order"]:
            node = board["nodes"][key]
            x, y = node["pos"]
            op = node["op"]
            inputs = [bool(values[ref]) for ref in node.get("inputs", [])]
            # A destroyed component breaks its circuit; traces alone cannot replace it.
            intact = not node.get("wall") or self.cell(x, y).wall_kind == node["wall"]
            value = False
            if intact:
                if op == "toggle":
                    value = runtime.get("switches", {}).get(key, node.get("initial", False))
                elif op in {"plate", "step"}:
                    value = self.entity_at(x, y) is not None or self.cell(x, y).wall_kind == "理念立方体"
                elif op == "pulse":
                    value = runtime.get("pulses", {}).get(key, -1) > (self.time if at_time is None else at_time)
                elif op == "cube":
                    value = self.cell(x, y).wall_kind == "理念立方体"
                elif op == "timer":
                    phase = node.get("phase", 0)
                    if node.get("phase_input") and values[node["phase_input"]]:
                        phase = node.get("on_phase", 0)
                    value = ((self.time if at_time is None else at_time) + phase) % node.get("period", 8) < node.get("window", 1)
                elif op == "sensor":
                    value = any(e.integrity > 0 and e.relation == "失控意识"
                                and max(abs(e.x-x), abs(e.y-y)) <= node.get("radius", 4)
                                for e in self.enemies)
                elif op == "and":
                    value = all(inputs)
                elif op == "or":
                    value = any(inputs)
                elif op == "not":
                    value = not inputs[0]
                elif op == "sequence":
                    value = runtime.get("sequences", {}).get(key, 0) == len(node["order"])
                elif op == "output":
                    value = inputs[0] or (node.get("latch", False) and previous.get(key, False))
            clock = self.time if at_time is None else at_time
            if intact and runtime.get("forced_until", {}).get(key, -1) > clock:
                value = True
            values[key] = bool(value)
            if ((key in player_inputs and (values[key] != previous.get(key, False)
                                         or op in {'pulse', 'step'}))
                    or any(ref in causal for ref in node.get('inputs', []))):
                causal.add(key)
            if op != "output" or not intact:
                continue
            kind = node.get("wall")
            if kind == "机关门":
                # Closing a level-controlled door waits until the doorway is empty.
                desired = not value
                if not desired or self.entity_at(x, y) is None:
                    self.cell(x, y).solid = desired
            elif value and not previous.get(key, False):
                if kind == "陷阱石台":
                    if self._effect_power("wire_safe") <= 0:
                        from ..materials.logic import TRAP_SCENARIO_LIBRARY
                        scenario = self.trap_scenarios.get(f"{x},{y}", "dud")
                        self._execute_scenario(x, y, TRAP_SCENARIO_LIBRARY.get(scenario, {"type": "dud"}))
                else:
                    sx,sy = board["nodes"][node["inputs"][0]]["pos"]
                    self._resolve_receiver(x, y, source_x=sx, source_y=sy)
            if value and not previous.get(key, False) and key in causal:
                index = next(i for i, item in enumerate(self.circuit_boards) if item is board)
                self._identity_receiver(x, y, f'board:{index}:{key}')
        runtime["values"] = values
        self._logic_energized.difference_update(tuple(p) for net in board["nets"] for p in net["path"])
        for net in board["nets"]:
            if values[net["from"]]:
                self._logic_energized.update(tuple(p) for p in net["path"])
        if board.get("completion") and values[board["completion"]]:
            if self.realm_id == "toy_memories":
                self._mark_toy_solved()

    def _tick_circuit_boards(self, at_time: int | None = None) -> None:
        for board in self.circuit_boards:
            self._settle_circuit(board, at_time)

    def force_circuit_node(self, x: int, y: int, *, by_player: bool = False) -> bool:
        hit = self.circuit_node_at(x,y)
        if hit is None or self.realm_id == "toy_memories":
            return False
        board,key,_ = hit
        board["state"].setdefault("forced_until", {})[key] = self.time+3
        self._settle_circuit(board, player_inputs={key} if by_player else None)
        return True

    def rewire_circuit_nodes(self, start, end, *, by_player: bool = False) -> bool:
        a,b = self.circuit_node_at(*start), self.circuit_node_at(*end)
        if not a or not b or a[0] is not b[0] or self.realm_id == "toy_memories":
            return False
        if a[2]["op"] not in INPUTS or b[2]["op"] != "output":
            return False
        from ..data.circuit_templates import connect_board
        board = deepcopy(a[0])
        board["nodes"][b[1]]["inputs"] = [a[1]]
        connect_board(board,self.width,self.height)
        board["order"] = validate_board(board,self.width,self.height)
        for net in a[0]["nets"]:
            for x,y in net["path"]:
                self.cell(x,y).wire = 0
        a[0].update(board)
        for net in board["nets"]:
            self.lay_wire_path([tuple(p) for p in net["path"]])
        self._settle_circuit(a[0], player_inputs={b[1]} if by_player else None)
        return True

    def _resume_circuit_boards(self) -> None:
        self._logic_energized = set()
        for board in self.circuit_boards:
            board["order"] = validate_board(board, self.width, self.height)
        if self.realm_id == "toy_memories":
            if not self.circuit_boards:
                # Legacy toy maps contain disconnected rooms and solid goals.
                # Migrate this puzzle only; never replace the main dream or inventory.
                self.reset_realm_puzzle()
                return
            self._toy_targets = [tuple(n["pos"]) for b in self.circuit_boards for n in b["nodes"].values() if n["op"] == "cube"]
            self.realm_gate_open = any(b["state"].get("acknowledged", False) for b in self.circuit_boards)
            solved = self.realm_gate_open or any(
                b['state'].get('solved') or b['state'].get('values', {}).get(b.get('completion'))
                for b in self.circuit_boards)
            if solved:
                self.realm_puzzle_solved[self.realm_depth] = True
            else:
                self.realm_puzzle_solved.pop(self.realm_depth, None)
            if self.realm_depth < 4:
                self.realm_challenges.setdefault('toy_variants', {}).setdefault(
                    str(self.realm_depth), self.circuit_boards[0].get('variant', 'classic'))
            else:
                from .toy_puzzles import resume_workshop
                resume_workshop(self)
        # Restore the displayed traces, never replay receiver edges while loading.
        # Doors and traps already carry their settled state in the saved cells.
        for board in self.circuit_boards:
            values = board["state"].get("values", {})
            for net in board["nets"]:
                if values.get(net["from"], False):
                    self._logic_energized.update(tuple(p) for p in net["path"])

    def _mark_toy_solved(self) -> None:
        for board in self.circuit_boards:
            board['state']['solved'] = True
        if not self.realm_puzzle_solved.get(self.realm_depth):
            self.realm_puzzle_solved[self.realm_depth] = True
            self.messages.append(tr("回路闭合——这一层的谜题完成了，去与守门人交谈。"))

    def talk_toy_keeper(self, npc) -> None:
        if self.realm_id != "toy_memories" or not str(getattr(npc, "npc_kind", "")).startswith("npc."):
            return
        from ..data.dreams import TOY_MEMORIES
        if getattr(npc, "npc_kind", "") != TOY_MEMORIES.npc_for_layer[self.realm_depth-1]:
            return
        if self.realm_puzzle_solved.get(self.realm_depth) and not self.realm_gate_open:
            self.realm_gate_open = True
            for board in self.circuit_boards:
                board["state"]["acknowledged"] = True
            text = ("{name}确认校准完成，可以返回主梦了。" if self.realm_depth == 4
                    else "{name}让开了路——这一层的门认得你了（N 下潜）。")
            self.messages.append(tr(text, name=tr(npc.label)))

    def reset_realm_puzzle(self) -> ActionResult:
        if self.realm_id != "toy_memories":
            return ActionResult(False, tr("这里没有可以重置的玩具机关。"))
        from ..data.dreams import TOY_MEMORIES
        depth = self.realm_depth
        self.layer_states.pop(self._realm_layer_key(depth), None)
        self.realm_puzzle_solved.pop(depth, None)
        self.realm_gate_open = False
        self._generate_realm_layer(TOY_MEMORIES, depth)
        self.pending_npc_id = None
        self.messages.append(tr("机关与立方体回到起点，背包与资源保持原状。"))
        return ActionResult(True, self.messages[-1], {"puzzle_reset": depth})

    def circuit_details(self, x: int, y: int) -> list[str]:
        hit = self.circuit_node_at(x, y)
        if hit is None:
            sources = {(i,n["from"]) for i,b in enumerate(self.circuit_boards) for n in b["nets"] if [x, y] in n["path"]}
            return [tr("绝缘交叉：线路互不连接。")] if len(sources) > 1 else []
        board, key, node = hit
        value = board["state"].get("values", {}).get(key, False)
        lines = [tr("{label}：{state}。", label=tr(node["label"]), state=tr("通电" if value else "断电"))]
        if node.get("inputs"):
            lines.append(tr("输入：{ports}", ports=" / ".join(tr(board["nodes"][p]["label"]) for p in node["inputs"])))
        meanings = {"and": "所有输入同时通电", "or": "任一输入通电", "not": "输入断电时输出通电", "cube": "仅立方体的重量有效"}
        if node["op"] in meanings:
            lines.append(tr(meanings[node["op"]]))
        if node["op"] == "timer":
            phase = node.get("phase", 0)
            if board["state"].get("values", {}).get(node.get("phase_input"), False):
                phase = node.get("on_phase", 0)
            lines.append(tr("周期 {period}，相位 {phase}，亮灯 {window} 回合。",
                            period=node.get("period", 8), phase=(self.time+phase) % node.get("period", 8), window=node.get("window", 1)))
        if node["op"] == "sequence":
            lines.append(tr("记忆接线：{count}/{total}。", count=board["state"].get("sequences", {}).get(key, 0), total=len(node["order"])))
        if self.insight_active("电工直觉"):
            lines.extend(self._wire_port_details(board, key, node))
        return lines

    def _wire_port_details(self, board: dict, key: str, node: dict) -> list[str]:
        """电工直觉：只列已确认的同板端口与接线兼容性。"""
        def confirmed(other: dict) -> bool:
            ox, oy = other["pos"]
            return bool(self.is_visible(ox, oy))

        all_outputs = [(k, n) for k, n in board["nodes"].items()
                       if n["op"] == "output"]
        inputs = [(k, n) for k, n in board["nodes"].items()
                  if n["op"] in INPUTS and k != key and confirmed(n)]
        outputs = [(k, n) for k, n in all_outputs if confirmed(n)]
        lines: list[str] = []
        if node["op"] in INPUTS:
            known = " / ".join(tr(n["label"]) for _, n in outputs)
            lines.append(tr("已知同板接收端口：{ports}（可接线）。", ports=known) if known
                         else tr("已知同板接收端口：尚未确认。"))
        else:
            known = " / ".join(tr(n["label"]) for _, n in inputs)
            lines.append(tr("已知同板输入端口：{ports}。", ports=known) if known
                         else tr("已知同板输入端口：尚未确认。"))
            lines.append(tr("接线兼容：输入端口可接到输出端口；其他端口不兼容。"))
        unknown = [n for _, n in all_outputs if not confirmed(n)]
        if unknown:
            lines.append(tr("未明连线：只显示到已确认边缘，不展开隐藏机关。"))
        return lines

    def trigger_insight_details(self, x: int, y: int) -> list[str]:
        """机关嗅觉：可见触发器的下一次触发类型与已确认接收器。

        隐藏接收器只提示可能存在未明连线，不给坐标，也不实际触发。
        """
        if not self.insight_active("机关嗅觉"):
            return []
        kinds = {"toggle": "开关", "pulse": "脉冲", "step": "踩踏",
                 "plate": "压力板", "cube": "重量", "timer": "定时", "sensor": "感应"}
        scenario_types = {"summon": "召唤异象", "cage": "囚笼锁闭", "gas": "毒气灌注",
                          "projectile": "弹药伏击", "portent": "征兆诅咒",
                          "terrain": "地形坍缩", "dud": "虚惊一场"}
        hit = self.circuit_node_at(x, y)
        lines: list[str] = []
        if hit is not None:
            board, key, node = hit
            if node["op"] not in INPUTS:
                return []
            lines.append(tr("下一次触发：{kind}。",
                            kind=tr(kinds.get(node["op"], node["op"]))))
            known = 0
            hidden = 0
            for other_key, other in board["nodes"].items():
                if other["op"] != "output":
                    continue
                if not self._node_reaches(board, key, other_key):
                    continue
                ox, oy = other["pos"]
                if not self.is_visible(ox, oy):
                    hidden += 1
                    continue
                known += 1
                wall = self.cell(ox, oy).wall_kind or str(other.get("wall", ""))
                if wall == "陷阱石台":
                    from ..materials.logic import TRAP_SCENARIO_LIBRARY
                    scenario = self.trap_scenarios.get(f"{ox},{oy}", "dud")
                    kind_name = scenario_types.get(
                        TRAP_SCENARIO_LIBRARY.get(scenario, {}).get("type", "dud"), "虚惊一场")
                    lines.append(tr("已确认接收器：{label}（{kind}）。",
                                    label=tr(other["label"]), kind=tr(kind_name)))
                else:
                    lines.append(tr("已确认接收器：{label}（{kind}）。",
                                    label=tr(other["label"]),
                                    kind=tr(wall or other["label"])))
            if hidden or not known:
                lines.append(tr("其余接收器未确认：可能存在未明连线。"))
            return lines
        if self.cell(x, y).wall_kind != "陷阱石台":
            return []
        scenario = self.trap_scenarios.get(f"{x},{y}")
        from ..materials.logic import TRAP_SCENARIO_LIBRARY
        kind_name = scenario_types.get(
            TRAP_SCENARIO_LIBRARY.get(scenario or "dud", {}).get("type", "dud"), "虚惊一场")
        lines.append(tr("下一次触发：{kind}。", kind=tr(kind_name)))
        lines.append(tr("接收器未确认：可能存在未明连线。"))
        return lines

    @staticmethod
    def _node_reaches(board: dict, source: str, target: str) -> bool:
        seen: set[str] = set()
        stack = [source]
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            for other_key, other in board["nodes"].items():
                if current in other.get("inputs", ()):
                    stack.append(other_key)
        return False
