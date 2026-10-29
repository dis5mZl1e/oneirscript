"""梦中梦运行时（2026-09-21）：进入 / 层内下潜上浮 / 返回入口 / 环形门廊地形。

- 进入：``enter_realm(realm_id)``——归档主梦当前层、记录入口坐标、生成 realm 第 1 层。
- 层内下潜（n）：realm_depth +1（不查崩解度，花 1 点清醒度）；到顶提示。
- 层内上浮（b）：realm_depth −1；**第 1 层上浮 = 返回主梦入口层与入口格**。
- 主梦的 ``self.depth`` 全程不变——区域主题、异象刷新、结局判定都不受支线影响。
- 地形算法以名字注册在 ``_REALM_GENERATORS``：新增 realm 即插即用。
"""

from __future__ import annotations

import random
import zlib

from ..data.dreams import (
    DREAM_REALM_DEFINITIONS,
    DreamRealmDef,
    EBBING_EXIT_REWARD,
    EMBER_REWARD_LABELS,
    realm_def,
    _DREAM_EVENT_DEFS,
)
from ..mapgen import layer_modifier_for
from ..i18n import tr
from ..mapgen.layout import normalize_map_form
from .ebbing import EBBING_FAIL_MIND_COST
from .entities import ActionResult, Cell


class DreamRealmMixin:
    """挂在 GameState 上：梦中梦的进出与生成。"""

    # ------------------------------------------------------------- 进出

    def enter_realm(self, realm_id: str) -> bool:
        """从主梦进入梦中梦（入口条件由调用方判定：物品/事件/地点）。"""
        definition = realm_def(realm_id)
        if definition is None or self.realm_id or realm_id in self.closed_realms:
            return False
        self._archive_active_layer()
        self.realm_id = realm_id
        self.realm_depth = 1
        self.realm_gate_open = False
        self.entry_depth = self.depth
        self._entry_layer_modifier = self.layer_modifier  # 退出时恢复
        self.layer_modifier = ""  # 梦中梦不受主梦修饰符影响
        self.entry_x, self.entry_y = self.player.x, self.player.y
        self._restore_or_generate_realm_layer(1)
        # 入口物品（非消耗范式）：进层授予、离开/通关/失败时回收。
        if definition.entry_grant_item:
            try:
                self._add_inventory_item(self._make_item(definition.entry_grant_item))
                self.messages.append(tr("你手里多了「{item}」。", item=tr(definition.entry_grant_item)))
            except ValueError:
                self.messages.append(tr("意识行囊已满，入口信物暂时没能带进来。"))
                if realm_id == "ember_bridge":
                    from .realm_challenges import say
                    self.messages.append(say('full_lighter'))
        self.messages.append(tr("钥匙在锁孔里转了半圈——你侧身走进了一扇不存在的门。"))
        self.messages.append(tr("—— 梦中梦·{name} 第 1 层 ——", name=tr(definition.name)))
        if realm_id in ('ember_bridge', 'ebbing_hall'):
            from .realm_challenges import say
            self.messages.append(say('ember_intro' if realm_id == 'ember_bridge' else 'tide_intro'))
        return True

    def _exit_realm(self, outcome: str = "leave") -> None:
        """从 realm 第 1 层上浮（或按结果退出）：回到进入时的主梦层与入口格。

        ``outcome``:
        - ``"leave"``：普通上浮（快照保留，可再次进入）——既有行为；
        - ``"clear"``：通关（本局关门，不可再进）；
        - ``"fail"``：未逃出（本局关门 + 扣心智），**绝不置 run_over**。
        """
        definition = realm_def(self.realm_id)
        self._archive_active_layer()
        name = tr(definition.name) if definition else self.realm_id
        if outcome in ("clear", "fail") and self.realm_id:
            self.closed_realms.add(self.realm_id)
        if outcome == "fail":
            floor = 1 if self.lucidity <= 0 and self.mind > 0 else 0
            fail_cost = min(EBBING_FAIL_MIND_COST, max(0, self.mind-floor))
            from .settlement import REASON_STORY, settle_delta
            settle_delta(self, 'mind', -fail_cost, reason=REASON_STORY,
                         source='退潮厅失败')
        # 回收入口物品（引火人的火柴一类非消耗信物别被带出位面）。
        if definition is not None and definition.entry_grant_item:
            self.inventory = [
                it for it in self.inventory
                if it.definition_id != definition.entry_grant_item
            ]
        self.realm_id = ""
        self.realm_depth = 0
        self._restore_or_generate_layer(self.entry_depth)
        # 入口格若被堵（门关上/显化物变动），就近找开放格落脚。
        if self.cell(self.entry_x, self.entry_y).solid or self.entity_at(self.entry_x, self.entry_y):
            spot = self._find_open_cell(self.cells, self.entry_x, self.entry_y)
            self.player.x, self.player.y = spot
        else:
            self.player.x, self.player.y = self.entry_x, self.entry_y
        # 恢复主梦修饰符：按入口层确定性重算（与初次生成一致）。
        self.layer_modifier = layer_modifier_for(self.seed, self.entry_depth)
        # 关门：把本局已关闭的位面入口从主梦层上抹掉（地点与 NPC 都清）。
        self._purge_closed_realm_entries()
        if outcome == "fail":
            self.messages.append(
                tr("{name}的潮水漫过了你的脚踝——你被冲了出来，心智 −{n}。",
                   name=name, n=fail_cost)
            )
        else:
            self.messages.append(tr("你从门里退了出来——{name}在你身后合拢。", name=name))

    def ascend_realm(self) -> bool:
        """层内上浮（b）：第 1 层 = 退出梦中梦；其余层号 −1。"""
        if not self.realm_id:
            return False
        # 退潮厅：跨过门槛后回头没有路（退潮已开始，门已合拢）。
        if self.realm_id == "ebbing_hall" and self.ebbing_past_threshold:
            self.messages.append(tr("潮水已经漫过门槛，回头没有路了。"))
            return False
        if self.realm_depth <= 1:
            self._exit_realm()
            return True
        definition = realm_def(self.realm_id)
        self._archive_active_layer()
        self.realm_depth -= 1
        self.realm_gate_open = bool(self.realm_puzzle_solved.get(self.realm_depth))
        self._restore_or_generate_realm_layer(self.realm_depth)
        self.messages.append(tr("你退回上一层门廊：梦中梦·{name} 第 {n} 层。",
                                name=tr(definition.name), n=self.realm_depth))
        return True

    def can_descend_realm(self) -> bool:
        """Validate the current doorway before charging travel time."""
        if not self.realm_id:
            return False
        definition = realm_def(self.realm_id)
        if not self.realm_gate_open:
            self._sync_task_realm_gate()
        if self.realm_depth >= definition.layer_count:
            self.messages.append(tr("{name}的最深处——门在这里只剩墙的形状。",
                                    name=tr(definition.name)))
            return False
        # 守门人门控（玩具的回忆/两谷）：解谜达成并与守门人对话后才放行。
        if definition.npc_gate and not self.realm_gate_open:
            self.messages.append(self._gate_refusal_message(definition))
            return False
        return True

    def descend_realm(self) -> bool:
        """Cross a validated realm doorway, paying its lucidity cost."""
        if not self.can_descend_realm():
            return False
        definition = realm_def(self.realm_id)
        from .settlement import REASON_ABILITY_COST, settle_delta
        settle_delta(self, 'lucidity', -1, reason=REASON_ABILITY_COST,
                     source='位面之门')
        self._check_run_over()
        if self.run_over:
            return False
        self._archive_active_layer()
        self.realm_depth += 1
        self.realm_gate_open = bool(self.realm_puzzle_solved.get(self.realm_depth))
        self._restore_or_generate_realm_layer(self.realm_depth)
        self.messages.append(tr("你又穿过一扇门：梦中梦·{name} 第 {n} 层。",
                                name=tr(definition.name), n=self.realm_depth))
        return True

    def _sync_task_realm_gate(self) -> None:
        """Task realms own their progress per layer; shared toy flags are insufficient."""
        if self.realm_id == 'library_palace':
            from .library_content import ensure_library_gate
            ensure_library_gate(self)
        elif self.realm_id == 'white_sanatorium':
            from .hospital_scenes import ensure_hospital_gate
            ensure_hospital_gate(self)

    def _gate_refusal_message(self, definition) -> str:
        """npc_gate 拒绝下潜时的提示：按位面报出本层还缺哪几项手续。

        进度账本由各位面模块维护（library_gate / hospital_gate，存在
        realm_features 里随层快照持久化）；这里只读不写。账本缺失
        （旧存档）时懒重建，保证已做完的条件不会因字段缺失而死锁。
        """
        if self.realm_id == "library_palace":
            from .library_content import ensure_library_gate
            gate = ensure_library_gate(self)
            names = {"card": "借书卡", "margin": "批注", "optional": "目录机关"}
        elif self.realm_id == "white_sanatorium":
            from .hospital_scenes import ensure_hospital_gate
            gate = ensure_hospital_gate(self)
            names = {"chart": "病历夹", "queue": "叫号屏", "scene": "一处设施"}
        else:
            gate = None
        if gate:
            missing = [tr(names[key]) for key in gate["required"]
                       if key not in gate["done"]]
            if missing:
                progress = tr("还差 {n} 项：{items}。",
                              n=len(missing), items="、".join(missing))
                return tr("门纹未亮——{reason}", reason=progress)
        return tr("门纹丝不动——先完成这一层的解谜，与守门人谈谈。")

    # --------------------------------------------------------- 掉线拨号（§4.1）

    def _maybe_dial_in(self, target_depth: int) -> None:
        """掉线拨号判定：主梦 depth≥11 的下潜 12% 概率触发，每局 2 次封顶。

        只在**成功下潜**后掷（玩家已落到 target_depth）——拨号出现在落脚层；
        「不必是新层」：同一层反复进出也照判，但已触发过的层（layers_seen）
        不再触发。触发 ≠ 强制进入：出现 24 回合限时状态，玩家按回应键应答。
        """
        if self.realm_id or target_depth < 11:
            return
        dial = self.dial_in
        if dial.get("triggers_used", 0) >= 2 or target_depth in dial.get("layers_seen", []):
            return
        if random.Random(self.seed ^ (self.time * 977) ^ target_depth * 131).random() >= 0.12:
            return
        dial["triggers_used"] = dial.get("triggers_used", 0) + 1
        dial.setdefault("layers_seen", []).append(target_depth)
        dial["active"] = {"rounds": 24}
        self.messages.append(tr("刺耳的调制音撕开梦面——网络邻居正在敲门。"))
        self.messages.append(tr("（{rounds} 回合内按「回应」应答，过时对面挂断。）", rounds=24))

    def _tick_dial_in(self, amount: int) -> None:
        """拨号倒计时：随 _advance 的客观回合推进，归零即挂断。"""
        if self.realm_id:
            return
        active = self.dial_in.get("active")
        if not active:
            return
        active["rounds"] = int(active.get("rounds", 0)) - amount
        if active["rounds"] <= 0:
            self.dial_in["active"] = None
            self.messages.append(tr("拨号音停了——对面挂断了。"))

    def _answer_dial_in(self) -> ActionResult:
        """回应拨号：进入千禧园（入口条件天然满足——active 存在即授权）。"""
        self.dial_in["active"] = None
        self.messages.append(tr("你摘下听筒——握手音之后，世界换了一层旧漆。"))
        self.enter_realm("millennium_garden")
        return ActionResult(True, self.messages[-1], {"realm": "millennium_garden"})

    # ------------------------------------------------------------- 生成

    def _realm_layer_key(self, depth: int) -> str:
        return f"R{self.realm_id}:{depth}"

    def _restore_or_generate_realm_layer(self, depth: int) -> None:
        self.library_bookmark = {}
        # §12 E 审计结论按层重置：旧层的场景组不能跟着带进新层。
        self.light_scene_report = {}
        self.light_fixture_report = {}
        """realm 层同样走快照：有旧残局就还原，没有才按种子生成。

        还原字段与主梦分支对齐（见 GameState._restore_or_generate_layer）——
        早年只搬 cells/enemies/items 会让玩家一换层就被传送回出生点、
        崩解度与机关状态一并清零。
        """
        snapshot = self.layer_states.get(self._realm_layer_key(depth))
        if snapshot:
            self.cells = snapshot.cells
            self._resume_material_clocks(snapshot)
            self.enemies = snapshot.enemies
            self.world_items = snapshot.world_items
            self.events = snapshot.events
            self.player.x, self.player.y = snapshot.player_x, snapshot.player_y
            self.dissolution = snapshot.dissolution
            self.map_form = normalize_map_form(snapshot.map_form)
            self.theme = snapshot.theme
            if snapshot.width > 0 and snapshot.height > 0:
                self.width, self.height = snapshot.width, snapshot.height
            self.trap_scenarios = dict(snapshot.logic_scenarios)
            self.valve_stored = {k: tuple(v) for k, v in snapshot.logic_valves.items()}
            from copy import deepcopy
            self.circuit_boards = deepcopy(snapshot.logic_boards)
            self._restore_logic_fences(snapshot.logic_fences)
            self.enemy_skill_fields = deepcopy(snapshot.enemy_skill_fields)
            self.realm_bg_zones = deepcopy(snapshot.realm_bg_zones)
            self.realm_features = deepcopy(snapshot.realm_features)
            self.gate_inputs = {}
            self._resume_circuit_boards()
            self._reset_material_index()
            self._sync_task_realm_gate()
            if self.realm_id == 'ember_bridge':
                from .realm_challenges import ensure_ember
                ensure_ember(self)
            elif self.realm_id == 'ebbing_hall':
                from .realm_challenges import ensure_tide_exit
                ensure_tide_exit(self)
            return
        self._generate_realm_layer(realm_def(self.realm_id), depth)
        self._sync_task_realm_gate()

    def _generate_realm_layer(self, definition: DreamRealmDef, depth: int) -> None:
        if definition.realm_id == 'toy_memories':
            # A new toy puzzle cannot inherit another realm's local depth flag.
            self.realm_puzzle_solved.pop(depth, None)
        self.realm_bg_zones = []
        self.realm_features = {}
        gen_name = definition.generator
        if definition.realm_id == "toy_memories" and depth == 4:
            gen_name = "toy_sokoban"
        generator = _REALM_GENERATORS.get(gen_name, _generate_ring_corridors)
        width, height, cells, spawn = generator(self, definition, depth)
        self.width, self.height = width, height
        self.cells = cells
        self.circuit_boards = []
        self.gate_inputs = {}
        self._logic_energized = set()
        self.trap_scenarios = {}
        self.valve_stored = {}
        self._mind_fences = {}
        self._rune_cooldowns = {}
        self._reset_material_index()
        self.player.x, self.player.y = spawn
        self.enemies = []
        self.world_items = []
        self.events = []
        self.dissolution = 0
        if getattr(self, "_pending_circuit_board", None):
            self.install_circuit_board(self._pending_circuit_board)
            self._pending_circuit_board = None
            self._tick_circuit_boards()
        self.map_form = f"梦中梦·{definition.name}"
        rng = random.Random(self.seed ^ zlib.crc32(definition.realm_id.encode('utf-8')) ^ depth * 3571)
        # ---- 异象守门：按层配额从池里抽，散在环廊上 ----
        count = definition.anomaly_count[min(depth, len(definition.anomaly_count)) - 1]
        if definition.realm_id == 'library_palace':
            from .library_content import spawn as spawn_library_encounters
            spawn_library_encounters(self, depth, rng)
            count = 0
        if definition.realm_id == 'white_sanatorium':
            from .hospital_skills import spawn_hospital_encounters
            spawn_hospital_encounters(self, depth, rng)
            count = 0
        placed = 0
        from ..data.realm_challenges import EMBER_GUARDS, EBBING_GUARDS
        guard_spots = (EMBER_GUARDS if definition.realm_id == 'ember_bridge' else
                       EBBING_GUARDS if definition.realm_id == 'ebbing_hall' else None)
        for attempt in range(count * 12):
            if placed >= count:
                break
            if guard_spots:
                if attempt >= len(guard_spots):
                    break
                x, y = guard_spots[attempt]
            else:
                x = rng.randrange(2, width - 2)
                y = rng.randrange(2, height - 2)
            main_path = self.realm_features.get('millennium_cabin', {}).get('main_path', ())
            if (x, y) in {tuple(p) for p in main_path}:
                continue
            cell = self.cell(x, y)
            if cell.solid or self.entity_at(x, y) or (abs(x - spawn[0]) + abs(y - spawn[1]) < 5):
                continue
            catalog_id = definition.anomaly_pool[rng.randrange(len(definition.anomaly_pool))]
            from .content import ANOMALY_DEFINITIONS

            base = ANOMALY_DEFINITIONS[catalog_id]
            enemy = self.add_defined_enemy(catalog_id, x, y)
            enemy.integrity = max(1, round(base["integrity"] * (1.0 + 0.15 * depth)))
            if guard_spots:
                enemy.integrity = 6
                enemy.mind_trauma = 2
                enemy.lucidity_trauma = 0
                enemy.vision = 4
                enemy.move_time = max(1.4, enemy.move_time)
            placed += 1
        # ---- 圣所独特物品：门之回廊只在第 3 层（最后一层）刷一件 ----
        # 千禧园例外：sanctum_in_generator=True，圣所物品由 millennium_park
        # 生成器放进木屋台面；这里跳过，否则中心开放时中心+木屋**双份**。
        # 其余 realm 保持旧口径：物品直接放地图中心格（中心是石台时=台面承载，
        # 是既有机制——不许按固体跳过，那会把门之回廊的圣所弄丢）。
        sanctum_items = definition.sanctum_items
        if sanctum_items and not definition.sanctum_in_generator:
            item_id = sanctum_items[min(depth, len(sanctum_items)) - 1]
            from .entities import WorldItem
            from ..core.content import ITEM_DEFINITIONS  # noqa: F401 循环导入防护

            sx, sy = width // 2, height // 2
            self.world_items.append(
                WorldItem(self._make_item(item_id), sx, sy))
            # ---- 门之回廊：连通性自检 + 特殊石台事件（玻璃瓶/气球均等）+ 守灯人 ----
        if definition.realm_id == "door_corridor":
            from collections import deque as _dq
            seen = {spawn}
            queue = _dq([spawn])
            while queue:
                cx, cy = queue.popleft()
                for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < width and 0 <= ny < height
                            and (nx, ny) not in seen
                            and (not cells[ny][nx].solid or cells[ny][nx].wall_kind == '门')):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            # 若圣所或某段环廊不可达：沿直线补凿一扇门（地形自愈）。
            cx0, cy0 = width // 2, height // 2
            if not any((cx0+dx, cy0+dy) in seen for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))):
                x, y = spawn
                while (x, y) != (cx0, cy0):
                    if (x, y) not in seen:
                        seen.add((x, y))
                        cells[y][x].solid = False
                        cells[y][x].wall_kind = ""
                    x += (cx0 > x) - (cx0 < x)
                    y += (cy0 > y) - (cy0 < y)
                seen.add((cx0, cy0))
                cells[cy0][cx0].solid = False
                cells[cy0][cx0].wall_kind = ""
            # 特殊石台事件：中层环廊随机点，50/50 玻璃瓶（瓶中之门）或气球
            #（无风的气球），事件实体放在石台相邻的开放格。
            from ..data.dreams import DOOR_CORRIDOR_EVENTS
            from .entities import WorldEvent as _WorldEvent

            event_id = DOOR_CORRIDOR_EVENTS[rng.randrange(len(DOOR_CORRIDOR_EVENTS))]
            open_cells = [
                (x, y) for y in range(height) for x in range(width)
                if not cells[y][x].solid and (x, y) != spawn
                and max(abs(x - spawn[0]), abs(y - spawn[1])) >= 3
            ]
            if open_cells:
                sx, sy = open_cells[rng.randrange(len(open_cells))]
                cells[sy][sx].wall_kind = "石台"
                cells[sy][sx].solid = True
                cells[sy][sx].hardness = 2
                cells[sy][sx].integrity = 70
                definition_map = {
                    "event.dream_bottle": _DREAM_EVENT_DEFS["event.dream_bottle"],
                    "event.dream_balloon": _DREAM_EVENT_DEFS["event.dream_balloon"],
                }
                edef = definition_map[event_id]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = sx + dx, sy + dy
                    if 0 <= nx < width and 0 <= ny < height and not cells[ny][nx].solid:
                        if not hasattr(self, "_pending_realm_events"):
                            self._pending_realm_events = []
                        self._pending_realm_events.append(_WorldEvent(
                            event_id=edef["event_id"], name=edef["name"],
                            x=nx, y=ny, description=edef["description"],
                            catalog_id=edef["catalog_id"], kind="compound",
                            dialogue=tuple(edef.get("dialogue", ())),
                            options=tuple(edef.get("options", ())),
                            uses_left=int(edef.get("uses", 1)),
                            bound=True,
                        ))
                        break
            # 守灯人：外环出生点附近两格。
            from ..data.dreams import DOOR_CORRIDOR_KEEPER
            from .entities import Entity as _Entity

            keeper_x, keeper_y = 3, spawn[1] + 2
            if not cells[keeper_y][keeper_x].solid:
                keeper = _Entity(
                    "npc.lantern_keeper", "提灯的门房", keeper_x, keeper_y,
                    integrity=40, relation="稳定意识", glyph="✜ ",
                    move_time=2.0, attack_time=99.0, trauma_type="清醒创伤",
                    communicates=True, drop_id=None, dissolution_reward=0, vision=0,
                )
                keeper.npc_kind = "npc.lantern_keeper"
                keeper.npc_options = ()
                if not hasattr(self, "_pending_realm_entities"):
                    self._pending_realm_entities = []
                self._pending_realm_entities.append(keeper)

        # ---- 挂起实体/事件并入（生成器与 enrichment 都已写入 pending）----
        if getattr(self, "_pending_realm_entities", None):
            self.enemies.extend(self._pending_realm_entities)
            self._pending_realm_entities = []
        if getattr(self, "_pending_realm_events", None):
            self.events.extend(self._pending_realm_events)
            self._pending_realm_events = []
        if getattr(self, "_pending_realm_items", None):
            self.world_items.extend(self._pending_realm_items)
            self._pending_realm_items = []
            # §14.6 台面落点：位面层同样只换落点、不增份数。医院的白瓷工作台与
            # 图书馆的胡桃木书架是可步行家具，算承载面（materials.SURFACE_KINDS）——
            # 没有这一步，两栋建筑里的家具永远只是装饰，东西一件也不会搁在上面。
            self.last_surface_report = self.stamp_surfaces()
        if definition.realm_id == 'white_sanatorium':
            from .hospital_scenes import install_hospital_actors
            install_hospital_actors(self)
        if definition.realm_id == 'ember_bridge':
            from .realm_challenges import ensure_ember
            ensure_ember(self)

        # ---- 玩具的回忆：摆放守门人 NPC，初始化本层解谜状态 ----
        if definition.realm_id == "toy_memories":
            npc_pos = getattr(self, "_toy_npc_pos", None)
            npc_id = definition.npc_for_layer[min(depth, len(definition.npc_for_layer)) - 1]
            if npc_pos:
                npc = self._add_npc(npc_id, *npc_pos)
                npc.always_visible = True  # 守门人在自己的房间里永远可见
            self.realm_gate_open = bool(self.realm_puzzle_solved.get(depth))
            # 注意：不在这里清 _toy_switches/_toy_plate_order——生成器已设好
            # 位置，清了会导致解谜检测找不到目标。
        # ---- 环境弥散印象：零星门隙之风 ----
        if definition.ambient_gas:
            from ..materials import GAS_DEFINITIONS

            if definition.ambient_gas in GAS_DEFINITIONS:
                for _ in range(5):
                    x = rng.randrange(2, width - 2)
                    y = rng.randrange(2, height - 2)
                    cell = self.cell(x, y)
                    dry_path = {tuple(p) for p in self.realm_features.get('millennium_cabin', {}).get('main_path', ())}
                    if not cell.solid and cell.gas == 0 and (x, y) not in dry_path:
                        self._add_gas(cell, definition.ambient_gas, 18)

        # ---- §12 E：位面光源场景（独立随机流，只改 Cell.plant）----
        # 位面专用光源（灯箱墙/日光壁/阅读灯/通电电路/门灯）仍由各生成器负责，
        # 这里只补一小片「无拔除收益」的弱光植物。保护：出生点 7×7、圣所 5×5、
        # 已落地的 NPC/事件/台面，以及千禧园主路——不占用唯一通路与机关格。
        from .light_scenes import place_light_scenes

        scene_protected: set[tuple[int, int]] = set()
        for sy in range(spawn[1] - 3, spawn[1] + 4):
            for sx in range(spawn[0] - 3, spawn[0] + 4):
                scene_protected.add((sx, sy))
        for sy in range(height // 2 - 2, height // 2 + 3):
            for sx in range(width // 2 - 2, width // 2 + 3):
                scene_protected.add((sx, sy))
        for entity in list(self.enemies):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    scene_protected.add((entity.x + dx, entity.y + dy))
        for event in list(self.events):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    scene_protected.add((event.x + dx, event.y + dy))
        for item in list(self.world_items):
            scene_protected.add((item.x, item.y))
        for px, py in self.realm_features.get('millennium_cabin', {}).get('main_path', ()):
            scene_protected.add((px, py))
        self.light_scene_report = place_light_scenes(
            cells, self.seed + depth * 1009, depth, definition.realm_id,
            protected=scene_protected,
        )
        # §12 F：位面环境设施。弧光灯架只装在玩具的回忆**真有电线**的墙格上，
        # 且初始亮灭按当前通电状态（后面每回合由 sync_light_fixtures 同步）；
        # 余烬灯盏只落在余烬廊桥，旁边不许有别的可燃物（防连片烧）。
        from .fixtures import place_light_fixtures
        fixture_protected = set(scene_protected)
        if definition.realm_id == "ember_bridge":
            # 余烬廊桥的三道蜡门是解谜闸门：灯盏绝不能改造它们（烧穿即绕过谜题）。
            from ..data.realm_challenges import EMBER_STAGES
            for stage in EMBER_STAGES:
                gate_x = stage["gate"][0]
                for gy in range(10, 14):
                    fixture_protected.add((gate_x, gy))
        self.light_fixture_report = place_light_fixtures(
            cells, self.seed + depth * 1009, depth, definition.realm_id,
            protected=fixture_protected, spawn=spawn,
            energized=self._logic_energized,
        )
        # ---- 通用环境填充（2026-10-24）：非任务型位面的骨架地图补常规内容 ----
        # 门之回廊这类「环廊探索」位面此前只有骨架：整层一种地板、没有变体、
        # 没有植物/容器/液气，大片走廊显得空旷。任务型短位面（玩具/余烬）是
        # 手关解谜，保持原样；退潮厅只补地板与少量植物，液气/容器交给潮汐规则。
        from .realm_environment import REALM_FLOOR_PALETTES, fill_environment
        env_protected: set[tuple[int, int]] = set()
        for sy in range(spawn[1] - 1, spawn[1] + 2):
            for sx in range(spawn[0] - 1, spawn[0] + 2):
                env_protected.add((sx, sy))
        for entity in self.enemies:
            env_protected.add((entity.x, entity.y))
        for event in self.events:
            env_protected.add((event.x, event.y))
        for item in self.world_items:
            env_protected.add((item.x, item.y))
        env_protected.add((width // 2, height // 2))
        for cy, row in enumerate(cells):
            for cx, cell in enumerate(row):
                if cell.liquid or cell.gas:
                    # 作者写好的液体/气体（如引火燃油）不参与自然投放。
                    env_protected.add((cx, cy))
        if definition.realm_id in ("millennium_garden", "library_palace", "white_sanatorium"):
            from .realm_environment import fill_long_realm_environment
            fill_long_realm_environment(self, depth, spawn, env_protected)
        elif definition.realm_id == "door_corridor":
            fill_environment(
                cells, seed=self.seed + depth * 1009, depth=depth,
                realm_id=definition.realm_id, protected=env_protected,
                palette=REALM_FLOOR_PALETTES["door_corridor"],
                base_coverage=0.55, plant_coverage=0.05,
                containers=True, liquids=True, gases=True,
                spawn=spawn,
            )
            for row in cells:
                for cell in row:
                    if cell.liquid or cell.gas:
                        self._prime_material_clocks(cell)
            self._reset_material_index()
        elif definition.realm_id == "ebbing_hall":
            # 退潮厅的水位由潮汐规则接管，只补地板与少量植物，不铺自然液气/容器。
            fill_environment(
                cells, seed=self.seed + depth * 1009, depth=depth,
                realm_id=definition.realm_id, protected=env_protected,
                palette=REALM_FLOOR_PALETTES["ebbing_hall"],
                base_coverage=0.5, plant_coverage=0.035,
                containers=False, liquids=False, gases=False,
                spawn=spawn,
            )
            self._reset_material_index()


# ---- 地形算法：同心环门廊（门之回廊） ----

def _generate_ring_corridors(state: "DreamRealmMixin", definition: DreamRealmDef,
                             depth: int) -> tuple[int, int, list[list[Cell]], tuple[int, int]]:
    """五重同心矩形环廊：外环 → 中环 → 内圣所，环与环之间以「门」相通。

    - 走廊宽 2 格；环间隔墙 2 格厚（realm 专属墙种「门扉之壁」）；
    - 每道隔墙按层号确定性地打成一条门廊（普通门墙种，踩上即开）；
    - 最内是 5×5 圣所：台面放着本层独特物品；
    - 玩家出生在外环西侧。
    """
    width, height = 66, 50
    cells = [[Cell() for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            cells[y][x].solid = True
            cells[y][x].wall_kind = definition.wall_kind
            cells[y][x].hardness = 3
            cells[y][x].integrity = 90

    def carve_ring(x1: int, y1: int, x2: int, y2: int, thickness: int = 2) -> None:
        """挖一条矩形环廊（沿边框向内 thickness 格的开放带）。"""
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                on_band = (
                    x <= x1 + thickness - 1 or x >= x2 - thickness + 1
                    or y <= y1 + thickness - 1 or y >= y2 - thickness + 1
                )
                if on_band:
                    _clear(cells, x, y)

    def open_door(x: int, y: int) -> None:
        """在隔墙上开一扇门（普通门：踩上即开）。"""
        cell = cells[y][x]
        cell.solid = True
        cell.wall_kind = "门"
        cell.hardness = 1
        cell.integrity = 30

    rng = random.Random(state.seed ^ depth * 3571)
    rings = [
        (2, 2, width - 3, height - 3),      # 外环
        (8, 7, width - 9, height - 8),
        (14, 12, width - 15, height - 13),
        (20, 17, width - 21, height - 18),
        (26, 22, width - 27, height - 23),
    ]
    for ring in rings:
        carve_ring(*ring)
    # 环与环之间的门：把整条隔墙打成门（隔墙 = 两环环带之间的实心带，
    # 上下 2 格厚、左右 3–4 格厚），位置随层号旋转。
    for k in range(len(rings) - 1):
        inner = rings[k + 1]
        # 隔墙实体范围：本环环带外沿之外、内环环带内沿之里。
        wall_top, wall_bottom = rings[k][1] + 2, inner[1] - 1
        wall_left, wall_right = inner[2] + 1, rings[k][2] - 2
        # 上侧门 + 右侧门（位置随层号平移，避免每层一样的走法）。
        door_x = inner[0] + 2 + (depth * 3 + k * 2) % max(1, inner[2] - inner[0] - 4)
        for wy in range(wall_top, wall_bottom + 1):   # 打穿上隔墙
            open_door(door_x, wy)
        door_y = inner[1] + 2 + (depth * 2 + k * 3) % max(1, inner[3] - inner[1] - 4)
        for wx in range(wall_left, wall_right + 1):   # 打穿右隔墙
            open_door(wx, door_y)
    # 内圣所：5×5 全开 + 中央石台。
    sx, sy = width // 2, height // 2
    for y in range(sy - 2, sy + 3):
        for x in range(sx - 2, sx + 3):
            _clear(cells, x, y)
    cells[sy][sx].solid = True
    cells[sy][sx].wall_kind = "石台"
    cells[sy][sx].hardness = 2
    cells[sy][sx].integrity = 70
    # 出生点：外环西侧走廊中段。
    spawn = (4, height // 2)
    _clear(cells, 3, height // 2)
    _clear(cells, 4, height // 2)
    return width, height, cells, spawn


def _clear(cells: list[list[Cell]], x: int, y: int) -> None:
    cell = cells[y][x]
    cell.solid = False
    cell.wall_kind = ""
    cell.hardness = 0
    cell.integrity = 0


def _carve_room(cells, x1, y1, x2, y2):
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            cells[y][x].solid = False
            cells[y][x].wall_kind = ""


def _generate_toy_rooms(state, definition: DreamRealmDef, depth: int):
    from .toy_puzzles import generate_toy_board
    return generate_toy_board(state, definition, depth)


def _generate_toy_sokoban(state, definition: DreamRealmDef, depth: int):
    from .toy_puzzles import generate_sokoban_board
    return generate_sokoban_board(state, definition, depth)


def _put_partition(cells: list[list[Cell]], x: int, ys) -> None:
    """立一道脆弱的隔墙（hardness 1 / integrity 20）：待气爆一举炸开。"""
    for y in ys:
        cell = cells[y][x]
        cell.solid = True
        cell.wall_kind = "门扉之壁"
        cell.hardness = 1
        cell.integrity = 20


def _generate_ember_bridge(state, definition: DreamRealmDef, depth: int):
    from .realm_layouts import ember_bridge
    return ember_bridge(state, definition, depth)


def _generate_ebbing_hall(state, definition: DreamRealmDef, depth: int):
    from .realm_layouts import ebbing_hall
    return ebbing_hall(state, definition, depth)


def _generate_millennium_park(state, definition: DreamRealmDef, depth: int):
    from .realm_layouts import millennium_park
    return millennium_park(state, definition, depth)


_REALM_GENERATORS = {
    "rings": _generate_ring_corridors,
    "toy_rooms": _generate_toy_rooms,
    "toy_sokoban": _generate_toy_sokoban,
    "ember_bridge": _generate_ember_bridge,
    "ebbing_hall": _generate_ebbing_hall,
    "millennium_park": _generate_millennium_park,
}


def _generate_library_palace(state, definition, depth):
    from .library_layouts import generate_library_layout
    from .entities import WorldEvent
    plan = generate_library_layout(state.seed, depth)
    from .library_content import install
    install(state, plan, depth)
    from .realm_enrichment import complete_content
    complete_content(state,plan,depth,'library_palace')
    return plan.width, plan.height, plan.cells, plan.spawn


_REALM_GENERATORS["library_palace"] = _generate_library_palace


def _generate_white_sanatorium(state, definition, depth):
    from .hospital_layouts import generate_hospital_layout
    from ..data.hospital import HOSPITAL_FLOOR_NAMES
    from .entities import WorldEvent
    plan = generate_hospital_layout(state.seed, depth)
    state.theme = HOSPITAL_FLOOR_NAMES[depth-1]
    state.realm_bg_zones = [{"rect": (0, 0, plan.width-1, plan.height-1), "color": "#b7b8b8"}]
    state.realm_features = {
        "version": plan.version, "rooms": plan.rooms, "tanks": plan.tanks,
        "lights": plan.lights, "furniture": plan.furniture,
        "protected": sorted(plan.protected_cells), "core_anchor": plan.core_anchor, 'exit': plan.exit,
        'core_fluid_open': True,
        'infusion_slots': [(plan.core_anchor[0]+dx, plan.core_anchor[1]+dy)
                           for dx, dy in ((0, 0), (1, 0), (-1, 0))] if plan.core_anchor else [],
    }
    state._pending_realm_events = [WorldEvent(
        event_id=f"event.hospital.return.{depth}", catalog_id="event.hospital.return",
        name="撤离登记台", x=plan.spawn[0]+1, y=plan.spawn[1], kind="compound", bound=True,
        description="入院记录上始终保留着离开的许可。",
        dialogue=("可以撤离至主梦；设备、储罐和已领取的物品会保留。",),
        options=({"label": "办理撤离，返回主梦", "realm_return": True},
                 {"label": "继续探索", "leave": True}), dissolution_reward=0)]
    for tank in plan.tanks:
        state._pending_realm_events.append(WorldEvent(
            event_id=tank['uid']+':port', catalog_id='event.hospital.tank',
            name='封闭气罐端口', x=tank['port'][0], y=tank['port'][1],
            description='封闭气室的外接端口；气体有限，可抽取或定量排放。',
            dialogue=(tr('罐内存有{kind}。每次至多转移 6 单位；操作消耗一回合，取消免费。', kind=tr(tank['gas'])),),
            kind='compound', bound=True, dissolution_reward=0,
            options=({'label': '抽取至首个兼容气体容器', 'hospital_control': {'operation': 'draw', 'tank_uid': tank['uid']}},
                     {'label': '向端口排放至多 6 单位', 'hospital_control': {'operation': 'vent', 'tank_uid': tank['uid']}},
                     {'label': '保留储气，离开', 'leave': True})))
    if plan.lights:
        sources = sorted(plan.lights, key=lambda p: abs(p[0]-plan.spawn[0])+abs(p[1]-plan.spawn[1]))[:4]
        state._pending_realm_events.append(WorldEvent(
            event_id=f'{state.seed}:hospital:{depth}:lights', catalog_id='event.hospital.lights',
            name='灯段控制台', x=plan.spawn[0]-1, y=plan.spawn[1],
            description='控制前厅附近四盏灯；开关同时影响双方视野。',
            dialogue=('灯光同样照见你。开关消耗一回合，取消不耗时。',),
            kind='compound', bound=True, dissolution_reward=0,
            options=({'label': '关闭灯段', 'hospital_control': {'operation': 'lights', 'enabled': False, 'sources': sources}},
                     {'label': '开启灯段', 'hospital_control': {'operation': 'lights', 'enabled': True, 'sources': sources}},
                     {'label': '保持灯光，离开', 'leave': True})))
    if plan.core_anchor:
        cx, cy = plan.core_anchor
        state._pending_realm_events.append(WorldEvent(
            event_id=f'{state.seed}:hospital:5:fluid_valve', catalog_id='event.hospital.core_valve',
            name='回流配液阀', x=cx-5, y=cy+4, description='控制核心的有限储液配给；关闭后停止回流配液，不回充储量。',
            dialogue=('阀门控制供液，不改变地上已有的液体。开关消耗一回合。',),
            kind='compound', bound=True, dissolution_reward=0,
            options=({'label': '关闭配液阀', 'hospital_control': {'operation': 'fluid_valve', 'enabled': False}},
                     {'label': '开启配液阀', 'hospital_control': {'operation': 'fluid_valve', 'enabled': True}},
                     {'label': '暂不操作', 'leave': True})))
    from .hospital_scenes import install_hospital_scenes
    install_hospital_scenes(state, plan, depth)
    from .realm_enrichment import complete_content
    complete_content(state,plan,depth,'white_sanatorium')
    return plan.width, plan.height, plan.cells, plan.spawn


_REALM_GENERATORS["white_sanatorium"] = _generate_white_sanatorium
